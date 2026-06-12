/**
 * API client for the Pico y Placa Cloudflare Worker.
 *
 * Base URL is configurable via HTML data attribute or falls back to
 * the production Worker URL.
 */

const BASE_URL =
  document.querySelector("script[data-api-url]")?.dataset.apiUrl ??
  "https://pico-y-placa-api.juanchob612.workers.dev";

/**
 * @typedef {Object} RestriccionResponse
 * @property {string} municipio
 * @property {string} fecha
 * @property {string} placa_normalized
 * @property {boolean} restricted
 * @property {number} last_digit
 * @property {string} formato_detectado
 * @property {"weekday"|"saturday"|"festivo"} rule
 * @property {"rotation"|"override"} source
 * @property {string} generated_at
 */

/**
 * @typedef {Object} ErrorResponse
 * @property {"bad_plate"|"bad_date"|"bad_municipio"|"rotation_unknown"} error
 * @property {string} [municipio]
 * @property {string} [requested_date]
 */

/**
 * @typedef {Object} ScheduleResponse
 * @property {Object|null} current
 * @property {Object|null} next
 * @property {string|null} message
 */

/**
 * Fetch restriction status for a plate.
 * @param {string} municipio
 * @param {string} fecha - YYYY-MM-DD
 * @param {string} placa
 * @returns {Promise<RestriccionResponse|ErrorResponse>}
 */
export async function fetchRestriccion(municipio, fecha, placa) {
  const params = new URLSearchParams({ municipio, fecha, placa });
  const res = await fetch(`${BASE_URL}/v1/restriccion?${params}`);
  return res.json();
}

/**
 * Fetch the current rotation schedule for a municipality.
 * @param {string} municipio
 * @returns {Promise<ScheduleResponse>}
 */
export async function fetchSchedule(municipio) {
  const params = new URLSearchParams({ municipio });
  const res = await fetch(`${BASE_URL}/v1/schedule?${params}`);
  return res.json();
}

const SCHEDULE_CACHE_KEY = "pyp_schedule_cache";
const SCHEDULE_CACHE_TTL = 3600_000; // 1 hora (el schedule trimestral no cambia)

const WEEKDAYS = [
  "domingo",
  "lunes",
  "martes",
  "miércoles",
  "jueves",
  "viernes",
  "sábado",
];

const UNACCENT_FALLBACK = {
  miercoles: "miércoles",
  sabado: "sábado",
};

/**
 * Try to load a cached schedule from localStorage.
 * @param {string} municipio
 * @returns {{ schedule: object, fromCache: boolean }|null}
 */
function loadCachedSchedule(municipio) {
  try {
    const raw = localStorage.getItem(SCHEDULE_CACHE_KEY);
    if (!raw) return null;
    const cache = JSON.parse(raw);
    if (cache.municipio !== municipio) return null;
    if (Date.now() - cache.ts > SCHEDULE_CACHE_TTL) return null;
    return { schedule: cache.schedule, fromCache: true };
  } catch {
    return null;
  }
}

/**
 * Save a schedule to localStorage.
 * @param {string} municipio
 * @param {object} schedule — raw_payload shape from /v1/schedule current
 */
function saveCachedSchedule(municipio, schedule) {
  try {
    localStorage.setItem(
      SCHEDULE_CACHE_KEY,
      JSON.stringify({ municipio, schedule, ts: Date.now() }),
    );
  } catch {
    // localStorage full — silently ignore
  }
}

/**
 * Calculate restricted digits for a given date from a raw_payload.
 * Pure function — no network, no side effects.
 * @param {object} payload — raw_payload with .weekdays and optional .saturday_calendar
 * @param {Date} date
 * @returns {number[]|null}
 */
function calcDigitsFromPayload(payload, date) {
  const dayIndex = date.getDay(); // 0=Sun
  if (dayIndex === 0) return null;

  const weekdayName = WEEKDAYS[dayIndex];
  const weekdays = payload.weekdays ?? {};

  let digits = weekdays[weekdayName];

  // Fallback: unaccented keys (scraper may produce either form)
  if (!digits) {
    const fallback = UNACCENT_FALLBACK[weekdayName];
    if (fallback) digits = weekdays[fallback];
  }

  if (!digits || digits.length === 0) return null;
  return digits;
}

/**
 * Fetch hero data: today's restricted digits and whether today is restricted.
 *
 * Strategy:
 *   1. Try cached schedule → compute digits client-side (0 ms)
 *   2. If no cache, fetch schedule + dummy restriccion in parallel (one round-trip)
 *   3. Dummy restriccion detects festivos / overrides that override the rotation
 *
 * @param {string} municipio
 * @param {string} fecha - YYYY-MM-DD
 * @returns {Promise<{digits: number[]|null, isRestricted: boolean}>}
 */
export async function fetchHeroData(municipio, fecha) {
  const date = new Date(fecha + "T12:00:00");

  // Sunday → always calm
  if (date.getDay() === 0) {
    return { digits: null, isRestricted: false };
  }

  try {
    // 1. Try cached schedule
    const cached = loadCachedSchedule(municipio);

    if (cached) {
      const digits = calcDigitsFromPayload(cached.schedule, date);

      // Quick festivo check — still need the API for this
      const dummy = await fetchRestriccion(municipio, fecha, "ABC123");

      if (dummy && dummy.rule === "festivo") {
        return { digits: null, isRestricted: false };
      }

      return {
        digits,
        isRestricted: !!digits && digits.length > 0,
      };
    }

    // 2. No cache — fetch schedule + dummy in parallel
    const [schedule, dummy] = await Promise.all([
      fetchSchedule(municipio),
      fetchRestriccion(municipio, fecha, "ABC123"),
    ]);

    // Cache the schedule for next time
    if (schedule.current) {
      saveCachedSchedule(municipio, schedule.current.raw_payload);
    }

    // If the dummy call says today is festivo → calm state
    if (dummy && dummy.rule === "festivo") {
      return { digits: null, isRestricted: false };
    }

    // If no current rotation → calm state
    if (!schedule.current || schedule.message) {
      return { digits: null, isRestricted: false };
    }

    const digits = calcDigitsFromPayload(schedule.current.raw_payload, date);

    if (!digits || digits.length === 0) {
      return { digits: null, isRestricted: false };
    }

    return { digits, isRestricted: true };
  } catch {
    // Offline or API unreachable → calm state
    return { digits: null, isRestricted: false };
  }
}

export { BASE_URL };

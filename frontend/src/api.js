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

/**
 * Fetch hero data: today's restricted digits and whether today is restricted.
 * Uses a two-call strategy: schedule for digits + a dummy restriccion to detect
 * festivos / overrides that make today restriction-free.
 *
 * @param {string} municipio
 * @param {string} fecha - YYYY-MM-DD (today)
 * @returns {Promise<{digits: number[]|null, isRestricted: boolean}>}
 */
export async function fetchHeroData(municipio, fecha) {
  const WEEKDAYS = [
    "domingo",
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
  ];

  try {
    const [schedule, dummy] = await Promise.all([
      fetchSchedule(municipio),
      fetchRestriccion(municipio, fecha, "ABC123"),
    ]);

    // If today is Sunday → calm state
    const todayIndex = new Date(fecha + "T12:00:00").getDay();
    if (todayIndex === 0) {
      return { digits: null, isRestricted: false };
    }

    // If the dummy call says today is festivo → calm state
    if (dummy && dummy.rule === "festivo") {
      return { digits: null, isRestricted: false };
    }

    // If no current rotation → calm state
    if (!schedule.current || schedule.message) {
      return { digits: null, isRestricted: false };
    }

    const weekdayName = WEEKDAYS[todayIndex];
    const weekdays = schedule.current.raw_payload?.weekdays ?? {};

    // Handle both accented and unaccented keys
    const digits =
      weekdays[weekdayName] ??
      weekdays[weekdayName.replace("é", "e")] ??
      weekdays[weekdayName.replace("á", "a")] ??
      null;

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

/**
 * Pico y Placa Bucaramanga — Cloudflare Worker API.
 *
 * Endpoints:
 *   GET /v1/restriccion?municipio=X&fecha=YYYY-MM-DD&placa=ABC123
 *   GET /v1/schedule?municipio=X
 *
 * Read-only. No auth, no CORS. Cache-Control: public, max-age=3600 on 200.
 */

import postgres from "postgres";
import { createQueries } from "./db";
import { parsePlaca, PlateValidationError } from "./parser";
import type {
  ErrorResponse,
  Queries,
  RestriccionResponse,
  RotationPayload,
  ScheduleResponse,
} from "./types";

// ---------------------------------------------------------------------------
// Environment
// ---------------------------------------------------------------------------

export interface Env {
  DATABASE_URL: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const VALID_MUNICIPIOS = new Set([
  "bucaramanga",
  "floridablanca",
  "giron",
  "piedecuesta",
]);

const DEFAULT_MUNICIPIO = "bucaramanga";

const SPANISH_WEEKDAYS: Record<number, string> = {
  0: "domingo",
  1: "lunes",
  2: "martes",
  3: "miércoles",
  4: "jueves",
  5: "viernes",
  6: "sábado",
};

/** Fallback unaccented weekday keys (scraper may output either form). */
const WEEKDAY_FALLBACK: Record<string, string> = {
  miercoles: "miércoles",
  sabado: "sábado",
};

const MIN_DATE = "2022-01-01";
const CACHE_HEADER = "public, max-age=3600";

// ---------------------------------------------------------------------------
// Default export — CF Worker entry point
// ---------------------------------------------------------------------------

export default {
  async fetch(
    request: Request,
    env: Env,
    _ctx: ExecutionContext,
  ): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path === "/v1/restriccion" && request.method === "GET") {
      const sql = postgres(env.DATABASE_URL, {
        idle_timeout: 10,
        max_lifetime: 60,
      });
      const queries = createQueries(sql);
      return handleRestriccion(url, queries);
    }

    if (path === "/v1/schedule" && request.method === "GET") {
      const sql = postgres(env.DATABASE_URL, {
        idle_timeout: 10,
        max_lifetime: 60,
      });
      const queries = createQueries(sql);
      return handleSchedule(url, queries);
    }

    return new Response("Not Found", { status: 404 });
  },
};

// ---------------------------------------------------------------------------
// GET /v1/restriccion — REQ-API-001/002/003
// ---------------------------------------------------------------------------

export async function handleRestriccion(
  url: URL,
  queries: Queries,
): Promise<Response> {
  // --- Parameter extraction ---
  const municipioRaw = url.searchParams.get("municipio");
  const municipio = (municipioRaw ?? DEFAULT_MUNICIPIO).toLowerCase().trim();
  const fecha = url.searchParams.get("fecha")?.trim() ?? "";
  const placa = url.searchParams.get("placa") ?? "";

  // --- Validation ---
  if (!VALID_MUNICIPIOS.has(municipio)) {
    return json(400, { error: "bad_municipio" });
  }
  if (!isValidDate(fecha)) {
    return json(400, { error: "bad_date" });
  }

  // Plate parsing (server-side — not duplicated in frontend)
  let parseResult;
  try {
    parseResult = parsePlaca(placa);
  } catch (err) {
    if (err instanceof PlateValidationError) {
      return json(400, { error: "bad_plate" });
    }
    return json(400, { error: "bad_plate" });
  }

  // --- Check exception override first (suspensions) ---
  const override = await queries.getOverride(municipio, fecha);
  if (override) {
    return json200({
      municipio,
      fecha,
      placa_normalized: parseResult.placaNormalized,
      restricted: false,
      last_digit: parseResult.lastDigit,
      formato_detectado: parseResult.formatoDetectado,
      rule: resolveDayRule(fecha),
      source: "override",
      generated_at: new Date().toISOString(),
    });
  }

  // --- Check holiday (festivo or Sunday) ---
  const holiday = await queries.getHoliday(fecha);
  const dateObj = parseDate(fecha)!;
  const dayOfWeek = dateObj.getUTCDay(); // 0=Sun, 6=Sat
  if (holiday || dayOfWeek === 0) {
    return json200({
      municipio,
      fecha,
      placa_normalized: parseResult.placaNormalized,
      restricted: false,
      last_digit: parseResult.lastDigit,
      formato_detectado: parseResult.formatoDetectado,
      rule: "festivo",
      source: "rotation",
      generated_at: new Date().toISOString(),
    });
  }

  // --- Look up rotation ---
  const rotation = await queries.getRotation(municipio, fecha);
  if (!rotation) {
    return json(404, {
      error: "rotation_unknown",
      municipio,
      requested_date: fecha,
    });
  }

  const payload = rotation.raw_payload as RotationPayload;

  // --- Saturday: consult per-week calendar ---
  if (dayOfWeek === 6) {
    const isoWeek = getISOWeek(dateObj);
    const calendar = payload.saturday_calendar ?? {};
    const digits = calendar[String(isoWeek)] ?? calendar[isoWeek];

    if (digits && digits.length > 0) {
      const restricted = digits.includes(parseResult.lastDigit);
      return json200({
        municipio,
        fecha,
        placa_normalized: parseResult.placaNormalized,
        restricted,
        last_digit: parseResult.lastDigit,
        formato_detectado: parseResult.formatoDetectado,
        rule: "saturday",
        source: "rotation",
        generated_at: new Date().toISOString(),
      });
    }

    // Conservative default — no calendar entry → not restricted
    return json200({
      municipio,
      fecha,
      placa_normalized: parseResult.placaNormalized,
      restricted: false,
      last_digit: parseResult.lastDigit,
      formato_detectado: parseResult.formatoDetectado,
      rule: "saturday",
      source: "rotation",
      generated_at: new Date().toISOString(),
    });
  }

  // --- Weekday: check rotation digits ---
  const weekdayKey = SPANISH_WEEKDAYS[dayOfWeek]!;
  const weekdays = payload.weekdays ?? {};
  let digits = weekdays[weekdayKey];

  // Fallback: try unaccented key
  if (!digits) {
    const fallback = WEEKDAY_FALLBACK[weekdayKey];
    if (fallback) {
      digits = weekdays[fallback];
    }
  }

  if (!digits || digits.length === 0) {
    // Weekday not present in payload — fail-safe
    return json(404, {
      error: "rotation_unknown",
      municipio,
      requested_date: fecha,
    });
  }

  const restricted = digits.includes(parseResult.lastDigit);

  return json200({
    municipio,
    fecha,
    placa_normalized: parseResult.placaNormalized,
    restricted,
    last_digit: parseResult.lastDigit,
    formato_detectado: parseResult.formatoDetectado,
    rule: "weekday",
    source: "rotation",
    generated_at: new Date().toISOString(),
  });
}

// ---------------------------------------------------------------------------
// GET /v1/schedule — REQ-API-006
// ---------------------------------------------------------------------------

export async function handleSchedule(
  url: URL,
  queries: Queries,
): Promise<Response> {
  const municipioRaw = url.searchParams.get("municipio");
  const municipio = (municipioRaw ?? DEFAULT_MUNICIPIO).toLowerCase().trim();

  if (!VALID_MUNICIPIOS.has(municipio)) {
    return json(400, { error: "bad_municipio" });
  }

  const current = await queries.getCurrentRotation(municipio);
  const next = await queries.getNextRotation(municipio);

  const body: ScheduleResponse = {
    current: current
      ? {
          valid_from: current.valid_from,
          valid_to: current.valid_to,
          raw_payload: current.raw_payload as Record<string, unknown>,
        }
      : null,
    next: next
      ? {
          valid_from: next.valid_from,
          valid_to: next.valid_to,
          raw_payload: next.raw_payload as Record<string, unknown>,
        }
      : null,
    message: current ? null : "rotation_unknown",
  };

  return json200(body);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Validate ISO date format YYYY-MM-DD, must be >= 2022-01-01. */
function isValidDate(s: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const d = parseDate(s);
  if (!d) return false;
  return s >= MIN_DATE;
}

/** Parse YYYY-MM-DD to Date in UTC (no timezone shift). */
function parseDate(s: string): Date | null {
  const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!parts) return null;
  const d = new Date(Date.UTC(+parts[1]!, +parts[2]! - 1, +parts[3]!));
  // Validate the parsed date matches input (catch Feb 30, etc.)
  const iso = d.toISOString().split("T")[0]!;
  return iso === s ? d : null;
}

/** Compute ISO 8601 week number. */
function getISOWeek(d: Date): number {
  const date = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  const dayNum = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

/** Resolve the rule label for a date (used when an override exists). */
function resolveDayRule(fecha: string): "weekday" | "saturday" | "festivo" {
  const d = parseDate(fecha);
  if (!d) return "weekday";
  const dow = d.getUTCDay();
  if (dow === 0) return "festivo";
  if (dow === 6) return "saturday";
  return "weekday";
}

/** Return a JSON 200 response with Cache-Control. */
function json200(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": CACHE_HEADER,
    },
  });
}

/** Return a JSON error response. */
function json(status: number, body: ErrorResponse): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

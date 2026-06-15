/**
 * Contract tests for the Worker API.
 *
 * Covers REQ-API-001 through REQ-API-009.
 * Tests call handler functions directly with mocked Queries interface —
 * no miniflare needed for contract validation.
 */

import { describe, expect, it } from "vitest";
import { handleRestriccion, handleSchedule } from "../src/index";
import type {
  HolidayRow,
  OverrideRow,
  Queries,
  RotationRow,
} from "../src/types";

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

/** Build a URL with query params. */
function makeUrl(path: string, params: Record<string, string>): URL {
  const url = new URL(`http://localhost${path}`);
  for (const [k, v] of Object.entries(params)) {
    url.searchParams.set(k, v);
  }
  return url;
}

/** Parse JSON body from a Response. */
async function bodyJson(resp: Response): Promise<Record<string, unknown>> {
  return resp.json() as Promise<Record<string, unknown>>;
}

/** Factory for a mock Queries object. */
function mockQueries(overrides: Partial<Queries> = {}): Queries {
  return {
    getRotation: async () => null,
    getOverride: async () => null,
    getHoliday: async () => null,
    getCurrentRotation: async () => null,
    getNextRotation: async () => null,
    ...overrides,
  };
}

/** Create a valid rotation row. */
function makeRotation(
  overrides: Partial<RotationRow> = {},
): RotationRow {
  return {
    id: "rot-1",
    municipality: "bucaramanga",
    valid_from: "2026-06-01",
    valid_to: "2026-09-30",
    raw_payload: {
      weekdays: {
        lunes: [5, 6],
        martes: [1, 2],
        miércoles: [3, 4],
        jueves: [7, 8],
        viernes: [9, 0],
      },
      saturday_calendar: {},
      article_title: "Test Rotation",
      article_url: "https://example.com",
    },
    source_url: "https://example.com",
    scraped_at: "2026-06-10T00:00:00Z",
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// REQ-API-001: GET /v1/restriccion happy path (200)
// ---------------------------------------------------------------------------

describe("REQ-API-001: GET /v1/restriccion — happy path (200)", () => {
  it("returns restricted=true for a restricted plate on a weekday", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-15", // Monday
      placa: "ABC005",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.municipio).toBe("bucaramanga");
    expect(body.fecha).toBe("2026-06-15");
    expect(body.placa_normalized).toBe("ABC005");
    expect(body.restricted).toBe(true);
    expect(body.last_digit).toBe(5);
    expect(body.formato_detectado).toBe("particular");
    expect(body.rule).toBe("weekday");
    expect(body.source).toBe("rotation");
    expect(body.generated_at).toBeDefined();
    expect(resp.headers.get("cache-control")).toBe("public, max-age=3600");
  });

  it("returns restricted=false for unrestricted plate", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-15", // Monday (restricts 5,6)
      placa: "ABC003",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.restricted).toBe(false);
    expect(body.last_digit).toBe(3);
  });

  it("extracts correct digit for letter-then-digit plate", async () => {
    const queries = mockQueries({
      getRotation: async () =>
        makeRotation({
          raw_payload: {
            weekdays: {
              lunes: [5, 6],
              martes: [1, 2],
              miércoles: [3, 4],
              jueves: [7, 8],
              viernes: [9, 0],
            },
            saturday_calendar: {},
            article_title: "Test",
            article_url: "",
          },
        }),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-16", // Tuesday (restricts 1,2)
      placa: "ABC12D",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.last_digit).toBe(2);
    expect(body.restricted).toBe(true);
    expect(body.placa_normalized).toBe("ABC12D");
    expect(body.formato_detectado).toBe("moto");
  });

  it("returns formato_detectado=oficial for OAB 123", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-16", // Tuesday
      placa: "OAB 123",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.formato_detectado).toBe("oficial");
    expect(body.placa_normalized).toBe("OAB123");
  });

  it("normalizes placa stripping whitespace and separators", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-16",
      placa: "abc-123",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.placa_normalized).toBe("ABC123");
  });

  it("defaults municipality to bucaramanga when omitted", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    const url = makeUrl("/v1/restriccion", {
      fecha: "2026-06-16",
      placa: "ABC123",
    });
    // Don't set municipio param
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.municipio).toBe("bucaramanga");
  });

  it("includes Cache-Control header on 200", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-16",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    expect(resp.headers.get("cache-control")).toBe("public, max-age=3600");
  });
});

// ---------------------------------------------------------------------------
// REQ-API-002: GET /v1/restriccion fail-safe (404)
// ---------------------------------------------------------------------------

describe("REQ-API-002: GET /v1/restriccion — fail-safe (404)", () => {
  it("returns 200 for a future date inside a known rotation", async () => {
    const queries = mockQueries({
      getRotation: async () =>
        makeRotation({
          valid_from: "2026-07-01",
          valid_to: "2026-09-30",
        }),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-08-15",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    expect(resp.status).toBe(200);
  });

  it("returns 404 for date outside any known rotation", async () => {
    const rotation = makeRotation({
      valid_from: "2026-07-01",
      valid_to: "2026-09-30",
    });
    const queries = mockQueries({
      // Mock is date-aware — returns null for dates outside range
      getRotation: async (_municipio, fecha) => {
        if (fecha >= rotation.valid_from && fecha <= rotation.valid_to) {
          return rotation;
        }
        return null;
      },
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-12-01",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(404);
    expect(body.error).toBe("rotation_unknown");
    expect(body.municipio).toBe("bucaramanga");
    expect(body.requested_date).toBe("2026-12-01");
  });

  it("returns 404 when rotations table is empty", async () => {
    const queries = mockQueries(); // all return null
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-15",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(404);
    expect(body.error).toBe("rotation_unknown");
  });
});

// ---------------------------------------------------------------------------
// REQ-API-003: GET /v1/restriccion validation errors (400)
// ---------------------------------------------------------------------------

describe("REQ-API-003: GET /v1/restriccion — validation errors (400)", () => {
  const queries = mockQueries();

  it("rejects malformed fecha", async () => {
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "not-a-date",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);
    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_date");
  });

  it("rejects ISO datetime (not date-only)", async () => {
    const url = new URL("http://localhost/v1/restriccion");
    url.searchParams.set("municipio", "bucaramanga");
    url.searchParams.set("fecha", "2026-06-15T10:00:00Z");
    url.searchParams.set("placa", "ABC123");
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);
    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_date");
  });

  it("rejects invalid fecha (Feb 30)", async () => {
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-02-30",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);
    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_date");
  });

  it("rejects unknown municipality slug", async () => {
    const url = makeUrl("/v1/restriccion", {
      municipio: "medellin",
      fecha: "2026-06-15",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);
    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_municipio");
  });

  it("rejects empty placa", async () => {
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-15",
      placa: "",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);
    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_plate");
  });

  it("rejects placa with no digit", async () => {
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-15",
      placa: "ABC",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);
    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_plate");
  });

  it("rejects placa over 32 chars", async () => {
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-15",
      placa: "A".repeat(33),
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);
    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_plate");
  });

  it("rejects bogota slug", async () => {
    const url = makeUrl("/v1/restriccion", {
      municipio: "bogota",
      fecha: "2026-06-15",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);
    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_municipio");
  });

  it("accepts all four AMB municipalities", async () => {
    const rotationQueries = mockQueries({
      getRotation: async () => makeRotation(),
      getHoliday: async () => null,
    });
    for (const m of ["bucaramanga", "floridablanca", "giron", "piedecuesta"]) {
      const url = makeUrl("/v1/restriccion", {
        municipio: m,
        fecha: "2026-06-16",
        placa: "ABC123",
      });
      const resp = await handleRestriccion(url, rotationQueries);
      expect(resp.status).toBe(200);
    }
  });
});

// ---------------------------------------------------------------------------
// REQ-API-004: Festivo behavior
// ---------------------------------------------------------------------------

describe("REQ-API-004: Festivo behavior", () => {
  it("festivo short-circuits the rule — returns restricted=false", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
      getHoliday: async (): Promise<HolidayRow> => ({
        date: "2026-07-20",
        name: "Día de la Independencia",
      }),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-07-20", // Independence day — Monday
      placa: "ABC005",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.restricted).toBe(false);
    expect(body.rule).toBe("festivo");
  });

  it("Sunday is treated as festivo", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-14", // Sunday
      placa: "ABC005",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.restricted).toBe(false);
    expect(body.rule).toBe("festivo");
  });
});

// ---------------------------------------------------------------------------
// REQ-API-005: Saturday behavior
// ---------------------------------------------------------------------------

describe("REQ-API-005: Saturday behavior", () => {
  it("Saturday WITH known calendar — restricted=true when digit matches", async () => {
    // June 13, 2026 is a Saturday. ISO week 24.
    const queries = mockQueries({
      getRotation: async () =>
        makeRotation({
          valid_from: "2026-06-01",
          valid_to: "2026-09-30",
          raw_payload: {
            weekdays: {
              lunes: [5, 6],
              martes: [1, 2],
              miércoles: [3, 4],
              jueves: [7, 8],
              viernes: [9, 0],
            },
            saturday_calendar: { "24": [1, 2] },
            article_title: "Test",
            article_url: "",
          },
        }),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-13", // Saturday in ISO week 24
      placa: "ABC001",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.restricted).toBe(true);
    expect(body.rule).toBe("saturday");
  });

  it("Saturday WITHOUT calendar — restricted=false (conservative default)", async () => {
    const queries = mockQueries({
      getRotation: async () =>
        makeRotation({
          // No saturday_calendar at all
          raw_payload: {
            weekdays: {
              lunes: [5, 6],
              martes: [1, 2],
              miércoles: [3, 4],
              jueves: [7, 8],
              viernes: [9, 0],
            },
            saturday_calendar: {},
            article_title: "Test",
            article_url: "",
          },
        }),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-13", // Saturday
      placa: "ABC005",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.restricted).toBe(false);
    expect(body.rule).toBe("saturday");
  });
});

// ---------------------------------------------------------------------------
// REQ-API-006: GET /v1/schedule
// ---------------------------------------------------------------------------

describe("REQ-API-006: GET /v1/schedule", () => {
  it("returns 200 with current rotation when active", async () => {
    const queries = mockQueries({
      getCurrentRotation: async () => ({
        valid_from: "2026-06-01",
        valid_to: "2026-09-30",
        raw_payload: {
          weekdays: { lunes: [5, 6] },
          saturday_calendar: {},
          article_title: "Q2",
          article_url: "",
        },
      }),
      getNextRotation: async () => null,
    });
    const url = makeUrl("/v1/schedule", { municipio: "bucaramanga" });
    const resp = await handleSchedule(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.current).toBeDefined();
    expect(body.current.valid_from).toBe("2026-06-01");
    expect(body.current.valid_to).toBe("2026-09-30");
    expect(body.current.raw_payload).toBeDefined();
    expect(body.next).toBeNull();
    expect(body.message).toBeNull();
    expect(resp.headers.get("cache-control")).toBe("public, max-age=3600");
  });

  it("returns 200 with message=rotation_unknown when no active rotation", async () => {
    const queries = mockQueries(); // all return null
    const url = makeUrl("/v1/schedule", { municipio: "bucaramanga" });
    const resp = await handleSchedule(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.current).toBeNull();
    expect(body.next).toBeNull();
    expect(body.message).toBe("rotation_unknown");
  });

  it("rejects invalid municipality with 400", async () => {
    const queries = mockQueries();
    const url = makeUrl("/v1/schedule", { municipio: "bogota" });
    const resp = await handleSchedule(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_municipio");
  });

  it("defaults municipality to bucaramanga", async () => {
    const queries = mockQueries({
      getCurrentRotation: async () => ({
        valid_from: "2026-06-01",
        valid_to: "2026-09-30",
        raw_payload: { weekdays: {}, saturday_calendar: {}, article_title: "", article_url: "" },
      }),
    });
    const url = makeUrl("/v1/schedule", {}); // no municipio param
    const resp = await handleSchedule(url, queries);
    expect(resp.status).toBe(200);
  });
});

// ---------------------------------------------------------------------------
// REQ-API-007: No auth, no CORS
// ---------------------------------------------------------------------------

describe("REQ-API-007: No CORS headers", () => {
  it("does not emit Access-Control-Allow-Origin on 200", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-16",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    expect(resp.headers.get("access-control-allow-origin")).toBeNull();
  });

  it("does not emit CORS headers on 400", async () => {
    const queries = mockQueries();
    const url = makeUrl("/v1/restriccion", {
      municipio: "bogota",
      fecha: "2026-06-16",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    expect(resp.headers.get("access-control-allow-origin")).toBeNull();
  });

  it("succeeds without Authorization header", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-16",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    expect(resp.status).toBe(200);
  });
});

// ---------------------------------------------------------------------------
// REQ-API-008: Municipality slug enum
// ---------------------------------------------------------------------------

describe("REQ-API-008: Municipality slug enum", () => {
  it("accepts all four AMB slugs in restriccion", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    for (const m of ["bucaramanga", "floridablanca", "giron", "piedecuesta"]) {
      const url = makeUrl("/v1/restriccion", {
        municipio: m,
        fecha: "2026-06-16",
        placa: "ABC123",
      });
      const resp = await handleRestriccion(url, queries);
      expect(resp.status).toBe(200);
    }
  });

  it("accepts all four AMB slugs in schedule", async () => {
    const queries = mockQueries({
      getCurrentRotation: async () => null,
    });
    for (const m of ["bucaramanga", "floridablanca", "giron", "piedecuesta"]) {
      const url = makeUrl("/v1/schedule", { municipio: m });
      const resp = await handleSchedule(url, queries);
      expect(resp.status).toBe(200);
    }
  });

  it("rejects slug outside enum", async () => {
    const queries = mockQueries();
    const url = makeUrl("/v1/restriccion", {
      municipio: "bogota",
      fecha: "2026-06-16",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);
    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_municipio");
  });
});

// ---------------------------------------------------------------------------
// REQ-API-009: fecha validation
// ---------------------------------------------------------------------------

describe("REQ-API-009: fecha validation", () => {
  it("accepts valid ISO date YYYY-MM-DD", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-15",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    expect(resp.status).toBe(200);
  });

  it("rejects ISO datetime with time component", async () => {
    const queries = mockQueries();
    const url = new URL("http://localhost/v1/restriccion");
    url.searchParams.set("municipio", "bucaramanga");
    url.searchParams.set("fecha", "2026-06-15T10:00:00Z");
    url.searchParams.set("placa", "ABC123");
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);
    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_date");
  });

  it("accepts dates ≥ 2022-01-01", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2022-01-01",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    expect(resp.status).toBe(200);
  });

  it("rejects dates before 2022-01-01", async () => {
    const queries = mockQueries();
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2021-12-31",
      placa: "ABC123",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);
    expect(resp.status).toBe(400);
    expect(body.error).toBe("bad_date");
  });
});

// ---------------------------------------------------------------------------
// Override behavior (source = "override")
// ---------------------------------------------------------------------------

describe("Exception overrides", () => {
  it("returns restricted=false with source=override when override exists", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
      getOverride: async (): Promise<OverrideRow> => ({
        id: "ovr-1",
        municipality: "bucaramanga",
        date: "2026-06-16",
        reason: "Semana Santa",
        source_url: "https://example.com",
        scraped_at: "2026-06-10T00:00:00Z",
      }),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-16",
      placa: "ABC001", // Would normally be restricted (Tuesday, digits 1,2)
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.restricted).toBe(false);
    expect(body.source).toBe("override");
    expect(body.rule).toBe("weekday"); // Tuesday
  });
});

// ---------------------------------------------------------------------------
// Edge cases
// ---------------------------------------------------------------------------

describe("Edge cases", () => {
  it("returns 200 with restricted=false for digit not in rotation", async () => {
    const queries = mockQueries({
      getRotation: async () =>
        makeRotation({
          raw_payload: {
            weekdays: { lunes: [5, 6], martes: [1, 2], miércoles: [3, 4], jueves: [7, 8], viernes: [9, 0] },
            saturday_calendar: {},
            article_title: "Test",
            article_url: "",
          },
        }),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-17", // Wednesday restricts 3,4
      placa: "ABC005", // digit 5 — NOT restricted
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.restricted).toBe(false);
    expect(body.last_digit).toBe(5);
  });

  // -------------------------------------------------------------------------
  // Holiday regression: real 2026 Colombian holidays (seed migration 0004)
  // -------------------------------------------------------------------------

  it("returns restricted=false for Sagrado Corazón (Jun 15, 2026)", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
      getHoliday: async (): Promise<HolidayRow> => ({
        date: "2026-06-15",
        name: "Sagrado Corazón de Jesús",
      }),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-15", // Monday — lunes restricts 5,6
      placa: "ABC005",      // digit 5, would be restricted without holiday
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.restricted).toBe(false);
    expect(body.rule).toBe("festivo");
    expect(body.last_digit).toBe(5);
  });

  it("returns restricted=true on non-holiday Monday for same digit", async () => {
    const queries = mockQueries({
      getRotation: async () => makeRotation(),
      // getHoliday returns null — no holiday for this date
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-22", // Monday, not a Colombian holiday
      placa: "ABC005",     // digit 5 — restricted on Monday (lunes: [5,6])
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.restricted).toBe(true);
    expect(body.rule).toBe("weekday");
    expect(body.last_digit).toBe(5);
  });

  it("handles accented weekday keys in raw_payload", async () => {
    // Scraper stores "miércoles" (accented). Worker should handle both.
    const queries = mockQueries({
      getRotation: async () =>
        makeRotation({
          raw_payload: {
            weekdays: {
              lunes: [5, 6],
              martes: [1, 2],
              miércoles: [3, 4], // accented
              jueves: [7, 8],
              viernes: [9, 0],
            },
            saturday_calendar: {},
            article_title: "Test",
            article_url: "",
          },
        }),
    });
    const url = makeUrl("/v1/restriccion", {
      municipio: "bucaramanga",
      fecha: "2026-06-17", // Wednesday
      placa: "ABC003",
    });
    const resp = await handleRestriccion(url, queries);
    const body = await bodyJson(resp);

    expect(resp.status).toBe(200);
    expect(body.restricted).toBe(true);
    expect(body.last_digit).toBe(3);
  });
});

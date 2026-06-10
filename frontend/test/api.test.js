/**
 * API client tests.
 *
 * Verifies URL construction, fetch integration, and error handling.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// We test the module's functions by importing them directly,
// mocking global fetch.
let apiModule;

beforeEach(async () => {
  // Reset modules so the BASE_URL re-reads from DOM
  vi.resetModules();
  apiModule = await import("../src/api.js");
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("fetchRestriccion", () => {
  it("constructs the correct URL with query params", async () => {
    const mockJson = vi.fn().mockResolvedValue({ restricted: false });
    globalThis.fetch = vi.fn().mockResolvedValue({ json: mockJson });

    await apiModule.fetchRestriccion("bucaramanga", "2026-06-10", "ABC123");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/restriccion?municipio=bucaramanga&fecha=2026-06-10&placa=ABC123")
    );
  });

  it("returns parsed JSON on success", async () => {
    const response = { restricted: true, last_digit: 3 };
    globalThis.fetch = vi.fn().mockResolvedValue({
      json: vi.fn().mockResolvedValue(response),
    });

    const result = await apiModule.fetchRestriccion("bucaramanga", "2026-06-10", "ABC123");
    expect(result).toEqual(response);
  });

  it("returns error JSON on 400", async () => {
    const errorResponse = { error: "bad_plate" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      json: vi.fn().mockResolvedValue(errorResponse),
    });

    const result = await apiModule.fetchRestriccion("bucaramanga", "2026-06-10", "!!!");
    expect(result.error).toBe("bad_plate");
  });
});

describe("fetchSchedule", () => {
  it("constructs the correct URL", async () => {
    const mockJson = vi.fn().mockResolvedValue({ current: null, next: null, message: null });
    globalThis.fetch = vi.fn().mockResolvedValue({ json: mockJson });

    await apiModule.fetchSchedule("floridablanca");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/schedule?municipio=floridablanca")
    );
  });
});

describe("fetchHeroData", () => {
  it("returns calm state when no rotation exists", async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        json: vi.fn().mockResolvedValue({ current: null, next: null, message: "rotation_unknown" }),
      })
      .mockResolvedValueOnce({
        json: vi.fn().mockResolvedValue({ restricted: false, rule: "weekday" }),
      });

    const result = await apiModule.fetchHeroData("bucaramanga", "2026-06-10");
    expect(result.isRestricted).toBe(false);
    expect(result.digits).toBeNull();
  });

  it("returns digits when rotation exists for a weekday", async () => {
    const fecha = "2026-06-10"; // Wednesday
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        json: vi.fn().mockResolvedValue({
          current: {
            raw_payload: {
              weekdays: { "miércoles": [1, 2], "miercoles": [1, 2] },
            },
          },
          next: null,
          message: null,
        }),
      })
      .mockResolvedValueOnce({
        json: vi.fn().mockResolvedValue({ restricted: true, rule: "weekday" }),
      });

    const result = await apiModule.fetchHeroData("bucaramanga", fecha);
    expect(result.isRestricted).toBe(true);
    expect(result.digits).toEqual([1, 2]);
  });

  it("returns calm state when today is festivo", async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        json: vi.fn().mockResolvedValue({
          current: { raw_payload: { weekdays: { "lunes": [5, 6] } } },
          next: null,
          message: null,
        }),
      })
      .mockResolvedValueOnce({
        json: vi.fn().mockResolvedValue({ restricted: false, rule: "festivo" }),
      });

    const result = await apiModule.fetchHeroData("bucaramanga", "2026-06-15"); // Monday
    expect(result.isRestricted).toBe(false);
    expect(result.digits).toBeNull();
  });

  it("returns calm state on network error", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

    const result = await apiModule.fetchHeroData("bucaramanga", "2026-06-10");
    expect(result.isRestricted).toBe(false);
    expect(result.digits).toBeNull();
  });
});

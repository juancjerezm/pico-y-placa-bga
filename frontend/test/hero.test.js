/**
 * Hero component tests.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { renderHero, updateHero, SPANISH_WEEKDAYS, MUNICIPIO_NAMES } from "../src/components/hero.js";

describe("renderHero", () => {
  it("renders the digit for an active restriction day", () => {
    renderHero({
      digits: [5, 6],
      isRestricted: true,
      municipio: "bucaramanga",
      fecha: "2026-06-10",
    });

    const digitEl = document.getElementById("hero-digit");
    expect(digitEl.textContent).toBe("5 - 6");
    expect(digitEl.classList.contains("hero-digit--active")).toBe(true);
    expect(digitEl.classList.contains("hero-digit--calm")).toBe(false);
  });

  it("renders calm state when no digits", () => {
    renderHero({
      digits: null,
      isRestricted: false,
      municipio: "bucaramanga",
      fecha: "2026-06-14", // Sunday
    });

    const digitEl = document.getElementById("hero-digit");
    expect(digitEl.textContent).toBe("—");
    expect(digitEl.classList.contains("hero-digit--calm")).toBe(true);
    expect(digitEl.classList.contains("hero-digit--active")).toBe(false);
  });

  it("renders calm state for empty digits array", () => {
    renderHero({
      digits: [],
      isRestricted: false,
      municipio: "giron",
      fecha: "2026-06-10",
    });

    const digitEl = document.getElementById("hero-digit");
    expect(digitEl.textContent).toBe("—");
  });

  it("shows weekday and municipality in the label", () => {
    // 2026-06-10 is a Wednesday
    renderHero({
      digits: [1, 2],
      isRestricted: true,
      municipio: "floridablanca",
      fecha: "2026-06-10",
    });

    const labelEl = document.getElementById("hero-label");
    expect(labelEl.textContent).toContain("miércoles");
    expect(labelEl.textContent).toContain("Floridablanca");
  });

  it("shows sub-text for active restriction", () => {
    // Use today's date so the "hoy" variant is selected
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, "0");
    const dd = String(today.getDate()).padStart(2, "0");
    const todayStr = `${yyyy}-${mm}-${dd}`;

    renderHero({
      digits: [7, 8],
      isRestricted: true,
      municipio: "bucaramanga",
      fecha: todayStr,
    });

    const subEl = document.getElementById("hero-sub");
    expect(subEl.textContent).toBe("Restricción hoy");
  });
});

describe("SPANISH_WEEKDAYS", () => {
  it("maps Sunday to domingo", () => {
    expect(SPANISH_WEEKDAYS[0]).toBe("domingo");
  });

  it("maps Monday to lunes", () => {
    expect(SPANISH_WEEKDAYS[1]).toBe("lunes");
  });

  it("has 7 entries", () => {
    expect(SPANISH_WEEKDAYS).toHaveLength(7);
  });
});

describe("MUNICIPIO_NAMES", () => {
  it("maps all 4 AMB municipalities", () => {
    expect(MUNICIPIO_NAMES.bucaramanga).toBe("Bucaramanga");
    expect(MUNICIPIO_NAMES.floridablanca).toBe("Floridablanca");
    expect(MUNICIPIO_NAMES.giron).toBe("Girón");
    expect(MUNICIPIO_NAMES.piedecuesta).toBe("Piedecuesta");
  });
});

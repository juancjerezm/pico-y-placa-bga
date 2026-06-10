/**
 * Input component tests — plate validation, live digit extraction, todayISO.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { extractLastDigit, todayISO, initInput, MUNICIPIO_SLUGS } from "../src/components/input.js";

describe("extractLastDigit", () => {
  it("extracts the last digit from a standard plate", () => {
    expect(extractLastDigit("ABC123")).toBe(3);
  });

  it("extracts from motorcycle plate (current format)", () => {
    expect(extractLastDigit("ABC12D")).toBe(2);
  });

  it("extracts from motorcycle plate (older format)", () => {
    expect(extractLastDigit("ABC12")).toBe(2);
  });

  it("handles whitespace (trailer format)", () => {
    expect(extractLastDigit("R 12345")).toBe(5);
  });

  it("handles dash separator", () => {
    expect(extractLastDigit("ABC-123")).toBe(3);
  });

  it("handles middle-dot separator", () => {
    expect(extractLastDigit("ABC·123")).toBe(3);
  });

  it("handles lower-case input", () => {
    expect(extractLastDigit("abc456")).toBe(6);
  });

  it("returns null for plate with no digits", () => {
    expect(extractLastDigit("ABC")).toBeNull();
  });

  it("returns null for empty string", () => {
    expect(extractLastDigit("")).toBeNull();
  });

  it("extracts last digit from diplomatic format", () => {
    expect(extractLastDigit("D AB 123")).toBe(3);
  });

  it("extracts digit from single-digit plate", () => {
    expect(extractLastDigit("A7")).toBe(7);
  });

  it("returns the last digit when multiple digit groups", () => {
    expect(extractLastDigit("T1234AB5")).toBe(5);
  });
});

describe("todayISO", () => {
  it("returns a string matching YYYY-MM-DD format", () => {
    const iso = todayISO();
    expect(iso).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("returns today's date components", () => {
    const now = new Date();
    const iso = todayISO();
    const [yyyy, mm, dd] = iso.split("-").map(Number);
    expect(yyyy).toBe(now.getFullYear());
    expect(mm).toBe(now.getMonth() + 1);
    expect(dd).toBe(now.getDate());
  });
});

describe("initInput", () => {
  beforeEach(() => {
    // Reset DOM to known state
    document.getElementById("plate-input").value = "";
    document.getElementById("live-digit").textContent = "";
    document.getElementById("live-digit").classList.remove("live-digit--visible");
    document.getElementById("municipio-select").value = "bucaramanga";
    document.getElementById("input-hint").textContent = "";
    document.getElementById("input-hint").classList.remove("input-hint--visible");
  });

  it("shows live digit when typing a plate with digits", () => {
    initInput();
    const plateInput = document.getElementById("plate-input");
    const liveDigit = document.getElementById("live-digit");

    plateInput.value = "ABC123";
    plateInput.dispatchEvent(new Event("input"));

    expect(liveDigit.textContent).toBe("3");
    expect(liveDigit.classList.contains("live-digit--visible")).toBe(true);
  });

  it("hides live digit when plate has no numbers", () => {
    initInput();
    const plateInput = document.getElementById("plate-input");
    const liveDigit = document.getElementById("live-digit");

    plateInput.value = "ABC";
    plateInput.dispatchEvent(new Event("input"));

    expect(liveDigit.textContent).toBe("");
    expect(liveDigit.classList.contains("live-digit--visible")).toBe(false);
  });

  it("shows validation hint when submitting empty plate", () => {
    const onSubmit = vi.fn();
    initInput({ onSubmit });
    const btn = document.getElementById("consultar-btn");
    const hint = document.getElementById("input-hint");

    btn.click();

    expect(hint.textContent).toBeTruthy();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows validation hint when plate has no digits", () => {
    const onSubmit = vi.fn();
    initInput({ onSubmit });
    const plateInput = document.getElementById("plate-input");
    const btn = document.getElementById("consultar-btn");
    const hint = document.getElementById("input-hint");

    plateInput.value = "ABC";
    btn.click();

    expect(hint.textContent).toContain("número");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("calls onSubmit with valid plate data", () => {
    const onSubmit = vi.fn();
    initInput({ onSubmit });
    const plateInput = document.getElementById("plate-input");
    const municipioSelect = document.getElementById("municipio-select");
    const dateInput = document.getElementById("date-input");
    const btn = document.getElementById("consultar-btn");

    plateInput.value = "ABC123";
    municipioSelect.value = "floridablanca";
    dateInput.value = "2026-06-15";
    btn.click();

    expect(onSubmit).toHaveBeenCalledWith({
      placa: "ABC123",
      municipio: "floridablanca",
      fecha: "2026-06-15",
    });
  });

  it("trims whitespace from plate input", () => {
    const onSubmit = vi.fn();
    initInput({ onSubmit });
    const plateInput = document.getElementById("plate-input");
    const btn = document.getElementById("consultar-btn");

    plateInput.value = "  ABC123  ";
    btn.click();

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ placa: "ABC123" })
    );
  });

  it("pre-fills fields from opts", () => {
    initInput({
      placa: "XYZ789",
      municipio: "piedecuesta",
      fecha: "2026-07-01",
    });

    expect(document.getElementById("plate-input").value).toBe("XYZ789");
    expect(document.getElementById("municipio-select").value).toBe("piedecuesta");
    expect(document.getElementById("date-input").value).toBe("2026-07-01");
  });

  it("submits on Enter key", () => {
    const onSubmit = vi.fn();
    initInput({ onSubmit });
    const plateInput = document.getElementById("plate-input");

    plateInput.value = "ABC123";
    plateInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));

    expect(onSubmit).toHaveBeenCalled();
  });
});

describe("MUNICIPIO_SLUGS", () => {
  it("contains all 4 AMB municipalities", () => {
    expect(MUNICIPIO_SLUGS).toContain("bucaramanga");
    expect(MUNICIPIO_SLUGS).toContain("floridablanca");
    expect(MUNICIPIO_SLUGS).toContain("giron");
    expect(MUNICIPIO_SLUGS).toContain("piedecuesta");
  });
});

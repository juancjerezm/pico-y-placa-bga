/**
 * Storage tests — localStorage persistence.
 */
import { describe, it, expect, beforeEach } from "vitest";
import {
  saveLastQuery,
  loadLastQuery,
  saveMunicipioPreference,
  loadMunicipioPreference,
  clearStorage,
} from "../src/storage.js";

describe("saveLastQuery / loadLastQuery", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("saves and loads a query round-trip", () => {
    saveLastQuery({ placa: "ABC123", municipio: "bucaramanga", fecha: "2026-06-10" });
    const loaded = loadLastQuery();
    expect(loaded.placa).toBe("ABC123");
    expect(loaded.municipio).toBe("bucaramanga");
    expect(loaded.fecha).toBe("2026-06-10");
  });

  it("returns null when no query is saved", () => {
    expect(loadLastQuery()).toBeNull();
  });

  it("preserves all fields including result data", () => {
    saveLastQuery({
      placa: "XYZ789",
      municipio: "giron",
      fecha: "2026-06-12",
      restricted: true,
      lastDigit: 9,
      rule: "weekday",
      source: "rotation",
    });
    const loaded = loadLastQuery();
    expect(loaded.restricted).toBe(true);
    expect(loaded.lastDigit).toBe(9);
    expect(loaded.rule).toBe("weekday");
    expect(loaded.source).toBe("rotation");
  });

  it("overwrites previous query on second save", () => {
    saveLastQuery({ placa: "AAA111", municipio: "bucaramanga", fecha: "2026-01-01" });
    saveLastQuery({ placa: "BBB222", municipio: "floridablanca", fecha: "2026-06-15" });
    const loaded = loadLastQuery();
    expect(loaded.placa).toBe("BBB222");
  });
});

describe("saveMunicipioPreference / loadMunicipioPreference", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("saves and loads municipio preference", () => {
    saveMunicipioPreference("piedecuesta");
    expect(loadMunicipioPreference()).toBe("piedecuesta");
  });

  it("returns null when no preference saved", () => {
    expect(loadMunicipioPreference()).toBeNull();
  });

  it("updates preference without losing other fields", () => {
    localStorage.setItem("pyp_prefs", JSON.stringify({ municipio: "giron", theme: "dark" }));
    saveMunicipioPreference("bucaramanga");
    const prefs = JSON.parse(localStorage.getItem("pyp_prefs"));
    expect(prefs.municipio).toBe("bucaramanga");
    expect(prefs.theme).toBe("dark");
  });
});

describe("clearStorage", () => {
  it("removes all stored data", () => {
    saveLastQuery({ placa: "ABC", municipio: "bucaramanga", fecha: "2026-01-01" });
    saveMunicipioPreference("floridablanca");
    clearStorage();
    expect(loadLastQuery()).toBeNull();
    expect(loadMunicipioPreference()).toBeNull();
  });
});

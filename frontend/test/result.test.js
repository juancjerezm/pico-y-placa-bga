/**
 * Result component tests — restriction status rendering and error display.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { showResult, hideResult } from "../src/components/result.js";

describe("showResult", () => {
  it("renders restricted state with red status", () => {
    showResult({
      restricted: true,
      rule: "weekday",
      source: "rotation",
      lastDigit: 5,
    });

    const section = document.getElementById("result");
    const statusEl = document.getElementById("result-status");
    const messageEl = document.getElementById("result-message");

    expect(section.classList.contains("result--hidden")).toBe(false);
    expect(statusEl.textContent).toBe("Restringido");
    expect(statusEl.classList.contains("result-status--restricted")).toBe(true);
    expect(messageEl.textContent).toContain("no podés circular");
  });

  it("renders unrestricted state with green status", () => {
    showResult({
      restricted: false,
      rule: "weekday",
      source: "rotation",
      lastDigit: 3,
    });

    const statusEl = document.getElementById("result-status");
    expect(statusEl.textContent).toBe("Sin restricción");
    expect(statusEl.classList.contains("result-status--unrestricted")).toBe(true);
  });

  it("shows festivo-specific message", () => {
    showResult({
      restricted: false,
      rule: "festivo",
      source: "rotation",
    });

    const messageEl = document.getElementById("result-message");
    expect(messageEl.textContent).toContain("festivo");
  });

  it("renders rotation_unknown error", () => {
    showResult({ error: "rotation_unknown" });

    const statusEl = document.getElementById("result-status");
    const messageEl = document.getElementById("result-message");

    expect(statusEl.classList.contains("result-status--error")).toBe(true);
    expect(messageEl.textContent).toContain("No tenemos datos");
  });

  it("renders bad_plate error with friendly message", () => {
    showResult({ error: "bad_plate" });

    const messageEl = document.getElementById("result-message");
    expect(messageEl.textContent).toContain("no es válida");
  });

  it("renders network error with friendly message", () => {
    showResult({ error: "network" });

    const messageEl = document.getElementById("result-message");
    expect(messageEl.textContent).toContain("conexión");
  });

  it("does NOT contain 'formato_detectado' in the DOM", () => {
    showResult({
      restricted: true,
      rule: "weekday",
      source: "rotation",
    });

    const text = document.body.textContent;
    expect(text).not.toContain("formato_detectado");
    expect(text).not.toContain("oficial");
    expect(text).not.toContain("diplomatico");
    expect(text).not.toContain("fuerza_publica");
  });
});

describe("hideResult", () => {
  it("adds result--hidden class after animation", async () => {
    showResult({ restricted: false, rule: "weekday", source: "rotation" });
    await hideResult();

    const section = document.getElementById("result");
    expect(section.classList.contains("result--hidden")).toBe(true);
  });
});

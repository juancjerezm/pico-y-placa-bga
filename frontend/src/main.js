/**
 * Pico y Placa Bucaramanga — Frontend entry point.
 *
 * Orchestrates the three components (Hero, Input, Result) and manages
 * state flow: localStorage re-hydration → Hero fetch → user query → Result display.
 */
import { fetchHeroData, fetchRestriccion } from "./api.js";
import {
  saveLastQuery,
  loadLastQuery,
  saveMunicipioPreference,
  loadMunicipioPreference,
} from "./storage.js";
import { renderHero, updateHero } from "./components/hero.js";
import { initInput, todayISO } from "./components/input.js";
import { showResult, hideResult } from "./components/result.js";

/** Current app state. */
const state = {
  municipio: "bucaramanga",
  fecha: todayISO(),
  lastResult: null,
};

/**
 * Bootstrap the application.
 */
async function bootstrap() {
  // 1. Re-hydrate from localStorage
  const saved = loadLastQuery();
  const savedMunicipio = loadMunicipioPreference();

  if (saved) {
    state.municipio = saved.municipio || "bucaramanga";
    state.fecha = saved.fecha || todayISO();
  } else if (savedMunicipio) {
    state.municipio = savedMunicipio;
  }

  // 2. Initialize input with re-hydrated values
  initInput({
    placa: saved?.placa ?? "",
    municipio: state.municipio,
    fecha: state.fecha,
    onSubmit: handleSubmit,
  });

  // 3. Fetch hero data
  const heroData = await fetchHeroData(state.municipio, state.fecha);
  renderHero({ ...heroData, municipio: state.municipio, fecha: state.fecha });

  // 4. If there was a saved query, re-run it
  if (saved && saved.placa) {
    handleSubmit(
      { placa: saved.placa, municipio: state.municipio, fecha: state.fecha },
      { silent: true }
    );
  }

  // 5. Wire municipality change → hero re-fetch
  const municipioSelect = document.getElementById("municipio-select");
  if (municipioSelect) {
    municipioSelect.addEventListener("change", () => {
      const newMunicipio = municipioSelect.value;
      if (newMunicipio === state.municipio) return;
      state.municipio = newMunicipio;
      saveMunicipioPreference(newMunicipio);
      onMunicipioChange(newMunicipio);
    });
  }
}

/**
 * Handle form submission.
 * @param {{placa: string, municipio: string, fecha: string}} data
 * @param {{silent?: boolean}} [opts]
 */
async function handleSubmit(data, opts = {}) {
  state.municipio = data.municipio;
  state.fecha = data.fecha;

  // Hide any previous result while loading
  if (!opts.silent) {
    hideResult();
  }

  try {
    const result = await fetchRestriccion(data.municipio, data.fecha, data.placa);

    // Persist query
    saveLastQuery({
      placa: data.placa,
      municipio: data.municipio,
      fecha: data.fecha,
      restricted: result.restricted,
      lastDigit: result.last_digit,
      rule: result.rule,
      source: result.source,
    });

    saveMunicipioPreference(data.municipio);
    state.lastResult = result;
    showResult(result);
  } catch {
    // Network error — show friendly message
    showResult({ error: "network" });
  }
}

/**
 * Handle municipality selector change — re-fetch hero.
 * @param {string} municipio
 */
async function onMunicipioChange(municipio) {
  const heroData = await fetchHeroData(municipio, state.fecha);
  updateHero({ ...heroData, municipio, fecha: state.fecha });

  // If there's a currently visible result, re-query with new municipio
  if (state.lastResult) {
    const plateInput = document.getElementById("plate-input");
    const placa = plateInput?.value?.trim();
    if (placa) {
      handleSubmit({ placa, municipio, fecha: state.fecha });
    }
  }
}

// Boot when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrap);
} else {
  bootstrap();
}

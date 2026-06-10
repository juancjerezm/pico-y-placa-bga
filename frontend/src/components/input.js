/**
 * Input component — plate entry field with live digit reveal.
 *
 * Features:
 *   - Plate text input with live last-digit extraction (client-side)
 *   - Municipality selector (custom-styled dropdown)
 *   - Date input (defaults to today)
 *   - Inline validation messages
 *   - "Consultar" submit button
 */
import { animate } from "motion";

const MUNICIPIO_SLUGS = [
  "bucaramanga",
  "floridablanca",
  "giron",
  "piedecuesta",
];

/**
 * Extract the last digit from a plate string (client-side, simplified).
 * Mirrors the server-side right-to-left scan.
 * @param {string} raw
 * @returns {number|null}
 */
export function extractLastDigit(raw) {
  // Normalize: uppercase, strip whitespace/dots/dashes/middle-dots
  const normalized = raw
    .toUpperCase()
    .replace(/[\s.\-·]/g, "");

  // Scan right to left for a digit
  for (let i = normalized.length - 1; i >= 0; i--) {
    const ch = normalized[i];
    if (ch >= "0" && ch <= "9") {
      return parseInt(ch, 10);
    }
  }
  return null;
}

/**
 * Initialize the input component.
 * @param {Object} opts
 * @param {string} [opts.municipio] - pre-selected municipality
 * @param {string} [opts.fecha] - pre-filled date (YYYY-MM-DD)
 * @param {string} [opts.placa] - pre-filled plate
 * @param {(data: {placa: string, municipio: string, fecha: string}) => void} opts.onSubmit
 */
export function initInput(opts = {}) {
  const plateInput = document.getElementById("plate-input");
  const liveDigit = document.getElementById("live-digit");
  const municipioSelect = document.getElementById("municipio-select");
  const dateInput = document.getElementById("date-input");
  const hintEl = document.getElementById("input-hint");
  const btn = document.getElementById("consultar-btn");

  if (!plateInput || !municipioSelect || !dateInput || !btn) return;

  // Pre-fill from opts or localStorage
  if (opts.placa) plateInput.value = opts.placa;
  if (opts.municipio) municipioSelect.value = opts.municipio;
  if (opts.fecha) dateInput.value = opts.fecha;
  else dateInput.value = todayISO();

  // Live digit reveal on input
  plateInput.addEventListener("input", () => {
    const digit = extractLastDigit(plateInput.value);
    if (digit !== null) {
      liveDigit.textContent = String(digit);
      liveDigit.classList.add("live-digit--visible");
      // Micro bounce on digit change
      animate(liveDigit, { scale: [1.3, 1] }, { duration: 0.25, easing: [0.34, 1.56, 0.64, 1] });
    } else {
      liveDigit.textContent = "";
      liveDigit.classList.remove("live-digit--visible");
    }
    // Clear hint when user types
    if (hintEl) hintEl.textContent = "";
  });

  // Focus glow animation
  plateInput.addEventListener("focus", () => {
    animate(
      plateInput.parentElement,
      { boxShadow: ["0 0 0 0 rgba(245, 158, 11, 0)", "0 0 0 2px rgba(245, 158, 11, 0.4)"] },
      { duration: 0.25 }
    );
  });

  plateInput.addEventListener("blur", () => {
    animate(
      plateInput.parentElement,
      { boxShadow: ["0 0 0 2px rgba(245, 158, 11, 0.4)", "0 0 0 0 rgba(245, 158, 11, 0)"] },
      { duration: 0.25 }
    );
  });

  // Validate plate on submit
  btn.addEventListener("click", () => {
    const placa = plateInput.value.trim();
    const municipio = municipioSelect.value;
    const fecha = dateInput.value;

    // Client-side validation
    if (!placa) {
      showHint(hintEl, "Ingresá una placa");
      animate(hintEl, { x: [-4, 4, -4, 4, 0] }, { duration: 0.3 });
      return;
    }

    const digit = extractLastDigit(placa);
    if (digit === null) {
      showHint(hintEl, "La placa debe contener al menos un número");
      animate(hintEl, { x: [-4, 4, -4, 4, 0] }, { duration: 0.3 });
      return;
    }

    if (placa.length < 3) {
      showHint(hintEl, "La placa parece demasiado corta");
      return;
    }

    // Clear hint on valid input
    if (hintEl) hintEl.textContent = "";

    if (opts.onSubmit) {
      opts.onSubmit({ placa, municipio, fecha });
    }
  });

  // Allow Enter key to submit
  plateInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") btn.click();
  });
}

/**
 * Show an inline validation hint with animation.
 * @param {HTMLElement} el
 * @param {string} msg
 */
function showHint(el, msg) {
  if (!el) return;
  el.textContent = msg;
  el.classList.add("input-hint--visible");
}

/**
 * Return today's date as YYYY-MM-DD in local timezone.
 * @returns {string}
 */
export function todayISO() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export { MUNICIPIO_SLUGS };

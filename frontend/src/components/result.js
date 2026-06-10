/**
 * Result component — restriction status display.
 *
 * Animates in from bottom with spring bounce. Shows:
 *   - GREEN (puede circular) for unrestricted
 *   - RED (no puede circular) for restricted
 *   - Friendly error messages for API failures
 */
import { animate } from "motion";

/**
 * @typedef {Object} ResultData
 * @property {boolean} restricted
 * @property {string} [rule] - "weekday"|"saturday"|"festivo"
 * @property {string} [source] - "rotation"|"override"
 * @property {number} [lastDigit]
 * @property {string} [placa]
 * @property {string} [municipio]
 */

/**
 * @typedef {Object} ResultError
 * @property {string} error - "rotation_unknown"|"bad_plate"|"bad_date"|"bad_municipio"|"network"
 * @property {string} [municipio]
 * @property {string} [requested_date]
 */

/**
 * Show the result panel with animated state transition.
 * @param {ResultData|ResultError} data
 */
export function showResult(data) {
  const section = document.getElementById("result");
  const statusEl = document.getElementById("result-status");
  const messageEl = document.getElementById("result-message");

  if (!section || !statusEl || !messageEl) return;

  // Handle error responses
  if (data && data.error) {
    renderError(data, statusEl, messageEl);
  } else {
    renderRestriction(data, statusEl, messageEl);
  }

  // Reveal animation — slide up with spring bounce
  section.classList.remove("result--hidden");
  animate(
    section,
    {
      y: [40, 0],
      scale: [0.95, 1],
      opacity: [0, 1],
    },
    {
      duration: 0.55,
      easing: { type: "spring", stiffness: 100, damping: 15 },
    }
  );
}

/**
 * Hide the result panel.
 */
export function hideResult() {
  const section = document.getElementById("result");
  if (!section) return;

  animate(
    section,
    { opacity: [1, 0], y: [0, 20], scale: [1, 0.95] },
    { duration: 0.2 }
  ).finished.then(() => {
    section.classList.add("result--hidden");
  });
}

/**
 * Render restriction status.
 */
function renderRestriction(data, statusEl, messageEl) {
  statusEl.className = "result-status";
  messageEl.className = "result-message";

  if (data.restricted) {
    statusEl.classList.add("result-status--restricted");
    statusEl.textContent = "Restringido";
    messageEl.textContent = "No podés circular hoy con este vehículo";
    messageEl.classList.add("result-message--restricted");
  } else {
    statusEl.classList.add("result-status--unrestricted");
    statusEl.textContent = "Sin restricción";
    messageEl.textContent = "Podés circular libremente hoy";

    if (data.rule === "festivo") {
      messageEl.textContent = "Hoy es festivo — podés circular libremente";
    }

    messageEl.classList.add("result-message--unrestricted");
  }

  // Animate status badge
  animate(
    statusEl,
    { scale: [0, 1], opacity: [0, 1] },
    { duration: 0.35, delay: 0.1, easing: [0.34, 1.56, 0.64, 1] }
  );

  // Animate message text
  animate(
    messageEl,
    { opacity: [0, 1], y: [10, 0] },
    { duration: 0.35, delay: 0.25, easing: "ease-out" }
  );
}

/**
 * Render error state.
 */
function renderError(data, statusEl, messageEl) {
  statusEl.className = "result-status result-status--error";
  statusEl.textContent = "Sin datos";

  messageEl.className = "result-message";

  switch (data.error) {
    case "rotation_unknown":
      messageEl.textContent =
        "No tenemos datos de la rotación vigente. Volvé a intentar más tarde.";
      break;
    case "bad_plate":
      messageEl.textContent = "La placa ingresada no es válida.";
      break;
    case "bad_date":
      messageEl.textContent = "La fecha ingresada no es válida.";
      break;
    case "bad_municipio":
      messageEl.textContent = "El municipio seleccionado no es válido.";
      break;
    default:
      messageEl.textContent =
        "No se pudo conectar con el servidor. Verificá tu conexión.";
      break;
  }

  // Animate error state
  animate(
    statusEl,
    { scale: [0, 1], opacity: [0, 1] },
    { duration: 0.35, delay: 0.1, easing: [0.34, 1.56, 0.64, 1] }
  );

  animate(
    messageEl,
    { opacity: [0, 1], y: [10, 0] },
    { duration: 0.35, delay: 0.25, easing: "ease-out" }
  );
}

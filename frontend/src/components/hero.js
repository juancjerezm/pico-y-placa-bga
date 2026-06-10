/**
 * Hero component — today's restricted digit(s) as a typographic centerpiece.
 *
 * Uses Motion One for airport-style flip animation on digit changes.
 * Shows a calm "no restriction" state on Sundays, festivos, or missing data.
 */
import { animate, stagger } from "motion";

const SPANISH_WEEKDAYS = [
  "domingo",
  "lunes",
  "martes",
  "miércoles",
  "jueves",
  "viernes",
  "sábado",
];

const MUNICIPIO_NAMES = {
  bucaramanga: "Bucaramanga",
  floridablanca: "Floridablanca",
  giron: "Girón",
  piedecuesta: "Piedecuesta",
};

/**
 * Render the hero with current data.
 * @param {{digits: number[]|null, isRestricted: boolean, municipio: string, fecha: string}} data
 */
export function renderHero(data) {
  const container = document.getElementById("hero-digit-container");
  const digitEl = document.getElementById("hero-digit");
  const labelEl = document.getElementById("hero-label");
  const subEl = document.getElementById("hero-sub");

  if (!container || !digitEl) return;

  const date = new Date(data.fecha + "T12:00:00");
  const weekday = SPANISH_WEEKDAYS[date.getDay()];
  const municipio = MUNICIPIO_NAMES[data.municipio] ?? data.municipio;

  // Check if the displayed date is today
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const isToday = date.toDateString() === now.toDateString();

  labelEl.textContent = `${weekday} · ${municipio}`;

  if (!data.digits || data.digits.length === 0) {
    // Calm "no restriction" state
    digitEl.textContent = "—";
    digitEl.classList.remove("hero-digit--active");
    digitEl.classList.add("hero-digit--calm");
    subEl.textContent = isToday ? "Sin restricción hoy" : "Sin restricción";

    animate(digitEl, { opacity: [0, 1], scale: [0.9, 1] }, { duration: 0.5 });
    return;
  }

  // Show digits (e.g., "5 - 6")
  const digitText = data.digits.join(" - ");
  digitEl.textContent = digitText;
  digitEl.classList.remove("hero-digit--calm");
  digitEl.classList.add("hero-digit--active");
  subEl.textContent = isToday ? "Restricción hoy" : "Restricción";

  // Flip animation — rotateX for airport-style flip
  animate(
    digitEl,
    { rotateX: [90, 0], opacity: [0, 1] },
    {
      duration: 0.55,
      easing: [0.34, 1.56, 0.64, 1], // overshoot for bounce feel
    }
  );
}

/**
 * Update the hero with new data (municipio change).
 * @param {{digits: number[]|null, isRestricted: boolean, municipio: string, fecha: string}} data
 */
export function updateHero(data) {
  const digitEl = document.getElementById("hero-digit");
  if (!digitEl) return;

  const currentText = digitEl.textContent;

  // Crossfade out
  animate(
    digitEl,
    { opacity: [1, 0], scale: [1, 0.95] },
    { duration: 0.2 }
  ).finished.then(() => {
    renderHero(data);
  });
}

export { SPANISH_WEEKDAYS, MUNICIPIO_NAMES };

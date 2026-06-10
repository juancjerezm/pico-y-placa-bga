/**
 * Hero component — today's restricted digit(s) as a typographic centerpiece.
 *
 * Uses Motion One for airport-style flip animation on digit changes.
 * Shows a calm "no restriction" state on Sundays, festivos, or missing data.
 * Live countdown timer for restriction hours.
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

/** Restriction hours per day type. */
const RESTRICTION_HOURS = {
  weekday: { start: 6, end: 20 },   // 6 AM - 8 PM
  saturday: { start: 9, end: 13 },  // 9 AM - 1 PM
};

let countdownInterval = null;

/**
 * Start the live countdown timer (updates every second for smooth progress).
 */
export function startCountdown() {
  if (countdownInterval) clearInterval(countdownInterval);
  updateCountdown();
  countdownInterval = setInterval(updateCountdown, 1000);
}

function updateCountdown() {
  const timerEl = document.getElementById("hero-timer");
  const progressEl = document.getElementById("hero-progress");
  const barEl = document.getElementById("hero-progress-bar");
  if (!timerEl) return;

  const now = new Date();
  const day = now.getDay();

  // No restriction on Sundays
  if (day === 0) {
    timerEl.textContent = "";
    timerEl.style.display = "none";
    if (progressEl) progressEl.style.display = "none";
    return;
  }

  const hours = day === 6 ? RESTRICTION_HOURS.saturday : RESTRICTION_HOURS.weekday;
  const startMins = hours.start * 60;
  const endMins = hours.end * 60;
  const totalMins = endMins - startMins;
  const currentMins = now.getHours() * 60 + now.getMinutes();
  const currentSecs = currentMins * 60 + now.getSeconds();

  timerEl.style.display = "block";
  if (progressEl) progressEl.style.display = "block";

  if (currentMins < hours.start * 60) {
    // Before restriction — countdown to start
    const secsLeft = startMins * 60 - currentSecs;
    const h = Math.floor(secsLeft / 3600);
    const m = Math.floor((secsLeft % 3600) / 60);
    const s = secsLeft % 60;
    timerEl.textContent = `Empieza en ${h}h ${m}m ${s.toString().padStart(2, "0")}s`;
    timerEl.className = "hero-timer hero-timer--upcoming";

    // Progress: how close to start (reverse)
    const totalWaitMins = startMins;
    const elapsedWait = currentMins;
    const pct = Math.min(100, Math.round((elapsedWait / totalWaitMins) * 100));
    if (barEl) {
      barEl.style.width = `${pct}%`;
      barEl.className = "hero-progress-bar hero-progress-bar--active";
    }
  } else if (currentMins < hours.end * 60) {
    // During restriction
    const secsLeft = endMins * 60 - currentSecs;
    const h = Math.floor(secsLeft / 3600);
    const m = Math.floor((secsLeft % 3600) / 60);
    const s = secsLeft % 60;
    const endLabel = `${hours.end}:00`;
    timerEl.textContent = `Faltan ${h}h ${m}m ${s.toString().padStart(2, "0")}s (hasta las ${endLabel})`;
    timerEl.className = "hero-timer hero-timer--active";

    // Progress: how much of restriction has elapsed
    const elapsedRestriction = currentMins - startMins;
    const pct = Math.round((elapsedRestriction / totalMins) * 100);
    if (barEl) {
      barEl.style.width = `${pct}%`;
      barEl.className = "hero-progress-bar hero-progress-bar--active";
    }
  } else {
    // Restriction ended
    timerEl.textContent = "Terminó por hoy";
    timerEl.className = "hero-timer hero-timer--ended";

    if (barEl) {
      barEl.style.width = "100%";
      barEl.className = "hero-progress-bar hero-progress-bar--ended";
    }
  }
}

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

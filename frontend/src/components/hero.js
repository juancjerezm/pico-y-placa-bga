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
let isActive = true;

/**
 * Red → Orange → Amber → Yellow → Lime → Green (6 stops).
 * Cada color cubre ~16.6% del progreso total.
 */
const COLOR_STOPS = [
  [239, 68, 68],   // 0%   — red    #ef4444
  [249, 115, 22],  // 17%  — orange #f97316
  [245, 158, 11],  // 33%  — amber  #f59e0b
  [234, 179, 8],   // 50%  — yellow #eab308
  [228, 210, 25],  // 67%  — lima amarillito
  [242, 255, 0],   // 83%  — amarillo neón #F2FF00
  [34, 197, 94],   // 100% — verde #22c55e
];

/**
 * Interpolate between two RGB colors.
 */
function lerpColor(c1, c2, t) {
  const r = Math.round(c1[0] + (c2[0] - c1[0]) * t);
  const g = Math.round(c1[1] + (c2[1] - c1[1]) * t);
  const b = Math.round(c1[2] + (c2[2] - c1[2]) * t);
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

/**
 * 6-color rainbow gradient across the restriction window.
 */
function progressColor(pct) {
  const t = Math.min(pct / 100, 1);
  const segments = COLOR_STOPS.length - 1; // 6 segments
  const seg = Math.min(Math.floor(t * segments), segments - 1);
  const local = (t * segments) - seg;
  return lerpColor(COLOR_STOPS[seg], COLOR_STOPS[seg + 1], local);
}

/**
 * Apply neon glow and color to the progress bar.
 */
function setBarGlow(barEl, pct) {
  const color = progressColor(pct);
  barEl.style.background = color;
  barEl.style.boxShadow = `0 0 12px ${color}99, 0 0 28px ${color}44`;
}

/**
 * Stop the countdown timer and hide progress elements.
 */
export function stopCountdown() {
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }
  const timerEl = document.getElementById("hero-timer");
  const progressEl = document.getElementById("hero-progress");
  if (timerEl) {
    timerEl.style.display = "none";
    timerEl.textContent = "";
  }
  if (progressEl) progressEl.style.display = "none";
}

/**
 * Start the live countdown timer (updates every second for smooth progress).
 */
export function startCountdown() {
  stopCountdown();
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

  // No restriction on Sundays or festivos / non-active days
  if (day === 0 || !isActive) {
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
    timerEl.style.color = "";
    timerEl.style.textShadow = "";

    // Progress: how close to start (reverse)
    const totalWaitMins = startMins;
    const elapsedWait = currentMins;
    const pct = Math.min(100, Math.round((elapsedWait / totalWaitMins) * 100));
    if (barEl) {
      barEl.style.width = `${pct}%`;
      barEl.style.background = "#f59e0b";
      barEl.style.boxShadow = "0 0 10px #f59e0b66, 0 0 24px #f59e0b33";
      barEl.className = "hero-progress-bar hero-progress-bar--gradient";
    }
  } else if (currentMins < hours.end * 60) {
    // During restriction
    const secsLeft = endMins * 60 - currentSecs;
    const h = Math.floor(secsLeft / 3600);
    const m = Math.floor((secsLeft % 3600) / 60);
    const s = secsLeft % 60;
    const endLabel = `${hours.end}:00`;
    timerEl.textContent = `Faltan ${h}h ${m}m ${s.toString().padStart(2, "0")}s (hasta las ${endLabel})`;

    // Progress: how much of restriction has elapsed
    const elapsedRestriction = currentMins - startMins;
    const pct = Math.round((elapsedRestriction / totalMins) * 100);

    // Dynamic color: 6-stop rainbow
    const color = progressColor(pct);
    timerEl.style.color = color;
    timerEl.style.textShadow = `0 0 12px ${color}66`;
    timerEl.className = "hero-timer hero-timer--gradient";

    if (barEl) {
      barEl.style.width = `${pct}%`;
      setBarGlow(barEl, pct);
      barEl.className = "hero-progress-bar hero-progress-bar--gradient";
    }
  } else {
    // Restriction ended
    timerEl.textContent = "Terminó por hoy";
    timerEl.className = "hero-timer hero-timer--ended";
    timerEl.style.color = "";
    timerEl.style.textShadow = "";

    if (barEl) {
      barEl.style.width = "100%";
      barEl.style.background = "#22c55e";
      barEl.style.boxShadow = "0 0 10px #22c55e66, 0 0 24px #22c55e33";
      barEl.className = "hero-progress-bar hero-progress-bar--gradient";
    }
  }
}

/**
 * Render the hero with current data.
 *
 * Text is set INSTANTLY (no opacity fade). The rotateX flip animation
 * is purely decorative — the number is visible from frame zero.
 *
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

  // Always clear the loading placeholder class
  digitEl.classList.remove("hero-digit--loading");

  if (!data.digits || data.digits.length === 0) {
    // Calm "no restriction" state — text instant, subtle scale-in
    isActive = false;
    stopCountdown();
    digitEl.textContent = "—";
    digitEl.classList.remove("hero-digit--active");
    digitEl.classList.add("hero-digit--calm");
    subEl.textContent = isToday ? "Sin restricción hoy" : "Sin restricción";

    animate(digitEl, { scale: [0.92, 1] }, { duration: 0.4, easing: "ease-out" });
    return;
  }

  // Show digits instantly (e.g., "5 - 6")
  isActive = true;
  const digitText = data.digits.join(" - ");
  digitEl.textContent = digitText;
  digitEl.classList.remove("hero-digit--calm");
  digitEl.classList.add("hero-digit--active");
  subEl.textContent = isToday ? "Restricción hoy" : "Restricción";

  if (isToday) startCountdown();

  // Flip animation — decorative only, text is already visible
  animate(
    digitEl,
    { rotateX: [90, 0] },
    {
      duration: 0.45,
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

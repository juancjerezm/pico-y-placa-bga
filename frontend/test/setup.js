/**
 * Test setup — jsdom DOM environment.
 *
 * Mocks Motion One's `animate()` to avoid animation failures in jsdom
 * (no Web Animations API or requestAnimationFrame).
 */
import { beforeAll, afterEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mock Motion One — must be at top level (hoisted by vitest)
// ---------------------------------------------------------------------------
vi.mock("motion", () => ({
  animate: vi.fn(() => ({
    finished: Promise.resolve(),
  })),
  stagger: vi.fn((delay) => delay ?? 0),
}));

// ---------------------------------------------------------------------------
// DOM scaffolding — minimal structure matching index.html
// ---------------------------------------------------------------------------
beforeAll(() => {
  document.body.innerHTML = `
    <main id="app">
      <section id="hero" class="hero">
        <span class="hero-label" id="hero-label">Cargando…</span>
        <div class="hero-digit-container" id="hero-digit-container">
          <span class="hero-digit" id="hero-digit" aria-live="polite"></span>
        </div>
        <span class="hero-sub" id="hero-sub"></span>
      </section>
      <section id="input-section" class="input-section">
        <div class="input-group">
          <label for="plate-input" class="input-label">Placa</label>
          <div class="plate-input-wrapper">
            <input type="text" id="plate-input" class="plate-input" maxlength="10" placeholder="ABC123" />
            <span class="live-digit" id="live-digit" aria-live="polite"></span>
          </div>
          <span class="input-hint" id="input-hint"></span>
        </div>
        <div class="input-group">
          <label for="municipio-select" class="input-label">Municipio</label>
          <div class="custom-select-wrapper">
            <select id="municipio-select" class="custom-select">
              <option value="bucaramanga">Bucaramanga</option>
              <option value="floridablanca">Floridablanca</option>
              <option value="giron">Girón</option>
              <option value="piedecuesta">Piedecuesta</option>
            </select>
          </div>
        </div>
        <div class="input-group">
          <label for="date-input" class="input-label">Fecha</label>
          <input type="date" id="date-input" class="date-input" />
        </div>
        <button type="button" id="consultar-btn" class="btn-consultar">Consultar</button>
      </section>
      <section id="result" class="result result--hidden" aria-live="polite">
        <div class="result-inner">
          <div class="result-status" id="result-status"></div>
          <p class="result-message" id="result-message"></p>
        </div>
      </section>
    </main>
    <script data-api-url="http://localhost:8787" type="module"></script>
  `;
});

afterEach(() => {
  localStorage.clear();
});

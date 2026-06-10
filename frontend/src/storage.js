/**
 * localStorage persistence helpers.
 *
 * Keys:
 *   pyp_last_query  → { placa, municipio, fecha, restricted, lastDigit, rule, source }
 *   pyp_prefs       → { municipio }
 */

const QUERY_KEY = "pyp_last_query";
const PREFS_KEY = "pyp_prefs";

/**
 * @typedef {Object} SavedQuery
 * @property {string} placa
 * @property {string} municipio
 * @property {string} fecha
 * @property {boolean} [restricted]
 * @property {number} [lastDigit]
 * @property {string} [rule]
 * @property {string} [source]
 */

/**
 * Save the last query result to localStorage.
 * @param {SavedQuery} query
 */
export function saveLastQuery(query) {
  try {
    localStorage.setItem(QUERY_KEY, JSON.stringify(query));
  } catch {
    // localStorage full or unavailable — silently ignore
  }
}

/**
 * Load the last query from localStorage.
 * @returns {SavedQuery|null}
 */
export function loadLastQuery() {
  try {
    const raw = localStorage.getItem(QUERY_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Save user preferences (municipio).
 * @param {string} municipio
 */
export function saveMunicipioPreference(municipio) {
  try {
    const prefs = JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}");
    prefs.municipio = municipio;
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {
    // silently ignore
  }
}

/**
 * Load user municipio preference.
 * @returns {string|null}
 */
export function loadMunicipioPreference() {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) return null;
    const prefs = JSON.parse(raw);
    return prefs.municipio ?? null;
  } catch {
    return null;
  }
}

/**
 * Clear all stored data.
 */
export function clearStorage() {
  try {
    localStorage.removeItem(QUERY_KEY);
    localStorage.removeItem(PREFS_KEY);
  } catch {
    // silently ignore
  }
}

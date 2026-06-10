/**
 * Plate parser — TypeScript port of python/plate_parser/parser.py.
 *
 * Pure functions, no I/O. Mirrors the Python implementation exactly
 * to keep the validation contract consistent server-side.
 */

// ---------------------------------------------------------------------------
// Output types
// ---------------------------------------------------------------------------

export interface ParseResult {
  lastDigit: number;
  formatoDetectado: string;
  placaNormalized: string;
}

export class PlateValidationError extends Error {
  errorType: string;

  constructor(errorType: string) {
    super(`Plate validation error: ${errorType}`);
    this.errorType = errorType;
    this.name = "PlateValidationError";
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function parsePlaca(raw: string): ParseResult {
  // Normalization (REQ-PP-001)
  const normalized = normalize(raw);

  if (!normalized) {
    throw new PlateValidationError("empty");
  }
  if (normalized.length > 32) {
    throw new PlateValidationError("too_long");
  }

  // Last-digit extraction (REQ-PP-002)
  const lastDigit = extractLastDigit(normalized);
  if (lastDigit === null) {
    throw new PlateValidationError("no_digit");
  }

  // Formato classification (REQ-PP-003)
  const classifiedForm = classifyForm(raw);
  const formato = classify(classifiedForm, normalized);

  return { lastDigit, formatoDetectado: formato, placaNormalized: normalized };
}

// ---------------------------------------------------------------------------
// Normalization (REQ-PP-001)
// ---------------------------------------------------------------------------

export function normalize(s: string): string {
  let result = s.toUpperCase();
  // Remove separators: dot, dash, middle-dot
  result = result.replace(/[.\-·]/g, "");
  // Collapse whitespace runs, then strip
  result = result.replace(/\s+/g, " ").trim();
  // Remove all spaces for compact form
  result = result.replace(/ /g, "");
  return result;
}

// ---------------------------------------------------------------------------
// Classify form (keeps dashes for rule 4 — fuerza_publica)
// ---------------------------------------------------------------------------

export function classifyForm(s: string): string {
  let result = s.toUpperCase();
  // Remove dots and middle-dots, but KEEP dashes
  result = result.replace(/[.·]/g, "");
  // Collapse whitespace, strip
  result = result.replace(/\s+/g, " ").trim();
  return result;
}

// ---------------------------------------------------------------------------
// Last-digit extraction (REQ-PP-002)
// ---------------------------------------------------------------------------

export function extractLastDigit(s: string): number | null {
  for (let i = s.length - 1; i >= 0; i--) {
    const ch = s[i]!;
    if (ch >= "0" && ch <= "9") {
      return parseInt(ch, 10);
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Formato classifier — 8 categories, deterministic order (REQ-PP-003)
// ---------------------------------------------------------------------------

export function classify(classifiedForm: string, compact: string): string {
  // Rule 1: Remolque — starts with 'R' followed by a digit
  if (matchRTDigit(compact, "R")) return "remolque";

  // Rule 2: Temporal — starts with 'T' followed by a digit
  if (matchRTDigit(compact, "T")) return "temporal";

  // Rule 3: Fuerza Pública — FAC prefix
  if (compact.startsWith("FAC")) return "fuerza_publica";

  // Rule 4: Fuerza Pública — national-police shape (#-#)
  if (/^\d{2,4}-\d{4}$/.test(classifiedForm)) return "fuerza_publica";

  // Rule 5: Diplomático — [DCM][A-Z]{2}[0-9]{1,4}
  if (matchDiplomatico(compact)) return "diplomatico";

  // Rule 6: Oficial — O[A-Z]{2} with whitespace in classified form
  if (matchOficial(classifiedForm, compact)) return "oficial";

  // Rule 7: Moto — [A-Z]{3}[0-9]{2}[A-Z]?
  if (/^[A-Z]{3}\d{2}[A-Z]?$/.test(compact)) return "moto";

  // Rule 8: Particular — [A-Z]{3}[0-9]{3}
  if (/^[A-Z]{3}\d{3}$/.test(compact)) return "particular";

  // Fallback
  return "desconocido";
}

// ---------------------------------------------------------------------------
// Rule-specific helpers
// ---------------------------------------------------------------------------

function matchRTDigit(compact: string, prefix: string): boolean {
  return compact.startsWith(prefix) && compact.length > 1 && compact[1]! >= "0" && compact[1]! <= "9";
}

function matchDiplomatico(compact: string): boolean {
  return /^[DCM][A-Z]{2}\d{1,4}$/.test(compact);
}

function matchOficial(classifiedForm: string, compact: string): boolean {
  // Must start with O + 2 letters + digits (compact), AND
  // have whitespace between letter and digit groups in classified form.
  if (!/^O[A-Z]{2}\d+$/.test(compact)) return false;
  return /^O[A-Z]{2}\s+\d+$/.test(classifiedForm);
}

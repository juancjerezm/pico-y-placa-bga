/** API contract types for Pico y Placa Worker. */

export interface RestriccionResponse {
  municipio: string;
  fecha: string;
  placa_normalized: string;
  restricted: boolean;
  last_digit: number;
  formato_detectado: string;
  rule: "weekday" | "saturday" | "festivo";
  source: "rotation" | "override";
  generated_at: string;
}

export interface ErrorResponse {
  error: "bad_plate" | "bad_date" | "bad_municipio" | "rotation_unknown";
  municipio?: string;
  requested_date?: string;
}

export interface RotationSummary {
  valid_from: string;
  valid_to: string;
  raw_payload: Record<string, unknown>;
}

export interface ScheduleResponse {
  current: RotationSummary | null;
  next: RotationSummary | null;
  message: string | null;
}

/** Raw rotation row from the database. */
export interface RotationRow {
  id: string;
  municipality: string;
  valid_from: string;
  valid_to: string;
  raw_payload: RotationPayload;
  source_url: string;
  scraped_at: string;
}

/** Shape of the raw_payload jsonb column in rotations. */
export interface RotationPayload {
  weekdays: Record<string, number[]>;
  saturday_calendar: Record<string, number[]>;
  article_title: string;
  article_url: string;
}

/** Raw exception_override row from the database. */
export interface OverrideRow {
  id: string;
  municipality: string;
  date: string;
  reason: string;
  source_url: string;
  scraped_at: string;
}

/** Raw holiday row from the database. */
export interface HolidayRow {
  date: string;
  name: string;
}

/** Query functions interface — allows mocking in tests. */
export interface Queries {
  getRotation(municipio: string, fecha: string): Promise<RotationRow | null>;
  getOverride(municipio: string, fecha: string): Promise<OverrideRow | null>;
  getHoliday(fecha: string): Promise<HolidayRow | null>;
  getCurrentRotation(
    municipio: string,
  ): Promise<Pick<RotationRow, "valid_from" | "valid_to" | "raw_payload"> | null>;
  getNextRotation(
    municipio: string,
  ): Promise<Pick<RotationRow, "valid_from" | "valid_to" | "raw_payload"> | null>;
}

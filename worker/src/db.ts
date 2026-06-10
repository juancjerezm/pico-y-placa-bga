/**
 * Database query layer — Supabase Postgres via postgres.js.
 *
 * All queries are READ-ONLY. The Worker never writes to the database.
 * Connection pooling is handled by Supabase Transaction pooler (port 6543).
 */

import type postgres from "postgres";
import type { HolidayRow, OverrideRow, Queries, RotationRow } from "./types";

export function createQueries(sql: postgres.Sql): Queries {
  return {
    /** Look up a rotation covering (municipio, fecha). Returns null if none. */
    async getRotation(
      municipio: string,
      fecha: string,
    ): Promise<RotationRow | null> {
      const rows = await sql<RotationRow[]>`
        SELECT id, municipality, valid_from, valid_to, raw_payload, source_url, scraped_at
        FROM rotations
        WHERE municipality = ${municipio}
          AND valid_from <= ${fecha}::date
          AND valid_to >= ${fecha}::date
        ORDER BY scraped_at DESC
        LIMIT 1
      `;
      return rows[0] ?? null;
    },

    /** Look up an exception override for (municipio, fecha). */
    async getOverride(
      municipio: string,
      fecha: string,
    ): Promise<OverrideRow | null> {
      const rows = await sql<OverrideRow[]>`
        SELECT id, municipality, date, reason, source_url, scraped_at
        FROM exception_overrides
        WHERE municipality = ${municipio}
          AND date = ${fecha}::date
        LIMIT 1
      `;
      return rows[0] ?? null;
    },

    /** Check if the given date is a Colombian festivo. */
    async getHoliday(fecha: string): Promise<HolidayRow | null> {
      const rows = await sql<HolidayRow[]>`
        SELECT date, name
        FROM holidays
        WHERE date = ${fecha}::date
        LIMIT 1
      `;
      return rows[0] ?? null;
    },

    /** Get the currently active rotation for a municipality. */
    async getCurrentRotation(
      municipio: string,
    ): Promise<Pick<RotationRow, "valid_from" | "valid_to" | "raw_payload"> | null> {
      const today = new Date().toISOString().split("T")[0]!;
      const rows = await sql<
        Pick<RotationRow, "valid_from" | "valid_to" | "raw_payload">[]
      >`
        SELECT valid_from, valid_to, raw_payload
        FROM rotations
        WHERE municipality = ${municipio}
          AND valid_from <= ${today}::date
          AND valid_to >= ${today}::date
        ORDER BY scraped_at DESC
        LIMIT 1
      `;
      return rows[0] ?? null;
    },

    /** Get the next upcoming rotation for a municipality. */
    async getNextRotation(
      municipio: string,
    ): Promise<Pick<RotationRow, "valid_from" | "valid_to" | "raw_payload"> | null> {
      const today = new Date().toISOString().split("T")[0]!;
      const rows = await sql<
        Pick<RotationRow, "valid_from" | "valid_to" | "raw_payload">[]
      >`
        SELECT valid_from, valid_to, raw_payload
        FROM rotations
        WHERE municipality = ${municipio}
          AND valid_from > ${today}::date
        ORDER BY valid_from ASC
        LIMIT 1
      `;
      return rows[0] ?? null;
    },
  };
}

-- 0003: Create holidays table
-- REQ-RD-003 — Colombian festivos (Sundays are implicit, not stored here)
-- Seeded from a manual CSV; law changes are rare.

create table holidays (
    date date primary key,
    name text not null
);

-- Fast lookup by date
create index idx_holidays_date on holidays (date);

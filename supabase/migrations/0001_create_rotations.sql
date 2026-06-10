-- 0001: Create rotations and scrape_logs tables
-- REQ-RD-001, REQ-RD-008 (audit trail)

create extension if not exists "pgcrypto";

-- Quarterly Pico y Placa rotation, one row per municipality
create table rotations (
    id uuid primary key default gen_random_uuid(),
    municipality text not null
        check (municipality in ('bucaramanga', 'floridablanca', 'giron', 'piedecuesta')),
    valid_from date not null,
    valid_to date not null,
    raw_payload jsonb not null,
    source_url text not null,
    scraped_at timestamptz not null default now(),

    constraint rotations_date_range check (valid_from <= valid_to)
);

-- Fast lookups by municipality + date window (used by the Worker API)
create index idx_rotations_municipality_dates
    on rotations (municipality, valid_from, valid_to);

-- For the stale-data alert: MAX(scraped_at) per municipality
create index idx_rotations_scraped_at
    on rotations (municipality, scraped_at desc);

-- Audit trail — written on every scraper run
create table scrape_logs (
    id uuid primary key default gen_random_uuid(),
    run_at timestamptz not null default now(),
    source text not null,
    success boolean not null default false,
    rows_written integer not null default 0,
    error text
);

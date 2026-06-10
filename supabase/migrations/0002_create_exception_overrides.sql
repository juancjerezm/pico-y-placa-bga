-- 0002: Create exception_overrides table
-- REQ-RD-002 — ad-hoc suspensions (e.g., Semana Santa)

create table exception_overrides (
    id uuid primary key default gen_random_uuid(),
    municipality text not null
        check (municipality in ('bucaramanga', 'floridablanca', 'giron', 'piedecuesta')),
    date date not null,
    reason text not null,
    source_url text not null,
    scraped_at timestamptz not null default now()
);

-- Fast lookup by (municipality, date) — checked before rotations lookup
create index idx_exception_overrides_lookup
    on exception_overrides (municipality, date);

-- Ensure one override per (municipality, date)
create unique index uq_exception_overrides_municipality_date
    on exception_overrides (municipality, date);

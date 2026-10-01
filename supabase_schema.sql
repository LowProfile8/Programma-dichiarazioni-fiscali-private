-- ════════════════════════════════════════════════════════════════════
-- Schema per l'archivio cloud di Athena (dichiarazioni, preventivi, fatture)
-- Da incollare UNA VOLTA SOLA nell'SQL Editor di Supabase (Database → SQL
-- Editor → New query → incolla tutto → Run). Vedi le istruzioni allegate
-- per il resto della configurazione (bucket, chiavi).
-- ════════════════════════════════════════════════════════════════════

-- Dichiarazioni fiscali in corso (lo stato completo del wizard)
create table if not exists dichiarazioni (
    id text primary key,
    titolo text not null,
    step integer not null default 0,
    dati jsonb not null,
    salvato timestamptz not null default now()
);

-- Preventivi e fatture generati (i dati del modulo + eventuali campi liberi
-- come "pagato"/"data_pagamento" per le fatture). Il PDF vero e proprio non
-- sta qui: sta nello storage, nel bucket "documenti-pdf".
create table if not exists documenti (
    id text primary key,
    tipo text not null check (tipo in ('preventivo', 'fattura')),
    titolo text not null,
    dati jsonb not null,
    extra jsonb not null default '{}'::jsonb,
    salvato timestamptz not null default now()
);

-- Un indice per trovare rapidamente "solo le fatture" o "solo i preventivi"
create index if not exists documenti_tipo_idx on documenti (tipo);

-- Sicurezza: il programma si collega con la "service_role key", che ha già
-- accesso completo e bypassa le regole RLS. Attiviamo comunque RLS sulle
-- tabelle per buona pratica (nessun'altra chiave potrà leggerle per sbaglio).
alter table dichiarazioni enable row level security;
alter table documenti enable row level security;

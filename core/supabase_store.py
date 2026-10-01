"""
core/supabase_store.py — connessione a Supabase: le tabelle (dati) e lo storage (PDF).

Perché serve: il container dove gira il programma su Streamlit Cloud si
svuota a ogni riavvio o aggiornamento del codice — tutto quello che veniva
salvato su disco (progetti_salvati/, archivio_documenti/) andava perso.
Con Supabase i dati restano in un database nel cloud, indipendente dal
programma: sopravvivono a riavvii, aggiornamenti e redeploy.

Le credenziali si leggono da st.secrets["SUPABASE_URL"] e
st.secrets["SUPABASE_KEY"] (la "service_role key", non la "anon key": vedi
le istruzioni che accompagnano questo file). Girano solo lato server, nel
codice di Streamlit — mai nel browser del cliente — quindi possono restare
private senza dover configurare le regole di accesso (RLS) su Supabase.

Se le chiavi non sono configurate, `disponibile()` ritorna False e i moduli
che usano questo file ricadono sul salvataggio locale su disco (comodo per
provare il programma in locale senza configurare nulla, ma NON persistente
su Streamlit Cloud: per quello servono le chiavi).
"""

from typing import Optional

import streamlit as st

BUCKET_PDF = "documenti-pdf"


def disponibile() -> bool:
    try:
        return bool(st.secrets["SUPABASE_URL"]) and bool(st.secrets["SUPABASE_KEY"])
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def _client():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


# ── Tabelle (dati in formato JSON) ──────────────────────────────────────
def upsert_riga(tabella: str, riga: dict) -> None:
    """riga deve contenere la chiave 'id'."""
    _client().table(tabella).upsert(riga).execute()


def elenco_righe(tabella: str, filtro: Optional[dict] = None) -> list:
    query = _client().table(tabella).select("*")
    if filtro:
        for campo, valore in filtro.items():
            query = query.eq(campo, valore)
    return query.order("salvato", desc=True).execute().data or []


def leggi_riga(tabella: str, id_riga: str) -> Optional[dict]:
    righe = _client().table(tabella).select("*").eq("id", id_riga).limit(1).execute().data
    return righe[0] if righe else None


def elimina_riga(tabella: str, id_riga: str) -> None:
    _client().table(tabella).delete().eq("id", id_riga).execute()


def aggiorna_riga(tabella: str, id_riga: str, campi: dict) -> None:
    _client().table(tabella).update(campi).eq("id", id_riga).execute()


# ── Storage (i PDF) ──────────────────────────────────────────────────────
def carica_file(percorso: str, contenuto: bytes, content_type: str = "application/pdf") -> None:
    """Salva (o sovrascrive) un file nel bucket PDF."""
    bucket = _client().storage.from_(BUCKET_PDF)
    opzioni = {"content-type": content_type, "upsert": "true"}
    try:
        bucket.upload(percorso, contenuto, opzioni)
    except Exception:
        bucket.update(percorso, contenuto, opzioni)   # esiste già: sovrascrive


def scarica_file(percorso: str) -> bytes:
    return _client().storage.from_(BUCKET_PDF).download(percorso)


def elimina_file(percorso: str) -> None:
    try:
        _client().storage.from_(BUCKET_PDF).remove([percorso])
    except Exception:
        pass   # già assente: non è un problema

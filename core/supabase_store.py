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


@st.cache_data(ttl=60, show_spinner=False)
def _stato_connessione_cache() -> bool:
    """Interrogazione minima, solo per sapere se Supabase risponde — in cache un minuto,
    così la barra di stato non rallenta la pagina controllandolo di continuo."""
    _client().table("dichiarazioni").select("id").limit(1).execute()
    return True


def stato_connessione():
    """True = collegato, False = configurato ma non raggiungibile, None = Supabase non
    configurato (si usa il salvataggio locale, niente da segnalare)."""
    if not disponibile():
        return None
    try:
        return _stato_connessione_cache()
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def _client():
    import re
    from supabase import create_client
    # SUPABASE_URL deve essere SOLO l'indirizzo del progetto (es. "https://xxxxx.supabase.co"):
    # la libreria aggiunge da sola "/rest/v1/..." quando serve. Se qualcuno incolla per sbaglio
    # anche "/rest/v1" (preso da un altro punto del pannello Supabase) o una barra finale,
    # il percorso raddoppia e Supabase risponde "Invalid path specified in request URL"
    # (PGRST125): qui lo ripuliamo comunque, invece di spiegarlo ogni volta.
    url = str(st.secrets["SUPABASE_URL"]).strip()
    url = re.sub(r"/rest/v1/?$", "", url).rstrip("/")
    key = str(st.secrets["SUPABASE_KEY"]).strip()
    return create_client(url, key)


def _messaggio_errore(errore: Exception) -> str:
    """Streamlit, sullo schermo dell'utente, nasconde il testo vero di un errore non gestito
    ('redatto per evitare fughe di dati'). Qui lo mostriamo noi esplicitamente con st.error,
    PRIMA che Streamlit lo nasconda, così si vede davvero cos'ha risposto Supabase."""
    dettaglio = getattr(errore, "args", [None])[0]
    if isinstance(dettaglio, dict):
        pezzi = [str(dettaglio[k]) for k in ("message", "details", "hint", "code") if dettaglio.get(k)]
        testo = " — ".join(pezzi) or str(dettaglio)
    else:
        testo = str(errore)
    return testo


def mostra_errore(descrizione: str, errore: Exception) -> None:
    """Mostra in chiaro un errore già capitato (es. in un thread secondario, dove chiamare
    st.error direttamente non è sicuro). Non rilancia l'eccezione: lo fa il chiamante."""
    st.error(
        f"**Errore da Supabase** durante «{descrizione}»:\n\n`{_messaggio_errore(errore)}`\n\n"
        "Controlla, nell'ordine: 1) di aver eseguito tutto `supabase_schema.sql` nell'SQL Editor; "
        "2) che il bucket si chiami esattamente `documenti-pdf`; 3) di aver messo la **Secret key** "
        "(non la Publishable key) in `SUPABASE_KEY`; 4) su Settings → API, il pulsante "
        "«Reload schema cache», se hai creato le tabelle da poco."
    )


def _con_errore_visibile(descrizione: str, funzione, *args, **kwargs):
    try:
        return funzione(*args, **kwargs)
    except Exception as errore:
        mostra_errore(descrizione, errore)
        raise


# ── Tabelle (dati in formato JSON) ──────────────────────────────────────
def upsert_riga(tabella: str, riga: dict) -> None:
    """riga deve contenere la chiave 'id'."""
    _con_errore_visibile(f"salvataggio in «{tabella}»", lambda: _client().table(tabella).upsert(riga).execute())


def elenco_righe(tabella: str, filtro: Optional[dict] = None) -> list:
    def chiamata():
        query = _client().table(tabella).select("*")
        if filtro:
            for campo, valore in filtro.items():
                query = query.eq(campo, valore)
        return query.order("salvato", desc=True).execute().data or []
    return _con_errore_visibile(f"lettura di «{tabella}»", chiamata)


def _leggi_riga_raw(tabella: str, id_riga: str) -> Optional[dict]:
    """Come leggi_riga, ma senza st.error in caso di errore: solo per uso interno, da un
    thread secondario (vedi archivio_docs.salva), dove le chiamate a Streamlit non sono sicure."""
    righe = _client().table(tabella).select("*").eq("id", id_riga).limit(1).execute().data
    return righe[0] if righe else None


def leggi_riga(tabella: str, id_riga: str) -> Optional[dict]:
    return _con_errore_visibile(f"lettura di «{tabella}»", _leggi_riga_raw, tabella, id_riga)


def elimina_riga(tabella: str, id_riga: str) -> None:
    _con_errore_visibile(
        f"cancellazione da «{tabella}»", lambda: _client().table(tabella).delete().eq("id", id_riga).execute()
    )


def aggiorna_riga(tabella: str, id_riga: str, campi: dict) -> None:
    _con_errore_visibile(
        f"aggiornamento di «{tabella}»", lambda: _client().table(tabella).update(campi).eq("id", id_riga).execute()
    )


def _assicura_bucket() -> None:
    """Crea il bucket dei PDF se non esiste già (succede solo la primissima volta che serve:
    dopo non deve più ricapitare, qualunque cosa sia stata dimenticata nella configurazione)."""
    storage = _client().storage
    try:
        storage.get_bucket(BUCKET_PDF)
    except Exception:
        try:
            storage.create_bucket(BUCKET_PDF, options={"public": False})
        except Exception:
            pass   # creato nel frattempo da un'altra richiesta, o permessi insufficienti: ci pensa il chiamante


# ── Storage (i PDF) ──────────────────────────────────────────────────────
def _carica_file_raw(percorso: str, contenuto: bytes, content_type: str = "application/pdf") -> None:
    """Come carica_file, ma senza st.error in caso di errore: solo per uso interno, da un
    thread secondario (vedi archivio_docs.salva), dove le chiamate a Streamlit non sono sicure."""
    opzioni = {"content-type": content_type, "upsert": "true"}
    bucket = _client().storage.from_(BUCKET_PDF)
    try:
        bucket.upload(percorso, contenuto, opzioni)
    except Exception as prima_volta:
        if "bucket not found" in str(prima_volta).lower() or "bucket not found" in repr(getattr(prima_volta, "args", [""])).lower():
            _assicura_bucket()
            bucket.upload(percorso, contenuto, opzioni)   # riprova, ora che il bucket esiste
        else:
            bucket.update(percorso, contenuto, opzioni)   # il file esiste già: sovrascrive


def carica_file(percorso: str, contenuto: bytes, content_type: str = "application/pdf") -> None:
    """Salva (o sovrascrive) un file nel bucket PDF. Crea il bucket da solo se manca ancora."""
    _con_errore_visibile(f"caricamento del file «{percorso}»", _carica_file_raw, percorso, contenuto, content_type)


def scarica_file(percorso: str) -> bytes:
    return _con_errore_visibile(
        f"scaricamento del file «{percorso}»", lambda: _client().storage.from_(BUCKET_PDF).download(percorso)
    )


def elimina_file(percorso: str) -> None:
    try:
        _client().storage.from_(BUCKET_PDF).remove([percorso])
    except Exception:
        pass   # già assente: non è un problema

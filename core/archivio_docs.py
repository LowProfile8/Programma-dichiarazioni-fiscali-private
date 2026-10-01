"""
core/archivio_docs.py — archivio dei preventivi e delle fatture generati.

Se in st.secrets sono configurate le chiavi di Supabase (vedi
core/supabase_store.py), i dati finiscono in una tabella Supabase e il PDF
nello storage Supabase: sopravvivono a riavvii, aggiornamenti del codice e
redeploy. Senza quelle chiavi ricade su una cartella locale
(archivio_documenti/), comoda in locale ma temporanea su Streamlit Cloud.

Più semplice di core/salvataggio.py (quello della dichiarazione, con oggetti
annidati): qui i dati sono due dataclass piatte (DatiPreventivo, DatiFattura),
quindi si salvano con un asdict() diretto.
"""

import base64
import dataclasses
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core import supabase_store

CARTELLA = Path(__file__).parent.parent / "archivio_documenti"
_ID_VALIDO = re.compile(r"^[a-z0-9_-]{1,80}$")


def _a_json(obj):
    if dataclasses.is_dataclass(obj):
        return {k: _a_json(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, date):
        return {"__date": obj.isoformat()}
    if isinstance(obj, dict):
        return {k: _a_json(v) for k, v in obj.items()}
    return obj


def _da_json(campo, valore):
    """Ricostruisce un campo (usa il tipo dichiarato nella dataclass per sapere se è una data)."""
    if isinstance(valore, dict) and "__date" in valore:
        return date.fromisoformat(valore["__date"])
    return valore


def _slug(testo: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (testo or "").lower()).strip("-")
    return s[:50] or "documento"


def _percorso_storage(tipo: str, doc_id: str) -> str:
    return f"{tipo}/{doc_id}.pdf"


def salva(tipo: str, dati, pdf_bytes: bytes, titolo: str, doc_id: Optional[str] = None, **extra) -> str:
    """tipo: 'preventivo' | 'fattura'. Ritorna l'id del documento (per aggiornarlo in seguito).
    extra: campi liberi (es. cliente=..., pagato=False) — se il documento esiste già, i campi
    extra già impostati a mano (come 'pagato') NON vengono sovrascritti da un valore di default."""
    doc_id = doc_id or f"{datetime.now():%Y%m%d-%H%M%S}_{_slug(titolo)}"
    if not _ID_VALIDO.match(doc_id):
        doc_id = _slug(doc_id)

    if supabase_store.disponibile():
        # La lettura (serve solo per non perdere campi come "pagato" già impostati a mano) e il
        # caricamento del PDF sono indipendenti: li facciamo partire insieme invece che in fila,
        # per non far aspettare due "viaggi" di rete verso Supabase uno dopo l'altro.
        percorso_pdf = _percorso_storage(tipo, doc_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futuro_lettura = pool.submit(supabase_store._leggi_riga_raw, "documenti", doc_id)
            futuro_caricamento = pool.submit(supabase_store._carica_file_raw, percorso_pdf, pdf_bytes)
            try:
                esistente = futuro_lettura.result()
            except Exception:
                esistente = None   # non blocca il salvataggio: trattato come "non esisteva ancora"
            errore_caricamento = None
            try:
                futuro_caricamento.result()
            except Exception as e:
                errore_caricamento = e

        extra_precedente = (esistente or {}).get("extra") or {}
        supabase_store.upsert_riga("documenti", {
            "id": doc_id, "tipo": tipo, "titolo": titolo,
            "dati": _a_json(dati), "extra": {**extra, **extra_precedente},
            "salvato": datetime.now().isoformat(timespec="seconds"),
        })
        if errore_caricamento is not None:
            # Il file non è arrivato su Supabase: se la riga era NUOVA (non esisteva prima),
            # la togliamo subito, altrimenti resterebbe nell'archivio senza nessun PDF da
            # scaricare — una riga "fantasma" impossibile da aprire in seguito.
            if esistente is None:
                try:
                    supabase_store.elimina_riga("documenti", doc_id)
                except Exception:
                    pass
            supabase_store.mostra_errore(f"caricamento del file «{percorso_pdf}»", errore_caricamento)
            raise errore_caricamento
        return doc_id

    CARTELLA.mkdir(exist_ok=True)
    percorso = CARTELLA / f"{doc_id}.json"
    extra_precedente = {}
    if percorso.exists():
        try:
            extra_precedente = json.loads(percorso.read_text(encoding="utf-8")).get("extra", {})
        except Exception:
            pass
    contenuto = {
        "tipo": tipo,
        "titolo": titolo,
        "salvato": datetime.now().isoformat(timespec="seconds"),
        "dati": _a_json(dati),
        "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        "extra": {**extra, **extra_precedente},   # i valori già salvati a mano (es. pagato=True) hanno la precedenza
    }
    percorso.write_text(json.dumps(contenuto, ensure_ascii=False), encoding="utf-8")
    return doc_id


def elenco(tipo: Optional[str] = None) -> list:
    """[{'id','tipo','titolo','salvato', ...campi extra tipo 'pagato'...}], dal più recente. tipo=None -> tutti."""
    if supabase_store.disponibile():
        try:
            righe = supabase_store.elenco_righe("documenti", {"tipo": tipo} if tipo else None)
        except Exception:
            return []
        risultato = []
        for r in righe:
            voce = {"id": r["id"], "tipo": r.get("tipo"), "titolo": r.get("titolo", r["id"]), "salvato": r.get("salvato", "")}
            voce.update(r.get("extra") or {})
            risultato.append(voce)
        return risultato

    if not CARTELLA.exists():
        return []
    risultato = []
    for file in CARTELLA.glob("*.json"):
        try:
            c = json.loads(file.read_text(encoding="utf-8"))
            if tipo and c.get("tipo") != tipo:
                continue
            voce = {"id": file.stem, "tipo": c.get("tipo"), "titolo": c.get("titolo", file.stem),
                    "salvato": c.get("salvato", "")}
            voce.update(c.get("extra", {}))
            risultato.append(voce)
        except Exception:
            continue
    return sorted(risultato, key=lambda p: p["salvato"], reverse=True)


def aggiorna_extra(doc_id: str, **campi) -> None:
    """Aggiorna/aggiunge campi liberi (es. pagato, data_pagamento, cliente) senza toccare dati/pdf."""
    if supabase_store.disponibile():
        riga = supabase_store.leggi_riga("documenti", doc_id)
        if riga is None:
            raise ValueError("Documento non trovato.")
        extra = {**(riga.get("extra") or {}), **campi}
        supabase_store.aggiorna_riga("documenti", doc_id, {"extra": extra})
        return
    percorso = _percorso(doc_id)
    c = json.loads(percorso.read_text(encoding="utf-8"))
    extra = c.setdefault("extra", {})
    extra.update(campi)
    percorso.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")


def carica_pdf(doc_id: str) -> bytes:
    if supabase_store.disponibile():
        riga = supabase_store.leggi_riga("documenti", doc_id)
        if riga is None:
            raise ValueError("Documento non trovato.")
        return supabase_store.scarica_file(_percorso_storage(riga["tipo"], doc_id))
    percorso = _percorso(doc_id)
    c = json.loads(percorso.read_text(encoding="utf-8"))
    return base64.b64decode(c["pdf_base64"])


def carica_dati(doc_id: str) -> dict:
    """I campi salvati (dict grezzo: il chiamante sa come ricostruire la propria dataclass)."""
    if supabase_store.disponibile():
        riga = supabase_store.leggi_riga("documenti", doc_id)
        if riga is None:
            raise ValueError("Documento non trovato.")
        return riga["dati"]
    percorso = _percorso(doc_id)
    c = json.loads(percorso.read_text(encoding="utf-8"))
    return c["dati"]


def _percorso(doc_id: str) -> Path:
    if not _ID_VALIDO.match(doc_id):
        raise ValueError("Identificativo non valido.")
    return CARTELLA / f"{doc_id}.json"


def elimina(doc_id: str) -> None:
    if supabase_store.disponibile():
        riga = supabase_store.leggi_riga("documenti", doc_id)
        supabase_store.elimina_riga("documenti", doc_id)
        if riga:
            supabase_store.elimina_file(_percorso_storage(riga["tipo"], doc_id))
        return
    _percorso(doc_id).unlink(missing_ok=True)

"""
core/archivio_docs.py — archivio dei preventivi e delle fatture generati.

Più semplice di core/salvataggio.py (quello della dichiarazione, con oggetti
annidati): qui i dati sono due dataclass piatte (DatiPreventivo, DatiFattura),
quindi si salvano con un asdict() diretto. Insieme ai dati si tiene anche
l'ultimo PDF generato, così riaprire un documento significa poterlo
riscaricare subito, senza doverlo rigenerare.
"""

import base64
import dataclasses
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

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


def salva(tipo: str, dati, pdf_bytes: bytes, titolo: str, doc_id: Optional[str] = None, **extra) -> str:
    """tipo: 'preventivo' | 'fattura'. Ritorna l'id del documento (per aggiornarlo in seguito).
    extra: campi liberi (es. cliente=..., pagato=False) — se il documento esiste già, i campi
    extra già impostati a mano (come 'pagato') NON vengono sovrascritti da un valore di default."""
    doc_id = doc_id or f"{datetime.now():%Y%m%d-%H%M%S}_{_slug(titolo)}"
    if not _ID_VALIDO.match(doc_id):
        doc_id = _slug(doc_id)
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
    percorso = _percorso(doc_id)
    c = json.loads(percorso.read_text(encoding="utf-8"))
    extra = c.setdefault("extra", {})
    extra.update(campi)
    percorso.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")


def carica_pdf(doc_id: str) -> bytes:
    percorso = _percorso(doc_id)
    c = json.loads(percorso.read_text(encoding="utf-8"))
    return base64.b64decode(c["pdf_base64"])


def carica_dati(doc_id: str) -> dict:
    """I campi salvati (dict grezzo: il chiamante sa come ricostruire la propria dataclass)."""
    percorso = _percorso(doc_id)
    c = json.loads(percorso.read_text(encoding="utf-8"))
    return c["dati"]


def _percorso(doc_id: str) -> Path:
    if not _ID_VALIDO.match(doc_id):
        raise ValueError("Identificativo non valido.")
    return CARTELLA / f"{doc_id}.json"


def elimina(doc_id: str) -> None:
    _percorso(doc_id).unlink(missing_ok=True)

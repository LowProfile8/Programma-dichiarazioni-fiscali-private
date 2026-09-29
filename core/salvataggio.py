"""
core/salvataggio.py — salvare un progetto a metà e riaprirlo dopo.

Due modi, entrambi basati sullo stesso file JSON:
1. Archivio «Progetti in corso» (cartella progetti_salvati/ accanto all'app),
   elencato nel menu laterale: si salva, si riapre, si elimina.
2. File di salvataggio scaricabile / ricaricabile: sopravvive ai riavvii
   dell'app (su Streamlit Cloud l'archivio locale è temporaneo).

Nel file finiscono solo i dati inseriti (e i NOMI dei documenti allegati, non
i documenti). Sono dati fiscali di clienti: l'archivio è visibile a chiunque
apra l'app, quindi va usato con l'accesso protetto (vedi app.py: codice di
accesso opzionale).
"""

import dataclasses
import enum
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core import models

CARTELLA = Path(__file__).parent.parent / "progetti_salvati"
VERSIONE = 1
_ID_VALIDO = re.compile(r"^[a-z0-9_-]{1,80}$")

_CLASSI = {
    nome: oggetto for nome, oggetto in vars(models).items()
    if isinstance(oggetto, type) and (dataclasses.is_dataclass(oggetto) or issubclass(oggetto, enum.Enum))
}


# ── serializzazione ─────────────────────────────────────────────────────
def a_json(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        risultato = {"__t": type(obj).__name__}
        for campo in dataclasses.fields(obj):
            risultato[campo.name] = a_json(getattr(obj, campo.name))
        return risultato
    if isinstance(obj, enum.Enum):
        return {"__enum": type(obj).__name__, "v": obj.value}
    if isinstance(obj, date):
        return {"__date": obj.isoformat()[:10]}
    if isinstance(obj, (list, tuple)):
        return [a_json(x) for x in obj]
    if isinstance(obj, dict):
        return {k: a_json(v) for k, v in obj.items()}
    return obj


def da_json(x):
    if isinstance(x, dict):
        if "__t" in x:
            classe = _CLASSI[x["__t"]]
            noti = {campo.name for campo in dataclasses.fields(classe)}   # ignora campi di versioni diverse
            return classe(**{k: da_json(v) for k, v in x.items() if k != "__t" and k in noti})
        if "__enum" in x:
            return _CLASSI[x["__enum"]](x["v"])
        if "__date" in x:
            return date.fromisoformat(x["__date"])
        return {k: da_json(v) for k, v in x.items()}
    if isinstance(x, list):
        return [da_json(v) for v in x]
    return x


def a_bytes(dichiarazione, step: int = 0) -> bytes:
    contenuto = {
        "versione": VERSIONE, "salvato": datetime.now().isoformat(timespec="seconds"),
        "step": step, "dichiarazione": a_json(dichiarazione),
    }
    return json.dumps(contenuto, ensure_ascii=False, indent=1).encode("utf-8")


def da_bytes(dati: bytes):
    """(dichiarazione, step) da un file di salvataggio; ValueError se il file non è valido."""
    try:
        contenuto = json.loads(dati.decode("utf-8"))
        return da_json(contenuto["dichiarazione"]), int(contenuto.get("step", 0))
    except Exception as errore:   # file non nostro, troncato o di altra versione
        raise ValueError("Il file non è un salvataggio valido.") from errore


# ── archivio locale ─────────────────────────────────────────────────────
def titolo(dichiarazione) -> str:
    c = dichiarazione.contribuente
    nome = f"{c.cognome} {c.nome}".strip() or "Senza nome"
    return f"{nome} — {dichiarazione.anno_fiscale}"


def _slug(testo: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", testo.lower()).strip("-")
    return s[:40] or "progetto"


def nuovo_id(dichiarazione) -> str:
    return f"{datetime.now():%Y%m%d-%H%M%S}_{_slug(titolo(dichiarazione))}"


def _percorso(progetto_id: str) -> Path:
    if not _ID_VALIDO.match(progetto_id):
        raise ValueError("Identificativo di progetto non valido.")
    return CARTELLA / f"{progetto_id}.json"


def salva(dichiarazione, step: int, progetto_id: Optional[str] = None) -> str:
    progetto_id = progetto_id or nuovo_id(dichiarazione)
    CARTELLA.mkdir(exist_ok=True)
    _percorso(progetto_id).write_bytes(a_bytes(dichiarazione, step))
    return progetto_id


def carica(progetto_id: str):
    return da_bytes(_percorso(progetto_id).read_bytes())


def elimina(progetto_id: str) -> None:
    _percorso(progetto_id).unlink(missing_ok=True)


def elenco() -> list:
    """Progetti salvati, dal più recente: [{'id', 'titolo', 'salvato'}]."""
    if not CARTELLA.exists():
        return []
    risultato = []
    for file in CARTELLA.glob("*.json"):
        try:
            contenuto = json.loads(file.read_text(encoding="utf-8"))
            dich = da_json(contenuto["dichiarazione"])
            risultato.append({"id": file.stem, "titolo": titolo(dich), "salvato": contenuto.get("salvato", "")})
        except Exception:
            continue   # file rovinato: non blocca l'elenco
    return sorted(risultato, key=lambda p: p["salvato"], reverse=True)

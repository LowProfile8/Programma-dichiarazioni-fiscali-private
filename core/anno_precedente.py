"""
core/anno_precedente.py

Permette, per QUALSIASI campo del wizard, di cercare il valore corrispondente
nella dichiarazione dell'anno precedente che il contribuente ha caricato
all'inizio (facoltativo).

Perché una ricerca "su richiesta" e non un'estrazione totale a monte:
la dichiarazione precedente è un PDF di 10-15 pagine con moduli diversi;
provare a pre-mappare OGNI possibile campo del wizard su OGNI possibile
posizione nel PDF sarebbe fragile (cambia struttura da modulo a modulo,
da anno ad anno, da cantone a cantone). Cercare puntualmente "trovami il
valore per [descrizione del campo]" con l'AI in modalità vision, solo
quando l'utente lo chiede esplicitamente, è più robusto e più semplice da
mantenere.

Il risultato non è MAI messo automaticamente nel campo: torna sempre
come proposta con provenienza dichiarata, e l'interfaccia (core/ui_helpers.py)
la marca con l'avviso ⚠️ e la lascia modificabile.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

from core.immagini import documento_in_immagini_base64

logger = logging.getLogger("dichiarazioni.anno_precedente")

MODELLO_VISION = "claude-sonnet-5"


@dataclass
class RisultatoRicercaAnnoPrecedente:
    trovato: bool
    valore: Optional[str] = None
    contesto: Optional[str] = None  # breve descrizione di dove è stato trovato, per fiducia dell'utente
    errore: Optional[str] = None


async def _cerca_async(api_key: str, immagini_b64: list[str], descrizione_campo: str) -> dict:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)

    prompt_sistema = f"""Stai esaminando le pagine di una dichiarazione d'imposta svizzera (Ticino) dell'anno precedente.
Cerca il valore corrispondente a questo campo: "{descrizione_campo}"

Rispondi SOLO con un oggetto JSON in questo formato, nessun testo prima o dopo:
{{"trovato": true/false, "valore": "il valore trovato come stringa, o null", "contesto": "breve descrizione di dove l'hai trovato, es. 'Modulo 2, riga UBS AG conto corrente', o null"}}

Se non sei sicuro o il campo non è presente in queste pagine, rispondi con trovato: false."""

    content = [{"type": "text", "text": f"Cerca: {descrizione_campo}"}]
    for b64 in immagini_b64:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})

    risposta = await client.messages.create(
        model=MODELLO_VISION,
        max_tokens=500,
        system=prompt_sistema,
        messages=[{"role": "user", "content": content}],
    )
    testo = "".join(b.text for b in risposta.content if b.type == "text").strip()
    if testo.startswith("```"):
        testo = testo.strip("`")
        if testo.startswith("json"):
            testo = testo[4:]
        testo = testo.strip()
    return json.loads(testo)


def cerca_valore_anno_precedente(
    pdf_bytes: bytes,
    nome_file: str,
    descrizione_campo: str,
    api_key: str,
    pagine_max: int = 6,
) -> RisultatoRicercaAnnoPrecedente:
    """Punto di ingresso sincrono. pagine_max limita quante pagine del PDF
    vengono mandate all'AI per tenere la ricerca veloce ed economica — 6
    pagine coprono di norma Modulo 1 e 2, le più cercate; se in futuro serve
    cercare nei moduli successivi (7, 8) andrà reso configurabile per sezione."""
    if not api_key:
        return RisultatoRicercaAnnoPrecedente(trovato=False, errore="Nessuna API key fornita.")

    try:
        immagini_b64 = documento_in_immagini_base64(pdf_bytes, nome_file, max_pagine=pagine_max)
    except Exception as e:
        return RisultatoRicercaAnnoPrecedente(trovato=False, errore=f"Impossibile leggere il PDF: {e}")

    try:
        risultato = asyncio.run(_cerca_async(api_key, immagini_b64, descrizione_campo))
    except Exception as e:
        logger.error("Ricerca anno precedente fallita: %s", e)
        return RisultatoRicercaAnnoPrecedente(trovato=False, errore=f"Ricerca non riuscita: {e}")

    return RisultatoRicercaAnnoPrecedente(
        trovato=bool(risultato.get("trovato")),
        valore=risultato.get("valore"),
        contesto=risultato.get("contesto"),
    )

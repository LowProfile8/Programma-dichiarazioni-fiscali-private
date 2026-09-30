"""
core/extraction.py — estrazione dei campi del certificato di salario tramite
AI vision, con retry se il JSON torna malformato. Restituisce sempre dati
grezzi: la validazione manuale avviene nel modulo Streamlit chiamante.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from core.immagini import documento_in_immagini_base64

logger = logging.getLogger("dichiarazioni.extraction")

MODELLO_VISION = "claude-sonnet-5"
MAX_TENTATIVI = 3

CAMPI_CERTIFICATO_SALARIO = [
    ("datore_lavoro", "Datore di lavoro", "Nome del datore di lavoro che emette il certificato"),
    ("cifra_10_contributi_lpp", "Cifra 10 — Contributi LPP", "Importo dei contributi alla previdenza professionale, cifra 10"),
    ("cifra_11_salario_netto", "Cifra 11 — Salario netto", "Importo alla cifra 11, il salario netto (dedotti AVS/AI/LPP/IPG/AD/AINP) — il valore che ci interessa davvero"),
]
# Nota: la cifra 1 (salario lordo) è stata tolta su richiesta esplicita —
# per la dichiarazione conta solo il netto (cifra 11).


@dataclass
class RisultatoEstrazione:
    campi: dict = field(default_factory=dict)
    avvisi: list = field(default_factory=list)
    errore: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.errore is None


def _costruisci_prompt() -> str:
    righe = "\n".join(f'- "{chiave}": {descrizione}' for chiave, _et, descrizione in CAMPI_CERTIFICATO_SALARIO)
    esempio = ", ".join(f'"{chiave}": null' for chiave, _et, _d in CAMPI_CERTIFICATO_SALARIO)
    return f"""Sei un assistente fiscale svizzero. Analizza il certificato di salario (Lohnausweis) allegato ed estrai:
{righe}

REGOLE:
- Se un campo non è leggibile, usa null (mai inventare).
- Importi come stringa, formato originale (es. "43'859.00"), senza convertire separatori.
- Rispondi SOLO con un oggetto JSON valido:
{{{esempio}}}
"""


async def _chiama_ai_vision(api_key: str, immagini_b64: list[str]) -> dict:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)
    content = [{"type": "text", "text": "Estrai i campi richiesti, rispondi SOLO in JSON."}]
    for b64 in immagini_b64:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})

    messaggi = [{"role": "user", "content": content}]
    ultimo_errore = None
    prompt_sistema = _costruisci_prompt()

    for tentativo in range(MAX_TENTATIVI):
        try:
            risposta = await client.messages.create(
                model=MODELLO_VISION, max_tokens=800, system=prompt_sistema, messages=messaggi,
            )
            testo = "".join(b.text for b in risposta.content if b.type == "text").strip()
            if testo.startswith("```"):
                testo = testo.strip("`")
                if testo.startswith("json"):
                    testo = testo[4:]
                testo = testo.strip()
            return json.loads(testo)
        except json.JSONDecodeError as e:
            ultimo_errore = f"Risposta AI non in formato JSON valido: {e}"
            logger.warning("Tentativo %d/%d fallito: %s", tentativo + 1, MAX_TENTATIVI, ultimo_errore)
            messaggi = messaggi + [
                {"role": "assistant", "content": testo},
                {"role": "user", "content": "Non era JSON valido. Rispondi di nuovo SOLO con l'oggetto JSON."},
            ]
        except Exception as e:
            ultimo_errore = f"Errore nella chiamata all'API: {e}"
            logger.error("Tentativo %d/%d fallito: %s", tentativo + 1, MAX_TENTATIVI, ultimo_errore)

    raise RuntimeError(ultimo_errore or "Estrazione fallita dopo tutti i tentativi")


def estrai_certificato_salario(file_bytes: bytes, nome_file: str, api_key: str) -> RisultatoEstrazione:
    if not api_key:
        return RisultatoEstrazione(errore="Nessuna API key Anthropic fornita (impostala in '⚙️ Impostazioni avanzate' in fondo alla pagina).")

    try:
        immagini_b64 = documento_in_immagini_base64(file_bytes, nome_file)
    except Exception as e:
        return RisultatoEstrazione(errore=f"Impossibile leggere il documento '{nome_file}': {e}")

    try:
        campi_grezzi = asyncio.run(_chiama_ai_vision(api_key, immagini_b64))
    except RuntimeError as e:
        return RisultatoEstrazione(errore=str(e))

    campi_finali, avvisi = {}, []
    for chiave, etichetta, _descrizione in CAMPI_CERTIFICATO_SALARIO:
        valore = campi_grezzi.get(chiave)
        campi_finali[chiave] = valore
        if valore in (None, ""):
            avvisi.append(f"Campo non trovato: {etichetta}")

    return RisultatoEstrazione(campi=campi_finali, avvisi=avvisi)

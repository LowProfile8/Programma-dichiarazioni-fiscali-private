"""
core/immagini.py — conversione PDF/immagine in JPEG base64 ottimizzati,
pronti per l'invio a un modello AI in modalità vision. Nessuna dipendenza
da API esterne: testabile da solo con qualunque file di esempio.
"""

import base64
import io
import logging
from pathlib import Path

from PIL import Image, ImageOps

logger = logging.getLogger("dichiarazioni.immagini")

ESTENSIONI_IMMAGINE = {".png", ".jpg", ".jpeg", ".webp"}


def _ottimizza_immagine(img: Image.Image, max_lato: int = 2000) -> Image.Image:
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    larghezza, altezza = img.size
    lato_max = max(larghezza, altezza)
    if lato_max > max_lato:
        scala = max_lato / lato_max
        img = img.resize((int(larghezza * scala), int(altezza * scala)), Image.LANCZOS)
    return img


def documento_in_immagini_base64(file_bytes: bytes, nome_file: str, max_pagine: int = 3) -> list[str]:
    estensione = Path(nome_file).suffix.lower()
    immagini: list[Image.Image] = []

    if estensione == ".pdf":
        from pdf2image import convert_from_bytes
        pagine = convert_from_bytes(file_bytes, fmt="jpeg", dpi=200)
        if not pagine:
            raise ValueError(f"Nessuna pagina trovata nel PDF '{nome_file}'")
        immagini = pagine[:max_pagine]
        if len(pagine) > max_pagine:
            logger.info("[%s] PDF con %d pagine, inviate solo le prime %d", nome_file, len(pagine), max_pagine)
    elif estensione in ESTENSIONI_IMMAGINE:
        immagini = [Image.open(io.BytesIO(file_bytes))]
    else:
        raise ValueError(f"Formato file non supportato: '{estensione}' (usa PDF, PNG o JPG)")

    risultato = []
    for img in immagini:
        img = _ottimizza_immagine(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88, optimize=True)
        risultato.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
    return risultato

"""
core/preventivo_libero.py — "Altri Preventivi": stesso stile lettera degli altri due
documenti (non più a fasce colorate), calibrato sul modello fornito. Oggetto e
descrizione dei servizi sono liberi: è il documento con più libertà di contenuto.
"""

from dataclasses import dataclass
from datetime import date
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit as _a_capo
from reportlab.pdfgen import canvas

from core.preventivo import ALTEZZA, BOLD, ITAL, LOGO, REG, _Pagina, _data_it, _prezzo, _validita_it

MARGINE = 95.4
X_DX = 501.6

MODALITA_PAGAMENTO = [
    "Fatturazione unica", "Mensile", "Trimestrale", "Semestrale", "Annuale",
    "Anticipato", "50% all'accettazione del preventivo, 50% alla consegna della documentazione",
]


@dataclass
class DatiPreventivoLibero:
    cliente_azienda: bool = False
    cliente_ragione_sociale: str = ""
    cliente_cognome: str = ""
    cliente_nome: str = ""
    cliente_via: str = ""
    cliente_npa: str = ""
    cliente_comune: str = ""
    oggetto: str = ""           # testo libero dopo "Oggetto:" — es. "Preventivo per Servizi di Consulenza - ..."
    descrizione: str = ""       # ogni riga (Invio) diventa un punto elenco in "1. Servizi Offerti"
    prezzo: str = ""
    iva: str = "esente"
    modalita_pagamento: str = "Fatturazione unica"
    validita: date = None
    data: date = None

    def nome_cliente(self) -> str:
        if self.cliente_azienda:
            return self.cliente_ragione_sociale.strip()
        return f"{self.cliente_nome} {self.cliente_cognome}".strip()


def _firma(p: _Pagina, top: float) -> None:
    p.testo(MARGINE, top, "ATHENA ADVISORY GROUP SAGL", 8.3, BOLD)
    p.testo(MARGINE, top + 11.1, "Simone Sciancalepore", 8.3, ITAL)
    p.testo(MARGINE, top + 21.6, "+41(0)779534999", 8.3, ITAL)


def genera_preventivo_libero(d: DatiPreventivoLibero) -> bytes:
    d.data = d.data or date.today()
    d.validita = d.validita or date.today()
    suffisso_iva = "" if d.iva == "esente" else " + IVA"

    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    cv.setTitle(f"Preventivo {d.nome_cliente()}")
    cv.setAuthor("ATHENA ADVISORY GROUP SAGL")
    p = _Pagina(cv)

    cv.drawImage(str(LOGO), MARGINE + 1.2, ALTEZZA - 138.0, width=153.3, height=63.0, mask=None)
    p.testo(MARGINE, 142.8, "ATHENA ADVISORY GROUP SAGL", 8.3, BOLD)
    p.testo(MARGINE, 159.3, "Piazza F. Borromini 15", 8.3)
    p.testo(MARGINE, 171.8, "6816 Bissone", 8.3)
    p.testo(MARGINE, 184.2, "CHE-270.639.059", 8.3)

    p.testo(X_DX, 214.7, "Alla cortese attenzione di:", 8.3, BOLD, "right")
    p.testo(X_DX, 226.9, d.nome_cliente(), 8.3, REG, "right")
    if d.cliente_via:
        p.testo(X_DX, 239.1, d.cliente_via, 8.3, REG, "right")
    p.testo(X_DX, 251.3, f"{d.cliente_npa} {d.cliente_comune}".strip(), 8.3, REG, "right")

    p.testo(MARGINE, 286.2, f"Bissone, {_data_it(d.data)}", 8.3)

    for riga, testo in enumerate(_a_capo(f"Oggetto: {d.oggetto}", BOLD, 7.8, X_DX - MARGINE)):
        p.testo(MARGINE, 307.5 + riga * 9.0, testo, 7.8, BOLD)
    y = 307.5 + len(_a_capo(f"Oggetto: {d.oggetto}", BOLD, 7.8, X_DX - MARGINE)) * 9.0 + 21.6

    p.testo(MARGINE, y, "Egregi Signori,", 8.3)
    y += 21.3
    for riga, testo in enumerate(_a_capo(
        "In riferimento alla Vostra richiesta, siamo lieti di presentarVi la nostra proposta per i servizi "
        "di seguito descritti.", REG, 8.3, X_DX - MARGINE,
    )):
        p.testo(MARGINE, y + riga * 11.0, testo, 8.3)
        y += 11.0
    y += 21.3
    p.testo(MARGINE, y, "Di seguito, i servizi offerti e le relative opzioni di preventivo:", 7.8, ITAL)
    y += 32.0

    p.testo(MARGINE, y, "1. Servizi Offerti", 8.4, BOLD)
    y += 33.0
    righe_servizi = [r for r in d.descrizione.strip().split("\n") if r.strip()] or ["Servizi di consulenza come da accordi."]
    for voce in righe_servizi:
        for riga, testo in enumerate(_a_capo(f"- {voce}", REG, 8.3, X_DX - MARGINE)):
            p.testo(MARGINE, y + riga * 8.2, testo, 8.3)
        y += max(1, len(_a_capo(f"- {voce}", REG, 8.3, X_DX - MARGINE))) * 8.2 + 13.2

    y += 11.0
    p.testo(MARGINE, y, "2. Preventivo", 8.4, BOLD)
    y += 22.5
    for riga, testo in enumerate(_a_capo(
        f"Descrizione: Gestione completa dei servizi sopraelencati per {d.nome_cliente()}", REG, 8.3, X_DX - MARGINE,
    )):
        p.testo(MARGINE, y + riga * 10.5, testo, 8.3)
        y += 10.5
    y += 10.5
    p.testo(MARGINE, y, f"Importo: CHF {_prezzo(d.prezzo)}{suffisso_iva}", 8.3)
    y += 10.5
    p.testo(MARGINE, y, f"Modalità di Pagamento: {d.modalita_pagamento}", 8.3)

    y += 31.5
    p.testo(MARGINE, y, f"Validità del Preventivo: Fino al {_validita_it(d.validita)}.", 8.3)
    y += 20.8
    p.testo(MARGINE, y, "Cordiali saluti,", 8.3)
    _firma(p, max(y + 31.8, 757.7))

    cv.showPage()
    cv.save()
    return buf.getvalue()

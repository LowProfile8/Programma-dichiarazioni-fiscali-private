"""
core/preventivo_libero.py — preventivo "Altro": nessun modello fornito, più libertà di
contenuto (persona fisica o azienda, titolo e descrizione a piacere). Disegno pensato per
restare SEMPRE su una pagina, senza grandi spazi bianchi: stesso linguaggio grafico delle
fatture (fasce azzurre con etichetta) unito all'intestazione dei preventivi.
"""

from dataclasses import dataclass, field
from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfgen import canvas

from core.preventivo import ALTEZZA, BOLD, ITAL, LOGO, REG, _Pagina, _data_it, _prezzo, _validita_it

MARGINE = 52.4
ACCENTO = "#4BA3F7"
BENEFICIARIO = "Athena Advisory Group Sagl"
BENEFICIARIO_INDIRIZZO = "Piazza F. Borromini 15"
BENEFICIARIO_NPA_COMUNE = "6816 Bissone (CH)"
BENEFICIARIO_UID = "CHE-270.639.059"

MODALITA_PAGAMENTO = [
    "Fatturazione unica", "Mensile", "Trimestrale", "Semestrale", "Annuale",
    "Anticipato", "50% acconto, 50% alla consegna",
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
    titolo: str = ""
    descrizione: str = ""
    prezzo: str = ""
    iva: str = "esente"
    modalita_pagamento: str = "Fatturazione unica"
    validita: date = None
    data: date = None

    def nome_cliente(self) -> str:
        if self.cliente_azienda:
            return self.cliente_ragione_sociale.strip()
        return f"{self.cliente_nome} {self.cliente_cognome}".strip()


def _numero(testo: str) -> float:
    t = (testo or "").strip().replace("'", "").replace("’", "").replace(" ", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return 0.0


def _barra(cv, top: float, titolo: str) -> float:
    altezza = 14.5
    cv.setFillColorRGB(0.906, 0.941, 0.980)
    cv.roundRect(MARGINE, ALTEZZA - (top + altezza), 542.5 - MARGINE, altezza, 5, fill=1, stroke=0)
    cv.setFillColorRGB(0.10, 0.25, 0.55)
    cv.setFont(BOLD, 7.4)
    cv.drawString(MARGINE + 6, ALTEZZA - (top + 10.4), titolo.upper())
    cv.setFillColorRGB(0, 0, 0)
    return top + altezza + 12.0


def genera_preventivo_libero(d: DatiPreventivoLibero) -> bytes:
    d.data = d.data or date.today()
    d.validita = d.validita or date.today()
    prezzo_num = _numero(d.prezzo)
    suffisso_iva = "" if d.iva == "esente" else " + IVA"

    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    cv.setTitle(f"Preventivo {d.nome_cliente()}")
    cv.setAuthor(BENEFICIARIO)
    p = _Pagina(cv)

    cv.drawImage(str(LOGO), 53.6, ALTEZZA - 122.8, width=206.5 - 53.6, height=63.0, mask=None)
    p.testo(MARGINE, 129.7, "ATHENA ADVISORY GROUP SAGL", 8.3, BOLD)
    p.testo(MARGINE, 142.3, BENEFICIARIO_INDIRIZZO, 8.3)
    p.testo(MARGINE, 154.9, BENEFICIARIO_NPA_COMUNE, 8.3)
    p.testo(MARGINE, 167.5, BENEFICIARIO_UID, 8.3)
    p.testo(542.5, 142.3, "PREVENTIVO", 15.5, BOLD, "right")
    p.testo(542.5, 160.5, f"Lugano, {_data_it(d.data)}", 8.3, REG, "right")

    y = _barra(cv, 189.0, "Destinatario")
    p.testo(MARGINE, y, d.nome_cliente(), 8.6, BOLD)
    if d.cliente_via:
        p.testo(MARGINE, y + 12.6, d.cliente_via, 8.3)
    p.testo(MARGINE, y + 25.2, f"{d.cliente_npa} {d.cliente_comune}".strip(), 8.3)

    y = _barra(cv, y + 46.0, "Prestazione")
    stile_cella = ParagraphStyle("cella_prev", fontName="Helvetica", fontSize=8.3, leading=11.5)
    righe_descrizione = [f"<b>{d.titolo or 'Prestazione'}</b>"]
    if d.descrizione.strip():
        righe_descrizione.extend(d.descrizione.strip().split("\n"))
    cella = Paragraph("<br/>".join(righe_descrizione), stile_cella)
    dati_tabella = [["Descrizione", "Importo (CHF)"], [cella, _prezzo(d.prezzo) + suffisso_iva]]
    tabella = Table(dati_tabella, colWidths=[370, 120])
    tabella.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.3),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.black),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    larghezza, altezza_tab = tabella.wrapOn(cv, 490, 400)
    tabella.drawOn(cv, MARGINE, ALTEZZA - y - altezza_tab)
    y += altezza_tab

    y = _barra(cv, y + 22.0, "Condizioni")
    p.testo(MARGINE, y, "Modalità di pagamento", 7.6, BOLD)
    p.testo(MARGINE, y + 12.2, d.modalita_pagamento, 8.3)
    p.testo(300.0, y, "Validità del preventivo", 7.6, BOLD)
    p.testo(300.0, y + 12.2, f"Fino al {_validita_it(d.validita)}", 8.3)

    y += 42.0
    p.testo(MARGINE, y, "Cordiali saluti,", 8.3)
    p.testo(MARGINE, y + 24.0, "ATHENA ADVISORY GROUP SAGL", 8.3, BOLD)
    p.testo(MARGINE, y + 35.2, "Simone Sciancalepore", 8.3, ITAL)
    p.testo(MARGINE, y + 46.4, "+41(0)779534999", 8.3, ITAL)

    cv.showPage()
    cv.save()
    return buf.getvalue()

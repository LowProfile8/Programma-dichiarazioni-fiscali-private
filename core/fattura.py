"""
core/fattura.py — fattura per i servizi fiduciari (1 pagina).

Stesso stile del preventivo (stesso logo, stessi font, stessa intestazione
mittente): cambia il corpo, organizzato come una vera fattura — cliente,
prestazione, importo/IVA/totale, termine di pagamento, dati per il bonifico.

I dati bancari sono quelli reali di Athena Advisory Group Sagl (dalle
fatture già emesse in passato, conservate nel Drive dello studio).
"""

import re
from dataclasses import dataclass
from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfgen import canvas

from core.preventivo import ALTEZZA, BOLD, ITAL, LOGO, REG, _Pagina, _data_it

# ── Dati fissi dello studio (da fatture reali già emesse) ──────────────
BENEFICIARIO = "Athena Advisory Group Sagl"
BENEFICIARIO_INDIRIZZO = "Piazza F. Borromini 15"
BENEFICIARIO_NPA_COMUNE = "6816 Bissone (CH)"
BENEFICIARIO_UID = "CHE-270.639.059"
BANCA_NOME = "UBS AG"
BANCA_IBAN = "CH49 0020 4204 2276 8701 Z"
BANCA_BIC = "UBSWCHZH80A"

ALIQUOTE_IVA = {"esente": 0.0, "8.1": 0.081, "2.5": 0.025}
TERMINI_PAGAMENTO = ["A vista", "1 settimana", "2 settimane", "1 mese", "60 giorni", "Altro"]


@dataclass
class DatiFattura:
    cliente_azienda: bool = False
    cliente_ragione_sociale: str = ""
    cliente_cognome: str = ""
    cliente_nome: str = ""
    cliente_via: str = ""
    cliente_npa: str = ""
    cliente_comune: str = ""

    titolo: str = ""            # es. "Prestazioni Settembre 2025"
    descrizione: str = ""       # facoltativa, testo libero
    periodo: str = ""           # facoltativo, es. "01.09.2025-30.09.2025"
    data: date = None
    numero: str = ""
    prezzo: str = ""            # importo NETTO (prima dell'IVA)
    iva: str = "esente"         # 'esente' | '8.1' | '2.5'
    termine_pagamento: str = "15 giorni"

    def nome_cliente(self) -> str:
        if self.cliente_azienda:
            return self.cliente_ragione_sociale.strip()
        return f"{self.cliente_nome} {self.cliente_cognome}".strip()


def prime_tre_consonanti(testo: str) -> str:
    """'Fermata Sagl' -> 'FRM' (le prime tre consonanti, maiuscole).
    Se il testo ne ha meno di tre, usa quello che c'è; se è vuoto, 'CLI'."""
    vocali = set("aeiouAEIOUàèéìòùÀÈÉÌÒÙ")
    consonanti = [c for c in testo if c.isalpha() and c not in vocali]
    sigla = "".join(consonanti[:3]).upper()
    if not sigla:
        lettere = [c for c in testo if c.isalpha()][:3]
        sigla = "".join(lettere).upper()
    return sigla or "CLI"


def suggerisci_numero_fattura(nome_cliente: str, oggi: date) -> str:
    """AAAAMMGG-XXX, con XXX le prime tre consonanti del nome del cliente."""
    return f"{oggi:%Y%m%d}-{prime_tre_consonanti(nome_cliente)}"


def _numero(testo: str) -> float:
    t = (testo or "").strip().replace("'", "").replace("’", "").replace(" ", "").replace(",", ".")
    pulito = re.sub(r"[^0-9.\-]", "", t)
    try:
        return float(pulito)
    except ValueError:
        return 0.0


def _fr(x: float) -> str:
    return f"{x:,.2f}".replace(",", "'")


def calcola_importi(d: DatiFattura) -> dict:
    netto = _numero(d.prezzo)
    aliquota = ALIQUOTE_IVA.get(d.iva, 0.0)
    iva_importo = netto * aliquota
    return {"netto": netto, "aliquota": aliquota, "iva_importo": iva_importo, "totale": netto + iva_importo}


def _firma(p: _Pagina, top: float) -> None:
    p.testo(52.4, top, "ATHENA ADVISORY GROUP SAGL", 8.3, BOLD)
    p.testo(52.4, top + 12.3, "Simone Sciancalepore", 8.3, ITAL)
    p.testo(52.4, top + 24.6, "+41(0)779534999", 8.3, ITAL)


def _barra(cv, top: float, titolo: str) -> float:
    """Una piccola fascia azzurra con l'etichetta della sezione (MAIUSCOLO), per separare
    chiaramente i gruppi della fattura. Restituisce la coordinata "top" da cui continuare."""
    altezza = 14.5
    cv.setFillColorRGB(0.906, 0.941, 0.980)
    cv.rect(52.4, ALTEZZA - (top + altezza), 542.5 - 52.4, altezza, fill=1, stroke=0)
    cv.setFillColorRGB(0.10, 0.25, 0.55)
    cv.setFont(BOLD, 7.4)
    cv.drawString(52.4 + 6, ALTEZZA - (top + 10.4), titolo.upper())
    cv.setFillColorRGB(0, 0, 0)
    return top + altezza + 12.0


def genera_fattura(d: DatiFattura) -> bytes:
    d.data = d.data or date.today()
    importi = calcola_importi(d)

    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    cv.setTitle(f"Fattura {d.numero}".strip())
    cv.setAuthor(BENEFICIARIO)
    p = _Pagina(cv)

    # ── intestazione mittente (stesso stile del preventivo) ──
    cv.drawImage(str(LOGO), 53.6, ALTEZZA - 122.8, width=206.5 - 53.6, height=63.0, mask=None)
    p.testo(52.4, 129.7, "ATHENA ADVISORY GROUP SAGL", 8.3, BOLD)
    p.testo(52.4, 142.3, BENEFICIARIO_INDIRIZZO, 8.3)
    p.testo(52.4, 154.9, BENEFICIARIO_NPA_COMUNE, 8.3)
    p.testo(52.4, 167.5, BENEFICIARIO_UID, 8.3)

    # ── titolo del documento, ben visibile ──
    p.testo(542.5, 142.3, "FATTURA", 15.5, BOLD, "right")
    p.testo(542.5, 160.5, f"N° {d.numero}", 9.5, REG, "right")

    # ── destinatario ──
    y = _barra(cv, 189.0, "Destinatario")
    x_dx = 542.5
    p.testo(52.4, y, d.nome_cliente(), 8.6, BOLD)
    if d.cliente_via:
        p.testo(52.4, y + 12.6, d.cliente_via, 8.3)
    p.testo(52.4, y + 25.2, f"{d.cliente_npa} {d.cliente_comune}".strip(), 8.3)

    # ── dettagli della fattura: data, periodo, termine di pagamento ──
    y = _barra(cv, y + 46.0, "Dettagli della fattura")
    col2 = 300.0
    p.testo(52.4, y, "Luogo e data", 7.6, BOLD, )
    p.testo(52.4, y + 12.2, f"Lugano, {_data_it(d.data)}", 8.3)
    if d.periodo:
        p.testo(col2, y, "Periodo di riferimento", 7.6, BOLD)
        p.testo(col2, y + 12.2, d.periodo, 8.3)
    y += 30.0
    p.testo(52.4, y, "Termine di pagamento", 7.6, BOLD)
    p.testo(52.4, y + 12.2, d.termine_pagamento, 8.3)

    # ── tabella della prestazione ──
    y = _barra(cv, y + 34.0, "Prestazione")
    intestazioni = ["Descrizione", "Periodo", "Importo (CHF)"]
    stile_cella = ParagraphStyle("cella_fattura", fontName="Helvetica", fontSize=8.3, leading=11.5)
    righe_descrizione = [f"<b>{d.titolo or 'Prestazioni'}</b>"]
    if d.descrizione.strip():
        righe_descrizione.append(d.descrizione.strip())
    riga_descrizione = Paragraph("<br/>".join(righe_descrizione), stile_cella)
    dati = [
        intestazioni,
        [riga_descrizione, d.periodo or "", _fr(importi["netto"])],
    ]
    if importi["aliquota"] > 0:
        dati.append(["", f"IVA {d.iva}%", _fr(importi["iva_importo"])])
    else:
        dati.append(["", "IVA", "Esente"])
    dati.append(["", "Totale CHF", _fr(importi["totale"])])

    tabella = Table(dati, colWidths=[266, 120, 104])
    tabella.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.3),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.black),
        ("LINEABOVE", (0, -1), (-1, -1), 0.7, colors.black),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    larghezza, altezza_tab = tabella.wrapOn(cv, 490, 200)
    tabella.drawOn(cv, 52.4, ALTEZZA - y - altezza_tab)
    y += altezza_tab

    # ── coordinate per il pagamento ──
    y = _barra(cv, y + 26.0, "Coordinate per il pagamento")
    p.testo(52.4, y, "Beneficiario", 7.6, BOLD)
    p.testo(52.4, y + 12.2, BENEFICIARIO, 8.3)
    p.testo(52.4, y + 24.4, f"{BENEFICIARIO_INDIRIZZO} - {BENEFICIARIO_NPA_COMUNE}", 7.8)
    p.testo(52.4, y + 35.5, f"Numero d'identificazione: {BENEFICIARIO_UID}", 7.8)
    p.testo(col2, y, "Istituto bancario", 7.6, BOLD)
    p.testo(col2, y + 12.2, BANCA_NOME, 8.3)
    y += 54.0
    p.testo(52.4, y, "IBAN per bonifico", 7.6, BOLD)
    p.testo(52.4, y + 12.2, BANCA_IBAN, 8.3)
    p.testo(col2, y, "BIC / SWIFT", 7.6, BOLD)
    p.testo(col2, y + 12.2, BANCA_BIC, 8.3)

    _firma(p, 699.1)

    cv.showPage()
    cv.save()
    return buf.getvalue()

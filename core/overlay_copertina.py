"""
core/overlay_copertina.py — prima pagina dell'output («Dati riassuntivi con
codice a barre») e numerazione delle pagine.

La pagina riassuntiva va firmata dal contribuente (e dal coniuge) e allegata
obbligatoriamente all'invio della dichiarazione. È ricostruita in vettoriale
sul modello della stampa di eTax (stesse posizioni, stessi font).

Il codice a barre in alto a destra (Code 128) è stato verificato contro tre
dichiarazioni eTax reali: codifica solo "numero registro + periodo + anno",
cioè dati già scritti in chiaro sulla stessa pagina — non un identificativo
segreto. Compare solo se è stato inserito un numero di registro (facoltativo,
assegnato dal Cantone al contribuente): senza quel numero il codice a barre
non verrebbe accettato comunque, quindi in quel caso la pagina resta come
prima, senza barcode.
"""

from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.graphics.barcode.code128 import Code128
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from core.calcoli import calcolo_mod1
from core.celle import ALTEZZA_A4, FONT, FONT_B, Scrittore, fmt_spazio

NERO = Color(0, 0, 0)
GRIGIO_BARRA = Color(0.8, 0.8, 0.8)
GRIGIO_BOX = Color(0.88235, 0.88235, 0.88235)
BLU = Color(0.01176, 0.41961, 0.71373)
RAPPORTO_BASE = 0.793   # linea di base = top + 0.793 × corpo (Helvetica, come nelle stampe di eTax)


def codice_registro(numero: str, anno: int) -> str:
    """Contenuto del Code 128: numero registro + periodo + anno."""
    yy = str(anno)[2:]
    return f"{numero}{yy}0101{yy}1231{anno}"


def _t(cv, x: float, top: float, s: str, size: float = 7.7, bold: bool = False,
       allinea: str = "left", colore=NERO) -> None:
    """Testo con la convenzione di eTax: `top` = bordo superiore del testo."""
    if not s:
        return
    font = FONT_B if bold else FONT
    larghezza = stringWidth(s, font, size)
    x_sx = x - larghezza if allinea == "right" else x
    cv.setFillColor(colore)
    cv.setFont(font, size)
    cv.drawString(x_sx, ALTEZZA_A4 - (top + RAPPORTO_BASE * size), s)


def _linea(cv, x0: float, x1: float, top: float) -> None:
    cv.setStrokeColor(NERO)
    cv.setLineWidth(0.4)
    cv.line(x0, ALTEZZA_A4 - top, x1, ALTEZZA_A4 - top)


def _rett(cv, x0: float, top: float, x1: float, bottom: float, colore) -> None:
    cv.setFillColor(colore)
    cv.rect(x0, ALTEZZA_A4 - bottom, x1 - x0, bottom - top, fill=1, stroke=0)


def pagina_copertina(writer: PdfWriter, d) -> None:
    c = d.contribuente
    m1 = calcolo_mod1(d)
    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)

    # ── intestazione ─────────────────────────────────────────────────
    cv.saveState()
    tracciato = cv.beginPath()
    tracciato.rect(28.6, ALTEZZA_A4 - 87.4, 96.0, 52.8)
    cv.clipPath(tracciato, stroke=0, fill=0)
    cv.linearGradient(28.6, 0, 124.6, 0, (Color(0.18, 0.42, 0.70), Color(1, 1, 1)), extend=False)
    cv.restoreState()
    _t(cv, 33.4, 74.6, "Cantone Ticino", colore=Color(1, 1, 1))
    _rett(cv, 471.7, 34.6, 549.5, 61.4, BLU)
    _t(cv, 489.5, 48.4, "eTax Ticino", bold=True, colore=Color(1, 1, 1))
    _t(cv, 485.0, 65.0, str(d.anno_fiscale), size=23.0, bold=True)
    _t(cv, 151.9, 35.6, "Dichiarazione d'imposta", size=15.4, bold=True)
    _t(cv, 151.9, 53.3, "delle persone fisiche", size=15.4, bold=True)
    for top in (34.7, 88.0):
        _linea(cv, 151.9, 549.5, top)
    _t(cv, 152.1, 92.9, "Dati riassuntivi con codice a barre", size=9.6, bold=True)
    for top in (105.9, 122.2):
        _linea(cv, 151.9, 549.5, top)

    # ── numero registro, comune, codice a barre ─────────────────────
    _t(cv, 155.9, 110.9, "Numero registro")
    _t(cv, 375.0 - stringWidth("Comune", FONT, 7.7), 110.7, "Comune")
    _t(cv, 381.5, 110.7, c.domicilio)
    if d.numero_controllo:
        _t(cv, 227.9, 111.4, d.numero_controllo)

        # Codice a barre (Code 128): stessa formula verificata sulle dichiarazioni eTax reali
        # — numero registro + periodo d'assoggettamento + anno fiscale, 26 cifre.
        valore_barcode = codice_registro(d.numero_controllo, d.anno_fiscale)
        barra = Code128(valore_barcode, barHeight=24.0, barWidth=0.66)
        x_barra = 549.5 - barra.width
        barra.drawOn(cv, x_barra, ALTEZZA_A4 - (136.0 + 24.0))
        _t(cv, 549.5, 167.7, valore_barcode, size=6.6, allinea="right")

    # ── nomi e indirizzo ────────────────────────────────────────────
    _t(cv, 156.9, 132.5, f"{c.cognome}, {c.nome}".strip(", "))
    if c.coniuge:
        _t(cv, 156.9, 146.3, f"{c.coniuge.cognome}, {c.coniuge.nome}".strip(", "))
    _t(cv, 156.9, 160.2, c.indirizzo)
    _t(cv, 156.9, 172.8, f"{c.npa} {c.domicilio}".strip())

    # ── periodo d'assoggettamento ───────────────────────────────────
    _t(cv, 37.0, 145.6, "Periodo d'assoggettamento:")
    _t(cv, 37.0, 160.5, "dal")
    _t(cv, 57.2, 160.5, f"01.01.{d.anno_fiscale}")
    _t(cv, 37.0, 173.5, "al")
    _t(cv, 57.2, 173.5, f"31.12.{d.anno_fiscale}")
    _linea(cv, 51.8, 123.8, 183.5)

    # ── contatti ────────────────────────────────────────────────────
    for top in (189.8, 201.7):
        _linea(cv, 151.9, 549.5, top)
    _t(cv, 155.9, 191.6, "Per informazioni complementari rivolgersi a:")
    _t(cv, 155.9, 205.4, "Telefono:")
    _t(cv, 219.3, 205.3, c.telefono)
    _t(cv, 346.0, 205.4, "E-mail:")
    _t(cv, 412.2, 204.7, c.email)
    _t(cv, 155.9, 218.2, "La rappresentanza contrattuale è ammessa unicamente in presenza di una procura scritta.")

    # ── dati riassuntivi ────────────────────────────────────────────
    _rett(cv, 37.0, 228.7, 549.5, 240.0, GRIGIO_BARRA)
    _linea(cv, 37.0, 549.5, 228.6)
    _linea(cv, 37.0, 549.5, 240.1)
    _t(cv, 37.0, 231.1, "Dati riassuntivi", bold=True)
    _rett(cv, 457.1, 240.2, 549.5, 295.7, GRIGIO_BOX)
    cv.setStrokeColor(NERO)
    cv.setLineWidth(0.4)
    cv.line(457.2, ALTEZZA_A4 - 240.2, 457.2, ALTEZZA_A4 - 295.9)
    _linea(cv, 457.1, 549.5, 251.6)
    _t(cv, 498.5, 242.7, "Fr.")
    _linea(cv, 250.0, 549.5, 265.2)
    _linea(cv, 250.0, 549.5, 293.8)
    _t(cv, 250.0, 253.8, "Reddito imponibile:")
    _t(cv, 250.0, 269.3, "Sostanza imponibile:")
    _t(cv, 250.0, 284.4, "Pretesa di rimborso dell'imposta preventiva:")
    _t(cv, 544.5, 255.0, fmt_spazio(m1["deduzioni"][264]), allinea="right")
    _t(cv, 544.5, 269.4, fmt_spazio(m1["sostanza"][340]), allinea="right")
    _t(cv, 544.5, 284.5, f"{m1['recupero_ip']:,.2f}".replace(",", " "), allinea="right")

    # ── firme ───────────────────────────────────────────────────────
    puntini = "." * 45
    _t(cv, 37.0, 330.5, f"Data: {puntini}", bold=True)
    _t(cv, 250.0, 330.5, f"Firma: {puntini}", bold=True)
    _t(cv, 394.4, 328.3, puntini, bold=True)
    _t(cv, 323.7 - stringWidth("Contribuente", FONT_B, 7.7), 341.1, "Contribuente", bold=True)
    _t(cv, 394.4, 341.1, "Coniuge/partner registrato", bold=True)

    # ── avvertenza ──────────────────────────────────────────────────
    _rett(cv, 37.0, 354.1, 549.5, 365.4, GRIGIO_BARRA)
    _linea(cv, 37.0, 549.5, 353.9)
    _linea(cv, 37.0, 549.5, 365.5)
    _t(cv, 37.0, 356.5, "Codice a barre", bold=True)
    _t(cv, 37.0, 367.3, "Il presente modulo, debitamente firmato, è obbligatoriamente da ritornare inserito nel modulo 1", size=8.6, bold=True)
    _t(cv, 37.0, 377.6, "(dichiarazione d'imposta originale) con tutti i moduli stampati tramite eTax e gli allegati di supporto.", size=8.6, bold=True)
    _t(cv, 37.0, 390.2, "In caso di mancata trasmissione l'autorità fiscale si riserva la possibilità di considerare la dichiarazione come non rientrata e di ritornarla al")
    _t(cv, 37.0, 400.1, "contribuente per completamento.")

    cv.showPage()
    cv.save()
    buf.seek(0)
    writer.add_page(PdfReader(buf).pages[0])


def numera_pagine(pdf_bytes: bytes) -> bytes:
    """Aggiunge «Pagina X / N» in basso a destra di ogni pagina della dichiarazione."""
    lettore = PdfReader(BytesIO(pdf_bytes))
    n = len(lettore.pages)
    scrittore = PdfWriter()
    for i, pagina in enumerate(lettore.pages, start=1):
        rotazione = int(pagina.get("/Rotate", 0) or 0) % 360
        larghezza, altezza = float(pagina.mediabox.width), float(pagina.mediabox.height)
        buf = BytesIO()
        cv = canvas.Canvas(buf, pagesize=(larghezza, altezza))
        scr = Scrittore(cv, rotata=(rotazione == 90), altezza=altezza)
        if rotazione == 90:      # tabella del Modulo 2, in orizzontale: angolo in basso a destra della vista
            scr.testo(828.0, 583.0, f"Pagina {i} / {n}", "right", FONT, 7.7)
        else:
            scr.testo(560.0, 819.0, f"Pagina {i} / {n}", "right", FONT, 7.7)
        cv.showPage()
        cv.save()
        buf.seek(0)
        pagina.merge_page(PdfReader(buf).pages[0])
        scrittore.add_page(pagina)
    out = BytesIO()
    scrittore.write(out)
    return out.getvalue()

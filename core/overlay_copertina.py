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
    x_sx = x - larghezza if allinea == "right" else (x - larghezza / 2 if allinea == "center" else x)
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
        # Misure rilevate su una stampa eTax reale: barre da x=365.6, alte 28.8 (da top 141.6),
        # modulo 1.0 (178 pt), cifre Helvetica 8 centrate sotto le barre (top 174.7).
        barra = Code128(valore_barcode, barHeight=28.8, barWidth=1.0, quiet=0)
        barra.drawOn(cv, 365.6, ALTEZZA_A4 - (141.6 + 28.8))
        _t(cv, 365.6 + barra.width / 2, 174.7, valore_barcode, size=8.0, allinea="center")

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


def _disegna_codice_pagina(cv, rotata: bool, altezza_visiva: float, codice: str, copri_originale: bool) -> None:
    """Piccolo Code 128 in basso a sinistra, con le cifre sotto, come nelle stampe di eTax
    (verificato su tre dichiarazioni reali: barre da x=16, alte 20, larghe 123, cifre Helvetica 8).
    Sui moduli ufficiali vuoti scaricati dal sito del Cantone c'è già una versione più piccola e
    senza cifre, con terminazione «011» invece di «761» (stampa «da compilare» invece che
    compilata): la ricopriamo con un rettangolo bianco e la sostituiamo con quella della stampa eTax."""
    # origine locale: sulla riga di base delle barre (top visivo 826 su pagina A4 in verticale)
    top_base = 826.0 - (249.6 if rotata else 0.0)
    cv.saveState()
    if rotata:
        cv.translate(top_base, 0)
        cv.rotate(90)
    else:
        cv.translate(0, altezza_visiva - top_base)
    if copri_originale:
        cv.setFillColorRGB(1, 1, 1)
        cv.setStrokeColorRGB(1, 1, 1)
        cv.rect(10.0, -5.0, 128.0, 27.0, fill=1, stroke=0)
    cv.setFillColorRGB(0, 0, 0)
    Code128(codice, barHeight=20.0, barWidth=1.0, quiet=0).drawOn(cv, 16.0, 0.0)
    cv.setFont("Helvetica", 8.0)
    cv.drawString(48.6, -10.6, codice)
    cv.restoreState()


def numera_pagine(pdf_bytes: bytes, d=None, codici=None, stile_online: bool = False) -> bytes:
    """Piè di pagina della dichiarazione.

    Stampa cartacea (predefinita): i moduli 2-8 sono i fogli ufficiali del Cantone scaricabili
    dal sito e restano com'erano (il loro piccolo codice a barre non ha cifre, niente data/ora,
    niente numero di pagina). Le pagine «personali» — Modulo 1, allegato veicoli, note — hanno
    invece, come nelle stampe eTax: piccolo codice a barre CON le cifre, nome e numero di registro
    (tranne sulla prima pagina del Modulo 1, che li mostra già nel corpo) e «Pagina X / N».
    Senza data e ora, che compaiono solo nella stampa online.

    stile_online=True: tutto come la stampa online di eTax (copertina inclusa) — data e ora,
    numero di pagina, richiamo nome/registro dalla pagina 3, codici su ogni pagina."""
    from datetime import datetime as _dt

    lettore = PdfReader(BytesIO(pdf_bytes))
    n = len(lettore.pages)
    timbro = _dt.now().strftime("%d.%m.%Y %H:%M:%S")

    nome_contribuente = ""
    numero_registro = ""
    if d is not None:
        c = d.contribuente
        if c.cognome or c.nome:
            nome_contribuente = f"{c.cognome}, {c.nome}".strip(", ")
        numero_registro = d.numero_controllo or ""

    scrittore = PdfWriter()
    for i, pagina in enumerate(lettore.pages, start=1):
        rotazione = int(pagina.get("/Rotate", 0) or 0) % 360
        larghezza, altezza = float(pagina.mediabox.width), float(pagina.mediabox.height)
        buf = BytesIO()
        cv = canvas.Canvas(buf, pagesize=(larghezza, altezza))
        scr = Scrittore(cv, rotata=(rotazione == 90), altezza=altezza)
        prefisso, nn, copri = (codici[i - 1] if codici and i - 1 < len(codici) else (None, 0, False))
        personale = prefisso in ("0901", "0101", "4901")
        if not stile_online and not personale:
            # foglio ufficiale del Cantone: lo lasciamo identico all'originale
            cv.showPage(); cv.save(); buf.seek(0)
            scrittore.add_page(pagina)
            continue
        # Posizioni misurate su tre stampe eTax reali (font Helvetica 8, bordi destri a 564 e 578;
        # pagina ruotata del Modulo 2: 784 e 798). C = scarto fra il bordo alto del testo (come lo
        # misura un lettore PDF) e la riga di base su cui scrive reportlab.
        C = 6.5
        if rotazione == 90:
            x_data, x_pag, x_nome = 784.0, 798.0, 341.0
            t_data, t_pag, t_nome, t_reg = 557.5 + C, 567.9 + C, 557.4 + C, 568.6 + C
        else:
            x_data, x_pag, x_nome = 564.0, 578.0, 241.0
            t_data, t_pag, t_nome, t_reg = 806.8 + C, 817.5 + C, 806.4 + C, 818.2 + C
        if stile_online:
            scr.testo(x_data, t_data, timbro, "right", FONT, 8.0)
        scr.testo(x_pag, t_pag, f"Pagina {i} / {n}", "right", FONT, 8.0)
        # nome e registro: non sulla copertina né sulla prima pagina del Modulo 1 (li hanno già nel corpo)
        mostra_nome = (i > 2) if stile_online else not (prefisso == "0101" and nn == 1)
        if mostra_nome and nome_contribuente:
            scr.testo(x_nome, t_nome, nome_contribuente, "left", FONT, 8.0)
            if numero_registro:
                scr.testo(x_nome, t_reg, numero_registro, "left", FONT, 8.0)
        if prefisso and d is not None:
            yy = str(d.anno_fiscale)[2:]
            if prefisso == "0101" and nn <= 4:
                # Le 4 pagine del Modulo 1 (ricostruite da immagini) non hanno la riga nera di
                # chiusura sopra il piè di pagina che le stampe di eTax hanno su ogni modulo
                # (y=793.8, x da 14.2 a 581.1, spessore 2).
                cv.setLineWidth(2.0)
                cv.setStrokeColorRGB(0, 0, 0)
                cv.line(14.2, altezza - 793.8, 581.1, altezza - 793.8)
            _disegna_codice_pagina(
                cv, rotazione == 90, larghezza if rotazione == 90 else altezza,
                f"{prefisso}{yy}21{nn:02d}761", copri,
            )
        cv.showPage()
        cv.save()
        buf.seek(0)
        pagina.merge_page(PdfReader(buf).pages[0])
        scrittore.add_page(pagina)
    out = BytesIO()
    scrittore.write(out)
    return out.getvalue()

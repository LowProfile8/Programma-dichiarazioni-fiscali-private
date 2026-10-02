"""
core/overlay_mod1.py — Modulo 1 (4 pagine) e Modulo 2 pagina 1.

Il Modulo 1 non esiste in versione vuota scaricabile: gli sfondi sono
schermate pulite (assets/moduli_ufficiali/Mod1_pagina3..6.png, senza dati
personali né codice a barre). Le posizioni dei valori sono quelle usate da
eTax stesso nelle sue stampe (estratte dal PDF di una dichiarazione reale:
solo le coordinate, nessun dato): bordo destro a 562.4 pt per le cifre,
Helvetica 7.7 pt, stessa altezza della riga della cifra.

La pagina 1 del Modulo 2 (domande su eredità/donazioni) è un'immagine a
150 dpi del modulo vuoto; i riquadri sono stati rilevati dall'immagine.
"""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from core.calcoli import (
    calcolo_mod1, calcolo_mod2, calcolo_mod4, calcolo_veicoli, descrizione_veicolo, numero, valore_veicolo,
)
from core.celle import ALTEZZA_A4, FONT, FONT_B, Scrittore, fmt_spazio
from core.models import GenereAttivita

CARTELLA = Path(__file__).parent.parent / "assets" / "moduli_ufficiali"

TOP_A_BASE = 6.106      # baseline = top + 6.106 per Helvetica 7.7 (calibrato)
DIM = 7.7
X_VALORI = 562.4        # bordo destro dei valori nelle pagine 4-6


def _pagina_con_sfondo(nome_png: str, disegna) -> "PdfReader":
    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    cv.drawImage(str(CARTELLA / nome_png), 0, 0, width=A4[0], height=A4[1])
    disegna(Scrittore(cv))
    cv.showPage()
    cv.save()
    buf.seek(0)
    return PdfReader(buf)


def _cognome_nome(p, virgola: bool = True) -> str:
    if not (p.cognome or p.nome):
        return ""
    return f"{p.cognome}, {p.nome}" if virgola else f"{p.cognome} {p.nome}".strip()


def _data(d) -> str:
    return d.strftime("%d.%m.%Y") if d else ""


def _importo_2dec(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ")


def _testo_top(scr: Scrittore, x: float, top: float, s: str, allinea: str = "left", larghezza_max: float = None) -> None:
    """Testo con la convenzione di eTax: `top` = bordo superiore del testo in Helvetica 7.7."""
    if not s:
        return
    size = DIM
    if larghezza_max:
        while size > 5 and stringWidth(s, FONT, size) > larghezza_max:
            size -= 0.25
    scr.testo(x, top + TOP_A_BASE * (size / DIM), s, allinea, FONT, size)


# ══════════════════════════════════════════════════════════════════════
# Pagina 3 — dati personali
# ══════════════════════════════════════════════════════════════════════
_X_CONTRIB = 147.3
_X_CONIUGE = 363.3
_TOP_RIGHE = {"nome": 318.2, "nascita": 334.2, "stato": 350.3, "domicilio": 366.2,
              "professione": 383.6, "lavoro": 443.4, "accessoria": 458.7}

# caselle «Genere di attività»: (x0, top) della casella 5.7×5.7 pt
_GENERE = {
    "contrib": {
        GenereAttivita.DIPENDENTE: (147.3, 398.7), GenereAttivita.INDIPENDENTE: (215.4, 398.7),
        GenereAttivita.STUDENTE: (283.1, 399.0), GenereAttivita.PENSIONATO: (147.3, 408.3),
        GenereAttivita.ALTRO: (215.4, 408.3), GenereAttivita.BENEFICIARIO_PRESTAZIONI: (147.3, 417.7),
    },
    "coniuge": {
        GenereAttivita.DIPENDENTE: (360.6, 398.7), GenereAttivita.INDIPENDENTE: (428.3, 398.7),
        GenereAttivita.STUDENTE: (496.4, 398.7), GenereAttivita.PENSIONATO: (360.6, 408.3),
        GenereAttivita.ALTRO: (428.3, 408.3), GenereAttivita.BENEFICIARIO_PRESTAZIONI: (360.6, 418.0),
    },
}
_LATO_CASELLA = 5.7

_FIGLI_TOP = [550.0, 565.0, 580.0]
_FIGLI_X = {"nome": 30.1, "anno": 170.5}
_FIGLI_CASELLE = {
    "cura_si": 327.9, "cura_no": 346.3,
    "scuola_si": 360.6, "scuola_no": 378.7,
    "fuori_cantone": 428.3,
    "studi_accademici": 533.0,
}


def _x_in_casella(scr: Scrittore, x0: float, top: float) -> None:
    scr.x_in_box((x0, x0 + _LATO_CASELLA, top, top + _LATO_CASELLA), size=7.5)


def _blocco_persona(scr: Scrittore, p, x: float, con_stato: bool, stato_civile=None) -> None:
    _testo_top(scr, x, _TOP_RIGHE["nome"], _cognome_nome(p), larghezza_max=170)
    _testo_top(scr, x, _TOP_RIGHE["nascita"], _data(p.data_nascita))
    if con_stato and stato_civile:
        _testo_top(scr, x, _TOP_RIGHE["stato"], stato_civile.value, larghezza_max=170)
    _testo_top(scr, x, _TOP_RIGHE["domicilio"], p.domicilio, larghezza_max=170)
    _testo_top(scr, x, _TOP_RIGHE["professione"], p.professione, larghezza_max=170)
    _testo_top(scr, x, _TOP_RIGHE["lavoro"], p.luogo_lavoro, larghezza_max=170)
    _testo_top(scr, x, _TOP_RIGHE["accessoria"], p.attivita_accessoria, larghezza_max=170)


def _pagina3(scr: Scrittore, d) -> None:
    c = d.contribuente
    m1 = calcolo_mod1(d)

    # intestazione e finestra dell'indirizzo (contribuente, coniuge, [via], NPA e comune)
    if d.numero_controllo:
        _testo_top(scr, 212.5, 89.9, d.numero_controllo)
    _testo_top(scr, 395.9, 90.0, c.domicilio)
    if c.ufficio_tassazione:
        _testo_top(scr, 517.0, 90.8, c.ufficio_tassazione)
    _testo_top(scr, 339.6, 129.4, _cognome_nome(c), larghezza_max=200)
    if c.coniuge:
        _testo_top(scr, 339.6, 143.1, _cognome_nome(c.coniuge), larghezza_max=200)
    _testo_top(scr, 339.6, 156.3, c.indirizzo, larghezza_max=200)
    _testo_top(scr, 339.6, 169.7, f"{c.npa} {c.domicilio}".strip(), larghezza_max=200)
    _testo_top(scr, 184.9, 262.0, c.telefono)
    _testo_top(scr, 385.5, 261.3, c.email, larghezza_max=170)

    _blocco_persona(scr, c, _X_CONTRIB, True, c.stato_civile)
    for g in c.genere_attivita:
        if g in _GENERE["contrib"]:
            _x_in_casella(scr, *_GENERE["contrib"][g])
    if c.coniuge:
        _blocco_persona(scr, c.coniuge, _X_CONIUGE, False)
        for g in c.coniuge.genere_attivita:
            if g in _GENERE["coniuge"]:
                _x_in_casella(scr, *_GENERE["coniuge"][g])

    # figli (le prime 3 righe della tabella)
    for figlio, top in zip(d.figli, _FIGLI_TOP):
        _testo_top(scr, _FIGLI_X["nome"], top, figlio.nome, larghezza_max=110)
        if figlio.anno_nascita:
            _testo_top(scr, _FIGLI_X["anno"], top, str(figlio.anno_nascita))
            eta = d.anno_fiscale - figlio.anno_nascita
            if eta < 14:
                x = _FIGLI_CASELLE["cura_si"] if figlio.in_cura_da_terzi else _FIGLI_CASELLE["cura_no"]
                _x_in_casella(scr, x, top)
        if figlio.scuola_luogo == "stesso_comune":
            _x_in_casella(scr, _FIGLI_CASELLE["scuola_si"], top)
        elif figlio.scuola_luogo in ("stesso_cantone", "fuori_cantone"):
            _x_in_casella(scr, _FIGLI_CASELLE["scuola_no"], top)
            if figlio.scuola_luogo == "fuori_cantone":
                _x_in_casella(scr, _FIGLI_CASELLE["fuori_cantone"], top)
        if figlio.agli_studi:
            _x_in_casella(scr, _FIGLI_CASELLE["studi_accademici"], top)

    # informazioni complementari: affitto
    if d.abita_in_affitto and numero(d.pigione_annua_netta) > 0:
        _testo_top(scr, 239.0, 687.3, fmt_spazio(int(round(numero(d.pigione_annua_netta)))), "right")
        proprietario = ", ".join(x for x in (d.proprietario_nome.strip(), d.proprietario_indirizzo.strip()) if x)
        _testo_top(scr, 380.5, 684.6, proprietario, larghezza_max=178)

    # rimborso imposta preventiva (cifra 999)
    _testo_top(scr, 537.8, 733.5, _importo_2dec(m1["recupero_ip"]), "right")   # eTax scrive «0.00» anche se zero


# ══════════════════════════════════════════════════════════════════════
# Pagine 4-5-6 — redditi, deduzioni, sostanza
# ══════════════════════════════════════════════════════════════════════
_TOP_P4 = {100: 74.0, 102: 88.9, 104: 103.9, 106: 118.9, 150: 475.4, 720: 519.4, 735: 534.8, 736: 550.3,
           738: 565.7, 730: 581.2, 774: 596.6, 178: 715.9}
_TOP_P5 = {438: 73.3, 488: 88.3, 208: 175.3, 210: 190.3, 600: 205.3, 214: 233.8, 500: 248.8, 230: 426.4, 236: 441.3,
           17: 485.8, 18: 500.8, 240: 515.5, 253: 530.5, 241: 545.4, 242: 620.3,
           248: 663.7, 256: 708.8, 264: 738.7}
_TOP_P6 = {300: 72.6, 306: 212.7, 308: 241.3, 740: 256.0, 322: 330.2, 504: 358.8, 330: 388.7, 334: 417.3, 336: 432.2, 340: 447.2}


def _valori_colonna(scr: Scrittore, tops: dict, valori: dict) -> None:
    for cifra, top in tops.items():
        v = valori.get(cifra, 0)
        if v:
            _testo_top(scr, X_VALORI, top, fmt_spazio(int(v)), "right")


def _piede(scr: Scrittore, d) -> None:
    """Come nelle stampe di eTax: nome del contribuente e numero di registro in fondo alle pagine 4-6."""
    _testo_top(scr, 243.3, 773.8, _cognome_nome(d.contribuente))
    if d.numero_controllo:
        _testo_top(scr, 243.3, 785.5, d.numero_controllo)


def _pagina4(scr: Scrittore, d) -> None:
    _valori_colonna(scr, _TOP_P4, calcolo_mod1(d)["redditi"])
    _piede(scr, d)


def _pagina5(scr: Scrittore, d) -> None:
    _valori_colonna(scr, _TOP_P5, calcolo_mod1(d)["deduzioni"])
    _piede(scr, d)


# allegati (pagina 6): casella (x0, top) e posizione del numero
_ALLEGATI = {"certificati": (30.5, 675.4), "elenco_titoli": (30.5, 686.9), "moduli": (30.5, 709.9)}
_ALLEGATI_NUMERO_X = 44.5


def _n_moduli_allegati(d) -> int:
    from core.overlay_moduli import _ha_moduli_2_8
    return _ha_moduli_2_8(d)


# assicurazioni sulla vita (cifra 304): quattro righe della tabella 29.3
_TOP_VITA = [137.3, 152.8, 168.0, 183.2]


def _pagina6(scr: Scrittore, d) -> None:
    _valori_colonna(scr, _TOP_P6, calcolo_mod1(d)["sostanza"])
    _piede(scr, d)
    vei = calcolo_veicoli(d)
    if vei["motore"]:
        _testo_top(scr, 154.9, 212.0, "vedi fogli aggiuntivi")        # 29.4: dettaglio nella pagina allegata
    if vei["natanti"]:
        elenco = ", ".join(f"Natante {descrizione_veicolo(v)}" for v in vei["natanti"])
        _testo_top(scr, 154.9, 240.6, elenco, larghezza_max=285)     # 29.5: barche
    for av, top in zip(d.assicurazioni_vita, _TOP_VITA):
        _testo_top(scr, 80.1, top, av.societa, larghezza_max=95)
        if av.anno_conclusione:
            _testo_top(scr, 184.9, top, str(av.anno_conclusione))
        if av.anno_scadenza:
            _testo_top(scr, 233.9, top, str(av.anno_scadenza))
        somma, valore = numero(av.somma_assicurata), numero(av.valore_fiscale)
        if somma:
            _testo_top(scr, 345.0, top, fmt_spazio(int(round(somma))), "right")
        if valore:
            _testo_top(scr, 440.1, top, fmt_spazio(int(round(valore))), "right")
            _testo_top(scr, X_VALORI + 0.5, top, fmt_spazio(int(round(valore))), "right")
    n_cert = len(d.certificati_salario)
    if n_cert:
        x0, top = _ALLEGATI["certificati"]
        _x_in_casella(scr, x0, top)
        _testo_top(scr, _ALLEGATI_NUMERO_X, top - 0.5, str(n_cert), "left")
    if calcolo_mod2(d)["righe"]:
        _x_in_casella(scr, *_ALLEGATI["elenco_titoli"])
    n_mod = _n_moduli_allegati(d)
    if n_mod:
        x0, top = _ALLEGATI["moduli"]
        _x_in_casella(scr, x0, top)
        _testo_top(scr, _ALLEGATI_NUMERO_X, top - 0.5, str(n_mod), "left")


def pagine_modulo1(writer: PdfWriter, d) -> None:
    """Le 4 pagine del Modulo 1 (sempre incluse)."""
    for png, disegna in (("Mod1_pagina3.png", _pagina3), ("Mod1_pagina4.png", _pagina4),
                         ("Mod1_pagina5.png", _pagina5), ("Mod1_pagina6.png", _pagina6)):
        writer.add_page(_pagina_con_sfondo(png, lambda scr, f=disegna: f(scr, d)).pages[0])


# ══════════════════════════════════════════════════════════════════════
# Pagina allegata «Modulo 1 - 29.4 Veicoli a motore» (come la stampa di eTax)
# ══════════════════════════════════════════════════════════════════════
_VEI_COLONNE = [46.6, 72.5, 349.9, 419.0, 478.6, 547.7]
_VEI_TOP_INTESTAZIONE, _VEI_TOP_RIGHE, _VEI_ALT_RIGA = 142.2, 172.9, 11.45


def pagina_veicoli(writer: PdfWriter, d) -> None:
    """Elenco dei veicoli a motore (auto e moto), da allegare al Modulo 1. Senza veicoli non viene creata."""
    vei = calcolo_veicoli(d)
    if not vei["motore"]:
        return
    c = d.contribuente
    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)

    def t(x, top, s_, size=7.7, bold=False, allinea="left"):
        font = FONT_B if bold else FONT
        w = stringWidth(s_, font, size)
        cv.setFont(font, size)
        cv.setFillColorRGB(0, 0, 0)
        cv.drawString(x - w if allinea == "right" else (x - w / 2 if allinea == "center" else x),
                      ALTEZZA_A4 - (top + 0.793 * size), s_)

    def linea(x0, top0, x1, top1):
        cv.setStrokeColorRGB(0, 0, 0)
        cv.setLineWidth(0.35)
        cv.line(x0, ALTEZZA_A4 - top0, x1, ALTEZZA_A4 - top1)

    t(48.4, 35.7, f"Allegati dichiarazione cantone Ticino {d.anno_fiscale}")
    t(48.4, 46.2, "Nome, cognome:")
    t(118.5, 46.5, _cognome_nome(c))
    t(48.4, 56.8, "Numero registro:")
    if d.numero_controllo:
        t(118.5, 57.5, d.numero_controllo)
    t(48.4, 107.3, "Modulo 1 - 29.4 Veicoli a motore", 11.5, bold=True)

    n = len(vei["motore"])
    top_fine = _VEI_TOP_RIGHE + _VEI_ALT_RIGA * n
    x0, x1 = _VEI_COLONNE[0], _VEI_COLONNE[-1]
    linea(x0, _VEI_TOP_INTESTAZIONE, x1, _VEI_TOP_INTESTAZIONE)
    for k in range(n + 1):
        y = _VEI_TOP_RIGHE + _VEI_ALT_RIGA * k
        linea(x0, y, x1, y)
    for x in _VEI_COLONNE:
        linea(x, _VEI_TOP_INTESTAZIONE, x, top_fine)
    # intestazioni
    t(52.5, 147.4, "No.", 8.6, True)
    t(131.4, 146.5, "Marca e eventuale rata mensile leasing", 8.6, True)
    for cx, riga1, riga2 in ((384.5, "Prezzo di", "acquisto"), (448.8, "Anno di", "acquisto")):
        t(cx, 147.4, riga1, 8.6, True, "center")
        t(cx, 161.0, riga2, 8.6, True, "center")
    t(513.0, 147.4, "Valore", 8.6, True, "center")

    totale = 0
    for k, v in enumerate(vei["motore"]):
        top = _VEI_TOP_RIGHE + _VEI_ALT_RIGA * k + 1.6
        t(70.5, top, str(k + 1), allinea="right")
        t(74.3, top, descrizione_veicolo(v))
        if v.modalita != "Leasing":
            if numero(v.prezzo_acquisto):
                t(418.0, top, fmt_spazio(int(round(numero(v.prezzo_acquisto)))), allinea="right")
            if v.anno_acquisto:
                t(477.5, top, str(v.anno_acquisto), allinea="right")
            valore = int(round(valore_veicolo(v)))
            totale += valore
            if valore:
                t(546.6, top, fmt_spazio(valore), allinea="right")
    # totale
    cv.rect(478.6, ALTEZZA_A4 - (top_fine + 0.2 + 16.0), 69.1, 16.0, fill=0, stroke=1)
    t(473.9, top_fine + 4.9, "Totale", allinea="right")
    t(546.6, top_fine + 4.8, fmt_spazio(totale), allinea="right")
    cv.showPage()
    cv.save()
    buf.seek(0)
    writer.add_page(PdfReader(buf).pages[0])

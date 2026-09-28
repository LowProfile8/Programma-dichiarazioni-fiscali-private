"""
core/overlay_moduli.py — compila i moduli ufficiali del Cantone Ticino.

Ogni valore viene scritto NELLE CASELLE dei PDF ufficiali usando la loro
geometria vettoriale (core/celle.py): una cifra per casella, allineata a
destra, con i centesimi dove il campo li prevede. I numeri arrivano tutti da
core/calcoli.py, gli stessi mostrati nel wizard.

Composizione dell'output finale (genera_dichiarazione_completa):
  Modulo 1 (4 pagine, sempre) · Modulo 2 (2 pagine) · Modulo 4 · Modulo 5 ·
  Modulo 6 · Modulo 7 (2 pagine per immobile) · Modulo 8 · pagina Note.
  I moduli 2-8 senza valori non vengono inclusi (non vanno inviati).
"""

import textwrap
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from core.calcoli import (
    calcolo_immobile, calcolo_mod1, calcolo_mod2, calcolo_mod4, calcolo_mod5,
    calcolo_mod6, calcolo_mod8, numero,
)
from core.celle import ALTEZZA_A4, FONT_B, Scrittore

CARTELLA_MODULI = Path(__file__).parent.parent / "assets" / "moduli_ufficiali"


# ══════════════════════════════════════════════════════════════════════
# Infrastruttura
# ══════════════════════════════════════════════════════════════════════
def _aggiungi_pagina(writer: PdfWriter, nome_pdf: str, indice: int, disegna, rotata: bool = False) -> None:
    """Aggiunge al writer la pagina `indice` del PDF ufficiale con sopra i dati."""
    percorso = CARTELLA_MODULI / nome_pdf
    lettore = PdfReader(str(percorso))
    pagina = lettore.pages[indice]
    larghezza = float(pagina.mediabox.width)
    altezza = float(pagina.mediabox.height)
    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=(larghezza, altezza))
    disegna(Scrittore(cv, rotata=rotata))
    cv.showPage()  # garantisce una pagina anche quando non c'è nulla da scrivere
    cv.save()
    buf.seek(0)
    pagina.merge_page(PdfReader(buf).pages[0])
    writer.add_page(pagina)


def _a_bytes(writer: PdfWriter) -> bytes:
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def _nome_completo(persona) -> str:
    """«Cognome Nome» come nelle stampe di eTax."""
    return f"{persona.cognome} {persona.nome}".strip()


def _fmt_pct(x: float) -> str:
    if abs(x - round(x)) < 0.005:
        return str(int(round(x)))
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _pct_in_box(scr: Scrittore, box, valore: float) -> None:
    """Percentuale prima del simbolo «%» stampato nella casella (gli ultimi ~12 pt del riquadro)."""
    x0, x1, top, bot = box
    if abs(valore - round(valore)) < 0.005:
        scr.cifre((x0, x1 - 12.2, top, bot), round(valore))
    else:
        scr.testo(x1 - 13.5, Scrittore._base(box, 8), _fmt_pct(valore), "right", size=8)


def _quota_in_celle(scr: Scrittore, box, quota: float) -> None:
    """Quota % nelle 3 caselle: sempre un numero intero (33%, 34%…), una cifra per casella."""
    scr.cifre(box, int(round(quota)))


def _data(d) -> str:
    return d.strftime("%d.%m.%Y") if d else ""


# ══════════════════════════════════════════════════════════════════════
# Intestazioni (Contribuente / Coniuge) — riquadri identici nei moduli
# ══════════════════════════════════════════════════════════════════════
_INTEST_M4_M5 = {"contribuente": (192.8, 361.4, 93.5, 109.1), "coniuge": (239.5, 361.4, 112.0, 127.6),
                 "registro": (426.6, 581.1, 93.5, 109.1)}
_INTEST_M6_M7_M8 = {"contribuente": (192.8, 361.4, 114.2, 129.8), "coniuge": (239.5, 361.4, 132.6, 148.2),
                    "registro": (426.6, 581.1, 114.2, 129.8)}
_INTEST_M4_PAG2 = {"contribuente": (239.5, 361.4, 93.5, 109.1), "registro": (426.6, 581.1, 93.5, 109.1)}


def _intestazione(scr: Scrittore, d, riquadri: dict, con_coniuge: bool = True, persona=None) -> None:
    """Nome nel riquadro «Contribuente» (o, per la pagina del coniuge nel Modulo 4, il nome del coniuge),
    coniuge nel suo riquadro, numero di controllo nel riquadro «Numero registro»."""
    c = d.contribuente
    titolare = persona or c
    scr.testo_in_box(riquadri["contribuente"], _nome_completo(titolare), size=8.5, pad=5.6)
    if con_coniuge and c.coniuge and "coniuge" in riquadri:
        scr.testo_in_box(riquadri["coniuge"], _nome_completo(c.coniuge), size=8.5, pad=5.6)
    if d.numero_controllo:
        scr.testo_in_box(riquadri["registro"], d.numero_controllo, size=8.5, pad=5.6)


# ══════════════════════════════════════════════════════════════════════
# MODULO 4 — spese professionali (pagina del contribuente)
# ══════════════════════════════════════════════════════════════════════
_M4_RIGHE_VEICOLO = [(300.3, 316.4), (316.3, 332.5)]
_M4_COL = {
    "dal": (37.8, 93.1), "al": (93.1, 148.4), "dom": (148.4, 213.6), "lav": (213.6, 278.8),
    "km": (278.8, 316.3), "kmg": (316.3, 353.9), "gg": (353.9, 391.4), "tot": (391.4, 453.8),
}
_M4_TOT_DISTANZA = (391.4, 453.8, 332.5, 348.6)
_M4_AUTO_KM = (229.8, 291.5, 349.1, 364.7)
_M4_V402 = (482.1, 581.3, 349.4, 365.0)
_M4_GRADO = (43.9, 81.2, 170.4, 186.0)
# 2.1 abbonamento mezzo pubblico: due righe, ognuna con il proprio importo (cifra 400)
_M4_ABBO_TOP = [(231.1, 246.7), (246.7, 262.3)]
_M4_ABBO_COL = {"dal": (125.2, 180.5), "al": (180.5, 235.8), "dom": (235.8, 344.9), "lav": (344.9, 454.0),
                "imp": (482.4, 581.6)}
_M4_V404 = (482.1, 581.3, 381.1, 396.7)
# 1. Durata dell'attività: «annuale» / «inferiore all'anno: durata dal … al …» con data completa GG/MM/AAAA
_M4_ANNUALE = (150.7, 158.7, 159.5, 167.5)
_M4_INFERIORE = (234.4, 242.4, 159.5, 167.5)
_M4_DURATA_CENTRI = [352.3, 364.45, 381.2, 393.35, 410.1, 422.25, 434.4, 446.55]   # G G M M A A A A
_M4_DURATA_DAL = (157.1, 171.3)
_M4_DURATA_AL = (173.2, 187.4)
# date GG/MM: centri delle 4 cifre (la barra è già stampata); il modulo non ha caselle per l'anno
_M4_DATE_VEICOLO = {"dal": [44.9, 57.05, 73.8, 85.95], "al": [100.15, 112.35, 129.05, 141.25]}
_M4_DATE_ABBO = {"dal": [132.3, 144.45, 161.2, 173.35], "al": [187.55, 199.7, 216.45, 228.6]}
_M4_PASTI_GIORNI = {False: (416.2, 453.5, 480.3, 495.9), True: (416.2, 453.5, 502.6, 518.2)}   # senza / con mensa
_M4_V408 = (482.1, 581.3, 502.8, 518.4)
_M4_V420 = (482.1, 581.3, 686.9, 702.5)
_M4_V432 = (482.1, 581.3, 732.2, 747.8)
_M4_V438 = (482.1, 581.3, 763.4, 779.0)


def _date_riga(scr: Scrittore, periodo, centri: dict, top: float, bot: float) -> None:
    """Date «dal»/«al» di una riga della tabella (il modulo ha le caselle solo per giorno e mese)."""
    if not periodo or not periodo[0] or not periodo[1]:
        return
    scr.cifre_ai_centri(centri["dal"], top, bot, periodo[0].strftime("%d%m"))
    scr.cifre_ai_centri(centri["al"], top, bot, periodo[1].strftime("%d%m"))


def _pagina_modulo4(writer: PdfWriter, d, persona: str) -> None:
    m4 = calcolo_mod4(d, persona)
    if not m4["ha_dati"]:
        return
    anagrafica = d.contribuente if persona == "contribuente" else d.contribuente.coniuge
    domicilio = anagrafica.indirizzo or d.contribuente.indirizzo or anagrafica.domicilio or d.contribuente.domicilio

    def disegna(scr: Scrittore) -> None:
        if persona == "contribuente":
            _intestazione(scr, d, _INTEST_M4_M5, con_coniuge=False)
        else:
            _intestazione(scr, d, _INTEST_M4_PAG2, con_coniuge=False, persona=anagrafica)
        scr.cifre(_M4_GRADO, m4["grado"])

        # 1. durata dell'attività professionale
        durata = m4["durata"]
        if durata["annuale"]:
            scr.x_in_box(_M4_ANNUALE, size=8)
        elif durata["dal"] or durata["al"]:
            scr.x_in_box(_M4_INFERIORE, size=8)
            for data, (top, bot) in ((durata["dal"], _M4_DURATA_DAL), (durata["al"], _M4_DURATA_AL)):
                if data:
                    scr.cifre_ai_centri(_M4_DURATA_CENTRI, top, bot, data.strftime("%d%m%Y"))

        # 2.1 abbonamento mezzo pubblico
        for ab, (top, bot) in zip(m4["abbonamenti"], _M4_ABBO_TOP):
            b = lambda k: (_M4_ABBO_COL[k][0], _M4_ABBO_COL[k][1], top, bot)
            _date_riga(scr, m4["periodi"].get(ab["cert"].uid), _M4_DATE_ABBO, top, bot)
            scr.testo_in_box(b("dom"), domicilio, size=8)
            scr.testo_in_box(b("lav"), ab["comune_lavoro"], size=8)
            scr.cifre(b("imp"), ab["importo"])

        # 2.2 veicolo privato
        for riga, (top, bot) in zip(m4["righe"], _M4_RIGHE_VEICOLO):
            box = lambda k: (_M4_COL[k][0], _M4_COL[k][1], top, bot)
            _date_riga(scr, m4["periodi"].get(riga["cert"].uid), _M4_DATE_VEICOLO, top, bot)
            scr.testo_in_box(box("dom"), domicilio, size=8)
            scr.testo_in_box(box("lav"), riga["comune_lavoro"], size=8)
            scr.cifre(box("km"), riga["km_tragitto"])
            scr.cifre(box("kmg"), riga["km_giorno"])
            scr.cifre(box("gg"), riga["giorni"])
            scr.cifre(box("tot"), riga["km_totali"])
        if m4["righe"]:
            scr.cifre(_M4_TOT_DISTANZA, m4["km_totali"])
            scr.cifre(_M4_AUTO_KM, m4["km_totali"])
            scr.cifre(_M4_V402, m4["trasporto"])

        # 2.3 bicicletta / ciclomotore
        scr.cifre(_M4_V404, m4["bici"])

        # 3.1 pasti principali fuori casa (giorni = somma dei giorni dei lavori, max 220)
        if m4["pasti"]:
            scr.cifre(_M4_PASTI_GIORNI[m4["pasti_con_mensa"]], m4["giorni_pasti"])
            scr.cifre(_M4_V408, m4["pasti"])

        scr.cifre(_M4_V420, m4["forfait_principale"])
        scr.cifre(_M4_V432, m4["forfait_accessoria"])
        scr.cifre(_M4_V438, m4["totale"])

    _aggiungi_pagina(writer, "Mod4.pdf", 0 if persona == "contribuente" else 1, disegna)


def pagine_modulo4(writer: PdfWriter, d) -> None:
    """Modulo 4: una pagina per il contribuente e, se c'è un coniuge con attività dipendente, una per il coniuge."""
    _pagina_modulo4(writer, d, "contribuente")
    if d.contribuente.coniuge is not None:
        _pagina_modulo4(writer, d, "coniuge")


# ══════════════════════════════════════════════════════════════════════
# MODULO 5 — debiti (pagina fronte)
# ══════════════════════════════════════════════════════════════════════
_M5_PRIMA_RIGA_TOP = 215.5
_M5_PASSO = 16.1
_M5_ALTEZZA = 16.1
_M5_RIGHE_MAX = 14
_M5_COL = {"cred": (14.4, 183.1), "gen": (183.1, 236.9), "imp": (382.4, 481.6), "int": (481.6, 580.8)}
_M5_TOT_IMP = (382.4, 481.6, 457.1, 473.7)
_M5_TOT_INT = (481.6, 580.8, 457.1, 473.7)


def pagine_modulo5(writer: PdfWriter, d) -> None:
    m5 = calcolo_mod5(d)
    if not m5["privati"]:
        return

    def disegna(scr: Scrittore) -> None:
        _intestazione(scr, d, _INTEST_M4_M5)
        for k, r in enumerate(m5["privati"][:_M5_RIGHE_MAX]):
            top = _M5_PRIMA_RIGA_TOP + _M5_PASSO * k
            bot = top + _M5_ALTEZZA
            scr.testo_in_box((_M5_COL["cred"][0], _M5_COL["cred"][1], top, bot), r["creditore"], size=7.5)
            scr.testo_in_box((_M5_COL["gen"][0], _M5_COL["gen"][1], top, bot), r["genere"], size=8.5, allinea="center")
            scr.cifre((_M5_COL["imp"][0], _M5_COL["imp"][1], top, bot), r["importo"])
            scr.cifre((_M5_COL["int"][0], _M5_COL["int"][1], top, bot), r["interessi"])
        scr.cifre(_M5_TOT_IMP, m5["tot_importo"])
        scr.cifre(_M5_TOT_INT, m5["tot_interessi"])

    _aggiungi_pagina(writer, "Mod5.pdf", 0, disegna)


# ══════════════════════════════════════════════════════════════════════
# MODULO 6 — oneri assicurativi (pagina fronte)
# ══════════════════════════════════════════════════════════════════════
_M6_X = (481.9, 581.1)
_M6_RIGHE_A = {  # a. malattia, b. infortuni, c. vita, d. interessi risparmio, e. perdita di guadagno
    "malattia": (185.9, 201.5), "infortuni": (201.5, 217.1), "vita": (217.1, 232.7),
    "interessi": (232.7, 248.3), "perdita": (248.3, 263.9),
}
_M6_TOT_A = (264.4, 281.0)
_M6_B = {
    "c_base": (332.9, 348.5), "c_figli": (348.5, 364.1), "c_prev": (382.5, 398.1),
    "a_base": (406.2, 421.8), "a_figli": (421.8, 437.4), "a_prev": (455.8, 471.4),
}
_M6_TOT_B = (478.8, 495.4)
_M6_AMMESSA = (522.0, 538.6)
_M6_CURA_TOP = [643.1, 659.2, 675.3, 691.4, 707.4]
_M6_CURA_ALT = 16.1
_M6_CURA_TOT = (723.8, 740.4)


def pagine_modulo6(writer: PdfWriter, d) -> None:
    m6 = calcolo_mod6(d)
    if m6["totale_a"] <= 0 and not m6["cura"]:
        return

    def disegna(scr: Scrittore) -> None:
        _intestazione(scr, d, _INTEST_M6_M7_M8)
        campo = lambda t: (_M6_X[0], _M6_X[1], t[0], t[1])
        scr.cifre(campo(_M6_RIGHE_A["malattia"]), m6["malattia"])
        scr.cifre(campo(_M6_RIGHE_A["infortuni"]), m6["infortuni"])
        scr.cifre(campo(_M6_RIGHE_A["vita"]), m6["vita"])
        scr.cifre(campo(_M6_RIGHE_A["interessi"]), m6["interessi_risparmio"])
        scr.cifre(campo(_M6_RIGHE_A["perdita"]), m6["perdita_guadagno"])
        scr.cifre(campo(_M6_TOT_A), m6["totale_a"])

        pref = "c_" if m6["coniugati"] else "a_"
        scr.cifre(campo(_M6_B[pref + "base"]), m6["base"])
        scr.cifre(campo(_M6_B[pref + "figli"]), m6["suppl_figli"])
        scr.cifre(campo(_M6_B[pref + "prev"]), m6["suppl_no_previdenza"])
        scr.cifre(campo(_M6_TOT_B), m6["totale_b"])
        scr.cifre(campo(_M6_AMMESSA), m6["ammessa"])

        for k, r in enumerate(m6["cura"][: len(_M6_CURA_TOP)]):
            top = _M6_CURA_TOP[k]
            bot = top + _M6_CURA_ALT
            f = r["figlio"]
            scr.testo_in_box((14.4, 125.0, top, bot), f.nome, size=7.5)
            scr.testo_in_box((125.0, 473.6, top, bot), f.nome_istituto_cura, size=7.5)
            scr.cifre((482.1, 581.4, top, bot), r["importo"])
        if m6["cura"]:
            scr.cifre((482.1, 581.4, _M6_CURA_TOT[0], _M6_CURA_TOT[1]), m6["cura_totale"])

    _aggiungi_pagina(writer, "Mod6.pdf", 0, disegna)


# ══════════════════════════════════════════════════════════════════════
# MODULO 8 — partecipazioni qualificate (pagina fronte)
# ══════════════════════════════════════════════════════════════════════
_M8_TOP_RIGHE = [229.0, 245.1, 261.2, 277.3, 293.4, 309.5, 325.5, 341.6, 357.7]
_M8_ALT = 16.1
_M8_COL = {"nom": (14.4, 100.2), "quota": (100.2, 137.4), "desc": (137.4, 354.3),
           "vf": (354.3, 453.5), "red": (453.5, 581.1)}
_M8_TOT_A = (374.1, 390.7)
_M8_RECUPERO = (184.3, 311.8, 397.4, 413.9)
_M8_TOT_C = (672.8, 689.4)
_M8_RIDUZIONE = (453.5, 581.1, 705.0, 721.6)
_M8_TOT_D = (453.5, 581.1, 737.2, 753.8)


def pagine_modulo8(writer: PdfWriter, d) -> None:
    m8 = calcolo_mod8(d)
    if not m8["righe"]:
        return

    def disegna(scr: Scrittore) -> None:
        _intestazione(scr, d, _INTEST_M6_M7_M8)
        for r, top in zip(m8["righe"], _M8_TOP_RIGHE):
            bot = top + _M8_ALT
            b = lambda k: (_M8_COL[k][0], _M8_COL[k][1], top, bot)
            scr.cifre(b("nom"), r["nominale"])
            _quota_in_celle(scr, b("quota"), r["quota"])
            scr.testo_in_box(b("desc"), r["descrizione"], size=8)
            scr.cifre(b("vf"), r["valore_fiscale"])
            scr.cifre(b("red"), r["reddito_lordo"], centesimi=True)

        def riga_tot(tb, sostanza, reddito):
            scr.cifre((_M8_COL["vf"][0], _M8_COL["vf"][1], tb[0], tb[1]), sostanza)
            scr.cifre((_M8_COL["red"][0], _M8_COL["red"][1], tb[0], tb[1]), reddito, centesimi=True)

        riga_tot(_M8_TOT_A, m8["tot_a_sostanza"], m8["tot_a_reddito_lordo"])
        scr.cifre(_M8_RECUPERO, m8["recupero_ip"], centesimi=True)
        riga_tot(_M8_TOT_C, m8["tot_c_sostanza"], m8["tot_c_reddito_lordo"])
        scr.cifre(_M8_RIDUZIONE, m8["riduzione_30"], centesimi=True)
        scr.cifre(_M8_TOT_D, m8["tot_d_reddito_netto"], centesimi=True)

    _aggiungi_pagina(writer, "Mod8.pdf", 0, disegna)


# ══════════════════════════════════════════════════════════════════════
# MODULO 7 — immobili (2 pagine per immobile)
# ══════════════════════════════════════════════════════════════════════
_M7_DEST = {
    "Uso proprio": (14.4, 22.4, 169.0, 177.0), "Uso di terzi": (14.4, 22.4, 181.0, 189.0),
    "Uso misto": (14.4, 22.4, 193.0, 201.0), "In usufrutto/diritto di abitazione": (14.4, 22.4, 205.0, 213.0),
}
_M7_TIPO = {
    "Unifamiliare": (14.4, 22.4, 245.0, 253.0), "Plurifamiliare": (14.4, 22.4, 257.0, 265.0),
    "Commerciale e abitativa": (14.4, 22.4, 269.0, 277.0), "Commerciale": (14.4, 22.4, 281.0, 289.0),
    "Altro": (14.4, 22.4, 293.0, 301.0),
}
_M7_PRIMARIA = (127.8, 135.8, 464.5, 472.5)
_M7_SECONDARIA = (127.8, 135.8, 480.6, 488.6)
_M7_FORFAIT = {0.10: (215.9, 223.9, 622.3, 630.3), 0.20: (285.4, 293.4, 622.3, 630.3)}
_M7_COMUNE = (198.4, 368.5, 170.8, 186.4)
_M7_INDIRIZZO = (198.4, 368.5, 187.1, 202.7)
_M7_NAZIONE = (430.9, 468.1, 170.8, 186.4)
_M7_REGISTRO_FOND = (127.6, 360.0, 215.5, 232.7)
_M7_ANNO = (371.3, 421.9, 215.7, 232.7)
_M7_ACQUISTO_DATA, _M7_ACQUISTO_PREZZO = (207.6, 313.9, 253.7, 269.3), (481.9, 581.1, 253.7, 269.3)
_M7_VENDITA_DATA, _M7_VENDITA_PREZZO = (207.4, 313.7, 270.0, 285.6), (481.9, 581.1, 270.0, 285.6)
_M7_STIMA_TOT = (481.9, 581.1, 383.0, 399.6)
_M7_V51 = (481.9, 581.2, 461.1, 476.7)
_M7_V52 = (481.9, 581.2, 477.2, 492.8)
_M7_AFFITTO_A = (339.0, 438.3, 507.5, 523.1)
_M7_AFFITTI_TOT_E = (338.8, 438.0, 572.1, 587.7)
_M7_V53 = (481.9, 581.2, 571.8, 587.4)
_M7_V54 = (481.9, 581.2, 587.9, 604.5)
_M7_V55_FORFAIT = (481.9, 581.2, 619.0, 634.5)
_M7_V55_EFFETTIVE = (481.9, 581.2, 635.0, 650.6)
_M7_V56 = (481.9, 581.2, 665.1, 681.6)

_M7P2_SPESE_TOP = [137.3 + 17.0 * k for k in range(14)]
_M7P2_SPESE_ALT = 17.0
_M7P2_TOT_SPESE = (481.9, 581.1, 407.8, 424.4)
_M7P2_COMPROPRIETA = (238.5, 246.5, 465.4, 473.4)
_M7P2_Q_CONTR = {"red": (478.7, 529.7, 553.0, 570.3), "sos": (529.7, 580.7, 553.0, 570.3)}
_M7P2_ALTRI_TOP = [625.7, 643.0, 660.2, 677.5, 694.7]
_M7P2_ALTRI_ALT = 17.3
_M7P2_ALTRI_COL = {"nome": (147.0, 311.4), "anno": (311.4, 365.3), "dom": (365.3, 478.7),
                   "red": (478.7, 529.7), "sos": (529.7, 580.7)}
_M7P2_QUOTA_PARTE = {"sos": (124.7, 175.7), "red": (175.7, 226.8), "stima": (226.8, 326.0),
                     "redditi": (326.0, 425.2), "spese": (425.2, 581.1)}
_M7P2_QUOTA_PARTE_Y = (761.6, 778.8)


def pagine_modulo7(writer: PdfWriter, d, imm) -> None:
    c = calcolo_immobile(imm)

    def pagina1(scr: Scrittore) -> None:
        _intestazione(scr, d, _INTEST_M6_M7_M8)
        scr.testo_in_box(_M7_COMUNE, imm.comune.valore or "", size=8.5)
        scr.testo_in_box(_M7_INDIRIZZO, imm.indirizzo.valore or "", size=8.5)
        scr.testo_in_box(_M7_NAZIONE, "Svizzera" if imm.in_svizzera else (imm.nazione_cantone.valore or ""),
                         size=8, pad=2, allinea="center")
        if imm.numero_registro_fondiario:
            scr.testo_in_box(_M7_REGISTRO_FOND, imm.numero_registro_fondiario, size=8.5)
        if imm.anno_costruzione:
            scr.cifre(_M7_ANNO, imm.anno_costruzione)
        if imm.destinazione in _M7_DEST:
            scr.x_in_box(_M7_DEST[imm.destinazione])
        if imm.tipo_immobile in _M7_TIPO:
            scr.x_in_box(_M7_TIPO[imm.tipo_immobile])

        if imm.comprato_venduto_anno == "comprato":
            scr.testo_in_box(_M7_ACQUISTO_DATA, _data(imm.data_operazione), size=8, allinea="center")
            scr.cifre(_M7_ACQUISTO_PREZZO, numero(imm.prezzo_operazione))
        elif imm.comprato_venduto_anno == "venduto":
            scr.testo_in_box(_M7_VENDITA_DATA, _data(imm.data_operazione), size=8, allinea="center")
            scr.cifre(_M7_VENDITA_PREZZO, numero(imm.prezzo_operazione))

        scr.cifre(_M7_STIMA_TOT, c["stima"])

        if imm.destinazione == "Uso proprio":
            if imm.abitazione_primaria:
                scr.x_in_box(_M7_PRIMARIA)
                scr.cifre(_M7_V51, c["valore_locativo"])
            else:
                scr.x_in_box(_M7_SECONDARIA)
                scr.cifre(_M7_V52, c["valore_locativo"])
        elif c["affitti"] > 0:
            scr.cifre(_M7_AFFITTO_A, c["affitti"])
            scr.cifre(_M7_AFFITTI_TOT_E, c["affitti"])
            scr.cifre(_M7_V53, c["affitti"])
        scr.cifre(_M7_V54, c["lordo"])

        if imm.usa_spese_effettive:
            scr.cifre(_M7_V55_EFFETTIVE, c["spese"])
        else:
            scr.x_in_box(_M7_FORFAIT[0.10 if c["forfait_pct"] < 0.15 else 0.20])
            scr.cifre(_M7_V55_FORFAIT, c["spese"])
        scr.cifre(_M7_V56, c["netto"])

    def pagina2(scr: Scrittore) -> None:
        if imm.usa_spese_effettive:
            for k, s in enumerate(imm.spese_effettive[: len(_M7P2_SPESE_TOP)]):
                top = _M7P2_SPESE_TOP[k]
                scr.cifre((481.9, 581.1, top, top + _M7P2_SPESE_ALT), numero(s))
            scr.cifre(_M7P2_TOT_SPESE, c["spese"])
        if not imm.piena_proprieta:
            scr.x_in_box(_M7P2_COMPROPRIETA)
            _pct_in_box(scr, _M7P2_Q_CONTR["red"], imm.quota_reddito_contribuente)
            _pct_in_box(scr, _M7P2_Q_CONTR["sos"], imm.quota_sostanza_contribuente)
            for k, comp in enumerate(imm.comproprietari[: len(_M7P2_ALTRI_TOP)]):
                top = _M7P2_ALTRI_TOP[k]
                bot = top + _M7P2_ALTRI_ALT
                col = lambda n: (_M7P2_ALTRI_COL[n][0], _M7P2_ALTRI_COL[n][1], top, bot)
                scr.testo_in_box(col("nome"), comp.cognome_nome, size=8)
                if comp.anno_nascita:
                    scr.cifre(col("anno"), comp.anno_nascita)
                scr.testo_in_box(col("dom"), comp.domicilio, size=8)
                _pct_in_box(scr, col("red"), comp.quota_reddito)
                _pct_in_box(scr, col("sos"), comp.quota_sostanza)
            y0, y1 = _M7P2_QUOTA_PARTE_Y
            qp = lambda n: (_M7P2_QUOTA_PARTE[n][0], _M7P2_QUOTA_PARTE[n][1], y0, y1)
            _pct_in_box(scr, qp("sos"), imm.quota_sostanza_contribuente)
            _pct_in_box(scr, qp("red"), imm.quota_reddito_contribuente)
            scr.cifre(qp("stima"), c["stima_q"])
            scr.cifre(qp("redditi"), c["lordo_q"])
            scr.cifre(qp("spese"), c["spese_q"])

    _aggiungi_pagina(writer, "Mod7.pdf", 0, pagina1)
    _aggiungi_pagina(writer, "Mod7.pdf", 1, pagina2)


# ══════════════════════════════════════════════════════════════════════
# MODULO 2 — pagina 2: elenco titoli (tabella in orizzontale)
# ══════════════════════════════════════════════════════════════════════
_M2_TOP_RIGHE = [127.9, 144.0, 160.1, 176.1, 192.2, 208.3, 224.4, 240.5, 256.6, 272.7, 288.8]
_M2_ALT = 16.1
_M2_COL = {
    "cl": (14.4, 39.2), "nom": (39.2, 112.6), "num": (112.6, 240.2), "cod": (240.2, 265.0),
    "den": (265.0, 403.2), "quota": (403.2, 437.2), "sos": (474.1, 573.3),
    "A": (573.3, 700.8), "B": (700.8, 828.4),
}
_M2_RIPORTO_FOGLI = (304.9, 321.0)
_M2_TOT = (353.4, 370.0)
_M2_RIPORTO_A = (700.8, 828.4, 377.9, 394.5)
_M2_RIPORTO_M8_SOS = (474.1, 572.6, 405.3, 420.9)
_M2_RIPORTO_M8_RED = (700.8, 828.4, 404.8, 421.4)
_M2_TOT_RIPORTARE = (464.5, 481.1)
_M2_RECUPERO = (572.6, 700.9, 512.7, 529.7)


def pagine_modulo2_tabella(writer: PdfWriter, d) -> None:
    m2 = calcolo_mod2(d)
    righe = m2["righe"]
    n = len(_M2_TOP_RIGHE)
    blocchi = [righe[i:i + n] for i in range(0, len(righe), n)] or [[]]

    def somma(b, k):
        return sum(r[k] for r in b)

    tot_fogli_agg = {k: sum(somma(b, k) for b in blocchi[1:]) for k in ("sostanza", "reddito_a", "reddito_b")}

    for indice, blocco in enumerate(blocchi):
        prima = indice == 0

        def disegna(scr: Scrittore, blocco=blocco, prima=prima) -> None:
            for r, top in zip(blocco, _M2_TOP_RIGHE):
                bot = top + _M2_ALT
                b = lambda k: (_M2_COL[k][0], _M2_COL[k][1], top, bot)
                scr.lettere_in_celle(b("cl"), r["classificazione"])
                scr.cifre(b("nom"), r["nominale"])
                scr.testo_in_box(b("num"), r["numero"], size=7.5)
                scr.lettere_in_celle(b("cod"), r["codice"])
                scr.testo_in_box(b("den"), r["denominazione"], size=8)
                if r["quota"] is not None:
                    scr.testo_in_box(b("quota"), _fmt_pct(r["quota"]), size=8, allinea="right", pad=4)
                scr.cifre(b("sos"), r["sostanza"])
                scr.cifre(b("A"), r["reddito_a"], centesimi=True)
                scr.cifre(b("B"), r["reddito_b"], centesimi=True)

            tot_s, tot_a, tot_b = somma(blocco, "sostanza"), somma(blocco, "reddito_a"), somma(blocco, "reddito_b")
            if prima:
                if len(blocchi) > 1:
                    y = _M2_RIPORTO_FOGLI
                    scr.cifre((_M2_COL["sos"][0], _M2_COL["sos"][1], y[0], y[1]), tot_fogli_agg["sostanza"])
                    scr.cifre((_M2_COL["A"][0], _M2_COL["A"][1], y[0], y[1]), tot_fogli_agg["reddito_a"], centesimi=True)
                    scr.cifre((_M2_COL["B"][0], _M2_COL["B"][1], y[0], y[1]), tot_fogli_agg["reddito_b"], centesimi=True)
                    tot_s += tot_fogli_agg["sostanza"]
                    tot_a += tot_fogli_agg["reddito_a"]
                    tot_b += tot_fogli_agg["reddito_b"]
            y = _M2_TOT
            scr.cifre((_M2_COL["sos"][0], _M2_COL["sos"][1], y[0], y[1]), tot_s)
            scr.cifre((_M2_COL["A"][0], _M2_COL["A"][1], y[0], y[1]), tot_a, centesimi=True)
            scr.cifre((_M2_COL["B"][0], _M2_COL["B"][1], y[0], y[1]), tot_b, centesimi=True)

            if prima:
                scr.cifre(_M2_RIPORTO_A, tot_a, centesimi=True)
                scr.cifre(_M2_RIPORTO_M8_SOS, m2["mod8_sostanza"])
                scr.cifre(_M2_RIPORTO_M8_RED, m2["mod8_reddito_netto"], centesimi=True)
                y = _M2_TOT_RIPORTARE
                scr.cifre((_M2_COL["sos"][0], _M2_COL["sos"][1], y[0], y[1]), m2["sostanza_da_riportare"])
                scr.cifre((_M2_COL["B"][0], _M2_COL["B"][1], y[0], y[1]), m2["reddito_da_riportare"], centesimi=True)
                scr.cifre(_M2_RECUPERO, m2["recupero_ip"], centesimi=True)

        _aggiungi_pagina(writer, "Mod2.pdf", 1, disegna, rotata=True)


# ══════════════════════════════════════════════════════════════════════
# MODULO 2 — pagina 1: domicilio, eredità, donazioni, allegati (geometria vettoriale)
# ══════════════════════════════════════════════════════════════════════
_M2P1 = {
    "contrib": (192.8, 361.4, 93.5, 109.1), "coniuge": (239.5, 361.4, 112.0, 127.6),
    "registro": (426.6, 581.1, 93.5, 109.1),
    "dom_contrib": (252.3, 416.7, 181.7, 215.7), "dom_coniuge": (416.7, 581.1, 181.7, 215.7),
}
_M2P1_X_NO, _M2P1_X_SI, _M2P1_LATO = 17.3, 47.9, 8.0
_M2P1_TOP_SI_NO = {"eredita": 323.0, "comunione": 433.1, "don_ricevute": 482.5, "don_fatte": 562.4, "societa": 627.9}
_M2P1_CELLE_DATA = [206.95, 219.05, 235.85, 247.95, 264.75, 276.9, 289.05, 301.15]   # G G / M M / A A A A
_M2P1_CELLE_CANTONE = [437.3, 449.5]
_M2P1_ERED = {
    "defunto": (198.4, 581.1, 311.3, 326.9), "grado": (198.4, 368.5, 327.6, 343.2),
    "domicilio": (430.9, 581.1, 327.6, 343.2), "decesso_top": 343.9, "decesso_bot": 359.5,
    "capitali": (450.7, 581.1, 360.0, 375.6),
}
_M2P1_COMUNIONE = (198.4, 581.1, 377.6, 393.2)
_M2P1_RICEVUTA = {
    "nome": (198.4, 581.1, 460.6, 476.2), "ind": (198.4, 581.1, 476.9, 492.5),
    "grado": (198.4, 368.5, 493.2, 508.8), "data_top": 509.3, "data_bot": 524.9,
    "capitali": (450.7, 581.1, 509.3, 524.9),
}
_M2P1_FATTA = {
    "nome": (198.4, 581.1, 526.9, 542.5), "ind": (198.4, 581.1, 543.2, 558.8),
    "grado": (198.4, 368.5, 559.5, 575.1), "data_top": 575.6, "data_bot": 591.2,
    "capitali": (450.7, 581.1, 575.6, 591.2),
}
_M2P1_SOCIETA = (198.4, 581.1, 606.0, 621.6)
_M2P1_ATTESTAZIONI_BANCARIE = (17.3, 756.7)


def _casella(scr: Scrittore, x0: float, top: float) -> None:
    scr.x_in_box((x0, x0 + _M2P1_LATO, top, top + _M2P1_LATO), size=8)


def _si_no(scr: Scrittore, chiave: str, si: bool) -> None:
    _casella(scr, _M2P1_X_SI if si else _M2P1_X_NO, _M2P1_TOP_SI_NO[chiave])


def _data_in_celle(scr: Scrittore, data, top: float, bottom: float, size: float = 8.5) -> None:
    if not data:
        return
    base = (top + bottom) / 2 + size * 0.36
    for cx, ch in zip(_M2P1_CELLE_DATA, data.strftime("%d%m%Y")):
        scr.testo(cx, base, ch, "center", "Helvetica", size)


def _riga_donazione(scr: Scrittore, campi: dict, lista: list) -> None:
    prima = lista[0]
    nome = prima.controparte + (" e altri (vedi dettaglio nelle note)" if len(lista) > 1 else "")
    scr.testo_in_box(campi["nome"], nome, size=8.5, pad=5)
    scr.testo_in_box(campi["ind"], prima.indirizzo, size=8.5, pad=5)
    scr.testo_in_box(campi["grado"], prima.grado_parentela, size=8.5, pad=5)
    _data_in_celle(scr, prima.data, campi["data_top"], campi["data_bot"])
    scr.cifre(campi["capitali"], sum(numero(x.importo) for x in lista))


def pagina1_modulo2(writer: PdfWriter, d) -> None:
    c = d.contribuente

    def disegna(scr: Scrittore) -> None:
        scr.testo_in_box(_M2P1["contrib"], _nome_completo(c), size=8.5, pad=5.6)
        scr.testo_in_box(_M2P1["dom_contrib"], _nome_completo(c), size=8.5, pad=5)
        if c.coniuge:
            scr.testo_in_box(_M2P1["coniuge"], _nome_completo(c.coniuge), size=8.5, pad=5.6)
            scr.testo_in_box(_M2P1["dom_coniuge"], _nome_completo(c.coniuge), size=8.5, pad=5)
        if d.numero_controllo:
            scr.testo_in_box(_M2P1["registro"], d.numero_controllo, size=8.5, pad=5.6)

        # eredità
        _si_no(scr, "eredita", d.eredita_ricevuta)
        if d.eredita_ricevuta:
            e = _M2P1_ERED
            scr.testo_in_box(e["defunto"], d.eredita_defunto, size=8.5, pad=5)
            scr.testo_in_box(e["grado"], d.eredita_grado, size=8.5, pad=5)
            scr.testo_in_box(e["domicilio"], d.eredita_ultimo_domicilio, size=8.5, pad=5)
            _data_in_celle(scr, d.eredita_data_decesso, e["decesso_top"], e["decesso_bot"])
            for cx, ch in zip(_M2P1_CELLE_CANTONE, (d.eredita_cantone or "").upper()[:2]):
                scr.testo(cx, (e["decesso_top"] + e["decesso_bot"]) / 2 + 3.06, ch, "center", "Helvetica", 8.5)
            scr.cifre(e["capitali"], numero(d.eredita_importo))

        # comunione ereditaria / indivisioni
        _si_no(scr, "comunione", d.comunione_ereditaria)
        if d.comunione_ereditaria:
            scr.testo_in_box(_M2P1_COMUNIONE, d.comunione_denominazione, size=8.5, pad=5)

        # donazioni
        ricevute = [x for x in d.donazioni if x.direzione == "ricevuta"]
        fatte = [x for x in d.donazioni if x.direzione == "data"]
        _si_no(scr, "don_ricevute", bool(ricevute))
        if ricevute:
            _riga_donazione(scr, _M2P1_RICEVUTA, ricevute)
        _si_no(scr, "don_fatte", bool(fatte))
        if fatte:
            _riga_donazione(scr, _M2P1_FATTA, fatte)

        # società in nome collettivo
        _si_no(scr, "societa", d.societa_nome_collettivo)
        if d.societa_nome_collettivo:
            scr.testo_in_box(_M2P1_SOCIETA, d.societa_ragione_sociale, size=8.5, pad=5)

        # allegati: attestazioni bancarie
        n_att = len(d.conti_correnti) + len(d.titoli_investimenti)
        if n_att:
            x0, top = _M2P1_ATTESTAZIONI_BANCARIE
            _casella(scr, x0, top)
            scr.testo(38.0, top + 6.4, str(n_att), "center", "Helvetica", 8)

    _aggiungi_pagina(writer, "Mod2.pdf", 0, disegna)


# ══════════════════════════════════════════════════════════════════════
# Pagina «Comunicazioni e note per l'Ufficio di tassazione»
# ══════════════════════════════════════════════════════════════════════
def testo_note(d) -> str:
    """Note libere dell'utente + note automatiche (dettaglio delle donazioni multiple, comunione ereditaria)."""
    blocchi = []
    if d.note_ufficio_tassazione.strip():
        blocchi.append(d.note_ufficio_tassazione.strip())
    for direzione, titolo in (("ricevuta", "Dettaglio donazioni ricevute"), ("data", "Dettaglio donazioni fatte")):
        lista = [x for x in d.donazioni if x.direzione == direzione]
        if len(lista) > 1:
            righe = [f"{titolo}:"]
            for x in lista:
                importo = f"{numero(x.importo):,.0f}".replace(",", "'")
                righe.append(f"- {_data(x.data)} {x.controparte} ({x.grado_parentela}), {x.indirizzo}: Fr. {importo}")
            blocchi.append("\n".join(righe))
    if d.comunione_ereditaria:
        parte = f" — parte del contribuente: Fr. {numero(d.comunione_importo):,.0f}".replace(",", "'") if numero(d.comunione_importo) else ""
        blocchi.append(
            f"Comunione ereditaria / indivisione: {d.comunione_denominazione or '(denominazione non indicata)'}{parte}. "
            "Se la comunione detiene unicamente capitali è possibile compilare il Modulo 20."
        )
    return "\n\n".join(blocchi)


def pagina_note(writer: PdfWriter, d) -> None:
    testo = testo_note(d)
    if not testo.strip():
        return
    larghezza, altezza = A4
    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    cv.setFillColorRGB(0.03, 0.4, 0.65)
    cv.rect(larghezza - 140, altezza - 70, 110, 32, fill=1, stroke=0)
    cv.setFillColorRGB(1, 1, 1)
    cv.setFont(FONT_B, 11)
    cv.drawCentredString(larghezza - 85, altezza - 50, "Note")
    cv.setFillColorRGB(0, 0, 0)
    cv.setFont(FONT_B, 20)
    cv.drawCentredString(larghezza - 85, altezza - 90, str(d.anno_fiscale))
    cv.setFont(FONT_B, 15)
    cv.drawString(50, altezza - 60, "Comunicazioni e note per l'Ufficio di tassazione")
    cv.setFont("Helvetica", 11)
    cv.drawString(50, altezza - 90, "Cantone Ticino")
    y_riga = altezza - 130
    cv.line(50, y_riga, larghezza - 50, y_riga)
    cv.setFont("Helvetica", 10)
    cv.drawString(50, y_riga + 5, "Contribuente:")
    cv.drawString(50, y_riga - 12, _nome_completo(d.contribuente))
    cv.drawString(340, y_riga + 5, "Numero registro")
    if d.numero_controllo:
        cv.drawString(340, y_riga - 12, d.numero_controllo)
    y_top, y_bot = y_riga - 40, 150
    cv.setFillColorRGB(1, 1, 0.75)
    cv.rect(50, y_bot, larghezza - 100, y_top - y_bot, fill=1, stroke=1)
    cv.setFillColorRGB(0, 0, 0)
    y = y_top - 20
    for paragrafo in testo.split("\n"):
        for riga in textwrap.wrap(paragrafo, width=95) or [""]:
            if y < y_bot + 15:
                break
            cv.drawString(65, y, riga)
            y -= 14
    cv.save()
    buf.seek(0)
    writer.add_page(PdfReader(buf).pages[0])


# ══════════════════════════════════════════════════════════════════════
# Composizione finale
# ══════════════════════════════════════════════════════════════════════
def _ha_moduli_2_8(d) -> int:
    """Quanti moduli tra 4, 5, 6, 7 (uno per immobile), 8 sono inclusi: serve al conteggio degli allegati (Modulo 1, pag. 6)."""
    m6 = calcolo_mod6(d)
    n = sum(1 for p in ("contribuente", "coniuge") if calcolo_mod4(d, p)["ha_dati"])
    n += 1 if calcolo_mod5(d)["privati"] else 0
    n += 1 if (m6["totale_a"] > 0 or m6["cura"]) else 0
    n += len(d.immobili)
    n += 1 if calcolo_mod8(d)["righe"] else 0
    return n


def _ha_dati_modulo2(d) -> bool:
    m2 = calcolo_mod2(d)
    return (bool(m2["righe"]) or bool(d.donazioni) or calcolo_mod8(d)["righe"] != []
            or d.eredita_ricevuta or d.comunione_ereditaria or d.societa_nome_collettivo)


def genera_dichiarazione_completa(d) -> bytes:
    """Un solo PDF: pagina riassuntiva → Modulo 1 (4 pagine) → 2 → 4 → 5 → 6 → 7 → 8 → Note, numerato.
    I moduli 2-8 privi di valori non vengono inclusi."""
    from core.overlay_copertina import numera_pagine, pagina_copertina
    from core.overlay_mod1 import pagine_modulo1

    writer = PdfWriter()
    pagina_copertina(writer, d)      # pagina riassuntiva da firmare (prima pagina)
    pagine_modulo1(writer, d)
    if _ha_dati_modulo2(d):
        pagina1_modulo2(writer, d)
        pagine_modulo2_tabella(writer, d)
    pagine_modulo4(writer, d)
    pagine_modulo5(writer, d)
    pagine_modulo6(writer, d)
    for imm in d.immobili:
        pagine_modulo7(writer, d, imm)
    pagine_modulo8(writer, d)
    pagina_note(writer, d)
    return numera_pagine(_a_bytes(writer))


# Funzioni singole (usate dai test)
def modulo_singolo(funzione, d, *extra) -> bytes:
    writer = PdfWriter()
    funzione(writer, d, *extra)
    return _a_bytes(writer)

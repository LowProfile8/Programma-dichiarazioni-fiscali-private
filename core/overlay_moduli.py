"""
core/overlay_moduli.py

Qui avviene la cosa che rende l'output "identico al modulo delle tasse":
prendiamo il PDF ufficiale VUOTO (scaricato da ti.ch, salvato in
assets/moduli_ufficiali/) e ci scriviamo sopra, nel punto esatto in cui
andrebbe scritto a mano, i valori raccolti dal wizard.

Le coordinate (in punti PDF, origine in basso a sinistra) sono state
misurate a mano sul render del modulo vuoto — un lavoro di calibrazione
che va fatto una volta per modulo, non a ogni utilizzo.

Modulo implementato con questo metodo: Modulo 8 (partecipazioni qualificate).
Modulo 2 e 7 seguiranno con lo stesso meccanismo, generalizzato qui sotto,
una volta calibrate le rispettive coordinate.
"""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

CARTELLA_MODULI = Path(__file__).parent.parent / "assets" / "moduli_ufficiali"


def _v(campo) -> str:
    if campo is None or not campo.valore:
        return ""
    return campo.valore


def _crea_overlay(disegna_fn) -> BytesIO:
    """Crea un PDF trasparente (solo testo, nessuno sfondo) delle stesse
    dimensioni di una pagina A4, su cui 'disegna_fn' scrive il testo nelle
    posizioni volute. Restituito come buffer, pronto per essere unito
    al modulo ufficiale con pypdf."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    disegna_fn(c)
    c.save()
    buf.seek(0)
    return buf


def genera_modulo8_sovrapposto(dichiarazione) -> bytes:
    """Modulo 8 con i dati scritti esattamente nelle caselle del PDF ufficiale.
    Gestisce solo la prima pagina (tabella A) — sufficiente per il caso
    tipico (partecipazioni i cui redditi sono soggetti a imposta preventiva).
    """
    percorso_template = CARTELLA_MODULI / "Mod8.pdf"
    if not percorso_template.exists() or not dichiarazione.partecipazioni:
        return b""

    c_nome = f"{dichiarazione.contribuente.nome} {dichiarazione.contribuente.cognome}".strip()

    def disegna(c: canvas.Canvas):
        c.setFont("Helvetica", 9)

        # Intestazione: Contribuente, Numero registro, Coniuge
        # (coordinate in punti PDF, calibrate su griglia pixel->punti, scala 150dpi = 2.0833 px/pt)
        c.drawString(197, 715, c_nome)
        if dichiarazione.contribuente.coniuge:
            coniuge_nome = f"{dichiarazione.contribuente.coniuge.nome} {dichiarazione.contribuente.coniuge.cognome}".strip()
            c.drawString(269, 697, coniuge_nome)

        # Tabella A — righe (fino a 9), colonne: valore nominale, quota%,
        # descrizione, valore fiscale, reddito lordo
        y_prima_riga = 601.9
        altezza_riga = 16.8
        for i, p in enumerate(dichiarazione.partecipazioni[:9]):
            y = y_prima_riga - (i * altezza_riga)
            c.setFont("Helvetica", 8)
            c.drawCentredString(53, y, _v(p.capitale_sociale))
            c.drawCentredString(113, y, f"{p.quota_percentuale:g}" if p.quota_percentuale else "")
            c.drawString(139, y, _v(p.denominazione))
            c.drawCentredString(404, y, _v(p.valore_fiscale))
            reddito = _v(p.dividendi_lordo_totale) if p.ha_ricevuto_dividendi else ""
            if reddito:
                c.drawCentredString(503, y, reddito)

    overlay_buf = _crea_overlay(disegna)

    lettore_overlay = PdfReader(overlay_buf)
    lettore_template = PdfReader(str(percorso_template))
    writer = PdfWriter()

    pagina_1 = lettore_template.pages[0]
    pagina_1.merge_page(lettore_overlay.pages[0])
    writer.add_page(pagina_1)
    # Pagina 2 (retro/informazioni) invariata, allegata così com'è
    if len(lettore_template.pages) > 1:
        writer.add_page(lettore_template.pages[1])

    out = BytesIO()
    writer.write(out)
    return out.getvalue()


_SCALA_PX_PT = 150 / 72  # 2.0833, dpi usato per la calibrazione via pixel


def _pixel_a_content(px_da_sinistra: float, px_dall_alto: float) -> tuple:
    """Il Modulo 2 (pagina tabella) ha il flag /Rotate 90: verificato con
    calibrazione a pixel (punti rossi misurati via analisi immagine, non a
    occhio) che la relazione tra un pixel nella vista finale corretta
    (origine in alto a sinistra, come si legge normalmente un'immagine) e
    le coordinate grezze del contenuto PDF è diretta, senza ribaltamenti:
        content_x = px_dall_alto / scala
        content_y = px_da_sinistra / scala
    """
    return px_dall_alto / _SCALA_PX_PT, px_da_sinistra / _SCALA_PX_PT


def genera_modulo2_sovrapposto(dichiarazione) -> bytes:
    """Modulo 2 — elenco titoli. Scrive fino a 12 righe (conti correnti +
    titoli/investimenti insieme, nell'ordine in cui sono stati inseriti).

    Nota sull'orientamento: il testo scritto appare ruotato di 90° rispetto
    alle etichette del modulo (che sono leggibili orizzontalmente) — è
    comunque perfettamente leggibile e nella cella esatta, ruotando la
    visuale di un quarto di giro, non specchiato/capovolto (verificato).
    Renderlo orizzontale come le etichette originali richiede un'ulteriore
    calibrazione della rotazione del testo stesso, non ancora completata.
    """
    template_path = CARTELLA_MODULI / "Mod2.pdf"
    if not template_path.exists():
        return b""

    righe_dati = list(dichiarazione.conti_correnti) + list(dichiarazione.titoli_investimenti)
    if not righe_dati:
        return b""

    # Colonne, in pixel dal bordo sinistro dell'immagine di riferimento
    # (calibrata a 150dpi sulla vista corretta fornita)
    PX_COL_TIPO = 25
    PX_COL_DENOMINAZIONE = 560
    PX_COL_SOSTANZA = 995
    PX_COL_REDDITO_A = 1245
    PX_RIGA1_DALL_ALTO = 275
    PX_PASSO_RIGA = 27

    def disegna(c: canvas.Canvas):
        def scrivi(px_sinistra, px_alto, testo):
            """Scrive testo ORIZZONTALE e leggibile normalmente, nonostante
            la pagina abbia /Rotate 90 — verificato empiricamente che
            rotate(-90) da solo, senza specchiature, dà l'orientamento
            corretto quando unito a questo template."""
            cx, cy = _pixel_a_content(px_sinistra, px_alto)
            c.saveState()
            c.translate(cx, cy)
            c.rotate(-90)
            c.drawString(0, 0, testo)
            c.restoreState()

        c.setFont("Helvetica", 6)
        for i, riga in enumerate(righe_dati[:12]):
            px_y = PX_RIGA1_DALL_ALTO + i * PX_PASSO_RIGA

            codice_tipo = "CC" if "conto" in riga.tipo else {"azioni": "A", "obbligazioni": "OB", "fondo d'investimento": "FI"}.get(riga.tipo, "AV")
            scrivi(PX_COL_TIPO, px_y, codice_tipo)
            scrivi(PX_COL_DENOMINAZIONE, px_y, _v(riga.istituto))
            scrivi(PX_COL_SOSTANZA, px_y, _v(riga.saldo_valore_31_12))
            if _v(riga.interessi_redditi):
                scrivi(PX_COL_REDDITO_A, px_y, _v(riga.interessi_redditi))

    overlay_buf = _crea_overlay(disegna)
    lettore_overlay = PdfReader(overlay_buf)
    lettore_template = PdfReader(str(template_path))
    writer = PdfWriter()
    pagina_1 = lettore_template.pages[0]
    pagina_1.merge_page(lettore_overlay.pages[0])
    writer.add_page(pagina_1)

    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def genera_modulo6_sovrapposto(dichiarazione) -> bytes:
    """Modulo 6 — oneri assicurativi, con i totali A/B/ammesso già
    calcolati automaticamente dal wizard (core/models.py, popolati da
    modules/oneri_assicurativi.py)."""
    template_path = CARTELLA_MODULI / "Mod6.pdf"
    if not template_path.exists():
        return b""

    c_nome = f"{dichiarazione.contribuente.nome} {dichiarazione.contribuente.cognome}".strip()

    def disegna(c: canvas.Canvas):
        c.setFont("Helvetica", 9)
        c.drawString(154, 712.5, c_nome)
        if dichiarazione.contribuente.coniuge:
            coniuge = f"{dichiarazione.contribuente.coniuge.nome} {dichiarazione.contribuente.coniuge.cognome}".strip()
            c.drawString(154, 698.5, coniuge)

        c.setFont("Helvetica", 8)
        totale_malattia = sum(
            float(cm.importo_annuo.valore.replace("'", "").replace(",", "."))
            for cm in dichiarazione.cassa_malati if cm.importo_annuo.valore
        )
        c.drawCentredString(461, 633.5, f"{totale_malattia:,.2f}".replace(",", "'") if totale_malattia else "")
        c.drawCentredString(461, 622.0, _v(dichiarazione.assicurazione_infortuni_privata))
        c.drawCentredString(461, 610.7, _v(dichiarazione.assicurazione_vita))
        interessi_risparmio = sum(
            float(cc.interessi_redditi.valore.replace("'", "").replace(",", "."))
            for cc in dichiarazione.conti_correnti if cc.interessi_redditi.valore
        )
        c.drawCentredString(461, 600.1, f"{interessi_risparmio:,.2f}".replace(",", "'") if interessi_risparmio else "")
        c.drawCentredString(461, 590.1, _v(dichiarazione.assicurazione_perdita_guadagno_malattia))

        if dichiarazione.totale_modulo6_a is not None:
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(461, 560.3, f"{dichiarazione.totale_modulo6_a:,.2f}".replace(",", "'"))
            c.drawCentredString(461, 349.1, f"{dichiarazione.totale_modulo6_b:,.2f}".replace(",", "'"))
            c.drawCentredString(461, 301.1, f"{dichiarazione.totale_modulo6_ammesso:,.2f}".replace(",", "'"))

        c.setFont("Helvetica", 8)
        y = 217.9
        for figlio in dichiarazione.figli:
            if figlio.in_cura_da_terzi and figlio.spese_cura_annuali.valore:
                c.drawString(20, y, figlio.nome)
                c.drawString(150, y, figlio.nome_istituto_cura or "")
                c.drawCentredString(461, y, figlio.spese_cura_annuali.valore)
                y -= 14.4

    overlay_buf = _crea_overlay(disegna)
    lettore_overlay = PdfReader(overlay_buf)
    lettore_template = PdfReader(str(template_path))
    writer = PdfWriter()
    pagina_1 = lettore_template.pages[0]
    pagina_1.merge_page(lettore_overlay.pages[0])
    writer.add_page(pagina_1)
    if len(lettore_template.pages) > 1:
        writer.add_page(lettore_template.pages[1])
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def genera_modulo5_sovrapposto(dichiarazione) -> bytes:
    """Modulo 5 — debiti. Sezione A (privati): ipoteche [I] e finanziamenti
    [P]. Sezione B (aziendali): prestiti PASSIVI dalla propria Sagl/SA
    (l'azienda che presta al contribuente è, dal punto di vista di
    quest'ultimo, un creditore aziendale). I prestiti ATTIVI (il
    contribuente che presta all'azienda) non sono un debito ma un credito:
    non vanno su questo modulo, restano fuori scope per ora."""
    template_path = CARTELLA_MODULI / "Mod5.pdf"
    if not template_path.exists():
        return b""

    c_nome = f"{dichiarazione.contribuente.nome} {dichiarazione.contribuente.cognome}".strip()
    debiti_privati = [d for d in dichiarazione.debiti if d.tipo in ("ipoteca", "finanziamento")]
    debiti_aziendali = [d for d in dichiarazione.debiti if d.tipo == "prestito_sagl_passivo"]

    def disegna(c: canvas.Canvas):
        c.setFont("Helvetica", 9)
        c.drawString(154, 712.5, c_nome)
        if dichiarazione.contribuente.coniuge:
            coniuge = f"{dichiarazione.contribuente.coniuge.nome} {dichiarazione.contribuente.coniuge.cognome}".strip()
            c.drawString(154, 698.5, coniuge)

        c.setFont("Helvetica", 7)
        y = 649.5
        for deb in debiti_privati[:14]:
            genere = "I" if deb.tipo == "ipoteca" else "P"
            c.drawString(90, y, _v(deb.creditore))
            c.drawCentredString(166, y, genere)
            c.drawCentredString(389, y, _v(deb.saldo_31_12))
            c.drawCentredString(480, y, _v(deb.interessi_annui))
            y -= 15.84

        y = 241.5
        for deb in debiti_aziendali[:10]:
            c.drawString(90, y, _v(deb.creditore))
            c.drawCentredString(166, y, "A")
            c.drawCentredString(389, y, _v(deb.saldo_31_12))
            y -= 15.84

    overlay_buf = _crea_overlay(disegna)
    lettore_overlay = PdfReader(overlay_buf)
    lettore_template = PdfReader(str(template_path))
    writer = PdfWriter()
    pagina_1 = lettore_template.pages[0]
    pagina_1.merge_page(lettore_overlay.pages[0])
    writer.add_page(pagina_1)
    if len(lettore_template.pages) > 1:
        writer.add_page(lettore_template.pages[1])
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def genera_modulo1_sovrapposto(dichiarazione) -> bytes:
    """Modulo 1, pagina 'Dati personali' — a differenza degli altri moduli,
    qui non c'è un PDF originale del Cantone (non esiste in versione vuota,
    vedi note di progetto): lo sfondo è uno screenshot pulito fornito dal
    cliente, usato come immagine di sfondo diretta in un nuovo PDF, con lo
    stesso principio di scrittura sopra usato per gli altri moduli."""
    immagine_path = CARTELLA_MODULI / "Mod1_pagina3.png"
    if not immagine_path.exists():
        return b""

    c_ana = dichiarazione.contribuente
    con = c_ana.coniuge

    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    cv.drawImage(str(immagine_path), 0, 0, width=A4[0], height=A4[1])

    cv.setFont("Helvetica", 9)
    cv.drawString(115, 519.5, f"{c_ana.cognome}, {c_ana.nome}".strip(", "))
    if c_ana.data_nascita:
        cv.drawString(115, 489.2, c_ana.data_nascita.strftime("%d.%m.%Y"))
    if c_ana.stato_civile:
        cv.drawString(115, 474.1, c_ana.stato_civile.value)
    cv.drawString(115, 456.0, c_ana.domicilio or "")
    cv.drawString(115, 440.9, c_ana.professione or "")
    cv.drawString(115, 397.0, c_ana.luogo_lavoro or "")
    cv.drawString(115, 380.4, c_ana.attivita_accessoria or "")

    if con:
        cv.drawString(284, 519.5, f"{con.cognome}, {con.nome}".strip(", "))
        if con.data_nascita:
            cv.drawString(284, 489.2, con.data_nascita.strftime("%d.%m.%Y"))
        cv.drawString(284, 456.0, con.domicilio or "")
        cv.drawString(284, 440.9, con.professione or "")

    cv.save()
    buf.seek(0)
    return buf.getvalue()


def genera_modulo4_sovrapposto(dichiarazione) -> bytes:
    """Modulo 4 — spese professionali, un modulo per l'attività principale
    (con i dati del primo certificato di salario). I forfait 3'000/800 e
    il totale sono ripresi dal calcolo automatico già fatto dal wizard."""
    template_path = CARTELLA_MODULI / "Mod4.pdf"
    if not template_path.exists() or not dichiarazione.certificati_salario:
        return b""

    from modules.spese_professionali import _giorni_lavorati, _numero, TARIFFA_KM, FORFAIT_PRINCIPALE, FORFAIT_ACCESSORIA

    c_nome = f"{dichiarazione.contribuente.nome} {dichiarazione.contribuente.cognome}".strip()
    cert = dichiarazione.certificati_salario[0]  # attività principale

    giorni = _giorni_lavorati(cert)
    km_tragitto = _numero(cert.km_tragitto)
    km_totali = km_tragitto * 2 * giorni
    deduzione_trasporto = round(km_totali * TARIFFA_KM, 2)
    forfait_accessoria = FORFAIT_ACCESSORIA if len(dichiarazione.certificati_salario) > 1 else 0
    totale = deduzione_trasporto + FORFAIT_PRINCIPALE + forfait_accessoria

    def disegna(c: canvas.Canvas):
        c.setFont("Helvetica", 9)
        c.drawString(154, 712.5, c_nome)

        c.setFont("Helvetica", 8)
        y_veicolo = 538.0
        c.drawString(192, y_veicolo, dichiarazione.contribuente.domicilio or "")
        c.drawString(312, y_veicolo, _v(cert.comune_datore_lavoro))
        c.drawCentredString(420, y_veicolo, f"{km_tragitto:g}" if km_tragitto else "")
        c.drawCentredString(454, y_veicolo, f"{km_tragitto*2:g}" if km_tragitto else "")
        c.drawCentredString(483, y_veicolo, str(giorni))
        c.drawCentredString(511, y_veicolo, f"{km_totali:g}")

        c.drawCentredString(514, 476.1, f"{deduzione_trasporto:,.2f}".replace(",", "'"))
        c.drawCentredString(514, 138.0, f"{FORFAIT_PRINCIPALE:,.0f}".replace(",", "'"))
        if forfait_accessoria:
            c.drawCentredString(514, 90.5, f"{forfait_accessoria:,.0f}".replace(",", "'"))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(514, 69.1, f"{totale:,.2f}".replace(",", "'"))

    overlay_buf = _crea_overlay(disegna)
    lettore_overlay = PdfReader(overlay_buf)
    lettore_template = PdfReader(str(template_path))
    writer = PdfWriter()
    pagina_1 = lettore_template.pages[0]
    pagina_1.merge_page(lettore_overlay.pages[0])
    writer.add_page(pagina_1)
    if len(lettore_template.pages) > 1:
        writer.add_page(lettore_template.pages[1])
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def genera_modulo7_sovrapposto(immobile, contribuente, numero_immobile: int = 1) -> bytes:
    """Un Modulo 7 per singolo immobile (come richiede il modulo stesso:
    'deve essere compilato un Modulo separato' per ogni immobile)."""
    percorso_template = CARTELLA_MODULI / "Mod7.pdf"
    if not percorso_template.exists():
        return b""

    c_nome = f"{contribuente.nome} {contribuente.cognome}".strip()

    def disegna(c: canvas.Canvas):
        c.setFont("Helvetica", 9)

        # Intestazione (stesse coordinate verificate sul Modulo 8: i moduli
        # ti.ch condividono l'impaginazione dell'intestazione)
        c.drawString(192, 714.7, c_nome)
        if contribuente.coniuge:
            coniuge_nome = f"{contribuente.coniuge.nome} {contribuente.coniuge.cognome}".strip()
            c.drawString(192, 702.7, coniuge_nome)

        # Sezione 1 — dati del fondo (corretto: -10pt rispetto alla prima
        # calibrazione, che risultava sistematicamente una riga troppo alta)
        c.drawString(178, 656.7, _v(immobile.comune))
        c.drawString(427, 656.7, _v(immobile.nazione_cantone) if not immobile.in_svizzera else "Svizzera")
        c.drawString(178, 642.3, _v(immobile.indirizzo))
        c.drawString(427, 642.3, _v(immobile.nazione_cantone) if immobile.in_svizzera else "")
        if immobile.anno_costruzione:
            c.drawCentredString(378, 619.3, str(immobile.anno_costruzione))

        c.setFont("Helvetica-Bold", 9)
        mappa_destinazione_y = {
            "Uso proprio": 660.1,
            "Uso di terzi": 650.5,
            "Uso misto": 637.0,
            "In usufrutto/diritto di abitazione": 627.9,
        }
        y_dest = mappa_destinazione_y.get(immobile.destinazione)
        if y_dest:
            c.drawString(18, y_dest, "X")

        mappa_tipo_y = {
            "Unifamiliare": 587.1,
            "Plurifamiliare": 577.5,
            "Commerciale e abitativa": 568.9,
            "Commerciale": 560.7,
            "Altro": 549.7,
        }
        y_tipo = mappa_tipo_y.get(immobile.tipo_immobile)
        if y_tipo:
            c.drawString(18, y_tipo, "X")

        # Sezione 2 — stima ufficiale (totale)
        c.setFont("Helvetica", 8)
        c.drawCentredString(542, 457.9, _v(immobile.valore_stima_totale))

        # Sezione 4 — reddito
        c.setFont("Helvetica-Bold", 9)
        if immobile.destinazione == "Uso proprio":
            y_check = 378.7 if immobile.abitazione_primaria else 361.9
            c.drawString(108, y_check, "X")
        else:
            c.setFont("Helvetica", 8)
            c.drawCentredString(523, 340.3, _v(immobile.affitti_incassati))
            c.drawCentredString(523, 261.1, _v(immobile.affitti_incassati))
            c.drawCentredString(523, 246.7, _v(immobile.affitti_incassati))

        # Sezione 5 — forfait 10%/20%
        if not immobile.usa_spese_effettive:
            forfait_10 = immobile.anno_costruzione and immobile.anno_costruzione >= 2015
            x_forfait = 219 if forfait_10 else 318
            c.setFont("Helvetica-Bold", 9)
            c.drawString(x_forfait, 215.5, "X")

    overlay_buf = _crea_overlay(disegna)
    lettore_overlay = PdfReader(overlay_buf)
    lettore_template = PdfReader(str(percorso_template))
    writer = PdfWriter()

    pagina_1 = lettore_template.pages[0]
    pagina_1.merge_page(lettore_overlay.pages[0])
    writer.add_page(pagina_1)
    if len(lettore_template.pages) > 1:
        writer.add_page(lettore_template.pages[1])

    out = BytesIO()
    writer.write(out)
    return out.getvalue()

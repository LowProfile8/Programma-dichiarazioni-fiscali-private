"""
core/preventivo_azienda.py — preventivo per la tenuta della contabilità aziendale.

Stesso stile grafico degli altri documenti (stesso logo, stessi font), ma
calibrato pixel per pixel sul modello fornito (margine 72.2pt invece di
52.4pt, usato solo da questo documento). La firma finale, come nel modello,
è «FID LAB Family Office SA» — non Athena — intenzionale, come nel
documento di riferimento.
"""

from dataclasses import dataclass
from datetime import date
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit as _a_capo
from reportlab.pdfgen import canvas

from core.preventivo import ALTEZZA, BOLD, ITAL, LOGO, REG, _Pagina, _data_it, _prezzo, _validita_it

MARGINE = 72.2
FIRMATARIO = "FID LAB FAMILY OFFICE SA"

RATE_PER_MODALITA = {"Mensile": 12, "Trimestrale": 4, "Semestrale": 2, "Annuale": 1}

FORME_GIURIDICHE = [
    "Ditta Individuale", "Società in nome collettivo", "Società in accomandita",
    "Società anonima (SA)", "Società a garanzia limitata (Sagl)", "Altro",
]


@dataclass
class DatiPreventivoAzienda:
    ragione_sociale: str = ""
    sede_legale: str = ""          # via e numero
    npa: str = ""
    comune: str = ""
    numero_idi: str = ""           # facoltativo
    forma_giuridica: str = "Società a garanzia limitata (Sagl)"
    esercizio: int = 2025
    prezzo: str = ""
    iva: str = "esente"            # 'esente' | '8.1' | '2.6'
    modalita_pagamento: str = "Annuale"
    opzione_sede_legale: bool = False
    prezzo_sede_legale: str = ""
    validita: date = None
    data: date = None


def _numero(testo: str) -> float:
    t = (testo or "").strip().replace("'", "").replace("’", "").replace(" ", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return 0.0


def _firma(p: _Pagina, top: float) -> None:
    p.testo(MARGINE, top, FIRMATARIO, 8.3, BOLD)
    p.testo(MARGINE, top + 11.2, "Simone Sciancalepore", 7.6, ITAL)
    p.testo(MARGINE, top + 22.4, "+41779534999", 7.6, ITAL)


def _intestazione(p: _Pagina, d: DatiPreventivoAzienda) -> None:
    cv = p.cv
    cv.drawImage(str(LOGO), MARGINE + 1.2, ALTEZZA - 112.0, width=153.3, height=63.0, mask=None)
    p.testo(MARGINE, 117.4, "ATHENA ADVISORY GROUP SAGL", 8.3, BOLD)
    p.testo(MARGINE, 129.7, "Piazza Borromini 15", 8.3)
    p.testo(MARGINE, 143.0, "6816 Bissone", 8.3)
    p.testo(MARGINE, 157.4, "CHE-270.639.059", 8.3)

    x_dx = 542.5
    p.testo(x_dx, 169.3, "Alla cortese attenzione di:", 7.6, BOLD, "right")
    p.testo(x_dx, 181.5, d.ragione_sociale, 7.6, REG, "right")
    if d.sede_legale:
        p.testo(x_dx, 193.7, d.sede_legale, 7.6, REG, "right")
    p.testo(x_dx, 205.9, f"{d.npa} {d.comune}".strip(), 7.6, REG, "right")

    p.testo(MARGINE, 225.2, f"Bissone, {_data_it(d.data)}", 7.6)


def calcola_importi(d: DatiPreventivoAzienda) -> dict:
    prezzo = _numero(d.prezzo)
    n_rate = RATE_PER_MODALITA.get(d.modalita_pagamento, 1)
    per_rata = prezzo / n_rate if n_rate else prezzo
    return {"prezzo": prezzo, "n_rate": n_rate, "per_rata": _prezzo(f"{per_rata:.2f}")}


def _pagina_preventivo(cv, d: DatiPreventivoAzienda, importi: dict) -> None:
    p = _Pagina(cv)
    _intestazione(p, d)

    x = p.testo(MARGINE, 247.6, "Oggetto: ", 8.3, BOLD)
    p.sottolineato(MARGINE + x, 247.6, f"Preventivo per Servizi Fiduciari - Esercizio {d.esercizio}", 8.3, BOLD)

    p.testo(MARGINE, 270.0, "Egregi Signori,", 8.3)
    for riga, testo in enumerate(_a_capo(
        f"In riferimento alla Vostra richiesta, siamo lieti di presentarVi la nostra proposta per la gestione "
        f"dei servizi fiduciari relativi all'esercizio {d.esercizio}.", REG, 8.3, 542.5 - MARGINE,
    )):
        p.testo(MARGINE, 292.7 + riga * 11.2, testo, 8.3)
    p.testo(MARGINE, 323.8, "Di seguito, i servizi offerti e le relative opzioni di preventivo:", 8.3)

    p.testo(MARGINE, 346.4, "1. Servizi Offerti", 9.0, BOLD)

    p.testo(MARGINE, 370.2, "Servizi Contabili e Amministrativi", 8.3, BOLD)
    for riga, testo in enumerate((
        "Tenuta della contabilità secondo i principi contabili svizzeri",
        "Redazione del bilancio annuale e del conto economico",
        "Chiusure contabili periodiche",
        "Gestione della reportistica finanziaria e gestionale",
    )):
        p.testo(MARGINE, 381.4 + riga * 11.2, testo, 8.3)

    p.testo(MARGINE, 437.4, "Servizi Fiscali", 8.3, BOLD)
    sigla = "PF" if d.forma_giuridica == "Ditta Individuale" else "PG"
    for riga, testo in enumerate((
        f"Compilazione e presentazione della dichiarazione fiscale delle {sigla}",
        "Dichiarazioni IVA trimestrali e annuali",
        "Consulenza continuativa per ottimizzazione fiscale e conformità normativa",
    )):
        p.testo(MARGINE, 448.5 + riga * 11.2, testo, 8.3)

    p.testo(MARGINE, 493.3, "Gestione del Personale e Oneri Sociali", 8.3, BOLD)
    for riga, testo in enumerate((
        "Elaborazione delle buste paga e adempimenti correlati",
        "Gestione delle dichiarazioni agli enti previdenziali e assicurativi",
        "Contrattualistica del personale",
        "Calcolo e versamento oneri sociali",
    )):
        p.testo(MARGINE, 504.5 + riga * 11.2, testo, 8.3)

    x = p.testo(
        MARGINE, 560.7,
        "Il presente preventivo è valido esclusivamente per i servizi fiduciari a partire dall'esercizio ",
        6.9, ITAL,
    )
    p.sottolineato(MARGINE + x, 560.7, str(d.esercizio), 6.9, ITAL)
    # Testo lungo: va a capo da solo entro il margine standard (542.5), invece di restare fisso su
    # due righe — con un font diverso da quello (incorporato) del documento originale, la stessa
    # riga sarebbe uscita quasi dal foglio.
    for riga, testo in enumerate(_a_capo(
        "e presuppone la chiusura contabile e fiscale degli esercizi precedenti. Eventuali attività relative a "
        "esercizi precedenti saranno oggetto di separata valutazione e preventivo.", ITAL, 6.9, 542.5 - MARGINE,
    )):
        p.testo(MARGINE, 568.6 + riga * 8.6, testo, 6.9, ITAL)

    p.testo(MARGINE, 601.7, "Opzioni di Preventivo", 9.0, BOLD)
    p.testo(
        MARGINE, 625.5,
        f"Descrizione: Gestione completa dei servizi fiduciari sopraelencati per la {d.ragione_sociale}", 8.3,
    )
    suffisso_iva = "" if d.iva == "esente" else " + IVA"
    p.testo(MARGINE, 636.7, f"Costo Annuale: CHF {_prezzo(d.prezzo)}{suffisso_iva}", 8.3)
    p.testo(
        MARGINE, 647.9,
        f"Modalità di Pagamento: {d.modalita_pagamento} — Rate {importi['n_rate']} da "
        f"CHF {importi['per_rata']}{suffisso_iva}", 8.3,
    )
    if d.opzione_sede_legale:
        p.testo(
            MARGINE, 661.0,
            f"Opzione Sede Legale (se richiesta): Supplemento di CHF {_prezzo(d.prezzo_sede_legale)}{suffisso_iva} / mese",
            8.3,
        )

    p.testo(MARGINE, 692.6, f"Validità del Preventivo: Fino al {_validita_it(d.validita)}.", 8.3)
    p.testo(MARGINE, 726.2, "Cordiali saluti,", 8.3)
    _firma(p, 759.8)


def _pagina_documenti(cv, d: DatiPreventivoAzienda) -> None:
    p = _Pagina(cv)
    _intestazione(p, d)
    p.testo(MARGINE, 243.3, "Documentazione", 9.0, BOLD)
    p.testo(
        MARGINE, 276.3,
        "Per poter svolgere al meglio le pratiche contabili, necessiteremmo della seguente documentazione:",
        7.6, ITAL,
    )
    documenti = [
        "Statuto societario", "Bilanci e Conto Economici degli ultimi 5 Anni (se disponibili)",
        "Verbali d'Assemblea Generali e Straordinari, decisioni di ripartizione dell'utile, allegati al bilancio",
        "Schede contabili degli ultimi 5 Anni", "Dichiarazioni fiscali degli ultimi 5 Anni",
        "Decisioni di tassazione degli ultimi 5 Anni", "Estratti Conto dell'anno Corrente",
        "Contratti di lavoro, buste paga dell'anno in corso", "Contratti di affitto, contratti cauzione locali",
        "Dichiarazioni AVS, LPP, IF degli ultimi 3 anni", "Dichiarazioni IVA ultimi 3 anni",
        "Polizze Assicurazioni Infortunio e Malattia", "Polizze Assicurazioni RC, PMI, Varie",
        "Polizza Assicurazione LPP", "Accessi ai portali: IVA, LPP",
        "Controlli e Risultati: Fiscali, IVA, AVS, IF, contratti di categoria",
    ]
    for riga, testo in enumerate(documenti):
        p.testo(MARGINE, 318.1 + riga * 11.0, f"- {testo}", 8.3)

    top_eventualmente = 318.1 + len(documenti) * 11.0 + 33.0
    p.testo(MARGINE, top_eventualmente, "Eventualmente", 8.3, BOLD)
    eventuali = [
        "Contratto di Acquisto Azioni/Quote Sociali", "Contratto di Acquisto Inventario",
        "Contratti di prestito vs soci", "Contratti di prestito vs terzi", "Contratti di Subaffitto Locali",
        "Contratti di Acquisto/Finanziamento/Leasing Veicoli", "Contratti di Collaborazione con terzi",
    ]
    for riga, testo in enumerate(eventuali):
        p.testo(MARGINE, top_eventualmente + 11.0 + riga * 11.0, f"- {testo}", 8.3)

    _firma(p, 760.4)


def genera_preventivo_azienda(d: DatiPreventivoAzienda) -> bytes:
    d.data = d.data or date.today()
    d.validita = d.validita or date.today()
    importi = calcola_importi(d)

    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    cv.setTitle(f"Preventivo tenuta contabilità {d.ragione_sociale}")
    cv.setAuthor(FIRMATARIO)

    _pagina_preventivo(cv, d, importi)
    cv.showPage()
    _pagina_documenti(cv, d)
    cv.showPage()

    cv.save()
    return buf.getvalue()

"""
core/preventivo.py — preventivo per i servizi fiduciari (2 pagine).

Riproduce esattamente il documento di riferimento (stesse intestazioni,
stesso testo, stesse posizioni: logo, blocco mittente, destinatario, oggetto,
elenco documenti, offerta): cambiano solo cliente e indirizzo, data (oggi),
esercizio fiscale, titolo (Sig./Sig.ra/Sigg.), prezzo e validità.

Il testo è in Helvetica (metriche identiche ad Arial, il font dell'originale);
le posizioni sono quelle del documento originale, misurate una per una.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

LOGO = Path(__file__).parent.parent / "assets" / "preventivo" / "logo_athena.png"
ALTEZZA = 841.8898
NERO = (0, 0, 0)

REG, BOLD, ITAL = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
RAPPORTO_BASE = 0.775   # calibrato sul documento originale (scarto verticale misurato: 0)

MESI = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto",
        "Settembre", "Ottobre", "Novembre", "Dicembre"]

TITOLI = {
    "Sig.": ("Sig.", "per il Sig."),
    "Sig.ra": ("Sig.ra", "per la Sig.ra"),
    "Sigg.": ("Sigg.", "per i Sigg."),
}


@dataclass
class DatiPreventivo:
    titolo: str = "Sig."
    cognome: str = ""
    nome: str = ""
    via: str = ""
    npa: str = ""
    comune: str = ""
    esercizio: int = 2025
    prezzo: str = ""
    validita: date = None
    data: date = None

    def nome_completo(self) -> str:
        return f"{self.nome} {self.cognome}".strip()


def fine_mese(d: date) -> date:
    primo_prossimo = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return primo_prossimo - timedelta(days=1)


def _prezzo(testo: str) -> str:
    """'300' → '300'; '1200' → '1'200'; '1200.5' → '1'200.50'; testo libero resta com'è."""
    t = (testo or "").strip().replace("CHF", "").replace("+ IVA", "").strip()
    pulito = t.replace("'", "").replace("’", "").replace(" ", "").replace(",", ".")
    try:
        v = float(pulito)
    except ValueError:
        return t
    if abs(v - round(v)) < 0.005:
        return f"{int(round(v)):,}".replace(",", "'")
    return f"{v:,.2f}".replace(",", "'")


def _data_it(d: date) -> str:
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def _validita_it(d: date) -> str:
    return f"{d.day} {MESI[d.month - 1]} {d.year}"


class _Pagina:
    def __init__(self, cv):
        self.cv = cv

    def testo(self, x: float, top: float, s: str, size: float = 8.3, font: str = REG, allinea: str = "left") -> float:
        """Scrive `s` con il bordo superiore a `top` (convenzione di pdfplumber); ritorna la larghezza."""
        w = stringWidth(s, font, size)
        x0 = x - w if allinea == "right" else x
        self.cv.setFont(font, size)
        self.cv.setFillColorRGB(*NERO)
        self.cv.drawString(x0, ALTEZZA - (top + RAPPORTO_BASE * size), s)
        return w

    def sequenza(self, x: float, top: float, parti: list, size: float = 8.3) -> None:
        """Pezzi di testo con stili diversi sulla stessa riga: [(testo, font), ...]."""
        for s, font in parti:
            x += self.testo(x, top, s, size, font)

    def sottolineato(self, x: float, top: float, s: str, size: float = 8.3, font: str = BOLD) -> None:
        w = self.testo(x, top, s, size, font)
        y = ALTEZZA - (top + RAPPORTO_BASE * size + 1.6)
        self.cv.setLineWidth(0.6)
        self.cv.line(x, y, x + w, y)


def _intestazione(p: _Pagina, d: DatiPreventivo, pagina: int) -> None:
    cv = p.cv
    x0_logo, x1_logo = (53.6, 206.5) if pagina == 1 else (54.2, 207.1)
    cv.drawImage(str(LOGO), x0_logo, ALTEZZA - 122.8, width=x1_logo - x0_logo, height=63.0, mask=None)
    corpo = 8.3 if pagina == 1 else 9.1
    top_rs = 129.7 if pagina == 1 else 128.9
    p.testo(52.4, top_rs, "ATHENA ADVISORY GROUP SAGL", corpo, BOLD)
    p.testo(52.4, 142.3, "Athena Advisory Group Sagl", 9.1)
    p.testo(52.4, 156.9, "6816 Bissone", 9.1)
    p.testo(52.4, 171.5, "CHE-270.639.059", 9.1)

    # destinatario, allineato a destra
    x_dx = 542.5
    p.testo(x_dx, 207.9, "Alla cortese attenzione di:", 8.3, BOLD, "right")
    p.testo(x_dx, 220.1, d.nome_completo(), 8.3, REG, "right")
    p.testo(x_dx, 232.4, d.via, 8.3, REG, "right")
    p.testo(x_dx, 244.6, f"{d.npa} {d.comune}".strip(), 8.3, REG, "right")
    p.testo(52.4, 269.1, f"Lugano, {_data_it(d.data)}", 8.3)


def _firma(p: _Pagina) -> None:
    p.testo(52.4, 699.1, "ATHENA ADVISORY GROUP SAGL", 8.3, BOLD)
    p.testo(52.4, 711.4, "Simone Sciancalepore", 8.3, ITAL)
    p.testo(52.4, 723.7, "+41(0)779534999", 8.3, ITAL)


def _pagina_documenti(cv, d: DatiPreventivo) -> None:
    p = _Pagina(cv)
    a = d.esercizio
    _intestazione(p, d, 1)
    x = p.testo(52.4, 293.6, "Oggetto: ", 8.3, BOLD)
    p.sottolineato(52.4 + x, 293.6,
                   f"Documentazione necessaria alla compilazione della dichiarazione fiscale privata {a} e calcolo dispendio")
    voci = [
        (352.6, "- Formulario Dichiarazione Fiscale (N° Controllo e Password in prima pagina)"),
        (377.1, "- Dichiarazione Fiscale anno precedente (modulo + decisione)"),
        (401.6, "- Documenti Identità Personali"),
        (427.8, f"- Attestato Banca al 31.12.{a}, conti privati Svizzeri e ev. conti Esteri"),
        (452.3, f"- Ev. Attestato Banca al 31.12.{a} - Investimenti Finanziari (dettaglio Azioni, Bond, Opzioni)"),
        (476.8, f"- Certificato di Salario {a}"),
        (501.3, "- Certificato Fiscale Cassa Malati + Eventuali spese mediche"),
        (527.6, "- Certificato 3° Pilastro / Assicurazioni private / Polizza Vita"),
        (552.1, "- Se immobili: Decisione di tassazione della stima ufficiale (da richiedere all'ufficio cantonale o tramite eportal)"),
        (576.6, "- Dettagli veicolo di proprietà (prezzo di acquisto, anno, valore attuale)"),
    ]
    for top, testo in voci:
        p.testo(52.4, top, testo)
    _firma(p)


def _pagina_preventivo(cv, d: DatiPreventivo) -> None:
    p = _Pagina(cv)
    a = d.esercizio
    _intestazione(p, d, 2)
    x = p.testo(52.4, 293.6, "Oggetto: ", 8.3, BOLD)
    p.sottolineato(52.4 + x, 293.6,
                   f"Preventivo per Servizi Fiduciari - Compilazione Dichiarazione fiscale delle PF {a} e calcolo dispendio")
    p.testo(52.4, 318.1, "Egregi Signori,")
    p.testo(52.4, 343.0, "In riferimento alla Vostra richiesta, siamo lieti di presentarVi la nostra proposta per la gestione dei "
                         "servizi fiduciari relativi alla")
    p.sequenza(52.4, 352.6, [
        ("compilazione della Dichiarazione Fiscale per ", REG), ("Persone Fisiche", BOLD),
        (" dell'esercizio ", REG), (str(a), BOLD), (", con relativo calcolo del dispendio.", REG),
    ])
    p.testo(52.4, 377.1, "Di seguito, i servizi offerti e le relative opzioni di preventivo:")
    p.testo(52.4, 414.1, "1. Servizi Offerti", 9.9, BOLD)
    p.testo(52.4, 440.1, "Servizi Fiscali", 8.3, BOLD)
    p.testo(52.4, 452.3, f"Compilazione completa del modulo della dichiarazione d'imposta {a}.")
    p.testo(52.4, 464.6, "Calcolo del Dispendio qualora applicabile ai sensi della legislazione ticinese.")
    p.testo(52.4, 476.8, "Consulenza sulle deduzioni ammissibili e verifica degli attestati fiscali.")
    p.testo(52.4, 513.8, "2. Preventivo", 9.9, BOLD)
    _, per = TITOLI.get(d.titolo, TITOLI["Sig."])
    p.testo(52.4, 539.9, f"Descrizione: Gestione completa dei servizi fiduciari sopraelencati {per} {d.nome_completo()}")
    p.testo(52.4, 552.1, f"Costo Annuale: CHF {_prezzo(d.prezzo)} + IVA")
    p.testo(52.4, 564.4, "Modalità di Pagamento: Fatturazione unica")
    p.testo(52.4, 613.4, f"Validità del Preventivo: Fino al {_validita_it(d.validita)}.")
    p.testo(52.4, 662.4, "Cordiali saluti,")
    _firma(p)


def genera_preventivo(d: DatiPreventivo) -> bytes:
    """PDF di 2 pagine: documentazione necessaria + preventivo."""
    d.data = d.data or date.today()
    d.validita = d.validita or fine_mese(d.data)
    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    cv.setTitle(f"Preventivo {d.nome_completo()}".strip())
    cv.setAuthor("Athena Advisory Group Sagl")
    _pagina_documenti(cv, d)
    cv.showPage()
    _pagina_preventivo(cv, d)
    cv.showPage()
    cv.save()
    return buf.getvalue()

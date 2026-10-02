"""
core/dispendio_pdf.py — estratto del calcolo del dispendio, una sola pagina A4.

Struttura: intestazione con i dati della persona (e numero di registro) →
redditi → spese e deduzioni → risparmio generato → variazione di liquidità
(conti e titoli) → altri movimenti di capitale (se ci sono) → verifica con
verdetto in verde (coerente) o in rosso (da verificare).
File separato dalla dichiarazione: non va allegato all'invio.
"""

from datetime import date
from io import BytesIO
from pathlib import Path

from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from core.dispendio import calcola_dispendio

LOGO = Path(__file__).parent.parent / "assets" / "preventivo" / "logo_athena.png"
W, H = A4
M_SX, M_DX = 44.0, W - 44.0

BLU = Color(0.10, 0.25, 0.55)
GRIGIO_TESTO = Color(0.42, 0.44, 0.48)
GRIGIO_FONDO = Color(0.955, 0.96, 0.97)
BARRA = Color(0.925, 0.94, 0.975)
LINEA = Color(0.78, 0.80, 0.84)
NERO = Color(0.10, 0.10, 0.12)

VERDE_FONDO, VERDE_BORDO, VERDE_TESTO = Color(0.90, 0.96, 0.91), Color(0.25, 0.60, 0.30), Color(0.09, 0.36, 0.14)
ROSSO_FONDO, ROSSO_BORDO, ROSSO_TESTO = Color(1.0, 0.93, 0.90), Color(0.80, 0.25, 0.18), Color(0.58, 0.11, 0.07)

REG, BOLD, ITAL = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
MAX_POSIZIONI = 16   # oltre questo numero le posizioni minori vengono raggruppate, per restare in una pagina


def _fr(x: float, segno: bool = False) -> str:
    n = int(round(abs(x)))
    testo = f"{n:,}".replace(",", "'")
    if x < -0.5:
        return f"-{testo}"
    return f"+{testo}" if segno and n else testo


def _raggruppa(posizioni: list) -> list:
    if len(posizioni) <= MAX_POSIZIONI:
        return posizioni
    ordinate = sorted(posizioni, key=lambda p: -abs(p["importo"]))
    principali, resto = ordinate[: MAX_POSIZIONI - 1], ordinate[MAX_POSIZIONI - 1:]
    principali.append({"tipo": "Altre posizioni", "denominazione": f"{len(resto)} posizioni minori",
                       "importo": sum(p["importo"] for p in resto)})
    return principali


class _Foglio:
    def __init__(self, cv, passo: float, corpo: float):
        self.cv, self.passo, self.corpo, self.y = cv, passo, corpo, 0.0

    def testo(self, x, y, s, size=None, font=REG, colore=NERO, allinea="left"):
        size = size or self.corpo
        w = stringWidth(s, font, size)
        self.cv.setFillColor(colore)
        self.cv.setFont(font, size)
        self.cv.drawString(x - w if allinea == "right" else (x - w / 2 if allinea == "center" else x), H - y, s)
        return w

    def barra(self, titolo: str) -> None:
        self.y += 3
        self.cv.setFillColor(BARRA)
        self.cv.rect(M_SX, H - (self.y + 12.5), M_DX - M_SX, 12.5, fill=1, stroke=0)
        self.testo(M_SX + 6, self.y + 9.2, titolo.upper(), 7.6, BOLD, BLU)
        self.y += 12.5 + 2

    def riga(self, etichetta: str, importo: float, nota: str = "", grassetto=False, segno=False, colore=NERO, rientro=0):
        self.y += self.passo
        base = self.y - 2.6
        w = self.testo(M_SX + 6 + rientro, base, etichetta, self.corpo, BOLD if grassetto else REG, colore)
        if nota:
            self.testo(M_SX + 6 + rientro + w + 6, base, nota, self.corpo - 1.4, ITAL, GRIGIO_TESTO)
        self.testo(M_DX - 6, base, _fr(importo, segno), self.corpo, BOLD if grassetto else REG, colore, "right")

    def totale(self, etichetta: str, importo: float, colore=NERO) -> None:
        self.cv.setStrokeColor(LINEA)
        self.cv.setLineWidth(0.5)
        self.cv.line(M_SX + 6, H - (self.y + 2.2), M_DX - 6, H - (self.y + 2.2))
        self.y += 1.5
        self.riga(etichetta, importo, grassetto=True, colore=colore)
        self.y += 2


def _intestazione(cv, d, dati: dict) -> float:
    c = d.contribuente
    if LOGO.exists():
        cv.drawImage(str(LOGO), M_SX - 4, H - 84, width=100, height=41.5, mask=None)
    cv.setFillColor(NERO)
    cv.setFont(BOLD, 17)
    cv.drawRightString(M_DX, H - 52, "Calcolo del dispendio")
    cv.setFillColor(GRIGIO_TESTO)
    cv.setFont(REG, 9.5)
    cv.drawRightString(M_DX, H - 66, f"Esercizio {d.anno_fiscale}")
    cv.setFont(ITAL, 7.4)
    cv.drawRightString(M_DX, H - 78, "Documento di lavoro: non fa parte della dichiarazione d'imposta")
    cv.setStrokeColor(BLU)
    cv.setLineWidth(1.1)
    cv.line(M_SX, H - 92, M_DX, H - 92)

    # riquadro della persona
    alto, basso = 100, 148
    cv.setFillColor(GRIGIO_FONDO)
    cv.roundRect(M_SX, H - basso, M_DX - M_SX, basso - alto, 4, fill=1, stroke=0)

    def blocco(x, titolo, righe):
        cv.setFillColor(GRIGIO_TESTO)
        cv.setFont(BOLD, 6.8)
        cv.drawString(x, H - 112, titolo.upper())
        cv.setFillColor(NERO)
        for k, riga in enumerate(r for r in righe if r):
            cv.setFont(BOLD if k == 0 else REG, 8.8 if k == 0 else 8.2)
            cv.drawString(x, H - (124 + 11.5 * k), riga)

    blocco(M_SX + 10, "Contribuente", [
        f"{c.nome} {c.cognome}".strip(), c.indirizzo, f"{c.npa} {c.domicilio}".strip(),
    ])
    if c.coniuge is not None:
        blocco(M_SX + 190, "Coniuge / partner registrato", [f"{c.coniuge.nome} {c.coniuge.cognome}".strip()])
    blocco(M_DX - 115, "Numero di registro", [d.numero_controllo or "—"])
    return basso + 6


def genera_pdf_dispendio(d, oggi: date = None) -> bytes:
    r = calcola_dispendio(d)
    oggi = oggi or date.today()
    posizioni = _raggruppa(r["posizioni"])

    # righe totali → passo verticale adattato per stare sempre in una pagina
    n_righe = (len(r["redditi"]) + len(r["spese"]) + len(posizioni) + len(r["movimenti"]) + 14)
    disponibile = 806 - 156 - 4 * 18 - 96
    passo = max(9.4, min(12.6, disponibile / max(n_righe, 1)))
    corpo = 8.6 if passo >= 11.4 else (8.0 if passo >= 10.2 else 7.4)

    buf = BytesIO()
    cv = canvas.Canvas(buf, pagesize=A4)
    cv.setTitle(f"Calcolo del dispendio {d.anno_fiscale}")
    cv.setAuthor("Athena Advisory Group Sagl")
    y0 = _intestazione(cv, d, r)
    f = _Foglio(cv, passo, corpo)
    f.y = y0

    # 1. Redditi
    f.barra("1 · Redditi")
    if r["redditi"]:
        for v in r["redditi"]:
            f.riga(v["voce"], v["importo"], v["nota"])
    else:
        f.riga("Nessun reddito inserito", 0)
    f.totale("Totale redditi", r["totale_redditi"])
    if r["valore_locativo"]:
        f.riga("Valore locativo: reddito figurativo, non in contanti (non conteggiato)", r["valore_locativo"], colore=GRIGIO_TESTO)
    # 2. Spese e deduzioni
    f.barra("2 · Spese e deduzioni")
    if r["spese"]:
        for v in r["spese"]:
            f.riga(v["voce"], v["importo"], v["nota"])
    else:
        f.riga("Nessuna spesa inserita", 0)
    f.totale("Totale spese e deduzioni", r["totale_spese"])

    # Risparmio
    f.y += 2
    cv.setFillColor(GRIGIO_FONDO)
    cv.rect(M_SX, H - (f.y + passo + 4), M_DX - M_SX, passo + 4, fill=1, stroke=0)
    f.riga("Risparmio generato nell'anno (redditi − spese)".replace("−", "-"), r["risparmio"], grassetto=True, colore=BLU)
    f.y += 4

    # 3. Liquidità
    f.barra("3 · Liquidità: conti e titoli al 31.12")
    for p in posizioni:
        f.riga(f"{p['tipo']}", p["importo"], p["denominazione"], rientro=0)
    f.totale(f"Totale conti e titoli al 31.12.{d.anno_fiscale}", r["liquidita_attuale"])
    if r["calcolabile"]:
        f.riga(f"Totale conti e titoli al 31.12.{d.anno_fiscale - 1}", r["liquidita_precedente"], "dalla dichiarazione dell'anno precedente")
        f.riga("Variazione della liquidità nell'anno", r["variazione"], grassetto=True, segno=True)
    else:
        f.riga("Somma dei conti e titoli dell'anno scorso non indicata: variazione non calcolabile", 0, colore=ROSSO_TESTO)

    # 4. Movimenti di capitale
    if r["movimenti"]:
        f.barra("4 · Altri movimenti di capitale (non sono redditi)")
        for v in r["movimenti"]:
            f.riga(v["voce"], v["importo"], v["nota"], segno=True)
        f.totale("Totale altri movimenti", r["totale_movimenti"])

    # Verifica
    f.barra("Verifica" if not r["movimenti"] else "5 · Verifica")
    f.riga("Risparmio generato", r["risparmio"])
    if r["movimenti"]:
        f.riga("Altri movimenti di capitale", r["totale_movimenti"], segno=True)
    f.riga("Crescita di liquidità spiegabile", r["crescita_spiegabile"], grassetto=True)
    if r["calcolabile"]:
        f.riga("Variazione effettiva della liquidità", -r["variazione"], "da sottrarre", segno=True)
        f.totale("Risultato del calcolo del dispendio", r["risultato"], VERDE_TESTO if r["coerente"] else ROSSO_TESTO)

    # Verdetto
    f.y += 4
    if not r["calcolabile"]:
        fondo, bordo, colore = GRIGIO_FONDO, LINEA, GRIGIO_TESTO
        titolo = "Calcolo non completo"
        messaggio = ("Indicare la somma dei titoli e dei conti dell'anno scorso (Modulo 2 della dichiarazione "
                     "precedente, Totale colonna Sostanza) per poter confrontare la variazione di liquidità.")
    elif r["coerente"]:
        fondo, bordo, colore = VERDE_FONDO, VERDE_BORDO, VERDE_TESTO
        titolo = "Il calcolo è corretto"
        messaggio = (f"Le spese sono state coerenti con i redditi: la liquidità è variata di Fr. {_fr(r['variazione'], True)}, "
                     f"entro il risparmio generato nell'anno (Fr. {_fr(r['crescita_spiegabile'])}). "
                     "Non emergono differenze da spiegare.")
    else:
        fondo, bordo, colore = ROSSO_FONDO, ROSSO_BORDO, ROSSO_TESTO
        titolo = "Attenzione: dichiarazione da verificare"
        messaggio = (f"Le spese sono state troppo alte rispetto ai redditi: la liquidità è cresciuta di Fr. {_fr(r['variazione'])}, "
                     f"più di quanto il risparmio generato consenta (Fr. {_fr(r['crescita_spiegabile'])}); "
                     f"differenza da spiegare: Fr. {_fr(-r['risultato'])}. "
                     "La dichiarazione è da verificare nuovamente sulla base del cash flow privato effettivamente avvenuto.")
    righe_msg = simpleSplit(messaggio, REG, 8.4, M_DX - M_SX - 34)
    altezza_box = 22 + 11 * len(righe_msg)
    cv.setFillColor(fondo)
    cv.setStrokeColor(bordo)
    cv.setLineWidth(0.9)
    cv.roundRect(M_SX, H - (f.y + altezza_box), M_DX - M_SX, altezza_box, 4, fill=1, stroke=1)
    cv.setFillColor(bordo)
    cv.rect(M_SX, H - (f.y + altezza_box), 5, altezza_box, fill=1, stroke=0)
    f.testo(M_SX + 16, f.y + 14, titolo, 9.6, BOLD, colore)
    for k, riga in enumerate(righe_msg):
        f.testo(M_SX + 16, f.y + 27 + 11 * k, riga, 8.4, REG, colore)
    f.y += altezza_box + 6

    # Note di metodo (piccole, in fondo)
    note = ("Metodo: risparmio generato = redditi − spese e deduzioni; il risultato è la crescita di liquidità spiegabile meno la variazione "
            "effettiva di conti e titoli (≥ 0 = coerente). Criterio prudente: valore locativo (figurativo) escluso dai redditi; deduzioni "
            "sociali (figli, coniuge, doppio reddito) escluse dalle spese; imposta preventiva trattenuta (35%) sottratta.")
    for k, riga in enumerate(simpleSplit(note.replace("−", "-"), ITAL, 6.6, M_DX - M_SX)):
        f.testo(M_SX, f.y + 7 + 8.2 * k, riga, 6.6, ITAL, GRIGIO_TESTO)
    cv.setFillColor(GRIGIO_TESTO)
    cv.setFont(REG, 6.8)
    cv.drawRightString(M_DX, 18, f"Elaborato il {oggi:%d.%m.%Y}")
    cv.drawString(M_SX, 18, "Athena Advisory Group Sagl")
    cv.showPage()
    cv.save()
    return buf.getvalue()

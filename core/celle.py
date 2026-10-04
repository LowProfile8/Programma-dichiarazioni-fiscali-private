"""
core/celle.py — scrittura precisa dentro le caselle dei moduli ufficiali.

Tutte le coordinate sono in PUNTI nel sistema «visivo» della pagina (origine
in alto a sinistra, y verso il basso — lo stesso che restituisce pdfplumber
leggendo i PDF vuoti del Cantone). Le caselle di ogni campo sono state
ricavate dalla geometria vettoriale dei moduli ufficiali, non a occhio.

Le caselle a cifra singola dei moduli hanno passo 12.2 pt (cella 11.3 pt):
qui ogni cifra viene centrata nella sua casella, allineando l'importo a
destra come si farebbe a mano. Dove il campo prevede i centesimi (colonne
«Fr. / Cts.») le ultime due caselle sono i centesimi.
"""

from reportlab.pdfbase.pdfmetrics import stringWidth

ALTEZZA_A4 = 841.8898

PASSO = 12.2          # distanza tra i centri di due caselle consecutive
META_CELLA = 5.65     # metà larghezza della cella (11.3 / 2)
BORDO_DX = 1.2        # bordo destro del campo → bordo destro dell'ultima cella (solo franchi)
BORDO_DX_CTS = 1.6    # idem, ma per l'ultima cella dei centesimi
STACCO_CTS = 29.5     # bordo destro del campo → bordo destro dell'ultima cella dei franchi (con centesimi)

FONT = "Helvetica"
FONT_B = "Helvetica-Bold"


def fmt_spazio(n: int) -> str:
    """10000 → '10 000' (separatore delle migliaia come nelle stampe di eTax)."""
    return f"{n:,}".replace(",", " ")


class Scrittore:
    """Scrive sul canvas di reportlab usando coordinate visive (top-origin).

    rotata=True per la pagina del Modulo 2 (tabella in orizzontale, ottenuta
    con /Rotate 90): il contenuto è ruotato di 90° rispetto a ciò che si vede,
    verificato con punti colorati misurati via analisi dell'immagine."""

    def __init__(self, cv, rotata: bool = False, altezza: float = ALTEZZA_A4):
        self.cv = cv
        self.rotata = rotata
        self.H = altezza

    # ── primitive ──────────────────────────────────────────────────────
    def _disegna(self, x_sx: float, top_base: float, s: str, font: str, size: float) -> None:
        cv = self.cv
        cv.setFont(font, size)
        if not self.rotata:
            cv.drawString(x_sx, self.H - top_base, s)
        else:
            cv.saveState()
            cv.translate(top_base, x_sx)  # x contenuto = top visivo, y contenuto = x visivo
            cv.rotate(90)
            cv.drawString(0, 0, s)
            cv.restoreState()

    def testo(self, x: float, top_base: float, s: str, allinea: str = "left",
              font: str = FONT, size: float = 8.0) -> None:
        if s is None or s == "":
            return
        w = stringWidth(s, font, size)
        if allinea == "right":
            x_sx = x - w
        elif allinea == "center":
            x_sx = x - w / 2
        else:
            x_sx = x
        self._disegna(x_sx, top_base, s, font, size)

    @staticmethod
    def _base(box, size: float) -> float:
        """Linea di base che centra verticalmente il testo (cifre/maiuscole) nel riquadro."""
        _, _, top, bot = box
        return (top + bot) / 2 + size * 0.36

    # ── testo in riquadro ──────────────────────────────────────────────
    def testo_in_box(self, box, s: str, size: float = 8.0, pad: float = 3.0, allinea: str = "left",
                     font: str = FONT, min_size: float = 5.0) -> None:
        """Testo centrato in verticale nel riquadro; rimpicciolisce se non ci sta."""
        if not s:
            return
        x0, x1, _, _ = box
        larghezza = (x1 - x0) - 2 * pad
        while size > min_size and stringWidth(s, font, size) > larghezza:
            size -= 0.25
        if allinea == "left":
            x = x0 + pad
        elif allinea == "right":
            x = x1 - pad
        else:
            x = (x0 + x1) / 2
        self.testo(x, self._base(box, size), s, allinea, font, size)

    # ── una cifra per casella ──────────────────────────────────────────
    def cifre(self, box, valore, centesimi: bool = False, size: float = 8.5, font: str = FONT) -> bool:
        """Scrive `valore` (numero) una cifra per casella, allineato a destra.

        box = (x0, x1, top, bottom) dell'INTERO campo, centesimi compresi.
        Valori nulli/zero → campo lasciato vuoto (nei moduli vuoto = 0).
        Restituisce False se il numero non entra nelle caselle (in tal caso
        lo scrive comunque come testo compatto, così non si perde)."""
        try:
            v = float(valore or 0)
        except (TypeError, ValueError):
            return True
        if abs(v) < 0.005:
            return True
        x0, x1, _, _ = box
        base = self._base(box, size)
        if centesimi:
            totale_cts = int(round(abs(v) * 100))
            franchi, cts = divmod(totale_cts, 100)
            cx_cts_unita = x1 - BORDO_DX_CTS - META_CELLA
            self.testo(cx_cts_unita, base, str(cts % 10), "center", font, size)
            self.testo(cx_cts_unita - PASSO, base, str(cts // 10), "center", font, size)
            cx0 = x1 - STACCO_CTS - META_CELLA
            bordo_dx_franchi = x1 - STACCO_CTS
        else:
            franchi = int(round(abs(v)))
            cx0 = x1 - BORDO_DX - META_CELLA
            bordo_dx_franchi = x1 - BORDO_DX
        cifre_str = str(franchi)
        # caselle disponibili: campi da 3 celle misurano 37.2 pt (passo reale 12.4): l'arrotondamento evita di perderne una
        n_celle = int(round((bordo_dx_franchi + BORDO_DX - x0) / PASSO))
        if len(cifre_str) > n_celle:
            self.testo_in_box(box, fmt_spazio(franchi), size=7, allinea="right")
            return False
        for k, c in enumerate(reversed(cifre_str)):
            self.testo(cx0 - k * PASSO, base, c, "center", font, size)
        return True

    def lettere_in_celle(self, box, s: str, size: float = 8.5, font: str = FONT) -> None:
        """Sigle brevi (P, CC, OB…) una lettera per casella, da sinistra."""
        if not s:
            return
        x0, _, _, _ = box
        base = self._base(box, size)
        for k, ch in enumerate(s):
            self.testo(x0 + 0.8 + META_CELLA + k * PASSO, base, ch, "center", font, size)

    def cifre_ai_centri(self, centri, top: float, bottom: float, testo: str, size: float = 8.5) -> None:
        """Una cifra per ciascun centro-casella dato (per le date GG/MM con la barra già stampata)."""
        base = (top + bottom) / 2 + size * 0.36
        for cx, ch in zip(centri, testo):
            self.testo(cx, base, ch, "center", FONT, size)

    def x_in_box(self, box, size: float = 9.5) -> None:
        """Casella di spunta selezionata: nelle stampe di eTax (verificato su tre dichiarazioni
        reali, in tutti i moduli) la casella spuntata è un quadrato nero pieno, non una «X»."""
        x0, x1, top, bot = box
        cv = self.cv
        cv.saveState()
        cv.setFillColorRGB(0, 0, 0)
        if self.rotata:
            cv.rect(top, x0, bot - top, x1 - x0, fill=1, stroke=0)
        else:
            cv.rect(x0, self.H - bot, x1 - x0, bot - top, fill=1, stroke=0)
        cv.restoreState()


def riga_top(primo_top: float, passo: float, k: int, altezza: float):
    """(top, bottom) della k-esima riga di una tabella con passo costante."""
    top = primo_top + passo * k
    return top, top + altezza

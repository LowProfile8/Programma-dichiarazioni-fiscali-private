"""
core/output_generator.py

Genera il PDF riepilogativo finale - un foglio con tutti i valori raccolti,
organizzato per modulo, pensato per essere ricopiato in eTax. NON è una
compilazione di eTax, è sempre e solo un foglio di supporto (principio
stabilito fin dall'inizio del progetto).

Uso fpdf2 (puro Python, nessuna dipendenza di sistema oltre pip) per tenere
il deploy su Streamlit Cloud semplice.
"""

from datetime import date
from io import BytesIO

from fpdf import FPDF

from core.models import DichiarazioneFiscale

BLU_ISTITUZIONALE = (22, 48, 92)
GRIGIO_TESTO = (30, 30, 30)
GRIGIO_CHIARO = (110, 110, 110)


class _PDFRiepilogo(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*BLU_ISTITUZIONALE)
        self.cell(0, 10, "Riepilogo dichiarazione fiscale privata", ln=True)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*GRIGIO_CHIARO)
        self.cell(0, 6, f"Generato il {date.today().strftime('%d.%m.%Y')} - documento di supporto, non sostituisce eTax", ln=True)
        self.ln(2)
        self.set_draw_color(169, 138, 75)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GRIGIO_CHIARO)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")

    def titolo_sezione(self, testo: str):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*BLU_ISTITUZIONALE)
        self.ln(3)
        self.cell(0, 8, testo, ln=True)
        self.set_text_color(*GRIGIO_TESTO)

    def riga(self, etichetta: str, valore: str):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 10)
        self.cell(70, 6, etichetta, new_x="RIGHT", new_y="TOP")
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, valore or "-", new_x="LMARGIN", new_y="NEXT")


def _v(campo) -> str:
    """Estrae il valore stampabile da un CampoValore, con nota se proviene
    dall'anno precedente (va segnalato anche nel PDF, non solo a schermo)."""
    if campo is None or not campo.valore:
        return "-"
    if getattr(campo, "da_rivedere", False):
        return f"{campo.valore}  ([ATTENZIONE] valore anno precedente, da rivalutare)"
    return campo.valore


def genera_pdf_riepilogo(dichiarazione: DichiarazioneFiscale) -> bytes:
    pdf = _PDFRiepilogo(orientation="P", unit="mm", format="A4")
    pdf.add_page()

    c = dichiarazione.contribuente
    pdf.titolo_sezione("1. Dati anagrafici")
    pdf.riga("Contribuente", f"{c.nome} {c.cognome}".strip() or "-")
    pdf.riga("Stato civile", c.stato_civile.value if c.stato_civile else "-")
    pdf.riga("Domicilio", c.domicilio or "-")
    pdf.riga("Professione", c.professione or "-")
    if c.coniuge:
        pdf.riga("Coniuge", f"{c.coniuge.nome} {c.coniuge.cognome}".strip() or "-")

    if dichiarazione.figli:
        pdf.titolo_sezione("Figli")
        for f in dichiarazione.figli:
            riga = f"{f.nome} (nato/a {f.anno_nascita})"
            if f.in_cura_da_terzi:
                riga += f" - in cura da terzi presso {f.nome_istituto_cura or '-'}, spese: {_v(f.spese_cura_annuali)}"
            if f.agli_studi:
                riga += " - agli studi"
            pdf.riga("", riga)

    if dichiarazione.certificati_salario:
        pdf.titolo_sezione("2. Reddito da attività dipendente")
        for cert in dichiarazione.certificati_salario:
            pdf.riga("Datore di lavoro", _v(cert.datore_lavoro))
            pdf.riga("Cifra 10 - Contributi LPP", _v(cert.cifra_10_contributi_lpp))
            pdf.riga("Cifra 11 - Salario netto", _v(cert.cifra_11_salario_netto))

    if dichiarazione.conti_correnti:
        pdf.titolo_sezione("Modulo 2a - Conti correnti/risparmio")
        for conto in dichiarazione.conti_correnti:
            titolarita = conto.titolarita
            if conto.titolarita == "cointestato":
                titolarita += f" ({conto.quota_proprieta}% di tua proprietà)"
            pdf.riga("Istituto", f"{_v(conto.istituto)} - {titolarita}")
            pdf.riga("Saldo al 31.12", _v(conto.saldo_valore_31_12))
            pdf.riga("Interessi", _v(conto.interessi_redditi))

    if dichiarazione.titoli_investimenti:
        pdf.titolo_sezione("Modulo 2b - Titoli e investimenti")
        for titolo in dichiarazione.titoli_investimenti:
            pdf.riga("Istituto/tipo", f"{_v(titolo.istituto)} - {titolo.tipo}")
            pdf.riga("Valore al 31.12", _v(titolo.saldo_valore_31_12))
            pdf.riga("Dividendi/cedole", _v(titolo.interessi_redditi))

    if dichiarazione.immobili:
        pdf.titolo_sezione("Modulo 7 - Immobili")
        for n, imm in enumerate(dichiarazione.immobili, start=1):
            pdf.riga(f"Immobile {n}", f"{_v(imm.comune)}, {_v(imm.indirizzo)}")
            pdf.riga("Destinazione", imm.destinazione)
            pdf.riga("Valore di stima", _v(imm.valore_stima_totale))
            if not imm.piena_proprieta:
                pdf.riga("Tua quota", f"reddito {imm.quota_reddito_contribuente}%, sostanza {imm.quota_sostanza_contribuente}%")

    if dichiarazione.partecipazioni:
        pdf.titolo_sezione("Modulo 8 - Partecipazioni qualificate")
        for p in dichiarazione.partecipazioni:
            pdf.riga(_v(p.denominazione), f"quota {p.quota_percentuale}% - valore fiscale {_v(p.valore_fiscale)}")

    return bytes(pdf.output())

"""
core/output_generator.py — v2

Genera un PDF organizzato ESATTAMENTE come i moduli ufficiali della
dichiarazione (stessa suddivisione, stessi numeri di cifra), in tabelle
leggibili — non una copia grafica del modulo eTax (fragile da mantenere,
e non è comunque l'obiettivo: l'obiettivo è che i numeri si trovino
esattamente dove il modulo ufficiale li chiede, pronti da ricopiare).

Ogni sezione ha nell'intestazione il riferimento al modulo/cifra ufficiale
così chi ricopia sa esattamente dove guardare.
"""

from datetime import date

from fpdf import FPDF

from core.models import DichiarazioneFiscale

BLU = (36, 81, 224)
TESTO = (20, 22, 26)
GRIGIO = (91, 100, 114)
GRIGIO_CHIARO = (246, 247, 249)
BIANCO = (255, 255, 255)


def _v(campo) -> str:
    if campo is None or not campo.valore:
        return "-"
    if getattr(campo, "da_rivedere", False):
        return f"{campo.valore}  [anno precedente - da rivalutare]"
    return campo.valore


def _fmt(valore) -> str:
    if valore is None:
        return "-"
    return f"{valore:,.2f}".replace(",", "'")


class _PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(*TESTO)
        self.cell(0, 9, "Riepilogo dichiarazione d'imposta", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GRIGIO)
        self.cell(0, 5, f"Generato il {date.today().strftime('%d.%m.%Y')} - documento di supporto, non sostituisce eTax",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GRIGIO)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")

    def intestazione_modulo(self, titolo: str, riferimento: str = ""):
        self.set_x(self.l_margin)
        self.set_fill_color(*BLU)
        self.set_text_color(*BIANCO)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, f"  {titolo}", fill=True, new_x="LMARGIN", new_y="NEXT")
        if riferimento:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*GRIGIO)
            self.cell(0, 5, riferimento, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*TESTO)
        self.ln(2)

    def tabella(self, intestazioni: list, righe: list, larghezze: list):
        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(*GRIGIO_CHIARO)
        self.set_x(self.l_margin)
        for h, w in zip(intestazioni, larghezze):
            self.cell(w, 6.5, h, fill=True, border=0)
        self.ln(6.5)

        self.set_font("Helvetica", "", 8.5)
        for riga in righe:
            self.set_x(self.l_margin)
            y_iniziale = self.get_y()
            altezza_max = 5.5
            for valore, w in zip(riga, larghezze):
                self.multi_cell(w, altezza_max, str(valore), border=0, align="L", new_x="RIGHT", new_y="TOP")
            self.ln(altezza_max)
            self.set_draw_color(*GRIGIO_CHIARO)
            self.line(self.l_margin, self.get_y(), self.l_margin + sum(larghezze), self.get_y())
        self.ln(4)

    def campo_singolo(self, etichetta: str, valore: str, cifra: str = ""):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 9)
        testo_etichetta = f"{etichetta}" + (f"  (cifra {cifra})" if cifra else "")
        self.cell(75, 6, testo_etichetta, new_x="RIGHT", new_y="TOP")
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 6, valore or "-", new_x="LMARGIN", new_y="NEXT")


def genera_pdf_riepilogo(dichiarazione: DichiarazioneFiscale) -> bytes:
    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    c = dichiarazione.contribuente

    # ── MODULO 1 — pagina 1: dati anagrafici ────────────────────────────
    pdf.intestazione_modulo("Modulo 1 - Dati personali e situazione familiare", "Pagina 1")
    pdf.campo_singolo("Contribuente", f"{c.nome} {c.cognome}".strip())
    pdf.campo_singolo("Stato civile", c.stato_civile.value if c.stato_civile else "-")
    pdf.campo_singolo("Domicilio", c.domicilio)
    pdf.campo_singolo("Professione", c.professione)
    pdf.campo_singolo("Genere di attivita", ", ".join(g.value for g in c.genere_attivita) or "-")
    if c.luogo_lavoro:
        pdf.campo_singolo("Luogo di lavoro", c.luogo_lavoro)
    if c.coniuge:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.cell(0, 6, "Coniuge / Partner registrato", new_x="LMARGIN", new_y="NEXT")
        pdf.campo_singolo("Nome", f"{c.coniuge.nome} {c.coniuge.cognome}".strip())
        pdf.campo_singolo("Domicilio", c.coniuge.domicilio)
        pdf.campo_singolo("Professione", c.coniuge.professione)

    if dichiarazione.figli:
        pdf.ln(3)
        righe_figli = []
        for f in dichiarazione.figli:
            cura = f"Si - {f.nome_istituto_cura} ({_v(f.spese_cura_annuali)})" if f.in_cura_da_terzi else "No"
            studi = "Si" if f.agli_studi else "No"
            righe_figli.append([f.nome, str(f.anno_nascita or "-"), cura, studi])
        pdf.tabella(
            ["Nome", "Anno nascita", "In cura da terzi", "Agli studi"],
            righe_figli, [45, 30, 80, 25],
        )

    # ── MODULO 1 — pagina 2: reddito da attivita dipendente ─────────────
    if dichiarazione.certificati_salario:
        pdf.add_page()
        pdf.intestazione_modulo("Modulo 1 - Redditi in Svizzera e all'estero", "Pagina 2, punto 1")
        for n, cert in enumerate(dichiarazione.certificati_salario, start=1):
            pdf.campo_singolo(f"Datore di lavoro #{n}", _v(cert.datore_lavoro))
            pdf.campo_singolo("Contributi LPP", _v(cert.cifra_10_contributi_lpp), cifra="10")
            pdf.campo_singolo("Salario netto", _v(cert.cifra_11_salario_netto), cifra="1.1 / 100")
            pdf.ln(2)

    # ── MODULO 2 — elenco titoli ─────────────────────────────────────────
    if dichiarazione.conti_correnti or dichiarazione.titoli_investimenti:
        pdf.add_page()
        pdf.intestazione_modulo("Modulo 2 - Elenco dei titoli e di altri collocamenti di capitali")

        if dichiarazione.conti_correnti:
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.cell(0, 6, "Conti correnti e di risparmio", new_x="LMARGIN", new_y="NEXT")
            righe = []
            for conto in dichiarazione.conti_correnti:
                titolarita = conto.titolarita
                if conto.titolarita == "cointestato":
                    titolarita += f" ({conto.quota_proprieta:g}%)"
                righe.append([_v(conto.istituto), conto.tipo, titolarita, _v(conto.saldo_valore_31_12), _v(conto.interessi_redditi)])
            pdf.tabella(
                ["Istituto", "Tipo", "Titolarita", "Sostanza 31.12", "Reddito"],
                righe, [40, 30, 35, 35, 40],
            )

        if dichiarazione.titoli_investimenti:
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.cell(0, 6, "Titoli e investimenti", new_x="LMARGIN", new_y="NEXT")
            righe = []
            for titolo in dichiarazione.titoli_investimenti:
                titolarita = titolo.titolarita
                if titolo.titolarita == "cointestato":
                    titolarita += f" ({titolo.quota_proprieta:g}%)"
                righe.append([_v(titolo.istituto), titolo.tipo, titolarita, _v(titolo.saldo_valore_31_12), _v(titolo.interessi_redditi)])
            pdf.tabella(
                ["Istituto", "Tipo", "Titolarita", "Sostanza 31.12", "Reddito"],
                righe, [40, 30, 35, 35, 40],
            )
        pdf.campo_singolo("Riportare a Modulo 1", "vedi tabelle sopra", cifra="150 / 300")

    # ── MODULO 7 — immobili ──────────────────────────────────────────────
    if dichiarazione.immobili:
        for n, imm in enumerate(dichiarazione.immobili, start=1):
            pdf.add_page()
            pdf.intestazione_modulo(f"Modulo 7 - Immobile n. {n}", "Determinazione sostanza e reddito immobiliare")
            pdf.campo_singolo("Comune", _v(imm.comune))
            pdf.campo_singolo("Indirizzo", _v(imm.indirizzo))
            pdf.campo_singolo("Cantone/Nazione", _v(imm.nazione_cantone))
            pdf.campo_singolo("Anno di costruzione", str(imm.anno_costruzione or "-"))
            pdf.campo_singolo("Destinazione", imm.destinazione)
            pdf.campo_singolo("Tipo di immobile", imm.tipo_immobile)
            pdf.ln(2)
            pdf.campo_singolo("Valore di stima totale", _v(imm.valore_stima_totale), cifra="30")
            if imm.destinazione == "Uso proprio":
                pdf.campo_singolo("Valore di reddito (da scheda stima)", _v(imm.valore_di_reddito))
                pdf.campo_singolo("Abitazione", "Primaria" if imm.abitazione_primaria else "Secondaria/vacanza",
                                   cifra="5.1" if imm.abitazione_primaria else "5.2")
            else:
                pdf.campo_singolo("Affitti incassati", _v(imm.affitti_incassati), cifra="5.3")
            if imm.usa_spese_effettive and imm.spese_effettive:
                totale = sum(
                    float(s.valore.replace("'", "").replace(",", "."))
                    for s in imm.spese_effettive if s.valore
                )
                pdf.campo_singolo("Spese di manutenzione effettive", _fmt(totale), cifra="5.5")
            else:
                pdf.campo_singolo("Deduzione forfettaria", "10% se costruito dal 2015, 20% se prima", cifra="5.5")
            if not imm.piena_proprieta:
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 9.5)
                pdf.cell(0, 6, "Comproprieta / comunione ereditaria", new_x="LMARGIN", new_y="NEXT")
                pdf.campo_singolo("Tua quota", f"reddito {imm.quota_reddito_contribuente:g}% - sostanza {imm.quota_sostanza_contribuente:g}%")
                righe = [[c.cognome_nome, str(c.anno_nascita or "-"), f"{c.quota_reddito:g}%", f"{c.quota_sostanza:g}%"] for c in imm.comproprietari]
                if righe:
                    pdf.tabella(["Comproprietario/erede", "Anno nascita", "% reddito", "% sostanza"], righe, [70, 35, 30, 30])

    # ── MODULO 8 — partecipazioni qualificate ────────────────────────────
    if dichiarazione.partecipazioni:
        pdf.add_page()
        pdf.intestazione_modulo("Modulo 8 - Partecipazioni qualificate nella sostanza privata")
        righe = []
        for p in dichiarazione.partecipazioni:
            div = _v(p.dividendi_lordo_totale) if p.ha_ricevuto_dividendi else "-"
            righe.append([_v(p.denominazione), f"{p.quota_percentuale:g}%" if p.quota_percentuale else "-", _v(p.capitale_sociale), _v(p.valore_fiscale), div])
        pdf.tabella(
            ["Societa", "Quota %", "Capitale sociale", "Valore fiscale", "Dividendi lordi"],
            righe, [40, 20, 38, 38, 40],
        )

    return bytes(pdf.output())

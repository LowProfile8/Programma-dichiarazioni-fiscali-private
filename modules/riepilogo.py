"""modules/riepilogo.py — riepilogo, controlli di completezza e scarico PDF."""

import streamlit as st

from core import state
from core.models import DichiarazioneFiscale
from core.output_generator import genera_pdf_riepilogo


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Riepilogo")

    c = dichiarazione.contribuente
    st.write(f"**Contribuente:** {c.nome} {c.cognome}")
    if c.stato_civile:
        st.write(f"**Stato civile:** {c.stato_civile.value}")
    if c.coniuge:
        st.write(f"**Coniuge:** {c.coniuge.nome} {c.coniuge.cognome}")
    st.write(f"**Figli:** {len(dichiarazione.figli)}")
    st.write(f"**Certificati di salario:** {len(dichiarazione.certificati_salario)}")
    st.write(f"**Conti correnti:** {len(dichiarazione.conti_correnti)}")
    st.write(f"**Titoli/investimenti:** {len(dichiarazione.titoli_investimenti)}")
    st.write(f"**Immobili:** {len(dichiarazione.immobili)}")
    st.write(f"**Partecipazioni qualificate:** {len(dichiarazione.partecipazioni)}")

    # ── Controlli di completezza: valori FONDAMENTALI mancanti ──────────
    avvisi_fondamentali = []
    ha_reddito = any(
        cert.cifra_11_salario_netto.valore for cert in dichiarazione.certificati_salario
    )
    if not ha_reddito:
        avvisi_fondamentali.append(
            "Nessun reddito da attività dipendente inserito (cifra 11 del certificato di salario) — "
            "manca un dato fondamentale della dichiarazione."
        )
    if not c.cognome or not c.nome:
        avvisi_fondamentali.append("Nome o cognome del contribuente non inseriti.")
    if c.richiede_dati_coniuge() and c.coniuge and not (c.coniuge.nome and c.coniuge.cognome):
        avvisi_fondamentali.append("Hai indicato coniugato/a, ma i dati del coniuge non sono completi.")

    if avvisi_fondamentali:
        st.error(
            "⚠️ **Valori fondamentali mancanti** — completali prima di considerare la dichiarazione pronta:\n\n"
            + "\n".join(f"- {a}" for a in avvisi_fondamentali)
        )

    # ── Valori presi dall'anno precedente, ancora da rivalutare ─────────
    campi_da_rivedere = []

    def _controlla(oggetto, nomi_campi, etichetta):
        for nome_campo in nomi_campi:
            campo = getattr(oggetto, nome_campo, None)
            if campo is not None and getattr(campo, "da_rivedere", False):
                campi_da_rivedere.append(f"{etichetta} — {nome_campo}")

    for cert in dichiarazione.certificati_salario:
        _controlla(cert, ["datore_lavoro", "cifra_10_contributi_lpp", "cifra_11_salario_netto"], "Certificato di salario")
    for conto in dichiarazione.conti_correnti:
        _controlla(conto, ["istituto", "iban_numero_conto", "saldo_valore_31_12", "interessi_redditi"], "Conto corrente")
    for titolo in dichiarazione.titoli_investimenti:
        _controlla(titolo, ["istituto", "iban_numero_conto", "saldo_valore_31_12", "interessi_redditi", "quantita_nominale"], "Titolo")
    for imm in dichiarazione.immobili:
        _controlla(imm, ["comune", "indirizzo", "valore_stima_totale", "valore_di_reddito", "affitti_incassati"], "Immobile")
    for p in dichiarazione.partecipazioni:
        _controlla(p, ["denominazione", "capitale_sociale", "dividendi_lordo_totale"], "Partecipazione")

    if campi_da_rivedere:
        st.warning(
            "⚠️ Questi campi usano ancora il valore dell'anno scorso e vanno rivalutati prima di generare il PDF definitivo:\n\n"
            + "\n".join(f"- {c}" for c in campi_da_rivedere)
        )

    partecipazioni_fuori_scope = [p for p in dichiarazione.partecipazioni if not p.detenuta_privatamente]
    if partecipazioni_fuori_scope:
        st.error(
            f"⚠️ {len(partecipazioni_fuori_scope)} partecipazione/i detenuta/e come attivo di ditta individuale "
            "(Modulo 8.1) — fuori scope v1, da gestire manualmente."
        )

    st.divider()
    st.subheader("Genera il foglio riepilogativo")
    st.caption("Formato PDF — un foglio con tutti i valori raccolti, organizzato per modulo, da usare come base per la compilazione in eTax.")

    if st.button("📄 Genera PDF", type="primary"):
        pdf_bytes = genera_pdf_riepilogo(dichiarazione)
        st.session_state["pdf_riepilogo_bytes"] = pdf_bytes
        st.success("PDF generato.")

    if "pdf_riepilogo_bytes" in st.session_state:
        st.download_button(
            "⬇️ Scarica il PDF",
            data=st.session_state["pdf_riepilogo_bytes"],
            file_name=f"riepilogo_dichiarazione_{dichiarazione.anno_fiscale}.pdf",
            mime="application/pdf",
        )

    if st.button("← Indietro"):
        state.go_back()
        st.rerun()

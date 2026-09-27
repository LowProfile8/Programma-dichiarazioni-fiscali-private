"""modules/riepilogo.py — riepilogo dati raccolti su tutti i moduli, con
evidenza dei valori ancora da rivalutare (origine 'anno_precedente')."""

import streamlit as st

from core import state
from core.models import DichiarazioneFiscale


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

    campi_da_rivedere = []

    def _controlla(oggetto, nomi_campi, etichetta):
        for nome_campo in nomi_campi:
            campo = getattr(oggetto, nome_campo, None)
            if campo is not None and getattr(campo, "da_rivedere", False):
                campi_da_rivedere.append(f"{etichetta} — {nome_campo}")

    for cert in dichiarazione.certificati_salario:
        _controlla(cert, ["datore_lavoro", "cifra_1_salario_lordo", "cifra_10_contributi_lpp", "cifra_11_salario_netto"], "Certificato di salario")
    for conto in dichiarazione.conti_correnti:
        _controlla(conto, ["istituto", "iban_numero_conto", "saldo_valore_31_12", "interessi_redditi"], "Conto corrente")
    for titolo in dichiarazione.titoli_investimenti:
        _controlla(titolo, ["istituto", "iban_numero_conto", "saldo_valore_31_12", "interessi_redditi", "quantita_nominale"], "Titolo")
    for imm in dichiarazione.immobili:
        _controlla(imm, ["comune", "indirizzo", "valore_stima_totale", "valore_di_reddito", "affitti_incassati"], "Immobile")
    for p in dichiarazione.partecipazioni:
        _controlla(p, ["denominazione", "capitale_sociale", "valore_fiscale", "dividendi_lordo_totale"], "Partecipazione")

    if campi_da_rivedere:
        st.warning(
            "⚠️ Questi campi usano ancora il valore dell'anno scorso e vanno rivalutati prima di generare i fogli finali:\n\n"
            + "\n".join(f"- {c}" for c in campi_da_rivedere)
        )
    else:
        st.success("Nessun valore in sospeso dall'anno precedente.")

    partecipazioni_fuori_scope = [p for p in dichiarazione.partecipazioni if not p.detenuta_privatamente]
    if partecipazioni_fuori_scope:
        st.error(
            f"⚠️ {len(partecipazioni_fuori_scope)} partecipazione/i detenuta/e come attivo di ditta individuale "
            "(Modulo 8.1) — fuori scope v1, da gestire manualmente."
        )

    st.divider()
    st.caption("Generazione dei fogli finali (Word/Excel) — prossimo passo, ora che i moduli principali sono collegati.")

    if st.button("← Indietro"):
        state.go_back()
        st.rerun()

"""modules/riepilogo.py — riepilogo dati raccolti, con evidenza dei valori
ancora da rivalutare (origine 'anno_precedente')."""

import streamlit as st

from core import state
from core.models import DichiarazioneFiscale


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Riepilogo")

    c = dichiarazione.contribuente
    st.write(f"**Contribuente:** {c.nome} {c.cognome}")
    st.write(f"**Figli:** {len(dichiarazione.figli)}")
    st.write(f"**Certificati di salario:** {len(dichiarazione.certificati_salario)}")
    st.write(f"**Conti/titoli:** {len(dichiarazione.conti_titoli)}")

    campi_da_rivedere = []
    for cert in dichiarazione.certificati_salario:
        for nome_campo in ("datore_lavoro", "cifra_1_salario_lordo", "cifra_10_contributi_lpp", "cifra_11_salario_netto"):
            campo = getattr(cert, nome_campo)
            if campo.da_rivedere:
                campi_da_rivedere.append(f"Certificato di salario — {nome_campo}")
    for conto in dichiarazione.conti_titoli:
        for nome_campo in ("istituto", "iban_numero_conto", "saldo_valore_31_12", "interessi_redditi"):
            campo = getattr(conto, nome_campo)
            if campo.da_rivedere:
                campi_da_rivedere.append(f"Conto/titolo — {nome_campo}")

    if campi_da_rivedere:
        st.warning(
            "⚠️ Questi campi usano ancora il valore dell'anno scorso e vanno rivalutati prima di generare i fogli finali:\n\n"
            + "\n".join(f"- {c}" for c in campi_da_rivedere)
        )
    else:
        st.success("Nessun valore in sospeso dall'anno precedente.")

    st.divider()
    st.caption("Generazione dei fogli finali (Word/Excel) — da implementare quando avremo validato anche gli altri moduli.")

    if st.button("← Indietro"):
        state.go_back()
        st.rerun()

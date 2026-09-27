"""
modules/benvenuto.py — primo passo del wizard, prima di qualunque dato.

Spiega cosa serve prima di iniziare, ma non blocca: il contribuente può
comunque procedere senza avere tutto a portata di mano (i documenti restano
facoltativi passo per passo), è solo un promemoria per arrivare preparati.
"""

import streamlit as st

from core import state
from core.models import DichiarazioneFiscale


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Benvenuto/a")
    st.write(
        "Questo assistente ti guida passo per passo nella raccolta dei dati per la tua "
        "dichiarazione fiscale privata. Alla fine otterrai un foglio riepilogativo in PDF "
        "da usare come base per la compilazione in eTax."
    )

    st.info(
        "**Non è un problema se non hai tutti i documenti sottomano ora**: puoi comunque "
        "iniziare e tornare più tardi a completare i campi mancanti. Se però manca un valore "
        "fondamentale (es. il reddito), te lo segnaleremo chiaramente al riepilogo finale."
    )

    st.subheader("Documenti utili da avere a portata di mano")
    st.markdown(
        """
- **Certificato/i di salario** dell'anno fiscale (tuo ed eventualmente del coniuge)
- **Attestati fiscali al 31.12** dei conti correnti/risparmio e dei depositi titoli
- **Dichiarazione fiscale dell'anno precedente** (facoltativa, ma utile per recuperare valori se sei in difficoltà)
- **Attestato dei versamenti al 3° pilastro A**, se ne hai uno
- **Scheda di calcolo della stima ufficiale** di eventuali immobili di proprietà
- **Attestati di rendite** (AVS, 2° pilastro, rendite vitalizie), se applicabile
- **Estratto del registro di commercio** se possiedi quote di una Sagl/SA
- **Fatture di cura da terzi** per figli sotto i 14 anni (asilo, tata, doposcuola), se applicabile
        """
    )

    st.divider()
    _, col_start = st.columns([3, 1])
    with col_start:
        if st.button("Inizia →", type="primary"):
            state.go_next()
            st.rerun()

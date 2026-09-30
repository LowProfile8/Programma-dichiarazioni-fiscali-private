"""
modules/benvenuto.py — primo passo del wizard.

Struttura decisa insieme: titolo grande, frase introduttiva in stile
"hero", poi la lista documenti, POI il box informativo blu (spostato sotto
la lista, non sopra), infine il pulsante "Inizia" — l'unico elemento
colorato di blu in tutta la pagina insieme agli avvisi.
"""

import streamlit as st

from core import state
from core.models import DichiarazioneFiscale
from core.stile import testo_hero


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.title("Benvenuto/a")
    testo_hero(
        "Questo assistente ti guiderà passo passo nella raccolta di dati per la tua "
        "dichiarazione fiscale privata. Alla fine otterrai i fogli ufficiali della "
        "dichiarazione già compilati, pronti per essere spediti in formato cartaceo "
        "oppure per la trascrizione sul programma ufficiale eTax."
    )

    st.subheader("Documenti utili da avere a portata di mano")
    st.markdown(
        """
- **Certificato/i di salario** dell'anno fiscale (tuo ed eventualmente del coniuge)
- **Attestati fiscali al 31.12** dei conti correnti/risparmio e dei depositi titoli
- **Attestato dei versamenti al 3° pilastro A**, se ne hai uno
- **Scheda di calcolo della stima ufficiale** di eventuali immobili di proprietà
- **Attestati di rendite** (AVS, 2° pilastro, rendite vitalizie), se applicabile
- **Dettagli dei veicoli** di proprietà o in leasing (marca e modello, anno di acquisto, valore attuale), barca compresa
- **Estratto del registro di commercio** se possiedi quote di una Sagl/SA
- **Fatture di cura da terzi** per figli sotto i 14 anni (asilo, tata, doposcuola), se applicabile
        """
    )

    st.info(
        "**Non è un problema se non hai tutti i documenti sottomano ora**: puoi comunque "
        "iniziare e tornare più tardi a completare i campi mancanti. Se manca un valore "
        "fondamentale (es. il reddito), te lo segnaleremo chiaramente al riepilogo finale."
    )

    st.write("")
    _, col_start = st.columns([3, 1])
    with col_start:
        if st.button("Inizia →", type="primary"):
            state.go_next()
            st.rerun()

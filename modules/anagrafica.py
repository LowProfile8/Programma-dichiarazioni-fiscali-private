"""
modules/anagrafica.py — pagina 1 del Modulo 1.

Corretto oggi: mancava completamente stato civile e coniuge — bug reale,
non solo un modulo "da aggiungere dopo". Ora c'è: se lo stato civile è
Coniugato/a o Unione domestica registrata, si apre lo stesso blocco di
campi anche per il coniuge (stessa logica già descritta nel documento
di progetto).
"""

import streamlit as st

from core import state
from core.models import Contribuente, DatiPersonaFisica, DichiarazioneFiscale, Figlio, GenereAttivita, StatoCivile
from core.ui_helpers import campo_con_fallback


def _blocco_persona(persona, key_prefix: str, titolo: str) -> None:
    st.markdown(f"**{titolo}**")
    col1, col2 = st.columns(2)
    with col1:
        persona.cognome = st.text_input("Cognome", value=persona.cognome, key=f"{key_prefix}_cognome")
        persona.data_nascita = st.date_input("Data di nascita", value=persona.data_nascita, key=f"{key_prefix}_nascita")
        persona.domicilio = st.text_input("Domicilio (comune)", value=persona.domicilio, key=f"{key_prefix}_domicilio")
    with col2:
        persona.nome = st.text_input("Nome", value=persona.nome, key=f"{key_prefix}_nome")
        persona.professione = st.text_input("Professione", value=persona.professione, key=f"{key_prefix}_professione")

    selezione = st.multiselect(
        "Genere di attività", options=list(GenereAttivita), format_func=lambda g: g.value,
        default=persona.genere_attivita, key=f"{key_prefix}_genere_ms",
    )
    persona.genere_attivita = selezione

    if GenereAttivita.BENEFICIARIO_PRESTAZIONI in selezione:
        st.caption(
            "ℹ️ Le prestazioni complementari AVS/AI non sono imponibili: nessun reddito da dichiarare per questa voce "
            "(fonte: Istruzioni ufficiali, punto 3.2)."
        )

    if GenereAttivita.DIPENDENTE in selezione:
        persona.luogo_lavoro = st.text_input(
            "Luogo di lavoro (ragione sociale, comune)", value=persona.luogo_lavoro, key=f"{key_prefix}_luogo_lavoro",
            help='Es. "La Fermata SA, Lugano" — solo testo, l\'indirizzo completo si raccoglie nel modulo Certificato di salario'
        )
        persona.attivita_accessoria = st.text_input(
            "Attività accessoria (se presente)", value=persona.attivita_accessoria, key=f"{key_prefix}_att_access"
        )


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("1. Dati anagrafici")

    c: Contribuente = dichiarazione.contribuente

    _blocco_persona(c, "contrib", "Contribuente")

    col1, col2 = st.columns(2)
    with col1:
        c.telefono = st.text_input("Telefono", value=c.telefono)
    with col2:
        c.email = st.text_input("Email", value=c.email)

    stato_civile_opzioni = list(StatoCivile)
    indice_corrente = stato_civile_opzioni.index(c.stato_civile) if c.stato_civile else 0
    c.stato_civile = st.selectbox(
        "Stato civile", options=stato_civile_opzioni, format_func=lambda s: s.value, index=indice_corrente,
    )

    if c.richiede_dati_coniuge():
        if c.coniuge is None:
            c.coniuge = DatiPersonaFisica()
        st.divider()
        _blocco_persona(c.coniuge, "coniuge", "Coniuge / Partner registrato")
    else:
        c.coniuge = None

    st.divider()
    st.subheader("Figli minorenni, a tirocinio o agli studi")
    if st.button("+ Aggiungi figlio"):
        dichiarazione.figli.append(Figlio())
        st.rerun()

    for i, figlio in enumerate(dichiarazione.figli):
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                figlio.nome = st.text_input("Nome", value=figlio.nome, key=f"figlio_nome_{i}")
            with col2:
                figlio.anno_nascita = st.number_input(
                    "Anno di nascita", min_value=1990, max_value=dichiarazione.anno_fiscale,
                    value=figlio.anno_nascita or dichiarazione.anno_fiscale, key=f"figlio_anno_{i}"
                )
            with col3:
                if st.button("Rimuovi", key=f"figlio_rimuovi_{i}"):
                    dichiarazione.figli.pop(i)
                    st.rerun()

            eta = dichiarazione.anno_fiscale - figlio.anno_nascita if figlio.anno_nascita else None
            if eta is not None:
                st.caption(f"Età al 31.12.{dichiarazione.anno_fiscale}: {eta} anni")
                if eta < 14:
                    figlio.in_cura_da_terzi = st.checkbox(
                        "In cura da terzi durante l'orario di lavoro dei genitori (asilo, tata, doposcuola — non le rette scolastiche)",
                        value=bool(figlio.in_cura_da_terzi), key=f"figlio_cura_{i}",
                    )
                    if figlio.in_cura_da_terzi:
                        figlio.nome_istituto_cura = st.text_input(
                            "Nome dell'istituto o della persona che presta la cura",
                            value=figlio.nome_istituto_cura, key=f"figlio_istituto_{i}",
                        )
                        campo_con_fallback(
                            figlio.spese_cura_annuali, "Spese annuali sostenute", key=f"figlio_spese_cura_{i}",
                            descrizione_ricerca=f"Spese di cura da terzi per il figlio {figlio.nome}, Modulo 6 retro, cifra 20"
                        )
                        file_fattura = st.file_uploader(
                            "Fattura/e della struttura o della persona che presta la cura",
                            type=["pdf", "png", "jpg", "jpeg"], key=f"figlio_fattura_{i}",
                        )
                        if file_fattura is not None:
                            figlio.file_fatture_cura = file_fattura.name
                elif 18 <= eta <= 28:
                    figlio.agli_studi = st.checkbox(
                        "Agli studi / in formazione (deduzione ammessa fino al 28° anno di età)",
                        value=bool(figlio.agli_studi), key=f"figlio_studi_{i}",
                    )
                elif eta > 28:
                    st.info("Oltre il 28° anno di età non è più ammessa la deduzione per figlio a carico o agli studi.")

    st.divider()
    _, col_next = st.columns([4, 1])
    with col_next:
        if st.button("Avanti →", type="primary"):
            state.go_next()
            st.rerun()

"""
modules/anagrafica.py — pagina 1 del Modulo 1.

Corretto oggi: mancava completamente stato civile e coniuge — bug reale,
non solo un modulo "da aggiungere dopo". Ora c'è: se lo stato civile è
Coniugato/a o Unione domestica registrata, si apre lo stesso blocco di
campi anche per il coniuge (stessa logica già descritta nel documento
di progetto).
"""

from datetime import date

import streamlit as st

from core import state
from core.models import Contribuente, DatiPersonaFisica, DichiarazioneFiscale, Figlio, GenereAttivita, StatoCivile
from core.ui_helpers import campo_con_fallback


def _blocco_persona(persona, key_prefix: str, titolo: str) -> None:
    st.markdown(f"**{titolo}**")
    col1, col2 = st.columns(2)
    with col1:
        persona.cognome = st.text_input("Cognome", value=persona.cognome, key=f"{key_prefix}_cognome")
        persona.data_nascita = st.date_input(
            "Data di nascita", value=persona.data_nascita, key=f"{key_prefix}_nascita",
            min_value=date(1900, 1, 1), max_value=date.today(), format="DD/MM/YYYY",
        )
    with col2:
        persona.nome = st.text_input("Nome", value=persona.nome, key=f"{key_prefix}_nome")
        persona.professione = st.text_input("Professione", value=persona.professione, key=f"{key_prefix}_professione")

    persona.indirizzo = st.text_input(
        "Indirizzo di residenza (via e numero)", value=persona.indirizzo, key=f"{key_prefix}_indirizzo",
        help='Es. "Via Nassa 5"',
    )
    col_dom, col_npa = st.columns([3, 1])
    with col_dom:
        persona.domicilio = st.text_input(
            "Domicilio (comune)", value=persona.domicilio, key=f"{key_prefix}_domicilio"
        )
    with col_npa:
        persona.npa = st.text_input(
            "NPA", value=persona.npa, key=f"{key_prefix}_npa", max_chars=4,
            help="Il codice postale del comune di domicilio (4 cifre)",
        )
    if persona.npa and not (persona.npa.isdigit() and len(persona.npa) == 4):
        st.caption("⚠️ L'NPA svizzero è composto da 4 cifre.")

    selezione = st.multiselect(
        "Genere di attività", options=list(GenereAttivita), format_func=lambda g: g.value,
        default=persona.genere_attivita, key=f"{key_prefix}_genere_ms",
        placeholder="Scegli una o più opzioni",
    )
    persona.genere_attivita = selezione

    if GenereAttivita.BENEFICIARIO_PRESTAZIONI in selezione:
        st.caption(
            "ℹ️ Le prestazioni complementari AVS/AI non sono imponibili: nessun reddito da dichiarare per questa voce "
            "(fonte: Istruzioni ufficiali, punto 3.2)."
        )

    if GenereAttivita.DIPENDENTE in selezione:
        st.markdown("**Luogo di lavoro**")
        col_rs, col_com = st.columns(2)
        with col_rs:
            persona.datore_lavoro = st.text_input(
                "Ragione sociale del datore di lavoro", value=persona.datore_lavoro,
                key=f"{key_prefix}_datore_lavoro", help='Es. "La Fermata SA"',
            )
        with col_com:
            persona.comune_lavoro = st.text_input(
                "Comune del datore di lavoro", value=persona.comune_lavoro,
                key=f"{key_prefix}_comune_lavoro", help='Es. "Lugano"',
            )
        persona.luogo_lavoro = ", ".join(x for x in (persona.datore_lavoro.strip(), persona.comune_lavoro.strip()) if x)

        persona.attivita_accessoria = st.text_input(
            "Attività accessoria (se presente): ragione sociale e comune del datore di lavoro",
            value=persona.attivita_accessoria, key=f"{key_prefix}_att_access",
            help='Come per il luogo di lavoro. Es. "Alborella Sagl, Lugano"',
        )


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("1. Dati anagrafici")

    c: Contribuente = dichiarazione.contribuente

    st.markdown("**Numero di controllo (facoltativo)**")
    st.caption(
        "È il «Numero registro» che si trova in alto nella prima pagina della dichiarazione di quest'anno, "
        "dell'anno scorso o di una qualsiasi decisione di tassazione: è sempre lo stesso ogni anno. "
        "Se lo inserisci, lo scriviamo in tutti i moduli."
    )
    dichiarazione.numero_controllo = st.text_input(
        "Numero di controllo", value=dichiarazione.numero_controllo,
        max_chars=10, placeholder="es. 0001234567", label_visibility="collapsed",
    ).strip()
    if dichiarazione.numero_controllo and not dichiarazione.numero_controllo.isdigit():
        st.caption("⚠️ Il numero di controllo è composto solo da cifre (di solito 10).")
    st.divider()

    _blocco_persona(c, "contrib", "Contribuente")

    col1, col2 = st.columns(2)
    with col1:
        c.telefono = st.text_input("Telefono", value=c.telefono)
    with col2:
        c.email = st.text_input("Email", value=c.email)

    stato_civile_opzioni = list(StatoCivile)
    indice_corrente = stato_civile_opzioni.index(c.stato_civile) if c.stato_civile else None
    c.stato_civile = st.selectbox(
        "Stato civile", options=stato_civile_opzioni, format_func=lambda s: s.value,
        index=indice_corrente, placeholder="Scegli lo stato civile", key="contrib_stato_civile",
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
    st.subheader("Informazioni complementari")
    dichiarazione.abita_in_affitto = st.checkbox(
        "Abiti in un'abitazione in affitto?", value=bool(dichiarazione.abita_in_affitto),
    )
    if dichiarazione.abita_in_affitto:
        campo_con_fallback(
            dichiarazione.pigione_annua_netta, "Pigione annua (senza spese accessorie)",
            key="pigione_annua", descrizione_ricerca="Pigione annua di affitto, Modulo 1 pagina 1, cifra 444",
        )
        col1, col2 = st.columns(2)
        with col1:
            dichiarazione.proprietario_nome = st.text_input(
                "Nome del/della proprietario/a dello stabile", value=dichiarazione.proprietario_nome,
            )
        with col2:
            dichiarazione.proprietario_indirizzo = st.text_input(
                "Indirizzo del/della proprietario/a", value=dichiarazione.proprietario_indirizzo,
            )

    st.divider()
    _, col_next = st.columns([4, 1])
    with col_next:
        if st.button("Avanti →", type="primary"):
            state.go_next()
            st.rerun()

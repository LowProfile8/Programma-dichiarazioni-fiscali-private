"""app.py — entry point. streamlit run app.py"""

import streamlit as st

from core import salvataggio, state
from core.stile import applica_stile, intestazione
from modules import (
    anagrafica,
    anno_precedente,
    benvenuto,
    certificato_salario,
    conti_correnti,
    debiti_donazioni,
    immobili,
    oneri_assicurativi,
    partecipazioni,
    preventivo,
    riepilogo,
    spese_professionali,
    titoli_investimenti,
    veicoli,
)

ANNO_FISCALE_DEFAULT = 2025
MODALITA_DICHIARAZIONE = "Dichiarazione fiscale privata"
MODALITA_PREVENTIVO = "Preventivo"

STEP_MODULES = {
    "benvenuto": benvenuto,
    "anno_precedente": anno_precedente,
    "anagrafica": anagrafica,
    "certificato_salario": certificato_salario,
    "spese_professionali": spese_professionali,
    "conti_correnti": conti_correnti,
    "titoli_investimenti": titoli_investimenti,
    "immobili": immobili,
    "veicoli": veicoli,
    "partecipazioni": partecipazioni,
    "debiti_donazioni": debiti_donazioni,
    "oneri_assicurativi": oneri_assicurativi,
    "riepilogo": riepilogo,
}


def _accesso_consentito() -> bool:
    """Se nei secrets di Streamlit c'è APP_PASSWORD chiede un codice di accesso; altrimenti l'app è aperta.
    Consigliato: il programma tratta dati fiscali di clienti e i progetti salvati sono visibili a chi entra."""
    try:
        password = st.secrets["APP_PASSWORD"]
    except Exception:
        return True
    if st.session_state.get("_autenticato"):
        return True
    intestazione("Athena", "Accesso riservato")
    codice = st.text_input("Codice di accesso", type="password")
    if codice:
        if codice == str(password):
            st.session_state["_autenticato"] = True
            st.rerun()
        st.error("Codice non corretto.")
    return False


def _apri_progetto(dichiarazione, step: int, progetto_id=None) -> None:
    state.pulisci_widget()
    st.session_state["dichiarazione"] = dichiarazione
    st.session_state["step_index"] = min(max(step, 0), len(state.STEPS) - 1)
    if progetto_id:
        st.session_state["progetto_id"] = progetto_id
    else:
        st.session_state.pop("progetto_id", None)
    st.rerun()


def _salva_progetto() -> None:
    dichiarazione = state.get_dichiarazione()
    progetto_id = salvataggio.salva(
        dichiarazione, st.session_state["step_index"], st.session_state.get("progetto_id")
    )
    st.session_state["progetto_id"] = progetto_id
    st.toast(f"Progetto salvato: {salvataggio.titolo(dichiarazione)}")


def _menu_laterale() -> str:
    """Menu a scomparsa: scelta della modalità e progetti in corso. Restituisce la modalità scelta."""
    with st.sidebar:
        st.markdown("### Athena")
        modalita = st.radio(
            "Cosa vuoi fare?", [MODALITA_DICHIARAZIONE, MODALITA_PREVENTIVO], key="modalita",
        )
        if modalita != MODALITA_DICHIARAZIONE:
            return modalita

        st.divider()
        st.markdown("**Progetti in corso**")
        progetti = salvataggio.elenco()
        if not progetti:
            st.caption("Nessun progetto salvato. Usa «Salva il progetto» in fondo alla pagina.")
        for p in progetti:
            attivo = p["id"] == st.session_state.get("progetto_id")
            st.markdown(f"{'▸ ' if attivo else ''}**{p['titolo']}**")
            st.caption(f"salvato il {p['salvato'][8:10]}.{p['salvato'][5:7]}.{p['salvato'][:4]} alle {p['salvato'][11:16]}")
            col_apri, col_elimina = st.columns(2)
            with col_apri:
                if st.button("Apri", key=f"apri_{p['id']}"):
                    dichiarazione, step = salvataggio.carica(p["id"])
                    _apri_progetto(dichiarazione, step, p["id"])
            with col_elimina:
                if st.button("Elimina", key=f"rimuovi_{p['id']}"):
                    st.session_state["conferma_elimina"] = p["id"]
                    st.rerun()
            if st.session_state.get("conferma_elimina") == p["id"]:
                st.warning("Eliminare definitivamente questo progetto?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Sì, elimina", key=f"rimuovi_si_{p['id']}"):
                        salvataggio.elimina(p["id"])
                        if st.session_state.get("progetto_id") == p["id"]:
                            st.session_state.pop("progetto_id", None)
                        st.session_state.pop("conferma_elimina", None)
                        st.rerun()
                with c2:
                    if st.button("No", key=f"annulla_{p['id']}"):
                        st.session_state.pop("conferma_elimina", None)
                        st.rerun()

        st.divider()
        st.markdown("**File di salvataggio**")
        st.caption("Una copia sul tuo computer: resta anche se l'app viene riavviata.")
        dichiarazione = state.get_dichiarazione()
        st.download_button(
            "Scarica il progetto", data=salvataggio.a_bytes(dichiarazione, st.session_state["step_index"]),
            file_name=f"{salvataggio._slug(salvataggio.titolo(dichiarazione))}.json", mime="application/json",
            key="scarica_progetto",
        )
        file = st.file_uploader("Apri da file di salvataggio", type=["json"], key="carica_progetto_file")
        if file is not None:
            try:
                dich, step = salvataggio.da_bytes(file.getvalue())
            except ValueError as errore:
                st.error(str(errore))
            else:
                if st.button("Apri questo file", key="apri_file_salvataggio"):
                    _apri_progetto(dich, step)
    return modalita


def _barra_fissa() -> None:
    """In fondo alla pagina: Ricomincia (sinistra), Salva, impostazioni (solo ingranaggio, a destra)."""
    with st.container(key="barra_fissa"):
        col_reset, col_salva, _, col_avanzate = st.columns([4, 3, 3, 1])
        with col_reset:
            if st.button("↺ Ricomincia da capo", key="reset_tutto"):
                state.reset_state()
                st.rerun()
        with col_salva:
            if st.button("Salva il progetto", key="salva_progetto"):
                _salva_progetto()
        with col_avanzate:
            with st.popover("⚙️"):
                st.caption(
                    "Usata solo dal pulsante 'Leggi documento con AI' nel certificato di salario. "
                    "Il resto del programma funziona anche senza."
                )
                try:
                    default_key = st.secrets["ANTHROPIC_API_KEY"]
                except Exception:
                    default_key = ""
                api_key_input = st.text_input(
                    "Chiave API Anthropic", type="password",
                    value=st.session_state.get("anthropic_api_key", default_key),
                )
                st.session_state["anthropic_api_key"] = api_key_input


def main() -> None:
    st.set_page_config(
        page_title="Athena — dichiarazione fiscale e preventivi",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    applica_stile()

    if not _accesso_consentito():
        return

    state.init_state(anno_fiscale=ANNO_FISCALE_DEFAULT)
    modalita = _menu_laterale()

    if modalita == MODALITA_PREVENTIVO:
        intestazione("Athena", "Preventivo — servizi fiduciari")
        preventivo.render()
        return

    dichiarazione = state.get_dichiarazione()
    intestazione("Athena", "Dichiarazione fiscale privata — compilazione assistita")

    step_corrente = state.current_step()
    indice = state.STEPS.index(step_corrente)
    st.progress(indice / (len(state.STEPS) - 1))
    st.caption(f"Anno fiscale {dichiarazione.anno_fiscale} — passo {indice + 1} di {len(state.STEPS)}")

    STEP_MODULES[step_corrente].render(dichiarazione)
    _barra_fissa()


if __name__ == "__main__":
    main()

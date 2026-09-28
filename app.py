"""app.py — entry point. streamlit run app.py

Homepage con 4 sotto-programmi (vista in session_state):
  'home'          — pagina iniziale, sceglie il sotto-programma
  'dichiarazione' — wizard della dichiarazione fiscale privata
  'preventivo'    — genera un preventivo per servizi fiduciari
  'fatturazione'  — genera una fattura
  'archivio'      — elenco delle dichiarazioni salvate, per riprenderle
"""

import streamlit as st

from core import salvataggio, state
from core.stile import applica_stile, intestazione
from core.ui_helpers import piede_pagina
from modules import (
    anagrafica,
    anno_precedente,
    benvenuto,
    certificato_salario,
    conti_correnti,
    debiti_donazioni,
    fatturazione,
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
    Consigliato: il programma tratta dati fiscali/di fatturazione di clienti e l'archivio è visibile a chi entra."""
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


def _vai(vista: str) -> None:
    st.session_state["vista"] = vista
    st.rerun()


def _apri_progetto(dichiarazione, step: int, progetto_id=None) -> None:
    state.pulisci_widget()
    st.session_state["dichiarazione"] = dichiarazione
    st.session_state["step_index"] = min(max(step, 0), len(state.STEPS) - 1)
    st.session_state["progetto_id"] = progetto_id
    st.session_state["vista"] = "dichiarazione"
    st.rerun()


def _salva_progetto() -> None:
    dichiarazione = state.get_dichiarazione()
    progetto_id = salvataggio.salva(
        dichiarazione, st.session_state["step_index"], st.session_state.get("progetto_id")
    )
    st.session_state["progetto_id"] = progetto_id
    st.toast(f"Progetto salvato: {salvataggio.titolo(dichiarazione)}")


# ══════════════════════════════════════════════════════════════════════
# Homepage
# ══════════════════════════════════════════════════════════════════════
def _pulsante_home() -> None:
    if st.button("← Home", key="torna_home"):
        _vai("home")


def _pagina_home() -> None:
    intestazione("Athena", "Cosa vuoi fare?")
    st.write("")

    # Dichiarazione fiscale — più in vista delle altre tre: card più grande ed evidenziata
    with st.container(key="home_df_card", border=True):
        st.markdown("### 📄 Dichiarazione fiscale — Persone fisiche")
        st.write(
            "Compilazione guidata della dichiarazione fiscale privata, con generazione automatica "
            "dei moduli ufficiali del Cantone Ticino e calcolo del dispendio."
        )
        if st.button("Inizia →", key="home_df", type="primary"):
            state.init_state(anno_fiscale=ANNO_FISCALE_DEFAULT)
            _vai("dichiarazione")

    st.write("")
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(key="home_prev_card", border=True):
            st.markdown("**Preventivo**")
            st.caption("Genera il preventivo per i servizi fiduciari.")
            if st.button("Apri", key="home_prev"):
                _vai("preventivo")
    with col2:
        with st.container(key="home_fatt_card", border=True):
            st.markdown("**Fatturazione**")
            st.caption("Genera una fattura per un cliente.")
            if st.button("Apri", key="home_fatt"):
                _vai("fatturazione")
    with col3:
        with st.container(key="home_arch_card", border=True):
            st.markdown("**Archivio dichiarazioni**")
            st.caption("Riprendi una dichiarazione già salvata.")
            if st.button("Apri", key="home_arch"):
                _vai("archivio")


# ══════════════════════════════════════════════════════════════════════
# Archivio dichiarazioni
# ══════════════════════════════════════════════════════════════════════
def _pagina_archivio() -> None:
    intestazione("Athena", "Archivio dichiarazioni")
    _pulsante_home()
    st.write("")

    progetti = salvataggio.elenco()
    if not progetti:
        st.info(
            "Nessuna dichiarazione salvata. Apri «Dichiarazione fiscale», compila quello che ti serve e usa "
            "«Salva il progetto» in fondo alla pagina: comparirà qui."
        )
    for p in progetti:
        with st.container(border=True):
            col_info, col_apri, col_elimina = st.columns([5, 1, 1])
            with col_info:
                st.markdown(f"**{p['titolo']}**")
                st.caption(f"salvato il {p['salvato'][8:10]}.{p['salvato'][5:7]}.{p['salvato'][:4]} alle {p['salvato'][11:16]}")
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
    st.markdown("**Apri da file di salvataggio**")
    st.caption("Se avevi scaricato una dichiarazione come file, la riapri da qui (funziona anche se non è nell'elenco sopra).")
    file = st.file_uploader("File di salvataggio (.json)", type=["json"], key="carica_progetto_file")
    if file is not None:
        try:
            dich, step = salvataggio.da_bytes(file.getvalue())
        except ValueError as errore:
            st.error(str(errore))
        else:
            if st.button("Apri questo file", key="apri_file_salvataggio"):
                _apri_progetto(dich, step)


# ══════════════════════════════════════════════════════════════════════
# Dichiarazione fiscale: barra fissa in fondo
# ══════════════════════════════════════════════════════════════════════
def _barra_fissa() -> None:
    """In fondo alla pagina: Home, Ricomincia, Salva, impostazioni (solo ingranaggio)."""
    with st.container(key="barra_fissa"):
        col_home, col_reset, col_salva, _, col_avanzate = st.columns([1, 3, 3, 3, 1])
        with col_home:
            if st.button("🏠", key="barra_home", help="Torna alla home"):
                _vai("home")
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


def _pagina_dichiarazione() -> None:
    state.init_state(anno_fiscale=ANNO_FISCALE_DEFAULT)
    dichiarazione = state.get_dichiarazione()
    intestazione("Athena", "Dichiarazione fiscale privata — compilazione assistita")

    step_corrente = state.current_step()
    indice = state.STEPS.index(step_corrente)
    st.progress(indice / (len(state.STEPS) - 1))
    st.caption(f"Anno fiscale {dichiarazione.anno_fiscale} — passo {indice + 1} di {len(state.STEPS)}")

    STEP_MODULES[step_corrente].render(dichiarazione)
    piede_pagina()
    _barra_fissa()


def main() -> None:
    st.set_page_config(
        page_title="Athena — dichiarazioni, preventivi e fatture",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    applica_stile()

    if not _accesso_consentito():
        return

    vista = st.session_state.get("vista", "home")

    if vista == "home":
        _pagina_home()
    elif vista == "dichiarazione":
        _pagina_dichiarazione()
    elif vista == "preventivo":
        intestazione("Athena", "Preventivo — servizi fiduciari")
        _pulsante_home()
        preventivo.render()
        piede_pagina(con_avviso=False)
    elif vista == "fatturazione":
        intestazione("Athena", "Fatturazione")
        _pulsante_home()
        fatturazione.render()
        piede_pagina(con_avviso=False)
    elif vista == "archivio":
        _pagina_archivio()
    else:
        st.session_state["vista"] = "home"
        st.rerun()


if __name__ == "__main__":
    main()

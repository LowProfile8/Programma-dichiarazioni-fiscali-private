"""app.py — entry point. streamlit run app.py"""

import streamlit as st

from core import state
from modules import anagrafica, anno_precedente, certificato_salario, conti_titoli, riepilogo

ANNO_FISCALE_DEFAULT = 2025

STEP_MODULES = {
    "anno_precedente": anno_precedente,
    "anagrafica": anagrafica,
    "certificato_salario": certificato_salario,
    "conti_titoli": conti_titoli,
    "riepilogo": riepilogo,
}


def main() -> None:
    st.set_page_config(page_title="Dichiarazione fiscale privata — Ticino", layout="centered")

    state.init_state(anno_fiscale=ANNO_FISCALE_DEFAULT)
    dichiarazione = state.get_dichiarazione()

    st.title("Assistente dichiarazione fiscale privata")

    step_corrente = state.current_step()
    indice = state.STEPS.index(step_corrente)
    st.progress(indice / (len(state.STEPS) - 1))
    st.caption(f"Passo {indice + 1} di {len(state.STEPS)}: {step_corrente}")

    STEP_MODULES[step_corrente].render(dichiarazione)

    with st.sidebar:
        st.caption(f"Anno fiscale: {dichiarazione.anno_fiscale}")
        st.divider()
        st.markdown("**Connessione AI**")
        try:
            default_key = st.secrets["ANTHROPIC_API_KEY"]
        except Exception:
            default_key = ""
        api_key_input = st.text_input(
            "Chiave API Anthropic:", type="password",
            value=st.session_state.get("anthropic_api_key", default_key),
        )
        st.session_state["anthropic_api_key"] = api_key_input
        st.divider()
        if st.button("Ricomincia da capo"):
            state.reset_state()
            st.rerun()


if __name__ == "__main__":
    main()

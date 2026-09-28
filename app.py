"""app.py — entry point. streamlit run app.py

Homepage con 4 sotto-programmi (vista in session_state):
  'home'          — pagina iniziale, sceglie il sotto-programma
  'dichiarazione' — wizard della dichiarazione fiscale privata
  'preventivo'    — genera un preventivo DF PF
  'fatturazione'  — genera una fattura
  'archivio'      — elenco delle dichiarazioni salvate, per riprenderle
  'archivio_docs' — elenco di preventivi e fatture salvati
"""

import streamlit as st

from core import archivio_docs, salvataggio, state
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
NOME_PREVENTIVO = "Preventivo DF PF"

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
    Consigliato: il programma tratta dati fiscali/di fatturazione di clienti e gli archivi sono visibili a chi entra."""
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


def _naviga(destinazione: str) -> None:
    """Cambia sotto-programma. Se si sta lasciando una dichiarazione in corso, chiede prima
    se salvarla (dialog di conferma), invece di uscire subito e perdere il lavoro fatto."""
    if st.session_state.get("vista") == "dichiarazione" and destinazione != "dichiarazione":
        st.session_state["nav_pendente"] = destinazione
        st.rerun()
    else:
        _vai(destinazione)


def _pulsante_home() -> None:
    """Tasto azzurro in alto a sinistra, presente in ogni programma (dichiarazione, preventivo, fatturazione)."""
    if st.button("← Home", key="torna_home", type="primary"):
        _naviga("home")


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


@st.dialog("Salvare questa dichiarazione?")
def _dialog_conferma_uscita() -> None:
    destinazione = st.session_state.get("nav_pendente")
    st.write("Stai per uscire da questa dichiarazione. Vuoi salvarla nell'archivio prima di continuare?")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Salva ed esci", type="primary", key="dlg_salva_esci"):
            _salva_progetto()
            st.session_state.pop("nav_pendente", None)
            _vai(destinazione)
    with c2:
        if st.button("Esci senza salvare", key="dlg_esci"):
            st.session_state.pop("nav_pendente", None)
            _vai(destinazione)
    with c3:
        if st.button("Annulla", key="dlg_annulla"):
            st.session_state.pop("nav_pendente", None)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
# Barra laterale: solo un piccolo menu (Home, i 4 programmi, impostazioni)
# ══════════════════════════════════════════════════════════════════════
def _barra_laterale() -> None:
    with st.sidebar:
        st.markdown("### Athena")
        if st.button("🏠 Home", key="side_home", use_container_width=True):
            _naviga("home")
        st.caption("Programmi")
        if st.button("📄 Dichiarazione fiscale — Persone fisiche", key="side_df", use_container_width=True):
            state.init_state(anno_fiscale=ANNO_FISCALE_DEFAULT)
            _naviga("dichiarazione")
        if st.button(f"📋 {NOME_PREVENTIVO}", key="side_prev", use_container_width=True):
            _naviga("preventivo")
        if st.button("🧾 Fatturazione", key="side_fatt", use_container_width=True):
            _naviga("fatturazione")
        if st.button("🗂️ Archivio dichiarazioni", key="side_arch", use_container_width=True):
            _naviga("archivio")
        if st.button("🗃️ Archivio preventivi e fatture", key="side_arch_docs", use_container_width=True):
            _naviga("archivio_docs")
        st.divider()
        with st.expander("⚙️ Impostazioni"):
            st.caption(
                "La chiave API serve solo al pulsante 'Leggi documento con AI' nel certificato di salario. "
                "Il resto del programma funziona anche senza."
            )
            try:
                default_key = st.secrets["ANTHROPIC_API_KEY"]
            except Exception:
                default_key = ""
            st.session_state["anthropic_api_key"] = st.text_input(
                "Chiave API Anthropic", type="password",
                value=st.session_state.get("anthropic_api_key", default_key), key="side_api_key",
            )


# ══════════════════════════════════════════════════════════════════════
# Homepage
# ══════════════════════════════════════════════════════════════════════
def _tile(key: str, titolo: str, descrizione: str, icona: str, vista: str) -> None:
    with st.container(key=f"{key}_card", border=True):
        st.markdown(f"<div class='tile-icona'>{icona}</div>", unsafe_allow_html=True)
        st.markdown(f"**{titolo}**")
        st.caption(descrizione)
        if st.button("Apri →", key=key):
            _naviga(vista)


def _pagina_home() -> None:
    intestazione("Athena", "Contabilità Canton Ticino")

    with st.container(key="home_df_card", border=True):
        st.markdown("<div class='hero-etichetta'>BENVENUTO</div>", unsafe_allow_html=True)
        st.markdown("### 📄 Dichiarazione fiscale — Persone fisiche")
        st.write(
            "Compilazione guidata della dichiarazione fiscale privata, con generazione automatica "
            "dei moduli ufficiali del Cantone Ticino e calcolo del dispendio."
        )
        if st.button("Inizia →", key="home_df", type="primary"):
            state.init_state(anno_fiscale=ANNO_FISCALE_DEFAULT)
            _naviga("dichiarazione")

    st.write("")
    col1, col2, col3 = st.columns(3)
    with col1:
        _tile("home_prev", NOME_PREVENTIVO, "Genera il preventivo per i servizi fiduciari.", "🛡️", "preventivo")
    with col2:
        _tile("home_fatt", "Fatturazione", "Genera una fattura per un cliente.", "🧾", "fatturazione")
    with col3:
        _tile("home_arch", "Archivio dichiarazioni", "Riprendi una dichiarazione già salvata.", "🗂️", "archivio")

    st.write("")
    progetti = salvataggio.elenco()
    prev = archivio_docs.elenco("preventivo")
    fatt = archivio_docs.elenco("fattura")
    with st.container(key="home_stats_card", border=True):
        st.markdown("**La tua attività, in un colpo d'occhio**")
        s1, s2, s3 = st.columns(3)
        s1.metric("Dichiarazioni salvate", len(progetti))
        s2.metric(f"{NOME_PREVENTIVO} generati", len(prev))
        s3.metric("Fatture emesse", len(fatt))


# ══════════════════════════════════════════════════════════════════════
# Archivio dichiarazioni
# ══════════════════════════════════════════════════════════════════════
def _pagina_archivio() -> None:
    intestazione("Athena", "Archivio dichiarazioni")
    st.write("")

    progetti = salvataggio.elenco()
    if not progetti:
        st.info(
            "Nessuna dichiarazione salvata. Apri «Dichiarazione fiscale», compila quello che ti serve e usa "
            "«Salva il progetto» nella barra di navigazione: comparirà qui."
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
# Archivio preventivi e fatture
# ══════════════════════════════════════════════════════════════════════
def _pagina_archivio_docs() -> None:
    intestazione("Athena", "Archivio preventivi e fatture")
    st.write("")

    for tipo, etichetta, mime_nome in (("preventivo", NOME_PREVENTIVO, "Preventivo"), ("fattura", "Fatture", "Fattura")):
        st.subheader(etichetta)
        elenco = archivio_docs.elenco(tipo)
        if not elenco:
            st.caption("Nessun documento salvato.")
        for doc in elenco:
            with st.container(border=True):
                col_info, col_scarica, col_elimina = st.columns([5, 1, 1])
                with col_info:
                    st.markdown(f"**{doc['titolo']}**")
                    st.caption(f"salvato il {doc['salvato'][8:10]}.{doc['salvato'][5:7]}.{doc['salvato'][:4]}")
                with col_scarica:
                    st.download_button(
                        "Scarica", data=archivio_docs.carica_pdf(doc["id"]),
                        file_name=f"{mime_nome}_{doc['titolo']}.pdf".replace(" ", "_"),
                        mime="application/pdf", key=f"scarica_doc_{doc['id']}",
                    )
                with col_elimina:
                    if st.button("Elimina", key=f"elimina_doc_{doc['id']}"):
                        archivio_docs.elimina(doc["id"])
                        st.rerun()
        st.write("")


# ══════════════════════════════════════════════════════════════════════
# Dichiarazione fiscale: navigazione centralizzata (Ricomincia, Salva, Indietro, Avanti)
# ══════════════════════════════════════════════════════════════════════
def _barra_navigazione(step_corrente: str, indice: int) -> None:
    with st.container(key="barra_fissa"):
        col_reset, col_salva, _, col_back, col_next = st.columns([1.3, 1.6, 3.2, 1, 1])
        with col_reset:
            if st.button("↺ Ricomincia", key="reset_tutto"):
                state.reset_state()
                st.rerun()
        with col_salva:
            if st.button("💾 Salva progetto", key="salva_progetto"):
                _salva_progetto()
        with col_back:
            if indice > 0:
                if st.button("← Indietro", key="nav_indietro"):
                    state.go_back()
                    st.rerun()
        with col_next:
            if step_corrente != "benvenuto" and indice < len(state.STEPS) - 1:
                if st.button("Avanti →", key="nav_avanti", type="primary"):
                    state.go_next()
                    st.rerun()


def _pagina_dichiarazione() -> None:
    state.init_state(anno_fiscale=ANNO_FISCALE_DEFAULT)
    dichiarazione = state.get_dichiarazione()
    intestazione("Athena", "Dichiarazione fiscale privata — compilazione assistita")
    _pulsante_home()

    step_corrente = state.current_step()
    indice = state.STEPS.index(step_corrente)
    st.progress(indice / (len(state.STEPS) - 1))
    st.caption(f"Anno fiscale {dichiarazione.anno_fiscale} — passo {indice + 1} di {len(state.STEPS)}")

    STEP_MODULES[step_corrente].render(dichiarazione)
    _barra_navigazione(step_corrente, indice)
    piede_pagina()


def main() -> None:
    st.set_page_config(
        page_title="Athena — dichiarazioni, preventivi e fatture",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    applica_stile()

    if not _accesso_consentito():
        return

    if st.session_state.get("nav_pendente"):
        _dialog_conferma_uscita()

    _barra_laterale()

    vista = st.session_state.get("vista", "home")

    if vista == "home":
        _pagina_home()
    elif vista == "dichiarazione":
        _pagina_dichiarazione()
    elif vista == "preventivo":
        intestazione("Athena", f"{NOME_PREVENTIVO} — servizi fiduciari")
        _pulsante_home()
        preventivo.render()
        piede_pagina(con_avviso=False)
    elif vista == "fatturazione":
        intestazione("Athena", "Fatturazione")
        _pulsante_home()
        fatturazione.render()
        piede_pagina(con_avviso=False)
    elif vista == "archivio":
        _pulsante_home()
        _pagina_archivio()
    elif vista == "archivio_docs":
        _pulsante_home()
        _pagina_archivio_docs()
    else:
        st.session_state["vista"] = "home"
        st.rerun()


if __name__ == "__main__":
    main()

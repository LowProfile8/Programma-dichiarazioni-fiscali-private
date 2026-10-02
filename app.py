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

from core import archivio_docs, salvataggio, state, supabase_store
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
    preventivo_azienda,
    preventivo_libero,
    preventivo_tipo,
    riepilogo,
    spese_professionali,
    titoli_investimenti,
    veicoli,
)

ANNO_FISCALE_DEFAULT = 2025
NOME_PREVENTIVO = "Preventivo"
VISTE_PREVENTIVO = ("preventivo_tipo", "preventivo", "preventivo_azienda", "preventivo_libero")

# Icone minimali (solo contorno) per le card della home — niente emoji, per un aspetto più sobrio
_ICONA_SCUDO = (
    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#16A34A" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/></svg>'
)
_ICONA_DOCUMENTO = (
    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/>'
    '<path d="M9.5 12.5h5M9.5 15.5h5M9.5 9.5h2"/></svg>'
)
_ICONA_CARTELLA = (
    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#9333EA" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M3 6.5a1 1 0 0 1 1-1h4.5l2 2H20a1 1 0 0 1 1 1V18a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/></svg>'
)

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
    """Schermata di accesso a schermo intero, prima di qualunque altra pagina. Password di
    default "Athena"; se nei secrets di Streamlit c'è APP_PASSWORD, quella ha la precedenza."""
    if st.session_state.get("_autenticato"):
        return True
    try:
        password_attesa = str(st.secrets["APP_PASSWORD"])
    except Exception:
        password_attesa = "Athena"

    st.markdown("<span class='accesso-marcatore'></span>", unsafe_allow_html=True)
    _, colonna_centro, _ = st.columns([1, 1.3, 1])
    with colonna_centro:
        st.markdown("<p class='accesso-titolo'>Password</p>", unsafe_allow_html=True)
        col_campo, col_tasto = st.columns([4, 1], gap="small", vertical_alignment="bottom")
        with col_campo:
            codice = st.text_input(
                "Password", key="campo_password", type="password",
                label_visibility="collapsed", placeholder="",
            )
        with col_tasto:
            st.button("→", key="invia_password")   # invio con Invio o con il clic: text_input già aggiorna codice
        if codice and codice != password_attesa:
            st.markdown("<p class='accesso-errore'>Codice non corretto.</p>", unsafe_allow_html=True)

        # Il tentativo di forzare lo sfondo azzurro della casella non ha funzionato in modo
        # affidabile (Chrome, per i campi password, impone il proprio stile e lo sostituisce
        # a ogni giro). Soluzione più semplice e sicura: lasciamo che la casella resti chiara
        # e scriviamo il testo in nero, così si legge comunque qualunque sia lo sfondo.
        st.markdown(
            """<style>
            div[data-testid="stTextInput"] input {
                color: #000000 !important; -webkit-text-fill-color: #000000 !important;
                caret-color: #000000 !important;
            }
            </style>""",
            unsafe_allow_html=True,
        )

    if codice and codice == password_attesa:
        st.session_state["_autenticato"] = True
        st.session_state.pop("campo_password", None)
        st.rerun()
    return False


def _vai(vista: str) -> None:
    st.session_state["vista"] = vista
    st.rerun()


_VISTE_CON_CONFERMA = ("dichiarazione", "preventivo", "preventivo_azienda", "preventivo_libero", "fatturazione")


def _naviga(destinazione: str) -> None:
    """Cambia sotto-programma. Se si sta lasciando una dichiarazione, un preventivo o una fattura
    in corso di compilazione, chiede prima se salvare (dialog di conferma), invece di uscire
    subito e perdere il lavoro fatto."""
    vista_attuale = st.session_state.get("vista")
    if vista_attuale in _VISTE_CON_CONFERMA and destinazione != vista_attuale:
        st.session_state["nav_pendente"] = destinazione
        st.session_state["nav_pendente_da"] = vista_attuale
        st.rerun()
    else:
        _vai(destinazione)


def _pulsante_home() -> None:
    """Tasto azzurro in alto a sinistra, presente in ogni programma (dichiarazione, preventivo, fatturazione)."""
    if st.button("← Home", key="torna_home", type="primary"):
        _naviga("home")


def _pulsante_home_e_preventivi() -> None:
    """Come _pulsante_home, ma con in più — alla stessa altezza, a destra, stessa grafica —
    un tasto per tornare alla scelta del tipo di preventivo (visibile mentre si compila uno
    dei tre tipi di preventivo)."""
    col_home, col_altri = st.columns([1, 1])
    with col_home:
        if st.button("← Home", key="torna_home", type="primary"):
            _naviga("home")
    with col_altri:
        with st.container(key="tasto_altri_preventivi"):
            if st.button("Altri preventivi →", key="torna_altri_preventivi", type="primary"):
                _naviga("preventivo_tipo")


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


_NOMI_VISTA = {
    "dichiarazione": "questa dichiarazione", "preventivo": "questo preventivo",
    "preventivo_azienda": "questo preventivo", "preventivo_libero": "questo preventivo",
    "fatturazione": "questa fattura",
}


_PREFISSO_SALVATAGGIO = {
    "preventivo": ("preventivo", "preventivo"),
    "preventivo_azienda": ("pa", "preventivo"),
    "preventivo_libero": ("pl", "preventivo"),
    "fatturazione": ("fattura", "fattura"),
}


def _salva_documento_in_sessione(vista_da: str) -> bool:
    """Salva nell'archivio il preventivo/fattura generato in questa vista, se c'è.
    Ritorna False se non era ancora stato generato nulla da salvare."""
    riferimento = _PREFISSO_SALVATAGGIO.get(vista_da)
    if not riferimento:
        return False
    prefisso, tipo = riferimento
    if f"{prefisso}_pdf" not in st.session_state:
        return False
    archivio_docs.salva(
        tipo, st.session_state[f"{prefisso}_dati"], st.session_state[f"{prefisso}_pdf"],
        st.session_state[f"{prefisso}_titolo_archivio"], doc_id=st.session_state[f"{prefisso}_doc_id"],
        **st.session_state[f"{prefisso}_extra"],
    )
    st.session_state[f"{prefisso}_salvato"] = True
    st.toast(f"Salvato: {st.session_state[f'{prefisso}_titolo_archivio']}")
    return True


@st.dialog("Salvare prima di uscire?")
def _dialog_conferma_uscita() -> None:
    destinazione = st.session_state.get("nav_pendente")
    vista_da = st.session_state.get("nav_pendente_da")
    nome = _NOMI_VISTA.get(vista_da, "questa scheda")
    e_dichiarazione = vista_da == "dichiarazione"
    if e_dichiarazione:
        st.write(f"Stai per uscire da {nome}. Vuoi salvarla nell'archivio prima di continuare?")
    else:
        st.write(
            f"Stai per uscire da {nome}. Se hai già generato il PDF, posso salvarlo nell'archivio "
            "prima di uscire — altrimenti non c'è ancora nulla da salvare."
        )
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Salva ed esci", type="primary", key="dlg_salva_esci"):
            if e_dichiarazione:
                _salva_progetto()
            else:
                _salva_documento_in_sessione(vista_da)
            st.session_state.pop("nav_pendente", None)
            st.session_state.pop("nav_pendente_da", None)
            _vai(destinazione)
    with c2:
        if st.button("Esci senza salvare", key="dlg_esci"):
            st.session_state.pop("nav_pendente", None)
            st.session_state.pop("nav_pendente_da", None)
            _vai(destinazione)
    with c3:
        if st.button("Annulla", key="dlg_annulla"):
            st.session_state.pop("nav_pendente", None)
            st.session_state.pop("nav_pendente_da", None)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
# Barra laterale: solo un piccolo menu (Home, i 4 programmi, impostazioni)
# ══════════════════════════════════════════════════════════════════════
def _voce_laterale(etichetta: str, vista: str, indica_dichiarazione: bool = False, anche_attiva_per: tuple = ()) -> None:
    """Una voce del menu; diventa una pillola piena se è il programma (o una delle sue
    sotto-pagine, tramite anche_attiva_per) in cui ci si trova adesso."""
    vista_attuale = st.session_state.get("vista", "home")
    attiva = vista_attuale == vista or vista_attuale in anche_attiva_per
    chiave = "side_attivo" if attiva else f"side_{vista}_{etichetta[:6]}"
    with st.container(key=chiave):
        if st.button(etichetta, key=f"btn_{chiave}_{etichetta[:10]}", use_container_width=True):
            if indica_dichiarazione:
                state.init_state(anno_fiscale=ANNO_FISCALE_DEFAULT)
            _naviga(vista)


def _barra_laterale() -> None:
    from core.ui_helpers import _LOGO_TICINO
    with st.sidebar:
        st.markdown("### Athena Advisory Group")
        if _LOGO_TICINO.exists():
            st.image(str(_LOGO_TICINO), width=20)
        st.divider()
        _voce_laterale("Home", "home")
        st.write("")
        _voce_laterale("Dichiarazione fiscale — Persone fisiche", "dichiarazione", indica_dichiarazione=True)
        _voce_laterale("Archivio dichiarazioni", "archivio")
        st.write("")
        _voce_laterale(NOME_PREVENTIVO, "preventivo_tipo", anche_attiva_per=VISTE_PREVENTIVO)
        _voce_laterale("Archivio preventivi", "archivio_preventivi")
        st.write("")
        _voce_laterale("Fatturazione", "fatturazione")
        _voce_laterale("Archivio fatture", "archivio_fatture")

        _barra_stato_supabase()


def _barra_stato_supabase() -> None:
    """Angolo in basso a sinistra, fissato allo schermo (non all'interno del normale flusso
    della barra laterale): un pallino verde se Supabase risponde, arancione se è configurato
    ma non raggiungibile (es. sospeso per inattività — qui lo si nota subito, invece di
    accorgersene solo quando un salvataggio fallisce)."""
    stato = supabase_store.stato_connessione()
    if stato is None:
        return   # Supabase non configurato: niente da segnalare, si usa il salvataggio locale
    colore, testo = ("#22C55E", "Cloud collegato") if stato else ("#F59E0B", "Cloud non raggiungibile")
    with st.container(key="stato_cloud_fisso"):
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:7px;'>"
            f"<span style='width:8px;height:8px;border-radius:50%;background:{colore};"
            f"box-shadow:0 0 5px {colore};flex-shrink:0;'></span>"
            f"<span style='font-size:0.76rem;color:#FFFFFF;'>{testo}</span></div>",
            unsafe_allow_html=True,
        )
        if not stato:
            st.caption(
                "Se dura, riapri il sito fra un minuto: Supabase a volte si sospende da solo "
                "dopo tanta inattività e si riattiva da solo alla prima richiesta."
            )


# ══════════════════════════════════════════════════════════════════════
# Homepage
# ══════════════════════════════════════════════════════════════════════
def _tile(key: str, titolo: str, descrizione: str, icona: str, colore: str, vista: str) -> None:
    with st.container(key=f"{key}_card", border=True):
        st.markdown(f"<div class='tile-icona tile-icona-{colore}'>{icona}</div>", unsafe_allow_html=True)
        st.markdown(f"**{titolo}**")
        st.caption(descrizione)
        st.markdown('<div class="tasto-freccia">', unsafe_allow_html=True)
        if st.button("→", key=key):
            _naviga(vista)
        st.markdown('</div>', unsafe_allow_html=True)


def _statistiche_home():
    """I tre elenchi per le statistiche della home, caricati insieme invece che in fila:
    sulla home la pagina deve apparire il più in fretta possibile."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_progetti = pool.submit(salvataggio.elenco)
        f_prev = pool.submit(archivio_docs.elenco, "preventivo")
        f_fatt = pool.submit(archivio_docs.elenco, "fattura")
        try:
            progetti = f_progetti.result()
        except Exception:
            progetti = []
        try:
            prev = f_prev.result()
        except Exception:
            prev = []
        try:
            fatt = f_fatt.result()
        except Exception:
            fatt = []
    return progetti, prev, fatt


def _pagina_home() -> None:
    intestazione("Athena Advisory Group", "Contabilità Canton Ticino")

    with st.container(key="home_df_card", border=True):
        col_spazio_sx, col_testo, col_icona, col_spazio_dx = st.columns([0.6, 4.4, 1, 0.3], vertical_alignment="center")
        with col_testo:
            st.markdown("<div class='hero-etichetta'>BENVENUTO</div>", unsafe_allow_html=True)
            st.markdown("### Dichiarazione fiscale — Persone fisiche")
            st.write(
                "Compilazione guidata della dichiarazione fiscale privata, con generazione automatica "
                "dei moduli ufficiali del Cantone Ticino e calcolo del dispendio."
            )
            if st.button("Inizia →", key="home_df", type="primary"):
                state.init_state(anno_fiscale=ANNO_FISCALE_DEFAULT)
                _naviga("dichiarazione")
        with col_icona:
            icona_hero = (
                _ICONA_DOCUMENTO.replace('width="26" height="26"', 'width="32" height="32"')
                .replace('stroke="#2563EB"', 'stroke="#9333EA"')   # viola, come il resto dei simboli della DF PF
            )
            st.markdown(
                "<div class='tile-icona tile-icona-viola' style='width:64px;height:64px;margin:0 auto;'>"
                f"{icona_hero}</div>",
                unsafe_allow_html=True,
            )

    st.write("")
    col1, col2, col3 = st.columns(3)
    with col1:
        _tile("home_prev", NOME_PREVENTIVO, "Genera un preventivo per servizi fiduciari.", _ICONA_SCUDO, "verde", "preventivo_tipo")
    with col2:
        _tile("home_fatt", "Fatturazione", "Genera una fattura per un cliente.", _ICONA_DOCUMENTO, "blu", "fatturazione")
    with col3:
        _tile("home_arch", "Archivio dichiarazioni", "Riprendi una dichiarazione già salvata.", _ICONA_CARTELLA, "viola", "archivio")

    st.write("")
    progetti, prev, fatt = _statistiche_home()
    with st.container(key="home_stats_card", border=True):
        st.markdown("**La tua attività, in un colpo d'occhio** — clicca per aprire l'archivio")
        # Stesso ordine dei tre tasti sopra: preventivi a sinistra, fatture al centro, dichiarazioni a destra
        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(f"<div class='tile-icona tile-icona-verde'>{_ICONA_SCUDO}</div>", unsafe_allow_html=True)
            st.metric(f"{NOME_PREVENTIVO} generati", len(prev))
            if st.button("Apri l'archivio", key="stat_arch_prev"):
                _naviga("archivio_preventivi")
        with s2:
            st.markdown(f"<div class='tile-icona tile-icona-blu'>{_ICONA_DOCUMENTO}</div>", unsafe_allow_html=True)
            st.metric("Fatture emesse", len(fatt))
            if st.button("Apri l'archivio", key="stat_arch_fatt"):
                _naviga("archivio_fatture")
        with s3:
            st.markdown(f"<div class='tile-icona tile-icona-viola'>{_ICONA_CARTELLA}</div>", unsafe_allow_html=True)
            st.metric("Dichiarazioni salvate", len(progetti))
            if st.button("Apri l'archivio", key="stat_arch_df"):
                _naviga("archivio")


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
                st.warning(f"Eliminare definitivamente **{p['titolo']}**?")
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
# Archivio preventivi / Archivio fatture (pagine separate)
# ══════════════════════════════════════════════════════════════════════
def _pagina_archivio_tipo(tipo: str, titolo_pagina: str, mime_nome: str) -> None:
    intestazione("Athena", titolo_pagina)
    st.write("")

    elenco = archivio_docs.elenco(tipo)
    if not elenco:
        st.info(f"Nessun documento salvato. Genera un {mime_nome.lower()} e comparirà qui.")
        return

    if tipo == "fattura":
        _archivio_fatture(elenco, mime_nome)
    else:
        _archivio_preventivi(elenco, mime_nome)


def _scarica_pdf_sicuro(doc_id: str):
    """Il PDF di un documento salvato potrebbe mancare (es. un tentativo precedente interrotto
    a metà, prima di una correzione): qui lo segnaliamo con un avviso invece di far bloccare
    tutta la pagina dell'archivio."""
    try:
        return archivio_docs.carica_pdf(doc_id)
    except Exception:
        return None


def _bottone_scarica(doc: dict, mime_nome: str, prefisso: str) -> None:
    """Scarica il PDF solo quando richiesto (un clic prepara, il secondo scarica), invece di
    scaricare per intero OGNI documento a ogni apertura della pagina solo per mostrare il
    tasto: con molti documenti è quello che rendeva l'archivio lento."""
    chiave_pdf = f"{prefisso}_pdf_{doc['id']}"
    if chiave_pdf in st.session_state:
        st.download_button(
            "Scarica", data=st.session_state[chiave_pdf],
            file_name=f"{mime_nome}_{doc['titolo']}.pdf".replace(" ", "_"),
            mime="application/pdf", key=f"{prefisso}_scarica_{doc['id']}",
        )
    else:
        if st.button("Prepara scarico", key=f"{prefisso}_prepara_{doc['id']}"):
            pdf = _scarica_pdf_sicuro(doc["id"])
            if pdf is not None:
                st.session_state[chiave_pdf] = pdf
                st.rerun()
            else:
                st.caption("⚠️ PDF non trovato")


def _archivio_preventivi(elenco: list, mime_nome: str) -> None:
    """Come l'archivio fatture: ricerca e filtro per cliente, più un interruttore
    accettato/non accettato per ogni preventivo (parte sempre su «No» appena creato)."""
    ricerca = st.text_input("Cerca per cliente", key="ricerca_preventivi", placeholder="es. Rossi, Esempio Sagl")
    if ricerca.strip():
        r = ricerca.strip().lower()
        elenco = [d for d in elenco if r in (d.get("cliente") or "").lower() or r in d["titolo"].lower()]

    clienti = sorted({d.get("cliente") or "Cliente sconosciuto" for d in elenco})
    scelta_cliente = st.selectbox("Filtra per cliente", ["Tutti i clienti"] + clienti, key="filtro_cliente_preventivi")
    if scelta_cliente != "Tutti i clienti":
        elenco = [d for d in elenco if (d.get("cliente") or "Cliente sconosciuto") == scelta_cliente]

    st.divider()
    if not elenco:
        st.caption("Nessun preventivo corrisponde alla ricerca.")
    for doc in elenco:
        accettato_attuale = bool(doc.get("accettato"))
        chiave = f"prev_card_{doc['id']}"
        if accettato_attuale:
            st.markdown(
                f"<style>.st-key-{chiave} {{ border: 1.6px solid #22C55E !important; border-radius: 10px; }}</style>",
                unsafe_allow_html=True,
            )
        with st.container(key=chiave, border=True):
            col_info, col_scarica, col_elimina = st.columns([5, 1, 1])
            with col_info:
                st.markdown(f"**{doc['titolo']}**")
                st.caption(f"salvato il {doc['salvato'][8:10]}.{doc['salvato'][5:7]}.{doc['salvato'][:4]}")
            with col_scarica:
                _bottone_scarica(doc, mime_nome, "prev")
            with col_elimina:
                if st.button("Elimina", key=f"elimina_prev_{doc['id']}"):
                    st.session_state["conferma_elimina_doc"] = doc["id"]
                    st.rerun()
            if st.session_state.get("conferma_elimina_doc") == doc["id"]:
                st.warning(f"Eliminare definitivamente **{doc['titolo']}**?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Sì, elimina", key=f"prev_elimina_si_{doc['id']}"):
                        archivio_docs.elimina(doc["id"])
                        st.session_state.pop("conferma_elimina_doc", None)
                        st.rerun()
                with c2:
                    if st.button("No", key=f"prev_elimina_no_{doc['id']}"):
                        st.session_state.pop("conferma_elimina_doc", None)
                        st.rerun()

            nuovo_accettato = st.radio(
                "Accettato", ["No", "Sì"], index=1 if accettato_attuale else 0,
                key=f"accettato_{doc['id']}", horizontal=True,
            ) == "Sì"
            if nuovo_accettato != accettato_attuale:
                archivio_docs.aggiorna_extra(doc["id"], accettato=nuovo_accettato)
                st.rerun()


def _archivio_fatture(elenco: list, mime_nome: str) -> None:
    """Serve anche da controllo pagamenti: chi ha pagato, chi manca ancora, filtrabile per cliente."""
    import datetime as _dt

    anno_corrente = _dt.date.today().year
    fatture_anno = [d for d in elenco if str(d.get("salvato", ""))[:4] == str(anno_corrente)]
    non_pagate = [d for d in elenco if not d.get("pagato")]
    totale_da_incassare = sum(float(d.get("importo") or 0) for d in non_pagate)
    fatturato_anno = sum(float(d.get("importo") or 0) for d in fatture_anno)
    incassato_anno = sum(float(d.get("importo") or 0) for d in fatture_anno if d.get("pagato"))

    c1, c2, c3 = st.columns(3)
    c1.metric("Fatture totali", len(elenco))
    c2.metric("Non ancora pagate", len(non_pagate))
    c3.metric("Da incassare", f"Fr. {totale_da_incassare:,.2f}".replace(",", "'"))
    c4, c5 = st.columns(2)
    c4.metric(f"Fatturato {anno_corrente}", f"Fr. {fatturato_anno:,.2f}".replace(",", "'"))
    c5.metric(f"Incassato {anno_corrente}", f"Fr. {incassato_anno:,.2f}".replace(",", "'"))

    ricerca = st.text_input("Cerca per cliente o numero fattura", key="ricerca_fatture", placeholder="es. Alborella, 20260930")
    if ricerca.strip():
        r = ricerca.strip().lower()
        elenco = [d for d in elenco if r in (d.get("cliente") or "").lower() or r in d["titolo"].lower()]

    clienti = sorted({d.get("cliente") or "Cliente sconosciuto" for d in elenco})
    scelta_cliente = st.selectbox("Filtra per cliente", ["Tutti i clienti"] + clienti, key="filtro_cliente_fatture")
    if scelta_cliente != "Tutti i clienti":
        elenco = [d for d in elenco if (d.get("cliente") or "Cliente sconosciuto") == scelta_cliente]

    st.divider()
    gruppi: dict = {}
    for d in elenco:
        gruppi.setdefault(d.get("cliente") or "Cliente sconosciuto", []).append(d)

    for cliente in sorted(gruppi):
        fatture_cliente = gruppi[cliente]
        dovuto = sum(float(d.get("importo") or 0) for d in fatture_cliente if not d.get("pagato"))
        etichetta_dovuto = f" · ancora da incassare: Fr. {dovuto:,.2f}".replace(",", "'") if dovuto else " · tutto pagato ✓"
        st.markdown(f"#### {cliente}{etichetta_dovuto}")

        for doc in fatture_cliente:
            pagato = bool(doc.get("pagato"))
            colore = "#22C55E" if pagato else "#F59E0B"   # verde se pagata, giallo/arancio se in attesa
            chiave = f"fatt_card_{doc['id']}"
            st.markdown(
                f"<style>.st-key-{chiave} {{ border: 1.6px solid {colore} !important; border-radius: 10px; }}</style>",
                unsafe_allow_html=True,
            )
            with st.container(key=chiave, border=True):
                col_info, col_importo, col_scarica, col_elimina = st.columns([3, 1.4, 1, 1])
                with col_info:
                    st.markdown(f"**{doc['titolo']}**")
                    st.caption(f"salvato il {doc['salvato'][8:10]}.{doc['salvato'][5:7]}.{doc['salvato'][:4]}")
                with col_importo:
                    importo = doc.get("importo")
                    if importo:
                        st.caption(f"Fr. {float(importo):,.2f}".replace(",", "'"))
                with col_scarica:
                    _bottone_scarica(doc, mime_nome, "fatt")
                with col_elimina:
                    if st.button("Elimina", key=f"elimina_fatt_{doc['id']}"):
                        st.session_state["conferma_elimina_doc"] = doc["id"]
                        st.rerun()
                if st.session_state.get("conferma_elimina_doc") == doc["id"]:
                    st.warning(f"Eliminare definitivamente **{doc['titolo']}**?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Sì, elimina", key=f"fatt_elimina_si_{doc['id']}"):
                            archivio_docs.elimina(doc["id"])
                            st.session_state.pop("conferma_elimina_doc", None)
                            st.rerun()
                    with c2:
                        if st.button("No", key=f"fatt_elimina_no_{doc['id']}"):
                            st.session_state.pop("conferma_elimina_doc", None)
                            st.rerun()

                col_pagato, col_data = st.columns([1, 2])
                with col_pagato:
                    nuovo_pagato = st.radio(
                        "Pagato", ["No", "Sì"], index=1 if pagato else 0, key=f"pagato_{doc['id']}", horizontal=True,
                    ) == "Sì"
                with col_data:
                    data_pagamento = None
                    if nuovo_pagato:
                        valore_data = doc.get("data_pagamento")
                        data_default = _dt.date.fromisoformat(valore_data) if valore_data else _dt.date.today()
                        data_pagamento = st.date_input(
                            "Data di pagamento (facoltativa)", value=data_default,
                            key=f"data_pag_{doc['id']}", format="DD/MM/YYYY",
                        )
                if nuovo_pagato != pagato or (nuovo_pagato and str(data_pagamento) != doc.get("data_pagamento")):
                    archivio_docs.aggiorna_extra(
                        doc["id"], pagato=nuovo_pagato,
                        data_pagamento=data_pagamento.isoformat() if (nuovo_pagato and data_pagamento) else None,
                    )
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════
# Dichiarazione fiscale: navigazione centralizzata (Ricomincia, Salva, Indietro, Avanti)
# ══════════════════════════════════════════════════════════════════════
def _barra_navigazione(step_corrente: str, indice: int) -> None:
    with st.container(key="barra_fissa"):
        col_reset, col_salva, _, col_back, col_next = st.columns([1.5, 1.8, 1.0, 1.4, 1.4])
        with col_reset:
            if st.button("Ricomincia", key="reset_tutto"):
                state.reset_state()
                st.rerun()
        with col_salva:
            if st.button("Salva progetto", key="salva_progetto"):
                _salva_progetto()
        with col_back:
            if indice > 0:
                if st.button("Indietro", key="nav_indietro"):
                    state.go_back()
                    st.rerun()
        with col_next:
            if step_corrente != "benvenuto" and indice < len(state.STEPS) - 1:
                if st.button("Avanti", key="nav_avanti", type="primary"):
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
    elif vista == "preventivo_tipo":
        intestazione("Athena", "Preventivo")
        _pulsante_home()
        preventivo_tipo.render(_naviga)
        piede_pagina(con_avviso=False)
    elif vista == "preventivo":
        intestazione("Athena", "Preventivo DF PF — servizi fiduciari")
        _pulsante_home_e_preventivi()
        preventivo.render()
        piede_pagina(con_avviso=False)
    elif vista == "preventivo_azienda":
        intestazione("Athena", "Preventivo — contabilità aziendale")
        _pulsante_home_e_preventivi()
        preventivo_azienda.render()
        piede_pagina(con_avviso=False)
    elif vista == "preventivo_libero":
        intestazione("Athena", "Altri Preventivi")
        _pulsante_home_e_preventivi()
        preventivo_libero.render()
        piede_pagina(con_avviso=False)
    elif vista == "fatturazione":
        intestazione("Athena", "Fatturazione")
        _pulsante_home()
        fatturazione.render()
        piede_pagina(con_avviso=False)
    elif vista == "archivio":
        _pulsante_home()
        _pagina_archivio()
    elif vista == "archivio_preventivi":
        _pulsante_home()
        _pagina_archivio_tipo("preventivo", "Archivio preventivi", "Preventivo")
    elif vista == "archivio_fatture":
        _pulsante_home()
        _pagina_archivio_tipo("fattura", "Archivio fatture", "Fattura")
    else:
        st.session_state["vista"] = "home"
        st.rerun()


if __name__ == "__main__":
    main()

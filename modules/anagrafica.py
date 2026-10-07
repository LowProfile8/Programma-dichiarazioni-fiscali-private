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
from core.calcoli import (
    DEDUZIONE_FIGLIO_IC, DEDUZIONE_FIGLIO_SOSTANZA, DEDUZIONE_PERSONA_BISOGNOSA_MAX, DEDUZIONE_PERSONA_BISOGNOSA_MIN,
    deduzione_persona_bisognosa, deduzione_studi_figlio, eta_figlio, formazione_figlio, numero,
)
from core.models import (
    Contribuente, DatiPersonaFisica, DichiarazioneFiscale, Figlio, GenereAttivita, PersonaBisognosa, StatoCivile,
)
from core.ui_helpers import campo_con_fallback


def _blocco_persona(persona, key_prefix: str, titolo: str, anno_fiscale: int) -> None:
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

    persona.domicilio_cambiato = not st.checkbox(
        "Ha vissuto tutto l'anno nella stessa casa", value=not persona.domicilio_cambiato, key=f"{key_prefix}_stesso_dom",
    )
    if persona.domicilio_cambiato:
        col_dom2, col_data = st.columns(2)
        with col_dom2:
            persona.domicilio_secondario = st.text_input(
                "Comune della seconda casa", value=persona.domicilio_secondario, key=f"{key_prefix}_dom2",
            )
        with col_data:
            persona.data_cambio_domicilio = st.date_input(
                "Da quando vive nella seconda casa", value=persona.data_cambio_domicilio, key=f"{key_prefix}_data_dom2",
                min_value=date(anno_fiscale, 1, 1), max_value=date(anno_fiscale, 12, 31), format="DD/MM/YYYY",
            )
        st.caption(
            "Nel Modulo 4 calcoliamo i km del tragitto casa-lavoro separatamente per i due periodi "
            "(dal 1° gennaio fino al cambio, e dal cambio al 31 dicembre)."
        )

    selezione = st.multiselect(
        "Genere di attività", options=list(GenereAttivita), format_func=lambda g: g.value,
        default=persona.genere_attivita, key=f"{key_prefix}_genere_ms",
        placeholder="Scegli una o più opzioni",
    )
    persona.genere_attivita = selezione

    if GenereAttivita.INDIPENDENTE in selezione:
        st.caption(
            "ℹ️ Il reddito da attività indipendente (utile o perdita dal conto economico dell'esercizio chiuso nel 2025) "
            "si inserisce nel passo «Altri redditi e deduzioni». Vanno allegati bilancio e conto economico firmati."
        )
    if GenereAttivita.PENSIONATO in selezione:
        st.caption(
            "ℹ️ Pensioni, rendite AVS/AI e rendite vitalizie si inseriscono nel passo «Altri redditi e deduzioni» "
            "(si dichiara l'importo lordo, al 100%): lì il programma calcola anche la quota esente per i beneficiari AVS/AI."
        )
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


_OPZIONI_FORMAZIONE = {
    "": "Nessuna (scuola dell'obbligo, lavora o altro)",
    "tirocinio": "Apprendistato / tirocinio",
    "scuola": "Scuola a tempo pieno oltre l'obbligo (liceo, scuola specializzata, ecc.)",
    "universita": "Studi accademici (università, scuola universitaria professionale)",
}


def _blocco_figlio(dichiarazione: DichiarazioneFiscale, figlio: Figlio, i: int) -> None:
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

        eta = eta_figlio(dichiarazione, figlio)
        if eta is None:
            return
        anno = dichiarazione.anno_fiscale
        st.caption(f"Età al 31.12.{anno}: {eta} anni")
        figlio.professione_attivita = st.text_input(
            "Scuola o attività (facoltativo)", value=figlio.professione_attivita, key=f"figlio_attivita_{i}",
            help="Es. «Scuola dell'infanzia», «Liceo cantonale di Lugano 1», «Apprendista meccanico». Si scrive nel Modulo 1.",
        )

        if eta < 14:
            figlio.in_cura_da_terzi = st.checkbox(
                "In cura da terzi durante l'orario di lavoro dei genitori (asilo nido, tata, doposcuola, famiglia diurna — non le rette scolastiche)",
                value=bool(figlio.in_cura_da_terzi), key=f"figlio_cura_{i}",
                help="Si deducono le spese comprovate di cura, fino a Fr. 26'200 per figlio, solo per le ore in cui i genitori lavorano "
                     "o studiano. Non sono ammessi pasti e alloggio, né il personale domestico. Se hai ricevuto rimborsi "
                     "(RiSC dell'IAS) indica la retta al netto del rimborso.",
            )
            if figlio.in_cura_da_terzi:
                figlio.nome_istituto_cura = st.text_input(
                    "Nome dell'istituto o della persona che presta la cura",
                    value=figlio.nome_istituto_cura, key=f"figlio_istituto_{i}",
                )
                campo_con_fallback(
                    figlio.spese_cura_annuali, "Spese annuali sostenute (al netto di eventuali rimborsi)", key=f"figlio_spese_cura_{i}",
                    descrizione_ricerca=f"Spese di cura da terzi per il figlio {figlio.nome}, Modulo 6 retro, cifra 20"
                )
                file_fattura = st.file_uploader(
                    "Fattura/e della struttura o della persona che presta la cura",
                    type=["pdf", "png", "jpg", "jpeg"], key=f"figlio_fattura_{i}",
                )
                if file_fattura is not None:
                    figlio.file_fatture_cura = file_fattura.name
            else:
                figlio.in_cura_da_terzi = False
        else:
            figlio.in_cura_da_terzi = False

        if eta < 18:
            st.caption(f"Minorenne: deduzione per figlio a carico Fr. {DEDUZIONE_FIGLIO_IC:,}.".replace(",", "'"))
        elif eta > 28:
            st.info("Oltre il 28° anno di età non è più ammessa la deduzione per figlio a carico né per figlio agli studi.")
            figlio.formazione, figlio.agli_studi = "", False
            return

        if eta >= 14:
            if eta >= 18:
                st.markdown("**Formazione** — dopo i 18 anni è a carico solo se a tirocinio o agli studi")
            else:
                st.markdown("**Formazione** (scuola oltre l'obbligo)")
            opzioni = list(_OPZIONI_FORMAZIONE.keys())
            scelta = st.selectbox(
                "Che cosa fa?", opzioni, index=opzioni.index(formazione_figlio(figlio)) if formazione_figlio(figlio) in opzioni else 0,
                format_func=lambda k: _OPZIONI_FORMAZIONE[k], key=f"figlio_formazione_{i}",
            )
            figlio.formazione = scelta
            figlio.agli_studi = scelta in ("scuola", "universita")
            if eta >= 18 and scelta == "":
                st.warning(
                    f"Senza tirocinio o studi un figlio maggiorenne non è a carico: nessuna deduzione di Fr. {DEDUZIONE_FIGLIO_IC:,}. "
                    "Se non può guadagnare per invalidità o malattia, indicalo tra le «persone bisognose a carico» qui sotto.".replace(",", "'"))
            if scelta == "tirocinio":
                st.caption(
                    f"Deduzione per figlio a carico Fr. {DEDUZIONE_FIGLIO_IC:,}. Per chi fa un apprendistato non spetta "
                    "la deduzione supplementare «agli studi».".replace(",", "'"))
            if scelta in ("scuola", "universita"):
                opzioni_sede = ["stesso_comune", "stesso_cantone", "fuori_cantone"]
                etichette_sede = {
                    "stesso_comune": "Nel comune dove abito",
                    "stesso_cantone": "In Ticino, in un altro comune",
                    "fuori_cantone": "Fuori Cantone",
                }
                indice_sede = opzioni_sede.index(figlio.scuola_luogo) if figlio.scuola_luogo in opzioni_sede else None
                figlio.scuola_luogo = st.radio(
                    "Dov'è la sede della scuola?", opzioni_sede, index=indice_sede, horizontal=True,
                    format_func=lambda k: etichette_sede[k], key=f"figlio_sede_{i}",
                )
                figlio.alloggio_fuori_famiglia = not st.checkbox(
                    "Rientra ogni giorno a casa", value=not figlio.alloggio_fuori_famiglia, key=f"figlio_rientra_{i}",
                    help="Togli la spunta se alloggia fuori famiglia (per esempio in un appartamento o in collegio vicino alla sede).",
                )
                figlio.borsa_oltre_1000 = st.checkbox(
                    "Riceve borse di studio o sussidi (pubblici o privati) superiori a Fr. 1'000 l'anno",
                    value=figlio.borsa_oltre_1000, key=f"figlio_borsa_{i}",
                    help="Le borse fino a Fr. 1'000 l'anno non contano. Oltre, la deduzione si riduce in parte: la calcola l'Ufficio di tassazione.",
                )
                st.caption(
                    "Deve trattarsi di studi a tempo pieno, di almeno due semestri, senza retribuzione né indennità, "
                    "che rilasciano un titolo o preparano a un esame riconosciuto."
                )
                if figlio.borsa_oltre_1000:
                    st.warning(
                        "Con borse di studio superiori a Fr. 1'000 la deduzione «agli studi» va ridotta: non la scriviamo, "
                        "lasciamo il calcolo all'Ufficio di tassazione (indicalo nelle note e allega la decisione della borsa).")
                elif figlio.scuola_luogo is None:
                    st.warning("Indica dov'è la sede della scuola per calcolare la deduzione agli studi.")
                else:
                    st.success(
                        f"Deduzione supplementare agli studi: Fr. {deduzione_studi_figlio(dichiarazione, figlio):,}".replace(",", "'"))
        else:
            figlio.formazione, figlio.agli_studi = "", False


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("1. Dati anagrafici")

    c: Contribuente = dichiarazione.contribuente

    st.markdown("**Numero di registro (facoltativo)**")
    st.caption(
        "Si trova in alto nella prima pagina della dichiarazione di quest'anno, "
        "dell'anno scorso o di una qualsiasi decisione di tassazione: è sempre lo stesso ogni anno. "
        "Se lo inserisci, lo scriviamo in tutti i moduli."
    )
    dichiarazione.numero_controllo = st.text_input(
        "Numero di registro", value=dichiarazione.numero_controllo,
        max_chars=10, placeholder="es. 0001234567", label_visibility="collapsed",
    ).strip()
    if dichiarazione.numero_controllo and not dichiarazione.numero_controllo.isdigit():
        st.caption("⚠️ Il numero di registro è composto solo da cifre (di solito 10).")
    st.divider()

    _blocco_persona(c, "contrib", "Contribuente", dichiarazione.anno_fiscale)

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
        _blocco_persona(c.coniuge, "coniuge", "Coniuge / Partner registrato", dichiarazione.anno_fiscale)
    else:
        c.coniuge = None

    st.divider()
    st.subheader("Figli minorenni, a tirocinio o agli studi")
    st.caption(
        f"Si deducono Fr. {DEDUZIONE_FIGLIO_IC:,} per ogni figlio/a a carico: i minorenni (al 31.12.{dichiarazione.anno_fiscale} "
        "non hanno ancora 18 anni) e, fino al 28° anno di età, chi è a tirocinio o agli studi. Per la sostanza si deducono "
        f"Fr. {DEDUZIONE_FIGLIO_SOSTANZA:,} per ogni figlio minorenne.".replace(",", "'")
    )
    if st.button("+ Aggiungi figlio"):
        dichiarazione.figli.append(Figlio())
        st.rerun()

    for i, figlio in enumerate(dichiarazione.figli):
        _blocco_figlio(dichiarazione, figlio, i)

    st.divider()
    st.subheader("Persone bisognose a carico")
    st.caption(
        "Persone (non il coniuge né i figli già indicati sopra) che mantieni in modo essenziale e che non possono lavorare, "
        f"in tutto o in parte: la deduzione va dal costo del sostentamento — da Fr. {DEDUZIONE_PERSONA_BISOGNOSA_MIN:,} a "
        f"Fr. {DEDUZIONE_PERSONA_BISOGNOSA_MAX:,} l'anno — e va comprovata con i giustificativi. Per l'imposta cantonale "
        "conta solo chi risiede in Svizzera. Non valgono i familiari che vivono nella tua economia domestica o vi "
        "lavorano: sono considerati in grado di guadagnare.".replace(",", "'")
    )
    if st.button("+ Aggiungi una persona bisognosa"):
        dichiarazione.persone_bisognose.append(PersonaBisognosa())
        st.rerun()
    for i, pers in enumerate(dichiarazione.persone_bisognose):
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                pers.nome = st.text_input("Cognome e nome", value=pers.nome, key=f"pb_nome_{i}")
                pers.parentela = st.text_input("Rapporto di parentela", value=pers.parentela, key=f"pb_parentela_{i}",
                                               help="Es. madre, padre, figlio/a maggiorenne")
            with c2:
                pers.anno_nascita = int(st.number_input(
                    "Anno di nascita", min_value=1900, max_value=dichiarazione.anno_fiscale,
                    value=pers.anno_nascita or 1950, key=f"pb_anno_{i}"))
                pers.domicilio = st.text_input("Domicilio (comune o Paese)", value=pers.domicilio, key=f"pb_dom_{i}")
            pers.residente_svizzera = st.checkbox(
                "Risiede in Svizzera", value=pers.residente_svizzera, key=f"pb_ch_{i}",
                help="Per l'imposta cantonale la deduzione spetta solo per le persone bisognose residenti in Svizzera.",
            )
            campo_con_fallback(
                pers.onere_versato, "Quanto hai versato per il suo sostentamento nell'anno (Fr., comprovato)", key=f"pb_onere_{i}",
            )
            file_g = st.file_uploader("Giustificativi dei versamenti", type=["pdf", "png", "jpg", "jpeg"], key=f"pb_file_{i}")
            if file_g is not None:
                pers.file_giustificativi = file_g.name
            costo = numero(pers.onere_versato)
            if not pers.residente_svizzera:
                st.warning("Persona residente all'estero: per l'imposta cantonale la deduzione non spetta.")
            elif costo and costo < DEDUZIONE_PERSONA_BISOGNOSA_MIN:
                st.warning(
                    f"Sotto Fr. {DEDUZIONE_PERSONA_BISOGNOSA_MIN:,} l'anno non spetta nessuna deduzione.".replace(",", "'"))
            elif costo:
                st.success(f"Deduzione: Fr. {deduzione_persona_bisognosa(pers):,}".replace(",", "'")
                           + (f" (massimo Fr. {DEDUZIONE_PERSONA_BISOGNOSA_MAX:,})".replace(",", "'")
                              if costo > DEDUZIONE_PERSONA_BISOGNOSA_MAX else ""))
            if pers.file_giustificativi is None and costo:
                st.caption("📎 Alleghiamo le copie dei giustificativi alla dichiarazione.")
            if st.button("Rimuovi", key=f"pb_rm_{i}"):
                dichiarazione.persone_bisognose.pop(i)
                st.rerun()

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



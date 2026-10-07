"""
modules/altri_redditi_deduzioni.py — Modulo 1: tutto ciò che non viene da un certificato di salario,
da un conto o da un immobile.

Redditi (pagina 4): attività indipendente e amministratore, pensioni e rendite, indennità, alimenti
ricevuti, altri redditi. Deduzioni (pagina 5): riscatti di cassa pensione, alimenti e oneri permanenti,
disabilità, malattia e infortunio, formazione, partiti politici, liberalità. Deduzioni sociali (cifra 25):
quota esente per i beneficiari AVS/AI.

Le spiegazioni e i limiti sono quelli delle Istruzioni 2025 del Cantone Ticino (le pagine sono indicate
nei suggerimenti). Si compila solo ciò che riguarda il contribuente: chi non ha nulla da aggiungere
passa direttamente al passo successivo.
"""

import streamlit as st

from core.calcoli import (
    DIETA_FORFAIT, FRANCHIGIA_MALATTIA, LIBERALITA_MAX_PCT, LIBERALITA_MIN, MAX_FORMAZIONE, MAX_PARTITI, calcolo_malattia,
    calcolo_mod1, numero, plafond_terzo_pilastro,
)
from core.models import DichiarazioneFiscale, Liberalita, SpesaMalattia
from core.ui_helpers import campo_con_fallback

_CASI_PARTICOLARI = [
    "Prestazione in capitale della previdenza (2° pilastro o 3° pilastro A) ricevuta nel 2025",
    "Liquidazione in capitale al posto di prestazioni ricorrenti (cifra 7)",
    "Pensione del 2° pilastro iniziata prima del 1.1.2002 con rapporto di previdenza già esistente al 31.12.1986 (solo imposta federale)",
    "Reddito o sostanza imponibili all'estero (tabella in fondo alla pagina 4 del Modulo 1)",
    "Rientro settimanale al domicilio con alloggio e vitto vicino al lavoro (Modulo 4, cifra 4)",
    "Immobile in costruzione, ampliamento o ristrutturazione con carattere di miglioria (cifra 30.1)",
    "Partecipazione qualificata nella sostanza aziendale (Modulo 8.1)",
    "Investimento in una start-up innovativa (imposta separata dell'1%)",
    "Imposte superiori al 60% del reddito: richiesta del freno all'imposta sulla sostanza",
    "Inizio o fine dell'assoggettamento nel 2025 (arrivo o partenza dall'estero, decesso)",
    "Autodenuncia esente da pena di elementi non dichiarati in passato",
]


def _fr(x: float) -> str:
    return f"Fr. {x:,.0f}".replace(",", "'")


def _coppia(dich: DichiarazioneFiscale, etichetta: str, campo_c: str, campo_k: str, key: str, aiuto: str = None) -> None:
    """Un importo per il contribuente e, se c'è, uno per il coniuge/partner registrato."""
    a = dich.altri
    if dich.contribuente.richiede_dati_coniuge() and dich.contribuente.coniuge is not None:
        col1, col2 = st.columns(2)
        with col1:
            campo_con_fallback(getattr(a, campo_c), f"{etichetta} — contribuente", key=f"{key}_c", aiuto=aiuto)
        with col2:
            campo_con_fallback(getattr(a, campo_k), f"{etichetta} — coniuge/partner", key=f"{key}_k", aiuto=aiuto)
    else:
        campo_con_fallback(getattr(a, campo_c), etichetta, key=f"{key}_c", aiuto=aiuto)


def _singolo(dich: DichiarazioneFiscale, etichetta: str, campo: str, key: str, aiuto: str = None) -> None:
    campo_con_fallback(getattr(dich.altri, campo), etichetta, key=key, aiuto=aiuto)


def _sezione_redditi(dich: DichiarazioneFiscale) -> None:
    a = dich.altri
    st.subheader("Redditi")

    with st.expander("Attività indipendente e amministratore di una società"):
        st.caption(
            "Indica il risultato netto dell'esercizio chiuso nel 2025, preso dal conto economico (utile; se c'è una perdita "
            "scrivila con il segno meno, per esempio −12'000). Vanno allegati bilancio e conto economico firmati; i giustificativi "
            "si conservano per dieci anni. I contributi del 3° pilastro A non si deducono qui ma nel passo «Modulo 6»."
        )
        _coppia(dich, "Attività indipendente principale (Fr.)", "ind_principale_c", "ind_principale_k", "alt_ind_p",
                "Cifra 2.1. L'utile dopo le spese aziendali e professionali; senza imposte e spese private.")
        _coppia(dich, "Attività indipendente accessoria (Fr.)", "ind_accessoria_c", "ind_accessoria_k", "alt_ind_a",
                "Cifra 2.2. Vale anche per i redditi accessori da lavoro dipendente su cui non sono stati versati i contributi AVS/AI/LPP/IPG/AD.")
        _singolo(dich, "Perdite non compensate degli ultimi sette esercizi (Fr.)", "perdite_precedenti", "alt_perdite",
                 "Cifra 2, riquadro a sinistra: le perdite fiscalmente accertate e non ancora compensate degli esercizi dal 2018 al 2024. "
                 "Non si scrivono nella colonna dei redditi.")
        _singolo(dich, "Onorari, tantièmes, gettoni come amministratore di persone giuridiche (Fr.)", "amministratore", "alt_admin",
                 "Cifra 1.3. Al netto dei contributi AVS/AI/IPG/AINP.")
        _singolo(dich, "Quota di società in nome collettivo, in accomandita o semplici — contribuente (Fr.)", "snc_c", "alt_snc_c",
                 "Cifra 2.3. Dal Questionario per le società (Modulo 30) compilato dalla società.")
        if dich.contribuente.richiede_dati_coniuge():
            _singolo(dich, "Quota di società in nome collettivo, in accomandita o semplici — coniuge (Fr.)", "snc_k", "alt_snc_k")
        _singolo(dich, "Reddito da attività aziendale di comunioni ereditarie o comproprietà (Fr.)", "comunione_attivita", "alt_comunione",
                 "Cifra 2.4.")

    with st.expander("Pensioni, rendite e indennità"):
        st.caption(
            "Si dichiara sempre l'importo lordo effettivamente incassato nel 2025 (100%), ricavato dalle attestazioni. "
            "Non sono imponibili: prestazioni complementari AVS/AI, assegni per grandi invalidi, assegni familiari, "
            "indennità di ospedalizzazione e le prestazioni dell'assicurazione militare iniziate prima del 1.1.1994."
        )
        _coppia(dich, "Pensioni della previdenza professionale e 3° pilastro A (Fr.)", "pens_prev_c", "pens_prev_k", "alt_pens",
                "Cifra 3.1. Pensioni di 2° pilastro e di previdenza individuale vincolata, al lordo. Le prestazioni in capitale vanno "
                "invece indicate in fondo alla pagina 4 del Modulo 1 (vedi «Casi particolari»).")
        _coppia(dich, "Rendite AVS e AI (Fr.)", "avs_ai_c", "avs_ai_k", "alt_avs",
                "Cifra 3.2. Rendite di vecchiaia, vedovili, d'orfano e d'invalidità, per l'intero importo.")
        _coppia(dich, "Rendite vitalizie e altre rendite (Fr.)", "rendite_c", "rendite_k", "alt_rendite",
                "Cifra 3.3. SUVA, responsabilità civile, 3° pilastro B. Dal 2025 per le rendite vitalizie si indica la «Quota di "
                "reddito imponibile complessiva» del certificato dell'assicurazione (allegarne copia).")
        _coppia(dich, "Indennità di disoccupazione, perdita di guadagno (AI, militare) (Fr.)", "perdita_guadagno_c", "perdita_guadagno_k", "alt_idg",
                "Cifra 3.4. Solo se non sono già nel certificato di salario del datore di lavoro.")
        _coppia(dich, "Indennità giornaliere per malattia e infortuni (Fr.)", "giornaliere_c", "giornaliere_k", "alt_giorn",
                "Cifra 3.5. Le spese di malattia si deducono a parte, più sotto.")
        if numero(a.avs_ai_c) > 0 or numero(a.avs_ai_k) > 0:
            a.avs_ai_parziale = st.checkbox(
                "La rendita AVS/AI è parziale (per esempio un quarto o mezza rendita AI)",
                value=a.avs_ai_parziale, key="alt_avs_parziale",
                help="Con una rendita parziale la quota esente non può superare la rendita stessa.",
            )

    with st.expander("Alimenti ricevuti"):
        st.caption(
            "Gli alimenti che ricevi dal coniuge divorziato o separato (per te e per i figli minorenni sotto la tua autorità "
            "parentale) e quelli che un genitore, anche celibe o nubile, riceve per i figli minorenni sono imponibili. "
            "Quelli per figli maggiorenni non si dichiarano. La prima volta allega la sentenza di divorzio o la convenzione di separazione."
        )
        _singolo(dich, "Alimenti ricevuti per te (Fr.)", "alimenti_ricevuti_se", "alt_alim_se", "Cifra 3.6.")
        _singolo(dich, "Alimenti ricevuti per i figli minorenni (Fr.)", "alimenti_ricevuti_figli", "alt_alim_figli", "Cifra 3.6.")
        if numero(a.alimenti_ricevuti_se) or numero(a.alimenti_ricevuti_figli):
            a.alimenti_pagante = st.text_input(
                "Generalità e indirizzo di chi versa gli alimenti", value=a.alimenti_pagante, key="alt_alim_pagante",
            )

    with st.expander("Altri redditi"):
        st.caption("Anche i redditi da piattaforme digitali (Airbnb, Booking, Uber, eBay, YouTube, ecc.) sono imponibili.")
        _singolo(dich, "Altri redditi della sostanza mobiliare (Fr.)", "altri_mobiliare", "alt_mob",
                 "Cifra 4.2. Vantaggi in denaro ricevuti da una società di cui sei azionista o persona vicina (uso privato dell'auto, ecc.): "
                 "al 70% se detieni almeno il 10%, altrimenti al 100%.")
        _singolo(dich, "Altri redditi immobiliari: diritti di superficie, cave, diritti di abitazione (Fr.)", "altri_immobiliari", "alt_imm",
                 "Cifra 5.7. Allegare la distinta.")
        _singolo(dich, "Diritti d'autore, licenze, brevetti (Fr.)", "diritti_autore", "alt_autore", "Cifra 6.1.")
        _singolo(dich, "Vincite a giochi in denaro (Fr.)", "vincite", "alt_vincite",
                 "Cifra 6.2: si scrive nel riquadro e non si somma ai redditi (per l'imposta cantonale la vincita ha una tassazione separata). "
                 "Casinò in Svizzera, giochi di piccola estensione: esenti. Giochi di grande estensione: esente fino a Fr. 1'070'400 per vincita. "
                 "Per ogni vincita lorda sopra Fr. 1'100 allega l'attestazione in originale: sarà l'Ufficio a stabilire la parte imponibile.")
        _singolo(dich, "Ogni altro reddito imponibile (Fr.)", "altri_redditi", "alt_altri",
                 "Cifra 6.3: provvigioni, mance, indennità per cessazione di un'attività o rinuncia a un diritto, reddito netto da subaffitto "
                 "(affitto incassato meno affitto pagato), redditi da piattaforme digitali.")
        if numero(a.altri_redditi):
            a.altri_redditi_descrizione = st.text_input(
                "Di che genere di reddito si tratta?", value=a.altri_redditi_descrizione, key="alt_altri_descr",
            )


def _sezione_deduzioni(dich: DichiarazioneFiscale) -> None:
    a = dich.altri
    st.subheader("Deduzioni")

    with st.expander("Riscatti di anni di assicurazione nella cassa pensione (2° pilastro)"):
        st.caption(
            "Si deducono i versamenti (unici o rateali) di riscatto effettivamente pagati nel 2025, nei limiti della legge (art. 79b LPP). "
            "Vanno sempre documentati con l'attestazione della cassa pensione. I contributi ordinari del 2° pilastro sono già compresi "
            "nel salario netto del certificato di salario: non vanno inseriti qui."
        )
        _coppia(dich, "Riscatto 2° pilastro pagato nel 2025 (Fr.)", "riscatto_lpp_c", "riscatto_lpp_k", "alt_riscatto",
                "Cifra 10.3.")

    with st.expander("Alimenti versati, oneri permanenti, rendite vitalizie pagate"):
        st.caption(
            "Si deduce l'importo effettivamente versato, comprovato (la prima volta allega la sentenza o la convenzione). "
            "Non sono deducibili gli alimenti per i figli maggiorenni né le prestazioni dovute per l'obbligo di mantenimento "
            "o assistenza del diritto di famiglia a un genitore per i figli minorenni."
        )
        _singolo(dich, "Alimenti versati al coniuge divorziato o separato (Fr.)", "alimenti_coniuge", "alt_ded_alim_c", "Cifra 14.1.")
        _singolo(dich, "Alimenti versati a un genitore per figli minorenni sotto la sua autorità parentale (Fr.)", "alimenti_figli", "alt_ded_alim_f", "Cifra 14.2.")
        _singolo(dich, "Oneri permanenti a tuo carico (Fr.)", "oneri_permanenti", "alt_oneri", "Cifra 14.3.")
        _singolo(dich, "Rendite vitalizie pagate a terzi: quota di reddito imponibile presso il beneficiario (Fr.)", "rendite_pagate", "alt_rend_pag",
                 "Cifra 14.4. Dal 2025 si indica la «Quota di reddito complessiva» che risulta imponibile al beneficiario.")
        if any(numero(getattr(a, c)) for c in ("alimenti_coniuge", "alimenti_figli", "oneri_permanenti", "rendite_pagate")):
            a.beneficiari = st.text_input(
                "Generalità del/della beneficiario/a (e indirizzo)", value=a.beneficiari, key="alt_benef",
                help="Si scrive sul lato sinistro della pagina 5 del Modulo 1.",
            )

    with st.expander("Spese per disabilità"):
        st.caption(
            "Le spese direttamente legate alla disabilità tua o di una persona che mantieni, per la parte che resta a tuo carico "
            "(tolte tutte le partecipazioni pubbliche e private). Non sono deducibili il mantenimento ordinario (vitto, vestiti, "
            "alloggio, tempo libero) né le spese di lusso. Si compila anche il Modulo 6.1 (da www.ti.ch/fisco): allega certificato "
            "medico, assegno per grandi invalidi, fatture. Le spese di malattia della stessa persona vanno a parte, qui sotto."
        )
        _singolo(dich, "Spese per disabilità a tuo carico (Fr.)", "disabilita", "alt_disab", "Cifra 15.1, dal Modulo 6.1.")

    with st.expander("Spese di malattia e infortunio non rimborsate"):
        st.caption(
            "Si deduce la parte a tuo carico dopo cassa malati e assicurazioni (compresa la franchigia della cassa malati) che supera "
            f"il {FRANCHIGIA_MALATTIA * 100:.0f}% del reddito netto intermedio II. I premi della cassa malati NON sono spese di malattia: "
            "si deducono nel Modulo 6 (oneri assicurativi). Allega i giustificativi e i conteggi della cassa malati."
        )
        if st.button("+ Aggiungi una spesa", key="alt_mal_add"):
            a.spese_malattia.append(SpesaMalattia())
            st.rerun()
        for i, sp in enumerate(a.spese_malattia):
            with st.container(border=True):
                c1, c2, c3 = st.columns([1.3, 2, 1.2])
                with c1:
                    sp.data = st.date_input("Data del pagamento", value=sp.data, key=f"alt_mal_data_{i}", format="DD/MM/YYYY")
                with c2:
                    sp.beneficiario = st.text_input("Beneficiario (medico, ospedale, farmacia…)", value=sp.beneficiario, key=f"alt_mal_ben_{i}")
                with c3:
                    campo_con_fallback(sp.importo, "Importo a tuo carico (Fr.)", key=f"alt_mal_imp_{i}")
                if st.button("Rimuovi", key=f"alt_mal_rm_{i}"):
                    a.spese_malattia.pop(i)
                    st.rerun()
        a.dieta_forfait = st.checkbox(
            f"Celiachia o dieta permanente di necessità vitale: forfait di Fr. {DIETA_FORFAIT:,} (serve un certificato medico)".replace(",", "'"),
            value=a.dieta_forfait, key="alt_dieta",
            help="Per le persone diabetiche il forfait non è ammesso: si chiedono i costi effettivi.",
        )
        mal = calcolo_malattia(dich)
        if mal["totale"]:
            m1 = calcolo_mod1(dich)
            d = m1["deduzioni"]
            if d[612] > 0:
                st.success(
                    f"Spese di malattia {_fr(mal['totale'])} − franchigia del 5% ({_fr(d[244])}) = deduzione {_fr(d[612])}.")
            else:
                st.info(
                    f"Le spese ({_fr(mal['totale'])}) non superano la franchigia del 5% del reddito netto intermedio II "
                    f"({_fr(d[244])}): nessuna deduzione. Il calcolo si aggiorna con tutti gli altri dati.")

    with st.expander("Formazione e perfezionamento professionale"):
        st.caption(
            f"Si deducono le spese documentate di formazione e formazione continua professionali (comprese le riqualificazioni), fino a "
            f"{_fr(MAX_FORMAZIONE)} per persona, se hai già un diploma del livello secondario II (liceo, scuola specializzata, "
            "formazione professionale di base) oppure hai compiuto 20 anni e le spese non servono a ottenere un primo diploma del "
            "livello secondario II. Le spese della prima formazione non sono deducibili. Se hai ricevuto contributi dalla SEFRI per i "
            "corsi preparatori agli esami federali, vanno dichiarati come altro reddito (cifra 6.3)."
        )
        _coppia(dich, "Spese di formazione professionale (Fr.)", "formazione_c", "formazione_k", "alt_formaz", "Cifre 15.3 e 15.4.")

    with st.expander("Versamenti a partiti politici"):
        st.caption(
            f"Contributi a partiti iscritti nel registro federale dei partiti e rappresentati in un parlamento cantonale, "
            f"o che hanno ottenuto almeno il 3% dei voti nell'ultima elezione: fino a {_fr(MAX_PARTITI)}. "
            "I due coniugi sommano gli importi. Allega le ricevute."
        )
        _singolo(dich, "Versamenti a partiti politici (Fr.)", "partiti", "alt_partiti", "Cifra 15.2.")

    with st.expander("Liberalità a enti di pubblica utilità"):
        st.caption(
            f"Prestazioni volontarie in denaro o in beni a enti esenti da imposta per il loro scopo pubblico o di utilità pubblica "
            f"(con sede in Svizzera), alla Confederazione, ai Cantoni, ai Comuni e alle parrocchie. Si deducono se in tutto sono almeno "
            f"{_fr(LIBERALITA_MIN)} l'anno, fino al {LIBERALITA_MAX_PCT * 100:.0f}% del reddito netto intermedio III. Non contano le "
            "donazioni a privati. Elenca ogni versamento con data ed ente e allega le ricevute."
        )
        if st.button("+ Aggiungi una liberalità", key="alt_lib_add"):
            a.liberalita.append(Liberalita())
            st.rerun()
        for i, lib in enumerate(a.liberalita):
            with st.container(border=True):
                c1, c2, c3 = st.columns([1.3, 2, 1.2])
                with c1:
                    lib.data = st.date_input("Data", value=lib.data, key=f"alt_lib_data_{i}", format="DD/MM/YYYY")
                with c2:
                    lib.ente = st.text_input("Ente beneficiario", value=lib.ente, key=f"alt_lib_ente_{i}")
                with c3:
                    campo_con_fallback(lib.importo, "Importo (Fr.)", key=f"alt_lib_imp_{i}")
                if st.button("Rimuovi", key=f"alt_lib_rm_{i}"):
                    a.liberalita.pop(i)
                    st.rerun()


def _riepilogo_effetti(dich: DichiarazioneFiscale) -> None:
    """Messaggi sui limiti: compaiono solo se un importo inserito supera il massimo ammesso."""
    m1 = calcolo_mod1(dich)
    info, d = m1["info"], m1["deduzioni"]
    messaggi = []
    if info["partiti_oltre_tetto"]:
        messaggi.append(f"Versamenti ai partiti: si deduce al massimo {_fr(MAX_PARTITI)} (eccedenza {_fr(info['partiti_oltre_tetto'])}).")
    if info["formazione_oltre_tetto"]:
        messaggi.append(f"Formazione professionale: si deduce al massimo {_fr(MAX_FORMAZIONE)} per persona.")
    if info["liberalita_sotto_minimo"]:
        messaggi.append(f"Liberalità: sotto {_fr(LIBERALITA_MIN)} in tutto non sono deducibili.")
    if info["liberalita_oltre_tetto"] > 0:
        messaggi.append(
            f"Liberalità: si deduce al massimo il 20% del reddito netto intermedio III ({_fr(d[510])}). Per deduzioni superiori "
            "(fino al 50%) bisogna rivolgersi alla Divisione delle contribuzioni.")
    if info["beneficiario_avs"]:
        if d[260]:
            messaggi.append(f"Quota esente per beneficiari AVS/AI (cifra 27): {_fr(d[260])}, calcolata sul reddito netto di {_fr(d[256])}.")
        else:
            messaggi.append("Quota esente per beneficiari AVS/AI: con questo reddito netto non spetta (si azzera sopra Fr. 42'000 per persone sole, "
                            "Fr. 48'000 per coniugati o con figli o persone bisognose a carico).")
        if dich.contribuente.richiede_dati_coniuge() and numero(dich.altri.avs_ai_c) > 0 and numero(dich.altri.avs_ai_k) > 0:
            messaggi.append("Entrambi i coniugi percepiscono una rendita: il programma applica una sola quota esente per la famiglia; "
                            "l'Ufficio di tassazione verifica.")
    for t in messaggi:
        st.info(t)


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Altri redditi e deduzioni")
    st.info(
        "Qui trovi tutto ciò che non è già nei passi precedenti: attività indipendente, pensioni e rendite, alimenti, spese di "
        "malattia, formazione, liberalità e così via. **Apri solo le voci che ti riguardano**; se non hai nulla da aggiungere "
        "premi «Avanti». Le regole sono quelle delle Istruzioni 2025 del Cantone Ticino."
    )
    _sezione_redditi(dichiarazione)
    st.divider()
    _sezione_deduzioni(dichiarazione)
    st.divider()

    st.subheader("Situazioni particolari")
    st.caption(
        "Alcuni casi non vengono compilati dal programma: spuntali se ti riguardano, così li ritrovi tra le «Verifiche» del riepilogo "
        "e non si dimenticano."
    )
    a = dichiarazione.altri
    a.casi_particolari = st.multiselect(
        "Mi riguarda:", options=_CASI_PARTICOLARI, default=[x for x in a.casi_particolari if x in _CASI_PARTICOLARI],
        key="alt_casi", placeholder="Scegli i casi che ti riguardano",
    )
    st.divider()
    _riepilogo_effetti(dichiarazione)
    p3 = [("contribuente", "contribuente")] + ([("coniuge", "coniuge")] if dichiarazione.contribuente.coniuge else [])
    for persona, nome in p3:
        versato = dichiarazione.terzo_pilastro_versato if persona == "contribuente" else dichiarazione.terzo_pilastro_coniuge_versato
        importo = dichiarazione.terzo_pilastro_importo if persona == "contribuente" else dichiarazione.terzo_pilastro_coniuge_importo
        massimo = plafond_terzo_pilastro(dichiarazione, persona)
        if versato and numero(importo) > massimo:
            st.warning(
                f"3° pilastro A ({nome}): hai versato {_fr(numero(importo))} ma il massimo deducibile è {_fr(massimo)} "
                "(Fr. 7'258 con cassa pensione; senza, il 20% del reddito da attività lucrativa, al massimo Fr. 36'288). "
                "L'eccedenza non si deduce."
            )

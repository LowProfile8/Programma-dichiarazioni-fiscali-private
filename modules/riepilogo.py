"""modules/riepilogo.py — riepilogo, controlli di completezza e un unico
scarico con tutta la dichiarazione (tutti i moduli applicabili uniti in
un solo PDF, nell'ordine ufficiale)."""

import streamlit as st

from core import state
from core.calcoli import calcolo_mod1, calcolo_mod2, numero
from core.dispendio import calcola_dispendio
from core.dispendio_pdf import genera_pdf_dispendio
from core.models import DichiarazioneFiscale
from core.overlay_moduli import genera_dichiarazione_completa


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Riepilogo")

    c = dichiarazione.contribuente
    col_riepilogo, col_controllo = st.columns([3, 2], gap="large")
    with col_riepilogo:
        st.write(f"**Contribuente:** {c.nome} {c.cognome}")
        if c.stato_civile:
            st.write(f"**Stato civile:** {c.stato_civile.value}")
        if c.coniuge:
            st.write(f"**Coniuge:** {c.coniuge.nome} {c.coniuge.cognome}")
        st.write(f"**Figli:** {len(dichiarazione.figli)}")
        st.write(f"**Certificati di salario:** {len(dichiarazione.certificati_salario)}")
        st.write(f"**Conti correnti:** {len(dichiarazione.conti_correnti)}")
        st.write(f"**Titoli/investimenti:** {len(dichiarazione.titoli_investimenti)}")
        st.write(f"**Debiti:** {len(dichiarazione.debiti)}")
        st.write(f"**Immobili:** {len(dichiarazione.immobili)}")
        st.write(f"**Veicoli e natanti:** {len(dichiarazione.veicoli)}")
        st.write(f"**Partecipazioni qualificate:** {len(dichiarazione.partecipazioni)}")
    with col_controllo:
        # Casella discreta: vuota se non è stato inserito prima; si può compilare anche ora
        with st.container(border=True):
            st.markdown("**Numero di registro**")
            dichiarazione.numero_controllo = st.text_input(
                "Numero di registro", value=dichiarazione.numero_controllo, max_chars=10,
                placeholder="0001234567", label_visibility="collapsed",
                help="Si trova in alto nella prima pagina della dichiarazione di quest'anno, "
                     "dell'anno scorso o di una decisione di tassazione: è sempre lo stesso.",
            ).strip()
            if dichiarazione.numero_controllo and not dichiarazione.numero_controllo.isdigit():
                st.caption("Solo cifre (di solito 10).")
            else:
                st.caption("Facoltativo · in alto nella prima pagina di una decisione di tassazione")
            dichiarazione.contribuente.ufficio_tassazione = st.text_input(
                "Ufficio di tassazione (facoltativo)", value=dichiarazione.contribuente.ufficio_tassazione,
                max_chars=6, placeholder="es. UT 2",
                help="Il codice «UT n» stampato accanto al Comune in alto nella prima pagina di una "
                     "dichiarazione precedente: cambia da comune a comune, lo conosci di solito già "
                     "seguendo quel cliente.",
            ).strip()

    # ── Controlli di completezza: valori FONDAMENTALI mancanti ──────────
    avvisi_fondamentali = []
    if not c.nome:
        avvisi_fondamentali.append("Nome del contribuente non inserito.")
    if not c.cognome:
        avvisi_fondamentali.append("Cognome del contribuente non inserito.")
    if not c.data_nascita:
        avvisi_fondamentali.append("Data di nascita del contribuente non inserita.")
    if not c.stato_civile:
        avvisi_fondamentali.append("Stato civile del contribuente non inserito.")

    ha_reddito = any(
        cert.cifra_11_salario_netto.valore for cert in dichiarazione.certificati_salario
    )
    if not ha_reddito:
        avvisi_fondamentali.append(
            "Nessun reddito netto inserito (cifra 11 del certificato di salario) — "
            "manca un dato fondamentale della dichiarazione."
        )

    if not dichiarazione.conti_correnti:
        avvisi_fondamentali.append("Nessun conto corrente inserito — va indicato almeno un conto (anche a saldo zero).")

    if c.richiede_dati_coniuge() and c.coniuge and not (c.coniuge.nome and c.coniuge.cognome):
        avvisi_fondamentali.append("Hai indicato coniugato/a, ma i dati del coniuge non sono completi.")
    for imm in dichiarazione.immobili:
        if not imm.piena_proprieta and not imm.intestazione_registro_fondiario.strip():
            avvisi_fondamentali.append(
                f"Immobile ({imm.comune.valore or 'senza comune'}) in comproprietà — manca l'intestazione esatta a registro fondiario."
            )

    if avvisi_fondamentali:
        st.error(
            "⚠️ **Valori fondamentali mancanti** — completali prima di considerare la dichiarazione pronta:\n\n"
            + "\n".join(f"- {a}" for a in avvisi_fondamentali)
        )

    # ── Allegati mancanti: un valore c'è, il file no ─────────────────────
    allegati_mancanti = []
    for cert in dichiarazione.certificati_salario:
        if cert.cifra_11_salario_netto.valore and not cert.file_origine:
            allegati_mancanti.append(f"Certificato di salario ({cert.datore_lavoro.valore or 'senza nome'}) — manca il certificato allegato")
    for conto in dichiarazione.conti_correnti:
        if conto.saldo_valore_31_12.valore and not conto.file_origine:
            allegati_mancanti.append(f"Conto corrente ({conto.istituto.valore or 'senza nome'}) — manca l'attestato fiscale")
    for titolo in dichiarazione.titoli_investimenti:
        if titolo.saldo_valore_31_12.valore and not titolo.file_origine:
            allegati_mancanti.append(f"Titolo ({titolo.istituto.valore or 'senza nome'}) — manca l'attestato fiscale")
    for imm in dichiarazione.immobili:
        if imm.valore_stima_totale.valore and not imm.file_origine:
            allegati_mancanti.append(f"Immobile ({imm.comune.valore or 'senza comune'}) — manca la scheda di stima ufficiale")
    for deb in dichiarazione.debiti:
        if deb.tipo in ("ipoteca", "finanziamento") and deb.saldo_31_12.valore and not deb.file_origine:
            allegati_mancanti.append(f"Debito ({deb.creditore.valore or 'senza nome'}) — manca l'attestato fiscale")
    for part in dichiarazione.partecipazioni:
        if part.capitale_sociale.valore and not part.file_origine:
            allegati_mancanti.append(f"Partecipazione ({part.denominazione.valore or 'senza nome'}) — manca l'estratto del registro di commercio")
    for cm in dichiarazione.cassa_malati:
        if cm.importo_annuo.valore and not cm.file_origine:
            allegati_mancanti.append(f"Cassa malati ({cm.persona}) — manca il certificato di fine anno")
    if dichiarazione.terzo_pilastro_versato and dichiarazione.terzo_pilastro_importo.valore and not dichiarazione.terzo_pilastro_file:
        allegati_mancanti.append("3° pilastro A — manca l'attestato dei versamenti")
    for figlio in dichiarazione.figli:
        if figlio.in_cura_da_terzi and figlio.spese_cura_annuali.valore and not figlio.file_fatture_cura:
            allegati_mancanti.append(f"Cura da terzi per {figlio.nome} — mancano le fatture")

    if allegati_mancanti:
        st.warning(
            "📎 **Allegati mancanti** — hai inserito un valore ma non hai caricato il documento corrispondente:\n\n"
            + "\n".join(f"- {a}" for a in allegati_mancanti)
        )

    # ── Domande rimaste senza risposta ───────────────────────────────────
    senza_risposta = []
    for pos in list(dichiarazione.conti_correnti) + list(dichiarazione.titoli_investimenti):
        if numero(pos.interessi_redditi) > 0 and pos.interessi_soggetti_ip is None:
            senza_risposta.append(
                f"{pos.istituto.valore or 'Conto/titolo senza nome'} — gli interessi sono soggetti a imposta preventiva? "
                "(la risposta è sull'attestato)"
            )
    if senza_risposta:
        st.warning("❓ **Domande senza risposta:**\n\n" + "\n".join(f"- {a}" for a in senza_risposta))

    # ── Valori principali calcolati + confronto con l'anno scorso ────────
    m1 = calcolo_mod1(dichiarazione)
    st.divider()
    st.subheader("Valori principali")
    fr = lambda x: f"Fr. {x:,.0f}".replace(",", "'")
    r1a, r1b = st.columns(2)
    r1a.metric("Totale dei redditi", fr(m1["redditi"][178]))
    r1b.metric("Reddito imponibile", fr(m1["deduzioni"][264]))
    r2a, r2b = st.columns(2)
    r2a.metric("Sostanza imponibile", fr(m1["sostanza"][340]))
    r2b.metric("Imposta preventiva da recuperare", f"Fr. {m1['recupero_ip']:,.2f}".replace(",", "'"))
    st.caption("L'imposta preventiva è la somma del 35% degli interessi e dei dividendi lordi: è il credito d'imposta scritto in basso a destra della prima pagina del Modulo 1.")

    sostanza_prec = numero(dichiarazione.sostanza_titoli_anno_precedente)
    if sostanza_prec > 0:
        sostanza_att = calcolo_mod2(dichiarazione)["tot_sostanza"]
        variazione = (sostanza_att - sostanza_prec) / sostanza_prec * 100
        st.metric(
            "Sostanza in titoli e conti: quest'anno rispetto all'anno scorso", fr(sostanza_att),
            delta=f"{variazione:+.1f}% (anno scorso: {fr(sostanza_prec)})",
        )
        if abs(variazione) >= 30:
            st.warning("La sostanza in titoli e conti è cambiata di molto rispetto all'anno scorso: controlla di averli inseriti tutti.")

    partecipazioni_fuori_scope = [p for p in dichiarazione.partecipazioni if not p.detenuta_privatamente]
    if partecipazioni_fuori_scope:
        st.error(
            f"⚠️ {len(partecipazioni_fuori_scope)} partecipazione/i detenuta/e come attivo di ditta individuale "
            "(Modulo 8.1) — fuori scope v1, da gestire manualmente."
        )

    st.divider()
    with st.expander("Verifiche prima di spedire (controllate sulle Istruzioni 2025 del Cantone)", expanded=True):
        st.caption(
            "Importi e regole verificati sulla «Tabella deduzioni 2025» e sulle Istruzioni del Cantone Ticino. "
            "Il programma compila i moduli con i valori che hai inserito; il calcolo definitivo spetta all'Ufficio di tassazione."
        )
        avvisi = []
        principali = [c for c in dichiarazione.certificati_salario if c.tipo_attivita == "principale"]
        if any(c.mezzo_trasporto == "auto" for c in principali):
            avvisi.append(
                "**Trasporti con veicolo privato.** Per l'imposta cantonale i km (auto Fr. 0.60, moto con targa bianca "
                "Fr. 0.40) si deducono solo se non hai un mezzo pubblico utilizzabile; altrimenti vale il costo del mezzo pubblico. "
                "Il tragitto di mezzogiorno non può superare la deduzione per i pasti (Fr. 15 al giorno, max Fr. 3'200)."
            )
        if any((c.grado_occupazione or 100) < 50 for c in principali):
            avvisi.append("**Occupazione sotto il 50%:** il forfait per altre spese professionali è ridotto a Fr. 1'500.")
        if any(c.tipo_attivita == "accessoria" for c in dichiarazione.certificati_salario):
            avvisi.append("**Attività accessoria:** forfait Fr. 800 al posto delle spese professionali, oppure le spese effettive documentate.")
        m1 = calcolo_mod1(dichiarazione)
        info = m1["info"]
        fr = lambda x: f"Fr. {x:,.0f}".replace(",", "'")
        if info["interessi_oltre_tetto"] > 0:
            avvisi.append(
                f"**Interessi passivi privati:** si deducono al massimo il reddito lordo della sostanza (cifre 4 e 5) più Fr. 50'000, "
                f"cioè {fr(info['tetto_interessi'])}. Gli interessi inseriti ({fr(info['interessi_privati'])}) lo superano: "
                f"l'eccedenza di {fr(info['interessi_oltre_tetto'])} non si deduce."
            )
        if info["partiti_oltre_tetto"] > 0:
            avvisi.append("**Partiti politici:** la deduzione è limitata a Fr. 10'600.")
        if info["formazione_oltre_tetto"] > 0:
            avvisi.append("**Formazione professionale:** la deduzione è limitata a Fr. 10'700 per persona.")
        if info["liberalita_sotto_minimo"]:
            avvisi.append("**Liberalità:** sotto Fr. 100 in totale non sono deducibili.")
        if info["liberalita_oltre_tetto"] > 0:
            avvisi.append("**Liberalità:** si deduce al massimo il 20% del reddito netto intermedio III.")
        if any(f.borsa_oltre_1000 for f in dichiarazione.figli):
            avvisi.append(
                "**Borse di studio superiori a Fr. 1'000:** la deduzione per figli agli studi è ridotta; il programma indica l'importo pieno "
                "e il calcolo della parte ammessa spetta all'Ufficio di tassazione. Allega il documento della borsa."
            )
        if dichiarazione.altri.spese_malattia and m1["deduzioni"][612] == 0:
            avvisi.append("**Spese di malattia:** non superano il 5% del reddito netto, quindi non danno diritto a deduzione.")
        if info["beneficiario_avs"]:
            avvisi.append("**Rendite AVS/AI:** la quota esente (cifra 27) è calcolata automaticamente in base al reddito netto.")
        for caso in dichiarazione.altri.casi_particolari:
            avvisi.append(f"**Situazione particolare non compilata dal programma:** {caso}. Compila a mano la parte relativa sul modulo oppure scrivilo nelle note.")
        avvisi += [
            "**Cura dei figli da terzi** (figli sotto i 14 anni, max Fr. 26'200) e **doppio reddito** (coniugati con due redditi, "
            "Fr. 8'100 al massimo): calcolati dal programma sulla base dei dati inseriti; ricontrolla le cifre sul Modulo 6 e sul Modulo 1.",
            "**Imposta federale diretta:** alcuni limiti sono diversi da quelli cantonali (es. figli Fr. 6'800, assicurazioni "
            "Fr. 3'700/1'800, spese professionali 3% dello stipendio). Sui moduli indichi gli importi effettivi: i limiti li applica l'Ufficio.",
            "**Dati importati dall'anno scorso:** il Cantone raccomanda di ricontrollarli sempre, uno per uno.",
        ]
        for a in avvisi:
            st.markdown(f"- {a}")

    st.divider()
    st.subheader("Note per l'Ufficio di tassazione")
    st.caption("Facoltativo — qualsiasi comunicazione libera che vuoi allegare alla dichiarazione (es. spiegazioni su una situazione particolare).")
    dichiarazione.note_ufficio_tassazione = st.text_area(
        "Testo della comunicazione", value=dichiarazione.note_ufficio_tassazione, height=120,
        label_visibility="collapsed",
    )

    st.divider()
    st.subheader("Scarica la dichiarazione completa")
    st.caption(
        "Un solo PDF per la **stampa cartacea**, che parte direttamente dal Modulo 1 (4 pagine, sempre incluso) e "
        "prosegue con i Moduli 2, 4, 5, 6, 7 (2 pagine per ogni immobile), 8 e la pagina delle note. "
        "I moduli 2-8 sono i fogli ufficiali del Cantone, identici a quelli scaricabili dal sito; solo le pagine "
        "«personali» (Modulo 1, allegati, note) portano codici, nome e numero di registro come nelle stampe eTax. "
        "I moduli per cui non hai inserito nulla non vengono inclusi (non vanno inviati)."
    )

    if st.button("Genera la dichiarazione completa", type="primary"):
        with st.spinner("Genero tutti i moduli..."):
            st.session_state["pdf_completo_bytes"] = genera_dichiarazione_completa(dichiarazione)
        st.success("Dichiarazione generata.")

    if "pdf_completo_bytes" in st.session_state:
        st.download_button(
            "Scarica la dichiarazione (PDF unico)",
            data=st.session_state["pdf_completo_bytes"],
            file_name=f"Dichiarazione_imposta_{dichiarazione.anno_fiscale}.pdf",
            mime="application/pdf",
        )

    with st.expander("Versione completa «stile stampa online di eTax» (con pagina riassuntiva, data e ora)"):
        st.caption(
            "Uguale alla stampa che esce dal programma online del Cantone: pagina riassuntiva iniziale, data e ora di "
            "stampa, numeri di pagina e codici su ogni pagina. Non contiene i tre grandi codici a barre 2D (cifrati dal "
            "Cantone: non è possibile riprodurli): per la spedizione cartacea usa il PDF qui sopra."
        )
        if st.button("Genera la versione stile eTax online"):
            st.session_state["pdf_online_bytes"] = genera_dichiarazione_completa(dichiarazione, stile_online=True)
        if "pdf_online_bytes" in st.session_state:
            st.download_button(
                "Scarica (stile eTax online)", data=st.session_state["pdf_online_bytes"],
                file_name=f"Dichiarazione_imposta_{dichiarazione.anno_fiscale}_stile_online.pdf",
                mime="application/pdf", key="scarica_online",
            )

    # ── Calcolo del dispendio (file a parte, non fa parte della dichiarazione) ──
    st.divider()
    st.subheader("Calcolo del dispendio")
    st.caption(
        "Verifica che il risparmio generato nell'anno (redditi meno spese e deduzioni) spieghi la crescita di conti e "
        "titoli rispetto all'anno scorso. Si scarica in un file a parte: non va allegato alla dichiarazione."
    )
    campo_prec = dichiarazione.sostanza_titoli_anno_precedente
    prec = st.text_input(
        "Somma di titoli e conti dell'anno scorso (Fr.)", value=campo_prec.valore or "",
        help="Modulo 2 della dichiarazione dell'anno scorso: riga «Totale», colonna «Sostanza».",
    )
    if prec != (campo_prec.valore or ""):
        campo_prec.valore, campo_prec.origine = prec, "utente"
    campo_altre = dichiarazione.dispendio_altre_spese
    altre = st.text_input(
        "Altre spese dell'anno non già presenti nella dichiarazione (facoltativo, Fr.)",
        value=campo_altre.valore or "", help="Per esempio le imposte pagate o le spese di vita: riducono il risparmio generato.",
    )
    if altre != (campo_altre.valore or ""):
        campo_altre.valore, campo_altre.origine = altre, "utente"

    if st.button("Calcola il dispendio", key="calcola_dispendio"):
        st.session_state["dispendio_mostra"] = True
    if st.session_state.get("dispendio_mostra"):
        r = calcola_dispendio(dichiarazione)
        fr = lambda x: f"Fr. {x:,.0f}".replace(",", "'")
        if not r["calcolabile"]:
            st.warning("Per confrontare la liquidità serve la somma di titoli e conti dell'anno scorso: indicala qui sopra.")
        else:
            m1c, m2c = st.columns(2)
            m1c.metric("Redditi", fr(r["totale_redditi"]))
            m2c.metric("Spese e deduzioni", fr(r["totale_spese"]))
            m3c, m4c = st.columns(2)
            m3c.metric("Risparmio generato", fr(r["risparmio"]))
            m4c.metric("Variazione della liquidità", fr(r["variazione"]))
            if r["coerente"]:
                st.success(
                    "**Il calcolo è corretto.** Le spese sono state coerenti con i redditi: la variazione della liquidità "
                    f"({fr(r['variazione'])}) rientra nella crescita spiegabile ({fr(r['crescita_spiegabile'])}). "
                    f"Margine: {fr(r['risultato'])}."
                )
            else:
                st.warning(
                    "**Attenzione: le spese sono state troppo alte rispetto ai redditi.** La liquidità è cresciuta di "
                    f"{fr(r['variazione'])}, più di quanto il risparmio generato consenta ({fr(r['crescita_spiegabile'])}): "
                    f"differenza da spiegare {fr(-r['risultato'])}. La dichiarazione è da verificare nuovamente sulla base "
                    "del cash flow privato effettivamente avvenuto."
                )
        with st.expander("Dettaglio del calcolo"):
            for titolo, voci in (("Redditi", r["redditi"]), ("Spese e deduzioni", r["spese"]), ("Altri movimenti di capitale", r["movimenti"])):
                if voci:
                    st.markdown(f"**{titolo}**")
                    st.markdown("\n".join(f"- {v['voce']}: {fr(v['importo'])}" for v in voci))
            if r["valore_locativo"]:
                st.caption(f"Valore locativo {fr(r['valore_locativo'])}: reddito figurativo, non conteggiato.")
        st.download_button(
            "Scarica il calcolo del dispendio (PDF)", data=genera_pdf_dispendio(dichiarazione),
            file_name=f"Calcolo_dispendio_{dichiarazione.contribuente.cognome or 'cliente'}_{dichiarazione.anno_fiscale}.pdf".replace(" ", "_"),
            mime="application/pdf", key="scarica_dispendio",
        )



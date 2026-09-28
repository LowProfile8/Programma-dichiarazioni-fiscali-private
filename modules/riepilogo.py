"""modules/riepilogo.py — riepilogo, controlli di completezza e un unico
scarico con tutta la dichiarazione (tutti i moduli applicabili uniti in
un solo PDF, nell'ordine ufficiale)."""

import streamlit as st

from core import state
from core.calcoli import calcolo_mod1, calcolo_mod2, numero
from core.models import DichiarazioneFiscale
from core.overlay_moduli import genera_dichiarazione_completa


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Riepilogo")

    c = dichiarazione.contribuente
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
    st.write(f"**Partecipazioni qualificate:** {len(dichiarazione.partecipazioni)}")

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
    c1, c2, c3, c4 = st.columns(4)
    fr = lambda x: f"Fr. {x:,.0f}".replace(",", "'")
    c1.metric("Totale dei redditi", fr(m1["redditi"][178]))
    c2.metric("Reddito imponibile", fr(m1["deduzioni"][264]))
    c3.metric("Sostanza imponibile", fr(m1["sostanza"][340]))
    c4.metric("Imposta preventiva da recuperare", f"Fr. {m1['recupero_ip']:,.2f}".replace(",", "'"))

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
    st.subheader("Numero di controllo (facoltativo)")
    st.caption(
        "È il «Numero registro» che si trova in alto nella prima pagina della dichiarazione di quest'anno, "
        "dell'anno scorso o di una qualsiasi decisione di tassazione: è sempre lo stesso ogni anno. "
        "Se lo inserisci, lo scriviamo in tutti i moduli; altrimenti lo aggiungi a mano."
    )
    dichiarazione.numero_controllo = st.text_input(
        "Numero di controllo", value=dichiarazione.numero_controllo, key="numero_controllo", max_chars=10,
        placeholder="es. 0001234567", label_visibility="collapsed",
    ).strip()
    if dichiarazione.numero_controllo and not dichiarazione.numero_controllo.isdigit():
        st.caption("⚠️ Il numero di controllo è composto solo da cifre (di solito 10).")

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
        "Un solo PDF con i moduli ufficiali compilati, nell'ordine corretto: Modulo 1 (4 pagine, sempre incluso), "
        "Modulo 2, 4, 5, 6, 7 (2 pagine per ogni immobile), 8 e la pagina delle note. "
        "I moduli per cui non hai inserito nulla non vengono inclusi (non vanno inviati)."
    )

    if st.button("📄 Genera la dichiarazione completa", type="primary"):
        with st.spinner("Genero tutti i moduli..."):
            st.session_state["pdf_completo_bytes"] = genera_dichiarazione_completa(dichiarazione)
        st.success("Dichiarazione generata.")

    if "pdf_completo_bytes" in st.session_state:
        st.download_button(
            "⬇️ Scarica la dichiarazione (PDF unico)",
            data=st.session_state["pdf_completo_bytes"],
            file_name=f"Dichiarazione_fiscale_{dichiarazione.anno_fiscale}.pdf",
            mime="application/pdf",
        )

    st.divider()
    if st.button("← Indietro"):
        state.go_back()
        st.rerun()

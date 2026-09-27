"""modules/riepilogo.py — riepilogo, controlli di completezza e scarico PDF."""

import streamlit as st

from core import state
from core.models import DichiarazioneFiscale
from core.output_generator import genera_pdf_riepilogo
from core.overlay_moduli import (
    genera_modulo1_sovrapposto,
    genera_modulo2_sovrapposto,
    genera_modulo4_sovrapposto,
    genera_modulo5_sovrapposto,
    genera_modulo6_sovrapposto,
    genera_modulo7_sovrapposto,
    genera_modulo8_sovrapposto,
)


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
    st.write(f"**Immobili:** {len(dichiarazione.immobili)}")
    st.write(f"**Partecipazioni qualificate:** {len(dichiarazione.partecipazioni)}")

    # ── Controlli di completezza: valori FONDAMENTALI mancanti ──────────
    avvisi_fondamentali = []
    ha_reddito = any(
        cert.cifra_11_salario_netto.valore for cert in dichiarazione.certificati_salario
    )
    if not ha_reddito:
        avvisi_fondamentali.append(
            "Nessun reddito da attività dipendente inserito (cifra 11 del certificato di salario) — "
            "manca un dato fondamentale della dichiarazione."
        )
    if not c.cognome or not c.nome:
        avvisi_fondamentali.append("Nome o cognome del contribuente non inseriti.")
    if c.richiede_dati_coniuge() and c.coniuge and not (c.coniuge.nome and c.coniuge.cognome):
        avvisi_fondamentali.append("Hai indicato coniugato/a, ma i dati del coniuge non sono completi.")

    if avvisi_fondamentali:
        st.error(
            "⚠️ **Valori fondamentali mancanti** — completali prima di considerare la dichiarazione pronta:\n\n"
            + "\n".join(f"- {a}" for a in avvisi_fondamentali)
        )

    # ── Valori presi dall'anno precedente, ancora da rivalutare ─────────
    campi_da_rivedere = []

    def _controlla(oggetto, nomi_campi, etichetta):
        for nome_campo in nomi_campi:
            campo = getattr(oggetto, nome_campo, None)
            if campo is not None and getattr(campo, "da_rivedere", False):
                campi_da_rivedere.append(f"{etichetta} — {nome_campo}")

    for cert in dichiarazione.certificati_salario:
        _controlla(cert, ["datore_lavoro", "cifra_10_contributi_lpp", "cifra_11_salario_netto"], "Certificato di salario")
    for conto in dichiarazione.conti_correnti:
        _controlla(conto, ["istituto", "iban_numero_conto", "saldo_valore_31_12", "interessi_redditi"], "Conto corrente")
    for titolo in dichiarazione.titoli_investimenti:
        _controlla(titolo, ["istituto", "iban_numero_conto", "saldo_valore_31_12", "interessi_redditi", "quantita_nominale"], "Titolo")
    for imm in dichiarazione.immobili:
        _controlla(imm, ["comune", "indirizzo", "valore_stima_totale", "valore_di_reddito", "affitti_incassati"], "Immobile")
    for p in dichiarazione.partecipazioni:
        _controlla(p, ["denominazione", "capitale_sociale", "dividendi_lordo_totale"], "Partecipazione")

    if campi_da_rivedere:
        st.warning(
            "⚠️ Questi campi usano ancora il valore dell'anno scorso e vanno rivalutati prima di generare il PDF definitivo:\n\n"
            + "\n".join(f"- {c}" for c in campi_da_rivedere)
        )

    partecipazioni_fuori_scope = [p for p in dichiarazione.partecipazioni if not p.detenuta_privatamente]
    if partecipazioni_fuori_scope:
        st.error(
            f"⚠️ {len(partecipazioni_fuori_scope)} partecipazione/i detenuta/e come attivo di ditta individuale "
            "(Modulo 8.1) — fuori scope v1, da gestire manualmente."
        )

    st.divider()
    st.subheader("Genera il foglio riepilogativo")
    st.caption("Formato PDF — un foglio con tutti i valori raccolti, organizzato per modulo, da usare come base per la compilazione in eTax.")

    if st.button("📄 Genera PDF", type="primary"):
        pdf_bytes = genera_pdf_riepilogo(dichiarazione)
        st.session_state["pdf_riepilogo_bytes"] = pdf_bytes
        st.success("PDF generato.")

    if "pdf_riepilogo_bytes" in st.session_state:
        st.download_button(
            "⬇️ Scarica il PDF riepilogativo",
            data=st.session_state["pdf_riepilogo_bytes"],
            file_name=f"riepilogo_dichiarazione_{dichiarazione.anno_fiscale}.pdf",
            mime="application/pdf",
        )

    if dichiarazione.conti_correnti or dichiarazione.titoli_investimenti:
        st.divider()
        st.subheader("Modulo 2 ufficiale precompilato")
        if st.button("📋 Genera Modulo 2 ufficiale"):
            mod2_bytes = genera_modulo2_sovrapposto(dichiarazione)
            if mod2_bytes:
                st.session_state["mod2_bytes"] = mod2_bytes
                st.success("Modulo 2 generato.")
        if "mod2_bytes" in st.session_state:
            st.download_button(
                "⬇️ Scarica Modulo 2 compilato", data=st.session_state["mod2_bytes"],
                file_name=f"Modulo_2_{dichiarazione.anno_fiscale}.pdf", mime="application/pdf",
            )

    if dichiarazione.immobili:
        st.divider()
        st.subheader("Moduli 7 ufficiali precompilati (uno per immobile)")
        st.caption("Un Modulo 7 originale per ciascun immobile, come richiesto dal Cantone.")
        if st.button("📋 Genera Moduli 7 ufficiali"):
            st.session_state["mod7_bytes_list"] = [
                (i + 1, genera_modulo7_sovrapposto(imm, dichiarazione.contribuente, i + 1))
                for i, imm in enumerate(dichiarazione.immobili)
            ]
            st.success(f"{len(dichiarazione.immobili)} Modulo/i 7 generato/i.")
        for numero, contenuto in st.session_state.get("mod7_bytes_list", []):
            if contenuto:
                st.download_button(
                    f"⬇️ Scarica Modulo 7 — Immobile {numero}",
                    data=contenuto, file_name=f"Modulo_7_immobile_{numero}_{dichiarazione.anno_fiscale}.pdf",
                    mime="application/pdf", key=f"dl_mod7_{numero}",
                )

    st.divider()
    st.subheader("Modulo 1 ufficiale precompilato — dati personali")
    st.caption("Sfondo da screenshot fornito dal cliente (il Modulo 1 non esiste in versione vuota scaricabile).")
    if st.button("📋 Genera Modulo 1 ufficiale"):
        b = genera_modulo1_sovrapposto(dichiarazione)
        if b:
            st.session_state["mod1_bytes"] = b
            st.success("Modulo 1 generato.")
    if "mod1_bytes" in st.session_state:
        st.download_button("⬇️ Scarica Modulo 1 compilato", data=st.session_state["mod1_bytes"],
                            file_name=f"Modulo_1_{dichiarazione.anno_fiscale}.pdf", mime="application/pdf")

    if dichiarazione.certificati_salario:
        st.divider()
        st.subheader("Modulo 4 ufficiale precompilato")
        st.caption("Attività principale (il primo certificato di salario inserito).")
        if st.button("📋 Genera Modulo 4 ufficiale"):
            b = genera_modulo4_sovrapposto(dichiarazione)
            if b:
                st.session_state["mod4_bytes"] = b
                st.success("Modulo 4 generato.")
        if "mod4_bytes" in st.session_state:
            st.download_button("⬇️ Scarica Modulo 4 compilato", data=st.session_state["mod4_bytes"],
                                file_name=f"Modulo_4_{dichiarazione.anno_fiscale}.pdf", mime="application/pdf")

    if dichiarazione.debiti:
        st.divider()
        st.subheader("Modulo 5 ufficiale precompilato")
        if st.button("📋 Genera Modulo 5 ufficiale"):
            b = genera_modulo5_sovrapposto(dichiarazione)
            if b:
                st.session_state["mod5_bytes"] = b
                st.success("Modulo 5 generato.")
        if "mod5_bytes" in st.session_state:
            st.download_button("⬇️ Scarica Modulo 5 compilato", data=st.session_state["mod5_bytes"],
                                file_name=f"Modulo_5_{dichiarazione.anno_fiscale}.pdf", mime="application/pdf")

    if dichiarazione.cassa_malati or dichiarazione.totale_modulo6_a is not None:
        st.divider()
        st.subheader("Modulo 6 ufficiale precompilato")
        if st.button("📋 Genera Modulo 6 ufficiale"):
            b = genera_modulo6_sovrapposto(dichiarazione)
            if b:
                st.session_state["mod6_bytes"] = b
                st.success("Modulo 6 generato.")
        if "mod6_bytes" in st.session_state:
            st.download_button("⬇️ Scarica Modulo 6 compilato", data=st.session_state["mod6_bytes"],
                                file_name=f"Modulo_6_{dichiarazione.anno_fiscale}.pdf", mime="application/pdf")

    if dichiarazione.partecipazioni:
        st.divider()
        st.subheader("Modulo 8 ufficiale precompilato")
        st.caption("Il modulo originale del Cantone, con i tuoi dati scritti esattamente nelle caselle — pronto da allegare.")
        if st.button("📋 Genera Modulo 8 ufficiale"):
            mod8_bytes = genera_modulo8_sovrapposto(dichiarazione)
            if mod8_bytes:
                st.session_state["mod8_bytes"] = mod8_bytes
                st.success("Modulo 8 generato.")
            else:
                st.warning("Impossibile generare (modulo template mancante o nessuna partecipazione inserita).")
        if "mod8_bytes" in st.session_state:
            st.download_button(
                "⬇️ Scarica Modulo 8 compilato",
                data=st.session_state["mod8_bytes"],
                file_name=f"Modulo_8_{dichiarazione.anno_fiscale}.pdf",
                mime="application/pdf",
            )

    if st.button("← Indietro"):
        state.go_back()
        st.rerun()

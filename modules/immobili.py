"""
modules/immobili.py — Modulo 7, uno per immobile (loop).

Implementa la logica documentata: forfait 10%/20% calcolato automaticamente
dall'anno di costruzione (soglia 31.12.2014), valore locativo calcolato da
"valore di reddito" (90% abitazione primaria, 63% secondaria), e la
gestione delle quote in caso di comproprietà/comunione ereditaria con
controllo che le percentuali sommino a 100%.
"""

import streamlit as st

from core import state
from core.models import Comproprietario, DichiarazioneFiscale, Immobile
from core.ui_helpers import campo_con_fallback, mostra_esempio_documento


def _calcola_forfait(anno_costruzione) -> float:
    """10% se costruito dal 31.12.2014 in poi, 20% se prima — soglia
    confermata dal secondo esempio reale usato per il documento di progetto."""
    if anno_costruzione is None:
        return 0.20
    return 0.10 if anno_costruzione >= 2014 else 0.20


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Modulo 7 — Immobili")

    st.write("**Hai case di proprietà in Svizzera o all'estero?**")
    if st.button("+ Aggiungi un immobile"):
        dichiarazione.immobili.append(Immobile())
        st.rerun()

    for i, imm in enumerate(dichiarazione.immobili):
        with st.container(border=True):
            st.markdown(f"**Immobile {i + 1}**")

            imm.in_svizzera = st.radio(
                "Ubicazione", ["Svizzera", "Estero"], index=0 if imm.in_svizzera else 1,
                horizontal=True, key=f"imm_ubic_{i}",
            ) == "Svizzera"

            col1, col2 = st.columns(2)
            with col1:
                campo_con_fallback(imm.comune, "Comune", key=f"imm_comune_{i}")
                imm.anno_costruzione = st.number_input(
                    "Anno di costruzione", min_value=1800, max_value=dichiarazione.anno_fiscale,
                    value=imm.anno_costruzione or 2000, key=f"imm_anno_{i}",
                )
            with col2:
                campo_con_fallback(
                    imm.nazione_cantone, "Cantone" if imm.in_svizzera else "Nazione", key=f"imm_cantone_{i}"
                )
                imm.numero_registro_fondiario = st.text_input(
                    "Numero registro fondiario (facoltativo)", value=imm.numero_registro_fondiario, key=f"imm_rf_{i}"
                )

            campo_con_fallback(imm.indirizzo, "Indirizzo", key=f"imm_indirizzo_{i}")

            imm.destinazione = st.selectbox(
                "Destinazione", ["Uso proprio", "Uso di terzi", "Uso misto", "In usufrutto/diritto di abitazione"],
                index=["Uso proprio", "Uso di terzi", "Uso misto", "In usufrutto/diritto di abitazione"].index(imm.destinazione),
                key=f"imm_dest_{i}",
            )
            imm.tipo_immobile = st.selectbox(
                "Tipo di immobile", ["Unifamiliare", "Plurifamiliare", "Commerciale e abitativa", "Commerciale", "Altro"],
                index=["Unifamiliare", "Plurifamiliare", "Commerciale e abitativa", "Commerciale", "Altro"].index(imm.tipo_immobile),
                key=f"imm_tipo_{i}",
            )

            comprato_venduto = st.checkbox("Comprato o venduto durante l'anno fiscale", key=f"imm_cv_check_{i}")
            if comprato_venduto:
                imm.comprato_venduto_anno = st.radio("Operazione", ["comprato", "venduto"], horizontal=True, key=f"imm_cv_{i}")
                imm.data_operazione = st.date_input("Data", key=f"imm_data_op_{i}")
                campo_con_fallback(imm.prezzo_operazione, "Prezzo", key=f"imm_prezzo_{i}")

            st.divider()
            st.markdown("**Stima ufficiale**")
            mostra_esempio_documento(
                "scheda_stima_ufficiale_esempio.png",
                "Scheda di calcolo della stima — contiene sia il valore di stima totale sia il 'valore di reddito' usati sotto.",
            )
            campo_con_fallback(
                imm.valore_stima_totale, "Valore di stima totale (casa + edifici accessori + terreno)", key=f"imm_stima_{i}",
                descrizione_ricerca="Totale valore stima ufficiale dell'immobile, Modulo 7 punto 2, cifra 30"
            )

            st.divider()
            st.markdown("**Reddito**")
            if imm.destinazione == "Uso proprio":
                imm.abitazione_primaria = st.radio(
                    "Abitazione primaria o secondaria/vacanza?", ["Primaria", "Secondaria/vacanza"],
                    index=0 if imm.abitazione_primaria else 1, horizontal=True, key=f"imm_prim_{i}",
                ) == "Primaria"
                campo_con_fallback(
                    imm.valore_di_reddito, "Valore di reddito (dalla scheda di stima)", key=f"imm_reddito_{i}",
                    descrizione_ricerca="Valore di reddito sulla scheda di calcolo della stima, sezione VALORE DI REDDITO"
                )
                if imm.valore_di_reddito.valore:
                    try:
                        valore_reddito_num = float(imm.valore_di_reddito.valore.replace("'", "").replace(",", "."))
                        percentuale = 0.90 if imm.abitazione_primaria else 0.63
                        valore_locativo = round(valore_reddito_num * percentuale, 2)
                        st.info(f"Valore locativo calcolato automaticamente: **Fr. {valore_locativo:,.2f}** ({int(percentuale*100)}% del valore di reddito)".replace(",", "'"))
                    except ValueError:
                        st.warning("Il valore di reddito inserito non è un numero valido — controllalo.")
            else:
                campo_con_fallback(
                    imm.affitti_incassati, "Totale affitti incassati nell'anno", key=f"imm_affitti_{i}",
                    descrizione_ricerca="Totale affitti incassati per questo immobile, Modulo 7 punto 4, cifra 5.3",
                    aiuto="Somma di tutti gli inquilini/locatari, incluso eventuale Airbnb",
                )

            forfait = _calcola_forfait(imm.anno_costruzione)
            st.caption(
                f"Deduzione forfettaria spese di gestione: **{int(forfait*100)}%** "
                f"(automatico, in base all'anno di costruzione {imm.anno_costruzione})"
            )

            st.divider()
            st.markdown("**Comproprietà / comunione ereditaria**")
            imm.piena_proprieta = st.radio(
                "Questo immobile è al 100% tuo, o in comproprietà/comunione ereditaria?",
                ["Al 100% mio", "Comproprietà/comunione ereditaria"],
                index=0 if imm.piena_proprieta else 1, key=f"imm_prop_{i}",
            ) == "Al 100% mio"

            if not imm.piena_proprieta:
                col1, col2 = st.columns(2)
                with col1:
                    imm.quota_reddito_contribuente = st.number_input(
                        "Tua quota % reddito", min_value=0.0, max_value=100.0, value=imm.quota_reddito_contribuente, key=f"imm_qr_{i}"
                    )
                with col2:
                    imm.quota_sostanza_contribuente = st.number_input(
                        "Tua quota % sostanza", min_value=0.0, max_value=100.0, value=imm.quota_sostanza_contribuente, key=f"imm_qs_{i}"
                    )

                if st.button("+ Aggiungi comproprietario/erede", key=f"imm_add_comp_{i}"):
                    imm.comproprietari.append(Comproprietario())
                    st.rerun()

                for j, comp in enumerate(imm.comproprietari):
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        comp.cognome_nome = st.text_input("Cognome e nome", value=comp.cognome_nome, key=f"imm_{i}_comp_{j}_nome")
                    with col2:
                        comp.quota_reddito = st.number_input("% reddito", min_value=0.0, max_value=100.0, value=comp.quota_reddito, key=f"imm_{i}_comp_{j}_qr")
                    with col3:
                        comp.quota_sostanza = st.number_input("% sostanza", min_value=0.0, max_value=100.0, value=comp.quota_sostanza, key=f"imm_{i}_comp_{j}_qs")
                    with col4:
                        if st.button("Rimuovi", key=f"imm_{i}_comp_{j}_rm"):
                            imm.comproprietari.pop(j)
                            st.rerun()

                totale_reddito = imm.quota_reddito_contribuente + sum(c.quota_reddito for c in imm.comproprietari)
                totale_sostanza = imm.quota_sostanza_contribuente + sum(c.quota_sostanza for c in imm.comproprietari)
                if abs(totale_reddito - 100) > 0.01 or abs(totale_sostanza - 100) > 0.01:
                    st.error(f"⚠️ Le quote devono sommare a 100%. Attualmente: reddito {totale_reddito}%, sostanza {totale_sostanza}%.")
                else:
                    st.success("✓ Le quote sommano correttamente a 100%.")

            if st.button("Rimuovi questo immobile", key=f"imm_rimuovi_{i}"):
                dichiarazione.immobili.pop(i)
                st.rerun()

    st.divider()
    col_back, _, col_next = st.columns([1, 3, 1])
    with col_back:
        if st.button("← Indietro"):
            state.go_back()
            st.rerun()
    with col_next:
        if st.button("Avanti →", type="primary"):
            state.go_next()
            st.rerun()

"""
modules/immobili.py — Modulo 7, uno per immobile (loop).

Corretto oggi:
- soglia forfait 10%/20%: dal 2015 in poi = 10%, prima del 2015 = 20%
  (indicazione esplicita del cliente, che prevale sulla lettura precedente)
- aggiunta la scelta esplicita tra deduzione forfettaria (calcolata in
  automatico) e spese effettive (con upload fatture)
- comproprietà: la quota del contribuente/coniuge ora si CALCOLA da sola
  come 100% meno la somma dei comproprietari, invece di essere un campo
  separato da tenere manualmente allineato — così la somma è sempre
  corretta per costruzione, non serve più "ricordarsi" di aggiustarla
"""

from datetime import date

import streamlit as st

from core import state
from core.calcoli import COEFF_VL_PRIMARIA, COEFF_VL_SECONDARIA
from core.models import CampoValore, Comproprietario, DichiarazioneFiscale, Immobile
from core.ui_helpers import campo_con_fallback, mostra_esempio_documento


def _calcola_forfait(anno_costruzione) -> float:
    """10% se costruito dal 2015 in poi, 20% se prima del 2015."""
    if anno_costruzione is None:
        return 0.20
    return 0.10 if anno_costruzione >= 2015 else 0.20


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
                    value=imm.anno_costruzione or dichiarazione.anno_fiscale, key=f"imm_anno_{i}",
                    help="Determina automaticamente il forfait spese di gestione: 10% dal 2015, 20% prima",
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
                imm.data_operazione = st.date_input(
                    "Data", key=f"imm_data_op_{i}", value=imm.data_operazione,
                    min_value=date(dichiarazione.anno_fiscale, 1, 1), max_value=date(dichiarazione.anno_fiscale, 12, 31),
                    format="DD/MM/YYYY",
                )
                campo_con_fallback(imm.prezzo_operazione, "Prezzo", key=f"imm_prezzo_{i}")
                etichetta_fin = (
                    "Di cui finanziato con un nuovo mutuo/ipoteca (facoltativo, Fr.)" if imm.comprato_venduto_anno == "comprato"
                    else "Di cui usato per estinguere il mutuo/ipoteca esistente (facoltativo, Fr.)"
                )
                campo_con_fallback(
                    imm.finanziamento_operazione, etichetta_fin, key=f"imm_finanziamento_{i}",
                    aiuto="Serve al calcolo del dispendio: solo la parte pagata/incassata realmente (non finanziata) "
                          "conta come movimento della tua liquidità.",
                )

            st.divider()
            st.markdown("**Stima ufficiale**")
            st.caption("Non hai la scheda di stima ufficiale? Puoi richiederla online:")
            st.link_button(
                "Richiedi la stima ufficiale (eServices Ticino)",
                "https://www.eservices.ti.ch/eservices/esrv/?SRV=XE3D",
                key=f"imm_link_stima_{i}",
            )
            mostra_esempio_documento(
                "scheda_stima_ufficiale_esempio.png",
                "Scheda di calcolo della stima — contiene sia il valore di stima totale sia il 'valore di reddito' usati sotto.",
            )
            if imm.comprato_venduto_anno == "venduto":
                st.info(
                    "Immobile venduto durante l'anno: il valore di stima al 31.12 viene impostato automaticamente "
                    "a **Fr. 0** (non è più di tua proprietà a fine anno), anche se qui sotto risulta un valore inserito in precedenza."
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
                if not imm.abitazione_primaria:
                    st.caption("Per l'abitazione secondaria il valore locativo è il 90% del valore di reddito diviso 0.70, cioè circa il 128.6% (Istruzioni 2025).")
                reddito_lordo_num = None
                if imm.valore_di_reddito.valore:
                    try:
                        valore_reddito_num = float(imm.valore_di_reddito.valore.replace("'", "").replace(",", "."))
                        percentuale = COEFF_VL_PRIMARIA if imm.abitazione_primaria else COEFF_VL_SECONDARIA
                        reddito_lordo_num = round(valore_reddito_num * percentuale, 2)
                        st.info(f"Valore locativo calcolato automaticamente: **Fr. {reddito_lordo_num:,.2f}** ({percentuale*100:.1f}% del valore di reddito)".replace(",", "'"))
                    except ValueError:
                        st.warning("Il valore di reddito inserito non è un numero valido — controllalo.")
            else:
                campo_con_fallback(
                    imm.affitti_incassati, "Totale affitti incassati nell'anno", key=f"imm_affitti_{i}",
                    descrizione_ricerca="Totale affitti incassati per questo immobile, Modulo 7 punto 4, cifra 5.3",
                    aiuto="Somma di tutti gli inquilini/locatari, incluso eventuale Airbnb",
                )
                reddito_lordo_num = None
                if imm.affitti_incassati.valore:
                    try:
                        reddito_lordo_num = float(imm.affitti_incassati.valore.replace("'", "").replace(",", "."))
                    except ValueError:
                        pass

            st.divider()
            st.markdown("**Spese di gestione, amministrazione e manutenzione**")
            forfait = _calcola_forfait(imm.anno_costruzione)
            st.caption(
                "Il forfait è il 10% per gli edifici costruiti dal 31.12.2015 in poi e il 20% per quelli più vecchi. "
                "Non si applica agli immobili affittati a uso aziendale, ai terreni non edificati e ai diritti di superficie "
                "(per questi servono le spese effettive). Se scegli le spese effettive, allega i giustificativi."
            )
            scelta_spese = st.radio(
                "Come vuoi dedurre le spese di gestione?",
                [f"Deduzione forfettaria ({int(forfait*100)}%, calcolata automaticamente)", "Spese effettive (con fatture)"],
                key=f"imm_spese_scelta_{i}",
            )
            if scelta_spese.startswith("Deduzione forfettaria"):
                imm.usa_spese_effettive = False
                if reddito_lordo_num is not None:
                    importo_forfait = round(reddito_lordo_num * forfait, 2)
                    st.success(f"Deduzione forfettaria: **Fr. {importo_forfait:,.2f}** ({int(forfait*100)}% di Fr. {reddito_lordo_num:,.2f})".replace(",", "'"))
                else:
                    st.caption(f"Aliquota applicabile: {int(forfait*100)}% (in base all'anno di costruzione {imm.anno_costruzione}) — inserisci prima il reddito per vedere l'importo.")
            else:
                imm.usa_spese_effettive = True
                if st.button("+ Aggiungi una spesa", key=f"imm_add_spesa_{i}"):
                    imm.spese_effettive.append(CampoValore())
                    st.rerun()
                totale_effettive = 0.0
                for k, spesa in enumerate(imm.spese_effettive):
                    col1, col2 = st.columns([3, 2])
                    with col1:
                        st.file_uploader("Fattura", type=["pdf", "png", "jpg"], key=f"imm_{i}_spesa_{k}_file", label_visibility="collapsed")
                    with col2:
                        campo_con_fallback(spesa, "Importo", key=f"imm_{i}_spesa_{k}_importo")
                    if spesa.valore:
                        try:
                            totale_effettive += float(spesa.valore.replace("'", "").replace(",", "."))
                        except ValueError:
                            pass
                st.info(f"Totale spese effettive inserite: **Fr. {totale_effettive:,.2f}**".replace(",", "'"))

            st.divider()
            st.markdown("**Comproprietà / comunione ereditaria**")
            imm.piena_proprieta = st.radio(
                "Questo immobile è al 100% tuo, o in comproprietà/comunione ereditaria?",
                ["Al 100% mio", "Comproprietà/comunione ereditaria"],
                index=0 if imm.piena_proprieta else 1, key=f"imm_prop_{i}",
            ) == "Al 100% mio"

            if not imm.piena_proprieta:
                imm.intestazione_registro_fondiario = st.text_input(
                    "Intestazione esatta a registro fondiario *", value=imm.intestazione_registro_fondiario,
                    key=f"imm_intestazione_rf_{i}",
                    help="Come risulta esattamente a registro fondiario (nomi di tutti i comproprietari/eredi). Obbligatoria in caso di comproprietà.",
                )
                if not imm.intestazione_registro_fondiario.strip():
                    st.caption("⚠️ Campo obbligatorio in caso di comproprietà: il Modulo 7 lo richiede sempre.")
                st.caption(
                    "Aggiungi ogni comproprietario/erede con la sua quota: la TUA quota si calcola "
                    "automaticamente come il resto, così la somma è sempre 100%."
                )
                if st.button("+ Aggiungi comproprietario/erede", key=f"imm_add_comp_{i}"):
                    imm.comproprietari.append(Comproprietario())
                    st.rerun()

                for j, comp in enumerate(imm.comproprietari):
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        comp.cognome_nome = st.text_input("Cognome e nome", value=comp.cognome_nome, key=f"imm_{i}_comp_{j}_nome")
                    with col2:
                        comp.quota_reddito = st.number_input("% reddito", min_value=0.0, max_value=100.0, value=float(comp.quota_reddito), key=f"imm_{i}_comp_{j}_qr")
                    with col3:
                        comp.quota_sostanza = st.number_input("% sostanza", min_value=0.0, max_value=100.0, value=float(comp.quota_sostanza), key=f"imm_{i}_comp_{j}_qs")
                    with col4:
                        st.write("")
                        if st.button("Rimuovi", key=f"imm_{i}_comp_{j}_rm"):
                            imm.comproprietari.pop(j)
                            st.rerun()

                somma_comp_reddito = sum(c.quota_reddito for c in imm.comproprietari)
                somma_comp_sostanza = sum(c.quota_sostanza for c in imm.comproprietari)

                if somma_comp_reddito > 100 or somma_comp_sostanza > 100:
                    st.error(
                        f"⚠️ I comproprietari da soli superano già il 100% "
                        f"(reddito {somma_comp_reddito}%, sostanza {somma_comp_sostanza}%). Correggi le quote sopra."
                    )
                    imm.quota_reddito_contribuente = 0.0
                    imm.quota_sostanza_contribuente = 0.0
                else:
                    imm.quota_reddito_contribuente = round(100 - somma_comp_reddito, 4)
                    imm.quota_sostanza_contribuente = round(100 - somma_comp_sostanza, 4)
                    st.success(
                        f"✓ Tua quota calcolata automaticamente: **{imm.quota_reddito_contribuente}%** reddito, "
                        f"**{imm.quota_sostanza_contribuente}%** sostanza (somma sempre garantita a 100%)."
                    )

            if st.button("Rimuovi questo immobile", key=f"imm_rimuovi_{i}"):
                dichiarazione.immobili.pop(i)
                st.rerun()

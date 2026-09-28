"""
modules/certificato_salario.py — Modulo 1, redditi da attività dipendente.

Come funziona (decisioni prese con il cliente):
- Nessun tasto "Conferma": ogni certificato vive direttamente nella
  dichiarazione, quindi non si può "dimenticare" di confermarlo.
- Il datore di lavoro e il suo comune NON si chiedono due volte: si
  precompilano dai dati anagrafici (luogo di lavoro), e restano modificabili.
- Se non si è lavorato tutto l'anno per questo datore di lavoro, si apre in
  automatico un altro blocco identico per il certificato successivo.
- Un'attività accessoria si aggiunge con il pulsante in fondo.
"""

from datetime import date

import streamlit as st

from core import state
from core.calcoli import mesi_certificati, periodo_certificati
from core.extraction import estrai_certificato_salario
from core.models import CertificatoSalario, DichiarazioneFiscale, GenereAttivita
from core.ui_helpers import campo_con_fallback, mostra_esempio_documento


def _anagrafica_persona(dichiarazione: DichiarazioneFiscale, persona: str):
    return dichiarazione.contribuente if persona == "contribuente" else dichiarazione.contribuente.coniuge


def _datore_da_anagrafica(dichiarazione: DichiarazioneFiscale, persona: str = "contribuente") -> tuple:
    c = _anagrafica_persona(dichiarazione, persona)
    return c.datore_lavoro.strip(), c.comune_lavoro.strip()


def _datore_da_accessoria(dichiarazione: DichiarazioneFiscale, persona: str = "contribuente") -> tuple:
    """L'attività accessoria è un solo testo 'ragione sociale, comune'."""
    testo = _anagrafica_persona(dichiarazione, persona).attivita_accessoria.strip()
    if "," in testo:
        ragione, comune = testo.rsplit(",", 1)
        return ragione.strip(), comune.strip()
    return testo, ""


def _sincronizza(chiave_widget: str, valore_corrente: str, valore_anagrafica: str, chiave_sync: str) -> str:
    """Tiene il campo allineato ai dati anagrafici finché l'utente non lo ha
    modificato a mano. Restituisce il valore da mostrare."""
    ultimo_sync = st.session_state.get(chiave_sync)
    if (valore_corrente == "" or valore_corrente == ultimo_sync) and valore_anagrafica != valore_corrente:
        st.session_state[chiave_widget] = valore_anagrafica
        valore_corrente = valore_anagrafica
    st.session_state[chiave_sync] = valore_anagrafica
    return valore_corrente


def _vuoto(cert: CertificatoSalario) -> bool:
    return not (
        cert.file_origine or cert.datore_lavoro.valore or cert.cifra_11_salario_netto.valore
        or cert.cifra_10_contributi_lpp.valore or cert.km_tragitto.valore
    )


_MEZZI = {
    "Auto / moto (veicolo privato)": "auto",
    "Mezzo pubblico (abbonamento)": "pubblico",
    "Bicicletta / ciclomotore": "bici",
    "Nessun tragitto (telelavoro, a piedi)": "nessuno",
}


def _etichetta_blocco(cert: CertificatoSalario, numero: int) -> str:
    if cert.tipo_attivita == "accessoria":
        return f"Certificato di salario n. {numero} — attività accessoria"
    if cert.auto_continuazione:
        return f"Certificato di salario n. {numero} — nuovo datore di lavoro (resto dell'anno)"
    return f"Certificato di salario n. {numero} — attività principale"


def _blocco(dichiarazione: DichiarazioneFiscale, cert: CertificatoSalario, indice: int) -> None:
    uid = cert.uid
    with st.container(border=True):
        st.markdown(f"**{_etichetta_blocco(cert, indice + 1)}**")

        file_caricato = st.file_uploader(
            "Certificato di salario", type=["pdf", "png", "jpg", "jpeg"], key=f"up_cert_{uid}"
        )
        if file_caricato is not None:
            cert.file_origine = file_caricato.name
        mostra_esempio_documento(
            "certificato_salario_esempio.png",
            "Il certificato di salario — di solito lo trovi allegato alla busta paga di dicembre o te lo invia il datore di lavoro a inizio anno.",
        )

        api_key = st.session_state.get("anthropic_api_key", "")
        if file_caricato is not None and api_key:
            if st.button("📄 Leggi documento con AI", key=f"ai_cert_{uid}"):
                with st.spinner("Lettura del documento in corso..."):
                    risultato = estrai_certificato_salario(file_caricato.getvalue(), file_caricato.name, api_key)
                if not risultato.ok:
                    st.error(f"Estrazione non riuscita: {risultato.errore}")
                else:
                    for chiave, widget in (
                        ("datore_lavoro", f"c_datore_{uid}"),
                        ("cifra_10_contributi_lpp", f"c_10_{uid}"),
                        ("cifra_11_salario_netto", f"c_11_{uid}"),
                    ):
                        valore = risultato.campi.get(chiave)
                        getattr(cert, chiave).valore = valore
                        getattr(cert, chiave).origine = "utente"
                        st.session_state[widget] = valore or ""
                    if risultato.avvisi:
                        st.warning("Campi non trovati:\n" + "\n".join(f"- {a}" for a in risultato.avvisi))
                    st.success("Documento letto. Controlla i valori qui sotto.")
                    st.rerun()

        # ── Datore di lavoro e comune: precompilati, modificabili ────────
        if cert.tipo_attivita == "accessoria":
            rag_anagrafica, com_anagrafica = _datore_da_accessoria(dichiarazione, cert.persona)
        elif cert.auto_continuazione:
            rag_anagrafica, com_anagrafica = "", ""
        else:
            rag_anagrafica, com_anagrafica = _datore_da_anagrafica(dichiarazione, cert.persona)

        rag_corrente = cert.datore_lavoro.valore or ""
        rag_corrente = _sincronizza(f"c_datore_{uid}", rag_corrente, rag_anagrafica, f"sync_datore_{uid}")
        if rag_corrente != (cert.datore_lavoro.valore or ""):
            cert.datore_lavoro.valore = rag_corrente
            cert.datore_lavoro.origine = "utente"

        com_corrente = cert.comune_datore_lavoro.valore or ""
        com_corrente = _sincronizza(f"c_comune_{uid}", com_corrente, com_anagrafica, f"sync_comune_{uid}")
        chiave_comune = f"c_comune_{uid}"
        opzioni_comune = {} if chiave_comune in st.session_state else {"value": com_corrente}
        cert.comune_datore_lavoro.valore = st.text_input(
            "Comune del datore di lavoro", key=chiave_comune,
            help="Confrontato con il comune di domicilio per le spese di trasporto (Modulo 4)",
            **opzioni_comune,
        )

        campo_con_fallback(cert.datore_lavoro, "Datore di lavoro (ragione sociale)", key=f"c_datore_{uid}")
        campo_con_fallback(
            cert.cifra_10_contributi_lpp, "Cifra 10 — Contributi LPP", key=f"c_10_{uid}",
            descrizione_ricerca="Contributi LPP, cifra 10 del certificato di salario",
        )
        campo_con_fallback(
            cert.cifra_11_salario_netto, "Cifra 11 — Salario netto", key=f"c_11_{uid}",
            descrizione_ricerca="Salario netto, cifra 11 del certificato di salario o cifra 100 del Modulo 1",
        )

        if cert.tipo_attivita == "principale":
            st.markdown("**Per il calcolo delle spese professionali (Modulo 4)**")
            etichette = list(_MEZZI.keys())
            corrente = next((k for k, v in _MEZZI.items() if v == cert.mezzo_trasporto), etichette[0])
            scelta = st.selectbox(
                "Come vai al lavoro?", etichette, index=etichette.index(corrente), key=f"c_mezzo_{uid}",
            )
            cert.mezzo_trasporto = _MEZZI[scelta]
            if cert.mezzo_trasporto == "auto":
                campo_con_fallback(
                    cert.km_tragitto, "Distanza casa-lavoro (km, solo andata)", key=f"c_km_{uid}",
                    aiuto="Il tragitto di andata — il calcolo del ritorno e dei giorni lavorati è automatico",
                )
            elif cert.mezzo_trasporto == "pubblico":
                campo_con_fallback(
                    cert.abbonamento_importo, "Costo annuo dell'abbonamento (Fr.)", key=f"c_abbo_{uid}",
                    aiuto="L'importo effettivamente pagato nell'anno per l'abbonamento ai mezzi pubblici",
                )
            elif cert.mezzo_trasporto == "bici":
                st.caption("Deduzione forfettaria per bicicletta/ciclomotore: Fr. 700.")
            cert.grado_occupazione = int(st.number_input(
                "Grado di occupazione (%)", min_value=1, max_value=100, value=int(cert.grado_occupazione or 100),
                key=f"c_grado_{uid}", help="100 se lavori a tempo pieno; riduce i giorni lavorativi del calcolo.",
            ))

        if cert.tipo_attivita == "accessoria":
            etichetta_anno = "Hai svolto questa attività per tutto l'anno fiscale"
        elif cert.auto_continuazione:
            etichetta_anno = "Hai lavorato qui fino alla fine dell'anno fiscale (nessun altro datore di lavoro dopo)"
        else:
            etichetta_anno = "Hai lavorato qui per tutto l'anno fiscale"
        cert.lavorato_tutto_anno = st.checkbox(etichetta_anno, value=cert.lavorato_tutto_anno, key=f"c_tutto_{uid}")
        anno = dichiarazione.anno_fiscale
        inizio_anno, fine_anno = date(anno, 1, 1), date(anno, 12, 31)
        periodo = periodo_certificati(dichiarazione, cert.persona).get(cert.uid, (None, None))
        if not cert.lavorato_tutto_anno:
            st.markdown("**Periodo di lavoro presso questo datore (date esatte)**")
            col_dal, col_al = st.columns(2)
            with col_dal:
                predefinito = periodo[0] or inizio_anno
                opzioni = {} if f"c_dal_{uid}" in st.session_state else {"value": cert.data_inizio or predefinito}
                cert.data_inizio = st.date_input(
                    "Dal", key=f"c_dal_{uid}", min_value=inizio_anno, max_value=fine_anno, format="DD/MM/YYYY", **opzioni,
                )
            with col_al:
                opzioni = {} if f"c_al_{uid}" in st.session_state else {"value": cert.data_fine}
                cert.data_fine = st.date_input(
                    "Al", key=f"c_al_{uid}", min_value=inizio_anno, max_value=fine_anno, format="DD/MM/YYYY", **opzioni,
                )
            if cert.data_inizio and cert.data_fine and cert.data_fine < cert.data_inizio:
                st.warning("La data di fine è precedente a quella di inizio: controlla.")
            if cert.tipo_attivita == "principale" and (cert.data_fine is None or cert.data_fine < fine_anno):
                st.caption("Qui sotto si apre il certificato del datore di lavoro successivo.")
        elif cert.auto_continuazione and periodo[0]:
            st.caption(f"Periodo: dal {periodo[0].strftime('%d.%m.%Y')} al {fine_anno.strftime('%d.%m.%Y')}.")

        if indice > 0 and st.button("Rimuovi questo certificato", key=f"rm_cert_{uid}"):
            dichiarazione.certificati_salario.remove(cert)
            st.rerun()


def _sezione_persona(dichiarazione: DichiarazioneFiscale, persona: str) -> None:
    """Blocchi dei certificati di UNA persona (contribuente o coniuge)."""
    tutti = dichiarazione.certificati_salario

    def suoi():
        return [c for c in tutti if c.persona == persona]

    if not suoi():
        tutti.append(CertificatoSalario(persona=persona))

    i = 0
    while i < len(suoi()):
        elenco = suoi()
        cert = elenco[i]
        _blocco(dichiarazione, cert, i)

        # Se non ha lavorato tutto l'anno per un'attività principale → serve il blocco successivo
        if cert.tipo_attivita == "principale":
            prossimo_e_continuazione = i + 1 < len(elenco) and elenco[i + 1].auto_continuazione
            fine_anno = date(dichiarazione.anno_fiscale, 12, 31)
            serve_altro = (not cert.lavorato_tutto_anno) and (cert.data_fine is None or cert.data_fine < fine_anno)
            if serve_altro and not prossimo_e_continuazione:
                nuovo = CertificatoSalario(persona=persona, auto_continuazione=True)
                nuovo.lavorato_tutto_anno = True
                tutti.insert(tutti.index(cert) + 1, nuovo)
            elif not serve_altro and prossimo_e_continuazione and _vuoto(elenco[i + 1]):
                tutti.remove(elenco[i + 1])
        i += 1

    principali = [c for c in suoi() if c.tipo_attivita == "principale"]
    periodi = periodo_certificati(dichiarazione, persona)
    intervalli = sorted((periodi[c.uid] for c in principali if periodi.get(c.uid, (None, None))[0] and periodi[c.uid][1]),
                        key=lambda x: x[0])
    if any(b[0] <= a[1] for a, b in zip(intervalli, intervalli[1:])):
        st.warning("I periodi di lavoro delle attività principali si sovrappongono: controlla le date.")

    if st.button("+ Aggiungi un'attività accessoria (altro datore di lavoro)", key=f"add_access_{persona}"):
        tutti.append(CertificatoSalario(persona=persona, tipo_attivita="accessoria"))
        st.rerun()


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("2. Certificato di salario")

    c = dichiarazione.contribuente
    coniuge = c.coniuge
    # se il coniuge non c'è (più), togliamo i suoi certificati: non devono finire nei calcoli
    if coniuge is None:
        dichiarazione.certificati_salario[:] = [x for x in dichiarazione.certificati_salario if x.persona != "coniuge"]
    coniuge_dipendente = coniuge is not None and (
        GenereAttivita.DIPENDENTE in coniuge.genere_attivita
        or any(x.persona == "coniuge" for x in dichiarazione.certificati_salario)
    )

    if coniuge is not None:
        st.subheader("Contribuente")
    _sezione_persona(dichiarazione, "contribuente")

    if coniuge is not None:
        st.divider()
        st.subheader(f"Coniuge / partner registrato — {coniuge.nome} {coniuge.cognome}".strip(" —"))
        if coniuge_dipendente:
            _sezione_persona(dichiarazione, "coniuge")
        else:
            st.caption(
                "Il/la coniuge non risulta lavoratore/trice dipendente. Se lo è, tornando all'anagrafica "
                "e scegliendo «Dipendente» compare qui il suo certificato di salario."
            )

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

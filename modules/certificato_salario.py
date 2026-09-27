"""
modules/certificato_salario.py

Dimostra insieme le due funzionalità decise oggi:
1. foto di esempio del documento da allegare (mostra_esempio_documento)
2. fallback "anno scorso" su ogni campo di valore (campo_con_fallback)
oltre all'estrazione AI già presente. Questo è il pattern di riferimento
da replicare sugli altri moduli (conti/titoli, immobili, ecc.).
"""

import streamlit as st

from core import state
from core.extraction import estrai_certificato_salario
from core.models import CertificatoSalario, DichiarazioneFiscale
from core.ui_helpers import campo_con_fallback, mostra_esempio_documento


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("2. Certificato di salario")

    if "certificato_in_corso" not in st.session_state:
        st.session_state["certificato_in_corso"] = CertificatoSalario()
    certificato: CertificatoSalario = st.session_state["certificato_in_corso"]

    mostra_esempio_documento(
        "certificato_salario_esempio.png",
        "Il certificato di salario (Lohnausweis) — di solito lo trovi allegato alla busta paga di dicembre o te lo invia il datore di lavoro a inizio anno.",
    )

    api_key = st.session_state.get("anthropic_api_key", "")
    file_caricato = st.file_uploader("Certificato di salario", type=["pdf", "png", "jpg", "jpeg"], key="upload_cert_salario")

    if file_caricato is not None:
        if st.button("📄 Leggi documento con AI", disabled=not api_key):
            with st.spinner("Lettura del documento in corso..."):
                risultato = estrai_certificato_salario(file_caricato.getvalue(), file_caricato.name, api_key)
            if not risultato.ok:
                st.error(f"Estrazione non riuscita: {risultato.errore}")
            else:
                for chiave in ("datore_lavoro", "cifra_10_contributi_lpp", "cifra_11_salario_netto"):
                    valore = risultato.campi.get(chiave)
                    campo = getattr(certificato, chiave)
                    campo.valore = valore
                    campo.origine = "utente"
                if risultato.avvisi:
                    st.warning("Campi non trovati:\n" + "\n".join(f"- {a}" for a in risultato.avvisi))
                st.success("Documento letto. Controlla i valori qui sotto prima di confermare.")
        certificato.file_origine = file_caricato.name

    st.subheader("Campi (verifica e correggi)")
    campo_con_fallback(certificato.datore_lavoro, "Datore di lavoro", key="c_datore")
    campo_con_fallback(
        certificato.cifra_10_contributi_lpp, "Cifra 10 — Contributi LPP", key="c_10",
        descrizione_ricerca="Contributi LPP, cifra 10 del certificato di salario"
    )
    campo_con_fallback(
        certificato.cifra_11_salario_netto, "Cifra 11 — Salario netto", key="c_11",
        descrizione_ricerca="Salario netto, cifra 11 del certificato di salario o cifra 100 del Modulo 1"
    )

    if certificato.comune_datore_lavoro.valore is None:
        certificato.comune_datore_lavoro.valore = ""
    certificato.comune_datore_lavoro.valore = st.text_input(
        "Comune del datore di lavoro", value=certificato.comune_datore_lavoro.valore or "",
        help="Confrontato con il comune di domicilio per le spese di trasporto (Modulo 4)"
    )

    st.markdown("**Per il calcolo delle spese di trasporto (Modulo 4)**")
    campo_con_fallback(
        certificato.km_tragitto, "Distanza casa-lavoro (km, solo andata)", key="c_km",
        aiuto="Il tragitto di andata — il calcolo del ritorno e dei giorni lavorati è automatico"
    )
    certificato.lavorato_tutto_anno = st.checkbox(
        "Hai lavorato qui per tutto l'anno fiscale", value=certificato.lavorato_tutto_anno, key="c_tutto_anno"
    )
    if not certificato.lavorato_tutto_anno:
        certificato.mesi_lavorati = st.number_input(
            "Per quanti mesi hai lavorato qui nell'anno", min_value=1, max_value=12,
            value=certificato.mesi_lavorati or 12, key="c_mesi",
        )

    if st.button("Conferma questo certificato", type="primary"):
        dichiarazione.certificati_salario.append(certificato)
        del st.session_state["certificato_in_corso"]
        st.success("Certificato aggiunto.")
        st.rerun()

    if dichiarazione.certificati_salario:
        st.subheader("Certificati confermati")
        for i, cert in enumerate(dichiarazione.certificati_salario, start=1):
            st.write(f"{i}. {cert.datore_lavoro.valore or '(datore non specificato)'}")

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

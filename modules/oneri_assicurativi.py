"""
modules/oneri_assicurativi.py — Modulo 6, punto 1-3.

Cassa malati chiesta separatamente per contribuente, coniuge, e ogni
figlio (come richiesto) — con l'istruzione esplicita di sommare premio +
eventuali fatture pagate elencate nel certificato di fine anno.

Poi il calcolo automatico ufficiale:
  (A) Totale oneri assicurativi = somma cassa malati di tutti +
      assicurazione infortuni + assicurazione vita + interessi risparmio
      (ripresi automaticamente dai conti correnti già inseriti) +
      assicurazione perdita di guadagno
  (B) Deduzione massima forfettaria = importo base (stato civile) +
      supplemento per figli/persone a carico + supplemento se nessun
      versamento 2°/3° pilastro — esattamente le regole del modulo ufficiale
  Deduzione ammessa = il minore tra (A) e (B)
"""

import streamlit as st

from core import state
from core.models import CassaMalati, DichiarazioneFiscale
from core.ui_helpers import campo_con_fallback, mostra_esempio_documento

BASE_CONIUGATI = 10900
BASE_ALTRI = 5500
SUPPLEMENTO_PER_FIGLIO = 1200
SUPPLEMENTO_NO_PREVIDENZA_CONIUGATI = 4500
SUPPLEMENTO_NO_PREVIDENZA_ALTRI = 2300


def _numero(campo_valore) -> float:
    if not campo_valore or not campo_valore.valore:
        return 0.0
    try:
        return float(campo_valore.valore.replace("'", "").replace(",", "."))
    except ValueError:
        return 0.0


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Modulo 6 — Oneri assicurativi e interessi a risparmio")

    # ── Cassa malati, per persona ────────────────────────────────────
    st.subheader("Cassa malati")
    st.info(
        "Per ogni persona, allega il certificato di fine anno della cassa malati e scrivi "
        "**la somma di premio annuo + eventuali fatture pagate** elencate nello stesso certificato."
    )

    persone_disponibili = ["Contribuente"]
    if dichiarazione.contribuente.coniuge:
        persone_disponibili.append("Coniuge")
    persone_disponibili += [f.nome for f in dichiarazione.figli if f.nome]

    persone_gia_inserite = {cm.persona for cm in dichiarazione.cassa_malati}
    for persona in persone_disponibili:
        if persona not in persone_gia_inserite:
            dichiarazione.cassa_malati.append(CassaMalati(persona=persona))
            persone_gia_inserite.add(persona)

    for cm in dichiarazione.cassa_malati:
        if cm.persona not in persone_disponibili:
            continue  # persona rimossa altrove (es. coniuge tolto)
        with st.container(border=True):
            st.markdown(f"**Cassa malati — {cm.persona}**")
            mostra_esempio_documento("attestato_3pilastro_esempio.png", "Il certificato di fine anno della cassa malati riporta premio e fatture pagate.")
            file_all = st.file_uploader(
                "Certificato di fine anno", type=["pdf", "png", "jpg"], key=f"cm_file_{cm.persona}"
            )
            if file_all is not None:
                cm.file_origine = file_all.name
            campo_con_fallback(
                cm.importo_annuo, "Totale pagato nell'anno (premio + fatture)", key=f"cm_importo_{cm.persona}",
            )

    st.divider()

    # ── Altri oneri assicurativi ──────────────────────────────────────
    st.subheader("Altri oneri assicurativi (se presenti)")
    campo_con_fallback(dichiarazione.assicurazione_infortuni_privata, "Assicurazione infortuni privata", key="ass_infortuni")
    campo_con_fallback(dichiarazione.assicurazione_vita, "Assicurazioni private vita/rendita vitalizia", key="ass_vita")
    campo_con_fallback(dichiarazione.assicurazione_perdita_guadagno_malattia, "Assicurazione perdita di guadagno per malattia", key="ass_perdita")

    interessi_risparmio = sum(
        _numero(c.interessi_redditi) for c in dichiarazione.conti_correnti
    )
    st.caption(f"Interessi su capitali a risparmio (ripresi automaticamente dai conti correnti già inseriti): Fr. {interessi_risparmio:,.2f}".replace(",", "'"))

    st.divider()

    # ── 3° pilastro A ─────────────────────────────────────────────────
    st.subheader("3° pilastro A")
    dichiarazione.terzo_pilastro_versato = st.checkbox(
        "Hai versato contributi al 3° pilastro A quest'anno?", value=bool(dichiarazione.terzo_pilastro_versato)
    )
    if dichiarazione.terzo_pilastro_versato:
        mostra_esempio_documento("attestato_3pilastro_esempio.png", "Attestazione dei versamenti al 3° pilastro A.")
        file_p3 = st.file_uploader("Attestato 3° pilastro A", type=["pdf", "png", "jpg"], key="p3_file")
        if file_p3 is not None:
            dichiarazione.terzo_pilastro_file = file_p3.name
        campo_con_fallback(dichiarazione.terzo_pilastro_importo, "Importo versato nell'anno (da attestato)", key="p3_importo")

    st.divider()

    # ── Calcolo automatico A / B / deduzione ammessa ─────────────────
    st.subheader("Calcolo automatico")

    totale_a = sum(_numero(cm.importo_annuo) for cm in dichiarazione.cassa_malati)
    totale_a += _numero(dichiarazione.assicurazione_infortuni_privata)
    totale_a += _numero(dichiarazione.assicurazione_vita)
    totale_a += _numero(dichiarazione.assicurazione_perdita_guadagno_malattia)
    totale_a += interessi_risparmio

    coniugati = dichiarazione.contribuente.richiede_dati_coniuge()
    base = BASE_CONIUGATI if coniugati else BASE_ALTRI
    supplemento_figli = SUPPLEMENTO_PER_FIGLIO * len(dichiarazione.figli)

    ha_previdenza = dichiarazione.terzo_pilastro_versato or any(
        c.cifra_10_contributi_lpp.valore for c in dichiarazione.certificati_salario
    )
    supplemento_no_prev = 0 if ha_previdenza else (
        SUPPLEMENTO_NO_PREVIDENZA_CONIUGATI if coniugati else SUPPLEMENTO_NO_PREVIDENZA_ALTRI
    )
    totale_b = base + supplemento_figli + supplemento_no_prev

    deduzione_ammessa = min(totale_a, totale_b)

    dichiarazione.totale_modulo6_a = totale_a
    dichiarazione.totale_modulo6_b = totale_b
    dichiarazione.totale_modulo6_ammesso = deduzione_ammessa

    col1, col2, col3 = st.columns(3)
    col1.metric("(A) Oneri effettivi", f"Fr. {totale_a:,.2f}".replace(",", "'"))
    col2.metric("(B) Massimo forfettario", f"Fr. {totale_b:,.2f}".replace(",", "'"))
    col3.metric("Deduzione ammessa (min A,B)", f"Fr. {deduzione_ammessa:,.2f}".replace(",", "'"))
    st.caption(
        f"(B) calcolato come: base {'coniugati' if coniugati else 'altri contribuenti'} Fr. {base:,.0f} "
        f"+ Fr. {supplemento_figli:,.0f} per {len(dichiarazione.figli)} figlio/i "
        f"+ Fr. {supplemento_no_prev:,.0f} (nessun versamento 2°/3° pilastro rilevato)".replace(",", "'")
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

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
from core.calcoli import calcolo_mod6
from core.models import AssicurazioneVita, CassaMalati, DichiarazioneFiscale
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
        "**la somma di premio annuo + eventuali fatture pagate** elencate nello stesso certificato "
        "(sul certificato: «Totale premi fatturati» + «Totale costi fatturati»)."
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
            file_all = st.file_uploader(
                "Certificato di fine anno", type=["pdf", "png", "jpg"], key=f"cm_file_{cm.persona}"
            )
            if file_all is not None:
                cm.file_origine = file_all.name
            mostra_esempio_documento(
                "cassa_malati_esempio.png",
                "Il certificato di fine anno della cassa malati: somma «Totale premi fatturati» e «Totale costi fatturati».",
            )
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
        _numero(c.interessi_redditi) for c in dichiarazione.conti_correnti if c.tipo == "Conti risparmio/libretto"
    )
    st.caption(
        "Interessi su capitali a risparmio (ripresi automaticamente dai conti di risparmio/libretti già inseriti): "
        f"Fr. {interessi_risparmio:,.2f}".replace(",", "'")
    )

    st.divider()

    # ── 3° pilastro A ─────────────────────────────────────────────────
    st.subheader("3° pilastro A")
    dichiarazione.terzo_pilastro_versato = st.checkbox(
        "Hai versato contributi al 3° pilastro A quest'anno?", value=bool(dichiarazione.terzo_pilastro_versato)
    )
    if dichiarazione.terzo_pilastro_versato:
        file_p3 = st.file_uploader("Attestato 3° pilastro A", type=["pdf", "png", "jpg"], key="p3_file")
        if file_p3 is not None:
            dichiarazione.terzo_pilastro_file = file_p3.name
        mostra_esempio_documento("attestato_3pilastro_esempio.png", "Attestazione dei versamenti al 3° pilastro A.")
        campo_con_fallback(dichiarazione.terzo_pilastro_importo, "Importo versato nell'anno (da attestato)", key="p3_importo")

    coniuge = dichiarazione.contribuente.coniuge
    if coniuge is not None:
        st.markdown(f"**3° pilastro A — {coniuge.nome or 'coniuge'}**")
        dichiarazione.terzo_pilastro_coniuge_versato = st.checkbox(
            "Il/la coniuge ha versato contributi al 3° pilastro A quest'anno?",
            value=bool(dichiarazione.terzo_pilastro_coniuge_versato), key="p3k_versato",
        )
        if dichiarazione.terzo_pilastro_coniuge_versato:
            file_p3k = st.file_uploader("Attestato 3° pilastro A del/della coniuge", type=["pdf", "png", "jpg"], key="p3k_file")
            if file_p3k is not None:
                dichiarazione.terzo_pilastro_coniuge_file = file_p3k.name
            mostra_esempio_documento("attestato_3pilastro_esempio.png", "Attestazione dei versamenti al 3° pilastro A.")
            campo_con_fallback(
                dichiarazione.terzo_pilastro_coniuge_importo, "Importo versato nell'anno dal/dalla coniuge (da attestato)",
                key="p3k_importo",
            )

    st.divider()

    # ── Assicurazioni sulla vita con valore di riscatto (sostanza, cifra 304) ─
    st.subheader("Assicurazioni sulla vita con valore di riscatto")
    st.caption(
        "Hai un'assicurazione sulla vita o di rendita con valore di riscatto (es. 3° pilastro B)? "
        "Il valore di riscatto al 31.12 è sostanza e si dichiara: lo trovi sull'attestato della compagnia."
    )
    if st.button("+ Aggiungi un'assicurazione sulla vita"):
        dichiarazione.assicurazioni_vita.append(AssicurazioneVita())
        st.rerun()
    for i, av in enumerate(dichiarazione.assicurazioni_vita):
        with st.container(border=True):
            file_av = st.file_uploader("Attestato al 31.12 della compagnia", type=["pdf", "png", "jpg"], key=f"av_file_{i}")
            if file_av is not None:
                av.file_origine = file_av.name
            av.societa = st.text_input("Compagnia di assicurazione", value=av.societa, key=f"av_soc_{i}")
            col1, col2 = st.columns(2)
            with col1:
                av.anno_conclusione = int(st.number_input(
                    "Anno di conclusione", min_value=1950, max_value=dichiarazione.anno_fiscale,
                    value=av.anno_conclusione or dichiarazione.anno_fiscale, key=f"av_conc_{i}"))
            with col2:
                av.anno_scadenza = int(st.number_input(
                    "Anno di scadenza", min_value=dichiarazione.anno_fiscale, max_value=2100,
                    value=av.anno_scadenza or dichiarazione.anno_fiscale + 10, key=f"av_scad_{i}"))
            col3, col4 = st.columns(2)
            with col3:
                campo_con_fallback(av.somma_assicurata, "Somma assicurata (Fr.)", key=f"av_somma_{i}")
            with col4:
                campo_con_fallback(av.valore_fiscale, "Valore di riscatto al 31.12 (Fr.)", key=f"av_valore_{i}")
            if st.button("Rimuovi", key=f"av_rm_{i}"):
                dichiarazione.assicurazioni_vita.pop(i)
                st.rerun()

    st.divider()

    # ── Calcolo automatico A / B / deduzione ammessa ─────────────────
    st.subheader("Calcolo automatico")

    r = calcolo_mod6(dichiarazione)
    totale_a, totale_b, deduzione_ammessa = r["totale_a"], r["totale_b"], r["ammessa"]
    coniugati, base = r["coniugati"], r["base"]
    supplemento_figli, supplemento_no_prev = r["suppl_figli"], r["suppl_no_previdenza"]

    dichiarazione.totale_modulo6_a = totale_a
    dichiarazione.totale_modulo6_b = totale_b
    dichiarazione.totale_modulo6_ammesso = deduzione_ammessa

    col1, col2, col3 = st.columns(3)
    col1.metric("(A) Oneri effettivi", f"Fr. {totale_a:,.2f}".replace(",", "'"))
    col2.metric("(B) Massimo forfettario", f"Fr. {totale_b:,.2f}".replace(",", "'"))
    col3.metric("Deduzione ammessa (min A,B)", f"Fr. {deduzione_ammessa:,.2f}".replace(",", "'"))
    st.caption(
        f"(B) calcolato come: base {'coniugati' if coniugati else 'altri contribuenti'} Fr. {base:,.0f} "
        f"+ Fr. {supplemento_figli:,.0f} per {r['n_figli']} figlio/i a carico "
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

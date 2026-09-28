"""
modules/spese_professionali.py — Modulo 4.

Quasi tutto qui è calcolo automatico dai dati già raccolti nel certificato
di salario (km tragitto, periodo lavorato): l'utente non inserisce nulla
di nuovo qui, solo controlla il risultato.

Logica:
- giorni = 220 se lavorato tutto l'anno, altrimenti 220 * mesi_lavorati/12
  (arrotondato), per ciascun certificato di salario indipendentemente
- km totali = km_tragitto * 2 (andata e ritorno) * giorni
- deduzione trasporto = km totali * Fr. 0.60
- forfait: Fr. 3'000.- per l'attività principale (il primo certificato
  inserito), Fr. 800.- per ogni attività accessoria (i successivi) —
  stessa logica di classificazione già usata per cifra 100/104
"""

import streamlit as st

from core import state
from core.models import DichiarazioneFiscale

TARIFFA_KM = 0.60
FORFAIT_PRINCIPALE = 3000
FORFAIT_ACCESSORIA = 800


def _giorni_lavorati(cert) -> int:
    if cert.lavorato_tutto_anno:
        return 220
    mesi = cert.mesi_lavorati or 12
    return round(220 * mesi / 12)


def _numero(campo_valore) -> float:
    if not campo_valore or not campo_valore.valore:
        return 0.0
    try:
        return float(campo_valore.valore.replace("'", "").replace(",", "."))
    except ValueError:
        return 0.0


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Modulo 4 — Spese professionali")

    if not dichiarazione.certificati_salario:
        st.info("Nessun certificato di salario inserito — questo modulo non si applica.")
    else:
        totale_generale = 0.0
        for n, cert in enumerate(dichiarazione.certificati_salario, start=1):
            with st.container(border=True):
                ruolo = "Attività principale" if n == 1 else "Attività accessoria"
                st.markdown(f"**{ruolo} — {cert.datore_lavoro.valore or f'Certificato {n}'}**")

                giorni = _giorni_lavorati(cert)
                km_tragitto = _numero(cert.km_tragitto)
                km_totali = km_tragitto * 2 * giorni
                deduzione_trasporto = round(km_totali * TARIFFA_KM, 2)
                forfait = FORFAIT_PRINCIPALE if n == 1 else FORFAIT_ACCESSORIA
                totale_cert = deduzione_trasporto + forfait
                totale_generale += totale_cert

                col1, col2, col3 = st.columns(3)
                col1.metric("Giorni lavorativi", giorni)
                col2.metric("Km totali (andata+ritorno)", f"{km_totali:,.0f}".replace(",", "'"))
                col3.metric("Deduzione trasporto", f"Fr. {deduzione_trasporto:,.2f}".replace(",", "'"))

                st.caption(
                    f"Forfait {'attività principale' if n == 1 else 'attività accessoria'}: "
                    f"Fr. {forfait:,.0f}".replace(",", "'")
                )
                st.write(f"**Totale spese professionali per questa attività: Fr. {totale_cert:,.2f}**".replace(",", "'"))

        st.divider()
        st.success(f"**Totale complessivo Modulo 4 (cifra 9): Fr. {totale_generale:,.2f}**".replace(",", "'"))
        dichiarazione.totale_modulo4 = totale_generale

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

"""
modules/partecipazioni.py — Modulo 8, partecipazioni qualificate (≥10%).

Nota sul valore fiscale: il metodo ufficiale per società non quotate è la
Circolare n. 28 della Conferenza fiscale svizzera (pesa valore sostanziale
e valore di rendimento, non un semplice prodotto) — ma su indicazione
esplicita del cliente, che gestisce la maggior parte di queste posizioni
lasciando poi all'autorità fiscale l'eventuale ripresa in sede di verifica
incrociata con la dichiarazione della società, il programma usa la stima
rapida capitale sociale × quota %. Resta comunque un valore MODIFICABILE
a mano, non imposto.
"""

import streamlit as st

from core import state
from core.models import DichiarazioneFiscale, Partecipazione
from core.ui_helpers import campo_con_fallback, mostra_esempio_documento


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Modulo 8 — Partecipazioni qualificate")
    st.write("**Fai parte, con più del 10% del capitale, di una Sagl o SA?**")

    if st.button("+ Aggiungi una società"):
        dichiarazione.partecipazioni.append(Partecipazione())
        st.rerun()

    for i, p in enumerate(dichiarazione.partecipazioni):
        with st.container(border=True):
            st.markdown(f"**Società {i + 1}**")

            mostra_esempio_documento(
                "estratto_registro_commercio_esempio.png",
                "Estratto del registro di commercio — conferma capitale sociale e quote in modo verificabile.",
            )

            campo_con_fallback(p.denominazione, "Denominazione (es. \"ABC SA\")", key=f"part_denom_{i}")
            col1, col2 = st.columns(2)
            with col1:
                campo_con_fallback(
                    p.capitale_sociale, "Capitale sociale", key=f"part_cap_{i}",
                    aiuto='Di solito Fr. 20\'000.- per una Sagl e Fr. 100\'000.- per una SA — verificabile sul registro di commercio (www.zefix.ch)',
                )
            with col2:
                p.quota_percentuale = st.number_input(
                    "Quota di partecipazione %", min_value=0.0, max_value=100.0,
                    value=p.quota_percentuale or 0.0, key=f"part_quota_{i}",
                )

            if p.quota_percentuale is not None and p.quota_percentuale < 10:
                st.warning(
                    "Sotto il 10% non è una partecipazione qualificata: va nell'Elenco titoli normale "
                    "(sezione Titoli e investimenti), non qui."
                )

            p.detenuta_privatamente = st.radio(
                "La detieni a titolo personale o è un attivo della tua ditta individuale?",
                ["A titolo personale", "Attivo della ditta individuale"],
                index=0 if p.detenuta_privatamente else 1, key=f"part_priv_{i}",
            ) == "A titolo personale"

            if not p.detenuta_privatamente:
                st.error(
                    "⚠️ Fuori scope v1: le partecipazioni detenute come attivo di una ditta individuale "
                    "vanno al Modulo 8.1, non ancora gestito da questo programma. Segnala questo caso "
                    "per la gestione manuale."
                )

            st.markdown("**Valore fiscale al 31.12**")

            valore_calcolato = None
            if p.capitale_sociale.valore and p.quota_percentuale:
                try:
                    capitale_num = float(p.capitale_sociale.valore.replace("'", "").replace(",", "."))
                    valore_calcolato = round(capitale_num * (p.quota_percentuale / 100), 2)
                except ValueError:
                    pass

            if valore_calcolato is not None:
                p.valore_fiscale.valore = f"{valore_calcolato:,.2f}".replace(",", "'")
                p.valore_fiscale.origine = "calcolato"
                st.metric("Valore fiscale (calcolato automaticamente)", f"Fr. {p.valore_fiscale.valore}")
                st.caption(
                    "= capitale sociale × quota % — nessun inserimento manuale richiesto. "
                    "È una stima semplificata: l'autorità fiscale può rettificarla in sede di ripresa "
                    "confrontandola con la dichiarazione della società."
                )
            else:
                st.caption("Compila capitale sociale e quota % qui sopra per calcolare automaticamente il valore fiscale.")

            p.ha_ricevuto_dividendi = st.checkbox("Ha ricevuto dividendi da questa società nell'anno fiscale", value=bool(p.ha_ricevuto_dividendi), key=f"part_div_check_{i}")
            if p.ha_ricevuto_dividendi:
                campo_con_fallback(
                    p.dividendi_lordo_totale, "Importo LORDO totale distribuito dalla società", key=f"part_div_{i}",
                    aiuto="Non l'importo arrivato in banca, ma il totale lordo distribuito PRIMA della trattenuta del 35% di imposta preventiva",
                )

            if st.button("Rimuovi questa società", key=f"part_rimuovi_{i}"):
                dichiarazione.partecipazioni.pop(i)
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

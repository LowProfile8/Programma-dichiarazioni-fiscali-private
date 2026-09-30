"""
modules/spese_professionali.py — Modulo 4.

Quasi tutto qui è calcolo automatico dai dati già raccolti nel certificato
di salario: l'utente non inserisce nulla di nuovo, solo controlla il
risultato. La logica sta in core/calcoli.py (calcolo_mod4), la stessa che
scrive poi i numeri nel Modulo 4 (una pagina per il contribuente e, se c'è,
una per il coniuge):

- giorni = 220 × mesi/12 × grado di occupazione, per ogni attività principale
- auto/moto: km andata × 2 × giorni × Fr. 0.60
- mezzo pubblico: costo effettivo dell'abbonamento
- bicicletta/ciclomotore: forfait fisso Fr. 700
- forfait fissi: Fr. 3'000 (attività principale) e Fr. 800 (accessoria), non ridotti
"""

import streamlit as st

from core import state
from core.calcoli import FORFAIT_ACCESSORIA, FORFAIT_PRINCIPALE, calcolo_mod4, mesi_certificati, numero
from core.models import DichiarazioneFiscale


def _fr(x: float, decimali: int = 0) -> str:
    return f"Fr. {x:,.{decimali}f}".replace(",", "'")


def _sezione(dichiarazione: DichiarazioneFiscale, persona: str) -> None:
    risultato = calcolo_mod4(dichiarazione, persona)
    if not risultato["ha_dati"]:
        st.info("Nessun certificato di salario inserito — questo modulo non si applica.")
        return
    mesi = {c.uid: m for c, m in mesi_certificati(dichiarazione, persona)}

    for n, cert in enumerate([c for c in dichiarazione.certificati_salario if c.persona == persona], start=1):
        with st.container(border=True):
            ruolo = "Attività accessoria" if cert.tipo_attivita == "accessoria" else "Attività principale"
            st.markdown(f"**{ruolo} — {cert.datore_lavoro.valore or f'Certificato {n}'}**")
            m = mesi.get(cert.uid, 12)
            if cert.tipo_attivita == "accessoria":
                st.caption(f"Forfait attività accessoria: {_fr(FORFAIT_ACCESSORIA)}")
                continue
            riga = next((r for r in risultato["righe"] if r["cert"] is cert), None)
            if riga:
                col1, col2, col3 = st.columns(3)
                col1.metric("Giorni lavorativi", riga["giorni"])
                col2.metric("Km totali (andata+ritorno)", f"{riga['km_totali']:,.0f}".replace(",", "'"))
                col3.metric("Deduzione trasporto", _fr(riga["km_totali"] * 0.60, 2))
            elif cert.mezzo_trasporto == "pubblico":
                st.caption(f"Abbonamento mezzi pubblici: {_fr(numero(cert.abbonamento_importo))}")
            elif cert.mezzo_trasporto == "bici":
                st.caption("Bicicletta/ciclomotore: forfait Fr. 700")
            else:
                st.caption("Nessuna deduzione di trasporto.")
            st.caption(f"Forfait attività principale: {_fr(FORFAIT_PRINCIPALE)}")

    # ── Pasti principali fuori casa (predefiniti, calcolati sui giorni già inseriti) ──
    anagrafica = dichiarazione.contribuente if persona == "contribuente" else dichiarazione.contribuente.coniuge
    if anagrafica is not None and any(
        c.tipo_attivita == "principale" for c in dichiarazione.certificati_salario if c.persona == persona
    ):
        with st.container(border=True):
            st.markdown("**Pasti principali fuori casa**")
            anagrafica.pasti_fuori_casa = st.checkbox(
                "Consumo il pasto principale fuori casa nei giorni di lavoro (Fr. 15 al giorno, al massimo Fr. 3'200 all'anno)",
                value=anagrafica.pasti_fuori_casa, key=f"pasti_fuori_{persona}",
                help="Calcolato sui giorni di lavoro già inseriti (somma dei vari lavori, al massimo 220). Togli la spunta se pranzi a casa.",
            )
            if anagrafica.pasti_fuori_casa:
                anagrafica.pasti_con_mensa = st.checkbox(
                    "Ho a disposizione una mensa o il datore di lavoro contribuisce alle spese (Fr. 7.50 al giorno, al massimo Fr. 1'600)",
                    value=anagrafica.pasti_con_mensa, key=f"pasti_mensa_{persona}",
                )
                nuovo = calcolo_mod4(dichiarazione, persona)
                if nuovo["pasti"]:
                    st.caption(f"{nuovo['giorni_pasti']} giorni → deduzione pasti {_fr(nuovo['pasti'])}")

    risultato = calcolo_mod4(dichiarazione, persona)   # ricalcolo dopo le scelte sui pasti

    st.success(f"**Totale Modulo 4: {_fr(risultato['totale'])}**")


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Modulo 4 — Spese professionali")
    coniuge = dichiarazione.contribuente.coniuge

    if coniuge is not None:
        st.subheader("Contribuente")
    _sezione(dichiarazione, "contribuente")
    dichiarazione.totale_modulo4 = float(calcolo_mod4(dichiarazione, "contribuente")["totale"])

    if coniuge is not None:
        st.divider()
        st.subheader("Coniuge / partner registrato")
        st.caption("Il Modulo 4 ha una pagina anche per il/la coniuge: la compiliamo con i suoi dati.")
        _sezione(dichiarazione, "coniuge")

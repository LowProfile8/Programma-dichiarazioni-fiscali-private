"""
modules/veicoli.py — auto, moto e barche (sostanza mobiliare, Modulo 1).

Per ogni mezzo si chiede: tipo, come lo si possiede (comprato, finanziamento,
leasing, comproprietà), marca e modello, anno di acquisto e valore di mercato
al 31.12 (con un link per verificarlo sui siti di compravendita).
Auto e moto vanno nella cifra 306 («29.4 Veicoli a motore», con una pagina
allegata); le barche nella cifra 308 («29.5 Altri elementi»).
Il leasing non è di proprietà: si chiede la rata mensile e non conta come sostanza.
"""

from urllib.parse import quote_plus

import streamlit as st

from core import state
from core.calcoli import calcolo_veicoli, valore_veicolo
from core.models import DichiarazioneFiscale, Veicolo
from core.ui_helpers import campo_con_fallback

MODALITA = ["Comprato", "Finanziamento", "Leasing", "Comproprietà"]
DESCRIZIONE_MODALITA = {
    "Comprato": "È di tua proprietà (pagato).",
    "Finanziamento": "L'hai comprato con un finanziamento: il valore è sostanza e il debito va indicato tra i debiti.",
    "Leasing": "Non è di tua proprietà: non conta come sostanza, ma indichiamo la rata mensile.",
    "Comproprietà": "Lo possiedi con altre persone: dichiariamo la tua quota del valore.",
}


def _fr(x: float) -> str:
    return f"Fr. {x:,.0f}".replace(",", "'")


def _link_valore(v: Veicolo) -> None:
    """Pulsante che apre la ricerca di un mezzo simile sul sito di compravendita."""
    ricerca = f"{v.marca_modello} {v.anno_acquisto or ''}".strip()
    if v.tipo == "Auto":
        st.link_button(
            "Cerca un'auto simile su AutoScout24",
            f"https://www.google.com/search?q={quote_plus('site:autoscout24.ch ' + ricerca)}" if ricerca else "https://www.autoscout24.ch",
        )
    elif v.tipo == "Moto":
        st.link_button(
            "Cerca una moto simile su MotoScout24",
            f"https://www.google.com/search?q={quote_plus('site:motoscout24.ch ' + ricerca)}" if ricerca else "https://www.motoscout24.ch",
        )
    else:
        st.link_button(
            "Cerca una barca simile su Barca24",
            f"https://www.google.com/search?q={quote_plus('site:barca24.ch ' + ricerca)}" if ricerca else "https://www.barca24.ch",
        )


def _blocco(dichiarazione: DichiarazioneFiscale, v: Veicolo, i: int) -> None:
    with st.container(border=True):
        if v.tipo in ("Auto", "Moto"):
            v.tipo = st.radio("Tipo di veicolo", ["Auto", "Moto"], index=["Auto", "Moto"].index(v.tipo),
                              horizontal=True, key=f"vei_tipo_{i}")
        else:
            st.markdown("**Barca / natante**")

        v.modalita = st.selectbox("Come lo possiedi?", MODALITA, index=MODALITA.index(v.modalita), key=f"vei_mod_{i}")
        st.caption(DESCRIZIONE_MODALITA[v.modalita])

        v.marca_modello = st.text_input("Marca e modello", value=v.marca_modello, key=f"vei_marca_{i}",
                                        placeholder="es. BMW C650 GT" if v.tipo != "Barca" else "es. Bayliner VR5")
        col1, col2 = st.columns(2)
        with col1:
            v.anno_acquisto = int(st.number_input(
                "Anno di acquisto", min_value=1950, max_value=dichiarazione.anno_fiscale,
                value=v.anno_acquisto or dichiarazione.anno_fiscale - 3, step=1, format="%d", key=f"vei_anno_{i}",
            ))
        with col2:
            if v.tipo != "Barca":
                campo_con_fallback(v.prezzo_acquisto, "Prezzo di acquisto (facoltativo, Fr.)", key=f"vei_prezzo_{i}")

        if v.modalita == "Leasing":
            campo_con_fallback(v.rata_leasing, "Rata mensile del leasing (Fr.)", key=f"vei_rata_{i}")
        else:
            if v.modalita == "Comproprietà":
                v.quota_proprieta = float(st.number_input(
                    "La tua quota di proprietà (%)", min_value=1, max_value=100, step=1, format="%d",
                    value=int(round(v.quota_proprieta)) if 0 < v.quota_proprieta < 100 else 50, key=f"vei_quota_{i}",
                ))
            campo_con_fallback(
                v.valore_31_12, "Valore di mercato al 31.12 (Fr.)", key=f"vei_valore_{i}",
                aiuto="Quanto varrebbe oggi sul mercato dell'usato, non il prezzo di acquisto.",
            )
            st.caption("Puoi verificare il valore confrontandolo con mezzi simili in vendita su internet:")
            _link_valore(v)
            if v.modalita == "Comproprietà" and valore_veicolo(v):
                st.caption(f"Valore dichiarato (tua quota): {_fr(valore_veicolo(v))}")

        if st.button("Rimuovi questo mezzo", key=f"vei_rimuovi_{i}"):
            dichiarazione.veicoli.pop(i)
            st.rerun()


def render(dichiarazione: DichiarazioneFiscale) -> None:
    st.header("Veicoli e natanti")
    st.write(
        "Possiedi o usi un'**auto**, una **moto** o una **barca**? Sono parte della sostanza (leasing compreso: "
        "in quel caso indichiamo solo la rata). Se non ne hai, vai avanti."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("+ Aggiungi un'auto o una moto", key="vei_add_motore"):
            dichiarazione.veicoli.append(Veicolo(tipo="Auto"))
            st.rerun()
    with col_b:
        if st.button("+ Aggiungi una barca", key="vei_add_barca"):
            dichiarazione.veicoli.append(Veicolo(tipo="Barca"))
            st.rerun()

    for i, v in enumerate(dichiarazione.veicoli):
        _blocco(dichiarazione, v, i)

    r = calcolo_veicoli(dichiarazione)
    if dichiarazione.veicoli:
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Veicoli a motore (cifra 306)", _fr(r["tot_motore"]))
        c2.metric("Natanti (cifra 308)", _fr(r["tot_natanti"]))

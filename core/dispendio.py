"""
core/dispendio.py — calcolo del dispendio.

Idea: quanto si è potuto risparmiare nell'anno (redditi − spese e deduzioni)
deve bastare a spiegare quanto sono cresciuti conti e titoli rispetto
all'anno scorso. Se la liquidità è cresciuta più del risparmio, il fisco può
sospettare redditi non dichiarati.

    risparmio generato     = redditi − spese
    crescita spiegabile    = risparmio generato + altri movimenti di capitale noti
    variazione di liquidità = conti e titoli al 31.12 − conti e titoli dell'anno scorso
    RISULTATO              = crescita spiegabile − variazione di liquidità
    RISULTATO ≥ 0 → coerente;  RISULTATO < 0 → da verificare sul cash flow reale

Criterio prudente nelle scelte dubbie (una segnalazione in più costa meno di
un «tutto a posto» sbagliato):
- i redditi sono quelli che entrano in cassa: il valore locativo (reddito
  figurativo, non in contanti) è mostrato ma NON conteggiato;
- le spese includono tutte le deduzioni chieste che rappresentano una spesa
  (anche i forfait professionali); non le deduzioni sociali (figli, coniuge,
  doppio reddito), che non sono spese;
- i dividendi e gli interessi sono al lordo, ma si sottrae l'imposta
  preventiva già trattenuta alla fonte (35%): non è mai arrivata sui conti.
"""

from core.calcoli import (
    calcolo_immobile, calcolo_mod1, calcolo_mod2, calcolo_mod4, calcolo_mod5, calcolo_mod6,
    calcolo_mod8, numero, reddito_persona,
)


def _voce(etichetta: str, importo: float, nota: str = "") -> dict:
    return {"voce": etichetta, "importo": float(importo), "nota": nota}


def _nome(p) -> str:
    return f"{p.nome} {p.cognome}".strip()


def calcola_dispendio(d) -> dict:
    c = d.contribuente
    m1 = calcolo_mod1(d)
    m2 = calcolo_mod2(d)
    m4c, m4k = calcolo_mod4(d, "contribuente"), calcolo_mod4(d, "coniuge")
    m5, m6, m8 = calcolo_mod5(d), calcolo_mod6(d), calcolo_mod8(d)

    # ── Redditi ──────────────────────────────────────────────────────
    redditi = []
    r_contrib = reddito_persona(d, "contribuente")
    if r_contrib:
        redditi.append(_voce(f"Reddito da attività dipendente — {_nome(c) or 'contribuente'}", r_contrib, "salario netto"))
    if c.coniuge is not None:
        r_coniuge = reddito_persona(d, "coniuge")
        if r_coniuge:
            redditi.append(_voce(f"Reddito da attività dipendente — {_nome(c.coniuge) or 'coniuge'}", r_coniuge, "salario netto"))
    interessi = m2["tot_a"] + m2["tot_b"]
    if interessi:
        redditi.append(_voce("Interessi e redditi da conti e titoli", interessi, "al lordo"))
    if m8["tot_a_reddito_lordo"]:
        redditi.append(_voce("Dividendi da partecipazioni qualificate", m8["tot_a_reddito_lordo"], "al lordo"))
    affitti = 0.0
    valore_locativo = 0.0
    for imm in d.immobili:
        ci = calcolo_immobile(imm)
        affitti += ci["affitti_q"]
        valore_locativo += ci["valore_locativo_q"]
    if affitti:
        redditi.append(_voce("Affitti incassati", affitti, "immobili"))
    totale_redditi = sum(v["importo"] for v in redditi)

    # ── Spese e deduzioni ────────────────────────────────────────────
    spese = []
    if d.abita_in_affitto and numero(d.pigione_annua_netta):
        spese.append(_voce("Affitto dell'abitazione", numero(d.pigione_annua_netta), "pigione annua"))
    leasing = sum(numero(v.rata_leasing) * 12 for v in d.veicoli if v.modalita == "Leasing")
    if leasing:
        spese.append(_voce("Leasing dei veicoli", leasing, "rata mensile × 12"))
    prof = (m4c["totale"] if m4c["ha_dati"] else 0) + (m4k["totale"] if m4k["ha_dati"] else 0)
    if prof:
        spese.append(_voce("Spese professionali", prof, "Modulo 4, come dedotte"))
    premi = m6["malattia"] + m6["infortuni"] + m6["vita"] + m6["perdita_guadagno"]
    if premi:
        spese.append(_voce("Cassa malati, assicurazioni e spese mediche", premi, "importi effettivi, Modulo 6"))
    cura = sum(r["importo"] for r in m6["cura"])
    if cura:
        spese.append(_voce("Cura dei figli da terzi", cura, "importo pagato"))
    p3 = m1["deduzioni"].get(208, 0) + m1["deduzioni"].get(210, 0)
    if p3:
        spese.append(_voce("Versamenti al 3° pilastro A", p3, "come dedotti"))
    if m1["deduzioni"].get(214):
        spese.append(_voce("Spese di amministrazione dei titoli", m1["deduzioni"][214]))
    if m5["tot_interessi"]:
        spese.append(_voce("Interessi passivi (ipoteche e debiti)", m5["tot_interessi"], "Modulo 5"))
    manutenzione = 0.0
    for imm in d.immobili:
        ci = calcolo_immobile(imm)
        manutenzione += ci["spese_q"] if imm.usa_spese_effettive else ci["affitti_q"] * ci["forfait_pct"]
    if manutenzione:
        spese.append(_voce("Spese immobiliari", manutenzione, "manutenzione effettiva o forfait sugli affitti"))
    if m2["recupero_ip"] > 0:
        spese.append(_voce("Imposta preventiva trattenuta alla fonte (35%)", m2["recupero_ip"],
                           "mai accreditata sui conti: credito da recuperare"))
    altre = numero(d.dispendio_altre_spese)
    if altre:
        spese.append(_voce("Altre spese dell'anno indicate", altre, "es. imposte pagate, spese di vita"))
    totale_spese = sum(v["importo"] for v in spese)

    risparmio = totale_redditi - totale_spese

    # ── Altri movimenti di capitale (non sono redditi) ──────────────
    movimenti = []
    if d.eredita_ricevuta and numero(d.eredita_importo):
        movimenti.append(_voce("Eredità ricevuta", numero(d.eredita_importo)))
    ricevute = sum(numero(x.importo) for x in d.donazioni if x.direzione == "ricevuta")
    fatte = sum(numero(x.importo) for x in d.donazioni if x.direzione == "data")
    if ricevute:
        movimenti.append(_voce("Donazioni ricevute", ricevute))
    if fatte:
        movimenti.append(_voce("Donazioni fatte", -fatte))
    for imm in d.immobili:
        prezzo = numero(imm.prezzo_operazione) * calcolo_immobile(imm)["q_sos"]
        if imm.comprato_venduto_anno == "venduto" and prezzo:
            movimenti.append(_voce(f"Vendita immobile {imm.comune.valore or ''}".strip(), prezzo, "prezzo di vendita"))
        elif imm.comprato_venduto_anno == "comprato" and prezzo:
            movimenti.append(_voce(f"Acquisto immobile {imm.comune.valore or ''}".strip(), -prezzo, "prezzo di acquisto"))
    totale_movimenti = sum(v["importo"] for v in movimenti)

    # ── Liquidità: conti e titoli (righe del Modulo 2) ──────────────
    posizioni = [{"tipo": r["tipo"], "denominazione": r["denominazione"], "importo": r["sostanza"]} for r in m2["righe"]]
    liquidita_attuale = m2["tot_sostanza"]
    disponibile = bool((d.sostanza_titoli_anno_precedente.valore or "").strip())
    liquidita_precedente = numero(d.sostanza_titoli_anno_precedente) if disponibile else None
    variazione = (liquidita_attuale - liquidita_precedente) if disponibile else None

    crescita_spiegabile = risparmio + totale_movimenti
    risultato = (crescita_spiegabile - variazione) if disponibile else None

    return {
        "anno": d.anno_fiscale,
        "redditi": redditi, "totale_redditi": totale_redditi,
        "valore_locativo": valore_locativo,
        "spese": spese, "totale_spese": totale_spese,
        "risparmio": risparmio,
        "movimenti": movimenti, "totale_movimenti": totale_movimenti,
        "crescita_spiegabile": crescita_spiegabile,
        "posizioni": posizioni,
        "liquidita_attuale": liquidita_attuale, "liquidita_precedente": liquidita_precedente,
        "variazione": variazione,
        "calcolabile": disponibile,
        "risultato": risultato,
        "coerente": (risultato >= 0) if disponibile else None,
    }

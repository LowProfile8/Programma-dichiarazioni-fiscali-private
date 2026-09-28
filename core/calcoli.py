"""
core/calcoli.py — tutti i calcoli fiscali in un punto solo.

Wizard (per mostrare gli importi all'utente) e generatore dei moduli
(per scriverli nelle caselle) usano SEMPRE queste funzioni, così un numero
non può risultare diverso tra schermo e PDF.

Convenzioni: importi in franchi (float); gli arrotondamenti a franchi
interi (le caselle dei moduli non hanno decimali, tranne dove indicato)
si fanno con arrotondamento commerciale (0.5 → su).
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

# ── Costanti fiscali (anno 2025, fonte: moduli e istruzioni ufficiali) ────
TARIFFA_KM = 0.60
GIORNI_ANNO = 220
FORFAIT_PRINCIPALE = 3000
FORFAIT_ACCESSORIA = 800
BASE_OPERE_ASS_CONIUGATI = 10900
BASE_OPERE_ASS_ALTRI = 5500
SUPPL_FIGLIO = 1200
SUPPL_NO_PREVIDENZA_CONIUGATI = 4500
SUPPL_NO_PREVIDENZA_ALTRI = 2300
PLAFOND_CURA_TERZI_IC = 26200
DEDUZIONE_FIGLIO_IC = 11500
DEDUZIONE_CONIUGATI_SOSTANZA = 60000
DEDUZIONE_FIGLIO_SOSTANZA = 30000
PLAFOND_3P_CON_LPP = 7258
PLAFOND_3P_SENZA_LPP_MAX = 36288
ALIQUOTA_IMPOSTA_PREVENTIVA = 0.35
RIDUZIONE_PARTECIPAZIONI = 0.30


def numero(v) -> float:
    """Converte '1'234.50', '1 234,50', 1234, CampoValore o None in float (0.0 se vuoto/non valido)."""
    if v is None:
        return 0.0
    if hasattr(v, "valore"):
        v = v.valore
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    testo = str(v).strip().replace("'", "").replace("’", "").replace(" ", "").replace(" ", "")
    testo = testo.replace(",", ".")
    pulito = "".join(ch for ch in testo if ch.isdigit() or ch in ".-")
    if pulito in ("", "-", "."):
        return 0.0
    try:
        return float(pulito)
    except ValueError:
        return 0.0


def franchi_giu(x: float) -> int:
    """Franco inferiore (come fa eTax sul totale dei redditi da titoli: 202.94 → 202)."""
    import math
    return int(math.floor(x + 1e-9))


def franchi(x: float) -> int:
    """Arrotondamento commerciale a franchi interi."""
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# ══════════════════════════════════════════════════════════════════════
# Certificati di salario: mesi effettivi per ciascuna attività
# ══════════════════════════════════════════════════════════════════════
def _anno(d) -> int:
    return d.anno_fiscale


def periodo_certificati(d, persona: str = None) -> dict:
    """{uid: (inizio, fine)} — periodo di lavoro di ogni certificato, con le date esatte.

    - «tutto l'anno»: dal 01.01 al 31.12
    - continuazione «fino a fine anno»: dal giorno dopo la fine del lavoro precedente al 31.12
    - altrimenti: le date indicate (se mancano → None, si ricade sui mesi)"""
    anno = _anno(d)
    inizio_anno, fine_anno = date(anno, 1, 1), date(anno, 12, 31)
    risultato = {}
    ultima_fine = {}
    for cert in d.certificati_salario:
        if persona and cert.persona != persona:
            continue
        if cert.tipo_attivita == "accessoria":
            if cert.lavorato_tutto_anno:
                ini, fin = inizio_anno, fine_anno
            else:
                ini, fin = cert.data_inizio, cert.data_fine
        elif cert.auto_continuazione:
            precedente = ultima_fine.get(cert.persona)
            ini = cert.data_inizio or (precedente + timedelta(days=1) if precedente else None)
            fin = fine_anno if cert.lavorato_tutto_anno else cert.data_fine
        else:
            if cert.lavorato_tutto_anno:
                ini, fin = inizio_anno, fine_anno
            else:
                ini, fin = cert.data_inizio or inizio_anno, cert.data_fine
        risultato[cert.uid] = (ini, fin)
        if cert.tipo_attivita == "principale" and fin:
            ultima_fine[cert.persona] = fin
    return risultato


def mesi_certificati(d, persona: str = None) -> list:
    """[(certificato, mesi)] nell'ordine inserito (mesi anche frazionari, calcolati dai giorni esatti)."""
    periodi = periodo_certificati(d, persona)
    anno = _anno(d)
    risultato = []
    usati = {}
    for cert in d.certificati_salario:
        if persona and cert.persona != persona:
            continue
        ini, fin = periodi.get(cert.uid, (None, None))
        if ini and fin and fin >= ini:
            giorni = (min(fin, date(anno, 12, 31)) - max(ini, date(anno, 1, 1))).days + 1
            mesi = min(12.0, max(0.0, giorni / 365 * 12)) if giorni < 365 else 12.0
        elif cert.tipo_attivita == "accessoria" or not cert.auto_continuazione:
            mesi = 12 if cert.lavorato_tutto_anno else (cert.mesi_lavorati or 12)
        else:
            mesi = max(0, 12 - usati.get(cert.persona, 0)) if cert.lavorato_tutto_anno else (cert.mesi_lavorati or 12)
        if cert.tipo_attivita == "principale":
            usati[cert.persona] = usati.get(cert.persona, 0) + mesi
        risultato.append((cert, min(12.0, mesi)))
    return risultato


def durata_attivita(d, persona: str) -> dict:
    """Riquadro 1 del Modulo 4: 'annuale' oppure 'inferiore all'anno' dal … al … (date complete)."""
    anno = _anno(d)
    periodi = periodo_certificati(d, persona)
    principali = [c for c in d.certificati_salario if c.persona == persona and c.tipo_attivita == "principale"]
    inizi = [periodi[c.uid][0] for c in principali if periodi.get(c.uid, (None, None))[0]]
    fini = [periodi[c.uid][1] for c in principali if periodi.get(c.uid, (None, None))[1]]
    tot_mesi = sum(m for c, m in mesi_certificati(d, persona) if c.tipo_attivita == "principale")
    if not principali:
        return {"annuale": False, "dal": None, "al": None}
    if tot_mesi >= 11.99 or (inizi and fini and min(inizi) <= date(anno, 1, 1) and max(fini) >= date(anno, 12, 31)
                              and tot_mesi >= 11.99):
        return {"annuale": True, "dal": None, "al": None}
    return {"annuale": False, "dal": min(inizi) if inizi else None, "al": max(fini) if fini else None}


def certificati_persona(d, persona: str) -> list:
    return [c for c in d.certificati_salario if c.persona == persona]


def reddito_persona(d, persona: str, solo_principale: bool = False) -> float:
    return sum(
        numero(c.cifra_11_salario_netto) for c in d.certificati_salario
        if c.persona == persona and (not solo_principale or c.tipo_attivita == "principale")
    )


def figli_a_carico(d) -> list:
    """Figli deducibili: fino al 28° anno di età (età calcolata al 31.12)."""
    return [f for f in d.figli if f.anno_nascita and (d.anno_fiscale - f.anno_nascita) <= 28]


# ══════════════════════════════════════════════════════════════════════
# Modulo 4 — spese professionali (contribuente)
# ══════════════════════════════════════════════════════════════════════
BICICLETTA_MAX = 700
PASTO_FUORI_CASA = 15.0
PASTO_FUORI_CASA_MAX = 3200
PASTO_MENSA = 7.5
PASTO_MENSA_MAX = 1600


def calcolo_mod4(d, persona: str = "contribuente") -> dict:
    """Spese professionali di UNA persona (contribuente o coniuge: il Modulo 4 ha una pagina ciascuno).

    Mezzo di trasporto per ogni attività principale:
      auto/moto  → riga della tabella 2.2 (km × 0.60), cifra 402
      pubblico   → abbonamento annuo effettivo, cifra 400
      bici       → forfait Fr. 700 (ridotto ai mesi lavorati), cifra 404
      nessuno    → nessuna deduzione di trasporto"""
    righe, abbonamenti = [], []
    giorni_totali = 0
    bici = 0.0
    forfait_principale = 0.0
    forfait_accessoria = 0.0
    grado = 100
    for cert, mesi in mesi_certificati(d, persona):
        if cert.tipo_attivita == "accessoria":
            forfait_accessoria = FORFAIT_ACCESSORIA        # forfait fisso, una sola volta (riga 6.1)
            continue
        grado = cert.grado_occupazione or 100
        forfait_principale = FORFAIT_PRINCIPALE            # forfait fisso, una sola volta (riga 5.1)
        giorni_totali += round(GIORNI_ANNO * mesi / 12 * grado / 100)   # giorni lavorati di questo lavoro
        mezzo = cert.mezzo_trasporto
        if mezzo == "auto":
            giorni = round(GIORNI_ANNO * mesi / 12 * grado / 100)
            km = numero(cert.km_tragitto)
            km_giorno = km * 2
            righe.append({
                "cert": cert, "mesi": mesi, "giorni": giorni, "km_tragitto": km,
                "km_giorno": km_giorno, "km_totali": km_giorno * giorni,
                "comune_lavoro": cert.comune_datore_lavoro.valore or "",
            })
        elif mezzo == "pubblico":
            abbonamenti.append({"cert": cert, "mesi": mesi, "importo": numero(cert.abbonamento_importo),
                                "comune_lavoro": cert.comune_datore_lavoro.valore or ""})
        elif mezzo == "bici":
            bici = BICICLETTA_MAX                          # forfait fisso Fr. 700
    km_totali_tot = sum(r["km_totali"] for r in righe)
    trasporto = franchi(km_totali_tot * TARIFFA_KM)

    # 3.1 pasti principali fuori casa: predefiniti, sui giorni lavorati (somma dei lavori, al massimo 220)
    anagrafica = d.contribuente if persona == "contribuente" else d.contribuente.coniuge
    giorni_pasti = min(GIORNI_ANNO, giorni_totali)
    pasti = 0
    if anagrafica is not None and anagrafica.pasti_fuori_casa and giorni_pasti > 0:
        if anagrafica.pasti_con_mensa:
            pasti = franchi(min(giorni_pasti * PASTO_MENSA, PASTO_MENSA_MAX))
        else:
            pasti = franchi(min(giorni_pasti * PASTO_FUORI_CASA, PASTO_FUORI_CASA_MAX))
    pubblico = franchi(sum(a["importo"] for a in abbonamenti))
    bici_f = franchi(bici)
    f_princ = franchi(forfait_principale)
    f_access = franchi(forfait_accessoria)
    return {
        "persona": persona,
        "righe": righe, "abbonamenti": abbonamenti, "grado": grado,
        "km_totali": km_totali_tot,
        "pubblico": pubblico,            # cifra 400
        "trasporto": trasporto,          # cifra 402
        "bici": bici_f,                  # cifra 404
        "giorni_pasti": giorni_pasti if pasti else 0,
        "pasti": pasti,                  # cifra 408
        "pasti_con_mensa": bool(anagrafica is not None and anagrafica.pasti_con_mensa),
        "forfait_principale": f_princ,   # cifra 420
        "forfait_accessoria": f_access,  # cifra 432
        "totale": pubblico + trasporto + bici_f + pasti + f_princ + f_access,  # cifra 438 (488 per il coniuge)
        "ha_dati": bool(certificati_persona(d, persona)),
        "durata": durata_attivita(d, persona),
        "periodi": periodo_certificati(d, persona),
    }


# ══════════════════════════════════════════════════════════════════════
# Modulo 6 — oneri assicurativi
# ══════════════════════════════════════════════════════════════════════
def calcolo_mod6(d) -> dict:
    malattia = sum(numero(cm.importo_annuo) for cm in d.cassa_malati)
    infortuni = numero(d.assicurazione_infortuni_privata)
    vita = numero(d.assicurazione_vita)
    # «Interessi su capitali a risparmio»: solo i conti di risparmio/libretti, non i conti correnti
    interessi_risparmio = sum(
        numero(c.interessi_redditi) for c in d.conti_correnti if c.tipo == "Conti risparmio/libretto"
    )
    perdita_guadagno = numero(d.assicurazione_perdita_guadagno_malattia)
    totale_a = malattia + infortuni + vita + interessi_risparmio + perdita_guadagno

    coniugati = d.contribuente.richiede_dati_coniuge()
    base = BASE_OPERE_ASS_CONIUGATI if coniugati else BASE_OPERE_ASS_ALTRI
    n_figli = len(figli_a_carico(d))
    suppl_figli = SUPPL_FIGLIO * n_figli
    # le condizioni per il supplemento devono valere per ENTRAMBI i coniugi: basta che uno abbia versato
    ha_previdenza = bool(d.terzo_pilastro_versato) or bool(d.terzo_pilastro_coniuge_versato) or any(
        c.cifra_10_contributi_lpp.valore for c in d.certificati_salario
    )
    suppl_prev = 0 if ha_previdenza else (SUPPL_NO_PREVIDENZA_CONIUGATI if coniugati else SUPPL_NO_PREVIDENZA_ALTRI)
    totale_b = base + suppl_figli + suppl_prev

    # Cura prestata da terzi a figli < 14 anni (tabella in basso)
    cura = []
    for f in d.figli:
        if f.in_cura_da_terzi and numero(f.spese_cura_annuali) > 0:
            cura.append({"figlio": f, "importo": numero(f.spese_cura_annuali)})
    cura_totale = sum(min(r["importo"], PLAFOND_CURA_TERZI_IC) for r in cura)

    return {
        "malattia": malattia, "infortuni": infortuni, "vita": vita,
        "interessi_risparmio": interessi_risparmio, "perdita_guadagno": perdita_guadagno,
        "totale_a": totale_a,
        "coniugati": coniugati, "base": base, "n_figli": n_figli, "suppl_figli": suppl_figli,
        "suppl_no_previdenza": suppl_prev, "totale_b": totale_b,
        "ammessa": min(totale_a, totale_b),
        "cura": cura, "cura_totale": cura_totale,
    }


# ══════════════════════════════════════════════════════════════════════
# Modulo 8 — partecipazioni qualificate (sostanza privata)
# ══════════════════════════════════════════════════════════════════════
def calcolo_mod8(d) -> dict:
    righe = []
    for p in d.partecipazioni:
        if not p.detenuta_privatamente:
            continue  # Modulo 8.1, fuori scope
        lordo = numero(p.dividendi_lordo_totale) if p.ha_ricevuto_dividendi else 0.0
        righe.append({
            "p": p,
            "nominale": numero(p.capitale_sociale),
            "quota": p.quota_percentuale or 0.0,
            "descrizione": p.denominazione.valore or "",
            "valore_fiscale": numero(p.valore_fiscale),
            "reddito_lordo": lordo,
        })
    tot_sostanza = sum(r["valore_fiscale"] for r in righe)
    tot_lordo = sum(r["reddito_lordo"] for r in righe)
    recupero = tot_lordo * ALIQUOTA_IMPOSTA_PREVENTIVA
    riduzione = tot_lordo * RIDUZIONE_PARTECIPAZIONI
    return {
        "righe": righe,
        "tot_a_sostanza": tot_sostanza, "tot_a_reddito_lordo": tot_lordo,
        "recupero_ip": recupero,              # 35% del Totale A (reddito lordo)
        "tot_c_sostanza": tot_sostanza, "tot_c_reddito_lordo": tot_lordo,
        "riduzione_30": riduzione,            # cifra 801
        "tot_d_reddito_netto": tot_lordo - riduzione,
        "ricevuto_netto": tot_lordo - recupero,  # quanto è già arrivato in banca (65%)
    }


# ══════════════════════════════════════════════════════════════════════
# Modulo 2 — elenco titoli (pagina 2)
# ══════════════════════════════════════════════════════════════════════
_CODICI_TIPO = {
    "Conti correnti": "CC", "Conti per garanzia affitto": "CC", "Conti risparmio/libretto": "LR",
    "Conto corrente postale": "CC", "Conto privato": "CC",
    "Azioni": "A", "Obbligazioni": "OB", "Fondi d'investimento": "FI",
    "Estratto fiscale deposito titoli": "DT", "Prestiti": "PR",
}


def codice_tipo_mod2(tipo: str) -> str:
    """Abbreviazione ufficiale per la colonna 4; ciò che non ha un codice
    dedicato va sotto 'AV — Altri valori e crediti'."""
    return _CODICI_TIPO.get(tipo, "AV")


def calcolo_mod2(d) -> dict:
    righe = []

    def aggiungi(pos, tipo_codice=None):
        quota = pos.quota_proprieta if pos.titolarita == "cointestato" else 100.0
        f = quota / 100.0
        reddito = numero(pos.interessi_redditi) * f
        soggetto = bool(pos.interessi_soggetti_ip)
        righe.append({
            "classificazione": "P",
            "tipo": pos.tipo,
            "numero": pos.iban_numero_conto.valore or "",
            "codice": tipo_codice or codice_tipo_mod2(pos.tipo),
            "denominazione": pos.istituto.valore or "",
            "quota": None if quota == 100.0 else quota,
            "sostanza": numero(pos.saldo_valore_31_12) * f,
            "reddito_a": reddito if soggetto else 0.0,
            "reddito_b": 0.0 if soggetto else reddito,
            "nominale": numero(pos.quantita_nominale),
        })

    for c in d.conti_correnti:
        aggiungi(c)
    for t in d.titoli_investimenti:
        aggiungi(t)
    # Prestiti ATTIVI alla propria società: sono un credito → 'PR' nell'elenco titoli
    for deb in d.debiti:
        if deb.tipo == "prestito_sagl_attivo" and numero(deb.saldo_31_12) > 0:
            righe.append({
                "classificazione": "P", "tipo": "Prestito alla società", "numero": "", "codice": "PR",
                "denominazione": deb.creditore.valore or "", "quota": None,
                "sostanza": numero(deb.saldo_31_12), "reddito_a": 0.0, "reddito_b": 0.0, "nominale": 0.0,
            })

    m8 = calcolo_mod8(d)
    tot_sostanza = sum(r["sostanza"] for r in righe)
    tot_a = sum(r["reddito_a"] for r in righe)
    tot_b = sum(r["reddito_b"] for r in righe)
    mod8_sostanza = m8["tot_c_sostanza"]
    mod8_netto = m8["tot_d_reddito_netto"]
    return {
        "righe": righe,
        "tot_sostanza": tot_sostanza, "tot_a": tot_a, "tot_b": tot_b,
        "mod8_sostanza": mod8_sostanza, "mod8_reddito_netto": mod8_netto,
        "sostanza_da_riportare": tot_sostanza + mod8_sostanza,             # → Modulo 1 cifra 300
        "reddito_da_riportare": tot_b + tot_a + mod8_netto,                # → Modulo 1 cifra 150
        "recupero_ip": (tot_a + m8["tot_a_reddito_lordo"]) * ALIQUOTA_IMPOSTA_PREVENTIVA,  # cifra 999
    }


# ══════════════════════════════════════════════════════════════════════
# Modulo 5 — debiti
# ══════════════════════════════════════════════════════════════════════
def calcolo_mod5(d) -> dict:
    """Sezione A (debiti privati): ipoteche [I], finanziamenti [P] e prestiti
    PASSIVI dalla propria società (un debito personale verso la società [P])."""
    privati = []
    for deb in d.debiti:
        if deb.tipo == "ipoteca":
            genere = "I"
        elif deb.tipo in ("finanziamento", "prestito_sagl_passivo"):
            genere = "P"
        else:
            continue
        privati.append({
            "deb": deb, "genere": genere, "creditore": deb.creditore.valore or "",
            "importo": numero(deb.saldo_31_12), "interessi": numero(deb.interessi_annui),
        })
    return {
        "privati": privati,
        "tot_importo": sum(r["importo"] for r in privati),
        "tot_interessi": sum(r["interessi"] for r in privati),
    }


# ══════════════════════════════════════════════════════════════════════
# Modulo 7 — immobili
# ══════════════════════════════════════════════════════════════════════
def forfait_immobile(anno_costruzione: Optional[int]) -> float:
    if anno_costruzione is None:
        return 0.20
    return 0.10 if anno_costruzione >= 2015 else 0.20


def calcolo_immobile(imm) -> dict:
    stima = numero(imm.valore_stima_totale)
    valore_locativo = 0.0
    affitti = 0.0
    if imm.destinazione == "Uso proprio":
        pct = 0.90 if imm.abitazione_primaria else 0.63
        valore_locativo = numero(imm.valore_di_reddito) * pct
    elif imm.destinazione in ("Uso di terzi", "Uso misto"):
        affitti = numero(imm.affitti_incassati)
    lordo = valore_locativo + affitti
    forfait = forfait_immobile(imm.anno_costruzione)
    if imm.usa_spese_effettive:
        spese = sum(numero(s) for s in imm.spese_effettive)
    else:
        spese = lordo * forfait
    q_red = (imm.quota_reddito_contribuente / 100.0) if not imm.piena_proprieta else 1.0
    q_sos = (imm.quota_sostanza_contribuente / 100.0) if not imm.piena_proprieta else 1.0
    return {
        "stima": stima, "valore_locativo": valore_locativo, "affitti": affitti, "lordo": lordo,
        "spese": spese, "forfait_pct": forfait, "netto": lordo - spese,
        "q_red": q_red, "q_sos": q_sos,
        # quote del contribuente (per il Modulo 1)
        "stima_q": stima * q_sos, "valore_locativo_q": valore_locativo * q_red,
        "affitti_q": affitti * q_red, "lordo_q": lordo * q_red, "spese_q": spese * q_red,
        "netto_q": (lordo - spese) * q_red,
    }


def calcolo_immobili(d) -> dict:
    """Somma delle quote del contribuente su tutti gli immobili (per il Modulo 1)."""
    tot = {k: 0.0 for k in ("stima", "vl_primaria", "vl_secondaria", "affitti", "lordo", "spese", "netto")}
    for imm in d.immobili:
        c = calcolo_immobile(imm)
        tot["stima"] += c["stima_q"]
        if imm.destinazione == "Uso proprio":
            if imm.abitazione_primaria:
                tot["vl_primaria"] += c["valore_locativo_q"]
            else:
                tot["vl_secondaria"] += c["valore_locativo_q"]
        tot["affitti"] += c["affitti_q"]
        tot["lordo"] += c["lordo_q"]
        tot["spese"] += c["spese_q"]
        tot["netto"] += c["netto_q"]
    return tot


# ══════════════════════════════════════════════════════════════════════
# Veicoli a motore e natanti (sostanza mobiliare)
# ══════════════════════════════════════════════════════════════════════
def valore_veicolo(v) -> float:
    """Valore da dichiarare al 31.12: il leasing non è di proprietà (0); la comproprietà conta per la quota."""
    if v.modalita == "Leasing":
        return 0.0
    quota = (v.quota_proprieta or 100.0) / 100.0 if v.modalita == "Comproprietà" else 1.0
    return numero(v.valore_31_12) * quota


def descrizione_veicolo(v) -> str:
    testo = v.marca_modello.strip() or v.tipo
    if v.modalita == "Leasing":
        rata = numero(v.rata_leasing)
        testo += f" - Rata Mensile Leasing {rata:,.2f} CHF".replace(",", "'") if rata else " - Leasing"
    elif v.modalita == "Comproprietà":
        testo += f" (quota {v.quota_proprieta:g}%)"
    return testo


def calcolo_veicoli(d) -> dict:
    motore = [v for v in d.veicoli if v.tipo in ("Auto", "Moto")]
    natanti = [v for v in d.veicoli if v.tipo == "Barca"]
    return {
        "motore": motore, "natanti": natanti,
        "tot_motore": sum(valore_veicolo(v) for v in motore),      # cifra 306
        "tot_natanti": sum(valore_veicolo(v) for v in natanti),    # cifra 308
    }


# ══════════════════════════════════════════════════════════════════════
# Modulo 1 — pagine 4 (redditi), 5 (deduzioni), 6 (sostanza)
# ══════════════════════════════════════════════════════════════════════
def _terzo_pilastro(d, persona: str) -> float:
    """3° pilastro A dedotto per una persona, entro il plafond: Fr. 7'258 se ha la cassa pensione (LPP),
    altrimenti il 20% del reddito da attività lucrativa, al massimo Fr. 36'288."""
    if persona == "contribuente":
        versato, importo = d.terzo_pilastro_versato, d.terzo_pilastro_importo
    else:
        versato, importo = d.terzo_pilastro_coniuge_versato, d.terzo_pilastro_coniuge_importo
    if not versato:
        return 0.0
    ha_lpp = any(c.cifra_10_contributi_lpp.valore for c in certificati_persona(d, persona))
    plafond = PLAFOND_3P_CON_LPP if ha_lpp else min(0.20 * reddito_persona(d, persona), PLAFOND_3P_SENZA_LPP_MAX)
    return min(numero(importo), plafond)


DEDUZIONE_DOPPIO_REDDITO_MAX = 8100


def deduzione_doppio_reddito(d) -> float:
    """Cifra 15.5: coniugi che esercitano entrambi un'attività lucrativa: al massimo Fr. 8'100,
    ma solo fino a concorrenza del minore dei due redditi."""
    if not d.contribuente.richiede_dati_coniuge():
        return 0.0
    r1, r2 = reddito_persona(d, "contribuente"), reddito_persona(d, "coniuge")
    if r1 <= 0 or r2 <= 0:
        return 0.0
    return min(DEDUZIONE_DOPPIO_REDDITO_MAX, r1, r2)


def calcolo_mod1(d) -> dict:
    """Restituisce {cifra: valore} già arrotondati a franchi interi, più i totali."""
    m2 = calcolo_mod2(d)
    m4c = calcolo_mod4(d, "contribuente")
    m4k = calcolo_mod4(d, "coniuge")
    m5 = calcolo_mod5(d)
    m6 = calcolo_mod6(d)
    imm = calcolo_immobili(d)

    # ── Pagina 4: redditi ──
    redditi = {
        100: reddito_persona(d, "contribuente", solo_principale=True),
        102: reddito_persona(d, "coniuge", solo_principale=True),
        104: sum(numero(c.cifra_11_salario_netto) for c in certificati_persona(d, "contribuente") if c.tipo_attivita == "accessoria"),
        106: sum(numero(c.cifra_11_salario_netto) for c in certificati_persona(d, "coniuge") if c.tipo_attivita == "accessoria"),
        150: m2["reddito_da_riportare"],
        720: imm["vl_primaria"], 735: imm["vl_secondaria"], 736: imm["affitti"],
        738: imm["lordo"], 730: imm["spese"], 774: imm["netto"],
    }
    redditi_int = {k: franchi(v) for k, v in redditi.items()}
    redditi_int[150] = franchi_giu(redditi[150])   # come eTax: 202.94 → 202
    tot_redditi = (redditi_int[100] + redditi_int[102] + redditi_int[104] + redditi_int[106]
                   + redditi_int[150] + redditi_int[774])
    redditi_int[178] = tot_redditi

    # ── Pagina 5: deduzioni ──
    ded = {
        438: m4c["totale"] if m4c["ha_dati"] else 0.0,
        488: m4k["totale"] if m4k["ha_dati"] else 0.0,
        214: sum(numero(t.spese_amministrazione) for t in d.titoli_investimenti),
        208: _terzo_pilastro(d, "contribuente"),
        210: _terzo_pilastro(d, "coniuge"),
        600: m6["ammessa"],
        500: m5["tot_interessi"],
        230: deduzione_doppio_reddito(d),
    }
    ded_int = {k: franchi(v) for k, v in ded.items()}
    tot_ded = sum(ded_int.values())
    ded_int[236] = tot_ded
    n_figli = len(figli_a_carico(d))
    reddito_i = max(0, tot_redditi - tot_ded)                       # 240
    cura = franchi(m6["cura_totale"])                               # 253
    reddito_ii = max(0, reddito_i - cura)                           # 241
    reddito_iii = reddito_ii                                        # 242 (nessuna deduzione supplementare raccolta)
    ded_figli = DEDUZIONE_FIGLIO_IC * n_figli                       # 248
    reddito_iv = max(0, reddito_iii - ded_figli)                    # 256
    ded_int.update({
        17: tot_redditi, 18: tot_ded, 240: reddito_i, 253: cura, 241: reddito_ii,
        242: reddito_iii, 248: ded_figli, 256: reddito_iv, 264: reddito_iv,
    })

    # ── Pagina 6: sostanza ──
    sostanza_titoli = m2["sostanza_da_riportare"]                   # 300
    vita = sum(numero(a.valore_fiscale) for a in d.assicurazioni_vita)   # 304
    sostanza_imm = imm["stima"]                                     # 740
    vei = calcolo_veicoli(d)
    tot_sostanza = (franchi(sostanza_titoli) + franchi(vita) + franchi(vei["tot_motore"])
                    + franchi(vei["tot_natanti"]) + franchi(sostanza_imm))                # 322
    debiti = franchi(m5["tot_importo"])                             # 504
    netta = max(0, tot_sostanza - debiti)                           # 330
    ded_coniugati = DEDUZIONE_CONIUGATI_SOSTANZA if d.contribuente.richiede_dati_coniuge() else 0   # 334
    figli_minorenni = [f for f in d.figli if f.anno_nascita and (d.anno_fiscale - f.anno_nascita) < 18]
    ded_figli_sost = DEDUZIONE_FIGLIO_SOSTANZA * len(figli_minorenni)    # 336
    imponibile_sost = max(0, netta - ded_coniugati - ded_figli_sost)     # 340
    sostanza = {
        300: franchi(sostanza_titoli), 304: franchi(vita), 306: franchi(vei["tot_motore"]),
        308: franchi(vei["tot_natanti"]), 740: franchi(sostanza_imm), 322: tot_sostanza,
        504: debiti, 330: netta, 334: ded_coniugati, 336: ded_figli_sost, 340: imponibile_sost,
    }

    return {
        "redditi": redditi_int,
        "deduzioni": ded_int,
        "sostanza": sostanza,
        "recupero_ip": m2["recupero_ip"],   # cifra 999 (pagina 3)
    }

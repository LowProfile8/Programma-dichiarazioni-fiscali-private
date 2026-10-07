"""
core/models.py

Strutture dati principali. CampoValore è il concetto centrale: ogni valore
che l'utente inserisce nel wizard passa da qui, non da una semplice stringa,
perché dobbiamo poter distinguere:
  - un valore inserito ora, dal documento dell'anno corrente
  - un valore preso dall'anno scorso come ripiego (da segnalare e rivalutare)
così l'interfaccia sa sempre se mostrare l'avviso ⚠️ o no.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class StatoCivile(str, Enum):
    CELIBE_NUBILE = "Celibe/Nubile"
    CONIUGATO = "Coniugato/a"
    SEPARATO = "Separato/a"
    DIVORZIATO = "Divorziato/a"
    VEDOVO = "Vedovo/a"
    UNIONE_DOMESTICA = "Unione domestica registrata"


class GenereAttivita(str, Enum):
    DIPENDENTE = "Dipendente"
    INDIPENDENTE = "Indipendente"
    STUDENTE = "Studente"
    PENSIONATO = "Pensionato/a"
    ALTRO = "Altro"
    BENEFICIARIO_PRESTAZIONI = "Beneficiario/a di prestazioni complementari"


class TipoDocumento(str, Enum):
    CERTIFICATO_SALARIO = "certificato_salario"
    ATTESTATO_CONTO = "attestato_conto"
    SCHEDA_STIMA = "scheda_stima"
    ATTESTATO_3_PILASTRO = "attestato_3_pilastro"


@dataclass
class CampoValore:
    """Un valore inserito dall'utente, con tracciabilità della provenienza.

    origine:
      'utente'        -> inserito/confermato manualmente per l'anno corrente
      'anno_precedente' -> preso dalla dichiarazione dell'anno scorso come
                            ripiego: va sempre mostrato con l'avviso ⚠️
    """
    valore: Optional[str] = None
    origine: str = "utente"  # 'utente' | 'anno_precedente'
    nota: Optional[str] = None  # es. dove è stato trovato nel PDF dell'anno scorso

    @property
    def da_rivedere(self) -> bool:
        return self.origine == "anno_precedente"


@dataclass
class DatiPersonaFisica:
    """Blocco anagrafico riusato identico per contribuente e coniuge —
    stessa struttura, popolata due volte quando c'è un coniuge/partner."""
    cognome: str = ""
    nome: str = ""
    data_nascita: Optional[date] = None
    domicilio: str = ""
    professione: str = ""
    genere_attivita: list = field(default_factory=list)  # lista di GenereAttivita
    luogo_lavoro: str = ""  # composto: "ragione sociale, comune" (usato nell'output)
    attivita_accessoria: str = ""
    npa: str = ""  # codice postale del comune di domicilio
    datore_lavoro: str = ""  # ragione sociale
    comune_lavoro: str = ""
    indirizzo: str = ""  # via e numero di residenza
    pasti_fuori_casa: bool = True   # Modulo 4, 3.1: pasto principale consumato fuori casa
    pasti_con_mensa: bool = False   # mensa / contributo del datore di lavoro (Fr. 7.50, max 1'600)
    lavoro_a_turni: bool = False    # Modulo 4, 3.2: turni o lavoro notturno di almeno 8 ore consecutive
    rimborso_rappresentanza: bool = False   # il datore rimborsa a forfait le spese di rappresentanza: niente forfait Fr. 3'000
    domicilio_cambiato: bool = False   # ha cambiato casa durante l'anno (stesso lavoro)
    domicilio_secondario: str = ""     # comune della seconda casa
    data_cambio_domicilio: Optional[date] = None   # primo giorno nella seconda casa


@dataclass
class Contribuente:
    cognome: str = ""
    nome: str = ""
    data_nascita: Optional[date] = None
    domicilio: str = ""
    professione: str = ""
    genere_attivita: list = field(default_factory=list)  # lista di GenereAttivita
    luogo_lavoro: str = ""  # composto: "ragione sociale, comune" (usato nell'output)
    attivita_accessoria: str = ""
    npa: str = ""  # codice postale del comune di domicilio
    datore_lavoro: str = ""  # ragione sociale
    comune_lavoro: str = ""
    indirizzo: str = ""  # via e numero di residenza
    pasti_fuori_casa: bool = True
    pasti_con_mensa: bool = False
    lavoro_a_turni: bool = False
    rimborso_rappresentanza: bool = False
    ufficio_tassazione: str = ""  # codice "UT n" stampato accanto al Comune (varia da comune a comune)
    domicilio_cambiato: bool = False
    domicilio_secondario: str = ""
    data_cambio_domicilio: Optional[date] = None
    telefono: str = ""
    email: str = ""
    stato_civile: Optional[StatoCivile] = None
    coniuge: Optional[DatiPersonaFisica] = None  # None finché stato_civile non lo richiede

    def richiede_dati_coniuge(self) -> bool:
        return self.stato_civile in (StatoCivile.CONIUGATO, StatoCivile.UNIONE_DOMESTICA)


@dataclass
class Figlio:
    nome: str = ""
    anno_nascita: Optional[int] = None
    professione_attivita: str = ""
    vive_in_comunione: bool = True
    in_cura_da_terzi: Optional[bool] = None
    nome_istituto_cura: str = ""
    spese_cura_annuali: CampoValore = field(default_factory=CampoValore)
    file_fatture_cura: Optional[str] = None  # nome file, se allegato
    agli_studi: Optional[bool] = None   # (vecchio) resta per i salvataggi precedenti: equivale a formazione = 'scuola'
    scuola_luogo: Optional[str] = None  # 'stesso_comune' | 'stesso_cantone' | 'fuori_cantone'
    # Dai 18 anni (fino al 28°): '' (nessuna) | 'tirocinio' | 'scuola' (a tempo pieno) | 'universita' (studi accademici)
    formazione: str = ""
    alloggio_fuori_famiglia: bool = False   # non rientra ogni giorno a casa (alloggia fuori famiglia)
    borsa_oltre_1000: bool = False          # borse di studio / sussidi superiori a Fr. 1'000 l'anno


@dataclass
class CertificatoSalario:
    """Campi del certificato di salario rilevanti per il wizard.
    Ogni campo è un CampoValore, mai una stringa nuda."""
    datore_lavoro: CampoValore = field(default_factory=CampoValore)
    comune_datore_lavoro: CampoValore = field(default_factory=CampoValore)
    indirizzo_datore_lavoro: CampoValore = field(default_factory=CampoValore)
    presente_al_31_12: Optional[bool] = None
    cifra_1_salario_lordo: CampoValore = field(default_factory=CampoValore)
    cifra_10_contributi_lpp: CampoValore = field(default_factory=CampoValore)
    cifra_11_salario_netto: CampoValore = field(default_factory=CampoValore)
    file_origine: Optional[str] = None

    # Per il Modulo 4 (spese professionali) — distanza casa-lavoro e periodo
    km_tragitto: CampoValore = field(default_factory=CampoValore)
    km_tragitto_2: CampoValore = field(default_factory=CampoValore)  # tragitto dalla seconda casa, se domicilio_cambiato
    lavorato_tutto_anno: bool = True
    mesi_lavorati: Optional[int] = None  # (vecchio) usato solo se mancano le date esatte
    data_inizio: Optional[date] = None   # periodo di lavoro esatto, se non copre tutto l'anno
    data_fine: Optional[date] = None

    # Identificatore stabile (serve a dare chiavi univoche ai widget quando
    # i blocchi vengono aggiunti/rimossi) e ruolo del certificato
    uid: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    tipo_attivita: str = "principale"  # 'principale' | 'accessoria'
    auto_continuazione: bool = False  # True se aperto in automatico perché il precedente non copre tutto l'anno
    persona: str = "contribuente"  # 'contribuente' | 'coniuge'
    mezzo_trasporto: str = "auto"  # 'auto' | 'pubblico' | 'bici' | 'nessuno'
    veicolo_tragitto: str = "auto"  # se mezzo 'auto': 'auto' (0.60/km) | 'moto' (targa bianca, 0.40/km)
    abbonamento_importo: CampoValore = field(default_factory=CampoValore)  # solo se mezzo pubblico
    grado_occupazione: int = 100  # %
    telelavoro_percentuale: int = 0  # % media dei giorni lavorati da casa (non danno diritto a trasporto e pasti)


@dataclass
class ContoTitolo:
    """Una posizione del Modulo 2 (conto corrente/risparmio o titolo)."""
    istituto: CampoValore = field(default_factory=CampoValore)
    iban_numero_conto: CampoValore = field(default_factory=CampoValore)
    titolarita: str = "privato"  # privato | cointestato
    quota_proprieta: float = 100.0  # rilevante solo se titolarita == "cointestato"
    tipo: str = "conto corrente"  # conto corrente | conto risparmio | azioni | obbligazioni | fondo | altro
    quantita_nominale: CampoValore = field(default_factory=CampoValore)  # solo per titoli
    saldo_valore_31_12: CampoValore = field(default_factory=CampoValore)
    interessi_redditi: CampoValore = field(default_factory=CampoValore)
    # Il reddito è soggetto a imposta preventiva? (lo dice l'attestato) —
    # decide la colonna del Modulo 2: A (soggetti) o B (non soggetti)
    interessi_soggetti_ip: Optional[bool] = None
    # Spese di amministrazione/custodia del deposito (da attestato): deduzione cifra 214
    spese_amministrazione: CampoValore = field(default_factory=CampoValore)
    file_origine: Optional[str] = None


@dataclass
class AssicurazioneVita:
    """Assicurazione privata sulla vita / di rendita vitalizia con valore di riscatto
    (sostanza: Modulo 1, cifra 304)."""
    societa: str = ""
    anno_conclusione: Optional[int] = None
    anno_scadenza: Optional[int] = None
    somma_assicurata: CampoValore = field(default_factory=CampoValore)
    valore_fiscale: CampoValore = field(default_factory=CampoValore)  # valore di riscatto al 31.12
    file_origine: Optional[str] = None


@dataclass
class Veicolo:
    """Auto, moto o natante (sostanza mobiliare: Modulo 1, cifra 306 «Veicoli a motore» e 308 «Altri elementi»)."""
    tipo: str = "Auto"                 # 'Auto' | 'Moto' | 'Barca'
    modalita: str = "Comprato"         # 'Comprato' | 'Finanziamento' | 'Leasing' | 'Comproprietà'
    marca_modello: str = ""
    anno_acquisto: Optional[int] = None
    prezzo_acquisto: CampoValore = field(default_factory=CampoValore)   # facoltativo
    valore_31_12: CampoValore = field(default_factory=CampoValore)      # valore di mercato al 31.12
    rata_leasing: CampoValore = field(default_factory=CampoValore)      # rata mensile, solo leasing
    quota_proprieta: float = 100.0                                      # % , solo comproprietà


@dataclass
class Comproprietario:
    cognome_nome: str = ""
    anno_nascita: Optional[int] = None
    domicilio: str = ""
    quota_reddito: float = 0.0
    quota_sostanza: float = 0.0


@dataclass
class Immobile:
    """Un immobile — un blocco di questi per ogni proprietà (loop)."""
    in_svizzera: bool = True
    comune: CampoValore = field(default_factory=CampoValore)
    nazione_cantone: CampoValore = field(default_factory=CampoValore)
    indirizzo: CampoValore = field(default_factory=CampoValore)
    anno_costruzione: Optional[int] = None
    numero_registro_fondiario: str = ""  # facoltativo
    intestazione_registro_fondiario: str = ""  # obbligatoria in comproprietà: come risulta a registro fondiario
    destinazione: str = "Uso proprio"  # Uso proprio | Uso di terzi | Uso misto | In usufrutto/diritto di abitazione
    tipo_immobile: str = "Unifamiliare"

    comprato_venduto_anno: Optional[str] = None  # None | "comprato" | "venduto"
    data_operazione: Optional[date] = None
    prezzo_operazione: CampoValore = field(default_factory=CampoValore)
    finanziamento_operazione: CampoValore = field(default_factory=CampoValore)  # mutuo/ipoteca coinvolto (acceso o estinto)

    valore_stima_totale: CampoValore = field(default_factory=CampoValore)
    valore_di_reddito: CampoValore = field(default_factory=CampoValore)  # solo se uso proprio

    abitazione_primaria: bool = True  # rilevante solo se destinazione = Uso proprio
    affitti_incassati: CampoValore = field(default_factory=CampoValore)  # rilevante se Uso di terzi/misto

    usa_spese_effettive: bool = False
    spese_effettive: list = field(default_factory=list)  # list[CampoValore], se usa_spese_effettive

    piena_proprieta: bool = True
    comproprietari: list = field(default_factory=list)  # list[Comproprietario]
    quota_reddito_contribuente: float = 100.0
    quota_sostanza_contribuente: float = 100.0

    file_origine: Optional[str] = None


@dataclass
class Partecipazione:
    """Una partecipazione qualificata (≥10%) — Modulo 8."""
    denominazione: CampoValore = field(default_factory=CampoValore)
    capitale_sociale: CampoValore = field(default_factory=CampoValore)
    quota_percentuale: Optional[float] = None
    valore_fiscale: CampoValore = field(default_factory=CampoValore)  # input manuale, vedi nota in modules/partecipazioni.py
    ha_ricevuto_dividendi: Optional[bool] = None
    dividendi_lordo_totale: CampoValore = field(default_factory=CampoValore)
    detenuta_privatamente: bool = True  # False = attivo di ditta individuale, fuori scope v1
    file_origine: Optional[str] = None  # estratto del registro di commercio


@dataclass
class Debito:
    """Un debito/prestito — Modulo 5. tipo: 'ipoteca' | 'finanziamento' |
    'prestito_sagl_attivo' (il contribuente ha prestato soldi alla sua
    società) | 'prestito_sagl_passivo' (la società ha prestato soldi al
    contribuente)."""
    tipo: str = "ipoteca"
    creditore: CampoValore = field(default_factory=CampoValore)  # banca/finanziaria o nome società
    saldo_31_12: CampoValore = field(default_factory=CampoValore)
    interessi_annui: CampoValore = field(default_factory=CampoValore)
    file_origine: Optional[str] = None  # attestato fiscale, richiesto solo per ipoteca/finanziamento


@dataclass
class Donazione:
    direzione: str = "ricevuta"  # ricevuta | data
    controparte: str = ""
    indirizzo: str = ""
    grado_parentela: str = ""
    data: Optional[date] = None
    importo: CampoValore = field(default_factory=CampoValore)


@dataclass
class CassaMalati:
    """Una polizza di cassa malati — un blocco per persona (contribuente,
    coniuge, ogni figlio). L'importo è la somma di premio + eventuali
    fatture pagate elencate nel certificato di fine anno."""
    persona: str = "Contribuente"
    importo_annuo: CampoValore = field(default_factory=CampoValore)
    file_origine: Optional[str] = None



@dataclass
class PersonaBisognosa:
    """Persona bisognosa a carico (Istruzioni 2025, cifra 25.3): il contribuente la sostiene, per almeno
    Fr. 5'900 l'anno comprovati. Per l'imposta cantonale conta solo se risiede in Svizzera."""
    nome: str = ""
    anno_nascita: Optional[int] = None
    parentela: str = ""
    domicilio: str = ""
    residente_svizzera: bool = True
    onere_versato: CampoValore = field(default_factory=CampoValore)
    file_giustificativi: Optional[str] = None


@dataclass
class SpesaMalattia:
    """Una spesa di malattia o infortunio NON rimborsata (Modulo 6, retro)."""
    data: Optional[date] = None
    beneficiario: str = ""
    importo: CampoValore = field(default_factory=CampoValore)


@dataclass
class Liberalita:
    """Una liberalità a un ente di pubblica utilità (Modulo 5, retro)."""
    data: Optional[date] = None
    ente: str = ""
    importo: CampoValore = field(default_factory=CampoValore)


@dataclass
class AltriRedditiDeduzioni:
    """Voci del Modulo 1 che non vengono da un certificato di salario, da un conto o da un immobile.
    Ogni importo è in franchi, per l'anno fiscale. «_c» = contribuente, «_k» = coniuge/partner."""
    # ── Redditi (pagina 4 del Modulo 1) ──
    amministratore: CampoValore = field(default_factory=CampoValore)           # 1.3  (108)
    ind_principale_c: CampoValore = field(default_factory=CampoValore)         # 2.1  (112)
    ind_principale_k: CampoValore = field(default_factory=CampoValore)         #      (114)
    ind_accessoria_c: CampoValore = field(default_factory=CampoValore)         # 2.2  (116)
    ind_accessoria_k: CampoValore = field(default_factory=CampoValore)         #      (118)
    snc_c: CampoValore = field(default_factory=CampoValore)                    # 2.3  (120)
    snc_k: CampoValore = field(default_factory=CampoValore)                    #      (122)
    comunione_attivita: CampoValore = field(default_factory=CampoValore)       # 2.4  (162)
    perdite_precedenti: CampoValore = field(default_factory=CampoValore)       # 2.   (riquadro a sinistra)
    pens_prev_c: CampoValore = field(default_factory=CampoValore)              # 3.1  (126)
    pens_prev_k: CampoValore = field(default_factory=CampoValore)              #      (128)
    avs_ai_c: CampoValore = field(default_factory=CampoValore)                 # 3.2  (130)
    avs_ai_k: CampoValore = field(default_factory=CampoValore)                 #      (132)
    avs_ai_parziale: bool = False                                              # rendita parziale (quota esente limitata)
    rendite_c: CampoValore = field(default_factory=CampoValore)                # 3.3  (134)
    rendite_k: CampoValore = field(default_factory=CampoValore)                #      (136)
    perdita_guadagno_c: CampoValore = field(default_factory=CampoValore)       # 3.4  (138)
    perdita_guadagno_k: CampoValore = field(default_factory=CampoValore)       #      (140)
    giornaliere_c: CampoValore = field(default_factory=CampoValore)            # 3.5  (141)
    giornaliere_k: CampoValore = field(default_factory=CampoValore)            #      (142)
    alimenti_ricevuti_se: CampoValore = field(default_factory=CampoValore)     # 3.6  (144)
    alimenti_ricevuti_figli: CampoValore = field(default_factory=CampoValore)  #      (146)
    alimenti_pagante: str = ""                                                 # generalità e indirizzo di chi li versa
    altri_mobiliare: CampoValore = field(default_factory=CampoValore)          # 4.2  (154)
    altri_immobiliari: CampoValore = field(default_factory=CampoValore)        # 5.7  (158)
    diritti_autore: CampoValore = field(default_factory=CampoValore)           # 6.1  (166)
    vincite: CampoValore = field(default_factory=CampoValore)                  # 6.2  (152, riquadro: non si somma)
    altri_redditi: CampoValore = field(default_factory=CampoValore)            # 6.3  (168)
    altri_redditi_descrizione: str = ""
    # ── Deduzioni (pagina 5 del Modulo 1) ──
    riscatto_lpp_c: CampoValore = field(default_factory=CampoValore)           # 10.3 (204)
    riscatto_lpp_k: CampoValore = field(default_factory=CampoValore)
    alimenti_coniuge: CampoValore = field(default_factory=CampoValore)         # 14.1 (220)
    alimenti_figli: CampoValore = field(default_factory=CampoValore)           # 14.2 (222)
    oneri_permanenti: CampoValore = field(default_factory=CampoValore)         # 14.3 (224)
    rendite_pagate: CampoValore = field(default_factory=CampoValore)           # 14.4 (226)
    beneficiari: str = ""                                                      # a chi vanno (cifra 14)
    disabilita: CampoValore = field(default_factory=CampoValore)               # 15.1 (246)
    partiti: CampoValore = field(default_factory=CampoValore)                  # 15.2 (511)
    formazione_c: CampoValore = field(default_factory=CampoValore)             # 15.3 (426)
    formazione_k: CampoValore = field(default_factory=CampoValore)             # 15.4 (476)
    spese_malattia: list = field(default_factory=list)                         # list[SpesaMalattia]  → 22.1
    dieta_forfait: bool = False                                                # celiachia/dieta permanente: forfait Fr. 2'500
    liberalita: list = field(default_factory=list)                             # list[Liberalita]     → 24
    # Situazioni particolari che il programma non compila (solo promemoria nel riepilogo)
    casi_particolari: list = field(default_factory=list)                       # list[str]


@dataclass
class DichiarazioneFiscale:
    anno_fiscale: int
    pdf_anno_precedente_path: Optional[str] = None  # path locale, se caricato
    contribuente: Contribuente = field(default_factory=Contribuente)
    figli: list = field(default_factory=list)  # list[Figlio]
    certificati_salario: list = field(default_factory=list)  # list[CertificatoSalario]
    conti_correnti: list = field(default_factory=list)  # list[ContoTitolo], tipo conto
    titoli_investimenti: list = field(default_factory=list)  # list[ContoTitolo], tipo azioni/obbligazioni/fondo
    immobili: list = field(default_factory=list)  # list[Immobile]
    partecipazioni: list = field(default_factory=list)  # list[Partecipazione]
    debiti: list = field(default_factory=list)  # list[Debito]
    donazioni: list = field(default_factory=list)  # list[Donazione]

    # Modulo 6 — oneri assicurativi
    cassa_malati: list = field(default_factory=list)  # list[CassaMalati]
    assicurazione_infortuni_privata: CampoValore = field(default_factory=CampoValore)
    assicurazione_vita: CampoValore = field(default_factory=CampoValore)
    assicurazione_perdita_guadagno_malattia: CampoValore = field(default_factory=CampoValore)
    terzo_pilastro_versato: Optional[bool] = None
    terzo_pilastro_importo: CampoValore = field(default_factory=CampoValore)
    terzo_pilastro_file: Optional[str] = None

    # Informazioni complementari (Modulo 1, cifra 444)
    abita_in_affitto: Optional[bool] = None
    pigione_annua_netta: CampoValore = field(default_factory=CampoValore)  # senza spese accessorie
    proprietario_nome: str = ""
    proprietario_indirizzo: str = ""

    # Totali calcolati automaticamente (cache per il riepilogo, non dati utente)
    totale_modulo4: Optional[float] = None
    totale_modulo6_a: Optional[float] = None
    totale_modulo6_b: Optional[float] = None
    totale_modulo6_ammesso: Optional[float] = None
    totale_modulo8_sostanza: Optional[float] = None
    totale_modulo8_reddito_lordo: Optional[float] = None
    totale_modulo8_recupero_imposta: Optional[float] = None

    # Numero di registro (il «Numero registro» in alto nella prima pagina): facoltativo, uguale ogni anno
    numero_controllo: str = ""

    # 3° pilastro A del coniuge
    terzo_pilastro_coniuge_versato: Optional[bool] = None
    terzo_pilastro_coniuge_importo: CampoValore = field(default_factory=CampoValore)
    terzo_pilastro_coniuge_file: Optional[str] = None

    # Calcolo del dispendio: altre spese dell'anno non già presenti nella dichiarazione (facoltativo)
    dispendio_altre_spese: CampoValore = field(default_factory=CampoValore)

    # Veicoli a motore e natanti (cifre 306 e 308)
    veicoli: list = field(default_factory=list)  # list[Veicolo]

    # Assicurazioni sulla vita con valore di riscatto (cifra 304)
    assicurazioni_vita: list = field(default_factory=list)  # list[AssicurazioneVita]

    # Modulo 2, pagina 1: eredità, comunione ereditaria, società in nome collettivo
    eredita_ricevuta: bool = False
    eredita_defunto: str = ""
    eredita_grado: str = ""
    eredita_ultimo_domicilio: str = ""
    eredita_cantone: str = ""
    eredita_data_decesso: Optional[date] = None
    eredita_importo: CampoValore = field(default_factory=CampoValore)
    comunione_ereditaria: bool = False
    comunione_denominazione: str = ""
    comunione_importo: CampoValore = field(default_factory=CampoValore)
    societa_nome_collettivo: bool = False
    societa_ragione_sociale: str = ""

    # Persone bisognose a carico (cifra 25.3) e altri redditi/deduzioni (Modulo 1)
    persone_bisognose: list = field(default_factory=list)  # list[PersonaBisognosa]
    altri: AltriRedditiDeduzioni = field(default_factory=AltriRedditiDeduzioni)

    # Comunicazioni libere per l'Ufficio di tassazione (corrisponde
    # all'allegato "Note" di eTax)
    note_ufficio_tassazione: str = ""

    # Somma dei titoli/conti (Modulo 2, Totale colonna Sostanza) della
    # dichiarazione dell'anno precedente — usata per un confronto nel riepilogo
    sostanza_titoli_anno_precedente: CampoValore = field(default_factory=CampoValore)

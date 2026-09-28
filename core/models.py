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
    agli_studi: Optional[bool] = None
    scuola_luogo: Optional[str] = None  # 'stesso_comune' | 'stesso_cantone' | 'fuori_cantone'


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
    abbonamento_importo: CampoValore = field(default_factory=CampoValore)  # solo se mezzo pubblico
    grado_occupazione: int = 100  # %


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

    # Comunicazioni libere per l'Ufficio di tassazione (corrisponde
    # all'allegato "Note" di eTax)
    note_ufficio_tassazione: str = ""

    # Somma dei titoli/conti (Modulo 2, Totale colonna Sostanza) della
    # dichiarazione dell'anno precedente — usata per un confronto nel riepilogo
    sostanza_titoli_anno_precedente: CampoValore = field(default_factory=CampoValore)

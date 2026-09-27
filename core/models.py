"""
core/models.py

Strutture dati principali. CampoValore è il concetto centrale: ogni valore
che l'utente inserisce nel wizard passa da qui, non da una semplice stringa,
perché dobbiamo poter distinguere:
  - un valore inserito ora, dal documento dell'anno corrente
  - un valore preso dall'anno scorso come ripiego (da segnalare e rivalutare)
così l'interfaccia sa sempre se mostrare l'avviso ⚠️ o no.
"""

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
    luogo_lavoro: str = ""
    attivita_accessoria: str = ""


@dataclass
class Contribuente:
    cognome: str = ""
    nome: str = ""
    data_nascita: Optional[date] = None
    domicilio: str = ""
    professione: str = ""
    genere_attivita: list = field(default_factory=list)  # lista di GenereAttivita
    luogo_lavoro: str = ""
    attivita_accessoria: str = ""
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
    file_origine: Optional[str] = None


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
    destinazione: str = "Uso proprio"  # Uso proprio | Uso di terzi | Uso misto | In usufrutto/diritto di abitazione
    tipo_immobile: str = "Unifamiliare"

    comprato_venduto_anno: Optional[str] = None  # None | "comprato" | "venduto"
    data_operazione: Optional[date] = None
    prezzo_operazione: CampoValore = field(default_factory=CampoValore)

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

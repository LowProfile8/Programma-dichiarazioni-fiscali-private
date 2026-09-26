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
class Contribuente:
    cognome: str = ""
    nome: str = ""
    data_nascita: Optional[date] = None
    domicilio: str = ""
    professione: str = ""
    genere_attivita: list = field(default_factory=list)  # lista di GenereAttivita
    luogo_lavoro: str = ""
    attivita_accessoria: str = ""


@dataclass
class Figlio:
    nome: str = ""
    anno_nascita: Optional[int] = None
    professione_attivita: str = ""
    vive_in_comunione: bool = True
    in_cura_da_terzi: Optional[bool] = None
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
    tipo: str = "conto corrente"  # conto corrente | conto risparmio | azioni | obbligazioni | fondo | altro
    quantita_nominale: CampoValore = field(default_factory=CampoValore)  # solo per titoli
    saldo_valore_31_12: CampoValore = field(default_factory=CampoValore)
    interessi_redditi: CampoValore = field(default_factory=CampoValore)
    file_origine: Optional[str] = None


@dataclass
class DichiarazioneFiscale:
    anno_fiscale: int
    pdf_anno_precedente_path: Optional[str] = None  # path locale, se caricato
    contribuente: Contribuente = field(default_factory=Contribuente)
    figli: list = field(default_factory=list)  # list[Figlio]
    certificati_salario: list = field(default_factory=list)  # list[CertificatoSalario]
    conti_titoli: list = field(default_factory=list)  # list[ContoTitolo]

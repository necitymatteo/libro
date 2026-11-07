import pytest

from libro import deposito


class MotoreFinto:
    """Risponde con le risposte preparate dal test, nell'ordine, e registra i prompt."""

    def __init__(self):
        self.risposte = []
        self.chiamate = []

    def __call__(self, sistema, prompt, schema, modello):
        self.chiamate.append({"sistema": sistema, "prompt": prompt, "modello": modello})
        if not self.risposte:
            raise AssertionError("Il test non ha preparato questa chiamata al motore.")
        risposta = self.risposte.pop(0)
        if isinstance(risposta, Exception):
            raise risposta
        return risposta


@pytest.fixture(autouse=True)
def dati(tmp_path, monkeypatch):
    monkeypatch.setenv("LIBRO_DATI", str(tmp_path / "dati"))
    monkeypatch.setenv("LIBRO_PORTA", "8765")
    return tmp_path / "dati"


@pytest.fixture
def motore(monkeypatch):
    finto = MotoreFinto()
    monkeypatch.setattr("libro.motore.chiedi_json", finto)
    return finto


@pytest.fixture
def mappa():
    valore = {
        **deposito.MAPPA_VUOTA,
        "titolo": "Libro di prova",
        "capitoli": [
            {"id": 1, "titolo": "Il porto", "tema": "Lavoro", "materiale": "", "stato": "vuoto"},
            {"id": 2, "titolo": "La scuola", "tema": "Studio", "materiale": "", "stato": "vuoto"},
        ],
        "buchi": [{"id": "b1", "testo": "Chi era il cuoco?", "chiuso": False, "capitolo": None}],
        "contraddizioni": [{"id": "c1", "testo": "Due date diverse", "risolta": False}],
    }
    deposito.salva_mappa(valore)
    return valore


def ricordo(testo="Lavoravo al porto", citazione="lavoravo al porto ogni estate", capitolo=1,
            persone=None, privacy="libro"):
    return {
        "testo": testo, "citazione": citazione, "capitolo": capitolo,
        "persone": persone or [], "periodo": "", "tipo": "fatto", "privacy": privacy,
    }


def risposta_archivista(ricordi=None, **altro):
    return {
        "ricordi": ricordi or [], "capitoli": [], "buchi_nuovi": [], "buchi_chiusi": [],
        "contraddizioni_nuove": [], "contraddizioni_risolte": [], "ricordi_superati": [],
        **altro,
    }


def cambiamento(**altro):
    return risposta_archivista(**altro)

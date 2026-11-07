import pytest

from libro import agenti, deposito, motore, scrivi


def _salva(capitolo_id):
    frase = {"testo": "Testo privato.", "fonti": ["r0001"], "connettivo": False, "segnalazioni": []}
    return deposito.salva_versione(
        capitolo_id,
        [{"id": "p1", "autore": "scrittore", "frasi": [frase]}],
        controllo="eseguito",
        autore="scrittore",
    )


@pytest.fixture
def lancia(monkeypatch):
    chiamati = []

    def finta(capitolo_id):
        chiamati.append(capitolo_id)
        return _salva(capitolo_id)

    monkeypatch.setattr(agenti, "scrivi_bozza", finta)
    monkeypatch.setattr(scrivi, "_app_accesa", lambda: False)

    def esegui(*argomenti):
        monkeypatch.setattr("sys.argv", ["scrivi", *argomenti])
        return scrivi.main(), chiamati

    return esegui


def test_tutte_riscrive_solo_chi_ha_gia_una_bozza(lancia, mappa, capsys):
    _salva(1)
    esito, chiamati = lancia("--tutte")
    assert esito == 0 and chiamati == [1]
    assert deposito.versioni(1) == [1, 2] and deposito.versioni(2) == []
    assert "Testo privato" not in capsys.readouterr().out


def test_senza_opzioni_scrive_solo_chi_non_ha_bozza(lancia, mappa, monkeypatch):
    _salva(1)
    monkeypatch.setattr(agenti, "capitoli_senza_bozza", lambda: [2])
    esito, chiamati = lancia()
    assert esito == 0 and chiamati == [2]


def test_con_l_app_accesa_non_scrive_niente(lancia, mappa, monkeypatch, capsys):
    _salva(1)
    monkeypatch.setattr(scrivi, "_app_accesa", lambda: True)
    esito, chiamati = lancia("--tutte")
    assert esito == 1 and chiamati == []
    assert deposito.versioni(1) == [1]
    assert "Chiudila" in capsys.readouterr().out


def test_un_errore_non_ferma_gli_altri(lancia, mappa, monkeypatch, capsys):
    _salva(1)
    _salva(2)
    chiamati = []

    def finta(capitolo_id):
        chiamati.append(capitolo_id)
        if capitolo_id == 1:
            raise motore.ErroreMotore("Limite raggiunto.")
        return _salva(capitolo_id)

    monkeypatch.setattr(agenti, "scrivi_bozza", finta)
    esito, _ = lancia("--tutte")
    assert esito == 1 and chiamati == [1, 2]
    assert "Limite raggiunto." in capsys.readouterr().out

import pytest

from libro import controlli


def test_una_citazione_vera_passa_anche_con_spazi_e_apostrofi_diversi():
    fonte = "Quella  sera\nl'aria era   ferma e nessuno parlava."
    assert controlli.citazione_valida("Quella sera l’aria era ferma", fonte)


@pytest.mark.parametrize("citazione", [
    "Quella sera pioveva forte",  # inventata
    "sera",  # troppo corta
    "",
])
def test_una_citazione_inventata_non_passa(citazione):
    assert not controlli.citazione_valida(citazione, "Quella sera l'aria era ferma")


# Frasi scritte apposta per provare il controllo: non sono di nessuno.
@pytest.mark.parametrize("testo", [
    "Prova: certe sere vorrei morire", "Prova: non voglio più vivere così",
    "Prova: ho pensato di farla finita", "PROVA: VOGLIO MORIRE",
])
def test_i_segnali_di_disagio_si_vedono(testo):
    assert controlli.segnali_disagio(testo)


@pytest.mark.parametrize("testo", [
    "Il nonno Bruno è morto quando ero a Bologna", "A scuola tutti ridevano", "Ho finito il capitolo",
])
def test_un_ricordo_doloroso_non_e_un_segnale(testo):
    assert not controlli.segnali_disagio(testo)


def test_dividi_testo_non_perde_niente_e_rispetta_il_limite():
    testo = "\n\n".join(f"Paragrafo {i} " + "parola " * 40 for i in range(30))
    pezzi = controlli.dividi_testo(testo, 1000)
    assert len(pezzi) > 1
    assert all(len(p) <= 1000 for p in pezzi)
    assert "".join(pezzi) == testo


def test_dividi_testo_lascia_intero_un_testo_corto():
    assert controlli.dividi_testo("corto", 1000) == ["corto"]


def test_dividi_testo_taglia_anche_un_blocco_senza_righe_vuote():
    testo = "x" * 2500
    pezzi = controlli.dividi_testo(testo, 1000)
    assert "".join(pezzi) == testo and all(len(p) <= 1000 for p in pezzi)


def test_una_buona_domanda_passa():
    assert controlli.problemi_domanda("Chi c'era quel giorno?", []) == []


@pytest.mark.parametrize("domanda", [
    "", "Chi c'era? E che ora era?", "Dimmi chi c'era.",
    "Chi " + "molto " * 40 + "c'era?",
])
def test_una_domanda_sbagliata_non_passa(domanda):
    assert controlli.problemi_domanda(domanda, [])


def test_una_domanda_gia_fatta_non_passa():
    assert controlli.problemi_domanda("Chi c'era quel giorno?", ["Chi c'era quel giorno ?"])


def test_una_frase_con_fonti_coerenti_passa():
    fonti = ["A nove anni partii per Trieste"]
    assert controlli.controlla_frase("Avevo 9 anni e andavo a Trieste.", fonti, False) == []


def test_un_numero_inventato_viene_segnalato():
    problemi = controlli.controlla_frase("Avevo 14 anni.", ["Avevo nove anni"], False)
    assert any("14" in p for p in problemi)


def test_un_nome_inventato_viene_segnalato():
    problemi = controlli.controlla_frase("Quel giorno arrivò Giovanni.", ["Quel giorno arrivò mio zio"], False)
    assert any("Giovanni" in p for p in problemi)


def test_un_nome_dopo_un_apostrofo_viene_controllato():
    problemi = controlli.controlla_frase("Partii per l'Islanda.", ["Partii per Trieste"], False)
    assert any("Islanda" in p for p in problemi)


def test_la_maiuscola_a_inizio_frase_o_discorso_non_e_un_nome():
    assert controlli.controlla_frase(
        "Pioveva. Nessuno parlava. Disse: «Basta».", ["pioveva nessuno parlava disse basta"], False,
    ) == []


def test_una_frase_senza_fonte_viene_segnalata():
    assert controlli.controlla_frase("Pioveva.", [], False)


def test_un_collegamento_senza_fatti_passa_ma_con_un_nome_no():
    assert controlli.controlla_frase("Poi tutto cambiò.", [], True) == []
    assert controlli.controlla_frase("Poi arrivò Marta.", [], True)

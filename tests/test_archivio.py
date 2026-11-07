import os
import stat

import pytest

from libro import archivio, deposito


def test_il_testo_torna_identico_byte_per_byte():
    originale = "Prima riga\r\n\r\n  spazi   strani\n\n<!-- non è metadato -->\n\nfine senza a capo è ok"
    voce = archivio.salva("annotazione", originale)
    assert archivio.leggi(voce.id).testo == originale


def test_i_metadati_con_testo_difficile_si_rileggono():
    voce = archivio.salva("risposta", "sì", domanda='Chi era? --> "lui"\nsu due righe')
    assert archivio.leggi(voce.id).meta["domanda"] == 'Chi era? --> "lui"\nsu due righe'


def test_il_file_nasce_in_sola_lettura_e_privato(dati):
    voce = archivio.salva("annotazione", "testo")
    percorso = next((dati / "archivio").glob(f"{voce.id}-*.md"))
    assert stat.S_IMODE(os.stat(percorso).st_mode) == 0o400
    assert stat.S_IMODE(os.stat(dati).st_mode) == 0o700
    with pytest.raises(PermissionError):
        open(percorso, "w")


def test_il_modulo_non_offre_modifiche_o_cancellazioni():
    pubbliche = {n for n in dir(archivio) if callable(getattr(archivio, n)) and not n.startswith("_")}
    assert {"salva", "leggi", "leggi_tutte"} <= pubbliche
    assert not {n for n in pubbliche if any(p in n for p in ("cancella", "modifica", "aggiorna", "elimina"))}


def test_le_voci_tornano_in_ordine_di_tempo():
    ids = [archivio.salva("annotazione", f"testo {i}").id for i in range(5)]
    assert [v.id for v in archivio.leggi_tutte()] == ids


@pytest.mark.parametrize("vuoto", ["", "   ", "\n\n"])
def test_il_testo_vuoto_non_entra(vuoto):
    with pytest.raises(ValueError):
        archivio.salva("annotazione", vuoto)


def test_le_versioni_delle_bozze_non_si_sovrascrivono():
    prima = deposito.salva_versione(1, [{"id": "p1", "autore": "tu", "testo": "uno"}])
    seconda = deposito.salva_versione(1, [{"id": "p1", "autore": "tu", "testo": "due"}])
    assert (prima["versione"], seconda["versione"]) == (1, 2)
    assert deposito.bozza(1, 1)["paragrafi"][0]["testo"] == "uno"
    assert deposito.bozza(1)["paragrafi"][0]["testo"] == "due"

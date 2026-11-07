from libro import archivio, deposito, importa

MAPPA_FINTA = """# Titolo di prova: mappa del libro

Un testo di prova.

Il filo è una frase di prova.

## I capitoli

| # | Capitolo | Tema | Materiale | Stato |
|---|---|---|---|---|
| 1 | Il porto | Il lavoro | L'estate, **il cuoco** | pieno |
| 2 | La scuola | Lo studio | Una frase | strano |

## I buchi più grandi

1. **Buco uno.** Manca.
2. **Buco due.** Manca.

## Un punto da chiarire

- Due date diverse.

## Le domande, in ordine

1. Chi c'era?
2. Che ora era?

## Decisioni che spettano a te

- **Una decisione.** Dopo.

## Regole per la scrittura

- Nessun fatto inventato.
"""


def cartella_finta(tmp_path, testo="Testo originale\r\n\r\nseconda parte"):
    cartella = tmp_path / "fonte"
    cartella.mkdir()
    with open(cartella / "fonte-originale.md", "w", encoding="utf-8", newline="") as file:
        file.write(testo)
    (cartella / "mappa.md").write_text(MAPPA_FINTA, encoding="utf-8")
    return cartella


def test_la_mappa_in_markdown_diventa_dati():
    mappa = importa.analizza_mappa(MAPPA_FINTA)
    assert mappa["titolo"] == "Titolo di prova"
    assert mappa["filo"].startswith("Il filo")
    assert mappa["capitoli"][0] == {
        "id": 1, "titolo": "Il porto", "tema": "Il lavoro",
        "materiale": "L'estate, il cuoco", "stato": "pieno",
    }
    assert mappa["capitoli"][1]["stato"] == "parziale"
    assert mappa["buchi"][0]["testo"] == "Buco uno. Manca."
    assert mappa["contraddizioni"][0]["id"] == "c1"
    assert mappa["domande_suggerite"] == ["Chi c'era?", "Che ora era?"]
    assert mappa["decisioni"] == ["Una decisione. Dopo."]
    assert mappa["regole"] == ["Nessun fatto inventato."]


def test_import_copia_il_testo_identico_e_non_duplica(tmp_path):
    cartella = cartella_finta(tmp_path)
    esito = importa.importa_cartella(cartella, nota="Nota di prova.")
    assert esito["capitoli"] == 2 and esito["fonte_gia_presente"] is False
    voci = archivio.leggi_tutte()
    assert voci[0].testo == "Testo originale\r\n\r\nseconda parte"
    assert voci[0].meta["nota"] == "Nota di prova."

    secondo = importa.importa_cartella(cartella)
    assert secondo["fonte_gia_presente"] is True and secondo["mappa_creata"] is False
    assert len(archivio.leggi_tutte()) == 1


def test_import_non_sovrascrive_una_mappa_gia_cambiata(tmp_path):
    cartella = cartella_finta(tmp_path)
    importa.importa_cartella(cartella)
    stato = deposito.mappa()
    stato["titolo"] = "Cambiato dall'autore"
    deposito.salva_mappa(stato)
    importa.importa_cartella(cartella)
    assert deposito.mappa()["titolo"] == "Cambiato dall'autore"

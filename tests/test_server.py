import time

import pytest
from conftest import ricordo, risposta_archivista
from fastapi.testclient import TestClient

from libro import agenti, archivio, deposito
from libro import motore as modulo_motore
from libro.coda import Coda

BASE = "http://127.0.0.1:8765"
ORIGINE = {"Origin": BASE}


@pytest.fixture
def client(monkeypatch):
    nuova = Coda()
    monkeypatch.setattr("libro.server.coda", nuova)
    with TestClient(app_vera(), base_url=BASE) as cliente:
        cliente.coda = nuova
        yield cliente


def app_vera():
    from libro.server import app
    return app


def domanda_finta(testo="Chi c'era quel giorno?"):
    return {"stato": "domanda", "domanda": testo, "tipo": "scena", "aggancio": "",
            "capitolo": 1, "motivo": "Manca un dettaglio."}


# Protezione ---------------------------------------------------------------

def test_un_altro_host_viene_rifiutato(client):
    risposta = client.get("/api/archivio", headers={"Host": "sito-malevolo.example"})
    assert risposta.status_code == 403


def test_un_altro_sito_non_puo_scrivere(client):
    risposta = client.post("/api/annotazioni", json={"testo": "x"}, headers={"Origin": "https://malevolo.example"})
    assert risposta.status_code == 403
    assert archivio.leggi_tutte() == []


def test_una_scrittura_senza_origine_viene_rifiutata(client):
    assert client.post("/api/annotazioni", json={"testo": "x"}).status_code == 403


def test_un_form_di_un_altro_sito_viene_rifiutato(client):
    risposta = client.post(
        "/api/annotazioni", content="testo=x",
        headers={**ORIGINE, "Content-Type": "application/x-www-form-urlencoded"},
    )
    assert risposta.status_code == 415


def test_le_pagine_impediscono_contenuti_esterni(client):
    intestazioni = client.get("/").headers
    assert "default-src 'self'" in intestazioni["content-security-policy"]
    assert intestazioni["cache-control"] == "no-store"


def test_la_pagina_non_carica_niente_da_fuori(client):
    assert "http" not in client.get("/").text
    assert "http" not in client.get("/statici/app.js").text
    assert "http" not in client.get("/statici/anteprima.js").text
    assert "http" not in client.get("/statici/app.css").text


# Pagina --------------------------------------------------------------------

def test_la_barra_laterale_riceve_tutti_i_capitoli(client, mappa):
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    deposito.applica_archivista(voce.id, [ricordo(), ricordo(capitolo=None)], [], 0)
    dati = client.get("/api/stato").json()
    assert dati["titolo"] == "Libro di prova" and dati["ricordi"] == 2 and dati["senza_capitolo"] == 1
    assert [(c["id"], c["ricordi"], c["bozza"]) for c in dati["capitoli"]] == [(1, 1, False), (2, 0, False)]
    assert dati["scritti"] == 0 and dati["domanda_pronta"] is False


def test_la_barra_laterale_conta_le_cose_da_fare(client, mappa):
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    deposito.applica_archivista(voce.id, [ricordo(persone=["Marta", "Luca"])], [], 0)
    deposito.scegli_persona("Luca", "consenso", "")
    deposito.salva_versione(2, [{"id": "p1", "autore": "scrittore", "frasi": [
        {"testo": "x", "fonti": [], "connettivo": False, "segnalazioni": ["Manca la fonte."]},
    ]}], controllo="eseguito", autore="scrittore")
    dati = client.get("/api/stato").json()
    assert dati["da_raccontare"] == 1 and dati["persone_da_decidere"] == 1
    assert dati["da_verificare"] == 1 and dati["capitolo_da_verificare"] == 2


def test_la_barra_laterale_non_conta_i_ricordi_superati(client, mappa):
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    deposito.applica_archivista(voce.id, [ricordo()], [], 0)
    correzione = archivio.salva("correzione", "Non era così.", capitolo=1)
    deposito.applica_archivista(correzione.id, [], [risposta_archivista(ricordi_superati=["r0001"])], 0)
    assert client.get("/api/stato").json()["ricordi"] == 0


# Annotazioni --------------------------------------------------------------

def test_annotazione_si_salva_subito_anche_se_claude_non_risponde(client, motore, mappa):
    motore.risposte = [modulo_motore.NonCollegato("Claude non è collegato.")]
    esito = client.post("/api/annotazioni", json={"testo": "Il mio testo"}, headers=ORIGINE)
    assert esito.status_code == 200
    client.coda.attendi()
    assert archivio.leggi_tutte()[0].testo == "Il mio testo"
    stato = client.get("/api/stato").json()["coda"]
    assert stato["errori"][0]["messaggio"] == "Claude non è collegato."


def test_riprova_rielabora_il_testo_rimasto_indietro(client, motore, mappa):
    motore.risposte = [modulo_motore.ErroreMotore("Limite")]
    client.post("/api/annotazioni", json={"testo": "lavoravo al porto ogni estate"}, headers=ORIGINE)
    client.coda.attendi()
    motore.risposte = [risposta_archivista([ricordo()])]
    client.post("/api/coda/riprova", json={}, headers=ORIGINE)
    client.coda.attendi()
    assert client.get("/api/stato").json()["coda"]["errori"] == []
    assert len(deposito.ricordi()) == 1


def test_all_avvio_tornano_in_coda_i_testi_non_letti(motore, mappa, monkeypatch):
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    motore.risposte = [risposta_archivista([ricordo()])]
    nuova = Coda()
    monkeypatch.setattr("libro.server.coda", nuova)
    with TestClient(app_vera(), base_url=BASE):
        nuova.attendi()
    assert deposito.elaborazioni()[voce.id]["stato"] == "fatto"


def test_un_errore_imprevisto_non_mette_il_testo_nel_registro(client, motore, mappa, caplog):
    motore.risposte = [ValueError("contenuto segreto dell'autore")]
    client.post("/api/annotazioni", json={"testo": "testo segreto"}, headers=ORIGINE)
    client.coda.attendi()
    assert "segreto" not in caplog.text


def test_lo_spunto_arriva_all_archivista_come_domanda(client, motore, mappa):
    motore.risposte = [risposta_archivista()]
    corpo = {"testo": "Un vicino.", "spunto": "Chi c'era quel giorno?"}
    client.post("/api/annotazioni", json=corpo, headers=ORIGINE)
    client.coda.attendi()
    voce = archivio.leggi_tutte()[0]
    assert voce.testo == "Un vicino." and voce.meta["domanda"] == "Chi c'era quel giorno?"
    assert "<domanda>Chi c'era quel giorno?</domanda>" in motore.chiamate[0]["prompt"]
    assert client.get("/api/archivio").json()[0]["domanda"] == "Chi c'era quel giorno?"


def test_una_annotazione_senza_spunto_non_ha_domanda(client, motore, mappa):
    motore.risposte = [risposta_archivista()]
    client.post("/api/annotazioni", json={"testo": "Testo."}, headers=ORIGINE)
    client.coda.attendi()
    assert "domanda" not in archivio.leggi_tutte()[0].meta


def test_il_testo_vuoto_non_entra(client):
    risposta = client.post("/api/annotazioni", json={"testo": "   "}, headers=ORIGINE)
    assert risposta.status_code == 422


def test_il_testo_in_corso_sopravvive_e_si_svuota_quando_salvi(client, motore, mappa):
    motore.risposte = [risposta_archivista()]
    client.post("/api/in-corso/annotazione", json={"testo": "a metà"}, headers=ORIGINE)
    assert client.get("/api/in-corso/annotazione").json()["testo"] == "a metà"
    client.post("/api/annotazioni", json={"testo": "finito"}, headers=ORIGINE)
    client.coda.attendi()
    assert client.get("/api/in-corso/annotazione").json()["testo"] == ""


def test_un_segnale_di_disagio_ferma_le_domande_e_salva_il_testo(client, motore, mappa):
    motore.risposte = [risposta_archivista()]
    esito = client.post("/api/annotazioni", json={"testo": "Prova: stasera voglio morire"}, headers=ORIGINE).json()
    client.coda.attendi()
    assert esito["pausa"] == agenti.MESSAGGIO_PAUSA
    assert archivio.leggi_tutte()[0].testo == "Prova: stasera voglio morire"


# Domande ------------------------------------------------------------------

def test_giro_completo_domanda_risposta_salto(client, motore, mappa):
    motore.risposte = [domanda_finta()]
    prima = client.post("/api/domande/prossima", json={}, headers=ORIGINE).json()
    assert prima["stato"] == "domanda" and prima["testo"] == "Chi c'era quel giorno?"

    motore.risposte = [risposta_archivista()]
    esito = client.post(f"/api/domande/{prima['id']}/risposta", json={"testo": "Un vicino."}, headers=ORIGINE)
    assert esito.status_code == 200
    client.coda.attendi()
    voce = archivio.leggi_tutte()[-1]
    assert voce.tipo == "risposta" and voce.meta["domanda"] == "Chi c'era quel giorno?"

    motore.risposte = [domanda_finta("Che ora era?")]
    seconda = client.post("/api/domande/prossima", json={}, headers=ORIGINE).json()
    assert client.post(f"/api/domande/{seconda['id']}/salta", json={}, headers=ORIGINE).status_code == 200
    assert deposito.domande()[1]["stato"] == "saltata"


def test_le_domande_chiuse_tornano_con_la_risposta_e_senza_quella_aperta(client, motore, mappa):
    motore.risposte = [domanda_finta("Prima domanda?"), risposta_archivista()]
    prima = client.post("/api/domande/prossima", json={}, headers=ORIGINE).json()
    client.post(f"/api/domande/{prima['id']}/risposta", json={"testo": "Mia risposta."}, headers=ORIGINE)
    client.coda.attendi()
    motore.risposte = [domanda_finta("Seconda domanda?")]
    seconda = client.post("/api/domande/prossima", json={}, headers=ORIGINE).json()
    client.post(f"/api/domande/{seconda['id']}/salta", json={}, headers=ORIGINE)
    motore.risposte = [domanda_finta("Terza domanda?")]
    client.post("/api/domande/prossima", json={}, headers=ORIGINE)
    storia = client.get("/api/domande").json()
    assert [(d["testo"], d["stato"], d["risposta"]) for d in storia] == [
        ("Seconda domanda?", "saltata", None),
        ("Prima domanda?", "risposta", "Mia risposta."),
    ]
    assert client.get("/api/stato").json()["domanda_pronta"] is True


def test_il_libro_porta_ultimi_ricordi_e_frasi_da_verificare(client, mappa):
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    deposito.applica_archivista(voce.id, [ricordo(testo=f"Ricordo {i}") for i in range(7)], [], 0)
    deposito.salva_versione(1, [{"id": "p1", "autore": "scrittore", "frasi": [
        {"testo": "x", "fonti": [], "connettivo": False, "segnalazioni": ["Manca la fonte."]},
    ]}], controllo="eseguito", autore="scrittore")
    dati = client.get("/api/libro").json()
    assert [r["testo"] for r in dati["ultimi_ricordi"]] == [f"Ricordo {i}" for i in (6, 5, 4, 3, 2)]
    assert dati["capitoli"][0]["da_verificare"] == 1 and dati["ricordi_minimi"] == 3


def test_i_dettagli_dei_capitoli_non_affollano_il_libro(client, mappa):
    deposito.aggiungi_buchi(["Un buco grande"])
    deposito.aggiungi_buchi([f"Capitolo 1: dettaglio {i}" for i in range(5)], 1)
    testi = [b["testo"] for b in client.get("/api/libro").json()["buchi"]]
    assert "Un buco grande" in testi and not any(t.startswith("Capitolo 1") for t in testi)
    assert client.get("/api/stato").json()["da_raccontare"] == 2
    assert len(client.get("/api/capitoli/1").json()["buchi"]) == 5


def test_un_capitolo_porta_i_suoi_buchi(client, mappa):
    deposito.aggiungi_buchi(["Capitolo 1: chi c'era?"], 1)
    deposito.aggiungi_buchi(["Capitolo 2: dove?"], 2)
    assert [b["testo"] for b in client.get("/api/capitoli/1").json()["buchi"]] == ["Capitolo 1: chi c'era?"]
    assert client.get("/api/capitoli/0").json()["buchi"] == []


def test_non_si_risponde_due_volte_alla_stessa_domanda(client, motore, mappa):
    motore.risposte = [domanda_finta(), risposta_archivista()]
    domanda = client.post("/api/domande/prossima", json={}, headers=ORIGINE).json()
    client.post(f"/api/domande/{domanda['id']}/risposta", json={"testo": "a"}, headers=ORIGINE)
    client.coda.attendi()
    doppia = client.post(f"/api/domande/{domanda['id']}/risposta", json={"testo": "b"}, headers=ORIGINE)
    assert doppia.status_code == 409
    assert [v.testo for v in archivio.leggi_tutte()] == ["a"]


def test_se_claude_non_risponde_la_pagina_riceve_il_messaggio(client, motore, mappa):
    motore.risposte = [modulo_motore.NonCollegato("Claude non è collegato.")]
    esito = client.post("/api/domande/prossima", json={}, headers=ORIGINE)
    assert esito.status_code == 503 and esito.json()["detail"] == "Claude non è collegato."


# Libro --------------------------------------------------------------------

def test_il_libro_conta_i_ricordi_e_nasconde_le_cose_chiuse(client, mappa):
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    deposito.applica_archivista(voce.id, [ricordo(), ricordo(privacy="solo_appunti", persone=["Marta"])], [], 0)
    dati = client.get("/api/libro").json()
    assert dati["capitoli"][0]["ricordi_libro"] == 1 and dati["capitoli"][0]["ricordi_privati"] == 1
    assert dati["persone"]["Marta"]["scelta"] == "da_decidere"


def test_un_ricordo_cambia_privacy_e_capitolo(client, mappa):
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    deposito.applica_archivista(voce.id, [ricordo()], [], 0)
    client.post("/api/ricordi/r0001", json={"privacy": "solo_appunti"}, headers=ORIGINE)
    client.post("/api/ricordi/r0001", json={"capitolo": 2, "cambia_capitolo": True}, headers=ORIGINE)
    salvato = deposito.ricordi()[0]
    assert salvato["privacy"] == "solo_appunti" and salvato["capitolo"] == 2
    assert client.post("/api/ricordi/r0001", json={"privacy": "pubblico"}, headers=ORIGINE).status_code == 422
    assert client.post("/api/ricordi/r0001", json={"capitolo": 99, "cambia_capitolo": True}, headers=ORIGINE).status_code == 404


def test_ricordi_senza_capitolo_hanno_una_pagina(client, mappa):
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    deposito.applica_archivista(voce.id, [ricordo(capitolo=None)], [], 0)
    dati = client.get("/api/capitoli/0").json()
    assert dati["capitolo"]["id"] == 0 and len(dati["ricordi"]) == 1


def test_nome_cambiato_richiede_il_nuovo_nome(client):
    corpo = {"nome": "Marta", "scelta": "nome_cambiato", "alias": ""}
    assert client.post("/api/persone", json=corpo, headers=ORIGINE).status_code == 422


def test_una_scelta_sconosciuta_viene_rifiutata(client):
    corpo = {"nome": "Marta", "scelta": "pubblica"}
    assert client.post("/api/persone", json=corpo, headers=ORIGINE).status_code == 422


def test_bozza_da_pagina_e_correzione(client, motore, mappa):
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    deposito.applica_archivista(voce.id, [ricordo(), ricordo(), ricordo()], [], 0)
    motore.risposte = [
        {"paragrafi": [{"blindato": "", "frasi": [{"testo": "Lavoravo al porto.", "fonti": ["r0001"], "connettivo": False}]}],
         "domande_aperte": []},
        {"segnalazioni": []},
    ]
    client.post("/api/capitoli/1/bozza", json={}, headers=ORIGINE)
    for _ in range(200):
        lavoro = client.get("/api/capitoli/1").json()["lavoro"]
        if lavoro["stato"] != "in_corso":
            break
        time.sleep(0.01)
    dati = client.get("/api/capitoli/1").json()
    assert dati["lavoro"]["stato"] == "fatto"
    assert dati["fonti"]["r0001"]["citazione"]

    motore.risposte = [risposta_archivista()]
    esito = client.post("/api/capitoli/1/paragrafi/p1", json={"testo": "Mia versione."}, headers=ORIGINE)
    assert esito.json()["versione"] == 2
    client.coda.attendi()
    assert client.get("/api/capitoli/1").json()["bozza"]["paragrafi"][0]["autore"] == "tu"
    assert client.post("/api/capitoli/1/paragrafi/p9", json={"testo": "x"}, headers=ORIGINE).status_code == 404

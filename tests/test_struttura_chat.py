import time

import pytest
from conftest import ricordo, risposta_archivista
from fastapi.testclient import TestClient

from libro import agenti, archivio, controlli, deposito
from libro import motore as modulo_motore
from libro.coda import Coda

BASE = "http://127.0.0.1:8765"
ORIGINE = {"Origin": BASE}


@pytest.fixture
def client(monkeypatch):
    from libro.server import app

    nuova = Coda()
    monkeypatch.setattr("libro.server.coda", nuova)
    with TestClient(app, base_url=BASE) as cliente:
        cliente.coda = nuova
        yield cliente


STRUTTURA = [
    {"titolo": "Primo", "tema": "Inizio", "capitoli": [{"id": 2, "titolo": "La scuola"}]},
    {"titolo": "Secondo", "tema": "", "capitoli": [{"id": 1, "titolo": "Il porto nuovo"}, {"id": None, "titolo": "Nuovo"}]},
]


def prepara_materiale(capitolo=1):
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    deposito.applica_archivista(voce.id, [ricordo(capitolo=capitolo)], [], 0)


def risposta_chat(testo="Vedo due cose.", proposta=None, stato="risposta"):
    return {"stato": stato, "testo": testo, "proposta": proposta}


def attendi_chat(client):
    for _ in range(300):
        if not client.get("/api/chat").json()["in_corso"]:
            return
        time.sleep(0.01)
    raise AssertionError("La chat non ha finito.")


# Struttura -----------------------------------------------------------------

def test_senza_struttura_tutto_sta_in_un_capitolo_solo(mappa):
    parti = deposito.struttura()
    assert [p["titolo"] for p in parti] == ["Il libro"]
    assert [c["numero"] for c in parti[0]["capitoli"]] == ["1.1", "1.2"]


def test_la_struttura_numera_capitoli_e_sottocapitoli(mappa):
    deposito.applica_struttura(STRUTTURA)
    parti = deposito.struttura()
    assert [(p["numero"], p["titolo"]) for p in parti] == [(1, "Primo"), (2, "Secondo")]
    assert [(c["id"], c["numero"], c["titolo"]) for c in parti[1]["capitoli"]] == [(1, "2.1", "Il porto nuovo"), (3, "2.2", "Nuovo")]
    assert [c["id"] for c in deposito.mappa()["capitoli"]] == [2, 1, 3]


def test_un_sottocapitolo_non_assegnato_non_si_perde(mappa):
    stato = deposito.mappa()
    stato["parti"] = [{"id": "parte1", "titolo": "Primo", "tema": "", "capitoli": [2]}]
    deposito.salva_mappa(stato)
    parti = deposito.struttura()
    assert [p["titolo"] for p in parti] == ["Primo", "Da sistemare"]
    assert parti[1]["capitoli"][0]["id"] == 1


def test_cambiare_struttura_non_tocca_ricordi_e_bozze(mappa):
    prepara_materiale(1)
    deposito.salva_versione(1, [{"id": "p1", "autore": "tu", "testo": "Mia bozza."}])
    deposito.applica_struttura(STRUTTURA)
    assert deposito.ricordi()[0]["capitolo"] == 1
    assert deposito.bozza(1)["paragrafi"][0]["testo"] == "Mia bozza."


def test_la_mappa_di_prima_resta_nello_storico(mappa, dati):
    deposito.applica_struttura(STRUTTURA, titolo="Altro titolo", filo="Altro filo")
    assert deposito.mappa()["titolo"] == "Altro titolo" and deposito.mappa()["filo"] == "Altro filo"
    assert len(list((dati / "storico-mappa").glob("*.json"))) == 1


@pytest.mark.parametrize("parti, parola", [
    ([], "almeno un capitolo"),
    ([{"titolo": " ", "capitoli": [{"id": 1, "titolo": "a"}, {"id": 2, "titolo": "b"}]}], "non ha il titolo"),
    ([{"titolo": "A", "capitoli": []}], "non ha sottocapitoli"),
    ([{"titolo": "A", "capitoli": [{"id": 1, "titolo": " "}, {"id": 2, "titolo": "b"}]}], "non ha il titolo"),
    ([{"titolo": "A", "capitoli": [{"id": 99, "titolo": "x"}, {"id": 1, "titolo": "a"}, {"id": 2, "titolo": "b"}]}], "non esiste"),
    ([{"titolo": "A", "capitoli": [{"id": 1, "titolo": "a"}, {"id": 1, "titolo": "a"}, {"id": 2, "titolo": "b"}]}], "due volte"),
    ([{"titolo": "A" * 81, "capitoli": [{"id": 1, "titolo": "a"}, {"id": 2, "titolo": "b"}]}], "80 caratteri"),
])
def test_una_struttura_sbagliata_viene_rifiutata(parti, parola):
    problemi = controlli.problemi_struttura(parti, {1: "a", 2: "b"}, set())
    assert any(parola in p for p in problemi), problemi


def test_un_sottocapitolo_con_materiale_non_puo_sparire():
    problemi = controlli.problemi_struttura(
        [{"titolo": "A", "capitoli": [{"id": 1, "titolo": "a"}]}], {1: "a", 2: "Te"}, {2},
    )
    assert any("Te" in p and "non può sparire" in p for p in problemi)


def test_un_sottocapitolo_vuoto_si_puo_togliere():
    assert controlli.problemi_struttura([{"titolo": "A", "capitoli": [{"id": 1, "titolo": "a"}]}], {1: "a", 2: "b"}, set()) == []


def test_la_pagina_cambia_la_struttura(client, mappa):
    prepara_materiale(1)
    assert client.post("/api/struttura", json={"parti": STRUTTURA}, headers=ORIGINE).status_code == 200
    dati = client.get("/api/libro").json()
    assert [p["titolo"] for p in dati["parti"]] == ["Primo", "Secondo"]
    assert dati["capitoli"][0]["numero"] == "1.1" and dati["capitoli"][0]["id"] == 2
    stato = client.get("/api/stato").json()
    assert stato["parti"][1]["ricordi"] == 1 and stato["capitoli"][1]["parte"] == "parte2"
    capitolo = client.get("/api/capitoli/1").json()
    assert capitolo["capitolo"]["numero"] == "2.1" and capitolo["capitolo"]["parte_titolo"] == "Secondo"
    assert [v["numero"] for v in capitolo["indice"]] == ["1.1", "2.1", "2.2"]


def test_la_pagina_non_puo_far_sparire_un_sottocapitolo_pieno(client, mappa):
    prepara_materiale(1)
    corpo = {"parti": [{"titolo": "Solo", "capitoli": [{"id": 2, "titolo": "La scuola"}]}]}
    risposta = client.post("/api/struttura", json=corpo, headers=ORIGINE)
    assert risposta.status_code == 422 and "non può sparire" in risposta.json()["detail"]
    assert len(deposito.mappa()["capitoli"]) == 2


def test_l_anteprima_ha_capitoli_con_dentro_i_sottocapitoli(client, mappa):
    deposito.applica_struttura(STRUTTURA)
    deposito.salva_versione(1, [{"id": "p1", "autore": "tu", "testo": "Testo uno."}])
    deposito.salva_versione(2, [{"id": "p1", "autore": "tu", "testo": "Testo due."}])
    dati = client.get("/api/anteprima").json()
    assert [(p["numero"], p["titolo"], [s["titolo"] for s in p["sotto"]]) for p in dati["parti"]] == [
        (1, "Primo", ["La scuola"]), (2, "Secondo", ["Il porto nuovo"]),
    ]
    assert dati["parti"][1]["sotto"][0]["paragrafi"] == ["Testo uno."]
    assert [c["titolo"] for c in dati["mancanti"]] == ["Nuovo"]


def test_lo_scrittore_sa_dove_sta_e_dove_va_il_libro(motore, mappa):
    deposito.applica_struttura(STRUTTURA, filo="Dal mare alla città.")
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    deposito.applica_archivista(voce.id, [ricordo(capitolo=1) for _ in range(3)], [], 0)
    motore.risposte = [
        {"paragrafi": [{"blindato": "", "frasi": [{"testo": "Lavoravo al porto.", "fonti": ["r0001"], "connettivo": False}]}], "domande_aperte": ["Che odore c'era?"]},
        {"segnalazioni": []},
    ]
    agenti.scrivi_bozza(1)
    prompt = motore.chiamate[0]["prompt"]
    assert "Dal mare alla città." in prompt and '"capitolo": "Secondo"' in prompt
    assert [b["testo"] for b in deposito.mappa()["buchi"] if b.get("capitolo") == 1] == ["Che odore c'era?"]


def test_l_intervistatore_conosce_filo_e_struttura(motore, mappa):
    deposito.applica_struttura(STRUTTURA, filo="Dal mare alla città.")
    motore.risposte = [{"stato": "domanda", "domanda": "Chi c'era?", "tipo": "scena", "aggancio": "", "capitolo": 1, "motivo": "x"}]
    agenti.prossima_domanda()
    prompt = motore.chiamate[0]["prompt"]
    assert "<filo>Dal mare alla città.</filo>" in prompt and '"numero": "2.1"' in prompt


# Chat ----------------------------------------------------------------------

def test_la_chat_salva_risponde_e_conosce_il_libro(client, motore, mappa):
    deposito.applica_struttura(STRUTTURA, filo="Dal mare alla città.")
    voce = archivio.salva("annotazione", "lavoravo al porto ogni estate")
    deposito.applica_archivista(voce.id, [ricordo(testo="Il ricordo del porto")], [], 0)
    deposito.salva_versione(1, [{"id": "p1", "autore": "tu", "testo": "Testo della bozza."}])
    motore.risposte = [risposta_chat("Il libro va verso il porto.")]
    esito = client.post("/api/chat", json={"testo": "Dove va?"}, headers=ORIGINE)
    assert esito.status_code == 200
    attendi_chat(client)
    dati = client.get("/api/chat").json()
    assert [(m["autore"], m["testo"]) for m in dati["messaggi"]] == [("tu", "Dove va?"), ("agente", "Il libro va verso il porto.")]
    prompt = motore.chiamate[0]["prompt"]
    for pezzo in ("Dal mare alla città.", "Il ricordo del porto", "lavoravo al porto", "Testo della bozza.", "<ultimo_messaggio>\nDove va?"):
        assert pezzo in prompt
    assert dati["contesto"]["ricordi"] == 1 and dati["contesto"]["bozze"] == 1 and dati["contesto"]["parti"][1]["sottocapitoli"] == 2


def test_la_chat_ricorda_i_messaggi_di_prima(client, motore, mappa):
    motore.risposte = [risposta_chat("Prima risposta.")]
    client.post("/api/chat", json={"testo": "Primo."}, headers=ORIGINE)
    attendi_chat(client)
    motore.risposte = [risposta_chat("Seconda risposta.")]
    client.post("/api/chat", json={"testo": "Secondo."}, headers=ORIGINE)
    attendi_chat(client)
    prompt = motore.chiamate[-1]["prompt"]
    assert "Autore: Primo." in prompt and "Tu: Prima risposta." in prompt


def test_le_parole_in_chat_entrano_nell_archivio_ma_non_in_gia_scritto(client, motore, mappa):
    motore.risposte = [risposta_chat()]
    client.post("/api/chat", json={"testo": "Sì."}, headers=ORIGINE)
    attendi_chat(client)
    assert archivio.leggi_tutte()[0].tipo == "chat" and archivio.leggi_tutte()[0].testo == "Sì."
    assert client.get("/api/archivio").json() == []


def test_un_messaggio_corto_non_chiama_l_archivista(client, motore, mappa):
    motore.risposte = [risposta_chat()]
    client.post("/api/chat", json={"testo": "Va bene."}, headers=ORIGINE)
    attendi_chat(client)
    client.coda.attendi()
    assert len(motore.chiamate) == 1
    assert deposito.elaborazioni()[archivio.leggi_tutte()[0].id]["stato"] == "fatto"


def test_un_messaggio_lungo_passa_dall_archivista(client, mappa, monkeypatch):
    chiamate = []

    def finto(sistema, prompt, schema, modello):
        chiamate.append(sistema)
        if "archivista" in sistema:
            return risposta_archivista([ricordo(citazione="lavoravo al porto ogni estate")])
        return risposta_chat()

    monkeypatch.setattr("libro.motore.chiedi_json", finto)
    testo = "Da ragazzo lavoravo al porto ogni estate con mio zio Carlo."
    client.post("/api/chat", json={"testo": testo}, headers=ORIGINE)
    attendi_chat(client)
    client.coda.attendi()
    assert len(deposito.ricordi()) == 1 and deposito.ricordi()[0]["fonte"] == archivio.leggi_tutte()[0].id
    assert any("Se tipo_testo è chat" in s for s in chiamate)


def test_non_si_scrive_mentre_l_agente_risponde(client, mappa, monkeypatch):
    def lento(*_):
        time.sleep(0.3)
        return risposta_chat()

    monkeypatch.setattr("libro.motore.chiedi_json", lento)
    assert client.post("/api/chat", json={"testo": "Uno."}, headers=ORIGINE).status_code == 200
    assert client.post("/api/chat", json={"testo": "Due."}, headers=ORIGINE).status_code == 409
    assert client.get("/api/chat").json()["in_corso"] is True
    attendi_chat(client)
    assert [m["testo"] for m in deposito.messaggi_chat() if m["autore"] == "tu"] == ["Uno."]


def test_se_claude_non_risponde_il_messaggio_resta_e_si_riprova(client, motore, mappa):
    motore.risposte = [modulo_motore.NonCollegato("Claude non è collegato.")]
    client.post("/api/chat", json={"testo": "Ciao."}, headers=ORIGINE)
    attendi_chat(client)
    messaggi = client.get("/api/chat").json()["messaggi"]
    assert messaggi[0]["testo"] == "Ciao." and messaggi[1]["errore"] is True
    motore.risposte = [risposta_chat("Eccomi.")]
    assert client.post("/api/chat/riprova", json={}, headers=ORIGINE).json()["ok"] is True
    attendi_chat(client)
    assert [m["testo"] for m in client.get("/api/chat").json()["messaggi"]] == ["Ciao.", "Eccomi."]


def test_un_segnale_di_disagio_ferma_la_chat_senza_chiamare_claude(client, motore, mappa):
    esito = client.post("/api/chat", json={"testo": "Prova: stasera voglio morire."}, headers=ORIGINE).json()
    assert esito["pausa"] is True and motore.chiamate == []
    messaggi = client.get("/api/chat").json()["messaggi"]
    assert messaggi[1]["pausa"] is True and "112" in messaggi[1]["testo"]
    assert archivio.leggi_tutte()[0].testo == "Prova: stasera voglio morire."


def test_la_pausa_decisa_dall_agente_usa_il_testo_fisso(client, motore, mappa):
    motore.risposte = [risposta_chat("Testo dell'agente", stato="pausa")]
    client.post("/api/chat", json={"testo": "Non ce la faccio."}, headers=ORIGINE)
    attendi_chat(client)
    ultimo = client.get("/api/chat").json()["messaggi"][-1]
    assert ultimo["testo"] == agenti.MESSAGGIO_PAUSA and ultimo["pausa"] is True


def test_una_proposta_si_applica_solo_con_il_bottone(client, motore, mappa):
    prepara_materiale(1)
    proposta = {"motivo": "Regge meglio.", "titolo": "Nuovo titolo", "filo": "Nuovo filo", "struttura": STRUTTURA}
    motore.risposte = [risposta_chat("Ti propongo questo.", proposta), risposta_archivista()]
    client.post("/api/chat", json={"testo": "Che ne pensi?"}, headers=ORIGINE)
    attendi_chat(client)
    agente = client.get("/api/chat").json()["messaggi"][-1]
    assert agente["proposta"]["titolo"] == "Nuovo titolo" and agente["esito_proposta"] is None
    assert deposito.mappa()["titolo"] == "Libro di prova" and not deposito.mappa()["parti"]
    assert client.post(f"/api/chat/{agente['id']}/proposta", json={"azione": "applica"}, headers=ORIGINE).status_code == 200
    stato = deposito.mappa()
    assert stato["titolo"] == "Nuovo titolo" and stato["filo"] == "Nuovo filo" and len(stato["parti"]) == 2
    assert client.get("/api/chat").json()["messaggi"][-1]["esito_proposta"] == "applicata"


def test_una_proposta_si_puo_scartare(client, motore, mappa):
    motore.risposte = [risposta_chat("Ti propongo questo.", {"motivo": "x", "titolo": "Altro", "filo": None, "struttura": None})]
    client.post("/api/chat", json={"testo": "Che ne pensi?"}, headers=ORIGINE)
    attendi_chat(client)
    agente = client.get("/api/chat").json()["messaggi"][-1]
    client.post(f"/api/chat/{agente['id']}/proposta", json={"azione": "scarta"}, headers=ORIGINE)
    assert deposito.mappa()["titolo"] == "Libro di prova"
    assert client.get("/api/chat").json()["messaggi"][-1]["esito_proposta"] == "scartata"


def test_una_proposta_che_perde_materiale_viene_rifatta_e_poi_tolta(client, motore, mappa):
    prepara_materiale(1)
    cattiva = {"motivo": "x", "titolo": "Titolo buono", "filo": None, "struttura": [{"titolo": "A", "tema": "", "capitoli": [{"id": 2, "titolo": "La scuola"}]}]}
    motore.risposte = [risposta_chat("Uno.", dict(cattiva)), risposta_chat("Due.", dict(cattiva))]
    client.post("/api/chat", json={"testo": "Riordina."}, headers=ORIGINE)
    attendi_chat(client)
    assert "non può sparire" in motore.chiamate[1]["prompt"]
    agente = client.get("/api/chat").json()["messaggi"][-1]
    assert agente["proposta"]["struttura"] is None and agente["proposta"]["titolo"] == "Titolo buono"


def test_una_proposta_vuota_non_mostra_il_bottone(client, motore, mappa):
    motore.risposte = [risposta_chat("Niente.", {"motivo": "x", "titolo": None, "filo": None, "struttura": None})]
    client.post("/api/chat", json={"testo": "Boh."}, headers=ORIGINE)
    attendi_chat(client)
    assert client.get("/api/chat").json()["messaggi"][-1]["proposta"] is None


def test_una_proposta_diventata_vecchia_viene_rifiutata(client, motore, mappa):
    motore.risposte = [risposta_chat("Ecco.", {"motivo": "x", "titolo": None, "filo": None, "struttura": [
        {"titolo": "Solo", "tema": "", "capitoli": [{"id": 2, "titolo": "La scuola"}]},
    ]})]
    client.post("/api/chat", json={"testo": "Togli il primo."}, headers=ORIGINE)
    attendi_chat(client)
    agente = client.get("/api/chat").json()["messaggi"][-1]
    prepara_materiale(1)
    risposta = client.post(f"/api/chat/{agente['id']}/proposta", json={"azione": "applica"}, headers=ORIGINE)
    assert risposta.status_code == 409 and "non vale più" in risposta.json()["detail"]
    assert len(deposito.mappa()["capitoli"]) == 2


def test_la_chat_rifiuta_altri_siti(client, mappa):
    assert client.post("/api/chat", json={"testo": "x"}, headers={"Origin": "https://malevolo.example"}).status_code == 403
    assert archivio.leggi_tutte() == []


def test_la_risposta_a_meta_della_chat_sopravvive(client, mappa):
    client.post("/api/in-corso/chat", json={"testo": "a metà"}, headers=ORIGINE)
    assert client.get("/api/in-corso/chat").json()["testo"] == "a metà"

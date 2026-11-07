import time

import pytest
from conftest import ricordo
from fastapi.testclient import TestClient

from libro import agenti, archivio, deposito, design
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


def prepara_capitolo(capitolo=1, numero=3, privacy="libro"):
    voce = archivio.salva("annotazione", "Lavoravo al porto ogni estate.")
    nuovi = [{**ricordo(testo=f"Ricordo {capitolo}.{i}", capitolo=capitolo), "privacy": privacy} for i in range(numero)]
    deposito.applica_archivista(voce.id, nuovi, [], 0)
    return deposito.ricordi()


def scrivi_bozza_a_mano(capitolo=1, testo="Lavoravo al porto.", fonti=None, segnalazioni=None):
    fonti = fonti if fonti is not None else [r["id"] for r in deposito.ricordi_per_scrittore(capitolo)[:1]]
    deposito.salva_versione(capitolo, [{
        "id": "p1", "autore": "scrittore",
        "frasi": [{"testo": testo, "fonti": fonti, "connettivo": False, "segnalazioni": segnalazioni or []}],
    }], controllo="eseguito", autore="scrittore")


# Regole del design ---------------------------------------------------------

def test_i_design_di_partenza_sono_validi_e_diversi():
    nomi = set()
    for voce in design.PREDEFINITI:
        pulito, avvisi = design.normalizza(voce)
        assert avvisi == [], voce["nome"]
        assert pulito == {**voce, "corpo_pt": float(voce["corpo_pt"]), "interlinea": float(voce["interlinea"])} or pulito == voce
        nomi.add(voce["nome"])
    assert len(nomi) == len(design.PREDEFINITI) >= 5


def test_un_font_non_installato_non_entra():
    pulito, avvisi = design.normalizza({"font_testo": "Comic Papyrus"})
    assert pulito["font_testo"] == design.predefinito()["font_testo"]
    assert any("Comic Papyrus" in a for a in avvisi)


def test_un_font_solo_da_titoli_non_diventa_font_del_testo():
    assert design.normalizza({"font_testo": "Snell Roundhand"})[0]["font_testo"] != "Snell Roundhand"
    assert design.normalizza({"font_titoli": "Snell Roundhand"})[0]["font_titoli"] == "Snell Roundhand"


@pytest.mark.parametrize("corpo, atteso", [(2, 9.0), (500, 14.0), (11.5, 11.5)])
def test_le_misure_assurde_tornano_nei_limiti(corpo, atteso):
    assert design.normalizza({"corpo_pt": corpo})[0]["corpo_pt"] == atteso


@pytest.mark.parametrize("valore", ["grande", None, True, [1]])
def test_un_numero_che_non_e_un_numero_viene_ignorato(valore):
    assert design.normalizza({"corpo_pt": valore})[0]["corpo_pt"] == design.predefinito()["corpo_pt"]


@pytest.mark.parametrize("colore", ["red", "#12", "url(http://evil)", "#12345G", 7, None])
def test_un_colore_non_valido_viene_ignorato(colore):
    pulito, avvisi = design.normalizza({"colore_carta": colore})
    assert pulito["colore_carta"] == design.predefinito()["colore_carta"]
    assert avvisi


def test_testo_illeggibile_viene_corretto():
    pulito, avvisi = design.normalizza({"colore_carta": "#FFFFFF", "colore_inchiostro": "#EEEEEE"})
    assert design.contrasto(pulito["colore_carta"], pulito["colore_inchiostro"]) >= 7
    assert avvisi


def test_titolo_illeggibile_in_copertina_viene_corretto():
    pulito, _ = design.normalizza({
        "copertina_composizione": "classica", "copertina_sfondo": "#111111", "copertina_testo": "#121212",
    })
    assert design.contrasto(pulito["copertina_sfondo"], pulito["copertina_testo"]) >= 3


def test_nella_fascia_il_titolo_si_misura_sulla_fascia():
    pulito, _ = design.normalizza({
        "copertina_composizione": "fascia", "copertina_sfondo": "#111111",
        "copertina_accento": "#FFFFFF", "copertina_testo": "#111111",
    })
    assert pulito["copertina_testo"] == "#111111"


def test_margini_troppo_larghi_vengono_ridotti():
    pulito, avvisi = design.normalizza({
        "formato": "tascabile", "margine_interno_mm": 40, "margine_esterno_mm": 40,
    })
    assert pulito["margine_interno_mm"] + pulito["margine_esterno_mm"] <= 120 * 0.45 + 0.01
    assert avvisi


def test_una_versione_vecchia_con_una_composizione_sparita_torna_valida(mappa):
    deposito.salva_design({**design.predefinito(), "copertina_composizione": "sparita"}, "Vecchia")
    assert agenti.design_corrente()["copertina_composizione"] == design.predefinito()["copertina_composizione"]


def test_i_campi_sconosciuti_non_entrano():
    assert "script" not in design.normalizza({"script": "alert(1)"})[0]


def test_lo_schema_elenca_solo_i_font_installati():
    schema = design.schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(design.predefinito())
    assert set(schema["properties"]["font_testo"]["enum"]) == set(design.FONT_TESTO)


# Designer ------------------------------------------------------------------

def test_la_modifica_crea_una_versione_e_spiega_cosa_ha_fatto(motore, mappa):
    corrente = design.predefinito()
    motore.risposte = [{
        "design": {**corrente, "corpo_pt": 13, "nome": "Altro nome"},
        "spiegazione": "Ho aumentato il corpo.",
        "non_possibile": "Non posso mettere una foto.",
    }]
    esito = agenti.modifica_design("Testo più grande e una foto")
    assert esito["cambiato"] is True and esito["non_possibile"] == "Non posso mettere una foto."
    salvato = deposito.design_versione()
    assert salvato["design"]["corpo_pt"] == 13 and salvato["etichetta"] == "Testo più grande e una foto"
    assert salvato["design"]["nome"] == corrente["nome"]


def test_una_modifica_che_non_cambia_niente_non_crea_versioni(motore, mappa):
    motore.risposte = [{"design": design.predefinito(), "spiegazione": "Niente.", "non_possibile": "Impossibile."}]
    assert agenti.modifica_design("Boh")["cambiato"] is False
    assert deposito.versioni_design() == []


def test_una_modifica_fuori_regola_viene_corretta_e_lo_dice(motore, mappa):
    motore.risposte = [{
        "design": {**design.predefinito(), "font_testo": "Font Inventato"},
        "spiegazione": "Ho cambiato il font.", "non_possibile": "",
    }]
    esito = agenti.modifica_design("Cambia il font")
    assert esito["cambiato"] is False
    assert any("Font Inventato" in a for a in esito["avvisi"])


def test_il_designer_non_vede_gli_appunti_privati(motore, mappa):
    prepara_capitolo(1, 3)
    voce = archivio.salva("annotazione", "La cosa del vicino resta privata.")
    deposito.applica_archivista(
        voce.id, [ricordo(testo="Segreto del vicino", citazione="cosa del vicino", privacy="solo_appunti")], [], 0,
    )
    motore.risposte = [{"design": design.predefinito(), "spiegazione": "", "non_possibile": ""}]
    agenti.modifica_design("Più scuro")
    prompt = motore.chiamate[0]["prompt"]
    assert "Segreto" not in prompt and "vicino" not in prompt
    assert "Ricordo 1.0" in prompt


def test_il_designer_legge_le_bozze_se_ci_sono(motore, mappa):
    prepara_capitolo(1, 3)
    scrivi_bozza_a_mano(testo="Frase vera della bozza.")
    motore.risposte = [{"proposte": [design.predefinito()]}]
    agenti.proponi_design()
    assert "Frase vera della bozza." in motore.chiamate[0]["prompt"]


def test_le_proposte_si_salvano_ma_non_cambiano_il_libro(motore, mappa):
    motore.risposte = [{"proposte": [
        {**design.predefinito(), "nome": f"Nuovo {i}", "font_testo": "Font Inventato"} for i in range(5)
    ]}]
    nuove = agenti.proponi_design()
    assert [p["nome"] for p in nuove] == ["Nuovo 0", "Nuovo 1", "Nuovo 2"]
    assert all(p["font_testo"] in design.FONT_TESTO for p in nuove)
    assert deposito.versioni_design() == []
    assert len(deposito.proposte_design()) == 3


def test_i_nomi_gia_visti_arrivano_al_designer(motore, mappa):
    deposito.aggiungi_proposte([{**design.predefinito(), "nome": "Gia Visto"}])
    motore.risposte = [{"proposte": [design.predefinito()]}]
    agenti.proponi_design()
    assert "Gia Visto" in motore.chiamate[0]["prompt"] and "Editoriale" in motore.chiamate[0]["prompt"]


# Pagina ---------------------------------------------------------------------

def test_l_anteprima_contiene_solo_le_bozze(client, mappa):
    prepara_capitolo(1, 3)
    voce = archivio.salva("annotazione", "Una cosa privatissima da non stampare mai.")
    deposito.applica_archivista(
        voce.id, [ricordo(citazione="cosa privatissima da", capitolo=1, privacy="solo_appunti", testo="Privatissimo")], [], 0,
    )
    scrivi_bozza_a_mano(testo="Lavoravo al porto.")
    risposta = client.get("/api/anteprima")
    assert risposta.status_code == 200
    assert "rivatissim" not in risposta.text
    dati = risposta.json()
    assert dati["capitoli"][0]["paragrafi"] == ["Lavoravo al porto."]
    assert dati["design"]["nome"] == "Essenziale" and dati["versione_design"] == 0


def test_l_anteprima_dice_quali_capitoli_mancano(client, mappa):
    prepara_capitolo(1, 3)
    prepara_capitolo(2, 2)
    dati = client.get("/api/anteprima").json()
    assert dati["capitoli"] == []
    assert [(c["id"], c["ricordi"], c["scrivibile"]) for c in dati["mancanti"]] == [(1, 3, True), (2, 2, False)]


def test_l_anteprima_conta_le_frasi_da_verificare(client, mappa):
    prepara_capitolo(1, 3)
    scrivi_bozza_a_mano(segnalazioni=["Il nome non è nelle fonti."])
    assert client.get("/api/anteprima").json()["capitoli"][0]["da_verificare"] == 1


def test_una_bozza_con_un_ricordo_diventato_privato_va_riscritta(client, mappa):
    tutti = prepara_capitolo(1, 3)
    scrivi_bozza_a_mano()
    assert client.get("/api/anteprima").json()["capitoli"][0]["da_riscrivere"] == 0
    deposito.aggiorna_ricordo(tutti[0]["id"], "solo_appunti", None, False)
    assert client.get("/api/anteprima").json()["capitoli"][0]["da_riscrivere"] == 1


def test_una_bozza_con_un_nome_cambiato_dopo_va_riscritta(client, mappa):
    prepara_capitolo(1, 3)
    scrivi_bozza_a_mano(testo="Marta era al porto.")
    deposito.scegli_persona("Marta", "nome_cambiato", "Anna")
    assert client.get("/api/anteprima").json()["capitoli"][0]["da_riscrivere"] == 1


def test_scegliere_un_design_crea_una_versione_valida(client, mappa):
    corpo = {"design": {**design.PREDEFINITI[1], "font_testo": "Font Inventato"}, "etichetta": "Classico"}
    esito = client.post("/api/design", json=corpo, headers=ORIGINE).json()
    assert esito["versione"] == 1 and esito["avvisi"]
    dati = client.get("/api/anteprima").json()
    assert dati["design"]["nome"] == "Classico" and dati["design"]["font_testo"] in design.FONT_TESTO


def test_tornare_a_una_versione_ne_crea_una_nuova_e_non_cancella(client, mappa):
    client.post("/api/design", json={"design": design.PREDEFINITI[1], "etichetta": "A"}, headers=ORIGINE)
    client.post("/api/design", json={"design": design.PREDEFINITI[2], "etichetta": "B"}, headers=ORIGINE)
    esito = client.post("/api/design/torna", json={"versione": 1}, headers=ORIGINE).json()
    assert esito["versione"] == 3
    dati = client.get("/api/anteprima").json()
    assert dati["design"]["nome"] == "Classico" and len(dati["versioni_design"]) == 3
    assert client.post("/api/design/torna", json={"versione": 99}, headers=ORIGINE).status_code == 404


def test_titolo_e_nome_in_copertina_si_cambiano(client, mappa):
    client.post("/api/libro/dati", json={"titolo": " Nuovo titolo ", "autore": "Un nome"}, headers=ORIGINE)
    dati = client.get("/api/anteprima").json()
    assert (dati["titolo"], dati["autore"]) == ("Nuovo titolo", "Un nome")


def test_una_mappa_vecchia_senza_autore_funziona(client, mappa):
    stato = deposito.mappa()
    stato.pop("autore", None)
    deposito.salva_mappa(stato)
    assert client.get("/api/anteprima").json()["autore"] == ""


def test_le_modifiche_di_design_rifiutano_altri_siti(client, mappa):
    corpo = {"design": design.PREDEFINITI[1]}
    assert client.post("/api/design", json=corpo, headers={"Origin": "https://malevolo.example"}).status_code == 403
    assert deposito.versioni_design() == []


def test_se_claude_non_risponde_la_modifica_dice_perche(client, motore, mappa):
    motore.risposte = [modulo_motore.NonCollegato("Claude non è collegato.")]
    esito = client.post("/api/design/modifica", json={"testo": "Più scuro"}, headers=ORIGINE)
    assert esito.status_code == 503 and esito.json()["detail"] == "Claude non è collegato."


def test_una_richiesta_vuota_non_chiama_claude(client, motore, mappa):
    assert client.post("/api/design/modifica", json={"testo": "  "}, headers=ORIGINE).status_code == 422
    assert motore.chiamate == []


# Bozze mancanti ------------------------------------------------------------

def test_le_bozze_mancanti_saltano_chi_ha_gia_una_bozza_o_pochi_ricordi(motore, mappa):
    prepara_capitolo(1, 3)
    prepara_capitolo(2, 2)
    assert agenti.capitoli_senza_bozza() == [1]
    scrivi_bozza_a_mano(1)
    assert agenti.capitoli_senza_bozza() == []


def test_le_bozze_mancanti_si_scrivono_una_alla_volta_e_si_fermano_solo_sul_capitolo_in_errore(client, motore, mappa):
    id1 = prepara_capitolo(1, 3)[0]["id"]
    prepara_capitolo(2, 3)
    id2 = deposito.ricordi_per_scrittore(2)[0]["id"]
    motore.risposte = [
        modulo_motore.ErroreMotore("Limite raggiunto"),
        {"paragrafi": [{"blindato": "", "frasi": [{"testo": "Lavoravo.", "fonti": [id2], "connettivo": False}]}], "domande_aperte": []},
        {"segnalazioni": []},
    ]
    esito = client.post("/api/bozze/mancanti", json={}, headers=ORIGINE).json()
    assert [l["capitolo"] for l in esito["lavori"]] == [1, 2]
    for _ in range(300):
        if not client.get("/api/stato").json()["coda"]["lavori"]:
            break
        time.sleep(0.01)
    assert deposito.versioni(1) == [] and deposito.versioni(2) == [1]
    dati = client.get("/api/anteprima").json()
    assert dati["mancanti"][0]["lavoro"]["messaggio"] == "Limite raggiunto"
    assert id1


def test_chiedere_due_volte_le_bozze_mancanti_non_le_raddoppia(client, motore, mappa, monkeypatch):
    prepara_capitolo(1, 3)
    uscita = []

    def lento(*_):
        uscita.append(1)
        time.sleep(0.05)
        raise modulo_motore.ErroreMotore("Fermo")

    monkeypatch.setattr("libro.motore.chiedi_json", lento)
    prima = client.post("/api/bozze/mancanti", json={}, headers=ORIGINE).json()["lavori"]
    seconda = client.post("/api/bozze/mancanti", json={}, headers=ORIGINE).json()["lavori"]
    assert len(prima) == 1 and seconda == []
    for _ in range(300):
        if not client.get("/api/stato").json()["coda"]["lavori"]:
            break
        time.sleep(0.01)
    assert len(uscita) == 1

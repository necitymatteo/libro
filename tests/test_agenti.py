import pytest
from conftest import cambiamento, ricordo, risposta_archivista

from libro import agenti, archivio, deposito, motore as modulo_motore

TESTO = "Da ragazzo lavoravo al porto ogni estate. Il cuoco Marco mi insegnava a pulire il pesce."
RICORDO_VERO = ricordo(citazione="lavoravo al porto ogni estate")


def domanda(testo="Chi era il cuoco?", stato="domanda", aggancio="", capitolo=1):
    return {"stato": stato, "domanda": testo, "tipo": "scena", "aggancio": aggancio,
            "capitolo": capitolo, "motivo": "Manca un nome."}


def frase(testo, fonti, connettivo=False):
    return {"testo": testo, "fonti": fonti, "connettivo": connettivo}


def scrittura(*paragrafi, domande_aperte=None):
    return {"paragrafi": list(paragrafi), "domande_aperte": domande_aperte or []}


def paragrafo(*frasi, blindato=""):
    return {"blindato": blindato, "frasi": list(frasi)}


def prepara_ricordi(n=3, **campi):
    voce = archivio.salva("annotazione", TESTO)
    nuovi = [{**ricordo(testo=f"Lavoravo al porto {i}"), **campi} for i in range(n)]
    deposito.applica_archivista(voce.id, nuovi, [], 0)
    return deposito.ricordi()


# Archivista ----------------------------------------------------------------

def test_archivista_salva_ricordi_con_fonte_e_marca_la_voce(motore, mappa):
    voce = archivio.salva("annotazione", TESTO)
    motore.risposte = [risposta_archivista([RICORDO_VERO])]
    assert agenti.elabora_voce(voce) == {"ricordi": 1, "scartati": 0}
    salvato = deposito.ricordi()[0]
    assert salvato["id"] == "r0001" and salvato["fonte"] == voce.id
    assert deposito.elaborazioni()[voce.id]["stato"] == "fatto"


def test_una_citazione_inventata_fa_riprovare_e_poi_viene_scartata(motore, mappa):
    voce = archivio.salva("annotazione", TESTO)
    falso = ricordo(testo="Pioveva", citazione="quel giorno pioveva forte")
    motore.risposte = [
        risposta_archivista([RICORDO_VERO, falso]),
        risposta_archivista([RICORDO_VERO, falso]),
    ]
    assert agenti.elabora_voce(voce) == {"ricordi": 1, "scartati": 1}
    assert len(motore.chiamate) == 2
    assert "quel giorno pioveva forte" in motore.chiamate[1]["prompt"]
    assert [r["testo"] for r in deposito.ricordi()] == [RICORDO_VERO["testo"]]


def test_la_citazione_deve_venire_dal_testo_non_dalla_domanda(motore, mappa):
    voce = archivio.salva("risposta", TESTO, domanda="Quando pioveva a Trieste forte?")
    falso = ricordo(citazione="pioveva a Trieste forte")
    motore.risposte = [risposta_archivista([falso]), risposta_archivista([falso])]
    assert agenti.elabora_voce(voce)["ricordi"] == 0


def test_un_ricordo_con_privacy_strana_resta_privato(motore, mappa):
    voce = archivio.salva("annotazione", TESTO)
    motore.risposte = [risposta_archivista([{**RICORDO_VERO, "privacy": "boh"}])]
    agenti.elabora_voce(voce)
    assert deposito.ricordi()[0]["privacy"] == "solo_appunti"


def test_un_capitolo_inesistente_diventa_senza_capitolo(motore, mappa):
    voce = archivio.salva("annotazione", TESTO)
    motore.risposte = [risposta_archivista([{**RICORDO_VERO, "capitolo": 99}])]
    agenti.elabora_voce(voce)
    assert deposito.ricordi()[0]["capitolo"] is None


def test_archivista_aggiorna_la_mappa(motore, mappa):
    voce = archivio.salva("annotazione", TESTO)
    motore.risposte = [risposta_archivista(
        [RICORDO_VERO],
        capitoli=[{"id": 1, "stato": "pieno", "materiale": "Il porto"}, {"id": 99, "stato": "pieno", "materiale": "x"}],
        buchi_chiusi=["b1"], buchi_nuovi=["Chi era il padrone?", "Chi era il padrone?"],
        contraddizioni_risolte=["c1"], contraddizioni_nuove=["Due nomi diversi"],
    )]
    agenti.elabora_voce(voce)
    stato = deposito.mappa()
    assert stato["capitoli"][0]["stato"] == "pieno"
    assert stato["buchi"][0]["chiuso"] is True
    assert [b["testo"] for b in stato["buchi"]].count("Chi era il padrone?") == 1
    assert stato["contraddizioni"][0]["risolta"] is True
    assert stato["contraddizioni"][1]["testo"] == "Due nomi diversi"


def test_un_testo_lungo_si_salva_tutto_o_niente(motore, mappa):
    primo = "Lavoravo al porto ogni estate. " * 500
    secondo = "Il cuoco Marco insegnava bene. " * 500
    voce = archivio.salva("fonte", primo + "\n\n" + secondo)
    motore.risposte = [
        risposta_archivista([ricordo(citazione="Lavoravo al porto ogni estate")]),
        modulo_motore.ErroreMotore("Limite raggiunto"),
    ]
    with pytest.raises(modulo_motore.ErroreMotore):
        agenti.elabora_voce(voce)
    assert deposito.ricordi() == []
    assert voce.id not in deposito.elaborazioni()


def test_una_correzione_supera_un_ricordo_esistente(motore, mappa):
    id_ricordo = prepara_ricordi(1)[0]["id"]
    voce = archivio.salva("correzione", "Non era il porto: era il mercato.", capitolo=1, prima="Il porto")
    motore.risposte = [risposta_archivista(ricordi_superati=[id_ricordo, "r9999"])]
    agenti.elabora_voce(voce)
    assert deposito.ricordi()[0]["superato_da"] == voce.id
    assert "<testo_sostituito_dall_autore>" in motore.chiamate[0]["prompt"]


# Intervistatore ------------------------------------------------------------

def test_intervistatore_vede_tutto_e_salva_la_domanda(motore, mappa):
    prepara_ricordi(1)
    motore.risposte = [domanda(aggancio="lavoravo al porto")]
    risultato = agenti.prossima_domanda()
    assert risultato["stato"] == "domanda" and risultato["aggancio"] == "lavoravo al porto"
    prompt = motore.chiamate[0]["prompt"]
    assert TESTO in prompt and "Lavoravo al porto 0" in prompt and "Il porto" in prompt


def test_una_domanda_aperta_non_consuma_una_chiamata(motore, mappa):
    motore.risposte = [domanda()]
    prima = agenti.prossima_domanda()
    seconda = agenti.prossima_domanda()
    assert prima["id"] == seconda["id"] and seconda["stato"] == "domanda"
    assert len(motore.chiamate) == 1


def test_una_domanda_ripetuta_viene_rifiutata(motore, mappa):
    motore.risposte = [domanda()]
    fatta = agenti.prossima_domanda()
    deposito.chiudi_domanda(fatta["id"], "saltata")
    motore.risposte = [domanda(), domanda("Chi c'era al mercato?")]
    assert agenti.prossima_domanda()["testo"] == "Chi c'era al mercato?"
    assert "già stata fatta" in motore.chiamate[-1]["prompt"]


def test_due_risposte_non_valide_danno_un_errore_chiaro(motore, mappa):
    motore.risposte = [domanda("Chi era? E dove?"), domanda("Chi era? E dove?")]
    with pytest.raises(modulo_motore.ErroreMotore):
        agenti.prossima_domanda()
    assert deposito.domande() == []


def test_un_aggancio_inventato_non_si_mostra(motore, mappa):
    archivio.salva("annotazione", TESTO)
    motore.risposte = [domanda(aggancio="parole mai dette prima")]
    assert agenti.prossima_domanda()["aggancio"] == ""


def test_la_pausa_usa_il_testo_fisso_e_non_crea_domande(motore, mappa):
    motore.risposte = [domanda(stato="pausa")]
    risultato = agenti.prossima_domanda()
    assert risultato == {"stato": "pausa", "messaggio": agenti.MESSAGGIO_PAUSA}
    assert "112" in risultato["messaggio"]
    assert deposito.domande() == []


def test_per_la_pausa_l_intervistatore_riceve_l_ultimo_testo_a_parte(motore, mappa):
    archivio.salva("annotazione", "Un testo vecchio.")
    archivio.salva("annotazione", "Il testo di adesso.")
    motore.risposte = [domanda()]
    agenti.prossima_domanda()
    blocco = motore.chiamate[0]["prompt"].split("<ultimo_testo", 1)[1]
    assert "Il testo di adesso." in blocco and "Un testo vecchio." not in blocco


@pytest.mark.parametrize("dettaglio, tipo, parola", [
    ("OAuth session expired. Please run /login", modulo_motore.NonCollegato, "claude auth login"),
    ("Not logged in", modulo_motore.NonCollegato, "claude auth login"),
    ("You've hit your limit", modulo_motore.ErroreMotore, "limite"),
    ("safeguards flagged this request", modulo_motore.ErroreMotore, "filtro"),
    ("boom", modulo_motore.ErroreMotore, "boom"),
])
def test_gli_errori_di_claude_diventano_istruzioni_chiare(dettaglio, tipo, parola):
    errore = modulo_motore._traduci_errore(dettaglio)
    assert isinstance(errore, tipo) and parola in str(errore)


def test_chi_riprende_lo_dice_all_intervistatore(motore, mappa):
    motore.risposte = [domanda()]
    agenti.prossima_domanda(riprende=True)
    assert "<riprende>" in motore.chiamate[0]["prompt"]


# Scrittore: privacy --------------------------------------------------------

def test_lo_scrittore_non_riceve_mai_i_ricordi_privati(motore, mappa):
    prepara_ricordi(3)
    voce = archivio.salva("annotazione", "La cosa del vicino resta privata qui.")
    segreto = ricordo(testo="Segreto del vicino", citazione="cosa del vicino", privacy="solo_appunti")
    deposito.applica_archivista(voce.id, [segreto], [], 0)
    id_buono = deposito.ricordi()[0]["id"]
    motore.risposte = [
        scrittura(paragrafo(frase("Lavoravo al porto.", [id_buono]))),
        {"segnalazioni": []},
    ]
    agenti.scrivi_bozza(1)
    assert "Segreto" not in motore.chiamate[0]["prompt"]
    assert "cosa del vicino" not in motore.chiamate[0]["prompt"]


def test_una_frase_che_cita_un_ricordo_privato_perde_la_fonte_e_viene_segnalata(motore, mappa):
    tutti = prepara_ricordi(4)
    id_privato = tutti[0]["id"]
    deposito.aggiorna_ricordo(id_privato, "solo_appunti", None, False)
    motore.risposte = [
        scrittura(paragrafo(frase("Lavoravo al porto.", [id_privato]))),
        {"segnalazioni": []},
    ]
    versione = agenti.scrivi_bozza(1)
    scritta = versione["paragrafi"][0]["frasi"][0]
    assert scritta["fonti"] == [] and len(scritta["segnalazioni"]) >= 1


def test_chi_e_fuori_dal_libro_non_arriva_allo_scrittore(motore, mappa):
    prepara_ricordi(3)
    voce = archivio.salva("annotazione", "Elena mi disse una cosa qualsiasi.")
    deposito.applica_archivista(
        voce.id, [ricordo(testo="Elena mi disse una cosa", citazione="Elena mi disse", persone=["Elena"])], [], 0,
    )
    deposito.scegli_persona("Elena", "niente", "")
    assert all("Elena" not in r["testo"] for r in deposito.ricordi_per_scrittore(1))


def test_il_nome_cambiato_arriva_allo_scrittore_con_il_nuovo_nome(motore, mappa):
    voce = archivio.salva("annotazione", "Elena mi disse una cosa qualsiasi.")
    deposito.applica_archivista(
        voce.id,
        [ricordo(testo="Elena mi disse una cosa", citazione="Elena mi disse", persone=["Elena"])],
        [], 0,
    )
    deposito.scegli_persona("Elena", "nome_cambiato", "Anna")
    testo = deposito.ricordi_per_scrittore(1)[0]
    assert testo["testo"].startswith("Anna") and "Elena" not in testo["citazione"]


def test_un_ricordo_superato_non_arriva_allo_scrittore(motore, mappa):
    id_ricordo = prepara_ricordi(1)[0]["id"]
    voce = archivio.salva("correzione", "Non era così.", capitolo=1)
    deposito.applica_archivista(voce.id, [], [cambiamento(ricordi_superati=[id_ricordo])], 0)
    assert deposito.ricordi_per_scrittore(1) == []


# Scrittore: correzioni protette --------------------------------------------

def prepara_bozza_con_correzione(motore):
    id_ricordo = prepara_ricordi(3)[0]["id"]
    motore.risposte = [
        scrittura(paragrafo(frase("Lavoravo al porto.", [id_ricordo])),
                  paragrafo(frase("D'estate faceva caldo.", [id_ricordo]))),
        {"segnalazioni": []},
    ]
    agenti.scrivi_bozza(1)
    agenti.correggi_paragrafo(1, "p2", "Questo l'ho scritto io, parola per parola.")
    return id_ricordo


def test_la_correzione_crea_una_versione_e_una_voce_d_archivio(motore, mappa):
    prepara_bozza_con_correzione(motore)
    assert deposito.versioni(1) == [1, 2]
    voce = archivio.leggi_tutte()[-1]
    assert voce.tipo == "correzione" and voce.testo == "Questo l'ho scritto io, parola per parola."
    assert voce.meta["prima"] == "D'estate faceva caldo."
    assert deposito.bozza(1, 1)["paragrafi"][1]["autore"] == "scrittore"


def test_lo_scrittore_non_puo_cambiare_un_paragrafo_protetto(motore, mappa):
    id_ricordo = prepara_bozza_con_correzione(motore)
    motore.risposte = [
        scrittura(
            paragrafo(frase("Testo cambiato di nascosto.", [id_ricordo]), blindato="p2"),
            paragrafo(frase("Lavoravo al porto, di nuovo.", [id_ricordo])),
        ),
        {"segnalazioni": []},
    ]
    versione = agenti.scrivi_bozza(1)
    protetto = versione["paragrafi"][0]
    assert protetto == {"id": "p2", "autore": "tu", "testo": "Questo l'ho scritto io, parola per parola."}
    assert versione["paragrafi"][1]["id"] != "p2"


def test_un_paragrafo_protetto_omesso_due_volte_non_si_perde(motore, mappa):
    id_ricordo = prepara_bozza_con_correzione(motore)
    senza = scrittura(paragrafo(frase("Solo un nuovo paragrafo.", [id_ricordo])))
    motore.risposte = [senza, senza, {"segnalazioni": []}]
    versione = agenti.scrivi_bozza(1)
    assert versione["paragrafi"][-1]["testo"] == "Questo l'ho scritto io, parola per parola."
    assert "mancavano questi paragrafi protetti: ['p2']" in motore.chiamate[-2]["prompt"]


def test_svuotare_un_paragrafo_lo_toglie_ma_resta_nella_versione_vecchia(motore, mappa):
    prepara_bozza_con_correzione(motore)
    agenti.correggi_paragrafo(1, "p1", "   ")
    assert [p["id"] for p in deposito.bozza(1)["paragrafi"]] == ["p2"]
    assert [p["id"] for p in deposito.bozza(1, 2)["paragrafi"]] == ["p1", "p2"]


def test_le_note_arrivano_allo_scrittore_ma_il_testo_sostituito_no(motore, mappa):
    id_ricordo = prepara_bozza_con_correzione(motore)
    archivio.salva("correzione", "Troppo romanzato.", capitolo=1)
    motore.risposte = [
        scrittura(paragrafo(frase("Lavoravo.", [id_ricordo])), paragrafo(frase("", []), blindato="p2")),
        {"segnalazioni": []},
    ]
    agenti.scrivi_bozza(1)
    assert "Troppo romanzato." in motore.chiamate[-2]["prompt"]


# Scrittore: controllo ------------------------------------------------------

def test_il_controllo_segnala_e_si_vede_nella_bozza(motore, mappa):
    id_ricordo = prepara_ricordi(3)[0]["id"]
    motore.risposte = [
        scrittura(paragrafo(frase("Lavoravo al porto.", [id_ricordo]), frase("Pioveva sempre.", [id_ricordo]))),
        {"segnalazioni": [{"indice": 1, "problema": "La pioggia non è nelle fonti."}, {"indice": 99, "problema": "x"}]},
    ]
    versione = agenti.scrivi_bozza(1)
    frasi = versione["paragrafi"][0]["frasi"]
    assert versione["controllo"] == "eseguito"
    assert frasi[0]["segnalazioni"] == [] and frasi[1]["segnalazioni"] == ["La pioggia non è nelle fonti."]
    assert "Pioveva sempre." in motore.chiamate[1]["prompt"]


def test_se_il_controllo_fallisce_la_bozza_resta_e_lo_dice(motore, mappa):
    id_ricordo = prepara_ricordi(3)[0]["id"]
    motore.risposte = [
        scrittura(paragrafo(frase("Lavoravo al porto.", [id_ricordo]))),
        modulo_motore.ErroreMotore("Limite"),
    ]
    assert agenti.scrivi_bozza(1)["controllo"] == "non_eseguito"


def test_le_domande_aperte_dello_scrittore_diventano_buchi(motore, mappa):
    id_ricordo = prepara_ricordi(3)[0]["id"]
    motore.risposte = [
        scrittura(paragrafo(frase("Lavoravo al porto.", [id_ricordo])), domande_aperte=["Che odore c'era?"]),
        {"segnalazioni": []},
    ]
    agenti.scrivi_bozza(1)
    assert any("Che odore c'era?" in b["testo"] for b in deposito.mappa()["buchi"])


def test_con_pochi_ricordi_lo_scrittore_dice_quanti_ne_mancano(motore, mappa):
    prepara_ricordi(2)
    with pytest.raises(modulo_motore.ErroreMotore, match="almeno 3"):
        agenti.scrivi_bozza(1)
    assert motore.chiamate == []

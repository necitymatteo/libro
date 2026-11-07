"""Server locale. Risponde solo a questo Mac e rifiuta le richieste di altri siti."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agenti, archivio, controlli, deposito, design, impostazioni, motore
from .coda import coda

_STATICI = Path(__file__).resolve().parent / "statici"
_CHIAVI_IN_CORSO = ("annotazione", "risposta", "chat")
_POLITICA = (
    "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; "
    "base-uri 'none'; form-action 'none'"
)


@asynccontextmanager
async def _ciclo(_: FastAPI):
    coda.avvia()
    yield


app = FastAPI(title="Il mio libro", docs_url=None, redoc_url=None, openapi_url=None, lifespan=_ciclo)


@app.middleware("http")
async def _protezione(richiesta: Request, prosegui):
    """Un sito aperto nel browser non deve poter leggere o scrivere in questa app."""
    porta = impostazioni.porta()
    consentiti = {f"127.0.0.1:{porta}", f"localhost:{porta}"}
    host = richiesta.headers.get("host", "")
    if host not in consentiti:
        return JSONResponse({"detail": "Host non consentito."}, status_code=403)
    if richiesta.method not in ("GET", "HEAD"):
        if richiesta.headers.get("origin") != f"http://{host}":
            return JSONResponse({"detail": "Origine non consentita."}, status_code=403)
        if not richiesta.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse({"detail": "Formato non consentito."}, status_code=415)
    risposta = await prosegui(richiesta)
    risposta.headers["Content-Security-Policy"] = _POLITICA
    risposta.headers["X-Content-Type-Options"] = "nosniff"
    risposta.headers["Referrer-Policy"] = "no-referrer"
    risposta.headers["Cache-Control"] = "no-store"
    return risposta


class Testo(BaseModel):
    testo: str


class Annotazione(BaseModel):
    testo: str
    spunto: str | None = None


class Prossima(BaseModel):
    riprende: bool = False


class CambioRicordo(BaseModel):
    privacy: str | None = None
    capitolo: int | None = None
    cambia_capitolo: bool = False


class NuovoDesign(BaseModel):
    design: dict
    etichetta: str = ""


class TornaDesign(BaseModel):
    versione: int


class DatiLibro(BaseModel):
    titolo: str | None = None
    autore: str | None = None


class NuovaStruttura(BaseModel):
    parti: list[dict]


class EsitoProposta(BaseModel):
    azione: str


class SceltaPersona(BaseModel):
    nome: str
    scelta: str
    alias: str = ""


def _testo_obbligatorio(corpo: Testo) -> str:
    if not corpo.testo.strip():
        raise HTTPException(422, "Il testo è vuoto.")
    return corpo.testo


def _errore_motore(errore: motore.ErroreMotore) -> HTTPException:
    return HTTPException(503, str(errore))


@app.get("/api/salute")
def salute() -> dict:
    return {"ok": True}


@app.get("/api/stato")
def stato() -> dict:
    """Quello che serve alla barra laterale su ogni pagina."""
    mappa = deposito.mappa()
    ricordi = [r for r in deposito.ricordi() if not r["superato_da"]]
    capitoli = []
    da_verificare = 0
    capitolo_da_verificare = None
    for voce in deposito.capitoli_numerati(mappa):
        frasi = _frasi_da_verificare(deposito.bozza(voce["id"]))
        da_verificare += frasi
        if frasi and capitolo_da_verificare is None:
            capitolo_da_verificare = voce["id"]
        capitoli.append({
            "id": voce["id"],
            "titolo": voce["titolo"],
            "numero": voce["numero"],
            "parte": voce["parte"],
            "ricordi": sum(1 for r in ricordi if r["capitolo"] == voce["id"]),
            "bozza": bool(deposito.versioni(voce["id"])),
        })
    parti = [
        {
            "id": parte["id"],
            "numero": parte["numero"],
            "titolo": parte["titolo"],
            "ricordi": sum(c["ricordi"] for c in capitoli if c["parte"] == parte["id"]),
        }
        for parte in deposito.struttura(mappa)
    ]
    return {
        "parti": parti,
        "da_raccontare": len(_buchi_del_libro(mappa)),
        "da_verificare": da_verificare,
        "capitolo_da_verificare": capitolo_da_verificare,
        "persone_da_decidere": sum(1 for p in deposito.persone().values() if p["scelta"] == "da_decidere"),
        "titolo": mappa["titolo"],
        "ricordi": len(ricordi),
        "capitoli": capitoli,
        "scritti": sum(1 for c in capitoli if c["bozza"]),
        "senza_capitolo": sum(1 for r in ricordi if r["capitolo"] is None),
        "domanda_pronta": deposito.domanda_aperta() is not None,
        "coda": coda.stato(),
    }


@app.post("/api/coda/riprova")
def riprova(_: dict) -> dict:
    coda.recupera()
    return coda.stato()


# Archivio ------------------------------------------------------------------

@app.get("/api/archivio")
def elenco_archivio() -> list[dict]:
    elaborazioni = deposito.elaborazioni()
    return [
        {
            "id": voce.id,
            "tipo": voce.tipo,
            "creato": voce.creato,
            "testo": voce.testo,
            "domanda": voce.meta.get("domanda"),
            "prima": voce.meta.get("prima"),
            "elaborazione": elaborazioni.get(voce.id, {}).get("stato", "in_attesa"),
        }
        for voce in reversed(archivio.leggi_tutte())
        if voce.tipo != "chat"
    ]


@app.post("/api/annotazioni")
def nuova_annotazione(corpo: Annotazione) -> dict:
    testo = _testo_obbligatorio(corpo)
    # Lo spunto arriva all'archivista come la domanda di una risposta.
    voce = archivio.salva("annotazione", testo, **({"domanda": corpo.spunto} if corpo.spunto else {}))
    deposito.salva_testo_in_corso("annotazione", "")
    coda.aggiungi(voce.id)
    risposta = {"id": voce.id}
    if controlli.segnali_disagio(testo):
        risposta["pausa"] = agenti.MESSAGGIO_PAUSA
    return risposta


@app.get("/api/in-corso/{chiave}")
def leggi_in_corso(chiave: str) -> dict:
    if chiave not in _CHIAVI_IN_CORSO:
        raise HTTPException(404, "Chiave sconosciuta.")
    return {"testo": deposito.testo_in_corso(chiave)}


@app.post("/api/in-corso/{chiave}")
def scrivi_in_corso(chiave: str, corpo: Testo) -> dict:
    if chiave not in _CHIAVI_IN_CORSO:
        raise HTTPException(404, "Chiave sconosciuta.")
    deposito.salva_testo_in_corso(chiave, corpo.testo)
    return {"ok": True}


# Domande -------------------------------------------------------------------

@app.get("/api/domande")
def domande_chiuse() -> list[dict]:
    """Le ultime domande chiuse, dalla piu' recente, con la risposta dell'autore."""
    chiuse = [d for d in deposito.domande() if d["stato"] != "aperta"]
    risultato = []
    for domanda in reversed(chiuse[-12:]):
        voce = archivio.leggi(domanda["risposta"]) if domanda["risposta"] else None
        risultato.append({
            "id": domanda["id"],
            "testo": domanda["testo"],
            "stato": domanda["stato"],
            "risposta": voce.testo if voce else None,
        })
    return risultato


@app.post("/api/domande/prossima")
def domanda_prossima(corpo: Prossima) -> dict:
    try:
        return agenti.prossima_domanda(corpo.riprende)
    except motore.ErroreMotore as errore:
        raise _errore_motore(errore) from errore


def _domanda_aperta(domanda_id: str) -> dict:
    for domanda in deposito.domande():
        if domanda["id"] == domanda_id:
            if domanda["stato"] != "aperta":
                raise HTTPException(409, "Questa domanda è già chiusa.")
            return domanda
    raise HTTPException(404, "Domanda non trovata.")


@app.post("/api/domande/{domanda_id}/risposta")
def rispondi(domanda_id: str, corpo: Testo) -> dict:
    testo = _testo_obbligatorio(corpo)
    domanda = _domanda_aperta(domanda_id)
    voce = archivio.salva(
        "risposta", testo, domanda=domanda["testo"], domanda_id=domanda_id, capitolo=domanda["capitolo"],
    )
    deposito.chiudi_domanda(domanda_id, "risposta", voce.id)
    deposito.salva_testo_in_corso("risposta", "")
    coda.aggiungi(voce.id)
    risposta = {"id": voce.id}
    if controlli.segnali_disagio(testo):
        risposta["pausa"] = agenti.MESSAGGIO_PAUSA
    return risposta


@app.post("/api/domande/{domanda_id}/salta")
def salta(domanda_id: str, _: dict) -> dict:
    _domanda_aperta(domanda_id)
    deposito.chiudi_domanda(domanda_id, "saltata")
    return {"ok": True}


# Libro ---------------------------------------------------------------------

def _buchi_del_libro(mappa: dict) -> list[dict]:
    """I buchi grandi. I dettagli chiesti dallo scrittore stanno nel loro capitolo."""
    return [b for b in mappa["buchi"] if not b["chiuso"] and b.get("capitolo") is None]


def _frasi_da_verificare(bozza_capitolo: dict | None) -> int:
    if not bozza_capitolo:
        return 0
    return sum(
        1
        for paragrafo in bozza_capitolo["paragrafi"]
        if paragrafo["autore"] == "scrittore"
        for frase in paragrafo["frasi"]
        if frase["segnalazioni"]
    )


@app.get("/api/libro")
def libro() -> dict:
    mappa = deposito.mappa()
    ricordi = [r for r in deposito.ricordi() if not r["superato_da"]]
    capitoli = []
    for capitolo in deposito.capitoli_numerati(mappa):
        propri = [r for r in ricordi if r["capitolo"] == capitolo["id"]]
        capitoli.append({
            **capitolo,
            "ricordi_libro": sum(1 for r in propri if r["privacy"] == "libro"),
            "ricordi_privati": sum(1 for r in propri if r["privacy"] != "libro"),
            "versioni": len(deposito.versioni(capitolo["id"])),
            "lavoro": coda.lavoro_capitolo(capitolo["id"]),
            "da_verificare": _frasi_da_verificare(deposito.bozza(capitolo["id"])),
        })
    return {
        "titolo": mappa["titolo"],
        "filo": mappa["filo"],
        "parti": [
            {"id": p["id"], "numero": p["numero"], "titolo": p["titolo"], "tema": p["tema"]}
            for p in deposito.struttura(mappa)
        ],
        "ricordi_minimi": agenti.RICORDI_MINIMI_PER_BOZZA,
        "ultimi_ricordi": [
            {"id": r["id"], "testo": r["testo"], "capitolo": r["capitolo"]} for r in reversed(ricordi[-5:])
        ],
        "capitoli": capitoli,
        "buchi": _buchi_del_libro(mappa),
        "contraddizioni": [c for c in mappa["contraddizioni"] if not c["risolta"]],
        "decisioni": mappa["decisioni"],
        "persone": deposito.persone(),
        "senza_capitolo": sum(1 for r in ricordi if r["capitolo"] is None),
    }


@app.get("/api/capitoli/{capitolo_id}")
def capitolo(capitolo_id: int, versione: int | None = None) -> dict:
    ricordi = deposito.ricordi()
    mappa = deposito.mappa()
    numerati = deposito.capitoli_numerati(mappa)
    indice = [{"id": c["id"], "titolo": c["titolo"], "numero": c["numero"]} for c in numerati]
    if capitolo_id == 0:
        return {
            "capitolo": {"id": 0, "titolo": "Ricordi senza sottocapitolo", "tema": "", "materiale": "", "stato": "", "numero": ""},
            "indice": indice,
            "ricordi": [r for r in ricordi if r["capitolo"] is None and not r["superato_da"]],
            "bozza": None,
            "versioni": [],
            "lavoro": None,
            "fonti": {},
            "buchi": [],
            "ricordi_minimi": agenti.RICORDI_MINIMI_PER_BOZZA,
        }
    dati = next((c for c in numerati if c["id"] == capitolo_id), None)
    if dati is None:
        raise HTTPException(404, "Sottocapitolo non trovato.")
    parte = next(p for p in deposito.struttura(mappa) if p["id"] == dati["parte"])
    dati = {**dati, "parte_numero": parte["numero"], "parte_titolo": parte["titolo"]}
    bozza = deposito.bozza(capitolo_id, versione)
    per_id = {r["id"]: r for r in ricordi}
    usati = {
        fonte
        for paragrafo in (bozza["paragrafi"] if bozza else [])
        if paragrafo["autore"] == "scrittore"
        for frase in paragrafo["frasi"]
        for fonte in frase["fonti"]
    }
    return {
        "capitolo": dati,
        "indice": indice,
        "ricordi": [r for r in ricordi if r["capitolo"] == capitolo_id],
        "bozza": bozza,
        "versioni": deposito.versioni(capitolo_id),
        "lavoro": coda.lavoro_capitolo(capitolo_id),
        "buchi": [b for b in mappa["buchi"] if b.get("capitolo") == capitolo_id and not b["chiuso"]],
        "ricordi_minimi": agenti.RICORDI_MINIMI_PER_BOZZA,
        "fonti": {
            f: {"testo": per_id[f]["testo"], "citazione": per_id[f]["citazione"]}
            for f in usati if f in per_id
        },
    }


@app.post("/api/capitoli/{capitolo_id}/bozza")
def bozza(capitolo_id: int, _: dict) -> dict:
    if deposito.capitolo(capitolo_id) is None:
        raise HTTPException(404, "Sottocapitolo non trovato.")
    return coda.avvia_bozza(capitolo_id)


@app.post("/api/capitoli/{capitolo_id}/paragrafi/{paragrafo_id}")
def correggi(capitolo_id: int, paragrafo_id: str, corpo: Testo) -> dict:
    try:
        versione, voce = agenti.correggi_paragrafo(capitolo_id, paragrafo_id, corpo.testo)
    except KeyError as errore:
        raise HTTPException(404, "Paragrafo non trovato.") from errore
    coda.aggiungi(voce.id)
    return {"versione": versione["versione"]}


@app.post("/api/capitoli/{capitolo_id}/nota")
def nota(capitolo_id: int, corpo: Testo) -> dict:
    if deposito.capitolo(capitolo_id) is None:
        raise HTTPException(404, "Sottocapitolo non trovato.")
    voce = archivio.salva("correzione", _testo_obbligatorio(corpo), capitolo=capitolo_id)
    coda.aggiungi(voce.id)
    return {"id": voce.id}


@app.post("/api/ricordi/{ricordo_id}")
def cambia_ricordo(ricordo_id: str, corpo: CambioRicordo) -> dict:
    if corpo.privacy not in (None, "libro", "solo_appunti"):
        raise HTTPException(422, "Privacy sconosciuta.")
    if corpo.cambia_capitolo and corpo.capitolo is not None and deposito.capitolo(corpo.capitolo) is None:
        raise HTTPException(404, "Sottocapitolo non trovato.")
    try:
        return deposito.aggiorna_ricordo(ricordo_id, corpo.privacy, corpo.capitolo, corpo.cambia_capitolo)
    except KeyError as errore:
        raise HTTPException(404, "Ricordo non trovato.") from errore


@app.post("/api/persone")
def cambia_persona(corpo: SceltaPersona) -> dict:
    if not corpo.nome.strip():
        raise HTTPException(422, "Il nome è vuoto.")
    if corpo.scelta == "nome_cambiato" and not corpo.alias.strip():
        raise HTTPException(422, "Scrivi il nome da usare nel libro.")
    try:
        deposito.scegli_persona(corpo.nome, corpo.scelta, corpo.alias.strip())
    except ValueError as errore:
        raise HTTPException(422, str(errore)) from errore
    return {"ok": True}


# Anteprima -----------------------------------------------------------------

def _da_riscrivere(capitolo_id: int, bozza: dict) -> int:
    """Frasi scritte prima che cambiassero privacy, persone o ricordi."""
    permessi = {r["id"] for r in deposito.ricordi_per_scrittore(capitolo_id)}
    cambiati = [
        nome for nome, scelta in deposito.persone().items()
        if scelta["scelta"] == "nome_cambiato" and scelta.get("alias")
    ]
    totale = 0
    for paragrafo in bozza["paragrafi"]:
        if paragrafo["autore"] != "scrittore":
            continue
        for frase in paragrafo["frasi"]:
            fuori = any(f not in permessi for f in frase["fonti"])
            nome_vecchio = any(nome in frase["testo"] for nome in cambiati)
            totale += 1 if fuori or nome_vecchio else 0
    return totale


@app.get("/api/anteprima")
def anteprima() -> dict:
    """Il libro come uscirebbe oggi: solo le bozze, senza note, ricordi o appunti."""
    mappa = deposito.mappa()
    scritti, mancanti = [], []
    for voce in deposito.capitoli_numerati(mappa):
        bozza_capitolo = deposito.bozza(voce["id"])
        if bozza_capitolo:
            scritti.append({
                "id": voce["id"],
                "numero": voce["numero"],
                "parte": voce["parte"],
                "titolo": voce["titolo"],
                "paragrafi": [agenti.testo_paragrafo(p) for p in bozza_capitolo["paragrafi"]],
                "da_verificare": _frasi_da_verificare(bozza_capitolo),
                "da_riscrivere": _da_riscrivere(voce["id"], bozza_capitolo),
            })
        else:
            disponibili = len(deposito.ricordi_per_scrittore(voce["id"]))
            mancanti.append({
                "id": voce["id"],
                "titolo": voce["titolo"],
                "ricordi": disponibili,
                "scrivibile": disponibili >= agenti.RICORDI_MINIMI_PER_BOZZA,
                "lavoro": coda.lavoro_capitolo(voce["id"]),
            })
    versione = deposito.design_versione()
    parti = []
    for parte in deposito.struttura(mappa):
        sotto = [c for c in scritti if c["parte"] == parte["id"]]
        if sotto:
            parti.append({"id": parte["id"], "numero": parte["numero"], "titolo": parte["titolo"], "sotto": sotto})
    return {
        "titolo": mappa["titolo"],
        "autore": mappa.get("autore", ""),
        "parti": parti,
        "capitoli": scritti,
        "mancanti": mancanti,
        "design": agenti.design_corrente(),
        "versione_design": versione["versione"] if versione else 0,
        "versioni_design": deposito.versioni_design(),
        "predefiniti": design.PREDEFINITI,
        "proposte": [design.normalizza(p)[0] for p in deposito.proposte_design()],
        "catalogo": design.catalogo(),
    }


@app.post("/api/struttura")
def cambia_struttura(corpo: NuovaStruttura) -> dict:
    esistenti = {c["id"]: c["titolo"] for c in deposito.mappa()["capitoli"]}
    problemi = controlli.problemi_struttura(corpo.parti, esistenti, deposito.capitoli_con_materiale())
    if problemi:
        raise HTTPException(422, " ".join(problemi))
    deposito.applica_struttura(corpo.parti)
    return {"ok": True}


@app.get("/api/chat")
def leggi_chat() -> dict:
    messaggi = deposito.messaggi_chat()
    return {
        "messaggi": messaggi,
        "in_corso": coda.chat_in_corso(),
        "contesto": agenti.contesto_chat(),
    }


@app.post("/api/chat")
def scrivi_in_chat(corpo: Testo) -> dict:
    testo = _testo_obbligatorio(corpo)
    if coda.chat_in_corso():
        raise HTTPException(409, "Aspetta la risposta prima di scrivere ancora.")
    # Le parole dell'autore entrano nell'archivio come ogni altro testo.
    voce = archivio.salva("chat", testo)
    if len(testo.split()) >= agenti.PAROLE_MINIME_PER_ARCHIVISTA:
        coda.aggiungi(voce.id)
    else:
        deposito.segna_elaborazione(voce.id, "fatto", ricordi=0, scartati=0)
    deposito.togli_errori_chat()
    messaggio = deposito.aggiungi_messaggio("tu", testo, voce=voce.id)
    deposito.salva_testo_in_corso("chat", "")
    if controlli.segnali_disagio(testo):
        deposito.aggiungi_messaggio("agente", agenti.MESSAGGIO_PAUSA, pausa=True)
        return {"id": messaggio["id"], "pausa": True}
    coda.avvia_chat()
    return {"id": messaggio["id"]}


@app.post("/api/chat/riprova")
def riprova_chat(_: dict) -> dict:
    deposito.togli_errori_chat()
    messaggi = deposito.messaggi_chat()
    if not messaggi or messaggi[-1]["autore"] != "tu":
        return {"ok": False}
    return {"ok": coda.avvia_chat()}


@app.post("/api/chat/{messaggio_id}/proposta")
def decidi_proposta(messaggio_id: str, corpo: EsitoProposta) -> dict:
    try:
        if corpo.azione == "applica":
            agenti.applica_proposta(messaggio_id)
        elif corpo.azione == "scarta":
            deposito.aggiorna_messaggio(messaggio_id, esito_proposta="scartata")
        else:
            raise HTTPException(422, "Azione sconosciuta.")
    except KeyError as errore:
        raise HTTPException(404, "Proposta non trovata.") from errore
    except ValueError as errore:
        raise HTTPException(409, f"La struttura è cambiata e la proposta non vale più. {errore}") from errore
    return {"ok": True}


@app.post("/api/bozze/mancanti")
def bozze_mancanti(_: dict) -> dict:
    return {"lavori": coda.avvia_bozze_mancanti()}


@app.post("/api/libro/dati")
def dati_libro(corpo: DatiLibro) -> dict:
    deposito.cambia_dati_libro(corpo.titolo, corpo.autore)
    return {"ok": True}


@app.post("/api/design")
def scegli_design(corpo: NuovoDesign) -> dict:
    nuovo, avvisi = design.normalizza(corpo.design, agenti.design_corrente())
    versione = deposito.salva_design(nuovo, corpo.etichetta or nuovo["nome"])
    return {"versione": versione["versione"], "avvisi": avvisi}


@app.post("/api/design/torna")
def torna_design(corpo: TornaDesign) -> dict:
    vecchia = deposito.design_versione(corpo.versione)
    if vecchia is None:
        raise HTTPException(404, "Versione non trovata.")
    versione = deposito.salva_design(vecchia["design"], f"Ritorno alla versione {corpo.versione}")
    return {"versione": versione["versione"]}


@app.post("/api/design/modifica")
def modifica(corpo: Testo) -> dict:
    try:
        return agenti.modifica_design(_testo_obbligatorio(corpo))
    except motore.ErroreMotore as errore:
        raise _errore_motore(errore) from errore


@app.post("/api/design/proposte")
def proposte(_: dict) -> dict:
    try:
        return {"proposte": agenti.proponi_design()}
    except motore.ErroreMotore as errore:
        raise _errore_motore(errore) from errore


# Pagine --------------------------------------------------------------------

@app.get("/")
def pagina() -> FileResponse:
    return FileResponse(_STATICI / "index.html")


app.mount("/statici", StaticFiles(directory=_STATICI), name="statici")

"""I file derivati: ricordi, mappa, domande, persone e versioni delle bozze.

Ogni scrittura passa da un file temporaneo e poi sostituisce quello vecchio, cosi'
un crash non lascia mai un file a meta'. Le versioni delle bozze non si sovrascrivono.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from . import impostazioni

BLOCCO = threading.RLock()
SCELTE_PERSONA = ("da_decidere", "consenso", "nome_cambiato", "niente")
MAPPA_VUOTA = {
    "titolo": "Il mio libro",
    "autore": "",
    "filo": "",
    "parti": [],
    "capitoli": [],
    "buchi": [],
    "contraddizioni": [],
    "domande_suggerite": [],
    "decisioni": [],
    "regole": [],
}


def _scrivi_atomico(percorso: Path, valore) -> None:
    percorso.parent.mkdir(parents=True, exist_ok=True)
    descrittore, temporaneo = tempfile.mkstemp(dir=percorso.parent, suffix=".tmp")
    with os.fdopen(descrittore, "w", encoding="utf-8") as file:
        json.dump(valore, file, ensure_ascii=False, indent=2)
        file.flush()
        os.fsync(file.fileno())
    os.chmod(temporaneo, 0o600)
    os.replace(temporaneo, percorso)


def _leggi(nome: str, predefinito):
    percorso = impostazioni.dati() / nome
    if not percorso.exists():
        return predefinito
    return json.loads(percorso.read_text(encoding="utf-8"))


def _scrivi(nome: str, valore) -> None:
    _scrivi_atomico(impostazioni.dati() / nome, valore)


def adesso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# Mappa ---------------------------------------------------------------------

def mappa() -> dict:
    return _leggi("mappa.json", json.loads(json.dumps(MAPPA_VUOTA)))


def salva_mappa(valore: dict) -> None:
    _scrivi("mappa.json", valore)


# La struttura: nel codice un "capitolo" e' l'unita' di scrittura, che sullo schermo si chiama
# sottocapitolo. Una "parte" raggruppa i capitoli, e sullo schermo si chiama capitolo. Cosi'
# ricordi e bozze restano legati ai loro numeri anche quando la struttura cambia.

def struttura(stato: dict | None = None) -> list[dict]:
    """Le parti nell'ordine del libro, ognuna con i suoi capitoli numerati (1.1, 1.2, 2.1)."""
    stato = stato or mappa()
    per_id = {c["id"]: c for c in stato["capitoli"]}
    visti: set[int] = set()
    grezze = []
    for parte in stato.get("parti", []):
        ids = [i for i in parte["capitoli"] if i in per_id and i not in visti]
        visti.update(ids)
        if ids:
            grezze.append({**parte, "capitoli": ids})
    resto = [c["id"] for c in stato["capitoli"] if c["id"] not in visti]
    if resto:
        grezze.append({
            "id": "senza-parte",
            "titolo": "Da sistemare" if grezze else "Il libro",
            "tema": "",
            "capitoli": resto,
        })
    risultato = []
    for numero, parte in enumerate(grezze, 1):
        voci = [
            {**per_id[i], "numero": f"{numero}.{posizione}", "parte": parte["id"]}
            for posizione, i in enumerate(parte["capitoli"], 1)
        ]
        risultato.append({
            "id": parte["id"], "numero": numero, "titolo": parte["titolo"],
            "tema": parte.get("tema", ""), "capitoli": voci,
        })
    return risultato


def capitoli_numerati(stato: dict | None = None) -> list[dict]:
    """Tutti i capitoli nell'ordine del libro, con numero e parte."""
    return [voce for parte in struttura(stato) for voce in parte["capitoli"]]


def capitoli_con_materiale() -> set[int]:
    con_ricordi = {r["capitolo"] for r in ricordi() if r["capitolo"] is not None}
    return con_ricordi | {c["id"] for c in mappa()["capitoli"] if versioni(c["id"])}


def applica_struttura(parti: list[dict] | None, titolo: str | None = None, filo: str | None = None) -> None:
    """Cambia struttura, titolo o filo. La mappa di prima resta in dati/storico-mappa."""
    with BLOCCO:
        stato = mappa()
        storico = impostazioni.dati() / "storico-mappa"
        numero = len(list(storico.glob("*.json"))) + 1 if storico.exists() else 1
        _scrivi_atomico(storico / f"{numero:04d}.json", stato)
        if titolo is not None:
            stato["titolo"] = titolo.strip()
        if filo is not None:
            stato["filo"] = filo.strip()
        if parti is not None:
            per_id = {c["id"]: c for c in stato["capitoli"]}
            prossimo = max(per_id, default=0) + 1
            capitoli_nuovi = []
            parti_nuove = []
            for posizione, parte in enumerate(parti, 1):
                ids = []
                for voce in parte["capitoli"]:
                    identificativo = voce.get("id")
                    if identificativo is None:
                        identificativo = prossimo
                        prossimo += 1
                        elemento = {"id": identificativo, "titolo": "", "tema": "", "materiale": "", "stato": "vuoto"}
                    else:
                        elemento = per_id[identificativo]
                    elemento["titolo"] = voce["titolo"].strip()
                    capitoli_nuovi.append(elemento)
                    ids.append(identificativo)
                parti_nuove.append({
                    "id": f"parte{posizione}",
                    "titolo": parte["titolo"].strip(),
                    "tema": str(parte.get("tema") or "").strip(),
                    "capitoli": ids,
                })
            stato["capitoli"] = capitoli_nuovi
            stato["parti"] = parti_nuove
        salva_mappa(stato)


def capitolo(capitolo_id: int) -> dict | None:
    for voce in mappa()["capitoli"]:
        if voce["id"] == capitolo_id:
            return voce
    return None


def _nuovo_id(prefisso: str, elementi: list[dict]) -> str:
    numeri = [int(e["id"][len(prefisso):]) for e in elementi]
    return f"{prefisso}{max(numeri, default=0) + 1}"


def aggiungi_buchi(testi: list[str], capitolo_id: int | None = None) -> None:
    with BLOCCO:
        stato = mappa()
        esistenti = {b["testo"] for b in stato["buchi"]}
        for testo in testi:
            if testo.strip() and testo not in esistenti:
                stato["buchi"].append({
                    "id": _nuovo_id("b", stato["buchi"]),
                    "testo": testo,
                    "chiuso": False,
                    "capitolo": capitolo_id,
                })
                esistenti.add(testo)
        salva_mappa(stato)


# Ricordi -------------------------------------------------------------------

def ricordi() -> list[dict]:
    return _leggi("ricordi.json", [])


def aggiorna_ricordo(ricordo_id: str, privacy: str | None, capitolo_id, cambia_capitolo: bool) -> dict:
    with BLOCCO:
        tutti = ricordi()
        for ricordo in tutti:
            if ricordo["id"] != ricordo_id:
                continue
            if privacy is not None:
                ricordo["privacy"] = privacy
            if cambia_capitolo:
                ricordo["capitolo"] = capitolo_id
            _scrivi("ricordi.json", tutti)
            return ricordo
    raise KeyError(ricordo_id)


def applica_archivista(voce_id: str, nuovi: list[dict], cambiamenti: list[dict], scartati: int) -> None:
    """Applica in un colpo solo il lavoro dell'archivista su una voce."""
    with BLOCCO:
        tutti = ricordi()
        ultimo = max((int(r["id"][1:]) for r in tutti), default=0)
        for ricordo in nuovi:
            ultimo += 1
            tutti.append({**ricordo, "id": f"r{ultimo:04d}", "fonte": voce_id, "superato_da": None})
        registra_persone([nome for ricordo in nuovi for nome in ricordo["persone"]])

        stato = mappa()
        capitoli = {c["id"]: c for c in stato["capitoli"]}
        for cambiamento in cambiamenti:
            for ricordo_id in cambiamento["ricordi_superati"]:
                for ricordo in tutti:
                    if ricordo["id"] == ricordo_id:
                        ricordo["superato_da"] = voce_id
            for voce in cambiamento["capitoli"]:
                if voce["id"] in capitoli:
                    capitoli[voce["id"]]["stato"] = voce["stato"]
                    capitoli[voce["id"]]["materiale"] = voce["materiale"]
            for elemento in stato["buchi"]:
                if elemento["id"] in cambiamento["buchi_chiusi"]:
                    elemento["chiuso"] = True
            for elemento in stato["contraddizioni"]:
                if elemento["id"] in cambiamento["contraddizioni_risolte"]:
                    elemento["risolta"] = True
            testi = {c["testo"] for c in stato["contraddizioni"]}
            for testo in cambiamento["contraddizioni_nuove"]:
                if testo.strip() and testo not in testi:
                    stato["contraddizioni"].append({
                        "id": _nuovo_id("c", stato["contraddizioni"]),
                        "testo": testo,
                        "risolta": False,
                    })
                    testi.add(testo)
        _scrivi("ricordi.json", tutti)
        salva_mappa(stato)
        for cambiamento in cambiamenti:
            aggiungi_buchi(cambiamento["buchi_nuovi"])
        segna_elaborazione(voce_id, "fatto", ricordi=len(nuovi), scartati=scartati)


def ricordi_per_scrittore(capitolo_id: int) -> list[dict]:
    """Solo cio' che puo' finire nel libro. Il filtro sta nel codice, non nel prompt."""
    scelte = persone()
    esclusi = {nome for nome, s in scelte.items() if s["scelta"] == "niente"}
    alias = {
        nome: s["alias"]
        for nome, s in scelte.items()
        if s["scelta"] == "nome_cambiato" and s.get("alias")
    }
    risultato = []
    for ricordo in ricordi():
        if ricordo["capitolo"] != capitolo_id or ricordo["privacy"] != "libro":
            continue
        if ricordo["superato_da"] or esclusi.intersection(ricordo["persone"]):
            continue
        copia = dict(ricordo)
        for nome, sostituto in alias.items():
            modello = re.compile(rf"\b{re.escape(nome)}\b")
            copia["testo"] = modello.sub(sostituto, copia["testo"])
            copia["citazione"] = modello.sub(sostituto, copia["citazione"])
        risultato.append(copia)
    return risultato


# Persone -------------------------------------------------------------------

def persone() -> dict:
    return _leggi("persone.json", {})


def registra_persone(nomi: list[str]) -> None:
    with BLOCCO:
        stato = persone()
        cambiato = False
        for nome in nomi:
            if nome.strip() and nome not in stato:
                stato[nome] = {"scelta": "da_decidere", "alias": ""}
                cambiato = True
        if cambiato:
            _scrivi("persone.json", stato)


def scegli_persona(nome: str, scelta: str, alias: str) -> None:
    if scelta not in SCELTE_PERSONA:
        raise ValueError(f"Scelta sconosciuta: {scelta}")
    with BLOCCO:
        stato = persone()
        stato[nome] = {"scelta": scelta, "alias": alias}
        _scrivi("persone.json", stato)


# Domande -------------------------------------------------------------------

def domande() -> list[dict]:
    return _leggi("domande.json", [])


def domanda_aperta() -> dict | None:
    for domanda in domande():
        if domanda["stato"] == "aperta":
            return domanda
    return None


def aggiungi_domanda(testo: str, tipo: str, aggancio: str, capitolo_id, motivo: str) -> dict:
    with BLOCCO:
        tutte = domande()
        domanda = {
            "id": f"d{len(tutte) + 1:04d}",
            "testo": testo,
            "tipo": tipo,
            "aggancio": aggancio,
            "capitolo": capitolo_id,
            "motivo": motivo,
            "creata": adesso(),
            "stato": "aperta",
            "risposta": None,
        }
        tutte.append(domanda)
        _scrivi("domande.json", tutte)
        return domanda


def chiudi_domanda(domanda_id: str, stato: str, risposta: str | None = None) -> None:
    with BLOCCO:
        tutte = domande()
        for domanda in tutte:
            if domanda["id"] == domanda_id:
                domanda["stato"] = stato
                domanda["risposta"] = risposta
                _scrivi("domande.json", tutte)
                return
    raise KeyError(domanda_id)


# Elaborazioni --------------------------------------------------------------

def elaborazioni() -> dict:
    return _leggi("elaborazioni.json", {})


def segna_elaborazione(voce_id: str, stato: str, **dettagli) -> None:
    with BLOCCO:
        tutte = elaborazioni()
        tutte[voce_id] = {"stato": stato, "quando": adesso(), **dettagli}
        _scrivi("elaborazioni.json", tutte)


# Testo in corso ------------------------------------------------------------

def testo_in_corso(chiave: str) -> str:
    return _leggi("in-corso.json", {}).get(chiave, "")


def salva_testo_in_corso(chiave: str, testo: str) -> None:
    with BLOCCO:
        stato = _leggi("in-corso.json", {})
        stato[chiave] = testo
        _scrivi("in-corso.json", stato)


# Bozze ---------------------------------------------------------------------

def _cartella_capitolo(capitolo_id: int) -> Path:
    return impostazioni.dati() / "capitoli" / f"{capitolo_id:02d}"


def versioni(capitolo_id: int) -> list[int]:
    cartella = _cartella_capitolo(capitolo_id)
    if not cartella.exists():
        return []
    return sorted(int(p.stem[1:]) for p in cartella.glob("v*.json"))


def bozza(capitolo_id: int, versione: int | None = None) -> dict | None:
    numeri = versioni(capitolo_id)
    if not numeri:
        return None
    numero = versione if versione is not None else numeri[-1]
    percorso = _cartella_capitolo(capitolo_id) / f"v{numero:04d}.json"
    if not percorso.exists():
        return None
    return json.loads(percorso.read_text(encoding="utf-8"))


def salva_versione(capitolo_id: int, paragrafi: list[dict], **dettagli) -> dict:
    """Crea sempre una versione nuova: le precedenti restano leggibili."""
    with BLOCCO:
        numero = max(versioni(capitolo_id), default=0) + 1
        valore = {
            "versione": numero,
            "creata": adesso(),
            "paragrafi": paragrafi,
            **dettagli,
        }
        _scrivi_atomico(_cartella_capitolo(capitolo_id) / f"v{numero:04d}.json", valore)
        return valore


# Design --------------------------------------------------------------------

def _cartella_design() -> Path:
    return impostazioni.dati() / "design"


def versioni_design() -> list[dict]:
    cartella = _cartella_design()
    if not cartella.exists():
        return []
    risultato = []
    for percorso in sorted(cartella.glob("v*.json")):
        dati = json.loads(percorso.read_text(encoding="utf-8"))
        risultato.append({k: dati[k] for k in ("versione", "creata", "etichetta")})
    return risultato


def design_versione(numero: int | None = None) -> dict | None:
    """La versione chiesta, oppure l'ultima. None se il design non e' mai cambiato."""
    versioni = versioni_design()
    if not versioni:
        return None
    scelta = numero if numero is not None else versioni[-1]["versione"]
    percorso = _cartella_design() / f"v{scelta:04d}.json"
    if not percorso.exists():
        return None
    return json.loads(percorso.read_text(encoding="utf-8"))


def salva_design(design: dict, etichetta: str) -> dict:
    """Ogni cambio e' una versione nuova, quindi si puo' sempre tornare indietro."""
    with BLOCCO:
        numero = max((v["versione"] for v in versioni_design()), default=0) + 1
        valore = {
            "versione": numero,
            "creata": adesso(),
            "etichetta": etichetta.strip()[:80],
            "design": design,
        }
        _scrivi_atomico(_cartella_design() / f"v{numero:04d}.json", valore)
        return valore


def proposte_design() -> list[dict]:
    return _leggi("design/proposte.json", [])


def aggiungi_proposte(nuove: list[dict]) -> None:
    with BLOCCO:
        _scrivi_atomico(_cartella_design() / "proposte.json", nuove + proposte_design())


def cambia_dati_libro(titolo: str | None, autore: str | None) -> None:
    with BLOCCO:
        stato = mappa()
        if titolo is not None:
            stato["titolo"] = titolo.strip()
        if autore is not None:
            stato["autore"] = autore.strip()
        salva_mappa(stato)


# Chat ----------------------------------------------------------------------

def messaggi_chat() -> list[dict]:
    return _leggi("chat.json", [])


def aggiungi_messaggio(autore: str, testo: str, **campi) -> dict:
    with BLOCCO:
        tutti = messaggi_chat()
        numero = max((int(m["id"][1:]) for m in tutti), default=0) + 1
        messaggio = {"id": f"m{numero:05d}", "autore": autore, "testo": testo, "creato": adesso(), **campi}
        tutti.append(messaggio)
        _scrivi("chat.json", tutti)
        return messaggio


def aggiorna_messaggio(messaggio_id: str, **campi) -> dict:
    with BLOCCO:
        tutti = messaggi_chat()
        for messaggio in tutti:
            if messaggio["id"] == messaggio_id:
                messaggio.update(campi)
                _scrivi("chat.json", tutti)
                return messaggio
    raise KeyError(messaggio_id)


def togli_errori_chat() -> None:
    with BLOCCO:
        _scrivi("chat.json", [m for m in messaggi_chat() if not m.get("errore")])

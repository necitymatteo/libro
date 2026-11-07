"""Porta nell'app un testo iniziale e una mappa in markdown. Non stampa i contenuti.

Uso: python -m libro.importa <cartella> [--nota "..."]
La cartella contiene fonte-originale.md e mappa.md. Si puo' rilanciare: non duplica.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

from . import archivio, deposito, impostazioni

_STATI = ("vuoto", "parziale", "pieno")


def _pulisci(testo: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", testo).strip()


def _sezioni(testo: str) -> tuple[str, dict[str, list[str]]]:
    preambolo: list[str] = []
    sezioni: dict[str, list[str]] = {}
    corrente = preambolo
    for riga in testo.splitlines():
        if riga.startswith("## "):
            corrente = sezioni.setdefault(riga[3:].strip().lower(), [])
        else:
            corrente.append(riga)
    return "\n".join(preambolo), sezioni


def _trova(sezioni: dict[str, list[str]], parola: str) -> list[str]:
    for titolo, righe in sezioni.items():
        if parola in titolo:
            return righe
    return []


def _voci_elenco(righe: list[str]) -> list[str]:
    risultato = []
    for riga in righe:
        trovata = re.match(r"^\s*(?:\d+\.|-)\s+(.*)$", riga)
        if trovata:
            risultato.append(_pulisci(trovata.group(1)))
    return risultato


def analizza_mappa(testo: str) -> dict:
    preambolo, sezioni = _sezioni(testo)
    titolo = "Il mio libro"
    filo = ""
    for riga in preambolo.splitlines():
        if riga.startswith("# "):
            titolo = riga[2:].split(":")[0].strip()
        elif "filo" in riga.lower() and not filo:
            filo = _pulisci(riga)

    capitoli = []
    for riga in _trova(sezioni, "capitoli"):
        celle = [c.strip() for c in riga.split("|")[1:-1]]
        if len(celle) == 5 and celle[0].isdigit():
            stato = celle[4].lower()
            capitoli.append({
                "id": int(celle[0]),
                "titolo": _pulisci(celle[1]),
                "tema": _pulisci(celle[2]),
                "materiale": _pulisci(celle[3]),
                "stato": stato if stato in _STATI else "parziale",
            })

    buchi = _voci_elenco(_trova(sezioni, "buchi"))
    contraddizioni = _voci_elenco(_trova(sezioni, "chiarire"))
    return {
        "titolo": titolo,
        "filo": filo,
        "capitoli": capitoli,
        "buchi": [
            {"id": f"b{i}", "testo": t, "chiuso": False, "capitolo": None}
            for i, t in enumerate(buchi, 1)
        ],
        "contraddizioni": [
            {"id": f"c{i}", "testo": t, "risolta": False}
            for i, t in enumerate(contraddizioni, 1)
        ],
        "domande_suggerite": _voci_elenco(_trova(sezioni, "domande")),
        "decisioni": _voci_elenco(_trova(sezioni, "decisioni")),
        "regole": _voci_elenco(_trova(sezioni, "regole")),
    }


def importa_cartella(cartella: Path, nota: str = "") -> dict:
    fonte = cartella / "fonte-originale.md"
    with open(fonte, encoding="utf-8", newline="") as file:
        testo = file.read()
    impronta = hashlib.sha256(testo.encode("utf-8")).hexdigest()

    gia_presente = any(v.meta.get("sha256") == impronta for v in archivio.leggi_tutte())
    if not gia_presente:
        meta = {"origine": fonte.name, "sha256": impronta}
        if nota:
            meta["nota"] = nota
        voce = archivio.salva("fonte", testo, **meta)
        riletta = archivio.leggi(voce.id)
        if riletta is None or riletta.testo != testo:
            raise RuntimeError("Il testo importato non è identico all'originale.")

    percorso_mappa = impostazioni.dati() / "mappa.json"
    mappa_creata = False
    if not percorso_mappa.exists():
        with deposito.BLOCCO:
            deposito.salva_mappa(analizza_mappa((cartella / "mappa.md").read_text(encoding="utf-8")))
        mappa_creata = True

    mappa = deposito.mappa()
    return {
        "byte_fonte": len(testo.encode("utf-8")),
        "fonte_gia_presente": gia_presente,
        "mappa_creata": mappa_creata,
        "capitoli": len(mappa["capitoli"]),
        "buchi": len(mappa["buchi"]),
        "contraddizioni": len(mappa["contraddizioni"]),
        "domande_suggerite": len(mappa["domande_suggerite"]),
        "decisioni": len(mappa["decisioni"]),
        "regole": len(mappa["regole"]),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cartella", type=Path)
    parser.add_argument("--nota", default="")
    argomenti = parser.parse_args()
    print(importa_cartella(argomenti.cartella, argomenti.nota))

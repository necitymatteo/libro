"""L'archivio originale: le parole dell'autore, esattamente come arrivano.

Regola: una voce si crea e non si cambia piu'. Questo modulo non ha funzioni per
modificare o cancellare. Il file nasce in sola lettura e la creazione fallisce se
il file esiste gia'. Ricordi, mappa e bozze sono derivati e si possono rifare.
"""
from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import impostazioni

TIPI = ("fonte", "annotazione", "risposta", "correzione", "chat")
_APERTURA = "<!-- "
_CHIUSURA = " -->"


@dataclass(frozen=True)
class Voce:
    id: str
    tipo: str
    creato: str
    testo: str
    meta: dict = field(default_factory=dict)


def _cartella() -> Path:
    cartella = impostazioni.dati() / "archivio"
    cartella.mkdir(exist_ok=True)
    os.chmod(cartella, 0o700)
    return cartella


def salva(tipo: str, testo: str, **meta) -> Voce:
    if tipo not in TIPI:
        raise ValueError(f"Tipo sconosciuto: {tipo}")
    if not testo.strip():
        raise ValueError("Il testo e' vuoto.")
    adesso = datetime.now().astimezone()
    voce_id = f"{adesso:%Y%m%d-%H%M%S-%f}-{secrets.token_hex(2)}"
    creato = adesso.isoformat(timespec="seconds")
    intestazione = json.dumps(
        {"id": voce_id, "tipo": tipo, "creato": creato, **meta},
        ensure_ascii=False,
    )
    percorso = _cartella() / f"{voce_id}-{tipo}.md"
    descrittore = os.open(percorso, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(descrittore, "w", encoding="utf-8", newline="") as file:
        file.write(f"{_APERTURA}{intestazione}{_CHIUSURA}\n\n{testo}")
        file.flush()
        os.fsync(file.fileno())
    return Voce(voce_id, tipo, creato, testo, dict(meta))


def _leggi_file(percorso: Path) -> Voce:
    with open(percorso, encoding="utf-8", newline="") as file:
        contenuto = file.read()
    riga, _, testo = contenuto.partition("\n\n")
    dati = json.loads(riga[len(_APERTURA):-len(_CHIUSURA)])
    voce_id = dati.pop("id")
    tipo = dati.pop("tipo")
    creato = dati.pop("creato")
    return Voce(voce_id, tipo, creato, testo, dati)


def leggi_tutte() -> list[Voce]:
    """Tutte le voci, dalla piu' vecchia alla piu' recente."""
    return [_leggi_file(p) for p in sorted(_cartella().glob("*.md"))]


def leggi(voce_id: str) -> Voce | None:
    for percorso in _cartella().glob(f"{voce_id}-*.md"):
        return _leggi_file(percorso)
    return None

"""Scrive le bozze dei sottocapitoli. Stampa solo conteggi, mai i testi.

Uso: python -m libro.scrivi            i sottocapitoli senza bozza
     python -m libro.scrivi --tutte    anche quelli che ne hanno gia' una: la versione di prima resta

Con l'app accesa non parte: due processi non devono scrivere negli stessi file.
"""
from __future__ import annotations

import argparse
import socket
import time

from . import agenti, deposito, impostazioni, motore


def _app_accesa() -> bool:
    with socket.socket() as prova:
        prova.settimeout(1)
        return prova.connect_ex(("127.0.0.1", impostazioni.porta())) == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tutte", action="store_true")
    argomenti = parser.parse_args()

    if _app_accesa():
        print("L'app e' accesa. Chiudila e rilancia.", flush=True)
        return 1

    numerati = deposito.capitoli_numerati()
    if argomenti.tutte:
        capitoli = [c["id"] for c in numerati if deposito.versioni(c["id"])]
    else:
        capitoli = agenti.capitoli_senza_bozza()
    numeri = {c["id"]: c["numero"] for c in numerati}
    print(f"Sottocapitoli da scrivere: {len(capitoli)}.", flush=True)

    errori = 0
    for capitolo_id in capitoli:
        inizio = time.time()
        try:
            versione = agenti.scrivi_bozza(capitolo_id)
        except motore.ErroreMotore as errore:
            errori += 1
            print(f"{numeri[capitolo_id]}: errore. {errore}", flush=True)
            continue
        frasi = [f for p in versione["paragrafi"] if p["autore"] == "scrittore" for f in p["frasi"]]
        tuoi = sum(1 for p in versione["paragrafi"] if p["autore"] == "tu")
        segnalate = sum(1 for f in frasi if f["segnalazioni"])
        print(
            f"{numeri[capitolo_id]}: versione {versione['versione']}, {len(versione['paragrafi'])} paragrafi "
            f"({tuoi} tuoi), {len(frasi)} frasi, {segnalate} da verificare, "
            f"controllo {versione['controllo']}, {round(time.time() - inizio)}s",
            flush=True,
        )
    print(f"Fatto. Errori: {errori}.", flush=True)
    return 1 if errori else 0


if __name__ == "__main__":
    raise SystemExit(main())

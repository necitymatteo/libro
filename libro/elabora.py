"""Elabora le voci in sospeso senza server. Stampa solo conteggi, mai i testi."""
from __future__ import annotations

from . import agenti, archivio, deposito, motore


def main() -> int:
    errori = 0
    fatte = deposito.elaborazioni()
    for voce in archivio.leggi_tutte():
        if fatte.get(voce.id, {}).get("stato") == "fatto":
            continue
        try:
            esito = agenti.elabora_voce(voce)
            print(f"{voce.tipo}: {esito['ricordi']} ricordi, {esito['scartati']} citazioni scartate")
        except motore.ErroreMotore as errore:
            errori += 1
            deposito.segna_elaborazione(voce.id, "errore", messaggio=str(errore))
            print(f"{voce.tipo}: errore. {errore}")
    tutti = deposito.ricordi()
    privati = sum(1 for r in tutti if r["privacy"] != "libro")
    senza_capitolo = sum(1 for r in tutti if r["capitolo"] is None)
    print(f"Totale: {len(tutti)} ricordi, {privati} solo appunti, {senza_capitolo} senza capitolo")
    return 1 if errori else 0


if __name__ == "__main__":
    raise SystemExit(main())

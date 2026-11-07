"""Prepara la persona inventata per guardare l'app senza testi veri. Nessuna chiamata a Claude.

Uso: LIBRO_DATI=<cartella di prova> python scripts/dati_prova.py
Non usare mai la cartella dei dati veri.
"""
from pathlib import Path

from libro import archivio, deposito, importa

CARTELLA = Path(__file__).resolve().parent.parent / "tests" / "dati_finti"
CONTEGGI = {1: 3, 2: 9, 3: 7, 4: 2}


def main() -> None:
    importa.importa_cartella(CARTELLA, nota="Persona inventata.")
    deposito.applica_struttura([
        {"titolo": "Il mare", "tema": "Da bambino", "capitoli": [{"id": 1, "titolo": "Il molo"}, {"id": 2, "titolo": "Il banco di Dario"}]},
        {"titolo": "Andare via", "tema": "Da grande", "capitoli": [{"id": 3, "titolo": "Mio padre"}, {"id": 4, "titolo": "Il quaderno nel canale"}]},
    ], filo="Guarda la linea dell'acqua, non il pesce.")
    voce = archivio.leggi_tutte()[0]
    deposito.segna_elaborazione(voce.id, "fatto", ricordi=0, scartati=0)
    nuovi = []
    for capitolo, quanti in CONTEGGI.items():
        for i in range(quanti):
            nuovi.append({
                "testo": f"Ricordo {i + 1} del capitolo {capitolo}.",
                "citazione": "Sono nato a Trieste nel 1982",
                "capitolo": capitolo,
                "persone": ["Dario", "Elena", "mio nonno Bruno"] if i == 0 else [],
                "periodo": "",
                "tipo": "fatto",
                "privacy": "solo_appunti" if i == quanti - 1 else "libro",
            })
    deposito.applica_archivista(voce.id, nuovi, [], 0)
    deposito.aggiungi_domanda(
        "Il giorno in cui tuo padre doveva ripartire e non è partito: dov'eri tu quando hai capito che restava?",
        "scena",
        "è tornato e non è più ripartito",
        3,
        "È il punto che dici di non saper scrivere: partiamo da una scena concreta.",
    )


if __name__ == "__main__":
    main()

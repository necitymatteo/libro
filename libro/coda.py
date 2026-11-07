"""Lavori in background: l'archivista legge una voce alla volta, le bozze hanno un thread.

Lo stato vero sta su disco. Ogni voce non ancora elaborata torna in coda quando
l'app riparte, quindi uno spegnimento non perde niente.
"""
from __future__ import annotations

import logging
import queue
import secrets
import threading

from . import agenti, archivio, deposito, motore

_registro = logging.getLogger("libro")
_MESSAGGIO_GENERICO = "Errore imprevisto durante l'elaborazione. I tuoi testi sono salvati."
_ATTIVI = ("in_attesa", "in_corso")


class Coda:
    def __init__(self) -> None:
        self._coda: queue.Queue[str] = queue.Queue()
        self._in_coda: set[str] = set()
        self._in_corso: str | None = None
        self._blocco = threading.Lock()
        self._thread: threading.Thread | None = None
        self._lavori: dict[str, dict] = {}
        self._chat_in_corso = False

    def avvia(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._gira, daemon=True, name="archivista")
            self._thread.start()
        self.recupera()

    def recupera(self) -> None:
        """Rimette in coda tutto quello che non e' stato elaborato."""
        fatte = deposito.elaborazioni()
        for voce in archivio.leggi_tutte():
            if fatte.get(voce.id, {}).get("stato") != "fatto":
                self.aggiungi(voce.id)

    def aggiungi(self, voce_id: str) -> None:
        with self._blocco:
            if voce_id in self._in_coda or voce_id == self._in_corso:
                return
            self._in_coda.add(voce_id)
        self._coda.put(voce_id)

    def _gira(self) -> None:
        while True:
            voce_id = self._coda.get()
            with self._blocco:
                self._in_coda.discard(voce_id)
                self._in_corso = voce_id
            self._elabora(voce_id)
            with self._blocco:
                self._in_corso = None
            self._coda.task_done()

    def _elabora(self, voce_id: str) -> None:
        voce = archivio.leggi(voce_id)
        if voce is None:
            return
        try:
            agenti.elabora_voce(voce)
        except motore.ErroreMotore as errore:
            deposito.segna_elaborazione(voce_id, "errore", messaggio=str(errore))
        except Exception as errore:  # il registro non contiene mai i testi
            _registro.error("Archivista: errore di tipo %s", type(errore).__name__)
            deposito.segna_elaborazione(voce_id, "errore", messaggio=_MESSAGGIO_GENERICO)

    def attendi(self) -> None:
        """Solo per i test e per l'elaborazione da riga di comando."""
        self._coda.join()

    def stato(self) -> dict:
        with self._blocco:
            in_attesa = len(self._in_coda)
            in_corso = self._in_corso
        errori = [
            {"voce": voce_id, "messaggio": dati.get("messaggio", "")}
            for voce_id, dati in deposito.elaborazioni().items()
            if dati["stato"] == "errore"
            and voce_id != in_corso
            and voce_id not in self._in_coda
        ]
        return {
            "in_attesa": in_attesa,
            "in_corso": in_corso is not None,
            "errori": errori,
            "lavori": [dict(l) for l in self._lavori.values() if l["stato"] in _ATTIVI],
        }

    def lavoro_capitolo(self, capitolo_id: int) -> dict | None:
        ultimo = None
        for lavoro in self._lavori.values():
            if lavoro["capitolo"] == capitolo_id:
                ultimo = lavoro
        return dict(ultimo) if ultimo else None

    def _nuovo_lavoro(self, capitolo_id: int, stato: str) -> dict:
        lavoro = {
            "id": secrets.token_hex(4),
            "capitolo": capitolo_id,
            "stato": stato,
            "messaggio": "",
        }
        self._lavori[lavoro["id"]] = lavoro
        return lavoro

    def _capitoli_attivi(self) -> dict[int, dict]:
        return {l["capitolo"]: l for l in self._lavori.values() if l["stato"] in _ATTIVI}

    def _esegui(self, lavoro: dict) -> None:
        lavoro["stato"] = "in_corso"
        try:
            agenti.scrivi_bozza(lavoro["capitolo"])
            lavoro["stato"] = "fatto"
        except motore.ErroreMotore as errore:
            lavoro["stato"] = "errore"
            lavoro["messaggio"] = str(errore)
        except Exception as errore:
            _registro.error("Scrittore: errore di tipo %s", type(errore).__name__)
            lavoro["stato"] = "errore"
            lavoro["messaggio"] = "Errore imprevisto durante la scrittura. Riprova."

    def chat_in_corso(self) -> bool:
        return self._chat_in_corso

    def avvia_chat(self) -> bool:
        """La risposta nasce qui e resta salvata anche se l'autore cambia pagina."""
        with self._blocco:
            if self._chat_in_corso:
                return False
            self._chat_in_corso = True

        def esegui() -> None:
            try:
                agenti.rispondi_chat()
            except motore.ErroreMotore as errore:
                deposito.aggiungi_messaggio("agente", str(errore), errore=True)
            except Exception as errore:
                _registro.error("Chat: errore di tipo %s", type(errore).__name__)
                deposito.aggiungi_messaggio("agente", "Errore imprevisto. Il tuo messaggio è salvato: riprova.", errore=True)
            finally:
                self._chat_in_corso = False

        threading.Thread(target=esegui, daemon=True, name="chat").start()
        return True

    def avvia_bozza(self, capitolo_id: int) -> dict:
        with self._blocco:
            attivo = self._capitoli_attivi().get(capitolo_id)
            if attivo:
                return dict(attivo)
            lavoro = self._nuovo_lavoro(capitolo_id, "in_corso")
        threading.Thread(target=self._esegui, args=(lavoro,), daemon=True, name=f"scrittore-{capitolo_id}").start()
        return dict(lavoro)

    def avvia_bozze_mancanti(self) -> list[dict]:
        """Scrive i capitoli senza bozza uno alla volta, per non consumare l'abbonamento in un colpo."""
        da_scrivere = agenti.capitoli_senza_bozza()
        with self._blocco:
            attivi = self._capitoli_attivi()
            nuovi = [self._nuovo_lavoro(c, "in_attesa") for c in da_scrivere if c not in attivi]

        def in_fila() -> None:
            for lavoro in nuovi:
                self._esegui(lavoro)

        if nuovi:
            threading.Thread(target=in_fila, daemon=True, name="scrittore-mancanti").start()
        return [dict(l) for l in nuovi]


coda = Coda()

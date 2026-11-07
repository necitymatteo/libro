"""Percorsi e modelli. Ogni valore si puo' cambiare con una variabile d'ambiente."""
import os
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def dati() -> Path:
    """Cartella dei testi privati: solo il proprietario puo' aprirla."""
    percorso = Path(os.environ.get("LIBRO_DATI", RADICE / "dati"))
    percorso.mkdir(parents=True, exist_ok=True)
    os.chmod(percorso, 0o700)
    return percorso


def porta() -> int:
    return int(os.environ.get("LIBRO_PORTA", "8765"))


def modello(agente: str) -> str:
    """L'archivista e il controllo leggono, gli altri due scrivono per l'autore."""
    predefiniti = {
        "archivista": "sonnet",
        "controllo": "sonnet",
        "designer": "sonnet",
        "intervistatore": "opus",
        "scrittore": "opus",
    }
    return os.environ.get(f"LIBRO_MODELLO_{agente.upper()}", predefiniti[agente])

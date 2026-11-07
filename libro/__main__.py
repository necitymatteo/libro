"""Avvia l'app del libro. Ascolta solo su 127.0.0.1 e non registra le richieste."""
import uvicorn

from . import impostazioni
from .server import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=impostazioni.porta(), access_log=False, log_level="warning")

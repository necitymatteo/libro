"""Chiamate al comando `claude -p` con l'abbonamento dell'utente, non con una API key.

Ogni chiamata e' isolata: niente strumenti, niente MCP, niente impostazioni o
CLAUDE.md, nessuna sessione salvata su disco, cartella neutra. I testi passano da
stdin, quindi non compaiono nell'elenco dei processi.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

_CARTELLA_NEUTRA = tempfile.gettempdir()
_ATTESA_SECONDI = 420


class ErroreMotore(RuntimeError):
    """Il messaggio e' pensato per essere mostrato all'autore."""


class NonCollegato(ErroreMotore):
    pass


def _ambiente_pulito() -> dict:
    """Toglie le variabili che cambierebbero il login o userebbero una API key."""
    rimosse = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDECODE")
    return {
        chiave: valore
        for chiave, valore in os.environ.items()
        if chiave not in rimosse and not chiave.startswith(("CLAUDE_CODE_", "CLAUDE_AGENT_SDK"))
    }


def _traduci_errore(dettaglio: str) -> ErroreMotore:
    testo = dettaglio.lower()
    if any(p in testo for p in ("not logged in", "/login", "oauth", "authentication", "auth login")):
        return NonCollegato(
            "Claude non è collegato. Apri il Terminale ed esegui: claude auth login. "
            "I tuoi testi sono già salvati."
        )
    if any(p in testo for p in ("usage limit", "limit reached", "hit your limit", "rate limit")):
        return ErroreMotore(
            "Hai raggiunto il limite dell'abbonamento Claude. I tuoi testi sono già salvati. "
            "Riprova quando il limite si azzera."
        )
    if "safeguards flagged" in testo:
        return ErroreMotore(
            "Il filtro di sicurezza di Claude ha rifiutato questa richiesta. "
            "I tuoi testi sono già salvati."
        )
    return ErroreMotore(f"Claude ha dato un errore: {dettaglio[:200]}")


def chiedi_json(sistema: str, prompt: str, schema: dict, modello: str) -> dict:
    eseguibile = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    comando = [
        eseguibile, "-p",
        "--model", modello,
        "--tools", "",
        "--strict-mcp-config",
        "--setting-sources", "",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--output-format", "json",
        "--json-schema", json.dumps(schema),
        "--system-prompt", sistema,
    ]
    try:
        esito = subprocess.run(
            comando,
            input=prompt,
            capture_output=True,
            text=True,
            env=_ambiente_pulito(),
            cwd=_CARTELLA_NEUTRA,
            timeout=_ATTESA_SECONDI,
        )
    except FileNotFoundError as errore:
        raise ErroreMotore("Non trovo il comando claude su questo Mac.") from errore
    except subprocess.TimeoutExpired as errore:
        raise ErroreMotore(
            f"Claude non ha risposto in {_ATTESA_SECONDI // 60} minuti. I tuoi testi sono già salvati."
        ) from errore

    try:
        risposta = json.loads(esito.stdout)
    except json.JSONDecodeError:
        raise _traduci_errore((esito.stderr or esito.stdout).strip()) from None

    if esito.returncode != 0 or risposta.get("is_error"):
        dettaglio = str(risposta.get("result") or esito.stderr or risposta.get("subtype"))
        raise _traduci_errore(dettaglio.strip())

    strutturata = risposta.get("structured_output")
    if not isinstance(strutturata, dict):
        raise ErroreMotore("Claude ha risposto in un formato inatteso. Riprova.")
    return strutturata

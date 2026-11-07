"""Il design del libro: formati, font, misure e colori consentiti, e 5 design di partenza.

Un design e' un elenco di valori, mai codice. Tutto quello che arriva dal modello o
dalla pagina passa da `normalizza`: font non installati, misure assurde e colori
illeggibili non entrano. Cosi' il modello puo' proporre senza poter rompere la pagina.
"""
from __future__ import annotations

import re

FORMATI = {
    "tascabile": {"nome": "Tascabile, 12 x 19 cm", "larghezza": 120, "altezza": 190},
    "romanzo": {"nome": "Romanzo, 14 x 21 cm", "larghezza": 140, "altezza": 210},
    "grande": {"nome": "Grande, 17 x 24 cm", "larghezza": 170, "altezza": 240},
    "quadrato": {"nome": "Quadrato, 19 x 19 cm", "larghezza": 190, "altezza": 190},
}

# Solo font di sistema di macOS.
FONT_TESTO = {
    "Palatino": "serif",
    "Baskerville": "serif",
    "Charter": "serif",
    "Georgia": "serif",
    "Hoefler Text": "serif",
    "Cochin": "serif",
    "PT Serif": "serif",
    "STIX Two Text": "serif",
    "Times New Roman": "serif",
    "Avenir Next": "sans-serif",
    "Gill Sans": "sans-serif",
    "Optima": "sans-serif",
    "PT Sans": "sans-serif",
    "American Typewriter": "serif",
    "Courier New": "monospace",
}
FONT_TITOLI = {
    **FONT_TESTO,
    "Big Caslon": "serif",
    "Didot": "serif",
    "Bodoni 72": "serif",
    "Bodoni 72 Smallcaps": "serif",
    "Copperplate": "serif",
    "Trattatello": "serif",
    "Futura": "sans-serif",
    "Helvetica Neue": "sans-serif",
    "Avenir Next Condensed": "sans-serif",
    "DIN Condensed": "sans-serif",
    "Snell Roundhand": "cursive",
    "Bradley Hand": "cursive",
    "SignPainter": "cursive",
}

_NUMERI = {
    "corpo_pt": (9.0, 14.0),
    "interlinea": (1.15, 1.8),
    "margine_interno_mm": (12, 40),
    "margine_esterno_mm": (10, 40),
    "margine_sopra_mm": (12, 40),
    "margine_sotto_mm": (14, 45),
    "discesa_capitolo_mm": (0, 110),
    "titolo_capitolo_pt": (14, 48),
}
_SCELTE = {
    "formato": tuple(FORMATI),
    "font_testo": tuple(FONT_TESTO),
    "font_titoli": tuple(FONT_TITOLI),
    "copertina_font": tuple(FONT_TITOLI),
    "allineamento": ("giustificato", "sinistra"),
    "paragrafi": ("rientro", "spazio"),
    "apertura_capitolo": ("destra", "continua"),
    "numero_capitolo": ("cifra", "lettere", "capitolo", "nessuno"),
    "titolo_capitolo_allineamento": ("sinistra", "centro"),
    "ornamento": ("nessuno", "filetto"),
    "testatine": ("libro_capitolo", "capitolo", "nessuna"),
    "numeri_pagina": ("esterno", "centro"),
    "copertina_composizione": ("classica", "grande", "basso", "fascia"),
}
_BOOLEANI = ("sillabazione", "capolettera")
_COLORI = (
    "colore_carta", "colore_inchiostro", "colore_accento",
    "copertina_sfondo", "copertina_testo", "copertina_accento",
)
_COLORE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_TESTO_MINIMO = 7.0
_COPERTINA_MINIMO = 3.0
_LARGHEZZA_TESTO_MINIMA = 0.55

_BASE = {
    "nome": "Essenziale",
    "motivo": "Un romanzo senza orpelli: testo chiaro, titolo sobrio, copertina bianca. Parlano le parole.",
    "formato": "romanzo",
    "font_testo": "Palatino",
    "font_titoli": "Palatino",
    "corpo_pt": 11.0,
    "interlinea": 1.45,
    "allineamento": "giustificato",
    "sillabazione": True,
    "paragrafi": "rientro",
    "margine_interno_mm": 22,
    "margine_esterno_mm": 18,
    "margine_sopra_mm": 22,
    "margine_sotto_mm": 26,
    "apertura_capitolo": "destra",
    "discesa_capitolo_mm": 48,
    "numero_capitolo": "cifra",
    "titolo_capitolo_allineamento": "sinistra",
    "titolo_capitolo_pt": 24,
    "capolettera": False,
    "ornamento": "nessuno",
    "testatine": "libro_capitolo",
    "numeri_pagina": "esterno",
    "colore_carta": "#FDFDFB",
    "colore_inchiostro": "#1F1F1F",
    "colore_accento": "#6A6A6F",
    "copertina_composizione": "classica",
    "copertina_sfondo": "#F4F4F2",
    "copertina_testo": "#1D1D1F",
    "copertina_accento": "#1D1D1F",
    "copertina_font": "Palatino",
}

PREDEFINITI = [
    dict(_BASE),
    {
        **_BASE,
        "nome": "Classico",
        "motivo": "Il libro della vita come un romanzo di una volta: capolettera, titoli al centro, tela verde.",
        "font_testo": "Baskerville",
        "font_titoli": "Baskerville",
        "corpo_pt": 11.5,
        "numero_capitolo": "lettere",
        "titolo_capitolo_allineamento": "centro",
        "titolo_capitolo_pt": 22,
        "capolettera": True,
        "ornamento": "filetto",
        "discesa_capitolo_mm": 56,
        "colore_carta": "#FAF7F0",
        "colore_inchiostro": "#231F1A",
        "colore_accento": "#6B4E1E",
        "copertina_composizione": "classica",
        "copertina_sfondo": "#1F3B33",
        "copertina_testo": "#F3EEDF",
        "copertina_accento": "#C9A45C",
        "copertina_font": "Baskerville",
    },
    {
        **_BASE,
        "nome": "Contemporaneo",
        "motivo": "Titoli grandi e testo a bandiera: secco come una storia raccontata oggi.",
        "font_testo": "Charter",
        "font_titoli": "Avenir Next",
        "corpo_pt": 10.5,
        "interlinea": 1.5,
        "allineamento": "sinistra",
        "sillabazione": False,
        "discesa_capitolo_mm": 70,
        "titolo_capitolo_pt": 36,
        "testatine": "nessuna",
        "numeri_pagina": "centro",
        "colore_carta": "#FFFFFF",
        "colore_inchiostro": "#141414",
        "colore_accento": "#E4572E",
        "copertina_composizione": "grande",
        "copertina_sfondo": "#E4572E",
        "copertina_testo": "#141414",
        "copertina_accento": "#FFFFFF",
        "copertina_font": "Avenir Next",
    },
    {
        **_BASE,
        "nome": "Diario",
        "motivo": "Formato piccolo e macchina da scrivere: un taccuino tenuto in tasca per anni.",
        "formato": "tascabile",
        "font_testo": "American Typewriter",
        "font_titoli": "American Typewriter",
        "corpo_pt": 9.5,
        "interlinea": 1.5,
        "allineamento": "sinistra",
        "sillabazione": False,
        "paragrafi": "spazio",
        "margine_interno_mm": 18,
        "margine_esterno_mm": 14,
        "margine_sopra_mm": 18,
        "margine_sotto_mm": 22,
        "apertura_capitolo": "continua",
        "discesa_capitolo_mm": 24,
        "titolo_capitolo_pt": 16,
        "testatine": "capitolo",
        "colore_carta": "#F6F1E6",
        "colore_inchiostro": "#26231E",
        "colore_accento": "#26231E",
        "copertina_composizione": "basso",
        "copertina_sfondo": "#C9B79C",
        "copertina_testo": "#26231E",
        "copertina_accento": "#26231E",
        "copertina_font": "American Typewriter",
    },
    {
        **_BASE,
        "nome": "Editoriale",
        "motivo": "Grande formato e contrasti forti: il libro come oggetto da tenere sul tavolo.",
        "formato": "grande",
        "font_testo": "Hoefler Text",
        "font_titoli": "Didot",
        "corpo_pt": 11.5,
        "interlinea": 1.5,
        "margine_interno_mm": 28,
        "margine_esterno_mm": 26,
        "margine_sopra_mm": 26,
        "margine_sotto_mm": 32,
        "discesa_capitolo_mm": 84,
        "numero_capitolo": "capitolo",
        "titolo_capitolo_pt": 42,
        "colore_carta": "#FBFBF8",
        "colore_inchiostro": "#111111",
        "colore_accento": "#8A1C1C",
        "copertina_composizione": "fascia",
        "copertina_sfondo": "#111111",
        "copertina_testo": "#111111",
        "copertina_accento": "#F4F1EA",
        "copertina_font": "Didot",
    },
]


def predefinito() -> dict:
    return dict(_BASE)


def _luminanza(colore: str) -> float:
    canali = [int(colore[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lineari = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canali]
    return 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]


def contrasto(primo: str, secondo: str) -> float:
    a, b = sorted((_luminanza(primo), _luminanza(secondo)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _leggibile(sfondo: str, colore: str) -> str:
    return max(("#111111", "#FFFFFF"), key=lambda c: contrasto(sfondo, c)) if colore else colore


def _numero(valore, minimo: float, massimo: float, base: float) -> float | None:
    if isinstance(valore, bool) or not isinstance(valore, (int, float)):
        return None
    return round(min(max(float(valore), minimo), massimo), 2) if valore == valore else base


def normalizza(proposta: dict, base: dict | None = None) -> tuple[dict, list[str]]:
    """Restituisce un design sempre valido e l'elenco di quello che ha dovuto correggere."""
    partenza = {**_BASE, **(base or {})}
    design: dict = {}
    avvisi: list[str] = []

    for chiave, valore_base in _BASE.items():
        valore = proposta.get(chiave, partenza[chiave])
        if chiave in _NUMERI:
            minimo, massimo = _NUMERI[chiave]
            pulito = _numero(valore, minimo, massimo, partenza[chiave])
            if pulito is None:
                avvisi.append(f"Ho ignorato il valore di {chiave}.")
                pulito = partenza[chiave]
            elif pulito != valore:
                avvisi.append(f"Ho riportato {chiave} tra {minimo:g} e {massimo:g}.")
            design[chiave] = pulito
        elif chiave in _SCELTE:
            if valore in _SCELTE[chiave]:
                design[chiave] = valore
            else:
                avvisi.append(f"{valore} non è disponibile per {chiave}.")
                design[chiave] = partenza[chiave]
        elif chiave in _BOOLEANI:
            design[chiave] = valore if isinstance(valore, bool) else partenza[chiave]
        elif chiave in _COLORI:
            if isinstance(valore, str) and _COLORE.match(valore):
                design[chiave] = valore.upper()
            else:
                avvisi.append(f"Ho ignorato il colore di {chiave}.")
                design[chiave] = partenza[chiave]
        else:
            testo = valore if isinstance(valore, str) else valore_base
            design[chiave] = testo.strip()[:200 if chiave == "motivo" else 60]

    if contrasto(design["colore_carta"], design["colore_inchiostro"]) < _TESTO_MINIMO:
        design["colore_inchiostro"] = _leggibile(design["colore_carta"], design["colore_inchiostro"])
        avvisi.append("Il testo non si leggeva bene sulla carta: ho scurito il colore del testo.")
    sfondo_titolo = (
        design["copertina_accento"]
        if design["copertina_composizione"] == "fascia"
        else design["copertina_sfondo"]
    )
    if contrasto(sfondo_titolo, design["copertina_testo"]) < _COPERTINA_MINIMO:
        design["copertina_testo"] = _leggibile(sfondo_titolo, design["copertina_testo"])
        avvisi.append("Il titolo non si leggeva bene in copertina: ho cambiato il suo colore.")

    larghezza = FORMATI[design["formato"]]["larghezza"]
    margini = design["margine_interno_mm"] + design["margine_esterno_mm"]
    limite = larghezza * (1 - _LARGHEZZA_TESTO_MINIMA)
    if margini > limite:
        fattore = limite / margini
        design["margine_interno_mm"] = round(design["margine_interno_mm"] * fattore, 2)
        design["margine_esterno_mm"] = round(design["margine_esterno_mm"] * fattore, 2)
        avvisi.append("I margini lasciavano poco testo: li ho ridotti.")
    return design, avvisi


def schema() -> dict:
    """Lo schema che il modello deve rispettare: niente font o valori fuori elenco."""
    proprieta: dict = {}
    for chiave in _BASE:
        if chiave in _NUMERI:
            minimo, massimo = _NUMERI[chiave]
            proprieta[chiave] = {"type": "number", "minimum": minimo, "maximum": massimo}
        elif chiave in _SCELTE:
            proprieta[chiave] = {"type": "string", "enum": list(_SCELTE[chiave])}
        elif chiave in _BOOLEANI:
            proprieta[chiave] = {"type": "boolean"}
        elif chiave in _COLORI:
            proprieta[chiave] = {"type": "string", "pattern": _COLORE.pattern}
        else:
            proprieta[chiave] = {"type": "string"}
    return {
        "type": "object",
        "properties": proprieta,
        "required": list(_BASE),
        "additionalProperties": False,
    }


def catalogo() -> dict:
    """Quello che serve alla pagina per disegnare il libro e i comandi."""
    return {
        "formati": FORMATI,
        "font_testo": FONT_TESTO,
        "font_titoli": FONT_TITOLI,
        "composizioni": list(_SCELTE["copertina_composizione"]),
    }

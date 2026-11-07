"""Controlli da codice. Non dipendono da quello che il modello dichiara di aver fatto."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

_NUMERI_IN_LETTERE = {
    "zero": 0, "uno": 1, "una": 1, "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6,
    "sette": 7, "otto": 8, "nove": 9, "dieci": 10, "undici": 11, "dodici": 12, "tredici": 13,
    "quattordici": 14, "quindici": 15, "sedici": 16, "diciassette": 17, "diciotto": 18,
    "diciannove": 19, "venti": 20, "ventuno": 21, "ventidue": 22, "ventitre": 23,
    "ventitré": 23, "ventiquattro": 24, "venticinque": 25, "trenta": 30, "quaranta": 40,
    "cinquanta": 50, "sessanta": 60, "settanta": 70, "ottanta": 80, "novanta": 90,
    "cento": 100, "mille": 1000,
}
_INIZI_DI_FRASE = '.!?:;«"“‘—–-('
_MODELLI_DISAGIO = re.compile(
    r"\b("
    r"voglio morire|vorrei morire|vorrei non esserci|voglio farla finita|"
    r"farla finita|togliermi la vita|uccidermi|ammazzarmi|suicidarmi|"
    r"non voglio pi[uù] vivere|non ce la faccio pi[uù] a vivere|farmi del male"
    r")\b",
    re.IGNORECASE,
)


def normalizza(testo: str) -> str:
    """Stessa citazione anche se cambiano spazi, a capo o tipo di apostrofo."""
    uniformato = (
        testo.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    )
    return re.sub(r"\s+", " ", uniformato).strip()


def citazione_valida(citazione: str, fonte: str) -> bool:
    """La citazione deve esistere davvero nel testo dell'autore."""
    pulita = normalizza(citazione)
    return len(pulita.split()) >= 2 and pulita in normalizza(fonte)


def segnali_disagio(testo: str) -> bool:
    return bool(_MODELLI_DISAGIO.search(testo))


def dividi_testo(testo: str, limite: int) -> list[str]:
    """Spezza i testi lunghi sulle righe vuote, per non perdere pezzi nell'elaborazione."""
    if len(testo) <= limite:
        return [testo]
    pezzi: list[str] = []
    corrente = ""
    for blocco in re.split(r"(\n\s*\n)", testo):
        if corrente and len(corrente) + len(blocco) > limite:
            pezzi.append(corrente)
            corrente = ""
        corrente += blocco
        while len(corrente) > limite:
            pezzi.append(corrente[:limite])
            corrente = corrente[limite:]
    if corrente.strip():
        pezzi.append(corrente)
    return pezzi


def problemi_domanda(domanda: str, precedenti: list[str]) -> list[str]:
    testo = domanda.strip()
    problemi = []
    if not testo:
        return ["La domanda è vuota."]
    if testo.count("?") != 1 or not testo.endswith("?"):
        problemi.append("Scrivi una sola domanda, con un solo punto interrogativo alla fine.")
    if len(testo.split()) > 35:
        problemi.append("La domanda supera 35 parole.")
    for precedente in precedenti:
        somiglianza = SequenceMatcher(None, testo.lower(), precedente.lower()).ratio()
        if somiglianza >= 0.85:
            problemi.append(f"Questa domanda è già stata fatta: {precedente}")
            break
    return problemi


def _numeri_nel_testo(testo: str) -> set[str]:
    numeri = set(re.findall(r"\d+", testo))
    for parola in re.findall(r"[^\W\d_]+", testo.lower()):
        if parola in _NUMERI_IN_LETTERE:
            numeri.add(str(_NUMERI_IN_LETTERE[parola]))
    return numeri


def _nomi_propri(frase: str) -> list[str]:
    """Parole maiuscole che non stanno all'inizio di una frase o di un discorso."""
    nomi = []
    for corrispondenza in re.finditer(r"[^\W\d_]+", frase):
        parola = corrispondenza.group()
        if len(parola) < 2 or not parola[0].isupper():
            continue
        prima = frase[: corrispondenza.start()].rstrip()
        if not prima or prima[-1] in _INIZI_DI_FRASE:
            continue
        nomi.append(parola)
    return nomi


def controlla_frase(testo: str, fonti: list[str], connettivo: bool) -> list[str]:
    """Trova numeri e nomi della frase che non compaiono nei ricordi citati."""
    problemi = []
    if not fonti and not connettivo:
        problemi.append("La frase non ha nessuna fonte.")
    insieme = " ".join(fonti)
    numeri_fonti = _numeri_nel_testo(insieme)
    for numero in sorted(set(re.findall(r"\d+", testo))):
        if numero not in numeri_fonti:
            problemi.append(f"Il numero {numero} non compare nelle fonti.")
    parole_fonti = {p.lower() for p in re.findall(r"[^\W\d_]+", insieme)}
    for nome in dict.fromkeys(_nomi_propri(testo)):
        if nome.lower() not in parole_fonti:
            problemi.append(f"Il nome {nome} non compare nelle fonti.")
    return problemi


def problemi_struttura(parti: list[dict], esistenti: dict[int, str], con_materiale: set[int]) -> list[str]:
    """Una struttura nuova non puo' perdere niente: ogni sottocapitolo con materiale resta."""
    problemi: list[str] = []
    if not parti:
        return ["Serve almeno un capitolo."]
    visti: set[int] = set()
    for parte in parti:
        titolo = str(parte.get("titolo") or "").strip()
        if not titolo:
            problemi.append("Un capitolo non ha il titolo.")
        elif len(titolo) > 80:
            problemi.append(f"Il titolo del capitolo {titolo[:30]} supera 80 caratteri.")
        voci = parte.get("capitoli") or []
        if not voci:
            problemi.append(f"Il capitolo {titolo or 'senza titolo'} non ha sottocapitoli.")
        for voce in voci:
            nome = str(voce.get("titolo") or "").strip()
            if not nome:
                problemi.append("Un sottocapitolo non ha il titolo.")
            elif len(nome) > 80:
                problemi.append(f"Il titolo del sottocapitolo {nome[:30]} supera 80 caratteri.")
            identificativo = voce.get("id")
            if identificativo is None:
                continue
            if identificativo not in esistenti:
                problemi.append(f"Il sottocapitolo {identificativo} non esiste.")
            elif identificativo in visti:
                problemi.append(f"Il sottocapitolo {esistenti[identificativo]} compare due volte.")
            visti.add(identificativo)
    for identificativo in con_materiale - visti:
        if identificativo in esistenti:
            problemi.append(f"Il sottocapitolo {esistenti[identificativo]} ha del materiale e non può sparire.")
    return problemi

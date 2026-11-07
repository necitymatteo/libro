# Libro

Un'app locale per scrivere un'autobiografia senza scriverla parola per parola.
Ogni giorno scrivi o detti annotazioni, oppure rispondi a una domanda alla volta.
Tre agenti tengono in ordine il materiale e scrivono le bozze.

## Provarla

Serve un Mac, con [Claude Code](https://claude.com/claude-code) installato e collegato a un
abbonamento, e Python 3.12. Copia ed esegui, un comando alla volta:

```bash
git clone https://github.com/necitymatteo/libro.git
```

```bash
cd libro && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Per partire da un libro di esempio, con una persona inventata:

```bash
.venv/bin/python -m libro.importa tests/dati_finti
```

Poi apri l'app:

```bash
./avvia.command
```

I tuoi testi restano in `dati/` sul tuo Mac, fuori da git, ma passano da Claude.

## Avvio

`avvia.command` apre `http://127.0.0.1:8765` in Safari, anche con un doppio clic.
L'app resta accesa finché quella finestra del Terminale è aperta: chiudendola si spegne.
`LIBRO_BROWSER` sceglie un altro browser. Per lanciarla con una parola sola, crea un
collegamento di nome `libro` in `~/.local/bin`.

## Come funziona

```
Scrivi, rispondi o correggi
        |
Archivio originale (dati/archivio: un file per voce, in sola lettura)
        |
Archivista: ricava ricordi e aggiorna la mappa del libro
        |
Ricordi e mappa
    |              |
Intervistatore    Scrittore + controllo
    |              |
La domanda      La bozza del capitolo
    |              |
    +--- tornano a te ---+
```

La chat è la stessa conoscenza in forma libera: legge testi, ricordi, bozze, struttura e filo,
risponde e può proporre un cambio di titolo, filo o struttura, che si applica solo con il bottone.
Quello che scrivi in chat entra nell'archivio e passa dall'archivista.

Nel codice un "capitolo" è il sottocapitolo dello schermo, una "parte" è il capitolo. Ricordi e bozze
restano legati al loro numero, quindi cambiare la struttura non li tocca. La mappa di prima resta
in `dati/storico-mappa/`.

Le chiamate a `claude -p` usano il tuo abbonamento: archivista, controllo e designer con
Sonnet, intervistatore, chat e scrittore con Opus. Si cambiano con le variabili
`LIBRO_MODELLO_ARCHIVISTA`, `_CONTROLLO`, `_INTERVISTATORE`, `_SCRITTORE`.

## Le regole, e dove stanno nel codice

Il modello propone, il codice decide. Queste regole non dipendono dal prompt.

| Regola | Dove |
|---|---|
| Un originale non cambia mai | `archivio.py`: file creato in sola lettura, nessuna funzione di modifica |
| Una citazione deve esistere nel testo, altrimenti il ricordo viene scartato | `controlli.citazione_valida` |
| Nel dubbio un ricordo resta "solo appunti" | `agenti._filtra_ricordi` |
| Lo scrittore riceve solo ricordi "libro", non superati, senza persone escluse | `deposito.ricordi_per_scrittore` |
| Un paragrafo corretto da te resta identico | `agenti._componi_paragrafi` |
| Numeri e nomi senza fonte vengono segnalati | `controlli.controlla_frase` |
| Un secondo lettore cerca i fatti senza fonte | `agenti._controlla_bozza` |
| Una domanda alla volta, mai ripetuta | `controlli.problemi_domanda` |
| Con segnali di disagio le domande si fermano, con un testo fisso | `controlli.segnali_disagio`, `agenti.MESSAGGIO_PAUSA` |
| Solo questo Mac, nessun altro sito | `server._protezione`, `__main__.py` |

## Anteprima

La pagina Anteprima mostra il libro come uscirebbe oggi, solo dalle bozze: copertina,
frontespizio, indice, capitoli, testatine e numeri di pagina. Ogni pagina è una colonna
misurata nel browser, quindi numeri e indice sono quelli reali (`statici/anteprima.js`).

Un design è un elenco di valori, mai codice. Il designer (`agenti.proponi_design`,
`agenti.modifica_design`) propone valori, `design.normalizza` accetta solo font
installati, misure nei limiti e colori leggibili. Ogni cambio è una versione nuova in
`dati/design/`, e tornare indietro crea un'altra versione.

## Privacy

- I file stanno in `dati/`, cartella con permessi 700, fuori da git.
- Il server ascolta solo su 127.0.0.1, non registra le richieste e non carica niente da fuori.
- Ogni chiamata a Claude passa i testi da stdin e non salva la sessione su disco.
- I testi passano comunque da Claude: non è un modello locale.
- Il registro contiene solo il tipo di errore, mai i testi.

## Limiti di oggi

- Non è terapia. L'intervistatore non fa diagnosi e non interpreta.
- Dopo un testo di disagio la pausa può tornare per qualche domanda. Basta un clic su "Riprendi".
- Non c'è il backup: va configurato a parte.
- Non c'è ancora il comando per rifare ricordi e bozze dagli originali. Gli originali lo permettono.
- Non esiste un modo per esportare il libro in PDF. L'anteprima si vede solo nell'app.
- I font sono quelli installati sul Mac: prima di stampare o vendere il libro va controllata la loro licenza.
- La copertina è fatta di testo e colori: non può contenere foto.
- Oltre 400.000 caratteri l'intervistatore legge i testi più recenti e tutti i ricordi, e la pagina lo dice.

## Sviluppo

```bash
.venv/bin/python -m pytest
```

I test non chiamano Claude. Le prove nel browser sì, con la persona inventata, sul motore di Safari:

```bash
tests/browser/completa.sh
```

```bash
tests/browser/guasti.sh
```

`scripts/prova.sh` avvia l'app con una cartella di prova
sulla porta 8766; `tests/dati_finti` contiene una persona inventata da importare con
`python -m libro.importa tests/dati_finti`. Non usare mai i dati veri per le prove.

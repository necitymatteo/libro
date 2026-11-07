// Cinque pagine: Scrivo io, Fammi domande, Chat, Il libro, Anteprima, piu' la pagina di ogni
// sottocapitolo. Nel codice "capitolo" e' il sottocapitolo dello schermo, "parte" il capitolo.
// I testi entrano nella pagina solo come nodi di testo, mai come HTML.

import { paginaAnteprima } from "./anteprima.js";

const pagina = document.getElementById("pagina");
const titolo = document.getElementById("titolo");
const sintesi = document.getElementById("sintesi");
const barraCapitoli = document.getElementById("capitoli");
const statoBarra = document.getElementById("stato");
const segnoDomanda = document.getElementById("domanda-pronta");
const daFare = document.getElementById("da-fare");

let turno = 0;
let timerStato = null;
let timerBozza = null;
let riprendeDopoPausa = false;
let ultimaBarra = "";
let spuntoScrittura = null;
let fineTurno = new AbortController();
let daLeggerePrima = 0;
let ricordiNoti = null;
let ricordiPrima = 0;

function el(tag, attributi = {}, ...figli) {
  const nodo = document.createElement(tag);
  for (const [chiave, valore] of Object.entries(attributi)) {
    if (valore === undefined || valore === null || valore === false) continue;
    if (chiave === "classe") nodo.className = valore;
    else if (chiave in nodo) nodo[chiave] = valore;
    else nodo.setAttribute(chiave, valore);
  }
  for (const figlio of figli.flat(Infinity)) {
    if (figlio !== null && figlio !== undefined && figlio !== false) nodo.append(figlio);
  }
  return nodo;
}

function mostra(...nodi) {
  pagina.replaceChildren(...nodi.filter(Boolean));
}

function layout(principale, laterale) {
  return el("div", { classe: laterale && laterale.length ? "contenuto" : "contenuto senza-lato" },
    el("div", { classe: "principale" }, principale),
    laterale && laterale.length ? el("aside", { classe: "lato" }, laterale) : null);
}

function bloccoLato(intestazione, ...figli) {
  return el("section", { classe: "blocco-lato" }, el("h2", {}, intestazione), figli);
}

async function api(percorso, dati) {
  const opzioni = dati === undefined
    ? {}
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(dati) };
  let risposta;
  try {
    risposta = await fetch(`/api${percorso}`, opzioni);
  } catch {
    throw new Error("L'app non risponde. Riavviala con avvia.command.");
  }
  const corpo = await risposta.json().catch(() => ({}));
  if (!risposta.ok) throw new Error(corpo.detail || "L'app ha dato un errore. Riprova.");
  return corpo;
}

function dataLunga(iso) {
  return new Date(iso).toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long" });
}

function plurale(numero, uno, tanti) {
  return numero === 1 ? `1 ${uno}` : `${numero} ${tanti}`;
}

function adattaAltezza(area, righeMinime) {
  const riga = parseFloat(getComputedStyle(area).lineHeight) || 28;
  area.style.height = "auto";
  const necessarie = Math.ceil(area.scrollHeight / riga);
  area.style.height = `${Math.max(necessarie, righeMinime) * riga}px`;
}

function contaParole(testo) {
  const pulito = testo.trim();
  return pulito ? pulito.split(/\s+/).length : 0;
}

// Un'area di scrittura che salva da sola: chiudere la pagina non perde il testo.
function areaDiScrittura({ chiave, etichetta, invito, righe, invia, alCambio, invioDiretto = false }) {
  const area = el("textarea", { "aria-label": etichetta, placeholder: invito, spellcheck: true, rows: righe });
  let attesa = null;
  area.addEventListener("input", () => {
    adattaAltezza(area, righe);
    if (alCambio) alCambio(area.value, "scrive");
    if (!chiave) return;
    clearTimeout(attesa);
    attesa = setTimeout(async () => {
      try {
        await api(`/in-corso/${chiave}`, { testo: area.value });
        if (alCambio) alCambio(area.value, "salvato");
      } catch {
        if (alCambio) alCambio(area.value, "errore");
      }
    }, 700);
  });
  area.addEventListener("keydown", (evento) => {
    const conInvio = evento.key === "Enter" && !evento.isComposing;
    if (conInvio && (evento.metaKey || (invioDiretto && !evento.shiftKey))) {
      evento.preventDefault();
      invia();
    }
  });
  if (chiave) {
    api(`/in-corso/${chiave}`).then(({ testo }) => {
      if (testo && !area.value) {
        area.value = testo;
        adattaAltezza(area, righe);
        if (alCambio) alCambio(area.value, "salvato");
      }
    }).catch(() => {});
  }
  requestAnimationFrame(() => adattaAltezza(area, righe));
  area.annullaSalvataggio = () => clearTimeout(attesa);
  return area;
}

// Il riquadro di scrittura con il conteggio delle parole e il salvataggio automatico.
function editor({ chiave, etichetta, invito, righe, testoBottone, invia, altreAzioni = [], variante = "", invioDiretto = false }) {
  const parole = el("span", { classe: "parole" }, "0 parole");
  const salvataggio = el("span", { classe: "salvataggio", "aria-live": "polite" });
  const area = areaDiScrittura({
    chiave,
    etichetta,
    invito,
    righe,
    invioDiretto,
    invia: () => bottone.click(),
    alCambio: (testo, stato) => {
      parole.textContent = plurale(contaParole(testo), "parola", "parole");
      if (stato === "salvato" && testo) salvataggio.textContent = "Salvato mentre scrivi";
      if (stato === "scrive") salvataggio.textContent = "";
      if (stato === "errore") salvataggio.textContent = "Salvataggio automatico non riuscito";
    },
  });
  const bottone = el("button", { classe: "primario", type: "button", onclick: invia }, testoBottone);
  const nodo = el("div", { classe: `editor ${variante}`.trim() }, area,
    el("div", { classe: "editor-piede" }, parole, salvataggio,
      el("div", { classe: "editor-azioni" }, altreAzioni, bottone)));
  const svuota = () => {
    area.value = "";
    adattaAltezza(area, righe);
    parole.textContent = "0 parole";
    salvataggio.textContent = "";
  };
  return { nodo, area, bottone, svuota };
}

function paginaPausa(messaggio, azioneRiprendi) {
  mostra(layout([
    el("p", { classe: "pausa" }, messaggio),
    el("div", { classe: "azioni" },
      el("button", { classe: "primario", type: "button", onclick: azioneRiprendi }, "Riprendi le domande"),
      el("a", { classe: "testuale", href: "#libro" }, "Torna al libro")),
  ]));
}

function nota(testo, classe = "aiuto") {
  return el("p", { classe, "aria-live": "polite" }, testo);
}

// Scrivo io -----------------------------------------------------------------

const NOMI_TIPO = {
  fonte: "Testo iniziale",
  annotazione: "Annotazione",
  risposta: "Risposta",
  correzione: "Correzione",
};

const NOMI_ELABORAZIONE = {
  in_attesa: "L'archivista deve ancora leggerlo",
  errore: "L'archivista non è riuscito a leggerlo",
};

function voceSalvata(voce) {
  const lunga = voce.testo.length > 420;
  const testo = el("p", { classe: `voce-testo${lunga ? " chiuso" : ""}` }, voce.testo);
  const apri = lunga
    ? el("button", {
        classe: "testuale", type: "button",
        onclick: (evento) => {
          testo.classList.toggle("chiuso");
          evento.target.textContent = testo.classList.contains("chiuso") ? "Leggi tutto" : "Chiudi";
        },
      }, "Leggi tutto")
    : null;
  const quando = new Date(voce.creato).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
  return el("article", { classe: "voce" },
    el("p", { classe: "voce-dati" },
      `${NOMI_TIPO[voce.tipo]}, ${quando}`,
      NOMI_ELABORAZIONE[voce.elaborazione] ? `. ${NOMI_ELABORAZIONE[voce.elaborazione]}` : ""),
    voce.domanda ? el("p", { classe: "voce-domanda" }, voce.domanda) : null,
    testo,
    apri);
}

function etichettaGiorno(iso) {
  const giorno = (data) => new Date(data.getFullYear(), data.getMonth(), data.getDate());
  const distanza = Math.round((giorno(new Date()) - giorno(new Date(iso))) / 86400000);
  if (distanza === 0) return "Oggi";
  if (distanza === 1) return "Ieri";
  return dataLunga(iso);
}

function elencoVoci(voci) {
  const nodi = [];
  let giorno = null;
  voci.forEach((voce) => {
    const questo = etichettaGiorno(voce.creato);
    if (questo !== giorno) {
      giorno = questo;
      nodi.push(el("h3", { classe: "giorno" }, questo));
    }
    nodi.push(voceSalvata(voce));
  });
  return nodi;
}

// Un buco del libro o una cosa da chiarire: un clic apre la scrittura con quello spunto.
function apriSpunto(testo) {
  spuntoScrittura = testo;
  if ((location.hash.replace(/^#/, "") || "scrivo") === "scrivo") vai();
  else location.hash = "#scrivo";
}

function rigaSpunto(testo) {
  return el("li", {}, el("button", {
    classe: "voce-lato", type: "button", title: "Scrivi su questo",
    onclick: () => apriSpunto(testo),
  }, testo));
}

function listaBuchi(buchi, quanti, togliCapitolo = false) {
  const voci = buchi.map((buco) => rigaSpunto(togliCapitolo ? buco.testo.replace(/^(Sotto)?[Cc]apitolo \d+: /, "") : buco.testo));
  const lista = el("ul", { classe: "elenco-lato" }, voci.slice(0, quanti));
  if (voci.length <= quanti) return [lista];
  const altri = el("button", {
    classe: "testuale", type: "button",
    onclick: () => {
      lista.append(...voci.slice(quanti));
      altri.remove();
    },
  }, `Mostra altri ${voci.length - quanti}`);
  return [lista, altri];
}

function listaRicordi(ricordi, nuovi = 0) {
  return el("ul", { classe: "elenco-lato" }, ricordi.map((ricordo, indice) => el("li", {},
    el("a", {
      classe: `voce-lato${indice < nuovi ? " nuovo" : ""}`,
      href: `#capitolo/${ricordo.capitolo ?? 0}`,
    }, ricordo.testo))));
}

async function paginaScrivo() {
  const mio = turno;
  const avviso = nota("Funziona anche la dettatura del Mac. Cmd+Invio salva.");
  const giaScritto = el("section", { classe: "sezione" });
  const lato = el("div");
  let spunto = spuntoScrittura;
  spuntoScrittura = null;
  let nuoviDaSegnare = 0;
  const riquadroSpunto = el("div", { classe: "spunto", hidden: !spunto },
    el("p", {}, el("span", { classe: "spunto-etichetta" }, "Stai scrivendo su: "), spunto || ""),
    el("button", {
      classe: "testuale", type: "button",
      onclick: () => {
        spunto = null;
        riquadroSpunto.hidden = true;
        scrittura.area.focus();
      },
    }, "Togli"));

  async function salva() {
    if (!scrittura.area.value.trim()) {
      avviso.textContent = "Scrivi qualcosa prima di salvare.";
      return;
    }
    scrittura.bottone.disabled = true;
    scrittura.area.annullaSalvataggio();
    try {
      const esito = await api("/annotazioni", { testo: scrittura.area.value, spunto });
      scrittura.svuota();
      spunto = null;
      riquadroSpunto.hidden = true;
      avviso.textContent = "Salvato. L'archivista lo sta leggendo.";
      aggiornaStato();
      if (esito.pausa) {
        paginaPausa(esito.pausa, () => {
          riprendeDopoPausa = true;
          location.hash = "#domande";
        });
        return;
      }
      await carica();
    } catch (errore) {
      avviso.textContent = errore.message;
    } finally {
      scrittura.bottone.disabled = false;
    }
  }

  const scrittura = editor({
    chiave: "annotazione",
    etichetta: "Il tuo testo",
    invito: "Scrivi o detta quello che hai in testa. Anche male.",
    righe: 9,
    testoBottone: "Salva il testo",
    invia: salva,
  });

  async function carica() {
    const [voci, libro] = await Promise.all([api("/archivio"), api("/libro")]);
    if (mio !== turno) return;
    giaScritto.replaceChildren(...(voci.length
      ? [el("h2", {}, "Già scritto"), ...elencoVoci(voci.slice(0, 30))]
      : [nota("Non c'è ancora niente. Quello che scrivi comparirà qui.")]));
    const blocchi = [];
    if (libro.buchi.length) {
      blocchi.push(bloccoLato("Da raccontare",
        listaBuchi(libro.buchi, 4),
        el("a", { classe: "secondario", href: "#domande" }, "Fammi una domanda")));
    }
    if (libro.ultimi_ricordi.length) {
      blocchi.push(bloccoLato("Ultimi ricordi salvati", listaRicordi(libro.ultimi_ricordi, nuoviDaSegnare)));
    }
    lato.replaceChildren(...blocchi);
  }

  // Appena l'archivista finisce, la colonna mostra subito cosa ha capito.
  window.addEventListener("archivista-finito", (evento) => {
    if (mio !== turno) return;
    nuoviDaSegnare = evento.detail.nuovi;
    avviso.textContent = nuoviDaSegnare
      ? `L'archivista ha trovato ${plurale(nuoviDaSegnare, "ricordo nuovo", "ricordi nuovi")}. Li vedi qui a fianco.`
      : "L'archivista ha letto il testo: nessun ricordo nuovo.";
    carica().catch(() => {});
  }, { signal: fineTurno.signal });

  mostra(layout([
    el("h1", { classe: "titolo-data" }, dataLunga(new Date().toISOString())),
    riquadroSpunto,
    scrittura.nodo,
    avviso,
    giaScritto,
  ], [lato]));
  scrittura.area.focus();
  carica().catch((errore) => { avviso.textContent = errore.message; });
}

// Fammi domande -------------------------------------------------------------

const NOMI_DOMANDA = {
  buco: "Manca un pezzo",
  scena: "Una scena",
  contraddizione: "Da chiarire",
  emozione: "Un momento preciso",
  rilettura: "Rilettura di una bozza",
};

async function storiaDomande(contenitore, mio) {
  const domande = await api("/domande");
  if (mio !== turno) return;
  if (!domande.length) {
    contenitore.replaceChildren();
    return;
  }
  contenitore.replaceChildren(
    el("h2", {}, "Già chieste"),
    ...domande.map((voce) => el("article", { classe: "voce" },
      el("p", { classe: "voce-domanda" }, voce.testo),
      voce.risposta
        ? el("p", { classe: "voce-testo chiuso" }, voce.risposta)
        : el("p", { classe: "voce-dati" }, "Saltata"))),
  );
}

async function latoDomanda(domanda, mio) {
  const blocchi = [];
  const tipo = NOMI_DOMANDA[domanda.tipo];
  if (domanda.motivo || tipo) {
    blocchi.push(bloccoLato("Perché te lo chiedo",
      el("p", { classe: "testo-lato" }, [tipo ? `${tipo}. ` : "", domanda.motivo || ""].join(""))));
  }
  if (domanda.capitolo) {
    try {
      const dati = await api(`/capitoli/${domanda.capitolo}`);
      if (mio !== turno) return blocchi;
      const attivi = dati.ricordi.filter((r) => !r.superato_da);
      blocchi.push(bloccoLato(`Capitolo ${dati.capitolo.parte_numero}, ${dati.capitolo.parte_titolo}`,
        el("p", { classe: "testo-lato capitolo-collegato" },
          puntoCapitolo({ bozza: dati.versioni.length > 0 }, attivi.length),
          el("a", { href: `#capitolo/${domanda.capitolo}` }, `${dati.capitolo.numero} ${dati.capitolo.titolo}`)),
        attivi.length ? listaRicordi(attivi) : el("p", { classe: "aiuto" }, "Ancora nessun ricordo.")));
      if (dati.buchi.length) blocchi.push(bloccoLato("Da raccontare", listaBuchi(dati.buchi, 5, true)));
    } catch {
      // Il riquadro del capitolo e' un aiuto: senza, la domanda funziona lo stesso.
    }
  }
  return blocchi;
}

async function paginaDomande(riprende = false) {
  const mio = turno;
  const storia = el("section", { classe: "sezione" });
  const latoAttesa = el("div");
  mostra(layout([
    el("div", { classe: "attesa-domanda" },
      el("span", { classe: "rotella", "aria-hidden": "true" }),
      el("p", {}, "L'intervistatore sta rileggendo tutto quello che hai scritto. Di solito ci vuole meno di un minuto.")),
    storia,
  ], [latoAttesa]));
  storiaDomande(storia, mio).catch(() => {});
  api("/libro").then((libro) => {
    if (mio === turno && libro.ultimi_ricordi.length) {
      latoAttesa.replaceChildren(bloccoLato("Ultimi ricordi salvati", listaRicordi(libro.ultimi_ricordi)));
    }
  }).catch(() => {});

  let domanda;
  try {
    domanda = await api("/domande/prossima", { riprende });
  } catch (errore) {
    if (mio !== turno) return;
    mostra(layout([
      el("p", { classe: "errore" }, errore.message),
      el("div", { classe: "azioni" },
        el("button", { classe: "primario", type: "button", onclick: () => paginaDomande(riprende) }, "Riprova")),
      storia,
    ]));
    return;
  }
  if (mio !== turno) return;
  aggiornaStato();
  if (domanda.stato === "pausa") {
    paginaPausa(domanda.messaggio, () => paginaDomande(true));
    return;
  }

  const avviso = nota(domanda.contesto_parziale
    ? "Hai scritto molto: questa volta l'intervistatore ha letto i testi più recenti e tutti i ricordi."
    : "Puoi saltare ogni domanda. Cmd+Invio invia la risposta.");

  async function rispondi() {
    if (!risposta.area.value.trim()) {
      avviso.textContent = "Scrivi una risposta, oppure salta la domanda.";
      return;
    }
    risposta.bottone.disabled = true;
    risposta.area.annullaSalvataggio();
    try {
      const esito = await api(`/domande/${domanda.id}/risposta`, { testo: risposta.area.value });
      aggiornaStato();
      if (esito.pausa) {
        paginaPausa(esito.pausa, () => paginaDomande(true));
        return;
      }
      paginaDomande();
    } catch (errore) {
      avviso.textContent = errore.message;
      risposta.bottone.disabled = false;
    }
  }

  async function salta() {
    try {
      await api(`/domande/${domanda.id}/salta`, {});
      aggiornaStato();
      paginaDomande();
    } catch (errore) {
      avviso.textContent = errore.message;
    }
  }

  const risposta = editor({
    chiave: "risposta",
    etichetta: "La tua risposta",
    invito: "Rispondi come viene.",
    righe: 7,
    testoBottone: "Rispondi",
    invia: rispondi,
    variante: "editor-alto",
    altreAzioni: [
      el("button", { classe: "testuale", type: "button", onclick: salta }, "Salta"),
      el("a", { classe: "testuale", href: "#libro" }, "Basta per oggi"),
    ],
  });

  const lato = el("div");
  mostra(layout([
    el("h1", { classe: "domanda" }, domanda.testo),
    domanda.aggancio ? el("p", { classe: "aggancio" }, `Da una tua frase: «${domanda.aggancio}»`) : null,
    risposta.nodo,
    avviso,
    storia,
  ], [lato]));
  risposta.area.focus();
  latoDomanda(domanda, mio).then((blocchi) => {
    if (mio === turno) lato.replaceChildren(...blocchi);
  }).catch(() => {});
}

// Chat -----------------------------------------------------------------------

const SPUNTI_CHAT = [
  "Dove sta andando il libro secondo te?",
  "Cosa regge finora, e cosa no?",
  "Qual è il capitolo più debole?",
];

function cartaProposta(messaggio, aggiorna) {
  const proposta = messaggio.proposta;
  const avviso = el("p", { classe: "errore", hidden: true });
  const decidi = async (azione) => {
    try {
      await api(`/chat/${messaggio.id}/proposta`, { azione });
      aggiornaStato();
      aggiorna();
    } catch (errore) {
      avviso.textContent = errore.message;
      avviso.hidden = false;
    }
  };
  return el("div", { classe: "proposta" },
    el("h3", {}, "Proposta"),
    proposta.motivo ? el("p", { classe: "aiuto" }, proposta.motivo) : null,
    proposta.titolo ? el("p", {}, el("span", { classe: "proposta-voce" }, "Titolo: "), proposta.titolo) : null,
    proposta.filo ? el("p", {}, el("span", { classe: "proposta-voce" }, "Filo: "), proposta.filo) : null,
    proposta.struttura
      ? el("ol", { classe: "proposta-struttura" }, proposta.struttura.map((parte) => el("li", {},
          el("span", { classe: "proposta-capitolo" }, parte.titolo),
          el("ul", {}, parte.capitoli.map((voce) => el("li", {}, voce.titolo))))))
      : null,
    messaggio.esito_proposta
      ? el("p", { classe: "aiuto" }, messaggio.esito_proposta === "applicata" ? "Applicata." : "Lasciata stare.")
      : el("div", { classe: "azioni" },
          el("button", { classe: "primario", type: "button", onclick: () => decidi("applica") }, "Applica"),
          el("button", { classe: "testuale", type: "button", onclick: () => decidi("scarta") }, "Lascia stare")),
    avviso);
}

async function paginaChat() {
  const mio = turno;
  const elenco = el("div", { classe: "messaggi" });
  const avviso = nota("Invio manda il messaggio. Maiusc+Invio va a capo. Ha letto tutto quello che hai scritto.");
  const lato = el("div");
  let firma = "";
  let attesa = null;

  async function invia(testoDiretto) {
    const testo = testoDiretto || scrittura.area.value;
    if (!testo.trim()) {
      avviso.textContent = "Scrivi qualcosa prima di mandarlo.";
      return;
    }
    scrittura.bottone.disabled = true;
    scrittura.area.annullaSalvataggio();
    try {
      await api("/chat", { testo });
      scrittura.svuota();
      await aggiorna();
      aggiornaStato();
    } catch (errore) {
      avviso.textContent = errore.message;
      scrittura.bottone.disabled = false;
    }
  }

  const scrittura = editor({
    chiave: "chat",
    etichetta: "Il tuo messaggio",
    invito: "Scrivi quello che vuoi: un'idea, un dubbio, delle note.",
    righe: 2,
    testoBottone: "Invia",
    invia: () => invia(),
    variante: "editor-compatto",
    invioDiretto: true,
  });

  function disegnaMessaggio(messaggio) {
    if (messaggio.autore === "tu") return el("div", { classe: "messaggio messaggio-tu" }, messaggio.testo);
    return el("div", { classe: `messaggio messaggio-agente${messaggio.errore ? " messaggio-errore" : ""}` },
      messaggio.testo,
      messaggio.proposta ? cartaProposta(messaggio, aggiorna) : null);
  }

  async function aggiorna() {
    let dati;
    try {
      dati = await api("/chat");
    } catch (errore) {
      avviso.textContent = errore.message;
      return;
    }
    if (mio !== turno) return;
    const nuova = JSON.stringify([dati.messaggi, dati.in_corso]);
    if (nuova !== firma) {
      firma = nuova;
      const nodi = dati.messaggi.map(disegnaMessaggio);
      const ultimo = dati.messaggi[dati.messaggi.length - 1];
      if (dati.in_corso) {
        nodi.push(el("div", { classe: "attesa-domanda attesa-chat" },
          el("span", { classe: "rotella", "aria-hidden": "true" }),
          el("p", {}, "Sta rileggendo il libro prima di risponderti.")));
      } else if (ultimo && (ultimo.errore || ultimo.autore === "tu")) {
        nodi.push(el("div", { classe: "azioni" }, el("button", {
          classe: "secondario", type: "button",
          onclick: async () => {
            try {
              await api("/chat/riprova", {});
              aggiorna();
            } catch (errore) {
              avviso.textContent = errore.message;
            }
          },
        }, "Riprova")));
      }
      if (!dati.messaggi.length) {
        nodi.push(el("div", { classe: "chat-vuota" },
          el("h1", {}, "Parliamo del libro"),
          el("p", { classe: "riassunto" }, "Dagli una nota, un'idea o un dubbio. Conosce tutto quello che hai scritto e dove sta andando il libro."),
          el("div", { classe: "azioni" }, SPUNTI_CHAT.map((spunto) =>
            el("button", { classe: "secondario", type: "button", onclick: () => invia(spunto) }, spunto)))));
      }
      elenco.replaceChildren(...nodi);
      const contesto = dati.contesto;
      lato.replaceChildren(
        bloccoLato("Dove sta andando il libro",
          el("p", { classe: "testo-lato testo-lato-forte" }, contesto.titolo),
          contesto.filo ? el("p", { classe: "testo-lato" }, contesto.filo) : null),
        bloccoLato("Capitoli",
          el("ul", { classe: "elenco-lato" }, contesto.parti.map((parte) => el("li", {},
            el("span", { classe: "voce-ferma" }, `${parte.numero}. ${parte.titolo}`))))),
        bloccoLato("Cosa ha letto",
          el("p", { classe: "testo-lato" },
            `${plurale(contesto.testi, "testo", "testi")}, ${plurale(contesto.ricordi, "ricordo", "ricordi")}, ${plurale(contesto.bozze, "bozza", "bozze")}.`)));
      window.scrollTo(0, document.documentElement.scrollHeight);
    }
    scrittura.bottone.disabled = dati.in_corso;
    clearTimeout(attesa);
    if (dati.in_corso) attesa = setTimeout(() => { if (mio === turno) aggiorna(); }, 1200);
  }

  mostra(layout([
    el("div", { classe: "colonna-chat" },
      elenco,
      el("div", { classe: "compositore" }, scrittura.nodo, avviso)),
  ], [lato]));
  scrittura.area.focus();
  await aggiorna();
}

// Il libro -------------------------------------------------------------------

const NOMI_STATO = {
  pieno: "Materiale forte",
  parziale: "Mancano pezzi",
  vuoto: "Quasi niente",
};

function puntoCapitolo(capitolo, conta) {
  if (capitolo.versioni || capitolo.bozza) return el("span", { classe: "punto scritto", title: "Bozza scritta" });
  if (conta) return el("span", { classe: "punto ricordi", title: "Solo ricordi" });
  return el("span", { classe: "punto vuoto", title: "Quasi niente" });
}

// Quello che e' cambiato dall'ultima visita resta segnato finche' non l'hai visto.
function ricordiVisti() {
  try {
    return JSON.parse(localStorage.getItem("ricordi-visti"));
  } catch {
    return null;
  }
}

function segnaVisti(capitoli) {
  try {
    localStorage.setItem("ricordi-visti", JSON.stringify(Object.fromEntries(
      capitoli.map((c) => [c.id, c.ricordi_libro + c.ricordi_privati]))));
  } catch {
    // Senza memoria del browser l'app funziona lo stesso.
  }
}

const NOMI_SCELTA = {
  da_decidere: "Da decidere",
  consenso: "Ho il consenso",
  nome_cambiato: "Nome cambiato",
  niente: "Fuori dal libro",
};

function rigaPersona(nome, dati) {
  const alias = el("input", {
    type: "text", value: dati.alias || "", placeholder: "Nome nel libro",
    "aria-label": `Nome nel libro per ${nome}`,
    hidden: dati.scelta !== "nome_cambiato",
  });
  const avviso = el("p", { classe: "errore", hidden: true });
  const scelta = el("select", { "aria-label": `Scelta per ${nome}` },
    Object.entries(NOMI_SCELTA).map(([valore, testo]) =>
      el("option", { value: valore, selected: valore === dati.scelta }, testo)));
  async function salva() {
    alias.hidden = scelta.value !== "nome_cambiato";
    if (scelta.value === "nome_cambiato" && !alias.value.trim()) {
      alias.focus();
      return;
    }
    try {
      await api("/persone", { nome, scelta: scelta.value, alias: alias.value });
      avviso.hidden = true;
    } catch (errore) {
      avviso.textContent = errore.message;
      avviso.hidden = false;
    }
  }
  scelta.addEventListener("change", salva);
  alias.addEventListener("change", salva);
  return el("div", {},
    el("div", { classe: "persona" }, el("span", {}, nome), alias, scelta),
    avviso);
}

// Cambiare capitoli e sottocapitoli a mano. Ricordi e bozze restano dove sono: cambia solo l'ordine.
function pannelloStruttura(dati) {
  const bozza = dati.parti.map((parte) => ({
    titolo: parte.titolo,
    tema: parte.tema || "",
    capitoli: dati.capitoli.filter((c) => c.parte === parte.id).map((c) => ({ id: c.id, titolo: c.titolo })),
  }));
  const corpo = el("div", {});
  const avviso = nota("Ricordi e bozze seguono i loro sottocapitoli: non si perde niente.");

  const sposta = (lista, indice, passo) => {
    const destinazione = indice + passo;
    if (destinazione < 0 || destinazione >= lista.length) return;
    [lista[indice], lista[destinazione]] = [lista[destinazione], lista[indice]];
    disegna();
  };
  const frecce = (lista, indice, nome) => [
    el("button", {
      classe: "testuale", type: "button", disabled: indice === 0,
      "aria-label": `Sposta su ${nome}`, onclick: () => sposta(lista, indice, -1),
    }, "Su"),
    el("button", {
      classe: "testuale", type: "button", disabled: indice === lista.length - 1,
      "aria-label": `Sposta giù ${nome}`, onclick: () => sposta(lista, indice, 1),
    }, "Giù"),
  ];

  function disegna() {
    corpo.replaceChildren(...bozza.map((parte, p) => el("section", { classe: "struttura-parte" },
      el("div", { classe: "struttura-riga struttura-testa" },
        el("span", { classe: "struttura-numero" }, String(p + 1)),
        el("input", {
          type: "text", value: parte.titolo, "aria-label": `Titolo del capitolo ${p + 1}`,
          oninput: (evento) => { parte.titolo = evento.target.value; },
        }),
        frecce(bozza, p, `il capitolo ${p + 1}`)),
      parte.capitoli.map((voce, v) => {
        const destinazione = el("select", { "aria-label": `Capitolo di ${voce.titolo}` },
          bozza.map((altra, a) => el("option", { value: String(a), selected: a === p }, `Capitolo ${a + 1}`)));
        destinazione.addEventListener("change", () => {
          parte.capitoli.splice(v, 1);
          bozza[Number(destinazione.value)].capitoli.push(voce);
          disegna();
        });
        return el("div", { classe: "struttura-riga" },
          el("span", { classe: "struttura-numero" }, `${p + 1}.${v + 1}`),
          el("input", {
            type: "text", value: voce.titolo, "aria-label": `Titolo del sottocapitolo ${p + 1}.${v + 1}`,
            oninput: (evento) => { voce.titolo = evento.target.value; },
          }),
          destinazione,
          frecce(parte.capitoli, v, voce.titolo));
      }),
      el("button", {
        classe: "testuale struttura-aggiungi", type: "button",
        onclick: () => {
          parte.capitoli.push({ id: null, titolo: "Nuovo sottocapitolo" });
          disegna();
        },
      }, "Aggiungi un sottocapitolo"))));
  }

  disegna();
  return el("details", { classe: "struttura sezione" },
    el("summary", {}, "Cambia capitoli e sottocapitoli"),
    corpo,
    el("div", { classe: "azioni" },
      el("button", {
        classe: "primario", type: "button",
        onclick: async () => {
          try {
            await api("/struttura", { parti: bozza.filter((parte) => parte.capitoli.length) });
            aggiornaStato();
            paginaLibro();
          } catch (errore) {
            avviso.textContent = errore.message;
          }
        },
      }, "Salva la struttura"),
      el("button", {
        classe: "secondario", type: "button",
        onclick: () => {
          bozza.push({ titolo: "Nuovo capitolo", tema: "", capitoli: [] });
          disegna();
        },
      }, "Aggiungi un capitolo")),
    avviso);
}

async function paginaLibro() {
  const mio = turno;
  let dati;
  try {
    dati = await api("/libro");
  } catch (errore) {
    mostra(layout([el("p", { classe: "errore" }, errore.message)]));
    return;
  }
  if (mio !== turno) return;

  const visti = ricordiVisti();
  const massimo = Math.max(1, ...dati.capitoli.map((c) => c.ricordi_libro + c.ricordi_privati));
  const frasiDaVerificare = dati.capitoli.reduce((somma, c) => somma + c.da_verificare, 0);
  const daScrivere = dati.capitoli.filter((c) => !c.versioni && c.ricordi_libro >= dati.ricordi_minimi);
  const inScrittura = dati.capitoli.some((c) => c.lavoro && ["in_attesa", "in_corso"].includes(c.lavoro.stato));

  const righe = dati.capitoli.map((capitolo) => {
    const totale = capitolo.ricordi_libro + capitolo.ricordi_privati;
    const prima = visti ? visti[capitolo.id] : undefined;
    const nuovi = prima === undefined ? 0 : Math.max(totale - prima, 0);
    const misura = el("span", { classe: "misura" });
    misura.style.width = `${Math.round((totale / massimo) * 72)}px`;
    const inCorso = capitolo.lavoro && ["in_attesa", "in_corso"].includes(capitolo.lavoro.stato);
    let bozza = "Non ancora";
    if (inCorso) bozza = "In scrittura";
    else if (capitolo.versioni) bozza = `Versione ${capitolo.versioni}`;
    return el("tr", {
      classe: "riga-sotto",
      "data-parte": capitolo.parte,
      onclick: (evento) => {
        if (evento.target.tagName !== "A") location.hash = `#capitolo/${capitolo.id}`;
      },
    },
      el("td", { classe: "num" }, capitolo.numero),
      el("td", {}, el("span", { classe: "cella-titolo" },
        puntoCapitolo(capitolo, totale),
        el("a", { href: `#capitolo/${capitolo.id}` }, capitolo.titolo))),
      el("td", {}, NOMI_STATO[capitolo.stato] || capitolo.stato),
      el("td", { classe: "cella-ricordi" }, misura, el("span", { classe: "num" }, String(totale)),
        nuovi ? el("span", { classe: "nuovi" }, `+${nuovi}`) : null),
      el("td", {}, bozza),
      el("td", { classe: capitolo.da_verificare ? "da-verificare" : "" },
        capitolo.da_verificare ? plurale(capitolo.da_verificare, "frase", "frasi") : ""));
  });
  segnaVisti(dati.capitoli);
  const righeLibro = dati.parti.flatMap((parte) => {
    const sotto = dati.capitoli.filter((c) => c.parte === parte.id);
    const ricordiParte = sotto.reduce((somma, c) => somma + c.ricordi_libro + c.ricordi_privati, 0);
    const fatti = sotto.filter((c) => c.versioni).length;
    return [
      el("tr", { classe: "riga-parte" }, el("td", { colSpan: 6 },
        el("span", { classe: "parte-testa" },
          el("span", { classe: "parte-titolo" }, `${parte.numero}. ${parte.titolo}`),
          el("span", { classe: "parte-dati" },
            `${fatti} di ${plurale(sotto.length, "sottocapitolo scritto", "sottocapitoli scritti")}, ${plurale(ricordiParte, "ricordo", "ricordi")}`)),
        parte.tema ? el("span", { classe: "parte-tema" }, parte.tema) : null)),
      ...righe.filter((riga) => riga.dataset.parte === parte.id),
    ];
  });

  const persone = Object.entries(dati.persone);
  const daDecidere = persone.filter(([, p]) => p.scelta === "da_decidere").length;
  const lato = [];
  if (dati.buchi.length) lato.push(bloccoLato("Da raccontare", listaBuchi(dati.buchi, 6)));
  if (dati.contraddizioni.length) {
    lato.push(bloccoLato("Da chiarire",
      el("ul", { classe: "elenco-lato" }, dati.contraddizioni.map((c) => rigaSpunto(c.testo)))));
  }
  if (dati.decisioni.length) {
    lato.push(bloccoLato("Decisioni che spettano a te",
      el("ul", { classe: "elenco-lato" }, dati.decisioni.map((d) => el("li", {},
        /person/i.test(d) && persone.length
          ? el("button", {
              classe: "voce-lato", type: "button",
              onclick: () => document.getElementById("persone-vere").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" }),
            }, d)
          : el("span", { classe: "voce-ferma" }, d))))));
  }

  const avvisoScrittura = nota("");
  avvisoScrittura.hidden = true;
  const azioni = [];
  if (daScrivere.length) {
    azioni.push(el("button", {
      classe: "primario", type: "button", disabled: inScrittura,
      onclick: async () => {
        try {
          await api("/bozze/mancanti", {});
          aggiornaStato();
          paginaLibro();
        } catch (errore) {
          avvisoScrittura.textContent = errore.message;
          avvisoScrittura.hidden = false;
        }
      },
    }, `Scrivi ${plurale(daScrivere.length, "bozza mancante", "bozze mancanti")}`));
  }
  azioni.push(el("a", { classe: "secondario", href: "#anteprima" }, "Guarda come esce"));
  azioni.push(el("a", { classe: "secondario", href: "#domande" }, "Fammi una domanda"));

  mostra(layout([
    el("h1", {}, dati.titolo),
    el("p", { classe: "riassunto riassunto-libro" }, [
      dati.buchi.length ? plurale(dati.buchi.length, "cosa da raccontare", "cose da raccontare") : null,
      daDecidere ? plurale(daDecidere, "persona da decidere", "persone da decidere") : null,
      frasiDaVerificare ? plurale(frasiDaVerificare, "frase da verificare", "frasi da verificare") : null,
    ].filter(Boolean).join(", ") || "Niente in sospeso."),
    dati.filo ? el("p", { classe: "filo" }, dati.filo) : null,
    el("div", { classe: "azioni" }, azioni),
    avvisoScrittura,
    dati.capitoli.length
      ? el("div", { classe: "contenitore-tabella" }, el("table", { classe: "tabella" },
          el("thead", {}, el("tr", {},
            el("th", {}, el("span", { classe: "solo-lettori" }, "Numero")),
            el("th", {}, "Sottocapitolo"),
            el("th", {}, "Materiale"),
            el("th", {}, "Ricordi"),
            el("th", {}, "Bozza"),
            el("th", {}, "Da verificare"))),
          el("tbody", {}, righeLibro)))
      : nota("Non ci sono ancora capitoli. Inizia da Scrivo io."),
    dati.capitoli.length
      ? el("p", { classe: "legenda" },
          el("span", {}, el("span", { classe: "punto scritto" }), "Bozza scritta"),
          el("span", {}, el("span", { classe: "punto ricordi" }), "Solo ricordi"),
          el("span", {}, el("span", { classe: "punto vuoto" }), "Quasi niente"))
      : null,
    dati.senza_capitolo
      ? el("p", { classe: "aiuto" }, el("a", { href: "#capitolo/0" }, plurale(dati.senza_capitolo, "ricordo senza sottocapitolo", "ricordi senza sottocapitolo")))
      : null,
    dati.capitoli.length ? pannelloStruttura(dati) : null,
    persone.length
      ? el("section", { classe: "sezione", id: "persone-vere" },
          el("h2", {}, "Persone vere"),
          el("p", { classe: "aiuto" },
            `${daDecidere ? `${plurale(daDecidere, "scelta", "scelte")} da fare. ` : ""}Decidi per ognuna prima di pubblicare. Chi è fuori dal libro non entra nelle bozze.`),
          persone.map(([nome, valore]) => rigaPersona(nome, valore)))
      : null,
  ], lato));

  if (inScrittura) {
    timerBozza = setTimeout(() => { if (mio === turno) paginaLibro(); }, 5000);
  }
}

// Un capitolo ----------------------------------------------------------------

function bloccoParagrafo(paragrafo, dati, modificabile, ricarica) {
  const dettagli = el("div", {});
  const contenuto = el("div", {});

  function apriFonti(frase) {
    if (dettagli.dataset.aperta === frase.testo) {
      dettagli.replaceChildren();
      delete dettagli.dataset.aperta;
      return;
    }
    dettagli.dataset.aperta = frase.testo;
    const voci = [];
    frase.segnalazioni.forEach((s) => voci.push(el("p", { classe: "segnalazione" }, s)));
    frase.fonti.forEach((id) => {
      const fonte = dati.fonti[id];
      if (!fonte) return;
      voci.push(el("p", { classe: "citazione" }, `«${fonte.citazione}»`));
      voci.push(el("p", { classe: "aiuto" }, fonte.testo));
    });
    if (!voci.length) voci.push(el("p", { classe: "aiuto" }, "Frase di collegamento: non contiene fatti."));
    dettagli.replaceChildren(el("div", { classe: "fonti" }, voci));
  }

  function leggi() {
    if (paragrafo.autore === "tu") {
      contenuto.replaceChildren(el("p", { classe: "testo-bozza" }, paragrafo.testo));
      return;
    }
    const frasi = [];
    paragrafo.frasi.forEach((frase, indice) => {
      if (indice) frasi.push(" ");
      frasi.push(el("span", {
        classe: `frase${frase.segnalazioni.length ? " segnalata" : ""}`,
        tabIndex: 0,
        role: "button",
        title: "Mostra da dove viene",
        onclick: () => apriFonti(frase),
        onkeydown: (evento) => {
          if (evento.key === "Enter" || evento.key === " ") {
            evento.preventDefault();
            apriFonti(frase);
          }
        },
      }, frase.testo));
    });
    contenuto.replaceChildren(el("p", { classe: "testo-bozza" }, frasi), dettagli);
  }

  function correggi() {
    const iniziale = paragrafo.autore === "tu"
      ? paragrafo.testo
      : paragrafo.frasi.map((f) => f.testo).join(" ");
    const avviso = nota("Lo scrittore non cambierà più questo paragrafo. Svuotalo per toglierlo dal capitolo.");
    async function salva() {
      if (area.value === iniziale) {
        leggi();
        return;
      }
      try {
        await api(`/capitoli/${dati.capitolo.id}/paragrafi/${paragrafo.id}`, { testo: area.value });
        aggiornaStato();
        ricarica();
      } catch (errore) {
        avviso.textContent = errore.message;
      }
    }
    const area = areaDiScrittura({ etichetta: "Correggi il paragrafo", invito: "", righe: 3, invia: salva });
    area.value = iniziale;
    contenuto.replaceChildren(
      el("div", { classe: "editor editor-compatto" }, area,
        el("div", { classe: "editor-piede" },
          el("div", { classe: "editor-azioni" },
            el("button", { classe: "testuale", type: "button", onclick: leggi }, "Annulla"),
            el("button", { classe: "primario", type: "button", onclick: salva }, "Salva la correzione")))),
      avviso);
    requestAnimationFrame(() => adattaAltezza(area, 3));
    area.focus();
  }

  leggi();
  return el("div", { classe: "paragrafo" },
    contenuto,
    el("div", { classe: "paragrafo-azioni" },
      paragrafo.autore === "tu" ? el("span", { classe: "scritto-da-te" }, "Scritto da te") : null,
      modificabile ? el("button", { classe: "testuale", type: "button", onclick: correggi }, "Correggi") : null));
}

function rigaRicordo(ricordo, indice, ricarica, aperto = false) {
  const avviso = el("p", { classe: "errore", hidden: true });
  const segnala = (errore) => {
    avviso.textContent = errore.message;
    avviso.hidden = false;
  };
  const scelta = el("select", { "aria-label": "Dove va questo ricordo" },
    el("option", { value: "libro", selected: ricordo.privacy === "libro" }, "Nel libro"),
    el("option", { value: "solo_appunti", selected: ricordo.privacy !== "libro" }, "Solo appunti"));
  scelta.addEventListener("change", () => {
    api(`/ricordi/${ricordo.id}`, { privacy: scelta.value }).then(() => {
      aggiornaStato();
      ricarica();
    }).catch(segnala);
  });
  const capitolo = el("select", { "aria-label": "Sottocapitolo del ricordo" },
    el("option", { value: "", selected: ricordo.capitolo === null }, "Senza sottocapitolo"),
    indice.map((c) => el("option", { value: String(c.id), selected: c.id === ricordo.capitolo }, `${c.numero} ${c.titolo}`)));
  capitolo.addEventListener("change", async () => {
    const valore = capitolo.value === "" ? null : Number(capitolo.value);
    try {
      await api(`/ricordi/${ricordo.id}`, { capitolo: valore, cambia_capitolo: true });
      aggiornaStato();
      ricarica();
    } catch (errore) {
      segnala(errore);
    }
  });
  const superato = Boolean(ricordo.superato_da);
  const scelte = el("div", { classe: "ricordo-scelte" }, scelta, capitolo);
  return el("article", { classe: `ricordo${superato ? " superato" : ""}` },
    el("p", { classe: "ricordo-testo" }, ricordo.testo),
    el("p", { classe: "ricordo-citazione" }, `«${ricordo.citazione}»`),
    !superato && ricordo.privacy !== "libro" ? el("p", { classe: "ricordo-privato" }, "Solo appunti") : null,
    superato
      ? el("p", { classe: "aiuto" }, "Superato da una tua correzione.")
      : aperto
        ? scelte
        : el("details", { classe: "ricordo-cambia" }, el("summary", {}, "Cambia"), scelte),
    avviso);
}

async function paginaCapitolo(id, versione) {
  const mio = turno;
  clearTimeout(timerBozza);
  let dati;
  try {
    dati = await api(`/capitoli/${id}${versione ? `?versione=${versione}` : ""}`);
  } catch (errore) {
    mostra(layout([el("p", { classe: "errore" }, errore.message)]));
    return;
  }
  if (mio !== turno) return;
  const ricarica = () => paginaCapitolo(id);
  const { capitolo, bozza, versioni, lavoro } = dati;
  const scrive = lavoro && ["in_attesa", "in_corso"].includes(lavoro.stato);
  const ultima = versioni.length ? versioni[versioni.length - 1] : null;
  const leggendoUltima = !bozza || bozza.versione === ultima;
  const attivi = dati.ricordi.filter((r) => !r.superato_da).length;
  const elencoRicordi = dati.ricordi.length
    ? dati.ricordi.map((r) => rigaRicordo(r, dati.indice, ricarica, !id))
    : nota("Nessun ricordo qui. L'archivista li aggiunge quando scrivi o rispondi.");

  if (!id) {
    mostra(layout([
      el("h1", {}, capitolo.titolo),
      el("p", { classe: "riassunto" }, "Scegli un sottocapitolo per ognuno: così lo scrittore può usarli."),
      el("div", { classe: "griglia-ricordi" }, elencoRicordi),
    ]));
    return;
  }

  if (scrive) timerBozza = setTimeout(() => { if (mio === turno) ricarica(); }, 4000);

  const avviso = el("p", { classe: "aiuto", "aria-live": "polite" });
  if (scrive) avviso.textContent = "Lo scrittore è al lavoro. Di solito ci vogliono da 1 a 3 minuti.";
  else if (lavoro && lavoro.stato === "errore") {
    avviso.textContent = lavoro.messaggio;
    avviso.className = "errore";
  }

  async function scrivi() {
    try {
      await api(`/capitoli/${id}/bozza`, {});
      aggiornaStato();
      ricarica();
    } catch (errore) {
      avviso.textContent = errore.message;
      avviso.className = "errore";
    }
  }

  const segnalate = bozza
    ? bozza.paragrafi.flatMap((p) => p.frasi || []).filter((f) => f.segnalazioni.length).length
    : 0;
  let esitoControllo = null;
  if (bozza) {
    const spiegazione = "Clicca una frase per vedere da dove viene.";
    if (bozza.controllo === "non_eseguito") {
      esitoControllo = `${spiegazione} Il secondo controllo non è partito: riscrivi la bozza per rifarlo.`;
    } else if (segnalate) {
      esitoControllo = segnalate === 1
        ? `${spiegazione} Il controllo chiede di verificarne 1: è sottolineata.`
        : `${spiegazione} Il controllo chiede di verificarne ${segnalate}: sono sottolineate.`;
    } else {
      esitoControllo = `${spiegazione} Il controllo non ha trovato fatti senza fonte.`;
    }
  }

  const selettore = versioni.length > 1
    ? el("select", { "aria-label": "Versione della bozza" },
        [...versioni].reverse().map((n) =>
          el("option", { value: String(n), selected: bozza && n === bozza.versione }, `Versione ${n}`)))
    : null;
  if (selettore) selettore.addEventListener("change", () => paginaCapitolo(id, Number(selettore.value)));

  const avvisoNota = nota("Lo scrittore legge la nota alla prossima bozza.");
  async function salvaNota() {
    if (!appunto.area.value.trim()) {
      avvisoNota.textContent = "Scrivi la nota prima di salvarla.";
      return;
    }
    try {
      await api(`/capitoli/${id}/nota`, { testo: appunto.area.value });
      appunto.svuota();
      avvisoNota.textContent = "Nota salvata.";
      aggiornaStato();
    } catch (errore) {
      avvisoNota.textContent = errore.message;
    }
  }
  const appunto = editor({
    etichetta: "Nota per lo scrittore",
    invito: "Non è andata così, questo è troppo finto, qui manca una cosa...",
    righe: 2,
    testoBottone: "Salva la nota",
    invia: salvaNota,
    variante: "editor-compatto",
  });

  const lato = [];
  if (dati.buchi.length) {
    lato.push(bloccoLato("Da raccontare",
      listaBuchi(dati.buchi, 5, true),
      el("a", { classe: "secondario", href: "#domande" }, "Fammi una domanda")));
  }
  lato.push(bloccoLato(plurale(attivi, "ricordo", "ricordi"), elencoRicordi));

  mostra(layout([
    el("h1", { classe: "titolo-capitolo" },
      puntoCapitolo({ bozza: versioni.length > 0 }, attivi),
      `${capitolo.numero} ${capitolo.titolo}`),
    el("p", { classe: "riassunto" },
      `Capitolo ${capitolo.parte_numero}, ${capitolo.parte_titolo}.${capitolo.tema ? ` ${capitolo.tema}` : ""}`),
    el("div", { classe: "azioni" },
      el("button", { classe: bozza ? "secondario" : "primario", type: "button", disabled: scrive, onclick: scrivi },
        bozza ? "Riscrivi la bozza" : "Scrivi la bozza"),
      selettore,
      el("a", { classe: "testuale", href: "#anteprima" }, "Guarda come esce")),
    avviso,
    esitoControllo ? nota(esitoControllo) : null,
    bozza
      ? el("div", { classe: "bozza" }, bozza.paragrafi.map((p) => bloccoParagrafo(p, dati, leggendoUltima, ricarica)))
      : el("p", { classe: "aiuto bozza-vuota" }, attivi >= dati.ricordi_minimi
          ? "Questo sottocapitolo non ha ancora una bozza."
          : `Servono almeno ${dati.ricordi_minimi} ricordi per il libro. Rispondi a qualche domanda per aggiungerne.`),
    el("section", { classe: "sezione" }, el("h2", {}, "Nota per lo scrittore"), appunto.nodo, avvisoNota),
  ], lato));
}

// La barra laterale -----------------------------------------------------------

// Quali capitoli restano aperti nella barra: lo ricorda il browser, senza non succede niente.
function partiAperte() {
  try {
    return JSON.parse(localStorage.getItem("parti-aperte")) || [];
  } catch {
    return [];
  }
}

function segnaParte(id, aperta) {
  try {
    const altre = partiAperte().filter((voce) => voce !== id);
    localStorage.setItem("parti-aperte", JSON.stringify(aperta ? [...altre, id] : altre));
  } catch {
    // Senza memoria del browser la barra funziona lo stesso.
  }
}

function voceDaFare(href, testo, numero) {
  return el("a", { classe: "cap da-fare-voce", href },
    el("span", { classe: "cap-titolo" }, testo),
    el("span", { classe: "cap-num" }, String(numero)));
}

function disegnaBarra(dati) {
  const firma = JSON.stringify([
    dati.titolo, dati.parti, dati.capitoli, dati.senza_capitolo, dati.ricordi, dati.da_raccontare,
    dati.da_verificare, dati.capitolo_da_verificare, dati.persone_da_decidere,
  ]);
  titolo.textContent = dati.titolo;
  document.title = dati.titolo;
  sintesi.textContent = `${plurale(dati.ricordi, "ricordo", "ricordi")}, ${plurale(dati.scritti, "sottocapitolo scritto", "sottocapitoli scritti")} su ${dati.capitoli.length}`;
  segnoDomanda.hidden = !dati.domanda_pronta;
  if (firma !== ultimaBarra) {
    ultimaBarra = firma;
    const cose = [];
    if (dati.da_raccontare) cose.push(voceDaFare("#domande", "Da raccontare", dati.da_raccontare));
    if (dati.da_verificare) cose.push(voceDaFare(`#capitolo/${dati.capitolo_da_verificare}`, "Frasi da verificare", dati.da_verificare));
    if (dati.persone_da_decidere) cose.push(voceDaFare("#libro", "Persone da decidere", dati.persone_da_decidere));
    daFare.hidden = !cose.length;
    daFare.replaceChildren(el("h2", {}, "Da fare"), ...cose);
    const aperte = partiAperte();
    const voci = dati.parti.map((parte) => {
      const sotto = dati.capitoli.filter((c) => c.parte === parte.id);
      const gruppo = el("details", { classe: "parte", open: aperte.includes(parte.id) },
        el("summary", {},
          el("span", { classe: "cap-titolo" }, `${parte.numero}. ${parte.titolo}`),
          el("span", { classe: "cap-num" }, String(parte.ricordi))),
        sotto.map((capitolo) => el("a", { classe: "cap", href: `#capitolo/${capitolo.id}`, "data-capitolo": String(capitolo.id) },
          puntoCapitolo(capitolo, capitolo.ricordi),
          el("span", { classe: "cap-titolo" }, capitolo.titolo),
          el("span", { classe: "cap-num" }, String(capitolo.ricordi)))));
      gruppo.addEventListener("toggle", () => segnaParte(parte.id, gruppo.open));
      return gruppo;
    });
    if (dati.senza_capitolo) {
      voci.push(el("a", { classe: "cap cap-sciolto", href: "#capitolo/0", "data-capitolo": "0" },
        el("span", { classe: "punto vuoto" }),
        el("span", { classe: "cap-titolo" }, "Senza sottocapitolo"),
        el("span", { classe: "cap-num" }, String(dati.senza_capitolo))));
    }
    barraCapitoli.replaceChildren(...voci);
  }
  segnaBarraAttiva();
}

function segnaBarraAttiva() {
  const [nome, valore] = location.hash.replace(/^#/, "").split("/");
  barraCapitoli.querySelectorAll(".cap").forEach((voce) => {
    if (nome === "capitolo" && voce.dataset.capitolo === String(Number(valore))) {
      voce.setAttribute("aria-current", "page");
      const gruppo = voce.closest("details");
      if (gruppo) gruppo.open = true;
    } else voce.removeAttribute("aria-current");
  });
}

async function aggiornaStato() {
  clearTimeout(timerStato);
  let prossimo = 15000;
  try {
    const dati = await api("/stato");
    disegnaBarra(dati);
    const { in_attesa: attesa, in_corso: corso, errori, lavori } = dati.coda;
    const daLeggere = attesa + (corso ? 1 : 0);
    if (daLeggere && !daLeggerePrima) ricordiPrima = ricordiNoti ?? dati.ricordi;
    if (!daLeggere && daLeggerePrima) {
      window.dispatchEvent(new CustomEvent("archivista-finito", {
        detail: { nuovi: Math.max(dati.ricordi - ricordiPrima, 0) },
      }));
    }
    daLeggerePrima = daLeggere;
    ricordiNoti = dati.ricordi;
    const frasi = [];
    if (daLeggere) frasi.push(`L'archivista sta leggendo ${plurale(daLeggere, "testo", "testi")}.`);
    if (lavori.length) frasi.push(`Lo scrittore ha ${plurale(lavori.length, "capitolo", "capitoli")} da scrivere.`);
    statoBarra.classList.toggle("con-errore", errori.length > 0 && !frasi.length);
    statoBarra.classList.toggle("al-lavoro", frasi.length > 0);
    if (frasi.length) {
      statoBarra.textContent = frasi.join(" ");
      prossimo = 3000;
    } else if (errori.length) {
      statoBarra.replaceChildren(
        `L'archivista non ha letto ${plurale(errori.length, "testo", "testi")}. ${errori[0].messaggio} `,
        el("button", {
          classe: "testuale", type: "button",
          onclick: async () => { await api("/coda/riprova", {}); aggiornaStato(); },
        }, "Riprova"));
    } else {
      statoBarra.textContent = "Tutto salvato.";
    }
  } catch (errore) {
    statoBarra.textContent = errore.message;
    statoBarra.classList.add("con-errore");
    statoBarra.classList.remove("al-lavoro");
  }
  timerStato = setTimeout(aggiornaStato, prossimo);
}

// Percorsi --------------------------------------------------------------------

function vai() {
  turno += 1;
  fineTurno.abort();
  fineTurno = new AbortController();
  clearTimeout(timerBozza);
  const percorso = location.hash.replace(/^#/, "") || "scrivo";
  const [nome, valore] = percorso.split("/");
  document.querySelectorAll("nav a").forEach((link) => {
    if (link.dataset.pagina === nome) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  segnaBarraAttiva();
  if (nome === "domande") {
    paginaDomande(riprendeDopoPausa);
    riprendeDopoPausa = false;
  } else if (nome === "chat") paginaChat();
  else if (nome === "libro") paginaLibro();
  else if (nome === "capitolo") paginaCapitolo(Number(valore));
  else if (nome === "anteprima") {
    paginaAnteprima({ el, api, mostra, aggiornaStato, turnoCorrente: () => turno });
  } else paginaScrivo();
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", vai);
vai();
aggiornaStato();

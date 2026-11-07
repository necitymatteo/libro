// Il libro come esce. Il testo scorre in colonne alte e larghe come il blocco di testo:
// ogni colonna e' una pagina. Numeri di pagina, testatine e indice vengono dalle
// posizioni misurate nel browser, non da una stima.

const MM = 96 / 25.4;
const PT = 96 / 72;
const INTERVALLO = 48;
const LETTERE = [
  "", "Uno", "Due", "Tre", "Quattro", "Cinque", "Sei", "Sette", "Otto", "Nove", "Dieci",
  "Undici", "Dodici", "Tredici", "Quattordici", "Quindici", "Sedici", "Diciassette",
  "Diciotto", "Diciannove", "Venti", "Ventuno", "Ventidue", "Ventitré", "Ventiquattro",
  "Venticinque", "Ventisei", "Ventisette", "Ventotto", "Ventinove", "Trenta",
];
const NOMI_COMPOSIZIONE = {
  classica: "Classica",
  grande: "Titolo enorme",
  basso: "Titolo in basso",
  fascia: "Fascia",
};

function misure(design, catalogo) {
  const formato = catalogo.formati[design.formato];
  const larghezza = Math.round(formato.larghezza * MM);
  const altezza = Math.round(formato.altezza * MM);
  const corpo = design.corpo_pt * PT;
  const riga = Math.round(corpo * design.interlinea);
  const interno = Math.round(design.margine_interno_mm * MM);
  const esterno = Math.round(design.margine_esterno_mm * MM);
  const sopra = Math.round(design.margine_sopra_mm * MM);
  const sotto = Math.round(design.margine_sotto_mm * MM);
  const righe = Math.floor((altezza - sopra - sotto) / riga);
  const titolo = design.titolo_capitolo_pt * PT;
  return {
    larghezza, altezza, corpo, riga, interno, esterno, sopra, sotto, righe, titolo,
    testoL: larghezza - interno - esterno,
    testoA: righe * riga,
    rigaTitolo: Math.ceil((titolo * 1.14) / riga) * riga,
    titoloSotto: titolo * 0.62,
    rigaSotto: Math.ceil((titolo * 0.62 * 1.14) / riga) * riga,
    discesa: Math.min(Math.round((design.discesa_capitolo_mm * MM) / riga), Math.floor(righe * 0.55)) * riga,
    passo: larghezza - interno - esterno + INTERVALLO,
  };
}

function famiglia(nome, catalogo) {
  return `"${nome}", ${catalogo.font_titoli[nome] || "serif"}`;
}

function applicaVariabili(radice, design, m, catalogo) {
  const px = (n) => `${n}px`;
  const valori = {
    "--l-larghezza": px(m.larghezza),
    "--l-altezza": px(m.altezza),
    "--l-carta": design.colore_carta,
    "--l-inchiostro": design.colore_inchiostro,
    "--l-accento": design.colore_accento,
    "--l-font-testo": famiglia(design.font_testo, catalogo),
    "--l-font-titoli": famiglia(design.font_titoli, catalogo),
    "--l-corpo": px(m.corpo),
    "--l-riga": px(m.riga),
    "--l-testo-l": px(m.testoL),
    "--l-testo-a": px(m.testoA),
    "--l-interno": px(m.interno),
    "--l-esterno": px(m.esterno),
    "--l-sopra": px(m.sopra),
    "--l-sotto": px(m.sotto),
    "--l-discesa": px(design.apertura_capitolo === "destra" ? m.discesa : m.riga * 3),
    "--l-titolo": px(m.titolo),
    "--l-riga-titolo": px(m.rigaTitolo),
    "--l-titolo-sotto": px(m.titoloSotto),
    "--l-riga-sotto": px(m.rigaSotto),
    "--l-titolo-allinea": design.titolo_capitolo_allineamento === "centro" ? "center" : "left",
    "--l-allinea": design.allineamento === "giustificato" ? "justify" : "left",
    "--l-sillaba": design.sillabazione ? "auto" : "manual",
    "--l-gap": px(INTERVALLO),
    "--c-sfondo": design.copertina_sfondo,
    "--c-testo": design.copertina_testo,
    "--c-accento": design.copertina_accento,
    "--c-font": famiglia(design.copertina_font, catalogo),
  };
  for (const [nome, valore] of Object.entries(valori)) radice.style.setProperty(nome, valore);
  radice.classList.toggle("con-capolettera", design.capolettera);
  radice.classList.toggle("par-spazio", design.paragrafi === "spazio");
  radice.classList.toggle("apertura-continua", design.apertura_capitolo === "continua");
  radice.classList.toggle("folio-centro", design.numeri_pagina === "centro");
}

function etichettaCapitolo(id, design) {
  if (design.numero_capitolo === "cifra") return String(id);
  if (design.numero_capitolo === "lettere") return LETTERE[id] || String(id);
  if (design.numero_capitolo === "capitolo") return `Capitolo ${id}`;
  return null;
}

function testaCapitolo(capitolo, design, el) {
  const numero = etichettaCapitolo(capitolo.numero, design);
  return el("header", { classe: "l-testa" },
    numero ? el("p", { classe: "l-numero" }, numero) : null,
    el("h2", { classe: "l-titolo" }, capitolo.titolo),
    design.ornamento === "filetto" ? el("div", { classe: "l-filetto" }) : null);
}

function paragrafiSotto(sotto, primoDelCapitolo, el) {
  return sotto.paragrafi.map((testo, i) => {
    let classe = "l-par";
    if (i === 0) classe += " l-primo";
    if (i === 0 && primoDelCapitolo) classe += " l-capolettera";
    return el("p", { classe }, testo);
  });
}

function creaFlusso(dati, design, el) {
  const flusso = el("div", { classe: "flusso", lang: "it" });
  const testate = new Map();
  const testateSotto = new Map();
  flusso.append(
    el("section", { classe: "l-frontespizio" },
      el("p", { classe: "l-f-titolo" }, dati.titolo),
      dati.autore ? el("p", { classe: "l-f-autore" }, dati.autore) : null),
    el("section", { classe: "l-colofon" }, el("p", {}, "Bozza privata.")),
    el("section", { classe: "l-indice", "data-indice": "1" },
      el("h2", { classe: "l-indice-titolo" }, "Indice"),
      dati.parti.map((parte) => [
        el("p", { classe: "l-indice-voce l-indice-parte" },
          el("span", {}, `${parte.numero}. ${parte.titolo}`),
          el("span", { classe: "l-indice-num", "data-parte": parte.id }, "0")),
        parte.sotto.map((sotto) => el("p", { classe: "l-indice-voce l-indice-sotto" },
          el("span", {}, sotto.titolo),
          el("span", { classe: "l-indice-num", "data-sotto": String(sotto.id) }, "0"))),
      ])),
  );
  dati.parti.forEach((parte) => {
    const testa = testaCapitolo(parte, design, el);
    testate.set(parte.id, testa);
    flusso.append(el("section", { classe: "l-capitolo", "data-capitolo": parte.id },
      testa,
      parte.sotto.map((sotto, posizione) => {
        const titolo = el("h3", { classe: "l-sotto" }, sotto.titolo);
        testateSotto.set(sotto.id, titolo);
        return [titolo, paragrafiSotto(sotto, posizione === 0, el)];
      })));
  });
  return { flusso, testate, testateSotto };
}

// Misura dove cade ogni cosa. Va chiamata con il flusso gia' nella pagina.
function misuraPagine(libro, dati, design, el) {
  const { flusso, testate, testateSotto, m } = libro;
  const paginaDi = (nodo) => {
    const rettangolo = nodo.getClientRects()[0];
    return Math.floor((rettangolo.left - flusso.getBoundingClientRect().left + 1) / m.passo) + 1;
  };

  if (design.apertura_capitolo === "destra") {
    dati.parti.forEach((capitolo) => {
      const testa = testate.get(capitolo.id);
      if (paginaDi(testa) % 2 === 0) {
        testa.parentNode.before(el("div", { classe: "l-vuota" }));
      }
    });
  }

  const vuote = new Set([...flusso.querySelectorAll(".l-vuota")].map(paginaDi));
  const aperture = new Map();
  dati.parti.forEach((capitolo) => aperture.set(paginaDi(testate.get(capitolo.id)), capitolo));
  const pagineSotto = new Map();
  testateSotto.forEach((nodo, id) => pagineSotto.set(id, paginaDi(nodo)));
  flusso.querySelectorAll(".l-indice-num").forEach((nodo) => {
    if (nodo.dataset.parte) nodo.textContent = String(paginaDi(testate.get(nodo.dataset.parte)));
    else nodo.textContent = String(pagineSotto.get(Number(nodo.dataset.sotto)));
  });

  const ultimo = flusso.lastElementChild.getClientRects();
  const totale = Math.floor(
    (ultimo[ultimo.length - 1].left - flusso.getBoundingClientRect().left + 1) / m.passo) + 1;
  const primaApertura = aperture.size ? Math.min(...aperture.keys()) : totale + 1;

  const capitoloDi = (pagina) => {
    let corrente = null;
    for (const [inizio, capitolo] of aperture) {
      if (inizio <= pagina) corrente = capitolo;
    }
    return corrente;
  };
  return { totale, vuote, aperture, pagineSotto, primaApertura, capitoloDi };
}

function creaCopertina(dati, design, el) {
  return el("div", { classe: `copertina comp-${design.copertina_composizione}` },
    el("div", { classe: "cop-riquadro" },
      el("p", { classe: "cop-titolo" }, dati.titolo),
      design.copertina_composizione === "classica" ? el("div", { classe: "cop-filetto" }) : null),
    dati.autore ? el("p", { classe: "cop-autore" }, dati.autore) : null);
}

function creaVisore(libro, dati, design, el, alCambio) {
  const { m, flusso, pagine, radice } = libro;

  function creaLato(lato) {
    const copia = flusso.cloneNode(true);
    const testo = el("div", { classe: "pagina-testo" }, copia);
    const testatina = el("p", { classe: "l-testatina" });
    const folio = el("p", { classe: "l-folio" });
    const nodo = el("div", { classe: `pagina-libro ${lato}` }, testatina, testo, folio);
    return { nodo, copia, testo, testatina, folio };
  }

  const verso = creaLato("verso");
  const recto = creaLato("recto");
  const copertina = creaCopertina(dati, design, el);
  const fogli = el("div", { classe: "fogli" }, verso.nodo, recto.nodo, copertina);
  const banco = el("div", { classe: "banco" }, fogli);
  radice.append(banco);

  const ultimaApertura = Math.ceil((pagine.totale + 1) / 2) + 1 - 1;
  let apertura = 0;

  function riempi(lato, numero) {
    if (!numero || numero > pagine.totale) {
      lato.nodo.classList.add("assente");
      return;
    }
    lato.nodo.classList.remove("assente");
    lato.copia.style.transform = `translateX(${-(numero - 1) * m.passo}px)`;
    const vuota = pagine.vuote.has(numero);
    lato.testo.hidden = vuota;
    const davanti = numero < pagine.primaApertura;
    const inApertura = pagine.aperture.has(numero);
    lato.folio.textContent = davanti || vuota ? "" : String(numero);
    let testa = "";
    if (!davanti && !vuota && !inApertura) {
      const capitolo = pagine.capitoloDi(numero);
      if (design.testatine === "capitolo" && capitolo) testa = capitolo.titolo;
      if (design.testatine === "libro_capitolo") {
        testa = numero % 2 === 0 ? dati.titolo : (capitolo ? capitolo.titolo : "");
      }
    }
    lato.testatina.textContent = testa;
  }

  function pagineVisibili() {
    if (apertura === 0) return [];
    if (apertura === 1) return [1];
    return [2 * apertura - 2, 2 * apertura - 1].filter((n) => n <= pagine.totale);
  }

  function disegna() {
    copertina.hidden = apertura !== 0;
    if (apertura === 0) {
      riempi(verso, null);
      riempi(recto, null);
    } else if (apertura === 1) {
      riempi(verso, null);
      riempi(recto, 1);
    } else {
      riempi(verso, 2 * apertura - 2);
      riempi(recto, 2 * apertura - 1);
    }
    alCambio({ apertura, ultimaApertura, pagine: pagineVisibili(), totale: pagine.totale });
  }

  function adatta() {
    const disponibile = banco.clientWidth;
    const scala = Math.min(
      (disponibile - 48) / (m.larghezza * 2),
      Math.max(window.innerHeight - 178, 320) / m.altezza,
      1.25,
    );
    fogli.style.transform = `scale(${scala})`;
    fogli.style.left = `${Math.max((disponibile - m.larghezza * 2 * scala) / 2, 0)}px`;
    fogli.style.top = "24px";
    banco.style.height = `${m.altezza * scala + 48}px`;
  }

  verso.nodo.addEventListener("click", () => vai(apertura - 1));
  recto.nodo.addEventListener("click", () => vai(apertura + 1));
  copertina.addEventListener("click", () => vai(apertura + 1));

  function vai(nuova) {
    apertura = Math.min(Math.max(nuova, 0), ultimaApertura);
    disegna();
  }

  function vaiAPagina(numero) {
    vai(numero === 1 ? 1 : Math.floor(numero / 2) + 1);
  }

  const osservatore = new ResizeObserver(adatta);
  osservatore.observe(banco);
  adatta();

  return {
    vai,
    vaiAPagina,
    avanti: () => vai(apertura + 1),
    indietro: () => vai(apertura - 1),
    apertura: () => apertura,
    pagina: () => pagineVisibili()[0] || 0,
    chiudi: () => osservatore.disconnect(),
  };
}

function creaMini(design, dati, catalogo, el) {
  const m = misure(design, catalogo);
  const radice = el("div", { classe: "libro-radice mini-radice" });
  applicaVariabili(radice, design, m, catalogo);
  const scala = 132 / m.larghezza;
  const capitolo = dati.parti[0] || { numero: 1, titolo: "Capitolo", sotto: [] };
  const sotto = capitolo.sotto[0];
  const interno = el("div", { classe: "flusso flusso-mini", lang: "it" },
    el("section", { classe: "l-capitolo" },
      testaCapitolo(capitolo, design, el),
      sotto ? [
        el("h3", { classe: "l-sotto" }, sotto.titolo),
        paragrafiSotto({ paragrafi: sotto.paragrafi.slice(0, 3) }, true, el),
      ] : null));
  const incornicia = (figlio) => {
    const scatola = el("div", { classe: "mini-scatola" }, figlio);
    scatola.style.width = `${m.larghezza * scala}px`;
    scatola.style.height = `${m.altezza * scala}px`;
    figlio.style.transform = `scale(${scala})`;
    return scatola;
  };
  const pagina = el("div", { classe: "pagina-libro recto mini-pagina" }, el("div", { classe: "pagina-testo" }, interno));
  radice.append(incornicia(creaCopertina(dati, design, el)), incornicia(pagina));
  return radice;
}

function selezione(etichetta, valori, attuale, alCambio, el) {
  const nodo = el("select", { "aria-label": etichetta },
    valori.map(([valore, testo]) => el("option", { value: String(valore), selected: String(valore) === String(attuale) }, testo)));
  nodo.addEventListener("change", () => alCambio(nodo.value));
  return el("label", { classe: "comando" }, el("span", {}, etichetta), nodo);
}

// La pagina ----------------------------------------------------------------------

export async function paginaAnteprima({ el, api, mostra, aggiornaStato, turnoCorrente }) {
  const mio = turnoCorrente();
  let visore = null;
  let paginaAttuale = 0;
  let attesaBozze = null;

  const abbandonata = () => mio !== turnoCorrente();

  function largo(...contenuto) {
    return el("div", { classe: "contenuto largo" }, ...contenuto);
  }

  async function ricarica() {
    let dati;
    try {
      dati = await api("/anteprima");
    } catch (errore) {
      if (!abbandonata()) mostra(largo(el("p", { classe: "errore" }, errore.message)));
      return;
    }
    if (!abbandonata()) disegna(dati);
  }

  async function cambiaDesign(design, etichetta) {
    const esito = await api("/design", { design, etichetta });
    await ricarica();
    return esito;
  }

  function disegna(dati) {
    const scorrimento = window.scrollY;
    if (visore) {
      paginaAttuale = visore.apertura() === 0 ? 0 : visore.pagina();
      visore.chiudi();
    }
    const { design, catalogo } = dati;
    const m = misure(design, catalogo);
    const radice = el("div", { classe: "libro-radice" });
    applicaVariabili(radice, design, m, catalogo);
    const { flusso, testate, testateSotto } = creaFlusso(dati, design, el);
    const nascosto = el("div", { classe: "libro-nascosto", "aria-hidden": "true" }, flusso);
    radice.append(nascosto);

    const dove = el("span", { classe: "dove", "aria-live": "polite" });
    const indietro = el("button", { classe: "secondario", type: "button", onclick: () => visore.indietro() }, "Indietro");
    const avanti = el("button", { classe: "secondario", type: "button", onclick: () => visore.avanti() }, "Avanti");
    const vaiA = el("select", { "aria-label": "Vai a un punto del libro" });
    const barra = el("div", { classe: "azioni barra-libro" }, indietro, avanti, dove, vaiA);

    const risposta = el("p", { classe: "aiuto", "aria-live": "polite" },
      "Scrivi in parole normali cosa vuoi cambiare. Il testo del libro non cambia.");
    const richiesta = el("textarea", {
      "aria-label": "Modifica di design da chiedere",
      placeholder: "Il testo è troppo piccolo. Vorrei una copertina più scura. I titoli più sobri.",
    });
    richiesta.rows = 2;
    const applica = el("button", { classe: "primario", type: "button" }, "Applica la modifica");
    applica.addEventListener("click", async () => {
      if (!richiesta.value.trim()) {
        risposta.textContent = "Scrivi prima cosa vuoi cambiare.";
        return;
      }
      applica.disabled = true;
      risposta.textContent = "Il designer sta lavorando. Di solito ci vuole meno di un minuto.";
      try {
        const esito = await api("/design/modifica", { testo: richiesta.value });
        await ricarica();
        // Il nuovo disegno ha sostituito la pagina: il messaggio va nel nuovo riquadro.
        const nuovo = document.getElementById("risposta-designer");
        if (nuovo) {
          nuovo.textContent = [
            esito.cambiato ? esito.spiegazione : "Non ho cambiato niente.",
            esito.non_possibile,
            ...esito.avvisi,
          ].filter(Boolean).join(" ");
        }
      } catch (errore) {
        risposta.textContent = errore.message;
        applica.disabled = false;
      }
    });
    risposta.id = "risposta-designer";

    const versioni = dati.versioni_design;
    const selettoreVersione = versioni.length > 1
      ? selezione("Versione del design", [...versioni].reverse().map((v) =>
          [v.versione, `${v.versione}. ${v.etichetta}`]), dati.versione_design, async (valore) => {
            if (Number(valore) !== dati.versione_design) {
              await api("/design/torna", { versione: Number(valore) });
              await ricarica();
            }
          }, el)
      : null;

    const cambia = (chiave, etichetta) => (valore) => {
      const convertito = chiave === "corpo_pt" ? Number(valore) : valore;
      cambiaDesign({ ...design, [chiave]: convertito }, etichetta(valore));
    };
    const corpi = [];
    for (let c = 9; c <= 14; c += 0.5) corpi.push([c, `${c} punti`]);
    const elencoFont = (font) => Object.keys(font).map((nome) => [nome, nome]);

    const titolo = el("input", { type: "text", value: dati.titolo, "aria-label": "Titolo del libro" });
    const autore = el("input", { type: "text", value: dati.autore, placeholder: "Il nome in copertina", "aria-label": "Nome in copertina" });
    const salvaDati = async () => {
      if (titolo.value.trim() === dati.titolo && autore.value.trim() === dati.autore) return;
      if (!titolo.value.trim()) {
        titolo.value = dati.titolo;
        return;
      }
      await api("/libro/dati", { titolo: titolo.value, autore: autore.value });
      aggiornaStato();
      await ricarica();
    };
    titolo.addEventListener("change", salvaDati);
    autore.addEventListener("change", salvaDati);

    const comandi = el("div", { classe: "comandi" },
      el("label", { classe: "comando" }, el("span", {}, "Titolo"), titolo),
      el("label", { classe: "comando" }, el("span", {}, "Nome in copertina"), autore),
      selezione("Formato", Object.entries(catalogo.formati).map(([k, f]) => [k, f.nome]), design.formato,
        cambia("formato", (v) => catalogo.formati[v].nome), el),
      selezione("Font del testo", elencoFont(catalogo.font_testo), design.font_testo,
        cambia("font_testo", (v) => `Testo in ${v}`), el),
      selezione("Font dei titoli", elencoFont(catalogo.font_titoli), design.font_titoli,
        cambia("font_titoli", (v) => `Titoli in ${v}`), el),
      selezione("Corpo del testo", corpi, design.corpo_pt,
        cambia("corpo_pt", (v) => `Corpo ${v} punti`), el),
      selezione("Copertina", catalogo.composizioni.map((c) => [c, NOMI_COMPOSIZIONE[c] || c]), design.copertina_composizione,
        cambia("copertina_composizione", (v) => `Copertina: ${NOMI_COMPOSIZIONE[v] || v}`), el),
      selettoreVersione);

    const avvisoProposte = el("p", { classe: "aiuto", "aria-live": "polite" },
      "Il designer legge il libro e propone 3 design nuovi. Il libro cambia solo quando ne scegli uno.");
    const proponi = el("button", { classe: "primario", type: "button" }, "Proponi 3 nuovi design");
    proponi.addEventListener("click", async () => {
      proponi.disabled = true;
      avvisoProposte.textContent = "Il designer sta leggendo il libro. Di solito ci vuole meno di un minuto.";
      try {
        await api("/design/proposte", {});
        await ricarica();
      } catch (errore) {
        avvisoProposte.textContent = errore.message;
        proponi.disabled = false;
      }
    });

    const galleria = [...dati.proposte, ...dati.predefiniti].map((voce) => {
      const attuale = voce.nome === design.nome;
      return el("article", { classe: `design-voce${attuale ? " attuale" : ""}` },
        creaMini(voce, dati, catalogo, el),
        el("h3", {}, voce.nome),
        el("p", { classe: "aiuto" }, voce.motivo),
        el("button", {
          classe: "testuale", type: "button",
          onclick: () => cambiaDesign(voce, `Design ${voce.nome}`),
        }, attuale ? "Rimetti questo design" : "Usa questo design"));
    });

    const scrivibili = dati.mancanti.filter((c) => c.scrivibile);
    const inScrittura = dati.mancanti.filter((c) => c.lavoro && ["in_attesa", "in_corso"].includes(c.lavoro.stato));
    const erroreBozze = dati.mancanti.find((c) => c.lavoro && c.lavoro.stato === "errore");
    const daVerificare = dati.capitoli.filter((c) => c.da_verificare);
    const daRiscrivere = dati.capitoli.filter((c) => c.da_riscrivere);
    const scriviTutte = el("button", {
      classe: "primario", type: "button", disabled: inScrittura.length > 0,
      onclick: async () => {
        await api("/bozze/mancanti", {});
        aggiornaStato();
        ricarica();
      },
    }, "Scrivi le bozze mancanti");

    const noteTesto = [];
    if (inScrittura.length) {
      noteTesto.push(el("p", { classe: "riassunto" },
        inScrittura.length === 1
          ? "Lo scrittore sta scrivendo l'ultimo sottocapitolo. Il libro si aggiorna da solo."
          : `Lo scrittore sta scrivendo ${inScrittura.length} sottocapitoli, uno alla volta. Il libro si aggiorna da solo.`));
    } else if (scrivibili.length) {
      noteTesto.push(el("p", { classe: "riassunto" },
        scrivibili.length === 1
          ? "1 sottocapitolo ha i ricordi per una bozza, ma non è ancora scritto."
          : `${scrivibili.length} sottocapitoli hanno i ricordi per una bozza, ma non sono ancora scritti.`),
        el("div", { classe: "azioni" }, scriviTutte));
    }
    if (erroreBozze) noteTesto.push(el("p", { classe: "errore" }, erroreBozze.lavoro.messaggio));
    const legami = (capitoli, conta) => el("ul", { classe: "elenco-lato" }, capitoli.map((c) =>
      el("li", {}, el("a", { href: `#capitolo/${c.id}` }, c.titolo), `: ${conta(c)}`)));
    const fuori = dati.mancanti.filter((c) => !c.scrivibile);
    if (fuori.length) {
      noteTesto.push(el("h2", {}, "Fuori dal libro per ora"),
        el("p", { classe: "aiuto" }, "Servono almeno 3 ricordi per scrivere un sottocapitolo. Rispondi alle domande per aggiungerne."),
        legami(fuori, (c) => (c.ricordi === 1 ? "1 ricordo per il libro" : `${c.ricordi} ricordi per il libro`)));
    }
    if (daRiscrivere.length) {
      noteTesto.push(el("h2", {}, "Da riscrivere"),
        el("p", { classe: "aiuto" }, "Questi sottocapitoli usano ricordi o nomi che hai cambiato dopo: riscrivile prima di mostrarle a qualcuno."),
        legami(daRiscrivere, (c) => (c.da_riscrivere === 1 ? "1 frase" : `${c.da_riscrivere} frasi`)));
    }
    if (daVerificare.length) {
      noteTesto.push(el("h2", {}, "Frasi da verificare"),
        el("p", { classe: "aiuto" }, "L'anteprima le mostra pulite. Le trovi sottolineate nel sottocapitolo."),
        legami(daVerificare, (c) => (c.da_verificare === 1 ? "1 frase" : `${c.da_verificare} frasi`)));
    }

    mostra(largo(
      el("h1", { classe: "solo-lettori" }, "Anteprima del libro"),
      radice,
      barra,
      el("div", { classe: "pannelli" },
        el("section", {},
          el("h2", {}, "Chiedi una modifica"),
          el("div", { classe: "editor editor-compatto" }, richiesta,
            el("div", { classe: "editor-piede" }, el("div", { classe: "editor-azioni" }, applica))),
          risposta),
        el("section", {},
          el("h2", {}, "Scegli tu"),
          comandi)),
      noteTesto.length ? el("section", { classe: "sezione note-testo" }, noteTesto) : null,
      el("section", { classe: "sezione" },
        el("h2", {}, "Altri design"),
        avvisoProposte,
        el("div", { classe: "azioni" }, proponi),
        el("div", { classe: "galleria" }, galleria)),
    ));

    const libro = { flusso, testate, testateSotto, m, radice };
    libro.pagine = misuraPagine(libro, dati, design, el);

    const opzioni = [["copertina", "Copertina"], ["p3", "Indice"]];
    dati.parti.forEach((capitolo) => {
      const [inizio] = [...libro.pagine.aperture].find(([, c]) => c.id === capitolo.id);
      opzioni.push([`p${inizio}`, `${capitolo.numero}. ${capitolo.titolo}`]);
      capitolo.sotto.forEach((sotto) => {
        opzioni.push([`p${libro.pagine.pagineSotto.get(sotto.id)}`, `\u00A0\u00A0\u00A0${sotto.titolo}`]);
      });
    });
    vaiA.replaceChildren(...opzioni.map(([valore, testo]) => el("option", { value: valore }, testo)));
    vaiA.addEventListener("change", () => {
      if (vaiA.value === "copertina") visore.vai(0);
      else visore.vaiAPagina(Number(vaiA.value.slice(1)));
    });

    visore = creaVisore(libro, dati, design, el, ({ apertura, ultimaApertura, pagine, totale }) => {
      indietro.disabled = apertura === 0;
      avanti.disabled = apertura === ultimaApertura;
      if (apertura === 0) dove.textContent = `Copertina. Il libro ha ${totale} pagine.`;
      else if (pagine.length === 1) dove.textContent = `Pagina ${pagine[0]} di ${totale}`;
      else dove.textContent = `Pagine ${pagine[0]} e ${pagine[1]} di ${totale}`;
    });
    if (paginaAttuale) visore.vaiAPagina(Math.min(paginaAttuale, libro.pagine.totale));
    else visore.vai(0);
    window.scrollTo(0, scorrimento);

    clearTimeout(attesaBozze);
    if (inScrittura.length) {
      const scritti = dati.capitoli.length;
      attesaBozze = setTimeout(async function controlla() {
        if (abbandonata()) return;
        const nuovi = await api("/anteprima").catch(() => null);
        if (abbandonata() || !nuovi) return;
        const attivi = nuovi.mancanti.some((c) => c.lavoro && ["in_attesa", "in_corso"].includes(c.lavoro.stato));
        if (nuovi.capitoli.length !== scritti || !attivi) disegna(nuovi);
        else attesaBozze = setTimeout(controlla, 6000);
      }, 6000);
    }
  }

  document.addEventListener("keydown", function freccia(evento) {
    if (abbandonata()) {
      document.removeEventListener("keydown", freccia);
      return;
    }
    if (!visore || /^(TEXTAREA|INPUT|SELECT)$/.test(document.activeElement?.tagName || "")) return;
    if (evento.key === "ArrowRight") visore.avanti();
    if (evento.key === "ArrowLeft") visore.indietro();
  });

  mostra(largo(el("p", { classe: "aiuto" }, "Sto impaginando il libro.")));
  await ricarica();
}

// Prima parte: Claude scollegato su ogni pagina, testo lungo, Cmd+Invio, testo a meta'.
const esiti = [];
const ok = (nome, condizione, dettaglio = "") => { esiti.push(`${condizione ? "OK " : "NO "} ${nome}${dettaglio !== "" ? ` | ${dettaglio}` : ""}`); return condizione; };
const dorme = (ms) => new Promise((r) => setTimeout(r, ms));
const aspetta = async (condizione, ms, nome) => {
  const inizio = Date.now();
  while (Date.now() - inizio < ms) {
    const valore = await condizione();
    if (valore) return valore;
    await dorme(250);
  }
  esiti.push(`NO  tempo scaduto: ${nome}`);
  return null;
};
const trova = (testo) => [...document.querySelectorAll("button, a")].find((n) => n.textContent.trim() === testo);
const scrivi = (area, testo) => { area.value = testo; area.dispatchEvent(new Event("input", { bubbles: true })); };
const get = (p) => fetch(`/api${p}`).then((r) => r.json());
const vai = async (hash) => { location.hash = hash; await dorme(500); };

try {
  // Salta la domanda gia' pronta dei dati di prova, cosi' la prossima deve chiamare Claude.
  const aperta = (await fetch("/api/domande/prossima", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).then((r) => r.json()));
  await fetch(`/api/domande/${aperta.id}/salta`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });

  // Testo lungo incollato e Cmd+Invio
  await vai("#scrivo");
  const paragrafo = "Sono cresciuto in una piccola città di mare e ogni estate lavoravo al porto. Il cuoco della mensa mi insegnava a pulire il pesce e mi raccontava i suoi viaggi. ";
  const lungo = Array.from({ length: 12 }, (_, i) => `${i + 1}. ${paragrafo.repeat(4)}`).join("\n\n");
  const area = document.querySelector("textarea");
  scrivi(area, lungo);
  ok("incolla: l'area cresce", area.offsetHeight > 400, area.offsetHeight);
  const prima = (await get("/archivio")).length;
  area.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", metaKey: true, bubbles: true, cancelable: true }));
  await aspetta(async () => (await get("/archivio")).length === prima + 1, 4000, "Cmd+Invio salva");
  const voci = await get("/archivio");
  ok("incolla: una voce sola, identica", voci.length === prima + 1 && voci[0].testo === lungo, `${lungo.length} caratteri`);
  ok("invio normale: va a capo e non salva", (() => {
    const a = document.querySelector("textarea");
    const e = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    a.dispatchEvent(e);
    return !e.defaultPrevented;
  })());

  // Claude scollegato: l'archivista
  await aspetta(async () => (await get("/stato")).coda.errori.length > 0, 20000, "errore archivista");
  await dorme(3500);
  const stato = document.getElementById("stato");
  await aspetta(() => /non ha letto/.test(stato.textContent), 18000, "errore nella barra");
  ok("scollegato: la barra lo dice", /claude auth login/.test(stato.textContent), stato.textContent);
  ok("scollegato: bottone Riprova", Boolean(stato.querySelector("button")));
  ok("scollegato: il testo è salvato", (await get("/archivio"))[0].testo === lungo);
  await vai("#libro"); await vai("#scrivo");
  await aspetta(() => /L'archivista non è riuscito/.test(document.querySelector(".principale").textContent), 5000, "voce marcata");
  ok("scollegato: la voce lo dice", /L'archivista non è riuscito a leggerlo/.test(document.querySelector(".principale").textContent));

  // Claude scollegato: le domande
  await vai("#domande");
  await aspetta(() => document.querySelector(".errore"), 15000, "errore domande");
  ok("scollegato: domande", /claude auth login/.test(document.querySelector(".errore")?.textContent || ""), document.querySelector(".errore")?.textContent);
  ok("scollegato: domande, Riprova", Boolean(trova("Riprova")));

  // Claude scollegato: lo scrittore
  await vai("#capitolo/2");
  await aspetta(() => trova("Scrivi la bozza"), 4000, "bottone bozza");
  trova("Scrivi la bozza").click();
  await aspetta(() => document.querySelector(".principale .errore"), 15000, "errore scrittore");
  ok("scollegato: scrittore", /claude auth login/.test(document.querySelector(".principale .errore")?.textContent || ""), document.querySelector(".principale .errore")?.textContent);

  // Capitolo con pochi ricordi
  await vai("#capitolo/4");
  await aspetta(() => trova("Scrivi la bozza"), 4000, "capitolo 4");
  trova("Scrivi la bozza").click();
  await aspetta(() => document.querySelector(".principale .errore"), 6000, "pochi ricordi");
  ok("pochi ricordi: lo dice", /almeno 3/.test(document.querySelector(".principale .errore")?.textContent || ""), document.querySelector(".principale .errore")?.textContent);

  // Claude scollegato: il designer
  await vai("#anteprima");
  await aspetta(() => document.querySelector(".dove")?.textContent, 5000, "anteprima");
  document.querySelector("textarea[aria-label='Modifica di design da chiedere']").value = "Più grande";
  trova("Applica la modifica").click();
  await aspetta(() => /claude auth login/.test(document.getElementById("risposta-designer")?.textContent || ""), 15000, "errore designer");
  ok("scollegato: designer lo dice", /claude auth login/.test(document.getElementById("risposta-designer")?.textContent || ""));
  ok("scollegato: designer, si può riprovare", !trova("Applica la modifica").disabled);
  trova("Proponi 3 nuovi design").click();
  await aspetta(() => !trova("Proponi 3 nuovi design").disabled, 15000, "errore proposte");
  ok("scollegato: proposte, si può riprovare", !trova("Proponi 3 nuovi design").disabled);

  // Claude scollegato: la chat
  await vai("#chat");
  await aspetta(() => document.querySelector("textarea"), 3000, "chat");
  scrivi(document.querySelector("textarea"), "Dove sta andando il libro?");
  trova("Invia").click();
  await aspetta(() => document.querySelector(".messaggio-errore"), 15000, "errore chat");
  ok("scollegato: chat lo dice", /claude auth login/.test(document.querySelector(".messaggio-errore")?.textContent || ""));
  ok("scollegato: chat, il messaggio resta", /Dove sta andando/.test(document.querySelector(".messaggio-tu")?.textContent || ""));
  ok("scollegato: chat, Riprova", Boolean(trova("Riprova")));

  // Pagine che non esistono
  await vai("#capitolo/99");
  await aspetta(() => document.querySelector(".errore"), 4000, "capitolo inesistente");
  ok("sottocapitolo inesistente: lo dice", /non trovato/i.test(document.querySelector(".errore")?.textContent || ""), document.querySelector(".errore")?.textContent);

  // Testo a meta': lo controlla la seconda parte dopo aver ricaricato la pagina
  await vai("#scrivo");
  scrivi(document.querySelector("textarea"), "Testo lasciato a metà prima di ricaricare");
  await dorme(1300);
} catch (errore) {
  esiti.push(`NO  ECCEZIONE ${errore.name}: ${errore.message}`);
}
return JSON.stringify(esiti);

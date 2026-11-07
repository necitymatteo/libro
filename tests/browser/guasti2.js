// Seconda parte: la pagina ricaricata, poi l'app spenta e riaccesa mentre la pagina resta aperta.
const esiti = [];
const ok = (nome, condizione, dettaglio = "") => { esiti.push(`${condizione ? "OK " : "NO "} ${nome}${dettaglio !== "" ? ` | ${dettaglio}` : ""}`); return condizione; };
const dorme = (ms) => new Promise((r) => setTimeout(r, ms));
const aspetta = async (condizione, ms, nome) => {
  const inizio = Date.now();
  while (Date.now() - inizio < ms) {
    const valore = await condizione();
    if (valore) return valore;
    await dorme(300);
  }
  esiti.push(`NO  tempo scaduto: ${nome}`);
  return null;
};
const trova = (testo) => [...document.querySelectorAll("button, a")].find((n) => n.textContent.trim() === testo);
const stato = document.getElementById("stato");
try {
  await aspetta(() => document.querySelector("textarea")?.value, 3000, "testo a metà");
  ok("ricarica: il testo a metà è rimasto", document.querySelector("textarea").value === "Testo lasciato a metà prima di ricaricare");
  // Il comando fuori da qui spegne l'app.
  await aspetta(() => /non risponde/.test(stato.textContent), 40000, "app spenta");
  ok("spenta: la barra lo dice", /avvia\.command/.test(stato.textContent), stato.textContent);
  trova("Salva il testo").click();
  await aspetta(() => /non risponde/.test(document.querySelector(".principale").textContent), 4000, "salvataggio con app spenta");
  ok("spenta: salvare non perde il testo", document.querySelector("textarea").value.length > 0, document.querySelector("textarea").value.length);
  ok("spenta: il salvataggio lo dice", /non risponde/.test(document.querySelector(".principale").textContent));
  ok("spenta: si può riprovare", !trova("Salva il testo").disabled);
  // Il comando fuori da qui riaccende l'app, con Claude collegato.
  await aspetta(() => !/non risponde/.test(stato.textContent), 60000, "app riaccesa");
  ok("riaccesa: la barra torna da sola", !stato.classList.contains("con-errore") || /non ha letto/.test(stato.textContent), stato.textContent);
  await aspetta(async () => {
    const dati = await fetch("/api/stato").then((r) => r.json());
    return !dati.coda.in_attesa && !dati.coda.in_corso;
  }, 200000, "testi recuperati");
  const finale = await fetch("/api/stato").then((r) => r.json());
  ok("riaccesa: i testi in sospeso sono stati letti", finale.coda.errori.length === 0, `errori ${finale.coda.errori.length}, ricordi ${finale.ricordi}`);
  await aspetta(() => /Tutto salvato/.test(stato.textContent), 20000, "tutto salvato");
  ok("riaccesa: Tutto salvato", /Tutto salvato/.test(stato.textContent), stato.textContent);
} catch (errore) {
  esiti.push(`NO  ECCEZIONE ${errore.name}: ${errore.message}`);
}
return JSON.stringify(esiti);

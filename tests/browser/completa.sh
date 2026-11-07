#!/bin/zsh
# Prova ogni funzione dalla pagina, sul motore di Safari, con Claude reale e la persona inventata.
# Non tocca i dati veri. Chiama Claude con il tuo abbonamento: circa 5 minuti.
QUI="${0:A:h}"
TMP=$(mktemp -d)
cd "$QUI/../.." || exit 1
swiftc -O "$QUI/webkit.swift" -o "$TMP/webkit" || exit 1
export LIBRO_DATI="$TMP/dati" LIBRO_PORTA=8766
PYTHONPATH=. .venv/bin/python -m libro.importa tests/dati_finti --nota "Persona inventata." > /dev/null
PYTHONPATH=. .venv/bin/python -m libro.elabora
.venv/bin/python -m libro > "$TMP/server.log" 2>&1 &
SRV=$!
for i in {1..30}; do curl -fs -m 1 http://127.0.0.1:8766/api/salute >/dev/null && break; /bin/sleep 0.2; done
ATTESA_MAX=1500 "$TMP/webkit" "http://127.0.0.1:8766/" 1.5 "@$QUI/completa.js" - chiaro > "$TMP/esito.json" 2>&1
kill $SRV; wait $SRV 2>/dev/null
cat "$TMP/server.log"
.venv/bin/python - "$TMP/esito.json" <<'PY'
import json, sys
testo = open(sys.argv[1]).read().strip()
try:
    dati = json.loads(testo)
except Exception:
    print(testo[:3000])
    raise SystemExit(1)
print("tempi:", dati["tempo"])
falliti = [r for r in dati["esiti"] if r.startswith("NO")]
for riga in falliti:
    print(riga[:300])
print(f"TOTALE: {len(dati['esiti'])} controlli, {len(falliti)} falliti")
raise SystemExit(1 if falliti else 0)
PY
ESITO=$?
rm -rf "$TMP"
exit $ESITO

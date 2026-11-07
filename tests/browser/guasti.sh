#!/bin/zsh
# I casi brutti, sul motore di Safari: Claude scollegato, testo lungo, pagina ricaricata, app spenta.
# Non tocca i dati veri. Prima usa un Claude finto che dice "non collegato", poi quello vero.
QUI="${0:A:h}"
TMP=$(mktemp -d)
cd "$QUI/../.." || exit 1
swiftc -O "$QUI/webkit.swift" -o "$TMP/webkit" || exit 1
mkdir -p "$TMP/finto"
cat > "$TMP/finto/claude" <<'EOF'
#!/bin/sh
cat > /dev/null
echo '{"type":"result","subtype":"error","is_error":true,"result":"OAuth session expired. Please run /login"}'
exit 1
EOF
chmod +x "$TMP/finto/claude"
export LIBRO_DATI="$TMP/dati" LIBRO_PORTA=8768
PYTHONPATH=. .venv/bin/python scripts/dati_prova.py || exit 1
PATH="$TMP/finto:$PATH" .venv/bin/python -m libro > "$TMP/server.log" 2>&1 &
SRV=$!
for i in {1..30}; do curl -fs -m 1 http://127.0.0.1:8768/api/salute >/dev/null && break; /bin/sleep 0.2; done
ATTESA_MAX=200 "$TMP/webkit" "http://127.0.0.1:8768/" 1.5 "@$QUI/guasti1.js" - chiaro > "$TMP/g1.json" 2>&1
ATTESA_MAX=400 "$TMP/webkit" "http://127.0.0.1:8768/" 1.5 "@$QUI/guasti2.js" - chiaro > "$TMP/g2.json" 2>&1 &
PROVA=$!
/bin/sleep 8
kill $SRV; wait $SRV 2>/dev/null
/bin/sleep 25
.venv/bin/python -m libro >> "$TMP/server.log" 2>&1 &
SRV=$!
wait $PROVA
kill $SRV; wait $SRV 2>/dev/null
cat "$TMP/server.log"
.venv/bin/python - "$TMP/g1.json" "$TMP/g2.json" <<'PY'
import json, sys
tutti = []
for nome in sys.argv[1:]:
    testo = open(nome).read().strip()
    try:
        tutti += json.loads(testo)
    except Exception:
        tutti.append("NO  uscita non valida: " + testo[:600])
falliti = [r for r in tutti if r.startswith("NO")]
for riga in falliti:
    print(riga[:300])
print(f"TOTALE: {len(tutti)} controlli, {len(falliti)} falliti")
raise SystemExit(1 if falliti else 0)
PY
ESITO=$?
rm -rf "$TMP"
exit $ESITO

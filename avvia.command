#!/bin/zsh -l
# Apre l'app del libro in Safari. Doppio clic nel Finder, oppure dal Terminale.
# Per chiuderlo: Ctrl+C in questa finestra.
# LIBRO_BROWSER cambia browser, LIBRO_PAGINA sceglie la pagina (per esempio "#anteprima").
cd "${0:A:h}" || exit 1

PORTA="${LIBRO_PORTA:-8765}"
INDIRIZZO="http://127.0.0.1:${PORTA}"
BROWSER="${LIBRO_BROWSER:-Safari}"
PAGINA="${LIBRO_PAGINA:-}"

if curl -fs "${INDIRIZZO}/api/salute" >/dev/null 2>&1; then
  open -a "$BROWSER" "${INDIRIZZO}/${PAGINA}"
  echo "L'app e' gia' aperta: ${INDIRIZZO}"
  exit 0
fi

(
  for _ in {1..50}; do
    if curl -fs "${INDIRIZZO}/api/salute" >/dev/null 2>&1; then
      open -a "$BROWSER" "${INDIRIZZO}/${PAGINA}"
      exit 0
    fi
    sleep 0.2
  done
) &

echo "App aperta su ${INDIRIZZO}. Ctrl+C chiude."
exec .venv/bin/python -m libro

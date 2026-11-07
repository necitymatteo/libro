#!/bin/zsh
# Avvia l'app con la persona inventata di tests/dati_finti, mai con i dati veri.
cd "${0:A:h}/.." || exit 1
export LIBRO_DATI="${LIBRO_DATI:-$PWD/dati-prova}"
export LIBRO_PORTA="${LIBRO_PORTA:-8766}"
exec .venv/bin/python -m libro

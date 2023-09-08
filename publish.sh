#!/usr/bin/env bash

if [ $# -eq 0 ]; then
    >&2 echo "PyPi API token required"
    exit 1
fi

# https://github.com/python-poetry/poetry/issues/5285#issuecomment-1336177595
poetry publish -u __token__ -p $1 --build

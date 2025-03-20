#!/usr/bin/env bash

if [ $# -eq 0 ]; then
    >&2 echo "PyPi API token required"
    exit 1
fi

rm -rf ./dist
uv build
uv publish -t $1

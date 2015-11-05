#!/usr/bin/env bash

SOURCE="./affinity.md"
echo "Creating affinity.1 man page from $SOURCE"
pandoc -s -t man "${SOURCE}" -o affinity.1
echo "Creating affinity PDF documentation from $SOURCE"
pandoc "${SOURCE}" -o affinity.pdf

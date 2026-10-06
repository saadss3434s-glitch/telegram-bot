#!/bin/bash

set -e

echo "=== Starting GPU Bot ==="

nvidia-smi

python -m pip install --upgrade pip

pip install -r requirements.txt

python app.py

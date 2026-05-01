#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# Force playwright to install browsers in a local folder that Render can see
export PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright
python -m playwright install chromium

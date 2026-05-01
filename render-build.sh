#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python -m playwright install chromium
# Note: On Render, if you hit dependency issues, you may need to use a Dockerfile.

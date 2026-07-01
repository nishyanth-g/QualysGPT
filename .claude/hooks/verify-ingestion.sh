#!/bin/bash
CHANGED_FILE="$1"
if [[ "$CHANGED_FILE" == *"ingestion/"* ]]; then
  echo '=== Auto-verification triggered ==='
  cd "$(git rev-parse --show-toplevel)"
  source venv/Scripts/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
  python tests/test_retrieval.py
  EXIT_CODE=$?
  if [ $EXIT_CODE -ne 0 ]; then
    echo 'VERIFICATION FAILED — do not proceed until fixed'
    exit 1
  fi
  echo '=== Verification passed ==='
fi

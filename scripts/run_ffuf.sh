#!/usr/bin/env bash
#
# Jalankan ffuf secara lokal untuk testing sebelum di-push ke GitHub Actions.
#
# Penggunaan:
#   ./scripts/run_ffuf.sh https://target-anda.com
#
set -euo pipefail

TARGET="${1:-}"
WORDLIST="${2:-wordlists/common.txt}"

if [ -z "$TARGET" ]; then
  echo "Usage: $0 <target_url> [wordlist_path]"
  exit 1
fi

if ! command -v ffuf &> /dev/null; then
  echo "ffuf belum terinstall. Install dengan:"
  echo "  go install github.com/ffuf/ffuf/v2@latest"
  exit 1
fi

mkdir -p results

SAFE_NAME=$(echo "$TARGET" | sed -E 's~https?://~~; s~[^a-zA-Z0-9.-]~_~g')
OUTPUT_FILE="results/${SAFE_NAME}.json"

echo "[*] Scanning: $TARGET"
echo "[*] Wordlist: $WORDLIST"
echo "[*] Output  : $OUTPUT_FILE"

ffuf -u "${TARGET}/FUZZ" \
     -w "$WORDLIST" \
     -mc 200,301,302,403 \
     -o "$OUTPUT_FILE" \
     -of json \
     -rate 20 \
     -t 10 \
     -timeout 10

echo "[+] Selesai. Hasil disimpan di $OUTPUT_FILE"

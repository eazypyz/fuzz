#!/usr/bin/env python3
"""
Kirim ringkasan hasil ffuf scan ke Discord melalui webhook.

Webhook URL WAJIB diambil dari environment variable DISCORD_WEBHOOK,
JANGAN pernah di-hardcode di file ini karena akan ter-commit ke repo.

Set di GitHub: Settings > Secrets and variables > Actions > New repository secret
  Name  : DISCORD_WEBHOOK
  Value : (paste webhook URL Discord Anda)
"""

import json
import os
import sys

import requests

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK", "").strip()
SUMMARY_FILE = "summary.json"


def build_embed(summary):
    total = summary.get("total_findings", 0)
    timestamp = summary.get("timestamp", "unknown")
    findings = summary.get("findings", [])

    color = 0x2ECC71 if total == 0 else 0xE74C3C  # hijau jika kosong, merah jika ada temuan

    description_lines = []
    for f in findings[:10]:
        description_lines.append(
            f"`{f['status']}` **{f['target']}**/{f['input']} "
            f"(len={f['length']}, words={f['words']})"
        )

    if not description_lines:
        description_lines.append("Tidak ada temuan pada scan ini.")

    embed = {
        "title": "🔍 FFUF Scan Report",
        "description": "\n".join(description_lines),
        "color": color,
        "fields": [
            {"name": "Total Temuan", "value": str(total), "inline": True},
            {"name": "Waktu Scan", "value": timestamp, "inline": True},
        ],
        "footer": {"text": "Automated by GitHub Actions + ffuf"},
    }
    return embed


def main():
    if not WEBHOOK_URL:
        print(
            "[!] DISCORD_WEBHOOK tidak diset. Tambahkan sebagai GitHub Secret "
            "bernama DISCORD_WEBHOOK. Melewati notifikasi.",
            file=sys.stderr,
        )
        return

    if not os.path.exists(SUMMARY_FILE):
        summary = {"total_findings": 0, "timestamp": "unknown", "findings": []}
    else:
        with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
            summary = json.load(f)

    payload = {
        "username": "FFUF Scanner",
        "embeds": [build_embed(summary)],
    }

    resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)

    if resp.status_code in (200, 204):
        print("[+] Notifikasi Discord terkirim.")
    else:
        print(
            f"[!] Gagal kirim notifikasi Discord: {resp.status_code} {resp.text}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()

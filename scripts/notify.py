#!/usr/bin/env python3
"""
Kirim ringkasan hasil ffuf scan ke Discord melalui webhook, LENGKAP dengan
file report.txt sebagai attachment supaya semua temuan (bukan cuma sample)
bisa dilihat.

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
REPORT_FILE = "report.txt"

# Batas ukuran file attachment Discord webhook standar (8 MB).
DISCORD_FILE_LIMIT_BYTES = 8 * 1024 * 1024


def build_embed(summary):
    total = summary.get("total_findings", 0)
    timestamp = summary.get("timestamp", "unknown")
    sample = summary.get("findings_sample", [])
    status_breakdown = summary.get("status_breakdown", {})
    likely_soft_404 = summary.get("likely_soft_404")

    color = 0x2ECC71 if total == 0 else 0xE74C3C

    description_lines = []
    for f in sample:
        description_lines.append(
            f"`{f['status']}` **{f['target']}**/{f['input']} "
            f"(len={f['length']}, words={f['words']})"
        )
    if not description_lines:
        description_lines.append("Tidak ada temuan pada scan ini.")

    remaining = total - len(sample)
    if remaining > 0:
        description_lines.append(
            f"\n*...dan {remaining} temuan lainnya. Lihat file `report.txt` "
            f"yang dilampirkan untuk daftar lengkap.*"
        )

    fields = [
        {"name": "Total Temuan", "value": str(total), "inline": True},
        {"name": "Waktu Scan", "value": timestamp, "inline": True},
    ]

    if status_breakdown:
        breakdown_text = ", ".join(
            f"`{code}`: {count}" for code, count in status_breakdown.items()
        )
        fields.append({"name": "Breakdown Status Code", "value": breakdown_text, "inline": False})

    if likely_soft_404:
        fields.append({
            "name": "⚠️ Kemungkinan False Positive",
            "value": (
                f"{likely_soft_404['pct']}% temuan ({likely_soft_404['count']} dari {total}) "
                f"punya length sama ({likely_soft_404['length']} bytes) — indikasi soft-404. "
                f"Pertimbangkan tambah filter `-fs {likely_soft_404['length']}`."
            ),
            "inline": False,
        })

    embed = {
        "title": "🔍 FFUF Scan Report",
        "description": "\n".join(description_lines)[:4000],  # jaga di bawah limit 4096
        "color": color,
        "fields": fields,
        "footer": {"text": "Automated by GitHub Actions + ffuf"},
    }
    return embed


def send_with_attachment(payload):
    """Kirim embed + file report.txt sekaligus lewat multipart request."""
    if not os.path.exists(REPORT_FILE):
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        return resp

    file_size = os.path.getsize(REPORT_FILE)
    if file_size > DISCORD_FILE_LIMIT_BYTES:
        print(
            f"[!] report.txt ({file_size} bytes) melebihi limit Discord "
            f"({DISCORD_FILE_LIMIT_BYTES} bytes), dikirim tanpa attachment.",
            file=sys.stderr,
        )
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        return resp

    with open(REPORT_FILE, "rb") as f:
        files = {"file": ("report.txt", f, "text/plain")}
        data = {"payload_json": json.dumps(payload)}
        resp = requests.post(WEBHOOK_URL, data=data, files=files, timeout=30)
    return resp


def main():
    if not WEBHOOK_URL:
        print(
            "[!] DISCORD_WEBHOOK tidak diset. Tambahkan sebagai GitHub Secret "
            "bernama DISCORD_WEBHOOK. Melewati notifikasi.",
            file=sys.stderr,
        )
        return

    if not os.path.exists(SUMMARY_FILE):
        summary = {"total_findings": 0, "timestamp": "unknown", "findings_sample": []}
    else:
        with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
            summary = json.load(f)

    payload = {
        "username": "FFUF Scanner",
        "embeds": [build_embed(summary)],
    }

    resp = send_with_attachment(payload)

    if resp.status_code in (200, 204):
        print("[+] Notifikasi Discord terkirim (dengan attachment report.txt).")
    else:
        print(
            f"[!] Gagal kirim notifikasi Discord: {resp.status_code} {resp.text}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()

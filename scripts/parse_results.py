#!/usr/bin/env python3
"""
Parse semua file hasil ffuf (*.json) yang diunduh dari artifact GitHub Actions,
lalu gabungkan menjadi satu laporan markdown (report.md).
"""

import json
import glob
import os
from datetime import datetime, timezone

SEARCH_DIR = "downloaded-results"
OUTPUT_FILE = "report.md"


def find_result_files():
    pattern = os.path.join(SEARCH_DIR, "**", "*.json")
    return glob.glob(pattern, recursive=True)


def parse_file(filepath):
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return findings

    target = data.get("config", {}).get("url", "unknown")
    for r in data.get("results", []):
        findings.append(
            {
                "target": target,
                "url": r.get("url", ""),
                "status": r.get("status", ""),
                "length": r.get("length", ""),
                "words": r.get("words", ""),
                "input": r.get("input", {}).get("FUZZ", ""),
            }
        )
    return findings


def main():
    files = find_result_files()
    all_findings = []
    for f in files:
        all_findings.extend(parse_file(f))

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("# FFUF Scan Report\n\n")
        out.write(f"**Waktu scan:** {timestamp}\n\n")
        out.write(f"**Total file hasil diproses:** {len(files)}\n\n")
        out.write(f"**Total temuan:** {len(all_findings)}\n\n")

        if not all_findings:
            out.write("Tidak ada temuan pada scan ini.\n")
        else:
            out.write("| Target | Path Ditemukan | Status | Length | Words |\n")
            out.write("|---|---|---|---|---|\n")
            for f in all_findings:
                out.write(
                    f"| {f['target']} | {f['input']} | {f['status']} | "
                    f"{f['length']} | {f['words']} |\n"
                )

    print(f"[+] Report ditulis ke {OUTPUT_FILE} ({len(all_findings)} temuan)")

    # Simpan juga ringkasan untuk dipakai script notifikasi
    with open("summary.json", "w", encoding="utf-8") as sf:
        json.dump(
            {
                "timestamp": timestamp,
                "total_findings": len(all_findings),
                "findings": all_findings[:20],  # batasi untuk notifikasi
            },
            sf,
        )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Parse semua file hasil ffuf (*.json) yang diunduh dari artifact GitHub Actions,
lalu gabungkan menjadi satu laporan markdown (report.txt) + summary.json untuk notifikasi.
"""

import json
import glob
import os
from collections import Counter
from datetime import datetime, timezone

SEARCH_DIR = "downloaded-results"
OUTPUT_FILE = "report.txt"

# Berapa banyak baris yang ditampilkan sebagai "sample" di embed Discord.
# Daftar LENGKAP tetap ada di report.txt yang dikirim sebagai file attachment,
# jadi angka ini tidak membatasi data yang bisa dilihat, hanya preview di chat.
SAMPLE_SIZE_FOR_NOTIFY = 15

# Kalau satu nilai 'length' (ukuran response) mendominasi lebih dari persentase ini,
# kemungkinan besar itu soft-404 / catch-all page, bukan temuan valid.
SOFT_404_THRESHOLD_PCT = 50


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

    # PENTING: config.url adalah TEMPLATE mentah yang dipakai untuk -u,
    # masih mengandung literal "FUZZ" yang BELUM di-substitute
    # (contoh: "https://target.com/FUZZ"). Ini cuma dipakai untuk
    # menampilkan domain/base target di kolom, bukan untuk path hasil scan.
    config_url_template = data.get("config", {}).get("url", "unknown")
    base_target = config_url_template.replace("/FUZZ", "").rstrip("/")

    for r in data.get("results", []):
        # r["url"] adalah URL HASIL SCAN yang sudah di-resolve (FUZZ sudah
        # diganti wordlist entry sebenarnya) — ini yang harus dipakai untuk
        # ditampilkan, BUKAN direkonstruksi manual dari target + input.
        findings.append(
            {
                "target": base_target,
                "full_url": r.get("url", ""),
                "status": r.get("status", ""),
                "length": r.get("length", ""),
                "words": r.get("words", ""),
                "input": r.get("input", {}).get("FUZZ", ""),
            }
        )
    return findings


def analyze(all_findings):
    """Hitung breakdown status code dan deteksi kemungkinan soft-404."""
    status_counter = Counter(f["status"] for f in all_findings)
    length_counter = Counter(f["length"] for f in all_findings)

    likely_soft_404 = None
    if all_findings:
        most_common_length, count = length_counter.most_common(1)[0]
        pct = (count / len(all_findings)) * 100
        if pct >= SOFT_404_THRESHOLD_PCT:
            likely_soft_404 = {
                "length": most_common_length,
                "count": count,
                "pct": round(pct, 1),
            }

    return status_counter, length_counter, likely_soft_404


def main():
    files = find_result_files()
    all_findings = []
    for f in files:
        all_findings.extend(parse_file(f))

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status_counter, length_counter, likely_soft_404 = analyze(all_findings)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("=" * 60 + "\n")
        out.write("FFUF SCAN REPORT\n")
        out.write("=" * 60 + "\n\n")
        out.write(f"Waktu scan          : {timestamp}\n")
        out.write(f"Total file diproses : {len(files)}\n")
        out.write(f"Total temuan        : {len(all_findings)}\n\n")

        out.write("-" * 60 + "\n")
        out.write("BREAKDOWN PER STATUS CODE\n")
        out.write("-" * 60 + "\n")
        for status, count in sorted(status_counter.items(), key=lambda x: -x[1]):
            out.write(f"  Status {status:<5} : {count}\n")
        out.write("\n")

        if likely_soft_404:
            out.write("-" * 60 + "\n")
            out.write("⚠️  PERINGATAN: KEMUNGKINAN FALSE POSITIVE (SOFT-404)\n")
            out.write("-" * 60 + "\n")
            out.write(
                f"{likely_soft_404['count']} dari {len(all_findings)} temuan "
                f"({likely_soft_404['pct']}%) punya response length yang SAMA "
                f"persis ({likely_soft_404['length']} bytes).\n"
                f"Ini indikasi kuat target mengembalikan halaman yang sama untuk "
                f"path apapun (catch-all/soft-404), bukan path yang benar-benar ada.\n"
                f"Rekomendasi: tambahkan filter -fs {likely_soft_404['length']} di ffuf "
                f"untuk membuang noise ini.\n\n"
            )

        out.write("-" * 60 + "\n")
        out.write("DAFTAR LENGKAP TEMUAN\n")
        out.write("-" * 60 + "\n")

        if not all_findings:
            out.write("Tidak ada temuan pada scan ini.\n")
        else:
            # Pakai separator " | " eksplisit, BUKAN fixed-width padding.
            # Fixed-width (mis. f"{x:<30}") tidak memotong string yang lebih
            # panjang dari width-nya, sehingga kolom bisa nempel tanpa spasi
            # kalau isinya kebetulan lebih panjang dari perkiraan.
            header = f"{'STATUS':<8} | {'LENGTH':<8} | {'WORDS':<7} | URL\n"
            out.write(header)
            out.write("-" * 70 + "\n")
            for f in all_findings:
                out.write(
                    f"{str(f['status']):<8} | {str(f['length']):<8} | "
                    f"{str(f['words']):<7} | {f['full_url']}\n"
                )

    print(f"[+] Report ditulis ke {OUTPUT_FILE} ({len(all_findings)} temuan)")

    # Ringkasan untuk notifikasi Discord.
    # Sample dibatasi untuk preview di embed, tapi report.txt (dikirim sebagai
    # file attachment) selalu berisi SEMUA temuan tanpa terpotong.
    with open("summary.json", "w", encoding="utf-8") as sf:
        json.dump(
            {
                "timestamp": timestamp,
                "total_findings": len(all_findings),
                "status_breakdown": dict(status_counter),
                "likely_soft_404": likely_soft_404,
                "findings_sample": all_findings[:SAMPLE_SIZE_FOR_NOTIFY],
            },
            sf,
        )


if __name__ == "__main__":
    main()

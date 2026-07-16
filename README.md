# FFUF Scanner via GitHub Actions

Automated fuzzing/scanning tool menggunakan [ffuf](https://github.com/ffuf/ffuf), dijalankan
otomatis lewat GitHub Actions (terjadwal harian atau manual trigger), dengan laporan
dikirim ke Discord.

> ⚠️ **Hanya gunakan untuk target yang Anda miliki atau yang sudah memberi izin eksplisit**
> (misalnya scope bug bounty resmi, atau environment internal/staging milik sendiri).
> Scanning tanpa otorisasi terhadap sistem pihak lain berpotensi melanggar hukum.

## Struktur Project

```
.
├── .github/workflows/ffuf-scan.yml   # Workflow utama
├── configs/targets.yml                # Daftar target scan
├── wordlists/common.txt               # Wordlist (ganti dengan SecLists untuk hasil lebih lengkap)
├── scripts/
│   ├── run_ffuf.sh                    # Jalankan scan manual/lokal
│   ├── parse_results.py               # Parse JSON hasil ffuf → report.md
│   └── notify.py                      # Kirim ringkasan ke Discord
└── reports/                           # (opsional) tempat simpan histori report
```

## Setup

### 1. Push project ini ke repo GitHub Anda

```bash
git init
git add .
git commit -m "Initial ffuf scanner setup"
git branch -M main
git remote add origin <URL_REPO_ANDA>
git push -u origin main
```

### 2. Tambahkan Discord Webhook sebagai GitHub Secret

**Jangan** taruh webhook URL langsung di file workflow — siapapun yang bisa membaca
repo (atau history commit) akan bisa memakainya untuk kirim pesan ke channel Anda.

Langkah:
1. Buka repo di GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Klik **New repository secret**
3. Name: `DISCORD_WEBHOOK`
4. Value: (paste webhook URL Discord Anda persis seperti ini)
   ```
   https://discord.com/api/webhooks/1380068184463380580/J9ALEGY_GFoCsYR15uSmr99qjVjN8gC_VCEOPONz07DSlYFwlwa29AG-TOYErTf3gNRZ
   ```
5. Klik **Add secret**

### 3. (Opsional) Tambahkan Auth Token jika target butuh autentikasi

Kalau target Anda memerlukan header Authorization, tambahkan secret lain:
- Name: `TARGET_AUTH_TOKEN`
- Value: token Anda

Kalau tidak dibutuhkan, workflow tetap jalan (header akan kosong).

### 4. Edit daftar target

Buka `configs/targets.yml` dan sesuaikan dengan target yang **sah Anda scan**.

### 5. Jalankan

- **Manual:** buka tab **Actions** di GitHub → pilih workflow **FFUF Fuzzing Scan** → **Run workflow**
- **Otomatis:** akan jalan tiap hari jam 02:00 UTC (ubah jadwal di `cron` pada file workflow)

## Testing Lokal (sebelum push ke CI)

```bash
go install github.com/ffuf/ffuf/v2@latest
chmod +x scripts/run_ffuf.sh
./scripts/run_ffuf.sh https://target-anda.com
```

## Kustomisasi

| Yang ingin diubah | Lokasi |
|---|---|
| Daftar target | `configs/targets.yml` |
| Wordlist | `wordlists/common.txt` (rekomendasi: ganti dengan [SecLists](https://github.com/danielmiessler/SecLists)) |
| Rate limit / threads | parameter `-rate` dan `-t` di `ffuf-scan.yml` |
| Filter status code | parameter `-mc` (match code) di `ffuf-scan.yml` |
| Jadwal scan | `cron` di bagian `on.schedule` pada `ffuf-scan.yml` |
| Format notifikasi Discord | `scripts/notify.py` |

## Keamanan

- Webhook Discord & auth token disimpan sebagai GitHub Secrets, tidak pernah muncul di log atau file yang ter-commit.
- `.gitignore` sudah mencegah hasil scan (`results/`, `report.md`, `summary.json`) ikut ter-commit tanpa sengaja.
- `max-parallel: 3` pada matrix job membatasi jumlah scan paralel agar tidak membebani target.
- `-rate` dan `-timeout` pada ffuf membatasi kecepatan request untuk mengurangi risiko dianggap serangan DoS.

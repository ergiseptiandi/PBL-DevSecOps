# Contekan Presentasi ATS — DevSecOps (± 15 menit)

Urutan ini dipakai sambil live di depan kelas. Setiap langkah: **apa yang kamu
tunjuk → apa yang kamu ucapkan**.

## 1. Opening (1 menit)

> "Aplikasi kami Task Manager — tapi yang dinilai bukan CRUD-nya, melainkan
> bagaimana setiap perubahan kode melewati gerbang keamanan otomatis sebelum
> sampai ke user. Inilah DevSecOps: security bukan tahap akhir, tapi bagian
> dari setiap tahap."

Tunjuk: `README.md` → bagian **Arsitektur** (diagram).

## 2. Arsitektur (2 menit)

Tunjuk diagram di README, jelaskan sambil menunjuk:

- **Nginx** = gerbang tunggal. Yang publik cuma port 80.
- **frontend** (Next.js) tidak pernah menyentuh database — jaringan `web` hanya.
- **backend blue & green** = image Python FastAPI yang sama, beda env
  `APP_COLOR`/`APP_VERSION`. Salah satu sedang melayani, yang lain standby.
- **postgres** di jaringan `data` — tidak bisa diakses dari frontend maupun luar.
- Semua rahasia (password DB) dari `.env` — tidak ada di source code.

## 3. Secure coding di Python (3 menit) — ini wajib per brief

Tunjuk `backend/app/` satu per satu:

| File | Yang ditunjuk |
|------|---------------|
| `schemas.py` | Validasi Pydantic: judul maks 140 karakter, karakter kontrol ditolak, `StrictBool` — `"yes"` ditolak |
| `models.py` + `db.py` | ORM SQLAlchemy → query selalu parameterized → **SQL Injection mustahil** |
| `security.py` | Rate limit 60 req/menit per IP + security headers (CSP `default-src 'none'`, `X-Frame-Options: DENY`, `nosniff`) |
| `main.py` | `/docs` dimatikan; error 500 generik (stack trace hanya di log); delete selalu 204 |
| `tests/test_api.py` | Test otomatis yang *menyerang aplikasi sendiri*: payload SQLi tersimpan sebagai literal, input kosong → 422, string dikoleksi → 422 |

Lalu buktikan live:

```bash
cd backend && pytest -v
```

→ 13 test hijau, termasuk `test_create_task_sql_injection_is_stored_literally`.

## 4. CI/CD — security gate, bukan cuma pull & install (4 menit)

Buka GitHub repo → tab **Actions** → klik run terakhir → tunjuk tiap job:

1. **gitleaks** — "Kalau ada token/password ketimpa commit, pipeline langsung merah."
2. **Bandit** — "SAST untuk Python: pola kode rentan."
3. **pip-audit** — "Dependency Python dicek ke database CVE (OSV)."
4. **pytest** — "Logika bisnis + abuse test."
5. **ESLint / npm audit / next build** — "Sisi JS juga dicek CVE-nya."
6. **Semgrep** — "SAST lintas bahasa + cari secret yang lolos."
7. **Trivy** — "Scan vulnerability dependency + misconfig Dockerfile/compose."
8. **CodeQL** (workflow terpisah) — "Analisis semantik mendalam, hasilnya di tab **Security → Code scanning**."

> Poin kunci: *"Tidak ada kode yang bisa sampai ke main kalau satu saja gate merah."*

## 5. Blue-green deployment live (3 menit)

Di terminal VPS:

```bash
curl http://<IP-VPS>/api/version        # {"color":"blue","version":"1.0.0"}
./scripts/switch-green.sh               # cutover
curl http://<IP-VPS>/api/version        # {"color":"green","version":"1.1.0"}
```

Refresh browser → badge kanan atas berubah. Jelaskan:

> "Release versi baru = nyalakan green, pindahkan Nginx, rollback cukup satu
> perintah. Tidak ada rebuild, tidak ada downtime."

## 6. Demo serangan kecil-kecilan (1 menit) — opsional, ampuh

Di UI, buat task dengan judul:

```
'; DROP TABLE tasks;--
```

→ tersimpan sebagai teks biasa; task lain masih ada.
Lalu tempel judul 200 karakter → ditolak (422).

## 7. Penutup & antisipasi pertanyaan (1 menit)

**Q: Kenapa Python, bukan cuma Next.js?**
A: Brief mensyaratkan secure coding di Python; dua instance backend ini juga
yang membuat blue-green deployment nyata bisa didemonstrasikan.

**Q: Apa yang terjadi kalau CI merah?**
A: Merge diblokir (buat branch protection rule di `main` — tunjukkan Settings →
Branches). Demo: push kode yang mengandung password palsu → gitleaks merah.

**Q: Apa yang tidak boleh di-commit?**
A: `.env`, password, token. Sudah di-gitignore + gitleaks sebagai jaring pengaman.

**Q: Bedanya npm audit vs Trivy?**
A: npm audit khusus tree dependency Node; Trivy lebih luas — filesystem,
image container, dan misconfig IaC (Dockerfile/compose).

**Q: Kenapa container non-root?**
A: Kalau container ditembus, penyerang tidak dapat privilege root; blast radius
lebih kecil.

---

Checklist sebelum maju:

- [ ] `docker compose ps` semua healthy di VPS
- [ ] Actions run terakhir **hijau** semua job
- [ ] Code scanning menampilkan hasil CodeQL (jalankan sekali sebelum demo)
- [ ] `.env` bersih dari git history
- [ ] Terminal VPS + browser (UI) + tab Actions + tab Security siap di-share screen

# PBL DevSecOps — Task Manager

![CI/CD](https://github.com/ergiseptiandi/PBL-DevSecOps/actions/workflows/ci-cd.yml/badge.svg)
![CodeQL](https://github.com/ergiseptiandi/PBL-DevSecOps/actions/workflows/codeql.yml/badge.svg)

Aplikasi **Task Manager** full-stack untuk tugas DevSecOps (PBL). Repo ini
mendemokan pipeline CI/CD dengan security gate di setiap tahap — secret scan,
SAST, SCA, CodeQL, Trivy — hingga blue-green deployment di belakang Nginx.

- Frontend: **Next.js 16** (App Router, TypeScript, Tailwind)
- Backend: **Python FastAPI** (SQLAlchemy + PostgreSQL)
- Database: **PostgreSQL 16** (container terpisah, tidak diekspos ke publik)
- Edge: **Nginx** (reverse proxy + blue-green switch)
- Orkestrasi: **Docker Compose** (jaringan `web` / `api` terpisah)
- CI/CD: **GitHub Actions** — gitleaks, Bandit, Semgrep, pip-audit, npm audit,
  CodeQL, Trivy — deploy ke VPS via self-hosted runner

---

## Arsitektur

```
 Browser ──HTTP──► Nginx (:8080 di host)
                    ├── /       ──►  frontend Next.js      (jaringan web)
                    └── /api/*  ──►  backend AKTIF         (jaringan api)
                                       ├── backend-blue  (FastAPI :8000)
                                       └── backend-green (FastAPI :8000)
                                             │
                                             ▼
                                    PostgreSQL 16 — dijangkau lewat
                                    network eksternal
                                    (nginx-proxy-manager_default)
```

- `web` : nginx ↔ frontend
- `api` : nginx ↔ backend-blue / backend-green
- Frontend tidak pernah menjangkau database; hanya backend yang terhubung ke
  Postgres lewat network Docker eksternal.

Blue dan green adalah dua container dari image yang sama, dibedakan lewat env
`APP_COLOR` / `APP_VERSION`. Badge di kanan atas UI menampilkan instance yang
sedang melayani (`BLUE · 1.0.0` atau `GREEN · 1.1.0`).

### Blue-green deployment

```bash
# traffic sedang di BLUE
curl http://localhost:8080/api/version     # {"color":"blue", ...}

./scripts/switch-green.sh                  # sed .env + nginx reload halus
curl http://localhost:8080/api/version     # {"color":"green", ...}

./scripts/switch-blue.sh                   # rollback satu perintah
```

Tidak ada rebuild image saat switch — hanya konfigurasi Nginx yang berubah.
Rollback satu perintah, tanpa downtime.

---

## Menjalankan di VPS

Prasyarat: Docker terpasang, dan Postgres yang terjangkau lewat network Docker
eksternal `nginx-proxy-manager_default` (di server ini sudah ada). Kalau
network-nya belum ada:

```bash
docker network create nginx-proxy-manager_default
# lalu jalankan Postgres di network tersebut dengan hostname `postgres`
```

Lanjut deploy:

```bash
git clone https://github.com/ergiseptiandi/PBL-DevSecOps.git
cd PBL-DevSecOps

cp .env.example .env
nano .env                 # isi password Postgres, sesuaikan nama DB

docker compose up -d --build
docker compose ps         # 4 service: backend-blue, backend-green, frontend, nginx
curl http://localhost:8080/api/health
```

Panduan lengkap (firewall, self-hosted runner, deploy otomatis, TLS) ada di
[`docs/VPS-DEPLOY.md`](docs/VPS-DEPLOY.md). Ringkasan alur presentasi ada di
[`docs/PRESENTASI.md`](docs/PRESENTASI.md).

---

## Menjalankan secara lokal (tanpa Docker)

**Backend** (Python ≥ 3.12) — tanpa `DATABASE_URL` otomatis memakai SQLite lokal:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest                           # 13 test, termasuk uji SQLi & validasi
uvicorn app.main:app --reload    # http://localhost:8000/api/health
```

**Frontend** (Node ≥ 20, disarankan 24):

```bash
cd frontend
npm ci
npm run dev                      # http://localhost:3000
```

`/api/*` dari frontend otomatis di-proxy ke `BACKEND_URL`
(default `http://localhost:8000`) lewat `rewrites()` di `next.config.ts`.

---

## CI/CD Pipeline

Workflow: [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) (push & PR ke `main`)

| Job | Tool | Fungsi security | Gagal kapan? |
|-----|------|-----------------|--------------|
| 🔐 `secret-scan` | gitleaks | Menangkap password/token/API key yang ter-commit | Ada secret terdeteksi |
| 🐍 `backend` | Bandit | SAST — pola rentan di Python (shell injection, hardcoded secret, dsb.) | Temuan severity medium+ |
| 🐍 `backend` | pip-audit | CVE dependency Python terhadap database OSV | Ada vuln high/critical |
| 🐍 `backend` | pytest | Unit test + abuse test (payload SQLi, input invalid, dsb.) | Test gagal |
| ▲ `frontend` | ESLint | Code quality & aturan `eslint-config-next` | Error lint |
| ▲ `frontend` | npm audit | CVE dependency JS | Ada vuln high+ |
| ▲ `frontend` | next build | Memastikan artifact produksi bisa dibuat | Build rusak |
| 🔎 `sast` | Semgrep (`p/python`, `p/javascript`, `p/secrets`) | SAST lintas bahasa + deteksi secret | Temuan berseverity |
| 🛡️ `trivy` | Trivy (fs + config) | CVE dependency & misconfig Dockerfile/compose | Vuln HIGH/CRITICAL |
| 🚀 `deploy` | self-hosted runner | CD ke VPS: build → up -d → smoke test `/api/health` | Smoke test gagal |

Workflow terpisah [`.github/workflows/codeql.yml`](.github/workflows/codeql.yml):
**CodeQL** (analisis semantik Python & JavaScript) untuk push, PR, dan scan
terjadwal tiap minggu. Hasilnya muncul di tab **Security → Code scanning**.

Deploy otomatis **hanya berjalan bila**: push ke `main`, repo variable
`DEPLOY_ENABLED=true` sudah diset (Settings → Secrets and variables → Actions
→ Variables), dan self-hosted runner terdaftar di VPS. Tanpa itu, job `deploy`
diskip dan pipeline tetap berjalan.

---

## Security — secure coding yang diterapkan

**Backend (Python/FastAPI)**

1. **Validasi input ketat** — Pydantic v2: tipe dipaksa (`StrictBool`), panjang maks 140,
   karakter kontrol ditolak, judul di-strip & tidak boleh kosong.
2. **Pencegahan SQL injection** — semua query lewat ORM SQLAlchemy (parameterized otomatis).
   Test khusus membuktikan payload `'; DROP TABLE tasks;--` tersimpan sebagai *literal*.
3. **Rate limiting** per-IP (slowapi, default 60 req/menit).
4. **Security headers** di setiap response: `Content-Security-Policy: default-src 'none'`,
   `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`, dst.
5. **CORS whitelist eksplisit** — bukan `*`; method & header dibatasi.
6. **Error tidak membocorkan internal** — stack trace hanya di log server;
   client menerima pesan generik. Endpoint delete selalu 204.
7. **Secret via environment** — tidak ada kredensial di source; `.env` di-gitignore,
   `.env.example` hanya berisi placeholder.
8. **Dokumentasi API dimatikan** — `/docs`, `/redoc`, `/openapi.json` nonaktif di produksi.
9. **Container non-root** — backend & frontend jalan sebagai user biasa.
10. **Database tidak diekspos** — tidak ada port 5432 yang dipublikasikan.

**Frontend**

- React/Next.js escape output secara default (mitigasi XSS).
- Tidak ada `dangerouslySetInnerHTML`.
- CSP untuk aplikasi web dikirim Nginx (`default-src 'self'`, inline script dibatasi).

**Pipeline**

- Setiap push/PR wajib lolos semua gate sebelum deploy.
- Workflow berjalan dengan `permissions: contents: read` (least privilege).

---

## Struktur Repository

```
PBL-DevSecOps/
├── .github/workflows/
│   ├── ci-cd.yml              # pipeline utama: scan → test → build → deploy
│   └── codeql.yml             # CodeQL (mingguan + setiap push/PR)
├── backend/                   # FastAPI + SQLAlchemy (blue & green)
│   ├── app/
│   │   ├── main.py            # routes, exception handler
│   │   ├── schemas.py         # validasi Pydantic (input untrusted)
│   │   ├── security.py        # security headers + rate limiter
│   │   ├── models.py / db.py / config.py
│   ├── tests/test_api.py      # termasuk abuse test SQLi & validasi
│   └── Dockerfile             # python:3.12-slim, non-root, healthcheck
├── frontend/                  # Next.js 16 (App Router, TS, Tailwind)
│   ├── src/app/page.tsx       # UI Task Manager
│   ├── src/lib/api.ts         # fetch wrapper /api/*
│   └── Dockerfile             # node:24-alpine, standalone, non-root
├── nginx/templates/           # reverse proxy + upstream blue/green (envsubst)
├── scripts/switch-blue.sh     # rollback ke BLUE
├── scripts/switch-green.sh    # cut-over ke GREEN
├── docker-compose.yml         # backend×2, frontend, nginx (postgres eksternal)
├── docs/                      # panduan VPS & ringkasan presentasi
└── .env.example               # placeholder — .env asli tidak di-commit
```

---

## Troubleshooting singkat

| Gejala | Solusi |
|--------|--------|
| Backend unhealthy / gagal connect ke `postgres` | Pastikan container Postgres jalan di network eksternal & kredensial `.env` sesuai |
| Badge UI selalu menampilkan warna sama setelah switch | Hard refresh browser (Ctrl+F5); switch memakai `docker compose up -d nginx` |
| Job `deploy` diskip di Actions | Normal bila `DEPLOY_ENABLED` belum `true` — set di Settings → Variables |
| `npm audit` gagal di CI | `cd frontend && npm audit fix`; commit lockfile-nya |
| `pip-audit` gagal di CI | Naikkan versi di `backend/requirements.txt` ke rilis bebas CVE, lalu freeze ulang |

---

## Hardening lanjutan (bahan diskusi / future work)

- User PostgreSQL non-superuser khusus aplikasi + `REVOKE` hak DELETE/DDL bila tak perlu.
- TLS termination (Certbot/Let's Encrypt) di Nginx + HSTS.
- Pin base image dengan digest (`python:3.12-slim@sha256:...`).
- `read_only: true` + `tmpfs` di compose, `cap_drop: ALL`, `no-new-privileges`.
- Notifikasi (mis. Telegram) dari workflow bila pipeline merah.

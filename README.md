# PBL DevSecOps — Task Manager

![CI/CD](https://github.com/ergiseptiandi/PBL-DevSecOps/actions/workflows/ci-cd.yml/badge.svg)
![CodeQL](https://github.com/ergiseptiandi/PBL-DevSecOps/actions/workflows/codeql.yml/badge.svg)

Aplikasi **Task/Todo Manager** full-stack yang dikembangkan untuk praktikum
**DevSecOps (PBL)**. Bukan sekadar CRUD — aplikasi ini menjadi kendaraan demo
untuk siklus **Plan → Code → Build → Test → Release → Deploy → Operate → Monitor**
yang di setiap tahapnya ada **security gate** otomatis, termasuk
*blue-green deployment* di belakang Nginx.

- Frontend: **Next.js 16** (App Router, TypeScript, Tailwind)
- Backend: **Python FastAPI** (secure coding, lihat bagian Security)
- Database: **PostgreSQL 16**
- Edge: **Nginx** (reverse proxy + blue-green switch)
- Orkestrasi: **Docker Compose** (jaringan `web` / `api` / `data` dipisah)
- CI/CD: **GitHub Actions** — gitleaks, Bandit, Semgrep, pip-audit, npm audit,
  CodeQL, Trivy — lalu deploy otomatis ke VPS via **self-hosted runner**

---

## Arsitektur

```
                        ┌────────────────────────────── VPS (Docker Compose) ─────────────────────────────┐
                        │                                                                                  │
  Browser ──HTTP──►  Nginx (:80) ──► /          ──►  Frontend  Next.js 16        (container, non-root)    │
                        │        └─► /api/*     ──►  backend AKTIF               (blue ATAU green)        │
                        │                            ┌────────────────────────┐                            │
                        │                            │  FastAPI (blue :8000)  │◄──┐                        │
                        │                            ├────────────────────────┤   │  jaringan `api` + `data`│
                        │                            │  FastAPI (green :8000) │◄──┤                        │
                        │                            └───────────┬────────────┘   │                        │
                        │                                        ▼                │                        │
                        │                              PostgreSQL 16 (:5432)      │  jaringan `data`       │
                        └─────────────────────────────────────────────────────────┼────────────────────────┘
                                                              volume db_data      ▼
```

- `web` : nginx ↔ frontend — edge publik
- `api` : nginx ↔ backend-blue / backend-green
- `data`: backend ↔ postgres — **frontend tidak bisa menjangkau database**

Blue dan green adalah dua container dari **image yang sama**, dibedakan hanya
lewat env `APP_COLOR` / `APP_VERSION`. Badge di kanan atas UI menampilkan
instance mana yang sedang melayani (`BLUE · 1.0.0` atau `GREEN · 1.1.0`).

### Blue-Green Deployment

```bash
# traffic sedang di BLUE
curl http://localhost/api/version     # {"color":"blue", ...}

./scripts/switch-green.sh             # sed .env + nginx reload halus
curl http://localhost/api/version     # {"color":"green", ...}

./scripts/switch-blue.sh              # rollback seketika
```

Tidak ada rebuild image saat switch — hanya konfigurasi Nginx yang berubah.
Rollback = satu perintah, tanpa downtime.

---

## Menjalankan di VPS (Linux) — cara utama sesuai brief

```bash
# 1. Install Docker (Ubuntu, sekali saja)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # logout/login setelahnya

# 2. Ambil source code
git clone https://github.com/ergiseptiandi/PBL-DevSecOps.git
cd PBL-DevSecOps

# 3. Siapkan rahasia — JANGAN commit .env
cp .env.example .env
nano .env        # ganti POSTGRES_PASSWORD dengan yang kuat

# 4. Build & jalankan semuanya
docker compose up -d --build
docker compose ps

# 5. Buka browser: http://<IP-VPS>
```

Panduan lengkap (firewall, self-hosted runner, deploy otomatis, TLS) ada di
[`docs/VPS-DEPLOY.md`](docs/VPS-DEPLOY.md).
Contekan alur presentasi ada di [`docs/PRESENTASI.md`](docs/PRESENTASI.md).

---

## Menjalankan secara lokal (tanpa Docker)

**Backend** (Python ≥ 3.12):

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

## CI/CD — bukan sekadar pull & npm install

Workflow: [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) (push & PR ke `main`)

| Job | Tool | Fungsi security | Gagal kapan? |
|-----|------|-----------------|--------------|
| 🔐 `secret-scan` | gitleaks | Menangkap password/token/API key yang tidak sengaja ke-commit | Ada secret terdeteksi |
| 🐍 `backend` | Bandit | SAST — cari pola rentan di Python (shell injection, hardcoded secret, dsb.) | Temuan severity medium+ |
| 🐍 `backend` | pip-audit | CVE dependency Python terhadap database OSV | Ada vuln high/critical |
| 🐍 `backend` | pytest | Unit test + **abuse test** (payload SQLi, input invalid, dsb.) | Test gagal |
| ▲ `frontend` | ESLint | Code quality & aturan `eslint-config-next` | Error lint |
| ▲ `frontend` | npm audit | CVE dependency JS | Ada vuln high+ |
| ▲ `frontend` | next build | Memastikan artifact produksi bisa dibuat | Build rusak |
| 🔎 `sast` | Semgrep (`p/python`, `p/javascript`, `p/secrets`) | SAST lintas bahasa + deteksi secret | Temuan berseverity |
| 🛡️ `trivy` | Trivy (fs + config) | CVE dependency & misconfig Dockerfile/compose | Vuln HIGH/CRITICAL |
| 🚀 `deploy` | self-hosted runner | CD ke VPS: build → up -d → smoke test `/api/health` | Smoke test gagal |

Workflow terpisah [`.github/workflows/codeql.yml`](.github/workflows/codeql.yml):
**CodeQL** (analisis semantik Python & JavaScript) untuk push, PR, dan scan
terjadwal tiap minggu. Hasilnya muncul di tab **Security → Code scanning**.

Deploy otomatis **hanya berjalan bila**:
`push ke main` **dan** repo variable `DEPLOY_ENABLED=true` sudah diset
(Settings → Secrets and variables → Actions → Variables) dan runner
self-hosted terdaftar di VPS. Jika belum, job `deploy` diskip — pipeline
tetap hijau. Detail: [`docs/VPS-DEPLOY.md`](docs/VPS-DEPLOY.md).

---

## Security — Secure Coding yang diterapkan

**Backend (Python/FastAPI)**

1. **Validasi input ketat** — Pydantic v2: tipe dipaksa (`StrictBool`), panjang maks 140,
   karakter kontrol ditolak, judul di-strip & tidak boleh kosong.
2. **Anti SQL Injection** — semua query lewat ORM SQLAlchemy (parameterized otomatis).
   Test khusus membuktikan payload `'; DROP TABLE tasks;--` tersimpan sebagai *literal*.
3. **Rate limiting** per-IP (slowapi, default 60 req/menit) → anti abuse/brute force.
4. **Security headers** di setiap response: `Content-Security-Policy: default-src 'none'`,
   `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`, dst.
5. **CORS whitelist eksplisit** — bukan `*`; method & header dibatasi.
6. **Error tidak membocorkan internal** — stack trace hanya di log server;
   client menerima pesan generik. Endpoint delete selalu 204 (tidak membocorkan eksistensi).
7. **Secret via environment** — tidak ada kredensial di source; `.env` di-gitignore,
   `.env.example` hanya berisi placeholder.
8. **Dokumentasi API dimatikan** — `/docs`, `/redoc`, `/openapi.json` nonaktif di produksi.
9. **Container non-root** — backend & frontend jalan sebagai user biasa, `read_only`
   bisa ditambahkan (lihat Hardening lanjutan).
10. **Database tidak diekspos** — port 5432 tidak dipublikasikan; hanya jaringan internal `data`.

**Frontend**

- React/Next.js escape output secara default (anti-XSS).
- Tidak ada `dangerouslySetInnerHTML`.
- CSP untuk aplikasi web dikirim Nginx (`default-src 'self'`, inline script dibatasi).

**Pipeline**

- Setiap push/PR wajib lolos semua gate — tidak ada "merge dulu, benerin nanti".
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
│   │   ├── main.py            # routes, exception handler (anti bocor detail)
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
├── docker-compose.yml         # postgres, backend×2, frontend, nginx
├── docs/                      # panduan VPS & contekan presentasi
└── .env.example               # placeholder — .env asli JANGAN di-commit
```

---

## Troubleshooting singkat

| Gejala | Solusi |
|--------|--------|
| `POSTGRES_PASSWORD wajib diisi` saat `docker compose up` | `cp .env.example .env` lalu isi password |
| Badge UI selalu menampilkan warna sama setelah switch | Bersihkan *hard refresh* (Ctrl+F5); switch memakai `docker compose up -d nginx` |
| Job `deploy` diskip di Actions | Normal bila `DEPLOY_ENABLED` belum `true` — set di Settings → Variables |
| `npm audit` gagal di CI | `cd frontend && npm audit fix`; commit lockfile-nya |
| `pip-audit` gagal di CI | Naikkan versi di `backend/requirements.txt` ke rilis bebas CVE, lalu freeze ulang |

---

## Hardening lanjutan (bahan diskusi/future work)

- User PostgreSQL non-superuser khusus aplikasi + `REVOKE` hak DELETE/DDL bila tak perlu.
- TLS termination (Certbot/Let's Encrypt) di Nginx + HSTS.
- Pin base image dengan digest (`python:3.12-slim@sha256:...`).
- `read_only: true` + `tmpfs` di compose, `cap_drop: ALL`, `no-new-privileges`.
- Pushover/Telegram alert dari workflow bila pipeline merah.

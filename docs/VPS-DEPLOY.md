# Panduan Deploy ke VPS + GitHub Self-Hosted Runner

Dokumen ini untuk tim PBL yang menjalankan repo ini di VPS Linux
(contoh: Ubuntu 22.04/24.04). Semua perintah dijalankan di VPS sebagai user
biasa (bukan root) kecuali disebutkan.

## 1. Install Docker & clone

```bash
sudo apt update && sudo apt install -y git curl
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker          # atau logout-login

git clone https://github.com/ergiseptiandi/PBL-DevSecOps.git
cd PBL-DevSecOps
```

## 2. Konfigurasi database (.env)

Aplikasi memakai Postgres yang terjangkau lewat network Docker eksternal
`nginx-proxy-manager_default` (hostname `postgres`). Pastikan Postgres berjalan
di network tersebut, buat database-nya, lalu:

```bash
cp .env.example .env
nano .env
```

Isi minimal:

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<password — mis. openssl rand -base64 24>
POSTGRES_DB=<nama database>
ACTIVE_BACKEND=backend-blue:8000
HTTP_PORT=8080
```

> `.env` sudah di-gitignore — jangan pernah commit.
> Cek cepat: `git status --ignored | grep .env`

## 3. Jalankan

```bash
docker compose up -d --build
docker compose ps        # semua harus healthy/running
curl http://localhost:8080/api/health
curl http://localhost:8080/api/version
```

Buka `http://IP-VPS:8080` di browser. Firewall:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 8080/tcp
sudo ufw enable
```

## 4. Demo blue-green

```bash
./scripts/switch-green.sh   # cutover ke GREEN (zero downtime)
curl http://localhost:8080/api/version   # {"color":"green","version":"1.1.0",...}
./scripts/switch-blue.sh    # rollback ke BLUE
```

## 5. Update aplikasi (pull model)

```bash
git pull
docker compose up -d --build
```

## 6. Self-hosted runner — deploy otomatis dari GitHub Actions

Supaya push ke `main` otomatis ter-deploy ke VPS:

1. Buka repo di GitHub → **Settings → Actions → Runners → New self-hosted runner**
2. Pilih **Linux**, arsitektur **x64**. Jalankan perintah yang ditampilkan
   (urutannya kurang lebih):

   ```bash
   mkdir -p ~/actions-runner && cd ~/actions-runner
   curl -o runner.tar.gz -L https://github.com/actions/runner/releases/download/<VERSI>/actions-runner-linux-x64-<VERSI>.tar.gz
   tar xzf runner.tar.gz
   ./config.sh --url https://github.com/ergiseptiandi/PBL-DevSecOps --token <TOKEN-SEKALI-PAKAI>
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

3. Supaya container di dalam job deploy bisa dijalankan: user service runner
   harus anggota grup `docker` (job deploy menjalankan `docker compose`).

4. Aktifkan job deploy:

   **Settings → Secrets and variables → Actions**
   - Tab **Variables** → New repository variable:
     - `DEPLOY_ENABLED` = `true`
   - Kredensial database **tidak** disimpan di GitHub — workflow deploy
     memakai `.env` yang sudah ada di VPS (non-destruktif, hanya menambah
     variabel yang belum ada).

5. Push apa pun ke `main` → job `🚀 Deploy ke VPS` berjalan di runner VPS.
   Atau trigger manual: **Actions → CI/CD → Run workflow**.

> Catatan keamanan: self-hosted runner di repo **public** sebaiknya hanya
> menerima job dari workflow yang kamu percaya (repo milik sendiri — fork PR
> tidak otomatis menjalankan runner karena `if: vars.DEPLOY_ENABLED == 'true'`;
> tapi matikan "Run workflows from fork pull requests" di Settings → Actions →
> General untuk ekstra aman).

## 7. Verifikasi akhir (checklist demo)

- [ ] `docker compose ps` → 4 service up/healthy
- [ ] `http://IP-VPS:8080` → UI Task Manager tampil, badge `BLUE`
- [ ] `./scripts/switch-green.sh` → badge berubah jadi `GREEN`
- [ ] GitHub → **Actions** → workflow terakhir hijau (semua job)
- [ ] GitHub → **Security → Code scanning** → hasil CodeQL muncul
- [ ] `git log --all -- .env` kosong — `.env` tidak ada di history

#!/usr/bin/env bash
# Switch traffic edge (Nginx) dari BLUE ke GREEN — tanpa rebuild apa pun.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "[!] .env belum ada — menyalin dari .env.example"
  cp .env.example .env
fi

sed -i -E 's|^ACTIVE_BACKEND=.*|ACTIVE_BACKEND=backend-green:8000|' .env

echo "[*] Mengarahkan Nginx ke backend-green ..."
docker compose up -d nginx

sleep 2
PORT="$(grep -E '^HTTP_PORT=' .env | cut -d= -f2 || true)"
PORT="${PORT:-80}"
echo "[*] Verifikasi via /api/version:"
curl -fsS "http://localhost:${PORT}/api/version" || echo "[!] Gagal memanggil /api/version — cek: docker compose ps"
echo
echo "[✓] Selesai. Traffic sekarang dilayani oleh GREEN."

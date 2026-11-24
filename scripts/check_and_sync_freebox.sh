#!/usr/bin/env bash
set -euo pipefail

VM_HOST="${FREEBOX_VM_HOST:-192.168.1.170}"
VM_USER="${FREEBOX_VM_USER:-freebox}"
VM_PORT="${SCIWATCH_PORT:-8095}"
VM_DIR="${FREEBOX_VM_DIR:-/opt/mykairn-sciwatch}"
PUBLIC_URL="${MYKAIRN_PUBLIC_URL:-https://www.mykairn.fr}"

echo "=== 1. Vérification VM Freebox (${VM_USER}@${VM_HOST}:${VM_PORT}) ==="
HEALTH_JSON="$(curl -fsS --retry 3 --retry-connrefused --retry-delay 1 --max-time 8 "http://${VM_HOST}:${VM_PORT}/api/health")"
echo "LAN /api/health: ${HEALTH_JSON}"

EXT_CODE="$(curl -sS --retry 3 --retry-connrefused --retry-delay 1 -o /dev/null -w "%{http_code}" --max-time 8 -H "CF-Connecting-IP: 8.8.8.8" "http://${VM_HOST}:${VM_PORT}/api/profiles")"
echo "Sécurité anti-accès externe sans secret (CF-Connecting-IP: 8.8.8.8): HTTP ${EXT_CODE}"
if [ "${EXT_CODE}" != "401" ]; then
  echo "❌ ERREUR: /api/profiles aurait dû renvoyer 401 avec un en-tête proxy externe sans secret !" >&2
  exit 1
fi

ssh -o BatchMode=yes "${VM_USER}@${VM_HOST}" "
  echo 'mykairn-sciwatch-web.service:' \$(systemctl is-active mykairn-sciwatch-web.service)
  echo 'mykairn-sciwatch-watch.timer:' \$(systemctl is-active mykairn-sciwatch-watch.timer)
  df -h /
"

echo ""
echo "=== 2. Synchronisation des Knowledge Packs 6D vers ${PUBLIC_URL}/api/science/packs ==="
ssh -o BatchMode=yes "${VM_USER}@${VM_HOST}" "
  set -euo pipefail
  cd '${VM_DIR}'
  /usr/bin/python3 - <<'PYEOF'
import pathlib, sqlite3, subprocess, sys

env_path = pathlib.Path('${VM_DIR}/.env')
webhook_secret = ''
if env_path.is_file():
    for raw in env_path.read_text(encoding='utf-8', errors='replace').splitlines():
        s = raw.strip()
        if s and not s.startswith('#') and '=' in s:
            k, _, v = s.partition('=')
            if k.strip() == 'MYKAIRN_WEBHOOK_SECRET':
                webhook_secret = v.strip().strip('\"').strip(\"'\")

if not webhook_secret:
    print('❌ MYKAIRN_WEBHOOK_SECRET est vide dans ${VM_DIR}/.env — impossible de pousser vers ${PUBLIC_URL}.', file=sys.stderr)
    sys.exit(2)

db_path = pathlib.Path('${VM_DIR}/data/sciwatch.db')
if not db_path.is_file():
    print('❌ Base SQLite introuvable:', db_path, file=sys.stderr)
    sys.exit(1)

conn = sqlite3.connect(str(db_path))
rows = conn.execute(
    'SELECT topic_slug, COUNT(*) FROM publications GROUP BY topic_slug HAVING COUNT(*) > 0 ORDER BY topic_slug'
).fetchall()
conn.close()

if not rows:
    print('⚠️ Aucune publication en base SQLite. Lancez d abord: sciwatch audit --profile trail_running_coaching')
    sys.exit(0)

for slug, count in rows:
    print(f'-> Push du profil {slug} ({count} études)...')
    res = subprocess.run(['/usr/local/bin/sciwatch', 'push', '--profile', slug], check=False)
    if res.returncode != 0:
        sys.exit(res.returncode)
PYEOF
"

echo ""
echo "=== 3. Vérification en ligne (${PUBLIC_URL}) ==="
PUB_PAGE_CODE="$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "${PUBLIC_URL}/sciwatch")"
PUB_API_CODE="$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "${PUBLIC_URL}/api/sciwatch?action=profiles")"
echo "${PUBLIC_URL}/sciwatch -> HTTP ${PUB_PAGE_CODE}"
echo "${PUBLIC_URL}/api/sciwatch?action=profiles -> HTTP ${PUB_API_CODE}"

if [ "${PUB_PAGE_CODE}" != "200" ] || [ "${PUB_API_CODE}" != "401" ]; then
  echo "❌ Vérification en ligne inattendue (attendu: /sciwatch=200, /api/sciwatch=401)." >&2
  exit 1
fi

echo "✅ Contrôle Freebox & synchronisation mykairn.fr terminés avec succès."

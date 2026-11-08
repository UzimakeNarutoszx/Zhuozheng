#!/usr/bin/env bash
# Run as root after uploading garden-deploy.tar.gz. Never prints credentials.
set -euo pipefail
archive=${1:?Usage: install-server.sh /path/to/garden-deploy.tar.gz}
private_overrides=${2:-}
test "$(id -u)" = 0
test ! -e /opt/garden || { echo 'Refusing to overwrite /opt/garden'; exit 1; }
test -f /opt/jianwen/backend/.env
tar -tzf "$archive" | python3 -c 'import sys,pathlib; names=sys.stdin.read().splitlines(); assert names and all(not pathlib.PurePosixPath(n).is_absolute() and ".." not in pathlib.PurePosixPath(n).parts and pathlib.PurePosixPath(n).parts[0]=="garden" for n in names)'
id garden >/dev/null 2>&1 || useradd --system --user-group --home-dir /opt/garden --shell /usr/sbin/nologin garden
tar -xzf "$archive" -C /opt --no-same-owner
python3 -m venv /opt/garden/backend/.venv
/opt/garden/backend/.venv/bin/pip install -r /opt/garden/backend/requirements.txt
GARDEN_PRIVATE_OVERRIDES="$private_overrides" /opt/garden/backend/.venv/bin/python - <<'PY'
from pathlib import Path
import ast, os, secrets, sqlite3
from dotenv import dotenv_values
source = dotenv_values('/opt/jianwen/backend/.env')
required = ('AI_API_KEY', 'ALIYUN_DYPNS_ACCESS_KEY_ID', 'ALIYUN_DYPNS_ACCESS_KEY_SECRET')
assert all(source.get(k) for k in required), 'Required provider configuration missing'
config = {k: v for k, v in source.items() if k.startswith('ALIYUN_DYPNS_') and v is not None}
# Jianwen may use its source default rather than an explicit .env sign name.
if not config.get('ALIYUN_DYPNS_SIGN_NAME'):
    tree = ast.parse(Path('/opt/jianwen/backend/app/core/config.py').read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == 'ALIYUN_DYPNS_SIGN_NAME':
            config['ALIYUN_DYPNS_SIGN_NAME'] = ast.literal_eval(node.value.args[1])
assert config.get('ALIYUN_DYPNS_SIGN_NAME'), 'SMS sign name missing'
config.update(ENVIRONMENT='production', SECRET_KEY=secrets.token_urlsafe(48),
    DATABASE_URL='sqlite:////opt/garden/backend/data/garden.db',
    MEDIA_DIR='/opt/garden/backend/data/media', SMS_PROVIDER='aliyun',
    AI_API_BASE_URL='https://api.deepseek.com/v1', AI_API_KEY=source['AI_API_KEY'],
    AI_MODEL='deepseek-flash', AI_TIMEOUT_SECONDS='180', AI_DAILY_QUESTION_LIMIT='20')
if os.environ.get('GARDEN_PRIVATE_OVERRIDES'):
    overrides = dotenv_values(os.environ['GARDEN_PRIVATE_OVERRIDES'])
    config.update({k: v for k, v in overrides.items() if k in {'ADMIN_PHONES', 'SENSITIVE_WORDS'} and v is not None})
path = Path('/opt/garden/backend/.env')
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as out:
    for k, v in config.items():
        escaped = str(v).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
        out.write(f"{k}='{escaped}'\n")
db = sqlite3.connect('/opt/garden/backend/data/garden.db')
assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
print('SQLite integrity: ok')
db.close()
PY
chown -R root:root /opt/garden
find /opt/garden/web -type d -exec chmod 755 {} +
find /opt/garden/web -type f -exec chmod 644 {} +
chown root:garden /opt/garden/backend/.env
chmod 640 /opt/garden/backend/.env
mkdir -p /opt/garden/backend/data/media
chown -R garden:garden /opt/garden/backend/data
chmod 750 /opt/garden/backend/data
install -m 644 /opt/garden/backend/deploy/garden.service /etc/systemd/system/garden.service
systemctl daemon-reload
systemctl enable --now garden
for attempt in {1..15}; do
    if curl -fsS http://127.0.0.1:8011/health; then
        systemctl show garden -p MainPID
        exit 0
    fi
    sleep 1
done
echo 'Garden health check failed; inspect journalctl -u garden'
exit 1

#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-stats-admin}"
SERVICE_USER="${SERVICE_USER:-ec2-user}"
SERVICE_GROUP="${SERVICE_GROUP:-${SERVICE_USER}}"
APP_DIR="${APP_DIR:-${PWD}}"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5000}"
WORKERS="${WORKERS:-2}"
THREADS="${THREADS:-4}"
TIMEOUT="${TIMEOUT:-120}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
SYS_CONFIG_DIR="${SYS_CONFIG_DIR:-/etc/sysconfig}"
ENV_FILE="${ENV_FILE:-${SYS_CONFIG_DIR}/${SERVICE_NAME}}"
SERVICE_FILE="${SERVICE_FILE:-${SYSTEMD_DIR}/${SERVICE_NAME}.service}"
CONFIG_INI="${CONFIG_INI:-${APP_DIR}/config.ini}"

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "python3 not found in PATH."
  exit 1
fi

if [[ ! -f "${APP_DIR}/app/__init__.py" ]]; then
  echo "Invalid APP_DIR: ${APP_DIR}"
  echo "Expected to find ${APP_DIR}/app/__init__.py"
  exit 1
fi

extract_secret_key() {
  "${PYTHON_BIN}" - "${APP_DIR}/config.py" <<'PY'
import ast
import re
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    source = f.read()

# 1) Fast-path: literal assignment via regex.
match = re.search(r'^\s*SECRET_KEY\s*=\s*["\']([^"\']+)["\']\s*$', source, flags=re.MULTILINE)
if match:
    print(match.group(1))
    raise SystemExit(0)

tree = ast.parse(source, filename=path)

def is_secret_target(node):
    return isinstance(node, ast.Name) and node.id == "SECRET_KEY"

def extract_default_from_call(node):
    # Handles patterns like os.environ.get("SECRET_KEY", "value")
    if not isinstance(node, ast.Call):
        return None
    if len(node.args) < 2:
        return None
    default_arg = node.args[1]
    if isinstance(default_arg, ast.Constant) and isinstance(default_arg.value, str):
        return default_arg.value
    return None

for node in tree.body:
    value = None
    target = None

    if isinstance(node, ast.Assign):
        if node.targets:
            target = node.targets[0]
        value = node.value
    elif isinstance(node, ast.AnnAssign):
        target = node.target
        value = node.value

    if not is_secret_target(target) or value is None:
        continue

    if isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value:
        print(value.value)
        raise SystemExit(0)

    default_value = extract_default_from_call(value)
    if isinstance(default_value, str) and default_value:
        print(default_value)
        raise SystemExit(0)

print("")
PY
}

SECRET_KEY_VALUE="${SECRET_KEY_VALUE:-${SECRET_KEY:-}}"
if [[ -z "${SECRET_KEY_VALUE}" ]]; then
  SECRET_KEY_VALUE="$(extract_secret_key)"
fi
if [[ -z "${SECRET_KEY_VALUE}" ]]; then
  echo "Could not read SECRET_KEY from ${APP_DIR}/config.py"
  echo "Set SECRET_KEY_VALUE explicitly (or export SECRET_KEY) and rerun."
  exit 1
fi

if ! "${PYTHON_BIN}" -c "import gunicorn" >/dev/null 2>&1; then
  echo "gunicorn is not installed for ${PYTHON_BIN}."
  echo "Install it first, for example:"
  echo "  ${PYTHON_BIN} -m pip install gunicorn"
  exit 1
fi

SUDO=""
if [[ "${EUID}" -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "Need root privileges to write ${SERVICE_FILE} and ${ENV_FILE}."
    echo "Run as root or install sudo."
    exit 1
  fi
fi

tmp_env="$(mktemp)"
tmp_service="$(mktemp)"
trap 'rm -f "${tmp_env}" "${tmp_service}"' EXIT

cat > "${tmp_env}" <<EOF
SECRET_KEY=${SECRET_KEY_VALUE}
STATS_ADMIN_CONFIG_INI=${CONFIG_INI}
CONFIG_FILE_PATH=${CONFIG_INI}
FLASK_ENV=production
FLASK_DEBUG=0
PYTHONUNBUFFERED=1
EOF

cat > "${tmp_service}" <<EOF
[Unit]
Description=LA Referencia Usage Stats Admin
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${PYTHON_BIN} -m gunicorn --bind ${HOST}:${PORT} --workers ${WORKERS} --threads ${THREADS} --timeout ${TIMEOUT} app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

${SUDO} install -d -m 755 "${SYSTEMD_DIR}"
${SUDO} install -d -m 755 "${SYS_CONFIG_DIR}"
${SUDO} install -m 640 "${tmp_env}" "${ENV_FILE}"
${SUDO} install -m 644 "${tmp_service}" "${SERVICE_FILE}"

${SUDO} systemctl daemon-reload
${SUDO} systemctl enable "${SERVICE_NAME}" >/dev/null
${SUDO} systemctl restart "${SERVICE_NAME}"

echo "Installed ${SERVICE_NAME}:"
echo "  service file: ${SERVICE_FILE}"
echo "  env file:     ${ENV_FILE}"
echo "  bind:         ${HOST}:${PORT}"
echo "  app dir:      ${APP_DIR}"
echo "  config ini:   ${CONFIG_INI}"
echo
${SUDO} systemctl --no-pager --full status "${SERVICE_NAME}" || true

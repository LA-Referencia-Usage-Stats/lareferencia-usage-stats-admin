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
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    tree = ast.parse(f.read(), filename=path)

for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "SECRET_KEY":
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    print(node.value.value)
                    raise SystemExit(0)

print("")
PY
}

SECRET_KEY_VALUE="${SECRET_KEY_VALUE:-$(extract_secret_key)}"
if [[ -z "${SECRET_KEY_VALUE}" ]]; then
  echo "Could not read SECRET_KEY from ${APP_DIR}/config.py"
  echo "Set SECRET_KEY_VALUE explicitly and rerun."
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

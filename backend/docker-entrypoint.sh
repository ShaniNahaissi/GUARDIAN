#!/bin/sh
set -e

cd /app/backend

RELOAD_ARGS=""
if [ "${UVICORN_RELOAD:-0}" = "1" ]; then
  RELOAD_ARGS="--reload --reload-dir /app/backend"
fi

if [ "${GUARDIAN_TLS_ENABLED:-1}" != "1" ]; then
  exec python -m uvicorn main:app --host 0.0.0.0 --port 8000 ${RELOAD_ARGS} "$@"
fi

CERT_DIR="${GUARDIAN_TLS_DIR:-/tmp/guardian-tls}"
mkdir -p "$CERT_DIR"

if [ -n "${SSL_CERTFILE:-}" ] && [ -n "${SSL_KEYFILE:-}" ]; then
  CERT="$SSL_CERTFILE"
  KEY="$SSL_KEYFILE"
elif [ -f "$CERT_DIR/cert.pem" ] && [ -f "$CERT_DIR/key.pem" ]; then
  CERT="$CERT_DIR/cert.pem"
  KEY="$CERT_DIR/key.pem"
elif [ "${GUARDIAN_TLS_AUTO_CERT:-1}" = "1" ]; then
  openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" -days 825 \
    -subj "/CN=localhost/O=Guardian/C=IL"
  CERT="$CERT_DIR/cert.pem"
  KEY="$CERT_DIR/key.pem"
else
  echo "guardian: TLS enabled but no certificate. Set SSL_CERTFILE and SSL_KEYFILE, or GUARDIAN_TLS_AUTO_CERT=1, or GUARDIAN_TLS_ENABLED=0." >&2
  exit 1
fi

exec python -m uvicorn main:app --host 0.0.0.0 --port 8000 \
  --ssl-certfile "$CERT" --ssl-keyfile "$KEY" \
  ${RELOAD_ARGS} \
  "$@"

#!/bin/bash
# Generates a local self-signed TLS certificate for dev/testing HTTPS.
# Never commit the output (key.pem especially) to version control --
# regenerate it locally instead. See README.md Section 7 (TLS / HTTPS).
set -e
mkdir -p "$(dirname "$0")/../certs"
openssl req -x509 -newkey rsa:2048 \
  -keyout "$(dirname "$0")/../certs/key.pem" \
  -out "$(dirname "$0")/../certs/cert.pem" \
  -days 365 -nodes -subj "/C=NG/ST=Adamawa/L=Yola/O=MAUMart Dev/CN=127.0.0.1"
echo "Generated backend/certs/cert.pem and backend/certs/key.pem"

#!/bin/bash
# Generate SSL certificates for Betfair Stream API

CERT_DIR="./certs"
mkdir -p "$CERT_DIR"

echo "Generating Betfair SSL certificates..."

# Generate private key
openssl genrsa -out "$CERT_DIR/client-2048.key" 2048

# Generate certificate signing request (CSR)
openssl req -new -x509 -key "$CERT_DIR/client-2048.key" \
    -out "$CERT_DIR/client-2048.crt" -days 1825 \
    -subj "/CN=Betfair API Client"

echo ""
echo "✓ Certificates generated successfully!"
echo ""
echo "Files created:"
echo "  - $CERT_DIR/client-2048.key (private key - keep secure!)"
echo "  - $CERT_DIR/client-2048.crt (public certificate)"
echo ""
echo "Next steps:"
echo "1. Go to https://myaccount.betfair.com/account/security/certificates"
echo "2. Upload client-2048.crt"
echo "3. Update your .env file with BETFAIR_CERT_PATH=./certs/client-2048.crt"
echo ""

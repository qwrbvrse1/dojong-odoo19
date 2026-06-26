#!/bin/bash
# Authenticated curl helper for testing protected Odoo routes

URL="${1:-http://127.0.0.1:8070/odoo/instructor-dashboard}"
DB="${2:-odoo19}"
LOGIN="${3:-admin@demo.com}"
PASSWORD="${4:-admin123}"

# Create a temporary cookie jar
COOKIE_JAR=$(mktemp)
trap "rm -f $COOKIE_JAR" EXIT

# Authenticate and get session
curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -X POST "http://127.0.0.1:8070/web/session/authenticate" \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"db\":\"$DB\",\"login\":\"$LOGIN\",\"password\":\"$PASSWORD\"}}" \
  > /dev/null

# Make the authenticated request
curl -s -b "$COOKIE_JAR" "$URL"

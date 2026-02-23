#!/usr/bin/env bash
set -euo pipefail

DB="aimail_prod"
OUTDIR="/opt/aimail_backups"
TS="$(date -u +%Y%m%d_%H%M%S)"
FILE="$OUTDIR/${DB}_${TS}.sql.gz"

# Dump using postgres user, write output as current user (cron runs as root)
sudo -u postgres pg_dump "$DB" | gzip -c > "$FILE"

# Tight perms + ownership for ops convenience
chmod 640 "$FILE"
chown mailops:mailops "$FILE"

# Keep only last 7 days
find "$OUTDIR" -type f -name "${DB}_*.sql.gz" -mtime +7 -delete

echo "OK: backup created $FILE"
ls -lh "$FILE"

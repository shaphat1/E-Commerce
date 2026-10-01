#!/bin/bash
# Backs up the Postgres database to a timestamped dump file.
# Usage: DATABASE_URL=postgresql://... ./backup_db.sh [output_dir]
set -e
OUT_DIR="${1:-./backups}"
mkdir -p "$OUT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_FILE="$OUT_DIR/maumart_backup_${TIMESTAMP}.dump"
pg_dump --format=custom --dbname="$DATABASE_URL" --file="$OUT_FILE"
echo "Backup written to $OUT_FILE"

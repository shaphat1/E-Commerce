#!/bin/bash
# Restores a Postgres database from a dump file produced by backup_db.sh.
# Usage: DATABASE_URL=postgresql://... ./restore_db.sh path/to/dump_file
set -e
DUMP_FILE="$1"
if [ -z "$DUMP_FILE" ]; then
  echo "Usage: $0 <dump_file>"
  exit 1
fi
pg_restore --clean --if-exists --dbname="$DATABASE_URL" "$DUMP_FILE"
echo "Restored from $DUMP_FILE"

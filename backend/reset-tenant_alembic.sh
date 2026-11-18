#!/bin/bash
#
# Resets the alembic_version table on every tenant (skool_*) database.
#
# Usage:
#   ./reset-tenant_alembic.sh                 # clears alembic_version (no revision stamped)
#   ./reset-tenant_alembic.sh <revision_id>   # clears and stamps the given revision
#

cd /var/www/sms/backend/current || exit

source venv/bin/activate

TARGET_REV="$1"

echo "========================================="
if [ -z "$TARGET_REV" ]; then
    echo "Resetting alembic_version on ALL tenant DBs"
    echo "(clearing version — no revision stamped)"
else
    echo "Resetting alembic_version on ALL tenant DBs"
    echo "Stamping to revision: $TARGET_REV"
fi
echo "========================================="
echo

read -r -p "Are you sure? This will wipe migration history on every tenant. [y/N] " confirm
case "$confirm" in
    [yY][eE][sS]|[yY]) ;;
    *) echo "Aborted."; exit 1 ;;
esac

if [ -z "$TARGET_REV" ]; then
    python app/utils/tenant_reset_alembic.py
else
    python app/utils/tenant_reset_alembic.py "$TARGET_REV"
fi

echo
echo "Done."

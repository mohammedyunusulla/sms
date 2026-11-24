#!/usr/bin/env python3
"""
Backfill for existing institutions: add system roles they don't have yet (e.g. Clerk), and give default
permissions to system roles that have none.

Roles that already have permissions (configured by hand) are left untouched.

Usage (from the backend folder, venv active):
    python backfill_role_permissions.py                         # dry run, all institutions
    python backfill_role_permissions.py --apply                 # write, all institutions
    python backfill_role_permissions.py --institution REMS --apply   # only the given institution code(s)
    python backfill_role_permissions.py --roles-only --apply    # only add missing roles; never fill permissions

Use --roles-only where an institution deliberately keeps a system role empty (e.g. Modern Institution's Principal).
"""
import sys

from app import create_app
from app.models.main.Institution import Institution
from app.utils.seeders import add_missing_system_roles, fill_empty_role_permissions
from app.utils.tenant_db import get_tenant_session


def main():
    apply = "--apply" in sys.argv
    roles_only = "--roles-only" in sys.argv
    if roles_only:
        print("Roles only: missing roles are added, no permissions are filled.")
    codes = [sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a == "--institution"]
    app = create_app()
    with app.app_context():
        query = Institution.query.order_by(Institution.id)
        if codes:
            query = query.filter(Institution.code.in_(codes))
        institutions = query.all()
        print(f"{'APPLYING' if apply else 'DRY RUN'} — {len(institutions)} institution(s)\n")
        for institution in institutions:
            session = get_tenant_session(f"eduspyre_{institution.skid}")
            try:
                added = add_missing_system_roles(session, apply=apply)
                changes = [] if roles_only else fill_empty_role_permissions(session, apply=apply)
            finally:
                session.close()
            print(f"{institution.name} ({institution.code}, eduspyre_{institution.skid}):")
            for code in added:
                print(f"  {'added' if apply else 'would add'} role {code}")
            if not changes and not added:
                print("  nothing missing — unchanged")
            for code, perms in changes:
                print(f"  {'filled' if apply else 'would fill'} {code}: {len(perms)} permissions")
            print()
        if not apply:
            print("Nothing was written. Re-run with --apply to save these changes.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Backfill for existing schools: add system roles they don't have yet (e.g. Clerk), and give default
permissions to system roles that have none.

Roles that already have permissions (configured by hand) are left untouched.

Usage (from the backend folder, venv active):
    python backfill_role_permissions.py                         # dry run, all schools
    python backfill_role_permissions.py --apply                 # write, all schools
    python backfill_role_permissions.py --school REMS --apply   # only the given school code(s)
    python backfill_role_permissions.py --roles-only --apply    # only add missing roles; never fill permissions

Use --roles-only where a school deliberately keeps a system role empty (e.g. Modern School's Principal).
"""
import sys

from app import create_app
from app.models.main.School import School
from app.utils.seeders import add_missing_system_roles, fill_empty_role_permissions
from app.utils.tenant_db import get_tenant_session


def main():
    apply = "--apply" in sys.argv
    roles_only = "--roles-only" in sys.argv
    if roles_only:
        print("Roles only: missing roles are added, no permissions are filled.")
    codes = [sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a == "--school"]
    app = create_app()
    with app.app_context():
        query = School.query.order_by(School.id)
        if codes:
            query = query.filter(School.code.in_(codes))
        schools = query.all()
        print(f"{'APPLYING' if apply else 'DRY RUN'} — {len(schools)} school(s)\n")
        for school in schools:
            session = get_tenant_session(f"skool_{school.skid}")
            try:
                added = add_missing_system_roles(session, apply=apply)
                changes = [] if roles_only else fill_empty_role_permissions(session, apply=apply)
            finally:
                session.close()
            print(f"{school.name} ({school.code}, skool_{school.skid}):")
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

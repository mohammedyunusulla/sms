#!/usr/bin/env python3
"""
One-time backfill: give default permissions to system roles that have none, in every school.

Roles that already have permissions (configured by hand) are left untouched.

Usage (from the backend folder, venv active):
    python backfill_role_permissions.py                         # dry run, all schools
    python backfill_role_permissions.py --apply                 # write, all schools
    python backfill_role_permissions.py --school REMS --apply   # only the given school code(s)
"""
import sys

from app import create_app
from app.models.main.School import School
from app.utils.seeders import fill_empty_role_permissions
from app.utils.tenant_db import get_tenant_session


def main():
    apply = "--apply" in sys.argv
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
                changes = fill_empty_role_permissions(session, apply=apply)
            finally:
                session.close()
            print(f"{school.name} ({school.code}, skool_{school.skid}):")
            if not changes:
                print("  no empty system roles — unchanged")
            for code, perms in changes:
                print(f"  {'filled' if apply else 'would fill'} {code}: {len(perms)} permissions")
            print()
        if not apply:
            print("Nothing was written. Re-run with --apply to save these changes.")


if __name__ == "__main__":
    main()

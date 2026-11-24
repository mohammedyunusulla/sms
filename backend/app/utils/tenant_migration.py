# utils/tenant_migration.py

import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import subprocess

load_dotenv()

MAIN_DB_URL = os.getenv("SUPER_ADMIN_DATABASE_URL")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")


def get_all_institutions():
    engine = create_engine(MAIN_DB_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT skid FROM institutions"))
        return [row[0] for row in result]


def upgrade_all_tenants():
    pwd = quote_plus(POSTGRES_PASSWORD)
    institution_ids = get_all_institutions()
    for skid in institution_ids:
        db_name = f"eduspyre_{skid}"
        db_url = f"postgresql://{POSTGRES_USER}:{pwd}@{POSTGRES_HOST}:{POSTGRES_PORT}/{db_name}"

        print(f"⚙️  Running migration for: {db_name}")
        env = os.environ.copy()
        env["TENANT_DB_URL"] = db_url

        subprocess.run([
            "alembic",
            "-c", "migrations_tenant/alembic_tenant.ini",
            "upgrade", "head"
        ], env=env)


if __name__ == "__main__":
    upgrade_all_tenants()

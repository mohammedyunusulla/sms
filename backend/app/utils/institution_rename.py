"""
One-time rename of the old "school" names in existing databases to the "institution" names the code uses
(EduSpyre serves schools, colleges and universities). Runs at start-up, before anything else touches the
database; safe to run on every start: once nothing is named "school" any more, it does nothing.

Uses the same mapping as the code rename (school -> institution, School -> Institution, SCHOOL -> INSTITUTION),
so tables, columns, enum types, enum values and the built-in admin role code all end up matching the models.
Old names never appear in code any more, so they are spelled here as OLD / OLD_UPPER.
"""
from sqlalchemy import text

OLD = "sch" + "ool"            # kept out of plain sight so a future text rename can't break this module
OLD_UPPER = OLD.upper()
OLD_ADMIN_CODE = f"{OLD_UPPER}_ADMIN"


def _convert(name: str) -> str:
    for old, new in ((OLD_UPPER + "S", "INSTITUTIONS"), (OLD.capitalize() + "s", "Institutions"), (OLD + "s", "institutions"),
                     (OLD_UPPER, "INSTITUTION"), (OLD.capitalize(), "Institution"), (OLD, "institution")):
        name = name.replace(old, new)
    return name


def _q(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def rename_database_objects(conn) -> list:
    """Rename tables, columns, enum types and enum values whose names contain the old word. Returns what changed."""
    done = []
    like = f"%{OLD}%"
    tables = conn.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
        "AND table_type = 'BASE TABLE' AND table_name ILIKE :like"), {"like": like}).scalars().all()
    existing = set(conn.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")).scalars().all())
    for old in tables:
        new = _convert(old)
        if new != old and new not in existing:
            conn.execute(text(f"ALTER TABLE {_q(old)} RENAME TO {_q(new)}"))
            done.append(f"table {old} -> {new}")

    columns = conn.execute(text(
        "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public' "
        "AND column_name ILIKE :like"), {"like": like}).all()
    for table, old in columns:
        new = _convert(old)
        clash = conn.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"),
            {"t": table, "c": new}).first()
        if new != old and not clash:
            conn.execute(text(f"ALTER TABLE {_q(table)} RENAME COLUMN {_q(old)} TO {_q(new)}"))
            done.append(f"column {table}.{old} -> {new}")

    types = conn.execute(text(
        "SELECT typname FROM pg_type WHERE typtype = 'e' AND typname ILIKE :like"), {"like": like}).scalars().all()
    for old in types:
        new = _convert(old)
        if not conn.execute(text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": new}).first():
            conn.execute(text(f"ALTER TYPE {_q(old)} RENAME TO {_q(new)}"))
            done.append(f"type {old} -> {new}")

    labels = conn.execute(text(
        "SELECT t.typname, e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE e.enumlabel ILIKE :like"),
        {"like": like}).all()
    for typ, old in labels:
        new = _convert(old)
        clash = conn.execute(text(
            "SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = :t AND e.enumlabel = :l"),
            {"t": typ, "l": new}).first()
        if not clash:
            conn.execute(text(f"ALTER TYPE {_q(typ)} RENAME VALUE '{old}' TO '{new}'"))
            done.append(f"enum {typ}: {old} -> {new}")
    return done


OLD_DB_PREFIX = "sk" + "ool_"   # old institution database prefix (spelled in parts so a text rename can't change it)
NEW_DB_PREFIX = "eduspyre_"


def rename_tenant_databases(admin_conn, skids) -> list:
    """
    Rename each institution database from the old prefix to eduspyre_<skid>. Runs at start-up before anything
    connects to those databases; admin_conn must be an AUTOCOMMIT connection to another database (e.g. the main one).
    Leftover connections to an old-named database (e.g. a stopped container's) are closed first, since PostgreSQL
    only renames a database nobody is connected to.
    """
    done = []
    for skid in skids:
        old, new = f"{OLD_DB_PREFIX}{skid}", f"{NEW_DB_PREFIX}{skid}"
        has = lambda name: admin_conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}).first()
        if not has(old) or has(new):
            continue
        admin_conn.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :n AND pid <> pg_backend_pid()"),
            {"n": old})
        admin_conn.execute(text(f"ALTER DATABASE {_q(old)} RENAME TO {_q(new)}"))
        done.append(f"{old} -> {new}")
    return done


def rename_tenant_data(conn) -> list:
    """Institution databases: the built-in admin role's code and the admins' old default designations."""
    done = []
    if conn.execute(text("SELECT to_regclass('roles')")).scalar():
        for column in ("role_code", "base_role"):
            n = conn.execute(text(f"UPDATE roles SET {column} = 'INSTITUTION_ADMIN' WHERE {column} = :old"),
                             {"old": OLD_ADMIN_CODE}).rowcount
            if n:
                done.append(f"roles.{column}: {n}")
        n = conn.execute(text(
            "UPDATE roles SET role_name = 'Institution Admin' WHERE role_code = 'INSTITUTION_ADMIN' AND role_name <> 'Institution Admin'")).rowcount
        if n:
            done.append(f"roles.role_name: {n}")
    if conn.execute(text("SELECT to_regclass('institution_admins')")).scalar():
        n = conn.execute(text(
            "UPDATE institution_admins SET designation = 'Institution Admin' WHERE designation IN (:a, :b, :c)"),
            {"a": f"{OLD.capitalize()} Admin", "b": f"{OLD.capitalize()} Administrator", "c": f"UserRole.{OLD_ADMIN_CODE}"}).rowcount
        if n:
            done.append(f"institution_admins.designation: {n}")
    return done

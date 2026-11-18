from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config


def _build_db_url(db_name: str) -> str:
    pwd = quote_plus(Config.POSTGRES_PASSWORD)
    return f'postgresql://{Config.POSTGRES_USER}:{pwd}@{Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/{db_name}'


def get_tenant_engine(db_name):
    return create_engine(_build_db_url(db_name))


def get_tenant_session(db_name):
    engine = get_tenant_engine(db_name)
    Session = sessionmaker(bind=engine)
    return Session()

import psycopg2
import psycopg2.errors
import logging
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine
from app.models.main.School import School
from config import Config
from app.models.base import BaseModelTenant
from app.models.tenant import SchoolUsers, Teacher, Staff, Student, Parent, Roles, Attendance, StudentEnrollment, StudentParent, Subject, UserRoles, Class, Section  # import all school models
from app.utils.tenant_db import get_tenant_engine
from app import db
from app.utils.seeders import seed_default_roles
from flask import current_app
from urllib.parse import urlparse
from urllib.parse import quote_plus


logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Utility class for managing multi-tenant databases
    """
    
    @staticmethod
    def create_school_database(db_name):
        """
        Create a new database for a school
        """
        try:
            # Connect to PostgreSQL server using credentials from config/.env
            conn = psycopg2.connect(
                host=Config.POSTGRES_HOST,
                port=Config.POSTGRES_PORT,
                database="postgres",  # admin DB — we connect here to CREATE the new DB
                user=Config.POSTGRES_USER,
                password=Config.POSTGRES_PASSWORD,
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            # Create database
            cursor = conn.cursor()
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            cursor.close()
            conn.close()
            
            return db_name
            
        except psycopg2.Error as e:
            if "already exists" in str(e):
                logger.warning(f"Database already exists: {db_name}")
                return db_name
            else:
                _log.error("error in db creation", str(e))
                raise Exception(f"Failed to create database: {str(e)}")
    
    @staticmethod
    def initialize_school_schema(db_name):
        """Initialize tables and schema for school database"""
        try:
            engine = get_tenant_engine(db_name)
            BaseModelTenant.metadata.create_all(engine)
            # Student.__table__.create(bind=engine, checkfirst=True)
            # Teacher.__table__.create(bind=engine, checkfirst=True)
            # Role.__table__.create(bind=engine, checkfirst=True)
            # BaseModel.metadata.create_all(bind=engine)
            
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=engine)
            session = Session()
    
            # Seed the default roles after the tables are created
            seed_default_roles(session)
    
            # Commit changes and close the session
            session.close()
            
            logger.info(f"Schema initialized successfully for database: {db_name}")
            
        except psycopg2.Error as e:
            _log.error("error in schema initialization", str(e))
            raise Exception(f"Failed to initialize schema: {str(e)}")
    

    def drop_school_database(db_name):
        """Drop a school database (for cleanup in case of errors)"""
        try:
            # Get database connection parameters from Flask config
            db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
            parsed = urlparse(db_uri)
            
            # Connect to postgres database to drop other databases
            conn = psycopg2.connect(
                host=parsed.hostname or Config.POSTGRES_HOST,
                port=parsed.port or Config.POSTGRES_PORT,
                database='postgres',  # Connect to default postgres DB
                user=parsed.username or Config.POSTGRES_USER,
                password=parsed.password or Config.POSTGRES_PASSWORD,
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Drop the database even while someone is connected to it. Ending connections and dropping
            # used to be two steps, and the drop could run before the connections had closed
            # ("database is being accessed by other users").
            try:
                cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')  # PostgreSQL 13+
            except psycopg2.errors.SyntaxError:
                # Older PostgreSQL: end connections, then retry the drop while they close
                import time
                for attempt in range(6):
                    cursor.execute("""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = %s AND pid <> pg_backend_pid()
                    """, (db_name,))
                    try:
                        cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
                        break
                    except psycopg2.errors.ObjectInUse:
                        if attempt == 5:
                            raise
                        time.sleep(0.5)
            
            cursor.close()
            conn.close()
            
            logger.info(f"Database dropped successfully: {db_name}")
            return True
            
        except psycopg2.Error as e:
            logger.error(f"Failed to drop database {db_name}: {str(e)}")
            raise Exception(f"Failed to drop database {db_name}: {str(e)}")


from contextlib import contextmanager
import logging
_log = logging.getLogger(__name__)
@contextmanager
def switch_to_school_db(skid):
    # Dynamically build DB URI
    db_name = f"skool_{skid}"
    encoded_password = quote_plus(Config.POSTGRES_PASSWORD)
    db_uri = f"postgresql://{Config.POSTGRES_USER}:{encoded_password}@{Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/{db_name}"
    engine = create_engine(db_uri)
    
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
        engine.dispose()
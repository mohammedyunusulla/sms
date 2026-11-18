@echo off
echo ===============================
echo Creating TENANT DB Revision...
echo ===============================
alembic -c migrations_tenant/alembic_tenant.ini revision --autogenerate -m "Tenant DB Update"

echo.
echo ===============================
echo Upgrading ALL TENANT databases...
echo ===============================
python app/utils/tenant_migration.py

echo.
echo Done.
pause

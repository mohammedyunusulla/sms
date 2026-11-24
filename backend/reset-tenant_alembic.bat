@echo off
REM Resets the alembic_version table on every tenant (eduspyre_*) database.
REM
REM Usage:
REM   reset-tenant_alembic.bat                 - clears alembic_version (no revision stamped)
REM   reset-tenant_alembic.bat <revision_id>   - clears and stamps the given revision

setlocal

set TARGET_REV=%~1

echo =========================================
if "%TARGET_REV%"=="" (
    echo Resetting alembic_version on ALL tenant DBs
    echo ^(clearing version - no revision stamped^)
) else (
    echo Resetting alembic_version on ALL tenant DBs
    echo Stamping to revision: %TARGET_REV%
)
echo =========================================
echo.

set /p CONFIRM="Are you sure? This will wipe migration history on every tenant. [y/N] "
if /i not "%CONFIRM%"=="y" if /i not "%CONFIRM%"=="yes" (
    echo Aborted.
    exit /b 1
)

if "%TARGET_REV%"=="" (
    python app\utils\tenant_reset_alembic.py
) else (
    python app\utils\tenant_reset_alembic.py %TARGET_REV%
)

echo.
echo Done.
pause
endlocal
 
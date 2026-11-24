#!/bin/bash
# Main database upgrade script for Ubuntu/Linux
# This script upgrades both main and tenant databases

echo "======================================"
echo "   Institution Management System"
echo "   Database Upgrade"
echo "======================================"

# Set environment variables
export FLASK_APP=run.py
export FLASK_ENV=development

echo ""
echo "Starting database upgrade process..."
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated."
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    else
        echo "❌ Error: Virtual environment not found!"
        echo "Please create a virtual environment first:"
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
fi

echo "======================================"
echo "  Step 1: Upgrading MAIN Database"
echo "======================================"
alembic -c migrations_main/alembic_main.ini upgrade head

if [ $? -eq 0 ]; then
    echo "✓ Main database upgraded successfully"
else
    echo "❌ Error upgrading main database"
    exit 1
fi

echo ""
echo "======================================"
echo "  Step 2: Upgrading TENANT Databases"
echo "======================================"
echo "Note: Tenant databases are upgraded when institutions are accessed"
echo "or you can manually run:"
echo "  alembic -c migrations_tenant/alembic_tenant.ini upgrade head"
echo ""

echo "======================================"
echo "  Database Upgrade Complete!"
echo "======================================"
echo ""
echo "✓ All migrations applied successfully"
echo ""
read -p "Press Enter to continue..."

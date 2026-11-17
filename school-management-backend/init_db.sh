#!/bin/bash
# Script to initialize database - first time setup on Ubuntu/Linux

echo "======================================"
echo "   School Management System"
echo "   Database Initialization"
echo "======================================"

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

echo ""
echo "======================================"
echo "  Step 1: Creating Main DB Migration"
echo "======================================"
alembic -c migrations_main/alembic_main.ini revision --autogenerate -m "Initial migration"

if [ $? -eq 0 ]; then
    echo "✓ Main database migration created"
else
    echo "❌ Error creating main database migration"
    exit 1
fi

echo ""
echo "======================================"
echo "  Step 2: Applying Main DB Migration"
echo "======================================"
alembic -c migrations_main/alembic_main.ini upgrade head

if [ $? -eq 0 ]; then
    echo "✓ Main database initialized"
else
    echo "❌ Error initializing main database"
    exit 1
fi

echo ""
echo "======================================"
echo "  Step 3: Creating Super Admin User"
echo "======================================"
python3 create_test_admin.py

if [ $? -eq 0 ]; then
    echo "✓ Super admin user created"
else
    echo "⚠️  Note: Super admin may already exist"
fi

echo ""
echo "======================================"
echo "  Database Initialization Complete!"
echo "======================================"
echo ""
echo "✓ Database is ready to use"
echo ""
echo "Default Super Admin Credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo "  Email: admin@school.com"
echo ""
echo "⚠️  IMPORTANT: Change the default password after first login!"
echo ""
read -p "Press Enter to continue..."

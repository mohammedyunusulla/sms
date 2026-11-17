#!/bin/bash
# Script to create migration and upgrade MAIN database on Ubuntu/Linux

echo "======================================"
echo "  Creating revision for MAIN DB..."
echo "======================================"
alembic -c migrations_main/alembic_main.ini revision --autogenerate -m "Main DB Update"

echo ""
echo "======================================"
echo "  Applying upgrade to MAIN DB..."
echo "======================================"
alembic -c migrations_main/alembic_main.ini upgrade head

echo ""
echo "✓ Main database migration complete!"
echo ""
read -p "Press Enter to continue..."

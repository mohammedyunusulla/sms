from flask import Blueprint, request, jsonify
from app.services.student_dashboard_service import StudentDashboardService
from app.decorators import login_required
from datetime import datetime

student_dashboard_bp = Blueprint('studentDashboard', __name__)

# Student timetable route has been moved to timeTable.py (GET /api/timeTable/student/<skid>/<student_id>/<date>)
# Future student dashboard routes (stats, announcements, etc.) go here.

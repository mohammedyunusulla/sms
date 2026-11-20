from flask import Blueprint, request, jsonify
from app.services.fee_service import FeeService
from app.decorators import login_required
from app.decorators.auth import student_access_required, student_fee_owner
from app.decorators import log_actions
from datetime import datetime

fee_bp = Blueprint('fee', __name__)


# CREATE FEE STRUCTURE
@fee_bp.route('/structure/create/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_fee_settings')
@log_actions('CREATE_FEE_STRUCTURE')
def create_fee_structure(skid):
    """
    Create fee structure for a class
    Body: {
        "academic_year_id": "1",
        "class_id": 1,
        "fee_name": "TUITION",
        "amount": 15000,
        "is_mandatory": true,
        "description": "Annual tuition fee"
    }
    """
     
    try:
        data = request.get_json()
        
        required_fields = ['academic_year_id', 'class_id', 'fee_name', 'amount']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        result = FeeService.create_fee_structure(data, skid)
        
        return jsonify({
            'message': 'Fee structure created successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500

# GET FEE STRUCTURES
@fee_bp.route('/structure/list/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER', 'CLERK'], permission=('view_fees', 'manage_fees'))
def get_fee_structures(skid):
    """Get all fee structures with optional filters"""
    try:
        academic_year_id = request.args.get('academic_year_id')
        class_id = request.args.get('class_id')
        print("Academic year id-------", academic_year_id)
        result = FeeService.get_fee_structures(skid, academic_year_id, class_id)
        
        return jsonify({
            'data': result,
            'total': len(result),
            'status': 'success',
            'code': 200
        }), 200
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500

# UPDATE FEE STRUCTURE
@fee_bp.route('/structure/update/<skid>/<int:fee_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_fee_settings')
@log_actions('UPDATE_FEE_STRUCTURE')
def update_fee_structure(skid, fee_id):
    """Update fee structure"""  
    try:
        data = request.get_json()
        result = FeeService.update_fee_structure(fee_id, data, skid)
        
        return jsonify({
            'message': 'Fee structure updated successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500



#================================ STUDENT FEE ASSIGNMENT ======================================



# BULK ASSIGN FEES TO CLASS
@fee_bp.route('/assign/class/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_fee_settings')
@log_actions('BULK_ASSIGN_FEES')
def bulk_assign_fees_to_class(skid):
    """
    Assign fees to all students in a class
    Body: {
        "class_id": 1,
        "academic_year_id": "2024-25"
    }
    """
    try:
        data = request.get_json()
        
        if 'class_id' not in data or 'academic_year_id' not in data:
            raise ValueError("class_id and academic_year_id are required")
        
        result = FeeService.bulk_assign_fees_to_class(
            data['class_id'],
            data['academic_year_id'],
            skid,
            due_date=data.get('due_date'),  # chosen in the dialog (it was always today + 30 days - QA C24)
        )
        
        return jsonify({
            'message': f"Fees assigned to {result['total_students']} students",
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500



#====================================== PAYMENT MANAGEMENT ==========================================

# RECORD PAYMENT
@fee_bp.route('/payment/record/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'ACCOUNTANT', 'CLERK'], permission='manage_fees')
@log_actions('RECORD_FEE_PAYMENT')
def record_payment(skid):
    """
    Record fee payment
    Body: {
        "student_fee_id": 1,
        "amount_paid": 5000,
        "payment_mode": "CASH",
        "payment_date": "2024-10-15",
        "transaction_id": "TXN123",
        "remarks": "Partial payment"
    }
    """
    try:
        from flask import g
        data = request.get_json()
        
        required_fields = ['student_fee_id', 'amount_paid', 'payment_mode']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        collected_by_id = g.current_user.school_user_id if hasattr(g, 'current_user') else None
        
        result = FeeService.record_payment(data, skid, collected_by_id)
        
        return jsonify({
            'message': 'Payment recorded successfully',
            'data': result,
            'receipt_number': result['receipt_number'],
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500

# CANCEL PAYMENT
@fee_bp.route('/payment/cancel/<skid>/<int:payment_id>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_fee_settings')
@log_actions('CANCEL_FEE_PAYMENT')
def cancel_payment(skid, payment_id):
    """
    Cancel a payment
    Body: {
        "reason": "Wrong amount entered"
    }
    """
    try:
        data = request.get_json()
        
        data = data or {}
        # the logged-in user is request.current_user (g.current_user.get() crashed with a 500)
        cancelled_by_id = getattr(request.current_user, 'school_user_id', None)

        result = FeeService.cancel_payment(payment_id, skid, cancelled_by_id, data.get('reason'))
        
        return jsonify({
            'message': 'Payment cancelled successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500

# CONVERT REMAINING INSTALLMENTS TO FULL PAYMENT
@fee_bp.route('/payment/convert-to-full/<skid>/<int:student_fee_id>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'ACCOUNTANT', 'CLERK'], permission='manage_fees')
def convert_to_full_payment(skid, student_fee_id):
    """Convert remaining installments to full payment option"""
    try:
        result = FeeService.convert_remaining_to_full_payment(student_fee_id, skid)
        return jsonify({
            'message': result['message'],
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500

# FULL PAYMENT FOR REMAINING CONVERTED INSTALLMENT AMOUNT
@fee_bp.route('/payment/record-full-remaining/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'ACCOUNTANT', 'CLERK'], permission='manage_fees')
def record_full_remaining_payment(skid):
    """Record full payment for remaining balance after installments"""
    try:
        from flask import g
        data = request.get_json()
        collected_by_id = getattr(request.current_user, 'school_user_id', None)
        result = FeeService.record_full_payment_after_installments(data, skid, collected_by_id)
        return jsonify({
            'message': 'Full payment recorded successfully',
            'data': result,
            'receipt_number': result['receipt_number'],
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# ==================== INSTALLMENT ROUTES ====================

# CREATE INSTALLMENTS
@fee_bp.route('/installments/create/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_fee_settings')
@log_actions('CREATE_FEE_INSTALLMENTS')
def create_installments(skid):
    """
    Create installment plan for a student fee
    Body: {
        "student_fee_id": 1,
        "installments": [
            {
                "installment_name": "Term 1",
                "amount": 5000,
                "due_date": "2024-07-31"
            },
            {
                "installment_name": "Term 2",
                "amount": 5000,
                "due_date": "2024-12-31"
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        if 'student_fee_id' not in data or 'installments' not in data:
            raise ValueError("student_fee_id and installments are required")
        
        result = FeeService.create_installments(
            data['student_fee_id'],
            data['installments'],
            skid
        )
        
        return jsonify({
            'message': f'{len(result)} installments created successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# AUTO-GENERATE INSTALLMENTS
@fee_bp.route('/installments/auto-generate/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_fee_settings')
@log_actions('AUTO_GENERATE_INSTALLMENTS')
def auto_generate_installments(skid):
    """
    Auto-generate equal installments
    Body: {
        "student_fee_id": 1,
        "num_installments": 3
    }
    """
    try:
        data = request.get_json()
        
        if 'student_fee_id' not in data or 'num_installments' not in data:
            raise ValueError("student_fee_id and num_installments are required")
        
        if data['num_installments'] < 2 or data['num_installments'] > 12:
            raise ValueError("Number of installments must be between 2 and 12")
        
        result = FeeService.auto_generate_installments(
            data['student_fee_id'],
            data['num_installments'],
            skid
        )
        
        return jsonify({
            'message': f'{len(result)} installments generated successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500

# RECURRING INSTALLMENTS
# skid is in the URL like every other route, so login_required checks the user belongs to that school
@fee_bp.route('/installments/auto-generate-recurring/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_fee_settings')
def auto_generate_recurring_installments(skid):
    """Auto-generate installments for recurring fees. Body: {student_fee_id, preview?}"""
    try:
        data = request.get_json() or {}
        student_fee_id = data.get("student_fee_id")
        preview = bool(data.get("preview"))
        result = FeeService.auto_generate_recurring_installments(student_fee_id, skid, preview=preview)
        return jsonify({
            'message': f'{len(result)} recurring installments {"planned" if preview else "generated"}',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500

# GET INSTALLMENTS
@fee_bp.route('/installments/get/<skid>/<int:student_fee_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'ACCOUNTANT', 'PARENT', 'STUDENT', 'CLERK'], permission=('view_fees', 'manage_fees'), own_roles=('STUDENT', 'PARENT'))
@student_access_required('student_fee_id', resolver=student_fee_owner)
def get_installments(skid, student_fee_id):
    """Get all installments for a student fee"""
    try:
        result = FeeService.get_fee_installments(student_fee_id, skid)
        
        return jsonify({
            'data': result,
            'total': len(result),
            'status': 'success',
            'code': 200
        }), 200
        
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# RECORD INSTALLMENT PAYMENT
@fee_bp.route('/installments/payment/<skid>/<int:installment_id>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'ACCOUNTANT', 'CLERK'], permission='manage_fees')
@log_actions('RECORD_INSTALLMENT_PAYMENT')
def record_installment_payment(skid, installment_id):
    """
    Record payment for a specific installment
    Body: {
        "amount_paid": 2500,
        "payment_mode": "UPI",
        "payment_date": "2024-10-17",
        "transaction_id": "UPI123456",
        "remarks": "Partial installment payment"
    }
    """
    try:
        data = request.get_json()
        
        required_fields = ['amount_paid', 'payment_mode']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Get collected_by_id
        collected_by_id = None
        if hasattr(request, 'current_user') and request.current_user:
            collected_by_id = request.current_user.school_user_id
        
        result = FeeService.record_installment_payment(
            installment_id,
            data,
            skid,
            collected_by_id
        )
        
        return jsonify({
            'message': 'Installment payment recorded successfully',
            'data': result,
            'receipt_number': result['receipt_number'],
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500



# ==================== FEE SUMMARY & REPORTS ====================

# GET STUDENT FEE SUMMARY
@fee_bp.route('/summary/student/<skid>/<int:student_id>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'TEACHER', 'PARENT', 'STUDENT', 'CLERK'], permission=('view_fees', 'manage_fees'), own_roles=('STUDENT', 'PARENT'))
@student_access_required('student_id')
def get_student_fee_summary(skid, student_id):
    """Get complete fee summary for a student"""
    try:
        academic_year_id = request.args.get('academic_year_id')
        if not academic_year_id:
            raise ValueError("academic_year_id parameter is required")
        
        result = FeeService.get_student_fee_summary(student_id, academic_year_id, skid)
        
        return jsonify({
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500

# FEE COLLECTION REPORT
@fee_bp.route('/report/collection/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'ACCOUNTANT', 'CLERK'], permission='manage_fees')
def get_fee_collection_report(skid):
    """Get fee collection report with filters"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        class_id = request.args.get('class_id')
        
        # a bad date used to escape as a 500
        try:
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Dates must be in YYYY-MM-DD format")
        if start_date and end_date and start_date > end_date:
            raise ValueError("'From' date can't be after 'To' date")
        if class_id:
            try:
                class_id = int(class_id)
            except ValueError:
                raise ValueError("Invalid class")

        result = FeeService.get_fee_collection_report(
            skid, start_date, end_date, class_id
        )
        
        return jsonify({
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500

# DEFAULTERS LIST
@fee_bp.route('/report/defaulters/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'ACCOUNTANT', 'CLERK'], permission='manage_fees')
def get_defaulters_list(skid):
    """Get list of students with pending fees"""
     
         
    
    try:
        academic_year_id = request.args.get('academic_year_id')
        if not academic_year_id:
            raise ValueError("academic_year_id parameter is required")
        
        as_of_date = request.args.get('as_of_date')
        if as_of_date:
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        
        result = FeeService.get_defaulters_list(skid, academic_year_id, as_of_date)
        
        return jsonify({
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500

# ==================== DISCOUNT MANAGEMENT ====================

# APPLY DISCOUNT
@fee_bp.route('/discount/apply/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_fee_settings')
@log_actions('APPLY_FEE_DISCOUNT')
def apply_discount(skid):
    """
    Apply discount to student
    Body: {
        "student_id": 123,
        "discount_name": "Merit Scholarship",
        "discount_type": "PERCENTAGE",
        "discount_value": 20,
        "academic_year_id": "2024-25",
        "valid_from": "2024-04-01",
        "valid_to": "2025-03-31",
        "reason": "Academic excellence"
    }
    """
    try:
        data = request.get_json()
        
        data = data or {}
        for field in ['student_id', 'discount_name', 'discount_type', 'discount_value']:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        approved_by_id = getattr(request.current_user, 'school_user_id', None)
        
        result = FeeService.apply_discount(data, skid, approved_by_id)
        
        return jsonify({
            'message': 'Discount applied successfully',
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# DELETE SINGLE FEE STRUCTURE
@fee_bp.route('/structure/delete/<skid>/<int:fee_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_fee_settings')
@log_actions('DELETE_FEE_STRUCTURE')
def delete_single_fee_structure(skid, fee_id):
    """
    Delete a single fee structure
    """
    try:
        result = FeeService.delete_single_fee_structure(fee_id, skid)
        
        return jsonify({
            'message': result['message'],
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500


# DELETE ALL FEE STRUCTURES FOR A CLASS
@fee_bp.route('/structure/delete-class/<skid>/<int:class_id>/<academic_year_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'], permission='manage_fee_settings')
@log_actions('DELETE_CLASS_FEE_STRUCTURES')
def delete_class_fee_structures(skid, class_id, academic_year_id):
    """
    Delete all fee structures for a class and academic year
    """
   
    try:
        result = FeeService.delete_all_class_fees(class_id, academic_year_id, skid)
        
        return jsonify({
            'message': result['message'],
            'data': result,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500



# UNIVERSAL STUDENT SEARCH FOR FEE COLLECTION
@fee_bp.route('/search-student/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'SCHOOL_ADMIN', 'ACCOUNTANT', 'CLERK'], permission='manage_fees')
def search_student_for_fees(skid):
    """
    Universal student search for fee collection
    Query params:
    - q: Search query (name/phone/roll_no)
    - class_id: Filter by class (optional)
    - academic_year_id: For fee filtering (default: 2024-25)
    """
    
    try:
        search_query = request.args.get('q', '').strip()
        class_id = request.args.get('class_id')
        academic_year_id = request.args.get('academic_year_id', '2024-25')
        
        if not search_query:
            raise ValueError("Search query is required")
        
        if len(search_query) < 2:
            raise ValueError("Search query must be at least 2 characters")
        
        # Call service function
        students_list = FeeService.search_students_for_fees(
            search_query=search_query,
            skid=skid,
            academic_year_id=academic_year_id,
            class_id=class_id
        )
        
        return jsonify({
            'data': students_list,
            'total': len(students_list),
            'search_query': search_query,
            'academic_year_id': academic_year_id,
            'status': 'success',
            'code': 200
        }), 200
        
    except ValueError as ve:
        return jsonify({'message': str(ve), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 500}), 500

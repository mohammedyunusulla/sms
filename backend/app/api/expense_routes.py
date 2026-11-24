from app.utils.validators import to_date
from flask import Blueprint, request, jsonify
from app.services.expense_service import ExpenseService
from app.decorators import login_required, log_actions

expense_bp = Blueprint('expenses', __name__)

# Salary Setup Routes
@expense_bp.route('/list/salary-setup/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_salaries')
@log_actions('GET_SALARY_SETUPS')
def get_salary_setups(skid):
    try:
        academic_year_id = request.args.get('academic_year_id')
        setups = ExpenseService.get_staff_salary_setups(skid, academic_year_id)
        return jsonify({
            'salary_setups': setups,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to get salary setups: {str(e)}'}), 500

@expense_bp.route('/salary-setup/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_salaries')
@log_actions('CREATE_SALARY_SETUP')
def create_salary_setup(skid):
    try:
        data = request.json
        setup = ExpenseService.create_salary_setup(skid, data)
        return jsonify({
            'salary_setup': setup,
            'message': 'Salary setup created successfully',
            'status': 'success'
        }), 201
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create salary setup: {str(e)}'}), 500


@expense_bp.route('/salary-setup/update/<skid>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_salaries')
@log_actions('UPDATE_SALARY_SETUP')
def update_salary_setup(skid):
    try:
        data = request.json
        ExpenseService.update_salary_setup(skid, data)
        return jsonify({
            'message': 'Salary setup updated successfully',
            'status': 'success'
        }), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update salary setup: {str(e)}'}), 500


@expense_bp.route('/salary-setup/delete/<skid>/<int:setup_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_salaries')
@log_actions('DELETE_SALARY_SETUP')
def delete_salary_setup(skid, setup_id):
    try:
        result = ExpenseService.delete_salary_setup(skid, setup_id)
        return jsonify({
            'message': result['message'],
            'soft_delete': result['soft_delete'],
            'status': 'success'
        }), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to delete salary setup: {str(e)}'}), 500


# Salary Payment Routes
@expense_bp.route('/salary-payments/generate/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_salaries')
@log_actions('GENERATE_SALARIES')
def generate_salaries(skid):
    try:
        data = request.json
        payments = ExpenseService.generate_monthly_salaries(
            skid,
            data['academic_year_id'],
            data['month'],
            data['year']
        )
        return jsonify({
            'salary_payments': payments,
            'message': 'Salaries generated successfully',
            'status': 'success'
        }), 201
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to generate salaries: {str(e)}'}), 500

@expense_bp.route('/salary-payments/<int:payment_id>/mark-paid/<skid>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_salaries')
@log_actions('MARK_SALARY_PAID')
def mark_salary_paid(skid, payment_id):
    try:
        data = request.json
        payment = ExpenseService.mark_salary_paid(skid, payment_id, data)
        return jsonify({
            'payment': payment,
            'message': 'Salary marked as paid successfully',
            'status': 'success'
        }), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to mark salary as paid: {str(e)}'}), 500


@expense_bp.route('/salary-payments/<skid>/mark-unpaid/<int:payment_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_salaries')
@log_actions('MARK_SALARY_UNPAID')
def mark_salary_unpaid(skid, payment_id):
    try:
        ExpenseService.mark_salary_unpaid(skid, payment_id)
        return jsonify({
            'message': 'Salary marked as unpaid successfully',
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to mark salary as unpaid: {str(e)}'}), 500


# Get salary payments for academic year
@expense_bp.route('/salary-payments/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_salaries')
@log_actions('GET_SALARY_PAYMENTS')
def get_salary_payments(skid):
    try:
        academic_year_id = request.args.get('academic_year_id')
        payments = ExpenseService.get_salary_payments(skid, academic_year_id)
        
        return jsonify({
            'salary_payments': payments,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to get salary payments: {str(e)}'}), 500


#-------------------------------------------Expense Routes-----------------------------------------------------------
@expense_bp.route('/<skid>', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission=('view_expenses', 'manage_expenses'))
@log_actions('GET_EXPENSES')
def get_expenses(skid):
    try:
        filters = {
            'academic_year_id': request.args.get('academic_year_id'),
            'category': request.args.get('category'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date')
        }
        # a bad date reached the database and came back as a psycopg2 error (QA D25)
        start = to_date(filters['start_date'], "Start date") if filters['start_date'] else None
        end = to_date(filters['end_date'], "End date") if filters['end_date'] else None
        if start and end and end < start:
            raise ValueError("End date is before the start date")  # it returned an empty list (QA C30)
        expenses = ExpenseService.get_expenses(skid, filters)
        return jsonify({
            'expenses': expenses,
            'status': 'success',
            'code': 200
        }), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to get expenses: {str(e)}'}), 500


@expense_bp.route('/create/<skid>', methods=['POST'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_expenses')
@log_actions('CREATE_EXPENSE')
def create_expense(skid):
    try:
        data = request.json
        expense = ExpenseService.create_expense(skid, data)
        return jsonify({
            'expense': expense,
            'message': 'Expense created successfully',
            'status': 'success'
        }), 201
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to create expense: {str(e)}'}), 500

# Get expense categories (constant list)
@expense_bp.route('/categories', methods=['GET'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission=('view_expenses', 'manage_expenses'))
def get_expense_categories():
    return jsonify({
        'categories': ExpenseService.EXPENSE_CATEGORIES,
        'status': 'success'
    }), 200


@expense_bp.route('/update/<skid>/<int:expense_id>', methods=['PUT'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_expenses')
@log_actions('UPDATE_EXPENSE')
def update_expense(skid, expense_id):
    try:
        data = request.json
        ExpenseService.update_expense(skid, expense_id, data)
        return jsonify({
            'message': 'Expense updated successfully',
            'status': 'success',
            'code':200
        }), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to update expense: {str(e)}'}), 500

@expense_bp.route('/delete/<skid>/<int:expense_id>', methods=['DELETE'])
@login_required(['SUPER_ADMIN', 'INSTITUTION_ADMIN'], permission='manage_expenses')
@log_actions('DELETE_EXPENSE')
def delete_expense(skid, expense_id):
    try:
        ExpenseService.delete_expense(skid, expense_id)
        return jsonify({
            'message': 'Expense deleted successfully',
            'status': 'success',
            'code':200
        }), 200
    except ValueError as e:
        return jsonify({'message': str(e), 'status': 'error', 'code': 400}), 400
    except Exception as e:
        return jsonify({'message': f'Failed to delete expense: {str(e)}'}), 500

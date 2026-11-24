from app.models.tenant import InstitutionUsers, Teacher, Staff
from app.models.tenant.ExpenseModels import *
from app.utils.db_manager import switch_to_institution_db
from sqlalchemy.orm import joinedload
from datetime import date
from app.utils.validators import non_negative_amount, not_in_future, number_in_range, positive_amount, to_date, within_an_academic_year


def _salary_totals(data):
    """Basic > 0, every allowance/deduction >= 0, and the net pay can't go below zero."""
    basic = positive_amount(data.get('basic_salary'), "Basic salary")
    allowances = {k: non_negative_amount(v, f"Allowance '{k}'") for k, v in (data.get('allowances') or {}).items()}
    deductions = {k: non_negative_amount(v, f"Deduction '{k}'") for k, v in (data.get('deductions') or {}).items()}
    gross = round(basic + sum(allowances.values()), 2)
    net = round(gross - sum(deductions.values()), 2)
    if net < 0:
        raise ValueError("Deductions can't be more than the gross salary")
    return basic, allowances, deductions, gross, net

# The choices the Expenses screen offers (frontend ExpenseList.tsx); any text used to be accepted (QA C27)
EXPENSE_CATEGORIES = ('Staff Salaries', 'Electricity Bill', 'Water Bill', 'Functions/Events', 'Transport/Vehicle Service',
                      'Maintenance', 'Supplies/Stationery', 'Infrastructure', 'Other')
PAYMENT_METHODS = ('cash', 'bank_transfer', 'cheque', 'online')


def _expense_category(value):
    match = next((c for c in EXPENSE_CATEGORIES if c.lower() == str(value or '').strip().lower()), None)
    if not match:
        raise ValueError(f"Choose an expense category: {', '.join(EXPENSE_CATEGORIES)}")
    return match


def _payment_method(value):
    method = str(value or '').strip().lower().replace(' ', '_')
    if method not in PAYMENT_METHODS:
        raise ValueError("Choose a payment method: Cash, Bank Transfer, Cheque or Online")
    return method


class ExpenseService:
    # Predefined categories (from UI constant)
    EXPENSE_CATEGORIES = [
        "Staff Salaries",
        "Electricity Bill",
        "Water Bill",
        "Functions/Events",
        "Transport/Vehicle Service",
        "Maintenance",
        "Supplies/Stationery",
        "Infrastructure",
        "Other"
    ]
    
    @staticmethod
    def get_staff_salary_setups(skid, academic_year_id):
        """Get all salary setups for staff - optimized with eager loading"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                setups = (
                    tenant_session.query(StaffSalarySetup)
                    .join(InstitutionUsers, StaffSalarySetup.staff_id == InstitutionUsers.id)
                    .outerjoin(Teacher, InstitutionUsers.id == Teacher.user_id)
                    .outerjoin(Staff, InstitutionUsers.id == Staff.user_id)
                    .options(
                        joinedload(StaffSalarySetup.staff).joinedload(InstitutionUsers.role_obj),
                        joinedload(StaffSalarySetup.staff).joinedload(InstitutionUsers.teacher),
                        joinedload(StaffSalarySetup.staff).joinedload(InstitutionUsers.staff)
                    )
                    .filter(
                        StaffSalarySetup.is_active == True,
                        StaffSalarySetup.academic_year_id == academic_year_id
                    )
                    .order_by(InstitutionUsers.first_name, InstitutionUsers.last_name)
                    .all()
                )
                
                return [
                    {
                        'id': s.id,
                        'staff_id': s.staff_id,
                        'staff_name': f"{s.staff.first_name} {s.staff.last_name}",
                        'role_name': s.staff.role_obj.role_name if s.staff.role_obj else None,
                        'employee_id': s.staff.teacher.employee_id if s.staff.teacher else (s.staff.staff.employee_id if s.staff.staff else None),
                        'basic_salary': float(s.basic_salary),
                        'allowances': s.allowances,
                        'deductions': s.deductions,
                        'gross_salary': float(s.gross_salary),
                        'net_salary': float(s.net_salary),
                        'effective_from': s.effective_from.isoformat() if s.effective_from else None,
                        'effective_to': s.effective_to.isoformat() if s.effective_to else None,
                        'is_active': s.is_active,
                        'academic_year_id': s.academic_year_id
                    }
                    for s in setups
                ]
                
        except Exception as e:
            raise Exception(f"Failed to get salary setups: {str(e)}")
    
    @staticmethod
    def create_salary_setup(skid, data):
        try:
            with switch_to_institution_db(skid) as tenant_session:
                basic, allowances, deductions, gross, net = _salary_totals(data)
                staff_id = int(data['staff_id'])
                # Salaries are for teachers and staff only, and one active setup per person per year
                is_staff = (tenant_session.query(Teacher).filter_by(user_id=staff_id).first()
                            or tenant_session.query(Staff).filter_by(user_id=staff_id).first())
                if not is_staff:
                    raise ValueError("Salary setups are only for teachers and staff")
                duplicate = tenant_session.query(StaffSalarySetup).filter(
                    StaffSalarySetup.staff_id == staff_id,
                    StaffSalarySetup.academic_year_id == data['academic_year_id'],
                    StaffSalarySetup.is_active.is_(True),
                ).first()
                if duplicate:
                    raise ValueError("This person already has a salary setup for this academic year. Edit it instead.")

                setup = StaffSalarySetup(
                    staff_id=staff_id,
                    academic_year_id=data['academic_year_id'],
                    basic_salary=basic,
                    allowances=allowances,
                    deductions=deductions,
                    gross_salary=gross,
                    net_salary=net,
                    effective_from=data['effective_from'],
                    effective_to=data.get('effective_to'),
                    is_active=True
                )
                
                tenant_session.add(setup)
                tenant_session.commit()
                return setup.to_dict()
        except ValueError:
            raise
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to create salary setup: {str(e)}")
            
    @staticmethod
    def update_salary_setup(skid, data):
        """Update existing salary setup - simplified"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                setup_id = data.get('id')
                if not setup_id:
                    raise ValueError("Setup ID is required for update")
                
                # Fetch setup
                setup = tenant_session.query(StaffSalarySetup).filter(
                    StaffSalarySetup.id == setup_id
                ).one_or_none()
                
                if not setup:
                    raise ValueError("Salary setup not found")
                
                # Calculate new totals (validated)
                basic, allowances, deductions, gross, net = _salary_totals(data)
                
                # Update fields
                setup.basic_salary = basic
                setup.allowances = allowances
                setup.deductions = deductions
                setup.gross_salary = gross
                setup.net_salary = net
                setup.effective_from = data['effective_from']
                setup.effective_to = data.get('effective_to')
                setup.is_active = data.get('is_active', True)
                
                tenant_session.commit()

        except ValueError:
            raise
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to update salary setup: {str(e)}")

            
    @staticmethod
    def delete_salary_setup(skid, setup_id):
        """Delete (soft delete) salary setup"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                setup = tenant_session.query(StaffSalarySetup).filter(
                    StaffSalarySetup.id == setup_id
                ).one_or_none()
                
                if not setup:
                    raise ValueError("Salary setup not found")
                
                # Check if there are any salary payments linked
                payment_count = tenant_session.query(SalaryPayment).filter(
                    SalaryPayment.salary_setup_id == setup_id
                ).count()
                
                if payment_count > 0:
                    # Soft delete - just mark as inactive
                    setup.is_active = False
                    tenant_session.commit()
                    return {'message': 'Salary setup deactivated (has payment history)', 'soft_delete': True}
                else:
                    # Hard delete - no payment history
                    tenant_session.delete(setup)
                    tenant_session.commit()
                    return {'message': 'Salary setup deleted successfully', 'soft_delete': False}
                    
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to delete salary setup: {str(e)}")
        
    @staticmethod
    def generate_monthly_salaries(skid, academic_year_id, month, year):
        month = int(number_in_range(month, 1, 12, "Month"))
        year = int(number_in_range(year, 2000, 2100, "Year"))
        try:
            with switch_to_institution_db(skid) as tenant_session:
                # Get all active salary setups
                setups = (
                    tenant_session.query(StaffSalarySetup)
                    .filter(
                        StaffSalarySetup.academic_year_id == academic_year_id,
                        StaffSalarySetup.is_active == True
                    )
                    .all()
                )
                
                payments = []
                for setup in setups:
                    # Check if already generated
                    existing = (
                        tenant_session.query(SalaryPayment)
                        .filter(
                            SalaryPayment.staff_id == setup.staff_id,
                            SalaryPayment.payment_month == month,
                            SalaryPayment.payment_year == year
                        )
                        .first()
                    )
                    
                    if not existing:
                        payment = SalaryPayment(
                            staff_id=setup.staff_id,
                            salary_setup_id=setup.id,
                            academic_year_id=academic_year_id,
                            payment_month=month,
                            payment_year=year,
                            basic_salary=setup.basic_salary,
                            allowances_paid=setup.allowances,
                            deductions_applied=setup.deductions,
                            gross_amount=setup.gross_salary,
                            net_amount_paid=setup.net_salary,
                            status='pending'
                        )
                        tenant_session.add(payment)
                        payments.append(payment)
                
                tenant_session.commit()
                return [
                    {
                        **p.to_dict(),
                        'staff_name': p.staff.full_name
                    }
                    for p in payments
                ]
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to generate salaries: {str(e)}")
    
    @staticmethod
    def mark_salary_paid(skid, payment_id, payment_data):
        try:
            with switch_to_institution_db(skid) as tenant_session:
                payment = tenant_session.query(SalaryPayment).get(payment_id)
                if not payment:
                    raise ValueError("Payment not found")
                if payment.status == 'paid':
                    # paying twice used to create a second expense entry
                    raise ValueError("This salary is already marked as paid")
                paid_on = not_in_future(payment_data.get('payment_date') or date.today(), "Payment date")

                payment.status = 'paid'
                payment.payment_date = paid_on
                payment.payment_method = payment_data.get('payment_method')
                payment.transaction_reference = payment_data.get('transaction_reference')
                payment.paid_by = payment_data.get('paid_by')
                
                # Auto-create expense entry
                expense = Expense(
                    academic_year_id=payment.academic_year_id,
                    expense_category='Staff Salaries',
                    expense_date=payment.payment_date,
                    amount=payment.net_amount_paid,
                    vendor_name=payment.staff.full_name,
                    description=f"Salary payment for {payment.staff.full_name} - {payment.payment_month}/{payment.payment_year}",
                    reference_type='salary_payment',
                    reference_id=payment.id,
                    payment_method=payment.payment_method,
                    approval_status='approved',
                    approved_by=payment_data.get('paid_by'),
                    created_by=payment_data.get('paid_by')
                )
                
                tenant_session.add(expense)
                tenant_session.commit()
                return payment.to_dict()
        except ValueError:
            raise
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to mark salary as paid: {str(e)}")
    
    
    @staticmethod
    def mark_salary_unpaid(skid, payment_id):
        """Mark salary as unpaid - revert payment and delete expense"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                # Get the salary payment
                payment = (
                    tenant_session.query(SalaryPayment)
                    .options(joinedload(SalaryPayment.staff))
                    .filter(SalaryPayment.id == payment_id)
                    .one_or_none()
                )
                
                if not payment:
                    raise ValueError("Payment not found")
                
                if payment.status != 'paid':
                    raise ValueError("Payment is not in paid status")
                
                # Find and delete the linked expense
                expense = tenant_session.query(Expense).filter(
                    Expense.reference_type == 'salary_payment',
                    Expense.reference_id == payment_id
                ).first()
                
                if expense:
                    tenant_session.delete(expense)
                
                # Revert payment status
                payment.status = 'pending'
                payment.payment_date = None
                payment.payment_method = None
                payment.transaction_reference = None
                payment.paid_by = None
                
                tenant_session.commit()

        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to mark salary as unpaid: {str(e)}")

    
    @staticmethod
    def create_expense(skid, data):
        """Create expense record - type-safe"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                amount = positive_amount(data.get('amount'), "Expense amount")
                expense_day = not_in_future(data.get('expense_date'), "Expense date")
                # filed under the academic year that contains the date
                academic_year_id = within_an_academic_year(tenant_session, expense_day, "Expense date")
                expense = Expense(
                    academic_year_id=academic_year_id,
                    expense_category=_expense_category(data.get('expense_category')),
                    expense_date=expense_day,
                    amount=amount,
                    vendor_name=data.get('vendor_name') or None,
                    description=data.get('description') or None,
                    payment_method=_payment_method(data.get('payment_method')),
                    receipt_attachment_url=data.get('receipt_attachment_url') or None,
                    approval_status=data.get('approval_status', 'approved'),
                    created_by=data.get('created_by'),
                    reference_type=data.get('reference_type'),
                    reference_id=data.get('reference_id')
                )
                
                tenant_session.add(expense)
                tenant_session.commit()
                tenant_session.refresh(expense)
                
                return {
                    'id': expense.id,
                    'expense_category': expense.expense_category,
                    'expense_date': expense.expense_date.isoformat(),
                    'amount': float(expense.amount),
                    'vendor_name': expense.vendor_name,
                    'payment_method': expense.payment_method,
                    'approval_status': expense.approval_status
                }
                
        except ValueError:
            raise
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to create expense: {str(e)}")

    @staticmethod
    def update_expense(skid, expense_id, data):
        """Update existing expense"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                expense = tenant_session.query(Expense).filter(
                    Expense.id == expense_id
                ).one_or_none()
                
                if not expense:
                    raise ValueError("Expense not found")
                if expense.reference_type == 'salary_payment':
                    raise ValueError("Salary expenses are managed from Salary Payments and can't be edited here")

                # Update only the fields that were sent (others used to be wiped)
                if 'amount' in data:
                    expense.amount = positive_amount(data['amount'], "Expense amount")
                if 'expense_date' in data:
                    expense_day = not_in_future(data['expense_date'], "Expense date")
                    expense.academic_year_id = within_an_academic_year(tenant_session, expense_day, "Expense date")
                    expense.expense_date = expense_day
                if data.get('expense_category'):
                    data['expense_category'] = _expense_category(data['expense_category'])
                if data.get('payment_method'):
                    data['payment_method'] = _payment_method(data['payment_method'])
                for field in ('expense_category', 'payment_method', 'vendor_name', 'description', 'receipt_attachment_url'):
                    if field in data:
                        setattr(expense, field, data[field] or (None if field in ('vendor_name', 'description', 'receipt_attachment_url') else getattr(expense, field)))

                tenant_session.commit()

        except ValueError:
            raise
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to update expense: {str(e)}")
    
    @staticmethod
    def delete_expense(skid, expense_id):
        """Delete expense"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                expense = tenant_session.query(Expense).filter(
                    Expense.id == expense_id
                ).one_or_none()
                
                if not expense:
                    raise ValueError("Expense not found")
                
                # Check if it's a salary payment reference
                if expense.reference_type == 'salary_payment':
                    raise ValueError("Cannot delete salary payment expense. Please delete from salary payments.")
                
                tenant_session.delete(expense)
                tenant_session.commit()
                
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to delete expense: {str(e)}")

   
    @staticmethod
    def get_salary_payments(skid, academic_year_id=None):
        try:
            with switch_to_institution_db(skid) as tenant_session:
                query = (
                    tenant_session.query(SalaryPayment)
                    .join(InstitutionUsers, SalaryPayment.staff_id == InstitutionUsers.id)
                )
                
                if academic_year_id:
                    query = query.filter(SalaryPayment.academic_year_id == academic_year_id)
                
                payments = query.order_by(
                    SalaryPayment.payment_year.desc(),
                    SalaryPayment.payment_month.desc()
                ).all()
                
                return [
                    {
                        **payment.to_dict(),
                        'staff_name': payment.staff.full_name
                    }
                    for payment in payments
                ]
        except Exception as e:
            raise Exception(f"Failed to get salary payments: {str(e)}")

    
    @staticmethod
    def get_expenses(skid, filters=None):
        try:
            with switch_to_institution_db(skid) as tenant_session:
                query = tenant_session.query(Expense)
                
                if filters:
                    if filters.get('academic_year_id'):
                        query = query.filter(Expense.academic_year_id == filters['academic_year_id'])
                    if filters.get('category'):
                        query = query.filter(Expense.expense_category == filters['category'])
                    if filters.get('start_date'):
                        query = query.filter(Expense.expense_date >= filters['start_date'])
                    if filters.get('end_date'):
                        query = query.filter(Expense.expense_date <= filters['end_date'])
                
                expenses = query.order_by(Expense.expense_date.desc()).all()
                return [expense.to_dict() for expense in expenses]
        except Exception as e:
            raise Exception(f"Failed to get expenses: {str(e)}")

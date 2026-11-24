from app.models.tenant import Class, Student, InstitutionUsers
from app.models.tenant.Sections import Section
from app.models.tenant.FeeModels import (
    FeeStructure, StudentFee, FeePayment, FeeDiscount, 
     FeeType, PaymentMode, PaymentStatus, FeeInstallment, RecurrenceType
)
from app.utils.db_manager import switch_to_institution_db
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_, extract
from decimal import Decimal
import json


# ------------------------------------------------------------------ shared fee helpers
def _money(value):
    return round(float(value or 0), 2)


def fee_balance(student_fee):
    """What is still owed on a fee: total - discount + late fee - paid."""
    return round(_money(student_fee.total_amount) - _money(student_fee.discount_amount)
                 + _money(student_fee.late_fee) - _money(student_fee.paid_amount), 2)


def refresh_fee_status(student_fee):
    if fee_balance(student_fee) <= 0:
        student_fee.status = PaymentStatus.PAID
    elif _money(student_fee.paid_amount) > 0:
        student_fee.status = PaymentStatus.PARTIAL
    else:
        student_fee.status = PaymentStatus.PENDING


def refresh_installment_status(installment):
    if installment.status == PaymentStatus.CANCELLED:
        return
    left = _money(installment.amount) - _money(installment.paid_amount)
    if left <= 0:
        installment.status = PaymentStatus.PAID
    elif _money(installment.paid_amount) > 0:
        installment.status = PaymentStatus.PARTIAL
    else:
        installment.status = PaymentStatus.PENDING


def _add_months(day, months):
    import calendar
    y, m = divmod(day.month - 1 + months, 12)
    y += day.year
    m += 1
    return date(y, m, min(day.day, calendar.monthrange(y, m)[1]))


def _year_range(session, student_fee):
    from app.models.tenant.AcademicYear import AcademicYear
    if not student_fee.academic_year_id:
        return None
    year = session.query(AcademicYear).filter_by(id=student_fee.academic_year_id).first()
    return (year.start_date, year.end_date) if year else None


def _shrink_from_end(amounts, reduce_by, floors=None):
    """Take reduce_by off the list, last entries first, never below each floor. Returns what couldn't be taken."""
    floors = floors or [0] * len(amounts)
    for i in range(len(amounts) - 1, -1, -1):
        if reduce_by <= 0:
            break
        take = min(reduce_by, round(amounts[i] - floors[i], 2))
        if take > 0:
            amounts[i] = round(amounts[i] - take, 2)
            reduce_by = round(reduce_by - take, 2)
    return reduce_by


def _replace_installments(session, student_fee, plan):
    """
    Validate an installment plan and make it the fee's plan. The plan splits what is still owed;
    a plan that already has payments against it can't be replaced.
    """
    from app.utils.validators import positive_amount, to_date
    if not plan:
        raise ValueError("Add at least one installment")
    if len(plan) > 24:
        raise ValueError("A fee can have at most 24 installments")
    balance = fee_balance(student_fee)
    if balance <= 0:
        raise ValueError("This fee is already fully paid")

    existing = session.query(FeeInstallment).filter_by(student_fee_id=student_fee.id).all()
    if existing:
        paid_against = session.query(FeePayment).filter(
            FeePayment.installment_id.in_([i.id for i in existing])).count()
        if paid_against:
            raise ValueError("Payments were already made against this fee's installments, so the plan can't be "
                             "replaced. Pay the remaining balance in full instead.")

    year = _year_range(session, student_fee)
    rows = []
    for idx, item in enumerate(plan, start=1):
        amount = positive_amount(item.get('amount'), f"Amount of installment {idx}")
        due = to_date(item.get('due_date'), f"Due date of installment {idx}")
        if year and not (year[0] <= due <= year[1]):
            raise ValueError(f"Due date of installment {idx} ({due.strftime('%d %b %Y')}) must be inside the academic "
                             f"year ({year[0].strftime('%d %b %Y')} - {year[1].strftime('%d %b %Y')})")
        name = (str(item.get('installment_name') or '').strip() or f"Installment {idx}")[:100]
        rows.append((name, amount, due))
    total = round(sum(r[1] for r in rows), 2)
    if abs(total - balance) > 0.01:
        raise ValueError(f"Installments add up to {total:.2f}, but the balance to split is {balance:.2f}")

    for old in existing:
        session.delete(old)
    session.flush()
    created = []
    for idx, (name, amount, due) in enumerate(rows, start=1):
        inst = FeeInstallment(student_fee_id=student_fee.id, installment_number=idx, installment_name=name,
                              amount=amount, due_date=due, paid_amount=0, status=PaymentStatus.PENDING)
        session.add(inst)
        created.append(inst)
    student_fee.has_installments = True
    session.flush()
    return created


def _recurring_plan(session, student_fee, fee_structure):
    """Installments for a recurring fee: one per period, covering only what is still owed."""
    rtype = getattr(fee_structure.recurrence_type, 'value', fee_structure.recurrence_type) or 'MONTHLY'
    payable = round(_money(student_fee.total_amount) - _money(student_fee.discount_amount)
                    + _money(student_fee.late_fee), 2)
    if rtype == 'ONE_TIME':
        amounts, step, label = [payable], 0, "Payment"
    else:
        step = {'MONTHLY': 1, 'QUARTERLY': 3, 'YEARLY': 12}.get(rtype)
        if not step:
            raise ValueError(f"Unknown recurrence type '{rtype}'")
        label = {'MONTHLY': 'Month', 'QUARTERLY': 'Quarter', 'YEARLY': 'Year'}[rtype]
        periods = int(fee_structure.recurrence_months or 0)
        per = _money(fee_structure.recurrence_amount)
        if periods < 1 or per <= 0:
            raise ValueError("This fee's recurring amount or number of periods isn't set. Edit the fee structure first.")
        amounts = [per] * periods
        diff = round(payable - sum(amounts), 2)
        if diff >= 0:
            amounts[-1] = round(amounts[-1] + diff, 2)
        else:
            _shrink_from_end(amounts, -diff)  # e.g. a discount: the last periods get smaller
    # what is already paid covers the earliest periods
    paid = _money(student_fee.paid_amount)
    for i in range(len(amounts)):
        take = min(amounts[i], paid)
        amounts[i] = round(amounts[i] - take, 2)
        paid = round(paid - take, 2)

    base = student_fee.due_date or date.today()
    year = _year_range(session, student_fee)
    plan = []
    for i, amount in enumerate(amounts):
        if amount <= 0:
            continue
        due = _add_months(base, step * i)
        if year:  # dues never run past the academic year
            due = min(max(due, year[0]), year[1])
        plan.append({'installment_name': f"{label} {i + 1}" if label != "Payment" else "Full Payment",
                     'amount': amount, 'due_date': due.isoformat()})
    return plan

class FeeService:
    
    @staticmethod
    def create_fee_structure(data, skid):
        """Create fee structure for a class"""
        from app.utils.validators import positive_amount
        try:
            with switch_to_institution_db(skid) as tenant_session:
                amount = positive_amount(data.get('amount'), "Fee amount")
                if data.get('is_recurring') and data.get('recurrence_amount') not in (None, ''):
                    data['recurrence_amount'] = positive_amount(data['recurrence_amount'], "Recurring amount")
                fee_structure = FeeStructure(
                    academic_year_id=data['academic_year_id'],
                    class_id=data['class_id'],
                    fee_name=data['fee_name'],
                    amount=amount,
                    is_mandatory=data.get('is_mandatory', True),
                    description=data.get('description'),
                    is_recurring=data.get('is_recurring', False),
                    recurrence_type=data.get('recurrence_type'),
                    recurrence_amount=data.get('recurrence_amount'),
                    recurrence_months=data.get('recurrence_months'),
                    allows_installments=data.get('allows_installments', True)
                )
                tenant_session.add(fee_structure)
                tenant_session.commit()

                return fee_structure.to_dict()
        except ValueError:
            raise
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to create fee structure: {str(e)}")
    
    @staticmethod
    def get_fee_structures(skid, academic_year_id, class_id=None):
        """Get all fee structures with filters"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                query = tenant_session.query(FeeStructure, Class).join(
                    Class, FeeStructure.class_id == Class.id
                )
                
                if academic_year_id:
                    query = query.filter(FeeStructure.academic_year_id == academic_year_id)
                if class_id:
                    query = query.filter(FeeStructure.class_id == class_id)
                
                results = query.all()
                
                fee_structures = []
                for fee_struct, class_info in results:
                    fee_dict = fee_struct.to_dict()
                    fee_dict['class'] = {
                        'id': class_info.id,
                        'class_name': class_info.class_name
                    }
                    fee_structures.append(fee_dict)
                
                return fee_structures
        except Exception as e:
            raise Exception(f"Failed to get fee structures: {str(e)}")
    
    @staticmethod
    def update_fee_structure(fee_id, data, skid):
        """Update fee structure"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                fee_structure = tenant_session.query(FeeStructure).filter_by(id=fee_id).first()
                if not fee_structure:
                    raise ValueError("Fee structure not found")

                from app.utils.validators import positive_amount
                if 'amount' in data:
                    data['amount'] = positive_amount(data['amount'], "Fee amount")
                if data.get('recurrence_amount') not in (None, ''):
                    data['recurrence_amount'] = positive_amount(data['recurrence_amount'], "Recurring amount")

                for key, value in data.items():
                    if hasattr(fee_structure, key) and key not in ['id', 'created_at']:
                        # if key == 'fee_type' and isinstance(value, str):
                        #     value = FeeType[value]
                        setattr(fee_structure, key, value)
                
                tenant_session.commit()
                return fee_structure.to_dict()
        except ValueError:
            raise
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to update fee structure: {str(e)}")
            
    @staticmethod
    def delete_single_fee_structure(fee_id, skid):
        """
        Delete a fee structure
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                # Get fee structure
                fee_structure = tenant_session.query(FeeStructure).filter_by(id=fee_id).first()
                
                if not fee_structure:
                    raise ValueError(f"Fee structure with ID {fee_id} not found")
                
                # Check if fee is assigned to any students
                assigned_count = tenant_session.query(StudentFee).filter_by(
                    fee_structure_id=fee_id
                ).count()
                
                if assigned_count > 0:
                    raise ValueError(
                        f"Cannot delete this fee structure. It is assigned to {assigned_count} student(s). "
                        f"Please remove student assignments first."
                    )
                
                # Delete the fee structure
                tenant_session.delete(fee_structure)
                tenant_session.commit()
                
                return {
                    'message': 'Fee structure deleted successfully',
                    'deleted_id': fee_id
                }
                
        except ValueError as ve:
            raise ve
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to delete fee structure: {str(e)}")



#=============================== STUDENT FEE ASSIGNMENT =====================================


    @staticmethod
    def assign_fees_to_student(student_id, academic_year_id, skid, custom_fees=None):
        """Assign fees to a student - auto or custom"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                student = tenant_session.query(Student).filter_by(user_id=student_id).first()
                if not student:
                    raise ValueError(f"Student with ID {student_id} not found")
                
                assigned_fees = []
                
                if custom_fees:
                    # Custom fee assignment
                    for fee_data in custom_fees:
                        student_fee = StudentFee(
                            student_id=student_id,
                            fee_structure_id=fee_data['fee_structure_id'],
                            academic_year_id=academic_year_id,
                            due_date=fee_data.get('due_date', date.today() + timedelta(days=30)),
                            total_amount=fee_data['amount'],
                            discount_amount=fee_data.get('discount', 0)
                        )
                        tenant_session.add(student_fee)
                        assigned_fees.append(student_fee)
                else:
                    # Auto-assign based on class
                    fee_structures = tenant_session.query(FeeStructure).filter_by(
                        class_id=student.class_id,
                        academic_year_id=academic_year_id,
                        is_active=True,
                        is_mandatory=True
                    ).all()
                    
                    # ✅ Debug: Check if fee structures exist
                    
                    for fee_struct in fee_structures:
                        # Check if already assigned
                        existing = tenant_session.query(StudentFee).filter_by(
                            student_id=student_id,
                            fee_structure_id=fee_struct.id,
                            academic_year_id=academic_year_id
                        ).first()
                        
                        if existing:
                            continue
                        
                        # ✅ Create new student fee
                        student_fee = StudentFee(
                            student_id=student_id,
                            fee_structure_id=fee_struct.id,
                            academic_year_id=academic_year_id,
                            due_date=date.today() + timedelta(days=30),
                            total_amount=fee_struct.amount,
                            status=PaymentStatus.PENDING
                        )
                        tenant_session.add(student_fee)
                        assigned_fees.append(student_fee)
                
                tenant_session.commit()
                
                return {
                    'assigned_count': len(assigned_fees),
                    'fees': [fee.to_dict() for fee in assigned_fees]
                }
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to assign fees: {str(e)}")

    
    @staticmethod
    def bulk_assign_fees_to_class(class_id, academic_year_id, skid, due_date=None):
        """Assign the class's mandatory fees to all its students, due on due_date (default: today + 30 days)"""
        try:
            from app.utils.validators import to_date
            due = to_date(due_date, "Due date") if due_date else date.today() + timedelta(days=30)
            with switch_to_institution_db(skid) as tenant_session:
                # ✅ First check if fee structures exist
                fee_structures = tenant_session.query(FeeStructure).filter_by(
                    class_id=class_id,
                    academic_year_id=academic_year_id,
                    is_active=True,
                    is_mandatory=True
                ).all()
                
                if not fee_structures:
                    raise ValueError(f"No active mandatory fee structures found for class_id={class_id} and year={academic_year_id}")
                
                # Get all students in the class
                students = tenant_session.query(Student).filter_by(class_id=class_id).all()
                
                if not students:
                    raise ValueError(f"No students found in class_id={class_id}")
                
                results = []
                total_assigned = 0
                total_skipped = 0
                
                for student in students:
                    student_assigned = 0
                    student_skipped = 0
                    
                    for fee_struct in fee_structures:
                        # Check if already assigned
                        existing = tenant_session.query(StudentFee).filter_by(
                            student_id=student.user_id,
                            fee_structure_id=fee_struct.id,
                            academic_year_id=academic_year_id
                        ).first()
                        
                        if existing:
                            student_skipped += 1
                            continue
                        
                        # Create new student fee
                        student_fee = StudentFee(
                            student_id=student.user_id,
                            fee_structure_id=fee_struct.id,
                            academic_year_id=academic_year_id,
                            due_date=due,
                            total_amount=fee_struct.amount,
                            status=PaymentStatus.PENDING,
                            # has_installments=fee_struct.allows_installments
                        )
                        tenant_session.add(student_fee)
                        student_assigned += 1
                    
                    total_assigned += student_assigned
                    total_skipped += student_skipped
                    
                    results.append({
                        'student_id': student.user_id,
                        'success': True,
                        'assigned_count': student_assigned,
                        'skipped_count': student_skipped
                    })
                
                tenant_session.commit()
                
                return {
                    'total_students': len(students),
                    'total_fee_structures': len(fee_structures),
                    'total_fees_assigned': total_assigned,
                    'total_fees_skipped': total_skipped,
                    'results': results
                }
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to bulk assign fees: {str(e)}")

    

#=================================== PAYMENT MANAGEMENT ==================================
    
    @staticmethod
    def record_payment(data, skid, collected_by_id):
        """Record a fee payment"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                student_fee = tenant_session.query(StudentFee).filter_by(
                    id=data['student_fee_id']
                ).first()
                
                if not student_fee:
                    raise ValueError("Student fee record not found")
                if student_fee.has_installments:
                    raise ValueError("This fee is paid in installments. Pay an installment, or use Pay Full Balance first.")

                # Validate amount, date and mode (zero / negative / future-dated payments used to be accepted,
                # and the balance ignored discounts and late fees)
                from app.utils.validators import not_in_future, positive_amount
                amount = positive_amount(data.get('amount_paid'), "Payment amount")
                payment_day = not_in_future(data.get('payment_date') or date.today(), "Payment date")
                balance = round(float(student_fee.total_amount) - float(student_fee.discount_amount or 0)
                                + float(student_fee.late_fee or 0) - float(student_fee.paid_amount or 0), 2)
                if balance <= 0:
                    raise ValueError("This fee is already fully paid")
                if amount > balance:
                    raise ValueError(f"Payment amount exceeds the balance of {balance:.2f}")
                if data.get('payment_mode') not in PaymentMode.__members__:
                    raise ValueError(f"Payment mode must be one of: {', '.join(PaymentMode.__members__)}")
                data['amount_paid'] = amount
                data['payment_date'] = payment_day.isoformat()
                
                # Generate receipt number
                last_payment = tenant_session.query(FeePayment).order_by(
                    FeePayment.id.desc()
                ).first()
                receipt_num = f"RCP{datetime.now().strftime('%Y%m%d')}{(last_payment.id + 1 if last_payment else 1):05d}"
                
                # Create payment record
                payment = FeePayment(
                    student_fee_id=data['student_fee_id'],
                    receipt_number=receipt_num,
                    payment_date=datetime.strptime(data.get('payment_date', str(date.today())), '%Y-%m-%d').date(),
                    amount_paid=data['amount_paid'],
                    payment_mode=PaymentMode[data['payment_mode']],
                    transaction_id=data.get('transaction_id'),
                    cheque_number=data.get('cheque_number'),
                    bank_name=data.get('bank_name'),
                    collected_by=collected_by_id,
                    remarks=data.get('remarks')
                )
                tenant_session.add(payment)
                
                # Update student fee
                student_fee.paid_amount = _money(student_fee.paid_amount) + amount
                refresh_fee_status(student_fee)

                tenant_session.commit()

                return {
                    'payment': payment.to_dict(),
                    'student_fee': student_fee.to_dict(),
                    'receipt_number': receipt_num
                }
        except ValueError:
            raise
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to record payment: {str(e)}")
    
    @staticmethod
    def cancel_payment(payment_id, skid, cancelled_by_id, reason):
        """Cancel a payment: reverses it on the fee and on its installment."""
        reason = (reason or '').strip()
        if not reason:
            raise ValueError("Give a reason for cancelling the payment")
        try:
            with switch_to_institution_db(skid) as tenant_session:
                payment = tenant_session.query(FeePayment).filter_by(id=payment_id).first()
                if not payment:
                    raise ValueError("Payment not found")
                if payment.is_cancelled:
                    raise ValueError("This payment is already cancelled")

                payment.is_cancelled = True
                payment.cancelled_by = cancelled_by_id
                payment.cancelled_at = datetime.now()
                payment.cancellation_reason = reason[:500]

                amount = _money(payment.amount_paid)
                student_fee = tenant_session.query(StudentFee).filter_by(id=payment.student_fee_id).first()
                student_fee.paid_amount = max(0, round(_money(student_fee.paid_amount) - amount, 2))
                if payment.installment_id:
                    installment = tenant_session.query(FeeInstallment).filter_by(id=payment.installment_id).first()
                    if installment:
                        installment.paid_amount = max(0, round(_money(installment.paid_amount) - amount, 2))
                        refresh_installment_status(installment)
                refresh_fee_status(student_fee)

                tenant_session.commit()
                return {'payment': payment.to_dict(), 'student_fee': student_fee.to_dict()}
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to cancel payment: {str(e)}")

    @staticmethod
    def record_full_payment_after_installments(data, skid, collected_by_id):
        """Pay the remaining balance in one go (after Pay Full Balance ended the installment plan)."""
        data = dict(data or {})
        if not data.get('remarks'):
            data['remarks'] = 'Full payment for remaining balance'
        return FeeService.record_payment(data, skid, collected_by_id)


#================================ PAYMENT INSTALLMENT MANAGEMENT ===================================

    @staticmethod
    def create_installments(student_fee_id, installments, skid):
        """
        Create the installment plan for a student fee. The installments must add up to what is still owed.
            installments: [{"installment_name": "Term 1", "amount": 5000, "due_date": "2024-07-31"}, ...]
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                student_fee = tenant_session.query(StudentFee).filter_by(id=student_fee_id).first()
                if not student_fee:
                    raise ValueError("Student fee not found")
                if not isinstance(installments, list):
                    raise ValueError("installments must be a list")
                created = _replace_installments(tenant_session, student_fee, installments)
                tenant_session.commit()
                return [inst.to_dict() for inst in created]
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to create installments: {str(e)}")


    @staticmethod
    def get_fee_installments(student_fee_id, skid):
        """Get all installments for a student fee"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                installments = tenant_session.query(FeeInstallment).filter_by(
                    student_fee_id=student_fee_id
                ).order_by(FeeInstallment.installment_number).all()

                return [inst.to_dict() for inst in installments]
        except Exception as e:
            raise Exception(f"Failed to get installments: {str(e)}")


    @staticmethod
    def record_installment_payment(installment_id, data, skid, collected_by_id):
        """Record payment for a specific installment"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                installment = tenant_session.query(FeeInstallment).filter_by(id=installment_id).first()
                if not installment:
                    raise ValueError("Installment not found")
                if installment.status == PaymentStatus.CANCELLED:
                    raise ValueError("This installment was cancelled. Pay the remaining balance in full instead.")
                student_fee = tenant_session.query(StudentFee).filter_by(id=installment.student_fee_id).first()

                # Validate amount, date and mode
                from app.utils.validators import not_in_future, positive_amount
                amount = positive_amount(data.get('amount_paid'), "Payment amount")
                payment_day = not_in_future(data.get('payment_date') or date.today(), "Payment date")
                balance = round(_money(installment.amount) - _money(installment.paid_amount), 2)
                if balance <= 0:
                    raise ValueError("This installment is already fully paid")
                if amount > balance:
                    raise ValueError(f"Payment amount exceeds the installment balance of {balance:.2f}")
                fee_left = fee_balance(student_fee)
                if amount > fee_left:  # installments can never overpay the fee
                    raise ValueError(f"Payment amount exceeds the fee balance of {fee_left:.2f}")
                if data.get('payment_mode') not in PaymentMode.__members__:
                    raise ValueError(f"Payment mode must be one of: {', '.join(PaymentMode.__members__)}")

                last_payment = tenant_session.query(FeePayment).order_by(FeePayment.id.desc()).first()
                receipt_num = f"RCP{datetime.now().strftime('%Y%m%d')}{(last_payment.id + 1 if last_payment else 1):05d}"

                payment = FeePayment(
                    student_fee_id=installment.student_fee_id,
                    installment_id=installment_id,
                    receipt_number=receipt_num,
                    payment_date=payment_day,
                    amount_paid=amount,
                    payment_mode=PaymentMode[data['payment_mode']],
                    transaction_id=data.get('transaction_id'),
                    cheque_number=data.get('cheque_number'),
                    bank_name=data.get('bank_name'),
                    collected_by=collected_by_id,
                    remarks=data.get('remarks')
                )
                tenant_session.add(payment)

                installment.paid_amount = _money(installment.paid_amount) + amount
                refresh_installment_status(installment)
                student_fee.paid_amount = _money(student_fee.paid_amount) + amount
                refresh_fee_status(student_fee)

                tenant_session.commit()

                return {
                    'payment': payment.to_dict(),
                    'installment': installment.to_dict(),
                    'student_fee': student_fee.to_dict(),
                    'receipt_number': receipt_num
                }
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to record installment payment: {str(e)}")


    @staticmethod
    def auto_generate_installments(student_fee_id, num_installments, skid):
        """Split what is still owed into equal installments, every 3 months, inside the academic year."""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                student_fee = tenant_session.query(StudentFee).filter_by(id=student_fee_id).first()
                if not student_fee:
                    raise ValueError("Student fee not found")
                count = int(num_installments)
                balance = fee_balance(student_fee)
                each = round(balance / count, 2)
                amounts = [each] * count
                amounts[-1] = round(balance - each * (count - 1), 2)
                base = student_fee.due_date or date.today()
                year = _year_range(tenant_session, student_fee)
                plan = []
                for i, amount in enumerate(amounts):
                    due = _add_months(base, 3 * i)
                    if year:
                        due = min(max(due, year[0]), year[1])
                    plan.append({'installment_name': f"Installment {i + 1}", 'amount': amount, 'due_date': due.isoformat()})
                created = _replace_installments(tenant_session, student_fee, plan)
                tenant_session.commit()
                return [inst.to_dict() for inst in created]
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to auto-generate installments: {str(e)}")


    @staticmethod
    def auto_generate_recurring_installments(student_fee_id, skid, preview=False):
        """
        Installments for a recurring fee (e.g. monthly tuition): one per period by the calendar, covering
        only what is still owed, with no due date past the academic year. preview=True returns the plan unsaved.
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                student_fee = tenant_session.query(StudentFee).filter_by(id=student_fee_id).first()
                if not student_fee:
                    raise ValueError("Student fee not found")
                fee_structure = tenant_session.query(FeeStructure).filter_by(id=student_fee.fee_structure_id).first()
                if not fee_structure:
                    raise ValueError("Fee structure not found")
                if not fee_structure.is_recurring:
                    raise ValueError("This is not a recurring fee")
                if not fee_structure.allows_installments:
                    raise ValueError("This fee does not allow installments")
                if fee_balance(student_fee) <= 0:
                    raise ValueError("This fee is already fully paid")

                plan = _recurring_plan(tenant_session, student_fee, fee_structure)
                if preview:
                    return plan
                created = _replace_installments(tenant_session, student_fee, plan)
                tenant_session.commit()
                return [inst.to_dict() for inst in created]
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to auto-generate recurring installments: {str(e)}")


    @staticmethod
    def convert_remaining_to_full_payment(student_fee_id, skid):
        """
        End the installment plan: unpaid installments are cancelled and the rest can be paid in one go.
        Scenario: student paid 3 months in installments, wants to pay the rest in full.
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                student_fee = tenant_session.query(StudentFee).filter_by(id=student_fee_id).first()
                if not student_fee:
                    raise ValueError("Student fee not found")

                open_installments = tenant_session.query(FeeInstallment).filter(
                    FeeInstallment.student_fee_id == student_fee_id,
                    FeeInstallment.status.in_([PaymentStatus.PENDING, PaymentStatus.PARTIAL]),
                ).all()
                if not student_fee.has_installments and not open_installments:
                    raise ValueError("This fee isn't on an installment plan")

                for inst in open_installments:
                    inst.status = PaymentStatus.CANCELLED
                student_fee.has_installments = False  # also un-sticks a fee flagged with no installments
                remaining = fee_balance(student_fee)

                tenant_session.commit()

                return {
                    'remaining_balance': remaining,
                    'message': f'Installments cancelled. Student can now pay remaining \u20b9{remaining:.2f} in full.',
                    'cancelled_installments': len(open_installments)
                }
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to convert to full payment: {str(e)}")


#================================ FEE REPORTS & ANALYTICS =========================================
    
    @staticmethod
    def get_student_fee_summary(student_id, academic_year_id, skid):
        """Get complete fee summary for a student"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                student_fees = tenant_session.query(
                    StudentFee, FeeStructure
                ).join(
                    FeeStructure, StudentFee.fee_structure_id == FeeStructure.id
                ).filter(
                    StudentFee.student_id == student_id,
                    StudentFee.academic_year_id == academic_year_id
                ).order_by(StudentFee.due_date, StudentFee.id).all()  # rows kept jumping after a payment (QA C29)

                total_amount = 0
                total_paid = 0
                total_discount = 0
                total_late_fee = 0
                
                fees_list = []
                for student_fee, fee_structure in student_fees:
                    fee_dict = student_fee.to_dict()
                    fee_dict['fee_structure'] = fee_structure.to_dict()
                    
                    # Get payments
                    payments = tenant_session.query(FeePayment).filter_by(
                        student_fee_id=student_fee.id,
                        is_cancelled=False
                    ).all()
                    fee_dict['payments'] = [p.to_dict() for p in payments]
                    # who took each payment, for the receipt's "Collected By"
                    collector_ids = {p.collected_by for p in payments if p.collected_by}
                    if collector_ids:
                        names = {u.id: f"{u.first_name} {u.last_name or ''}".strip()
                                 for u in tenant_session.query(InstitutionUsers).filter(InstitutionUsers.id.in_(collector_ids)).all()}
                        for pd in fee_dict['payments']:
                            pd['collected_by_name'] = names.get(pd.get('collected_by'))
                    
                    fees_list.append(fee_dict)
                    total_amount += float(student_fee.total_amount)
                    total_paid += float(student_fee.paid_amount)
                    total_discount += float(student_fee.discount_amount or 0)
                    total_late_fee += float(student_fee.late_fee or 0)
                
                return {
                    'student_id': student_id,
                    'academic_year_id': academic_year_id,
                    'total_amount': total_amount,
                    'total_paid': total_paid,
                    'total_discount': total_discount,
                    'total_late_fee': total_late_fee,
                    'balance': total_amount - total_paid - total_discount + total_late_fee,
                    'fees': fees_list
                }
        except Exception as e:
            raise Exception(f"Failed to get fee summary: {str(e)}")
    
    @staticmethod
    def get_fee_collection_report(skid, start_date=None, end_date=None, class_id=None):
        """Get fee collection report"""
        try:
            with switch_to_institution_db(skid) as tenant_session:
                query = tenant_session.query(
                    FeePayment,
                    StudentFee,
                    Student,
                    InstitutionUsers
                ).join(
                    StudentFee, FeePayment.student_fee_id == StudentFee.id
                ).join(
                    Student, StudentFee.student_id == Student.user_id
                ).join(
                    InstitutionUsers, Student.user_id == InstitutionUsers.id
                ).filter(
                    FeePayment.is_cancelled == False
                )
                
                if start_date:
                    query = query.filter(FeePayment.payment_date >= start_date)
                if end_date:
                    query = query.filter(FeePayment.payment_date <= end_date)
                if class_id:
                    query = query.filter(Student.class_id == class_id)
                
                results = query.order_by(FeePayment.payment_date.desc(), FeePayment.id.desc()).all()

                # names for the report rows: class/section, fee, and who collected the payment
                classes = {c.id: c.class_name for c in tenant_session.query(Class).all()}
                sections = {s.id: s.section_name for s in tenant_session.query(Section).all()}
                structure_ids = {sf.fee_structure_id for _, sf, _, _ in results if sf.fee_structure_id}
                fee_names = {fs.id: fs.fee_name for fs in tenant_session.query(FeeStructure).filter(FeeStructure.id.in_(structure_ids)).all()} if structure_ids else {}
                collector_ids = {p.collected_by for p, _, _, _ in results if p.collected_by}
                collectors = {u.id: f"{u.first_name} {u.last_name or ''}".strip() for u in tenant_session.query(InstitutionUsers).filter(InstitutionUsers.id.in_(collector_ids)).all()} if collector_ids else {}

                total_collected = 0
                collection_by_mode = {}
                payments_list = []
                
                for payment, student_fee, student, user in results:
                    payment_dict = payment.to_dict()
                    payment_dict['student_name'] = f"{user.first_name} {user.last_name or ''}".strip()
                    payment_dict['student_id'] = student.user_id
                    payment_dict['admission_number'] = student.admission_number
                    payment_dict['class'] = classes.get(student.class_id)
                    payment_dict['section'] = sections.get(student.section_id)
                    payment_dict['fee_name'] = fee_names.get(student_fee.fee_structure_id)
                    payment_dict['collected_by_name'] = collectors.get(payment.collected_by)
                    payment_dict['payment_mode_label'] = payment.payment_mode.value if payment.payment_mode else None
                    payments_list.append(payment_dict)
                    
                    total_collected += float(payment.amount_paid)
                    
                    mode = payment.payment_mode.value if payment.payment_mode else 'Unknown'
                    collection_by_mode[mode] = round(collection_by_mode.get(mode, 0) + float(payment.amount_paid), 2)
                
                return {
                    'total_collected': round(total_collected, 2),
                    'total_transactions': len(payments_list),
                    'collection_by_mode': collection_by_mode,
                    'payments': payments_list
                }
        except Exception as e:
            raise Exception(f"Failed to get collection report: {str(e)}")
    
    @staticmethod
    def get_defaulters_list(skid, academic_year_id, as_of_date=None):
        """
        Students with overdue fees: a fee past its due date with a balance, or an installment plan with
        unpaid installments past their due date. One row per overdue fee.
        """
        from app.models.tenant.StudentParent import StudentParent
        try:
            with switch_to_institution_db(skid) as tenant_session:
                as_of = as_of_date or date.today()
                rows = tenant_session.query(StudentFee, InstitutionUsers, Student, FeeStructure).join(
                    InstitutionUsers, StudentFee.student_id == InstitutionUsers.id
                ).join(
                    Student, Student.user_id == StudentFee.student_id
                ).outerjoin(
                    FeeStructure, FeeStructure.id == StudentFee.fee_structure_id
                ).filter(StudentFee.academic_year_id == academic_year_id).all()

                classes = {c.id: c.class_name for c in tenant_session.query(Class).all()}
                sections = {sec.id: sec.section_name for sec in tenant_session.query(Section).all()}
                defaulters = []
                for student_fee, user, student, structure in rows:
                    balance = fee_balance(student_fee)
                    if balance <= 0:
                        continue
                    if student_fee.has_installments:
                        late = tenant_session.query(FeeInstallment).filter(
                            FeeInstallment.student_fee_id == student_fee.id,
                            FeeInstallment.status.in_([PaymentStatus.PENDING, PaymentStatus.PARTIAL]),
                            FeeInstallment.due_date < as_of,
                        ).all()
                        if not late:
                            continue
                        overdue = round(sum(_money(i.amount) - _money(i.paid_amount) for i in late), 2)
                        first_due = min(i.due_date for i in late)
                    else:
                        if not student_fee.due_date or student_fee.due_date >= as_of:
                            continue
                        overdue, first_due = balance, student_fee.due_date

                    parent_phone = None
                    link = tenant_session.query(StudentParent).filter_by(student_user_id=student.user_id).first()
                    if link:
                        parent = tenant_session.query(InstitutionUsers).filter_by(id=link.parent_user_id).first()
                        parent_phone = parent.phone if parent else None

                    defaulters.append({
                        'student_id': student.user_id,
                        'student_fee_id': student_fee.id,
                        'student_name': f"{user.first_name} {user.last_name or ''}".strip(),
                        'admission_number': student.admission_number,
                        'class': classes.get(student.class_id),
                        'section': sections.get(student.section_id),
                        'phone': user.phone,
                        'parent_phone': parent_phone,
                        'fee_name': structure.fee_name if structure else None,
                        'total_amount': _money(student_fee.total_amount),
                        'paid_amount': _money(student_fee.paid_amount),
                        'discount_amount': _money(student_fee.discount_amount),
                        'balance': balance,
                        'overdue_amount': overdue,
                        'due_date': first_due.isoformat(),
                        'days_overdue': (as_of - first_due).days,
                        'status': getattr(student_fee.status, 'value', student_fee.status),
                    })

                defaulters.sort(key=lambda d: (-d['days_overdue'], d['student_name']))
                return {
                    'as_of_date': as_of.isoformat(),
                    'total_defaulters': len({d['student_id'] for d in defaulters}),
                    'total_overdue_amount': round(sum(d['overdue_amount'] for d in defaulters), 2),
                    'total_pending_amount': round(sum(d['balance'] for d in defaulters), 2),
                    'defaulters': defaulters
                }
        except Exception as e:
            raise Exception(f"Failed to get defaulters list: {str(e)}")


#=================================== DISCOUNT MANAGEMENT ===================================
    
    @staticmethod
    def apply_discount(data, skid, approved_by_id):
        """
        Give a student a discount on chosen fees (default: all their fees for the year).
        PERCENTAGE takes that share of each fee; FIXED is one amount spread over the fees (earliest due first).
        A discount never exceeds what is still owed; installment plans shrink from their last installments.
        """
        from app.utils.validators import positive_amount, to_date
        from app.models.tenant.AcademicYear import AcademicYear
        try:
            with switch_to_institution_db(skid) as tenant_session:
                student_id = int(data.get('student_id') or 0)
                if not tenant_session.query(Student).filter_by(user_id=student_id).first():
                    raise ValueError("Student not found")
                name = (str(data.get('discount_name') or '')).strip()
                if not name:
                    raise ValueError("Give the discount a name")
                kind = str(data.get('discount_type') or '').upper()
                if kind not in ('PERCENTAGE', 'FIXED'):
                    raise ValueError("Discount type must be PERCENTAGE or FIXED")
                value = positive_amount(data.get('discount_value'), "Discount value")
                if kind == 'PERCENTAGE' and value > 100:
                    raise ValueError("A percentage discount can't be more than 100")

                year_id = data.get('academic_year_id')
                if not year_id:
                    current = tenant_session.query(AcademicYear).filter_by(is_current=True).first()
                    year_id = current.id if current else None
                if not year_id:
                    raise ValueError("Choose the academic year")
                valid_from = to_date(data.get('valid_from') or date.today(), "Valid from")
                valid_to = to_date(data['valid_to'], "Valid to") if data.get('valid_to') else None
                if valid_to and valid_to < valid_from:
                    raise ValueError("'Valid to' can't be before 'Valid from'")

                query = tenant_session.query(StudentFee).filter_by(student_id=student_id, academic_year_id=year_id)
                fee_ids = data.get('student_fee_ids') or data.get('applicable_fees') or []
                if fee_ids:
                    fee_ids = [int(i) for i in fee_ids]
                    query = query.filter(StudentFee.id.in_(fee_ids))
                fees = query.order_by(StudentFee.due_date, StudentFee.id).all()
                if fee_ids and len(fees) != len(set(fee_ids)):
                    raise ValueError("Some of the chosen fees don't belong to this student for that year")
                fees = [f for f in fees if fee_balance(f) > 0]
                if not fees:
                    raise ValueError("Nothing is left to pay on the chosen fees")

                if kind == 'PERCENTAGE':
                    shares = [round(min(_money(f.total_amount) * value / 100, fee_balance(f)), 2) for f in fees]
                else:
                    owed = round(sum(fee_balance(f) for f in fees), 2)
                    if value > owed:
                        raise ValueError(f"The discount ({value:.2f}) is more than what is still owed on the chosen fees ({owed:.2f})")
                    shares, left = [], value
                    for f in fees:
                        take = round(min(left, fee_balance(f)), 2)
                        shares.append(take)
                        left = round(left - take, 2)

                applied = []
                for f, share in zip(fees, shares):
                    if share <= 0:
                        continue
                    f.discount_amount = round(_money(f.discount_amount) + share, 2)
                    if f.has_installments:  # keep the plan equal to what is owed
                        open_insts = tenant_session.query(FeeInstallment).filter(
                            FeeInstallment.student_fee_id == f.id,
                            FeeInstallment.status.in_([PaymentStatus.PENDING, PaymentStatus.PARTIAL]),
                        ).order_by(FeeInstallment.installment_number).all()
                        amounts = [_money(i.amount) for i in open_insts]
                        _shrink_from_end(amounts, share, [_money(i.paid_amount) for i in open_insts])
                        for inst, amount in zip(open_insts, amounts):
                            inst.amount = amount
                            refresh_installment_status(inst)
                    refresh_fee_status(f)
                    structure = tenant_session.query(FeeStructure).filter_by(id=f.fee_structure_id).first()
                    applied.append({'student_fee_id': f.id, 'fee_name': structure.fee_name if structure else None,
                                    'discount_added': share, 'balance_now': fee_balance(f)})

                discount = FeeDiscount(
                    student_id=student_id,
                    academic_year_id=year_id,
                    discount_name=name[:100],
                    discount_type=kind,
                    discount_value=value,
                    applicable_fees=json.dumps([a['student_fee_id'] for a in applied]),
                    valid_from=valid_from,
                    valid_to=valid_to,
                    approved_by=approved_by_id,
                    reason=data.get('reason')
                )
                tenant_session.add(discount)
                tenant_session.commit()
                return {'discount': discount.to_dict(), 'applied': applied,
                        'total_discount_added': round(sum(a['discount_added'] for a in applied), 2)}
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to apply discount: {str(e)}")


    @staticmethod
    def delete_all_class_fees(class_id, academic_year_id, skid):
        """
        Delete all fee structures for a class and academic year
        Args:
            class_id: Class ID
            academic_year_id: Academic year
            skid: Institution identifier
        Returns:
            Success message with count
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                # Get all fee structures for the class
                fee_structures = tenant_session.query(FeeStructure).filter_by(
                    class_id=class_id,
                    academic_year_id=academic_year_id
                ).all()
                
                if not fee_structures:
                    raise ValueError(f"No fee structures found for this class")
                
                # Check if any fee is assigned to students
                fee_ids = [fee.id for fee in fee_structures]
                assigned_count = tenant_session.query(StudentFee).filter(
                    StudentFee.fee_structure_id.in_(fee_ids)
                ).count()
                
                if assigned_count > 0:
                    raise ValueError(
                        f"Cannot delete fee structures. They are assigned to {assigned_count} student(s). "
                        f"Please remove student assignments first."
                    )
                
                # Delete all fee structures
                deleted_count = len(fee_structures)
                for fee in fee_structures:
                    tenant_session.delete(fee)
                
                tenant_session.commit()
                
                return {
                    'message': f'{deleted_count} fee structure(s) deleted successfully',
                    'deleted_count': deleted_count
                }
                
        except ValueError as ve:
            raise ve
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to delete fee structures: {str(e)}")
    

    @staticmethod
    def search_students_for_fees(search_query, skid, academic_year_id, class_id=None):
        """
        Universal student search for fee collection
        Search by name, phone number, or roll number
        
        Args:
            search_query: Search term (name/phone/roll_no)
            skid: Institution identifier
            academic_year_id: Academic year for fee filtering
            class_id: Optional class filter
        
        Returns:
            List of students with fee summary
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                # Build query with joins
                query = tenant_session.query(
                    Student, InstitutionUsers, Class, Section
                ).join(
                    InstitutionUsers, Student.user_id == InstitutionUsers.id
                ).outerjoin(
                    Class, Student.class_id == Class.id
                ).outerjoin(
                    Section, Student.section_id == Section.id
                )
                
                # Multi-field search using OR condition
                search_conditions = or_(
                    # Search by name (first name, last name, or full name)
                    InstitutionUsers.first_name.ilike(f'%{search_query}%'),
                    InstitutionUsers.last_name.ilike(f'%{search_query}%'),
                    func.concat(InstitutionUsers.first_name, ' ', InstitutionUsers.last_name).ilike(f'%{search_query}%'),
                    
                    # Search by phone number
                    InstitutionUsers.phone.ilike(f'%{search_query}%'),
                    
                    # Search by roll number (student_id field)
                    Student.roll_no.ilike(f'%{search_query}%')
                )
                
                query = query.filter(search_conditions)
                
                # Optional class filter
                if class_id:
                    query = query.filter(Student.class_id == class_id)
                
                # Limit results to 20
                results = query.limit(20).all()
                
                students_list = []
                for student, user, class_info, section_info in results:
                    # Get fee summary for this student
                    fee_summary = tenant_session.query(
                        func.count(StudentFee.id).label('total_fees'),
                        func.sum(StudentFee.total_amount).label('total_amount'),
                        func.sum(StudentFee.paid_amount).label('paid_amount'),
                        func.sum(StudentFee.discount_amount).label('discount_amount')
                    ).filter(
                        StudentFee.student_id == student.user_id,
                        StudentFee.academic_year_id == academic_year_id
                    ).first()
                    
                    # Calculate balance
                    total_amount = float(fee_summary.total_amount or 0)
                    paid_amount = float(fee_summary.paid_amount or 0)
                    discount_amount = float(fee_summary.discount_amount or 0)
                    balance = total_amount - paid_amount - discount_amount
                    
                    students_list.append({
                        'user_id': student.user_id,
                        'roll_no': student.roll_no,  # Roll number
                        'name': f"{user.first_name} {user.last_name}",
                        'phone': user.phone,
                        'email': user.email,
                        'class': class_info.class_name if class_info else 'N/A',
                        'section': section_info.section_name if section_info else 'N/A',
                        'class_id': student.class_id,
                        'section_id': student.section_id,
                        'fee_summary': {
                            'total_fees': int(fee_summary.total_fees or 0),
                            'total_amount': total_amount,
                            'paid_amount': paid_amount,
                            'discount_amount': discount_amount,
                            'balance': balance
                        }
                    })
                
                return students_list
                
        except Exception as e:
            raise Exception(f"Failed to search students: {str(e)}")

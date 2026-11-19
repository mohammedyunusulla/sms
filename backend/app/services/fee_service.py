from app.models.tenant import Class, Student, SchoolUsers
from app.models.tenant.Sections import Section
from app.models.tenant.FeeModels import (
    FeeStructure, StudentFee, FeePayment, FeeDiscount, 
     FeeType, PaymentMode, PaymentStatus, FeeInstallment, RecurrenceType
)
from app.utils.db_manager import switch_to_school_db
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_, extract
from decimal import Decimal
import json

class FeeService:
    
    @staticmethod
    def create_fee_structure(data, skid):
        """Create fee structure for a class"""
        from app.utils.validators import positive_amount
        try:
            with switch_to_school_db(skid) as tenant_session:
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
            with switch_to_school_db(skid) as tenant_session:
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
            with switch_to_school_db(skid) as tenant_session:
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
            with switch_to_school_db(skid) as tenant_session:
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
            with switch_to_school_db(skid) as tenant_session:
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
                    print(f"Found {len(fee_structures)} fee structures for class_id={student.class_id}, year={academic_year_id}")
                    
                    for fee_struct in fee_structures:
                        # Check if already assigned
                        existing = tenant_session.query(StudentFee).filter_by(
                            student_id=student_id,
                            fee_structure_id=fee_struct.id,
                            academic_year_id=academic_year_id
                        ).first()
                        
                        if existing:
                            print(f"Fee {fee_struct.fee_name} already assigned to student {student_id}")
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
                        print(f"Assigned fee {fee_struct.fee_name} to student {student_id}")
                
                tenant_session.commit()
                
                return {
                    'assigned_count': len(assigned_fees),
                    'fees': [fee.to_dict() for fee in assigned_fees]
                }
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to assign fees: {str(e)}")

    
    @staticmethod
    def bulk_assign_fees_to_class(class_id, academic_year_id, skid):
        """Assign fees to all students in a class with detailed results"""
        try:
            with switch_to_school_db(skid) as tenant_session:
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
                            due_date=date.today() + timedelta(days=30),
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
            with switch_to_school_db(skid) as tenant_session:
                student_fee = tenant_session.query(StudentFee).filter_by(
                    id=data['student_fee_id']
                ).first()
                
                if not student_fee:
                    raise ValueError("Student fee record not found")

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
                student_fee.paid_amount = float(student_fee.paid_amount or 0) + float(data['amount_paid'])
                
                # Update status
                total_payable = float(student_fee.total_amount) - float(student_fee.discount_amount or 0)
                if student_fee.paid_amount >= total_payable:
                    student_fee.status = PaymentStatus.PAID
                elif student_fee.paid_amount > 0:
                    student_fee.status = PaymentStatus.PARTIAL
                
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
        """Cancel a payment"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                payment = tenant_session.query(FeePayment).filter_by(id=payment_id).first()
                if not payment:
                    raise ValueError("Payment not found")
                
                if payment.is_cancelled:
                    raise ValueError("Payment already cancelled")
                
                # Mark payment as cancelled
                payment.is_cancelled = True
                payment.cancelled_by = cancelled_by_id
                payment.cancelled_at = datetime.now()
                payment.cancellation_reason = reason
                
                # Update student fee
                student_fee = tenant_session.query(StudentFee).filter_by(
                    id=payment.student_fee_id
                ).first()
                student_fee.paid_amount = float(student_fee.paid_amount) - float(payment.amount_paid)
                
                # Update status
                if student_fee.paid_amount == 0:
                    student_fee.status = PaymentStatus.PENDING
                elif student_fee.paid_amount < student_fee.total_amount:
                    student_fee.status = PaymentStatus.PARTIAL
                
                tenant_session.commit()
                return payment.to_dict()
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to cancel payment: {str(e)}")
    
    @staticmethod
    def record_full_payment_after_installments(data, skid, collected_by_id):
        """
        Record full payment for remaining amount after some installments paid
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                student_fee = tenant_session.query(StudentFee).filter_by(
                    id=data['student_fee_id']
                ).first()
                
                if not student_fee:
                    raise ValueError("Student fee record not found")
                
                # Calculate actual balance (considering discounts)
                balance = float(student_fee.total_amount) - float(student_fee.paid_amount or 0) - float(student_fee.discount_amount or 0)
                
                if float(data['amount_paid']) > balance:
                    raise ValueError(f"Payment amount exceeds balance. Balance: ₹{balance:.2f}")
                
                # Generate receipt number
                last_payment = tenant_session.query(FeePayment).order_by(
                    FeePayment.id.desc()
                ).first()
                receipt_num = f"RCP{datetime.now().strftime('%Y%m%d')}{(last_payment.id + 1 if last_payment else 1):05d}"
                
                # Create payment record (without installment_id for full payment)
                payment = FeePayment(
                    student_fee_id=data['student_fee_id'],
                    installment_id=None,  # Full payment, not linked to installment
                    receipt_number=receipt_num,
                    payment_date=datetime.strptime(data.get('payment_date', str(date.today())), '%Y-%m-%d').date(),
                    amount_paid=data['amount_paid'],
                    payment_mode=PaymentMode[data['payment_mode']],
                    transaction_id=data.get('transaction_id'),
                    cheque_number=data.get('cheque_number'),
                    bank_name=data.get('bank_name'),
                    collected_by=collected_by_id,
                    remarks=data.get('remarks', 'Full payment for remaining balance')
                )
                
                tenant_session.add(payment)
                
                # Update student fee
                student_fee.paid_amount = float(student_fee.paid_amount or 0) + float(data['amount_paid'])
                
                # Update status
                total_payable = float(student_fee.total_amount) - float(student_fee.discount_amount or 0)
                if student_fee.paid_amount >= total_payable:
                    student_fee.status = 'PAID'
                    student_fee.has_installments = False  # Mark as complete
                elif student_fee.paid_amount > 0:
                    student_fee.status = 'PARTIAL'
                
                tenant_session.commit()
                
                return {
                    'payment': payment.to_dict(),
                    'student_fee': student_fee.to_dict(),
                    'receipt_number': receipt_num
                }
        
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to record payment: {str(e)}")
    

#================================ PAYMENT INSTALLMENT MANAGEMENT ===================================

    @staticmethod
    def create_installments(student_fee_id, installments, skid):
        """
        Create installment plan for a student fee
        
        Args:
            student_fee_id: Student fee ID
            installments: List of installments
                [{
                    "installment_name": "Term 1",
                    "amount": 5000,
                    "due_date": "2024-07-31"
                }, ...]
            skid: School identifier
        
        Returns:
            List of created installments
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                student_fee = tenant_session.query(StudentFee).filter_by(id=student_fee_id).first()
                
                if not student_fee:
                    raise ValueError("Student fee not found")
                
                # Validate total installment amount matches fee amount
                total_installment = sum(float(inst['amount']) for inst in installments)
                if total_installment != float(student_fee.total_amount):
                    raise ValueError(
                        f"Total installment amount ({total_installment}) must equal fee amount ({student_fee.total_amount})"
                    )
                
                # Delete existing installments if any
                tenant_session.query(FeeInstallment).filter_by(student_fee_id=student_fee_id).delete()
                
                # Create new installments
                installments = []
                for idx, inst_data in enumerate(installments, start=1):
                    installment = FeeInstallment(
                        student_fee_id=student_fee_id,
                        installment_number=idx,
                        installment_name=inst_data['installment_name'],
                        amount=inst_data['amount'],
                        due_date=datetime.strptime(inst_data['due_date'], '%Y-%m-%d').date()
                    )
                    tenant_session.add(installment)
                    installments.append(installment)
                
                # Mark student fee as having installments
                student_fee.has_installments = True
                
                tenant_session.commit()
                
                return [inst.to_dict() for inst in installments]
                
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to create installments: {str(e)}")
    
    
    @staticmethod
    def get_fee_installments(student_fee_id, skid):
        """Get all installments for a student fee"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                installments = tenant_session.query(FeeInstallment).filter_by(
                    student_fee_id=student_fee_id
                ).order_by(FeeInstallment.installment_number).all()
                
                return [inst.to_dict() for inst in installments]
        except Exception as e:
            raise Exception(f"Failed to get installments: {str(e)}")
    
    
    @staticmethod
    def record_installment_payment(installment_id, data, skid, collected_by_id):
        """
        Record payment for a specific installment
        
        Args:
            installment_id: Installment ID
            data: Payment data
            skid: School identifier
            collected_by_id: User ID who collected payment
        
        Returns:
            Payment and installment details
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                installment = tenant_session.query(FeeInstallment).filter_by(id=installment_id).first()
                
                if not installment:
                    raise ValueError("Installment not found")

                # Validate amount, date and mode
                from app.utils.validators import not_in_future, positive_amount
                amount = positive_amount(data.get('amount_paid'), "Payment amount")
                payment_day = not_in_future(data.get('payment_date') or date.today(), "Payment date")
                balance = round(float(installment.amount) - float(installment.paid_amount or 0), 2)
                if balance <= 0:
                    raise ValueError("This installment is already fully paid")
                if amount > balance:
                    raise ValueError(f"Payment amount exceeds the installment balance of {balance:.2f}")
                if data.get('payment_mode') not in PaymentMode.__members__:
                    raise ValueError(f"Payment mode must be one of: {', '.join(PaymentMode.__members__)}")
                data['amount_paid'] = amount
                data['payment_date'] = payment_day.isoformat()
                
                # Generate receipt number
                last_payment = tenant_session.query(FeePayment).order_by(FeePayment.id.desc()).first()
                receipt_num = f"RCP{datetime.now().strftime('%Y%m%d')}{(last_payment.id + 1 if last_payment else 1):05d}"
                
                # Create payment record
                payment = FeePayment(
                    student_fee_id=installment.student_fee_id,
                    installment_id=installment_id,  # Link to installment
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
                
                # Update installment
                installment.paid_amount = float(installment.paid_amount or 0) + float(data['amount_paid'])
                
                # Update installment status
                if installment.paid_amount >= installment.amount:
                    installment.status = PaymentStatus.PAID
                elif installment.paid_amount > 0:
                    installment.status = PaymentStatus.PARTIAL
                
                # Update parent student fee
                student_fee = tenant_session.query(StudentFee).filter_by(id=installment.student_fee_id).first()
                student_fee.paid_amount = float(student_fee.paid_amount or 0) + float(data['amount_paid'])
                
                # Update student fee status
                total_payable = float(student_fee.total_amount) - float(student_fee.discount_amount or 0)
                if student_fee.paid_amount >= total_payable:
                    student_fee.status = PaymentStatus.PAID
                elif student_fee.paid_amount > 0:
                    student_fee.status = PaymentStatus.PARTIAL
                
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
            tenant_session.rollback()
            raise Exception(f"Failed to record installment payment: {str(e)}")
    
    
    @staticmethod
    def auto_generate_installments(student_fee_id, num_installments, skid):
        """
        Auto-generate equal installments
        
        Args:
            student_fee_id: Student fee ID
            num_installments: Number of installments (2, 3, 4...)
            skid: School identifier
        
        Returns:
            List of created installments
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                student_fee = tenant_session.query(StudentFee).filter_by(id=student_fee_id).first()
                
                if not student_fee:
                    raise ValueError("Student fee not found")
                
                # Calculate installment amount
                total_amount = float(student_fee.total_amount)
                installment_amount = total_amount / num_installments
                
                # Generate due dates (every 3 months from admission date or today)
                base_date = student_fee.due_date or date.today()
                
                installment_plan = []
                for i in range(num_installments):
                    # Calculate due date (every 3 months)
                    due_date = base_date + timedelta(days=90 * i)
                    
                    installment_plan.append({
                        'installment_name': f"Installment {i+1}",
                        'amount': round(installment_amount, 2),
                        'due_date': due_date.isoformat()
                    })
                
                # Adjust last installment for rounding differences
                total_planned = sum(inst['amount'] for inst in installment_plan)
                if total_planned != total_amount:
                    installment_plan[-1]['amount'] += (total_amount - total_planned)
                
                return FeeService.create_installments(student_fee_id, installment_plan, skid)
                
        except Exception as e:
            raise Exception(f"Failed to auto-generate installments: {str(e)}")
    
    
    # Replace the auto_generate_recurring_installments function in fee_service.py

    @staticmethod
    def auto_generate_recurring_installments(student_fee_id, skid):
        """
        Auto-generate installments based on recurrence type
        For recurring fees like monthly tuition
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                student_fee = tenant_session.query(StudentFee).filter_by(id=student_fee_id).first()
                if not student_fee:
                    raise ValueError("Student fee not found")
                
                fee_structure = tenant_session.query(FeeStructure).filter_by(
                    id=student_fee.fee_structure_id
                ).first()
                
                if not fee_structure:
                    raise ValueError("Fee structure not found")
                
                if not fee_structure.is_recurring:
                    raise ValueError("This is not a recurring fee")
                
                if not fee_structure.allows_installments:
                    raise ValueError("This fee does not allow installments")
                
                # Delete existing installments
                tenant_session.query(FeeInstallment).filter_by(student_fee_id=student_fee_id).delete()
                tenant_session.commit()  # ✅ Commit the deletion first
                
                # Generate installments based on recurrence type
                base_date = student_fee.due_date or date.today()
                installments_to_create = []
                
                # Get recurrence details
                recurrence_amount = float(fee_structure.recurrence_amount or 0)
                recurrence_months = int(fee_structure.recurrence_months or 0)
                recurrence_type = fee_structure.recurrence_type
                
                if recurrence_type == 'MONTHLY':
                    for i in range(recurrence_months):
                        due_date = base_date + timedelta(days=30 * i)
                        installments_to_create.append(
                            FeeInstallment(
                                student_fee_id=student_fee_id,
                                installment_number=i + 1,
                                installment_name=f"Month {i+1}",
                                amount=recurrence_amount,
                                due_date=due_date
                            )
                        )
                
                elif recurrence_type == 'QUARTERLY':
                    for i in range(recurrence_months):
                        due_date = base_date + timedelta(days=90 * i)
                        installments_to_create.append(
                            FeeInstallment(
                                student_fee_id=student_fee_id,
                                installment_number=i + 1,
                                installment_name=f"Quarter {i+1}",
                                amount=recurrence_amount,
                                due_date=due_date
                            )
                        )
                
                elif recurrence_type == 'YEARLY':
                    for i in range(recurrence_months):
                        due_date = base_date + timedelta(days=365 * i)
                        installments_to_create.append(
                            FeeInstallment(
                                student_fee_id=student_fee_id,
                                installment_number=i + 1,
                                installment_name=f"Year {i+1}",
                                amount=recurrence_amount,
                                due_date=due_date
                            )
                        )
                
                elif recurrence_type == 'ONE_TIME':
                    # For one-time fees, create a single installment
                    installments_to_create.append(
                        FeeInstallment(
                            student_fee_id=student_fee_id,
                            installment_number=1,
                            installment_name="Full Payment",
                            amount=float(fee_structure.amount),
                            due_date=base_date
                        )
                    )
                
                # Validate total before creating
                total_installment = sum(float(inst.amount) for inst in installments_to_create)
                expected_total = float(student_fee.total_amount)
                
                # Handle floating point rounding issues
                if abs(total_installment - expected_total) > 0.01:
                    # Adjust last installment to match total exactly
                    difference = expected_total - total_installment
                    if installments_to_create:
                        installments_to_create[-1].amount += difference
                
                # Add all installments to session
                for installment in installments_to_create:
                    tenant_session.add(installment)
                
                # Mark student fee as having installments
                student_fee.has_installments = True
                
                # Commit everything
                tenant_session.commit()
                
                # Return the created installments
                return [inst.to_dict() for inst in installments_to_create]
        
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to auto-generate recurring installments: {str(e)}")


    @staticmethod
    def convert_remaining_to_full_payment(student_fee_id, skid):
        """
        Convert remaining installments to full payment
        Scenario: Student paid 3 months in installments, wants to pay rest in full
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                student_fee = tenant_session.query(StudentFee).filter_by(id=student_fee_id).first()
                if not student_fee:
                    raise ValueError("Student fee not found")
                
                # Get all installments
                installments = tenant_session.query(FeeInstallment).filter_by(
                    student_fee_id=student_fee_id
                ).all()
                
                if not installments:
                    raise ValueError("No installments found for this fee")
                
                # Calculate remaining balance from unpaid/partial installments
                remaining_balance = 0
                cancelled_count = 0
                
                for inst in installments:
                    if inst.status in ['PENDING', 'PARTIAL']:
                        remaining_balance += float(inst.amount) - float(inst.paid_amount or 0)
                        inst.status = 'CANCELLED'
                        cancelled_count += 1
                
                # Mark fee as no longer having installments
                student_fee.has_installments = False
                
                tenant_session.commit()
                
                return {
                    'remaining_balance': remaining_balance,
                    'message': f'Installments cancelled. Student can now pay remaining ₹{remaining_balance:.2f} in full.',
                    'cancelled_installments': cancelled_count
                }
        
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to convert to full payment: {str(e)}")


    
#================================ FEE REPORTS & ANALYTICS =========================================
    
    @staticmethod
    def get_student_fee_summary(student_id, academic_year_id, skid):
        """Get complete fee summary for a student"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                student_fees = tenant_session.query(
                    StudentFee, FeeStructure
                ).join(
                    FeeStructure, StudentFee.fee_structure_id == FeeStructure.id
                ).filter(
                    StudentFee.student_id == student_id,
                    StudentFee.academic_year_id == academic_year_id
                ).all()
                
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
            with switch_to_school_db(skid) as tenant_session:
                query = tenant_session.query(
                    FeePayment,
                    StudentFee,
                    Student,
                    SchoolUsers
                ).join(
                    StudentFee, FeePayment.student_fee_id == StudentFee.id
                ).join(
                    Student, StudentFee.student_id == Student.user_id
                ).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).filter(
                    FeePayment.is_cancelled == False
                )
                
                if start_date:
                    query = query.filter(FeePayment.payment_date >= start_date)
                if end_date:
                    query = query.filter(FeePayment.payment_date <= end_date)
                if class_id:
                    query = query.filter(Student.class_id == class_id)
                
                results = query.all()
                
                total_collected = 0
                collection_by_mode = {}
                payments_list = []
                
                for payment, student_fee, student, user in results:
                    payment_dict = payment.to_dict()
                    payment_dict['student_name'] = f"{user.first_name} {user.last_name}"
                    payment_dict['student_id'] = student.user_id
                    payments_list.append(payment_dict)
                    
                    total_collected += float(payment.amount_paid)
                    
                    mode = payment.payment_mode.value
                    collection_by_mode[mode] = collection_by_mode.get(mode, 0) + float(payment.amount_paid)
                
                return {
                    'total_collected': total_collected,
                    'total_transactions': len(payments_list),
                    'collection_by_mode': collection_by_mode,
                    'payments': payments_list
                }
        except Exception as e:
            raise Exception(f"Failed to get collection report: {str(e)}")
    
    @staticmethod
    def get_defaulters_list(skid, academic_year_id, as_of_date=None):
        """Get list of students with pending fees"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                if not as_of_date:
                    as_of_date = date.today()
                
                query = tenant_session.query(
                    StudentFee,
                    Student,
                    SchoolUsers,
                    Class
                ).join(
                    Student, StudentFee.student_id == Student.user_id
                ).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).join(
                    Class, Student.class_id == Class.id
                ).filter(
                    StudentFee.academic_year_id == academic_year_id,
                    StudentFee.status.in_([PaymentStatus.PENDING, PaymentStatus.PARTIAL]),
                    StudentFee.due_date < as_of_date
                )
                
                results = query.all()
                
                defaulters = []
                for student_fee, student, user, class_info in results:
                    balance = float(student_fee.total_amount) - float(student_fee.paid_amount) - float(student_fee.discount_amount or 0)
                    days_overdue = (as_of_date - student_fee.due_date).days
                    
                    defaulters.append({
                        'student_id': student.user_id,
                        'student_name': f"{user.first_name} {user.last_name}",
                        'class': class_info.class_name,
                        'phone': user.phone,
                        'total_amount': float(student_fee.total_amount),
                        'paid_amount': float(student_fee.paid_amount),
                        'balance': balance,
                        'due_date': student_fee.due_date.isoformat(),
                        'days_overdue': days_overdue,
                        'status': student_fee.status.value
                    })
                
                return {
                    'total_defaulters': len(defaulters),
                    'total_pending_amount': sum(d['balance'] for d in defaulters),
                    'defaulters': defaulters
                }
        except Exception as e:
            raise Exception(f"Failed to get defaulters list: {str(e)}")
    
    

#=================================== DISCOUNT MANAGEMENT ===================================
    
    @staticmethod
    def apply_discount(data, skid, approved_by_id):
        """Apply discount/concession to a student"""
        try:
            with switch_to_school_db(skid) as tenant_session:
                discount = FeeDiscount(
                    student_id=data['student_id'],
                    discount_name=data['discount_name'],
                    discount_type=data['discount_type'],  # PERCENTAGE or FIXED
                    discount_value=data['discount_value'],
                    applicable_fees=json.dumps(data.get('applicable_fees', [])),
                    valid_from=datetime.strptime(data['valid_from'], '%Y-%m-%d').date(),
                    valid_to=datetime.strptime(data['valid_to'], '%Y-%m-%d').date() if data.get('valid_to') else None,
                    approved_by=approved_by_id,
                    reason=data.get('reason')
                )
                tenant_session.add(discount)
                
                # Apply discount to applicable student fees
                student_fees = tenant_session.query(StudentFee).filter_by(
                    student_id=data['student_id'],
                    academic_year_id=data.get('academic_year_id')
                ).all()
                
                for student_fee in student_fees:
                    if data['discount_type'] == 'PERCENTAGE':
                        discount_amount = float(student_fee.total_amount) * float(data['discount_value']) / 100
                    else:
                        discount_amount = float(data['discount_value'])
                    
                    student_fee.discount_amount = discount_amount
                
                tenant_session.commit()
                return discount.to_dict()
        except Exception as e:
            tenant_session.rollback()
            raise Exception(f"Failed to apply discount: {str(e)}")
    
    
    @staticmethod
    def delete_all_class_fees(class_id, academic_year_id, skid):
        """
        Delete all fee structures for a class and academic year
        Args:
            class_id: Class ID
            academic_year_id: Academic year
            skid: School identifier
        Returns:
            Success message with count
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
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
            skid: School identifier
            academic_year_id: Academic year for fee filtering
            class_id: Optional class filter
        
        Returns:
            List of students with fee summary
        """
        try:
            with switch_to_school_db(skid) as tenant_session:
                # Build query with joins
                query = tenant_session.query(
                    Student, SchoolUsers, Class, Section
                ).join(
                    SchoolUsers, Student.user_id == SchoolUsers.id
                ).outerjoin(
                    Class, Student.class_id == Class.id
                ).outerjoin(
                    Section, Student.section_id == Section.id
                )
                
                # Multi-field search using OR condition
                search_conditions = or_(
                    # Search by name (first name, last name, or full name)
                    SchoolUsers.first_name.ilike(f'%{search_query}%'),
                    SchoolUsers.last_name.ilike(f'%{search_query}%'),
                    func.concat(SchoolUsers.first_name, ' ', SchoolUsers.last_name).ilike(f'%{search_query}%'),
                    
                    # Search by phone number
                    SchoolUsers.phone.ilike(f'%{search_query}%'),
                    
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

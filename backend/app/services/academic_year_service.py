from datetime import datetime
from app.models.tenant.AcademicYear import AcademicYear
from app.utils.db_manager import switch_to_institution_db
from app import db


class AcademicYearService:
    
    @staticmethod
    def get_all_academic_years(skid):
        """
        Get all academic years for an institution
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                academic_years = (
                    tenant_session.query(AcademicYear)
                    .filter_by(is_active=True)
                    .order_by(AcademicYear.start_date.desc())
                    .all()
                )
                
                return [year.to_dict() for year in academic_years]
                
        except Exception as e:
            raise Exception(f"Error fetching academic years: {str(e)}")
    
    
    @staticmethod
    def create_academic_year(data, skid):
        """
        Create a new academic year
        """
        try:
            # Parse dates
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            
            # Validate dates
            if end_date <= start_date:
                raise ValueError("End date must be after start date")
            
            with switch_to_institution_db(skid) as tenant_session:
                # Check for overlapping years
                existing_year = (
                    tenant_session.query(AcademicYear)
                    .filter(
                        AcademicYear.year_name == data['year_name'],
                        AcademicYear.is_active == True
                    )
                    .first()
                )
                
                if existing_year:
                    raise ValueError(f"Academic year '{data['year_name']}' already exists")
                
                # If this is marked as current, unset other current years
                is_current = data.get('is_current', False)
                if is_current:
                    tenant_session.query(AcademicYear).update(
                        {'is_current': False}
                    )
                
                # Create new academic year
                new_year = AcademicYear(
                    year_name=data['year_name'],
                    start_date=start_date,
                    end_date=end_date,
                    is_current=is_current,
                    is_active=data.get('is_active', True)
                )
                
                tenant_session.add(new_year)
                tenant_session.commit()
                tenant_session.refresh(new_year)
                
                return new_year.to_dict()
                
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Error creating academic year: {str(e)}")
    
    
    @staticmethod
    def update_academic_year(data, skid, year_id):
        """
        Update an existing academic year
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                # Get existing academic year
                academic_year = tenant_session.query(AcademicYear).filter_by(
                    id=year_id,
                    is_active=True
                ).first()
                
                if not academic_year:
                    raise ValueError("Academic year not found")
                
                # Update fields if provided
                if 'year_name' in data:
                    # Check for duplicate name
                    duplicate = (
                        tenant_session.query(AcademicYear)
                        .filter(
                            AcademicYear.year_name == data['year_name'],
                            AcademicYear.id != year_id,
                            AcademicYear.is_active == True
                        )
                        .first()
                    )
                    if duplicate:
                        raise ValueError(f"Academic year '{data['year_name']}' already exists")
                    
                    academic_year.year_name = data['year_name']
                
                if 'start_date' in data:
                    academic_year.start_date = datetime.strptime(
                        data['start_date'], '%Y-%m-%d'
                    ).date()
                
                if 'end_date' in data:
                    academic_year.end_date = datetime.strptime(
                        data['end_date'], '%Y-%m-%d'
                    ).date()
                
                # Validate dates
                if academic_year.end_date <= academic_year.start_date:
                    raise ValueError("End date must be after start date")
                
                tenant_session.commit()
                tenant_session.refresh(academic_year)
                
                return academic_year.to_dict()
                
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Error updating academic year: {str(e)}")
    
    
    @staticmethod
    def delete_academic_year(skid, year_id):
        """
        Soft-delete an academic year (sets is_active=False).
        Refuses to delete the year currently marked as current.
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                academic_year = tenant_session.query(AcademicYear).filter_by(
                    id=year_id,
                    is_active=True
                ).first()

                if not academic_year:
                    raise ValueError("Academic year not found")

                if academic_year.is_current:
                    raise ValueError(
                        "Cannot delete the current academic year. "
                        "Set another year as current first."
                    )

                academic_year.is_active = False
                tenant_session.commit()

                return {'id': year_id}

        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Error deleting academic year: {str(e)}")


    @staticmethod
    def set_current_academic_year(skid, year_id):
        """
        Set an academic year as current
        Unsets all other years as current
        """
        try:
            with switch_to_institution_db(skid) as tenant_session:
                # Get the target academic year
                target_year = tenant_session.query(AcademicYear).filter_by(
                    id=year_id,
                    is_active=True
                ).first()
                
                if not target_year:
                    raise ValueError("Academic year not found")
                
                # Set all years as not current
                tenant_session.query(AcademicYear).update({'is_current': False})
                
                # Set target year as current
                target_year.is_current = True
                
                tenant_session.commit()
                tenant_session.refresh(target_year)
                
                return target_year.to_dict()
                
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Error setting current academic year: {str(e)}")

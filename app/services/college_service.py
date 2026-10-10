"""
College service for registration, authentication, and status lookup.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.domain.models import College, Registration, Student, registration_members
from app.domain.schemas import CollegeRegisterRequest, CollegeResponse, CollegeStatusResponse
from app.core.security import create_access_token
import re
from fastapi import HTTPException, status
from app.core.exceptions import CollegeNotFoundException
from app.core.constants import MAX_COLLEGE_STUDENTS_CAP, GENERAL_RULE_REMINDERS


def _normalize_phone(p: str) -> str:
    """Strip spaces, dashes, parentheses and +91 prefix to compare last 10 digits."""
    digits = re.sub(r"\D", "", p or "")
    return digits[-10:] if len(digits) >= 10 else digits


class CollegeService:
    @staticmethod
    def register_or_get_college(db: Session, request: CollegeRegisterRequest) -> CollegeResponse:
        """
        Registers a new college or authenticates returning coordinator if already registered.
        Verifies BOTH faculty email and phone number to prevent unauthorized overwrites.
        """
        college = db.query(College).filter(
            College.college_name.ilike(request.college_name.strip())
        ).first()

        req_email = request.faculty_email.lower().strip()
        req_phone_norm = _normalize_phone(request.faculty_phone)

        if not college:
            # Fresh registration: create new college
            college = College(
                college_name=request.college_name.strip(),
                faculty_coordinator_name=request.faculty_coordinator_name.strip(),
                faculty_phone=request.faculty_phone.strip(),
                faculty_email=req_email,
                total_students_registered=0
            )
            db.add(college)
            db.commit()
            db.refresh(college)
        else:
            # Existing college: STRICT verification of BOTH email and phone
            stored_email = college.faculty_email.lower().strip()
            stored_phone_norm = _normalize_phone(college.faculty_phone)

            email_matches = (stored_email == req_email)
            phone_matches = (stored_phone_norm == req_phone_norm)

            if not email_matches or not phone_matches:
                mismatch_fields = []
                if not email_matches:
                    mismatch_fields.append("Faculty Email")
                if not phone_matches:
                    mismatch_fields.append("Faculty Phone Number")
                mismatches_str = " and ".join(mismatch_fields)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error_code": "COLLEGE_COORDINATOR_MISMATCH",
                        "message": (
                            f"College '{college.college_name}' is already registered with different coordinator credentials. "
                            f"{mismatches_str} does not match the registered coordinator. "
                            "Please use the original registered email and phone number, or contact the fest organizers."
                        ),
                        "details": {
                            "college_name": college.college_name,
                            "email_matched": email_matches,
                            "phone_matched": phone_matches
                        }
                    }
                )

            # Verified returning coordinator: do NOT overwrite details! Keep original credentials.

        # Fetch all already submitted events for this college
        existing_regs = db.query(Registration).filter(Registration.college_id == college.id).all()
        registered_events_list = [r.event_name for r in existing_regs]

        token = create_access_token({"sub": college.id, "college_name": college.college_name})
        remaining_quota = max(0, MAX_COLLEGE_STUDENTS_CAP - college.total_students_registered)

        return CollegeResponse(
            college_id=college.id,
            college_name=college.college_name,
            faculty_coordinator_name=college.faculty_coordinator_name,
            faculty_phone=college.faculty_phone,
            faculty_email=college.faculty_email,
            total_students_registered=college.total_students_registered,
            remaining_student_quota=remaining_quota,
            access_token=token,
            token_type="bearer",
            registered_events=registered_events_list
        )

    @staticmethod
    def get_college_by_id(db: Session, college_id: str) -> College:
        college = db.query(College).filter(College.id == college_id).first()
        if not college:
            raise CollegeNotFoundException(college_id)
        return college

    @staticmethod
    def get_college_status(db: Session, college_id: str) -> CollegeStatusResponse:
        college = CollegeService.get_college_by_id(db, college_id)
        
        # Get all registered events for this college
        registrations = db.query(Registration).filter(Registration.college_id == college_id).all()
        events_list = [reg.event_name for reg in registrations]
        
        remaining_quota = max(0, MAX_COLLEGE_STUDENTS_CAP - college.total_students_registered)

        return CollegeStatusResponse(
            college_id=college.id,
            college_name=college.college_name,
            faculty_coordinator_name=college.faculty_coordinator_name,
            faculty_phone=college.faculty_phone,
            faculty_email=college.faculty_email,
            total_unique_students=college.total_students_registered,
            max_capacity_cap=MAX_COLLEGE_STUDENTS_CAP,
            remaining_quota=remaining_quota,
            is_quota_full=(college.total_students_registered >= MAX_COLLEGE_STUDENTS_CAP),
            registered_events=events_list,
            rule_reminders=GENERAL_RULE_REMINDERS
        )

    @staticmethod
    def query_college_detailed_status(db: Session, college_name: str, faculty_email: str) -> dict:
        clean_name = college_name.strip()
        clean_email = faculty_email.strip().lower()

        # Find matching college by name and verify faculty email
        college = db.query(College).filter(
            College.college_name.ilike(clean_name)
        ).first()

        if not college:
            # Try fuzzy/contains match on name
            college = db.query(College).filter(
                College.college_name.ilike(f"%{clean_name}%")
            ).first()

        if not college:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=404,
                detail=f"No registration found for college '{college_name}'. Please check the name or register your college first."
            )

        if college.faculty_email.lower().strip() != clean_email:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail=f"Faculty email '{faculty_email}' does not match the registered email for '{college.college_name}'."
            )

        # Fetch registrations with team members
        registrations = db.query(Registration).filter(Registration.college_id == college.id).all()
        
        events_detail = []
        for reg in registrations:
            members = [
                {
                    "student_name": s.student_name,
                    "student_phone": s.student_phone or "N/A",
                    "puc_year": s.puc_year
                }
                for s in reg.team_members
            ]
            events_detail.append({
                "event_name": reg.event_name,
                "department": reg.department,
                "team_members": members
            })

        # Fetch all unique registered students
        students = db.query(Student).filter(Student.college_id == college.id).all()
        student_details = []
        for stu in students:
            stu_events = [r.event_name for r in stu.registrations]
            student_details.append({
                "id": stu.id,
                "student_name": stu.student_name,
                "student_phone": stu.student_phone or "N/A",
                "puc_year": stu.puc_year,
                "events": stu_events
            })

        remaining_quota = max(0, MAX_COLLEGE_STUDENTS_CAP - college.total_students_registered)

        return {
            "college_id": college.id,
            "college_name": college.college_name,
            "faculty_coordinator_name": college.faculty_coordinator_name,
            "faculty_phone": college.faculty_phone,
            "faculty_email": college.faculty_email,
            "total_unique_students": college.total_students_registered,
            "max_capacity_cap": MAX_COLLEGE_STUDENTS_CAP,
            "remaining_quota": remaining_quota,
            "is_quota_full": (college.total_students_registered >= MAX_COLLEGE_STUDENTS_CAP),
            "registered_events": events_detail,
            "students": student_details,
            "rule_reminders": GENERAL_RULE_REMINDERS
        }

"""
Registration service: Core business logic engine enforcing:
- Rule 1: The 25-Student College Cap (Unique Student Tracking)
- Rule 2: Strict Event Team-Size Validation Matrix
- Rule 3: Registration Deadline Enforcement (24/10/2026 23:59:59 IST)
"""
from datetime import datetime
from typing import Optional, List, Set
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings, IST
from app.core.constants import (
    EVENT_RULES_MATRIX,
    MAX_COLLEGE_STUDENTS_CAP,
    GENERAL_RULE_REMINDERS,
)
from app.core.exceptions import (
    DeadlineExceededException,
    TeamSizeMismatchException,
    DepartmentMismatchException,
    CollegeStudentCapExceededException,
    DuplicateEventRegistrationException,
    DuplicateParticipantInTeamException,
    CollegeNotFoundException,
    EventNotFoundException,
)
from app.domain.models import College, Student, Registration, registration_members
from app.domain.schemas import EventRegisterRequest, EventRegisterResponse, StudentResponse


class RegistrationService:
    @staticmethod
    def verify_deadline(current_time: Optional[datetime] = None) -> None:
        """
        Rule 3: Registration Deadline Enforcement.
        Denies any registration submissions where server timestamp > 24/10/2026 23:59:59 IST.
        """
        now = current_time or datetime.now(IST)
        deadline = settings.deadline_datetime
        if now > deadline:
            raise DeadlineExceededException(
                deadline_str=deadline.strftime("%d/%m/%Y %H:%M:%S %Z"),
                current_time_str=now.strftime("%d/%m/%Y %H:%M:%S %Z")
            )

    @staticmethod
    def get_canonical_event_info(event_name: str):
        """
        Validates event existence and resolves aliases (e.g., Olympus Oracle).
        """
        # Exact match or case-insensitive match
        matched_key = None
        for key in EVENT_RULES_MATRIX.keys():
            if key.strip().lower() == event_name.strip().lower():
                matched_key = key
                break

        if not matched_key:
            raise EventNotFoundException(event_name)

        rule_info = EVENT_RULES_MATRIX[matched_key]
        canonical_name = rule_info.get("canonical_name", matched_key)
        return canonical_name, rule_info

    @staticmethod
    def register_event(
        db: Session,
        request: EventRegisterRequest,
        current_time: Optional[datetime] = None
    ) -> EventRegisterResponse:
        """
        Enrolls a team into an event with atomic validation of all business constraints.
        """
        # 1. Rule 3: Registration Deadline Enforcement
        RegistrationService.verify_deadline(current_time)

        # 2. Verify College existence and acquire lock for concurrent safety
        college = db.query(College).filter(College.id == request.college_id).with_for_update(nowait=False, of=College).first() if not db.bind.name.startswith("sqlite") else db.query(College).filter(College.id == request.college_id).first()
        
        if not college:
            raise CollegeNotFoundException(request.college_id or "Unknown")

        # 3. Rule 2: Event and Department Validation Matrix
        canonical_name, rule_info = RegistrationService.get_canonical_event_info(request.event_name)
        expected_dept = rule_info["department"]
        if request.department != expected_dept:
            raise DepartmentMismatchException(
                event_name=canonical_name,
                expected_dept=expected_dept.value,
                provided_dept=request.department.value
            )

        # 4. Rule 2: Strict Team-Size Validation Matrix
        expected_team_size = rule_info["team_size"]
        provided_team_size = len(request.participants)
        if provided_team_size != expected_team_size:
            raise TeamSizeMismatchException(
                event_name=canonical_name,
                expected_size=expected_team_size,
                provided_size=provided_team_size
            )

        # 5. Check duplicate participants within the submitted payload
        seen_names = set()
        for p in request.participants:
            norm_key = (p.student_name.strip().lower(), p.puc_year.value)
            if norm_key in seen_names:
                raise DuplicateParticipantInTeamException(p.student_name)
            seen_names.add(norm_key)

        # 6. Check if college already registered for this event (Single team per college rule)
        existing_registration = db.query(Registration).filter(
            Registration.college_id == college.id,
            Registration.event_name == canonical_name
        ).first()

        if existing_registration:
            raise DuplicateEventRegistrationException(college.college_name, canonical_name)

        # 7. Identify or Create Students under this College
        team_students: List[Student] = []
        for p in request.participants:
            # Query if student exists under this college
            student = db.query(Student).filter(
                Student.college_id == college.id,
                Student.student_name.ilike(p.student_name.strip()),
                Student.puc_year == p.puc_year.value
            ).first()

            if not student:
                student = Student(
                    college_id=college.id,
                    student_name=p.student_name.strip(),
                    student_phone=p.student_phone.strip() if p.student_phone else None,
                    puc_year=p.puc_year.value
                )
                db.add(student)
                db.flush()  # Generate student.id
            else:
                if p.student_phone and not student.student_phone:
                    student.student_phone = p.student_phone.strip()
                    db.flush()
            team_students.append(student)


        # 8. Rule 1: The 25-Student College Cap (Unique Student Tracking across all events)
        # Fetch all unique student IDs already participating in ANY registration of this college
        query_current_unique_ids = db.execute(
            select(registration_members.c.student_id)
            .join(Registration, registration_members.c.registration_id == Registration.id)
            .where(Registration.college_id == college.id)
        ).scalars().all()

        current_unique_student_ids: Set[str] = set(query_current_unique_ids)
        current_unique_count = len(current_unique_student_ids)

        # New team student IDs
        incoming_student_ids: Set[str] = {s.id for s in team_students}

        # Projected unique student set
        projected_unique_ids: Set[str] = current_unique_student_ids.union(incoming_student_ids)
        projected_unique_count = len(projected_unique_ids)
        newly_introduced_count = projected_unique_count - current_unique_count

        if projected_unique_count > MAX_COLLEGE_STUDENTS_CAP:
            db.rollback()
            raise CollegeStudentCapExceededException(
                college_id=college.id,
                college_name=college.college_name,
                current_unique_count=current_unique_count,
                attempted_new_unique_count=newly_introduced_count,
                projected_total=projected_unique_count,
                cap=MAX_COLLEGE_STUDENTS_CAP
            )

        # 9. Create Registration and Associate Team Members
        registration = Registration(
            college_id=college.id,
            event_name=canonical_name,
            department=request.department.value
        )
        db.add(registration)
        db.flush()

        for s in team_students:
            registration.team_members.append(s)

        # 10. Update College's total_students_registered to current unique student count
        college.total_students_registered = projected_unique_count
        db.commit()
        db.refresh(registration)
        db.refresh(college)

        remaining_quota = MAX_COLLEGE_STUDENTS_CAP - college.total_students_registered

        return EventRegisterResponse(
            registration_id=registration.id,
            college_id=college.id,
            college_name=college.college_name,
            event_name=registration.event_name,
            department=registration.department,
            team_size=len(team_students),
            team_members=[
                StudentResponse(
                    id=s.id,
                    student_name=s.student_name,
                    student_phone=s.student_phone,
                    puc_year=s.puc_year,
                    college_id=s.college_id
                )
                for s in team_students
            ],

            newly_introduced_students_count=newly_introduced_count,
            total_unique_students_registered=college.total_students_registered,
            remaining_college_quota=remaining_quota,
            rule_reminders=GENERAL_RULE_REMINDERS
        )

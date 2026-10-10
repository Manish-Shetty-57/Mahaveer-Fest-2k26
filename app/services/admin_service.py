"""
Admin reporting and analytics service for organizing faculty.
"""
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.config import IST
from app.core.constants import EVENT_RULES_MATRIX, MAX_COLLEGE_STUDENTS_CAP, GENERAL_RULE_REMINDERS
from app.domain.models import College, Student, Registration, registration_members
from app.domain.schemas import (
    AdminSummaryResponse,
    CollegeSummaryItem,
    EventSummaryItem,
    EventRosterItem,
    StudentResponse,
)


class AdminService:
    @staticmethod
    def get_fest_summary(
        db: Session,
        college_id: Optional[str] = None,
        department: Optional[str] = None,
        event_name: Optional[str] = None
    ) -> AdminSummaryResponse:
        """
        Generates event-wise and college-wise participation rosters and overall fest statistics.
        """
        # Base queries
        colleges_query = db.query(College)
        if college_id:
            colleges_query = colleges_query.filter(College.id == college_id)
        colleges = colleges_query.order_by(College.college_name).all()

        registrations_query = db.query(Registration)
        if college_id:
            registrations_query = registrations_query.filter(Registration.college_id == college_id)
        if department:
            registrations_query = registrations_query.filter(Registration.department == department)
        if event_name:
            registrations_query = registrations_query.filter(Registration.event_name.ilike(event_name))
        registrations = registrations_query.all()

        # 1. Total unique participating students across the entire fest
        total_unique_fest_students = db.query(func.count(func.distinct(registration_members.c.student_id))).scalar() or 0

        # 2. Department statistics
        dept_stats = {
            "SCIENCE": 0,
            "COMMERCE": 0,
            "IT": 0,
            "HUMANITIES": 0
        }
        for reg in registrations:
            if reg.department in dept_stats:
                dept_stats[reg.department] += 1

        # 3. College-wise summary
        college_summary_list: List[CollegeSummaryItem] = []
        for col in colleges:
            col_regs = [r for r in registrations if r.college_id == col.id]
            
            # Find unique students registered for events for this college
            unique_students_query = (
                db.query(Student)
                .join(registration_members, Student.id == registration_members.c.student_id)
                .join(Registration, registration_members.c.registration_id == Registration.id)
                .filter(Registration.college_id == col.id)
                .distinct()
                .all()
            )

            student_roster = [
                StudentResponse(
                    id=s.id,
                    student_name=s.student_name,
                    student_phone=s.student_phone,
                    puc_year=s.puc_year,
                    college_id=s.college_id
                )
                for s in unique_students_query
            ]

            events_enrolled = list({r.event_name for r in col_regs})

            college_summary_list.append(
                CollegeSummaryItem(
                    college_id=col.id,
                    college_name=col.college_name,
                    faculty_coordinator_name=col.faculty_coordinator_name,
                    faculty_phone=col.faculty_phone,
                    faculty_email=col.faculty_email,
                    total_unique_students=len(unique_students_query),
                    remaining_quota=max(0, MAX_COLLEGE_STUDENTS_CAP - len(unique_students_query)),
                    events_enrolled=events_enrolled,
                    unique_students_roster=student_roster
                )
            )

        # 4. Event-wise summary
        event_summary_list: List[EventSummaryItem] = []
        # Group events defined in the matrix
        for ev_name, ev_meta in EVENT_RULES_MATRIX.items():
            # Skip aliases in matrix summary to avoid duplication
            if "canonical_name" in ev_meta:
                continue

            ev_regs = [r for r in registrations if r.event_name.lower() == ev_name.lower()]
            
            roster_items: List[EventRosterItem] = []
            total_event_participants = 0
            for r in ev_regs:
                members = [
                    StudentResponse(
                        id=m.id,
                        student_name=m.student_name,
                        student_phone=m.student_phone,
                        puc_year=m.puc_year,
                        college_id=m.college_id
                    )
                    for m in r.team_members
                ]

                total_event_participants += len(members)
                roster_items.append(
                    EventRosterItem(
                        registration_id=r.id,
                        college_id=r.college_id,
                        college_name=r.college.college_name,
                        faculty_coordinator=r.college.faculty_coordinator_name,
                        faculty_phone=r.college.faculty_phone,
                        team_members=members
                    )
                )

            event_summary_list.append(
                EventSummaryItem(
                    event_name=ev_name,
                    department=ev_meta["department"].value,
                    required_team_size=ev_meta["team_size"],
                    total_teams_registered=len(ev_regs),
                    total_participants=total_event_participants,
                    roster=roster_items
                )
            )

        now_ist = datetime.now(IST).strftime("%d/%m/%Y %H:%M:%S IST")

        return AdminSummaryResponse(
            summary_generated_at=now_ist,
            fest_title="MAHAVEERA FEST 2K26",
            fest_date="30 October 2026",
            venue="Sri Mahaveera College, Kodangallu, Moodbidri",
            total_colleges=len(colleges),
            total_unique_students_across_fest=total_unique_fest_students,
            total_event_enrollments=len(registrations),
            department_stats=dept_stats,
            college_wise_summary=college_summary_list,
            event_wise_summary=event_summary_list,
            rule_reminders=GENERAL_RULE_REMINDERS
        )

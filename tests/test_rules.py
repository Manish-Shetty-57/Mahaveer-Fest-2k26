"""
Comprehensive test suite for Core Backend Logic and Business Constraints:
- Rule 1: The 25-Student College Cap (Unique Student Tracking)
- Rule 2: Strict Event Team-Size Validation Matrix
- Rule 3: Registration Deadline Enforcement
"""
import pytest
from datetime import datetime
from app.core.config import IST
from app.domain.schemas import CollegeRegisterRequest, EventRegisterRequest, ParticipantInput
from app.services.college_service import CollegeService
from app.services.registration_service import RegistrationService
from app.core.exceptions import (
    DeadlineExceededException,
    TeamSizeMismatchException,
    DepartmentMismatchException,
    CollegeStudentCapExceededException,
    DuplicateEventRegistrationException,
    DuplicateParticipantInTeamException,
)
from app.core.constants import DepartmentEnum, PUCYearEnum


# ============================================================================
# Rule 3 Tests: Registration Deadline Enforcement
# ============================================================================

def test_deadline_enforcement_valid():
    """Registrations before or at 29/10/2026 16:00:00 IST should be allowed."""
    valid_time = datetime(2026, 10, 29, 15, 59, 58, tzinfo=IST)
    RegistrationService.verify_deadline(current_time=valid_time)


def test_deadline_enforcement_exceeded():
    """Registrations after 29/10/2026 16:00:00 IST should be rejected."""
    expired_time = datetime(2026, 10, 29, 16, 0, 1, tzinfo=IST)
    with pytest.raises(DeadlineExceededException) as excinfo:
        RegistrationService.verify_deadline(current_time=expired_time)
    assert excinfo.value.status_code == 403
    assert excinfo.value.detail["error_code"] == "REGISTRATION_DEADLINE_EXCEEDED"


# ============================================================================
# Rule 2 Tests: Strict Event Team-Size Validation Matrix
@pytest.fixture(autouse=True)
def mock_valid_time_for_rule_tests(monkeypatch, request):
    if "deadline" in request.node.name:
        return
    valid_time = datetime(2026, 10, 25, 12, 0, 0, tzinfo=IST)
    orig_verify = RegistrationService.verify_deadline
    monkeypatch.setattr(
        RegistrationService,
        "verify_deadline",
        lambda current_time=None: orig_verify(current_time or valid_time)
    )
# ============================================================================

def test_team_size_math_crunch_exact_4(db_session):
    """Math Crunch requires exactly 4 participants."""
    college_req = CollegeRegisterRequest(
        college_name="SDM PU College, Ujire",
        faculty_coordinator_name="Dr. Shridhar",
        faculty_phone="9876543210",
        faculty_email="shridhar@sdm.edu"
    )
    col = CollegeService.register_or_get_college(db_session, college_req)

    # 3 participants (should fail)
    req_invalid = EventRegisterRequest(
        college_id=col.college_id,
        event_name="Math Crunch",
        department=DepartmentEnum.SCIENCE,
        participants=[
            ParticipantInput(student_name="Student 1", puc_year=PUCYearEnum.FIRST_PUC),
            ParticipantInput(student_name="Student 2", puc_year=PUCYearEnum.FIRST_PUC),
            ParticipantInput(student_name="Student 3", puc_year=PUCYearEnum.SECOND_PUC),
        ]
    )
    with pytest.raises(TeamSizeMismatchException) as exc:
        RegistrationService.register_event(db_session, req_invalid)
    assert exc.value.detail["error_code"] == "INVALID_TEAM_SIZE"
    assert exc.value.detail["details"]["expected_team_size"] == 4
    assert exc.value.detail["details"]["provided_team_size"] == 3

    # Exactly 4 participants (should succeed)
    req_valid = EventRegisterRequest(
        college_id=col.college_id,
        event_name="Math Crunch",
        department=DepartmentEnum.SCIENCE,
        participants=[
            ParticipantInput(student_name="Student 1", puc_year=PUCYearEnum.FIRST_PUC),
            ParticipantInput(student_name="Student 2", puc_year=PUCYearEnum.FIRST_PUC),
            ParticipantInput(student_name="Student 3", puc_year=PUCYearEnum.SECOND_PUC),
            ParticipantInput(student_name="Student 4", puc_year=PUCYearEnum.SECOND_PUC),
        ]
    )
    res = RegistrationService.register_event(db_session, req_valid)
    assert res.event_name == "Math Crunch"
    assert res.team_size == 4
    assert res.total_unique_students_registered == 4


def test_department_mismatch_rejection(db_session):
    """Mismatched department must be rejected with 422."""
    college_req = CollegeRegisterRequest(
        college_name="Alva's PU College, Moodbidri",
        faculty_coordinator_name="Prof. Mohan",
        faculty_phone="9876543211",
        faculty_email="mohan@alvas.edu"
    )
    col = CollegeService.register_or_get_college(db_session, college_req)

    # Code Wars belongs to IT, passing SCIENCE should fail
    req_mismatch = EventRegisterRequest(
        college_id=col.college_id,
        event_name="Code Wars",
        department=DepartmentEnum.SCIENCE,
        participants=[
            ParticipantInput(student_name="Coder 1", puc_year=PUCYearEnum.FIRST_PUC),
            ParticipantInput(student_name="Coder 2", puc_year=PUCYearEnum.SECOND_PUC),
        ]
    )
    with pytest.raises(DepartmentMismatchException) as exc:
        RegistrationService.register_event(db_session, req_mismatch)
    assert exc.value.detail["error_code"] == "DEPARTMENT_MISMATCH"
    assert exc.value.detail["details"]["expected_department"] == "IT"


def test_duplicate_participant_in_same_team_rejection(db_session):
    """Submitting the same student twice in the same event team must be rejected."""
    college_req = CollegeRegisterRequest(
        college_name="Canara PU College, Mangaluru",
        faculty_coordinator_name="Prof. Savitha",
        faculty_phone="9876543212",
        faculty_email="savitha@canara.edu"
    )
    col = CollegeService.register_or_get_college(db_session, college_req)

    req = EventRegisterRequest(
        college_id=col.college_id,
        event_name="Brand Rangoli",
        department=DepartmentEnum.COMMERCE,
        participants=[
            ParticipantInput(student_name="Pooja Rao", puc_year=PUCYearEnum.SECOND_PUC),
            ParticipantInput(student_name="Pooja Rao", puc_year=PUCYearEnum.SECOND_PUC),
        ]
    )
    with pytest.raises(DuplicateParticipantInTeamException):
        RegistrationService.register_event(db_session, req)


def test_single_team_per_college_rule(db_session):
    """A college cannot register multiple teams for the same event."""
    college_req = CollegeRegisterRequest(
        college_name="St. Agnes PU College",
        faculty_coordinator_name="Sister Carmel",
        faculty_phone="9876543213",
        faculty_email="carmel@stagnes.edu"
    )
    col = CollegeService.register_or_get_college(db_session, college_req)

    req = EventRegisterRequest(
        college_id=col.college_id,
        event_name="Prompt Wars",
        department=DepartmentEnum.IT,
        participants=[
            ParticipantInput(student_name="AI Student 1", puc_year=PUCYearEnum.FIRST_PUC),
            ParticipantInput(student_name="AI Student 2", puc_year=PUCYearEnum.SECOND_PUC),
        ]
    )
    RegistrationService.register_event(db_session, req)

    # Attempting to register another team for Prompt Wars
    req2 = EventRegisterRequest(
        college_id=col.college_id,
        event_name="Prompt Wars",
        department=DepartmentEnum.IT,
        participants=[
            ParticipantInput(student_name="AI Student 3", puc_year=PUCYearEnum.FIRST_PUC),
            ParticipantInput(student_name="AI Student 4", puc_year=PUCYearEnum.SECOND_PUC),
        ]
    )
    with pytest.raises(DuplicateEventRegistrationException):
        RegistrationService.register_event(db_session, req2)


# ============================================================================
# Rule 1 Tests: The 25-Student College Cap (Unique Student Tracking)
# ============================================================================

def test_unique_student_tracking_multiple_events(db_session):
    """
    If a student registers for multiple events, they must only be counted once
    toward the college's 25-student pool.
    """
    col = CollegeService.register_or_get_college(
        db_session,
        CollegeRegisterRequest(
            college_name="Poornaprajna PU College, Udupi",
            faculty_coordinator_name="Dr. Raghavendra",
            faculty_phone="9876543214",
            faculty_email="raghav@ppc.edu"
        )
    )

    # Event 1: Math Crunch (4 members: A, B, C, D)
    res1 = RegistrationService.register_event(
        db_session,
        EventRegisterRequest(
            college_id=col.college_id,
            event_name="Math Crunch",
            department=DepartmentEnum.SCIENCE,
            participants=[
                ParticipantInput(student_name="Student A", puc_year=PUCYearEnum.FIRST_PUC),
                ParticipantInput(student_name="Student B", puc_year=PUCYearEnum.FIRST_PUC),
                ParticipantInput(student_name="Student C", puc_year=PUCYearEnum.SECOND_PUC),
                ParticipantInput(student_name="Student D", puc_year=PUCYearEnum.SECOND_PUC),
            ]
        )
    )
    assert res1.total_unique_students_registered == 4
    assert res1.newly_introduced_students_count == 4
    assert res1.remaining_college_quota == 21

    # Event 2: Prompt Wars (2 members: Student A [cross-registered!], Student E [new])
    res2 = RegistrationService.register_event(
        db_session,
        EventRegisterRequest(
            college_id=col.college_id,
            event_name="Prompt Wars",
            department=DepartmentEnum.IT,
            participants=[
                ParticipantInput(student_name="Student A", puc_year=PUCYearEnum.FIRST_PUC),  # Existing
                ParticipantInput(student_name="Student E", puc_year=PUCYearEnum.FIRST_PUC),  # New
            ]
        )
    )
    # Total unique students should be 5 (A, B, C, D, E), not 6!
    assert res2.total_unique_students_registered == 5
    assert res2.newly_introduced_students_count == 1
    assert res2.remaining_college_quota == 20


def test_25_student_cap_enforcement_and_overflow(db_session, monkeypatch):
    """
    Each college is strictly limited to 25 unique participating students.
    Exceeding 25 must immediately reject the transaction.
    """
    col = CollegeService.register_or_get_college(
        db_session,
        CollegeRegisterRequest(
            college_name="Sharada PU College, Mangaluru",
            faculty_coordinator_name="Prof. Divya",
            faculty_phone="9876543215",
            faculty_email="divya@sharada.edu"
        )
    )

    # Register 12 events for col (leaving out Math Crunch, which requires 4):
    # Total unique students registered = 21
    # 1. Chemvista (1) -> 1
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Chemvista", department=DepartmentEnum.SCIENCE,
        participants=[ParticipantInput(student_name="S1", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 2. Pandora's Mystery (1) -> 2
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Pandora's Mystery", department=DepartmentEnum.COMMERCE,
        participants=[ParticipantInput(student_name="S2", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 3. Chitra Pratiyogita (1) -> 3
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Chitra Pratiyogita", department=DepartmentEnum.HUMANITIES,
        participants=[ParticipantInput(student_name="S3", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 4. Physispark (2) -> 5
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Physispark", department=DepartmentEnum.SCIENCE,
        participants=[ParticipantInput(student_name="S4", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="S5", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 5. Brand Rangoli (2) -> 7
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Brand Rangoli", department=DepartmentEnum.COMMERCE,
        participants=[ParticipantInput(student_name="S6", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="S7", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 6. Olympus Oracle (2) -> 9
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Olympus Oracle Business Quiz", department=DepartmentEnum.COMMERCE,
        participants=[ParticipantInput(student_name="S8", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="S9", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 7. Code Wars (2) -> 11
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Code Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="S10", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="S11", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 8. Prompt Wars (2) -> 13
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Prompt Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="S12", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="S13", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 9. Mind Wars (2) -> 15
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Mind Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="S14", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="S15", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 10. Innovation Wars (2) -> 17
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Innovation Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="S16", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="S17", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 11. Arthalankara (2) -> 19
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Arthalankara", department=DepartmentEnum.HUMANITIES,
        participants=[ParticipantInput(student_name="S18", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="S19", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 12. Chitra Phalakam (2) -> 21
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col.college_id, event_name="Chitra Phalakam", department=DepartmentEnum.HUMANITIES,
        participants=[ParticipantInput(student_name="S20", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="S21", puc_year=PUCYearEnum.FIRST_PUC)]
    ))

    # At this point, exactly 21 unique students are registered.
    # Quota remaining is 25 - 21 = 4.
    status = CollegeService.get_college_status(db_session, col.college_id)
    assert status.total_unique_students == 21
    assert status.remaining_quota == 4

    # Now, if we attempt to register Math Crunch (which requires 4 members)
    # with 5 members, team size fails.
    # What if college already has 23 unique students?
    # Let's cross-register a new event or add students.
    # Since Math Crunch is the only remaining event, let's see what happens if 4 NEW students register:
    # 21 + 4 = 25 (Succeeds exactly at 25).
    res_exact_25 = RegistrationService.register_event(
        db_session,
        EventRegisterRequest(
            college_id=col.college_id,
            event_name="Math Crunch",
            department=DepartmentEnum.SCIENCE,
            participants=[
                ParticipantInput(student_name="S22", puc_year=PUCYearEnum.FIRST_PUC),
                ParticipantInput(student_name="S23", puc_year=PUCYearEnum.FIRST_PUC),
                ParticipantInput(student_name="S24", puc_year=PUCYearEnum.SECOND_PUC),
                ParticipantInput(student_name="S25", puc_year=PUCYearEnum.SECOND_PUC),
            ]
        )
    )
    assert res_exact_25.total_unique_students_registered == 25
    assert res_exact_25.remaining_college_quota == 0

    # Now college 'col' has 25 unique students!
    # Status check confirms quota full:
    status_full = CollegeService.get_college_status(db_session, col.college_id)
    assert status_full.total_unique_students == 25
    assert status_full.is_quota_full is True
    assert status_full.remaining_quota == 0

    # Now create college 'col_overflow' to test exceeding 25 cap:
    # Suppose college 'col_overflow' registers 11 events (total 22 students).
    col_overflow = CollegeService.register_or_get_college(
        db_session,
        CollegeRegisterRequest(
            college_name="Canara College Cap Check",
            faculty_coordinator_name="Dr. Ganesh",
            faculty_phone="9876543233",
            faculty_email="ganesh@canara.edu"
        )
    )
    # Register 11 two-participant/one-participant events:
    # 1. Chemvista (1) -> 1
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Chemvista", department=DepartmentEnum.SCIENCE,
        participants=[ParticipantInput(student_name="C1", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 2. Pandora's Mystery (1) -> 2
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Pandora's Mystery", department=DepartmentEnum.COMMERCE,
        participants=[ParticipantInput(student_name="C2", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 3. Chitra Pratiyogita (1) -> 3
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Chitra Pratiyogita", department=DepartmentEnum.HUMANITIES,
        participants=[ParticipantInput(student_name="C3", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 4 to 12: Nine 2-member events = 18 students -> total 3 + 18 = 21 students
    # 4. Physispark (2) -> 5
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Physispark", department=DepartmentEnum.SCIENCE,
        participants=[ParticipantInput(student_name="C4", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="C5", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 5. Brand Rangoli (2) -> 7
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Brand Rangoli", department=DepartmentEnum.COMMERCE,
        participants=[ParticipantInput(student_name="C6", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="C7", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 6. Olympus Oracle (2) -> 9
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Olympus Oracle Business Quiz", department=DepartmentEnum.COMMERCE,
        participants=[ParticipantInput(student_name="C8", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="C9", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 7. Code Wars (2) -> 11
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Code Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="C10", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="C11", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 8. Prompt Wars (2) -> 13
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Prompt Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="C12", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="C13", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 9. Mind Wars (2) -> 15
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Mind Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="C14", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="C15", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 10. Innovation Wars (2) -> 17
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Innovation Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="C16", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="C17", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 11. Arthalankara (2) -> 19
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Arthalankara", department=DepartmentEnum.HUMANITIES,
        participants=[ParticipantInput(student_name="C18", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="C19", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 12. Chitra Phalakam (2) -> 21
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_overflow.college_id, event_name="Chitra Phalakam", department=DepartmentEnum.HUMANITIES,
        participants=[ParticipantInput(student_name="C20", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="C21", puc_year=PUCYearEnum.FIRST_PUC)]
    ))

    # col_overflow has 21 unique students. Remaining quota is 4.
    # Now, if col_overflow had 23 unique students (e.g. if we had 2 more students),
    # and tried to register Math Crunch (which brings 4 NEW students):
    # Projected unique students = 23 + 4 = 27 > 25 -> REJECTED!
    # Let's add 2 students by creating a custom event registration or reusing:
    # Say we didn't register Math Crunch yet.
    # What if col_overflow tries to register Math Crunch with 4 NEW students when quota is less than 4?
    # To demonstrate quota being exceeded, let's create a test where college has 24 unique students:
    # In col_overflow, we have 21 unique students. If we try to register an event with 5 students (not possible by team size),
    # but what if Math Crunch is registered when current is 22, 23, or 24?
    # Let's create `col_strict_cap`:
    col_strict = CollegeService.register_or_get_college(
        db_session,
        CollegeRegisterRequest(
            college_name="KVT Strict Cap College",
            faculty_coordinator_name="Dr. Pai",
            faculty_phone="9876543288",
            faculty_email="pai@kvt.edu"
        )
    )
    # Register 12 events for col_strict (giving 23 unique students by cross-registering):
    # 1. Chemvista (1) -> C1
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Chemvista", department=DepartmentEnum.SCIENCE,
        participants=[ParticipantInput(student_name="K1", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 2. Pandora's Mystery (1) -> K2
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Pandora's Mystery", department=DepartmentEnum.COMMERCE,
        participants=[ParticipantInput(student_name="K2", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 3. Chitra Pratiyogita (1) -> K3
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Chitra Pratiyogita", department=DepartmentEnum.HUMANITIES,
        participants=[ParticipantInput(student_name="K3", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 4. Physispark (2) -> K4, K5 (Total 5)
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Physispark", department=DepartmentEnum.SCIENCE,
        participants=[ParticipantInput(student_name="K4", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="K5", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 5. Brand Rangoli (2) -> K6, K7 (Total 7)
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Brand Rangoli", department=DepartmentEnum.COMMERCE,
        participants=[ParticipantInput(student_name="K6", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="K7", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 6. Olympus Oracle (2) -> K8, K9 (Total 9)
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Olympus Oracle Business Quiz", department=DepartmentEnum.COMMERCE,
        participants=[ParticipantInput(student_name="K8", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="K9", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 7. Code Wars (2) -> K10, K11 (Total 11)
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Code Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="K10", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="K11", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 8. Prompt Wars (2) -> K12, K13 (Total 13)
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Prompt Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="K12", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="K13", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 9. Mind Wars (2) -> K14, K15 (Total 15)
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Mind Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="K14", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="K15", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 10. Innovation Wars (2) -> K16, K17 (Total 17)
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Innovation Wars", department=DepartmentEnum.IT,
        participants=[ParticipantInput(student_name="K16", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="K17", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 11. Arthalankara (2) -> K18, K19 (Total 19)
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Arthalankara", department=DepartmentEnum.HUMANITIES,
        participants=[ParticipantInput(student_name="K18", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="K19", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 12. Chitra Phalakam (2) -> K20, K21 (Total 21)
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_strict.college_id, event_name="Chitra Phalakam", department=DepartmentEnum.HUMANITIES,
        participants=[ParticipantInput(student_name="K20", puc_year=PUCYearEnum.FIRST_PUC),
                      ParticipantInput(student_name="K21", puc_year=PUCYearEnum.FIRST_PUC)]
    ))

    # Current unique count = 21. Quota remaining = 4.
    # Math Crunch is un-registered. Math Crunch requires 4 participants.
    # If Math Crunch is submitted with 4 NEW students (K22, K23, K24, K25):
    # Total unique count becomes exactly 25.
    # But what if col_strict had already 22 unique students, and tried to register Math Crunch with 4 NEW students?
    # Then projected = 22 + 4 = 26 > 25!
    # Let's test that directly:
    # If Math Crunch is attempted with 4 NEW students when remaining quota is only 3 or fewer:
    # Let's say col_overflow from above had 21 students.
    # If col_overflow had 23 students, 23 + 4 = 27 > 25!
    # Let's test this in a targeted test:
    # College registers 10 events giving 23 unique students, and tries Math Crunch (4 new students).
    # Projected: 23 + 4 = 27 > 25. Rejected with 422!
    col_test_cap = CollegeService.register_or_get_college(
        db_session,
        CollegeRegisterRequest(
            college_name="Cap Overflow Demo College",
            faculty_coordinator_name="Prof. Hegde",
            faculty_phone="9876543200",
            faculty_email="hegde@capdemo.edu"
        )
    )
    # Register 12 events giving 23 unique students:
    # 1. Chemvista (1) -> 1
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_test_cap.college_id, event_name="Chemvista", department=DepartmentEnum.SCIENCE,
        participants=[ParticipantInput(student_name="D1", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 2. Pandora's Mystery (1) -> 2
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_test_cap.college_id, event_name="Pandora's Mystery", department=DepartmentEnum.COMMERCE,
        participants=[ParticipantInput(student_name="D2", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # 3. Chitra Pratiyogita (1) -> 3
    RegistrationService.register_event(db_session, EventRegisterRequest(
        college_id=col_test_cap.college_id, event_name="Chitra Pratiyogita", department=DepartmentEnum.HUMANITIES,
        participants=[ParticipantInput(student_name="D3", puc_year=PUCYearEnum.FIRST_PUC)]
    ))
    # College 'col_test_cap' now has exactly 3 unique students registered (D1, D2, D3).
    # If MAX_COLLEGE_STUDENTS_CAP is set to 5:
    # Math Crunch requires 4 participants. Projected unique total = 3 + 4 = 7, which exceeds 5!
    monkeypatch.setattr("app.services.registration_service.MAX_COLLEGE_STUDENTS_CAP", 5)
    with pytest.raises(CollegeStudentCapExceededException) as exc:
        RegistrationService.register_event(
            db_session,
            EventRegisterRequest(
                college_id=col_test_cap.college_id,
                event_name="Math Crunch",
                department=DepartmentEnum.SCIENCE,
                participants=[
                    ParticipantInput(student_name="New S1", puc_year=PUCYearEnum.FIRST_PUC),
                    ParticipantInput(student_name="New S2", puc_year=PUCYearEnum.FIRST_PUC),
                    ParticipantInput(student_name="New S3", puc_year=PUCYearEnum.FIRST_PUC),
                    ParticipantInput(student_name="New S4", puc_year=PUCYearEnum.FIRST_PUC),
                ]
            )
        )
    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == "COLLEGE_STUDENT_CAP_EXCEEDED"
    assert exc.value.detail["details"]["maximum_cap"] == 5
    assert exc.value.detail["details"]["current_unique_students"] == 3
    assert exc.value.detail["details"]["new_students_in_request"] == 4
    assert exc.value.detail["details"]["projected_unique_total"] == 7
    assert exc.value.detail["details"]["exceeded_margin"] == 2
    assert exc.value.detail["details"]["remaining_quota_before_request"] == 2



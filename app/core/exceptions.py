"""
Custom domain exceptions for business rules validation.
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class DomainException(HTTPException):
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "error_code": error_code,
                "message": message,
                "details": details or {}
            }
        )


class DeadlineExceededException(DomainException):
    def __init__(self, deadline_str: str, current_time_str: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="REGISTRATION_DEADLINE_EXCEEDED",
            message=f"Online registration is closed. Don’t worry, spot registration is available at the venue! (Online deadline closed on {deadline_str}).",
            details={
                "deadline": deadline_str,
                "server_time": current_time_str,
                "rule": f"Rule 3: Registration submissions past {deadline_str} are rejected."
            }
        )


class TeamSizeMismatchException(DomainException):
    def __init__(self, event_name: str, expected_size: int, provided_size: int):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="INVALID_TEAM_SIZE",
            message=f"Event '{event_name}' requires exactly {expected_size} participant(s), but {provided_size} was provided.",
            details={
                "event_name": event_name,
                "expected_team_size": expected_size,
                "provided_team_size": provided_size,
                "rule": f"Rule 2: Strict team size validation matrix for {event_name}."
            }
        )


class DepartmentMismatchException(DomainException):
    def __init__(self, event_name: str, expected_dept: str, provided_dept: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="DEPARTMENT_MISMATCH",
            message=f"Event '{event_name}' belongs to department '{expected_dept}', not '{provided_dept}'.",
            details={
                "event_name": event_name,
                "expected_department": expected_dept,
                "provided_department": provided_dept
            }
        )


class CollegeStudentCapExceededException(DomainException):
    def __init__(
        self,
        college_id: str,
        college_name: str,
        current_unique_count: int,
        attempted_new_unique_count: int,
        projected_total: int,
        cap: int = 25
    ):
        exceeded_by = projected_total - cap
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="COLLEGE_STUDENT_CAP_EXCEEDED",
            message=(
                f"College '{college_name}' cap exceeded! Registering these participants would bring "
                f"the unique student count to {projected_total}, which exceeds the maximum limit of {cap} by {exceeded_by}."
            ),
            details={
                "college_id": college_id,
                "college_name": college_name,
                "maximum_cap": cap,
                "current_unique_students": current_unique_count,
                "new_students_in_request": attempted_new_unique_count,
                "projected_unique_total": projected_total,
                "exceeded_margin": exceeded_by,
                "remaining_quota_before_request": max(0, cap - current_unique_count),
                "rule": "Rule 1: Each college is strictly limited to a maximum of 25 unique participating students across all events."
            }
        )


class DuplicateEventRegistrationException(DomainException):
    def __init__(self, college_name: str, event_name: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="DUPLICATE_EVENT_REGISTRATION",
            message=f"College '{college_name}' has already registered a team for event '{event_name}'.",
            details={
                "college_name": college_name,
                "event_name": event_name,
                "rule": "Only one team per college is allowed per event."
            }
        )


class DuplicateParticipantInTeamException(DomainException):
    def __init__(self, participant_name: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="DUPLICATE_PARTICIPANT_IN_REQUEST",
            message=f"Duplicate participant '{participant_name}' detected in the submitted team roster.",
            details={"duplicate_name": participant_name}
        )


class CollegeNotFoundException(DomainException):
    def __init__(self, college_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="COLLEGE_NOT_FOUND",
            message=f"College with ID '{college_id}' was not found.",
            details={"college_id": college_id}
        )


class EventNotFoundException(DomainException):
    def __init__(self, event_name: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="EVENT_NOT_FOUND",
            message=f"Event '{event_name}' is not recognized in the official fest schedule.",
            details={"event_name": event_name}
        )

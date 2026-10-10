"""
Events Router: Handles event enrollment and team registration under strict business rules.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.database.session import get_db
from app.api.dependencies import get_current_college_id
from app.domain.schemas import (
    EventRegisterRequest,
    EventRegisterResponse,
    APIResponse,
)
from app.core.constants import EVENT_RULES_MATRIX, GENERAL_RULE_REMINDERS
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/events", tags=["Events & Registration"])


@router.post(
    "/register",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a Team for an Event"
)
def register_for_event(
    request: EventRegisterRequest,
    current_college_id: Optional[str] = Depends(get_current_college_id),
    db: Session = Depends(get_db)
):
    """
    Handles event enrollment with atomic validation:
    1. Deadline verification (timestamp <= 24/10/2026 23:59:59 IST)
    2. Event team size matrix validation
    3. Department alignment validation
    4. 25-Student unique contingent cap enforcement
    5. Single team per college validation
    """
    # Prefer college_id from body if provided; otherwise use authenticated token
    effective_college_id = request.college_id or current_college_id
    if not effective_college_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="college_id must be provided in the request body or via 'Authorization: Bearer <token>' header."
        )

    # Set normalized effective college_id
    request.college_id = effective_college_id

    response_data = RegistrationService.register_event(db=db, request=request)

    return APIResponse(
        status="success",
        message=f"Team successfully registered for '{response_data.event_name}' ({response_data.department}).",
        data=response_data
    )


@router.get(
    "/matrix",
    summary="Get Official Events Matrix and Team Size Rules"
)
def get_event_matrix():
    """
    Returns the official event catalog, department groupings, and team size rules.
    """
    matrix_output: Dict[str, Any] = {}
    for event_name, info in EVENT_RULES_MATRIX.items():
        if "canonical_name" not in info:
            matrix_output[event_name] = {
                "department": info["department"].value,
                "team_size": info["team_size"],
                "description": info["description"],
                "category": info["category"]
            }

    return {
        "status": "success",
        "fest_title": "MAHAVEERA FEST 2K26",
        "event_date": "30 October 2026",
        "max_unique_students_per_college": 25,
        "registration_deadline": "24/10/2026 23:59:59 IST",
        "events": matrix_output,
        "rule_reminders": GENERAL_RULE_REMINDERS
    }

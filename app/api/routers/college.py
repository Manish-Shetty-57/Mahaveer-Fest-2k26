"""
College Router: Endpoints for college registration and status inquiries.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.domain.schemas import (
    CollegeRegisterRequest,
    CollegeStatusQueryRequest,
    CollegeResponse,
    CollegeStatusResponse,
    APIResponse,
)
from app.services.college_service import CollegeService

router = APIRouter(prefix="/college", tags=["Colleges"])


@router.post(
    "/register",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register or Authenticate College Details"
)
def register_college(
    request: CollegeRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Registers or authenticates a PU college for Mahaveera Fest 2K26.
    Returns the persistent college_id, authentication token, and current student capacity.
    """
    college_data = CollegeService.register_or_get_college(db, request)
    return APIResponse(
        status="success",
        message=f"College '{college_data.college_name}' successfully registered/authenticated.",
        data=college_data
    )


@router.get(
    "/{college_id}/status",
    response_model=APIResponse,
    summary="Check College Enrollment Quota Status"
)
def get_college_status(
    college_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the current unique student count, remaining quota under 25, and enrolled events.
    """
    status_data = CollegeService.get_college_status(db, college_id)
    return APIResponse(
        status="success",
        message=f"Quota status retrieved for college {status_data.college_name}",
        data=status_data
    )


@router.post(
    "/status",
    response_model=APIResponse,
    summary="Verify College and Faculty Email, Return All Registered Students and Events"
)
def query_college_status(
    request: CollegeStatusQueryRequest,
    db: Session = Depends(get_db)
):
    """
    Verifies College Name and Faculty Email, returning only that specific college's
    registered students, their assigned events, and total unique student count.
    """
    detailed_data = CollegeService.query_college_detailed_status(
        db,
        college_name=request.college_name,
        faculty_email=str(request.faculty_email)
    )
    return APIResponse(
        status="success",
        message=f"Registration details retrieved for {detailed_data['college_name']}.",
        data=detailed_data
    )

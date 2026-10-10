from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.admin_service import AdminService
from app.domain.schemas import APIResponse
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["Admin & Organization"])


@router.get(
    "/summary",
    response_model=APIResponse,
    summary="Get Fest Participation Summary and Rosters"
)
def get_fest_summary(
    ADMIN_SECRET_KEY: Optional[str] = Query(None, description="Secret admin verification key"),
    college_id: Optional[str] = Query(None, description="Filter rosters by College ID"),
    department: Optional[str] = Query(None, description="Filter by department (SCIENCE, COMMERCE, IT, HUMANITIES)"),
    event_name: Optional[str] = Query(None, description="Filter rosters by Event Name"),
    db: Session = Depends(get_db)
):
    """
    Generates event-wise and college-wise participation rosters, unique student headcounts,
    and department breakdowns for organizing faculty. Protected by ADMIN_SECRET_KEY.
    """
    if not ADMIN_SECRET_KEY or ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "error_code": "RESTRICTED_AREA",
                "message": "Restricted Area. Valid ADMIN_SECRET_KEY is required."
            }
        )

    summary_data = AdminService.get_fest_summary(
        db=db,
        college_id=college_id,
        department=department,
        event_name=event_name
    )

    return APIResponse(
        status="success",
        message="Fest participation summary and rosters compiled successfully.",
        data=summary_data
    )

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.admin_service import AdminService
from app.domain.schemas import APIResponse
from app.core.config import settings
from app.domain.models import College, Student, Registration, registration_members
from pydantic import BaseModel

class CollegeUpdate(BaseModel):
    college_name: Optional[str] = None
    faculty_coordinator_name: Optional[str] = None
    faculty_phone: Optional[str] = None
    faculty_email: Optional[str] = None

class StudentUpdate(BaseModel):
    student_name: Optional[str] = None
    student_phone: Optional[str] = None
    puc_year: Optional[str] = None

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

@router.delete("/college/{college_id}", response_model=APIResponse)
def delete_college(
    college_id: str,
    ADMIN_SECRET_KEY: Optional[str] = Query(None, description="Secret admin verification key"),
    db: Session = Depends(get_db)
):
    if not ADMIN_SECRET_KEY or ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "error_code": "RESTRICTED_AREA",
                "message": "Restricted Area. Valid ADMIN_SECRET_KEY is required."
            }
        )
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    name = college.college_name
    db.delete(college)
    db.commit()
    return APIResponse(status="success", message=f"Deleted college {name}", data=None)

@router.delete("/registration/{registration_id}", response_model=APIResponse)
def delete_registration(
    registration_id: str,
    ADMIN_SECRET_KEY: Optional[str] = Query(None, description="Secret admin verification key"),
    db: Session = Depends(get_db)
):
    if not ADMIN_SECRET_KEY or ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "error_code": "RESTRICTED_AREA",
                "message": "Restricted Area. Valid ADMIN_SECRET_KEY is required."
            }
        )
    reg = db.query(Registration).filter(Registration.id == registration_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    event_name = reg.event_name
    college = db.query(College).filter(College.id == reg.college_id).first()
    college_name = college.college_name if college else "Unknown"
    db.delete(reg)
    db.commit()
    return APIResponse(status="success", message=f"Deleted event {event_name} and college {college_name}", data=None)

@router.put("/college/{college_id}", response_model=APIResponse)
def update_college(
    college_id: str,
    update_data: CollegeUpdate,
    ADMIN_SECRET_KEY: Optional[str] = Query(None, description="Secret admin verification key"),
    db: Session = Depends(get_db)
):
    if not ADMIN_SECRET_KEY or ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "error_code": "RESTRICTED_AREA",
                "message": "Restricted Area. Valid ADMIN_SECRET_KEY is required."
            }
        )
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    
    update_dict = update_data.model_dump(exclude_unset=True) if hasattr(update_data, "model_dump") else update_data.dict(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(college, k, v)
    db.commit()
    db.refresh(college)
    return APIResponse(status="success", message="College updated successfully", data={"id": college.id, "college_name": college.college_name})

@router.put("/student/{student_id}", response_model=APIResponse)
def update_student(
    student_id: str,
    update_data: StudentUpdate,
    ADMIN_SECRET_KEY: Optional[str] = Query(None, description="Secret admin verification key"),
    db: Session = Depends(get_db)
):
    if not ADMIN_SECRET_KEY or ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "error_code": "RESTRICTED_AREA",
                "message": "Restricted Area. Valid ADMIN_SECRET_KEY is required."
            }
        )
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    update_dict = update_data.model_dump(exclude_unset=True) if hasattr(update_data, "model_dump") else update_data.dict(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(student, k, v)
    db.commit()
    db.refresh(student)
    return APIResponse(status="success", message="Student updated successfully", data={"id": student.id, "student_name": student.student_name})

@router.delete("/student/{student_id}", response_model=APIResponse)
def delete_student(
    student_id: str,
    ADMIN_SECRET_KEY: Optional[str] = Query(None, description="Secret admin verification key"),
    db: Session = Depends(get_db)
):
    if not ADMIN_SECRET_KEY or ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "error_code": "RESTRICTED_AREA",
                "message": "Restricted Area. Valid ADMIN_SECRET_KEY is required."
            }
        )
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    db.execute(registration_members.delete().where(registration_members.c.student_id == student_id))
    
    college_id = student.college_id
    db.delete(student)
    
    college = db.query(College).filter(College.id == college_id).first()
    if college:
        college.total_students_registered = max(0, college.total_students_registered - 1)
        
    db.commit()
    return APIResponse(status="success", message="Student deleted successfully", data=None)

@router.post("/clear-all", response_model=APIResponse)
def clear_all(
    ADMIN_SECRET_KEY: Optional[str] = Query(None, description="Secret admin verification key"),
    db: Session = Depends(get_db)
):
    if not ADMIN_SECRET_KEY or ADMIN_SECRET_KEY != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "error_code": "RESTRICTED_AREA",
                "message": "Restricted Area. Valid ADMIN_SECRET_KEY is required."
            }
        )
    
    deleted_members = db.execute(registration_members.delete()).rowcount
    deleted_regs = db.query(Registration).delete()
    deleted_students = db.query(Student).delete()
    deleted_colleges = db.query(College).delete()
    
    db.commit()
    
    return APIResponse(status="success", message="All data cleared successfully", data={"registration_members": deleted_members, "registrations": deleted_regs, "students": deleted_students, "colleges": deleted_colleges})

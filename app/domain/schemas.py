"""
Pydantic validation schemas for API inputs, outputs, and validation rules.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
import re
from app.core.constants import DepartmentEnum, PUCYearEnum, GENERAL_RULE_REMINDERS, MAX_COLLEGE_STUDENTS_CAP


# ==========================================
# College Schemas
# ==========================================

class CollegeRegisterRequest(BaseModel):
    college_name: str = Field(..., min_length=3, max_length=255, description="Full registered name of the PU college")
    faculty_coordinator_name: str = Field(..., min_length=2, max_length=255, description="Name of accompanying faculty coordinator")
    faculty_phone: str = Field(..., description="Active phone/mobile number of the faculty coordinator")
    faculty_email: EmailStr = Field(..., description="Official contact email of the faculty coordinator")

    @field_validator("college_name", "faculty_coordinator_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("String field cannot be empty or whitespace only")
        return v

    @field_validator("faculty_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean_phone = re.sub(r"[\s\-\(\)]", "", v)
        # Supports +91... or standard 10-15 digit numbers
        if not re.match(r"^(\+?[0-9]{10,15})$", clean_phone):
            raise ValueError("Invalid phone number format. Provide a valid 10-15 digit contact number.")
        return clean_phone


class CollegeResponse(BaseModel):
    college_id: str
    college_name: str
    faculty_coordinator_name: str
    faculty_phone: str
    faculty_email: str
    total_students_registered: int
    remaining_student_quota: int
    access_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
    registered_events: Optional[List[str]] = []


class CollegeStatusQueryRequest(BaseModel):
    college_name: str = Field(..., min_length=2, max_length=255, description="Full or partial registered name of the PU college")
    faculty_email: EmailStr = Field(..., description="Official email of the registered faculty coordinator")

    @field_validator("college_name")
    @classmethod
    def sanitize_college_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("College name cannot be empty")
        return v


class CollegeEventRegistrationDetail(BaseModel):
    event_name: str
    department: str
    team_members: List[Dict[str, Any]]


class CollegeStudentDetail(BaseModel):
    id: str
    student_name: str
    student_phone: Optional[str] = None
    puc_year: str
    events: List[str] = []


class DetailedCollegeStatusResponse(BaseModel):
    college_id: str
    college_name: str
    faculty_coordinator_name: str
    faculty_phone: str
    faculty_email: str
    total_unique_students: int
    max_capacity_cap: int = MAX_COLLEGE_STUDENTS_CAP
    remaining_quota: int
    is_quota_full: bool
    registered_events: List[CollegeEventRegistrationDetail]
    students: List[CollegeStudentDetail]
    rule_reminders: Dict[str, Any] = GENERAL_RULE_REMINDERS


class CollegeStatusResponse(BaseModel):
    college_id: str
    college_name: str
    faculty_coordinator_name: str
    faculty_phone: str
    faculty_email: str
    total_unique_students: int
    max_capacity_cap: int = MAX_COLLEGE_STUDENTS_CAP
    remaining_quota: int
    is_quota_full: bool
    registered_events: List[str]
    rule_reminders: Dict[str, Any] = GENERAL_RULE_REMINDERS


# ==========================================
# Student Schemas
# ==========================================

class ParticipantInput(BaseModel):
    student_name: str = Field(..., min_length=2, max_length=255, description="Full student name as per College ID")
    student_phone: Optional[str] = Field(None, description="Active participant mobile/phone number")
    puc_year: PUCYearEnum = Field(..., description="Academic year: '1st PUC' or '2nd PUC'")

    @field_validator("student_name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = re.sub(r"\s+", " ", v.strip())
        if len(v) < 2:
            raise ValueError("Student name must be at least 2 characters")
        return v

    @field_validator("student_phone")
    @classmethod
    def validate_student_phone(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean_phone = re.sub(r"[\s\-\(\)]", "", v.strip())
        if not clean_phone:
            return None
        if not re.match(r"^(\+?[0-9]{10,15})$", clean_phone):
            raise ValueError("Invalid student phone number format. Provide a valid 10-15 digit contact number.")
        return clean_phone


class StudentResponse(BaseModel):
    id: str
    student_name: str
    student_phone: Optional[str] = None
    puc_year: str
    college_id: str

    model_config = {"from_attributes": True}



# ==========================================
# Event Registration Schemas
# ==========================================

class EventRegisterRequest(BaseModel):
    college_id: Optional[str] = Field(None, description="College UUID (can also be derived from Bearer token)")
    event_name: str = Field(..., min_length=2, max_length=100, description="Official event name")
    department: DepartmentEnum = Field(..., description="Department organizing the event")
    participants: List[ParticipantInput] = Field(..., min_length=1, description="List of participant students")

    @field_validator("event_name")
    @classmethod
    def clean_event_name(cls, v: str) -> str:
        return v.strip()


class EventRegisterResponse(BaseModel):
    registration_id: str
    college_id: str
    college_name: str
    event_name: str
    department: str
    team_size: int
    team_members: List[StudentResponse]
    newly_introduced_students_count: int
    total_unique_students_registered: int
    remaining_college_quota: int
    rule_reminders: Dict[str, Any] = GENERAL_RULE_REMINDERS


# ==========================================
# Admin and Reporting Schemas
# ==========================================

class EventRosterItem(BaseModel):
    registration_id: str
    college_id: str
    college_name: str
    faculty_coordinator: str
    faculty_phone: str
    team_members: List[StudentResponse]


class EventSummaryItem(BaseModel):
    event_name: str
    department: str
    required_team_size: int
    total_teams_registered: int
    total_participants: int
    roster: List[EventRosterItem]


class CollegeSummaryItem(BaseModel):
    college_id: str
    college_name: str
    faculty_coordinator_name: str
    faculty_phone: str
    faculty_email: str
    total_unique_students: int
    remaining_quota: int
    events_enrolled: List[str]
    unique_students_roster: List[StudentResponse]


class AdminSummaryResponse(BaseModel):
    summary_generated_at: str
    fest_title: str = "MAHAVEERA FEST 2K26"
    fest_date: str = "30 October 2026"
    venue: str = "Sri Mahaveera College, Moodbidri"
    total_colleges: int
    total_unique_students_across_fest: int
    total_event_enrollments: int
    department_stats: Dict[str, int]
    college_wise_summary: List[CollegeSummaryItem]
    event_wise_summary: List[EventSummaryItem]
    rule_reminders: Dict[str, Any] = GENERAL_RULE_REMINDERS


# ==========================================
# Generic API Wrapper
# ==========================================

class APIResponse(BaseModel):
    status: str = "success"
    message: str
    data: Any
    rule_reminders: Optional[Dict[str, Any]] = GENERAL_RULE_REMINDERS

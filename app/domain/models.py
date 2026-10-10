"""
Database ORM models for Mahaveera Fest 2K26.
Compatible with SQLite and PostgreSQL.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Table,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Association table representing the many-to-many relationship
# between Registrations and participating Students
registration_members = Table(
    "registration_members",
    Base.metadata,
    Column("registration_id", String(36), ForeignKey("registrations.id", ondelete="CASCADE"), primary_key=True),
    Column("student_id", String(36), ForeignKey("students.id", ondelete="RESTRICT"), primary_key=True),
    Index("ix_reg_member_student", "student_id"),
    Index("ix_reg_member_registration", "registration_id"),
)


class College(Base):
    __tablename__ = "colleges"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    college_name = Column(String(255), unique=True, nullable=False, index=True)
    faculty_coordinator_name = Column(String(255), nullable=False)
    faculty_phone = Column(String(20), nullable=False)
    faculty_email = Column(String(255), nullable=False, index=True)
    total_students_registered = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    students = relationship("Student", back_populates="college", cascade="all, delete-orphan")
    registrations = relationship("Registration", back_populates="college", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<College id={self.id} name='{self.college_name}' registered_count={self.total_students_registered}>"


class Student(Base):
    __tablename__ = "students"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    student_name = Column(String(255), nullable=False)
    student_phone = Column(String(20), nullable=True)  # Participant phone number
    puc_year = Column(String(20), nullable=False)  # "1st PUC" or "2nd PUC"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    college = relationship("College", back_populates="students")
    registrations = relationship("Registration", secondary=registration_members, back_populates="team_members")

    __table_args__ = (
        Index("ix_students_college_name_puc", "college_id", "student_name", "puc_year"),
        Index("ix_students_phone", "student_phone"),
    )


    def __repr__(self) -> str:
        return f"<Student id={self.id} name='{self.student_name}' year='{self.puc_year}'>"


class Registration(Base):
    __tablename__ = "registrations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    event_name = Column(String(100), nullable=False)
    department = Column(String(50), nullable=False)  # SCIENCE, COMMERCE, IT, HUMANITIES
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    college = relationship("College", back_populates="registrations")
    team_members = relationship("Student", secondary=registration_members, back_populates="registrations")

    __table_args__ = (
        UniqueConstraint("college_id", "event_name", name="uq_college_event_registration"),
        Index("ix_registrations_college_dept", "college_id", "department"),
    )

    def __repr__(self) -> str:
        return f"<Registration id={self.id} event='{self.event_name}' dept='{self.department}'>"

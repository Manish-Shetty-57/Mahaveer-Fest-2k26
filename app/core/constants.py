"""
Core constants, event matrices, and business rule definitions for Mahaveera Fest 2K26.
Sri Mahaveera College, Moodbidri (Held on 30 October 2026).
"""
from enum import Enum
from typing import Dict, Any


class DepartmentEnum(str, Enum):
    SCIENCE = "SCIENCE"
    COMMERCE = "COMMERCE"
    IT = "IT"
    HUMANITIES = "HUMANITIES"


class PUCYearEnum(str, Enum):
    FIRST_PUC = "1st PUC"
    SECOND_PUC = "2nd PUC"


# Event rules and team sizes as per the official brochure
# Science: NOVEXA
# Commerce: COMQUEST
# IT: UTKARSH
# Humanities: MAHAVITH
EVENT_RULES_MATRIX: Dict[str, Dict[str, Any]] = {
    # SCIENCE (NOVEXA)
    "Math Crunch": {
        "department": DepartmentEnum.SCIENCE,
        "team_size": 4,
        "description": "The Mathematical Race - 4 participants per team",
        "category": "NOVEXA",
    },
    "Chemvista": {
        "department": DepartmentEnum.SCIENCE,
        "team_size": 1,
        "description": "Exploring Ideas, Expanding Horizons - Individual presentation",
        "category": "NOVEXA",
    },
    "Physispark": {
        "department": DepartmentEnum.SCIENCE,
        "team_size": 2,
        "description": "Igniting Ideas, Bringing Physics to Life - 2 participants",
        "category": "NOVEXA",
    },

    # COMMERCE (COMQUEST)
    "Brand Rangoli": {
        "department": DepartmentEnum.COMMERCE,
        "team_size": 2,
        "description": "Brand Rangoli for a company/brand - 2 participants",
        "category": "COMQUEST",
    },
    "Olympus Oracle Business Quiz": {
        "department": DepartmentEnum.COMMERCE,
        "team_size": 2,
        "description": "Business Quiz - 2 participants",
        "category": "COMQUEST",
    },
    "Olympus Oracle": {  # Alias for Olympus Oracle Business Quiz
        "department": DepartmentEnum.COMMERCE,
        "team_size": 2,
        "description": "Business Quiz (Alias) - 2 participants",
        "category": "COMQUEST",
        "canonical_name": "Olympus Oracle Business Quiz",
    },
    "Pandora's Mystery": {
        "department": DepartmentEnum.COMMERCE,
        "team_size": 1,
        "description": "Special Event - Individual participation (1 member)",
        "category": "COMQUEST",
    },

    # IT (UTKARSH)
    "Code Wars": {
        "department": DepartmentEnum.IT,
        "team_size": 2,
        "description": "Coding / Programming Competition (Python debugging) - 2 participants",
        "category": "UTKARSH",
    },
    "Prompt Wars": {
        "department": DepartmentEnum.IT,
        "team_size": 2,
        "description": "AI Prompt Engineering & Image Generation - 2 participants",
        "category": "UTKARSH",
    },
    "Mind Wars": {
        "department": DepartmentEnum.IT,
        "team_size": 2,
        "description": "IT Quiz Competition (Science & IT) - 2 participants",
        "category": "UTKARSH",
    },
    "Innovation Wars": {
        "department": DepartmentEnum.IT,
        "team_size": 2,
        "description": "Imaginary Product Launch & Startup Pitch - 2 participants",
        "category": "UTKARSH",
    },

    # HUMANITIES (MAHAVITH)
    "Arthalankara": {
        "department": DepartmentEnum.HUMANITIES,
        "team_size": 2,
        "description": "Eco Rangoli Competition (Economics-themed) - 2 participants",
        "category": "MAHAVITH",
    },
    "Chitra Phalakam": {
        "department": DepartmentEnum.HUMANITIES,
        "team_size": 2,
        "description": "Collage Competition (Historical places of Karnataka) - 2 participants",
        "category": "MAHAVITH",
    },
    "Chitra Pratiyogita": {
        "department": DepartmentEnum.HUMANITIES,
        "team_size": 1,
        "description": "Pencil Sketch Competition (Political Science) - 1 participant",
        "category": "MAHAVITH",
    },
}

# Maximum unique participating students allowed per college across all events
MAX_COLLEGE_STUDENTS_CAP = 25

# Official General Rule Reminders for all participants and faculty
GENERAL_RULE_REMINDERS = {
    "registration_fee": "No registration fee (Free participation).",
    "mandatory_documents": [
        "Original College ID card for every participant",
        "Official authorization letter/card from the college principal or head"
    ],
    "reporting_time": "All participants must report to the campus before 8:45 AM on 30 October 2026 for registration and badge verification.",
    "event_date": "30 October 2026",
    "venue": "Sri Mahaveera College, Kodangallu - 574197, Moodbidri, D.K. District, Karnataka",
    "hospitality": "Complimentary breakfast and lunch will be provided to all registered participants and accompanying faculty.",
    "ta_da": "No TA/DA will be provided.",
    "certificates": "A Certificate of Participation will be awarded to every student.",
    "judging": "The judges' and organizers' decision will be final and binding."
}

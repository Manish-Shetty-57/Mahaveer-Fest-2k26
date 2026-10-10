# MAHAVEERA FEST 2K26 - Backend System & Business Logic Engine

> **Intercollegiate Competition for Pre-University (PU) Students**  
> **Organized by:** Internal Quality Assurance Cell (IQAC), Science (NOVEXA), Commerce (COMQUEST), IT (UTKARSH), and Humanities (MAHAVITH) Associations  
> **Venue:** Sri Mahaveera College, Kodangallu - 574197, Moodbidri, D.K. District, Karnataka  
> **Event Date:** 30 October 2026  
> **Registration Deadline:** 24 October 2026 at 23:59:59 IST  

---

## 1. Architectural Overview & System Design

The backend system is designed with **Clean Architecture** and **Domain-Driven Design (DDD)** principles to guarantee high reliability, strict business rule enforcement, zero over-registration, and atomic data consistency.

```
┌────────────────────────────────────────────────────────┐
│                   Client Layer (Web UI)                │
└───────────────────────────┬────────────────────────────┘
                            │ REST / JSON (JWT / Headers)
┌───────────────────────────▼────────────────────────────┐
│                  FastAPI Application Gateway           │
│  - CORS Middleware & Request Validation (Pydantic V2)  │
│  - Unified Domain Error & Validation Handlers          │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                    API Routing Layer                   │
│  - POST /api/college/register                          │
│  - GET  /api/college/{id}/status                       │
│  - POST /api/events/register                           │
│  - GET  /api/events/matrix                             │
│  - GET  /api/admin/summary                             │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│               Service & Business Logic Engine          │
│  Rule 1: 25-Unique Student Contingent Cap Engine       │
│  Rule 2: Event Team-Size & Department Matrix Engine    │
│  Rule 3: Registration Deadline Enforcement (IST Clock) │
│  Rule 4: Automated Rule Reminders Feedback             │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│               Data Persistence Layer                   │
│  - Production PostgreSQL (DDL, Triggers, Constraints)  │
│  - Production MongoDB (JSON Schema & Indexes)          │
│  - SQLAlchemy ORM with ACID Transactions               │
└────────────────────────────────────────────────────────┘
```

---

## 2. Database Schema Design

### 2.1 PostgreSQL Relational Design
The PostgreSQL schema uses standard relational normalization with foreign keys, compound indexes, unique constraints, and database-level trigger functions.

* **Colleges Table (`colleges`)**:
  - `id`: UUID (Primary Key, default `uuid_generate_v4()`)
  - `college_name`: `VARCHAR(255)` (Unique, Indexed)
  - `faculty_coordinator_name`: `VARCHAR(255)`
  - `faculty_phone`: `VARCHAR(20)`
  - `faculty_email`: `VARCHAR(255)`
  - `total_students_registered`: `INTEGER` (Default `0`, `CHECK (total_students_registered >= 0 AND total_students_registered <= 25)`)
  - `created_at`, `updated_at`: `TIMESTAMP WITH TIME ZONE`

* **Students Table (`students`)**:
  - `id`: UUID (Primary Key)
  - `college_id`: UUID (Foreign Key to `colleges.id` ON DELETE CASCADE)
  - `student_name`: `VARCHAR(255)`
  - `puc_year`: `puc_year_enum` (`'1st PUC'`, `'2nd PUC'`)
  - `created_at`, `updated_at`: `TIMESTAMP WITH TIME ZONE`
  - Constraint: `UNIQUE (college_id, student_name, puc_year)`

* **Registrations Table (`registrations`)**:
  - `id`: UUID (Primary Key)
  - `college_id`: UUID (Foreign Key to `colleges.id` ON DELETE CASCADE)
  - `event_name`: `VARCHAR(100)`
  - `department`: `department_enum` (`'SCIENCE'`, `'COMMERCE'`, `'IT'`, `'HUMANITIES'`)
  - `created_at`, `updated_at`: `TIMESTAMP WITH TIME ZONE`
  - Constraint: `UNIQUE (college_id, event_name)` *(Enforces 1 team per college per event)*

* **Registration Members Table (`registration_members`)**:
  - `registration_id`: UUID (Foreign Key to `registrations.id` ON DELETE CASCADE)
  - `student_id`: UUID (Foreign Key to `students.id` ON DELETE RESTRICT)
  - Primary Key: `(registration_id, student_id)`

> Full DDL script located at: [`schemas/postgresql_schema.sql`](file:///c:/Users/ACER/OneDrive/Desktop/Mahaveer-Fest-2k26/schemas/postgresql_schema.sql)

### 2.2 MongoDB Document Design
MongoDB collections are provisioned with `$jsonSchema` validators and compound unique indexes.

* **`colleges` collection**: Contains coordinator contacts and indexed `college_name`.
* **`students` collection**: Contains student names and PUC year, indexed by `{ college_id: 1, student_name: 1, puc_year: 1 }`.
* **`registrations` collection**: Contains `team_members` as an array of Student UUID references with size bounds and uniqueness:
  ```json
  {
    "_id": "c1f7b822-482f-4a3e-b816-466d713ee099",
    "college_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "event_name": "Math Crunch",
    "department": "SCIENCE",
    "team_members": [
      "1e6b35d0-9f5b-4352-823a-e01f609e3f01",
      "2a7c41e1-8c4d-4e99-8877-a12b3c4d5e6f",
      "3b8d52f2-7d3e-4fa0-9988-b23c4d5e6f7a",
      "4c9e63a3-6e2f-40b1-aa99-c34d5e6f7a8b"
    ],
    "created_at": "ISODate('2026-10-15T10:00:00Z')",
    "updated_at": "ISODate('2026-10-15T10:00:00Z')"
  }
  ```

> Full MongoDB schema script located at: [`schemas/mongodb_schema.js`](file:///c:/Users/ACER/OneDrive/Desktop/Mahaveer-Fest-2k26/schemas/mongodb_schema.js)

---

## 3. Core Backend Logic & Business Constraints

### Rule 1: The 25-Student College Cap (Unique Student Tracking)
* **Invariant:** No college may register more than 25 unique students across all events combined.
* **Cross-Event Deduplication:** If an individual student participates in multiple events (e.g. Rahul Rao registers for *Math Crunch* and *Prompt Wars*), he is counted **only once** toward the college's 25-student contingent limit.
* **Transaction Isolation:** In concurrent registration attempts, the college record is locked (`SELECT FOR UPDATE`), the current set of distinct enrolled student IDs is queried:
  $$\text{Current Unique} = |\{s \in \text{Students} \mid s \in \text{RegisteredTeams}(\text{college})\}|$$
  $$\text{Projected Total} = |(\text{Current Unique Students}) \cup (\text{New Participants})|$$
* If $\text{Projected Total} > 25$, the transaction rolls back immediately and returns HTTP `422 Unprocessable Content` with the exact violation details (current count, new students attempted, projected total, and remaining margin).

### Rule 2: Strict Event Team-Size Validation Matrix
Each event strictly enforces the official team size and department grouping. Requests with incorrect sizes or mismatched departments are immediately rejected:

| Department | Event Name | Official Category | Team Size | Participation Type |
| :--- | :--- | :--- | :---: | :--- |
| **SCIENCE** | Math Crunch | NOVEXA | **4** | Team (The Mathematical Race) |
| **SCIENCE** | Chemvista | NOVEXA | **1** | Individual Presentation |
| **SCIENCE** | Physispark | NOVEXA | **2** | Team (Physics Working Model) |
| **COMMERCE** | Brand Rangoli | COMQUEST | **2** | Team |
| **COMMERCE** | Olympus Oracle Business Quiz | COMQUEST | **2** | Team |
| **COMMERCE** | Pandora's Mystery | COMQUEST | **1** | Individual Special Event |
| **IT** | Code Wars | UTKARSH | **2** | Team (Python Debugging) |
| **IT** | Prompt Wars | UTKARSH | **2** | Team (AI Prompt Engg & Image Gen) |
| **IT** | Mind Wars | UTKARSH | **2** | Team (IT & Science Quiz) |
| **IT** | Innovation Wars | UTKARSH | **2** | Team (Startup Pitch & Product Launch) |
| **HUMANITIES** | Arthalankara | MAHAVITH | **2** | Team (Eco Rangoli) |
| **HUMANITIES** | Chitra Phalakam | MAHAVITH | **2** | Team (Collage - Historical Karnataka) |
| **HUMANITIES** | Chitra Pratiyogita | MAHAVITH | **1** | Individual (Pencil Sketch) |

*Single Team Constraint:* A college can register only **one team per event**. Duplicate submissions return HTTP `409 Conflict`.  
*Duplicate Participant Defense:* Submitting the same student twice in the same event team payload is rejected with HTTP `422`.

### Rule 3: Registration Deadline Enforcement
* **Deadline:** **24/10/2026 23:59:59 IST** (`2026-10-24T23:59:59+05:30`).
* Any registration submission with server timestamp > deadline is rejected with HTTP `403 Forbidden` (`REGISTRATION_DEADLINE_EXCEEDED`).

### Rule 4: Mandatory Rule Reminders in API Feedback
Every response payload automatically delivers the institutional instructions:
1. **No registration fee** (Participation is free).
2. **Mandatory documents:** Original College ID card and authorization letter/card from the college.
3. **Reporting time:** Before **8:45 AM on 30 October 2026** at Sri Mahaveera College, Moodbidri.
4. **Hospitality:** Complimentary breakfast and lunch provided for participants and faculty coordinators.

---

## 4. API Endpoints & Workflow

### 4.1 Register / Authenticate College
* **Endpoint:** `POST /api/college/register`
* **Request:**
  ```json
  {
    "college_name": "Canara PU College, Mangaluru",
    "faculty_coordinator_name": "Prof. Savitha Hegde",
    "faculty_phone": "+91 9845123456",
    "faculty_email": "savitha@canaracollege.in"
  }
  ```
* **Response (HTTP 201):**
  ```json
  {
    "status": "success",
    "message": "College 'Canara PU College, Mangaluru' successfully registered/authenticated.",
    "data": {
      "college_id": "c1f7b822-482f-4a3e-b816-466d713ee099",
      "college_name": "Canara PU College, Mangaluru",
      "faculty_coordinator_name": "Prof. Savitha Hegde",
      "faculty_phone": "9845123456",
      "faculty_email": "savitha@canaracollege.in",
      "total_students_registered": 0,
      "remaining_student_quota": 25,
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer"
    },
    "rule_reminders": { ... }
  }
  ```

---

### 4.2 Enroll Team into an Event
* **Endpoint:** `POST /api/events/register`
* **Headers:** `Authorization: Bearer <token>` (or pass `college_id` in request body)
* **Request:**
  ```json
  {
    "college_id": "c1f7b822-482f-4a3e-b816-466d713ee099",
    "event_name": "Math Crunch",
    "department": "SCIENCE",
    "participants": [
      { "student_name": "Aryan Shenoy", "puc_year": "2nd PUC" },
      { "student_name": "Bhavya Pai", "puc_year": "1st PUC" },
      { "student_name": "Chetan Prabhu", "puc_year": "2nd PUC" },
      { "student_name": "Deepa Kamath", "puc_year": "1st PUC" }
    ]
  }
  ```
* **Response (HTTP 201):**
  ```json
  {
    "status": "success",
    "message": "Team successfully registered for 'Math Crunch' (SCIENCE).",
    "data": {
      "registration_id": "8a0ef93e-2b5d-4c31-9b0d-58b88523b123",
      "college_id": "c1f7b822-482f-4a3e-b816-466d713ee099",
      "college_name": "Canara PU College, Mangaluru",
      "event_name": "Math Crunch",
      "department": "SCIENCE",
      "team_size": 4,
      "team_members": [
        {
          "id": "1e6b35d0-9f5b-4352-823a-e01f609e3f01",
          "student_name": "Aryan Shenoy",
          "puc_year": "2nd PUC",
          "college_id": "c1f7b822-482f-4a3e-b816-466d713ee099"
        },
        ...
      ],
      "newly_introduced_students_count": 4,
      "total_unique_students_registered": 4,
      "remaining_college_quota": 21
    },
    "rule_reminders": { ... }
  }
  ```

---

### 4.3 Check College Contingent Status
* **Endpoint:** `GET /api/college/{college_id}/status`
* **Response (HTTP 200):**
  ```json
  {
    "status": "success",
    "message": "Quota status retrieved for college Canara PU College, Mangaluru",
    "data": {
      "college_id": "c1f7b822-482f-4a3e-b816-466d713ee099",
      "college_name": "Canara PU College, Mangaluru",
      "faculty_coordinator_name": "Prof. Savitha Hegde",
      "faculty_phone": "9845123456",
      "faculty_email": "savitha@canaracollege.in",
      "total_unique_students": 4,
      "max_capacity_cap": 25,
      "remaining_quota": 21,
      "is_quota_full": false,
      "registered_events": [
        "Math Crunch"
      ]
    }
  }
  ```

---

### 4.4 Admin Fest Summary & Event Rosters
* **Endpoint:** `GET /api/admin/summary`
* **Query Parameters:** `?department=SCIENCE` / `?college_id=...` / `?event_name=...`
* **Response (HTTP 200):**
  Generates event-wise and college-wise participation rosters, student rosters, faculty contact lists, and department breakdowns for organizers.

---

### 4.5 Official Events Matrix & Rules
* **Endpoint:** `GET /api/events/matrix`
* **Response (HTTP 200):**
  Returns all 13 events, team sizes, descriptions, deadline info, and reminders.

---

## 5. Verification & Automated Test Suite

A complete test suite is provided covering all edge cases, business constraints, and API flows:

```powershell
python -m pytest -v
```

**Results:**
- `test_api_full_workflow`: College registration, token generation, team enrollment, quota updates, admin summary.
- `test_api_invalid_team_size_error_payload`: Rejection of improper team sizes with structured details.
- `test_api_validation_error_puc_year`: Schema validation rejecting non-PUC grades.
- `test_deadline_enforcement_valid`: Timestamps before 24/10/2026 23:59:59 IST succeed.
- `test_deadline_enforcement_exceeded`: Timestamps past deadline are rejected with HTTP 403.
- `test_team_size_math_crunch_exact_4`: Verifies exact team size 4 requirement.
- `test_department_mismatch_rejection`: Rejects events registered under wrong departments.
- `test_duplicate_participant_in_same_team_rejection`: Catches duplicated students in the payload.
- `test_single_team_per_college_rule`: Enforces maximum 1 team per college per event.
- `test_unique_student_tracking_multiple_events`: Verifies cross-event deduplication (student participating in multiple events is counted only once toward the 25 pool).
- `test_25_student_cap_enforcement_and_overflow`: Verifies strict rejection when projected unique student count exceeds the cap.

---

## 6. How to Run the Server

```powershell
# Run the backend with Uvicorn
python run_server.py
```
Or directly via uvicorn:
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* **Interactive OpenAPI Documentation (Swagger UI):** `http://localhost:8000/docs`
* **ReDoc Documentation:** `http://localhost:8000/redoc`
* **Health & Deadline Status:** `http://localhost:8000/api/health`
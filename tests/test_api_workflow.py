"""
Integration and End-to-End API workflow test suite for Mahaveera Fest 2K26.
"""
from fastapi.testclient import TestClient


def test_api_full_workflow(client: TestClient):
    """
    Tests the complete API lifecycle:
    1. College registration -> token generation
    2. Event registration with team members
    3. Rule reminders feedback in response
    4. Quota status check
    5. Admin summary generation
    """
    # 1. Register College
    college_payload = {
        "college_name": "Govt PU College, Mangaluru",
        "faculty_coordinator_name": "Dr. Ramesh Nayak",
        "faculty_phone": "+91 9448123456",
        "faculty_email": "ramesh.nayak@govpuc.ac.in"
    }
    col_res = client.post("/api/college/register", json=college_payload)
    assert col_res.status_code == 201
    col_json = col_res.json()
    assert col_json["status"] == "success"
    college_id = col_json["data"]["college_id"]
    token = col_json["data"]["access_token"]
    assert token is not None
    assert col_json["data"]["remaining_student_quota"] == 25

    # Check General Rule Reminders in response
    assert "rule_reminders" in col_json
    reminders = col_json["rule_reminders"]
    assert "No registration fee" in reminders["registration_fee"]
    assert any("College ID card" in doc for doc in reminders["mandatory_documents"])
    assert "8:45 AM" in reminders["reporting_time"]
    assert "30 October 2026" in reminders["event_date"]

    # 2. Get Events Matrix
    matrix_res = client.get("/api/events/matrix")
    assert matrix_res.status_code == 200
    matrix_data = matrix_res.json()
    assert "Math Crunch" in matrix_data["events"]
    assert matrix_data["events"]["Math Crunch"]["team_size"] == 4
    assert matrix_data["events"]["Code Wars"]["team_size"] == 2

    # 3. Register Event: Math Crunch (Science - 4 members) using Bearer Token
    event_payload = {
        "event_name": "Math Crunch",
        "department": "SCIENCE",
        "participants": [
            {"student_name": "Aryan Shenoy", "puc_year": "2nd PUC"},
            {"student_name": "Bhavya Pai", "puc_year": "1st PUC"},
            {"student_name": "Chetan Prabhu", "puc_year": "2nd PUC"},
            {"student_name": "Deepa Kamath", "puc_year": "1st PUC"}
        ]
    }
    ev_res = client.post(
        "/api/events/register",
        json=event_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert ev_res.status_code == 201
    ev_json = ev_res.json()
    assert ev_json["data"]["total_unique_students_registered"] == 4
    assert ev_json["data"]["remaining_college_quota"] == 21
    assert len(ev_json["data"]["team_members"]) == 4

    # 4. Register Event: Chemvista (Science - 1 member) with college_id in body
    chem_payload = {
        "college_id": college_id,
        "event_name": "Chemvista",
        "department": "SCIENCE",
        "participants": [
            {"student_name": "Esha Karkera", "puc_year": "2nd PUC"}
        ]
    }
    chem_res = client.post("/api/events/register", json=chem_payload)
    assert chem_res.status_code == 201
    assert chem_res.json()["data"]["total_unique_students_registered"] == 5
    assert chem_res.json()["data"]["remaining_college_quota"] == 20

    # 5. Check College Quota Status
    status_res = client.get(f"/api/college/{college_id}/status")
    assert status_res.status_code == 200
    status_json = status_res.json()["data"]
    assert status_json["total_unique_students"] == 5
    assert status_json["remaining_quota"] == 20
    assert "Math Crunch" in status_json["registered_events"]
    assert "Chemvista" in status_json["registered_events"]

    # 6. Admin Fest Summary: Verify Restricted Area without key
    unauthorized_res = client.get("/api/admin/summary")
    assert unauthorized_res.status_code == 403
    assert unauthorized_res.json()["detail"]["error_code"] == "RESTRICTED_AREA"

    # Verify access with valid ADMIN_SECRET_KEY
    admin_res = client.get("/api/admin/summary?ADMIN_SECRET_KEY=Mahaveera2026Secure")
    assert admin_res.status_code == 200
    admin_json = admin_res.json()["data"]
    assert admin_json["total_colleges"] >= 1
    assert admin_json["total_unique_students_across_fest"] == 5
    assert admin_json["total_event_enrollments"] == 2
    assert admin_json["department_stats"]["SCIENCE"] == 2

    # Check that event roster in admin summary contains our participants
    math_summary = next(item for item in admin_json["event_wise_summary"] if item["event_name"] == "Math Crunch")
    assert math_summary["total_teams_registered"] == 1
    assert math_summary["total_participants"] == 4
    assert math_summary["roster"][0]["college_name"] == "Govt PU College, Mangaluru"



def test_api_invalid_team_size_error_payload(client: TestClient):
    """Ensure invalid team size returns structured error with rule reminder."""
    # Register college
    col_res = client.post(
        "/api/college/register",
        json={
            "college_name": "Vivekananda PU College, Puttur",
            "faculty_coordinator_name": "Prof. Krishna",
            "faculty_phone": "9876543219",
            "faculty_email": "krishna@vkp.edu"
        }
    )
    college_id = col_res.json()["data"]["college_id"]

    # Physispark requires 2 participants; send 1
    bad_res = client.post(
        "/api/events/register",
        json={
            "college_id": college_id,
            "event_name": "Physispark",
            "department": "SCIENCE",
            "participants": [
                {"student_name": "Solo Student", "puc_year": "1st PUC"}
            ]
        }
    )
    assert bad_res.status_code == 422
    err_json = bad_res.json()
    assert err_json["status"] == "error"
    assert err_json["error"]["error_code"] == "INVALID_TEAM_SIZE"
    assert "expected_team_size" in err_json["error"]["details"]
    assert err_json["error"]["details"]["expected_team_size"] == 2


def test_api_validation_error_puc_year(client: TestClient):
    """Ensure invalid PUC year enum is caught by Pydantic validation."""
    col_res = client.post(
        "/api/college/register",
        json={
            "college_name": "Besant PU College, Mangaluru",
            "faculty_coordinator_name": "Prof. Shaila",
            "faculty_phone": "9876543220",
            "faculty_email": "shaila@besant.edu"
        }
    )
    college_id = col_res.json()["data"]["college_id"]

    res = client.post(
        "/api/events/register",
        json={
            "college_id": college_id,
            "event_name": "Code Wars",
            "department": "IT",
            "participants": [
                {"student_name": "Valid Student", "puc_year": "3rd PUC"},  # Invalid
                {"student_name": "Valid Student 2", "puc_year": "1st PUC"}
            ]
        }
    )
    assert res.status_code == 422
    assert res.json()["status"] == "error"

"""
MAHAVEERA FEST 2K26 Registration Web Application Backend.
Sri Mahaveera College, Moodbidri (Held on 30 October 2026).
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from datetime import datetime

from app.core.config import settings, IST
from app.core.constants import GENERAL_RULE_REMINDERS
from app.core.exceptions import DomainException
from app.database.session import init_db
from app.api.routers import college, events, admin

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema tables exist on application startup."""
    init_db()
    yield


# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production backend system for MAHAVEERA FEST 2K26 intercollegiate competition for PU students. "
        "Organized jointly by IQAC, Science (NOVEXA), Commerce (COMQUEST), IT (UTKARSH), and Humanities (MAHAVITH) Associations "
        "at Sri Mahaveera College, Moodbidri on 30 October 2026."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enable CORS for web frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom Exception Handler for Domain Business Rules
@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error": exc.detail,
            "rule_reminders": GENERAL_RULE_REMINDERS
        }
    )


# Custom Exception Handler for Request Validation Errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field_loc = " -> ".join([str(x) for x in err.get("loc", [])])
        errors.append({
            "field": field_loc,
            "message": err.get("msg"),
            "type": err.get("type")
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "status": "error",
            "error": {
                "error_code": "REQUEST_VALIDATION_ERROR",
                "message": "The submitted payload failed validation constraints.",
                "details": errors
            },
            "rule_reminders": GENERAL_RULE_REMINDERS
        }
    )


# Include API Routers
app.include_router(college.router, prefix=settings.API_V1_STR)
app.include_router(events.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)


import os
from fastapi.responses import JSONResponse, FileResponse


@app.get("/", tags=["Pages"])
def home_page():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"title": "MAHAVEERA FEST 2K26 Registration API", "status": "online"}


from typing import Optional
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi import Request


RESTRICTED_AREA_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restricted Area | MAHAVEERA FEST 2K26</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #0a0f1e; color: #f8fafc; font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">
    <div class="max-w-md w-full bg-red-950/20 border border-red-500/30 rounded-2xl p-8 text-center backdrop-blur-md shadow-2xl">
        <div class="w-16 h-16 rounded-full bg-red-900/40 border border-red-500/50 flex items-center justify-center text-red-400 text-2xl mx-auto mb-6">
            <i class="fa-solid fa-shield-halved"></i>
        </div>
        <h1 class="text-3xl font-bold font-['Cinzel'] text-white mb-2 tracking-wide">Restricted Area</h1>
        <p class="text-red-300 text-sm mb-6">
            Access to the Administrator Dashboard requires an authorized secret key parameter.
        </p>
        <div class="p-3 bg-black/40 border border-white/10 rounded-lg text-xs text-gray-400 mb-6 font-mono">
            Error: Invalid or missing ADMIN KEY
        </div>

        <a href="/" class="inline-block px-6 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white text-xs font-semibold uppercase tracking-wider transition">
            <i class="fa-solid fa-arrow-left mr-1"></i> Return to Fest Home
        </a>
    </div>
</body>
</html>
"""


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@app.get("/admin/dashboard", tags=["Pages"])
def admin_dashboard_page(request: Request):
    secret_key = request.query_params.get("ADMIN_SECRET_KEY")
    if not secret_key or secret_key != settings.ADMIN_SECRET_KEY:
        return HTMLResponse(content=RESTRICTED_AREA_HTML, status_code=403)

    tmpl_path = os.path.join(BASE_DIR, "admin_dashboard.html")
    if os.path.exists(tmpl_path):
        return FileResponse(tmpl_path)
    return {"message": "Admin dashboard page template not found."}



@app.get("/register", tags=["Pages"])
@app.get("/register.html", tags=["Pages"])
def register_page():
    tmpl_path = os.path.join(BASE_DIR, "register.html")
    if os.path.exists(tmpl_path):
        return FileResponse(tmpl_path)
    return {"message": "Registration page not found."}


@app.get("/check-status", tags=["Pages"])
@app.get("/check-status.html", tags=["Pages"])
def check_status_page():
    tmpl_path = os.path.join(BASE_DIR, "check_status.html")
    if os.path.exists(tmpl_path):
        return FileResponse(tmpl_path)
    return {"message": "Check status page not found."}


@app.get("/science", tags=["Pages"])
@app.get("/science.html", tags=["Pages"])
def science_page():
    tmpl_path = os.path.join(BASE_DIR, "science.html")
    if os.path.exists(tmpl_path):
        return FileResponse(tmpl_path)
    return {"message": "Science department page not found."}


@app.get("/commerce", tags=["Pages"])
@app.get("/commerce.html", tags=["Pages"])
def commerce_page():
    tmpl_path = os.path.join(BASE_DIR, "commerce.html")
    if os.path.exists(tmpl_path):
        return FileResponse(tmpl_path)
    return {"message": "Commerce department page not found."}


@app.get("/it", tags=["Pages"])
@app.get("/it.html", tags=["Pages"])
def it_page():
    tmpl_path = os.path.join(BASE_DIR, "it.html")
    if os.path.exists(tmpl_path):
        return FileResponse(tmpl_path)
    return {"message": "IT department page not found."}


@app.get("/humanities", tags=["Pages"])
@app.get("/humanities.html", tags=["Pages"])
def humanities_page():
    tmpl_path = os.path.join(BASE_DIR, "humanities.html")
    if os.path.exists(tmpl_path):
        return FileResponse(tmpl_path)
    return {"message": "Humanities department page not found."}


@app.get("/about", tags=["Pages"])
@app.get("/about.html", tags=["Pages"])
def about_page():
    tmpl_path = os.path.join(BASE_DIR, "about.html")
    if os.path.exists(tmpl_path):
        return FileResponse(tmpl_path)
    return {"message": "About page not found."}



@app.get("/api/health", tags=["Root"])
def health_check():
    now_ist = datetime.now(IST)
    is_registration_open = now_ist <= settings.deadline_datetime
    return {
        "status": "healthy",
        "server_time_ist": now_ist.strftime("%d/%m/%Y %H:%M:%S %Z"),
        "registration_deadline_ist": settings.deadline_datetime.strftime("%d/%m/%Y %H:%M:%S %Z"),
        "is_registration_open": is_registration_open,
        "max_unique_students_per_college": 25
    }

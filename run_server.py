"""
Entrypoint script to run the MAHAVEERA FEST 2K26 backend application.
Usage:
    python run_server.py
"""
import uvicorn

if __name__ == "__main__":
    print("================================================================")
    print("  MAHAVEERA FEST 2K26 - REGISTRATION BACKEND SERVER")
    print("  Sri Mahaveera College, Moodbidri (Event: 30 October 2026)")
    print("  Registration Deadline: 24 October 2026 23:59:59 IST")
    print("================================================================")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

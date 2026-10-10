"""
FastAPI route dependencies: Database session, Authentication, and Token extraction.
"""
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.security import verify_access_token


def get_current_college_id(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[str]:
    """
    Extracts and verifies the college_id from Bearer token if provided in header.
    Returns None if no authorization header is provided.
    """
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'."
        )

    token = parts[1]
    payload = verify_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication session token."
        )

    return payload["sub"]

import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from database import init_db
from schemas import (
    DEFAULT_CATEGORIES,
    DashboardStats,
    LoginRequest,
    LoginResponse,
    RequestCreate,
    RequestResponse,
    RequestUpdateStatus,
    SignupRequest,
    UserResponse,
)
import crud

STATIC_DIR = os.path.join(BASE_DIR, "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema & seed default accounts
    init_db()
    yield


app = FastAPI(
    title="E-Waste Management System",
    description="Backend API and web interface for managing electronic waste collection and recycling",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory if it exists
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _get_user_from_header(authorization: Optional[str]) -> Optional[dict]:
    """Helper to extract and validate session token from Authorization header."""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").replace("bearer ", "").strip()
    return crud.get_user_by_session_token(token)


# -------------------------------------------------------------
# Core Root & Compatibility Endpoints
# -------------------------------------------------------------
@app.get("/")
def home():
    """Preserved endpoint expected by existing test."""
    return {"message": "EWaste API is running!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/categories")
def get_categories():
    return {"categories": DEFAULT_CATEGORIES}


@app.get("/api/items")
def get_items():
    """Preserved mock items endpoint for backward compatibility."""
    return {
        "items": [
            {
                "id": 1,
                "name": "Old Mobile Phone",
                "category": "Mobile Phones",
                "condition": "Used",
            },
            {
                "id": 2,
                "name": "Old Laptop",
                "category": "Laptops",
                "condition": "Used",
            },
        ]
    }


# -------------------------------------------------------------
# Authentication Endpoints
# -------------------------------------------------------------
@app.post("/api/auth/signup", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
@app.post("/api/auth/signup/", response_model=LoginResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def signup(payload: SignupRequest):
    """Registers a new resident user account and creates an active session."""
    user = crud.create_user(
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        role="user",
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in instead.",
        )
    token = crud.create_session(user["id"], user["email"], user["role"])
    return {"token": token, "user": user}


@app.post("/api/auth/login", response_model=LoginResponse)
@app.post("/api/auth/login/", response_model=LoginResponse, include_in_schema=False)
def login(payload: LoginRequest):
    """Authenticates admin or resident user credentials and returns session token."""
    user = crud.authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials.",
        )
    token = crud.create_session(user["id"], user["email"], user["role"])
    return {"token": token, "user": user}


@app.post("/api/auth/logout")
@app.post("/api/auth/logout/", include_in_schema=False)
def logout(authorization: Optional[str] = Header(None)):
    """Logs out the user and invalidates the session token."""
    if authorization:
        token = authorization.replace("Bearer ", "").replace("bearer ", "").strip()
        crud.delete_session(token)
    return {"message": "Logged out successfully"}


@app.get("/api/auth/me", response_model=UserResponse)
@app.get("/api/auth/me/", response_model=UserResponse, include_in_schema=False)
def get_current_user_profile(authorization: Optional[str] = Header(None)):
    """Returns the authenticated user's profile and assigned role."""
    user = _get_user_from_header(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing or expired",
        )
    return user


# -------------------------------------------------------------
# Frontend Application Delivery Route
# -------------------------------------------------------------
@app.get("/app", response_class=HTMLResponse)
@app.get("/app/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse, include_in_schema=False)
def serve_frontend_app():
    """Serves the interactive single-page e-waste management portal."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(
        content="<h2>Frontend file is currently loading... Please refresh in a moment.</h2>"
    )


# -------------------------------------------------------------
# E-Waste Collection Request Endpoints
# -------------------------------------------------------------
@app.get("/api/dashboard/stats", response_model=DashboardStats)
def get_dashboard_metrics(authorization: Optional[str] = Header(None)):
    """Returns calculated counts from SQLite (scoped to user if logged in as user, or system-wide for admin)."""
    current_user = _get_user_from_header(authorization)
    user_email = current_user["email"] if current_user and current_user.get("role") == "user" else None
    stats = crud.get_dashboard_stats(user_email=user_email)
    return stats


@app.get("/api/requests")
def list_requests(
    status: Optional[str] = Query(None, description="Filter by status: Pending, Scheduled, Collected, Processed"),
    category: Optional[str] = Query(None, description="Filter by item category"),
    search: Optional[str] = Query(None, description="Search by name, phone, tracking ID, or description"),
    authorization: Optional[str] = Header(None),
):
    """Fetches collection requests (scoped to user if logged in as user, or all requests for admin)."""
    current_user = _get_user_from_header(authorization)
    user_email = current_user["email"] if current_user and current_user.get("role") == "user" else None
    requests = crud.get_requests(
        status=status,
        category=category,
        search=search,
        user_email=user_email,
    )
    return {"requests": requests, "count": len(requests)}


@app.post("/api/requests", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
def submit_request(data: RequestCreate):
    """Submits a new e-waste pickup request with input validation."""
    new_request = crud.create_request(data)
    return new_request


@app.get("/api/requests/{request_id}", response_model=RequestResponse)
def get_single_request(request_id: int):
    """Fetches full details of a specific collection request."""
    req = crud.get_request_by_id(request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request #{request_id} not found",
        )
    return req


@app.patch("/api/requests/{request_id}/status", response_model=RequestResponse)
def update_status(
    request_id: int,
    payload: RequestUpdateStatus,
    authorization: Optional[str] = Header(None),
):
    """Updates the processing status of a collection request (requires admin role)."""
    current_user = _get_user_from_header(authorization)
    if current_user and current_user.get("role") == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges are required to update collection request status.",
        )

    updated = crud.update_request_status(request_id, payload.status)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request #{request_id} not found",
        )
    return updated


@app.delete("/api/requests/{request_id}")
def remove_request(
    request_id: int,
    authorization: Optional[str] = Header(None),
):
    """Deletes an e-waste collection request (requires admin role)."""
    current_user = _get_user_from_header(authorization)
    if current_user and current_user.get("role") == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges are required to delete collection requests.",
        )

    success = crud.delete_request(request_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request #{request_id} not found",
        )
    return {"message": "Request deleted successfully", "id": request_id}


# -------------------------------------------------------------
# Optional Demo Data Management Endpoints
# -------------------------------------------------------------
@app.post("/api/demo/seed")
def seed_demo_records(authorization: Optional[str] = Header(None)):
    """Generates realistic sample collection requests for demonstration."""
    current_user = _get_user_from_header(authorization)
    if current_user and current_user.get("role") == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges are required to seed demo data.",
        )

    count = crud.seed_demo_data()
    return {"message": f"Successfully created {count} demo collection requests.", "count": count}


@app.post("/api/demo/clear")
def clear_demo_records(authorization: Optional[str] = Header(None)):
    """Clears all collection requests to reset the demonstration database."""
    current_user = _get_user_from_header(authorization)
    if current_user and current_user.get("role") == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges are required to clear demo data.",
        )

    deleted_count = crud.clear_all_requests()
    return {"message": f"Successfully cleared {deleted_count} records.", "count": deleted_count}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

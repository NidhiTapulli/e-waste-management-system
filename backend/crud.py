import random
import secrets
import string
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from database import get_db, verify_password, hash_password
from schemas import RequestCreate


def _generate_tracking_id() -> str:
    """Generates a human-friendly unique tracking identifier like EW-2026-X8K2"""
    year = datetime.now().year
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"EW-{year}-{suffix}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------------------------------
# Authentication & Session Operations
# -------------------------------------------------------------
def create_user(full_name: str, email: str, password: str, role: str = "user") -> Optional[Dict[str, Any]]:
    """Creates a new user. Role is strictly forced to 'user' for public registrations."""
    email_clean = email.strip().lower()
    now = _now_iso()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email_clean,))
        if cursor.fetchone():
            return None  # Email already registered

        hashed = hash_password(password)
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role, created_at)
            VALUES (?, ?, ?, 'user', ?)
            """,
            (full_name.strip(), email_clean, hashed, now),
        )
        new_id = cursor.lastrowid
        return {
            "id": new_id,
            "full_name": full_name.strip(),
            "email": email_clean,
            "role": "user",
        }


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Checks user credentials and returns user profile if valid."""
    email_clean = email.strip().lower()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email_clean,))
        user = cursor.fetchone()
        if not user:
            return None
        if not verify_password(user["password_hash"], password):
            return None
        return {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        }


def create_session(user_id: int, email: str, role: str) -> str:
    """Generates a secure token and creates a session record."""
    token = secrets.token_hex(24)
    now = _now_iso()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions (token, user_id, email, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (token, user_id, email.lower(), role, now),
        )
    return token


def get_user_by_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Retrieves authenticated user from session token."""
    if not token:
        return None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.id, u.email, u.full_name, u.role
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
            """,
            (token.strip(),),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_session(token: str) -> bool:
    """Removes a session token upon logout."""
    if not token:
        return False
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token.strip(),))
        return cursor.rowcount > 0


# -------------------------------------------------------------
# Request Operations (with role-based user_email scoping)
# -------------------------------------------------------------
def create_request(data: RequestCreate) -> Dict[str, Any]:
    tracking_id = _generate_tracking_id()
    now = _now_iso()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO collection_requests (
                tracking_id, full_name, email, phone, address, city, pincode,
                category, item_description, quantity, condition, preferred_date,
                special_notes, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
            """,
            (
                tracking_id,
                data.full_name.strip(),
                data.email.strip().lower(),
                data.phone.strip(),
                data.address.strip(),
                data.city.strip(),
                data.pincode.strip(),
                data.category.strip(),
                data.item_description.strip(),
                data.quantity,
                data.condition.strip(),
                data.preferred_date.strip(),
                (data.special_notes or "").strip(),
                now,
                now,
            ),
        )
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM collection_requests WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        return dict(row)


def get_requests(
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    user_email: Optional[str] = None,
    limit: int = 300,
) -> List[Dict[str, Any]]:
    query = "SELECT * FROM collection_requests WHERE 1=1"
    params: List[Any] = []

    # If regular user is authenticated, scope strictly to their email
    if user_email:
        query += " AND LOWER(email) = ?"
        params.append(user_email.strip().lower())

    if status and status.lower() != "all":
        query += " AND status = ?"
        params.append(status)

    if category and category.lower() != "all":
        query += " AND category = ?"
        params.append(category)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query += """ AND (
            tracking_id LIKE ? OR
            full_name LIKE ? OR
            phone LIKE ? OR
            item_description LIKE ? OR
            city LIKE ? OR
            address LIKE ?
        )"""
        params.extend([term, term, term, term, term, term])

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_request_by_id(request_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM collection_requests WHERE id = ?", (request_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_request_status(request_id: int, new_status: str) -> Optional[Dict[str, Any]]:
    now = _now_iso()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE collection_requests
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_status, now, request_id),
        )
        if cursor.rowcount == 0:
            return None
        cursor.execute("SELECT * FROM collection_requests WHERE id = ?", (request_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_request(request_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM collection_requests WHERE id = ?", (request_id,))
        return cursor.rowcount > 0


def get_dashboard_stats(user_email: Optional[str] = None) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        where_clause = ""
        params: List[Any] = []

        if user_email:
            where_clause = " WHERE LOWER(email) = ?"
            params.append(user_email.strip().lower())

        # Total counts
        cursor.execute(f"SELECT COUNT(*) AS total FROM collection_requests{where_clause}", params)
        total = cursor.fetchone()["total"]

        # Status counts
        status_counts = {"Pending": 0, "Scheduled": 0, "Collected": 0, "Processed": 0}
        cursor.execute(
            f"SELECT status, COUNT(*) AS count FROM collection_requests{where_clause} GROUP BY status",
            params,
        )
        for row in cursor.fetchall():
            if row["status"] in status_counts:
                status_counts[row["status"]] = row["count"]

        # Category counts
        cursor.execute(
            f"SELECT category, COUNT(*) AS count FROM collection_requests{where_clause} GROUP BY category",
            params,
        )
        category_counts = {row["category"]: row["count"] for row in cursor.fetchall()}

        # Recent 5 requests
        cursor.execute(
            f"SELECT * FROM collection_requests{where_clause} ORDER BY id DESC LIMIT 5",
            params,
        )
        recent = [dict(r) for r in cursor.fetchall()]

        return {
            "total_requests": total,
            "pending": status_counts["Pending"],
            "scheduled": status_counts["Scheduled"],
            "collected": status_counts["Collected"],
            "processed": status_counts["Processed"],
            "category_counts": category_counts,
            "recent_activity": recent,
        }


def seed_demo_data() -> int:
    """Inserts sample college demonstration requests if the table is empty or upon user trigger."""
    sample_items = [
        {
            "full_name": "Demo Resident User",
            "email": "user@ewaste.com",
            "phone": "+91 98765 43210",
            "address": "Flat 402, Green Meadows Apartment, MG Road",
            "city": "Bengaluru",
            "pincode": "560001",
            "category": "Laptops",
            "item_description": "Dell Inspiron 15 (2018 model), broken hinge and dead battery",
            "quantity": 1,
            "condition": "Semi-functional",
            "preferred_date": "2026-10-15",
            "special_notes": "Call 15 minutes before arrival",
            "status": "Pending",
        },
        {
            "full_name": "Demo Resident User",
            "email": "user@ewaste.com",
            "phone": "+91 98765 43210",
            "address": "Flat 402, Green Meadows Apartment, MG Road",
            "city": "Bengaluru",
            "pincode": "560001",
            "category": "Mobile Phones",
            "item_description": "Samsung Galaxy S9 with non-responsive touch screen",
            "quantity": 1,
            "condition": "Non-functional / Scrap",
            "preferred_date": "2026-10-17",
            "special_notes": "Charging cable included",
            "status": "Scheduled",
        },
        {
            "full_name": "Priya Patel",
            "email": "priya.p@example.com",
            "phone": "+91 98234 56789",
            "address": "12 Lotus Residency, Satellite",
            "city": "Ahmedabad",
            "pincode": "380015",
            "category": "Mobile Phones",
            "item_description": "2 x Samsung Galaxy J7 & 1 x iPhone 7 with cracked screens",
            "quantity": 3,
            "condition": "Non-functional / Scrap",
            "preferred_date": "2026-10-14",
            "special_notes": "Chargers and original boxes included",
            "status": "Scheduled",
        },
        {
            "full_name": "Rohan Deshmukh",
            "email": "rohan.deshmukh@example.com",
            "phone": "+91 91234 56780",
            "address": "Plot 88, Shivaji Park, Dadar West",
            "city": "Mumbai",
            "pincode": "400028",
            "category": "Batteries",
            "item_description": "Assorted rechargeable laptop & UPS lead-acid batteries",
            "quantity": 4,
            "condition": "Non-functional / Scrap",
            "preferred_date": "2026-10-12",
            "special_notes": "Stored in sealed plastic bin for safe handling",
            "status": "Collected",
        },
        {
            "full_name": "Sneha Iyer",
            "email": "sneha.iyer@example.com",
            "phone": "+91 94455 66778",
            "address": "Villa 9, Palm Grove, ECR",
            "city": "Chennai",
            "pincode": "600041",
            "category": "Televisions",
            "item_description": "32-inch Sony Bravia LCD TV with display line fault",
            "quantity": 1,
            "condition": "Semi-functional",
            "preferred_date": "2026-10-10",
            "special_notes": "Remote control also available",
            "status": "Processed",
        },
        {
            "full_name": "Vikram Malhotra",
            "email": "vikram.m@example.com",
            "phone": "+91 99887 76655",
            "address": "C-14, Sector 62",
            "city": "Noida",
            "pincode": "201301",
            "category": "Computers",
            "item_description": "Old desktop CPU tower, Intel Core 2 Duo, 500GB HDD",
            "quantity": 1,
            "condition": "Working",
            "preferred_date": "2026-10-18",
            "special_notes": "Personal data drives have been formatted",
            "status": "Pending",
        },
    ]

    now = _now_iso()
    inserted = 0
    with get_db() as conn:
        cursor = conn.cursor()
        for item in sample_items:
            tracking_id = _generate_tracking_id()
            cursor.execute(
                """
                INSERT INTO collection_requests (
                    tracking_id, full_name, email, phone, address, city, pincode,
                    category, item_description, quantity, condition, preferred_date,
                    special_notes, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tracking_id,
                    item["full_name"],
                    item["email"],
                    item["phone"],
                    item["address"],
                    item["city"],
                    item["pincode"],
                    item["category"],
                    item["item_description"],
                    item["quantity"],
                    item["condition"],
                    item["preferred_date"],
                    item["special_notes"],
                    item["status"],
                    now,
                    now,
                ),
            )
            inserted += 1
    return inserted


def clear_all_requests() -> int:
    """Removes all requests (for clean demonstration reset)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM collection_requests")
        return cursor.rowcount

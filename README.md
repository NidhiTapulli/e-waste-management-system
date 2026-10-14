# ♻️ E-Waste Management System

A full-stack, responsive web application for managing electronic waste collection, tracking requests, and monitoring recycling metrics with **Gated Authentication (Login First Screen)** and **Role-Based Access Control (Resident User & Admin views)**. Built with **FastAPI**, **SQLite**, and modern **Vanilla HTML/CSS/JavaScript**.

---

## 🌟 Key Features

1. **Login & Signup as First Screen**:
   - When anyone opens `/app`, the **Login/Signup page is shown first**.
   - Unauthenticated visitors cannot access or view protected content (dashboard, requests table, pickup form).
   - Eco-friendly green styling with floating animated recycling badges (`♻️`, `🌿`, `💻`, `🔋`).
   - Clean credentials form: Email, Password, **Show/Hide password toggle (👁️ / 🙈)**, and Sign In action.
   - **User Registration (Sign Up)**: New resident users can register with their Name, Email, and Password (min 6 characters). Role is strictly enforced as `"user"`.
   - **1-Click College Demo Accounts Assistant**: Auto-fills Admin or Resident User credentials for instant evaluation.

2. **Role-Based Access Control (RBAC)**:
   - **Resident User Portal**:
     - **Personal Dashboard**: Shows counts for the user's own collection requests.
     - **Schedule Pickup**: Automatically pre-fills the logged-in user's name and email.
     - **My Requests Page**: Shows only the requests submitted by that user with tracking codes and live statuses (`Pending`, `Scheduled`, `Collected`, `Processed`).
     - **Security**: Regular users cannot change request statuses, delete requests, or seed demo data (restricted both in the frontend UI and strictly enforced on the backend with `403 Forbidden`).
   - **System Administrator Portal**:
     - **Admin Command Dashboard**: Displays real-time system-wide statistics across all users.
     - **Manage All Requests**: Search, filter by status and category, view full customer and pickup details, and change request statuses inline (`Pending` ➔ `Scheduled` ➔ `Collected` ➔ `Processed`).
     - **Delete Requests**: Confirmation modal before deleting any record.
     - **Demo Data Tools**: One-click demo seeding and database reset.

3. **Security & Simplicity**:
   - Zero external auth dependencies: Uses Python's standard library `hashlib.pbkdf2_hmac` with cryptographic random salts for password hashing.
   - Session tokens stored in SQLite with Bearer token authentication.
   - Predefined accounts configurable via environment variables (`ADMIN_EMAIL`, `ADMIN_PASSWORD`).
   - Parameterized SQLite queries (`?`) prevent SQL injection attacks.

---

## 🔑 Predefined Accounts (For College Demonstration)

| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@ewaste.com` | `admin123` | Full access to all requests, status updates, deletion, system stats, and demo data tools. |
| **Resident User (Demo)** | `user@ewaste.com` | `user123` | Can submit requests, view personal dashboard, and track own requests and statuses. |

*(Public registration creates normal resident accounts. The administrator account is pre-seeded or managed via environment variables and cannot be created via public signup).*

---

## 🚀 Quick Start Guide (Windows PowerShell)

Follow these exact commands in Windows PowerShell:

### 1. Open Windows PowerShell and navigate to the project directory
```powershell
cd C:\Users\Niddhi\Desktop\EWaste\EWaste
```

### 2. Activate the Virtual Environment
```powershell
.\backend\venv\Scripts\Activate.ps1
```
*(If PowerShell shows an execution policy error, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` once).*

### 3. Run the Automated Tests (Verifies All Features, Roles & Signup)
```powershell
cd backend
python -m pytest tests -v
cd ..
```
*All 12 automated test cases will run and pass, verifying the root endpoint, health check, CRUD operations, input validation, role separation, permissions enforcement, signup flow, and session lifecycle.*

### 4. Start the Application Server
```powershell
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🌐 URLs to Open in Your Browser

| Page / Feature | URL | Description |
| :--- | :--- | :--- |
| **Web Application Portal** | **[http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)** | Main frontend portal (opens the Login/Signup screen first). |
| **Original API Root** | [http://127.0.0.1:8000/](http://127.0.0.1:8000/) | Returns `{"message": "EWaste API is running!"}` (verified by existing tests). |
| **Interactive API Documentation** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Swagger UI for interactive API exploration. |
| **System Health Check** | [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) | Returns `{"status": "healthy"}`. |

---

## 🎓 College Presentation Demo Script (3 Minutes)

1. Open **[http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)**.
2. **Show Login As First Screen**:
   - Point out that `/app` immediately opens the **Login / Sign Up** screen.
   - Protected features (dashboard, requests table) are hidden until authentication.
3. **Show User Registration & Resident Portal**:
   - Click the **"🌱 Create Account"** tab on the card.
   - Enter a name (e.g., `Ankit Rao`), email (`ankit@example.com`), password (`securePass123`), and test the show/hide password toggle (`👁️` / `🙈`).
   - Click **Register Resident Account**.
   - Notice the system immediately logs in and opens the **Resident Recycling Portal**.
   - Navigate to **Schedule Pickup** to show that their name and email are pre-filled. Submit an item (e.g. Broken Laptop).
   - Go to **My Requests** to view the newly submitted request with its tracking code and `Pending` status. Point out that admin status changers and delete buttons are not visible.
4. **Show Admin Portal**:
   - Click **`🚪 Logout`** in the top navbar (redirects back to the Login screen).
   - Click the 1-click **"🛡️ Admin Account (admin@ewaste.com)"** button and sign in.
   - Point out the **Administrator Command Dashboard** displaying system-wide counts.
   - Go to **Manage Requests**:
     - See all requests from all users.
     - Search by customer name, phone, or tracking ID.
     - Change request status from `Pending` to `Scheduled` or `Collected` directly from the inline dropdown to demonstrate live database updates.
     - Click **`👁️ View`** to see full details.
     - Click **`🗑️`** to demonstrate delete with safety confirmation.
5. **Show Automated Tests**: Run `python -m pytest tests -v` in PowerShell to show 12 passing tests (100% pass rate).

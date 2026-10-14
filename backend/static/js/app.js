/**
 * E-Waste Management System - Client Application Logic
 * Supports role-based views (Guest, Resident User, Admin) and interactive UI.
 * Unauthenticated users are strictly gated at the Login/Signup screen.
 */

let cachedRequests = [];
let categoriesList = [];
let searchDebounceTimer = null;
let currentDeleteId = null;
let currentUser = null;
let authToken = localStorage.getItem("ewaste_auth_token") || null;
let currentAuthMode = "signin";

const CATEGORY_ICONS = {
  "Mobile Phones": "📱",
  "Laptops": "💻",
  "Computers": "🖥️",
  "Televisions": "📺",
  "Batteries": "🔋",
  "Home Appliances": "🔌",
  "Other Electronics": "⚙️",
};

function getAuthHeaders() {
  const headers = {};
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  return headers;
}

function formatApiError(data, fallback = "An unexpected error occurred.") {
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        let msg = item.msg || JSON.stringify(item);
        if (typeof msg === "string" && msg.startsWith("Value error, ")) {
          msg = msg.replace("Value error, ", "");
        }
        return msg;
      })
      .join(". ");
  }
  if (data.message) return data.message;
  return fallback;
}

// -------------------------------------------------------------
// Authentication & Session Management
// -------------------------------------------------------------
async function checkAuthStatus() {
  if (!authToken) {
    currentUser = null;
    updateAuthUI();
    switchTab("login");
    return;
  }
  try {
    const res = await fetch("/api/auth/me", { headers: getAuthHeaders() });
    if (res.ok) {
      currentUser = await res.json();
      updateAuthUI();
      // If returning user has a valid tab hash, preserve it; otherwise go to dashboard
      const rawHash = (window.location.hash || "").replace("#", "").trim();
      const validTabs = ["dashboard", "pickup", "requests", "home"];
      if (validTabs.includes(rawHash)) {
        switchTab(rawHash);
      } else {
        switchTab("dashboard");
      }
    } else {
      // Invalid/expired token
      authToken = null;
      currentUser = null;
      localStorage.removeItem("ewaste_auth_token");
      updateAuthUI();
      switchTab("login");
    }
  } catch (err) {
    console.error("Auth check failed:", err);
    updateAuthUI();
    switchTab("login");
  }
}

function updateAuthUI() {
  const navLinksList = document.getElementById("navLinksList");
  const navPickupBtn = document.getElementById("navPickupBtn");
  const navLoginBtn = document.getElementById("navLoginBtn");
  const heroLoginBtn = document.getElementById("heroLoginBtn");
  const navUserBadge = document.getElementById("navUserBadge");
  const navRoleIcon = document.getElementById("navRoleIcon");
  const navUserEmail = document.getElementById("navUserEmail");
  const navRoleTag = document.getElementById("navRoleTag");
  const demoDataBtn = document.getElementById("demoDataBtn");
  const emptyStateDemoBtn = document.getElementById("emptyStateDemoBtn");
  const navDashboardLink = document.getElementById("navDashboardLink");
  const navRequestsLink = document.getElementById("navRequestsLink");
  const dashboardTitle = document.getElementById("dashboardTitle");
  const dashboardSubtitle = document.getElementById("dashboardSubtitle");
  const dashboardRoleBadge = document.getElementById("dashboardRoleBadge");
  const requestsTitle = document.getElementById("requestsTitle");
  const requestsSubtitle = document.getElementById("requestsSubtitle");
  const labelTotal = document.getElementById("labelTotal");

  if (!currentUser) {
    // Unauthenticated (Guest) - Strictly gated at Login
    if (navLinksList) navLinksList.style.display = "none";
    if (navPickupBtn) navPickupBtn.style.display = "none";
    if (navLoginBtn) navLoginBtn.style.display = "inline-flex";
    if (heroLoginBtn) heroLoginBtn.style.display = "inline-flex";
    if (navUserBadge) navUserBadge.style.display = "none";
    if (demoDataBtn) demoDataBtn.style.display = "none";
    if (emptyStateDemoBtn) emptyStateDemoBtn.style.display = "none";
  } else if (currentUser.role === "user") {
    // Resident User View
    if (navLinksList) navLinksList.style.display = "flex";
    if (navPickupBtn) navPickupBtn.style.display = "inline-flex";
    if (navLoginBtn) navLoginBtn.style.display = "none";
    if (heroLoginBtn) heroLoginBtn.style.display = "none";
    if (navUserBadge) navUserBadge.style.display = "inline-flex";
    if (navRoleIcon) navRoleIcon.textContent = "👤";
    if (navUserEmail) navUserEmail.textContent = currentUser.full_name || currentUser.email;
    if (navRoleTag) {
      navRoleTag.textContent = "Resident";
      navRoleTag.className = "user-role-badge role-user";
    }
    if (demoDataBtn) demoDataBtn.style.display = "none";
    if (emptyStateDemoBtn) emptyStateDemoBtn.style.display = "none";

    if (navDashboardLink) navDashboardLink.textContent = "Resident Dashboard";
    if (navRequestsLink) navRequestsLink.textContent = "My Requests";
    if (dashboardRoleBadge) dashboardRoleBadge.textContent = "Resident Portal";
    if (dashboardTitle) dashboardTitle.textContent = "Resident Recycling Portal";
    if (dashboardSubtitle) dashboardSubtitle.textContent = "Schedule pickups, view your tracking codes, and track collection statuses.";
    if (requestsTitle) requestsTitle.textContent = "My Pickup Requests";
    if (requestsSubtitle) requestsSubtitle.textContent = "Track the live status of your electronic waste pickups.";
    if (labelTotal) labelTotal.textContent = "My Requests";

    // Auto-fill pickup form with user details
    const nameField = document.getElementById("full_name");
    const emailField = document.getElementById("email");
    if (nameField) nameField.value = currentUser.full_name;
    if (emailField) emailField.value = currentUser.email;
  } else if (currentUser.role === "admin") {
    // Admin View
    if (navLinksList) navLinksList.style.display = "flex";
    if (navPickupBtn) navPickupBtn.style.display = "inline-flex";
    if (navLoginBtn) navLoginBtn.style.display = "none";
    if (heroLoginBtn) heroLoginBtn.style.display = "none";
    if (navUserBadge) navUserBadge.style.display = "inline-flex";
    if (navRoleIcon) navRoleIcon.textContent = "🛡️";
    if (navUserEmail) navUserEmail.textContent = currentUser.email;
    if (navRoleTag) {
      navRoleTag.textContent = "Admin";
      navRoleTag.className = "user-role-badge role-admin";
    }
    if (demoDataBtn) demoDataBtn.style.display = "inline-flex";
    if (emptyStateDemoBtn) emptyStateDemoBtn.style.display = "inline-flex";

    if (navDashboardLink) navDashboardLink.textContent = "Admin Dashboard";
    if (navRequestsLink) navRequestsLink.textContent = "Manage Requests";
    if (dashboardRoleBadge) dashboardRoleBadge.textContent = "Admin Command";
    if (dashboardTitle) dashboardTitle.textContent = "Administrator Collection Dashboard";
    if (dashboardSubtitle) dashboardSubtitle.textContent = "Real-time system-wide statistics across all collection requests.";
    if (requestsTitle) requestsTitle.textContent = "All Collection Requests (Admin Management)";
    if (requestsSubtitle) requestsSubtitle.textContent = "Manage, filter, search, update statuses, or delete requests with SQLite persistence.";
    if (labelTotal) labelTotal.textContent = "Total System Requests";
  }
}

// -------------------------------------------------------------
// Auth Mode Switching (Sign In vs Sign Up)
// -------------------------------------------------------------
function switchAuthMode(mode) {
  currentAuthMode = mode;
  const tabSignIn = document.getElementById("tabSignInBtn");
  const tabSignUp = document.getElementById("tabSignUpBtn");
  const loginForm = document.getElementById("loginForm");
  const signupForm = document.getElementById("signupForm");
  const authTitle = document.getElementById("authTitle");
  const authSubtitle = document.getElementById("authSubtitle");
  const authIcon = document.getElementById("authHeaderIcon");
  const alertBox = document.getElementById("loginAlertBox");

  if (alertBox) alertBox.style.display = "none";

  if (mode === "signin") {
    if (tabSignIn) tabSignIn.classList.add("active");
    if (tabSignUp) tabSignUp.classList.remove("active");
    if (loginForm) loginForm.style.display = "block";
    if (signupForm) signupForm.style.display = "none";
    if (authTitle) authTitle.textContent = "Sign In to EcoCycle";
    if (authSubtitle) authSubtitle.textContent = "Access your recycling dashboard or manage collections as administrator.";
    if (authIcon) authIcon.textContent = "♻️";
  } else {
    if (tabSignUp) tabSignUp.classList.add("active");
    if (tabSignIn) tabSignIn.classList.remove("active");
    if (loginForm) loginForm.style.display = "none";
    if (signupForm) signupForm.style.display = "block";
    if (authTitle) authTitle.textContent = "Create Resident Account";
    if (authSubtitle) authSubtitle.textContent = "Join the circular economy. Schedule pickups and track your recycling.";
    if (authIcon) authIcon.textContent = "🌱";
  }
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const alertBox = document.getElementById("loginAlertBox");
  if (alertBox) {
    alertBox.style.display = "none";
    alertBox.textContent = "";
  }

  const email = document.getElementById("loginEmail").value.trim().toLowerCase();
  const password = document.getElementById("loginPassword").value;
  const submitBtn = document.getElementById("loginSubmitBtn");
  const originalText = submitBtn.innerHTML;

  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span>⏳ Signing in...</span>`;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    let data;
    try {
      data = await res.json();
    } catch {
      data = null;
    }

    if (!res.ok) {
      const errorMsg = formatApiError(data, "Invalid email or password. Please verify your credentials.");
      throw new Error(errorMsg);
    }

    authToken = data.token;
    currentUser = data.user;
    localStorage.setItem("ewaste_auth_token", authToken);

    showToast(`Welcome back, ${currentUser.full_name}!`, "success");
    updateAuthUI();
    loadDashboardStats();
    loadRequests();
    switchTab("dashboard");
  } catch (err) {
    if (alertBox) {
      alertBox.textContent = `⚠️ ${err.message}`;
      alertBox.style.display = "flex";
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalText;
  }
}

async function handleSignupSubmit(event) {
  event.preventDefault();
  const alertBox = document.getElementById("loginAlertBox");
  if (alertBox) {
    alertBox.style.display = "none";
    alertBox.textContent = "";
  }

  const fullName = document.getElementById("signupFullName").value.trim();
  const email = document.getElementById("signupEmail").value.trim().toLowerCase();
  const password = document.getElementById("signupPassword").value;
  const submitBtn = document.getElementById("signupSubmitBtn");
  const originalText = submitBtn.innerHTML;

  if (fullName.length < 2) {
    if (alertBox) {
      alertBox.textContent = "⚠️ Full name must be at least 2 characters long.";
      alertBox.style.display = "flex";
    }
    return;
  }

  if (password.length < 6) {
    if (alertBox) {
      alertBox.textContent = "⚠️ Password must be at least 6 characters long.";
      alertBox.style.display = "flex";
    }
    return;
  }

  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span>⏳ Creating account...</span>`;

  try {
    const res = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name: fullName, email, password }),
    });

    let data;
    try {
      data = await res.json();
    } catch {
      data = null;
    }

    if (!res.ok) {
      const errorMsg = formatApiError(data, "Registration failed. Please check your inputs.");
      throw new Error(errorMsg);
    }

    authToken = data.token;
    currentUser = data.user;
    localStorage.setItem("ewaste_auth_token", authToken);

    showToast(`Account created! Welcome to EcoCycle, ${currentUser.full_name}!`, "success");
    updateAuthUI();
    loadDashboardStats();
    loadRequests();
    switchTab("dashboard");
  } catch (err) {
    if (alertBox) {
      alertBox.textContent = `⚠️ ${err.message}`;
      alertBox.style.display = "flex";
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalText;
  }
}

async function handleLogout() {
  if (authToken) {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: getAuthHeaders(),
      });
    } catch (e) {
      console.error(e);
    }
  }

  authToken = null;
  currentUser = null;
  localStorage.removeItem("ewaste_auth_token");
  showToast("Logged out successfully.", "info");
  updateAuthUI();
  switchTab("login");
}

function togglePasswordVisibility(inputId = "loginPassword", btnId = "togglePwdBtn") {
  const pwdInput = document.getElementById(inputId);
  const toggleBtn = document.getElementById(btnId);
  if (!pwdInput || !toggleBtn) return;
  if (pwdInput.type === "password") {
    pwdInput.type = "text";
    toggleBtn.textContent = "🙈";
  } else {
    pwdInput.type = "password";
    toggleBtn.textContent = "👁️";
  }
}

function quickFillCredentials(email, password) {
  switchAuthMode("signin");
  document.getElementById("loginEmail").value = email;
  document.getElementById("loginPassword").value = password;
  const alertBox = document.getElementById("loginAlertBox");
  if (alertBox) alertBox.style.display = "none";
  showToast(`Filled credentials for ${email}`, "info");
}

// -------------------------------------------------------------
// Navigation & Tab Switching (Protected from Unauthenticated Access)
// -------------------------------------------------------------
function switchTab(tabName) {
  // Enforce: unauthenticated users cannot access protected views
  if (!currentUser && tabName !== "login") {
    tabName = "login";
    window.location.hash = "#login";
  }

  const sections = document.querySelectorAll(".tab-section");
  sections.forEach((sec) => sec.classList.remove("active"));

  let target = document.getElementById(`section-${tabName}`);
  if (!target) {
    tabName = currentUser ? "dashboard" : "login";
    target = document.getElementById(`section-${tabName}`);
  }
  if (target) {
    target.classList.add("active");
  }

  // Update hash when user navigates
  if (currentUser) {
    window.location.hash = `#${tabName}`;
  }

  // Update navbar links
  const links = document.querySelectorAll(".nav-link");
  links.forEach((link) => {
    if (link.dataset.tab === tabName) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });

  // Refresh relevant data
  if (tabName === "dashboard" && currentUser) {
    loadDashboardStats();
  } else if (tabName === "requests" && currentUser) {
    loadRequests();
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

// -------------------------------------------------------------
// Toast Notifications
// -------------------------------------------------------------
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const icon = type === "success" ? "✅" : type === "error" ? "⚠️" : "ℹ️";
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// -------------------------------------------------------------
// Modals
// -------------------------------------------------------------
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add("active");
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove("active");
}

function openDemoModal() {
  openModal("demoModal");
}

// -------------------------------------------------------------
// Load Categories
// -------------------------------------------------------------
async function loadCategories() {
  try {
    const res = await fetch("/api/categories");
    const data = await res.json();
    categoriesList = data.categories || [];

    // Populate Pickup Form category select
    const formSelect = document.getElementById("category");
    if (formSelect) {
      formSelect.innerHTML = categoriesList
        .map((c) => `<option value="${c}">${c}</option>`)
        .join("");
    }

    // Populate Table Filter category select
    const filterSelect = document.getElementById("categoryFilter");
    if (filterSelect) {
      filterSelect.innerHTML =
        '<option value="all">All Categories</option>' +
        categoriesList.map((c) => `<option value="${c}">${c}</option>`).join("");
    }

    // Populate Landing Page categories showcase
    const catGrid = document.getElementById("acceptedCategoriesGrid");
    if (catGrid) {
      catGrid.innerHTML = categoriesList
        .map((c) => {
          const icon = CATEGORY_ICONS[c] || "📦";
          return `
            <div class="category-chip">
              <span class="cat-emoji">${icon}</span>
              <div>
                <h4>${c}</h4>
                <span>Safe recycling & dismantling</span>
              </div>
            </div>
          `;
        })
        .join("");
    }
  } catch (err) {
    console.error("Failed to load categories:", err);
  }
}

// -------------------------------------------------------------
// Dashboard Statistics (Scoped for user or system-wide for admin)
// -------------------------------------------------------------
async function loadDashboardStats() {
  if (!currentUser) return;
  try {
    const res = await fetch("/api/dashboard/stats", {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Could not fetch metrics");
    const stats = await res.json();

    // Stat Cards
    document.getElementById("statTotal").textContent = stats.total_requests || 0;
    document.getElementById("statPending").textContent = stats.pending || 0;
    document.getElementById("statScheduled").textContent = stats.scheduled || 0;
    document.getElementById("statCollected").textContent = stats.collected || 0;
    document.getElementById("statProcessed").textContent = stats.processed || 0;

    // Status Progress Bars
    const total = stats.total_requests || 0;
    const calcPct = (cnt) => (total > 0 ? Math.round((cnt / total) * 100) : 0);

    const barContainer = document.getElementById("statusDistributionBars");
    if (barContainer) {
      const pendingPct = calcPct(stats.pending);
      const scheduledPct = calcPct(stats.scheduled);
      const collectedPct = calcPct(stats.collected);
      const processedPct = calcPct(stats.processed);

      barContainer.innerHTML = `
        <div class="progress-group">
          <div class="progress-label-wrap">
            <span>Pending Pickup</span>
            <span>${stats.pending} (${pendingPct}%)</span>
          </div>
          <div class="progress-bar-bg"><div class="progress-bar-fill progress-pending" style="width: ${pendingPct}%"></div></div>
        </div>

        <div class="progress-group">
          <div class="progress-label-wrap">
            <span>Scheduled</span>
            <span>${stats.scheduled} (${scheduledPct}%)</span>
          </div>
          <div class="progress-bar-bg"><div class="progress-bar-fill progress-scheduled" style="width: ${scheduledPct}%"></div></div>
        </div>

        <div class="progress-group">
          <div class="progress-label-wrap">
            <span>Collected</span>
            <span>${stats.collected} (${collectedPct}%)</span>
          </div>
          <div class="progress-bar-bg"><div class="progress-bar-fill progress-collected" style="width: ${collectedPct}%"></div></div>
        </div>

        <div class="progress-group">
          <div class="progress-label-wrap">
            <span>Processed / Recycled</span>
            <span>${stats.processed} (${processedPct}%)</span>
          </div>
          <div class="progress-bar-bg"><div class="progress-bar-fill progress-processed" style="width: ${processedPct}%"></div></div>
        </div>
      `;
    }

    // Category Tags
    const catTagsContainer = document.getElementById("categoryDistributionTags");
    if (catTagsContainer) {
      const counts = stats.category_counts || {};
      const keys = Object.keys(counts);
      if (keys.length === 0) {
        catTagsContainer.innerHTML = `<span style="color: var(--text-muted); font-size: 0.85rem;">No items recorded yet.</span>`;
      } else {
        catTagsContainer.innerHTML = keys
          .map((cat) => {
            const icon = CATEGORY_ICONS[cat] || "📦";
            return `
              <div class="cat-count-pill">
                <span>${icon} ${cat}</span>
                <strong>${counts[cat]}</strong>
              </div>
            `;
          })
          .join("");
      }
    }

    // Recent Activity Table
    const recentTbody = document.getElementById("recentActivityTableBody");
    if (recentTbody) {
      const recent = stats.recent_activity || [];
      if (recent.length === 0) {
        recentTbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-muted); padding: 1.5rem;">No collection activity recorded yet.</td></tr>`;
      } else {
        recentTbody.innerHTML = recent
          .map(
            (r) => `
            <tr>
              <td><span class="tracking-code">${r.tracking_id}</span></td>
              <td><strong>${escapeHtml(r.full_name)}</strong><br><small style="color:var(--text-muted);">${escapeHtml(r.city)}</small></td>
              <td>${escapeHtml(r.category)} - ${escapeHtml(r.item_description.substring(0, 30))}...</td>
              <td>${r.preferred_date}</td>
              <td><span class="status-badge ${r.status.toLowerCase()}">${r.status}</span></td>
            </tr>
          `
          )
          .join("");
      }
    }
  } catch (err) {
    console.error("Dashboard metrics error:", err);
  }
}

// -------------------------------------------------------------
// Requests Table, Search & Filter (User vs Admin)
// -------------------------------------------------------------
async function loadRequests() {
  if (!currentUser) return;
  const search = document.getElementById("searchInput")?.value || "";
  const status = document.getElementById("statusFilter")?.value || "all";
  const category = document.getElementById("categoryFilter")?.value || "all";

  const params = new URLSearchParams();
  if (search.trim()) params.append("search", search.trim());
  if (status && status !== "all") params.append("status", status);
  if (category && category !== "all") params.append("category", category);

  try {
    const res = await fetch(`/api/requests?${params.toString()}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load requests");
    const data = await res.json();
    cachedRequests = data.requests || [];
    renderRequestsTable(cachedRequests);
  } catch (err) {
    console.error("Error fetching requests:", err);
    showToast("Failed to fetch requests", "error");
  }
}

function renderRequestsTable(requests) {
  const tbody = document.getElementById("requestsTableBody");
  const emptyState = document.getElementById("tableEmptyState");
  const countBadge = document.getElementById("tableCountBadge");
  const isAdmin = currentUser && currentUser.role === "admin";

  if (countBadge) {
    const label = currentUser && currentUser.role === "user" ? "your requests" : "requests";
    countBadge.textContent = `Showing ${requests.length} ${label}`;
  }

  if (!requests || requests.length === 0) {
    tbody.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }

  emptyState.style.display = "none";
  tbody.innerHTML = requests
    .map((r) => {
      const catIcon = CATEGORY_ICONS[r.category] || "📦";

      // Inline status dropdown is only enabled for admins
      const statusCell = isAdmin
        ? `
          <div style="display:flex; flex-direction:column; gap:0.35rem;">
            <span class="status-badge ${r.status.toLowerCase()}">${r.status}</span>
            <select class="status-select-inline" onchange="updateRequestStatus(${r.id}, this.value)" title="Change request status">
              <option value="Pending" ${r.status === "Pending" ? "selected" : ""}>Pending</option>
              <option value="Scheduled" ${r.status === "Scheduled" ? "selected" : ""}>Scheduled</option>
              <option value="Collected" ${r.status === "Collected" ? "selected" : ""}>Collected</option>
              <option value="Processed" ${r.status === "Processed" ? "selected" : ""}>Processed</option>
            </select>
          </div>
        `
        : `<span class="status-badge ${r.status.toLowerCase()}" style="font-size:0.85rem; padding:0.35rem 0.65rem;">${r.status}</span>`;

      // Delete action is only available for admins
      const actionsCell = isAdmin
        ? `
          <div class="table-actions">
            <button class="btn btn-secondary btn-sm" onclick="viewRequestDetails(${r.id})" title="View Details">
              👁️ View
            </button>
            <button class="btn btn-danger btn-sm" onclick="promptDelete(${r.id}, '${r.tracking_id}', '${escapeHtml(r.full_name)}')" title="Delete Request">
              🗑️
            </button>
          </div>
        `
        : `
          <div class="table-actions">
            <button class="btn btn-secondary btn-sm" onclick="viewRequestDetails(${r.id})" title="View Details">
              👁️ View Details
            </button>
          </div>
        `;

      return `
      <tr>
        <td>
          <span class="tracking-code">${r.tracking_id}</span><br>
          <small style="color:var(--text-muted); font-size:0.75rem;">ID: #${r.id}</small>
        </td>
        <td>
          <div class="customer-name">${escapeHtml(r.full_name)}</div>
          <div class="customer-sub">📞 ${escapeHtml(r.phone)}</div>
          <div class="customer-sub">📍 ${escapeHtml(r.city)}</div>
        </td>
        <td>
          <div><strong>${catIcon} ${escapeHtml(r.category)}</strong></div>
          <div style="font-size: 0.8rem; color: #475569;">${escapeHtml(r.item_description)}</div>
          <div style="margin-top: 0.25rem;">
            <span class="condition-badge">${escapeHtml(r.condition)}</span>
          </div>
        </td>
        <td><strong>${r.quantity}</strong></td>
        <td>
          <div>${r.preferred_date}</div>
        </td>
        <td>${statusCell}</td>
        <td>${actionsCell}</td>
      </tr>
    `;
    })
    .join("");
}

function onSearchChange() {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    loadRequests();
  }, 250);
}

function onFilterChange() {
  loadRequests();
}

// -------------------------------------------------------------
// Update Status (Admin Only)
// -------------------------------------------------------------
async function updateRequestStatus(id, newStatus) {
  try {
    const res = await fetch(`/api/requests/${id}/status`, {
      method: "PATCH",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status: newStatus }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to update status");
    }

    showToast(`Request #${id} status changed to ${newStatus}`, "success");
    loadRequests();
    loadDashboardStats();
  } catch (err) {
    showToast(err.message, "error");
    loadRequests();
  }
}

// -------------------------------------------------------------
// View Request Details Modal
// -------------------------------------------------------------
async function viewRequestDetails(id) {
  let req = cachedRequests.find((r) => r.id === id);
  if (!req) {
    try {
      const res = await fetch(`/api/requests/${id}`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) req = await res.json();
    } catch (e) {
      console.error(e);
    }
  }

  if (!req) {
    showToast("Request not found", "error");
    return;
  }

  const isAdmin = currentUser && currentUser.role === "admin";
  const modalBody = document.getElementById("detailsModalBody");

  const adminStatusControls = isAdmin
    ? `
      <div style="margin-top:1.25rem; padding-top:1rem; border-top:1px solid var(--border-color); display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.5rem;">
        <span style="font-size:0.85rem; font-weight:600;">Update Status:</span>
        <select class="form-select" style="width: auto; padding: 0.4rem 0.8rem;" onchange="updateRequestStatus(${req.id}, this.value); closeModal('detailsModal');">
          <option value="Pending" ${req.status === "Pending" ? "selected" : ""}>Pending</option>
          <option value="Scheduled" ${req.status === "Scheduled" ? "selected" : ""}>Scheduled</option>
          <option value="Collected" ${req.status === "Collected" ? "selected" : ""}>Collected</option>
          <option value="Processed" ${req.status === "Processed" ? "selected" : ""}>Processed</option>
        </select>
      </div>
    `
    : `
      <div style="margin-top:1.25rem; padding-top:1rem; border-top:1px solid var(--border-color); font-size:0.825rem; color:var(--text-muted);">
        Status is verified and managed by the certified recycling team.
      </div>
    `;

  modalBody.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.25rem; flex-wrap:wrap; gap:0.5rem;">
      <div>
        <span class="tracking-code" style="font-size:1.05rem;">${req.tracking_id}</span>
        <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.2rem;">Submitted on: ${req.created_at}</div>
      </div>
      <span class="status-badge ${req.status.toLowerCase()}" style="font-size:0.85rem; padding:0.35rem 0.8rem;">
        ${req.status}
      </span>
    </div>

    <div class="details-grid">
      <div>
        <div class="detail-item-label">Customer Name</div>
        <div class="detail-item-value">${escapeHtml(req.full_name)}</div>
      </div>
      <div>
        <div class="detail-item-label">Contact Details</div>
        <div class="detail-item-value">📞 ${escapeHtml(req.phone)}<br>✉️ ${escapeHtml(req.email)}</div>
      </div>
      <div style="grid-column: span 2;">
        <div class="detail-item-label">Pickup Address</div>
        <div class="detail-item-value">${escapeHtml(req.address)}, ${escapeHtml(req.city)} - ${escapeHtml(req.pincode)}</div>
      </div>
      <div>
        <div class="detail-item-label">Item Category & Qty</div>
        <div class="detail-item-value">${escapeHtml(req.category)} (${req.quantity} unit${req.quantity > 1 ? "s" : ""})</div>
      </div>
      <div>
        <div class="detail-item-label">Condition</div>
        <div class="detail-item-value">${escapeHtml(req.condition)}</div>
      </div>
      <div style="grid-column: span 2;">
        <div class="detail-item-label">Item Description</div>
        <div class="detail-item-value" style="font-weight:400; background:#f8fafc; padding:0.6rem; border-radius:var(--radius-sm); border:1px solid #e2e8f0;">
          ${escapeHtml(req.item_description)}
        </div>
      </div>
      <div>
        <div class="detail-item-label">Preferred Date</div>
        <div class="detail-item-value">📅 ${req.preferred_date}</div>
      </div>
      <div>
        <div class="detail-item-label">Special Notes</div>
        <div class="detail-item-value" style="font-weight:400;">
          ${req.special_notes ? escapeHtml(req.special_notes) : "None provided"}
        </div>
      </div>
    </div>

    ${adminStatusControls}
  `;

  openModal("detailsModal");
}

// -------------------------------------------------------------
// Delete Request Modal & Confirmation (Admin Only)
// -------------------------------------------------------------
function promptDelete(id, trackingId, customerName) {
  currentDeleteId = id;
  document.getElementById("deleteTrackingId").textContent = trackingId;
  document.getElementById("deleteCustomerName").textContent = customerName;

  const confirmBtn = document.getElementById("confirmDeleteBtn");
  confirmBtn.onclick = executeDelete;

  openModal("deleteModal");
}

async function executeDelete() {
  if (!currentDeleteId) return;

  try {
    const res = await fetch(`/api/requests/${currentDeleteId}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to delete request");
    }

    closeModal("deleteModal");
    showToast("Request successfully deleted", "success");
    currentDeleteId = null;
    loadRequests();
    loadDashboardStats();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// -------------------------------------------------------------
// Form Submission & Validation
// -------------------------------------------------------------
function resetValidation() {
  const groups = document.querySelectorAll(".form-group");
  groups.forEach((g) => g.classList.remove("has-error"));
}

function validateField(id, condition) {
  const group = document.getElementById(`group-${id}`);
  if (!group) return true;
  if (!condition) {
    group.classList.add("has-error");
    return false;
  } else {
    group.classList.remove("has-error");
    return true;
  }
}

async function handleFormSubmit(event) {
  event.preventDefault();
  resetValidation();

  const fullName = document.getElementById("full_name").value.trim();
  const email = document.getElementById("email").value.trim();
  const phone = document.getElementById("phone").value.trim();
  const address = document.getElementById("address").value.trim();
  const city = document.getElementById("city").value.trim();
  const pincode = document.getElementById("pincode").value.trim();
  const category = document.getElementById("category").value;
  const quantity = parseInt(document.getElementById("quantity").value, 10);
  const condition = document.getElementById("condition").value;
  const itemDescription = document.getElementById("item_description").value.trim();
  const preferredDate = document.getElementById("preferred_date").value;
  const specialNotes = document.getElementById("special_notes").value.trim();

  // Validate
  let isValid = true;
  if (!validateField("full_name", fullName.length >= 2)) isValid = false;

  const emailRegex = /^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$/;
  if (!validateField("email", emailRegex.test(email))) isValid = false;

  const phoneDigits = phone.replace(/[^\d+]/g, "");
  if (!validateField("phone", phoneDigits.length >= 7)) isValid = false;

  if (!validateField("address", address.length >= 5)) isValid = false;
  if (!validateField("city", city.length >= 2)) isValid = false;
  if (!validateField("pincode", pincode.length >= 3)) isValid = false;
  if (!validateField("category", !!category)) isValid = false;
  if (!validateField("quantity", quantity >= 1 && quantity <= 1000)) isValid = false;
  if (!validateField("item_description", itemDescription.length >= 3)) isValid = false;
  if (!validateField("preferred_date", !!preferredDate)) isValid = false;

  if (!isValid) {
    showToast("Please correct the highlighted fields.", "error");
    return;
  }

  const submitBtn = document.getElementById("submitBtn");
  const originalText = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span>⏳ Submitting...</span>`;

  try {
    const payload = {
      full_name: fullName,
      email: email,
      phone: phone,
      address: address,
      city: city,
      pincode: pincode,
      category: category,
      item_description: itemDescription,
      quantity: quantity,
      condition: condition,
      preferred_date: preferredDate,
      special_notes: specialNotes,
    };

    const res = await fetch("/api/requests", {
      method: "POST",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Submission failed");
    }

    const created = await res.json();

    // Show success receipt
    document.getElementById("pickupFormCard").style.display = "none";
    const successCard = document.getElementById("submitSuccessCard");
    successCard.style.display = "block";

    document.getElementById("successTrackingId").textContent = created.tracking_id;
    document.getElementById("successDate").textContent = created.preferred_date;
    document.getElementById("successSummaryText").innerHTML = `
      Collection scheduled for <strong>${created.preferred_date}</strong> for <strong>${created.quantity}x ${escapeHtml(created.category)}</strong>.
    `;

    showToast("Collection request submitted successfully!", "success");
    loadDashboardStats();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalText;
  }
}

function resetFormForNew() {
  document.getElementById("pickupForm").reset();
  resetValidation();
  setDefaultPickupDate();

  if (currentUser) {
    document.getElementById("full_name").value = currentUser.full_name;
    document.getElementById("email").value = currentUser.email;
  }

  document.getElementById("submitSuccessCard").style.display = "none";
  document.getElementById("pickupFormCard").style.display = "block";
}

function setDefaultPickupDate() {
  const dateInput = document.getElementById("preferred_date");
  if (dateInput) {
    const today = new Date().toISOString().split("T")[0];
    dateInput.min = today;
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    dateInput.value = tomorrow.toISOString().split("T")[0];
  }
}

// -------------------------------------------------------------
// Demo Data Helpers (Admin Only)
// -------------------------------------------------------------
async function seedDemoData() {
  closeModal("demoModal");
  try {
    const res = await fetch("/api/demo/seed", {
      method: "POST",
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to seed demo data");
    showToast(`Added ${data.count} demo requests for presentation!`, "success");
    loadDashboardStats();
    loadRequests();
    switchTab("requests");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function clearAllDemoData() {
  closeModal("demoModal");
  try {
    const res = await fetch("/api/demo/clear", {
      method: "POST",
      headers: getAuthHeaders(),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to clear data");
    showToast(data.message, "info");
    loadDashboardStats();
    loadRequests();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// -------------------------------------------------------------
// Utility Functions
// -------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// -------------------------------------------------------------
// App Initialization
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  try {
    await loadCategories();
  } catch (e) {
    console.warn("Categories initialization error:", e);
  }
  try {
    setDefaultPickupDate();
  } catch (e) {
    console.warn("Pickup date initialization error:", e);
  }
  try {
    await checkAuthStatus();
  } catch (e) {
    console.error("Auth status initialization error:", e);
    switchTab("login");
  }
});

const views = {
  dashboard: ["Dashboard", "Overview of your restaurant intelligence project."],
  recommendations: ["Restaurant Recommendations", "Find restaurants from user preferences using the FastAPI backend."],
  rating: ["Rating Prediction", "Show model results, metrics, and feature importance."],
  location: ["Location Analysis", "Explore generated maps and geographical insights."],
  admin: ["Admin", "Create users and plan admin-only restaurant management."],
  manager: ["Restaurant Manager", "Manager portal concept for assigned restaurant operations."],
  reports: ["Reports", "Saved model and analysis outputs."],
};

const apiBaseInput = document.querySelector("#apiBase");
const authApiBaseInput = document.querySelector("#authApiBase");
const currentUserIdInput = document.querySelector("#currentUserId");
const apiStatus = document.querySelector("#apiStatus");
const pageTitle = document.querySelector("#pageTitle");
const pageSubtitle = document.querySelector("#pageSubtitle");
const authScreen = document.querySelector("#authScreen");
const appShell = document.querySelectorAll(".app-shell");
const sessionStatus = document.querySelector("#sessionStatus");
const authOutput = document.querySelector("#authOutput");

let currentUser = null;

function apiBase() {
  return apiBaseInput.value.replace(/\/$/, "");
}

function syncApiBaseFromAuth() {
  apiBaseInput.value = authApiBaseInput.value;
}

function showApp(user) {
  currentUser = user;
  currentUserIdInput.value = user.user_id;
  sessionStatus.textContent = `${user.name} (${user.role})`;
  applyRoleVisibility(user.role);
  authScreen.classList.add("hidden");
  appShell.forEach((element) => element.classList.remove("hidden"));
  setView("dashboard");
}

function showAuth() {
  currentUser = null;
  currentUserIdInput.value = "";
  sessionStatus.textContent = "Not logged in";
  authScreen.classList.remove("hidden");
  appShell.forEach((element) => element.classList.add("hidden"));
}

function applyRoleVisibility(role) {
  document.querySelectorAll("[data-roles]").forEach((element) => {
    const allowedRoles = element.dataset.roles.split(",").map((item) => item.trim());
    element.classList.toggle("hidden", !allowedRoles.includes(role));
  });
}

function setView(viewName) {
  const targetViewButton = document.querySelector(`.nav-item[data-view="${viewName}"]`);
  if (targetViewButton && targetViewButton.classList.contains("hidden")) {
    viewName = "dashboard";
  }
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.querySelector(`#${viewName}`).classList.add("active");
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === viewName));
  pageTitle.textContent = views[viewName][0];
  pageSubtitle.textContent = views[viewName][1];
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view));
});

document.querySelectorAll("[data-view-jump]").forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.viewJump));
});

async function request(path, options = {}) {
  const userId = currentUserIdInput.value.trim();
  const authHeaders = userId ? { "X-User-Id": userId } : {};
  const response = await fetch(`${apiBase()}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeaders, ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!response.ok) {
    throw new Error(JSON.stringify(data, null, 2));
  }
  return data;
}

document.querySelector("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseFromAuth();
  const form = new FormData(event.currentTarget);
  authOutput.textContent = "Logging in...";
  try {
    const user = await request("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: form.get("email"),
        password: form.get("password"),
      }),
    });
    authOutput.textContent = `Logged in as ${user.name} (${user.role})`;
    showApp(user);
  } catch (error) {
    authOutput.textContent = error.message;
  }
});

document.querySelector("#registerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  syncApiBaseFromAuth();
  const form = new FormData(event.currentTarget);
  authOutput.textContent = "Creating account...";
  try {
    const user = await request("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        name: form.get("name"),
        email: form.get("email"),
        password: form.get("password"),
        role: form.get("role") || "user",
        managed_restaurant_id: optionalNumber(form.get("managed_restaurant_id")),
      }),
    });
    authOutput.textContent = `Created and logged in as ${user.name} (${user.role}), user_id: ${user.user_id}`;
    showApp(user);
  } catch (error) {
    authOutput.textContent = error.message;
  }
});

document.querySelector("#logoutBtn").addEventListener("click", () => {
  showAuth();
});

document.querySelector("#healthBtn").addEventListener("click", async () => {
  apiStatus.className = "status muted";
  apiStatus.textContent = "Checking...";
  try {
    const data = await request("/health");
    apiStatus.className = "status ok";
    apiStatus.textContent = `Connected: ${data.status}`;
  } catch (error) {
    apiStatus.className = "status bad";
    apiStatus.textContent = "API not reachable";
  }
});

document.querySelector("#importBtn").addEventListener("click", async () => {
  const output = document.querySelector("#importOutput");
  output.textContent = "Importing Dataset/cleaned_dataset.csv...";
  try {
    const data = await request("/restaurants/import", { method: "POST" });
    output.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    output.textContent = error.message;
  }
});

document.querySelector("#userForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const output = document.querySelector("#userOutput");
  const payload = {
    name: form.get("name"),
    email: form.get("email"),
    password: form.get("password"),
    role: form.get("role") || "user",
    managed_restaurant_id: optionalNumber(form.get("managed_restaurant_id")),
  };
  try {
    const data = await request("/users", { method: "POST", body: JSON.stringify(payload) });
    if (data.user_id) {
      currentUserIdInput.value = data.user_id;
      output.textContent = `Created user_id: ${data.user_id}\n\n${JSON.stringify(data, null, 2)}`;
    } else {
      output.textContent = JSON.stringify(data, null, 2);
    }
  } catch (error) {
    output.textContent = error.message;
  }
});

document.querySelector("#loadUsersBtn").addEventListener("click", async () => {
  const output = document.querySelector("#usersOutput");
  output.textContent = "Loading users from backend...";
  try {
    const data = await request("/users");
    output.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    output.textContent = error.message;
  }
});

document.querySelector("#adminRestaurantForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const output = document.querySelector("#adminRestaurantOutput");
  output.textContent = "Creating restaurant...";
  try {
    const payload = restaurantPayloadFromForm(new FormData(event.currentTarget));
    const data = await request("/admin/restaurants", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    output.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    output.textContent = error.message;
  }
});

document.querySelector("#assignManagerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const output = document.querySelector("#assignManagerOutput");
  output.textContent = "Assigning manager...";
  try {
    const data = await request("/admin/assign-manager", {
      method: "POST",
      body: JSON.stringify({
        manager_user_id: optionalNumber(form.get("manager_user_id")),
        restaurant_id: optionalNumber(form.get("restaurant_id")),
      }),
    });
    output.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    output.textContent = error.message;
  }
});

document.querySelector("#managerRestaurantForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const output = document.querySelector("#managerRestaurantOutput");
  const restaurantId = optionalNumber(form.get("restaurant_id"));
  output.textContent = "Updating restaurant...";
  try {
    const payload = restaurantPayloadFromForm(form);
    const data = await request(`/manager/restaurants/${restaurantId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    output.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    output.textContent = error.message;
  }
});

function restaurantPayloadFromForm(form) {
  const cuisines = optionalText(form.get("cuisines"));
  return {
    restaurant_name: form.get("restaurant_name"),
    city: optionalText(form.get("city")),
    address: optionalText(form.get("address")),
    locality: optionalText(form.get("locality")),
    cuisines: cuisines ? cuisines.split(",").map((item) => item.trim()).filter(Boolean) : [],
    average_cost_inr: optionalNumber(form.get("average_cost_inr")),
    price_range: optionalNumber(form.get("price_range")),
    aggregate_rating: optionalNumber(form.get("aggregate_rating")),
    votes: optionalNumber(form.get("votes")),
    has_table_booking: optionalText(form.get("has_table_booking")),
    has_online_delivery: optionalText(form.get("has_online_delivery")),
    is_delivering_now: optionalText(form.get("is_delivering_now")),
  };
}

function optionalNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  return Number(value);
}

function optionalText(value) {
  if (value === null || value === undefined || value.trim() === "") return null;
  return value.trim();
}

document.querySelector("#recommendForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const results = document.querySelector("#recommendationResults");
  results.innerHTML = "<p class='muted'>Loading recommendations...</p>";

  const cuisines = optionalText(form.get("cuisines"));
  const payload = {
    user_id: currentUser ? currentUser.user_id : null,
    cuisines: cuisines ? cuisines.split(",").map((item) => item.trim()).filter(Boolean) : [],
    city: optionalText(form.get("city")),
    price_range: optionalNumber(form.get("price_range")),
    min_rating: optionalNumber(form.get("min_rating")),
    max_cost: optionalNumber(form.get("max_cost")),
    online_delivery: optionalText(form.get("online_delivery")),
    table_booking: optionalText(form.get("table_booking")),
    popularity_category: optionalText(form.get("popularity_category")),
    cost_category: optionalText(form.get("cost_category")),
    top_n: optionalNumber(form.get("top_n")) || 10,
    save_history: true,
  };

  try {
    const data = await request("/recommendations", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderRecommendations(data.recommendations || []);
  } catch (error) {
    results.innerHTML = `<pre class="output-box">${error.message}</pre>`;
  }
});

function renderRecommendations(items) {
  const results = document.querySelector("#recommendationResults");
  if (!items.length) {
    results.innerHTML = "<p class='muted'>No recommendations found.</p>";
    return;
  }

  results.innerHTML = items.map((item) => `
    <article class="restaurant-card">
      <header>
        <h4>#${item.rank} ${item.restaurant_name}</h4>
        <span class="score">${Number(item.score).toFixed(2)}</span>
      </header>
      <dl>
        <dt>City</dt><dd>${item.city || "-"}</dd>
        <dt>Cuisines</dt><dd>${item.cuisines || "-"}</dd>
        <dt>Rating</dt><dd>${item.aggregate_rating ?? "-"}</dd>
        <dt>Cost</dt><dd>Rs. ${item.average_cost_inr ?? "-"}</dd>
        <dt>Price Range</dt><dd>${item.price_range ?? "-"}</dd>
        <dt>Delivery</dt><dd>${item.has_online_delivery || "-"}</dd>
      </dl>
      <p class="reason">${item.match_reasons || "Score generated from available restaurant attributes."}</p>
    </article>
  `).join("");
}

import { User, UserPlus, UtensilsCrossed } from "lucide-react";
import { useState } from "react";
import vegetablesImg from "./assets/login-vegetables.png";

// ============================================================
// Constants
// ============================================================
const VIEW_META = {
  dashboard:       ["Dashboard",                 "Overview of your restaurant intelligence project."],
  recommendations: ["Restaurant Recommendations","Find restaurants from user preferences using the FastAPI backend."],
  rating:          ["Rating Prediction",         "Show model results, metrics, and feature importance."],
  location:        ["Location Analysis",         "Explore generated maps and geographical insights."],
  admin:           ["Admin",                     "Create users and plan admin-only restaurant management."],
  manager:         ["Restaurant Manager",        "Manager portal concept for assigned restaurant operations."],
  reports:         ["Reports",                   "Saved model and analysis outputs."],
};

const NAV_ITEMS = [
  { view: "dashboard",       icon: "🏠", label: "Dashboard" },
  { view: "recommendations", icon: "🍽️", label: "Recommendations" },
  { view: "rating",          icon: "⭐",  label: "Rating Prediction" },
  { view: "location",        icon: "📍", label: "Location Analysis" },
  { view: "admin",           icon: "⚙️", label: "Admin",              roles: ["admin"] },
  { view: "manager",         icon: "🏪", label: "Restaurant Manager", roles: ["admin", "manager"] },
  { view: "reports",         icon: "📊", label: "Reports" },
];

const TOP_MENU_ITEMS = [
  { view: "dashboard", label: "Home" },
  { view: "recommendations", label: "Get Recommendation" },
  { view: "location", label: "Explore Maps" },
  { view: "rating", label: "Rating" },
  { view: "reports", label: "Reports" },
  { view: "admin", label: "Admin", roles: ["admin"] },
  { view: "manager", label: "Manager", roles: ["admin", "manager"] },
];

const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const CUISINE_OPTIONS = ["Italian", "Japanese", "French", "Mexican", "Indian", "Thai", "Chinese", "American", "Mediterranean", "Korean"];
const CITY_OPTIONS = ["New Delhi", "Mumbai", "Bangalore", "Pune", "Chennai", "Hyderabad", "Kolkata", "Goa"];
const MATCH_IMAGES = [
  "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=160&q=80",
  "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=160&q=80",
  "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=160&q=80",
  "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=160&q=80",
];

// ============================================================
// Helpers
// ============================================================
function optNum(v) {
  if (v === null || v === undefined || String(v).trim() === "") return null;
  return Number(v);
}
function optStr(v) {
  if (v === null || v === undefined || String(v).trim() === "") return null;
  return String(v).trim();
}

// ============================================================
// API request — same logic as original app.js
// ============================================================
async function makeRequest(apiBase, userId, path, options = {}) {
  const authHeaders = userId ? { "X-User-Id": String(userId) } : {};
  const isFormData = options.body instanceof FormData;
  const res = await fetch(`${apiBase}${path}`, {
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...authHeaders,
      ...(options.headers || {}),
    },
    ...options,
  });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; }
  catch { data = { raw: text }; }
  if (!res.ok) throw new Error(JSON.stringify(data, null, 2));
  return data;
}

// ============================================================
// Styles
// ============================================================
const APP_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Inter:wght@400;500;600;700;800;900&display=swap');
*, *::before, *::after { box-sizing: border-box; letter-spacing: 0; }

.ri-body { min-height: 100vh; font-family: Inter, "Segoe UI", Arial, sans-serif; color: #1a2e1a; }

/* AUTH */
.ri-auth { position: fixed; inset: 0; z-index: 20; display: flex; align-items: stretch; background: #f0f3ea; overflow-y: auto; }
.ri-auth-card { display: flex; width: 100%; min-height: 100vh; }
.ri-auth-copy { position: relative; flex: 0 0 55%; padding: clamp(28px,3.5vw,48px); display: flex; flex-direction: column; overflow: hidden; color: white; background-size: cover; background-position: center; }
.ri-auth-copy > * { position: relative; z-index: 1; }
.ri-brand { display: flex; align-items: center; gap: 10px; }
.ri-brand-mark { width: 38px; height: 38px; border-radius: 8px; background: rgba(255,255,255,0.20); display: grid; place-items: center; color: white; flex-shrink: 0; }
.ri-brand h1 { font-size: 15px; font-weight: 600; color: white; margin: 0; }
.ri-auth-headline { margin-top: auto; }
.ri-auth-headline h2 { font-family: "Playfair Display", Georgia, serif; font-size: clamp(22px,2.6vw,34px); font-weight: 700; line-height: 1.1; color: #fff; margin: 0 0 10px; max-width: 420px; }
.ri-lead { font-size: 13px; color: rgba(255,255,255,0.82); line-height: 1.6; max-width: 400px; margin: 0 0 24px; }
.ri-auth-stats { display: flex; gap: 28px; }
.ri-auth-stats span { display: flex; flex-direction: column; gap: 2px; font-size: 12px; color: rgba(255,255,255,0.78); }
.ri-auth-stats strong { display: block; font-family: "Playfair Display", Georgia, serif; font-size: 20px; font-weight: 700; color: white; line-height: 1; }

.ri-auth-forms { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 18px; padding: clamp(36px,5vw,72px) clamp(32px,4.5vw,64px); background: #f0f3ea; overflow-y: auto; }
.ri-auth-heading h2 { font-family: Inter, sans-serif; font-size: 26px; font-weight: 700; color: #111a11; margin: 0 0 5px; letter-spacing: -0.02em; }
.ri-auth-heading p { color: #6b7a6b; font-size: 13px; line-height: 1.5; margin: 0; max-width: 380px; }
.ri-auth-switch { display: grid; grid-template-columns: 1fr 1fr; padding: 3px; border-radius: 9px; background: #dde3d4; width: min(380px,100%); }
.ri-auth-tab { display: flex; align-items: center; justify-content: center; gap: 7px; min-height: 38px; border: 0; border-radius: 7px; background: transparent; color: #6b7a6b; font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 150ms; }
.ri-auth-tab.active { background: #fff; color: #1a2e1a; box-shadow: 0 1px 5px rgba(20,40,20,0.14); }
.ri-form { display: grid; gap: 14px; width: min(380px,100%); }
.ri-api-label { width: min(380px,100%); display: grid; gap: 5px; font-size: 13px; font-weight: 600; color: #6b7a6b; }
.ri-label { display: grid; gap: 6px; font-size: 14px; font-weight: 600; color: #2a3a2a; }
.ri-input, .ri-select { width: 100%; height: 44px; border: 1px solid #cdd5c4; border-radius: 8px; padding: 0 13px; background: #fff; color: #1a2e1a; font: inherit; font-size: 14px; outline: none; transition: border-color 150ms, box-shadow 150ms; }
.ri-input:focus, .ri-select:focus { border-color: #3d8b45; box-shadow: 0 0 0 3px rgba(61,139,69,0.14); }
.ri-input::placeholder { color: #aab5aa; }
.ri-btn-primary { width: 100%; height: 46px; border: 0; border-radius: 8px; font: inherit; font-size: 15px; font-weight: 700; cursor: pointer; background: #3d8b45; color: white; transition: background 140ms, transform 100ms; }
.ri-btn-primary:hover { background: #2e6e35; transform: translateY(-1px); }
.ri-btn-secondary { width: 100%; height: 46px; border: 0; border-radius: 8px; font: inherit; font-size: 15px; font-weight: 700; cursor: pointer; background: #dde3d4; color: #1a2e1a; transition: background 140ms, transform 100ms; }
.ri-btn-secondary:hover { background: #ccd4c0; transform: translateY(-1px); }
.ri-output { border-radius: 8px; background: #dde3d4; color: #1a2e1a; font-size: 12px; font-family: monospace; line-height: 1.5; min-height: 48px; padding: 10px 13px; white-space: pre-wrap; word-break: break-word; overflow: auto; width: min(380px,100%); margin: 0; }

/* APP SHELL */
.ri-shell { display: block; min-height: 100vh; font-family: Inter, sans-serif; color: #1a3c22; background: #f4f8ed; }
.ri-sidebar { position: fixed; z-index: 10; inset: 0 auto 0 0; width: min(320px,88vw); transform: translateX(-104%); transition: transform 220ms ease; background: linear-gradient(160deg,#163621 0%,#0e2718 100%); color: white; padding: 28px 18px; display: flex; flex-direction: column; gap: 22px; min-height: 100vh; box-shadow: 18px 0 60px rgba(10,25,15,0.28); }
.ri-shell.sidebar-open .ri-sidebar { transform: translateX(0); }
.ri-sidebar::after { content: ""; position: absolute; top: 0; right: 0; width: 2px; height: 100%; background: linear-gradient(180deg,#f5c518 0%,transparent 60%); pointer-events: none; }
.ri-sidebar .ri-brand-mark { width: 56px; height: 56px; border-radius: 16px; background: #f5c518; color: #0e2718; font-size: 0; }
.ri-sidebar .ri-brand-mark::before { content: "♨"; font-size: 26px; line-height: 1; }
.ri-sidebar .ri-brand h1 { font-size: 17px; font-weight: 800; color: white; }
.ri-sidebar .ri-brand p { color: rgba(255,255,255,0.55); font-size: 12px; }
.ri-nav { display: grid; gap: 3px; }
.ri-nav-item { display: flex; align-items: center; gap: 10px; min-height: 44px; border: 0; border-radius: 12px; padding: 0 14px; background: transparent; color: rgba(255,255,255,0.72); font: inherit; font-size: 14px; font-weight: 700; cursor: pointer; text-align: left; transition: all 150ms; }
.ri-nav-item:hover { background: rgba(245,197,24,0.12); color: rgba(255,255,255,0.95); }
.ri-nav-item.active { background: rgba(245,197,24,0.2); color: #f5c518; }
.ri-nav-icon { font-size: 16px; width: 20px; text-align: center; flex-shrink: 0; }
.ri-api-box { margin-top: auto; display: grid; gap: 8px; border-radius: 20px; padding: 16px; background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.09); }
.ri-api-box-label { display: block; font-size: 12px; font-weight: 700; color: rgba(255,255,255,0.65); }
.ri-api-box .ri-input { height: 40px; border-radius: 10px; background: rgba(255,255,255,0.92); border-color: transparent; font-size: 13px; color: #1a3c22; }
.ri-session { font-size: 13px; color: rgba(255,255,255,0.72); margin: 0; }
.ri-status-ok { color: #6dd470; } .ri-status-bad { color: #ff7b72; } .ri-status-muted { color: rgba(255,255,255,0.55); }
.ri-overlay { position: fixed; inset: 0; z-index: 8; background: rgba(10,25,15,0.45); backdrop-filter: blur(2px); }
.ri-main { padding: 20px 32px 32px; overflow-x: hidden; }
.ri-home-menu { position: sticky; top: 0; z-index: 7; min-height: 66px; display: grid; grid-template-columns: auto minmax(0,1fr) auto; align-items: center; gap: 22px; margin: -20px -32px 26px; padding: 0 56px; background: rgba(255,255,255,0.94); border-bottom: 1px solid rgba(232,223,202,0.86); box-shadow: 0 8px 30px rgba(20,40,20,0.06); backdrop-filter: blur(12px); }
.ri-home-brand { display: flex; align-items: center; gap: 12px; min-width: 220px; }
.ri-home-logo { width: 42px; height: 42px; display: grid; place-items: center; border-radius: 50%; background: #fef9c3; color: #6a5300; font-size: 23px; border: 1px solid #ecd671; }
.ri-home-name { font-family: "Playfair Display", Georgia, serif; font-size: 28px; font-weight: 800; color: #1a2e1a; line-height: 1; }
.ri-home-nav { display: flex; align-items: center; justify-content: center; gap: 4px; min-width: 0; }
.ri-home-nav-item { min-height: 40px; border: 0; border-radius: 999px; padding: 0 14px; background: transparent; color: #283728; font: inherit; font-size: 14px; font-weight: 700; cursor: pointer; white-space: nowrap; transition: background 140ms, color 140ms, transform 140ms; }
.ri-home-nav-item:hover { background: #edf4df; color: #1a5c22; transform: translateY(-1px); }
.ri-home-nav-item.active { background: #163621; color: #fff; }
.ri-home-actions { display: flex; align-items: center; gap: 10px; }
.ri-home-icon-btn, .ri-menu-btn { width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; border: 0; border-radius: 50%; background: #fff; color: #17351f; cursor: pointer; box-shadow: 0 8px 24px rgba(20,40,20,0.10); flex-shrink: 0; }
.ri-menu-btn { flex-direction: column; gap: 4px; background: #163621; }
.ri-menu-btn span { display: block; width: 18px; height: 2px; border-radius: 999px; background: white; }
.ri-home-user-pill { min-height: 40px; display: flex; align-items: center; gap: 8px; border-radius: 999px; padding: 0 14px; background: #f4f8ed; color: #17351f; font-size: 13px; font-weight: 800; border: 1px solid #e1e8d4; white-space: nowrap; }
.ri-home-role-dot { width: 8px; height: 8px; border-radius: 50%; background: #2d7a3a; box-shadow: 0 0 0 4px rgba(45,122,58,0.12); }
.ri-topbar { display: grid; grid-template-columns: minmax(0,1fr) auto; align-items: center; gap: 16px; margin-bottom: 28px; }
.ri-eyebrow { font-size: 11px; font-weight: 900; letter-spacing: 0.14em; text-transform: uppercase; color: #2d7a3a; margin: 0 0 6px; }
.ri-page-title { font-family: "Playfair Display", Georgia, serif; font-size: clamp(36px,4vw,58px); font-weight: 700; line-height: 1; color: #0e2718; margin: 0; }
.ri-page-subtitle { font-size: 15px; color: #7a8c6a; margin: 5px 0 0; }

/* HERO */
.ri-hero { display: grid; grid-template-columns: minmax(340px,1.05fr) minmax(240px,0.95fr); min-height: 380px; border-radius: 28px; overflow: hidden; box-shadow: 0 20px 60px rgba(20,40,20,0.14); margin-bottom: 22px; background: linear-gradient(105deg,#fefce8 0%,#fdf5b8 38%,rgba(253,244,170,0.2) 100%), url("https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=1500&q=90") right/cover; }
.ri-hero-content { padding: clamp(34px,5vw,62px); display: grid; align-content: center; gap: 14px; }
.ri-hero h2 { font-family: "Playfair Display", Georgia, serif; font-size: clamp(36px,4.5vw,62px); font-weight: 700; line-height: 0.98; color: #0e2718; margin: 0; }
.ri-hero p { font-size: 17px; color: #7a8c6a; line-height: 1.6; max-width: 520px; margin: 0; }
.ri-action-row { display: flex; flex-wrap: wrap; gap: 10px; }
.ri-hero-plate { background: radial-gradient(circle at 50% 40%,rgba(255,255,255,0.28),transparent 52%), url("https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=900&q=90") center/cover; clip-path: ellipse(72% 70% at 58% 50%); min-height: 300px; }

/* CATEGORY CHIPS */
.ri-category-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 20px; padding: 14px 18px; background: white; border-radius: 20px; border: 1.5px solid #e8dfca; box-shadow: 0 4px 16px rgba(20,40,20,0.06); }
.ri-chip { display: flex; align-items: center; gap: 6px; padding: 7px 15px; background: #f4f9e8; border: 1.5px solid #d8edb8; border-radius: 999px; font-size: 14px; font-weight: 700; color: #2d5a2e; cursor: pointer; transition: all 140ms; }
.ri-chip:hover { background: #2d7a3a; color: white; border-color: #2d7a3a; transform: translateY(-1px); }
.ri-chip-icon { font-size: 17px; }

/* METRIC GRID */
.ri-metric-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 16px; margin-bottom: 20px; }
.ri-metric-card { position: relative; background: white; border: 1.5px solid #e8dfca; border-radius: 22px; padding: 22px; box-shadow: 0 6px 20px rgba(20,40,20,0.07); overflow: hidden; }
.ri-metric-card::after { content: ""; position: absolute; bottom: 0; left: 0; right: 0; height: 3px; border-radius: 0 0 22px 22px; }
.ri-metric-card:nth-child(1)::after { background: #f5c518; } .ri-metric-card:nth-child(2)::after { background: #2d7a3a; } .ri-metric-card:nth-child(3)::after { background: #e07b2b; } .ri-metric-card:nth-child(4)::after { background: #5db131; }
.ri-metric-icon { width: 50px; height: 50px; border-radius: 14px; display: grid; place-items: center; font-size: 24px; margin-bottom: 14px; }
.ri-metric-label { display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #9aaa8a; }
.ri-metric-value { display: block; font-family: "Playfair Display", Georgia, serif; font-size: 32px; font-weight: 700; color: #0e2718; margin: 6px 0 8px; }
.ri-metric-desc { font-size: 13px; color: #7a8c6a; line-height: 1.4; margin: 0; }

/* FEATURE STRIP */
.ri-feature-strip { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 16px; margin-bottom: 20px; }
.ri-feature-card { background: white; border: 1.5px solid #e8dfca; border-radius: 22px; padding: 26px; box-shadow: 0 6px 20px rgba(20,40,20,0.07); transition: transform 160ms, box-shadow 160ms; }
.ri-feature-card:hover { transform: translateY(-4px); box-shadow: 0 16px 40px rgba(20,40,20,0.13); }
.ri-feature-icon { display: inline-grid; place-items: center; width: 52px; height: 52px; border-radius: 16px; background: #eef6e2; font-size: 26px; margin-bottom: 16px; }
.ri-feature-card h3 { font-family: "Playfair Display", Georgia, serif; font-size: 21px; font-weight: 700; color: #0e2718; margin: 0 0 10px; }
.ri-feature-card p { font-size: 14px; color: #7a8c6a; line-height: 1.6; margin: 0; }

/* PANELS */
.ri-panel-grid { display: grid; grid-template-columns: minmax(0,1fr) minmax(360px,0.8fr); gap: 18px; }
.ri-workspace { display: grid; grid-template-columns: minmax(0,1fr) minmax(360px,0.8fr); gap: 18px; align-items: start; }
.ri-panel, .ri-form-panel, .ri-results-panel { background: white; border: 1.5px solid #e8dfca; border-radius: 22px; padding: 26px; box-shadow: 0 6px 20px rgba(20,40,20,0.07); }
.ri-panel h3, .ri-form-panel h3, .ri-results-panel h3 { font-family: "Playfair Display", Georgia, serif; font-size: 22px; font-weight: 700; color: #0e2718; margin: 0 0 12px; }
.ri-panel p, .ri-muted { font-size: 14px; color: #7a8c6a; line-height: 1.6; margin: 0 0 10px; }
.ri-food-panel { background: linear-gradient(120deg,rgba(254,252,232,0.97) 0%,rgba(240,249,228,0.95) 100%), url("https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80") center/cover; }
.ri-module-list { display: grid; gap: 10px; }
.ri-module-item { border: 1.5px solid #e8dfca; border-radius: 14px; padding: 12px 16px; }
.ri-module-item strong { display: block; font-size: 15px; font-weight: 700; color: #0e2718; }
.ri-module-item span { display: block; font-size: 13px; color: #7a8c6a; margin-top: 3px; }

/* SECTION BANNERS */
.ri-section-intro { min-height: 300px; display: grid; align-items: end; border-radius: 28px; padding: clamp(34px,5vw,58px); margin-bottom: 22px; overflow: hidden; box-shadow: 0 20px 60px rgba(20,40,20,0.14); }
.ri-section-intro h2 { font-family: "Playfair Display", Georgia, serif; font-size: clamp(36px,4vw,58px); font-weight: 700; line-height: 0.98; margin: 0 0 10px; }
.ri-section-intro p { font-size: 17px; line-height: 1.6; margin: 0; max-width: 600px; }
.ri-image-intro h2, .ri-image-intro p, .ri-image-intro .ri-eyebrow { color: white; }
.ri-image-intro .ri-eyebrow { color: rgba(245,197,24,0.9); }
.ri-recommendation-intro { background: linear-gradient(110deg,rgba(15,35,22,0.88) 0%,rgba(15,35,22,0.18) 100%), url("https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1400&q=90") center/cover; }
.ri-rating-intro { background: linear-gradient(110deg,rgba(15,35,22,0.88) 0%,rgba(15,35,22,0.18) 100%), url("https://images.unsplash.com/photo-1551218808-94e220e084d2?auto=format&fit=crop&w=1400&q=90") center/cover; }
.ri-location-intro { background: linear-gradient(110deg,rgba(15,35,22,0.88) 0%,rgba(15,35,22,0.18) 100%), url("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1400&q=90") center/cover; }
.ri-report-intro { background: linear-gradient(110deg,rgba(15,35,22,0.88) 0%,rgba(15,35,22,0.18) 100%), url("https://images.unsplash.com/photo-1559339352-11d035aa65de?auto=format&fit=crop&w=1400&q=90") center/cover; }
.ri-admin-intro, .ri-manager-intro { background: linear-gradient(120deg,#fefce8 0%,#f0f9e4 60%,#dff0c8 100%); border: 1.5px solid #ddf0c4; min-height: 240px; }
.ri-admin-intro h2, .ri-manager-intro h2 { color: #0e2718; }
.ri-admin-intro .ri-eyebrow, .ri-manager-intro .ri-eyebrow { color: #2d7a3a; }
.ri-admin-intro p, .ri-manager-intro p { color: #7a8c6a; }

/* FORMS */
.ri-form-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 12px; margin-bottom: 14px; }
.ri-form-label { display: grid; gap: 6px; font-size: 13px; font-weight: 700; color: #4d584d; }
.ri-form-input, .ri-form-select { width: 100%; height: 42px; border: 1px solid #ddd8c4; border-radius: 10px; padding: 0 12px; background: #fffdf6; color: #1a3c22; font: inherit; font-size: 14px; outline: none; transition: border-color 140ms, box-shadow 140ms; }
.ri-form-input:focus, .ri-form-select:focus { border-color: #2d7a3a; box-shadow: 0 0 0 3px rgba(45,122,58,0.14); }
.ri-app-output { background: #f0f7e8; color: #1a3c22; border-radius: 16px; border: 1.5px solid #d4eabc; font-size: 13px; font-family: monospace; line-height: 1.5; min-height: 80px; padding: 12px 16px; margin-top: 14px; white-space: pre-wrap; word-break: break-word; overflow: auto; }

/* BUTTONS */
.ri-app-btn-primary { min-height: 44px; border: 0; border-radius: 999px; padding: 0 22px; font: inherit; font-size: 15px; font-weight: 800; cursor: pointer; background: linear-gradient(135deg,#2d7a3a 0%,#4da828 100%); color: white; box-shadow: 0 8px 24px rgba(45,122,58,0.26); transition: transform 140ms, box-shadow 140ms; }
.ri-app-btn-primary:hover { transform: translateY(-1px); box-shadow: 0 12px 32px rgba(45,122,58,0.32); }
.ri-app-btn-secondary { min-height: 44px; border: 1.5px solid #f5c518; border-radius: 999px; padding: 0 22px; font: inherit; font-size: 15px; font-weight: 800; cursor: pointer; background: #fef9c3; color: #5a3a08; transition: all 140ms; }
.ri-app-btn-secondary:hover { background: #f5c518; color: #1a3c22; transform: translateY(-1px); }
.ri-app-danger { min-height: 40px; border: 1.5px solid #f5c5c5; border-radius: 999px; padding: 0 22px; font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; background: #ffe4e4; color: #7a1c1c; transition: all 140ms; }
.ri-app-danger:hover { background: #ffcccc; transform: translateY(-1px); }

/* LINKS */
.ri-link-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
.ri-link-grid a { background: #eaf5d8; color: #1a5c22; border-radius: 12px; padding: 9px 16px; font-weight: 700; font-size: 14px; text-decoration: none; transition: all 140ms; }
.ri-link-grid a:hover { background: #2d7a3a; color: white; transform: translateY(-1px); }

/* RESTAURANT CARDS */
.ri-cards-list { display: grid; gap: 14px; }
.ri-empty-state { min-height: 160px; display: grid; place-items: center; border: 2px dashed #d4eabc; border-radius: 22px; color: #9aaa8a; background: #f8fdf0; text-align: center; padding: 28px; font-size: 15px; }
.ri-restaurant-card { background: white; border: 1.5px solid #e8dfca; border-radius: 22px; overflow: hidden; box-shadow: 0 8px 24px rgba(20,40,20,0.08); transition: transform 160ms, box-shadow 160ms; }
.ri-restaurant-card:hover { transform: translateY(-4px); box-shadow: 0 16px 44px rgba(20,40,20,0.14); }
.ri-restaurant-img { height: 120px; background: linear-gradient(180deg,rgba(15,35,22,0.04),rgba(15,35,22,0.42)), url("https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=800&q=90") center/cover; }
.ri-restaurant-body { padding: 14px; }
.ri-restaurant-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 10px; }
.ri-restaurant-header h4 { font-size: 16px; font-weight: 800; color: #0e2718; margin: 0; }
.ri-score { background: #eaf5d8; color: #1a5c22; border-radius: 999px; padding: 4px 12px; font-weight: 800; font-size: 14px; white-space: nowrap; }
.ri-restaurant-dl { display: grid; grid-template-columns: repeat(2,1fr); gap: 6px 12px; font-size: 13px; margin: 0 0 10px; }
.ri-restaurant-dl dt { color: #9aaa8a; }
.ri-restaurant-dl dd { margin: 0; font-weight: 700; color: #1a3c22; }
.ri-reason { font-size: 13px; color: #2d7a3a; line-height: 1.4; }
.ri-clean-list { margin: 10px 0 0; padding-left: 20px; color: #7a8c6a; line-height: 1.8; font-size: 14px; }

/* RECOMMENDATION EXPERIENCE */
.ri-rec-board { background: #fffdf6; border: 1.5px solid #d8c8ad; border-radius: 4px; padding: 26px; box-shadow: 0 10px 28px rgba(20,40,20,0.06); }
.ri-rec-board h3 { font-family: "Playfair Display", Georgia, serif; font-size: 24px; margin: 0 0 2px; color: #0e2718; }
.ri-rec-section { margin-bottom: 22px; }
.ri-rec-section-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; }
.ri-rec-index { color: #c84c16; font-size: 10px; font-weight: 900; letter-spacing: 0.14em; text-transform: uppercase; }
.ri-rec-title { font-family: "Playfair Display", Georgia, serif; font-size: 18px; font-weight: 800; color: #1a140f; }
.ri-rec-section-sub { color: #b9501d; font-size: 9px; font-weight: 900; letter-spacing: 0.14em; text-transform: uppercase; margin-top: 4px; }
.ri-cuisine-picks { display: flex; gap: 8px; flex-wrap: wrap; }
.ri-cuisine-pill { min-height: 28px; border: 1px solid #ccb89b; border-radius: 999px; background: transparent; color: #5d4732; padding: 0 13px; font-size: 11px; font-weight: 900; letter-spacing: 0.08em; text-transform: uppercase; cursor: pointer; }
.ri-cuisine-pill.active { background: #1a100b; border-color: #1a100b; color: #fffdf6; }
.ri-rec-grid-2 { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 14px; }
.ri-rec-select { width: 100%; height: 38px; border: 1px solid #d8c8ad; background: #fffaf0; color: #1a140f; border-radius: 3px; padding: 0 10px; font: inherit; }
.ri-price-buttons { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 6px; }
.ri-price-btn { height: 40px; border: 0; border-radius: 3px; background: #1a100b; color: #fffdf6; font-weight: 900; cursor: pointer; }
.ri-price-btn.active { outline: 3px solid #c84c16; background: #c84c16; }
.ri-range-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 20px; }
.ri-range-field { display: grid; gap: 8px; color: #1a140f; font-size: 12px; font-weight: 800; }
.ri-range-top { display: flex; justify-content: space-between; color: #c84c16; font-size: 11px; font-weight: 900; }
.ri-range-field input[type="range"] { accent-color: #c84c16; width: 100%; }
.ri-toggle-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 10px; }
.ri-toggle-row { min-height: 42px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #d8c8ad; background: #fffaf0; border-radius: 3px; padding: 0 12px; color: #6e5f50; font-size: 12px; font-weight: 700; }
.ri-switch { width: 34px; height: 18px; position: relative; display: inline-flex; }
.ri-switch input { display: none; }
.ri-switch span { position: absolute; inset: 0; border-radius: 999px; background: #d9ccbd; }
.ri-switch span::after { content: ""; position: absolute; width: 14px; height: 14px; left: 2px; top: 2px; border-radius: 50%; background: white; transition: transform 140ms; }
.ri-switch input:checked + span { background: #c84c16; }
.ri-switch input:checked + span::after { transform: translateX(16px); }
.ri-rec-actions { display: flex; align-items: center; gap: 14px; border-top: 1px solid #d8c8ad; padding-top: 18px; }
.ri-rec-submit { min-height: 42px; border: 0; border-radius: 999px; padding: 0 22px; background: #c84c16; color: white; font-size: 11px; font-weight: 900; letter-spacing: 0.08em; cursor: pointer; text-transform: uppercase; }
.ri-rec-reset { border: 0; background: transparent; color: #6e5f50; font-size: 11px; font-weight: 900; letter-spacing: 0.08em; cursor: pointer; text-transform: uppercase; }
.ri-live-panel { background: #1a100b; color: #fffaf0; border-radius: 3px; padding: 24px; box-shadow: 0 14px 38px rgba(26,16,11,0.18); }
.ri-live-head { color: #f6b327; font-size: 11px; font-weight: 900; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 12px; }
.ri-live-row { display: grid; grid-template-columns: 32px 52px minmax(0,1fr) auto; gap: 12px; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.18); padding: 10px 0; }
.ri-live-rank { color: #d8c8ad; font-size: 12px; font-weight: 900; }
.ri-live-img { width: 48px; height: 48px; border-radius: 10px; object-fit: cover; }
.ri-live-name { font-family: "Playfair Display", Georgia, serif; font-size: 18px; color: white; }
.ri-live-meta { color: #d8c8ad; font-size: 9px; font-weight: 900; letter-spacing: 0.12em; text-transform: uppercase; }
.ri-live-score { background: #d5571f; color: white; border-radius: 999px; padding: 5px 9px; font-size: 11px; font-weight: 900; }
.ri-live-full { width: 100%; height: 36px; margin-top: 16px; border: 1px solid rgba(255,255,255,0.35); border-radius: 999px; background: transparent; color: white; font-size: 11px; font-weight: 900; letter-spacing: 0.08em; cursor: pointer; }

/* TRENDING */
.ri-trending-section { margin: 28px 0 22px; }
.ri-trending-heading { margin-bottom: 18px; }
.ri-trending-heading h2 { font-family: "Playfair Display", Georgia, serif; font-size: clamp(36px,4vw,54px); line-height: 1; margin: 0 0 8px; color: #0e2718; }
.ri-trending-heading p { margin: 0; color: #6f7861; }
.ri-trending-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 22px; }
.ri-trend-card { background: #fffdf6; border: 1.5px solid #d8c8ad; border-radius: 4px; overflow: hidden; box-shadow: 0 10px 30px rgba(20,40,20,0.07); }
.ri-trend-img-wrap { position: relative; height: 220px; overflow: hidden; }
.ri-trend-img-wrap img { width: 100%; height: 100%; object-fit: cover; }
.ri-trend-badges { position: absolute; top: 12px; left: 12px; right: 12px; display: flex; justify-content: space-between; align-items: center; }
.ri-trend-badge { min-height: 24px; border-radius: 999px; background: #fffdf6; color: #1a100b; padding: 0 10px; display: inline-flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 900; text-transform: uppercase; }
.ri-trend-hot { background: #d5571f; color: white; }
.ri-trend-save { width: 28px; height: 28px; border: 0; border-radius: 50%; background: #fffdf6; cursor: pointer; }
.ri-trend-body { padding: 18px; }
.ri-trend-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.ri-trend-body h3 { font-family: "Playfair Display", Georgia, serif; font-size: 24px; margin: 0; color: #1a100b; }
.ri-trend-rating { background: #1a100b; color: #ffd15c; border-radius: 2px; padding: 4px 8px; font-size: 11px; font-weight: 900; }
.ri-trend-cuisine { color: #6e5f50; font-size: 12px; margin: 4px 0 14px; }
.ri-trend-quote { border-left: 2px solid #d5571f; padding-left: 12px; color: #1a100b; font-family: "Playfair Display", Georgia, serif; font-size: 15px; font-style: italic; line-height: 1.35; }
.ri-trend-meta { margin-top: 14px; color: #7a6c5e; font-size: 10px; font-weight: 900; letter-spacing: 0.12em; text-transform: uppercase; line-height: 1.8; }
.ri-trend-footer { border-top: 1px solid #d8c8ad; margin-top: 18px; padding-top: 14px; display: flex; justify-content: space-between; align-items: center; color: #6e5f50; font-size: 12px; }
.ri-trend-view { border: 0; background: transparent; font-weight: 900; cursor: pointer; color: #1a100b; }

/* MANAGER MENU UPLOAD */
.ri-photo-upload { border: 1.5px dashed #d8c8ad; border-radius: 18px; padding: 18px; background: #fffaf0; display: grid; gap: 10px; }
.ri-photo-upload input[type="file"] { font-size: 13px; }
.ri-textarea { min-height: 96px; padding-top: 12px; resize: vertical; }
.ri-empty-dark { color: rgba(255,255,255,0.72); border-color: rgba(255,255,255,0.16); background: rgba(255,255,255,0.06); }

/* RESPONSIVE */
@media (max-width: 1080px) {
  .ri-home-menu { grid-template-columns: auto auto minmax(0,1fr); padding: 0 18px; gap: 12px; }
  .ri-home-brand { min-width: 0; }
  .ri-home-nav { grid-column: 1 / -1; order: 4; justify-content: flex-start; overflow-x: auto; padding-bottom: 10px; }
  .ri-home-actions { justify-self: end; }
  .ri-home-user-pill { display: none; }
  .ri-metric-grid, .ri-feature-strip, .ri-panel-grid, .ri-workspace, .ri-trending-grid, .ri-rec-grid-2, .ri-range-grid, .ri-toggle-grid { grid-template-columns: 1fr; }
  .ri-auth-card { flex-direction: column; }
  .ri-auth-copy { flex: 0 0 auto; min-height: 300px; }
  .ri-auth { position: static; min-height: 100vh; overflow-y: auto; }
  .ri-hero { grid-template-columns: 1fr; }
  .ri-hero-plate { min-height: 220px; clip-path: none; }
}
@media (max-width: 720px) {
  .ri-auth-copy, .ri-auth-forms { padding: 24px; }
  .ri-main { padding: 18px; }
  .ri-home-menu { margin: -18px -18px 18px; min-height: auto; padding: 12px 14px 0; }
  .ri-home-logo { width: 36px; height: 36px; font-size: 20px; }
  .ri-home-name { font-size: 22px; }
  .ri-auth-stats { flex-wrap: wrap; }
  .ri-category-row { overflow-x: auto; flex-wrap: nowrap; }
  .ri-form-grid { grid-template-columns: 1fr; }
  .ri-topbar { grid-template-columns: 1fr; }
  .ri-topbar > :last-child { display: none; }
}
`;

// ============================================================
// View Components
// ============================================================

function ViewDashboard({ onViewJump, importOutput, onImport }) {
  return (
    <div>
      <div className="ri-hero">
        <div className="ri-hero-content">
          <p className="ri-eyebrow">Taste-led recommendations</p>
          <h2>Find the right restaurant with data, ratings &amp; preferences.</h2>
          <p>Combines recommendation logic, rating prediction, location analysis and role-based management in one place.</p>
          <div className="ri-action-row">
            <button className="ri-app-btn-primary" onClick={() => onViewJump("recommendations")}>Get Recommendations</button>
            <button className="ri-app-btn-secondary" onClick={() => onViewJump("location")}>Explore Maps</button>
            <button className="ri-app-btn-secondary" onClick={() => onViewJump("admin")}>Admin Panel</button>
          </div>
        </div>
        <div className="ri-hero-plate" aria-label="Fresh restaurant food preview" />
      </div>

      <div className="ri-category-row">
        {[["🌶️","Indian"],["🍕","Italian"],["🍜","Chinese"],["🥗","Healthy"],["🍣","Japanese"],["🌮","Mexican"],["🍔","American"],["🥘","Continental"]].map(([icon, label]) => (
          <span key={label} className="ri-chip" onClick={() => onViewJump("recommendations")}>
            <span className="ri-chip-icon">{icon}</span>{label}
          </span>
        ))}
      </div>

      <section className="ri-trending-section">
        <div className="ri-trending-heading">
          <p className="ri-eyebrow">Trending now</p>
          <h2>What the city is eating.</h2>
          <p>Ranked by popularity score across reviews, bookings, and recommendation matches.</p>
        </div>
        <div className="ri-trending-grid">
          {[
            ["01", true, "Marcella", "Italian · Mediterranean", "4.9", "A cacio e pepe worth writing home about.", "West Village, New York · 25 min · ₹₹₹", "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=800&q=90"],
            ["02", false, "Sobremesa", "Mexican", "4.8", "Salsa verde so bright it hums.", "Roma Norte, Mexico City · 15 min · ₹₹", "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?auto=format&fit=crop&w=800&q=90"],
            ["03", true, "Le Petit Ours", "French", "4.7", "Steak frites and a natural pét-nat — the trip is made.", "Le Marais, Paris · 40 min · ₹₹₹", "https://images.unsplash.com/photo-1514933651103-005eec06c04b?auto=format&fit=crop&w=800&q=90"],
          ].map(([rank, hot, name, cuisine, rating, quote, meta, image]) => (
            <article className="ri-trend-card" key={name}>
              <div className="ri-trend-img-wrap">
                <img src={image} alt={name} />
                <div className="ri-trend-badges">
                  <span>
                    <span className="ri-trend-badge">#{rank}</span>
                    {hot && <span className="ri-trend-badge ri-trend-hot">Hot</span>}
                  </span>
                  <button className="ri-trend-save" type="button">♡</button>
                </div>
              </div>
              <div className="ri-trend-body">
                <div className="ri-trend-title-row">
                  <h3>{name}</h3>
                  <span className="ri-trend-rating">★ {rating}</span>
                </div>
                <p className="ri-trend-cuisine">{cuisine}</p>
                <p className="ri-trend-quote">"{quote}"</p>
                <p className="ri-trend-meta">{meta}<br />Cost for two · Recommendation ready</p>
                <div className="ri-trend-footer">
                  <span>Trending · Popular</span>
                  <button className="ri-trend-view" type="button" onClick={() => onViewJump("recommendations")}>View ↗</button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      <div className="ri-metric-grid">
        {[
          { icon: "🧩", bg: "#fef9c3", label: "Total Modules",  value: "4",       desc: "Recommendation, rating, location, reporting" },
          { icon: "⚡",  bg: "#e4f5e9", label: "Backend",        value: "FastAPI",  desc: "Connected to PostgreSQL" },
          { icon: "🏪", bg: "#fef0e4", label: "Dataset",         value: "9,551",   desc: "Restaurants in cleaned data" },
          { icon: "🔐", bg: "#e8effe", label: "Access",          value: "3 Roles", desc: "User, manager and admin views" },
        ].map(({ icon, bg, label, value, desc }) => (
          <article key={label} className="ri-metric-card">
            <div className="ri-metric-icon" style={{ background: bg }}>{icon}</div>
            <span className="ri-metric-label">{label}</span>
            <span className="ri-metric-value">{value}</span>
            <p className="ri-metric-desc">{desc}</p>
          </article>
        ))}
      </div>

      <div className="ri-feature-strip">
        {[
          { icon: "🎯", title: "Personal Picks",  desc: "Search by cuisine, city, budget, rating and service preferences to get ranked results." },
          { icon: "🏪", title: "Manager Control", desc: "Managers can update only their assigned restaurant — no other access granted." },
          { icon: "⚙️", title: "Admin Console",   desc: "Admin can import data, create users, add restaurants and assign managers." },
        ].map(({ icon, title, desc }) => (
          <article key={title} className="ri-feature-card">
            <span className="ri-feature-icon">{icon}</span>
            <h3>{title}</h3>
            <p>{desc}</p>
          </article>
        ))}
      </div>

      <div className="ri-panel-grid">
        <article className="ri-panel ri-food-panel">
          <h3>Featured Workflow</h3>
          <div className="ri-module-list">
            <div className="ri-module-item"><strong>Recommend</strong><span>Generate ranked restaurants using live backend scoring.</span></div>
            <div className="ri-module-item"><strong>Analyze</strong><span>Open city, cuisine and map-based analysis outputs.</span></div>
            <div className="ri-module-item"><strong>Operate</strong><span>Let admin and managers maintain restaurant records.</span></div>
          </div>
        </article>
        <article className="ri-panel">
          <h3>Dataset Import</h3>
          <p>Admin can load the cleaned CSV into PostgreSQL before using recommendations.</p>
          <button className="ri-app-btn-primary" style={{ marginTop: 10 }} onClick={onImport}>Import Dataset</button>
          <pre className="ri-app-output">{importOutput}</pre>
        </article>
      </div>
    </div>
  );
}

function ViewRecommendations({ apiBase, userId, currentUser }) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");
  const [selectedCuisines, setSelectedCuisines] = useState(["Italian", "Indian"]);
  const [priceRange, setPriceRange] = useState(2);
  const [minRating, setMinRating] = useState(4);
  const [maxCost, setMaxCost] = useState(400);
  const [minPopularity, setMinPopularity] = useState(0);
  const [topN, setTopN] = useState(6);
  const [onlineDelivery, setOnlineDelivery] = useState(false);
  const [tableBooking, setTableBooking] = useState(false);

  function toggleCuisine(cuisine) {
    setSelectedCuisines((items) => (
      items.includes(cuisine) ? items.filter((item) => item !== cuisine) : [...items, cuisine]
    ));
  }

  function resetPreferences() {
    setSelectedCuisines(["Italian", "Indian"]);
    setPriceRange(2);
    setMinRating(4);
    setMaxCost(400);
    setMinPopularity(0);
    setTopN(6);
    setOnlineDelivery(false);
    setTableBooking(false);
    setResults([]);
    setError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setLoading(true); setResults([]); setError("");
    const payload = {
      user_id: currentUser ? currentUser.user_id : null,
      cuisines: selectedCuisines,
      city: optStr(fd.get("city")),
      price_range: priceRange,
      min_rating: minRating,
      max_cost: maxCost,
      online_delivery: onlineDelivery ? "Yes" : null,
      table_booking: tableBooking ? "Yes" : null,
      cost_category: optStr(fd.get("cost_category")),
      top_n: topN,
      save_history: true,
    };
    try {
      const data = await makeRequest(apiBase, userId, "/recommendations", { method: "POST", body: JSON.stringify(payload) });
      setResults(data.recommendations || []);
    } catch (err) { setError(String(err)); }
    setLoading(false);
  }

  return (
    <div>
      <div className="ri-section-intro ri-image-intro ri-recommendation-intro">
        <div>
          <p className="ri-eyebrow">For users</p>
          <h2>Build a dining shortlist from preferences.</h2>
          <p>Choose cuisine, city, budget, rating and service filters. The backend ranks and explains each match.</p>
        </div>
      </div>
      <div className="ri-workspace">
        <form className="ri-rec-board" onSubmit={handleSubmit}>
          <div className="ri-rec-section">
            <div className="ri-rec-section-head"><span className="ri-rec-index">A</span><span className="ri-rec-title">Cuisines</span></div>
            <div className="ri-rec-section-sub">Pick any you love</div>
            <div className="ri-cuisine-picks">
              {CUISINE_OPTIONS.map((cuisine) => (
                <button className={`ri-cuisine-pill ${selectedCuisines.includes(cuisine) ? "active" : ""}`} key={cuisine} type="button" onClick={() => toggleCuisine(cuisine)}>
                  {cuisine}
                </button>
              ))}
            </div>
          </div>

          <div className="ri-rec-grid-2 ri-rec-section">
            <label>
              <div className="ri-rec-section-head"><span className="ri-rec-index">B</span><span className="ri-rec-title">City</span></div>
              <select className="ri-rec-select" name="city">
                <option value="">Any city</option>
                {CITY_OPTIONS.map((city) => <option key={city}>{city}</option>)}
              </select>
            </label>
            <label>
              <div className="ri-rec-section-head"><span className="ri-rec-index">C</span><span className="ri-rec-title">Cost category</span></div>
              <select className="ri-rec-select" name="cost_category">
                <option value="">Any category</option>
                <option>Low</option>
                <option>Medium</option>
                <option>High</option>
                <option>Premium</option>
              </select>
            </label>
          </div>

          <div className="ri-rec-section">
            <div className="ri-rec-section-head"><span className="ri-rec-index">D</span><span className="ri-rec-title">Price range</span></div>
            <div className="ri-rec-section-sub">₹ = casual, ₹₹₹₹ = luxury</div>
            <div className="ri-price-buttons">
              {[1, 2, 3, 4].map((p) => (
                <button className={`ri-price-btn ${priceRange === p ? "active" : ""}`} type="button" key={p} onClick={() => setPriceRange(p)}>
                  {"₹".repeat(p)}
                </button>
              ))}
            </div>
          </div>

          <div className="ri-range-grid ri-rec-section">
            <label className="ri-range-field">
              <span className="ri-range-top"><span>Minimum rating</span><span>{minRating.toFixed(1)} ★</span></span>
              <input type="range" min="0" max="5" step="0.1" value={minRating} onChange={(e) => setMinRating(Number(e.target.value))} />
            </label>
            <label className="ri-range-field">
              <span className="ri-range-top"><span>Max cost for two</span><span>₹{maxCost}</span></span>
              <input type="range" min="100" max="5000" step="100" value={maxCost} onChange={(e) => setMaxCost(Number(e.target.value))} />
            </label>
            <label className="ri-range-field">
              <span className="ri-range-top"><span>Min popularity</span><span>{minPopularity}</span></span>
              <input type="range" min="0" max="1000" step="25" value={minPopularity} onChange={(e) => setMinPopularity(Number(e.target.value))} />
            </label>
            <label className="ri-range-field">
              <span className="ri-range-top"><span>Top K results</span><span>{topN}</span></span>
              <input type="range" min="3" max="20" step="1" value={topN} onChange={(e) => setTopN(Number(e.target.value))} />
            </label>
          </div>

          <div className="ri-toggle-grid ri-rec-section">
            <label className="ri-toggle-row">
              <span>Online delivery available</span>
              <span className="ri-switch"><input checked={onlineDelivery} onChange={(e) => setOnlineDelivery(e.target.checked)} type="checkbox" /><span /></span>
            </label>
            <label className="ri-toggle-row">
              <span>Table booking available</span>
              <span className="ri-switch"><input checked={tableBooking} onChange={(e) => setTableBooking(e.target.checked)} type="checkbox" /><span /></span>
            </label>
          </div>

          <div className="ri-rec-actions">
            <button className="ri-rec-submit" type="submit">{loading ? "Searching..." : "Show my recommendations ↗"}</button>
            <button className="ri-rec-reset" type="button" onClick={resetPreferences}>Reset</button>
          </div>
        </form>

        <div className="ri-live-panel">
          <div className="ri-live-head">Live match · top {results.length ? Math.min(results.length, topN) : 3}</div>
          {error && <pre className="ri-app-output">{error}</pre>}
          {!error && !loading && results.length === 0 && <div className="ri-empty-state ri-empty-dark">Submit preferences to see ranked matches.</div>}
          {loading && <div className="ri-empty-state ri-empty-dark">Finding restaurants...</div>}
          {results.length > 0 && (
            <div>
              {results.map((r, index) => (
                <article key={`${r.rank}-${r.restaurant_id || r.restaurant_name}`} className="ri-live-row">
                  <span className="ri-live-rank">{String(r.rank || index + 1).padStart(2, "0")}</span>
                  <img className="ri-live-img" alt="" src={MATCH_IMAGES[index % MATCH_IMAGES.length]} />
                  <div>
                    <div className="ri-live-name">{r.restaurant_name}</div>
                    <div className="ri-live-meta">{r.city || "City"} · {r.cuisines || "Cuisine"} · ₹{r.average_cost_inr ?? "Cost"}</div>
                  </div>
                  <span className="ri-live-score">{Math.round(Number(r.score || 0) * 100)}%</span>
                </article>
              ))}
              <button className="ri-live-full" type="button">See full list →</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
function ViewRating() {
  return (
    <div>
      <div className="ri-section-intro ri-image-intro ri-rating-intro">
        <div>
          <p className="ri-eyebrow">Model reports</p>
          <h2>Review rating prediction outputs.</h2>
          <p>Open saved CatBoost and XGBoost metrics, feature importance and comparison reports.</p>
        </div>
      </div>
      <div className="ri-panel-grid">
        <article className="ri-panel">
          <h3>Rating Prediction Module</h3>
          <p>Presents trained CatBoost/XGBoost rating models and saved metrics.</p>
          <div className="ri-link-grid">
            <a href="../ml/rating/results/rating_model_engineered_results/final_metrics_toggle.html" target="_blank">Engineered Metrics</a>
            <a href="../ml/rating/results/rating_model_engineered_results/feature_importance_toggle.html" target="_blank">Feature Importance</a>
            <a href="../ml/rating/results/rating_model_xgboost_engineered_results/final_metrics_toggle.html" target="_blank">XGBoost Metrics</a>
            <a href="../ml/rating/results/rating_model_without_votes_results/final_metrics_toggle.html" target="_blank">Without Votes Metrics</a>
          </div>
        </article>
        <article className="ri-panel">
          <h3>What To Show Here</h3>
          <ul className="ri-clean-list">
            <li>Best model name</li><li>MAE, RMSE, R²</li>
            <li>Feature importance</li><li>Comparison between model versions</li>
          </ul>
        </article>
      </div>
    </div>
  );
}

function ViewLocation() {
  return (
    <div>
      <div className="ri-section-intro ri-image-intro ri-location-intro">
        <div>
          <p className="ri-eyebrow">Geographical analysis</p>
          <h2>Explore restaurant concentration by place.</h2>
          <p>Open map visualizations and generated statistics for cities, localities, ratings, cuisines and price ranges.</p>
        </div>
      </div>
      <article className="ri-panel">
        <h3>Location Analysis</h3>
        <p>Open the generated maps and city analysis graphs. Marker maps include legends for rating levels, and heatmaps show restaurant density.</p>
        <div className="ri-link-grid">
          <a href="../analysis/location_results/restaurant_location_marker_map.html" target="_blank">Restaurant Marker Map</a>
          <a href="../analysis/location_results/restaurant_density_heatmap.html" target="_blank">Density Heatmap</a>
          <a href="../analysis/location_results/top_cities_by_restaurant_count.html" target="_blank">Top Cities</a>
          <a href="../analysis/location_results/city_rating_vs_cost.html" target="_blank">Rating vs Cost</a>
          <a href="../analysis/location_results/top_cuisines_overall.html" target="_blank">Top Cuisines</a>
          <a href="../analysis/location_results/location_analysis_report.md" target="_blank">Insights Report</a>
        </div>
      </article>
    </div>
  );
}

function ViewAdmin({ apiBase, userId }) {
  const [userOut,   setUserOut]   = useState("User creation response will appear here.");
  const [usersOut,  setUsersOut]  = useState("Saved users will appear here.");
  const [restOut,   setRestOut]   = useState("Restaurant creation response will appear here.");
  const [assignOut, setAssignOut] = useState("Manager assignment response will appear here.");

  async function handleUser(e) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      const d = await makeRequest(apiBase, userId, "/users", {
        method: "POST",
        body: JSON.stringify({ name: fd.get("name"), email: fd.get("email"), password: fd.get("password"), role: fd.get("role") || "user", managed_restaurant_id: optNum(fd.get("managed_restaurant_id")) }),
      });
      setUserOut(d.user_id ? `Created ${d.role} account with user_id: ${d.user_id}\n\n${JSON.stringify(d, null, 2)}` : JSON.stringify(d, null, 2));
    } catch (err) { setUserOut(String(err)); }
  }

  async function loadUsers() {
    setUsersOut("Loading users from backend…");
    try {
      const d = await makeRequest(apiBase, userId, "/users");
      setUsersOut(JSON.stringify(d, null, 2));
    } catch (err) { setUsersOut(String(err)); }
  }

  async function handleRest(e) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setRestOut("Creating restaurant…");
    try {
      const cuisines = optStr(fd.get("cuisines"));
      const d = await makeRequest(apiBase, userId, "/admin/restaurants", {
        method: "POST",
        body: JSON.stringify({
          restaurant_name: fd.get("restaurant_name"), city: optStr(fd.get("city")), address: optStr(fd.get("address")), locality: optStr(fd.get("locality")),
          cuisines: cuisines ? cuisines.split(",").map(s => s.trim()).filter(Boolean) : [],
          average_cost_inr: optNum(fd.get("average_cost_inr")), price_range: optNum(fd.get("price_range")),
          aggregate_rating: optNum(fd.get("aggregate_rating")), votes: optNum(fd.get("votes")),
          has_table_booking: optStr(fd.get("has_table_booking")), has_online_delivery: optStr(fd.get("has_online_delivery")), is_delivering_now: optStr(fd.get("is_delivering_now")),
        }),
      });
      setRestOut(JSON.stringify(d, null, 2));
    } catch (err) { setRestOut(String(err)); }
  }

  async function handleAssign(e) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setAssignOut("Assigning manager…");
    try {
      const d = await makeRequest(apiBase, userId, "/admin/assign-manager", { method: "POST", body: JSON.stringify({ manager_user_id: optNum(fd.get("manager_user_id")), restaurant_id: optNum(fd.get("restaurant_id")) }) });
      setAssignOut(JSON.stringify(d, null, 2));
    } catch (err) { setAssignOut(String(err)); }
  }

  return (
    <div>
      <div className="ri-section-intro ri-admin-intro">
        <div>
          <p className="ri-eyebrow">Admin only</p>
          <h2>Manage platform users and restaurant records.</h2>
          <p>Only one admin is allowed by the backend. Admin can create managers/users, import data, add restaurants and assign managers.</p>
        </div>
      </div>
      <div className="ri-workspace">
        <form className="ri-form-panel" onSubmit={handleUser}>
          <h3>Create User / Admin Record</h3>
          <p className="ri-muted">Admin can create user or manager accounts. A second admin is blocked by the backend.</p>
          <div className="ri-form-grid">
            <label className="ri-form-label">Name<input className="ri-form-input" name="name" required placeholder="Admin Name" /></label>
            <label className="ri-form-label">Email<input className="ri-form-input" name="email" type="email" required placeholder="user@example.com" /></label>
            <label className="ri-form-label">Password<input className="ri-form-input" name="password" type="password" required minLength={6} placeholder="Min 6 characters" /></label>
            <label className="ri-form-label">Role<select className="ri-form-select" name="role"><option>user</option><option>admin</option><option>manager</option></select></label>
            <label className="ri-form-label">Managed Restaurant ID<input className="ri-form-input" name="managed_restaurant_id" type="number" placeholder="Only for manager" /></label>
          </div>
          <button className="ri-app-btn-primary" type="submit">Create User</button>
          <pre className="ri-app-output">{userOut}</pre>
        </form>

        <article className="ri-panel">
          <h3>Users In Backend</h3>
          <p>Use an admin ID in the sidebar, then refresh to confirm users are saved in PostgreSQL.</p>
          <button className="ri-app-btn-secondary" style={{ marginTop: 8 }} onClick={loadUsers}>Refresh Users</button>
          <pre className="ri-app-output">{usersOut}</pre>
        </article>

        <form className="ri-form-panel" onSubmit={handleRest}>
          <h3>Add Restaurant</h3>
          <div className="ri-form-grid">
            <label className="ri-form-label">Restaurant Name<input className="ri-form-input" name="restaurant_name" required placeholder="Pizza Zone" /></label>
            <label className="ri-form-label">City<input className="ri-form-input" name="city" placeholder="New Delhi" /></label>
            <label className="ri-form-label">Address<input className="ri-form-input" name="address" placeholder="Street address" /></label>
            <label className="ri-form-label">Locality<input className="ri-form-input" name="locality" placeholder="Locality" /></label>
            <label className="ri-form-label">Cuisines<input className="ri-form-input" name="cuisines" placeholder="Italian, Pizza" /></label>
            <label className="ri-form-label">Price Range<select className="ri-form-select" name="price_range"><option value="">Any</option><option>1</option><option>2</option><option>3</option><option>4</option></select></label>
            <label className="ri-form-label">Avg Cost INR<input className="ri-form-input" name="average_cost_inr" type="number" min="0" placeholder="800" /></label>
            <label className="ri-form-label">Rating<input className="ri-form-input" name="aggregate_rating" type="number" min="0" max="5" step="0.1" placeholder="4.1" /></label>
            <label className="ri-form-label">Votes<input className="ri-form-input" name="votes" type="number" min="0" placeholder="120" /></label>
            <label className="ri-form-label">Online Delivery<select className="ri-form-select" name="has_online_delivery"><option value="">Unknown</option><option>Yes</option><option>No</option></select></label>
            <label className="ri-form-label">Table Booking<select className="ri-form-select" name="has_table_booking"><option value="">Unknown</option><option>Yes</option><option>No</option></select></label>
            <label className="ri-form-label">Delivering Now<select className="ri-form-select" name="is_delivering_now"><option value="">Unknown</option><option>Yes</option><option>No</option></select></label>
          </div>
          <button className="ri-app-btn-primary" type="submit">Add Restaurant</button>
          <pre className="ri-app-output">{restOut}</pre>
        </form>

        <form className="ri-form-panel" onSubmit={handleAssign}>
          <h3>Assign Manager</h3>
          <div className="ri-form-grid">
            <label className="ri-form-label">Manager User ID<input className="ri-form-input" name="manager_user_id" type="number" required placeholder="2" /></label>
            <label className="ri-form-label">Restaurant ID<input className="ri-form-input" name="restaurant_id" type="number" required placeholder="10001" /></label>
          </div>
          <button className="ri-app-btn-secondary" type="submit">Assign Manager</button>
          <pre className="ri-app-output">{assignOut}</pre>
        </form>
      </div>
    </div>
  );
}

function ViewManager({ apiBase, userId }) {
  const [out, setOut] = useState("Restaurant update response will appear here.");
  const [menuOut, setMenuOut] = useState("Menu item upload response will appear here.");

  async function handleSubmit(e) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const restId = optNum(fd.get("restaurant_id"));
    setOut("Updating restaurant…");
    try {
      const cuisines = optStr(fd.get("cuisines"));
      const d = await makeRequest(apiBase, userId, `/manager/restaurants/${restId}`, {
        method: "PATCH",
        body: JSON.stringify({
          restaurant_name: fd.get("restaurant_name"), city: optStr(fd.get("city")), address: optStr(fd.get("address")), locality: optStr(fd.get("locality")),
          cuisines: cuisines ? cuisines.split(",").map(s => s.trim()).filter(Boolean) : [],
          average_cost_inr: optNum(fd.get("average_cost_inr")), price_range: optNum(fd.get("price_range")),
          aggregate_rating: optNum(fd.get("aggregate_rating")), votes: optNum(fd.get("votes")),
          has_table_booking: optStr(fd.get("has_table_booking")), has_online_delivery: optStr(fd.get("has_online_delivery")),
        }),
      });
      setOut(JSON.stringify(d, null, 2));
    } catch (err) { setOut(String(err)); }
  }

  async function handleMenuSubmit(e) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const restId = optNum(fd.get("restaurant_id"));
    const body = new FormData();
    body.append("item_name", fd.get("item_name"));
    body.append("description", fd.get("description") || "");
    body.append("category", fd.get("category") || "");
    if (fd.get("price_inr")) body.append("price_inr", fd.get("price_inr"));
    body.append("is_available", fd.get("is_available") ? "true" : "false");
    const photo = fd.get("photo");
    if (photo && photo.size) body.append("photo", photo);

    setMenuOut("Uploading menu item...");
    try {
      const d = await makeRequest(apiBase, userId, `/manager/restaurants/${restId}/menu-items`, { method: "POST", body });
      setMenuOut(JSON.stringify(d, null, 2));
      e.currentTarget.reset();
    } catch (err) { setMenuOut(String(err)); }
  }

  return (
    <div>
      <div className="ri-section-intro ri-manager-intro">
        <div>
          <p className="ri-eyebrow">Manager workspace</p>
          <h2>Update assigned restaurant details.</h2>
          <p>Managers can only update the restaurant assigned by an admin. Admins can update any restaurant.</p>
        </div>
      </div>
      <div className="ri-workspace">
        <form className="ri-form-panel" onSubmit={handleSubmit}>
          <h3>Edit Assigned Restaurant</h3>
          <p className="ri-muted">Managers can only update their assigned restaurant. Admins can update any.</p>
          <div className="ri-form-grid">
            <label className="ri-form-label">Restaurant ID<input className="ri-form-input" name="restaurant_id" type="number" required placeholder="Assigned restaurant id" /></label>
            <label className="ri-form-label">Name<input className="ri-form-input" name="restaurant_name" required placeholder="Updated name" /></label>
            <label className="ri-form-label">City<input className="ri-form-input" name="city" placeholder="City" /></label>
            <label className="ri-form-label">Address<input className="ri-form-input" name="address" placeholder="Address" /></label>
            <label className="ri-form-label">Locality<input className="ri-form-input" name="locality" placeholder="Locality" /></label>
            <label className="ri-form-label">Cuisines<input className="ri-form-input" name="cuisines" placeholder="Italian, Pizza" /></label>
            <label className="ri-form-label">Price Range<select className="ri-form-select" name="price_range"><option value="">No change</option><option>1</option><option>2</option><option>3</option><option>4</option></select></label>
            <label className="ri-form-label">Avg Cost INR<input className="ri-form-input" name="average_cost_inr" type="number" min="0" /></label>
            <label className="ri-form-label">Rating<input className="ri-form-input" name="aggregate_rating" type="number" min="0" max="5" step="0.1" /></label>
            <label className="ri-form-label">Votes<input className="ri-form-input" name="votes" type="number" min="0" /></label>
            <label className="ri-form-label">Online Delivery<select className="ri-form-select" name="has_online_delivery"><option value="">No change</option><option>Yes</option><option>No</option></select></label>
            <label className="ri-form-label">Table Booking<select className="ri-form-select" name="has_table_booking"><option value="">No change</option><option>Yes</option><option>No</option></select></label>
          </div>
          <button className="ri-app-btn-primary" type="submit">Update Restaurant</button>
          <pre className="ri-app-output">{out}</pre>
        </form>
        <article className="ri-panel">
          <h3>Manager Access</h3>
          <div className="ri-module-list">
            <div className="ri-module-item"><strong>Assigned Restaurant</strong><span>Admin chooses which restaurant a manager can edit.</span></div>
            <div className="ri-module-item"><strong>Restaurant Details</strong><span>Manager can update cuisine, city, delivery, booking and pricing fields.</span></div>
            <div className="ri-module-item"><strong>Protected Endpoint</strong><span>Backend blocks managers from editing other restaurants.</span></div>
          </div>
        </article>
        <form className="ri-form-panel" onSubmit={handleMenuSubmit}>
          <h3>Add Menu Item With Photo</h3>
          <p className="ri-muted">Use this when a manager adds a new dish or updates the restaurant menu.</p>
          <div className="ri-form-grid">
            <label className="ri-form-label">Restaurant ID<input className="ri-form-input" name="restaurant_id" type="number" required placeholder="Assigned restaurant id" /></label>
            <label className="ri-form-label">Item Name<input className="ri-form-input" name="item_name" required placeholder="Paneer Tikka Bowl" /></label>
            <label className="ri-form-label">Category<input className="ri-form-input" name="category" placeholder="Starter, Main Course, Dessert" /></label>
            <label className="ri-form-label">Price INR<input className="ri-form-input" name="price_inr" type="number" min="0" step="0.01" placeholder="299" /></label>
            <label className="ri-form-label">Description<textarea className="ri-form-input ri-textarea" name="description" placeholder="Short menu description" /></label>
            <label className="ri-form-label ri-photo-upload">Dish Photo<input name="photo" type="file" accept="image/*" /></label>
            <label className="ri-form-label"><span><input name="is_available" type="checkbox" defaultChecked /> Available now</span></label>
          </div>
          <button className="ri-app-btn-primary" type="submit">Add Menu Item</button>
          <pre className="ri-app-output">{menuOut}</pre>
        </form>
      </div>
    </div>
  );
}

function ViewReports() {
  return (
    <div>
      <div className="ri-section-intro ri-image-intro ri-report-intro">
        <div>
          <p className="ri-eyebrow">Saved outputs</p>
          <h2>Open project reports and generated artifacts.</h2>
          <p>Use this section during presentation to show model metrics, analysis CSVs and location insights.</p>
        </div>
      </div>
      <article className="ri-panel">
        <h3>Saved Reports</h3>
        <div className="ri-link-grid">
          <a href="../ml/rating/results/rating_model_engineered_results/training_report.txt" target="_blank">Rating Training Report</a>
          <a href="../analysis/location_results/location_analysis_report.md" target="_blank">Location Report</a>
          <a href="../ml/rating/results/rating_model_engineered_results/final_metrics.csv" target="_blank">Rating Metrics CSV</a>
          <a href="../analysis/location_results/city_statistics.csv" target="_blank">City Statistics CSV</a>
        </div>
      </article>
    </div>
  );
}

// ============================================================
// Root App
// ============================================================
export default function App() {
  const [currentUser,   setCurrentUser]   = useState(null);
  const [currentView,   setCurrentView]   = useState("dashboard");
  const [authTab,       setAuthTab]       = useState("login");
  const [apiBase,       setApiBase]       = useState(DEFAULT_API_BASE);
  const [authApiBase,   setAuthApiBase]   = useState(DEFAULT_API_BASE);
  const [sidebarOpen,   setSidebarOpen]   = useState(false);
  const [authOutput,    setAuthOutput]    = useState("Create the first admin account once. After that, the backend blocks any second admin account.");
  const [apiStatusText, setApiStatusText] = useState("Not checked");
  const [apiStatusCls,  setApiStatusCls]  = useState("ri-status-muted");
  const [importOutput,  setImportOutput]  = useState("Dataset import response will appear here.");

  const userId = currentUser ? String(currentUser.user_id) : "";

  function setView(v) {
    const item = NAV_ITEMS.find(n => n.view === v);
    if (item?.roles && currentUser && !item.roles.includes(currentUser.role)) return;
    setCurrentView(v);
    setSidebarOpen(false);
  }

  function isNavVisible(item) {
    if (!item.roles) return true;
    if (!currentUser) return false;
    return item.roles.includes(currentUser.role);
  }

  async function handleLogin(e) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setApiBase(authApiBase);
    setAuthOutput("Logging in…");
    try {
      const user = await makeRequest(authApiBase, "", "/auth/login", { method: "POST", body: JSON.stringify({ email: fd.get("email"), password: fd.get("password") }) });
      setAuthOutput(`Logged in as ${user.name} (${user.role})`);
      setCurrentUser(user);
    } catch (err) { setAuthOutput(String(err)); }
  }

  async function handleRegister(e) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setApiBase(authApiBase);
    setAuthOutput("Creating account…");
    try {
      const user = await makeRequest(authApiBase, "", "/auth/register", {
        method: "POST",
        body: JSON.stringify({ name: fd.get("name"), email: fd.get("email"), password: fd.get("password"), role: fd.get("role") || "user", managed_restaurant_id: optNum(fd.get("managed_restaurant_id")) }),
      });
      setAuthOutput(`Created and logged in as ${user.name} (${user.role}), user_id: ${user.user_id}`);
      setCurrentUser(user);
    } catch (err) { setAuthOutput(String(err)); }
  }

  async function handleCheckApi() {
    setApiStatusText("Checking…"); setApiStatusCls("ri-status-muted");
    try {
      const d = await makeRequest(apiBase, userId, "/health");
      setApiStatusText(`Connected: ${d.status}`);
      setApiStatusCls("ri-status-ok");
    } catch { setApiStatusText("API not reachable"); setApiStatusCls("ri-status-bad"); }
  }

  async function handleImport() {
    setImportOutput("Importing Dataset/cleaned_dataset.csv…");
    try {
      const d = await makeRequest(apiBase, userId, "/restaurants/import", { method: "POST" });
      setImportOutput(JSON.stringify(d, null, 2));
    } catch (err) { setImportOutput(String(err)); }
  }

  return (
    <div className="ri-body">
      <style>{APP_CSS}</style>

      {/* AUTH SCREEN */}
      {!currentUser && (
        <div className="ri-auth">
          <div className="ri-auth-card">
            {/* LEFT — vegetables image + green overlay */}
            <div
              className="ri-auth-copy"
              style={{ backgroundImage: `linear-gradient(160deg,rgba(34,88,38,0.82) 0%,rgba(52,112,46,0.74) 50%,rgba(72,130,54,0.60) 100%),url(${vegetablesImg})` }}
            >
              <div className="ri-brand">
                <div className="ri-brand-mark"><UtensilsCrossed size={18} strokeWidth={2} /></div>
                <h1>Restaurant Intelligence</h1>
              </div>
              <div className="ri-auth-headline">
                <h2>Taste the data behind every great restaurant.</h2>
                <p className="ri-lead">Recommendations, rating prediction, and location analytics — all served fresh from your own FastAPI backend.</p>
              </div>
              <div className="ri-auth-stats">
                <span><strong>9,551</strong>restaurants</span>
                <span><strong>4</strong>intelligence modules</span>
              </div>
            </div>

            {/* RIGHT — forms */}
            <div className="ri-auth-forms">
              <div className="ri-auth-heading">
                <h2>{authTab === "login" ? "Sign in" : "Register"}</h2>
                <p>{authTab === "login" ? "Create the first admin account once. After that, user and manager accounts can be registered." : "Create user and manager accounts. Only one admin account is allowed."}</p>
              </div>

              <div className="ri-auth-switch">
                <button className={`ri-auth-tab${authTab === "login" ? " active" : ""}`} onClick={() => setAuthTab("login")} type="button">
                  <User size={15} strokeWidth={2} />Login
                </button>
                <button className={`ri-auth-tab${authTab === "register" ? " active" : ""}`} onClick={() => setAuthTab("register")} type="button">
                  <UserPlus size={15} strokeWidth={2} />Register
                </button>
              </div>

              {authTab === "login" && (
                <form className="ri-form" onSubmit={handleLogin}>
                  <label className="ri-label">Email<input className="ri-input" name="email" type="email" required placeholder="admin@example.com" /></label>
                  <label className="ri-label">Password<input className="ri-input" name="password" type="password" required placeholder="Password" /></label>
                  <button className="ri-btn-primary" type="submit">Sign in</button>
                  <label className="ri-api-label">API Base URL<input className="ri-input" value={authApiBase} onChange={e => setAuthApiBase(e.target.value)} /></label>
                </form>
              )}

              {authTab === "register" && (
                <form className="ri-form" onSubmit={handleRegister}>
                  <label className="ri-label">Name<input className="ri-input" name="name" required placeholder="Your name" /></label>
                  <label className="ri-label">Email<input className="ri-input" name="email" type="email" required placeholder="you@example.com" /></label>
                  <label className="ri-label">Password<input className="ri-input" name="password" type="password" required minLength={6} placeholder="Minimum 6 characters" /></label>
                  <label className="ri-label">Role<select className="ri-select" name="role"><option>user</option><option>manager</option><option>admin</option></select></label>
                  <label className="ri-label">Managed Restaurant ID<input className="ri-input" name="managed_restaurant_id" type="number" placeholder="Only for manager" /></label>
                  <button className="ri-btn-secondary" type="submit">Register</button>
                  <label className="ri-api-label">API Base URL<input className="ri-input" value={authApiBase} onChange={e => setAuthApiBase(e.target.value)} /></label>
                </form>
              )}

              <pre className="ri-output">{authOutput}</pre>
            </div>
          </div>
        </div>
      )}

      {/* APP SHELL */}
      {currentUser && (
        <div className={`ri-shell${sidebarOpen ? " sidebar-open" : ""}`}>
          {sidebarOpen && <div className="ri-overlay" onClick={() => setSidebarOpen(false)} />}

          <aside className="ri-sidebar">
            <div className="ri-brand">
              <div className="ri-brand-mark" />
              <div>
                <h1>Restaurant Intelligence</h1>
                <p>Analytics &amp; recommendation console</p>
              </div>
            </div>
            <nav className="ri-nav">
              {NAV_ITEMS.filter(isNavVisible).map(item => (
                <button key={item.view} className={`ri-nav-item${currentView === item.view ? " active" : ""}`} onClick={() => setView(item.view)}>
                  <span className="ri-nav-icon">{item.icon}</span>{item.label}
                </button>
              ))}
            </nav>
            <div className="ri-api-box">
              <span className="ri-api-box-label">API Base URL</span>
              <input className="ri-input" value={apiBase} onChange={e => setApiBase(e.target.value)} />
              <span className="ri-api-box-label">Logged-in user ID</span>
              <input className="ri-input" value={userId} readOnly placeholder="Admin / manager / user id" />
              <p className="ri-session">{currentUser.name} ({currentUser.role})</p>
              <button className="ri-app-btn-secondary" style={{ width: "100%" }} onClick={handleCheckApi}>Check API</button>
              <button className="ri-app-danger" style={{ width: "100%" }} onClick={() => { setCurrentUser(null); setCurrentView("dashboard"); }}>Logout</button>
              <p className={`ri-session ${apiStatusCls}`}>{apiStatusText}</p>
            </div>
          </aside>

          <main className="ri-main">
            <header className="ri-home-menu">
              <div className="ri-home-brand">
                <button className="ri-menu-btn" onClick={() => setSidebarOpen(s => !s)} aria-label="Open menu">
                  <span /><span /><span />
                </button>
                <span className="ri-home-logo">♨</span>
                <span className="ri-home-name">Ticrou</span>
              </div>
              <nav className="ri-home-nav">
                {TOP_MENU_ITEMS.filter(isNavVisible).map(item => (
                  <button
                    key={item.view}
                    className={`ri-home-nav-item${currentView === item.view ? " active" : ""}`}
                    onClick={() => setView(item.view)}
                    type="button"
                  >
                    {item.label}
                  </button>
                ))}
              </nav>
              <div className="ri-home-actions">
                <button className="ri-home-icon-btn" type="button" onClick={handleCheckApi} aria-label="Check API">⌕</button>
                <span className="ri-home-user-pill"><span className="ri-home-role-dot" />{currentUser.role}</span>
              </div>
            </header>

            <div className="ri-topbar">
              <div>
                <p className="ri-eyebrow">Restaurant intelligence workspace</p>
                <h1 className="ri-page-title">{VIEW_META[currentView][0]}</h1>
                <p className="ri-page-subtitle">{VIEW_META[currentView][1]}</p>
              </div>
              {currentUser.role === "admin" && (
                <button className="ri-app-btn-primary" onClick={handleImport}>Import Dataset</button>
              )}
            </div>

            {currentView === "dashboard"       && <ViewDashboard onViewJump={setView} importOutput={importOutput} onImport={handleImport} />}
            {currentView === "recommendations" && <ViewRecommendations apiBase={apiBase} userId={userId} currentUser={currentUser} />}
            {currentView === "rating"          && <ViewRating />}
            {currentView === "location"        && <ViewLocation />}
            {currentView === "admin"           && <ViewAdmin apiBase={apiBase} userId={userId} />}
            {currentView === "manager"         && <ViewManager apiBase={apiBase} userId={userId} />}
            {currentView === "reports"         && <ViewReports />}
          </main>
        </div>
      )}
    </div>
  );
}

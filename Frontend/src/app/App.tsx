import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area,
} from "recharts";
import {
  Star, MapPin, LogOut, ChefHat, Home, Search, Map, TrendingUp,
  FileText, Shield, BarChart2, Compass, Upload, Edit2, Download,
  CheckCircle, AlertCircle, Info, Settings, Bell, ChevronDown,
  Utensils, ArrowUpRight, Menu, X,
} from "lucide-react";

type Role = "user" | "manager" | "admin";
interface UserT { id: number; name: string; email: string; role: Role; managed_restaurant_id?: number | null; }
interface AuthState { user: UserT; token: string | null; apiBaseUrl: string; }
interface Restaurant { id: number; name: string; city: string; locality: string; cuisine: string; avg_cost: number; price_range: number; rating: number; votes: number; online_delivery: boolean; table_booking: boolean; image: string; match_score?: number; }
interface AppMetadata { restaurant_count: number; cuisine_count: number; city_count: number; admin_added_count: number; average_rating: number; cuisines?: string[]; cities?: string[]; cost_categories?: string[]; }

const formatCount = (value: number) => Number(value || 0).toLocaleString("en-IN");

function toAppUser(data: any): UserT {
  return {
    id: Number(data.user_id ?? data.id),
    name: data.name,
    email: data.email,
    role: data.role,
    managed_restaurant_id: data.managed_restaurant_id ?? null,
  };
}

function toRestaurant(data: any, index = 0): Restaurant {
  const score = Number(data.score ?? data.match_score ?? 0);
  const matchScore = score <= 1 ? Math.round(score * 100) : Math.round(score);
  return {
    id: Number(data.restaurant_id ?? data.id ?? index + 1),
    name: data.restaurant_name ?? data.name ?? "Restaurant",
    city: data.city ?? "",
    locality: data.locality ?? "",
    cuisine: Array.isArray(data.cuisines) ? data.cuisines.join(", ") : (data.cuisines ?? data.cuisine ?? ""),
    avg_cost: Number(data.average_cost_inr ?? data.avg_cost ?? 0),
    price_range: Number(data.price_range ?? 0),
    rating: Number(data.aggregate_rating ?? data.rating ?? 0),
    votes: Number(data.votes ?? 0),
    online_delivery: String(data.has_online_delivery ?? "").toLowerCase() === "yes" || data.online_delivery === true,
    table_booking: String(data.has_table_booking ?? "").toLowerCase() === "yes" || data.table_booking === true,
    image: MOCK_RESTAURANTS[index % MOCK_RESTAURANTS.length]?.image ?? "1565299585323-38d6b0865b47",
    match_score: matchScore,
  };
}

function createApi(baseUrl: string, userId: string | null) {
  const req = async (method: string, path: string, body?: unknown) => {
    const isFormData = body instanceof FormData;
    const headers: Record<string, string> = {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(userId ? { "X-User-Id": String(userId) } : {}),
    };
    const cleanBaseUrl = (baseUrl || "http://127.0.0.1:8000").trim().replace(/\/+$/, "");
    const requestInit = { method, headers, ...(body ? { body: isFormData ? body as BodyInit : JSON.stringify(body) } : {}) };
    let res: Response;
    try {
      res = await fetch(`${cleanBaseUrl}${path}`, requestInit);
    } catch (error) {
      if (!cleanBaseUrl.includes("localhost")) throw error;
      res = await fetch(`${cleanBaseUrl.replace("localhost", "127.0.0.1")}${path}`, requestInit);
    }
    const text = await res.text();
    let data: any = {};
    try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
    if (!res.ok) throw new Error(data.detail || data.raw || JSON.stringify(data));
    return data;
  };
  return {
    get: (p: string) => req("GET", p),
    post: (p: string, b?: unknown) => req("POST", p, b),
    patch: (p: string, b: unknown) => req("PATCH", p, b),
    put: (p: string, b: unknown) => req("PUT", p, b),
    delete: (p: string) => req("DELETE", p),
  };
}

const MOCK_RESTAURANTS: Restaurant[] = [
  { id: 1, name: "Spice Garden", city: "Mumbai", locality: "Bandra", cuisine: "Indian", avg_cost: 800, price_range: 2, rating: 4.3, votes: 2341, online_delivery: true, table_booking: true, image: "1585937421612-70a008356fbe" },
  { id: 2, name: "Tokyo Ramen Co.", city: "Delhi", locality: "Connaught Place", cuisine: "Japanese", avg_cost: 1200, price_range: 3, rating: 4.6, votes: 1876, online_delivery: true, table_booking: false, image: "1569050467447-ce54b3bbc37d" },
  { id: 3, name: "La Maison", city: "Bangalore", locality: "Koramangala", cuisine: "French", avg_cost: 2500, price_range: 4, rating: 4.8, votes: 987, online_delivery: false, table_booking: true, image: "1414235077428-338989a2e8c0" },
  { id: 4, name: "Taco Fiesta", city: "Pune", locality: "Kalyani Nagar", cuisine: "Mexican", avg_cost: 600, price_range: 2, rating: 4.1, votes: 3214, online_delivery: true, table_booking: false, image: "1565299585323-38d6b0865b47" },
];
const FALLBACK_CUISINES = ["Italian", "Japanese", "French", "Mexican", "Indian", "Thai", "Chinese", "American", "Mediterranean", "Korean"];
const CITIES = ["Mumbai", "Delhi", "Bangalore", "Pune", "Chennai", "Hyderabad", "Kolkata", "Ahmedabad"];
const PRICE_LEVELS = [
  { value: 1, label: "Affordable" },
  { value: 2, label: "Casual" },
  { value: 3, label: "Premium" },
  { value: 4, label: "Luxury" },
];

const BG_BLOBS = [
  { top: "-8%", right: "-4%", size: 500, img: "1414235077428-338989a2e8c0", delay: 0 },
  { top: "35%", left: "-6%", size: 360, img: "1565299585323-38d6b0865b47", delay: 1.5 },
  { bottom: "-4%", right: "12%", size: 400, img: "1504674900247-0877df9cc836", delay: 0.8 },
];

function AnimatedBackground() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
      <div className="absolute inset-0 bg-gradient-to-br from-[#FFF8EF] via-[#FFF1DC] to-[#FFE0B2]" />
      {BG_BLOBS.map((b, i) => (
        <motion.div key={i} className="absolute rounded-full overflow-hidden"
          style={{ top: (b as any).top, left: (b as any).left, right: (b as any).right, bottom: (b as any).bottom, width: b.size, height: b.size }}
          animate={{ y: [0, -18, 0], scale: [1, 1.03, 1] }}
          transition={{ duration: 8 + i * 2, repeat: Infinity, ease: "easeInOut", delay: b.delay }}>
          <img src={`https://images.unsplash.com/photo-${b.img}?w=600&h=600&fit=crop&auto=format`} alt="" className="w-full h-full object-cover opacity-[0.18] blur-2xl" />
        </motion.div>
      ))}
      <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse at 80% 0%, rgba(196,98,29,0.06) 0%, transparent 60%), radial-gradient(ellipse at 20% 100%, rgba(45,80,22,0.05) 0%, transparent 60%)" }} />
    </div>
  );
}

function GlassCard({ children, className = "", hover = true }: { children: React.ReactNode; className?: string; hover?: boolean }) {
  return (
    <motion.div whileHover={hover ? { y: -3, boxShadow: "0 20px 50px rgba(196,98,29,0.13)" } : undefined}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      className={`bg-white/55 backdrop-blur-xl border border-white/70 rounded-2xl shadow-[0_8px_32px_rgba(196,98,29,0.07)] ${className}`}>
      {children}
    </motion.div>
  );
}

function Toast({ message, type, onClose }: { message: string; type: "success" | "error" | "info"; onClose: () => void }) {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t); }, [onClose]);
  const bg = { success: "bg-[#2D5016]", error: "bg-red-500", info: "bg-[#C4621D]" }[type];
  const Icon = { success: CheckCircle, error: AlertCircle, info: Info }[type];
  return (
    <motion.div initial={{ opacity: 0, y: -20, scale: 0.9 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
      className={`fixed top-5 right-5 z-50 flex items-center gap-2 px-4 py-3 rounded-2xl text-white text-sm shadow-2xl ${bg}`}>
      <Icon size={15} /> {message}
    </motion.div>
  );
}

function StarRating({ rating }: { rating: number }) {
  return (
    <span className="inline-flex items-center gap-1">
      <Star size={13} fill="#C4621D" stroke="none" />
      <span className="text-sm font-semibold text-[#C4621D]">{rating.toFixed(1)}</span>
    </span>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button role="switch" aria-checked={checked} onClick={onChange}
      className={`relative w-10 h-5 rounded-full transition-colors flex-shrink-0 ${checked ? "bg-[#C4621D]" : "bg-gray-300"}`}>
      <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${checked ? "translate-x-5" : "translate-x-0"}`} />
    </button>
  );
}

function FormInput({ label, value, onChange, type = "text", placeholder = "" }: { label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string; }) {
  return (
    <div>
      <label className="block text-sm font-medium text-[#1C1612] mb-1.5">{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full px-4 py-2.5 rounded-xl border border-white/50 bg-white/50 backdrop-blur-sm text-[#1C1612] placeholder-[#7A6E64] text-sm focus:outline-none focus:border-[#C4621D]/50 focus:ring-2 focus:ring-[#C4621D]/15 focus:bg-white/70 transition-all" />
    </div>
  );
}

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: Home, roles: ["user", "manager", "admin"] },
  { id: "recommendations", label: "Recommendations", icon: Search, roles: ["user", "manager", "admin"] },
  { id: "location", label: "Location", icon: Map, roles: ["user", "manager", "admin"] },
  { id: "rating", label: "Rating AI", icon: TrendingUp, roles: ["user", "manager", "admin"] },
  { id: "admin", label: "Admin", icon: Shield, roles: ["admin"] },
  { id: "manager", label: "Manager", icon: ChefHat, roles: ["manager", "admin"] },
  { id: "reports", label: "Reports", icon: FileText, roles: ["user", "manager", "admin"] },
] as const;

function HorizontalNav({ page, setPage, user, onLogout }: { page: string; setPage: (p: string) => void; user: UserT; onLogout: () => void; }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const items = NAV_ITEMS.filter(n => n.roles.includes(user.role as any));

  return (
    <header className="sticky top-0 z-30 bg-white/50 backdrop-blur-2xl border-b border-white/60 shadow-[0_2px_20px_rgba(196,98,29,0.06)]">
      <div className="max-w-[1400px] mx-auto px-5 flex items-center gap-3 h-16">
        <div className="flex items-center gap-2.5 flex-shrink-0 mr-4">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#C4621D] to-[#E8943A] flex items-center justify-center shadow-md shadow-orange-200">
            <ChefHat size={18} className="text-white" />
          </div>
          <span className="text-base font-semibold text-[#1C1612] hidden sm:block" style={{ fontFamily: "'Playfair Display', serif" }}>
            Restaurant<span className="text-[#C4621D]"> AI</span>
          </span>
        </div>

        <nav className="hidden lg:flex items-center gap-0.5 flex-1">
          {items.map(item => {
            const Icon = item.icon;
            const active = page === item.id;
            return (
              <button key={item.id} onClick={() => setPage(item.id)}
                className={`relative flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-medium transition-all ${active ? "text-[#C4621D]" : "text-[#7A6E64] hover:text-[#1C1612] hover:bg-white/50"}`}>
                <Icon size={15} />
                {item.label}
                {active && (
                  <motion.div layoutId="nav-pill"
                    className="absolute inset-0 rounded-xl bg-orange-50/90 border border-orange-200/60 -z-10"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }} />
                )}
              </button>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#2D5016]/10 border border-[#2D5016]/20">
            <span className="w-1.5 h-1.5 rounded-full bg-[#2D5016] animate-pulse" />
            <span className="text-xs font-medium text-[#2D5016] capitalize">{user.role}</span>
          </div>

          <button className="w-9 h-9 flex items-center justify-center rounded-xl bg-white/60 border border-white/70 text-[#7A6E64] hover:text-[#C4621D] hover:bg-white transition-all relative">
            <Bell size={16} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[#C4621D] border border-white" />
          </button>

          <div className="relative">
            <button onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/60 border border-white/70 hover:bg-white transition-all">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#2D5016] to-[#4A7A25] flex items-center justify-center text-white text-xs font-bold">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <span className="text-sm font-medium text-[#1C1612] hidden sm:block">{user.name.split(" ")[0]}</span>
              <ChevronDown size={13} className={`text-[#7A6E64] transition-transform ${userMenuOpen ? "rotate-180" : ""}`} />
            </button>
            <AnimatePresence>
              {userMenuOpen && (
                <motion.div initial={{ opacity: 0, y: 8, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 8, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 top-full mt-2 w-48 bg-white/90 backdrop-blur-xl border border-white/70 rounded-2xl shadow-xl overflow-hidden">
                  <div className="p-3 border-b border-gray-100">
                    <p className="text-sm font-semibold text-[#1C1612]">{user.name}</p>
                    <p className="text-xs text-[#7A6E64]">{user.email}</p>
                  </div>
                  <button onClick={() => { onLogout(); setUserMenuOpen(false); }}
                    className="w-full flex items-center gap-2 px-4 py-3 text-sm text-red-500 hover:bg-red-50 transition-colors">
                    <LogOut size={15} /> Sign Out
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <button onClick={() => setMenuOpen(!menuOpen)}
            className="lg:hidden w-9 h-9 flex items-center justify-center rounded-xl bg-white/60 border border-white/70 text-[#7A6E64]">
            {menuOpen ? <X size={17} /> : <Menu size={17} />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {menuOpen && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            className="lg:hidden overflow-hidden border-t border-white/50 bg-white/60 backdrop-blur-xl">
            <div className="p-3 grid grid-cols-2 gap-1">
              {items.map(item => {
                const Icon = item.icon;
                const active = page === item.id;
                return (
                  <button key={item.id} onClick={() => { setPage(item.id); setMenuOpen(false); }}
                    className={`flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${active ? "bg-orange-50 text-[#C4621D]" : "text-[#7A6E64] hover:bg-white/60"}`}>
                    <Icon size={15} /> {item.label}
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}

function DashboardPage({ auth, setPage }: { auth: AuthState; setPage: (p: string) => void }) {
  const [meta, setMeta] = useState<AppMetadata | null>(null);

  useEffect(() => {
    let active = true;
    const api = createApi(auth.apiBaseUrl, auth.token);
    api.get("/metadata/recommendations")
      .then(data => { if (active) setMeta(data); })
      .catch(() => { if (active) setMeta(null); });
    return () => { active = false; };
  }, [auth.apiBaseUrl, auth.token]);

  const ratingDistData = [
    { rating: "0.0\n(Unrated)", count: 2187, unrated: true },
    { rating: "1.0–1.9", count: 124 },
    { rating: "2.0–2.9", count: 312 },
    { rating: "3.0–3.4", count: 986 },
    { rating: "3.5–3.9", count: 1843 },
    { rating: "4.0–4.4", count: 2654 },
    { rating: "4.5–5.0", count: 1445 },
  ];

  const cuisineData = [
    { name: "North Indian", count: 3241 },
    { name: "Chinese", count: 1876 },
    { name: "Fast Food", count: 1543 },
    { name: "Mughlai", count: 1120 },
    { name: "Italian", count: 876 },
    { name: "Cafe", count: 654 },
  ];

  const cityData = [
    { city: "New Delhi", count: 5473 },
    { city: "Gurgaon", count: 1118 },
    { city: "Noida", count: 1080 },
    { city: "Faridabad", count: 251 },
    { city: "Ghaziabad", count: 25 },
  ];

  const STATS = [
    { label: "Total Restaurants", value: formatCount(meta?.restaurant_count ?? 9551), sub: meta?.admin_added_count ? `${meta.admin_added_count} added by admin` : "Restaurants in database", icon: Utensils, color: "from-orange-400 to-amber-500" },
    { label: "Avg. Rating Score", value: `${(meta?.average_rating ?? 3.75).toFixed(2)} / 5`, sub: "Excluding 0.0 ratings", icon: Star, color: "from-[#C4621D] to-[#E8943A]" },
    { label: "Cuisine Types", value: formatCount(meta?.cuisine_count ?? 120), sub: "Available cuisine categories", icon: ChefHat, color: "from-[#2D5016] to-[#4A7A25]" },
    { label: "Active Modules", value: "4", sub: "Recommend · Rating · Location · Reports", icon: BarChart2, color: "from-purple-500 to-violet-600" },
  ];

  const matchBars = [
    { label: "Cuisine Match", pct: 88, color: "#C4621D" },
    { label: "Rating Match", pct: 76, color: "#2D5016" },
    { label: "Cost Match", pct: 81, color: "#7B4F2E" },
    { label: "Location Match", pct: 64, color: "#4A7A25" },
    { label: "Delivery / Booking", pct: 72, color: "#E8943A" },
  ];

  const recentActivity = [
    { icon: Search, text: "User searched Indian restaurants in Mumbai", time: "2 min ago", color: "bg-orange-100 text-[#C4621D]" },
    { icon: Search, text: "User searched Italian restaurants under ₹1,200", time: "14 min ago", color: "bg-amber-100 text-amber-700" },
    { icon: Search, text: "User searched cafes with online delivery", time: "31 min ago", color: "bg-orange-100 text-[#C4621D]" },
    { icon: Edit2, text: "Manager updated menu item photo", time: "1 hr ago", color: "bg-green-100 text-[#2D5016]" },
    { icon: Upload, text: "Admin imported restaurant dataset", time: "3 hr ago", color: "bg-purple-100 text-purple-700" },
  ];

  const TS = { borderRadius: 12, border: "1px solid rgba(196,98,29,0.15)", background: "rgba(255,255,255,0.9)", backdropFilter: "blur(12px)", fontSize: 11 };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex-1">
          <h1 className="text-2xl font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>
            Restaurant Intelligence Dashboard
          </h1>
          <p className="text-[#7A6E64] text-sm mt-0.5">Recommendations, ratings and location insights in one place.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/60 border border-white/70 backdrop-blur-sm text-[#7A6E64]">
            <Search size={14} />
            <input className="bg-transparent outline-none text-sm text-[#1C1612] placeholder-[#7A6E64] w-36" placeholder="Search anything…" />
          </div>
          <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#2D5016]/10 border border-[#2D5016]/20">
            <span className="w-1.5 h-1.5 rounded-full bg-[#2D5016] animate-pulse" />
            <span className="text-xs font-semibold text-[#2D5016] capitalize">{auth.user.role}</span>
          </div>
        </div>
      </motion.div>

      {/* Quick Actions */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div className="flex flex-wrap gap-2.5">
          {[
            { label: "Get Recommendations", page: "recommendations", icon: Search, cls: "bg-gradient-to-r from-[#C4621D] to-[#E8943A] text-white shadow-md shadow-orange-200" },
            { label: "Explore Location Map", page: "location", icon: Map, cls: "bg-gradient-to-r from-[#2D5016] to-[#4A7A25] text-white shadow-md shadow-green-200" },
            { label: "View Rating Reports", page: "rating", icon: TrendingUp, cls: "bg-white/70 border border-white/70 text-[#1C1612] hover:bg-white" },
            { label: "Admin Panel", page: "admin", icon: Shield, cls: "bg-white/70 border border-white/70 text-[#1C1612] hover:bg-white" },
          ].filter(a => a.page !== "admin" || auth.user.role === "admin").map(a => {
            const Icon = a.icon;
            return (
              <motion.button key={a.page} onClick={() => setPage(a.page)} whileHover={{ y: -2 }} whileTap={{ scale: 0.96 }}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${a.cls}`}>
                <Icon size={14} /> {a.label}
              </motion.button>
            );
          })}
        </div>
      </motion.div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STATS.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <motion.div key={stat.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 + i * 0.08, type: "spring", stiffness: 280, damping: 22 }}>
              <GlassCard className="p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center shadow-md`}>
                    <Icon size={19} className="text-white" />
                  </div>
                </div>
                <div className="text-2xl font-bold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>{stat.value}</div>
                <div className="text-xs font-semibold text-[#1C1612] mt-0.5">{stat.label}</div>
                <div className="text-[10px] text-[#7A6E64] mt-0.5 leading-tight">{stat.sub}</div>
              </GlassCard>
            </motion.div>
          );
        })}
      </div>

      {/* Rating Distribution + Recommendation Match */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <motion.div className="lg:col-span-2" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.32 }}>
          <GlassCard className="p-5" hover={false}>
            <div className="flex items-start justify-between mb-5">
              <div>
                <h2 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>Rating Distribution</h2>
                <p className="text-xs text-[#7A6E64] mt-0.5">Restaurant ratings across the dataset</p>
              </div>
              <div className="flex items-center gap-3 text-[10px]">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-[#C4621D] inline-block" /> Rated</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-[#DDD] inline-block" /> Unrated</span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={185}>
              <BarChart data={ratingDistData} margin={{ top: 4, right: 4, left: -22, bottom: 0 }}
                barSize={28}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(196,98,29,0.07)" vertical={false} />
                <XAxis dataKey="rating" tick={{ fontSize: 10, fill: "#7A6E64" }} axisLine={false} tickLine={false} interval={0} />
                <YAxis tick={{ fontSize: 10, fill: "#7A6E64" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={TS} formatter={(v: number, _n: string, props: any) => [v.toLocaleString(), props.payload.unrated ? "Unrated Restaurants" : "Restaurants"]} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {ratingDistData.map((entry, index) => (
                    <Cell key={index} fill={entry.unrated ? "#C9BFB5" : "#C4621D"} fillOpacity={entry.unrated ? 0.7 : 1} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </GlassCard>
        </motion.div>

        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.37 }}>
          <GlassCard className="p-5 h-full flex flex-col" hover={false}>
            <div className="mb-4">
              <h2 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>Recommendation Match</h2>
              <p className="text-xs text-[#7A6E64] mt-0.5">Average match scores by factor</p>
            </div>
            <div className="space-y-3 flex-1">
              {matchBars.map((m, i) => (
                <div key={m.label}>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-[#7A6E64] font-medium">{m.label}</span>
                    <span className="font-semibold text-[#1C1612]" style={{ fontFamily: "'DM Mono', monospace" }}>{m.pct}%</span>
                  </div>
                  <div className="h-2 bg-black/8 rounded-full overflow-hidden">
                    <motion.div className="h-full rounded-full" style={{ background: m.color }}
                      initial={{ width: 0 }} animate={{ width: `${m.pct}%` }}
                      transition={{ delay: 0.55 + i * 0.07, duration: 0.75, ease: "easeOut" }} />
                  </div>
                </div>
              ))}
            </div>
            <motion.button onClick={() => setPage("recommendations")} whileHover={{ y: -1 }} whileTap={{ scale: 0.97 }}
              className="mt-5 w-full py-2.5 rounded-xl bg-orange-50 border border-orange-200 text-[#C4621D] text-xs font-semibold hover:bg-orange-100 transition-all flex items-center justify-center gap-1.5">
              <Search size={12} /> Run Recommendations
            </motion.button>
          </GlassCard>
        </motion.div>
      </div>

      {/* Top Recommended Restaurants */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>Top Recommended Restaurants</h2>
            <p className="text-xs text-[#7A6E64] mt-0.5">Highest scoring across dataset filters</p>
          </div>
          <button onClick={() => setPage("recommendations")} className="text-xs font-semibold text-[#C4621D] hover:text-[#a0511a] transition-colors flex items-center gap-1">
            View All <ArrowUpRight size={13} />
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {MOCK_RESTAURANTS.map((r, i) => (
            <motion.div key={r.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.55 + i * 0.07, type: "spring", stiffness: 280, damping: 22 }}>
              <GlassCard className="overflow-hidden">
                <div className="relative h-40 bg-amber-100 overflow-hidden">
                  <img src={`https://images.unsplash.com/photo-${r.image}?w=400&h=300&fit=crop&auto=format`} alt={r.name} className="w-full h-full object-cover transition-transform duration-500 hover:scale-105" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
                  <div className="absolute top-2.5 left-2.5 w-6 h-6 rounded-full bg-[#C4621D] flex items-center justify-center text-white text-xs font-bold shadow">{i + 1}</div>
                  <div className="absolute bottom-2.5 right-2.5">
                    <span className="flex items-center gap-1 bg-black/50 backdrop-blur-sm px-2 py-0.5 rounded-full">
                      <Star size={10} fill="#F59E0B" stroke="none" />
                      <span className="text-white text-[11px] font-semibold">{r.rating}</span>
                    </span>
                  </div>
                </div>
                <div className="p-3.5">
                  <h3 className="font-semibold text-[#1C1612] text-sm" style={{ fontFamily: "'Playfair Display', serif" }}>{r.name}</h3>
                  <p className="text-[#7A6E64] text-xs mt-0.5">{r.cuisine}</p>
                  <div className="flex items-center gap-1 mt-1 text-xs text-[#7A6E64]"><MapPin size={10} /> {r.city}</div>
                  <div className="flex items-center justify-between mt-3">
                    <span className="text-sm font-bold text-[#C4621D]" style={{ fontFamily: "'Playfair Display', serif" }}>₹{r.avg_cost}</span>
                    <div className="flex gap-1">
                      {r.online_delivery && <span className="px-1.5 py-0.5 bg-green-100 text-green-700 text-[10px] rounded-full font-medium">Delivery</span>}
                      {r.table_booking && <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 text-[10px] rounded-full font-medium">Booking</span>}
                    </div>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Cuisine Popularity + Location Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <motion.div className="lg:col-span-2" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.65 }}>
          <GlassCard className="p-5" hover={false}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>Cuisine Popularity</h2>
                <p className="text-xs text-[#7A6E64] mt-0.5">Most common cuisine categories in the dataset</p>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={185}>
              <BarChart data={cuisineData} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(196,98,29,0.07)" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: "#7A6E64" }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "#7A6E64" }} width={82} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={TS} formatter={(v: number) => [v.toLocaleString(), "Restaurants"]} />
                <Bar dataKey="count" fill="#C4621D" radius={[0, 6, 6, 0]}
                  background={{ fill: "rgba(196,98,29,0.05)", radius: 6 }} />
              </BarChart>
            </ResponsiveContainer>
          </GlassCard>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }}>
          <GlassCard className="overflow-hidden h-full flex flex-col" hover={false}>
            <div className="relative h-32 flex-shrink-0">
              <img src="https://images.unsplash.com/photo-1524661135-423995f22d0b?w=600&h=300&fit=crop&auto=format" alt="Map" className="w-full h-full object-cover opacity-50" />
              <div className="absolute inset-0 bg-gradient-to-br from-[#1C1612]/75 to-[#2D5016]/55" />
              <div className="absolute bottom-3 left-4">
                <p className="text-white text-xs font-semibold tracking-wider uppercase opacity-70">Location Insights</p>
                <p className="text-white text-sm font-semibold" style={{ fontFamily: "'Playfair Display', serif" }}>Restaurant Density</p>
              </div>
            </div>
            <div className="p-4 flex-1 flex flex-col">
              <div className="space-y-1.5 flex-1">
                {[
                  { label: "Top city by restaurants", value: "New Delhi", sub: "5,473 listings" },
                  { label: "Highest avg. rating", value: "Bangalore", sub: "4.3 avg score" },
                  { label: "Most common cuisine", value: "North Indian", sub: "Across all cities" },
                ].map(item => (
                  <div key={item.label} className="flex items-center justify-between p-2 rounded-lg bg-white/40 hover:bg-white/60 transition-colors">
                    <div>
                      <p className="text-[10px] text-[#7A6E64]">{item.label}</p>
                      <p className="text-xs font-semibold text-[#1C1612]">{item.value}</p>
                    </div>
                    <span className="text-[10px] text-[#7A6E64]">{item.sub}</span>
                  </div>
                ))}
              </div>
              <motion.button onClick={() => setPage("location")} whileTap={{ scale: 0.97 }}
                className="mt-3 w-full py-2 rounded-xl bg-[#2D5016]/10 border border-[#2D5016]/25 text-[#2D5016] text-xs font-semibold hover:bg-[#2D5016]/15 transition-all flex items-center justify-center gap-1.5">
                <Map size={12} /> Open Map Analysis
              </motion.button>
            </div>
          </GlassCard>
        </motion.div>
      </div>

      {/* City Concentration + Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.78 }}>
          <GlassCard className="p-5" hover={false}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>City Concentration</h2>
                <p className="text-xs text-[#7A6E64] mt-0.5">Restaurants by city in the dataset</p>
              </div>
            </div>
            <div className="space-y-2.5">
              {cityData.map((c, i) => (
                <div key={c.city}>
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="font-medium text-[#1C1612] flex items-center gap-1.5">
                      <span className="w-4 h-4 rounded-md bg-gradient-to-br from-[#C4621D] to-[#E8943A] flex items-center justify-center text-white text-[9px] font-bold">{i + 1}</span>
                      {c.city}
                    </span>
                    <span className="font-semibold text-[#1C1612]" style={{ fontFamily: "'DM Mono', monospace" }}>{c.count.toLocaleString()}</span>
                  </div>
                  <div className="h-2 bg-black/8 rounded-full overflow-hidden">
                    <motion.div className="h-full rounded-full bg-gradient-to-r from-[#C4621D] to-[#E8943A]"
                      initial={{ width: 0 }} animate={{ width: `${(c.count / 5473) * 100}%` }}
                      transition={{ delay: 0.85 + i * 0.07, duration: 0.7, ease: "easeOut" }} />
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.82 }}>
          <GlassCard className="p-5" hover={false}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>Recent Recommendation Activity</h2>
                <p className="text-xs text-[#7A6E64] mt-0.5">Latest user and admin actions</p>
              </div>
            </div>
            <div className="space-y-2">
              {recentActivity.map((a, i) => {
                const Icon = a.icon;
                return (
                  <motion.div key={i} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.9 + i * 0.05 }}
                    className="flex items-start gap-3 p-2.5 rounded-xl bg-white/40 hover:bg-white/60 transition-colors">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${a.color}`}>
                      <Icon size={12} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-[#1C1612] leading-snug">{a.text}</p>
                      <p className="text-[10px] text-[#7A6E64] mt-0.5">{a.time}</p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </div>
  );
}

function RecommendationsPage({ auth }: { auth: AuthState }) {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Restaurant[]>([]);
  const [searched, setSearched] = useState(false);
  const [pref, setPref] = useState({ cuisines: [] as string[], cities: [] as string[], price_range: 0, min_rating: 3.5, max_cost: 2000, min_popularity: 0, top_k: 10, online_delivery: false, table_booking: false });
  const [options, setOptions] = useState({ cuisines: [] as string[], cities: [] as string[], cost_categories: [] as string[] });

  useEffect(() => {
    let active = true;
    const api = createApi(auth.apiBaseUrl, auth.token);
    api.get("/metadata/recommendations")
      .then(data => {
        if (!active) return;
        setOptions({
          cuisines: Array.isArray(data.cuisines) ? data.cuisines : [],
          cities: Array.isArray(data.cities) ? data.cities : [],
          cost_categories: Array.isArray(data.cost_categories) ? data.cost_categories : [],
        });
      })
      .catch(() => {
        if (active) setOptions({ cuisines: [], cities: [], cost_categories: [] });
      });
    return () => { active = false; };
  }, [auth.apiBaseUrl, auth.token]);

  const cuisineOptions = options.cuisines.length ? options.cuisines : FALLBACK_CUISINES;
  const cityOptions = options.cities.length ? options.cities : CITIES;
  const toggle = (c: string) => setPref(p => ({ ...p, cuisines: p.cuisines.includes(c) ? p.cuisines.filter(x => x !== c) : [...p.cuisines, c] }));
  const toggleCity = (city: string) => setPref(p => ({ ...p, cities: p.cities.includes(city) ? p.cities.filter(x => x !== city) : [...p.cities, city] }));

  const handleSearch = async () => {
    setLoading(true);
    try {
      const api = createApi(auth.apiBaseUrl, auth.token);
      const data = await api.post("/recommendations", {
        user_id: auth.user.id,
        cuisines: pref.cuisines,
        cities: pref.cities,
        city: pref.cities[0] || null,
        price_range: pref.price_range || null,
        min_rating: pref.min_rating,
        max_cost: pref.max_cost,
        min_votes: pref.min_popularity,
        popularity_category: null,
        top_n: pref.top_k,
        online_delivery: pref.online_delivery ? "Yes" : null,
        table_booking: pref.table_booking ? "Yes" : null,
        save_history: true,
      });
      setResults((data.recommendations || []).map(toRestaurant));
    } catch (err: any) {
      setResults([]);
      alert(err.message || "Unable to fetch recommendations from backend.");
    }
    setSearched(true); setLoading(false);
  };

  const TS = { borderRadius: 12, border: "1px solid rgba(196,98,29,0.15)", background: "rgba(255,255,255,0.85)", backdropFilter: "blur(12px)", fontSize: 12 };

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <GlassCard className="p-6" hover={false}>
          <h2 className="text-lg font-semibold text-[#1C1612] mb-5" style={{ fontFamily: "'Playfair Display', serif" }}>Your Preferences</h2>
          <div className="mb-5">
            <div className="flex items-center justify-between mb-2.5">
              <p className="text-sm font-medium text-[#1C1612]">Cuisine Type</p>
              <span className="text-xs text-[#7A6E64]">{cuisineOptions.length} available</span>
            </div>
            <div className="flex max-h-40 flex-wrap gap-2 overflow-y-auto pr-1">
              {cuisineOptions.map(c => (
                <motion.button key={c} onClick={() => toggle(c)} whileTap={{ scale: 0.92 }}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${pref.cuisines.includes(c) ? "bg-[#C4621D] text-white border-[#C4621D] shadow-md shadow-orange-200" : "bg-white/50 text-[#7A6E64] border-white/60 hover:border-[#C4621D]/40 hover:text-[#C4621D]"}`}>
                  {c}
                </motion.button>
              ))}
            </div>
          </div>

          <div className="mb-5">
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label className="block text-sm font-medium text-[#1C1612]">Cities</label>
                <span className="text-xs text-[#7A6E64]">{pref.cities.length ? `${pref.cities.length} selected` : "Any city"}</span>
              </div>
              <div className="flex max-h-28 flex-wrap gap-2 overflow-y-auto rounded-xl border border-white/50 bg-white/40 p-2">
                {cityOptions.map(city => (
                  <motion.button key={city} type="button" whileTap={{ scale: 0.92 }} onClick={() => toggleCity(city)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${pref.cities.includes(city) ? "bg-[#C4621D] text-white border-[#C4621D] shadow-sm" : "bg-white/60 text-[#7A6E64] border-white/70 hover:border-[#C4621D]/40 hover:text-[#C4621D]"}`}>
                    {city}
                  </motion.button>
                ))}
              </div>
            </div>
          </div>

          <div className="mb-5">
            <label className="block text-sm font-medium text-[#1C1612] mb-1.5">Price Range</label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {PRICE_LEVELS.map(level => (
                <motion.button key={level.value} whileTap={{ scale: 0.9 }} onClick={() => setPref({ ...pref, price_range: pref.price_range === level.value ? 0 : level.value })}
                  className={`py-2 rounded-xl text-sm font-medium border transition-all ${pref.price_range === level.value ? "bg-[#C4621D] text-white border-[#C4621D] shadow-md" : "bg-white/50 text-[#7A6E64] border-white/50 hover:border-[#C4621D]/40"}`}>
                  {level.label}
                </motion.button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
            {[
              { key: "min_rating" as const, label: "Minimum Rating", min: 1, max: 5, step: 0.1, fmt: (v: number) => v.toFixed(1) },
              { key: "max_cost" as const, label: "Max Cost for Two (₹)", min: 200, max: 5000, step: 100, fmt: (v: number) => `₹${v}` },
              { key: "min_popularity" as const, label: "Min Popularity (votes)", min: 0, max: 2000, step: 50, fmt: (v: number) => `${v}` },
              { key: "top_k" as const, label: "Maximum Results", min: 5, max: 50, step: 5, fmt: (v: number) => `${v}` },
            ].map(s => (
              <div key={s.key}>
                <label className="block text-sm font-medium text-[#1C1612] mb-1.5">{s.label}: <span className="text-[#C4621D] font-semibold">{s.fmt(pref[s.key] as number)}</span></label>
                <input type="range" min={s.min} max={s.max} step={s.step} value={pref[s.key] as number} onChange={e => setPref({ ...pref, [s.key]: parseFloat(e.target.value) })} className="w-full accent-[#C4621D]" />
                <div className="flex justify-between text-xs text-[#7A6E64] mt-1"><span>{s.fmt(s.min)}</span><span>{s.fmt(s.max)}</span></div>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-8 mb-6">
            {[["online_delivery", "Online Delivery"], ["table_booking", "Table Booking"]].map(([k, l]) => (
              <label key={k} className="flex items-center gap-2.5 cursor-pointer">
                <Toggle checked={(pref as any)[k]} onChange={() => setPref({ ...pref, [k]: !(pref as any)[k] })} />
                <span className="text-sm text-[#1C1612]">{l}</span>
              </label>
            ))}
          </div>

          <div className="flex gap-3">
            <motion.button onClick={handleSearch} disabled={loading} whileTap={{ scale: 0.97 }}
              className="flex-1 py-3 bg-gradient-to-r from-[#C4621D] to-[#E8943A] text-white rounded-xl font-medium shadow-lg shadow-orange-200 hover:shadow-xl hover:shadow-orange-200 transition-all disabled:opacity-60">
              {loading ? "Finding restaurants…" : "Show My Recommendations"}
            </motion.button>
            <button onClick={() => { setPref({ cuisines: [], cities: [], price_range: 0, min_rating: 3.5, max_cost: 2000, min_popularity: 0, top_k: 10, online_delivery: false, table_booking: false }); setResults([]); setSearched(false); }}
              className="px-5 py-3 bg-white/50 text-[#7A6E64] rounded-xl font-medium hover:bg-white/70 border border-white/60 transition-all">
              Reset
            </button>
          </div>
        </GlassCard>
      </motion.div>

      <AnimatePresence>
        {searched && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <GlassCard hover={false}>
              <div className="px-5 py-4 border-b border-white/50 flex items-center justify-between bg-gradient-to-r from-[#1C1612]/90 to-[#2D5016]/90 backdrop-blur-xl rounded-t-2xl">
                <h2 className="text-lg font-semibold text-white" style={{ fontFamily: "'Playfair Display', serif" }}>{results.length} Restaurant{results.length !== 1 ? "s" : ""} Found</h2>
                <span className="text-white/40 text-xs">By match score</span>
              </div>
              <div className="divide-y divide-white/30">
                {results.length === 0 ? <p className="p-8 text-center text-[#7A6E64]">No restaurants match your filters.</p>
                  : results.map((r, i) => (
                    <motion.div key={r.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
                      className="flex items-center gap-4 p-4 hover:bg-white/40 transition-colors">
                      <span className="w-7 text-center text-[#C4621D] font-bold text-sm flex-shrink-0">#{i + 1}</span>
                      <div className="w-12 h-12 rounded-xl overflow-hidden bg-amber-100 flex-shrink-0">
                        <img src={`https://images.unsplash.com/photo-${r.image}?w=100&h=100&fit=crop&auto=format`} alt={r.name} className="w-full h-full object-cover" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[#1C1612] text-sm font-semibold truncate">{r.name}</p>
                        <p className="text-[#7A6E64] text-xs mt-0.5">{r.cuisine} · {r.city}</p>
                      </div>
                      <span className="hidden sm:block text-[#7A6E64] text-xs">₹{r.avg_cost}</span>
                      <StarRating rating={r.rating} />
                      {r.match_score != null && <span className="hidden md:block px-2.5 py-1 rounded-full bg-green-100 text-green-700 text-xs font-semibold flex-shrink-0">{r.match_score}% match</span>}
                    </motion.div>
                  ))}
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function LocationPage({ auth }: { auth: AuthState }) {
  const [meta, setMeta] = useState<AppMetadata | null>(null);

  useEffect(() => {
    let active = true;
    const api = createApi(auth.apiBaseUrl, auth.token);
    api.get("/metadata/recommendations")
      .then(data => { if (active) setMeta(data); })
      .catch(() => { if (active) setMeta(null); });
    return () => { active = false; };
  }, [auth.apiBaseUrl, auth.token]);

  const cityData = [
    { city: "Mumbai", restaurants: 2341, avg_rating: 4.2, avg_cost: 1200 },
    { city: "Delhi", restaurants: 1876, avg_rating: 4.0, avg_cost: 950 },
    { city: "Bangalore", restaurants: 1654, avg_rating: 4.3, avg_cost: 1100 },
    { city: "Pune", restaurants: 987, avg_rating: 4.1, avg_cost: 750 },
    { city: "Chennai", restaurants: 876, avg_rating: 3.9, avg_cost: 680 },
    { city: "Hyderabad", restaurants: 743, avg_rating: 4.0, avg_cost: 820 },
    { city: "Kolkata", restaurants: 654, avg_rating: 4.1, avg_cost: 700 },
    { city: "Ahmedabad", restaurants: 420, avg_rating: 3.8, avg_cost: 550 },
  ];
  const cuisineData = [
    { cuisine: "North Indian", count: 3241 }, { cuisine: "Chinese", count: 1876 },
    { cuisine: "Fast Food", count: 1543 }, { cuisine: "South Indian", count: 1234 },
    { cuisine: "Italian", count: 876 }, { cuisine: "Continental", count: 654 },
  ];
  const TS = { borderRadius: 12, border: "1px solid rgba(196,98,29,0.15)", background: "rgba(255,255,255,0.9)", backdropFilter: "blur(12px)", fontSize: 12 };
  const openAnalysis = (file: string) => {
    window.open(`${auth.apiBaseUrl}/analysis/location_results/${file}`, "_blank", "noopener,noreferrer");
  };
  const locationActions = [
    { label: "Restaurant Markers", icon: MapPin, color: "from-orange-400 to-amber-500", file: "restaurant_location_marker_map.html" },
    { label: "Density Heatmap", icon: Map, color: "from-red-400 to-rose-500", file: "restaurant_density_heatmap.html" },
    { label: "City Statistics", icon: BarChart2, color: "from-green-400 to-emerald-500", file: "top_cities_by_restaurant_count.html" },
    { label: "Cuisine Statistics", icon: Compass, color: "from-blue-400 to-indigo-500", file: "top_cuisines_overall.html" },
  ];

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="relative h-52 rounded-2xl overflow-hidden">
          <img src="https://images.unsplash.com/photo-1524661135-423995f22d0b?w=1400&h=600&fit=crop&auto=format" alt="Map" className="w-full h-full object-cover opacity-55" />
          <div className="absolute inset-0 bg-gradient-to-br from-[#1C1612]/80 to-[#2D5016]/60 backdrop-blur-sm" />
          <div className="absolute bottom-5 left-6">
            <p className="text-[#C4621D] text-xs font-semibold tracking-widest uppercase mb-1.5">Geographical Intelligence</p>
            <h2 className="text-2xl text-white font-semibold" style={{ fontFamily: "'Playfair Display', serif" }}>Restaurant Density Analysis</h2>
            <p className="text-white/55 text-sm mt-1">{formatCount(meta?.restaurant_count ?? 9551)} restaurants across {formatCount(meta?.city_count ?? 8)} cities</p>
          </div>
          <div className="absolute top-4 right-4 flex gap-2">
            {[["High", "bg-red-400"], ["Medium", "bg-yellow-400"], ["Low", "bg-green-400"]].map(([l, c]) => (
              <div key={l} className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/30 backdrop-blur-sm"><span className={`w-2 h-2 rounded-full ${c}`} /><span className="text-white text-xs">{l}</span></div>
            ))}
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {locationActions.map(a => {
          const Icon = a.icon;
          return (
            <motion.button key={a.label} type="button" onClick={() => openAnalysis(a.file)} whileHover={{ y: -3 }} whileTap={{ scale: 0.96 }} className="text-left">
              <GlassCard className="p-4 flex flex-col items-center text-center gap-2 cursor-pointer h-full">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${a.color} flex items-center justify-center shadow-md`}><Icon size={18} className="text-white" /></div>
                <span className="text-xs font-semibold text-[#1C1612]">{a.label}</span>
                <span className="text-[10px] text-[#7A6E64]">Open report</span>
              </GlassCard>
            </motion.button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {[{ title: "Top Cities by Restaurant Count", dataKey: "restaurants", color: "#2D5016" }, { title: "Average Rating by City", dataKey: "avg_rating", color: "#C4621D" }, { title: "Average Cost for Two (₹)", dataKey: "avg_cost", color: "#7B4F2E" }].map(chart => (
          <motion.div key={chart.title} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <GlassCard className="p-5" hover={false}>
              <h3 className="font-semibold text-[#1C1612] mb-4" style={{ fontFamily: "'Playfair Display', serif" }}>{chart.title}</h3>
              <ResponsiveContainer width="100%" height={190}>
                <BarChart data={cityData}><CartesianGrid strokeDasharray="3 3" stroke="rgba(196,98,29,0.08)" /><XAxis dataKey="city" tick={{ fontSize: 10, fill: "#7A6E64" }} axisLine={false} tickLine={false} /><YAxis tick={{ fontSize: 10, fill: "#7A6E64" }} axisLine={false} tickLine={false} /><Tooltip contentStyle={TS} /><Bar dataKey={chart.dataKey} fill={chart.color} radius={[6, 6, 0, 0]} /></BarChart>
              </ResponsiveContainer>
            </GlassCard>
          </motion.div>
        ))}

        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <GlassCard className="p-5" hover={false}>
            <h3 className="font-semibold text-[#1C1612] mb-4" style={{ fontFamily: "'Playfair Display', serif" }}>Popular Cuisines</h3>
            <ResponsiveContainer width="100%" height={190}>
              <BarChart data={cuisineData} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="rgba(196,98,29,0.08)" horizontal={false} /><XAxis type="number" tick={{ fontSize: 10, fill: "#7A6E64" }} axisLine={false} tickLine={false} /><YAxis type="category" dataKey="cuisine" tick={{ fontSize: 10, fill: "#7A6E64" }} width={85} axisLine={false} tickLine={false} /><Tooltip contentStyle={TS} /><Bar dataKey="count" fill="#2D5016" radius={[0, 6, 6, 0]} /></BarChart>
            </ResponsiveContainer>
          </GlassCard>
        </motion.div>
      </div>

      <GlassCard hover={false}>
        <div className="p-5 border-b border-white/50"><h3 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>City Statistics</h3></div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead><tr className="bg-white/30">{["City", "Restaurants", "Avg Rating", "Avg Cost (₹)", "Density"].map(h => <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-[#7A6E64] uppercase tracking-wider">{h}</th>)}</tr></thead>
            <tbody className="divide-y divide-white/40">
              {cityData.map((r, i) => (
                <motion.tr key={r.city} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }} className="hover:bg-white/40 transition-colors">
                  <td className="px-5 py-3 text-sm font-medium text-[#1C1612]">{r.city}</td>
                  <td className="px-5 py-3 text-sm text-[#7A6E64]">{r.restaurants.toLocaleString()}</td>
                  <td className="px-5 py-3"><StarRating rating={r.avg_rating} /></td>
                  <td className="px-5 py-3 text-sm text-[#7A6E64]">₹{r.avg_cost}</td>
                  <td className="px-5 py-3 w-32">
                    <div className="h-1.5 bg-black/8 rounded-full overflow-hidden"><motion.div className="h-full rounded-full bg-gradient-to-r from-[#C4621D] to-[#E8943A]" initial={{ width: 0 }} animate={{ width: `${(r.restaurants / 2341) * 100}%` }} transition={{ delay: 0.5 + i * 0.05, duration: 0.7 }} /></div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}

function RatingPage({ auth }: { auth: AuthState }) {
  const features = [
    { feature: "Popularity Category", importance: 0.3769 },
    { feature: "Cuisines", importance: 0.2021 },
    { feature: "Log Votes", importance: 0.1203 },
    { feature: "City Location Cluster", importance: 0.1019 },
    { feature: "City", importance: 0.0690 },
    { feature: "City Restaurant Count", importance: 0.0377 },
    { feature: "Country Code", importance: 0.0355 },
    { feature: "Location Cluster", importance: 0.0154 },
  ];
  const models = [
    { model: "XGBoost Engineered", mae: "0.1977", rmse: "0.2954", r2: "0.9620", within50: "90.30%", best: true, note: "Best test performance" },
    { model: "CatBoost Engineered", mae: "0.2032", rmse: "0.2991", r2: "0.9610", within50: "89.81%", best: false, note: "Strong tuned baseline" },
    { model: "CatBoost Base", mae: "0.2032", rmse: "0.2997", r2: "0.9608", within50: "89.18%", best: false, note: "Base feature set" },
    { model: "CatBoost Without Votes", mae: "0.8028", rmse: "1.0664", r2: "0.5045", within50: "44.66%", best: false, note: "Votes removed" },
  ];
  const tuningSummary = [
    { label: "Algorithm", value: "XGBoost Regressor" },
    { label: "Tuning Setup", value: "8 candidates, 3-fold CV" },
    { label: "Best CV Result", value: "RMSE 0.3023, MAE 0.1990, R2 0.9606" },
    { label: "Best Hyperparameters", value: "max_depth=6, learning_rate=0.03, n_estimators=1200, subsample=0.9, colsample_bytree=0.9, reg_lambda=7" },
  ];
  const TS = { borderRadius: 12, border: "1px solid rgba(196,98,29,0.15)", background: "rgba(255,255,255,0.9)", backdropFilter: "blur(12px)", fontSize: 12 };
  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#1C1612] to-[#2D5016] p-6 text-white">
        <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-[#C4621D]/10 blur-3xl pointer-events-none" />
        <p className="text-[#C4621D] text-xs font-semibold tracking-widest uppercase mb-2">ML Model Overview</p>
        <h2 className="text-2xl font-semibold mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>Rating Prediction Engine</h2>
        <p className="text-white/55 text-sm max-w-xl">Rating prediction model trained on 9,551 restaurant records using engineered restaurant, cuisine, location, cost and popularity features.</p>
        <div className="flex flex-wrap gap-3 mt-4">
          <span className="px-3 py-1.5 rounded-full bg-white/10 border border-white/20 text-white text-xs font-medium">Best Model: XGBoost Engineered</span>
          <span className="px-3 py-1.5 rounded-full bg-[#C4621D]/20 border border-[#C4621D]/40 text-[#C4621D] text-xs font-medium">Test R2: 0.9620</span>
          <span className="px-3 py-1.5 rounded-full bg-white/10 border border-white/20 text-white text-xs font-medium">Within 0.50 Rating: 90.30%</span>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[{ l: "MAE", v: "0.1977", d: "Mean Absolute Error" }, { l: "RMSE", v: "0.2954", d: "Root Mean Squared Error" }, { l: "R2 Score", v: "0.9620", d: "Coefficient of determination" }, { l: "Within 0.50", v: "90.30%", d: "Test predictions within half rating" }].map((m, i) => (
          <motion.div key={m.l} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
            <GlassCard className="p-5 text-center">
              <div className="text-3xl font-bold text-[#C4621D] mb-1" style={{ fontFamily: "'Playfair Display', serif" }}>{m.v}</div>
              <div className="text-sm font-semibold text-[#1C1612]">{m.l}</div>
              <div className="text-xs text-[#7A6E64] mt-0.5">{m.d}</div>
            </GlassCard>
          </motion.div>
        ))}
      </div>

      <GlassCard className="p-5" hover={false}>
        <div className="flex items-center justify-between gap-4 mb-4">
          <h3 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>Hyperparameter Tuning Summary</h3>
          <span className="text-xs text-[#7A6E64]">XGBoost engineered rating model</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {tuningSummary.map(item => (
            <div key={item.label} className="rounded-xl bg-white/45 border border-white/60 p-3">
              <p className="text-xs font-semibold text-[#C4621D] uppercase tracking-wide">{item.label}</p>
              <p className="text-sm text-[#1C1612] mt-1 leading-relaxed">{item.value}</p>
            </div>
          ))}
        </div>
      </GlassCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <GlassCard className="p-5" hover={false}>
          <h3 className="font-semibold text-[#1C1612] mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>Feature Importance</h3>
          <p className="text-xs text-[#7A6E64] mb-4">From the best XGBoost engineered model. Popularity, cuisine and vote signals dominate the rating prediction.</p>
          <div className="space-y-3">
            {features.map((f, i) => (
              <div key={f.feature} className="flex items-center gap-3">
                <span className="text-sm text-[#7A6E64] w-40 flex-shrink-0">{f.feature}</span>
                <div className="flex-1 bg-black/8 rounded-full h-2 overflow-hidden">
                  <motion.div className="h-full rounded-full bg-gradient-to-r from-[#C4621D] to-[#E8943A]" initial={{ width: 0 }} animate={{ width: `${f.importance * 100}%` }} transition={{ delay: 0.3 + i * 0.08, duration: 0.7 }} />
                </div>
                <span className="text-sm font-semibold text-[#1C1612] w-8 text-right" style={{ fontFamily: "'DM Mono', monospace" }}>{(f.importance * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </GlassCard>
        <GlassCard className="p-5" hover={false}>
          <h3 className="font-semibold text-[#1C1612] mb-4" style={{ fontFamily: "'Playfair Display', serif" }}>Feature Importance Chart</h3>
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={features} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="rgba(196,98,29,0.08)" horizontal={false} /><XAxis type="number" tick={{ fontSize: 10, fill: "#7A6E64" }} axisLine={false} tickLine={false} tickFormatter={v => `${(v * 100).toFixed(0)}%`} /><YAxis type="category" dataKey="feature" tick={{ fontSize: 10, fill: "#7A6E64" }} width={130} axisLine={false} tickLine={false} /><Tooltip contentStyle={TS} formatter={(v: number) => [`${(v * 100).toFixed(1)}%`, "Importance"]} /><Bar dataKey="importance" fill="#C4621D" radius={[0, 6, 6, 0]} /></BarChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>

      <GlassCard hover={false}>
        <div className="p-5 border-b border-white/50 flex items-center justify-between"><h3 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>Rating Model Analysis</h3><span className="text-xs text-[#7A6E64]">Lower MAE/RMSE and higher R2 indicate better test performance</span></div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead><tr className="bg-white/30">{["Model", "MAE", "RMSE", "R2", "Within 0.50", "Analysis"].map(h => <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-[#7A6E64] uppercase tracking-wider">{h}</th>)}</tr></thead>
            <tbody className="divide-y divide-white/40">
              {models.map(m => (
                <tr key={m.model} className={`hover:bg-white/40 transition-colors ${m.best ? "bg-orange-50/40" : ""}`}>
                  <td className="px-5 py-3"><div className="flex items-center gap-2 text-sm font-medium text-[#1C1612]">{m.model}{m.best && <span className="px-2 py-0.5 bg-[#C4621D] text-white text-xs rounded-full">Best</span>}</div></td>
                  <td className="px-5 py-3 text-sm text-[#7A6E64]" style={{ fontFamily: "'DM Mono', monospace" }}>{m.mae}</td>
                  <td className="px-5 py-3 text-sm text-[#7A6E64]" style={{ fontFamily: "'DM Mono', monospace" }}>{m.rmse}</td>
                  <td className="px-5 py-3 text-sm font-semibold text-[#2D5016]" style={{ fontFamily: "'DM Mono', monospace" }}>{m.r2}</td>
                  <td className="px-5 py-3 text-sm text-[#7A6E64]" style={{ fontFamily: "'DM Mono', monospace" }}>{m.within50}</td>
                  <td className="px-5 py-3">{m.best ? <span className="flex items-center gap-1 text-[#2D5016] text-xs font-medium"><CheckCircle size={12} /> {m.note}</span> : <span className="text-[#7A6E64] text-xs">{m.note}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
      <div className="flex flex-wrap gap-3">
        {["Rating Report", "Feature Importance", "Model Metrics CSV"].map(label => (
          <motion.button key={label} whileHover={{ y: -2 }} whileTap={{ scale: 0.96 }} className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/60 border border-white/60 text-[#1C1612] text-sm font-medium hover:bg-white/80 transition-all shadow-sm"><Download size={14} /> {label}</motion.button>
        ))}
      </div>
    </div>
  );
}

function AdminPanel({ auth }: { auth: AuthState }) {
  type Tab = "users" | "restaurants" | "assign" | "import";
  const [tab, setTab] = useState<Tab>("users");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const showToast = (msg: string, type: "success" | "error" | "info" = "success") => setToast({ message: msg, type });
  const [users, setUsers] = useState<UserT[]>([]);
  const [uForm, setUForm] = useState({ name: "", email: "", password: "", role: "user", managed_restaurant_id: "" });
  const [rForm, setRForm] = useState({ name: "", city: "", locality: "", address: "", cuisines: "", avg_cost: "", price_range: "1", rating: "", votes: "", online_delivery: false, table_booking: false });
  const [aForm, setAForm] = useState({ manager_id: "", restaurant_id: "" });
  const TABS: { id: Tab; label: string }[] = [{ id: "users", label: "Users" }, { id: "restaurants", label: "Add Restaurant" }, { id: "assign", label: "Assign Manager" }, { id: "import", label: "Import Dataset" }];
  const ROLE_COLORS: Record<string, string> = { admin: "bg-red-100 text-red-700", manager: "bg-amber-100 text-amber-700", user: "bg-green-100 text-green-700" };
  const btnCls = "w-full py-2.5 bg-gradient-to-r from-[#C4621D] to-[#E8943A] text-white rounded-xl text-sm font-medium shadow-md hover:shadow-lg transition-all";

  const loadUsers = async () => {
    try {
      const api = createApi(auth.apiBaseUrl, auth.token);
      const data = await api.get("/users");
      setUsers((data || []).map(toAppUser));
    } catch (err: any) {
      showToast(err.message || "Unable to load users", "error");
    }
  };

  useEffect(() => { loadUsers(); }, []);
  return (
    <div className="space-y-6">
      <AnimatePresence>{toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}</AnimatePresence>
      <div className="flex gap-1 p-1 bg-white/50 border border-white/60 rounded-2xl w-fit backdrop-blur-sm flex-wrap">
        {TABS.map(t => <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${tab === t.id ? "bg-white text-[#C4621D] shadow-sm" : "text-[#7A6E64] hover:text-[#1C1612]"}`}>{t.label}</button>)}
      </div>

      {tab === "users" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <GlassCard className="p-6" hover={false}>
            <h3 className="font-semibold text-[#1C1612] mb-5" style={{ fontFamily: "'Playfair Display', serif" }}>Create User</h3>
            <form onSubmit={async e => { e.preventDefault(); try { const api = createApi(auth.apiBaseUrl, auth.token); const d = await api.post("/users", { name: uForm.name, email: uForm.email, password: uForm.password, role: uForm.role, managed_restaurant_id: null }); setUsers(p => [...p, toAppUser(d)]); showToast(`User #${d.user_id} created as ${d.role}`, "success"); setUForm({ name: "", email: "", password: "", role: "user", managed_restaurant_id: "" }); } catch (err: any) { showToast(err.message || "Unable to create user", "error"); } }} className="space-y-4">
              <FormInput label="Full Name" value={uForm.name} onChange={v => setUForm({ ...uForm, name: v })} placeholder="Jane Smith" />
              <FormInput label="Email" value={uForm.email} onChange={v => setUForm({ ...uForm, email: v })} type="email" placeholder="jane@example.com" />
              <FormInput label="Password" value={uForm.password} onChange={v => setUForm({ ...uForm, password: v })} type="password" placeholder="••••••••" />
              <div><label className="block text-sm font-medium text-[#1C1612] mb-1.5">Role</label><select value={uForm.role} onChange={e => setUForm({ ...uForm, role: e.target.value })} className="w-full px-4 py-2.5 rounded-xl border border-white/50 bg-white/50 text-[#1C1612] text-sm focus:outline-none"><option value="user">User</option><option value="manager">Restaurant Manager</option></select></div>
              {uForm.role === "manager" && <p className="rounded-xl bg-amber-50 border border-amber-100 px-3 py-2 text-xs text-amber-700">Create the manager account here, then assign a restaurant from the Assign Manager tab.</p>}
              <button type="submit" className={btnCls}>Create User</button>
            </form>
          </GlassCard>
          <GlassCard hover={false}>
            <div className="p-5 border-b border-white/50"><h3 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>All Users ({users.length})</h3></div>
            <div className="divide-y divide-white/40">
              {users.map(u => (
                <div key={u.id} className="flex items-center gap-3 px-5 py-3 hover:bg-white/30 transition-colors">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#C4621D] to-[#E8943A] flex items-center justify-center text-white text-xs font-bold flex-shrink-0">{u.name.charAt(0)}</div>
                  <div className="flex-1 min-w-0"><p className="text-sm font-medium text-[#1C1612]">#{u.id} · {u.name}</p><p className="text-xs text-[#7A6E64] truncate">{u.email}{u.managed_restaurant_id ? ` · Restaurant #${u.managed_restaurant_id}` : ""}</p></div>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${ROLE_COLORS[u.role]}`}>{u.role}</span>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      )}

      {tab === "restaurants" && (
        <GlassCard className="p-6 max-w-2xl" hover={false}>
          <h3 className="font-semibold text-[#1C1612] mb-5" style={{ fontFamily: "'Playfair Display', serif" }}>Add Restaurant</h3>
          <form onSubmit={async e => { e.preventDefault(); try { const api = createApi(auth.apiBaseUrl, auth.token); const d = await api.post("/admin/restaurants", { restaurant_name: rForm.name, city: rForm.city || null, locality: rForm.locality || null, address: rForm.address || null, cuisines: rForm.cuisines.split(",").map(s => s.trim()).filter(Boolean), average_cost_inr: rForm.avg_cost ? Number(rForm.avg_cost) : null, price_range: rForm.price_range ? Number(rForm.price_range) : null, aggregate_rating: rForm.rating ? Number(rForm.rating) : null, votes: rForm.votes ? Number(rForm.votes) : null, has_online_delivery: rForm.online_delivery ? "Yes" : "No", has_table_booking: rForm.table_booking ? "Yes" : "No" }); showToast(`Restaurant #${d.restaurant_id} added`, "success"); setRForm({ name: "", city: "", locality: "", address: "", cuisines: "", avg_cost: "", price_range: "1", rating: "", votes: "", online_delivery: false, table_booking: false }); } catch (err: any) { showToast(err.message || "Unable to add restaurant", "error"); } }} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormInput label="Restaurant Name" value={rForm.name} onChange={v => setRForm({ ...rForm, name: v })} placeholder="Spice Garden" />
              <FormInput label="City" value={rForm.city} onChange={v => setRForm({ ...rForm, city: v })} placeholder="Mumbai" />
              <FormInput label="Locality" value={rForm.locality} onChange={v => setRForm({ ...rForm, locality: v })} placeholder="Bandra" />
              <FormInput label="Average Cost (₹)" value={rForm.avg_cost} onChange={v => setRForm({ ...rForm, avg_cost: v })} type="number" placeholder="800" />
              <FormInput label="Rating" value={rForm.rating} onChange={v => setRForm({ ...rForm, rating: v })} type="number" placeholder="4.2" />
              <FormInput label="Votes" value={rForm.votes} onChange={v => setRForm({ ...rForm, votes: v })} type="number" placeholder="2341" />
            </div>
            <FormInput label="Address" value={rForm.address} onChange={v => setRForm({ ...rForm, address: v })} placeholder="42 Hill Road, Bandra West" />
            <FormInput label="Cuisines" value={rForm.cuisines} onChange={v => setRForm({ ...rForm, cuisines: v })} placeholder="Indian, Chinese" />
            <div className="flex gap-6">{[["online_delivery", "Online Delivery"], ["table_booking", "Table Booking"]].map(([k, l]) => <label key={k} className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={(rForm as any)[k]} onChange={e => setRForm({ ...rForm, [k]: e.target.checked })} className="rounded accent-[#C4621D]" /><span className="text-sm">{l}</span></label>)}</div>
            <button type="submit" className={btnCls}>Add Restaurant</button>
          </form>
        </GlassCard>
      )}

      {tab === "assign" && (
        <GlassCard className="p-6 max-w-md" hover={false}>
          <h3 className="font-semibold text-[#1C1612] mb-5" style={{ fontFamily: "'Playfair Display', serif" }}>Assign Manager to Restaurant</h3>
          <form onSubmit={async e => { e.preventDefault(); if (!aForm.manager_id || !aForm.restaurant_id) { showToast("Select a manager and enter a restaurant ID", "error"); return; } try { const api = createApi(auth.apiBaseUrl, auth.token); const d = await api.post("/admin/assign-manager", { manager_user_id: Number(aForm.manager_id), restaurant_id: Number(aForm.restaurant_id) }); showToast(`Manager #${d.user_id} assigned to restaurant #${d.managed_restaurant_id}`, "success"); setAForm({ manager_id: "", restaurant_id: "" }); loadUsers(); } catch (err: any) { showToast(err.message || "Unable to assign manager", "error"); } }} className="space-y-4">
            <div><label className="block text-sm font-medium text-[#1C1612] mb-1.5">Manager Account</label><select value={aForm.manager_id} onChange={e => setAForm({ ...aForm, manager_id: e.target.value })} className="w-full px-4 py-2.5 rounded-xl border border-white/50 bg-white/50 text-[#1C1612] text-sm focus:outline-none"><option value="">Select manager/user</option>{users.filter(u => u.role !== "admin").map(u => <option key={u.id} value={u.id}>#{u.id} · {u.name} ({u.role})</option>)}</select></div>
            <FormInput label="Restaurant ID" value={aForm.restaurant_id} onChange={v => setAForm({ ...aForm, restaurant_id: v })} type="number" placeholder="1" />
            <button type="submit" className={btnCls}>Assign Manager</button>
          </form>
        </GlassCard>
      )}

      {tab === "import" && (
        <GlassCard className="p-6 max-w-md" hover={false}>
          <h3 className="font-semibold text-[#1C1612] mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>Import Dataset</h3>
          <p className="text-[#7A6E64] text-sm mb-5">Load the cleaned CSV into PostgreSQL using <code className="text-xs bg-white/60 px-1.5 py-0.5 rounded">POST /restaurants/import</code>.</p>
          <motion.div whileHover={{ borderColor: "#C4621D" }} className="border-2 border-dashed border-white/50 rounded-2xl p-10 text-center cursor-pointer transition-all">
            <Upload size={30} className="mx-auto text-[#7A6E64] mb-3" />
            <p className="text-sm font-medium text-[#1C1612]">Drop your CSV file here</p>
            <p className="text-xs text-[#7A6E64] mt-1">or click to browse</p>
          </motion.div>
          <button onClick={async () => { try { const api = createApi(auth.apiBaseUrl, auth.token); const d = await api.post("/restaurants/import"); showToast(`Imported ${d.restaurants_imported} restaurants and ${d.cuisines_imported} cuisines`, "success"); } catch (err: any) { showToast(err.message || "Unable to import dataset", "error"); } }} className={`mt-4 ${btnCls}`}>Import Dataset</button>
        </GlassCard>
      )}
    </div>
  );
}

function ManagerPanel({ auth }: { auth: AuthState }) {
  type Tab = "restaurant" | "menu";
  const [tab, setTab] = useState<Tab>("restaurant");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const showToast = (msg: string, type: "success" | "error" | "info" = "success") => setToast({ message: msg, type });
  const rid = auth.user.managed_restaurant_id;
  const emptyRestaurantForm = { name: "", city: "", locality: "", address: "", cuisines: "", avg_cost: "", price_range: "", rating: "", votes: "", online_delivery: false, table_booking: false };
  const [rForm, setRForm] = useState(emptyRestaurantForm);
  const [loadingRestaurant, setLoadingRestaurant] = useState(false);
  const [mForm, setMForm] = useState({ name: "", category: "", price: "", description: "", available: true });
  const [menuPhoto, setMenuPhoto] = useState<File | null>(null);
  const [menu, setMenu] = useState<{ id: number; name: string; category: string; price: number; description: string; available: boolean; image: string }[]>([]);
  const btnCls = "w-full py-2.5 bg-gradient-to-r from-[#C4621D] to-[#E8943A] text-white rounded-xl text-sm font-medium shadow-md hover:shadow-lg transition-all";

  useEffect(() => {
    if (!rid) {
      setRForm(emptyRestaurantForm);
      setMenu([]);
      return;
    }

    let active = true;
    const api = createApi(auth.apiBaseUrl, auth.token);
    const loadAssignedRestaurant = async () => {
      setLoadingRestaurant(true);
      try {
        const restaurant = await api.get(`/restaurants/${rid}`);
        if (!active) return;
        setRForm({
          name: restaurant.restaurant_name || "",
          city: restaurant.city || "",
          locality: restaurant.locality || "",
          address: restaurant.address || "",
          cuisines: Array.isArray(restaurant.cuisines) ? restaurant.cuisines.join(", ") : "",
          avg_cost: restaurant.average_cost_inr != null ? String(restaurant.average_cost_inr) : "",
          price_range: restaurant.price_range != null ? String(restaurant.price_range) : "",
          rating: restaurant.aggregate_rating != null ? String(restaurant.aggregate_rating) : "",
          votes: restaurant.votes != null ? String(restaurant.votes) : "",
          online_delivery: String(restaurant.has_online_delivery || "").toLowerCase() === "yes",
          table_booking: String(restaurant.has_table_booking || "").toLowerCase() === "yes",
        });

        const items = await api.get(`/manager/restaurants/${rid}/menu-items`);
        if (!active) return;
        setMenu((Array.isArray(items) ? items : []).map((item: any) => ({
          id: Number(item.menu_item_id),
          name: item.item_name || "Menu Item",
          category: item.category || "Uncategorized",
          price: Number(item.price_inr || 0),
          description: item.description || "",
          available: item.is_available !== false,
          image: item.photo_url || "1567620905732-5e91f4cd42c5",
        })));
      } catch (err: any) {
        if (active) showToast(err.message || "Unable to load assigned restaurant", "error");
      } finally {
        if (active) setLoadingRestaurant(false);
      }
    };

    loadAssignedRestaurant();
    return () => { active = false; };
  }, [rid, auth.apiBaseUrl, auth.token]);

  if (!rid) {
    return (
      <GlassCard className="p-8 max-w-2xl" hover={false}>
        <h3 className="font-semibold text-[#1C1612] mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>No Restaurant Assigned</h3>
        <p className="text-sm text-[#7A6E64] leading-relaxed">This manager account is active, but an admin has not assigned a restaurant yet. Ask the admin to use the Assign Manager tab with this user ID: <span className="font-semibold text-[#C4621D]">#{auth.user.id}</span>.</p>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-6">
      <AnimatePresence>{toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}</AnimatePresence>
      <div className="flex gap-1 p-1 bg-white/50 border border-white/60 rounded-2xl w-fit backdrop-blur-sm">
        {[{ id: "restaurant" as Tab, label: "Edit Restaurant" }, { id: "menu" as Tab, label: "Manage Menu" }].map(t => <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${tab === t.id ? "bg-white text-[#C4621D] shadow-sm" : "text-[#7A6E64] hover:text-[#1C1612]"}`}>{t.label}</button>)}
      </div>

      {tab === "restaurant" && (
        <GlassCard className="p-6 max-w-2xl" hover={false}>
          <h3 className="font-semibold text-[#1C1612] mb-5" style={{ fontFamily: "'Playfair Display', serif" }}>Edit Restaurant #{rid}</h3>
          {loadingRestaurant && <p className="mb-4 text-sm text-[#7A6E64]">Loading assigned restaurant details...</p>}
          <form onSubmit={async e => { e.preventDefault(); try { const api = createApi(auth.apiBaseUrl, auth.token); await api.patch(`/manager/restaurants/${rid}`, { restaurant_name: rForm.name, city: rForm.city || null, locality: rForm.locality || null, address: rForm.address || null, cuisines: rForm.cuisines.split(",").map(s => s.trim()).filter(Boolean), average_cost_inr: rForm.avg_cost ? Number(rForm.avg_cost) : null, price_range: rForm.price_range ? Number(rForm.price_range) : null, aggregate_rating: rForm.rating ? Number(rForm.rating) : null, votes: rForm.votes ? Number(rForm.votes) : null, has_online_delivery: rForm.online_delivery ? "Yes" : "No", has_table_booking: rForm.table_booking ? "Yes" : "No" }); showToast("Updated!", "success"); } catch (err: any) { showToast(err.message || "Unable to update restaurant", "error"); } }} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormInput label="Restaurant Name" value={rForm.name} onChange={v => setRForm({ ...rForm, name: v })} />
              <FormInput label="City" value={rForm.city} onChange={v => setRForm({ ...rForm, city: v })} />
              <FormInput label="Locality" value={rForm.locality} onChange={v => setRForm({ ...rForm, locality: v })} />
              <FormInput label="Average Cost (₹)" value={rForm.avg_cost} onChange={v => setRForm({ ...rForm, avg_cost: v })} type="number" />
              <FormInput label="Rating" value={rForm.rating} onChange={v => setRForm({ ...rForm, rating: v })} type="number" />
              <FormInput label="Votes" value={rForm.votes} onChange={v => setRForm({ ...rForm, votes: v })} type="number" />
            </div>
            <FormInput label="Address" value={rForm.address} onChange={v => setRForm({ ...rForm, address: v })} />
            <FormInput label="Cuisines" value={rForm.cuisines} onChange={v => setRForm({ ...rForm, cuisines: v })} />
            <div className="flex gap-6">{[["online_delivery", "Online Delivery"], ["table_booking", "Table Booking"]].map(([k, l]) => <label key={k} className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={(rForm as any)[k]} onChange={e => setRForm({ ...rForm, [k]: e.target.checked })} className="rounded accent-[#C4621D]" /><span className="text-sm">{l}</span></label>)}</div>
            <button type="submit" className={btnCls}>Save Changes</button>
          </form>
        </GlassCard>
      )}

      {tab === "menu" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <GlassCard className="p-6" hover={false}>
            <h3 className="font-semibold text-[#1C1612] mb-5" style={{ fontFamily: "'Playfair Display', serif" }}>Add Menu Item</h3>
            <form onSubmit={async e => { e.preventDefault(); try { const api = createApi(auth.apiBaseUrl, auth.token); const body = new FormData(); body.append("item_name", mForm.name); body.append("category", mForm.category); body.append("price_inr", mForm.price || "0"); body.append("description", mForm.description); body.append("is_available", String(mForm.available)); if (menuPhoto) body.append("photo", menuPhoto); const d = await api.post(`/manager/restaurants/${rid}/menu-items`, body); setMenu(p => [...p, { id: d.menu_item_id || Date.now(), name: d.item_name, category: d.category || mForm.category, price: Number(d.price_inr || mForm.price || 0), description: d.description || mForm.description, available: d.is_available, image: d.photo_url || "1567620905732-5e91f4cd42c5" }]); showToast("Item added!", "success"); setMForm({ name: "", category: "", price: "", description: "", available: true }); setMenuPhoto(null); } catch (err: any) { showToast(err.message || "Unable to add menu item", "error"); } }} className="space-y-4">
              <FormInput label="Item Name" value={mForm.name} onChange={v => setMForm({ ...mForm, name: v })} placeholder="Butter Chicken" />
              <FormInput label="Category" value={mForm.category} onChange={v => setMForm({ ...mForm, category: v })} placeholder="Main Course" />
              <FormInput label="Price (₹)" value={mForm.price} onChange={v => setMForm({ ...mForm, price: v })} type="number" placeholder="340" />
              <FormInput label="Description" value={mForm.description} onChange={v => setMForm({ ...mForm, description: v })} placeholder="A short description…" />
              <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={mForm.available} onChange={e => setMForm({ ...mForm, available: e.target.checked })} className="rounded accent-[#C4621D]" /><span className="text-sm">Available</span></label>
              <label className="block border-2 border-dashed border-white/50 rounded-xl p-4 text-center cursor-pointer transition-all hover:border-[#C4621D]"><Upload size={18} className="mx-auto text-[#7A6E64] mb-1" /><p className="text-xs text-[#7A6E64]">{menuPhoto ? menuPhoto.name : "Upload dish photo"}</p><input type="file" accept="image/*" className="hidden" onChange={e => setMenuPhoto(e.target.files?.[0] || null)} /></label>
              <button type="submit" className={btnCls}>Add Menu Item</button>
            </form>
          </GlassCard>
          <div className="space-y-3">
            <h3 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>Menu Preview ({menu.length} items)</h3>
            {menu.map((item, i) => (
              <motion.div key={item.id} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}>
                <GlassCard className="flex items-center gap-4 p-4">
                  <div className="w-14 h-14 rounded-xl overflow-hidden bg-amber-100 flex-shrink-0"><img src={item.image.startsWith("/") ? `${auth.apiBaseUrl.replace(/\/+$/, "")}${item.image}` : `https://images.unsplash.com/photo-${item.image}?w=100&h=100&fit=crop&auto=format`} alt={item.name} className="w-full h-full object-cover" /></div>
                  <div className="flex-1 min-w-0"><p className="text-sm font-semibold text-[#1C1612]">{item.name}</p><p className="text-xs text-[#7A6E64]">{item.category} · ₹{item.price}</p><p className="text-xs text-[#7A6E64]/70 mt-0.5 truncate">{item.description}</p></div>
                  <div className="flex flex-col items-end gap-2 flex-shrink-0">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${item.available ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>{item.available ? "Available" : "Unavailable"}</span>
                    <button className="p-1.5 rounded-lg bg-white/50 text-[#7A6E64] hover:text-[#C4621D] transition-colors"><Edit2 size={12} /></button>
                  </div>
                </GlassCard>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ReportsPage({ auth }: { auth: AuthState }) {
  const REPORTS = [
    { title: "Rating Prediction Report", desc: "ML model predictions and confidence scores", icon: TrendingUp, color: "from-orange-400 to-amber-500", type: "PDF" },
    { title: "Feature Importance Report", desc: "Key factors influencing restaurant ratings", icon: BarChart2, color: "from-green-400 to-emerald-500", type: "PDF" },
    { title: "Location Analysis Report", desc: "Geographic distribution and density maps", icon: Map, color: "from-blue-400 to-indigo-500", type: "PDF" },
    { title: "Recommendation History", desc: "Your past recommendation sessions", icon: Search, color: "from-purple-400 to-violet-500", type: "JSON" },
    { title: "City Statistics CSV", desc: "Restaurant counts, ratings, costs by city", icon: FileText, color: "from-orange-400 to-amber-500", type: "CSV" },
    { title: "Cuisine Statistics CSV", desc: "Cuisine distribution and popularity data", icon: ChefHat, color: "from-red-400 to-rose-500", type: "CSV" },
    { title: "Model Metrics CSV", desc: "MAE, RMSE, R² scores for all models", icon: Settings, color: "from-gray-500 to-slate-600", type: "CSV" },
  ];

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h2 className="text-xl font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>Saved Reports</h2>
        <p className="text-[#7A6E64] text-sm mt-1">Download analysis outputs and data exports.</p>
      </motion.div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {REPORTS.map((r, i) => {
          const Icon = r.icon;
          return (
            <motion.div key={r.title} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}>
              <GlassCard className="p-5">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${r.color} flex items-center justify-center mb-4 shadow-md`}><Icon size={17} className="text-white" /></div>
                <h3 className="font-semibold text-[#1C1612] text-sm mb-1">{r.title}</h3>
                <p className="text-[#7A6E64] text-xs mb-4 leading-relaxed">{r.desc}</p>
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 bg-white/60 text-[#7A6E64] text-xs rounded-full font-medium border border-white/60">{r.type}</span>
                  <motion.button whileHover={{ x: 2 }} className="flex items-center gap-1.5 text-xs font-medium text-[#C4621D] hover:text-[#a0511a] transition-colors"><Download size={12} /> Download</motion.button>
                </div>
              </GlassCard>
            </motion.div>
          );
        })}
      </div>
      <GlassCard hover={false}>
        <div className="p-5 border-b border-white/50"><h3 className="font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>Recent Activity</h3></div>
        <div className="divide-y divide-white/40">
          {[{ action: "Generated rating prediction report", time: "Today, 2:34 PM" }, { action: "Ran recommendation search (Mumbai, Indian)", time: "Today, 1:12 PM" }, { action: "Exported city statistics CSV", time: "Yesterday, 4:20 PM" }, { action: "Viewed location analysis for Delhi", time: "Yesterday, 11:05 AM" }].map((a, i) => (
            <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.06 }} className="flex items-center gap-3 px-5 py-3 hover:bg-white/30 transition-colors">
              <span className="w-2 h-2 rounded-full bg-[#C4621D] flex-shrink-0" />
              <div className="flex-1"><p className="text-sm text-[#1C1612]">{a.action}</p><p className="text-xs text-[#7A6E64] mt-0.5">{a.time}</p></div>
            </motion.div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}

function LoginPage({ onAuth }: { onAuth: (a: AuthState) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [apiUrl, setApiUrl] = useState("http://127.0.0.1:8000");
  const [meta, setMeta] = useState<AppMetadata | null>(null);
  const [login, setLogin] = useState({ email: "", password: "" });
  const [reg, setReg] = useState({ name: "", email: "", password: "", role: "user" as Role, managed_restaurant_id: "" });

  useEffect(() => {
    let active = true;
    const api = createApi(apiUrl, null);
    api.get("/metadata/recommendations")
      .then(data => { if (active) setMeta(data); })
      .catch(() => { if (active) setMeta(null); });
    return () => { active = false; };
  }, [apiUrl]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true); setMsg(null);
    try {
      const res = await fetch(`${apiUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(login),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Invalid email or password");
      const user = toAppUser(data);
      onAuth({ user, token: String(user.id), apiBaseUrl: apiUrl });
    } catch (err: any) {
      setMsg({ text: err.message || "Unable to login. Check backend and credentials.", ok: false });
    }
    setLoading(false);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true); setMsg(null);
    try {
      const res = await fetch(`${apiUrl}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...reg, managed_restaurant_id: reg.managed_restaurant_id ? parseInt(reg.managed_restaurant_id) : null }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Unable to create account");
      setMsg({ text: "Account created! Please sign in.", ok: true });
      setTimeout(() => { setMode("login"); setMsg(null); }, 1800);
    } catch (err: any) {
      setMsg({ text: err.message || "Unable to create account.", ok: false });
    }
    setLoading(false);
  };
  return (
    <div className="min-h-screen flex relative overflow-hidden" style={{ fontFamily: "'DM Sans', sans-serif" }}>
      <div className="absolute inset-0 bg-gradient-to-br from-[#FFF8EF] via-[#FFF1DC] to-[#FFE0B2]" />
      {[{ top: "-10%", right: "-5%", size: 500, img: "1414235077428-338989a2e8c0" }, { bottom: "-5%", left: "-5%", size: 380, img: "1504674900247-0877df9cc836" }].map((b, i) => (
        <motion.div key={i} className="absolute rounded-full overflow-hidden pointer-events-none"
          style={{ top: (b as any).top, right: (b as any).right, left: (b as any).left, bottom: (b as any).bottom, width: b.size, height: b.size }}
          animate={{ y: [0, -15, 0] }} transition={{ duration: 8 + i * 2, repeat: Infinity, ease: "easeInOut" }}>
          <img src={`https://images.unsplash.com/photo-${b.img}?w=600&h=600&fit=crop&auto=format`} alt="" className="w-full h-full object-cover opacity-[0.22] blur-2xl" />
        </motion.div>
      ))}

      <div className="hidden lg:flex lg:w-[52%] relative flex-col justify-end p-14">
        <div className="absolute inset-4 rounded-3xl overflow-hidden">
          <img src="https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1200&h=900&fit=crop&auto=format" alt="Restaurant" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-br from-[#1C1612]/78 via-[#1C1612]/42 to-[#C4621D]/52" />
        </div>
        <div className="relative z-10">
          <motion.div className="flex items-center gap-3 mb-10" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-[#C4621D] to-[#E8943A] flex items-center justify-center shadow-lg"><ChefHat size={22} className="text-white" /></div>
            <span className="text-2xl text-white font-semibold" style={{ fontFamily: "'Playfair Display', serif" }}>Restaurant Intelligence</span>
          </motion.div>
          <motion.h2 className="text-5xl text-white font-semibold leading-[1.12] mb-5" style={{ fontFamily: "'Playfair Display', serif" }} initial={{ opacity: 0, y: 25 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            Taste the data<br />behind every<br /><span className="text-[#E8943A]">great restaurant.</span>
          </motion.h2>
          <motion.p className="text-white/60 text-lg max-w-md leading-relaxed" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>AI-powered recommendations, location analytics, and rating predictions.</motion.p>
          <motion.div className="flex flex-wrap gap-3 mt-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
            {[`${formatCount(meta?.restaurant_count ?? 9551)} Restaurants`, "FastAPI + PostgreSQL", "ML-Powered", "3 Roles"].map(tag => <span key={tag} className="px-3 py-1.5 rounded-full bg-white/15 border border-white/25 text-white/80 text-xs font-medium backdrop-blur-sm">{tag}</span>)}
          </motion.div>
        </div>
      </div>

      <div className="relative flex-1 flex items-center justify-center p-8">
        <motion.div className="w-full max-w-md" initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5 }}>
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#C4621D] to-[#E8943A] flex items-center justify-center"><ChefHat size={16} className="text-white" /></div>
            <span className="text-xl font-semibold text-[#1C1612]" style={{ fontFamily: "'Playfair Display', serif" }}>Restaurant Intelligence</span>
          </div>

          <div className="bg-white/60 backdrop-blur-2xl border border-white/70 rounded-3xl p-8 shadow-[0_20px_60px_rgba(196,98,29,0.12)]">
            <h2 className="text-2xl font-semibold text-[#1C1612] mb-1" style={{ fontFamily: "'Playfair Display', serif" }}>{mode === "login" ? "Welcome back" : "Create account"}</h2>
            <p className="text-[#7A6E64] text-sm mb-6">{mode === "login" ? "Sign in to your intelligence dashboard." : "Join the Restaurant Intelligence platform."}</p>

            <div className="flex gap-1 mb-6 p-1 bg-white/40 border border-white/50 rounded-xl">
              {(["login", "register"] as const).map(m => <button key={m} onClick={() => { setMode(m); setMsg(null); }} className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${mode === m ? "bg-white text-[#C4621D] shadow-sm" : "text-[#7A6E64] hover:text-[#1C1612]"}`}>{m === "login" ? "Sign In" : "Register"}</button>)}
            </div>

            {msg && <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className={`mb-4 p-3 rounded-xl text-sm border ${msg.ok ? "bg-green-50 text-green-700 border-green-200" : "bg-red-50 text-red-700 border-red-200"}`}>{msg.text}</motion.div>}

            {mode === "login" ? (
              <form onSubmit={handleLogin} className="space-y-4">
                <FormInput label="Email address" value={login.email} onChange={v => setLogin({ ...login, email: v })} type="email" placeholder="you@example.com" />
                <FormInput label="Password" value={login.password} onChange={v => setLogin({ ...login, password: v })} type="password" placeholder="••••••••" />
                <div>
                  <label className="block text-sm font-medium text-[#1C1612] mb-1.5">FastAPI Base URL</label>
                  <input type="url" value={apiUrl} onChange={e => setApiUrl(e.target.value)} className="w-full px-4 py-2.5 rounded-xl border border-white/50 bg-white/50 text-[#1C1612] text-sm focus:outline-none focus:border-[#C4621D]/50 focus:ring-2 focus:ring-[#C4621D]/15 transition-all" placeholder="http://localhost:8000" />
                  <p className="text-xs text-[#7A6E64] mt-1">Your FastAPI backend URL. Start the backend before signing in.</p>
                </div>
                <motion.button type="submit" disabled={loading} whileTap={{ scale: 0.97 }} className="w-full py-3 bg-gradient-to-r from-[#C4621D] to-[#E8943A] text-white rounded-xl font-medium shadow-lg shadow-orange-200 hover:shadow-xl transition-all disabled:opacity-60">{loading ? "Signing in…" : "Sign In"}</motion.button>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="space-y-4">
                <FormInput label="Full name" value={reg.name} onChange={v => setReg({ ...reg, name: v })} placeholder="Jane Smith" />
                <FormInput label="Email address" value={reg.email} onChange={v => setReg({ ...reg, email: v })} type="email" placeholder="jane@example.com" />
                <FormInput label="Password" value={reg.password} onChange={v => setReg({ ...reg, password: v })} type="password" placeholder="••••••••" />
                <div><label className="block text-sm font-medium text-[#1C1612] mb-1.5">Role</label><select value={reg.role} onChange={e => setReg({ ...reg, role: e.target.value as Role })} className="w-full px-4 py-2.5 rounded-xl border border-white/50 bg-white/50 text-[#1C1612] text-sm focus:outline-none"><option value="user">User</option><option value="manager">Restaurant Manager</option><option value="admin">Admin</option></select></div>
                {reg.role === "manager" && <FormInput label="Managed Restaurant ID" value={reg.managed_restaurant_id} onChange={v => setReg({ ...reg, managed_restaurant_id: v })} type="number" placeholder="1" />}
                <motion.button type="submit" disabled={loading} whileTap={{ scale: 0.97 }} className="w-full py-3 bg-gradient-to-r from-[#C4621D] to-[#E8943A] text-white rounded-xl font-medium shadow-lg shadow-orange-200 hover:shadow-xl transition-all disabled:opacity-60">{loading ? "Creating…" : "Create Account"}</motion.button>
              </form>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}

export default function App() {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [page, setPage] = useState("dashboard");

  if (!auth) return <LoginPage onAuth={a => { setAuth(a); setPage("dashboard"); }} />;

  const renderPage = () => {
    switch (page) {
      case "dashboard": return <DashboardPage auth={auth} setPage={setPage} />;
      case "recommendations": return <RecommendationsPage auth={auth} />;
      case "location": return <LocationPage auth={auth} />;
      case "rating": return <RatingPage auth={auth} />;
      case "admin": return auth.user.role === "admin" ? <AdminPanel auth={auth} /> : <p className="py-20 text-center text-[#7A6E64]">Access denied.</p>;
      case "manager": return ["manager", "admin"].includes(auth.user.role) ? <ManagerPanel auth={auth} /> : <p className="py-20 text-center text-[#7A6E64]">Access denied.</p>;
      case "reports": return <ReportsPage auth={auth} />;
      default: return <DashboardPage auth={auth} setPage={setPage} />;
    }
  };

  return (
    <div className="min-h-screen" style={{ fontFamily: "'DM Sans', sans-serif" }}>
      <AnimatedBackground />
      <HorizontalNav page={page} setPage={setPage} user={auth.user} onLogout={() => { setAuth(null); setPage("dashboard"); }} />
      <main className="max-w-[1400px] mx-auto px-5 py-7 pb-16">
        <AnimatePresence mode="wait">
          <motion.div key={page} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.22, ease: "easeOut" }}>
            {renderPage()}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

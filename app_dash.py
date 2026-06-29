import streamlit as st
import math
import json
import uuid
from datetime import datetime
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, Fullscreen, MiniMap
import base64

# ─────────────────────────────────────────────────────────────────────────────
# إعداد الصفحة
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="محلل شبكات السيول",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"About": None},
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

* { box-sizing: border-box; font-family: 'Cairo', sans-serif !important; }
html, body, [class*="css"] { direction: rtl; text-align: right; }
.stApp { background: #eef2f7; }

/* Header */
.main-header {
    background: linear-gradient(135deg, #0a2a5e 0%, #1a5fa8 60%, #2980d4 100%);
    color: white;
    padding: 30px 40px;
    border-radius: 16px;
    margin-bottom: 25px;
    box-shadow: 0 8px 30px rgba(10,42,94,0.25);
    text-align: center;
}
.main-header h1 { font-size: 2.4rem; font-weight: 900; margin: 0 0 6px 0; letter-spacing: 1px; }
.main-header p  { font-size: 1rem; margin: 0; opacity: 0.85; }

/* Step badges */
.step-badge {
    display: inline-block;
    background: #1a5fa8;
    color: white;
    border-radius: 50%;
    width: 36px; height: 36px;
    line-height: 36px;
    text-align: center;
    font-weight: 900;
    font-size: 1.1rem;
    margin-left: 10px;
    box-shadow: 0 2px 8px rgba(26,95,168,0.4);
}
.section-title {
    font-size: 1.5rem;
    font-weight: 900;
    color: #0a2a5e;
    border-right: 5px solid #1a5fa8;
    padding-right: 14px;
    margin: 20px 0 18px 0;
}

/* Cards */
.kpi-card {
    background: white;
    border-radius: 14px;
    padding: 20px 16px;
    text-align: center;
    border-top: 5px solid #1a5fa8;
    box-shadow: 0 4px 16px rgba(0,0,0,0.07);
    margin-bottom: 12px;
}
.kpi-value { font-size: 2.2rem; font-weight: 900; color: #0a2a5e; }
.kpi-label { font-size: 0.9rem; color: #6b7a99; font-weight: 700; margin-top: 4px; }

/* Workflow steps (home) */
.step-card {
    background: white;
    border-radius: 14px;
    padding: 28px 20px;
    text-align: center;
    border: 2px solid #d0e4f7;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    transition: transform 0.2s, box-shadow 0.2s;
    height: 100%;
}
.step-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(26,95,168,0.15); }
.step-icon { font-size: 2.8rem; margin-bottom: 12px; }
.step-title { font-size: 1.1rem; font-weight: 900; color: #0a2a5e; margin-bottom: 8px; }
.step-desc { font-size: 0.88rem; color: #6b7a99; line-height: 1.5; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #1a5fa8 0%, #0a2a5e 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 10px 20px !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }

/* Tab styling */
.stTabs [role="tab"] {
    font-weight: 700 !important;
    font-size: 0.95rem !important;
}

/* Info banner */
.info-banner {
    background: #e8f4fd;
    border-right: 4px solid #1a5fa8;
    border-radius: 8px;
    padding: 12px 16px;
    color: #0a2a5e;
    font-weight: 600;
    margin-bottom: 14px;
}

/* Table */
.stDataFrame { border-radius: 10px !important; overflow: hidden !important; }

/* Total cost row */
.total-row {
    background: #0a2a5e;
    color: white;
    border-radius: 10px;
    padding: 16px 24px;
    font-size: 1.4rem;
    font-weight: 900;
    text-align: center;
    margin-top: 16px;
    box-shadow: 0 4px 16px rgba(10,42,94,0.25);
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ثوابت
# ─────────────────────────────────────────────────────────────────────────────
PIPE_PRICES = {
    400: 454, 500: 619, 600: 725, 700: 906, 800: 1045,
    900: 1225, 1000: 1440, 1100: 1600, 1200: 1812,
    1300: 1920, 1400: 2132,
}

PIPE_COLORS = {
    400: "#2196F3", 500: "#4CAF50", 600: "#FF9800",
    700: "#9C27B0", 800: "#F44336", 900: "#00BCD4",
    1000: "#FF5722", 1100: "#795548", 1200: "#607D8B",
    1300: "#E91E63", 1400: "#3F51B5",
}

MANHOLE_PRICE  = 3_000   # ريال / عدد
TRAP_PRICE     = 2_000   # ريال / عدد
EXCAVATION     = 50      # ريال / م
BACKFILL_PRICE = 30      # ريال / م³
TRAP_SPACING   = 35      # م

# ─────────────────────────────────────────────────────────────────────────────
# دوال مساعدة
# ─────────────────────────────────────────────────────────────────────────────
def haversine(c1, c2):
    R = 6_371_000
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def line_length(coords):
    return sum(haversine(coords[i], coords[i+1]) for i in range(len(coords)-1))

def num_traps(length):
    return max(1, round(length / TRAP_SPACING))

def get_bounds(coords):
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return [[min(lats)-0.002, min(lons)-0.002], [max(lats)+0.002, max(lons)+0.002]]

def center_of(coords):
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return [(min(lats)+max(lats))/2, (min(lons)+max(lons))/2]

# ─────────────────────────────────────────────────────────────────────────────
# محلل الشبكة
# ─────────────────────────────────────────────────────────────────────────────
class NetworkAnalyzer:
    def __init__(self, lines):
        self.lines = [ln for ln in lines if ln.get("selected", True)]
        self.G = nx.Graph()
        self.edges_list = []
        self.nodes_coords = {}
        self._build()

    def _build(self):
        nid = 0
        for line in self.lines:
            coords = line.get("coords", [])
            if len(coords) < 2:
                continue
            for i in range(len(coords)-1):
                s = tuple(coords[i][:2])
                e = tuple(coords[i+1][:2])
                for pt in (s, e):
                    if pt not in self.nodes_coords:
                        self.nodes_coords[pt] = nid
                        self.G.add_node(nid)
                        nid += 1
                dist = haversine(coords[i], coords[i+1])
                sn, en = self.nodes_coords[s], self.nodes_coords[e]
                self.G.add_edge(sn, en, distance=dist)
                self.edges_list.append({
                    "id": len(self.edges_list),
                    "start_coord": s,
                    "end_coord": e,
                    "distance": dist,
                    "line_name": line.get("name", "خط"),
                    "node_start": sn,
                    "node_end": en,
                    "diameter": 600,
                    "depth": 1.5,
                })

    def stats(self):
        return {
            "nodes": self.G.number_of_nodes(),
            "edges": len(self.edges_list),
            "length": sum(e["distance"] for e in self.edges_list),
            "components": nx.number_connected_components(self.G),
        }

# ─────────────────────────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────────────────────────
for key, val in [("lines", []), ("analyzer", None), ("cost", None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🌊 محلل شبكات السيول</h1>
    <p>تحليل متكامل وحساب دقيق لتكاليف شبكات الصرف السيلية</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# التبويبات الرئيسية بالترتيب المنطقي
# ─────────────────────────────────────────────────────────────────────────────
TAB_LABELS = [
    "🏠 الرئيسية",
    "🗺️ ١ · رسم وإدخال",
    "🌐 ٢ · تحليل الشبكة",
    "💰 ٣ · التكاليف",
    "📋 ٤ · التقرير والطباعة",
]
tabs = st.tabs(TAB_LABELS)

# ══════════════════════════════════════════════════════════════════════════════
# التبويب 0: الرئيسية
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("<div class='section-title'>خطوات استخدام التطبيق</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    steps = [
        ("🗺️", "١ · رسم وإدخال", "ارسم خطوط الشبكة مباشرة على الخريطة أو استورد ملفات GeoJSON القياسية"),
        ("🌐", "٢ · تحليل الشبكة", "حلل المناهل والفروع والأطوال واعرضها على خريطة تفاعلية ملونة"),
        ("💰", "٣ · التكاليف", "أدخل قطر وعمق كل فرع ثم احسب كميات التربة والأنابيب والمناهل والتكلفة"),
        ("📋", "٤ · التقرير", "تصدير تقرير PDF كامل مع الخريطة وجداول الكميات والتكاليف"),
    ]
    for col, (icon, title, desc) in zip([c1, c2, c3, c4], steps):
        with col:
            st.markdown(f"""
            <div class="step-card">
                <div class="step-icon">{icon}</div>
                <div class="step-title">{title}</div>
                <div class="step-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ملخص الحالة
    st.markdown("<div class='section-title'>ملخص المشروع</div>", unsafe_allow_html=True)
    km1, km2, km3, km4 = st.columns(4)
    n_lines  = len(st.session_state.lines)
    n_nodes  = st.session_state.analyzer.stats()["nodes"] if st.session_state.analyzer else 0
    tot_km   = (st.session_state.analyzer.stats()["length"]/1000) if st.session_state.analyzer else 0.0
    tot_cost = st.session_state.cost["total_cost"] if st.session_state.cost else 0

    for col, val, lbl in zip(
        [km1, km2, km3, km4],
        [n_lines, n_nodes, f"{tot_km:.2f}", f"{tot_cost/1e6:.2f}M"],
        ["الخطوط المدخلة", "المناهل", "الطول الكلي (كم)", "التكلفة (ريال)"]
    ):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{val}</div>
                <div class="kpi-label">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# التبويب 1: رسم وإدخال
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("<div class='section-title'>🗺️ رسم وإدخال الشبكة</div>", unsafe_allow_html=True)

    sub1, sub2 = st.tabs(["✏️ رسم على الخريطة", "📤 استيراد GeoJSON"])

    # ── رسم ──────────────────────────────────────────────────────────────────
    with sub1:
        st.markdown("""
        <div class="info-banner">
            📌 استخدم أداة الرسم في أعلى يسار الخريطة لرسم خطوط الشبكة.
            انقر لإضافة نقاط ثم انقر مرتين لإنهاء الخط.
        </div>
        """, unsafe_allow_html=True)

        # تحديد مركز الخريطة
        if st.session_state.lines:
            all_c = [pt for ln in st.session_state.lines for pt in ln["coords"]]
            map_center = center_of(all_c)
            zoom = 14
        else:
            map_center = [24.7136, 46.6753]
            zoom = 12

        m_draw = folium.Map(location=map_center, zoom_start=zoom, tiles="OpenStreetMap")
        Fullscreen(title="ملء الشاشة").add_to(m_draw)
        MiniMap(toggle_display=True).add_to(m_draw)

        # رسم الخطوط الموجودة
        for ln in st.session_state.lines:
            coords = ln.get("coords", [])
            if coords:
                folium.PolyLine(
                    coords, color="#e63946", weight=4, opacity=0.9,
                    tooltip=ln["name"],
                    popup=folium.Popup(
                        f"<b>{ln['name']}</b><br>الطول: {ln['length']:.1f} م",
                        max_width=200
                    )
                ).add_to(m_draw)
                # نقطة البداية
                folium.CircleMarker(coords[0], radius=6, color="#0a2a5e",
                                    fill=True, fillColor="#1a5fa8", weight=2,
                                    popup="بداية").add_to(m_draw)
                # نقطة النهاية
                folium.CircleMarker(coords[-1], radius=6, color="#e63946",
                                    fill=True, fillColor="#e63946", weight=2,
                                    popup="نهاية").add_to(m_draw)

        draw_ctrl = Draw(
            export=False,
            position="topleft",
            draw_options={
                "polyline": {"shapeOptions": {"color": "#e63946", "weight": 4}},
                "polygon": False, "rectangle": False,
                "circle": False, "marker": False, "circlemarker": False,
            },
            edit_options={"remove": True},
        )
        draw_ctrl.add_to(m_draw)

        map_data = st_folium(m_draw, width=None, height=650, key="draw_map")

        # معالجة الرسم
        if map_data and map_data.get("last_active_drawing"):
            drawing = map_data["last_active_drawing"]
            geom = drawing.get("geometry", {})
            if geom.get("type") == "LineString":
                raw_coords = geom.get("coordinates", [])
                coords = [(c[1], c[0]) for c in raw_coords]
                if len(coords) >= 2:
                    length = line_length(coords)
                    # تجنب التكرار بالتحقق من آخر خط
                    is_dup = False
                    if st.session_state.lines:
                        last = st.session_state.lines[-1]
                        if abs(last["length"] - length) < 0.1:
                            is_dup = True
                    if not is_dup:
                        new_line = {
                            "id": str(uuid.uuid4()),
                            "name": f"خط {len(st.session_state.lines)+1}",
                            "length": length,
                            "coords": coords,
                            "selected": True,
                        }
                        st.session_state.lines.append(new_line)
                        st.session_state.analyzer = None
                        st.session_state.cost = None
                        st.success(f"✅ تمت إضافة {new_line['name']} — الطول: {length:.1f} م")
                        st.rerun()

        # قائمة الخطوط
        if st.session_state.lines:
            st.markdown("---")
            st.markdown("**الخطوط المدخلة:**")
            for i, ln in enumerate(st.session_state.lines):
                c1_, c2_, c3_ = st.columns([4, 2, 1])
                with c1_:
                    new_name = st.text_input("الاسم", value=ln["name"], key=f"name_{i}", label_visibility="collapsed")
                    st.session_state.lines[i]["name"] = new_name
                with c2_:
                    st.write(f"📏 {ln['length']:.1f} م")
                with c3_:
                    if st.button("🗑️", key=f"del_{i}"):
                        st.session_state.lines.pop(i)
                        st.session_state.analyzer = None
                        st.session_state.cost = None
                        st.rerun()

            if st.button("🗑️ حذف جميع الخطوط", use_container_width=True):
                st.session_state.lines = []
                st.session_state.analyzer = None
                st.session_state.cost = None
                st.rerun()

    # ── GeoJSON (تم استبدال geopandas بـ مكتبة json القياسية تماماً) ─────────
    with sub2:
        st.markdown("### استيراد ملف GeoJSON")
        uploaded_geojson = st.file_uploader("اختر ملف GeoJSON", type=["geojson", "json"], key="geo_up")
        if uploaded_geojson:
            try:
                gj = json.load(uploaded_geojson)
                features = gj.get("features", [])
                added = 0
                for idx, feat in enumerate(features):
                    geom = feat.get("geometry", {})
                    if geom.get("type") == "LineString":
                        coords = [(c[1], c[0]) for c in geom.get("coordinates", [])]
                        if len(coords) >= 2:
                            name = feat.get("properties", {}).get("name", f"خط {len(st.session_state.lines)+1}")
                            st.session_state.lines.append({
                                "id": str(uuid.uuid4()),
                                "name": name,
                                "length": line_length(coords),
                                "coords": coords,
                                "selected": True,
                            })
                            added += 1
                st.session_state.analyzer = None
                st.session_state.cost = None
                st.success(f"✅ تمت إضافة {added} خط من GeoJSON بنجاح!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ في قراءة ملف GeoJSON: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# التبويب 2: تحليل الشبكة
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("<div class='section-title'>🌐 تحليل الشبكة</div>", unsafe_allow_html=True)

    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً في الخطوة السابقة أولاً.")
    else:
        col_btn, col_sp = st.columns([1, 4])
        with col_btn:
            if st.button("🔍 تحليل الشبكة", use_container_width=True):
                with st.spinner("جاري التحليل..."):
                    st.session_state.analyzer = NetworkAnalyzer(st.session_state.lines)
                    st.session_state.cost = None
                st.success("✅ تم التحليل!")
                st.rerun()

        if st.session_state.analyzer:
            ana  = st.session_state.analyzer
            stat = ana.stats()

            # KPIs
            k1, k2, k3, k4 = st.columns(4)
            for col, val, lbl in zip(
                [k1, k2, k3, k4],
                [stat["nodes"], stat["edges"], f"{stat['length']/1000:.2f}", stat["components"]],
                ["المناهل (عقد)", "الفروع (حواف)", "الطول الكلي (كم)", "الأجزاء المتصلة"]
            ):
                with col:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-value">{val}</div>
                        <div class="kpi-label">{lbl}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("---")

            # جدول الفروع
            st.markdown("#### 📋 تفاصيل الفروع")
            rows = []
            for e in ana.edges_list:
                rows.append({
                    "الفرع": e["line_name"],
                    "الطول (م)": f"{e['distance']:.1f}",
                    "العقدة البداية": e["node_start"],
                    "العقدة النهاية": e["node_end"],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            st.markdown("---")

            # خريطة تحليل الشبكة
            st.markdown("#### 🗺️ خريطة الشبكة التحليلية")
            st.markdown("""
            <div class="info-banner">
                🔵 الخطوط الزرقاء = فروع الشبكة &nbsp;|&nbsp;
                🔴 الدوائر الحمراء = مناهل الشبكة
            </div>
            """, unsafe_allow_html=True)

            all_c = [pt for ln in st.session_state.lines for pt in ln["coords"]]
            mc    = center_of(all_c)
            bnds  = get_bounds(all_c)

            m_net = folium.Map(location=mc, zoom_start=14, tiles="CartoDB positron")
            Fullscreen(title="ملء الشاشة").add_to(m_net)
            MiniMap(toggle_display=True).add_to(m_net)

            # رسم الفروع بألوان حسب الترتيب
            edge_colors = ["#1a5fa8", "#e63946", "#2a9d8f", "#e9c46a",
                           "#f4a261", "#264653", "#6d6875", "#80b918"]
            for i, e in enumerate(ana.edges_list):
                color = edge_colors[i % len(edge_colors)]
                folium.PolyLine(
                    [e["start_coord"], e["end_coord"]],
                    color=color, weight=5, opacity=0.85,
                    tooltip=f"{e['line_name']} — {e['distance']:.1f} م",
                    popup=folium.Popup(
                        f"<b>{e['line_name']}</b><br>الطول: {e['distance']:.1f} م<br>"
                        f"العقد: {e['node_start']} ← {e['node_end']}",
                        max_width=220
                    )
                ).add_to(m_net)

            # رسم المناهل
            for coord, nid in ana.nodes_coords.items():
                degree = ana.G.degree(nid)
                # تمييز المناهل بحجم يعكس درجة الاتصال
                radius = 7 + degree * 2
                folium.CircleMarker(
                    location=coord,
                    radius=radius,
                    color="#0a2a5e", weight=2,
                    fill=True, fillColor="#e63946", fillOpacity=0.85,
                    tooltip=f"منهل #{nid} — درجة الاتصال: {degree}",
                    popup=folium.Popup(
                        f"<b>منهل #{nid}</b><br>درجة الاتصال: {degree}<br>"
                        f"إحداثيات: {coord[0]:.5f}, {coord[1]:.5f}",
                        max_width=220
                    )
                ).add_to(m_net)

            m_net.fit_bounds(bnds)
            st_folium(m_net, width=None, height=700, key="net_map")

# ══════════════════════════════════════════════════════════════════════════════
# التبويب 3: التكاليف
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("<div class='section-title'>💰 إعدادات وحساب التكاليف</div>", unsafe_allow_html=True)

    if not st.session_state.analyzer:
        st.warning("⚠️ حلل الشبكة في الخطوة السابقة أولاً.")
    else:
        ana = st.session_state.analyzer

        st.markdown("""
        <div class="info-banner">
            📌 أدخل القطر (مم) والعمق (م) لكل فرع ثم اضغط "احسب التكاليف"
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### إعداد الفروع")

        # رؤوس الجدول
        hc = st.columns([0.5, 2.5, 1.5, 2, 2])
        for col, txt in zip(hc, ["#", "اسم الفرع", "الطول (م)", "القطر (مم)", "العمق (م)"]):
            col.markdown(f"**{txt}**")
        st.markdown("---")

        for idx, edge in enumerate(ana.edges_list):
            cols = st.columns([0.5, 2.5, 1.5, 2, 2])
            cols[0].write(f"**{idx+1}**")
            cols[1].write(edge["line_name"])
            cols[2].write(f"{edge['distance']:.1f}")
            with cols[3]:
                d = st.selectbox(
                    "القطر", sorted(PIPE_PRICES.keys()),
                    index=list(sorted(PIPE_PRICES.keys())).index(edge.get("diameter", 600)),
                    key=f"dia_{idx}", label_visibility="collapsed"
                )
            with cols[4]:
                dp = st.number_input(
                    "العمق", min_value=0.5, max_value=10.0,
                    value=float(edge.get("depth", 1.5)), step=0.1,
                    key=f"dep_{idx}", label_visibility="collapsed"
                )
            ana.edges_list[idx]["diameter"] = d
            ana.edges_list[idx]["depth"]    = dp

        st.markdown("---")

        if st.button("🧮 احسب التكاليف", use_container_width=True):
            with st.spinner("جاري الحساب..."):
                all_items: dict = {}
                per_edge = []
                stat = ana.stats()
                total_len = stat["length"]

                for edge in ana.edges_list:
                    d   = edge["diameter"]
                    dep = edge["depth"]
                    L   = edge["distance"]
                    share    = L / total_len if total_len > 0 else 0
                    n_mh     = max(1, round(stat["nodes"] * share))
                    n_tr     = num_traps(L)
                    p_pipe   = PIPE_PRICES.get(d, 725)

                    items = [
                        {"البند": "أنابيب صرف (خرسانية)",
                         "الكمية": L, "الوحدة": "م",
                         "السعر": p_pipe, "الإجمالي": L * p_pipe},
                        {"البند": "حفر خنادق",
                         "الكمية": L, "الوحدة": "م",
                         "السعر": EXCAVATION, "الإجمالي": L * EXCAVATION},
                        {"البند": "مناهل تفتيش",
                         "الكمية": n_mh, "الوحدة": "عدد",
                         "السعر": MANHOLE_PRICE, "الإجمالي": n_mh * MANHOLE_PRICE},
                        {"البند": "مصائد رمل وحطام",
                         "الكمية": n_tr, "الوحدة": "عدد",
                         "السعر": TRAP_PRICE, "الإجمالي": n_tr * TRAP_PRICE},
                        {"البند": "ردم وتسوية",
                         "الكمية": L * dep, "الوحدة": "م³",
                         "السعر": BACKFILL_PRICE, "الإجمالي": L * dep * BACKFILL_PRICE},
                    ]

                    total = sum(it["الإجمالي"] for it in items)
                    per_edge.append({
                        "line_name": edge["line_name"],
                        "diameter": d, "depth": dep,
                        "length": L, "items": items,
                        "total": total,
                        "n_manholes": n_mh, "n_traps": n_tr,
                        "start_coord": edge["start_coord"],
                        "end_coord": edge["end_coord"],
                    })

                    for it in items:
                        k = it["البند"]
                        if k not in all_items:
                            all_items[k] = {"الكمية": 0, "الإجمالي": 0, "الوحدة": it["الوحدة"]}
                        all_items[k]["الكمية"]   += it["الكمية"]
                        all_items[k]["الإجمالي"] += it["الإجمالي"]

                total_cost = sum(v["الإجمالي"] for v in all_items.values())

                st.session_state.cost = {
                    "per_edge": per_edge,
                    "all_items": all_items,
                    "total_cost": total_cost,
                    "stat": stat,
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            st.success("✅ تم حساب التكاليف!")
            st.rerun()

        # عرض النتائج
        if st.session_state.cost:
            result = st.session_state.cost

            st.markdown("---")
            st.markdown("#### 📊 ملخص التكاليف الكلي")

            k1, k2, k3, k4 = st.columns(4)
            total_mh = sum(e["n_manholes"] for e in result["per_edge"])
            total_tr = sum(e["n_traps"]    for e in result["per_edge"])
            for col, val, lbl in zip(
                [k1, k2, k3, k4],
                [total_mh, total_tr, len(result["per_edge"]),
                 f"{result['total_cost']/1e6:.3f}M"],
                ["المناهل", "المصائد", "الفروع", "التكلفة الإجمالية (ريال)"]
            ):
                with col:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-value">{val}</div>
                        <div class="kpi-label">{lbl}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # جدول البنود
            st.markdown("#### 📋 جدول الكميات والتكاليف")
            rows = []
            for name, data in result["all_items"].items():
                rows.append({
                    "البند": name,
                    "الكمية": f"{data['الكمية']:,.2f}",
                    "الوحدة": data["الوحدة"],
                    "التكلفة (ريال)": f"{data['الإجمالي']:,.0f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            st.markdown(f"""
            <div class="total-row">
                💰 التكلفة الإجمالية للمشروع: {result['total_cost']:,.0f} ريال
            </div>
            """, unsafe_allow_html=True)

            # تفاصيل كل فرع
            with st.expander("📂 تفاصيل كل فرع على حدة"):
                for e in result["per_edge"]:
                    st.markdown(f"**{e['line_name']}** — قطر {e['diameter']} مم | عمق {e['depth']} م | طول {e['length']:.1f} م")
                    df_e = pd.DataFrame([
                        {"البند": it["البند"], "الكمية": f"{it['الكمية']:,.2f}",
                         "الوحدة": it["الوحدة"], "السعر/وحدة": f"{it['السعر']:,}",
                         "الإجمالي (ريال)": f"{it['الإجمالي']:,.0f}"}
                        for it in e["items"]
                    ])
                    st.dataframe(df_e, use_container_width=True, hide_index=True)
                    st.markdown(f"**إجمالي الفرع: {e['total']:,.0f} ريال**")
                    st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# التبويب 4: التقرير والطباعة
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown("<div class='section-title'>📋 التقرير والطباعة</div>", unsafe_allow_html=True)

    if not st.session_state.cost:
        st.warning("⚠️ احسب التكاليف في الخطوة السابقة أولاً.")
    else:
        result = st.session_state.cost
        ana    = st.session_state.analyzer

        rep_sub1, rep_sub2 = st.tabs(["🗺️ خريطة التقرير", "📥 تصدير PDF"])

        # ── خريطة التقرير ──────────────────────────────────────────────────
        with rep_sub1:
            st.markdown("""
            <div class="info-banner">
                🗺️ خريطة كاملة للشبكة مع معلومات كل فرع (القطر، العمق، التكلفة)
            </div>
            """, unsafe_allow_html=True)

            all_c = [pt for ln in st.session_state.lines for pt in ln["coords"]]
            mc    = center_of(all_c)
            bnds  = get_bounds(all_c)

            # الخريطة
            m_rep = folium.Map(location=mc, zoom_start=14,
                               tiles="OpenStreetMap")
            FullScreen(title="ملء الشاشة").add_to(m_rep)
            MiniMap(toggle_display=True).add_to(m_rep)

            # طبقة الأقمار الصناعية اختياري
            folium.TileLayer("CartoDB positron", name="خريطة فاتحة").add_to(m_rep)
            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri", name="صور فضائية"
            ).add_to(m_rep)
            folium.LayerControl(position="topright").add_to(m_rep)

            # رسم الفروع ملونة حسب القطر
            diameter_legend_added = set()
            for edge_r in result["per_edge"]:
                d     = edge_r["diameter"]
                color = PIPE_COLORS.get(d, "#1a5fa8")
                cost  = edge_r["total"]

                folium.PolyLine(
                    [edge_r["start_coord"], edge_r["end_coord"]],
                    color=color, weight=6, opacity=0.9,
                    tooltip=f"{edge_r['line_name']} | Ø{d}مم | {edge_r['length']:.1f}م",
                    popup=folium.Popup(
                        f"<div dir='rtl' style='font-family:Cairo,sans-serif;min-width:200px'>"
                        f"<b>{edge_r['line_name']}</b><br>"
                        f"القطر: {d} مم<br>"
                        f"العمق: {edge_r['depth']} م<br>"
                        f"الطول: {edge_r['length']:.1f} م<br>"
                        f"المناهل: {edge_r['n_manholes']}<br>"
                        f"المصائد: {edge_r['n_traps']}<br>"
                        f"<b>التكلفة: {cost:,.0f} ريال</b></div>",
                        max_width=250
                    )
                ).add_to(m_rep)
                diameter_legend_added.add(d)

            # رسم المناهل
            for coord, nid in ana.nodes_coords.items():
                deg = ana.G.degree(nid)
                folium.CircleMarker(
                    location=coord,
                    radius=8 + deg,
                    color="#0a2a5e", weight=2,
                    fill=True, fillColor="#e63946", fillOpacity=0.9,
                    tooltip=f"منهل #{nid}",
                    popup=folium.Popup(
                        f"<div dir='rtl'><b>منهل #{nid}</b><br>"
                        f"درجة الاتصال: {deg}</div>",
                        max_width=180
                    )
                ).add_to(m_rep)

            # مفتاح الألوان بالقطر
            legend_items = "".join([
                f"<div style='display:flex;align-items:center;margin:3px 0'>"
                f"<span style='display:inline-block;width:30px;height:6px;"
                f"background:{PIPE_COLORS.get(d,'#1a5fa8')};border-radius:3px;margin-left:8px'></span>"
                f"Ø{d} مم</div>"
                for d in sorted(diameter_legend_added)
            ])
            legend_html = f"""
            <div style="
                position:fixed; bottom:30px; right:30px; z-index:9999;
                background:white; padding:14px 18px; border-radius:10px;
                box-shadow:0 4px 14px rgba(0,0,0,0.15);
                font-family:'Cairo',sans-serif; direction:rtl; font-size:13px;
                border-top:4px solid #1a5fa8;
            ">
                <b style="color:#0a2a5e">مفتاح الأقطار</b><br><br>
                {legend_items}
                <hr style="margin:8px 0">
                <div style='display:flex;align-items:center;margin:3px 0'>
                <span style='display:inline-block;width:14px;height:14px;
                background:#e63946;border-radius:50%;margin-left:8px;border:2px solid #0a2a5e'></span>
                مناهل تفتيش</div>
            </div>
            """
            m_rep.get_root().html.add_child(folium.Element(legend_html))
            m_rep.fit_bounds(bnds)

            st_folium(m_rep, width=None, height=750, key="report_map")

        # ── تصدير PDF ──────────────────────────────────────────────────────
        with rep_sub2:
            st.markdown("### إنشاء وتحميل تقرير PDF")

            proj_name = st.text_input("اسم المشروع", value="مشروع شبكة صرف سيلي")
            proj_owner = st.text_input("الجهة المالكة", value="أمانة المنطقة")
            engineer   = st.text_input("المهندس المشرف", value="")

            if st.button("📥 إنشاء وتحميل التقرير PDF", use_container_width=True):
                with st.spinner("جاري إنشاء التقرير..."):
                    try:
                        from reportlab.lib.pagesizes import landscape, A4
                        from reportlab.lib import colors
                        from reportlab.lib.units import mm
                        from reportlab.platypus import (
                            SimpleDocTemplate, Table, TableStyle,
                            Paragraph, Spacer, HRFlowable, PageBreak
                        )
                        from reportlab.lib.styles import ParagraphStyle
                        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

                        buf = io.BytesIO()
                        doc = SimpleDocTemplate(
                            buf, pagesize=landscape(A4),
                            rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=15*mm, bottomMargin=15*mm,
                        )

                        BLUE  = colors.HexColor("#0a2a5e")
                        LBLUE = colors.HexColor("#1a5fa8")
                        GREY  = colors.HexColor("#f0f4f8")
                        WHITE = colors.white
                        RED   = colors.HexColor("#e63946")

                        s_title = ParagraphStyle("title",
                            fontName="Helvetica-Bold", fontSize=20,
                            textColor=WHITE, alignment=TA_CENTER, spaceAfter=4)
                        s_sub = ParagraphStyle("sub",
                            fontName="Helvetica", fontSize=11,
                            textColor=WHITE, alignment=TA_CENTER)
                        s_h2 = ParagraphStyle("h2",
                            fontName="Helvetica-Bold", fontSize=13,
                            textColor=BLUE, spaceBefore=10, spaceAfter=6)
                        s_normal = ParagraphStyle("normal",
                            fontName="Helvetica", fontSize=10,
                            textColor=colors.black)
                        s_footer = ParagraphStyle("footer",
                            fontName="Helvetica", fontSize=8,
                            textColor=colors.grey, alignment=TA_CENTER)

                        elems = []

                        # غلاف (جدول عريض كهيدر)
                        header_data = [[
                            Paragraph(f"FLOOD DRAINAGE NETWORK REPORT<br/><font size=11>{proj_name}</font>", s_title),
                        ]]
                        header_tbl = Table(header_data, colWidths=[260*mm])
                        header_tbl.setStyle(TableStyle([
                            ("BACKGROUND", (0,0), (-1,-1), BLUE),
                            ("TOPPADDING",    (0,0), (-1,-1), 18),
                            ("BOTTOMPADDING", (0,0), (-1,-1), 18),
                            ("LEFTPADDING",   (0,0), (-1,-1), 20),
                            ("RIGHTPADDING",  (0,0), (-1,-1), 20),
                            ("ROUNDEDCORNERS", (0,0), (-1,-1), [8,8,8,8]),
                        ]))
                        elems.append(header_tbl)
                        elems.append(Spacer(1, 8*mm))

                        # معلومات المشروع
                        info_data = [
                            ["Project Owner", proj_owner, "Date", result["generated_at"]],
                            ["Supervising Engineer", engineer or "—", "Version", "13.0"],
                        ]
                        info_tbl = Table(info_data, colWidths=[55*mm, 75*mm, 35*mm, 75*mm])
                        info_tbl.setStyle(TableStyle([
                            ("FONTNAME",  (0,0), (-1,-1), "Helvetica"),
                            ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
                            ("FONTNAME",  (2,0), (2,-1), "Helvetica-Bold"),
                            ("FONTSIZE",  (0,0), (-1,-1), 10),
                            ("GRID",      (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")),
                            ("BACKGROUND",(0,0), (0,-1), GREY),
                            ("BACKGROUND",(2,0), (2,-1), GREY),
                            ("TOPPADDING",    (0,0), (-1,-1), 5),
                            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                            ("LEFTPADDING",   (0,0), (-1,-1), 8),
                        ]))
                        elems.append(info_tbl)
                        elems.append(Spacer(1, 8*mm))

                        # ملخص المشروع
                        elems.append(Paragraph("1. PROJECT SUMMARY", s_h2))
                        total_mh = sum(e["n_manholes"] for e in result["per_edge"])
                        total_tr = sum(e["n_traps"]    for e in result["per_edge"])
                        stat     = result["stat"]

                        summary_data = [
                            ["Parameter", "Value", "Parameter", "Value"],
                            ["Total Network Length (km)",  f"{stat['length']/1000:.3f}", "Total Branches",   str(stat["edges"])],
                            ["Total Manholes",             str(total_mh),                "Total Traps",       str(total_tr)],
                            ["Connected Components",       str(stat["components"]),       "Network Nodes",     str(stat["nodes"])],
                            ["TOTAL PROJECT COST (SAR)",   f"{result['total_cost']:,.0f}", "", ""],
                        ]
                        sum_tbl = Table(summary_data, colWidths=[75*mm, 55*mm, 75*mm, 55*mm])
                        sum_style = [
                            ("FONTNAME",  (0,0), (-1,0), "Helvetica-Bold"),
                            ("BACKGROUND",(0,0), (-1,0), LBLUE),
                            ("TEXTCOLOR", (0,0), (-1,0), WHITE),
                            ("FONTNAME",  (0,1), (0,-1), "Helvetica-Bold"),
                            ("FONTNAME",  (2,1), (2,-1), "Helvetica-Bold"),
                            ("FONTSIZE",  (0,0), (-1,-1), 10),
                            ("GRID",      (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")),
                            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, GREY]),
                            ("TOPPADDING",    (0,0), (-1,-1), 5),
                            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                            ("LEFTPADDING",   (0,0), (-1,-1), 8),
                            # صف التكلفة الكلية
                            ("BACKGROUND",  (0,-1), (-1,-1), BLUE),
                            ("TEXTCOLOR",   (0,-1), (-1,-1), WHITE),
                            ("FONTNAME",    (0,-1), (-1,-1), "Helvetica-Bold"),
                            ("FONTSIZE",    (0,-1), (-1,-1), 12),
                            ("SPAN",        (1,-1), (-1,-1)),
                        ]
                        sum_tbl.setStyle(TableStyle(sum_style))
                        elems.append(sum_tbl)
                        elems.append(Spacer(1, 8*mm))

                        # جدول الكميات الكلية
                        elems.append(Paragraph("2. BILL OF QUANTITIES", s_h2))
                        boq_data = [["Item Description", "Quantity", "Unit", "Unit Price (SAR)", "Total (SAR)"]]
                        for name, d in result["all_items"].items():
                            unit_price = d["الإجمالي"] / d["الكمية"] if d["الكمية"] else 0
                            boq_data.append([
                                name,
                                f"{d['الكمية']:,.2f}",
                                d["الوحدة"],
                                f"{unit_price:,.0f}",
                                f"{d['الإجمالي']:,.0f}",
                            ])
                        # إجمالي
                        boq_data.append(["TOTAL", "", "", "", f"{result['total_cost']:,.0f}"])

                        boq_tbl = Table(boq_data, colWidths=[80*mm, 35*mm, 25*mm, 50*mm, 55*mm])
                        boq_style = [
                            ("FONTNAME",  (0,0), (-1,0), "Helvetica-Bold"),
                            ("BACKGROUND",(0,0), (-1,0), LBLUE),
                            ("TEXTCOLOR", (0,0), (-1,0), WHITE),
                            ("FONTSIZE",  (0,0), (-1,-1), 10),
                            ("GRID",      (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")),
                            ("ROWBACKGROUNDS", (0,1), (-1,-2), [WHITE, GREY]),
                            ("ALIGN",     (1,0), (-1,-1), "CENTER"),
                            ("TOPPADDING",    (0,0), (-1,-1), 5),
                            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                            ("LEFTPADDING",   (0,0), (-1,-1), 8),
                            # صف الإجمالي
                            ("BACKGROUND", (0,-1), (-1,-1), BLUE),
                            ("TEXTCOLOR",  (0,-1), (-1,-1), WHITE),
                            ("FONTNAME",   (0,-1), (-1,-1), "Helvetica-Bold"),
                            ("FONTSIZE",   (0,-1), (-1,-1), 11),
                        ]
                        boq_tbl.setStyle(TableStyle(boq_style))
                        elems.append(boq_tbl)

                        elems.append(PageBreak())

                        # تفاصيل الفروع
                        elems.append(Paragraph("3. BRANCH DETAILS", s_h2))
                        branch_data = [
                            ["Branch", "Length (m)", "Diameter (mm)", "Depth (m)",
                             "Manholes", "Traps", "Total Cost (SAR)"]
                        ]
                        for e in result["per_edge"]:
                            branch_data.append([
                                e["line_name"],
                                f"{e['length']:.1f}",
                                str(e["diameter"]),
                                str(e["depth"]),
                                str(e["n_manholes"]),
                                str(e["n_traps"]),
                                f"{e['total']:,.0f}",
                            ])

                        col_ws = [65*mm, 30*mm, 35*mm, 25*mm, 25*mm, 20*mm, 45*mm]
                        br_tbl = Table(branch_data, colWidths=col_ws, repeatRows=1)
                        br_style = [
                            ("FONTNAME",  (0,0), (-1,0), "Helvetica-Bold"),
                            ("BACKGROUND",(0,0), (-1,0), LBLUE),
                            ("TEXTCOLOR", (0,0), (-1,0), WHITE),
                            ("FONTSIZE",  (0,0), (-1,-1), 9),
                            ("GRID",      (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")),
                            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, GREY]),
                            ("ALIGN",     (1,0), (-1,-1), "CENTER"),
                            ("TOPPADDING",    (0,0), (-1,-1), 5),
                            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                            ("LEFTPADDING",   (0,0), (-1,-1), 8),
                        ]
                        br_tbl.setStyle(TableStyle(br_style))
                        elems.append(br_tbl)
                        elems.append(Spacer(1, 10*mm))

                        # تذييل
                        elems.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d0d8e8")))
                        elems.append(Spacer(1, 3*mm))
                        elems.append(Paragraph(
                            f"Flood Network Analyzer v13.0  |  Generated: {result['generated_at']}  |  Confidential",
                            s_footer
                        ))

                        doc.build(elems)
                        buf.seek(0)

                        st.download_button(
                            label="📥 تحميل التقرير PDF",
                            data=buf.getvalue(),
                            file_name=f"FloodNetwork_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                        st.success("✅ تم إنشاء التقرير! اضغط الزر أعلاه للتحميل.")

                    except ImportError:
                        st.error("❌ مكتبة reportlab غير مثبتة.")
                    except Exception as ex:
                        st.error(f"❌ خطأ في إنشاء التقرير: {ex}")

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#9aa4b8;font-size:0.85rem;padding:16px 0">
    🌊 محلل شبكات السيول — الإصدار 13.0 (نسخة السحاب الخفيفة)
    &nbsp;|&nbsp; الخطوات: رسم ← تحليل ← تكاليف ← تقرير
</div>
""", unsafe_allow_html=True)

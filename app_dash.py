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
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght=400;600;700;900&display=swap');

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

/* Workflow steps */
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

# خريطة مصطلحات البنود للترجمة في التقرير الإنجليزي
ITEM_TRANSLATIONS = {
    "أنابيب صرف (خرسانية)": "Concrete Drainage Pipes",
    "حفر خنادق": "Trench Excavation",
    "مناهل تفتيش": "Inspection Manholes",
    "مصائد رمل وحطام": "Sand & Debris Traps",
    "ردم وتسوية داخلية": "Internal Backfilling & Compaction"
}

PIPE_COLORS = {
    400: "#2196F3", 500: "#4CAF50", 600: "#FF9800",
    700: "#9C27B0", 800: "#F44336", 900: "#00BCD4",
    1000: "#FF5722", 1100: "#795548", 1200: "#607D8B",
    1300: "#E91E63", 1400: "#3F51B5",
}

MANHOLE_PRICE  = 3_000   # ريال سعودي / عدد
TRAP_PRICE     = 2_000   # ريال سعودي / عدد
EXCAVATION     = 50      # ريال سعودي / م
BACKFILL_PRICE = 30      # ريال سعودي / م³
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
            
            if line.get("reversed", False):
                coords = coords[::-1]

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
                    "id": line["id"],
                    "start_coord": s,
                    "end_coord": e,
                    "distance": dist,
                    "line_name": line.get("name", "Line"),
                    "node_start": sn,
                    "node_end": en,
                    "diameter": line.get("diameter", 600),
                    "depth": line.get("depth", 1.5),
                    "reversed": line.get("reversed", False)
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
    <p>تحليل متكامل وحساب دقيق لتكاليف شبكات الصرف السيلية بالريال السعودي (SAR)</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# التبويبات الرئيسية
# ─────────────────────────────────────────────────────────────────────────────
TAB_LABELS = [
    "🏠 الرئيسية",
    "🗺️ ١ · رسم وإدخل البيانات",
    "🌐 ٢ · تحليل الشبكة والتكاليف المدمج",
    "📋 ٣ · التقرير والطباعة (PDF)",
]
tabs = st.tabs(TAB_LABELS)

# ══════════════════════════════════════════════════════════════════════════════
# التبويب 0: الرئيسية
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("<div class='section-title'>خطوات استخدام التطبيق</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    steps = [
        ("🗺️", "1 · رسم وإدخال", "ارسم خطوط الشبكة مباشرة على الخريطة أو استورد ملفات GeoJSON القياسية"),
        ("🌐", "2 · التحليل والتكاليف", "شاهد الخريطة التحليلية، عدل اتجاه المصب، أدخل الأقطار، واحسب التكاليف بالريال السعودي"),
        ("📋", "3 · التقرير والطباعة", "تصدير تقرير PDF هندسي باللغة الإنجليزية يحتوي على خريطة المخطط التفصيلية للأقطار"),
    ]
    for col, (icon, title, desc) in zip([c1, c2, c3], steps):
        with col:
            st.markdown(f"""
            <div class="step-card">
                <div class="step-icon">{icon}</div>
                <div class="step-title">{title}</div>
                <div class="step-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>ملخص المشروع الحالي</div>", unsafe_allow_html=True)
    km1, km2, km3, km4 = st.columns(4)
    n_lines  = len(st.session_state.lines)
    n_nodes  = st.session_state.analyzer.stats()["nodes"] if st.session_state.analyzer else 0
    tot_km   = (st.session_state.analyzer.stats()["length"]/1000) if st.session_state.analyzer else 0.0
    tot_cost = st.session_state.cost["total_cost"] if st.session_state.cost else 0

    for col, val, lbl in zip(
        [km1, km2, km3, km4],
        [n_lines, n_nodes, f"{tot_km:.2f}", f"{tot_cost:,.0f} SAR"],
        ["الخطوط المدخلة", "المناهل", "الطول الكلي (كم)", "التكلفة (ريال سعودي)"]
    ):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{val}</div>
                <div class="kpi-label">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# التبويب 1: رسم وإدخل البيانات
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("<div class='section-title'>🗺️ رسم وإدخال الشبكة</div>", unsafe_allow_html=True)
    sub1, sub2 = st.tabs(["✏️ رسم على الخريطة", "📤 استيراد GeoJSON"])

    with sub1:
        st.markdown("""<div class="info-banner">📌 استخدم أداة الرسم في أعلى يسار الخريطة لرسم خطوط الشبكة. انقر لإضافة نقاط ثم انقر مرتين لإنهاء الخط.</div>""", unsafe_allow_html=True)
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

        for ln in st.session_state.lines:
            coords = ln.get("coords", [])
            if coords:
                folium.PolyLine(coords, color="#e63946", weight=4, opacity=0.9, tooltip=ln["name"]).add_to(m_draw)

        draw_ctrl = Draw(
            export=False, position="topleft",
            draw_options={"polyline": {"shapeOptions": {"color": "#e63946", "weight": 4}}, "polygon": False, "rectangle": False, "circle": False, "marker": False, "circlemarker": False},
            edit_options={"remove": True},
        )
        draw_ctrl.add_to(m_draw)
        map_data = st_folium(m_draw, width=None, height=500, key="draw_map")

        if map_data and map_data.get("last_active_drawing"):
            drawing = map_data["last_active_drawing"]
            geom = drawing.get("geometry", {})
            if geom.get("type") == "LineString":
                raw_coords = geom.get("coordinates", [])
                coords = [(c[1], c[0]) for c in raw_coords]
                if len(coords) >= 2:
                    length = line_length(coords)
                    is_dup = False
                    if st.session_state.lines:
                        last = st.session_state.lines[-1]
                        if abs(last["length"] - length) < 0.1:
                            is_dup = True
                    if not is_dup:
                        new_line = {
                            "id": str(uuid.uuid4()), "name": f"خط {len(st.session_state.lines)+1}", "length": length, "coords": coords, "selected": True, "diameter": 600, "depth": 1.5, "reversed": False
                        }
                        st.session_state.lines.append(new_line)
                        st.session_state.analyzer = None
                        st.session_state.cost = None
                        st.success(f"✅ تمت إضافة {new_line['name']}")
                        st.rerun()

    with sub2:
        uploaded_geojson = st.file_uploader("اختر ملف GeoJSON", type=["geojson", "json"], key="geo_up")
        if uploaded_geojson:
            try:
                gj = json.load(uploaded_geojson)
                features = gj.get("features", [])
                added = 0
                for feat in features:
                    geom = feat.get("geometry", {})
                    if geom.get("type") == "LineString":
                        coords = [(c[1], c[0]) for c in geom.get("coordinates", [])]
                        if len(coords) >= 2:
                            name = feat.get("properties", {}).get("name", f"خط {len(st.session_state.lines)+1}")
                            st.session_state.lines.append({
                                "id": str(uuid.uuid4()), "name": name, "length": line_length(coords), "coords": coords, "selected": True, "diameter": 600, "depth": 1.5, "reversed": False
                            })
                            added += 1
                st.session_state.analyzer = None
                st.session_state.cost = None
                st.success(f"✅ تمت إضافة {added} خط بنجاح!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# التبويب 2: تحليل الشبكة والتكاليف المدمج
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("<div class='section-title'>🌐 تحليل الشبكة وإدخال التكاليف المتكامل (SAR)</div>", unsafe_allow_html=True)

    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً في الخطوة السابقة أولاً.")
    else:
        st.session_state.analyzer = NetworkAnalyzer(st.session_state.lines)
        ana = st.session_state.analyzer
        stat = ana.stats()

        all_c = [pt for ln in st.session_state.lines for pt in ln["coords"]]
        mc = center_of(all_c)
        bnds = get_bounds(all_c)

        m_net = folium.Map(location=mc, zoom_start=14, tiles="CartoDB positron")
        Fullscreen(title="ملء الشاشة").add_to(m_net)
        
        edge_colors = ["#1a5fa8", "#e63946", "#2a9d8f", "#e9c46a", "#f4a261"]
        for i, e in enumerate(ana.edges_list):
            color = edge_colors[i % len(edge_colors)]
            folium.PolyLine([e["start_coord"], e["end_coord"]], color=color, weight=5, opacity=0.85, tooltip=f"{e['line_name']}: منهل {e['node_start']} ➔ منهل {e['node_end']}").add_to(m_net)
            mid_point = [(e["start_coord"][0] + e["end_coord"][0])/2, (e["start_coord"][1] + e["end_coord"][1])/2]
            folium.RegularPolygonMarker(location=mid_point, fill_color=color, number_of_sides=3, radius=6, rotation=90).add_to(m_net)

        for coord, nid in ana.nodes_coords.items():
            folium.CircleMarker(location=coord, radius=8, color="#0a2a5e", fill=True, fillColor="#e63946", tooltip=f"منهل #{nid}").add_to(m_net)

        m_net.fit_bounds(bnds)
        st_folium(m_net, width=None, height=380, key="integrated_net_map")

        st.markdown("---")
        st.markdown("#### ⚙️ جدول التحكم بالخطوط، الاتجاهات، وإدخال مواصفات التكاليف")

        header_cols = st.columns([2, 1.5, 1.5, 1.5, 2.5, 1])
        header_cols[0].markdown("**اسم الخط**")
        header_cols[1].markdown("**الطول**")
        header_cols[2].markdown("**القطر (مم)**")
        header_cols[3].markdown("**العمق (م)**")
        header_cols[4].markdown("**اتجاه المصب (من ➔ إلى)**")
        header_cols[5].markdown("**إجراء**")
        st.markdown("---")

        any_change = False
        lines_to_delete = []

        for idx, line in enumerate(st.session_state.lines):
            corresponding_edge = next((e for e in ana.edges_list if e["id"] == line["id"]), None)
            node_info = f"عقدة {corresponding_edge['node_start']} ➔ عقدة {corresponding_edge['node_end']}" if corresponding_edge else "—"

            row_cols = st.columns([2, 1.5, 1.5, 1.5, 2.5, 1])
            
            with row_cols[0]:
                new_name = st.text_input("الاسم", value=line["name"], key=f"int_name_{line['id']}", label_visibility="collapsed")
                if new_name != line["name"]:
                    st.session_state.lines[idx]["name"] = new_name
                    any_change = True
            
            row_cols[1].write(f"📏 {line['length']:.1f} م")
            
            with row_cols[2]:
                d_val = st.selectbox("القطر", sorted(PIPE_PRICES.keys()), index=list(sorted(PIPE_PRICES.keys())).index(line.get("diameter", 600)), key=f"int_dia_{line['id']}", label_visibility="collapsed")
                if d_val != line.get("diameter"):
                    st.session_state.lines[idx]["diameter"] = d_val
                    any_change = True
                    
            with row_cols[3]:
                dp_val = st.number_input("العمق", min_value=0.5, max_value=10.0, value=float(line.get("depth", 1.5)), step=0.1, key=f"int_dep_{line['id']}", label_visibility="collapsed")
                if dp_val != line.get("depth"):
                    st.session_state.lines[idx]["depth"] = dp_val
                    any_change = True
            
            with row_cols[4]:
                rev_click = st.checkbox(f"تحويل المصب ({node_info})", value=line.get("reversed", False), key=f"int_rev_{line['id']}")
                if rev_click != line.get("reversed"):
                    st.session_state.lines[idx]["reversed"] = rev_click
                    any_change = True

            with row_cols[5]:
                if st.button("🗑️", key=f"int_del_{line['id']}"):
                    lines_to_delete.append(idx)

        if lines_to_delete:
            for d_idx in sorted(lines_to_delete, reverse=True):
                st.session_state.lines.pop(d_idx)
            st.rerun()

        if any_change:
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🧮 حساب وتحديث كشف حساب التكاليف والكميات (SAR) فوراً", use_container_width=True):
            all_items = {}
            per_edge = []
            total_len = stat["length"]

            for edge in ana.edges_list:
                d = edge["diameter"]
                dep = edge["depth"]
                L = edge["distance"]
                share = L / total_len if total_len > 0 else 0
                n_mh = max(1, round(stat["nodes"] * share))
                n_tr = num_traps(L)
                p_pipe = PIPE_PRICES.get(d, 725)

                items = [
                    {"البند": "أنابيب صرف (خرسانية)", "الكمية": L, "الوحدة": "m", "السعر": p_pipe, "الإجمالي": L * p_pipe},
                    {"البند": "حفر خنادق", "الكمية": L, "الوحدة": "m", "السعر": EXCAVATION, "الإجمالي": L * EXCAVATION},
                    {"البند": "مناهل تفتيش", "الكمية": n_mh, "الوحدة": "Qty", "السعر": MANHOLE_PRICE, "الإجمالي": n_mh * MANHOLE_PRICE},
                    {"البند": "مصائد رمل وحطام", "الكمية": n_tr, "الوحدة": "Qty", "السعر": TRAP_PRICE, "الإجمالي": n_tr * TRAP_PRICE},
                    {"البند": "ردم وتسوية داخلية", "الكمية": L * dep, "الوحدة": "m³", "السعر": BACKFILL_PRICE, "الإجمالي": L * dep * BACKFILL_PRICE},
                ]

                total = sum(it["الإجمالي"] for it in items)
                per_edge.append({
                    "line_name": edge["line_name"], "diameter": d, "depth": dep, "length": L, "items": items, "total": total, "n_manholes": n_mh, "n_traps": n_tr, 
                    "start_node": edge["node_start"], "end_node": edge["node_end"], "start_coord": edge["start_coord"], "end_coord": edge["end_coord"]
                })

                for it in items:
                    k = it["البند"]
                    if k not in all_items:
                        all_items[k] = {"الكمية": 0, "الإجمالي": 0, "الوحدة": it["الوحدة"]}
                    all_items[k]["الكمية"] += it["الكمية"]
                    all_items[k]["الإجمالي"] += it["الإجمالي"]

            st.session_state.cost = {
                "per_edge": per_edge, "all_items": all_items, "total_cost": sum(v["الإجمالي"] for v in all_items.values()), "stat": stat, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            st.success("✅ تم تحديث وتحليل التكاليف بالريال السعودي!")

        if st.session_state.cost:
            result = st.session_state.cost
            st.markdown("### 📊 كشف الحساب المالي التقديري (Saudi Riyal)")
            
            rows = []
            for name, data in result["all_items"].items():
                eng_name = ITEM_TRANSLATIONS.get(name, name)
                rows.append({"Description (البند)": eng_name, "Total Qty (الكمية)": f"{data['الكمية']:,.2f}", "Unit (الوحدة)": data["الوحدة"], "Total Cost (التكلفة)": f"{data['الإجمالي']:,.0f} SAR"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            st.markdown(f'<div class="total-row">💰 التكلفة الإجمالية المعتمدة للمشروع: {result["total_cost"]:,.0f} ريال سعودي (SAR)</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# التبويب 3: التقرير والطباعة (PDF المطور بالإنجليزية مع الخريطة المدمجة)
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("<div class='section-title'>📋 التقرير والطباعة والتصدير الهندسي بالإنجليزية</div>", unsafe_allow_html=True)

    if not st.session_state.cost:
        st.warning("⚠️ يرجى الضغط على زر 'حساب وتحديث كشف حساب التكاليف' من التبويب السابق لتوليد البيانات والمخطط الهيكلي للتقرير أولاً.")
    else:
        result = st.session_state.cost
        ana = st.session_state.analyzer
        
        st.markdown("""<div class="info-banner">📝 سيحتوي ملف الـ PDF النهائي المولد أدناه على خريطة مصممة ومرفقة برمجياً للأقطار والخطوط (Network Map Sketch)، وستكون كل البنود بالريال السعودي (SAR) واللغة الإنجليزية.</div>""", unsafe_allow_html=True)

        proj_name = st.text_input("Project Name (اسم المشروع)", value="Stormwater Drainage Network Expansion Project")
        proj_owner = st.text_input("Project Owner / Client (الجهة المالكة)", value="Ministry of Municipal and Rural Affairs (MoMRA)")
        engineer   = st.text_input("Supervising Engineer (المهندس المشرف)", value="Eng. Ahmad Al-Saudi")

        if st.button("📥 إنشاء وتحميل التقرير النهائي والخريطة المدمجة (PDF)", use_container_width=True):
            with st.spinner("جاري تصميم الخريطة وبناء المستند الهندسي..."):
                try:
                    # 1. توليد الخريطة وحفظها كصورة برمجية لإدراجها في الـ PDF
                    fig, ax = plt.subplots(figsize=(7, 4.5))
                    ax.set_title("Network Schema Sketch (Diameters & Nodes Layout)", fontsize=10, fontweight='bold', color='#0a2a5e')
                    
                    # رسم الفروع والأنابيب حسب قطرها
                    plotted_diameters = set()
                    for edge_r in result["per_edge"]:
                        d = edge_r["diameter"]
                        color = PIPE_COLORS.get(d, "#1a5fa8")
                        # تنسيق سماكة الخط بناءً على القطر
                        line_w = 1.5 + (d / 400) * 2.0
                        
                        x_coords = [edge_r["start_coord"][1], edge_r["end_coord"][1]]
                        y_coords = [edge_r["start_coord"][0], edge_r["end_coord"][0]]
                        
                        ax.plot(x_coords, y_coords, color=color, linewidth=line_w, alpha=0.9, label=f"Ø {d} mm" if d not in plotted_diameters else "")
                        plotted_diameters.add(d)
                        
                        # تسمية الفرع في المنتصف
                        mx, my = sum(x_coords)/2, sum(y_coords)/2
                        ax.text(mx, my, edge_r["line_name"], fontsize=7, color='#333333', weight='bold', backgroundcolor='#ffffffcc')

                    # رسم عقد المناهل
                    x_nodes = [coord[1] for coord in ana.nodes_coords.keys()]
                    y_nodes = [coord[0] for coord in ana.nodes_coords.keys()]
                    ax.scatter(x_nodes, y_nodes, color="#e63946", s=45, edgecolors="#0a2a5e", zorder=5)
                    
                    for coord, nid in ana.nodes_coords.items():
                        ax.text(coord[1], coord[0], f" MH{nid}", fontsize=7, color='#0a2a5e', weight='black')

                    ax.axis('off')
                    ax.legend(loc="lower right", fontsize=7, frameon=True, facecolor="#ffffff")
                    plt.tight_layout()
                    
                    # حفظ في Memory Buffer كمخطط مدمج
                    img_buf = io.BytesIO()
                    plt.savefig(img_buf, format='png', dpi=200)
                    img_buf.seek(0)
                    plt.close(fig)

                    # 2. بناء التقرير الهندسي عبر ReportLab
                    from reportlab.lib.pagesizes import portrait, A4
                    from reportlab.lib import colors
                    from reportlab.lib.units import mm
                    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, PageBreak, Image
                    from reportlab.lib.styles import ParagraphStyle
                    from reportlab.lib.enums import TA_CENTER, TA_LEFT

                    buf = io.BytesIO()
                    # استخدام الاتجاه الرأسي ليكون كوثيقة هندسية رسمية
                    doc = SimpleDocTemplate(buf, pagesize=portrait(A4), rightMargin=15*mm, leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)

                    BLUE, LBLUE, GREY, WHITE = colors.HexColor("#0a2a5e"), colors.HexColor("#1a5fa8"), colors.HexColor("#f0f4f8"), colors.white
                    
                    s_title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=18, textColor=WHITE, alignment=TA_CENTER)
                    s_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, textColor=BLUE, spaceBefore=8, spaceAfter=4)
                    s_meta = ParagraphStyle("meta", fontName="Helvetica-Bold", fontSize=10, textColor=colors.black)
                    s_normal = ParagraphStyle("norm", fontName="Helvetica", fontSize=9, textColor=colors.black)
                    s_footer = ParagraphStyle("footer", fontName="Helvetica", fontSize=7.5, textColor=colors.grey, alignment=TA_CENTER)

                    elems = []
                    
                    # ترويسة رئيسية للغلاف
                    header_tbl = Table([[Paragraph(f"STORMWATER DRAINAGE INFRASTRUCTURE REPORT<br/><font size=10>{proj_name}</font>", s_title)]], colWidths=[180*mm])
                    header_tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), BLUE), ('PADDING', (0,0), (-1,-1), 14), ('ROUNDEDCORNERS', (0,0), (-1,-1), [4,4,4,4])]))
                    elems.append(header_tbl)
                    elems.append(Spacer(1, 5*mm))

                    # جدول المعلومات التعريفية للمشروع
                    meta_data = [
                        [Paragraph("Client Name:", s_meta), Paragraph(proj_owner, s_normal), Paragraph("Date:", s_meta), Paragraph(result["generated_at"], s_normal)],
                        [Paragraph("Supervising Engineer:", s_meta), Paragraph(engineer if engineer else "N/A", s_normal), Paragraph("Currency:", s_meta), Paragraph("Saudi Riyal (SAR)", s_normal)]
                    ]
                    meta_tbl = Table(meta_data, colWidths=[35*mm, 60*mm, 25*mm, 60*mm])
                    meta_tbl.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")), ('BACKGROUND', (0,0), (0,-1), GREY), ('BACKGROUND', (2,0), (2,-1), GREY), ('PADDING', (0,0), (-1,-1), 5)]))
                    elems.append(meta_tbl)
                    elems.append(Spacer(1, 5*mm))

                    # القسم الأول: المخطط المرفق للشبكة والأقطار
                    elems.append(Paragraph("1. NETWORK SCHEMA & PIPE DIAMETERS SKETCH MAP", s_h2))
                    elems.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceBefore=1, spaceAfter=4))
                    
                    # إضافة صورة الخريطة المحدثة والمولدة ديناميكياً
                    report_img = Image(img_buf, width=170*mm, height=110*mm)
                    elems.append(report_img)
                    elems.append(Spacer(1, 5*mm))

                    # القسم الثاني: جدول الكميات والتكلفة الكلية بالريال السعودي
                    elems.append(Paragraph("2. BILL OF QUANTITIES (BOQ) & DIRECT COSTS", s_h2))
                    elems.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceBefore=1, spaceAfter=4))
                    
                    boq_data = [["Item Description", "Total Quantity", "Unit", "Total Cost (SAR)"]]
                    for name, d in result["all_items"].items():
                        eng_name = ITEM_TRANSLATIONS.get(name, name)
                        boq_data.append([eng_name, f"{d['الكمية']:,.2f}", d["الوحدة"], f"{d['الإجمالي']:,.0f} SAR"])
                    
                    boq_data.append(["TOTAL ESTIMATED PROJECT BUDGET", "", "", f"{result['total_cost']:,.0f} SAR"])

                    boq_tbl = Table(boq_data, colWidths=[75*mm, 35*mm, 25*mm, 45*mm])
                    boq_tbl.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), LBLUE), ('TEXTCOLOR', (0,0), (-1,0), WHITE), ('FONTNAME', (0,0), (-1,0), "Helvetica-Bold"),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")), ('PADDING', (0,0), (-1,-1), 5), ('ALIGN', (1,0), (-1,-1), "CENTER"),
                        ('BACKGROUND', (0,-1), (-1,-1), BLUE), ('TEXTCOLOR', (0,-1), (-1,-1), WHITE), ('FONTNAME', (0,-1), (-1,-1), "Helvetica-Bold")
                    ]))
                    elems.append(boq_tbl)
                    
                    elems.append(PageBreak())

                    # القسم الثالث: كشف التفاصيل الدقيقة لكل فرع خط
                    elems.append(Paragraph("3. DETAILED INFRASTRUCTURE SPECIFICATIONS BY PIPELINE", s_h2))
                    elems.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceBefore=1, spaceAfter=4))
                    
                    branch_data = [["Line Reference", "Length (m)", "Dia (mm)", "Depth (m)", "Manholes", "Traps", "Sub-Total (SAR)"]]
                    for e in result["per_edge"]:
                        branch_data.append([
                            e["line_name"], f"{e['length']:.1f}", str(e['diameter']), f"{e['depth']:.1f}", 
                            str(e["n_manholes"]), str(e["n_traps"]), f"{e['total']:,.0f} SAR"
                        ])

                    br_tbl = Table(branch_data, colWidths=[35*mm, 23*mm, 20*mm, 20*mm, 22*mm, 18*mm, 42*mm])
                    br_tbl.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), LBLUE), ('TEXTCOLOR', (0,0), (-1,0), WHITE), ('FONTNAME', (0,0), (-1,0), "Helvetica-Bold"), ('FONTSIZE', (0,0), (-1,-1), 8.5),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")), ('PADDING', (0,0), (-1,-1), 5), ('ALIGN', (1,0), (-1,-1), "CENTER")
                    ]))
                    elems.append(br_tbl)
                    
                    # تذييل الصفحة وثيقة رسمية
                    elems.append(Spacer(1, 15*mm))
                    elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d0d8e8")))
                    elems.append(Paragraph(f"Stormwater Network Analytical Tool v13.0 | Currency Approved: SAR (Saudi Riyal) | Confidential Engineering Report", s_footer))

                    doc.build(elems)
                    buf.seek(0)

                    st.download_button(
                        label="📥 اضغط هنا لبدء تحميل تقرير الـ PDF المطور والخريطة المدمجة", 
                        data=buf.getvalue(), 
                        file_name=f"Stormwater_Network_Report_SAR.pdf", 
                        mime="application/pdf", 
                        use_container_width=True
                    )
                    st.success("✅ تم توليد التقرير الهندسي بنجاح باللغة الإنجليزية وعملة الـ SAR!")
                except Exception as ex:
                    st.error(f"❌ حدث خطأ أثناء إعداد المخطط الهيكلي أو مستند الـ PDF: {ex}")

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div style="text-align:center;color:#9aa4b8;font-size:0.85rem;padding:16px 0">🌊 محلل شبكات السيول المتطور — النسخة المعتمدة للتصدير الدولي (المملكة العربية السعودية)</div>', unsafe_allow_html=True)

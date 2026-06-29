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
            
            # التحقق من خيار عكس الاتجاه (تحويل المصب)
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
                    "line_name": line.get("name", "خط"),
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
    <p>تحليل متكامل وحساب دقيق لتكاليف شبكات الصرف السيلية</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# التبويبات الرئيسية المحدثة
# ─────────────────────────────────────────────────────────────────────────────
TAB_LABELS = [
    "🏠 الرئيسية",
    "🗺️ ١ · رسم وإدخل البيانات",
    "🌐 ٢ · تحليل الشبكة والتكاليف المدمج",
    "📋 ٣ · التقرير والطباعة",
]
tabs = st.tabs(TAB_LABELS)

# ══════════════════════════════════════════════════════════════════════════════
# التبويب 0: الرئيسية
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("<div class='section-title'>خطوات استخدام التطبيق</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    steps = [
        ("🗺️", "١ · رسم وإدخال", "ارسم خطوط الشبكة مباشرة على الخريطة أو استورد ملفات GeoJSON القياسية"),
        ("🌐", "٢ · التحليل والتكاليف", "شاهد الخريطة التحليلية، عدل اتجاه المصب، أدخل الأقطار، واحسب التكاليف مباشرة"),
        ("📋", "٣ · التقرير", "تصدير تقرير PDF كامل مع الخريطة وجداول الكميات والتكاليف المعتمدة"),
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
                folium.PolyLine(
                    coords, color="#e63946", weight=4, opacity=0.9,
                    tooltip=ln["name"]
                ).add_to(m_draw)

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
                            "id": str(uuid.uuid4()),
                            "name": f"خط {len(st.session_state.lines)+1}",
                            "length": length,
                            "coords": coords,
                            "selected": True,
                            "diameter": 600,
                            "depth": 1.5,
                            "reversed": False
                        }
                        st.session_state.lines.append(new_line)
                        st.session_state.analyzer = None
                        st.session_state.cost = None
                        st.success(f"✅ تمت إضافة {new_line['name']}")
                        st.rerun()

    # ── GeoJSON ──────────────────────────────────────────────────────────────
    with sub2:
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
# التبويب 2: تحليل الشبكة والتكاليف المدمج (التحديث الرئيسي)
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("<div class='section-title'>🌐 تحليل الشبكة وإدخال التكاليف المتكامل</div>", unsafe_allow_html=True)

    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً في الخطوة السابقة أولاً.")
    else:
        # تشغيل التحليل تلقائياً لتحديث البيانات باستمرار
        st.session_state.analyzer = NetworkAnalyzer(st.session_state.lines)
        ana = st.session_state.analyzer
        stat = ana.stats()

        # عرض خريطة الشبكة التحليلية في الأعلى مباشرة
        all_c = [pt for ln in st.session_state.lines for pt in ln["coords"]]
        mc = center_of(all_c)
        bnds = get_bounds(all_c)

        m_net = folium.Map(location=mc, zoom_start=14, tiles="CartoDB positron")
        Fullscreen(title="ملء الشاشة").add_to(m_net)
        
        # رسم الفروع بالأسهم الملونة لبيان اتجاه المصب الحالي
        edge_colors = ["#1a5fa8", "#e63946", "#2a9d8f", "#e9c46a", "#f4a261"]
        for i, e in enumerate(ana.edges_list):
            color = edge_colors[i % len(edge_colors)]
            folium.PolyLine(
                [e["start_coord"], e["end_coord"]], color=color, weight=5, opacity=0.85,
                tooltip=f"{e['line_name']}: منهل {e['node_start']} ➔ منهل {e['node_end']}"
            ).add_to(m_net)
            
            # إضافة سهم صغير في منتصف الخط لتوضيح الاتجاه والمصب
            mid_point = [(e["start_coord"][0] + e["end_coord"][0])/2, (e["start_coord"][1] + e["end_coord"][1])/2]
            folium.RegularPolygonMarker(location=mid_point, fill_color=color, number_of_sides=3, radius=6, rotation=90).add_to(m_net)

        # رسم المناهل (العقد)
        for coord, nid in ana.nodes_coords.items():
            folium.CircleMarker(location=coord, radius=8, color="#0a2a5e", fill=True, fillColor="#e63946", tooltip=f"منهل #{nid}").add_to(m_net)

        m_net.fit_bounds(bnds)
        st_folium(m_net, width=None, height=400, key="integrated_net_map")

        st.markdown("---")
        st.markdown("#### ⚙️ جدول التحكم بالخطوط، الاتجاهات، وإدخال مواصفات التكاليف")
        st.markdown("""
        <div class="info-banner">
            💡 يمكنك تعديل <b>اسم الخط</b>، <b>القطر</b>، <b>العمق</b>، أو <b>تحويل اتجاه المصب (عكس البداية والنهاية)</b> أو <b>حذف الخط</b> بالكامل مباشرة من الجدول أدناه.
        </div>
        """, unsafe_allow_html=True)

        # تصميم جدول مرن لإدخال وتعديل وإجراء العمليات
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
            # إيجاد العقد المقابلة لهذا الخط من المحلل
            corresponding_edge = next((e for e in ana.edges_list if e["id"] == line["id"]), None)
            node_info = f"عقدة {corresponding_edge['node_start']} ➔ عقدة {corresponding_edge['node_end']}" if corresponding_edge else "—"

            row_cols = st.columns([2, 1.5, 1.5, 1.5, 2.5, 1])
            
            # 1. اسم الخط
            with row_cols[0]:
                new_name = st.text_input("الاسم", value=line["name"], key=f"int_name_{line['id']}", label_visibility="collapsed")
                if new_name != line["name"]:
                    st.session_state.lines[idx]["name"] = new_name
                    any_change = True
            
            # 2. الطول
            row_cols[1].write(f"📏 {line['length']:.1f} م")
            
            # 3. اختيار القطر
            with row_cols[2]:
                d_val = st.selectbox("القطر", sorted(PIPE_PRICES.keys()), index=list(sorted(PIPE_PRICES.keys())).index(line.get("diameter", 600)), key=f"int_dia_{line['id']}", label_visibility="collapsed")
                if d_val != line.get("diameter"):
                    st.session_state.lines[idx]["diameter"] = d_val
                    any_change = True
                    
            # 4. إدخال العمق
            with row_cols[3]:
                dp_val = st.number_input("العمق", min_value=0.5, max_value=10.0, value=float(line.get("depth", 1.5)), step=0.1, key=f"int_dep_{line['id']}", label_visibility="collapsed")
                if dp_val != line.get("depth"):
                    st.session_state.lines[idx]["depth"] = dp_val
                    any_change = True
            
            # 5. خيار تحويل المصب (عكس الاتجاه)
            with row_cols[4]:
                rev_click = st.checkbox(f"تحويل المصب ({node_info})", value=line.get("reversed", False), key=f"int_rev_{line['id']}")
                if rev_click != line.get("reversed"):
                    st.session_state.lines[idx]["reversed"] = rev_click
                    any_change = True

            # 6. زر الحذف
            with row_cols[5]:
                if st.button("🗑️", key=f"int_del_{line['id']}"):
                    lines_to_delete.append(idx)

        # تنفيذ الحذف إن وجد
        if lines_to_delete:
            for d_idx in sorted(lines_to_delete, reverse=True):
                st.session_state.lines.pop(d_idx)
            st.rerun()

        if any_change:
            st.rerun()

        # زر حساب وتحديث التكاليف الفوري
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🧮 حساب وتحديث كشف حساب التكاليف والكميات فوراً", use_container_width=True):
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
                    {"البند": "أنابيب صرف (خرسانية)", "الكمية": L, "الوحدة": "م", "السعر": p_pipe, "الإجمالي": L * p_pipe},
                    {"البند": "حفر خنادق", "الكمية": L, "الوحدة": "م", "السعر": EXCAVATION, "الإجمالي": L * EXCAVATION},
                    {"البند": "مناهل تفتيش", "الكمية": n_mh, "الوحدة": "عدد", "السعر": MANHOLE_PRICE, "الإجمالي": n_mh * MANHOLE_PRICE},
                    {"البند": "مصائد رمل وحطام", "الكمية": n_tr, "الوحدة": "عدد", "السعر": TRAP_PRICE, "الإجمالي": n_tr * TRAP_PRICE},
                    {"البند": "ردم وتسوية داخلية", "الكمية": L * dep, "الوحدة": "م³", "السعر": BACKFILL_PRICE, "الإجمالي": L * dep * BACKFILL_PRICE},
                ]

                total = sum(it["الإجمالي"] for it in items)
                per_edge.append({"line_name": edge["line_name"], "diameter": d, "depth": dep, "length": L, "items": items, "total": total, "n_manholes": n_mh, "n_traps": n_tr, "start_coord": edge["start_coord"], "end_coord": edge["end_coord"]})

                for it in items:
                    k = it["البند"]
                    if k not in all_items:
                        all_items[k] = {"الكمية": 0, "الإجمالي": 0, "الوحدة": it["الوحدة"]}
                    all_items[k]["الكمية"] += it["الكمية"]
                    all_items[k]["الإجمالي"] += it["الإجمالي"]

            st.session_state.cost = {
                "per_edge": per_edge, "all_items": all_items, "total_cost": sum(v["الإجمالي"] for v in all_items.values()), "stat": stat, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            st.success("✅ تم تحديث التكاليف بناءً على معطيات الجدول الجديد!")

        # عرض جداول التكاليف والكميات المحسوبة مباشرة بالأسفل
        if st.session_state.cost:
            result = st.session_state.cost
            st.markdown("### 📊 كشف الحساب المالي للمشروع")
            
            rows = []
            for name, data in result["all_items"].items():
                rows.append({"البند": name, "الكمية الكلية": f"{data['الكمية']:,.2f}", "الوحدة": data["الوحدة"], "التكلفة الإجمالية (ريال)": f"{data['الإجمالي']:,.0f}"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            st.markdown(f'<div class="total-row">💰 التكلفة الإجمالية المعتمدة للمشروع: {result["total_cost"]:,.0f} ريال قطري/سعودي</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# التبويب 3: التقرير والطباعة
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("<div class='section-title'>📋 التقرير والطباعة والتصدير</div>", unsafe_allow_html=True)

    if not st.session_state.cost:
        st.warning("⚠️ يرجى الضغط على زر 'حساب وتحديث كشف حساب التكاليف' من التبويب السابق أولاً لتوليد بيانات التقرير.")
    else:
        result = st.session_state.cost
        proj_name = st.text_input("اسم المشروع للتصدير", value="مشروع شبكة صرف سيلي متكامل")
        proj_owner = st.text_input("الجهة المالكة", value="أمانة المنطقة / البلدية")
        engineer   = st.text_input("المهندس الفاحص المشرف", value="")

        if st.button("📥 إنشاء وتحميل التقرير النهائي بصيغة PDF", use_container_width=True):
            with st.spinner("جاري إنشاء المستند الهندسي..."):
                try:
                    from reportlab.lib.pagesizes import landscape, A4
                    from reportlab.lib import colors
                    from reportlab.lib.units import mm
                    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, PageBreak
                    from reportlab.lib.styles import ParagraphStyle
                    from reportlab.lib.enums import TA_CENTER

                    buf = io.BytesIO()
                    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), rightMargin=15*mm, leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)

                    BLUE, LBLUE, GREY, WHITE = colors.HexColor("#0a2a5e"), colors.HexColor("#1a5fa8"), colors.HexColor("#f0f4f8"), colors.white
                    s_title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20, textColor=WHITE, alignment=TA_CENTER)
                    s_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, textColor=BLUE, spaceBefore=10, spaceAfter=6)
                    s_footer = ParagraphStyle("footer", fontName="Helvetica", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)

                    elems = []
                    header_tbl = Table([[Paragraph(f"FLOOD DRAINAGE NETWORK REPORT<br/><font size=11>{proj_name}</font>", s_title)]], colWidths=[260*mm])
                    header_tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), BLUE), ('PADDING', (0,0), (-1,-1), 16), ('ROUNDEDCORNERS', (0,0), (-1,-1), [6,6,6,6])]))
                    elems.append(header_tbl)
                    elems.append(Spacer(1, 6*mm))

                    # ملخص الجدول الأول
                    elems.append(Paragraph("1. GENERAL QUANTITIES & SUMMARY", s_h2))
                    boq_data = [["Item Description", "Quantity", "Unit", "Total (SAR)"]]
                    for name, d in result["all_items"].items():
                        boq_data.append([name, f"{d['الكمية']:,.2f}", d["الوحدة"], f"{d['الإجمالي']:,.0f}"])
                    boq_data.append(["TOTAL PROJECT COST", "", "", f"{result['total_cost']:,.0f}"])

                    boq_tbl = Table(boq_data, colWidths=[100*mm, 40*mm, 40*mm, 80*mm])
                    boq_tbl.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), LBLUE), ('TEXTCOLOR', (0,0), (-1,0), WHITE),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")), ('PADDING', (0,0), (-1,-1), 6),
                        ('BACKGROUND', (0,-1), (-1,-1), BLUE), ('TEXTCOLOR', (0,-1), (-1,-1), WHITE), ('FONTNAME', (0,-1), (-1,-1), "Helvetica-Bold")
                    ]))
                    elems.append(boq_tbl)
                    
                    elems.append(Spacer(1, 10*mm))
                    elems.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d0d8e8")))
                    elems.append(Paragraph(f"Generated via Flood Analyzer | Date: {result['generated_at']}", s_footer))

                    doc.build(elems)
                    buf.seek(0)

                    st.download_button(label="📥 اضغط هنا لبدء تحميل ملف الـ PDF", data=buf.getvalue(), file_name=f"StormNetwork_Report.pdf", mime="application/pdf", use_container_width=True)
                except Exception as ex:
                    st.error(f"❌ حدث خطأ أثناء بناء ملف الـ PDF: {ex}")

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div style="text-align:center;color:#9aa4b8;font-size:0.85rem;padding:16px 0">🌊 محلل شبكات السيول المتطور — نسخة التحكم الكامل والمباشر بالاتجاهات والأبعاد</div>', unsafe_allow_html=True)

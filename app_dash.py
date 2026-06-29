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

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except Exception:
    GEOPANDAS_AVAILABLE = False

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

PIPE_COLORS = {
    400: "#2196F3", 500: "#4CAF50", 600: "#FF9800",
    700: "#9C27B0", 800: "#F44336", 900: "#00BCD4",
    1000: "#FF5722", 1100: "#795548", 1200: "#607D8B",
    1300: "#E91E63", 1400: "#3F51B5",
}

MANHOLE_PRICE  = 3_000   
TRAP_PRICE     = 2_000   
EXCAVATION     = 50      
BACKFILL_PRICE = 30      
TRAP_SPACING   = 35      

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
                    "id": line["id"],
                    "start_coord": s,
                    "end_coord": e,
                    "distance": dist,
                    "line_name": line.get("name", "خط"),
                    "node_start": sn,
                    "node_end": en,
                    "diameter": line.get("diameter", 600),
                    "depth": line.get("depth", 1.5),
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
# التبويبات الرئيسية
# ─────────────────────────────────────────────────────────────────────────────
TAB_LABELS = [
    "🏠 الرئيسية",
    "🗺️ ١ · رسم وإدخل",
    "🌐 ٢ · تحليل الشبكة",
    "💰 ٣ · التكاليف وحساب الكميات",
    "📋 ٤ · التقرير والطباعة",
]
tabs = st.tabs(TAB_LABELS)

# التبويب 0: الرئيسية
with tabs[0]:
    st.markdown("<div class='section-title'>خطوات استخدام التطبيق</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    steps = [
        ("🗺️", "١ · رسم وإدخل", "ارسم خطوط الشبكة مباشرة على الخريطة أو استورد ملفات GeoJSON / Shapefile"),
        ("🌐", "٢ · تحليل الشبكة", "حلل المناهل والفروع والأطوال واعرضها على خريطة تفاعلية ملونة"),
        ("💰", "٣ · التكاليف", "أدخل قطر وعمق كل فرع بشكل مستقل ثم احسب كميات التربة والأنابيب والتكلفة الكلية للمشروع"),
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

    st.markdown("<div class='section-title'>ملخص المشروع</div>", unsafe_allow_html=True)
    km1, km2, km3, km4 = st.columns(4)
    n_lines  = len(st.session_state.lines)
    n_nodes  = st.session_state.analyzer.stats()["nodes"] if st.session_state.analyzer else 0
    tot_km   = (st.session_state.analyzer.stats()["length"]/1000) if st.session_state.analyzer else 0.0
    tot_cost = st.session_state.cost["total_cost"] if st.session_state.cost else 0

    for col, val, lbl in zip(
        [km1, km2, km3, km4],
        [n_lines, n_nodes, f"{tot_km:.2f}", f"{tot_cost:,.0f}"],
        ["الخطوط المدخلة", "المناهل", "الطول الكلي (كم)", "التكلفة الكلية (ريال)"]
    ):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{val}</div>
                <div class="kpi-label">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)

# التبويب 1: رسم وإدخل
with tabs[1]:
    st.markdown("<div class='section-title'>🗺️ رسم وإدخال الشبكة</div>", unsafe_allow_html=True)
    sub1, sub2, sub3 = st.tabs(["✏️ رسم على الخريطة", "📤 استيراد GeoJSON", "📦 استيراد Shapefile"])

    with sub1:
        st.markdown("""
        <div class="info-banner">
            📌 استخدم أداة الرسم في أعلى يسار الخريطة لرسم خطوط الشبكة. انقر لإضافة نقاط ثم انقر مرتين لإنهاء الخط.
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
                folium.PolyLine(coords, color="#e63946", weight=4, opacity=0.9, tooltip=ln["name"]).add_to(m_draw)
                folium.CircleMarker(coords[0], radius=6, color="#0a2a5e", fill=True, fillColor="#1a5fa8").add_to(m_draw)
                folium.CircleMarker(coords[-1], radius=6, color="#e63946", fill=True, fillColor="#e63946").add_to(m_draw)

        draw_ctrl = Draw(
            export=False, position="topleft",
            draw_options={"polyline": {"shapeOptions": {"color": "#e63946", "weight": 4}}, "polygon": False, "rectangle": False, "circle": False, "marker": False, "circlemarker": False}
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
                            "diameter": 600,
                            "depth": 1.5,
                            "selected": True,
                        }
                        st.session_state.lines.append(new_line)
                        st.session_state.analyzer = None
                        st.session_state.cost = None
                        st.success(f"✅ تمت إضافة {new_line['name']}")
                        st.rerun()

        if st.session_state.lines:
            st.markdown("---")
            st.markdown("**الخطوط المدخلة حالياً:**")
            for i, ln in enumerate(st.session_state.lines):
                c1_, c2_, c3_ = st.columns([4, 2, 1])
                with c1_:
                    st.session_state.lines[i]["name"] = st.text_input("الاسم", value=ln["name"], key=f"name_{ln['id']}", label_visibility="collapsed")
                with c2_:
                    st.write(f"📏 {ln['length']:.1f} م")
                with c3_:
                    if st.button("🗑️", key=f"del_{ln['id']}"):
                        st.session_state.lines.pop(i)
                        st.session_state.analyzer = None
                        st.session_state.cost = None
                        st.rerun()

            if st.button("🗑️ حذف جميع الخطوط", use_container_width=True):
                st.session_state.lines = []
                st.session_state.analyzer = None
                st.session_state.cost = None
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
                                "id": str(uuid.uuid4()), "name": name, "length": line_length(coords),
                                "coords": coords, "diameter": 600, "depth": 1.5, "selected": True
                            })
                            added += 1
                st.session_state.analyzer = None
                st.session_state.cost = None
                st.success(f"✅ تمت إضافة {added} خط من GeoJSON")
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ في الملف: {e}")

    with sub3:
        if GEOPANDAS_AVAILABLE:
            uploaded_shp = st.file_uploader("اختر ملف ZIP يحتوي على Shapefile", type=["zip"], key="shp_up")
            if uploaded_shp:
                try:
                    import tempfile, zipfile, os
                    with tempfile.TemporaryDirectory() as tmpdir:
                        with zipfile.ZipFile(uploaded_shp, 'r') as zf:
                            zf.extractall(tmpdir)
                        shp_path = next((os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")), None)
                        if shp_path:
                            gdf = gpd.read_file(shp_path)
                            if gdf.crs and str(gdf.crs) != "EPSG:4326":
                                gdf = gdf.to_crs("EPSG:4326")
                            added = 0
                            for idx, row in gdf.iterrows():
                                if row.geometry and row.geometry.geom_type == "LineString":
                                    coords = [(lat, lon) for lon, lat in row.geometry.coords]
                                    if len(coords) >= 2:
                                        st.session_state.lines.append({
                                            "id": str(uuid.uuid4()), "name": f"خط {len(st.session_state.lines)+1}",
                                            "length": line_length(coords), "coords": coords, "diameter": 600, "depth": 1.5, "selected": True
                                        })
                                        added += 1
                            st.session_state.analyzer = None
                            st.session_state.cost = None
                            st.success(f"✅ تمت إضافة {added} خط من Shapefile")
                            st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
        else:
            st.warning("⚠️ مكتبة geopandas غير مثبتة.")

# التبويب 2: تحليل الشبكة
with tabs[2]:
    st.markdown("<div class='section-title'>🌐 تحليل هندسة الشبكة والعقد والتركيز الموجه</div>", unsafe_allow_html=True)

    if not st.session_state.lines:
        st.warning("⚠️ يرجى إضافة ورسم مسارات خطوط أولاً من التبويب السابق.")
    else:
        if st.button("🔍 إجراء تحليل ومحاكاة الشبكة الحالية", use_container_width=True) or st.session_state.analyzer is None:
            st.session_state.analyzer = NetworkAnalyzer(st.session_state.lines)

        ana = st.session_state.analyzer
        stat = ana.stats()

        k1, k2, k3, k4 = st.columns(4)
        for col, val, lbl in zip(
            [k1, k2, k3, k4],
            [stat["nodes"], stat["edges"], f"{stat['length']/1000:.2f} كم", stat["components"]],
            ["مناهل التفتيش الكلية (عقد)", "الفروع الهيدروليكية (حواف)", "الطول الإجمالي للشبكة", "الأجزاء المستقلة المتصلة"]
        ):
            with col:
                st.markdown(f'<div class="kpi-card"><div class="kpi-value">{val}</div><div class="kpi-label">{lbl}</div></div>', unsafe_allow_html=True)

        st.markdown("#### 🔍 تحديد فرع لعمل تكبير (Zoom) تلقائي عليه")
        line_names = [ln["name"] for ln in st.session_state.lines]
        target_focus = st.selectbox("اختر الخط المراد عمل التكبير والتركيز المباشر عليه:", ["كامل الشبكة"] + line_names)

        st.markdown("#### 🗺️ خريطة الفروع والعقد الهندسية")
        
        if target_focus == "كامل الشبكة":
            all_c = [pt for ln in st.session_state.lines for pt in ln["coords"]]
        else:
            all_c = next(ln["coords"] for ln in st.session_state.lines if ln["name"] == target_focus)

        m_net = folium.Map(location=center_of(all_c), zoom_start=14, tiles="OpenStreetMap")
        Fullscreen().add_to(m_net)

        for e in ana.edges_list:
            is_target = (target_focus == "كامل الشبكة" or e["line_name"] == target_focus)
            weight_render = 8 if is_target else 4
            opacity_render = 1.0 if is_target else 0.4
            
            folium.PolyLine([e["start_coord"], e["end_coord"]], color="#1a5fa8", weight=weight_render, opacity=opacity_render, tooltip=e["line_name"]).add_to(m_net)

        for coord, nid in ana.nodes_coords.items():
            folium.CircleMarker(location=coord, radius=7, color="#0a2a5e", fill=True, fillColor="#e63946", fillOpacity=0.9, tooltip=f"منهل #{nid}").add_to(m_net)

        m_net.fit_bounds(get_bounds(all_c))
        st_folium(m_net, width=None, height=500, key="analysis_map")

        st.markdown("#### 📋 قائمة فروع الشبكة المحللة")
        rows = [{"اسم الفرع الهيدروليكي": e["line_name"], "طول الفرع (م)": f"{e['distance']:.2f}", "منهل البداية": f"منهل #{e['node_start']}", "منهل النهاية": f"منهل #{e['node_end']}"} for e in ana.edges_list]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# التبويب 3: التكاليف وحساب الكميات
with tabs[3]:
    st.markdown("<div class='section-title'>💰 لوحة التحكم في مواصفات الفروع وجدول الكميات</div>", unsafe_allow_html=True)

    if not st.session_state.lines:
        st.warning("⚠️ يرجى رسم وإدخال خطوط الشبكة أولاً.")
    else:
        st.session_state.analyzer = NetworkAnalyzer(st.session_state.lines)
        ana = st.session_state.analyzer

        st.markdown("""
        <div class="info-banner">
            ⚙️ يمكنك تحديد <b>اسم الفرع، القطر (مم)، والعمق (م)</b> بشكل مستقل لكل فرع أدناه، ثم الضغط على <b>"🧮 حساب وتحديث جدول كميات المشروع"</b> لتوليد الفواتير والجداول فوراً.
        </div>
        """, unsafe_allow_html=True)

        hc = st.columns([0.5, 2.5, 1.5, 2, 2])
        headers = ["#", "اسم الفرع", "الطول (م)", "القطر الاختياري (مم)", "العمق الاختياري (م)"]
        for col, txt in zip(hc, headers):
            col.markdown(f"**{txt}**")
        st.markdown("<hr style='margin:8px 0;'>", unsafe_allow_html=True)

        for idx, line in enumerate(st.session_state.lines):
            cols = st.columns([0.5, 2.5, 1.5, 2, 2])
            cols[0].write(f"**{idx+1}**")
            
            new_name = cols[1].text_input("الاسم", value=line["name"], key=f"cost_name_{line['id']}", label_visibility="collapsed")
            if new_name != line["name"]:
                st.session_state.lines[idx]["name"] = new_name
                st.session_state.cost = None 
            
            cols[2].write(f"{line['length']:.1f} م")
            
            current_dia = line.get("diameter", 600)
            dia_options = sorted(PIPE_PRICES.keys())
            selected_dia = cols[3].selectbox(
                "القطر", dia_options,
                index=dia_options.index(current_dia) if current_dia in dia_options else 2,
                key=f"cost_dia_{line['id']}", label_visibility="collapsed"
            )
            if selected_dia != current_dia:
                st.session_state.lines[idx]["diameter"] = selected_dia
                st.session_state.cost = None

            current_depth = float(line.get("depth", 1.5))
            selected_depth = cols[4].number_input(
                "العمق", min_value=0.5, max_value=12.0, value=current_depth, step=0.1,
                key=f"cost_dep_{line['id']}", label_visibility="collapsed"
            )
            if selected_depth != current_depth:
                st.session_state.lines[idx]["depth"] = selected_depth
                st.session_state.cost = None

        st.markdown("---")

        if st.button("🧮 حساب وتحديث جدول كميات المشروع بالكامل", use_container_width=True):
            st.session_state.analyzer = NetworkAnalyzer(st.session_state.lines)
            ana = st.session_state.analyzer
            
            all_items = {}
            per_edge = []
            stat = ana.stats()
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
                    {"البند": "أنابيب صرف خرسانية مدعمة", "الكمية": L, "الوحدة": "متر طولي", "السعر": p_pipe, "الإجمالي": L * p_pipe},
                    {"البند": "أعمال حفر الخنادق المفتوحة للأنابيب", "الكمية": L, "الوحدة": "متر طولي", "السعر": EXCAVATION, "الإجمالي": L * EXCAVATION},
                    {"البند": "مناهل تفتيش خرسانية دائرية معتمدة", "الكمية": n_mh, "الوحدة": "عدد", "السعر": MANHOLE_PRICE, "الإجمالي": n_mh * MANHOLE_PRICE},
                    {"البند": "مصائد رمل وحطام جغرافية", "الكمية": n_tr, "الوحدة": "عدد", "السعر": TRAP_PRICE, "الإجمالي": n_tr * TRAP_PRICE},
                    {"البند": "إعادة الردم والتسوية والدمك الإنشائي للمسار", "الكمية": L * dep, "الوحدة": "متر مكعب", "السعر": BACKFILL_PRICE, "الإجمالي": L * dep * BACKFILL_PRICE},
                ]

                total = sum(it["الإجمالي"] for it in items)
                per_edge.append({
                    "line_name": edge["line_name"], "diameter": d, "depth": dep, "length": L,
                    "items": items, "total": total, "n_manholes": n_mh, "n_traps": n_tr,
                    "start_coord": edge["start_coord"], "end_coord": edge["end_coord"]
                })

                for it in items:
                    k = it["البند"]
                    if k not in all_items:
                        all_items[k] = {"الكمية": 0, "الإجمالي": 0, "الوحدة": it["الوحدة"]}
                    all_items[k]["الكمية"] += it["الكمية"]
                    all_items[k]["الإجمالي"] += it["الإجمالي"]

            st.session_state.cost = {
                "per_edge": per_edge, "all_items": all_items,
                "total_cost": sum(v["الإجمالي"] for v in all_items.values()),
                "stat": stat, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            st.success("✅ تم تحديث كشوفات التكلفة وحساب الكميات الهندسية بنجاح!")
            st.rerun()

        if st.session_state.cost:
            result = st.session_state.cost
            st.markdown("### 📊 كشف حساب وجدول كميات المشروع المعتمد")

            k1, k2, k3, k4 = st.columns(4)
            t_mh = sum(e["n_manholes"] for e in result["per_edge"])
            t_tr = sum(e["n_traps"] for e in result["per_edge"])
            
            k1.markdown(f'<div class="kpi-card"><div class="kpi-value">{t_mh}</div><div class="kpi-label">المناهل الكلية</div></div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="kpi-card"><div class="kpi-value">{t_tr}</div><div class="kpi-label">مصائد الحطام</div></div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(result["per_edge"])}</div><div class="kpi-label">عدد مسارات الفروع</div></div>', unsafe_allow_html=True)
            k4.markdown(f'<div class="kpi-card"><div class="kpi-value">{result["total_cost"]:,.0f}</div><div class="kpi-label">الميزانية الإجمالية التقديرية (SAR)</div></div>', unsafe_allow_html=True)

            rows_boq = [{"البند الإنشائي للمشروع": name, "الكمية المحسوبة": f"{data['الكمية']:,.2f}", "الوحدة": data["الوحدة"], "الإجمالي (ريال سعودي)": f"{data['الإجمالي']:,.2f}"} for name, data in result["all_items"].items()]
            st.dataframe(pd.DataFrame(rows_boq), use_container_width=True, hide_index=True)

            st.markdown(f'<div class="total-row">💰 صافي تكلفة البنود الإنشائية الرأسمالية: {result["total_cost"]:,.0f} ريال سعودي</div>', unsafe_allow_html=True)

            with st.expander("📂 استعراض الفواتير التحليلية والكميات لكل فرع على حدة"):
                for e in result["per_edge"]:
                    st.markdown(f"📌 **{e['line_name']}** — مواصفات مخصصة: [ القطر: {e['diameter']} مم | العمق: {e['depth']} م | الطول: {e['length']:.1f} م ]")
                    df_e = pd.DataFrame([{"البند": it["البند"], "الكمية": f"{it['الكمية']:,.2f}", "الوحدة": it["الوحدة"], "سعر الوحدة": f"{it['السعر']:,}", "الإجمالي (SAR)": f"{it['الإجمالي']:,.0f}"} for it in e["items"]])
                    st.dataframe(df_e, use_container_width=True, hide_index=True)
                    st.markdown(f"**إجمالي تكلفة هذا الفرع الفرعي بشكل مستقل: {e['total']:,.0f} ريال**")
                    st.markdown("<hr style='border-top:1px dashed #9aa4b8;'>", unsafe_allow_html=True)

# التبويب 4: التقرير والطباعة
with tabs[4]:
    st.markdown("<div class='section-title'>📋 تصدير التقارير الفنية وطباعة PDF</div>", unsafe_allow_html=True)

    if not st.session_state.cost:
        st.warning("⚠️ يرجى تفعيل وإجراء عملية حساب التكاليف والكميات من التبويب السابق أولاً.")
    else:
        result = st.session_state.cost
        ana = st.session_state.analyzer
        rep_sub1, rep_sub2 = st.tabs(["🗺️ خريطة تمايز الأقطار للتقرير", "📥 تحميل مستند الـ PDF الفني"])

        with rep_sub1:
            st.markdown("""<div class="info-banner">🗺️ كروكي تفاعلي ملون حسب أقطار الأنابيب المخصصة لكل فرع.</div>""", unsafe_allow_html=True)
            all_c = [pt for ln in st.session_state.lines for pt in ln["coords"]]
            m_rep = folium.Map(location=center_of(all_c), zoom_start=14, tiles="OpenStreetMap")
            Fullscreen().add_to(m_rep)

            diameter_legend_added = set()
            for edge_r in result["per_edge"]:
                d = edge_r["diameter"]
                color = PIPE_COLORS.get(d, "#1a5fa8")
                folium.PolyLine(
                    [edge_r["start_coord"], edge_r["end_coord"]], color=color, weight=6, opacity=0.9,
                    popup=f"<b>{edge_r['line_name']}</b><br>القطر: {d}مم<br>العمق: {edge_r['depth']}م<br>التكلفة: {edge_r['total']:,.0f} SAR"
                ).add_to(m_rep)
                diameter_legend_added.add(d)

            for coord, nid in ana.nodes_coords.items():
                folium.CircleMarker(location=coord, radius=8, color="#0a2a5e", fill=True, fillColor="#e63946").add_to(m_rep)

            legend_items = "".join([f'<div style="display:flex;align-items:center;margin:3px 0"><span style="display:inline-block;width:30px;height:6px;background:{PIPE_COLORS.get(d, "#1a5fa8")};border-radius:3px;margin-left:8px"></span>Ø{d} مم</div>' for d in sorted(diameter_legend_added)])
            legend_html = f'<div style="position:fixed; bottom:30px; right:30px; z-index:9999; background:white; padding:14px 18px; border-radius:10px; box-shadow:0 4px 14px rgba(0,0,0,0.15); font-family:\'Cairo\'; direction:rtl; font-size:13px; border-top:4px solid #1a5fa8;"><b>دليل الأقطار</b><br>{legend_items}</div>'
            m_rep.get_root().html.add_child(folium.Element(legend_html))
            
            m_rep.fit_bounds(get_bounds(all_c))
            st_folium(m_rep, width=None, height=550, key="report_map")

        with rep_sub2:
            proj_name = st.text_input("اسم المشروع الرسمي بالتقرير", value="مشروع شبكة صرف سيلي متكامل")
            proj_owner = st.text_input("الجهة المالكة للمشروع", value="أمانة المنطقة")
            engineer = st.text_input("اسم المهندس المسؤول", value="")
            
            st.markdown("#### 🌍 إرفاق كروكي خريطة الخلفية للـ PDF")
            uploaded_map_img = st.file_uploader("ارفع لقطة شاشة خريطة OpenStreetMap (اختياري)", type=["png", "jpg", "jpeg"])

            if st.button("📥 إنشاء وتحميل التقرير الهندسي PDF النهائي", use_container_width=True):
                with st.spinner("جاري صياغة ملف PDF..."):
                    try:
                        from reportlab.lib.pagesizes import landscape, A4
                        from reportlab.lib import colors
                        from reportlab.lib.units import mm
                        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, PageBreak, Image
                        from reportlab.lib.styles import ParagraphStyle
                        from reportlab.lib.enums import TA_CENTER

                        buf = io.BytesIO()
                        doc = SimpleDocTemplate(buf, pagesize=landscape(A4), rightMargin=15*mm, leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)

                        BLUE, LBLUE, GREY, WHITE = colors.HexColor("#0a2a5e"), colors.HexColor("#1a5fa8"), colors.HexColor("#f0f4f8"), colors.white
                        s_title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20, textColor=WHITE, alignment=TA_CENTER)
                        s_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, textColor=BLUE, spaceBefore=10, spaceAfter=6)
                        s_norm = ParagraphStyle("n", fontName="Helvetica", fontSize=10)
                        s_footer = ParagraphStyle("f", fontName="Helvetica", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)

                        elems = []
                        elems.append(Table([[Paragraph(f"FLOOD INFRASTRUCTURE ENGINEERING REPORT<br/><font size=11>{proj_name}</font>", s_title)]], colWidths=[265*mm], style=[('BACKGROUND', (0,0), (-1,-1), BLUE), ('PADDING', (0,0), (-1,-1), 15), ('ROUNDEDCORNERS', (0,0), (-1,-1), [6,6,6,6])]))
                        elems.append(Spacer(1, 6*mm))

                        info_data = [["Project Client / Owner:", proj_owner, "Calculation Timestamp:", result["generated_at"]], ["Lead Reviewing Engineer:", engineer or "Engineering Dept", "System Engine Version:", "v14.0 المطور"]]
                        info_tbl = Table(info_data, colWidths=[55*mm, 75*mm, 45*mm, 90*mm], style=[('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")), ('BACKGROUND', (0,0), (0,-1), GREY), ('BACKGROUND', (2,0), (2,-1), GREY), ('PADDING', (0,0), (-1,-1), 6)])
                        elems.append(info_tbl)
                        elems.append(Spacer(1, 6*mm))

                        if uploaded_map_img:
                            elems.append(Paragraph("GEOGRAPHICAL INFRASTRUCTURE ROUTE LAYOUT", s_h2))
                            elems.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=4))
                            elems.append(Image(uploaded_map_img, width=260*mm, height=120*mm))
                            elems.append(PageBreak())

                        elems.append(Paragraph("1. DIRECT COST INFRASTRUCTURE BILL OF QUANTITIES (BOQ)", s_h2))
                        boq_data = [["Item Description Specification", "Calculated Qty", "Unit", "Total (SAR)"]]
                        for name, d in result["all_items"].items():
                            boq_data.append([name, f"{d['الكمية']:,.2f}", d.get("الوحدة", "Unit"), f"{d['الإجمالي']:,.0f} SAR"])
                        boq_data.append(["TOTAL PROJECT BUDGET ESTIMATION", "", "", f"{result['total_cost']:,.0f} SAR"])

                        boq_tbl = Table(boq_data, colWidths=[110*mm, 40*mm, 35*mm, 80*mm], style=[('BACKGROUND', (0,0), (-1,0), LBLUE), ('TEXTCOLOR', (0,0), (-1,0), WHITE), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")), ('PADDING', (0,0), (-1,-1), 6), ('BACKGROUND', (0,-1), (-1,-1), BLUE), ('TEXTCOLOR', (0,-1), (-1,-1), WHITE), ('FONTNAME', (0,-1), (-1,-1), "Helvetica-Bold")])
                        elems.append(boq_tbl)

                        elems.append(PageBreak())
                        elems.append(Paragraph("2. INDIVIDUAL STORM SEGMENTS TECHNICAL PARAMETERS & SPECIFICATIONS", s_h2))
                        branch_data = [["Segment ID", "Length (m)", "Assigned Diameter (mm)", "Assigned Excavation Depth (m)", "Manholes", "Traps", "Subtotal Cost"]]
                        for e in result["per_edge"]:
                            branch_data.append([e["line_name"], f"{e['length']:.1f}", str(e["diameter"]), str(e["depth"]), str(e["n_manholes"]), str(e["n_traps"]), f"{e['total']:,.0f} SAR"])

                        br_tbl = Table(branch_data, colWidths=[55*mm, 30*mm, 45*mm, 50*mm, 25*mm, 20*mm, 40*mm], style=[('BACKGROUND', (0,0), (-1,0), LBLUE), ('TEXTCOLOR', (0,0), (-1,0), WHITE), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")), ('PADDING', (0,0), (-1,-1), 5), ('ALIGN', (1,0), (-1,-1), "CENTER")])
                        elems.append(br_tbl)
                        
                        elems.append(Spacer(1, 10*mm))
                        elems.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d0d8e8")))
                        elems.append(Paragraph(f"Stormwater Infrastructure Analysis Solution Suite  | Report Generated: {result['generated_at']}", s_footer))

                        doc.build(elems)
                        buf.seek(0)

                        st.download_button(
                            label="📥 اضغط هنا لبدء تحميل ملف التقرير الهندسي PDF المعتمد", data=buf.getvalue(),
                            file_name=f"Stormwater_Network_BOQ_Report.pdf", mime="application/pdf", use_container_width=True
                        )
                    except Exception as ex:
                        st.error(f"❌ خطأ أثناء صياغة مستند الـ PDF: {ex}")

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""<div style="text-align:center;color:#9aa4b8;font-size:0.85rem;padding:16px 0">🌊 محلل شبكات ومصارف السيول — لوحة التحكم الذكية المحدثة والتركيز التلقائي</div>""", unsafe_allow_html=True)

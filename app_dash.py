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

try:
    from staticmap import StaticMap, Line as SMLine, CircleMarker as SMCircle
    STATICMAP_AVAILABLE = True
except Exception:
    STATICMAP_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# دعم اللغة العربية في تقرير PDF (تشكيل الحروف + اتجاه RTL + خط Amiri)
# ─────────────────────────────────────────────────────────────────────────────
import os as _os
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SHAPING_AVAILABLE = True
except Exception:
    ARABIC_SHAPING_AVAILABLE = False

_FONT_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "assets", "fonts")
ARABIC_FONT_REGULAR = "Amiri"
ARABIC_FONT_BOLD = "Amiri-Bold"
ARABIC_FONT_AVAILABLE = False

def register_arabic_fonts():
    """يسجّل خط Amiri (عادي وغامق) لدى ReportLab لدعم رسم النصوص العربية بشكل صحيح."""
    global ARABIC_FONT_AVAILABLE
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        reg_path = _os.path.join(_FONT_DIR, "Amiri-Regular.ttf")
        bold_path = _os.path.join(_FONT_DIR, "Amiri-Bold.ttf")
        if _os.path.exists(reg_path) and _os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont(ARABIC_FONT_REGULAR, reg_path))
            pdfmetrics.registerFont(TTFont(ARABIC_FONT_BOLD, bold_path))
            ARABIC_FONT_AVAILABLE = True
        else:
            ARABIC_FONT_AVAILABLE = False
    except Exception:
        ARABIC_FONT_AVAILABLE = False
    return ARABIC_FONT_AVAILABLE

def ar(text):
    """
    يحوّل أي نص عربي (أو مختلط) إلى الصيغة الصحيحة للعرض في PDF:
    تشكيل اتصال الحروف العربية (reshaping) ثم ترتيب الاتجاه البصري (bidi).
    الأرقام والنصوص الإنجليزية تبقى دون تأثير.
    """
    text = str(text)
    if not ARABIC_SHAPING_AVAILABLE:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text

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
# 🔧 تهيئة متغيرات Session State (إصلاح مشكلة AttributeError)
# ─────────────────────────────────────────────────────────────────────────────
if "cost" not in st.session_state:
    st.session_state.cost = None

if "analyzer" not in st.session_state:
    st.session_state.analyzer = None

if "lines" not in st.session_state:
    st.session_state.lines = []

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
# أنماط خلفية الخريطة (تُستخدم في الخرائط التفاعلية وفي خريطة تقرير الـ PDF)
# ─────────────────────────────────────────────────────────────────────────────
MAP_STYLES = {
    "🗺️ خريطة الشوارع (OpenStreetMap)": {
        "tiles": "OpenStreetMap",
        "attr": None,
        "static_url": "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "label_en": "OpenStreetMap",
    },
    "🛰️ صورة جوية (أقمار صناعية)": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        "static_url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "label_en": "Satellite Imagery (Esri World Imagery)",
    },
    "⚪ خريطة فاتحة مبسطة (Carto Positron)": {
        "tiles": "CartoDB positron",
        "attr": None,
        "static_url": "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "label_en": "Light Basemap (CartoDB Positron)",
    },
    "⛰️ خريطة تضاريس (OpenTopoMap)": {
        "tiles": "https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
        "attr": "Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)",
        "static_url": "https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
        "label_en": "Terrain (OpenTopoMap)",
    },
}
DEFAULT_MAP_STYLE = "🗺️ خريطة الشوارع (OpenStreetMap)"

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

def renumber_lines():
    """يعيد ترقيم جميع الفروع بأسماء رمزية فريدة ومتسلسلة (PIPE1, PIPE2, ...) لتمييزها في الخريطة والبيانات."""
    for i, ln in enumerate(st.session_state.lines):
        ln["code"] = f"PIPE{i+1}"

def split_and_add_branches(coords, group_label=None, base_diameter=600, base_depth=1.5):
    """
    يقسّم أي خط (متعدد النقاط) إلى فروع مستقلة — فرع واحد لكل ضلع بين نقطتين متتاليتين.
    كل فرع ناتج يحصل على معرّف/ترقيم خاص به (PIPE..) وبيانات قطر وعمق مستقلة تماماً
    عن بقية فروع نفس الخط الأصلي، بدلاً من اعتبار الخط بأكمله فرعاً واحداً.
    يعيد قائمة الفروع الجديدة المضافة فعلياً.
    """
    coords = [tuple(c[:2]) for c in coords]
    if len(coords) < 2:
        return []
    if group_label is None:
        st.session_state.group_counter = st.session_state.get("group_counter", 0) + 1
        group_label = f"خط {st.session_state.group_counter}"
    multi = len(coords) > 2
    added = []
    for i in range(len(coords) - 1):
        s, e = coords[i], coords[i + 1]
        if s == e:
            continue
        seg_len = haversine(s, e)
        new_branch = {
            "id": str(uuid.uuid4()),
            "name": f"{group_label} - جزء {i+1}" if multi else group_label,
            "group": group_label,
            "code": "",
            "length": seg_len,
            "coords": [s, e],
            "diameter": base_diameter,
            "depth": base_depth,
            "selected": True,
        }
        st.session_state.lines.append(new_branch)
        added.append(new_branch)
    renumber_lines()
    st.session_state.analyzer = None
    st.session_state.cost = None
    return added

def make_base_map(location, zoom_start, style_key=None):
    """ينشئ خريطة folium بخلفية حسب النمط المختار (شوارع / صورة جوية / أخرى)."""
    style_key = style_key or st.session_state.get("map_style", DEFAULT_MAP_STYLE)
    style = MAP_STYLES.get(style_key, MAP_STYLES[DEFAULT_MAP_STYLE])
    if style.get("attr"):
        return folium.Map(location=location, zoom_start=zoom_start, tiles=style["tiles"], attr=style["attr"])
    return folium.Map(location=location, zoom_start=zoom_start, tiles=style["tiles"])

# ─────────────────────────────────────────────────────────────────────────────
# ترجمة أسماء البنود والوحدات إلى الإنجليزية (تُستخدم حصرياً داخل تقرير PDF)
# ─────────────────────────────────────────────────────────────────────────────
ITEM_NAME_EN = {
    "أنابيب صرف خرسانية مدعمة": "Reinforced Concrete Drainage Pipes",
    "أعمال حفر الخنادق المفتوحة للأنابيب": "Open Trench Excavation Works",
    "مناهل تفتيش خرسانية دائرية معتمدة": "Approved Circular Concrete Inspection Manholes",
    "مصائد مياه الأمطار": "Rainwater Catch Basins",
    "إعادة الردم والتسوية والدمك الإنشائي للمسار": "Backfilling, Grading & Structural Compaction",
}
UNIT_NAME_EN = {
    "متر طولي": "Linear Meter (L.M.)",
    "عدد": "No.",
    "متر مكعب": "Cubic Meter (m3)",
}
def en_item(name):
    return ITEM_NAME_EN.get(name, name)
def en_unit(u):
    return UNIT_NAME_EN.get(u, u)

def get_bounds(coords):
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return [[min(lats)-0.002, min(lons)-0.002], [max(lats)+0.002, max(lons)+0.002]]

def center_of(coords):
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return [(min(lats)+max(lats))/2, (min(lons)+max(lons))/2]

def render_static_map(per_edge, nodes_coords, pipe_colors, style_key=None, width=1400, height=750):
    """
    يولّد صورة PNG لخريطة الشبكة بخلفية حقيقية (شوارع OpenStreetMap، صورة جوية، أو نمط آخر
    يختاره المستخدم)، مع تلوين كل فرع حسب القطر ورسم المناهل، لتُضمَّن مباشرة داخل تقرير PDF.
    يعيد bytes الصورة (PNG) أو None إذا تعذّر الاتصال بخوادم البلاطات.
    """
    if not STATICMAP_AVAILABLE:
        return None
    style_key = style_key or DEFAULT_MAP_STYLE
    style = MAP_STYLES.get(style_key, MAP_STYLES[DEFAULT_MAP_STYLE])
    try:
        m = StaticMap(
            width, height,
            url_template=style["static_url"],
            headers={"User-Agent": "FloodNetworkAnalyzer/1.0 (engineering report generator)"},
        )

        for e in per_edge:
            d = e["diameter"]
            hex_color = pipe_colors.get(d, "#1a5fa8")
            # staticmap يستقبل الإحداثيات بصيغة (lon, lat)
            coords_lonlat = [
                (e["start_coord"][1], e["start_coord"][0]),
                (e["end_coord"][1], e["end_coord"][0]),
            ]
            m.add_line(SMLine(coords_lonlat, hex_color, 5))

        for coord in nodes_coords.keys():
            m.add_marker(SMCircle((coord[1], coord[0]), "#ffffff", 12))
            m.add_marker(SMCircle((coord[1], coord[0]), "#e63946", 9))
            m.add_marker(SMCircle((coord[1], coord[0]), "#0a2a5e", 4))

        img = m.render()
        out = io.BytesIO()
        img.save(out, format="PNG")
        out.seek(0)
        return out.getvalue()
    except Exception:
        return None

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
                    "code": line.get("code", ""),
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
for key, val in [
    ("lines", []), ("analyzer", None), ("cost", None),
    ("map_style", DEFAULT_MAP_STYLE), ("group_counter", 0),
]:
    if key not in st.session_state:
        st.session_state[key] = val

# ─────────────────────────────────────────────────────────────────────────────
# التبويبات الرئيسية
# ─────────────────────────────────────────────────────────────────────────────
TAB_LABELS = [
    "🏠 الرئيسية",
    "🗺️ ١ · رسم وإدخال",
    "🌐 ٢ · التحليل والتكاليف",
    "📋 ٣ · التقرير والطباعة",
]
tabs = st.tabs(TAB_LABELS)

# التبويب 0: الرئيسية
with tabs[0]:
    st.markdown("<div class='section-title'>خطوات استخدام التطبيق</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    steps = [
        ("🗺️", "١ · رسم وإدخال", "ارسم خطوط الشبكة مباشرة على الخريطة أو استورد ملفات GeoJSON / Shapefile"),
        ("🌐", "٢ · التحليل والتكاليف", "لكل فرع رمز مميز (PIPE1, PIPE2...)، حدّد قطر وعمق مختلف لكل فرع، واحسب الكميات والتكلفة فوراً في نفس المكان"),
        ("📋", "٣ · التقرير", "تصدير تقرير PDF كامل (باللغة الإنجليزية) مع خريطة OpenStreetMap وجداول الكميات والتكاليف"),
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

    st.markdown("<div class='section-title'>ملخص المشروع</div>", unsafe_allow_html=True)
    km1, km2, km3, km4 = st.columns(4)
    n_lines  = len(st.session_state.get("lines", []))
    analyzer = st.session_state.get("analyzer")
    n_nodes  = analyzer.stats()["nodes"] if analyzer else 0
    tot_km   = (analyzer.stats()["length"]/1000) if analyzer else 0.0
    cost_data = st.session_state.get("cost")
    tot_cost = cost_data["total_cost"] if cost_data else 0

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

    style_keys = list(MAP_STYLES.keys())
    sel_style = st.selectbox(
        "🎨 نمط خلفية الخريطة التفاعلية (شوارع / صورة جوية / أخرى)",
        style_keys,
        index=style_keys.index(st.session_state.map_style) if st.session_state.map_style in style_keys else 0,
        key="map_style_selector_tab1",
    )
    st.session_state.map_style = sel_style

    st.markdown("""
    <div class="info-banner">
        📌 <b>مهم:</b> أي خط يحتوي على أكثر من نقطتين (رسماً أو استيراداً) يُقسَّم تلقائياً إلى
        <b>فروع مستقلة</b> — فرع واحد بين كل نقطتين متتاليتين، وكل فرع يأخذ <b>ترقيماً خاصاً به</b>
        (PIPE1, PIPE2, ...) ويمكن إدخال قطر وعمق مختلفين لكل فرع على حدة من تبويب «التحليل والتكاليف».
    </div>
    """, unsafe_allow_html=True)

    sub1, sub_manual, sub2, sub3 = st.tabs([
        "✏️ رسم على الخريطة", "⌨️ إدخال يدوي بالإحداثيات", "📤 استيراد GeoJSON", "📦 استيراد Shapefile"
    ])

    with sub1:
        st.markdown("""
        <div class="info-banner">
            📌 استخدم أداة الرسم في أعلى يسار الخريطة لرسم خطوط الشبكة. انقر لإضافة نقاط ثم انقر مرتين لإنهاء الخط.
            كل ضلع بين نقطتين متتاليتين سيُضاف كفرع مستقل بترقيمه الخاص.
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.lines:
            all_c = [pt for ln in st.session_state.lines for pt in ln["coords"]]
            map_center = center_of(all_c)
            zoom = 14
        else:
            map_center = [24.7136, 46.6753]
            zoom = 12

        m_draw = make_base_map(map_center, zoom)
        Fullscreen(title="ملء الشاشة").add_to(m_draw)
        MiniMap(toggle_display=True).add_to(m_draw)

        for ln in st.session_state.lines:
            coords = ln.get("coords", [])
            if coords:
                folium.PolyLine(coords, color="#e63946", weight=4, opacity=0.9, tooltip=f"{ln.get('code','')} — {ln['name']}").add_to(m_draw)
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
                    draw_hash = hash(json.dumps(raw_coords))
                    if st.session_state.get("_last_draw_hash") != draw_hash:
                        st.session_state["_last_draw_hash"] = draw_hash
                        added = split_and_add_branches(coords)
                        if added:
                            codes_txt = "، ".join(b["code"] for b in added)
                            st.success(f"✅ تمت إضافة {len(added)} فرع جديد: {codes_txt}")
                            st.rerun()

        if st.session_state.lines:
            st.markdown("---")
            st.markdown("**الفروع المدخلة حالياً:**")
            for i, ln in enumerate(st.session_state.lines):
                c0_, c1_, c2_, c3_ = st.columns([1, 3.5, 2, 1])
                with c0_:
                    st.markdown(f"<b>{ln.get('code', f'PIPE{i+1}')}</b>", unsafe_allow_html=True)
                with c1_:
                    st.session_state.lines[i]["name"] = st.text_input("الاسم", value=ln["name"], key=f"name_{ln['id']}", label_visibility="collapsed")
                    if ln.get("group"):
                        st.caption(f"المجموعة الأصلية: {ln['group']} · Ø{ln.get('diameter',600)} مم · عمق {ln.get('depth',1.5)} م")
                with c2_:
                    st.write(f"📏 {ln['length']:.1f} م")
                with c3_:
                    if st.button("🗑️", key=f"del_{ln['id']}"):
                        st.session_state.lines.pop(i)
                        renumber_lines()
                        st.session_state.analyzer = None
                        st.session_state.cost = None
                        st.rerun()

            if st.button("🗑️ حذف جميع الفروع", use_container_width=True):
                st.session_state.lines = []
                st.session_state.analyzer = None
                st.session_state.cost = None
                st.rerun()

    with sub_manual:
        st.markdown("""
        <div class="info-banner">
            ⌨️ أضف فرعاً جديداً مباشرة بإدخال إحداثيات <b>بداية الفرع ونهايته</b> بالإضافة إلى
            <b>القطر والعمق</b>، وستظهر النتيجة فوراً على الخريطة أدناه.
        </div>
        """, unsafe_allow_html=True)

        with st.form("manual_add_form", clear_on_submit=True):
            cA, cB = st.columns(2)
            m_name = cA.text_input("اسم الفرع (اختياري)", value="")
            m_group = cB.text_input("اسم المجموعة/المسار (اختياري)", value="")

            st.markdown("**إحداثيات بداية الفرع**")
            c1, c2 = st.columns(2)
            lat1 = c1.number_input("خط العرض Lat (بداية)", value=24.713600, format="%.6f", key="man_lat1")
            lon1 = c2.number_input("خط الطول Lon (بداية)", value=46.675300, format="%.6f", key="man_lon1")

            st.markdown("**إحداثيات نهاية الفرع**")
            c3, c4 = st.columns(2)
            lat2 = c3.number_input("خط العرض Lat (نهاية)", value=24.715600, format="%.6f", key="man_lat2")
            lon2 = c4.number_input("خط الطول Lon (نهاية)", value=46.677300, format="%.6f", key="man_lon2")

            st.markdown("**مواصفات الفرع**")
            c5, c6 = st.columns(2)
            dia_opts = sorted(PIPE_PRICES.keys())
            m_dia = c5.selectbox("القطر (مم)", dia_opts, index=2)
            m_depth = c6.number_input("العمق (م)", min_value=0.5, max_value=12.0, value=1.5, step=0.1)

            submit_manual = st.form_submit_button("➕ إضافة الفرع إلى الشبكة", use_container_width=True)

        if submit_manual:
            if abs(lat1 - lat2) < 1e-9 and abs(lon1 - lon2) < 1e-9:
                st.error("❌ إحداثيات البداية والنهاية متطابقة — الرجاء إدخال نقطتين مختلفتين.")
            elif not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180):
                st.error("❌ إحداثيات غير صالحة — تأكد من نطاق خط العرض [-90, 90] وخط الطول [-180, 180].")
            else:
                group_label = m_group.strip() or None
                added = split_and_add_branches(
                    [(lat1, lon1), (lat2, lon2)],
                    group_label=group_label,
                    base_diameter=m_dia,
                    base_depth=m_depth,
                )
                if added:
                    if m_name.strip():
                        added[0]["name"] = m_name.strip()
                    st.success(f"✅ تمت إضافة الفرع {added[0]['code']} بنجاح — الطول: {added[0]['length']:.1f} م")
                    st.rerun()

        if st.session_state.lines:
            st.markdown("---")
            st.markdown("**🗺️ معاينة مباشرة لجميع فروع الشبكة الحالية**")
            all_c = [pt for ln in st.session_state.lines for pt in ln["coords"]]
            m_prev = make_base_map(center_of(all_c), 14)
            Fullscreen(title="ملء الشاشة").add_to(m_prev)
            for ln in st.session_state.lines:
                coords = ln.get("coords", [])
                if coords:
                    folium.PolyLine(
                        coords, color="#e63946", weight=4, opacity=0.9,
                        tooltip=f"{ln.get('code','')} — {ln['name']} — Ø{ln.get('diameter',600)} مم"
                    ).add_to(m_prev)
                    folium.CircleMarker(coords[0], radius=5, color="#0a2a5e", fill=True, fillColor="#1a5fa8").add_to(m_prev)
                    folium.CircleMarker(coords[-1], radius=5, color="#e63946", fill=True, fillColor="#e63946").add_to(m_prev)
            m_prev.fit_bounds(get_bounds(all_c))
            st_folium(m_prev, width=None, height=420, key="manual_preview_map")

    with sub2:
        st.markdown("""
        <div class="info-banner">
            📌 كل LineString داخل ملف GeoJSON يُقسَّم تلقائياً إلى فروع مستقلة (فرع بين كل نقطتين متتاليتين).
        </div>
        """, unsafe_allow_html=True)
        uploaded_geojson = st.file_uploader("اختر ملف GeoJSON", type=["geojson", "json"], key="geo_up")
        if uploaded_geojson:
            try:
                gj = json.load(uploaded_geojson)
                features = gj.get("features", [])
                added_total = 0
                for feat in features:
                    geom = feat.get("geometry", {})
                    if geom.get("type") == "LineString":
                        coords = [(c[1], c[0]) for c in geom.get("coordinates", [])]
                        if len(coords) >= 2:
                            feat_name = feat.get("properties", {}).get("name")
                            added_total += len(split_and_add_branches(coords, group_label=feat_name))
                st.success(f"✅ تمت إضافة {added_total} فرع من ملف GeoJSON")
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ في الملف: {e}")

    with sub3:
        st.markdown("""
        <div class="info-banner">
            📌 كل خط داخل ملف Shapefile يُقسَّم تلقائياً إلى فروع مستقلة (فرع بين كل نقطتين متتاليتين).
        </div>
        """, unsafe_allow_html=True)
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
                            added_total = 0
                            for idx, row in gdf.iterrows():
                                if row.geometry and row.geometry.geom_type == "LineString":
                                    coords = [(lat, lon) for lon, lat in row.geometry.coords]
                                    if len(coords) >= 2:
                                        added_total += len(split_and_add_branches(coords))
                            st.success(f"✅ تمت إضافة {added_total} فرع من ملف Shapefile")
                            st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
        else:
            st.warning("⚠️ مكتبة geopandas غير مثبتة.")

# التبويب 2: تحليل الشبكة
with tabs[2]:
    st.markdown("<div class='section-title'>🌐 تحليل الشبكة والتكاليف</div>", unsafe_allow_html=True)

    if not st.session_state.lines:
        st.warning("⚠️ يرجى إضافة ورسم مسارات خطوط أولاً من التبويب السابق.")
    else:
        # تحليل تلقائي للشبكة عند أي تغيير في الخطوط
        st.session_state.analyzer = NetworkAnalyzer(st.session_state.lines)
        ana = st.session_state.analyzer
        stat = ana.stats()

        # ── مؤشرات الشبكة العامة ──────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        for col, val, lbl in zip(
            [k1, k2, k3, k4],
            [stat["nodes"], stat["edges"], f"{stat['length']/1000:.2f} كم", stat["components"]],
            ["مناهل التفتيش الكلية (عقد)", "الفروع الهيدروليكية (حواف)", "الطول الإجمالي للشبكة", "الأجزاء المستقلة المتصلة"]
        ):
            with col:
                st.markdown(f'<div class="kpi-card"><div class="kpi-value">{val}</div><div class="kpi-label">{lbl}</div></div>', unsafe_allow_html=True)

        st.markdown("---")

        # ── خريطة تحليلية مع تكبير على فرع مختار ──────────────────────────
        st.markdown("#### 🔍 تحديد فرع لعمل تكبير (Zoom) تلقائي عليه")
        line_labels = [f"{ln.get('code', '')} — {ln['name']}" for ln in st.session_state.lines]
        label_to_name = {f"{ln.get('code', '')} — {ln['name']}": ln["name"] for ln in st.session_state.lines}
        target_focus_label = st.selectbox(
            "اختر الفرع المراد عمل التكبير والتركيز المباشر عليه:",
            ["كامل الشبكة"] + line_labels,
            key="analysis_focus_select",
        )
        target_focus = label_to_name.get(target_focus_label, "كامل الشبكة")

        st.markdown("#### 🗺️ خريطة الفروع والعقد الهندسية")

        full_c = [pt for ln in st.session_state.lines for pt in ln["coords"]]
        if target_focus_label == "كامل الشبكة":
            focus_c = full_c
        else:
            focus_c = next(ln["coords"] for ln in st.session_state.lines if ln["name"] == target_focus)

        m_net = make_base_map(center_of(focus_c), 16)
        Fullscreen(title="ملء الشاشة").add_to(m_net)

        for e in ana.edges_list:
            is_target = (target_focus_label == "كامل الشبكة" or e["line_name"] == target_focus)
            weight_render  = 8 if is_target else 4
            opacity_render = 1.0 if is_target else 0.35
            color_render   = "#e63946" if (is_target and target_focus_label != "كامل الشبكة") else "#1a5fa8"
            folium.PolyLine(
                [e["start_coord"], e["end_coord"]],
                color=color_render, weight=weight_render, opacity=opacity_render,
                tooltip=f"{e.get('code','')} — {e['line_name']} — Ø{e['diameter']}مم — {e['distance']:.1f} م"
            ).add_to(m_net)

        for coord, nid in ana.nodes_coords.items():
            folium.CircleMarker(
                location=coord, radius=7, color="#0a2a5e",
                fill=True, fillColor="#e63946", fillOpacity=0.9,
                tooltip=f"منهل #{nid}"
            ).add_to(m_net)

        m_net.fit_bounds(get_bounds(focus_c), max_zoom=18)
        st_folium(m_net, width=None, height=550, key=f"analysis_map_{target_focus}")

        st.markdown("---")

        # ── إعداد كل فرع بشكل مستقل (الرمز، الاسم، القطر، العمق) ───────────
        st.markdown("#### ⚙️ مواصفات كل فرع على حدة (رمز الفرع، القطر، العمق)")
        st.markdown("""
        <div class="info-banner">
            📌 لكل فرع <b>رمز تعريفي فريد</b> (PIPE1, PIPE2, ...) يظهر على الخريطة وفي جميع الجداول. حدّد
            <b>القطر (مم) والعمق (م)</b> بشكل مستقل لكل فرع — يُعاد احتساب الكميات والتكلفة تلقائياً وفوراً مع أي تعديل، من هذا المكان فقط.
        </div>
        """, unsafe_allow_html=True)

        hc = st.columns([1, 2.3, 1.3, 1.8, 1.8])
        headers = ["الرمز", "اسم الفرع", "الطول (م)", "القطر (مم)", "العمق (م)"]
        for col, txt in zip(hc, headers):
            col.markdown(f"**{txt}**")
        st.markdown("<hr style='margin:8px 0;'>", unsafe_allow_html=True)

        for idx, line in enumerate(st.session_state.lines):
            cols = st.columns([1, 2.3, 1.3, 1.8, 1.8])
            cols[0].markdown(f"**{line.get('code', f'PIPE{idx+1}')}**")

            new_name = cols[1].text_input("الاسم", value=line["name"], key=f"cost_name_{line['id']}", label_visibility="collapsed")
            if new_name != line["name"]:
                st.session_state.lines[idx]["name"] = new_name

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

            current_depth = float(line.get("depth", 1.5))
            selected_depth = cols[4].number_input(
                "العمق", min_value=0.5, max_value=12.0, value=current_depth, step=0.1,
                key=f"cost_dep_{line['id']}", label_visibility="collapsed"
            )
            if selected_depth != current_depth:
                st.session_state.lines[idx]["depth"] = selected_depth

        st.markdown("---")

        recalc = st.button("🧮 حساب وتحديث جدول كميات المشروع بالكامل", use_container_width=True)

        # ✅ يُعاد الحساب تلقائياً وبشكل مباشر من مواصفات الفروع أعلاه في كل مرة
        # (مصدر وحيد للبيانات — لا يوجد أي إدخال مكرر للقطر/العمق في مكان آخر)
        st.session_state.analyzer = NetworkAnalyzer(st.session_state.lines)
        ana = st.session_state.analyzer

        all_items = {}
        per_edge = []
        stat = ana.stats()

        # عدد المناهل يُشتق مباشرة من بيانات التحليل (عقد الشبكة الفعلية) بحيث
        # لا يتكرر احتساب نفس المنهل المشترك بين فرعين مرتين، ويكون المجموع مطابقاً
        # تماماً لعدد "مناهل التفتيش الكلية" الظاهر في مؤشرات التحليل أعلاه.
        assigned_nodes = set()
        for edge in ana.edges_list:
            new_nodes = [n for n in (edge["node_start"], edge["node_end"]) if n not in assigned_nodes]
            assigned_nodes.update(new_nodes)
            n_mh = len(new_nodes)
            n_tr = num_traps(edge["distance"])

            d = edge["diameter"]
            dep = edge["depth"]
            L = edge["distance"]
            p_pipe = PIPE_PRICES.get(d, 725)

            items = [
                {"البند": "أنابيب صرف خرسانية مدعمة", "الكمية": L, "الوحدة": "متر طولي", "السعر": p_pipe, "الإجمالي": L * p_pipe},
                {"البند": "أعمال حفر الخنادق المفتوحة للأنابيب", "الكمية": L, "الوحدة": "متر طولي", "السعر": EXCAVATION, "الإجمالي": L * EXCAVATION},
                {"البند": "مناهل تفتيش خرسانية دائرية معتمدة", "الكمية": n_mh, "الوحدة": "عدد", "السعر": MANHOLE_PRICE, "الإجمالي": n_mh * MANHOLE_PRICE},
                {"البند": "مصائد مياه الأمطار", "الكمية": n_tr, "الوحدة": "عدد", "السعر": TRAP_PRICE, "الإجمالي": n_tr * TRAP_PRICE},
                {"البند": "إعادة الردم والتسوية والدمك الإنشائي للمسار", "الكمية": L * dep, "الوحدة": "متر مكعب", "السعر": BACKFILL_PRICE, "الإجمالي": L * dep * BACKFILL_PRICE},
            ]

            total = sum(it["الإجمالي"] for it in items)
            per_edge.append({
                "line_name": edge["line_name"], "code": edge.get("code", ""), "diameter": d, "depth": dep, "length": L,
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
        if recalc:
            st.success("✅ تم تحديث كشوفات التكلفة وحساب الكميات الهندسية بنجاح!")

        # ── عرض نتائج التكاليف ─────────────────────────────────────────────
        if st.session_state.cost:
            result = st.session_state.cost
            st.markdown("### 📊 كشف حساب وجدول كميات المشروع المعتمد")

            k1, k2, k3, k4 = st.columns(4)
            t_mh = sum(e["n_manholes"] for e in result["per_edge"])
            t_tr = sum(e["n_traps"] for e in result["per_edge"])

            k1.markdown(f'<div class="kpi-card"><div class="kpi-value">{t_mh}</div><div class="kpi-label">المناهل الكلية</div></div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="kpi-card"><div class="kpi-value">{t_tr}</div><div class="kpi-label">مصائد الأمطار</div></div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(result["per_edge"])}</div><div class="kpi-label">عدد مسارات الفروع</div></div>', unsafe_allow_html=True)
            k4.markdown(f'<div class="kpi-card"><div class="kpi-value">{result["total_cost"]:,.0f}</div><div class="kpi-label">الميزانية الإجمالية التقديرية (SAR)</div></div>', unsafe_allow_html=True)

            rows_boq = [{"البند الإنشائي للمشروع": name, "الكمية المحسوبة": f"{data['الكمية']:,.2f}", "الوحدة": data["الوحدة"], "الإجمالي (ريال سعودي)": f"{data['الإجمالي']:,.2f}"} for name, data in result["all_items"].items()]
            st.dataframe(pd.DataFrame(rows_boq), use_container_width=True, hide_index=True)

            st.markdown(f'<div class="total-row">💰 صافي تكلفة البنود الإنشائية الرأسمالية: {result["total_cost"]:,.0f} ريال سعودي</div>', unsafe_allow_html=True)

            with st.expander("📂 استعراض الفواتير التحليلية والكميات لكل فرع على حدة"):
                st.markdown("""
                <div class="info-banner">
                ℹ️ هذا العرض للاطلاع فقط. لتعديل القطر أو العمق استخدم جدول <b>«مواصفات كل فرع على حدة»</b> أعلاه —
                فهو المصدر الوحيد للبيانات، وأي تعديل هناك ينعكس فوراً هنا وعلى التكلفة.
                </div>
                """, unsafe_allow_html=True)

                for e in result["per_edge"]:
                    st.markdown(f"📌 **{e.get('code','')} — {e['line_name']}** — الطول: {e['length']:.1f} م — القطر: Ø{e['diameter']} مم — العمق: {e['depth']} م")

                    ecol3, = st.columns([1])
                    with ecol3:
                        st.metric("إجمالي تكلفة الفرع", f"{e['total']:,.0f} ريال")

                    df_e = pd.DataFrame([{"البند": it["البند"], "الكمية": f"{it['الكمية']:,.2f}", "الوحدة": it["الوحدة"], "سعر الوحدة": f"{it['السعر']:,}", "الإجمالي (SAR)": f"{it['الإجمالي']:,.0f}"} for it in e["items"]])
                    st.dataframe(df_e, use_container_width=True, hide_index=True)
                    st.markdown("<hr style='border-top:1px dashed #9aa4b8;'>", unsafe_allow_html=True)

            st.markdown("#### 📋 قائمة فروع الشبكة المحللة")
            rows = [{"رمز الفرع": e.get("code", ""), "اسم الفرع الهيدروليكي": e["line_name"], "طول الفرع (م)": f"{e['distance']:.2f}", "منهل البداية": f"منهل #{e['node_start']}", "منهل النهاية": f"منهل #{e['node_end']}"} for e in ana.edges_list]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# التبويب 3: التقرير والطباعة
with tabs[3]:
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
            m_rep = make_base_map(center_of(all_c), 14)
            Fullscreen().add_to(m_rep)

            diameter_legend_added = set()
            for edge_r in result["per_edge"]:
                d = edge_r["diameter"]
                color = PIPE_COLORS.get(d, "#1a5fa8")
                folium.PolyLine(
                    [edge_r["start_coord"], edge_r["end_coord"]], color=color, weight=6, opacity=0.9,
                    popup=f"<b>{edge_r.get('code','')} — {edge_r['line_name']}</b><br>القطر: {d}مم<br>العمق: {edge_r['depth']}م<br>التكلفة: {edge_r['total']:,.0f} SAR"
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
            st.markdown("""
            <div class="info-banner">
            ℹ️ تقرير الـ PDF النهائي يُصاغ باللغة الإنجليزية فقط لتفادي مشكلة عرض الخط العربي داخل الملف.
            يُفضّل كتابة اسم المشروع والجهة المالكة واسم المهندس أدناه بأحرف إنجليزية ليظهروا بشكل صحيح في التقرير.
            </div>
            """, unsafe_allow_html=True)
            proj_name = st.text_input("اسم المشروع الرسمي بالتقرير (يُفضّل بالإنجليزية)", value="Integrated Flood Drainage Network Project")
            proj_owner = st.text_input("الجهة المالكة للمشروع (يُفضّل بالإنجليزية)", value="Municipality")
            engineer = st.text_input("اسم المهندس المسؤول (يُفضّل بالإنجليزية)", value="")
            
            st.markdown("#### 🌍 خريطة الخلفية داخل التقرير")
            st.markdown("""
            <div class="info-banner">
            🗺️ سيتم توليد صورة الخريطة تلقائياً بخلفية حقيقية حسب النمط الذي تختاره أدناه
            (شوارع OpenStreetMap، صورة جوية من الأقمار الصناعية، أو نمط آخر) وتضمينها داخل التقرير،
            مع تلوين كل فرع حسب قطره ورسم جميع المناهل عليها. لا حاجة لأي لقطة شاشة يدوية.
            </div>
            """, unsafe_allow_html=True)
            auto_map = st.checkbox("توليد خريطة الخلفية تلقائياً داخل التقرير", value=True)
            pdf_style_keys = list(MAP_STYLES.keys())
            pdf_map_style = DEFAULT_MAP_STYLE
            uploaded_map_img = None
            if auto_map:
                pdf_map_style = st.selectbox(
                    "نمط خلفية الخريطة في التقرير",
                    pdf_style_keys,
                    index=pdf_style_keys.index(st.session_state.map_style) if st.session_state.map_style in pdf_style_keys else 0,
                    key="pdf_map_style_selector",
                    help="اختر بين خريطة الشوارع (OpenStreetMap)، صورة جوية من الأقمار الصناعية، أو نمط آخر.",
                )
            else:
                uploaded_map_img = st.file_uploader("أو ارفع لقطة شاشة خريطة بديلة (اختياري)", type=["png", "jpg", "jpeg"])

            if st.button("📥 إنشاء وتحميل التقرير الهندسي PDF النهائي", use_container_width=True):
                with st.spinner("جاري صياغة ملف PDF..."):
                    try:
                        from reportlab.lib.pagesizes import landscape, A4
                        from reportlab.lib import colors
                        from reportlab.lib.units import mm
                        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, PageBreak, Image
                        from reportlab.lib.styles import ParagraphStyle
                        from reportlab.lib.enums import TA_CENTER, TA_LEFT

                        # ملاحظة: التقرير النهائي (PDF) يُصاغ بالكامل باللغة الإنجليزية بخطوط
                        # Helvetica القياسية المدعومة أصلاً في ReportLab، لتفادي مشكلة عرض الخط العربي.
                        FONT_REG  = "Helvetica"
                        FONT_BOLD = "Helvetica-Bold"

                        report_ref = f"FNA-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

                        buf = io.BytesIO()
                        doc = SimpleDocTemplate(buf, pagesize=landscape(A4), rightMargin=15*mm, leftMargin=15*mm, topMargin=15*mm, bottomMargin=20*mm)

                        BLUE, LBLUE, GREY, WHITE = colors.HexColor("#0a2a5e"), colors.HexColor("#1a5fa8"), colors.HexColor("#f0f4f8"), colors.white
                        GOLD = colors.HexColor("#c9962c")

                        # ── Canvas مخصّص لإضافة تذييل احترافي (ترقيم الصفحات + خط علوي) ──
                        from reportlab.pdfgen import canvas as _pdfcanvas

                        class NumberedCanvas(_pdfcanvas.Canvas):
                            def __init__(self, *args, **kwargs):
                                _pdfcanvas.Canvas.__init__(self, *args, **kwargs)
                                self._saved_page_states = []

                            def showPage(self):
                                self._saved_page_states.append(dict(self.__dict__))
                                self._startPage()

                            def save(self):
                                total_pages = len(self._saved_page_states)
                                for state in self._saved_page_states:
                                    self.__dict__.update(state)
                                    self._draw_footer(total_pages)
                                    _pdfcanvas.Canvas.showPage(self)
                                _pdfcanvas.Canvas.save(self)

                            def _draw_footer(self, total_pages):
                                w, h = landscape(A4)
                                self.saveState()
                                self.setStrokeColor(BLUE)
                                self.setLineWidth(1.1)
                                self.line(15*mm, 14*mm, w-15*mm, 14*mm)
                                self.setFont(FONT_BOLD, 8)
                                self.setFillColor(BLUE)
                                self.drawString(15*mm, 9*mm, "Flood Network Analyzer")
                                self.setFont(FONT_REG, 8)
                                self.setFillColor(colors.HexColor("#6b7a99"))
                                self.drawCentredString(w/2, 9*mm, f"Report Ref: {report_ref}")
                                self.drawRightString(w-15*mm, 9*mm, f"Page {self._pageNumber} of {total_pages}")
                                self.restoreState()

                        s_title = ParagraphStyle("title", fontName=FONT_BOLD, fontSize=20, textColor=WHITE, alignment=TA_CENTER, leading=26)
                        s_h2    = ParagraphStyle("h2", fontName=FONT_BOLD, fontSize=14, textColor=BLUE, alignment=TA_LEFT, spaceBefore=10, spaceAfter=6, leading=20)
                        s_norm  = ParagraphStyle("n", fontName=FONT_REG, fontSize=10, alignment=TA_LEFT, leading=15)
                        s_cell  = ParagraphStyle("cell", fontName=FONT_REG, fontSize=9.5, alignment=TA_LEFT, leading=14)
                        s_cell_b= ParagraphStyle("cellb", fontName=FONT_BOLD, fontSize=9.5, textColor=WHITE, alignment=TA_CENTER, leading=14)
                        s_cell_c= ParagraphStyle("cellc", fontName=FONT_REG, fontSize=9.5, alignment=TA_CENTER, leading=14)
                        s_footer= ParagraphStyle("f", fontName=FONT_REG, fontSize=8, textColor=colors.grey, alignment=TA_CENTER)

                        def P(text, style=s_cell):
                            return Paragraph(str(text), style)

                        elems = []

                        # ── Report Cover ───────────────────────────────────
                        elems.append(Table(
                            [[Paragraph(f"{proj_name}<br/><font size=11>Engineering Report - Flood Drainage Network</font>", s_title)]],
                            colWidths=[265*mm],
                            style=[
                                ('BACKGROUND', (0,0), (-1,-1), BLUE),
                                ('PADDING', (0,0), (-1,-1), 15),
                                ('ROUNDEDCORNERS', (0,0), (-1,-1), [6,6,6,6]),
                            ]
                        ))
                        elems.append(Spacer(1, 6*mm))

                        # ── Project Information ────────────────────────────
                        info_data = [
                            [P("Owner:"), P(proj_owner), P("Issue Date:"), P(result["generated_at"])],
                            [P("Responsible Engineer:"), P(engineer or "-"), P("Report Reference:"), P(report_ref)],
                        ]
                        info_tbl = Table(
                            info_data, colWidths=[45*mm, 90*mm, 40*mm, 90*mm],
                            style=[
                                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")),
                                ('BACKGROUND', (0,0), (0,-1), GREY),
                                ('BACKGROUND', (2,0), (2,-1), GREY),
                                ('PADDING', (0,0), (-1,-1), 6),
                                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                            ]
                        )
                        elems.append(info_tbl)
                        elems.append(Spacer(1, 6*mm))

                        # ── Executive Summary (KPI cards) ──────────────────
                        elems.append(P("Executive Summary", s_h2))
                        elems.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=4))
                        s_kpi_val = ParagraphStyle("kpiv", fontName=FONT_BOLD, fontSize=15, textColor=BLUE, alignment=TA_CENTER, leading=18)
                        s_kpi_lbl = ParagraphStyle("kpil", fontName=FONT_REG, fontSize=8.5, textColor=colors.HexColor("#6b7a99"), alignment=TA_CENTER, leading=11)
                        t_mh_sum = sum(e["n_manholes"] for e in result["per_edge"])
                        t_tr_sum = sum(e["n_traps"] for e in result["per_edge"])
                        kpi_defs = [
                            (f"{len(result['per_edge'])}", "Total Branches"),
                            (f"{result['stat']['length']/1000:.2f} km", "Total Network Length"),
                            (f"{t_mh_sum}", "Inspection Manholes"),
                            (f"{t_tr_sum}", "Rainwater Catch Basins"),
                            (f"{result['total_cost']:,.0f} SAR", "Estimated Total Cost"),
                        ]
                        kpi_row = [[Paragraph(v, s_kpi_val) for v, _ in kpi_defs]]
                        kpi_lbl_row = [[Paragraph(l, s_kpi_lbl) for _, l in kpi_defs]]
                        kpi_tbl = Table(
                            kpi_row + kpi_lbl_row, colWidths=[53*mm]*5,
                            style=[
                                ('BACKGROUND', (0,0), (-1,-1), GREY),
                                ('BOX', (0,0), (-1,-1), 0.6, colors.HexColor("#d0d8e8")),
                                ('LINEAFTER', (0,0), (-2,-1), 0.6, colors.HexColor("#d0d8e8")),
                                ('TOPPADDING', (0,0), (-1,0), 10),
                                ('BOTTOMPADDING', (0,0), (-1,0), 2),
                                ('TOPPADDING', (0,1), (-1,1), 0),
                                ('BOTTOMPADDING', (0,1), (-1,1), 10),
                                ('LINEABOVE', (0,0), (-1,0), 3, GOLD),
                            ]
                        )
                        elems.append(kpi_tbl)
                        elems.append(Spacer(1, 8*mm))

                        # ── Network Map (background per user-selected style) ─
                        if uploaded_map_img:
                            elems.append(P("Network Route Map", s_h2))
                            elems.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=4))
                            elems.append(Image(uploaded_map_img, width=260*mm, height=120*mm))
                            elems.append(PageBreak())
                        elif auto_map:
                            map_png_bytes = render_static_map(
                                result["per_edge"], ana.nodes_coords, PIPE_COLORS,
                                style_key=pdf_map_style, width=1600, height=850,
                            )
                            if map_png_bytes:
                                map_title_en = MAP_STYLES.get(pdf_map_style, MAP_STYLES[DEFAULT_MAP_STYLE])["label_en"]
                                elems.append(P(f"Network Route Map ({map_title_en} Background)", s_h2))
                                elems.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=4))
                                elems.append(Image(io.BytesIO(map_png_bytes), width=260*mm, height=138*mm))

                                legend_used = sorted({e["diameter"] for e in result["per_edge"]})
                                legend_text = "   ".join(
                                    f'<font color="{PIPE_COLORS.get(d,"#1a5fa8")}">■</font> D{d} mm'
                                    for d in legend_used
                                ) + '   <font color="#e63946">●</font> Inspection Manhole'
                                elems.append(Spacer(1, 2*mm))
                                elems.append(Table([[Paragraph(legend_text, s_norm)]], colWidths=[260*mm]))
                                elems.append(PageBreak())
                            else:
                                elems.append(P(
                                    "Note: Could not automatically generate the map background "
                                    "(no connection to map tile servers in this environment). "
                                    "You may disable auto-map generation and upload a map screenshot instead.",
                                    s_norm
                                ))
                                elems.append(Spacer(1, 6*mm))

                        # ── Total Bill of Quantities (BOQ) ─────────────────
                        elems.append(P("1. Project Total Bill of Quantities & Costs", s_h2))
                        boq_header = [P("Item", s_cell_b), P("Quantity", s_cell_b), P("Unit", s_cell_b), P("Total (SAR)", s_cell_b)]
                        boq_data = [boq_header]
                        for name, d in result["all_items"].items():
                            boq_data.append([
                                P(en_item(name)),
                                P(f"{d['الكمية']:,.2f}", s_cell_c),
                                P(en_unit(d.get("الوحدة", "")), s_cell_c),
                                P(f"{d['الإجمالي']:,.0f}", s_cell_c),
                            ])
                        boq_data.append([
                            P("Project Grand Total", ParagraphStyle("totlbl", fontName=FONT_BOLD, fontSize=11, textColor=WHITE, alignment=TA_LEFT)),
                            Paragraph("", s_cell_c), Paragraph("", s_cell_c),
                            P(f"{result['total_cost']:,.0f}", ParagraphStyle("totval", fontName=FONT_BOLD, fontSize=11, textColor=WHITE, alignment=TA_CENTER)),
                        ])

                        boq_tbl = Table(boq_data, colWidths=[110*mm, 50*mm, 35*mm, 70*mm], repeatRows=1)
                        boq_tbl.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), LBLUE),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")),
                            ('ROWBACKGROUNDS', (0,1), (-1,-2), [WHITE, GREY]),
                            ('PADDING', (0,0), (-1,-1), 6),
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                            ('BACKGROUND', (0,-1), (-1,-1), BLUE),
                            ('SPAN', (1,-1), (2,-1)),
                        ]))
                        elems.append(boq_tbl)
                        elems.append(PageBreak())

                        # ── Per-Branch Technical Specifications ────────────
                        elems.append(P("2. Technical Specifications per Branch", s_h2))
                        branch_header = [
                            P("Code", s_cell_b), P("Branch Name", s_cell_b), P("Length (m)", s_cell_b),
                            P("Diameter (mm)", s_cell_b), P("Depth (m)", s_cell_b),
                            P("Manholes", s_cell_b), P("Catch Basins", s_cell_b),
                            P("Cost (SAR)", s_cell_b),
                        ]
                        branch_data = [branch_header]
                        for e in result["per_edge"]:
                            branch_data.append([
                                P(e.get("code", "")),
                                P(e["line_name"]),
                                P(f"{e['length']:.1f}", s_cell_c),
                                P(str(e["diameter"]), s_cell_c),
                                P(str(e["depth"]), s_cell_c),
                                P(str(e["n_manholes"]), s_cell_c),
                                P(str(e["n_traps"]), s_cell_c),
                                P(f"{e['total']:,.0f}", s_cell_c),
                            ])

                        br_tbl = Table(
                            branch_data,
                            colWidths=[22*mm, 45*mm, 25*mm, 28*mm, 25*mm, 22*mm, 25*mm, 43*mm],
                            repeatRows=1,
                        )
                        br_tbl.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), LBLUE),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")),
                            ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, GREY]),
                            ('PADDING', (0,0), (-1,-1), 5),
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ]))
                        elems.append(br_tbl)

                        doc.build(elems, canvasmaker=NumberedCanvas)
                        buf.seek(0)

                        st.download_button(
                            label="📥 اضغط هنا لبدء تحميل ملف التقرير الهندسي PDF المعتمد (باللغة الإنجليزية)", data=buf.getvalue(),
                            file_name=f"Flood_Network_Report_{report_ref}.pdf",
                            mime="application/pdf", use_container_width=True
                        )
                        st.success("✅ تم إنشاء التقرير بنجاح باللغة الإنجليزية — بتنسيق احترافي مع ترقيم صفحات وخريطة خلفية — اضغط الزر أعلاه للتحميل.")
                    except Exception as ex:
                        st.error(f"❌ خطأ أثناء صياغة مستند الـ PDF: {ex}")
                        import traceback
                        st.text(traceback.format_exc())

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""<div style="text-align:center;color:#9aa4b8;font-size:0.85rem;padding:16px 0">🌊 محلل شبكات ومصارف السيول — لوحة التحكم الذكية المحدثة والتركيز التلقائي</div>""", unsafe_allow_html=True)

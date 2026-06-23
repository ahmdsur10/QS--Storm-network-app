import streamlit as st
import math
import json
import uuid
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd

try:
    import folium
    from streamlit_folium import st_folium
    from folium.plugins import Draw
    FOLIUM_AVAILABLE = True
except:
    FOLIUM_AVAILABLE = False

# ═════════════════════════════════════════════════════════════════════════════════
# إعدادات الصفحة
# ═════════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="محلل شبكات السيول",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: 'Cairo', sans-serif !important;
}

html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
}

.stApp {
    background: #f8f9fa;
}

/* Header */
.header-main {
    background: linear-gradient(135deg, #0a2a5e 0%, #1a5fa8 100%);
    color: white;
    padding: 35px;
    border-radius: 15px;
    margin-bottom: 30px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    text-align: center;
}

.header-main h1 {
    font-size: 2.5rem;
    font-weight: 900;
    margin-bottom: 10px;
}

.header-main p {
    font-size: 1.1rem;
    opacity: 0.95;
}

/* Sidebar - ارشادي فقط */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a2a5e 0%, #1a5fa8 100%) !important;
    padding-top: 20px !important;
}

.sidebar-title {
    color: white;
    font-size: 1.2rem;
    font-weight: 900;
    margin-top: 25px;
    margin-bottom: 15px;
    border-bottom: 3px solid rgba(255,255,255,0.3);
    padding-bottom: 10px;
}

.sidebar-box {
    background: rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 15px;
    margin: 15px 0;
    border-left: 5px solid white;
    color: white;
    font-size: 0.95rem;
    line-height: 1.8;
}

.sidebar-box strong {
    font-weight: 700;
    font-size: 1rem;
    display: block;
    margin-bottom: 8px;
}

.metric-value-sidebar {
    font-size: 1.8rem;
    font-weight: 900;
    color: #4dd0e1;
    margin: 5px 0;
}

.metric-label-sidebar {
    color: rgba(255,255,255,0.8);
    font-size: 0.85rem;
    font-weight: 600;
}

/* الأقسام الرئيسية في الصفحة */
.section-container {
    background: white;
    border-radius: 15px;
    padding: 30px;
    margin-bottom: 25px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.section-title {
    color: #0a2a5e;
    font-size: 2rem;
    font-weight: 900;
    margin-bottom: 20px;
    border-bottom: 4px solid #1a5fa8;
    padding-bottom: 15px;
}

.section-subtitle {
    color: #0a2a5e;
    font-size: 1.3rem;
    font-weight: 700;
    margin: 20px 0 15px 0;
}

/* البطاقات الكبيرة */
.big-metric-card {
    background: white;
    border-radius: 12px;
    padding: 25px;
    margin: 15px 0;
    border: 3px solid #1a5fa8;
    text-align: center;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(26, 95, 168, 0.1);
}

.big-metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 16px rgba(26, 95, 168, 0.15);
    border-color: #0a2a5e;
}

.big-metric-value {
    font-size: 3rem;
    font-weight: 900;
    color: #0a2a5e;
    margin: 10px 0;
}

.big-metric-label {
    font-size: 1.1rem;
    color: #6b7a99;
    font-weight: 700;
}

/* الأزرار */
.stButton > button {
    background: linear-gradient(135deg, #1a5fa8 0%, #0a2a5e 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 15px 25px !important;
    min-height: 55px !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(26, 95, 168, 0.3) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(26, 95, 168, 0.4) !important;
}

/* التبويبات */
[data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 3px solid #1a5fa8 !important;
    gap: 10px !important;
}

[data-baseweb="tab"] {
    background-color: white !important;
    border-radius: 8px 8px 0 0 !important;
    border: 2px solid #e0e0e0 !important;
    border-bottom: none !important;
    color: #6b7a99 !important;
    font-weight: 700 !important;
    padding: 15px 20px !important;
}

[aria-selected="true"] {
    background-color: white !important;
    border-color: #1a5fa8 !important;
    color: #0a2a5e !important;
    border-bottom: 3px solid white !important;
}

/* جداول */
.stDataFrame {
    border-radius: 10px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
}

/* النصوص */
.info-text {
    color: #0a2a5e;
    font-size: 1.05rem;
    line-height: 1.8;
    margin: 15px 0;
}

.success-box {
    background: white;
    border-left: 5px solid #28a745;
    padding: 15px;
    border-radius: 8px;
    margin: 15px 0;
    color: #155724;
    font-weight: 500;
}

.warning-box {
    background: white;
    border-left: 5px solid #ffc107;
    padding: 15px;
    border-radius: 8px;
    margin: 15px 0;
    color: #856404;
    font-weight: 500;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════════
# الثوابت
# ═════════════════════════════════════════════════════════════════════════════════

PIPE_PRICES = {
    400: 454, 500: 619, 600: 725, 700: 906, 800: 1045,
    900: 1225, 1000: 1440, 1100: 1600, 1200: 1812, 1300: 1920, 1400: 2132,
}

# ═════════════════════════════════════════════════════════════════════════════════
# دوال مساعدة
# ═════════════════════════════════════════════════════════════════════════════════

def haversine_distance(coord1, coord2):
    """حساب المسافة بين نقطتين"""
    lat1, lon1 = coord1[0], coord1[1]
    lat2, lon2 = coord2[0], coord2[1]
    R = 6_371_000
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def calculate_auto_traps(length):
    """حساب المصائد: الطول ÷ 35"""
    return max(1, round(length / 35))

class AdvancedNetworkAnalyzer:
    """محلل الشبكة"""
    
    def __init__(self, lines):
        self.lines = [ln for ln in lines if ln.get("selected", True)]
        self.G = nx.Graph()
        self.node_to_line = {}
        self._build_network()
    
    def _build_network(self):
        """بناء الشبكة"""
        node_id = 0
        
        for line_idx, line in enumerate(self.lines):
            coords = line.get("coords", [])
            if len(coords) < 2:
                continue
            
            for i in range(len(coords) - 1):
                start = tuple(coords[i][:2])
                end = tuple(coords[i + 1][:2])
                
                if start not in self.node_to_line:
                    self.G.add_node(node_id, coord=start)
                    self.node_to_line[start] = node_id
                    node_id += 1
                
                if end not in self.node_to_line:
                    self.G.add_node(node_id, coord=end)
                    self.node_to_line[end] = node_id
                    node_id += 1
                
                distance = haversine_distance(coords[i], coords[i+1])
                start_node = self.node_to_line[start]
                end_node = self.node_to_line[end]
                
                self.G.add_edge(start_node, end_node, distance=distance, diameter=line.get("diameter", 600))
    
    def get_stats(self):
        """إحصائيات الشبكة"""
        if self.G.number_of_nodes() == 0:
            return None
        
        return {
            "num_nodes": self.G.number_of_nodes(),
            "num_edges": self.G.number_of_edges(),
            "total_length": sum(data['distance'] for _, _, data in self.G.edges(data=True)),
            "is_connected": nx.is_connected(self.G),
        }
    
    def get_centrality(self):
        """حساب المركزية"""
        try:
            betweenness = nx.betweenness_centrality(self.G, weight='distance')
            return {"betweenness": betweenness}
        except:
            return None
    
    def get_critical_nodes(self):
        """المناهل الحرجة"""
        centrality = self.get_centrality()
        if not centrality:
            return []
        return sorted(centrality["betweenness"].items(), key=lambda x: x[1], reverse=True)[:10]

def calculate_line_cost(line, num_nodes):
    """حساب التكلفة"""
    diameter = line.get("diameter", 600)
    depth = line.get("depth", 1.5)
    length = line.get("length", 0)
    
    price_per_meter = PIPE_PRICES.get(diameter, 725)
    num_traps = calculate_auto_traps(length)
    
    items = [
        {"البند": "أنابيب صرف", "الكمية": length, "الوحدة": "م", "السعر": price_per_meter, "الإجمالي": length * price_per_meter},
        {"البند": "حفر الخندق", "الكمية": length, "الوحدة": "م", "السعر": 50, "الإجمالي": length * 50},
        {"البند": "مناهل", "الكمية": num_nodes, "الوحدة": "عدد", "السعر": 3000, "الإجمالي": num_nodes * 3000},
        {"البند": "مصائد", "الكمية": num_traps, "الوحدة": "عدد", "السعر": 2000, "الإجمالي": num_traps * 2000},
        {"البند": "ردم وتسوية", "الكمية": length * depth, "الوحدة": "م³", "السعر": 30, "الإجمالي": length * depth * 30},
    ]
    
    return {
        "items": items,
        "total": sum(item["الإجمالي"] for item in items),
        "num_manholes": num_nodes,
        "num_traps": num_traps,
    }

# ═════════════════════════════════════════════════════════════════════════════════
# Session State
# ═════════════════════════════════════════════════════════════════════════════════

if "lines" not in st.session_state:
    st.session_state.lines = []
if "analyzer" not in st.session_state:
    st.session_state.analyzer = None
if "cost_result" not in st.session_state:
    st.session_state.cost_result = None

# ═════════════════════════════════════════════════════════════════════════════════
# Sidebar - ارشادي فقط
# ═════════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h2 style='color: white; font-size: 1.8rem; margin: 0;'>📘 دليل الاستخدام</h2></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("<div class='sidebar-title'>🎯 الخطوات الأساسية</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='sidebar-box'>
    <strong>1️⃣ أضف الخطوط</strong>
    ارسم على الخريطة أو استورد من GeoJSON
    
    <strong>2️⃣ حلل الشبكة</strong>
    استخرج البيانات الفعلية للشبكة
    
    <strong>3️⃣ احسب التكاليف</strong>
    احصل على حسابات دقيقة جداً
    
    <strong>4️⃣ احمل التقرير</strong>
    احفظ النتائج بصيغ مختلفة
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("<div class='sidebar-title'>📊 معلومات المشروع</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; text-align: center;'>
        <div class='metric-value-sidebar'>{len(st.session_state.lines)}</div>
        <div class='metric-label-sidebar'>🗺️ الخطوط</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_length = sum(ln.get("length", 0) for ln in st.session_state.lines)
        st.markdown(f"""
        <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; text-align: center;'>
        <div class='metric-value-sidebar'>{total_length/1000:.1f}</div>
        <div class='metric-label-sidebar'>📏 الطول (كم)</div>
        </div>
        """, unsafe_allow_html=True)
    
    if st.session_state.analyzer:
        stats = st.session_state.analyzer.get_stats()
        if stats:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; text-align: center;'>
                <div class='metric-value-sidebar'>{stats['num_nodes']}</div>
                <div class='metric-label-sidebar'>🔴 المناهل</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; text-align: center;'>
                <div class='metric-value-sidebar'>{stats['num_edges']}</div>
                <div class='metric-label-sidebar'>🔗 الأنابيب</div>
                </div>
                """, unsafe_allow_html=True)
    
    if st.session_state.cost_result:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; text-align: center;'>
            <div class='metric-value-sidebar'>{st.session_state.cost_result.get("total_traps", 0)}</div>
            <div class='metric-label-sidebar'>💧 المصائد</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            cost = st.session_state.cost_result.get("total_cost", 0) / 1e6
            st.markdown(f"""
            <div style='background: rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; text-align: center;'>
            <div class='metric-value-sidebar'>{cost:.2f}M</div>
            <div class='metric-label-sidebar'>💵 التكلفة</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("<div class='sidebar-title'>💡 نصائح مهمة</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='sidebar-box'>
    ✅ التحليل أولاً يضمن نتائج دقيقة جداً
    
    ✅ المصائد = الطول ÷ 35
    
    ✅ احمل التقارير بصيغة CSV أو JSON
    
    ✅ الأقسام في أعلى الصفحة
    </div>
    """, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════════
# Header الرئيسي
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="header-main">
    <h1>🌊 محلل شبكات السيول</h1>
    <p>تطبيق احترافي لتحليل وحساب تكاليف شبكات الصرف السيلية بدقة عالية</p>
</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════════
# الأقسام الرئيسية - في الصفحة
# ═════════════════════════════════════════════════════════════════════════════════

tabs = st.tabs(["🏠 الرئيسية", "🗺️ إدارة الخطوط", "🌐 تحليل الشبكة", "💰 حساب التكاليف", "📊 التقارير"])

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 1: الرئيسية
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[0]:
    st.markdown("""
    <div class="section-container">
    <h2 class="section-title">🏠 مرحباً بك في محلل شبكات السيول</h2>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="big-metric-card">
        <div style="font-size: 2.5rem; margin-bottom: 10px;">🗺️</div>
        <h3 style="color: #0a2a5e; margin: 10px 0;">إدارة الخطوط</h3>
        <p style="color: #6b7a99; margin: 0; font-size: 0.95rem;">أضف الخطوط على الخريطة أو استورد من ملفات GeoJSON</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="big-metric-card">
        <div style="font-size: 2.5rem; margin-bottom: 10px;">🌐</div>
        <h3 style="color: #0a2a5e; margin: 10px 0;">تحليل الشبكة</h3>
        <p style="color: #6b7a99; margin: 0; font-size: 0.95rem;">فهم عميق لبنية الشبكة وتحديد المناهل الحرجة</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="big-metric-card">
        <div style="font-size: 2.5rem; margin-bottom: 10px;">💰</div>
        <h3 style="color: #0a2a5e; margin: 10px 0;">حساب التكاليف</h3>
        <p style="color: #6b7a99; margin: 0; font-size: 0.95rem;">احسب التكاليف باستخدام البيانات الفعلية من التحليل</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <p class="info-text" style="margin-top: 30px;">
    هذا التطبيق يوفر حلاً متكاملاً لتحليل وحساب تكاليف شبكات الصرف السيلية بدقة عالية جداً.
    يستخدم بيانات تحليل الشبكة الفعلية في الحسابات مما يضمن نتائج موثوقة وصحيحة.
    </p>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <h3 class="section-subtitle">📖 كيفية الاستخدام</h3>
        <div class="info-text">
        <strong>الخطوة 1:</strong> انتقل إلى تبويب "إدارة الخطوط" وأضف خطوطك على الخريطة أو استورد من GeoJSON
        
        <strong>الخطوة 2:</strong> انتقل إلى تبويب "تحليل الشبكة" واستخرج البيانات الفعلية
        
        <strong>الخطوة 3:</strong> انتقل إلى تبويب "حساب التكاليف" واحصل على حسابات دقيقة
        
        <strong>الخطوة 4:</strong> انتقل إلى تبويب "التقارير" واحمل النتائج
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <h3 class="section-subtitle">✨ المميزات الرئيسية</h3>
        <div class="info-text">
        ✅ رسم تفاعلي على الخريطة
        
        ✅ استيراف ملفات GeoJSON
        
        ✅ تحليل شامل للشبكة الفعلية
        
        ✅ حسابات دقيقة جداً (المصائد = الطول ÷ 35)
        
        ✅ تقارير قابلة للتصدير (CSV, TXT, JSON)
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.success("✅ استخدم التبويبات أعلاه للبدء!")

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 2: إدارة الخطوط
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[1]:
    st.markdown("""
    <div class="section-container">
    <h2 class="section-title">🗺️ إدارة الخطوط</h2>
    </div>
    """, unsafe_allow_html=True)
    
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🎨 رسم", "📤 استيراف", "📋 الخطوط"])
    
    with sub_tab1:
        st.markdown("""
        <div class="section-container">
        <h3 class="section-subtitle">رسم الخطوط على الخريطة</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if FOLIUM_AVAILABLE:
            m = folium.Map(location=[24.7136, 46.6753], zoom_start=12)
            
            for idx, line in enumerate(st.session_state.lines):
                coords = line.get("coords", [])
                if coords:
                    folium.PolyLine(coords, color="red", weight=3).add_to(m)
            
            draw = Draw(
                export=True,
                position="topleft",
                draw_options={"polyline": True, "polygon": False, "rectangle": False}
            )
            draw.add_to(m)
            
            map_data = st_folium(m, width=None, height=500)
            
            if map_data and map_data.get("last_active_drawing"):
                drawing = map_data["last_active_drawing"]
                if drawing.get("geometry", {}).get("type") == "LineString":
                    coords = [(c[1], c[0]) for c in drawing["geometry"]["coordinates"]]
                    if len(coords) >= 2:
                        length = sum(haversine_distance(coords[i], coords[i+1]) for i in range(len(coords)-1))
                        
                        new_line = {
                            "id": str(uuid.uuid4()),
                            "name": f"خط {len(st.session_state.lines) + 1}",
                            "length": length,
                            "coords": coords,
                            "source": "رسم يدوي",
                            "selected": True,
                            "diameter": 600,
                            "depth": 1.5,
                        }
                        st.session_state.lines.append(new_line)
                        st.session_state.analyzer = None
                        st.session_state.cost_result = None
                        st.success(f"✅ تم إضافة {new_line['name']}")
                        st.rerun()
    
    with sub_tab2:
        st.markdown("""
        <div class="section-container">
        <h3 class="section-subtitle">استيراف ملفات GeoJSON</h3>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("اختر ملف GeoJSON", type=["geojson"])
        
        if uploaded_file:
            try:
                geojson_data = json.load(uploaded_file)
                features = geojson_data.get("features", [])
                
                if features:
                    for idx, feature in enumerate(features):
                        geom = feature.get("geometry", {})
                        if geom.get("type") == "LineString":
                            coords = [(lat, lon) for lon, lat in geom.get("coordinates", [])]
                            if len(coords) >= 2:
                                length = sum(haversine_distance(coords[i], coords[i+1]) for i in range(len(coords)-1))
                                
                                new_line = {
                                    "id": str(uuid.uuid4()),
                                    "name": feature.get("properties", {}).get("name", f"خط {idx+1}"),
                                    "length": length,
                                    "coords": coords,
                                    "source": "GeoJSON",
                                    "selected": True,
                                    "diameter": 600,
                                    "depth": 1.5,
                                }
                                st.session_state.lines.append(new_line)
                    
                    st.session_state.analyzer = None
                    st.session_state.cost_result = None
                    st.success(f"✅ تم استيراف {len(features)} خط")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
    
    with sub_tab3:
        st.markdown("""
        <div class="section-container">
        <h3 class="section-subtitle">الخطوط المضافة</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.lines:
            st.info("لا توجد خطوط مضافة حتى الآن")
        else:
            for line in st.session_state.lines:
                with st.expander(f"✏️ {line['name']} ({line['length']:,.0f} م)"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        line["selected"] = st.checkbox("✅ تفعيل", value=line["selected"], key=f"sel_{line['id']}")
                    with col2:
                        line["diameter"] = st.selectbox("القطر (ملم)", sorted(PIPE_PRICES.keys()),
                                                       index=list(PIPE_PRICES.keys()).index(line.get("diameter", 600)),
                                                       key=f"diam_{line['id']}")
                    with col3:
                        line["depth"] = st.number_input("العمق (م)", min_value=0.5, value=line.get("depth", 1.5),
                                                       step=0.1, key=f"depth_{line['id']}")
                    with col4:
                        if st.button("🗑️ حذف", key=f"del_{line['id']}"):
                            st.session_state.lines = [l for l in st.session_state.lines if l['id'] != line['id']]
                            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 3: تحليل الشبكة
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[2]:
    st.markdown("""
    <div class="section-container">
    <h2 class="section-title">🌐 تحليل الشبكة الفعلية</h2>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً أولاً من تبويب 'إدارة الخطوط'")
    else:
        col1, col2 = st.columns([4, 1])
        
        with col2:
            if st.button("🔍 حلل الشبكة", use_container_width=True):
                with st.spinner("جاري تحليل الشبكة..."):
                    st.session_state.analyzer = AdvancedNetworkAnalyzer(st.session_state.lines)
                    st.success("✅ تم التحليل!")
        
        if st.session_state.analyzer:
            analyzer = st.session_state.analyzer
            stats = analyzer.get_stats()
            
            if stats:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="big-metric-card">
                    <div class="big-metric-value">{stats['num_nodes']}</div>
                    <div class="big-metric-label">المناهل (الفعلي)</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="big-metric-card">
                    <div class="big-metric-value">{stats['num_edges']}</div>
                    <div class="big-metric-label">الأنابيب</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="big-metric-card">
                    <div class="big-metric-value">{stats['total_length']/1000:.1f}</div>
                    <div class="big-metric-label">الطول (كم)</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="big-metric-card">
                    <div class="big-metric-value">{'✅' if stats['is_connected'] else '❌'}</div>
                    <div class="big-metric-label">الاتصالية</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                with st.expander("🔴 المناهل الحرجة", expanded=True):
                    critical = analyzer.get_critical_nodes()
                    
                    if critical:
                        critical_df = pd.DataFrame([
                            {"#": i+1, "المنهل": node, "الأهمية": f"{score:.4f}"}
                            for i, (node, score) in enumerate(critical)
                        ])
                        st.dataframe(critical_df, use_container_width=True, hide_index=True)
                
                st.success(f"✅ عدد المناهل الفعلي من التحليل: **{stats['num_nodes']}**")

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 4: حساب التكاليف
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[3]:
    st.markdown("""
    <div class="section-container">
    <h2 class="section-title">💰 حساب التكاليف والكميات</h2>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً أولاً")
    elif not st.session_state.analyzer:
        st.warning("⚠️ قم بتحليل الشبكة أولاً من تبويب 'تحليل الشبكة'")
    else:
        col1, col2 = st.columns([4, 1])
        
        with col2:
            if st.button("🧮 احسب التكاليف", use_container_width=True):
                with st.spinner("جاري الحساب..."):
                    analyzer = st.session_state.analyzer
                    stats = analyzer.get_stats()
                    selected_lines = [ln for ln in st.session_state.lines if ln.get("selected", True)]
                    
                    if selected_lines and stats:
                        num_actual_nodes = stats['num_nodes']
                        all_items = {}
                        per_line_result = []
                        total_length = sum(ln.get("length", 0) for ln in selected_lines)
                        
                        for line in selected_lines:
                            line_share = (line.get("length", 0) / total_length) if total_length > 0 else 0
                            num_nodes_for_line = max(1, round(num_actual_nodes * line_share))
                            
                            cost_data = calculate_line_cost(line, num_nodes_for_line)
                            per_line_result.append({"line": line, "cost_data": cost_data})
                            
                            for item in cost_data["items"]:
                                key = item["البند"]
                                if key not in all_items:
                                    all_items[key] = {"الكمية": 0, "الإجمالي": 0, "الوحدة": item["الوحدة"]}
                                all_items[key]["الكمية"] += item["الكمية"]
                                all_items[key]["الإجمالي"] += item["الإجمالي"]
                        
                        total_cost = sum(item["الإجمالي"] for item in all_items.values())
                        total_traps = sum(item["cost_data"]["num_traps"] for item in per_line_result)
                        
                        st.session_state.cost_result = {
                            "per_line": per_line_result,
                            "all_items": all_items,
                            "total_cost": total_cost,
                            "total_manholes": num_actual_nodes,
                            "total_traps": total_traps,
                        }
                        
                        st.success("✅ تم الحساب!")
        
        if st.session_state.cost_result:
            result = st.session_state.cost_result
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"""
                <div class="big-metric-card">
                <div class="big-metric-value">{result['total_manholes']}</div>
                <div class="big-metric-label">المناهل</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="big-metric-card">
                <div class="big-metric-value">{result['total_traps']}</div>
                <div class="big-metric-label">المصائد</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="big-metric-card">
                <div class="big-metric-value">{result['total_cost']/1e6:.2f}M</div>
                <div class="big-metric-label">التكلفة</div>
                </div>
                """, unsafe_allow_html=True)
            with col4:
                st.markdown(f"""
                <div class="big-metric-card">
                <div class="big-metric-value">{len(result['per_line'])}</div>
                <div class="big-metric-label">الخطوط</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            sub_tab1, sub_tab2 = st.tabs(["📋 الكميات", "🔍 التفاصيل"])
            
            with sub_tab1:
                items_list = []
                for item_name, item_data in result["all_items"].items():
                    items_list.append({
                        "البند": item_name,
                        "الكمية": f"{item_data['الكمية']:,.2f}",
                        "الوحدة": item_data["الوحدة"],
                        "الإجمالي": f"{item_data['الإجمالي']:,.0f}"
                    })
                st.dataframe(pd.DataFrame(items_list), use_container_width=True, hide_index=True)
                st.markdown(f"### 💵 التكلفة الإجمالية: **{result['total_cost']:,.0f} ريال**")
            
            with sub_tab2:
                for per_line in result["per_line"]:
                    line = per_line["line"]
                    cost_data = per_line["cost_data"]
                    
                    with st.expander(f"📍 {line['name']} ({line['length']:,.0f} م)"):
                        st.dataframe(pd.DataFrame(cost_data["items"]), use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 5: التقارير
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[4]:
    st.markdown("""
    <div class="section-container">
    <h2 class="section-title">📊 التقارير والتصدير</h2>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.cost_result:
        st.warning("⚠️ احسب التكاليف أولاً")
    else:
        result = st.session_state.cost_result
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv_content = "البند,الكمية,الوحدة,الإجمالي\n"
            for name, data in result["all_items"].items():
                csv_content += f"{name},{data['الكمية']:.2f},{data['الوحدة']},{data['الإجمالي']:.0f}\n"
            
            st.download_button(label="📥 تحميل CSV", data=csv_content,
                             file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                             mime="text/csv", use_container_width=True)
        
        with col2:
            txt_content = f"تقرير شبكة السيول\nالتاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            txt_content += f"المناهل: {result['total_manholes']}\nالمصائد: {result['total_traps']}\nالتكلفة: {result['total_cost']:,.0f} ريال\n"
            
            st.download_button(label="📥 تحميل TXT", data=txt_content,
                             file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                             mime="text/plain", use_container_width=True)
        
        with col3:
            json_content = json.dumps({
                "total_manholes": result['total_manholes'],
                "total_traps": result['total_traps'],
                "total_cost": result['total_cost'],
            }, ensure_ascii=False, indent=2)
            
            st.download_button(label="📥 تحميل JSON", data=json_content,
                             file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                             mime="application/json", use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════════
# Footer
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.9rem; padding: 25px;">
    <p style="margin-bottom: 5px;">🌊 محلل شبكات السيول | النسخة 8.0 - واجهة احترافية محسّنة</p>
    <p style="margin: 0;">✅ Sidebar ارشادي | ✅ معلومات سريعة واضحة | ✅ أقسام في الصفحة | ✅ ألوان بيضاء</p>
</div>
""", unsafe_allow_html=True)

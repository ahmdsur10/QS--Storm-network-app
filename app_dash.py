import streamlit as st
import math
import json
import tempfile
import uuid
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# استيراد المكتبات الاختيارية
try:
    import folium
    from streamlit_folium import st_folium
    from folium.plugins import Draw
    FOLIUM_AVAILABLE = True
except:
    FOLIUM_AVAILABLE = False

# ═════════════════════════════════════════════════════════════════════════════════
# إعدادات الصفحة والأنماط
# ═════════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="محلل شبكات السيول",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS محسّن جداً
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
    background: linear-gradient(135deg, #f5f7fa 0%, #e8f0f6 100%);
}

/* Header الرئيسي */
.header-main {
    background: linear-gradient(135deg, #0a2a5e 0%, #1a5fa8 100%);
    color: white;
    padding: 25px;
    border-radius: 15px;
    margin-bottom: 20px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.15);
    text-align: center;
}

.header-main h1 {
    font-size: 2.2rem;
    font-weight: 900;
    margin-bottom: 8px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.header-main p {
    font-size: 1rem;
    opacity: 0.95;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a2a5e 0%, #1a5fa8 100%) !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    color: white !important;
}

/* البطاقات */
.metric-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    border-left: 5px solid #1a5fa8;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    text-align: center;
    transition: all 0.3s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}

.metric-value {
    font-size: 2rem;
    font-weight: 900;
    color: #0a2a5e;
    margin-bottom: 8px;
}

.metric-label {
    font-size: 0.9rem;
    color: #6b7a99;
    font-weight: 600;
}

/* عناوين الأقسام */
.section-title {
    background: linear-gradient(135deg, #1a5fa8 0%, #0a2a5e 100%);
    color: white;
    padding: 15px;
    border-radius: 10px;
    margin: 20px 0 15px 0;
    font-size: 1.2rem;
    font-weight: 900;
    text-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

/* صناديق المعلومات */
.info-box {
    background: #d1ecf1;
    border-left: 4px solid #17a2b8;
    padding: 15px;
    border-radius: 8px;
    margin: 15px 0;
    color: #0c5460;
    font-weight: 500;
}

.success-box {
    background: #d4edda;
    border-left: 4px solid #28a745;
    padding: 15px;
    border-radius: 8px;
    margin: 15px 0;
    color: #155724;
    font-weight: 500;
}

.warning-box {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 15px;
    border-radius: 8px;
    margin: 15px 0;
    color: #856404;
    font-weight: 500;
}

.danger-box {
    background: #f8d7da;
    border-left: 4px solid #dc3545;
    padding: 15px;
    border-radius: 8px;
    margin: 15px 0;
    color: #721c24;
    font-weight: 500;
}

/* الأزرار */
.stButton > button {
    background: linear-gradient(135deg, #1a5fa8 0%, #0a2a5e 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 12px 20px !important;
    min-height: 50px !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(26, 95, 168, 0.3) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(26, 95, 168, 0.4) !important;
}

.stDownloadButton > button {
    background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%) !important;
    color: white !important;
}

/* جداول */
.stDataFrame {
    border-radius: 10px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
}

/* Expandables */
.streamlit-expanderHeader {
    background-color: #f0f5fa !important;
    border-radius: 8px !important;
    border-left: 4px solid #1a5fa8 !important;
}

/* التبويبات */
[data-baseweb="tab-list"] {
    gap: 5px !important;
}

[data-baseweb="tab"] {
    background-color: #f0f5fa !important;
    border-radius: 8px 8px 0 0 !important;
    border-left: 3px solid transparent !important;
}

[aria-selected="true"] {
    border-left-color: #1a5fa8 !important;
    background-color: white !important;
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

BOX_DIMENSIONS = {
    "0.6×0.6": {"width": 0.6, "height": 0.6, "price": 850},
    "0.8×0.6": {"width": 0.8, "height": 0.6, "price": 950},
    "1.0×0.6": {"width": 1.0, "height": 0.6, "price": 1050},
    "1.0×0.8": {"width": 1.0, "height": 0.8, "price": 1200},
    "1.2×0.8": {"width": 1.2, "height": 0.8, "price": 1400},
    "1.5×1.0": {"width": 1.5, "height": 1.0, "price": 1800},
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

def calculate_auto_manholes(length, diameter=600):
    """حساب عدد المناهل تلقائياً"""
    if diameter >= 1000:
        spacing = 150
    elif diameter <= 600:
        spacing = 100
    else:
        spacing = 120
    
    return max(2, int(length / spacing) + 1)

def calculate_auto_traps(length):
    """حساب عدد المصائد تلقائياً"""
    return max(1, int(length / 150))

def calculate_line_cost(line):
    """حساب تكلفة خط واحد"""
    diameter = line.get("diameter", 600)
    depth = line.get("depth", 1.5)
    length = line.get("length", 0)
    
    price_per_meter = PIPE_PRICES.get(diameter, 725)
    
    # عدد المناهل والمصائد
    num_manholes = calculate_auto_manholes(length, diameter)
    num_traps = calculate_auto_traps(length)
    
    # البنود
    items = [
        {"البند": "أنابيب صرف", "الكمية": length, "الوحدة": "م", "السعر": price_per_meter, "الإجمالي": length * price_per_meter},
        {"البند": "حفر الخندق", "الكمية": length, "الوحدة": "م", "السعر": 50, "الإجمالي": length * 50},
        {"البند": "مناهل", "الكمية": num_manholes, "الوحدة": "عدد", "السعر": 3000, "الإجمالي": num_manholes * 3000},
        {"البند": "مصائد", "الكمية": num_traps, "الوحدة": "عدد", "السعر": 2000, "الإجمالي": num_traps * 2000},
        {"البند": "ردم وتسوية", "الكمية": length * depth, "الوحدة": "م³", "السعر": 30, "الإجمالي": length * depth * 30},
    ]
    
    return {
        "items": items,
        "total": sum(item["الإجمالي"] for item in items),
        "num_manholes": num_manholes,
        "num_traps": num_traps,
    }

class AdvancedNetworkAnalyzer:
    """محلل الشبكة"""
    
    def __init__(self, lines):
        self.lines = [ln for ln in lines if ln.get("selected", True)]
        self.G = nx.Graph()
        self._build_network()
    
    def _build_network(self):
        """بناء الشبكة"""
        for line in self.lines:
            coords = line.get("coords", [])
            if len(coords) < 2:
                continue
            
            for i in range(len(coords) - 1):
                start = tuple(coords[i][:2])
                end = tuple(coords[i + 1][:2])
                
                distance = haversine_distance(coords[i], coords[i+1])
                
                self.G.add_edge(start, end, distance=distance, diameter=line.get("diameter", 600))
    
    def get_stats(self):
        """إحصائيات الشبكة"""
        if self.G.number_of_nodes() == 0:
            return None
        
        return {
            "num_nodes": self.G.number_of_nodes(),
            "num_edges": self.G.number_of_edges(),
            "total_length": sum(data['distance'] for _, _, data in self.G.edges(data=True)),
            "is_connected": nx.is_connected(self.G),
            "density": nx.density(self.G),
            "avg_degree": sum(dict(self.G.degree()).values()) / self.G.number_of_nodes(),
        }
    
    def get_centrality(self):
        """حساب المركزية"""
        try:
            betweenness = nx.betweenness_centrality(self.G, weight='distance')
            degree = nx.degree_centrality(self.G)
            return {"betweenness": betweenness, "degree": degree}
        except:
            return None
    
    def get_critical_nodes(self):
        """المناهل الحرجة"""
        centrality = self.get_centrality()
        if not centrality:
            return []
        
        return sorted(centrality["betweenness"].items(), key=lambda x: x[1], reverse=True)[:10]

# ═════════════════════════════════════════════════════════════════════════════════
# تهيئة Session State
# ═════════════════════════════════════════════════════════════════════════════════

if "lines" not in st.session_state:
    st.session_state.lines = []
if "analyzer" not in st.session_state:
    st.session_state.analyzer = None
if "cost_result" not in st.session_state:
    st.session_state.cost_result = None
if "current_section" not in st.session_state:
    st.session_state.current_section = "الرئيسية"

# ═════════════════════════════════════════════════════════════════════════════════
# Header الرئيسي
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="header-main">
    <h1>🌊 محلل شبكات السيول المتقدم</h1>
    <p>تطبيق احترافي لتحليل وحساب تكاليف شبكات الصرف السيلية</p>
</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════════
# Sidebar
# ═════════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 📋 القائمة الرئيسية")
    st.markdown("---")
    
    sections = {
        "🏠 الرئيسية": "الرئيسية",
        "🗺️ إدارة الخطوط": "الخطوط",
        "💰 حساب التكاليف": "التكاليف",
        "🌐 تحليل الشبكة": "تحليل",
        "📊 التقارير": "تقارير"
    }
    
    selected_section = st.radio(
        "اختر القسم:",
        list(sections.keys()),
        index=0,
        label_visibility="collapsed"
    )
    
    st.session_state.current_section = sections[selected_section]
    
    st.markdown("---")
    
    # معلومات سريعة
    st.markdown("""
    <h4 style="color: white; text-align: center;">📊 معلومات سريعة</h4>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("الخطوط", len(st.session_state.lines))
    with col2:
        total_length = sum(ln.get("length", 0) for ln in st.session_state.lines)
        st.metric("الطول", f"{total_length/1000:.1f} كم")
    
    if st.session_state.cost_result:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("المناهل", st.session_state.cost_result.get("total_manholes", 0))
        with col2:
            st.metric("المصائد", st.session_state.cost_result.get("total_traps", 0))
    
    st.markdown("---")
    
    with st.expander("❓ كيفية الاستخدام"):
        st.markdown("""
        1️⃣ **أضف الخطوط**: من إدارة الخطوط
        2️⃣ **احسب التكاليف**: من حساب التكاليف
        3️⃣ **حلل الشبكة**: من تحليل الشبكة
        4️⃣ **احصل على التقرير**: من التقارير
        """)

# ═════════════════════════════════════════════════════════════════════════════════
# المحتوى الرئيسي
# ═════════════════════════════════════════════════════════════════════════════════

# 1. الصفحة الرئيسية
if st.session_state.current_section == "الرئيسية":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">🗺️</div>
            <div class="metric-label">إدارة الخطوط</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">💰</div>
            <div class="metric-label">حساب التكاليف</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">📊</div>
            <div class="metric-label">التقارير</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("<div class='section-title'>👋 مرحباً بك</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 المميزات الرئيسية
        
        ✅ **رسم تفاعلي**: ارسم خطوطك على الخريطة
        ✅ **استيراد الملفات**: استورد من GeoJSON
        ✅ **حساب تلقائي**: احسب المناهل والمصائد
        ✅ **تحليل الشبكة**: احصل على إحصائيات متقدمة
        ✅ **تقارير شاملة**: احمل النتائج بسهولة
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 البدء السريع
        
        1. اذهب لـ **إدارة الخطوط**
        2. ارسم أو استورد الخطوط
        3. اذهب لـ **حساب التكاليف**
        4. شاهد النتائج والكميات
        5. احمل التقرير
        
        **سهل وسريع وفعّال!** 💪
        """)

# 2. إدارة الخطوط
elif st.session_state.current_section == "الخطوط":
    st.markdown("<div class='section-title'>🗺️ إدارة الخطوط</div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🎨 رسم الخطوط", "📤 استيراد", "📋 الخطوط"])
    
    with tab1:
        st.markdown("### رسم الخطوط على الخريطة")
        
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
        else:
            st.error("❌ مكتبة folium غير مثبتة")
    
    with tab2:
        st.markdown("### استيراد ملفات GeoJSON")
        
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
                    st.success(f"✅ تم استيراد {len(features)} خط")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
    
    with tab3:
        st.markdown("### الخطوط المضافة وإعداداتها")
        
        if not st.session_state.lines:
            st.info("لا توجد خطوط مضافة")
        else:
            for line in st.session_state.lines:
                with st.expander(f"✏️ {line['name']} - {line['length']:,.0f} م", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        line["selected"] = st.checkbox("✅ تفعيل", value=line["selected"], key=f"sel_{line['id']}")
                    
                    with col2:
                        line["diameter"] = st.selectbox(
                            "القطر (ملم)",
                            sorted(PIPE_PRICES.keys()),
                            index=list(PIPE_PRICES.keys()).index(line.get("diameter", 600)),
                            key=f"diam_{line['id']}"
                        )
                    
                    with col3:
                        line["depth"] = st.number_input(
                            "العمق (م)",
                            min_value=0.5,
                            value=line.get("depth", 1.5),
                            step=0.1,
                            key=f"depth_{line['id']}"
                        )
                    
                    with col4:
                        if st.button("🗑️ حذف", key=f"del_{line['id']}"):
                            st.session_state.lines = [l for l in st.session_state.lines if l['id'] != line['id']]
                            st.rerun()

# 3. حساب التكاليف
elif st.session_state.current_section == "التكاليف":
    st.markdown("<div class='section-title'>💰 حساب التكاليف والكميات</div>", unsafe_allow_html=True)
    
    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً أولاً من قسم إدارة الخطوط")
    else:
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("🧮 احسب التكاليف", key="calc_btn"):
                with st.spinner("جاري الحساب..."):
                    selected_lines = [ln for ln in st.session_state.lines if ln.get("selected", True)]
                    
                    if selected_lines:
                        all_items = {}
                        per_line_result = []
                        
                        for line in selected_lines:
                            cost_data = calculate_line_cost(line)
                            per_line_result.append({"line": line, "cost_data": cost_data})
                            
                            for item in cost_data["items"]:
                                key = item["البند"]
                                if key not in all_items:
                                    all_items[key] = {"الكمية": 0, "الإجمالي": 0, "الوحدة": item["الوحدة"], "السعر": item["السعر"]}
                                all_items[key]["الكمية"] += item["الكمية"]
                                all_items[key]["الإجمالي"] += item["الإجمالي"]
                        
                        total_cost = sum(item["الإجمالي"] for item in all_items.values())
                        total_manholes = sum(item["cost_data"]["num_manholes"] for item in per_line_result)
                        total_traps = sum(item["cost_data"]["num_traps"] for item in per_line_result)
                        
                        st.session_state.cost_result = {
                            "per_line": per_line_result,
                            "all_items": all_items,
                            "total_cost": total_cost,
                            "total_manholes": total_manholes,
                            "total_traps": total_traps,
                        }
                        
                        st.success("✅ تم الحساب بنجاح!")
        
        with col1:
            st.markdown("")
        
        if st.session_state.cost_result:
            result = st.session_state.cost_result
            
            # ملخص سريع
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{len(result['per_line'])}</div>
                    <div class="metric-label">الخطوط</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{result['total_manholes']}</div>
                    <div class="metric-label">المناهل</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{result['total_traps']}</div>
                    <div class="metric-label">المصائد</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{result['total_cost']/1e6:.2f}M</div>
                    <div class="metric-label">التكلفة (ريال)</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # التفاصيل
            tab1, tab2, tab3 = st.tabs(["📋 الكميات المجمعة", "🔍 تفاصيل كل خط", "📈 رسم بياني"])
            
            with tab1:
                st.markdown("### جدول الكميات والتكاليف")
                
                items_list = []
                for item_name, item_data in result["all_items"].items():
                    avg_price = item_data["الإجمالي"] / item_data["الكمية"] if item_data["الكمية"] > 0 else 0
                    items_list.append({
                        "البند": item_name,
                        "الكمية": f"{item_data['الكمية']:,.2f}",
                        "الوحدة": item_data["الوحدة"],
                        "السعر": f"{avg_price:,.0f}",
                        "الإجمالي": f"{item_data['الإجمالي']:,.0f}"
                    })
                
                st.dataframe(pd.DataFrame(items_list), use_container_width=True, hide_index=True)
                
                st.markdown(f"### 💵 **التكلفة الإجمالية: {result['total_cost']:,.0f} ريال**")
            
            with tab2:
                st.markdown("### تفاصيل كل خط")
                
                for per_line in result["per_line"]:
                    line = per_line["line"]
                    cost_data = per_line["cost_data"]
                    
                    with st.expander(f"📍 {line['name']} - {line['length']:,.0f} م", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("القطر", f"{line.get('diameter', 600)} ملم")
                        with col2:
                            st.metric("المناهل", cost_data["num_manholes"])
                        with col3:
                            st.metric("المصائد", cost_data["num_traps"])
                        
                        st.markdown("**البنود:**")
                        
                        items_df = pd.DataFrame(cost_data["items"])
                        st.dataframe(items_df, use_container_width=True, hide_index=True)
                        
                        st.markdown(f"**المجموع: {cost_data['total']:,.0f} ريال**")
            
            with tab3:
                st.markdown("### رسم بياني للتكاليف")
                
                fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
                
                items_names = list(result["all_items"].keys())
                items_costs = [result["all_items"][name]["الإجمالي"] for name in items_names]
                
                colors = ['#1a5fa8', '#0a2a5e', '#17a2b8', '#28a745', '#ffc107']
                ax.bar(range(len(items_names)), items_costs, color=colors[:len(items_names)])
                ax.set_xticks(range(len(items_names)))
                ax.set_xticklabels(items_names, rotation=45, ha='right')
                ax.set_ylabel('التكلفة (ريال)', fontsize=11, fontweight='bold')
                ax.set_title('توزيع التكاليف حسب البند', fontsize=13, fontweight='bold')
                ax.grid(axis='y', alpha=0.3)
                
                for i, cost in enumerate(items_costs):
                    ax.text(i, cost, f'{cost:,.0f}', ha='center', va='bottom', fontweight='bold')
                
                st.pyplot(fig, use_container_width=True)

# 4. تحليل الشبكة
elif st.session_state.current_section == "تحليل":
    st.markdown("<div class='section-title'>🌐 تحليل الشبكة</div>", unsafe_allow_html=True)
    
    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً أولاً")
    else:
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("🔍 حلل", key="analyze_btn"):
                with st.spinner("جاري التحليل..."):
                    st.session_state.analyzer = AdvancedNetworkAnalyzer(st.session_state.lines)
                    st.success("✅ تم!")
        
        with col1:
            st.markdown("")
        
        if st.session_state.analyzer:
            analyzer = st.session_state.analyzer
            stats = analyzer.get_stats()
            
            if stats:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{stats['num_nodes']}</div>
                        <div class="metric-label">المناهل</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{stats['num_edges']}</div>
                        <div class="metric-label">الأنابيب</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{stats['total_length']/1000:.1f}</div>
                        <div class="metric-label">الطول (كم)</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{'✅' if stats['is_connected'] else '❌'}</div>
                        <div class="metric-label">الاتصالية</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                with st.expander("🔴 المناهل الحرجة", expanded=True):
                    critical = analyzer.get_critical_nodes()
                    
                    if critical:
                        critical_df = pd.DataFrame([
                            {"#": i+1, "الموقع": f"{node[0]:.5f}, {node[1]:.5f}", "الأهمية": f"{score:.4f}"}
                            for i, (node, score) in enumerate(critical)
                        ])
                        st.dataframe(critical_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("لا توجد نقاط حرجة")
                
                with st.expander("📈 رسم الشبكة", expanded=True):
                    fig, ax = plt.subplots(figsize=(12, 8), facecolor='white')
                    
                    G = analyzer.G
                    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
                    
                    nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.4, ax=ax)
                    nx.draw_networkx_nodes(G, pos, node_size=300, node_color='#1a5fa8', 
                                          ax=ax, edgecolors='#0a2a5e', linewidths=2)
                    
                    st.pyplot(fig, use_container_width=True)

# 5. التقارير
elif st.session_state.current_section == "تقارير":
    st.markdown("<div class='section-title'>📊 التقارير</div>", unsafe_allow_html=True)
    
    if not st.session_state.cost_result:
        st.warning("⚠️ احسب التكاليف أولاً")
    else:
        result = st.session_state.cost_result
        
        col1, col2, col3 = st.columns(3)
        
        # CSV
        with col1:
            csv_content = "البند,الكمية,الوحدة,السعر,الإجمالي\n"
            for name, data in result["all_items"].items():
                avg_price = data["الإجمالي"] / data["الكمية"] if data["الكمية"] > 0 else 0
                csv_content += f"{name},{data['الكمية']:.2f},{data['الوحدة']},{avg_price:.0f},{data['الإجمالي']:.0f}\n"
            
            st.download_button(
                label="📥 تحميل CSV",
                data=csv_content,
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # TXT
        with col2:
            txt_content = "تقرير تحليل شبكة السيول\n"
            txt_content += f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            txt_content += f"عدد الخطوط: {len(result['per_line'])}\n"
            txt_content += f"المناهل: {result['total_manholes']}\n"
            txt_content += f"المصائد: {result['total_traps']}\n"
            txt_content += f"التكلفة الإجمالية: {result['total_cost']:,.0f} ريال\n"
            
            st.download_button(
                label="📥 تحميل TXT",
                data=txt_content,
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        # JSON
        with col3:
            json_content = json.dumps({
                "lines": len(result['per_line']),
                "total_manholes": result['total_manholes'],
                "total_traps": result['total_traps'],
                "total_cost": result['total_cost'],
                "items": {k: {"qty": v["الكمية"], "total": v["الإجمالي"]} for k, v in result["all_items"].items()}
            }, ensure_ascii=False, indent=2)
            
            st.download_button(
                label="📥 تحميل JSON",
                data=json_content,
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        st.markdown("---")
        
        st.markdown("### 📋 معاينة التقرير")
        
        with st.expander("ملخص المشروع", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**عدد الخطوط:** {len(result['per_line'])}")
                st.write(f"**المناهل الكلية:** {result['total_manholes']}")
                st.write(f"**المصائد الكلية:** {result['total_traps']}")
            with col2:
                st.write(f"**التكلفة الإجمالية:** {result['total_cost']:,.0f} ريال")

# ═════════════════════════════════════════════════════════════════════════════════
# Footer
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.85rem; padding: 20px;">
    <p>🌊 محلل شبكات السيول | النسخة 4.0 | تطبيق احترافي</p>
    <p>آخر تحديث: يونيو 2025</p>
</div>
""", unsafe_allow_html=True)

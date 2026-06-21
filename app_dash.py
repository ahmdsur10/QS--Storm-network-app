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

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except:
    GEOPANDAS_AVAILABLE = False

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
    margin: 0;
}

/* Sidebar محسّن */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a2a5e 0%, #1a5fa8 100%) !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    color: white !important;
}

/* أزرار Sidebar */
.sidebar-section {
    background: white;
    border-radius: 12px;
    padding: 15px;
    margin: 12px 0;
    border-left: 5px solid #1a5fa8;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.sidebar-title {
    font-size: 1.1rem;
    font-weight: 900;
    color: #0a2a5e;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 10px;
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
    width: 100% !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(26, 95, 168, 0.3) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(26, 95, 168, 0.4) !important;
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

/* التخطيط */
.element-container {
    animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* responsive */
@media (max-width: 768px) {
    .header-main h1 {
        font-size: 1.5rem;
    }
    
    .metric-value {
        font-size: 1.5rem;
    }
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

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

class AdvancedNetworkAnalyzer:
    """محلل الشبكة المتقدم"""
    
    def __init__(self, lines):
        self.lines = [ln for ln in lines if ln.get("selected", True)]
        self.G = nx.Graph()
        self.G_directed = nx.DiGraph()
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
                self.G_directed.add_edge(start, end, distance=distance, diameter=line.get("diameter", 600))
    
    def get_stats(self):
        """احصائيات الشبكة"""
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
            closeness = nx.closeness_centrality(self.G, distance='distance')
            return {"betweenness": betweenness, "degree": degree, "closeness": closeness}
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
if "current_section" not in st.session_state:
    st.session_state.current_section = "الرئيسية"

# ═════════════════════════════════════════════════════════════════════════════════
# Header الرئيسي
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="header-main">
    <h1>🌊 محلل شبكات السيول المتقدم</h1>
    <p>أداة احترافية لتحليل وتصميم شبكات الصرف السيلية بتقنيات NetworkX المتطورة</p>
</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════════
# Sidebar - القائمة الرئيسية
# ═════════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 📋 القائمة الرئيسية")
    st.markdown("---")
    
    st.markdown("""
    <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; color: white;">
        <h4 style="margin-top: 0; text-align: center;">اختر القسم الذي تريده</h4>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # الأقسام الرئيسية
    sections = {
        "🏠 الرئيسية": "الرئيسية",
        "🗺️ إدارة الخطوط": "الخطوط",
        "🌐 تحليل الشبكة": "تحليل",
        "🔀 تحليل الـ Flow": "flow",
        "📦 القنوات الصندوقية": "قنوات",
        "⚠️ تقييم المخاطر": "مخاطر",
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
    <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
        <h4 style="color: white; margin-top: 0;">📊 معلومات سريعة</h4>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("الخطوط المضافة", len(st.session_state.lines))
    with col2:
        total_length = sum(ln.get("length", 0) for ln in st.session_state.lines)
        st.metric("الطول الكلي", f"{total_length/1000:.1f} كم")
    
    st.markdown("---")
    
    # تعليمات
    with st.expander("❓ كيفية الاستخدام", expanded=False):
        st.markdown("""
        1. **أضف الخطوط**: من قسم إدارة الخطوط
        2. **حلل الشبكة**: من قسم تحليل الشبكة
        3. **تفقد المخاطر**: من قسم تقييم المخاطر
        4. **احمل التقرير**: من قسم التقارير
        """)

# ═════════════════════════════════════════════════════════════════════════════════
# محتوى الصفحة حسب الاختيار
# ═════════════════════════════════════════════════════════════════════════════════

# 1. الصفحة الرئيسية
if st.session_state.current_section == "الرئيسية":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">🗺️</div>
            <div class="metric-label">إدارة الخطوط</div>
            <p style="font-size: 0.85rem; margin-top: 8px; color: #666;">رسم واستيراد الخطوط</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">🌐</div>
            <div class="metric-label">تحليل الشبكة</div>
            <p style="font-size: 0.85rem; margin-top: 8px; color: #666;">احصائيات متقدمة</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">📊</div>
            <div class="metric-label">التقارير</div>
            <p style="font-size: 0.85rem; margin-top: 8px; color: #666;">تحميل النتائج</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("<div class='section-title'>👋 مرحباً بك في محلل شبكات السيول</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 ما هذا التطبيق؟
        
        تطبيق احترافي يستخدم تقنيات NetworkX المتقدمة لتحليل شبكات الصرف السيلية بطرق علمية دقيقة.
        
        #### المميزات الرئيسية:
        - 🗺️ رسم خطوط تفاعلي
        - 📊 تحليل شبكات متقدم
        - 🔀 تحليل تدفق الجريان
        - ⚠️ تقييم المخاطر الذكي
        - 📦 دعم القنوات الصندوقية
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 البدء السريع
        
        اتبع هذه الخطوات:
        
        1. **اذهب لـ 🗺️ إدارة الخطوط**
           - ارسم خطوطك أو استورد ملفات
        
        2. **اذهب لـ 🌐 تحليل الشبكة**
           - انقر زر التحليل
           - شاهد النتائج
        
        3. **اذهب لـ ⚠️ تقييم المخاطر**
           - اعرض درجات الخطورة
        
        4. **اذهب لـ 📊 التقارير**
           - احمل ملفات النتائج
        """)
    
    st.markdown("---")
    
    st.info("💡 استخدم القائمة الجانبية للتنقل بين الأقسام المختلفة")

# 2. إدارة الخطوط
elif st.session_state.current_section == "الخطوط":
    st.markdown("<div class='section-title'>🗺️ إدارة الخطوط</div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🎨 رسم الخطوط", "📤 استيراد ملفات", "📋 الخطوط المضافة"])
    
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
                                    "name": feature.get("properties", {}).get("name", f"خط GeoJSON {idx+1}"),
                                    "length": length,
                                    "coords": coords,
                                    "source": "GeoJSON",
                                    "selected": True,
                                    "diameter": 600,
                                    "depth": 1.5,
                                }
                                st.session_state.lines.append(new_line)
                    
                    st.session_state.analyzer = None
                    st.success(f"✅ تم استيراد {len(features)} خط")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
    
    with tab3:
        st.markdown("### الخطوط المضافة")
        
        if not st.session_state.lines:
            st.info("لا توجد خطوط مضافة حتى الآن")
        else:
            for line in st.session_state.lines:
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.write(f"**{line['name']}** | {line['length']:,.0f} م | {line['source']}")
                
                with col2:
                    if st.button("🗑️", key=line['id']):
                        st.session_state.lines = [l for l in st.session_state.lines if l['id'] != line['id']]
                        st.rerun()
            
            st.markdown("---")
            
            st.markdown("### ⚙️ إعدادات الخطوط")
            
            for line in st.session_state.lines:
                with st.expander(f"إعدادات: {line['name']}", expanded=False):
                    line["selected"] = st.checkbox("تفعيل هذا الخط", value=line["selected"], key=f"sel_{line['id']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        line["diameter"] = st.selectbox(
                            "القطر (ملم)",
                            [400, 500, 600, 700, 800, 900, 1000, 1100, 1200],
                            index=2,
                            key=f"diam_{line['id']}"
                        )
                    with col2:
                        line["depth"] = st.number_input(
                            "العمق (م)",
                            min_value=0.5,
                            value=1.5,
                            step=0.1,
                            key=f"depth_{line['id']}"
                        )

# 3. تحليل الشبكة
elif st.session_state.current_section == "تحليل":
    st.markdown("<div class='section-title'>🌐 تحليل الشبكة</div>", unsafe_allow_html=True)
    
    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً أولاً من قسم إدارة الخطوط")
    else:
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("🔍 حلل الشبكة", key="analyze_btn"):
                with st.spinner("جاري التحليل..."):
                    st.session_state.analyzer = AdvancedNetworkAnalyzer(st.session_state.lines)
                    st.success("✅ تم التحليل بنجاح!")
        
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
                
                # المناهل الحرجة
                with st.expander("🔴 المناهل الحرجة (Critical Nodes)", expanded=True):
                    critical = analyzer.get_critical_nodes()
                    
                    if critical:
                        critical_df = pd.DataFrame([
                            {"#": i+1, "المنهل": f"{node[0]:.4f}, {node[1]:.4f}", "الأهمية": f"{score:.4f}"}
                            for i, (node, score) in enumerate(critical)
                        ])
                        st.dataframe(critical_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("لا توجد نقاط حرجة محددة")
                
                # رسم الشبكة
                with st.expander("📈 رسم الشبكة", expanded=True):
                    fig, ax = plt.subplots(figsize=(12, 8), facecolor='white')
                    
                    G = analyzer.G
                    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
                    
                    nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.4, ax=ax)
                    nx.draw_networkx_nodes(G, pos, node_size=300, node_color='#1a5fa8', 
                                          ax=ax, edgecolors='#0a2a5e', linewidths=2)
                    
                    st.pyplot(fig, use_container_width=True)

# 4. تحليل الـ Flow
elif st.session_state.current_section == "flow":
    st.markdown("<div class='section-title'>🔀 تحليل الـ Flow</div>", unsafe_allow_html=True)
    
    st.info("💡 تحليل اتجاه الجريان في الشبكة (قريباً)")

# 5. القنوات الصندوقية
elif st.session_state.current_section == "قنوات":
    st.markdown("<div class='section-title'>📦 القنوات الصندوقية</div>", unsafe_allow_html=True)
    
    st.info("💡 حساب السعة الهيدروليكية للقنوات الصندوقية (قريباً)")

# 6. تقييم المخاطر
elif st.session_state.current_section == "مخاطر":
    st.markdown("<div class='section-title'>⚠️ تقييم المخاطر</div>", unsafe_allow_html=True)
    
    st.info("💡 تقييم مخاطر الشبكة (قريباً)")

# 7. التقارير
elif st.session_state.current_section == "تقارير":
    st.markdown("<div class='section-title'>📊 التقارير</div>", unsafe_allow_html=True)
    
    if st.session_state.analyzer:
        stats = st.session_state.analyzer.get_stats()
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_content = "المؤشر,القيمة\n"
            csv_content += f"عدد المناهل,{stats['num_nodes']}\n"
            csv_content += f"عدد الأنابيب,{stats['num_edges']}\n"
            csv_content += f"الطول الإجمالي,{stats['total_length']:.0f}\n"
            csv_content += f"الكثافة,{stats['density']:.4f}\n"
            
            st.download_button(
                label="📥 تحميل CSV",
                data=csv_content,
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            txt_content = "تقرير تحليل الشبكة\n"
            txt_content += f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            txt_content += f"عدد المناهل: {stats['num_nodes']}\n"
            txt_content += f"عدد الأنابيب: {stats['num_edges']}\n"
            txt_content += f"الطول الإجمالي: {stats['total_length']/1000:.2f} كم\n"
            txt_content += f"الكثافة: {stats['density']:.4f}\n"
            
            st.download_button(
                label="📥 تحميل TXT",
                data=txt_content,
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    else:
        st.warning("⚠️ قم بتحليل الشبكة أولاً")

# ═════════════════════════════════════════════════════════════════════════════════
# Footer
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.85rem; padding: 20px;">
    <p>🌊 محلل شبكات السيول | النسخة 4.0 | تطبيق احترافي محسّن</p>
    <p>آخر تحديث: يونيو 2025</p>
</div>
""", unsafe_allow_html=True)

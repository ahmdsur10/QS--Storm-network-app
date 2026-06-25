import streamlit as st
import math
import json
import uuid
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO

try:
    import folium
    from streamlit_folium import st_folium
    from folium.plugins import Draw
    FOLIUM_AVAILABLE = True
except:
    FOLIUM_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    PDF_AVAILABLE = True
except:
    PDF_AVAILABLE = False

# ═════════════════════════════════════════════════════════════════════════════════
# إعدادات الصفحة
# ═════════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="محلل شبكات السيول", page_icon="🌊", layout="wide", initial_sidebar_state="expanded")

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Cairo', sans-serif !important; }
html, body, [class*="css"] { direction: rtl; text-align: right; }
.stApp { background: #f8f9fa; }
.header-main {
    background: linear-gradient(135deg, #0a2a5e 0%, #1a5fa8 100%);
    color: white; padding: 35px; border-radius: 15px; margin-bottom: 30px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.15); text-align: center;
}
.header-main h1 { font-size: 2.5rem; font-weight: 900; margin-bottom: 10px; }
.section-title { color: #0a2a5e; font-size: 1.8rem; font-weight: 900; margin: 20px 0 15px 0; border-bottom: 4px solid #1a5fa8; padding-bottom: 10px; }
.big-metric-card { background: white; border-radius: 12px; padding: 25px; margin: 15px 0; border: 3px solid #1a5fa8; text-align: center; }
.big-metric-value { font-size: 3rem; font-weight: 900; color: #0a2a5e; margin: 10px 0; }
.big-metric-label { font-size: 1.1rem; color: #6b7a99; font-weight: 700; }
.stButton > button { background: linear-gradient(135deg, #1a5fa8 0%, #0a2a5e 100%) !important; color: white !important; border-radius: 10px !important; font-weight: 700 !important; }
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

def calculate_traps(length):
    """حساب المصائد: الطول ÷ 35"""
    return max(1, round(length / 35))

class AdvancedNetworkAnalyzer:
    """محلل الشبكة"""
    
    def __init__(self, lines):
        self.lines = [ln for ln in lines if ln.get("selected", True)]
        self.G = nx.Graph()
        self.edges_info = {}  # معلومات كل حافة (فرع)
        self.node_to_coord = {}
        self._build_network()
    
    def _build_network(self):
        """بناء الشبكة مع معلومات الفروع"""
        node_id = 0
        edge_id = 0
        
        for line_idx, line in enumerate(self.lines):
            coords = line.get("coords", [])
            if len(coords) < 2:
                continue
            
            for i in range(len(coords) - 1):
                start = tuple(coords[i][:2])
                end = tuple(coords[i + 1][:2])
                
                if start not in self.node_to_coord:
                    self.G.add_node(node_id, coord=start)
                    self.node_to_coord[start] = node_id
                    node_id += 1
                
                if end not in self.node_to_coord:
                    self.G.add_node(node_id, coord=end)
                    self.node_to_coord[end] = node_id
                    node_id += 1
                
                distance = haversine_distance(coords[i], coords[i+1])
                start_node = self.node_to_coord[start]
                end_node = self.node_to_coord[end]
                
                # معلومات الفرع
                edge_key = f"edge_{edge_id}"
                self.edges_info[edge_key] = {
                    "id": edge_key,
                    "start_coord": start,
                    "end_coord": end,
                    "distance": distance,
                    "diameter": line.get("diameter", 600),
                    "depth": line.get("depth", 1.5),
                    "line_name": line.get("name"),
                    "node_start": start_node,
                    "node_end": end_node,
                }
                
                self.G.add_edge(start_node, end_node, distance=distance, edge_id=edge_key)
                edge_id += 1
    
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

# ═════════════════════════════════════════════════════════════════════════════════
# Session State
# ═════════════════════════════════════════════════════════════════════════════════

if "lines" not in st.session_state:
    st.session_state.lines = []
if "analyzer" not in st.session_state:
    st.session_state.analyzer = None
if "edges_data" not in st.session_state:
    st.session_state.edges_data = {}
if "cost_result" not in st.session_state:
    st.session_state.cost_result = None

# ═════════════════════════════════════════════════════════════════════════════════
# Header
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="header-main">
    <h1>🌊 محلل شبكات السيول - النسخة المحسّنة</h1>
    <p>تحليل الشبكة أولاً، ثم إدارة بيانات كل فرع، ثم حساب التكاليف مع تقرير PDF</p>
</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════════
# الأقسام الرئيسية
# ═════════════════════════════════════════════════════════════════════════════════

tabs = st.tabs(["🏠 الرئيسية", "🗺️ الرسم والاستيراف", "🌐 تحليل الشبكة", "⚙️ إدارة البيانات", "💰 حساب التكاليف", "📊 التقرير"])

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 1: الرئيسية
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[0]:
    st.markdown("<h2 class='section-title'>🏠 مرحباً بك</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    ## تدفق العمل الجديد:
    
    **1️⃣ ارسم الخطوط أو استورد من ملفات**
    - استخدم تبويب "الرسم والاستيراف"
    
    **2️⃣ حلل الشبكة**
    - استخدم تبويب "تحليل الشبكة"
    - سيظهر لك عدد المناهل والفروع
    
    **3️⃣ أدخل بيانات كل فرع**
    - استخدم تبويب "إدارة البيانات"
    - أدخل القطر والعمق لكل فرع
    
    **4️⃣ احسب التكاليف**
    - استخدم تبويب "حساب التكاليف"
    - احصل على الكميات والأسعار
    
    **5️⃣ احمل التقرير**
    - استخدم تبويب "التقرير"
    - احصل على PDF مع خريطة OpenStreetMap
    """)

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 2: الرسم والاستيراف
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[1]:
    st.markdown("<h2 class='section-title'>🗺️ الرسم والاستيراف</h2>", unsafe_allow_html=True)
    
    sub_tab1, sub_tab2 = st.tabs(["🎨 الرسم", "📤 الاستيراف"])
    
    with sub_tab1:
        if FOLIUM_AVAILABLE:
            m = folium.Map(location=[24.7136, 46.6753], zoom_start=12, tiles="OpenStreetMap")
            
            for line in st.session_state.lines:
                coords = line.get("coords", [])
                if coords:
                    folium.PolyLine(coords, color="red", weight=3).add_to(m)
            
            draw = Draw(export=True, position="topleft", draw_options={"polyline": True, "polygon": False, "rectangle": False})
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
                            "selected": True,
                            "diameter": 600,
                            "depth": 1.5,
                        }
                        st.session_state.lines.append(new_line)
                        st.success(f"✅ تم إضافة {new_line['name']}")
                        st.rerun()
    
    with sub_tab2:
        uploaded_file = st.file_uploader("اختر GeoJSON", type=["geojson"])
        
        if uploaded_file:
            try:
                geojson_data = json.load(uploaded_file)
                features = geojson_data.get("features", [])
                
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
                                "selected": True,
                                "diameter": 600,
                                "depth": 1.5,
                            }
                            st.session_state.lines.append(new_line)
                
                st.success(f"✅ تم استيراف {len(features)} خط")
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 3: تحليل الشبكة
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[2]:
    st.markdown("<h2 class='section-title'>🌐 تحليل الشبكة</h2>", unsafe_allow_html=True)
    
    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً أولاً")
    else:
        col1, col2 = st.columns([4, 1])
        
        with col2:
            if st.button("🔍 حلل", use_container_width=True):
                with st.spinner("جاري التحليل..."):
                    st.session_state.analyzer = AdvancedNetworkAnalyzer(st.session_state.lines)
                    st.session_state.edges_data = {}
                    
                    if st.session_state.analyzer:
                        for edge_key, edge_info in st.session_state.analyzer.edges_info.items():
                            st.session_state.edges_data[edge_key] = {
                                "diameter": edge_info["diameter"],
                                "depth": edge_info["depth"],
                            }
                    
                    st.success("✅ تم!")
        
        if st.session_state.analyzer:
            stats = st.session_state.analyzer.get_stats()
            
            if stats:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="big-metric-card">
                    <div class="big-metric-value">{stats['num_nodes']}</div>
                    <div class="big-metric-label">المناهل</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="big-metric-card">
                    <div class="big-metric-value">{stats['num_edges']}</div>
                    <div class="big-metric-label">الفروع (الأنابيب)</div>
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

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 4: إدارة البيانات (كل فرع)
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[3]:
    st.markdown("<h2 class='section-title'>⚙️ إدارة بيانات كل فرع</h2>", unsafe_allow_html=True)
    
    if not st.session_state.analyzer:
        st.warning("⚠️ حلل الشبكة أولاً")
    else:
        st.info("📌 أدخل بيانات كل فرع (أنبوب)")
        
        edges = st.session_state.analyzer.edges_info
        
        for edge_key, edge_info in edges.items():
            with st.expander(f"🔧 {edge_info['line_name']} - {edge_info['distance']/1000:.3f} كم"):
                col1, col2 = st.columns(2)
                
                with col1:
                    diameter = st.selectbox(
                        "القطر (ملم)",
                        sorted(PIPE_PRICES.keys()),
                        index=list(PIPE_PRICES.keys()).index(st.session_state.edges_data.get(edge_key, {}).get("diameter", 600)),
                        key=f"diam_{edge_key}"
                    )
                
                with col2:
                    depth = st.number_input(
                        "العمق (م)",
                        min_value=0.5,
                        value=float(st.session_state.edges_data.get(edge_key, {}).get("depth", 1.5)),
                        step=0.1,
                        key=f"depth_{edge_key}"
                    )
                
                if edge_key not in st.session_state.edges_data:
                    st.session_state.edges_data[edge_key] = {}
                
                st.session_state.edges_data[edge_key]["diameter"] = diameter
                st.session_state.edges_data[edge_key]["depth"] = depth

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 5: حساب التكاليف
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[4]:
    st.markdown("<h2 class='section-title'>💰 حساب التكاليف</h2>", unsafe_allow_html=True)
    
    if not st.session_state.analyzer or not st.session_state.edges_data:
        st.warning("⚠️ أدخل بيانات الفروع أولاً")
    else:
        col1, col2 = st.columns([4, 1])
        
        with col2:
            if st.button("🧮 احسب", use_container_width=True):
                with st.spinner("جاري الحساب..."):
                    analyzer = st.session_state.analyzer
                    stats = analyzer.get_stats()
                    
                    all_items = {}
                    per_edge_result = []
                    total_length = stats['total_length']
                    
                    for edge_key, edge_info in analyzer.edges_info.items():
                        edge_data = st.session_state.edges_data.get(edge_key, {})
                        diameter = edge_data.get("diameter", 600)
                        depth = edge_data.get("depth", 1.5)
                        length = edge_info["distance"]
                        
                        # حصة هذا الفرع من المناهل
                        share = length / total_length if total_length > 0 else 0
                        num_nodes = max(1, round(stats['num_nodes'] * share))
                        num_traps = calculate_traps(length)
                        
                        price_per_meter = PIPE_PRICES.get(diameter, 725)
                        
                        items = [
                            {"البند": "أنابيب", "الكمية": length, "الوحدة": "م", "السعر": price_per_meter, "الإجمالي": length * price_per_meter},
                            {"البند": "حفر", "الكمية": length, "الوحدة": "م", "السعر": 50, "الإجمالي": length * 50},
                            {"البند": "مناهل", "الكمية": num_nodes, "الوحدة": "عدد", "السعر": 3000, "الإجمالي": num_nodes * 3000},
                            {"البند": "مصائد", "الكمية": num_traps, "الوحدة": "عدد", "السعر": 2000, "الإجمالي": num_traps * 2000},
                            {"البند": "ردم", "الكمية": length * depth, "الوحدة": "م³", "السعر": 30, "الإجمالي": length * depth * 30},
                        ]
                        
                        total = sum(item["الإجمالي"] for item in items)
                        
                        per_edge_result.append({
                            "edge_key": edge_key,
                            "line_name": edge_info["line_name"],
                            "diameter": diameter,
                            "depth": depth,
                            "length": length,
                            "items": items,
                            "total": total,
                            "num_nodes": num_nodes,
                            "num_traps": num_traps,
                        })
                        
                        for item in items:
                            key = item["البند"]
                            if key not in all_items:
                                all_items[key] = {"الكمية": 0, "الإجمالي": 0, "الوحدة": item["الوحدة"]}
                            all_items[key]["الكمية"] += item["الكمية"]
                            all_items[key]["الإجمالي"] += item["الإجمالي"]
                    
                    total_cost = sum(item["الإجمالي"] for item in all_items.values())
                    total_traps = sum(edge["num_traps"] for edge in per_edge_result)
                    total_nodes = sum(edge["num_nodes"] for edge in per_edge_result)
                    
                    st.session_state.cost_result = {
                        "per_edge": per_edge_result,
                        "all_items": all_items,
                        "total_cost": total_cost,
                        "total_nodes": total_nodes,
                        "total_traps": total_traps,
                        "analyzer": analyzer,
                    }
                    
                    st.success("✅ تم!")
        
        if st.session_state.cost_result:
            result = st.session_state.cost_result
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="big-metric-card">
                <div class="big-metric-value">{result['total_nodes']}</div>
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
                <div class="big-metric-value">{len(result['per_edge'])}</div>
                <div class="big-metric-label">الفروع</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            sub_tab1, sub_tab2 = st.tabs(["📋 الملخص", "🔍 التفاصيل"])
            
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
            
            with sub_tab2:
                for edge in result["per_edge"]:
                    with st.expander(f"📍 {edge['line_name']} ({edge['length']/1000:.3f} كم) - قطر {edge['diameter']}"):
                        st.dataframe(pd.DataFrame(edge["items"]), use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 6: التقرير PDF
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[5]:
    st.markdown("<h2 class='section-title'>📊 التقرير PDF مع الخريطة</h2>", unsafe_allow_html=True)
    
    if not st.session_state.cost_result:
        st.warning("⚠️ احسب التكاليف أولاً")
    else:
        if st.button("📥 توليد التقرير PDF", use_container_width=True):
            with st.spinner("جاري توليد التقرير..."):
                try:
                    result = st.session_state.cost_result
                    analyzer = result["analyzer"]
                    
                    # إنشاء خريطة OpenStreetMap
                    map_osm = folium.Map(location=[24.7136, 46.6753], zoom_start=12, tiles="OpenStreetMap")
                    
                    # رسم الخطوط على الخريطة
                    for line in st.session_state.lines:
                        coords = line.get("coords", [])
                        if coords:
                            folium.PolyLine(coords, color="blue", weight=3, opacity=0.8, popup=line['name']).add_to(map_osm)
                    
                    # رسم المناهل
                    for node, node_data in analyzer.G.nodes(data=True):
                        if 'coord' in node_data:
                            coord = node_data['coord']
                            folium.CircleMarker(
                                location=coord,
                                radius=6,
                                popup="منهل",
                                color="red",
                                fill=True,
                                fillColor="red"
                            ).add_to(map_osm)
                    
                    # حفظ الخريطة مؤقتاً
                    map_file = f"/tmp/map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    map_osm.save(map_file)
                    
                    # إنشاء PDF
                    pdf_file = f"/tmp/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    
                    if PDF_AVAILABLE:
                        doc = SimpleDocTemplate(pdf_file, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
                        elements = []
                        
                        # العنوان
                        styles = getSampleStyleSheet()
                        title_style = ParagraphStyle(name='Title', fontSize=24, textColor=colors.HexColor('#0a2a5e'),
                                                     alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=20)
                        elements.append(Paragraph("تقرير شبكة السيول", title_style))
                        elements.append(Spacer(1, 10))
                        
                        # معلومات المشروع
                        info_style = ParagraphStyle(name='Info', fontSize=10, alignment=TA_RIGHT)
                        elements.append(Paragraph(f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}", info_style))
                        elements.append(Spacer(1, 15))
                        
                        # ملخص
                        summary_data = [
                            ["المؤشر", "القيمة"],
                            ["المناهل", str(result["total_nodes"])],
                            ["الأنابيب (الفروع)", str(len(result["per_edge"]))],
                            ["المصائد", str(result["total_traps"])],
                            [f"التكلفة الإجمالية (ريال)", f"{result['total_cost']:,.0f}"],
                        ]
                        
                        summary_table = Table(summary_data, colWidths=[100*mm, 100*mm])
                        summary_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5fa8')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 12),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        
                        elements.append(summary_table)
                        elements.append(Spacer(1, 15))
                        
                        # جدول الكميات
                        elements.append(Paragraph("الكميات والأسعار", title_style))
                        elements.append(Spacer(1, 10))
                        
                        items_data = [["البند", "الكمية", "الوحدة", "الإجمالي (ريال)"]]
                        for item_name, item_data in result["all_items"].items():
                            items_data.append([
                                item_name,
                                f"{item_data['الكمية']:,.2f}",
                                item_data["الوحدة"],
                                f"{item_data['الإجمالي']:,.0f}"
                            ])
                        
                        items_table = Table(items_data, colWidths=[70*mm, 60*mm, 50*mm, 70*mm])
                        items_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5fa8')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        
                        elements.append(items_table)
                        elements.append(PageBreak())
                        
                        # الخريطة
                        elements.append(Paragraph("خريطة الشبكة", title_style))
                        elements.append(Spacer(1, 10))
                        elements.append(Paragraph("اضغط <a href='#'>هنا</a> لعرض الخريطة", info_style))
                        
                        doc.build(elements)
                        
                        # قراءة ملف PDF
                        with open(pdf_file, "rb") as f:
                            pdf_bytes = f.read()
                        
                        st.download_button(
                            label="📥 تحميل PDF",
                            data=pdf_bytes,
                            file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        
                        st.success("✅ تم إنشاء التقرير!")
                    
                    # عرض الخريطة
                    st.markdown("---")
                    st.markdown("### 🗺️ خريطة الشبكة (OpenStreetMap)")
                    
                    with open(map_file, "r", encoding="utf-8") as f:
                        map_html = f.read()
                    
                    st.components.v1.html(map_html, height=600)
                    
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

# ═════════════════════════════════════════════════════════════════════════════════
# Footer
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.9rem; padding: 20px;">
    <p>🌊 محلل شبكات السيول | النسخة 9.0 - تحليل → إدارة بيانات → حساب → تقرير PDF</p>
</div>
""", unsafe_allow_html=True)

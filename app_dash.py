import streamlit as st
import math
import json
import uuid
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
from folium.plugins import FullScreen

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except:
    GEOPANDAS_AVAILABLE = False

# إزالة الأزرار الخطيرة
st.set_page_config(page_title="محلل شبكات السيول", page_icon="🌊", layout="wide", initial_sidebar_state="expanded", menu_items={"About": None})

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Cairo', sans-serif !important; }
html, body, [class*="css"] { direction: rtl; text-align: right; }
.stApp { background: #f8f9fa; }
.header { background: linear-gradient(135deg, #0a2a5e 0%, #1a5fa8 100%); color: white; padding: 35px; border-radius: 15px; margin-bottom: 30px; box-shadow: 0 8px 25px rgba(0,0,0,0.15); text-align: center; }
.header h1 { font-size: 2.5rem; font-weight: 900; margin-bottom: 10px; }
.title { color: #0a2a5e; font-size: 1.8rem; font-weight: 900; margin: 20px 0 15px 0; border-bottom: 4px solid #1a5fa8; padding-bottom: 10px; }
.card { background: white; border-radius: 12px; padding: 25px; margin: 15px 0; border: 3px solid #1a5fa8; text-align: center; }
.card-value { font-size: 2.5rem; font-weight: 900; color: #0a2a5e; }
.card-label { font-size: 1rem; color: #6b7a99; font-weight: 700; }
.stButton > button { background: linear-gradient(135deg, #1a5fa8 0%, #0a2a5e 100%) !important; color: white !important; border-radius: 10px !important; font-weight: 700 !important; }
.zoom-button { background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%) !important; font-size: 1.2rem !important; padding: 15px 30px !important; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# الثوابت
PIPE_PRICES = {
    400: 454, 500: 619, 600: 725, 700: 906, 800: 1045,
    900: 1225, 1000: 1440, 1100: 1600, 1200: 1812, 1300: 1920, 1400: 2132,
}

def haversine_distance(coord1, coord2):
    lat1, lon1 = coord1[0], coord1[1]
    lat2, lon2 = coord2[0], coord2[1]
    R = 6_371_000
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat, delta_lon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def calculate_traps(length):
    return max(1, round(length / 35))

def get_bounds(coords):
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]

class NetworkAnalyzer:
    def __init__(self, lines):
        self.lines = [ln for ln in lines if ln.get("selected", True)]
        self.G = nx.Graph()
        self.edges_list = []
        self.nodes_coords = {}
        self._build_network()
    
    def _build_network(self):
        node_id = 0
        
        for line in self.lines:
            coords = line.get("coords", [])
            if len(coords) < 2:
                continue
            
            for i in range(len(coords) - 1):
                start = tuple(coords[i][:2])
                end = tuple(coords[i + 1][:2])
                
                if start not in self.nodes_coords:
                    self.nodes_coords[start] = node_id
                    self.G.add_node(node_id)
                    node_id += 1
                
                if end not in self.nodes_coords:
                    self.nodes_coords[end] = node_id
                    self.G.add_node(node_id)
                    node_id += 1
                
                distance = haversine_distance(coords[i], coords[i+1])
                start_node = self.nodes_coords[start]
                end_node = self.nodes_coords[end]
                
                self.G.add_edge(start_node, end_node, distance=distance)
                
                self.edges_list.append({
                    "id": len(self.edges_list),
                    "start_coord": start,
                    "end_coord": end,
                    "distance": distance,
                    "line_name": line.get("name"),
                    "node_start": start_node,
                    "node_end": end_node,
                    "diameter": 600,
                    "depth": 1.5,
                })
    
    def get_stats(self):
        return {
            "num_nodes": self.G.number_of_nodes(),
            "num_edges": len(self.edges_list),
            "total_length": sum(e["distance"] for e in self.edges_list),
        }

# Session State
if "lines" not in st.session_state:
    st.session_state.lines = []
if "analyzer" not in st.session_state:
    st.session_state.analyzer = None
if "cost_result" not in st.session_state:
    st.session_state.cost_result = None

# Header
st.markdown("""
<div class="header">
    <h1>🌊 محلل شبكات السيول</h1>
    <p>تحليل شامل وحساب دقيق لتكاليف شبكات الصرف السيلية</p>
</div>
""", unsafe_allow_html=True)

# الأقسام
tabs = st.tabs(["🏠 الرئيسية", "🗺️ الرسم والاستيراف", "🌐 التحليل", "⚙️ الإعدادات والحساب", "🗺️ التقرير"])

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 1: الرئيسية
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[0]:
    st.markdown("<h2 class='title'>مرحباً بك في محلل شبكات السيول</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="card">
        <div style="font-size: 2rem; margin-bottom: 10px;">1️⃣</div>
        <div class="card-label"><strong>الرسم والاستيراف</strong><br>ارسم الخطوط أو استورد</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
        <div style="font-size: 2rem; margin-bottom: 10px;">2️⃣</div>
        <div class="card-label"><strong>التحليل</strong><br>حلل الشبكة الفعلية</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card">
        <div style="font-size: 2rem; margin-bottom: 10px;">3️⃣</div>
        <div class="card-label"><strong>الحساب</strong><br>احسب التكاليف والكميات</div>
        </div>
        """, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 2: الرسم والاستيراف
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[1]:
    st.markdown("<h2 class='title'>🗺️ الرسم والاستيراف</h2>", unsafe_allow_html=True)
    
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🎨 رسم", "📤 GeoJSON", "📦 Shapefile"])
    
    with sub_tab1:
        st.markdown("### رسم الخطوط على الخريطة")
        m = folium.Map(location=[24.7136, 46.6753], zoom_start=12, tiles="OpenStreetMap")
        FullScreen().add_to(m)
        
        for line in st.session_state.lines:
            coords = line.get("coords", [])
            if coords:
                folium.PolyLine(coords, color="red", weight=3, popup=line["name"]).add_to(m)
        
        draw = Draw(export=True, position="topleft", draw_options={"polyline": True, "polygon": False, "rectangle": False})
        draw.add_to(m)
        
        map_data = st_folium(m, width=None, height=700)
        
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
                    }
                    st.session_state.lines.append(new_line)
                    st.session_state.analyzer = None
                    st.success(f"✅ تم إضافة {new_line['name']}")
                    st.rerun()
    
    with sub_tab2:
        st.markdown("### استيراف GeoJSON")
        uploaded_geojson = st.file_uploader("اختر ملف GeoJSON", type=["geojson", "json"])
        
        if uploaded_geojson:
            try:
                geojson_data = json.load(uploaded_geojson)
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
                            }
                            st.session_state.lines.append(new_line)
                
                st.session_state.analyzer = None
                st.success(f"✅ تم استيراف {len(features)} خط")
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
    
    with sub_tab3:
        if GEOPANDAS_AVAILABLE:
            st.markdown("### استيراف Shapefile")
            uploaded_shp = st.file_uploader("اختر ملف Shapefile (ZIP)", type=["zip"])
            
            if uploaded_shp:
                try:
                    import tempfile
                    import zipfile
                    
                    with tempfile.TemporaryDirectory() as tmpdir:
                        with zipfile.ZipFile(uploaded_shp, 'r') as zip_ref:
                            zip_ref.extractall(tmpdir)
                        
                        import os
                        shp_file = None
                        for file in os.listdir(tmpdir):
                            if file.endswith('.shp'):
                                shp_file = os.path.join(tmpdir, file)
                                break
                        
                        if shp_file:
                            gdf = gpd.read_file(shp_file)
                            
                            if gdf.crs is not None and gdf.crs != 'EPSG:4326':
                                gdf = gdf.to_crs('EPSG:4326')
                            
                            for idx, row in gdf.iterrows():
                                if row.geometry.geom_type == 'LineString':
                                    coords = [(lat, lon) for lon, lat in row.geometry.coords]
                                    if len(coords) >= 2:
                                        length = sum(haversine_distance(coords[i], coords[i+1]) for i in range(len(coords)-1))
                                        
                                        new_line = {
                                            "id": str(uuid.uuid4()),
                                            "name": f"خط {idx+1}",
                                            "length": length,
                                            "coords": coords,
                                            "selected": True,
                                        }
                                        st.session_state.lines.append(new_line)
                            
                            st.session_state.analyzer = None
                            st.success(f"✅ تم استيراف {len(gdf)} خط")
                            st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
        else:
            st.warning("⚠️ مكتبة geopandas غير مثبتة")

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 3: التحليل
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[2]:
    st.markdown("<h2 class='title'>🌐 تحليل الشبكة</h2>", unsafe_allow_html=True)
    
    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً أولاً")
    else:
        col1, col2 = st.columns([4, 1])
        
        with col2:
            if st.button("🔍 حلل الشبكة", use_container_width=True):
                with st.spinner("جاري التحليل..."):
                    st.session_state.analyzer = NetworkAnalyzer(st.session_state.lines)
                    st.success("✅ تم!")
        
        if st.session_state.analyzer:
            stats = st.session_state.analyzer.get_stats()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="card">
                <div class="card-value">{stats['num_nodes']}</div>
                <div class="card-label">المناهل</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="card">
                <div class="card-value">{stats['num_edges']}</div>
                <div class="card-label">الفروع</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="card">
                <div class="card-value">{stats['total_length']/1000:.1f}</div>
                <div class="card-label">الطول (كم)</div>
                </div>
                """, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 4: الإعدادات والحساب
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[3]:
    st.markdown("<h2 class='title'>⚙️ الإعدادات والحساب</h2>", unsafe_allow_html=True)
    
    if not st.session_state.analyzer:
        st.warning("⚠️ حلل الشبكة أولاً")
    else:
        st.markdown("### إدارة الفروع")
        st.info("📌 أدخل القطر والعمق لكل فرع")
        
        for idx, edge in enumerate(st.session_state.analyzer.edges_list):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 2])
            
            with col1:
                st.write(f"**{idx+1}. {edge['line_name']}**")
            
            with col2:
                st.write(f"الطول: {edge['distance']/1000:.3f} كم")
            
            with col3:
                diameter = st.selectbox(
                    "القطر",
                    sorted(PIPE_PRICES.keys()),
                    index=list(PIPE_PRICES.keys()).index(600),
                    key=f"d_{idx}",
                    label_visibility="collapsed"
                )
            
            with col4:
                depth = st.number_input(
                    "العمق",
                    min_value=0.5,
                    value=1.5,
                    step=0.1,
                    key=f"dp_{idx}",
                    label_visibility="collapsed"
                )
            
            st.session_state.analyzer.edges_list[idx]["diameter"] = diameter
            st.session_state.analyzer.edges_list[idx]["depth"] = depth
        
        st.markdown("---")
        
        col1, col2 = st.columns([4, 1])
        
        with col2:
            if st.button("🧮 احسب التكاليف", use_container_width=True):
                with st.spinner("جاري الحساب..."):
                    analyzer = st.session_state.analyzer
                    stats = analyzer.get_stats()
                    
                    all_items = {}
                    per_edge_result = []
                    total_length = stats['total_length']
                    
                    for edge in analyzer.edges_list:
                        diameter = edge["diameter"]
                        depth = edge["depth"]
                        length = edge["distance"]
                        
                        share = length / total_length if total_length > 0 else 0
                        num_nodes = max(1, round(stats['num_nodes'] * share))
                        num_traps = calculate_traps(length)
                        
                        price_per_meter = PIPE_PRICES.get(diameter, 725)
                        
                        items = [
                            {"البند": "أنابيب صرف", "الكمية": length, "الوحدة": "م", "السعر": price_per_meter, "الإجمالي": length * price_per_meter},
                            {"البند": "حفر الخندق", "الكمية": length, "الوحدة": "م", "السعر": 50, "الإجمالي": length * 50},
                            {"البند": "مناهل", "الكمية": num_nodes, "الوحدة": "عدد", "السعر": 3000, "الإجمالي": num_nodes * 3000},
                            {"البند": "مصائد", "الكمية": num_traps, "الوحدة": "عدد", "السعر": 2000, "الإجمالي": num_traps * 2000},
                            {"البند": "ردم وتسوية", "الكمية": length * depth, "الوحدة": "م³", "السعر": 30, "الإجمالي": length * depth * 30},
                        ]
                        
                        total = sum(item["الإجمالي"] for item in items)
                        
                        per_edge_result.append({
                            "line_name": edge["line_name"],
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
                    
                    st.session_state.cost_result = {
                        "per_edge": per_edge_result,
                        "all_items": all_items,
                        "total_cost": total_cost,
                        "stats": stats,
                    }
                    
                    st.success("✅ تم!")
        
        if st.session_state.cost_result:
            result = st.session_state.cost_result
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="card">
                <div class="card-value">{sum(e['num_nodes'] for e in result['per_edge'])}</div>
                <div class="card-label">المناهل</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="card">
                <div class="card-value">{sum(e['num_traps'] for e in result['per_edge'])}</div>
                <div class="card-label">المصائد</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="card">
                <div class="card-value">{len(result['per_edge'])}</div>
                <div class="card-label">الفروع</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="card">
                <div class="card-value">{result['total_cost']/1e6:.2f}M</div>
                <div class="card-label">التكلفة (ريال)</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            items_list = []
            for item_name, item_data in result["all_items"].items():
                items_list.append({
                    "البند": item_name,
                    "الكمية": f"{item_data['الكمية']:,.2f}",
                    "الوحدة": item_data["الوحدة"],
                    "الإجمالي": f"{item_data['الإجمالي']:,.0f}"
                })
            
            st.dataframe(pd.DataFrame(items_list), use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 5: التقرير والخريطة
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[4]:
    st.markdown("<h2 class='title'>🗺️ التقرير والخريطة</h2>", unsafe_allow_html=True)
    
    if not st.session_state.analyzer:
        st.warning("⚠️ حلل الشبكة أولاً")
    else:
        sub_tab1, sub_tab2 = st.tabs(["🗺️ الخريطة", "📊 التقرير PDF"])
        
        with sub_tab1:
            st.markdown("### خريطة الشبكة (OpenStreetMap)")
            
            analyzer = st.session_state.analyzer
            
            all_coords = []
            for line in st.session_state.lines:
                all_coords.extend(line.get("coords", []))
            
            if all_coords:
                bounds = get_bounds(all_coords)
                center = [
                    (bounds[0][0] + bounds[1][0]) / 2,
                    (bounds[0][1] + bounds[1][1]) / 2
                ]
            else:
                center = [24.7136, 46.6753]
            
            map_osm = folium.Map(location=center, zoom_start=14, tiles="OpenStreetMap")
            FullScreen().add_to(map_osm)
            
            for line in st.session_state.lines:
                coords = line.get("coords", [])
                if coords:
                    folium.PolyLine(coords, color="blue", weight=3, opacity=0.8, popup=line['name']).add_to(map_osm)
            
            for node_id in analyzer.G.nodes():
                for coord, nid in analyzer.nodes_coords.items():
                    if nid == node_id:
                        folium.CircleMarker(
                            location=coord,
                            radius=6,
                            popup="منهل",
                            color="red",
                            fill=True,
                            fillColor="red",
                            weight=2
                        ).add_to(map_osm)
            
            if all_coords:
                map_osm.fit_bounds(bounds)
            
            st.markdown("### 🔍 تكبير الخريطة")
            st.info("اضغط على أيقونة المربع في أعلى يسار الخريطة لتكبيرها بملء الشاشة")
            
            st_folium(map_osm, width=None, height=800)
        
        with sub_tab2:
            if not st.session_state.cost_result:
                st.warning("⚠️ احسب التكاليف أولاً")
            else:
                if st.button("📥 تحميل التقرير PDF", use_container_width=True):
                    with st.spinner("جاري توليد التقرير..."):
                        try:
                            from reportlab.lib.pagesizes import landscape, A4
                            from reportlab.lib import colors
                            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
                            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
                            from reportlab.lib.enums import TA_CENTER
                            from reportlab.lib.units import mm
                            
                            result = st.session_state.cost_result
                            
                            pdf_buffer = io.BytesIO()
                            doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
                            
                            elements = []
                            styles = getSampleStyleSheet()
                            
                            title = Paragraph("DRAINAGE NETWORK ANALYSIS REPORT", styles['Heading1'])
                            elements.append(title)
                            elements.append(Spacer(1, 12))
                            
                            date_text = Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal'])
                            elements.append(date_text)
                            elements.append(Spacer(1, 12))
                            
                            summary_data = [
                                ["Metric", "Value"],
                                ["Total Manholes", str(sum(e['num_nodes'] for e in result['per_edge']))],
                                ["Total Branches", str(len(result['per_edge']))],
                                ["Total Traps", str(sum(e['num_traps'] for e in result['per_edge']))],
                                ["Total Cost (SAR)", f"{result['total_cost']:,.0f}"],
                            ]
                            
                            summary_table = Table(summary_data, colWidths=[100*mm, 100*mm])
                            summary_table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5fa8')),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black)
                            ]))
                            
                            elements.append(summary_table)
                            elements.append(Spacer(1, 15))
                            
                            items_data = [["Item", "Quantity", "Unit", "Total (SAR)"]]
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
                                ('GRID', (0, 0), (-1, -1), 1, colors.black)
                            ]))
                            
                            elements.append(items_table)
                            
                            doc.build(elements)
                            
                            pdf_buffer.seek(0)
                            
                            st.download_button(
                                label="📥 احمل التقرير PDF",
                                data=pdf_buffer.getvalue(),
                                file_name=f"تقرير_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                            
                            st.success("✅ تم إنشاء التقرير!")
                            
                        except ImportError:
                            st.warning("⚠️ مكتبة reportlab غير مثبتة")

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.9rem; padding: 20px;">
    <p>🌊 محلل شبكات السيول | الإصدار 12.0</p>
    <p>التطبيق بالعربية | التقرير بالإنجليزي | تكبير الخريطة مدعوم</p>
</div>
""", unsafe_allow_html=True)

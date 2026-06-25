import streamlit as st
import math
import json
import uuid
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import io

try:
    import folium
    from streamlit_folium import st_folium
    from folium.plugins import Draw
    FOLIUM_AVAILABLE = True
except:
    FOLIUM_AVAILABLE = False

# إعدادات الصفحة
st.set_page_config(page_title="محلل شبكات السيول", page_icon="🌊", layout="wide", initial_sidebar_state="expanded")

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
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# الثوابت
PIPE_PRICES = {
    400: 454, 500: 619, 600: 725, 700: 906, 800: 1045,
    900: 1225, 1000: 1440, 1100: 1600, 1200: 1812, 1300: 1920, 1400: 2132,
}

# دوال
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
                
                # إضافة العقد
                if start not in self.nodes_coords:
                    self.nodes_coords[start] = node_id
                    self.G.add_node(node_id)
                    node_id += 1
                
                if end not in self.nodes_coords:
                    self.nodes_coords[end] = node_id
                    self.G.add_node(node_id)
                    node_id += 1
                
                # إضافة الحافة (الفرع)
                distance = haversine_distance(coords[i], coords[i+1])
                start_node = self.nodes_coords[start]
                end_node = self.nodes_coords[end]
                
                self.G.add_edge(start_node, end_node, distance=distance)
                
                # حفظ معلومات الفرع
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
    <p>التحليل أولاً ← إدارة البيانات ← الحساب ← التقرير PDF</p>
</div>
""", unsafe_allow_html=True)

# الأقسام
tabs = st.tabs(["🏠 البداية", "🗺️ الرسم", "🌐 التحليل", "⚙️ إدارة الفروع", "💰 الحساب", "🗺️ الخريطة", "📊 التقرير"])

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 1: البداية
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[0]:
    st.markdown("<h2 class='title'>🎯 خطوات الاستخدام</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="card">
        <div style="font-size: 2rem; margin-bottom: 10px;">1️⃣</div>
        <div class="card-label"><strong>الرسم</strong><br>ارسم الخطوط على الخريطة</div>
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
        <div class="card-label"><strong>البيانات</strong><br>أدخل القطر والعمق لكل فرع</div>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="card">
        <div style="font-size: 2rem; margin-bottom: 10px;">4️⃣</div>
        <div class="card-label"><strong>الحساب</strong><br>احسب التكاليف والكميات</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
        <div style="font-size: 2rem; margin-bottom: 10px;">5️⃣</div>
        <div class="card-label"><strong>الخريطة</strong><br>عرض خريطة OpenStreetMap</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card">
        <div style="font-size: 2rem; margin-bottom: 10px;">6️⃣</div>
        <div class="card-label"><strong>التقرير</strong><br>احمل PDF مع الخريطة</div>
        </div>
        """, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 2: الرسم
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[1]:
    st.markdown("<h2 class='title'>🗺️ الرسم على الخريطة</h2>", unsafe_allow_html=True)
    
    if FOLIUM_AVAILABLE:
        m = folium.Map(location=[24.7136, 46.6753], zoom_start=12, tiles="OpenStreetMap")
        
        for line in st.session_state.lines:
            coords = line.get("coords", [])
            if coords:
                folium.PolyLine(coords, color="red", weight=3, popup=line["name"]).add_to(m)
        
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
                    }
                    st.session_state.lines.append(new_line)
                    st.session_state.analyzer = None
                    st.success(f"✅ تم إضافة {new_line['name']}")
                    st.rerun()

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
                <div class="card-label">🔴 المناهل</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="card">
                <div class="card-value">{stats['num_edges']}</div>
                <div class="card-label">🔗 الفروع</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="card">
                <div class="card-value">{stats['total_length']/1000:.1f}</div>
                <div class="card-label">📏 الطول (كم)</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.success(f"✅ عدد المناهل: {stats['num_nodes']} | الفروع: {stats['num_edges']}")

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 4: إدارة الفروع
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[3]:
    st.markdown("<h2 class='title'>⚙️ إدارة بيانات الفروع</h2>", unsafe_allow_html=True)
    
    if not st.session_state.analyzer:
        st.warning("⚠️ حلل الشبكة أولاً")
    else:
        st.info("📌 أدخل القطر والعمق لكل فرع")
        
        # جدول الفروع
        edges_data = []
        
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
            
            with col5:
                st.write(f"💾 تم الحفظ")
            
            st.session_state.analyzer.edges_list[idx]["diameter"] = diameter
            st.session_state.analyzer.edges_list[idx]["depth"] = depth

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 5: الحساب
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[4]:
    st.markdown("<h2 class='title'>💰 حساب التكاليف</h2>", unsafe_allow_html=True)
    
    if not st.session_state.analyzer:
        st.warning("⚠️ أدخل البيانات أولاً")
    else:
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
                        
                        # حصة هذا الفرع من المناهل
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
            
            # جدول الكميات
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
# التبويب 6: الخريطة
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[5]:
    st.markdown("<h2 class='title'>🗺️ خريطة الشبكة (OpenStreetMap)</h2>", unsafe_allow_html=True)
    
    if not st.session_state.analyzer:
        st.warning("⚠️ حلل الشبكة أولاً")
    else:
        analyzer = st.session_state.analyzer
        
        map_osm = folium.Map(location=[24.7136, 46.6753], zoom_start=12, tiles="OpenStreetMap")
        
        # رسم الخطوط
        for line in st.session_state.lines:
            coords = line.get("coords", [])
            if coords:
                folium.PolyLine(coords, color="blue", weight=3, opacity=0.8, popup=line['name']).add_to(map_osm)
        
        # رسم المناهل
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
        
        st_folium(map_osm, width=None, height=600)

# ═════════════════════════════════════════════════════════════════════════════════
# التبويب 7: التقرير PDF
# ═════════════════════════════════════════════════════════════════════════════════

with tabs[6]:
    st.markdown("<h2 class='title'>📊 تقرير PDF مع الخريطة</h2>", unsafe_allow_html=True)
    
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
                    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
                    from reportlab.lib.units import mm
                    
                    result = st.session_state.cost_result
                    
                    # إنشاء خريطة
                    map_osm = folium.Map(location=[24.7136, 46.6753], zoom_start=12, tiles="OpenStreetMap")
                    
                    for line in st.session_state.lines:
                        coords = line.get("coords", [])
                        if coords:
                            folium.PolyLine(coords, color="blue", weight=3).add_to(map_osm)
                    
                    map_file = "/tmp/map.html"
                    map_osm.save(map_file)
                    
                    # إنشاء PDF
                    pdf_buffer = io.BytesIO()
                    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
                    
                    elements = []
                    styles = getSampleStyleSheet()
                    
                    # العنوان
                    title = Paragraph("تقرير تحليل شبكة السيول", styles['Heading1'])
                    elements.append(title)
                    elements.append(Spacer(1, 12))
                    
                    # التاريخ
                    date_text = Paragraph(f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal'])
                    elements.append(date_text)
                    elements.append(Spacer(1, 12))
                    
                    # ملخص
                    summary_data = [
                        ["المؤشر", "القيمة"],
                        ["المناهل", str(sum(e['num_nodes'] for e in result['per_edge']))],
                        ["الفروع", str(len(result['per_edge']))],
                        ["المصائد", str(sum(e['num_traps'] for e in result['per_edge']))],
                        ["التكلفة الإجمالية (ريال)", f"{result['total_cost']:,.0f}"],
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
                    
                    # جدول الكميات
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
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    
                    elements.append(items_table)
                    
                    # بناء PDF
                    doc.build(elements)
                    
                    pdf_buffer.seek(0)
                    
                    st.download_button(
                        label="📥 تحميل PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.success("✅ تم إنشاء التقرير!")
                    
                except ImportError:
                    st.warning("⚠️ مكتبة reportlab غير مثبتة. استخدم CSV بدلاً من ذلك")
                    
                    # بديل CSV
                    csv_content = "البند,الكمية,الوحدة,الإجمالي\n"
                    for item_name, item_data in result["all_items"].items():
                        csv_content += f"{item_name},{item_data['الكمية']:.2f},{item_data['الوحدة']},{item_data['الإجمالي']:.0f}\n"
                    
                    st.download_button(
                        label="📥 تحميل CSV",
                        data=csv_content,
                        file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.9rem; padding: 20px;">
    <p>🌊 محلل شبكات السيول | النسخة 10.0 - تحليل شامل مع PDF وخريطة OpenStreetMap</p>
</div>
""", unsafe_allow_html=True)

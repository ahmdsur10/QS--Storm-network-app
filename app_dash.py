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
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

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
# إعداد الصفحة
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="محلل شبكات السيول - نظام تحليل وتصميم الصرف الصحي",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"About": None},
)

# ─────────────────────────────────────────────────────────────────────────────
# 🔧 تهيئة متغيرات Session State
# ─────────────────────────────────────────────────────────────────────────────
if "cost" not in st.session_state:
    st.session_state.cost = None

if "analyzer" not in st.session_state:
    st.session_state.analyzer = None

if "lines" not in st.session_state:
    st.session_state.lines = []

if "pipe_count" not in st.session_state:
    st.session_state.pipe_count = 0

if "map_type" not in st.session_state:
    st.session_state.map_type = "OpenStreetMap"

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

.info-banner {
    background: #e8f4fd;
    border-right: 4px solid #1a5fa8;
    padding: 12px 14px;
    border-radius: 6px;
    font-size: 0.9rem;
    color: #0a2a5e;
    margin: 12px 0;
    font-weight: 600;
}

.total-row {
    background: linear-gradient(135deg, #0a2a5e 0%, #1a5fa8 100%);
    color: white;
    padding: 14px 16px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 1.05rem;
    margin: 18px 0 12px 0;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ثوابت التسعير
# ─────────────────────────────────────────────────────────────────────────────
PIPE_PRICES = {
    200: 185,
    250: 220,
    300: 265,
    350: 310,
    400: 360,
    500: 470,
    600: 580,
    700: 690,
    800: 800,
    900: 910,
    1000: 1020,
    1200: 1250,
}

EXCAVATION = 85
MANHOLE_PRICE = 4500
TRAP_PRICE = 2500
BACKFILL_PRICE = 95

def num_traps(length):
    """حساب عدد مصائد الأمطار = الطول / 35"""
    return max(1, round(length / 35))

# ─────────────────────────────────────────────────────────────────────────────
# فئة تحليل الشبكة
# ─────────────────────────────────────────────────────────────────────────────
class NetworkAnalyzer:
    def __init__(self, lines):
        self.lines = lines
        self.graph = nx.DiGraph()
        self._build_network()
    
    def _build_network(self):
        for line in self.lines:
            start = tuple(line["start_coord"])
            end = tuple(line["end_coord"])
            self.graph.add_edge(start, end, data=line)
    
    def stats(self):
        num_nodes = self.graph.number_of_nodes()
        total_length = sum(
            math.sqrt((line["end_coord"][0] - line["start_coord"][0])**2 + 
                     (line["end_coord"][1] - line["start_coord"][1])**2)
            for line in self.lines
        )
        return {
            "nodes": num_nodes,
            "edges": len(self.lines),
            "length": total_length
        }
    
    @property
    def edges_list(self):
        return [
            {
                "line_name": line["name"],
                "diameter": line.get("diameter", 600),
                "depth": line.get("depth", 1.5),
                "distance": math.sqrt(
                    (line["end_coord"][0] - line["start_coord"][0])**2 + 
                    (line["end_coord"][1] - line["start_coord"][1])**2
                ),
                "start_coord": line["start_coord"],
                "end_coord": line["end_coord"]
            }
            for line in self.lines
        ]

# ─────────────────────────────────────────────────────────────────────────────
# رأس الصفحة
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🌊 نظام تحليل شبكات السيول</h1>
    <p>نظام ذكي لتحليل شبكات الأودية والسيول وحساب التكاليف والكميات</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# التبويبات
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 إدخال البيانات والتصميم", "🗺️ الخريطة والتصور", "💰 تحليل التكاليف", "📄 التقرير"])

# ─────────────────────────────────────────────────────────────────────────────
# التبويب 1: إدخال البيانات
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 📥 إدخال بيانات شبكة السيول")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info("✏️ أدخل كل جزء من أجزاء قنوات السيول مع مواصفاته. سيتم ترقيم القنوات تلقائياً (قناة1، قناة2، إلخ)")
    
    with col2:
        if st.button("➕ إضافة قناة جديدة", use_container_width=True):
            st.session_state.pipe_count += 1
            st.session_state.lines = []
            st.rerun()
    
    # عرض نموذج إدخال لكل قناة
    num_pipes = st.session_state.pipe_count
    
    if num_pipes == 0:
        st.warning("👈 اضغط على 'إضافة قناة جديدة' للبدء")
    else:
        for i in range(num_pipes):
            with st.expander(f"🔧 قناة{i+1} - المواصفات", expanded=(i == num_pipes - 1)):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    start_lat = st.number_input(
                        f"دائرة العرض (البداية)", 
                        value=24.7136 + i * 0.001,
                        format="%.6f",
                        key=f"start_lat_{i}"
                    )
                
                with col2:
                    start_lng = st.number_input(
                        f"خط الطول (البداية)",
                        value=46.6753 + i * 0.001,
                        format="%.6f",
                        key=f"start_lng_{i}"
                    )
                
                with col3:
                    end_lat = st.number_input(
                        f"دائرة العرض (النهاية)",
                        value=24.7140 + i * 0.001,
                        format="%.6f",
                        key=f"end_lat_{i}"
                    )
                
                with col4:
                    end_lng = st.number_input(
                        f"خط الطول (النهاية)",
                        value=46.6760 + i * 0.001,
                        format="%.6f",
                        key=f"end_lng_{i}"
                    )
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    diameter = st.selectbox(
                        "عرض القناة (سم)",
                        options=sorted(PIPE_PRICES.keys()),
                        key=f"diameter_{i}"
                    )
                
                with col2:
                    depth = st.number_input(
                        "عمق القناة (متر)",
                        min_value=0.5,
                        max_value=12.0,
                        value=1.5,
                        step=0.1,
                        key=f"depth_{i}"
                    )
                
                with col3:
                    num_nodes = st.number_input(
                        "عدد نقاط التفتيش",
                        min_value=1,
                        max_value=50,
                        value=2,
                        step=1,
                        key=f"num_nodes_{i}"
                    )
                
                # حفظ البيانات
                if i < len(st.session_state.lines):
                    st.session_state.lines[i] = {
                        "id": i,
                        "name": f"قناة{i+1}",
                        "start_coord": (start_lat, start_lng),
                        "end_coord": (end_lat, end_lng),
                        "diameter": diameter,
                        "depth": depth,
                        "num_nodes": num_nodes
                    }
                else:
                    st.session_state.lines.append({
                        "id": i,
                        "name": f"قناة{i+1}",
                        "start_coord": (start_lat, start_lng),
                        "end_coord": (end_lat, end_lng),
                        "diameter": diameter,
                        "depth": depth,
                        "num_nodes": num_nodes
                    })
        
        # زر إزالة آخر قناة
        if num_pipes > 0:
            col1, col2 = st.columns([5, 1])
            with col2:
                if st.button("➖ حذف آخر قناة", use_container_width=True):
                    st.session_state.pipe_count -= 1
                    st.session_state.lines.pop()
                    st.session_state.cost = None
                    st.rerun()
    
    # زر الحساب
    if num_pipes > 0:
        if st.button("🧮 حساب التكاليف والتحليل", use_container_width=True, type="primary"):
            st.session_state.analyzer = NetworkAnalyzer(st.session_state.lines)
            
            analyzer = st.session_state.analyzer
            stats = analyzer.stats()
            
            # حساب التكاليف
            all_items = {}
            per_edge = []
            total_cost = 0
            
            for edge in analyzer.edges_list:
                d = edge["diameter"]
                dep = edge["depth"]
                L = edge["distance"]
                n_mh = edge.get("num_nodes", 2)
                n_tr = num_traps(L)
                p_pipe = PIPE_PRICES.get(d, 725)
                
                items = [
                    {"البند": "قنوات خرسانية مدعمة", "الكمية": L, "الوحدة": "متر طولي", "السعر": p_pipe, "الإجمالي": L * p_pipe},
                    {"البند": "أعمال الحفر والخنادق", "الكمية": L, "الوحدة": "متر طولي", "السعر": EXCAVATION, "الإجمالي": L * EXCAVATION},
                    {"البند": "نقاط تفتيش خرسانية", "الكمية": n_mh, "الوحدة": "عدد", "السعر": MANHOLE_PRICE, "الإجمالي": n_mh * MANHOLE_PRICE},
                    {"البند": "فتحات التصريف والفلاتر", "الكمية": n_tr, "الوحدة": "عدد", "السعر": TRAP_PRICE, "الإجمالي": n_tr * TRAP_PRICE},
                    {"البند": "أعمال الردم والدمك", "الكمية": L * dep, "الوحدة": "متر مكعب", "السعر": BACKFILL_PRICE, "الإجمالي": L * dep * BACKFILL_PRICE},
                ]
                
                edge_total = sum(it["الإجمالي"] for it in items)
                per_edge.append({
                    "line_name": edge["line_name"],
                    "diameter": d,
                    "depth": dep,
                    "length": L,
                    "items": items,
                    "total": edge_total,
                    "n_manholes": n_mh,
                    "n_traps": n_tr,
                    "start_coord": edge["start_coord"],
                    "end_coord": edge["end_coord"]
                })
                total_cost += edge_total
            
            st.session_state.cost = {
                "per_edge": per_edge,
                "total_cost": total_cost,
                "all_items": all_items
            }
            st.success("✅ تم الحساب بنجاح!")
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# التبويب 2: الخريطة
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 🗺️ تصور الشبكة على الخريطة")
    
    # خيار اختيار نوع الخريطة
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("🗺️ اختر نوع الخريطة المفضلة لديك")
    with col2:
        map_type = st.selectbox(
            "نوع الخريطة",
            options=["OpenStreetMap", "Satellite", "Terrain"],
            index=0 if st.session_state.map_type == "OpenStreetMap" else (1 if st.session_state.map_type == "Satellite" else 2),
            key="map_type_selector"
        )
        st.session_state.map_type = map_type
    
    if st.session_state.lines:
        # خريطة Folium
        center_lat = sum(line["start_coord"][0] for line in st.session_state.lines) / len(st.session_state.lines)
        center_lng = sum(line["start_coord"][1] for line in st.session_state.lines) / len(st.session_state.lines)
        
        # اختيار نوع الخريطة
        map_tiles = {
            "OpenStreetMap": "OpenStreetMap",
            "Satellite": "OpenTopoMap",
            "Terrain": "Stamen Terrain"
        }
        
        selected_tiles = map_tiles.get(st.session_state.map_type, "OpenStreetMap")
        
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=13,
            tiles=selected_tiles
        )
        
        colors_list = ["red", "blue", "green", "purple", "orange", "darkred", "darkblue", "darkgreen"]
        
        for idx, line in enumerate(st.session_state.lines):
            color = colors_list[idx % len(colors_list)]
            
            # رسم الخط
            folium.PolyLine(
                locations=[line["start_coord"], line["end_coord"]],
                color=color,
                weight=3,
                opacity=0.8,
                popup=f"{line['name']}<br>عرض القناة: {line.get('diameter', 600)}سم<br>العمق: {line.get('depth', 1.5)}متر"
            ).add_to(m)
            
            # نقاط البداية والنهاية
            folium.CircleMarker(
                location=line["start_coord"],
                radius=8,
                color=color,
                fill=True,
                fillColor=color,
                popup=f"{line['name']} - البداية",
                tooltip=f"{line['name']} البداية"
            ).add_to(m)
            
            folium.CircleMarker(
                location=line["end_coord"],
                radius=8,
                color=color,
                fill=True,
                fillColor=color,
                popup=f"{line['name']} - النهاية",
                tooltip=f"{line['name']} النهاية"
            ).add_to(m)
        
        st_folium(m, width=1400, height=600)
    else:
        st.info("📍 أضف أنابيب لرؤية الشبكة على الخريطة")

# ─────────────────────────────────────────────────────────────────────────────
# التبويب 3: تحليل التكاليف
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 💰 تحليل التكاليف والمواصفات")
    
    if st.session_state.cost:
        result = st.session_state.cost
        
        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        t_mh = sum(e["n_manholes"] for e in result["per_edge"])
        t_tr = sum(e["n_traps"] for e in result["per_edge"])
        
        k1.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(result["per_edge"])}</div><div class="kpi-label">إجمالي القنوات</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi-card"><div class="kpi-value">{t_mh}</div><div class="kpi-label">إجمالي نقاط التفتيش</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi-card"><div class="kpi-value">{t_tr}</div><div class="kpi-label">فتحات التصريف</div></div>', unsafe_allow_html=True)
        k4.markdown(f'<div class="kpi-card"><div class="kpi-value">ر.س {result["total_cost"]:,.0f}</div><div class="kpi-label">إجمالي التكلفة المتوقعة</div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # جدول الكميات الإجمالية
        st.subheader("📊 ملخص الكميات والتكاليف")
        
        summary_data = []
        for edge in result["per_edge"]:
            summary_data.append({
                "القناة": edge["line_name"],
                "العرض (سم)": edge["diameter"],
                "العمق (متر)": f"{edge['depth']:.2f}",
                "الطول (متر)": f"{edge['length']:.2f}",
                "نقاط التفتيش": edge["n_manholes"],
                "الفتحات": edge["n_traps"],
                "التكلفة (ر.س)": f"{edge['total']:,.0f}"
            })
        
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
        
        st.markdown(f'<div class="total-row">💰 إجمالي التكلفة المتوقعة: ر.س {result["total_cost"]:,.0f}</div>', unsafe_allow_html=True)
        
        # تفاصيل كل قناة
        st.markdown("---")
        st.subheader("🔍 التفاصيل الكاملة لكل قناة")
        
        for edge_idx, e in enumerate(result["per_edge"]):
            with st.expander(f"📌 {e['line_name']} - الطول: {e['length']:.1f} متر", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("العرض", f"{e['diameter']} سم")
                
                with col2:
                    st.metric("العمق", f"{e['depth']} متر")
                
                with col3:
                    st.metric("إجمالي التكلفة", f"ر.س {e['total']:,.0f}")
                
                # جدول العناصر
                items_data = []
                for it in e["items"]:
                    items_data.append({
                        "البند": it["البند"],
                        "الكمية": f"{it['الكمية']:.2f}",
                        "الوحدة": it["الوحدة"],
                        "سعر الوحدة (ر.س)": f"{it['السعر']:,.0f}",
                        "الإجمالي (ر.س)": f"{it['الإجمالي']:,.0f}"
                    })
                
                df_items = pd.DataFrame(items_data)
                st.dataframe(df_items, use_container_width=True, hide_index=True)
    else:
        st.info("💡 اضغط على 'حساب التكاليف والتحليل' في تبويب إدخال البيانات لرؤية التحليل")

# ─────────────────────────────────────────────────────────────────────────────
# التبويب 4: التقرير PDF (بالإنجليزية فقط)
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 📄 التقرير (بصيغة PDF)")
    
    if st.session_state.cost:
        result = st.session_state.cost
        analyzer = st.session_state.analyzer
        stats = analyzer.stats()
        
        def create_pdf_report():
            buffer = io.BytesIO()
            pdf = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35)
            elements = []
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#0a2a5e'),
                spaceAfter=12,
                spaceBefore=0,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#1a5fa8'),
                spaceAfter=8,
                spaceBefore=6,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=3,
                spaceBefore=0,
                fontName='Helvetica'
            )
            
            # Title
            elements.append(Paragraph("WADI & STORMWATER NETWORK ANALYSIS & COST ESTIMATION REPORT", title_style))
            elements.append(Spacer(1, 0.15*inch))
            
            # Project Information
            elements.append(Paragraph("PROJECT INFORMATION", heading_style))
            elements.append(Spacer(1, 0.05*inch))
            
            info_data = [
                ["Report Date:", datetime.now().strftime("%Y-%m-%d")],
                ["Total Channels:", str(len(st.session_state.lines))],
                ["Total Network Length:", f"{stats['length']:.2f} m"],
                ["Total Inspection Points:", str(stats['nodes'])],
                ["Total Estimated Cost:", f"SAR {result['total_cost']:,.0f}"]
            ]
            
            info_table = Table(info_data, colWidths=[2.2*inch, 3.0*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4fd')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 0.15*inch))
            
            # Pipe Details
            elements.append(Paragraph("CHANNEL SPECIFICATIONS & QUANTITIES", heading_style))
            elements.append(Spacer(1, 0.05*inch))
            
            for edge in result["per_edge"]:
                pipe_data = [
                    ["Channel Name:", edge["line_name"]],
                    ["Width:", f"{edge['diameter']} cm"],
                    ["Depth:", f"{edge['depth']:.2f} m"],
                    ["Channel Length:", f"{edge['length']:.2f} m"],
                    ["Number of Inspection Points:", str(edge["n_manholes"])],
                    ["Number of Drainage Outlets:", str(edge["n_traps"])],
                    ["Total Cost:", f"SAR {edge['total']:,.0f}"]
                ]
                
                pipe_table = Table(pipe_data, colWidths=[2.2*inch, 3.0*inch])
                pipe_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#d0e4f7')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]))
                elements.append(pipe_table)
                elements.append(Spacer(1, 0.08*inch))
            
            elements.append(Spacer(1, 0.1*inch))
            
            # Cost Summary
            elements.append(Paragraph("COST SUMMARY", heading_style))
            elements.append(Spacer(1, 0.05*inch))
            
            cost_data = [["Item", "Qty", "Unit", "Unit Price", "Total"]]
            
            # جمع جميع العناصر
            item_totals = {}
            for edge in result["per_edge"]:
                for item in edge["items"]:
                    item_name = item["البند"]
                    if item_name not in item_totals:
                        item_totals[item_name] = {
                            "quantity": 0,
                            "unit": item["الوحدة"],
                            "price": item["السعر"],
                            "total": 0
                        }
                    item_totals[item_name]["quantity"] += item["الكمية"]
                    item_totals[item_name]["total"] += item["الإجمالي"]
            
            for item_name, data in item_totals.items():
                cost_data.append([
                    item_name,
                    f"{data['quantity']:.1f}",
                    data["unit"],
                    f"{data['price']:,.0f}",
                    f"{data['total']:,.0f}"
                ])
            
            cost_data.append(["", "", "", "TOTAL:", f"{result['total_cost']:,.0f}"])
            
            cost_table = Table(cost_data, colWidths=[2.0*inch, 0.65*inch, 0.55*inch, 1.0*inch, 1.2*inch])
            cost_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0a2a5e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#1a5fa8')),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('TOPPADDING', (0, -1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
            ]))
            elements.append(cost_table)
            
            # Footer
            elements.append(Spacer(1, 0.15*inch))
            elements.append(Paragraph("_" * 60, normal_style))
            elements.append(Spacer(1, 0.05*inch))
            elements.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
            elements.append(Paragraph("© Storm Network Analysis System", normal_style))
            
            pdf.build(elements)
            buffer.seek(0)
            return buffer
        
        pdf_buffer = create_pdf_report()
        
        st.download_button(
            label="📥 تنزيل التقرير بصيغة PDF",
            data=pdf_buffer,
            file_name=f"Drainage_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        st.success("✅ التقرير جاهز للتنزيل")
    else:
        st.info("💡 أكمل التحليل في تبويب إدخال البيانات لتوليد التقرير")

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""<div style="text-align:center;color:#9aa4b8;font-size:0.85rem;padding:16px 0">
🌊 نظام تحليل شبكات السيول - حلول هندسية متقدمة لتصميم الأودية والسيول
</div>""", unsafe_allow_html=True)

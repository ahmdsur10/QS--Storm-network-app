import streamlit as st
import math
import os
import io
import json
import zipfile
import uuid
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import folium
    from streamlit_folium import st_folium
    from folium.plugins import Draw
    FOLIUM_AVAILABLE = True
except ModuleNotFoundError:
    FOLIUM_AVAILABLE = False

try:
    import shapefile
    SHAPEFILE_AVAILABLE = True
except ModuleNotFoundError:
    SHAPEFILE_AVAILABLE = False

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ModuleNotFoundError:
    GEOPANDAS_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import mm, inch
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, 
        PageBreak, Image as RLImage
    )
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import arabic_reshaper
    from bidi.algorithm import get_display
    PDF_AVAILABLE = True
except ModuleNotFoundError:
    PDF_AVAILABLE = False

st.set_page_config(
    page_title="حاسبة شبكات السيول - متقدمة", 
    page_icon="🌊",
    layout="wide", 
    initial_sidebar_state="collapsed",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

PIPE_PRICES = {
    400: 454, 500: 619, 600: 725, 700: 906, 800: 1045,
    900: 1225, 1000: 1440, 1100: 1600, 1200: 1812, 1300: 1920, 1400: 2132,
}

LINE_COLORS = ["#FF0000", "#0a7d34", "#e8a93a", "#7a1fa8", "#1a5fa8", "#c2185b", "#00838f", "#5d4037"]

MAIN_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
*{box-sizing:border-box}
html,body,[class*="css"],.stApp{font-family:'Cairo',sans-serif!important;direction:rtl;-webkit-text-size-adjust:100%}
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stToolbarActions"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"],#MainMenu,footer,footer *,.stToolbar
{display:none!important;visibility:hidden!important;height:0!important;overflow:hidden!important;pointer-events:none!important}

.block-container{padding:0.5rem 0.6rem 2rem!important;max-width:1400px!important;margin:0 auto!important}
.hdr{background:linear-gradient(135deg,#0a2a5e,#1a5fa8);color:#fff;padding:12px 14px;border-radius:12px;
  margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px}
.hdr h1{margin:0;font-size:1rem;font-weight:900;line-height:1.4}
.section-title{color:#0a2a5e;font-size:.92rem;font-weight:900;margin:14px 0 8px;
  border-bottom:2px solid #1a5fa8;padding-bottom:4px}
.mc{background:#fff;border-radius:10px;padding:10px 8px;box-shadow:0 2px 8px rgba(0,0,0,.08);
  border-top:3px solid #1a5fa8;text-align:center;margin-bottom:6px}
.mc .v{font-size:1.1rem;font-weight:900;color:#0a2a5e;word-break:break-word}
.mc .l{font-size:.68rem;color:#6b7a99;margin-top:2px}
.stButton>button{background:linear-gradient(135deg,#1a5fa8,#0a2a5e)!important;color:#fff!important;
  border:none!important;border-radius:10px!important;font-family:'Cairo',sans-serif!important;
  font-weight:700!important;font-size:.95rem!important;padding:13px 8px!important;min-height:48px!important;width:100%!important}
.cost-table{width:100%;border-collapse:collapse;font-size:0.82rem;direction:rtl;margin:10px 0;
  display:block;overflow-x:auto;white-space:nowrap}
.cost-table th,.cost-table td{padding:8px;border:1px solid #d0e4f7;text-align:right}
.cost-table th{background:#eaf4ff;color:#0a2a5e;font-weight:700}
.cost-table tr:nth-child(even){background:#f8fbfe}
.cost-table .total{background:#0a2a5e;color:#fff;font-weight:700}
.success-box{background:#d4edda;border:1px solid #c3e6cb;padding:10px;border-radius:5px;margin:10px 0;color:#155724}
.warning-box{background:#fff3cd;border:1px solid #ffeaa7;padding:10px;border-radius:5px;margin:10px 0;color:#856404}
</style>"""

# ═════════════════════════════════════════════════════════════════════════════════
# دوال تحليل الشبكة المتقدمة
# ═════════════════════════════════════════════════════════════════════════════════

def build_network_from_lines(lines):
    """بناء شبكة NetworkX من الخطوط مع حساب المناهل الفعلية"""
    G = nx.Graph()
    line_details = {}
    
    for idx, line in enumerate(lines):
        if not line.get("selected", True):
            continue
            
        coords = line.get("coords", [])
        if len(coords) < 2:
            continue
        
        line_nodes = []
        line_edges = []
        
        # إضافة الحواف والعقد
        for i in range(len(coords) - 1):
            start = tuple(coords[i])
            end = tuple(coords[i + 1])
            
            # إضافة العقد
            start_node = f"node_{idx}_{i}"
            end_node = f"node_{idx}_{i+1}"
            
            G.add_node(start_node, position=start, line_idx=idx, coord=start)
            G.add_node(end_node, position=end, line_idx=idx, coord=end)
            
            # إضافة الحافة
            distance = calculate_haversine_distance(coords[i], coords[i+1])
            G.add_edge(start_node, end_node, weight=distance, line_idx=idx, distance=distance)
            
            line_nodes.extend([start_node, end_node])
            line_edges.append((start_node, end_node))
        
        line_details[idx] = {
            "name": line.get("name", f"الخط {idx+1}"),
            "nodes": list(set(line_nodes)),
            "edges": line_edges,
            "length": line.get("length", 0),
            "diameter": line.get("diameter", 600),
        }
    
    return G, line_details

def calculate_haversine_distance(coord1, coord2):
    """حساب المسافة بين نقطتين بـ Haversine Formula"""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6_371_000  # متر
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def count_actual_manholes(G, line_details):
    """حساب عدد المناهل الفعلية من الشبكة"""
    total_nodes = len(G.nodes())
    return total_nodes

def calculate_network_stats(G, line_details):
    """حساب إحصائيات الشبكة"""
    if G.number_of_nodes() == 0:
        return None
    
    stats = {
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "total_length": sum(data.get('distance', 0) for _, _, data in G.edges(data=True)),
        "num_components": nx.number_connected_components(G),
        "is_connected": nx.is_connected(G),
        "density": nx.density(G),
        "avg_degree": sum(dict(G.degree()).values()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
        "line_details": line_details,
    }
    return stats

def generate_cost_from_network(lines, network_stats):
    """حساب التكاليف بناءً على إحصائيات الشبكة الفعلية"""
    if not network_stats:
        return None
    
    # عدد المناهل من الشبكة الفعلية
    num_manholes = network_stats["num_nodes"]
    
    per_line = []
    all_items = {}
    
    for idx, line in enumerate(lines):
        if not line.get("selected", True):
            continue
        
        diameter = line.get("diameter", 600)
        depth = line.get("depth", 1.5)
        length = line.get("length", 0)
        price_per_meter = PIPE_PRICES.get(diameter, 725)
        
        # عدد المصائد = كل 150 متر
        num_traps = max(1, int(length / 150))
        
        # عدد المناهل في هذا الخط من الشبكة
        line_nodes = network_stats["line_details"].get(idx, {}).get("nodes", [])
        line_manholes = len(line_nodes)
        
        # البنود
        items = [
            {"name": "أنابيب صرف", "qty": length, "unit": "م", "price": price_per_meter, "total": length * price_per_meter},
            {"name": "حفر (بناء الأساس)", "qty": length, "unit": "م", "price": 50, "total": length * 50},
            {"name": "مناهل", "qty": line_manholes, "unit": "عدد", "price": 3000, "total": line_manholes * 3000},
            {"name": "مصائد", "qty": num_traps, "unit": "عدد", "price": 2000, "total": num_traps * 2000},
            {"name": "ردم وتسوية", "qty": length * depth, "unit": "م³", "price": 30, "total": length * depth * 30},
        ]
        
        total = sum(item["total"] for item in items)
        
        per_line.append({
            "line": line,
            "manholes": line_manholes,
            "traps": num_traps,
            "items": items,
            "total": total,
        })
        
        # جمع البنود
        for item in items:
            key = item["name"]
            if key not in all_items:
                all_items[key] = {"qty": 0, "total": 0, "unit": item["unit"], "price": item["price"]}
            all_items[key]["qty"] += item["qty"]
            all_items[key]["total"] += item["total"]
    
    grand_total = sum(item["total"] for item in all_items.values())
    merged_items = [{"name": name, **data} for name, data in all_items.items()]
    
    total_traps = sum(item["traps"] for item in per_line)
    
    return {
        "per_line": per_line,
        "merged_items": merged_items,
        "grand_total": grand_total,
        "total_manholes": num_manholes,
        "total_traps": total_traps,
        "network_stats": network_stats,
    }

def load_geojson_lines(geojson_data):
    """تحميل خطوط من ملف GeoJSON"""
    lines = []
    try:
        features = geojson_data.get("features", [])
        for idx, feature in enumerate(features):
            geom = feature.get("geometry", {})
            if geom.get("type") == "LineString":
                coords = [(lat, lon) for lon, lat in geom.get("coordinates", [])]
                if len(coords) >= 2:
                    length = sum(calculate_haversine_distance(coords[i], coords[i+1]) 
                               for i in range(len(coords)-1))
                    
                    line = {
                        "id": str(uuid.uuid4()),
                        "name": feature.get("properties", {}).get("name", f"GeoJSON خط {idx+1}"),
                        "length": length,
                        "coords": coords,
                        "source": "GeoJSON",
                        "selected": True,
                        "diameter": 600,
                        "depth": 1.5,
                        "traps_mode": "تلقائي",
                        "traps_value": max(1, int(length / 150)),
                        "manholes_mode": "تلقائي",
                        "manholes_value": max(2, int(length / 120) + 1),
                    }
                    lines.append(line)
    except Exception as e:
        st.error(f"خطأ في تحميل GeoJSON: {e}")
    
    return lines

def load_shapefile_lines(shp_file):
    """تحميل خطوط من ملف Shapefile"""
    lines = []
    try:
        if GEOPANDAS_AVAILABLE:
            gdf = gpd.read_file(shp_file)
            for idx, row in gdf.iterrows():
                geom = row.geometry
                if geom.geom_type == "LineString":
                    coords = [(lat, lon) for lon, lat in geom.coords]
                    if len(coords) >= 2:
                        length = sum(calculate_haversine_distance(coords[i], coords[i+1]) 
                                   for i in range(len(coords)-1))
                        
                        line = {
                            "id": str(uuid.uuid4()),
                            "name": row.get("name", f"Shapefile خط {idx+1}") if "name" in row else f"Shapefile خط {idx+1}",
                            "length": length,
                            "coords": coords,
                            "source": "Shapefile",
                            "selected": True,
                            "diameter": 600,
                            "depth": 1.5,
                            "traps_mode": "تلقائي",
                            "traps_value": max(1, int(length / 150)),
                            "manholes_mode": "تلقائي",
                            "manholes_value": max(2, int(length / 120) + 1),
                        }
                        lines.append(line)
        else:
            st.warning("⚠️ مكتبة geopandas غير متوفرة. استخدم GeoJSON بدلاً منها.")
    except Exception as e:
        st.error(f"خطأ في تحميل Shapefile: {e}")
    
    return lines

def generate_pdf_report(combined_result, lines, network_stats):
    """إنشاء تقرير PDF شامل"""
    if not PDF_AVAILABLE:
        return None
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        
        styles = getSampleStyleSheet()
        story = []
        
        # العنوان
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor('#0a2a5e'),
            spaceAfter=12,
            alignment=TA_CENTER,
        )
        
        story.append(Paragraph("تقرير شبكة صرف السيول", title_style))
        story.append(Paragraph(f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # ملخص المشروع
        story.append(Paragraph("📊 ملخص المشروع", styles['Heading2']))
        
        summary_data = [
            ["المؤشر", "القيمة"],
            ["عدد الخطوط", str(len(combined_result["per_line"]))],
            ["الطول الإجمالي (متر)", f"{sum(pl['line'].get('length', 0) for pl in combined_result['per_line']):,.0f}"],
            ["عدد المناهل", str(combined_result["total_manholes"])],
            ["عدد المصائد", str(combined_result["total_traps"])],
            ["التكلفة الإجمالية (ريال)", f"{combined_result['grand_total']:,.0f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[200, 200])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5fa8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 12))
        
        # تفاصيل كل خط
        story.append(PageBreak())
        story.append(Paragraph("📋 تفاصيل الخطوط", styles['Heading2']))
        
        for idx, pl in enumerate(combined_result["per_line"]):
            ln = pl["line"]
            story.append(Paragraph(f"{ln['name']} - {ln['length']:,.0f} م", styles['Heading3']))
            
            line_data = [
                ["المواصفة", "القيمة"],
                ["القطر (ملم)", str(ln.get("diameter", 600))],
                ["العمق (متر)", f"{ln.get('depth', 1.5):.2f}"],
                ["عدد المناهل", str(pl.get("manholes", 0))],
                ["عدد المصائد", str(pl.get("traps", 0))],
            ]
            
            line_table = Table(line_data, colWidths=[200, 200])
            line_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0a7d34')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(line_table)
            story.append(Spacer(1, 6))
            
            # جدول البنود
            items_data = [["البند", "الكمية", "السعر", "الإجمالي"]]
            for item in pl.get("items", []):
                items_data.append([
                    item["name"],
                    f"{item['qty']:,.2f} {item['unit']}",
                    f"{item['price']:,.0f}",
                    f"{item['total']:,.0f}",
                ])
            
            items_data.append(["الإجمالي", "", "", f"{pl['total']:,.0f}"])
            
            items_table = Table(items_data, colWidths=[150, 100, 100, 100])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf4ff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0a2a5e')),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#0a2a5e')),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ]))
            story.append(items_table)
            story.append(Spacer(1, 12))
        
        # جدول الكميات المجمعة
        story.append(PageBreak())
        story.append(Paragraph("📦 الكميات المجمعة", styles['Heading2']))
        
        merged_data = [["البند", "الكمية", "الوحدة", "السعر", "الإجمالي"]]
        for item in combined_result.get("merged_items", []):
            avg_price = item["total"] / item["qty"] if item["qty"] > 0 else 0
            merged_data.append([
                item["name"],
                f"{item['qty']:,.2f}",
                item["unit"],
                f"{avg_price:,.0f}",
                f"{item['total']:,.0f}",
            ])
        
        merged_table = Table(merged_data, colWidths=[150, 80, 60, 80, 80])
        merged_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5fa8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(merged_table)
        
        # إحصائيات الشبكة
        story.append(Spacer(1, 12))
        story.append(Paragraph("🌐 إحصائيات الشبكة", styles['Heading2']))
        
        if network_stats:
            network_data = [
                ["المؤشر", "القيمة"],
                ["عدد المناهل (Nodes)", str(network_stats["num_nodes"])],
                ["عدد الأنابيب (Edges)", str(network_stats["num_edges"])],
                ["الطول الإجمالي (كم)", f"{network_stats['total_length']/1000:.2f}"],
                ["كثافة الشبكة", f"{network_stats['density']:.4f}"],
                ["متصلة تماماً", "نعم" if network_stats["is_connected"] else "لا"],
            ]
            
            network_table = Table(network_data, colWidths=[200, 200])
            network_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7a1fa8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(network_table)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    except Exception as e:
        st.error(f"خطأ في إنشاء التقرير: {e}")
        return None

# ═════════════════════════════════════════════════════════════════════════════════
# Initialize Session State
# ═════════════════════════════════════════════════════════════════════════════════

if "network_lines" not in st.session_state:
    st.session_state["network_lines"] = []
if "combined_result" not in st.session_state:
    st.session_state["combined_result"] = None
if "network_stats" not in st.session_state:
    st.session_state["network_stats"] = None
if "last_drawing_signature" not in st.session_state:
    st.session_state["last_drawing_signature"] = None

# ═════════════════════════════════════════════════════════════════════════════════
# الواجهة الرئيسية
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown(MAIN_CSS, unsafe_allow_html=True)
st.markdown('<div class="hdr"><h1>🌊 حاسبة شبكات السيول - محلل الشبكة والتكاليف المتقدم</h1></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🗺️ إضافة الخطوط", "📊 تحليل الشبكة", "💰 حساب التكاليف", "📄 التقرير"])

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 1 - إضافة الخطوط (رسم + استيراد)
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab1:
    st.markdown('<div class="section-title">🗺️ إضافة الخطوط</div>', unsafe_allow_html=True)
    
    col_draw, col_upload = st.columns(2)
    
    # الرسم على الخريطة
    with col_draw:
        st.markdown("### رسم الخطوط")
        if FOLIUM_AVAILABLE:
            m = folium.Map(location=[24.7136, 46.6753], zoom_start=12, tiles="OpenStreetMap")
            
            # إضافة الخطوط الموجودة
            for idx, line in enumerate(st.session_state["network_lines"]):
                coords = line.get("coords", [])
                if coords:
                    color = LINE_COLORS[idx % len(LINE_COLORS)]
                    folium.PolyLine(coords, color=color, weight=3, opacity=0.8, popup=line["name"]).add_to(m)
            
            # أداة الرسم
            draw = Draw(
                export=True,
                position="topleft",
                draw_options={
                    "polyline": True,
                    "polygon": False,
                    "rectangle": False,
                    "circle": False,
                    "marker": False,
                },
            )
            draw.add_to(m)
            
            map_data = st_folium(m, width=None, height=400, key="main_map", returned_objects=["last_active_drawing"])
            
            if map_data and map_data.get("last_active_drawing"):
                last_drawing = map_data["last_active_drawing"]
                if last_drawing.get("geometry", {}).get("type") == "LineString":
                    coords = [(c[1], c[0]) for c in last_drawing["geometry"]["coordinates"]]
                    drawing_signature = json.dumps(coords)
                    if st.session_state.get("last_drawing_signature") != drawing_signature and len(coords) >= 2:
                        length = sum(calculate_haversine_distance(coords[i], coords[i+1]) for i in range(len(coords)-1))
                        
                        new_line = {
                            "id": str(uuid.uuid4()),
                            "name": f"خط رسم {len(st.session_state['network_lines']) + 1}",
                            "length": length,
                            "coords": coords,
                            "source": "رسم يدوي",
                            "selected": True,
                            "diameter": 600,
                            "depth": 1.5,
                            "traps_mode": "تلقائي",
                            "traps_value": max(1, int(length / 150)),
                            "manholes_mode": "تلقائي",
                            "manholes_value": max(2, int(length / 120) + 1),
                        }
                        st.session_state["network_lines"].append(new_line)
                        st.session_state["last_drawing_signature"] = drawing_signature
                        st.success(f"✅ تمت إضافة {new_line['name']} بطول {new_line['length']:,.0f} متر")
                        st.rerun()
    
    # استيراد الملفات
    with col_upload:
        st.markdown("### استيراد الملفات")
        
        uploaded_file = st.file_uploader(
            "اختر ملف GeoJSON أو Shapefile",
            type=["geojson", "shp", "zip"],
            help="يمكنك رفع ملف GeoJSON أو Shapefile أو zip يحتوي عليهم"
        )
        
        if uploaded_file:
            file_ext = uploaded_file.name.split('.')[-1].lower()
            
            if file_ext == "geojson":
                try:
                    geojson_data = json.load(uploaded_file)
                    new_lines = load_geojson_lines(geojson_data)
                    
                    if new_lines:
                        st.session_state["network_lines"].extend(new_lines)
                        st.success(f"✅ تم استيراد {len(new_lines)} خط من GeoJSON")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ في قراءة GeoJSON: {e}")
            
            elif file_ext == "shp":
                try:
                    with tempfile.NamedTemporaryFile(suffix=".shp", delete=False) as tmp:
                        tmp.write(uploaded_file.getbuffer())
                        new_lines = load_shapefile_lines(tmp.name)
                        
                        if new_lines:
                            st.session_state["network_lines"].extend(new_lines)
                            st.success(f"✅ تم استيراد {len(new_lines)} خط من Shapefile")
                            st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ في قراءة Shapefile: {e}")
            
            elif file_ext == "zip":
                try:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                            zip_ref.extractall(tmpdir)
                        
                        # البحث عن ملفات shp أو geojson
                        for root, dirs, files in os.walk(tmpdir):
                            for file in files:
                                if file.endswith('.geojson'):
                                    with open(os.path.join(root, file)) as f:
                                        geojson_data = json.load(f)
                                        new_lines = load_geojson_lines(geojson_data)
                                        if new_lines:
                                            st.session_state["network_lines"].extend(new_lines)
                                
                                elif file.endswith('.shp'):
                                    new_lines = load_shapefile_lines(os.path.join(root, file))
                                    if new_lines:
                                        st.session_state["network_lines"].extend(new_lines)
                        
                        if st.session_state["network_lines"]:
                            st.success(f"✅ تم استيراد الملفات بنجاح")
                            st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ في معالجة ZIP: {e}")
    
    # قائمة الخطوط
    st.markdown('<div class="section-title">📋 الخطوط المضافة</div>', unsafe_allow_html=True)
    
    if not st.session_state["network_lines"]:
        st.info("لا توجد خطوط مضافة. ارسم على الخريطة أو استورد ملف.")
    else:
        for idx, ln in enumerate(st.session_state["network_lines"]):
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.write(f"**{ln['name']}** | الطول: {ln['length']:,.0f} م | المصدر: {ln['source']}")
            with col_del:
                if st.button("🗑️", key=f"del_{ln['id']}"):
                    st.session_state["network_lines"] = [l for l in st.session_state["network_lines"] if l['id'] != ln['id']]
                    st.rerun()

import tempfile

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 2 - تحليل الشبكة
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab2:
    st.markdown('<div class="section-title">🌐 تحليل الشبكة</div>', unsafe_allow_html=True)
    
    if not st.session_state["network_lines"]:
        st.warning("لا توجد خطوط للتحليل. أضف خطوطاً أولاً من التبويب السابق.")
    else:
        if st.button("🔍 حلل الشبكة", use_container_width=True):
            with st.spinner("جاري تحليل الشبكة..."):
                G, line_details = build_network_from_lines(st.session_state["network_lines"])
                network_stats = calculate_network_stats(G, line_details)
                st.session_state["network_stats"] = network_stats
                st.success("✅ تم تحليل الشبكة بنجاح!")
        
        if st.session_state["network_stats"]:
            stats = st.session_state["network_stats"]
            
            # عرض الإحصائيات
            col1, col2, col3, col4 = st.columns(4)
            col1.markdown(f'<div class="mc"><div class="v">{stats["num_nodes"]}</div><div class="l">المناهل</div></div>', unsafe_allow_html=True)
            col2.markdown(f'<div class="mc"><div class="v">{stats["num_edges"]}</div><div class="l">الأنابيب</div></div>', unsafe_allow_html=True)
            col3.markdown(f'<div class="mc"><div class="v">{stats["num_components"]}</div><div class="l">المكونات</div></div>', unsafe_allow_html=True)
            col4.markdown(f'<div class="mc"><div class="v">{stats["density"]:.3f}</div><div class="l">الكثافة</div></div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("الطول الإجمالي", f"{stats['total_length']/1000:.2f} كم")
            with col2:
                st.metric("متوسط الاتصالات", f"{stats['avg_degree']:.2f}")
            
            if stats["is_connected"]:
                st.markdown('<div class="success-box">✅ الشبكة متصلة بالكامل</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="warning-box">⚠️ الشبكة بها {stats["num_components"]} أجزاء منفصلة</div>', unsafe_allow_html=True)
            
            # رسم الشبكة
            st.markdown("### 📊 رسم الشبكة")
            fig, ax = plt.subplots(figsize=(12, 8), facecolor='white')
            
            G, _ = build_network_from_lines(st.session_state["network_lines"])
            pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
            
            nx.draw_networkx_edges(G, pos, width=2, alpha=0.6, edge_color='#1a5fa8', ax=ax)
            nx.draw_networkx_nodes(G, pos, node_color='#FF6B6B', node_size=300, ax=ax, edgecolors='#0a2a5e', linewidths=2)
            nx.draw_networkx_labels(G, pos, labels={node: f"M{i}" for i, node in enumerate(G.nodes())}, 
                                   font_size=8, font_weight='bold', ax=ax)
            
            ax.set_title("🌐 رسم شبكة الصرف", fontsize=14, fontweight='bold', pad=20)
            ax.axis('off')
            
            st.pyplot(fig, use_container_width=True)

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 3 - حساب التكاليف
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab3:
    st.markdown('<div class="section-title">💰 حساب التكاليف</div>', unsafe_allow_html=True)
    
    if not st.session_state["network_lines"]:
        st.warning("لا توجد خطوط للحساب. أضف خطوطاً أولاً.")
    else:
        st.markdown("#### إعدادات الخطوط")
        
        for ln in st.session_state["network_lines"]:
            with st.expander(f"⚙️ {ln['name']} — {ln['length']:,.0f} م", expanded=False):
                ln["selected"] = st.checkbox("تضمين في الحساب", value=ln["selected"], key=f"sel_{ln['id']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    diam_options = sorted(PIPE_PRICES.keys())
                    ln["diameter"] = st.selectbox(
                        "القطر (ملم)", options=diam_options,
                        index=diam_options.index(ln["diameter"]) if ln["diameter"] in diam_options else 0,
                        key=f"diam_{ln['id']}",
                    )
                with col2:
                    ln["depth"] = st.number_input(
                        "العمق (م)", min_value=0.5, value=float(ln["depth"]), step=0.1, key=f"depth_{ln['id']}",
                    )
        
        if st.button("💰 احسب التكاليف من الشبكة", use_container_width=True, type="primary"):
            if not st.session_state.get("network_stats"):
                st.error("❌ يجب تحليل الشبكة أولاً من التبويب السابق")
            else:
                with st.spinner("جاري حساب التكاليف..."):
                    selected = [ln for ln in st.session_state["network_lines"] if ln["selected"]]
                    combined = generate_cost_from_network(selected, st.session_state["network_stats"])
                    st.session_state["combined_result"] = combined
                    st.success("✅ تم الحساب بنجاح!")
                    st.rerun()
        
        if st.session_state["combined_result"]:
            combined = st.session_state["combined_result"]
            
            st.markdown("### 📊 ملخص التكاليف")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.markdown(f'<div class="mc"><div class="v">{len(combined["per_line"])}</div><div class="l">الخطوط</div></div>', unsafe_allow_html=True)
            col2.markdown(f'<div class="mc"><div class="v">{combined["total_manholes"]}</div><div class="l">المناهل</div></div>', unsafe_allow_html=True)
            col3.markdown(f'<div class="mc"><div class="v">{combined["total_traps"]}</div><div class="l">المصائد</div></div>', unsafe_allow_html=True)
            col4.markdown(f'<div class="mc"><div class="v">{combined["grand_total"]/1e6:.2f}M</div><div class="l">التكلفة (ريال)</div></div>', unsafe_allow_html=True)
            
            # جدول الكميات المجمعة
            st.markdown("### 📦 الكميات")
            
            items_df = pd.DataFrame([
                {
                    "البند": item["name"],
                    "الكمية": f"{item['qty']:,.2f}",
                    "الوحدة": item["unit"],
                    "السعر": f"{(item['total']/item['qty'] if item['qty']>0 else 0):,.0f}",
                    "الإجمالي": f"{item['total']:,.0f}",
                }
                for item in combined["merged_items"]
            ])
            st.dataframe(items_df, use_container_width=True, hide_index=True)
            
            st.markdown(f"### 💵 **التكلفة الإجمالية: {combined['grand_total']:,.0f} ريال**")

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 4 - التقرير
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab4:
    st.markdown('<div class="section-title">📄 التقرير الشامل</div>', unsafe_allow_html=True)
    
    if not st.session_state["combined_result"]:
        st.warning("لا توجد بيانات للتقرير. أكمل الخطوات السابقة أولاً.")
    else:
        combined = st.session_state["combined_result"]
        
        col_pdf, col_csv = st.columns(2)
        
        with col_pdf:
            pdf_bytes = generate_pdf_report(
                combined, 
                st.session_state["network_lines"],
                st.session_state.get("network_stats")
            )
            
            if pdf_bytes:
                st.download_button(
                    label="📥 تحميل PDF",
                    data=pdf_bytes,
                    file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        
        with col_csv:
            csv_data = "البند,الكمية,الوحدة,السعر,الإجمالي\n"
            for item in combined["merged_items"]:
                avg_price = item["total"] / item["qty"] if item["qty"] > 0 else 0
                csv_data += f"{item['name']},{item['qty']:.2f},{item['unit']},{avg_price:.0f},{item['total']:.0f}\n"
            
            st.download_button(
                label="📥 تحميل CSV",
                data=csv_data,
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        
        # معاينة التقرير
        st.markdown("### 📋 معاينة التقرير")
        
        with st.expander("ملخص المشروع", expanded=True):
            st.write(f"**عدد الخطوط:** {len(combined['per_line'])}")
            st.write(f"**الطول الإجمالي:** {sum(pl['line'].get('length', 0) for pl in combined['per_line']):,.0f} متر")
            st.write(f"**عدد المناهل:** {combined['total_manholes']}")
            st.write(f"**عدد المصائد:** {combined['total_traps']}")
            st.write(f"**التكلفة الإجمالية:** {combined['grand_total']:,.0f} ريال")
        
        with st.expander("تفاصيل الخطوط"):
            for pl in combined["per_line"]:
                ln = pl["line"]
                st.write(f"**{ln['name']}**")
                st.write(f"- الطول: {ln['length']:,.0f} متر")
                st.write(f"- القطر: {ln.get('diameter', 600)} ملم")
                st.write(f"- العمق: {ln.get('depth', 1.5):.2f} متر")
                st.write(f"- المناهل: {pl['manholes']}")
                st.write(f"- المصائد: {pl['traps']}")
                st.write(f"- التكلفة: {pl['total']:,.0f} ريال")
                st.divider()
        
        with st.expander("الكميات المجمعة"):
            st.dataframe(
                pd.DataFrame([
                    {
                        "البند": item["name"],
                        "الكمية": f"{item['qty']:,.2f}",
                        "الوحدة": item["unit"],
                        "الإجمالي": f"{item['total']:,.0f}",
                    }
                    for item in combined["merged_items"]
                ]),
                use_container_width=True,
                hide_index=True
            )

st.markdown("<div style='text-align:center;color:#999;font-size:0.75rem;margin-top:20px'>© 2025 Flood Drainage Network Analysis</div>", unsafe_allow_html=True)

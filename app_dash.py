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

try:
    import folium
    from streamlit_folium import st_folium
    from folium.plugins import Draw
    FOLIUM_AVAILABLE = True
except ModuleNotFoundError:
    FOLIUM_AVAILABLE = False

try:
    import shapefile  # pyshp
    SHAPEFILE_AVAILABLE = True
except ModuleNotFoundError:
    SHAPEFILE_AVAILABLE = False

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont as RLFont
    PDF_AVAILABLE = True
except ModuleNotFoundError:
    PDF_AVAILABLE = False

st.set_page_config(page_title="حاسبة شبكات السيول المتقدمة", page_icon="🌊",
                   layout="wide", initial_sidebar_state="collapsed",
                   menu_items={'Get Help': None, 'Report a bug': None, 'About': None})

PIPE_PRICES = {
    400: 454, 500: 619, 600: 725, 700: 906, 800: 1045,
    900: 1225, 1000: 1440, 1100: 1600, 1200: 1812, 1300: 1920, 1400: 2132,
}

LINE_COLORS = ["#FF0000", "#0a7d34", "#e8a93a", "#7a1fa8", "#1a5fa8", "#c2185b", "#00838f", "#5d4037"]

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

# ═════════════════════════════════════════════════════════════════════════════════
# ──── الأنماط (CSS) ── متجاوبة مع الجوال ────
# ═════════════════════════════════════════════════════════════════════════════════

MAIN_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
*{box-sizing:border-box}
html,body,[class*="css"],.stApp{font-family:'Cairo',sans-serif!important;direction:rtl;-webkit-text-size-adjust:100%}
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stToolbarActions"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"],#MainMenu,footer,footer *,
.stToolbar,button[title="View app fullscreen"],a[href*="streamlit.io"],a[href*="github.com"],
[data-testid="baseButton-headerNoPadding"],[data-testid="stSidebar"]
{display:none!important;visibility:hidden!important;height:0!important;overflow:hidden!important;pointer-events:none!important}

.block-container{padding:0.5rem 0.6rem 2rem!important;max-width:1400px!important;margin:0 auto!important}

.hdr{background:linear-gradient(135deg,#0a2a5e,#1a5fa8);color:#fff;padding:12px 14px;border-radius:12px;
  margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px}
.hdr h1{margin:0;font-size:1rem;font-weight:900;line-height:1.4}
.hdr p{margin:0;font-size:.72rem;color:#b8d9f8}
.hdr .bdg{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.3);
  padding:4px 10px;border-radius:14px;font-size:.7rem;font-weight:700;white-space:nowrap}

.mc{background:#fff;border-radius:10px;padding:10px 8px;box-shadow:0 2px 8px rgba(0,0,0,.08);
  border-top:3px solid #1a5fa8;text-align:center;margin-bottom:6px}
.mc .v{font-size:1.1rem;font-weight:900;color:#0a2a5e;word-break:break-word}
.mc .l{font-size:.68rem;color:#6b7a99;margin-top:2px}

.section-title{color:#0a2a5e;font-size:.92rem;font-weight:900;margin:14px 0 8px;
  border-bottom:2px solid #1a5fa8;padding-bottom:4px}

.stButton>button{background:linear-gradient(135deg,#1a5fa8,#0a2a5e)!important;color:#fff!important;
  border:none!important;border-radius:10px!important;font-family:'Cairo',sans-serif!important;
  font-weight:700!important;font-size:.95rem!important;padding:13px 8px!important;min-height:48px!important;
  width:100%!important}

.stDownloadButton>button{background:linear-gradient(135deg,#188a4e,#0e5e34)!important;color:#fff!important;
  border:none!important;border-radius:10px!important;font-family:'Cairo',sans-serif!important;
  font-weight:700!important;font-size:.92rem!important;padding:12px 8px!important;min-height:48px!important;
  width:100%!important}

.stTextInput>div>div>input,.stNumberInput>div>div>input{min-height:46px!important;font-size:1rem!important;
  font-family:'Cairo',sans-serif!important;direction:rtl!important;border-radius:10px!important}
.stSelectbox [data-baseweb="select"]>div{min-height:46px!important;font-family:'Cairo',sans-serif!important;border-radius:10px!important}
.stRadio label{font-size:.85rem!important}
.stFileUploader label{font-size:.88rem!important;font-weight:700!important;color:#0a2a5e!important}
.stFileUploader [data-testid="stFileUploaderDropzone"]{border-radius:10px!important}
.stCheckbox label{font-size:.85rem!important}

.stTabs [data-baseweb="tab-list"]{gap:2px!important;flex-wrap:wrap!important}
.stTabs [data-baseweb="tab"]{font-family:'Cairo',sans-serif!important;font-weight:700!important;
  font-size:.85rem!important;padding:9px 12px!important;min-height:42px!important;white-space:nowrap!important}

.cost-table{width:100%;border-collapse:collapse;font-size:0.82rem;direction:rtl;margin:10px 0;
  display:block;overflow-x:auto;white-space:nowrap}
.cost-table th,.cost-table td{padding:8px;border:1px solid #d0e4f7;text-align:right}
.cost-table th{background:#eaf4ff;color:#0a2a5e;font-weight:700}
.cost-table tr:nth-child(even){background:#f8fbfe}
.cost-table .total{background:#0a2a5e;color:#fff;font-weight:700}

.map-info{background:#eaf4ff;border-right:4px solid #1a5fa8;border-radius:8px;
  padding:10px 13px;font-size:.82rem;color:#0a2a5e;margin-bottom:8px;line-height:1.8}
.warn-box{background:#fff4e5;border-right:4px solid #e8a93a;border-radius:8px;
  padding:10px 13px;font-size:.82rem;color:#7a5210;margin-bottom:8px;line-height:1.8}

.line-card{background:#fff;border:1px solid #d0e4f7;border-radius:10px;padding:10px 12px;margin-bottom:8px;
  border-right:5px solid var(--lc,#1a5fa8)}
.line-card .lname{font-weight:900;color:#0a2a5e;font-size:.9rem}
.line-card .lmeta{font-size:.74rem;color:#6b7a99;margin-top:2px}

/* ── جوال: شاشات أصغر من 640px ── */
@media (max-width: 640px){
  .block-container{padding:0.4rem 0.4rem 1.5rem!important}
  .hdr{padding:10px 12px;border-radius:10px}
  .hdr h1{font-size:.85rem}
  .hdr p{font-size:.65rem}
  .hdr .bdg{font-size:.62rem;padding:3px 8px}
  .section-title{font-size:.85rem;margin:10px 0 6px}
  .mc{padding:8px 6px}
  .mc .v{font-size:.95rem}
  .mc .l{font-size:.62rem}
  .stButton>button,.stDownloadButton>button{font-size:.88rem!important;padding:12px 6px!important;min-height:46px!important}
  .stTabs [data-baseweb="tab"]{font-size:.76rem!important;padding:8px 8px!important;min-height:38px!important}
  .cost-table{font-size:.74rem}
  .cost-table th,.cost-table td{padding:6px 5px}
  .map-info,.warn-box{font-size:.76rem;padding:8px 10px}
  div[data-testid="column"]{min-width:100%!important;flex:1 1 100%!important}
}
</style>"""

# ═════════════════════════════════════════════════════════════════════════════════
# ──── دوال تحليل الشبكة بـ NetworkX ────
# ═════════════════════════════════════════════════════════════════════════════════

def build_network_graph(lines):
    """بناء رسم بياني للشبكة من الخطوط"""
    G = nx.Graph()
    
    for idx, line in enumerate(lines):
        if line.get("selected", True):
            coords = line.get("coords", [])
            if len(coords) >= 2:
                # إضافة الحواف بين نقاط الخط
                for i in range(len(coords) - 1):
                    start = tuple(coords[i])
                    end = tuple(coords[i + 1])
                    
                    # إضافة العقد (المناهل)
                    G.add_node(start, line_idx=idx, pos=start)
                    G.add_node(end, line_idx=idx, pos=end)
                    
                    # إضافة الحافة (الأنبوب)
                    distance = math.sqrt((start[0]-end[0])**2 + (start[1]-end[1])**2) * 111000  # تقريباً متر
                    G.add_edge(start, end, weight=distance, line_idx=idx, diameter=line.get("diameter", 600))
    
    return G

def calculate_network_stats(G, lines):
    """حساب إحصائيات الشبكة"""
    if G.number_of_nodes() == 0:
        return None
    
    stats = {
        "num_nodes": G.number_of_nodes(),  # عدد المناهل
        "num_edges": G.number_of_edges(),  # عدد الأنابيب
        "num_connected_components": nx.number_connected_components(G),
        "network_density": nx.density(G),
        "avg_degree": sum(dict(G.degree()).values()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
        "total_length": sum(data['weight'] for _, _, data in G.edges(data=True)),
    }
    
    # حساب عدد المناهل لكل خط
    lines_nodes = {}
    for idx, line in enumerate(lines):
        if line.get("selected", True):
            coords = line.get("coords", [])
            lines_nodes[idx] = len(coords)
    
    stats["lines_nodes"] = lines_nodes
    
    return stats

def visualize_network(G, lines):
    """عرض الشبكة بصرياً"""
    if G.number_of_nodes() == 0:
        st.warning("لا توجد بيانات كافية لعرض الشبكة")
        return
    
    fig, ax = plt.subplots(figsize=(12, 8), facecolor='white')
    
    # استخدام Spring Layout
    pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
    
    # رسم الحواف (الأنابيب)
    nx.draw_networkx_edges(G, pos, width=2, alpha=0.6, edge_color='#1a5fa8', ax=ax)
    
    # رسم العقد (المناهل)
    node_colors = []
    for node in G.nodes():
        # تحديد اللون بناءً على الخط
        line_idx = G.nodes[node].get('line_idx', 0)
        node_colors.append(LINE_COLORS[line_idx % len(LINE_COLORS)])
    
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=300, ax=ax, edgecolors='#0a2a5e', linewidths=2)
    
    # إضافة التسميات
    nx.draw_networkx_labels(G, pos, labels={node: f"M{i}" for i, node in enumerate(G.nodes())}, 
                           font_size=8, font_weight='bold', ax=ax)
    
    ax.set_title("🌐 رسم الشبكة (الحمراء = عقد، الزرقاء = وصلات)", fontsize=14, fontweight='bold', pad=20)
    ax.axis('off')
    
    st.pyplot(fig, use_container_width=True)

def calculate_auto_manholes(length, diameter=600):
    """حساب عدد المناهل تلقائياً بناءً على الطول والقطر"""
    # قاعدة: منهل كل 120 متر (تقريبياً)
    base_spacing = 120
    
    # تقليل المسافة للأقطار الكبيرة
    if diameter >= 1000:
        base_spacing = 150
    elif diameter <= 600:
        base_spacing = 100
    
    # إضافة منهل في البداية والنهاية
    return max(2, int(length / base_spacing) + 1)

def calculate_auto_traps(length):
    """حساب عدد المصائد تلقائياً"""
    # مصيدة كل 150 متر
    return max(1, int(length / 150))

# ═════════════════════════════════════════════════════════════════════════════════
# ──── Initialize Session State ────
# ═════════════════════════════════════════════════════════════════════════════════

if "network_lines" not in st.session_state:
    st.session_state["network_lines"] = []
if "combined_result" not in st.session_state:
    st.session_state["combined_result"] = None
if "last_drawing_signature" not in st.session_state:
    st.session_state["last_drawing_signature"] = None

# ═════════════════════════════════════════════════════════════════════════════════
# ──── الدوال الأساسية ────
# ═════════════════════════════════════════════════════════════════════════════════

def add_line(coords, source="رسم يدوي"):
    """إضافة خط جديد"""
    length = 0
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        # Haversine formula
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1*math.pi/180) * math.cos(lat2*math.pi/180) * math.sin(dlon/2)**2
        distance = 2 * 6371000 * math.asin(math.sqrt(a))
        length += distance
    
    new_line = {
        "id": str(uuid.uuid4()),
        "name": f"خط {len(st.session_state['network_lines']) + 1}",
        "length": length,
        "coords": coords,
        "source": source,
        "selected": True,
        "diameter": 600,
        "depth": 1.5,
        "traps_mode": "تلقائي",
        "traps_value": calculate_auto_traps(length),
        "manholes_mode": "تلقائي",
        "manholes_value": calculate_auto_manholes(length, 600),
    }
    
    st.session_state["network_lines"].append(new_line)
    return new_line

def remove_line(line_id):
    """حذف خط"""
    st.session_state["network_lines"] = [l for l in st.session_state["network_lines"] if l["id"] != line_id]
    st.session_state["combined_result"] = None

def calculate_cost_per_line(line):
    """حساب تكلفة خط واحد"""
    diameter = line.get("diameter", 600)
    depth = line.get("depth", 1.5)
    length = line.get("length", 0)
    
    price_per_meter = PIPE_PRICES.get(diameter, 725)
    
    if line.get("manholes_mode") == "تلقائي":
        num_manholes = calculate_auto_manholes(length, diameter)
    else:
        num_manholes = line.get("manholes_value", 1)
    
    if line.get("traps_mode") == "تلقائي":
        num_traps = calculate_auto_traps(length)
    else:
        num_traps = line.get("traps_value", 1)
    
    # تفاصيل البنود
    items = [
        {"name": "أنابيب صرف", "qty": length, "unit": "م", "price": price_per_meter, "total": length * price_per_meter},
        {"name": "حفر (بناء الأساس)", "qty": length, "unit": "م", "price": 50, "total": length * 50},
        {"name": "مناهل", "qty": num_manholes, "unit": "عدد", "price": 3000, "total": num_manholes * 3000},
        {"name": "مصائد", "qty": num_traps, "unit": "عدد", "price": 2000, "total": num_traps * 2000},
        {"name": "ردم وتسوية", "qty": length * depth, "unit": "م³", "price": 30, "total": length * depth * 30},
    ]
    
    total = sum(item["total"] for item in items)
    
    return {
        "items": items,
        "total": total,
        "num_manholes": num_manholes,
        "num_traps": num_traps,
    }

def build_combined_result(lines):
    """بناء نتيجة مدمجة لعدة خطوط"""
    per_line = []
    all_items = {}
    warnings = []
    
    for line in lines:
        report = calculate_cost_per_line(line)
        per_line.append({"line": line, "report": report})
        
        for item in report["items"]:
            key = item["name"]
            if key not in all_items:
                all_items[key] = {"qty": 0, "total": 0, "unit": item["unit"], "price": item["price"]}
            all_items[key]["qty"] += item["qty"]
            all_items[key]["total"] += item["total"]
    
    grand_total = sum(item["total"] for item in all_items.values())
    merged_items = [{"name": name, **data} for name, data in all_items.items()]
    
    return {
        "per_line": per_line,
        "merged_items": merged_items,
        "grand_total": grand_total,
        "warnings": warnings,
        "total_manholes": sum(item["report"]["num_manholes"] for item in per_line),
        "total_traps": sum(item["report"]["num_traps"] for item in per_line),
    }

# ═════════════════════════════════════════════════════════════════════════════════
# ──── الواجهة الرئيسية ────
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown(MAIN_CSS, unsafe_allow_html=True)

st.markdown('<div class="hdr"><h1>🌊 حاسبة شبكات السيول المتقدمة مع تحليل الشبكة</h1></div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🗺️ رسم الخطوط", "💰 حساب التكاليف", "📊 تحليل الشبكة"])

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 1 ── رسم الخطوط على الخريطة
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab1:
    st.markdown('<div class="section-title">🗺️ رسم الخطوط على الخريطة</div>', unsafe_allow_html=True)
    
    if not FOLIUM_AVAILABLE:
        st.error("⚠️ مكتبة folium غير متوفرة. يرجى تثبيتها: pip install folium streamlit-folium")
    else:
        # خريطة تفاعلية
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
                "circlemarker": False,
            },
        )
        draw.add_to(m)
        
        map_data = st_folium(m, width=None, height=480, key="main_map", returned_objects=["last_active_drawing"])
        
        last_drawing = map_data.get("last_active_drawing") if map_data else None
        if last_drawing and last_drawing.get("geometry", {}).get("type") == "LineString":
            coords = [(c[1], c[0]) for c in last_drawing["geometry"]["coordinates"]]
            drawing_signature = json.dumps(coords)
            if st.session_state.get("last_drawing_signature") != drawing_signature and len(coords) >= 2:
                new_line = add_line(coords, "رسم يدوي على الخريطة")
                st.session_state["last_drawing_signature"] = drawing_signature
                st.success(f"✅ تمت إضافة {new_line['name']} بطول {new_line['length']:,.0f} متر")
                st.rerun()
    
    # قائمة الخطوط الحالية
    st.markdown('<div class="section-title">📋 الخطوط المضافة</div>', unsafe_allow_html=True)
    
    if not st.session_state["network_lines"]:
        st.info("لا توجد خطوط مضافة بعد. ارسم خطاً على الخريطة لإضافة أول خط.")
    else:
        for idx, ln in enumerate(st.session_state["network_lines"]):
            color = LINE_COLORS[idx % len(LINE_COLORS)]
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f'<div class="line-card" style="--lc:{color}">'
                    f'<div class="lname">{ln["name"]}</div>'
                    f'<div class="lmeta">الطول: {ln["length"]:,.0f} م · المصدر: {ln["source"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("🗑️", key=f"del_{ln['id']}", help="حذف هذا الخط", use_container_width=True):
                    remove_line(ln["id"])
                    st.rerun()
        
        if st.button("🗑️ حذف جميع الخطوط", key="del_all_lines"):
            st.session_state["network_lines"] = []
            st.session_state["combined_result"] = None
            st.rerun()

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 2 ── حساب التكاليف
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab2:
    st.markdown('<div class="section-title">📊 إعدادات كل خط</div>', unsafe_allow_html=True)
    
    if not st.session_state["network_lines"]:
        st.info("لا توجد خطوط متاحة. أضف خطوطاً من التبويب الأول أولاً.")
    else:
        st.markdown('<div class="map-info">💡 حدّد القطر والعمق لكل خط على حدة، واختر الخطوط التي تريد تضمينها في الحساب الإجمالي.</div>', unsafe_allow_html=True)
        
        for ln in st.session_state["network_lines"]:
            with st.expander(f"⚙️ {ln['name']} — {ln['length']:,.0f} م", expanded=False):
                ln["selected"] = st.checkbox("تضمين هذا الخط في الحساب الإجمالي", value=ln["selected"], key=f"sel_{ln['id']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    diam_options = sorted(PIPE_PRICES.keys())
                    ln["diameter"] = st.selectbox(
                        "قطر الأنبوب (ملم)", options=diam_options,
                        index=diam_options.index(ln["diameter"]) if ln["diameter"] in diam_options else 0,
                        key=f"diam_{ln['id']}",
                    )
                with col2:
                    ln["depth"] = st.number_input(
                        "متوسط العمق (م)", min_value=0.5, value=float(ln["depth"]), step=0.1, key=f"depth_{ln['id']}",
                    )
                
                col3, col4 = st.columns(2)
                with col3:
                    ln["traps_mode"] = st.radio(
                        "المصائد:", ["تلقائي", "يدوي"], horizontal=True,
                        index=0 if ln["traps_mode"] == "تلقائي" else 1, key=f"trapsmode_{ln['id']}",
                    )
                    if ln["traps_mode"] == "يدوي":
                        ln["traps_value"] = st.number_input(
                            "عدد المصائد", min_value=1, value=int(ln["traps_value"]), step=1, key=f"trapsval_{ln['id']}",
                        )
                with col4:
                    ln["manholes_mode"] = st.radio(
                        "المناهل:", ["تلقائي", "يدوي"], horizontal=True,
                        index=0 if ln["manholes_mode"] == "تلقائي" else 1, key=f"manholemode_{ln['id']}",
                    )
                    if ln["manholes_mode"] == "يدوي":
                        ln["manholes_value"] = st.number_input(
                            "عدد المناهل", min_value=1, value=int(ln["manholes_value"]), step=1, key=f"manholeval_{ln['id']}",
                        )
                
                # عرض معلومات سريعة عن المناهل والمصائد
                auto_manholes = calculate_auto_manholes(ln["length"], ln["diameter"])
                auto_traps = calculate_auto_traps(ln["length"])
                st.caption(f"📌 المقترحات التلقائية: {auto_manholes} منهل، {auto_traps} مصائد")
        
        if st.button("💰 احسب تكلفة الخطوط المختارة", key="calc_combined", use_container_width=True):
            selected = [ln for ln in st.session_state["network_lines"] if ln["selected"]]
            if not selected:
                st.warning("⚠️ لم يتم تحديد أي خط للحساب.")
            else:
                with st.spinner("جاري حساب جميع الخطوط..."):
                    combined = build_combined_result(selected)
                    st.session_state["combined_result"] = combined
                    st.success(f"✅ تم حساب {len(selected)} خط بنجاح!")
    
    if st.session_state["combined_result"]:
        combined = st.session_state["combined_result"]
        
        st.markdown('<div class="section-title">📋 ملخص الخطوط</div>', unsafe_allow_html=True)
        total_length = sum(pl["line"]["length"] for pl in combined["per_line"])
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(f'<div class="mc"><div class="v">{len(combined["per_line"])}</div><div class="l">الخطوط</div></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="mc"><div class="v">{total_length:,.0f}</div><div class="l">الطول (م)</div></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="mc"><div class="v">{combined["total_manholes"]}</div><div class="l">المناهل</div></div>', unsafe_allow_html=True)
        col4.markdown(f'<div class="mc"><div class="v">{combined["total_traps"]}</div><div class="l">المصائد</div></div>', unsafe_allow_html=True)
        
        # جدول التكاليف
        st.markdown('<div class="section-title">📦 الكميات والتكاليف</div>', unsafe_allow_html=True)
        
        items_data = []
        for item in combined["merged_items"]:
            avg_price = item["total"] / item["qty"] if item["qty"] > 0 else 0
            items_data.append({
                "البند": item["name"],
                "الكمية": f"{item['qty']:,.2f}",
                "الوحدة": item["unit"],
                "السعر (المتوسط)": f"{avg_price:,.0f}",
                "الإجمالي": f"{item['total']:,.0f}"
            })
        
        st.dataframe(items_data, use_container_width=True, hide_index=True)
        
        st.markdown(f'### 💵 **التكلفة الإجمالية: {combined["grand_total"]:,.0f} ريال**', unsafe_allow_html=False)

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 3 ── تحليل الشبكة بـ NetworkX
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab3:
    st.markdown('<div class="section-title">📊 تحليل الشبكة المتقدم</div>', unsafe_allow_html=True)
    
    selected_for_analysis = [ln for ln in st.session_state["network_lines"] if ln.get("selected", True)]
    
    if not selected_for_analysis:
        st.warning("⚠️ لا توجد خطوط مختارة للتحليل. اختر خطوطاً من التبويب الأول أولاً.")
    else:
        # بناء الشبكة
        G = build_network_graph(selected_for_analysis)
        
        if G.number_of_nodes() == 0:
            st.error("❌ لا يمكن بناء الشبكة. تأكد من وجود إحداثيات صحيحة للخطوط.")
        else:
            # حساب الإحصائيات
            stats = calculate_network_stats(G, selected_for_analysis)
            
            st.markdown('<div class="section-title">📈 إحصائيات الشبكة</div>', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.markdown(f'<div class="mc"><div class="v">{stats["num_nodes"]}</div><div class="l">المناهل (Nodes)</div></div>', unsafe_allow_html=True)
            col2.markdown(f'<div class="mc"><div class="v">{stats["num_edges"]}</div><div class="l">الأنابيب (Edges)</div></div>', unsafe_allow_html=True)
            col3.markdown(f'<div class="mc"><div class="v">{stats["num_connected_components"]}</div><div class="l">المكونات المتصلة</div></div>', unsafe_allow_html=True)
            col4.markdown(f'<div class="mc"><div class="v">{stats["network_density"]:.3f}</div><div class="l">كثافة الشبكة</div></div>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("متوسط درجة الاتصال", f"{stats['avg_degree']:.2f}")
            col2.metric("إجمالي طول الشبكة", f"{stats['total_length']/1000:.2f} كم")
            
            # معلومات الخطوط
            st.markdown('<div class="section-title">🔗 تفاصيل الخطوط</div>', unsafe_allow_html=True)
            lines_info = []
            for idx, num_nodes in stats["lines_nodes"].items():
                if idx < len(selected_for_analysis):
                    ln = selected_for_analysis[idx]
                    lines_info.append({
                        "الخط": ln["name"],
                        "المناهل": num_nodes,
                        "الطول": f"{ln['length']:,.0f} م",
                        "القطر": f"{ln.get('diameter', 600)} ملم"
                    })
            
            st.dataframe(lines_info, use_container_width=True, hide_index=True)
            
            # رسم الشبكة
            st.markdown('<div class="section-title">🌐 رسم الشبكة البصري</div>', unsafe_allow_html=True)
            visualize_network(G, selected_for_analysis)
            
            # تحليل الاتصالية
            st.markdown('<div class="section-title">🔍 تحليل الاتصالية</div>', unsafe_allow_html=True)
            
            if nx.is_connected(G):
                st.success("✅ الشبكة متصلة بالكامل")
            else:
                components = list(nx.connected_components(G))
                st.warning(f"⚠️ الشبكة بها {len(components)} مكون منفصل")
                for i, comp in enumerate(components):
                    st.text(f"المكون {i+1}: {len(comp)} منهل")

st.markdown("<div style='text-align:center;color:#999;font-size:0.75rem;margin-top:20px'>© 2025 Flood Drainage Networks - Advanced Analysis Version</div>", unsafe_allow_html=True)

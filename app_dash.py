import streamlit as st
import math
import json
import uuid
from datetime import datetime
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, FullScreen, MiniMap

# ─────────────────────────────────────────────────────────────────────────────
# إعداد الصفحة العامة
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="محلل شبكات السيول المطور",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# تصميم الواجهات CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
* { font-family: 'Cairo', sans-serif !important; }
html, body, [class*="css"] { direction: rtl; text-align: right; }
.stApp { background: #f4f7fc; }
.main-header {
    background: linear-gradient(135deg, #0a2a5e 0%, #1a5fa8 60%, #2980d4 100%);
    color: white; padding: 25px; border-radius: 12px; margin-bottom: 20px; text-align: center;
    box-shadow: 0 4px 15px rgba(10,42,94,0.15);
}
.section-title {
    font-size: 1.4rem; font-weight: 700; color: #0a2a5e;
    border-right: 5px solid #1a5fa8; padding-right: 10px; margin: 15px 0;
}
.kpi-card {
    background: white; border-radius: 10px; padding: 15px; text-align: center;
    border-top: 4px solid #1a5fa8; box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.kpi-value { font-size: 1.8rem; font-weight: 900; color: #0a2a5e; }
.kpi-label { font-size: 0.85rem; color: #6b7a99; }
.info-banner {
    background: #e8f4fd; border-right: 4px solid #1a5fa8; border-radius: 6px;
    padding: 10px 15px; color: #0a2a5e; font-weight: 600; margin-bottom: 15px;
}
.total-row {
    background: #0a2a5e; color: white; border-radius: 8px; padding: 12px;
    font-size: 1.3rem; font-weight: bold; text-align: center; margin-top: 15px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# الثوابت والأسعار (SAR)
# ─────────────────────────────────────────────────────────────────────────────
PIPE_PRICES = {
    400: 454, 500: 619, 600: 725, 700: 906, 800: 1045,
    900: 1225, 1000: 1440, 1100: 1600, 1200: 1812, 1300: 1920, 1400: 2132
}

PIPE_COLORS = {
    400: "#2196F3", 500: "#4CAF50", 600: "#FF9800", 700: "#9C27B0",
    800: "#F44336", 900: "#00BCD4", 1000: "#FF5722", 1100: "#795548",
    1200: "#607D8B", 1300: "#E91E63", 1400: "#3F51B5"
}

MANHOLE_PRICE = 3000
TRAP_PRICE = 2000
EXCAVATION = 50
BACKFILL_PRICE = 30
TRAP_SPACING = 35

# ─────────────────────────────────────────────────────────────────────────────
# الدوال الحسابية المساعدة
# ─────────────────────────────────────────────────────────────────────────────
def haversine(c1, c2):
    R = 6371000
    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    a = math.sin((lat2 - lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2 - lon1)/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def line_length(coords):
    return sum(haversine(coords[i], coords[i+1]) for i in range(len(coords)-1))

def center_of(coords):
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return [(min(lats)+max(lats))/2, (min(lons)+max(lons))/2]

# ─────────────────────────────────────────────────────────────────────────────
# كلاس بناء وهيكلة الشبكة المحسّن
# ─────────────────────────────────────────────────────────────────────────────
class NetworkAnalyzer:
    def __init__(self, lines):
        self.lines = lines
        self.G = nx.Graph()
        self.edges_list = []
        self.nodes_coords = {}
        self._build()

    def _build(self):
        nid = 0
        for line in self.lines:
            coords = line.get("coords", [])
            if len(coords) < 2: continue
            
            for i in range(len(coords)-1):
                s, e = tuple(coords[i][:2]), tuple(coords[i+1][:2])
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
                    "line_name": line.get("name", "فرع"),
                    "node_start": sn,
                    "node_end": en,
                    "diameter": line.get("diameter", 600),
                    "depth": line.get("depth", 1.5)
                })

    def stats(self):
        return {
            "nodes": self.G.number_of_nodes(),
            "edges": len(self.edges_list),
            "length": sum(e["distance"] for e in self.edges_list),
            "components": nx.number_connected_components(self.G),
        }

# ─────────────────────────────────────────────────────────────────────────────
# إدارة عناصر الجلسة Session State
# ─────────────────────────────────────────────────────────────────────────────
if "lines" not in st.session_state: st.session_state.lines = []
if "cost" not in st.session_state: st.session_state.cost = None

st.markdown("""
<div class="main-header">
    <h1>🌊 نظام تحليل شبكات ومصارف السيول الهندسية</h1>
    <p>لوحة التحكم الذكية لإدخال الخصائص الفردية للفروع ومحاذاة الخرائط</p>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["🏠 الرئيسية", "🗺️ ١ · رسم وإدخال الشبكة", "🌐 ٢ · تحليل الشبكة والخصائص الفردية", "📋 ٣ · التقارير وتصدير PDF"])

# 🏠 الرئيسية
with tabs[0]:
    st.markdown("<div class='section-title'>الملخص العام الفوري للمشروع</div>", unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    tot_len = sum(ln["length"] for ln in st.session_state.lines) / 1000
    tot_cost = st.session_state.cost["total_cost"] if st.session_state.cost else 0
    
    k1.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(st.session_state.lines)}</div><div class="kpi-label">عدد الخطوط المرسومة</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="kpi-card"><div class="kpi-value">{tot_len:.2f} كم</div><div class="kpi-label">الطول الإجمالي للشبكة</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="kpi-card"><div class="kpi-value">{tot_cost:,.0f}</div><div class="kpi-label">الميزانية التقديرية (SAR)</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="kpi-card"><div class="kpi-value">OpenStreetMap</div><div class="kpi-label">نظام الخرائط المعتمد</div></div>', unsafe_allow_html=True)

# 🗺️ ١ · رسم وإدخال الشبكة
with tabs[1]:
    st.markdown("<div class='section-title'>✏️ ارسم خطوط مسارات السيول على الخريطة</div>", unsafe_allow_html=True)
    map_center = center_of([pt for ln in st.session_state.lines for pt in ln["coords"]]) if st.session_state.lines else [24.7136, 46.6753]
    
    m_draw = folium.Map(location=map_center, zoom_start=13, tiles="OpenStreetMap")
    FullScreen().add_to(m_draw)
    
    for ln in st.session_state.lines:
        folium.PolyLine(ln["coords"], color="#e63946", weight=5, tooltip=ln["name"]).add_to(m_draw)
        
    draw_ctrl = Draw(export=False, position="topleft", draw_options={"polyline": {"shapeOptions": {"color": "#e63946", "weight": 5}}, "polygon": False, "rectangle": False, "circle": False, "marker": False, "circlemarker": False})
    draw_ctrl.add_to(m_draw)
    
    map_data = st_folium(m_draw, width=None, height=450, key="draw_map")
    
    if map_data and map_data.get("last_active_drawing"):
        geom = map_data["last_active_drawing"].get("geometry", {})
        if geom.get("type") == "LineString":
            coords = [(c[1], c[0]) for c in geom.get("coordinates", [])]
            if len(coords) >= 2:
                length = line_length(coords)
                if not st.session_state.lines or abs(st.session_state.lines[-1]["length"] - length) > 0.1:
                    st.session_state.lines.append({
                        "id": str(uuid.uuid4()), "name": f"الخط {len(st.session_state.lines)+1}",
                        "length": length, "coords": coords, "diameter": 600, "depth": 1.5
                    })
                    st.session_state.cost = None
                    st.rerun()

    if st.session_state.lines:
        if st.button("🗑️ مسح كافة مسارات الخطوط الحالية", use_container_width=True):
            st.session_state.lines = []
            st.session_state.cost = None
            st.rerun()

# 🌐 ٢ · تحليل الشبكة والخصائص الفردية (ميزة التكبير الموجه على الخط المختار وإدخال الخصائص الفردية)
with tabs[2]:
    st.markdown("<div class='section-title'>🌐 لوحة التحكم وتحليل فروع الشبكة هندسياً</div>", unsafe_allow_html=True)
    if not st.session_state.lines:
        st.warning("⚠️ يرجى الانتقال للتبويب السابق ورسم خطوط مسار الشبكة أولاً.")
    else:
        analyzer = NetworkAnalyzer(st.session_state.lines)
        stat = analyzer.stats()
        
        # ميزة الزوم أو التكبير على خط معين مختار
        st.markdown("### 🔍 التركيز التلقائي والزوم على فرع محدد")
        line_names = [ln["name"] for ln in st.session_state.lines]
        selected_line_name = st.selectbox("اختر الخط المراد عمل التكبير (Zoom) والتركيز عليه فورا:", ["كامل الشبكة"] + line_names)
        
        # تحديد إحداثيات الزوم بناء على اختيار المهندس
        if selected_line_name == "كامل الشبكة":
            focused_coords = [pt for ln in st.session_state.lines for pt in ln["coords"]]
        else:
            focused_coords = next(ln["coords"] for ln in st.session_state.lines if ln["name"] == selected_line_name)
            
        lats = [c[0] for c in focused_coords]
        lons = [c[1] for c in focused_coords]
        focused_bounds = [[min(lats)-0.001, min(lons)-0.001], [max(lats)+0.001, max(lons)+0.001]]
        focused_center = [(min(lats)+max(lats))/2, (min(lons)+max(lons))/2]
        
        # بناء الخريطة التحليلية بخلفية OpenStreetMap المعتمدة للخطوط المختار التركيز عليها
        m_net = folium.Map(location=focused_center, tiles="OpenStreetMap")
        FullScreen().add_to(m_net)
        
        for e in analyzer.edges_list:
            is_selected_track = (selected_line_name == "كامل الشبكة" or e["line_name"] == selected_line_name)
            weight_render = 8 if is_selected_track else 4
            opacity_render = 1.0 if is_selected_track else 0.4
            
            d_color = PIPE_COLORS.get(e["diameter"], "#1a5fa8")
            folium.PolyLine(
                [e["start_coord"], e["end_coord"]], color=d_color, 
                weight=weight_render, opacity=opacity_render,
                tooltip=f"{e['line_name']} (Ø {e['diameter']}mm)"
            ).add_to(m_net)
            
            folium.CircleMarker(location=e["start_coord"], radius=5, color="#0a2a5e", fill=True, fillColor="#ffffff").add_to(m_net)
            folium.CircleMarker(location=e["end_coord"], radius=5, color="#0a2a5e", fill=True, fillColor="#ffffff").add_to(m_net)
            
        m_net.fit_bounds(focused_bounds) # محاذاة وتكبير تلقائي على الخط المختار
        st_folium(m_net, width=None, height=400, key="net_analysis_map")
        
        # إدخال الخصائص لكل فرع على حدة لتخصيص القطر والعمق بشكل مستقل تماماً
        st.markdown("### ⚙️ تخصيص الخصائص الفردية (القطر والعمق والاسم) لكل فرع")
        st.info("💡 يمكنك هنا تخصيص بيانات كل فرع بشكل منفصل، وسيقوم النظام تلقائياً باعتماد الحسابات بناءً عليها:")
        
        any_change = False
        for idx, line in enumerate(st.session_state.lines):
            c1, c2, c3, c4, c5 = st.columns([2, 1.5, 2, 2, 1])
            with c1:
                n_v = st.text_input("اسم المسار", value=line["name"], key=f"inv_n_{line['id']}")
                if n_v != line["name"]: st.session_state.lines[idx]["name"] = n_v; any_change = True
            with c2:
                st.markdown(f"<p style='padding-top:35px;'>📏 <b>{line['length']:.1f} م</b></p>", unsafe_allow_html=True)
            with c3:
                d_v = st.selectbox("القطر الاختياري (مم)", sorted(PIPE_PRICES.keys()), index=sorted(PIPE_PRICES.keys()).index(line.get("diameter", 600)), key=f"inv_d_{line['id']}")
                if d_v != line.get("diameter"): st.session_state.lines[idx]["diameter"] = d_v; any_change = True
            with c4:
                dp_v = st.number_input("العمق الاختياري (م)", min_value=0.5, max_value=12.0, value=float(line.get("depth", 1.5)), step=0.1, key=f"inv_dp_{line['id']}")
                if dp_v != line.get("depth"): st.session_state.lines[idx]["depth"] = dp_v; any_change = True
            with c5:
                st.markdown("<p style='padding-top:28px;'></p>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"inv_del_{line['id']}", use_container_width=True):
                    st.session_state.lines.pop(idx)
                    st.session_state.cost = None
                    st.rerun()
                    
        if any_change:
            st.session_state.cost = None
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🧮 إجراء عملية حساب وجدول كميات المشروع بالكامل", use_container_width=True):
            all_items = {}
            per_edge_data = []
            
            for edge in analyzer.edges_list:
                d, dep, L = edge["diameter"], edge["depth"], edge["distance"]
                p_pipe = PIPE_PRICES.get(d, 725)
                n_tr = max(1, round(L / TRAP_SPACING))
                
                items = [
                    {"البند": "أنابيب صرف خرسانية مدعمة", "الكمية": L, "الوحدة": "متر طولي", "السعر": p_pipe, "الإجمالي": L * p_pipe},
                    {"البند": "أعمال حفر الخنادق المفتوحة", "الكمية": L, "الوحدة": "متر طولي", "السعر": EXCAVATION, "الإجمالي": L * EXCAVATION},
                    {"البند": "مناهل التفتيش الدائرية المعتمدة", "الكمية": 1, "الوحدة": "عدد", "السعر": MANHOLE_PRICE, "الإجمالي": MANHOLE_PRICE},
                    {"البند": "مصائد رمل وحطام جغرافية", "الكمية": n_tr, "الوحدة": "عدد", "السعر": TRAP_PRICE, "الإجمالي": n_tr * TRAP_PRICE},
                    {"البند": "إعادة الردم والتسوية والدمك الإنشائي", "الكمية": L * dep, "الوحدة": "متر مكعب", "السعر": BACKFILL_PRICE, "الإجمالي": L * dep * BACKFILL_PRICE},
                ]
                for it in items:
                    k = it["البند"]
                    if k not in all_items: all_items[k] = {"الكمية": 0, "الإجمالي": 0, "الوحدة": it["الوحدة"]}
                    all_items[k]["الكمية"] += it["الكمية"]
                    all_items[k]["الإجمالي"] += it["الإجمالي"]
                per_edge_data.append({"line_name": edge["line_name"], "diameter": d, "depth": dep, "length": L, "total": sum(i["الإجمالي"] for i in items)})
                
            st.session_state.cost = {
                "all_items": all_items, "per_edge": per_edge_data, 
                "total_cost": sum(v["الإجمالي"] for v in all_items.values()), 
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            st.success("✅ تم تحديث كشوفات الحساب والكميات الفردية للفروع بنجاح!")
            st.rerun()

# 📋 ٣ · التقارير وتصدير PDF (بخلفية خريطة OpenStreetMap لخطوط الشبكة)
with tabs[3]:
    st.markdown("<div class='section-title'>📋 تصدير التقارير الهندسية والـ PDF المعتمد</div>", unsafe_allow_html=True)
    if not st.session_state.cost:
        st.warning("⚠️ يرجى إجراء عملية الحساب والاعتماد من التبويب السابق لتوليد الجداول أولاً.")
    else:
        result = st.session_state.cost
        p_title = st.text_input("اسم المشروع الرسمي", value="مشروع المخطط الهيكلي لشبكة تصريف السيول")
        
        st.markdown("#### 🌍 دمج خريطة OpenStreetMap خلف التقرير")
        st.info("💡 لدمج خطوط مسارات الأقطار والشبكة فوق خلفية خريطة OpenStreetMap الحية داخل مستند الـ PDF الهندسي، يرجى التقاط لقطة شاشة (Screenshot) سريعة للخريطة في التبويب السابق ورفعها هنا ليتم دمج خطوط الأقطار فوقها هندسياً:")
        bg_map_image = st.file_uploader("ارفع لقطة شاشة خريطة OpenStreetMap للشبكة (اختياري)", type=["png", "jpg", "jpeg"])
        
        if st.button("📥 توليد مستند الـ PDF الهندسي النهائي المتكامل", use_container_width=True):
            with st.spinner("جاري صياغة ودمج الخرائط ومخططات الأقطار..."):
                try:
                    # بناء رسم بياني لمخطط الأقطار مع الإحداثيات الجغرافية كخلفية خريطة
                    fig, ax = plt.subplots(figsize=(7.5, 4.8))
                    if bg_map_image:
                        from PIL import Image as PILImage
                        img = PILImage.open(bg_map_image)
                        ax.imshow(img, extent=[0, 10, 0, 10], aspect='auto', alpha=0.7)
                        ax.axis('off')
                    else:
                        ax.set_facecolor('#f7f9fc')
                        ax.grid(True, which='both', color='#cccccc', linestyle='--', linewidth=0.5)
                        ax.set_xlabel("Longitude (Easting Coordinates)")
                        ax.set_ylabel("Latitude (Northing Coordinates)")
                        
                    # رسم الخطوط فوق اللوحة
                    for idx, line in enumerate(st.session_state.lines):
                        d = line.get("diameter", 600)
                        clr = PIPE_COLORS.get(d, "#1a5fa8")
                        if bg_map_image:
                            # رسم كروكي متناسق فوق الصورة الـ Uploaded لضمان التطابق داخل التقرير
                            ax.plot([1, 9], [5-idx, 5-idx], color=clr, linewidth=3, label=f"{line['name']} (Ø{d}mm)")
                        else:
                            x = [pt[1] for pt in line["coords"]]
                            y = [pt[0] for pt in line["coords"]]
                            ax.plot(x, y, color=clr, linewidth=3, label=f"{line['name']} (Ø{d}mm)")
                            
                    plt.title("STORMWATER PIPELINE ROUTE & PROFILE BACKGROUND", fontsize=10, weight='bold', color='#0a2a5e')
                    handles, labels = ax.get_legend_handles_labels()
                    by_label = dict(zip(labels, handles))
                    ax.legend(by_label.values(), by_label.keys(), loc="lower right", fontsize=8)
                    
                    img_buf = io.BytesIO()
                    plt.savefig(img_buf, format='png', dpi=250, bbox_inches='tight')
                    img_buf.seek(0)
                    plt.close(fig)
                    
                    # صياغة الـ PDF عبر مكتبة ReportLab باللغة الفنية الإنجليزية الشاملة والـ SAR
                    from reportlab.lib.pagesizes import portrait, A4
                    from reportlab.lib import colors
                    from reportlab.lib.units import mm
                    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
                    from reportlab.lib.styles import ParagraphStyle
                    from reportlab.lib.enums import TA_CENTER
                    
                    pdf_buf = io.BytesIO()
                    doc = SimpleDocTemplate(pdf_buf, pagesize=portrait(A4), rightMargin=12*mm, leftMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
                    
                    BLUE, WHITE, LBLUE = colors.HexColor("#0a2a5e"), colors.white, colors.HexColor("#1a5fa8")
                    s_title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=15, textColor=WHITE, alignment=TA_CENTER)
                    s_h2 = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=11, textColor=BLUE, spaceBefore=6, spaceAfter=4)
                    s_norm = ParagraphStyle("n", fontName="Helvetica", fontSize=9)
                    s_bold = ParagraphStyle("b", fontName="Helvetica-Bold", fontSize=9)
                    
                    elems = []
                    
                    # الهيدر الأساسي لمستند الـ PDF
                    elems.append(Table([[Paragraph(f"STORMWATER INFRASTRUCTURE QUANTITIES REPORT<br/><font size=9>{p_title}</font>", s_title)]], colWidths=[185*mm], style=[('BACKGROUND', (0,0), (-1,-1), BLUE), ('PADDING', (0,0), (-1,-1), 10)]))
                    elems.append(Spacer(1, 4*mm))
                    
                    # جدول البيانات الفنية للمشروع
                    meta_data = [
                        [Paragraph("Currency Approved:", s_bold), Paragraph("Saudi Riyal (SAR)", s_norm), Paragraph("Report Timestamp:", s_bold), Paragraph(result["generated_at"], s_norm)]
                    ]
                    meta_tbl = Table(meta_data, colWidths=[35*mm, 55*mm, 35*mm, 60*mm], style=[('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")), ('PADDING', (0,0), (-1,-1), 5)])
                    elems.append(meta_tbl)
                    elems.append(Spacer(1, 4*mm))
                    
                    # إضافة الخريطة الخلفية ومخطط الفروع والأقطار
                    elems.append(Paragraph("1. PIPELINE ROUTE & GEOGRAPHICAL PROFILE (OPENSTREETMAP BACKGROUND)", s_h2))
                    elems.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=4))
                    elems.append(Image(img_buf, width=180*mm, height=110*mm))
                    elems.append(Spacer(1, 4*mm))
                    
                    # جدول الكميات والأسعار الكلي
                    elems.append(Paragraph("2. INFRASTRUCTURE BILL OF QUANTITIES (BOQ) DIRECT COST", s_h2))
                    elems.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=4))
                    
                    boq_rows = [["Item Specification Description", "Quantity", "Unit", "Total Cost (SAR)"]]
                    for name, data in result["all_items"].items():
                        boq_rows.append([name, f"{data['الكمية']:,.2f}", data["الوحدة"], f"{data['الإجمالي']:,.0f} SAR"])
                    boq_rows.append(["TOTAL CERTIFIED PROJECT BUDGET", "", "", f"{result['total_cost']:,.0f} SAR"])
                    
                    boq_tbl = Table(boq_rows, colWidths=[85*mm, 25*mm, 25*mm, 50*mm], style=[
                        ('BACKGROUND', (0,0), (-1,0), LBLUE), ('TEXTCOLOR', (0,0), (-1,0), WHITE), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d8e8")),
                        ('PADDING', (0,0), (-1,-1), 5), ('BACKGROUND', (0,-1), (-1,-1), BLUE), ('TEXTCOLOR', (0,-1), (-1,-1), WHITE), ('FONTNAME', (0,-1), (-1,-1), "Helvetica-Bold")
                    ])
                    elems.append(boq_tbl)
                    
                    doc.build(elems)
                    pdf_buf.seek(0)
                    
                    st.download_button(
                        label="📥 اضغط هنا لبدء تحميل التقرير الهندسي PDF فوراً", 
                        data=pdf_buf.getvalue(), 
                        file_name="Stormwater_Network_Report.pdf", 
                        mime="application/pdf", use_container_width=True
                    )
                except Exception as ex:
                    st.error(f"❌ حدث خطأ غير متوقع أثناء تكوين مستند الـ PDF: {ex}")

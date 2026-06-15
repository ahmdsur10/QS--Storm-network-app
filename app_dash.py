# ══════════════════════════════════════════════════════════════════
#  حاسبة تكلفة شبكات تصريف السيول — Streamlit Version
#  Eng. Ahmed Adam | 2025
# ══════════════════════════════════════════════════════════════════
import streamlit as st
import json, math, os, tempfile, zipfile, base64
from io import BytesIO
import pandas as pd

# ضبط إعدادات الصفحة في ستريمليت وتفعيل الاتجاه العربي (RTL)
st.set_page_config(page_title="حاسبة شبكات السيول", layout="wide", initial_sidebar_state="collapsed")
st.markdown('<style>body{direction: rtl; text-align: right;}</style>', unsafe_allow_html=True)

# ══ الأسعار وثوابت الشبكة ══
PIPE_PRICES = {
    400:2713, 500:2935, 600:3145, 700:3431, 800:4009,
    900:4299, 1000:4625, 1100:5010, 1200:5335, 1300:5725, 1400:6055,
}
BOX_CHANNEL_PRICE  = 9336.0
OPEN_CHANNEL_PRICE = 13052.0
LINE_TYPES = {"pipe":"أنبوب", "box_channel":"قناة صندوقية", "open_channel":"قناة مفتوحة"}

# ══ دوال حسابية ══
def hav(lon1, lat1, lon2, lat2):
    R = 6371000; p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin(math.radians(lat2-lat1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(lon2-lon1)/2)**2
    return 2 * R * math.asin(math.sqrt(max(0, a)))

def length_m(coords):
    t = 0.0
    for i in range(len(coords)-1):
        try: t += hav(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
        except: pass
    return t

def length_proj(coords):
    t = 0.0
    for i in range(len(coords)-1):
        dx = coords[i+1][0]-coords[i][0]; dy = coords[i+1][1]-coords[i][1]
        t += math.sqrt(dx*dx + dy*dy)
    return t

def is_proj(c): return bool(c) and (abs(c[0][0])>180 or abs(c[0][1])>90)

def get_price(lt, dia=None, cp=None):
    if cp and cp > 0: return float(cp)
    if lt == "box_channel": return BOX_CHANNEL_PRICE
    if lt == "open_channel": return OPEN_CHANNEL_PRICE
    if dia and dia in PIPE_PRICES: return float(PIPE_PRICES[dia])
    if dia: return float(PIPE_PRICES[min(PIPE_PRICES, key=lambda x:abs(x-dia))])
    return float(PIPE_PRICES[1400])

def parse_geom(geom):
    if not geom: return []
    t = geom.get("type",""); raw = geom.get("coordinates",[])
    pts = raw if t=="LineString" else [p for part in raw for p in part] if t=="MultiLineString" else []
    return [[float(c[0]), float(c[1])] for c in pts if isinstance(c,(list,tuple)) and len(c)>=2]

def convert_wgs84(coords, epsg=32637):
    try:
        from pyproj import Transformer
        tr = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        return [[lon, lat] for lon, lat in (tr.transform(x, y) for x, y in coords)]
    except: return coords

def sanitize_props(props):
    clean = {}
    for k, v in props.items():
        try:
            if v is None: clean[str(k)] = None
            elif isinstance(v, (int, float, bool, str)): clean[str(k)] = v
            else: clean[str(k)] = str(v)
        except: pass
    return clean

def load_geojson(uploaded_file):
    try:
        gj = json.loads(uploaded_file.read().decode("utf-8", "ignore"))
        crs = gj.get("crs",{}); epsg = None
        if crs:
            name = crs.get("properties",{}).get("name","")
            if "EPSG:" in name.upper():
                try: epsg = int(name.upper().split("EPSG:")[-1].strip().split()[0])
                except: pass
        feats = []
        for i, f in enumerate(gj.get("features", [])):
            if not isinstance(f, dict): continue
            coords = parse_geom(f.get("geometry") or {})
            if len(coords) < 2: continue
            props = sanitize_props(f.get("properties") or {})
            if is_proj(coords):
                length = round(length_proj(coords), 2)
                coords = convert_wgs84(coords, epsg or 32637)
            else: length = round(length_m(coords), 2)
            feats.append({"i": i, "len": length, "coords": coords, "props": props})
        return feats
    except Exception as e:
        st.error(f"خطأ في قراءة GeoJSON: {e}"); return []

def load_shapefile(uploaded_file):
    try:
        import shapefile
        with tempfile.TemporaryDirectory() as td:
            with zipfile.ZipFile(BytesIO(uploaded_file.read())) as z: z.extractall(td)
            shp = next((os.path.join(r, f) for r, _, fs in os.walk(td) for f in fs if f.lower().endswith(".shp")), None)
            if not shp: return []
            epsg = None
            prj = shp.replace(".shp", ".prj")
            if os.path.exists(prj):
                try:
                    from pyproj import CRS
                    with open(prj, "r", errors="ignore") as pf: ep = CRS.from_wkt(pf.read()).to_epsg()
                    if ep: epsg = ep
                except: pass
            sf = shapefile.Reader(shp); fnames = [f[0] for f in sf.fields[1:]]
            feats = []
            for i, sr in enumerate(sf.shapeRecords()):
                coords = [[float(p[0]), float(p[1])] for p in sr.shape.points if len(p)>=2]
                if len(coords) < 2: continue
                props = sanitize_props(dict(zip(fnames, sr.record)))
                if is_proj(coords):
                    length = round(length_proj(coords), 2)
                    coords = convert_wgs84(coords, epsg or 32637)
                else: length = round(length_m(coords), 2)
                feats.append({"i": i, "len": length, "coords": coords, "props": props})
            return feats
    except Exception as e:
        st.error(f"خطأ في قراءة Shapefile: {e}"); return []

def gen_pdf(segments_data, stot, total_cost):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as rlc
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    FONTB_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        pdfmetrics.registerFont(TTFont("AF", FONT_PATH)); pdfmetrics.registerFont(TTFont("AFB", FONTB_PATH))
        FONT="AF"; FONTB="AFB"
    except: FONT="Helvetica"; FONTB="Helvetica-Bold"
    C = rlc.HexColor; buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    def S(nm,**kw): return ParagraphStyle(nm, parent=styles["Normal"], fontName=FONT, **kw)
    def SB(nm,**kw): return ParagraphStyle(nm, parent=styles["Normal"], fontName=FONTB, **kw)
    story = []
    story.append(Paragraph("Flood Drainage Network Cost Report", SB("t", fontSize=16, textColor=C("#0a2a5e"), alignment=TA_CENTER, spaceAfter=4)))
    story.append(Paragraph("Eng. Ahmed Adam | Flood Drainage Networks 2025", S("s", fontSize=9, textColor=C("#1a5fa8"), alignment=TA_CENTER, spaceAfter=10)))
    story.append(HRFlowable(width="100%", thickness=2, color=C("#1a5fa8"), spaceAfter=10))
    rows = [["Description", "Value"], ["Number of Elements", str(len(segments_data))],
          ["Total Length", "%.2f m / %.3f km"%(stot, stot/1000)],
          ["Total Cost", "%.2f SAR"%total_cost], ["In Millions", "%.4f M SAR"%(total_cost/1e6)]]
    t = Table(rows, colWidths=[7*cm, 10*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), C("#0a2a5e")), ("TEXTCOLOR", (0,0), (-1,0), rlc.white),
        ("FONTNAME", (0,0), (-1,0), FONTB), ("FONTNAME", (0,1), (-1,-1), FONT),
        ("FONTSIZE", (0,0), (-1,-1), 10), ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("BACKGROUND", (0,-1), (-1,-1), C("#1a5fa8")),
        ("TEXTCOLOR", (0,-1), (-1,-1), rlc.white), ("FONTNAME", (0,-1), (-1,-1), FONTB),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [rlc.white, C("#f0f7ff")]),
        ("GRID", (0,0), (-1,-1), .5, C("#d0e4f7")), ("ROWHEIGHT", (0,0), (-1,-1), 22)]))
    story += [t, Spacer(1, 14)]
    story += [HRFlowable(width="100%", thickness=1, color=C("#1a5fa8"), spaceAfter=5),
            Paragraph("Eng. Ahmed Adam | Flood Drainage Networks © 2025", S("ft", fontSize=8, textColor=C("#888"), alignment=TA_CENTER))]
    doc.build(story); return buf.getvalue()

# ══════════════════════════════════════════════════════════════════
# واجهة المستخدم بنظام Streamlit
# ══════════════════════════════════════════════════════════════════
st.title("🌊 حاسبة تكلفة شبكات تصريف السيول")
st.caption("برمجة: م. أحمد آدم | تحليل الشبكات الحسابية وتقدير التكاليف")

# نظام إدارة الرفع للملفات
uploaded_file = st.file_uploader("📂 ارفع ملف بيانات الشبكة (GeoJSON أو Shapefile مضغوط .zip)", type=["geojson", "json", "zip"])

if uploaded_file is not None:
    # قراءة البيانات وتخزينها في جلسة العمل
    if "feats" not in st.session_state:
        ext = uploaded_file.name.lower().rsplit(".", 1)[-1]
        if ext in ("geojson", "json"):
            st.session_state.feats = load_geojson(uploaded_file)
        elif ext == "zip":
            st.session_state.feats = load_shapefile(uploaded_file)
            
    feats = st.session_state.get("feats", [])
    
    if feats:
        st.success(f"✅ تم تحميل {len(feats)} خط بنجاح!")
        
        # إنشاء التبويبات
        tab1, tab2 = st.tabs(["🗺️ إعدادات الحساب والتكاليف", "📊 جدول بيانات المخطط"])
        
        with tab1:
            st.subheader("⚙️ تخصيص أسعار وأنواع خطوط الشبكة")
            
            # مصفوفة لحفظ اختيارات المستخدم لكل خط
            meta_results = {}
            total_length = 0.0
            total_network_cost = 0.0
            segments_summary = []
            
            for f in feats:
                fi = f["i"]
                st.markdown(f"**📍 الخط رقم #{fi} (الطول: {f['len']:,.1f} متر)**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    lt = col1.selectbox("نوع الخط", list(LINE_TYPES.keys()), format_func=lambda x: LINE_TYPES[x], key=f"lt_{fi}")
                with col2:
                    dia = None
                    if lt == "pipe":
                        dia = col2.selectbox("القطر (ملم)", list(PIPE_PRICES.keys()), index=len(PIPE_PRICES)-1, key=f"dia_{fi}")
                with col3:
                    gp = get_price(lt, dia, None)
                    cp = col3.number_input("السعر المخصص (ريال/م)", min_value=0.0, value=float(gp), step=50.0, key=f"cp_{fi}")
                
                # حساب تكلفة الخط الفردي
                line_cost = f["len"] * cp
                total_length += f["len"]
                total_network_cost += line_cost
                
                segments_summary.append({
                    "label": f"#{fi}", "len": f["len"], "line_type": lt,
                    "diameter_mm": dia, "price_per_m": cp, "cost": line_cost
                })
                st.caption(f"💰 التكلفة المقدرة لهذا الخط: **{line_cost:,.2f} ريال**")
                st.markdown("---")
            
            # عرض النتائج الكلية
            st.subheader("📊 ملخص التكلفة الإجمالي للشبكة")
            c1, c2, c3 = st.columns(3)
            c1.metric("إجمالي الأطوال (متر)", f"{total_length:,.2f} م")
            c2.metric("التكلفة الإجمالية (ريال)", f"{total_network_cost:,.2f} ريال")
            c3.metric("التكلفة بالملايين", f"{total_network_cost/1e6:.3f} مليون ريال")
            
            # زر طباعة التقرير PDF
            if st.button("📄 تصدير تقرير PDF معتمد"):
                try:
                    pdf_data = gen_pdf(segments_summary, total_length, total_network_cost)
                    st.download_button(label="📥 تحميل ملف الـ PDF", data=pdf_data, file_name="flood_drainage_report.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"حدث خطأ أثناء إعداد PDF: {e}")
                    
        with tab2:
            st.subheader("📋 الجدول التفصيلي للبيانات والخصائص")
            rows = []
            for f in feats:
                r = {"رقم الخط": f["i"], "الطول (م)": round(f["len"], 2), "الطول (كم)": round(f["len"]/1000, 4)}
                r.update({str(k): v for k, v in f["props"].items()})
                rows.append(r)
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.warning("⚠️ لم يتم العثور على خطوط هندسية صالحة في الملف المرفوع.")

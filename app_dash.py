import streamlit as st
import math
import os
import io
import json
import zipfile
from datetime import datetime

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

st.set_page_config(page_title="حاسبة شبكات السيول", page_icon="🌊",
                   layout="wide", initial_sidebar_state="collapsed",
                   menu_items={'Get Help': None, 'Report a bug': None, 'About': None})

PIPE_PRICES = {
    400: 454, 500: 619, 600: 725, 700: 906, 800: 1045,
    900: 1225, 1000: 1440, 1100: 1600, 1200: 1812, 1300: 1920, 1400: 2132,
}

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

.res{background:linear-gradient(135deg,#0a2a5e,#1a5fa8);color:#fff!important;padding:14px 16px;
  border-radius:12px;font-size:.88rem;font-weight:700;text-align:center;
  box-shadow:0 4px 14px rgba(26,95,168,.3);margin-top:8px;line-height:2.1}

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

.stTextInput>div>div>input,.stNumberInput>div>div>input{min-height:48px!important;font-size:1rem!important;
  font-family:'Cairo',sans-serif!important;direction:rtl!important;border-radius:10px!important}
.stSelectbox [data-baseweb="select"]>div{min-height:48px!important;font-family:'Cairo',sans-serif!important;border-radius:10px!important}
.stRadio label{font-size:.85rem!important}
.stFileUploader label{font-size:.88rem!important;font-weight:700!important;color:#0a2a5e!important}
.stFileUploader [data-testid="stFileUploaderDropzone"]{border-radius:10px!important}

.stTabs [data-baseweb="tab-list"]{gap:2px!important;flex-wrap:wrap!important}
.stTabs [data-baseweb="tab"]{font-family:'Cairo',sans-serif!important;font-weight:700!important;
  font-size:.82rem!important;padding:9px 10px!important;min-height:42px!important;white-space:nowrap!important}

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

.src-badge{display:inline-block;background:#eaf4ff;color:#0a2a5e;border:1px solid #b8d9f8;
  border-radius:20px;padding:4px 12px;font-size:.72rem;font-weight:700;margin-bottom:8px}

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
  .stTabs [data-baseweb="tab"]{font-size:.74rem!important;padding:8px 7px!important;min-height:38px!important}
  .cost-table{font-size:.74rem}
  .cost-table th,.cost-table td{padding:6px 5px}
  .map-info,.warn-box{font-size:.76rem;padding:8px 10px}
  div[data-testid="column"]{min-width:100%!important;flex:1 1 100%!important}
}
</style>"""


def check_credentials(u, p):
    try:
        users = st.secrets["users"]
        return users.get(u) == p
    except Exception:
        return False


def login_page():
    st.markdown(MAIN_CSS, unsafe_allow_html=True)
    st.markdown("""<style>
.stApp{background:linear-gradient(135deg,#050e1f,#091830,#0d2447)!important}
.block-container{max-width:420px!important;padding-top:2rem!important}
.stTextInput>div>div>input{background:rgba(255,255,255,.07)!important;
  border:1.5px solid rgba(255,255,255,.15)!important;color:#fff!important}
.stTextInput label{color:rgba(200,225,255,.9)!important;font-weight:600!important}
</style>""", unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;font-size:3.2rem;margin:20px 0 4px">🌊</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;color:#fff;font-size:1.3rem;font-weight:900;margin-bottom:4px">حاسبة شبكات تصريف السيول</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;color:rgba(180,210,255,.65);font-size:.78rem;margin-bottom:24px">مع خرائط تفاعلية ودعم SHP/GeoJSON · Eng. Ahmed Adam</div>', unsafe_allow_html=True)
    st.markdown('<hr style="border-color:rgba(26,95,168,.4);margin-bottom:20px">', unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("اسم المستخدم", placeholder="أدخل اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password", placeholder="• • • • • • • •")
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🔑  تسجيل الدخول", use_container_width=True)

    if submitted:
        if check_credentials(username.strip(), password):
            st.session_state.update({"authenticated": True, "current_user": username.strip()})
            st.rerun()
        else:
            st.error("❌  اسم المستخدم أو كلمة المرور غير صحيحة")


if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if not st.session_state["authenticated"]:
    login_page()
    st.stop()

st.markdown(MAIN_CSS, unsafe_allow_html=True)

# ── Session State ──
DEFAULTS = {
    "drawn_line_length": 0.0,
    "drawn_coords": [],
    "line_source": None,
    "detailed_calc": None,
    "cost_result": None,
    "active_length_tab2": 1000.0,
    "active_length_tab3": 1000.0,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

RLAT, RLON = 24.7136, 46.6753

# ═════════════════════════════════════════════════════════════════════════════════
# ──── دوال حساب المسافة والإحداثيات ────
# ═════════════════════════════════════════════════════════════════════════════════


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def calculate_line_length(coords):
    if len(coords) < 2:
        return 0.0
    total_length = 0.0
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        total_length += haversine_distance(lat1, lon1, lat2, lon2)
    return total_length


def extract_coordinates_from_geojson_geometry(geometry):
    if not geometry:
        return []
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    lines = []

    if gtype == "LineString":
        lines.append([(c[1], c[0]) for c in coords])
    elif gtype == "MultiLineString":
        for part in coords:
            lines.append([(c[1], c[0]) for c in part])
    elif gtype == "GeometryCollection":
        for geom in geometry.get("geometries", []):
            lines.extend(extract_coordinates_from_geojson_geometry(geom))
    return lines


def parse_geojson_file(file_bytes):
    try:
        data = json.loads(file_bytes.decode("utf-8"))
    except Exception as e:
        return [], f"تعذّرت قراءة الملف كـ GeoJSON صحيح: {e}"

    lines = []
    if data.get("type") == "FeatureCollection":
        for feat in data.get("features", []):
            lines.extend(extract_coordinates_from_geojson_geometry(feat.get("geometry")))
    elif data.get("type") == "Feature":
        lines.extend(extract_coordinates_from_geojson_geometry(data.get("geometry")))
    else:
        lines.extend(extract_coordinates_from_geojson_geometry(data))

    if not lines:
        return [], "لم يتم العثور على أي خطوط (LineString) داخل ملف GeoJSON."
    return lines, None


def parse_shapefile_zip(file_bytes):
    if not SHAPEFILE_AVAILABLE:
        return [], "مكتبة قراءة الشيب فايل (pyshp) غير مثبتة في هذه البيئة."

    try:
        zf = zipfile.ZipFile(io.BytesIO(file_bytes))
    except zipfile.BadZipFile:
        return [], "الملف المرفوع ليس أرشيف ZIP صحيحاً."

    names = zf.namelist()
    shp_names = [n for n in names if n.lower().endswith(".shp")]
    if not shp_names:
        return [], "لم يُعثر على ملف .shp داخل الأرشيف. تأكد من ضغط shp و shx و dbf معاً."

    shp_name = shp_names[0]
    base = shp_name[:-4]
    try:
        shp_io = io.BytesIO(zf.read(base + ".shp"))
        shx_io = io.BytesIO(zf.read(base + ".shx")) if (base + ".shx") in names else None
        dbf_io = io.BytesIO(zf.read(base + ".dbf")) if (base + ".dbf") in names else None
        prj_name = base + ".prj"
        has_prj = prj_name in names
    except KeyError as e:
        return [], f"ملف ناقص داخل الأرشيف: {e}"

    try:
        sf = shapefile.Reader(shp=shp_io, shx=shx_io, dbf=dbf_io)
    except Exception as e:
        return [], f"تعذّرت قراءة الشيب فايل: {e}"

    if sf.shapeType not in (shapefile.POLYLINE, shapefile.POLYLINEZ, shapefile.POLYLINEM):
        return [], "نوع الشكل في الشيب فايل ليس خطاً (Polyline) — تأكد من رفع طبقة خطوط."

    warning = None
    if not has_prj:
        warning = (
            "⚠️ لا يوجد ملف .prj (نظام الإسناد الإحداثي) داخل الأرشيف. "
            "تم افتراض أن الإحداثيات بنظام WGS84 (خطوط الطول والعرض)؛ "
            "إن كانت بنظام UTM أو غيره ستكون نتيجة الطول غير صحيحة."
        )

    lines = []
    for shape_rec in sf.shapeRecords():
        pts = shape_rec.shape.points
        if not pts:
            continue
        parts = list(shape_rec.shape.parts) + [len(pts)]
        for i in range(len(parts) - 1):
            segment = pts[parts[i]:parts[i + 1]]
            lines.append([(p[1], p[0]) for p in segment])

    if not lines:
        return [], "لم يتم العثور على أي إحداثيات داخل طبقة الخطوط."

    return lines, warning


def coords_look_valid(all_lines):
    for line in all_lines:
        for lat, lon in line:
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return False
    return True


def load_excel_formulas():
    formulas = {}
    for diameter, pipe_price in PIPE_PRICES.items():
        formulas[diameter] = {
            'pipe_price': pipe_price,
            'excavation_price': 130,
            'backfill_price': 90 if diameter == 400 else 110,
            'gravel_price': 320,
        }
    return formulas


def calculate_pipe_details(pipe_length, diameter_mm, avg_depth, num_traps=None, num_manholes=None):
    warnings = []
    try:
        diameter_m = diameter_mm / 1000

        if diameter_mm >= 1300:
            trench_width = diameter_m + 1.0
        elif diameter_mm >= 800:
            trench_width = diameter_m + 0.85
        else:
            trench_width = diameter_m + 0.7

        min_required_depth = diameter_m + 0.3
        if avg_depth < min_required_depth:
            warnings.append(
                f"⚠️ متوسط العمق ({avg_depth:.2f} م) أقل من الحد الأدنى المقترح "
                f"({min_required_depth:.2f} م) لهذا القطر — تحقق من القيمة."
            )

        excavation_qty = pipe_length * avg_depth * trench_width

        pipe_volume = math.pi * ((diameter_m / 2) ** 2) * pipe_length
        pipe_half_volume = pipe_volume / 2

        backfill_qty = pipe_length * trench_width * max(avg_depth - diameter_m, 0)
        final_backfill = backfill_qty - pipe_half_volume

        gravel_depth = 0.2 + (diameter_m / 2)
        gravel_volume = gravel_depth * pipe_length * trench_width
        final_gravel = gravel_volume - pipe_half_volume

        if final_backfill < 0:
            warnings.append("⚠️ كمية الردم المحسوبة كانت سالبة وتم تصحيحها إلى صفر؛ تحقق من العمق والقطر المدخلين.")
            final_backfill = 0.0
        if final_gravel < 0:
            warnings.append("⚠️ حجم البحص المحسوب كان سالباً وتم تصحيحه إلى صفر؛ تحقق من العمق والقطر المدخلين.")
            final_gravel = 0.0

        if num_traps is None:
            num_traps = max(1, round(pipe_length / 35))
        trap_lengths = num_traps * 7

        if num_manholes is None:
            num_manholes = max(1, int(pipe_length / 100))
        manhole_depth_increase = num_manholes * 1.0

        result = {
            'pipe_length': pipe_length,
            'diameter_mm': diameter_mm,
            'avg_depth': avg_depth,
            'trench_width': trench_width,
            'excavation_qty': excavation_qty,
            'final_backfill': final_backfill,
            'final_gravel': final_gravel,
            'num_traps': num_traps,
            'trap_lengths': trap_lengths,
            'num_manholes': num_manholes,
            'manhole_depth_increase': manhole_depth_increase,
        }
        return result, warnings
    except Exception as e:
        st.error(f"خطأ في الحساب: {e}")
        return None, warnings


def generate_cost_report(calc_data, prices):
    try:
        items = [
            {'name': '1. أطوال الأنابيب', 'unit': 'م', 'qty': calc_data['pipe_length'], 'price': prices.get('pipe_price', 0)},
            {'name': '2. كمية الحفر', 'unit': 'م³', 'qty': calc_data['excavation_qty'], 'price': prices.get('excavation_price', 130)},
            {'name': '3. كمية الردم', 'unit': 'م³', 'qty': calc_data['final_backfill'], 'price': prices.get('backfill_price', 110)},
            {'name': '4. حجم البحص', 'unit': 'م³', 'qty': calc_data['final_gravel'], 'price': prices.get('gravel_price', 320)},
            {'name': '5. عدد المصائد', 'unit': 'عدد', 'qty': calc_data['num_traps'], 'price': 9000},
            {'name': '6. أطوال المصائد', 'unit': 'م', 'qty': calc_data['trap_lengths'], 'price': 500},
            {'name': '7. عدد المناهل', 'unit': 'عدد', 'qty': calc_data['num_manholes'], 'price': 20000},
            {'name': '8. زيادة أعماق المناهل', 'unit': 'م', 'qty': calc_data['manhole_depth_increase'], 'price': 5000},
        ]
        report_items = []
        total_cost = 0
        for item in items:
            cost = item['qty'] * item['price']
            report_items.append({**item, 'total': cost})
            total_cost += cost
        return {'items': report_items, 'total': total_cost}
    except Exception as e:
        st.error(f"خطأ في التقرير: {e}")
        return None


def build_csv(report, include_unit=False):
    if include_unit:
        lines = ["البند,الكمية,الوحدة,السعر,الإجمالي"]
        for item in report['items']:
            lines.append(f'"{item["name"]}",{item["qty"]:.2f},{item["unit"]},{item["price"]:.0f},{item["total"]:.0f}')
        lines.append(f"المجموع,,,,{report['total']:.0f}")
    else:
        lines = ["البند,الكمية,السعر,الإجمالي"]
        for item in report['items']:
            lines.append(f'"{item["name"]}",{item["qty"]:.2f},{item["price"]:.0f},{item["total"]:.0f}')
        lines.append(f"المجموع,,,{report['total']:.0f}")
    return "\n".join(lines) + "\n"


def render_cost_table(report):
    table_html = '<table class="cost-table"><thead><tr><th>البند</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr></thead><tbody>'
    for item in report['items']:
        unit = item.get('unit', '')
        table_html += f'<tr><td>{item["name"]}</td><td>{item["qty"]:,.2f} {unit}</td><td>{item["price"]:,.0f}</td><td>{item["total"]:,.0f}</td></tr>'
    table_html += f'<tr class="total"><td colspan="3">المجموع الإجمالي</td><td>{report["total"]:,.0f}</td></tr></tbody></table>'
    st.markdown(table_html, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════════
# ──── إنشاء تقرير PDF ────
# ═════════════════════════════════════════════════════════════════════════════════

_ARABIC_FONTS_REGISTERED = False


def _register_arabic_fonts():
    global _ARABIC_FONTS_REGISTERED
    if _ARABIC_FONTS_REGISTERED:
        return True
    reg_path = os.path.join(FONTS_DIR, "NotoNaskhArabic-Regular.ttf")
    bold_path = os.path.join(FONTS_DIR, "NotoNaskhArabic-Bold.ttf")
    if not (os.path.exists(reg_path) and os.path.exists(bold_path)):
        return False
    pdfmetrics.registerFont(RLFont("ArabicReg", reg_path))
    pdfmetrics.registerFont(RLFont("ArabicBold", bold_path))
    _ARABIC_FONTS_REGISTERED = True
    return True


def ar(text):
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def build_pdf_report(calc, report, meta=None):
    if not PDF_AVAILABLE:
        return None
    if not _register_arabic_fonts():
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm, leftMargin=15 * mm, rightMargin=15 * mm,
    )

    title_style = ParagraphStyle(
        "title", fontName="ArabicBold", fontSize=16, alignment=1,
        textColor=colors.HexColor("#0a2a5e"), spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "subtitle", fontName="ArabicReg", fontSize=9.5, alignment=1,
        textColor=colors.HexColor("#5a6b85"), spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "section", fontName="ArabicBold", fontSize=12.5, alignment=2,
        textColor=colors.HexColor("#0a2a5e"), spaceBefore=12, spaceAfter=6,
    )
    normal_style = ParagraphStyle(
        "normal", fontName="ArabicReg", fontSize=10, alignment=2, leading=15,
    )

    story = []
    story.append(Paragraph(ar("تقرير حساب تكاليف شبكة تصريف السيول"), title_style))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(ar(f"تاريخ التقرير: {now_str}"), subtitle_style))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#1a5fa8"), thickness=1.2))
    story.append(Spacer(1, 6 * mm))

    if meta and meta.get("source"):
        story.append(Paragraph(ar(f"مصدر مسار الأنبوب: {meta['source']}"), normal_style))
        story.append(Spacer(1, 3 * mm))

    story.append(Paragraph(ar("بيانات المشروع"), section_style))
    summary_rows = [
        [str(round(calc["pipe_length"], 1)), ar("طول الأنبوب (م)")],
        [str(calc["diameter_mm"]), ar("قطر الأنبوب (ملم)")],
        [str(round(calc["avg_depth"], 2)), ar("متوسط العمق (م)")],
        [str(round(calc["trench_width"], 2)), ar("عرض الخندق (م)")],
        [str(calc["num_traps"]), ar("عدد المصائد")],
        [str(calc["num_manholes"]), ar("عدد المناهل")],
    ]
    summary_table = Table(summary_rows, colWidths=[60 * mm, 110 * mm])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'ArabicReg'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#d0e4f7")),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor("#f8fbfe"), colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph(ar("تفاصيل التكاليف"), section_style))
    table_data = [[ar("الإجمالي (ريال)"), ar("السعر"), ar("الكمية"), ar("الوحدة"), ar("البند")]]
    for item in report["items"]:
        table_data.append([
            f"{item['total']:,.0f}",
            f"{item['price']:,.0f}",
            f"{item['qty']:,.2f}",
            ar(item["unit"]),
            ar(item["name"]),
        ])
    table_data.append([f"{report['total']:,.0f}", "", "", "", ar("المجموع الإجمالي")])

    cost_table = Table(table_data, colWidths=[32 * mm, 25 * mm, 28 * mm, 18 * mm, 67 * mm], repeatRows=1)
    cost_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'ArabicReg'),
        ('FONTNAME', (0, 0), (-1, 0), 'ArabicBold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0a2a5e")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -2), 0.4, colors.HexColor("#d0e4f7")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fbfe")]),
        ('SPAN', (0, -1), (0, -1)),
        ('SPAN', (1, -1), (3, -1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#0a2a5e")),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'ArabicBold'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(cost_table)
    story.append(Spacer(1, 8 * mm))

    footer_style = ParagraphStyle(
        "footer", fontName="ArabicReg", fontSize=8, alignment=1, textColor=colors.HexColor("#999999"),
    )
    story.append(HRFlowable(width="100%", color=colors.HexColor("#d0e4f7"), thickness=0.8))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(ar("© حاسبة شبكات تصريف السيول مع الخرائط التفاعلية"), footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ═════════════════════════════════════════════════════════════════════════════════
# ──── الواجهة الرئيسية ────
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="hdr"><h1>🌊 حاسبة شبكات تصريف السيول مع الخرائط التفاعلية</h1><div class="bdg">V4.0</div></div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📍 الخريطة والملفات", "📊 حساب التكاليف", "🔧 حساب متقدم"])

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 1 ── الخريطة، الرسم اليدوي، ورفع SHP/GeoJSON
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab1:
    st.markdown('<div class="section-title">📍 تحديد مسار الأنبوب</div>', unsafe_allow_html=True)

    input_mode = st.radio(
        "اختر طريقة تحديد المسار:",
        ["🖊️ رسم على الخريطة", "📁 رفع ملف (Shapefile أو GeoJSON)"],
        horizontal=True, key="input_mode",
    )

    if input_mode == "📁 رفع ملف (Shapefile أو GeoJSON)":
        st.markdown(
            '<div class="map-info">💡 يمكنك رفع ملف <b>GeoJSON</b> (.geojson أو .json) مباشرة، '
            'أو ملف <b>Shapefile</b> مضغوط بصيغة <b>.zip</b> يحتوي الامتدادات shp وshx وdbf معاً '
            '(ويفضّل إضافة prj). يجب أن تكون الطبقة من نوع خطوط (Polyline / LineString).</div>',
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "اختر ملف GeoJSON أو ZIP (Shapefile)",
            type=["geojson", "json", "zip"],
            key="geo_file_uploader",
        )

        if uploaded_file is not None:
            file_bytes = uploaded_file.read()
            fname = uploaded_file.name.lower()

            if fname.endswith(".zip"):
                lines, msg = parse_shapefile_zip(file_bytes)
                source_label = f"ملف Shapefile: {uploaded_file.name}"
            else:
                lines, msg = parse_geojson_file(file_bytes)
                source_label = f"ملف GeoJSON: {uploaded_file.name}"

            if not lines:
                st.error(f"❌ {msg}")
            else:
                if msg:
                    st.warning(msg)

                if not coords_look_valid(lines):
                    st.error(
                        "❌ الإحداثيات المستخرجة خارج مدى خطوط الطول/العرض المعتاد "
                        "(قد تكون بنظام إسناد غير WGS84 مثل UTM). لا يمكن حساب الطول بدقة."
                    )
                else:
                    total_len = sum(calculate_line_length(line) for line in lines)
                    all_points = [pt for line in lines for pt in line]

                    st.session_state['drawn_coords'] = all_points
                    st.session_state['drawn_line_length'] = total_len
                    st.session_state['line_source'] = source_label

                    col_a, col_b = st.columns(2)
                    col_a.markdown(f'<div class="mc"><div class="v">{total_len:,.0f}</div><div class="l">الطول الإجمالي (متر)</div></div>', unsafe_allow_html=True)
                    col_b.markdown(f'<div class="mc"><div class="v">{len(lines)}</div><div class="l">عدد الأجزاء (Segments)</div></div>', unsafe_allow_html=True)

                    st.success(f"✅ تمت قراءة الملف بنجاح — الطول الإجمالي: {total_len:,.0f} متر")

                    if FOLIUM_AVAILABLE:
                        with st.expander("🗺️ معاينة المسار على الخريطة"):
                            avg_lat = sum(p[0] for p in all_points) / len(all_points)
                            avg_lon = sum(p[1] for p in all_points) / len(all_points)
                            preview_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=13, tiles='OpenStreetMap')
                            for line in lines:
                                folium.PolyLine(locations=line, color="#FF0000", weight=3).add_to(preview_map)
                            st_folium(preview_map, width=None, height=420, key="preview_map")

                    if st.button("✅ استخدام هذا الطول في تبويبي التكاليف", key="use_uploaded_length", use_container_width=True):
                        st.session_state['active_length_tab2'] = total_len
                        st.session_state['active_length_tab3'] = total_len
                        st.success(f"تم تعيين الطول: {total_len:.0f} متر في تبويبي التكاليف")

    else:
        if not FOLIUM_AVAILABLE:
            st.markdown(
                '<div class="warn-box">⚠️ مكتبات الخرائط (folium / streamlit-folium) غير مثبتة في هذه البيئة. '
                'تأكد من وجود ملف requirements.txt يحتوي عليها في جذر المستودع، ثم أعد تشغيل التطبيق بالكامل (Reboot). '
                'بإمكانك استخدام خيار رفع ملف GeoJSON/Shapefile بدلاً من ذلك، أو إدخال الطول يدوياً في التبويبين الآخرين.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="map-info">💡 استخدم أداة الرسم (الخط المنكسر) لرسم مسار الأنبوب على الخريطة. سيتم حساب الطول تلقائياً.</div>', unsafe_allow_html=True)

            m = folium.Map(location=[RLAT, RLON], zoom_start=11, tiles='OpenStreetMap')
            draw = Draw(
                draw_options={
                    'polyline': {'shapeOptions': {'color': '#FF0000', 'weight': 3}},
                    'polygon': False, 'rectangle': False, 'circle': False,
                    'marker': False, 'circlemarker': False,
                },
                edit_options={'edit': True},
                position='topleft',
            )
            draw.add_to(m)

            map_data = st_folium(m, width=None, height=480, key="main_map")

            if map_data and map_data.get('all_drawings'):
                last_line_coords = []
                for drawing in map_data['all_drawings']:
                    if drawing.get('geometry', {}).get('type') == 'LineString':
                        coords = [(c[1], c[0]) for c in drawing['geometry']['coordinates']]
                        if coords:
                            last_line_coords = coords
                if last_line_coords:
                    st.session_state['drawn_coords'] = last_line_coords
                    st.session_state['drawn_line_length'] = calculate_line_length(last_line_coords)
                    st.session_state['line_source'] = "رسم يدوي على الخريطة"

            st.markdown('<div class="section-title">📏 بيانات الخط</div>', unsafe_allow_html=True)

            if st.session_state['drawn_line_length'] > 0 and st.session_state.get('line_source') == "رسم يدوي على الخريطة":
                col_a, col_b = st.columns(2)
                col_a.markdown(f'<div class="mc"><div class="v">{st.session_state["drawn_line_length"]:,.0f}</div><div class="l">طول الخط (متر)</div></div>', unsafe_allow_html=True)
                col_b.markdown(f'<div class="mc"><div class="v">{len(st.session_state["drawn_coords"])}</div><div class="l">عدد النقاط</div></div>', unsafe_allow_html=True)

                if st.button("✅ استخدام هذا الطول في تبويبي التكاليف", key="use_line_length", use_container_width=True):
                    st.session_state['active_length_tab2'] = st.session_state['drawn_line_length']
                    st.session_state['active_length_tab3'] = st.session_state['drawn_line_length']
                    st.success(f"تم تعيين الطول: {st.session_state['drawn_line_length']:.0f} متر في تبويبي التكاليف")
            else:
                st.info("🖊️ ارسم خطاً على الخريطة لحساب الطول")

    if st.session_state.get('line_source'):
        st.markdown(f'<span class="src-badge">📌 آخر مصدر: {st.session_state["line_source"]}</span>', unsafe_allow_html=True)

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 2 ── حساب التكاليف
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab2:
    st.markdown('<div class="section-title">📊 حساب التكاليف الأساسية</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        diameter = st.selectbox("قطر الأنبوب (ملم)", options=sorted(PIPE_PRICES.keys()), key="diameter_tab2")
    with col2:
        pipe_length = st.number_input(
            "طول الأنبوب (م)", min_value=1.0,
            value=float(st.session_state['active_length_tab2']),
            step=10.0, key="length_tab2",
        )

    col3, col4 = st.columns(2)
    with col3:
        avg_depth = st.number_input("متوسط العمق (م)", min_value=0.5, value=3.0, step=0.1, key="depth_tab2")
    with col4:
        default_traps = max(1, round(pipe_length / 35)) if pipe_length else 1
        num_traps_manual = st.number_input("عدد المصائد", min_value=1, value=default_traps, step=1, key="traps_tab2")

    if st.button("💰 احسب التكاليف", key="calc_tab2", use_container_width=True):
        with st.spinner("جاري الحساب..."):
            excel_prices = load_excel_formulas()
            prices = excel_prices.get(diameter, {})
            calc_data, calc_warnings = calculate_pipe_details(pipe_length, diameter, avg_depth, num_traps_manual)
            if calc_data:
                report = generate_cost_report(calc_data, prices)
                if report:
                    st.session_state.cost_result = report
                    st.session_state.detailed_calc = calc_data
                    for w in calc_warnings:
                        st.warning(w)
                    st.success("✅ تم الحساب بنجاح!")

    if st.session_state.cost_result:
        st.markdown('<div class="section-title">💰 جدول التكاليف</div>', unsafe_allow_html=True)

        calc = st.session_state.detailed_calc
        col1, col2, col3 = st.columns(3)
        col1.markdown(f'<div class="mc"><div class="v">{calc["pipe_length"]:,.0f}</div><div class="l">طول الأنبوب (م)</div></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="mc"><div class="v">{calc["diameter_mm"]}</div><div class="l">قطر الأنبوب (ملم)</div></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="mc"><div class="v">{st.session_state.cost_result["total"]/1e6:.2f}M</div><div class="l">التكلفة الإجمالية</div></div>', unsafe_allow_html=True)

        render_cost_table(st.session_state.cost_result)

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            csv_content = build_csv(st.session_state.cost_result, include_unit=False)
            st.download_button(
                label="📥 تحميل CSV", data=csv_content,
                file_name=f"cost_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv", key="download_csv_tab2", use_container_width=True,
            )
        with dl_col2:
            if PDF_AVAILABLE:
                pdf_bytes = build_pdf_report(calc, st.session_state.cost_result, meta={"source": st.session_state.get('line_source')})
                if pdf_bytes:
                    st.download_button(
                        label="📄 تحميل PDF", data=pdf_bytes,
                        file_name=f"cost_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf", key="download_pdf_tab2", use_container_width=True,
                    )
                else:
                    st.caption("⚠️ تعذّر إنشاء PDF (تحقق من توفر ملفات الخطوط في مجلد fonts/)")
            else:
                st.caption("⚠️ مكتبات إنشاء PDF غير مثبتة (reportlab, arabic-reshaper, python-bidi)")

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 3 ── الحساب المتقدم
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab3:
    st.markdown('<div class="section-title">🔧 حساب متقدم مع خيارات مرنة</div>', unsafe_allow_html=True)

    st.markdown('<div class="map-info">💡 يمكنك استخدام الطول من التبويب الأول (رسم أو ملف SHP/GeoJSON) أو تعديله يدوياً هنا.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        diameter_adv = st.selectbox("قطر الأنبوب (ملم)", options=sorted(PIPE_PRICES.keys()), key="diameter_tab3")
    with col2:
        pipe_length_adv = st.number_input(
            "طول الأنبوب (م)", min_value=1.0,
            value=float(st.session_state['active_length_tab3']),
            step=10.0, key="length_tab3",
        )

    avg_depth_adv = st.number_input("متوسط العمق (م)", min_value=0.5, value=3.0, step=0.1, key="depth_tab3")

    col4, col5 = st.columns(2)
    with col4:
        trap_mode = st.radio("المصائد:", ["من المعادلة", "مدخل يدوي"], horizontal=True, key="trap_mode")
        num_traps_adv = st.number_input("عدد المصائد", min_value=1, value=1, step=1, key="traps_adv") if trap_mode == "مدخل يدوي" else None
    with col5:
        manhole_mode = st.radio("المناهل:", ["من المعادلة", "مدخل يدوي"], horizontal=True, key="manhole_mode")
        num_manholes_adv = st.number_input("عدد المناهل", min_value=1, value=1, step=1, key="manholes_adv") if manhole_mode == "مدخل يدوي" else None

    if st.button("⚡ احسب التفاصيل الآن", key="calc_adv", use_container_width=True):
        with st.spinner("جاري الحساب المتقدم..."):
            excel_prices = load_excel_formulas()
            prices = excel_prices.get(diameter_adv, {})
            calc_data, calc_warnings = calculate_pipe_details(
                pipe_length_adv, diameter_adv, avg_depth_adv, num_traps_adv, num_manholes_adv
            )
            if calc_data:
                report = generate_cost_report(calc_data, prices)
                if report:
                    st.session_state.cost_result = report
                    st.session_state.detailed_calc = calc_data
                    for w in calc_warnings:
                        st.warning(w)
                    st.success("✅ تم الحساب بنجاح!")

    if st.session_state.detailed_calc:
        calc = st.session_state.detailed_calc
        report = st.session_state.cost_result

        st.markdown('<div class="section-title">📊 النتائج التفصيلية</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        col1.markdown(f'<div class="mc"><div class="v">{calc["pipe_length"]:,.0f}</div><div class="l">طول الأنبوب</div></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="mc"><div class="v">{calc["num_traps"]}</div><div class="l">المصائد</div></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="mc"><div class="v">{calc["num_manholes"]}</div><div class="l">المناهل</div></div>', unsafe_allow_html=True)

        render_cost_table(report)

        with st.expander("📋 تفاصيل الكميات المحسوبة"):
            st.metric("كمية الحفر (م³)", f"{calc['excavation_qty']:,.2f}")
            st.metric("كمية الردم (م³)", f"{calc['final_backfill']:,.2f}")
            st.metric("حجم البحص (م³)", f"{calc['final_gravel']:,.2f}")
            st.metric("أطوال المصائد (م)", f"{calc['trap_lengths']:,.2f}")
            st.metric("زيادة أعماق المناهل (م)", f"{calc['manhole_depth_increase']:,.2f}")
            st.metric("عرض الخندق (م)", f"{calc['trench_width']:.2f}")

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            csv_content = build_csv(report, include_unit=True)
            st.download_button(
                label="📥 تحميل CSV", data=csv_content,
                file_name=f"advanced_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv", key="download_csv_adv", use_container_width=True,
            )
        with dl_col2:
            if PDF_AVAILABLE:
                pdf_bytes = build_pdf_report(calc, report, meta={"source": st.session_state.get('line_source')})
                if pdf_bytes:
                    st.download_button(
                        label="📄 تحميل PDF", data=pdf_bytes,
                        file_name=f"advanced_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf", key="download_pdf_adv", use_container_width=True,
                    )
                else:
                    st.caption("⚠️ تعذّر إنشاء PDF (تحقق من توفر ملفات الخطوط في مجلد fonts/)")
            else:
                st.caption("⚠️ مكتبات إنشاء PDF غير مثبتة (reportlab, arabic-reshaper, python-bidi)")

st.markdown("<div style='text-align:center;color:#999;font-size:0.75rem;margin-top:20px'>© 2025 Flood Drainage Networks with Interactive Maps</div>", unsafe_allow_html=True)
PYEOF
echo "تم إنشاء الملف"
wc -l /home/claude/storm_app/app_dash.py
Output

تم إنشاء الملف
887 /home/claude/storm_app/app_dash.py

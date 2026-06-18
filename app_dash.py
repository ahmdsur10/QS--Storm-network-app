import streamlit as st
import math
import os
import io
import json
import zipfile
import uuid
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
    st.markdown('<div style="text-align:center;color:rgba(180,210,255,.65);font-size:.78rem;margin-bottom:24px">رسم ورفع ملفات + حساب متعدد الخطوط · Eng. Ahmed Adam</div>', unsafe_allow_html=True)
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
# network_lines: قائمة قواميس، كل عنصر يمثل خطاً مستقلاً:
# {id, name, length, coords, source, diameter, depth, traps_mode, traps_value, manholes_mode, manholes_value, selected}
if "network_lines" not in st.session_state:
    st.session_state["network_lines"] = []
if "line_counter" not in st.session_state:
    st.session_state["line_counter"] = 0
if "combined_result" not in st.session_state:
    st.session_state["combined_result"] = None

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
        has_prj = (base + ".prj") in names
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
            "⚠️ لا يوجد ملف .prj داخل الأرشيف. تم افتراض نظام WGS84؛ "
            "إن كانت الإحداثيات بنظام UTM أو غيره ستكون نتيجة الطول غير صحيحة."
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


def next_line_name():
    st.session_state["line_counter"] += 1
    return f"خط {st.session_state['line_counter']}"


def add_line(coords, source):
    """يضيف خطاً جديداً إلى القائمة الموحّدة بقيم افتراضية للحساب"""
    length = calculate_line_length(coords)
    line = {
        "id": str(uuid.uuid4())[:8],
        "name": next_line_name(),
        "length": length,
        "coords": coords,
        "source": source,
        "diameter": 1000,
        "depth": 3.0,
        "traps_mode": "تلقائي",
        "traps_value": max(1, round(length / 35)) if length else 1,
        "manholes_mode": "تلقائي",
        "manholes_value": max(1, int(length / 100)) if length else 1,
        "selected": True,
    }
    st.session_state["network_lines"].append(line)
    return line


def remove_line(line_id):
    st.session_state["network_lines"] = [
        ln for ln in st.session_state["network_lines"] if ln["id"] != line_id
    ]


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
            f"⚠️ العمق ({avg_depth:.2f} م) أقل من الحد الأدنى المقترح ({min_required_depth:.2f} م) لقطر {diameter_mm} ملم."
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
        warnings.append("⚠️ كمية الردم كانت سالبة وتم تصحيحها إلى صفر.")
        final_backfill = 0.0
    if final_gravel < 0:
        warnings.append("⚠️ حجم البحص كان سالباً وتم تصحيحه إلى صفر.")
        final_gravel = 0.0

    if num_traps is None:
        num_traps = max(1, round(pipe_length / 35))
    trap_lengths = num_traps * 7

    if num_manholes is None:
        num_manholes = max(1, int(pipe_length / 100))
    manhole_depth_increase = num_manholes * 1.0

    result = {
        'pipe_length': pipe_length, 'diameter_mm': diameter_mm, 'avg_depth': avg_depth,
        'trench_width': trench_width, 'excavation_qty': excavation_qty,
        'final_backfill': final_backfill, 'final_gravel': final_gravel,
        'num_traps': num_traps, 'trap_lengths': trap_lengths,
        'num_manholes': num_manholes, 'manhole_depth_increase': manhole_depth_increase,
    }
    return result, warnings


def generate_cost_report(calc_data, prices):
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


def compute_line_report(line):
    """يحسب التفاصيل والتقرير لخط واحد بمعاملاته الحالية"""
    excel_prices = load_excel_formulas()
    prices = excel_prices.get(line["diameter"], {})
    traps = line["traps_value"] if line["traps_mode"] == "يدوي" else None
    manholes = line["manholes_value"] if line["manholes_mode"] == "يدوي" else None
    calc, warnings = calculate_pipe_details(line["length"], line["diameter"], line["depth"], traps, manholes)
    report = generate_cost_report(calc, prices)
    return calc, report, warnings


def build_combined_result(selected_lines):
    """يبني نتيجة موحّدة: تقرير لكل خط + ملخص لكل خط + بنود مجمّعة + المجموع الكلي"""
    per_line = []
    merged_items = {}
    grand_total = 0
    all_warnings = []

    for line in selected_lines:
        calc, report, warnings = compute_line_report(line)
        per_line.append({"line": line, "calc": calc, "report": report})
        grand_total += report["total"]
        for w in warnings:
            all_warnings.append(f"{line['name']}: {w}")

        for item in report["items"]:
            key = item["name"]
            if key not in merged_items:
                merged_items[key] = {"name": item["name"], "unit": item["unit"], "qty": 0.0, "total": 0.0}
            merged_items[key]["qty"] += item["qty"]
            merged_items[key]["total"] += item["total"]

    merged_list = []
    for key in sorted(merged_items.keys()):
        v = merged_items[key]
        eff_price = (v["total"] / v["qty"]) if v["qty"] else 0
        merged_list.append({**v, "price": eff_price})

    return {
        "per_line": per_line,
        "merged_items": merged_list,
        "grand_total": grand_total,
        "warnings": all_warnings,
    }


def build_csv_combined(combined):
    lines_out = ["=== ملخص الخطوط ===", "اسم الخط,الطول (م),القطر (ملم),التكلفة (ريال)"]
    for pl in combined["per_line"]:
        ln = pl["line"]
        lines_out.append(f'"{ln["name"]}",{ln["length"]:.2f},{ln["diameter"]},{pl["report"]["total"]:.0f}')
    lines_out.append("")
    lines_out.append("=== الكميات المجمّعة لكل البنود ===")
    lines_out.append("البند,الكمية الإجمالية,الوحدة,متوسط السعر,الإجمالي")
    for item in combined["merged_items"]:
        lines_out.append(f'"{item["name"]}",{item["qty"]:.2f},{item["unit"]},{item["price"]:.2f},{item["total"]:.0f}')
    lines_out.append("")
    lines_out.append(f"المجموع الكلي,,,,{combined['grand_total']:.0f}")
    return "\n".join(lines_out) + "\n"


def render_lines_summary_table(combined):
    html = '<table class="cost-table"><thead><tr><th>اسم الخط</th><th>الطول (م)</th><th>القطر (ملم)</th><th>التكلفة (ريال)</th></tr></thead><tbody>'
    for pl in combined["per_line"]:
        ln = pl["line"]
        html += f'<tr><td>{ln["name"]}</td><td>{ln["length"]:,.0f}</td><td>{ln["diameter"]}</td><td>{pl["report"]["total"]:,.0f}</td></tr>'
    html += f'<tr class="total"><td colspan="3">المجموع الكلي</td><td>{combined["grand_total"]:,.0f}</td></tr></tbody></table>'
    st.markdown(html, unsafe_allow_html=True)


def render_merged_items_table(combined):
    html = '<table class="cost-table"><thead><tr><th>البند</th><th>الكمية الإجمالية</th><th>متوسط السعر</th><th>الإجمالي</th></tr></thead><tbody>'
    for item in combined["merged_items"]:
        html += f'<tr><td>{item["name"]}</td><td>{item["qty"]:,.2f} {item["unit"]}</td><td>{item["price"]:,.2f}</td><td>{item["total"]:,.0f}</td></tr>'
    html += f'<tr class="total"><td colspan="3">المجموع الكلي</td><td>{combined["grand_total"]:,.0f}</td></tr></tbody></table>'
    st.markdown(html, unsafe_allow_html=True)


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


def build_pdf_report_combined(combined):
    if not PDF_AVAILABLE or not _register_arabic_fonts():
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm,
                             leftMargin=15 * mm, rightMargin=15 * mm)

    title_style = ParagraphStyle("title", fontName="ArabicBold", fontSize=16, alignment=1,
                                  textColor=colors.HexColor("#0a2a5e"), spaceAfter=4)
    subtitle_style = ParagraphStyle("subtitle", fontName="ArabicReg", fontSize=9.5, alignment=1,
                                     textColor=colors.HexColor("#5a6b85"), spaceAfter=10)
    section_style = ParagraphStyle("section", fontName="ArabicBold", fontSize=12.5, alignment=2,
                                    textColor=colors.HexColor("#0a2a5e"), spaceBefore=12, spaceAfter=6)

    story = []
    story.append(Paragraph(ar("تقرير حساب تكاليف شبكة تصريف السيول"), title_style))
    story.append(Paragraph(ar(f"تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), subtitle_style))
    story.append(Paragraph(ar(f"عدد الخطوط المحسوبة: {len(combined['per_line'])}"), subtitle_style))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#1a5fa8"), thickness=1.2))
    story.append(Spacer(1, 6 * mm))

    # ملخص الخطوط
    story.append(Paragraph(ar("ملخص الخطوط"), section_style))
    lines_data = [[ar("التكلفة (ريال)"), ar("القطر (ملم)"), ar("الطول (م)"), ar("اسم الخط")]]
    for pl in combined["per_line"]:
        ln = pl["line"]
        lines_data.append([f"{pl['report']['total']:,.0f}", str(ln["diameter"]), f"{ln['length']:,.1f}", ar(ln["name"])])
    lines_data.append([f"{combined['grand_total']:,.0f}", "", "", ar("المجموع الكلي")])

    lines_table = Table(lines_data, colWidths=[40 * mm, 30 * mm, 30 * mm, 70 * mm], repeatRows=1)
    lines_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'ArabicReg'),
        ('FONTNAME', (0, 0), (-1, 0), 'ArabicBold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0a2a5e")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -2), 0.4, colors.HexColor("#d0e4f7")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fbfe")]),
        ('SPAN', (1, -1), (2, -1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#0a2a5e")),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'ArabicBold'),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(lines_table)
    story.append(Spacer(1, 8 * mm))

    # الكميات المجمّعة
    story.append(Paragraph(ar("الكميات المجمّعة لكل البنود (لكل الخطوط المختارة)"), section_style))
    merged_data = [[ar("الإجمالي (ريال)"), ar("متوسط السعر"), ar("الكمية"), ar("الوحدة"), ar("البند")]]
    for item in combined["merged_items"]:
        merged_data.append([
            f"{item['total']:,.0f}", f"{item['price']:,.2f}", f"{item['qty']:,.2f}", ar(item["unit"]), ar(item["name"]),
        ])
    merged_data.append([f"{combined['grand_total']:,.0f}", "", "", "", ar("المجموع الكلي")])

    merged_table = Table(merged_data, colWidths=[32 * mm, 25 * mm, 25 * mm, 18 * mm, 70 * mm], repeatRows=1)
    merged_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'ArabicReg'),
        ('FONTNAME', (0, 0), (-1, 0), 'ArabicBold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0a2a5e")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -2), 0.4, colors.HexColor("#d0e4f7")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fbfe")]),
        ('SPAN', (1, -1), (3, -1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#0a2a5e")),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'ArabicBold'),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(merged_table)
    story.append(Spacer(1, 8 * mm))

    footer_style = ParagraphStyle("footer", fontName="ArabicReg", fontSize=8, alignment=1,
                                   textColor=colors.HexColor("#999999"))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#d0e4f7"), thickness=0.8))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(ar("© حاسبة شبكات تصريف السيول مع الخرائط التفاعلية"), footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ═════════════════════════════════════════════════════════════════════════════════
# ──── الواجهة الرئيسية ────
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="hdr"><h1>🌊 حاسبة شبكات تصريف السيول مع الخرائط التفاعلية</h1><div class="bdg">V5.0</div></div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📍 الخريطة (رسم + رفع ملفات)", "📊 حساب التكاليف لكل الخطوط"])

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 1 ── خريطة مدمجة: رسم + رفع SHP/GeoJSON على نفس القائمة
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab1:
    st.markdown('<div class="section-title">📍 تحديد مسارات الأنابيب</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="map-info">💡 يمكنك رفع ملف GeoJSON أو Shapefile (مضغوط ZIP)، ثم رسم خطوط إضافية '
        'على نفس الخريطة — كل خط (من رفع أو رسم) يُضاف إلى القائمة الموحّدة أدناه بدون استبدال ما سبق.</div>',
        unsafe_allow_html=True,
    )

    # ── رفع ملف ──
    with st.expander("📁 رفع ملف GeoJSON أو Shapefile (ZIP)", expanded=False):
        uploaded_file = st.file_uploader(
            "اختر ملف GeoJSON (.geojson/.json) أو ZIP يحتوي Shapefile",
            type=["geojson", "json", "zip"], key="geo_file_uploader",
        )
        if uploaded_file is not None:
            already_added_key = f"processed_{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get("last_uploaded_key") != already_added_key:
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
                elif not coords_look_valid(lines):
                    st.error(
                        "❌ الإحداثيات خارج مدى خطوط الطول/العرض المعتاد "
                        "(قد تكون بنظام إسناد غير WGS84 مثل UTM)."
                    )
                else:
                    if msg:
                        st.warning(msg)
                    added_names = []
                    for line_coords in lines:
                        new_line = add_line(line_coords, source_label)
                        added_names.append(new_line["name"])
                    st.session_state["last_uploaded_key"] = already_added_key
                    st.success(f"✅ تمت إضافة {len(added_names)} خط/أجزاء من الملف: {', '.join(added_names)}")
                    st.rerun()

    # ── الرسم على الخريطة ──
    if not FOLIUM_AVAILABLE:
        st.markdown(
            '<div class="warn-box">⚠️ مكتبات الخرائط (folium / streamlit-folium) غير مثبتة في هذه البيئة. '
            'تأكد من وجود ملف requirements.txt في جذر المستودع، ثم أعد تشغيل التطبيق بالكامل (Reboot). '
            'بإمكانك الاستمرار باستخدام رفع الملفات فقط.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="map-info">🖊️ استخدم أداة الرسم (الخط المنكسر) أعلى يسار الخريطة لإضافة خط جديد. الخطوط المضافة سابقاً تظهر على الخريطة بألوان مختلفة.</div>', unsafe_allow_html=True)

        existing_lines = st.session_state["network_lines"]
        if existing_lines:
            avg_lat = sum(p[0] for ln in existing_lines for p in ln["coords"]) / sum(len(ln["coords"]) for ln in existing_lines)
            avg_lon = sum(p[1] for ln in existing_lines for p in ln["coords"]) / sum(len(ln["coords"]) for ln in existing_lines)
            map_center = [avg_lat, avg_lon]
        else:
            map_center = [RLAT, RLON]

        m = folium.Map(location=map_center, zoom_start=12, tiles='OpenStreetMap')

        for idx, ln in enumerate(existing_lines):
            color = LINE_COLORS[idx % len(LINE_COLORS)]
            folium.PolyLine(
                locations=ln["coords"], color=color, weight=4,
                tooltip=f'{ln["name"]} — {ln["length"]:,.0f} م',
            ).add_to(m)

        draw = Draw(
            draw_options={
                'polyline': {'shapeOptions': {'color': '#FF0000', 'weight': 3}},
                'polygon': False, 'rectangle': False, 'circle': False,
                'marker': False, 'circlemarker': False,
            },
            edit_options={'edit': False},
            position='topleft',
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

    # ── قائمة الخطوط الحالية ──
    st.markdown('<div class="section-title">📋 الخطوط المضافة</div>', unsafe_allow_html=True)

    if not st.session_state["network_lines"]:
        st.info("لا توجد خطوط مضافة بعد. ارسم خطاً على الخريطة أو ارفع ملفاً لإضافة أول خط.")
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
# ║ TAB 2 ── حساب التكاليف لكل الخطوط (دمج التبويبين السابقين)
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab2:
    st.markdown('<div class="section-title">📊 إعدادات كل خط</div>', unsafe_allow_html=True)

    if not st.session_state["network_lines"]:
        st.info("لا توجد خطوط متاحة. أضف خطوطاً من التبويب الأول (رسم أو رفع ملف) أولاً.")
    else:
        st.markdown('<div class="map-info">💡 حدّد القطر والعمق لكل خط على حدة، واختر الخطوط التي تريد تضمينها في الحساب الإجمالي.</div>', unsafe_allow_html=True)

        for ln in st.session_state["network_lines"]:
            with st.expander(f"⚙️ {ln['name']} — {ln['length']:,.0f} م ({ln['source']})", expanded=False):
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

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        if st.button("💰 احسب تكلفة الخطوط المختارة", key="calc_combined", use_container_width=True):
            selected = [ln for ln in st.session_state["network_lines"] if ln["selected"]]
            if not selected:
                st.warning("⚠️ لم يتم تحديد أي خط للحساب. فعّل خانة 'تضمين هذا الخط' لخط واحد على الأقل.")
            else:
                with st.spinner("جاري حساب جميع الخطوط..."):
                    combined = build_combined_result(selected)
                    st.session_state["combined_result"] = combined
                    for w in combined["warnings"]:
                        st.warning(w)
                    st.success(f"✅ تم حساب {len(selected)} خط بنجاح!")

    if st.session_state["combined_result"]:
        combined = st.session_state["combined_result"]

        st.markdown('<div class="section-title">📋 ملخص الخطوط</div>', unsafe_allow_html=True)
        total_length = sum(pl["line"]["length"] for pl in combined["per_line"])
        col1, col2, col3 = st.columns(3)
        col1.markdown(f'<div class="mc"><div class="v">{len(combined["per_line"])}</div><div class="l">عدد الخطوط</div></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="mc"><div class="v">{total_length:,.0f}</div><div class="l">الطول الإجمالي (م)</div></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="mc"><div class="v">{combined["grand_total"]/1e6:.2f}M</div><div class="l">التكلفة الإجمالية</div></div>', unsafe_allow_html=True)

        render_lines_summary_table(combined)

        st.markdown('<div class="section-title">📦 الكميات المجمّعة لكل البنود</div>', unsafe_allow_html=True)
        st.caption("ملاحظة: عند اختلاف الأقطار بين الخطوط، السعر المعروض هو متوسط فعلي (إجمالي التكلفة ÷ إجمالي الكمية) لهذا البند.")
        render_merged_items_table(combined)

        with st.expander("📋 تفاصيل كل خط على حدة"):
            for pl in combined["per_line"]:
                ln = pl["line"]
                st.markdown(f"**{ln['name']}** — قطر {ln['diameter']} ملم، عمق {ln['depth']:.2f} م")
                html = '<table class="cost-table"><thead><tr><th>البند</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr></thead><tbody>'
                for item in pl["report"]["items"]:
                    html += f'<tr><td>{item["name"]}</td><td>{item["qty"]:,.2f} {item["unit"]}</td><td>{item["price"]:,.0f}</td><td>{item["total"]:,.0f}</td></tr>'
                html += f'<tr class="total"><td colspan="3">إجمالي الخط</td><td>{pl["report"]["total"]:,.0f}</td></tr></tbody></table>'
                st.markdown(html, unsafe_allow_html=True)

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            csv_content = build_csv_combined(combined)
            st.download_button(
                label="📥 تحميل CSV", data=csv_content,
                file_name=f"combined_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv", key="download_csv_combined", use_container_width=True,
            )
        with dl_col2:
            if PDF_AVAILABLE:
                pdf_bytes = build_pdf_report_combined(combined)
                if pdf_bytes:
                    st.download_button(
                        label="📄 تحميل PDF", data=pdf_bytes,
                        file_name=f"combined_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf", key="download_pdf_combined", use_container_width=True,
                    )
                else:
                    st.caption("⚠️ تعذّر إنشاء PDF (تحقق من توفر ملفات الخطوط في مجلد fonts/)")
            else:
                st.caption("⚠️ مكتبات إنشاء PDF غير مثبتة (reportlab, arabic-reshaper, python-bidi)")

st.markdown("<div style='text-align:center;color:#999;font-size:0.75rem;margin-top:20px'>© 2025 Flood Drainage Networks with Interactive Maps</div>", unsafe_allow_html=True)

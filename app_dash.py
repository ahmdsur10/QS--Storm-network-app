import streamlit as st
import json, math, os, tempfile, zipfile, folium
from streamlit_folium import st_folium
from folium.plugins import Draw
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="حاسبة شبكات السيول", page_icon="🌊",
                   layout="wide", initial_sidebar_state="collapsed",
                   menu_items={'Get Help': None, 'Report a bug': None, 'About': None})

PIPE_PRICES = {
    400:454, 500:619, 600:725, 700:906, 800:1045,
    900:1225, 1000:1440, 1100:1600, 1200:1812, 1300:1920, 1400:2132,
}

MAIN_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
*{box-sizing:border-box}
html,body,[class*="css"],.stApp{font-family:'Cairo',sans-serif!important;direction:rtl;-webkit-text-size-adjust:100%}
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stToolbarActions"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"],#MainMenu,footer,footer *,
.stToolbar,button[title="View app fullscreen"],a[href*="streamlit.io"],a[href*="github.com"],
[data-testid="baseButton-headerNoPadding"],[data-testid="stSidebar"]
{display:none!important;visibility:hidden!important;height:0!important;overflow:hidden!important;pointer-events:none!important}
.block-container{padding:0.5rem 0.75rem 2rem!important;max-width:1400px!important;margin:0 auto!important}
.hdr{background:linear-gradient(135deg,#0a2a5e,#1a5fa8);color:#fff;padding:12px 14px;border-radius:12px;
  margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px}
.hdr h1{margin:0;font-size:1rem;font-weight:900;line-height:1.4}
.hdr p{margin:0;font-size:.72rem;color:#b8d9f8}
.hdr .bdg{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.3);
  padding:4px 10px;border-radius:14px;font-size:.7rem;font-weight:700;white-space:nowrap}
.mc{background:#fff;border-radius:10px;padding:10px 8px;box-shadow:0 2px 8px rgba(0,0,0,.08);
  border-top:3px solid #1a5fa8;text-align:center;margin-bottom:6px}
.mc .v{font-size:1.1rem;font-weight:900;color:#0a2a5e}
.mc .l{font-size:.68rem;color:#6b7a99;margin-top:2px}
.res{background:linear-gradient(135deg,#0a2a5e,#1a5fa8);color:#fff!important;padding:14px 16px;
  border-radius:12px;font-size:.88rem;font-weight:700;text-align:center;
  box-shadow:0 4px 14px rgba(26,95,168,.3);margin-top:8px;line-height:2.1}
.section-title{color:#0a2a5e;font-size:.92rem;font-weight:900;margin:14px 0 8px;
  border-bottom:2px solid #1a5fa8;padding-bottom:4px}
.stButton>button{background:linear-gradient(135deg,#1a5fa8,#0a2a5e)!important;color:#fff!important;
  border:none!important;border-radius:10px!important;font-family:'Cairo',sans-serif!important;
  font-weight:700!important;font-size:.95rem!important;padding:13px 8px!important;min-height:50px!important}
.stTextInput>div>div>input,.stNumberInput>div>div>input{min-height:50px!important;font-size:1rem!important;
  font-family:'Cairo',sans-serif!important;direction:rtl!important;border-radius:10px!important}
.stSelectbox [data-baseweb="select"]>div{min-height:50px!important;font-family:'Cairo',sans-serif!important;border-radius:10px!important}
.stTabs [data-baseweb="tab"]{font-family:'Cairo',sans-serif!important;font-weight:700!important;
  font-size:.88rem!important;padding:10px 14px!important;min-height:44px!important}
.cost-table{width:100%;border-collapse:collapse;font-size:0.85rem;direction:rtl;margin:10px 0}
.cost-table th,.cost-table td{padding:8px;border:1px solid #d0e4f7;text-align:right}
.cost-table th{background:#eaf4ff;color:#0a2a5e;font-weight:700}
.cost-table tr:nth-child(even){background:#f8fbfe}
.cost-table .total{background:#0a2a5e;color:#fff;font-weight:700}
.map-info{background:#eaf4ff;border-right:4px solid #1a5fa8;border-radius:8px;
  padding:10px 13px;font-size:.83rem;color:#0a2a5e;margin-bottom:8px;line-height:1.9}
</style>"""

def check_credentials(u, p):
    try:
        users = st.secrets["users"]
        return users.get(u) == p
    except:
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
    st.markdown('<div style="text-align:center;color:rgba(180,210,255,.65);font-size:.78rem;margin-bottom:24px">مع خرائط تفاعلية · Eng. Ahmed Adam</div>', unsafe_allow_html=True)
    st.markdown('<hr style="border-color:rgba(26,95,168,.4);margin-bottom:20px">', unsafe_allow_html=True)
    username = st.text_input("اسم المستخدم", placeholder="أدخل اسم المستخدم", key="login_user")
    password = st.text_input("كلمة المرور", type="password", placeholder="• • • • • • • •", key="login_pass")
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    if st.button("🔑  تسجيل الدخول", use_container_width=True):
        if check_credentials(username.strip(), password):
            st.session_state.update({"authenticated":True,"current_user":username.strip()})
            st.rerun()
        else:
            st.error("❌  اسم المستخدم أو كلمة المرور غير صحيحة")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if not st.session_state["authenticated"]:
    login_page(); st.stop()

st.markdown(MAIN_CSS, unsafe_allow_html=True)

# ── Session State ──
DEFAULTS = {
    "map_data": None, "drawn_line_length": 0, "drawn_coords": [],
    "selected_diameter": 1000, "avg_depth": 3.0, "num_traps": None,
    "num_manholes": None, "detailed_calc": None, "cost_result": None,
}
for k,v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k] = v

RLAT, RLON = 24.7136, 46.6753

# ═════════════════════════════════════════════════════════════════════════════════
# ──── دوال حساب المسافة ────
# ═════════════════════════════════════════════════════════════════════════════════

def haversine_distance(lat1, lon1, lat2, lon2):
    """حساب المسافة بين نقطتين بالكيلومتر"""
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c * 1000  # تحويل لمتر

def calculate_line_length(coords):
    """حساب طول الخط من الإحداثيات"""
    if len(coords) < 2:
        return 0
    
    total_length = 0
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        total_length += haversine_distance(lat1, lon1, lat2, lon2)
    
    return total_length

def extract_coordinates_from_geojson(geojson_data):
    """استخراج الإحداثيات من GeoJSON"""
    if not geojson_data or "geometry" not in geojson_data:
        return []
    
    geometry = geojson_data["geometry"]
    if geometry["type"] == "LineString":
        return [(coord[1], coord[0]) for coord in geometry["coordinates"]]
    return []

def load_excel_formulas():
    """تحميل معاملات الحساب"""
    formulas = {
        400: {'pipe_price': 454, 'excavation_price': 130, 'backfill_price': 90, 'gravel_price': 320},
        500: {'pipe_price': 619, 'excavation_price': 130, 'backfill_price': 110, 'gravel_price': 320},
        600: {'pipe_price': 725, 'excavation_price': 130, 'backfill_price': 110, 'gravel_price': 320},
        700: {'pipe_price': 906, 'excavation_price': 130, 'backfill_price': 110, 'gravel_price': 320},
        800: {'pipe_price': 1045, 'excavation_price': 130, 'backfill_price': 110, 'gravel_price': 320},
        900: {'pipe_price': 1225, 'excavation_price': 130, 'backfill_price': 110, 'gravel_price': 320},
        1000: {'pipe_price': 1440, 'excavation_price': 130, 'backfill_price': 110, 'gravel_price': 320},
        1100: {'pipe_price': 1600, 'excavation_price': 130, 'backfill_price': 110, 'gravel_price': 320},
        1200: {'pipe_price': 1812, 'excavation_price': 130, 'backfill_price': 110, 'gravel_price': 320},
        1300: {'pipe_price': 1920, 'excavation_price': 130, 'backfill_price': 110, 'gravel_price': 320},
        1400: {'pipe_price': 2132, 'excavation_price': 130, 'backfill_price': 110, 'gravel_price': 320},
    }
    return formulas

def calculate_pipe_details(pipe_length, diameter_mm, avg_depth, num_traps=None, num_manholes=None):
    """حساب تفاصيل الأنابيب"""
    try:
        diameter_m = diameter_mm / 1000
        
        # عرض الخندق
        if diameter_mm >= 1300:
            trench_width = diameter_m + 1.0
        elif diameter_mm >= 800:
            trench_width = diameter_m + 0.85
        else:
            trench_width = diameter_m + 0.7
        
        # كمية الحفر
        excavation_qty = pipe_length * avg_depth * trench_width
        
        # حجم الأنبوب
        pipe_volume = math.pi * ((diameter_m / 2) ** 2) * pipe_length
        pipe_half_volume = pipe_volume / 2
        
        # كمية الردم
        backfill_qty = pipe_length * trench_width * (avg_depth - (diameter_m / 2))
        final_backfill = backfill_qty - pipe_half_volume
        
        # البحص
        gravel_depth = 0.2 + (diameter_m / 2)
        gravel_volume = gravel_depth * pipe_length * trench_width
        final_gravel = gravel_volume - pipe_half_volume
        
        # المصائد
        if num_traps is None:
            num_traps = max(1, round(pipe_length / 35))
        
        trap_lengths = num_traps * 7
        
        # المناهل
        if num_manholes is None:
            num_manholes = max(1, int(pipe_length / 100))
        
        manhole_depth_increase = num_manholes * 1.0
        
        return {
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
    except Exception as e:
        st.error(f"خطأ في الحساب: {e}")
        return None

def generate_cost_report(calc_data, prices):
    """إنشاء تقرير التكاليف"""
    try:
        items = [
            {'name': '1. أطوال الأنابيب', 'unit': 'م', 'qty': calc_data['pipe_length'], 'price': prices.get('pipe_price', 0)},
            {'name': '2. كمية الحفر', 'unit': 'م³', 'qty': calc_data['excavation_qty'], 'price': prices.get('excavation_price', 130)},
            {'name': '3. كمية الردم', 'unit': 'م³', 'qty': calc_data['final_backfill'], 'price': prices.get('backfill_price', 90)},
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

# ═════════════════════════════════════════════════════════════════════════════════
# ──── الواجهة الرئيسية ────
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="hdr"><h1>🌊 حاسبة شبكات تصريف السيول مع الخرائط التفاعلية</h1><div class="bdg">V3.0</div></div>', unsafe_allow_html=True)

# إنشاء التبويبات
tab1, tab2, tab3 = st.tabs(["📍 الخريطة والرسم", "📊 حساب التكاليف", "🔧 حساب متقدم"])

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 1 ── الخريطة والرسم
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab1:
    st.markdown('<div class="section-title">📍 الخريطة التفاعلية - ارسم مسار الأنبوب</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="map-info">💡 استخدم أداة الرسم لرسم مسار الأنبوب على الخريطة. سيتم حساب الطول تلقائياً.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # إنشاء الخريطة
        m = folium.Map(
            location=[RLAT, RLON],
            zoom_start=11,
            tiles='OpenStreetMap',
            height=600
        )
        
        # إضافة أداة الرسم
        draw = Draw(
            draw_options={
                'polyline': {'shapeOptions': {'color': '#FF0000', 'weight': 3}},
                'polygon': False,
                'rectangle': False,
                'circle': False,
                'marker': False,
                'circlemarker': False
            },
            position='topleft'
        )
        draw.add_to(m)
        
        # عرض الخريطة والحصول على البيانات
        map_data = st_folium(m, width=700, height=600)
        
        # معالجة بيانات الخريطة
        if map_data and map_data.get('all_drawings'):
            for drawing in map_data['all_drawings']:
                if drawing['geometry']['type'] == 'LineString':
                    coords = extract_coordinates_from_geojson(drawing)
                    if coords:
                        line_length = calculate_line_length(coords)
                        st.session_state['drawn_line_length'] = line_length
                        st.session_state['drawn_coords'] = coords
    
    with col2:
        st.markdown('<div class="section-title">📏 بيانات الخط</div>', unsafe_allow_html=True)
        
        if st.session_state['drawn_line_length'] > 0:
            st.markdown(f'''
            <div class="mc">
                <div class="v">{st.session_state["drawn_line_length"]:,.0f}</div>
                <div class="l">طول الخط (متر)</div>
            </div>
            ''', unsafe_allow_html=True)
            
            st.markdown(f'''
            <div class="mc">
                <div class="v">{len(st.session_state["drawn_coords"])}</div>
                <div class="l">عدد النقاط</div>
            </div>
            ''', unsafe_allow_html=True)
            
            if st.button("✅ استخدام هذا الطول", key="use_line_length"):
                st.success(f"تم استخدام الطول: {st.session_state['drawn_line_length']:.0f} متر")
        else:
            st.info("🖊️ ارسم خطاً على الخريطة لحساب الطول")

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 2 ── حساب التكاليف
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab2:
    st.markdown('<div class="section-title">📊 حساب التكاليف الأساسية</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        diameter = st.selectbox("قطر الأنبوب (ملم)", options=sorted(PIPE_PRICES.keys()), key="diameter_tab2")
    
    with col2:
        pipe_length = st.number_input("طول الأنبوب (م)", min_value=1.0, value=st.session_state.get('drawn_line_length', 1000.0), step=10.0, key="length_tab2")
    
    with col3:
        avg_depth = st.number_input("متوسط العمق (م)", min_value=0.5, value=3.0, step=0.1, key="depth_tab2")
    
    with col4:
        num_traps_manual = st.number_input("عدد المصائد", min_value=1, value=int((pipe_length or 1000) / 35), step=1, key="traps_tab2")
    
    if st.button("💰 احسب التكاليف", key="calc_tab2"):
        with st.spinner("جاري الحساب..."):
            excel_prices = load_excel_formulas()
            prices = excel_prices.get(diameter, {})
            
            calc_data = calculate_pipe_details(pipe_length, diameter, avg_depth, num_traps_manual)
            
            if calc_data:
                report = generate_cost_report(calc_data, prices)
                
                if report:
                    st.session_state.cost_result = report
                    st.session_state.detailed_calc = calc_data
                    st.success("✅ تم الحساب بنجاح!")
    
    # عرض النتائج
    if st.session_state.cost_result:
        st.markdown('<div class="section-title">💰 جدول التكاليف</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        col1.markdown(f'<div class="mc"><div class="v">{pipe_length:,.0f}</div><div class="l">طول الأنبوب (م)</div></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="mc"><div class="v">{diameter}</div><div class="l">قطر الأنبوب (ملم)</div></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="mc"><div class="v">{st.session_state.cost_result["total"]/1e6:.2f}M</div><div class="l">التكلفة الإجمالية</div></div>', unsafe_allow_html=True)
        
        # جدول HTML
        table_html = '<table class="cost-table"><thead><tr><th>البند</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr></thead><tbody>'
        
        for item in st.session_state.cost_result['items']:
            table_html += f'<tr><td>{item["name"]}</td><td>{item["qty"]:,.2f}</td><td>{item["price"]:,.0f}</td><td>{item["total"]:,.0f}</td></tr>'
        
        table_html += f'<tr class="total"><td colspan="3">المجموع</td><td>{st.session_state.cost_result["total"]:,.0f}</td></tr></tbody></table>'
        
        st.markdown(table_html, unsafe_allow_html=True)
        
        # تصدير CSV
        if st.button("📥 تصدير CSV", key="export_csv_tab2"):
            csv_content = "البند,الكمية,السعر,الإجمالي\n"
            for item in st.session_state.cost_result['items']:
                csv_content += f'"{item["name"]}",{item["qty"]:.2f},{item["price"]:.0f},{item["total"]:.0f}\n'
            csv_content += f"المجموع,,,{st.session_state.cost_result['total']:.0f}\n"
            
            st.download_button(
                label="⬇️ حميل CSV",
                data=csv_content,
                file_name=f"cost_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 3 ── الحساب المتقدم
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab3:
    st.markdown('<div class="section-title">🔧 حساب متقدم مع خيارات مرنة</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="map-info">💡 هذا التبويب يستخدم الطول المرسوم على الخريطة من التبويب الأول تلقائياً</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        diameter_adv = st.selectbox("قطر الأنبوب (ملم)", options=sorted(PIPE_PRICES.keys()), key="diameter_tab3")
    
    with col2:
        pipe_length_adv = st.number_input("طول الأنبوب (م)", min_value=1.0, 
                                          value=st.session_state.get('drawn_line_length', 1000.0), 
                                          step=10.0, key="length_tab3")
    
    with col3:
        avg_depth_adv = st.number_input("متوسط العمق (م)", min_value=0.5, value=3.0, step=0.1, key="depth_tab3")
    
    col4, col5 = st.columns(2)
    
    with col4:
        trap_mode = st.radio("المصائد:", ["من المعادلة", "مدخل يدوي"], horizontal=True, key="trap_mode")
        if trap_mode == "مدخل يدوي":
            num_traps_adv = st.number_input("عدد المصائد", min_value=1, value=1, step=1, key="traps_adv")
        else:
            num_traps_adv = None
    
    with col5:
        manhole_mode = st.radio("المناهل:", ["من المعادلة", "مدخل يدوي"], horizontal=True, key="manhole_mode")
        if manhole_mode == "مدخل يدوي":
            num_manholes_adv = st.number_input("عدد المناهل", min_value=1, value=1, step=1, key="manholes_adv")
        else:
            num_manholes_adv = None
    
    if st.button("⚡ احسب التفاصيل الآن", key="calc_adv"):
        with st.spinner("جاري الحساب المتقدم..."):
            excel_prices = load_excel_formulas()
            prices = excel_prices.get(diameter_adv, {})
            
            calc_data = calculate_pipe_details(pipe_length_adv, diameter_adv, avg_depth_adv, 
                                               num_traps_adv, num_manholes_adv)
            
            if calc_data:
                report = generate_cost_report(calc_data, prices)
                
                if report:
                    st.session_state.cost_result = report
                    st.session_state.detailed_calc = calc_data
                    st.success("✅ تم الحساب بنجاح!")
    
    # عرض النتائج المتقدمة
    if st.session_state.detailed_calc:
        calc = st.session_state.detailed_calc
        report = st.session_state.cost_result
        
        st.markdown('<div class="section-title">📊 النتائج التفصيلية</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        col1.markdown(f'<div class="mc"><div class="v">{calc["pipe_length"]:,.0f}</div><div class="l">طول الأنبوب</div></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="mc"><div class="v">{calc["num_traps"]}</div><div class="l">المصائد</div></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="mc"><div class="v">{calc["num_manholes"]}</div><div class="l">المناهل</div></div>', unsafe_allow_html=True)
        
        # جدول التفاصيل
        table_html = '<table class="cost-table"><thead><tr><th>البند</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr></thead><tbody>'
        
        for item in report['items']:
            table_html += f'<tr><td>{item["name"]}</td><td>{item["qty"]:,.2f} {item["unit"]}</td><td>{item["price"]:,.0f}</td><td>{item["total"]:,.0f}</td></tr>'
        
        table_html += f'<tr class="total"><td colspan="3">المجموع الإجمالي</td><td>{report["total"]:,.0f}</td></tr></tbody></table>'
        
        st.markdown(table_html, unsafe_allow_html=True)
        
        # تفاصيل إضافية
        with st.expander("📋 تفاصيل الكميات المحسوبة"):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("كمية الحفر (م³)", f"{calc['excavation_qty']:,.2f}")
                st.metric("كمية الردم (م³)", f"{calc['final_backfill']:,.2f}")
                st.metric("حجم البحص (م³)", f"{calc['final_gravel']:,.2f}")
            
            with col2:
                st.metric("أطوال المصائد (م)", f"{calc['trap_lengths']:,.2f}")
                st.metric("زيادة أعماق المناهل (م)", f"{calc['manhole_depth_increase']:,.2f}")
                st.metric("عرض الخندق (م)", f"{calc['trench_width']:.2f}")
        
        # تصدير
        if st.button("📥 تصدير CSV متقدم", key="export_csv_adv"):
            csv_content = "البند,الكمية,الوحدة,السعر,الإجمالي\n"
            for item in report['items']:
                csv_content += f'"{item["name"]}",{item["qty"]:.2f},{item["unit"]},{item["price"]:.0f},{item["total"]:.0f}\n'
            csv_content += f"المجموع,,,{report['total']:.0f}\n"
            
            st.download_button(
                label="⬇️ تحميل CSV",
                data=csv_content,
                file_name=f"advanced_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

st.markdown("<div style='text-align:center;color:#999;font-size:0.75rem;margin-top:20px'>© 2025 Flood Drainage Networks with Interactive Maps</div>", unsafe_allow_html=True)

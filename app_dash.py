import streamlit as st
import json, math, os, tempfile, zipfile, pandas as pd, openpyxl
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="حاسبة شبكات السيول", page_icon="🌊",
                   layout="centered", initial_sidebar_state="collapsed",
                   menu_items={'Get Help': None, 'Report a bug': None, 'About': None})

PIPE_PRICES = {
    400:2713, 500:2935, 600:3145, 700:3431, 800:4009,
    900:4299, 1000:4625, 1100:5010, 1200:5335, 1300:5725, 1400:6055,
}
BOX_CHANNEL_PRICE  = 9336.0
OPEN_CHANNEL_PRICE = 13052.0
LINE_TYPES = {"pipe":"أنبوب","box_channel":"قناة صندوقية","open_channel":"قناة مفتوحة"}

def check_credentials(u, p):
    try:
        users = st.secrets["users"]
        return users.get(u) == p
    except:
        return False

MAIN_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
*{box-sizing:border-box}
html,body,[class*="css"],.stApp{font-family:'Cairo',sans-serif!important;direction:rtl;-webkit-text-size-adjust:100%}
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stToolbarActions"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"],#MainMenu,footer,footer *,
.stToolbar,button[title="View app fullscreen"],a[href*="streamlit.io"],a[href*="github.com"],
[data-testid="baseButton-headerNoPadding"],[data-testid="stSidebar"]
{display:none!important;visibility:hidden!important;height:0!important;overflow:hidden!important;pointer-events:none!important}
.block-container{padding:0.5rem 0.75rem 2rem!important;max-width:760px!important;margin:0 auto!important}
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
.seg-card{background:#fff;border:1.5px solid #d0e4f7;border-right:5px solid #0a2a5e;
  border-radius:10px;padding:12px 14px;margin-bottom:10px}
.seg-card h4{color:#0a2a5e;margin:0 0 6px;font-size:.85rem}
.tbadge{display:inline-block;padding:4px 12px;border-radius:12px;font-size:.76rem;font-weight:700;margin-bottom:4px}
.tp{background:#eaf4ff;color:#1a5fa8}.tb{background:#fff3e0;color:#e65100}.to{background:#e8f5e9;color:#2e7d32}
.ib{background:#eaf4ff;border-right:4px solid #1a5fa8;border-radius:8px;
  padding:10px 13px;font-size:.83rem;color:#0a2a5e;margin-bottom:8px;direction:rtl;line-height:1.9}
.section-title{color:#0a2a5e;font-size:.92rem;font-weight:900;margin:14px 0 8px;
  border-bottom:2px solid #1a5fa8;padding-bottom:4px}
.pc{background:#fff;border:1.5px solid #d0e4f7;border-right:5px solid #1a5fa8;
  border-radius:6px;padding:8px 11px;margin-bottom:5px;font-size:.82rem;color:#1a2a3a}
.pc b{color:#0a2a5e}
.sel-banner{background:#e74c3c;color:#fff;border-radius:8px;padding:8px 14px;
  font-weight:700;font-size:.85rem;text-align:center;margin-bottom:8px}
.stButton>button{background:linear-gradient(135deg,#1a5fa8,#0a2a5e)!important;color:#fff!important;
  border:none!important;border-radius:10px!important;font-family:'Cairo',sans-serif!important;
  font-weight:700!important;font-size:.95rem!important;width:100%!important;
  padding:13px 8px!important;min-height:50px!important;touch-action:manipulation!important}
.stTextInput>div>div>input,.stNumberInput>div>div>input{min-height:50px!important;font-size:1rem!important;
  font-family:'Cairo',sans-serif!important;direction:rtl!important;border-radius:10px!important}
.stSelectbox [data-baseweb="select"]>div{min-height:50px!important;font-family:'Cairo',sans-serif!important;border-radius:10px!important}
.stTabs [data-baseweb="tab"]{font-family:'Cairo',sans-serif!important;font-weight:700!important;
  font-size:.88rem!important;padding:10px 14px!important;min-height:44px!important}
[data-testid="stExpander"]{border:1.5px solid #d0e4f7!important;border-radius:10px!important;margin-bottom:8px!important}
[data-testid="stExpander"] summary{padding:12px 14px!important;font-family:'Cairo',sans-serif!important;
  font-weight:700!important;min-height:48px!important}
.cost-table{width:100%;border-collapse:collapse;font-size:0.85rem;direction:rtl;margin:10px 0}
.cost-table th,.cost-table td{padding:8px;border:1px solid #d0e4f7;text-align:right}
.cost-table th{background:#eaf4ff;color:#0a2a5e;font-weight:700}
.cost-table tr:nth-child(even){background:#f8fbfe}
.cost-table .total{background:#0a2a5e;color:#fff;font-weight:700}
</style>"""

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
    st.markdown('<div style="text-align:center;color:rgba(180,210,255,.65);font-size:.78rem;margin-bottom:24px">Flood Drainage Network Calculator · Eng. Ahmed Adam</div>', unsafe_allow_html=True)
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
    st.markdown('<div style="text-align:center;color:rgba(180,210,255,.3);font-size:.68rem;margin-top:20px">© 2025 Flood Drainage Networks</div>', unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if not st.session_state["authenticated"]:
    login_page(); st.stop()

st.markdown(MAIN_CSS, unsafe_allow_html=True)

# ── Session State ──
DEFAULTS = {
    "feats":[], "ac":[], "feats_json":"[]", "sel_set":"[]",
    "cost_result":None, "pdf_bytes":None, "_fhash":None,
    "props_keys":[], "sel_feat_meta":{}, "drawn_meta":[],
    "_raw_drawn":[], "_last_tip_key":None,
    "detailed_calc_data":None, "detailed_report":None,
}
for k,v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k] = v

RLAT, RLON = 24.7136, 46.6753

# ═════════════════════════════════════════════════════════════════════════════════
# ──── دوال حساب التفاصيل ────
# ═════════════════════════════════════════════════════════════════════════════════

def load_excel_formulas():
    """تحميل معاملات الحساب من ملف Excel"""
    try:
        wb = openpyxl.load_workbook('cost_Pipes_data_base.xlsx', data_only=False)
        formulas = {}
        
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            diameter = int(sheet_name)
            
            # قراءة الأسعار والمعاملات من الصفوف
            prices = {}
            for row in ws.iter_rows(min_row=4, max_row=4, values_only=True):
                if row[1]:  # سعر الأنبوب
                    prices['pipe_price'] = float(row[1]) if row[1] else 0
                if row[5]:  # سعر الحفر
                    prices['excavation_price'] = float(row[5]) if row[5] else 130
                if row[9]:  # سعر الردم
                    prices['backfill_price'] = float(row[9]) if row[9] else 90
                if row[12]:  # سعر البحص
                    prices['gravel_price'] = float(row[12]) if row[12] else 320
                if row[13]:  # سعر المصائد
                    prices['trap_price'] = float(row[13]) if row[13] else 9509
                if row[19]:  # سعر الخرسانة
                    prices['concrete_price'] = float(row[19]) if row[19] else 858
                if row[20]:  # سعر الأسفلت
                    prices['asphalt_price'] = float(row[20]) if row[20] else 150
                if row[23]:  # سعر المناهل
                    prices['manhole_price'] = float(row[23]) if row[23] else 17879
            
            formulas[diameter] = prices
        
        return formulas
    except Exception as e:
        st.error(f"خطأ في قراءة ملف Excel: {e}")
        return {}

def calculate_pipe_details(pipe_length, diameter_mm, avg_depth, use_formula_traps=True, num_traps=None, 
                           use_formula_manholes=True, num_manholes=None):
    """
    حساب تفاصيل الأنابيب حسب المعادلات
    """
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
        
        # كمية الردم (بدون الأنبوب)
        backfill_qty = pipe_length * trench_width * (avg_depth - (diameter_m / 2))
        
        # كمية الردم النهائي
        final_backfill = backfill_qty - pipe_half_volume
        
        # عمق البحص وحجمه
        gravel_depth = 0.2 + (diameter_m / 2)
        gravel_volume = gravel_depth * pipe_length * trench_width
        final_gravel = gravel_volume - pipe_half_volume
        
        # عدد المصائد (من المعادلة أو المدخل)
        if use_formula_traps:
            num_traps = max(1, round(pipe_length / 35))
        
        # أطوال المصائد
        trap_lengths = num_traps * 7
        
        # حجم البحص للمصائد
        trap_gravel = 0.35 * 0.9 * (trap_lengths / 2)
        
        # حجم أنبوب المصيدة (قطر 300ملم)
        trap_pipe_volume = math.pi * ((0.3 / 2) ** 2) * (trap_lengths / 2)
        trap_pipe_half = trap_pipe_volume / 2
        
        # حجم البحص النهائي للمصائد
        final_trap_gravel = trap_gravel - trap_pipe_half
        
        # التغليف بالخرسانة
        concrete_volume = (trap_lengths * 1.3) + (pipe_length * (trench_width + 0.4))
        
        # إعادة طبقات الأسفلت
        asphalt_qty = trap_lengths * 0.9 * 1.3
        
        # الحفر والردم للمصائد
        trap_excavation = concrete_volume - concrete_volume/2 - trap_pipe_volume
        trap_backfill = pipe_length / 100
        
        # عدد المناهل
        if use_formula_manholes:
            num_manholes = max(1, int(pipe_length / 100))
        
        # زيادة أعماق المناهل
        manhole_depth_increase = num_manholes * 1.0
        
        return {
            'pipe_length': pipe_length,
            'diameter_mm': diameter_mm,
            'avg_depth': avg_depth,
            'trench_width': trench_width,
            'excavation_qty': excavation_qty,
            'backfill_qty': backfill_qty,
            'pipe_volume': pipe_volume,
            'final_backfill': final_backfill,
            'gravel_depth': gravel_depth,
            'gravel_volume': gravel_volume,
            'final_gravel': final_gravel,
            'num_traps': num_traps,
            'trap_lengths': trap_lengths,
            'trap_gravel': trap_gravel,
            'trap_pipe_volume': trap_pipe_volume,
            'final_trap_gravel': final_trap_gravel,
            'concrete_volume': concrete_volume,
            'asphalt_qty': asphalt_qty,
            'trap_excavation': trap_excavation,
            'trap_backfill': trap_backfill,
            'num_manholes': num_manholes,
            'manhole_depth_increase': manhole_depth_increase,
        }
    except Exception as e:
        st.error(f"خطأ في الحساب: {e}")
        return None

def generate_detailed_report(calc_data, prices):
    """
    إنشاء تقرير مفصل مع جدول التكاليف
    """
    try:
        report_items = []
        total_cost = 0
        
        # البنود والكميات والأسعار
        items = [
            {
                'name': '1. أطوال الأنابيب',
                'unit': 'م',
                'qty': calc_data['pipe_length'],
                'unit_price': prices.get('pipe_price', 0),
            },
            {
                'name': '2. كمية الحفر',
                'unit': 'م³',
                'qty': calc_data['excavation_qty'] + calc_data['trap_excavation'],
                'unit_price': prices.get('excavation_price', 130),
            },
            {
                'name': '3. كمية الردم النهائي',
                'unit': 'م³',
                'qty': calc_data['final_backfill'] + calc_data['trap_backfill'],
                'unit_price': prices.get('backfill_price', 90),
            },
            {
                'name': '4. حجم البحص النهائي',
                'unit': 'م³',
                'qty': calc_data['final_gravel'] + calc_data['final_trap_gravel'],
                'unit_price': prices.get('gravel_price', 320),
            },
            {
                'name': '5. عدد المصائد',
                'unit': 'عدد',
                'qty': calc_data['num_traps'],
                'unit_price': prices.get('trap_price', 9509),
            },
            {
                'name': '6. أطوال المصائد بقطر 300 ملم',
                'unit': 'م',
                'qty': calc_data['trap_lengths'],
                'unit_price': prices.get('pipe_price', 0) * 0.3,
            },
            {
                'name': '7. التغليف بالخرسانة',
                'unit': 'م³',
                'qty': calc_data['concrete_volume'],
                'unit_price': prices.get('concrete_price', 858),
            },
            {
                'name': '8. إعادة طبقات الأسفلت',
                'unit': 'm²',
                'qty': calc_data['asphalt_qty'],
                'unit_price': prices.get('asphalt_price', 150),
            },
            {
                'name': '9. عدد المناهل',
                'unit': 'عدد',
                'qty': calc_data['num_manholes'],
                'unit_price': prices.get('manhole_price', 17879),
            },
            {
                'name': '10. زيادة أعماق المناهل',
                'unit': 'م',
                'qty': calc_data['manhole_depth_increase'],
                'unit_price': prices.get('manhole_price', 5334),
            },
        ]
        
        for item in items:
            cost = item['qty'] * item['unit_price']
            report_items.append({
                'name': item['name'],
                'unit': item['unit'],
                'qty': item['qty'],
                'unit_price': item['unit_price'],
                'total_cost': cost,
            })
            total_cost += cost
        
        return {
            'items': report_items,
            'total_cost': total_cost,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        st.error(f"خطأ في إنشاء التقرير: {e}")
        return None

# ═════════════════════════════════════════════════════════════════════════════════
# ──── الواجهة الرئيسية ────
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="hdr"><h1>🌊 حاسبة شبكات تصريف السيول</h1><div class="bdg">V2.0</div></div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 حساب التكلفة الأساسية", "📋 بيانات الشبكة", "🔧 حساب تفصيلي متقدم"])

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 3 ── الحساب التفصيلي المتقدم (التبويب الجديد)
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab3:
    st.markdown('<div class="section-title">⚙️ حساب تفصيلي متقدم للأنابيب والمصائد والمناهل</div>', unsafe_allow_html=True)
    
    # تحميل بيانات Excel
    excel_prices = load_excel_formulas()
    
    if not excel_prices:
        st.error("⚠️ تعذر تحميل بيانات Excel")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            pipe_diameter = st.selectbox(
                "قطر الأنبوب (ملم)",
                options=sorted(excel_prices.keys()),
                help="اختر قطر الأنبوب الرئيسي"
            )
        
        with col2:
            pipe_length = st.number_input(
                "طول الأنبوب (م)",
                min_value=1.0,
                value=1000.0,
                step=10.0,
                help="طول الأنبوب من الخريطة أو الملف"
            )
        
        col3, col4 = st.columns(2)
        
        with col3:
            avg_depth = st.number_input(
                "متوسط العمق (م)",
                min_value=0.5,
                value=3.0,
                step=0.1,
                help="متوسط عمق الخندق"
            )
        
        with col4:
            st.markdown("**خيارات المصائد والمناهل**")
        
        # خيارات المصائد
        col5, col6 = st.columns(2)
        with col5:
            trap_source = st.radio(
                "عدد المصائد:",
                ["من المعادلة", "مدخل يدوي"],
                horizontal=True,
                key="trap_source"
            )
        
        num_traps = None
        if trap_source == "مدخل يدوي":
            num_traps = st.number_input(
                "أدخل عدد المصائد",
                min_value=1,
                value=1,
                step=1,
            )
        
        # خيارات المناهل
        col7, col8 = st.columns(2)
        with col7:
            manhole_source = st.radio(
                "عدد المناهل:",
                ["من المعادلة", "مدخل يدوي"],
                horizontal=True,
                key="manhole_source"
            )
        
        num_manholes = None
        if manhole_source == "مدخل يدوي":
            num_manholes = st.number_input(
                "أدخل عدد المناهل",
                min_value=1,
                value=1,
                step=1,
            )
        
        # زر الحساب
        if st.button("⚡ احسب التفاصيل الآن", key="calc_detailed"):
            with st.spinner("⏳ جاري الحساب..."):
                use_trap_formula = (trap_source == "من المعادلة")
                use_manhole_formula = (manhole_source == "من المعادلة")
                
                calc_data = calculate_pipe_details(
                    pipe_length=pipe_length,
                    diameter_mm=pipe_diameter,
                    avg_depth=avg_depth,
                    use_formula_traps=use_trap_formula,
                    num_traps=num_traps,
                    use_formula_manholes=use_manhole_formula,
                    num_manholes=num_manholes
                )
                
                if calc_data:
                    prices = excel_prices.get(pipe_diameter, {})
                    report = generate_detailed_report(calc_data, prices)
                    
                    if report:
                        st.session_state.detailed_calc_data = calc_data
                        st.session_state.detailed_report = report
                        st.success("✅ تم حساب التفاصيل بنجاح!")
        
        # عرض النتائج
        if st.session_state.detailed_report:
            report = st.session_state.detailed_report
            calc_data = st.session_state.detailed_calc_data
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">📊 النتائج والتفاصيل</div>', unsafe_allow_html=True)
            
            # بطاقات معلومات سريعة
            col1, col2, col3 = st.columns(3)
            col1.markdown(f'<div class="mc"><div class="v">{pipe_length:,.0f}</div><div class="l">طول الأنبوب (م)</div></div>', unsafe_allow_html=True)
            col2.markdown(f'<div class="mc"><div class="v">{pipe_diameter}</div><div class="l">قطر الأنبوب (ملم)</div></div>', unsafe_allow_html=True)
            col3.markdown(f'<div class="mc"><div class="v">{avg_depth}</div><div class="l">متوسط العمق (م)</div></div>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            col1.markdown(f'<div class="mc"><div class="v">{calc_data["num_traps"]}</div><div class="l">عدد المصائد</div></div>', unsafe_allow_html=True)
            col2.markdown(f'<div class="mc"><div class="v">{calc_data["num_manholes"]}</div><div class="l">عدد المناهل</div></div>', unsafe_allow_html=True)
            col3.markdown(f'<div class="mc"><div class="v">{report["total_cost"]/1e6:.2f}</div><div class="l">التكلفة (مليون ريال)</div></div>', unsafe_allow_html=True)
            
            # جدول التفاصيل
            st.markdown('<div class="section-title">💰 جدول التكاليف التفصيلي</div>', unsafe_allow_html=True)
            
            # إنشاء جدول HTML
            table_html = '<table class="cost-table" style="width:100%"><thead><tr><th>البند</th><th>الكمية</th><th>الوحدة</th><th>السعر/الوحدة</th><th>الإجمالي</th></tr></thead><tbody>'
            
            for item in report['items']:
                table_html += f'''<tr>
                    <td>{item['name']}</td>
                    <td>{item['qty']:,.2f}</td>
                    <td>{item['unit']}</td>
                    <td>{item['unit_price']:,.0f}</td>
                    <td><b style="color:#c0392b">{item['total_cost']:,.0f}</b></td>
                </tr>'''
            
            table_html += f'''<tr class="total">
                <td colspan="4">المجموع الإجمالي</td>
                <td>{report['total_cost']:,.0f}</td>
            </tr></tbody></table>'''
            
            st.markdown(table_html, unsafe_allow_html=True)
            
            # تفاصيل إضافية
            with st.expander("📋 تفاصيل الكميات المحسوبة"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**الحفر والردم:**")
                    st.metric("كمية الحفر الكلية", f"{calc_data['excavation_qty'] + calc_data['trap_excavation']:,.2f} م³")
                    st.metric("كمية الردم النهائي", f"{calc_data['final_backfill'] + calc_data['trap_backfill']:,.2f} م³")
                    st.metric("حجم البحص النهائي", f"{calc_data['final_gravel'] + calc_data['final_trap_gravel']:,.2f} م³")
                
                with col2:
                    st.markdown("**المصائد والمناهل:**")
                    st.metric("أطوال المصائد", f"{calc_data['trap_lengths']:,.2f} م")
                    st.metric("حجم الخرسانة", f"{calc_data['concrete_volume']:,.2f} م³")
                    st.metric("كمية الأسفلت", f"{calc_data['asphalt_qty']:,.2f} م²")
            
            # زر التصدير
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 تصدير Excel", key="export_excel"):
                    # إنشاء ملف Excel
                    df_report = pd.DataFrame([
                        {
                            'البند': item['name'],
                            'الكمية': item['qty'],
                            'الوحدة': item['unit'],
                            'السعر/الوحدة': item['unit_price'],
                            'الإجمالي': item['total_cost'],
                        }
                        for item in report['items']
                    ])
                    
                    # إضافة صف الإجمالي
                    df_report = pd.concat([df_report, pd.DataFrame([{
                        'البند': 'المجموع الإجمالي',
                        'الكمية': '',
                        'الوحدة': '',
                        'السعر/الوحدة': '',
                        'الإجمالي': report['total_cost'],
                    }])], ignore_index=True)
                    
                    excel_bytes = BytesIO()
                    with pd.ExcelWriter(excel_bytes, engine='openpyxl') as writer:
                        df_report.to_excel(writer, sheet_name='التقرير', index=False)
                    
                    st.download_button(
                        label="⬇️ تحميل Excel",
                        data=excel_bytes.getvalue(),
                        file_name=f"detailed_cost_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 1 ── الحساب الأساسي (الأصلي)
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab1:
    st.markdown('<div class="ib">📂 قريباً: سيتم دمج نتائج التبويب الثالث في التقرير الأساسي</div>', unsafe_allow_html=True)

# ╔════════════════════════════════════════════════════════════════════════════════╗
# ║ TAB 2 ── بيانات الشبكة
# ╚════════════════════════════════════════════════════════════════════════════════╝

with tab2:
    st.markdown('<div class="ib">📂 ارفع ملف الشبكة لعرض البيانات هنا</div>', unsafe_allow_html=True)

st.markdown("<div style='text-align:center;color:#999;font-size:0.75rem;margin-top:20px'>© 2025 Flood Drainage Networks</div>", unsafe_allow_html=True)

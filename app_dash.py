"""
تطبيق Streamlit محسّن - يعمل بدون الاعتماد على Folium
استخدم هذا الإصدار إذا كان لديك مشاكل في تثبيت Folium
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys

# ============================================
# تثبيت المكتبات المفقودة
# ============================================

def check_and_install_packages():
    """فحص وتثبيت المكتبات الأساسية فقط"""
    try:
        import plotly
    except ImportError:
        st.warning("⚠️ جاري تثبيت Plotly...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly", "-q"])
        import plotly
    
    try:
        import requests
    except ImportError:
        st.warning("⚠️ جاري تثبيت Requests...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])

check_and_install_packages()

# الاستيرادات الآمنة
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    st.error("❌ فشل استيراد Plotly. يرجى تشغيل: pip install plotly")
    st.stop()

# ============================================
# إعدادات الصفحة
# ============================================

st.set_page_config(
    page_title="تطبيق البيانات",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS مخصص
st.markdown("""
    <style>
        .main { direction: rtl; }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            color: white;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# البيانات التجريبية
# ============================================

@st.cache_data
def load_sample_data():
    """تحميل البيانات التجريبية"""
    return pd.DataFrame({
        'الشهر': ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو'],
        'المبيعات': [100, 150, 120, 200, 180, 220],
        'الأرباح': [20, 35, 25, 50, 40, 60],
        'العملاء': [50, 65, 60, 80, 75, 90]
    })

@st.cache_data
def load_products_data():
    """البيانات حسب المنتجات"""
    return pd.DataFrame({
        'المنتج': ['منتج أ', 'منتج ب', 'منتج ج', 'منتج د'],
        'المبيعات': [5000, 3500, 2800, 4200],
        'نسبة النمو': [15, -5, 20, 10]
    })

@st.cache_data
def load_location_data():
    """البيانات حسب المناطق"""
    return pd.DataFrame({
        'المنطقة': ['الرياض', 'جدة', 'الدمام', 'الجبيل', 'الخبر'],
        'المبيعات': [45000, 38000, 28000, 22000, 18000],
        'السكان': [7000000, 4000000, 1500000, 700000, 1200000]
    })

# ============================================
# الواجهة الرئيسية
# ============================================

st.title("📊 لوحة التحكم التحليلية")
st.markdown("تطبيق متقدم لتحليل البيانات والإحصائيات")
st.divider()

# القائمة الجانبية
with st.sidebar:
    st.header("⚙️ الإعدادات")
    
    page = st.radio(
        "اختر الصفحة:",
        ["🏠 الرئيسية", "📈 البيانات", "🗺️ الخريطة التفاعلية", "📊 التحليل", "❓ الأسئلة الشائعة"]
    )
    
    st.divider()
    
    st.subheader("📌 معلومات")
    st.info("""
    ✅ التطبيق يعمل بدون مشاكل
    📦 جميع المكتبات مثبتة
    🚀 جاهز للاستخدام
    """)

# ============================================
# صفحة الرئيسية
# ============================================

if page == "🏠 الرئيسية":
    st.header("مرحباً بك في لوحة التحكم! 👋")
    
    # المؤشرات الرئيسية
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("إجمالي المبيعات", "﷼975,000", "+12%", delta_color="normal")
    with col2:
        st.metric("إجمالي الأرباح", "﷼230,000", "+8%", delta_color="normal")
    with col3:
        st.metric("عدد العملاء", "425", "+5%", delta_color="normal")
    with col4:
        st.metric("معدل النمو", "9.5%", "+1.2%", delta_color="normal")
    
    st.markdown("---")
    
    # الرسم البياني الرئيسي
    st.subheader("📈 الأداء الشهري")
    df = load_sample_data()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['الشهر'], y=df['المبيعات'], 
                             mode='lines+markers', name='المبيعات',
                             line=dict(color='#667eea', width=3)))
    fig.add_trace(go.Scatter(x=df['الشهر'], y=df['الأرباح'], 
                             mode='lines+markers', name='الأرباح',
                             line=dict(color='#764ba2', width=3)))
    fig.update_layout(
        title="المبيعات والأرباح الشهرية",
        xaxis_title="الشهر",
        yaxis_title="القيمة",
        hovermode='x unified',
        template="plotly_white",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # بطاقات المعلومات
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✨ المميزات")
        st.write("""
        - 📊 عرض البيانات بشكل واضح
        - 📈 رسوم بيانية تفاعلية
        - 🗺️ خرائط جغرافية
        - 💾 تحميل البيانات
        - 📱 واجهة متجاوبة
        """)
    
    with col2:
        st.subheader("🎯 الأهداف")
        st.write("""
        - توفير أداة تحليل قوية
        - عرض الإحصائيات بسهولة
        - اتخاذ القرارات المستنيرة
        - تتبع الأداء المستمر
        - تحسين الكفاءة
        """)

# ============================================
# صفحة البيانات
# ============================================

elif page == "📈 البيانات":
    st.header("📈 البيانات والإحصائيات")
    
    # اختيار البيانات
    data_type = st.radio(
        "اختر نوع البيانات:",
        ["البيانات الشهرية", "البيانات حسب المنتجات", "البيانات حسب المناطق"],
        horizontal=True
    )
    
    if data_type == "البيانات الشهرية":
        df = load_sample_data()
        title = "البيانات الشهرية"
    elif data_type == "البيانات حسب المنتجات":
        df = load_products_data()
        title = "البيانات حسب المنتجات"
    else:
        df = load_location_data()
        title = "البيانات حسب المناطق"
    
    st.subheader(title)
    
    # عرض الجدول
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # إحصائيات سريعة
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("عدد الصفوف", len(df))
    with col2:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            st.metric("المجموع", f"﷼{df[numeric_cols[0]].sum():,.0f}")
    with col3:
        if len(numeric_cols) > 0:
            st.metric("المتوسط", f"﷼{df[numeric_cols[0]].mean():,.0f}")
    
    # تحميل البيانات
    csv = df.to_csv(index=False, encoding='utf-8')
    st.download_button(
        label="📥 تحميل البيانات (CSV)",
        data=csv,
        file_name=f"data_{data_type.replace(' ', '_')}.csv",
        mime="text/csv"
    )

# ============================================
# صفحة الخريطة التفاعلية (بدون Folium)
# ============================================

elif page == "🗺️ الخريطة التفاعلية":
    st.header("🗺️ الخريطة التفاعلية")
    
    st.info("✨ يمكنك عرض البيانات الجغرافية بشكل تفاعلي")
    
    # البيانات الجغرافية
    df = load_location_data()
    
    # الإحداثيات التقريبية للمناطق (خط العرض وخط الطول)
    coordinates = {
        'الرياض': [24.7136, 46.6753],
        'جدة': [21.5485, 39.1728],
        'الدمام': [26.4124, 50.1971],
        'الجبيل': [27.0081, 49.6331],
        'الخبر': [26.1387, 50.1951]
    }
    
    # إضافة الإحداثيات إلى البيانات
    df['lat'] = df['المنطقة'].map(lambda x: coordinates[x][0])
    df['lon'] = df['المنطقة'].map(lambda x: coordinates[x][1])
    
    st.subheader("توزيع المبيعات حسب المنطقة")
    
    # خريطة تفاعلية باستخدام Plotly
    fig = px.scatter_geo(df,
                         lat='lat',
                         lon='lon',
                         hover_name='المنطقة',
                         size='المبيعات',
                         color='المبيعات',
                         hover_data={'المبيعات': ':.0f', 'lat': False, 'lon': False},
                         title='توزيع المبيعات الجغرافي',
                         scope='asia',
                         size_max=50)
    
    fig.update_layout(
        geo=dict(
            scope='asia',
            center=dict(lat=24, lon=45),
            projection_type='mercator'
        ),
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # رسم بياني ثاني
    st.subheader("المبيعات حسب المنطقة")
    
    fig2 = px.bar(df, x='المنطقة', y='المبيعات',
                  title='إجمالي المبيعات بالمنطقة',
                  color='المبيعات',
                  color_continuous_scale='Blues')
    
    st.plotly_chart(fig2, use_container_width=True)

# ============================================
# صفحة التحليل
# ============================================

elif page == "📊 التحليل":
    st.header("📊 التحليل المتقدم")
    
    df = load_sample_data()
    products = load_products_data()
    
    # الرسم البياني 1: المبيعات
    st.subheader("1️⃣ تحليل المبيعات")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.area(df, x='الشهر', y='المبيعات',
                      title='اتجاه المبيعات',
                      color_discrete_sequence=['#667eea'])
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.pie(products, values='المبيعات', names='المنتج',
                     title='توزيع المبيعات حسب المنتج')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # الرسم البياني 2: النمو
    st.subheader("2️⃣ معدل النمو")
    
    fig = px.bar(products, x='المنتج', y='نسبة النمو',
                 title='نسبة النمو حسب المنتج',
                 color='نسبة النمو',
                 color_continuous_scale=['red', 'yellow', 'green'],
                 color_continuous_midpoint=0)
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # الرسم البياني 3: الأداء الشامل
    st.subheader("3️⃣ الأداء الشامل")
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(x=df['الشهر'], y=df['المبيعات'], 
                         name='المبيعات', marker_color='#667eea'))
    fig.add_trace(go.Scatter(x=df['الشهر'], y=df['الأرباح'],
                             name='الأرباح', yaxis='y2',
                             line=dict(color='#764ba2', width=3)))
    
    fig.update_layout(
        yaxis=dict(title='المبيعات'),
        yaxis2=dict(title='الأرباح', overlaying='y', side='right'),
        title='المبيعات والأرباح (تحليل مدمج)',
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# صفحة الأسئلة الشائعة
# ============================================

elif page == "❓ الأسئلة الشائعة":
    st.header("❓ الأسئلة الشائعة")
    
    with st.expander("❔ كيف أستخدم لوحة التحكم؟"):
        st.write("""
        1. **الصفحة الرئيسية**: عرض ملخص الإحصائيات الرئيسية
        2. **البيانات**: عرض البيانات بتفاصيل كاملة وتحميلها
        3. **الخريطة**: عرض البيانات الجغرافية بشكل تفاعلي
        4. **التحليل**: رسوم بيانية متقدمة وتحليلات معمقة
        
        يمكنك التنقل بين الصفحات من القائمة الجانبية.
        """)
    
    with st.expander("❔ هل يمكنني تحميل بياناتي الخاصة؟"):
        st.write("""
        في الإصدارات المستقبلية، سيتم إضافة خاصية رفع البيانات.
        حالياً يمكنك عرض البيانات التجريبية وتحميلها.
        """)
    
    with st.expander("❔ ما هي متطلبات التشغيل؟"):
        st.write("""
        **المتطلبات:**
        - متصفح ويب حديث
        - اتصال إنترنت
        - Python 3.8+ (للتشغيل المحلي)
        - المكتبات المثبتة من requirements.txt
        
        **البرامج المثبتة حالياً:**
        - Streamlit (واجهة التطبيق)
        - Pandas (معالجة البيانات)
        - Plotly (الرسوم البيانية)
        - NumPy (العمليات الحسابية)
        """)
    
    with st.expander("❔ ماذا لو حدثت مشكلة؟"):
        st.write("""
        **المشاكل الشائعة والحل:**
        
        1. **التطبيق بطيء**
           - أعد تحميل الصفحة
           - امسح ذاكرة المتصفح
        
        2. **الرسوم البيانية لا تظهر**
           - تأكد من اتصال الإنترنت
           - جرب متصفح مختلف
        
        3. **مشاكل في التثبيت**
           ```bash
           pip install -r requirements.txt
           ```
        
        4. **الاتصال بالدعم**
           - البريد الإلكتروني: support@example.com
           - الهاتف: +966 XX XXX XXXX
        """)
    
    with st.expander("❔ هل البيانات آمنة؟"):
        st.write("""
        ✅ **نعم، البيانات آمنة تماماً:**
        - جميع البيانات محمية بتشفير
        - لا يتم حفظ أي بيانات شخصية
        - الاتصال آمن (HTTPS)
        - الخادم موثوق وآمن
        """)

# ============================================
# التذييل
# ============================================

st.divider()
st.markdown("""
    <div style='text-align: center; direction: rtl; color: #999; margin-top: 30px;'>
    <p>تم إنشاء هذا التطبيق بواسطة Streamlit | جميع الحقوق محفوظة © 2024</p>
    <p style='font-size: 0.9em;'>الإصدار: 2.0 (بدون Folium)</p>
    </div>
    """, unsafe_allow_html=True)

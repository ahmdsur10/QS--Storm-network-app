"""
تطبيق Streamlit محسّن مع معالجة أخطاء الاستيرادات
"""

import sys
import subprocess
import streamlit as st

# ============================================
# معالجة الاستيرادات والمكتبات الناقصة
# ============================================

def install_missing_packages():
    """تثبيت المكتبات الناقصة تلقائياً"""
    required_packages = {
        'folium': 'folium',
        'streamlit_folium': 'streamlit-folium',
        'pandas': 'pandas',
        'plotly': 'plotly',
        'requests': 'requests',
        'geopy': 'geopy'
    }
    
    missing_packages = []
    
    for lib_name, package_name in required_packages.items():
        try:
            __import__(lib_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        st.warning(f"⚠️ جاري تثبيت المكتبات المفقودة: {', '.join(missing_packages)}")
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])
            except Exception as e:
                st.error(f"❌ خطأ في تثبيت {package}: {str(e)}")
                st.info("📋 يرجى تثبيت المكتبات يدوياً باستخدام: pip install -r requirements.txt")
                return False
    
    return True

# تثبيت المكتبات إذا لزم الأمر
if not install_missing_packages():
    st.stop()

# ============================================
# الاستيرادات الآمنة
# ============================================

try:
    import folium
    from streamlit_folium import st_folium
    import pandas as pd
    import plotly.express as px
    import requests
    from geopy.geocoders import Nominatim
except ImportError as e:
    st.error(f"❌ خطأ في استيراد المكتبات: {str(e)}")
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

# ============================================
# CSS مخصص
# ============================================

st.markdown("""
    <style>
    .main {
        direction: rtl;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================
# الواجهة الرئيسية
# ============================================

st.title("📊 تطبيق لوحة التحكم")
st.markdown("---")

# الشريط الجانبي
with st.sidebar:
    st.header("⚙️ الإعدادات")
    page = st.radio(
        "اختر الصفحة:",
        ["🏠 الرئيسية", "📈 البيانات", "🗺️ الخريطة", "ℹ️ المساعدة"]
    )

# ============================================
# المحتوى حسب الصفحة المختارة
# ============================================

if page == "🏠 الرئيسية":
    st.header("مرحباً بك! 👋")
    st.write("هذا التطبيق يعرض لك البيانات والخرائط بشكل متقدم.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("إجمالي البيانات", "1,234")
    with col2:
        st.metric("المستخدمين النشطين", "567")
    with col3:
        st.metric("نسبة النمو", "23%")

elif page == "📈 البيانات":
    st.header("📈 عرض البيانات")
    
    # إنشاء بيانات تجريبية
    try:
        data = pd.DataFrame({
            'الشهر': ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو'],
            'المبيعات': [100, 150, 120, 200, 180, 220],
            'الأرباح': [20, 35, 25, 50, 40, 60]
        })
        
        # عرض الجدول
        st.subheader("البيانات الجدولية")
        st.dataframe(data, use_container_width=True)
        
        # رسم بياني
        st.subheader("الرسم البياني")
        fig = px.line(data, x='الشهر', y=['المبيعات', 'الأرباح'], 
                     title='المبيعات والأرباح الشهرية',
                     markers=True)
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ خطأ في عرض البيانات: {str(e)}")

elif page == "🗺️ الخريطة":
    st.header("🗺️ الخريطة التفاعلية")
    
    try:
        # إنشاء خريطة
        m = folium.Map(
            location=[24.7136, 46.6753],  # إحداثيات الرياض
            zoom_start=12,
            tiles="OpenStreetMap"
        )
        
        # إضافة علامة
        folium.Marker(
            location=[24.7136, 46.6753],
            popup="الرياض",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)
        
        # عرض الخريطة
        st_folium(m, width=700, height=500)
        
    except Exception as e:
        st.error(f"❌ خطأ في عرض الخريطة: {str(e)}")

elif page == "ℹ️ المساعدة":
    st.header("ℹ️ المساعدة والدعم")
    
    st.markdown("""
    ### 📋 تعليمات الاستخدام:
    
    1. **الصفحة الرئيسية**: عرض ملخص الإحصائيات الرئيسية
    2. **البيانات**: عرض البيانات في جداول ورسوم بيانية
    3. **الخريطة**: عرض خريطة تفاعلية
    
    ### 🔧 حل المشاكل الشائعة:
    
    **المشكلة**: خطأ ModuleNotFoundError
    - **الحل**: تثبيت المكتبات من `requirements.txt`
    ```bash
    pip install -r requirements.txt
    ```
    
    **المشكلة**: الخريطة لا تظهر
    - **الحل**: التأكد من اتصال الإنترنت
    
    **المشكلة**: البيانات لا تحمّل
    - **الحل**: تحديث الصفحة (F5)
    
    ### 📞 التواصل:
    للدعم الفني، يرجى التواصل عبر البريد الإلكتروني.
    """)

# ============================================
# تذييل الصفحة
# ============================================

st.markdown("---")
st.markdown("""
    <div style='text-align: center; direction: rtl;'>
    <p>تم إنشاء هذا التطبيق بواسطة Streamlit | جميع الحقوق محفوظة ©</p>
    </div>
    """, unsafe_allow_html=True)

"""
تطبيق Streamlit بسيط جداً - بدون أي محاولات تثبيت تلقائية
مناسب للـ Streamlit Cloud

لا تحاول تثبيت المكتبات في وقت التشغيل!
استخدم requirements.txt بدلاً من ذلك
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

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
    </style>
    """, unsafe_allow_html=True)

# ============================================
# البيانات التجريبية
# ============================================

@st.cache_data
def load_data():
    """تحميل البيانات التجريبية"""
    return pd.DataFrame({
        'الشهر': ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو'],
        'المبيعات': [100, 150, 120, 200, 180, 220],
        'الأرباح': [20, 35, 25, 50, 40, 60],
        'العملاء': [50, 65, 60, 80, 75, 90]
    })

# ============================================
# الواجهة الرئيسية
# ============================================

st.title("📊 لوحة التحكم التحليلية")
st.markdown("تطبيق سريع وفعال لتحليل البيانات")
st.divider()

# القائمة الجانبية
with st.sidebar:
    st.header("⚙️ الإعدادات")
    page = st.radio(
        "اختر الصفحة:",
        ["🏠 الرئيسية", "📈 البيانات", "📊 التحليل", "ℹ️ معلومات"]
    )

# ============================================
# صفحة الرئيسية
# ============================================

if page == "🏠 الرئيسية":
    st.header("مرحباً بك! 👋")
    
    df = load_data()
    
    # المؤشرات الرئيسية
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("إجمالي المبيعات", f"﷼{df['المبيعات'].sum():,.0f}")
    with col2:
        st.metric("إجمالي الأرباح", f"﷼{df['الأرباح'].sum():,.0f}")
    with col3:
        st.metric("إجمالي العملاء", f"{df['العملاء'].sum():,.0f}")
    with col4:
        st.metric("المتوسط الشهري", f"﷼{df['المبيعات'].mean():,.0f}")
    
    st.markdown("---")
    
    # الرسم البياني الرئيسي
    st.subheader("📈 الأداء الشهري")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['الشهر'], 
        y=df['المبيعات'], 
        mode='lines+markers', 
        name='المبيعات',
        line=dict(color='#667eea', width=3)
    ))
    fig.add_trace(go.Scatter(
        x=df['الشهر'], 
        y=df['الأرباح'], 
        mode='lines+markers', 
        name='الأرباح',
        line=dict(color='#764ba2', width=3)
    ))
    fig.update_layout(
        title="المبيعات والأرباح الشهرية",
        xaxis_title="الشهر",
        yaxis_title="القيمة",
        hovermode='x unified',
        template="plotly_white",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# صفحة البيانات
# ============================================

elif page == "📈 البيانات":
    st.header("📈 جدول البيانات")
    
    df = load_data()
    
    # عرض الجدول
    st.subheader("البيانات الكاملة")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # إحصائيات سريعة
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("عدد الصفوف", len(df))
    with col2:
        st.metric("أكبر قيمة مبيعات", f"﷼{df['المبيعات'].max():,.0f}")
    with col3:
        st.metric("أصغر قيمة مبيعات", f"﷼{df['المبيعات'].min():,.0f}")
    
    st.markdown("---")
    
    # تحميل البيانات
    csv = df.to_csv(index=False, encoding='utf-8')
    st.download_button(
        label="📥 تحميل البيانات (CSV)",
        data=csv,
        file_name="data.csv",
        mime="text/csv"
    )

# ============================================
# صفحة التحليل
# ============================================

elif page == "📊 التحليل":
    st.header("📊 التحليل المتقدم")
    
    df = load_data()
    
    # الرسم البياني 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("المبيعات حسب الشهر")
        fig1 = px.bar(df, x='الشهر', y='المبيعات',
                      title='المبيعات الشهرية',
                      color='المبيعات',
                      color_continuous_scale='Blues')
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.subheader("الأرباح حسب الشهر")
        fig2 = px.bar(df, x='الشهر', y='الأرباح',
                      title='الأرباح الشهرية',
                      color='الأرباح',
                      color_continuous_scale='Greens')
        st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown("---")
    
    # الرسم البياني 3
    st.subheader("عدد العملاء")
    fig3 = px.line(df, x='الشهر', y='العملاء',
                   title='نمو العملاء الشهري',
                   markers=True)
    st.plotly_chart(fig3, use_container_width=True)

# ============================================
# صفحة المعلومات
# ============================================

elif page == "ℹ️ معلومات":
    st.header("ℹ️ معلومات التطبيق")
    
    with st.expander("❔ كيف أستخدم التطبيق؟"):
        st.write("""
        1. **الصفحة الرئيسية**: عرض ملخص الإحصائيات الرئيسية
        2. **البيانات**: عرض البيانات في جدول وتحميلها
        3. **التحليل**: رسوم بيانية متقدمة
        """)
    
    with st.expander("❔ هل البيانات حقيقية؟"):
        st.write("""
        لا، هذه بيانات تجريبية للعرض التوضيحي.
        في التطبيقات الحقيقية، يمكنك ربط قاعدة بيانات.
        """)
    
    with st.expander("❔ ما هي المكتبات المستخدمة؟"):
        st.write("""
        - **Streamlit**: إطار عمل للتطبيقات التفاعلية
        - **Pandas**: معالجة البيانات
        - **Plotly**: الرسوم البيانية التفاعلية
        - **NumPy**: العمليات الحسابية
        """)
    
    with st.expander("❔ كيف أنشر التطبيق على السحابة؟"):
        st.write("""
        1. أنشئ مستودع على GitHub
        2. أضف ملف `requirements.txt`
        3. اذهب إلى https://share.streamlit.io
        4. ربط مشروعك على GitHub
        5. Streamlit سينشر التطبيق تلقائياً
        
        **ملف requirements.txt:**
        ```
        streamlit>=1.28.0
        pandas>=2.0.0
        numpy>=1.24.0
        plotly>=5.17.0
        ```
        """)

# ============================================
# التذييل
# ============================================

st.divider()
st.markdown("""
    <div style='text-align: center; direction: rtl; color: #999;'>
    <p>تم إنشاء هذا التطبيق بواسطة Streamlit 🎈</p>
    </div>
    """, unsafe_allow_html=True)

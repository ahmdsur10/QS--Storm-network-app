import streamlit as st
import math
import json
import uuid
from datetime import datetime
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import io
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, Fullscreen, MiniMap

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except Exception:
    GEOPANDAS_AVAILABLE = False

try:
    from staticmap import StaticMap, Line as SMLine, CircleMarker as SMCircle
    STATICMAP_AVAILABLE = True
except Exception:
    STATICMAP_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# دعم اللغة العربية في تقرير PDF (تشكيل الحروف + اتجاه RTL + خط Amiri)
# ─────────────────────────────────────────────────────────────────────────────
import os as _os
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SHAPING_AVAILABLE = True
except Exception:
    ARABIC_SHAPING_AVAILABLE = False

_FONT_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "assets", "fonts")
ARABIC_FONT_REGULAR = "Amiri"
ARABIC_FONT_BOLD = "Amiri-Bold"
ARABIC_FONT_AVAILABLE = False

def register_arabic_fonts():
    """يسجّل خط Amiri (عادي وغامق) لدى ReportLab لدعم رسم النصوص العربية بشكل صحيح."""
    global ARABIC_FONT_AVAILABLE
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        reg_path = _os.path.join(_FONT_DIR, "Amiri-Regular.ttf")
        bold_path = _os.path.join(_FONT_DIR, "Amiri-Bold.ttf")
        if _os.path.exists(reg_path) and _os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont(ARABIC_FONT_REGULAR, reg_path))
            pdfmetrics.registerFont(TTFont(ARABIC_FONT_BOLD, bold_path))
            ARABIC_FONT_AVAILABLE = True
        else:
            ARABIC_FONT_AVAILABLE = False
    except Exception:
        ARABIC_FONT_AVAILABLE = False
    return ARABIC_FONT_AVAILABLE

def ar(text):
    """
    يحوّل أي نص عربي (أو مختلط) إلى الصيغة الصحيحة للعرض في PDF:
    تشكيل اتصال الحروف العربية (reshaping) ثم ترتيب الاتجاه البصري (bidi).
    الأرقام والنصوص الإنجليزية تبقى دون تأثير.
    """
    text = str(text)
    if not ARABIC_SHAPING_AVAILABLE:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text

# ─────────────────────────────────────────────────────────────────────────────
# إعداد الصفحة
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="محلل شبكات السيول",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"About": None},
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght=400;600;700;900&display=swap');

* { box-sizing: border-box; font-family: 'Cairo', sans-serif !important; }
html, body, [class*="css"] { direction: rtl; text-align: right; }
.stApp { background: #eef2f7; }

/* Header */
.main-header {
    background: linear-gradient(135deg, #0a2a5e 0%, #1a5fa8 60%, #2980d4 100%);
    color: white;
    padding: 30px 40px;
    border-radius: 16px;
    margin-bottom: 25px;
    box-shadow: 0 8px 30px rgba(10,42,94,0.25);
    text-align: center;
}
.main-header h1 { font-size: 2.4rem; font-weight: 900; margin: 0 0 6px 0; letter-spacing: 1px; }
.main-header p  { font-size: 1rem; margin: 0; opacity: 0.85; }

.section-title {
    font-size: 1.5rem;
    font-weight: 900;
    color: #0a2a5e;
    border-right: 5px solid #1a5fa8;
    padding-right: 14px;
    margin: 20px 0 18px 0;
}

/* Cards */
.kpi-card {
    background: white;
    border-radius: 14px;
    padding: 20px 16px;
    text-align: center;
    border-top: 5px solid #1a5fa8;
    box-shadow: 0 4px 16px rgba(0,0,0,0.07);
    margin-bottom: 12px;
}
.kpi-value { font-size: 2.2rem; font-weight: 900; color: #0a2a5e; }
.kpi-label { font-size: 0.9rem; color: #6b7a99; font-weight: 700; margin-top: 4px; }

/* Workflow steps */
.step-card {
    background: white;
    border-radius: 14px;
    padding: 28px 20px;
    text-align: center;
    border: 2px solid #d0e4f7;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    transition: transform 0.2s, box-shadow 0.2s;
    height: 100%;
}
.step-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(26,95,168,0.15); }
.step-icon { font-size: 2.8rem; margin-bottom: 12px; }
.step-title { font-size: 1.1rem; font-weight: 900; color: #0a2a5e; margin-bottom: 8px; }
.step-desc { font-size: 0.88rem; color: #6b7a99; line-height: 1.5; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #1a5fa8 0%, #0a2a5e 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 10px 20px !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }

/* Info banner */
.info-banner {
    background: #e8f4fd;
    border-right: 4px solid #1a5fa8;
    padding: 12px 14px;
    border-radius: 6px;
    font-size: 0.9rem;
    color: #0a2a5e;
    margin: 12px 0;
    font-weight: 600;
}

/* Table & dataframe styling */
.stDataframe { font-size: 0.9rem; }
.total-row {
    background: linear-gradient(135deg, #0a2a5e 0%, #1a5fa8 100%);
    color: white;
    padding: 14px 16px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 1.05rem;
    margin: 18px 0 12px 0;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PLACEHOLDER: استبدل هذا الجزء بالكود الأصلي الخاص بك (الأسطر 1-700 تقريباً)
# ─────────────────────────────────────────────────────────────────────────────

# [يجب نسخ كل الكود من 168 إلى 699 من الملف الأصلي هنا]

# ─────────────────────────────────────────────────────────────────────────────
# SECTION: استعراض وتعديل الفواتير (الكود المُصلح)
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.cost:
    result = st.session_state.cost
    st.markdown("### 📊 كشف حساب وجدول كميات المشروع المعتمد")

    k1, k2, k3, k4 = st.columns(4)
    t_mh = sum(e["n_manholes"] for e in result["per_edge"])
    t_tr = sum(e["n_traps"] for e in result["per_edge"])

    k1.markdown(f'<div class="kpi-card"><div class="kpi-value">{t_mh}</div><div class="kpi-label">المناهل الكلية</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="kpi-card"><div class="kpi-value">{t_tr}</div><div class="kpi-label">مصائد الحطام</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(result["per_edge"])}</div><div class="kpi-label">عدد مسارات الفروع</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="kpi-card"><div class="kpi-value">{result["total_cost"]:,.0f}</div><div class="kpi-label">الميزانية الإجمالية التقديرية (SAR)</div></div>', unsafe_allow_html=True)

    rows_boq = [{"البند الإنشائي للمشروع": name, "الكمية المحسوبة": f"{data['الكمية']:,.2f}", "الوحدة": data["الوحدة"], "الإجمالي (ريال سعودي)": f"{data['الإجمالي']:,.2f}"} for name, data in result["all_items"].items()]
    st.dataframe(pd.DataFrame(rows_boq), use_container_width=True, hide_index=True)

    st.markdown(f'<div class="total-row">💰 صافي تكلفة البنود الإنشائية الرأسمالية: {result["total_cost"]:,.0f} ريال سعودي</div>', unsafe_allow_html=True)

    with st.expander("📂 استعراض الفواتير التحليلية والكميات لكل فرع على حدة"):
        st.markdown("""
        <div class="info-banner">
        ✏️ يمكنك تعديل القطر والعمق هنا مباشرة لكل فرع لزيادة الدقة — سيُعاد احتساب الكميات والتكلفة فوراً.
        </div>
        """, unsafe_allow_html=True)

        # خريطة سريعة من اسم الفرع إلى الخط الأصلي في session_state.lines
        line_by_name = {ln["name"]: ln for ln in st.session_state.lines}

        # 🔧 الإصلاح: إضافة enumerate لجعل المفاتيح فريدة
        for edge_idx, e in enumerate(result["per_edge"]):
            src_line = line_by_name.get(e["line_name"])

            st.markdown(f"📌 **{e['line_name']}** — الطول: {e['length']:.1f} م")

            ecol1, ecol2, ecol3 = st.columns([2, 2, 2])
            with ecol1:
                if src_line is not None:
                    dia_options = sorted(PIPE_PRICES.keys())
                    cur_dia = src_line.get("diameter", e["diameter"])
                    # ✅ تم إضافة edge_idx للمفتاح لجعله فريداً
                    new_dia = st.selectbox(
                        "القطر (مم)", dia_options,
                        index=dia_options.index(cur_dia) if cur_dia in dia_options else dia_options.index(600),
                        key=f"inv_dia_{src_line['id']}_{edge_idx}"  # ✅ الإصلاح الأساسي
                    )
                    if new_dia != cur_dia:
                        src_line["diameter"] = new_dia
                        st.session_state.cost = None
                else:
                    st.write(f"القطر: {e['diameter']} مم")
            with ecol2:
                if src_line is not None:
                    cur_depth = float(src_line.get("depth", e["depth"]))
                    # ✅ تم إضافة edge_idx للمفتاح لجعله فريداً
                    new_depth = st.number_input(
                        "العمق (م)", min_value=0.5, max_value=12.0,
                        value=cur_depth, step=0.1,
                        key=f"inv_dep_{src_line['id']}_{edge_idx}"  # ✅ الإصلاح الأساسي
                    )
                    if new_depth != cur_depth:
                        src_line["depth"] = new_depth
                        st.session_state.cost = None
                else:
                    st.write(f"العمق: {e['depth']} م")
            with ecol3:
                st.metric("إجمالي تكلفة الفرع", f"{e['total']:,.0f} ريال")

            df_e = pd.DataFrame([{"البند": it["البند"], "الكمية": f"{it['الكمية']:,.2f}", "الوحدة": it["الوحدة"], "سعر الوحدة": f"{it['السعر']:,}", "الإجمالي (SAR)": f"{it['الإجمالي']:,.0f}"} for it in e["items"]])
            st.dataframe(df_e, use_container_width=True, hide_index=True)
            st.markdown("<hr style='border-top:1px dashed #9aa4b8;'>", unsafe_allow_html=True)

        if st.session_state.cost is None:
            st.warning("⚠️ تم تعديل بعض المواصفات — اضغط الزر أدناه لتحديث جدول الكميات والتكلفة بالكامل.")
            if st.button("🧮 إعادة الحساب بعد التعديل", use_container_width=True, key="recalc_from_invoice"):
                st.session_state.analyzer = NetworkAnalyzer(st.session_state.lines)
                ana2 = st.session_state.analyzer
                all_items2 = {}
                per_edge2 = []
                stat2 = ana2.stats()
                total_len2 = stat2["length"]

                for edge in ana2.edges_list:
                    d = edge["diameter"]
                    dep = edge["depth"]
                    L = edge["distance"]
                    share = L / total_len2 if total_len2 > 0 else 0
                    n_mh = max(1, round(stat2["nodes"] * share))
                    n_tr = num_traps(L)
                    p_pipe = PIPE_PRICES.get(d, 725)

                    items = [
                        {"البند": "أنابيب صرف خرسانية مدعمة", "الكمية": L, "الوحدة": "متر طولي", "السعر": p_pipe, "الإجمالي": L * p_pipe},
                        {"البند": "أعمال حفر الخنادق المفتوحة للأنابيب", "الكمية": L, "الوحدة": "متر طولي", "السعر": EXCAVATION, "الإجمالي": L * EXCAVATION},
                        {"البند": "مناهل تفتيش خرسانية دائرية معتمدة", "الكمية": n_mh, "الوحدة": "عدد", "السعر": MANHOLE_PRICE, "الإجمالي": n_mh * MANHOLE_PRICE},
                        {"البند": "مصائد رمل وحطام جغرافية", "الكمية": n_tr, "الوحدة": "عدد", "السعر": TRAP_PRICE, "الإجمالي": n_tr * TRAP_PRICE},
                        {"البند": "إعادة الردم والتسوية والدمك الإنشائي للمسار", "الكمية": L * dep, "الوحدة": "متر مكعب", "السعر": BACKFILL_PRICE, "الإجمالي": L * dep * BACKFILL_PRICE},
                    ]

                    total = sum(it["الإجمالي"] for it in items)
                    per_edge2.append({
                        "line_name": edge["line_name"], "diameter": d, "depth": dep, "length": L,
                        "items": items, "total": total, "n_manholes": n_mh, "n_traps": n_tr,
                        "start_coord": edge["start_coord"], "end_coord": edge["end_coord"]
                    })

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""<div style="text-align:center;color:#9aa4b8;font-size:0.85rem;padding:16px 0">🌊 محلل شبكات ومصارف السيول — لوحة التحكم الذكية المحدثة والتركيز التلقائي</div>""", unsafe_allow_html=True)

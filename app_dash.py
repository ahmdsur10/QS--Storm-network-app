import streamlit as st
import math
import json
import uuid
from datetime import datetime

st.set_page_config(page_title="محلل شبكات السيول", page_icon="🌊", layout="wide", menu_items={})

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@700;900&display=swap');
* { font-family: 'Cairo', sans-serif !important; direction: rtl; text-align: right; }
.header { background: #0a2a5e; color: white; padding: 30px; border-radius: 15px; margin-bottom: 20px; text-align: center; }
.header h1 { font-size: 2.5rem; margin: 0; }
.card { background: white; border: 3px solid #1a5fa8; border-radius: 10px; padding: 20px; margin: 10px 0; text-align: center; }
.card-value { font-size: 2rem; font-weight: 900; color: #0a2a5e; }
.stButton > button { background: linear-gradient(135deg, #1a5fa8 0%, #0a2a5e 100%) !important; color: white !important; border-radius: 10px !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

PIPES = {400: 454, 500: 619, 600: 725, 700: 906, 800: 1045, 900: 1225, 1000: 1440, 1100: 1600, 1200: 1812, 1300: 1920, 1400: 2132}

if "lines" not in st.session_state:
    st.session_state.lines = []
if "analyzer" not in st.session_state:
    st.session_state.analyzer = None
if "costs" not in st.session_state:
    st.session_state.costs = None

st.markdown('<div class="header"><h1>🌊 محلل شبكات السيول</h1><p>تحليل وحساب تكاليف الشبكات</p></div>', unsafe_allow_html=True)

tabs = st.tabs(["🏠 الرئيسية", "📊 الإدخال", "🌐 التحليل", "⚙️ الحساب", "📋 النتائج"])

# التبويب 1: الرئيسية
with tabs[0]:
    st.markdown("<h2 style='color: #0a2a5e;'>🌊 مرحباً بك في محلل شبكات السيول</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="card"><div style="font-size: 2.5rem;">📊</div><strong>إدخال البيانات</strong></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card"><div style="font-size: 2.5rem;">🌐</div><strong>التحليل</strong></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card"><div style="font-size: 2.5rem;">💰</div><strong>الحساب</strong></div>', unsafe_allow_html=True)
    
    st.success("✅ التطبيق جاهز للاستخدام")

# التبويب 2: الإدخال
with tabs[1]:
    st.markdown("<h2 style='color: #0a2a5e;'>📊 إدخال بيانات الخطوط</h2>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        line_name = st.text_input("اسم الخط", f"خط {len(st.session_state.lines)+1}")
    with col2:
        line_length = st.number_input("الطول (متر)", 100, 50000, 1000, step=100)
    with col3:
        line_diameter = st.selectbox("القطر (ملم)", sorted(PIPES.keys()), index=2)
    with col4:
        line_depth = st.number_input("العمق (متر)", 0.5, 5.0, 1.5, step=0.1)
    
    if st.button("➕ إضافة خط", use_container_width=True):
        st.session_state.lines.append({
            "id": str(uuid.uuid4()),
            "name": line_name,
            "length": line_length,
            "diameter": line_diameter,
            "depth": line_depth,
            "selected": True
        })
        st.success(f"✅ تم إضافة {line_name}")
        st.rerun()
    
    st.markdown("---")
    st.markdown("<h3 style='color: #0a2a5e;'>الخطوط المضافة:</h3>", unsafe_allow_html=True)
    
    if not st.session_state.lines:
        st.warning("لم تضف أي خطوط حتى الآن")
    else:
        for idx, line in enumerate(st.session_state.lines):
            col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1, 1, 1])
            with col1:
                st.write(f"**{line['name']}**")
            with col2:
                st.write(f"{line['length']:,} م")
            with col3:
                st.write(f"∅ {line['diameter']}")
            with col4:
                st.write(f"عمق {line['depth']}")
            with col5:
                if st.button("🗑️", key=f"del_{idx}"):
                    st.session_state.lines.pop(idx)
                    st.rerun()

# التبويب 3: التحليل
with tabs[2]:
    st.markdown("<h2 style='color: #0a2a5e;'>🌐 تحليل الشبكة</h2>", unsafe_allow_html=True)
    
    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً أولاً")
    else:
        if st.button("🔍 حلل الشبكة", use_container_width=True):
            total_length = sum(line["length"] for line in st.session_state.lines)
            num_manholes = max(1, int(total_length / 250))
            num_traps = max(1, int(total_length / 35))
            
            st.session_state.analyzer = {
                "lines": st.session_state.lines,
                "total_length": total_length,
                "num_manholes": num_manholes,
                "num_traps": num_traps,
                "num_branches": len(st.session_state.lines)
            }
            st.success("✅ تم التحليل!")
        
        if st.session_state.analyzer:
            a = st.session_state.analyzer
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'<div class="card"><div class="card-value">{a["num_manholes"]}</div><div>المناهل</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="card"><div class="card-value">{a["num_branches"]}</div><div>الفروع</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="card"><div class="card-value">{a["num_traps"]}</div><div>المصائد</div></div>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<div class="card"><div class="card-value">{a["total_length"]/1000:.1f}</div><div>الطول (كم)</div></div>', unsafe_allow_html=True)

# التبويب 4: الحساب
with tabs[3]:
    st.markdown("<h2 style='color: #0a2a5e;'>⚙️ حساب التكاليف</h2>", unsafe_allow_html=True)
    
    if not st.session_state.analyzer:
        st.warning("⚠️ حلل الشبكة أولاً")
    else:
        if st.button("🧮 احسب التكاليف", use_container_width=True):
            a = st.session_state.analyzer
            all_items = {}
            
            for line in a["lines"]:
                length = line["length"]
                diameter = line["diameter"]
                depth = line["depth"]
                
                pipe_price = PIPES.get(diameter, 725)
                
                items = {
                    "أنابيب صرف": {"quantity": length, "unit": "م", "price": pipe_price, "total": length * pipe_price},
                    "حفر الخندق": {"quantity": length, "unit": "م", "price": 50, "total": length * 50},
                    "مناهل": {"quantity": max(1, int(length / 250)), "unit": "عدد", "price": 3000, "total": max(1, int(length / 250)) * 3000},
                    "مصائد": {"quantity": max(1, int(length / 35)), "unit": "عدد", "price": 2000, "total": max(1, int(length / 35)) * 2000},
                    "ردم وتسوية": {"quantity": length * depth, "unit": "م³", "price": 30, "total": length * depth * 30},
                }
                
                for item_name, item_data in items.items():
                    if item_name not in all_items:
                        all_items[item_name] = {"quantity": 0, "unit": item_data["unit"], "price": item_data["price"], "total": 0}
                    all_items[item_name]["quantity"] += item_data["quantity"]
                    all_items[item_name]["total"] += item_data["total"]
            
            total_cost = sum(item["total"] for item in all_items.values())
            
            st.session_state.costs = {
                "items": all_items,
                "total": total_cost,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            st.success("✅ تم الحساب!")
        
        if st.session_state.costs:
            c = st.session_state.costs
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f'<div class="card"><div class="card-value">{c["total"]/1e6:.2f}M</div><div>التكلفة</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="card"><div class="card-value">{len(st.session_state.analyzer["lines"])}</div><div>الخطوط</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="card"><div class="card-value">{st.session_state.analyzer["total_length"]/1000:.1f}</div><div>الطول (كم)</div></div>', unsafe_allow_html=True)

# التبويب 5: النتائج
with tabs[4]:
    st.markdown("<h2 style='color: #0a2a5e;'>📋 النتائج</h2>", unsafe_allow_html=True)
    
    if not st.session_state.costs:
        st.warning("⚠️ احسب التكاليف أولاً")
    else:
        c = st.session_state.costs
        
        st.markdown("<h3 style='color: #0a2a5e;'>جدول الكميات والأسعار:</h3>", unsafe_allow_html=True)
        
        st.markdown("|البند|الكمية|الوحدة|السعر|الإجمالي|")
        st.markdown("|---|---|---|---|---|")
        for item_name, item_data in c["items"].items():
            st.markdown(f"|{item_name}|{item_data['quantity']:,.2f}|{item_data['unit']}|{item_data['price']:,.0f}|{item_data['total']:,.0f}|")
        
        st.markdown("---")
        st.markdown(f"### 💰 **التكلفة الإجمالية: {c['total']:,.0f} ريال**")
        
        # PDF
        try:
            from reportlab.lib.pagesizes import landscape, A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
            import io
            
            if st.button("📥 تحميل PDF", use_container_width=True):
                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
                elements = []
                styles = getSampleStyleSheet()
                
                elements.append(Paragraph("DRAINAGE NETWORK ANALYSIS REPORT", styles['Heading1']))
                elements.append(Spacer(1, 12))
                
                summary = [["Metric", "Value"], ["Total Cost (SAR)", f"{c['total']:,.0f}"]]
                t1 = Table(summary, colWidths=[100*mm, 100*mm])
                t1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a5fa8')), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
                elements.append(t1)
                elements.append(Spacer(1, 15))
                
                items_data = [["Item", "Quantity", "Unit", "Total"]]
                for item_name, item_data in c["items"].items():
                    items_data.append([item_name, f"{item_data['quantity']:,.2f}", item_data["unit"], f"{item_data['total']:,.0f}"])
                
                t2 = Table(items_data, colWidths=[70*mm, 60*mm, 50*mm, 70*mm])
                t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a5fa8')), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
                elements.append(t2)
                
                doc.build(elements)
                pdf_buffer.seek(0)
                
                st.download_button(label="📥 احمل PDF", data=pdf_buffer.getvalue(), file_name=f"تقرير_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf", use_container_width=True)
                st.success("✅ جاهز!")
        except:
            pass

st.markdown("---")
st.markdown('<div style="text-align: center; color: #999;"><p>🌊 محلل شبكات السيول</p></div>', unsafe_allow_html=True)

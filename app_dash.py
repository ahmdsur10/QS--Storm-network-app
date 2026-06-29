import streamlit as st
import math
import json
import uuid
from datetime import datetime
import networkx as nx
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, FullScreen

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

def distance(c1, c2):
    lat1, lon1, lat2, lon2 = math.radians(c1[0]), math.radians(c1[1]), math.radians(c2[0]), math.radians(c2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 6371000 * 2 * math.asin(math.sqrt(a))

class Analyzer:
    def __init__(self, lines):
        self.lines = [l for l in lines if l.get("selected")]
        self.G = nx.Graph()
        self.edges = []
        self.nodes = {}
        self._build()
    
    def _build(self):
        nid = 0
        for line in self.lines:
            coords = line.get("coords", [])
            if len(coords) < 2: continue
            for i in range(len(coords)-1):
                s, e = tuple(coords[i][:2]), tuple(coords[i+1][:2])
                if s not in self.nodes: self.nodes[s] = nid; self.G.add_node(nid); nid += 1
                if e not in self.nodes: self.nodes[e] = nid; self.G.add_node(nid); nid += 1
                d = distance(coords[i], coords[i+1])
                self.G.add_edge(self.nodes[s], self.nodes[e], distance=d)
                self.edges.append({"distance": d, "line": line.get("name"), "diameter": 600, "depth": 1.5})
    
    def stats(self):
        return {"nodes": self.G.number_of_nodes(), "edges": len(self.edges), "length": sum(e["distance"] for e in self.edges)}

if "lines" not in st.session_state: st.session_state.lines = []
if "analyzer" not in st.session_state: st.session_state.analyzer = None
if "costs" not in st.session_state: st.session_state.costs = None

st.markdown('<div class="header"><h1>🌊 محلل شبكات السيول</h1><p>تحليل وحساب تكاليف الشبكات</p></div>', unsafe_allow_html=True)

tabs = st.tabs(["🏠 الرئيسية", "🗺️ الرسم", "🌐 التحليل", "⚙️ الحساب", "🗺️ التقرير"])

with tabs[0]:
    st.markdown("<h2 style='color: #0a2a5e; text-align: right;'>مرحباً بك</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="card"><div style="font-size: 2rem;">🗺️</div><strong>الرسم</strong></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card"><div style="font-size: 2rem;">🌐</div><strong>التحليل</strong></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card"><div style="font-size: 2rem;">💰</div><strong>الحساب</strong></div>', unsafe_allow_html=True)

with tabs[1]:
    st.markdown("<h2 style='color: #0a2a5e;'>الرسم على الخريطة</h2>", unsafe_allow_html=True)
    m = folium.Map(location=[24.7136, 46.6753], zoom_start=12, tiles="OpenStreetMap")
    FullScreen().add_to(m)
    for line in st.session_state.lines:
        if line.get("coords"): folium.PolyLine(line["coords"], color="red", weight=3).add_to(m)
    Draw(export=True, position="topleft", draw_options={"polyline": True, "polygon": False, "rectangle": False}).add_to(m)
    map_data = st_folium(m, width=None, height=600)
    if map_data and map_data.get("last_active_drawing"):
        g = map_data["last_active_drawing"].get("geometry", {})
        if g.get("type") == "LineString":
            coords = [(c[1], c[0]) for c in g.get("coordinates", [])]
            if len(coords) >= 2:
                st.session_state.lines.append({"id": str(uuid.uuid4()), "name": f"خط {len(st.session_state.lines)+1}", "coords": coords, "selected": True})
                st.session_state.analyzer = None
                st.success("✅ تم!")
                st.rerun()

with tabs[2]:
    st.markdown("<h2 style='color: #0a2a5e;'>تحليل الشبكة</h2>", unsafe_allow_html=True)
    if not st.session_state.lines:
        st.warning("⚠️ أضف خطوطاً أولاً")
    else:
        if st.button("🔍 حلل الشبكة", use_container_width=True):
            st.session_state.analyzer = Analyzer(st.session_state.lines)
            st.success("✅ تم!")
        if st.session_state.analyzer:
            s = st.session_state.analyzer.stats()
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f'<div class="card"><div class="card-value">{s["nodes"]}</div><div>المناهل</div></div>', unsafe_allow_html=True)
            with col2: st.markdown(f'<div class="card"><div class="card-value">{s["edges"]}</div><div>الفروع</div></div>', unsafe_allow_html=True)
            with col3: st.markdown(f'<div class="card"><div class="card-value">{s["length"]/1000:.1f}</div><div>الطول (كم)</div></div>', unsafe_allow_html=True)

with tabs[3]:
    st.markdown("<h2 style='color: #0a2a5e;'>الحساب والإعدادات</h2>", unsafe_allow_html=True)
    if not st.session_state.analyzer:
        st.warning("⚠️ حلل الشبكة أولاً")
    else:
        st.info("📌 أدخل القطر والعمق لكل فرع")
        for i, e in enumerate(st.session_state.analyzer.edges):
            col1, col2, col3 = st.columns([2, 1.5, 1.5])
            with col1: st.write(f"**{i+1}. {e['line']}** - {e['distance']/1000:.3f} كم")
            with col2: e["diameter"] = st.selectbox("القطر", sorted(PIPES.keys()), index=3, key=f"d{i}", label_visibility="collapsed")
            with col3: e["depth"] = st.number_input("العمق", 0.5, 5.0, 1.5, 0.1, key=f"dp{i}", label_visibility="collapsed")
        
        if st.button("🧮 احسب التكاليف", use_container_width=True):
            a = st.session_state.analyzer
            s = a.stats()
            all_items = {}
            results = []
            tl = s["length"]
            for e in a.edges:
                share = e["distance"] / tl if tl > 0 else 0
                nm = max(1, round(s["nodes"] * share))
                nt = max(1, round(e["distance"] / 35))
                pp = PIPES.get(e["diameter"], 725)
                items = [
                    {"البند": "أنابيب", "الكمية": e["distance"], "الوحدة": "م", "السعر": pp, "الإجمالي": e["distance"]*pp},
                    {"البند": "حفر", "الكمية": e["distance"], "الوحدة": "م", "السعر": 50, "الإجمالي": e["distance"]*50},
                    {"البند": "مناهل", "الكمية": nm, "الوحدة": "عدد", "السعر": 3000, "الإجمالي": nm*3000},
                    {"البند": "مصائد", "الكمية": nt, "الوحدة": "عدد", "السعر": 2000, "الإجمالي": nt*2000},
                    {"البند": "ردم", "الكمية": e["distance"]*e["depth"], "الوحدة": "م³", "السعر": 30, "الإجمالي": e["distance"]*e["depth"]*30},
                ]
                for it in items:
                    k = it["البند"]
                    if k not in all_items: all_items[k] = {"الكمية": 0, "الإجمالي": 0, "الوحدة": it["الوحدة"]}
                    all_items[k]["الكمية"] += it["الكمية"]
                    all_items[k]["الإجمالي"] += it["الإجمالي"]
            
            st.session_state.costs = {"all": all_items, "total": sum(it["الإجمالي"] for it in all_items.values()), "nodes": sum(e.get("nodes", max(1, round(s["nodes"]*e["distance"]/tl))) for e in a.edges)}
            st.success("✅ تم!")
        
        if st.session_state.costs:
            c = st.session_state.costs
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f'<div class="card"><div class="card-value">{c["total"]/1e6:.2f}M</div><div>التكلفة</div></div>', unsafe_allow_html=True)
            with col2: st.markdown(f'<div class="card"><div class="card-value">{len(st.session_state.analyzer.edges)}</div><div>الفروع</div></div>', unsafe_allow_html=True)
            with col3: st.markdown(f'<div class="card"><div class="card-value">{st.session_state.analyzer.stats()["nodes"]}</div><div>المناهل</div></div>', unsafe_allow_html=True)
            
            data = [{"البند": k, "الكمية": f"{v['الكمية']:,.2f}", "الوحدة": v["الوحدة"], "الإجمالي": f"{v['الإجمالي']:,.0f}"} for k, v in c["all"].items()]
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

with tabs[4]:
    st.markdown("<h2 style='color: #0a2a5e;'>التقرير والخريطة</h2>", unsafe_allow_html=True)
    if not st.session_state.analyzer:
        st.warning("⚠️ حلل الشبكة أولاً")
    else:
        sub1, sub2 = st.tabs(["🗺️ الخريطة", "📊 PDF"])
        
        with sub1:
            a = st.session_state.analyzer
            coords = []
            for line in st.session_state.lines:
                coords.extend(line.get("coords", []))
            
            if coords:
                lats = [c[0] for c in coords]
                lons = [c[1] for c in coords]
                center = [(min(lats)+max(lats))/2, (min(lons)+max(lons))/2]
            else:
                center = [24.7136, 46.6753]
            
            m2 = folium.Map(location=center, zoom_start=14, tiles="OpenStreetMap")
            FullScreen().add_to(m2)
            
            for line in st.session_state.lines:
                if line.get("coords"): folium.PolyLine(line["coords"], color="blue", weight=3).add_to(m2)
            
            for node in a.G.nodes():
                for coord, nid in a.nodes.items():
                    if nid == node: folium.CircleMarker(location=coord, radius=5, color="red", fill=True, fillColor="red").add_to(m2)
            
            if coords:
                m2.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
            
            st.info("🔍 اضغط على المربع في أعلى يسار الخريطة لتكبيرها")
            st_folium(m2, width=None, height=700)
        
        with sub2:
            if not st.session_state.costs:
                st.warning("⚠️ احسب التكاليف أولاً")
            else:
                if st.button("📥 تحميل PDF", use_container_width=True):
                    try:
                        from reportlab.lib.pagesizes import landscape, A4
                        from reportlab.lib import colors
                        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                        from reportlab.lib.styles import getSampleStyleSheet
                        from reportlab.lib.units import mm
                        import io
                        
                        pdf_buffer = io.BytesIO()
                        doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
                        elements = []
                        styles = getSampleStyleSheet()
                        
                        elements.append(Paragraph("DRAINAGE NETWORK ANALYSIS REPORT", styles['Heading1']))
                        elements.append(Spacer(1, 12))
                        elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
                        elements.append(Spacer(1, 12))
                        
                        c = st.session_state.costs
                        summary = [["Metric", "Value"], ["Total Cost (SAR)", f"{c['total']:,.0f}"], ["Total Branches", str(len(st.session_state.analyzer.edges))], ["Total Nodes", str(st.session_state.analyzer.stats()["nodes"])]]
                        t1 = Table(summary, colWidths=[100*mm, 100*mm])
                        t1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a5fa8')), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
                        elements.append(t1)
                        elements.append(Spacer(1, 15))
                        
                        items = [["Item", "Quantity", "Unit", "Total (SAR)"]]
                        for k, v in c["all"].items():
                            items.append([k, f"{v['الكمية']:,.2f}", v["الوحدة"], f"{v['الإجمالي']:,.0f}"])
                        
                        t2 = Table(items, colWidths=[70*mm, 60*mm, 50*mm, 70*mm])
                        t2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a5fa8')), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
                        elements.append(t2)
                        
                        doc.build(elements)
                        pdf_buffer.seek(0)
                        
                        st.download_button(label="📥 احمل التقرير", data=pdf_buffer.getvalue(), file_name=f"تقرير_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf", use_container_width=True)
                        st.success("✅ تم!")
                    except: st.error("❌ خطأ في PDF")

st.markdown("---")
st.markdown('<div style="text-align: center; color: #999;"><p>🌊 محلل شبكات السيول | النسخة 13.0 (بسيطة وسريعة)</p></div>', unsafe_allow_html=True)

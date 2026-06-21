import streamlit as st
import math
import os
import io
import json
import zipfile
import uuid
import tempfile
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
import seaborn as sns

try:
    import folium
    from streamlit_folium import st_folium
    from folium.plugins import Draw
    FOLIUM_AVAILABLE = True
except ModuleNotFoundError:
    FOLIUM_AVAILABLE = False

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ModuleNotFoundError:
    GEOPANDAS_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
    )
    PDF_AVAILABLE = True
except ModuleNotFoundError:
    PDF_AVAILABLE = False

st.set_page_config(
    page_title="محلل شبكات السيول المتقدم", 
    page_icon="🌊",
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ═════════════════════════════════════════════════════════════════════════════════
# الثوابت والإعدادات
# ═════════════════════════════════════════════════════════════════════════════════

PIPE_PRICES = {
    400: 454, 500: 619, 600: 725, 700: 906, 800: 1045,
    900: 1225, 1000: 1440, 1100: 1600, 1200: 1812, 1300: 1920, 1400: 2132,
}

# أقطار القنوات الصندوقية بالملم
BOX_CHANNEL_DIMENSIONS = {
    "0.6x0.6": {"width": 0.6, "height": 0.6, "price": 850},
    "0.8x0.6": {"width": 0.8, "height": 0.6, "price": 950},
    "1.0x0.6": {"width": 1.0, "height": 0.6, "price": 1050},
    "1.0x0.8": {"width": 1.0, "height": 0.8, "price": 1200},
    "1.2x0.8": {"width": 1.2, "height": 0.8, "price": 1400},
    "1.5x1.0": {"width": 1.5, "height": 1.0, "price": 1800},
}

LINE_COLORS = ["#FF0000", "#0a7d34", "#e8a93a", "#7a1fa8", "#1a5fa8", "#c2185b", "#00838f", "#5d4037"]

MAIN_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
*{box-sizing:border-box}
html,body,[class*="css"],.stApp{font-family:'Cairo',sans-serif!important;direction:rtl}
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stStatusWidget"],#MainMenu,footer
{display:none!important}
.block-container{padding:0.5rem 0.6rem 2rem!important;max-width:1400px!important}
.hdr{background:linear-gradient(135deg,#0a2a5e,#1a5fa8);color:#fff;padding:15px;border-radius:12px;
  margin-bottom:15px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap}
.hdr h1{margin:0;font-size:1.2rem;font-weight:900}
.section-title{color:#0a2a5e;font-size:.95rem;font-weight:900;margin:15px 0 10px;
  border-bottom:3px solid #1a5fa8;padding-bottom:5px}
.metric-card{background:linear-gradient(135deg,#1a5fa8,#0a2a5e);color:#fff;padding:12px;border-radius:10px;
  text-align:center;margin-bottom:8px;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.metric-card .value{font-size:1.3rem;font-weight:900}
.metric-card .label{font-size:.8rem;opacity:0.9;margin-top:4px}
.success-box{background:#d4edda;border-left:4px solid #28a745;padding:12px;border-radius:8px;margin:10px 0;color:#155724}
.warning-box{background:#fff3cd;border-left:4px solid #ffc107;padding:12px;border-radius:8px;margin:10px 0;color:#856404}
.danger-box{background:#f8d7da;border-left:4px solid #dc3545;padding:12px;border-radius:8px;margin:10px 0;color:#721c24}
.info-box{background:#d1ecf1;border-left:4px solid #17a2b8;padding:12px;border-radius:8px;margin:10px 0;color:#0c5460}
.stButton>button{background:linear-gradient(135deg,#1a5fa8,#0a2a5e)!important;color:#fff!important;
  border:none!important;border-radius:10px!important;font-weight:700!important;padding:12px!important;width:100%!important}
</style>"""

# ═════════════════════════════════════════════════════════════════════════════════
# دوال متقدمة لتحليل الشبكة
# ═════════════════════════════════════════════════════════════════════════════════

class AdvancedNetworkAnalyzer:
    """محلل الشبكة المتقدم باستخدام NetworkX"""
    
    def __init__(self, lines):
        self.lines = lines
        self.G_undirected = None
        self.G_directed = None
        self.node_map = {}  # للربط بين node_id والإحداثيات
        self.line_details = {}
        self._build_networks()
    
    def _build_networks(self):
        """بناء شبكتين: موجهة وغير موجهة"""
        self.G_undirected = nx.Graph()
        self.G_directed = nx.DiGraph()
        
        node_counter = 0
        
        for idx, line in enumerate(self.lines):
            if not line.get("selected", True):
                continue
            
            coords = line.get("coords", [])
            if len(coords) < 2:
                continue
            
            line_nodes = []
            line_length = 0
            elevation_change = 0
            
            # إضافة العقد والحواف
            for i in range(len(coords) - 1):
                start = tuple(coords[i])
                end = tuple(coords[i + 1])
                
                # الحصول على معرف المناهل (node IDs)
                if start not in self.node_map:
                    node_id = f"N{node_counter}"
                    self.node_map[start] = {
                        "id": node_id,
                        "coord": start,
                        "line_idx": idx,
                        "elevation": coords[i][2] if len(coords[i]) > 2 else 0,
                    }
                    node_counter += 1
                
                if end not in self.node_map:
                    node_id = f"N{node_counter}"
                    self.node_map[end] = {
                        "id": node_id,
                        "coord": end,
                        "line_idx": idx,
                        "elevation": coords[i + 1][2] if len(coords[i + 1]) > 2 else 0,
                    }
                    node_counter += 1
                
                start_id = self.node_map[start]["id"]
                end_id = self.node_map[end]["id"]
                
                # حساب المسافة والارتفاع
                distance = self._haversine_distance(coords[i], coords[i+1])
                start_elev = self.node_map[start]["elevation"]
                end_elev = self.node_map[end]["elevation"]
                elev_diff = start_elev - end_elev  # المنحدر
                
                # إضافة الحواف بالخصائص
                edge_attrs = {
                    "distance": distance,
                    "diameter": line.get("diameter", 600),
                    "line_idx": idx,
                    "elevation_diff": elev_diff,
                    "slope": (elev_diff / distance) if distance > 0 else 0,
                }
                
                # الشبكة غير الموجهة
                self.G_undirected.add_edge(start_id, end_id, **edge_attrs)
                
                # الشبكة الموجهة (في اتجاه الانحدار)
                if elev_diff >= 0:
                    self.G_directed.add_edge(start_id, end_id, **edge_attrs)
                else:
                    self.G_directed.add_edge(end_id, start_id, **edge_attrs)
                
                # إضافة الخصائص للعقد
                self.G_undirected.nodes[start_id].update(self.node_map[start])
                self.G_undirected.nodes[end_id].update(self.node_map[end])
                self.G_directed.nodes[start_id].update(self.node_map[start])
                self.G_directed.nodes[end_id].update(self.node_map[end])
                
                line_nodes.extend([start_id, end_id])
                line_length += distance
            
            self.line_details[idx] = {
                "name": line.get("name"),
                "nodes": list(set(line_nodes)),
                "length": line_length,
                "diameter": line.get("diameter", 600),
            }
    
    def _haversine_distance(self, coord1, coord2):
        """حساب المسافة بين نقطتين"""
        lat1, lon1 = coord1[0], coord1[1]
        lat2, lon2 = coord2[0], coord2[1]
        R = 6_371_000
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c
    
    def get_centrality_analysis(self):
        """تحليل أهمية المناهل باستخدام مقاييس مختلفة"""
        G = self.G_undirected
        
        # Degree Centrality - عدد الاتصالات
        degree_centrality = nx.degree_centrality(G)
        
        # Betweenness Centrality - عدد المسارات التي تمر عبره
        betweenness = nx.betweenness_centrality(G, weight='distance')
        
        # Closeness Centrality - القرب من باقي المناهل
        closeness = nx.closeness_centrality(G, distance='distance')
        
        # Eigenvector Centrality - الاتصال بمناهل مهمة
        try:
            eigenvector = nx.eigenvector_centrality(G, weight='distance', max_iter=100)
        except:
            eigenvector = {node: 0 for node in G.nodes()}
        
        return {
            "degree": degree_centrality,
            "betweenness": betweenness,
            "closeness": closeness,
            "eigenvector": eigenvector,
        }
    
    def identify_critical_nodes(self):
        """تحديد المناهل الحرجة التي قد تؤثر على الشبكة"""
        centrality = self.get_centrality_analysis()
        
        # المناهل ذات أعلى betweenness centrality هي الحرجة
        critical_nodes = sorted(
            centrality["betweenness"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return critical_nodes
    
    def detect_communities(self):
        """كشف المجموعات (الأحياء/القطاعات) في الشبكة"""
        G = self.G_undirected
        
        # استخدام Louvain algorithm
        try:
            from networkx.algorithms import community
            communities = list(community.greedy_modularity_communities(G))
            return communities
        except:
            return [set(G.nodes())]
    
    def get_flow_analysis(self):
        """تحليل اتجاه الجريان (Flow Direction)"""
        G = self.G_directed
        
        # مصادر الجريان (nodes بدون تدفق داخل)
        sources = [node for node in G.nodes() if G.in_degree(node) == 0]
        
        # مصبات الجريان (nodes بدون تدفق خارجي)
        sinks = [node for node in G.nodes() if G.out_degree(node) == 0]
        
        return {
            "sources": sources,
            "sinks": sinks,
            "total_flow_paths": len(list(nx.all_simple_paths(G, sources[0], sinks[0]))) if sources and sinks else 0,
        }
    
    def analyze_network_resilience(self):
        """تحليل مدى قوة الشبكة (Resilience)"""
        G = self.G_undirected
        
        total_nodes = G.number_of_nodes()
        is_connected = nx.is_connected(G)
        
        # حساب عدد المناهل التي يجب حذفها لتفكيك الشبكة
        if total_nodes > 1:
            try:
                node_connectivity = nx.node_connectivity(G)
            except:
                node_connectivity = 0
        else:
            node_connectivity = 0
        
        # حساب Diameter (أطول أقصر مسار)
        if is_connected and total_nodes > 1:
            diameter = nx.diameter(G, weight='distance')
        else:
            diameter = float('inf')
        
        # Average Clustering Coefficient
        avg_clustering = nx.average_clustering(G)
        
        return {
            "is_connected": is_connected,
            "node_connectivity": node_connectivity,
            "diameter": diameter,
            "clustering_coefficient": avg_clustering,
            "density": nx.density(G),
        }
    
    def calculate_hydraulic_capacity(self, node_id, diameter):
        """حساب السعة الهيدروليكية للأنبوب (Manning equation)"""
        # معادلة Manning: Q = (A * R^(2/3) * S^(1/2)) / n
        # حيث: Q = التدفق (m3/s)
        #      A = المساحة (m2)
        #      R = نصف قطر هيدروليكي
        #      S = المنحدر
        #      n = معامل Manning
        
        radius = diameter / 2000  # من ملم إلى متر
        area = math.pi * (radius ** 2)
        n_manning = 0.015  # معامل Manning للأنابيب الخرسانية
        
        # افترض منحدر 1%
        slope = 0.01
        hydraulic_radius = radius / 2
        
        capacity = (area * (hydraulic_radius ** (2/3)) * (slope ** 0.5)) / n_manning
        return capacity
    
    def get_bottleneck_analysis(self):
        """تحديد الاختناقات (Bottlenecks) في الشبكة"""
        G = self.G_undirected
        
        # الحواف ذات الأقطار الأصغر هي اختناقات محتملة
        edges_by_diameter = sorted(
            G.edges(data=True),
            key=lambda x: x[2].get('diameter', 600)
        )
        
        bottlenecks = edges_by_diameter[:5]  # أصغر 5 أقطار
        
        return bottlenecks
    
    def get_comprehensive_stats(self):
        """إحصائيات شاملة للشبكة"""
        G_u = self.G_undirected
        G_d = self.G_directed
        
        stats = {
            "total_nodes": G_u.number_of_nodes(),
            "total_edges": G_u.number_of_edges(),
            "total_length": sum(data['distance'] for _, _, data in G_u.edges(data=True)),
            "density": nx.density(G_u),
            "avg_degree": sum(dict(G_u.degree()).values()) / G_u.number_of_nodes() if G_u.number_of_nodes() > 0 else 0,
            "num_components": nx.number_connected_components(G_u),
            "is_connected": nx.is_connected(G_u),
        }
        
        return stats

def load_geojson_lines(geojson_data):
    """تحميل خطوط من GeoJSON"""
    lines = []
    try:
        features = geojson_data.get("features", [])
        for idx, feature in enumerate(features):
            geom = feature.get("geometry", {})
            if geom.get("type") == "LineString":
                coords = [(lat, lon) for lon, lat in geom.get("coordinates", [])]
                if len(coords) >= 2:
                    length = sum(AdvancedNetworkAnalyzer([])._haversine_distance(coords[i], coords[i+1]) 
                               for i in range(len(coords)-1))
                    
                    line = {
                        "id": str(uuid.uuid4()),
                        "name": feature.get("properties", {}).get("name", f"GeoJSON خط {idx+1}"),
                        "length": length,
                        "coords": coords,
                        "source": "GeoJSON",
                        "selected": True,
                        "diameter": 600,
                        "depth": 1.5,
                        "channel_type": "circular",
                    }
                    lines.append(line)
    except Exception as e:
        st.error(f"❌ خطأ في تحميل GeoJSON: {e}")
    
    return lines

# ═════════════════════════════════════════════════════════════════════════════════
# Session State Initialization
# ═════════════════════════════════════════════════════════════════════════════════

if "network_lines" not in st.session_state:
    st.session_state["network_lines"] = []
if "analyzer" not in st.session_state:
    st.session_state["analyzer"] = None
if "last_drawing_signature" not in st.session_state:
    st.session_state["last_drawing_signature"] = None

# ═════════════════════════════════════════════════════════════════════════════════
# الواجهة الرئيسية
# ═════════════════════════════════════════════════════════════════════════════════

st.markdown(MAIN_CSS, unsafe_allow_html=True)
st.markdown('<div class="hdr"><h1>🌊 محلل شبكات السيول المتقدم - تحليلات الـ Flow والقنوات</h1></div>', unsafe_allow_html=True)

# القائمة الجانبية بسيطة
with st.sidebar:
    st.markdown("### 📊 القائمة الرئيسية")
    page = st.radio("اختر القسم", [
        "🗺️ إدارة الخطوط",
        "🌐 تحليل الشبكة المتقدم",
        "🔀 تحليل الـ Flow",
        "📦 حساب القنوات الصندوقية",
        "⚠️ تحليل المخاطر",
        "📊 التقارير"
    ])

# ═════════════════════════════════════════════════════════════════════════════════
# القسم 1: إدارة الخطوط
# ═════════════════════════════════════════════════════════════════════════════════

if page == "🗺️ إدارة الخطوط":
    st.markdown('<div class="section-title">🗺️ إدارة الخطوط والبيانات</div>', unsafe_allow_html=True)
    
    col_draw, col_upload = st.columns(2)
    
    with col_draw:
        st.markdown("### 🎨 رسم الخطوط")
        if FOLIUM_AVAILABLE:
            m = folium.Map(location=[24.7136, 46.6753], zoom_start=12, tiles="OpenStreetMap")
            
            for idx, line in enumerate(st.session_state["network_lines"]):
                coords = line.get("coords", [])
                if coords:
                    color = LINE_COLORS[idx % len(LINE_COLORS)]
                    folium.PolyLine(coords, color=color, weight=3, opacity=0.8).add_to(m)
            
            draw = Draw(
                export=True,
                position="topleft",
                draw_options={"polyline": True, "polygon": False, "rectangle": False, "circle": False, "marker": False},
            )
            draw.add_to(m)
            
            map_data = st_folium(m, width=None, height=400, key="main_map", returned_objects=["last_active_drawing"])
            
            if map_data and map_data.get("last_active_drawing"):
                last_drawing = map_data["last_active_drawing"]
                if last_drawing.get("geometry", {}).get("type") == "LineString":
                    coords = [(c[1], c[0]) for c in last_drawing["geometry"]["coordinates"]]
                    drawing_signature = json.dumps(coords)
                    if st.session_state.get("last_drawing_signature") != drawing_signature and len(coords) >= 2:
                        length = sum(AdvancedNetworkAnalyzer([])._haversine_distance(coords[i], coords[i+1]) for i in range(len(coords)-1))
                        
                        new_line = {
                            "id": str(uuid.uuid4()),
                            "name": f"خط رسم {len(st.session_state['network_lines']) + 1}",
                            "length": length,
                            "coords": coords,
                            "source": "رسم يدوي",
                            "selected": True,
                            "diameter": 600,
                            "depth": 1.5,
                            "channel_type": "circular",
                        }
                        st.session_state["network_lines"].append(new_line)
                        st.session_state["last_drawing_signature"] = drawing_signature
                        st.session_state["analyzer"] = None
                        st.success(f"✅ تمت إضافة {new_line['name']}")
                        st.rerun()
    
    with col_upload:
        st.markdown("### 📤 استيراد الملفات")
        uploaded_file = st.file_uploader("GeoJSON أو Shapefile", type=["geojson", "shp", "zip"])
        
        if uploaded_file:
            if uploaded_file.name.endswith(".geojson"):
                try:
                    geojson_data = json.load(uploaded_file)
                    new_lines = load_geojson_lines(geojson_data)
                    if new_lines:
                        st.session_state["network_lines"].extend(new_lines)
                        st.session_state["analyzer"] = None
                        st.success(f"✅ تم استيراد {len(new_lines)} خط")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
    
    st.markdown('<div class="section-title">📋 الخطوط المضافة</div>', unsafe_allow_html=True)
    
    if not st.session_state["network_lines"]:
        st.info("لا توجد خطوط مضافة حتى الآن")
    else:
        for idx, ln in enumerate(st.session_state["network_lines"]):
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.write(f"**{ln['name']}** | {ln['length']:,.0f} م | {ln.get('channel_type', 'دائري')}")
            with col_del:
                if st.button("🗑️", key=f"del_{ln['id']}"):
                    st.session_state["network_lines"] = [l for l in st.session_state["network_lines"] if l['id'] != ln['id']]
                    st.session_state["analyzer"] = None
                    st.rerun()
        
        # إعدادات الخطوط
        st.markdown("### ⚙️ إعدادات الخطوط")
        for ln in st.session_state["network_lines"]:
            with st.expander(f"{ln['name']}", expanded=False):
                ln["selected"] = st.checkbox("تفعيل", value=ln["selected"], key=f"sel_{ln['id']}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    ln["diameter"] = st.selectbox("القطر (ملم)", sorted(PIPE_PRICES.keys()), 
                                                  key=f"diam_{ln['id']}")
                with col2:
                    ln["depth"] = st.number_input("العمق (م)", min_value=0.5, value=float(ln.get("depth", 1.5)), 
                                                  step=0.1, key=f"depth_{ln['id']}")
                with col3:
                    ln["channel_type"] = st.selectbox("نوع القناة", ["circular", "box"], 
                                                      key=f"type_{ln['id']}")

# ═════════════════════════════════════════════════════════════════════════════════
# القسم 2: تحليل الشبكة المتقدم
# ═════════════════════════════════════════════════════════════════════════════════

elif page == "🌐 تحليل الشبكة المتقدم":
    st.markdown('<div class="section-title">🌐 تحليل الشبكة بالتفصيل</div>', unsafe_allow_html=True)
    
    if not st.session_state["network_lines"]:
        st.warning("أضف خطوطاً أولاً من القسم السابق")
    else:
        if st.button("🔍 ابدأ التحليل", use_container_width=True, type="primary"):
            with st.spinner("جاري تحليل الشبكة..."):
                st.session_state["analyzer"] = AdvancedNetworkAnalyzer(st.session_state["network_lines"])
                st.success("✅ تم التحليل!")
        
        if st.session_state.get("analyzer"):
            analyzer = st.session_state["analyzer"]
            stats = analyzer.get_comprehensive_stats()
            resilience = analyzer.analyze_network_resilience()
            
            # عرض الإحصائيات الأساسية
            col1, col2, col3, col4 = st.columns(4)
            col1.markdown(f'<div class="metric-card"><div class="value">{stats["total_nodes"]}</div><div class="label">المناهل</div></div>', unsafe_allow_html=True)
            col2.markdown(f'<div class="metric-card"><div class="value">{stats["total_edges"]}</div><div class="label">الأنابيب</div></div>', unsafe_allow_html=True)
            col3.markdown(f'<div class="metric-card"><div class="value">{stats["total_length"]/1000:.2f}</div><div class="label">الطول (كم)</div></div>', unsafe_allow_html=True)
            col4.markdown(f'<div class="metric-card"><div class="value">{stats["density"]:.3f}</div><div class="label">الكثافة</div></div>', unsafe_allow_html=True)
            
            # تحليل المركزية
            with st.expander("📊 تحليل أهمية المناهل (Centrality)", expanded=True):
                centrality = analyzer.get_centrality_analysis()
                critical = analyzer.identify_critical_nodes()
                
                st.markdown("### 🔴 المناهل الحرجة (Critical Nodes)")
                critical_df = pd.DataFrame([
                    {
                        "منهل": node,
                        "أهمية": f"{score:.4f}",
                        "النوع": "تقاطع رئيسي" if score > 0.3 else "نقطة ربط"
                    }
                    for node, score in critical
                ])
                st.dataframe(critical_df, use_container_width=True, hide_index=True)
            
            # تحليل المرونة
            with st.expander("💪 تحليل مرونة الشبكة (Resilience)", expanded=True):
                if resilience["is_connected"]:
                    st.markdown('<div class="success-box">✅ الشبكة متصلة بالكامل</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="warning-box">⚠️ الشبكة بها {stats["num_components"]} أجزاء منفصلة</div>', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                col1.metric("اتصالية العقد", resilience["node_connectivity"])
                col2.metric("قطر الشبكة", f"{resilience['diameter']:.0f}" if resilience['diameter'] != float('inf') else "∞")
                col3.metric("معامل التجميع", f"{resilience['clustering_coefficient']:.4f}")
            
            # كشف المجموعات
            with st.expander("🎯 كشف المجموعات (Community Detection)"):
                communities = analyzer.detect_communities()
                st.write(f"عدد المجموعات المكتشفة: {len(communities)}")
                
                for i, comm in enumerate(communities):
                    st.write(f"**المجموعة {i+1}:** {len(comm)} منهل")
            
            # الاختناقات
            with st.expander("⚠️ تحديد الاختناقات (Bottlenecks)"):
                bottlenecks = analyzer.get_bottleneck_analysis()
                
                bottleneck_df = pd.DataFrame([
                    {
                        "من": edge[0],
                        "إلى": edge[1],
                        "القطر": edge[2].get('diameter', 600),
                        "المسافة": f"{edge[2].get('distance', 0)/1000:.2f} كم"
                    }
                    for edge in bottlenecks
                ])
                st.dataframe(bottleneck_df, use_container_width=True, hide_index=True)
            
            # رسم الشبكة
            with st.expander("📈 رسم الشبكة البصري", expanded=True):
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
                
                G = analyzer.G_undirected
                pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
                
                # الرسم الأول: بالألوان حسب الأهمية
                centrality = analyzer.get_centrality_analysis()
                node_colors = [centrality["betweenness"].get(node, 0) for node in G.nodes()]
                
                nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.4, ax=ax1)
                nodes = nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                                              node_size=300, cmap="YlOrRd", ax=ax1, 
                                              edgecolors='#0a2a5e', linewidths=2)
                nx.draw_networkx_labels(G, pos, labels={node: node for node in G.nodes()}, 
                                       font_size=7, ax=ax1)
                ax1.set_title("🌐 أهمية المناهل (Betweenness Centrality)", fontsize=12, fontweight='bold')
                ax1.axis('off')
                plt.colorbar(nodes, ax=ax1, label="الأهمية")
                
                # الرسم الثاني: حسب درجة الاتصال
                degree_sizes = [G.degree(node) * 100 for node in G.nodes()]
                
                nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.4, ax=ax2)
                nx.draw_networkx_nodes(G, pos, node_color='#1a5fa8', node_size=degree_sizes, 
                                      ax=ax2, edgecolors='#0a2a5e', linewidths=2)
                nx.draw_networkx_labels(G, pos, labels={node: node for node in G.nodes()}, 
                                       font_size=7, ax=ax2)
                ax2.set_title("📊 درجة الاتصال (Node Degree)", fontsize=12, fontweight='bold')
                ax2.axis('off')
                
                st.pyplot(fig, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════════
# القسم 3: تحليل الـ Flow
# ═════════════════════════════════════════════════════════════════════════════════

elif page == "🔀 تحليل الـ Flow":
    st.markdown('<div class="section-title">🔀 تحليل اتجاه الجريان (Flow Direction)</div>', unsafe_allow_html=True)
    
    if not st.session_state.get("analyzer"):
        st.warning("قم بتحليل الشبكة أولاً من القسم السابق")
    else:
        analyzer = st.session_state["analyzer"]
        flow_analysis = analyzer.get_flow_analysis()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📍 مصادر الجريان (Sources)")
            if flow_analysis["sources"]:
                for source in flow_analysis["sources"]:
                    st.write(f"• {source}")
            else:
                st.info("لا توجد مصادر محددة")
        
        with col2:
            st.markdown("### 🏁 مصبات الجريان (Sinks)")
            if flow_analysis["sinks"]:
                for sink in flow_analysis["sinks"]:
                    st.write(f"• {sink}")
            else:
                st.info("لا توجد مصبات محددة")
        
        # رسم الشبكة الموجهة
        st.markdown("### 🔗 خريطة الجريان الموجهة")
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        G_d = analyzer.G_directed
        if G_d.number_of_nodes() > 0:
            pos = nx.spring_layout(G_d, k=2, iterations=50, seed=42)
            
            # رسم الحواف الموجهة
            nx.draw_networkx_edges(G_d, pos, edge_color='#1a5fa8', arrows=True, 
                                   arrowsize=20, arrowstyle='->', width=2, 
                                   connectionstyle="arc3,rad=0.1", ax=ax)
            
            # تلوين المناهل حسب نوعها
            node_colors = []
            for node in G_d.nodes():
                if node in flow_analysis["sources"]:
                    node_colors.append('#FF6B6B')  # أحمر للمصادر
                elif node in flow_analysis["sinks"]:
                    node_colors.append('#4ECDC4')  # أزرق للمصبات
                else:
                    node_colors.append('#95E1D3')  # أخضر للوسيطة
            
            nx.draw_networkx_nodes(G_d, pos, node_color=node_colors, node_size=400, 
                                  ax=ax, edgecolors='#0a2a5e', linewidths=2)
            nx.draw_networkx_labels(G_d, pos, labels={node: node for node in G_d.nodes()}, 
                                   font_size=8, font_weight='bold', ax=ax)
            
            ax.set_title("🔀 خريطة اتجاه الجريان\n🔴 مصادر | 🔵 مصبات | 🟢 وسيطة", 
                        fontsize=14, fontweight='bold', pad=20)
            ax.axis('off')
            st.pyplot(fig, use_container_width=True)
        
        # حساب المسارات
        st.markdown("### 📐 تحليل المسارات")
        
        if flow_analysis["sources"] and flow_analysis["sinks"]:
            try:
                source = flow_analysis["sources"][0]
                sink = flow_analysis["sinks"][0]
                
                # أقصر مسار
                shortest_path = nx.shortest_path(analyzer.G_undirected, source, sink, weight='distance')
                shortest_distance = nx.shortest_path_length(analyzer.G_undirected, source, sink, weight='distance')
                
                st.write(f"**أقصر مسار:** {' → '.join(shortest_path)}")
                st.write(f"**المسافة:** {shortest_distance/1000:.2f} كم")
                
                # جميع المسارات البديلة
                try:
                    all_paths = list(nx.all_simple_paths(analyzer.G_undirected, source, sink, 
                                                         cutoff=5))
                    st.write(f"**عدد المسارات البديلة:** {len(all_paths)}")
                except:
                    pass
            except:
                st.info("لا يمكن حساب المسارات بين المصادر والمصبات")

# ═════════════════════════════════════════════════════════════════════════════════
# القسم 4: حساب القنوات الصندوقية
# ═════════════════════════════════════════════════════════════════════════════════

elif page == "📦 حساب القنوات الصندوقية":
    st.markdown('<div class="section-title">📦 تحليل القنوات الصندوقية (Box Channels)</div>', unsafe_allow_html=True)
    
    if not st.session_state["network_lines"]:
        st.warning("أضف خطوطاً أولاً")
    else:
        st.markdown("### ⚙️ إعدادات القناة الصندوقية")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_line = st.selectbox("اختر خط", 
                                        [ln['name'] for ln in st.session_state["network_lines"]])
            line = next(ln for ln in st.session_state["network_lines"] if ln['name'] == selected_line)
        
        with col2:
            channel_dim = st.selectbox("أبعاد القناة (العرض x الارتفاع)",
                                      list(BOX_CHANNEL_DIMENSIONS.keys()))
        
        dims = BOX_CHANNEL_DIMENSIONS[channel_dim]
        width = dims["width"]
        height = dims["height"]
        price_per_meter = dims["price"]
        
        # حساب السعة الهيدروليكية
        area = width * height
        perimeter = 2 * (width + height)
        hydraulic_radius = area / perimeter
        
        # معامل Manning للخرسانة
        n_manning = 0.015
        
        # افترض منحدر 1%
        slope = 0.01
        
        # معادلة Manning
        velocity = (hydraulic_radius ** (2/3) * slope ** 0.5) / n_manning
        capacity = area * velocity
        
        st.markdown("### 📊 الخصائص الهيدروليكية")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("المساحة (م²)", f"{area:.3f}")
        col2.metric("السرعة (م/ث)", f"{velocity:.3f}")
        col3.metric("السعة (م³/ث)", f"{capacity:.3f}")
        col4.metric("السعة (لتر/ث)", f"{capacity*1000:.0f}")
        
        # رسم المقطع العرضي
        st.markdown("### 📐 المقطع العرضي")
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # رسم القناة الصندوقية
        rect = FancyBboxPatch((0, 0), width, height, 
                             boxstyle="round,pad=0.05", 
                             edgecolor='#1a5fa8', facecolor='#eaf4ff', 
                             linewidth=3)
        ax.add_patch(rect)
        
        # إضافة الأبعاد
        ax.text(width/2, -0.15, f'العرض = {width} م', ha='center', fontsize=11, fontweight='bold')
        ax.text(-0.15, height/2, f'الارتفاع = {height} م', ha='right', va='center', 
               fontsize=11, fontweight='bold', rotation=90)
        
        # معلومات إضافية
        ax.text(width/2, height/2, 
               f'المساحة = {area:.3f} م²\nالسعة = {capacity:.3f} م³/ث',
               ha='center', va='center', fontsize=12, fontweight='bold',
               bbox=dict(boxstyle='round', facecolor='#fff3cd', alpha=0.8))
        
        ax.set_xlim(-0.5, width + 0.5)
        ax.set_ylim(-0.5, height + 0.5)
        ax.set_aspect('equal')
        ax.set_xlabel('العرض (متر)', fontsize=11, fontweight='bold')
        ax.set_ylabel('الارتفاع (متر)', fontsize=11, fontweight='bold')
        ax.set_title('📐 المقطع العرضي للقناة الصندوقية', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        st.pyplot(fig, use_container_width=True)
        
        # حساب التكلفة
        st.markdown("### 💰 حساب التكلفة")
        
        length = line.get("length", 0)
        total_cost = length * price_per_meter
        
        col1, col2, col3 = st.columns(3)
        col1.metric("طول الخط", f"{length:,.0f} م")
        col2.metric("السعر/متر", f"{price_per_meter:,.0f} ريال")
        col3.metric("التكلفة الإجمالية", f"{total_cost:,.0f} ريال")
        
        if total_cost > 0:
            if capacity >= 0.5:
                st.markdown('<div class="success-box">✅ السعة الهيدروليكية كافية للجريان المتوقع</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="warning-box">⚠️ السعة الهيدروليكية قد لا تكون كافية، قد تحتاج لقناة أكبر</div>', unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════════
# القسم 5: تحليل المخاطر
# ═════════════════════════════════════════════════════════════════════════════════

elif page == "⚠️ تحليل المخاطر":
    st.markdown('<div class="section-title">⚠️ تقييم المخاطر والمشاكل المحتملة</div>', unsafe_allow_html=True)
    
    if not st.session_state.get("analyzer"):
        st.warning("قم بتحليل الشبكة أولاً")
    else:
        analyzer = st.session_state["analyzer"]
        
        risk_assessment = {
            "الشبكة غير متصلة": {
                "severity": "عالي" if not analyzer.analyze_network_resilience()["is_connected"] else "منخفض",
                "description": "بعض أجزاء الشبكة غير مرتبطة بالبقية",
                "solution": "ربط الأجزاء المنفصلة بخطوط إضافية"
            },
            "اختناقات في التدفق": {
                "severity": "عالي",
                "description": "وجود أنابيب بأقطار صغيرة قد تحد من التدفق",
                "solution": "استبدال الأنابيب الصغيرة بأقطار أكبر"
            },
            "نقاط حرجة متعددة": {
                "severity": "متوسط",
                "description": "وجود مناهل حرجة قد تؤثر على الشبكة عند عطلها",
                "solution": "إضافة مسارات بديلة حول النقاط الحرجة"
            },
            "تجميع عالي": {
                "severity": "منخفض" if analyzer.analyze_network_resilience()["clustering_coefficient"] < 0.5 else "متوسط",
                "description": "مناطق متجمعة قد تسبب احتقان",
                "solution": "توزيع المناهل بشكل أفضل"
            }
        }
        
        for risk, details in risk_assessment.items():
            severity_color = {
                "عالي": "#dc3545",
                "متوسط": "#ffc107",
                "منخفض": "#28a745"
            }[details["severity"]]
            
            st.markdown(f"""
            <div style="border-left: 5px solid {severity_color}; padding: 12px; margin: 10px 0; 
                       background-color: rgba(0,0,0,0.02); border-radius: 5px;">
                <h4 style="color: {severity_color}; margin-top: 0;">⚠️ {risk}</h4>
                <p><strong>الخطورة:</strong> {details['severity']}</p>
                <p><strong>الوصف:</strong> {details['description']}</p>
                <p><strong>الحل:</strong> {details['solution']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # تقرير المخاطر
        st.markdown("### 📋 تقييم المخاطر الشامل")
        
        resilience = analyzer.analyze_network_resilience()
        centrality = analyzer.get_centrality_analysis()
        bottlenecks = analyzer.get_bottleneck_analysis()
        
        risk_score = 0
        
        # الاتصالية
        if not resilience["is_connected"]:
            risk_score += 30
        
        # عدد النقاط الحرجة
        critical_count = sum(1 for score in centrality["betweenness"].values() if score > 0.2)
        risk_score += min(20, critical_count * 5)
        
        # الاختناقات
        risk_score += min(20, len(bottlenecks) * 4)
        
        # كثافة الشبكة
        if resilience["density"] < 0.3:
            risk_score += 15
        
        # الكثافة في طريقة عرض
        risk_percentage = min(100, risk_score)
        
        st.markdown("### 📊 درجة المخاطر الكلية")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            fig, ax = plt.subplots(figsize=(10, 2))
            
            colors = ['#28a745', '#ffc107', '#dc3545']
            if risk_percentage < 33:
                color = colors[0]
            elif risk_percentage < 66:
                color = colors[1]
            else:
                color = colors[2]
            
            ax.barh([0], [risk_percentage], color=color, height=0.5)
            ax.set_xlim(0, 100)
            ax.set_ylim(-0.5, 0.5)
            ax.set_xlabel('درجة المخاطر (%)', fontsize=12, fontweight='bold')
            ax.set_title('📊 تقييم مستوى المخاطر', fontsize=13, fontweight='bold')
            ax.set_yticks([])
            
            # إضافة النسبة المئوية
            ax.text(risk_percentage/2, 0, f'{risk_percentage:.0f}%', 
                   ha='center', va='center', fontsize=16, fontweight='bold', color='white')
            
            st.pyplot(fig, use_container_width=True)
        
        with col2:
            if risk_percentage < 33:
                st.markdown('<div class="success-box">✅ منخفضة</div>', unsafe_allow_html=True)
            elif risk_percentage < 66:
                st.markdown('<div class="warning-box">⚠️ متوسطة</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="danger-box">❌ عالية</div>', unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════════
# القسم 6: التقارير
# ═════════════════════════════════════════════════════════════════════════════════

elif page == "📊 التقارير":
    st.markdown('<div class="section-title">📊 التقارير الشاملة</div>', unsafe_allow_html=True)
    
    if not st.session_state.get("analyzer"):
        st.warning("قم بتحليل الشبكة أولاً")
    else:
        analyzer = st.session_state["analyzer"]
        stats = analyzer.get_comprehensive_stats()
        resilience = analyzer.analyze_network_resilience()
        centrality = analyzer.get_centrality_analysis()
        
        # ملخص المشروع
        with st.expander("📋 ملخص المشروع", expanded=True):
            col1, col2, col3 = st.columns(3)
            col1.metric("عدد الخطوط", len(st.session_state["network_lines"]))
            col2.metric("عدد المناهل", stats["total_nodes"])
            col3.metric("عدد الأنابيب", stats["total_edges"])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("الطول الإجمالي", f"{stats['total_length']/1000:.2f} كم")
            col2.metric("متصلة", "نعم" if resilience["is_connected"] else "لا")
            col3.metric("كثافة الشبكة", f"{resilience['density']:.4f}")
        
        # المناهل الحرجة
        with st.expander("🔴 المناهل الحرجة"):
            critical = analyzer.identify_critical_nodes()
            critical_df = pd.DataFrame([
                {"المنهل": node, "الأهمية": f"{score:.4f}"}
                for node, score in critical
            ])
            st.dataframe(critical_df, use_container_width=True, hide_index=True)
        
        # إحصائيات الخطوط
        with st.expander("📋 إحصائيات الخطوط"):
            lines_data = []
            for idx, line in enumerate(st.session_state["network_lines"]):
                if line.get("selected", True):
                    lines_data.append({
                        "الخط": line.get("name"),
                        "الطول (م)": f"{line.get('length', 0):,.0f}",
                        "القطر (ملم)": line.get("diameter", 600),
                        "نوع القناة": line.get("channel_type", "دائري"),
                    })
            
            if lines_data:
                st.dataframe(pd.DataFrame(lines_data), use_container_width=True, hide_index=True)
        
        # تحميل التقارير
        st.markdown("### 📥 تحميل التقارير")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # تقرير CSV
            csv_content = "المؤشر,القيمة\n"
            csv_content += f"عدد المناهل,{stats['total_nodes']}\n"
            csv_content += f"عدد الأنابيب,{stats['total_edges']}\n"
            csv_content += f"الطول الإجمالي (م),{stats['total_length']:.0f}\n"
            csv_content += f"كثافة الشبكة,{resilience['density']:.4f}\n"
            csv_content += f"معامل التجميع,{resilience['clustering_coefficient']:.4f}\n"
            
            st.download_button(
                label="📊 تحميل تقرير CSV",
                data=csv_content,
                file_name=f"network_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # تقرير نصي
            txt_content = "=" * 50 + "\n"
            txt_content += "تقرير تحليل شبكة السيول\n"
            txt_content += f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            txt_content += "=" * 50 + "\n\n"
            
            txt_content += "📊 الإحصائيات الأساسية:\n"
            txt_content += f"- عدد المناهل: {stats['total_nodes']}\n"
            txt_content += f"- عدد الأنابيب: {stats['total_edges']}\n"
            txt_content += f"- الطول الإجمالي: {stats['total_length']/1000:.2f} كم\n\n"
            
            txt_content += "💪 تقييم المرونة:\n"
            txt_content += f"- الشبكة متصلة: {'نعم' if resilience['is_connected'] else 'لا'}\n"
            txt_content += f"- كثافة الشبكة: {resilience['density']:.4f}\n"
            txt_content += f"- معامل التجميع: {resilience['clustering_coefficient']:.4f}\n"
            
            st.download_button(
                label="📄 تحميل تقرير نصي",
                data=txt_content,
                file_name=f"network_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )

st.markdown("<div style='text-align:center;color:#999;font-size:0.75rem;margin-top:30px'>© 2025 Advanced Flood Drainage Network Analysis - v3.0</div>", unsafe_allow_html=True)

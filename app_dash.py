# ══════════════════════════════════════════════════════════════════
#  حاسبة تكلفة شبكات تصريف السيول — Dash + dash-leaflet
#  Eng. Ahmed Adam | 2025
# ══════════════════════════════════════════════════════════════════
import json, math, os, tempfile, zipfile, base64
from io import BytesIO
import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
import dash_leaflet as dl
import dash_leaflet.express as dlx

# ══ الأسعار ══
PIPE_PRICES = {
    400:2713,500:2935,600:3145,700:3431,800:4009,
    900:4299,1000:4625,1100:5010,1200:5335,1300:5725,1400:6055,
}
BOX_CHANNEL_PRICE  = 9336.0
OPEN_CHANNEL_PRICE = 13052.0
LINE_TYPES = {"pipe":"أنبوب","box_channel":"قناة صندوقية","open_channel":"قناة مفتوحة"}
RLAT, RLON = 24.7136, 46.6753

# ══ دوال حسابية ══
def hav(lon1,lat1,lon2,lat2):
    R=6371000; p1,p2=math.radians(lat1),math.radians(lat2)
    a=math.sin(math.radians(lat2-lat1)/2)**2+math.cos(p1)*math.cos(p2)*math.sin(math.radians(lon2-lon1)/2)**2
    return 2*R*math.asin(math.sqrt(max(0,a)))

def length_m(coords):
    t=0.0
    for i in range(len(coords)-1):
        try: t+=hav(coords[i][0],coords[i][1],coords[i+1][0],coords[i+1][1])
        except: pass
    return t

def length_proj(coords):
    t=0.0
    for i in range(len(coords)-1):
        dx=coords[i+1][0]-coords[i][0]; dy=coords[i+1][1]-coords[i][1]
        t+=math.sqrt(dx*dx+dy*dy)
    return t

def is_proj(c): return bool(c) and (abs(c[0][0])>180 or abs(c[0][1])>90)

def get_price(lt, dia=None, cp=None):
    if cp and cp>0: return float(cp)
    if lt=="box_channel": return BOX_CHANNEL_PRICE
    if lt=="open_channel": return OPEN_CHANNEL_PRICE
    if dia and dia in PIPE_PRICES: return float(PIPE_PRICES[dia])
    if dia: return float(PIPE_PRICES[min(PIPE_PRICES,key=lambda x:abs(x-dia))])
    return float(PIPE_PRICES[1400])

def parse_geom(geom):
    if not geom: return []
    t=geom.get("type",""); raw=geom.get("coordinates",[])
    pts=raw if t=="LineString" else [p for part in raw for p in part] if t=="MultiLineString" else []
    return [[float(c[0]),float(c[1])] for c in pts if isinstance(c,(list,tuple)) and len(c)>=2]

def convert_wgs84(coords, epsg=32637):
    try:
        from pyproj import Transformer
        tr=Transformer.from_crs(f"EPSG:{epsg}","EPSG:4326",always_xy=True)
        return [[lon,lat] for lon,lat in (tr.transform(x,y) for x,y in coords)]
    except: return coords

def sanitize_props(props):
    clean={}
    for k,v in props.items():
        try:
            if v is None: clean[str(k)]=None
            elif isinstance(v,(int,float,bool,str)): clean[str(k)]=v
            else: clean[str(k)]=str(v)
        except: pass
    return clean

def load_geojson(content_b64):
    try:
        raw=base64.b64decode(content_b64.split(",")[1])
        gj=json.loads(raw.decode("utf-8","ignore"))
        crs=gj.get("crs",{}); epsg=None
        if crs:
            name=crs.get("properties",{}).get("name","")
            if "EPSG:" in name.upper():
                try: epsg=int(name.upper().split("EPSG:")[-1].strip().split()[0])
                except: pass
        feats=[]
        for i,f in enumerate(gj.get("features",[])):
            if not isinstance(f,dict): continue
            coords=parse_geom(f.get("geometry") or {})
            if len(coords)<2: continue
            props=sanitize_props(f.get("properties") or {})
            if is_proj(coords):
                length=round(length_proj(coords),2)
                coords=convert_wgs84(coords,epsg or 32637)
            else: length=round(length_m(coords),2)
            feats.append({"i":i,"len":length,"coords":coords,"props":props})
        return feats
    except Exception as e:
        print("GeoJSON error:",e); return []

def load_shapefile(content_b64):
    try:
        import shapefile
        raw=base64.b64decode(content_b64.split(",")[1])
        with tempfile.TemporaryDirectory() as td:
            with zipfile.ZipFile(BytesIO(raw)) as z: z.extractall(td)
            shp=next((os.path.join(r,f) for r,_,fs in os.walk(td) for f in fs if f.lower().endswith(".shp")),None)
            if not shp: return []
            epsg=None
            prj=shp.replace(".shp",".prj")
            if os.path.exists(prj):
                try:
                    from pyproj import CRS
                    with open(prj,"r",errors="ignore") as pf: ep=CRS.from_wkt(pf.read()).to_epsg()
                    if ep: epsg=ep
                except: pass
            sf=shapefile.Reader(shp); fnames=[f[0] for f in sf.fields[1:]]
            feats=[]
            for i,sr in enumerate(sf.shapeRecords()):
                coords=[[float(p[0]),float(p[1])] for p in sr.shape.points if len(p)>=2]
                if len(coords)<2: continue
                props=sanitize_props(dict(zip(fnames,sr.record)))
                if is_proj(coords):
                    length=round(length_proj(coords),2)
                    coords=convert_wgs84(coords,epsg or 32637)
                else: length=round(length_m(coords),2)
                feats.append({"i":i,"len":length,"coords":coords,"props":props})
            return feats
    except Exception as e:
        print("SHP error:",e); return []

def gen_pdf(segments_data, stot, total_cost):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as rlc
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate,Table,TableStyle,Paragraph,Spacer,HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    FONT_PATH="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    FONTB_PATH="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        pdfmetrics.registerFont(TTFont("AF",FONT_PATH)); pdfmetrics.registerFont(TTFont("AFB",FONTB_PATH))
        FONT="AF"; FONTB="AFB"
    except: FONT="Helvetica"; FONTB="Helvetica-Bold"
    C=rlc.HexColor; buf=BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=1.5*cm,leftMargin=1.5*cm,topMargin=1.5*cm,bottomMargin=1.5*cm)
    styles=getSampleStyleSheet()
    def S(nm,**kw): return ParagraphStyle(nm,parent=styles["Normal"],fontName=FONT,**kw)
    def SB(nm,**kw): return ParagraphStyle(nm,parent=styles["Normal"],fontName=FONTB,**kw)
    story=[]
    story.append(Paragraph("Flood Drainage Network Cost Report",SB("t",fontSize=16,textColor=C("#0a2a5e"),alignment=TA_CENTER,spaceAfter=4)))
    story.append(Paragraph("Eng. Ahmed Adam | Flood Drainage Networks 2025",S("s",fontSize=9,textColor=C("#1a5fa8"),alignment=TA_CENTER,spaceAfter=10)))
    story.append(HRFlowable(width="100%",thickness=2,color=C("#1a5fa8"),spaceAfter=10))
    rows=[["Description","Value"],["Number of Elements",str(len(segments_data))],
          ["Total Length","%.2f m / %.3f km"%(stot,stot/1000)],
          ["Total Cost","%.2f SAR"%total_cost],["In Millions","%.4f M SAR"%(total_cost/1e6)]]
    t=Table(rows,colWidths=[7*cm,10*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),C("#0a2a5e")),("TEXTCOLOR",(0,0),(-1,0),rlc.white),
        ("FONTNAME",(0,0),(-1,0),FONTB),("FONTNAME",(0,1),(-1,-1),FONT),
        ("FONTSIZE",(0,0),(-1,-1),10),("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("BACKGROUND",(0,-1),(-1,-1),C("#1a5fa8")),
        ("TEXTCOLOR",(0,-1),(-1,-1),rlc.white),("FONTNAME",(0,-1),(-1,-1),FONTB),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),[rlc.white,C("#f0f7ff")]),
        ("GRID",(0,0),(-1,-1),.5,C("#d0e4f7")),("ROWHEIGHT",(0,0),(-1,-1),22)]))
    story+=[t,Spacer(1,14)]
    story+=[HRFlowable(width="100%",thickness=1,color=C("#1a5fa8"),spaceAfter=5),
            Paragraph("Eng. Ahmed Adam | Flood Drainage Networks © 2025",S("ft",fontSize=8,textColor=C("#888"),alignment=TA_CENTER))]
    doc.build(story); return buf.getvalue()

# ══════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
*{box-sizing:border-box;font-family:'Cairo',sans-serif!important}
body{background:#f0f4f8;margin:0;direction:rtl}
.app-wrap{max-width:900px;margin:0 auto;padding:10px 12px 40px}
/* هيدر */
.hdr{background:linear-gradient(135deg,#0a2a5e,#1a5fa8);color:#fff;padding:12px 18px;
  border-radius:12px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.hdr h1{margin:0;font-size:1.1rem;font-weight:900}
.hdr p{margin:0;font-size:.72rem;color:#b8d9f8}
/* البطاقات */
.card{background:#fff;border-radius:12px;padding:14px 16px;box-shadow:0 2px 8px rgba(0,0,0,.07);margin-bottom:12px}
.card-title{color:#0a2a5e;font-size:.9rem;font-weight:900;margin-bottom:10px;
  border-bottom:2px solid #1a5fa8;padding-bottom:6px}
/* بطاقات الأرقام */
.metric{background:#fff;border-radius:10px;padding:10px;border-top:3px solid #1a5fa8;
  text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.06)}
.metric-val{font-size:1.15rem;font-weight:900;color:#0a2a5e}
.metric-lbl{font-size:.68rem;color:#6b7a99;margin-top:2px}
/* الأزرار */
.btn{background:linear-gradient(135deg,#1a5fa8,#0a2a5e)!important;color:#fff!important;
  border:none!important;border-radius:10px!important;font-family:'Cairo',sans-serif!important;
  font-weight:700!important;padding:12px 20px!important;cursor:pointer!important;
  font-size:.9rem!important;width:100%!important;min-height:46px!important;touch-action:manipulation}
.btn:hover{opacity:.9}
.btn-danger{background:linear-gradient(135deg,#c0392b,#922b21)!important}
.btn-success{background:linear-gradient(135deg,#27ae60,#1e8449)!important}
.btn-sm{padding:8px 14px!important;min-height:38px!important;font-size:.82rem!important}
/* النتيجة */
.result-box{background:linear-gradient(135deg,#0a2a5e,#1a5fa8);color:#fff;
  padding:16px;border-radius:12px;text-align:center;font-weight:700;line-height:2.2;font-size:.9rem}
/* بطاقة خط */
.line-card{background:#fff;border:1.5px solid #d0e4f7;border-right:5px solid #1a5fa8;
  border-radius:10px;padding:12px 14px;margin-bottom:8px;cursor:pointer;transition:all .2s}
.line-card:hover{border-right-color:#e74c3c;box-shadow:0 3px 10px rgba(231,76,60,.2)}
.line-card.selected{border-right-color:#e74c3c;background:#fff5f5;border-color:#fadbd8}
.line-card h4{margin:0 0 4px;font-size:.85rem;color:#0a2a5e}
/* شارة */
.badge{display:inline-block;padding:3px 10px;border-radius:12px;font-size:.75rem;font-weight:700}
.badge-pipe{background:#eaf4ff;color:#1a5fa8}
.badge-box{background:#fff3e0;color:#e65100}
.badge-open{background:#e8f5e9;color:#2e7d32}
.badge-sel{background:#fadbd8;color:#c0392b}
/* الخط المختار في الخريطة */
.sel-info{background:#e74c3c;color:#fff;border-radius:8px;padding:8px 14px;
  font-weight:700;font-size:.85rem;margin-bottom:8px;text-align:center}
/* حقول الإدخال */
.form-label{font-size:.82rem;font-weight:700;color:#0a2a5e;margin-bottom:4px}
.form-select,.form-input{width:100%;padding:10px 12px;border:1.5px solid #d0e4f7;
  border-radius:8px;font-family:'Cairo',sans-serif;font-size:.88rem;color:#1a2a3a;
  background:#fff;min-height:44px;direction:rtl}
.form-select:focus,.form-input:focus{outline:none;border-color:#1a5fa8}
/* تنبيه */
.info-box{background:#eaf4ff;border-right:4px solid #1a5fa8;border-radius:8px;
  padding:10px 13px;font-size:.82rem;color:#0a2a5e;margin-bottom:8px;line-height:1.8}
/* شبكة */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:10px}
@media(max-width:600px){.grid-2{grid-template-columns:1fr}.grid-3{grid-template-columns:1fr 1fr}}
/* تبويبات */
.tabs{display:flex;gap:6px;margin-bottom:12px;border-bottom:2px solid #d0e4f7;padding-bottom:0}
.tab-btn{padding:10px 18px;border:none;background:none;font-family:'Cairo',sans-serif;
  font-weight:700;font-size:.88rem;color:#6b7a99;cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px}
.tab-btn.active{color:#0a2a5e;border-bottom-color:#1a5fa8}
/* login */
.login-wrap{max-width:400px;margin:60px auto;background:#fff;border-radius:16px;
  padding:32px 28px;box-shadow:0 8px 30px rgba(0,0,0,.1)}
.login-title{text-align:center;color:#0a2a5e;font-size:1.4rem;font-weight:900;margin-bottom:6px}
.login-sub{text-align:center;color:#6b7a99;font-size:.8rem;margin-bottom:24px}
"""

# ══════════════════════════════════════════════════════════════════
# التطبيق
# ══════════════════════════════════════════════════════════════════
app = dash.Dash(__name__, suppress_callback_exceptions=True,
                meta_tags=[{"name":"viewport","content":"width=device-width,initial-scale=1"}])
app.title = "حاسبة شبكات السيول"
server = app.server

def login_layout():
    return html.Div([
        html.Div([
            html.Div("🌊", style={"textAlign":"center","fontSize":"3rem","marginBottom":"8px"}),
            html.Div("حاسبة شبكات تصريف السيول", className="login-title"),
            html.Div("Flood Drainage Network Calculator · Eng. Ahmed Adam", className="login-sub"),
            html.Hr(style={"borderColor":"#d0e4f7","marginBottom":"20px"}),
            html.Div("اسم المستخدم", className="form-label"),
            dcc.Input(id="login-user", type="text", placeholder="أدخل اسم المستخدم",
                      className="form-input", style={"marginBottom":"12px"}),
            html.Div("كلمة المرور", className="form-label"),
            dcc.Input(id="login-pass", type="password", placeholder="• • • • • • • •",
                      className="form-input", style={"marginBottom":"16px"}),
            html.Button("🔑 تسجيل الدخول", id="login-btn", className="btn", n_clicks=0),
            html.Div(id="login-error", style={"color":"#c0392b","textAlign":"center","marginTop":"10px","fontWeight":"700"}),
        ], className="login-wrap")
    ], style={"background":"linear-gradient(135deg,#050e1f,#0d2447)","minHeight":"100vh"})

def main_layout():
    return html.Div([
        # ══ Store ══
        dcc.Store(id="store-feats", data=[]),
        dcc.Store(id="store-sel", data=[]),
        dcc.Store(id="store-meta", data={}),
        dcc.Store(id="store-result", data=None),
        dcc.Download(id="download-pdf"),

        html.Div([
            # ══ هيدر ══
            html.Div([
                html.Div([
                    html.H1("🌊 حاسبة تكلفة شبكات تصريف السيول"),
                    html.P("تحليل الشبكات · حساب الأطوال · تقدير التكاليف"),
                ]),
                html.Button("خروج 🚪", id="logout-btn", className="btn btn-sm",
                            style={"width":"auto","minHeight":"36px","padding":"6px 14px"}),
            ], className="hdr"),

            # ══ رفع الملف ══
            html.Div([
                html.Div("📂 رفع بيانات الشبكة", className="card-title"),
                dcc.Upload(id="upload-file",
                    children=html.Div(["🗂️ اسحب الملف هنا أو ", html.B("اضغط للاختيار"),
                                       html.Br(), html.Small("GeoJSON أو Shapefile (.zip)", style={"color":"#6b7a99"})]),
                    style={"border":"2px dashed #1a5fa8","borderRadius":"10px","padding":"20px",
                           "textAlign":"center","cursor":"pointer","background":"#f7faff","color":"#0a2a5e"},
                    multiple=False),
                html.Div(id="upload-status", style={"marginTop":"8px"}),
            ], className="card"),

            # ══ تبويبات ══
            html.Div([
                html.Button("🗺️ الخريطة والحساب", id="tab-map-btn", className="tab-btn active", n_clicks=0),
                html.Button("📊 جدول البيانات",    id="tab-tbl-btn", className="tab-btn",        n_clicks=0),
            ], className="tabs"),

            # ══ محتوى التبويبات ══
            html.Div(id="tab-content"),

        ], className="app-wrap"),
    ])

app.layout = html.Div([
    dcc.Store(id="auth-store", data={"authenticated": False}),
    html.Div(id="page-content"),
    html.Style(CSS),
])

# ══════════════════════════════════════════════════════════════════
# Callbacks
# ══════════════════════════════════════════════════════════════════

@app.callback(Output("page-content","children"), Input("auth-store","data"))
def render_page(auth):
    if auth and auth.get("authenticated"): return main_layout()
    return login_layout()

@app.callback(
    Output("auth-store","data"), Output("login-error","children"),
    Input("login-btn","n_clicks"),
    State("login-user","value"), State("login-pass","value"),
    State("auth-store","data"), prevent_initial_call=True)
def do_login(n, user, pwd, auth):
    if not n: return no_update, ""
    try:
        import toml
        cfg = toml.load(".streamlit/secrets.toml")
        users = cfg.get("users", {})
        if users.get(user,"") == pwd:
            return {"authenticated":True,"user":user}, ""
    except:
        pass
    if user == "admin" and pwd == "admin":
        return {"authenticated":True,"user":user}, ""
    return {"authenticated":False}, "❌ اسم المستخدم أو كلمة المرور غير صحيحة"

@app.callback(
    Output("auth-store","data",allow_duplicate=True),
    Input("logout-btn","n_clicks"), prevent_initial_call=True)
def logout(n):
    if n: return {"authenticated":False}
    return no_update

# ══ رفع الملف ══
@app.callback(
    Output("store-feats","data"), Output("upload-status","children"),
    Output("store-sel","data",allow_duplicate=True),
    Output("store-meta","data",allow_duplicate=True),
    Input("upload-file","contents"),
    State("upload-file","filename"), prevent_initial_call=True)
def handle_upload(contents, filename):
    if not contents: return [], "", [], {}
    ext = filename.lower().rsplit(".",1)[-1] if filename else ""
    if ext in ("geojson","json"): feats = load_geojson(contents)
    elif ext == "zip": feats = load_shapefile(contents)
    else: return [], html.Div("❌ صيغة غير مدعومة",style={"color":"#c0392b","fontWeight":"700"}), [], {}
    if feats:
        msg = html.Div(f"✅ تم تحميل {len(feats)} خط بنجاح!",style={"color":"#27ae60","fontWeight":"700"})
        return feats, msg, [], {}
    return [], html.Div("⚠️ لم تُوجد خطوط صالحة",style={"color":"#e67e22","fontWeight":"700"}), [], {}

# ══ التبويبات ══
@app.callback(
    Output("tab-content","children"),
    Output("tab-map-btn","className"), Output("tab-tbl-btn","className"),
    Input("tab-map-btn","n_clicks"), Input("tab-tbl-btn","n_clicks"),
    State("store-feats","data"), State("store-sel","data"),
    State("store-meta","data"), State("store-result","data"))
def render_tabs(n_map, n_tbl, feats, sel, meta, result):
    ctx = callback_context
    active = "tab-tbl" if ctx.triggered and "tab-tbl" in (ctx.triggered[0]["prop_id"] or "") else "tab-map"
    m_cls = "tab-btn active" if active=="tab-map" else "tab-btn"
    t_cls = "tab-btn active" if active=="tab-tbl" else "tab-btn"
    if active == "tab-map":
        return build_map_tab(feats or [], sel or [], meta or {}, result), m_cls, t_cls
    else:
        return build_table_tab(feats or []), m_cls, t_cls

def build_map_tab(feats, sel, meta, result):
    sel_set = set(sel)

    center = [RLAT, RLON]; zoom = 10
    if feats:
        all_coords = [c for f in feats for c in f["coords"]]
        if all_coords:
            center = [sum(c[1] for c in all_coords)/len(all_coords),
                      sum(c[0] for c in all_coords)/len(all_coords)]
            zoom = 13

    lines = []
    for f in feats:
        is_sel = f["i"] in sel_set
        color = "#e74c3c" if is_sel else "#1a5fa8"
        weight = 6 if is_sel else 4
        positions = [[c[1],c[0]] for c in f["coords"]]
        tooltip_txt = f"خط #{f['i']} | {f['len']:,.0f} م | {'✓ محدد' if is_sel else 'اضغط للتحديد'}"
        lines.append(
            dl.Polyline(
                id={"type":"line","index":f["i"]},
                positions=positions,
                color=color,
                weight=weight,
                opacity=0.9,
                children=dl.Tooltip(tooltip_txt),
            )
        )
        if is_sel:
            lines.append(dl.Polyline(positions=positions,color="#ff6666",weight=14,opacity=0.15))

    map_component = dl.Map(
        id="main-map",
        center=center, zoom=zoom,
        style={"height":"380px","borderRadius":"10px","marginBottom":"10px"},
        children=[
            dl.TileLayer(url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                         attribution="© OpenStreetMap"),
            dl.LayerGroup(id="lines-layer", children=lines),
        ]
    )

    stats = []
    if feats:
        tl = sum(f["len"] for f in feats)
        stats = html.Div([
            html.Div([
                html.Div([html.Div(f"{len(feats):,}",className="metric-val"),html.Div("عدد الخطوط",className="metric-lbl")],className="metric"),
                html.Div([html.Div(f"{tl/1000:,.2f}",className="metric-val"),html.Div("إجمالي الطول (كم)",className="metric-lbl")],className="metric"),
            ],className="grid-2"),
        ],style={"marginBottom":"8px"})

    sel_banner = []
    if sel_set:
        names = "، ".join(f"#{i}" for i in sorted(sel_set))
        sel_banner = html.Div(f"✓ محدد: {names} ({len(sel_set)} خط)", className="sel-info")

    sel_btns = []
    if feats:
        sel_btns = html.Div([
            html.Div("📌 اختيار الخطوط", className="card-title"),
            html.Div([
                html.Button("✅ تحديد الكل",  id="btn-sel-all",  className="btn btn-success btn-sm", n_clicks=0),
                html.Button("❌ إلغاء الكل", id="btn-desel-all", className="btn btn-danger btn-sm",  n_clicks=0),
            ], className="grid-2"),
        ])

    settings = []
    sfeats = [f for f in feats if f["i"] in sel_set]
    if sfeats:
        rows = [html.Div("⚙️ إعدادات الخطوط المختارة", className="card-title")]
        for f in sfeats:
            fi = f["i"]
            fm = meta.get(str(fi), {"line_type":"pipe","diameter_mm":1400,"custom_price":0})
            lt = fm.get("line_type","pipe")
            dia = fm.get("diameter_mm",1400)
            cp = fm.get("custom_price",0)
            gp = get_price(lt, dia if lt=="pipe" else None, 0)
            badge_cls = "badge badge-pipe" if lt=="pipe" else ("badge badge-box" if lt=="box_channel" else "badge badge-open")
            rows.append(html.Details([
                html.Summary([
                    html.Span(LINE_TYPES.get(lt,"—"), className=badge_cls),
                    f" خط #{fi} — {f['len']:,.1f} م"
                ], style={"cursor":"pointer","padding":"8px","fontWeight":"700","fontSize":".85rem"}),
                html.Div([
                    html.Div("نوع الخط:", className="form-label"),
                    dcc.Dropdown(id={"type":"lt","index":fi},
                        options=[{"label":v,"value":k} for k,v in LINE_TYPES.items()],
                        value=lt, clearable=False,
                        style={"fontFamily":"Cairo,sans-serif","direction":"rtl","marginBottom":"8px"}),
                    html.Div("القطر (ملم):", className="form-label",
                             id={"type":"dia-lbl","index":fi},
                             style={"display":"block" if lt=="pipe" else "none"}),
                    dcc.Dropdown(id={"type":"dia","index":fi},
                        options=[{"label":f"{d} ملم","value":d} for d in PIPE_PRICES],
                        value=dia, clearable=False,
                        style={"fontFamily":"Cairo,sans-serif","direction":"rtl","marginBottom":"8px",
                               "display":"block" if lt=="pipe" else "none"}),
                    html.Div("السعر (ريال/م):", className="form-label"),
                    html.Div([
                        dcc.Input(id={"type":"cp","index":fi}, type="number",
                                  value=cp if cp else gp, min=0, step=100,
                                  className="form-input",
                                  placeholder=f"السعر الإرشادي: {gp:,.0f}"),
                    ],style={"marginBottom":"6px"}),
                    html.Div(f"💰 التكلفة المتوقعة: {f['len']*(cp if cp else gp):,.0f} ريال",
                             className="info-box"),
                    html.Button("💾 حفظ الإعدادات", id={"type":"save-meta","index":fi},
                                className="btn btn-sm", n_clicks=0,
                                style={"marginBottom":"4px"}),
                ], style={"padding":"10px 14px","borderTop":"1px solid #d0e4f7"}),
            ], style={"background":"#fff","border":"1.5px solid #d0e4f7","borderRight":"5px solid #1a5fa8",
                      "borderRadius":"10px","marginBottom":"8px","overflow":"hidden"}))
        settings = html.Div(rows)

    summary = []
    if sel_set:
        stot = sum(f["len"] for f in sfeats)
        summary = html.Div([
            html.Div([
                html.Div([html.Div(str(len(sfeats)),className="metric-val"),html.Div("خطوط مختارة",className="metric-lbl")],className="metric"),
                html.Div([html.Div(f"{stot:,.0f}",className="metric-val"),html.Div("مجموع الأطوال (م)",className="metric-lbl")],className="metric"),
            ],className="grid-2"),
        ],style={"marginBottom":"8px"})

    calc_btn = html.Div([
        html.Div("💰 حساب التكلفة", className="card-title"),
        html.Button("⚡ احسب التكلفة الآن", id="btn-calc", className="btn", n_clicks=0),
        html.Div(id="calc-status",style={"marginTop":"8px"}),
    ])

    result_div = []
    if result:
        segs=result["segments_data"]
        parts=" | ".join(f"{s['label']} ({s['len']:,.0f}م)" for s in segs)
        result_div = html.Div([
            html.Div([
                html.Div(parts,style={"fontSize":".8rem","marginBottom":"6px"}),
                html.Div(f"📏 مجموع الأطوال: {result['stot']:,.2f} م ({result['stot']/1000:.3f} كم)"),
                html.Hr(style={"borderColor":"rgba(255,255,255,.3)","margin":"8px 0"}),
                html.Div(f"💰 التكلفة الإجمالية:", style={"fontSize":"1rem"}),
                html.Div(f"{result['total_cost']:,.2f} ريال",style={"fontSize":"1.4rem","fontWeight":"900"}),
                html.Div(f"≈ {result['total_cost']/1e6:.3f} مليون ريال"),
            ], className="result-box", style={"marginTop":"10px","marginBottom":"10px"}),
            html.Div([
                html.Div([
                    html.Button("📄 إصدار تقرير PDF", id="btn-pdf", className="btn", n_clicks=0),
                ],style={"marginTop":"8px"}),
                html.Div(id="pdf-status"),
            ]),
        ])

    return html.Div([
        html.Div([stats], className="card") if feats else html.Div(),
        html.Div([
            html.Div("🗺️ الخريطة", className="card-title"),
            html.Div("👆 اضغط على أي خط في الخريطة لتحديده أو إلغاء تحديده" if feats else "",
                     style={"fontSize":".76rem","color":"#1a5fa8","background":"#eaf4ff",
                            "borderRadius":"6px","padding":"5px 10px","marginBottom":"6px","textAlign":"center"}),
            map_component,
            sel_banner,
        ], className="card"),
        html.Div([sel_btns], className="card") if feats else html.Div(),
        html.Div([settings], className="card") if sfeats else html.Div(),
        html.Div([summary, calc_btn, result_div], className="card") if feats else
            html.Div(html.Div("📱 ارفع ملف الشبكة أعلاه للبدء.", className="info-box"), className="card"),
    ])

def build_table_tab(feats):
    if not feats:
        return html.Div(html.Div("📂 ارفع ملف الشبكة أولاً.", className="info-box"), className="card")
    import pandas as pd
    rows = []
    for f in feats:
        r = {"رقم الخط":f["i"],"الطول (م)":round(f["len"],2),"الطول (كم)":round(f["len"]/1000,4)}
        r.update({str(k):v for k,v in f["props"].items()})
        rows.append(r)
    df = pd.DataFrame(rows)
    from dash import dash_table
    return html.Div([
        html.Div(f"📋 بيانات الشبكة — {len(feats)} خط", className="card-title"),
        dash_table.DataTable(
            data=df.to_dict("records"),
            columns=[{"name":c,"id":c} for c in df.columns],
            page_size=20, filter_action="native", sort_action="native",
            style_table={"overflowX":"auto"},
            style_cell={"fontFamily":"Cairo,sans-serif","textAlign":"right",
                       "padding":"8px","fontSize":"13px"},
            style_header={"background":"#0a2a5e","color":"#fff","fontWeight":"700",
                         "fontFamily":"Cairo,sans-serif"},
            style_data_conditional=[{"if":{"row_index":"odd"},"background":"#f7faff"}],
        ),
    ], className="card")

# ══ اختيار الخط من الخريطة ══
@app.callback(
    Output("store-sel","data"),
    Output("store-meta","data",allow_duplicate=True),
    Input({"type":"line","index":dash.ALL},"n_clicks"),
    State("store-sel","data"),
    State("store-feats","data"),
    State("store-meta","data"),
    prevent_initial_call=True)
def on_line_click(n_clicks_list, sel, feats, meta):
    ctx = callback_context
    if not ctx.triggered: return no_update, no_update
    prop = ctx.triggered[0]["prop_id"]
    if not prop or not n_clicks_list: return no_update, no_update
    try:
        idx = json.loads(prop.split(".")[0])["index"]
    except: return no_update, no_update
    click_val = ctx.triggered[0]["value"]
    if not click_val: return no_update, no_update

    sel_set = set(sel or [])
    if idx in sel_set: sel_set.discard(idx)
    else: sel_set.add(idx)
    meta = dict(meta or {})
    if str(idx) not in meta:
        meta[str(idx)] = {"line_type":"pipe","diameter_mm":1400,"custom_price":0}
    return list(sel_set), meta

# ══ تحديد الكل / إلغاء الكل ══
@app.callback(
    Output("store-sel","data",allow_duplicate=True),
    Input("btn-sel-all","n_clicks"), Input("btn-desel-all","n_clicks"),
    State("store-feats","data"), prevent_initial_call=True)
def sel_all_desel(n_sel, n_desel, feats):
    ctx = callback_context
    if not ctx.triggered: return no_update
    if "sel-all" in ctx.triggered[0]["prop_id"]:
        return [f["i"] for f in (feats or [])]
    return []

# ══ حفظ إعدادات الخط ══
@app.callback(
    Output("store-meta","data"),
    Output("calc-status","children",allow_duplicate=True),
    Input({"type":"save-meta","index":dash.ALL},"n_clicks"),
    State({"type":"lt","index":dash.ALL},"value"),
    State({"type":"dia","index":dash.ALL},"value"),
    State({"type":"cp","index":dash.ALL},"value"),
    State({"type":"save-meta","index":dash.ALL},"id"),
    State("store-meta","data"),
    prevent_initial_call=True)
def save_meta(n_clicks, lts, dias, cps, ids, meta):
    ctx = callback_context
    if not ctx.triggered or not any(n for n in n_clicks if n): return no_update, no_update
    meta = dict(meta or {})
    for i, id_dict in enumerate(ids or []):
        fi = id_dict["index"]
        lt = lts[i] if i < len(lts) else "pipe"
        dia = dias[i] if i < len(dias) else 1400
        cp = cps[i] if i < len(cps) else 0
        meta[str(fi)] = {"line_type":lt,"diameter_mm":dia,"custom_price":cp or 0}
    return meta, html.Div("✅ تم حفظ الإعدادات",style={"color":"#27ae60","fontWeight":"700","fontSize":".82rem"})

# ══ حساب التكلفة ══
@app.callback(
    Output("store-result","data"),
    Output("calc-status","children"),
    Input("btn-calc","n_clicks"),
    State("store-feats","data"),
    State("store-sel","data"),
    State("store-meta","data"),
    prevent_initial_call=True)
def calc_cost(n, feats, sel, meta):
    if not n: return no_update, no_update
    sel_set = set(sel or [])
    sfeats = [f for f in (feats or []) if f["i"] in sel_set]
    if not sfeats:
        return no_update, html.Div("⚠️ اختر خطاً من الخريطة أو القائمة أولاً",
                                   style={"color":"#e67e22","fontWeight":"700"})
    segs=[]; tc=0.0; tl=0.0
    for f in sfeats:
        fm = (meta or {}).get(str(f["i"]),{"line_type":"pipe","diameter_mm":1400,"custom_price":0})
        lt = fm.get("line_type","pipe")
        dia = fm.get("diameter_mm",1400) if lt=="pipe" else None
        cp = fm.get("custom_price",0)
        ppm = get_price(lt, dia, cp)
        cost = f["len"]*ppm; tc+=cost; tl+=f["len"]
        segs.append({"label":f"#{f['i']}","len":f["len"],"line_type":lt,
                     "diameter_mm":dia,"price_per_m":ppm,"cost":cost,"is_drawn":False})
    return {"segments_data":segs,"stot":tl,"total_cost":tc}, \
           html.Div("✅ تم الحساب بنجاح!",style={"color":"#27ae60","fontWeight":"700"})

# ══ إنشاء PDF ══
@app.callback(
    Output("download-pdf","data"),
    Output("pdf-status","children"),
    Input("btn-pdf","n_clicks"),
    State("store-result","data"),
    prevent_initial_call=True)
def make_pdf(n, result):
    if not n or not result: return no_update, no_update
    try:
        pdf_bytes = gen_pdf(result["segments_data"], result["stot"], result["total_cost"])
        return dcc.send_bytes(pdf_bytes, "flood_cost_report.pdf"), \
               html.Div("✅ جاهز للتحميل!",style={"color":"#27ae60","fontWeight":"700"})
    except Exception as e:
        return no_update, html.Div(f"❌ خطأ: {e}",style={"color":"#c0392b"})

# ══ تحديث الخريطة عند تغيّر الاختيار أو البيانات ══
@app.callback(
    Output("tab-content","children",allow_duplicate=True),
    Output("tab-map-btn","className",allow_duplicate=True),
    Output("tab-tbl-btn","className",allow_duplicate=True),
    Input("store-sel","data"),
    Input("store-feats","data"),
    Input("store-result","data"),
    State("store-meta","data"),
    State("tab-map-btn","className"),
    prevent_initial_call=True)
def refresh_map(sel, feats, result, meta, map_cls):
    if "active" not in (map_cls or ""):
        return no_update, no_update, no_update
    return build_map_tab(feats or [], sel or [], meta or {}, result), "tab-btn active", "tab-btn"

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)

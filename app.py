import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io
import time
from pathlib import Path

st.set_page_config(
    page_title="Smart Waste Segregation System",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Rajdhani:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #0d0d0d;
    color: #e8e8e8;
}
[data-testid="stSidebar"] {
    background: #111111;
    border-right: 1px solid #2a2a2a;
}
h1, h2, h3 { font-family: 'Rajdhani', sans-serif; }
p, div, span, label { font-family: 'Space Mono', monospace; font-size: 0.82rem; }

@keyframes floatBin {
    0%   { transform: translateY(0px); }
    50%  { transform: translateY(-8px); }
    100% { transform: translateY(0px); }
}
.bin-float { display:inline-block; animation: floatBin 3s ease-in-out infinite; }

.metric-card {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 1.1rem 1.2rem;
    text-align: center;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: #a855f7; }
.metric-val {
    font-family: 'Rajdhani', sans-serif;
    font-size: 2.4rem;
    font-weight: 700;
    color: #a855f7;
}
.metric-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}
.bar-wrap {
    background: #1a1a1a;
    border-radius: 4px;
    height: 10px;
    width: 100%;
    margin: 4px 0 10px;
}
.bar-fill { height: 10px; border-radius: 4px; transition: width 0.6s ease; }

.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #ec4899);
    color: #fff;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 0.08em;
    border: none;
    border-radius: 6px;
    padding: 0.5rem 1.5rem;
    cursor: pointer;
}
.stButton > button:hover { opacity: 0.85; }

[data-testid="stFileUploader"] {
    border: 2px dashed #2a2a2a;
    border-radius: 8px;
    background: #111;
}
.section-divider {
    border: none;
    border-top: 1px solid #2a2a2a;
    margin: 1.5rem 0;
}
.kw {
    color: #ffffff;
    font-weight: 700;
    background: rgba(168, 85, 247, 0.45);
    border: 1.5px solid rgba(192, 132, 252, 0.85);
    border-radius: 4px;
    padding: 2px 7px;
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    box-shadow: 0 0 8px rgba(168,85,247,0.5), inset 0 0 6px rgba(168,85,247,0.15);
}
.sb-section-head {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    color: #c084fc;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 4px;
    margin: 14px 0 8px;
}
.model-badge {
    display: inline-block;
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border-radius: 4px;
    padding: 2px 8px;
    margin-bottom: 6px;
}
.report-box {
    background: linear-gradient(135deg, #0f0a1e, #161626);
    border: 1px solid #3a2a5a;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    position: relative;
    overflow: hidden;
}
.report-box::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #7c3aed, #ec4899, #38bdf8);
}
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────
CLASS_NAMES = ["Cardboard","Paper","Plastic","Metal","Glass","Wood","Cloth","Rubber","Waste"]

RECYCLABILITY = {
    "Cardboard":0.92,"Paper":0.88,"Plastic":0.60,
    "Metal":0.95,"Glass":0.90,"Wood":0.45,
    "Cloth":0.35,"Rubber":0.25,"Waste":0.05,"garbage":0.05,
}

RECYCLE_INFO = {
    "Cardboard":("♻️ Highly Recyclable",    "#a855f7","Flatten & drop in paper bin. Remove tape first."),
    "Paper":    ("♻️ Highly Recyclable",    "#a855f7","Dry paper only. Shred confidential docs before recycling."),
    "Plastic":  ("⚠️ Moderately Recyclable","#ffcc00","Check resin code (1–7). Rinse before recycling."),
    "Metal":    ("♻️ Highly Recyclable",    "#a855f7","Aluminium & steel — crush cans to save space."),
    "Glass":    ("♻️ Highly Recyclable",    "#a855f7","Sort by colour. Remove lids. Do NOT mix with ceramics."),
    "Wood":     ("🔄 Partially Recyclable", "#ff9500","Clean wood → composting. Treated/painted → general waste."),
    "Cloth":    ("🔄 Partially Recyclable", "#ff9500","Donate wearable items. Scraps → textile recycling banks."),
    "Rubber":   ("⚠️ Low Recyclability",    "#ff4d4d","Tyres → tyre recycling drop-off. Small rubber → landfill."),
    "Waste":    ("🗑️ Non-Recyclable",       "#ff2222","General waste bin. Reduce at source."),
    "garbage":  ("🗑️ Non-Recyclable",       "#ff2222","General waste bin. Reduce at source."),
}

CLASS_SIDEBAR_COLOR = {
    "Cardboard":"#c084fc","Paper":"#d4d4d4","Plastic":"#38bdf8",
    "Metal":"#c0c0c0","Glass":"#4ade80","Wood":"#fb923c",
    "Cloth":"#f472b6","Rubber":"#ff073a","Waste":"#e0e0e0",
}
CLASS_EMOJI = {
    "Cardboard":"📦","Paper":"📄","Plastic":"🧴","Metal":"🔩",
    "Glass":"🍶","Wood":"🧱","Cloth":"👕","Rubber":"🛢","Waste":"🗑️",
}
CLASS_COLORS_BGR = {
    "Cardboard":(200,100,255),"Paper":(200,200,200),"Plastic":(255,200,0),
    "Metal":(180,180,180),"Glass":(50,220,50),"Wood":(0,140,255),
    "Cloth":(180,100,240),"Rubber":(0,0,220),"Waste":(80,80,80),
}
MODEL1_COLOR_BGR = (0,0,255)

SVG_DUSTBIN = """
<svg xmlns="http://www.w3.org/2000/svg" width="54" height="64" viewBox="0 0 54 64">
  <defs>
    <linearGradient id="binGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%"   stop-color="#c084fc"/>
      <stop offset="50%"  stop-color="#a855f7"/>
      <stop offset="100%" stop-color="#ec4899"/>
    </linearGradient>
  </defs>
  <rect x="20" y="2" width="14" height="5" rx="2.5" fill="url(#binGrad)"/>
  <rect x="6" y="9" width="42" height="8" rx="3" fill="url(#binGrad)"/>
  <path d="M10 19 L12 58 Q12 61 15 61 L39 61 Q42 61 42 58 L44 19 Z" fill="url(#binGrad)" opacity="0.92"/>
  <line x1="21" y1="23" x2="20" y2="57" stroke="#0d0d0d" stroke-width="2.5" stroke-linecap="round" opacity="0.35"/>
  <line x1="27" y1="23" x2="27" y2="57" stroke="#0d0d0d" stroke-width="2.5" stroke-linecap="round" opacity="0.35"/>
  <line x1="33" y1="23" x2="34" y2="57" stroke="#0d0d0d" stroke-width="2.5" stroke-linecap="round" opacity="0.35"/>
</svg>"""


# ── Model helpers ──────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_model(model_path: str):
    from ultralytics import YOLO
    return YOLO(model_path)


def get_adaptive_font_params(img_h, img_w):
    base = min(img_h, img_w)
    font_scale = max(0.4, min(0.8, base / 700.0))
    thickness  = max(1, int(base / 600))
    box_thick  = max(2, int(base / 350))
    return font_scale, thickness, box_thick


def run_detection_model1(model, image_np, conf_thresh):
    """Garbage zone detector — tight NMS, limited detections."""
    results = model.predict(
        source=image_np, conf=conf_thresh, iou=0.35,
        imgsz=640, agnostic_nms=True, verbose=False, max_det=8,
    )
    return results[0]


def run_detection_model2(model, image_np, conf_thresh, iou_thresh, garbage_boxes=None):
    """9-class detector — filter to inside garbage zones if provided."""
    results = model.predict(
        source=image_np, conf=conf_thresh, iou=iou_thresh,
        imgsz=640, agnostic_nms=True, verbose=False, max_det=120,
    )
    result = results[0]

    if garbage_boxes and len(garbage_boxes) > 0 and result.boxes is not None and len(result.boxes) > 0:
        keep = []
        for i, box in enumerate(result.boxes):
            bx1,by1,bx2,by2 = map(int, box.xyxy[0])
            box_area = max(1,(bx2-bx1)*(by2-by1))
            inside = False
            for gx1,gy1,gx2,gy2 in garbage_boxes:
                ix1=max(bx1,gx1); iy1=max(by1,gy1)
                ix2=min(bx2,gx2); iy2=min(by2,gy2)
                if ix2>ix1 and iy2>iy1:
                    if (ix2-ix1)*(iy2-iy1)/box_area >= 0.25:
                        inside=True; break
            if inside:
                keep.append(i)
        result.boxes = result.boxes[keep] if keep else result.boxes[result.boxes[:0]]
    return result


def merge_garbage_zones(result1):
    """Merge overlapping / adjacent garbage zone boxes into tighter ones."""
    if result1 is None or result1.boxes is None or len(result1.boxes) == 0:
        return []
    raw = [tuple(map(int, b.xyxy[0])) for b in result1.boxes]
    merged = True
    while merged:
        merged = False
        out = []
        used = [False]*len(raw)
        for i in range(len(raw)):
            if used[i]: continue
            ax1,ay1,ax2,ay2 = raw[i]
            for j in range(i+1,len(raw)):
                if used[j]: continue
                bx1,by1,bx2,by2 = raw[j]
                # IoU or containment
                ix1=max(ax1,bx1); iy1=max(ay1,by1)
                ix2=min(ax2,bx2); iy2=min(ay2,by2)
                if ix2>ix1 and iy2>iy1:
                    inter=(ix2-ix1)*(iy2-iy1)
                    union=(ax2-ax1)*(ay2-ay1)+(bx2-bx1)*(by2-by1)-inter
                    if union>0 and inter/union>0.05:
                        ax1=min(ax1,bx1); ay1=min(ay1,by1)
                        ax2=max(ax2,bx2); ay2=max(ay2,by2)
                        used[j]=True; merged=True
            out.append((ax1,ay1,ax2,ay2)); used[i]=True
        raw=out
    return raw


def draw_boxes_dual(image_np, result1, result2, merged_zones):
    img = image_np.copy()
    h,w = img.shape[:2]
    fs,th,bt = get_adaptive_font_params(h,w)

    # ── Model 1: merged garbage zones ──
    for (x1,y1,x2,y2) in merged_zones:
        overlay = img.copy()
        cv2.rectangle(overlay,(x1,y1),(x2,y2),MODEL1_COLOR_BGR,-1)
        cv2.addWeighted(overlay,0.06,img,0.94,0,img)
        cv2.rectangle(img,(x1,y1),(x2,y2),MODEL1_COLOR_BGR,bt+1)
        label="garbage zone"
        (tw,tth),_=cv2.getTextSize(label,cv2.FONT_HERSHEY_SIMPLEX,fs,th)
        cv2.rectangle(img,(x1,y1-tth-8),(x1+tw+8,y1),MODEL1_COLOR_BGR,-1)
        cv2.putText(img,label,(x1+4,y1-4),cv2.FONT_HERSHEY_SIMPLEX,fs,(255,255,255),th,cv2.LINE_AA)

    # ── Model 2: 9-class objects ──
    if result2 is not None and result2.boxes is not None and len(result2.boxes)>0:
        for box in result2.boxes:
            cls_id=int(box.cls[0]); conf=float(box.conf[0])
            label=CLASS_NAMES[cls_id] if cls_id<len(CLASS_NAMES) else str(cls_id)
            color=CLASS_COLORS_BGR.get(label,(200,200,200))
            x1,y1,x2,y2=map(int,box.xyxy[0])
            cv2.rectangle(img,(x1,y1),(x2,y2),color,bt)
            txt=f"{label} {conf:.2f}"
            (tw,tth),_=cv2.getTextSize(txt,cv2.FONT_HERSHEY_SIMPLEX,fs,th)
            ly=max(y1,tth+8)
            cv2.rectangle(img,(x1,ly-tth-8),(x1+tw+8,ly),color,-1)
            cv2.putText(img,txt,(x1+4,ly-4),cv2.FONT_HERSHEY_SIMPLEX,fs,(0,0,0),th,cv2.LINE_AA)
    return img


def draw_boxes_single(image_np, result, is_model1=False, merged_zones=None):
    img = image_np.copy()
    h,w = img.shape[:2]
    fs,th,bt = get_adaptive_font_params(h,w)

    if is_model1 and merged_zones:
        for (x1,y1,x2,y2) in merged_zones:
            overlay=img.copy()
            cv2.rectangle(overlay,(x1,y1),(x2,y2),MODEL1_COLOR_BGR,-1)
            cv2.addWeighted(overlay,0.06,img,0.94,0,img)
            cv2.rectangle(img,(x1,y1),(x2,y2),MODEL1_COLOR_BGR,bt+1)
            label="garbage zone"
            (tw,tth),_=cv2.getTextSize(label,cv2.FONT_HERSHEY_SIMPLEX,fs,th)
            cv2.rectangle(img,(x1,y1-tth-8),(x1+tw+8,y1),MODEL1_COLOR_BGR,-1)
            cv2.putText(img,label,(x1+4,y1-4),cv2.FONT_HERSHEY_SIMPLEX,fs,(255,255,255),th,cv2.LINE_AA)
        return img

    if result is None or result.boxes is None or len(result.boxes)==0:
        return img
    for box in result.boxes:
        cls_id=int(box.cls[0]); conf=float(box.conf[0])
        label=CLASS_NAMES[cls_id] if cls_id<len(CLASS_NAMES) else str(cls_id)
        color=CLASS_COLORS_BGR.get(label,(200,200,200))
        x1,y1,x2,y2=map(int,box.xyxy[0])
        cv2.rectangle(img,(x1,y1),(x2,y2),color,bt)
        txt=f"{label} {conf:.2f}"
        (tw,tth),_=cv2.getTextSize(txt,cv2.FONT_HERSHEY_SIMPLEX,fs,th)
        ly=max(y1,tth+8)
        cv2.rectangle(img,(x1,ly-tth-8),(x1+tw+8,ly),color,-1)
        cv2.putText(img,txt,(x1+4,ly-4),cv2.FONT_HERSHEY_SIMPLEX,fs,(0,0,0),th,cv2.LINE_AA)
    return img


def aggregate_detections(result, class_names=None):
    counts={}
    if result is None or result.boxes is None: return counts
    for box in result.boxes:
        cls_id=int(box.cls[0]); conf=float(box.conf[0])
        if class_names:
            label=class_names[cls_id] if cls_id<len(class_names) else str(cls_id)
        else:
            label=result.names.get(cls_id,str(cls_id)) if result.names else str(cls_id)
        counts.setdefault(label,[]).append(conf)
    return counts


def aggregate_dual(result1, result2, merged_zones):
    counts={}
    if result1 is not None and merged_zones:
        for _ in merged_zones:
            counts.setdefault("garbage",[]).append(0.5)
    if result2 is not None:
        for k,v in aggregate_detections(result2,CLASS_NAMES).items():
            counts.setdefault(k,[]).extend(v)
    return counts


def overall_recyclability(det_counts):
    total=sum(len(v) for v in det_counts.values())
    if total==0: return 0.0
    return sum(RECYCLABILITY.get(k,0)*len(v) for k,v in det_counts.items())/total


def generate_text_report(det_counts, overall_rc, total, elapsed_ms, source_label):
    lines=[]
    lines.append("="*52)
    lines.append("   AI BASED SMART WASTE SEGREGATION SYSTEM")
    lines.append("         Detection Report")
    lines.append("="*52)
    lines.append(f"  Image Source      : {source_label}")
    lines.append(f"  Inference Time    : {elapsed_ms:.0f} ms")
    lines.append(f"  Total Detections  : {total}")
    lines.append(f"  Unique Classes    : {len(det_counts)}")
    lines.append(f"  Recyclability Score: {overall_rc*100:.1f}%")
    lines.append("-"*52)
    lines.append("  PER-CLASS BREAKDOWN")
    lines.append("-"*52)
    for cls,confs in sorted(det_counts.items(),key=lambda x:-len(x[1])):
        rc=RECYCLABILITY.get(cls,0)
        avg=sum(confs)/len(confs) if confs else 0
        lbl=RECYCLE_INFO.get(cls,("Unknown","",""))[0]
        lines.append(f"  {cls:<12} | Count:{len(confs):>3} | Recycle:{rc*100:.0f}% | AvgConf:{avg*100:.1f}% | {lbl}")
    lines.append("-"*52)
    recyclable=sum(len(v) for k,v in det_counts.items() if RECYCLABILITY.get(k,0)>=0.6)
    lines.append(f"  Recyclable Items  : {recyclable}")
    lines.append(f"  Non-Recyclable    : {total-recyclable}")
    lines.append("="*52)
    lines.append("  Supervised by : Engr. Dr. Imran Khan")
    lines.append("  Developed by  : Muzna Siddiqui, Maheen Siddiqui,")
    lines.append("                  Sumama Madda, Kaif Abdullah")
    lines.append("="*52)
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:

    # ── Supervised / Developed By ──
    st.markdown("""
    <div style='background:linear-gradient(135deg,#0d0d0d,#161626);
         border:1px solid #3a2a5a;border-radius:10px;padding:16px 16px 14px;
         box-shadow:0 0 20px rgba(168,85,247,0.10)'>
      <div style='display:flex;align-items:center;gap:8px;margin-bottom:14px'>
        <div style='width:3px;height:30px;background:linear-gradient(180deg,#a855f7,#38bdf8);
             border-radius:2px;flex-shrink:0'></div>
        <div>
          <div style='font-family:Space Mono,monospace;font-size:0.58rem;font-weight:700;
               color:#6b5580;letter-spacing:.18em;text-transform:uppercase;margin-bottom:3px'>
            Supervised By</div>
          <div style='font-family:Rajdhani,sans-serif;font-size:1.05rem;font-weight:700;
               background:linear-gradient(110deg,#c084fc,#38bdf8);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
               background-clip:text;line-height:1.2'>
            Engr. Dr. Imran Khan</div>
        </div>
      </div>
      <div style='border-top:1px solid #2a2a3a;margin:0 0 12px'></div>
      <div style='display:flex;align-items:flex-start;gap:8px'>
        <div style='width:3px;height:80px;background:linear-gradient(180deg,#ec4899,#a855f7);
             border-radius:2px;margin-top:3px;flex-shrink:0'></div>
        <div>
          <div style='font-family:Space Mono,monospace;font-size:0.58rem;font-weight:700;
               color:#6b5580;letter-spacing:.18em;text-transform:uppercase;margin-bottom:6px'>
            Developed By</div>
          <div style='font-family:Rajdhani,sans-serif;font-size:0.95rem;font-weight:600;
               color:#e8e8e8;line-height:2.2'>
            Muzna Siddiqui<br>Maheen Siddiqui<br>Sumama Madda<br>Kaif Abdullah
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── GAP then App Title ──
    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='margin-bottom:18px'>
      <div style='font-family:Rajdhani,sans-serif;font-size:1.75rem;font-weight:700;
           background:linear-gradient(110deg,#c084fc,#a855f7,#d4d4d4,#c0c0c0,#b39ddb);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
           line-height:1.25'>
        AI BASED SMART WASTE<br>SEGREGATION SYSTEM
      </div>
      <div style='font-family:Space Mono,monospace;font-size:0.63rem;color:#6b7280;
           letter-spacing:0.15em;text-transform:uppercase;margin-top:7px'>
        ─ YOLOv8 Waste Detector ─
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Settings ──
    with st.expander("⚙️  SETTINGS", expanded=True):
        detection_mode = st.selectbox(
            "Detection Mode",
            options=["Dual Model (Model1 + Model2)","Model 1 Only (cluttered garbage)","Model 2 Only (9-class)"],
            help="Dual: Model 1 finds garbage zones (red), Model 2 classifies items inside"
        )
        conf_thresh = st.slider("Confidence threshold", 0.10, 0.95, 0.20, 0.05)
        iou_thresh  = st.slider("IoU (NMS) threshold",  0.10, 0.95, 0.35, 0.05)

    # ── Box Colors ──
    st.markdown("<div class='sb-section-head'>🎨 Box Colors</div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='background:#161616;border:1px solid #2a2a2a;border-radius:8px;
         padding:12px 14px;margin-bottom:4px'>
      <div style='display:flex;align-items:center;gap:10px;margin-bottom:12px'>
        <div style='width:24px;height:11px;background:#ff0000;border-radius:3px;flex-shrink:0'></div>
        <div>
          <div style='font-family:Rajdhani,sans-serif;font-size:0.85rem;font-weight:700;
               color:#ff6b6b;letter-spacing:0.08em'>MODEL 1</div>
          <div style='font-family:Space Mono,monospace;font-size:0.6rem;color:#666'>
            Cluttered Garbage Zone</div>
        </div>
      </div>
      <div style='display:flex;align-items:center;gap:10px'>
        <div style='width:24px;height:11px;
             background:linear-gradient(90deg,#c084fc,#38bdf8,#4ade80);
             border-radius:3px;flex-shrink:0'></div>
        <div>
          <div style='font-family:Rajdhani,sans-serif;font-size:0.85rem;font-weight:700;
               color:#c084fc;letter-spacing:0.08em'>MODEL 2</div>
          <div style='font-family:Space Mono,monospace;font-size:0.6rem;color:#666'>
            9 Individual Waste Classes</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Model 1 classes ──
    st.markdown("<div class='sb-section-head'>🔴 Model 1 — Cluttered Garbage</div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='display:flex;align-items:center;gap:9px;padding:6px 4px;border-bottom:1px solid #1a1a1a'>
      <div style='width:13px;height:13px;background:#ff0000;border-radius:2px;flex-shrink:0'></div>
      <span style='font-family:Rajdhani,sans-serif;font-size:0.9rem;font-weight:700;color:#ff6b6b'>garbage</span>
      <span style='font-family:Space Mono,monospace;font-size:0.6rem;color:#555'>(zone)</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Model 2 classes ──
    st.markdown("<div class='sb-section-head'>🟢 Model 2 — 9 Waste Classes</div>", unsafe_allow_html=True)
    for cls in CLASS_NAMES:
        color = CLASS_SIDEBAR_COLOR.get(cls,"#aaa")
        emoji = CLASS_EMOJI.get(cls,"•")
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:9px;
             padding:5px 4px;border-bottom:1px solid #1a1a1a'>
          <span style='font-size:0.9rem'>{emoji}</span>
          <span style='font-family:Rajdhani,sans-serif;font-size:0.88rem;
               font-weight:700;color:{color}'>{cls}</span>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  MAIN HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding-top:1.2rem;font-family:Space Mono,monospace;
     font-size:0.72rem;letter-spacing:0.22em;text-transform:uppercase;font-weight:700;
     background:linear-gradient(110deg,#a855f7,#c0c0c8,#ff073a);
     -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text'>
  Final Year Project &nbsp;·&nbsp; YOLOv8m &nbsp;·&nbsp; AI Powered
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style='text-align:center;padding:0.4rem 0 0'>
  <span style='font-family:Rajdhani,sans-serif;font-size:4.8rem;font-weight:700;
       letter-spacing:0.06em;line-height:1.05;
       background:linear-gradient(110deg,#c084fc,#a855f7,#ec4899,#38bdf8);
       -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text'>
    AI BASED SMART WASTE<br>SEGREGATION SYSTEM
  </span>
  <span class='bin-float' style='display:inline-block;margin-left:18px;
       vertical-align:middle;position:relative;top:-8px'>
    {SVG_DUSTBIN}
  </span>
</div>
<div style='text-align:center;padding-bottom:0.9rem;font-family:Space Mono,monospace;
     font-size:0.72rem;letter-spacing:0.2em;text-transform:uppercase;margin-top:0.5rem;
     font-weight:700;
     background:linear-gradient(110deg,#a855f7,#c0c0c8,#ff073a);
     -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text'>
  Mixed Waste Detection &amp; Recyclability Analysis &nbsp;·&nbsp; YOLOv8m
</div>
""", unsafe_allow_html=True)

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
# ─────────────────────────────────────────────
#  MODEL LOAD
# ─────────────────────────────────────────────
MODEL_PATHS = {"model1":"weights/model1_best.pt","model2":"weights/model2_best.pt"}
model1=None; model2=None

use_m1 = detection_mode in ["Dual Model (Model1 + Model2)","Model 1 Only (garbage zone)"]
use_m2 = detection_mode in ["Dual Model (Model1 + Model2)","Model 2 Only (9-class)"]

if use_m1:
    if Path(MODEL_PATHS["model1"]).exists():
        with st.spinner("Loading Model 1…"):
            try:
                model1=load_model(MODEL_PATHS["model1"])
                st.markdown("""<div style='background:#0d1b2a;border:1px solid #1d4ed8;border-radius:6px;
                     padding:0.5rem 1rem;font-family:Space Mono;font-size:0.75rem;color:#60a5fa;margin-bottom:4px'>
                  🔴 Model 1 loaded (garbage zone detector)</div>""", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Model 1 load failed: {e}")
    else:
        st.warning(f"⚠️ Model 1 not found at `{MODEL_PATHS['model1']}`")

if use_m2:
    if Path(MODEL_PATHS["model2"]).exists():
        with st.spinner("Loading Model 2…"):
            try:
                model2=load_model(MODEL_PATHS["model2"])
                st.markdown("""<div style='background:#0d1b2a;border:1px solid #1d4ed8;border-radius:6px;
                     padding:0.5rem 1rem;font-family:Space Mono;font-size:0.75rem;color:#60a5fa;margin-bottom:4px'>
                  🟢 Model 2 loaded (9-class detector)</div>""", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Model 2 load failed: {e}")
    else:
        st.warning(f"⚠️ Model 2 not found at `{MODEL_PATHS['model2']}`")

if not Path(MODEL_PATHS["model1"]).exists() or not Path(MODEL_PATHS["model2"]).exists():
    st.info("📁 Place weights as:\n```\nweights/model1_best.pt\nweights/model2_best.pt\n```")

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  INPUT
# ─────────────────────────────────────────────
tab_upload, tab_cam = st.tabs(["📁  Upload Image","📷  Camera"])
image_pil=None; source_label=""

with tab_upload:
    uploaded=st.file_uploader("Image",type=["jpg","jpeg","jfif","png","bmp","webp"],label_visibility="collapsed")
    if uploaded:
        image_pil=Image.open(uploaded).convert("RGB"); source_label=uploaded.name

with tab_cam:
    cam_img=st.camera_input("Take a photo of garbage")
    if cam_img:
        image_pil=Image.open(cam_img).convert("RGB"); source_label="camera_capture"

# ─────────────────────────────────────────────
#  DETECTION
# ─────────────────────────────────────────────
if image_pil is not None:
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    img_np  = np.array(image_pil)
    img_bgr = cv2.cvtColor(img_np,cv2.COLOR_RGB2BGR)

    col_img,col_res = st.columns([1,1],gap="large")
    with col_img:
        st.markdown("**Original Image**")
        st.image(image_pil,use_container_width=True)
        h,w=img_np.shape[:2]
        st.caption(f"Resolution: {w}×{h} px  |  Source: {source_label}")

    if model1 is None and model2 is None:
        with col_res:
            st.info("Load at least one model to run detection.")
    else:
        with st.spinner("🔍 Scanning…"):
            t0=time.time()
            result1=None; result2=None; merged_zones=[]

            if model1 is not None:
                result1=run_detection_model1(model1,img_bgr,conf_thresh)
                merged_zones=merge_garbage_zones(result1)

            if model2 is not None:
                gb=merged_zones if detection_mode=="Dual Model (Model1 + Model2)" and merged_zones else None
                result2=run_detection_model2(model2,img_bgr,conf_thresh,iou_thresh,gb)

            elapsed=time.time()-t0

            if result1 is not None and result2 is not None:
                ann_bgr=draw_boxes_dual(img_bgr,result1,result2,merged_zones)
            elif result1 is not None:
                ann_bgr=draw_boxes_single(img_bgr,result1,is_model1=True,merged_zones=merged_zones)
            else:
                ann_bgr=draw_boxes_single(img_bgr,result2,is_model1=False)

            ann_rgb=cv2.cvtColor(ann_bgr,cv2.COLOR_BGR2RGB)

        with col_res:
            st.markdown("**Detection Result**")
            legend=[]
            if merged_zones: legend.append("🔴 Red = Garbage Zone (Model 1)")
            if result2 is not None: legend.append("🟢 Colours = Waste Classes (Model 2)")
            if legend: st.caption("  |  ".join(legend))
            st.image(ann_rgb,use_container_width=True)
            st.caption(f"Inference: {elapsed*1000:.0f} ms")

        det_counts=aggregate_dual(result1,result2,merged_zones)
        total_dets=sum(len(v) for v in det_counts.values())
        rc_score=overall_recyclability(det_counts)

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        # ── KPIs ──
        k1,k2,k3,k4=st.columns(4)
        rc_color="#a855f7" if rc_score>=0.7 else "#ffcc00" if rc_score>=0.4 else "#ff4d4d"
        kpi=lambda val,lbl,c="#a855f7": f"<div class='metric-card'><div class='metric-val' style='color:{c}'>{val}</div><div class='metric-label'>{lbl}</div></div>"
        k1.markdown(kpi(total_dets,"Items Detected"),unsafe_allow_html=True)
        k2.markdown(kpi(len(det_counts),"Unique Classes"),unsafe_allow_html=True)
        k3.markdown(kpi(f"{rc_score*100:.0f}%","Recyclability Score",rc_color),unsafe_allow_html=True)
        k4.markdown(kpi(f"{elapsed*1000:.0f}ms","Inference Time","#38bdf8"),unsafe_allow_html=True)

        # ── Zoom option ──
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        with st.expander("🔍 Zoom / Inspect Detected Image", expanded=False):
            zoom=st.slider("Zoom level",1.0,4.0,1.0,0.25,key="zoom_slider")
            zh=int(ann_rgb.shape[0]*zoom)
            zw=int(ann_rgb.shape[1]*zoom)
            zoomed=cv2.resize(ann_rgb,(zw,zh),interpolation=cv2.INTER_LINEAR)
            st.image(zoomed,use_container_width=False,width=min(zw,1200))
            st.caption(f"Zoomed: {zw}×{zh} px  (×{zoom})")

        # ── Per-class breakdown ──
        if det_counts:
            st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
            st.markdown("### 🗂️ Per-Class Breakdown")
            for cls_name,confs in sorted(det_counts.items(),key=lambda x:-len(x[1])):
                rc_ratio=RECYCLABILITY.get(cls_name,0)
                rc_label,rc_hex,tip=RECYCLE_INFO.get(cls_name,("Unknown","#888",""))
                avg_conf=sum(confs)/len(confs); count=len(confs); pct=int(rc_ratio*100)
                with st.expander(f"{rc_label}  ·  **{cls_name}**  ({count} detected)",expanded=True):
                    ca,cb=st.columns([2,1])
                    with ca:
                        st.markdown(f"""
                        <div style='font-family:Space Mono;font-size:0.75rem;color:#888;margin-bottom:4px'>Recyclability Rate</div>
                        <div class='bar-wrap'><div class='bar-fill' style='width:{pct}%;background:{rc_hex}'></div></div>
                        <span style='color:{rc_hex};font-family:Rajdhani;font-size:1.5rem;font-weight:700'>{pct}%</span>
                        <div style='color:#888;font-size:0.73rem;margin-top:6px'>💡 {tip}</div>
                        """,unsafe_allow_html=True)
                    with cb:
                        st.markdown(f"""
                        <div style='text-align:center;padding:0.8rem;background:#161616;border-radius:6px;border:1px solid #2a2a2a'>
                          <div style='font-family:Rajdhani;font-size:2rem;font-weight:700;color:{rc_hex}'>{count}</div>
                          <div style='font-family:Space Mono;font-size:0.62rem;color:#555'>ITEMS</div>
                          <br>
                          <div style='font-family:Rajdhani;font-size:1.4rem;font-weight:600;color:#aaa'>{avg_conf*100:.1f}%</div>
                          <div style='font-family:Space Mono;font-size:0.62rem;color:#555'>AVG CONF</div>
                        </div>""",unsafe_allow_html=True)

        # ── Summary Report ──
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        if total_dets==0:
            st.markdown("""
            <div class='report-box'>
              <div style='font-family:Rajdhani;font-size:1.1rem;font-weight:700;color:#a855f7;margin-bottom:0.5rem'>
                🔍 No Waste Detected
              </div>
              <div style='font-family:Space Mono;font-size:0.72rem;color:#666;line-height:1.9'>
                Nothing found at current threshold.<br>
                Try lowering the Confidence slider or use a clearer image.
              </div>
            </div>""",unsafe_allow_html=True)
        else:
            rc_emoji="🟢" if rc_score>=0.7 else "🟡" if rc_score>=0.4 else "🔴"
            recyclable=sum(len(v) for k,v in det_counts.items() if RECYCLABILITY.get(k,0)>=0.6)
            non_rec=total_dets-recyclable

            st.markdown(f"""
            <div class='report-box'>
              <div style='font-family:Rajdhani;font-size:1.5rem;font-weight:700;margin-bottom:0.8rem;
                   background:linear-gradient(110deg,#c084fc,#38bdf8);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text'>
                {rc_emoji} Waste Analysis Report
              </div>
              <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:1rem'>
                <div style='background:#111;border:1px solid #2a2a2a;border-radius:8px;padding:0.8rem;text-align:center'>
                  <div style='font-family:Rajdhani;font-size:1.8rem;font-weight:700;color:#a855f7'>{total_dets}</div>
                  <div style='font-family:Space Mono;font-size:0.6rem;color:#555;text-transform:uppercase'>Total Items</div>
                </div>
                <div style='background:#111;border:1px solid #2a2a2a;border-radius:8px;padding:0.8rem;text-align:center'>
                  <div style='font-family:Rajdhani;font-size:1.8rem;font-weight:700;color:{rc_color}'>{rc_score*100:.1f}%</div>
                  <div style='font-family:Space Mono;font-size:0.6rem;color:#555;text-transform:uppercase'>Recyclability</div>
                </div>
                <div style='background:#111;border:1px solid #2a2a2a;border-radius:8px;padding:0.8rem;text-align:center'>
                  <div style='font-family:Rajdhani;font-size:1.8rem;font-weight:700;color:#4ade80'>{recyclable}</div>
                  <div style='font-family:Space Mono;font-size:0.6rem;color:#555;text-transform:uppercase'>Recyclable</div>
                </div>
                <div style='background:#111;border:1px solid #2a2a2a;border-radius:8px;padding:0.8rem;text-align:center'>
                  <div style='font-family:Rajdhani;font-size:1.8rem;font-weight:700;color:#ff4d4d'>{non_rec}</div>
                  <div style='font-family:Space Mono;font-size:0.6rem;color:#555;text-transform:uppercase'>Non-Recyclable</div>
                </div>
              </div>
              <div style='font-family:Space Mono;font-size:0.72rem;color:#555;line-height:1.8;border-top:1px solid #2a2a2a;padding-top:0.8rem'>
                Classes detected: <span class='kw'>{", ".join(det_counts.keys())}</span>
              </div>
            </div>""",unsafe_allow_html=True)

        # ── Download options ──
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.markdown("### 📥 Export Options")
        dc1,dc2=st.columns(2)

        with dc1:
            buf=io.BytesIO()
            Image.fromarray(ann_rgb).save(buf,format="PNG")
            st.download_button(
                label="⬇️ Download Annotated Image",
                data=buf.getvalue(),
                file_name="waste_detection_result.png",
                mime="image/png",
            )

        with dc2:
            report_txt=generate_text_report(
                det_counts, rc_score, total_dets, elapsed*1000, source_label
            )
            st.download_button(
                label="📄 Download Detection Report",
                data=report_txt.encode(),
                file_name="waste_detection_report.txt",
                mime="text/plain",
            )

else:
    st.markdown("""
    <div style='text-align:center;padding:4rem 2rem;background:#111;border:1px dashed #2a2a2a;border-radius:12px'>
      <div style='font-size:3rem;margin-bottom:0.8rem'>♻️</div>
      <div style='font-family:Rajdhani;font-size:1.4rem;font-weight:700;letter-spacing:0.1em;
           background:linear-gradient(110deg,#a855f7,#d4d4d4,#ff073a);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text'>
        Upload an image or use the camera to start scanning
      </div>
      <div style='font-family:Space Mono;font-size:0.72rem;color:#555;margin-top:0.5rem'>
        Supports: JPG · PNG · BMP · WEBP · JFIF
      </div>
    </div>
    """,unsafe_allow_html=True)

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align:center;font-family:Space Mono;font-size:0.68rem;color:#888;padding:0.5rem'>
  AI BASED SMART WASTE SEGREGATION SYSTEM · YOLOv8m · 9 Classes · Built with Streamlit
</div>
""", unsafe_allow_html=True)
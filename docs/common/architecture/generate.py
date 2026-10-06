"""Generate the page-generation architecture diagrams (diagram-design default skin)."""
import math
import sys
import unicodedata
from pathlib import Path

PAPER, INK, MUTED, SOFT, ACCENT, LINK = "#f5f5f5", "#2d3142", "#4f5d75", "#7a8399", "#eb6c36", "#2e5aa8"
SANS = "'Geist', 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
MONO = "'Geist Mono', monospace"
SERIF = "'Instrument Serif', 'Noto Serif KR', serif"
FONTS = ("https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist:wght@400;500;600"
         "&family=Geist+Mono:wght@400;500;600&family=Noto+Sans+KR:wght@400;500;600&family=Noto+Serif+KR:wght@400&display=swap")

KINDS = {  # fill, stroke, dash, tag colour
    "focal": ("rgba(235,108,54,0.08)", ACCENT, None, ACCENT),
    "backend": ("#ffffff", INK, None, INK),
    "store": ("rgba(45,49,66,0.05)", MUTED, None, MUTED),
    "external": ("rgba(45,49,66,0.03)", "rgba(45,49,66,0.30)", None, INK),
    "input": ("rgba(79,93,117,0.10)", SOFT, None, MUTED),
}
STROKES = {"default": (MUTED, "arrow"), "accent": (ACCENT, "arrow-accent"), "link": (LINK, "arrow-link")}


def wide(s):
    return any(unicodedata.east_asian_width(c) in "WF" for c in s)


def tw(s, size, mono=False):
    return sum(size if unicodedata.east_asian_width(c) in "WF" else size * (0.62 if mono else 0.60) for c in s)


def up4(v):
    return int(math.ceil(v / 4.0) * 4)


def up8(v):  # label masks are centred, so half the width must stay on the 4px grid
    return int(math.ceil(v / 8.0) * 8)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=12, weight=None, fill=INK, font=SANS, anchor="middle", extra=""):
    w = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}"{w} font-family="{font}" '
            f'text-anchor="{anchor}"{extra}>{esc(s)}</text>')


def tag(x, y, s, colour):
    w = up4(tw(s, 7, True) + len(s) * 0.56 + 12)
    return (f'<rect x="{x}" y="{y}" width="{w}" height="12" rx="2" fill="transparent" stroke="{colour}" '
            f'stroke-opacity="0.4" stroke-width="0.8"/>'
            + text(x + w / 2, y + 9, s, 7, None, colour, MONO, extra=' fill-opacity="0.8" letter-spacing="0.08em"'))


def box(x, y, w, h, kind, rx=6):
    fill, stroke, dash, _ = KINDS[kind]
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{PAPER}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1"{d}/>')


def node(x, y, w, h, kind, name, sub=None, tg=None, rx=6):
    cx, cy = x + w / 2, y + h / 2
    out = [box(x, y, w, h, kind, rx)]
    shift = 0
    if tg:
        out.append(tag(x + 8, y + 6, tg, KINDS[kind][3]))
        shift = 4 if h >= 64 else 0
    if sub:
        out.append(text(cx, cy + 2 + shift, name, 12, 600))
        out.append(text(cx, cy + 18 + shift, sub, 9, None, MUTED, MONO))
    else:
        out.append(text(cx, cy + 4 + shift, name, 12, 600))
    return "".join(out)


def zone(x, y, w, h, label, dashed=False):
    stroke = 'stroke="rgba(45,49,66,0.20)" stroke-dasharray="4,4"' if dashed else 'stroke="rgba(45,49,66,0.10)"'
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="rgba(45,49,66,0.02)" {stroke} stroke-width="0.8"/>']
    if wide(label):
        lw = up4(tw(label, 12) + 12)
        out.append(f'<rect x="{x + 12}" y="{y + 4}" width="{lw}" height="16" rx="2" fill="{PAPER}"/>')
        out.append(text(x + 12 + lw / 2, y + 16, label, 12, 500, "rgba(45,49,66,0.55)"))
    else:
        lw = up4(tw(label, 7, True) + len(label) * 0.98 + 12)
        out.append(f'<rect x="{x + 12}" y="{y + 4}" width="{lw}" height="12" rx="2" fill="{PAPER}"/>')
        out.append(text(x + 12 + lw / 2, y + 13, label, 7, None, "rgba(45,49,66,0.40)", MONO, extra=' letter-spacing="0.14em"'))
    return "".join(out)


def arrow(pts, kind="default", dashed=False, r=8, marker=True, width=1.2):
    stroke, mk = STROKES[kind]
    d = f"M {pts[0][0]},{pts[0][1]}"
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        sg = lambda v: (v > 0) - (v < 0)
        a = (p1[0] - sg(p1[0] - p0[0]) * r, p1[1] - sg(p1[1] - p0[1]) * r)
        b = (p1[0] + sg(p2[0] - p1[0]) * r, p1[1] + sg(p2[1] - p1[1]) * r)
        d += f" L {a[0]},{a[1]} Q {p1[0]},{p1[1]} {b[0]},{b[1]}"
    d += f" L {pts[-1][0]},{pts[-1][1]}"
    dash = ' stroke-dasharray="5,4"' if dashed else ""
    m = f' marker-end="url(#{mk})"' if marker else ""
    return f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{1 if dashed else width}"{dash}{m}/>'


def _label(s):
    if wide(s):
        return up8(tw(s, 12) + 8), 16, 12, dict(size=12, weight=500, font=SANS, extra="")
    return up8(tw(s, 8, True) + len(s) * 0.48 + 8), 12, 9, dict(size=8, weight=None, font=MONO, extra=' letter-spacing="0.06em"')


def hlabel(cx, line_y, s, below=False, fill=SOFT):
    w, h, base, st = _label(s)
    y = line_y + 8 if below else line_y - 8 - h
    return (f'<rect x="{cx - w / 2}" y="{y}" width="{w}" height="{h}" rx="2" fill="{PAPER}"/>'
            + text(cx, y + base, s, st["size"], st["weight"], fill, st["font"], extra=st["extra"]))


def vlabel(line_x, cy, s, left=False, fill=SOFT):
    w, h, base, st = _label(s)
    x = line_x - 8 - w if left else line_x + 8
    return (f'<rect x="{x}" y="{cy - h / 2}" width="{w}" height="{h}" rx="2" fill="{PAPER}"/>'
            + text(x + w / 2, cy - h / 2 + base, s, st["size"], st["weight"], fill, st["font"], extra=st["extra"]))


def callout(x, y, s, leader, dot, accent=False, anchor="start"):
    col = ACCENT if accent else INK
    lead = "rgba(235,108,54,0.50)" if accent else "rgba(45,49,66,0.40)"
    return (text(x, y, s, 14, None, col, SERIF, anchor, ' font-style="italic"')
            + f'<path d="{leader}" fill="none" stroke="{lead}" stroke-width="1" stroke-dasharray="4,3"/>'
            + f'<circle cx="{dot[0]}" cy="{dot[1]}" r="2" fill="{col}"/>')


def legend(y, width, items):
    out = [f'<line x1="32" y1="{y - 8}" x2="{width - 32}" y2="{y - 8}" stroke="rgba(45,49,66,0.10)" stroke-width="0.8"/>',
           text(32, y + 12, "LEGEND", 8, None, MUTED, MONO, "start", ' letter-spacing="0.14em"')]
    x = 104
    for kind, label in items:
        if kind in KINDS:
            fill, stroke, dash, _ = KINDS[kind]
            out.append(f'<rect x="{x}" y="{y + 4}" width="16" height="12" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        elif kind == "oval":
            out.append(f'<rect x="{x}" y="{y + 4}" width="16" height="12" rx="6" fill="#ffffff" stroke="{INK}" stroke-width="1"/>')
        elif kind == "diamond":
            out.append(f'<polygon points="{x + 8},{y} {x + 16},{y + 8} {x + 8},{y + 16} {x},{y + 8}" fill="#ffffff" stroke="{INK}" stroke-width="1"/>')
        elif kind == "zone":
            out.append(f'<rect x="{x}" y="{y + 4}" width="16" height="12" rx="2" fill="rgba(45,49,66,0.02)" stroke="rgba(45,49,66,0.30)" stroke-width="0.8" stroke-dasharray="3,2"/>')
        elif kind == "chip":
            out.append(f'<rect x="{x}" y="{y + 4}" width="16" height="12" rx="4" fill="rgba(45,49,66,0.05)" stroke="{MUTED}" stroke-width="0.8"/>')
        else:  # line kinds: "default", "link", "accent", optionally "-dash"
            base = kind.replace("-dash", "")
            stroke, mk = STROKES[base]
            dash = ' stroke-dasharray="5,4"' if kind.endswith("-dash") else ""
            out.append(f'<line x1="{x}" y1="{y + 8}" x2="{x + 20}" y2="{y + 8}" stroke="{stroke}" stroke-width="1.2"{dash} marker-end="url(#{mk})"/>')
            x += 8
        out.append(text(x + 24, y + 12, label, 12, None, MUTED, SANS, "start"))
        x += 24 + up4(tw(label, 12)) + 28
    return "".join(out)


def page(slug, eyebrow, title, desc, w, h, body):
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <link href="{FONTS}" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --color-paper: {PAPER}; --color-ink: {INK}; --color-muted: {MUTED}; --color-accent: {ACCENT};
      --font-sans: 'Geist', 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', system-ui, sans-serif;
      --font-serif: 'Instrument Serif', 'Noto Serif KR', serif;
      --font-mono: 'Geist Mono', ui-monospace, monospace;
    }}
    body {{ font-family: var(--font-sans); background: var(--color-paper); color: var(--color-ink);
           min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 3rem 2rem; }}
    .frame {{ max-width: {w}px; width: 100%; }}
    .eyebrow {{ font-family: var(--font-mono); font-size: 0.66rem; font-weight: 500; letter-spacing: 0.18em;
               text-transform: uppercase; color: var(--color-muted); margin-bottom: 0.5rem; }}
    h1 {{ font-family: var(--font-serif); font-size: clamp(1.5rem, 2.4vw + 0.75rem, 2rem); font-weight: 400;
         letter-spacing: -0.02em; line-height: 1.15; color: var(--color-ink); margin-bottom: 1.5rem; }}
    svg {{ width: 100%; min-width: 900px; display: block; }}
  </style>
</head>
<body>
  <div class="frame">
    <p class="eyebrow">{esc(eyebrow)}</p>
    <h1>{esc(title)}</h1>
    <svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{slug}-title {slug}-desc">
      <title id="{slug}-title">{esc(title)}</title>
      <desc id="{slug}-desc">{esc(desc)}</desc>
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{MUTED}"/></marker>
        <marker id="arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{ACCENT}"/></marker>
        <marker id="arrow-link" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{LINK}"/></marker>
      </defs>
      <rect x="0" y="0" width="{w}" height="{h}" fill="{PAPER}"/>
{body}
    </svg>
  </div>
</body>
</html>
"""


def join(*groups):
    return "\n".join("      <g>" + "".join(g) + "</g>" for g in groups)


# ── 1. 시스템 구성 ─────────────────────────────────────────────────────────────
def d_overview():
    W, H = 1120, 552
    zones = [zone(400, 48, 688, 432, "AI CONTAINER · AI-SGLANG"), zone(848, 64, 232, 184, "GPU · L40S 48GB")]
    arrows = [
        arrow([(144, 252), (200, 252)]),
        arrow([(312, 240), (432, 240)], "link"),
        arrow([(432, 264), (312, 264)], "link", dashed=True),
        arrow([(576, 252), (640, 252)]),
        arrow([(784, 228), (808, 228), (808, 124), (864, 124)]),
        arrow([(784, 244), (832, 244), (832, 204), (864, 204)]),
        arrow([(784, 260), (832, 260), (832, 300), (864, 300)]),
        arrow([(784, 276), (808, 276), (808, 380), (864, 380)]),
        arrow([(504, 280), (504, 392)]),
        arrow([(712, 292), (712, 392)]),
    ]
    labels = [
        hlabel(372, 240, "내부 API"),
        hlabel(372, 264, "결과 콜백", below=True),
        vlabel(504, 336, "작업 상태"),
        vlabel(712, 336, "자산 · outbox", left=True),
    ]
    nodes = [
        node(32, 224, 112, 56, "input", "장인 화면", "FE", "USER"),
        node(200, 224, 112, 56, "external", "BE", "Spring Boot", "EXT"),
        node(432, 224, 144, 56, "focal", "AI API", "FastAPI :8000", "API"),
        node(640, 212, 144, 80, "backend", "생성 파이프라인", "one job at a time", "SVC"),
        node(864, 96, 200, 56, "backend", "텍스트 · 비전 모델", "Qwen3.8-27B · :30000", "SGLANG"),
        node(864, 176, 200, 56, "backend", "이미지 생성 모델", "FLUX.2-klein-9B · :30001", "SGLANG"),
        node(864, 272, 200, 56, "backend", "누끼 (배경 제거)", "rembg BiRefNet", "CPU"),
        node(864, 352, 200, 56, "backend", "PNG 렌더러", "HTML/CSS + Playwright", "CPU"),
        node(448, 392, 320, 56, "store", "영속 저장소", "SQLite (jobs · outbox) + SHA-256 files", "DISK"),
    ]
    notes = [
        callout(32, 336, "AI는 BE의 내부 호출만 받는다", "M 148,322 Q 216,316 254,286", (256, 284), accent=True),
        callout(1088, 28, "GPU 한 장을 두 모델이 나눠 쓴다 — 텍스트 서버 기본 50%", "M 900,34 Q 916,46 924,62", (924, 64), anchor="end"),
    ]
    lg = [legend(512, W, [("focal", "연동 지점"), ("backend", "서비스"), ("store", "저장소"), ("external", "외부 시스템"),
                          ("input", "사용자"), ("link", "HTTP 호출"), ("link-dash", "콜백"), ("default", "내부 호출")])]
    return ("01-system-overview", "Architecture · Page Generation", "상세페이지 생성 — 시스템 구성",
            "장인 화면은 BE만 호출하고, BE가 AI API에 작업을 맡기면 생성 파이프라인이 텍스트·이미지 모델 서버와 CPU 누끼·PNG 렌더러를 "
            "차례로 써서 결과를 만들고, 상태와 결과를 디스크에 남긴 뒤 BE로 콜백하는 구성을 보여 준다.",
            W, H, join(zones, arrows, labels, nodes, notes, lg))


# ── 2. 요청 순서 ───────────────────────────────────────────────────────────────
def d_sequence():
    W, H = 1280, 704
    fe, be, ai, md = 136, 392, 656, 904
    top, bottom = 72, 624
    life = [f'<line x1="{x}" y1="{top}" x2="{x}" y2="{bottom}" stroke="rgba(45,49,66,0.20)" stroke-width="1" stroke-dasharray="3,3"/>'
            for x in (fe, be, ai, md)]
    bar = lambda x, y1, y2: f'<rect x="{x - 4}" y="{y1}" width="8" height="{y2 - y1}" fill="rgba(45,49,66,0.06)" stroke="{MUTED}" stroke-width="0.8"/>'
    bars = [bar(ai, 152, 336), bar(ai, 448, 560), bar(md, 232, 272), bar(md, 488, 528)]

    def msg(a, b, y, s, kind="default", dashed=False):
        d = 1 if b > a else -1
        return arrow([(a + 4 * d, y), (b - 4 * d, y)], kind, dashed), hlabel((a + b) / 2, y, s, fill=ACCENT if kind == "accent" else SOFT)

    ms = [
        msg(fe, be, 112, "사진 · 설명 등록"),
        msg(be, ai, 152, "POST JOBS", "link"),
        msg(ai, be, 192, "202 JOB_ID", "link", True),
        msg(ai, md, 232, "사진 분석 · 카피"),
        msg(be, ai, 288, "GET JOB", "link"),
        msg(ai, be, 328, "초안 (DRAFT_READY)", "link", True),
        msg(be, fe, 368, "초안 표시"),
        msg(fe, be, 408, "수정 · 승인"),
        msg(be, ai, 448, "POST RENDERS", "link"),
        msg(ai, md, 488, "연출 컷 생성"),
        msg(ai, be, 552, "결과 콜백 (multipart)", "accent"),
        msg(be, fe, 592, "결과 표시"),
    ]
    actors = [
        node(fe - 80, 24, 160, 48, "input", "장인 화면 (FE)"),
        node(be - 80, 24, 160, 48, "external", "BE"),
        node(ai - 80, 24, 160, 48, "focal", "AI 서비스"),
        node(md - 80, 24, 160, 48, "backend", "모델 서버"),
    ]
    notes = [
        callout(984, 300, "초안 단계 — PNG를 만들지 않는다", "M 980,294 Q 940,286 912,262", (910, 260)),
        callout(984, 540, "렌더 단계 — 분석 모델을 다시 부르지 않는다", "M 980,534 Q 944,528 914,512", (912, 510)),
    ]
    lg = [legend(664, W, [("link", "API 호출"), ("link-dash", "응답"), ("default", "내부 처리 · 화면"), ("accent", "결과 전달")])]
    return ("02-request-sequence", "Sequence · Page Generation", "상세페이지 생성 — 요청 순서",
            "장인이 사진과 설명을 등록하면 BE가 AI에 작업을 접수하고 상태를 조회해 초안을 받으며, 장인이 고치고 승인한 뒤에야 "
            "AI가 연출 컷을 만들고 PNG를 렌더해 BE로 결과를 콜백하는 순서를 보여 준다.",
            W, H, join(life, bars, [a for a, _ in ms], [l for _, l in ms], actors, notes, lg))


# ── 3. 생성 파이프라인 ─────────────────────────────────────────────────────────
def d_pipeline():
    W, H = 1120, 520
    xs = [48, 260, 472, 684, 896]
    zones = [zone(24, 48, 864, 128, "초안 단계"), zone(24, 256, 1076, 144, "승인 후 렌더 단계")]
    row1 = [("QUEUED", "접수 · 원본 저장", "SHA-256 asset store", "backend"),
            ("ANALYZING", "사진 분석 · 카피 초안", "Qwen3.8-27B", "backend"),
            ("EXTRACTING", "쓸 사진 영역 결정", "roles · crop", "backend"),
            ("DRAFT_READY", "초안 조립 · 검증", "draft + react_document", "focal")]
    row2 = [("GENERATING_BACKGROUNDS", "누끼 · 연출 컷 생성", "rembg · FLUX.2-klein-9B", "backend"),
            ("COMPOSING", "원본 + 생성 배경 합성", "Pillow · deterministic", "backend"),
            ("VERIFYING", "원본 보존 검증", "hash · crop · pixels", "backend"),
            ("RENDERING", "섹션 · 전체 PNG 렌더", "HTML/CSS + Playwright", "backend"),
            ("DELIVERING", "BE로 결과 전달", "outbox → callback", "backend")]
    arrows = [arrow([(xs[i] + 180, 120), (xs[i + 1], 120)]) for i in range(3)]
    arrows += [arrow([(xs[i] + 180, 328), (xs[i + 1], 328)]) for i in range(4)]
    arrows.append(arrow([(774, 152), (774, 216), (192, 216), (192, 296)], "accent"))
    labels = [hlabel(484, 216, "장인 확인 · 수정 · 승인", fill=ACCENT),
              text(986, 380, "→ COMPLETED | FAILED", 8, None, MUTED, MONO, extra=' letter-spacing="0.06em"')]
    nodes = [node(xs[i], 88, 180, 64, k, n, s, t) for i, (t, n, s, k) in enumerate(row1)]
    nodes += [node(xs[i], 296, 180, 64, k, n, s, t) for i, (t, n, s, k) in enumerate(row2)]
    notes = [
        callout(1100, 28, "문구만 고쳐 저장할 때는 모델도 PNG도 부르지 않는다", "M 1004,36 Q 1004,188 780,196", (776, 196), accent=True, anchor="end"),
        callout(24, 448, "렌더 단계에서는 분석 모델을 다시 부르지 않는다 — 승인된 초안이 기준", "M 320,428 Q 340,420 354,405", (356, 402)),
    ]
    lg = [legend(480, W, [("backend", "처리 단계 (왼쪽 위 = 작업 상태값)"), ("focal", "장인에게 보이는 초안"), ("accent", "사람의 승인"), ("default", "자동 진행")])]
    return ("03-generation-pipeline", "Pipeline · Page Generation", "상세페이지 생성 — 단계와 상태",
            "작업이 초안 단계의 네 단계(접수, 사진 분석, 사진 영역 결정, 초안 조립)를 거쳐 장인의 확인과 승인을 받은 뒤, "
            "렌더 단계의 다섯 단계(누끼와 연출 컷 생성, 합성, 원본 보존 검증, PNG 렌더, BE 전달)를 지나는 흐름과 단계별 상태값을 보여 준다.",
            W, H, join(zones, arrows, labels, nodes, notes, lg))


# ── 4. 전달 보장 ───────────────────────────────────────────────────────────────
def d_delivery():
    W, H = 960, 552

    def diamond(cx, cy, hw, hh, name, sub):
        pts = f"{cx},{cy - hh} {cx + hw},{cy} {cx},{cy + hh} {cx - hw},{cy}"
        return (f'<polygon points="{pts}" fill="{PAPER}"/><polygon points="{pts}" fill="#ffffff" stroke="{INK}" stroke-width="1"/>'
                + text(cx, cy, name, 12, 600) + text(cx, cy + 16, sub, 8, None, MUTED, MONO))

    arrows = [
        arrow([(480, 72), (480, 104)]),
        arrow([(480, 160), (480, 200)]),
        arrow([(480, 256), (480, 292)]),
        arrow([(480, 372), (480, 428)], "accent"),
        arrow([(584, 332), (688, 332)]),
        arrow([(800, 292), (800, 256)]),
        arrow([(800, 372), (800, 428)]),
        arrow([(680, 228), (600, 228)]),
    ]
    labels = [vlabel(480, 400, "예", fill=ACCENT), hlabel(636, 332, "아니오"), vlabel(800, 276, "예"), vlabel(800, 400, "아니오")]
    nodes = [
        node(400, 32, 160, 40, "backend", "렌더 완료", rx=20),
        node(360, 104, 240, 56, "backend", "결과를 outbox에 먼저 저장", "PENDING · fixed generation_id"),
        node(360, 200, 240, 56, "backend", "BE로 전달", "DELIVERING · lease + heartbeat"),
        diamond(480, 332, 104, 40, "BE가 받았나?", "2xx ack"),
        node(380, 428, 200, 48, "focal", "전달 완료", "DELIVERED → COMPLETED", rx=20),
        diamond(800, 332, 112, 40, "다시 보낼 수 있나?", "retryable · attempts < 8"),
        node(680, 200, 240, 56, "backend", "기다렸다가 다시 전달", "1s → 2s → 4s … 64s"),
        node(700, 428, 200, 48, "backend", "전달 중단", "FAILED · PERMANENT_FAILED", rx=20),
    ]
    notes = [
        callout(24, 128, "재시작해도 outbox에 남아 이어서 보낸다", "M 304,124 Q 332,124 354,131", (356, 132)),
        callout(24, 236, "전달 중 죽으면 lease 만료 뒤 다시 잡는다", "M 320,232 Q 340,232 354,229", (356, 228)),
    ]
    lg = [legend(512, W, [("oval", "시작 · 끝"), ("backend", "처리"), ("diamond", "판단"), ("accent", "정상 경로"), ("default", "그 밖의 경로")])]
    return ("04-delivery-guarantee", "Flowchart · Page Generation", "결과 전달 보장 — outbox와 재시도",
            "렌더가 끝나면 결과를 outbox에 먼저 저장한 뒤 BE로 보내고, BE가 받지 못하면 재시도 가능한 오류이고 시도가 8회 미만일 때 "
            "간격을 늘려 가며 다시 보내며, 그렇지 않으면 전달을 중단하는 판단 흐름을 보여 준다.",
            W, H, join(arrows, labels, nodes, notes, lg))


# ── 5. 배포 구성 ───────────────────────────────────────────────────────────────
def d_deploy():
    W, H = 1160, 552

    def dnode(x, y, w, h, kind, tg, name, sub, chips, replicas=None):
        out = [box(x, y, w, h, kind), tag(x + 8, y + 6, tg, KINDS[kind][3])]
        if replicas:
            out.append(f'<rect x="{x + w - 32}" y="{y + 6}" width="24" height="12" rx="2" fill="{PAPER}" stroke="{MUTED}" stroke-width="0.8"/>')
            out.append(text(x + w - 20, y + 15, replicas, 8, None, MUTED, MONO))
        out.append(text(x + w / 2, y + 36, name, 12, 600))
        out.append(text(x + w / 2, y + 50, sub, 9, None, MUTED, MONO))
        for i, (cn, cv) in enumerate(chips):
            cy = y + 60 + i * 32
            out.append(f'<rect x="{x + 12}" y="{cy}" width="{w - 24}" height="24" rx="4" fill="rgba(45,49,66,0.05)" stroke="{MUTED}" stroke-width="0.8"/>')
            out.append(text(x + 20, cy + 16, cn, 12, None, INK, SANS, "start"))
            out.append(text(x + w - 20, cy + 16, cv, 9, None, MUTED, MONO, "end"))
        return "".join(out)

    zones = [zone(24, 48, 264, 424, "BUILD · GITHUB ACTIONS + ECR", True), zone(336, 48, 800, 424, "EKS STAGE CLUSTER", True)]
    arrows = [
        arrow([(156, 304), (156, 224)]),
        arrow([(264, 176), (360, 176)], "link"),
        arrow([(768, 164), (680, 164)]),
        arrow([(680, 188), (768, 188)], dashed=True),
        arrow([(520, 320), (520, 256)]),
        arrow([(680, 116), (960, 116)]),
    ]
    labels = [vlabel(156, 264, "PUSH"), hlabel(312, 176, "PULL @DIGEST"), hlabel(724, 164, "HTTP:8000"),
              hlabel(724, 188, "CALLBACK", below=True), vlabel(520, 288, "MOUNT"), hlabel(820, 116, "METRICS · LOGS")]
    nodes = [
        dnode(48, 128, 216, 96, "store", "MANAGED", "ECR", "jangin-ai/page-generation", [("이미지", "immutable SHA tag")]),
        dnode(48, 304, 216, 128, "backend", "CI", "GenAI CI", "GitHub Actions", [("테스트", "536 passed"), ("이미지 빌드", "docker buildx")]),
        dnode(360, 96, 320, 160, "focal", "POD", "ai-sglang", "g6e.xlarge · L40S 48GB · limit 24Gi",
              [("AI API", "FastAPI :8000"), ("텍스트 서버", "SGLang :30000"), ("이미지 서버", "SGLang :30001")], "x1"),
        dnode(360, 320, 320, 128, "store", "PVC", "모델 볼륨", "synced from S3",
              [("Qwen3.8-27B", "AWQ-INT4"), ("FLUX.2-klein-9B", "bnb-4bit")]),
        node(768, 148, 120, 56, "external", "BE", "backend", "POD"),
        dnode(960, 96, 160, 160, "external", "SVC", "관측 스택", "run by infra team",
              [("Prometheus", "scrape"), ("Loki", "logs"), ("Grafana", "DCGM GPU")]),
    ]
    notes = [
        callout(24, 28, "digest는 인프라 팀이 매니페스트에 반영한다", "M 222,36 Q 230,84 221,124", (220, 126), accent=True),
        callout(400, 28, "상태가 파드 디스크에 있어 파드는 하나만 띄운다", "M 560,36 Q 566,64 561,92", (560, 94)),
    ]
    lg = [legend(512, W, [("zone", "환경 경계"), ("focal", "AI 파드"), ("chip", "올라가는 구성 요소"),
                          ("link", "경계를 넘는 경로"), ("default", "클러스터 안"), ("default-dash", "비동기 콜백")])]
    return ("05-deployment", "Deployment · Page Generation", "상세페이지 생성 — 배포 구성 (Stage)",
            "GenAI CI가 테스트와 이미지 빌드를 거쳐 ECR에 이미지를 올리고, EKS Stage의 ai-sglang 파드 하나가 그 이미지를 받아 "
            "AI API와 텍스트·이미지 모델 서버를 함께 띄우며, 모델은 PVC에서 읽고 BE와는 HTTP로 통신하며 지표와 로그는 같은 클러스터의 관측 스택이 수집하는 배치를 보여 준다.",
            W, H, join(zones, arrows, labels, nodes, notes, lg))


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for fn in (d_overview, d_sequence, d_pipeline, d_delivery, d_deploy):
        slug, eyebrow, title, desc, w, h, body = fn()
        (out / f"{slug}.html").write_text(page(slug, eyebrow, title, desc, w, h, body), encoding="utf-8")
        print(slug, w, h)

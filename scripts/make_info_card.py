"""
Build a neofetch-style info card SVG (Andrew6rant style) to sit to the RIGHT of
the ASCII portrait: colored key/value rows for work experience, tech stack, and
highlights -- NOT GitHub stats (the contribution graph covers those).

Static content, hand-authored below. Lines fade/slide in on a short stagger so
it feels like the panel is printing alongside the portrait. STATIC=1 emits the
frozen state for Quick Look previews.
"""
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "info-card.svg")
STATIC = os.environ.get("STATIC", "").lower() in ("1", "true", "yes")

W = 480
PAD = 20
TITLEBAR_H = 30
KEY_X = PAD
VAL_X = PAD + 92
LINE_H = 20.5

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
MUTED = "#7d8590"
INK = "#c9d1d9"
KEY = "#ffa657"      # orange keys (matches Andrew)
SECTION = "#58a6ff"  # blue section headers
GREEN = "#3fb950"
ACCENT = "#22d3ee"

# content model: tuples describing each row
# ("host",)                    -> "aadish@github" + rule
# ("kv", key, value)           -> orange key + light value
# ("sec", title)               -> blue "— title —" rule
# ("bul", text)                -> green dot + light text
# ("gap",)                     -> vertical space
ROWS = [
    ("host",),
    ("kv", "Now", "CSE Student @ SRM IST"),
    ("kv", "Prev", "Technical Team Member @ Dbugs Lab"),
    ("kv", "Also", "AI/ML Enthusiast • Full-Stack Developer"),
    ("kv", "Edu", "B.Tech CSE (CGPA 9.21) • SRM '27"),
    ("gap",),
    ("sec", "Stack"),
    ("kv", "Languages", "Python, C++, JavaScript, SQL"),
    ("kv", "Frontend", "React.js, Next.js, HTML, CSS"),
    ("kv", "Backend", "Node.js, Express.js, FastAPI"),
    ("kv", "AI / ML", "LangGraph, Scikit-learn, Pandas,"),
    ("kv", "", "NumPy, Deep Learning, ChromaDB"),
    ("kv", "Cloud", "AWS EC2, ECR, Docker, Kubernetes,"),
    ("kv", "", "MongoDB Atlas, GitHub Actions"),
    ("gap",),
    ("sec", "Projects"),
    ("kv", "Athena", "Multi-Agent Academic Assistant"),
    ("kv", "", "5-agent AI workflow using LangGraph"),
    ("kv", "StayEase", "Full-Stack Property Rental Platform"),
    ("kv", "", "AWS-deployed MVC architecture"),
    ("gap",),
    ("sec", "Achievements"),
    ("bul", "Rank 42, SRMJEEE (All India)"),
    ("bul", "Champion Tier, Google Arcade"),
    ("bul", "Top Performer, COSC HackWeek 2025"),
    ("gap",),
    ("sec", "Certifications"),
    ("kv", "AI-300", "Microsoft Certified:"),
    ("kv", "", "Machine Learning Operations Engineer"),
    ("kv", "NPTEL", "Introduction to Machine Learning"),
    ("kv", "GitHub", "GitHub Actions Certified"),
]


def esc(s):
    return html.escape(s)


def rise(inner, i):
    """fade + slight upward slide, staggered by row index; freezes visible."""
    if STATIC:
        return f"<g>{inner}</g>"
    delay = 0.15 + i * 0.06
    return (f'<g opacity="0" transform="translate(0,5)">{inner}'
            f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" dur="0.4s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" from="0 5" to="0 0" '
            f'begin="{delay:.2f}s" dur="0.4s" fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/></g>')


def build_svg():
    # Calculate height dynamically from content
    y = TITLEBAR_H + 30
    for row in ROWS:
        kind = row[0]
        if kind == "gap":
            y += LINE_H * 0.5
        else:
            y += LINE_H
    H = int(y + PAD + 10)  # add bottom padding

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        '<defs>'
        f'<linearGradient id="ibg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
        f'<rect width="{W}" height="{H}" rx="12" fill="url(#ibg)"/>',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{FRAME}"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
    ]
    for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
    parts.append(f'<text x="{W/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12" '
                 f'text-anchor="middle">aadish@github: ~$ neofetch</text>')

    y = TITLEBAR_H + 30
    for i, row in enumerate(ROWS):
        kind = row[0]
        if kind == "gap":
            y += LINE_H * 0.5
            continue
        if kind == "host":
            inner = (f'<text x="{KEY_X}" y="{y:.1f}" font-size="14" font-weight="700">'
                     f'<tspan fill="{GREEN}">aadish</tspan><tspan fill="{MUTED}">@</tspan>'
                     f'<tspan fill="{ACCENT}">github</tspan></text>'
                     f'<line x1="{KEY_X+120}" y1="{y-4:.1f}" x2="{W-PAD}" y2="{y-4:.1f}" '
                     f'stroke="{FRAME}" stroke-opacity="0.8"/>')
        elif kind == "sec":
            title = esc(row[1])
            inner = (f'<text x="{KEY_X}" y="{y:.1f}" fill="{SECTION}" font-size="12.5" font-weight="700">'
                     f'&#8212; {title}</text>'
                     f'<line x1="{KEY_X + 12 + len(row[1])*8}" y1="{y-4:.1f}" x2="{W-PAD}" y2="{y-4:.1f}" '
                     f'stroke="{FRAME}" stroke-opacity="0.8"/>')
        elif kind == "kv":
            key, val = esc(row[1]), esc(row[2])
            # Skip empty key text element for continuation rows
            if key:
                inner = (f'<text x="{KEY_X}" y="{y:.1f}" fill="{KEY}" font-size="12.5" font-weight="700">{key}</text>'
                         f'<text x="{VAL_X}" y="{y:.1f}" fill="{INK}" font-size="12.5">{val}</text>')
            else:
                inner = f'<text x="{VAL_X}" y="{y:.1f}" fill="{INK}" font-size="12.5">{val}</text>'
        elif kind == "bul":
            txt = esc(row[1])
            inner = (f'<circle cx="{KEY_X+3}" cy="{y-4:.1f}" r="2.5" fill="{GREEN}"/>'
                     f'<text x="{KEY_X+14}" y="{y:.1f}" fill="{INK}" font-size="12.5">{txt}</text>')
        else:
            continue
        parts.append(rise(inner, i))
        y += LINE_H

    parts.append("</svg>")
    return "".join(parts), W, H, round(y)


if __name__ == "__main__":
    svg, w, h, content_bottom = build_svg()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", OUT, len(svg), "bytes;", w, "x", h, "content_bottom", content_bottom)

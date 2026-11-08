"""
Convert a portrait photo into a CLEAN, monochrome ASCII-art SVG (Andrew6rant
style: one light-gray color, subject isolated on a dark background) that "types"
itself in like a terminal, then holds.

Monochrome is deliberate -- per-character rainbow color is what makes ASCII
portraits look noisy. One fill color + a good density ramp + high contrast
reads as neat and legible.

Tone mapping is POSITIVE: light ink on a dark terminal means a bright pixel
must become a dense glyph. The background is blanked using the subject mask
(alpha channel written by prep_photo.py), not by brightness, so it can't fight
the tone mapping. Brightness is stretched over the subject's own histogram so
the face spans the whole ramp and dark features (glasses, eyes, hairline) stay
sparse instead of drowning in dense glyphs.

GitHub renders SVGs embedded via <img> and runs their SMIL animations there (JS
does not run). Each row is revealed with a left-to-right clip wipe plus a small
block cursor riding the wipe edge, staggered top -> bottom, so the whole
portrait prints once and freezes.
"""
from PIL import Image
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Configuration
USERNAME = "aadish"
DISPLAY_NAME = "Aadish Jain"

# defaults to the prepped grayscale+alpha image (see prep_photo.py)
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-prepped.png")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "aadish-ascii.svg")

COLS = 110           # rows are derived from the image aspect ratio
CELL_W = 3.4        # tiny cells: the card is built at the info card's scale so their
CELL_H = 6.375      # title bars match side by side (keeps the 8:15 glyph ratio)
# sparse -> dense. index 0 (space) is reserved for background.
RAMP = " .:-=+*#%@"   # perceptually even density steps

GAMMA = 1.15         # >1 spreads the highlights so a bright face keeps detail
STRETCH = (2, 98)    # percentile black/white points, measured on the subject only
MIN_INK = 1          # every subject cell gets at least RAMP[MIN_INK] -> solid silhouette
MASK_CUTOFF = 0.5    # alpha below this is background

PAD = 20
TITLEBAR_H = 30
STATUS_H = 30

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"      # the single ascii color
INK_HI = "#e6edf3"   # brighter tone for the densest glyphs (subtle depth)
CURSOR = "#c9d1d9"

# ---- reveal timing (one-shot; a cursor rasters top -> bottom) -------------
ROW_DUR = 0.06
STAGGER = 0.06       # == ROW_DUR -> a single cursor sweeping down

STATIC = os.environ.get("STATIC", "").lower() in ("1", "true", "yes")


def sample(src):
    """Return list of ROWS strings of COLS glyphs."""
    im = Image.open(src)
    has_alpha = im.mode in ("LA", "RGBA") or "transparency" in im.info
    if has_alpha:
        im = im.convert("LA")
        gray, alpha = im.split()
    else:
        # legacy prepped image: background composited to white
        gray = im.convert("L")
        alpha = gray.point(lambda v: 0 if v >= 245 else 255)

    rows = max(1, round(COLS * gray.height / gray.width * CELL_W / CELL_H))

    g = gray.resize((COLS, rows), Image.Resampling.LANCZOS).load()
    a = alpha.resize((COLS, rows), Image.Resampling.BOX).load()

    # black/white points from the SUBJECT's own histogram, so the face uses the
    # whole ramp instead of piling up at the dense end
    vals = sorted(g[x, y] for y in range(rows) for x in range(COLS)
                  if a[x, y] / 255.0 >= MASK_CUTOFF) or [0, 255]
    lo = vals[int(len(vals) * STRETCH[0] / 100)]
    hi = vals[min(len(vals) - 1, int(len(vals) * STRETCH[1] / 100))]
    span = max(1, hi - lo)

    top = len(RAMP) - 1
    out = []
    for y in range(rows):
        chars = []
        for x in range(COLS):
            if a[x, y] / 255.0 < MASK_CUTOFF:
                chars.append(" ")
                continue
            d = pow(min(1.0, max(0.0, (g[x, y] - lo) / span)), GAMMA)
            idx = MIN_INK + int(d * (top - MIN_INK) + 0.5)
            chars.append(RAMP[max(MIN_INK, min(top, idx))])
        out.append("".join(chars))

    # drop fully blank rows at top/bottom so the art sits snugly in the frame
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def build_svg():
    if not os.path.isfile(SRC):
        print(f"error: source image not found: {SRC}", file=sys.stderr)
        print("run prep_photo.py first, or pass the image path as argv[1]", file=sys.stderr)
        sys.exit(1)

    rows_txt = sample(SRC)
    rows = len(rows_txt)
    art_w = COLS * CELL_W
    art_h = rows * CELL_H
    canvas_w = art_w + PAD * 2
    art_top = TITLEBAR_H + PAD * 0.6
    canvas_h = int(art_top + art_h + PAD * 0.6 + STATUS_H + PAD * 0.4)

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w} {canvas_h}" font-family="ui-monospace, SFMono-Regular, '
        f'Menlo, Consolas, monospace">'
    )
    parts.append('<defs>'
                 f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
                 f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
                 f'</linearGradient>'
                 # soft vignette behind the subject so it doesn't sit on a flat slab
                 f'<radialGradient id="glow" cx="0.5" cy="0.42" r="0.6">'
                 f'<stop offset="0" stop-color="#58a6ff" stop-opacity="0.07"/>'
                 f'<stop offset="1" stop-color="#58a6ff" stop-opacity="0"/>'
                 f'</radialGradient></defs>')

    parts.append(f'<rect width="{canvas_w}" height="{canvas_h}" rx="12" fill="url(#bg)"/>')
    parts.append(f'<rect x="0" y="{TITLEBAR_H}" width="{canvas_w}" height="{art_h + PAD:.0f}" fill="url(#glow)"/>')
    parts.append(f'<rect x="0.5" y="0.5" width="{canvas_w-1}" height="{canvas_h-1}" rx="12" '
                 f'fill="none" stroke="{FRAME}" stroke-width="1"/>')

    parts.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{canvas_w}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>')
    for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
    parts.append(f'<text x="{canvas_w/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
                 f'text-anchor="middle">{USERNAME}@github: ~$ ./portrait.sh</text>')

    # one <text> per row; the densest glyphs get a slightly brighter tone via
    # tspans so highlights pop without breaking the monochrome look
    dense = set(RAMP[-3:])
    font_size = CELL_H * 0.86
    for ry, line in enumerate(rows_txt):
        y = art_top + ry * CELL_H + CELL_H * 0.74
        row_y = art_top + ry * CELL_H
        delay = ry * STAGGER

        segs, cur, cur_hi = [], "", None
        for ch in line:
            hi = ch in dense
            if cur and hi != cur_hi:
                segs.append((cur, cur_hi))
                cur = ""
            cur += ch
            cur_hi = hi
        if cur:
            segs.append((cur, cur_hi))
        body = "".join(f'<tspan fill="{INK_HI}" font-weight="700">{html.escape(s)}</tspan>' if hi
                       else html.escape(s) for s, hi in segs)

        text = (f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" '
                f'font-size="{font_size:.1f}" textLength="{art_w}" lengthAdjust="spacing">{body}</text>')

        if STATIC:
            parts.append(text)
            continue

        parts.append(
            f'<clipPath id="r{ry}"><rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}" width="0">'
            f'<animate attributeName="width" from="0" to="{art_w}" begin="{delay:.3f}s" '
            f'dur="{ROW_DUR:.2f}s" fill="freeze"/></rect></clipPath>'
        )
        parts.append(f'<g clip-path="url(#r{ry})">{text}</g>')
        parts.append(
            f'<rect y="{row_y+1:.1f}" width="{CELL_W}" height="{CELL_H-2}" fill="{CURSOR}" opacity="0">'
            f'<animate attributeName="x" from="{PAD}" to="{PAD+art_w}" begin="{delay:.3f}s" '
            f'dur="{ROW_DUR:.2f}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
            f'<set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/></rect>'
        )

    # status bar with a steady blinking cursor
    status_line_y = art_top + art_h + PAD * 0.6
    status_y = status_line_y + 20
    status_text = f"{USERNAME}@github:~$ whoami "
    # Pin the status line to an exact width with textLength (like the art rows)
    # so the cursor lands right after the name whatever monospace font renders.
    char_w = 7.8   # nominal advance of a 13px monospace glyph (0.6em)
    status_w = (len(status_text) + len(DISPLAY_NAME)) * char_w
    cursor_x = PAD + status_w + 2
    parts.append(f'<line x1="0" y1="{status_line_y:.1f}" x2="{canvas_w}" y2="{status_line_y:.1f}" stroke="{FRAME}"/>')
    parts.append(f'<text xml:space="preserve" x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13" '
                 f'textLength="{status_w:.1f}" lengthAdjust="spacingAndGlyphs">'
                 f'{html.escape(status_text)}<tspan fill="{INK}">{html.escape(DISPLAY_NAME)}</tspan></text>')
    parts.append(f'<rect x="{cursor_x:.1f}" y="{status_y-12:.1f}" width="8" height="14" fill="{INK}">'
                 f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
                 f'dur="1s" repeatCount="indefinite"/></rect>')

    parts.append("</svg>")
    return "".join(parts), canvas_w, canvas_h


if __name__ == "__main__":
    svg, w, h = build_svg()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", OUT, len(svg), "bytes;", w, "x", h)

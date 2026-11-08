"""
Prepare a portrait photo for clean ASCII conversion:
  1. remove the background (rembg) so the subject is isolated
  2. crop to a 3:4 head-and-shoulders frame centred on the subject, so the
     face fills the card instead of floating in empty space
  3. boost LOCAL contrast (CLAHE) so a flatly-lit face gains highlights and
     shadows -- this is what turns a dark blob into a recognizable face

Output: source-prepped.png -- grayscale + ALPHA (mode "LA"). The alpha channel
is the subject mask; make_ascii_svg.py uses it to blank the background, which
frees the luminance to map the right way round (bright skin -> dense, bright
glyphs on the dark terminal) instead of the photo-negative look you get when
"white background -> blank" forces bright -> sparse.

Run once whenever the source photo changes; the ascii SVG itself is static.

    python scripts/prep_photo.py [input.jpg] [output.png]
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import remove

HERE = os.path.dirname(os.path.abspath(__file__))

ASPECT = 0.65          # output width / height -- tall enough to match the info card
HEAD_ROOM = 0.05        # fraction of crop height kept above the top of the head
ZOOM = 0.7              # crop width as a fraction of the subject's width:
                        # <1 trims the shoulders so the face fills more cells


def subject_crop(alpha):
    """ASPECT head-and-shoulders box, top anchored just above the head."""
    h, w = alpha.shape
    ys, xs = np.nonzero(alpha > 40)
    if len(xs) == 0:
        return 0, 0, w, h
    top, bottom = ys.min(), ys.max()

    # centre horizontally on the head (top 20% of the subject), not the whole
    # silhouette -- shoulders/arms would pull it off-centre
    head_rows = alpha[top: top + max(1, int((bottom - top) * 0.2))] > 40
    head_xs = np.nonzero(head_rows.any(axis=0))[0]
    cx = int((head_xs.min() + head_xs.max()) / 2) if len(head_xs) else int(xs.mean())

    crop_w = min(w, int((xs.max() - xs.min()) * ZOOM))
    crop_h = int(crop_w / ASPECT)
    if crop_h > h:
        crop_h = h
        crop_w = int(crop_h * ASPECT)

    y0 = max(0, top - int(crop_h * HEAD_ROOM))
    y0 = min(y0, h - crop_h)
    x0 = min(max(0, cx - crop_w // 2), w - crop_w)
    return x0, y0, x0 + crop_w, y0 + crop_h


def prep_photo(inp, out):
    if not os.path.isfile(inp):
        print(f"error: input image not found: {inp}", file=sys.stderr)
        sys.exit(1)

    # 1. cut out the subject
    cut = remove(Image.open(inp).convert("RGBA"))
    rgb = np.array(cut.convert("RGB"))
    alpha = np.array(cut.split()[-1])                 # 0 = background

    # 2. crop to the subject
    x0, y0, x1, y1 = subject_crop(alpha)
    rgb, alpha = rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1]

    # 3. local-contrast the luminance (CLAHE); clipLimit = strength per tile
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.4, tileGridSize=(6, 6))
    gray = clahe.apply(gray)

    # soften the mask edge slightly so the silhouette doesn't stair-step
    alpha = cv2.GaussianBlur(alpha, (0, 0), 1.0)

    Image.fromarray(np.dstack([gray, alpha]), mode="LA").save(out)
    print("wrote", out, gray.shape[::-1], "crop", (x0, y0, x1, y1))


if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.jpg")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-prepped.png")
    prep_photo(inp, out)

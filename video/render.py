# Dibuja los cuadros del video (540x960, 24 fps) con PIL. Uso: python3 render.py [cuadro_inicial cuadro_final]
import os, sys, math, json, colorsys, random, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import multiprocessing as mp
import tl
from tl import *

W, H, FPS = 540, 960, 24
SS = int(os.environ.get('SS', '2'))
FR = WD + '/frames'; os.makedirs(FR, exist_ok=True)
HANDLE = '@cuenta_de_el_memmes'
NF = int(round(DURATION * FPS))
HOR = 265
R1 = dict(x=140, base=455, h=215, th=0)
R2 = dict(x=395, base=385, h=185, th=1)
GATE = (270, 585)
GU = 16.0

_FP = next(p for p in ['/system/fonts/DroidSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if os.path.exists(p))
@functools.lru_cache(None)
def F(sz): return ImageFont.truetype(_FP, max(6, int(round(sz))))

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, k): return a + (b - a) * k
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return 3 * x * x - 2 * x ** 3
def back(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def hsl(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l, s); return (int(r * 255), int(g * 255), int(b * 255))
def unit(y): return 8 + (y - HOR) * 0.032

class Cv:
    def __init__(s, base=None):
        s.im = base.copy() if base is not None else Image.new('RGB', (W * SS, H * SS), (0, 0, 0))
        s.d = ImageDraw.Draw(s.im, 'RGBA')
    def rect(s, x0, y0, x1, y1, fill=None, outline=None, w=1):
        s.d.rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=fill, outline=outline, width=max(1, int(w * SS)))
    def rw(s, x, y, w, h, r, fill=None, outline=None, ow=1):
        if w <= 0 or h <= 0: return
        s.d.rounded_rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], radius=max(0, r * SS), fill=fill, outline=outline, width=max(1, int(ow * SS)))
    def ell(s, cx, cy, rx, ry, fill=None, outline=None, w=1):
        if rx <= 0 or ry <= 0: return
        s.d.ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], fill=fill, outline=outline, width=max(1, int(w * SS)))
    def poly(s, pts, fill):
        s.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)
    def line(s, pts, fill, w=1):
        s.d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=max(1, int(w * SS)), joint='curve')
    def arc(s, cx, cy, rx, ry, a0, a1, fill, w=1):
        s.d.arc([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], a0, a1, fill=fill, width=max(1, int(w * SS)))
    def text(s, x, y, t, size, fill=(255, 255, 255), anchor='mm', stroke=0, sfill=(0, 0, 0)):
        s.d.text((x * SS, y * SS), t, font=F(size * SS), fill=fill, anchor=anchor, stroke_width=int(stroke * SS), stroke_fill=sfill)
    def tw(s, t, size): return F(size * SS).getlength(t) / SS
    def glow(s, cx, cy, r, col, a=0.5):
        m = _glow_mask(int(r * SS)).point(lambda v: int(v * a))
        s.im.paste(Image.new('RGB', m.size, col), (int(cx * SS - m.size[0] / 2), int(cy * SS - m.size[1] / 2)), m)
    def check(s, cx, cy, r, col=(255, 255, 255), w=3):
        s.line([(cx - r * 0.5, cy), (cx - r * 0.1, cy + r * 0.4), (cx + r * 0.55, cy - r * 0.4)], col, w)

@functools.lru_cache(None)
def _glow_mask(r):
    r = max(4, r); n = 2 * r
    yy, xx = np.mgrid[-r:r, -r:r]
    d = np.sqrt(xx * xx + yy * yy) / r
    a = np.clip(1 - d, 0, 1) ** 2 * 255
    return Image.fromarray(a.astype(np.uint8), 'L')

def vgrad_img(w, h, stops):
    ys = np.linspace(0, 1, h)
    col = np.stack([np.interp(ys, [p for p, _ in stops], [c[i] for _, c in stops]) for i in range(3)], axis=1)
    return Image.fromarray(np.repeat(col[:, None, :], w, axis=1).astype(np.uint8), 'RGB')

# ---------------------------------------------------------------- fondos con caché
_rnd = random.Random(5)
STARS = [(_rnd.random() * W, _rnd.random() * (HOR + 10), 0.6 + _rnd.random() * 1.6, _rnd.random() * 6.28) for _ in range(90)]
MOUNT = [(i * W / 12.0, HOR - (14 + _rnd.random() * 40)) for i in range(13)]
MOUNT2 = [(i * W / 12.0, HOR - (4 + _rnd.random() * 24)) for i in range(13)]
_sx = -4; SKY = []
while _sx < W:
    bw = 12 + _rnd.random() * 24; bh = 10 + _rnd.random() * 40
    SKY.append((_sx, bw, bh, _rnd.random() < 0.25)); _sx += bw + 1 + _rnd.random() * 3

_BG = {}
def world_bg():
    if 'w' in _BG: return _BG['w']
    top = vgrad_img(W * SS, HOR * SS, [(0, (4, 6, 26)), (0.55, (20, 32, 90)), (1, (90, 58, 140))])
    bot = vgrad_img(W * SS, (H - HOR) * SS, [(0, (42, 50, 112)), (0.35, (26, 33, 88)), (1, (11, 15, 48))])
    im = Image.new('RGB', (W * SS, H * SS)); im.paste(top, (0, 0)); im.paste(bot, (0, HOR * SS))
    c = Cv(im)
    c.glow(190, 120, 230, (120, 70, 200), 0.45); c.glow(470, 80, 200, (60, 170, 220), 0.35); c.glow(40, 220, 170, (220, 80, 160), 0.3)
    c.poly([(0, HOR + 1)] + MOUNT + [(W, HOR + 1)], (42, 47, 107)); c.poly([(0, HOR + 1)] + MOUNT2 + [(W, HOR + 1)], (28, 33, 80))
    for (x, bw, bh, ant) in SKY:
        c.rect(x, HOR - bh, x + bw, HOR + 1, fill=(20, 25, 65)); c.rect(x, HOR - bh, x + bw * 0.35, HOR + 1, fill=(29, 35, 88))
        for wy in range(4, int(bh) - 3, 7):
            for wx in range(3, int(bw) - 3, 6):
                if (int(x) * 7 + wx * 13 + wy * 5) % 9 < 5: c.rect(x + wx, HOR - bh + wy, x + wx + 2, HOR - bh + wy + 3, fill=(255, 226, 130, 200))
        if ant: c.line([(x + bw / 2, HOR - bh), (x + bw / 2, HOR - bh - 11)], (58, 68, 134), 1)
    for kx in range(-14, 15):
        c.line([(W / 2 + kx * 4, HOR), (W / 2 + kx * W * 0.2, H)], (140, 160, 255, 34), 1)
    # planeta con anillo
    px, py, pr = 440, 205, 38
    c.arc(px, py, pr * 1.9, pr * 0.5, 180, 360, (230, 190, 140, 150), 5)
    c.ell(px, py, pr, pr, fill=(217, 138, 78)); c.ell(px - pr * 0.25, py - pr * 0.25, pr * 0.6, pr * 0.6, fill=(255, 217, 160, 150))
    c.ell(px, py + pr * 0.12, pr, pr * 0.15, fill=(120, 60, 50, 70))
    c.arc(px, py, pr * 1.9, pr * 0.5, 0, 180, (240, 200, 150, 190), 5)
    c.ell(70, 130, 22, 22, fill=(255, 246, 214))
    c.glow(70, 130, 70, (255, 245, 210), 0.4)
    hg = vgrad_img(W * SS, 70 * SS, [(0, (0, 0, 0)), (0.55, (80, 60, 130)), (1, (0, 0, 0))])
    c.im.paste(hg.point(lambda v: v), (0, (HOR - 40) * SS), hg.convert('L').point(lambda v: min(255, v * 2)))
    _BG['w'] = c.im
    return c.im

def world_dyn(c, gt):
    for (x, y, r, p) in STARS:
        a = 0.35 + 0.65 * abs(math.sin(gt * 1.3 + p))
        c.ell(x, y, r, r, fill=(255, 255, 255, int(255 * a)))
    off = (gt * 0.12) % 1
    for j in range(12):
        tt = (j + off) / 12.0; yy = HOR + (H - HOR) * tt * tt
        c.line([(0, yy), (W, yy)], (140, 160, 255, int(30 + 60 * tt)), 1)

# ---------------------------------------------------------------- piezas dibujadas
def pad(c, x, y, rx):
    ry = rx * 0.26; th = ry * 0.9
    c.ell(x + 6, y + th + 4, rx * 1.05, ry * 1.05, fill=(0, 0, 0, 90))
    c.ell(x, y + th, rx, ry, fill=(58, 68, 112)); c.rect(x - rx, y, x + rx, y + th, fill=(98, 110, 170)); c.ell(x, y + th, rx, ry, fill=(58, 68, 112))
    c.rect(x - rx, y, x - rx * 0.55, y + th, fill=(78, 90, 145)); c.ell(x, y, rx, ry, fill=(150, 162, 220)); c.ell(x - rx * 0.2, y - ry * 0.15, rx * 0.6, ry * 0.55, fill=(176, 186, 235, 120))
    c.ell(x, y, rx * 0.72, ry * 0.72, outline=(255, 255, 255, 90), w=1.2)

def tower(c, x, base, h):
    tw = h * 0.07
    c.line([(x, base), (x, base - h)], (74, 86, 144), 2); c.line([(x + tw, base), (x + tw, base - h)], (74, 86, 144), 2)
    n = 9
    for i in range(n):
        y0 = base - h * i / n; y1 = base - h * (i + 1) / n
        c.line([(x, y0), (x + tw, y1)], (74, 86, 144), 1); c.line([(x + tw, y0), (x, y1)], (74, 86, 144), 1); c.line([(x, y1), (x + tw, y1)], (74, 86, 144), 1)
    c.ell(x + tw / 2, base - h - 4, 3, 3, fill=(255, 77, 94))

THEMES = [
    dict(nose=(214, 48, 70), noseL=(255, 96, 112), fin=(176, 32, 52), finL=(212, 51, 71)),
    dict(nose=(48, 80, 217), noseL=(96, 136, 255), fin=(32, 58, 176), finL=(51, 88, 212)),
]
def bez(p0, c, p1, n=14):
    return [((1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * c[0] + s * s * p1[0], (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * c[1] + s * s * p1[1]) for s in [i / n for i in range(n + 1)]]

def flame(c, x, y, ln, wd, t):
    f = 0.85 + 0.15 * math.sin(t * 60) + 0.1 * math.sin(t * 37)
    ln *= f
    c.glow(x, y + ln * 0.25, wd * 4.5, (255, 150, 60), 0.55)
    c.poly([(x - wd, y), (x - wd * 0.7, y + ln * 0.55), (x, y + ln), (x + wd * 0.7, y + ln * 0.55), (x + wd, y)], (255, 110, 30, 220))
    c.poly([(x - wd * 0.62, y), (x - wd * 0.4, y + ln * 0.5), (x, y + ln * 0.8), (x + wd * 0.4, y + ln * 0.5), (x + wd * 0.62, y)], (255, 210, 70, 235))
    c.poly([(x - wd * 0.3, y), (x, y + ln * 0.55), (x + wd * 0.3, y)], (255, 255, 235, 245))

def rocket(c, x, base, h, th=0, fl=0.0, t=0.0, windows=(), num=None):
    T = THEMES[th % len(THEMES)]
    w = h * 0.32; bw = w / 2; nozH = h * 0.07; noseH = h * 0.28
    yb = base - nozH; yTop = base - h; yn = yTop + noseH
    if fl > 0: flame(c, x, base - 2, h * fl, bw * 0.62, t)
    for sd, col in ((-1, T['fin']), (1, T['finL'])):
        sx = x + sd * bw
        c.poly(bez((sx, yb - h * 0.30), (sx + sd * bw * 0.95, yb - h * 0.12), (sx + sd * bw * 1.0, base + h * 0.01)) + [(sx, yb + 2)], col)
    c.poly([(x - bw * 0.55, yb - 2), (x - bw * 0.7, base), (x + bw * 0.7, base), (x + bw * 0.55, yb - 2)], (130, 140, 175))
    L = bez((x - bw, yn), (x - bw, yTop + noseH * 0.18), (x, yTop)); R = bez((x, yTop), (x + bw, yTop + noseH * 0.18), (x + bw, yn))
    body = [(x - bw, yb)] + L + R + [(x + bw, yb)] + bez((x + bw, yb), (x, yb + bw * 0.28), (x - bw, yb))
    c.poly(body, (220, 227, 244))
    c.poly([(max(px, x + bw * 0.25), py) for px, py in body], (141, 153, 192))
    c.poly([(min(px, x - bw * 0.55), py) for px, py in body if px < x - bw * 0.2 or py > yn] , (255, 255, 255, 0))
    cut = yTop + noseH * 0.72
    nz = [p for p in L if p[1] <= cut] + [p for p in R if p[1] <= cut]
    if len(nz) > 3:
        c.poly(nz, T['nose']); c.poly([(min(px, x - bw * 0.1), py) for px, py in nz], T['noseL'])
        c.poly([(max(px, x + bw * 0.3), py) for px, py in nz], tuple(int(v * 0.6) for v in T['nose']))
    bh = yb - yn
    c.rect(x - bw, yn + bh * 0.9, x + bw, yn + bh * 0.98, fill=T['nose'])
    c.rect(x - bw * 0.62, yTop + noseH * 0.5, x - bw * 0.5, yb - 6, fill=(255, 255, 255, 110))
    if num is not None: c.text(x + bw * 0.05, yn + bh * 0.82, str(num), bw * 0.75, fill=(30, 40, 100, 170))
    n = 4; pr = min(bw * 0.42, bh / (n + 1) * 0.46)
    for i in range(n):
        py = yn + bh * 0.07 + bh * 0.72 * ((i + 0.5) / n) - bh * 0.03
        c.ell(x, py, pr * 1.18, pr * 1.18, fill=(224, 230, 250)); c.ell(x, py, pr, pr, fill=(10, 26, 58))
        if i < len(windows) and windows[i] is not None:
            nm, hue = windows[i]; c.ell(x, py, pr * 0.9, pr * 0.9, fill=hsl(hue, 0.7, 0.55)); c.text(x, py + pr * 0.04, nm[:1].upper(), pr * 1.1, fill=(255, 255, 255))
        c.ell(x - pr * 0.3, py - pr * 0.35, pr * 0.3, pr * 0.15, fill=(255, 255, 255, 150))
    if fl == 0: c.poly([(x - bw * 0.3 - 10, base + 1), (x - bw * 0.3 - 10, base - h * 0.07), (x - 10, base - h * 0.12), (x + bw * 0.3 - 10, base - h * 0.07), (x + bw * 0.3 - 10, base + 1)], (26, 34, 80))

def astro(c, x, y, u, hue, name, ph=0.0, walk=0.0, label=True, gold=False, scale=1.0, ok=0.0, tag=None, style=0):
    u = u * scale
    if u < 2: return
    sw = math.sin(ph) * u * 0.38 * walk; bob = abs(math.sin(ph)) * u * 0.14 * walk
    suit = hsl(hue, 0.68, 0.52); dark = hsl(hue, 0.68, 0.34); light = hsl(hue, 0.80, 0.72)
    by = y - bob
    c.ell(x, y + u * 0.05, u * 1.0, u * 0.3, fill=(0, 0, 0, 95))
    c.rw(x + u * 0.5, by - u * 2.05, u * 0.62, u * 1.1, u * 0.2, fill=(57, 64, 110))
    c.rw(x - u * 0.62 + sw * 0.4, by - u * 0.72, u * 0.5, u * 0.72, u * 0.2, fill=dark); c.rw(x + u * 0.12 - sw * 0.4, by - u * 0.72, u * 0.5, u * 0.72, u * 0.2, fill=dark)
    c.rw(x - u * 0.68 + sw * 0.4, by - u * 0.2, u * 0.62, u * 0.26, u * 0.12, fill=(32, 38, 74)); c.rw(x + u * 0.06 - sw * 0.4, by - u * 0.2, u * 0.62, u * 0.26, u * 0.12, fill=(32, 38, 74))
    c.rw(x + u * 0.62, by - u * 1.95 - sw * 0.2, u * 0.4, u * 1.0, u * 0.2, fill=dark)
    c.rw(x - u * 0.78, by - u * 2.15, u * 1.56, u * 1.6, u * 0.45, fill=suit)
    c.rw(x - u * 0.72, by - u * 2.1, u * 0.4, u * 1.5, u * 0.2, fill=light + (150,)); c.rw(x + u * 0.38, by - u * 2.1, u * 0.36, u * 1.5, u * 0.2, fill=dark + (140,))
    c.ell(x, by - u * 1.5, u * 0.22, u * 0.22, fill=(255, 255, 255, 220)) if style % 3 == 0 else c.rw(x - u * 0.4, by - u * 1.65, u * 0.8, u * 0.22, u * 0.1, fill=(255, 255, 255, 220))
    c.rw(x - u * 1.02, by - u * 1.95 + sw * 0.2, u * 0.4, u * 1.0, u * 0.2, fill=suit)
    hy = by - u * 2.95; hr = u * 1.02
    c.ell(x, hy, hr, hr, fill=(222, 228, 248)); c.ell(x, hy, hr, hr, outline=suit, w=max(1.5, u * 0.14))
    c.ell(x, hy, hr * 0.78, hr * 0.78, fill=hsl(hue, 0.7, 0.55))
    c.text(x, hy + hr * 0.04, (name.strip()[:1] or '?').upper(), hr * 0.9, fill=(255, 255, 255))
    c.ell(x - hr * 0.3, hy - hr * 0.42, hr * 0.36, hr * 0.16, fill=(255, 255, 255, 110))
    if style % 5 == 0:
        c.line([(x, hy - hr), (x, hy - hr - u * 0.55)], (207, 214, 255), max(1, u * 0.1)); c.ell(x, hy - hr - u * 0.6, u * 0.2, u * 0.2, fill=(255, 84, 104))
    elif style % 5 == 4:
        c.poly([(x - hr * 0.5, hy - hr * 0.9), (x - hr * 0.3, hy - hr * 1.35), (x, hy - hr * 1.0), (x + hr * 0.3, hy - hr * 1.35), (x + hr * 0.5, hy - hr * 0.9)], (255, 210, 90))
    if label:
        fs = clamp(u * 0.8, 12, 19); lab = name if len(name) <= 11 else name[:10] + '…'
        tw = c.tw(lab, fs) + 16; th = fs + 10; ly = hy - hr - u * (1.1 if style % 5 == 0 else 0.55) - th
        c.rw(x - tw / 2, ly, tw, th, th / 2, fill=(6, 10, 34, 205), outline=(255, 210, 90) if gold else suit, ow=2)
        c.text(x, ly + th / 2 + 0.5, lab, fs, fill=(255, 255, 255))
        if ok > 0:
            a = int(255 * clamp(ok)); ox = x + tw / 2 + 4; oy = ly + th / 2; r = th * 0.58
            c.ell(ox, oy, r, r, fill=(47, 211, 122, a)); c.check(ox, oy, r, (255, 255, 255, a), max(2, r * 0.22))
        if tag:
            c.text(x, ly - 14, tag, 15, fill=(255, 210, 90), stroke=3)

def cop(c, x, y, u, face, skin, active=False, target=None, t=0.0):
    f = face
    c.ell(x, y + u * 0.05, u * 1.0, u * 0.3, fill=(0, 0, 0, 95))
    c.rw(x - u * 0.55, y - u * 0.85, u * 0.45, u * 0.85, u * 0.18, fill=(23, 35, 90)); c.rw(x + u * 0.1, y - u * 0.85, u * 0.45, u * 0.85, u * 0.18, fill=(23, 35, 90))
    c.rw(x - u * 0.62, y - u * 0.2, u * 0.58, u * 0.24, u * 0.1, fill=(12, 15, 34)); c.rw(x + u * 0.04, y - u * 0.2, u * 0.58, u * 0.24, u * 0.1, fill=(12, 15, 34))
    c.rw(x - f * u * 0.95 - u * 0.2, y - u * 2.0, u * 0.4, u * 1.0, u * 0.2, fill=(26, 44, 120))
    c.rw(x - u * 0.8, y - u * 2.25, u * 1.6, u * 1.55, u * 0.4, fill=(42, 74, 168)); c.rw(x - u * 0.76, y - u * 2.2, u * 0.4, u * 1.45, u * 0.2, fill=(58, 95, 207, 150))
    c.rect(x - u * 0.8, y - u * 0.95, x + u * 0.8, y - u * 0.73, fill=(16, 20, 46)); c.rect(x - u * 0.15, y - u * 0.95, x + u * 0.15, y - u * 0.73, fill=(255, 210, 90))
    c.ell(x - f * u * 0.35, y - u * 1.7, u * 0.2, u * 0.2, fill=(255, 210, 90))
    hy = y - u * 2.9 + math.sin(t * 1.6) * u * 0.03; hr = u * 0.9
    c.ell(x, hy, hr, hr, fill=skin)
    c.rw(x - hr * 0.8, hy - hr * 0.2, hr * 1.6, hr * 0.4, hr * 0.15, fill=(16, 20, 46)); c.rect(x - hr * 0.6, hy - hr * 0.12, x - hr * 0.25, hy - hr * 0.02, fill=(255, 255, 255, 90))
    c.arc(x, hy + hr * 0.3, hr * 0.3, hr * 0.3, 10, 170, (122, 59, 42), max(1, u * 0.08))
    c.d.pieslice([(x - hr * 1.02) * SS, (hy - hr * 0.15 - hr * 1.02) * SS, (x + hr * 1.02) * SS, (hy - hr * 0.15 + hr * 1.02) * SS], 180, 360, fill=(22, 39, 106))
    c.rect(x - hr * 1.02, hy - hr * 0.24, x + hr * 1.02, hy - hr * 0.04, fill=(12, 20, 64)); c.ell(x + f * hr * 0.75, hy - hr * 0.12, hr * 0.55, hr * 0.14, fill=(10, 15, 46))
    c.ell(x, hy - hr * 0.72, hr * 0.2, hr * 0.2, fill=(255, 210, 90))
    shx = x + f * u * 0.85; shy = y - u * 2.0
    hx = shx + f * u * (0.9 if active else 0.35); hy2 = shy + u * (-0.1 if active else 0.7)
    c.line([(shx, shy + u * 0.1), (hx, hy2)], (42, 74, 168), u * 0.42)
    c.rw(hx - u * 0.18, hy2 - u * 0.55, u * 0.36, u * 0.85, u * 0.12, fill=(230, 236, 255)); c.rect(hx - u * 0.12, hy2 - u * 0.55, hx + u * 0.12, hy2 - u * 0.37, fill=(56, 232, 255) if active else (122, 134, 184))
    if active and target:
        tx, ty = target; bx, by = hx, hy2 - u * 0.5
        a = int(150 + 90 * math.sin(t * 22))
        c.poly([(bx, by), (tx, ty - u * 1.1), (tx, ty + u * 1.1)], (80, 240, 255, a))

def gate_back(c, t, scanning):
    x, y = GATE; u = GU; hw = u * 1.7; ph = u * 4.6
    c.ell(x, y + u * 0.1, hw * 1.35, u * 0.5, fill=(0, 0, 0, 80)); c.ell(x, y + u * 0.05, hw * 1.2, u * 0.42, fill=(58, 72, 128)); c.ell(x, y + u * 0.05, hw * 1.2, u * 0.42, outline=(255, 210, 90), w=1.5)
    for sx in (-1, 1):
        c.rw(x + sx * hw - u * 0.28, y - ph, u * 0.56, ph, u * 0.2, fill=(120, 133, 190)); c.rw(x + sx * hw - u * 0.28 + (u * 0.28 if sx < 0 else 0), y - ph, u * 0.28, ph, u * 0.14, fill=(74, 84, 144))
    c.rw(x - hw - u * 0.5, y - ph - u * 0.6, hw * 2 + u, u * 0.95, u * 0.28, fill=(38, 48, 122), outline=(122, 136, 208), ow=1.5)
    c.text(x, y - ph - u * 0.1, 'REVISIÓN', u * 0.6, fill=(230, 236, 255))
    on = scanning and int(t * 8) % 2 == 0
    c.ell(x + hw + u * 0.12, y - ph - u * 0.12, u * 0.18, u * 0.18, fill=(255, 210, 90) if scanning and on else ((138, 106, 16) if scanning else (47, 211, 122)))

def gate_front(c, k):
    x, y = GATE; u = GU; hw = u * 1.7; ph = u * 4.6
    c.rect(x - hw + u * 0.28, y - ph, x + hw - u * 0.28, y, fill=(80, 220, 255, 26))
    yy = y - ph * (0.5 - 0.5 * math.cos(k * 6.283 * 1.5))
    c.rect(x - hw + u * 0.28, yy - u * 0.25, x + hw - u * 0.28, yy + u * 0.25, fill=(120, 250, 255, 200))

def lane(c, pts, t):
    c.line(pts, (110, 130, 255, 34), 30)
    n = 0
    for (a, b) in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1]); k = 0.0
        while k < L:
            s0 = (k + (t * 26) % 24) % L; e0 = min(L, s0 + 10)
            p0 = (a[0] + (b[0] - a[0]) * s0 / L, a[1] + (b[1] - a[1]) * s0 / L); p1 = (a[0] + (b[0] - a[0]) * e0 / L, a[1] + (b[1] - a[1]) * e0 / L)
            c.line([p0, p1], (200, 212, 255, 90), 1.5); k += 24

def confetti(c, t, n=36, seed=1, area=(0, 0, W, H), g=260):
    r = random.Random(seed)
    for i in range(n):
        x0 = area[0] + r.random() * (area[2] - area[0]); v = 60 + r.random() * 110; ph = r.random() * 6.28
        col = [(255, 84, 104), (255, 210, 90), (80, 220, 255), (126, 224, 160), (190, 120, 255)][i % 5]
        y = area[1] + ((t * v + r.random() * 400) % (area[3] - area[1])); x = x0 + math.sin(t * 3 + ph) * 18
        s = 3 + r.random() * 4
        c.rw(x, y, s, s * 1.6, 1, fill=col + (230,))

# ---------------------------------------------------------------- personajes y rutas
VIEW = [('Valeria', 330, 0), ('Diego_pe', 200, 1), ('Camila', 40, 2), ('Juancho', 130, 3), ('LuzMaria', 285, 4)]
JOINS = JOIN + [TU_JOIN]
CHARS = [dict(name=n, hue=h, st=s, join=JOINS[k]) for k, (n, h, s) in enumerate(VIEW)] + [dict(name='TU NOMBRE', hue=48, st=5, join=TU_JOIN, gold=True)]
LEAVES = {0: LEAVE0, 1: LEAVE1}
QX = 270
def qy(slot): return 648 + 58 * slot
def path(t, pts):
    if t <= pts[0][0]: return pts[0][1], pts[0][2]
    for a, b in zip(pts, pts[1:]):
        if t <= b[0]:
            k = eio((t - a[0]) / max(1e-6, b[0] - a[0])); return lerp(a[1], b[1], k), lerp(a[2], b[2], k)
    return pts[-1][1], pts[-1][2]

def char_state(k, t):
    """devuelve (x, y, moving, visible, scale, ok) del personaje k"""
    ch = CHARS[k]
    if t < ch['join']: return None
    slot = k - sum(eo((t - LEAVES[j]) / 0.5) for j in LEAVES if j < k)
    x, y = QX, qy(slot)
    jk = eo((t - ch['join']) / 0.6)
    if t < ch['join'] + 0.6: y = lerp(995, y, jk)
    moving = (t < ch['join'] + 0.6)
    sc = 0.85; ok = 0.0
    if k == 0:
        if t >= LEAVES[0]:
            x, y = path(t, [(LEAVES[0], QX, qy(0)), (GATE0, QX, 612), (OK0, QX, 612), (DOOR0, R1['x'], R1['base'] + 18)])
            moving = not (GATE0 <= t <= OK0) and t < DOOR0
            sc = 0.85 + 0.15 * eo((t - LEAVES[0]) / 0.5); ok = clamp((t - OK0) / 0.25) if t >= OK0 else 0.0
            if t >= DOOR0: sc *= 1 - eo((t - DOOR0) / 0.25)
            if t >= DOOR0 + 0.25: return None
    elif k == 1:
        if t >= LEAVES[1]:
            x, y = path(t, [(LEAVES[1], QX, qy(0)), (LEAVES[1] + 0.5, QX, 612), (DOOR1, R1['x'], R1['base'] + 18)])
            moving = t < DOOR1; sc = 1.0; ok = 1.0 if t > LEAVES[1] + 0.5 else 0.0
            if t >= DOOR1: sc *= 1 - eo((t - DOOR1) / 0.25)
            if t >= DOOR1 + 0.25: return None
    return x, y, moving, sc, ok

def draw_char(c, k, t, label=True, tag=None):
    st = char_state(k, t)
    if st is None: return
    x, y, mv, sc, ok = st; ch = CHARS[k]
    astro(c, x, y, unit(y), ch['hue'], ch['name'], ph=t * 14 + k, walk=1.0 if mv else 0.0, label=label, gold=ch.get('gold', False), scale=sc, ok=ok, tag=tag, style=ch['st'])

# ---------------------------------------------------------------- superpuestos
def live_pill(c, x, y, s=1.0, t=0.0):
    w, h = 64 * s, 26 * s
    c.rw(x, y, w, h, h / 2, fill=(255, 40, 70))
    pul = 0.5 + 0.5 * math.sin(t * 7)
    c.ell(x + 13 * s, y + h / 2, 4.5 * s, 4.5 * s, fill=(255, 255, 255, int(150 + 105 * pul)))
    c.text(x + 38 * s, y + h / 2 + 0.5, 'LIVE', 14 * s, fill=(255, 255, 255))

def hud(c, t):
    live_pill(c, 16, 132, 1.0, t)
    c.text(92, 145, HANDLE, 17, fill=(255, 255, 255), anchor='lm', stroke=3)

def toasts(c, t):
    for k, (n, h, s) in enumerate(VIEW):
        dt = t - JOIN[k]
        if -0.0 <= dt <= 1.5:
            ax = eo(dt / 0.25) if dt < 1.2 else 1 - eo((dt - 1.2) / 0.3)
            if dt >= 1.2: ax = 1 - eo((dt - 1.2) / 0.3)
            x = lerp(-230, 14, clamp(ax)); y = 190 + (k % 3) * 40
            lab = n + ' entró'; w = c.tw(lab, 16) + 44
            c.rw(x, y, w, 32, 16, fill=(10, 14, 44, 225), outline=hsl(h, 0.7, 0.55), ow=2)
            c.ell(x + 17, y + 16, 11, 11, fill=hsl(h, 0.7, 0.55)); c.text(x + 17, y + 16.5, n[:1], 14, fill=(255, 255, 255))
            c.text(x + 34, y + 16.5, lab, 16, anchor='lm')

def flash(c, t):
    for s in S[1:]:
        dt = t - s
        if 0 <= dt < 0.18:
            c.rect(0, 0, W, H, fill=(255, 255, 255, int(150 * (1 - dt / 0.18))))

def chunks_for(line):
    words = line['text'].split(); n = len(words); ws = line['words']
    if len(ws) != n: ws = [[w, line['t0'] + (line['t1'] - line['t0']) * i / n, line['t0'] + (line['t1'] - line['t0']) * (i + 1) / n] for i, w in enumerate(words)]
    g = max(1, math.ceil(n / 3)); out = []; i = 0
    for j in range(g):
        m = (n - i + (g - j) - 1) // (g - j); out.append((i, i + m)); i += m
    return words, ws, out

_CH = [chunks_for(l) for l in LINES]
def captions(c, t, y=775):
    li = line_at(t)
    if li is None: return
    words, ws, ch = _CH[li]
    cur = None
    for (a, b) in ch:
        if t >= ws[a][1] - 0.04: cur = (a, b)
    if cur is None: return
    a, b = cur
    if t > ws[b - 1][2] + 0.45 and (b < len(words) or t > LINES[li]['t1'] + 0.3): return
    size = 36
    while sum(c.tw(w, size) for w in words[a:b]) + c.tw(' ', size) * (b - a - 1) > 500 and size > 20: size -= 2
    sp = c.tw(' ', size); tot = sum(c.tw(w, size) for w in words[a:b]) + sp * (b - a - 1)
    x = W / 2 - tot / 2
    for idx in range(a, b):
        w = words[idx]; wd = c.tw(w, size)
        act = ws[idx][1] - 0.02 <= t <= ws[idx][2] + 0.05
        pop = 1.0
        c.text(x, y, w, size, fill=(255, 224, 64) if act else (255, 255, 255), anchor='lm', stroke=6, sfill=(0, 0, 0))
        x += wd + sp

# ---------------------------------------------------------------- escenas
def base_world(t):
    c = Cv(world_bg()); world_dyn(c, t); return c

def ground_props(c, t, r1=True, r1flame=0.0, r1dy=0.0, r2=True, r1windows=(), r2windows=(), shake=0.0, r1num=1):
    pad(c, R1['x'], R1['base'], 62); pad(c, R2['x'], R2['base'], 54)
    tower(c, R1['x'] + 70, R1['base'] + 4, 175); tower(c, R2['x'] - 62, R2['base'] + 4, 150)
    if r2: rocket(c, R2['x'], R2['base'], R2['h'], 1, 0.0, t, r2windows, 2)
    if r1: rocket(c, R1['x'] + math.sin(t * 90) * shake, R1['base'] + r1dy, R1['h'], 0, r1flame, t, r1windows, r1num)

def scene_A(t):
    c = base_world(t)
    la = max(0, t - 0.5); dy = -(la ** 2) * 190
    ground_props(c, t, r1flame=0.9 if t > 0 else 0.9, r1dy=dy, shake=2.0 if t < 1.2 else 1.0, r1num=1)
    if dy < -60: c.glow(R1['x'], R1['base'] + dy + 40, 120, (255, 160, 70), 0.3)
    pu = 1.0 + 0.04 * math.sin(t * 8)
    c.text(W / 2, 205, 'ENTRA AL', 54 * pu, fill=(255, 255, 255), stroke=7)
    c.text(W / 2, 268, 'LIVE', 78 * pu, fill=(255, 214, 64), stroke=9)
    c.text(W / 2, 330, 'y tu skin sube a un cohete', 25, fill=(255, 255, 255), stroke=5)
    return c

def scene_BC(t, withtu):
    c = base_world(t)
    ground_props(c, t)
    lane(c, [(QX, 990), (QX, 630)], t)
    gate_back(c, t, False)
    for k in range(len(CHARS) - 1 + (1 if withtu else 0), -1, -1):
        pass
    order = sorted(range(len(CHARS)), key=lambda k: (char_state(k, t) or (0, -1))[1])
    for k in order:
        if k == 5 and not withtu: continue
        draw_char(c, k, t, True, tag='¡ESE ERES TÚ!' if (k == 5 and t - TU_JOIN > 0.7) else None)
    gate_front(c, 0.0 if t < 0 else 0.0) if False else None
    if not withtu: toasts(c, t)
    else:
        a = clamp((t - TU_JOIN) / 0.3)
        c.text(W / 2, 205, 'HAZ FILA', 44 * (0.9 + 0.1 * back(a)), fill=(255, 255, 255), stroke=6)
        c.text(W / 2, 255, 'con tu nombre', 28, fill=(255, 224, 64), stroke=5)
    return c

def scene_D(t):
    c = base_world(t)
    ground_props(c, t)
    lane(c, [(QX, 990), (QX, 630)], t)
    scanning = SCAN[0] <= t <= SCAN[1]
    gate_back(c, t, scanning)
    # policías
    tgt = (QX, 612)
    cop(c, QX - 78, 610, 15.0, 1, (233, 184, 144), scanning, tgt if scanning else None, t)
    cop(c, QX + 78, 610, 15.0, -1, (141, 91, 60), scanning, tgt if scanning else None, t)
    order = sorted(range(len(CHARS)), key=lambda k: (char_state(k, t) or (0, -1))[1])
    for k in order: draw_char(c, k, t, True)
    if scanning: gate_front(c, (t - SCAN[0]) / (SCAN[1] - SCAN[0]))
    c.text(W / 2, 205, '2 POLICÍAS', 42, fill=(255, 255, 255), stroke=6)
    c.text(W / 2, 252, 'revisan tu skin', 28, fill=(120, 240, 255), stroke=5)
    if t >= OK0:
        a = back((t - OK0) / 0.3)
        w = 250 * a; c.rw(W / 2 - w / 2, 300, w, 46, 23, fill=(47, 211, 122, 240))
        if a > 0.6:
            c.check(W / 2 - 95, 323, 14, (255, 255, 255), 4); c.text(W / 2 + 12, 324, 'SKIN APROBADA', 22, fill=(255, 255, 255))
    return c

def scene_E(t):
    c = base_world(t)
    n_in = (1 if t >= DOOR0 else 0) + (1 if t >= DOOR1 else 0)
    wins = [(CHARS[0]['name'], CHARS[0]['hue']) if t >= DOOR0 else None, (CHARS[1]['name'], CHARS[1]['hue']) if t >= DOOR1 else None, None, None]
    wins = [w for w in wins if w] + [None] * 4
    lt = t - LAUNCH
    dy = -(lt ** 2) * 230 if lt > 0 else 0.0
    fl = 0.0
    if CD[0] - 0.4 <= t < LAUNCH: fl = 0.4 + 0.4 * clamp((t - CD[0]) / 1.5)
    if lt >= 0: fl = 1.0
    ground_props(c, t, r1flame=fl, r1dy=dy, r1windows=wins, shake=(2.0 if CD[0] <= t < LAUNCH else 0.0))
    if lt >= 0 and lt < 1.2: c.glow(R1['x'], R1['base'] + 10, 140, (255, 200, 120), 0.55 * (1 - lt / 1.2))
    lane(c, [(QX, 990), (QX, 630)], t)
    gate_back(c, t, False)
    order = sorted(range(len(CHARS)), key=lambda k: (char_state(k, t) or (0, -1))[1])
    for k in order: draw_char(c, k, t, True)
    for i, ct in enumerate(CD):
        dt = t - ct
        if 0 <= dt < 0.5:
            a = 1 - dt / 0.5; s = 150 * (0.8 + 0.5 * eo(dt / 0.5))
            c.text(W / 2, 400, str(3 - i), s, fill=(255, 224, 64, int(255 * a ** 0.5)), stroke=10)
    if t < CD[0]:
        c.text(W / 2, 205, 'SUBES AL COHETE', 40, fill=(255, 255, 255), stroke=6)
    if lt >= 0 and lt < 1.6:
        a = back(lt / 0.3); c.text(W / 2, 330, '¡DESPEGUE!', 62 * a, fill=(255, 100, 90), stroke=8)
    return c

PLAN = [('Mercurio', 52, 0.25, 6, (190, 180, 170)), ('Venus', 78, -0.85, 9, (240, 200, 120)), ('Tierra', 112, 0.35, 10, (80, 150, 255)),
        ('Marte', 200, -0.6, 9, (230, 90, 60)), ('Júpiter', 300, 0.7, 20, (225, 175, 120)), ('Saturno', 400, -0.5, 17, (235, 205, 140)), ('Urano', 350, 0.1, 12, (130, 220, 230))]
SUN = (40, 520)
def ppos(name):
    for n, r, a, s, col in PLAN:
        if n == name: return SUN[0] + r * math.cos(a), SUN[1] + r * math.sin(a)

def scene_F(t):
    c = Cv(vgrad_img(W * SS, H * SS, [(0, (3, 4, 20)), (1, (14, 12, 44))]))
    for (x, y, r, p) in STARS: c.ell(x, y * 3.5 % H, r, r, fill=(255, 255, 255, int(80 + 120 * abs(math.sin(t + p)))))
    c.glow(SUN[0], SUN[1], 190, (255, 190, 60), 0.9); c.ell(SUN[0], SUN[1], 34, 34, fill=(255, 214, 90))
    for n, r, a, s, col in PLAN: c.ell(SUN[0], SUN[1], r, r, outline=(150, 165, 255, 55), w=1)
    for n, r, a, s, col in PLAN:
        x, y = ppos(n); c.glow(x, y, s * 2.2, col, 0.4); c.ell(x, y, s, s, fill=col)
        if n == 'Saturno': c.ell(x, y, s * 1.9, s * 0.5, outline=(240, 220, 170, 200), w=3)
        c.text(x, y + s + 12, n, 13, fill=(220, 228, 255), stroke=2)
    ea = ppos('Tierra'); span = max(0.1, E[5] - sF); k = clamp((t - sF) / span)
    for i, (dest, frac) in enumerate([('Marte', 0.95), ('Saturno', 0.6), ('Júpiter', 0.78)]):
        b = ppos(dest); p = eo(k) * frac
        x = lerp(ea[0], b[0], p); y = lerp(ea[1], b[1], p)
        c.line([ea, (x, y)], (255, 224, 120, 140), 2)
        ang = math.atan2(b[1] - ea[1], b[0] - ea[0])
        c.glow(x, y, 20, (255, 160, 70), 0.7)
        ux, uy = math.cos(ang), math.sin(ang); nx, ny = -uy, ux
        c.poly([(x + ux * 11, y + uy * 11), (x - ux * 8 + nx * 5, y - uy * 8 + ny * 5), (x - ux * 8 - nx * 5, y - uy * 8 - ny * 5)], (235, 240, 255))
        c.poly([(x - ux * 8 + nx * 3, y - uy * 8 + ny * 3), (x - ux * 18, y - uy * 18), (x - ux * 8 - nx * 3, y - uy * 8 - ny * 3)], (255, 170, 60))
        lab = '#%d → %s' % (i + 1, dest); w = c.tw(lab, 15) + 16
        lx = (x - 14 - w) if i == 0 else (x + 14); ly = y - 26 - (i % 2) * 6
        c.rw(lx, ly, w, 24, 12, fill=(10, 14, 44, 225), outline=(255, 210, 90), ow=1.5); c.text(lx + 8, ly + 12.5, lab, 15, anchor='lm')
    c.text(W / 2, 205, 'CADA COHETE', 40, fill=(255, 255, 255), stroke=6)
    c.text(W / 2, 250, 'VIAJA A UN PLANETA', 32, fill=(255, 224, 64), stroke=5)
    return c

def scene_G(t):
    c = Cv(vgrad_img(W * SS, H * SS, [(0, (30, 10, 28)), (0.55, (120, 50, 50)), (1, (60, 22, 24))]))
    for (x, y, r, p) in STARS[:50]: c.ell(x, y * 2.0 % 500, r, r, fill=(255, 235, 220, 160))
    c.glow(400, 250, 120, (255, 200, 150), 0.3)
    c.ell(270, 1160, 560, 520, fill=(176, 72, 44)); c.ell(270, 1160, 560, 520, outline=(255, 150, 110, 120), w=3)
    for (cx, cy, r) in [(120, 700, 34), (410, 740, 44), (250, 840, 28), (60, 820, 22), (480, 650, 20)]:
        c.ell(cx, cy, r, r * 0.4, fill=(122, 44, 30)); c.ell(cx, cy - 2, r * 0.85, r * 0.3, fill=(150, 60, 40))
    land = clamp((t - sG) / (ARRIVE - sG)); ry = lerp(150, 660, eo(land)); base = ry
    c.ell(270, 668, 70 * (0.4 + 0.6 * land), 12, fill=(0, 0, 0, 90))
    rocket(c, 270, base, 190, 0, (1 - land) * 0.9 + (0.0 if land >= 1 else 0.1), t, [(CHARS[0]['name'], CHARS[0]['hue']), (CHARS[1]['name'], CHARS[1]['hue'])], 1)
    if land >= 1:
        a = clamp((t - ARRIVE) / 0.4)
        for k, (dx, ch) in enumerate([(-80, 0), (80, 1)]):
            wv = math.sin(t * 9 + k) * 0.5
            astro(c, 270 + dx * eo(a), 700 + 6 * k, 14.5, CHARS[ch]['hue'], CHARS[ch]['name'], ph=t * 3 + k, walk=0.0, label=True, scale=eo(a), style=CHARS[ch]['st'])
        confetti(c, t - ARRIVE, 40, 3, (0, 150, 540, 700))
    a = back(clamp((t - sG) / 0.35))
    c.text(W / 2, 205, '¡LLEGAMOS A', 44 * a, fill=(255, 255, 255), stroke=6)
    c.text(W / 2, 270, 'MARTE!', 78 * a, fill=(255, 214, 64), stroke=9)
    return c

def scene_CTA(t, last):
    c = base_world(t)
    sl = eo((t - sH) / 0.5)
    pad(c, R1['x'], R1['base'], 62); pad(c, R2['x'], R2['base'], 54)
    tower(c, R1['x'] + 70, R1['base'] + 4, 175); tower(c, R2['x'] - 62, R2['base'] + 4, 150)
    rocket(c, R2['x'], R2['base'], R2['h'], 1, 0.0, t, [], 2)
    rocket(c, R1['x'], R1['base'] - (1 - sl) * 520, R1['h'], 0, 0.5 * (1 - sl), t, [], 3)
    lane(c, [(QX, 990), (QX, 630)], t)
    gate_back(c, t, False)
    for k in range(4):
        y = 650 + 60 * k; astro(c, QX + math.sin(t * 2 + k) * 0, y, unit(y) * 0.85, [330, 200, 40, 285][k], ['Ana', 'Leo', 'Sol', 'Max'][k], ph=t * 14, walk=0.0, label=True, style=k)
    pu = 1 + 0.05 * math.sin(t * 8)
    c.text(W / 2, 205, 'ENTRA AL LIVE', 50 * pu, fill=(255, 255, 255), stroke=7)
    c.text(W / 2, 262, 'AHORA', 66 * pu, fill=(255, 214, 64), stroke=8)
    live_pill(c, W / 2 - 64, 300, 2.0, t)
    c.text(W / 2, 372, HANDLE, 26, fill=(255, 255, 255), stroke=5)
    if last: confetti(c, t, 46, 9)
    return c

def make_frame(i):
    t = i / FPS
    if t < sB: c = scene_A(t)
    elif t < sC: c = scene_BC(t, False)
    elif t < sD: c = scene_BC(t, True)
    elif t < sE: c = scene_D(t)
    elif t < sF: c = scene_E(t)
    elif t < sG: c = scene_F(t)
    elif t < sH: c = scene_G(t)
    elif t < sI: c = scene_CTA(t, False)
    else: c = scene_CTA(t, True)
    flash(c, t); hud(c, t); captions(c, t)
    im = c.im.resize((W, H), Image.LANCZOS) if SS != 1 else c.im
    return im

def work(i):
    make_frame(i).save('%s/f%05d.jpg' % (FR, i), quality=90)
    return i

if __name__ == '__main__':
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    b = int(sys.argv[2]) if len(sys.argv) > 2 else NF
    idx = list(range(a, min(b, NF)))
    with mp.Pool(mp.cpu_count()) as p:
        for n, _ in enumerate(p.imap(work, idx, chunksize=4)):
            if n % 60 == 0: print('cuadro', n, '/', len(idx), flush=True)
    print('listo', len(idx))

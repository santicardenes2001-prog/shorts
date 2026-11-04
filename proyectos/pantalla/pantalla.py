"""Short "¿Cómo funciona la pantalla de tu celular?" — animación procedural (sin personaje).

    python proyectos/pantalla/pantalla.py --fotos 1,5.5,14     # fotogramas sueltos
    python proyectos/pantalla/pantalla.py                      # render completo -> salidas/

Todo se dibuja con cairo (vector) + numpy/opencv (zoom a subpíxeles, barrido fila por fila).
Los tiempos salen de audio/palabras.json (ver tiempos.py); subtítulos con el estilo del motor.
"""
import argparse
import functools
import math
import os
import subprocess
import sys
import tempfile
import wave
from multiprocessing import Pool

import cairo
import cv2
import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, ROOT)
sys.path.insert(0, AQUI)
import motor  # noqa: E402
from tiempos import NARRACION, Tiempos  # noqa: E402

W, H, FPS = 1080, 1920, 30
SR = 48000


def _registrar_fuente():
    """cairo busca 'Lilita One' por nombre: la instala para el usuario si no está."""
    try:
        if "Lilita One" in subprocess.run(["fc-list"], capture_output=True, text=True).stdout:
            return
        dst = os.path.expanduser("~/.local/share/fonts")
        os.makedirs(dst, exist_ok=True)
        import shutil
        shutil.copy(os.path.join(ROOT, "fonts", "LilitaOne-Regular.ttf"), dst)
        subprocess.run(["fc-cache", "-f"], capture_output=True)
    except FileNotFoundError:
        print("aviso: no encuentro fontconfig; instalá la fuente fonts/LilitaOne-Regular.ttf a mano")


_registrar_fuente()
T = Tiempos()
TOTAL = T.total
b = T.b

# ------------------------------------------------------------------ colores
def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


INK = hx("#24201F")
AMARILLO = hx("#FFD600")          # azul = 0: en el zoom solo se prenden rojo y verde
BLANCO = (1, 1, 1)
CIAN = hx("#22E4FF")
ROJO_SP, VERDE_SP, AZUL_SP = hx("#FF3B30"), hx("#34E05A"), hx("#3A7BFF")
PIEL = hx("#F2B896")
ROJO_BOTON = hx("#E5252A")
LILITA = "Lilita One"
UI = "Inter"


# ------------------------------------------------------------------ utilidades
def clamp(v, a=0.0, c=1.0):
    return max(a, min(c, v))


def lerp(a, c, p):
    return a + (c - a) * p


def ease(p, kind="inout"):
    return motor.ease(kind, clamp(p))


def prog(t, t0, d, kind="inout"):
    return ease((t - t0) / max(d, 1e-6), kind)


def pop(t, t0, d=0.35):
    """Escala de entrada con rebote (0 antes de t0)."""
    if t < t0:
        return 0.0
    return max(motor.ease("back", clamp((t - t0) / d)), 0.0)


def bump(t, t0, d=0.3, amp=0.18):
    """Golpe de escala que vuelve a 1."""
    if t < t0 or t > t0 + d:
        return 1.0
    q = (t - t0) / d
    return 1 + amp * math.sin(math.pi * q) * (1 - q * 0.3)


def rng(seed):
    return np.random.default_rng(seed)


# ------------------------------------------------------------------ cairo <-> numpy
def lienzo():
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    return s, cairo.Context(s)


def a_rgb(s):
    s.flush()
    a = np.ndarray((H, W, 4), np.uint8, s.get_data())
    return a[..., 2::-1].copy()


def desde_rgb(rgb):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    a = np.ndarray((H, W, 4), np.uint8, s.get_data())
    a[..., 0] = rgb[..., 2]
    a[..., 1] = rgb[..., 1]
    a[..., 2] = rgb[..., 0]
    a[..., 3] = 255
    s.mark_dirty()
    return s, cairo.Context(s)


def rrect(ctx, x, y, w, h, r):
    r = max(0, min(r, w / 2, h / 2))
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def fuente(ctx, fam, size, bold=False):
    ctx.select_font_face(fam, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)


def texto(ctx, s, x, y, size, fill=BLANCO, stroke=INK, sw=10, ax=0.5, ay=0.5, fam=LILITA, bold=False, alpha=1.0):
    fuente(ctx, fam, size, bold)
    xb, yb, tw, th, xa, _ = ctx.text_extents(s)
    asc, desc = ctx.font_extents()[:2]
    px = x - ax * xa
    py = y - (yb + th / 2) if ay == 0.5 else y
    ctx.move_to(px, py)
    ctx.text_path(s)
    if stroke is not None and sw > 0:
        ctx.set_source_rgba(*stroke, alpha)
        ctx.set_line_width(sw * 2)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
    ctx.set_source_rgba(*fill, alpha)
    ctx.fill()
    return xa


def cartel(ctx, txt, x, y, size, box=AMARILLO, fg=INK, s=1.0, alpha=1.0, rot=0.0, pad=(36, 20), r=28, borde=6,
           sombra=10, fam=LILITA):
    """Cartel con caja, contorno y sombra (estilo del canal)."""
    if s <= 0.003 or alpha <= 0.003:
        return
    lines = txt.split("\n")
    fuente(ctx, fam, size)
    ws = [ctx.text_extents(l)[4] for l in lines]
    asc, desc = ctx.font_extents()[:2]
    lh = (asc + desc) * 0.86
    bw = max(ws) + 2 * pad[0]
    bh = lh * len(lines) + 2 * pad[1]
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.scale(s, s)
    ctx.push_group()
    if sombra:
        rrect(ctx, -bw / 2, -bh / 2 + sombra, bw, bh, r)
        ctx.set_source_rgb(*INK)
        ctx.fill()
    rrect(ctx, -bw / 2, -bh / 2, bw, bh, r)
    ctx.set_source_rgb(*box)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(borde)
    ctx.stroke()
    for i, l in enumerate(lines):
        cy = -bh / 2 + pad[1] + lh * (i + 0.5)
        texto(ctx, l, 0, cy + size * 0.04, size, fill=fg, stroke=None, fam=fam)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()
    return bw, bh


def etiqueta_lenta(ctx, t, t0, t1, txt="CÁMARA LENTA", y=520):
    """Píldora con punto rojo que parpadea."""
    if t < t0 or t > t1 + 0.3:
        return
    s = pop(t, t0) * (1 - prog(t, t1, 0.3, "in"))
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(540, y)
    ctx.scale(s, s)
    fuente(ctx, LILITA, 50)
    tw = ctx.text_extents(txt)[4]
    w, h = tw + 120, 86
    rrect(ctx, -w / 2, -h / 2, w, h, h / 2)
    ctx.set_source_rgba(0.05, 0.06, 0.1, 0.82)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.9)
    ctx.set_line_width(4)
    ctx.stroke()
    on = (t * 2.2) % 1 < 0.6
    ctx.arc(-w / 2 + 48, 0, 15, 0, 2 * math.pi)
    ctx.set_source_rgb(*(hx("#FF3B30") if on else (0.35, 0.1, 0.1)))
    ctx.fill()
    texto(ctx, txt, -w / 2 + 80, 2, 50, ax=0, stroke=None)
    ctx.restore()


# ------------------------------------------------------------------ fondo oscuro
@functools.lru_cache(maxsize=1)
def _tile_puntos():
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 60, 60)
    c = cairo.Context(s)
    c.arc(30, 30, 2.2, 0, 2 * math.pi)
    c.set_source_rgba(0.55, 0.75, 1.0, 0.22)
    c.fill()
    return s


def fondo(ctx, t, tinte=(0.03, 0.05, 0.11)):
    g = cairo.RadialGradient(540, 820, 80, 540, 900, 1300)
    g.add_color_stop_rgb(0, tinte[0] * 2.2, tinte[1] * 2.2, tinte[2] * 2.2)
    g.add_color_stop_rgb(1, tinte[0] * 0.5, tinte[1] * 0.5, tinte[2] * 0.5)
    ctx.set_source(g)
    ctx.paint()
    pat = cairo.SurfacePattern(_tile_puntos())
    pat.set_extend(cairo.EXTEND_REPEAT)
    m = cairo.Matrix()
    m.translate(0, (t * 14) % 60)
    pat.set_matrix(m)
    ctx.set_source(pat)
    ctx.paint()


# ------------------------------------------------------------------ paisaje (la "imagen")
@functools.lru_cache(maxsize=None)
def _cresta(seed, base, amp, valle):
    xs = np.linspace(-40, 1120, 59)
    r = rng(seed)
    ph = r.uniform(0, 6.28, 4)
    ys = []
    for x in xs:
        lado = min(1.0, abs(x - 540) / 470) ** 1.3 if valle else 1.0
        n = (0.62 + 0.22 * math.sin(x * 0.011 + ph[0]) + 0.12 * math.sin(x * 0.029 + ph[1])
             + 0.05 * math.sin(x * 0.083 + ph[2]))
        ys.append(base - amp * (0.28 + 0.72 * lado) * n)
    return tuple(zip(xs.tolist(), ys))


def _montana(ctx, pts, color, fondo_y=1300):
    ctx.move_to(pts[0][0], fondo_y)
    for x, y in pts:
        ctx.line_to(x, y)
    ctx.line_to(pts[-1][0], fondo_y)
    ctx.close_path()
    ctx.set_source_rgb(*color)
    ctx.fill()


@functools.lru_cache(maxsize=1)
def _estrellas():
    r = rng(7)
    return [(r.uniform(0, 1080), r.uniform(0, 1100) ** 1.0, r.uniform(1.2, 3.4), r.uniform(0, 6.28)) for _ in range(170)]


def paisaje(ctx, t, modo="dia"):
    """Atardecer (o noche) en 1080x1920, dibujado en coordenadas locales."""
    dia = modo == "dia"
    HZ = 1245
    g = cairo.LinearGradient(0, 0, 0, HZ)
    stops = ([(0, "#1C0A3A"), (0.33, "#5A1A6E"), (0.6, "#D03A5C"), (0.8, "#FF7E3D"), (1, "#FFC85A")] if dia else
             [(0, "#02040F"), (0.45, "#081440"), (0.8, "#173070"), (1, "#2C4E94")])
    for o, c in stops:
        g.add_color_stop_rgb(o, *hx(c))
    ctx.rectangle(0, 0, 1080, HZ + 5)
    ctx.set_source(g)
    ctx.fill()
    if dia:
        sx, sy, sr = 540, 1105, 205
        halo = cairo.RadialGradient(sx, sy, sr * 0.8, sx, sy, sr * 3.0)
        halo.add_color_stop_rgba(0, 1, 0.78, 0.35, 0.55 + 0.05 * math.sin(t * 2))
        halo.add_color_stop_rgba(1, 1, 0.5, 0.3, 0)
        ctx.set_source(halo)
        ctx.paint()
        sol = cairo.RadialGradient(sx, sy - 40, 10, sx, sy, sr)
        sol.add_color_stop_rgb(0, *hx("#FFF6C8"))
        sol.add_color_stop_rgb(0.7, *hx("#FFD25A"))
        sol.add_color_stop_rgb(1, *hx("#FFB23C"))
        ctx.arc(sx, sy, sr, 0, 2 * math.pi)
        ctx.set_source(sol)
        ctx.fill()
    else:
        for x, y, r, ph in _estrellas():
            a = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * 3 + ph))
            ctx.arc(x, y, r, 0, 2 * math.pi)
            ctx.set_source_rgba(0.9, 0.95, 1, a)
            ctx.fill()
        mx, my, mr = 760, 520, 100
        halo = cairo.RadialGradient(mx, my, mr, mx, my, mr * 4)
        halo.add_color_stop_rgba(0, 0.7, 0.8, 1, 0.35)
        halo.add_color_stop_rgba(1, 0.4, 0.5, 1, 0)
        ctx.set_source(halo)
        ctx.paint()
        ctx.arc(mx, my, mr, 0, 2 * math.pi)
        ctx.set_source_rgb(*hx("#EEF2FF"))
        ctx.fill()
        for cx, cy, cr in ((735, 495, 22), (790, 545, 15), (772, 488, 9)):
            ctx.arc(cx, cy, cr, 0, 2 * math.pi)
            ctx.set_source_rgba(0.75, 0.8, 0.92, 0.8)
            ctx.fill()
    cols = (["#A03C78", "#5E1F68", "#2E1040"] if dia else ["#1E2E5E", "#121D45", "#080F2A"])
    _montana(ctx, _cresta(1, 1200, 330, True), hx(cols[0]))
    _montana(ctx, _cresta(2, 1240, 250, True), hx(cols[1]))
    _montana(ctx, _cresta(3, 1262, 150, False), hx(cols[2]))
    # mar
    g = cairo.LinearGradient(0, HZ, 0, 1920)
    for o, c in ([(0, "#4A1C5C"), (1, "#12061F")] if dia else [(0, "#0E1C44"), (1, "#03060F")]):
        g.add_color_stop_rgb(o, *hx(c))
    ctx.rectangle(0, HZ, 1080, 1920 - HZ)
    ctx.set_source(g)
    ctx.fill()
    rx = 540 if dia else 760
    col = (1, 0.8, 0.35) if dia else (0.85, 0.9, 1)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for k in range(30):
        y = HZ + 18 + k * 21 + 4 * math.sin(t * 1.3 + k)
        w = (330 if dia else 200) * (1 - k / 42) + 50 * math.sin(t * 2.1 + k * 1.7)
        off = 26 * math.sin(t * 1.6 + k * 2.3)
        ctx.move_to(rx - w / 2 + off, y)
        ctx.line_to(rx + w / 2 + off, y)
        ctx.set_line_width(7 + 4 * (k / 30))
        ctx.set_source_rgba(*col, 0.75 * (1 - k / 32))
        ctx.stroke()
    if dia:
        ctx.set_line_width(7)
        for i in range(3):
            x = (180 + 55 * t + i * 120) % 1240 - 80
            y = 640 + i * 55 + 9 * math.sin(t * 3 + i)
            f = 14 * math.sin(t * 9 + i * 2)
            ctx.move_to(x - 30, y - 6 - f)
            ctx.curve_to(x - 18, y - 16 - f, x - 6, y - 8, x, y)
            ctx.curve_to(x + 6, y - 8, x + 18, y - 16 - f, x + 30, y - 6 - f)
            ctx.set_source_rgb(*hx("#2A0E36"))
            ctx.stroke()


@functools.lru_cache(maxsize=4)
def paisaje_rgb(t_fijo, modo="dia"):
    s, c = lienzo()
    paisaje(c, t_fijo, modo)
    return a_rgb(s)


def paisaje_frame(t, modo="dia"):
    s, c = lienzo()
    paisaje(c, t, modo)
    return a_rgb(s)


# ------------------------------------------------------------------ título amarillo
TITULO = "¿CÓMO FUNCIONA\nTU PANTALLA?"
TIT_XY = (540, 275)


def titulo(ctx, t, s=1.0, alpha=1.0, rot=0.0):
    respira = 1 + 0.012 * math.sin(t * 2.4)
    cartel(ctx, TITULO, TIT_XY[0], TIT_XY[1], 80, s=s * respira, alpha=alpha, rot=rot, pad=(64, 30))


# ------------------------------------------------------------------ zoom a subpíxeles
COLS = np.array([ROJO_SP, VERDE_SP, AZUL_SP], np.float32)
COLS = np.array([[1.0, 0.12, 0.09], [0.14, 1.0, 0.26], [0.2, 0.42, 1.0]], np.float32)


def smooth(a, c, x):
    x = clamp((x - a) / (c - a))
    return x * x * (3 - 2 * x)


def zoom_sub(src, cx, cy, z, emph=(1, 1, 1), off=0.07, fila=None, fila_k=0.0):
    """Vista ampliada de `src` centrada en (cx, cy). A partir de ~6x aparecen los subpíxeles RGB."""
    if z <= 1.0005 and cx == W / 2 and cy == H / 2:
        return src
    Hs, Ws = src.shape[:2]
    M = np.float32([[z, 0, W / 2 - 0.5 - z * (cx - 0.5)], [0, z, H / 2 - 0.5 - z * (cy - 0.5)]])
    lin = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    k_near = smooth(2.0, 5.0, z)
    k_sub = smooth(5.0, 12.0, z)
    if k_near <= 0:
        return lin
    xs = cx + (np.arange(W, dtype=np.float64) - W / 2 + 0.5) / z
    ys = cy + (np.arange(H, dtype=np.float64) - H / 2 + 0.5) / z
    ix = np.clip(np.floor(xs).astype(np.int32), 0, Ws - 1)
    iy = np.clip(np.floor(ys).astype(np.int32), 0, Hs - 1)
    near = src[iy][:, ix].astype(np.float32) / 255
    out = lin.astype(np.float32) / 255 * (1 - k_near) + near * k_near
    if k_sub > 0:
        fx = (xs - np.floor(xs)).astype(np.float32)
        fy = (ys - np.floor(ys)).astype(np.float32)
        c = np.minimum((fx * 3).astype(np.int32), 2)
        sxp = fx * 3 - c
        aa_x = 1.3 / max(z / 3, 1e-3)
        mx = np.clip((np.minimum(sxp, 1 - sxp) - 0.13) / aa_x + 0.5, 0, 1)
        aa_y = 1.3 / z
        my = np.clip((np.minimum(fy, 1 - fy) - 0.05) / aa_y + 0.5, 0, 1)
        mask = my[:, None] * mx[None, :]
        idx = np.broadcast_to(c[None, :, None], (H, W, 1))
        I = np.take_along_axis(near, idx, axis=2)[..., 0]
        e = np.asarray(emph, np.float32)
        I = I * e[c][None, :]
        if fila is not None and fila_k > 0:
            I = I * np.where(iy == fila, 1.0, 1 - 0.75 * fila_k).astype(np.float32)[:, None]
        lvl = off + (1 - off) * I
        sub = 1.35 * lvl[..., None] * COLS[c][None, :, :] * mask[..., None]
        small = cv2.resize(sub, (W // 3, H // 3), interpolation=cv2.INTER_AREA)
        g = cv2.GaussianBlur(small, (0, 0), max(1.0, z / 14))
        sub = sub + 0.6 * cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)
        out = out * (1 - k_sub) + sub * k_sub
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def zoom_lineal(rgb, s, cx, cy):
    M = np.float32([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]])
    return cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def zexp(t, t0, d, z0, z1, kind="inout"):
    return math.exp(lerp(math.log(z0), math.log(z1), prog(t, t0, d, kind)))


# ------------------------------------------------------------------ piezas
def dedo(ctx, x, y, ang=0.0, s=1.0, alpha=1.0, largo=1500, sombra=0.0):
    """Dedo índice visto del lado de la uña; (x, y) es la punta."""
    if alpha <= 0.01:
        return
    if sombra > 0:
        g = cairo.RadialGradient(x + 18 * s, y + 30 * s, 5, x + 18 * s, y + 30 * s, 150 * s)
        g.add_color_stop_rgba(0, 0, 0, 0, 0.45 * sombra)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(g)
        ctx.paint()
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(ang))
    ctx.scale(s, s)
    ctx.push_group()
    w = 196
    r = w / 2

    def silueta():
        ctx.new_path()
        ctx.move_to(-r, largo)
        ctx.line_to(-r, r)
        ctx.arc(0, r, r, math.pi, 2 * math.pi)
        ctx.line_to(r, largo)
        ctx.close_path()

    silueta()
    g = cairo.LinearGradient(-r, 0, r, 0)
    g.add_color_stop_rgb(0, *hx("#C98466"))
    g.add_color_stop_rgb(0.3, *hx("#F0B593"))
    g.add_color_stop_rgb(0.62, *hx("#F7C6A6"))
    g.add_color_stop_rgb(1, *hx("#B9765A"))
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    rrect(ctx, -0.32 * w, 26, 0.64 * w, 236, 56)
    g = cairo.LinearGradient(0, 26, 0, 262)
    g.add_color_stop_rgb(0, *hx("#FCE3D8"))
    g.add_color_stop_rgb(1, *hx("#EDB7A6"))
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()
    rrect(ctx, -0.2 * w, 48, 0.12 * w, 120, 12)
    ctx.set_source_rgba(1, 1, 1, 0.55)
    ctx.fill()
    ctx.set_line_width(5)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for yy, k in ((440, 0.24), (478, 0.18), (800, 0.26), (838, 0.2)):
        ctx.move_to(-k * w, yy)
        ctx.curve_to(-0.08 * w, yy + 14, 0.08 * w, yy + 14, k * w, yy)
        ctx.set_source_rgba(*INK, 0.55)
        ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def particulas(ctx, t, src, dst, t0, t1, n=26, color=CIAN, rate=1.6, curva=110, r=8, seed=3):
    """Chispitas que viajan de src a dst entre t0 y t1."""
    if t < t0 or t > t1 + 0.7:
        return
    rr = rng(seed)
    ph = rr.uniform(0, 1, n)
    lado = rr.uniform(-1, 1, n)
    for i in range(n):
        q = (t - t0) * rate + ph[i]
        k = math.floor(q)
        f = q - k
        nacio = t0 + (k - ph[i]) / rate
        if nacio < t0 - 1e-6 or nacio > t1:
            continue
        x0, y0 = src
        x1, y1 = dst
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1
        cxp, cyp = mx - dy / L * curva * lado[i], my + dx / L * curva * lado[i]
        e = f
        x = (1 - e) ** 2 * x0 + 2 * (1 - e) * e * cxp + e * e * x1
        y = (1 - e) ** 2 * y0 + 2 * (1 - e) * e * cyp + e * e * y1
        a = math.sin(math.pi * f)
        ctx.arc(x, y, r * 2.6, 0, 2 * math.pi)
        ctx.set_source_rgba(*color, 0.18 * a)
        ctx.fill()
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.set_source_rgba(min(1, color[0] + 0.5), min(1, color[1] + 0.3), min(1, color[2] + 0.3), 0.95 * a)
        ctx.fill()


def neon_linea(ctx, x0, y0, x1, y1, color=CIAN, a=1.0, w=5):
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for lw, al in ((w * 5, 0.10), (w * 2.4, 0.22), (w, 0.9)):
        ctx.move_to(x0, y0)
        ctx.line_to(x1, y1)
        ctx.set_line_width(lw)
        ctx.set_source_rgba(*color, al * a)
        ctx.stroke()


def punto_brillo(ctx, x, y, r, color=CIAN, a=1.0):
    g = cairo.RadialGradient(x, y, 0, x, y, r * 4)
    g.add_color_stop_rgba(0, *color, 0.55 * a)
    g.add_color_stop_rgba(1, *color, 0)
    ctx.set_source(g)
    ctx.arc(x, y, r * 4, 0, 2 * math.pi)
    ctx.fill()
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source_rgba(min(1, color[0] + 0.6), min(1, color[1] + 0.4), min(1, color[2] + 0.4), a)
    ctx.fill()


def mira(ctx, x, y, p, color=hx("#FF4D4D"), tam=62):
    """Mira que se cierra sobre (x, y). p de 0 a 1."""
    if p <= 0:
        return
    e = ease(p, "out")
    s = lerp(3.2, 1.0, e)
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(lerp(80, 0, e)))
    a = clamp(p * 3)
    L = tam * s
    ctx.set_line_width(9)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for sx_, sy_ in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        ctx.move_to(sx_ * L, sy_ * (L - 26))
        ctx.line_to(sx_ * L, sy_ * L)
        ctx.line_to(sx_ * (L - 26), sy_ * L)
        ctx.set_source_rgba(*INK, a)
        ctx.set_line_width(16)
        ctx.stroke_preserve()
        ctx.set_source_rgba(*color, a)
        ctx.set_line_width(9)
        ctx.stroke()
    if p >= 1:
        q = clamp((p - 1) * 2.5)
        ctx.arc(0, 0, lerp(10, 90, q), 0, 2 * math.pi)
        ctx.set_source_rgba(*color, 0.7 * (1 - q))
        ctx.set_line_width(6)
        ctx.stroke()
    ctx.restore()


def marca_robo(ctx, x, y, t, k, r=26):
    """Cruce al que le falta carga: se ve 'a través' del dedo."""
    if k <= 0.01:
        return
    ctx.arc(x, y, r * 0.5, 0, 2 * math.pi)
    ctx.set_source_rgba(0.05, 0.08, 0.12, 0.85 * k)
    ctx.fill_preserve()
    ctx.set_source_rgba(*CIAN, 0.5 * k)
    ctx.set_line_width(3)
    ctx.stroke()
    pul = 0.5 + 0.5 * math.sin(t * 9)
    ctx.arc(x, y, r + 6 * pul, 0, 2 * math.pi)
    ctx.set_source_rgba(*INK, 0.8 * k)
    ctx.set_line_width(11)
    ctx.stroke_preserve()
    ctx.set_source_rgba(*hx("#FF4D4D"), k)
    ctx.set_line_width(6)
    ctx.stroke()


def flecha(ctx, x0, y0, x1, y1, t, color=BLANCO, w=16, curva=0.25, alpha=1.0, bote=True):
    """Flecha curva dibujada a mano (de x0,y0 hacia x1,y1)."""
    if alpha <= 0.01:
        return
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    if bote:
        k = 14 * math.sin(t * 9)
        x1 += ux * k
        y1 += uy * k
        x0 += ux * k
        y0 += uy * k
    cx, cy = (x0 + x1) / 2 - uy * L * curva, (y0 + y1) / 2 + ux * L * curva
    tx, ty = x1 - cx, y1 - cy
    tl = math.hypot(tx, ty)
    tx, ty = tx / tl, ty / tl
    hl = 46
    for lw, col in ((w + 12, INK), (w, color)):
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.move_to(x0, y0)
        ctx.curve_to(cx, cy, cx, cy, x1 - tx * 6, y1 - ty * 6)
        ctx.set_line_width(lw)
        ctx.set_source_rgba(*col, alpha)
        ctx.stroke()
        for sg in (1, -1):
            ax_ = x1 - tx * hl + (-ty) * sg * hl * 0.62
            ay_ = y1 - ty * hl + tx * sg * hl * 0.62
            ctx.move_to(x1, y1)
            ctx.line_to(ax_, ay_)
            ctx.stroke()


def cerebro(ctx, x, y, s, brillo=0.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(max(s, 1e-4), max(s, 1e-4))
    if brillo > 0:
        g = cairo.RadialGradient(0, 0, 60, 0, 0, 420)
        g.add_color_stop_rgba(0, *AMARILLO, 0.75 * brillo)
        g.add_color_stop_rgba(1, *AMARILLO, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, 420, 0, 2 * math.pi)
        ctx.fill()
    blobs = [(-95, -40, 92), (-20, -78, 98), (70, -60, 92), (120, 15, 80), (55, 60, 88), (-45, 55, 90),
             (-120, 25, 78)]
    for bx, by, br in blobs:
        ctx.arc(bx, by, br + 8, 0, 2 * math.pi)
        ctx.set_source_rgb(*INK)
        ctx.fill()
    ctx.arc(95, 112, 52, 0, 2 * math.pi)
    ctx.fill()
    rrect(ctx, 30, 120, 50, 120, 22)
    ctx.fill()
    ctx.arc(95, 112, 44, 0, 2 * math.pi)
    ctx.set_source_rgb(*hx("#E58BA6"))
    ctx.fill()
    rrect(ctx, 38, 120, 34, 112, 16)
    ctx.set_source_rgb(*hx("#E58BA6"))
    ctx.fill()
    for bx, by, br in blobs:
        ctx.arc(bx, by, br, 0, 2 * math.pi)
        ctx.set_source_rgb(*hx("#FF9EBB"))
        ctx.fill()
    ctx.set_source_rgba(*INK, 0.85)
    ctx.set_line_width(7)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    curvas = [(-170, -20, -120, -70, -60, 0, -20, -40), (-60, -140, -40, -90, 20, -120, 30, -60),
              (40, -130, 90, -100, 60, -50, 120, -40), (-150, 60, -100, 20, -60, 90, -10, 40),
              (20, 0, 60, 40, 100, -10, 150, 30), (-40, 110, 0, 80, 40, 130, 80, 90),
              (-100, -110, -80, -60, -130, -40, -150, -10)]
    for c in curvas:
        ctx.move_to(c[0], c[1])
        ctx.curve_to(*c[2:])
        ctx.stroke()
    ctx.restore()


# ------------------------------------------------------------------ celular, teclado y comentarios
def telefono(ctx, cx, cy, s, contenido, t, brillo=0.0):
    sw, sh = 1080 * s, 1920 * s
    bz = 24
    ctx.save()
    # sombra
    g = cairo.RadialGradient(cx, cy + sh * 0.52, 20, cx, cy + sh * 0.52, sw * 0.8)
    g.add_color_stop_rgba(0, 0, 0, 0, 0.5)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(g)
    ctx.paint()
    rrect(ctx, cx - sw / 2 - bz, cy - sh / 2 - bz, sw + 2 * bz, sh + 2 * bz, 70 * s + bz)
    ctx.set_source_rgb(*hx("#121418"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    rrect(ctx, cx - sw / 2 - bz + 6, cy - sh / 2 - bz + 6, sw + 2 * bz - 12, sh + 2 * bz - 12, 70 * s + bz - 6)
    ctx.set_source_rgba(1, 1, 1, 0.12)
    ctx.set_line_width(3)
    ctx.stroke()
    for yy, hh in ((-0.28, 0.08), (-0.16, 0.08)):
        rrect(ctx, cx - sw / 2 - bz - 7, cy + yy * sh, 9, hh * sh, 4)
        ctx.set_source_rgb(*hx("#2A2D33"))
        ctx.fill()
    rrect(ctx, cx + sw / 2 + bz - 2, cy - 0.22 * sh, 9, 0.12 * sh, 4)
    ctx.fill()
    ctx.save()
    rrect(ctx, cx - sw / 2, cy - sh / 2, sw, sh, 70 * s)
    ctx.clip()
    ctx.translate(cx - sw / 2, cy - sh / 2)
    ctx.scale(s, s)
    contenido(ctx)
    if brillo > 0:
        ctx.rectangle(0, 0, 1080, 1920)
        ctx.set_source_rgba(1, 1, 1, brillo)
        ctx.fill()
    ctx.arc(540, 56, 22, 0, 2 * math.pi)
    ctx.set_source_rgb(0.02, 0.02, 0.03)
    ctx.fill()
    ctx.restore()
    ctx.restore()


def tel_a_pantalla(cx, cy, s, lx, ly):
    return cx - 540 * s + lx * s, cy - 960 * s + ly * s


TECLAS = {}


def _layout_teclado():
    y1, y2, y3, y4, kh = 1440, 1560, 1680, 1800, 104
    for i, ch in enumerate("QWERTYUIOP"):
        TECLAS[ch] = (i * 108 + 8, y1, 92, kh, ch, False)
    for i, ch in enumerate("ASDFGHJKLÑ"):
        TECLAS[ch] = (i * 108 + 8, y2, 92, kh, ch, False)
    TECLAS["shift"] = (8, y3, 142, kh, "⇧", True)
    x0 = (1080 - 7 * 108) / 2
    for i, ch in enumerate("ZXCVBNM"):
        TECLAS[ch] = (x0 + i * 108 + 8, y3, 92, kh, ch, False)
    TECLAS["del"] = (930, y3, 142, kh, "⌫", True)
    TECLAS["123"] = (8, y4, 150, kh, "123", True)
    TECLAS[","] = (166, y4, 92, kh, ",", False)
    TECLAS[" "] = (266, y4, 460, kh, "espacio", True)
    TECLAS["."] = (734, y4, 92, kh, ".", False)
    TECLAS["enviar"] = (834, y4, 238, kh, "enviar", True)


_layout_teclado()


def centro_tecla(ch):
    x, y, w, h = TECLAS[ch][:4]
    return x + w / 2, y + h / 2


def teclado(ctx, y_off=0.0, pulsada=None, pulso=0.0):
    ctx.save()
    ctx.translate(0, y_off)
    ctx.rectangle(0, 1420, 1080, 520)
    ctx.set_source_rgb(*hx("#202124"))
    ctx.fill()
    for k, (x, y, w, h, lab, esp) in TECLAS.items():
        rrect(ctx, x, y, w, h, 16)
        base = hx("#333438") if esp else hx("#55575C")
        if k == pulsada:
            base = tuple(lerp(c, 0.85, pulso) for c in base)
        ctx.set_source_rgb(*base)
        ctx.fill()
        size = 34 if len(lab) > 2 else 52
        texto(ctx, lab, x + w / 2, y + h / 2, size, fill=BLANCO, stroke=None, fam=UI, bold=True)
    ctx.restore()


def globo_tecla(ctx, ch, p):
    if p <= 0:
        return
    x, y, w, h = TECLAS[ch][:4]
    s = pop(p, 0, 1)
    ctx.save()
    ctx.translate(x + w / 2, y)
    ctx.scale(s, s)
    rrect(ctx, -78, -230, 156, 250, 30)
    ctx.set_source_rgb(*hx("#6A6C72"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()
    texto(ctx, ch, 0, -125, 120, fill=BLANCO, stroke=None, fam=UI, bold=True)
    ctx.restore()


CAMPO = (40, 1286, 1000, 108)


def comentarios_ui(ctx, t, escrito="", teclado_p=0.0, campo_brillo=0.0, pulsada=None, pulso=0.0, cursor=True,
                   video_t=0.0, globo=None):
    paisaje(ctx, video_t, "dia")
    ctx.rectangle(0, 0, 1080, 1920)
    ctx.set_source_rgba(0, 0, 0, 0.45)
    ctx.fill()
    rrect(ctx, 0, 620, 1080, 1400, 52)
    ctx.set_source_rgb(*hx("#17181A"))
    ctx.fill()
    rrect(ctx, 490, 644, 100, 12, 6)
    ctx.set_source_rgb(*hx("#5A5C60"))
    ctx.fill()
    texto(ctx, "Comentarios", 60, 735, 54, fill=BLANCO, stroke=None, fam=UI, bold=True, ax=0)
    texto(ctx, "2,4 mil", 420, 735, 44, fill=hx("#9EA1A6"), stroke=None, fam=UI, ax=0)
    texto(ctx, "✕", 1010, 735, 52, fill=BLANCO, stroke=None, fam=UI)
    ctx.rectangle(0, 790, 1080, 2)
    ctx.set_source_rgb(*hx("#2C2D30"))
    ctx.fill()
    avs = ["#E57373", "#64B5F6", "#81C784", "#FFB74D", "#BA68C8"]
    for i, y in enumerate((860, 1010, 1160, 1460, 1610, 1760)):
        ctx.arc(100, y + 10, 42, 0, 2 * math.pi)
        ctx.set_source_rgb(*hx(avs[i % 5]))
        ctx.fill()
        for (bx, by, bw, bh, col) in ((165, y - 30, 220, 22, "#6A6C70"), (165, y + 8, 720 - 90 * (i % 3), 26, "#3C3E42"),
                                      (165, y + 46, 480 + 60 * (i % 2), 26, "#3C3E42")):
            rrect(ctx, bx, by, bw, bh, bh / 2)
            ctx.set_source_rgb(*hx(col))
            ctx.fill()
    x, y, w, h = CAMPO
    rrect(ctx, x, y, w, h, h / 2)
    ctx.set_source_rgb(*hx("#2A2B2E"))
    ctx.fill_preserve()
    if campo_brillo > 0:
        ctx.set_source_rgba(*CIAN, campo_brillo)
        ctx.set_line_width(6)
        ctx.stroke()
    else:
        ctx.new_path()
    if escrito:
        xa = texto(ctx, escrito, x + 52, y + h / 2, 58, fill=BLANCO, stroke=None, fam=UI, ax=0)
    else:
        texto(ctx, "Agrega un comentario...", x + 52, y + h / 2, 46, fill=hx("#8E9196"), stroke=None, fam=UI, ax=0)
        xa = 0
    if cursor and (t * 2) % 1 < 0.55:
        ctx.rectangle(x + 52 + xa + 6, y + 24, 5, h - 48)
        ctx.set_source_rgb(*CIAN)
        ctx.fill()
    if teclado_p > 0:
        teclado(ctx, y_off=(1 - ease(teclado_p, "out")) * 560, pulsada=pulsada, pulso=pulso)
        if globo:
            globo_tecla(ctx, *globo)


# ------------------------------------------------------------------ cuadrícula táctil
def cuadricula(ctx, xs, ys, t, a=1.0, pulsos=True, nodos=True, apagado=None, apag_k=0.0, escaneo=None,
               lw=5, color=CIAN, vel=420):
    x0, x1 = xs[0] - 60, xs[-1] + 60
    y0, y1 = ys[0] - 60, ys[-1] + 60
    for x in xs:
        neon_linea(ctx, x, y0, x, y1, color, 0.55 * a, lw)
    for j, y in enumerate(ys):
        hl = 0.0
        if escaneo is not None:
            hl = max(0.0, 1 - abs(escaneo - j) * 1.4)
        neon_linea(ctx, x0, y, x1, y, color if hl < 0.5 else BLANCO, (0.55 + 0.45 * hl) * a, lw * (1 + hl * 0.6))
    if pulsos:
        L = x1 - x0
        for j, y in enumerate(ys):
            for k in range(2):
                px = x0 + ((t * vel + j * 137 + k * L / 2) % L)
                punto_brillo(ctx, px, y, 7, color, 0.9 * a)
        Lv = y1 - y0
        for i, x in enumerate(xs):
            py = y0 + ((t * vel * 0.8 + i * 211) % Lv)
            punto_brillo(ctx, x, py, 6, color, 0.6 * a)
    if nodos:
        for j, y in enumerate(ys):
            for i, x in enumerate(xs):
                k = 1.0
                if apagado == (i, j):
                    k = 1 - 0.8 * apag_k
                hl = 0.0
                if escaneo is not None:
                    hl = max(0.0, 1 - abs(escaneo - j) * 1.4)
                col = color
                if apagado == (i, j) and apag_k > 0.5:
                    col = tuple(lerp(c, r_, apag_k) for c, r_ in zip(color, hx("#FF4D4D")))
                punto_brillo(ctx, x, y, 9 + 5 * hl, col, a * k * (0.85 + 0.15 * math.sin(t * 5 + i + j)))


# ------------------------------------------------------------------ escenas
S = [0.0, b(1), b(2), b(3), b(4), b(5), b(8), b(9), b(10), b(11), b(12), b(13), b(15), b(16)]
S = [S[0]] + [x - 0.08 for x in S[1:]]


def escena_de(t):
    i = 0
    for k, s0 in enumerate(S):
        if t >= s0:
            i = k
    return i


# ---- 0. gancho
def sc_gancho(t):
    s, ctx = lienzo()
    paisaje(ctx, t, "dia")
    # destello de barrido (anticipo)
    td = b(0, "dibujó")
    if td <= t < td + 0.35:
        y = (t - td) / 0.35 * 1920
        g = cairo.LinearGradient(0, y - 90, 0, y + 10)
        g.add_color_stop_rgba(0, 1, 1, 1, 0)
        g.add_color_stop_rgba(1, 1, 1, 1, 0.35)
        ctx.rectangle(0, y - 90, 1080, 100)
        ctx.set_source(g)
        ctx.fill()
    titulo(ctx, t)
    contador(ctx, t)
    return a_rgb(s)


def contador(ctx, t, alpha=1.0, esc=1.0):
    n = int(min(t, S[1]) * 60)
    t100 = b(0, "100")
    k = bump(t, t100, 0.35, 0.28) * esc
    if k <= 0.01 or alpha <= 0.01:
        return
    ctx.save()
    ctx.translate(540, 660)
    ctx.scale(k, k)
    ctx.push_group()
    rrect(ctx, -250, -115, 500, 230, 50)
    ctx.set_source_rgba(0.04, 0.03, 0.08, 0.72)
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.85)
    ctx.set_line_width(5)
    ctx.stroke()
    texto(ctx, f"{n}", 0, -18, 140, fill=BLANCO, sw=9)
    texto(ctx, "REDIBUJOS", 0, 72, 44, fill=CIAN, stroke=None)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()
    if t >= t100:
        cartel(ctx, "+100", 790, 545, 64, box=BLANCO, fg=INK, s=pop(t, t100, 0.3) * esc, rot=8, alpha=alpha)


# ---- 1. barrido fila por fila
T_RED = b(1, "redibuja")
T_RAP = b(1, "rápido")
BARRIDOS = [(T_RED, T_RAP - T_RED + 0.05, "noche", "dia")]
_t = T_RAP + 0.05
for i, d in enumerate((0.75, 0.55, 0.45)):
    nuevo = "dia" if i % 2 == 0 else "noche"
    viejo = "noche" if nuevo == "dia" else "dia"
    BARRIDOS.append((_t, d, nuevo, viejo))
    _t += d


def _img(modo, t, suave):
    im = paisaje_frame(t, "dia" if modo == "dia" else "noche")
    if modo == "noche" and suave > 0:
        dia = paisaje_frame(t, "dia")
        im = (im.astype(np.float32) * (1 - suave) + dia.astype(np.float32) * suave).astype(np.uint8)
    return im


def sc_barrido(t):
    FILA = 24
    actual = None
    for k, (t0, d, nuevo, viejo) in enumerate(BARRIDOS):
        if t >= t0:
            actual = (k, t0, d, nuevo, viejo)
    if actual is None or t >= actual[1] + actual[2]:
        estado = "dia" if actual is None else actual[3]
        k = -1 if actual is None else actual[0]
        suave = 0.0 if k <= 0 else min(0.55, 0.18 * k)
        img = _img(estado, t, suave)
        y = None
    else:
        k, t0, d, nuevo, viejo = actual
        suave = 0.0 if k == 0 else min(0.55, 0.18 * k)
        p = (t - t0) / d
        filas = 1920 // FILA
        fila = int(p * filas)
        y = fila * FILA
        a = _img(nuevo, t, suave)
        bb = _img(viejo, t, suave)
        img = bb.copy()
        img[:y] = a[:y]
    s, ctx = desde_rgb(img)
    # líneas de fila
    al = 0.12 * prog(t, S[1], 0.6)
    if al > 0:
        ctx.set_source_rgba(0, 0, 0, al)
        for yy in range(0, 1920, FILA):
            ctx.rectangle(0, yy, 1080, 2)
        ctx.fill()
    if y is not None:
        lento = actual[0] == 0
        h = FILA if lento else 70
        g = cairo.LinearGradient(0, y - h * 3, 0, y + FILA)
        g.add_color_stop_rgba(0, *CIAN, 0)
        g.add_color_stop_rgba(0.75, *CIAN, 0.35)
        g.add_color_stop_rgba(1, 1, 1, 1, 0.95)
        ctx.rectangle(0, y - h * 3, 1080, h * 3 + FILA)
        ctx.set_source(g)
        ctx.fill()
        ctx.rectangle(0, y, 1080, FILA)
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.fill()
    titulo(ctx, t)
    if t < S[1] + 0.4:
        q = prog(t, S[1], 0.4, "in")
        contador(ctx, t, alpha=1 - q, esc=1 - 0.6 * q)
    # velocidad
    if t < T_RAP:
        etiqueta_lenta(ctx, t, S[1] + 0.38, 99, "CÁMARA LENTA", y=530)
    else:
        txt = "MÁS RÁPIDO" if t < T_RAP + 1.3 else "VELOCIDAD REAL"
        etiqueta_lenta(ctx, t, T_RAP - 10, 99, txt, y=530)
    return a_rgb(s)


# ---- 2. zoom hasta los puntitos
ZC = (604, 1140)        # la montaña cruzando el sol: muchos colores juntos
Z_MAX = 46


def _src_dia():
    return paisaje_rgb(round(S[2], 2), "dia")


def _zoom_in_estado(t):
    t0 = S[2]
    t1 = b(2, "puntitos", fin=True) + 0.25
    z = zexp(t, t0, t1 - t0, 1.0, Z_MAX)
    q = prog(t, t0, t1 - t0)
    cx = lerp(540, ZC[0], min(1, q * 1.15))
    cy = lerp(960, ZC[1], min(1, q * 1.15))
    z *= 1 + 0.04 * clamp((t - t1) / 4)
    return z, cx, cy


def emph_colores(t):
    e = np.ones(3, np.float32)
    tr, tv, ta, tf = b(2, "rojo"), b(2, "verde"), b(2, "azul"), S[3]
    for k, t0, t1 in ((0, tr, tv), (1, tv, ta), (2, ta, tf)):
        if t0 - 0.05 <= t < t1 - 0.05:
            e[:] = 0.12
            e[k] = 1.0
    return e


def sc_zoom_in(t):
    z, cx, cy = _zoom_in_estado(t)
    fila_k = 0.0
    tf0, tf1 = b(2, "hilera"), b(2, "tres")
    if t >= tf0:
        fila_k = clamp((t - tf0) / 0.3) * (1 - clamp((t - tf1) / 0.3))
    img = zoom_sub(_src_dia(), cx, cy, z, emph=emph_colores(t), fila=int(cy), fila_k=fila_k)
    s, ctx = desde_rgb(img)
    titulo(ctx, t)
    if fila_k > 0.05:
        cartel(ctx, "1 FILA", 860, H / 2 - z * 0.5 - 70, 52, box=BLANCO, s=pop(t, tf0) , alpha=fila_k)
        flecha(ctx, 860, H / 2 - z * 0.5 - 20, 760, H / 2 - 4, t, alpha=fila_k, curva=-0.2, bote=False)
    for nombre, col, pal in (("ROJO", hx("#FF3B30"), "rojo"), ("VERDE", hx("#2DD455"), "verde"),
                             ("AZUL", hx("#2F6BFF"), "azul")):
        t0 = b(2, pal)
        t1 = S[3]
        if t0 <= t < t1 + 0.1:
            idx = ["rojo", "verde", "azul"].index(pal)
            x = 260 + idx * 280
            cartel(ctx, nombre, x, 1250, 64, box=col, fg=BLANCO, s=pop(t, t0))
    return a_rgb(s)


# ---- 3. un píxel y sus perillas
KEYS_RGB = [(S[3], (0.15, 0.15, 0.15)), (b(3, "prenderlos"), (1.0, 0.48, 0.06)), (b(3, "fuerte"), (0.7, 0.1, 1.0)),
            (b(3, "suave"), (0.12, 0.6, 1.0)), (S[4] - 0.35, (1.0, 1.0, 1.0))]


def rgb_en(t):
    v = np.array(KEYS_RGB[0][1])
    for (t0, c0), (t1, c1) in zip(KEYS_RGB, KEYS_RGB[1:]):
        if t >= t1:
            v = np.array(c1)
        elif t >= t0:
            v = np.array(c0)
    # suavizado: interpolar desde la clave anterior durante 0.45 s
    for i in range(1, len(KEYS_RGB)):
        t1, c1 = KEYS_RGB[i]
        c0 = KEYS_RGB[i - 1][1]
        if t1 <= t < t1 + 0.45:
            p = ease((t - t1) / 0.45)
            v = np.array(c0) * (1 - p) + np.array(c1) * p
    return v


def sc_perillas(t):
    t0 = S[3]
    if t < t0 + 0.3:
        z = zexp(t, t0, 0.3, Z_MAX * 1.04, Z_MAX * 9, "in")
        z0, cx, cy = _zoom_in_estado(t0)
        img = zoom_sub(_src_dia(), math.floor(cx) + 0.5, math.floor(cy) + 0.5, z)
        s, ctx = desde_rgb(img)
        q = prog(t, t0 + 0.15, 0.15)
        if q > 0:
            ctx.set_source_rgba(0.02, 0.03, 0.07, q)
            ctx.paint()
        titulo(ctx, t)
        return a_rgb(s)
    s, ctx = lienzo()
    fondo(ctx, t)
    v = rgb_en(t)
    ap = pop(t, t0 + 0.25, 0.4)
    ctx.save()
    ctx.translate(410, 770)
    ctx.scale(max(ap, 1e-4), max(ap, 1e-4))
    rrect(ctx, -230, -300, 460, 600, 40)
    ctx.set_source_rgb(0.03, 0.03, 0.05)
    ctx.fill_preserve()
    ctx.set_source_rgb(*hx("#3A4258"))
    ctx.set_line_width(6)
    ctx.stroke()
    for k in range(3):
        x = -195 + k * 136
        col = COLS[k]
        I = float(v[k])
        g = cairo.RadialGradient(x + 60, 0, 30, x + 60, 0, 330)
        g.add_color_stop_rgba(0, *col, 0.55 * I)
        g.add_color_stop_rgba(1, *col, 0)
        ctx.set_source(g)
        ctx.rectangle(-230, -300, 460, 600)
        ctx.fill()
        rrect(ctx, x, -270, 118, 540, 34)
        ctx.set_source_rgb(*(c * (0.1 + 0.9 * I) for c in col))
        ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.25 + 0.5 * I)
        ctx.set_line_width(4)
        ctx.stroke()
    ctx.restore()
    cartel(ctx, "1 PÍXEL", 410, 448, 50, box=BLANCO, s=ap)
    # de lejos
    ap2 = pop(t, t0 + 0.5, 0.4)
    flecha(ctx, 660, 770, 735, 770, t, alpha=clamp(ap2), curva=0, bote=True, w=14)
    ctx.save()
    ctx.translate(880, 770)
    ctx.scale(max(ap2, 1e-4), max(ap2, 1e-4))
    g = cairo.RadialGradient(0, 0, 100, 0, 0, 230)
    g.add_color_stop_rgba(0, *v, 0.5)
    g.add_color_stop_rgba(1, *v, 0)
    ctx.set_source(g)
    ctx.arc(0, 0, 230, 0, 2 * math.pi)
    ctx.fill()
    ctx.arc(0, 0, 118, 0, 2 * math.pi)
    ctx.set_source_rgb(*v)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.restore()
    cartel(ctx, "DE LEJOS", 880, 590, 44, box=BLANCO, s=ap2)
    # perillas
    for k in range(3):
        y = 1150 + k * 92
        ap3 = pop(t, t0 + 0.35 + 0.08 * k, 0.4)
        if ap3 <= 0:
            continue
        ctx.save()
        ctx.translate(540, y)
        ctx.scale(ap3, 1)
        rrect(ctx, -380, -14, 760, 28, 14)
        ctx.set_source_rgb(*hx("#1E2333"))
        ctx.fill()
        rrect(ctx, -380, -14, 760 * float(v[k]), 28, 14)
        ctx.set_source_rgb(*COLS[k])
        ctx.fill()
        kx = -380 + 760 * float(v[k])
        ctx.arc(kx, 0, 30, 0, 2 * math.pi)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(6)
        ctx.stroke()
        ctx.restore()
    titulo(ctx, t)
    return a_rgb(s)


# ---- 4. zoom out (con un cabello para comparar)
def sc_zoom_out(t):
    t0 = S[4]
    ts, tm = b(4, "separan"), b(4, "mezclados", fin=True)
    zs = Z_MAX * 1.12
    if t < ts:
        z = lerp(zs, Z_MAX, clamp((t - t0) / (ts - t0)))
    else:
        z = zexp(t, ts, tm - ts + 0.1, Z_MAX, 1.0)
    q = 1 - prog(t, ts, tm - ts + 0.1)
    cx, cy = lerp(540, ZC[0], q), lerp(960, ZC[1], q)
    img = zoom_sub(_src_dia(), cx, cy, z)
    s, ctx = desde_rgb(img)
    # cabello (~1,3 píxeles de ancho)
    tc = b(4, "chiquitos")
    if t >= tc:
        a = clamp((t - tc) / 0.3) * smooth(6, 14, z)
        if a > 0.01:
            pts = [(ZC[0] - 60 + k * 6, ZC[1] - 32 + k * 3 + 0.8 * math.sin(k * 0.35)) for k in range(-40, 60)]
            entra = prog(t, tc, 0.5, "out")
            ctx.save()
            ctx.translate(-(1 - entra) * 900, 0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            for lw, col, al in ((1.3 * z + 8, INK, 1.0), (1.3 * z, hx("#6B4426"), 1.0), (0.35 * z, hx("#A97A52"), 0.8)):
                for i, (px, py) in enumerate(pts):
                    X, Y = (px - cx) * z + W / 2, (py - cy) * z + H / 2
                    (ctx.move_to if i == 0 else ctx.line_to)(X, Y)
                ctx.set_line_width(lw)
                ctx.set_source_rgba(*col, a * al)
                ctx.stroke()
            ctx.restore()
            cartel(ctx, "UN CABELLO", 400, 1010, 60, box=BLANCO, s=pop(t, tc + 0.35), alpha=a, rot=24)
    titulo(ctx, t)
    return a_rgb(s)


# ---- 5. el amarillo
YZ = (200, 275)     # zona amarilla limpia (margen izquierdo del cartel, sin letras)


def _base_amarillo(t, flecha_a=0.0, wig=0.0):
    s, ctx = lienzo()
    paisaje(ctx, t, "dia")
    titulo(ctx, t, rot=wig)
    if flecha_a > 0:
        flecha(ctx, 820, 640, 760, 445, t, alpha=flecha_a, curva=-0.3)
    return a_rgb(s)


def sc_amarillo(t):
    tm = b(5, "Mira")
    tz0 = b(6) - 0.05
    tz1 = b(6, "color", fin=True)
    tzo = b(7) - 0.05
    tb_ = b(7, "inventando") - 0.35
    if t < tb_:
        fa = clamp((t - tm) / 0.2) * (1 - clamp((t - tz0) / 0.2))
        wig = 4 * math.sin((t - tm) * 18) * math.exp(-(t - tm) * 4) if t >= tm else 0
        base = _base_amarillo(t if t < tz0 else tz0, fa, wig)
        if t < tz0:
            z = 1.0 + 0.06 * prog(t, tm, 0.6)
            img = zoom_lineal(base, z, 540, 700)
        elif t < tzo:
            z = zexp(t, tz0, tz1 - tz0, 1.06, 40)
            q = prog(t, tz0, tz1 - tz0)
            z *= 1 + 0.05 * clamp((t - tz1) / 2.5)
            cx, cy = lerp(540, YZ[0], min(1, q * 1.2)), lerp(700, YZ[1], min(1, q * 1.2))
            img = zoom_sub(base, cx, cy, z)
        else:
            z = zexp(t, tzo, tb_ - tzo, 40, 1.0)
            q = 1 - prog(t, tzo, tb_ - tzo)
            cx, cy = lerp(540, YZ[0], q), lerp(960, YZ[1], q)
            img = zoom_sub(base, cx, cy, z)
        s, ctx = desde_rgb(img)
        tr, tv = b(6, "rojos"), b(6, "verdes")
        sal = 1 - clamp((t - tzo) / 0.2)
        if t >= tr and sal > 0:
            cartel(ctx, "ROJO", 270, 1250, 70, box=hx("#FF3B30"), fg=BLANCO, s=pop(t, tr), alpha=sal)
        if t >= tv and sal > 0:
            texto(ctx, "+", 540, 1250, 110, fill=BLANCO, sw=8, alpha=sal * clamp((t - tv) / 0.15))
            cartel(ctx, "VERDE", 800, 1250, 70, box=hx("#2DD455"), fg=BLANCO, s=pop(t, tv), alpha=sal)
        tj = b(6, "juntos")
        if t >= tj and sal > 0:
            cartel(ctx, "AZUL: APAGADO", 540, 1080, 46, box=hx("#1B2240"), fg=hx("#6E8CFF"), s=pop(t, tj), alpha=sal)
        return a_rgb(s)
    # rojo + verde -> cerebro -> amarillo
    s, ctx = lienzo()
    fondo(ctx, t)
    tc = b(7, "cerebro")
    tin = b(7, "inventando")
    T_MEZCLA = tb_ + 0.75
    q = prog(t, tb_ + 0.15, T_MEZCLA - tb_ - 0.15, "in")
    for x0, col in ((180, hx("#FF3B30")), (900, hx("#2DD455"))):
        x = lerp(x0, 540, q)
        y = 760 - 120 * math.sin(math.pi * q)
        r = lerp(95, 30, q)
        if q < 0.98:
            g = cairo.RadialGradient(x, y, r * 0.5, x, y, r * 2.4)
            g.add_color_stop_rgba(0, *col, 0.6)
            g.add_color_stop_rgba(1, *col, 0)
            ctx.set_source(g)
            ctx.arc(x, y, r * 2.4, 0, 2 * math.pi)
            ctx.fill()
            ctx.arc(x, y, r, 0, 2 * math.pi)
            ctx.set_source_rgb(*col)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(7)
            ctx.stroke()
    br = clamp((t - T_MEZCLA) / 0.3)
    cerebro(ctx, 540, 780, 1.25 * pop(t, tb_ + 0.05, 0.4) * bump(t, T_MEZCLA, 0.35, 0.12) * bump(t, tc, 0.3, 0.08),
            brillo=br)
    if t >= T_MEZCLA:
        cartel(ctx, "AMARILLO", 540, 1180, 84, box=AMARILLO, s=pop(t, T_MEZCLA + 0.05), rot=-3)
    titulo(ctx, t)
    return a_rgb(s)


# ---- 6. también te siente
TEL = (540, 800, 0.56)


def sc_siente(t):
    t0 = S[6]
    s, ctx = lienzo()
    fondo(ctx, t)
    p = prog(t, t0, 0.6, "out")
    k = lerp(1.0, TEL[2], p)
    cx, cy = lerp(540, TEL[0], p), lerp(960, TEL[1], p) + 10 * math.sin(t * 1.6) * p
    ts = b(8, "siente")
    brillo = 0.25 * (1 - clamp((t - ts) / 0.25)) if t >= ts else 0
    telefono(ctx, cx, cy, k, lambda c: paisaje(c, t, "dia"), t, brillo=brillo)
    # título que se va
    if t < t0 + 0.4:
        ctx.save()
        ctx.translate(0, -prog(t, t0, 0.4, "in") * 500)
        titulo(ctx, t)
        ctx.restore()
    tx, ty = cx + 20, cy - 40
    td = b(8, "También")
    if t >= td - 0.1:
        q = prog(t, td - 0.1, ts - td + 0.1, "out")
        if t >= ts:
            for i in range(3):
                rq = (t - ts - i * 0.16) / 0.8
                if 0 <= rq <= 1:
                    ctx.arc(tx, ty, lerp(20, 260, ease(rq, "out")), 0, 2 * math.pi)
                    ctx.set_source_rgba(*CIAN, 0.8 * (1 - rq))
                    ctx.set_line_width(10 * (1 - rq) + 2)
                    ctx.stroke()
        dedo(ctx, lerp(tx + 420, tx, q), lerp(ty + 900, ty, q), ang=-22, s=0.62, sombra=q)
        if t >= ts:
            cartel(ctx, "TE SIENTE", 540, 210, 76, box=CIAN, fg=INK, s=pop(t, ts + 0.05), rot=-3)
    return a_rgb(s)


# ---- 7. capas
def _mat(p, cx, cy):
    th = math.radians(lerp(0, 38, p))
    sq = lerp(1.0, 0.56, p)
    k = lerp(TEL[2], 0.38, p)
    a = k * math.cos(th)
    bb = -k * math.sin(th)
    c = sq * k * math.sin(th)
    d = sq * k * math.cos(th)
    return cairo.Matrix(a, c, bb, d, cx, cy)


def _cara(ctx, M, dy, dibujar, borde=True, espesor=0, col_lado=(0.1, 0.1, 0.12), radio=70, alpha=1.0,
          marco=0):
    ctx.save()
    ctx.translate(0, dy)
    if espesor > 0:
        ctx.save()
        ctx.translate(0, espesor)
        ctx.transform(M)
        rrect(ctx, -540 - marco, -960 - marco, 1080 + 2 * marco, 1920 + 2 * marco, radio + marco)
        ctx.restore()
        ctx.set_source_rgba(*col_lado, alpha)
        ctx.fill()
    ctx.save()
    ctx.transform(M)
    rrect(ctx, -540 - marco, -960 - marco, 1080 + 2 * marco, 1920 + 2 * marco, radio + marco)
    ctx.restore()
    path = ctx.copy_path()
    ctx.save()
    ctx.clip()
    ctx.transform(M)
    ctx.push_group()
    dibujar(ctx)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()
    if borde:
        ctx.new_path()
        ctx.append_path(path)
        ctx.set_source_rgba(*INK, alpha)
        ctx.set_line_width(6)
        ctx.stroke()
    ctx.restore()


GX = [-540 + (i + 0.5) * 1080 / 7 for i in range(7)]
GY = [-960 + (j + 0.5) * 1920 / 12 for j in range(12)]


def _capa_grilla(ctx, t, brillo, pulsos_a):
    ctx.rectangle(-540, -960, 1080, 1920)
    ctx.set_source_rgba(0.6, 0.9, 1.0, 0.07)
    ctx.fill()
    for x in GX:
        neon_linea(ctx, x, -960, x, 960, CIAN, 0.5 + 0.5 * brillo, 9)
    for y in GY:
        neon_linea(ctx, -540, y, 540, y, CIAN, 0.5 + 0.5 * brillo, 9)
    if pulsos_a > 0:
        for j, y in enumerate(GY):
            for kk in range(2):
                x = -540 + ((t * 700 + j * 173 + kk * 540) % 1080)
                punto_brillo(ctx, x, y, 16, CIAN, pulsos_a)
        for i, x in enumerate(GX):
            y = -960 + ((t * 600 + i * 271) % 1920)
            punto_brillo(ctx, x, y, 13, CIAN, 0.7 * pulsos_a)


def _capa_vidrio(ctx, t, brillo):
    ctx.rectangle(-540, -960, 1080, 1920)
    ctx.set_source_rgba(0.85, 0.95, 1.0, 0.16 + 0.12 * brillo)
    ctx.fill()
    off = ((t * 300) % 3400) - 1700
    g = cairo.LinearGradient(off - 300, -960, off + 300, 960)
    g.add_color_stop_rgba(0, 1, 1, 1, 0)
    g.add_color_stop_rgba(0.5, 1, 1, 1, 0.35 + 0.2 * brillo)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    ctx.set_source(g)
    ctx.rectangle(-540, -960, 1080, 1920)
    ctx.fill()


def _capa_pantalla(ctx, t):
    ctx.save()
    ctx.translate(-540, -960)
    paisaje(ctx, t, "dia")
    ctx.restore()


def _punto(M, dy, lx, ly):
    x, y = M.transform_point(lx, ly)
    return x, y + dy


def sc_capas(t):
    t0 = S[7]
    s, ctx = lienzo()
    fondo(ctx, t)
    p = prog(t, t0, 0.85)
    tv, tc, te = b(9, "vidrio"), b(9, "cuadrícula"), b(9, "electricidad")
    sep = prog(t, tv - 0.15, 0.6, "out")
    cx, cy = 540, lerp(TEL[1], 860, p)
    M = _mat(p, cx, cy)
    d_fondo, d_grilla, d_vidrio = 170 * sep, 0, -170 * sep
    if p >= 0.999:
        z = 1 + 0.05 * clamp((t - tv) / 5)
        ctx.translate(540, 860)
        ctx.scale(z, z)
        ctx.translate(-540, -860)
    ctx.translate(0, -0)
    # pantalla (abajo)
    _cara(ctx, M, d_fondo, lambda c: _capa_pantalla(c, t), espesor=34 * p, col_lado=(0.05, 0.05, 0.07), marco=40)
    gb = clamp((t - tc) / 0.3) * (1 - 0.6 * clamp((t - tc - 0.8) / 0.5)) if t >= tc else 0
    pa = clamp((t - te) / 0.3) if t >= te else 0
    if sep > 0.02:
        _cara(ctx, M, d_grilla, lambda c: _capa_grilla(c, t, gb, pa), borde=True, espesor=6 * sep,
              col_lado=(0.1, 0.5, 0.6), alpha=sep)
        vb = clamp((t - tv) / 0.3) * (1 - clamp((t - tv - 0.9) / 0.4)) if t >= tv else 0
        _cara(ctx, M, d_vidrio, lambda c: _capa_vidrio(c, t, vb), borde=True, espesor=10 * sep,
              col_lado=(0.5, 0.65, 0.75), alpha=sep)
    else:
        # sin separar todavía: vidrio pegado a la pantalla
        _cara(ctx, M, d_fondo, lambda c: _capa_vidrio(c, t, 0), borde=False, alpha=0.6)
    if p > 0.5:
        for etq, dy, lx, ly, t_e, col in (("VIDRIO", d_vidrio, -540, -400, tv, BLANCO),
                                          ("CUADRÍCULA", d_grilla, -540, -100, tc, CIAN),
                                          ("PUNTITOS", d_fondo, -540, 200, tv + 0.3, AMARILLO)):
            if t < t_e:
                continue
            x, y = _punto(M, dy, lx, ly)
            a = pop(t, t_e)
            lx2, ly2 = 230, y - 120
            ctx.set_line_width(5)
            ctx.move_to(x, y)
            ctx.line_to(lx2, ly2)
            ctx.set_source_rgba(1, 1, 1, clamp(a))
            ctx.stroke()
            ctx.arc(x, y, 10, 0, 2 * math.pi)
            ctx.fill()
            cartel(ctx, etq, lx2, ly2 - 10, 52, box=col, fg=INK, s=a)
    if pa > 0:
        cartel(ctx, "ELECTRICIDAD", 540, 250, 70, box=CIAN, fg=INK, s=pop(t, te), rot=2)
    # dedo que se va
    td = t0
    if t < td + 0.45:
        q = prog(t, td, 0.45, "in")
        dedo(ctx, TEL[0] + 20 + 420 * q, TEL[1] - 40 + 900 * q, ang=-22, s=0.62)
    return a_rgb(s)


# ---- 8. el dedo conduce como un cable
def cable(ctx, x, ytop, w=130):
    ctx.save()
    rrect(ctx, x - w / 2, ytop + 170, w, 2000, 30)
    path_ais = ctx.copy_path()
    g = cairo.LinearGradient(x - w / 2, 0, x + w / 2, 0)
    g.add_color_stop_rgb(0, *hx("#1C1F24"))
    g.add_color_stop_rgb(0.45, *hx("#4A4F58"))
    g.add_color_stop_rgb(1, *hx("#15171B"))
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    cw = w * 0.56
    rrect(ctx, x - cw / 2, ytop, cw, 200, cw / 2)
    g = cairo.LinearGradient(x - cw / 2, 0, x + cw / 2, 0)
    g.add_color_stop_rgb(0, *hx("#9A4E1E"))
    g.add_color_stop_rgb(0.45, *hx("#F7B26A"))
    g.add_color_stop_rgb(1, *hx("#8A4418"))
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.set_line_width(3)
    for k in range(-2, 3):
        ctx.move_to(x + k * cw / 6, ytop + 18)
        ctx.line_to(x + k * cw / 6, ytop + 190)
        ctx.set_source_rgba(0.45, 0.2, 0.05, 0.6)
        ctx.stroke()
    ctx.restore()
    return path_ais


def _flujo_vertical(ctx, t, x0, x1, ytop, ybot, n, vel, seed, a=1.0):
    r = rng(seed)
    xs_ = r.uniform(x0, x1, n)
    ph = r.uniform(0, 1, n)
    L = ybot - ytop
    for i in range(n):
        y = ybot - ((t * vel / L + ph[i]) % 1) * L
        punto_brillo(ctx, xs_[i], y, 8, CIAN, a)


def sc_conduce(t):
    t0 = S[8]
    s, ctx = lienzo()
    fondo(ctx, t)
    cuadricula(ctx, [140, 380, 620, 860], [380, 620, 860, 1100, 1340], t, a=0.18, pulsos=False, nodos=False)
    td, tc, ti, tcb = b(10, "dedo"), b(10, "conduce"), b(10, "igual"), b(10, "cable")
    q = prog(t, t0, 0.45, "out")
    fx, fy = 320, lerp(1500, 600, q)
    dedo(ctx, fx, fy, s=1.0)
    if t >= tc:
        a = clamp((t - tc) / 0.3)
        ctx.save()
        ctx.new_path()
        ctx.move_to(fx - 98, 1920)
        ctx.line_to(fx - 98, fy + 98)
        ctx.arc(fx, fy + 98, 98, math.pi, 2 * math.pi)
        ctx.line_to(fx + 98, 1920)
        ctx.close_path()
        ctx.clip()
        _flujo_vertical(ctx, t, fx - 70, fx + 70, fy + 20, 1920, 34, 520, 11, a)
        ctx.restore()
        cartel(ctx, "CONDUCE", 320, 330, 66, box=CIAN, s=pop(t, tc), rot=-4)
    if t >= ti - 0.1:
        qc = prog(t, ti - 0.1, 0.4, "out")
        cx_ = lerp(1300, 770, qc)
        cable(ctx, cx_, 600)
        ctx.save()
        rrect(ctx, cx_ - 36, 600, 72, 1400, 36)
        ctx.clip()
        _flujo_vertical(ctx, t, cx_ - 26, cx_ + 26, 610, 1920, 26, 520, 12)
        ctx.restore()
        texto(ctx, "=", 545, 820, 150, fill=BLANCO, sw=10, alpha=clamp((t - ti) / 0.2))
    if t >= tcb:
        cartel(ctx, "CABLE", 770, 330, 66, box=hx("#F7B26A"), s=pop(t, tcb), rot=4)
    return a_rgb(s)


# ---- 9. la cuadrícula: robo, escaneo y mira
JX = [180 + i * 144 for i in range(6)]
JY = [400 + j * 140 for j in range(7)]
JT = (2, 3)


def sc_cuadricula(t):
    t0 = S[9]
    s, ctx = lienzo()
    fondo(ctx, t)
    ta, tl, tr, t100, tn, tf = (b(11, "apoyas"), b(11, "lleva"), b(11, "revisa"), b(11, "100"), b(11, "nota"),
                                b(11, "falta"))
    nx, ny = JX[JT[0]], JY[JT[1]]
    apag = clamp((t - tl) / 0.8) if t >= tl else 0.0
    esc = None
    if tr <= t < tn + 0.5:
        if t < tn:
            esc = ((t - tr) * 22) % (len(JY) + 1.5) - 0.75
        else:
            q = prog(t, tn, 0.5, "out")
            esc = lerp(((tn - tr) * 22) % (len(JY) + 1.5) - 0.75, JT[1], q)
    elif t >= tn + 0.5:
        esc = JT[1] if t < tf + 0.5 else None
    cuadricula(ctx, JX, JY, t, a=prog(t, t0, 0.4), apagado=JT, apag_k=apag, escaneo=esc)
    # dedo
    q = prog(t, t0, ta - t0 + 0.05, "out")
    fuera = prog(t, S[10] - 0.45, 0.4, "in")
    dx, dy = lerp(nx + 380, nx, q) + 600 * fuera, lerp(ny + 900, ny, q) + 1300 * fuera
    if t >= tl:
        particulas(ctx, t, (nx, ny), (nx + 40, ny + 230), tl - 0.05, tf, n=30, rate=1.8, curva=70)
    dedo(ctx, dx, dy, ang=-14, s=0.7, sombra=q * (1 - fuera))
    if t >= tl:
        particulas(ctx, t, (nx, ny), (nx + 40, ny + 230), tl - 0.05, tf, n=14, rate=1.8, curva=40, seed=9)
        marca_robo(ctx, nx, ny, t, apag * (1 - fuera))
    if t >= ta - 0.02:
        rq = (t - ta) / 0.6
        if 0 <= rq <= 1:
            ctx.arc(nx, ny, lerp(10, 160, ease(rq, "out")), 0, 2 * math.pi)
            ctx.set_source_rgba(*CIAN, 0.9 * (1 - rq))
            ctx.set_line_width(8)
            ctx.stroke()
    if t100 - 0.1 <= t:
        cartel(ctx, "+100 VECES\nPOR SEGUNDO", 540, 215, 64, s=pop(t, t100 - 0.1), rot=-2,
               alpha=1 - clamp((t - tn - 0.2) / 0.25))
    if t >= tn + 0.15:
        lock = tn + 0.75
        mira(ctx, nx, ny, (t - (tn + 0.15)) / 0.6)
        if t >= lock:
            cartel(ctx, "¡AQUÍ!", nx + 250, ny - 120, 70, box=hx("#FF4D4D"), fg=BLANCO, s=pop(t, lock), rot=6)
            cartel(ctx, "FILA 4 · COLUMNA 3", 540, 215, 54, box=BLANCO, s=pop(t, lock + 0.15))
    return a_rgb(s)


# ---- 10..13. comentarios, letra en cámara lenta, escritura rápida
TECLA_H = centro_tecla("H")


def cam(ctx, P, Q, s):
    ctx.translate(*Q)
    ctx.scale(s, s)
    ctx.translate(-P[0], -P[1])


def _texto_escrito(t):
    if t < T_LETRA:
        return ""
    txt = "H"
    for i, (tt, ch) in enumerate(TIPEO):
        if t >= tt + 0.04:
            txt += {",": ",", " ": " "}.get(ch, ch.lower())
    return txt


T_LETRA = b(14, "redibujo") + 0.3      # momento en que el barrido pasa por el campo


def sc_comentarios(t):
    t0 = S[10]
    s, ctx = lienzo()
    fondo(ctx, t)
    tcm, tes = b(12, "comentarios"), b(12, "escribe")
    q = prog(t, t0, 0.5, "out")
    cy = lerp(2400, TEL[1], q)
    cb = (0.55 + 0.45 * math.sin(t * 8)) * clamp((t - tcm) / 0.25) if t >= tcm else 0
    kp = clamp((t - tes) / 0.45) if t >= tes else 0
    telefono(ctx, TEL[0], cy, TEL[2],
             lambda c: comentarios_ui(c, t, "", teclado_p=kp, campo_brillo=cb, video_t=t), t)
    if t >= tcm:
        fx, fy = tel_a_pantalla(TEL[0], cy, TEL[2], CAMPO[0], CAMPO[1] + CAMPO[3] / 2)
        flecha(ctx, 40, fy - 160, fx - 12, fy, t, alpha=clamp((t - tcm) / 0.2), curva=0.35, w=14)
        cartel(ctx, "TU TURNO", 540, 190, 72, box=AMARILLO, s=pop(t, tcm), rot=-3)
    return a_rgb(s)


def _ui_letra(c, t, escrito, pulsada, pulso, globo, grilla_a, apag_k, esc, mira_p, barrido_y):
    comentarios_ui(c, t, escrito, teclado_p=1.0, pulsada=pulsada, pulso=pulso, video_t=S[11], globo=None,
                   cursor=True)
    if grilla_a > 0:
        xs = [TECLA_H[0] + k * 108 for k in range(-6, 5)]
        ys = [TECLA_H[1] + m * 120 for m in range(-1, 3)]
        cuadricula(c, xs, ys, t, a=0.6 * grilla_a, apagado=(6, 1), apag_k=apag_k, escaneo=esc, lw=4, vel=300)
    if globo:
        globo_tecla(c, *globo)
    if barrido_y is not None:
        y = barrido_y
        g = cairo.LinearGradient(0, y - 160, 0, y)
        g.add_color_stop_rgba(0, *CIAN, 0)
        g.add_color_stop_rgba(1, 1, 1, 1, 0.85)
        c.rectangle(0, y - 160, 1080, 172)
        c.set_source(g)
        c.fill()


def sc_letra(t):
    t0 = S[11]
    tt, tro, tcr = b(13, "toca"), b(13, "roba"), b(13, "cruce")
    ten, tpu, tsa, tle = b(14, "encuentra"), b(14, "punto"), b(14, "sabe"), b(14, "letra")
    trd, tpr, tfo = b(14, "redibujo"), b(14, "prende"), b(14, "forman", fin=True)
    P_h = tel_a_pantalla(*TEL, *TECLA_H)
    P_campo = tel_a_pantalla(*TEL, 300, CAMPO[1] + CAMPO[3] / 2)
    # cámara
    zq = prog(t, t0, 0.6)
    ida = prog(t, trd - 0.7, 0.7)
    s_cam = lerp(lerp(1.0, 2.2, zq), 1.7, ida)
    P = (lerp(lerp(540, P_h[0], zq), P_campo[0], ida), lerp(lerp(TEL[1], P_h[1], zq), P_campo[1], ida))
    Q = (540, lerp(860, 820, ida))
    grilla_a = prog(t, t0 + 0.3, 0.5) * (1 - prog(t, trd - 0.5, 0.4))
    apag = clamp((t - tro) / 0.6) if t >= tro else 0
    esc = None
    if ten <= t < tpu:
        esc = ((t - ten) * 14) % 5.5 - 1.5
    elif tpu <= t < trd - 0.4:
        esc = 1
    mira_p = (t - tpu + 0.1) / 0.5 if tpu - 0.1 <= t < trd - 0.4 else 0
    globo = ("H", clamp((t - tsa) / 0.35)) if tsa <= t < trd - 0.4 else None
    pulsada = "H" if tt <= t < trd - 0.5 else None
    barrido_y = None
    if trd <= t < trd + 0.7:
        barrido_y = (t - trd) / 0.7 * 1980
    escrito = "H" if t >= trd + 0.7 * (CAMPO[1] + 50) / 1980 else ""
    s, ctx = lienzo()
    fondo(ctx, t)
    ctx.save()
    cam(ctx, P, Q, s_cam)
    telefono(ctx, TEL[0], TEL[1], TEL[2],
             lambda c: _ui_letra(c, t, escrito, pulsada, 1.0 if pulsada else 0, globo, grilla_a, apag, esc,
                                 mira_p, barrido_y), t)
    # dedo (en coordenadas del teléfono, sigue a la cámara)
    hx_, hy_ = P_h
    q = prog(t, t0 + 0.35, tt - t0 - 0.35, "out")
    sale = prog(t, trd - 0.75, 0.45, "in")
    if q > 0 and sale < 1:
        if t >= tro:
            particulas(ctx, t, (hx_, hy_), (hx_ + 20, hy_ + 120), tro - 0.05, ten, n=24, rate=1.7, curva=40, r=5)
        dedo(ctx, lerp(hx_ + 250, hx_, q) + 250 * sale, lerp(hy_ + 600, hy_, q) + 600 * sale, ang=-12, s=0.36,
             sombra=q * (1 - sale))
        if t >= tro:
            particulas(ctx, t, (hx_, hy_), (hx_ + 20, hy_ + 120), tro - 0.05, ten, n=10, rate=1.7, curva=20,
                       r=5, seed=8)
    ctx.save()
    ctx.translate(hx_, hy_)
    ctx.scale(TEL[2], TEL[2])
    marca_robo(ctx, 0, 0, t, apag * (1 - sale))
    if mira_p > 0:
        mira(ctx, 0, 0, mira_p, tam=60)
    ctx.restore()
    ctx.restore()
    etiqueta_lenta(ctx, t, t0 + 0.2, trd - 0.6, "CÁMARA LENTA", y=200)
    if tcr <= t < ten:
        a = pop(t, tcr)
        cartel(ctx, "CRUCE", 800, 680, 60, box=CIAN, s=a, rot=5)
        flecha(ctx, 740, 730, 600, 835, t, alpha=clamp(a), curva=0.2, w=12)
    img = a_rgb(s)
    # zoom a los puntitos de la letra
    if t >= tpr - 0.1:
        # posición de la H en pantalla con la cámara final
        hxl = tel_a_pantalla(*TEL, CAMPO[0] + 52 + 20, CAMPO[1] + CAMPO[3] / 2)
        X = Q[0] + s_cam * (hxl[0] - P[0])
        Y = Q[1] + s_cam * (hxl[1] - P[1])
        zfin = 26
        z = zexp(t, tpr - 0.1, 0.8, 1.0, zfin)
        qq = prog(t, tpr - 0.1, 0.8)
        cx, cy = lerp(540, X, min(1, qq * 1.2)), lerp(Q[1], Y, min(1, qq * 1.2))
        img = zoom_sub(img, cx, cy, z)
        if t >= tfo - 0.2:
            s2_, c2 = desde_rgb(img)
            cartel(c2, "R + V + A = BLANCO", 540, 1250, 56, box=BLANCO, s=pop(t, tfo - 0.2))
            img = a_rgb(s2_)
    return img


TIPEO_TXT = "ola, buen dato"
_T_TIP0 = b(15, "eso")
_T_TIP1 = b(15, "segundo", fin=True) - 0.1
TIPEO = [(_T_TIP0 + i * (_T_TIP1 - _T_TIP0) / len(TIPEO_TXT), ch) for i, ch in enumerate(TIPEO_TXT)]


def _tecla_de(ch):
    return {" ": " ", ",": ","}.get(ch, ch.upper())


def sc_rapido(t):
    t0 = S[12]
    s, ctx = lienzo()
    fondo(ctx, t)
    # pos del dedo
    pulsada, globo, pulso = None, None, 0.0
    idx = -1
    for i, (tt, ch) in enumerate(TIPEO):
        if t >= tt:
            idx = i
    if idx >= 0:
        tt, ch = TIPEO[idx]
        dt = t - tt
        if dt < 0.12:
            pulsada = _tecla_de(ch)
            pulso = 1 - dt / 0.12
            if ch not in " ,":
                globo = (ch.upper(), clamp(dt / 0.06))
    escrito = "H" + "".join(ch for tt, ch in TIPEO if t >= tt + 0.03)
    escrito = escrito[0] + escrito[1:]
    zq = prog(t, t0, 0.4)
    s_cam = lerp(1.7, 1.0, zq)
    P_campo = tel_a_pantalla(*TEL, 300, CAMPO[1] + CAMPO[3] / 2)
    P = (lerp(P_campo[0], 540, zq), lerp(P_campo[1], TEL[1], zq))
    Q = (540, lerp(820, TEL[1], zq))
    ctx.save()
    cam(ctx, P, Q, s_cam)

    def ui(c):
        comentarios_ui(c, t, escrito, teclado_p=1.0, pulsada=pulsada, pulso=pulso, video_t=S[11], globo=globo)
        xs = [TECLA_H[0] + k * 108 for k in range(-6, 5)]
        ys = [TECLA_H[1] + m * 120 for m in range(-1, 3)]
        cuadricula(c, xs, ys, t, a=0.35, nodos=False, lw=3, vel=300)
        if pulsada:
            kx, ky = centro_tecla(pulsada)
            punto_brillo(c, kx, ky, 14, CIAN, pulso)
            c.arc(kx, ky, lerp(70, 10, pulso), 0, 2 * math.pi)
            c.set_source_rgba(*CIAN, pulso)
            c.set_line_width(5)
            c.stroke()

    telefono(ctx, TEL[0], TEL[1], TEL[2], ui, t)
    # dedo que salta de tecla en tecla
    if idx >= 0 or t >= _T_TIP0 - 0.3:
        if idx < 0:
            dest = centro_tecla(_tecla_de(TIPEO[0][1]))
            q = prog(t, _T_TIP0 - 0.3, 0.3, "out")
            org = (dest[0] + 250, dest[1] + 600)
            lx, ly = lerp(org[0], dest[0], q), lerp(org[1], dest[1], q)
            alto = 0
        else:
            tt, ch = TIPEO[idx]
            cur = centro_tecla(_tecla_de(ch))
            nxt = centro_tecla(_tecla_de(TIPEO[idx + 1][1])) if idx + 1 < len(TIPEO) else (cur[0] + 300, cur[1] + 700)
            dur = (TIPEO[idx + 1][0] - tt) if idx + 1 < len(TIPEO) else 0.5
            q = clamp((t - tt - 0.05) / max(dur - 0.05, 0.01))
            e = ease(q)
            lx, ly = lerp(cur[0], nxt[0], e), lerp(cur[1], nxt[1], e)
            alto = math.sin(math.pi * q)
        X, Y = tel_a_pantalla(*TEL, lx, ly)
        dedo(ctx, X + 30 * alto, Y + 50 * alto, ang=-12, s=0.36 * (1 + 0.08 * alto), sombra=1 - alto)
    ctx.restore()
    etiqueta_lenta(ctx, t, t0 + 0.1, S[13] - 0.2, "VELOCIDAD REAL", y=200)
    return a_rgb(s)


# ---- 14. suscribirse
BTN = (540, 790, 780, 200)


def sc_suscribirse(t):
    t0 = S[13]
    s, ctx = lienzo()
    fondo(ctx, t)
    trb, tsu, tint = b(16, "Róbale"), b(16, "suscribirse"), b(16, "interesó")
    # teléfono que se va
    if t < t0 + 0.45:
        q = prog(t, t0, 0.45, "in")
        telefono(ctx, TEL[0], TEL[1] + 1500 * q, TEL[2],
                 lambda c: comentarios_ui(c, t, "H" + TIPEO_TXT, teclado_p=1.0, video_t=S[11]), t)
    ap = pop(t, t0 + 0.25, 0.45)
    xs = [BTN[0] - 360 + k * 144 for k in range(6)]
    ys = [BTN[1] - 280 + k * 140 for k in range(5)]
    if ap > 0:
        cuadricula(ctx, xs, ys, t, a=0.55 * clamp(ap), nodos=False)
    hecho = t >= tsu + 0.2
    k = ap * bump(t, tint, 0.35, 0.08) * bump(t, tsu + 0.2, 0.35, 0.15)
    if k > 0:
        ctx.save()
        ctx.translate(BTN[0], BTN[1])
        ctx.scale(k, k)
        w, h = BTN[2], BTN[3]
        rrect(ctx, -w / 2, -h / 2 + 12, w, h, h / 2)
        ctx.set_source_rgb(*INK)
        ctx.fill()
        rrect(ctx, -w / 2, -h / 2, w, h, h / 2)
        ctx.set_source_rgb(*(hx("#3B3D42") if hecho else ROJO_BOTON))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(8)
        ctx.stroke()
        # la cuadrícula se ve "a través" del botón
        ctx.save()
        rrect(ctx, -w / 2, -h / 2, w, h, h / 2)
        ctx.clip()
        for x in xs:
            ctx.move_to(x - BTN[0], -h)
            ctx.line_to(x - BTN[0], h)
        for y in ys:
            ctx.move_to(-w, y - BTN[1])
            ctx.line_to(w, y - BTN[1])
        ctx.set_source_rgba(*CIAN, 0.18)
        ctx.set_line_width(4)
        ctx.stroke()
        ctx.restore()
        if hecho:
            texto(ctx, "SUSCRITO", 40, 6, 92, fill=BLANCO, stroke=None)
            ctx.set_line_width(16)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.move_to(-300, 0)
            ctx.line_to(-262, 38)
            ctx.line_to(-198, -40)
            ctx.set_source_rgb(*hx("#4CE07A"))
            ctx.stroke()
        else:
            texto(ctx, "SUSCRIBIRSE", 0, 6, 92, fill=BLANCO, stroke=None)
        ctx.restore()
    # dedo
    nx, ny = xs[3], ys[2]
    tin = b(16, "video") - 0.15
    if t >= tin:
        q = prog(t, tin, trb - tin + 0.05, "out")
        sale = prog(t, tsu + 0.35, 0.5, "in")
        if t >= trb:
            particulas(ctx, t, (nx, ny), (nx + 40, ny + 230), trb, tsu + 0.1, n=30, rate=1.8, curva=70)
        dedo(ctx, lerp(nx + 380, nx, q) + 700 * sale, lerp(ny + 900, ny, q) + 1400 * sale, ang=-14, s=0.7,
             sombra=q * (1 - sale))
        if t >= trb:
            particulas(ctx, t, (nx, ny), (nx + 40, ny + 230), trb, tsu + 0.1, n=12, rate=1.8, curva=40, seed=5)
    if hecho:
        for i in range(18):
            ang = i / 18 * 2 * math.pi
            rq = clamp((t - tsu - 0.2) / 0.7)
            if rq < 1:
                r = lerp(80, 520, ease(rq, "out"))
                punto_brillo(ctx, BTN[0] + math.cos(ang) * r, BTN[1] + math.sin(ang) * r * 0.6, 9, AMARILLO if i % 2
                             else CIAN, 1 - rq)
        fa = clamp((t - tsu - 0.5) / 0.3)
        flecha(ctx, 330, 1100, 150, 1330, t, alpha=fa, curva=0.25)
    if t >= trb:
        cartel(ctx, "¡RÓBALE!", 540, 300, 80, box=AMARILLO, s=pop(t, trb), rot=-3)
    return a_rgb(s)


ESCENAS = [sc_gancho, sc_barrido, sc_zoom_in, sc_perillas, sc_zoom_out, sc_amarillo, sc_siente, sc_capas,
           sc_conduce, sc_cuadricula, sc_comentarios, sc_letra, sc_rapido, sc_suscribirse]


# ------------------------------------------------------------------ subtítulos
CAPS = motor.Captions(T.words, {"size": 76, "y": 1470, "max_palabras": 3, "max_letras": 18})


def cuadro(t):
    i = escena_de(t)
    try:
        img = ESCENAS[i](t)
    except Exception as e:
        raise RuntimeError(f"falló la escena {ESCENAS[i].__name__} en t={t:.3f}: {e}") from e
    # pequeño flash/corte entre escenas
    if i > 0 and t - S[i] < 0.08 and i not in (2, 4):
        k = 1 - (t - S[i]) / 0.08
        img = (img.astype(np.float32) * (1 - 0.35 * k) + 255 * 0.35 * k).astype(np.uint8)
    im = Image.fromarray(img)
    CAPS.draw(im, t)
    return im


# ------------------------------------------------------------------ sonido
def _env(n, a=0.005, r=0.05):
    e = np.ones(n, np.float32)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def s_tick(f=1700, d=0.06):
    t = np.arange(int(d * SR)) / SR
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 70) * 0.7).astype(np.float32)


def s_click():
    n = int(0.03 * SR)
    x = np.random.default_rng(4).standard_normal(n).astype(np.float32)
    x = np.diff(x, prepend=0)
    t = np.arange(n) / SR
    return (x * np.exp(-t * 260) * 0.35 + np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 300) * 0.3).astype(np.float32)


def s_chispa(d=0.7, seed=1):
    n = int(d * SR)
    r = np.random.default_rng(seed)
    out = np.zeros(n, np.float32)
    for _ in range(int(d * 70)):
        i = r.integers(0, n - 800)
        L = r.integers(80, 700)
        out[i:i + L] += r.standard_normal(L).astype(np.float32) * np.exp(-np.arange(L) / (L / 4)) * r.uniform(0.3, 1)
    out = np.diff(out, prepend=0)
    t = np.arange(n) / SR
    buzz = 0.15 * np.sign(np.sin(2 * np.pi * 120 * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t))
    out = out / (np.abs(out).max() + 1e-6) * 0.8 + buzz.astype(np.float32)
    return (out * _env(n, 0.01, 0.15)).astype(np.float32)


def s_beep():
    t = np.arange(int(0.08 * SR)) / SR
    tone = np.sin(2 * np.pi * 1320 * t) * _env(len(t), 0.003, 0.02)
    gap = np.zeros(int(0.04 * SR))
    t2 = np.arange(int(0.12 * SR)) / SR
    tone2 = np.sin(2 * np.pi * 1760 * t2) * _env(len(t2), 0.003, 0.05)
    return (np.concatenate([tone, gap, tone2]) * 0.55).astype(np.float32)


def s_zumbido(d=2.0):
    n = int(d * SR)
    t = np.arange(n) / SR
    sig = sum(np.sin(2 * np.pi * 110 * k * t) / k for k in range(1, 7))
    sig *= 0.6 + 0.4 * np.sin(2 * np.pi * 6 * t)
    return (sig / 2.5 * 0.45 * _env(n, 0.25, 0.4)).astype(np.float32)


def s_escaneo(d=1.0, f0=900, f1=2600, rate=22):
    n = int(d * SR)
    out = np.zeros(n, np.float32)
    k = 0
    while True:
        tt = k / rate
        if tt >= d:
            break
        f = f0 + (f1 - f0) * tt / d
        tk = s_tick(f, 0.035) * 0.5
        i = int(tt * SR)
        out[i:i + len(tk)] += tk[:max(0, n - i)]
        k += 1
    return out


def s_frenada(d=0.6):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = 700 * np.exp(-t * 4) + 40
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 - t / d) ** 1.5
    return (sig * 0.5).astype(np.float32)


def s_golpe():
    t = np.arange(int(0.45 * SR)) / SR
    f = 120 * np.exp(-t * 8) + 45
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * 0.9).astype(np.float32)


def s_subida(d=0.8):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = 300 + 1500 * (t / d) ** 2
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / d) ** 2 * 0.3
    x = np.random.default_rng(3).standard_normal(n).astype(np.float32)
    x = np.convolve(x, np.ones(20) / 20, mode="same") * (t / d) ** 3 * 0.6
    return (sig + x).astype(np.float32)


def sonido(kind, **kw):
    motor.SR = SR
    f = {"tick": s_tick, "click": s_click, "chispa": s_chispa, "beep": s_beep, "zumbido": s_zumbido,
         "escaneo": s_escaneo, "frenada": s_frenada, "golpe": s_golpe, "subida": s_subida}.get(kind)
    if f:
        return f(**kw)
    return motor.synth(kind, 0.5)


def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    # gancho
    for i in range(int(b(1) * 15)):
        ev(i / 15, "tick", 0.12, f=2400 + 8 * i, d=0.03)
    ev(b(0, "100"), "pop", 0.9)
    # barrido
    ev(S[1], "frenada", 0.7)
    ev(T_RED, "escaneo", 0.35, d=T_RAP - T_RED, f0=500, f1=900, rate=24)
    for t0, d, *_ in BARRIDOS[1:]:
        ev(t0, "whoosh_suave", 0.7)
    ev(T_RAP, "subida", 0.6, d=1.2)
    # zoom in
    ev(S[2], "zoom", 0.9)
    ev(b(2, "hilera"), "pop", 0.5)
    for i, p in enumerate(("rojo", "verde", "azul")):
        ev(b(2, p), "tick", 0.8, f=900 + 300 * i, d=0.12)
    # perillas
    ev(S[3], "whoosh", 0.8)
    for t0, _ in KEYS_RGB[1:]:
        ev(t0, "tick", 0.5, f=1300, d=0.08)
    # zoom out
    ev(b(4, "chiquitos"), "whoosh_suave", 0.8)
    ev(b(4, "chiquitos") + 0.35, "pop", 0.6)
    ev(b(4, "separan"), "whoosh", 1.0)
    # amarillo
    ev(b(5, "Mira"), "boing", 0.7)
    ev(b(6) - 0.05, "zoom", 0.9)
    ev(b(6, "rojos"), "pop", 0.7)
    ev(b(6, "verdes"), "pop", 0.7)
    ev(b(6, "juntos"), "tick", 0.5, f=700, d=0.1)
    ev(b(7) - 0.05, "whoosh", 0.8)
    ev(b(7, "inventando") - 0.3, "pop", 0.6)
    ev(b(7, "inventando") + 0.4, "ding", 0.9)
    # siente
    ev(S[6], "whoosh", 0.9)
    ev(b(8, "También") - 0.1, "whoosh_suave", 0.6)
    ev(b(8, "siente"), "golpe", 1.0)
    # capas
    ev(S[7], "whoosh", 0.8)
    ev(b(9, "vidrio") - 0.15, "whoosh_suave", 0.8)
    ev(b(9, "vidrio"), "pop", 0.5)
    ev(b(9, "cuadrícula"), "pop", 0.5)
    ev(b(9, "electricidad"), "zumbido", 0.55, d=S[8] - b(9, "electricidad") + 0.3)
    ev(b(9, "electricidad"), "pop", 0.6)
    # conduce
    ev(S[8], "whoosh_suave", 0.7)
    ev(b(10, "conduce"), "chispa", 0.5, d=0.5, seed=2)
    ev(b(10, "conduce"), "pop", 0.6)
    ev(b(10, "igual") - 0.1, "whoosh", 0.7)
    ev(b(10, "cable"), "pop", 0.6)
    # cuadrícula
    ev(S[9], "zumbido", 0.3, d=S[10] - S[9])
    ev(b(11, "apoyas"), "golpe", 0.7)
    ev(b(11, "lleva") - 0.05, "chispa", 0.75, d=1.2, seed=3)
    ev(b(11, "revisa"), "escaneo", 0.5, d=b(11, "nota") - b(11, "revisa"), f0=1200, f1=2200, rate=22)
    ev(b(11, "100") - 0.1, "pop", 0.8)
    ev(b(11, "nota") + 0.75, "beep", 0.8)
    ev(b(11, "nota") + 0.75, "pop", 0.6)
    # comentarios
    ev(S[10], "whoosh", 0.9)
    ev(b(12, "comentarios"), "pop", 0.8)
    ev(b(12, "escribe"), "whoosh_suave", 0.7)
    # letra
    ev(S[11], "frenada", 0.6)
    ev(S[11] + 0.1, "zoom", 0.6)
    ev(b(13, "toca"), "click", 0.9)
    ev(b(13, "toca"), "golpe", 0.5)
    ev(b(13, "roba") - 0.05, "chispa", 0.75, d=1.0, seed=4)
    ev(b(13, "cruce"), "pop", 0.6)
    ev(b(14, "encuentra"), "escaneo", 0.5, d=b(14, "punto") - b(14, "encuentra"), f0=1200, f1=2200)
    ev(b(14, "punto") + 0.35, "beep", 0.8)
    ev(b(14, "sabe"), "pop", 0.8)
    ev(b(14, "redibujo") - 0.7, "whoosh_suave", 0.6)
    ev(b(14, "redibujo"), "escaneo", 0.35, d=0.7, f0=600, f1=1400, rate=30)
    ev(b(14, "prende") - 0.1, "zoom", 0.8)
    ev(b(14, "forman", fin=True) - 0.2, "pop", 0.6)
    # rápido
    ev(S[12], "whoosh", 0.8)
    for tt, ch in TIPEO:
        ev(tt, "click", 0.8)
    # suscribirse
    ev(S[13], "whoosh", 0.8)
    ev(S[13] + 0.25, "pop", 0.8)
    ev(b(16, "Róbale"), "chispa", 0.75, d=b(16, "suscribirse") - b(16, "Róbale") + 0.2, seed=5)
    ev(b(16, "Róbale"), "pop", 0.6)
    ev(b(16, "suscribirse") + 0.2, "ding", 1.0)
    ev(b(16, "suscribirse") + 0.2, "golpe", 0.6)
    return E


def pista_efectos():
    n = int((TOTAL + 2) * SR)
    mix = np.zeros(n, np.float32)
    for t, k, v, kw in eventos():
        snd = sonido(k, **kw) * v
        i0 = int(t * SR)
        i1 = min(n, i0 + len(snd))
        if 0 <= i0 < n:
            mix[i0:i1] += snd[:i1 - i0]
    peak = np.abs(mix).max() or 1
    mix *= 0.55 / peak
    return mix


def escribir_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    st = np.stack([pcm, pcm], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())


# ------------------------------------------------------------------ render
def _seg(args):
    f0, f1, out = args
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r",
           str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(cuadro(f / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return out


def render(salida, hilos=2, desde=0.0, hasta=None):
    hasta = hasta or TOTAL
    fa, fb = int(desde * FPS), int(math.ceil(hasta * FPS))
    tmp = tempfile.mkdtemp(prefix="render_", dir=AQUI)
    k = hilos * 3
    bounds = [fa + round((fb - fa) * i / k) for i in range(k + 1)]
    segs = [(bounds[i], bounds[i + 1], os.path.join(tmp, f"seg{i:02d}.mp4")) for i in range(k)]
    with Pool(hilos) as pool:
        files = pool.map(_seg, segs, chunksize=1)
    lst = os.path.join(tmp, "lista.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{x}'\n" for x in files)
    video = os.path.join(tmp, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video],
                   check=True)
    sfx = os.path.join(tmp, "efectos.wav")
    escribir_wav(sfx, pista_efectos()[int(desde * SR):])
    voz = os.path.join(AQUI, "audio", "voz.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-ss", f"{desde:.3f}", "-i", voz, "-i", sfx,
                    "-filter_complex", "[1:a][2:a]amix=inputs=2:normalize=0:duration=longest,"
                    "alimiter=limit=0.89:level=false[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    salida], check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fotos")
    ap.add_argument("--dir", default=os.path.join(AQUI, "fotos"))
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "como_funciona_tu_pantalla.mp4"))
    ap.add_argument("--desde", type=float, default=0.0)
    ap.add_argument("--hasta", type=float)
    ap.add_argument("--hilos", type=int, default=2)
    a = ap.parse_args()
    if a.fotos:
        os.makedirs(a.dir, exist_ok=True)
        for ts in a.fotos.split(","):
            t = float(ts)
            cuadro(t).save(os.path.join(a.dir, f"f_{t:06.2f}.png"))
        print("fotos en", a.dir)
        return
    os.makedirs(os.path.dirname(a.salida), exist_ok=True)
    render(a.salida, a.hilos, a.desde, a.hasta)
    print("listo:", a.salida, f"{TOTAL:.1f}s")


if __name__ == "__main__":
    main()

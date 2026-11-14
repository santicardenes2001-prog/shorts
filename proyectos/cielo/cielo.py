"""Short "¿Por qué el cielo de noche es negro?" — animación procedural, mismo estilo que pantalla/picante/pulmones.

Misterio que se resuelve al final: la noche no tenía explicación, la pista la dio Edgar Allan Poe (la luz tarda
en viajar, así que el universo tuvo que nacer) y el negro del cielo es luz que todavía viene en camino.
El último cuadro es igual al primero y la última frase empalma con la primera (loop), con una cola mínima.

    python proyectos/cielo/cielo.py --fotos 0,5.5,14
    python proyectos/cielo/cielo.py            # render completo -> salidas/por_que_el_cielo_es_negro.mp4
"""
import argparse
import functools
import io
import json
import math
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import cairo
import cairosvg
import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "proyectos", "pantalla"))
sys.path.insert(0, os.path.join(ROOT, "proyectos", "picante"))
import kit  # noqa: E402
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, bump, cartel, clamp, ease, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rng, rrect, texto)
from picante import _elipse_suave, capa, carita, fondo_azul  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "La oscuridad de la noche no tenía explicación.",                        # b0
    "Parece obvio: es de noche porque el Sol se fue.",                       # b1
    "Pero el Sol es solo una estrella entre muchísimas.",                    # b2
    "Antes se creía que el universo era infinito y eterno.",                 # b3
    "Si fuera así, habría estrellas en todas las direcciones.",              # b4
    "Mires hacia donde mires, tu vista terminaría en una estrella.",         # b5
    "El cielo entero brillaría como la superficie del Sol.",                 # b6
    "No existiría la noche.",                                                # b7
    "Pero la noche existe, así que algo estaba mal.",                        # b8
    "La primera pista correcta no la dio un astrónomo.",                     # b9
    "La escribió un autor de cuentos de terror: Edgar Allan Poe.",           # b10
    "Su idea era simple.",                                                   # b11
    "La luz no llega al instante: tarda en viajar.",                         # b12
    "La de las estrellas más lejanas todavía no llegó hasta aquí.",          # b13
    "Para que eso pase, el universo no puede ser eterno.",                   # b14
    "Tuvo que nacer en algún momento.",                                      # b15
    "Cerca de un siglo después, la ciencia le dio la razón.",                # b16
    "El universo nació hace casi catorce mil millones de años.",             # b17
    "Desde entonces, la luz solo pudo recorrer una parte del camino.",       # b18
    "Por eso entre las estrellas ves negro.",                                # b19
    "Ese negro es luz que todavía viene en camino.",                         # b20
    "Durante siglos faltó esa sola idea:",                                   # b21
]
WORDS = motor.align_times([{"texto": t} for t in NARRACION],
                          json.load(open(os.path.join(AQUI, "audio", "palabras.json"))))
COLA = 0.3                      # casi sin hueco: la frase puente cae sobre la primera
TOTAL = WORDS[-1][-1]["end"] + COLA


def b(i, palabra=None, fin=False, n=0):
    ws = WORDS[i]
    if palabra is None:
        return ws[-1]["end"] if fin else ws[0]["start"]
    obj = motor.norm(palabra)
    cand = [w for w in ws if w["n"] == obj] or [w for w in ws if w["n"].startswith(obj)]
    if not cand:
        raise ValueError(f"no está {palabra!r} en b{i}")
    w = cand[min(n, len(cand) - 1)]
    return w["end"] if fin else w["start"]


# ------------------------------------------------------------------ colores
ROJO = hx("#FF3B2F")
VERDE = hx("#2BD45A")
CIAN = P.CIAN
SOL = hx("#FFC933")
SOL2 = hx("#FF9A1F")
LUZ = hx("#FFE98A")
NOCHE = hx("#070B1C")
LOMA = hx("#0A0F26")
GRIS = hx("#6B7691")
PAPEL = hx("#F6EEDC")
AZUL_T = hx("#3D8BFF")
VERDE_T = hx("#44C767")

# ------------------------------------------------------------------ ayudas
KF = 60 * round(14 * TOTAL / 60) / (14 * TOTAL)      # el fondo de puntos cierra justo en el loop


def fondo(ctx, t, oscuro=0.0):
    fondo_azul(ctx, t * KF)
    if oscuro > 0:
        ctx.set_source_rgba(*NOCHE, oscuro)
        ctx.paint()


def sale(t, t1, d=0.2):
    return 1 - prog(t, t1, d, "in")


def titila(t, ph, k):
    """Brillo que se repite exacto al cerrar el loop."""
    return 0.72 + 0.28 * math.sin(TAU * k * t / TOTAL + ph)


def estrella(ctx, x, y, r, a=1.0, col=BLANCO, halo=1.0):
    if a <= 0.01 or r <= 0.15:
        return
    if halo > 0:
        _elipse_suave(ctx, x, y, r * 3.4, r * 3.4, col, 0.30 * a * halo)
    if r < 3.2:
        ctx.arc(x, y, r, 0, TAU)
        ctx.set_source_rgba(*col, a)
        ctx.fill()
        return
    k = 0.2 * r
    ctx.move_to(x, y - r)
    for i in range(4):
        a0 = -math.pi / 2 + i * math.pi / 2
        a1 = a0 + math.pi / 2
        am = (a0 + a1) / 2
        ctx.curve_to(x + k * math.cos(am), y + k * math.sin(am), x + k * math.cos(am), y + k * math.sin(am),
                     x + r * math.cos(a1), y + r * math.sin(a1))
    ctx.close_path()
    ctx.set_source_rgba(*col, a)
    ctx.fill()
    ctx.arc(x, y, r * 0.3, 0, TAU)
    ctx.fill()


@functools.lru_cache(maxsize=None)
def campo_pts(seed, n, y1=1300):
    r = rng(seed)
    return tuple((float(r.uniform(30, 1050)), float(r.uniform(40, y1)), float(r.uniform(2.0, 7.5)),
                  float(r.uniform(0, TAU)), int(r.integers(14, 40))) for _ in range(n))


def campo(ctx, t, seed=7, n=70, a=1.0, y1=1300, esc=1.0):
    if a <= 0.01:
        return
    for x, y, r, ph, k in campo_pts(seed, n, y1):
        estrella(ctx, x, y, r * esc, a * titila(t, ph, k), halo=0.7)


def cara(ctx, x, y, R, ojos="open", boca="smile", ceja=None, look=(0, 0), rubor=False):
    carita(ctx, x, y - 0.06 * R, 0.62 * R, R / 150, ojos=ojos, boca=boca, ceja=ceja, look=look, rubor=rubor)


def sol(ctx, x, y, R, t, ojos="open", boca="smile", ceja=None, look=(0, 0), a=1.0, con_cara=1.0):
    if a <= 0.01 or R <= 0.5:
        return
    ctx.save()
    ctx.push_group()
    _elipse_suave(ctx, x, y, R * 2.3, R * 2.3, SOL, 0.35)
    n = 12
    for i in range(n):
        ang = TAU * i / n + t * 0.35
        r0, r1 = R * 1.12, R * (1.36 + 0.06 * math.sin(t * 3 + i))
        w = 0.13
        ctx.move_to(x + r0 * math.cos(ang - w), y + r0 * math.sin(ang - w))
        ctx.line_to(x + r1 * math.cos(ang), y + r1 * math.sin(ang))
        ctx.line_to(x + r0 * math.cos(ang + w), y + r0 * math.sin(ang + w))
        ctx.close_path()
    ctx.set_source_rgb(*SOL2)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(1.5, R * 0.035))
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.arc(x, y, R, 0, TAU)
    g = cairo.RadialGradient(x - R * 0.3, y - R * 0.35, R * 0.1, x, y, R)
    g.add_color_stop_rgb(0, *hx("#FFE56B"))
    g.add_color_stop_rgb(1, *SOL)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(2, R * 0.05))
    ctx.stroke()
    if con_cara > 0.02 and R > 26:
        ctx.push_group()
        cara(ctx, x, y, R, ojos, boca, ceja, look, rubor=True)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(con_cara)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


MANCHAS = [(-0.45, -0.35, 0.42, 0.3), (0.35, -0.1, 0.36, 0.44), (-0.2, 0.5, 0.5, 0.26), (0.55, 0.6, 0.3, 0.2),
           (-0.75, 0.15, 0.2, 0.3)]


def tierra(ctx, x, y, R, t, ojos="open", boca="smile", ceja=None, look=(0, 0), a=1.0, lentes=0.0):
    if a <= 0.01:
        return
    ctx.save()
    ctx.push_group()
    _elipse_suave(ctx, x, y, R * 1.9, R * 1.9, AZUL_T, 0.25)
    ctx.arc(x, y, R, 0, TAU)
    ctx.set_source_rgb(*AZUL_T)
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    for mx, my, rx, ry in MANCHAS:
        ctx.save()
        ctx.translate(x + mx * R, y + my * R)
        ctx.scale(rx * R, ry * R)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.set_source_rgb(*VERDE_T)
        ctx.fill()
    ctx.restore()
    ctx.arc(x, y, R, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(3, R * 0.07))
    ctx.stroke()
    cara(ctx, x, y, R, ojos, boca, ceja, look)
    if lentes > 0.02:
        ctx.push_group()
        yy = y - 0.06 * R
        for sx in (-1, 1):
            rrect(ctx, x + sx * 0.31 * R - 0.27 * R, yy - 0.2 * R, 0.54 * R, 0.38 * R, 0.14 * R)
        ctx.set_source_rgb(*INK)
        ctx.fill()
        ctx.move_to(x - 0.6 * R, yy - 0.1 * R)
        ctx.line_to(x + 0.6 * R, yy - 0.1 * R)
        ctx.set_line_width(R * 0.07)
        ctx.stroke()
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(lentes)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def foton(ctx, x, y, ang, r=16, a=1.0, cola=120, con_cara=False):
    """Un poco de luz en viaje: bolita con estela. ang = hacia dónde va."""
    if a <= 0.01:
        return
    bx, by = x - cola * math.cos(ang), y - cola * math.sin(ang)
    g = cairo.LinearGradient(bx, by, x, y)
    g.add_color_stop_rgba(0, *LUZ, 0)
    g.add_color_stop_rgba(1, *LUZ, 0.85 * a)
    ctx.set_source(g)
    ctx.set_line_width(r * 1.1)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(bx, by)
    ctx.line_to(x, y)
    ctx.stroke()
    _elipse_suave(ctx, x, y, r * 2.8, r * 2.8, LUZ, 0.5 * a)
    ctx.arc(x, y, r, 0, TAU)
    ctx.set_source_rgba(*hx("#FFF6C8"), a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(max(2, r * 0.16))
    ctx.stroke()
    if con_cara and r > 12 and a > 0.6:
        carita(ctx, x, y - 1, 0.7 * r, r / 62, ojos="dot", boca="smile")


def punteada(ctx, x0, y0, x1, y1, col, w=5, a=1.0, paso=(14, 16), fase=0.0):
    if a <= 0.01:
        return
    ctx.save()
    ctx.set_source_rgba(*col, a)
    ctx.set_line_width(w)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_dash(list(paso), fase)
    ctx.move_to(x0, y0)
    ctx.line_to(x1, y1)
    ctx.stroke()
    ctx.restore()


def tachado(ctx, x, y, w, p, ang=-8, grosor=18, a=1.0):
    """Línea roja que tacha de izquierda a derecha."""
    if p <= 0.01 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(ang))
    for lw, col in ((grosor + 12, INK), (grosor, ROJO)):
        ctx.move_to(-w / 2, 0)
        ctx.line_to(-w / 2 + w * p, 0)
        ctx.set_line_width(lw)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgba(*col, a)
        ctx.stroke()
    ctx.restore()


def cruz(ctx, x, y, r, s=1.0, a=1.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for lw, col in ((r * 0.5, INK), (r * 0.3, ROJO)):
        for sg in (-1, 1):
            ctx.move_to(-r, -r * sg)
            ctx.line_to(r, r * sg)
        ctx.set_line_width(lw)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgba(*col, a)
        ctx.stroke()
    ctx.restore()


def tilde(ctx, x, y, r, s=1.0, a=1.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for lw, col in ((r * 0.52, INK), (r * 0.32, VERDE)):
        ctx.move_to(-r, 0)
        ctx.line_to(-r * 0.3, r * 0.7)
        ctx.line_to(r, -r * 0.8)
        ctx.set_line_width(lw)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgba(*col, a)
        ctx.stroke()
    ctx.restore()


def zoom(ctx, z, cx=540, cy=900):
    z = max(z, 0.01)
    ctx.translate(cx, cy)
    ctx.scale(z, z)
    ctx.translate(-cx, -cy)


# ------------------------------------------------------------------ Vos (solo en la apertura y en el empalme)
@functools.lru_cache(maxsize=None)
def vos_surface(ojos):
    body = kit.vos(eyes=ojos, brows="up", mouth_kind="o", look=(0.15, -1))
    png = cairosvg.svg2png(bytestring=kit.svg(520, 820, body).encode(), output_width=1040, output_height=1640)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


def vos(ctx, x, y, k=1.0, alpha=1.0, ojos="wide"):
    """Vos con los pies en (x, y); k = 1 es el dibujo a 520x820."""
    if alpha <= 0.01 or k <= 0.01:
        return
    s = vos_surface(ojos)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(k / 2, k / 2)
    ctx.translate(-520, -1612)
    ctx.set_source_surface(s, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


# ------------------------------------------------------------------ el paisaje: loma, cielo y el signo de pregunta
def loma(ctx, a=1.0):
    ctx.move_to(-10, 1560)
    ctx.curve_to(240, 1380, 400, 1318, 560, 1318)
    ctx.curve_to(760, 1318, 900, 1420, 1090, 1500)
    ctx.line_to(1090, 1930)
    ctx.line_to(-10, 1930)
    ctx.close_path()
    ctx.set_source_rgba(*LOMA, a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*hx("#2B3A78"), a)
    ctx.set_line_width(6)
    ctx.stroke()


def _q_pts():
    """Puntos del signo de pregunta (centro 540, 560)."""
    pts = []
    cx, cy, R = 540, 395, 150
    for i in range(9):                         # el gancho: de arriba a la izquierda hasta abajo
        ang = math.radians(-165 + i * 255 / 8)
        pts.append((cx + R * math.cos(ang), cy + R * math.sin(ang)))
    pts.append((540, 595))
    pts.append((540, 675))
    return pts


Q_PTS = _q_pts()
Q_DOT = (540, 800)
_r = rng(31)
Q_ORIGEN = [(float(_r.uniform(60, 1020)), float(_r.uniform(80, 1150))) for _ in range(len(Q_PTS) + 1)]


def pregunta(ctx, t, forma=1.0, a=1.0, pulso=1.0):
    """El '?' hecho de estrellas. forma 0 = estrellas sueltas, 1 = formado."""
    if a <= 0.01:
        return
    f = ease(forma, "inout")
    pts = [(lerp(o[0], p[0], f), lerp(o[1], p[1], f)) for o, p in zip(Q_ORIGEN, Q_PTS + [Q_DOT])]
    cuerpo, punto = pts[:-1], pts[-1]
    la = a * clamp((forma - 0.75) / 0.25)
    if la > 0.01:
        ctx.save()
        ctx.set_source_rgba(*LUZ, 0.55 * la)
        ctx.set_line_width(7)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.move_to(*cuerpo[0])
        for p in cuerpo[1:]:
            ctx.line_to(*p)
        ctx.stroke()
        ctx.restore()
    for i, (x, y) in enumerate(pts):
        r = (30 if i == len(pts) - 1 else 21) * pulso * lerp(0.45, 1.0, f)
        estrella(ctx, x, y, r, a * titila(t, i * 1.3, 18 + i), col=LUZ)


VOS_XY = (540, 1338)
VOS_K = 0.56


def parpadeo(t):
    return "closed" if (t % 3.1) > 2.98 else "wide"


# ------------------------------------------------------------------ 1. gancho: el "?" en el cielo y el Sol que se va
T_EXPL = b(0, "explicacion")
T_OBVIO = b(1, "obvio")
T_SOL1 = b(1, "Sol")
T_ES = b(1, "es")
T_FUE = b(1, "fue")
SOL_X = 870


def sol_y(t):
    sube = prog(t, T_ES - 0.1, 0.5, "out")
    baja = prog(t, T_SOL1 + 0.15, T_FUE + 0.22 - (T_SOL1 + 0.15), "in")
    return lerp(1560, 1010, sube) + 560 * baja


def d_inicio(ctx, t):
    z = 1 + 0.035 * prog(t, 0, b(2), "inout")
    ctx.save()
    zoom(ctx, z, 540, 1000)
    dia = prog(t, T_ES - 0.15, 0.5) * sale(t, T_FUE - 0.15, 0.4)
    qa = 1 - 0.8 * prog(t, T_OBVIO - 0.2, 0.35)
    pulso = bump(t, T_EXPL - 0.05, 0.4, 0.22) * (1 + 0.03 * math.sin(TAU * 3 * t / TOTAL * 9))
    fondo(ctx, t, 0.35)
    campo(ctx, t, 7, 70, 1 - 0.75 * dia, y1=1240)
    if dia > 0.01:                               # el cielo de la tarde
        g = cairo.LinearGradient(0, 300, 0, 1500)
        g.add_color_stop_rgba(0, 0.25, 0.35, 0.8, 0.0)
        g.add_color_stop_rgba(0.55, 0.95, 0.5, 0.35, 0.42 * dia)
        g.add_color_stop_rgba(1, 1.0, 0.72, 0.3, 0.7 * dia)
        ctx.set_source(g)
        ctx.paint()
    pregunta(ctx, t, 1.0, qa, pulso)
    if t >= T_ES - 0.1:
        mira = (-0.6, -0.2)
        boca = "grin" if t < T_SOL1 + 0.15 else "o"
        sol(ctx, SOL_X, sol_y(t), 135, t, ojos="open" if t < T_SOL1 + 0.15 else "wide", boca=boca, look=mira)
    loma(ctx)
    vos(ctx, VOS_XY[0], VOS_XY[1], VOS_K, ojos=parpadeo(t))
    ctx.restore()
    if t >= T_OBVIO - 0.15:
        s = pop(t, T_OBVIO - 0.15) * sale(t, b(2) - 0.3)
        cartel(ctx, "¿OBVIO?", 300, 330, 92, s=s, rot=-5)
    if t >= T_FUE - 0.1:
        s = pop(t, T_FUE - 0.1) * sale(t, b(2) - 0.3)
        cartel(ctx, "SE FUE EL SOL", 650, 520, 62, box=BLANCO, s=s, rot=4)


# ------------------------------------------------------------------ 2. el Sol es una estrella entre muchísimas
T_SOLO = b(2, "solo")
T_ESTR = b(2, "estrella")
T_MUCH = b(2, "muchisimas")
_r = rng(11)
MUCHAS = [(float(_r.uniform(-1, 1)), float(_r.uniform(-1, 1)), float(_r.uniform(6, 20)), float(_r.uniform(0, TAU)),
           int(_r.integers(14, 40)), float(_r.uniform(0, 1))) for _ in range(260)]


def d_muchas(ctx, t):
    fondo(ctx, t, 0.45)
    p = prog(t, b(2) + 0.1, T_ESTR + 0.25 - b(2), "inout")          # la cámara se aleja
    p2 = prog(t, T_MUCH - 0.1, b(2, fin=True) + 0.4 - T_MUCH, "out")
    esc = lerp(2.6, 1.0, p) * lerp(1.0, 0.62, p2)
    cx, cy = 540, 830
    n = int(lerp(0, 90, p) + 170 * p2)
    for i, (ux, uy, r, ph, k, _) in enumerate(MUCHAS[:n]):
        x, y = cx + ux * 620 * esc, cy + uy * 760 * esc
        if math.hypot(x - cx, y - cy) < 70 * esc + 30:
            continue
        nace = pop(t, b(2) + 0.1 + 0.9 * i / 90, 0.3) if i < 90 else pop(t, T_MUCH - 0.1 + 0.5 * (i - 90) / 170, 0.3)
        estrella(ctx, x, y, r * lerp(1.2, 0.8, p2) * nace, titila(t, ph, k), col=BLANCO if i % 4 else LUZ, halo=0.7)
    R = lerp(250, 24, p) * lerp(1.0, 0.75, p2)
    sol(ctx, cx, cy, R, t, ojos="wide" if p > 0.3 else "open", boca="o" if p > 0.3 else "smile",
        con_cara=1 - clamp((p - 0.55) / 0.3))
    if t >= T_ESTR - 0.1:
        s = pop(t, T_ESTR - 0.1)
        cartel(ctx, "EL SOL", 760, 640, 64, s=s, rot=4)
        if s > 0.5:
            P.flecha(ctx, 700, 700, cx + 46, cy - 38, t, color=AMARILLO, w=12, curva=0.3)
    if t >= T_MUCH - 0.05:
        cartel(ctx, "UNA ENTRE MUCHÍSIMAS", 540, 330, 70, box=BLANCO, s=pop(t, T_MUCH - 0.05), rot=-2)


# ------------------------------------------------------------------ 3. la idea vieja: infinito y eterno
T_INF = b(3, "infinito")
T_ETE = b(3, "eterno")
_r = rng(5)
VUELO = [(float(_r.uniform(0, TAU)), float(_r.uniform(0, 1)), float(_r.uniform(0.6, 1.4))) for _ in range(150)]


def vuelo(ctx, t, a=1.0, vel=0.16, cx=540, cy=860):
    """Estrellas que vienen de frente: profundidad sin fin."""
    for ang, z0, m in VUELO:
        z = (z0 + t * vel * m) % 1.0
        d = 40 + 1150 * z * z
        x, y = cx + d * math.cos(ang), cy + d * math.sin(ang) * 1.25
        estrella(ctx, x, y, 2 + 13 * z * z, a * clamp(z * 4) * clamp((1 - z) * 6), halo=0.6)


def infinito(ctx, x, y, s, a=1.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for lw, col in ((34, INK), (20, CIAN)):
        ctx.move_to(0, 0)
        ctx.curve_to(60, -90, 170, -70, 170, 0)
        ctx.curve_to(170, 70, 60, 90, 0, 0)
        ctx.curve_to(-60, -90, -170, -70, -170, 0)
        ctx.curve_to(-170, 70, -60, 90, 0, 0)
        ctx.set_line_width(lw)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgba(*col, a)
        ctx.stroke()
    ctx.restore()


def reloj_sin_fin(ctx, x, y, s, t, a=1.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.arc(0, 0, 92, 0, TAU)
    ctx.set_source_rgba(*BLANCO, a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(14)
    ctx.stroke()
    for i in range(12):
        an = TAU * i / 12
        ctx.move_to(70 * math.cos(an), 70 * math.sin(an))
        ctx.line_to(80 * math.cos(an), 80 * math.sin(an))
    ctx.set_line_width(7)
    ctx.stroke()
    for L, w, v in ((62, 10, 5.0), (40, 13, 0.6)):
        an = t * v - math.pi / 2
        ctx.move_to(0, 0)
        ctx.line_to(L * math.cos(an), L * math.sin(an))
        ctx.set_line_width(w)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    ctx.restore()


def d_infinito(ctx, t):
    fondo(ctx, t, 0.45)
    z = 1 + 0.04 * prog(t, b(3), b(4) - b(3))
    ctx.save()
    zoom(ctx, z, 540, 860)
    vuelo(ctx, t)
    ctx.restore()
    cartel(ctx, "ANTES SE CREÍA...", 540, 300, 62, box=BLANCO, s=pop(t, b(3) + 0.05), rot=-2)
    if t >= T_INF - 0.15:
        s = pop(t, T_INF - 0.15)
        infinito(ctx, 540, 610, 0.95 * s)
        cartel(ctx, "INFINITO", 540, 790, 110, s=s, rot=-3)
    if t >= T_ETE - 0.15:
        s = pop(t, T_ETE - 0.15)
        reloj_sin_fin(ctx, 300, 1080, 0.9 * s, t)
        cartel(ctx, "ETERNO", 640, 1080, 110, s=s, rot=3)


# ------------------------------------------------------------------ 4. estrellas en todas las direcciones -> el cielo blanco
TC = (540, 880)                                  # la Tierra, en el centro
TR = 104
_r = rng(23)
CAPAS = []                                       # (radio, [(ang, r, ph, k)])
for _i, (_rad, _n, _sz) in enumerate([(210, 9, 21), (330, 14, 18), (450, 20, 15), (570, 26, 13), (700, 34, 11),
                                      (840, 42, 9), (990, 52, 8)]):
    CAPAS.append((_rad, [(TAU * j / _n + float(_r.uniform(-0.12, 0.12)) + 0.3 * _i,
                          _sz * float(_r.uniform(0.8, 1.2)), float(_r.uniform(0, TAU)), int(_r.integers(14, 40)),
                          float(_r.uniform(-18, 18))) for j in range(_n)]))
RELLENO = [(float(_r.uniform(0, W)), float(_r.uniform(0, H)), float(_r.uniform(5, 15)), float(_r.uniform(0, 1)))
           for _ in range(900)]
T_TODAS = b(4, "todas")
T_BRILLA = b(6, "brillaria")
T_SUPERF = b(6, "superficie")
T_NOEX = b(7)
T_NOCHE7 = b(7, "noche")
# rayos de la vista: (momento, capa, índice de estrella), siempre hacia una estrella que se ve en pantalla
def _elige(grados, capas=(1, 2, 3)):
    mejor, d0 = None, 9
    for ci in capas:
        rad, st = CAPAS[ci]
        for j, (ang, r, ph, k, dr) in enumerate(st):
            x, y = TC[0] + (rad + dr) * math.cos(ang), TC[1] + (rad + dr) * 1.12 * math.sin(ang)
            d = abs((ang - math.radians(grados) + math.pi) % TAU - math.pi)
            if 90 < x < 990 and 430 < y < 1330 and d < d0:
                mejor, d0 = (ci, j), d
    return mejor


RAYOS = [(b(5) + 0.0, *_elige(95, (2,))), (b(5, "donde") + 0.0, *_elige(-50, (1,))),
         (b(5, "tu") - 0.05, *_elige(205, (2, 3))), (b(5, "terminaria") + 0.1, *_elige(20, (2,))),
         (b(5, "estrella") - 0.1, *_elige(-125, (3,)))]


def pos_capa(ci, j):
    rad, st = CAPAS[ci]
    ang, r, ph, k, dr = st[j]
    return TC[0] + (rad + dr) * math.cos(ang), TC[1] + (rad + dr) * 1.12 * math.sin(ang), r, ph, k


def d_lleno(ctx, t):
    fondo(ctx, t, 0.45)
    z = 1 + 0.05 * prog(t, b(4), b(8) - b(4))
    ctx.save()
    zoom(ctx, z, *TC)
    blanco = ease(clamp((t - (b(6) + 0.1)) / (T_SUPERF + 0.3 - b(6))), "inout")
    # capas de estrellas que van apareciendo, cada vez más lejos
    for ci in range(len(CAPAS)):
        t0 = b(4) + 0.25 + ci * (b(4, fin=True) - b(4)) / len(CAPAS)
        for j in range(len(CAPAS[ci][1])):
            x, y, r, ph, k = pos_capa(ci, j)
            s = pop(t, t0 + 0.02 * j, 0.3)
            golpe = 1.0
            for tr, rc, rj in RAYOS:
                if rc == ci and rj == j:
                    golpe = bump(t, tr + 0.32, 0.45, 0.9)
            estrella(ctx, x, y, r * s * golpe * (1 + 1.4 * blanco), titila(t, ph, k), col=LUZ if golpe > 1.01 else BLANCO)
    # relleno: no queda ningún hueco
    if t >= b(6):
        n = int(len(RELLENO) * clamp((t - b(6)) / (T_SUPERF + 0.2 - b(6))))
        for x, y, r, u in RELLENO[:n]:
            estrella(ctx, x, y, r * (1 + 1.6 * blanco), 0.9, col=LUZ, halo=0.8)
    # los rayos de la vista
    for i, (tr, rc, rj) in enumerate(RAYOS):
        if t < tr:
            continue
        x, y, r, _, _ = pos_capa(rc, rj)
        p = prog(t, tr, 0.32, "out")
        a = sale(t, b(6) + 0.1, 0.4) * (1.0 if i == len(RAYOS) - 1 or t < RAYOS[i + 1][0] else 0.45)
        dx, dy = x - TC[0], y - TC[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        punteada(ctx, TC[0] + ux * (TR + 14), TC[1] + uy * (TR + 14), TC[0] + ux * lerp(TR + 14, L - r, p),
                 TC[1] + uy * lerp(TR + 14, L - r, p), AMARILLO, w=9, a=a, paso=(20, 16), fase=-t * 60)
        if p >= 1 and a > 0.5:
            q = clamp((t - tr - 0.32) / 0.5)
            ctx.arc(x, y, r + 50 * q, 0, TAU)
            ctx.set_source_rgba(*AMARILLO, 0.8 * (1 - q))
            ctx.set_line_width(7)
            ctx.stroke()
    ctx.restore()
    # el resplandor: el cielo entero brilla
    if blanco > 0.005:
        ctx.set_source_rgba(*hx("#FFE9A0"), min(1.0, 1.25 * blanco) * 0.97)
        ctx.paint()
        _elipse_suave(ctx, 540, 880, 900, 1200, BLANCO, 0.8 * blanco)
    # la Tierra mira hacia donde apunta el rayo
    look, ojos, boca, ceja = (0, 0), "open", "smile", None
    act = [r for r in RAYOS if t >= r[0]]
    if act and t < b(6):
        x, y, *_ = pos_capa(act[-1][1], act[-1][2])
        L = math.hypot(x - TC[0], y - TC[1])
        look = ((x - TC[0]) / L, (y - TC[1]) / L)
    if t >= b(4) and t < b(5):
        an = (t - b(4)) * 3.0
        look = (math.cos(an), math.sin(an))
        ojos = "wide"
    if t >= T_BRILLA - 0.1:
        ojos, boca, ceja = "closed", "wavy", "worried"
    lentes = pop(t, T_NOEX + 0.05, 0.3) if t >= T_NOEX else 0.0
    if lentes > 0.5:
        boca, ceja = "flat", None
    ctx.save()
    zoom(ctx, z, *TC)
    tierra(ctx, TC[0], TC[1], TR, t, ojos=ojos, boca=boca, ceja=ceja, look=look, lentes=min(1.0, lentes))
    ctx.restore()
    if b(5, "estrella") - 0.25 <= t:
        s = pop(t, b(5, "estrella") - 0.25) * sale(t, b(6) + 0.1)
        cartel(ctx, "SIEMPRE HAY UNA ESTRELLA", 540, 300, 62, s=s, rot=-2)
    if t >= T_SUPERF - 0.1:
        s = pop(t, T_SUPERF - 0.1) * sale(t, T_NOEX - 0.1)
        cartel(ctx, "TODO EL CIELO = SOL", 540, 320, 72, box=SOL, s=s, rot=-2)
    if t >= T_NOEX:
        s = pop(t, T_NOEX)
        cartel(ctx, "NOCHE", 540, 400, 150, box=hx("#1B2456"), fg=BLANCO, s=s, rot=-4)
        tachado(ctx, 540, 400, 520 * s, prog(t, T_NOCHE7 - 0.15, 0.3, "out"), ang=-14, grosor=26)


# ------------------------------------------------------------------ 5. pero la noche existe: algo estaba mal
T_EXISTE = b(8, "existe")
T_ALGO = b(8, "algo")
T_ASI = b(8, "asi")
T_MAL = b(8, "mal")


def d_existe(ctx, t):
    fondo(ctx, t, 0.45)
    campo(ctx, t, 9, 60, 1.0, y1=1350)
    baja = prog(t, T_ASI - 0.1, 0.5)
    ty = lerp(TC[1], 1180, baja)
    feliz = t < T_ASI
    tierra(ctx, TC[0], ty, lerp(TR, 66, baja), t, ojos="happy" if feliz else "open", boca="grin" if feliz else "flat",
           ceja=None if feliz else "worried", look=(0, -0.8) if not feliz else (0, 0),
           lentes=sale(t, b(8) + 0.25, 0.25))
    if t < T_ASI + 0.3:
        s = pop(t, T_EXISTE - 0.2) * sale(t, T_ASI - 0.1)
        cartel(ctx, "LA NOCHE EXISTE", 540, 420, 84, box=hx("#1B2456"), fg=BLANCO, s=s, rot=-3)
    if t >= T_ASI + 0.12:
        tiembla = 9 * math.sin(t * 46) * sale(t, T_MAL + 0.5, 0.4) * clamp((t - T_ALGO) / 0.2)
        s1 = pop(t, T_ASI + 0.12)
        s2 = pop(t, T_ASI + 0.32)
        cartel(ctx, "INFINITO", 400 + tiembla, 520, 92, s=s1, rot=-5)
        cartel(ctx, "ETERNO", 680 - tiembla, 700, 92, s=s2, rot=4)
    if t >= T_MAL - 0.15:
        s = pop(t, T_MAL - 0.15, 0.25)
        cartel(ctx, "ALGO FALLA", 540, 910, 96, box=ROJO, fg=BLANCO, s=s * (1 + 0.5 * (1 - clamp((t - T_MAL + 0.15) / 0.2))),
               rot=-9)
    fl = 1 - prog(t, b(8) - 0.08, 0.45, "out")       # venimos del cielo blanco
    if fl > 0.005:
        ctx.set_source_rgba(*hx("#FFE9A0"), 0.97 * fl)
        ctx.paint()
        _elipse_suave(ctx, 540, 880, 900, 1200, BLANCO, 0.8 * fl)


# ------------------------------------------------------------------ 6. el telescopio (un astrónomo no fue)
T_PISTA = b(9, "pista")
T_NO9 = b(9, "no")
T_ASTRO = b(9, "astronomo")


def telescopio(ctx, x, y, s, t, feliz=False, a=1.0):
    """Telescopio con cara sobre un trípode. (x, y) = donde se unen las patas."""
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.push_group()
    for dx in (-110, 0, 110):                    # patas
        ctx.move_to(0, 0)
        ctx.line_to(dx, 300)
        for lw, col in ((34, INK), (18, hx("#8A6A45"))):
            ctx.set_line_width(lw)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_source_rgb(*col)
            ctx.stroke_preserve()
        ctx.new_path()
    ctx.rotate(math.radians(-32 + 1.5 * math.sin(t * 1.6)))
    rrect(ctx, -250, -78, 440, 156, 30)          # tubo
    ctx.set_source_rgb(*hx("#E9EEF7"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(12)
    ctx.stroke()
    rrect(ctx, 170, -98, 110, 196, 26)           # boca
    ctx.set_source_rgb(*hx("#4D6FE0"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    rrect(ctx, -330, -40, 90, 80, 18)            # ocular
    ctx.set_source_rgb(*hx("#4D6FE0"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.rotate(math.radians(32))
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()
    # la cara va derecha, sobre el tubo
    fx, fy = x - 30 * s, y - 20 * s
    if feliz:
        carita(ctx, fx, fy, 96 * s, 0.82 * s, ojos="happy", boca="grin", rubor=True)
    else:
        carita(ctx, fx, fy, 96 * s, 0.82 * s, ojos="open", boca="wavy", ceja="worried", look=(0.6, -0.7))


def d_astronomo(ctx, t):
    fondo(ctx, t, 0.45)
    campo(ctx, t, 9, 60, 1.0, y1=1350)
    z = 1 + 0.05 * prog(t, b(9), b(10) - b(9))
    ctx.save()
    zoom(ctx, z, 540, 900)
    sube = pop(t, b(9) + 0.0, 0.4)
    telescopio(ctx, 540, 900 + 500 * (1 - min(1, sube)), 1.0, t)
    for i in range(3):                           # piensa y no le sale
        if t >= b(9) + 0.5 + 0.22 * i and t < T_NO9:
            ctx.arc(760 + 46 * i, 560 - 30 * i, 12 + 5 * i, 0, TAU)
            ctx.set_source_rgb(*BLANCO)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(5)
            ctx.stroke()
    cruz(ctx, 540, 840, 170, pop(t, T_NO9 - 0.1, 0.3), 0.92)
    ctx.restore()
    cartel(ctx, "LA PRIMERA PISTA", 540, 310, 76, s=pop(t, T_PISTA - 0.2), rot=-2)
    cartel(ctx, "NO FUE UN ASTRÓNOMO", 540, 1290, 62, box=BLANCO, s=pop(t, T_ASTRO - 0.15), rot=2)


# ------------------------------------------------------------------ 7. Poe: la escribió un autor de cuentos de terror
T_ESCR = b(10, "escribio")
T_TERROR = b(10, "terror")
T_POE = b(10, "Edgar")
T_IDEA = b(11, "idea")
T_SIMPLE = b(11, "simple")
HOJA = (540, 800, 500, 640)
RENGLONES = [(-190, -230, 380), (-190, -160, 330), (-190, -90, 370), (-190, -20, 300), (-190, 50, 360), (-190, 120, 240)]


def pluma(ctx, x, y, s, rot):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.scale(s, s)
    ctx.move_to(0, 0)
    ctx.curve_to(60, -80, 70, -230, 20, -330)
    ctx.curve_to(-50, -250, -60, -120, 0, 0)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#E9EEF7"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.move_to(0, 26)
    ctx.line_to(14, -300)
    ctx.set_line_width(7)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.restore()


def cuervo(ctx, x, y, s, t):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    bob = 4 * math.sin(t * 2.2)
    ctx.translate(0, bob)
    ctx.move_to(-70, 40)                         # cola
    ctx.line_to(-170, 90)
    ctx.line_to(-80, 80)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#1B1E2E"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.save()                                   # cuerpo
    ctx.scale(1.0, 0.82)
    ctx.arc(0, 30, 96, 0, TAU)
    ctx.restore()
    ctx.set_source_rgb(*hx("#22263A"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.arc(62, -62, 60, 0, TAU)                 # cabeza
    ctx.set_source_rgb(*hx("#22263A"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.move_to(112, -78)                        # pico
    ctx.line_to(196, -52)
    ctx.line_to(114, -36)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#F0B429"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    cerrado = (t % 2.7) > 2.58
    if cerrado:
        ctx.move_to(60, -72)
        ctx.line_to(96, -72)
        ctx.set_source_rgb(*BLANCO)
        ctx.set_line_width(7)
        ctx.stroke()
    else:
        ctx.arc(78, -74, 19, 0, TAU)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()
        ctx.arc(84, -72, 8, 0, TAU)
        ctx.set_source_rgb(*INK)
        ctx.fill()
    for dx in (-22, 22):                         # patas
        ctx.move_to(dx, 104)
        ctx.line_to(dx, 138)
        ctx.set_source_rgb(*hx("#F0B429"))
        ctx.set_line_width(9)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    ctx.restore()


def murcielago(ctx, x, y, s, t, a=1.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    al = 0.55 + 0.45 * math.sin(t * 16)
    ctx.move_to(0, -14)
    for sg in (1, -1):
        ctx.curve_to(sg * 30, -50 * al, sg * 70, -60 * al, sg * 110, -20 * al)
        ctx.curve_to(sg * 84, -8, sg * 70, 8, sg * 60, 26)
        ctx.curve_to(sg * 44, 6, sg * 26, 8, 0, 30)
        if sg == 1:
            ctx.line_to(0, -14)
    ctx.close_path()
    ctx.set_source_rgba(*hx("#2B3270"), a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*hx("#7C89E0"), a)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.restore()


def bombita(ctx, x, y, s, t, a=1.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    _elipse_suave(ctx, 0, -20, 330, 330, LUZ, 0.55 * a * (0.85 + 0.15 * math.sin(t * 7)))
    for i in range(8):
        an = TAU * i / 8 + t * 0.6
        ctx.move_to(170 * math.cos(an), -20 + 170 * math.sin(an))
        ctx.line_to(215 * math.cos(an), -20 + 215 * math.sin(an))
    ctx.set_source_rgba(*AMARILLO, a)
    ctx.set_line_width(14)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.arc(0, -30, 118, math.radians(125), math.radians(55))
    ctx.line_to(46, 110)
    ctx.line_to(-46, 110)
    ctx.close_path()
    ctx.set_source_rgba(*hx("#FFE56B"), a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(12)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    rrect(ctx, -50, 110, 100, 62, 14)
    ctx.set_source_rgba(*hx("#AEB6C8"), a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.stroke()
    carita(ctx, 0, -40, 84, 0.72, ojos="happy", boca="grin", rubor=True)
    ctx.restore()


def d_poe(ctx, t):
    fondo(ctx, t, 0.62)
    # luna pálida y murciélagos: clima de cuento de terror
    ml = prog(t, b(10), 0.5, "out")
    _elipse_suave(ctx, 830, 370, 330, 330, hx("#C9D3FF"), 0.22 * ml)
    ctx.arc(830, 370, 140 * ml, 0, TAU)
    ctx.set_source_rgb(*hx("#E6E9F5"))
    ctx.fill()
    for cxm, cym, rm in ((790, 330, 26), (870, 420, 18), (850, 300, 12)):
        ctx.arc(cxm, cym, rm * ml, 0, TAU)
        ctx.set_source_rgba(*hx("#B9C0DA"), 0.9)
        ctx.fill()
    if t >= T_TERROR - 0.5:
        for i, (x0, y0, v) in enumerate(((1180, 420, 330), (1260, 560, 300), (-120, 360, -310))):
            dt = t - (T_TERROR - 0.5) - 0.12 * i
            if dt > 0:
                murcielago(ctx, x0 - v * dt, y0 - 46 * dt + 26 * math.sin(dt * 5 + i), 0.9 - 0.12 * i, t + i)
    apaga = prog(t, T_IDEA - 0.1, 0.4)
    z = 1 + 0.05 * prog(t, b(10), b(12) - b(10))
    ctx.save()
    zoom(ctx, z, 540, 900)
    ctx.push_group()
    x, y, w, h = HOJA
    sp = pop(t, b(10) + 0.0, 0.4)
    ctx.save()
    ctx.translate(x, y + 700 * (1 - min(1, sp)))
    ctx.rotate(math.radians(-4))
    rrect(ctx, -w / 2 + 14, -h / 2 + 18, w, h, 22)
    ctx.set_source_rgba(0, 0, 0, 0.45)
    ctx.fill()
    rrect(ctx, -w / 2, -h / 2, w, h, 22)
    ctx.set_source_rgb(*PAPEL)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(10)
    ctx.stroke()
    # renglones que se escriben
    avance = clamp((t - T_ESCR) / max(0.1, T_POE - T_ESCR + 0.4)) * len(RENGLONES)
    px, py = RENGLONES[0][0], RENGLONES[0][1]
    for i, (rx, ry, rl) in enumerate(RENGLONES):
        p = clamp(avance - i)
        if p <= 0:
            continue
        ctx.move_to(rx, ry)
        n = 24
        for kk in range(1, int(n * p) + 1):
            xx = rx + rl * kk / n
            ctx.line_to(xx, ry + 9 * math.sin(kk * 1.9 + i))
            px, py = xx, ry + 9 * math.sin(kk * 1.9 + i)
        ctx.set_source_rgb(*hx("#3A3350"))
        ctx.set_line_width(7)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    if t >= T_POE - 0.1:                          # la firma
        texto(ctx, "E. A. Poe", 60, 230, 62, fill=hx("#3A3350"), stroke=None, alpha=prog(t, T_POE - 0.1, 0.4))
    if t >= T_ESCR - 0.2:
        pluma(ctx, px + 4, py - 6, 1.0 * pop(t, T_ESCR - 0.2, 0.3), 24 + 5 * math.sin(t * 13))
    ctx.restore()
    if t >= b(10, "autor") - 0.15:
        cuervo(ctx, 300, 420, 0.95 * pop(t, b(10, "autor") - 0.15, 0.35), t)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(1 - 0.6 * apaga)
    ctx.restore()
    if t >= T_POE - 0.15 and t < T_IDEA + 0.3:
        s = pop(t, T_POE - 0.15) * sale(t, T_IDEA - 0.15)
        cartel(ctx, "EDGAR ALLAN POE", 540, 1215, 82, s=s, rot=-2)
        cartel(ctx, "«EUREKA», 1848", 740, 1322, 46, box=BLANCO, s=pop(t, T_POE + 0.35) * sale(t, T_IDEA - 0.15), rot=3)
    if t >= T_IDEA - 0.1:
        bombita(ctx, 540, 700, pop(t, T_IDEA - 0.1, 0.4) * (1 + 0.5 * prog(t, b(12) - 0.3, 0.3, "in")), t)
        cartel(ctx, "UNA IDEA SIMPLE", 540, 1225, 80, s=pop(t, T_SIMPLE - 0.15), rot=-2)


# ------------------------------------------------------------------ 8. la luz tarda en viajar
E_W = (540, 1130)                                # la Tierra (mundo)
S1 = (540, 300)                                  # estrella cercana
LEJ = [((-420, -560), 0.36), ((1500, -860), 0.30), ((600, -1500), 0.22)]     # lejanas: (posición, cuánto recorrió su luz)
T_LLEGA = b(12, "llega")
T_TARDA = b(12, "tarda")
T_VIAJ = b(12, "viajar")
T_LEJ = b(13, "lejanas")
T_TODAV = b(13, "todavia")
T_AQUI = b(13, "aqui")
T_SALE = b(12) + 0.15
T_ARRIBA = b(12, fin=True) + 0.15                # la luz de la cercana llega a la Tierra


def d_luz(ctx, t):
    fondo(ctx, t, 0.5)
    campo(ctx, t, 13, 40, 0.5, y1=1400)
    zc = lerp(1.0, 0.37, prog(t, b(13) - 0.1, T_LEJ + 0.5 - b(13), "inout"))

    def pr(p):
        return 540 + (p[0] - E_W[0]) * zc, E_W[1] + (p[1] - E_W[1]) * zc

    esc = lerp(1.0, 0.6, (1 - zc) / 0.63)
    ex, ey = pr(E_W)
    sx, sy = pr(S1)
    viaje = clamp((t - T_SALE) / (T_ARRIBA - T_SALE))
    llego = t >= T_ARRIBA
    # el camino de la cercana
    punteada(ctx, sx, sy + 110 * esc, ex, ey - 130 * esc, LUZ, w=6 * esc + 2, a=0.5, fase=-t * 40)
    # lejanas: su luz está a mitad de camino
    if t >= b(13) - 0.1:
        for i, (p, f0) in enumerate(LEJ):
            a = prog(t, b(13) + 0.25 * i, 0.4)
            lx, ly = pr(p)
            f = f0 + 0.022 * (t - b(13))
            fx, fy = lerp(lx, ex, f), lerp(ly, ey, f)
            punteada(ctx, fx, fy, ex, ey, GRIS, w=5, a=0.75 * a)
            punteada(ctx, lx, ly, fx, fy, LUZ, w=5, a=0.6 * a, fase=-t * 30)
            ang = math.atan2(ey - ly, ex - lx)
            foton(ctx, fx, fy, ang, r=20, a=a, cola=120, con_cara=True)
            sol(ctx, lx, ly, 58 * a, t + i, ojos="open", boca="smile")
            if t >= T_TODAV - 0.2 + 0.12 * i:
                s = pop(t, T_TODAV - 0.2 + 0.12 * i, 0.3)
                ox, oy = ((-10, 78), (20, 80), (170, 10))[i]
                cartel(ctx, "EN VIAJE", fx + ox, fy + oy, 40, box=BLANCO, s=s, rot=(-4, 4, -3)[i])
    # la cercana y su luz
    sol(ctx, sx, sy, 104 * esc, t, ojos="happy" if llego else "open", boca="grin" if llego else "smile")
    if T_SALE <= t < T_ARRIBA:
        yy = lerp(sy + 120, ey - 140, ease(viaje, "inout"))
        foton(ctx, sx, yy, math.pi / 2, r=30, cola=190, con_cara=True)
        if t >= T_TARDA - 0.1:                    # el reloj corre mientras viaja
            ctx.save()
            ctx.translate(sx + 210, yy - 10)
            reloj_sin_fin(ctx, 0, 0, 0.8 * pop(t, T_TARDA - 0.1, 0.3), (t - T_TARDA) * 2.4)
            ctx.restore()
    look = (0, -1)
    tierra(ctx, ex, ey, 122 * esc, t, ojos="happy" if llego and t < b(13) + 0.3 else "wide" if llego else "open",
           boca="grin" if llego and t < b(13) + 0.3 else "o" if llego else "smile", look=look)
    if llego:
        q = clamp((t - T_ARRIBA) / 0.5)
        ctx.arc(ex, ey, 122 * esc + 90 * q, 0, TAU)
        ctx.set_source_rgba(*LUZ, 0.8 * (1 - q))
        ctx.set_line_width(9)
        ctx.stroke()
    if t < b(13) + 0.2:
        cartel(ctx, "NO LLEGA AL INSTANTE", 540, 700, 64, box=BLANCO, s=pop(t, T_LLEGA - 0.1) * sale(t, T_TARDA - 0.2),
               rot=-3)
        cartel(ctx, "TARDA", 250, 700, 120, s=pop(t, T_TARDA - 0.1) * sale(t, b(13) - 0.1), rot=-6)
    if t >= T_AQUI - 0.5:
        cartel(ctx, "TODAVÍA NO LLEGÓ", 540, 1322, 66, s=pop(t, T_TODAV + 0.25), rot=-2)
    if llego and t >= b(13):
        tilde(ctx, sx - 105, sy - 30, 30, pop(t, b(13) + 0.6, 0.3))


# ------------------------------------------------------------------ 9. no puede ser eterno: tuvo que nacer
T_NOPUEDE = b(14, "no")
T_ETERNO2 = b(14, "eterno")
T_NACER = b(15, "nacer")
BANG = (540, 880)
_r = rng(41)
CHISPAS = [(float(_r.uniform(0, TAU)), float(_r.uniform(0.35, 1.0)), float(_r.uniform(5, 16)), float(_r.uniform(0, TAU)))
           for _ in range(120)]


def estallido(ctx, t, t0, cx, cy, fuerza=1.0, sigue=True):
    """Un punto que estalla: anillos, destello y estrellas que salen."""
    dt = t - t0
    if dt < -0.6:
        return
    if dt < 0:                                   # el punto antes de nacer
        k = (dt + 0.6) / 0.6
        _elipse_suave(ctx, cx, cy, 120 * k, 120 * k, LUZ, 0.7)
        ctx.arc(cx, cy, 10 + 8 * k + 4 * math.sin(t * 30), 0, TAU)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()
        return
    fl = 1 - clamp(dt / 0.5)
    if fl > 0:
        _elipse_suave(ctx, cx, cy, 1400 * (0.3 + dt), 1400 * (0.3 + dt), BLANCO, 0.9 * fl)
    for n in range(4):
        d = dt - 0.18 * n
        if sigue:
            d = d % 2.2 if d > 0 else d
        if d <= 0:
            continue
        R = 560 * fuerza * ease(clamp(d / 2.2), "out")
        ctx.arc(cx, cy, R, 0, TAU)
        ctx.set_source_rgba(*LUZ, 0.6 * (1 - clamp(d / 2.2)))
        ctx.set_line_width(10)
        ctx.stroke()
    for ang, v, r, ph in CHISPAS:
        d = 620 * fuerza * v * ease(clamp(dt / 1.6), "out") + 14 * dt * v
        estrella(ctx, cx + d * math.cos(ang), cy + d * math.sin(ang), r * clamp(dt / 0.25),
                 0.6 + 0.4 * math.sin(t * 5 + ph), col=LUZ if r > 11 else BLANCO, halo=0.7)
    _elipse_suave(ctx, cx, cy, 170, 170, LUZ, 0.55)


def d_eterno(ctx, t):
    fondo(ctx, t, 0.5)
    campo(ctx, t, 17, 45, 0.7 * sale(t, b(15) - 0.2, 0.3), y1=1350)
    cae = prog(t, T_ETERNO2 + 0.45, 0.45, "in")
    if cae < 1:
        tiembla = 10 * math.sin(t * 50) * clamp((t - T_NOPUEDE) / 0.15) * sale(t, T_ETERNO2 + 0.4, 0.2)
        ctx.save()
        ctx.translate(0, 900 * cae)
        reloj_sin_fin(ctx, 540, 600, 1.15 * pop(t, b(14) + 0.05), t)
        cartel(ctx, "ETERNO", 540 + tiembla, 860, 150, s=pop(t, b(14) + 0.15), rot=-3 + 22 * cae)
        tachado(ctx, 540 + tiembla, 860, 560, prog(t, T_NOPUEDE - 0.05, 0.3, "out"), ang=-10 + 22 * cae, grosor=28)
        ctx.restore()
        cruz(ctx, 540, 600 + 900 * cae, 110, pop(t, T_NOPUEDE + 0.1, 0.25), 0.95)
    estallido(ctx, t, T_NACER - 0.05, *BANG)
    if t >= T_NACER - 0.05:
        cartel(ctx, "TUVO UN COMIENZO", 540, 330, 82, s=pop(t, T_NACER + 0.05), rot=-2)


# ------------------------------------------------------------------ 10. un siglo después, la ciencia le dio la razón
T_SIGLO = b(16, "siglo")
T_CIENCIA = b(16, "ciencia")
T_RAZON = b(16, "razon")
LX0, LX1, LY = 190, 890, 1090


def d_ciencia(ctx, t):
    fondo(ctx, t, 0.5)
    campo(ctx, t, 17, 45, 0.7, y1=1350)
    p = prog(t, b(16) + 0.1, T_SIGLO + 0.5 - b(16), "inout")
    xx = lerp(LX0, LX1, p)
    for lw, col in ((26, INK), (14, BLANCO)):
        ctx.move_to(LX0, LY)
        ctx.line_to(xx, LY)
        ctx.set_line_width(lw)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgb(*col)
        ctx.stroke()
    for i in range(1, 10):
        x = lerp(LX0, LX1, i / 10)
        if x < xx:
            ctx.move_to(x, LY - 22)
            ctx.line_to(x, LY + 22)
            ctx.set_source_rgba(*BLANCO, 0.8)
            ctx.set_line_width(6)
            ctx.stroke()
    # 1848: la pluma
    s0 = pop(t, b(16) - 0.05)
    ctx.arc(LX0, LY, 26 * s0, 0, TAU)
    ctx.set_source_rgb(*AMARILLO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    pluma(ctx, LX0 + 6, LY - 60, 0.8 * s0, 14)
    cartel(ctx, "1848", LX0 + 30, LY + 110, 70, s=s0, rot=-3)
    # un siglo después: el telescopio, ahora contento
    if p > 0.98 or t >= T_SIGLO + 0.3:
        s1 = pop(t, T_SIGLO + 0.3)
        ctx.arc(LX1, LY, 26 * s1, 0, TAU)
        ctx.set_source_rgb(*VERDE)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(9)
        ctx.stroke()
    if t >= T_CIENCIA - 0.2:
        s2 = pop(t, T_CIENCIA - 0.2, 0.4)
        telescopio(ctx, 720, 700 + 30 * (1 - min(1, s2)), 0.82 * s2, t, feliz=t >= T_RAZON - 0.3)
    if t >= T_SIGLO - 0.2:
        cartel(ctx, "UN SIGLO DESPUÉS", 730, LY + 110, 54, box=BLANCO, s=pop(t, T_SIGLO - 0.2), rot=3)
    tilde(ctx, 300, 600, 110, pop(t, T_RAZON - 0.1, 0.3) * bump(t, T_RAZON + 0.2, 0.3, 0.12))
    cartel(ctx, "TENÍA RAZÓN", 540, 310, 92, box=VERDE, s=pop(t, T_RAZON - 0.05), rot=-3)


# ------------------------------------------------------------------ 11. hace casi 14.000 millones de años
T_NACIO = b(17, "nacio")
T_CASI = b(17, "casi")
T_MILL = b(17, "millones")
T_ANOS = b(17, "anos")


def fmt(v):
    return f"{int(round(v)):,}".replace(",", ".")


def d_edad(ctx, t):
    fondo(ctx, t, 0.5)
    z = 1 + 0.06 * prog(t, b(17), b(18) - b(17))
    ctx.save()
    zoom(ctx, z, 540, 1040)
    estallido(ctx, t, T_NACIO - 0.1, 540, 1040, fuerza=1.15)
    ctx.restore()
    if t >= T_CASI - 0.15:
        s = pop(t, T_CASI - 0.15)
        v = lerp(0, 13800, prog(t, T_CASI - 0.1, T_MILL + 0.1 - T_CASI, "out"))
        v = round(v / 100) * 100
        ctx.save()
        ctx.translate(540, 470)
        ctx.scale(max(s, 0.01) * bump(t, T_MILL + 0.05, 0.3, 0.1), max(s, 0.01) * bump(t, T_MILL + 0.05, 0.3, 0.1))
        texto(ctx, fmt(v), 0, 0, 230, fill=AMARILLO, sw=16)
        ctx.restore()
    if t >= T_MILL - 0.1:
        cartel(ctx, "MILLONES DE AÑOS", 540, 650, 80, box=BLANCO, s=pop(t, T_MILL - 0.1), rot=-2)


# ------------------------------------------------------------------ 12. la luz solo recorrió una parte del camino
T_LUZ18 = b(18, "luz")
T_PARTE = b(18, "parte")
T_CAMINO = b(18, "camino")
HC = (540, 860)
HR = 345
_r = rng(53)
DENTRO = []
for _i in range(15):
    _a = TAU * _i / 15 + float(_r.uniform(-0.15, 0.15))
    _d = float(_r.uniform(165, HR - 40))
    DENTRO.append((_a, _d, float(_r.uniform(13, 20)), float(_r.uniform(0, TAU)), int(_r.integers(14, 40))))
FUERA = []
for _i in range(18):
    _a = TAU * _i / 18 + float(_r.uniform(-0.1, 0.1))
    _d = float(_r.uniform(HR + 95, HR + 270))
    FUERA.append((_a, _d, float(_r.uniform(11, 17)), float(_r.uniform(0.25, 0.6))))


def d_horizonte(ctx, t):
    fondo(ctx, t, 0.5)
    z = 1 + 0.04 * prog(t, b(18), b(19) - b(18))
    ctx.save()
    zoom(ctx, z, *HC)
    R = HR * prog(t, b(18) + 0.2, T_CAMINO - b(18), "out")
    if R > 2:
        _elipse_suave(ctx, HC[0], HC[1], R * 1.25, R * 1.25, CIAN, 0.16)
        ctx.arc(*HC, R, 0, TAU)
        ctx.set_source_rgba(*CIAN, 0.07)
        ctx.fill()
        ctx.save()
        ctx.arc(*HC, R, 0, TAU)
        ctx.set_source_rgba(*CIAN, 0.95)
        ctx.set_line_width(8)
        ctx.set_dash([26, 18], -t * 30)
        ctx.stroke()
        ctx.restore()
    for ang, d, r, ph, k in DENTRO:               # se ven cuando la luz las alcanza
        x, y = HC[0] + d * math.cos(ang), HC[1] + d * math.sin(ang)
        if R >= d:
            td = b(18) + 0.2 + (T_CAMINO - b(18)) * (1 - math.sqrt(max(0.0, 1 - d / HR)))
            estrella(ctx, x, y, r * bump(t, td, 0.4, 0.5), titila(t, ph, k), col=LUZ)
        else:
            estrella(ctx, x, y, r * 0.7, 0.25, col=GRIS, halo=0)
    for i, (ang, d, r, f0) in enumerate(FUERA):   # las de afuera: su luz sigue en viaje
        x, y = HC[0] + d * math.cos(ang), HC[1] + d * math.sin(ang)
        a = prog(t, b(18) + 0.3 + 0.03 * i, 0.4)
        estrella(ctx, x, y, r, 0.5 * a, col=GRIS, halo=0.2)
        if t >= T_PARTE - 0.4:
            af = prog(t, T_PARTE - 0.4 + 0.02 * i, 0.3)
            dd = lerp(d - 26, HR + 34, f0 + 0.03 * (t - T_PARTE))
            foton(ctx, HC[0] + dd * math.cos(ang), HC[1] + dd * math.sin(ang), ang + math.pi, r=12, a=0.9 * af, cola=60)
    tierra(ctx, HC[0], HC[1], 86, t, ojos="open", boca="smile", look=(0.6 * math.cos(t * 1.4), 0.6 * math.sin(t * 1.4)))
    ctx.restore()
    if t >= T_LUZ18 - 0.1:
        cartel(ctx, "HASTA AQUÍ LLEGÓ LA LUZ", 540, 300, 64, box=CIAN, s=pop(t, T_LUZ18 - 0.1), rot=-2)
    if t >= T_PARTE - 0.1:
        cartel(ctx, "LA DEMÁS SIGUE EN VIAJE", 540, 1322, 58, box=BLANCO, s=pop(t, T_PARTE - 0.1), rot=2)


# ------------------------------------------------------------------ 13. el negro es luz en camino -> vuelve el "?" (loop)
T_ENTRE = b(19, "entre")
T_NEGRO = b(19, "negro")
T_NEGRO2 = b(20, "negro")
T_LUZ20 = b(20, "luz")
T_VIENE = b(20, "viene")
T_FIN = b(21)
HUECOS = [(300, 430, 150), (790, 640, 135), (420, 930, 140)]
_r = rng(67)
VIENEN = []
for _hx, _hy, _hr in HUECOS:
    for _ in range(5):
        _a, _d = float(_r.uniform(0, TAU)), float(_r.uniform(0, _hr * 0.6))
        VIENEN.append((_hx + _d * math.cos(_a), _hy + _d * math.sin(_a), float(_r.uniform(0, 1)),
                       float(_r.uniform(0.7, 1.3))))
for _ in range(10):
    VIENEN.append((float(_r.uniform(80, 1000)), float(_r.uniform(120, 1150)), float(_r.uniform(0, 1)),
                   float(_r.uniform(0.7, 1.3))))


@functools.lru_cache(maxsize=None)
def campo_sin_huecos():
    out = []
    for x, y, r, ph, k in campo_pts(7, 70, 1240):
        dentro = any(math.hypot(x - hx_, y - hy) < hr + 14 for hx_, hy, hr in HUECOS)
        out.append((x, y, r, ph, k, dentro))
    return tuple(out)


def d_cierre(ctx, t):
    forma = prog(t, T_FIN + 0.15, 1.35, "inout")
    z = 1 + 0.035 * (1 - prog(t, T_FIN, TOTAL - T_FIN, "inout")) * prog(t, b(19), 1.0)
    ctx.save()
    zoom(ctx, z, 540, 1000)
    fondo(ctx, t, 0.35)
    vuelve = prog(t, T_FIN, 0.6)
    for x, y, r, ph, k, dentro in campo_sin_huecos():      # entre las estrellas hay huecos negros de verdad
        a = (vuelve if dentro else 1.0) * titila(t, ph, k)
        estrella(ctx, x, y, r * (1.25 - 0.25 * vuelve) if not dentro else r, a, halo=0.7)
    ah = pop(t, T_ENTRE - 0.1, 0.3) * sale(t, T_FIN - 0.05, 0.3)
    for i, (x, y, r) in enumerate(HUECOS):
        s = pop(t, T_ENTRE - 0.1 + 0.14 * i, 0.3)
        if s > 0.01 and ah > 0.01:
            ctx.save()
            ctx.arc(x, y, r * s, 0, TAU)
            ctx.set_source_rgba(0, 0, 0, 0.55 * min(1, ah))
            ctx.fill_preserve()
            ctx.set_source_rgba(*BLANCO, 0.9 * min(1, ah))
            ctx.set_line_width(7)
            ctx.set_dash([22, 16], t * 24)
            ctx.stroke()
            ctx.restore()
    # la luz que todavía viene: puntitos que crecen de a poco
    if t >= T_LUZ20 - 0.2:
        av = prog(t, T_LUZ20 - 0.2, 0.5) * sale(t, T_FIN + 0.1, 0.5)
        for i, (x, y, u, m) in enumerate(VIENEN):
            dt = t - (T_LUZ20 - 0.2) - 0.25 * u
            if dt <= 0:
                continue
            r = (2.5 + 5.5 * clamp(dt / 4.5)) * m
            pulso = 0.6 + 0.4 * math.sin(t * 4 + i)
            _elipse_suave(ctx, x, y, r * 5, r * 5, LUZ, 0.5 * av * pulso)
            for kk in range(3):                   # anillos que se achican: viene hacia vos
                q = ((dt * 0.7 + kk / 3) % 1.0)
                ctx.arc(x, y, r + 34 * (1 - q), 0, TAU)
                ctx.set_source_rgba(*LUZ, 0.55 * av * q)
                ctx.set_line_width(3)
                ctx.stroke()
            ctx.arc(x, y, r, 0, TAU)
            ctx.set_source_rgba(*hx("#FFF6C8"), av)
            ctx.fill()
    pregunta(ctx, t, forma, prog(t, T_FIN + 0.1, 0.5), 1.0)
    loma(ctx)
    sube = 1 - prog(t, T_FIN + 0.1, 0.75, "out")
    if sube < 1:
        ctx.save()
        if sube > 0.005:
            ctx.rectangle(0, 0, W, 1323)
            ctx.clip()
        vos(ctx, VOS_XY[0], VOS_XY[1] + 620 * sube, VOS_K, ojos=parpadeo(t) if t < TOTAL - 0.4 else "wide")
        ctx.restore()
    ctx.restore()
    if t < T_FIN + 0.3:
        s = pop(t, T_NEGRO - 0.15) * sale(t, T_NEGRO2 + 0.2)
        cartel(ctx, "NEGRO", 800, 330, 96, box=hx("#05070F"), fg=BLANCO, s=s, rot=4)
        s = pop(t, T_VIENE - 0.3) * sale(t, T_FIN - 0.05)
        cartel(ctx, "LUZ EN CAMINO", 540, 1160, 74, s=s, rot=-2)


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_inicio),
    (b(2) - 0.08, d_muchas),
    (b(3) - 0.08, d_infinito),
    (b(4) - 0.08, d_lleno),
    (b(8) - 0.08, d_existe),
    (b(9) - 0.08, d_astronomo),
    (b(10) - 0.08, d_poe),
    (b(12) - 0.08, d_luz),
    (b(14) - 0.08, d_eterno),
    (b(16) - 0.08, d_ciencia),
    (b(17) - 0.08, d_edad),
    (b(18) - 0.08, d_horizonte),
    (b(19) - 0.08, d_cierre),
]
CONTINUAS = {d_existe}
XF = 0.18


def punch(t, t0, d=0.3, amp=0.06):
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


def escena(t):
    return max(k for k, (t0, _) in enumerate(ESCENAS) if t >= t0)


def componer(ctx, t):
    i = escena(t)
    t0, fn = ESCENAS[i]
    dt = t - t0
    if i > 0 and dt < XF and fn not in CONTINUAS:
        capa(ctx, ESCENAS[i - 1][1], t)
        z = punch(t, t0)
        ctx.save()
        ctx.push_group()
        zoom(ctx, z)
        fn(ctx, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(clamp(dt / XF))
        ctx.restore()
        return
    if fn not in CONTINUAS and i > 0:
        zoom(ctx, punch(t, t0))
    fn(ctx, t)


CAPS = motor.Captions(WORDS, {"size": 76, "y": 1470, "max_palabras": 3, "max_letras": 18})


def cuadro(t):
    s, ctx = lienzo()
    try:
        componer(ctx, min(t, TOTAL))
    except Exception as e:
        raise RuntimeError(f"falló el cuadro en t={t:.3f}: {e}") from e
    im = Image.fromarray(a_rgb(s))
    CAPS.draw(im, t)
    return im


# ------------------------------------------------------------------ sonido
def sonido(kind, **kw):
    return K.snd(kind, **kw)


def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    ev(0.05, "chispa", 0.35, d=0.7)
    ev(T_EXPL - 0.05, "pop", 0.6)
    ev(T_ES - 0.1, "whoosh_suave", 0.5)
    ev(T_OBVIO - 0.15, "pop", 0.7)
    ev(T_SOL1 + 0.15, "frenada", 0.35, d=0.5)
    ev(T_FUE - 0.1, "pop", 0.5)
    ev(b(2) - 0.08, "whoosh", 0.7)
    for k in range(10):
        ev(b(2) + 0.15 + k * 0.09, "tick", 0.14, f=1800 + 60 * k, d=0.03)
    ev(T_ESTR - 0.1, "pop", 0.7)
    ev(T_MUCH - 0.1, "chispa", 0.4, d=0.8)
    ev(b(3) - 0.08, "whoosh", 0.6)
    ev(T_INF - 0.15, "pop", 0.8)
    ev(T_ETE - 0.15, "pop", 0.8)
    ev(b(4) - 0.08, "whoosh_suave", 0.6)
    for ci in range(len(CAPAS)):
        ev(b(4) + 0.25 + ci * (b(4, fin=True) - b(4)) / len(CAPAS), "pop", 0.3)
    for tr, _, _ in RAYOS:
        ev(tr, "whoosh_suave", 0.35)
        ev(tr + 0.32, "tick", 0.5, f=1500, d=0.08)
    ev(b(6) + 0.1, "subida", 0.55, d=T_SUPERF + 0.4 - b(6))
    ev(T_NOEX, "golpe", 0.7)
    ev(T_NOCHE7 - 0.15, "whoosh", 0.5)
    ev(b(8) - 0.08, "frenada", 0.5, d=0.5)
    ev(T_EXISTE - 0.2, "pop", 0.6)
    ev(T_ASI + 0.12, "pop", 0.5)
    ev(T_ASI + 0.32, "pop", 0.5)
    ev(T_MAL - 0.15, "golpe", 0.9)
    ev(b(9) - 0.08, "whoosh", 0.6)
    ev(T_PISTA - 0.2, "pop", 0.6)
    ev(T_NO9 - 0.1, "tick", 0.6, f=180, d=0.22)
    ev(T_ASTRO - 0.15, "pop", 0.5)
    ev(b(10) - 0.08, "whoosh", 0.6)
    for k in range(int((T_POE - T_ESCR) / 0.13)):
        ev(T_ESCR + k * 0.13, "tick", 0.12, f=2600 + 200 * (k % 3), d=0.04)
    ev(T_TERROR - 0.5, "whoosh_suave", 0.4)
    ev(T_POE - 0.15, "pop", 0.8)
    ev(T_IDEA - 0.1, "ding", 0.6)
    ev(T_SIMPLE - 0.15, "pop", 0.5)
    ev(b(12) - 0.08, "whoosh", 0.6)
    ev(T_SALE, "chispa", 0.4, d=0.5)
    for k in range(int((T_ARRIBA - T_TARDA) / 0.16)):
        ev(T_TARDA + k * 0.16, "tick", 0.2, f=1300, d=0.03)
    ev(T_TARDA - 0.1, "pop", 0.7)
    ev(T_ARRIBA, "ding", 0.5)
    ev(b(13) - 0.1, "whoosh_suave", 0.6)
    for i in range(3):
        ev(T_TODAV - 0.2 + 0.12 * i, "pop", 0.4)
    ev(T_TODAV + 0.25, "pop", 0.6)
    ev(b(14) - 0.08, "whoosh", 0.6)
    ev(T_NOPUEDE - 0.05, "whoosh", 0.5)
    ev(T_NOPUEDE + 0.1, "tick", 0.6, f=180, d=0.22)
    ev(T_ETERNO2 + 0.45, "frenada", 0.4, d=0.4)
    ev(T_NACER - 0.6, "subida", 0.5, d=0.55)
    ev(T_NACER - 0.05, "golpe", 1.0)
    ev(T_NACER, "chispa", 0.5, d=1.0)
    ev(b(16) - 0.08, "whoosh_suave", 0.6)
    for k in range(9):
        ev(b(16) + 0.2 + k * (T_SIGLO + 0.4 - b(16)) / 9, "tick", 0.25, f=1700, d=0.03)
    ev(T_CIENCIA - 0.2, "pop", 0.5)
    ev(T_RAZON - 0.1, "ding", 0.7)
    ev(b(17) - 0.08, "whoosh", 0.6)
    ev(T_NACIO - 0.1, "golpe", 0.8)
    for k in range(int((T_MILL + 0.1 - T_CASI) / 0.07)):
        ev(T_CASI - 0.1 + k * 0.07, "tick", 0.16, f=1900 + 20 * k, d=0.025)
    ev(T_MILL + 0.05, "ding", 0.5)
    ev(b(18) - 0.08, "whoosh_suave", 0.6)
    ev(b(18) + 0.2, "escaneo", 0.22, d=T_CAMINO - b(18))
    ev(T_LUZ18 - 0.1, "pop", 0.6)
    ev(T_PARTE - 0.1, "pop", 0.5)
    ev(b(19) - 0.08, "whoosh", 0.6)
    for i in range(3):
        ev(T_ENTRE - 0.1 + 0.14 * i, "pop", 0.4)
    ev(T_NEGRO - 0.15, "golpe", 0.6)
    ev(T_LUZ20 - 0.2, "chispa", 0.35, d=1.2)
    ev(T_VIENE - 0.3, "pop", 0.6)
    ev(T_FIN, "whoosh_suave", 0.5)
    ev(T_FIN + 0.2, "subida", 0.3, d=1.2)
    return E


def pista_efectos():
    n = int((TOTAL + 3) * SR)
    mix = np.zeros(n, np.float32)
    for t, k, v, kw in eventos():
        x = sonido(k, **kw) * v
        i0 = int(t * SR)
        i1 = min(n, i0 + len(x))
        if 0 <= i0 < n:
            mix[i0:i1] += x[:i1 - i0]
    mix = mix[:int(TOTAL * SR)]
    fade = int(0.08 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix *= 0.5 / (np.abs(mix).max() or 1)
    return mix


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


def render(salida, hilos=2):
    fb = int(math.ceil(TOTAL * FPS))
    tmp = tempfile.mkdtemp(prefix="render_", dir=AQUI)
    k = hilos * 3
    bounds = [round(fb * i / k) for i in range(k + 1)]
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
    P.escribir_wav(sfx, pista_efectos())
    voz = os.path.join(AQUI, "audio", "voz.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", voz, "-i", sfx,
                    "-filter_complex", "[1:a][2:a]amix=inputs=2:normalize=0:duration=first,"
                    "alimiter=limit=0.89:level=false[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL:.3f}",
                    salida], check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fotos")
    ap.add_argument("--dir", default=os.path.join(AQUI, "fotos"))
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "por_que_el_cielo_es_negro.mp4"))
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
    render(a.salida, a.hilos)
    print("listo:", a.salida, f"{TOTAL:.1f}s")


if __name__ == "__main__":
    main()

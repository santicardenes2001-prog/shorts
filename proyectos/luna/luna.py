"""Short "¿Por qué la Luna siempre muestra la misma cara?" — animación procedural (armazón de sueno.py).

Usa las piezas espaciales de cielo.py (estrellas, Tierra con cara, Vos y la loma).
- Gancho (G2): el primer cuadro ya muestra la paradoja: la Luna con cara, una flecha que la hace girar
  y la cara que no se mueve. El cuadro de TOTAL es igual al de 0 (loop, F4).
- Pregunta a los 5,4 s (C3) y primer dato fuerte a los 13,2 s (C5): sin números ni mecánica antes.
- Cada tramo sube la intensidad (C7): la órbita -> la Luna que giraba loca y la Tierra que la frena ->
  el candado -> la foto de 1959 -> la Luna frena a la Tierra -> los dinosaurios -> las dos trabadas.
Vos sale solo en la apertura y en el cierre del loop (V2); el resto lo cuentan la Luna y la Tierra con cara.

    python proyectos/luna/luna.py --fotos 0,5.5,14
    python proyectos/luna/luna.py --probar
    python proyectos/luna/luna.py        # render completo -> salidas/la_luna_siempre_te_mira.mp4
"""
import argparse
import functools
import json
import math
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import cairo
import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
for _p in (ROOT, os.path.join(ROOT, "proyectos", "pantalla"), os.path.join(ROOT, "proyectos", "picante"),
           os.path.join(ROOT, "proyectos", "cielo")):
    sys.path.insert(0, _p)
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
import cielo as C  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, UI, a_rgb, bump, cartel, clamp, ease, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rng, rrect, texto)
from picante import _elipse_suave, fondo_azul  # noqa: E402
from cielo import LUZ, ROJO, VERDE, cruz, estrella, punteada, tachado, tierra, tilde, zoom  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "La Luna gira, pero siempre te muestra la misma cara.",                    # b0
    "Ningún humano vio el otro lado desde la Tierra.",                         # b1
    "Si gira, ¿por qué nunca se da vuelta?",                                   # b2
    "Porque gira justo al ritmo en que nos rodea.",                            # b3
    "Una vuelta sobre sí misma por cada vuelta a la Tierra.",                  # b4
    "Parece una coincidencia imposible, y no lo es.",                          # b5
    "Hace mucho, la Luna giraba bastante más rápido,",                         # b6
    "pero la gravedad de la Tierra la fue frenando.",                          # b7
    "La frenó hasta dejarla trabada, mirándonos para siempre.",                # b8
    "El otro lado recién se conoció por una foto.",                            # b9
    "La tomó una nave en 1959.",                                               # b10
    "Lo más extraño es que ella nos hace lo mismo.",                           # b11
    "Su gravedad frena a la Tierra, muy despacio.",                            # b12
    "Cada siglo, tus días duran un poquito más.",                              # b13
    "Cuando vivían los dinosaurios, el día duraba media hora menos.",          # b14
    "Con tiempo de sobra, la Tierra también quedaría trabada.",                # b15
    "Por ahora, la única atrapada es ella:",                                   # b16
]
WORDS = motor.align_times([{"texto": t} for t in NARRACION],
                          json.load(open(os.path.join(AQUI, "audio", "palabras.json"))))
COLA = 0.3
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
LUNA = hx("#E3E6EE")
LUNA2 = hx("#B9BFCE")
MAR = hx("#9AA2B6")
CRATER = hx("#A7AEBF")
CANDADO = hx("#FFC933")
GRIS_OSC = hx("#2B2F3A")
DINO = hx("#5DBB63")
DINO2 = hx("#3E9447")
PAPEL = hx("#FBF7EE")
CIELO_F = hx("#0B1233")
KF = 60 * round(14 * TOTAL / 60) / (14 * TOTAL)      # el fondo de puntos cierra justo en el loop
WHOOSH = []


# ------------------------------------------------------------------ ayudas
def fondo(ctx, t, oscuro=0.25):
    fondo_azul(ctx, t * KF)
    if oscuro > 0:
        ctx.set_source_rgba(0.027, 0.043, 0.11, oscuro)
        ctx.paint()


def per(t, k, ph=0.0):
    """Vaivén que cierra justo en el loop."""
    return math.sin(TAU * k * t / TOTAL + ph)


def sale(t, t1, d=0.2):
    return 1 - prog(t, t1, d, "in")


def titila(t, ph, k):
    return 0.72 + 0.28 * math.sin(TAU * k * t / TOTAL + ph)


@functools.lru_cache(maxsize=None)
def campo_pts(seed, n, y1=1300):
    r = rng(seed)
    return tuple((float(r.uniform(30, 1050)), float(r.uniform(40, y1)), float(r.uniform(2.0, 7.0)),
                  float(r.uniform(0, TAU)), int(r.integers(14, 40))) for _ in range(n))


def campo(ctx, t, seed=7, n=60, a=1.0, y1=1300):
    for x, y, r, ph, k in campo_pts(seed, n, y1):
        estrella(ctx, x, y, r, a * titila(t, ph, k), halo=0.7)


def kartel(ctx, txt, x, y, size, t, t0, t1=None, **kw):
    if t < t0:
        return
    s = pop(t, t0) * (sale(t, t1) if t1 is not None else 1.0)
    if s > 0.01:
        cartel(ctx, txt, x, y, size, s=s, **kw)


def etiqueta(ctx, txt, x, y, size, a=1.0, col=hx("#C9D3EA"), ax=0.5):
    if a > 0.01:
        texto(ctx, txt, x, y, size, fill=col, stroke=None, fam=UI, bold=True, ax=ax, alpha=a)


def parpadeo(t):
    return "closed" if (t % 3.1) > 2.98 else "wide"


def flash(ctx, t, t0, d=0.35):
    if t0 <= t < t0 + d:
        ctx.set_source_rgba(1, 1, 1, 0.85 * (1 - (t - t0) / d))
        ctx.paint()


# ------------------------------------------------------------------ la Luna
_rc = rng(5)
CRATERES_CERCA = [(float(_rc.uniform(-0.8, 0.8)), float(_rc.uniform(-0.8, 0.8)), float(_rc.uniform(0.04, 0.09)))
                  for _ in range(14)]
_rc = rng(9)
CRATERES_LEJOS = [(float(_rc.uniform(-0.85, 0.85)), float(_rc.uniform(-0.85, 0.85)), float(_rc.uniform(0.04, 0.14)))
                  for _ in range(34)]
# mares del lado cercano (oscuros y grandes) y del lejano (casi no tiene)
MARES_CERCA = [(-0.42, -0.42, 0.34, 0.26), (0.28, -0.5, 0.26, 0.2), (0.45, -0.12, 0.22, 0.3),
               (-0.6, 0.1, 0.26, 0.42), (-0.05, 0.62, 0.3, 0.16)]
MARES_LEJOS = [(0.3, -0.35, 0.12, 0.1)]


def luna(ctx, x, y, R, ojos="open", boca="smile", ceja=None, look=(0, 0), a=1.0, rot=0.0, lado="cerca",
         sx=1.0, sy=1.0, rubor=False, halo=1.0):
    """La Luna con cara. lado='lejos' es el otro lado: sin cara, sin mares y llena de cráteres."""
    if a <= 0.01 or R <= 1:
        return
    ctx.save()
    ctx.push_group()
    if halo > 0:
        _elipse_suave(ctx, x, y, R * 1.9 * sx, R * 1.9 * sy, LUNA, 0.16 * halo)
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(sx, sy)
    ctx.arc(0, 0, R, 0, TAU)
    g = cairo.RadialGradient(-R * 0.35, -R * 0.4, R * 0.1, 0, 0, R)
    g.add_color_stop_rgb(0, *LUNA)
    g.add_color_stop_rgb(1, *LUNA2)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    for mx, my, rx, ry in (MARES_CERCA if lado == "cerca" else MARES_LEJOS):
        ctx.save()
        ctx.translate(mx * R, my * R)
        ctx.scale(rx * R, ry * R)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.set_source_rgba(*MAR, 0.55)
        ctx.fill()
    for cx, cy, cr in (CRATERES_CERCA if lado == "cerca" else CRATERES_LEJOS):
        ctx.arc(cx * R, cy * R, cr * R, 0, TAU)
        ctx.set_source_rgba(*CRATER, 0.9)
        ctx.fill_preserve()
        ctx.set_source_rgba(*INK, 0.35)
        ctx.set_line_width(max(1.2, R * 0.012))
        ctx.stroke()
    ctx.restore()
    ctx.arc(0, 0, R, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(3, R * 0.06))
    ctx.stroke()
    if lado == "cerca" and R > 24:
        C.cara(ctx, 0, 0, R, ojos, boca, ceja, look, rubor=rubor)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def casquete(ctx, x, y, R, a):
    """Oscurece la parte de arriba de la Luna (la que da al espacio), sin tapar la cara."""
    if a <= 0.01:
        return
    h = 0.38 * R
    ang = math.asin(h / R)
    ctx.new_path()
    ctx.arc(x, y, R + 4, math.pi + ang, TAU - ang)
    ctx.close_path()
    ctx.set_source_rgba(*CIELO_F, a)
    ctx.fill()


def flecha_giro(ctx, x, y, r, ang, largo=1.5, col=AMARILLO, w=16, a=1.0, sentido=-1):
    """Arco con punta alrededor de (x, y). sentido=-1 gira como la Luna vista desde arriba (antihorario)."""
    if a <= 0.01 or largo <= 0.02:
        return
    a0 = ang
    a1 = ang + sentido * largo
    for lw, c in ((w + 10, INK), (w, col)):
        ctx.new_path()
        if sentido < 0:
            ctx.arc_negative(x, y, r, a0, a1)
        else:
            ctx.arc(x, y, r, a0, a1)
        ctx.set_source_rgba(*c, a)
        ctx.set_line_width(lw)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    # punta
    px, py = x + r * math.cos(a1), y + r * math.sin(a1)
    tang = a1 + sentido * math.pi / 2
    s = w * 1.7
    ctx.move_to(px + s * math.cos(tang), py + s * math.sin(tang))
    ctx.line_to(px + s * 0.9 * math.cos(tang + 2.3), py + s * 0.9 * math.sin(tang + 2.3))
    ctx.line_to(px + s * 0.9 * math.cos(tang - 2.3), py + s * 0.9 * math.sin(tang - 2.3))
    ctx.close_path()
    ctx.set_source_rgba(*col, a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(5)
    ctx.stroke()


def candado(ctx, x, y, s, a=1.0, abierto=0.0):
    if a <= 0.01 or s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    sube = 34 * abierto
    ctx.new_path()
    ctx.arc(0, -40 - sube, 44, math.pi, 0)
    ctx.line_to(44, -10 - sube)
    for lw, c in ((34, INK), (20, hx("#C9CFD8"))):
        ctx.new_path()
        ctx.move_to(-44, -10 - sube * (1 - abierto))
        ctx.arc(0, -40 - sube, 44, math.pi, 0)
        ctx.line_to(44, -10 - sube)
        ctx.set_line_width(lw)
        ctx.set_source_rgba(*c, a)
        ctx.stroke()
    rrect(ctx, -70, -30, 140, 112, 22)
    ctx.set_source_rgba(*CANDADO, a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(9)
    ctx.stroke()
    ctx.arc(0, 18, 14, 0, TAU)
    ctx.fill()
    ctx.move_to(-7, 22)
    ctx.line_to(7, 22)
    ctx.line_to(4, 52)
    ctx.line_to(-4, 52)
    ctx.close_path()
    ctx.fill()
    ctx.restore()


def gravedad(ctx, x0, y0, x1, y1, t, a=1.0, n=3, sep=46):
    """Líneas punteadas que tiran de un cuerpo hacia el otro (la fase avanza hacia (x0, y0))."""
    if a <= 0.01:
        return
    ang = math.atan2(y1 - y0, x1 - x0)
    nx, ny = -math.sin(ang), math.cos(ang)
    for k in range(n):
        o = (k - (n - 1) / 2) * sep
        punteada(ctx, x0 + nx * o, y0 + ny * o, x1 + nx * o * 0.6, y1 + ny * o * 0.6, LUZ, 7, 0.75 * a,
                 (18, 18), fase=t * 90)


def reloj(ctx, x, y, R, hora=0.0, a=1.0, cuna=0.0, h24=True, cara=False):
    """Esfera de un día. hora en horas. cuna = horas recortadas en rojo al final del día."""
    if a <= 0.01:
        return
    ctx.save()
    ctx.push_group()
    ctx.arc(x, y + 10, R, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.arc(x, y, R, 0, TAU)
    ctx.set_source_rgb(*PAPEL)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(R * 0.06)
    ctx.stroke()
    div = 24 if h24 else 12
    if cuna > 0:
        a1 = -math.pi / 2
        a0 = a1 - TAU * cuna / div
        ctx.move_to(x, y)
        ctx.arc(x, y, R * 0.94, a0, a1)
        ctx.close_path()
        ctx.set_source_rgb(*ROJO)
        ctx.fill()
    for k in range(div):
        ang = TAU * k / div - math.pi / 2
        l0 = R * (0.78 if k % 6 == 0 else 0.84)
        ctx.move_to(x + l0 * math.cos(ang), y + l0 * math.sin(ang))
        ctx.line_to(x + R * 0.92 * math.cos(ang), y + R * 0.92 * math.sin(ang))
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(R * (0.04 if k % 6 == 0 else 0.022))
        ctx.stroke()
    ang = TAU * hora / div - math.pi / 2
    ctx.move_to(x, y)
    ctx.line_to(x + R * 0.7 * math.cos(ang), y + R * 0.7 * math.sin(ang))
    ctx.set_source_rgb(*ROJO)
    ctx.set_line_width(R * 0.06)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.arc(x, y, R * 0.07, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def nave(ctx, x, y, s, rot=0.0, a=1.0):
    """Sonda tipo Luna 3: cilindro con tapas redondeadas y cuatro antenas."""
    if a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s, s)
    for sx in (-1, 1):
        for sy in (-1, 1):
            ctx.move_to(sx * 20, sy * 30)
            ctx.line_to(sx * 58, sy * 62)
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(6)
    ctx.stroke()
    rrect(ctx, -32, -48, 64, 96, 26)
    ctx.set_source_rgba(*hx("#C9CFD8"), a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(6)
    ctx.stroke()
    for yy in (-14, 14):
        rrect(ctx, -26, yy - 8, 52, 16, 4)
        ctx.set_source_rgba(*hx("#3D6BFF"), a)
        ctx.fill()
    ctx.arc(0, -48, 9, 0, TAU)
    ctx.set_source_rgba(*INK, a)
    ctx.fill()
    ctx.restore()


def dino(ctx, x, y, s, t, a=1.0):
    """Saurópodo con cara, de perfil mirando a la derecha; (x, y) = los pies."""
    if a <= 0.01 or s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.push_group()
    cab = 4 * math.sin(TAU * 0.6 * t)
    # cola
    ctx.move_to(-150, -150)
    ctx.curve_to(-260, -150, -330, -110, -380, -60)
    ctx.curve_to(-320, -95, -250, -110, -150, -100)
    ctx.close_path()
    # cuello
    ctx.move_to(120, -190)
    ctx.curve_to(170, -260, 190, -360, 210, -420 + cab)
    ctx.line_to(260, -415 + cab)
    ctx.curve_to(245, -340, 225, -240, 170, -130)
    ctx.close_path()
    ctx.set_source_rgb(*DINO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    # patas de atrás
    for px in (-110, 90):
        rrect(ctx, px - 30, -110, 62, 112, 18)
        ctx.set_source_rgb(*DINO2)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.stroke()
    # cuerpo
    ctx.save()
    ctx.translate(-10, -160)
    ctx.scale(190, 95)
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()
    ctx.set_source_rgb(*DINO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    # patas de adelante
    for px in (-70, 130):
        rrect(ctx, px - 30, -100, 62, 102, 18)
        ctx.set_source_rgb(*DINO)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.stroke()
    # cabeza
    ctx.save()
    ctx.translate(250, -428 + cab)
    ctx.scale(62, 40)
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()
    ctx.set_source_rgb(*DINO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    K.carita(ctx, 262, -436 + cab, 34, 0.42, ojos="open", boca="smile", look=(0.5, 0))
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


# ------------------------------------------------------------------ 0. apertura (y cierre del loop)
LUNA_A = (650, 560, 235)
VOS_A = (250, 1350, 0.5)


def base_apertura(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 7, 60, 1.0, y1=1220)
    x, y, R = LUNA_A
    ang = TAU * 6 * t / TOTAL                          # la flecha da 6 vueltas en todo el video: cierra el loop
    flecha_giro(ctx, x, y, R + 58, ang, 1.7, a=0.95)
    luna(ctx, x, y, R, ojos="open", boca="smile", look=(-0.45, 0.35), rubor=True)
    C.loma(ctx)
    C.vos(ctx, VOS_A[0], VOS_A[1], VOS_A[2], ojos=parpadeo(t))


T_GIRA = b(0, "gira")
T_CARA = b(0, "cara")


def d_apertura(ctx, t):
    base_apertura(ctx, t)
    kartel(ctx, "GIRA", 870, 230, 74, t, T_GIRA, b(1) - 0.2, rot=6)
    kartel(ctx, "LA MISMA CARA", 650, 905, 70, t, T_CARA - 0.1, b(1) - 0.2, box=BLANCO, rot=-3)


def d_vuelta(ctx, t):
    base_apertura(ctx, t)


# ------------------------------------------------------------------ 1. nadie vio el otro lado
T_OTRO = b(1, "otro")
T_DESDE = b(1, "desde")


def d_otro_lado(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 11, 50, 0.9, y1=1300)
    ex, ey, ER = 540, 1290, 190
    mx, my, MR = 540, 560, 210
    tierra(ctx, ex, ey, ER, t, ojos="wide", boca="o", look=(0, -1))
    luna(ctx, mx, my, MR, ojos="open", boca="smile", look=(0, 0.8))
    # el otro lado, a oscuras, con un signo de pregunta
    q = prog(t, T_OTRO - 0.1, 0.35)
    if q > 0.01:
        casquete(ctx, mx, my, MR, 0.86 * q)
        texto(ctx, "?", mx, my - 135, 120 * pop(t, T_OTRO), fill=AMARILLO, stroke=INK, sw=12)
    kartel(ctx, "EL OTRO LADO", 540, 230, 70, t, T_OTRO, rot=-3)
    # la mirada desde la Tierra
    for k in (-1, 1):
        punteada(ctx, ex + k * 40, ey - ER, mx + k * 120, my + 150, LUZ, 6, 0.6 * prog(t, T_DESDE - 0.2, 0.4))


# ------------------------------------------------------------------ 2. ¿por qué nunca se da vuelta?
T_PQ = b(2, "por")
T_VUELTA2 = b(2, "vuelta")


def d_porque(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 13, 50, 0.9)
    # intenta darse vuelta y vuelve: se aplasta de costado
    q = (t - b(2)) / max(b(3) - b(2), 0.1)
    sx = 1 - 0.32 * abs(math.sin(math.pi * 2 * clamp(q)))
    look = (-0.9 if math.sin(math.pi * 2 * q) > 0 else 0.9, 0)
    luna(ctx, 540, 700, 250, ojos="wide", boca="o", look=look, sx=sx, ceja="worried")
    flecha_giro(ctx, 540, 700, 330, -1.1 + 2.5 * prog(t, b(2), 0.8), 1.4, a=prog(t, b(2), 0.3))
    s = pop(t, T_PQ - 0.05) * bump(t, T_VUELTA2, 0.35, 0.12)
    cartel(ctx, "¿POR QUÉ NUNCA\nSE DA VUELTA?", 540, 1180, 72, s=s, rot=-2)


# ------------------------------------------------------------------ 3-4. la órbita vista desde arriba
OC = (540, 700)
ORB = 350
T_O0 = b(3) - 0.05
T_O1 = b(4, "Tierra", fin=True)
T_GIRO1 = b(4, "misma")
T_VUELTA1 = b(4, "Tierra")


def fi(t):
    return -math.pi / 2 - TAU * prog(t, T_O0 + 0.25, T_O1 - T_O0 - 0.25, "inout")


def d_orbita(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 17, 50, 0.8)
    ctx.arc(*OC, ORB, 0, TAU)
    ctx.set_source_rgba(1, 1, 1, 0.35)
    ctx.set_line_width(5)
    ctx.set_dash([16, 18])
    ctx.stroke()
    ctx.set_dash([])
    # recorrido hecho
    f = fi(t)
    if f < -math.pi / 2 - 0.01:
        ctx.new_path()
        ctx.arc_negative(*OC, ORB, -math.pi / 2, f)
        ctx.set_source_rgb(*AMARILLO)
        ctx.set_line_width(12)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    tierra(ctx, *OC, 120, t, ojos="open", boca="smile", look=(0.6 * math.cos(f), 0.6 * math.sin(f)))
    mx, my = OC[0] + ORB * math.cos(f), OC[1] + ORB * math.sin(f)
    punteada(ctx, mx, my, OC[0], OC[1], LUZ, 5, 0.5)
    luna(ctx, mx, my, 92, ojos="open", boca="smile", look=(0, 0.8), rot=f + math.pi / 2, halo=0.6)
    flecha_giro(ctx, mx, my, 126, f + math.pi / 2 - math.pi / 2 - 0.4, 1.2, w=11,
                a=prog(t, T_O0 + 0.2, 0.3) * (1 - prog(t, T_O1, 0.3)))
    kartel(ctx, "1 GIRO", 330, 1225, 66, t, T_GIRO1, rot=-4)
    kartel(ctx, "1 VUELTA", 760, 1225, 66, t, T_VUELTA1, rot=4, box=BLANCO)
    if t >= T_VUELTA1 + 0.15:
        texto(ctx, "=", 545, 1225, 90 * pop(t, T_VUELTA1 + 0.15), fill=AMARILLO, stroke=INK, sw=10)


# ------------------------------------------------------------------ 5. ¿casualidad? no
T_COINC = b(5, "coincidencia")
T_NO = b(5, "no")


def d_casualidad(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 19, 50, 0.8)
    no = t >= T_NO
    luna(ctx, 540, 760, 230, ojos="open" if not no else "happy", boca="flat" if not no else "grin",
         ceja="worried" if not no else None, look=(0.6, -0.4))
    if t >= T_COINC - 0.1:
        s = pop(t, T_COINC - 0.1)
        cartel(ctx, "¿CASUALIDAD?", 540, 330, 86, s=s, rot=-4)
        tachado(ctx, 540, 330, 600, prog(t, T_NO, 0.3), ang=-4)
    kartel(ctx, "NO", 820, 470, 90, t, T_NO + 0.2, box=ROJO, fg=BLANCO, rot=8)


# ------------------------------------------------------------------ 6-8. giraba rápido, la Tierra la frena, trabada
T_F0 = b(6) - 0.06
T_RAP = b(6, "rapido")
T_GRAV = b(7, "gravedad")
T_FREN = b(7, "frenando")
T_TRAB = b(8, "trabada")
T_MIR = b(8, "mirandonos")
FR_D = T_TRAB - T_GRAV                       # frenado: de "gravedad" a "trabada"
W0 = TAU * round(2.4 * (T_GRAV - T_F0 + FR_D / 2)) / (T_GRAV - T_F0 + FR_D / 2)   # termina derecha


def giro_luna(t):
    if t < T_GRAV:
        return W0 * (t - T_F0)
    q = clamp((t - T_GRAV) / FR_D)
    return W0 * (T_GRAV - T_F0) + W0 * FR_D * (q - q * q / 2)


def d_frena(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 23, 50, 0.8, y1=1100)
    sube = prog(t, T_GRAV - 0.3, 0.6)
    ex, ey = 540, lerp(1600, 1190, sube)
    tierra(ctx, ex, ey, 190, t, ojos="open" if t < T_TRAB else "happy", boca="grin" if t < T_TRAB else "smile",
           look=(0, -1), a=sube)
    mx, my, R = 540, 560, 190
    q = clamp((t - T_GRAV) / FR_D)
    w = W0 * (1 - q) if t >= T_GRAV else W0
    # estelas de velocidad
    va = clamp(w / W0)
    for k in range(3):
        flecha_giro(ctx, mx, my, R + 40 + 34 * k, -giro_luna(t) * 0.6 + k * 2.1, 0.5 + 0.9 * va, w=10,
                    col=LUZ, a=0.75 * va)
    gravedad(ctx, ex, ey - 190, mx, my + R, t, a=sube * (1 - prog(t, T_TRAB + 0.6, 0.5)))
    estira = 1 + 0.07 * sube
    lento = t >= T_TRAB - 0.25
    luna(ctx, mx, my, R, ojos="wide" if not lento else "open", boca="o" if t < T_GRAV else ("flat" if not lento
         else "smile"), look=(0, 0.9) if lento else (0, 0), rot=-giro_luna(t), sy=estira, sx=1 / estira ** 0.5)
    kartel(ctx, "HACE MUCHO", 540, 220, 72, t, b(6) + 0.05, T_GRAV - 0.2, box=BLANCO, rot=-4)
    kartel(ctx, "MÁS RÁPIDO", 540, 330, 66, t, T_RAP - 0.1, T_GRAV - 0.2, rot=3)
    kartel(ctx, "LA FRENA", 540, 220, 72, t, T_FREN - 0.1, T_TRAB - 0.15, rot=-3)
    if t >= T_TRAB:
        candado(ctx, 790, 880, 0.85 * pop(t, T_TRAB))
        kartel(ctx, "TRABADA", 540, 220, 76, t, T_TRAB, box=ROJO, fg=BLANCO, rot=-3)


# ------------------------------------------------------------------ 9. el otro lado, por una foto
T_FOTO = b(9, "foto")


def d_foto(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 29, 50, 0.8)
    pre = 1 - prog(t, T_FOTO - 0.05, 0.25)
    if pre > 0.01:
        luna(ctx, 540, 700, 220, ojos="open", boca="smile", look=(0, 0.8), a=pre)
        casquete(ctx, 540, 700, 220, 0.86 * pre)
        texto(ctx, "?", 540, 560, 120, fill=AMARILLO, stroke=INK, sw=12, alpha=pre)
    kartel(ctx, "EL OTRO LADO", 540, 230, 70, t, b(9) + 0.05, rot=-3)
    if t >= T_FOTO - 0.05:
        s = pop(t, T_FOTO - 0.05, 0.45)
        rev = prog(t, T_FOTO + 0.1, 0.9)                 # la foto "se revela"
        ctx.save()
        ctx.translate(540, 760)
        ctx.rotate(math.radians(-4))
        ctx.scale(s, s)
        rrect(ctx, -300, -330, 600, 700, 18)
        ctx.set_source_rgb(*INK)
        ctx.fill()
        rrect(ctx, -290, -340, 600, 700, 18)
        ctx.set_source_rgb(*PAPEL)
        ctx.fill()
        rrect(ctx, -250, -300, 520, 520, 8)
        ctx.set_source_rgb(*CIELO_F)
        ctx.fill()
        luna(ctx, 10, -40, 210, lado="lejos", a=rev, halo=0.4)
        ctx.restore()
        etiqueta(ctx, "LADO LEJANO", 548, 1035, 44, a=rev, col=INK)
    flash(ctx, t, T_FOTO)


# ------------------------------------------------------------------ 10. una nave en 1959
T_NAVE = b(10, "nave")
T_1959 = b(10, "1959")
NV0, NV1 = b(10) - 0.06, b(10, fin=True) + 0.35


def pos_nave(t):
    q = prog(t, NV0, NV1 - NV0, "inout")
    ang = lerp(math.radians(150), math.radians(-215), q)       # sale de abajo a la izquierda y pasa por detrás
    rx, ry = 300, 380
    return 600 + rx * math.cos(ang), 620 + ry * math.sin(ang), ang


def d_nave(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 31, 50, 0.8)
    tierra(ctx, 190, 1270, 120, t, ojos="open", boca="smile", look=(0.6, -0.6))
    luna(ctx, 600, 620, 160, ojos="open", boca="smile", look=(-0.6, 0.7))
    # el recorrido
    pts = [pos_nave(NV0 + (NV1 - NV0) * k / 60) for k in range(61)]
    q = clamp((t - NV0) / (NV1 - NV0))
    n = max(1, int(60 * prog(t, NV0, NV1 - NV0, "inout")))
    ctx.move_to(pts[0][0], pts[0][1])
    for p in pts[1:n + 1]:
        ctx.line_to(p[0], p[1])
    ctx.set_source_rgba(*LUZ, 0.55)
    ctx.set_line_width(6)
    ctx.set_dash([14, 14])
    ctx.stroke()
    ctx.set_dash([])
    x, y, ang = pos_nave(t)
    nave(ctx, x, y, 0.85, rot=ang, a=prog(t, NV0, 0.2) if q < 1 else 1.0)
    detras = y < 520
    if detras:
        estrella(ctx, x, y + 60, 26 * (0.6 + 0.4 * math.sin(t * 30)), 1.0, col=BLANCO)
    kartel(ctx, "1959", 540, 230, 110, t, T_1959 - 0.05, rot=-4)
    if t >= T_NAVE:
        etiqueta(ctx, "SONDA LUNA 3", x, y + 90, 38, a=prog(t, T_NAVE, 0.3) * (1 - prog(t, NV1 - 0.3, 0.3)))


# ------------------------------------------------------------------ 11-12. ella nos hace lo mismo
T_EXTR = b(11, "extraño")
T_MISMO = b(11, "mismo")
T_FRENA_T = b(12, "frena")
T_DESP = b(12, "despacio")


def d_ella(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 37, 50, 0.8)
    ex, ey, ER = 500, 880, 250
    mx, my, MR = 850, 300, 105
    sorpresa = t >= T_MISMO
    gira = 1 - 0.55 * prog(t, T_FRENA_T, b(13) - T_FRENA_T)
    ang = TAU * 0.5 * (t - b(11)) * (0.7 + 0.3 * gira)
    flecha_giro(ctx, ex, ey, ER + 60, -ang, 1.3 + 0.6 * gira, w=16)
    tierra(ctx, ex, ey, ER, t, ojos="wide" if sorpresa else "open", boca="o" if sorpresa else "smile",
           look=(0.7, -0.7))
    gravedad(ctx, mx, my + MR, ex + 120, ey - ER + 30, -t, a=prog(t, T_EXTR, 0.4))
    luna(ctx, mx, my, MR, ojos="happy" if sorpresa else "open", boca="grin", look=(-0.7, 0.7), halo=0.6)
    kartel(ctx, "¡LO MISMO!", 380, 300, 76, t, T_MISMO - 0.05, b(12) - 0.1, rot=-5)
    kartel(ctx, "FRENA A LA TIERRA", 540, 1290, 60, t, T_FRENA_T - 0.05, rot=-2)
    kartel(ctx, "MUY DESPACIO", 380, 300, 70, t, T_DESP - 0.05, box=BLANCO, rot=-4)


# ------------------------------------------------------------------ 13. cada siglo, un poquito más
T_SIGLO = b(13, "siglo")
T_DIAS = b(13, "dias")
T_MAS = b(13, "poquito")


def d_siglo(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 41, 40, 0.7)
    q = clamp((t - b(13)) / (b(14) - b(13)))
    reloj(ctx, 540, 760, 300, hora=24 * q * 0.98, a=1.0)
    etiqueta(ctx, "1 DÍA = 24 H", 540, 1110, 52, a=prog(t, T_DIAS, 0.3), col=BLANCO)
    kartel(ctx, "CADA SIGLO", 540, 270, 80, t, T_SIGLO - 0.1, rot=-3)
    kartel(ctx, "+0,002 SEGUNDOS", 540, 1230, 64, t, T_MAS, box=BLANCO, rot=2)


# ------------------------------------------------------------------ 14. los dinosaurios
T_DINO = b(14, "dinosaurios")
T_MEDIA = b(14, "media")
T_MENOS = b(14, "menos")


def d_dino(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 43, 40, 0.7, y1=800)
    dino(ctx, 380, 1310, 0.95 * pop(t, b(14) - 0.05, 0.4), t)
    cuna = 0.5 * prog(t, T_MEDIA, T_MENOS - T_MEDIA + 0.2)
    reloj(ctx, 760, 600, 230, hora=24 - cuna, cuna=cuna)
    kartel(ctx, "−30 MIN", 760, 900, 66, t, T_MEDIA + 0.05, box=ROJO, fg=BLANCO, rot=4)
    kartel(ctx, "DÍA DE 23 H 30 MIN", 540, 200, 64, t, T_MENOS - 0.05, rot=-3)


# ------------------------------------------------------------------ 15. con tiempo de sobra, las dos trabadas
T_SOBRA = b(15, "sobra")
T_TAMB = b(15, "tambien")
T_TRAB2 = b(15, "trabada")


def d_futuro(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 47, 50, 0.8)
    ex, ey, ER = 330, 780, 170
    mx, my, MR = 820, 780, 115
    para = 1 - prog(t, T_TAMB, T_TRAB2 - T_TAMB)
    ang = TAU * 0.6 * (t - b(15)) * (0.3 + 0.7 * para)
    flecha_giro(ctx, ex, ey, ER + 50, -ang, 0.4 + 1.2 * para, w=14, a=0.3 + 0.7 * para)
    tierra(ctx, ex, ey, ER, t, ojos="open", boca="smile" if t < T_TRAB2 else "flat", look=(1, 0))
    luna(ctx, mx, my, MR, ojos="open", boca="smile", look=(-1, 0), halo=0.6)
    gravedad(ctx, mx - MR, my, ex + ER, ey, t, a=0.8, n=2, sep=60)
    candado(ctx, mx, my - MR - 70, 0.6 * pop(t, b(15) + 0.05))
    if t >= T_TRAB2:
        candado(ctx, ex, ey - ER - 70, 0.75 * pop(t, T_TRAB2))
    kartel(ctx, "MUCHÍSIMO TIEMPO", 540, 250, 70, t, T_SOBRA - 0.15, rot=-3)
    kartel(ctx, "LAS DOS", 540, 1210, 72, t, T_TRAB2 + 0.05, box=ROJO, fg=BLANCO, rot=2)


# ------------------------------------------------------------------ 16. por ahora, la única atrapada es ella
T_AHORA = b(16, "ahora")
T_UNICA = b(16, "unica")
T_ELLA = b(16, "ella")
T_VUELTA = T_ELLA - 0.12


def d_atrapada(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 47, 50, 0.8)
    q = prog(t, T_UNICA - 0.1, T_VUELTA - T_UNICA + 0.15, "inout")
    ex, ey, ER = lerp(330, -200, q), lerp(780, 1100, q), 170
    mx, my, MR = lerp(820, LUNA_A[0], q), lerp(780, LUNA_A[1], q), lerp(115, LUNA_A[2], q)
    libre = prog(t, T_AHORA, 0.4)
    ang = TAU * 0.6 * (t - b(16)) * libre
    flecha_giro(ctx, ex, ey, ER + 50, -ang, 1.6 * libre, w=14, a=libre * (1 - q))
    tierra(ctx, ex, ey, ER, t, ojos="happy", boca="grin", look=(1, 0), a=1 - q)
    candado(ctx, ex, ey - ER - 70 - 160 * libre, 0.75, a=1 - libre, abierto=libre)
    luna(ctx, mx, my, MR, ojos="open", boca="flat", ceja="worried", look=(-0.6, 0.3))
    candado(ctx, mx, my - MR - 70 * (MR / 115), 0.6 * MR / 115 * (1 - prog(t, T_VUELTA - 0.15, 0.15)))
    kartel(ctx, "SOLO ELLA", 540, 1200, 74, t, T_UNICA, T_VUELTA - 0.1, box=ROJO, fg=BLANCO, rot=-3)


# ------------------------------------------------------------------ escenas
ESCENAS = [
    (0.0, d_apertura),
    (b(1) - 0.06, d_otro_lado),
    (b(2) - 0.06, d_porque),
    (b(3) - 0.06, d_orbita),
    (b(5) - 0.06, d_casualidad),
    (b(6) - 0.06, d_frena),
    (b(9) - 0.06, d_foto),
    (b(10) - 0.06, d_nave),
    (b(11) - 0.06, d_ella),
    (b(13) - 0.06, d_siglo),
    (b(14) - 0.06, d_dino),
    (b(15) - 0.06, d_futuro),
    (b(16) - 0.06, d_atrapada),
    (T_VUELTA, d_vuelta),
]
XF = 0.18
WHOOSH += [t0 for t0, _ in ESCENAS[1:]]
DERIVA_CAM = {d_orbita, d_frena, d_ella, d_siglo}


def punch(t, t0, d=0.3, amp=0.05):
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


def escena(t):
    return max(k for k, (t0, _) in enumerate(ESCENAS) if t >= t0)


def dibujar(ctx, i, t):
    t0, fn = ESCENAS[i]
    t1 = ESCENAS[i + 1][0] if i + 1 < len(ESCENAS) else TOTAL
    ctx.save()
    if 0 < i < len(ESCENAS) - 1:
        zoom(ctx, punch(t, t0))
    if fn in DERIVA_CAM:
        zoom(ctx, 1 + 0.035 * clamp((t - t0) / (t1 - t0)))
    fn(ctx, t)
    ctx.restore()


def componer(ctx, t):
    i = escena(t)
    t0, fn = ESCENAS[i]
    dt = t - t0
    if i > 0 and dt < XF:
        dibujar(ctx, i - 1, t)
        ctx.push_group()
        dibujar(ctx, i, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(clamp(dt / XF))
        return
    dibujar(ctx, i, t)


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
def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    for t0 in WHOOSH[:-1]:
        ev(t0, "whoosh_suave", 0.4)
    ev(T_GIRA, "pop", 0.35)
    ev(T_CARA - 0.1, "pop", 0.35)
    ev(T_OTRO - 0.1, "whoosh_suave", 0.3)
    ev(T_OTRO, "golpe", 0.45)
    ev(T_PQ - 0.05, "pop", 0.45)
    ev(b(2) + 0.1, "boing", 0.3)
    # órbita
    ev(T_O0 + 0.25, "siseo", 0.12, d=T_O1 - T_O0 - 0.3)
    ev(T_GIRO1, "pop", 0.4)
    ev(T_VUELTA1, "pop", 0.4)
    ev(T_VUELTA1 + 0.15, "ding", 0.4)
    # casualidad
    ev(T_COINC - 0.1, "pop", 0.4)
    ev(T_NO, "whoosh", 0.4)
    ev(T_NO + 0.2, "golpe", 0.55)
    # giraba rápido y la frenan
    ev(b(6), "zumbido", 0.14, d=T_GRAV - b(6))
    ev(T_RAP - 0.1, "pop", 0.35)
    ev(T_GRAV - 0.3, "subida", 0.22, d=0.6)
    for k in range(8):
        ev(T_GRAV + FR_D * (1 - (1 - k / 8) ** 0.5), "tick", 0.2, f=1300 - 90 * k, d=0.04)
    ev(T_TRAB, "clunk", 0.7)
    ev(T_TRAB + 0.02, "golpe", 0.6)
    # foto
    ev(T_FOTO - 0.05, "clic", 0.7)
    ev(T_FOTO, "ding", 0.3)
    # nave
    ev(NV0 + 0.05, "whoosh_suave", 0.35)
    ev(T_1959 - 0.05, "golpe", 0.5)
    # ella nos hace lo mismo
    ev(T_MISMO - 0.05, "boing", 0.35)
    ev(T_FRENA_T - 0.05, "pop", 0.35)
    ev(T_DESP - 0.05, "pop", 0.3)
    # reloj
    for k in range(12):
        ev(b(13) + k * (b(14) - b(13)) / 12, "tick", 0.18, f=1500, d=0.03)
    ev(T_MAS, "ding", 0.35)
    # dinosaurios
    ev(b(14), "pop", 0.35)
    ev(T_MEDIA + 0.05, "golpe", 0.45)
    # futuro
    ev(T_SOBRA - 0.15, "pop", 0.35)
    ev(T_TRAB2, "clunk", 0.7)
    ev(T_TRAB2 + 0.05, "golpe", 0.5)
    # por ahora
    ev(T_AHORA, "clic", 0.5)
    ev(T_UNICA, "pop", 0.35)
    ev(T_VUELTA, "whoosh_suave", 0.35)
    return E


def pista_efectos():
    n = int((TOTAL + 3) * SR)
    mix = np.zeros(n, np.float32)
    for t, k, v, kw in eventos():
        x = K.snd(k, **kw) * v
        i0 = int(t * SR)
        i1 = min(n, i0 + len(x))
        if 0 <= i0 < n:
            mix[i0:i1] += x[:i1 - i0]
    mix = mix[:int(TOTAL * SR)]
    fade = int(0.08 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix *= 0.45 / (np.abs(mix).max() or 1)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "la_luna_siempre_te_mira.mp4"))
    ap.add_argument("--hilos", type=int, default=2)
    ap.add_argument("--probar", action="store_true", help="dibuja 1 de cada 6 cuadros para cazar errores")
    a = ap.parse_args()
    if a.probar:
        for f in range(0, int(TOTAL * FPS), 6):
            cuadro(f / FPS)
        pista_efectos()
        print("sin errores")
        return
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

"""Short "¿Por qué la Luna siempre muestra la misma cara?" — animación procedural (armazón de sueno.py).

Usa las piezas espaciales de cielo.py (estrellas, Tierra con cara, Vos y la loma).
- Gancho (G2): pasan las noches, cambia la fase y la cara de la Luna es siempre la misma. El cuadro de TOTAL es igual al de 0 (loop, F4).
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


def sombra_fase(ctx, x, y, R, f, a=0.82):
    """Sombra de la fase. f = 0 llena, 0.5 nueva, 1 llena otra vez."""
    f = f % 1.0
    th = TAU * f
    if abs(math.sin(th / 2)) < 0.02:
        return
    c = math.cos(th)
    lado = 1 if f < 0.5 else -1
    k = c if f < 0.5 else -c
    N = 40
    ys = [-R + 2 * R * i / N for i in range(N + 1)]
    ctx.new_path()
    for i, yy in enumerate(ys):
        hw = math.sqrt(max(R * R - yy * yy, 0))
        px = x + k * hw
        ctx.line_to(px, y + yy) if i else ctx.move_to(px, y + yy)
    for yy in reversed(ys):
        hw = math.sqrt(max(R * R - yy * yy, 0))
        ctx.line_to(x + lado * hw, y + yy)
    ctx.close_path()
    ctx.set_source_rgba(*CIELO_F, a)
    ctx.fill()


def tierra_g(ctx, x, y, R, t, rot=0.0, ojos="open", boca="smile", ceja=None, look=(0, 0), a=1.0, marea=None):
    """La Tierra con los continentes girando debajo de la cara. marea = (ángulo, cuánto)."""
    if a <= 0.01:
        return
    ctx.save()
    ctx.push_group()
    _elipse_suave(ctx, x, y, R * 1.9, R * 1.9, C.AZUL_T, 0.25)
    if marea:
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(marea[0])
        ctx.scale(1 + 0.2 * marea[1], 1.0)
        ctx.arc(0, 0, R * 1.02, 0, TAU)
        ctx.restore()
        ctx.set_source_rgb(*hx("#8FD0FF"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(max(3, R * 0.05))
        ctx.stroke()
    ctx.arc(x, y, R, 0, TAU)
    ctx.set_source_rgb(*C.AZUL_T)
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    ctx.translate(x, y)
    ctx.rotate(rot)
    for mx, my, rx, ry in C.MANCHAS + [(0.1, -0.75, 0.3, 0.16)]:
        ctx.save()
        ctx.translate(mx * R, my * R)
        ctx.scale(rx * R, ry * R)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.set_source_rgb(*C.VERDE_T)
        ctx.fill()
    ctx.restore()
    ctx.arc(x, y, R, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(3, R * 0.07))
    ctx.stroke()
    C.cara(ctx, x, y, R, ojos, boca, ceja, look)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def medidor(ctx, x, y, R, v, a=1.0, titulo=None):
    """Velocímetro de giro: v de 0 a 1."""
    if a <= 0.01:
        return
    ctx.save()
    ctx.push_group()
    ctx.arc(x, y, R * 1.18, math.pi, TAU)
    ctx.line_to(x + R * 1.18, y + R * 0.3)
    ctx.line_to(x - R * 1.18, y + R * 0.3)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#0B1030"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    for a0, a1, col in ((0, 0.4, VERDE), (0.4, 0.7, AMARILLO), (0.7, 1.0, ROJO)):
        ctx.new_path()
        ctx.arc(x, y, R * 0.9, math.pi + math.pi * a0 + 0.03, math.pi + math.pi * a1 - 0.03)
        ctx.set_source_rgb(*col)
        ctx.set_line_width(R * 0.2)
        ctx.stroke()
    ang = math.pi + math.pi * clamp(v)
    ctx.move_to(x, y)
    ctx.line_to(x + R * 0.82 * math.cos(ang), y + R * 0.82 * math.sin(ang))
    ctx.set_source_rgb(*BLANCO)
    ctx.set_line_width(R * 0.09)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.arc(x, y, R * 0.12, 0, TAU)
    ctx.fill()
    if titulo:
        texto(ctx, titulo, x, y + R * 0.52, R * 0.3, fill=BLANCO, stroke=INK, sw=7)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def cadena(ctx, x0, y0, x1, y1, a=1.0, paso=44):
    if a <= 0.01:
        return
    L = math.hypot(x1 - x0, y1 - y0)
    n = max(2, int(L / paso))
    ang = math.atan2(y1 - y0, x1 - x0)
    for k in range(n):
        q = (k + 0.5) / n
        ctx.save()
        ctx.translate(lerp(x0, x1, q), lerp(y0, y1, q))
        ctx.rotate(ang)
        ctx.scale(paso * 0.62, 15 if k % 2 == 0 else 8)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        for lw, col in ((15, INK), (7, hx("#C9CFD8"))):
            ctx.set_source_rgba(*col, a)
            ctx.set_line_width(lw)
            ctx.stroke_preserve()
        ctx.new_path()


def chispas(ctx, x, y, t, a=1.0, n=12, abanico=(0.15, math.pi - 0.15), largo=170):
    if a <= 0.01:
        return
    for k in range(n):
        ph = (t * 2.4 + k / n + 0.37 * (k % 3)) % 1.0
        ang = lerp(abanico[0], abanico[1], (k * 0.618) % 1.0)
        d = 20 + ph * largo
        estrella(ctx, x + d * math.cos(ang), y + d * math.sin(ang) * 0.6, 16 * (1 - ph) + 3, a * (1 - ph),
                 col=AMARILLO if k % 2 else BLANCO, halo=0.6)


def mosaico(ctx, x0, y0, w, h, t, a=1.0, celda=34):
    if a <= 0.01:
        return
    n = int(t * 5)
    for i in range(int(w / celda) + 1):
        for j in range(int(h / celda) + 1):
            v = (math.sin(i * 12.9898 + j * 78.233 + n * 37.7) * 43758.5453) % 1.0
            g = 0.18 + 0.42 * v
            ctx.rectangle(x0 + i * celda, y0 + j * celda, celda + 1, celda + 1)
            ctx.set_source_rgba(g * 0.85, g * 0.88, g * 1.1, a)
            ctx.fill()


def rodillo(ctx, x, y, w, h, t, t0, t_stop, final, titulo):
    s = pop(t, t0)
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s * bump(t, t_stop, 0.3, 0.12), s * bump(t, t_stop, 0.3, 0.12))
    rrect(ctx, -w / 2 + 8, -h / 2 + 10, w, h, 26)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    rrect(ctx, -w / 2, -h / 2, w, h, 26)
    ctx.set_source_rgb(*PAPEL)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    ctx.save()
    rrect(ctx, -w / 2 + 6, -h / 2 + 6, w - 12, h - 12, 20)
    ctx.clip()
    if t < t_stop:
        u = t * 14
        n = int(u)
        fr = u - n
        for k in (0, 1):
            num = (n * 7 + k * 7) % 60 + 1
            texto(ctx, str(num), 0, -20 + (fr - k) * h * 0.9, 120, fill=INK, stroke=None)
    else:
        texto(ctx, final, 0, -22, 128, fill=ROJO, stroke=None)
    texto(ctx, "DÍAS", 0, h / 2 - 48, 46, fill=INK, stroke=None)
    ctx.restore()
    texto(ctx, titulo, 0, -h / 2 - 50, 50, fill=BLANCO, stroke=INK, sw=9)
    ctx.restore()


def caracol(ctx, x, y, s, t, a=1.0):
    if a <= 0.01 or s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.push_group()
    rrect(ctx, -120, -22, 250, 44, 22)
    ctx.set_source_rgb(*hx("#F2C078"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    for dx in (96, 122):
        ctx.move_to(dx, -18)
        ctx.line_to(dx + 10, -70 + 4 * math.sin(t * 5 + dx))
        ctx.stroke()
        ctx.arc(dx + 10, -74 + 4 * math.sin(t * 5 + dx), 11, 0, TAU)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.stroke()
        ctx.arc(dx + 12, -74 + 4 * math.sin(t * 5 + dx), 4, 0, TAU)
        ctx.fill()
    ctx.arc(-20, -70, 72, 0, TAU)
    ctx.set_source_rgb(*hx("#B5651D"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.new_path()
    for k in range(60):
        an = k * 0.22
        rr = 60 - k * 0.95
        px, py = -20 + rr * math.cos(an), -70 + rr * math.sin(an)
        ctx.line_to(px, py) if k else ctx.move_to(px, py)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def reloj_arena(ctx, x, y, s, q, a=1.0):
    if a <= 0.01 or s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for sg in (-1, 1):
        ctx.move_to(-70, sg * 110)
        ctx.line_to(70, sg * 110)
        ctx.line_to(8, 0)
        ctx.line_to(-8, 0)
        ctx.close_path()
        ctx.set_source_rgba(*hx("#DCEBFF"), 0.9 * a)
        ctx.fill_preserve()
        ctx.set_source_rgba(*INK, a)
        ctx.set_line_width(8)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    h = 80 * (1 - q)
    ctx.move_to(-8 - 62 * h / 110, -h)
    ctx.line_to(8 + 62 * h / 110, -h)
    ctx.line_to(6, -4)
    ctx.line_to(-6, -4)
    ctx.close_path()
    ctx.set_source_rgba(*AMARILLO, a)
    ctx.fill()
    h2 = 70 * q
    ctx.move_to(-66, 106)
    ctx.line_to(66, 106)
    ctx.line_to(66 - 58 * h2 / 106, 106 - h2)
    ctx.line_to(-66 + 58 * h2 / 106, 106 - h2)
    ctx.close_path()
    ctx.fill()
    ctx.move_to(0, 0)
    ctx.line_to(0, 100)
    ctx.set_line_width(5)
    ctx.stroke()
    for sg in (-1, 1):
        rrect(ctx, -86, sg * 118 - 12, 172, 24, 10)
        ctx.set_source_rgba(*hx("#B5651D"), a)
        ctx.fill_preserve()
        ctx.set_source_rgba(*INK, a)
        ctx.set_line_width(7)
        ctx.stroke()
    ctx.restore()


def sacudida(t, t0, d=0.4, amp=16.0):
    if t < t0 or t > t0 + d:
        return 0.0, 0.0
    q = 1 - (t - t0) / d
    return amp * q * math.sin((t - t0) * 83), amp * q * math.cos((t - t0) * 71)


# ------------------------------------------------------------------ 0. apertura (y cierre del loop)
LUNA_A = (640, 560, 250)
VOS_A = (250, 1350, 0.5)
T_GIRA = b(0, "gira")
T_CARA = b(0, "cara")
T_F0 = 0.3
T_F1 = T_CARA + 0.1


def base_apertura(ctx, t, f=0.0):
    fondo(ctx, t)
    campo(ctx, t, 7, 60, 1.0, y1=1220)
    x, y, R = LUNA_A
    luna(ctx, x, y, R, ojos="open", boca="smile", look=(-0.45, 0.35), rubor=True)
    ctx.save()
    ctx.arc(x, y, R - 3, 0, TAU)
    ctx.clip()
    sombra_fase(ctx, x, y, R, f)
    ctx.restore()
    C.loma(ctx)
    C.vos(ctx, VOS_A[0], VOS_A[1], VOS_A[2], ojos=parpadeo(t))


def d_apertura(ctx, t):
    """Pasan las noches, cambia la fase, y la cara es siempre la misma."""
    q = clamp((t - T_F0) / (T_F1 - T_F0))
    f = q * q * (3 - 2 * q)
    base_apertura(ctx, t, f)
    if T_F0 <= t < b(1) - 0.2:
        n = min(29, 1 + int(f * 29))
        s = pop(t, T_F0) * sale(t, b(1) - 0.3)
        cartel(ctx, f"NOCHE {n}", 300, 250, 78, s=s, rot=-5, box=BLANCO)
    s = pop(t, T_CARA - 0.15) * bump(t, T_CARA + 0.2, 0.3, 0.1) * sale(t, b(1) - 0.3)
    if t >= T_CARA - 0.15:
        cartel(ctx, "¡LA MISMA CARA!", 640, 930, 76, s=s, rot=-3)


def d_vuelta(ctx, t):
    base_apertura(ctx, t)


# ------------------------------------------------------------------ 1. nadie vio el otro lado
T_OTRO = b(1, "otro")
T_DESDE = b(1, "desde")


def d_otro_lado(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 11, 50, 0.9, y1=1300)
    ex, ey, ER = 540, 1220, 170
    mx, my, MR = 540, 590, 240
    for k in (-2, -1, 0, 1, 2):
        punteada(ctx, ex + k * 45, ey - ER + 10, mx + k * 95, my + 120 + 20 * abs(k), LUZ, 6,
                 0.6 * prog(t, b(1) + 0.1, 0.4), fase=-t * 80)
    tierra(ctx, ex, ey, ER, t, ojos="wide", boca="o", look=(0, -1))
    luna(ctx, mx, my, MR, ojos="open", boca="smile", look=(0, 0.8))
    q = prog(t, T_OTRO - 0.25, 0.3)
    if q > 0.01:                                  # la mitad que da al espacio, censurada
        ctx.save()
        ctx.arc(mx, my, MR - 4, 0, TAU)
        ctx.clip()
        mosaico(ctx, mx - MR, my - MR, 2 * MR, MR * 0.62, t, a=q)
        ctx.restore()
        ctx.move_to(mx - MR * 0.93, my - MR * 0.38)
        ctx.line_to(mx + MR * 0.93, my - MR * 0.38)
        ctx.set_source_rgba(*INK, q)
        ctx.set_line_width(8)
        ctx.stroke()
        texto(ctx, "?", mx, my - MR * 0.68, 130 * pop(t, T_OTRO) * (1 + 0.06 * math.sin(t * 9)), fill=AMARILLO,
              stroke=INK, sw=12)
    kartel(ctx, "NUNCA VISTO", 540, 200, 78, t, T_OTRO, box=ROJO, fg=BLANCO, rot=-4)


# ------------------------------------------------------------------ 2. ¿por qué nunca se da vuelta?
T_PQ = b(2, "por")
T_VUELTA2 = b(2, "vuelta")


def d_porque(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 13, 50, 0.9)
    q = clamp((t - b(2)) / max(b(3) - b(2), 0.1))
    ang = 1.25 * math.sin(TAU * 1.5 * q) * (1 - 0.3 * q)       # intenta darse vuelta y rebota
    sx = max(0.12, math.cos(ang))
    luna(ctx, 540 + 60 * math.sin(ang), 680, 260, ojos="wide", boca="o", look=(1.0 if ang > 0 else -1.0, 0),
         sx=sx, ceja="worried")
    for k in range(3):                                         # gotitas de esfuerzo
        ph = (t * 1.8 + k / 3) % 1
        gx = 540 + (230 + 90 * ph) * (1 if k % 2 else -1)
        gy = 480 - 60 * k + 120 * ph * ph
        ctx.save()
        ctx.translate(gx, gy)
        ctx.scale(12, 18)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.set_source_rgba(*hx("#8FD0FF"), 1 - ph)
        ctx.fill()
    s = pop(t, T_PQ - 0.05) * bump(t, T_VUELTA2, 0.35, 0.12)
    cartel(ctx, "¿POR QUÉ NUNCA\nSE DA VUELTA?", 540, 1160, 76, s=s, rot=-2)


# ------------------------------------------------------------------ 3-4. la órbita vista desde arriba
OC = (540, 610)
ORB = 330
T_O0 = b(3) - 0.05
T_O1 = b(4, "Tierra", fin=True)
T_GIRO1 = b(4, "misma")
T_VUELTA1 = b(4, "Tierra")
INS = (810, 1170, 100)


def fi(t):
    return -math.pi / 2 - TAU * prog(t, T_O0 + 0.25, T_O1 - T_O0 - 0.25, "inout")


def luna_arriba(ctx, x, y, R, f, halo=0.5):
    """La Luna en la vista de arriba: la cara apunta a la Tierra y la espalda queda a oscuras."""
    rot = f + math.pi / 2
    luna(ctx, x, y, R, ojos="open", boca="smile", look=(0, 0.8), rot=rot, halo=halo)
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.arc(0, 0, R - 2, 0, TAU)
    ctx.clip()
    ctx.rectangle(-R, -R, 2 * R, R * 0.62)
    ctx.set_source_rgba(*hx("#3A2A6B"), 0.8)
    ctx.fill()
    ctx.restore()


def d_orbita(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 17, 50, 0.8)
    ctx.arc(*OC, ORB, 0, TAU)
    ctx.set_source_rgba(1, 1, 1, 0.35)
    ctx.set_line_width(5)
    ctx.set_dash([16, 18])
    ctx.stroke()
    ctx.set_dash([])
    f = fi(t)
    if f < -math.pi / 2 - 0.01:
        ctx.new_path()
        ctx.arc_negative(*OC, ORB, -math.pi / 2, f)
        ctx.set_source_rgb(*AMARILLO)
        ctx.set_line_width(12)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    for k in range(1, 4):                                       # fantasmas cada cuarto de vuelta
        fk = -math.pi / 2 - TAU * k / 4
        if f < fk - 0.25:
            ctx.push_group()
            luna_arriba(ctx, OC[0] + ORB * math.cos(fk), OC[1] + ORB * math.sin(fk), 70, fk, halo=0)
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(0.38)
    mx, my = OC[0] + ORB * math.cos(f), OC[1] + ORB * math.sin(f)
    punteada(ctx, mx, my, OC[0], OC[1], LUZ, 6, 0.6, fase=-t * 60)
    tierra(ctx, *OC, 125, t, ojos="open", boca="smile", look=(0.7 * math.cos(f), 0.7 * math.sin(f)))
    luna_arriba(ctx, mx, my, 92, f)
    # recuadro: la misma Luna, quieta en su lugar, para ver que sí gira
    ix, iy, ir = INS
    a = prog(t, T_O0 + 0.15, 0.3)
    if a > 0.01:
        ctx.push_group()
        ctx.arc(ix, iy, ir + 34, 0, TAU)
        ctx.set_source_rgb(*hx("#0B1030"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*AMARILLO)
        ctx.set_line_width(8)
        ctx.stroke()
        luna_arriba(ctx, ix, iy, ir, f, halo=0)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)
        texto(ctx, "ELLA SOLA", ix, iy - ir - 78, 46, fill=BLANCO, stroke=INK, sw=8, alpha=a)
    kartel(ctx, "1 VUELTA", 300, 1120, 70, t, T_VUELTA1, rot=-4, box=BLANCO)
    kartel(ctx, "= 1 GIRO", 320, 1250, 70, t, T_VUELTA1 + 0.25, rot=3)


# ------------------------------------------------------------------ 5. ¿casualidad? no
T_COINC = b(5, "coincidencia")
T_NO = b(5, "no")
T_R1 = b(5) + 0.75
T_R2 = T_COINC + 0.45


def d_casualidad(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 19, 50, 0.8)
    rodillo(ctx, 300, 640, 380, 330, t, b(5), T_R1, "27", "GIRO")
    rodillo(ctx, 780, 640, 380, 330, t, b(5) + 0.12, T_R2, "27", "VUELTA")
    if t >= T_R2:
        texto(ctx, "=", 540, 640, 110 * pop(t, T_R2), fill=AMARILLO, stroke=INK, sw=12)
    kartel(ctx, "¿CASUALIDAD?", 540, 250, 86, t, T_COINC - 0.1, rot=-4, box=BLANCO)
    if t >= T_NO:
        tachado(ctx, 540, 250, 640, prog(t, T_NO, 0.25), ang=-4)
        s = max(pop(t, T_NO + 0.12, 0.3), 0.001)
        ctx.save()
        ctx.translate(540, 1040)
        ctx.rotate(math.radians(-9))
        ctx.scale(s, s)
        rrect(ctx, -300, -90, 600, 180, 24)
        ctx.set_source_rgba(*ROJO, 0.95)
        ctx.set_line_width(16)
        ctx.stroke()
        texto(ctx, "NO LO ES", 0, 0, 120, fill=ROJO, stroke=None)
        ctx.restore()


# ------------------------------------------------------------------ 6-8. giraba rápido, la Tierra la frena, trabada
T_E0 = b(6) - 0.06
T_RAP = b(6, "rapido")
T_GRAV = b(7, "gravedad")
T_FREN = b(7, "frenando")
T_TRAB = b(8, "trabada")
T_MIR = b(8, "mirandonos")
FR_D = T_TRAB - T_GRAV
_v = (T_GRAV - T_E0 + FR_D / 2)
W0 = TAU * round(1.5 * _v) / _v                        # frena justo con la cara hacia la Tierra


def giro_luna(t):
    if t < T_GRAV:
        return W0 * (t - T_E0)
    q = clamp((t - T_GRAV) / FR_D)
    return W0 * (T_GRAV - T_E0) + W0 * FR_D * (q - q * q / 2)


def d_frena(ctx, t):
    dx, dy = sacudida(t, T_TRAB, 0.45, 20)
    ctx.translate(dx, dy)
    fondo(ctx, t)
    campo(ctx, t, 23, 50, 0.8, y1=1100)
    sube = prog(t, T_GRAV - 0.35, 0.6)
    ex, ey, ER = 540, lerp(1650, 1180, sube), 190
    mx, my, R = 540, 590, 195
    q = clamp((t - T_GRAV) / FR_D)
    va = 1 - q if t >= T_GRAV else 1.0
    g = giro_luna(t)
    for k in range(4):                                        # líneas de velocidad, sin punta
        a0 = -g * 0.7 + k * TAU / 4
        ctx.new_path()
        ctx.arc(mx, my, R + 38 + 26 * (k % 2), a0, a0 + 0.2 + 0.9 * va)
        ctx.set_source_rgba(1, 1, 1, 0.55 * va)
        ctx.set_line_width(9)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    frenando = T_GRAV <= t < T_TRAB
    if sube > 0.01:
        gravedad(ctx, ex, ey - ER, mx, my + R, t, a=sube, n=3, sep=60)
    tierra(ctx, ex, ey, ER, t, ojos="open" if t < T_TRAB else "happy", boca="grin" if t < T_TRAB else "smile",
           ceja="angry" if frenando else None, look=(0, -1), a=sube)
    quieta = t >= T_TRAB - 0.3
    luna(ctx, mx, my, R, ojos="wide" if not quieta else "open",
         boca="o" if not quieta else ("flat" if t < T_MIR else "smile"), look=(0, 0.9) if quieta else (0, 0),
         rot=-g)
    if frenando:
        chispas(ctx, mx, my + R - 6, t, a=0.4 + 0.6 * va)
    medidor(ctx, 850, 330, 120, 0.92 * va + 0.02 * math.sin(t * 40) * va, a=prog(t, b(6) + 0.1, 0.3),
            titulo="GIRO")
    kartel(ctx, "HACE MUCHO", 330, 200, 68, t, b(6) + 0.05, T_GRAV - 0.2, box=BLANCO, rot=-4)
    kartel(ctx, "LA FRENA", 330, 200, 76, t, T_FREN - 0.15, T_TRAB - 0.15, rot=-3)
    if t >= T_TRAB:
        cadena(ctx, ex, ey - ER + 10, mx, my + R - 10, a=prog(t, T_TRAB, 0.15))
        candado(ctx, 540, (ey - ER + my + R) / 2 + 20, 0.95 * pop(t, T_TRAB))
        kartel(ctx, "TRABADA", 330, 200, 80, t, T_TRAB, box=ROJO, fg=BLANCO, rot=-3)


# ------------------------------------------------------------------ 9. el otro lado, por una foto
T_FOTO = b(9, "foto")


def d_foto(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 29, 50, 0.8)
    pre = 1 - prog(t, T_FOTO - 0.05, 0.25)
    if pre > 0.01:
        mx, my, MR = 540, 700, 240
        ctx.push_group()
        luna(ctx, mx, my, MR, ojos="open", boca="smile", look=(0, 0.8))
        ctx.save()
        ctx.arc(mx, my, MR - 4, 0, TAU)
        ctx.clip()
        mosaico(ctx, mx - MR, my - MR, 2 * MR, MR * 0.62, t)
        ctx.restore()
        texto(ctx, "?", mx, my - MR * 0.68, 130, fill=AMARILLO, stroke=INK, sw=12)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(pre)
    kartel(ctx, "EL OTRO LADO", 540, 200, 74, t, b(9) + 0.05, rot=-3)
    if t >= T_FOTO - 0.05:
        s = pop(t, T_FOTO - 0.05, 0.45)
        rev = prog(t, T_FOTO + 0.1, 0.8)
        ctx.save()
        ctx.translate(540, 760)
        ctx.rotate(math.radians(-4 + 2 * math.sin(t * 2)))
        ctx.scale(s, s)
        rrect(ctx, -320, -350, 660, 780, 18)
        ctx.set_source_rgb(*INK)
        ctx.fill()
        rrect(ctx, -330, -362, 660, 780, 18)
        ctx.set_source_rgb(*PAPEL)
        ctx.fill()
        rrect(ctx, -290, -322, 580, 580, 8)
        ctx.set_source_rgb(*CIELO_F)
        ctx.fill()
        luna(ctx, 0, -32, 240, lado="lejos", a=rev, halo=0.4)
        texto(ctx, "SIN CARA", 0, 338, 70, fill=INK, stroke=None, alpha=rev)
        ctx.restore()
    flash(ctx, t, T_FOTO)


# ------------------------------------------------------------------ 10. una nave en 1959
T_NAVE = b(10, "nave")
T_1959 = b(10, "1959")
NV0, NV1 = b(10) - 0.06, b(11) - 0.1
MN = (640, 640, 190)
T_CLICK = lerp(NV0, NV1, 0.52)


def pos_nave(t):
    q = clamp((t - NV0) / (NV1 - NV0))
    q = q * q * (3 - 2 * q)
    ang = lerp(math.radians(140), math.radians(-200), q)
    return MN[0] + 330 * math.cos(ang), MN[1] + 400 * math.sin(ang), ang


def d_nave(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 31, 50, 0.8)
    tx, ty = 170, 1230
    tierra(ctx, tx, ty, 125, t, ojos="open" if t < T_CLICK else "wide", boca="smile" if t < T_CLICK else "o",
           look=(0.7, -0.7))
    luna(ctx, *MN, ojos="open", boca="smile", look=(-0.6, 0.7))
    n = max(1, int(60 * clamp((t - NV0) / (NV1 - NV0))))
    pts = [pos_nave(NV0 + (NV1 - NV0) * k / 60) for k in range(n + 1)]
    ctx.move_to(pts[0][0], pts[0][1])
    for p in pts[1:]:
        ctx.line_to(p[0], p[1])
    ctx.set_source_rgba(*LUZ, 0.6)
    ctx.set_line_width(7)
    ctx.set_dash([16, 14])
    ctx.stroke()
    ctx.set_dash([])
    x, y, ang = pos_nave(t)
    nave(ctx, x, y, 1.5, rot=ang + math.pi / 2, a=prog(t, NV0, 0.2))
    if t >= T_CLICK:                               # saca la foto detrás de la Luna y la manda a la Tierra
        fx, fy = pos_nave(T_CLICK)[:2]
        fl = 1 - clamp((t - T_CLICK) / 0.3)
        estrella(ctx, fx, fy + 50, 90 * fl, fl, col=BLANCO)
        q = prog(t, T_CLICK + 0.15, NV1 - T_CLICK - 0.2, "inout")
        px, py = lerp(fx, tx + 60, q), lerp(fy, ty - 190, q) - 160 * math.sin(math.pi * q)
        ctx.save()
        ctx.translate(px, py)
        ctx.rotate(-0.3 + 0.5 * q)
        ctx.scale(0.24, 0.24)
        rrect(ctx, -330, -362, 660, 780, 18)
        ctx.set_source_rgb(*PAPEL)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(26)
        ctx.stroke()
        rrect(ctx, -290, -322, 580, 580, 8)
        ctx.set_source_rgb(*CIELO_F)
        ctx.fill()
        luna(ctx, 0, -32, 240, lado="lejos", halo=0)
        ctx.restore()
    kartel(ctx, "1959", 300, 240, 130, t, T_1959 - 0.05, rot=-5)


# ------------------------------------------------------------------ 11-12. ella nos hace lo mismo
T_EXTR = b(11, "extraño")
T_MISMO = b(11, "mismo")
T_FRENA_T = b(12, "frena")
T_DESP = b(12, "despacio")


def d_ella(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 37, 50, 0.8)
    ex, ey, ER = 470, 900, 245
    mx, my, MR = 850, 330, 120
    sorpresa = t >= T_MISMO
    dirl = math.atan2(my - ey, mx - ex)
    tira = prog(t, T_EXTR, 0.5)
    rot = -TAU * 0.3 * (t - b(11))
    gravedad(ctx, mx - 60, my + MR - 20, ex + (ER + 30) * math.cos(dirl), ey + (ER + 30) * math.sin(dirl), -t,
             a=tira, n=3, sep=50)
    tierra_g(ctx, ex, ey, ER, t, rot=rot, ojos="wide" if sorpresa else "open", boca="o" if sorpresa else "smile",
             look=(0.7, -0.7), marea=(dirl, tira))
    if t >= T_FRENA_T:
        chispas(ctx, ex + (ER + 20) * math.cos(dirl), ey + (ER + 20) * math.sin(dirl), t, a=0.8, n=8,
                abanico=(dirl - 1.3, dirl + 1.3), largo=110)
    luna(ctx, mx, my, MR, ojos="happy" if sorpresa else "open", boca="grin", look=(-0.7, 0.7), halo=0.6,
         ceja="angry" if t >= T_FRENA_T else None)
    kartel(ctx, "¡LO MISMO!", 340, 250, 82, t, T_MISMO - 0.05, b(12) - 0.1, rot=-5)
    if t >= b(12):
        medidor(ctx, 260, 330, 120, 0.62 - 0.03 * prog(t, T_FRENA_T, 2.0), a=prog(t, b(12), 0.3), titulo="GIRO")
    if t >= T_DESP - 0.1:
        q = prog(t, T_DESP - 0.1, 0.35, "out")
        caracol(ctx, lerp(-200, 250, q) + 30 * (t - T_DESP), 1290, 0.9, t)
        kartel(ctx, "MUY DESPACIO", 700, 1270, 66, t, T_DESP, box=BLANCO, rot=3)


# ------------------------------------------------------------------ 13. cada siglo, un poquito más
T_SIGLO = b(13, "siglo")
T_DIAS = b(13, "dias")
T_MAS = b(13, "poquito")
SIGLOS = ["XVIII", "XIX", "XX", "XXI"]


def d_siglo(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 41, 40, 0.7)
    k = min(3, int(4 * clamp((t - b(13)) / (T_MAS - b(13) + 0.3))))
    kartel(ctx, f"SIGLO {SIGLOS[k]}", 540, 260, 92, t, b(13) + 0.02, rot=-3)
    bx0, bx1, by, bh = 110, 900, 600, 120
    rrect(ctx, bx0 + 8, by + 10, bx1 - bx0 + 60, bh, 26)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    rrect(ctx, bx0, by, bx1 - bx0, bh, 26)
    ctx.set_source_rgb(*hx("#3D8BFF"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    extra = 14 * (k + 1)
    rrect(ctx, bx1 - 12, by, extra + 12, bh, 12)
    ctx.set_source_rgb(*AMARILLO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    texto(ctx, "TU DÍA: 24 HORAS", (bx0 + bx1) / 2, by + bh / 2, 70, fill=BLANCO, stroke=INK, sw=9)
    if t >= T_DIAS - 0.1:                           # lupa sobre la puntita
        s = pop(t, T_DIAS - 0.1)
        lx, ly, lr = 640, 1050, 210 * s
        ctx.move_to(bx1 + 10, by + bh)
        ctx.line_to(lx + 60, ly - lr + 10)
        ctx.set_source_rgba(1, 1, 1, 0.7)
        ctx.set_line_width(6)
        ctx.stroke()
        ctx.arc(lx, ly, lr, 0, TAU)
        ctx.set_source_rgb(*hx("#0B1030"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*BLANCO)
        ctx.set_line_width(14)
        ctx.stroke_preserve()
        ctx.save()
        ctx.clip()
        ctx.rectangle(lx - lr, ly - 150 * s, lr * 0.9, 120 * s)
        ctx.set_source_rgb(*hx("#3D8BFF"))
        ctx.fill()
        ctx.rectangle(lx - lr * 0.1, ly - 150 * s, lr * (0.5 + 0.1 * math.sin(t * 6)), 120 * s)
        ctx.set_source_rgb(*AMARILLO)
        ctx.fill()
        ctx.restore()
        texto(ctx, "+0,002 s", lx, ly + 70 * s, 84 * s, fill=AMARILLO, stroke=INK, sw=10)
        ctx.move_to(lx - lr * 0.75, ly + lr * 0.75)
        ctx.line_to(lx - lr * 1.25, ly + lr * 1.25)
        ctx.set_source_rgb(*BLANCO)
        ctx.set_line_width(30)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()


# ------------------------------------------------------------------ 14. los dinosaurios
T_DINO = b(14, "dinosaurios")
T_MEDIA = b(14, "media")
T_MENOS = b(14, "menos")


def d_dino(ctx, t):
    fondo(ctx, t)
    q = clamp((t - b(14)) / (b(15) - b(14)))
    sa = math.pi * (1 + (2.2 * q) % 1.0)                       # el sol cruza rápido: los días pasan volando
    dia = max(0.0, math.sin(sa - math.pi))
    g = cairo.LinearGradient(0, 200, 0, 1400)
    g.add_color_stop_rgba(0, 0.35, 0.6, 1.0, 0.55 * dia)
    g.add_color_stop_rgba(1, 1.0, 0.75, 0.4, 0.5 * dia)
    ctx.set_source(g)
    ctx.paint()
    campo(ctx, t, 43, 40, 0.8 * (1 - dia), y1=800)
    C.sol(ctx, 540 + 620 * math.cos(sa), 1150 + 900 * math.sin(sa), 110, t)
    C.loma(ctx)
    dino(ctx, 400, 1345, 0.92 * pop(t, b(14) - 0.05, 0.4), t)
    cuna = 0.5 * prog(t, T_MEDIA, T_MENOS - T_MEDIA + 0.2)
    reloj(ctx, 790, 560, 215, hora=24 - cuna, cuna=cuna * 1.0, a=prog(t, T_DINO + 0.3, 0.3))
    kartel(ctx, "−30 MIN", 790, 850, 70, t, T_MEDIA + 0.05, box=ROJO, fg=BLANCO, rot=4)
    kartel(ctx, "HACE 70 MILLONES DE AÑOS", 540, 200, 54, t, T_DINO, box=BLANCO, rot=-2)


# ------------------------------------------------------------------ 15. con tiempo de sobra, las dos trabadas
T_SOBRA = b(15, "sobra")
T_TAMB = b(15, "tambien")
T_TRAB2 = b(15, "trabada")
EF = (310, 700, 180)
MF = (810, 700, 120)


def giro_tierra_f(t):
    q = clamp((t - b(15)) / (T_TRAB2 - b(15)))
    return -TAU * 1.2 * (q - q * q / 2)


def d_futuro(ctx, t):
    dx, dy = sacudida(t, T_TRAB2, 0.4, 18)
    ctx.translate(dx, dy)
    fondo(ctx, t)
    campo(ctx, t, 47, 50, 0.8)
    ex, ey, ER = EF
    mx, my, MR = MF
    cadena(ctx, mx - MR + 8, my, ex + ER - 8, ey, a=prog(t, T_TAMB, 0.4))
    tierra_g(ctx, ex, ey, ER, t, rot=giro_tierra_f(t), ojos="open" if t < T_TRAB2 else "wide",
             boca="smile" if t < T_TRAB2 else "flat", look=(1, 0), marea=(0, 0.6))
    luna(ctx, mx, my, MR, ojos="happy", boca="grin", look=(-1, 0), halo=0.6)
    if t >= T_TRAB2:
        candado(ctx, (ex + ER + mx - MR) / 2, ey + 14, 0.8 * pop(t, T_TRAB2))
    q = clamp((t - b(15)) / (T_TRAB2 - b(15)))
    reloj_arena(ctx, 540, 1130, pop(t, T_SOBRA - 0.2), q)
    kartel(ctx, "MUCHÍSIMO TIEMPO", 540, 250, 72, t, T_SOBRA - 0.15, rot=-3)


# ------------------------------------------------------------------ 16. por ahora, la única atrapada es ella
T_AHORA = b(16, "ahora")
T_UNICA = b(16, "unica")
T_ELLA = b(16, "ella")
T_VUELTA = T_ELLA - 0.12


def d_atrapada(ctx, t):
    fondo(ctx, t)
    campo(ctx, t, 47, 50, 0.8)
    q = prog(t, T_UNICA - 0.1, T_VUELTA - T_UNICA + 0.15, "inout")
    ex, ey, ER = lerp(EF[0], -260, q), lerp(EF[1], 1150, q), EF[2]
    mx, my, MR = lerp(MF[0], LUNA_A[0], q), lerp(MF[1], LUNA_A[1], q), lerp(MF[2], LUNA_A[2], q)
    libre = prog(t, T_AHORA, 0.35)
    cadena(ctx, mx - MR + 8, my, ex + ER - 8, ey, a=1 - libre)
    candado(ctx, (ex + ER + mx - MR) / 2, ey + 14 + 500 * libre * libre, 0.8, a=1 - 0.6 * libre, abierto=libre)
    tierra_g(ctx, ex, ey, ER, t, rot=giro_tierra_f(b(16)) - TAU * 0.7 * (t - T_AHORA) * libre,
             ojos="happy", boca="grin", look=(1, 0), a=1 - q, marea=(0, 0.6))
    luna(ctx, mx, my, MR, ojos="open", boca="flat" if q < 0.7 else "smile", ceja="worried" if q < 0.7 else None,
         look=(lerp(-1, -0.45, q), lerp(0, 0.35, q)), rubor=q > 0.7)
    kartel(ctx, "SOLO ELLA", 540, 1200, 78, t, T_UNICA, T_VUELTA - 0.1, box=ROJO, fg=BLANCO, rot=-3)


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
DERIVA_CAM = {d_orbita, d_frena, d_ella, d_siglo, d_otro_lado, d_nave}


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
        zoom(ctx, 1 + 0.04 * clamp((t - t0) / (t1 - t0)))
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


# ------------------------------------------------------------------ sonido (sin zumbidos ni siseos sostenidos)
def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    for t0 in WHOOSH[:-1]:
        ev(t0, "whoosh_suave", 0.35)
    for k in range(8):                                   # las noches que pasan
        ev(T_F0 + (T_F1 - T_F0) * k / 8, "tick", 0.14, f=1400, d=0.03)
    ev(T_CARA - 0.15, "pop", 0.4)
    ev(T_OTRO, "golpe", 0.45)
    ev(T_PQ - 0.05, "pop", 0.45)
    ev(b(2) + 0.25, "boing", 0.3)
    for k in range(1, 4):                                # cada cuarto de vuelta
        ev(T_O0 + 0.25 + (T_O1 - T_O0 - 0.25) * k / 4, "tick", 0.2, f=1100 + 150 * k, d=0.05)
    ev(T_VUELTA1, "ding", 0.4)
    ev(T_VUELTA1 + 0.25, "pop", 0.4)
    for k in range(10):                                  # los rodillos
        ev(b(5) + 0.08 * k, "tick", 0.16, f=900, d=0.03)
    ev(T_R1, "clunk", 0.5)
    ev(T_R2, "clunk", 0.5)
    ev(T_R2 + 0.02, "ding", 0.35)
    ev(T_NO + 0.12, "golpe", 0.7)
    n = int(W0 * (T_GRAV - T_E0) / TAU)
    for k in range(n):                                   # una pasada por vuelta mientras gira rápido
        ev(T_E0 + (k + 0.5) * TAU / W0, "whoosh_suave", 0.22)
    for k in range(7):
        ev(T_GRAV + FR_D * (1 - (1 - k / 7) ** 0.5), "tick", 0.2, f=1300 - 110 * k, d=0.05)
    ev(T_TRAB, "clunk", 0.8)
    ev(T_TRAB + 0.02, "golpe", 0.7)
    ev(T_FOTO - 0.05, "clic", 0.7)
    ev(T_FOTO + 0.1, "ding", 0.3)
    ev(T_CLICK, "clic", 0.6)
    ev(T_1959 - 0.05, "golpe", 0.5)
    ev(T_MISMO - 0.05, "boing", 0.35)
    ev(T_FRENA_T, "pop", 0.3)
    ev(T_DESP, "pop", 0.35)
    for k in range(4):
        ev(b(13) + 0.02 + k * (T_MAS - b(13) + 0.3) / 4, "pop", 0.3)
    ev(T_DIAS - 0.1, "ding", 0.35)
    ev(b(14), "pop", 0.35)
    ev(T_MEDIA + 0.05, "golpe", 0.45)
    ev(T_SOBRA - 0.15, "pop", 0.35)
    ev(T_TRAB2, "clunk", 0.8)
    ev(T_TRAB2 + 0.03, "golpe", 0.6)
    ev(T_AHORA, "clic", 0.5)
    ev(T_UNICA, "pop", 0.35)
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
    mix *= 0.4 / (np.abs(mix).max() or 1)
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

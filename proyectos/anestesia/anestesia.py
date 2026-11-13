"""Short "Así operaban antes de la anestesia" — animación procedural (armazón de estomago.py).

Tema con violencia real: tono sobrio, sin personajes, sin caras y sin caricaturas (regla V3). Todo se cuenta con
objetos: la mesa con correas, la sierra, el reloj de bolsillo, las gradas, el inhalador de éter, un ojo y una línea
de dolor. Sin sangre. El último cuadro es igual al primero (loop).

    python proyectos/anestesia/anestesia.py --fotos 0,5.5,14
    python proyectos/anestesia/anestesia.py --probar
    python proyectos/anestesia/anestesia.py        # render completo -> salidas/asi_operaban_antes_de_la_anestesia.mp4
"""
import argparse
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
for _p in (ROOT, os.path.join(ROOT, "proyectos", "pantalla"), os.path.join(ROOT, "proyectos", "picante")):
    sys.path.insert(0, _p)
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, bump, cartel, clamp, ease, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rng, rrect, texto)
from picante import _elipse_suave, capa, fondo_azul, mezcla  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Hace menos de 200 años, te operaban despierto.",                        # b0
    "No existía nada que te durmiera.",                                      # b1
    "Sentías cada corte, de principio a fin.",                               # b2
    "Para aguantar, te daban alcohol u opio.",                               # b3
    "No alcanzaba:",                                                         # b4
    "varios ayudantes te sujetaban contra la mesa.",                         # b5
    "Por eso, al cirujano no se lo medía por su cuidado.",                   # b6
    "Se lo medía por su velocidad.",                                         # b7
    "Cuanto menos duraba la operación, menos sufrías.",                      # b8
    "Los mejores amputaban una pierna en menos de 30 segundos.",             # b9
    "Los estudiantes miraban con el reloj en la mano.",                      # b10
    "Con tanto dolor, solo se operaba para salvar una vida.",                # b11
    "Todo cambió en 1846.",                                                  # b12
    "En Boston, un paciente respiró un vapor nuevo: el éter.",               # b13
    "Se quedó dormido y le quitaron un bulto de la mandíbula.",              # b14
    "No sintió nada.",                                                       # b15
    "Dos meses después, la noticia llegó a Londres.",                        # b16
    "Allí trabajaba el cirujano más rápido de su época.",                    # b17
    "Durmió a su paciente con éter y le amputó una pierna.",                 # b18
    "Fue tan veloz como siempre.",                                           # b19
    "El paciente despertó a los pocos minutos.",                             # b20
    "Preguntó cuándo iba a empezar la operación.",                           # b21
    "No sabía de lo que se había salvado:",                                  # b22
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


# ------------------------------------------------------------------ colores (paleta sobria)
MADERA = hx("#7A4E2D")
MADERA_OSC = hx("#55341C")
MADERA_CLARA = hx("#9C6A42")
CUERO = hx("#3E2A1E")
BRONCE = hx("#C9A23A")
ACERO = hx("#C9CFD8")
ACERO_OSC = hx("#8C95A3")
CREMA = hx("#F6EEDC")
ROJO = hx("#E5383B")
LUZ = hx("#FFE6A8")
VIDRIO = hx("#BFE3FF")
SOMBRA = hx("#141A33")
SOMBRA_B = hx("#3B4687")
PIEL = hx("#D9A58E")
VERDE = hx("#2BD45A")
KF = 60 * round(14 * TOTAL / 60) / (14 * TOTAL)      # el fondo de puntos cierra justo en el loop
POPS, WHOOSH = [], []


# ------------------------------------------------------------------ ayudas
def fondo(ctx, t, oscuro=0.0):
    fondo_azul(ctx, t * KF)
    if oscuro > 0:
        ctx.set_source_rgba(0.027, 0.043, 0.11, oscuro)
        ctx.paint()


def sale(t, t1, d=0.2):
    return 1 - prog(t, t1, d, "in")


def zoom(ctx, z, cx=540, cy=900):
    z = max(z, 0.01)
    ctx.translate(cx, cy)
    ctx.scale(z, z)
    ctx.translate(-cx, -cy)


def kartel(ctx, txt, x, y, size, t, t0, t1=None, **kw):
    if t < t0:
        return
    s = pop(t, t0) * (sale(t, t1) if t1 is not None else 1.0)
    if s > 0.01:
        cartel(ctx, txt, x, y, size, s=s, **kw)


def capsula(ctx, x0, y0, x1, y1, w):
    ctx.move_to(x0, y0)
    ctx.line_to(x1, y1)
    ctx.set_line_width(w)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)


def luz_cenital(ctx, x, a=1.0, ancho=520, y1=1150):
    """Cono de luz que baja desde un tragaluz, como en los quirófanos de la época."""
    if a <= 0.01:
        return
    g = cairo.LinearGradient(0, 0, 0, y1)
    g.add_color_stop_rgba(0, *LUZ, 0.32 * a)
    g.add_color_stop_rgba(1, *LUZ, 0.05 * a)
    ctx.move_to(x - 120, -20)
    ctx.line_to(x + 120, -20)
    ctx.line_to(x + ancho, y1)
    ctx.line_to(x - ancho, y1)
    ctx.close_path()
    ctx.set_source(g)
    ctx.fill()


def tachado(ctx, x, y, w, p, ang=-8, grosor=18):
    if p <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(ang))
    for lw, col in ((grosor + 12, INK), (grosor, ROJO)):
        ctx.move_to(-w / 2, 0)
        ctx.line_to(-w / 2 + w * p, 0)
        ctx.set_line_width(lw)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgb(*col)
        ctx.stroke()
    ctx.restore()


def cruz(ctx, x, y, r, s=1.0):
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
        ctx.set_source_rgb(*col)
        ctx.stroke()
    ctx.restore()


# ------------------------------------------------------------------ la mesa de operaciones (vista de tres cuartos)
MB_Y, MF_Y, MFACE = 900, 1060, 52               # borde de atrás, borde de adelante, espesor
MB_X0, MB_X1, MF_X0, MF_X1 = 250, 830, 150, 930


def sobre_mesa(u, v):
    """Punto de la tabla: u de izquierda a derecha, v de atrás (0) hacia adelante (1)."""
    x0 = lerp(MB_X0, MF_X0, v)
    x1 = lerp(MB_X1, MF_X1, v)
    return lerp(x0, x1, u), lerp(MB_Y, MF_Y, v)


def mesa(ctx, apriete=0.0):
    # patas de atrás
    for x in (MB_X0 + 40, MB_X1 - 40):
        ctx.rectangle(x - 15, MB_Y + 40, 30, 300)
        ctx.set_source_rgb(*MADERA_OSC)
        ctx.fill()
    # tabla
    ctx.move_to(MB_X0, MB_Y)
    ctx.line_to(MB_X1, MB_Y)
    ctx.line_to(MF_X1, MF_Y)
    ctx.line_to(MF_X0, MF_Y)
    ctx.close_path()
    ctx.set_source_rgb(*MADERA)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    for v in (0.33, 0.66):                       # vetas de la madera
        x0, y0 = sobre_mesa(0.03, v)
        x1, y1 = sobre_mesa(0.97, v)
        ctx.move_to(x0, y0)
        ctx.line_to(x1, y1)
        ctx.set_source_rgba(*MADERA_OSC, 0.55)
        ctx.set_line_width(4)
        ctx.stroke()
    # frente
    ctx.rectangle(MF_X0, MF_Y, MF_X1 - MF_X0, MFACE)
    ctx.set_source_rgb(*MADERA_OSC)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    # patas de adelante
    for x in (MF_X0 + 30, MF_X1 - 30):
        ctx.rectangle(x - 20, MF_Y + MFACE, 40, 300)
        ctx.set_source_rgb(*MADERA_OSC)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(8)
        ctx.stroke()
    # correas de cuero con hebilla
    for u in (0.27, 0.7):
        bx0, by0 = sobre_mesa(u - 0.03, 0)
        bx1, by1 = sobre_mesa(u + 0.03, 0)
        fx1, fy1 = sobre_mesa(u + 0.035, 1)
        fx0, fy0 = sobre_mesa(u - 0.035, 1)
        ctx.move_to(bx0, by0)
        ctx.line_to(bx1, by1)
        ctx.line_to(fx1, fy1)
        ctx.line_to(fx0, fy0)
        ctx.close_path()
        ctx.set_source_rgb(*CUERO)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5)
        ctx.stroke()
        cx = (fx0 + fx1) / 2
        w = fx1 - fx0
        cuelga = 120 - 34 * apriete
        rrect(ctx, cx - w / 2, MF_Y, w, MFACE + cuelga, 6)
        ctx.set_source_rgb(*CUERO)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.stroke()
        hy = MF_Y + MFACE + cuelga * 0.35
        rrect(ctx, cx - w / 2 - 8, hy - 18, w + 16, 36, 6)
        ctx.set_source_rgb(*BRONCE)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5)
        ctx.stroke()
        ctx.move_to(cx, hy - 14)
        ctx.line_to(cx, hy + 14)
        ctx.stroke()


def sierra(ctx, x, y, s, rot=0.0, aplasta=0.55, a=1.0):
    """Sierra de amputación: hoja de acero con dientes y mango de madera."""
    if s <= 0.01 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s, s * aplasta)
    ctx.push_group()
    ctx.move_to(-230, -30)                        # hoja
    ctx.line_to(130, -38)
    ctx.line_to(130, 40)
    n = 26
    for k in range(n + 1):
        xx = lerp(130, -230, k / n)
        yy = lerp(40, 22, k / n) + (12 if k % 2 else 0)
        ctx.line_to(xx, yy)
    ctx.close_path()
    ctx.set_source_rgb(*ACERO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.move_to(-210, -14)
    ctx.line_to(110, -20)
    ctx.set_source_rgba(*BLANCO, 0.6)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.move_to(120, -60)                         # mango
    ctx.curve_to(200, -70, 250, -40, 255, 10)
    ctx.curve_to(260, 60, 230, 90, 190, 80)
    ctx.curve_to(160, 72, 130, 60, 120, 50)
    ctx.close_path()
    ctx.set_source_rgb(*MADERA_CLARA)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.save()
    ctx.translate(195, 12)
    ctx.scale(28, 22)
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()
    ctx.set_source_rgb(*SOMBRA)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()
    for yy in (-30, 40):                          # remaches
        ctx.arc(150, yy, 7, 0, TAU)
        ctx.set_source_rgb(*BRONCE)
        ctx.fill()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


SIERRA0 = (560, 990, -0.06)


def botella(ctx, x, y, s, a=1.0):
    """Botella de licor parada (y = la base)."""
    if s <= 0.01 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.push_group()
    ctx.move_to(-62, 0)
    ctx.line_to(-62, -170)
    ctx.curve_to(-62, -210, -22, -220, -20, -250)
    ctx.line_to(-20, -300)
    ctx.line_to(20, -300)
    ctx.line_to(20, -250)
    ctx.curve_to(22, -220, 62, -210, 62, -170)
    ctx.line_to(62, 0)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#8A5A1E"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    rrect(ctx, -22, -330, 44, 36, 6)              # corcho
    ctx.set_source_rgb(*hx("#C9A27A"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    rrect(ctx, -50, -140, 100, 80, 8)             # etiqueta
    ctx.set_source_rgb(*CREMA)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()
    ctx.move_to(-46, -150)
    ctx.line_to(-46, -40)
    ctx.set_source_rgba(*BLANCO, 0.4)
    ctx.set_line_width(9)
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def frasco(ctx, x, y, s, a=1.0):
    """Frasco chico de vidrio oscuro, como el del láudano (opio)."""
    if s <= 0.01 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.push_group()
    rrect(ctx, -45, -120, 90, 120, 14)
    ctx.set_source_rgb(*hx("#4A2E1A"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.rectangle(-18, -150, 36, 32)
    ctx.set_source_rgb(*hx("#4A2E1A"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    rrect(ctx, -22, -172, 44, 26, 5)
    ctx.set_source_rgb(*hx("#C9A27A"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    rrect(ctx, -34, -86, 68, 48, 6)
    ctx.set_source_rgb(*CREMA)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def mano(ctx, x, y, s, ang, a=1.0):
    """Silueta de una mano que aprieta hacia abajo, con el brazo saliendo de arriba. Sin detalles: es una sombra."""
    if s <= 0.01 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.scale(s, s)
    ctx.push_group()
    g = cairo.LinearGradient(0, -60, 0, -560)     # el brazo se pierde en la oscuridad
    g.add_color_stop_rgba(0, *SOMBRA, 1)
    g.add_color_stop_rgba(1, *SOMBRA, 0)
    ctx.rectangle(-56, -600, 112, 560)
    ctx.set_source(g)
    ctx.fill()
    rrect(ctx, -66, -90, 132, 112, 44)            # palma
    ctx.set_source_rgb(*SOMBRA)
    ctx.fill()
    for fx, ln in ((-46, 76), (-16, 88), (15, 84), (44, 70)):   # dedos
        capsula(ctx, fx, 10, fx, 10 + ln, 27)
        ctx.set_source_rgb(*SOMBRA)
        ctx.stroke()
    capsula(ctx, -58, -30, -96, 34, 30)           # pulgar
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(0.95 * a)
    ctx.restore()


# ------------------------------------------------------------------ el ojo y la línea del dolor
def ojo(ctx, x, y, w, ab=1.0, mira=(0.0, 0.0), a=1.0):
    """Ojo dibujado de frente. ab = cuánto está abierto (0 cerrado, 1 abierto).
    Cerrado se dibuja como una curva clara con pestañas, para que se lea sobre el fondo oscuro."""
    if a <= 0.01 or w <= 1:
        return
    h = 0.42 * w
    k_abierto = clamp((ab - 0.08) / 0.3)          # cuánto del ojo abierto se ve
    ctx.save()
    ctx.translate(x, y)
    if k_abierto > 0.01:
        ctx.push_group()

        def almendra():
            ctx.new_path()
            ctx.move_to(-w / 2, 0)
            ctx.curve_to(-w / 4, -h, w / 4, -h, w / 2, 0)
            ctx.curve_to(w / 4, 0.85 * h, -w / 4, 0.85 * h, -w / 2, 0)
            ctx.close_path()

        almendra()
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()
        ctx.save()
        almendra()
        ctx.clip()
        ix, iy = mira[0] * 0.14 * w, mira[1] * 0.08 * w
        ctx.arc(ix, iy, 0.23 * w, 0, TAU)
        ctx.set_source_rgb(*hx("#6B4A2E"))
        ctx.fill()
        ctx.arc(ix, iy, 0.11 * w, 0, TAU)
        ctx.set_source_rgb(*INK)
        ctx.fill()
        ctx.arc(ix - 0.07 * w, iy - 0.07 * w, 0.04 * w, 0, TAU)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()
        borde = lerp(0.8 * h, -h, ab)             # el párpado baja hasta este y
        ctx.rectangle(-w, -2 * h, 2 * w, borde + 2 * h)
        ctx.set_source_rgb(*PIEL)
        ctx.fill()
        ctx.restore()
        if ab < 0.98:
            yc = lerp(0.85 * h, -h, ab)
            ctx.move_to(-w / 2, 0)
            ctx.curve_to(-w / 4, yc, w / 4, yc, w / 2, 0)
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(max(3, w * 0.03))
            ctx.stroke()
        almendra()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(max(3, w * 0.035))
        ctx.stroke()
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a * k_abierto)
    if k_abierto < 0.99:                          # ojo cerrado
        ac = a * (1 - k_abierto)
        ctx.move_to(-w / 2, -0.05 * h)
        ctx.curve_to(-w / 4, 0.6 * h, w / 4, 0.6 * h, w / 2, -0.05 * h)
        for lw, col in ((max(6, w * 0.06), INK), (max(3, w * 0.03), BLANCO)):
            ctx.set_source_rgba(*col, ac)
            ctx.set_line_width(lw)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke_preserve()
        ctx.new_path()
        for k in range(6):
            u = (k + 1) / 7
            px = lerp(-w / 2, w / 2, u)
            py = 0.43 * h * 4 * u * (1 - u) * 0.75 + 0.1 * h * (1 - 4 * u * (1 - u))
            ctx.move_to(px, py)
            ctx.line_to(px + (u - 0.5) * 0.12 * w, py + 0.12 * w)
            ctx.set_source_rgba(*BLANCO, ac)
            ctx.set_line_width(max(2, w * 0.022))
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
    ctx.restore()


_r = rng(21)
PICOS = [float(v) for v in _r.uniform(0.3, 1.0, 400)]


def linea_dolor(ctx, x0, x1, y, t, amp, avance=1.0, col=ROJO, w=9, a=1.0):
    """Línea tipo monitor: con dolor salta en picos, sin dolor queda plana."""
    if a <= 0.01 or avance <= 0.01:
        return
    xe = lerp(x0, x1, avance)
    ctx.new_path()
    ctx.move_to(x0, y)
    paso = 16
    k = 0
    xx = x0
    while xx < xe:
        xx = min(xe, xx + paso)
        k += 1
        pico = PICOS[(k + int(t * 22)) % len(PICOS)]
        sgn = 1 if k % 2 else -1
        ctx.line_to(xx, y + sgn * amp * pico)
    for lw, c, al in ((w + 10, INK, 0.8 * a), (w, col, a)):
        ctx.set_source_rgba(*c, al)
        ctx.set_line_width(lw)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke_preserve()
    ctx.new_path()
    _elipse_suave(ctx, xe, y, 40, 40, col, 0.5 * a)


def pulso_rojo(ctx, k):
    if k > 0.005:
        ctx.set_source_rgba(0.85, 0.08, 0.12, 0.2 * k)
        ctx.paint()


# ------------------------------------------------------------------ reloj de bolsillo
def reloj(ctx, x, y, R, t, seg=None, arco=False, limite=False, a=1.0, cadena=True):
    """Reloj de bolsillo. seg = segundos que marca la aguja roja; arco = sombrea lo recorrido."""
    if R <= 1 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.push_group()
    if cadena:
        for k in range(9):
            cx, cy = 0.15 * R * math.sin(k * 0.5), -1.22 * R - k * 0.16 * R
            ctx.save()
            ctx.translate(cx, cy)
            ctx.rotate(0.6 if k % 2 else -0.6)
            ctx.scale(0.07 * R, 0.045 * R)
            ctx.arc(0, 0, 1, 0, TAU)
            ctx.restore()
            ctx.set_source_rgb(*BRONCE)
            ctx.set_line_width(max(2, 0.025 * R))
            ctx.stroke()
    ctx.arc(0, -1.12 * R, 0.13 * R, 0, TAU)       # argolla
    ctx.set_source_rgb(*BRONCE)
    ctx.set_line_width(max(3, 0.05 * R))
    ctx.stroke()
    rrect(ctx, -0.09 * R, -1.08 * R, 0.18 * R, 0.14 * R, 0.03 * R)   # corona
    ctx.set_source_rgb(*BRONCE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(2, 0.03 * R))
    ctx.stroke()
    ctx.arc(0, 0, R, 0, TAU)                      # caja
    ctx.set_source_rgb(*hx("#D9B44A"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(3, 0.06 * R))
    ctx.stroke()
    ctx.arc(0, 0, 0.86 * R, 0, TAU)               # esfera
    ctx.set_source_rgb(*CREMA)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(2, 0.025 * R))
    ctx.stroke()
    if arco and seg is not None and seg > 0:
        ctx.move_to(0, 0)
        ctx.arc(0, 0, 0.8 * R, -math.pi / 2, -math.pi / 2 + TAU * seg / 60)
        ctx.close_path()
        ctx.set_source_rgba(*ROJO, 0.28)
        ctx.fill()
    for i in range(60):
        an = TAU * i / 60 - math.pi / 2
        r0 = 0.72 * R if i % 5 == 0 else 0.77 * R
        ctx.move_to(r0 * math.cos(an), r0 * math.sin(an))
        ctx.line_to(0.82 * R * math.cos(an), 0.82 * R * math.sin(an))
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(max(1.5, (0.03 if i % 5 == 0 else 0.012) * R))
        ctx.stroke()
    if limite:                                    # la marca de los 30 segundos
        ctx.move_to(0, 0.6 * R)
        ctx.line_to(0, 0.84 * R)
        ctx.set_source_rgb(*ROJO)
        ctx.set_line_width(max(3, 0.06 * R))
        ctx.stroke()
    for L, wd, an in ((0.45, 0.05, math.radians(-60)), (0.62, 0.035, math.radians(60))):   # horas y minutos quietos
        ctx.move_to(0, 0)
        ctx.line_to(L * R * math.cos(an - math.pi / 2), L * R * math.sin(an - math.pi / 2))
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(max(2, wd * R))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    s = seg if seg is not None else t
    an = TAU * s / 60 - math.pi / 2
    ctx.move_to(-0.12 * R * math.cos(an), -0.12 * R * math.sin(an))
    ctx.line_to(0.78 * R * math.cos(an), 0.78 * R * math.sin(an))
    ctx.set_source_rgb(*ROJO)
    ctx.set_line_width(max(2, 0.025 * R))
    ctx.stroke()
    ctx.arc(0, 0, 0.05 * R, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


# ------------------------------------------------------------------ 1. la mesa (b0 a b5): despierto, sin anestesia, cada corte
T_200 = b(0, "200")
T_DESP = b(0, "despierto")
T_NADA = b(1, "nada")
T_CORTE = b(2, "corte")
T_FIN2 = b(2, "fin")
T_ALC = b(3, "alcohol")
T_OPIO = b(3, "opio")
T_NOALC = b(4)
T_SUJ = b(5, "sujetaban")
T_MESA = b(5, "mesa")
POPS += [T_200 - 0.1, T_NADA - 0.1, T_CORTE - 0.1, T_ALC - 0.1, T_OPIO - 0.1, T_NOALC, T_SUJ - 0.1]
MANOS = [((300, 975), -0.5, b(5, "varios") - 0.05), ((780, 975), 0.5, b(5, "ayudantes") - 0.1),
         ((450, 1000), -0.22, b(5, "ayudantes") + 0.15), ((640, 1000), 0.24, b(5, "te") + 0.05)]


def vista_mesa(ctx, t, sierra_dx=0.0, apriete=0.0):
    fondo(ctx, t, 0.35)
    luz_cenital(ctx, 540)
    mesa(ctx, apriete)
    x, y, r = SIERRA0
    sierra(ctx, x + sierra_dx, y, 1.0, r)


def golpes_sierra(t):
    """Movimiento de la sierra mientras se dice 'cada corte, de principio a fin'."""
    if t < T_CORTE - 0.1 or t > b(3) - 0.1:
        return 0.0, 0.0
    f = 2.4
    fase = (t - (T_CORTE - 0.1)) * f
    dx = 55 * math.sin(TAU * fase)
    golpe = abs(math.cos(TAU * fase)) ** 8          # picos en cada cambio de dirección
    return dx * sale(t, b(3) - 0.35, 0.25), golpe


def d_mesa(ctx, t):
    dx, golpe = golpes_sierra(t)
    apr = prog(t, T_SUJ - 0.2, 0.5, "out")
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, 0, b(6)), 540, 950)
    vista_mesa(ctx, t, sierra_dx=dx, apriete=apr)
    # alcohol y opio sobre la mesa
    if t >= T_ALC - 0.25:
        caida = 1 - ease(clamp((t - (T_ALC - 0.25)) / 0.35), "in")
        botella(ctx, 300, 980 - 500 * caida, 0.85)
    if t >= T_OPIO - 0.25:
        caida = 1 - ease(clamp((t - (T_OPIO - 0.25)) / 0.35), "in")
        frasco(ctx, 420, 1000 - 500 * caida, 0.95)
    # manos que sujetan
    for (mx, my), ang, t0 in MANOS:
        if t >= t0:
            p = ease(clamp((t - t0) / 0.35), "out")
            aprieta = 6 * math.sin((t - t0) * 9) * clamp((t - t0 - 0.35) / 0.2)
            mano(ctx, mx + 420 * math.sin(ang) * (1 - p), my - 420 * math.cos(ang) * (1 - p) + aprieta, 1.0, ang,
                 a=p)
    ctx.restore()
    # el ojo despierto y la línea del dolor
    if T_DESP - 0.15 <= t < b(3) - 0.1:
        ab = ease(clamp((t - (T_DESP - 0.15)) / 0.35), "out")
        ojo(ctx, 540, 600, 330, ab=ab, mira=(0.3 * math.sin(t * 1.3), 0.2), a=sale(t, b(3) - 0.3, 0.2))
    if t >= T_CORTE - 0.15 and t < b(3) - 0.05:
        av = prog(t, T_CORTE - 0.15, T_FIN2 + 0.3 - (T_CORTE - 0.15))
        linea_dolor(ctx, 60, 1020, 820, t, 20 + 70 * golpe, avance=av, a=sale(t, b(3) - 0.25, 0.2))
        pulso_rojo(ctx, golpe * sale(t, b(3) - 0.3))
    if t >= T_NOALC:
        cruz(ctx, 360, 860, 120, pop(t, T_NOALC, 0.25) * sale(t, b(5) + 0.1, 0.25))
    # carteles
    kartel(ctx, "HACE MENOS DE 200 AÑOS", 540, 300, 64, t, T_200 - 0.1, b(1) - 0.15, box=BLANCO, rot=-2)
    if t >= T_NADA - 0.1 and t < b(2) + 0.5:
        s = pop(t, T_NADA - 0.1) * sale(t, b(2) + 0.25)
        cartel(ctx, "ANESTESIA", 540, 300, 96, box=BLANCO, s=s, rot=-3)
        tachado(ctx, 540, 300, 520 * s, prog(t, T_NADA + 0.25, 0.3, "out"), ang=-10, grosor=24)
    kartel(ctx, "CADA CORTE", 540, 300, 96, t, T_CORTE - 0.1, b(3) - 0.15, box=ROJO, fg=BLANCO, rot=-3)
    kartel(ctx, "ALCOHOL", 250, 590, 54, t, T_ALC - 0.1, T_NOALC + 0.3, box=BLANCO, rot=-4)
    kartel(ctx, "OPIO", 470, 700, 54, t, T_OPIO - 0.1, T_NOALC + 0.3, box=BLANCO, rot=4)
    kartel(ctx, "NO ALCANZABA", 540, 300, 90, t, T_NOALC, b(5) + 0.3, box=ROJO, fg=BLANCO, rot=-3)
    kartel(ctx, "TE SUJETABAN", 540, 300, 96, t, T_SUJ - 0.1, b(6) - 0.15, rot=-2)


def d_cierre(ctx, t):
    ctx.save()
    zoom(ctx, 1 + 0.04 * (1 - prog(t, b(22), TOTAL - b(22))), 540, 950)
    vista_mesa(ctx, t)
    ctx.restore()


# ------------------------------------------------------------------ 2. la balanza: cuidado o velocidad
T_CUID = b(6, "cuidado")
T_VELOC = b(7, "velocidad")
T_SUFR = b(8, "menos", n=1)
POPS += [T_CUID - 0.1, T_VELOC - 0.1, T_SUFR - 0.1]


def aguja(ctx, x, y, s):
    """Aguja con hilo: el cuidado."""
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(-70, 40)
    ctx.line_to(70, -40)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(14)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.move_to(-70, 40)
    ctx.line_to(70, -40)
    ctx.set_source_rgb(*ACERO)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.move_to(62, -36)
    ctx.curve_to(110, -80, 60, -120, 20, -80)
    ctx.curve_to(-20, -40, -60, -90, -100, -60)
    ctx.set_source_rgb(*ROJO)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.restore()


def balanza(ctx, x, y, s, inc, t, izq=None, der=None):
    """Balanza de dos platos. inc > 0 baja el plato derecho."""
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(-150, 520)                        # base y columna
    ctx.line_to(150, 520)
    ctx.line_to(90, 470)
    ctx.line_to(-90, 470)
    ctx.close_path()
    ctx.set_source_rgb(*BRONCE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.rectangle(-16, 0, 32, 475)
    ctx.set_source_rgb(*BRONCE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    L = 300
    ex, ey = L * math.cos(inc), L * math.sin(inc)
    for lw, col in ((26, INK), (14, BRONCE)):     # cruz de la balanza
        ctx.move_to(-ex, -ey)
        ctx.line_to(ex, ey)
        ctx.set_line_width(lw)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgb(*col)
        ctx.stroke()
    ctx.arc(0, 0, 22, 0, TAU)
    ctx.set_source_rgb(*BRONCE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    for sg, fn in ((-1, izq), (1, der)):
        px, py = sg * ex, sg * ey
        bajo = py + 230
        for dx in (-95, 0, 95):
            ctx.move_to(px, py)
            ctx.line_to(px + dx, bajo)
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(4)
            ctx.stroke()
        ctx.move_to(px - 120, bajo)
        ctx.curve_to(px - 100, bajo + 50, px + 100, bajo + 50, px + 120, bajo)
        ctx.close_path()
        ctx.set_source_rgb(*BRONCE)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(7)
        ctx.stroke()
        if fn:
            fn(px, bajo)
    ctx.restore()


def barra(ctx, x, y, w, h, p, col, etiqueta):
    rrect(ctx, x, y, w, h, h / 2)
    ctx.set_source_rgba(*BLANCO, 0.15)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    if p > 0.01:
        rrect(ctx, x + 6, y + 6, max(h - 12, (w - 12) * p), h - 12, (h - 12) / 2)
        ctx.set_source_rgb(*col)
        ctx.fill()
    texto(ctx, etiqueta, x + w / 2, y - 42, 50, fill=BLANCO, sw=7)


def d_balanza(ctx, t):
    fondo(ctx, t, 0.35)
    luz_cenital(ctx, 540, 0.6)
    sube = prog(t, b(8) - 0.15, 0.5, "inout")
    inc = lerp(-0.18, 0.32, ease(prog(t, T_VELOC - 0.05, 0.5), "out")) + 0.02 * math.sin(t * 3)
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(6), b(9) - b(6)), 540, 900)

    def izq(px, py):
        aguja(ctx, px, py - 40, 0.75)

    def der(px, py):
        if t >= T_VELOC - 0.25:
            reloj(ctx, px, py - 80 + 30 * (1 - pop(t, T_VELOC - 0.25, 0.3)), 62, t * 6, cadena=False,
                  a=prog(t, T_VELOC - 0.25, 0.15))

    balanza(ctx, 540, lerp(640, 470, sube), lerp(1.0, 0.72, sube) * pop(t, b(6) - 0.05, 0.4), inc, t, izq, der)
    ctx.restore()
    if sube < 0.5:
        kartel(ctx, "CUIDADO", 300, 1090, 60, t, T_CUID - 0.1, b(8) - 0.1, box=BLANCO, rot=-3)
        kartel(ctx, "VELOCIDAD", 790, 1180, 64, t, T_VELOC - 0.1, b(8) - 0.1, rot=3)
    if t >= b(8) - 0.05:                          # menos tiempo, menos dolor
        p = 1 - 0.75 * ease(prog(t, b(8, "duraba"), T_SUFR + 0.3 - b(8, "duraba")), "inout")
        a = prog(t, b(8) - 0.05, 0.3)
        ctx.save()
        ctx.push_group()
        barra(ctx, 170, 1010, 740, 70, p, AMARILLO, "TIEMPO")
        barra(ctx, 170, 1180, 740, 70, p, ROJO, "DOLOR")
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)
        ctx.restore()
    kartel(ctx, "MENOS TIEMPO, MENOS DOLOR", 540, 300, 64, t, T_SUFR - 0.1, b(9) - 0.15, rot=-2)


# ------------------------------------------------------------------ 3. menos de 30 segundos
T_AMP = b(9, "amputaban")
T_30 = b(9, "30")
T_SEG9 = b(9, "segundos")
POPS += [T_30 - 0.1]


def d_reloj30(ctx, t):
    fondo(ctx, t, 0.35)
    luz_cenital(ctx, 540, 0.5)
    seg = 28 * ease(prog(t, T_AMP, T_SEG9 + 0.1 - T_AMP), "inout")
    ctx.save()
    zoom(ctx, 1 + 0.05 * prog(t, b(9), b(10) - b(9)), 540, 760)
    reloj(ctx, 540, 760, 300 * pop(t, b(9) - 0.05, 0.4), t, seg=seg, arco=True, limite=True)
    dx = 70 * math.sin(TAU * 3.2 * (t - T_AMP)) if T_AMP <= t < T_SEG9 + 0.2 else 0
    sierra(ctx, 540 + dx, 1290, 0.8 * pop(t, b(9) + 0.1, 0.4), -0.04, aplasta=1.0)
    ctx.restore()
    if seg >= 1:
        texto(ctx, f"{int(seg)} s", 540, 1135, 96, fill=ROJO, sw=10)
    kartel(ctx, "MENOS DE 30 SEGUNDOS", 540, 300, 72, t, T_30 - 0.1, box=ROJO, fg=BLANCO, rot=-2)


# ------------------------------------------------------------------ 4. las gradas: estudiantes con el reloj en la mano
T_EST = b(10, "estudiantes")
T_RELOJ10 = b(10, "reloj")
POPS += [T_RELOJ10 - 0.1]
FILAS = 5


def fila_y(k, x):
    return 1080 - 165 * k - 0.00028 * (1 + 0.25 * k) * (x - 540) ** 2


_r = rng(31)
RELOJITOS = [(k, float(x0) + float(_r.uniform(-20, 20)), float(_r.uniform(0, TAU)))
             for k in range(FILAS) for x0 in np.linspace(70, 1010, 8 + k)]


def d_gradas(ctx, t):
    fondo(ctx, t, 0.45)
    ctx.save()
    zoom(ctx, lerp(1.12, 1.0, prog(t, b(10) - 0.1, 1.2, "out")), 540, 1150)
    for k in range(FILAS - 1, -1, -1):            # de atrás para adelante
        ys = [(x, fila_y(k, x)) for x in range(-40, 1121, 40)]
        ctx.move_to(-40, ys[0][1] + 120)
        for x, y in ys:
            ctx.line_to(x, y + 120)
        for x, y in reversed(ys):
            ctx.line_to(x, y)
        ctx.close_path()
        ctx.set_source_rgb(*mezcla(MADERA_OSC, hx("#2A1C12"), k / FILAS))
        ctx.fill()
        for x in range(-20, 1121, 70):            # barrotes
            y = fila_y(k, x)
            ctx.move_to(x, y)
            ctx.line_to(x, y + 120)
            ctx.set_source_rgba(*INK, 0.6)
            ctx.set_line_width(6)
            ctx.stroke()
        ctx.move_to(*ys[0])
        for x, y in ys[1:]:
            ctx.line_to(x, y)
        for lw, col in ((18, INK), (9, MADERA_CLARA)):
            ctx.set_source_rgb(*col)
            ctx.set_line_width(lw)
            ctx.stroke_preserve()
        ctx.new_path()
    # relojes colgando de la baranda, uno por estudiante
    for i, (k, x, ph) in enumerate(RELOJITOS):
        t0 = T_RELOJ10 - 0.35 + 0.025 * i
        if t < t0:
            continue
        y = fila_y(k, x)
        baja = ease(clamp((t - t0) / 0.3), "out")
        sw = 0.18 * math.sin(t * 2.2 + ph)
        L = 70 * baja
        rx, ry = x + L * math.sin(sw), y + L * math.cos(sw)
        ctx.move_to(x, y)
        ctx.line_to(rx, ry)
        ctx.set_source_rgb(*BRONCE)
        ctx.set_line_width(3)
        ctx.stroke()
        reloj(ctx, rx, ry + 26, 24 - 2 * k, t * 6 + ph, cadena=False)
    # la mesa abajo, chiquita, bajo la luz
    ctx.save()
    ctx.translate(540, 1300)
    ctx.scale(0.42, 0.42)
    ctx.translate(-540, -1000)
    luz_cenital(ctx, 540, 1.0)
    mesa(ctx)
    sierra(ctx, *SIERRA0[:2], 1.0, SIERRA0[2])
    ctx.restore()
    ctx.restore()
    kartel(ctx, "ESTUDIANTES", 540, 300, 72, t, T_EST - 0.1, T_RELOJ10 - 0.2, box=BLANCO, rot=-2)
    kartel(ctx, "CON EL RELOJ EN LA MANO", 540, 300, 64, t, T_RELOJ10 - 0.1, rot=-2)


# ------------------------------------------------------------------ 5. solo para salvar una vida
T_DOLOR11 = b(11, "dolor")
T_VIDA = b(11, "salvar")
POPS += [T_VIDA - 0.1]


def corazon(ctx, x, y, s, a=1.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(0, 110)
    ctx.curve_to(-60, 60, -160, 0, -160, -70)
    ctx.curve_to(-160, -140, -70, -170, 0, -100)
    ctx.curve_to(70, -170, 160, -140, 160, -70)
    ctx.curve_to(160, 0, 60, 60, 0, 110)
    ctx.close_path()
    ctx.set_source_rgba(*ROJO, a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(12)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.move_to(-100, -90)
    ctx.curve_to(-110, -120, -80, -135, -55, -125)
    ctx.set_source_rgba(*BLANCO, 0.6 * a)
    ctx.set_line_width(12)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.restore()


def latido(t):
    f = (t * 1.25) % 1.0
    return 1 + 0.12 * math.exp(-((f - 0.05) / 0.05) ** 2) + 0.07 * math.exp(-((f - 0.22) / 0.05) ** 2)


def d_vida(ctx, t):
    fondo(ctx, t, 0.4)
    amp = 80 * prog(t, T_DOLOR11 - 0.2, 0.3) * sale(t, T_VIDA - 0.1, 0.5) + 14
    linea_dolor(ctx, 40, 1040, 1180, t, amp, avance=prog(t, b(11) - 0.05, 1.0), a=1.0)
    corazon(ctx, 540, 720, 1.25 * pop(t, b(11), 0.4) * latido(t))
    kartel(ctx, "TANTO DOLOR", 540, 300, 84, t, T_DOLOR11 - 0.15, T_VIDA - 0.25, box=ROJO, fg=BLANCO, rot=-3)
    kartel(ctx, "SOLO PARA SALVAR UNA VIDA", 540, 300, 62, t, T_VIDA - 0.1, rot=-2)


# ------------------------------------------------------------------ 6. 1846
T_CAMBIO = b(12, "cambio")
T_1846 = b(12, "1846")
POPS += [T_CAMBIO - 0.1]


def hoja_calendario(ctx, x, y, s, anio, voltea=0.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s * (1 - 0.85 * voltea))
    w, h = 620, 520
    rrect(ctx, -w / 2 + 12, -h / 2 + 16, w, h, 26)
    ctx.set_source_rgba(0, 0, 0, 0.45)
    ctx.fill()
    rrect(ctx, -w / 2, -h / 2, w, h, 26)
    ctx.set_source_rgb(*CREMA)
    ctx.fill()
    ctx.save()
    rrect(ctx, -w / 2, -h / 2, w, h, 26)
    ctx.clip()
    ctx.rectangle(-w / 2, -h / 2, w, 120)
    ctx.set_source_rgb(*hx("#8E2A2A"))
    ctx.fill()
    ctx.restore()
    rrect(ctx, -w / 2, -h / 2, w, h, 26)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(10)
    ctx.stroke()
    texto(ctx, str(anio), 0, 60, 230, fill=INK, stroke=None)
    for sx in (-1, 1):
        rrect(ctx, sx * 160 - 14, -h / 2 - 30, 28, 64, 14)
        ctx.set_source_rgb(*hx("#AEB6C8"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(7)
        ctx.stroke()
    ctx.restore()


def d_1846(ctx, t):
    fondo(ctx, t, 0.4)
    p = ease(prog(t, b(12) + 0.05, T_1846 + 0.1 - b(12)), "out")
    anio = int(round(lerp(1800, 1846, p)))
    voltea = 0.0 if p >= 1 else ((t * 9) % 1.0) * 0.6
    llega = bump(t, T_1846 + 0.1, 0.35, 0.12)
    ctx.save()
    zoom(ctx, 1 + 0.06 * prog(t, b(12), b(13) - b(12)), 540, 880)
    hoja_calendario(ctx, 540, 880, pop(t, b(12) - 0.05, 0.4) * llega, anio, voltea)
    ctx.restore()
    if t >= T_1846 + 0.1:
        q = clamp((t - T_1846 - 0.1) / 0.8)
        ctx.arc(540, 880, 340 + 260 * ease(q, "out"), 0, TAU)
        ctx.set_source_rgba(*LUZ, 0.6 * (1 - q))
        ctx.set_line_width(12)
        ctx.stroke()
    kartel(ctx, "TODO CAMBIÓ", 540, 330, 100, t, T_CAMBIO - 0.1, rot=-3)


# ------------------------------------------------------------------ 7. Boston: el éter
T_BOSTON = b(13, "Boston")
T_RESP = b(13, "respiro")
T_ETER = b(13, "eter")
T_DORM = b(14, "dormido")
T_BULTO = b(14, "bulto")
T_NADA15 = b(15, "sintio")
POPS += [T_BOSTON - 0.1, T_ETER - 0.1, T_BULTO - 0.1, T_NADA15 - 0.1]


def inhalador(ctx, x, y, s, t, vapor=1.0):
    """Inhalador de éter de 1846: globo de vidrio con una esponja adentro y una boquilla."""
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for x0, x1, yy, hh in ((120, 270, -10, 56),):  # cuello hacia la boquilla
        rrect(ctx, x0, yy - hh / 2, x1 - x0, hh, 18)
        ctx.set_source_rgba(*VIDRIO, 0.25)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(8)
        ctx.stroke()
    ctx.move_to(260, -36)                         # boquilla
    ctx.line_to(350, -26)
    ctx.line_to(350, 6)
    ctx.line_to(260, 16)
    ctx.close_path()
    ctx.set_source_rgb(*MADERA_CLARA)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.save()                                    # cuello de arriba, para que entre aire
    ctx.rotate(math.radians(-40))
    rrect(ctx, -30, -230, 60, 110, 16)
    ctx.set_source_rgba(*VIDRIO, 0.25)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    rrect(ctx, -38, -250, 76, 30, 8)
    ctx.set_source_rgb(*BRONCE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.restore()
    ctx.arc(0, 0, 150, 0, TAU)                    # globo
    ctx.set_source_rgba(*VIDRIO, 0.18)
    ctx.fill()
    ctx.save()
    ctx.arc(0, 0, 150, 0, TAU)
    ctx.clip()
    ctx.rectangle(-160, 70, 320, 100)
    ctx.set_source_rgba(*hx("#F3EFC0"), 0.55)
    ctx.fill()
    rrect(ctx, -70, 40, 140, 70, 26)              # esponja
    ctx.set_source_rgb(*hx("#E9C25A"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    for hx_, hy, hr in ((-40, 62, 8), (-5, 78, 6), (30, 60, 9), (50, 88, 6), (-30, 92, 5)):
        ctx.arc(hx_, hy, hr, 0, TAU)
        ctx.set_source_rgb(*hx("#B98F2E"))
        ctx.fill()
    for i in range(5):                            # vapor adentro
        q = (t * 0.35 + i / 5) % 1.0
        ctx.arc(-60 + 30 * i + 12 * math.sin(t + i), lerp(40, -110, q), 26 + 16 * q, 0, TAU)
        ctx.set_source_rgba(*BLANCO, 0.22 * (1 - q) * vapor)
        ctx.fill()
    ctx.restore()
    ctx.arc(0, 0, 150, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    ctx.arc(0, 0, 118, math.radians(200), math.radians(250))
    ctx.set_source_rgba(*BLANCO, 0.6)
    ctx.set_line_width(12)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    for i in range(4):                            # vapor que sale por la boquilla
        q = (t * 0.5 + i / 4) % 1.0
        xx, yy = 350 + 200 * q, -10 - 160 * q + 30 * math.sin(q * 6 + i)
        ctx.arc(xx, yy, 18 + 40 * q, 0, TAU)
        ctx.set_source_rgba(*BLANCO, 0.3 * (1 - q) * vapor)
        ctx.fill()
    ctx.restore()


def d_eter(ctx, t):
    fondo(ctx, t, 0.4)
    luz_cenital(ctx, 540, 0.5)
    ctx.save()
    zoom(ctx, 1 + 0.05 * prog(t, b(13), b(16) - b(13)), 540, 900)
    inhalador(ctx, 420, 1010, 1.0 * pop(t, b(13) - 0.05, 0.4), t, vapor=prog(t, T_RESP - 0.2, 0.6))
    ab = 1 - ease(prog(t, T_DORM - 0.1, 0.6), "inout")
    ojo(ctx, 600, 560, 300 * pop(t, T_RESP - 0.1, 0.35), ab=ab, mira=(0.4, 0.6))
    ctx.restore()
    if t >= b(15) - 0.2:
        linea_dolor(ctx, 60, 1020, 1300, t, 0.0, avance=prog(t, b(15) - 0.2, 0.6), col=BLANCO)
    kartel(ctx, "BOSTON, 1846", 540, 300, 66, t, T_BOSTON - 0.1, T_ETER - 0.2, box=BLANCO, rot=-2)
    kartel(ctx, "ÉTER", 540, 300, 110, t, T_ETER - 0.1, b(14) + 0.6, rot=-3)
    kartel(ctx, "BULTO EN LA MANDÍBULA", 540, 300, 62, t, T_BULTO - 0.1, b(15) - 0.15, box=BLANCO, rot=-2)
    kartel(ctx, "NO SINTIÓ NADA", 540, 300, 90, t, T_NADA15 - 0.1, box=VERDE, rot=-3)


# ------------------------------------------------------------------ 8. la noticia cruza el océano
T_MESES = b(16, "meses")
T_LOND = b(16, "Londres")
POPS += [T_MESES - 0.1, b(16) + 0.1, T_LOND - 0.1]
BOS, LON = (170, 980), (910, 820)


def pin(ctx, x, y, s, col):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(0, 0)
    ctx.curve_to(-60, -70, -54, -140, 0, -140)
    ctx.curve_to(54, -140, 60, -70, 0, 0)
    ctx.close_path()
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.arc(0, -92, 20, 0, TAU)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill()
    ctx.restore()


def barco(ctx, x, y, s, t):
    ctx.save()
    ctx.translate(x, y + 6 * math.sin(t * 3))
    ctx.rotate(0.05 * math.sin(t * 2.4))
    ctx.scale(s, s)
    ctx.move_to(-120, 0)
    ctx.line_to(120, 0)
    ctx.line_to(90, 50)
    ctx.line_to(-90, 50)
    ctx.close_path()
    ctx.set_source_rgb(*MADERA)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    for mx, hh in ((-45, 190), (45, 220)):
        ctx.move_to(mx, 0)
        ctx.line_to(mx, -hh)
        ctx.set_line_width(8)
        ctx.stroke()
        for k, (yy, ww) in enumerate(((-hh + 20, 70), (-hh + 95, 90))):
            ctx.move_to(mx - ww / 2, yy)
            ctx.line_to(mx + ww / 2, yy)
            ctx.curve_to(mx + ww / 2 + 10, yy + 35, mx + ww / 2 + 10, yy + 55, mx + ww / 2, yy + 65)
            ctx.line_to(mx - ww / 2, yy + 65)
            ctx.curve_to(mx - ww / 2 + 10, yy + 55, mx - ww / 2 + 10, yy + 35, mx - ww / 2, yy)
            ctx.close_path()
            ctx.set_source_rgb(*CREMA)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(6)
            ctx.stroke()
    ctx.restore()


def arco_pt(u):
    x = lerp(BOS[0], LON[0], u)
    y = lerp(BOS[1], LON[1], u) - 260 * math.sin(math.pi * u)
    return x, y


def d_oceano(ctx, t):
    fondo(ctx, t, 0.3)
    ctx.rectangle(0, 640, W, 900)
    ctx.set_source_rgba(*hx("#123B7A"), 0.55)
    ctx.fill()
    for row in range(6):                          # olas
        yy = 700 + row * 110
        for k in range(8):
            xx = (k * 160 + row * 70 + t * 30) % (W + 160) - 80
            ctx.move_to(xx, yy)
            ctx.curve_to(xx + 20, yy - 16, xx + 40, yy - 16, xx + 60, yy)
            ctx.set_source_rgba(*hx("#5B8BD9"), 0.6)
            ctx.set_line_width(5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
    u = ease(prog(t, b(16) + 0.15, T_LOND + 0.2 - (b(16) + 0.15)), "inout")
    ctx.set_dash([18, 14])
    ctx.move_to(*arco_pt(0))
    for k in range(1, 41):
        if k / 40 > u:
            break
        ctx.line_to(*arco_pt(k / 40))
    ctx.set_source_rgba(*BLANCO, 0.8)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.set_dash([])
    pin(ctx, *BOS, 1.0 * pop(t, b(16) + 0.05, 0.35), hx("#3D8BFF"))
    pin(ctx, *LON, 1.0 * pop(t, T_LOND - 0.15, 0.35), ROJO)
    bx, by = arco_pt(u)
    barco(ctx, bx, by + 40, 0.55, t)
    kartel(ctx, "DOS MESES DESPUÉS", 540, 300, 76, t, T_MESES - 0.1, rot=-2)
    kartel(ctx, "BOSTON", BOS[0] + 30, BOS[1] + 70, 46, t, b(16) + 0.1, box=BLANCO, rot=-3)
    kartel(ctx, "LONDRES", LON[0] - 30, LON[1] + 70, 46, t, T_LOND - 0.1, box=BLANCO, rot=3)


# ------------------------------------------------------------------ 9. el cirujano más rápido, ahora con éter
T_RAPIDO = b(17, "rapido")
T_DURM = b(18, "durmio")
T_AMPUTO = b(18, "amputo")
T_VELOZ = b(19, "veloz")
POPS += [T_RAPIDO - 0.15, T_VELOZ - 0.1]


def d_londres(ctx, t):
    fondo(ctx, t, 0.35)
    luz_cenital(ctx, 540, 0.5)
    seg = 25 * ease(prog(t, T_AMPUTO, T_VELOZ + 0.1 - T_AMPUTO), "inout")
    ctx.save()
    zoom(ctx, 1 + 0.05 * prog(t, b(17), b(20) - b(17)), 540, 760)
    reloj(ctx, 540, 720, 280 * pop(t, b(17) - 0.05, 0.4), t, seg=seg, arco=seg > 0, limite=True)
    dx = 70 * math.sin(TAU * 3.2 * (t - T_AMPUTO)) if T_AMPUTO <= t < T_VELOZ + 0.2 else 0
    sierra(ctx, 640 + dx, 1250, 0.75 * pop(t, b(17) + 0.2, 0.4), -0.04, aplasta=1.0)
    if t >= b(18) - 0.2:
        inhalador(ctx, 210, 1200, 0.5 * pop(t, b(18) - 0.2, 0.35), t)
        ab = 1 - ease(prog(t, T_DURM + 0.1, 0.5), "inout")
        ojo(ctx, 860, 1010, 180 * pop(t, b(18) - 0.05, 0.35), ab=ab, mira=(-0.5, 0.4))
    ctx.restore()
    if seg >= 1:
        texto(ctx, f"{int(seg)} s", 540, 1075, 90, fill=ROJO, sw=10)
    kartel(ctx, "EL MÁS RÁPIDO", 540, 300, 90, t, T_RAPIDO - 0.15, b(18) + 0.4, rot=-3)
    kartel(ctx, "CON ÉTER", 540, 300, 96, t, b(18, "eter") - 0.1, T_VELOZ - 0.25, box=BLANCO, rot=-2)
    kartel(ctx, "TAN VELOZ COMO SIEMPRE", 540, 300, 64, t, T_VELOZ - 0.1, rot=-2)


# ------------------------------------------------------------------ 10. despertó: ¿cuándo empieza?
T_DESPERTO = b(20, "desperto")
T_POCOS = b(20, "pocos")
T_CUANDO = b(21, "cuando")
POPS += [T_POCOS - 0.1, T_CUANDO - 0.1]


def globo(ctx, x, y, w, h, s, lineas):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    rrect(ctx, -w / 2, -h / 2, w, h, 40)
    ctx.move_to(-w * 0.2, h / 2 - 4)
    ctx.line_to(-w * 0.32, h / 2 + 90)
    ctx.line_to(-w * 0.05, h / 2 - 4)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill()
    rrect(ctx, -w / 2, -h / 2, w, h, 40)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(10)
    ctx.stroke()
    ctx.move_to(-w * 0.2, h / 2 + 2)
    ctx.line_to(-w * 0.32, h / 2 + 90)
    ctx.line_to(-w * 0.05, h / 2 + 2)
    ctx.stroke()
    for i, ln in enumerate(lineas):
        texto(ctx, ln, 0, (i - (len(lineas) - 1) / 2) * 92, 78, fill=INK, stroke=None)
    ctx.restore()


def d_desperto(ctx, t):
    fondo(ctx, t, 0.4)
    ab = ease(prog(t, T_DESPERTO, 0.6), "out")
    ctx.save()
    zoom(ctx, 1 + 0.05 * prog(t, b(20), b(22) - b(20)), 540, 900)
    parpadeo = 1 - 0.9 * math.exp(-((t - (T_DESPERTO + 1.2)) / 0.08) ** 2)
    ojo(ctx, 540, 1080, 420 * pop(t, b(20) - 0.05, 0.4), ab=ab * parpadeo, mira=(0.3 * math.sin(t * 1.1), 0))
    ctx.restore()
    kartel(ctx, "A LOS POCOS MINUTOS", 540, 300, 66, t, T_POCOS - 0.1, T_CUANDO - 0.2, box=BLANCO, rot=-2)
    globo(ctx, 600, 620, 820, 300, pop(t, T_CUANDO - 0.1, 0.4), ["¿CUÁNDO EMPIEZA", "LA OPERACIÓN?"])


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_mesa),
    (b(6) - 0.08, d_balanza),
    (b(9) - 0.08, d_reloj30),
    (b(10) - 0.08, d_gradas),
    (b(11) - 0.08, d_vida),
    (b(12) - 0.08, d_1846),
    (b(13) - 0.08, d_eter),
    (b(16) - 0.08, d_oceano),
    (b(17) - 0.08, d_londres),
    (b(20) - 0.08, d_desperto),
    (b(22) - 0.08, d_cierre),
]
XF = 0.18
WHOOSH += [t0 for t0, _ in ESCENAS[1:]]


def punch(t, t0, d=0.3, amp=0.05):
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


def escena(t):
    return max(k for k, (t0, _) in enumerate(ESCENAS) if t >= t0)


def componer(ctx, t):
    i = escena(t)
    t0, fn = ESCENAS[i]
    dt = t - t0
    if i > 0 and dt < XF:
        capa(ctx, ESCENAS[i - 1][1], t)
        ctx.save()
        ctx.push_group()
        zoom(ctx, punch(t, t0))
        fn(ctx, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(clamp(dt / XF))
        ctx.restore()
        return
    if i > 0:
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


# ------------------------------------------------------------------ sonido (sobrio: tic-tac, golpes graves, aire)
def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    for t0 in WHOOSH:
        ev(t0, "whoosh_suave", 0.45)
    for t0 in POPS:
        ev(t0, "pop", 0.35)
    ev(T_DESP - 0.15, "whoosh_suave", 0.4)
    ev(T_NADA + 0.25, "whoosh", 0.4)
    k = 0
    while T_CORTE - 0.1 + k / 4.8 < b(3) - 0.35:      # cada golpe de sierra
        ev(T_CORTE - 0.1 + k / 4.8, "tick", 0.3, f=320 + 40 * (k % 2), d=0.09)
        k += 1
    ev(T_ALC - 0.25 + 0.35, "clunk", 0.5)
    ev(T_OPIO - 0.25 + 0.35, "clunk", 0.4)
    ev(T_NOALC, "golpe", 0.6)
    for (_, _, t0) in MANOS:
        ev(t0 + 0.3, "golpe", 0.35)
    ev(T_VELOC - 0.05, "clunk", 0.5)
    for k in range(int((T_SEG9 + 0.1 - T_AMP) / 0.1)):
        ev(T_AMP + k * 0.1, "tick", 0.2, f=2100, d=0.03)
    for k in range(10):
        ev(T_RELOJ10 - 0.35 + k * 0.12, "tick", 0.18, f=2400 + 80 * k, d=0.03)
    for k in range(int((b(12) - b(11)) * 1.25)):
        ev(b(11) + 0.02 + k / 1.25, "golpe", 0.22)
    ev(T_1846 + 0.1, "golpe", 0.8)
    ev(T_1846 + 0.12, "subida", 0.3, d=0.9)
    ev(T_RESP - 0.2, "siseo", 0.35, d=1.8)
    ev(T_DORM - 0.1, "whoosh_suave", 0.35)
    ev(b(15) - 0.2, "subida", 0.2, d=0.6)
    ev(b(16) + 0.15, "whoosh_suave", 0.5)
    ev(b(18) - 0.2, "siseo", 0.3, d=1.2)
    for k in range(int((T_VELOZ + 0.1 - T_AMPUTO) / 0.1)):
        ev(T_AMPUTO + k * 0.1, "tick", 0.2, f=2100, d=0.03)
    ev(T_VELOZ + 0.1, "ding", 0.4)
    ev(T_DESPERTO, "whoosh_suave", 0.35)
    ev(b(22) + 0.1, "whoosh_suave", 0.3)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "asi_operaban_antes_de_la_anestesia.mp4"))
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

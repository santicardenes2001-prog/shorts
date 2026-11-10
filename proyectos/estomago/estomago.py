"""Short "¿Por qué tu estómago no se digiere a sí mismo?" — animación procedural (mismo armazón que cielo.py y gps.py).

El estómago se dibuja en corte, con la forma real en J vista de frente: el esófago entra arriba, el fondo se
abomba a la derecha de la pantalla (el lado izquierdo del cuerpo) y el píloro sale a la izquierda hacia el duodeno.
La explicación pasa a un corte de la pared: ácido arriba, capa de moco con bicarbonato y la fila de células.
El último cuadro es igual al primero (loop).

    python proyectos/estomago/estomago.py --fotos 0,5.5,14
    python proyectos/estomago/estomago.py --probar
    python proyectos/estomago/estomago.py        # render completo -> salidas/por_que_tu_estomago_no_se_digiere.mp4
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
from picante import _elipse_suave, capa, carita, fondo_azul, mezcla  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Tu estómago fabrica un ácido capaz de corroer metal.",                  # b0
    "Lo usa para deshacer la carne que comes.",                              # b1
    "Pero tu estómago también es carne.",                                    # b2
    "Entonces, ¿por qué no se deshace a sí mismo?",                          # b3
    "Porque nunca deja que el ácido lo toque.",                              # b4
    "Toda la pared está cubierta por una capa de moco espeso.",              # b5
    "El ácido queda de un lado y la pared del otro.",                        # b6
    "Dentro de ese moco hay algo escondido: bicarbonato.",                   # b7
    "Es lo contrario de un ácido, y lo neutraliza.",                         # b8
    "El ácido que entra ahí se apaga antes de llegar.",                      # b9
    "Aun así, la defensa no es perfecta.",                                   # b10
    "La superficie se desgasta todo el tiempo.",                             # b11
    "Para eso existe el último recurso, el más extremo.",                    # b12
    "Tu estómago descarta las células gastadas y fabrica otras nuevas.",     # b13
    "Pierde medio millón de células por minuto.",                            # b14
    "En unos tres días, toda la superficie se renovó.",                      # b15
    "La que hoy toca tu comida no existía la semana pasada.",                # b16
    "Tiene que ser así:",                                                    # b17
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
PARED = hx("#EE7A96")
PARED_VIEJA = hx("#958791")
INTERIOR = hx("#FBC6D2")
PLIEGUE = hx("#F09DB2")
ACIDO = hx("#8BE04A")
ACIDO_CLARO = hx("#C8FF8A")
GRIS_N = hx("#C9D3DC")
MOCO = hx("#DCEBFF")
BICA = hx("#4DA3FF")
CELULA = hx("#F79CB2")
CELULA_VIEJA = hx("#B9939E")
NUCLEO = hx("#9B3F6B")
TEJIDO = hx("#B9476A")
VASO_S = hx("#D9334A")
CARNE = hx("#D9576B")
FIBRA = hx("#F59AA8")
GRASA = hx("#FFE6D8")
METAL = hx("#C9CFD8")
OXIDO = hx("#8C7A62")
ROJO = hx("#FF3B2F")
VERDE = hx("#2BD45A")
KF = 60 * round(14 * TOTAL / 60) / (14 * TOTAL)      # el fondo de puntos cierra justo en el loop
POPS, WHOOSH = [], []


# ------------------------------------------------------------------ ayudas
def fondo(ctx, t, oscuro=0.0):
    fondo_azul(ctx, t * KF)
    if oscuro > 0:
        ctx.set_source_rgba(0.027, 0.043, 0.11, oscuro)
        ctx.paint()


def per(t, k, ph=0.0):
    """Vaivén que cierra justo en el loop."""
    return math.sin(TAU * k * t / TOTAL + ph)


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


def fmt(v):
    return f"{int(round(v)):,}".replace(",", ".")


def estrella(ctx, x, y, r, a=1.0, col=BLANCO):
    if a <= 0.01 or r <= 0.3:
        return
    _elipse_suave(ctx, x, y, r * 3.2, r * 3.2, col, 0.3 * a)
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


def suave(ctx, pts):
    """Camino cerrado suave (Catmull-Rom) por los puntos."""
    n = len(pts)
    ctx.move_to(*pts[0])
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        ctx.curve_to(*c1, *c2, *p2)
    ctx.close_path()


def anillo(ctx, x, y, q, r0=20, r1=90, col=BLANCO, w=7):
    if q <= 0 or q >= 1:
        return
    ctx.arc(x, y, lerp(r0, r1, ease(q, "out")), 0, TAU)
    ctx.set_source_rgba(*col, 0.9 * (1 - q))
    ctx.set_line_width(w)
    ctx.stroke()


# ------------------------------------------------------------------ el estómago (forma en J, vista de frente)
# Dos tramos abiertos: A baja por el borde izquierdo del esófago, la curvatura menor, el píloro y el duodeno;
# B vuelve desde el corte del duodeno por la curvatura mayor y el fondo hasta el borde derecho del esófago.
SEG_A = ((-40, -1050), [("l", -40, -340), ("c", -42, -180, -65, -40, -135, 28), ("c", -195, 78, -270, 70, -320, 62),
                        ("c", -345, 58, -365, 52, -392, 52), ("c", -440, 52, -472, 82, -472, 130),
                        ("l", -472, 270)])
SEG_B = ((-402, 270), [("l", -402, 142), ("c", -402, 126, -394, 118, -380, 118), ("c", -362, 118, -346, 120, -330, 128),
                       ("c", -250, 250, -100, 340, 60, 320), ("c", 230, 300, 330, 160, 330, -40),
                       ("c", 330, -220, 300, -380, 170, -420), ("c", 90, -445, 52, -400, 50, -340),
                       ("l", 50, -1050)])
X0, Y0 = 600, 960                                # dónde va el estómago en pantalla
CARA0 = dict(ojos="open", boca="smile", look=(-0.2, 0.5))


def _tramo(ctx, seg, mover=True):
    (x, y), ops = seg
    if mover:
        ctx.move_to(x, y)
    else:
        ctx.line_to(x, y)
    for op in ops:
        if op[0] == "l":
            ctx.line_to(op[1], op[2])
        else:
            ctx.curve_to(*op[1:])


def silueta(ctx):
    ctx.new_path()
    _tramo(ctx, SEG_A)
    _tramo(ctx, SEG_B, mover=False)
    ctx.close_path()


def borde(ctx):
    """El contorno sin cerrar: el duodeno queda abierto, como un tubo que sigue."""
    ctx.new_path()
    _tramo(ctx, SEG_A)
    _tramo(ctx, SEG_B)


RUGAS = [((200, -330), (270, -150), (250, 40), (210, 140)), ((110, -280), (170, -80), (150, 90), (80, 200)),
         ((20, -200), (50, -20), (-20, 120), (-140, 190)), ((-150, 110), (-200, 150), (-260, 140), (-310, 100))]
_r = rng(4)
BURB = [(float(_r.uniform(-300, 290)), float(_r.uniform(0, 1)), int(_r.integers(7, 14)), float(_r.uniform(5, 11)))
        for _ in range(16)]


def acido_y(x, t, base, ola):
    return base + ola * (6 * per(t, 7, x * 0.025) + 4 * per(t, 11, x * 0.041 + 1.3))


def estomago(ctx, x, y, s, t, cara=None, acido=80.0, ola=1.0, pared=PARED, barrido=None, dentro=None,
             acido_col=ACIDO):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    silueta(ctx)
    ctx.set_source_rgb(*INTERIOR)
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    for p0, p1, p2, p3 in RUGAS:                 # pliegues de la mucosa
        ctx.move_to(*p0)
        ctx.curve_to(*p1, *p2, *p3)
        ctx.set_source_rgba(*PLIEGUE, 0.9)
        ctx.set_line_width(11)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    # el ácido
    ctx.move_to(-560, 700)
    for xx in range(-560, 420, 20):
        ctx.line_to(xx, acido_y(xx, t, acido, ola))
    ctx.line_to(420, 700)
    ctx.close_path()
    ctx.set_source_rgba(*acido_col, 0.93)
    ctx.fill()
    ctx.move_to(-560, acido_y(-560, t, acido, ola))
    for xx in range(-540, 420, 20):
        ctx.line_to(xx, acido_y(xx, t, acido, ola))
    ctx.set_source_rgba(*ACIDO_CLARO, 0.9)
    ctx.set_line_width(7)
    ctx.stroke()
    for bx, ph, k, r in BURB:                    # burbujas que suben y revientan en la superficie
        yy = 300 - 230 * ((t * k / TOTAL + ph) % 1.0)
        sup = acido_y(bx, t, acido, ola)
        if yy < sup + 8:
            continue
        ctx.arc(bx, yy, r, 0, TAU)
        ctx.set_source_rgba(*ACIDO_CLARO, 0.75)
        ctx.fill_preserve()
        ctx.set_source_rgba(*hx("#3E8F22"), 0.6)
        ctx.set_line_width(2.5)
        ctx.stroke()
    if dentro:
        dentro(ctx)
    borde(ctx)                                   # la pared (la mitad de adentro del trazo)
    ctx.set_source_rgb(*pared)
    ctx.set_line_width(46)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    if barrido is not None:                      # la superficie nueva avanza de derecha a izquierda
        ctx.save()
        ctx.rectangle(barrido, -1200, 2000, 2600)
        ctx.clip()
        borde(ctx)
        ctx.set_source_rgb(*PARED)
        ctx.set_line_width(46)
        ctx.stroke()
        ctx.restore()
        for i, yy in enumerate((-390, -260, -120, 30, 170, 290)):
            estrella(ctx, barrido + 12 * math.sin(t * 9 + i), yy, 17 + 6 * math.sin(t * 11 + i * 2), 1.0, AMARILLO)
    ctx.restore()
    if cara:
        carita(ctx, 130, -170, 120, 1.0, rubor=True, **cara)
    borde(ctx)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(11)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.restore()


# ------------------------------------------------------------------ carne, fibras, lupa, vaso y tornillo
def fibras(ctx, cx, cy, R, ang=-0.45, col=FIBRA):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(ang)
    for i in range(-14, 15):
        yy = i * 20
        ctx.move_to(-R, yy)
        ctx.curve_to(-R / 3, yy - 8, R / 3, yy + 8, R, yy)
    ctx.set_source_rgba(*col, 0.6)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.restore()


_r = rng(6)
NC = [float(abs(v)) for v in _r.uniform(-1, 1, 18)]


def carne(ctx, x, y, s, t, rot=0.0, dis=0.0, a=1.0):
    """Un trozo de carne con vetas de músculo y un borde de grasa. dis = cuánto se deshizo (0..1)."""
    if s <= 0.01 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s, s)
    ctx.push_group()
    pts = []
    n = 18
    for k in range(n):
        an = TAU * k / n
        r = 100 * (1 + 0.13 * math.sin(2 * an + 0.7) + 0.07 * math.sin(5 * an + 1.3))
        r = r * (1 - 0.45 * dis) - dis * 34 * NC[k] + dis * 6 * math.sin(t * 18 + k * 1.7)
        pts.append((max(r, 8) * math.cos(an) * 1.25, max(r, 8) * math.sin(an) * 0.85))
    suave(ctx, pts)
    ctx.set_source_rgb(*CARNE)
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    fibras(ctx, 0, 0, 220)
    ctx.move_to(-130, -50)
    ctx.curve_to(-60, -100, 60, -100, 130, -48)
    ctx.set_source_rgb(*GRASA)
    ctx.set_line_width(24)
    ctx.stroke()
    ctx.restore()
    suave(ctx, pts)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def lupa(ctx, x, y, R, s):
    """Lupa sobre la pared: adentro se ve el músculo, igual que en la carne."""
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for lw, col in ((R * 0.3, INK), (R * 0.18, hx("#8A6A45"))):
        ctx.move_to(R * 0.72, R * 0.72)
        ctx.line_to(R * 1.55, R * 1.55)
        ctx.set_line_width(lw)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgb(*col)
        ctx.stroke()
    ctx.save()
    ctx.arc(0, 0, R, 0, TAU)
    ctx.clip()
    ctx.set_source_rgb(*CARNE)
    ctx.paint()
    fibras(ctx, 0, 0, R * 1.6)
    ctx.restore()
    ctx.arc(0, 0, R, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(R * 0.17)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*METAL)
    ctx.set_line_width(R * 0.09)
    ctx.stroke()
    ctx.arc(0, 0, R * 0.78, math.radians(200), math.radians(250))
    ctx.set_source_rgba(*BLANCO, 0.7)
    ctx.set_line_width(R * 0.07)
    ctx.stroke()
    ctx.restore()


_r = rng(8)
HOYOS = [(float(_r.uniform(-13, 13)), float(_r.uniform(12, 160)), float(_r.uniform(3, 6.5))) for _ in range(18)]
BURB_V = [(float(_r.uniform(-24, 24)), float(_r.uniform(0, 1)), float(_r.uniform(3, 6))) for _ in range(12)]


def tornillo(ctx, x, y, s, corr):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    col = mezcla(METAL, OXIDO, 0.75 * corr)
    w = 20 - 5 * corr
    rrect(ctx, -w, 0, 2 * w, 170, 6)
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    for k in range(9):
        yy = 14 + k * 17
        ctx.move_to(-w, yy)
        ctx.line_to(w, yy + 8)
    ctx.set_source_rgba(*INK, 0.5)
    ctx.set_line_width(4)
    ctx.stroke()
    rrect(ctx, -46, -30, 92, 34, 8)
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    for px, py, pr in HOYOS[:int(len(HOYOS) * corr)]:
        ctx.arc(px * (w / 20), py, pr, 0, TAU)
        ctx.set_source_rgb(*hx("#5E4B3A"))
        ctx.fill()
    ctx.restore()


def vaso(ctx, x, y, s, t, corr):
    """Vaso de laboratorio con ácido del estómago y un tornillo que se corroe."""
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    rrect(ctx, -115, -150, 230, 290, 26)
    ctx.set_source_rgba(0.75, 0.88, 1, 0.14)
    ctx.fill()
    ctx.save()
    rrect(ctx, -115, -150, 230, 290, 26)
    ctx.clip()
    ctx.move_to(-130, 200)
    for xx in range(-130, 140, 20):
        ctx.line_to(xx, -60 + 4 * math.sin(t * 3 + xx * 0.05))
    ctx.line_to(140, 200)
    ctx.close_path()
    ctx.set_source_rgba(*ACIDO, 0.85)
    ctx.fill()
    tornillo(ctx, 0, -20, 0.85, corr)
    if corr > 0:
        for bx, ph, r in BURB_V:
            q = (t * 0.9 + ph) % 1.0
            yy = lerp(120, -60, q)
            ctx.arc(bx + 6 * math.sin(q * 9), yy, r * (0.6 + 0.6 * q), 0, TAU)
            ctx.set_source_rgba(*ACIDO_CLARO, 0.85 * min(1, corr * 3))
            ctx.fill()
    ctx.restore()
    rrect(ctx, -115, -150, 230, 290, 26)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    ctx.move_to(-132, -150)
    ctx.line_to(132, -150)
    ctx.set_line_width(13)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.move_to(-82, -110)
    ctx.line_to(-82, 90)
    ctx.set_source_rgba(*BLANCO, 0.55)
    ctx.set_line_width(10)
    ctx.stroke()
    ctx.restore()


# ------------------------------------------------------------------ gotas de ácido, bicarbonato y células
def gota(ctx, x, y, r, col=ACIDO, cara=None, a=1.0):
    if r <= 0.5 or a <= 0.01:
        return
    ctx.save()
    ctx.push_group()
    ctx.move_to(x, y - 1.75 * r)
    ctx.curve_to(x + 0.5 * r, y - 1.1 * r, x + r, y - 0.6 * r, x + r, y)
    ctx.arc(x, y, r, 0, math.pi)
    ctx.curve_to(x - r, y - 0.6 * r, x - 0.5 * r, y - 1.1 * r, x, y - 1.75 * r)
    ctx.close_path()
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(3, r * 0.15))
    ctx.stroke()
    ctx.save()
    ctx.translate(x - 0.42 * r, y - 0.45 * r)
    ctx.scale(0.16 * r, 0.26 * r)
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()
    ctx.set_source_rgba(*BLANCO, 0.75)
    ctx.fill()
    if cara:
        carita(ctx, x, y + 0.08 * r, 0.62 * r, r / 105, **cara)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


CARA_ACIDO = dict(ojos="open", boca="grin", ceja="angry")
CARA_APAGADA = dict(ojos="closed", boca="smile")


def bicarbonato(ctx, x, y, r, s=1.0, a=1.0):
    if s <= 0.01 or a <= 0.01:
        return
    rr = r * s
    ctx.save()
    ctx.push_group()
    _elipse_suave(ctx, x, y, rr * 2.2, rr * 2.2, BICA, 0.35)
    ctx.arc(x, y, rr, 0, TAU)
    ctx.set_source_rgb(*BICA)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()
    carita(ctx, x, y + 2, 0.68 * rr, rr / 100, ojos="happy", boca="smile")
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


NSLOT = 11
SX0 = -60                                        # ranura i: x = SX0 + 110 i, centro = x + 52
CW, CH = 104, 300
CY = 1060                                        # tope de las células
MT, MB = 900, 1090                               # moco: borde de arriba y de abajo
CARAS_CEL = {2, 5, 8}
RUIDO = rng(5).uniform(-1, 1, (NSLOT + 4, 25))


def celula(ctx, x, ytop, w=CW, h=CH, wear=0.0, nick=False, cara=None, a=1.0, rot=0.0, seed=0, fantasma=False):
    if a <= 0.01:
        return
    ctx.save()
    ctx.translate(x + w / 2, ytop + h / 2)
    ctx.rotate(rot)
    ctx.translate(-w / 2, -h / 2)
    ctx.push_group()
    dome = 0.38 * w
    ctx.new_path()
    ctx.move_to(0, h)
    n = 24
    for k in range(n + 1):
        u = k / n
        yy = dome * (2 * u - 1) ** 2 + wear * RUIDO[seed % len(RUIDO)][k] * 16
        if nick and 0.32 <= u <= 0.68:
            yy += 0.33 * w * (1 - abs(u - 0.5) / 0.18)
        ctx.line_to(w * u, max(0, yy))
    ctx.line_to(w, h)
    ctx.close_path()
    if fantasma:
        ctx.set_source_rgba(*INK, 0.55)
        ctx.set_line_width(5)
        ctx.set_dash([14, 10])
        ctx.stroke()
        ctx.set_dash([])
    else:
        ctx.set_source_rgb(*mezcla(CELULA, CELULA_VIEJA, wear))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(6)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
        ctx.save()
        ctx.translate(w / 2, h * 0.74)
        ctx.scale(w * 0.25, h * 0.1)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.set_source_rgba(*NUCLEO, 0.85)
        ctx.fill()
        if cara:
            carita(ctx, w / 2, h * 0.37, 0.42 * w, w / 250, **cara)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


# ------------------------------------------------------------------ 1. apertura: el ácido que corroe metal
T_ACIDO0 = b(0, "acido")
T_CORROER = b(0, "corroer")
POPS += [T_ACIDO0 - 0.1, T_CORROER - 0.2]


def vista_inicio(ctx, t, cara=CARA0, acido_col=ACIDO):
    fondo(ctx, t, 0.25)
    estomago(ctx, X0, Y0, 1.0, t, cara=cara, acido_col=acido_col)


def d_inicio(ctx, t):
    ctx.save()
    zoom(ctx, 1 + 0.035 * prog(t, 0, b(1)), 600, 900)
    k = bump(t, T_ACIDO0, 0.5, 1.0) - 1
    vista_inicio(ctx, t, acido_col=mezcla(ACIDO, ACIDO_CLARO, k))
    vaso(ctx, 265, 660, 0.95 * pop(t, T_CORROER - 0.2, 0.35) * sale(t, b(1) - 0.15), t,
         prog(t, T_CORROER, b(1) - T_CORROER))
    ctx.restore()
    kartel(ctx, "ÁCIDO CLORHÍDRICO", 540, 300, 70, t, T_ACIDO0 - 0.1, b(1) - 0.15, rot=-2)
    kartel(ctx, "CORROE METAL", 265, 880, 58, t, T_CORROER - 0.05, b(1) - 0.15, box=BLANCO, rot=3)


def d_cierre(ctx, t):
    ctx.save()
    zoom(ctx, 1 + 0.035 * (1 - prog(t, b(17), TOTAL - b(17))), 600, 900)
    vista_inicio(ctx, t)
    ctx.restore()


# ------------------------------------------------------------------ 2. deshace la carne que comes
T_DESH = b(1, "deshacer")
T_CARNE1 = b(1, "carne")
POPS += [T_CARNE1 - 0.1]


def pos_carne(t):
    """Posición del trozo en coordenadas del estómago: baja por el esófago y cae en el ácido."""
    t0, t1 = b(1), b(1) + 0.45
    if t < t1:
        return 5, lerp(-1100, -340, prog(t, t0, t1 - t0, "in")), 0.0
    p = prog(t, t1, T_DESH - t1, "in")
    return lerp(5, 110, p), lerp(-340, 70, p) + 40 * prog(t, T_DESH, 1.4), 0.6 * p


def d_carne(ctx, t):
    dis = prog(t, T_DESH + 0.05, 1.5, "inout")

    def dentro(c):
        x, y, rot = pos_carne(t)
        carne(c, x, y, 0.42, t, rot=rot + 0.3 * dis, dis=dis, a=1 - prog(t, T_DESH + 1.2, 0.35))
        if t >= T_DESH:
            q = clamp((t - T_DESH) / 0.6)
            c.save()
            c.translate(110, 82)
            c.scale(1, 0.35)
            anillo(c, 0, 0, q, 30, 170, ACIDO_CLARO, 9)
            c.restore()
            for i in range(10):                  # burbujas extra mientras se deshace
                qq = ((t - T_DESH) * 1.6 + i / 10) % 1.0
                c.arc(110 + 60 * math.sin(i * 2.3) + 10 * math.sin(qq * 8), lerp(150, 85, qq), 5 + 4 * qq, 0, TAU)
                c.set_source_rgba(*ACIDO_CLARO, 0.8 * (1 - dis * 0.6))
                c.fill()

    cara = dict(ojos="happy", boca="grin") if t >= T_DESH else CARA0
    fondo(ctx, t, 0.25)
    estomago(ctx, X0, Y0, 1.0, t, cara=cara, ola=1 + 2.0 * (bump(t, T_DESH, 0.7, 1.0) - 1),
             dentro=dentro)
    kartel(ctx, "DESHACE LA CARNE", 540, 300, 74, t, T_CARNE1 - 0.1, b(2) - 0.15, rot=-2)


# ------------------------------------------------------------------ 3. tu estómago también es carne
T_TAMB = b(2, "tambien")
T_CARNE2 = b(2, "carne")
POPS += [b(2) + 0.05, T_TAMB - 0.1, T_CARNE2 - 0.15]


def d_tambien(ctx, t):
    fondo(ctx, t, 0.25)
    preoc = t >= T_CARNE2 - 0.05
    cara = dict(ojos="wide", boca="o", ceja="worried", look=(-0.6, -0.4)) if preoc else dict(ojos="open", boca="smile",
                                                                                            look=(-0.8, -0.5))
    estomago(ctx, X0, Y0, 1.0, t, cara=cara)
    s1 = pop(t, b(2) + 0.05, 0.4)
    carne(ctx, 270, 590, 0.95 * s1, t, rot=-0.1)
    kartel(ctx, "CARNE", 270, 430, 52, t, b(2) + 0.15, box=BLANCO, rot=-3)
    if t >= T_TAMB - 0.1:
        s = pop(t, T_TAMB - 0.1, 0.3)
        ctx.save()
        ctx.translate(535, 590)
        ctx.scale(max(s, 0.01), max(s, 0.01))
        texto(ctx, "=", 0, 0, 170, fill=AMARILLO, sw=14)
        ctx.restore()
    lupa(ctx, 800, 590, 115, pop(t, T_TAMB - 0.1, 0.35))
    kartel(ctx, "TU ESTÓMAGO", 800, 430, 52, t, T_TAMB, box=BLANCO, rot=3)
    kartel(ctx, "TAMBIÉN ES CARNE", 540, 270, 76, t, T_CARNE2 - 0.15, b(3) - 0.15, rot=-2)


# ------------------------------------------------------------------ 4. ¿por qué no se deshace a sí mismo?
T_PORQ = b(3, "por")
POPS += [T_PORQ - 0.1]


def d_porque(ctx, t):
    z = 1 + 1.7 * prog(t, b(4) - 0.55, 0.55, "in")
    ctx.save()
    zoom(ctx, z, 905, 1100)
    fondo(ctx, t, 0.25)
    tiembla = 7 * math.sin(t * 47) * prog(t, b(3) + 0.2, 0.3)
    estomago(ctx, X0 + tiembla, Y0, 1.0, t, cara=dict(ojos="wide", boca="wavy", ceja="worried", look=(0, 0.8)),
             acido=lerp(80, 30, prog(t, b(3), 0.8)), ola=lerp(1.0, 4.0, prog(t, b(3), 0.8)))
    ctx.restore()
    kartel(ctx, "¿POR QUÉ NO SE DESHACE?", 540, 300, 70, t, T_PORQ - 0.1, b(4) - 0.4, rot=-2)


# ------------------------------------------------------------------ 5. el corte de la pared (b4 a b14)
T_TOQUE = b(4, "toque")
T_POUR = b(5) + 0.05
T_MOCO = b(5, "moco")
T_ACIDO6 = b(6, "acido")
T_PARED6 = b(6, "pared")
T_ESCOND = b(7, "escondido")
T_BICA = b(7, "bicarbonato")
T_CONTR = b(8, "contrario")
T_NEU = b(8, "neutraliza")
T_APAGA = b(9, "apaga")
T_DIP = b(10) + 0.1
T_D0 = T_DIP + 0.9
T_MORD = b(10, "perfecta") - 0.05
T_DESG = b(11, "desgasta")
T_ULT = b(12, "ultimo")
T_DESC = b(13, "descarta")
T_FABR = b(13, "fabrica")
T_MEDIO = b(14, "medio")
T_CEL14 = b(14, "celulas")
T_MIN = b(14, "minuto")
POPS += [T_TOQUE - 0.1, T_MOCO - 0.15, T_ACIDO6 - 0.1, T_PARED6 - 0.1, T_BICA - 0.1, T_CONTR - 0.1, T_NEU,
         T_APAGA - 0.1, T_MORD + 0.05, T_DESG - 0.1, T_DESC - 0.05, T_FABR - 0.05, T_CEL14 - 0.05]


def front(t):
    return lerp(-80, 1180, prog(t, T_POUR, 1.1, "inout"))


def _t_cubre(x):
    tt = T_POUR
    while front(tt) < x + 20 and tt < T_POUR + 1.3:
        tt += 0.01
    return tt


def dip(t):
    return 112 * prog(t, T_DIP, 0.9) * (1 - prog(t, T_DESC - 0.3, 0.8))


def moco_top(x, t):
    return MT + 8 * per(t, 5, x * 0.018) + dip(t) * math.exp(-((x - 542) / 72) ** 2)


# gotas que bajan en b4 y quedan apoyadas sobre el moco: (x, empiezan, hasta dónde bajan)
REPOSO = [(180, b(4) + 0.25, 700), (542, b(4), 1006), (760, b(4) + 0.45, 780), (980, b(4) + 0.65, 640)]
T_CUBRE = [_t_cubre(x) for x, _, _ in REPOSO]
GOTA_B = (380, 1032)                             # la que se cruza con el bicarbonato en b8
BICAS = [(130, 1000), (255, 1042), (480, 985), (640, 1035), (810, 995), (975, 1040)]
GOTAS_C = [(330, b(9) + 0.05), (655, b(9) + 0.45), (885, b(9) + 0.85)]
_r = rng(9)
ORDEN = list(_r.permutation(NSLOT))
T_SHED = {int(i): T_DESC + 0.24 * k for k, i in enumerate(ORDEN)}
P_CICLO = 0.85
C_START = {i: b(14) + 0.05 + float(_r.uniform(0, P_CICLO)) for i in range(NSLOT)}
_r = rng(12)
BURB_C = [(float(_r.uniform(20, 1060)), float(_r.uniform(0, 1)), float(_r.uniform(0.12, 0.25)), float(_r.uniform(4, 10)))
          for _ in range(26)]


def y_reposo(i, t):
    x, t0, meta = REPOSO[i]
    if i == 1:
        yd = lerp(150, meta, prog(t, t0, T_TOQUE - t0, "inout"))
    else:
        yd = lerp(150, meta, prog(t, t0, 1.5, "out"))
    y = lerp(yd, MT - 46 + 6 * per(t, 9, i), prog(t, T_CUBRE[i], 0.45, "out"))
    if i == 1 and t >= T_D0:                     # la del medio se cuela por el hueco del moco
        y = lerp(y, 1018, prog(t, T_D0, T_MORD - T_D0, "in"))
    return x, y


def wear0(t):
    return prog(t, b(11) + 0.1, 1.7)


def cara_cel(i, t, gen=0):
    if i not in CARAS_CEL:
        return None
    if gen > 0:
        return dict(ojos="happy", boca="grin")
    if i == 5 and T_MORD <= t < b(11):
        return dict(ojos="closed", boca="wavy", ceja="worried")
    if t >= b(11):
        return dict(ojos="open", boca="flat", ceja="worried")
    if i == 5 and (b(4) + 0.6 <= t < T_CUBRE[1] + 0.2 or T_D0 - 0.2 <= t < T_MORD):
        return dict(ojos="wide", boca="o", ceja="worried", look=(0, -1))
    if t >= T_CUBRE[0]:
        return dict(ojos="happy", boca="grin")
    return dict(ojos="open", boca="smile", look=(0, -0.8))


def celulas(ctx, t):
    ctx.save()
    ctx.rectangle(-400, -400, 1900, CY + CH + 400)
    ctx.clip()
    for i in range(NSLOT):
        x = SX0 + 110 * i
        ts = T_SHED[i]
        nick = i == 5 and t >= T_MORD
        if t < ts:
            celula(ctx, x, CY, wear=wear0(t), nick=nick, cara=cara_cel(i, t), seed=i)
            continue
        q = (t - ts) / 1.3                       # la vieja se suelta y sube al ácido
        if q < 1:
            celula(ctx, x + 14 * math.sin(q * 5), CY - 360 * ease(q, "out"), wear=1.0, nick=nick,
                   cara=dict(ojos="closed", boca="flat") if i in CARAS_CEL else None, a=1 - q, rot=0.5 * q * (1 if i % 2 else -1),
                   seed=i)
        cs = C_START[i]
        if t < cs:
            r = prog(t, ts + 0.12, 0.55, "out")
            celula(ctx, x, CY + CH * (1 - r), cara=cara_cel(i, t, 1), seed=i + 1)
            continue
        u = ((t - cs) / P_CICLO) % 1.0           # medio millón por minuto: se van y aparecen sin parar
        g = int((t - cs) / P_CICLO)
        if u < 0.8:
            qq = u / 0.8
            celula(ctx, x + 10 * math.sin(qq * 5), CY - 330 * ease(qq, "out"), wear=0.6, a=1 - qq,
                   rot=0.4 * qq * (1 if (i + g) % 2 else -1), seed=i + g + 1)
        r = ease(min(1.0, u / 0.4), "out")
        celula(ctx, x, CY + CH * (1 - r), cara=cara_cel(i, t, 2), seed=i + g + 2)
    ctx.restore()


def tejido(ctx):
    ctx.rectangle(-400, CY + 40, 1900, 1400)       # detrás de las células: si una se va, se ve el tejido
    ctx.set_source_rgb(*TEJIDO)
    ctx.fill()
    for yy, ph in ((1450, 0.0), (1610, 1.7)):
        for lw, col in ((34, INK), (22, VASO_S)):
            ctx.move_to(-100, yy)
            for xx in range(-100, 1240, 40):
                ctx.line_to(xx, yy + 18 * math.sin(xx * 0.01 + ph))
            ctx.set_source_rgb(*col)
            ctx.set_line_width(lw)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()


def moco(ctx, t):
    f = front(t)
    if f <= -60:
        return
    xe = min(f, 1240)
    ctx.new_path()
    ctx.move_to(-120, MB)
    xx = -120
    while xx < xe:
        ctx.line_to(xx, moco_top(xx, t))
        xx += 12
    ctx.line_to(xe, moco_top(xe, t))
    yt = moco_top(xe, t)
    ctx.curve_to(xe + 40, yt + 30, xe + 40, MB - 20, xe, MB)
    ctx.close_path()
    ctx.set_source_rgba(*MOCO, 0.8)
    ctx.fill_preserve()
    ctx.set_source_rgba(*BLANCO, 0.9)
    ctx.set_line_width(5)
    ctx.stroke()
    for x0, x1, yy in ((60, 260, 935), (420, 520, 955), (700, 900, 940)):     # brillos
        if x1 < xe:
            ctx.move_to(x0, yy + 6 * per(t, 5, x0 * 0.018))
            ctx.line_to(x1, yy + 6 * per(t, 5, x1 * 0.018))
            ctx.set_source_rgba(*BLANCO, 0.55)
            ctx.set_line_width(7)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()


_r = rng(15)
FLOTAN = [(float(_r.uniform(0, 1)), float(_r.uniform(330, 760)), float(_r.uniform(0.025, 0.05)), float(_r.uniform(0, TAU)),
           int(_r.integers(0, 2))) for _ in range(7)]


def gotas_fondo(ctx, t):
    """Gotas de ácido que flotan lejos, para que se lea que arriba todo es ácido."""
    for u, y, v, ph, sg in FLOTAN:
        q = (u + t * v * (1 if sg else -1)) % 1.0
        gota(ctx, lerp(-80, 1160, q), y + 18 * math.sin(t * 1.3 + ph), 26, cara=CARA_ACIDO, a=0.55)


def gotas(ctx, t):
    # las cuatro que bajan en b4
    for i in range(len(REPOSO)):
        if t < REPOSO[i][1]:
            continue
        x, y = y_reposo(i, t)
        a = 1.0
        if i == 1 and t >= T_MORD:
            a = 1 - prog(t, T_MORD, 0.15)
            anillo(ctx, x, 1050, clamp((t - T_MORD) / 0.5), 20, 110, ACIDO_CLARO, 8)
        gota(ctx, x + 3 * math.sin(t * 5 + i), y, 42, cara=CARA_ACIDO, a=a)
    # b8: una gota contra un bicarbonato
    if b(8) <= t < T_NEU + 1.4:
        x, yb = GOTA_B
        if t < T_NEU:
            y = lerp(180, 975, prog(t, b(8), T_NEU - 0.2 - b(8), "inout"))
            gota(ctx, x, y, 42, cara=CARA_ACIDO)
        else:
            q = clamp((t - T_NEU) / 1.4)
            gota(ctx, x, 1000 - 30 * q, 30 * (1 - 0.4 * q), col=GRIS_N, cara=CARA_APAGADA, a=1 - q)
            anillo(ctx, x, 1000, clamp((t - T_NEU) / 0.5), 20, 130, AMARILLO, 9)
    # b9: entran tres y se apagan antes de llegar
    for x, t0 in GOTAS_C:
        if t < t0 or t > t0 + 1.3:
            continue
        y = lerp(180, 1012, prog(t, t0, 1.05, "in"))
        g = clamp((y - 905) / 45)
        a = 1 - clamp((y - 965) / 45)
        gota(ctx, x, y, 40, col=mezcla(ACIDO, GRIS_N, g), cara=CARA_APAGADA if g > 0.5 else CARA_ACIDO, a=a)
        if y > 950:
            anillo(ctx, x, 955, clamp((y - 950) / 60), 20, 80, AMARILLO, 7)


def bicarbonatos(ctx, t):
    if t < T_ESCOND - 0.1:
        return
    a = prog(t, T_ESCOND - 0.1, 0.4)
    for i, (x, y) in enumerate(BICAS):
        bicarbonato(ctx, x + 5 * math.sin(t * 2 + i), y + 4 * math.sin(t * 2.6 + i), 24,
                    pop(t, T_ESCOND - 0.1 + 0.07 * i, 0.35), a)
    x, y = GOTA_B                                # el que sale al cruce de la gota
    if t < T_NEU:
        yy = lerp(y, 1005, prog(t, T_NEU - 0.9, 0.7))
        bicarbonato(ctx, x, yy, 24, pop(t, T_ESCOND, 0.35) * bump(t, T_CONTR - 0.1, 0.4, 0.3), a)


def d_corte(ctx, t):
    z = (1 + 0.3 * (prog(t, b(7), 0.7) - prog(t, b(9) - 0.05, 0.6))
         + 0.12 * (prog(t, b(12), 0.8) - prog(t, b(13) - 0.1, 0.5)))
    ctx.save()
    zoom(ctx, z, 540, 1000)
    fondo(ctx, t, 0.2)
    g = cairo.LinearGradient(0, 0, 0, 1100)
    g.add_color_stop_rgba(0, *ACIDO, 0.08)
    g.add_color_stop_rgba(1, *ACIDO, 0.26)
    ctx.rectangle(-400, -400, 1900, 1500)
    ctx.set_source(g)
    ctx.fill()
    for x, ph, v, r in BURB_C:                   # burbujas del ácido
        q = (t * v + ph) % 1.0
        ctx.arc(x + 12 * math.sin(q * 7 + x), lerp(880, 120, q), r, 0, TAU)
        ctx.set_source_rgba(*ACIDO_CLARO, 0.35 * (1 - q))
        ctx.fill()
    gotas_fondo(ctx, t)
    tejido(ctx)
    celulas(ctx, t)
    moco(ctx, t)
    bicarbonatos(ctx, t)
    gotas(ctx, t)
    ctx.restore()
    if b(12) <= t < b(13) + 0.4:                 # el último recurso: alarma roja
        a = prog(t, b(12), 0.4) * sale(t, b(13), 0.4) * (0.5 + 0.5 * math.sin(t * 6))
        ctx.set_source_rgba(0.9, 0.1, 0.15, 0.16 * a)
        ctx.paint()
    # carteles
    kartel(ctx, "NUNCA LO TOCA", 540, 320, 80, t, T_TOQUE - 0.1, b(5) + 0.5, rot=-2)
    kartel(ctx, "CAPA DE MOCO", 540, 320, 84, t, T_MOCO - 0.15, b(6) + 0.1, box=MOCO, rot=-2)
    kartel(ctx, "ÁCIDO", 270, 560, 72, t, T_ACIDO6 - 0.1, b(7) + 0.2, box=ACIDO, rot=-4)
    kartel(ctx, "PARED", 300, 1240, 64, t, T_PARED6 - 0.1, b(7) + 0.2, box=CELULA, rot=3)
    kartel(ctx, "BICARBONATO", 540, 320, 84, t, T_BICA - 0.1, b(8) + 0.3, box=BICA, fg=BLANCO, rot=-2)
    kartel(ctx, "LO CONTRARIO DEL ÁCIDO", 540, 320, 62, t, T_CONTR - 0.1, T_NEU - 0.15, box=BLANCO, rot=-2)
    kartel(ctx, "¡NEUTRALIZADO!", 540, 320, 84, t, T_NEU, b(9) + 0.3, box=VERDE, rot=-3)
    kartel(ctx, "SE APAGA ANTES DE LLEGAR", 540, 320, 62, t, T_APAGA - 0.1, b(10) - 0.1, rot=-2)
    kartel(ctx, "NO ES PERFECTA", 540, 320, 84, t, T_MORD + 0.05, b(11) + 0.4, box=ROJO, fg=BLANCO, rot=-3)
    kartel(ctx, "SE DESGASTA", 540, 320, 90, t, T_DESG - 0.1, b(12) - 0.05, rot=-2)
    kartel(ctx, "ÚLTIMO RECURSO", 540, 430, 100, t, T_ULT - 0.1, b(13) - 0.1, box=ROJO, fg=BLANCO, rot=-4)
    kartel(ctx, "DESCARTA LAS GASTADAS", 540, 320, 66, t, T_DESC - 0.05, b(14) - 0.1, box=BLANCO, rot=-2)
    kartel(ctx, "FABRICA NUEVAS", 540, 450, 80, t, T_FABR - 0.05, b(14) - 0.1, box=VERDE, rot=3)
    if t >= T_MEDIO - 0.1:
        v = 500000 * prog(t, T_MEDIO, T_MIN - 0.2 - T_MEDIO, "out")
        s = pop(t, T_MEDIO - 0.1, 0.3) * bump(t, T_MIN - 0.15, 0.3, 0.12)
        ctx.save()
        ctx.translate(540, 420)
        ctx.scale(max(s, 0.01), max(s, 0.01))
        texto(ctx, fmt(round(v / 1000) * 1000), 0, 0, 180, fill=AMARILLO, sw=15)
        ctx.restore()
    kartel(ctx, "CÉLULAS POR MINUTO", 540, 600, 70, t, T_CEL14 - 0.05, box=BLANCO, rot=-2)


# ------------------------------------------------------------------ 6. en tres días, toda la superficie es nueva
T_DIA = [b(15, "unos"), b(15, "dias"), b(15, "superficie")]
T_RENOVO = b(15, "renovo")
POPS += T_DIA + [T_RENOVO - 0.1]


def d_renueva(ctx, t):
    fondo(ctx, t, 0.25)
    p = prog(t, T_DIA[0], T_RENOVO + 0.1 - T_DIA[0], "inout")
    xs = lerp(380, -520, p)
    listo = t >= T_RENOVO - 0.1
    cara = dict(ojos="happy", boca="grin") if listo else dict(ojos="open", boca="flat", ceja="worried")
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(15), b(16) - b(15)), 600, 900)
    estomago(ctx, X0, Y0, 1.0, t, cara=cara, pared=PARED_VIEJA, barrido=xs if p < 0.999 else None)
    ctx.restore()
    if t >= T_DIA[0] - 0.1:
        d = 1 + sum(1 for td in T_DIA[1:] if t >= td)
        tt = max(td for td in T_DIA if td <= max(t, T_DIA[0]))
        cartel(ctx, f"DÍA {d}", 540, 300, 100, s=pop(t, T_DIA[0] - 0.1) * bump(t, tt, 0.3, 0.15), rot=-3)
    kartel(ctx, "SUPERFICIE NUEVA", 540, 440, 70, t, T_RENOVO - 0.1, box=VERDE, rot=2)


# ------------------------------------------------------------------ 7. la de hoy no existía la semana pasada
T_HOY = b(16, "hoy")
T_NOEX = b(16, "no")
T_SEMANA = b(16, "semana")
POPS += [T_HOY - 0.1, T_NOEX - 0.1, T_SEMANA - 0.1]


def mini_corte(ctx, x0, y0, w, h, modo, t):
    ctx.set_source_rgba(*ACIDO, 0.22)
    ctx.paint()
    cw = w / 4
    ytop = y0 + h * 0.56
    ctx.rectangle(x0, ytop + h * 0.4, w, h)
    ctx.set_source_rgb(*TEJIDO)
    ctx.fill()
    for i in range(4):
        celula(ctx, x0 + i * cw + 3, ytop, w=cw - 6, h=h * 0.42, cara=dict(ojos="happy", boca="grin") if modo == "hoy"
               and i in (1, 2) else None, seed=i, fantasma=modo != "hoy")
    ctx.rectangle(x0, y0 + h * 0.42, w, h * 0.17)
    ctx.set_source_rgba(*MOCO, 0.7)
    ctx.fill()
    if modo == "hoy":
        carne(ctx, x0 + w * 0.5, y0 + h * 0.33, 0.55, t, rot=-0.15)
    else:
        texto(ctx, "?", x0 + w * 0.5, y0 + h * 0.25, 120, fill=BLANCO, sw=10, alpha=0.9)


def calendario(ctx, cx, cy, w, h, titulo, s, fn):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(s, s)
    rrect(ctx, -w / 2 + 10, -h / 2 + 14, w, h, 26)
    ctx.set_source_rgba(0, 0, 0, 0.45)
    ctx.fill()
    rrect(ctx, -w / 2, -h / 2, w, h, 26)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill()
    ctx.save()
    rrect(ctx, -w / 2, -h / 2, w, h, 26)
    ctx.clip()
    ctx.rectangle(-w / 2, -h / 2, w, 110)
    ctx.set_source_rgb(*ROJO)
    ctx.fill()
    ctx.restore()
    texto(ctx, titulo, 0, -h / 2 + 58, 50, fill=BLANCO, sw=7)
    ctx.save()
    rrect(ctx, -w / 2 + 20, -h / 2 + 130, w - 40, h - 150, 16)
    ctx.clip()
    fn(ctx, -w / 2 + 20, -h / 2 + 130, w - 40, h - 150)
    ctx.restore()
    rrect(ctx, -w / 2 + 20, -h / 2 + 130, w - 40, h - 150, 16)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    rrect(ctx, -w / 2, -h / 2, w, h, 26)
    ctx.set_line_width(9)
    ctx.stroke()
    for sx in (-1, 1):                           # anillas
        rrect(ctx, sx * w * 0.25 - 12, -h / 2 - 26, 24, 56, 12)
        ctx.set_source_rgb(*hx("#AEB6C8"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(6)
        ctx.stroke()
    ctx.restore()


def d_hoy(ctx, t):
    fondo(ctx, t, 0.3)
    mueve = prog(t, T_NOEX - 0.25, 0.4)
    calendario(ctx, lerp(540, 790, mueve), 860, 460, 600, "HOY", pop(t, T_HOY - 0.1, 0.4) * lerp(1.0, 0.95, mueve),
               lambda c, x0, y0, w, h: mini_corte(c, x0, y0, w, h, "hoy", t))
    calendario(ctx, 290, 860, 460, 600, "SEMANA PASADA", pop(t, T_NOEX - 0.1, 0.4) * 0.95,
               lambda c, x0, y0, w, h: mini_corte(c, x0, y0, w, h, "antes", t))
    kartel(ctx, "NO EXISTÍA", 290, 1245, 66, t, T_SEMANA - 0.1, box=ROJO, fg=BLANCO, rot=-3)
    kartel(ctx, "TOCA TU COMIDA", 790, 1245, 56, t, T_HOY + 0.3, box=BLANCO, rot=3)


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_inicio),
    (b(1) - 0.08, d_carne),
    (b(2) - 0.08, d_tambien),
    (b(3) - 0.08, d_porque),
    (b(4) - 0.08, d_corte),
    (b(15) - 0.08, d_renueva),
    (b(16) - 0.08, d_hoy),
    (b(17) - 0.08, d_cierre),
]
CONTINUAS = {d_carne, d_tambien, d_porque}
XF = 0.18
WHOOSH += [t0 for t0, fn in ESCENAS[1:] if fn not in CONTINUAS]


def punch(t, t0, d=0.3, amp=0.06):
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


def escena(t):
    return max(k for k, (t0, _) in enumerate(ESCENAS) if t >= t0)


def componer(ctx, t):
    i = escena(t)
    t0, fn = ESCENAS[i]
    dt = t - t0
    if fn in CONTINUAS:
        fn(ctx, t)
        return
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


# ------------------------------------------------------------------ sonido
def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    for i, t0 in enumerate(WHOOSH):
        ev(t0, "whoosh" if i % 2 else "whoosh_suave", 0.6)
    for t0 in POPS:
        ev(t0, "pop", 0.55)
    ev(0.05, "siseo", 0.22, d=1.4)
    ev(T_CORROER, "siseo", 0.35, d=1.0)
    ev(b(1), "whoosh_suave", 0.45)
    ev(T_DESH, "plop", 0.8)
    ev(T_DESH + 0.05, "siseo", 0.4, d=1.4)
    ev(T_CARNE2 - 0.05, "boing", 0.4)
    ev(b(3) + 0.2, "zumbido", 0.15, d=1.2)
    ev(b(4) - 0.55, "zoom", 0.7)
    for i in range(len(REPOSO)):
        ev(REPOSO[i][1], "whoosh_suave", 0.25)
    ev(T_TOQUE, "frenada", 0.45, d=0.35)
    ev(T_POUR, "vertido", 0.5, d=1.2)
    ev(b(7), "zoom", 0.5)
    ev(T_ESCOND - 0.1, "brote", 0.4, d=0.8)
    ev(T_NEU, "ding", 0.65)
    ev(T_NEU, "chispa", 0.35, d=0.5)
    for x, t0 in GOTAS_C:
        ev(t0 + 0.95, "tick", 0.4, f=1500, d=0.07)
    ev(T_D0, "whoosh_suave", 0.4)
    ev(T_MORD, "crunch", 0.6, d=0.35)
    ev(b(11) + 0.1, "zumbido", 0.12, d=1.6)
    ev(b(12), "subida", 0.4, d=1.3)
    ev(T_ULT - 0.1, "golpe", 0.8)
    for i, ts in T_SHED.items():
        ev(ts, "pop", 0.22)
        ev(ts + 0.15, "plop", 0.18)
    for k in range(int((T_MIN - T_MEDIO) / 0.07)):
        ev(T_MEDIO + k * 0.07, "tick", 0.14, f=1800 + 25 * k, d=0.025)
    ev(T_MIN - 0.15, "ding", 0.5)
    ev(T_DIA[0], "subida", 0.35, d=T_RENOVO - T_DIA[0])
    ev(T_RENOVO - 0.1, "ding", 0.55)
    ev(T_NOEX - 0.25, "whoosh_suave", 0.4)
    ev(b(17) + 0.1, "chispa", 0.25, d=0.8)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "por_que_tu_estomago_no_se_digiere.mp4"))
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

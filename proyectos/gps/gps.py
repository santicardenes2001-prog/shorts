"""Short "¿Cómo sabe tu celular dónde estás?" — animación procedural (mismo armazón que cielo.py).

Toda la explicación cuelga de una comparación: contar los segundos entre el rayo y el trueno. El celular hace esa
cuenta con cuatro satélites que llevan relojes. El último cuadro es igual al primero (loop).

    python proyectos/gps/gps.py --fotos 0,5.5,14
    python proyectos/gps/gps.py            # render completo -> salidas/como_sabe_tu_celular_donde_estas.mp4
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
for _p in (ROOT, os.path.join(ROOT, "proyectos", "pantalla"), os.path.join(ROOT, "proyectos", "picante"),
           os.path.join(ROOT, "proyectos", "cielo")):
    sys.path.insert(0, _p)
import kit  # noqa: E402
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
import cielo as C  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, bump, cartel, clamp, ease, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rng, rrect, texto)
from picante import _elipse_suave, capa, carita, fondo_azul  # noqa: E402
from cielo import (CIAN, GRIS, LUZ, ROJO, VERDE, cruz, estrella, punteada, sale, tachado, tierra, tilde,  # noqa: E402
                   zoom)

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Tu celular te ubica con relojes que flotan en el espacio.",             # b0
    "Funciona como contar los segundos después de un rayo.",                 # b1
    "Ves el rayo, cuentas, y llega el trueno.",                              # b2
    "Cuanto más tarda, más lejos cayó.",                                     # b3
    "Tu celular hace esa misma cuenta con satélites.",                       # b4
    "Sobre tu cabeza giran unos treinta.",                                   # b5
    "Cada uno lleva un reloj y transmite su hora sin parar.",                # b6
    "Esa señal baja hasta ti a la velocidad de la luz.",                     # b7
    "Tu celular mira cuánto tardó en llegar.",                               # b8
    "Con ese tiempo calcula a qué distancia está el satélite.",              # b9
    "Un solo satélite no alcanza.",                                          # b10
    "Sabrías la distancia, pero no hacia qué lado.",                         # b11
    "Por eso tu celular escucha cuatro a la vez.",                           # b12
    "Solo hay un lugar que coincide con las cuatro distancias.",             # b13
    "Ese lugar eres tú.",                                                    # b14
    "Para que funcione, los relojes tienen que ser casi perfectos.",         # b15
    "Si uno falla una millonésima de segundo, hay problemas.",               # b16
    "Apareces a trescientos metros de donde estás.",                         # b17
    "Son tan exactos que detectan algo increíble.",                          # b18
    "Allá arriba, el tiempo pasa más rápido que en el suelo.",               # b19
    "Einstein lo predijo, y el sistema lo corrige todos los días.",          # b20
    "Sin esa corrección, tu mapa fallaría por kilómetros.",                  # b21
    "Todo eso ocurre cada vez que abres el mapa:",                           # b22
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


AZUL = hx("#2F7BFF")
AZUL_PANEL = hx("#3D62D9")
METAL = hx("#E4E9F2")
ORO = hx("#F2C14E")
NUBE = hx("#5B6584")
MAPA_F = hx("#103039")
MAPA_C = hx("#2B6B78")
MAPA_V = hx("#1E5B45")
KF = 60 * round(14 * TOTAL / 60) / (14 * TOTAL)
POPS, WHOOSH = [], []                        # momentos de carteles, para los efectos


def fondo(ctx, t, oscuro=0.0):
    fondo_azul(ctx, t * KF)
    if oscuro > 0:
        ctx.set_source_rgba(*C.NOCHE, oscuro)
        ctx.paint()


def per(t, k, ph=0.0):
    """Vaivén que cierra justo en el loop."""
    return math.sin(TAU * k * t / TOTAL + ph)


def campo(ctx, t, seed=7, n=60, a=1.0, y1=1300):
    for x, y, r, ph, k in C.campo_pts(seed, n, y1):
        estrella(ctx, x, y, r, a * (0.72 + 0.28 * per(t, k, ph)), halo=0.7)


def kartel(ctx, txt, x, y, size, t, t0, t1=None, **kw):
    """Cartel que entra con rebote en t0 y sale en t1."""
    if t < t0:
        return
    s = pop(t, t0) * (sale(t, t1) if t1 is not None else 1.0)
    cartel(ctx, txt, x, y, size, s=s, **kw)


# ------------------------------------------------------------------ piezas
def reloj(ctx, x, y, R, t, vel=1.0, ojos=None, boca="smile", ceja=None, look=(0, 0), a=1.0, marco=METAL, salto=0.0):
    """Reloj redondo; con ojos = tiene cara (debajo de las agujas)."""
    if R <= 1 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.push_group()
    ctx.arc(0, 0, R, 0, TAU)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(3, R * 0.13))
    ctx.stroke()
    ctx.arc(0, 0, R * 0.93, 0, TAU)
    ctx.set_source_rgb(*marco)
    ctx.set_line_width(max(2, R * 0.07))
    ctx.stroke()
    for i in range(12):
        an = TAU * i / 12
        ctx.move_to(R * 0.74 * math.cos(an), R * 0.74 * math.sin(an))
        ctx.line_to(R * 0.84 * math.cos(an), R * 0.84 * math.sin(an))
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(1.5, R * 0.045))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    if ojos:
        carita(ctx, 0, R * 0.2, R * 0.62, R / 170, ojos=ojos, boca=boca, ceja=ceja, look=look, rubor=True)
    for L, w, v in ((0.62, 0.06, 6.0), (0.4, 0.085, 0.5)):
        an = t * v * vel - math.pi / 2 + salto
        ctx.move_to(0, -R * 0.2 if ojos else 0)
        ctx.line_to(R * L * math.cos(an) * (0.6 if ojos else 1), (-R * 0.2 if ojos else 0) + R * L * math.sin(an) * (0.6 if ojos else 1))
        ctx.set_line_width(max(2, R * w))
        ctx.set_source_rgb(*ROJO if v > 1 else INK)
        ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def satelite(ctx, x, y, s, t, vel=1.0, ojos="open", boca="smile", ceja=None, look=(0, 0.6), a=1.0, simple=False):
    """Satélite con paneles; su cuerpo es un reloj con cara."""
    if s <= 0.01 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.push_group()
    for sg in (-1, 1):                           # paneles
        ctx.rectangle(sg * 96 - (0 if sg > 0 else 150), -44, 150, 88)
        ctx.set_source_rgb(*AZUL_PANEL)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(9)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
        if not simple:
            for i in range(1, 3):
                xx = sg * 96 + sg * 50 * i
                ctx.move_to(xx, -44)
                ctx.line_to(xx, 44)
            ctx.move_to(sg * 96, 0)
            ctx.line_to(sg * 246, 0)
            ctx.set_source_rgba(*INK, 0.7)
            ctx.set_line_width(4)
            ctx.stroke()
    ctx.move_to(0, 90)                           # antena hacia abajo
    ctx.line_to(0, 150)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(12)
    ctx.stroke()
    ctx.arc(0, 150, 26, 0, math.pi)
    ctx.close_path()
    ctx.set_source_rgb(*ORO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()
    reloj(ctx, x, y, 100 * s, t, vel=vel, ojos=None if simple else ojos, boca=boca, ceja=ceja, look=look, a=a, marco=ORO)


def mini_sat(ctx, x, y, s, a=1.0):
    if a <= 0.01 or s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.rectangle(-30, -7, 60, 14)
    ctx.set_source_rgba(*AZUL_PANEL, a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.arc(0, 0, 11, 0, TAU)
    ctx.set_source_rgba(*BLANCO, a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.stroke()
    ctx.restore()


def punto_azul(ctx, x, y, t, s=1.0, a=1.0, col=AZUL):
    if s <= 0.01 or a <= 0.01:
        return
    q = (t * 0.9) % 1.0
    ctx.arc(x, y, (26 + 60 * q) * s, 0, TAU)
    ctx.set_source_rgba(*col, 0.35 * (1 - q) * a)
    ctx.fill()
    ctx.arc(x, y, 26 * s, 0, TAU)
    ctx.set_source_rgba(*BLANCO, a)
    ctx.fill()
    ctx.arc(x, y, 19 * s, 0, TAU)
    ctx.set_source_rgba(*col, a)
    ctx.fill()


def mapa(ctx, x0, y0, w, h, paso=120, ox=0.0, oy=0.0, r=0, borde=True):
    """Mapa de calles visto desde arriba, recortado al rectángulo."""
    ctx.save()
    rrect(ctx, x0, y0, w, h, r)
    ctx.clip()
    ctx.set_source_rgb(*MAPA_F)
    ctx.paint()
    rg = rng(3)
    nx, ny = int(w / paso) + 3, int(h / paso) + 3
    for i in range(-1, nx):
        for j in range(-1, ny):
            if rg.uniform() < 0.16:
                ctx.rectangle(x0 + ox % paso + i * paso + 12, y0 + oy % paso + j * paso + 12, paso - 24, paso - 24)
                ctx.set_source_rgb(*MAPA_V)
                ctx.fill()
    ctx.set_source_rgb(*MAPA_C)
    ctx.set_line_width(max(5, paso * 0.13))
    for i in range(-1, nx):
        xx = x0 + ox % paso + i * paso
        ctx.move_to(xx, y0 - 5)
        ctx.line_to(xx, y0 + h + 5)
    for j in range(-1, ny):
        yy = y0 + oy % paso + j * paso
        ctx.move_to(x0 - 5, yy)
        ctx.line_to(x0 + w + 5, yy)
    ctx.stroke()
    ctx.set_source_rgba(*hx("#3F8E9E"), 0.9)          # una avenida en diagonal
    ctx.set_line_width(max(7, paso * 0.2))
    ctx.move_to(x0 - 20, y0 + h * 0.82 + oy * 0.2)
    ctx.line_to(x0 + w + 20, y0 + h * 0.3 + oy * 0.2)
    ctx.stroke()
    ctx.restore()
    if borde:
        rrect(ctx, x0, y0, w, h, r)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(10)
        ctx.stroke()


def telefono(ctx, x, y, s, t, contenido=None, cara=None, rot=0.0, a=1.0):
    """Celular de 250x460. contenido(ctx) dibuja la pantalla en (-108..108, -200..200)."""
    if s <= 0.01 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.scale(s, s)
    ctx.push_group()
    rrect(ctx, -125 + 8, -230 + 12, 250, 460, 40)
    ctx.set_source_rgba(0, 0, 0, 0.4)
    ctx.fill()
    rrect(ctx, -125, -230, 250, 460, 40)
    ctx.set_source_rgb(*hx("#1C2033"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(10)
    ctx.stroke()
    ctx.save()
    rrect(ctx, -108, -204, 216, 408, 24)
    ctx.clip()
    ctx.set_source_rgb(*hx("#22305E"))
    ctx.paint()
    if contenido:
        contenido(ctx)
    ctx.restore()
    if cara:
        carita(ctx, 0, -10, 96, 0.8, **cara)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def pantalla_mapa(t, dx=0.0, dy=0.0):
    def f(ctx):
        mapa(ctx, -108, -204, 216, 408, paso=62, borde=False)
        punto_azul(ctx, dx, 20 + dy, t, 0.62)
    return f


def nube(ctx, x, y, s, t, ojos="open", boca="wavy", ceja="angry", a=1.0):
    if s <= 0.01 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.push_group()
    for cx, cy, r in ((-150, 20, 90), (-60, -50, 120), (70, -40, 110), (160, 20, 85), (0, 40, 120)):
        ctx.arc(cx, cy, r + 8, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    for cx, cy, r in ((-150, 20, 90), (-60, -50, 120), (70, -40, 110), (160, 20, 85), (0, 40, 120)):
        ctx.arc(cx, cy, r, 0, TAU)
    ctx.set_source_rgb(*NUBE)
    ctx.fill()
    carita(ctx, 0, 0, 130, 1.05, ojos=ojos, boca=boca, ceja=ceja)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def rayo(ctx, x, y0, y1, a=1.0, ancho=1.0):
    if a <= 0.01:
        return
    pts = [(0, 0), (-60, 0.42), (10, 0.40), (-50, 1.0), (70, 0.52), (0, 0.55), (60, 0)]
    for lw, col, fill in ((18, INK, False), (0, AMARILLO, True)):
        ctx.move_to(x + pts[0][0] * ancho, y0)
        for dx, f in pts[1:]:
            ctx.line_to(x + dx * ancho, lerp(y0, y1, f))
        ctx.close_path()
        if fill:
            ctx.set_source_rgba(*AMARILLO, a)
            ctx.fill()
        else:
            ctx.set_source_rgba(*INK, a)
            ctx.set_line_width(lw)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.stroke()


def casa(ctx, x, y, s, ojos="open", boca="smile", ceja=None, look=(0.6, -0.3)):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.rectangle(-110, -150, 220, 150)
    ctx.set_source_rgb(*hx("#F0D9A8"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(10)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.move_to(-140, -150)
    ctx.line_to(0, -270)
    ctx.line_to(140, -150)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#D9534F"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    carita(ctx, 0, -95, 90, 0.72, ojos=ojos, boca=boca, ceja=ceja, look=look)
    ctx.restore()


def ondas(ctx, x, y, t, t0, n=3, R=260, col=CIAN, a=1.0, a0=0.0, a1=TAU, vel=1.0, w=8):
    """Anillos que se alejan del punto."""
    for i in range(n):
        q = ((t - t0) * vel - i / n) % 1.0
        if t < t0 + i / (n * vel):
            continue
        ctx.new_sub_path()
        ctx.arc(x, y, 20 + R * q, a0, a1)
        ctx.set_source_rgba(*col, 0.85 * (1 - q) * a)
        ctx.set_line_width(w)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()


def suelo(ctx, y=1330, a=1.0):
    """Horizonte curvo de la Tierra."""
    ctx.arc(540, y + 2300, 2300, 0, TAU)
    ctx.set_source_rgba(*hx("#123B7A"), a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*hx("#3D8BFF"), a)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.save()
    ctx.arc(540, y + 2300, 2296, 0, TAU)
    ctx.clip()
    for cx, cy, rx, ry in ((200, y + 90, 230, 60), (860, y + 70, 260, 50), (560, y + 230, 300, 70)):
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(rx, ry)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.set_source_rgba(*hx("#1E6B4A"), a)
        ctx.fill()
    ctx.restore()


# ------------------------------------------------------------------ Vos (solo en la apertura y en el empalme)
@functools.lru_cache(maxsize=None)
def vos_surface(ojos):
    body = kit.vos(eyes=ojos, brows="up", mouth_kind="smile", look=(0.9, 0.1))
    png = cairosvg.svg2png(bytestring=kit.svg(520, 820, body).encode(), output_width=1040, output_height=1640)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


def vos(ctx, x, y, k=1.0, ojos="open"):
    sf = vos_surface(ojos)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(k / 2, k / 2)
    ctx.translate(-520, -1612)
    ctx.set_source_surface(sf, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint()
    ctx.restore()


# ------------------------------------------------------------------ 1 y 12. apertura / empalme
SATS0 = [(210, 470, 0.62, 0.0), (540, 330, 0.78, 2.1), (870, 480, 0.62, 4.2)]
TEL0 = (770, 1040)
VOS0 = (380, 1345)


def apertura(ctx, t, ent=1.0, senal=1.0):
    fondo(ctx, t, 0.3)
    campo(ctx, t, 7, 55, 1.0, y1=1150)
    suelo(ctx, 1330 + 700 * (1 - ent))
    for i, (x, y, s, ph) in enumerate(SATS0):
        yy = y + 14 * per(t, 9, ph)
        se = pop(ent * 1.0, 0.25 + 0.12 * i, 0.45) if ent < 1 else 1.0
        if senal > 0.01 and se > 0.9:
            punteada(ctx, x, yy + 100 * s, TEL0[0], TEL0[1] - 250, CIAN, w=6, a=0.55 * senal, fase=-t * 70)
        satelite(ctx, x, yy, s * se, t, look=(0.3 * (1 - i), 0.7))
    if ent > 0.35:
        ctx.save()
        ctx.rectangle(0, 0, W, 2000)
        ctx.clip()
        vos(ctx, VOS0[0], VOS0[1] + 700 * (1 - ent), 0.5, ojos="closed" if (t % 3.3) > 3.18 and ent >= 1 else "open")
        ctx.restore()
    ts = pop(ent, 0.45, 0.5) if ent < 1 else 1.0
    telefono(ctx, TEL0[0], TEL0[1] + 10 * per(t, 7), 0.92 * ts, t, contenido=pantalla_mapa(t), rot=5)


T_UBICA = b(0, "ubica")
T_RELOJES0 = b(0, "relojes")
T_ESPACIO = b(0, "espacio")
POPS += [T_RELOJES0 - 0.15]


def d_inicio(ctx, t):
    ctx.save()
    zoom(ctx, 1 + 0.035 * prog(t, 0, b(1)), 540, 900)
    apertura(ctx, t)
    for i, (x, y, s, ph) in enumerate(SATS0):       # los relojes saltan cuando se los nombra
        k = bump(t, T_RELOJES0 - 0.1 + 0.1 * i, 0.4, 0.3)
        if k > 1.001:
            ctx.arc(x, y + 14 * per(t, 9, ph), 100 * s * k + 8, 0, TAU)
            ctx.set_source_rgba(*AMARILLO, 0.9)
            ctx.set_line_width(9)
            ctx.stroke()
    ctx.restore()
    kartel(ctx, "RELOJES EN EL ESPACIO", 540, 700, 66, t, T_RELOJES0 - 0.15, b(1) - 0.25, rot=-2)


def d_cierre(ctx, t):
    ent = prog(t, b(22) + 0.05, 1.5, "out")
    ctx.save()
    zoom(ctx, 1 + 0.035 * (1 - prog(t, b(22), TOTAL - b(22))), 540, 900)
    apertura(ctx, t, ent=ent, senal=prog(t, b(22) + 1.3, 0.5))
    ctx.restore()


# ------------------------------------------------------------------ 2. el rayo y el trueno
T_SEG = b(1, "segundos")
T_RAYO1 = b(1, "rayo")
T_RAYO2 = b(2, "rayo")
T_CUENTAS = b(2, "cuentas")
T_TRUENO = b(2, "trueno")
T_TARDA3 = b(3, "tarda")
T_LEJOS = b(3, "lejos")
CASA = (190, 1230)
POPS += [T_SEG - 0.1, T_CUENTAS, T_CUENTAS + 0.3, T_CUENTAS + 0.6, T_LEJOS - 0.1]


def d_rayo(ctx, t):
    fondo(ctx, t, 0.55)
    lejos = prog(t, b(3) - 0.05, T_LEJOS + 0.4 - b(3), "inout")
    nx = lerp(620, 860, lejos)
    destello = max(1 - clamp((t - T_RAYO1) / 0.25), 1 - clamp((t - T_RAYO2) / 0.25) if t >= T_RAYO2 else 0)
    if t < T_RAYO1:
        destello = 0
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(1), b(4) - b(1)), 540, 900)
    # suelo
    ctx.rectangle(-40, 1230, 1200, 800)
    ctx.set_source_rgb(*hx("#0D1A33"))
    ctx.fill()
    ctx.move_to(-40, 1230)
    ctx.line_to(1120, 1230)
    ctx.set_source_rgb(*hx("#2B3A78"))
    ctx.set_line_width(6)
    ctx.stroke()
    asust = T_RAYO1 <= t < T_RAYO1 + 0.7 or T_TRUENO - 0.05 <= t < T_TRUENO + 0.9
    casa(ctx, CASA[0], CASA[1], 1.0 * pop(t, b(1), 0.4), ojos="wide" if asust else "open", boca="o" if asust else "smile",
         look=(0.8, -0.5))
    en = pop(t, b(1) + 0.1, 0.45)
    nube(ctx, nx, 470, 0.95 * en, t)
    dur = 0.55
    for tr in (T_RAYO1, T_RAYO2):
        if tr <= t < tr + dur:
            rayo(ctx, nx + 10, 560, 1228, a=1 - clamp((t - tr - 0.3) / 0.25), ancho=1.2)
    if t >= b(3):                                   # en b3 el rayo cae cada vez más lejos
        k = (t - b(3)) % 0.9
        if k < 0.3:
            rayo(ctx, nx + 10, 560, 1228, a=1 - clamp((k - 0.15) / 0.15), ancho=1.2)
    # el trueno viaja hasta la casa
    if t >= T_TRUENO - 0.5 and t < b(3):
        q = clamp((t - (T_TRUENO - 0.5)) / 0.5)
        for i in range(3):
            xx = lerp(nx - 40, CASA[0] + 160, q) + 34 * i
            ctx.new_sub_path()
            ctx.arc(xx + 130, 1040, 130, math.radians(140), math.radians(220))
            ctx.set_source_rgba(*BLANCO, 0.8 - 0.2 * i)
            ctx.set_line_width(12)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
    # la distancia, en b3
    if t >= b(3):
        yl = 1300
        for lw, col in ((22, INK), (10, AMARILLO)):
            ctx.move_to(CASA[0], yl)
            ctx.line_to(lerp(CASA[0] + 40, nx + 10, prog(t, b(3), 0.3, "out")), yl)
            ctx.set_line_width(lw)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_source_rgb(*col)
            ctx.stroke()
    ctx.restore()
    if destello > 0.01:
        ctx.set_source_rgba(1, 1, 0.9, 0.32 * destello)
        ctx.paint()
    kartel(ctx, "CONTAR LOS SEGUNDOS", 540, 760, 64, t, T_SEG - 0.1, T_RAYO2 - 0.2, box=BLANCO, rot=-2)
    for i in range(3):                              # 1, 2, 3...
        ti = T_CUENTAS + 0.3 * i
        if ti <= t < b(3):
            s = pop(t, ti, 0.25) * sale(t, b(3) - 0.2)
            ctx.save()
            ctx.translate(330 + 150 * i, 800)
            ctx.scale(max(s, 0.01), max(s, 0.01))
            texto(ctx, str(i + 1), 0, 0, 170, fill=AMARILLO, sw=14)
            ctx.restore()
    if T_TRUENO - 0.05 <= t < b(3):
        s = pop(t, T_TRUENO - 0.05, 0.25) * sale(t, b(3) - 0.2)
        cartel(ctx, "¡BRUUUM!", 560 + 8 * math.sin(t * 50), 1010, 100, box=ROJO, fg=BLANCO, s=s, rot=-6)
    if t >= b(3):
        seg = 1 + 4 * lejos
        ctx.save()
        ctx.translate(540, 800)
        s = pop(t, b(3), 0.3)
        ctx.scale(max(s, 0.01), max(s, 0.01))
        texto(ctx, f"{seg:.0f} s", 0, 0, 190, fill=AMARILLO, sw=15)
        ctx.restore()
        kartel(ctx, "MÁS TARDA = MÁS LEJOS", 540, 300, 66, t, T_LEJOS - 0.1, rot=-2)


# ------------------------------------------------------------------ 3. la misma cuenta, con satélites
T_MISMA = b(4, "misma")
T_SATS4 = b(4, "satelites")
POPS += [T_MISMA - 0.1, T_SATS4 - 0.15]


def d_misma(ctx, t):
    fondo(ctx, t, 0.4)
    campo(ctx, t, 11, 45, 0.8, y1=1300)
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(4), b(5) - b(4)), 540, 900)
    cambio = prog(t, T_SATS4 - 0.2, 0.35)
    nube(ctx, 540, 430, 0.8 * (1 - cambio) * pop(t, b(4) - 0.05, 0.3), t, a=1 - cambio)
    satelite(ctx, 540, 430, 1.25 * pop(t, T_SATS4 - 0.15, 0.4), t)
    punteada(ctx, 540, 640, 540, 880, CIAN, w=8, a=0.7 * prog(t, T_SATS4 + 0.1, 0.3), fase=-t * 70)
    telefono(ctx, 540, 1130, 0.95 * pop(t, b(4) + 0.0, 0.4), t, cara=dict(ojos="open", boca="grin", look=(0, -0.9)))
    ctx.restore()
    kartel(ctx, "LA MISMA CUENTA", 540, 760, 76, t, T_MISMA - 0.1, rot=-3)


# ------------------------------------------------------------------ 4. giran unos treinta
T_GIRAN = b(5, "giran")
T_30 = b(5, "treinta")
ORBITAS = [(-28, 0.0), (32, 1.1), (90, 2.3)]
POPS += [T_30 - 0.1, T_30 + 0.35]


def d_treinta(ctx, t):
    fondo(ctx, t, 0.45)
    campo(ctx, t, 13, 45, 0.7, y1=1350)
    cx, cy, R = 540, 880, 185
    ctx.save()
    zoom(ctx, 1 + 0.05 * prog(t, b(5), b(6) - b(5)), cx, cy)
    en = prog(t, b(5) + 0.1, 0.6, "out")
    sats = []
    for oi, (rot, ph) in enumerate(ORBITAS):
        ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(math.radians(rot))
        ctx.scale(430, 135)
        ctx.arc(0, 0, 1, 0, TAU)
        ctx.restore()
        ctx.set_source_rgba(*CIAN, 0.28 * en)
        ctx.set_line_width(4)
        ctx.stroke()
        for j in range(10):
            an = TAU * j / 10 + ph + (t - b(5)) * 0.9
            ex, ey = 430 * math.cos(an), 135 * math.sin(an)
            x, y = cx + ex * ca - ey * sa, cy + ex * sa + ey * ca
            sats.append((math.sin(an) < 0, x, y, pop(t, b(5) + 0.1 + 0.025 * (oi * 10 + j), 0.3)))
    for atras, x, y, s in sats:
        if atras:
            mini_sat(ctx, x, y, 0.8 * s, 0.8)
    tierra(ctx, cx, cy, R, t, ojos="open", boca="smile", look=(0.7 * math.cos(t * 2.2), -0.6))
    for atras, x, y, s in sats:
        if not atras:
            mini_sat(ctx, x, y, 1.0 * s)
    ctx.restore()
    kartel(ctx, "31 SATÉLITES GPS", 540, 320, 86, t, T_30 - 0.1, rot=-3)
    kartel(ctx, "A 20.200 KM DE ALTURA", 540, 1330, 56, t, T_30 + 0.35, box=BLANCO, rot=2)


# ------------------------------------------------------------------ 5. el reloj, la señal y la distancia
SAT = (540, 400)
TEL = (540, 1140)
T_RELOJ6 = b(6, "reloj")
T_TRANS = b(6, "transmite")
T_HORA = b(6, "hora")
T_BAJA = b(7, "baja")
T_VEL = b(7, "velocidad")
T_LUZ7 = b(7, fin=True)
T_MIRA = b(8, "mira")
T_TARDO = b(8, "tardo")
T_TIEMPO9 = b(9, "tiempo")
T_DIST9 = b(9, "distancia")
POPS += [T_RELOJ6 - 0.1, T_VEL - 0.1, T_TARDO - 0.1, T_TIEMPO9 - 0.1, T_DIST9 - 0.1]


def hora_txt(t):
    s = int(t * 1.0) % 60
    return f"12:00:{s:02d}"


def d_senal(ctx, t):
    fondo(ctx, t, 0.45)
    campo(ctx, t, 17, 40, 0.6, y1=900)
    z = 1 + 0.05 * prog(t, b(6), b(10) - b(6))
    ctx.save()
    zoom(ctx, z, 540, 800)
    baja_cam = prog(t, b(7) - 0.2, 0.6)               # en b6 el satélite está grande y centrado
    sx, sy = SAT[0], lerp(700, SAT[1], baja_cam)
    ss = lerp(1.9, 1.15, baja_cam)
    # transmite su hora: anillos y cartelitos con la hora
    if t >= T_TRANS - 0.1:
        ondas(ctx, sx, sy + 150 * ss, t, T_TRANS - 0.1, n=3, R=lerp(430, 300, baja_cam), a=0.8, a0=math.radians(25),
              a1=math.radians(155), vel=0.9)
    if T_HORA - 0.2 <= t < b(7) + 0.2:
        for i, (dx, rot) in enumerate(((-300, -8), (0, 0), (300, 8))):
            q = ((t - T_HORA + 0.2) * 0.8 + i * 0.33) % 1.0
            cartel(ctx, hora_txt(t * 3), sx + dx * q, sy + 190 * ss + 330 * q, 44, box=BLANCO, s=min(1, q * 5) * (1 - q) ** 0.5 *
                   sale(t, b(7) - 0.1, 0.3), rot=rot)
    satelite(ctx, sx, sy, ss * pop(t, b(6), 0.4) * bump(t, T_RELOJ6 - 0.05, 0.4, 0.14), t, vel=1.4,
             boca="grin" if t >= T_TRANS else "smile")
    # el celular abajo
    tel_s = pop(t, b(7) - 0.1, 0.4)
    midiendo = t >= T_MIRA - 0.1

    def cont(c2):
        c2.set_source_rgb(*hx("#152046"))
        c2.paint()
        if midiendo:
            v = 0.067 * prog(t, T_MIRA, T_TARDO + 0.3 - T_MIRA, "out")
            texto(c2, f"{v:.3f}".replace(".", ","), 0, -40, 62, fill=AMARILLO, sw=6)
            texto(c2, "segundos", 0, 30, 34, fill=BLANCO, sw=4)

    # el pulso que baja
    if t >= T_BAJA - 0.1:
        p = clamp((t - (T_BAJA - 0.1)) / (T_LUZ7 + 0.1 - (T_BAJA - 0.1)))
        punteada(ctx, sx, sy + 180 * ss, TEL[0], TEL[1] - 240, CIAN, w=7, a=0.6, fase=-t * 90)
        if p < 1:
            yy = lerp(sy + 190 * ss, TEL[1] - 250, ease(p, "inout"))
            C.foton(ctx, sx, yy, math.pi / 2, r=30, cola=200, con_cara=True)
        elif t < T_LUZ7 + 0.6:
            q = clamp((t - T_LUZ7 - 0.1) / 0.5)
            ctx.arc(TEL[0], TEL[1], 240 + 120 * q, 0, TAU)
            ctx.set_source_rgba(*CIAN, 0.8 * (1 - q))
            ctx.set_line_width(10)
            ctx.stroke()
    telefono(ctx, TEL[0], TEL[1], 0.9 * tel_s, t, contenido=cont,
             cara=None if midiendo else dict(ojos="open", boca="smile", look=(0, -0.9)))
    # la regla de la distancia
    if t >= T_DIST9 - 0.3:
        p = prog(t, T_DIST9 - 0.3, 0.6, "out")
        x = 190
        y0, y1 = sy + 60, TEL[1] - 150
        for lw, col in ((24, INK), (11, AMARILLO)):
            ctx.move_to(x, y0)
            ctx.line_to(x, lerp(y0, y1, p))
            ctx.set_line_width(lw)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_source_rgb(*col)
            ctx.stroke()
        for yy in (y0, y1):
            if yy <= lerp(y0, y1, p) + 1:
                ctx.move_to(x - 34, yy)
                ctx.line_to(x + 34, yy)
                ctx.set_source_rgb(*AMARILLO)
                ctx.set_line_width(11)
                ctx.stroke()
    ctx.restore()
    kartel(ctx, "LLEVA UN RELOJ", 540, 300, 74, t, T_RELOJ6 - 0.1, b(7) - 0.2, rot=-2)
    kartel(ctx, "300.000 KM POR SEGUNDO", 600, 800, 52, t, T_VEL - 0.1, T_MIRA - 0.1, box=BLANCO, rot=-3)
    kartel(ctx, "TARDÓ 0,067 s", 760, 800, 60, t, T_TARDO - 0.1, T_TIEMPO9 - 0.25, rot=4)
    kartel(ctx, "TIEMPO × VELOCIDAD", 640, 720, 52, t, T_TIEMPO9 - 0.1, box=BLANCO, rot=-2)
    kartel(ctx, "= 20.200 KM", 640, 830, 78, t, T_DIST9 - 0.1, rot=2)


# ------------------------------------------------------------------ 6. un satélite no alcanza: hacen falta cuatro
U = (540, 880)                                   # donde está el celular de verdad
SATS4 = [(250, 520), (860, 600), (230, 1180), (800, 1230)]
COLS4 = [CIAN, AMARILLO, hx("#FF7AD9"), VERDE]
T_NOALC = b(10, "no")
T_DIST11 = b(11, "distancia")
T_LADO = b(11, "lado")
T_CUATRO = b(12, "cuatro")
T_COINC = b(13, "coincide")
T_TU = b(14, "tu")
POPS += [T_NOALC - 0.05, T_LADO - 0.2, T_CUATRO - 0.1, T_CUATRO + 0.1, T_CUATRO + 0.3, T_COINC - 0.1, T_TU - 0.15]


def circulo(ctx, c, r, col, p=1.0, a=1.0, w=9):
    if p <= 0.005 or a <= 0.01:
        return
    ctx.new_sub_path()
    ctx.arc(c[0], c[1], r, -math.pi / 2, -math.pi / 2 + TAU * p)
    ctx.set_source_rgba(*INK, 0.8 * a)
    ctx.set_line_width(w + 8)
    ctx.stroke_preserve()
    ctx.set_source_rgba(*col, a)
    ctx.set_line_width(w)
    ctx.stroke()


def d_circulos(ctx, t):
    ctx.save()
    zoom(ctx, 1 + 0.05 * prog(t, b(10), b(15) - b(10)), *U)
    mapa(ctx, -80, -80, 1240, 2080, paso=135, borde=False)
    ctx.set_source_rgba(*C.NOCHE, 0.35)
    ctx.paint()
    tiempos = [b(10) + 0.15, T_CUATRO - 0.1, T_CUATRO + 0.1, T_CUATRO + 0.3]
    fin_unico = prog(t, T_COINC - 0.2, 0.5)
    for i, (c, col, t0) in enumerate(zip(SATS4, COLS4, tiempos)):
        if t < t0:
            continue
        r = math.hypot(c[0] - U[0], c[1] - U[1])
        circulo(ctx, c, r, col, prog(t, t0 + 0.1, 0.7, "inout"), a=1 - 0.35 * fin_unico)
        mini = pop(t, t0, 0.35)
        ctx.arc(c[0], c[1], 58 * mini, 0, TAU)
        ctx.set_source_rgba(*INK, 0.55)
        ctx.fill()
        satelite(ctx, c[0], c[1], 0.36 * mini, t, simple=True)
    # con uno solo: podrías estar en cualquier punto del círculo
    if b(10) + 0.9 <= t < T_CUATRO + 0.3:
        c = SATS4[0]
        r = math.hypot(c[0] - U[0], c[1] - U[1])
        an = math.atan2(U[1] - c[1], U[0] - c[0]) + 2.6 * (t - (b(10) + 0.9))
        a = sale(t, T_CUATRO - 0.1, 0.4)
        for k in range(5):
            ak = an - 0.16 * k
            punto_azul(ctx, c[0] + r * math.cos(ak), c[1] + r * math.sin(ak), 0, 0.8 - 0.1 * k, a * (1 - 0.2 * k), col=GRIS if k else AZUL)
    # el único lugar
    if t >= T_COINC - 0.1:
        q = ((t - T_COINC) * 1.1) % 1.0
        ctx.arc(*U, 30 + 110 * q, 0, TAU)
        ctx.set_source_rgba(*BLANCO, 0.9 * (1 - q))
        ctx.set_line_width(9)
        ctx.stroke()
        punto_azul(ctx, U[0], U[1], t, 1.25 * pop(t, T_COINC - 0.1, 0.35) * bump(t, T_TU - 0.1, 0.4, 0.3))
    ctx.restore()
    cruz(ctx, 900, 330, 64, pop(t, T_NOALC - 0.05, 0.3) * sale(t, b(12) - 0.2), 0.95)
    kartel(ctx, "UNO SOLO", 640, 330, 80, t, b(10) + 0.1, b(12) - 0.2, rot=-3)
    kartel(ctx, "¿HACIA QUÉ LADO?", 600, 1330, 66, t, T_LADO - 0.2, b(12) - 0.2, box=BLANCO, rot=2)
    kartel(ctx, "CUATRO A LA VEZ", 540, 320, 80, t, T_CUATRO - 0.1, T_COINC - 0.3, rot=-2)
    kartel(ctx, "UN SOLO LUGAR", 540, 320, 84, t, T_COINC - 0.1, T_TU - 0.25, rot=-2)
    if t >= T_TU - 0.15:
        cartel(ctx, "TÚ", 700, 700, 120, s=pop(t, T_TU - 0.15), rot=5)
        if t >= T_TU:
            P.flecha(ctx, 660, 770, U[0] + 44, U[1] - 44, t, color=AMARILLO, w=13, curva=0.25)


# ------------------------------------------------------------------ 7. relojes casi perfectos / una millonésima
T_PERF = b(15, "perfectos")
T_FALLA = b(16, "falla")
T_MILLON = b(16, "millonesima")
T_PROB = b(16, "problemas")
POPS += [T_PERF - 0.15, T_MILLON - 0.1, T_PROB - 0.1]


def d_relojes(ctx, t):
    fondo(ctx, t, 0.45)
    campo(ctx, t, 19, 40, 0.6, y1=1350)
    falla = t >= T_FALLA
    ctx.save()
    zoom(ctx, 1 + 0.06 * prog(t, b(15), b(17) - b(15)), 540, 860)
    tem = 7 * math.sin(t * 60) * clamp((t - T_FALLA) / 0.1) * sale(t, T_FALLA + 0.5, 0.2) if falla else 0
    _elipse_suave(ctx, 540, 860, 520, 520, ROJO if t >= T_PROB - 0.1 else LUZ, 0.25)
    reloj(ctx, 540 + tem, 860, 290 * pop(t, b(15) + 0.0, 0.45), t, vel=1.0, ojos="wide" if falla else "happy",
          boca="o" if falla else "grin", ceja="worried" if falla else None, marco=ORO,
          salto=0.5 * math.sin(t * 40) * sale(t, T_FALLA + 0.5, 0.2) if falla else 0)
    if not falla:                                     # brillitos de reloj perfecto
        for i in range(6):
            an = TAU * i / 6 + t * 0.8
            estrella(ctx, 540 + 380 * math.cos(an), 860 + 380 * math.sin(an), 22 * pop(t, b(15) + 0.3 + 0.08 * i, 0.3), 1,
                     col=AMARILLO)
    ctx.restore()
    kartel(ctx, "RELOJES ATÓMICOS", 540, 330, 72, t, b(15, "relojes") - 0.1, T_FALLA - 0.2, box=BLANCO, rot=-2)
    kartel(ctx, "CASI PERFECTOS", 540, 1300, 84, t, T_PERF - 0.15, T_FALLA - 0.2, rot=2)
    kartel(ctx, "0,000001 SEGUNDOS", 540, 330, 80, t, T_MILLON - 0.1, rot=-2)
    if t >= T_PROB - 0.1:
        cartel(ctx, "¡PROBLEMAS!", 540, 1300, 92, box=ROJO, fg=BLANCO, s=pop(t, T_PROB - 0.1, 0.25), rot=-5)


# ------------------------------------------------------------------ 8. apareces a 300 metros
REAL = (330, 1120)
FALSO = (770, 560)
T_APAR = b(17, "apareces")
T_300 = b(17, "trescientos")
T_ESTAS = b(17, "estas")
POPS += [T_300 - 0.1, T_ESTAS - 0.2]


def pin(ctx, x, y, s, col=VERDE):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(0, 0)
    ctx.curve_to(-70, -80, -62, -160, 0, -160)
    ctx.curve_to(62, -160, 70, -80, 0, 0)
    ctx.close_path()
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.arc(0, -104, 22, 0, TAU)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill()
    ctx.restore()


def d_mapa300(ctx, t):
    ctx.save()
    zoom(ctx, 1 + 0.05 * prog(t, b(17), b(18) - b(17)), 540, 860)
    mapa(ctx, -80, -80, 1240, 2080, paso=150, ox=40, oy=70, borde=False)
    ctx.set_source_rgba(*C.NOCHE, 0.25)
    ctx.paint()
    p = prog(t, T_APAR + 0.05, 0.45, "inout")
    x, y = lerp(REAL[0], FALSO[0], p), lerp(REAL[1], FALSO[1], p) - 120 * math.sin(math.pi * p)
    if p > 0.02:
        punteada(ctx, REAL[0], REAL[1], x, y + 120 * math.sin(math.pi * p), ROJO, w=10, a=0.95, paso=(22, 18))
    pin(ctx, REAL[0], REAL[1], pop(t, b(17) - 0.05, 0.35))
    punto_azul(ctx, x, y, t, 1.5 * pop(t, b(17) + 0.0, 0.3))
    ctx.restore()
    kartel(ctx, "300 METROS", 690, 930, 70, t, T_300 - 0.1, box=ROJO, fg=BLANCO, rot=-38)
    kartel(ctx, "ESTÁS AQUÍ", 430, 1300, 60, t, T_ESTAS - 0.2, box=VERDE, rot=2)
    kartel(ctx, "EL MAPA TE PONE ACÁ".replace("ACÁ", "AQUÍ"), 640, 380, 54, t, T_APAR + 0.5, box=BLANCO, rot=-2)


# ------------------------------------------------------------------ 9. tan exactos... allá arriba el tiempo pasa más rápido
T_EXACT = b(18, "exactos")
T_INCRE = b(18, "increible")
T_ARRIBA = b(19, "arriba")
T_RAPIDO = b(19, "rapido")
T_SUELO = b(19, "suelo")
POPS += [T_INCRE - 0.15, T_ARRIBA - 0.1, T_RAPIDO - 0.1, T_SUELO - 0.15]


def d_exactos(ctx, t):
    fondo(ctx, t, 0.45)
    parte = prog(t, b(19) - 0.15, 0.5)                # de un reloj a dos
    campo(ctx, t, 19, 45, 0.7, y1=lerp(1350, 800, parte))
    if parte > 0.01:                                  # el suelo
        ctx.rectangle(0, lerp(1960, 1000, parte), W, 1000)
        ctx.set_source_rgb(*hx("#123B2C"))
        ctx.fill()
        ctx.move_to(0, lerp(1960, 1000, parte))
        ctx.line_to(W, lerp(1960, 1000, parte))
        ctx.set_source_rgb(*hx("#2FA86B"))
        ctx.set_line_width(8)
        ctx.stroke()
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(18), b(20) - b(18)), 540, 860)
    sorp = t >= T_INCRE - 0.2 and t < b(19)
    y_arr = lerp(860, 650, parte)
    R = lerp(190, 150, parte)
    satelite(ctx, 540, y_arr, R / 100 * pop(t, b(18), 0.4), t, vel=lerp(1.0, 2.6, parte), ojos="wide" if sorp else "open",
             boca="o" if sorp else "smile", look=(0, 0.3))
    if sorp:
        for i, dx in enumerate((-330, 330)):
            ctx.save()
            ctx.translate(540 + dx, 600)
            s = pop(t, T_INCRE - 0.15 + 0.1 * i, 0.3)
            ctx.scale(max(s, 0.01), max(s, 0.01))
            texto(ctx, "!", 0, 0, 220, fill=AMARILLO, sw=14)
            ctx.restore()
    if parte > 0.3:
        reloj(ctx, 540, 1200, 140 * pop(t, b(19) + 0.1, 0.4), t, vel=1.0, ojos="open", boca="smile", look=(0, -0.8), marco=VERDE)
    ctx.restore()
    kartel(ctx, "TAN EXACTOS QUE...", 540, 320, 72, t, T_EXACT - 0.1, b(19) - 0.2, rot=-2)
    kartel(ctx, "ALLÁ ARRIBA", 260, 330, 60, t, T_ARRIBA - 0.1, box=BLANCO, rot=-4)
    kartel(ctx, "MÁS RÁPIDO", 800, 340, 72, t, T_RAPIDO - 0.1, rot=4)
    kartel(ctx, "EN EL SUELO", 250, 1090, 56, t, T_SUELO - 0.15, box=BLANCO, rot=3)
    kartel(ctx, "+38 MILLONÉSIMAS POR DÍA", 540, 925, 54, t, T_RAPIDO + 0.4, box=CIAN, rot=-2)


# ------------------------------------------------------------------ 10. Einstein lo predijo y el sistema lo corrige
T_PRED = b(20, "predijo")
T_CORR = b(20, "corrige")
T_DIAS = b(20, "dias")
POPS += [b(20) - 0.05, T_CORR - 0.15, T_DIAS - 0.2]


def pizarron(ctx, x, y, s, t, p):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    rrect(ctx, -360, -260, 720, 520, 20)
    ctx.set_source_rgb(*hx("#8A6A45"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(12)
    ctx.stroke()
    rrect(ctx, -330, -230, 660, 460, 10)
    ctx.set_source_rgb(*hx("#1F4A3A"))
    ctx.fill()
    tiza = hx("#F4F1E4")
    a1 = prog(p, 0.05, 0.3)
    texto(ctx, "1915", -190, -150, 96, fill=tiza, stroke=None, alpha=a1)
    # dos relojes dibujados con tiza: arriba corre más
    for i, (cx, cy, v) in enumerate(((-180, 60, 1.0), (180, 60, 2.6))):
        a = prog(p, 0.3 + 0.2 * i, 0.3)
        ctx.arc(cx, cy, 86, 0, TAU)
        ctx.set_source_rgba(*tiza, a)
        ctx.set_line_width(8)
        ctx.stroke()
        an = t * 3 * v
        ctx.move_to(cx, cy)
        ctx.line_to(cx + 62 * math.cos(an), cy + 62 * math.sin(an))
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    texto(ctx, "≠", 0, 60, 120, fill=tiza, stroke=None, alpha=prog(p, 0.6, 0.3))
    texto(ctx, "suelo", -180, 190, 44, fill=tiza, stroke=None, alpha=prog(p, 0.4, 0.3))
    texto(ctx, "espacio", 180, 190, 44, fill=tiza, stroke=None, alpha=prog(p, 0.6, 0.3))
    ctx.restore()


def d_einstein(ctx, t):
    fondo(ctx, t, 0.45)
    ctx.save()
    zoom(ctx, 1 + 0.05 * prog(t, b(20), b(21) - b(20)), 540, 860)
    corr = prog(t, T_CORR - 0.25, 0.45)
    pizarron(ctx, 540, lerp(820, 620, corr), lerp(1.0, 0.72, corr) * pop(t, b(20) - 0.05, 0.4), t,
             clamp((t - b(20)) / max(0.2, T_PRED + 0.5 - b(20))))
    if corr > 0.01:
        satelite(ctx, 420, 1130, 1.0 * pop(t, T_CORR - 0.15, 0.4), t, vel=1.0, ojos="happy", boca="grin")
        tilde(ctx, 760, 1120, 90, pop(t, T_CORR + 0.25, 0.3))
    ctx.restore()
    kartel(ctx, "EINSTEIN", 540, 300, 100, t, b(20) - 0.05, T_CORR - 0.3, rot=-3)
    kartel(ctx, "CORREGIDO", 540, 290, 90, t, T_CORR - 0.15, box=VERDE, rot=-3)
    kartel(ctx, "TODOS LOS DÍAS", 540, 1340, 62, t, T_DIAS - 0.2, box=BLANCO, rot=2)


# ------------------------------------------------------------------ 11. sin la corrección, el mapa falla por kilómetros
T_MAPA21 = b(21, "mapa")
T_FALLARIA = b(21, "fallaria")
T_KM = b(21, "kilometros")
POPS += [b(21) + 0.1, T_KM - 0.1]


def d_mapakm(ctx, t):
    deriva = prog(t, T_MAPA21, b(22) - 0.1 - T_MAPA21, "in")
    z = lerp(1.25, 0.62, prog(t, T_MAPA21 - 0.1, b(22) - T_MAPA21, "inout"))
    ctx.save()
    zoom(ctx, z, 420, 1050)
    mapa(ctx, -700, -900, 2500, 3800, paso=120, borde=False)
    ctx.set_source_rgba(*C.NOCHE, 0.25)
    ctx.paint()
    real = (420, 1050)
    x, y = real[0] + 760 * deriva, real[1] - 1050 * deriva
    punteada(ctx, real[0], real[1], x, y, ROJO, w=10 / z, a=0.95 * clamp(deriva * 20), paso=(22 / z, 18 / z))
    pin(ctx, real[0], real[1], 1.0 / z * pop(t, b(21) - 0.05, 0.3))
    punto_azul(ctx, x, y, t, 1.4 / z)
    ctx.restore()
    kartel(ctx, "SIN LA CORRECCIÓN", 540, 300, 72, t, b(21) + 0.1, box=BLANCO, rot=-2)
    if t >= T_KM - 0.1:
        cartel(ctx, "KILÓMETROS DE ERROR", 540, 1330, 70, box=ROJO, fg=BLANCO, s=pop(t, T_KM - 0.1, 0.25), rot=-3)
    if t >= T_FALLARIA:
        dia = 1 + int(clamp((t - T_FALLARIA) / (b(22) - T_FALLARIA)) * 5)
        cartel(ctx, f"DÍA {dia}", 800, 480, 76, s=pop(t, T_FALLARIA, 0.3), rot=4)


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_inicio),
    (b(1) - 0.08, d_rayo),
    (b(4) - 0.08, d_misma),
    (b(5) - 0.08, d_treinta),
    (b(6) - 0.08, d_senal),
    (b(10) - 0.08, d_circulos),
    (b(15) - 0.08, d_relojes),
    (b(17) - 0.08, d_mapa300),
    (b(18) - 0.08, d_exactos),
    (b(20) - 0.08, d_einstein),
    (b(21) - 0.08, d_mapakm),
    (b(22) - 0.08, d_cierre),
]
XF = 0.18
WHOOSH += [t0 for t0, _ in ESCENAS[1:]]


def punch(t, t0, d=0.3, amp=0.06):
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


# ------------------------------------------------------------------ sonido
def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    for i, t0 in enumerate(WHOOSH):
        ev(t0, "whoosh" if i % 2 else "whoosh_suave", 0.6)
    for t0 in POPS:
        ev(t0, "pop", 0.6)
    ev(0.05, "chispa", 0.3, d=0.6)
    for tr in (T_RAYO1, T_RAYO2):
        ev(tr, "chispa", 0.7, d=0.4)
    ev(T_TRUENO - 0.05, "golpe", 1.0)
    for k in range(5):
        ev(b(3) + 0.1 + k * (T_LEJOS + 0.4 - b(3)) / 5, "tick", 0.3, f=1500, d=0.04)
    for k in range(12):
        ev(b(5) + 0.15 + k * 0.07, "tick", 0.14, f=1900 + 40 * k, d=0.03)
    for k in range(int((b(7) - T_TRANS) / 0.33)):
        ev(T_TRANS + k * 0.33, "tick", 0.3, f=2200, d=0.05)
    ev(T_BAJA - 0.1, "subida", 0.35, d=T_LUZ7 - T_BAJA + 0.2)
    ev(T_LUZ7 + 0.1, "ding", 0.5)
    for k in range(int((T_TARDO + 0.3 - T_MIRA) / 0.08)):
        ev(T_MIRA + k * 0.08, "tick", 0.15, f=2000, d=0.025)
    ev(T_NOALC - 0.05, "tick", 0.6, f=180, d=0.22)
    ev(T_COINC - 0.1, "ding", 0.6)
    ev(T_TU - 0.15, "boing", 0.5)
    ev(T_FALLA, "zumbido", 0.3, d=0.5)
    ev(T_PROB - 0.1, "golpe", 0.8)
    ev(T_APAR + 0.05, "whoosh", 0.6)
    ev(T_APAR + 0.5, "tick", 0.6, f=180, d=0.22)
    ev(T_INCRE - 0.15, "boing", 0.5)
    ev(T_CORR + 0.25, "ding", 0.6)
    ev(T_MAPA21, "frenada", 0.35, d=1.2)
    ev(b(22) + 0.1, "subida", 0.3, d=1.2)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "como_sabe_tu_celular_donde_estas.mp4"))
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

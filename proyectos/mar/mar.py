"""Short "¿Por qué el mar es salado si los ríos son dulces?" — animación procedural (armazón de dedos.py).

Estilo del canal: fondo azul con puntos, cosas con cara (el río, el mar, los granos de sal, la gota, la botella, la
alcancía, la Tierra) y subtítulos palabra por palabra. Sin Vos: el primer cuadro es el paisaje del río que desemboca
en el mar, y el cierre vuelve a ese cuadro para el loop.

Hilo que se repite: los granos de sal con cara. Salen de las piedras, viajan por el río, se quedan en el mar cuando el
agua sube a las nubes, llenan la alcancía y terminan tapando los continentes.

    python proyectos/mar/mar.py --hoja 0,3,6      # hoja de fotogramas -> proyectos/mar/fotos/hoja.png
    python proyectos/mar/mar.py --probar
    python proyectos/mar/mar.py                   # render -> salidas/por_que_el_mar_es_salado.mp4
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import cairo
import numpy as np
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
for _p in (ROOT, os.path.join(ROOT, "proyectos", "pantalla"), os.path.join(ROOT, "proyectos", "picante"),
           os.path.join(ROOT, "proyectos", "tierra")):
    sys.path.insert(0, _p)
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, clamp, ease, hx, lerp, lienzo, pop, prog, rrect,  # noqa: E402
                      texto)
from picante import _elipse_suave, carita, fondo_azul  # noqa: E402
from tierra import (ROJO, VERDE, alfa, destello, elipse, en, kartel, nube, rellena, sello, signo, sol,  # noqa: E402
                    tachado, tilde, trazo, zoom)

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Todos los ríos del mundo le echan agua dulce al mar.",                                    # b0
    "Aun así, el mar es salado.",                                                              # b1
    "Si solo le entra agua dulce, ¿de dónde sale la sal?",                                     # b2
    "El agua dulce no es tan dulce.",                                                          # b3
    "Mira la etiqueta de una botella de agua.",                                                # b4
    "Dice sodio, lo mismo que sala el mar.",                                                   # b5
    "El río lo arranca de las piedras por donde pasa.",                                        # b6
    "Tan poquito que no lo sientes.",                                                          # b7
    "Entonces, ¿cómo un poquito de sal hizo un mar salado?",                                   # b8
    "Por acumulación,",                                                                        # b9
    "como una alcancía que se llena de a una moneda.",                                         # b10
    "El sol se lleva el agua del mar a las nubes.",                                            # b11
    "La sal no puede subir, se queda.",                                                        # b12
    "Esa agua llueve, vuelve a los ríos y trae otro poquito.",                                 # b13
    "El agua va y viene.",                                                                     # b14
    "La sal se juntó durante cientos de millones de años.",                                    # b15
    "Si sacaras toda esa sal y la tiraras sobre la tierra, taparía todos los continentes.",    # b16
    "La capa sería más alta que un edificio de 40 pisos.",                                     # b17
    "Casi toda la trajo el agua dulce de los ríos.",                                           # b18
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
KF = 60 * round(14 * TOTAL / 60) / (14 * TOTAL)      # el fondo de puntos cierra justo en el loop
MAR = hx("#1E9BEA")
MAR_OSC = hx("#0B5FA8")
MAR_CLARO = hx("#8EDBFF")
RIO = hx("#62CCFF")
RIO_OSC = hx("#2D9FE6")
PASTO = hx("#4CD07D")
PASTO_OSC = hx("#2E9E58")
PASTO_CLARO = hx("#8BEA9F")
MONTE = hx("#9A86F5")
MONTE_OSC = hx("#6F5AD6")
ARENA = hx("#FFD98A")
SAL = hx("#FFFFFF")
SAL_SOMBRA = hx("#CFE3F5")
PIEDRA = hx("#B3BCD0")
PIEDRA_OSC = hx("#7D88A2")
CHANCHO = hx("#FF93BC")
CHANCHO_OSC = hx("#E8679A")
ORO = hx("#FFC933")
ORO_OSC = hx("#E0960F")
BOTELLA = hx("#D6F2FF")
TAPA = hx("#2A8FD6")
LADRILLO = hx("#FF7E5F")
LADRILLO_OSC = hx("#D9583B")
VENTANA = hx("#FFE27A")
GRIS = hx("#C9D1DE")
TRONCO = hx("#A86B3C")
VIOLETA = hx("#B98CFF")


# ------------------------------------------------------------------ ayudas generales
def fondo(ctx, t, oscuro=0.0):
    fondo_azul(ctx, t * KF)
    if oscuro > 0:
        ctx.set_source_rgba(0.027, 0.043, 0.11, oscuro)
        ctx.paint()


def bez(p, s):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p
    m = 1 - s
    return (m ** 3 * x0 + 3 * m * m * s * x1 + 3 * m * s * s * x2 + s ** 3 * x3,
            m ** 3 * y0 + 3 * m * m * s * y1 + 3 * m * s * s * y2 + s ** 3 * y3)


def normal(p, s):
    x1, y1 = bez(p, max(0.0, s - 0.01))
    x2, y2 = bez(p, min(1.0, s + 0.01))
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1
    return -dy / L, dx / L


def cinta(ctx, p, w0, w1, n=48):
    """Camino de una cinta que sigue la curva p y se ensancha de w0 a w1."""
    izq, der = [], []
    for j in range(n + 1):
        s = j / n
        x, y = bez(p, s)
        nx, ny = normal(p, s)
        w = lerp(w0, w1, s ** 1.3) / 2
        izq.append((x + nx * w, y + ny * w))
        der.append((x - nx * w, y - ny * w))
    ctx.move_to(*izq[0])
    for q in izq[1:]:
        ctx.line_to(*q)
    for q in reversed(der):
        ctx.line_to(*q)
    ctx.close_path()


def linea_en(ctx, p, off, w0, w1, s0=0.0, s1=1.0, n=40):
    """Línea paralela a la curva p, corrida off (-0.5..0.5) del ancho."""
    for j in range(n + 1):
        s = lerp(s0, s1, j / n)
        x, y = bez(p, s)
        nx, ny = normal(p, s)
        w = lerp(w0, w1, s ** 1.3)
        (ctx.move_to if j == 0 else ctx.line_to)(x + nx * w * off, y + ny * w * off)


def brillo(ctx, x, y, r, a, col=AMARILLO):
    if a <= 0.01:
        return
    g = cairo.RadialGradient(x, y, r * 0.1, x, y, r)
    g.add_color_stop_rgba(0, *col, 0.8 * a)
    g.add_color_stop_rgba(1, *col, 0)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, TAU)
    ctx.fill()


def chispa(ctx, x, y, r, a=1.0, col=BLANCO):
    """Estrellita de cuatro puntas."""
    if a <= 0.01 or r <= 0.5:
        return
    ctx.move_to(x, y - r)
    ctx.curve_to(x + r * 0.12, y - r * 0.12, x + r * 0.12, y - r * 0.12, x + r, y)
    ctx.curve_to(x + r * 0.12, y + r * 0.12, x + r * 0.12, y + r * 0.12, x, y + r)
    ctx.curve_to(x - r * 0.12, y + r * 0.12, x - r * 0.12, y + r * 0.12, x - r, y)
    ctx.curve_to(x - r * 0.12, y - r * 0.12, x - r * 0.12, y - r * 0.12, x, y - r)
    ctx.close_path()
    ctx.set_source_rgba(*col, a)
    ctx.fill()


def suave(t, t0, d=0.3):
    """Entrada suave (0..1) sin rebote."""
    return prog(t, t0, d, "out")


def flecha_curva(ctx, p, a, col, w=16, s1=1.0):
    """Flecha que sigue la curva p (dibujada hasta s1)."""
    if a <= 0.01 or s1 <= 0.02:
        return
    n = 30
    for j in range(n + 1):
        x, y = bez(p, s1 * j / n)
        (ctx.move_to if j == 0 else ctx.line_to)(x, y)
    trazo(ctx, INK, w + 10, a)
    for j in range(n + 1):
        x, y = bez(p, s1 * j / n)
        (ctx.move_to if j == 0 else ctx.line_to)(x, y)
    trazo(ctx, col, w, a)
    x, y = bez(p, s1)
    x0, y0 = bez(p, max(0, s1 - 0.04))
    g = math.atan2(y - y0, x - x0)
    with en(ctx, x, y, 1.0, g):
        ctx.move_to(22, 0)
        ctx.line_to(-22, -26)
        ctx.line_to(-22, 26)
        ctx.close_path()
        rellena(ctx, col, 7, a=a)


# ------------------------------------------------------------------ personajes y objetos
def grano(ctx, x, y, r, cara=("open", "smile"), rot=0.0, a=1.0, look=(0, 0), ceja=None, s=1.0):
    """Grano de sal: un cubito blanco con brillo (y cara si r es grande)."""
    if a <= 0.01 or r * s <= 0.6:
        return
    with en(ctx, x, y, s, rot), alfa(ctx, a):
        rrect(ctx, -r, -r, 2 * r, 2 * r, r * 0.32)
        ctx.set_source_rgb(*SAL)
        ctx.fill_preserve()
        ctx.save()
        ctx.clip()
        ctx.move_to(r * 1.2, -r * 1.2)
        ctx.line_to(r * 1.2, r * 1.2)
        ctx.line_to(-r * 1.2, r * 1.2)
        ctx.close_path()
        ctx.set_source_rgb(*SAL_SOMBRA)
        ctx.fill()
        rrect(ctx, -r * 0.78, -r * 0.78, r * 1.56, r * 1.56, r * 0.26)
        ctx.set_source_rgb(*SAL)
        ctx.fill()
        ctx.restore()
        rrect(ctx, -r, -r, 2 * r, 2 * r, r * 0.32)
        trazo(ctx, INK, max(2.5, r * 0.13))
        if cara and r >= 14:
            carita(ctx, 0, -0.08 * r, 0.66 * r, r / 95, ojos=cara[0], boca=cara[1], look=look, ceja=ceja)
        else:
            chispa(ctx, -r * 0.35, -r * 0.35, r * 0.45, 0.9)


def gota(ctx, x, y, R, a=1.0, cara=("open", "smile"), look=(0, 0), s=1.0, ceja=None, col=RIO):
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        ctx.move_to(0, -1.45 * R)
        ctx.curve_to(0.55 * R, -0.7 * R, R, -0.25 * R, R, 0.28 * R)
        ctx.curve_to(R, 0.85 * R, 0.5 * R, 1.15 * R, 0, 1.15 * R)
        ctx.curve_to(-0.5 * R, 1.15 * R, -R, 0.85 * R, -R, 0.28 * R)
        ctx.curve_to(-R, -0.25 * R, -0.55 * R, -0.7 * R, 0, -1.45 * R)
        ctx.close_path()
        g = cairo.LinearGradient(0, -1.4 * R, 0, 1.15 * R)
        g.add_color_stop_rgb(0, *MAR_CLARO)
        g.add_color_stop_rgb(1, *col)
        ctx.set_source(g)
        ctx.fill_preserve()
        trazo(ctx, INK, max(4, R / 14))
        ctx.move_to(-0.55 * R, 0.0)
        ctx.curve_to(-0.6 * R, -0.3 * R, -0.45 * R, -0.55 * R, -0.3 * R, -0.75 * R)
        trazo(ctx, BLANCO, R / 9, 0.7)
        if cara:
            carita(ctx, 0, 0.25 * R, 0.62 * R, R / 120, ojos=cara[0], boca=cara[1], look=look, ceja=ceja)


def gotita(ctx, x, y, r, a=1.0, col=MAR_CLARO):
    if a <= 0.01 or r <= 0.5:
        return
    ctx.move_to(x, y - 1.5 * r)
    ctx.curve_to(x + r, y - 0.2 * r, x + r, y + r, x, y + r)
    ctx.curve_to(x - r, y + r, x - r, y - 0.2 * r, x, y - 1.5 * r)
    ctx.close_path()
    rellena(ctx, col, max(2.5, r / 5), a=a)


def ola(x, u, amp=12.0):
    return amp * math.sin(x * 0.017 + u * 2.2) + amp * 0.5 * math.sin(x * 0.043 - u * 1.6)


def mar(ctx, x0, x1, ytop, ybot, u, amp=12.0, r=80, borde=8.0):
    """Cuerpo de mar con olas arriba y esquinas redondeadas abajo."""
    ctx.move_to(x0, ytop + ola(x0, u, amp))
    for x in range(int(x0), int(x1) + 1, 16):
        ctx.line_to(x, ytop + ola(x, u, amp))
    ctx.line_to(x1, ytop + ola(x1, u, amp))
    ctx.line_to(x1, ybot - r)
    ctx.curve_to(x1, ybot - r * 0.45, x1 - r * 0.45, ybot, x1 - r, ybot)
    ctx.line_to(x0 + r, ybot)
    ctx.curve_to(x0 + r * 0.45, ybot, x0, ybot - r * 0.45, x0, ybot - r)
    ctx.close_path()
    g = cairo.LinearGradient(0, ytop - amp, 0, ybot)
    g.add_color_stop_rgb(0, *MAR_CLARO)
    g.add_color_stop_rgb(0.18, *MAR)
    g.add_color_stop_rgb(1, *MAR_OSC)
    ctx.set_source(g)
    ctx.fill_preserve()
    trazo(ctx, INK, borde)
    # espuma de las olas
    ctx.move_to(x0 + 20, ytop + ola(x0 + 20, u, amp) + 12)
    for x in range(int(x0) + 20, int(x1) - 19, 16):
        ctx.line_to(x, ytop + ola(x, u, amp) + 12)
    trazo(ctx, BLANCO, 6, 0.55)
    # rayitas de brillo que se mueven
    for k in range(7):
        ph = (u * 0.18 + k / 7) % 1
        xx = lerp(x0 + 60, x1 - 60, (k * 0.37 + ph) % 1)
        yy = lerp(ytop + 60, ybot - 60, ((k * 0.61) % 1))
        L = 40 + 20 * (k % 3)
        aa = 0.35 * math.sin(ph * math.pi)
        ctx.move_to(xx - L / 2, yy)
        ctx.curve_to(xx - L / 4, yy - 8, xx + L / 4, yy + 8, xx + L / 2, yy)
        trazo(ctx, BLANCO, 5, aa)


def cara_mar(ctx, x, y, k, t, ojos="open", boca="wavy", ceja="worried", look=(0, 0), lengua=0.0):
    carita(ctx, x, y, 150 * k, 1.3 * k, ojos=ojos, boca=boca, ceja=ceja, look=look, rubor=True)
    if lengua > 0.01:
        with en(ctx, x + 10 * k, y + 70 * k, lengua * k):
            elipse(ctx, 0, 14, 26, 30)
            rellena(ctx, hx("#FF6F8E"), 6)
            ctx.move_to(0, 0)
            ctx.line_to(0, 26)
            trazo(ctx, hx("#D94A6A"), 4)


def montana(ctx, x, base, w, h, col=MONTE, osc=MONTE_OSC, nieve=True):
    px, py = x + w * 0.04, base - h
    ctx.move_to(x - w / 2, base)
    ctx.line_to(px - 22, py + 18)
    ctx.curve_to(px - 10, py - 2, px + 10, py - 2, px + 22, py + 18)
    ctx.line_to(x + w / 2, base)
    ctx.close_path()
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    ctx.move_to(px, py)
    ctx.line_to(x + w / 2 + 10, base + 10)
    ctx.line_to(px + w * 0.05, base + 10)
    ctx.close_path()
    ctx.set_source_rgb(*osc)
    ctx.fill()
    if nieve:
        hh = h * 0.3
        ctx.move_to(px - 0.5 * hh * w / (2 * h) * 2, py + hh)
        for j, f in enumerate((-0.6, -0.3, 0.0, 0.3, 0.6)):
            ctx.line_to(px + f * hh * w / h * 0.5, py + hh * (0.8 if j % 2 else 1.08))
        ctx.line_to(px + 0.5 * hh * w / (2 * h) * 2, py + hh)
        ctx.line_to(px, py - 10)
        ctx.close_path()
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()
    ctx.restore()
    ctx.move_to(x - w / 2, base)
    ctx.line_to(px - 22, py + 18)
    ctx.curve_to(px - 10, py - 2, px + 10, py - 2, px + 22, py + 18)
    ctx.line_to(x + w / 2, base)
    trazo(ctx, INK, 7)


def arbolito(ctx, x, y, s, u, k=0):
    with en(ctx, x, y, s, 0.04 * math.sin(u * 1.8 + k)):
        rrect(ctx, -10, -40, 20, 46, 8)
        rellena(ctx, TRONCO, 5)
        ctx.arc(0, -78, 46, 0, TAU)
        rellena(ctx, PASTO_OSC, 6)
        ctx.arc(-14, -92, 16, 0, TAU)
        ctx.set_source_rgba(*PASTO_CLARO, 0.8)
        ctx.fill()


def piedra(ctx, x, y, r, cara=("open", "smile"), ceja=None, look=(0, 0), seed=0, s=1.0):
    if s <= 0.01:
        return
    rnd = random.Random(seed)
    pts = []
    n = 9
    for j in range(n):
        g = TAU * j / n
        rr = r * (0.82 + 0.22 * rnd.random())
        pts.append((rr * math.cos(g), rr * math.sin(g) * 0.72))
    with en(ctx, x, y, s):
        ctx.move_to(*pts[0])
        for j in range(n):
            a0, a1 = pts[j], pts[(j + 1) % n]
            mx, my = (a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2
            ctx.curve_to(a0[0], a0[1], a0[0], a0[1], mx, my)
        ctx.close_path()
        g = cairo.LinearGradient(0, -r, 0, r)
        g.add_color_stop_rgb(0, *PIEDRA)
        g.add_color_stop_rgb(1, *PIEDRA_OSC)
        ctx.set_source(g)
        ctx.fill_preserve()
        trazo(ctx, INK, 7)
        ctx.move_to(-r * 0.5, -r * 0.35)
        ctx.curve_to(-r * 0.3, -r * 0.5, 0, -r * 0.52, r * 0.15, -r * 0.48)
        trazo(ctx, BLANCO, 6, 0.5)
        if cara:
            carita(ctx, 0, -r * 0.05, r * 0.6, r / 120, ojos=cara[0], boca=cara[1], ceja=ceja, look=look)


def salero(ctx, x, y, s=1.0, look=(0, 0), ojos="open", boca="o", ceja="worried", rot=0.0):
    if s <= 0.01:
        return
    with en(ctx, x, y, s, rot):
        rrect(ctx, -80, -110, 160, 230, 46)
        ctx.set_source_rgba(*BOTELLA, 0.95)
        ctx.fill_preserve()
        trazo(ctx, INK, 8)
        ctx.save()
        rrect(ctx, -80, -110, 160, 230, 46)
        ctx.clip()
        rrect(ctx, -90, 40, 180, 100, 0)
        ctx.set_source_rgb(*SAL)
        ctx.fill()
        for k in range(14):
            gx, gy = -60 + (k * 37) % 120, 46 + (k * 23) % 60
            ctx.rectangle(gx, gy, 9, 9)
            ctx.set_source_rgb(*SAL_SOMBRA)
            ctx.fill()
        ctx.restore()
        rrect(ctx, -80, -110, 160, 230, 46)
        trazo(ctx, INK, 8)
        ctx.move_to(-58, -80)
        ctx.line_to(-58, 10)
        trazo(ctx, BLANCO, 10, 0.7)
        rrect(ctx, -86, -176, 172, 76, 30)
        g = cairo.LinearGradient(-86, 0, 86, 0)
        g.add_color_stop_rgb(0, *hx("#EEF2F8"))
        g.add_color_stop_rgb(0.5, *hx("#C3CCDA"))
        g.add_color_stop_rgb(1, *hx("#9AA5B8"))
        ctx.set_source(g)
        ctx.fill_preserve()
        trazo(ctx, INK, 8)
        for hx_, hy in ((-30, -150), (0, -158), (30, -150), (-15, -134), (15, -134)):
            ctx.arc(hx_, hy, 6, 0, TAU)
            ctx.set_source_rgb(*INK)
            ctx.fill()
        carita(ctx, 0, -40, 70, 0.75, ojos=ojos, boca=boca, ceja=ceja, look=look, rubor=True)


def moneda(ctx, x, y, r, giro=0.0, a=1.0):
    if a <= 0.01:
        return
    sx = max(0.12, abs(math.cos(giro)))
    with alfa(ctx, a):
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(sx, 1)
        ctx.arc(0, 0, r, 0, TAU)
        ctx.restore()
        rellena(ctx, ORO, 6)
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(sx, 1)
        ctx.arc(0, 0, r * 0.68, 0, TAU)
        ctx.restore()
        trazo(ctx, ORO_OSC, 5)
        if sx > 0.5:
            ctx.save()
            ctx.translate(x, y)
            ctx.scale(sx, 1)
            texto(ctx, "$", 0, 2, r * 0.95, fill=ORO_OSC, sw=0)
            ctx.restore()


def chancho(ctx, x, y, s=1.0, lleno=0.0, look=(0.6, 0.0), ojos="open", boca="smile", t=0.0):
    """Alcancía chanchito mirando a la derecha; lleno = monedas en la panza (0..1, se ven por la ventana)."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        # patas
        for px in (-130, -60, 70, 140):
            rrect(ctx, px - 28, 110, 56, 90, 22)
            rellena(ctx, CHANCHO_OSC, 7)
        # cola
        ctx.move_to(-240, -10)
        ctx.curve_to(-300, -30, -300, -90, -262, -90)
        ctx.curve_to(-230, -90, -240, -40, -275, -50)
        trazo(ctx, INK, 16)
        ctx.move_to(-240, -10)
        ctx.curve_to(-300, -30, -300, -90, -262, -90)
        ctx.curve_to(-230, -90, -240, -40, -275, -50)
        trazo(ctx, CHANCHO_OSC, 8)
        # orejas
        for ox, rot in ((60, -0.25), (150, 0.15)):
            with en(ctx, ox, -150, 1.0, rot):
                ctx.move_to(-38, 20)
                ctx.line_to(0, -60)
                ctx.line_to(38, 20)
                ctx.close_path()
                rellena(ctx, CHANCHO_OSC, 7)
        # cuerpo
        elipse(ctx, 0, 0, 250, 175)
        g = cairo.RadialGradient(-60, -80, 30, 0, 0, 260)
        g.add_color_stop_rgb(0, *hx("#FFC2DA"))
        g.add_color_stop_rgb(1, *CHANCHO)
        ctx.set_source(g)
        ctx.fill_preserve()
        trazo(ctx, INK, 8)
        # ranura
        rrect(ctx, -70, -183, 130, 24, 12)
        rellena(ctx, INK, 4)
        # ventana con las monedas
        wx, wy, wr = -70, 40, 96
        ctx.arc(wx, wy, wr, 0, TAU)
        ctx.set_source_rgb(*hx("#FFF4FA"))
        ctx.fill()
        ctx.save()
        ctx.arc(wx, wy, wr, 0, TAU)
        ctx.clip()
        n = int(round(lleno * 9))
        for k in range(n):
            cy = wy + wr - 18 - k * 20
            elipse(ctx, wx + (6 if k % 2 else -6), cy, 70, 16)
            rellena(ctx, ORO, 5, ORO_OSC)
        ctx.restore()
        ctx.arc(wx, wy, wr, 0, TAU)
        trazo(ctx, INK, 9)
        ctx.arc(wx, wy, wr, -2.4, -1.6)
        trazo(ctx, BLANCO, 10, 0.8)
        # hocico y cara
        carita(ctx, 130, -55, 82, 0.85, ojos=ojos, boca=boca, look=look, dy_boca=118, rubor=True)
        elipse(ctx, 205, 10, 54, 44)
        rellena(ctx, hx("#FFB0CF"), 7)
        for nx in (-14, 14):
            elipse(ctx, 205 + nx, 10, 7, 12)
            ctx.set_source_rgb(*CHANCHO_OSC)
            ctx.fill()


def botella(ctx, x, y, s=1.0, u=0.0, ojos="open", boca="smile", look=(0, 0), brillo_et=0.0):
    """Botella de agua; (x, y) = centro de la etiqueta."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        def silueta():
            ctx.move_to(-56, -400)
            ctx.line_to(56, -400)
            ctx.line_to(56, -340)
            ctx.curve_to(56, -300, 140, -290, 140, -200)
            ctx.line_to(140, 330)
            ctx.curve_to(140, 380, 110, 400, 70, 400)
            ctx.line_to(-70, 400)
            ctx.curve_to(-110, 400, -140, 380, -140, 330)
            ctx.line_to(-140, -200)
            ctx.curve_to(-140, -290, -56, -300, -56, -340)
            ctx.close_path()
        silueta()
        ctx.set_source_rgba(*BOTELLA, 0.9)
        ctx.fill()
        # agua adentro, con la superficie que se mueve
        ctx.save()
        silueta()
        ctx.clip()
        ys = -250
        ctx.move_to(-150, ys)
        for xx in range(-150, 151, 15):
            ctx.line_to(xx, ys + 8 * math.sin(xx * 0.03 + u * 3))
        ctx.line_to(150, 420)
        ctx.line_to(-150, 420)
        ctx.close_path()
        g = cairo.LinearGradient(0, ys, 0, 400)
        g.add_color_stop_rgb(0, *MAR_CLARO)
        g.add_color_stop_rgb(1, *RIO)
        ctx.set_source(g)
        ctx.fill()
        for k in range(5):
            ph = (u * 0.35 + k / 5) % 1
            ctx.arc(-80 + k * 40, lerp(360, -220, ph), 6 + 3 * (k % 2), 0, TAU)
            ctx.set_source_rgba(1, 1, 1, 0.6 * math.sin(ph * math.pi))
            ctx.fill()
        ctx.restore()
        silueta()
        trazo(ctx, INK, 8)
        # aros del cuerpo
        for yy in (190, 250):
            ctx.move_to(-140, yy)
            ctx.curve_to(-50, yy + 16, 50, yy + 16, 140, yy)
            trazo(ctx, INK, 5, 0.5)
        ctx.move_to(-104, -190)
        ctx.line_to(-104, 330)
        trazo(ctx, BLANCO, 14, 0.55)
        # tapa
        rrect(ctx, -68, -470, 136, 80, 18)
        rellena(ctx, TAPA, 8)
        for k in range(5):
            ctx.move_to(-44 + 22 * k, -460)
            ctx.line_to(-44 + 22 * k, -400)
            trazo(ctx, INK, 4, 0.45)
        # etiqueta
        rrect(ctx, -144, -110, 288, 200, 10)
        rellena(ctx, BLANCO, 7)
        if brillo_et > 0.01:
            rrect(ctx, -144, -110, 288, 200, 10)
            trazo(ctx, AMARILLO, 14, brillo_et)
        rrect(ctx, -144, -110, 288, 60, 10)
        ctx.set_source_rgb(*TAPA)
        ctx.fill()
        texto(ctx, "AGUA", 0, -78, 44, fill=BLANCO, sw=0)
        for k in range(4):
            ctx.move_to(-100, -20 + k * 24)
            ctx.line_to(lerp(60, 100, (k * 0.37) % 1), -20 + k * 24)
            trazo(ctx, GRIS, 9)
        carita(ctx, 0, 160, 92, 0.95, ojos=ojos, boca=boca, look=look, rubor=True)


def vaso(ctx, x, y, s=1.0, u=0.0, ojos="open", boca="smile", look=(0, 0), ceja=None):
    """Vaso de agua de río con cara; (x, y) = base."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        def forma():
            ctx.move_to(-150, -420)
            ctx.line_to(150, -420)
            ctx.line_to(118, 0)
            ctx.line_to(-118, 0)
            ctx.close_path()
        forma()
        ctx.set_source_rgba(*BOTELLA, 0.8)
        ctx.fill()
        ctx.save()
        forma()
        ctx.clip()
        ys = -320
        ctx.move_to(-160, ys)
        for xx in range(-160, 161, 16):
            ctx.line_to(xx, ys + 7 * math.sin(xx * 0.035 + u * 2.6))
        ctx.line_to(160, 10)
        ctx.line_to(-160, 10)
        ctx.close_path()
        g = cairo.LinearGradient(0, ys, 0, 0)
        g.add_color_stop_rgb(0, *MAR_CLARO)
        g.add_color_stop_rgb(1, *RIO_OSC)
        ctx.set_source(g)
        ctx.fill()
        ctx.restore()
        # pajita
        ctx.move_to(60, -230)
        ctx.line_to(110, -520)
        ctx.line_to(170, -540)
        trazo(ctx, INK, 30)
        ctx.move_to(60, -230)
        ctx.line_to(110, -520)
        ctx.line_to(170, -540)
        trazo(ctx, ROJO, 18)
        forma()
        trazo(ctx, INK, 8)
        ctx.move_to(-120, -380)
        ctx.line_to(-96, -60)
        trazo(ctx, BLANCO, 14, 0.6)
        carita(ctx, 0, -170, 100, 1.0, ojos=ojos, boca=boca, look=look, ceja=ceja, rubor=True)


def medidor(ctx, x, y, R, frac, titulo="SAL", s=1.0):
    """Medidor de aguja (frac 0..1)."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.move_to(-R - 20, 30)
        ctx.arc(0, 30, R + 20, math.pi, TAU)
        ctx.close_path()
        rellena(ctx, BLANCO, 8)
        for k, col in enumerate((VERDE, AMARILLO, hx("#FF9A1F"), ROJO)):
            ctx.arc(0, 30, R - 18, math.pi + k * math.pi / 4, math.pi + (k + 1) * math.pi / 4)
            trazo(ctx, col, 26)
            ctx.new_path()
        g = math.pi + math.pi * clamp(frac)
        ctx.move_to(0, 30)
        ctx.line_to(0.8 * R * math.cos(g), 30 + 0.8 * R * math.sin(g))
        trazo(ctx, INK, 12)
        ctx.arc(0, 30, 16, 0, TAU)
        ctx.set_source_rgb(*INK)
        ctx.fill()
        texto(ctx, titulo, 0, 82, 50, fill=BLANCO, sw=9)


def calendario(ctx, x, y, s, num, flip=0.0):
    """Hoja de calendario con el número; flip = 0..1 la hoja de arriba se levanta."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        rrect(ctx, -190, -130, 380, 260, 26)
        rellena(ctx, BLANCO, 8)
        rrect(ctx, -190, -130, 380, 70, 26)
        ctx.set_source_rgb(*ROJO)
        ctx.fill()
        rrect(ctx, -190, -130, 380, 260, 26)
        trazo(ctx, INK, 8)
        for rx in (-110, 110):
            rrect(ctx, rx - 10, -154, 20, 50, 10)
            rellena(ctx, GRIS, 5)
        texto(ctx, "AÑOS", 0, -95, 40, fill=BLANCO, sw=0)
        texto(ctx, num, 0, 34, 66 if len(num) < 9 else 52, fill=INK, sw=0)
        if flip > 0.01:
            with en(ctx, 0, -60, 1.0):
                ctx.scale(1, max(0.02, 1 - flip))
                rrect(ctx, -186, 0, 372, 186, 18)
                rellena(ctx, hx("#F2F4FA"), 6)


# ------------------------------------------------------------------ 1. apertura: el río le echa agua dulce al mar
T_TODOS = b(0)
T_RIOS0 = b(0, "rios")
T_MUNDO = b(0, "mundo")
T_DULCE0 = b(0, "dulce")
T_MAR0 = b(0, "mar")
T_AUN = b(1)
T_SALADO1 = b(1, "salado")
T_SI2 = b(2)
T_ENTRA = b(2, "entra")
T_DULCE2 = b(2, "dulce")
T_DE2 = b(2, "de")
T_SAL2 = b(2, "sal")
RIO_P = [(250, 560), (560, 690), (210, 880), (600, 1080)]
MAR_Y = 1060
BOCA = bez(RIO_P, 1.0)
CARA_MAR = (720, 1250)
ZOOM_Q = (600, 1070)


def paisaje(ctx, u, rio_cara=("happy", "grin"), mar_k=None, granos=0.0, brillo_rio=0.0):
    """Montañas, el río con cara que baja y el mar con cara. u = tiempo (periódico, para el loop)."""
    _elipse_suave(ctx, 540, 900, 620, 520, hx("#5FB8FF"), 0.10)
    sol(ctx, 900, 330, 78, u)
    for k, (nx, ny, nr) in enumerate(((240, 300, 70), (640, 230, 56))):
        nube(ctx, nx + 26 * math.sin(u * 0.45 + k * 2), ny, nr)
    montana(ctx, 460, 760, 520, 420, MONTE, MONTE_OSC)
    montana(ctx, 160, 780, 460, 470, hx("#8873EE"), MONTE_OSC)
    # pasto: lomas que bajan al mar
    ctx.move_to(-40, MAR_Y + 60)
    ctx.line_to(-40, 700)
    ctx.curve_to(140, 640, 300, 700, 440, 690)
    ctx.curve_to(620, 680, 760, 760, 900, 840)
    ctx.curve_to(1000, 900, 1080, 940, 1120, 980)
    ctx.line_to(1120, MAR_Y + 60)
    ctx.close_path()
    g = cairo.LinearGradient(0, 650, 0, MAR_Y)
    g.add_color_stop_rgb(0, *PASTO_CLARO)
    g.add_color_stop_rgb(1, *PASTO)
    ctx.set_source(g)
    ctx.fill_preserve()
    trazo(ctx, INK, 7)
    for k, (tx, ty, ts) in enumerate(((90, 790, 0.9), (760, 860, 0.85), (880, 930, 0.7), (470, 1000, 0.6))):
        arbolito(ctx, tx, ty, ts, u, k)
    # arena de la costa
    elipse(ctx, 540, MAR_Y + 4, 600, 46)
    rellena(ctx, ARENA, 7)
    # el río
    if brillo_rio > 0.01:
        cinta(ctx, RIO_P, 60, 220)
        trazo(ctx, AMARILLO, 40, 0.6 * brillo_rio)
    cinta(ctx, RIO_P, 44, 190)
    g = cairo.LinearGradient(*RIO_P[0], *RIO_P[3])
    g.add_color_stop_rgb(0, *MAR_CLARO)
    g.add_color_stop_rgb(1, *RIO)
    ctx.set_source(g)
    ctx.fill_preserve()
    trazo(ctx, INK, 7)
    ctx.set_dash([34, 56], -u * 150)
    for off in (-0.25, 0.0, 0.28):
        linea_en(ctx, RIO_P, off, 44, 190, 0.02, 0.97)
        trazo(ctx, BLANCO, 6, 0.7)
    ctx.set_dash([])
    # granos de sal que bajan con el río
    if granos > 0.01:
        for k in range(5):
            s = ((u * 0.28) + k / 5) % 1
            gx, gy = bez(RIO_P, s)
            nx, ny = normal(RIO_P, s)
            off = 22 * math.sin(k * 2.3)
            grano(ctx, gx + nx * off, gy + ny * off - 4, 13, cara=None, rot=u * 2 + k,
                  a=granos * min(1, s * 6, (1 - s) * 8))
    # cara del río
    cx, cy = bez(RIO_P, 0.58)
    carita(ctx, cx + 4, cy - 8, 58, 0.62, ojos=rio_cara[0], boca=rio_cara[1], rubor=True, look=(0.4, 0.4))
    # el mar
    mar(ctx, -40, 1120, MAR_Y, 1460, u, r=0)
    # salpicadura donde entra el río
    for k in range(6):
        ph = (u * 1.3 + k / 6) % 1
        ang = -math.pi / 2 + (k - 2.5) * 0.35
        r = 30 + 70 * ph
        gotita(ctx, BOCA[0] + 20 + r * math.cos(ang), MAR_Y + 10 + r * math.sin(ang) + 120 * ph * ph, 9,
               0.9 * math.sin(ph * math.pi))
    mk = mar_k or {}
    cara_mar(ctx, CARA_MAR[0], CARA_MAR[1], 1.0, u, **mk)


def d_apertura(ctx, u):
    """Apertura; también es el cierre con el tiempo corrido (u < 0 = antes del principio)."""
    fondo(ctx, u % TOTAL)
    z = 1.0
    if u > 0:
        z = lerp(1.0, 1.45, prog(u, T_SI2 - 0.1, 1.4, "inout"))
    with en(ctx, 0, 0):
        zoom(ctx, z, *ZOOM_Q)
        sal1 = P.bump(u, T_SALADO1, 0.45, 0.08) if u > 0 else 1.0
        mk = dict(ojos="open", boca="wavy", ceja="worried", look=(-0.5, -0.5))
        if u > T_SALADO1 - 0.05:
            mk = dict(ojos="closed", boca="wavy", ceja="worried",
                      lengua=pop(u, T_SALADO1, 0.3) * (1 - prog(u, T_SI2 + 0.4, 0.3)))
        if u > T_SAL2:
            mk = dict(ojos="wide", boca="o", ceja="worried", look=(-0.6, -0.6))
        with en(ctx, CARA_MAR[0], CARA_MAR[1], sal1):
            ctx.translate(-CARA_MAR[0], -CARA_MAR[1])
            paisaje(ctx, u, mar_k=mk, granos=0.0, brillo_rio=P.bump(u, T_DULCE0 - 0.1, 0.7, 1.0) - 1.0
                    if u > 0 else 0.0)
        if u > 0:
            # gotas dulces que entran en el mar
            for k in range(4):
                t0 = T_ENTRA - 0.2 + 0.25 * k
                q = clamp((u - t0) / 0.7)
                if 0 < q < 1:
                    gx = BOCA[0] + 30 + 90 * q
                    gota(ctx, gx, lerp(BOCA[1] - 40, MAR_Y + 90, ease(q, "in")) - 60 * math.sin(q * math.pi),
                         22, a=1 - prog(q, 0.8, 0.2), cara=("happy", "smile"))
    if u > 0:
        kartel(ctx, "DULCE", 300, 940, 62, u, T_DULCE0 - 0.05, T_SALADO1 - 0.3, box=AMARILLO)
        sello(ctx, "SALADO", 720, 930, 92, u, T_SALADO1 - 0.05, T_SI2 - 0.1)
        # ¿de dónde sale la sal?
        ss = pop(u, T_DE2 - 0.1, 0.4)
        salero(ctx, 820, 640, 1.45 * ss, look=(-0.3, 0.6), rot=0.12 * math.sin((u - T_DE2) * 5))
        signo(ctx, "?", 600, 470, 150, u, T_SAL2 - 0.05)
        signo(ctx, "?", 990, 400, 120, u, T_SAL2 + 0.1)


def d_cierre(ctx, t):
    """Casi toda la trajo el agua dulce de los ríos: el paisaje de la apertura, con los granos bajando por el río."""
    u = t - TOTAL
    fondo(ctx, u % TOTAL)
    gr = clamp((t - T_CASI) / 0.5) * clamp(-u / 0.9)
    br = P.bump(t, T_DULCE18 - 0.1, 0.8, 1.0) - 1.0
    mk = dict(ojos="open", boca="wavy", ceja="worried", look=(-0.5, -0.5))
    paisaje(ctx, u, mar_k=mk, granos=gr, brillo_rio=br)


# ------------------------------------------------------------------ 2. el agua dulce no es tan dulce
T_EL3 = b(3)
T_NO3 = b(3, "no")
T_TAN3 = b(3, "tan")
T_DULCE3 = b(3, "dulce", n=1)


def d_gota(ctx, t):
    fondo(ctx, t)
    s = pop(t, T_EL3 - 0.05, 0.45)
    sorpresa = t > T_DULCE3
    look = (0.0, 0.7) if sorpresa else (0.2, -0.3)
    cara = ("wide", "o") if sorpresa else ("happy", "grin")
    R = 230
    gx, gy = 540, 830 + 10 * math.sin(t * 3)
    brillo(ctx, gx, gy, 520, 0.35, MAR_CLARO)
    gota(ctx, gx, gy, R, s=s, cara=cara, look=look, ceja="up" if sorpresa else None)
    # granitos de sal escondidos adentro
    for k, (dx, dy) in enumerate(((-110, 170), (60, 210), (140, 110), (-40, 120), (-150, 60))):
        a = suave(t, T_DULCE3 + 0.08 * k, 0.25)
        if a > 0.01:
            grano(ctx, gx + dx * s, gy + dy * s, 20, cara=None, rot=0.3 * k + t, s=a)
            chispa(ctx, gx + dx * s + 18, gy + dy * s - 18, 14 * a, a * (0.5 + 0.5 * math.sin(t * 9 + k)))
    tachado(ctx, "DULCE", 540, 380, 120, t, T_EL3 + 0.1, T_TAN3)
    if t > T_DULCE3:
        kartel(ctx, "¡TIENE SAL!", 540, 1300, 64, t, T_DULCE3 + 0.1, box=BLANCO)


# ------------------------------------------------------------------ 3. la etiqueta de la botella
T_MIRA = b(4)
T_ETIQUETA = b(4, "etiqueta")
T_BOTELLA = b(4, "botella")
T_DICE = b(5)
T_SODIO = b(5, "sodio")
T_MISMO = b(5, "mismo")
T_SALA = b(5, "sala")
T_MAR5 = b(5, "mar")
BOT = (290, 860, 1.12)
PANEL = (770, 600)
FILAS = [("Calcio", "32"), ("Magnesio", "8"), ("Sodio", "14"), ("Potasio", "2")]


def d_botella(ctx, t):
    fondo(ctx, t)
    bx, by, bs = BOT
    s = pop(t, T_MIRA - 0.05, 0.45)
    rot = 0.05 * math.sin(t * 2.2)
    with en(ctx, bx, by, 1.0, rot):
        ctx.translate(-bx, -by)
        botella(ctx, bx, by, bs * s, t, look=(0.7, -0.3), brillo_et=suave(t, T_ETIQUETA, 0.3) *
                (0.6 + 0.4 * math.sin(t * 6)))
    # la etiqueta, en grande
    a = suave(t, T_ETIQUETA, 0.35)
    if a > 0.01:
        px, py = PANEL
        ps = pop(t, T_ETIQUETA, 0.4)
        ctx.move_to(bx + 140 * bs, by - 110 * bs)
        ctx.line_to(px - 230 * ps, py - 200 * ps)
        ctx.line_to(px - 230 * ps, py + 220 * ps)
        ctx.line_to(bx + 140 * bs, by + 90 * bs)
        ctx.close_path()
        ctx.set_source_rgba(*AMARILLO, 0.18 * a)
        ctx.fill()
        with en(ctx, px, py, ps * 1.08):
            rrect(ctx, -250, -230, 500, 470, 30)
            rellena(ctx, BLANCO, 9)
            rrect(ctx, -250, -230, 500, 100, 30)
            ctx.set_source_rgb(*TAPA)
            ctx.fill()
            rrect(ctx, -250, -230, 500, 470, 30)
            trazo(ctx, INK, 9)
            texto(ctx, "COMPOSICIÓN", 0, -195, 46, fill=BLANCO, sw=0)
            texto(ctx, "mg por litro", 0, -150, 30, fill=BLANCO, sw=0)
            for k, (nom, val) in enumerate(FILAS):
                yy = -70 + k * 76
                es_sodio = nom == "Sodio"
                hl = suave(t, T_SODIO - 0.05, 0.25) if es_sodio else 0.0
                dim = 1 - 0.55 * suave(t, T_SODIO - 0.05, 0.3) if not es_sodio else 1.0
                if hl > 0.01:
                    rrect(ctx, -236, yy - 34, 472 * hl, 68, 16)
                    ctx.set_source_rgb(*AMARILLO)
                    ctx.fill()
                ent = suave(t, T_ETIQUETA + 0.15 + 0.1 * k, 0.25)
                with alfa(ctx, ent * dim):
                    texto(ctx, nom, -205, yy, 46 if not es_sodio else 48, fill=INK, sw=0, ax=0.0)
                    texto(ctx, val, 205, yy, 46, fill=INK, sw=0, ax=1.0)
                if k < len(FILAS) - 1:
                    ctx.move_to(-220, yy + 38)
                    ctx.line_to(220, yy + 38)
                    trazo(ctx, GRIS, 3, ent)
    # lo mismo que sala el mar
    sm = pop(t, T_MISMO - 0.15, 0.45)
    if sm > 0.01:
        mx, my = 790, 1185
        with en(ctx, mx, my, sm):
            ctx.save()
            ctx.translate(-mx, -my)
            ctx.arc(mx, my, 150, 0, TAU)
            ctx.clip()
            mar(ctx, mx - 170, mx + 170, my - 90, my + 170, t, amp=10, r=0, borde=0)
            ctx.restore()
            ctx.arc(0, 0, 150, 0, TAU)
            trazo(ctx, INK, 9)
            salado = t > T_SALA
            carita(ctx, 0, 30, 90, 0.85, ojos="closed" if salado else "open", boca="wavy" if salado else "smile",
                   ceja="worried" if salado else None, rubor=True)
        # el sodio viaja de la etiqueta al mar
        q = prog(t, T_MISMO, 0.55, "inout")
        if 0 < q < 1:
            sx, sy = PANEL[0], PANEL[1] - 70 + 2 * 76
            x = lerp(sx, mx, q)
            y = lerp(sy, my - 60, q) - 140 * math.sin(q * math.pi)
            P.cartel(ctx, "SODIO", x, y, 44, box=AMARILLO, s=1 - 0.4 * q)
        signo(ctx, "=", 520, 1185, 120, t, T_MISMO - 0.05)
        grano(ctx, 330, 1185, 62, cara=("open", "smile"), s=pop(t, T_MISMO - 0.05, 0.4), rot=0.1 * math.sin(t * 3))
    destello(ctx, 790, 1185, 190, t, T_SALA - 0.05)


# ------------------------------------------------------------------ 4. el río lo arranca de las piedras
T_RIO6 = b(6)
T_ARRANCA = b(6, "arranca")
T_PIEDRAS = b(6, "piedras")
T_PASA = b(6, "pasa")
CAUCE = (640, 1260)          # arriba y abajo del agua
PIEDRAS = [(160, 1170, 150, 0), (480, 1200, 130, 1), (790, 1165, 155, 2), (1050, 1195, 120, 3)]


def d_piedras(ctx, t):
    fondo(ctx, t)
    y0, y1 = CAUCE
    # de dónde viene el río: montañas y sol
    sol(ctx, 900, 250, 70, t)
    montana(ctx, 330, y0 - 20, 640, 440, MONTE, MONTE_OSC)
    montana(ctx, 760, y0 - 20, 520, 330, hx("#8873EE"), MONTE_OSC)
    # orillas con pasto
    for yy, sgn in ((y0, -1), (y1, 1)):
        ctx.move_to(-40, yy)
        for x in range(-40, 1121, 40):
            ctx.line_to(x, yy + sgn * (30 + 10 * math.sin(x * 0.02)))
        ctx.line_to(1120, yy + sgn * (120 if sgn < 0 else 260))
        ctx.line_to(-40, yy + sgn * (120 if sgn < 0 else 260))
        ctx.close_path()
        rellena(ctx, PASTO, 7)
    for k, (tx, ty) in enumerate(((120, y0 - 30), (960, y0 - 35), (600, y0 - 40))):
        arbolito(ctx, tx, ty, 0.9, t, k)
    # el agua del río
    ctx.rectangle(-40, y0, 1160, y1 - y0)
    g = cairo.LinearGradient(0, y0, 0, y1)
    g.add_color_stop_rgb(0, *MAR_CLARO)
    g.add_color_stop_rgb(1, *RIO_OSC)
    ctx.set_source(g)
    ctx.fill()
    for k in range(12):
        yy = y0 + 40 + k * 48
        ctx.set_dash([60 + 10 * (k % 3), 90], -t * (260 + 30 * (k % 3)))
        ctx.move_to(-40, yy)
        for x in range(-40, 1121, 30):
            ctx.line_to(x, yy + 6 * math.sin(x * 0.02 + t * 3 + k))
        trazo(ctx, BLANCO, 6, 0.5)
    ctx.set_dash([])
    for yy in (y0, y1):
        ctx.move_to(-40, yy)
        ctx.line_to(1120, yy)
        trazo(ctx, INK, 7)
    # las piedras del fondo (a medio tapar) y los granos que les arranca el agua
    duele = t > T_ARRANCA
    for k, (px, py, pr, seed) in enumerate(PIEDRAS):
        cara = ("closed", "wavy") if duele and (int((t - T_ARRANCA) * 2.5) + k) % 3 == 0 else ("open", "flat")
        if not duele:
            cara = ("open", "smile")
        piedra(ctx, px, py + 4 * math.sin(t * 2 + k), pr, cara=cara, ceja="worried" if duele else None,
               look=(0.7, 0), seed=seed, s=pop(t, T_RIO6 - 0.05 + 0.08 * k, 0.4))
    if duele:
        for k in range(14):
            t0 = T_ARRANCA + 0.17 * k
            if t < t0:
                continue
            px, py, pr, _ = PIEDRAS[k % 4]
            q = (t - t0) / 2.2
            x = px + 40 + q * 900
            y = py - pr * 0.55 - 120 * min(1, q * 3) + 20 * math.sin(q * 12 + k)
            if x < 1140:
                grano(ctx, x, y, 28, cara=("happy", "smile") if k % 2 else ("open", "o"), rot=q * 6 + k)
                chispa(ctx, x - 30, y - 26, 12, 0.8 * math.sin(q * 20 + k) ** 2)
    kartel(ctx, "PIEDRAS", 300, 420, 70, t, T_PIEDRAS - 0.05, box=BLANCO)
    # flecha de la corriente
    flecha_curva(ctx, [(600, 430), (720, 370), (880, 370), (980, 430)], suave(t, T_RIO6, 0.3), AMARILLO, 14,
                 s1=prog(t, T_RIO6, 0.6))


# ------------------------------------------------------------------ 5. tan poquito que no lo sientes
T_TAN7 = b(7)
T_POQUITO7 = b(7, "poquito")
T_SIENTES = b(7, "sientes")


def d_poquito(ctx, t):
    fondo(ctx, t)
    s = pop(t, T_TAN7 - 0.05, 0.45)
    nada = t > T_SIENTES - 0.1
    vaso(ctx, 380, 1320, 1.05 * s, t, ojos="open" if not nada else "happy",
         boca="o" if t > T_TAN7 + 0.1 and not nada else ("smile" if nada else "flat"), look=(0.6, -0.4))
    # la gota de agua con su granito: con lupa
    ms = pop(t, T_POQUITO7 - 0.1, 0.4)
    medidor(ctx, 800, 640, 190, 0.035 + 0.02 * math.sin(t * 9), "SAL", s=ms)
    kartel(ctx, "CASI NADA", 800, 900, 60, t, T_POQUITO7 + 0.2, box=AMARILLO)
    if nada:
        signo(ctx, "?", 560, 640, 120, t, T_SIENTES - 0.1)
    grano(ctx, 800, 1130, 10, cara=None, s=pop(t, T_POQUITO7, 0.4), rot=t)
    chispa(ctx, 818, 1110, 12, suave(t, T_POQUITO7, 0.3) * (0.5 + 0.5 * math.sin(t * 8)))


# ------------------------------------------------------------------ 6. ¿cómo un poquito de sal hizo un mar salado?
T_ENTONCES = b(8)
T_COMO8 = b(8, "como")
T_POQUITO8 = b(8, "poquito")
T_HIZO = b(8, "hizo")
T_MAR8 = b(8, "mar")
T_SALADO8 = b(8, "salado")
GRANO_Q = (250, 1125)


def d_pregunta(ctx, t):
    fondo(ctx, t)
    z = lerp(1.75, 1.0, prog(t, T_HIZO - 0.1, 1.1, "inout"))
    with en(ctx, 0, 0):
        zoom(ctx, z, GRANO_Q[0], GRANO_Q[1] - 40)
        # el mar enorme, hasta el horizonte
        mar(ctx, -40, 1120, 620, 1500, t, amp=20, r=0)
        cara_mar(ctx, 640, 900, 1.4, t, ojos="closed" if t > T_SALADO8 else "open",
                 boca="wavy", ceja="worried", look=(-0.8, 0.5))
        # la playita con el granito, adelante
        ctx.move_to(-40, 1500)
        ctx.line_to(-40, 1210)
        ctx.curve_to(120, 1150, 330, 1170, 470, 1260)
        ctx.curve_to(540, 1310, 560, 1400, 560, 1500)
        ctx.close_path()
        rellena(ctx, ARENA, 7)
        for k in range(5):
            ctx.arc(60 + 80 * k, 1300 + 30 * (k % 2), 6, 0, TAU)
            ctx.set_source_rgba(*hx("#E8B860"), 1)
            ctx.fill()
        grano(ctx, GRANO_Q[0], GRANO_Q[1] + 6 * math.sin(t * 4), 40, cara=("open", "o"),
              look=(0.8, -0.6) if t > T_MAR8 - 0.3 else (0.0, -0.3), ceja="up",
              s=pop(t, T_ENTONCES - 0.05, 0.4))
        signo(ctx, "?", GRANO_Q[0] - 40, GRANO_Q[1] - 110, 70, t, T_COMO8 - 0.05)
    signo(ctx, "?", 540, 380, 170, t, T_MAR8 - 0.1)
    if t > T_POQUITO8 - 0.1 and t < T_HIZO + 0.2:
        kartel(ctx, "UN POQUITO", 540, 560, 64, t, T_POQUITO8 - 0.1, T_HIZO, box=BLANCO)


# ------------------------------------------------------------------ 7. por acumulación (corte seco)
T_POR9 = b(9)
T_ACUM = b(9, "acumulacion")


def d_acumulacion(ctx, t):
    fondo(ctx, t, 0.35)
    # granos que caen y se apilan
    rnd = random.Random(5)
    n = 70
    orden = list(range(n))
    random.Random(9).shuffle(orden)
    for k in range(n):
        t0 = T_POR9 - 0.05 + 0.016 * (k // 14) * 14 + 0.016 * orden[k] * 0.3
        if t < t0:
            continue
        col = k % 14
        fila = k // 14
        xs = 160 + col * 58 + rnd.uniform(-6, 6) + (20 if fila % 2 else 0)
        ys = 1330 - fila * 50
        q = clamp((t - t0) / 0.3)
        y = lerp(200, ys, ease(q, "in"))
        grano(ctx, xs, y, 26, cara=("happy", "smile") if k % 9 == 0 else None, rot=rnd.uniform(-0.3, 0.3))
    sello(ctx, "POR", 540, 640, 96, t, T_POR9 - 0.05, rot=-6, col=AMARILLO)
    sello(ctx, "ACUMULACIÓN", 540, 800, 104, t, T_ACUM - 0.02, rot=-6)


# ------------------------------------------------------------------ 8. como una alcancía
T_COMO10 = b(10)
T_ALCANCIA = b(10, "alcancia")
T_LLENA = b(10, "llena")
T_MONEDA = b(10, "moneda")
CH = (540, 1000, 1.32)
N_MON = 6


def monedas_t():
    return [T_ALCANCIA - 0.05 + 0.42 * k for k in range(N_MON)]


def d_alcancia(ctx, t):
    fondo(ctx, t)
    x, y, s = CH
    caidas = [t0 + 0.42 for t0 in monedas_t()]
    n = sum(1 for tc in caidas if t >= tc)
    bump = max([P.bump(t, tc, 0.25, 0.06) for tc in caidas] + [1.0])
    sq = s * pop(t, T_COMO10 - 0.05, 0.45)
    with en(ctx, x, y + 200, bump):
        ctx.translate(-x, -(y + 200))
        chancho(ctx, x, y, sq, lleno=n / 9 + 0.12, ojos="happy" if n else "open",
                boca="grin" if n else "smile", t=t)
    # monedas que caen de a una en la ranura
    rx, ry = x - 5 * s, y - 175 * s
    for k, t0 in enumerate(monedas_t()):
        q = clamp((t - t0) / 0.42)
        if 0 < q < 1:
            moneda(ctx, rx, lerp(320, ry, ease(q, "in")), 52, giro=q * 7)
        if t >= t0 + 0.42:
            qq = clamp((t - t0 - 0.42) / 0.5)
            if qq < 1:
                with alfa(ctx, 1 - qq):
                    texto(ctx, "+1", rx + 150, ry - 60 - 80 * qq, 64, fill=AMARILLO, sw=10)
    kartel(ctx, "DE A UNA", 540, 380, 64, t, T_MONEDA - 0.1, box=AMARILLO)


# ------------------------------------------------------------------ 9. el ciclo: el agua sube, la sal se queda
T_SOL = b(11)
T_LLEVA = b(11, "lleva")
T_NUBES = b(11, "nubes")
T_LA12 = b(12)
T_SUBIR = b(12, "subir")
T_QUEDA = b(12, "queda")
T_ESA = b(13)
T_LLUEVE = b(13, "llueve")
T_VUELVE = b(13, "vuelve")
T_TRAE = b(13, "trae")
T_POQUITO13 = b(13, "poquito")
T_VA = b(14)
T_VIENE = b(14, "viene")
SOL_C = (880, 330)
NUBE_C = (360, 400)
MAR2_Y = 1100
RIO2 = [(250, 780), (330, 900), (280, 1000), (430, 1105)]
GRANOS_MAR = [(560, 1230), (700, 1300), (850, 1215), (980, 1310), (640, 1380), (900, 1385), (480, 1340)]


def d_ciclo(ctx, t):
    fondo(ctx, t)
    # el sol
    ss = pop(t, T_SOL - 0.1, 0.45) * P.bump(t, T_SOL, 0.4, 0.1)
    brillo(ctx, *SOL_C, 300, 0.4 * suave(t, T_SOL, 0.4))
    with en(ctx, *SOL_C, ss):
        sol(ctx, 0, 0, 92, t, boca="grin", look=(-0.6, 0.6))
    # montaña con el río
    montana(ctx, 240, MAR2_Y + 10, 520, 470, MONTE, MONTE_OSC)
    ctx.move_to(-40, MAR2_Y + 40)
    ctx.curve_to(100, 960, 300, 990, 560, MAR2_Y + 20)
    ctx.line_to(560, MAR2_Y + 60)
    ctx.close_path()
    rellena(ctx, PASTO, 7)
    lluvia_a = suave(t, T_LLUEVE - 0.15, 0.3) * (1 - prog(t, T_VIENE + 0.3, 0.4))
    brillo_r = 0.6 * suave(t, T_VUELVE - 0.1, 0.4)
    if brillo_r > 0.01:
        cinta(ctx, RIO2, 40, 110)
        trazo(ctx, AMARILLO, 36, brillo_r * (1 - prog(t, T_VA, 0.5)))
    cinta(ctx, RIO2, 26, 90)
    rellena(ctx, RIO, 6)
    ctx.set_dash([24, 40], -t * 110)
    linea_en(ctx, RIO2, 0.0, 26, 90, 0.03, 0.95)
    trazo(ctx, BLANCO, 5, 0.7)
    ctx.set_dash([])
    # el mar
    mar(ctx, -40, 1120, MAR2_Y, 1460, t, r=0)
    cara_mar(ctx, 300, 1270, 0.8, t, ojos="open", boca="smile", ceja=None, look=(0.6, -0.5))
    # gotas que suben del mar a la nube
    sube = suave(t, T_LLEVA - 0.2, 0.2) * (1 - prog(t, T_LA12 + 0.6, 0.4))
    if t > T_VA:
        sube = suave(t, T_VA - 0.05, 0.3)
    if sube > 0.01:
        for k in range(9):
            ph = ((t - T_LLEVA) * 0.55 + k / 9) % 1
            x0 = 560 + (k * 61) % 440
            p = [(x0, MAR2_Y + 20), (x0 - 40, 850), (NUBE_C[0] + 260, 650), (NUBE_C[0] + 60 * math.sin(k), NUBE_C[1])]
            x, y = bez(p, ph)
            gota(ctx, x, y, 26, a=sube * min(1, (1 - ph) * 6, ph * 8), cara=("happy", "smile"), look=(-0.5, -0.6))
    # la nube (crece con el agua que sube) y la lluvia
    nk = 1 + 0.25 * prog(t, T_LLEVA, 1.6)
    nube(ctx, NUBE_C[0], NUBE_C[1] + 10 * math.sin(t * 1.4), 120 * nk * pop(t, T_LLEVA, 0.5),
         cara=("closed", "grin") if t > T_LLUEVE else ("happy", "smile"))
    if lluvia_a > 0.01:
        for k in range(16):
            ph = (t * 1.6 + k / 16) % 1
            x = NUBE_C[0] - 180 + (k * 97) % 360
            y = NUBE_C[1] + 40 + ph * 520
            gotita(ctx, x - 40 * ph, y, 12, lluvia_a * math.sin(ph * math.pi), MAR_CLARO)
    # la sal: granos con cara en el mar, que intentan subir y no pueden
    extra = 1 if t > T_POQUITO13 + 0.9 else 0
    if t > T_VA:
        extra += min(4, int((t - T_VA) / 0.4))
    for k, (gx, gy) in enumerate(GRANOS_MAR[:3 + extra + (1 if t > T_POQUITO13 + 0.9 else 0)]):
        salto = 0.0
        if T_SUBIR - 0.4 < t < T_QUEDA + 0.3:
            ph = ((t - (T_SUBIR - 0.4)) * 2.6 + k * 0.3) % 1
            salto = 120 * math.sin(ph * math.pi) ** 1.2
        triste = T_QUEDA - 0.1 < t < T_ESA + 0.6
        mira = (-0.5, -0.8) if t > T_LLEVA else (0, 0)
        cara = ("open", "flat") if triste else (("open", "o") if salto > 30 else ("happy", "smile"))
        grano(ctx, gx, gy - salto + 5 * math.sin(t * 3 + k), 34, cara=cara, look=mira,
              ceja="worried" if triste else None, rot=0.1 * math.sin(t * 2 + k),
              s=pop(t, T_SOL + 0.1 * k, 0.4) if k < 3 else pop(t, T_POQUITO13 + 0.9 if k == 3 else T_VA + 0.4 *
                                                                (k - 4), 0.4))
    # el granito nuevo que trae el río
    q = prog(t, T_TRAE - 0.1, 1.4, "inout")
    if 0 < q < 1:
        x, y = bez(RIO2, q)
        grano(ctx, x, y - 10, 26, cara=("happy", "grin"), rot=q * 5)
    if T_TRAE < t < T_VA:
        kartel(ctx, "+1", 560, 1000, 70, t, T_POQUITO13 + 0.6, T_VA - 0.1, box=AMARILLO)
    kartel(ctx, "SE QUEDA", 760, 1000, 66, t, T_QUEDA - 0.05, T_ESA + 0.3, box=BLANCO)
    # el agua va y viene: flechas del ciclo
    fa = suave(t, T_VA - 0.1, 0.3)
    if fa > 0.01:
        flecha_curva(ctx, [(980, 1060), (1040, 800), (900, 560), (560, 400)], fa, MAR_CLARO, 16,
                     s1=prog(t, T_VA - 0.1, 0.6))
        flecha_curva(ctx, [(140, 560), (60, 700), (90, 900), (180, 1000)], fa, MAR_CLARO, 16,
                     s1=prog(t, T_VIENE - 0.1, 0.6))
        kartel(ctx, "VA Y VIENE", 700, 760, 60, t, T_VA + 0.1, box=AMARILLO)


# ------------------------------------------------------------------ 10. cientos de millones de años
T_LA15 = b(15)
T_JUNTO = b(15, "junto")
T_CIENTOS = b(15, "cientos")
T_MILLONES = b(15, "millones")
T_ANOS = b(15, "anos")
TANQUE = (140, 640, 940, 1360)
PUNTOS = [(random.Random(k).uniform(0, 1), random.Random(k + 999).uniform(0, 1)) for k in range(260)]


def anos_en(t):
    q = prog(t, T_LA15 + 0.2, T_ANOS + 0.3 - (T_LA15 + 0.2), "in")
    return int(round(300_000_000 * q ** 1.6 / 1_000_000)) * 1_000_000


def fmt(n):
    return f"{n:,}".replace(",", ".")


def d_anos(ctx, t):
    fondo(ctx, t)
    x0, y0, x1, y1 = TANQUE
    s = pop(t, T_LA15 - 0.05, 0.45)
    with en(ctx, 540, 1000, s):
        ctx.translate(-540, -1000)
        ctx.save()
        rrect(ctx, x0, y0 - 60, x1 - x0, y1 - y0 + 60, 50)
        ctx.clip()
        mar(ctx, x0 - 10, x1 + 10, y0, y1 + 10, t, amp=12, r=0, borde=0)
        q = prog(t, T_LA15, T_ANOS + 0.5 - T_LA15, "in")
        n = int(len(PUNTOS) * q)
        for k, (px, py) in enumerate(PUNTOS[:n]):
            gx = lerp(x0 + 30, x1 - 30, px) + 10 * math.sin(t * 1.5 + k)
            gy = lerp(y0 + 50, y1 - 30, py) + 6 * math.cos(t * 1.2 + k)
            grano(ctx, gx, gy, 9, cara=None, rot=k + t)
        ctx.restore()
        rrect(ctx, x0, y0 - 60, x1 - x0, y1 - y0 + 60, 50)
        trazo(ctx, INK, 10)
        cara_mar(ctx, 540, 960, 1.0, t, ojos="closed" if q > 0.6 else "open",
                 boca="wavy" if q > 0.3 else "smile", ceja="worried" if q > 0.3 else None, look=(0, -0.6),
                 lengua=pop(t, T_ANOS, 0.3) * 0.9)
    # el calendario que corre
    cs = pop(t, T_LA15 + 0.05, 0.45)
    per = 0.22
    flip = ((t - T_LA15) % per) / per if T_LA15 < t < T_ANOS + 0.3 else 0.0
    calendario(ctx, 540, 400, cs, fmt(anos_en(t)), flip)
    kartel(ctx, "CIENTOS DE MILLONES", 540, 610, 56, t, T_CIENTOS - 0.05, box=AMARILLO)


# ------------------------------------------------------------------ 11. la sal tapa los continentes
T_SI16 = b(16)
T_SACARAS = b(16, "sacaras")
T_TODA16 = b(16, "toda")
T_TIRARAS = b(16, "tiraras")
T_TIERRA16 = b(16, "tierra")
T_TAPARIA = b(16, "taparia")
T_TODOS16 = b(16, "todos")
T_CONTINENTES = b(16, "continentes")
GLOBO = (540, 760, 300)
# continentes caricaturizados (x, y en radios del globo; vista centrada en el Atlántico)
CONTINENTES = [
    [(-0.98, -0.5), (-0.75, -0.74), (-0.42, -0.72), (-0.28, -0.5), (-0.42, -0.3), (-0.5, -0.08), (-0.68, -0.14),
     (-0.88, -0.28)],                                                                             # América del Norte
    [(-0.46, 0.02), (-0.24, 0.08), (-0.12, 0.26), (-0.22, 0.5), (-0.38, 0.84), (-0.47, 0.56), (-0.56, 0.24)],
    [(0.04, -0.14), (0.34, -0.2), (0.52, 0.04), (0.44, 0.36), (0.3, 0.64), (0.2, 0.48), (0.12, 0.18),
     (-0.04, 0.06)],                                                                              # África
    [(0.04, -0.3), (0.14, -0.56), (0.4, -0.68), (0.58, -0.48), (0.42, -0.3), (0.2, -0.26)],         # Europa
    [(0.58, -0.68), (0.86, -0.56), (0.98, -0.26), (0.86, -0.06), (0.66, -0.18), (0.56, -0.42)],    # Asia
    [(-0.36, -0.94), (-0.14, -0.92), (-0.18, -0.76), (-0.34, -0.78)],                             # Groenlandia
]
ORDEN_C = [2, 0, 3, 1, 4, 5]


def blob(ctx, pts, cx, cy, R):
    q = [(cx + x * R, cy + y * R) for x, y in pts]
    n = len(q)
    ctx.move_to(*q[0])
    for i in range(n):
        p0, p1, p2, p3 = q[i - 1], q[i], q[(i + 1) % n], q[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        ctx.curve_to(*c1, *c2, *p2)
    ctx.close_path()


def blanco_c(t, k):
    return prog(t, T_TAPARIA - 0.1 + 0.22 * ORDEN_C.index(k), 0.45, "out")


def d_continentes(ctx, t):
    fondo(ctx, t)
    cx, cy, R = GLOBO
    gs = pop(t, T_TIRARAS - 0.3, 0.5)
    sorpresa = t > T_TAPARIA
    if gs > 0.01:
        with en(ctx, cx, cy, gs * P.bump(t, T_TAPARIA, 0.35, 0.05)):
            ctx.translate(-cx, -cy)
            _elipse_suave(ctx, cx, cy, R * 1.6, R * 1.6, hx("#3D8BFF"), 0.22)
            ctx.arc(cx, cy, R, 0, TAU)
            g = cairo.RadialGradient(cx - R * 0.35, cy - R * 0.4, R * 0.1, cx, cy, R)
            g.add_color_stop_rgb(0, *MAR_CLARO)
            g.add_color_stop_rgb(1, *MAR)
            ctx.set_source(g)
            ctx.fill()
            ctx.save()
            ctx.arc(cx, cy, R, 0, TAU)
            ctx.clip()
            for k, c in enumerate(CONTINENTES):
                w = blanco_c(t, k)
                col = tuple(lerp(a, b_, w) for a, b_ in zip(PASTO, SAL))
                blob(ctx, c, cx, cy, R)
                rellena(ctx, col, 6)
                if w > 0.3:
                    x = cx + sum(p[0] for p in c) / len(c) * R
                    y = cy + sum(p[1] for p in c) / len(c) * R
                    chispa(ctx, x + 20, y - 10, 18 * w, w * (0.5 + 0.5 * math.sin(t * 7 + k)))
            ctx.restore()
            ctx.arc(cx, cy, R, 0, TAU)
            trazo(ctx, INK, 9)
            ctx.arc(cx, cy, R * 0.86, -2.5, -1.7)
            trazo(ctx, BLANCO, 12, 0.5)
            carita(ctx, cx, cy + R * 0.48, 0.42 * R, R / 300, ojos="wide" if sorpresa else "open",
                   boca="o" if sorpresa else "smile", ceja="up" if sorpresa else None, look=(0, -0.7))
    # la montaña de sal: sale del mar y se vuelca sobre la Tierra
    hs = pop(t, T_SACARAS - 0.1, 0.5)
    sube = prog(t, T_TIRARAS - 0.1, 0.8, "inout")
    vacia = prog(t, T_TAPARIA - 0.1, 1.5, "in")
    hx_, hy = 540, lerp(1330, 330, sube)
    k_ = hs * lerp(1.0, 0.6, sube) * (1 - vacia * 0.9)
    if k_ > 0.02:
        with en(ctx, hx_, hy, k_, 0.08 * math.sin(t * 3) * sube):
            ctx.move_to(-330, 0)
            ctx.curve_to(-260, -160, -120, -290, 0, -300)
            ctx.curve_to(120, -290, 260, -160, 330, 0)
            ctx.close_path()
            g = cairo.LinearGradient(0, -300, 0, 0)
            g.add_color_stop_rgb(0, *SAL)
            g.add_color_stop_rgb(1, *SAL_SOMBRA)
            ctx.set_source(g)
            ctx.fill_preserve()
            trazo(ctx, INK, 9)
            for j in range(8):
                chispa(ctx, -220 + 62 * j, -60 - 120 * math.sin(j * 0.9) ** 2, 16, 0.6 + 0.4 * math.sin(t * 6 + j))
            carita(ctx, 0, -120, 110, 1.1, ojos="happy", boca="grin", rubor=True)
    # el mar de donde sale (adelante de la montaña de sal); se va cuando la sal sube
    am = 1 - prog(t, T_TIRARAS + 0.2, 0.5)
    if am > 0.01:
        with alfa(ctx, am):
            mar(ctx, -40, 1120, 1300 + 200 * (1 - am), 1500, t, r=0)
            cara_mar(ctx, 300, 1400 + 200 * (1 - am), 0.6, t, ojos="wide", boca="o", ceja="up", look=(0.6, -0.8))
    # chorro de sal sobre la Tierra
    ch = suave(t, T_TAPARIA - 0.25, 0.2) * (1 - prog(t, T_CONTINENTES + 0.4, 0.3))
    if ch > 0.01:
        for k in range(26):
            ph = (t * 1.8 + k / 26) % 1
            x = hx_ + (-120 + (k * 53) % 240) * (1 - 0.4 * ph)
            y = lerp(hy + 10, cy - R * 0.4, ph)
            grano(ctx, x, y, 11, cara=None, rot=k + ph * 4, a=ch)
    kartel(ctx, "TODOS LOS CONTINENTES", 540, 1210, 56, t, T_TODOS16 - 0.05, box=BLANCO)


# ------------------------------------------------------------------ 12. una capa más alta que un edificio de 40 pisos
T_LA17 = b(17)
T_CAPA = b(17, "capa")
T_MAS = b(17, "mas")
T_EDIFICIO = b(17, "edificio")
T_40 = b(17, "40")
T_PISOS = b(17, "pisos")
SUELO = 1390
PISO_H = 21.0
ED = (650, 270)              # centro x, ancho
TECHO = SUELO - 40 * PISO_H


def nivel_capa(t):
    q = prog(t, T_CAPA - 0.1, T_PISOS + 0.2 - (T_CAPA - 0.1), "inout")
    return lerp(SUELO, TECHO - 60, q)


def d_edificio(ctx, t):
    fondo(ctx, t)
    ex, ew = ED
    es = pop(t, T_LA17 - 0.05, 0.4)
    # edificio
    with en(ctx, ex, SUELO, es):
        ctx.translate(-ex, -SUELO)
        rrect(ctx, ex - ew / 2, TECHO, ew, SUELO - TECHO, 10)
        g = cairo.LinearGradient(ex - ew / 2, 0, ex + ew / 2, 0)
        g.add_color_stop_rgb(0, *LADRILLO)
        g.add_color_stop_rgb(1, *LADRILLO_OSC)
        ctx.set_source(g)
        ctx.fill_preserve()
        trazo(ctx, INK, 8)
        for f in range(40):
            yy = SUELO - (f + 1) * PISO_H
            for c in range(5):
                xx = ex - ew / 2 + 22 + c * 47
                ctx.rectangle(xx, yy + 5, 30, 11)
                on = (f * 7 + c * 3) % 5 != 0
                ctx.set_source_rgb(*(VENTANA if on else hx("#5B3A6E")))
                ctx.fill()
        rrect(ctx, ex - ew / 2 - 14, TECHO - 20, ew + 28, 30, 10)
        rellena(ctx, LADRILLO_OSC, 7)
        ctx.move_to(ex + 60, TECHO - 20)
        ctx.line_to(ex + 60, TECHO - 110)
        trazo(ctx, INK, 7)
        ctx.arc(ex + 60, TECHO - 114, 10, 0, TAU)
        rellena(ctx, ROJO, 5)
        carita(ctx, ex, TECHO + 70, 90, 0.8, ojos="wide" if t > T_MAS else "open",
               boca="o" if t > T_MAS else "smile", ceja="up" if t > T_MAS else None, look=(0, 0.8), rubor=True)
    # personita para la escala
    px = 230
    ctx.arc(px, SUELO - 66, 16, 0, TAU)
    rellena(ctx, hx("#F8C9A2"), 5)
    rrect(ctx, px - 16, SUELO - 50, 32, 50, 12)
    rellena(ctx, hx("#3FA9F5"), 5)
    # suelo
    ctx.rectangle(-40, SUELO, 1160, 200)
    rellena(ctx, PASTO, 7)
    # la capa de sal que sube
    L = nivel_capa(t)
    if L < SUELO - 2:
        ctx.move_to(-40, SUELO)
        ctx.line_to(-40, L)
        for x in range(-40, 1121, 30):
            ctx.line_to(x, L + 8 * math.sin(x * 0.05) + 4 * math.sin(x * 0.13 + 1))
        ctx.line_to(1120, SUELO)
        ctx.close_path()
        g = cairo.LinearGradient(0, L, 0, SUELO)
        g.add_color_stop_rgb(0, *SAL)
        g.add_color_stop_rgb(1, *hx("#DCEBFA"))
        ctx.set_source(g)
        ctx.fill_preserve()
        trazo(ctx, INK, 8)
        # el edificio enterrado, como fantasma
        ctx.save()
        ctx.rectangle(-40, L + 6, 1160, SUELO - L)
        ctx.clip()
        with alfa(ctx, 0.5 * es):
            rrect(ctx, ex - ew / 2, TECHO, ew, SUELO - TECHO, 10)
            ctx.set_dash([18, 12])
            trazo(ctx, hx("#7FA8D8"), 6)
            ctx.set_dash([])
            for f in range(40):
                yy = SUELO - (f + 1) * PISO_H
                for c in range(5):
                    ctx.rectangle(ex - ew / 2 + 22 + c * 47, yy + 5, 30, 11)
            ctx.set_source_rgba(*hx("#A9C6E8"), 0.8)
            ctx.fill()
        ctx.restore()
        for k in range(14):
            x = 40 + (k * 83) % 1000
            y = lerp(L + 30, SUELO - 20, ((k * 0.37) % 1))
            if y > L + 20:
                grano(ctx, x, y, 9, cara=None, rot=k)
            chispa(ctx, x + 30, L + 14, 12, 0.6 + 0.4 * math.sin(t * 8 + k))
        # contador de pisos
        piso = int(clamp((SUELO - L) / PISO_H, 0, 40))
        if piso >= 1:
            P.cartel(ctx, f"PISO {piso}", 230, L - 70, 50, box=BLANCO)
        # regla
        ctx.move_to(990, SUELO)
        ctx.line_to(990, L)
        trazo(ctx, AMARILLO, 10)
    if t > T_PISOS - 0.1:
        tilde(ctx, 900, TECHO - 160, 1.2 * pop(t, T_PISOS - 0.1, 0.35))
    kartel(ctx, "40 PISOS", 540, 300, 76, t, T_40 - 0.05, box=AMARILLO)


# ------------------------------------------------------------------ 13. cierre (= apertura)
T_CASI = b(18)
T_DULCE18 = b(18, "dulce")


# ------------------------------------------------------------------ escenas
ESCENAS = [
    (0.0, d_apertura),
    (b(3) - 0.05, d_gota),
    (b(4) - 0.05, d_botella),
    (b(6) - 0.05, d_piedras),
    (b(7) - 0.05, d_poquito),
    (b(8) - 0.05, d_pregunta),
    (b(9) - 0.05, d_acumulacion),
    (b(10) - 0.05, d_alcancia),
    (b(11) - 0.05, d_ciclo),
    (b(15) - 0.05, d_anos),
    (b(16) - 0.05, d_continentes),
    (b(17) - 0.05, d_edificio),
    (b(18) - 0.05, d_cierre),
]
CORTE_SECO = {d_acumulacion}
XF = 0.18


def punch(t, t0, d=0.3, amp=0.05):
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


def deriva(t, i):
    """Acercamiento lento de cámara dentro de cada escena del medio (la escena nunca queda quieta)."""
    if i == 0 or i == len(ESCENAS) - 1:
        return 1.0
    t0 = ESCENAS[i][0]
    t1 = ESCENAS[i + 1][0]
    return lerp(1.0, 1.035, clamp((t - t0) / (t1 - t0)))


def escena(t):
    return max(k for k, (t0, _) in enumerate(ESCENAS) if t >= t0)


def capa(ctx, fn, t, z=1.0):
    ctx.save()
    zoom(ctx, z)
    fn(ctx, t)
    ctx.restore()


def componer(ctx, t):
    i = escena(t)
    t0, fn = ESCENAS[i]
    dt = t - t0
    sin_punch = i == len(ESCENAS) - 1          # el cierre termina igual al inicio
    if i > 0 and dt < XF and fn not in CORTE_SECO:
        capa(ctx, ESCENAS[i - 1][1], t, deriva(t, i - 1))
        ctx.save()
        ctx.push_group()
        if not sin_punch:
            zoom(ctx, punch(t, t0))
        zoom(ctx, deriva(t, i))
        fn(ctx, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(clamp(dt / XF))
        ctx.restore()
        return
    if i > 0 and not sin_punch:
        zoom(ctx, punch(t, t0))
    zoom(ctx, deriva(t, i))
    fn(ctx, t)


CAPS = motor.Captions(WORDS, {"size": 76, "y": 1500, "max_palabras": 3, "max_letras": 18})


def cuadro(t):
    s, ctx = lienzo()
    try:
        componer(ctx, min(t, TOTAL))
    except Exception as e:
        raise RuntimeError(f"falló el cuadro en t={t:.3f}: {e}") from e
    im = Image.fromarray(a_rgb(s))
    CAPS.draw(im, t)
    return im


# ------------------------------------------------------------------ sonido (solo golpes cortos)
def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    # 1. apertura
    ev(T_DULCE0 - 0.05, "pop", 0.3)
    ev(T_SALADO1 - 0.05, "golpe", 0.45)
    for k in range(4):
        ev(T_ENTRA - 0.2 + 0.25 * k + 0.6, "plop", 0.22)
    ev(T_DE2 - 0.1, "pop", 0.4)
    ev(T_SAL2 - 0.05, "pop", 0.3)
    # 2. gota
    ev(T_EL3 - 0.05, "pop", 0.4)
    ev(T_TAN3, "clunk", 0.4)
    ev(T_DULCE3, "ding", 0.35)
    # 3. botella
    ev(T_MIRA - 0.05, "pop", 0.4)
    ev(T_ETIQUETA, "pop", 0.35)
    for k in range(4):
        ev(T_ETIQUETA + 0.15 + 0.1 * k, "tick", 0.15, f=900 + 100 * k, d=0.04)
    ev(T_SODIO - 0.05, "ding", 0.4)
    ev(T_MISMO - 0.15, "pop", 0.35)
    ev(T_SALA - 0.05, "golpe", 0.35)
    # 4. piedras
    for k in range(4):
        ev(T_RIO6 - 0.05 + 0.08 * k, "pop", 0.2)
    for k in range(0, 14, 2):
        ev(T_ARRANCA + 0.17 * k, "crunch", 0.2, d=0.12)
    ev(T_PIEDRAS - 0.05, "pop", 0.3)
    # 5. poquito
    ev(T_TAN7 - 0.05, "pop", 0.35)
    ev(T_POQUITO7 - 0.1, "clic", 0.35)
    ev(T_SIENTES - 0.1, "pop", 0.3)
    # 6. pregunta
    ev(T_ENTONCES - 0.05, "pop", 0.35)
    ev(T_MAR8 - 0.1, "pop", 0.4)
    # 7. acumulación (corte seco)
    ev(T_POR9 - 0.05, "golpe", 0.5)
    for k in range(0, 70, 6):
        ev(T_POR9 - 0.05 + k * 0.016 + 0.3, "tick", 0.12, f=1300 + 15 * k, d=0.03)
    ev(T_ACUM - 0.02, "golpe", 0.5)
    # 8. alcancía
    ev(T_COMO10 - 0.05, "pop", 0.35)
    for t0 in monedas_t():
        ev(t0 + 0.42, "ding", 0.25)
    # 9. ciclo
    ev(T_SOL - 0.1, "pop", 0.4)
    ev(T_LLEVA, "plop", 0.25)
    ev(T_SUBIR - 0.2, "clic", 0.25)
    ev(T_QUEDA - 0.05, "clunk", 0.4)
    ev(T_LLUEVE - 0.1, "plop", 0.3)
    ev(T_POQUITO13 + 0.9, "pop", 0.35)
    ev(T_VA - 0.05, "pop", 0.35)
    for k in range(4):
        ev(T_VA + 0.4 * (k + 1), "pop", 0.18)
    # 10. años
    ev(T_LA15 - 0.05, "pop", 0.4)
    j = 0
    while T_LA15 + 0.22 * j < T_ANOS + 0.3:
        ev(T_LA15 + 0.22 * j, "tick", 0.1, f=1500, d=0.03)
        j += 1
    ev(T_CIENTOS - 0.05, "ding", 0.35)
    # 11. continentes
    ev(T_SACARAS - 0.1, "pop", 0.4)
    ev(T_TIRARAS - 0.1, "clic", 0.3)
    for k in range(6):
        ev(T_TAPARIA - 0.1 + 0.22 * k, "crunch", 0.2, d=0.12)
    ev(T_TODOS16 - 0.05, "pop", 0.3)
    # 12. edificio
    ev(T_LA17 - 0.05, "pop", 0.4)
    for k in range(10):
        ev(lerp(T_CAPA, T_PISOS, k / 10), "tick", 0.12, f=700 + 80 * k, d=0.04)
    ev(T_40 - 0.05, "golpe", 0.45)
    ev(T_PISOS - 0.1, "ding", 0.35)
    # 13. cierre
    ev(T_DULCE18 - 0.1, "pop", 0.25)
    return E


def pista_efectos():
    n = int((TOTAL + 3) * SR)
    mix = np.zeros(n, np.float32)
    for t, k, v, kw in eventos():
        x = (K.s_zap(**kw) if k == "zap" else K.snd(k, **kw)) * v
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


def hoja(tiempos, salida, cols=5):
    """Hoja de fotogramas: miniaturas con su segundo, para revisar antes del render."""
    tw, th = 270, 480
    filas = math.ceil(len(tiempos) / cols)
    im = Image.new("RGB", (cols * tw, filas * th), (0, 0, 0))
    d = ImageDraw.Draw(im)
    for k, t in enumerate(tiempos):
        x, y = (k % cols) * tw, (k // cols) * th
        im.paste(cuadro(t).resize((tw, th), Image.LANCZOS), (x, y))
        d.rectangle((x, y, x + 78, y + 24), fill=(0, 0, 0))
        d.text((x + 5, y + 5), f"{t:.2f}", fill=(255, 255, 0))
    im.save(salida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fotos")
    ap.add_argument("--hoja", help="segundos separados por coma; arma una hoja de miniaturas")
    ap.add_argument("--dir", default=os.path.join(AQUI, "fotos"))
    ap.add_argument("--nombre", default="hoja.png")
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "por_que_el_mar_es_salado.mp4"))
    ap.add_argument("--hilos", type=int, default=2)
    ap.add_argument("--probar", action="store_true", help="dibuja 1 de cada 6 cuadros para cazar errores")
    a = ap.parse_args()
    if a.probar:
        for f in range(0, int(TOTAL * FPS), 6):
            cuadro(f / FPS)
        pista_efectos()
        print("sin errores")
        return
    if a.hoja:
        os.makedirs(a.dir, exist_ok=True)
        hoja([float(x) for x in a.hoja.split(",")], os.path.join(a.dir, a.nombre))
        print("hoja en", os.path.join(a.dir, a.nombre))
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

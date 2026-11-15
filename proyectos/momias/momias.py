"""Short "¿Por qué Europa comía momias?" — animación procedural (armazón de anestesia.py y luna.py).

Historia oscura: tono sobrio, sin personajes, sin caras y sin caricaturas (regla V3). Todo se cuenta con objetos:
el frasco de botica, el sarcófago (sin rasgos), el mortero, la corona, el libro, la brea, la lista de precios.
Sin flechas de giro ni sonidos sostenidos (corrección de Luna v2): solo golpes cortos. El último cuadro es igual
al primero (loop).

    python proyectos/momias/momias.py --hoja 0,3,6      # hoja de fotogramas -> proyectos/momias/fotos/hoja.png
    python proyectos/momias/momias.py --probar
    python proyectos/momias/momias.py                   # render -> salidas/por_que_europa_comia_momias.mp4
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from multiprocessing import Pool

import cairo
import numpy as np
from PIL import Image, ImageDraw

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
    "Durante siglos, los europeos comieron momias para curarse.",            # b0
    "No era brujería: lo recetaban los médicos.",                            # b1
    "¿Cómo terminó un muerto egipcio en una farmacia?",                      # b2
    "Las boticas vendían momia molida, en frascos.",                         # b3
    "Hasta un rey de Francia la llevaba siempre encima.",                    # b4
    "Todo empezó con un error de traducción.",                               # b5
    "El remedio original era una brea negra de Persia.",                     # b6
    "Se llamaba mumia, y las momias parecían cubiertas de ella.",            # b7
    "Primero rasparon esa costra oscura de los cuerpos.",                    # b8
    "Después, directamente, molieron el cuerpo entero.",                     # b9
    "Las tumbas de Egipto se saquearon para llenar frascos.",                # b10
    "Pero las momias no alcanzaban para tanta demanda.",                     # b11
    "Entonces aparecieron las falsas, hechas con muertos recientes.",        # b12
    "Cuerpos de ejecutados, secados al sol y vendidos como antiguos.",       # b13
    "Nadie notaba la diferencia, porque nunca curó nada.",                   # b14
    "En 1924, un laboratorio alemán todavía la vendía.",                     # b15
    "Polvo de momia egipcia, a 12 marcos el kilo.",                          # b16
    "Fue el último rastro de una historia difícil de creer:",                # b17
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


# ------------------------------------------------------------------ colores (paleta sobria de botica y desierto)
MADERA = hx("#7A4E2D")
MADERA_OSC = hx("#55341C")
MADERA_CLARA = hx("#9C6A42")
CUERO = hx("#3E2A1E")
CUERO_CLARO = hx("#8A5A34")
ORO = hx("#E0B43C")
ORO_OSC = hx("#B8892A")
ORO_CLARO = hx("#F3D573")
TURQ = hx("#2FA8A0")
ACERO = hx("#C9CFD8")
CREMA = hx("#F6EEDC")
ROJO = hx("#E5383B")
ROJO_OSC = hx("#A32226")
LUZ = hx("#FFE6A8")
VIDRIO = hx("#BFE3FF")
VIDRIO_OSC = hx("#7FA9C9")
CORCHO = hx("#B88A5A")
POLVO = hx("#4A3423")
POLVO_CLARO = hx("#6B4D35")
VENDA = hx("#DCCBA2")
VENDA_OSC = hx("#9A855C")
COSTRA = hx("#231A14")
BREA = hx("#120E0C")
PIEDRA = hx("#B9B4AC")
PIEDRA_OSC = hx("#6E6A64")
PIEDRA_CLARA = hx("#DAD6CF")
ARENA = hx("#E2C48D")
ARENA_OSC = hx("#B8935A")
PIEDRA_ARENA = hx("#CDAE78")
ROCA = hx("#3A3440")
ROCA_CLARA = hx("#544C5C")
BARRO = hx("#B5673F")
BARRO_OSC = hx("#7C4226")
TERCIOPELO = hx("#8E1F2F")
VIOLETA = hx("#7B5BD6")
VERDE = hx("#2BD45A")
SOMBRA = hx("#141A33")
LADRILLO = hx("#5A6079")
LADRILLO_OSC = hx("#3E4359")
KF = 60 * round(14 * TOTAL / 60) / (14 * TOTAL)      # el fondo de puntos cierra justo en el loop


# ------------------------------------------------------------------ ayudas
@contextmanager
def en(ctx, x, y, s=1.0, rot=0.0):
    ctx.save()
    ctx.translate(x, y)
    if rot:
        ctx.rotate(rot)
    s = max(s, 1e-3)
    ctx.scale(s, s)
    try:
        yield
    finally:
        ctx.restore()


@contextmanager
def alfa(ctx, a):
    ctx.push_group()
    try:
        yield
    finally:
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(clamp(a))


def trazo(ctx, col=INK, w=7.0, a=1.0):
    ctx.set_source_rgba(*col, a)
    ctx.set_line_width(w)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()


def rellena(ctx, col, w=7.0, borde=INK, a=1.0):
    ctx.set_source_rgba(*col, a)
    ctx.fill_preserve()
    trazo(ctx, borde, w)


def elipse(ctx, x, y, rx, ry):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(max(rx, 1e-3), max(ry, 1e-3))
    ctx.new_sub_path()
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()


def fondo(ctx, t, oscuro=0.0, calido=0.0):
    fondo_azul(ctx, t * KF)
    if oscuro > 0:
        ctx.set_source_rgba(0.027, 0.043, 0.11, oscuro)
        ctx.paint()
    if calido > 0:
        ctx.set_source_rgba(1.0, 0.62, 0.25, calido)
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


def sacudida(t, t0, d=0.35, amp=14.0):
    if t < t0 or t > t0 + d:
        return 0.0, 0.0
    q = (t - t0) / d
    k = amp * (1 - q) ** 2
    return k * math.sin(t * 90), k * math.cos(t * 70)


def luz_cenital(ctx, x, a=1.0, ancho=560, y1=1300):
    if a <= 0.01:
        return
    g = cairo.LinearGradient(0, 0, 0, y1)
    g.add_color_stop_rgba(0, *LUZ, 0.30 * a)
    g.add_color_stop_rgba(1, *LUZ, 0.04 * a)
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
    with en(ctx, x, y, 1.0, math.radians(ang)):
        for lw, col in ((grosor + 12, INK), (grosor, ROJO)):
            ctx.move_to(-w / 2, 0)
            ctx.line_to(-w / 2 + w * p, 0)
            trazo(ctx, col, lw)


def sello(ctx, txt, x, y, size, t, t0, rot=-8, col=ROJO):
    """Sello de goma que cae de golpe."""
    if t < t0:
        return
    q = clamp((t - t0) / 0.14)
    sc = lerp(2.4, 1.0, ease(q, "in"))
    with en(ctx, x, y, sc, math.radians(rot)), alfa(ctx, min(1.0, q * 1.6)):
        P.fuente(ctx, P.LILITA, size)
        tw = ctx.text_extents(txt)[4]
        bw, bh = tw + 80, size * 1.4
        rrect(ctx, -bw / 2, -bh / 2, bw, bh, 16)
        ctx.set_source_rgb(*CREMA)
        ctx.fill()
        rrect(ctx, -bw / 2, -bh / 2, bw, bh, 16)
        trazo(ctx, col, 11)
        rrect(ctx, -bw / 2 + 15, -bh / 2 + 15, bw - 30, bh - 30, 8)
        trazo(ctx, col, 4)
        texto(ctx, txt, 0, size * 0.04, size, fill=col, stroke=None)


def renglones(ctx, x, y, w, n, gap=40, seed=1, p=1.0, col=(0.45, 0.4, 0.33), alto=12):
    anchos = rng(seed).uniform(0.55, 1.0, n)
    tot = p * n
    for k in range(n):
        f = clamp(tot - k)
        if f <= 0:
            break
        ctx.rectangle(x, y + k * gap, w * anchos[k] * f, alto)
    ctx.set_source_rgba(*col, 0.55)
    ctx.fill()


# ------------------------------------------------------------------ objetos
def tabla(ctx, y, x0=-40, x1=1120):
    ctx.rectangle(x0, y, x1 - x0, 44)
    ctx.set_source_rgb(*MADERA)
    ctx.fill()
    ctx.rectangle(x0, y + 44, x1 - x0, 16)
    ctx.set_source_rgb(*MADERA_OSC)
    ctx.fill()
    ctx.rectangle(x0, y, x1 - x0, 7)
    ctx.set_source_rgb(*MADERA_CLARA)
    ctx.fill()
    ctx.rectangle(x0, y, x1 - x0, 60)
    trazo(ctx, INK, 6)


def frasco(ctx, x, y, s=1.0, nivel=1.0, etiqueta="MUMIA", a=1.0, tam=None):
    """Frasco de vidrio con corcho; (x, y) es el centro de la base."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        _elipse_suave(ctx, 0, 4, 120, 22, (0, 0, 0), 0.45)
        rrect(ctx, -90, -240, 180, 240, 36)
        ctx.set_source_rgba(*VIDRIO, 0.30)
        ctx.fill()
        if nivel > 0.01:
            ctx.save()
            rrect(ctx, -90, -240, 180, 240, 36)
            ctx.clip()
            top = -8 - 205 * clamp(nivel)
            ctx.rectangle(-90, top, 180, -top)
            ctx.set_source_rgb(*POLVO)
            ctx.fill()
            elipse(ctx, 0, top, 90, 12)
            ctx.set_source_rgb(*POLVO_CLARO)
            ctx.fill()
            ctx.restore()
        rrect(ctx, -90, -240, 180, 240, 36)
        trazo(ctx)
        ctx.move_to(-64, -205)
        ctx.line_to(-64, -70)
        trazo(ctx, BLANCO, 10, 0.45)
        rrect(ctx, -58, -268, 116, 40, 10)
        rellena(ctx, VIDRIO_OSC)
        rrect(ctx, -46, -306, 92, 48, 12)
        rellena(ctx, CORCHO)
        if etiqueta:
            rrect(ctx, -78, -168, 156, 72, 10)
            rellena(ctx, CREMA, w=5)
            texto(ctx, etiqueta, 0, -132, tam or (38 if len(etiqueta) <= 6 else 26), fill=INK, stroke=None)


def sarcofago(ctx, x, y, s=1.0, a=1.0, brillo=0.0):
    """Sarcófago de pie, sin rasgos; (x, y) es el centro de la base. Mide 610 de alto con s = 1."""
    if s <= 0.01 or a <= 0.01:
        return

    def forma():
        ctx.move_to(-62, 0)
        ctx.line_to(-112, -420)
        ctx.curve_to(-118, -500, -90, -600, 0, -610)
        ctx.curve_to(90, -600, 118, -500, 112, -420)
        ctx.line_to(62, 0)
        ctx.close_path()

    with en(ctx, x, y, s):
        if brillo > 0.01:
            _elipse_suave(ctx, 0, -320, 340, 500, LUZ, 0.38 * brillo)
        with alfa(ctx, a):
            forma()
            ctx.set_source_rgb(*ORO)
            ctx.fill()
            ctx.save()
            forma()
            ctx.clip()
            for k in range(9):
                ctx.rectangle(-130, -610 + k * 26, 260, 13)
            ctx.set_source_rgb(*TURQ)
            ctx.fill()
            elipse(ctx, 0, -500, 58, 74)
            ctx.set_source_rgb(*ORO_CLARO)
            ctx.fill_preserve()
            trazo(ctx, INK, 5)
            for k, col in enumerate((TURQ, ROJO_OSC, TURQ)):
                ctx.new_sub_path()
                ctx.arc(0, -420, 70 + k * 22, 0.15 * math.pi, 0.85 * math.pi)
                ctx.set_source_rgb(*col)
                ctx.set_line_width(14)
                ctx.set_line_cap(cairo.LINE_CAP_BUTT)
                ctx.stroke()
            for yy in (-250, -170, -90):
                ctx.rectangle(-130, yy, 260, 16)
            ctx.set_source_rgb(*TURQ)
            ctx.fill()
            ctx.rectangle(-12, -300, 24, 300)
            ctx.set_source_rgb(*ORO_OSC)
            ctx.fill()
            ctx.restore()
            forma()
            trazo(ctx, INK, 8)


def momia(ctx, x, y, s=1.0, osc=0.0, a=1.0, rot=0.0):
    """Cuerpo vendado, acostado, con la cabeza a la izquierda y sin rasgos; (x, y) es el centro."""
    if s <= 0.01 or a <= 0.01:
        return
    base = mezcla(VENDA, COSTRA, osc)
    linea = mezcla(VENDA_OSC, (0.04, 0.03, 0.03), osc)

    def forma():
        ctx.move_to(-215, -78)
        ctx.curve_to(-120, -110, 40, -92, 330, -52)
        ctx.curve_to(362, -40, 362, 40, 330, 52)
        ctx.curve_to(40, 92, -120, 110, -215, 78)
        ctx.curve_to(-250, 50, -250, -50, -215, -78)
        ctx.close_path()
        ctx.new_sub_path()
        ctx.arc(-292, 0, 64, 0, TAU)

    with en(ctx, x, y, s, rot), alfa(ctx, a):
        forma()
        trazo(ctx, INK, 14)
        forma()
        ctx.set_source_rgb(*base)
        ctx.fill()
        ctx.save()
        forma()
        ctx.clip()
        for k in range(-8, 12):
            ctx.move_to(k * 58 - 40, -130)
            ctx.line_to(k * 58 + 40, 130)
        trazo(ctx, linea, 6)
        for k in range(-9, 12):
            ctx.move_to(k * 58 + 59, -130)
            ctx.line_to(k * 58 - 1, 130)
        trazo(ctx, linea, 4, 0.5)
        ctx.restore()


def mortero_fondo(ctx, x, y, s=1.0, nivel=0.0):
    with en(ctx, x, y, s):
        _elipse_suave(ctx, 0, 6, 190, 28, (0, 0, 0), 0.45)
        elipse(ctx, 0, -170, 150, 30)
        rellena(ctx, PIEDRA_OSC)
        if nivel > 0.01:
            elipse(ctx, 0, -163, 118 * clamp(0.45 + 0.55 * nivel), 19)
            ctx.set_source_rgb(*POLVO)
            ctx.fill()


def mortero_mano(ctx, x, y, s=1.0, sube=1.0):
    with en(ctx, x, y, s):
        with en(ctx, 55, -150 - 110 * sube, 1.0, math.radians(22)):
            rrect(ctx, -24, -290, 48, 300, 24)
            rellena(ctx, PIEDRA_CLARA)


def mortero_frente(ctx, x, y, s=1.0):
    with en(ctx, x, y, s):
        ctx.move_to(-150, -170)
        ctx.curve_to(-150, -40, -110, -8, -80, 0)
        ctx.line_to(80, 0)
        ctx.curve_to(110, -8, 150, -40, 150, -170)
        ctx.curve_to(100, -138, -100, -138, -150, -170)
        ctx.close_path()
        rellena(ctx, PIEDRA)
        ctx.move_to(-108, -110)
        ctx.curve_to(-104, -60, -86, -34, -66, -24)
        trazo(ctx, PIEDRA_CLARA, 9)


def corona(ctx, x, y, s=1.0):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        pts = [(-160, 0), (-180, -150), (-100, -70), (-60, -190), (0, -80), (60, -190), (100, -70), (180, -150),
               (160, 0)]
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        rellena(ctx, ORO, w=8)
        rrect(ctx, -168, -10, 336, 58, 14)
        rellena(ctx, ORO_OSC, w=8)
        for px, py in ((-180, -150), (-60, -190), (60, -190), (180, -150)):
            elipse(ctx, px, py, 20, 20)
            rellena(ctx, ORO_CLARO, w=6)
        for k, col in enumerate((ROJO, TURQ, ROJO)):
            elipse(ctx, -90 + 90 * k, 19, 16, 16)
            rellena(ctx, col, w=5)


def cojin(ctx, x, y, s=1.0):
    with en(ctx, x, y, s):
        _elipse_suave(ctx, 0, 70, 260, 30, (0, 0, 0), 0.45)
        ctx.move_to(-230, -40)
        ctx.curve_to(-120, -70, 120, -70, 230, -40)
        ctx.curve_to(250, 0, 250, 30, 230, 60)
        ctx.curve_to(120, 80, -120, 80, -230, 60)
        ctx.curve_to(-250, 30, -250, 0, -230, -40)
        ctx.close_path()
        rellena(ctx, TERCIOPELO, w=8)
        for sx in (-1, 1):
            elipse(ctx, sx * 236, 62, 14, 14)
            rellena(ctx, ORO, w=5)


def bolsa(ctx, x, y, s=1.0, ang=0.0):
    """Bolsita de cuero colgada; (x, y) es el punto del que cuelga."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s, ang):
        ctx.move_to(0, 0)
        ctx.line_to(0, 70)
        trazo(ctx, CUERO, 9)
        ctx.move_to(-24, 70)
        ctx.curve_to(-110, 120, -100, 250, 0, 250)
        ctx.curve_to(100, 250, 110, 120, 24, 70)
        ctx.close_path()
        rellena(ctx, CUERO_CLARO)
        rrect(ctx, -34, 62, 68, 22, 8)
        rellena(ctx, ORO, w=5)
        rrect(ctx, -60, 150, 120, 52, 8)
        rellena(ctx, CREMA, w=4)
        texto(ctx, "MUMIA", 0, 177, 30, fill=INK, stroke=None)


def papel(ctx, w, h):
    ctx.rectangle(-w / 2 + 10, -h / 2 + 12, w, h)
    ctx.set_source_rgba(*INK, 0.55)
    ctx.fill()
    ctx.rectangle(-w / 2, -h / 2, w, h)
    rellena(ctx, CREMA, w=6)


def gota(ctx, x, y, s=1.0, col=BREA):
    with en(ctx, x, y, s):
        ctx.move_to(0, -50)
        ctx.curve_to(40, 10, 34, 46, 0, 46)
        ctx.curve_to(-34, 46, -40, 10, 0, -50)
        ctx.close_path()
        rellena(ctx, col, w=5)
        elipse(ctx, -10, 14, 6, 11)
        ctx.set_source_rgba(1, 1, 1, 0.35)
        ctx.fill()


def cuenco(ctx, x, y, s=1.0, nivel=1.0, col=BREA):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        _elipse_suave(ctx, 0, 4, 150, 22, (0, 0, 0), 0.4)
        elipse(ctx, 0, -90, 130, 26)
        rellena(ctx, BARRO_OSC)
        if nivel > 0.01:
            elipse(ctx, 0, -85, 112 * clamp(0.4 + 0.6 * nivel), 18)
            ctx.set_source_rgb(*col)
            ctx.fill()
            elipse(ctx, -30, -88, 26 * clamp(nivel), 5)
            ctx.set_source_rgba(1, 1, 1, 0.3)
            ctx.fill()
        ctx.move_to(-130, -90)
        ctx.curve_to(-120, -10, -60, 0, -40, 0)
        ctx.line_to(40, 0)
        ctx.curve_to(60, 0, 120, -10, 130, -90)
        ctx.curve_to(90, -62, -90, -62, -130, -90)
        ctx.close_path()
        rellena(ctx, BARRO)


def cuchara(ctx, x, y, s=1.0, ang=0.0):
    """Cuchara con polvo; el mango sale hacia la izquierda."""
    with en(ctx, x, y, s, ang):
        ctx.move_to(-40, 0)
        ctx.line_to(-420, 0)
        trazo(ctx, INK, 28)
        ctx.move_to(-40, 0)
        ctx.line_to(-420, 0)
        trazo(ctx, ACERO, 15)
        elipse(ctx, 0, 0, 74, 42)
        rellena(ctx, ACERO)
        ctx.move_to(-54, -4)
        ctx.curve_to(-32, -64, 32, -64, 54, -4)
        ctx.close_path()
        rellena(ctx, POLVO, w=5)


def pluma(ctx, x, y, s=1.0):
    with en(ctx, x, y, s, math.radians(35)):
        ctx.move_to(0, 0)
        ctx.line_to(0, -60)
        trazo(ctx, INK, 8)
        ctx.move_to(0, -50)
        ctx.curve_to(-46, -120, -40, -230, 0, -290)
        ctx.curve_to(40, -230, 46, -120, 0, -50)
        ctx.close_path()
        rellena(ctx, CREMA, w=6)
        ctx.move_to(0, -60)
        ctx.line_to(0, -270)
        trazo(ctx, VENDA_OSC, 4)


def libro(ctx, x, y, w=880, h=600):
    with en(ctx, x, y):
        _elipse_suave(ctx, 0, h / 2 + 20, w * 0.6, 40, (0, 0, 0), 0.45)
        rrect(ctx, -w / 2 - 20, -h / 2 - 14, w + 40, h + 34, 18)
        rellena(ctx, MADERA_OSC, w=8)
        for sx in (-1, 1):
            x0 = -w / 2 if sx < 0 else 4
            rrect(ctx, x0, -h / 2, w / 2 - 4, h, 8)
            rellena(ctx, CREMA, w=6)
        g = cairo.LinearGradient(-60, 0, 60, 0)
        g.add_color_stop_rgba(0, 0, 0, 0, 0)
        g.add_color_stop_rgba(0.5, 0, 0, 0, 0.22)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.rectangle(-60, -h / 2, 120, h)
        ctx.set_source(g)
        ctx.fill()


def piramide(ctx, x, y, w, h, a=1.0):
    with alfa(ctx, a):
        ctx.move_to(x - w / 2, y)
        ctx.line_to(x, y - h)
        ctx.line_to(x + w * 0.14, y)
        ctx.close_path()
        rellena(ctx, ARENA, w=6)
        ctx.move_to(x + w * 0.14, y)
        ctx.line_to(x, y - h)
        ctx.line_to(x + w / 2, y)
        ctx.close_path()
        rellena(ctx, ARENA_OSC, w=6)


def arena(ctx, y0):
    g = cairo.LinearGradient(0, y0, 0, H)
    g.add_color_stop_rgb(0, *ARENA)
    g.add_color_stop_rgb(1, *ARENA_OSC)
    ctx.move_to(-10, y0 + 20)
    ctx.curve_to(300, y0 - 30, 700, y0 + 40, 1090, y0 - 10)
    ctx.line_to(1090, H)
    ctx.line_to(-10, H)
    ctx.close_path()
    ctx.set_source(g)
    ctx.fill_preserve()
    trazo(ctx, INK, 6)


def tumba(ctx, x, y, s=1.0):
    with en(ctx, x, y, s):
        ctx.move_to(-110, 0)
        ctx.line_to(-90, -300)
        ctx.line_to(90, -300)
        ctx.line_to(110, 0)
        ctx.close_path()
        rellena(ctx, PIEDRA_ARENA)
        ctx.rectangle(-104, -332, 208, 38)
        rellena(ctx, ARENA_OSC)
        ctx.move_to(-62, 0)
        ctx.line_to(-54, -232)
        ctx.line_to(54, -232)
        ctx.line_to(62, 0)
        ctx.close_path()
        rellena(ctx, (0.05, 0.04, 0.06), w=5)


def sol(ctx, x, y, r, t):
    _elipse_suave(ctx, x, y, r * 3.2, r * 3.2, AMARILLO, 0.35)
    for k in range(12):
        ang = k * TAU / 12
        r1 = r * (1.55 + 0.14 * math.sin(t * 5 + k * 1.7))
        ctx.move_to(x + r * 1.25 * math.cos(ang), y + r * 1.25 * math.sin(ang))
        ctx.line_to(x + r1 * math.cos(ang), y + r1 * math.sin(ang))
    trazo(ctx, INK, 22)
    for k in range(12):
        ang = k * TAU / 12
        r1 = r * (1.55 + 0.14 * math.sin(t * 5 + k * 1.7))
        ctx.move_to(x + r * 1.25 * math.cos(ang), y + r * 1.25 * math.sin(ang))
        ctx.line_to(x + r1 * math.cos(ang), y + r1 * math.sin(ang))
    trazo(ctx, AMARILLO, 11)
    elipse(ctx, x, y, r, r)
    rellena(ctx, AMARILLO, w=8)


def colgante(ctx, x, y, txt, ang=0.0, s=1.0, col=CREMA, tam=30, fg=INK):
    """Etiqueta atada con un hilo; (x, y) es el punto del que cuelga."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s, ang):
        ctx.move_to(0, 0)
        ctx.line_to(0, 50)
        trazo(ctx, VENDA_OSC, 4)
        P.fuente(ctx, P.LILITA, tam)
        w = ctx.text_extents(txt)[4] + 50
        ctx.move_to(0, 44)
        ctx.line_to(w / 2, 66)
        ctx.line_to(w / 2, 132)
        ctx.line_to(-w / 2, 132)
        ctx.line_to(-w / 2, 66)
        ctx.close_path()
        rellena(ctx, col, w=5)
        elipse(ctx, 0, 62, 6, 6)
        ctx.set_source_rgb(*INK)
        ctx.fill()
        texto(ctx, txt, 0, 101, tam, fill=fg, stroke=None)


def edificio(ctx, x, y, s=1.0, luz=0.0):
    with en(ctx, x, y, s):
        ctx.rectangle(210, -500, 64, 190)
        rellena(ctx, LADRILLO_OSC)
        ctx.rectangle(-330, -320, 660, 320)
        rellena(ctx, LADRILLO)
        ctx.move_to(-330, -320)
        for k in range(4):
            x0 = -330 + k * 165
            ctx.line_to(x0, -392)
            ctx.line_to(x0 + 165, -320)
        ctx.close_path()
        rellena(ctx, LADRILLO_OSC)
        n = 0
        for fila in range(2):
            for c in range(5):
                ctx.rectangle(-290 + c * 124, -272 + fila * 132, 84, 92)
                rellena(ctx, AMARILLO if luz * 10 > n else SOMBRA, w=5)
                n += 1


def rasqueta(ctx, x, y, s=1.0, ang=0.2):
    with en(ctx, x, y, s, ang):
        rrect(ctx, -26, -340, 52, 200, 18)
        rellena(ctx, MADERA)
        ctx.move_to(-30, -150)
        ctx.line_to(30, -150)
        ctx.line_to(46, 160)
        ctx.line_to(-46, 160)
        ctx.close_path()
        rellena(ctx, ACERO)
        ctx.move_to(-40, 158)
        ctx.line_to(40, 158)
        trazo(ctx, BLANCO, 5)


def brocha(ctx, x, y, s=1.0, ang=-0.25):
    with en(ctx, x, y, s, ang):
        rrect(ctx, -22, -330, 44, 190, 16)
        rellena(ctx, MADERA)
        ctx.rectangle(-40, -150, 80, 50)
        rellena(ctx, ACERO)
        ctx.move_to(-40, -100)
        ctx.line_to(40, -100)
        ctx.line_to(48, 10)
        ctx.curve_to(20, 26, -20, 26, -48, 10)
        ctx.close_path()
        rellena(ctx, BREA)


# ------------------------------------------------------------------ 1. la botica (apertura y cierre del loop)
EST_Y = 1240
T_COMIERON = b(0, "comieron")
T_MOMIAS = b(0, "momias")
T_CURAR = b(0, "curarse")
T_BRUJ = b(1, "brujeria")
T_RECET = b(1, "recetaban")
T_MEDICOS = b(1, "medicos")


def botica(ctx, t, brillo=0.0):
    """El estante con el frasco de mumia y el sarcófago al fondo. Con brillo = 0 es el cuadro del loop."""
    fondo(ctx, t, 0.45)
    luz_cenital(ctx, 520)
    sarcofago(ctx, 890, EST_Y, 1.16, a=0.6 + 0.4 * brillo, brillo=brillo)
    tabla(ctx, EST_Y)
    frasco(ctx, 110, EST_Y, 0.78, 0.45, etiqueta="")
    frasco(ctx, 262, EST_Y, 0.62, 0.8, etiqueta="")
    frasco(ctx, 520, EST_Y, 1.55, 0.8, "MUMIA")


def receta(ctx, t):
    q = prog(t, T_RECET - 0.1, 0.35, "out")
    if q <= 0:
        return
    with en(ctx, 250, lerp(2200, 1010, q), 1.0, math.radians(-7)):
        papel(ctx, 380, 470)
        texto(ctx, "Rp.", -150, -180, 56, fill=INK, stroke=None, ax=0)
        renglones(ctx, -150, -118, 300, 2, 34, seed=3)
        e = prog(t, T_RECET + 0.3, 0.3, "out")
        if e > 0:
            texto(ctx, "MUMIA", 0, -8, 70, fill=ROJO_OSC, stroke=None, alpha=e)
        renglones(ctx, -150, 56, 300, 2, 34, seed=4)
        f = prog(t, T_MEDICOS, 0.5, "linear")
        if f > 0:
            ctx.move_to(-20, 165)
            for k in range(1, int(40 * f) + 1):
                u = k / 40
                ctx.line_to(-20 + 170 * u, 165 - 28 * math.sin(u * 9) * (1 - u * 0.5))
            trazo(ctx, INK, 5)


def d_botica(ctx, t):
    z = 1 + 0.09 * prog(t, 0.0, 1.3, "out") + 0.04 * prog(t, 1.3, b(2) - 1.3, "linear")
    ctx.save()
    zoom(ctx, z, 540, 1000)
    brillo = prog(t, T_MOMIAS - 0.1, 0.35, "out") * sale(t, T_BRUJ, 0.4)
    botica(ctx, t, brillo)
    # la cuchara con el polvo: "comieron"
    e = prog(t, T_COMIERON - 0.45, 0.5, "out") * sale(t, T_BRUJ - 0.15, 0.3)
    if e > 0.01:
        cuchara(ctx, lerp(-200, 420, e), 610 + 10 * math.sin(t * 4), 1.0, math.radians(-6 + 4 * math.sin(t * 3)))
    receta(ctx, t)
    ctx.restore()
    kartel(ctx, "MOMIA", 890, 470, 62, t, T_MOMIAS, T_BRUJ - 0.1, box=ORO, rot=3)
    kartel(ctx, "REMEDIO", 380, 440, 70, t, T_CURAR, T_BRUJ - 0.1)
    kartel(ctx, "¿BRUJERÍA?", 540, 360, 84, t, T_BRUJ - 0.03, T_RECET - 0.12, box=VIOLETA, fg=BLANCO, rot=-3)
    if t < T_RECET - 0.05:
        tachado(ctx, 540, 360, 520, prog(t, T_BRUJ + 0.5, 0.25, "out"))
    kartel(ctx, "RECETA MÉDICA", 560, 360, 76, t, T_RECET, box=BLANCO, rot=2)


T_ULTIMO = b(17, "ultimo")
T_HIST = b(17, "historia")


def d_cierre(ctx, t):
    z = 1 + 0.12 * (1 - prog(t, b(17), TOTAL - 0.12 - b(17), "inout"))
    ctx.save()
    zoom(ctx, z, 540, 1000)
    botica(ctx, t, brillo=0.0)
    # la etiqueta de 1924 cuelga del frasco y se cae
    q = clamp((t - T_HIST) / 0.9)
    if q < 1:
        ang = 0.35 * math.exp(-(t - b(17)) * 1.4) * math.cos((t - b(17)) * 7) + 1.2 * q * q
        colgante(ctx, 610 + 60 * q, EST_Y - 420 + 1500 * q * q, "1924", ang, 1.5 * pop(t, b(17) + 0.05, 0.3),
                 col=AMARILLO, tam=40)
    ctx.restore()
    kartel(ctx, "EL ÚLTIMO RASTRO", 540, 380, 72, t, T_ULTIMO, T_HIST + 0.1, box=BLANCO, rot=-2)


# ------------------------------------------------------------------ 2. la pregunta
T_MUERTO = b(2, "muerto")
T_EGIPCIO = b(2, "egipcio")
T_FARM = b(2, "farmacia")
CAM_A, CAM_C, CAM_B = (250, 500), (540, 160), (830, 700)


def camino(u):
    return tuple((1 - u) ** 2 * a + 2 * u * (1 - u) * c + u * u * d for a, c, d in zip(CAM_A, CAM_C, CAM_B))


def d_pregunta(ctx, t):
    fondo(ctx, t, 0.4)
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(2), b(3) - b(2), "linear"), 540, 900)
    elipse(ctx, 250, 1122, 200, 34)
    rellena(ctx, ARENA_OSC, w=6)
    sarcofago(ctx, 250, 1120, 0.95 * pop(t, b(2) - 0.05, 0.35))
    tabla(ctx, 1120, 650, 1010)
    frasco(ctx, 830, 1120, 1.25 * pop(t, T_FARM - 0.3, 0.35), 0.8)
    p = prog(t, T_MUERTO, T_FARM - T_MUERTO, "inout")
    if p > 0:
        for k in range(1, 25):
            u = k / 25
            if u > p:
                break
            x, y = camino(u)
            elipse(ctx, x, y, 11, 11)
            rellena(ctx, BLANCO, w=5)
        x, y = camino(p)
        elipse(ctx, x, y, 24, 24)
        rellena(ctx, AMARILLO, w=7)
    ctx.restore()
    s = pop(t, b(2) + 0.05, 0.35) * bump(t, T_FARM, 0.35, 0.25)
    if s > 0.01:
        with en(ctx, 540, 820, s):
            texto(ctx, "?", 0, 0, 380, fill=AMARILLO, sw=16)
    kartel(ctx, "EGIPTO", 250, 1230, 60, t, T_EGIPCIO - 0.05, box=ARENA)
    kartel(ctx, "FARMACIA", 830, 1230, 60, t, T_FARM, box=BLANCO)


# ------------------------------------------------------------------ 3. momia molida, en frascos
T_MOLIDA = b(3, "molida")
T_MOMIA3 = b(3, "momia")
T_FRASCOS = b(3, "frascos")
PASO = 0.36
GOLPES3 = [b(3) + 0.18 + k * PASO for k in range(int((T_FRASCOS - b(3)) / PASO))]
FR3 = [(160, T_FRASCOS - 0.55), (413, T_FRASCOS - 0.38), (667, T_FRASCOS - 0.21), (920, T_FRASCOS - 0.04)]


def d_frascos(ctx, t):
    fondo(ctx, t, 0.45)
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(3), b(4) - b(3), "linear"), 540, 900)
    tabla(ctx, 900, 170, 910)
    moliendo = t < T_FRASCOS - 0.1
    sube = abs(math.cos(math.pi * (t - b(3)) / PASO)) if moliendo else 1.0
    niv = prog(t, b(3), T_FRASCOS - b(3), "linear")
    mortero_fondo(ctx, 540, 900, 1.45, niv)
    mortero_mano(ctx, 540, 900, 1.45, sube)
    mortero_frente(ctx, 540, 900, 1.45)
    tabla(ctx, 1290)
    for x, t0 in FR3:
        frasco(ctx, x, 1290, 0.78 * pop(t, t0, 0.3), prog(t, t0 + 0.1, 0.3, "out") * 0.85)
    ctx.restore()
    kartel(ctx, "MOMIA MOLIDA", 540, 380, 84, t, T_MOMIA3)


# ------------------------------------------------------------------ 4. el rey
T_REY = b(4, "rey")
T_LLEV = b(4, "llevaba")
T_SIEMPRE = b(4, "siempre")


def d_rey(ctx, t):
    fondo(ctx, t, 0.5)
    _elipse_suave(ctx, 540, 820, 700, 620, TERCIOPELO, 0.35)
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(4), b(5) - b(4), "linear"), 540, 900)
    cojin(ctx, 540, 880, 1.25)
    q = clamp((t - (b(4) - 0.05)) / 0.6)
    corona(ctx, 540, lerp(-300, 822, ease(q, "bounce")), 1.15)
    # el cinturón con la bolsita
    rrect(ctx, 110, 1030, 860, 50, 12)
    rellena(ctx, CUERO_CLARO)
    rrect(ctx, 250, 1018, 90, 74, 12)
    rellena(ctx, ORO)
    dt = t - T_LLEV
    ang = 0.5 * math.exp(-dt * 1.6) * math.cos(dt * 7) if dt > 0 else 0.5
    bolsa(ctx, 660, 1078, 1.1 * pop(t, T_LLEV - 0.12, 0.3), ang)
    ctx.restore()
    kartel(ctx, "REY DE FRANCIA", 540, 370, 80, t, T_REY)
    kartel(ctx, "SIGLO XVI", 540, 480, 50, t, T_REY + 0.3, box=BLANCO)
    kartel(ctx, "SIEMPRE ENCIMA", 310, 1250, 56, t, T_SIEMPRE, rot=-3)


# ------------------------------------------------------------------ 5. el error de traducción
T_ERROR = b(5, "error")
T_TRAD = b(5, "traduccion")


def d_error(ctx, t):
    fondo(ctx, t, 0.45)
    dx, dy = sacudida(t, T_ERROR, 0.35, 16)
    ctx.save()
    ctx.translate(dx, dy)
    zoom(ctx, 1 + 0.04 * prog(t, b(5), b(6) - b(5), "linear"), 540, 900)
    libro(ctx, 540, 900)
    # página izquierda: mumia = brea
    texto(ctx, "MUMIA", 320, 700, 78, fill=INK, stroke=None)
    gota(ctx, 230, 830, 0.9)
    texto(ctx, "= BREA", 370, 832, 52, fill=INK, stroke=None)
    renglones(ctx, 150, 940, 340, 5, 40, seed=7)
    # página derecha: se escribe mumia = momia
    e = prog(t, b(5) + 0.1, 0.3, "out")
    if e > 0:
        texto(ctx, "MUMIA", 760, 700, 78, fill=INK, stroke=None, alpha=e)
    e2 = prog(t, b(5) + 0.45, 0.3, "out")
    if e2 > 0:
        momia(ctx, 700, 832, 0.26, osc=0.9, a=e2)
        texto(ctx, "= MOMIA", 880, 912, 46, fill=INK, stroke=None, alpha=e2, ax=1.0)
    pr = prog(t, b(5) + 0.2, T_ERROR - b(5) - 0.3, "linear")
    renglones(ctx, 590, 980, 340, 4, 40, seed=9, p=pr)
    if 0 < pr < 1:
        k = min(3, int(pr * 4))
        pluma(ctx, 590 + 340 * 0.8 * (pr * 4 - k), 986 + k * 40)
    sello(ctx, "ERROR", 760, 1050, 120, t, T_ERROR)
    ctx.restore()
    kartel(ctx, "ERROR DE TRADUCCIÓN", 540, 370, 66, t, T_TRAD, box=BLANCO, rot=-2)


# ------------------------------------------------------------------ 6. la brea de Persia
T_ORIG = b(6, "original")
T_BREA = b(6, "brea")
T_PERSIA = b(6, "persia")
CHORROS = [(505, 800, 250, 0.0), (585, 760, 400, 0.2), (655, 860, 180, 0.45)]
GOTAS6 = [T_BREA + 0.25 + k * 0.42 for k in range(4)]


def d_brea(ctx, t):
    fondo(ctx, t, 0.3, 0.06)
    ctx.save()
    zoom(ctx, 1 + 0.05 * prog(t, b(6), b(7) - b(6), "linear"), 560, 900)
    ctx.move_to(40, 1310)
    for p in ((250, 820), (380, 930), (560, 520), (700, 800), (840, 700), (1050, 1310)):
        ctx.line_to(*p)
    ctx.close_path()
    rellena(ctx, ROCA, w=8)
    ctx.move_to(560, 520)
    ctx.line_to(700, 800)
    ctx.line_to(640, 1310)
    ctx.line_to(470, 1310)
    ctx.close_path()
    ctx.set_source_rgb(*ROCA_CLARA)
    ctx.fill()
    ctx.rectangle(-20, 1300, 1120, 80)
    rellena(ctx, ROCA, w=6)
    # la grieta y los chorros de brea
    elipse(ctx, 580, 800, 118, 30)
    rellena(ctx, BREA, w=6)
    largo2 = 0.0
    for k, (x, y, L, d) in enumerate(CHORROS):
        ln = L * prog(t, b(6) + 0.15 + d, 1.3, "out")
        if ln > 2:
            ctx.move_to(x, y)
            ctx.line_to(x, y + ln)
            trazo(ctx, BREA, 30)
            elipse(ctx, x, y + ln, 21, 24)
            ctx.set_source_rgb(*BREA)
            ctx.fill()
            ctx.move_to(x - 7, y + 12)
            ctx.line_to(x - 7, y + ln * 0.8)
            trazo(ctx, BLANCO, 5, 0.25)
        if k == 1:
            largo2 = ln
    for t0 in GOTAS6:
        q = (t - t0) / 0.3
        if 0 <= q < 1:
            gota(ctx, 585, lerp(760 + largo2 + 30, 1190, q * q), 0.55)
    niv = clamp(sum(1 for t0 in GOTAS6 if t > t0 + 0.3) / len(GOTAS6))
    cuenco(ctx, 585, 1300, 1.0, niv)
    ctx.restore()
    kartel(ctx, "REMEDIO ORIGINAL", 540, 330, 64, t, T_ORIG - 0.05, box=BLANCO)
    kartel(ctx, "BREA NEGRA", 830, 1020, 62, t, T_BREA, rot=3)
    kartel(ctx, "PERSIA", 270, 650, 76, t, T_PERSIA, box=ARENA, rot=-4)


# ------------------------------------------------------------------ 7. se llamaba mumia, y las momias parecían cubiertas
T_MUMIA = b(7, "mumia")
T_MOMIAS7 = b(7, "momias")
T_PAREC = b(7, "parecian")
T_CUB = b(7, "cubiertas")


def muestra(ctx, x, y, r):
    elipse(ctx, x, y, r + 8, r + 8)
    rellena(ctx, BLANCO, w=7)
    elipse(ctx, x, y, r, r)
    ctx.set_source_rgb(*BREA)
    ctx.fill()
    elipse(ctx, x - r * 0.3, y - r * 0.3, r * 0.2, r * 0.12)
    ctx.set_source_rgba(1, 1, 1, 0.3)
    ctx.fill()


def d_parecidas(ctx, t):
    fondo(ctx, t, 0.42)
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(7), b(8) - b(7), "linear"), 540, 900)
    cuenco(ctx, 540, 720, 1.5, 1.0)
    e = prog(t, T_MOMIAS7 - 0.25, 0.5, "out")
    if e > 0:
        _elipse_suave(ctx, 570, 1160, 560, 200, LUZ, 0.22 * e)
        momia(ctx, lerp(1700, 570, e), 1160, 1.12, osc=0.95)
        # brillo que recorre la costra
        q = (t - T_CUB) / 0.6
        if 0 < q < 1:
            ctx.save()
            ctx.rectangle(lerp(150, 950, q) - 30, 1020, 60, 280)
            ctx.clip()
            momia(ctx, 570, 1160, 1.12, osc=0.55)
            ctx.restore()
    # dos muestras, una del cuenco y otra de la momia, se juntan: son iguales a la vista
    m = prog(t, T_PAREC, 0.45, "out")
    if m > 0:
        muestra(ctx, lerp(540, 420, m), lerp(600, 905, m), 58 * min(1.0, m * 2))
        muestra(ctx, lerp(570, 660, m), lerp(1160, 905, m), 58 * min(1.0, m * 2))
    ctx.restore()
    s = pop(t, T_PAREC + 0.4, 0.3)
    if s > 0.01:
        with en(ctx, 540, 905, s):
            texto(ctx, "=", 0, 0, 130, fill=AMARILLO, sw=12)
    kartel(ctx, "MUMIA", 540, 400, 110, t, T_MUMIA - 0.05)


# ------------------------------------------------------------------ 8. primero rasparon la costra
T_RASP = b(8, "rasparon")
T_COSTRA = b(8, "costra")
RA0, RA1 = T_RASP - 0.1, b(9) - 0.25
_r = rng(31)
ESCAMAS = [(RA0 + (RA1 - RA0) * k / 46, float(_r.uniform(640, 1150)), float(_r.uniform(-90, 90)),
            float(_r.uniform(12, 26)), float(_r.uniform(0, TAU))) for k in range(46)]


def x_rasqueta(t):
    return lerp(110, 1010, prog(t, RA0, RA1 - RA0, "inout"))


def d_raspar(ctx, t):
    fondo(ctx, t, 0.45)
    ctx.save()
    zoom(ctx, 1 + 0.03 * prog(t, b(8), b(9) - b(8), "linear"), 540, 900)
    xs = x_rasqueta(t)
    momia(ctx, 700, 900, 3.0, osc=0.0)
    ctx.save()
    ctx.rectangle(xs, 0, 1400, H)
    ctx.clip()
    momia(ctx, 700, 900, 3.0, osc=1.0)
    ctx.restore()
    for t0, y0, vx, r, ang in ESCAMAS:
        dt = t - t0
        if dt <= 0:
            continue
        y = y0 + 950 * dt * dt
        if y > 1380:
            continue
        with en(ctx, x_rasqueta(t0) + vx * dt, y, 1.0, ang + dt * 5):
            ctx.rectangle(-r, -r * 0.6, 2 * r, 1.2 * r)
            ctx.set_source_rgba(*COSTRA, clamp((1380 - y) / 120))
            ctx.fill()
    if RA0 - 0.3 < t:
        e = prog(t, RA0 - 0.3, 0.3, "out")
        rasqueta(ctx, xs + 8 * math.sin(t * 26), lerp(300, 900, e) + 60 * math.sin(t * 13), 1.15, 0.22)
    ctx.restore()
    kartel(ctx, "PRIMERO: LA COSTRA", 540, 370, 70, t, T_COSTRA - 0.3)


# ------------------------------------------------------------------ 9. después molieron el cuerpo entero
T_DIRECT = b(9, "directamente")
T_MOL = b(9, "molieron")
T_CUERPO9 = b(9, "cuerpo")
T_ENTERO = b(9, "entero")
_r = rng(52)
MIGAS = [(T_MOL + float(_r.uniform(0.05, 1.05)), float(_r.uniform(-150, 150)), float(_r.uniform(260, 520)),
          float(_r.uniform(10, 20))) for _ in range(40)]


def d_moler(ctx, t):
    fondo(ctx, t, 0.5)
    dx, dy = sacudida(t, T_MOL, 1.0, 9)
    ctx.save()
    ctx.translate(dx, dy)
    zoom(ctx, 1 + 0.04 * prog(t, b(9), b(10) - b(9), "linear"), 540, 1000)
    hunde = prog(t, T_MOL, 1.05, "inout")
    mortero_fondo(ctx, 540, 1300, 1.9, hunde)
    entra = prog(t, b(9) - 0.05, 0.5, "out")
    yc = lerp(-500, 590, entra) + 9 * math.sin(t * 5) * (1 - hunde) + 830 * hunde
    ctx.save()
    ctx.rectangle(0, -600, W, 1030 + 600)
    ctx.clip()
    momia(ctx, 540, yc, 1.1, osc=0.75, rot=math.pi / 2)
    ctx.restore()
    for t0, vx, vy, r in MIGAS:
        dt = t - t0
        if 0 < dt < 0.7:
            y = 980 - vy * dt + 900 * dt * dt
            if y < 1000:
                ctx.rectangle(540 + vx * dt * 1.6 - r / 2, y - r / 2, r, r)
                ctx.set_source_rgba(*POLVO_CLARO, 1 - dt / 0.7)
                ctx.fill()
    mortero_frente(ctx, 540, 1300, 1.9)
    ctx.restore()
    kartel(ctx, "DESPUÉS...", 250, 420, 64, t, T_DIRECT - 0.5, T_MOL - 0.1, box=BLANCO, rot=-4)
    kartel(ctx, "EL CUERPO ENTERO", 540, 420, 76, t, T_CUERPO9)


# ------------------------------------------------------------------ 10. las tumbas se saquearon para llenar frascos
T_EGIPTO = b(10, "egipto")
T_SAQ = b(10, "saquearon")
T_FRASCOS10 = b(10, "frascos")
TX = [150, 410, 670, 930]
T_SALE = [T_SAQ - 0.45 + k * 0.3 for k in range(4)]


def d_tumbas(ctx, t):
    fondo(ctx, t, 0.2, 0.10)
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(10), b(11) - b(10), "linear"), 540, 900)
    piramide(ctx, 300, 1125, 600, 440, 0.9)
    piramide(ctx, 800, 1125, 420, 300, 0.9)
    arena(ctx, 1110)
    tabla(ctx, 600, 40, 1040)
    for k, x in enumerate(TX):
        tumba(ctx, x, 1130)
        q = (t - T_SALE[k]) / 0.42
        if q <= 0:
            sarcofago(ctx, x, 1124, 0.34)
        elif q < 1:
            e = ease(q, "inout")
            sarcofago(ctx, x + 70 * math.sin(math.pi * e), lerp(1124, 600, e), 0.34 * (1 - 0.6 * e), a=1 - 0.5 * e)
        frasco(ctx, x, 600, 0.7 * pop(t, T_SALE[k] + 0.36, 0.3), 0.85)
    ctx.restore()
    kartel(ctx, "TUMBAS DE EGIPTO", 540, 728, 54, t, T_EGIPTO - 0.1, T_SALE[3] + 0.3, box=ARENA)
    sello(ctx, "SAQUEADAS", 540, 728, 78, t, T_SALE[3] + 0.45, rot=-4)


# ------------------------------------------------------------------ 11. no alcanzaban para tanta demanda
T_ALC = b(11, "alcanzaban")
T_DEM = b(11, "demanda")
FX11 = [130, 335, 540, 745, 950]
T_VACIA = [b(11) + 0.2 + k * 0.26 for k in range(5)]
_r = rng(77)
PEDIDOS = [(T_ALC + 0.25 + k * 0.13, float(_r.uniform(-150, 150)), float(_r.uniform(-9, 9))) for k in range(12)]


def d_demanda(ctx, t):
    fondo(ctx, t, 0.45)
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(11), b(12) - b(11), "linear"), 540, 900)
    tabla(ctx, 760)
    for x, t0 in zip(FX11, T_VACIA):
        frasco(ctx, x, 760, 0.72, 0.85 * (1 - prog(t, t0, 0.22, "out")))
    for k, (t0, dx, rot) in enumerate(PEDIDOS):
        s = pop(t, t0, 0.22)
        if s > 0.01:
            with en(ctx, 540 + dx, 1250 - k * 17, s, math.radians(rot)):
                papel(ctx, 300, 104)
                texto(ctx, "PEDIDO", 0, 2, 50, fill=INK, stroke=None)
    ctx.restore()
    kartel(ctx, "NO ALCANZAN", 540, 330, 88, t, T_ALC, box=ROJO, fg=BLANCO, rot=-2)
    kartel(ctx, "DEMANDA", 540, 930, 66, t, T_DEM - 0.05)


# ------------------------------------------------------------------ 12. aparecieron las falsas
T_FALSAS = b(12, "falsas")
T_HECHAS = b(12, "hechas")
T_MUERTOS = b(12, "muertos")
BR0, BR1 = T_MUERTOS + 0.1, b(12, fin=True) + 0.05


def d_falsas(ctx, t):
    fondo(ctx, t, 0.45)
    dx, dy = sacudida(t, T_FALSAS, 0.35, 16)
    ctx.save()
    ctx.translate(dx, dy)
    zoom(ctx, 1 + 0.04 * prog(t, b(12), b(13) - b(12), "linear"), 540, 900)
    tabla(ctx, 850, 200, 880)
    e = prog(t, b(12) - 0.05, 0.45, "out")
    frasco(ctx, lerp(1400, 540, e), 850, 1.45, 0.85)
    sello(ctx, "FALSA", 540, 640, 130, t, T_FALSAS)
    # el cuerpo reciente, con vendas claras, que se pinta de brea
    e2 = prog(t, T_HECHAS - 0.1, 0.4, "out")
    if e2 > 0:
        xm = lerp(-700, 560, e2)
        _elipse_suave(ctx, 560, 1200, 520, 190, LUZ, 0.22 * e2)
        momia(ctx, xm, 1200, 1.0, osc=0.0)
        xb = lerp(180, 960, prog(t, BR0, BR1 - BR0, "inout"))
        if t > BR0:
            ctx.save()
            ctx.rectangle(0, 1000, xb, 400)
            ctx.clip()
            momia(ctx, xm, 1200, 1.0, osc=0.95)
            ctx.restore()
        if t > BR0 - 0.3:
            brocha(ctx, lerp(-200, xb, prog(t, BR0 - 0.3, 0.3, "out")), 1150 + 40 * math.sin(t * 14), 1.0)
    ctx.restore()
    kartel(ctx, "MUERTOS RECIENTES", 540, 1010, 58, t, T_MUERTOS - 0.05, box=BLANCO)


# ------------------------------------------------------------------ 13. ejecutados, secados al sol, vendidos como antiguos
T_EJEC = b(13, "ejecutados")
T_SECADOS = b(13, "secados")
T_SOL = b(13, "sol")
T_VEND = b(13, "vendidos")
T_ANTIG = b(13, "antiguos")
BULTOS = [(330, 1075), (720, 1160), (400, 1265)]


def d_sol(ctx, t):
    seca = prog(t, T_SECADOS, T_VEND - T_SECADOS, "linear")
    fondo(ctx, t, 0.15, 0.10 + 0.10 * seca)
    ctx.save()
    zoom(ctx, 1 + 0.05 * prog(t, b(13), b(14) - b(13), "linear"), 540, 900)
    sol(ctx, 830, 400, 120 * (0.6 + 0.4 * pop(t, T_SECADOS - 0.25, 0.4)), t)
    arena(ctx, 990)
    for k, (x, y) in enumerate(BULTOS):
        momia(ctx, x, y, 0.62 * pop(t, b(13) + 0.05 + k * 0.14, 0.3), osc=0.2 + 0.75 * seca)
    # el calor sube en rayitas cortas
    if 0 < seca < 1:
        for k in range(7):
            x = 170 + k * 120
            y = 1000 - ((t * 150 + k * 67) % 230)
            ctx.move_to(x, y)
            ctx.curve_to(x + 16, y - 20, x - 16, y - 40, x, y - 60)
            trazo(ctx, BLANCO, 7, 0.55 * clamp((1000 - y) / 60) * clamp((y - 770) / 60))
    for k, (x, y) in enumerate(BULTOS):
        t0 = T_VEND + 0.05 + k * 0.16
        dt = t - t0
        ang = 0.3 * math.exp(-dt * 2) * math.cos(dt * 8) if dt > 0 else 0.0
        colgante(ctx, x + 150, y - 170, "ANTIGUA", ang, 1.1 * pop(t, t0, 0.3), col=AMARILLO, tam=34)
    ctx.restore()
    kartel(ctx, "EJECUTADOS", 330, 470, 70, t, T_EJEC, T_SECADOS - 0.1, box=BLANCO, rot=-2)
    kartel(ctx, "SECADOS AL SOL", 330, 470, 64, t, T_SECADOS, T_VEND - 0.1, rot=-2)
    kartel(ctx, "«DE 3.000 AÑOS»", 330, 470, 64, t, T_ANTIG - 0.15, rot=-2)


# ------------------------------------------------------------------ 14. nadie notaba la diferencia; nunca curó nada
T_NOTABA = b(14, "notaba")
T_DIF = b(14, "diferencia")
T_NUNCA = b(14, "nunca")
T_CURO = b(14, "curo")
SW = [(T_NOTABA + 0.25, 0.3), (T_NOTABA + 0.6, 0.3), (T_NOTABA + 0.95, 0.3)]


def d_diferencia(ctx, t):
    fondo(ctx, t, 0.45)
    dx, dy = sacudida(t, T_CURO, 0.35, 16)
    ctx.save()
    ctx.translate(dx, dy)
    zoom(ctx, 1 + 0.04 * prog(t, b(14), b(15) - b(14), "linear"), 540, 900)
    tabla(ctx, 1180)
    # los dos frascos se cruzan tres veces: ya no se sabe cuál es cuál
    u, lift = 0.0, 0.0
    for t0, d in SW:
        q = clamp((t - t0) / d)
        u += ease(q, "inout")
        if 0 < q < 1:
            lift = math.sin(math.pi * q)
    xa = lerp(310, 770, u % 2 if u % 2 <= 1 else 2 - u % 2)
    xb = 1080 - xa
    frasco(ctx, xb, 1180, 1.25, 0.85)
    frasco(ctx, xa, 1180 - 46 * lift, 1.25, 0.85)
    ctx.restore()
    antes = t < SW[0][0]
    if antes:
        kartel(ctx, "VERDADERA", 310, 700, 56, t, b(14) - 0.05, box=VERDE)
        kartel(ctx, "FALSA", 770, 700, 56, t, b(14) + 0.05, box=ROJO, fg=BLANCO)
    else:
        for x in (310, 770):
            s = pop(t, SW[2][0] + 0.3, 0.3) * sale(t, T_CURO, 0.15)
            if s > 0.01:
                with en(ctx, x, 690, s):
                    texto(ctx, "?", 0, 0, 170, fill=AMARILLO, sw=12)
    kartel(ctx, "¿CUÁL ES CUÁL?", 540, 380, 76, t, T_DIF, T_CURO - 0.1, box=BLANCO, rot=-2)
    sello(ctx, "NO CURABA NADA", 540, 620, 92, t, T_CURO, rot=-5)


# ------------------------------------------------------------------ 15. en 1924 un laboratorio alemán todavía la vendía
T_1924 = b(15, "1924")
T_LAB = b(15, "laboratorio")
T_ALEMAN = b(15, "aleman")
T_TODAVIA = b(15, "todavia")
T_VENDIA = b(15, "vendia")
AN0, AN1 = b(15) - 0.05, T_1924 + 0.75


def anio(t):
    return int(round(lerp(1600, 1924, prog(t, AN0, AN1 - AN0, "out"))))


def d_1924(ctx, t):
    fondo(ctx, t, 0.5)
    ctx.save()
    zoom(ctx, 1 + 0.04 * prog(t, b(15), b(16) - b(15), "linear"), 540, 900)
    e = prog(t, T_LAB - 0.15, 0.5, "out")
    if e > 0:
        luz = prog(t, T_LAB + 0.1, 0.9, "linear")
        edificio(ctx, 540, lerp(2100, 1340, e), 1.0, luz)
        ctx.rectangle(-20, 1336, 1120, 70)
        rellena(ctx, LADRILLO_OSC, w=6)
    s = pop(t, T_TODAVIA - 0.05, 0.35)
    if s > 0.01:
        frasco(ctx, 400, 1345, 1.05 * s, 0.85)
    ctx.restore()
    kartel(ctx, "EN VENTA", 700, 1215, 66, t, T_VENDIA - 0.05, rot=4)
    sy = pop(t, AN0, 0.25) * bump(t, AN1, 0.35, 0.16)
    if sy > 0.01:
        with en(ctx, 540, 500, sy):
            texto(ctx, str(anio(t)), 0, 0, 270, fill=AMARILLO, sw=16)
    kartel(ctx, "LABORATORIO ALEMÁN", 540, 760, 60, t, T_ALEMAN - 0.1, box=BLANCO, rot=-2)


# ------------------------------------------------------------------ 16. la lista de precios
T_POLVO = b(16, "polvo")
T_EGIPCIA = b(16, "egipcia")
T_12 = b(16, "12")
T_KILO = b(16, "kilo")
FILA_Y = 60


def d_lista(ctx, t):
    fondo(ctx, t, 0.5)
    z = 1 + 0.28 * prog(t, T_POLVO + 0.1, 1.3, "inout")
    ctx.save()
    zoom(ctx, z, 540, 900)
    e = prog(t, b(16) - 0.05, 0.4, "out")
    with en(ctx, 540, lerp(2300, 840, e), 1.0, math.radians(-2)):
        papel(ctx, 860, 1060)
        texto(ctx, "LISTA DE PRECIOS", 0, -440, 66, fill=INK, stroke=None)
        texto(ctx, "1924", 0, -368, 50, fill=ROJO_OSC, stroke=None)
        ctx.move_to(-370, -322)
        ctx.line_to(370, -322)
        trazo(ctx, INK, 5)
        anchos = rng(5).uniform(180, 380, 10)
        for k in range(10):
            y = -270 + k * 82.5
            if abs(y - FILA_Y) < 5:
                continue
            ctx.rectangle(-370, y - 8, anchos[k], 16)
            ctx.rectangle(290, y - 8, 80, 16)
            ctx.set_source_rgba(0.45, 0.4, 0.33, 0.5)
            ctx.fill()
            for xx in range(int(-370 + anchos[k] + 24), 276, 22):
                ctx.rectangle(xx, y - 2, 6, 5)
            ctx.set_source_rgba(0.45, 0.4, 0.33, 0.4)
            ctx.fill()
        # la fila real, subrayada con resaltador
        m = prog(t, T_POLVO, 0.6, "out")
        if m > 0:
            ctx.rectangle(-386, FILA_Y - 36, 772 * m, 72)
            ctx.set_source_rgba(*AMARILLO, 0.85)
            ctx.fill()
        texto(ctx, "MUMIA VERA AEGYPTIACA", -370, FILA_Y, 40, fill=INK, stroke=None, ax=0)
        for xx in range(110, 276, 22):
            ctx.rectangle(xx, FILA_Y - 2, 6, 5)
        ctx.set_source_rgb(*INK)
        ctx.fill()
        texto(ctx, "12 M", 370, FILA_Y, 44, fill=INK, stroke=None, ax=1)
        # círculo rojo, dibujado a mano, alrededor del precio
        c = prog(t, T_12 - 0.1, 0.35, "inout")
        if c > 0:
            ctx.save()
            ctx.translate(325, FILA_Y)
            ctx.scale(72, 46)
            ctx.new_sub_path()
            ctx.arc(0, 0, 1, -2.2, -2.2 + TAU * 1.06 * c)
            ctx.restore()
            trazo(ctx, ROJO, 9)
    ctx.restore()
    kartel(ctx, "«MOMIA EGIPCIA VERDADERA»", 540, 1020, 50, t, T_EGIPCIA - 0.3, T_12 - 0.05, box=BLANCO, rot=-2)
    kartel(ctx, "12 MARCOS EL KILO", 540, 1250, 80, t, T_12 + 0.1, rot=-2)


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_botica),
    (b(2) - 0.08, d_pregunta),
    (b(3) - 0.08, d_frascos),
    (b(4) - 0.08, d_rey),
    (b(5) - 0.08, d_error),
    (b(6) - 0.08, d_brea),
    (b(7) - 0.08, d_parecidas),
    (b(8) - 0.08, d_raspar),
    (b(9) - 0.08, d_moler),
    (b(10) - 0.08, d_tumbas),
    (b(11) - 0.08, d_demanda),
    (b(12) - 0.08, d_falsas),
    (b(13) - 0.08, d_sol),
    (b(14) - 0.08, d_diferencia),
    (b(15) - 0.08, d_1924),
    (b(16) - 0.08, d_lista),
    (b(17) - 0.08, d_cierre),
]
XF = 0.18


def punch(t, t0, d=0.3, amp=0.05):
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


def escena(t):
    return max(k for k, (t0, _) in enumerate(ESCENAS) if t >= t0)


def componer(ctx, t):
    i = escena(t)
    t0, fn = ESCENAS[i]
    dt = t - t0
    ultima = i == len(ESCENAS) - 1          # el cierre no lleva golpe de zoom: tiene que terminar igual al inicio
    if i > 0 and dt < XF:
        capa(ctx, ESCENAS[i - 1][1], t)
        ctx.save()
        ctx.push_group()
        if not ultima:
            zoom(ctx, punch(t, t0))
        fn(ctx, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(clamp(dt / XF))
        ctx.restore()
        return
    if i > 0 and not ultima:
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


# ------------------------------------------------------------------ sonido (solo golpes cortos, sin sonidos sostenidos)
def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    # 1. botica
    ev(T_MOMIAS, "pop", 0.4)
    ev(T_CURAR, "pop", 0.35)
    ev(T_BRUJ, "pop", 0.4)
    ev(T_BRUJ + 0.5, "tick", 0.4, f=500, d=0.09)
    ev(T_RECET, "pop", 0.4)
    ev(T_RECET + 0.3, "clic", 0.35)
    # 2. pregunta
    ev(b(2) + 0.05, "pop", 0.5)
    ev(T_EGIPCIO, "pop", 0.3)
    ev(T_FARM, "ding", 0.35)
    # 3. mortero y frascos
    for t0 in GOLPES3:
        ev(t0, "clunk", 0.4)
    ev(T_MOMIA3, "pop", 0.35)
    for _, t0 in FR3:
        ev(t0, "pop", 0.4)
    # 4. rey
    ev(b(4) + 0.17, "clunk", 0.6)
    ev(b(4) + 0.38, "clunk", 0.3)
    ev(T_REY, "ding", 0.3)
    ev(T_LLEV - 0.1, "pop", 0.4)
    ev(T_SIEMPRE, "pop", 0.35)
    # 5. error
    for k in range(4):
        ev(b(5) + 0.25 + k * 0.2, "tick", 0.2, f=2600, d=0.03)
    ev(T_ERROR, "golpe", 0.9)
    ev(T_TRAD, "pop", 0.35)
    # 6. brea
    ev(T_ORIG, "pop", 0.35)
    ev(T_BREA, "pop", 0.4)
    for t0 in GOTAS6:
        ev(t0 + 0.3, "plop", 0.4)
    ev(T_PERSIA, "pop", 0.45)
    # 7. parecidas
    ev(T_MUMIA, "ding", 0.35)
    ev(T_MOMIAS7 + 0.2, "clunk", 0.35)
    ev(T_PAREC + 0.4, "pop", 0.45)
    # 8. raspar
    ev(T_COSTRA - 0.3, "pop", 0.3)
    k = 0
    while RA0 + k * 0.2 < RA1:
        ev(RA0 + k * 0.2, "tick", 0.3, f=420 + 60 * (k % 2), d=0.08)
        k += 1
    # 9. moler
    ev(b(9) + 0.4, "clunk", 0.35)
    for k in range(5):
        ev(T_MOL + k * 0.2, "clunk", 0.45)
    ev(T_CUERPO9, "golpe", 0.6)
    # 10. tumbas
    ev(T_EGIPTO, "pop", 0.3)
    for t0 in T_SALE:
        ev(t0, "tick", 0.35, f=900, d=0.06)
        ev(t0 + 0.36, "pop", 0.4)
    ev(T_SALE[3] + 0.45, "golpe", 0.7)
    # 11. demanda
    for t0 in T_VACIA:
        ev(t0, "clic", 0.4)
    ev(T_ALC, "golpe", 0.6)
    for t0, _, _ in PEDIDOS:
        ev(t0, "tick", 0.22, f=1900, d=0.03)
    ev(T_DEM, "pop", 0.4)
    # 12. falsas
    ev(b(12) + 0.3, "clunk", 0.35)
    ev(T_FALSAS, "golpe", 0.9)
    ev(T_MUERTOS, "pop", 0.35)
    # 13. sol
    ev(T_EJEC, "pop", 0.35)
    ev(T_SECADOS, "pop", 0.4)
    for k in range(3):
        ev(T_VEND + 0.05 + k * 0.16, "tick", 0.35, f=1500, d=0.05)
    ev(T_ANTIG - 0.15, "ding", 0.3)
    # 14. diferencia
    for t0, _ in SW:
        ev(t0 + 0.05, "tick", 0.3, f=700, d=0.07)
    ev(T_DIF, "pop", 0.35)
    ev(T_CURO, "golpe", 0.9)
    # 15. 1924
    for k in range(int((AN1 - AN0) / 0.09)):
        ev(AN0 + k * 0.09, "tick", 0.2, f=2000 + 30 * k, d=0.03)
    ev(AN1, "ding", 0.45)
    ev(T_LAB + 0.2, "clunk", 0.4)
    ev(T_TODAVIA, "pop", 0.35)
    ev(T_VENDIA, "pop", 0.4)
    # 16. lista
    ev(b(16) + 0.2, "clunk", 0.3)
    ev(T_POLVO + 0.3, "tick", 0.3, f=1200, d=0.08)
    ev(T_12 + 0.1, "ding", 0.5)
    # 17. cierre
    ev(T_ULTIMO, "pop", 0.3)
    ev(T_HIST + 0.1, "tick", 0.3, f=900, d=0.06)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "por_que_europa_comia_momias.mp4"))
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

"""Short "Vas a más de mil km/h y no lo sentís" — animación procedural (armazón de cerebro.py).

Estilo del canal: fondo azul con puntos, cosas con cara (el vasito de agua, la Tierra, el Sol, las bolitas de aire) y
subtítulos palabra por palabra. Vos sale solo en la apertura (dormido en la cama) y el cierre vuelve al primer cuadro:
el cuadro de TOTAL es igual al de 0. Sin flechas de giro ni sonidos sostenidos.

Hilos que se repiten: el velocímetro (0 -> 1.000 -> 107.000 -> 0) y el vasito de agua con cara, que hace de "lo que
siente tu cuerpo": el agua quieta es no sentir nada; el agua que se sacude es sentir un cambio de velocidad.

    python proyectos/tierra/tierra.py --hoja 0,3,6      # hoja de fotogramas -> proyectos/tierra/fotos/hoja.png
    python proyectos/tierra/tierra.py --probar
    python proyectos/tierra/tierra.py                   # render -> salidas/vas_a_mas_de_mil_km_por_hora.mp4
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
from contextlib import contextmanager
from multiprocessing import Pool

import cairo
import cairosvg
import numpy as np
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
for _p in (ROOT, os.path.join(ROOT, "proyectos", "pantalla"), os.path.join(ROOT, "proyectos", "picante")):
    sys.path.insert(0, _p)
import kit  # noqa: E402
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, bump, cartel, clamp, ease, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rrect, texto)
from picante import _elipse_suave, carita, fondo_azul  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Estás en tu cama, completamente quieto.",                                  # b0
    "O eso crees.",                                                             # b1
    "La Tierra gira y te lleva a más de 1.000 kilómetros por hora.",            # b2
    "Más rápido que un avión.",                                                 # b3
    "¿Por qué no sientes nada?",                                                # b4
    "Si fueras tan rápido, te golpearía el viento.",                            # b5
    "No pasa, porque el aire gira contigo.",                                    # b6
    "Tu casa, tu calle y las nubes también.",                                   # b7
    "El resto lo hace tu cuerpo.",                                              # b8
    "No siente la velocidad, solo siente cuando cambia.",                       # b9
    "Piensa en un avión en pleno vuelo.",                                       # b10
    "Vas rapidísimo, pero caminas por el pasillo como en tu casa.",             # b11
    "Lo único que sientes es el despegue, el aterrizaje y las sacudidas.",      # b12
    "La Tierra es un avión que nunca frena, nunca acelera y nunca se sacude.",  # b13
    "Tu cuerpo no tiene nada que sentir.",                                      # b14
    "Ese ni siquiera es tu viaje más rápido.",                                  # b15
    "Alrededor del Sol vas a 107.000 kilómetros por hora.",                     # b16
    "Aun así, jurarías que...",                                                 # b17
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
ROJO = hx("#E5383B")
VERDE = hx("#2BD45A")
VERDE_OSC = hx("#1F9E45")
CREMA = hx("#F6EEDC")
AGUA = hx("#4FB6F5")
AGUA_OSC = hx("#2A8FD6")
VIDRIO = hx("#DDF1FF")
AZUL_T = hx("#3D8BFF")
VERDE_T = hx("#44C767")
SOL_C = hx("#FFC933")
SOL2 = hx("#FF9A1F")
MADERA = hx("#B8662B")
MADERA_OSC = hx("#8A4519")
PANEL = hx("#1B2347")
GRIS = hx("#C9D1DE")
GRIS_OSC = hx("#8E97A8")
ASIENTO = hx("#5C6BC0")
AIRE = hx("#BDE6FF")
TECHO = hx("#E5383B")
PARED = hx("#FFE3B3")
ASFALTO = hx("#4A4F63")
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
    if a >= 0.999:
        yield
        return
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
    trazo(ctx, borde, w, a)


def elipse(ctx, x, y, rx, ry):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(max(rx, 1e-3), max(ry, 1e-3))
    ctx.new_sub_path()
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()


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


def sello(ctx, txt, x, y, size, t, t0, t1=None, rot=-8, col=ROJO):
    """Sello de goma que cae de golpe."""
    if t < t0:
        return
    q = clamp((t - t0) / 0.14)
    sc = lerp(2.4, 1.0, ease(q, "in"))
    a = min(1.0, q * 1.6) * (sale(t, t1) if t1 is not None else 1.0)
    if a <= 0.01:
        return
    with en(ctx, x, y, sc, math.radians(rot)), alfa(ctx, a):
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


def signo(ctx, txt, x, y, size, t, t0, t1=None, col=AMARILLO, sw=14):
    """Signo grande ("?", "!") que entra con rebote."""
    s = pop(t, t0, 0.35) * (sale(t, t1) if t1 is not None else 1.0)
    if t < t0 or s <= 0.01:
        return
    with en(ctx, x, y, s, math.radians(4 * math.sin((t - t0) * 6))):
        texto(ctx, txt, 0, 0, size, fill=col, sw=sw)


def destello(ctx, x, y, r, t, t0, d=0.5):
    if not (t0 <= t < t0 + d):
        return
    q = (t - t0) / d
    for k in range(8):
        a_ = k * TAU / 8
        r0, r1 = r * (0.4 + 0.6 * q), r * (0.75 + 0.6 * q)
        ctx.move_to(x + r0 * math.cos(a_), y + r0 * math.sin(a_))
        ctx.line_to(x + r1 * math.cos(a_), y + r1 * math.sin(a_))
    trazo(ctx, AMARILLO, 9, 1 - q)


def tilde(ctx, x, y, s, a=1.0):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.arc(0, 0, 46, 0, TAU)
        rellena(ctx, VERDE, 6, a=a)
        ctx.move_to(-22, 2)
        ctx.line_to(-6, 18)
        ctx.line_to(24, -16)
        trazo(ctx, BLANCO, 11, a)


def cruz_roja(ctx, x, y, s, a=1.0):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        for sx in (-1, 1):
            ctx.move_to(-110 * sx, -110)
            ctx.line_to(110 * sx, 110)
        trazo(ctx, INK, 48, a)
        for sx in (-1, 1):
            ctx.move_to(-110 * sx, -110)
            ctx.line_to(110 * sx, 110)
        trazo(ctx, ROJO, 32, a)


def tachado(ctx, txt, x, y, size, t, t0, t_tacha):
    """Palabra que entra y después se tacha con una raya roja."""
    s = pop(t, t0, 0.3)
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        texto(ctx, txt, 0, 0, size, fill=BLANCO, sw=10)
        p = prog(t, t_tacha, 0.18, "out")
        if p > 0.01:
            P.fuente(ctx, P.LILITA, size)
            tw = ctx.text_extents(txt)[4] + 40
            ctx.move_to(-tw / 2, 8)
            ctx.line_to(-tw / 2 + tw * p, -8)
            trazo(ctx, INK, 26)
            ctx.move_to(-tw / 2, 8)
            ctx.line_to(-tw / 2 + tw * p, -8)
            trazo(ctx, ROJO, 16)


def lineas_velocidad(ctx, x, y, largo, t, n=5, sep=34, a=1.0, ang=0.0, seed=0, col=BLANCO):
    """Rayitas de velocidad que corren hacia atrás (ang = hacia dónde va lo que se mueve)."""
    if a <= 0.01:
        return
    with en(ctx, x, y, 1.0, ang):
        for k in range(n):
            ph = (t * 2.2 + 0.37 * k + 0.13 * seed) % 1.0
            yy = (k - (n - 1) / 2) * sep
            x0 = -40 - ph * largo
            ctx.move_to(x0, yy)
            ctx.line_to(x0 - largo * 0.45, yy)
            trazo(ctx, col, 7, a * (1 - ph) * 0.85)


# ------------------------------------------------------------------ personajes y objetos
@functools.lru_cache(maxsize=None)
def cama_surface():
    png = cairosvg.svg2png(bytestring=kit.svg(680, 400, kit.cama(True)).encode(), output_width=1360,
                           output_height=800)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


def cama(ctx, x, y, k=1.0, rot=0.0, alpha=1.0):
    """Cama con Vos dormido; (x, y) = centro de abajo; k = 1 es el dibujo a 680x400."""
    if alpha <= 0.01 or k <= 0.01:
        return
    s = cama_surface()
    ctx.save()
    ctx.translate(x, y)
    if rot:
        ctx.rotate(rot)
    ctx.scale(k / 2, k / 2)
    ctx.translate(-680, -790)
    ctx.set_source_surface(s, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def zetas(ctx, x, y, t, s=1.0, a=1.0):
    """Zzz que suben (ciclo de 2,4 s)."""
    if a <= 0.01:
        return
    for k in range(3):
        ph = ((t + 0.8 * k) / 2.4) % 1.0
        aa = a * min(1, ph * 4) * (1 - ph)
        if aa > 0.01:
            texto(ctx, "z", x + 60 * ph * s + 18 * k * s, y - 150 * ph * s, (40 + 22 * k) * s, fill=BLANCO,
                  sw=7 * s, alpha=aa)


def mesita(ctx, x, y, s=1.0):
    """Mesita de luz; (x, y) = centro de arriba."""
    with en(ctx, x, y, s):
        rrect(ctx, -90, 0, 180, 170, 14)
        rellena(ctx, MADERA, 7)
        rrect(ctx, -70, 30, 140, 50, 8)
        rellena(ctx, MADERA_OSC, 5)
        ctx.arc(0, 55, 8, 0, TAU)
        rellena(ctx, AMARILLO, 4)
        for sx in (-1, 1):
            ctx.rectangle(sx * 70 - 9, 168, 18, 28)
            rellena(ctx, MADERA_OSC, 5)


def vasito(ctx, x, y, s=1.0, rot=0.0, ola=0.0, cara="tranqui", piernas=0.0, paso=0.0, t=0.0, look=(0, 0),
           gotas=0.0, alpha=1.0):
    """Vasito de agua con cara. (x, y) = centro de abajo. ola = inclinación de la superficie del agua (radianes,
    respecto del suelo). piernas = 0..1 (aparecen), paso = fase de la caminata."""
    if s <= 0.01 or alpha <= 0.01:
        return
    caras = {"tranqui": dict(ojos="open", boca="smile"), "dormido": dict(ojos="closed", boca="smile"),
             "susto": dict(ojos="wide", boca="o", ceja="worried"), "feliz": dict(ojos="happy", boca="grin"),
             "mira": dict(ojos="open", boca="flat"), "aprieta": dict(ojos="closed", boca="wavy", ceja="worried")}
    with en(ctx, x, y, s), alfa(ctx, alpha):
        if piernas > 0.01:
            for k, sx in enumerate((-1, 1)):
                fase = math.sin(paso * TAU + k * math.pi)
                largo = 46 * piernas
                ctx.move_to(sx * 26, -6)
                fx, fy = sx * 26 + 18 * fase, -6 + largo - 8 * max(0, fase if k == 0 else -fase)
                ctx.line_to(fx, fy)
                trazo(ctx, INK, 11)
                elipse(ctx, fx + 10, fy + 2, 18, 9)
                rellena(ctx, INK, 2)
            ctx.translate(0, -46 * piernas + 6 * piernas)
        ctx.rotate(rot)
        ctx.move_to(-62, -170)
        ctx.line_to(62, -170)
        ctx.line_to(50, 0)
        ctx.line_to(-50, 0)
        ctx.close_path()
        path = ctx.copy_path()
        ctx.set_source_rgba(*VIDRIO, 0.85)
        ctx.fill()
        # agua: la superficie queda horizontal respecto del suelo (más la ola)
        ctx.save()
        ctx.append_path(path)
        ctx.clip()
        ctx.translate(0, -78)
        ctx.rotate(-rot + ola + 0.05 * math.sin(t * 9) * min(1, abs(ola) * 4))
        ctx.rectangle(-300, 0, 600, 600)
        ctx.set_source_rgb(*AGUA)
        ctx.fill()
        ctx.move_to(-300, 0)
        ctx.line_to(300, 0)
        trazo(ctx, AGUA_OSC, 6)
        ctx.restore()
        ctx.append_path(path)
        trazo(ctx, INK, 8)
        ctx.move_to(-44, -150)
        ctx.line_to(-36, -18)
        trazo(ctx, BLANCO, 9, 0.7)
        carita(ctx, 0, -116, 52, 0.62, **caras[cara], look=look)
        if gotas > 0.01:
            for k in range(5):
                ang = -math.pi / 2 + (k - 2) * 0.45
                d = 40 + 120 * gotas
                gx, gy = d * math.cos(ang), -170 + d * math.sin(ang) + 140 * gotas * gotas
                ctx.arc(gx, gy, 11 * (1 - 0.4 * gotas), 0, TAU)
                rellena(ctx, AGUA, 4, a=1 - gotas)


def velo(ctx, x, y, R, frac, num, s=1.0, temblor=0.0, t=0.0, unidad="KM/H", a=1.0, rojo=0.0):
    """Velocímetro: dial de media luna (frac 0..1) y lectura con número y unidad."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        # panel
        ctx.new_sub_path()
        ctx.arc(0, 0, R * 1.12, math.pi, TAU)
        ctx.line_to(R * 1.12, R * 0.62)
        ctx.line_to(-R * 1.12, R * 0.62)
        ctx.close_path()
        rellena(ctx, PANEL, 8)
        # arco de color verde -> amarillo -> rojo
        for k in range(30):
            a0 = math.pi + math.pi * k / 30
            a1 = math.pi + math.pi * (k + 1) / 30 + 0.01
            q = k / 29
            col = (lerp(0.17, 1.0, min(1, q * 2)), lerp(0.83, 0.23, max(0, q * 2 - 1)), lerp(0.35, 0.23, q))
            ctx.arc(0, 0, R * 0.92, a0, a1)
            trazo(ctx, col, R * 0.12)
        for k in range(11):
            ang = math.pi + math.pi * k / 10
            r0 = R * (0.72 if k % 5 == 0 else 0.78)
            ctx.move_to(r0 * math.cos(ang), r0 * math.sin(ang))
            ctx.line_to(R * 0.84 * math.cos(ang), R * 0.84 * math.sin(ang))
            trazo(ctx, BLANCO, 6 if k % 5 == 0 else 4)
        # aguja
        f = clamp(frac, 0, 1.06) + temblor * 0.035 * math.sin(t * 47) + temblor * 0.02 * math.sin(t * 31)
        ang = math.pi + math.pi * f
        ctx.move_to(-R * 0.12 * math.cos(ang), -R * 0.12 * math.sin(ang))
        ctx.line_to(R * 0.8 * math.cos(ang), R * 0.8 * math.sin(ang))
        trazo(ctx, INK, R * 0.1)
        ctx.move_to(-R * 0.12 * math.cos(ang), -R * 0.12 * math.sin(ang))
        ctx.line_to(R * 0.8 * math.cos(ang), R * 0.8 * math.sin(ang))
        trazo(ctx, ROJO, R * 0.06)
        ctx.arc(0, 0, R * 0.11, 0, TAU)
        rellena(ctx, BLANCO, 6)
        # lectura
        if num:
            col = (lerp(1, 1, rojo), lerp(1, 0.35, rojo), lerp(1, 0.35, rojo))
            texto(ctx, num, 0, R * 0.3, R * 0.36, fill=col, sw=R * 0.05)
            texto(ctx, unidad, 0, R * 0.52, R * 0.15, fill=GRIS, stroke=None)


def nube(ctx, x, y, r, a=1.0, cara=None, look=(0, 0)):
    """Nube de base plana; (x, y) = centro de la base, r = radio del bulto del medio."""
    if a <= 0.01 or r <= 0.5:
        return
    with alfa(ctx, a):
        bultos = [(-1.1, -0.35, 0.62), (-0.45, -0.75, 0.82), (0.35, -0.85, 1.0), (1.05, -0.4, 0.66)]
        for bx, by, br in bultos:
            ctx.new_sub_path()
            ctx.arc(x + bx * r, y + by * r, br * r, 0, TAU)
        ctx.new_sub_path()
        rrect(ctx, x - 1.6 * r, y - 0.5 * r, 3.2 * r, 0.5 * r, 0.25 * r)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(max(3, r * 0.14))
        ctx.stroke_preserve()
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        if cara:
            carita(ctx, x, y - 0.45 * r, 0.5 * r, r / 120, ojos=cara[0], boca=cara[1], look=look)


def bolita_aire(ctx, x, y, r, a=1.0, cara=("open", "smile"), look=(0, 0), ceja=None):
    if a <= 0.01 or r <= 0.5:
        return
    with alfa(ctx, a):
        ctx.arc(x, y, r, 0, TAU)
        rellena(ctx, AIRE, max(3, r * 0.12))
        carita(ctx, x, y - 0.05 * r, 0.62 * r, r / 110, ojos=cara[0], boca=cara[1], ceja=ceja, look=look)


MANCHAS_P = [(0.55, 0.2, 0.30, 0.55), (0.62, 1.6, 0.26, 0.45), (0.5, 2.7, 0.32, 0.5), (0.68, 3.9, 0.22, 0.6),
             (0.6, 5.1, 0.3, 0.45), (0.25, 4.4, 0.22, 0.3), (0.82, 0.95, 0.12, 0.3), (0.85, 2.2, 0.1, 0.25),
             (0.83, 4.6, 0.12, 0.3), (0.3, 1.2, 0.18, 0.25)]


def tierra_polo(ctx, cx, cy, R, giro, cara=True, ojos="open", boca="smile", look=(0, 0), a=1.0):
    """La Tierra vista desde arriba del polo norte: los continentes giran (giro en radianes; positivo = antihorario
    en pantalla, que es como gira vista desde el norte)."""
    if a <= 0.01 or R <= 1:
        return
    with alfa(ctx, a):
        _elipse_suave(ctx, cx, cy, R * 1.6, R * 1.6, AZUL_T, 0.22)
        ctx.arc(cx, cy, R, 0, TAU)
        ctx.set_source_rgb(*AZUL_T)
        ctx.fill_preserve()
        ctx.save()
        ctx.clip()
        for rf, ang, ra, rt in MANCHAS_P:
            th = ang - giro
            with en(ctx, cx + rf * R * math.cos(th), cy + rf * R * math.sin(th), 1.0, th):
                elipse(ctx, 0, 0, 0.62 * ra * R, 0.62 * rt * R)
                ctx.set_source_rgb(*VERDE_T)
                ctx.fill()
        ctx.arc(cx, cy, R * 0.16, 0, TAU)            # hielo del polo
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.fill()
        ctx.restore()
        ctx.arc(cx, cy, R, 0, TAU)
        trazo(ctx, INK, max(3, R * 0.03))
        if cara:
            carita(ctx, cx, cy - 0.04 * R, 0.42 * R, R / 300, ojos=ojos, boca=boca, look=look)


MANCHAS = [(-0.45, -0.35, 0.42, 0.3), (0.35, -0.1, 0.36, 0.44), (-0.2, 0.5, 0.5, 0.26), (0.55, 0.6, 0.3, 0.2),
           (-0.75, 0.15, 0.2, 0.3)]


def tierra_lado(ctx, x, y, R, ojos="open", boca="smile", look=(0, 0), a=1.0):
    if a <= 0.01:
        return
    with alfa(ctx, a):
        _elipse_suave(ctx, x, y, R * 1.7, R * 1.7, AZUL_T, 0.22)
        ctx.arc(x, y, R, 0, TAU)
        ctx.set_source_rgb(*AZUL_T)
        ctx.fill_preserve()
        ctx.save()
        ctx.clip()
        for mx, my, rx, ry in MANCHAS:
            elipse(ctx, x + mx * R, y + my * R, rx * R, ry * R)
            ctx.set_source_rgb(*VERDE_T)
            ctx.fill()
        ctx.restore()
        ctx.arc(x, y, R, 0, TAU)
        trazo(ctx, INK, max(3, R * 0.035))
        carita(ctx, x, y - 0.06 * R, 0.62 * R, R / 150, ojos=ojos, boca=boca, look=look)


def sol(ctx, x, y, R, t, ojos="open", boca="smile", look=(0, 0), a=1.0):
    if a <= 0.01 or R <= 0.5:
        return
    with alfa(ctx, a):
        _elipse_suave(ctx, x, y, R * 2.4, R * 2.4, SOL_C, 0.35)
        for i in range(12):
            ang = TAU * i / 12 + t * 0.35
            r0, r1 = R * 1.12, R * (1.38 + 0.06 * math.sin(t * 3 + i))
            w = 0.13
            ctx.move_to(x + r0 * math.cos(ang - w), y + r0 * math.sin(ang - w))
            ctx.line_to(x + r1 * math.cos(ang), y + r1 * math.sin(ang))
            ctx.line_to(x + r0 * math.cos(ang + w), y + r0 * math.sin(ang + w))
            ctx.close_path()
        rellena(ctx, SOL2, max(1.5, R * 0.035))
        ctx.arc(x, y, R, 0, TAU)
        g = cairo.RadialGradient(x - R * 0.3, y - R * 0.35, R * 0.1, x, y, R)
        g.add_color_stop_rgb(0, *hx("#FFE56B"))
        g.add_color_stop_rgb(1, *SOL_C)
        ctx.set_source(g)
        ctx.fill_preserve()
        trazo(ctx, INK, max(2, R * 0.05))
        carita(ctx, x, y - 0.06 * R, 0.62 * R, R / 150, ojos=ojos, boca=boca, look=look, rubor=True)


def avion_arriba(ctx, x, y, s, rot, a=1.0):
    """Avión visto desde arriba, apuntando hacia +x."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s, rot), alfa(ctx, a):
        ctx.move_to(-20, 0)
        ctx.line_to(-38, -100)
        ctx.line_to(-8, -100)
        ctx.line_to(30, -4)
        ctx.line_to(30, 4)
        ctx.line_to(-8, 100)
        ctx.line_to(-38, 100)
        ctx.close_path()
        rellena(ctx, GRIS, 5)
        ctx.move_to(-92, 0)
        ctx.line_to(-104, -36)
        ctx.line_to(-88, -36)
        ctx.line_to(-70, 0)
        ctx.line_to(-88, 36)
        ctx.line_to(-104, 36)
        ctx.close_path()
        rellena(ctx, GRIS, 5)
        elipse(ctx, 0, 0, 110, 17)
        rellena(ctx, BLANCO, 5)
        elipse(ctx, 88, 0, 12, 9)
        ctx.set_source_rgb(*AGUA_OSC)
        ctx.fill()


# ------------------------------------------------------------------ Vos y la pieza (la apertura)
BED = (640, 1270, 1.1)            # centro de abajo de la cama y escala
MES = (150, 1130, 0.95)           # mesita (centro de arriba)
VAS = (MES[0], MES[1], 0.55)      # vasito arriba de la mesita
VEL = (540, 600, 230)             # velocímetro (x, y del centro del dial, radio)

T_QUIETO = b(0, "quieto")
T_O = b(1)
T_CREES = b(1, "crees")
T_LA2 = b(2)
T_GIRA = b(2, "gira")
T_MIL = b(2, "1.000")
T_MAS3 = b(3)
T_AVION3 = b(3, "avion")
T_POR4 = b(4)
T_NADA4 = b(4, "nada")
T_SI5 = b(5)


def apertura_velo(u):
    """(fracción de la aguja, número) del velocímetro de la apertura; antes de 0 es el cierre del loop: la aguja
    viene desde 107.000 y cae a 0 justo al cerrar."""
    if u < 0:
        caida = prog(u, -1.25, 1.2, "inout")
        frac = lerp(1.04, 0.0, caida)
        v = 107000 * (1 - caida) ** 2.2
        return frac, fmt_num(v)
    frac = 0.0
    if u >= T_O:
        frac = 0.03 * prog(u, T_O, 0.4)
    return frac, "0"


def fmt_num(v):
    v = int(round(v))
    return f"{v:,}".replace(",", ".")


def d_apertura(ctx, u, modo="apertura"):
    """La pieza: Vos dormido en la cama, la mesita con el vasito y el velocímetro arriba.
    modo "pregunta" = la misma pieza mientras se pregunta "¿por qué no sientes nada?" (va a más de 1.000)."""
    fondo(ctx, u)
    preg = modo == "pregunta"
    z = 1.0
    if not preg:
        z = 1 + 0.06 * prog(u, T_O, 1.0, "inout")
    ctx.save()
    zoom(ctx, z, 540, 1000)
    if preg:
        for k in range(4):
            lineas_velocidad(ctx, 900, 820 + k * 140, 420, u + 0.3 * k, n=3, sep=40, a=0.55, ang=math.pi, seed=k)
    bx, by, bk = BED
    cama(ctx, bx, by, bk * pop(u, -2.0, 0.4))
    zetas(ctx, bx - 250, by - 300, u, 1.0, a=prog(u, -1.6, 0.3) if not preg else 1.0)
    mx, my, mk = MES
    sm = pop(u, -1.7, 0.35)
    if sm > 0.01:
        mesita(ctx, mx, my, mk * sm)
    vx, vy, vk = VAS
    if preg:
        cara, look = "tranqui", (0.6, -0.6)
    elif u >= T_O:
        cara, look = "mira", (0.5, -0.8)
    else:
        cara, look = "dormido", (0, 0)
    vasito(ctx, vx, vy, vk * pop(u, -1.45, 0.35), cara=cara, look=look, t=u)
    # velocímetro
    x, y, R = VEL
    if preg:
        velo(ctx, x, y, R, 0.82, "+1.000", t=u)
        signo(ctx, "?", 870, 960, 260, u, T_POR4 - 0.05)
    else:
        frac, num = apertura_velo(u)
        tem = 0.6 * prog(u, T_O, 0.3) if u >= 0 else 0.4 * (1 - prog(u, -0.3, 0.3))
        velo(ctx, x, y, R, frac, num, s=pop(u, -1.3, 0.35), temblor=tem, t=u)
        if u >= 0:
            signo(ctx, "?", x + 300, y - 170, 150, u, T_CREES - 0.05)
    ctx.restore()


def d_pregunta(ctx, t):
    d_apertura(ctx, t, "pregunta")


# ------------------------------------------------------------------ 2. la Tierra gira y te lleva
TC = (540, 1000)                  # centro de la Tierra (vista del polo)
RT = 340
KB = 0.2                          # escala de la cama sobre la Tierra
OMEGA = 0.6                       # giro por segundo (exagerado: la de verdad da una vuelta por día)
T_Z0 = b(2) - 0.08
T_Z1 = T_Z0 + 1.35


def giro2(t):
    """Ángulo girado por la Tierra en la escena 2 (arranca suave en "gira")."""
    dt = t - (T_GIRA - 0.1)
    if dt <= 0:
        return 0.0
    ramp = 0.5
    return OMEGA * (dt - ramp / 2) if dt > ramp else OMEGA * dt * dt / (2 * ramp)


def en_borde(th, r):
    return TC[0] + r * math.cos(th), TC[1] + r * math.sin(th)


def d_tierra(ctx, t):
    fondo(ctx, t)
    q = prog(t, T_Z0, T_Z1 - T_Z0, "inout")
    g = giro2(t)
    th_b = -math.pi / 2 - g
    bxw, byw = en_borde(th_b, RT)
    # cámara: de la cama en primer plano (como en la apertura) a la Tierra entera
    z0 = BED[2] / KB
    z = z0 ** (1 - q)
    fx, fy = lerp(bxw, TC[0], q), lerp(byw, TC[1], q)
    ax, ay = lerp(BED[0], TC[0], q), lerp(BED[1], TC[1], q)
    ctx.save()
    ctx.translate(ax, ay)
    ctx.scale(z, z)
    ctx.translate(-fx, -fy)
    tierra_polo(ctx, TC[0], TC[1], RT, g, ojos="open", look=(0.0, -0.4))
    # rayitas detrás de la cama
    mov = clamp((t - T_GIRA) / 0.6)
    for k in range(3):
        rr = RT + 40 + k * 32
        for j in range(2):
            ph = (t * 1.8 + 0.33 * k + 0.5 * j) % 1.0
            a0 = th_b + 0.18 + ph * 0.5
            ctx.new_sub_path()
            ctx.arc(TC[0], TC[1], rr, a0, a0 + 0.22)
            trazo(ctx, BLANCO, 6 / max(z, 1), 0.7 * mov * (1 - ph))
    cama(ctx, bxw, byw, KB, rot=th_b + math.pi / 2)
    # el avión: va al lado, más lento, y queda atrás
    if t >= T_MAS3 - 0.25:
        g0 = giro2(T_MAS3 - 0.25)
        ga = g0 + 0.16 + 0.62 * (g - g0)
        th_a = -math.pi / 2 - ga
        px, py = en_borde(th_a, RT + 115)
        rot = math.atan2(-math.cos(th_a), math.sin(th_a))
        sa = pop(t, T_MAS3 - 0.25, 0.35)
        avion_arriba(ctx, px, py, 0.55 * sa, rot)
    ctx.restore()
    # velocímetro (pantalla): baja de la apertura a la parte de arriba
    x, y, R = VEL
    vy, vs = lerp(y, 330, q), lerp(1.0, 0.68, q)
    frac = lerp(0.03, 0.82, prog(t, T_GIRA, T_MIL + 0.3 - T_GIRA, "inout"))
    num = "0" if t < T_GIRA else ("+1.000" if t >= T_MIL - 0.05 else fmt_num(1000 * prog(t, T_GIRA, T_MIL - T_GIRA)))
    velo(ctx, x, vy, R, frac, num, s=vs * bump(t, T_MIL - 0.05, 0.3, 0.12), t=t)
    if t >= T_MAS3:
        kartel(ctx, "MÁS RÁPIDO QUE UN AVIÓN", 540, 1440 - 60, 50, t, T_AVION3 - 0.1, box=AMARILLO)


# ------------------------------------------------------------------ 4a. si fueras tan rápido: el viento
T_FUERAS = b(5, "fueras")
T_GOLPEARIA = b(5, "golpearia")
T_VIENTO = b(5, "viento")
T_NO6 = b(6)
T_PORQUE6 = b(6, "porque")


def d_viento(ctx, t):
    fondo(ctx, t)
    gris = prog(t, T_NO6, 0.3)
    # marco punteado: es lo que pasaría, no lo que pasa
    ctx.set_dash([26, 18])
    rrect(ctx, 90, 330, 900, 1010, 40)
    trazo(ctx, BLANCO, 8, 0.7)
    ctx.set_dash([])
    kartel(ctx, "SI FUERAS ASÍ...", 540, 330, 54, t, T_SI5 - 0.05, box=BLANCO)
    golpe = prog(t, T_GOLPEARIA - 0.15, 0.35, "out") * (1 - prog(t, T_NO6, 0.4))
    # bolitas de aire enojadas que chocan de frente
    for k in range(7):
        ph = ((t - T_SI5) * 1.6 + 0.143 * k) % 1.0
        yy = 520 + (k * 113) % 640
        xx = lerp(1080, 200, ph)
        a = min(1, ph * 5) * min(1, (1 - ph) * 5) * clamp((t - T_SI5) / 0.3) * (1 - gris)
        bolita_aire(ctx, xx, yy, 46, a=a, cara=("open", "wavy"), ceja="angry", look=(-1, 0))
        ctx.move_to(xx + 60, yy)
        ctx.line_to(xx + 200, yy)
        trazo(ctx, BLANCO, 7, 0.6 * a)
    # el vasito en la mesita, empujado por el viento
    sac = golpe * (0.5 + 0.5 * math.sin(t * 13))
    mesita(ctx, 540, 1080, 1.4)
    vasito(ctx, 540 - 20 * golpe, 1080, 1.25, rot=-0.22 * golpe - 0.05 * sac, ola=-0.3 * golpe, t=t,
           cara="aprieta" if golpe > 0.3 else "tranqui", gotas=golpe * ((t * 1.3) % 1.0))
    if gris > 0.01:
        ctx.set_source_rgba(0.05, 0.07, 0.15, 0.45 * gris)
        ctx.paint()
        cruz_roja(ctx, 540, 830, pop(t, T_NO6 - 0.03, 0.3) * 1.6)


# ------------------------------------------------------------------ 4b. el aire, tu casa, tu calle y las nubes giran contigo
TC2 = (540, 960)
RT2 = 300
OMEGA2 = 0.32
T_AIRE6 = b(6, "aire")
T_CONTIGO = b(6, "contigo")
T_CASA7 = b(7, "casa")
T_CALLE7 = b(7, "calle")
T_NUBES7 = b(7, "nubes")
T_TAMBIEN7 = b(7, "tambien")
T_E4B = T_PORQUE6 - 0.1
BOLITAS = [(-1.2, 52), (-0.55, 78), (0.15, 48), (0.85, 74), (1.6, 55), (2.35, 80), (3.1, 50), (3.85, 72),
           (4.6, 58), (5.35, 76)]


def d_aire(ctx, t):
    fondo(ctx, t)
    g = OMEGA2 * (t - T_E4B)
    cx, cy = TC2
    # capa de aire: gira con la Tierra
    sa = pop(t, T_AIRE6 - 0.15, 0.4)
    if sa > 0.01:
        ctx.arc(cx, cy, RT2 + 125 * sa, 0, TAU)
        ctx.set_source_rgba(*hx("#5FB8FF"), 0.35)
        ctx.fill()
        ctx.arc(cx, cy, RT2 + 125 * sa, 0, TAU)
        ctx.set_dash([18, 14])
        trazo(ctx, AIRE, 5, 0.8)
        ctx.set_dash([])
    tierra_polo(ctx, cx, cy, RT2, g, ojos="happy", boca="grin")
    for k, (ph, dr) in enumerate(BOLITAS):
        th = ph - g
        s = pop(t, T_AIRE6 - 0.1 + 0.04 * k, 0.3)
        bolita_aire(ctx, cx + (RT2 + dr) * math.cos(th), cy + (RT2 + dr) * math.sin(th), 32 * s,
                    cara=("happy", "smile"))
    # la calle (un tramo del borde), el farol y la casa
    th0 = -math.pi / 2 - g
    sc = prog(t, T_CALLE7 - 0.1, 0.35, "out")
    if sc > 0.01:
        a0, a1 = th0 + 0.12, th0 + 0.12 + 0.55 * sc
        ctx.new_sub_path()
        ctx.arc(cx, cy, RT2 + 4, a0, a1)
        trazo(ctx, ASFALTO, 22)
        ctx.new_sub_path()
        ctx.arc(cx, cy, RT2 + 4, a0, a1)
        ctx.set_dash([10, 12])
        trazo(ctx, AMARILLO, 4)
        ctx.set_dash([])
        tf = th0 + 0.5
        fx, fy = cx + RT2 * math.cos(tf), cy + RT2 * math.sin(tf)
        with en(ctx, fx, fy, pop(t, T_CALLE7, 0.3), tf + math.pi / 2):
            ctx.move_to(0, 0)
            ctx.line_to(0, -82)
            ctx.line_to(14, -92)
            trazo(ctx, INK, 9)
            ctx.arc(18, -86, 10, 0, TAU)
            rellena(ctx, AMARILLO, 4)
    scasa = pop(t, T_CASA7 - 0.1, 0.35)
    if scasa > 0.01:
        hx_, hy_ = cx + RT2 * math.cos(th0), cy + RT2 * math.sin(th0)
        with en(ctx, hx_, hy_, scasa * 0.9, th0 + math.pi / 2):
            ctx.rectangle(-40, -62, 80, 62)
            rellena(ctx, PARED, 6)
            ctx.move_to(-54, -60)
            ctx.line_to(0, -108)
            ctx.line_to(54, -60)
            ctx.close_path()
            rellena(ctx, TECHO, 6)
            rrect(ctx, -12, -36, 24, 36, 4)
            rellena(ctx, MADERA, 4)
    # nubes
    for k, (ph, dr) in enumerate([(-0.45, 92), (0.35, 100)]):
        sn = pop(t, T_NUBES7 - 0.1 + 0.08 * k, 0.35)
        th = -math.pi / 2 + ph - g
        with en(ctx, cx + (RT2 + dr) * math.cos(th), cy + (RT2 + dr) * math.sin(th), 1.0, th + math.pi / 2):
            nube(ctx, 0, 16, 30 * sn, cara=("happy", "smile"))
    # tildes: todo va con vos
    for tt, ox in ((T_AIRE6, -330), (T_CASA7, -110), (T_CALLE7, 110), (T_NUBES7, 330)):
        tilde(ctx, 540 + ox, 300, pop(t, tt + 0.1, 0.3) * 1.15)
    for tt, ox, txt in ((T_AIRE6, -330, "AIRE"), (T_CASA7, -110, "CASA"), (T_CALLE7, 110, "CALLE"),
                        (T_NUBES7, 330, "NUBES")):
        s = pop(t, tt + 0.1, 0.3)
        if s > 0.01:
            texto(ctx, txt, 540 + ox, 380, 40 * s, fill=BLANCO, sw=7)


# ------------------------------------------------------------------ 5. tu cuerpo: no siente la velocidad, siente el cambio
T_CUERPO8 = b(8, "cuerpo")
T_NO9 = b(9)
T_VELOCIDAD9 = b(9, "velocidad")
T_SOLO9 = b(9, "solo")
T_CAMBIA9 = b(9, "cambia")


def frac_cuerpo(t):
    f = 0.82
    if t >= T_SOLO9 + 0.35:
        k = prog(t, T_SOLO9 + 0.35, 0.25, "out") * (1 - prog(t, T_CAMBIA9 - 0.05, 0.25, "inout"))
        f -= 0.5 * k
        f += 0.45 * prog(t, T_CAMBIA9 - 0.05, 0.25, "out") * (1 - prog(t, T_CAMBIA9 + 0.4, 0.3))
    return f


def d_cuerpo(ctx, t):
    fondo(ctx, t)
    f = frac_cuerpo(t)
    df = (frac_cuerpo(t + 0.03) - frac_cuerpo(t - 0.03)) / 0.06       # cambio de velocidad
    sac = clamp(abs(df) / 2.0)
    sac_lento = max(sac, clamp(abs(frac_cuerpo(t - 0.15) - f) * 3))
    velo(ctx, 760, 760, 190, f, fmt_num(1000 * f / 0.82), s=pop(t, b(8) - 0.1, 0.35), temblor=sac, t=t)
    cara = "susto" if sac_lento > 0.15 else ("dormido" if t >= T_NO9 else "tranqui")
    ola = -0.5 * clamp(df / 2.0, -1, 1) + 0.12 * sac_lento * math.sin(t * 14)
    vasito(ctx, 300, 1180, 1.6 * pop(t, b(8) - 0.05, 0.35), rot=0.06 * sac * math.sin(t * 30), ola=ola, cara=cara,
           t=t, gotas=sac_lento * ((t * 2.5) % 1.0))
    kartel(ctx, "TU CUERPO", 300, 640, 58, t, T_CUERPO8 - 0.1, box=AMARILLO, rot=-0.04)
    if T_NO9 <= t < T_SOLO9 + 0.2:
        signo(ctx, "0", 300, 860, 120, t, T_VELOCIDAD9, col=VERDE, sw=12)
    signo(ctx, "!", 450, 820, 200, t, T_CAMBIA9 - 0.02, col=AMARILLO)


# ------------------------------------------------------------------ 6. el avión: pleno vuelo, el pasillo, despegue y sacudidas
T_PIENSA = b(10)
T_VUELO10 = b(10, "vuelo")
T_VAS11 = b(11)
T_RAPIDISIMO = b(11, "rapidisimo")
T_CAMINAS = b(11, "caminas")
T_PASILLO = b(11, "pasillo")
T_CASA11 = b(11, "casa")
T_UNICO = b(12, "unico")
T_DESPEGUE = b(12, "despegue")
T_ATERRIZAJE = b(12, "aterrizaje")
T_SACUDIDAS = b(12, "sacudidas")
AV = (540, 860, 0.8)


def pitch_avion(t):
    p = 0.2 * prog(t, T_DESPEGUE - 0.1, 0.3) * (1 - prog(t, T_ATERRIZAJE - 0.25, 0.3))
    p -= 0.16 * prog(t, T_ATERRIZAJE - 0.1, 0.25) * (1 - prog(t, T_SACUDIDAS - 0.3, 0.3))
    return p


def sacude_avion(t):
    if t < T_SACUDIDAS - 0.05:
        return 0.0, 0.0
    k = clamp((t - T_SACUDIDAS + 0.05) / 0.15)
    return k * 16 * math.sin(t * 37), k * 0.04 * math.sin(t * 23)


def d_avion(ctx, t):
    fondo(ctx, t)
    t0 = T_PIENSA - 0.08
    vel = 0.25 + 0.75 * prog(t, T_RAPIDISIMO - 0.2, 0.4)
    # nubes que pasan (atrás)
    for k in range(6):
        ph = ((t - t0) * (0.35 + 0.9 * vel) * 0.5 + 0.19 * k) % 1.0
        nube(ctx, lerp(1300, -260, ph), 300 + (k * 197) % 900, 50 + 18 * (k % 3), a=0.85)
    for k in range(5):
        lineas_velocidad(ctx, 960, 420 + k * 200, 500, t + 0.2 * k, n=2, sep=60, a=0.5 * prog(t, T_RAPIDISIMO - 0.2,
                         0.4), ang=0, seed=k)
    entra = 1 - prog(t, t0, 0.6, "out")
    p = pitch_avion(t)
    sx, sr = sacude_avion(t)
    corte = prog(t, T_CAMINAS - 0.35, 0.4)
    x, y, s = AV
    with en(ctx, x - 1200 * entra + sx, y + 0.6 * sx, s, -p + sr):
        # ala de atrás y cola
        ctx.move_to(-60, 40)
        ctx.line_to(-200, -60)
        ctx.line_to(-120, -60)
        ctx.line_to(60, 40)
        ctx.close_path()
        rellena(ctx, GRIS_OSC, 6)
        ctx.move_to(-470, -60)
        ctx.line_to(-560, -250)
        ctx.line_to(-480, -250)
        ctx.line_to(-370, -60)
        ctx.close_path()
        rellena(ctx, ROJO, 6)
        # fuselaje
        ctx.move_to(-560, -40)
        ctx.curve_to(-560, -110, -500, -130, -420, -130)
        ctx.line_to(380, -130)
        ctx.curve_to(520, -130, 600, -60, 600, 0)
        ctx.curve_to(600, 70, 520, 130, 380, 130)
        ctx.line_to(-420, 130)
        ctx.curve_to(-520, 130, -560, 60, -560, -40)
        ctx.close_path()
        cuerpo = ctx.copy_path()
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()
        # adentro: piso, asientos y el vasito que camina
        if corte > 0.01:
            ctx.save()
            rrect(ctx, -440, -105, 860, 205, 30)
            ctx.clip()
            ctx.rectangle(-440, -105, 860, 205)
            ctx.set_source_rgb(*CREMA)
            ctx.fill()
            ctx.rectangle(-440, 80, 860, 30)
            ctx.set_source_rgb(*hx("#A9B4C8"))
            ctx.fill()
            for k in range(6):
                ax = -380 + k * 150
                rrect(ctx, ax, -40, 34, 122, 10)
                rellena(ctx, ASIENTO, 5)
                rrect(ctx, ax - 6, 40, 70, 30, 8)
                rellena(ctx, ASIENTO, 5)
            # caminata: avanza por el pasillo hasta el despegue
            pos = lerp(-330, 250, prog(t, T_CAMINAS, T_DESPEGUE - 0.2 - T_CAMINAS, "inout"))
            camina = 1 - prog(t, T_DESPEGUE - 0.3, 0.3)
            # en el despegue se va para atrás; en el aterrizaje, para adelante; en las sacudidas, salta
            emp = 70 * prog(t, T_DESPEGUE - 0.1, 0.3) * (1 - prog(t, T_ATERRIZAJE - 0.25, 0.3))
            emp -= 50 * prog(t, T_ATERRIZAJE - 0.1, 0.25) * (1 - prog(t, T_SACUDIDAS - 0.3, 0.3))
            salto = abs(math.sin(t * 19)) * 14 * clamp((t - T_SACUDIDAS) / 0.15)
            if t < T_DESPEGUE - 0.15:
                cara, ola, tilt = ("feliz" if t > T_CASA11 else "tranqui"), 0.0, 0.0
            elif t < T_ATERRIZAJE - 0.15:
                cara, ola, tilt = "susto", 0.45, -0.18
            elif t < T_SACUDIDAS - 0.15:
                cara, ola, tilt = "susto", -0.4, 0.15
            else:
                cara, ola, tilt = "aprieta", 0.35 * math.sin(t * 17), 0.1 * math.sin(t * 21)
            vasito(ctx, pos - emp, 82 - salto, 0.78, rot=tilt, ola=ola + p, cara=cara, piernas=1.0,
                   paso=(t - T_CAMINAS) * 1.6 * camina, t=t,
                   gotas=clamp((t - T_SACUDIDAS) / 0.2) * ((t * 2.2) % 1.0))
            ctx.restore()
            # el costado se abre
            ctx.save()
            rrect(ctx, -440, -105, 860, 205, 30)
            ctx.clip()
            ctx.rectangle(-440, -105, 860, 205)
            ctx.set_source_rgba(1, 1, 1, 1 - corte)
            ctx.fill()
            ctx.restore()
            rrect(ctx, -440, -105, 860, 205, 30)
            trazo(ctx, INK, 6, corte)
        # ventanillas (se van con el corte)
        for k in range(9):
            rrect(ctx, -380 + k * 90, -70, 44, 54, 18)
            ctx.set_source_rgba(*AGUA_OSC, 1 - corte)
            ctx.fill_preserve()
            trazo(ctx, INK, 4, 1 - corte)
        # cabina
        ctx.move_to(470, -88)
        ctx.curve_to(520, -84, 556, -56, 570, -30)
        ctx.line_to(480, -30)
        ctx.close_path()
        rellena(ctx, AGUA_OSC, 5)
        ctx.append_path(cuerpo)
        trazo(ctx, INK, 9)
        # ala de adelante
        ctx.move_to(-80, 60)
        ctx.line_to(-260, 230)
        ctx.line_to(-150, 230)
        ctx.line_to(90, 60)
        ctx.close_path()
        rellena(ctx, GRIS, 6)
    kartel(ctx, "COMO EN TU CASA", 540, 1180, 56, t, T_CASA11 - 0.1, T_UNICO - 0.1, box=VERDE)
    for tt, txt, xx, yy, rot in ((T_DESPEGUE, "DESPEGUE", 230, 1180, -0.06),
                                 (T_ATERRIZAJE, "ATERRIZAJE", 540, 1290, 0.04),
                                 (T_SACUDIDAS, "SACUDIDAS", 850, 1180, -0.05)):
        kartel(ctx, txt, xx, yy, 48, t, tt - 0.05, box=AMARILLO, rot=rot)


# ------------------------------------------------------------------ 7. la Tierra es un avión que nunca frena
T_TIERRA13 = b(13, "tierra")
T_AVION13 = b(13, "avion")
T_FRENA = b(13, "frena")
T_ACELERA = b(13, "acelera")
T_SACUDE = b(13, "sacude")
T_CUERPO14 = b(14, "cuerpo")
T_NADA14 = b(14, "nada")
T_SENTIR14 = b(14, "sentir")
TA = (540, 980, 210)


def d_tierra_avion(ctx, t):
    fondo(ctx, t, oscuro=0.25)
    for k in range(6):
        lineas_velocidad(ctx, 1000, 520 + k * 150, 520, t + 0.17 * k, n=2, sep=55, a=0.55, ang=0, seed=k)
    x, y, R = TA
    alas = pop(t, T_AVION13 - 0.15, 0.4)
    yy = y + 6 * math.sin(t * 1.3)
    if alas > 0.01:
        with en(ctx, x, yy, 1.0):
            # cola
            ctx.move_to(-R * 0.7, -R * 0.45)
            ctx.line_to(-R * 0.7 - 150 * alas, -R * 0.45 - 170 * alas)
            ctx.line_to(-R * 0.7 - 70 * alas, -R * 0.45 - 170 * alas)
            ctx.line_to(-R * 0.35, -R * 0.75)
            ctx.close_path()
            rellena(ctx, ROJO, 7)
            # ala
            ctx.move_to(-R * 0.4, R * 0.25)
            ctx.line_to(-R * 0.4 - 230 * alas, R * 0.25 + 250 * alas)
            ctx.line_to(-R * 0.4 - 90 * alas, R * 0.25 + 250 * alas)
            ctx.line_to(R * 0.45, R * 0.35)
            ctx.close_path()
            rellena(ctx, GRIS, 7)
    tierra_lado(ctx, x, yy, R * pop(t, b(13) - 0.15, 0.4), ojos="happy" if t > T_SACUDE else "open",
                boca="grin" if t > T_SACUDE else "smile")
    # el vasito arriba de la Tierra, dormido
    sv = pop(t, T_CUERPO14 - 0.15, 0.35)
    if sv > 0.01:
        vasito(ctx, x, yy - R + 6, 0.62 * sv, cara="dormido", t=t)
        zetas(ctx, x + 50, yy - R - 120, t, 0.8, a=prog(t, T_NADA14, 0.3))
    for tt, txt, yv in ((T_FRENA, "FRENA", 300), (T_ACELERA, "ACELERA", 410), (T_SACUDE, "SE SACUDE", 520)):
        tachado(ctx, txt, 540, yv, 76, t, tt - 0.25, tt + 0.1)
    if t >= T_SENTIR14:
        signo(ctx, "0", 820, 690, 150, t, T_SENTIR14 - 0.05, col=VERDE, sw=12)


# ------------------------------------------------------------------ 8. alrededor del Sol, a 107.000 km/h
T_ESE15 = b(15)
T_MAS15 = b(15, "mas")
T_ALREDEDOR = b(16)
T_SOL16 = b(16, "sol")
T_107 = b(16, "107.000")
T_HORA16 = b(16, "hora")
SC = (540, 900)
RO = 330
OMEGA_O = 0.55


def pos_orbita(t):
    th = -math.pi / 2 - 0.4 - OMEGA_O * (t - T_ESE15)
    return SC[0] + RO * math.cos(th), SC[1] + RO * math.sin(th), th


def d_orbita(ctx, t):
    fondo(ctx, t, oscuro=0.35)
    ex, ey, th = pos_orbita(t)
    q = prog(t, T_ALREDEDOR - 0.6, 1.2, "inout")
    z = lerp(2.6, 1.0, q)
    fx, fy = lerp(ex, SC[0], q), lerp(ey, SC[1], q)
    ctx.save()
    ctx.translate(lerp(540, SC[0], q), lerp(820, SC[1], q))
    ctx.scale(z, z)
    ctx.translate(-fx, -fy)
    # órbita
    ctx.new_sub_path()
    ctx.arc(SC[0], SC[1], RO, 0, TAU)
    ctx.set_dash([16, 16])
    trazo(ctx, BLANCO, 5 / z, 0.55)
    ctx.set_dash([])
    sol(ctx, SC[0], SC[1], 120 * pop(t, T_SOL16 - 0.2, 0.4), t, look=(math.cos(th) * 0.8, math.sin(th) * 0.8))
    # estela de la Tierra
    for k in range(10):
        tt = t - 0.06 * (k + 1)
        px, py, _ = pos_orbita(tt)
        ctx.arc(px, py, 50 * (1 - k / 11), 0, TAU)
        ctx.set_source_rgba(*AZUL_T, 0.25 * (1 - k / 10) * prog(t, T_ESE15, 0.4))
        ctx.fill()
    rapido = prog(t, T_107 - 0.1, 0.3)
    tierra_lado(ctx, ex, ey, 56, ojos="wide" if rapido > 0.5 else "open", boca="o" if rapido > 0.5 else "smile",
                look=(0.6, 0.0))
    ctx.restore()
    # velocímetro: se pasa de rosca
    sv = pop(t, T_ALREDEDOR - 0.1, 0.35)
    f = lerp(0.82, 1.06, rapido)
    num = "+1.000" if t < T_107 - 0.05 else "107.000"
    velo(ctx, 540, 330, 170, f, num, s=sv * bump(t, T_107 - 0.05, 0.3, 0.15), temblor=rapido, t=t, rojo=rapido)


# ------------------------------------------------------------------ 9. cierre: vuelve el primer cuadro
T_CIERRE = b(17) - 0.08


def d_cierre(ctx, t):
    d_apertura(ctx, t - TOTAL)


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_apertura),
    (T_Z0, d_tierra),
    (T_POR4 - 0.08, d_pregunta),
    (T_SI5 - 0.08, d_viento),
    (T_E4B, d_aire),
    (b(8) - 0.08, d_cuerpo),
    (T_PIENSA - 0.08, d_avion),
    (b(13) - 0.08, d_tierra_avion),
    (T_ESE15 - 0.08, d_orbita),
    (T_CIERRE, d_cierre),
]
XF = 0.18


def punch(t, t0, d=0.3, amp=0.05):
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


def escena(t):
    return max(k for k, (t0, _) in enumerate(ESCENAS) if t >= t0)


def capa(ctx, fn, t):
    ctx.save()
    fn(ctx, t)
    ctx.restore()


def componer(ctx, t):
    i = escena(t)
    t0, fn = ESCENAS[i]
    dt = t - t0
    sin_punch = i == len(ESCENAS) - 1 or fn is d_tierra     # el cierre termina igual al inicio; la Tierra sale de la cama
    if i > 0 and dt < XF:
        capa(ctx, ESCENAS[i - 1][1], t)
        ctx.save()
        ctx.push_group()
        if not sin_punch:
            zoom(ctx, punch(t, t0))
        fn(ctx, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(clamp(dt / XF))
        ctx.restore()
        return
    if i > 0 and not sin_punch:
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

    # 1. apertura
    ev(T_QUIETO, "tick", 0.25, f=900, d=0.06)
    ev(T_O, "clic", 0.3)
    ev(T_CREES - 0.05, "pop", 0.4)
    # 2. la Tierra
    ev(T_Z0 + 0.1, "pop", 0.3)
    for k in range(5):
        ev(T_GIRA + 0.25 * k, "tick", 0.18, f=900 + 120 * k, d=0.05)
    ev(T_MIL - 0.05, "golpe", 0.55)
    ev(T_MAS3 - 0.25, "pop", 0.35)
    ev(T_AVION3 - 0.1, "pop", 0.4)
    # 3. pregunta
    ev(T_POR4 - 0.05, "pop", 0.45)
    # 4a. viento
    ev(T_SI5 - 0.05, "pop", 0.35)
    ev(T_GOLPEARIA - 0.1, "golpe", 0.5)
    ev(T_VIENTO, "plop", 0.3)
    ev(T_NO6 - 0.03, "clunk", 0.5)
    # 4b. aire, casa, calle, nubes
    ev(T_AIRE6 - 0.1, "plop", 0.35)
    for tt in (T_AIRE6, T_CASA7, T_CALLE7, T_NUBES7):
        ev(tt + 0.1, "ding", 0.25)
    ev(T_CASA7 - 0.1, "pop", 0.35)
    ev(T_CALLE7 - 0.1, "clic", 0.3)
    ev(T_NUBES7 - 0.1, "pop", 0.3)
    # 5. cuerpo
    ev(b(8) - 0.05, "pop", 0.35)
    ev(T_CUERPO8 - 0.1, "pop", 0.4)
    ev(T_VELOCIDAD9, "tick", 0.3, f=700, d=0.08)
    ev(T_SOLO9 + 0.35, "clunk", 0.4)
    ev(T_CAMBIA9 - 0.05, "golpe", 0.5)
    ev(T_CAMBIA9, "plop", 0.35)
    # 6. avión
    ev(T_PIENSA, "pop", 0.35)
    ev(T_CAMINAS - 0.35, "clic", 0.3)
    k = 0
    while T_CAMINAS + k / 1.6 / 2 < T_DESPEGUE - 0.3:
        ev(T_CAMINAS + k / 1.6 / 2, "tick", 0.1, f=500, d=0.04)
        k += 1
    ev(T_CASA11 - 0.1, "ding", 0.35)
    ev(T_DESPEGUE - 0.05, "golpe", 0.45)
    ev(T_ATERRIZAJE - 0.05, "clunk", 0.45)
    for j in range(4):
        ev(T_SACUDIDAS + 0.16 * j, "golpe", 0.3)
    ev(T_SACUDIDAS + 0.1, "plop", 0.35)
    # 7. la Tierra avión
    ev(b(13) - 0.05, "pop", 0.4)
    ev(T_AVION13 - 0.15, "pop", 0.35)
    for tt in (T_FRENA, T_ACELERA, T_SACUDE):
        ev(tt + 0.1, "clic", 0.4)
    ev(T_CUERPO14 - 0.15, "pop", 0.35)
    ev(T_SENTIR14 - 0.05, "ding", 0.35)
    # 8. órbita
    ev(T_ESE15, "pop", 0.3)
    ev(T_SOL16 - 0.2, "pop", 0.45)
    ev(T_ALREDEDOR - 0.1, "pop", 0.35)
    ev(T_107 - 0.05, "golpe", 0.6)
    for j in range(5):
        ev(T_107 + 0.12 * j, "tick", 0.2, f=1400 + 100 * j, d=0.04)
    # 9. cierre
    ev(TOTAL - 1.3, "pop", 0.3)
    for j in range(6):
        ev(TOTAL - 1.2 + 0.18 * j, "tick", 0.15, f=1500 - 150 * j, d=0.04)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "vas_a_mas_de_mil_km_por_hora.mp4"))
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

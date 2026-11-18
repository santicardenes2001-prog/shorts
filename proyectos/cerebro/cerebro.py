"""Short "¿Por qué pueden operarte el cerebro despierto?" — animación procedural (armazón de astronauta.py).

Estilo del canal: fondo azul con puntos, cosas con cara (el cerebro, los sensores de dolor, el tumor) y subtítulos
palabra por palabra. Vos sale solo en la apertura y el cierre vuelve al primer cuadro: el cuadro de TOTAL es igual al
de 0. La violinista (caso real) no tiene cara: solo manos y violín (T2). Sin flechas de giro ni sonidos sostenidos.

Hilos que se repiten: los rayitos rojos de dolor (suben del cuerpo al cerebro), los sensores con cara en las capas que
envuelven al cerebro y el mapa del cerebro con la zona que hay que cuidar.

    python proyectos/cerebro/cerebro.py --hoja 0,3,6      # hoja de fotogramas -> proyectos/cerebro/fotos/hoja.png
    python proyectos/cerebro/cerebro.py --probar
    python proyectos/cerebro/cerebro.py                   # render -> salidas/por_que_pueden_operarte_el_cerebro_despierto.mp4
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
for _p in (ROOT, os.path.join(ROOT, "proyectos", "pantalla"), os.path.join(ROOT, "proyectos", "picante"),
           os.path.join(ROOT, "proyectos", "sueno")):
    sys.path.insert(0, _p)
import kit  # noqa: E402
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
import sueno as S  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, bump, cartel, clamp, ease, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rng, rrect, texto)
from picante import _elipse_suave, boquita, capa, carita, cejas, fondo_azul, mezcla  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Tu cerebro interpreta el dolor de tu cuerpo, menos el del propio cerebro.",   # b0
    "Si lo tocaran ahora mismo, no te dolería.",                                    # b1
    "Por eso, muchas veces te lo operan despierto.",                                # b2
    "El paciente abre los ojos en plena operación.",                                # b3
    "Habla con los médicos mientras le trabajan el cerebro.",                       # b4
    "No le duele, porque ahí adentro no hay sensores de dolor.",                    # b5
    "Solo le duermen la piel y el hueso.",                                          # b6
    "El dolor de cabeza viene de lo que lo envuelve.",                              # b7
    "¿Para qué despertarlo?",                                                       # b8
    "Para no cortar de más.",                                                       # b9
    "Un tumor puede estar pegado a la zona del habla.",                             # b10
    "Mientras el paciente habla, el cirujano sabe que va bien.",                    # b11
    "Si se traba, se detiene.",                                                     # b12
    "Por ahí no.",                                                                  # b13
    "En Londres operaron así a una violinista.",                                    # b14
    "El tumor estaba junto a la zona que mueve su mano.",                           # b15
    "La despertaron y le dieron su violín.",                                        # b16
    "Tocó mientras le sacaban el tumor.",                                           # b17
    "Conservó su mano intacta, gracias a un detalle.",                              # b18
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
ROSA = hx("#FF9EBB")
ROSA_OSC = hx("#E58BA6")
PIEL = hx("#F8C9A2")
PIEL_OSC = hx("#E3A47E")
HUESO = hx("#F1E6C8")
HUESO_OSC = hx("#D9C79A")
MEMB = hx("#B07AD9")
PANO = hx("#3FA88A")
PANO_OSC = hx("#2D8068")
GUANTE = hx("#8FD0F5")
GUANTE_OSC = hx("#5BAAD8")
ACERO = hx("#D5DAE2")
ACERO_OSC = hx("#8E97A8")
TUMOR = hx("#A3A87E")
TUMOR_OSC = hx("#7A7F58")
MADERA = hx("#B8662B")
MADERA_OSC = hx("#8A4519")
NEGRO = hx("#1A1A22")
LUZ = hx("#FFF4C8")
SENSOR_DORMIDO = hx("#6FB7F2")
NOCHE = hx("#16224A")
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


def poli_cum(pts):
    d = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d.append(d[-1] + math.hypot(x1 - x0, y1 - y0))
    return d


def poli_punto(pts, cum, s):
    s = clamp(s, 0, cum[-1])
    for i in range(1, len(cum)):
        if cum[i] >= s:
            q = (s - cum[i - 1]) / max(cum[i] - cum[i - 1], 1e-6)
            return lerp(pts[i - 1][0], pts[i][0], q), lerp(pts[i - 1][1], pts[i][1], q)
    return pts[-1]


def luz_cenital(ctx, x, a=1.0, ancho=520, y1=1150):
    """Cono de luz de la lámpara del quirófano."""
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


def tilde(ctx, x, y, s, a=1.0):
    """Tilde verde dentro de un círculo."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        ctx.arc(0, 0, 46, 0, TAU)
        rellena(ctx, VERDE, 7)
        ctx.move_to(-22, 2)
        ctx.line_to(-6, 18)
        ctx.line_to(24, -16)
        trazo(ctx, BLANCO, 12)


def cruz_roja(ctx, x, y, s, a=1.0):
    if s <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        for sx in (-1, 1):
            ctx.move_to(-40 * sx, -40)
            ctx.line_to(40 * sx, 40)
        trazo(ctx, INK, 30)
        for sx in (-1, 1):
            ctx.move_to(-40 * sx, -40)
            ctx.line_to(40 * sx, 40)
        trazo(ctx, ROJO, 18)


# ------------------------------------------------------------------ piezas chicas
def rayito(ctx, x, y, r, a=1.0, rot=0.0):
    """Rayito rojo de dolor (la señal que viaja al cerebro)."""
    if r <= 0.5 or a <= 0.01:
        return
    _elipse_suave(ctx, x, y, r * 2.2, r * 2.2, ROJO, 0.45 * a)
    with en(ctx, x, y, r / 30, rot), alfa(ctx, a):
        pts = [(6, -36), (-16, 4), (0, 4), (-8, 36), (18, -8), (2, -8), (12, -36)]
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        rellena(ctx, ROJO, 5)


def estrella(ctx, x, y, r, a=1.0, col=AMARILLO, rot=0.0):
    """Estrella de golpe."""
    if r <= 0.5 or a <= 0.01:
        return
    with en(ctx, x, y, 1.0, rot), alfa(ctx, a):
        n = 9
        for k in range(2 * n + 1):
            rr = r if k % 2 == 0 else r * 0.5
            ang = k * math.pi / n - math.pi / 2
            (ctx.move_to if k == 0 else ctx.line_to)(rr * math.cos(ang), rr * math.sin(ang))
        ctx.close_path()
        rellena(ctx, col, 6)


def chinche(ctx, x, y, s=1.0, a=1.0):
    """Chinche dada vuelta en el piso: cabeza roja abajo y la punta para arriba."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        ctx.move_to(0, -8)
        ctx.line_to(0, -54)
        trazo(ctx, INK, 13)
        ctx.move_to(0, -8)
        ctx.line_to(0, -54)
        trazo(ctx, ACERO, 6)
        elipse(ctx, 0, 0, 40, 14)
        rellena(ctx, ROJO, 6)
        elipse(ctx, -10, -4, 14, 4)
        ctx.set_source_rgba(1, 1, 1, 0.5)
        ctx.fill()


def sensor(ctx, x, y, r, dormido=0.0, enojo=0.0, a=1.0, t=0.0):
    """Sensor de dolor: bolita roja con cara. dormido = 1: azul, ojos cerrados y una z."""
    if r <= 0.5 or a <= 0.01:
        return
    col = mezcla(ROJO, SENSOR_DORMIDO, dormido)
    with alfa(ctx, a):
        if enojo > 0.01:
            _elipse_suave(ctx, x, y, r * 2.4, r * 2.4, ROJO, 0.55 * enojo)
        ctx.arc(x, y, r, 0, TAU)
        rellena(ctx, col, max(3, r * 0.18))
        k = r / 40
        if dormido > 0.5:
            for sx in (-1, 1):
                ctx.move_to(x + sx * 15 * k - 9 * k, y - 4 * k)
                ctx.curve_to(x + sx * 15 * k - 4 * k, y + 4 * k, x + sx * 15 * k + 4 * k, y + 4 * k,
                             x + sx * 15 * k + 9 * k, y - 4 * k)
            trazo(ctx, INK, max(2, 5 * k))
            zq = (t * 0.8) % 1
            texto(ctx, "z", x + r * 0.9 + 10 * zq * k, y - r - 20 * zq * k, 30 * k, fill=BLANCO, sw=4 * k,
                  alpha=1 - zq)
        else:
            carita(ctx, x, y - 4 * k, 30 * k, 0.75 * k, ojos="open", boca="flat" if enojo < 0.5 else "wavy",
                   ceja="angry")


def lupa(ctx, x, y, r, s=1.0, contenido=None):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.move_to(r * 0.7, r * 0.7)
        ctx.line_to(r * 1.55, r * 1.55)
        trazo(ctx, INK, 34)
        ctx.move_to(r * 0.75, r * 0.75)
        ctx.line_to(r * 1.5, r * 1.5)
        trazo(ctx, hx("#7A4A2A"), 20)
        ctx.arc(0, 0, r, 0, TAU)
        ctx.set_source_rgba(1, 1, 1, 0.18)
        ctx.fill()
        if contenido:
            ctx.save()
            ctx.arc(0, 0, r, 0, TAU)
            ctx.clip()
            contenido(ctx)
            ctx.restore()
        ctx.arc(0, 0, r, 0, TAU)
        trazo(ctx, INK, 16)
        ctx.arc(0, 0, r, 0, TAU)
        trazo(ctx, ACERO, 7)
        ctx.arc(-r * 0.35, -r * 0.35, r * 0.3, math.pi * 1.05, math.pi * 1.45)
        trazo(ctx, BLANCO, 8, 0.7)


def jeringa(ctx, x, y, s, rot, emb=0.0):
    """Jeringa; (x, y) = punta de la aguja. emb = cuánto bajó el émbolo (0 a 1)."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s, rot):
        ctx.move_to(0, 0)
        ctx.line_to(0, -120)
        trazo(ctx, INK, 9)
        ctx.move_to(0, -4)
        ctx.line_to(0, -120)
        trazo(ctx, ACERO, 4)
        rrect(ctx, -16, -140, 32, 24, 6)
        rellena(ctx, ACERO_OSC, 5)
        rrect(ctx, -40, -380, 80, 245, 14)
        rellena(ctx, hx("#EAF6FF"), 6)
        liq = lerp(200, 40, emb)
        ctx.rectangle(-34, -140 - liq, 68, liq)
        ctx.set_source_rgba(*hx("#7FD0FF"), 0.85)
        ctx.fill()
        for k in range(5):
            ctx.move_to(-40, -170 - 40 * k)
            ctx.line_to(-18, -170 - 40 * k)
        trazo(ctx, INK, 4)
        py = -140 - liq - 10
        rrect(ctx, -34, py - 10, 68, 20, 5)
        rellena(ctx, ACERO_OSC, 5)
        ctx.move_to(0, py)
        ctx.line_to(0, -440)
        trazo(ctx, INK, 16)
        ctx.move_to(0, py)
        ctx.line_to(0, -440)
        trazo(ctx, ACERO, 8)
        rrect(ctx, -46, -452, 92, 22, 8)
        rellena(ctx, ACERO, 5)
        rrect(ctx, -70, -390, 140, 18, 8)
        rellena(ctx, ACERO, 5)


def sonda(ctx, x, y, s, rot, a=1.0):
    """Instrumento fino con mango y una mano con guante; (x, y) = la punta; rot = ángulo hacia donde apunta el mango."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s, rot), alfa(ctx, a):
        ctx.move_to(0, 0)
        ctx.line_to(230, 0)
        trazo(ctx, INK, 14)
        ctx.move_to(4, 0)
        ctx.line_to(230, 0)
        trazo(ctx, ACERO, 7)
        rrect(ctx, 220, -20, 200, 40, 18)
        rellena(ctx, hx("#3E7BE0"), 6)
        # mano con guante que agarra el mango
        rrect(ctx, 270, -62, 150, 124, 50)
        rellena(ctx, GUANTE, 6)
        for k in range(4):
            ctx.arc(280 + 34 * k, 48, 22, 0, TAU)
            rellena(ctx, GUANTE, 5)
        elipse(ctx, 300, -50, 46, 26)
        rellena(ctx, GUANTE, 5)
        rrect(ctx, 400, -70, 260, 140, 40)
        rellena(ctx, GUANTE, 6)


def dedo(ctx, x, y, s, rot):
    """Mano con guante que señala con el índice; (x, y) = la yema del índice; rot = hacia dónde queda la mano."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s, rot):
        rrect(ctx, 140, -70, 380, 150, 60)          # muñeca y puño
        rellena(ctx, GUANTE, 7)
        for k in range(3):
            rrect(ctx, 150 + 50 * k, 40, 60, 80, 28)
            rellena(ctx, GUANTE, 6)
        rrect(ctx, -6, -34, 200, 64, 32)            # índice
        rellena(ctx, GUANTE, 7)
        elipse(ctx, 210, -70, 60, 30)               # pulgar
        rellena(ctx, GUANTE, 6)
        ctx.move_to(70, -28)
        ctx.line_to(70, 24)
        trazo(ctx, GUANTE_OSC, 5)


def globo(ctx, x, y, w, h, s, txt, size=64, col=INK, cola=-1, sacude=0.0, t=0.0):
    if s <= 0.01:
        return
    dx = sacude * 9 * math.sin(t * 70)
    with en(ctx, x + dx, y, s):
        rrect(ctx, -w / 2, -h / 2, w, h, 40)
        cx = cola * w * 0.22
        ctx.move_to(cx - 26, h / 2 - 4)
        ctx.line_to(cx + cola * 30, h / 2 + 70)
        ctx.line_to(cx + 26, h / 2 - 4)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()
        rrect(ctx, -w / 2, -h / 2, w, h, 40)
        trazo(ctx, INK, 9)
        ctx.move_to(cx - 26, h / 2 + 2)
        ctx.line_to(cx + cola * 30, h / 2 + 70)
        ctx.line_to(cx + 26, h / 2 + 2)
        trazo(ctx, INK, 9)
        texto(ctx, txt, 0, 4, size, fill=col, stroke=None)


def nota(ctx, x, y, s, a=1.0, rot=0.0):
    """Nota musical (corchea)."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s, rot), alfa(ctx, a):
        elipse(ctx, 0, 0, 26, 19)
        ctx.save()
        ctx.set_source_rgb(*BLANCO)
        ctx.fill_preserve()
        ctx.restore()
        trazo(ctx, INK, 6)
        ctx.move_to(22, -4)
        ctx.line_to(22, -96)
        ctx.curve_to(40, -80, 62, -70, 50, -36)
        trazo(ctx, BLANCO, 16)
        ctx.move_to(22, -4)
        ctx.line_to(22, -96)
        ctx.curve_to(40, -80, 62, -70, 50, -36)
        trazo(ctx, INK, 6)


# ------------------------------------------------------------------ el mapa del cerebro (vista de costado)
BLOBS = [(-95, -40, 92), (-20, -78, 98), (70, -60, 92), (120, 15, 80), (55, 60, 88), (-45, 55, 90), (-120, 25, 78)]
CISURA_LAT = [(-148, 44), (-80, 30), (-10, 18), (60, 0), (82, -16)]          # separa el lóbulo temporal
CISURA_CEN = [(16, -176), (4, -120), (-12, -70), (-26, -20), (-38, 12)]       # adelante de esta: la franja que mueve
SURCOS = [(-150, -60, -120, -95, -80, -100, -60, -140), (60, -150, 80, -110, 120, -110, 150, -70),
          (-120, 90, -80, 70, -40, 100, 0, 80), (30, 60, 70, 50, 100, 80, 140, 50), (90, -60, 110, -40, 150, -40, 180, -10)]


def _forma_cerebro(ctx):
    for bx, by, br in BLOBS:
        ctx.new_sub_path()
        ctx.arc(bx, by, br, 0, TAU)


def cerebro_mapa(ctx, x, y, s, espejo=False, a=1.0, zonas=None):
    """Cerebro de costado (el de pantalla.py) con las cisuras en su lugar. Sin espejo, el frente queda a la izquierda
    (hemisferio izquierdo); con espejo, a la derecha (hemisferio derecho). zonas(ctx) dibuja encima, recortado."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        if espejo:
            ctx.scale(-1, 1)
        # cerebelo y tronco
        ctx.arc(95, 112, 52, 0, TAU)
        ctx.set_source_rgb(*INK)
        ctx.fill()
        rrect(ctx, 30, 120, 50, 120, 22)
        ctx.fill()
        ctx.arc(95, 112, 44, 0, TAU)
        ctx.set_source_rgb(*ROSA_OSC)
        ctx.fill()
        rrect(ctx, 38, 120, 34, 112, 16)
        ctx.fill()
        for bx, by, br in BLOBS:
            ctx.arc(bx, by, br + 8, 0, TAU)
            ctx.set_source_rgb(*INK)
            ctx.fill()
        _forma_cerebro(ctx)
        ctx.set_source_rgb(*ROSA)
        ctx.fill()
        ctx.save()
        _forma_cerebro(ctx)
        ctx.clip()
        for c in SURCOS:
            ctx.move_to(c[0], c[1])
            ctx.curve_to(*c[2:])
            trazo(ctx, INK, 5, 0.45)
        for pts, w in ((CISURA_LAT, 8), (CISURA_CEN, 7)):
            ctx.move_to(*pts[0])
            for p in pts[1:]:
                ctx.line_to(*p)
            trazo(ctx, INK, w, 0.85)
        if zonas:
            zonas(ctx)
        ctx.restore()


def tumor(ctx, x, y, r, a=1.0, t=0.0, cara=True):
    """Tumor: bulto gris verdoso con cara de pocos amigos."""
    if r <= 1 or a <= 0.01:
        return
    with alfa(ctx, a):
        ctx.new_path()
        n = 14
        for k in range(n + 1):
            ang = k * TAU / n
            rr = r * (1 + 0.09 * math.sin(3 * ang + 1.3) + 0.05 * math.sin(5 * ang))
            (ctx.move_to if k == 0 else ctx.line_to)(x + rr * math.cos(ang), y + rr * math.sin(ang))
        ctx.close_path()
        rellena(ctx, TUMOR, max(3, r * 0.12), TUMOR_OSC)
        if cara and r > 14:
            k = r / 40
            carita(ctx, x, y - 4 * k, 26 * k, 0.6 * k, ojos="open", boca="flat", ceja="angry")


def zona(ctx, x, y, r, col=AMARILLO, a=1.0, rojo=0.0):
    """Zona marcada en el mapa (en coordenadas del cerebro)."""
    if a <= 0.01 or r <= 1:
        return
    c = mezcla(col, ROJO, rojo)
    elipse(ctx, x, y, r, r * 0.85)
    ctx.set_source_rgba(*c, 0.55 * a)
    ctx.fill_preserve()
    ctx.set_dash([10, 8])
    trazo(ctx, c, 5, a)
    ctx.set_dash([])


# ------------------------------------------------------------------ Vos (solo en la apertura)
VOS_POSES = {
    "neutral": dict(),
    "ay": dict(eyes="wide", brows="up", mouth_kind="o"),
    "mira": dict(look=(0.2, -1.0)),
    "contento": dict(eyes="happy", brows="happy", mouth_kind="open_smile"),
}


@functools.lru_cache(maxsize=None)
def vos_surface(pose):
    body = kit.vos(**VOS_POSES[pose])
    png = cairosvg.svg2png(bytestring=kit.svg(520, 820, body).encode(), output_width=1040, output_height=1640)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


def vos(ctx, pose, x, y, k=1.0, alpha=1.0):
    """Vos con los pies en (x, y); k = 1 es el dibujo a 520x820."""
    if alpha <= 0.01 or k <= 0.01:
        return
    s = vos_surface(pose)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(k / 2, k / 2)
    ctx.translate(-520, -1612)
    ctx.set_source_surface(s, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


# ================================================================== escenas
# ------------------------------------------------------------------ 1. apertura (y cierre del loop): todo duele, menos el cerebro
VX, VY, VK = 540, 1365, 0.95                  # pies de Vos


def vp(dx, dy):
    """Punto del dibujo de Vos (520x820) en la pantalla."""
    return VX + (dx - 260) * VK, VY + (dy - 806) * VK


CB = (496, 425, 0.8)                          # cerebro arriba de la cabeza
TALLO = (CB[0] + 55 * CB[2], CB[1] + 236 * CB[2])
CUELLO, CADERA, CABEZA_TOP = vp(260, 455), vp(260, 640), vp(260, 108)
PIE = (604, 1338)
MANO_D, MANO_I = vp(372, 655), vp(148, 655)
HOMBRO_D, HOMBRO_I = vp(338, 505), vp(182, 505)
FIN = (CB[0] + 10, CB[1] + 40)
CAMINOS = [
    [PIE, vp(300, 700), CADERA, CUELLO, CABEZA_TOP, TALLO, FIN],
    [MANO_D, HOMBRO_D, CUELLO, CABEZA_TOP, TALLO, FIN],
    [MANO_I, HOMBRO_I, CUELLO, CABEZA_TOP, TALLO, FIN],
]
CAM_CUM = [poli_cum(c) for c in CAMINOS]
T_DOLOR0 = b(0, "dolor")
T_CUERPO = b(0, "cuerpo")
T_MENOS = b(0, "menos")
T_PROPIO = b(0, "propio")
T_SI1 = b(1)
T_TOCARAN = b(1, "tocaran")
T_AHORA = b(1, "ahora")
T_MISMO = b(1, "mismo")
T_DOLERIA = b(1, "doleria")
GOLPES = [(0.0, 0, 0.85), (T_CUERPO - 0.32, 1, 0.75), (T_CUERPO - 0.1, 2, 0.75)]   # (sale, camino, dura)
LLEGA = [t0 + d for t0, _, d in GOLPES]
TOQUES = [T_PROPIO, T_TOCARAN + 0.05, T_MISMO]
MED = (875, 300, 330)                          # medidor de dolor (x, y de arriba, alto)


def nivel_dolor(u):
    f = 0.0
    for k, tl in enumerate(LLEGA):
        f = max(f, (0.55, 0.78, 1.0)[k] * prog(u, tl - 0.05, 0.25, "out"))
    return f * (1 - prog(u, T_MENOS + 0.05, 0.6))


def medidor(ctx, u, a=1.0):
    x, y0, h = MED
    s = pop(u, -0.75, 0.35)
    if s <= 0.01:
        return
    with en(ctx, x, y0 + h / 2, s), alfa(ctx, a):
        w = 74
        rrect(ctx, -w / 2, -h / 2, w, h, w / 2)
        rellena(ctx, hx("#1B2347"), 7)
        f = nivel_dolor(u)
        if f > 0.01:
            ctx.save()
            rrect(ctx, -w / 2 + 9, -h / 2 + 9, w - 18, h - 18, w / 2 - 9)
            ctx.clip()
            ctx.rectangle(-w / 2, h / 2 - 9 - (h - 18) * f, w, (h - 18) * f + 10)
            ctx.set_source_rgb(*mezcla(hx("#FF9A3D"), ROJO, f))
            ctx.fill()
            ctx.restore()
        texto(ctx, "DOLOR", 0, -h / 2 - 42, 40, fill=BLANCO, sw=7)
        cero = pop(u, T_DOLERIA - 0.05, 0.35)
        if cero > 0.01:
            with en(ctx, 0, h / 2 + 70, cero):
                texto(ctx, "0", 0, 0, 96, fill=VERDE, sw=10)


def d_apertura(ctx, u):
    fondo(ctx, u)
    z = 1 + 0.12 * prog(u, T_SI1 - 0.1, 1.6, "inout")
    ctx.save()
    zoom(ctx, z, 560, 520)
    # Vos y la chinche
    chinche(ctx, PIE[0] + 4, PIE[1] + 32, pop(u, -0.65, 0.3))
    if u >= T_MENOS + 0.2:
        pose = "contento" if u >= T_DOLERIA - 0.1 else "mira"
    elif u >= -0.1:
        pose = "ay"
    else:
        pose = "neutral"
    vos(ctx, pose, VX, VY, VK * pop(u, -1.0, 0.4))
    # cable punteado de la cabeza al cerebro
    cab = prog(u, -0.6, 0.35)
    if cab > 0.01:
        ctx.set_dash([12, 12])
        ctx.move_to(*CABEZA_TOP)
        ctx.line_to(lerp(CABEZA_TOP[0], TALLO[0], cab), lerp(CABEZA_TOP[1], TALLO[1], cab))
        trazo(ctx, AMARILLO, 7, 0.8)
        ctx.set_dash([])
    # golpes: estrella donde duele y el rayito que sube
    for k, (t0, c, d) in enumerate(GOLPES):
        x0, y0 = CAMINOS[c][0]
        st = pop(u, t0 - 0.15, 0.35) * sale(u, t0 + 0.9, 0.3)
        estrella(ctx, x0, y0, (62 if k == 0 else 44) * st, rot=0.2 * k)
        if k == 0 and st > 0.3:
            texto(ctx, "¡AY!", x0 + 120, y0 - 40, 58 * st, fill=AMARILLO, sw=8)
        if t0 <= u < t0 + d + 0.12:
            q = clamp((u - t0) / d)
            px, py = poli_punto(CAMINOS[c], CAM_CUM[c], ease(q, "in") * CAM_CUM[c][-1])
            rayito(ctx, px, py, 34, a=1 - prog(u, t0 + d, 0.12))
    # el cerebro
    toque = max([bump(u, tt, 0.35, 0.10) for tt in TOQUES] + [1.0])
    llega = max([bump(u, tl, 0.3, 0.12) for tl in LLEGA] + [1.0])
    duele = max([clamp(1 - abs(u - (tl + 0.25)) / 0.4) for tl in LLEGA] + [0.0]) * (1 - prog(u, T_MENOS, 0.3))
    bx, by, bs = CB
    for tl in LLEGA:
        if tl <= u < tl + 0.5:
            _elipse_suave(ctx, bx, by, 260, 220, ROJO, 0.5 * (1 - (u - tl) / 0.5))
    mira_dedo = prog(u, T_PROPIO - 0.6, 0.3) * (1 - prog(u, T_DOLERIA - 0.2, 0.3))
    S.cerebrito(ctx, bx, by, bs * pop(u, -0.85, 0.4) * toque * llega,
                p=0.55 * duele, boca="wavy" if duele > 0.4 else ("grin" if u >= T_DOLERIA - 0.1 else "smile"),
                ceja="worried" if duele > 0.4 else None, look=(-0.8 * mira_dedo, -0.3 * mira_dedo), t=u)
    # el dedo que lo toca
    if u >= T_PROPIO - 0.75:
        ent = prog(u, T_PROPIO - 0.75, 0.45, "out") * sale(u, T_DOLERIA + 0.3, 0.4)
        emp = max([clamp(1 - abs(u - tt) / 0.16) for tt in TOQUES] + [0.0])
        tx = bx - 172 * bs + 8 + 22 * emp
        ty = by - 30
        dedo(ctx, lerp(-420, tx, ent), lerp(-120, ty, ent), 0.9, math.radians(200))
        for tt in TOQUES:
            destello(ctx, tx - 6, ty, 50, u, tt, 0.35)
    medidor(ctx, u)
    ctx.restore()


# ------------------------------------------------------------------ 2. quirófano: despierto, abre los ojos y habla
T_POR = b(2)
T_OPERAN = b(2, "operan")
T_DESPIERTO = b(2, "despierto")
T_PACIENTE3 = b(3, "paciente")
T_ABRE = b(3, "abre")
T_OJOS = b(3, "ojos")
T_PLENA = b(3, "plena")
T_HABLA4 = b(4)
T_MEDICOS = b(4, "medicos")
T_TRABAJAN = b(4, "trabajan")
CAB = (540, 880)                              # centro de la cabeza del paciente
VENT = (590, 700, 72)                         # ventana del paño donde se ve el cerebro


def cabeza_paciente(ctx, t, ojos=1.0, look=(0, 0), boca="smile"):
    cx, cy = CAB
    # paño del cuerpo
    ctx.move_to(-60, 1160)
    ctx.curve_to(220, 1080, 860, 1080, 1140, 1160)
    ctx.line_to(1140, H + 40)
    ctx.line_to(-60, H + 40)
    ctx.close_path()
    rellena(ctx, PANO, 8)
    for x0 in (200, 420, 660, 880):
        ctx.move_to(x0, 1140)
        ctx.curve_to(x0 + 20, 1230, x0 - 10, 1300, x0 + 10, 1380)
        trazo(ctx, PANO_OSC, 7)
    # orejas y cara
    for sx in (-1, 1):
        elipse(ctx, cx + sx * 212, cy + 30, 34, 52)
        rellena(ctx, PIEL, 7)
    elipse(ctx, cx, cy, 215, 250)
    rellena(ctx, PIEL, 8)
    # paño sobre la cabeza, con la ventana
    ctx.save()
    elipse(ctx, cx, cy, 215, 250)
    ctx.clip()
    ctx.move_to(cx - 260, cy - 60)
    ctx.curve_to(cx - 120, cy - 110, cx + 120, cy - 110, cx + 260, cy - 60)
    ctx.line_to(cx + 260, cy - 400)
    ctx.line_to(cx - 260, cy - 400)
    ctx.close_path()
    ctx.set_source_rgb(*PANO)
    ctx.fill()
    ctx.move_to(cx - 260, cy - 60)
    ctx.curve_to(cx - 120, cy - 110, cx + 120, cy - 110, cx + 260, cy - 60)
    trazo(ctx, INK, 7)
    vx, vy, vr = VENT
    ctx.arc(vx, vy, vr + 10, 0, TAU)
    ctx.set_source_rgb(*PIEL_OSC)
    ctx.fill()
    ctx.arc(vx, vy, vr, 0, TAU)
    ctx.set_source_rgb(*ROSA)
    ctx.fill()
    ctx.save()
    ctx.arc(vx, vy, vr, 0, TAU)
    ctx.clip()
    for k in range(4):
        ctx.move_to(vx - 90, vy - 50 + 34 * k)
        ctx.curve_to(vx - 40, vy - 80 + 34 * k, vx + 10, vy - 20 + 34 * k, vx + 90, vy - 60 + 34 * k)
        trazo(ctx, INK, 5, 0.5)
    ctx.restore()
    ctx.arc(vx, vy, vr, 0, TAU)
    trazo(ctx, INK, 6)
    ctx.restore()
    elipse(ctx, cx, cy, 215, 250)
    trazo(ctx, INK, 8)
    # cara
    for sx in (-1, 1):
        S.ojo_p(ctx, cx + sx * 75, cy + 40, 1.45, ojos, look, tapa=PIEL)
    ctx.move_to(cx - 8, cy + 85)
    ctx.curve_to(cx + 14, cy + 110, cx + 6, cy + 125, cx - 10, cy + 125)
    trazo(ctx, PIEL_OSC, 7)
    boquita(ctx, cx, cy + 165, boca, 1.25)


def d_quirofano(ctx, t):
    fondo(ctx, t, 0.35)
    luz_cenital(ctx, 560, 0.9, 560, 1200)
    # monitor
    mx, my = 880, 300
    with en(ctx, mx, my, pop(t, T_POR + 0.1, 0.35)):
        rrect(ctx, -130, -90, 260, 180, 22)
        rellena(ctx, hx("#1B2347"), 7)
        ctx.save()
        rrect(ctx, -112, -72, 224, 144, 12)
        ctx.clip()
        pts = []
        for k in range(90):
            xx = -112 + k * 2.6
            ph = ((t * 1.2 - k * 0.012) % 1)
            yy = -60 * math.exp(-((ph - 0.5) * 40) ** 2) + 20 * math.exp(-((ph - 0.56) * 30) ** 2)
            pts.append((xx, yy + 10))
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        trazo(ctx, hx("#7CFF8A"), 5)
        ctx.restore()
    z = 1 + 0.12 * prog(t, T_PACIENTE3 - 0.2, 1.0) - 0.06 * prog(t, T_HABLA4 - 0.1, 0.8)
    ctx.save()
    zoom(ctx, z, CAB[0], CAB[1] + 40)
    ojos = 1 - prog(t, T_ABRE - 0.05, 0.3, "out")
    look = (0.6 * math.sin((t - T_OJOS) * 2.2), -0.3) if t > T_OJOS else (0, 0)
    habla = T_HABLA4 <= t < T_MEDICOS + 0.4
    boca = ("o" if int((t - T_HABLA4) * 8) % 2 == 0 else "grin") if habla else ("smile" if t > T_ABRE else "flat")
    cabeza_paciente(ctx, t, ojos, look, boca)
    # la sonda que trabaja en la ventana
    vx, vy, vr = VENT
    ent = prog(t, T_OPERAN - 0.35, 0.45, "out")
    mueve = 10 * math.sin((t - T_TRABAJAN) * 18) if t >= T_TRABAJAN else 0.0
    if ent > 0.01:
        sonda(ctx, lerp(vx + 600, vx + 18 + mueve, ent), lerp(vy - 520, vy - 6, ent), 1.0, math.radians(-40))
    destello(ctx, vx + 18, vy - 6, 70, t, T_TRABAJAN, 0.45)
    ctx.restore()
    sello(ctx, "DESPIERTO", 360, 330, 82, t, T_DESPIERTO - 0.05, T_ABRE - 0.15, rot=-7)
    globo(ctx, 270, 450, 360, 140, pop(t, T_HABLA4 + 0.1, 0.35), "BLA, BLA", 66, cola=1)


# ------------------------------------------------------------------ 3. capas: piel, hueso, membrana y cerebro
T_NO5 = b(5)
T_PORQUE5 = b(5, "porque")
T_ADENTRO = b(5, "adentro")
T_SENSORES = b(5, "sensores")
T_DOLOR5 = b(5, "dolor")
T_SOLO = b(6)
T_DUERMEN = b(6, "duermen")
T_PIEL = b(6, "piel")
T_HUESO = b(6, "hueso")
T_EL7 = b(7)
T_DOLOR7 = b(7, "dolor")
T_CABEZA7 = b(7, "cabeza")
T_ENVUELVE = b(7, "envuelve")
RC = (540, 2900)
R_PIEL, R_HUESO, R_MEMB, R_CER = 2430, 2320, 2180, 2110
CAPAS = [  # (radio de arriba, radio de abajo, color, nombre, sensores x)
    (R_PIEL, R_HUESO, PIEL, "PIEL", (340, 570, 800, 990)),
    (R_HUESO, R_MEMB, HUESO, "HUESO", (400, 660, 920)),
    (R_MEMB, R_CER, MEMB, "MEMBRANA", (360, 580, 800, 1000)),
]
T_DUERME = [T_PIEL - 0.05, T_HUESO - 0.05, T_HUESO + 0.25]


def y_arco(x, R):
    return RC[1] - math.sqrt(R * R - (x - RC[0]) ** 2)


def banda(ctx, R0, R1):
    xs = np.linspace(-20, W + 20, 40)
    ctx.move_to(xs[0], y_arco(xs[0], R0))
    for x in xs[1:]:
        ctx.line_to(x, y_arco(x, R0))
    for x in xs[::-1]:
        ctx.line_to(x, y_arco(x, R1))
    ctx.close_path()


def d_capas(ctx, t):
    fondo(ctx, t)
    dy = lerp(-700, 0, prog(t, T_NO5 - 0.1, 0.45, "out"))
    rojo = 0.0
    if t >= T_DOLOR7 - 0.1:
        rojo = 0.55 + 0.35 * max(bump(t, T_CABEZA7, 0.5, 1.0) - 1, bump(t, T_ENVUELVE, 0.5, 1.0) - 1)
        rojo *= prog(t, T_DOLOR7 - 0.1, 0.3)
    ctx.save()
    ctx.translate(0, dy)
    # cerebro (todo lo de abajo)
    xs = np.linspace(-20, W + 20, 120)
    ctx.move_to(xs[0], y_arco(xs[0], R_CER))
    for x in xs[1:]:
        ctx.line_to(x, y_arco(x, R_CER) + 10 * (1 - math.cos(x / 36)))
    ctx.line_to(W + 20, H + 20)
    ctx.line_to(-20, H + 20)
    ctx.close_path()
    rellena(ctx, ROSA, 7)
    for k in range(12):
        x0 = 45 + k * 90
        y0 = y_arco(x0, R_CER) + 18
        ctx.move_to(x0, y0)
        ctx.curve_to(x0 + 20, y0 + 70, x0 - 25, y0 + 120, x0 + 5, y0 + 170)
        trazo(ctx, INK, 5, 0.4)
    # las capas que lo envuelven
    for R0, R1, col, nombre, xs_ in CAPAS:
        banda(ctx, R0, R1)
        rellena(ctx, col, 7)
        if rojo > 0.01:
            banda(ctx, R0, R1)
            ctx.set_source_rgba(*ROJO, 0.55 * rojo)
            ctx.fill()
    for k in range(9):
        x0 = 80 + k * 115
        ctx.arc(x0, (y_arco(x0, R_HUESO) + y_arco(x0, R_MEMB)) / 2, 9, 0, TAU)
        ctx.set_source_rgba(*HUESO_OSC, 0.9)
        ctx.fill()
    for i, (R0, R1, col, nombre, xs_) in enumerate(CAPAS):
        ym = (y_arco(140, R0) + y_arco(140, R1)) / 2
        cartel(ctx, nombre, 140, ym, 38 if i < 2 else 32, box=BLANCO, rot=-2, pad=(18, 8), sombra=5, borde=5)
    # sensores
    for i, (R0, R1, col, nombre, xs_) in enumerate(CAPAS):
        for j, x in enumerate(xs_):
            y = (y_arco(x, R0) + y_arco(x, R1)) / 2
            s_ = pop(t, T_SENSORES - 0.1 + 0.05 * (i * 4 + j), 0.3)
            dormido = prog(t, T_DUERME[i] + 0.05 * j, 0.25) * (1 - prog(t, T_DOLOR7 - 0.15, 0.25))
            enojo = (rojo / 0.9) * (1 - dormido)
            rr = (36, 40, 28)[i] * s_ * (1 + 0.15 * enojo * math.sin(t * 30 + j))
            sensor(ctx, x, y, rr, dormido=dormido, enojo=enojo, t=t + j * 0.3)
    # cara del cerebro: tranquilo todo el tiempo
    fs = pop(t, T_NO5 + 0.1, 0.4)
    if fs > 0.01:
        with en(ctx, 540, 1110, fs):
            carita(ctx, 0, 0, 150, 1.6, ojos="open", boca="grin" if t >= T_DOLOR7 else "smile",
                   look=(0, -0.6) if t >= T_DOLOR7 else (0, 0), rubor=True)
    ctx.restore()
    # la lupa que busca sensores adentro
    if T_ADENTRO - 0.2 <= t < T_SOLO + 0.2:
        ls = pop(t, T_ADENTRO - 0.2, 0.35) * sale(t, T_SOLO - 0.05, 0.25)
        lx = lerp(260, 820, prog(t, T_ADENTRO, T_DOLOR5 - T_ADENTRO, "inout"))
        ly = 1040 + 30 * math.sin(t * 5)

        def adentro(c):
            c.set_source_rgb(*ROSA)
            c.paint()
            if t >= T_DOLOR5 - 0.1:
                with en(c, 0, 4, pop(t, T_DOLOR5 - 0.1, 0.35)):
                    texto(c, "0", 0, 0, 150, fill=ROJO, sw=10)

        lupa(ctx, lx, ly, 120, ls, adentro)
    # la jeringa que duerme las capas
    if T_SOLO - 0.3 <= t < T_EL7 + 0.4:
        ent = prog(t, T_SOLO - 0.3, 0.4, "out") * sale(t, T_EL7, 0.35)
        tipx, tipy = 735, y_arco(735, R_PIEL) + 40
        emb = prog(t, T_DUERMEN, T_HUESO + 0.3 - T_DUERMEN)
        jeringa(ctx, lerp(tipx + 500, tipx, ent), lerp(tipy - 500, tipy, ent), 0.85, math.radians(40), emb)
    kartel(ctx, "DOLOR DE CABEZA", 540, 230, 74, t, T_DOLOR7 - 0.1, box=ROJO, fg=BLANCO, rot=-3)


# ------------------------------------------------------------------ 4. el mapa: no cortar de más, la zona del habla
T_PARA8 = b(8)
T_DESPERTARLO = b(8, "despertarlo")
T_PARA9 = b(9)
T_CORTAR = b(9, "cortar")
T_DEMAS = b(9, "de")
T_UN10 = b(10)
T_TUMOR10 = b(10, "tumor")
T_PEGADO = b(10, "pegado")
T_ZONA10 = b(10, "zona")
T_HABLA10 = b(10, "habla")
T_MIENTRAS = b(11)
T_HABLA11 = b(11, "habla")
T_CIRUJANO = b(11, "cirujano")
T_BIEN = b(11, "bien")
T_SI12 = b(12)
T_TRABA = b(12, "traba")
T_DETIENE = b(12, "detiene")
T_POR13 = b(13)
MAPA = (560, 860, 1.75)
BROCA = (-104, -4, 34)
TUM1 = (-56, -46, 36)


def a_mapa(lx, ly, m=MAPA, espejo=False):
    x, y, s = m
    return x + (-lx if espejo else lx) * s, y + ly * s


def d_mapa(ctx, t):
    fondo(ctx, t)
    mx, my, ms = MAPA
    corte_r = 0.0
    corte_a = 0.0
    if T_CORTAR - 0.15 <= t < T_UN10 + 0.1:
        corte_a = prog(t, T_CORTAR - 0.15, 0.25) * sale(t, T_UN10 - 0.1, 0.25)
        corte_r = lerp(46, 120, prog(t, T_DEMAS - 0.05, 0.35, "out"))
    pasa = prog(t, T_DEMAS + 0.15, 0.2) * sale(t, T_UN10 - 0.1, 0.25)
    tum_r = TUM1[2] * pop(t, T_PARA8 + 0.1, 0.4) * bump(t, T_TUMOR10, 0.35, 0.2) * \
        lerp(1, 0.55, prog(t, T_CIRUJANO, T_BIEN + 0.3 - T_CIRUJANO))
    tx_ = TUM1[0] + 6 * math.sin(clamp((t - T_PEGADO) / 0.4) * math.pi) if t >= T_PEGADO else TUM1[0]
    traba = prog(t, T_TRABA - 0.05, 0.15) * sale(t, T_POR13 + 0.6, 0.3)
    bien = T_HABLA11 <= t < T_TRABA - 0.05
    habla_a = prog(t, T_ZONA10 - 0.1, 0.3)
    pulso = 0.0
    if bien:
        pulso = 0.5 + 0.5 * math.sin((t - T_HABLA11) * 14)
    if traba > 0.01:
        pulso = 0.5 + 0.5 * math.sin(t * 30)

    def zonas(c):
        if habla_a > 0.01:
            zona(c, BROCA[0], BROCA[1], BROCA[2] * (1 + 0.08 * pulso) * pop(t, T_ZONA10 - 0.1, 0.35),
                 a=habla_a * (0.75 + 0.25 * pulso), rojo=traba)
        if pasa > 0.01:
            c.arc(TUM1[0], TUM1[1], corte_r, 0, TAU)
            c.set_source_rgba(*ROJO, 0.45 * pasa)
            c.fill()

    cerebro_mapa(ctx, mx, my, ms * pop(t, T_PARA8 - 0.08, 0.4), zonas=zonas)
    ctx.save()
    ctx.translate(mx, my)
    ctx.scale(ms, ms)
    tumor(ctx, tx_, TUM1[1], tum_r, t=t)
    if corte_a > 0.01:
        ctx.set_dash([9, 8])
        ctx.arc(TUM1[0], TUM1[1], corte_r, 0, TAU)
        trazo(ctx, BLANCO, 5, corte_a)
        ctx.set_dash([])
    ctx.restore()
    if pasa > 0.01:
        cruz_roja(ctx, *a_mapa(-150, 40), pop(t, T_DEMAS + 0.15, 0.3) * sale(t, T_UN10 - 0.1, 0.25))
    # tijera de corte que sigue la línea
    if corte_a > 0.01:
        ang = (t - T_CORTAR) * 5
        sx_, sy_ = a_mapa(TUM1[0] + corte_r * math.cos(ang), TUM1[1] + corte_r * math.sin(ang))
        with en(ctx, sx_, sy_, 0.9, ang + math.pi / 2), alfa(ctx, corte_a):
            for sgn in (-1, 1):
                with en(ctx, 0, 0, 1, sgn * 0.25):
                    ctx.move_to(0, 0)
                    ctx.line_to(0, -70)
                    trazo(ctx, INK, 14)
                    ctx.move_to(0, 0)
                    ctx.line_to(0, -70)
                    trazo(ctx, ACERO, 7)
                    ctx.arc(0, 26, 18, 0, TAU)
                    trazo(ctx, INK, 9)
                    ctx.arc(0, 26, 18, 0, TAU)
                    trazo(ctx, hx("#3E7BE0"), 5)
    signo(ctx, "?", 870, 380, 190, t, T_PARA8 + 0.05, T_PARA9 - 0.05)
    # la etiqueta de la zona del habla
    bx_, by_ = a_mapa(BROCA[0], BROCA[1])
    kartel(ctx, "HABLA", bx_ - 40, by_ + 175, 58, t, T_HABLA10 - 0.15, box=AMARILLO if traba < 0.5 else ROJO,
           fg=INK if traba < 0.5 else BLANCO, rot=-3)
    # la sonda que va sacando el tumor
    if t >= T_CIRUJANO - 0.5:
        tpx, tpy = a_mapa(TUM1[0] + 10, TUM1[1] - 16)
        ent = prog(t, T_CIRUJANO - 0.5, 0.45, "out") * sale(t, T_POR13 + 0.35, 0.3)
        para = prog(t, T_DETIENE - 0.05, 0.12)
        mueve = 8 * math.sin((t - T_CIRUJANO) * 16) * (1 - para) * (1 if t < T_TRABA else 0)
        sonda(ctx, lerp(tpx + 520, tpx + mueve, ent), lerp(tpy - 560, tpy, ent), 0.9, math.radians(-50))
        if para > 0.01 and t < T_POR13 + 0.4:
            ctx.arc(tpx + 150, tpy - 170, 26 * pop(t, T_DETIENE - 0.05, 0.3), 0, TAU)
            rellena(ctx, ROJO, 6)
    # el globo del paciente
    gs = pop(t, T_MIENTRAS + 0.1, 0.35)
    txt = "BLA, BLA" if traba < 0.5 else "B... B..."
    globo(ctx, 300, 330, 380, 140, gs, txt, 66, col=INK if traba < 0.5 else ROJO, cola=1, sacude=traba, t=t)
    tilde(ctx, 530, 300, pop(t, T_BIEN - 0.05, 0.35) * (1 - prog(t, T_TRABA - 0.1, 0.1)))
    sello(ctx, "POR AHÍ NO", 560, 1270, 84, t, T_POR13 - 0.05, rot=-6)
    if t >= T_POR13 - 0.05:
        cruz_roja(ctx, *a_mapa((BROCA[0] + TUM1[0]) / 2, (BROCA[1] + TUM1[1]) / 2), 0.8 * pop(t, T_POR13, 0.3))


# ------------------------------------------------------------------ 5. Londres
T_EN14 = b(14)
T_LONDRES = b(14, "londres")
T_VIOLINISTA = b(14, "violinista")


def torre(ctx, x, y, s, a=1.0, t=0.0):
    """Torre del reloj genérica; (x, y) = base."""
    with en(ctx, x, y, s), alfa(ctx, a):
        ctx.rectangle(-70, -560, 140, 560)
        rellena(ctx, NOCHE, 7)
        for k in range(5):
            for sx in (-1, 1):
                rrect(ctx, sx * 30 - 12, -110 - 90 * k, 24, 50, 10)
                ctx.set_source_rgba(*AMARILLO, 0.7)
                ctx.fill()
        ctx.rectangle(-92, -760, 184, 200)
        rellena(ctx, NOCHE, 7)
        ctx.arc(0, -660, 70, 0, TAU)
        rellena(ctx, CREMA, 7)
        ang_h = -math.pi / 2 + 0.6
        ang_m = -math.pi / 2 + t * 1.5
        for ang, L in ((ang_h, 34), (ang_m, 54)):
            ctx.move_to(0, -660)
            ctx.line_to(L * math.cos(ang), -660 + L * math.sin(ang))
            trazo(ctx, INK, 7)
        ctx.rectangle(-76, -880, 152, 120)
        rellena(ctx, NOCHE, 7)
        ctx.move_to(-92, -880)
        ctx.line_to(0, -1080)
        ctx.line_to(92, -880)
        ctx.close_path()
        rellena(ctx, NOCHE, 7)
        ctx.move_to(0, -1080)
        ctx.line_to(0, -1130)
        trazo(ctx, INK, 8)


def violin(ctx, x, y, s, rot, a=1.0):
    """Violín; (x, y) = centro de la caja. En su marco, la voluta queda arriba (y negativa)."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s, rot), alfa(ctx, a):
        # mástil y clavijero
        rrect(ctx, -20, -360, 40, 200, 12)
        rellena(ctx, MADERA_OSC, 6)
        rrect(ctx, -24, -420, 48, 70, 14)
        rellena(ctx, MADERA_OSC, 6)
        for sy in (-405, -378):
            for sx in (-1, 1):
                rrect(ctx, sx * 24 - (26 if sx < 0 else 0), sy - 6, 26, 12, 5)
                rellena(ctx, NEGRO, 4)
        ctx.arc(0, -440, 26, 0, TAU)
        rellena(ctx, MADERA_OSC, 6)
        ctx.arc(0, -440, 11, 0, TAU)
        trazo(ctx, INK, 4)
        # caja
        der = [(0, -195), (70, -195, 104, -165, 102, -110), (100, -60, 62, -52, 64, -12),
               (66, 28, 120, 40, 120, 110), (120, 175, 70, 205, 0, 205)]
        ctx.move_to(*der[0])
        for c in der[1:]:
            ctx.curve_to(*c)
        izq = [(-70, 205, -120, 175, -120, 110), (-120, 40, -66, 28, -64, -12), (-62, -52, -100, -60, -102, -110),
               (-104, -165, -70, -195, 0, -195)]
        for c in izq:
            ctx.curve_to(*c)
        ctx.close_path()
        rellena(ctx, MADERA, 7)
        elipse(ctx, -30, -100, 28, 60)
        ctx.set_source_rgba(1, 1, 1, 0.18)
        ctx.fill()
        # diapasón
        rrect(ctx, -17, -360, 34, 330, 10)
        rellena(ctx, NEGRO, 4)
        # efes
        for sx in (-1, 1):
            ctx.move_to(sx * 44, -30)
            ctx.curve_to(sx * 30, 10, sx * 58, 50, sx * 44, 90)
            trazo(ctx, INK, 6)
        # puente y cordal
        rrect(ctx, -36, 40, 72, 14, 4)
        rellena(ctx, CREMA, 4)
        ctx.move_to(-14, 70)
        ctx.line_to(14, 70)
        ctx.line_to(22, 185)
        ctx.line_to(-22, 185)
        ctx.close_path()
        rellena(ctx, NEGRO, 4)
        for k in range(4):
            xx = -9 + 6 * k
            ctx.move_to(xx, -355)
            ctx.line_to(xx * 1.4, 180)
        trazo(ctx, hx("#E8E2C8"), 2)


def arco(ctx, x, y, s, rot, a=1.0):
    """Arco del violín; (x, y) = centro de la vara."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s, rot), alfa(ctx, a):
        ctx.move_to(-330, 0)
        ctx.line_to(330, 0)
        trazo(ctx, INK, 12)
        ctx.move_to(-330, 0)
        ctx.line_to(330, 0)
        trazo(ctx, MADERA_OSC, 6)
        ctx.move_to(-290, 18)
        ctx.line_to(326, 6)
        trazo(ctx, hx("#F4EFE0"), 5)
        rrect(ctx, -320, -6, 46, 34, 6)
        rellena(ctx, NEGRO, 4)


def puño(ctx, x, y, s, rot=0.0):
    """Mano cerrada (piel), sin cara ni brazo visible."""
    with en(ctx, x, y, s, rot):
        rrect(ctx, -60, -48, 120, 96, 40)
        rellena(ctx, PIEL, 6)
        for k in range(4):
            ctx.arc(-42 + 28 * k, -40, 20, math.pi, TAU)
            trazo(ctx, INK, 5)
        elipse(ctx, -58, 6, 26, 40)
        rellena(ctx, PIEL, 5)


def d_londres(ctx, t):
    fondo(ctx, t, 0.45)
    rr = rng(31)
    for k in range(40):
        x, y = rr.uniform(0, W), rr.uniform(120, 1000)
        tw = 0.5 + 0.5 * math.sin(t * 3 + k)
        ctx.arc(x, y, rr.uniform(2, 4.5), 0, TAU)
        ctx.set_source_rgba(1, 1, 1, 0.35 + 0.4 * tw)
        ctx.fill()
    torre(ctx, 360, 1380, 0.95 * pop(t, T_EN14 - 0.08, 0.4), t=t)
    kartel(ctx, "LONDRES, 2020", 600, 300, 82, t, T_LONDRES - 0.1, rot=-3)
    vs = pop(t, T_VIOLINISTA - 0.05, 0.4)
    violin(ctx, 760, 1010, 0.82 * vs, math.radians(22))
    arco(ctx, 700, 1090, 0.8 * vs, math.radians(-36))


# ------------------------------------------------------------------ 6. la zona que mueve la mano (hemisferio derecho)
T_EL15 = b(15)
T_TUMOR15 = b(15, "tumor")
T_JUNTO = b(15, "junto")
T_ZONA15 = b(15, "zona")
T_MUEVE = b(15, "mueve")
T_MANO15 = b(15, "mano")
MAPA2 = (540, 860, 1.75)
FRANJA = [(-12, -176), (-26, -120), (-42, -70), (-56, -20), (-66, 14)]    # franja que mueve el cuerpo (adelante de la cisura central)
MANO_Z = (-36, -88, 34)
TUM2 = (-96, -96, 34)


def mano_icono(ctx, x, y, s):
    with en(ctx, x, y, s):
        rrect(ctx, -34, -10, 68, 60, 22)
        rellena(ctx, PIEL, 5)
        for k, L in enumerate((50, 62, 58, 46)):
            rrect(ctx, -32 + 17 * k, -10 - L, 14, L + 14, 7)
            rellena(ctx, PIEL, 4)
        elipse(ctx, -40, 18, 12, 24)
        rellena(ctx, PIEL, 4)


def d_mano_zona(ctx, t):
    fondo(ctx, t)
    mx, my, ms = MAPA2
    fr = prog(t, T_ZONA15 - 0.1, 0.35)
    mz = pop(t, T_MUEVE - 0.1, 0.35)

    def zonas(c):
        if fr > 0.01:
            c.move_to(*FRANJA[0])
            for p in FRANJA[1:]:
                c.line_to(*p)
            trazo(c, AMARILLO, 30, 0.5 * fr)
        if mz > 0.01:
            zona(c, MANO_Z[0], MANO_Z[1], MANO_Z[2] * mz * bump(t, T_MANO15, 0.35, 0.2), a=1.0)

    cerebro_mapa(ctx, mx, my, ms * pop(t, T_EL15 - 0.08, 0.4), espejo=True, zonas=zonas)
    ctx.save()
    ctx.translate(mx, my)
    ctx.scale(-ms, ms)
    jx = 8 * prog(t, T_JUNTO - 0.1, 0.3, "out")
    with en(ctx, TUM2[0] + jx, TUM2[1], 1):
        ctx.scale(-1, 1)
        tumor(ctx, 0, 0, TUM2[2] * pop(t, T_TUMOR15 - 0.1, 0.4) * bump(t, T_JUNTO, 0.3, 0.15), t=t)
    ctx.restore()
    hx_, hy_ = a_mapa(MANO_Z[0], MANO_Z[1], MAPA2, espejo=True)
    if mz > 0.01:
        mano_icono(ctx, hx_ - 20, hy_ - 230, 1.3 * pop(t, T_MANO15 - 0.1, 0.35))
        ctx.set_dash([10, 10])
        ctx.move_to(hx_ - 10, hy_ - 150)
        ctx.line_to(hx_, hy_ - 40)
        trazo(ctx, BLANCO, 5, pop(t, T_MANO15 - 0.1, 0.35))
        ctx.set_dash([])
    kartel(ctx, "MANO", hx_ + 150, hy_ - 250, 64, t, T_MANO15 - 0.05, rot=4)
    texto(ctx, "FRENTE", 920, 1280, 40, fill=BLANCO, sw=7, alpha=pop(t, T_EL15 + 0.2, 0.3))
    ctx.move_to(990, 1280)
    ctx.line_to(1040, 1280)
    ctx.move_to(1020, 1262)
    ctx.line_to(1042, 1280)
    ctx.line_to(1020, 1298)
    trazo(ctx, BLANCO, 6, pop(t, T_EL15 + 0.2, 0.3))


# ------------------------------------------------------------------ 7. la despiertan, toca el violín y le sacan el tumor
T_LA16 = b(16)
T_DESPERTARON = b(16, "despertaron")
T_DIERON = b(16, "dieron")
T_VIOLIN16 = b(16, "violin")
T_TOCO = b(17)
T_SACABAN = b(17, "sacaban")
T_TUMOR17 = b(17, "tumor")
T_CONSERVO = b(18)
VIO = (470, 790, 1.0, math.radians(37))      # violín (centro de la caja, escala, giro)
ARCADAS = 1.25                                # idas y vueltas del arco por segundo
MAPA3 = (600, 330, 0.62)


def vl(lx, ly):
    x, y, s, r = VIO
    c, sn = math.cos(r), math.sin(r)
    return x + s * (lx * c - ly * sn), y + s * (lx * sn + ly * c)


def arco_dx(t):
    if t < T_TOCO:
        return 0.0
    return 150 * math.sin(TAU * ARCADAS * (t - T_TOCO))


def d_violin(ctx, t):
    fondo(ctx, t, 0.35)
    luz_cenital(ctx, 520, 0.8, 560, 1200)
    sube = prog(t, T_DIERON - 0.2, 0.55, "out")
    y_off = lerp(520, 0, sube)
    toca = t >= T_TOCO
    # violín, arco y manos (sin cara: solo manos)
    ctx.save()
    ctx.translate(0, y_off)
    x, y, s, r = VIO
    violin(ctx, x, y, s, r)
    pdir = (math.cos(r + math.pi / 2 - 1.35), math.sin(r + math.pi / 2 - 1.35))
    ax, ay = vl(0, 20)
    d = arco_dx(t)
    bxc, byc = ax + pdir[0] * d, ay + pdir[1] * d
    ang_arco = math.atan2(pdir[1], pdir[0])
    arco(ctx, bxc, byc, 1.0, ang_arco)
    puño(ctx, bxc - math.cos(ang_arco) * 300, byc - math.sin(ang_arco) * 300, 1.0, ang_arco)
    nx, ny = vl(0, -300)
    puño(ctx, nx, ny, 0.95, r + math.pi / 2)
    ctx.restore()
    # el paño tapa todo lo demás
    ctx.move_to(-60, 1090)
    ctx.curve_to(260, 1030, 820, 1030, 1140, 1090)
    ctx.line_to(1140, H + 40)
    ctx.line_to(-60, H + 40)
    ctx.close_path()
    rellena(ctx, PANO, 8)
    for x0 in (160, 400, 660, 900):
        ctx.move_to(x0, 1080)
        ctx.curve_to(x0 + 20, 1180, x0 - 10, 1260, x0 + 10, 1360)
        trazo(ctx, PANO_OSC, 7)
    sello(ctx, "DESPIERTA", 540, 330, 88, t, T_DESPERTARON - 0.05, T_TOCO - 0.2, rot=-6, col=VERDE_OSC)
    # notas que salen del violín
    if toca:
        for k in range(10):
            t0 = T_TOCO + k * 0.22
            if t < t0:
                continue
            q = (t - t0) / 1.3
            if q > 1:
                continue
            sx0, sy0 = vl(-60, 60)
            nota(ctx, sx0 - 90 - 140 * q + 30 * math.sin(k * 2.1), sy0 - 60 - 380 * q, 0.9 * pop(t, t0, 0.25),
                 a=1 - q ** 2, rot=0.2 * math.sin(t * 4 + k))
    # arriba: el mapa con el tumor que se achica mientras toca
    if t >= T_TOCO - 0.15:
        ms_ = pop(t, T_TOCO - 0.15, 0.4)
        mx, my, s3 = MAPA3

        def zonas(c):
            zona(c, MANO_Z[0], MANO_Z[1], MANO_Z[2], a=1.0)

        cerebro_mapa(ctx, mx, my, s3 * ms_, espejo=True, zonas=zonas)
        ctx.save()
        ctx.translate(mx, my)
        ctx.scale(-s3 * ms_, s3 * ms_)
        achica = lerp(1.0, 0.0, prog(t, T_SACABAN - 0.1, T_CONSERVO - T_SACABAN, "inout"))
        with en(ctx, TUM2[0], TUM2[1], 1):
            ctx.scale(-1, 1)
            tumor(ctx, 0, 0, TUM2[2] * achica, t=t, cara=achica > 0.4)
        ctx.restore()
        tpx, tpy = a_mapa(TUM2[0], TUM2[1], MAPA3, espejo=True)
        ent = prog(t, T_TOCO, 0.4, "out")
        mueve = 5 * math.sin((t - T_TOCO) * 16)
        sonda(ctx, lerp(tpx - 500, tpx - 8 + mueve, ent), lerp(tpy - 300, tpy - 6, ent), 0.55, math.radians(-150))


# ------------------------------------------------------------------ 8. mano intacta
T_MANO18 = b(18, "mano")
T_INTACTA = b(18, "intacta")
T_GRACIAS = b(18, "gracias")
T_CIERRE = b(18, "un") - 0.12
DEDOS = [(-105, 300, -0.08), (-35, 340, -0.02), (35, 330, 0.03), (100, 260, 0.1)]  # (x base, largo, giro)


def mano_grande(ctx, x, y, s, t, mueve=0.0):
    """Mano izquierda con la palma hacia nosotros: el pulgar queda a nuestra izquierda."""
    with en(ctx, x, y, s):
        rrect(ctx, -80, 150, 160, 260, 50)           # muñeca
        rellena(ctx, PIEL, 8)
        for k, (bx_, L, g) in enumerate(DEDOS):
            gi = g + mueve * 0.12 * math.sin(t * 9 - k * 0.9)
            with en(ctx, bx_, -60, 1, gi):
                rrect(ctx, -32, -L, 64, L + 40, 32)
                rellena(ctx, PIEL, 8)
                for j in (0.38, 0.68):
                    ctx.move_to(-18, -L * j)
                    ctx.line_to(18, -L * j)
                trazo(ctx, PIEL_OSC, 5)
        gp = -0.75 + mueve * 0.15 * math.sin(t * 9 + 2)
        with en(ctx, -150, 80, 1, gp):                 # pulgar
            rrect(ctx, -34, -190, 68, 220, 34)
            rellena(ctx, PIEL, 8)
            ctx.move_to(-18, -110)
            ctx.line_to(18, -110)
            trazo(ctx, PIEL_OSC, 5)
        rrect(ctx, -150, -100, 300, 290, 90)          # palma
        rellena(ctx, PIEL, 8)
        ctx.move_to(-110, -10)
        ctx.curve_to(-40, 30, 40, 0, 120, -40)
        ctx.move_to(-120, 60)
        ctx.curve_to(-60, 20, 0, 40, 60, 10)
        ctx.move_to(-60, 160)
        ctx.curve_to(-90, 100, -100, 60, -100, 20)
        trazo(ctx, PIEL_OSC, 6)


def d_mano(ctx, t):
    fondo(ctx, t)
    s_ = pop(t, T_CONSERVO - 0.05, 0.4)
    mano_grande(ctx, 540, 900, 1.05 * s_, t, mueve=prog(t, T_MANO18 - 0.1, 0.3))
    sello(ctx, "INTACTA", 540, 300, 96, t, T_INTACTA - 0.05, rot=-6, col=VERDE_OSC)
    for k in range(4):
        destello(ctx, 540 + (k - 1.5) * 150, 520, 60, t, T_INTACTA + 0.05 * k, 0.5)


# ------------------------------------------------------------------ 9. cierre: vuelve el primer cuadro
def d_cierre(ctx, t):
    d_apertura(ctx, t - TOTAL)


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_apertura),
    (b(2) - 0.08, d_quirofano),
    (b(5) - 0.08, d_capas),
    (b(8) - 0.08, d_mapa),
    (b(14) - 0.08, d_londres),
    (b(15) - 0.08, d_mano_zona),
    (b(16) - 0.08, d_violin),
    (b(18) - 0.08, d_mano),
    (T_CIERRE, d_cierre),
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
    sin_punch = i == len(ESCENAS) - 1          # el cierre no lleva golpe de zoom: tiene que terminar igual al inicio
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
def s_nota(f=660.0, d=0.32):
    """Nota corta de cuerda (pizzicato suave)."""
    tt = np.arange(int(d * SR)) / SR
    x = sum(np.sin(TAU * f * h * tt) * (0.6 / h) for h in (1, 2, 3, 4))
    return (x * np.exp(-tt * 11) * np.minimum(1, tt / 0.004) * 0.5).astype(np.float32)


def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    # 1. apertura
    ev(0.0, "golpe", 0.6)
    ev(0.02, "pop", 0.35)
    for tl in LLEGA:
        ev(tl, "tick", 0.35, f=700, d=0.08)
    for t0, c, _ in GOLPES[1:]:
        ev(t0, "golpe", 0.4)
    for tt in TOQUES:
        ev(tt, "plop", 0.35)
    ev(T_DOLERIA - 0.05, "ding", 0.4)
    # 2. quirófano
    k = 0
    while T_POR + 0.3 + 0.85 * k < b(5) - 0.2:
        ev(T_POR + 0.3 + 0.85 * k, "tick", 0.12, f=1000, d=0.07)
        k += 1
    ev(T_OPERAN - 0.3, "clic", 0.35)
    ev(T_DESPIERTO - 0.05, "golpe", 0.55)
    ev(T_ABRE - 0.05, "pop", 0.45)
    ev(T_HABLA4 + 0.1, "pop", 0.45)
    ev(T_TRABAJAN, "clic", 0.35)
    # 3. capas
    ev(T_NO5 - 0.05, "clunk", 0.4)
    ev(T_ADENTRO - 0.2, "pop", 0.35)
    for j in range(11):
        ev(T_SENSORES - 0.1 + 0.05 * j, "tick", 0.2, f=1300 + 60 * j, d=0.03)
    ev(T_DOLOR5 - 0.1, "pop", 0.45)
    ev(T_SOLO - 0.1, "clic", 0.35)
    for td in T_DUERME:
        ev(td, "plop", 0.3)
    ev(T_DOLOR7 - 0.1, "golpe", 0.5)
    ev(T_ENVUELVE, "tick", 0.3, f=600, d=0.08)
    # 4. mapa
    ev(T_PARA8 - 0.05, "pop", 0.45)
    ev(T_CORTAR - 0.1, "clic", 0.35)
    ev(T_DEMAS + 0.15, "golpe", 0.5)
    ev(T_TUMOR10, "plop", 0.35)
    ev(T_ZONA10 - 0.1, "pop", 0.4)
    ev(T_MIENTRAS + 0.1, "pop", 0.4)
    ev(T_CIRUJANO - 0.2, "clic", 0.3)
    ev(T_BIEN - 0.05, "ding", 0.4)
    ev(T_TRABA - 0.05, "tick", 0.35, f=500, d=0.1)
    ev(T_DETIENE - 0.05, "clunk", 0.45)
    ev(T_POR13 - 0.05, "golpe", 0.6)
    # 5. Londres
    ev(T_EN14 - 0.05, "pop", 0.4)
    ev(T_LONDRES - 0.1, "pop", 0.35)
    ev(T_VIOLINISTA - 0.05, "nota", 0.5, f=660)
    # 6. zona de la mano
    ev(T_TUMOR15 - 0.1, "plop", 0.35)
    ev(T_ZONA15 - 0.1, "tick", 0.3, f=1400, d=0.05)
    ev(T_MANO15 - 0.1, "pop", 0.45)
    # 7. violín
    ev(T_DESPERTARON - 0.05, "golpe", 0.5)
    ev(T_DIERON - 0.2, "clic", 0.3)
    escala = (587, 659, 740, 784, 880, 784, 740, 659, 587, 659)
    for k, f in enumerate(escala):
        ev(T_TOCO + k * 0.22, "nota", 0.45, f=f)
    ev(T_SACABAN, "clic", 0.3)
    # 8. mano
    ev(T_CONSERVO - 0.05, "pop", 0.45)
    ev(T_INTACTA - 0.05, "golpe", 0.55)
    ev(T_INTACTA + 0.05, "ding", 0.4)
    # 9. cierre
    ev(T_CIERRE + 0.15, "pop", 0.3)
    return E


def pista_efectos():
    n = int((TOTAL + 3) * SR)
    mix = np.zeros(n, np.float32)
    for t, k, v, kw in eventos():
        x = (s_nota(**kw) if k == "nota" else K.snd(k, **kw)) * v
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "por_que_pueden_operarte_el_cerebro_despierto.mp4"))
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

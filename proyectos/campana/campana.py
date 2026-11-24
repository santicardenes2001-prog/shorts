"""Short "¿Por qué enterraban a los muertos con una campana?" — animación procedural (armazón de bostezo.py y mar.py).

Historia oscura: tono sobrio, sin caras ni personajes (V3). Fondo azul con puntos y subtítulos palabra por palabra
(V1). El hilo es el corte del cementerio: la campana arriba, el tubo con la cuerda y el ataúd abajo. El primer cuadro es
ese corte y el cierre vuelve a él para el loop.

    python proyectos/campana/campana.py --hoja 0,3,6      # hoja de fotogramas -> proyectos/campana/fotos/hoja.png
    python proyectos/campana/campana.py --probar
    python proyectos/campana/campana.py                   # render -> salidas/por_que_enterraban_con_campana.mp4
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
from picante import fondo_azul  # noqa: E402
from tierra import ROJO, VERDE, elipse, en, kartel, rellena, sale, sello, signo, tilde, trazo, zoom  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Hace unos 200 años, a algunos muertos los enterraban con una campana.",   # b0
    "Una cuerda bajaba desde la campana hasta su mano.",                        # b1
    "¿Para qué querría un muerto una campana?",                                 # b2
    "Por si no estaba muerto.",                                                 # b3
    "En las epidemias de cólera, enterraban rápido por miedo al contagio.",     # b4
    "A veces, sin distinguir al muerto del moribundo.",                         # b5
    "Los diarios contaban de ataúdes arañados por dentro.",                     # b6
    "El miedo creció tanto que se inventaron ataúdes de seguridad.",            # b7
    "Solo en Alemania se patentaron más de 30 modelos.",                        # b8
    "Algunos tenían un tubo para respirar.",                                    # b9
    "Otros levantaban una bandera si el cuerpo se movía.",                      # b10
    "Un médico quiso probar el suyo.",                                          # b11
    "Se hizo enterrar vivo durante varias horas.",                              # b12
    "Le pasaban sopa, cerveza y salchichas por un tubo.",                       # b13
    "Pero los inventos tenían un problema.",                                    # b14
    "Muchos ataban cuerdas a los brazos y las piernas.",                        # b15
    "Un cuerpo, al descomponerse, se hincha y se mueve.",                       # b16
    "La campana podía sonar sola.",                                             # b17
    "Desde arriba, nadie podía saber quién la tocaba.",                         # b18
    "Si un vivo… o un muerto.",                                                 # b19
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


# ------------------------------------------------------------------ colores (sobrios)
KF = 60 * round(14 * TOTAL / 60) / (14 * TOTAL)      # el fondo de puntos cierra justo en el loop
LUNA = hx("#F4F1DE")
PASTO = hx("#2E7D4F")
PASTO_OSC = hx("#1F5C39")
TIERRA = hx("#4A3326")
TIERRA2 = hx("#3B2A20")
TIERRA_FOSA = hx("#5A3D2C")
PIEDRA = hx("#8E97AB")
PIEDRA_OSC = hx("#626B80")
MADERA = hx("#8A5530")
MADERA_OSC = hx("#5E3720")
MADERA_IN = hx("#B07A4E")
BRONCE = hx("#E0AE4A")
BRONCE_OSC = hx("#A8741E")
SABANA = hx("#E9ECF4")
SABANA_SOM = hx("#BFC6D8")
MANO = hx("#E8D9C5")
CUERDA = hx("#D8C08A")
METAL = hx("#8F9AB2")
METAL_OSC = hx("#5D6880")
PLANO = hx("#1D4F9C")
PLANO_GRID = hx("#2F65B8")
LINEA = hx("#EAF3FF")
PAPEL = hx("#F1E7CF")
PAPEL_OSC = hx("#CDBF9E")
NEGRO = hx("#1A1A24")
ORO = hx("#FFC933")
SOPA = hx("#F0A04B")
CERVEZA = hx("#F5B83D")
SALCHICHA = hx("#C8553D")
LUZ = hx("#FFD27A")

SUELO = 760                     # línea del pasto en el corte del cementerio
TUBO_X = 800
CAMP = (800, 438)               # de dónde cuelga la campana
ATA = (220, 1062, 900, 1262)    # ataúd: x0, y0, x1, y1
MANO_P = (792, 1150)


# ------------------------------------------------------------------ ayudas
def fondo(ctx, t, oscuro=0.25):
    fondo_azul(ctx, t * KF)
    if oscuro > 0:
        ctx.set_source_rgba(0.02, 0.03, 0.08, oscuro)
        ctx.paint()


def cam(ctx, cx, cy, z):
    """Cámara: el punto (cx, cy) del mundo queda en (540, 880) de la pantalla, con zoom z."""
    ctx.translate(540, 880)
    ctx.scale(z, z)
    ctx.translate(-cx, -cy)


def mezcla_cam(a, b_, q):
    return tuple(lerp(x, y, q) for x, y in zip(a, b_))


def suave(t, t0, d=0.3):
    return ease(clamp((t - t0) / d), "inout")


def vaiven(t, t0, amp=0.5, f=1.6, caida=1.2, dur=None):
    """Ángulo de una campana que se sacude desde t0 y se va calmando."""
    if t < t0:
        return 0.0
    dt = t - t0
    if dur is not None and dt > dur:
        return 0.0
    a = amp * math.exp(-dt / caida) * math.sin(TAU * f * dt)
    if dur is not None:
        a *= 1 - ease(clamp((dt - dur + 0.4) / 0.4), "in")
    return a


def luna(ctx, x, y, r, t):
    for k in range(5, 0, -1):
        ctx.arc(x, y, r * (1 + 0.35 * k), 0, TAU)
        ctx.set_source_rgba(*LUNA, 0.035)
        ctx.fill()
    ctx.arc(x, y, r, 0, TAU)
    rellena(ctx, LUNA, 6)
    for dx, dy, rr in ((-20, -14, 14), (18, 16, 10), (10, -28, 7)):
        ctx.arc(x + dx, y + dy, rr, 0, TAU)
        ctx.set_source_rgba(*hx("#D8D3B8"), 1)
        ctx.fill()


def lapida(ctx, x, base, w=210, h=290, s=1.0, texto_=True):
    if s <= 0.01:
        return
    with en(ctx, x, base, s):
        ctx.move_to(-w / 2, 0)
        ctx.line_to(-w / 2, -h + w / 2)
        ctx.arc(0, -h + w / 2, w / 2, math.pi, TAU)
        ctx.line_to(w / 2, 0)
        ctx.close_path()
        rellena(ctx, PIEDRA, 8)
        ctx.move_to(-w / 2 + 20, -h + w / 2)
        ctx.arc(0, -h + w / 2, w / 2 - 20, math.pi, TAU)
        trazo(ctx, PIEDRA_OSC, 5)
        if texto_:
            texto(ctx, "R.I.P.", 0, -h + 130, 46, fill=PIEDRA_OSC, stroke=None)
        ctx.move_to(w / 2 - 50, -h + 60)
        ctx.line_to(w / 2 - 70, -h + 100)
        ctx.line_to(w / 2 - 56, -h + 130)
        trazo(ctx, PIEDRA_OSC, 4)


def campana(ctx, x, y, s=1.0, ang=0.0, ring=0.0, t=0.0, linea=False):
    """Campana colgada de (x, y); ang = vaivén; ring = 0..1 ondas de sonido."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s, ang):
        if linea:
            ctx.move_to(-26, 6)
            ctx.curve_to(-30, 30, -40, 70, -58, 92)
            ctx.line_to(58, 92)
            ctx.curve_to(40, 70, 30, 30, 26, 6)
            ctx.close_path()
            trazo(ctx, LINEA, 6)
            ctx.arc(-ang * 20, 104, 10, 0, TAU)
            trazo(ctx, LINEA, 5)
        else:
            rrect(ctx, -16, -10, 32, 18, 6)
            rellena(ctx, MADERA_OSC, 6)
            ctx.arc(-ang * 22, 102, 12, 0, TAU)
            rellena(ctx, BRONCE_OSC, 5)
            ctx.move_to(-26, 6)
            ctx.curve_to(-30, 30, -40, 70, -58, 92)
            ctx.line_to(58, 92)
            ctx.curve_to(40, 70, 30, 30, 26, 6)
            ctx.close_path()
            rellena(ctx, BRONCE, 7)
            elipse(ctx, 0, 92, 60, 9)
            rellena(ctx, BRONCE_OSC, 6)
            ctx.move_to(-14, 20)
            ctx.curve_to(-18, 40, -24, 60, -34, 78)
            trazo(ctx, hx("#FFE3A3"), 6, 0.8)
    if ring > 0.01:
        col = LINEA if linea else BLANCO
        for j in range(3):
            q = (t * 2.2 + j / 3) % 1.0
            r = s * (85 + 90 * q)
            a = ring * (1 - q)
            for a0 in (-0.55, math.pi - 0.55):
                ctx.new_sub_path()
                ctx.arc(x, y + 55 * s, r, a0, a0 + 1.1)
            trazo(ctx, col, 7 * s, a)


def poste(ctx, x, base, top, brazo_x):
    rrect(ctx, x - 12, top, 24, base - top + 10, 6)
    rellena(ctx, MADERA_OSC, 6)
    rrect(ctx, x - 12, top - 4, brazo_x - x + 30, 20, 6)
    rellena(ctx, MADERA_OSC, 6)


def monticulo(ctx, x0, x1, y, h=34):
    ctx.move_to(x0, y + 4)
    ctx.curve_to(x0 + 80, y - h, x1 - 80, y - h, x1, y + 4)
    ctx.close_path()
    rellena(ctx, TIERRA_FOSA, 6)


def pasto(ctx, x0, x1, y, t):
    ctx.rectangle(x0, y - 10, x1 - x0, 22)
    ctx.set_source_rgb(*PASTO)
    ctx.fill()
    for i, x in enumerate(range(int(x0), int(x1), 26)):
        sw = 4 * math.sin(t * 2.0 + x * 0.05)
        hh = 16 + (i * 7) % 11
        ctx.move_to(x - 7, y - 6)
        ctx.line_to(x + sw, y - 6 - hh)
        ctx.line_to(x + 7, y - 6)
        ctx.close_path()
        ctx.set_source_rgb(*(PASTO if i % 2 else PASTO_OSC))
        ctx.fill()


def suelo(ctx, y, x0=-400, x1=1480, y1=2600, fosa=None):
    ctx.rectangle(x0, y, x1 - x0, y1 - y)
    ctx.set_source_rgb(*TIERRA)
    ctx.fill()
    for k, yy in enumerate((y + 120, y + 260, y + 600, y + 760)):
        ctx.move_to(x0, yy)
        for x in range(int(x0), int(x1) + 60, 60):
            ctx.line_to(x, yy + 10 * math.sin(x * 0.02 + k))
        trazo(ctx, TIERRA2, 10)
    rnd = random.Random(7)
    for _ in range(26):
        px, py = rnd.uniform(x0 + 300, x1 - 300), rnd.uniform(y + 40, y + 820)
        if fosa and fosa[0] - 20 < px < fosa[2] + 20 and py < fosa[3] + 20:
            continue
        elipse(ctx, px, py, rnd.uniform(8, 16), rnd.uniform(6, 11))
        ctx.set_source_rgb(*TIERRA2)
        ctx.fill()
    if fosa:
        rrect(ctx, fosa[0], y, fosa[2] - fosa[0], fosa[3] - y, 16)
        ctx.set_source_rgb(*TIERRA_FOSA)
        ctx.fill()
    # el piso se oscurece hacia abajo
    g = cairo.LinearGradient(0, y + 680, 0, y + 900)
    g.add_color_stop_rgba(0, 0.02, 0.02, 0.05, 0.0)
    g.add_color_stop_rgba(1, 0.02, 0.02, 0.05, 0.75)
    ctx.rectangle(x0, y + 680, x1 - x0, y1 - y)
    ctx.set_source(g)
    ctx.fill()


def ataud_hex(ctx, x, y, L=260, A=110, rot=0.0):
    """Ataúd visto desde arriba: la forma clásica de seis lados."""
    with en(ctx, x, y, 1.0, rot):
        pts = [(-L / 2, -0.3 * A), (-L / 2 + 0.28 * L, -0.5 * A), (L / 2, -0.24 * A),
               (L / 2, 0.24 * A), (-L / 2 + 0.28 * L, 0.5 * A), (-L / 2, 0.3 * A)]
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        rellena(ctx, MADERA, 8)
        k = 0.78
        ctx.move_to(pts[0][0] * k, pts[0][1] * k)
        for p in pts[1:]:
            ctx.line_to(p[0] * k, p[1] * k)
        ctx.close_path()
        trazo(ctx, MADERA_OSC, 5)


def ataud(ctx, x0, y0, x1, y1, interior=True):
    rrect(ctx, x0, y0, x1 - x0, y1 - y0, 18)
    rellena(ctx, MADERA, 9)
    if interior:
        rrect(ctx, x0 + 20, y0 + 22, x1 - x0 - 40, y1 - y0 - 40, 10)
        ctx.set_source_rgb(*MADERA_IN)
        ctx.fill()
        ctx.move_to(x0 + 20, y0 + 22)
        ctx.line_to(x1 - 20, y0 + 22)
        trazo(ctx, MADERA_OSC, 8)
    ctx.move_to(x0 - 8, y0 + 4)
    ctx.line_to(x1 + 8, y0 + 4)
    trazo(ctx, MADERA_OSC, 14)


def sabana(ctx, x0, y0, x1, y1, infla=0.0):
    """Cuerpo tapado con una sábana dentro del ataúd (sin cara)."""
    ctx.save()
    rrect(ctx, x0 + 20, y0 + 22, x1 - x0 - 40, y1 - y0 - 40, 10)
    ctx.clip()
    elipse(ctx, x0 + 80, y1 - 52, 50, 26)
    rellena(ctx, hx("#D8DCE8"), 5)
    hy = y1 - 40
    ctx.move_to(x0 + 60, hy)
    ctx.curve_to(x0 + 60, hy - 120 - 20 * infla, x0 + 150, hy - 120 - 20 * infla, x0 + 170, hy - 70)
    ctx.curve_to(x0 + 260, hy - 90 - 30 * infla, x1 - 160, hy - 95 - 40 * infla, x1 - 80, hy - 50)
    ctx.curve_to(x1 - 50, hy - 40, x1 - 40, hy, x1 - 40, hy + 8)
    ctx.line_to(x0 + 50, hy + 8)
    ctx.close_path()
    rellena(ctx, SABANA, 6)
    for k in range(3):
        xx = x0 + 260 + 120 * k
        ctx.move_to(xx, hy - 70)
        ctx.curve_to(xx + 20, hy - 40, xx + 10, hy - 20, xx + 30, hy)
        trazo(ctx, SABANA_SOM, 5)
    ctx.restore()


def mano(ctx, x, y, s=1.0, dedo=0.0, glow=0.0):
    """Mano que sale de la sábana y agarra la cuerda; dedo = 0..1 (se levanta el índice)."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        if glow > 0.01:
            for k in range(4, 0, -1):
                ctx.arc(0, 0, 40 + 18 * k, 0, TAU)
                ctx.set_source_rgba(*LUZ, 0.08 * glow)
                ctx.fill()
        rrect(ctx, -46, 18, 40, 40, 14)
        rellena(ctx, SABANA, 5)
        with en(ctx, -10, -26, 1.0, -0.9 * dedo):
            rrect(ctx, -8, -46, 18, 50, 9)
            rellena(ctx, MANO, 5)
        rrect(ctx, -30, -24, 56, 50, 20)
        rellena(ctx, MANO, 6)
        for k in range(3):
            ctx.move_to(-22 + 14 * k, -20)
            ctx.line_to(-22 + 14 * k, -6)
            trazo(ctx, hx("#BFAE96"), 4)
        elipse(ctx, 26, 6, 12, 18)
        rellena(ctx, MANO, 5)


def cuerda(ctx, x, y0, y1, glow=0.0, tension=0.0):
    ctx.move_to(x, y0)
    ctx.line_to(x, y1)
    trazo(ctx, INK, 12)
    ctx.move_to(x, y0)
    ctx.line_to(x, y1)
    trazo(ctx, CUERDA, 6)
    if glow > 0.01:
        yy = lerp(y0, y1, clamp(glow))
        ctx.move_to(x, y0)
        ctx.line_to(x, yy)
        trazo(ctx, ORO, 9)
        ctx.arc(x, yy, 14, 0, TAU)
        ctx.set_source_rgba(*ORO, 0.9)
        ctx.fill()


def tubo(ctx, x, top, bot, w=40, glow=0.0):
    rrect(ctx, x - w / 2, top, w, bot - top, 8)
    rellena(ctx, METAL, 7)
    rrect(ctx, x - w / 2 - 8, top - 10, w + 16, 22, 6)
    rellena(ctx, METAL_OSC, 6)
    if glow > 0.01:
        rrect(ctx, x - w / 2, top, w, bot - top, 8)
        trazo(ctx, ORO, 8, glow)


def reloj(ctx, x, y, R, ang, s=1.0):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.arc(0, 0, R, 0, TAU)
        rellena(ctx, PAPEL, 8)
        for k in range(12):
            a = k * TAU / 12
            ctx.move_to(0.8 * R * math.cos(a), 0.8 * R * math.sin(a))
            ctx.line_to(0.9 * R * math.cos(a), 0.9 * R * math.sin(a))
            trazo(ctx, INK, 5)
        for L, a, w in ((0.5, ang / 12, 9), (0.75, ang, 6)):
            ctx.move_to(0, 0)
            ctx.line_to(L * R * math.sin(a), -L * R * math.cos(a))
            trazo(ctx, INK, w)
        ctx.arc(0, 0, 8, 0, TAU)
        ctx.set_source_rgb(*INK)
        ctx.fill()


def plano_hoja(ctx, x0, y0, x1, y1, titulo=None, a_tit=1.0):
    rrect(ctx, x0, y0, x1 - x0, y1 - y0, 18)
    rellena(ctx, PLANO, 9)
    ctx.save()
    rrect(ctx, x0, y0, x1 - x0, y1 - y0, 18)
    ctx.clip()
    for xx in range(int(x0) + 40, int(x1), 40):
        ctx.move_to(xx, y0)
        ctx.line_to(xx, y1)
    for yy in range(int(y0) + 40, int(y1), 40):
        ctx.move_to(x0, yy)
        ctx.line_to(x1, yy)
    trazo(ctx, PLANO_GRID, 2)
    ctx.restore()
    rrect(ctx, x0 + 18, y0 + 18, x1 - x0 - 36, y1 - y0 - 36, 10)
    trazo(ctx, LINEA, 3, 0.6)
    if titulo and a_tit > 0.01:
        ctx.save()
        ctx.push_group()
        texto(ctx, titulo, (x0 + x1) / 2, y0 + 70, 50, fill=LINEA, stroke=None)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a_tit)
        ctx.restore()


def revela(ctx, x0, x1, q):
    """Recorta a la izquierda de lerp(x0, x1, q): efecto de dibujo que avanza."""
    ctx.rectangle(-2000, -2000, lerp(x0, x1, q) + 2000, 6000)
    ctx.clip()


def cota(ctx, x0, y, x1, a=1.0):
    ctx.move_to(x0, y)
    ctx.line_to(x1, y)
    for xx, sg in ((x0, 1), (x1, -1)):
        ctx.move_to(xx + sg * 16, y - 10)
        ctx.line_to(xx, y)
        ctx.line_to(xx + sg * 16, y + 10)
    trazo(ctx, LINEA, 3, a)


# ================================================================== el corte del cementerio
def cementerio(ctx, t, ang=0.0, ring=0.0, glow_cuerda=0.0, dedo=0.0, glow_mano=0.0, cuerda_on=True,
               camp_on=True, extra=None, cartel_rip=True):
    """Cielo con luna, lápida, poste con campana, tubo hasta el ataúd y el cuerpo con la mano en la cuerda."""
    luna(ctx, 880, 250, 64, t)
    suelo(ctx, SUELO, fosa=(ATA[0] - 30, 0, ATA[2] + 30, ATA[3] + 30))
    lapida(ctx, 330, SUELO + 6, texto_=cartel_rip)
    if camp_on:
        poste(ctx, 700, SUELO, CAMP[1] - 10, CAMP[0])
    monticulo(ctx, 230, 890, SUELO)
    pasto(ctx, -400, 1480, SUELO, t)
    if camp_on:
        tubo(ctx, TUBO_X, SUELO - 70, ATA[1] + 14)
    ataud(ctx, *ATA)
    sabana(ctx, *ATA)
    if cuerda_on:
        cuerda(ctx, TUBO_X, CAMP[1] + 100, MANO_P[1] - 20, glow_cuerda)
        mano(ctx, MANO_P[0], MANO_P[1], 1.0, dedo, glow_mano)
    if extra:
        extra(ctx)
    if camp_on:
        campana(ctx, CAMP[0], CAMP[1], 1.0, ang, ring, t)


# ------------------------------------------------------------------ 1. apertura (y cierre del loop)
T_200 = b(0, "200")
T_UNA1 = b(1)
T_CUERDA1 = b(1, "cuerda")
T_MANO1 = b(1, "mano")
CAM0 = (565, 850, 1.13)
CAM_MANO = (700, 1040, 1.22)


def d_apertura(ctx, u):
    fondo(ctx, u % TOTAL)
    if u >= 0:
        q1 = suave(u, T_UNA1 - 0.1, T_MANO1 - T_UNA1 + 0.3)
        c = mezcla_cam(CAM0, CAM_MANO, q1)
        c = (c[0], c[1], c[2] * lerp(1.0, 1.04, clamp(u / T_UNA1)))
        glow = prog(u, T_CUERDA1 - 0.1, T_MANO1 - T_CUERDA1 + 0.1, "inout")
        gm = prog(u, T_MANO1 - 0.05, 0.25) * (0.75 + 0.25 * math.sin(u * 8))
        ang = 0.0
    else:
        uc = u + TOTAL
        q = suave(uc, b(19) - 0.1, TOTAL - 0.35 - b(19))
        c = mezcla_cam((660, 960, 1.22), CAM0, q)
        glow, gm = 0.0, 0.0
        ang = vaiven(uc, b(19, "vivo") - 0.1, 0.22, 1.4, 0.45, dur=TOTAL - 0.35 - b(19, "vivo"))
    ctx.save()
    cam(ctx, *c)
    cementerio(ctx, u % TOTAL, ang=ang, glow_cuerda=glow, glow_mano=gm)
    ctx.restore()
    if u >= 0:
        kartel(ctx, "HACE 200 AÑOS", 540, 200, 76, u, T_200 - 0.05, T_UNA1)


def d_cierre(ctx, t):
    d_apertura(ctx, t - TOTAL)


# ------------------------------------------------------------------ 2. ¿para qué querría un muerto una campana?
T_PARA = b(2)
T_CAMPANA2 = b(2, "campana")


def d_pregunta(ctx, t):
    fondo(ctx, t)
    q = suave(t, T_PARA - 0.05, 0.9)
    c = mezcla_cam(CAM_MANO, (CAMP[0] - 40, CAMP[1] + 120, 1.75), q)
    ctx.save()
    cam(ctx, *c)
    cementerio(ctx, t, ang=0.03 * math.sin(t * 2.2))
    ctx.restore()
    signo(ctx, "?", 260, 560, 230, t, T_CAMPANA2 - 0.1, col=LUZ)
    signo(ctx, "?", 860, 1120, 170, t, T_CAMPANA2 + 0.1, col=LUZ)


# ------------------------------------------------------------------ 3. por si no estaba muerto (corte seco)
T_POR3 = b(3)
T_NO3 = b(3, "no")
T_ESTABA = b(3, "estaba")
T_MUERTO3 = b(3, "muerto")


def d_porsi(ctx, t):
    fondo(ctx, t)
    dedo = ease(clamp((t - T_NO3 + 0.1) / 0.2), "out")
    tiron = prog(t, T_NO3, 0.15)
    q = suave(t, T_ESTABA - 0.1, T_MUERTO3 - T_ESTABA + 0.05)
    c = mezcla_cam((MANO_P[0] - 20, MANO_P[1] - 40, 2.3), (CAMP[0] - 40, CAMP[1] + 140, 1.6), q)
    ang = vaiven(t, T_MUERTO3 - 0.05, 0.55, 1.7, 0.9)
    ring = prog(t, T_MUERTO3 - 0.05, 0.1)
    ctx.save()
    cam(ctx, *c)
    cementerio(ctx, t, ang=ang, ring=ring, dedo=dedo, glow_mano=0.6 * dedo, glow_cuerda=tiron * (1 - q))
    ctx.restore()
    # estela de la panorámica rápida
    if 0.05 < q < 0.95:
        ctx.set_source_rgba(0.02, 0.03, 0.08, 0.35 * math.sin(math.pi * q))
        ctx.paint()


# ------------------------------------------------------------------ 4. epidemias de cólera: enterraban rápido
T_EPIDEMIAS = b(4, "epidemias")
T_COLERA = b(4, "colera")
T_ENTERRABAN = b(4, "enterraban")
T_RAPIDO = b(4, "rapido")
T_MIEDO4 = b(4, "miedo")
POZOS = [180, 540, 900]
SUELO4 = 1020


def d_colera(ctx, t):
    fondo(ctx, t)
    t0 = b(4)
    suelo(ctx, SUELO4)
    pasto(ctx, -400, 1480, SUELO4, t)
    for j, x in enumerate(POZOS):
        ctx.rectangle(x - 135, SUELO4 - 6, 270, 190)
        ctx.set_source_rgb(*TIERRA2)
        ctx.fill()
    for j, x in enumerate(POZOS):
        t_cae = T_ENTERRABAN - 0.1 + 0.32 * j
        q = clamp((t - t_cae) / 0.35)
        if t < t_cae - 0.6:
            continue
        y = lerp(640, SUELO4 + 60, ease(q, "in")) - (12 * math.sin(math.pi * clamp((t - t_cae - 0.35) / 0.2)) if q >= 1 else 0)
        rot = (1 - q) * (0.35 if j % 2 else -0.35)
        ataud_hex(ctx, x, y, 250, 110, rot)
        # tierra que tapa
        tapa = prog(t, t_cae + 0.45, 0.4, "out")
        if tapa > 0.01:
            monticulo(ctx, x - 140, x + 140, SUELO4 + 4, 46 * tapa)
            ctx.rectangle(x - 135, SUELO4 + 4, 270, 186 * tapa)
            ctx.set_source_rgb(*TIERRA_FOSA)
            ctx.fill()
    reloj(ctx, 820, 470, 120, (t - T_RAPIDO) * 22 if t > T_RAPIDO else 0, pop(t, T_RAPIDO - 0.15, 0.3))
    sello(ctx, "CÓLERA", 330, 430, 100, t, T_COLERA - 0.05, rot=-7)
    kartel(ctx, "MIEDO AL CONTAGIO", 540, 760, 54, t, T_MIEDO4 - 0.05)


# ------------------------------------------------------------------ 5. sin distinguir al muerto del moribundo
T_A5 = b(5)
T_DISTINGUIR = b(5, "distinguir")
T_MUERTO5 = b(5, "muerto")
T_MORIBUNDO = b(5, "moribundo")


def camilla(ctx, x, y, s, t, latido, a=1.0):
    with en(ctx, x, y, s):
        rrect(ctx, -330, 40, 660, 26, 10)
        rellena(ctx, METAL_OSC, 6)
        for xx in (-300, 300):
            ctx.move_to(xx, 66)
            ctx.line_to(xx, 130)
            trazo(ctx, METAL_OSC, 12)
        sabana(ctx, -340, -120, 340, 80)
        # línea del pulso (casi igual en los dos)
        ctx.move_to(-300, -190)
        for k in range(0, 61):
            xx = -300 + 10 * k
            fase = (xx / 600 + t * 0.6) % 1.0
            yy = -190
            if latido and 0.48 < fase < 0.52:
                yy -= 26 * math.sin((fase - 0.48) / 0.04 * math.pi)
            ctx.line_to(xx, yy)
        trazo(ctx, VERDE if latido else hx("#7C8AA5"), 6, a)


def d_distinguir(ctx, t):
    fondo(ctx, t)
    s1 = pop(t, T_A5 - 0.05, 0.4)
    s2 = pop(t, T_A5 + 0.1, 0.4)
    if s1 > 0.01:
        camilla(ctx, 540, 720, 1.05 * s1, t, False)
    if s2 > 0.01:
        camilla(ctx, 540, 1150, 1.05 * s2, t, True)
    kartel(ctx, "MUERTO", 540, 500, 60, t, T_MUERTO5 - 0.05)
    kartel(ctx, "MORIBUNDO", 540, 935, 60, t, T_MORIBUNDO - 0.05)
    signo(ctx, "?", 960, 935, 200, t, T_DISTINGUIR - 0.05, col=LUZ)


# ------------------------------------------------------------------ 6. los diarios: ataúdes arañados por dentro
T_DIARIOS = b(6, "diarios")
T_ATAUDES6 = b(6, "ataudes")
T_ARANADOS = b(6, "aranados")
T_DENTRO = b(6, "dentro")
DIARIO = (540, 860)
CAJA = (540, 980)
RASGU = [(-150, -60, -100, 90), (-80, -80, -30, 80), (10, -70, 60, 100), (90, -90, 140, 70)]


def d_diario(ctx, t):
    fondo(ctx, t)
    p = prog(t, T_DIARIOS - 0.2, 0.6, "out")
    zq = suave(t, T_ARANADOS - 0.25, 0.7)
    ctx.save()
    cx, cy, z = mezcla_cam((DIARIO[0], DIARIO[1] + 20, 1.0), (CAJA[0], CAJA[1] - 60, 1.45), zq)
    cam(ctx, cx, cy, z)
    with en(ctx, DIARIO[0], DIARIO[1], max(p, 0.02), (1 - p) * 2.5 * TAU):
        rrect(ctx, -380, -500, 760, 1000, 10)
        rellena(ctx, PAPEL, 9)
        texto(ctx, "LA GACETA", 0, -420, 70, fill=INK, stroke=None)
        ctx.move_to(-340, -370)
        ctx.line_to(340, -370)
        trazo(ctx, INK, 5)
        texto(ctx, "¡ENTERRADO", 0, -290, 92, fill=INK, stroke=None)
        texto(ctx, "VIVO!", 0, -195, 92, fill=ROJO, stroke=None)
        for k in range(2):
            ctx.move_to(-340, 300 + 40 * k)
            ctx.line_to(340, 300 + 40 * k)
            trazo(ctx, PAPEL_OSC, 12)
        for k in range(3):
            ctx.move_to(-340, 400 + 40 * k)
            ctx.line_to(-20, 400 + 40 * k)
            ctx.move_to(20, 400 + 40 * k)
            ctx.line_to(340, 400 + 40 * k)
            trazo(ctx, PAPEL_OSC, 12)
        # el grabado: la tapa del ataúd por dentro
        with en(ctx, CAJA[0] - DIARIO[0], CAJA[1] - DIARIO[1], 1.0):
            rrect(ctx, -280, -170, 560, 340, 8)
            rellena(ctx, MADERA_OSC, 7)
            for k in range(6):
                ctx.move_to(-260, -140 + 56 * k)
                ctx.curve_to(-80, -150 + 56 * k, 80, -130 + 56 * k, 260, -140 + 56 * k)
                trazo(ctx, MADERA, 5)
            for j, (x0, y0, x1, y1) in enumerate(RASGU):
                q = prog(t, T_ARANADOS - 0.05 + 0.2 * j, 0.22, "out")
                if q <= 0.01:
                    continue
                for k in range(3):
                    dx = 14 * k
                    ctx.move_to(x0 + dx, y0)
                    ctx.line_to(lerp(x0, x1, q) + dx, lerp(y0, y1, q))
                trazo(ctx, hx("#E8CDAA"), 6)
    ctx.restore()


# ------------------------------------------------------------------ 7. el miedo creció: ataúdes de seguridad
T_MIEDO7 = b(7, "miedo")
T_CRECIO = b(7, "crecio")
T_INVENTARON = b(7, "inventaron")
T_ATAUDES7 = b(7, "ataudes")
T_SEGURIDAD = b(7, "seguridad")
HOJA7 = (110, 500, 970, 1320)


def dibujo_ataud_seguridad(ctx, cx, cy, s, q, t, ang=0.0, ring=0.0):
    """El plano: suelo punteado, ataúd, tubo, cuerda y campana, en líneas blancas."""
    with en(ctx, cx, cy, s):
        ctx.save()
        revela(ctx, -380, 380, q)
        ctx.set_dash([18, 12])
        ctx.move_to(-380, -40)
        ctx.line_to(380, -40)
        trazo(ctx, LINEA, 4)
        ctx.set_dash([])
        rrect(ctx, -300, 120, 520, 150, 12)
        trazo(ctx, LINEA, 6)
        ctx.move_to(-300, 150)
        ctx.line_to(220, 150)
        trazo(ctx, LINEA, 3)
        rrect(ctx, 130, -150, 34, 270, 6)
        trazo(ctx, LINEA, 5)
        ctx.move_to(147, -260)
        ctx.line_to(147, 200)
        trazo(ctx, LINEA, 3)
        ctx.move_to(70, -300)
        ctx.line_to(70, -40)
        ctx.move_to(70, -300)
        ctx.line_to(150, -300)
        trazo(ctx, LINEA, 6)
        cota(ctx, -300, 310, 220)
        texto(ctx, "FIG. 1", -250, -230, 34, fill=LINEA, stroke=None)
        ctx.restore()
    if q > 0.85:
        campana(ctx, cx + 147 * s, cy - 300 * s, 0.85 * s, ang, ring, t, linea=True)


def d_plano(ctx, t):
    fondo(ctx, t)
    t0 = b(7)
    # el miedo: un termómetro que se llena
    sale_m = prog(t, T_INVENTARON - 0.2, 0.35, "in")
    s_m = pop(t, t0 - 0.05, 0.35)
    if s_m > 0.01 and sale_m < 1:
        with en(ctx, 540 - 900 * sale_m, 860, s_m):
            rrect(ctx, -60, -380, 120, 640, 60)
            rellena(ctx, PAPEL, 9)
            ctx.arc(0, 290, 100, 0, TAU)
            rellena(ctx, ROJO, 9)
            f = prog(t, T_MIEDO7 - 0.05, T_INVENTARON - T_MIEDO7, "inout")
            rrect(ctx, -32, 260 - 600 * f, 64, 600 * f + 30, 30)
            ctx.set_source_rgb(*ROJO)
            ctx.fill()
            for k in range(6):
                ctx.move_to(60, 220 - 100 * k)
                ctx.line_to(95, 220 - 100 * k)
                trazo(ctx, BLANCO, 6)
        kartel(ctx, "MIEDO", 540 - 900 * sale_m, 380, 70, t, T_MIEDO7 - 0.05)
    # el plano
    p = prog(t, T_INVENTARON - 0.15, 0.45, "out")
    if p > 0.01:
        with en(ctx, 540 + 700 * (1 - p), 0, 1.0):
            ctx.translate(-540, 0)
            plano_hoja(ctx, *HOJA7, titulo="ATAÚD DE SEGURIDAD", a_tit=prog(t, T_ATAUDES7 - 0.1, 0.3))
            q = prog(t, T_INVENTARON + 0.1, T_SEGURIDAD - T_INVENTARON + 0.2, "inout")
            dibujo_ataud_seguridad(ctx, 560, 990, 1.12, q, t)


# ------------------------------------------------------------------ 8. Alemania: más de 30 patentes
T_ALEMANIA = b(8, "alemania")
T_PATENTARON = b(8, "patentaron")
T_30 = b(8, "30")
GRID = [(190 + 140 * c, 560 + 152 * f) for f in range(6) for c in range(6)]


def mini_plano(ctx, x, y, s, j):
    with en(ctx, x, y, s, (j % 5 - 2) * 0.03):
        rrect(ctx, -58, -66, 116, 132, 8)
        rellena(ctx, PLANO, 5)
        rrect(ctx, -40, 14, 80, 30, 4)
        trazo(ctx, LINEA, 3)
        v = j % 3
        if v == 0:
            ctx.move_to(24, 14)
            ctx.line_to(24, -40)
            trazo(ctx, LINEA, 3)
            elipse(ctx, 24, -44, 12, 8)
            trazo(ctx, LINEA, 3)
        elif v == 1:
            ctx.move_to(-10, 14)
            ctx.line_to(-10, -50)
            ctx.line_to(16, -42)
            ctx.line_to(-10, -34)
            trazo(ctx, LINEA, 3)
        else:
            rrect(ctx, 14, -46, 12, 60, 3)
            trazo(ctx, LINEA, 3)
        ctx.move_to(-48, -2)
        ctx.line_to(48, -2)
        ctx.set_dash([6, 5])
        trazo(ctx, LINEA, 2)
        ctx.set_dash([])


def d_patentes(ctx, t):
    fondo(ctx, t)
    s = pop(t, T_ALEMANIA - 0.1, 0.4)
    if s > 0.01:
        with en(ctx, 540, 360, s):
            for k, col in enumerate((NEGRO, ROJO, ORO)):
                rrect(ctx, -170, 40 + 22 * k, 340, 22, 4 if k in (0, 2) else 0)
                ctx.set_source_rgb(*col)
                ctx.fill()
            rrect(ctx, -170, 40, 340, 66, 6)
            trazo(ctx, INK, 6)
        kartel(ctx, "ALEMANIA", 540, 330, 72, t, T_ALEMANIA - 0.1)
    n = len(GRID)
    for j, (x, y) in enumerate(GRID):
        tj = T_PATENTARON - 0.1 + (T_30 - T_PATENTARON + 0.05) * j / n
        sj = pop(t, tj, 0.25)
        if sj > 0.01:
            mini_plano(ctx, x, y, sj, j)
    sello(ctx, "MÁS DE 30", 540, 940, 120, t, T_30 - 0.05, rot=-8)


# ------------------------------------------------------------------ 9. un tubo para respirar / una bandera si se movía
T_ALGUNOS = b(9)
T_TUBO9 = b(9, "tubo")
T_RESPIRAR = b(9, "respirar")
T_OTROS = b(10)
T_BANDERA = b(10, "bandera")
T_MOVIA = b(10, "movia")
CAM9 = (660, 920, 1.18)


def flechas_aire(ctx, x, top, bot, t, a):
    if a <= 0.01:
        return
    for k in range(4):
        q = (t * 0.9 + k / 4) % 1.0
        y = lerp(top + 20, bot - 30, q)
        ctx.move_to(x - 12, y - 10)
        ctx.line_to(x, y + 4)
        ctx.line_to(x + 12, y - 10)
        trazo(ctx, BLANCO, 6, a * math.sin(math.pi * q))


def d_tubo(ctx, t):
    fondo(ctx, t)
    bandera_on = t >= T_OTROS - 0.05
    dedo = ease(clamp((t - T_MOVIA + 0.05) / 0.2), "out") if bandera_on else 0.0
    sube = prog(t, T_MOVIA + 0.05, 0.35, "out")

    def extra(c):
        top = SUELO - 70
        if not bandera_on:
            tubo(c, TUBO_X, top, ATA[1] + 14, w=44, glow=prog(t, T_TUBO9 - 0.1, 0.25) * sale(t, T_OTROS - 0.1))
            flechas_aire(c, TUBO_X, top, ATA[1], t, prog(t, T_RESPIRAR - 0.2, 0.3))
        else:
            tubo(c, TUBO_X, top, ATA[1] + 14, w=44)
            # varilla que sube cuando la mano se mueve
            y_top = top - 30 - 170 * sube
            c.move_to(TUBO_X, MANO_P[1] - 40)
            c.line_to(TUBO_X, y_top)
            trazo(c, INK, 12)
            c.move_to(TUBO_X, MANO_P[1] - 40)
            c.line_to(TUBO_X, y_top)
            trazo(c, METAL_OSC, 6)
            ab = prog(t, T_MOVIA + 0.25, 0.3, "out")
            ond = 10 * math.sin(t * 9)
            c.move_to(TUBO_X + 4, y_top)
            if ab > 0.01:
                c.curve_to(TUBO_X + 60 * ab, y_top - 20 + ond, TUBO_X + 110 * ab, y_top + 20 - ond,
                           TUBO_X + 160 * ab, y_top + 4)
                c.line_to(TUBO_X + 160 * ab, y_top + 74)
                c.curve_to(TUBO_X + 110 * ab, y_top + 90 - ond, TUBO_X + 60 * ab, y_top + 50 + ond, TUBO_X + 4,
                           y_top + 70)
            else:
                c.line_to(TUBO_X + 22, y_top + 10)
                c.line_to(TUBO_X + 22, y_top + 60)
                c.line_to(TUBO_X + 4, y_top + 70)
            c.close_path()
            rellena(c, ROJO, 6)
        mano(c, MANO_P[0], MANO_P[1], 1.0, dedo, 0.7 * dedo)

    ctx.save()
    cam(ctx, *CAM9)
    cementerio(ctx, t, cuerda_on=False, camp_on=False, extra=extra)
    ctx.restore()
    if not bandera_on:
        kartel(ctx, "PARA RESPIRAR", 540, 300, 64, t, T_RESPIRAR - 0.1)
    else:
        kartel(ctx, "SI SE MOVÍA", 540, 300, 64, t, T_MOVIA - 0.05)


# ------------------------------------------------------------------ 10. un médico quiso probar el suyo
T_MEDICO = b(11, "medico")
T_PROBAR = b(11, "probar")
T_SUYO = b(11, "suyo")


def maletin(ctx, x, y, s):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.move_to(-60, -110)
        ctx.curve_to(-60, -170, 60, -170, 60, -110)
        trazo(ctx, INK, 30)
        ctx.move_to(-60, -110)
        ctx.curve_to(-60, -170, 60, -170, 60, -110)
        trazo(ctx, NEGRO, 16)
        rrect(ctx, -200, -120, 400, 260, 50)
        rellena(ctx, NEGRO, 9)
        ctx.move_to(-200, -40)
        ctx.line_to(200, -40)
        trazo(ctx, hx("#3A3A4A"), 8)
        rrect(ctx, -26, -20, 52, 120, 6)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()
        rrect(ctx, -60, 14, 120, 52, 6)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()


def d_medico(ctx, t):
    fondo(ctx, t)
    s = pop(t, T_MEDICO - 0.15, 0.4)
    mover = suave(t, T_PROBAR - 0.1, 0.4)
    maletin(ctx, lerp(540, 300, mover), lerp(860, 900, mover), 1.1 * s)
    kartel(ctx, "MÉDICO", lerp(540, 300, mover), 620, 64, t, T_MEDICO - 0.1)
    sp = prog(t, T_PROBAR - 0.05, 0.4, "out")
    if sp > 0.01:
        with en(ctx, 780, 880, 0.55 * sp, 0.05):
            plano_hoja(ctx, -380, -360, 380, 360)
            dibujo_ataud_seguridad(ctx, 0, 60, 0.75, 1.0, t)
        if t >= T_SUYO:
            tilde(ctx, 950, 700, 1.3 * pop(t, T_SUYO, 0.3))


# ------------------------------------------------------------------ 11. se hizo enterrar vivo durante varias horas
T_SE12 = b(12)
T_ENTERRAR = b(12, "enterrar")
T_VIVO12 = b(12, "vivo")
T_VARIAS = b(12, "varias")
SUELO11 = 820


def d_enterrado(ctx, t):
    fondo(ctx, t)
    luna(ctx, 860, 260, 60, t)
    pit = (300, SUELO11, 780, SUELO11 + 300)
    suelo(ctx, SUELO11, fosa=(pit[0], 0, pit[2], pit[3]))
    pasto(ctx, -400, 1480, SUELO11, t)
    baja = prog(t, T_SE12, T_VIVO12 - T_SE12, "inout")
    y = lerp(380, SUELO11 + 180, baja)
    with en(ctx, 540, y, 0.68):
        ataud(ctx, -340, -100, 340, 100)
        sabana(ctx, -340, -100, 340, 100)
        # late: está vivo
        lat = prog(t, T_VIVO12 - 0.05, 0.2) * (0.5 + 0.5 * math.sin(t * 9))
        if lat > 0.01:
            for k in range(3, 0, -1):
                rrect(ctx, -340 - 14 * k, -100 - 14 * k, 680 + 28 * k, 200 + 28 * k, 22 + 10 * k)
                ctx.set_source_rgba(*LUZ, 0.07 * lat)
                ctx.fill()
    tapa = prog(t, T_VIVO12 + 0.1, 0.45, "out")
    if tapa > 0.01:
        techo = SUELO11 + 180 - 68
        ctx.rectangle(pit[0], techo - 112 * tapa, pit[2] - pit[0], 112 * tapa)
        ctx.set_source_rgb(*TIERRA)
        ctx.fill()
        monticulo(ctx, pit[0] - 10, pit[2] + 10, SUELO11, 40 * tapa)
        tubo(ctx, 640, SUELO11 - 80 * tapa, SUELO11 + 120, w=40)
    ang = (t - T_VARIAS + 0.2) * 14 if t > T_VARIAS - 0.2 else 0
    reloj(ctx, 840, 420, 120, ang, pop(t, T_VARIAS - 0.25, 0.35))
    kartel(ctx, "VARIAS HORAS", 540, 250, 66, t, T_VARIAS - 0.05)


# ------------------------------------------------------------------ 12. sopa, cerveza y salchichas por un tubo
T_SOPA = b(13, "sopa")
T_CERVEZA = b(13, "cerveza")
T_SALCHICHAS = b(13, "salchichas")
T_TUBO13 = b(13, "tubo")
CAM12 = (620, 900, 1.15)


def plato(ctx, x, y, s, t, a=1.0):
    with en(ctx, x, y, s):
        for k in (-26, 0, 26):
            ctx.move_to(k, -70)
            ctx.curve_to(k + 14, -96, k - 14, -116, k, -140)
            trazo(ctx, BLANCO, 6, 0.6 * a)
        elipse(ctx, 0, -30, 90, 22)
        rellena(ctx, SOPA, 6)
        ctx.move_to(-90, -30)
        ctx.curve_to(-90, 50, 90, 50, 90, -30)
        rellena(ctx, BLANCO, 7)


def jarra(ctx, x, y, s):
    with en(ctx, x, y, s):
        ctx.arc(70, 0, 36, -1.4, 1.4)
        trazo(ctx, INK, 20)
        ctx.arc(70, 0, 36, -1.4, 1.4)
        trazo(ctx, hx("#DDEEF7"), 10)
        rrect(ctx, -60, -80, 130, 170, 18)
        rellena(ctx, CERVEZA, 8)
        for xx in (-30, 0, 30):
            ctx.move_to(xx, -50)
            ctx.line_to(xx, 60)
            trazo(ctx, hx("#FFD77A"), 6)
        for dx, r in ((-40, 30), (-5, 36), (34, 30)):
            ctx.arc(dx, -84, r, 0, TAU)
            rellena(ctx, BLANCO, 6)


def salchichas(ctx, x, y, s):
    with en(ctx, x, y, s):
        for k in range(3):
            with en(ctx, -110 + 110 * k, 10 * (k % 2), 1.0, 0.15 * (k - 1)):
                rrect(ctx, -52, -26, 104, 52, 26)
                rellena(ctx, SALCHICHA, 7)
                ctx.move_to(-26, -8)
                ctx.line_to(20, -12)
                trazo(ctx, hx("#E88A73"), 6)
        for k in range(2):
            ctx.arc(-55 + 110 * k, 6, 8, 0, TAU)
            rellena(ctx, hx("#F2D6B0"), 4)


COMIDA = [(T_SOPA, plato), (T_CERVEZA, jarra), (T_SALCHICHAS, salchichas)]


def d_comida(ctx, t):
    fondo(ctx, t)

    def extra(c):
        top = SUELO - 70
        tubo(c, TUBO_X, top, ATA[1] + 14, w=56, glow=prog(t, T_TUBO13 - 0.1, 0.25))
        for j, (t0, fn) in enumerate(COMIDA):
            if t < t0 - 0.15:
                continue
            s_in = pop(t, t0 - 0.15, 0.3)
            q = prog(t, t0 + 0.35, 0.7, "in")
            if q >= 1:
                continue
            x = lerp(TUBO_X + 110, TUBO_X, ease(clamp(q * 3), "out"))
            y = lerp(top - 190, ATA[1] + 60, q)
            sc = lerp(1.0, 0.18, q) * s_in
            if fn is plato:
                plato(c, x, y, sc, t)
            elif fn is salchichas:
                fn(c, x - 30, y, 0.75 * sc)
            else:
                fn(c, x, y, sc)
        mano(c, MANO_P[0], MANO_P[1], 1.0, 0.0, 0.0)

    ctx.save()
    cam(ctx, *CAM12)
    cementerio(ctx, t, cuerda_on=False, camp_on=False, extra=extra)
    ctx.restore()


# ------------------------------------------------------------------ 13. pero los inventos tenían un problema
T_INVENTOS = b(14, "inventos")
T_PROBLEMA = b(14, "problema")


def d_problema(ctx, t):
    fondo(ctx, t)
    xs = [230, 540, 850]
    for j, x in enumerate(xs):
        s = pop(t, T_INVENTOS - 0.15 + 0.12 * j, 0.35)
        if s <= 0.01:
            continue
        tiembla = 6 * math.sin(t * 40 + j) * prog(t, T_PROBLEMA - 0.05, 0.1)
        with en(ctx, x + tiembla, 860, s):
            rrect(ctx, -135, -170, 270, 340, 22)
            rellena(ctx, PLANO, 8)
            if j == 0:
                campana(ctx, 0, -110, 1.1, 0.0, 0.0, t, linea=True)
            elif j == 1:
                rrect(ctx, -20, -120, 40, 220, 6)
                trazo(ctx, LINEA, 6)
                for k in range(3):
                    yy = -80 + 60 * k
                    ctx.move_to(-10, yy - 8)
                    ctx.line_to(0, yy + 4)
                    ctx.line_to(10, yy - 8)
                    trazo(ctx, LINEA, 4)
            else:
                ctx.move_to(-40, 120)
                ctx.line_to(-40, -120)
                trazo(ctx, LINEA, 6)
                ctx.move_to(-40, -120)
                ctx.curve_to(0, -140, 30, -100, 70, -110)
                ctx.line_to(70, -40)
                ctx.curve_to(30, -30, 0, -70, -40, -50)
                trazo(ctx, LINEA, 6)
    sello(ctx, "PROBLEMA", 540, 860, 120, t, T_PROBLEMA - 0.05, rot=-9)


# ------------------------------------------------------------------ 14-15. cuerdas en brazos y piernas; el cuerpo se hincha
T_ATABAN = b(15, "ataban")
T_BRAZOS = b(15, "brazos")
T_PIERNAS = b(15, "piernas")
T_CUERPO16 = b(16, "cuerpo")
T_DESCOMP = b(16, "descomponerse")
T_HINCHA = b(16, "hincha")
T_MUEVE = b(16, "mueve")
HOJA14 = (90, 380, 990, 1360)
BAR_Y = 660
CENTRO = (560, 1080)


def silueta(ctx, inf, t):
    """Contorno del cuerpo acostado (de perfil, sin cara), en líneas de plano. inf = 0..1 hinchazón."""
    wob = 0.02 * math.sin(t * 5) * inf
    sx, sy = 1 + 0.1 * inf + wob, 1 + 0.4 * inf - wob
    with en(ctx, CENTRO[0], CENTRO[1], 1.0):
        ctx.scale(sx, sy)
        ctx.arc(-330, -10, 58, 0, TAU)
        trazo(ctx, LINEA, 6)
        rrect(ctx, -262, -62, 330, 110, 50)
        trazo(ctx, LINEA, 6)
        rrect(ctx, -230, -6, 260, 40, 20)
        trazo(ctx, LINEA, 5)
        rrect(ctx, 60, -50, 300, 46, 22)
        trazo(ctx, LINEA, 6)
        rrect(ctx, 60, 0, 300, 46, 22)
        trazo(ctx, LINEA, 6)
        rrect(ctx, 350, -58, 30, 60, 12)
        trazo(ctx, LINEA, 5)


def puntos_ata(inf):
    sx, sy = 1 + 0.1 * inf, 1 + 0.4 * inf
    muneca = (CENTRO[0] + 40 * sx, CENTRO[1] + 14 * sy - 30 * inf)
    tobillo = (CENTRO[0] + 340 * sx, CENTRO[1] - 30 * sy - 30 * inf)
    return muneca, tobillo


def linea_parcial(ctx, a, b_, q, col=ORO, w=6):
    if q <= 0.01:
        return
    ctx.move_to(*a)
    ctx.line_to(lerp(a[0], b_[0], q), lerp(a[1], b_[1], q))
    trazo(ctx, col, w)


def d_cuerdas(ctx, t):
    """Escenas 14 y 15: el mismo plano. Primero se atan las cuerdas; después el cuerpo se hincha y tira."""
    fondo(ctx, t)
    plano_hoja(ctx, *HOJA14)
    inf = prog(t, T_DESCOMP - 0.1, T_MUEVE - T_DESCOMP + 0.1, "inout")
    tira = prog(t, T_MUEVE - 0.15, 0.25)
    # la barra y la campana arriba
    ctx.move_to(260, BAR_Y)
    ctx.line_to(960, BAR_Y)
    trazo(ctx, LINEA, 6)
    ang = vaiven(t, T_MUEVE - 0.05, 0.35, 1.8, 1.0) + 0.06 * inf * math.sin(t * 7)
    campana(ctx, 600, BAR_Y - 180, 1.0, ang, prog(t, T_MUEVE - 0.05, 0.1) * 0.9, t, linea=True)
    ctx.move_to(600, BAR_Y - 80)
    ctx.line_to(600, BAR_Y)
    trazo(ctx, LINEA, 4)
    silueta(ctx, inf, t)
    mu, to = puntos_ata(inf)
    for (p, t0, xb) in ((mu, T_BRAZOS - 0.1, 560), (to, T_PIERNAS - 0.1, 900)):
        q = prog(t, t0, 0.35, "out")
        floja = (1 - inf) * 30
        if q > 0.01:
            ctx.move_to(xb, BAR_Y)
            ctx.curve_to(xb + floja, lerp(BAR_Y, p[1], 0.5), p[0] - floja, lerp(BAR_Y, p[1], 0.7),
                         lerp(xb, p[0], q), lerp(BAR_Y, p[1], q))
            trazo(ctx, ORO, 7 + 3 * tira)
            if q > 0.95:
                ctx.arc(p[0], p[1], 12, 0, TAU)
                trazo(ctx, ORO, 6)
    if inf > 0.3:
        a = clamp((inf - 0.3) / 0.3)
        for k in range(6):
            ang_k = k * TAU / 6 + 0.3
            r0 = 300 + 30 * math.sin(t * 4 + k)
            x0, y0 = CENTRO[0] + r0 * 1.2 * math.cos(ang_k), CENTRO[1] + 0.45 * r0 * math.sin(ang_k)
            ctx.move_to(x0, y0)
            ctx.line_to(x0 + 40 * math.cos(ang_k), y0 + 20 * math.sin(ang_k))
            trazo(ctx, LUZ, 6, a)
    if t < T_CUERPO16 - 0.1:
        kartel(ctx, "BRAZOS", 400, 1300, 48, t, T_BRAZOS - 0.05)
        kartel(ctx, "PIERNAS", 860, 1300, 48, t, T_PIERNAS - 0.05)
    else:
        kartel(ctx, "SE HINCHA", 540, 300, 68, t, T_HINCHA - 0.05)


# ------------------------------------------------------------------ 16. la campana podía sonar sola
T_CAMPANA17 = b(17, "campana")
T_SONAR = b(17, "sonar")
T_SOLA = b(17, "sola")
SUELO16 = 1180


def escena_superficie(ctx, t, ang, ring, xc=540, s=1.0, lapidas=True):
    luna(ctx, 860, 300, 64, t)
    suelo(ctx, SUELO16)
    if lapidas:
        for x, sc in ((150, 0.6), (930, 0.7)):
            lapida(ctx, x, SUELO16 + 6, s=sc, texto_=False)
    poste(ctx, xc - 120 * s, SUELO16, SUELO16 - 640 * s, xc)
    monticulo(ctx, xc - 330, xc + 250, SUELO16)
    pasto(ctx, -400, 1480, SUELO16, t)
    tubo(ctx, xc, SUELO16 - 70, SUELO16 + 60)
    cuerda(ctx, xc, SUELO16 - 640 * s + 110, SUELO16 + 40)
    campana(ctx, xc, SUELO16 - 640 * s + 10, 1.7 * s, ang, ring, t)


def d_sola(ctx, t):
    fondo(ctx, t)
    ang = vaiven(t, T_CAMPANA17 - 0.05, 0.5, 1.6, 2.5)
    ring = prog(t, T_CAMPANA17 - 0.05, 0.1)
    sh = 7 * ring * math.sin(t * 50) * math.exp(-(t - T_CAMPANA17) / 1.2) if t > T_CAMPANA17 else 0
    ctx.save()
    ctx.translate(sh, 0)
    escena_superficie(ctx, t, ang, ring)
    ctx.restore()
    kartel(ctx, "SOLA", 540, 300, 80, t, T_SOLA - 0.05)


# ------------------------------------------------------------------ 17. desde arriba, nadie podía saber quién la tocaba
T_DESDE = b(18)
T_NADIE = b(18, "nadie")
T_QUIEN = b(18, "quien")


def farol(ctx, x, y, a=1.0):
    for k in range(5, 0, -1):
        ctx.arc(x, y, 30 + 26 * k, 0, TAU)
        ctx.set_source_rgba(*LUZ, 0.06 * a)
        ctx.fill()
    ctx.move_to(x, y - 70)
    ctx.line_to(x, y - 40)
    trazo(ctx, INK, 6, a)
    rrect(ctx, x - 26, y - 40, 52, 76, 8)
    rellena(ctx, LUZ, 6, a=a)
    rrect(ctx, x - 32, y - 46, 64, 12, 4)
    rellena(ctx, NEGRO, 4, a=a)


def d_nadie(ctx, t):
    fondo(ctx, t)
    t0 = b(18)
    q = suave(t, t0 - 0.05, 0.9)
    ctx.save()
    zoom(ctx, lerp(1.0, 0.82, q), 540, 1000)
    ang = vaiven(t, t0 - 1.0, 0.4, 1.6, 2.0)
    escena_superficie(ctx, t, ang, 0.8, xc=700, s=0.8)
    xf = lerp(-140, 230, suave(t, T_NADIE - 0.4, 1.0))
    farol(ctx, xf, 1020 + 6 * math.sin(t * 6), pop(t, T_NADIE - 0.5, 0.3))
    ctx.restore()
    signo(ctx, "?", 540, 520, 260, t, T_QUIEN - 0.1, col=LUZ)


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_apertura),
    (T_PARA - 0.05, d_pregunta),
    (T_POR3 - 0.05, d_porsi),
    (b(4) - 0.05, d_colera),
    (b(5) - 0.05, d_distinguir),
    (b(6) - 0.05, d_diario),
    (b(7) - 0.05, d_plano),
    (b(8) - 0.05, d_patentes),
    (b(9) - 0.05, d_tubo),
    (b(11) - 0.05, d_medico),
    (b(12) - 0.05, d_enterrado),
    (b(13) - 0.05, d_comida),
    (b(14) - 0.05, d_problema),
    (b(15) - 0.05, d_cuerdas),
    (b(17) - 0.05, d_sola),
    (b(18) - 0.05, d_nadie),
    (b(19) - 0.05, d_cierre),
]
CORTE_SECO = {d_porsi, d_pregunta, d_sola}
XF = 0.18


def punch(t, t0, d=0.3, amp=0.05):
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


def deriva(t, i):
    """Acercamiento lento de cámara dentro de cada escena del medio (la escena nunca queda quieta)."""
    if i == 0 or i == len(ESCENAS) - 1:
        return 1.0
    t0 = ESCENAS[i][0]
    t1 = ESCENAS[i + 1][0]
    return lerp(1.0, 1.04, clamp((t - t0) / (t1 - t0)))


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


# ------------------------------------------------------------------ sonido (solo golpes cortos, sin sonidos sostenidos)
def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    ev(T_200 - 0.05, "pop", 0.3)
    for j in range(4):
        ev(T_CUERDA1 + 0.5 * j, "tick", 0.12, f=600 + 60 * j, d=0.04)
    ev(T_MANO1 - 0.05, "ding", 0.18)
    ev(T_CAMPANA2 - 0.1, "pop", 0.3)
    ev(T_NO3 - 0.05, "clic", 0.45)
    ev(T_ESTABA - 0.1, "whoosh", 0.35)
    ev(T_MUERTO3 - 0.05, "ding", 0.6)
    ev(T_COLERA - 0.05, "golpe", 0.5)
    for j in range(3):
        ev(T_ENTERRABAN + 0.25 + 0.32 * j, "clunk", 0.4)
    for j in range(6):
        ev(T_RAPIDO - 0.15 + 0.12 * j, "tick", 0.15, f=1000, d=0.03)
    ev(T_MIEDO4 - 0.05, "pop", 0.25)
    ev(T_A5, "pop", 0.3)
    ev(T_DISTINGUIR - 0.05, "pop", 0.3)
    ev(T_MUERTO5 - 0.05, "tick", 0.2, f=500, d=0.05)
    ev(T_MORIBUNDO - 0.05, "tick", 0.2, f=700, d=0.05)
    ev(T_DIARIOS - 0.2, "whoosh", 0.4)
    ev(T_DIARIOS + 0.4, "golpe", 0.35)
    for j in range(len(RASGU)):
        ev(T_ARANADOS - 0.05 + 0.2 * j, "crunch", 0.18)
    ev(b(7), "pop", 0.3)
    ev(T_INVENTARON - 0.15, "whoosh", 0.3)
    ev(T_ATAUDES7 - 0.1, "pop", 0.3)
    ev(T_ALEMANIA - 0.1, "pop", 0.35)
    for j in range(0, len(GRID), 3):
        ev(T_PATENTARON - 0.1 + (T_30 - T_PATENTARON + 0.05) * j / len(GRID), "tick", 0.1, f=900 + 20 * j, d=0.03)
    ev(T_30 - 0.05, "golpe", 0.5)
    ev(T_TUBO9 - 0.1, "pop", 0.3)
    ev(T_OTROS - 0.05, "pop", 0.25)
    ev(T_MOVIA - 0.05, "clic", 0.4)
    ev(T_MOVIA + 0.25, "pop", 0.35)
    ev(T_MEDICO - 0.15, "pop", 0.35)
    ev(T_PROBAR - 0.05, "pop", 0.3)
    ev(T_SUYO, "ding", 0.25)
    ev(T_VIVO12 + 0.1, "clunk", 0.4)
    ev(T_VARIAS - 0.25, "pop", 0.3)
    for j in range(6):
        ev(T_VARIAS + 0.15 * j, "tick", 0.12, f=1000, d=0.03)
    for t0, _ in COMIDA:
        ev(t0 - 0.15, "pop", 0.3)
        ev(t0 + 1.0, "plop", 0.3)
    ev(T_INVENTOS - 0.15, "pop", 0.3)
    ev(T_PROBLEMA - 0.05, "golpe", 0.5)
    ev(T_BRAZOS - 0.1, "clic", 0.3)
    ev(T_PIERNAS - 0.1, "clic", 0.3)
    ev(T_HINCHA - 0.05, "pop", 0.25)
    ev(T_MUEVE - 0.05, "ding", 0.35)
    for j in range(4):
        ev(T_CAMPANA17 - 0.05 + 0.31 * j, "ding", 0.55 - 0.08 * j)
    ev(T_SOLA - 0.05, "pop", 0.25)
    ev(T_NADIE - 0.5, "pop", 0.2)
    ev(T_QUIEN - 0.1, "pop", 0.35)
    ev(b(19, "vivo") - 0.1, "ding", 0.2)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "por_que_enterraban_con_campana.mp4"))
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

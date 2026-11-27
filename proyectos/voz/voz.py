"""Short "¿Por qué odias tu voz grabada?" — animación procedural (armazón de bostezo.py).

Estilo del canal: fondo azul con puntos, cosas con cara (el celular, el parlante, el micrófono) y subtítulos palabra por
palabra. Vos sale solo en la apertura y el cierre vuelve al primer cuadro: Vos hablando, con las ondas doradas de su
voz que salen de la boca y le vuelven a entrar por las orejas.

Hilo que se repite: las ondas doradas (la voz que oís vos, por dentro) contra las ondas blancas (la que viaja por el
aire, la que oyen los demás y el micrófono).

    python proyectos/voz/voz.py --hoja 0,3,6      # hoja de fotogramas -> proyectos/voz/fotos/hoja.png
    python proyectos/voz/voz.py --probar
    python proyectos/voz/voz.py                   # render -> salidas/por_que_odias_tu_voz_grabada.mp4
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
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
for _p in (ROOT, os.path.join(ROOT, "proyectos", "pantalla"), os.path.join(ROOT, "proyectos", "picante"),
           os.path.join(ROOT, "proyectos", "tierra"), os.path.join(ROOT, "proyectos", "bostezo")):
    sys.path.insert(0, _p)
import kit  # noqa: E402
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, cartel, clamp, ease, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rrect, texto)
from picante import fondo_azul  # noqa: E402
from tierra import (CREMA, ROJO, VERDE, alfa, cruz_roja, destello, elipse, en, kartel, rellena, sale, sello,  # noqa: E402
                    signo, tilde, trazo, zoom)
from bostezo import PELOS, PIELES, REMERAS, PANEL, cabeza, cara, corazon, medidor, ondas, torso  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "La voz que escuchas cuando hablas no es tu voz.",                 # b0
    "La verdadera es la de tus audios, esa que odias.",                # b1
    "¿De dónde sale, entonces, la que oyes tú?",                       # b2
    "Tápate los oídos y habla.",                                       # b3
    "Tu voz no se apaga. Suena más fuerte, como en un barril.",        # b4
    "No entra solo por las orejas.",                                   # b5
    "Pon la mano en tu garganta y habla.",                             # b6
    "Vibra, y esa vibración no se queda ahí.",                         # b7
    "Sube por algo duro que rodea tu oído.",                           # b8
    "Tu cráneo.",                                                      # b9
    "Es un parlante pegado al oído, que suma graves.",                 # b10
    "El micrófono no tiene tus huesos.",                               # b11
    "Capta solo el aire: lo mismo que oye la gente.",                  # b12
    "Sin huesos, suena más aguda.",                                    # b13
    "En un estudio, 80 personas calificaron voces grabadas.",          # b14
    "Sin avisarles, entre esas voces estaba la suya.",                 # b15
    "Pero calificaron su propia voz mejor que los demás.",             # b16
    "Les gustaba su voz, mientras no supieran que era suya.",          # b17
    "Lo que te molesta es descubrir que",                              # b18
]
WORDS = motor.align_times([{"texto": t} for t in NARRACION],
                          json.load(open(os.path.join(AQUI, "audio", "palabras.json"))))
COLA = 0.3
TOTAL = WORDS[-1][-1]["end"] + COLA
FLAT = [w for ws in WORDS for w in ws]


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


def hablando(t, desde=0.0, hasta=1e9):
    """0 = boca cerrada; 1 y 2 = abierta (alterna por palabra)."""
    if not (desde <= t < hasta):
        return 0
    for k, w in enumerate(FLAT):
        if w["start"] + 0.03 <= t < w["end"] - 0.03:
            return 1 + (k % 2)
    return 0


# ------------------------------------------------------------------ colores
KF = 60 * round(14 * TOTAL / 60) / (14 * TOTAL)      # el fondo de puntos cierra justo en el loop
ORO = hx("#FFC93C")
ORO2 = hx("#FF9F1C")
OSCURO = hx("#0B1230")
MADERA = hx("#B8662B")
MADERA2 = hx("#8E4A1C")
METAL = hx("#5B6475")
GRIS = hx("#C9D1DE")
GRIS2 = hx("#8D97A8")
PIEL_M = PIELES[1]          # el muñequito (no es Vos)
PELO_M = PELOS[2]
REMERA_M = REMERAS[1]
PIEL_P = PIELES[0]
HUESO = hx("#F6EBD6")
SUDOR = hx("#8FD3FF")


def fondo(ctx, t, oscuro=0.0):
    fondo_azul(ctx, t * KF)
    if oscuro > 0:
        ctx.set_source_rgba(0.027, 0.043, 0.11, oscuro)
        ctx.paint()


def deriva(ctx, t, t0, t1, z0=1.0, z1=1.07, cx=540, cy=860):
    zoom(ctx, lerp(z0, z1, ease(clamp((t - t0) / max(t1 - t0, 1e-3)), "inout")), cx, cy)


def onda_arco(ctx, x, y, ang, r, col, a=1.0, w=9):
    """Un arquito de onda de sonido en (x, y), abierto hacia ang."""
    if a <= 0.01:
        return
    with en(ctx, x, y, 1.0, ang):
        ctx.arc(-r * 0.6, 0, r, -0.8, 0.8)
        trazo(ctx, INK, w + 7, a)
        ctx.arc(-r * 0.6, 0, r, -0.8, 0.8)
        trazo(ctx, col, w, a)


def bez(p0, p1, p2, p3, q):
    u = 1 - q
    x = u ** 3 * p0[0] + 3 * u * u * q * p1[0] + 3 * u * q * q * p2[0] + q ** 3 * p3[0]
    y = u ** 3 * p0[1] + 3 * u * u * q * p1[1] + 3 * u * q * q * p2[1] + q ** 3 * p3[1]
    dx = 3 * u * u * (p1[0] - p0[0]) + 6 * u * q * (p2[0] - p1[0]) + 3 * q * q * (p3[0] - p2[0])
    dy = 3 * u * u * (p1[1] - p0[1]) + 6 * u * q * (p2[1] - p1[1]) + 3 * q * q * (p3[1] - p2[1])
    return x, y, math.atan2(dy, dx)


def ondas_curva(ctx, pts, t, periodo=1.2, n=4, col=ORO, r=34, a=1.0, w=9):
    """Ondas que viajan sin parar por una curva (bezier de 4 puntos)."""
    for j in range(n):
        q = ((t / periodo) + j / n) % 1.0
        x, y, ang = bez(*pts, q)
        aa = a * min(1.0, q * 6, (1 - q) * 6)
        onda_arco(ctx, x, y, ang, r * (0.8 + 0.4 * math.sin(q * math.pi)), col, aa, w)


def anillos(ctx, x, y, t, rmax, col=ORO, n=3, periodo=0.9, a=1.0, w=10):
    """Anillos que se expanden desde (x, y)."""
    for j in range(n):
        q = ((t / periodo) + j / n) % 1.0
        aa = a * (1 - q) * min(1, q * 5)
        if aa <= 0.01:
            continue
        ctx.arc(x, y, 20 + q * rmax, 0, TAU)
        trazo(ctx, INK, w + 6, aa * 0.8)
        ctx.arc(x, y, 20 + q * rmax, 0, TAU)
        trazo(ctx, col, w, aa)


def estrella(ctx, x, y, r, col=AMARILLO, a=1.0, rot=0.0):
    if r <= 0.5:
        return
    with en(ctx, x, y, 1.0, rot):
        for k in range(10):
            rr = r if k % 2 == 0 else r * 0.45
            ang = -math.pi / 2 + k * math.pi / 5
            (ctx.move_to if k == 0 else ctx.line_to)(rr * math.cos(ang), rr * math.sin(ang))
        ctx.close_path()
        rellena(ctx, col, max(3, r / 9), a=a)


def gota_sudor(ctx, x, y, s, a=1.0):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.move_to(0, -26)
        ctx.curve_to(16, -4, 18, 14, 0, 18)
        ctx.curve_to(-18, 14, -16, -4, 0, -26)
        ctx.close_path()
        rellena(ctx, SUDOR, 5, a=a)


def jitter(t, amp, f=37.0, seed=0.0):
    return amp * math.sin(t * f + seed) + amp * 0.5 * math.sin(t * f * 1.7 + 2 * seed)


# ------------------------------------------------------------------ Vos
def _rubor():
    return ('<ellipse cx="160" cy="372" rx="40" ry="22" fill="#FF5D5D" opacity=".75"/>'
            '<ellipse cx="360" cy="372" rx="40" ry="22" fill="#FF5D5D" opacity=".75"/>')


VOS_POSES = {
    "c": dict(mouth_kind="smile"),
    "m": dict(mouth_kind="mid"),
    "o": dict(mouth_kind="o"),
    "verg": dict(eyes="squint", brows="sad", mouth_kind="flat", extra=_rubor()),
    "verg_o": dict(eyes="squint", brows="sad", mouth_kind="mid", extra=_rubor()),
}


@functools.lru_cache(maxsize=None)
def vos_surface(pose):
    body = kit.vos(**VOS_POSES[pose])
    png = cairosvg.svg2png(bytestring=kit.svg(520, 820, body).encode(), output_width=1040, output_height=1640)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


def vos(ctx, pose, x, y, k=1.0, alpha=1.0, rot=0.0):
    """Vos con los pies en (x, y); k = 1 es el dibujo a 520x820."""
    if alpha <= 0.01 or k <= 0.01:
        return
    s = vos_surface(pose)
    ctx.save()
    ctx.translate(x, y)
    if rot:
        ctx.rotate(rot)
    ctx.scale(k / 2, k / 2)
    ctx.translate(-520, -1612)
    ctx.set_source_surface(s, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def vos_punto(x, y, k, sx, sy):
    """Punto del dibujo de Vos (coordenadas del svg 520x820) en la pantalla."""
    return x + (sx - 260) * k, y + (sy - 806) * k


# ------------------------------------------------------------------ objetos
def celular(ctx, x, y, s, t, sonando=0.0, sacude=0.0):
    """Celular con cara, con un audio de chat que se reproduce."""
    if s <= 0.01:
        return

    def contenido(c):
        c.rectangle(0, 0, 1080, 1920)
        c.set_source_rgb(*hx("#0E1B2E"))
        c.fill()
        # barra de arriba con la carita del celu
        c.rectangle(0, 0, 1080, 260)
        c.set_source_rgb(*hx("#1B2E4A"))
        c.fill()
        K.carita(c, 540, 150, 170, 1.6, ojos="open", boca="grin" if sonando > 0.5 else "smile")
        # burbuja de audio
        rrect(c, 90, 760, 900, 300, 80)
        c.set_source_rgb(*hx("#1F7A55"))
        c.fill_preserve()
        c.set_source_rgb(*INK)
        c.set_line_width(10)
        c.stroke()
        # play
        c.arc(250, 910, 85, 0, TAU)
        c.set_source_rgb(*BLANCO)
        c.fill()
        c.move_to(222, 860)
        c.line_to(300, 910)
        c.line_to(222, 960)
        c.close_path()
        c.set_source_rgb(*hx("#1F7A55"))
        c.fill()
        # barritas de la onda
        for k in range(16):
            xx = 380 + k * 34
            base = 0.35 + 0.65 * abs(math.sin(k * 1.7 + 0.4))
            amp = base * (0.45 + 0.55 * abs(math.sin(t * 9 + k * 0.8))) if sonando > 0 else base * 0.5
            hh = 150 * amp
            rrect(c, xx, 910 - hh / 2, 20, hh, 10)
            c.set_source_rgb(*(BLANCO if k / 16 < (t * 0.25) % 1 or sonando <= 0 else hx("#9FE3C4")))
            c.fill()
        texto(c, "0:07", 820, 1180, 90, fill=BLANCO, stroke=None)

    dx = jitter(t, 10 * sacude, 50)
    P.telefono(ctx, x + dx, y, s, contenido, t)


def barril(ctx, x, y_top, w, h, a=1.0):
    """Barril de madera; (x, y_top) = centro de la boca."""
    if a <= 0.01:
        return
    with alfa(ctx, a):
        hw = w / 2
        ctx.move_to(x - hw, y_top)
        ctx.curve_to(x - hw * 1.18, y_top + h * 0.33, x - hw * 1.18, y_top + h * 0.67, x - hw, y_top + h)
        ctx.line_to(x + hw, y_top + h)
        ctx.curve_to(x + hw * 1.18, y_top + h * 0.67, x + hw * 1.18, y_top + h * 0.33, x + hw, y_top)
        ctx.close_path()
        rellena(ctx, MADERA, 9)
        for k in range(1, 6):
            fx = -1 + 2 * k / 6
            ctx.move_to(x + fx * hw, y_top + 6)
            ctx.curve_to(x + fx * hw * 1.16, y_top + h * 0.4, x + fx * hw * 1.16, y_top + h * 0.6, x + fx * hw, y_top + h - 6)
            trazo(ctx, MADERA2, 6)
        for fy in (0.16, 0.84):
            bulge = 1 + 0.18 * math.sin(fy * math.pi)
            elipse(ctx, x, y_top + h * fy, hw * bulge, 16)
            ctx.set_line_width(26)
            ctx.set_source_rgb(*INK)
            ctx.stroke()
            elipse(ctx, x, y_top + h * fy, hw * bulge, 16)
            ctx.set_line_width(16)
            ctx.set_source_rgb(*METAL)
            ctx.stroke()
        elipse(ctx, x, y_top, hw, 34)
        rellena(ctx, MADERA2, 9)


def parlante(ctx, x, y, s, k=0.0, cara_k="grin"):
    """Parlante con cara; k = cuánto bombea el cono (0..1)."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        rrect(ctx, -110, -150, 220, 300, 36)
        rellena(ctx, hx("#3A3F55"), 9)
        K.carita(ctx, 0, -95, 70, 0.75, ojos="happy" if cara_k == "grin" else "open", boca=cara_k)
        rc = 70 * (1 + 0.12 * k)
        ctx.arc(0, 45, rc, 0, TAU)
        rellena(ctx, hx("#1E2233"), 8)
        ctx.arc(0, 45, rc * 0.55, 0, TAU)
        rellena(ctx, hx("#4C5470"), 6)
        ctx.arc(0, 45, rc * 0.2, 0, TAU)
        rellena(ctx, ORO, 5)


def perilla(ctx, x, y, s, frac, etiqueta="BAJOS"):
    """Perilla de volumen; frac = 0..1."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        rrect(ctx, -150, -150, 300, 360, 40)
        rellena(ctx, PANEL, 8)
        a0, a1 = math.radians(135), math.radians(405)
        ctx.arc(0, 0, 105, a0, a1)
        trazo(ctx, hx("#2E3A66"), 22)
        if frac > 0.01:
            ctx.arc(0, 0, 105, a0, a0 + (a1 - a0) * clamp(frac))
            trazo(ctx, ORO, 22)
        ctx.arc(0, 0, 78, 0, TAU)
        rellena(ctx, GRIS, 8)
        ang = a0 + (a1 - a0) * clamp(frac)
        ctx.move_to(22 * math.cos(ang), 22 * math.sin(ang))
        ctx.line_to(62 * math.cos(ang), 62 * math.sin(ang))
        trazo(ctx, INK, 14)
        texto(ctx, etiqueta, 0, 160, 62, fill=BLANCO, sw=8)


def microfono(ctx, x, y, s, t, encoge=0.0, cara_b="smile", ceja=None, look=(0, 0)):
    """Micrófono con cara y bracitos; encoge = 0..1 (se encoge de hombros)."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        # bracitos
        for sx in (-1, 1):
            hx0, hy0 = sx * 52, 40
            ex = sx * lerp(95, 120, encoge)
            ey = lerp(140, 10, encoge)
            hxx = sx * lerp(105, 165, encoge)
            hyy = lerp(230, -50, encoge)
            ctx.move_to(hx0, hy0)
            ctx.curve_to(ex, ey, ex, ey, hxx, hyy)
            trazo(ctx, INK, 22)
            ctx.move_to(hx0, hy0)
            ctx.curve_to(ex, ey, ex, ey, hxx, hyy)
            trazo(ctx, GRIS2, 12)
            ctx.arc(hxx, hyy, 22, 0, TAU)
            rellena(ctx, BLANCO, 6)
        # mango
        rrect(ctx, -52, -10, 104, 330, 40)
        rellena(ctx, hx("#2A2F3F"), 9)
        rrect(ctx, -60, 40, 120, 30, 12)
        rellena(ctx, METAL, 6)
        # cabeza (rejilla)
        ctx.arc(0, -120, 135, 0, TAU)
        rellena(ctx, GRIS, 9)
        ctx.save()
        ctx.arc(0, -120, 128, 0, TAU)
        ctx.clip()
        for k in range(-6, 7):
            ctx.move_to(k * 24 - 140, -260)
            ctx.line_to(k * 24 + 140, 20)
            ctx.move_to(k * 24 + 140, -260)
            ctx.line_to(k * 24 - 140, 20)
        trazo(ctx, GRIS2, 3, 0.7)
        ctx.restore()
        K.carita(ctx, 0, -120, 110, 1.15, ojos="open", boca=cara_b, ceja=ceja, look=look)


def calavera(ctx, x, y, s, a=1.0):
    if s <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        ctx.arc(0, -10, 70, 0, TAU)
        rellena(ctx, HUESO, 7)
        rrect(ctx, -40, 30, 80, 52, 16)
        rellena(ctx, HUESO, 7)
        for sx in (-1, 1):
            elipse(ctx, sx * 27, -10, 19, 22)
            ctx.set_source_rgb(*INK)
            ctx.fill()
        ctx.move_to(0, 14)
        ctx.line_to(-9, 30)
        ctx.line_to(9, 30)
        ctx.close_path()
        ctx.fill()
        for k in range(-2, 3):
            ctx.move_to(k * 13, 52)
            ctx.line_to(k * 13, 78)
        trazo(ctx, INK, 4)


def auriculares(ctx, x, y, R, a=1.0, col=ROJO):
    ctx.arc(x, y - 0.05 * R, 1.12 * R, math.pi * 1.05, math.pi * 1.95)
    trazo(ctx, INK, 0.22 * R, a)
    ctx.arc(x, y - 0.05 * R, 1.12 * R, math.pi * 1.05, math.pi * 1.95)
    trazo(ctx, hx("#3A3F55"), 0.12 * R, a)
    for sx in (-1, 1):
        rrect(ctx, x + sx * 1.02 * R - 0.2 * R, y - 0.2 * R, 0.4 * R, 0.55 * R, 0.16 * R)
        rellena(ctx, col, max(3, 0.06 * R), a=a)


def muneco(ctx, x, y, R, boca="smile", ojos="open", ceja=None, look=(0, 0), auris=False, col_auris=ROJO, s=1.0,
           piel=PIEL_M, pelo=PELO_M, remera=REMERA_M, rubor=True):
    """El muñequito de las pruebas (no es Vos): cabeza de radio R en (x, y) y remera."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        torso(ctx, 0, 0, R, remera)
        cabeza(ctx, 0, 0, R, piel=piel, pelo=pelo, look=look, ojos=ojos, boca=boca, ceja=ceja, rubor=rubor)
        if auris:
            auriculares(ctx, 0, 0, R, col=col_auris)


def tarjeta_audio(ctx, x, y, s, t, avatar=None, brillo=0.0, sonando=True):
    """Tarjeta de un audio grabado: avatar, play y onda. avatar=None -> signo de pregunta."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        if brillo > 0.01:
            g = cairo.RadialGradient(0, 0, 40, 0, 0, 260)
            g.add_color_stop_rgba(0, *ORO, 0.55 * brillo)
            g.add_color_stop_rgba(1, *ORO, 0)
            ctx.set_source(g)
            ctx.arc(0, 0, 260, 0, TAU)
            ctx.fill()
        rrect(ctx, -170, -70, 340, 140, 34)
        rellena(ctx, BLANCO if brillo < 0.5 else hx("#FFF4C9"), 8)
        ctx.arc(-110, 0, 44, 0, TAU)
        rellena(ctx, GRIS if avatar is None else PIEL_M, 6)
        if avatar is None:
            texto(ctx, "?", -110, 4, 60, fill=BLANCO, sw=6)
        else:
            ctx.save()
            ctx.arc(-110, 0, 44, 0, TAU)
            ctx.clip()
            elipse(ctx, -110, -34, 46, 22)
            ctx.set_source_rgb(*PELO_M)
            ctx.fill()
            ctx.restore()
            K.carita(ctx, -110, 6, 30, 0.32, ojos="open", boca="smile")
        for k in range(9):
            xx = -40 + k * 22
            base = 0.4 + 0.6 * abs(math.sin(k * 1.3 + (0 if avatar is None else 1)))
            amp = base * (0.5 + 0.5 * abs(math.sin(t * 8 + k))) if sonando else base * 0.6
            hh = 80 * amp
            rrect(ctx, xx, -hh / 2, 12, hh, 6)
            ctx.set_source_rgb(*hx("#1F7A55"))
            ctx.fill()


# ------------------------------------------------------------------ cabeza de perfil
def _perfil_path(ctx):
    ctx.move_to(-130, 470)
    ctx.curve_to(-138, 330, -175, 245, -232, 150)
    ctx.curve_to(-335, -10, -300, -255, -120, -322)
    ctx.curve_to(40, -382, 200, -300, 216, -150)
    ctx.curve_to(222, -95, 210, -72, 226, -42)
    ctx.curve_to(262, 8, 290, 40, 264, 62)
    ctx.curve_to(248, 76, 232, 72, 229, 88)
    ctx.curve_to(246, 100, 242, 122, 229, 130)
    ctx.curve_to(243, 145, 237, 166, 223, 172)
    ctx.curve_to(231, 212, 216, 247, 170, 260)
    ctx.curve_to(130, 268, 110, 286, 106, 322)
    ctx.curve_to(100, 382, 106, 432, 112, 470)
    ctx.close_path()


def _craneo_path(ctx):
    ctx.move_to(-210, 150)
    ctx.curve_to(-298, 20, -275, -235, -115, -296)
    ctx.curve_to(30, -346, 176, -286, 191, -160)
    ctx.curve_to(197, -110, 187, -78, 197, -50)
    ctx.line_to(206, -30)
    ctx.curve_to(213, 0, 201, 30, 191, 55)
    ctx.curve_to(206, 70, 206, 100, 193, 112)
    ctx.line_to(60, 112)
    ctx.curve_to(20, 112, -10, 92, -30, 72)
    ctx.curve_to(-80, 122, -150, 172, -210, 150)
    ctx.close_path()


def _mandibula_path(ctx):
    ctx.move_to(-22, 76)
    ctx.curve_to(-32, 122, -36, 172, -10, 200)
    ctx.curve_to(60, 226, 140, 236, 190, 228)
    ctx.curve_to(206, 210, 201, 170, 191, 150)
    ctx.line_to(80, 150)
    ctx.curve_to(30, 150, 10, 122, 4, 84)
    ctx.close_path()


OREJA = (-50, 32)
COCLEA = (-44, 36)
LARINGE = (92, 362)
PULSO = (LARINGE, (60, 255), (-12, 150), COCLEA)


def perfil(ctx, x, y, s, t=0.0, oscuro=0.0, xray=0.0, brillo=0.0, vib=0.0, boca=0, oreja=0.0, look=1.0):
    """Cabeza de perfil mirando a la derecha; (x, y) = centro de la cabeza; s = escala.

    oscuro: 0 = piel, 1 = silueta oscura. xray: deja ver el cráneo. brillo: el cráneo se ilumina.
    vib: el cráneo vibra. boca: 0 cerrada, 1/2 hablando. oreja: resalta la oreja.
    """
    if s <= 0.01:
        return
    jx = jitter(t, 4 * vib, 61) if vib > 0 else 0.0
    with en(ctx, x + jx, y, s):
        _perfil_path(ctx)
        col = tuple(lerp(a_, b_, oscuro) for a_, b_ in zip(PIEL_P, hx("#1A2350")))
        rellena(ctx, col, 9)
        # pelo
        ctx.save()
        _perfil_path(ctx)
        ctx.clip()
        ctx.move_to(-340, 150)
        ctx.curve_to(-360, -150, -260, -330, -60, -360)
        ctx.curve_to(110, -385, 230, -300, 232, -190)
        ctx.curve_to(150, -250, 40, -250, -60, -200)
        ctx.curve_to(-140, -160, -150, -40, -120, 80)
        ctx.close_path()
        pc = tuple(lerp(a_, b_, oscuro) for a_, b_ in zip(PELOS[0], hx("#11183A")))
        ctx.set_source_rgb(*pc)
        ctx.fill()
        ctx.restore()
        _perfil_path(ctx)
        trazo(ctx, INK, 9)
        if xray > 0.01:
            with alfa(ctx, xray):
                ctx.save()
                _perfil_path(ctx)
                ctx.clip()
                ctx.set_source_rgba(0.04, 0.07, 0.18, 0.78)
                ctx.paint()
                for k in range(5):
                    ry = 236 + k * 48
                    rrect(ctx, -142, ry, 74, 36, 12)
                    rellena(ctx, HUESO, 5)
                if brillo > 0.01:
                    g = cairo.RadialGradient(-20, -60, 30, -20, -60, 420)
                    g.add_color_stop_rgba(0, *ORO, 0.75 * brillo)
                    g.add_color_stop_rgba(1, *ORO, 0)
                    ctx.set_source(g)
                    ctx.paint()
                cr = tuple(lerp(a_, b_, brillo) for a_, b_ in zip(HUESO, hx("#FFF1B8")))
                _craneo_path(ctx)
                rellena(ctx, cr, 8)
                _mandibula_path(ctx)
                rellena(ctx, cr, 8)
                for k in range(5):
                    rrect(ctx, 118 + k * 15, 112, 13, 18, 4)
                    rellena(ctx, BLANCO, 3)
                    rrect(ctx, 118 + k * 15, 132, 13, 18, 4)
                    rellena(ctx, BLANCO, 3)
                elipse(ctx, 130, -58, 44, 38)
                ctx.set_source_rgb(*OSCURO)
                ctx.fill_preserve()
                trazo(ctx, INK, 6)
                # laringe
                rrect(ctx, LARINGE[0] - 26, LARINGE[1] - 38, 52, 76, 16)
                rellena(ctx, hx("#F4B6B0"), 5)
                ctx.move_to(LARINGE[0] - 12, LARINGE[1] - 18)
                ctx.line_to(LARINGE[0] + 2, LARINGE[1] + 16)
                ctx.line_to(LARINGE[0] + 14, LARINGE[1] - 18)
                trazo(ctx, ORO2, 5)
                # cóclea (el caracol del oído)
                cx_, cy_ = COCLEA
                ctx.move_to(cx_, cy_)
                for k in range(1, 60):
                    th = k * 0.22
                    rr = 1.2 + k * 0.42
                    ctx.line_to(cx_ + rr * math.cos(th), cy_ + rr * math.sin(th))
                trazo(ctx, ORO, 7)
                ctx.restore()
        else:
            # cara
            ojo_x, ojo_y = 150, -62
            if oscuro < 0.6:
                elipse(ctx, ojo_x + 6 * look, ojo_y, 16, 22)
                ctx.set_source_rgb(*INK)
                ctx.fill()
                ctx.move_to(118, -112)
                ctx.curve_to(140, -124, 168, -122, 186, -110)
                trazo(ctx, INK, 9)
                if boca == 0:
                    ctx.move_to(205, 128)
                    ctx.curve_to(218, 134, 226, 132, 232, 126)
                    trazo(ctx, INK, 7)
                else:
                    elipse(ctx, 220, 130, 16, 10 if boca == 1 else 16)
                    ctx.set_source_rgb(*hx(kit.P["boca"]))
                    ctx.fill_preserve()
                    trazo(ctx, INK, 6)
                ctx.arc(60, 70, 30, 0, TAU)
                ctx.set_source_rgba(1, 0.56, 0.66, 0.35)
                ctx.fill()
        # oreja
        ox, oy = OREJA
        elipse(ctx, ox, oy, 42, 66)
        oc = tuple(lerp(a_, b_, oscuro * (1 - xray)) for a_, b_ in zip(hx("#F0B48C"), hx("#1A2350")))
        if xray > 0.01:
            ctx.set_source_rgba(*oc, 1 - 0.6 * xray)
            ctx.fill_preserve()
            trazo(ctx, INK, 7)
        else:
            rellena(ctx, oc, 7)
        ctx.move_to(ox + 14, oy - 40)
        ctx.curve_to(ox - 24, oy - 44, ox - 28, oy + 30, ox + 6, oy + 42)
        trazo(ctx, INK, 6, 1 - 0.5 * xray)
        if oreja > 0.01:
            elipse(ctx, ox, oy, 56, 82)
            trazo(ctx, ORO, 12, oreja)


def perfil_mundo(x, y, s, p):
    """Punto local del perfil en la pantalla."""
    return x + p[0] * s, y + p[1] * s


# ------------------------------------------------------------------ 1. apertura: Vos y la voz que le entra por la cabeza
T_LA1 = b(1)
T_AUDIOS = b(1, "audios")
T_ODIAS = b(1, "odias")
VY, VK = 1390, 1.08


def vos_x(u):
    return lerp(540, 300, prog(u, T_LA1 - 0.15, 0.45, "inout")) if u >= 0 else 540


def ondas_vos(ctx, x, u, a=1.0):
    """Las ondas doradas: salen de la boca y le entran por las dos orejas."""
    mx, my = vos_punto(x, VY, VK, 260, 400)
    for sx in (-1, 1):
        ox, oy = vos_punto(x, VY, VK, 260 + sx * 178, 292)
        pts = ((mx + sx * 40, my + 20), (mx + sx * 330, my + 150), (ox + sx * 210, oy - 260), (ox + sx * 8, oy))
        ondas_curva(ctx, pts, u + (0.3 if sx > 0 else 0), periodo=1.3, n=4, col=ORO, r=40, a=a, w=12)


def d_apertura(ctx, u):
    t = u % TOTAL
    fondo(ctx, t)
    x = vos_x(u)
    hab = hablando(t, 0, TOTAL)
    if u >= 0 and u >= T_ODIAS - 0.05:
        pose = "verg_o" if hab else "verg"
    else:
        pose = "c" if hab == 0 else ("m" if hab == 1 else "o")
    # balanceo de cuerpo al hablar
    rot = 0.015 * math.sin(t * 2.4)
    if u >= 0:
        sc = 1 - 0.08 * prog(u, T_LA1 - 0.15, 0.45)
    else:
        sc = 1.0
    k = VK * sc
    ondas_vos(ctx, x, u, a=1.0)
    vos(ctx, pose, x, VY, k, rot=rot)
    if u >= 0:
        s_cel = pop(u, T_LA1 - 0.05, 0.4)
        if s_cel > 0.01:
            cx, cy = 790, 800 + 10 * math.sin(u * 3)
            son = 1.0 if u >= T_AUDIOS - 0.1 else 0.0
            # ondas blancas: las que salen del celu hacia afuera (la voz que oyen todos)
            if son:
                anillos(ctx, cx, cy + 120, u, 300, col=BLANCO, n=3, periodo=1.0, a=0.8 * s_cel, w=7)
            celular(ctx, cx, cy, 0.26 * s_cel, u, sonando=son, sacude=prog(u, T_ODIAS - 0.1, 0.2))
            kartel(ctx, "TU VOZ REAL", cx, cy - 330, 54, u, T_AUDIOS - 0.05, box=BLANCO)
            if u >= T_ODIAS - 0.05:
                gota_sudor(ctx, *vos_punto(x, VY, k, 420, 190), pop(u, T_ODIAS, 0.3))


def d_cierre(ctx, t):
    d_apertura(ctx, t - TOTAL)


# ------------------------------------------------------------------ 2. pregunta: ¿de dónde sale la que oyes?
T_P2 = b(2)
T_OYES = b(2, "oyes")
T_TU2 = b(2, "tu")
PX, PY, PS = 560, 800, 1.25


def d_pregunta(ctx, t):
    fondo(ctx, t)
    deriva(ctx, t, T_P2, b(3), 1.0, 1.08)
    perfil(ctx, PX, PY, PS * pop(t, T_P2, 0.35), t, boca=hablando(t, T_P2, b(3)) and 1, oreja=0.0)
    # una onda dorada que da vueltas buscando por dónde entra
    q = (t - T_P2) * 0.9
    for j in range(3):
        th = q * 2.2 - j * 0.35
        rx, ry = 470, 380
        x = PX + rx * math.cos(th)
        y = PY - 60 + ry * math.sin(th)
        onda_arco(ctx, x, y, th + math.pi / 2, 34, ORO, a=min(1, (t - T_P2) * 3) * (1 - 0.25 * j))
    ox, oy = perfil_mundo(PX, PY, PS, OREJA)
    if t >= T_OYES - 0.1:
        anillos(ctx, ox, oy, t, 150, col=ORO, n=2, periodo=0.8, a=prog(t, T_OYES - 0.1, 0.2))
    signo(ctx, "?", ox - 20, oy - 260, 260, t, T_TU2 - 0.2)


# ------------------------------------------------------------------ 3. oídos tapados: suena más fuerte, como en un barril
T_TAPATE = b(3)
T_OIDOS = b(3, "oidos")
T_HABLA3 = b(3, "habla")
T_TU4 = b(4)
T_SUENA = b(4, "suena")
T_FUERTE = b(4, "fuerte")
T_BARRIL = b(4, "como")
T_NO5 = b(5)
T_ENTRA = b(5, "entra")
T_OREJAS = b(5, "orejas")
MX, MY, MR = 540, 760, 190


def manos_orejas(ctx, x, y, R, p, t, cerrado=0.0):
    """Brazos del muñequito: p = 0 abajo, 1 tapando las orejas."""
    pe = ease(clamp(p), "inout")
    for sx in (-1, 1):
        sh = (x + sx * 0.7 * R, y + 1.05 * R)
        down = (x + sx * 1.05 * R, y + 2.0 * R)
        up = (x + sx * 1.0 * R, y + 0.1 * R)
        hxx, hyy = lerp(down[0], up[0], pe), lerp(down[1], up[1], pe)
        elbow = (x + sx * lerp(1.0, 1.45, pe) * R, y + lerp(1.55, 1.0, pe) * R)
        for col, w in ((INK, 0.34 * R), (PIEL_M, 0.22 * R)):
            ctx.move_to(*sh)
            ctx.curve_to(elbow[0], elbow[1], elbow[0], elbow[1], hxx, hyy)
            trazo(ctx, col, w)
        ctx.arc(hxx, hyy, 0.27 * R, 0, TAU)
        rellena(ctx, PIEL_M, 0.05 * R)
        if cerrado > 0.01:
            cartel(ctx, "CERRADO", hxx + sx * 0.05 * R, hyy - 0.42 * R, 0.17 * R, box=ROJO, fg=BLANCO,
                   s=cerrado, rot=sx * 0.12)


def d_oidos(ctx, t):
    fondo(ctx, t)
    # cámara: se acerca a la cabeza desde "No entra solo por las orejas"
    zc = lerp(1.0, 1.06, prog(t, T_TAPATE, T_NO5 - T_TAPATE))
    zc *= lerp(1.0, 1.32, prog(t, T_NO5 - 0.1, 0.8, "inout"))
    zoom(ctx, zc, MX, MY + 60)
    s = pop(t, T_TAPATE - 0.05, 0.35)
    p = prog(t, T_TAPATE + 0.15, T_OIDOS - T_TAPATE + 0.1)
    hab = hablando(t, T_HABLA3 - 0.05, b(6))
    temblor = (jitter(t, 6, 47) if t >= T_FUERTE - 0.1 else 0.0) * (1 - prog(t, T_NO5, 0.3))
    x = MX + temblor
    with en(ctx, 0, 0, 1.0):
        if s > 0.01:
            # barril (detrás de los brazos de arriba, delante del cuerpo)
            torso(ctx, x, MY, MR, REMERA_M)
            dentro = t >= T_TU4 - 0.05
            boca = "o" if hab else ("wavy" if dentro and t < T_SUENA else "smile")
            ojos = "wide" if t >= T_FUERTE - 0.05 else "open"
            ceja = "up" if t >= T_SUENA else None
            cabeza(ctx, x, MY, MR * s, piel=PIEL_M, pelo=PELO_M, boca=boca, ojos=ojos, ceja=ceja)
            # la voz que se queda adentro: anillos dorados dentro de la cabeza
            if dentro:
                fuerza = 1 + 0.6 * prog(t, T_SUENA - 0.05, 0.4)
                ctx.save()
                ctx.arc(x, MY, MR * 0.98, 0, TAU)
                ctx.clip()
                anillos(ctx, x, MY + 0.3 * MR, t, 160 * fuerza, col=ORO, n=3, periodo=0.75,
                        a=0.85 * prog(t, T_TU4 - 0.05, 0.3), w=8 * fuerza)
                ctx.restore()
            # barril
            sube = prog(t, T_BARRIL - 0.1, 0.45, "out")
            if sube > 0.01:
                top = lerp(1950, MY + 1.0 * MR, sube)
                barril(ctx, x, top, 2.3 * MR, 1.5 * MR)
                # eco: arquitos que rebotan dentro del barril
                for j in range(4):
                    q = ((t - T_BARRIL) * 1.4 + j / 4) % 1
                    xx = x + lerp(-0.9, 0.9, abs(2 * q - 1)) * MR
                    onda_arco(ctx, xx, top + 0.55 * MR, 0 if (2 * q - 1) > 0 else math.pi, 26, ORO,
                              a=0.9 * sube, w=7)
            manos_orejas(ctx, x, MY, MR * s, p, t, cerrado=pop(t, T_ENTRA - 0.1, 0.3))
    kartel(ctx, "¡MÁS FUERTE!", 540, 300, 84, t, T_FUERTE - 0.1, T_BARRIL - 0.05, box=AMARILLO)
    if t >= T_NO5:
        signo(ctx, "?", 860, 420, 200, t, T_OREJAS - 0.2)


# ------------------------------------------------------------------ 4. garganta: vibra, y la vibración sube
T_PON = b(6)
T_MANO = b(6, "mano")
T_HABLA6 = b(6, "habla")
T_VIBRA = b(7)
T_ESA7 = b(7, "esa")
T_QUEDA = b(7, "queda")
T_AHI = b(7, "ahi")


def mano_garganta(ctx, x, y, s, t):
    """Mano apoyada sobre la garganta; (x, y) = centro de la palma."""
    with en(ctx, x, y, s):
        for k in range(4):
            fy = -78 + k * 52
            largo = 250 - abs(k - 1.3) * 30
            rrect(ctx, -10, fy - 22, largo, 46, 23)
            rellena(ctx, PIEL_M, 7)
        rrect(ctx, -170, -110, 200, 230, 70)
        rellena(ctx, PIEL_M, 8)
        ctx.move_to(-30, -100)
        ctx.curve_to(10, -170, 60, -190, 90, -170)
        trazo(ctx, INK, 50)
        ctx.move_to(-30, -100)
        ctx.curve_to(10, -170, 60, -190, 90, -170)
        trazo(ctx, PIEL_M, 34)
        rrect(ctx, -330, -62, 220, 124, 50)
        rellena(ctx, PIEL_M, 8)
        rrect(ctx, -620, -88, 330, 176, 50)
        ctx.set_source_rgb(*REMERA_M)
        ctx.fill_preserve()
        trazo(ctx, INK, 8)


def d_garganta(ctx, t):
    fondo(ctx, t)
    # la cámara sube siguiendo a la vibración
    sube = prog(t, T_QUEDA - 0.2, T_AHI - T_QUEDA + 0.6, "in")
    zoom(ctx, lerp(1.0, 1.08, prog(t, T_PON, b(8) - T_PON)), 540, 800)
    ctx.translate(0, 420 * sube)
    hab = hablando(t, T_HABLA6 - 0.05, b(8))
    vib = prog(t, T_HABLA6, 0.2) * (0.6 + 0.8 * prog(t, T_VIBRA - 0.05, 0.2))
    vib *= 1 - 0.5 * prog(t, T_ESA7, 0.4)
    jx = jitter(t, 7 * vib, 55)
    with en(ctx, jx, 0):
        # cuello
        rrect(ctx, 380, 380, 320, 1200, 60)
        rellena(ctx, PIEL_M, 9)
        ctx.move_to(520, 760)
        ctx.curve_to(560, 730, 600, 760, 590, 800)
        trazo(ctx, hx("#C4885F"), 8)
        # cara (mandíbula y boca) arriba
        elipse(ctx, 540, 250, 360, 300)
        rellena(ctx, PIEL_M, 9)
        ctx.save()
        elipse(ctx, 540, 250, 360, 300)
        ctx.clip()
        ctx.rectangle(0, -200, 1080, 200)
        ctx.set_source_rgb(*PELO_M)
        ctx.fill()
        ctx.restore()
        for sx in (-1, 1):
            K.ojo(ctx, 540 + sx * 120, 170, 1.7, "open", (0, 0.3))
        if vib > 0.5:
            K.cejas(ctx, 540, 100, 240, "up", 1.7)
        ctx.move_to(548, 230)
        ctx.curve_to(580, 280, 560, 300, 530, 300)
        trazo(ctx, INK, 8)
        if hab:
            elipse(ctx, 540, 400, 70, 34 if hab == 1 else 48)
            ctx.set_source_rgb(*hx(kit.P["boca"]))
            ctx.fill_preserve()
            trazo(ctx, INK, 8)
        else:
            ctx.move_to(470, 395)
            ctx.curve_to(510, 425, 570, 425, 610, 395)
            trazo(ctx, INK, 10)
        # cuello de la remera
        ctx.move_to(300, 1400)
        ctx.line_to(420, 1240)
        ctx.curve_to(480, 1300, 600, 1300, 660, 1240)
        ctx.line_to(780, 1400)
        ctx.line_to(780, 1700)
        ctx.line_to(300, 1700)
        ctx.close_path()
        rellena(ctx, REMERA_M, 9)
    # la mano entra desde la izquierda
    pm = prog(t, T_PON - 0.05, T_MANO - T_PON + 0.35, "out")
    if pm > 0.01:
        mano_garganta(ctx, lerp(-200, 470, pm) + jx * 1.4, 820, 1.0, t)
    # vibración: rayitas a los costados
    if vib > 0.05:
        for sx in (-1, 1):
            for j in range(3):
                q = ((t * 3 + j / 3) % 1)
                xx = 540 + sx * (210 + 70 * j + 20 * q)
                ctx.arc(xx - sx * 60, 820, 60 + 30 * j, -0.6 if sx > 0 else math.pi - 0.6,
                        0.6 if sx > 0 else math.pi + 0.6)
                trazo(ctx, BLANCO, 9, vib * (1 - q) * 0.9)
    kartel(ctx, "¡VIBRA!", 820, 560, 96, t, T_VIBRA - 0.05, T_ESA7 + 0.6, box=AMARILLO, rot=-0.08)
    # el pulso dorado arranca a subir
    if t >= T_ESA7 - 0.1:
        a = prog(t, T_ESA7 - 0.1, 0.3)
        py = lerp(820, 120, prog(t, T_QUEDA - 0.1, T_AHI - T_QUEDA + 0.55, "in"))
        g = cairo.RadialGradient(540, py, 10, 540, py, 160)
        g.add_color_stop_rgba(0, *ORO, 0.95 * a)
        g.add_color_stop_rgba(1, *ORO, 0)
        ctx.set_source(g)
        ctx.arc(540, py, 160, 0, TAU)
        ctx.fill()
        anillos(ctx, 540, py, t, 110, col=ORO, n=2, periodo=0.6, a=a, w=8)


# ------------------------------------------------------------------ 5. perfil: sube por algo duro... tu cráneo. Un parlante.
T_SUBE = b(8)
T_DURO = b(8, "duro")
T_RODEA = b(8, "rodea")
T_OIDO8 = b(8, "oido")
T_CRANEO = b(9)
T_CRANEO_W = b(9, "craneo")
T_ES10 = b(10)
T_PARLANTE = b(10, "parlante")
T_PEGADO = b(10, "pegado")
T_SUMA = b(10, "suma")
T_GRAVES = b(10, "graves")
QX, QY, QS = 560, 820, 1.35


def d_perfil(ctx, t):
    fondo(ctx, t, oscuro=0.55 * (1 - prog(t, T_CRANEO - 0.05, 0.2)))
    ox, oy = perfil_mundo(QX, QY, QS, COCLEA)
    ctx.save()
    zcam = lerp(1.0, 1.05, prog(t, T_SUBE, T_CRANEO - T_SUBE))
    zcam *= 1 + 0.06 * (1 - ease(clamp((t - T_CRANEO) / 0.35), "out")) * (t >= T_CRANEO)
    zp = prog(t, T_ES10 - 0.05, 0.9, "inout")
    zoom(ctx, zcam * lerp(1.0, 1.75, zp), lerp(540, ox, zp), lerp(860, oy, zp))
    craneo = t >= T_CRANEO - 0.05
    brillo = prog(t, T_CRANEO - 0.05, 0.15) * (0.55 + 0.45 * abs(math.sin(t * 7)))
    perfil(ctx, QX, QY, QS, t, oscuro=0.92, xray=1.0 if craneo else 0.25, brillo=brillo if craneo else 0.0,
           vib=0.8 if craneo else 0.0, oreja=0.8 * prog(t, T_RODEA - 0.1, 0.25) * (1 - prog(t, T_CRANEO, 0.2)))
    # el pulso sube por la mandíbula hasta el oído
    q = prog(t, T_SUBE, T_OIDO8 - T_SUBE + 0.25, "inout")
    if not craneo and q < 1:
        pts = tuple(perfil_mundo(QX, QY, QS, p) for p in PULSO)
        x, y, ang = bez(*pts, q)
        g = cairo.RadialGradient(x, y, 6, x, y, 110)
        g.add_color_stop_rgba(0, *ORO, 0.95)
        g.add_color_stop_rgba(1, *ORO, 0)
        ctx.set_source(g)
        ctx.arc(x, y, 110, 0, TAU)
        ctx.fill()
        # estela
        for j in range(1, 7):
            xx, yy, _ = bez(*pts, max(0, q - j * 0.04))
            ctx.arc(xx, yy, 18 - 2 * j, 0, TAU)
            ctx.set_source_rgba(*ORO, 0.7 - 0.09 * j)
            ctx.fill()
    if craneo:
        # el cráneo vibra: anillos alrededor
        anillos(ctx, *perfil_mundo(QX, QY, QS, (-20, -40)), t, 330, col=ORO, n=3, periodo=0.7,
                a=0.7 * (1 - zp * 0.7), w=10)
        destello(ctx, *perfil_mundo(QX, QY, QS, (-20, -60)), 360, t, T_CRANEO - 0.05, 0.5)
    # el parlante pegado al oído
    if t >= T_PARLANTE - 0.15:
        k = 0.5 + 0.5 * math.sin(t * (18 if t < T_SUMA else 30))
        sp = pop(t, T_PARLANTE - 0.15, 0.35)
        px, py = ox + 95, oy - 10
        anillos(ctx, ox, oy, t, 70, col=ORO, n=2, periodo=0.5, a=sp, w=5)
        parlante(ctx, px + 20, py, 0.58 * sp, k=k)
    ctx.restore()
    if t < T_CRANEO:
        signo(ctx, "?", 840, 420, 200, t, T_DURO - 0.15)
    kartel(ctx, "CRÁNEO", 540, 330, 96, t, T_CRANEO_W - 0.05, T_ES10 + 0.4, box=AMARILLO)
    if t >= T_SUMA - 0.15:
        f = lerp(0.2, 0.95, prog(t, T_SUMA, T_GRAVES - T_SUMA + 0.4, "inout"))
        perilla(ctx, 845, 1235, 0.8 * pop(t, T_SUMA - 0.15, 0.3), f, "BAJOS")


# ------------------------------------------------------------------ 6. micrófono: no tiene tus huesos; capta el aire; aguda
T_EL11 = b(11)
T_MICRO = b(11, "microfono")
T_NO11 = b(11, "no")
T_HUESOS11 = b(11, "huesos")
T_CAPTA = b(12)
T_AIRE = b(12, "aire")
T_LO12 = b(12, "lo")
T_GENTE = b(12, "gente")
T_SIN13 = b(13)
T_HUESOS13 = b(13, "huesos")
T_AGUDA = b(13, "aguda")


def onda_linea(ctx, x0, x1, y, amp, ciclos, fase, col, w):
    n = 220
    for k in range(n + 1):
        q = k / n
        xx = lerp(x0, x1, q)
        env = math.sin(q * math.pi) ** 0.6
        yy = y + amp * env * math.sin(q * ciclos * TAU + fase)
        (ctx.move_to if k == 0 else ctx.line_to)(xx, yy)
    trazo(ctx, INK, w + 8)
    for k in range(n + 1):
        q = k / n
        xx = lerp(x0, x1, q)
        env = math.sin(q * math.pi) ** 0.6
        yy = y + amp * env * math.sin(q * ciclos * TAU + fase)
        (ctx.move_to if k == 0 else ctx.line_to)(xx, yy)
    trazo(ctx, col, w)


def d_micro(ctx, t):
    fondo(ctx, t)
    zoom(ctx, lerp(1.0, 1.05, prog(t, T_EL11, b(14) - T_EL11)), 540, 860)
    # fase A: el micrófono solo, se encoge de hombros
    abre = prog(t, T_CAPTA - 0.1, 0.5, "inout")            # pasa a la escena del aire
    baja = prog(t, T_SIN13 - 0.1, 0.45, "inout")            # pasa a la onda aguda
    mic_x = lerp(540, 560, abre)
    mic_y = lerp(860, 900, abre) - 1600 * baja
    mic_s = lerp(1.55, 0.85, abre) * pop(t, T_EL11 - 0.05, 0.35)
    enc = prog(t, T_NO11 - 0.05, 0.25) * (1 - prog(t, T_CAPTA - 0.1, 0.3))
    microfono(ctx, mic_x, mic_y, mic_s, t, encoge=enc, cara_b="flat" if enc > 0.5 else "smile",
              ceja="up" if enc > 0.5 else None, look=(-0.6, 0) if abre > 0.5 else (0, 0))
    if t < T_CAPTA + 0.3:
        a = pop(t, T_HUESOS11 - 0.1, 0.3) * sale(t, T_CAPTA)
        if a > 0.01:
            calavera(ctx, 840, 520, 1.9 * a)
            cruz_roja(ctx, 840, 530, 0.85 * a)
    # fase B: el muñequito habla; las ondas blancas van por el aire al micrófono y a la gente
    if abre > 0.01:
        off = -1600 * baja
        sx = lerp(-200, 190, abre)
        muneco(ctx, sx, 860 + off, 135, boca="o" if hablando(t, T_CAPTA, T_SIN13) else "smile", s=1.0)
        if t >= T_CAPTA + 0.15:
            p = ((t - T_CAPTA) * 0.9) % 1.3
            ondas(ctx, sx + 150, 860 + off, mic_x - 130, mic_y - 100, p, a=abre, n=3, col=BLANCO)
        kartel(ctx, "AIRE", 380, 620 + off, 70, t, T_AIRE - 0.1, box=BLANCO)
        amigos = ((880, 520, PIELES[3], PELOS[1], REMERAS[0]), (880, 1150, PIELES[4], PELOS[3], REMERAS[3]))
        for k, (ax, ay, pi, pe, re) in enumerate(amigos):
            sa = pop(t, T_LO12 - 0.1 + 0.15 * k, 0.35)
            if sa > 0.01:
                muneco(ctx, ax, ay + off, 120, s=sa, piel=pi, pelo=pe, remera=re, look=(-0.8, 0),
                       boca="smile")
                p = ((t - T_LO12) * 0.9 + 0.3 * k) % 1.3
                ondas(ctx, sx + 150, 860 + off, ax - 130, ay + off, p, a=sa * abre, n=3, col=BLANCO)
                if t >= T_GENTE - 0.1:
                    tilde(ctx, ax + 120, ay - 120 + off, pop(t, T_GENTE - 0.1 + 0.1 * k, 0.3))
    # fase C: sin huesos -> la onda se afina
    if baja > 0.01:
        off = 1100 * (1 - baja)
        fr = lerp(0.95, 0.05, prog(t, T_HUESOS13 - 0.1, 0.6, "inout"))
        perilla(ctx, 540, 520 + off, 0.95, fr, "BAJOS")
        amp = lerp(150, 55, 1 - fr)
        ciclos = lerp(2.5, 9.0, 1 - fr)
        w = lerp(30, 11, 1 - fr)
        onda_linea(ctx, 110, 970, 1080 + off, amp, ciclos, t * 7, BLANCO, w)
        kartel(ctx, "AGUDA", 540, 1290 + off, 80, t, T_AGUDA - 0.1, box=AMARILLO)
        microfono(ctx, 160, 1080 + off - 190, 0.5, t)


# ------------------------------------------------------------------ 7. estudio: 80 personas
T_EN14 = b(14)
T_ESTUDIO = b(14, "estudio")
T_80 = b(14, "80")
T_CALIF = b(14, "calificaron")
T_VOCES14 = b(14, "voces")
COLS, FILAS = 8, 10


def d_estudio(ctx, t):
    fondo(ctx, t)
    deriva(ctx, t, T_EN14, b(15), 1.0, 1.09, 540, 820)
    x0, y0, dx, dy = 135, 360, 115, 98
    for f in range(FILAS):
        for c in range(COLS):
            k = f * COLS + c
            t0 = T_ESTUDIO - 0.1 + (f + c) * 0.055
            s = pop(t, t0, 0.3)
            if s <= 0.01:
                continue
            x, y = x0 + c * dx, y0 + f * dy
            rr = P.rng(k)
            piel = PIELES[k % 5]
            pelo = PELOS[(k * 3) % 5]
            bob = 3 * math.sin(t * 4 + k)
            cabeza(ctx, x, y + bob, 40 * s, piel=piel, pelo=pelo, boca="smile")
            auriculares(ctx, x, y + bob, 40 * s, col=REMERAS[(k * 7) % 5])
            if t >= T_CALIF:
                ts = T_CALIF + (rr.random() * 1.2)
                st = pop(t, ts, 0.25)
                if st > 0.01:
                    estrella(ctx, x + 30, y - 38 + bob, 18 * st, AMARILLO, rot=0.3 * math.sin(t * 3 + k))
    n = int(round(80 * prog(t, T_ESTUDIO, T_80 - T_ESTUDIO + 0.25, "out")))
    if t >= T_ESTUDIO - 0.1:
        kartel(ctx, f"{n} PERSONAS", 540, 225, 86, t, T_ESTUDIO - 0.1, box=AMARILLO)
    if t >= T_VOCES14 - 0.1:
        # notas musicales de "voces grabadas" que pasan
        for j in range(4):
            q = ((t - T_VOCES14) * 0.6 + j / 4) % 1
            xx = lerp(1150, -80, q)
            tarjeta_audio(ctx, xx, 1325, 0.5 * pop(t, T_VOCES14 - 0.1 + 0.1 * j, 0.3), t)


# ------------------------------------------------------------------ 8. una de esas voces era la suya; su nota
T_SIN15 = b(15)
T_AVISARLES = b(15, "avisarles")
T_ESTABA = b(15, "estaba")
T_SUYA15 = b(15, "suya")
T_PERO16 = b(16)
T_CALIF16 = b(16, "calificaron")
T_MEJOR = b(16, "mejor")
T_DEMAS = b(16, "demas")
LX, LY, LR = 540, 1000, 200


def d_escucha(ctx, t):
    fondo(ctx, t)
    deriva(ctx, t, T_SIN15, b(17), 1.0, 1.06, 540, 860)
    barras = prog(t, T_PERO16 - 0.1, 0.5, "inout")
    # el muñequito con auriculares escucha (en las barras se achica y sube a su barra)
    mx = lerp(LX, 300, barras)
    my = lerp(LY, 370, barras)
    ms = lerp(1.0, 0.42, barras) * pop(t, T_SIN15 - 0.05, 0.35)
    ojos = "happy" if t >= T_MEJOR else "open"
    muneco(ctx, mx, my, LR, boca="grin" if t >= T_MEJOR else "smile", ojos=ojos, look=(0, -0.7) if barras < 0.5 else (0, 0),
           auris=True, s=ms)
    # carrusel de audios arriba: pasan de derecha a izquierda y frena en el suyo (j = 0), en el centro
    if barras < 0.99:
        a_c = 1 - barras
        e = ease(clamp((t - T_SIN15) / (T_ESTABA + 0.15 - T_SIN15)), "out")
        shift = lerp(-6.0, 0.0, e)
        for j in range(-7, 4):
            xx = 540 + (j - shift) * 400
            if -300 < xx < 1380:
                suya = j == 0 and t >= T_SUYA15 - 0.2
                tarjeta_audio(ctx, xx, 470, 0.95 * a_c * pop(t, T_SIN15, 0.3), t,
                              avatar="suya" if suya else None, brillo=prog(t, T_SUYA15 - 0.2, 0.3) if suya else 0.0)
    if t < T_PERO16:
        kartel(ctx, "SIN AVISARLES", 540, 250, 62, t, T_AVISARLES - 0.1, T_ESTABA, box=BLANCO)
    # barras: su nota contra la de los demás
    if barras > 0.01:
        llen = prog(t, T_CALIF16, 0.8, "out")
        h, y0 = 600, 560
        medidor(ctx, 300, y0, h, 0.92 * llen, ORO, s=barras)
        medidor(ctx, 780, y0, h, 0.55 * llen, GRIS2, s=barras)
        texto(ctx, "ÉL", 300, y0 + h + 70, 72, fill=BLANCO, alpha=barras)
        texto(ctx, "LOS DEMÁS", 780, y0 + h + 70, 72, fill=BLANCO, alpha=barras)
        for k in range(3):
            cabeza(ctx, 700 + k * 80, 470 - 20 * (k == 1), 46 * barras, piel=PIELES[k + 2], pelo=PELOS[k + 1],
                   boca="flat", ojos="open")
        if t >= T_MEJOR - 0.1:
            estrella(ctx, 450, y0 + h * 0.08 + 20, 70 * pop(t, T_MEJOR - 0.1, 0.35), AMARILLO,
                     rot=0.2 * math.sin(t * 4))
            destello(ctx, 450, y0 + h * 0.08 + 20, 150, t, T_MEJOR - 0.1, 0.5)


# ------------------------------------------------------------------ 9. les gustaba... mientras no supieran que era suya
T_LES = b(17)
T_GUSTABA = b(17, "gustaba")
T_MIENTRAS = b(17, "mientras")
T_SUPIERAN = b(17, "supieran")
T_ERA = b(17, "era")
T_SUYA17 = b(17, "suya")


def d_gusta(ctx, t):
    fondo(ctx, t)
    deriva(ctx, t, T_LES, b(18), 1.0, 1.1, 540, 900)
    sabe = t >= T_SUYA17 - 0.12
    temblor = jitter(t, 5, 50) if sabe else 0.0
    if sabe:
        muneco(ctx, 540 + temblor, 1000, 210, boca="wavy", ojos="wide", ceja="worried", look=(0.6, -0.4),
               auris=True, rubor=True)
        # cachetes colorados
        for sx in (-1, 1):
            elipse(ctx, 540 + temblor + sx * 115, 1060, 50, 26)
            ctx.set_source_rgba(1, 0.25, 0.25, 0.55 * prog(t, T_SUYA17 - 0.12, 0.2))
            ctx.fill()
        gota_sudor(ctx, 540 + 205, 880, pop(t, T_SUYA17, 0.3))
    else:
        muneco(ctx, 540, 1000 + 8 * math.sin(t * 5), 210, boca="grin", ojos="happy", auris=True)
    # corazones que suben mientras le gusta
    if t >= T_GUSTABA - 0.1:
        for j in range(5):
            t0 = T_GUSTABA - 0.1 + j * 0.25
            if t < t0:
                continue
            q = (t - t0) / 1.6
            if sabe:
                a = 1 - prog(t, T_SUYA17 - 0.12, 0.2)
            else:
                a = 1.0
            a *= clamp(1 - q)
            if a <= 0.01:
                continue
            xx = 540 + (j % 2 * 2 - 1) * (170 + 40 * j) + 20 * math.sin(t * 3 + j)
            yy = 780 - 360 * q
            corazon(ctx, xx, yy, 0.55 * pop(t, t0, 0.3), a=a)
    # la tarjeta de su voz: primero "?", al final cae el sello
    tarjeta_audio(ctx, 540, 420, 1.15 * pop(t, T_LES - 0.05, 0.3), t, avatar="suya" if sabe else None,
                  brillo=0.6 if not sabe else 0.0)
    if t >= T_MIENTRAS - 0.1:
        signo(ctx, "?", 800, 300, 150, t, T_MIENTRAS - 0.1, T_SUYA17 - 0.2)
    sello(ctx, "ES TU VOZ", 560, 430, 74, t, T_SUYA17 - 0.12, rot=-8, col=ROJO)


# ------------------------------------------------------------------ escenas
ESCENAS = [
    (0.0, d_apertura),
    (T_P2, d_pregunta),
    (T_TAPATE, d_oidos),
    (T_PON, d_garganta),
    (T_SUBE, d_perfil),
    (T_EL11, d_micro),
    (T_EN14, d_estudio),
    (T_SIN15, d_escucha),
    (T_LES, d_gusta),
    (b(18), d_cierre),
]
XF = 0.18
CORTES_SECOS = {T_SUBE}


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
    sin_punch = i == len(ESCENAS) - 1          # el cierre termina igual al inicio
    if i > 0 and dt < XF and t0 not in CORTES_SECOS:
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

    # 1. apertura
    ev(T_LA1 - 0.05, "pop", 0.4)
    ev(T_AUDIOS - 0.05, "pop", 0.35)
    ev(T_ODIAS - 0.1, "plop", 0.35)
    # 2. pregunta
    ev(T_P2, "whoosh", 0.3)
    ev(T_TU2 - 0.2, "pop", 0.45)
    # 3. oídos
    ev(T_TAPATE - 0.05, "pop", 0.35)
    ev(T_OIDOS - 0.05, "clic", 0.35)
    ev(T_FUERTE - 0.1, "golpe", 0.45)
    ev(T_BARRIL - 0.1, "whoosh", 0.3)
    ev(T_BARRIL + 0.3, "clunk", 0.45)
    ev(T_ENTRA - 0.1, "pop", 0.35)
    ev(T_ENTRA, "pop", 0.3)
    ev(T_OREJAS - 0.2, "pop", 0.4)
    # 4. garganta
    ev(T_PON - 0.05, "whoosh", 0.3)
    ev(T_MANO + 0.2, "clic", 0.3)
    for j in range(6):
        ev(T_VIBRA - 0.05 + 0.05 * j, "tick", 0.15, f=180 + 20 * j, d=0.04)
    ev(T_VIBRA - 0.05, "golpe", 0.4)
    ev(T_QUEDA, "subida", 0.3)
    # 5. perfil
    ev(T_DURO - 0.15, "pop", 0.35)
    ev(T_RODEA, "tick", 0.25, f=900, d=0.05)
    ev(T_CRANEO - 0.05, "golpe", 0.55)
    ev(T_CRANEO_W - 0.05, "ding", 0.35)
    ev(T_PARLANTE - 0.15, "pop", 0.4)
    ev(T_SUMA - 0.15, "clic", 0.35)
    # 6. micrófono
    ev(T_EL11 - 0.05, "pop", 0.4)
    ev(T_NO11 - 0.05, "plop", 0.3)
    ev(T_HUESOS11 - 0.1, "clunk", 0.4)
    ev(T_CAPTA - 0.1, "whoosh", 0.3)
    ev(T_AIRE - 0.1, "pop", 0.3)
    ev(T_LO12 - 0.1, "pop", 0.3)
    ev(T_LO12 + 0.05, "pop", 0.3)
    ev(T_GENTE - 0.1, "ding", 0.3)
    ev(T_SIN13 - 0.1, "whoosh", 0.3)
    ev(T_HUESOS13 - 0.1, "clic", 0.35)
    ev(T_AGUDA - 0.1, "pop", 0.4)
    # 7. estudio
    for j in range(8):
        ev(T_ESTUDIO - 0.1 + j * 0.12, "tick", 0.13, f=900 + 70 * j, d=0.03)
    ev(T_80 - 0.05, "ding", 0.35)
    for j in range(6):
        ev(T_CALIF + 0.2 * j, "tick", 0.15, f=1300 + 50 * j, d=0.03)
    # 8. escucha
    ev(T_SIN15 - 0.05, "pop", 0.35)
    ev(T_ESTABA - 0.3, "frenada", 0.25)
    ev(T_SUYA15 - 0.2, "ding", 0.4)
    ev(T_PERO16 - 0.1, "whoosh", 0.3)
    ev(T_MEJOR - 0.1, "golpe", 0.4)
    ev(T_MEJOR, "ding", 0.3)
    # 9. gusta
    for j in range(5):
        ev(T_GUSTABA - 0.1 + 0.25 * j, "pop", 0.18)
    ev(T_MIENTRAS - 0.1, "pop", 0.35)
    ev(T_SUYA17 - 0.12, "golpe", 0.55)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "por_que_odias_tu_voz_grabada.mp4"))
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

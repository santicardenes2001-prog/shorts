"""Short "¿Por qué los bostezos se contagian?" — animación procedural (armazón de tierra.py).

Estilo del canal: fondo azul con puntos, cosas con cara (la almohada, el bostecito amarillo, los animales, el libro)
y subtítulos palabra por palabra. Vos sale solo en la apertura y el cierre vuelve al primer cuadro: el cuadro de
TOTAL es igual al de 0 salvo la barra de progreso, que vuelve a empezar como cuando el video se repite.

Hilo que se repite: la boca de bostezo (`cara(..., k=...)`) y las ondas que viajan de una boca a otra (el contagio).

    python proyectos/bostezo/bostezo.py --hoja 0,3,6      # hoja de fotogramas -> proyectos/bostezo/fotos/hoja.png
    python proyectos/bostezo/bostezo.py --probar
    python proyectos/bostezo/bostezo.py                   # render -> salidas/por_que_los_bostezos_se_contagian.mp4
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
           os.path.join(ROOT, "proyectos", "tierra")):
    sys.path.insert(0, _p)
import kit  # noqa: E402
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, cartel, clamp, ease, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rrect, texto)
from picante import carita, fondo_azul  # noqa: E402
from tierra import (CREMA, ROJO, VERDE, alfa, cruz_roja, elipse, en, kartel, rellena, sale, sello,  # noqa: E402
                    signo, tilde, trazo, zetas, zoom)

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Antes de que termine este video, vas a bostezar.",                     # b0
    "No hace falta que tengas sueño.",                                      # b1
    "Alcanza con ver a alguien hacerlo.",                                   # b2
    "¿Por qué tu cuerpo copia un bostezo ajeno?",                           # b3
    "Bostezar lo hace casi cualquier animal.",                              # b4
    "Hasta las serpientes bostezan.",                                       # b5
    "Pero contagiarse es rarísimo.",                                        # b6
    "Solo se comprobó en humanos, chimpancés y, quizás, perros.",           # b7
    "Ni siquiera hace falta verlo.",                                        # b8
    "Leer sobre bostezos puede hacerte bostezar.",                          # b9
    "Los bebés, en cambio, no se contagian.",                               # b10
    "El contagio aparece cerca de los 4 años.",                             # b11
    "Justo cuando empiezas a entender lo que sienten los demás.",           # b12
    "Por eso, muchos científicos lo ligan a la empatía.",                   # b13
    "Te contagias más de tu familia que de un extraño.",                    # b14
    "Tu perro también: se contagia más de ti que de un desconocido.",       # b15
    "Pero un estudio grande no encontró esa relación.",                     # b16
    "Hoy nadie sabe del todo por qué pasa.",                                # b17
    "Lo seguro es que a la mitad de los adultos le funciona.",              # b18
    "Si todavía no bostezaste, no te preocupes.",                           # b19
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
BOCA = hx(kit.P["boca"])
LENGUA = hx(kit.P["lengua"])
LAGRIMA = hx("#8FD3FF")
ROJO_BARRA = hx("#FF3B3B")
PANEL = hx("#1B2347")
ALMOHADA = hx("#F4F1FF")
ALMOHADA_SOMBRA = hx("#D6D0F0")
NARANJA = hx("#FF8F3F")
NARANJA_OSC = hx("#E06A1A")
AZUL_P = hx("#4FB6F5")
AZUL_P2 = hx("#2A8FD6")
PICO = hx("#FFB020")
VERDE_S = hx("#46C281")
VERDE_S2 = hx("#2E9E62")
MONO = hx("#5A3A26")
MONO_CARA = hx("#E8C49A")
PERRO = hx("#D9A066")
PERRO_OREJA = hx("#8A5A2B")
PERRO_HOCICO = hx("#F3D9B1")
PAGINA = hx("#FFF7E8")
LIBRO = hx("#E5383B")
TORTA = hx("#FF8FA8")
TORTA2 = hx("#FFD1DC")
MADERA = hx("#B8662B")
GRIS = hx("#C9D1DE")
PIELES = [hx("#F8C9A2"), hx("#E0A57E"), hx("#B97A55"), hx("#F2D0B5"), hx("#8D5A3C")]
PELOS = [hx("#3B2B23"), hx("#1F1A18"), hx("#C77A2E"), hx("#E8C35A"), hx("#6B4A2F")]
REMERAS = [hx("#FF5D5D"), hx("#46C281"), hx("#FFD23F"), hx("#7A5CFF"), hx("#FF8FA8")]


# ------------------------------------------------------------------ ayudas
def fondo(ctx, t, oscuro=0.0):
    fondo_azul(ctx, t * KF)
    if oscuro > 0:
        ctx.set_source_rgba(0.027, 0.043, 0.11, oscuro)
        ctx.paint()


def bostezo_k(t, t0, d=1.5, sube=0.4, baja=0.45):
    """Cuánto está abierta la boca (0..1) en un bostezo que empieza en t0 y dura d."""
    if t < t0 or t > t0 + d:
        return 0.0
    if t < t0 + sube:
        return ease(clamp((t - t0) / sube), "out")
    if t > t0 + d - baja:
        return 1 - ease(clamp((t - (t0 + d - baja)) / baja), "in")
    return 1.0


def boca_bostezo(ctx, x, y, r, k):
    """Boca de bostezo: (x, y) = borde de arriba; k = 0..1."""
    rx, ry = (16 + 8 * k) * r, (6 + 30 * k) * r
    cy = y + ry
    elipse(ctx, x, cy, rx, ry)
    ctx.set_source_rgb(*BOCA)
    ctx.fill()
    ctx.save()
    elipse(ctx, x, cy, rx, ry)
    ctx.clip()
    elipse(ctx, x, cy + ry * 0.75, rx * 0.75, ry * 0.42)
    ctx.set_source_rgb(*LENGUA)
    ctx.fill()
    ctx.restore()
    elipse(ctx, x, cy, rx, ry)
    trazo(ctx, INK, 6 * r)


def lagrimita(ctx, x, y, r, a):
    if a <= 0.01:
        return
    ctx.move_to(x, y - 12 * r)
    ctx.curve_to(x + 9 * r, y, x + 9 * r, y + 10 * r, x, y + 10 * r)
    ctx.curve_to(x - 9 * r, y + 10 * r, x - 9 * r, y, x, y - 12 * r)
    ctx.close_path()
    rellena(ctx, LAGRIMA, 3 * r, a=a)


def cara(ctx, x, y, sep, r, k=0.0, ojos="open", boca="smile", ceja=None, look=(0, 0), rubor=False, dy_boca=None,
         sin_boca=False):
    """Cara del canal; con k > 0 bosteza: cierra los ojos, sube las cejas, abre la boca y larga una lágrima."""
    k = clamp(k)
    yb = y + (dy_boca if dy_boca is not None else 40 * r)
    if k < 0.03:
        if sin_boca:
            carita(ctx, x, y, sep, r, ojos=ojos, boca="ninguna", ceja=ceja, look=look, rubor=rubor)
        else:
            carita(ctx, x, y, sep, r, ojos=ojos, boca=boca, ceja=ceja, look=look, rubor=rubor,
                   dy_boca=None if dy_boca is None else dy_boca - 4 * r)
        return
    oj = "closed" if k > 0.35 else ojos
    dy = -5 * r * k
    K.ojo(ctx, x - sep / 2, y + dy, r, oj, look)
    K.ojo(ctx, x + sep / 2, y + dy, r, oj, look)
    if k > 0.35:
        K.cejas(ctx, x, y - 38 * r, sep, "up", r)
    if not sin_boca:
        boca_bostezo(ctx, x, yb - 6 * r, r, k)
    lagrimita(ctx, x + sep / 2 + 20 * r, y + 18 * r, r, clamp((k - 0.7) / 0.3))


def ondas(ctx, x0, y0, x1, y1, p, a=1.0, n=3, col=BLANCO):
    """Ondas de bostezo que viajan de (x0, y0) a (x1, y1); p = 0..1 (si p > 1, rebotan y vuelven)."""
    if a <= 0.01:
        return
    ang = math.atan2(y1 - y0, x1 - x0)
    for j in range(n):
        q = p - 0.12 * j
        vuelta = q > 1
        if vuelta:
            q = 2 - q
        if not (0 < q < 1):
            continue
        x, y = lerp(x0, x1, q), lerp(y0, y1, q)
        aa = a * min(1, q * 5, (1 - q) * 5 + 0.3)
        with en(ctx, x, y, 1.0, ang + (math.pi if vuelta else 0)):
            ctx.arc(-30, 0, 46 - 8 * j, -0.75, 0.75)
            trazo(ctx, INK, 15, aa)
            ctx.arc(-30, 0, 46 - 8 * j, -0.75, 0.75)
            trazo(ctx, col, 8, aa)


def corazon(ctx, x, y, s, col=ROJO, a=1.0):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.move_to(0, 62)
        ctx.curve_to(-120, -14, -62, -96, 0, -42)
        ctx.curve_to(62, -96, 120, -14, 0, 62)
        ctx.close_path()
        rellena(ctx, col, 9, a=a)
        ctx.move_to(-46, -36)
        ctx.curve_to(-62, -26, -66, -8, -58, 6)
        trazo(ctx, BLANCO, 9, 0.55 * a)


def medidor(ctx, x, y0, h, frac, col, s=1.0):
    """Barra vertical de "cuánto se contagia"; (x, y0) = centro de arriba."""
    if s <= 0.01:
        return
    with en(ctx, x, y0 + h / 2, s):
        w = 124
        rrect(ctx, -w / 2, -h / 2, w, h, 26)
        rellena(ctx, PANEL, 8)
        fh = (h - 20) * clamp(frac)
        if fh > 2:
            rrect(ctx, -w / 2 + 10, h / 2 - 10 - fh, w - 20, fh, 18)
            ctx.set_source_rgb(*col)
            ctx.fill()


def bostecito(ctx, x, y, R, k=0.0, look=(0, 0), s=1.0):
    """El bostezo hecho personaje: una bolita amarilla con cara."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.arc(0, 0, R, 0, TAU)
        rellena(ctx, AMARILLO, 7 * R / 90)
        cara(ctx, 0, -0.12 * R, 0.62 * R, R / 110, k=k, look=look)


# ------------------------------------------------------------------ personajes
VOS_POSES = {
    "neutral": dict(),
    "mira": dict(look=(1.0, 0.15)),
    "estira": dict(eyes="closed", brows="up", mouth_kind="yawn", arm_kind="up"),
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


def almohada(ctx, x, y, s=1.0, k=0.0, look=(0, 0), ojos="open", boca="smile", ceja=None, rot=0.0):
    """Almohada con cara; (x, y) = centro."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s, rot):
        w, h = 170, 115
        ctx.move_to(-w - 18, -h - 14)
        ctx.curve_to(-60, -h + 12, 60, -h + 12, w + 18, -h - 14)
        ctx.curve_to(w - 14, -40, w - 14, 40, w + 18, h + 14)
        ctx.curve_to(60, h - 12, -60, h - 12, -w - 18, h + 14)
        ctx.curve_to(-w + 14, 40, -w + 14, -40, -w - 18, -h - 14)
        ctx.close_path()
        rellena(ctx, ALMOHADA, 9)
        ctx.move_to(-w + 10, h - 30)
        ctx.curve_to(-60, h - 46, 60, h - 46, w - 10, h - 30)
        trazo(ctx, ALMOHADA_SOMBRA, 8)
        cara(ctx, 0, -26, 116, 1.3, k=k, ojos=ojos, boca=boca, ceja=ceja, look=look, rubor=True)


def cabeza(ctx, x, y, R, k=0.0, piel=PIELES[0], pelo=PELOS[0], estilo="corto", look=(0, 0), ojos="open",
           boca="smile", ceja=None, lentes=False, sombrero=False, rubor=True, s=1.0):
    """Cabeza humana genérica (no es Vos); (x, y) = centro."""
    if s <= 0.01 or R < 2:
        return
    with en(ctx, x, y, s):
        if estilo == "largo":
            rrect(ctx, -1.08 * R, -0.5 * R, 2.16 * R, 1.55 * R, 0.5 * R)
            rellena(ctx, pelo, 7)
        for sx in (-1, 1):
            ctx.arc(sx * R * 0.98, 0.08 * R, 0.2 * R, 0, TAU)
            rellena(ctx, piel, 7)
        ctx.arc(0, 0, R, 0, TAU)
        rellena(ctx, piel, 7)
        if estilo in ("corto", "largo"):
            ctx.save()
            ctx.arc(0, 0, R, 0, TAU)
            ctx.clip()
            elipse(ctx, 0, -0.78 * R, 1.12 * R, 0.6 * R)
            ctx.set_source_rgb(*pelo)
            ctx.fill()
            ctx.restore()
            ctx.arc(0, 0, R, math.pi * 1.08, math.pi * 1.92)
            trazo(ctx, INK, 7)
        elif estilo == "bebe":
            ctx.move_to(0, -R + 4)
            ctx.curve_to(-0.05 * R, -1.32 * R, 0.32 * R, -1.32 * R, 0.24 * R, -1.08 * R)
            trazo(ctx, INK, 9)
            ctx.move_to(0, -R + 4)
            ctx.curve_to(-0.05 * R, -1.32 * R, 0.32 * R, -1.32 * R, 0.24 * R, -1.08 * R)
            trazo(ctx, pelo, 5)
        r = R / 150
        cara(ctx, 0, 0.08 * R, 0.6 * R, r, k=k, look=look, ojos=ojos, boca=boca, ceja=ceja, rubor=rubor)
        if lentes and k < 0.35:
            for sx in (-1, 1):
                rrect(ctx, sx * 0.3 * R - 0.24 * R, -0.06 * R, 0.48 * R, 0.3 * R, 0.1 * R)
                rellena(ctx, INK, 5)
            ctx.move_to(-0.06 * R, 0.0)
            ctx.line_to(0.06 * R, 0.0)
            trazo(ctx, INK, 7)
        if sombrero:
            elipse(ctx, 0, -0.72 * R, 1.25 * R, 0.2 * R)
            rellena(ctx, hx("#3A3A4A"), 7)
            rrect(ctx, -0.7 * R, -1.42 * R, 1.4 * R, 0.72 * R, 0.16 * R)
            rellena(ctx, hx("#3A3A4A"), 7)
            ctx.rectangle(-0.7 * R, -0.9 * R, 1.4 * R, 0.14 * R)
            ctx.set_source_rgb(*ROJO)
            ctx.fill()


def torso(ctx, x, y, R, col, s=1.0):
    """Cuerpito (remera) debajo de una cabeza de radio R centrada en (x, y)."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        rrect(ctx, -0.82 * R, 0.82 * R, 1.64 * R, 1.25 * R, 0.5 * R)
        rellena(ctx, col, 7)


def mono(ctx, x, y, R, k=0.0, look=(0, 0), s=1.0):
    """Cabeza de chimpancé."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        for sx in (-1, 1):
            ctx.arc(sx * 0.98 * R, -0.02 * R, 0.3 * R, 0, TAU)
            rellena(ctx, MONO, 7)
            ctx.arc(sx * 0.98 * R, -0.02 * R, 0.17 * R, 0, TAU)
            ctx.set_source_rgb(*MONO_CARA)
            ctx.fill()
        ctx.arc(0, 0, R, 0, TAU)
        rellena(ctx, MONO, 7)
        # la cara clara: dos círculos para los ojos y el hocico abajo
        for sx in (-1, 1):
            ctx.new_sub_path()
            ctx.arc(sx * 0.26 * R, -0.16 * R, 0.34 * R, 0, TAU)
        ctx.set_source_rgb(*MONO_CARA)
        ctx.fill()
        elipse(ctx, 0, 0.3 * R, 0.56 * R, 0.42 * R)
        rellena(ctx, MONO_CARA, 7)
        # cejas de hueso
        ctx.move_to(-0.56 * R, -0.42 * R)
        ctx.curve_to(-0.3 * R, -0.56 * R, 0.3 * R, -0.56 * R, 0.56 * R, -0.42 * R)
        trazo(ctx, MONO, 0.1 * R)
        r = R / 150
        for sx in (-1, 1):
            ctx.arc(sx * 0.07 * R, 0.12 * R, 0.035 * R, 0, TAU)
            ctx.set_source_rgb(*INK)
            ctx.fill()
        cara(ctx, 0, -0.16 * R, 0.52 * R, r, k=k, look=look, dy_boca=0.46 * R)


def perro(ctx, x, y, R, k=0.0, look=(0, 0), s=1.0, ojos="open", boca="smile", rot=0.0):
    """Cabeza de perro de orejas caídas."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s, rot):
        for sx in (-1, 1):
            with en(ctx, sx * 0.86 * R, 0.1 * R, 1.0, -sx * 0.22):
                elipse(ctx, 0, 0, 0.3 * R, 0.62 * R)
                rellena(ctx, PERRO_OREJA, 7)
        ctx.arc(0, 0, R, 0, TAU)
        rellena(ctx, PERRO, 7)
        elipse(ctx, 0, 0.38 * R, 0.5 * R, 0.36 * R)
        rellena(ctx, PERRO_HOCICO, 7)
        r = R / 150
        cara(ctx, 0, -0.2 * R, 0.6 * R, r, k=k, look=look, ojos=ojos, boca=boca, dy_boca=0.56 * R)
        elipse(ctx, 0, 0.2 * R, 0.16 * R, 0.11 * R)
        rellena(ctx, INK, 4)
        if k > 0.4:
            # la lengua que se asoma
            elipse(ctx, 0, 0.62 * R + 0.3 * R * k, 0.12 * R, 0.1 * R * k)
            rellena(ctx, LENGUA, 5)


def pez(ctx, x, y, s=1.0, k=0.0, look=(0, 0)):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.move_to(-120, 0)
        ctx.line_to(-210, -72)
        ctx.curve_to(-196, 0, -196, 0, -210, 72)
        ctx.close_path()
        rellena(ctx, NARANJA_OSC, 7)
        ctx.move_to(-40, -78)
        ctx.curve_to(-10, -140, 50, -130, 60, -82)
        rellena(ctx, NARANJA_OSC, 7)
        elipse(ctx, 0, 0, 150, 96)
        rellena(ctx, NARANJA, 8)
        for dx in (-70, -36):
            ctx.arc(dx, 0, 60, -0.9, 0.9)
            trazo(ctx, NARANJA_OSC, 6)
        cara(ctx, 62, -18, 62, 0.7, k=k, look=look)


def pajaro(ctx, x, y, s=1.0, k=0.0, look=(0, 0)):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        for sx in (-14, 22):
            ctx.move_to(sx, 96)
            ctx.line_to(sx, 140)
            trazo(ctx, PICO, 9)
        ctx.arc(0, 0, 112, 0, TAU)
        rellena(ctx, AZUL_P, 8)
        elipse(ctx, 6, 46, 72, 56)
        ctx.set_source_rgb(*hx("#CDEBFF"))
        ctx.fill()
        ctx.move_to(-84, 0)
        ctx.curve_to(-140, 30, -110, 86, -40, 60)
        rellena(ctx, AZUL_P2, 7)
        for j, dx in enumerate((-16, 6, 28)):
            ctx.move_to(dx - 8, -106)
            ctx.curve_to(dx - 20, -150, dx + 14, -150, dx + 6, -108)
            rellena(ctx, AZUL_P2, 5)
        cara(ctx, 10, -30, 74, 0.72, k=k, look=look, sin_boca=True)
        # pico: se abre con el bostezo
        ab = 0.75 * clamp(k)
        for sg in (-1, 1):
            with en(ctx, 12, 10, 1.0, sg * ab * 0.5):
                ctx.move_to(-30, 0)
                ctx.line_to(30, 0)
                ctx.line_to(0, sg * 38 if sg > 0 else -30)
                ctx.close_path()
                rellena(ctx, PICO, 6)
        if ab > 0.05:
            ctx.move_to(-18, 10)
            ctx.line_to(42, 10)
            trazo(ctx, BOCA, 5)


def serpiente(ctx, x, y, s=1.0, k=0.0, look=(0, 0), t=0.0):
    """Serpiente enroscada con la cabeza levantada, de perfil; (x, y) = bisagra de la mandíbula. k = boca abierta."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.move_to(-380, 400)
        ctx.curve_to(-180, 470, 170, 460, 175, 330)
        ctx.curve_to(180, 210, -10, 220, -40, 140)
        ctx.curve_to(-55, 100, -40, 60, -20, 30)
        cuerpo = ctx.copy_path()
        ctx.new_path()
        ctx.append_path(cuerpo)
        trazo(ctx, INK, 96)
        ctx.append_path(cuerpo)
        trazo(ctx, VERDE_S, 80)
        ctx.append_path(cuerpo)
        ctx.set_dash([10, 46])
        trazo(ctx, hx("#FFE066"), 22)
        ctx.set_dash([])
        k = clamp(k)
        ab = 0.62 * k
        up, dn = -0.12 - ab, 0.08 + ab
        # adentro de la boca: el triángulo entre las dos mandíbulas
        if k > 0.03:
            tip_u = (150 * math.cos(up) + 6 * math.sin(up), 150 * math.sin(up))
            tip_d = (140 * math.cos(dn), 140 * math.sin(dn) + 14)
            ctx.move_to(0, 6)
            ctx.line_to(*tip_u)
            ctx.line_to(*tip_d)
            ctx.close_path()
            rellena(ctx, BOCA, 6)
        # mandíbula de abajo
        with en(ctx, 0, 0, 1.0, dn):
            ctx.move_to(-20, 4)
            ctx.line_to(138, 6)
            ctx.curve_to(150, 8, 150, 30, 132, 32)
            ctx.curve_to(80, 44, 10, 48, -24, 34)
            ctx.close_path()
            rellena(ctx, VERDE_S2, 7)
            if k > 0.03:
                ctx.move_to(20, 10)
                ctx.curve_to(60, 4, 100, 4, 128, 10)
                trazo(ctx, LENGUA, 12)
        # cabeza de arriba
        with en(ctx, 0, 0, 1.0, up):
            ctx.move_to(-30, 14)
            ctx.curve_to(-50, -40, 0, -78, 70, -74)
            ctx.curve_to(130, -70, 168, -40, 162, -8)
            ctx.curve_to(160, 4, 150, 8, 136, 8)
            ctx.line_to(-30, 14)
            ctx.close_path()
            rellena(ctx, VERDE_S, 8)
            if k > 0.03:
                for fx in (112, 82):
                    ctx.move_to(fx - 9, 8)
                    ctx.line_to(fx - 2, 8 + 30 * k)
                    ctx.line_to(fx + 5, 8)
                    ctx.close_path()
                    rellena(ctx, BLANCO, 3)
            else:
                ctx.move_to(0, 10)
                ctx.line_to(136, 8)
                trazo(ctx, INK, 6)
            ctx.arc(148, -26, 5, 0, TAU)
            ctx.set_source_rgb(*INK)
            ctx.fill()
            oj = "closed" if k > 0.35 else "open"
            K.ojo(ctx, 78, -38, 1.0, oj, look)
            if k > 0.35:
                ctx.move_to(52, -80)
                ctx.curve_to(70, -94, 92, -94, 108, -82)
                trazo(ctx, INK, 7)
            lagrimita(ctx, 108, -14, 1.0, clamp((k - 0.7) / 0.3))
            if k < 0.03:
                # lengua bífida que entra y sale
                q = (t * 1.3) % 1.0
                if q < 0.35:
                    L = 60 * math.sin(q / 0.35 * math.pi)
                    ctx.move_to(150, 8)
                    ctx.line_to(150 + L, 10)
                    ctx.line_to(150 + L + 14, 0)
                    ctx.move_to(150 + L, 10)
                    ctx.line_to(150 + L + 14, 20)
                    trazo(ctx, ROJO, 6)


def ojo_grande(ctx, x, y, s=1.0):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.move_to(-230, 0)
        ctx.curve_to(-120, -170, 120, -170, 230, 0)
        ctx.curve_to(120, 170, -120, 170, -230, 0)
        ctx.close_path()
        ojo_path = ctx.copy_path()
        rellena(ctx, BLANCO, 12)
        ctx.save()
        ctx.append_path(ojo_path)
        ctx.clip()
        ctx.arc(0, 0, 92, 0, TAU)
        ctx.set_source_rgb(*hx("#3D8BFF"))
        ctx.fill()
        ctx.arc(0, 0, 44, 0, TAU)
        ctx.set_source_rgb(*INK)
        ctx.fill()
        ctx.arc(-26, -30, 18, 0, TAU)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()
        ctx.restore()
        for j in range(5):
            a_ = math.pi * (1.2 + 0.15 * j)
            x0, y0 = 150 * math.cos(a_) * 1.15, -104 + 0 * j
            ctx.move_to(-100 + 50 * j, -112 + 18 * abs(j - 2))
            ctx.line_to(-118 + 59 * j, -160 + 22 * abs(j - 2))
            trazo(ctx, INK, 10)


def libro(ctx, x, y, s=1.0, k=0.0, brillo=0.0):
    """Libro abierto con cara: un ojo en cada página y la boca en el lomo."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        rrect(ctx, -300, -200, 600, 420, 30)
        rellena(ctx, LIBRO, 9)
        for sg in (-1, 1):
            ctx.move_to(0, -172)
            ctx.curve_to(sg * 90, -200, sg * 200, -200, sg * 278, -184)
            ctx.line_to(sg * 278, 182)
            ctx.curve_to(sg * 200, 170, sg * 90, 170, 0, 196)
            ctx.close_path()
            rellena(ctx, PAGINA, 7)
        for sg in (-1, 1):
            for yy in (-140, -112):
                ctx.move_to(sg * 50, yy)
                ctx.line_to(sg * 240, yy)
                trazo(ctx, GRIS, 9)
        for yy in (40, 72, 104, 136):
            ctx.move_to(-240, yy)
            ctx.line_to(-80, yy)
            trazo(ctx, GRIS, 9)
        for yy in (92, 124):
            ctx.move_to(70, yy)
            ctx.line_to(240, yy)
            trazo(ctx, GRIS, 9)
        if brillo > 0.01:
            rrect(ctx, 52, 4, 206, 64, 14)
            ctx.set_source_rgba(*AMARILLO, brillo)
            ctx.fill()
        texto(ctx, "BOSTEZO", 155, 38, 42, fill=INK, stroke=None)
        cara(ctx, 0, -70, 300, 1.45, k=k, dy_boca=140)


def torta(ctx, x, y, s=1.0, velas=0.0, t=0.0):
    """Torta con 4 velas; velas = cuántas están prendidas (0..4, continuo)."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        elipse(ctx, 0, 110, 250, 40)
        rellena(ctx, BLANCO, 7)
        rrect(ctx, -200, -70, 400, 180, 30)
        rellena(ctx, TORTA, 8)
        ctx.move_to(-200, 20)
        ctx.line_to(200, 20)
        trazo(ctx, TORTA2, 16)
        ctx.move_to(-200, -40)
        for j in range(8):
            x0 = -200 + 50 * j
            ctx.curve_to(x0 + 10, 10, x0 + 40, 10, x0 + 50, -40)
        ctx.line_to(200, -76)
        ctx.line_to(-200, -76)
        ctx.close_path()
        rellena(ctx, BLANCO, 7)
        for j, vx in enumerate((-120, -40, 40, 120)):
            rrect(ctx, vx - 13, -190, 26, 118, 8)
            rellena(ctx, (AMARILLO, hx("#7EC8FF"), VERDE, hx("#C9A8FF"))[j], 6)
            p = clamp(velas - j)
            if p > 0.01:
                fl = 1 + 0.08 * math.sin(t * 17 + j * 2)
                with en(ctx, vx, -200, p * fl):
                    ctx.move_to(0, -52)
                    ctx.curve_to(26, -18, 22, 8, 0, 8)
                    ctx.curve_to(-22, 8, -26, -18, 0, -52)
                    ctx.close_path()
                    rellena(ctx, hx("#FFB020"), 5)
                    elipse(ctx, 0, -6, 7, 12)
                    ctx.set_source_rgb(*AMARILLO)
                    ctx.fill()


def cadena(ctx, x0, x1, y, rotura=0.0, s=1.0):
    """Eslabones entre x0 y x1; con rotura > 0 el del medio se abre y los costados se separan."""
    if s <= 0.01:
        return
    xs = [lerp(x0, x1, q) for q in (0.2, 0.5, 0.8)]
    for j, xx in enumerate(xs):
        dx = (-1 if j == 0 else 1) * 46 * rotura if j != 1 else 0
        a = 1.0 - (rotura if j == 1 else 0)
        with en(ctx, xx + dx, y, s, 0 if j != 1 else math.pi / 2 * 0):
            if j == 1:
                rrect(ctx, -60, -18, 120, 36, 18)
            else:
                rrect(ctx, -52, -32, 104, 64, 30)
            trazo(ctx, INK, 22, a)
            if j == 1:
                rrect(ctx, -60, -18, 120, 36, 18)
            else:
                rrect(ctx, -52, -32, 104, 64, 30)
            trazo(ctx, GRIS, 12, a)


def planilla_estudio(ctx, x, y, s=1.0, llenado=1.0):
    """Tablero con la palabra ESTUDIO y una grilla de cabecitas (muchísima gente)."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        rrect(ctx, -250, -300, 500, 600, 30)
        rellena(ctx, MADERA, 9)
        rrect(ctx, -212, -250, 424, 520, 14)
        rellena(ctx, BLANCO, 6)
        rrect(ctx, -80, -326, 160, 60, 14)
        rellena(ctx, GRIS, 7)
        texto(ctx, "ESTUDIO", 0, -186, 64, fill=INK, stroke=None)
        n = 0
        for fila in range(5):
            for col in range(6):
                q = clamp(llenado * 31 - n)
                n += 1
                if q <= 0.01:
                    continue
                cx, cy = -165 + 66 * col, -100 + 78 * fila
                with en(ctx, cx, cy, ease(q, "out")):
                    ctx.arc(0, 0, 25, 0, TAU)
                    rellena(ctx, PIELES[(fila + col) % 5], 4)
                    ctx.save()
                    ctx.arc(0, 0, 25, 0, TAU)
                    ctx.clip()
                    elipse(ctx, 0, -20, 28, 14)
                    ctx.set_source_rgb(*PELOS[(fila * 2 + col) % 5])
                    ctx.fill()
                    ctx.restore()
                    for sx in (-1, 1):
                        ctx.arc(sx * 8, 2, 3.6, 0, TAU)
                        ctx.set_source_rgb(*INK)
                        ctx.fill()


# ================================================================== escenas
# ------------------------------------------------------------------ 1. apertura (y cierre del loop)
BARRA = (100, 860, 250)            # x0, x1, y de la barra de progreso
ICONO = (958, 250, 74)             # bostecito al final de la barra
VY, VK = 1405, 1.22                 # pies de Vos
ALM = (815, 1130)                  # almohada
T_BOSTEZAR0 = b(0, "bostezar")
T_NO1 = b(1)
T_TENGAS = b(1, "tengas")
T_ALCANZA = b(2)
T_ALGUIEN = b(2, "alguien")
T_HACERLO = b(2, "hacerlo")
T_POR3 = b(3)
T_COPIA = b(3, "copia")
T_AJENO = b(3, "ajeno")
T_BOSTEZASTE = b(19, "bostezaste")
T_PREOCUPES = b(19, "preocupes")


def vos_x(u):
    return lerp(540, 330, prog(u, T_ALCANZA - 0.1, 0.45, "inout")) if u >= 0 else 540


def vos_pose(u):
    if u < 0:
        uc = u + TOTAL
        if T_PREOCUPES - 0.35 <= uc < TOTAL - 0.45:
            return "contento"
        return "neutral"
    if T_COPIA - 0.05 <= u < T_COPIA + 1.45:
        return "estira"
    if T_ALCANZA + 0.25 <= u:
        return "mira"
    return "neutral"


def barra(ctx, u):
    x0, x1, y = BARRA
    frac = (u % TOTAL) / TOTAL
    rrect(ctx, x0 - 6, y - 19, x1 - x0 + 12, 38, 19)
    rellena(ctx, PANEL, 7)
    xf = lerp(x0, x1, frac)
    if xf > x0 + 2:
        rrect(ctx, x0, y - 11, xf - x0, 22, 11)
        ctx.set_source_rgb(*ROJO_BARRA)
        ctx.fill()
    ctx.arc(xf, y, 21, 0, TAU)
    rellena(ctx, ROJO_BARRA, 6)
    # el bostecito espera al final
    uc = u % TOTAL
    k = max(bostezo_k(uc, T_BOSTEZAR0 - 0.15, 1.3), bostezo_k(uc, T_BOSTEZASTE - 0.2, 1.4))
    sc = P.bump(uc, T_BOSTEZAR0 - 0.15, 0.4, 0.35)
    bostecito(ctx, ICONO[0], ICONO[1], ICONO[2], k=k, s=sc)


def d_apertura(ctx, u):
    fondo(ctx, u % TOTAL)
    barra(ctx, u)
    x = vos_x(u)
    vos(ctx, vos_pose(u), x, VY, VK)
    if u >= 0:
        # no hace falta sueño: Zzz que se tachan
        a = prog(u, T_NO1 - 0.1, 0.25) * sale(u, T_ALCANZA + 0.1)
        if a > 0.01:
            zetas(ctx, x + 250, 560, u, 2.4, a)
            if u >= T_TENGAS - 0.1:
                cruz_roja(ctx, x + 330, 430, 0.85 * pop(u, T_TENGAS - 0.1, 0.25), a)
        # alguien bosteza: la almohada
        s_alm = pop(u, T_ALCANZA + 0.15, 0.4)
        k_alm = bostezo_k(u, T_HACERLO - 0.15, 1.5)
        almohada(ctx, ALM[0], ALM[1], 1.08 * s_alm, k=k_alm, look=(-0.9, 0.1))
        # el contagio: ondas de boca a boca
        p = prog(u, T_HACERLO + 0.25, T_COPIA - T_HACERLO - 0.15, "inout")
        if 0 < p < 1:
            ondas(ctx, ALM[0] - 230, ALM[1] + 10, x + 80, VY - 400 * VK, p)
        signo(ctx, "?", 160, 520, 260, u, T_AJENO - 0.25)


def d_cierre(ctx, t):
    d_apertura(ctx, t - TOTAL)


# ------------------------------------------------------------------ 2. animales: casi todos bostezan, hasta las serpientes
T_B4 = b(4)
T_CASI = b(4, "casi")
T_ANIMAL = b(4, "animal")
T_HASTA = b(5)
T_SERPIENTES = b(5, "serpientes")
T_BOSTEZAN = b(5, "bostezan")
T_PERO6 = b(6)
T_RARISIMO = b(6, "rarisimo")
PEZ = (290, 590)
PAJ = (810, 570)
SERP = (580, 800)


def d_animales(ctx, t):
    fondo(ctx, t)
    mira_serp = prog(t, T_HASTA + 0.2, 0.3)
    pez(ctx, PEZ[0], PEZ[1], 1.15 * pop(t, T_B4 - 0.05, 0.4), k=bostezo_k(t, T_CASI - 0.1, 1.3),
        look=(lerp(0, 0.8, mira_serp), lerp(0, 0.9, mira_serp)))
    pajaro(ctx, PAJ[0], PAJ[1], 1.25 * pop(t, T_B4 + 0.35, 0.4), k=bostezo_k(t, T_ANIMAL - 0.15, 1.3),
           look=(lerp(0, -0.6, mira_serp), lerp(0, 0.9, mira_serp)))
    serpiente(ctx, SERP[0], SERP[1], 1.12 * pop(t, T_HASTA, 0.45), k=bostezo_k(t, T_BOSTEZAN - 0.3, 2.6, 0.45, 0.5),
              t=t)
    # pero no se copian: los otros miran serios
    if t >= T_PERO6:
        sello(ctx, "RARÍSIMO", 540, 330, 92, t, T_RARISIMO - 0.05)


# ------------------------------------------------------------------ 3. dónde se comprobó: humanos, chimpancés y, quizás, perros
T_SOLO7 = b(7)
T_HUMANOS = b(7, "humanos")
T_CHIMP = b(7, "chimpances")
T_QUIZAS = b(7, "quizas")
T_PERROS = b(7, "perros")
CARTAS = [(190, T_HUMANOS, "HUMANOS"), (540, T_CHIMP, "CHIMPANCÉS"), (890, T_QUIZAS, "PERROS")]
CY = 870


def d_quienes(ctx, t):
    fondo(ctx, t)
    kartel(ctx, "COMPROBADO EN", 540, 430, 70, t, T_SOLO7 + 0.05)
    for j, (cx, t0, lab) in enumerate(CARTAS):
        s0 = pop(t, T_SOLO7 + 0.15 + 0.12 * j, 0.35)
        if s0 <= 0.01:
            continue
        s = pop(t, t0 - 0.1, 0.4)
        with en(ctx, cx, CY, s0 * P.bump(t, t0 - 0.1, 0.35, 0.12)):
            rrect(ctx, -160, -235, 320, 470, 36)
            rellena(ctx, CREMA if s > 0.01 else PANEL, 8)
            if s <= 0.01:
                texto(ctx, "?", 0, 0, 170, fill=hx("#3A4677"), stroke=None)
            kk = bostezo_k(t, t0 + 0.2, 1.4)
            with en(ctx, 0, -20, s):
                if j == 0:
                    cabeza(ctx, 0, 0, 118, k=kk, piel=PIELES[1], pelo=PELOS[1], estilo="largo")
                elif j == 1:
                    mono(ctx, 0, 0, 112, k=kk)
                else:
                    perro(ctx, 0, 0, 110, k=bostezo_k(t, T_PERROS + 0.15, 1.4))
        kartel(ctx, lab, cx, CY + 300, 40 if j == 1 else 46, t, t0)
        if j < 2:
            if t >= t0 + 0.3:
                tilde(ctx, cx + 130, CY - 215, 1.1 * pop(t, t0 + 0.3, 0.3))
        else:
            signo(ctx, "?", cx + 120, CY - 225, 170, t, T_PERROS - 0.05)


# ------------------------------------------------------------------ 4. ni siquiera hace falta verlo: alcanza con leer
T_NI8 = b(8)
T_VERLO = b(8, "verlo")
T_LEER = b(9)
T_BOSTEZOS9 = b(9, "bostezos")
T_BOSTEZAR9 = b(9, "bostezar")


def d_leer(ctx, t):
    fondo(ctx, t)
    s_ojo = pop(t, T_NI8, 0.4) * sale(t, T_LEER + 0.05, 0.25)
    ojo_grande(ctx, 540, 820, 1.1 * s_ojo)
    if t >= T_VERLO - 0.1 and s_ojo > 0.01:
        cruz_roja(ctx, 540, 820, 1.2 * pop(t, T_VERLO - 0.1, 0.25) * s_ojo / 1.0)
    s_lib = pop(t, T_LEER + 0.1, 0.45)
    brillo = 0.85 * prog(t, T_BOSTEZOS9 - 0.05, 0.2) * (0.75 + 0.25 * math.sin(t * 9))
    libro(ctx, 540, 880, 1.15 * s_lib, k=bostezo_k(t, T_BOSTEZAR9 - 0.1, 1.6), brillo=brillo)


# ------------------------------------------------------------------ 5. los bebés no se contagian
T_BEBES = b(10, "bebes")
T_NO10 = b(10, "no")
T_CONTAGIAN = b(10, "contagian")
ALM5 = (290, 900)
BEBE = (780, 930)


def d_bebe(ctx, t):
    fondo(ctx, t)
    t0 = b(10)
    almohada(ctx, ALM5[0], ALM5[1], 1.0 * pop(t, t0 - 0.05, 0.4), k=bostezo_k(t, t0 + 0.25, 1.4),
             look=(0.9, 0.1))
    s = pop(t, T_BEBES - 0.05, 0.4)
    feliz = prog(t, T_NO10 - 0.05, 0.15)
    if s > 0.01:
        torso(ctx, BEBE[0], BEBE[1], 150, hx("#9AD7FF"), s)
        cabeza(ctx, BEBE[0], BEBE[1], 150 * s, estilo="bebe", piel=PIELES[3], pelo=PELOS[2],
               ojos="happy" if feliz > 0.5 else "open", boca="grin" if feliz > 0.5 else "smile", look=(-0.6, 0))
    # las ondas llegan y rebotan
    p = clamp((t - (t0 + 0.55)) / (T_NO10 - (t0 + 0.55))) * 1.0 + clamp((t - T_NO10) / 0.9) * 0.9
    if 0 < p < 1.9:
        ondas(ctx, ALM5[0] + 150, ALM5[1] + 20, BEBE[0] - 190, BEBE[1] + 20, p)


# ------------------------------------------------------------------ 6. aparece a los 4 años, cuando entiendes lo que sienten los demás
T_APARECE = b(11, "aparece")
T_4 = b(11, "4")
T_JUSTO = b(12)
T_ENTENDER = b(12, "entender")
T_SIENTEN = b(12, "sienten")
T_DEMAS = b(12, "demas")
NENE = (310, 980)
ALM6 = (790, 990)


def d_edad(ctx, t):
    fondo(ctx, t)
    t0 = b(11)
    # la torta, que después se achica arriba
    q = prog(t, T_JUSTO - 0.05, 0.45)
    tx, ty, ts = lerp(540, 830, q), lerp(820, 420, q), lerp(1.15, 0.55, q)
    velas = 4 * prog(t, T_APARECE - 0.1, T_4 - T_APARECE, "inout")
    torta(ctx, tx, ty, ts * pop(t, t0 - 0.05, 0.4), velas=velas, t=t)
    if t < T_JUSTO + 0.2:
        kartel(ctx, "4 AÑOS", 540, 420, 96, t, T_4 - 0.05, T_JUSTO)
    # el nene y la almohada triste
    s_n = pop(t, T_JUSTO + 0.05, 0.4)
    preocupa = prog(t, T_SIENTEN - 0.05, 0.2)
    torso(ctx, NENE[0], NENE[1], 135, REMERAS[0], s_n)
    cabeza(ctx, NENE[0], NENE[1], 135 * s_n, piel=PIELES[0], pelo=PELOS[2], look=(0.9, 0.1),
           boca="wavy" if preocupa > 0.5 else "smile", ceja="worried" if preocupa > 0.5 else None)
    s_a = pop(t, T_JUSTO + 0.2, 0.4)
    almohada(ctx, ALM6[0], ALM6[1], 0.95 * s_a, boca="wavy", ceja="worried", look=(-0.8, 0.2))
    if s_a > 0.01:
        lagrimita(ctx, ALM6[0] + 70, ALM6[1] + 10 + 60 * ((t * 0.9) % 1.0), 2.2,
                  prog(t, T_ENTENDER - 0.1, 0.2) * (1 - (t * 0.9) % 1.0))
    corazon(ctx, 550, 760, 0.85 * pop(t, T_DEMAS - 0.05, 0.4) * P.bump(t, T_DEMAS + 0.35, 0.35, 0.15))


# ------------------------------------------------------------------ 7. por eso lo ligan a la empatía
T_CIENTIFICOS = b(13, "cientificos")
T_EMPATIA = b(13, "empatia")
LAZO_Y = 820


def lazo(ctx, t, t0, y=LAZO_Y, rotura=0.0, k=0.0):
    s = pop(t, t0, 0.4)
    bostecito(ctx, 230, y, 120, k=k, s=s)
    corazon(ctx, 850, y, 1.15 * pop(t, t0 + 0.2, 0.4))
    cadena(ctx, 360, 720, y, rotura=rotura, s=pop(t, t0 + 0.35, 0.35))


def d_empatia(ctx, t):
    fondo(ctx, t)
    t0 = b(13)
    lazo(ctx, t, t0 - 0.05, k=bostezo_k(t, T_CIENTIFICOS, 1.4))
    sello(ctx, "EMPATÍA", 540, 1160, 110, t, T_EMPATIA - 0.05, rot=-6, col=ROJO)


# ------------------------------------------------------------------ 8. más de tu familia que de un extraño
T_TE14 = b(14)
T_FAMILIA = b(14, "familia")
T_EXTRANO = b(14, "extrano")
MED_Y, MED_H = 1010, 330


def d_familia(ctx, t):
    fondo(ctx, t)
    t0 = T_TE14
    bostecito(ctx, 540, 430, 104, k=bostezo_k(t, t0 + 0.1, 1.5), s=pop(t, t0 - 0.05, 0.4))
    # familia: mamá y nene juntos
    s_f = pop(t, T_FAMILIA - 0.25, 0.4)
    kf = bostezo_k(t, T_FAMILIA + 0.1, 1.3)
    cabeza(ctx, 225, 760, 115 * s_f, k=kf, piel=PIELES[2], pelo=PELOS[0], estilo="largo")
    cabeza(ctx, 385, 800, 86 * s_f, k=bostezo_k(t, T_FAMILIA + 0.25, 1.2), piel=PIELES[2], pelo=PELOS[0])
    corazon(ctx, 305, 620, 0.42 * s_f)
    kartel(ctx, "FAMILIA", 300, 930, 50, t, T_FAMILIA - 0.25)
    medidor(ctx, 300, MED_Y, MED_H, 0.88 * prog(t, T_FAMILIA + 0.15, 0.5, "out"), VERDE, s_f)
    # extraño: sombrero y lentes, no contagia mucho
    s_e = pop(t, T_EXTRANO - 0.3, 0.4)
    cabeza(ctx, 790, 770, 115 * s_e, piel=PIELES[4], pelo=PELOS[1], lentes=True, sombrero=True, boca="flat")
    kartel(ctx, "EXTRAÑO", 790, 930, 50, t, T_EXTRANO - 0.3)
    medidor(ctx, 790, MED_Y, MED_H, 0.25 * prog(t, T_EXTRANO + 0.1, 0.5, "out"), AMARILLO, s_e)


# ------------------------------------------------------------------ 9. tu perro también
T_PERRO15 = b(15, "perro")
T_TAMBIEN = b(15, "tambien")
T_SE15 = b(15, "se")
T_TI = b(15, "ti")
T_DESCONOCIDO = b(15, "desconocido")
PE = (540, 560)


def d_perro(ctx, t):
    fondo(ctx, t)
    t0 = b(15)
    # el perro copia a su dueño, al desconocido no
    k_p = max(bostezo_k(t, T_TAMBIEN - 0.05, 1.2), bostezo_k(t, T_SE15 + 0.45, 1.0, 0.3, 0.3))
    mira = (-0.9, 0.6) if t < T_DESCONOCIDO - 0.5 else (0.9, 0.6)
    nope = prog(t, T_DESCONOCIDO - 0.1, 0.3)
    perro(ctx, PE[0], PE[1], 150, k=k_p, look=mira, s=pop(t, t0 - 0.05, 0.45),
          rot=-0.12 * nope, boca="flat" if nope > 0.5 else "smile")
    s_t = pop(t, T_SE15 - 0.1, 0.4)
    cabeza(ctx, 280, 900, 112 * s_t, k=bostezo_k(t, T_SE15 + 0.05, 1.3), piel=PIELES[1], pelo=PELOS[4])
    kartel(ctx, "TÚ", 280, 1065, 54, t, T_SE15 - 0.1)
    medidor(ctx, 280, 1120, 270, 0.88 * prog(t, T_TI, 0.5, "out"), VERDE, s_t)
    s_d = pop(t, T_DESCONOCIDO - 0.45, 0.4)
    cabeza(ctx, 800, 900, 112 * s_d, k=bostezo_k(t, T_DESCONOCIDO - 0.35, 1.2), piel=PIELES[3], pelo=PELOS[3],
           sombrero=True)
    kartel(ctx, "DESCONOCIDO", 800, 1065, 48, t, T_DESCONOCIDO - 0.45)
    medidor(ctx, 800, 1120, 270, 0.25 * prog(t, T_DESCONOCIDO + 0.15, 0.5, "out"), AMARILLO, s_d)


# ------------------------------------------------------------------ 10. pero un estudio grande no encontró esa relación
T_ESTUDIO = b(16, "estudio")
T_GRANDE = b(16, "grande")
T_NO16 = b(16, "no")
T_RELACION = b(16, "relacion")


def d_estudio(ctx, t):
    fondo(ctx, t)
    t0 = b(16)
    planilla_estudio(ctx, 540, 640, 0.88 * pop(t, T_ESTUDIO - 0.2, 0.4),
                     llenado=prog(t, T_GRANDE - 0.15, 0.65, "out"))
    rot = prog(t, T_RELACION - 0.15, 0.3, "out")
    lazo(ctx, t, T_NO16 - 0.3, y=1150, rotura=rot)
    if t >= T_RELACION - 0.05:
        cruz_roja(ctx, 540, 1150, 0.7 * pop(t, T_RELACION - 0.05, 0.25))


# ------------------------------------------------------------------ 11. nadie sabe por qué
T_NADIE = b(17, "nadie")
SIGNOS = [(220, 520, 150, 0.0), (860, 600, 130, 0.35), (210, 1130, 120, 0.7), (870, 1160, 160, 1.05)]


def d_misterio(ctx, t):
    fondo(ctx, t, 0.15)
    t0 = b(17)
    bostecito(ctx, 540, 850, 190, k=bostezo_k(t, t0 + 0.25, 1.9), s=pop(t, t0 - 0.05, 0.45))
    for x, y, sz, dt in SIGNOS:
        signo(ctx, "?", x, y, sz, t, T_NADIE + dt)


# ------------------------------------------------------------------ 12. a la mitad de los adultos le funciona
T_MITAD = b(18, "mitad")
T_ADULTOS = b(18, "adultos")
GRUPO = [(130 + 205 * c, 700 + 330 * f) for f in range(2) for c in range(5)]
BOSTEZAN = {0, 2, 4, 6, 8}


def d_mitad(ctx, t):
    fondo(ctx, t)
    t0 = b(18)
    for j, (x, y) in enumerate(GRUPO):
        s = pop(t, t0 - 0.05 + 0.06 * j, 0.35)
        k = bostezo_k(t, T_MITAD - 0.1 + 0.05 * (j % 5), 1.8, 0.4, 0.4) if j in BOSTEZAN else 0.0
        cabeza(ctx, x, y, 92 * s, k=k, piel=PIELES[(j * 3) % 5], pelo=PELOS[(j * 2 + 1) % 5],
               estilo="largo" if j in (1, 4, 7) else "corto", look=(0, 0.3))
        torso(ctx, x, y, 92, REMERAS[j % 5], s)
    kartel(ctx, "LA MITAD", 540, 420, 92, t, T_ADULTOS - 0.05)


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_apertura),
    (T_B4 - 0.08, d_animales),
    (T_SOLO7 - 0.08, d_quienes),
    (T_NI8 - 0.08, d_leer),
    (b(10) - 0.08, d_bebe),
    (b(11) - 0.08, d_edad),
    (b(13) - 0.08, d_empatia),
    (T_TE14 - 0.08, d_familia),
    (b(15) - 0.08, d_perro),
    (b(16) - 0.08, d_estudio),
    (b(17) - 0.08, d_misterio),
    (b(18) - 0.08, d_mitad),
    (b(19) - 0.08, d_cierre),
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
    sin_punch = i == len(ESCENAS) - 1          # el cierre termina igual al inicio
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
    ev(T_BOSTEZAR0 - 0.15, "pop", 0.35)
    ev(T_NO1, "pop", 0.3)
    ev(T_TENGAS - 0.1, "clunk", 0.45)
    ev(T_ALCANZA + 0.15, "pop", 0.4)
    for j in range(3):
        ev(T_HACERLO + 0.3 + 0.2 * j, "tick", 0.18, f=700 + 120 * j, d=0.05)
    ev(T_COPIA - 0.05, "plop", 0.35)
    ev(T_AJENO - 0.25, "pop", 0.45)
    # 2. animales
    ev(T_B4, "pop", 0.35)
    ev(T_B4 + 0.35, "pop", 0.3)
    ev(T_HASTA, "pop", 0.45)
    ev(T_BOSTEZAN - 0.3, "plop", 0.35)
    ev(T_RARISIMO - 0.05, "golpe", 0.5)
    # 3. quiénes
    ev(T_SOLO7 + 0.05, "pop", 0.3)
    for _, t0, _ in CARTAS:
        ev(t0 - 0.1, "pop", 0.4)
    ev(T_HUMANOS + 0.3, "ding", 0.3)
    ev(T_CHIMP + 0.3, "ding", 0.3)
    ev(T_PERROS - 0.05, "pop", 0.35)
    # 4. leer
    ev(T_NI8, "pop", 0.35)
    ev(T_VERLO - 0.1, "clunk", 0.45)
    ev(T_LEER + 0.1, "pop", 0.4)
    ev(T_BOSTEZOS9 - 0.05, "ding", 0.3)
    ev(T_BOSTEZAR9 - 0.1, "plop", 0.35)
    # 5. bebé
    ev(b(10), "pop", 0.35)
    ev(T_BEBES - 0.05, "pop", 0.35)
    ev(T_NO10, "clic", 0.4)
    # 6. edad
    ev(b(11), "pop", 0.35)
    for j in range(4):
        ev(T_APARECE - 0.1 + j * (T_4 - T_APARECE) / 4, "tick", 0.2, f=900 + 150 * j, d=0.05)
    ev(T_4 - 0.05, "golpe", 0.45)
    ev(T_JUSTO + 0.05, "pop", 0.35)
    ev(T_DEMAS - 0.05, "ding", 0.35)
    # 7. empatía
    ev(b(13), "pop", 0.35)
    ev(b(13) + 0.35, "clic", 0.3)
    ev(T_EMPATIA - 0.05, "golpe", 0.5)
    # 8. familia
    ev(T_TE14, "pop", 0.3)
    ev(T_FAMILIA - 0.25, "pop", 0.35)
    ev(T_FAMILIA + 0.15, "ding", 0.3)
    ev(T_EXTRANO - 0.3, "pop", 0.35)
    ev(T_EXTRANO + 0.1, "tick", 0.25, f=500, d=0.06)
    # 9. perro
    ev(b(15), "pop", 0.4)
    ev(T_SE15 - 0.1, "pop", 0.3)
    ev(T_TI, "ding", 0.3)
    ev(T_DESCONOCIDO - 0.45, "pop", 0.3)
    ev(T_DESCONOCIDO + 0.15, "tick", 0.25, f=500, d=0.06)
    # 10. estudio
    ev(T_ESTUDIO - 0.2, "pop", 0.35)
    for j in range(6):
        ev(T_GRANDE - 0.15 + 0.1 * j, "tick", 0.12, f=1100 + 60 * j, d=0.03)
    ev(T_NO16 - 0.3, "pop", 0.3)
    ev(T_RELACION - 0.15, "clunk", 0.45)
    ev(T_RELACION - 0.05, "golpe", 0.4)
    # 11. misterio
    ev(b(17), "pop", 0.35)
    for _, _, _, dt in SIGNOS:
        ev(T_NADIE + dt, "pop", 0.22)
    # 12. mitad
    for j in range(10):
        ev(b(18) - 0.05 + 0.06 * j, "tick", 0.12, f=800 + 40 * j, d=0.03)
    ev(T_ADULTOS - 0.05, "pop", 0.4)
    # 13. cierre
    ev(T_PREOCUPES - 0.35, "pop", 0.3)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "por_que_los_bostezos_se_contagian.mp4"))
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

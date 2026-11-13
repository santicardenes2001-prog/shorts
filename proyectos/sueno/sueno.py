"""Short "Un día sin dormir te deja como borracho" — animación procedural (armazón de anestesia.py).

Pensado para el gancho y la retención:
- el primer cuadro ya se mueve: Vos cansado se bambolea y se le duplica la vista (el cuadro de TOTAL es igual al 0);
- un contador de horas y dos barras que se comparan (17 h = 0,05 %; 24 h = 0,10 %) hacen de hilo;
- el video mismo "se duerme": los párpados tapan la pantalla en "se apaga" y vuelven a parpadear cuando
  "más veces te pasa" (nunca más de 3 parpadeos por segundo);
- cambio visual cada 1,5 a 3 s y cada tramo sube la intensidad (C7): laboratorio -> alarma -> apagón ->
  ruta de noche -> 3 de cada 4 -> la autopista con la cancha al lado.
Vos sale solo en la apertura y en el cierre del loop (V2); el resto lo cuentan objetos con cara.

    python proyectos/sueno/sueno.py --fotos 0,5.5,14
    python proyectos/sueno/sueno.py --probar
    python proyectos/sueno/sueno.py        # render completo -> salidas/un_dia_sin_dormir.mp4
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
for _p in (ROOT, os.path.join(ROOT, "proyectos", "pantalla"), os.path.join(ROOT, "proyectos", "picante")):
    sys.path.insert(0, _p)
import kit  # noqa: E402
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, LILITA, UI, a_rgb, bump, cartel, clamp, ease, fuente, hx,  # noqa: E402
                      lerp, lienzo, pop, prog, rrect, texto)
from picante import _elipse_suave, boquita, capa, cejas, fondo_azul, mezcla  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Un día entero sin dormir te deja como borracho.",                  # b0
    "No es una forma de decir: está medido.",                           # b1
    "Tras 17 horas despierto, ya reaccionas más lento.",                # b2
    "Rindes igual que alguien con alcohol en la sangre.",               # b3
    "A las 24 horas, el efecto se duplica.",                            # b4
    "Rindes como alguien que superó el límite legal para conducir.",    # b5
    "Lo peor viene después.",                                           # b6
    "Tu cerebro necesita dormir, y no va a pedirte permiso.",           # b7
    "Si no lo dejas, se duerme solo.",                                  # b8
    "Se apaga unos segundos, sin avisarte.",                            # b9
    "Tus ojos pueden seguir abiertos.",                                 # b10
    "Pareces despierto, pero tu cerebro ya no registra nada.",          # b11
    "Se llama microsueño.",                                             # b12
    "Tú ni siquiera te das cuenta.",                                    # b13
    "Cuanto más sueño acumulas, más veces te pasa.",                    # b14
    "Ahora imagina que ocurre mientras conduces.",                      # b15
    "En una prueba, pusieron al volante a personas sin dormir.",        # b16
    "Tres de cada cuatro tuvieron microsueños durante el manejo.",      # b17
    "Un microsueño dura apenas unos segundos.",                         # b18
    "En una autopista, en ese rato recorres más de 100 metros.",        # b19
    "Es una cancha de fútbol entera,",                                  # b20
    "sin nadie al volante.",                                            # b21
    "Para llegar a eso, no hace falta mucho:",                          # b22
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
NARANJA = hx("#FF8A3D")
CELESTE = hx("#5CC8FF")
ROSA = hx("#FF9EBB")
ROSA_OSC = hx("#E58BA6")
GRIS = hx("#8C95A3")
GRIS_OSC = hx("#2B2F3A")
ACERO = hx("#C9CFD8")
CERVEZA = hx("#F4B23A")
ESPUMA = hx("#FFF6E0")
PALILLO = hx("#E9C98B")
ASFALTO = hx("#30343F")
PASTO = hx("#3FA34D")
PASTO2 = hx("#369145")
LILA = hx("#8E6CE0")
PANEL = hx("#0B1030")
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


def sacudida(t, t0, d=0.4, amp=16.0):
    """Temblor de cámara que se apaga solo."""
    if t < t0 or t > t0 + d:
        return 0.0, 0.0
    q = 1 - (t - t0) / d
    return amp * q * math.sin((t - t0) * 83), amp * q * math.cos((t - t0) * 71)


def etiqueta(ctx, txt, x, y, size, a=1.0, col=hx("#C9D3EA"), ax=0.5):
    if a > 0.01:
        texto(ctx, txt, x, y, size, fill=col, stroke=None, fam=UI, bold=True, ax=ax, alpha=a)


def estrella(ctx, x, y, r, a=1.0, col=BLANCO):
    """Destello de cuatro puntas (de estomago.py)."""
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


def zzz(ctx, x, y, t, s=1.0, a=1.0, fase=0.0):
    """Tres Z que suben y se desvanecen (cíclico)."""
    if a <= 0.01:
        return
    for k in range(3):
        q = ((t * 0.9 + fase + k / 3) % 1.0)
        al = a * math.sin(math.pi * q)
        if al <= 0.02:
            continue
        texto(ctx, "Z", x + 40 * s * q + 12 * s * math.sin(q * 6), y - 120 * s * q, (34 + 26 * q) * s,
              fill=BLANCO, stroke=INK, sw=6 * s, alpha=al)


# ------------------------------------------------------------------ Vos (solo apertura y cierre del loop)
OJERAS = "".join(f'<ellipse cx="{x}" cy="{kit.EYE_Y + 52}" rx="44" ry="15" fill="#6E4FB8" opacity=".38"/>'
                 for x in (kit.EYE_L, kit.EYE_R))
VOS_POSES = {
    "cansado": dict(eyes="tired", brows="sad", mouth_kind="flat", extra=OJERAS),
    "hic": dict(eyes="closed", brows="up", mouth_kind="o", extra=OJERAS),
}


@functools.lru_cache(maxsize=None)
def vos_surface(pose):
    body = kit.vos(**VOS_POSES[pose])
    png = cairosvg.svg2png(bytestring=kit.svg(520, 820, body).encode(), output_width=1040, output_height=1640)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


def vos(ctx, pose, x, y, k=1.0, alpha=1.0, rot=0.0, sy=1.0):
    """Vos con los pies en (x, y); k = 1 es el dibujo a 520x820."""
    if alpha <= 0.01 or k <= 0.01:
        return
    s = vos_surface(pose)
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.scale(k / 2, k / 2 * sy)
    ctx.translate(-520, -1612)
    ctx.set_source_surface(s, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


AMT0 = 0.7        # cuánto se le dobla la vista en el primer (y en el último) cuadro


def vos_borracho(ctx, t, amt, pose="cansado", hic=0.0):
    """Vos que se bambolea con visión doble. Todo depende de t con per(): el cuadro de TOTAL es igual al de 0."""
    rot = amt * (5.0 * per(t, 27) + 1.6 * per(t, 41, 0.7))
    _elipse_suave(ctx, 540, 1368, 270, 36, (0, 0, 0), 0.35)

    def cuerpo(c):
        vos(c, pose, 540, 1360 - 46 * hic, k=1.45, rot=rot, sy=1 + 0.05 * hic)

    cuerpo(ctx)
    if amt > 0.01:
        dx = amt * (40 + 14 * per(t, 19, 1.1))
        ctx.save()
        ctx.translate(dx, -0.3 * dx)
        ctx.push_group()
        cuerpo(ctx)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(0.42 * min(1.0, amt * 1.6))
        ctx.restore()


# ------------------------------------------------------------------ el cerebro con cara
def ojo_p(ctx, x, y, r, p=0.0, look=(0, 0), tapa=ROSA, wide=False):
    """Ojo con párpado: p = 0 abierto, 1 cerrado."""
    rx, ry = (30 * r, 34 * r) if wide else (24 * r, 28 * r)
    if p >= 0.93:
        ctx.move_to(x - 22 * r, y + 2 * r)
        ctx.curve_to(x - 10 * r, y + 13 * r, x + 10 * r, y + 13 * r, x + 22 * r, y + 2 * r)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(7 * r)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()
    path = ctx.copy_path()
    ctx.set_source_rgb(*BLANCO)
    ctx.fill()
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    pr = (8 if wide else 11) * r
    px, py = x + look[0] * 9 * r, y + look[1] * 9 * r + 3 * r
    ctx.arc(px, py, pr, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.arc(px - pr * 0.35, py - pr * 0.4, pr * 0.34, 0, TAU)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill()
    if p > 0.01:
        yb = y - ry + 2 * ry * p
        ctx.rectangle(x - rx - 4, y - ry - 4, 2 * rx + 8, yb - (y - ry) + 4)
        ctx.set_source_rgb(*tapa)
        ctx.fill()
        ctx.move_to(x - rx, yb)
        ctx.line_to(x + rx, yb)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5 * r)
        ctx.stroke()
    ctx.restore()
    ctx.append_path(path)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5 * r)
    ctx.stroke()


def bostezo(ctx, x, y, r, q):
    if q <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y + 14 * r)
    ctx.scale(22 * r * (0.6 + 0.4 * q), 30 * r * q)
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()
    path = ctx.copy_path()
    ctx.set_source_rgb(*hx(kit.P["boca"]))
    ctx.fill()
    ctx.append_path(path)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6 * r)
    ctx.stroke()


def cerebrito(ctx, x, y, s, p=0.0, look=(0, 0), boca="smile", ceja=None, rubor=False, gris=0.0, rot=0.0,
              a=1.0, wide=False, ojeras=0.0, mareo=0.0, t=0.0, yawn=0.0, dy_cara=0.0):
    """Cerebro (el de pantalla.py) con cara. p = párpados; gris = apagado; mareo = ojos en espiral."""
    if s <= 0.01 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.push_group()
    ctx.push_group()
    P.cerebro(ctx, 0, 0, s)
    forma = ctx.pop_group()
    ctx.set_source(forma)
    ctx.paint()
    if gris > 0.01:
        ctx.set_source_rgba(0.45, 0.47, 0.55, 0.75 * gris)
        ctx.mask(forma)
    r = 1.15 * s
    fx, fy = 0, -18 * s + dy_cara * s
    sep = 118 * s
    tapa = mezcla(ROSA, hx("#9DA2B3"), gris * 0.75)
    if rubor:
        for sx in (-1, 1):
            _elipse_suave(ctx, fx + sx * sep * 0.78, fy + 40 * r, 26 * r, 15 * r, hx("#FF5A7A"), 0.75)
    if ojeras > 0.01:
        for sx in (-1, 1):
            _elipse_suave(ctx, fx + sx * sep / 2, fy + 32 * r, 30 * r, 12 * r, LILA, 0.7 * ojeras)
    for sx in (-1, 1):
        ex = fx + sx * sep / 2
        if mareo > 0.01:
            ctx.save()
            ctx.translate(ex, fy)
            ctx.rotate(t * 7 * sx)
            ctx.arc(0, 0, 25 * r, 0, TAU)
            ctx.set_source_rgb(*BLANCO)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(5 * r)
            ctx.stroke()
            for k in range(46):
                ang = k * 0.32
                rr = 2 + k * 0.45 * r
                (ctx.move_to if k == 0 else ctx.line_to)(rr * math.cos(ang), rr * math.sin(ang))
            ctx.set_line_width(4 * r)
            ctx.stroke()
            ctx.restore()
        else:
            ojo_p(ctx, ex, fy, r, p, look, tapa=tapa, wide=wide)
    if ceja:
        cejas(ctx, fx, fy - (40 if wide else 36) * r, sep, ceja, r)
    if yawn > 0.01:
        bostezo(ctx, fx, fy + 40 * r, r, yawn)
    elif boca:
        boquita(ctx, fx, fy + 38 * r, boca, r)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


# ------------------------------------------------------------------ objetos
def jarra(ctx, x, y, s, rot=0.0, a=1.0):
    """Jarra de cerveza; (x, y) = centro del cuerpo."""
    if s <= 0.01 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.scale(s, s)
    ctx.push_group()
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.arc(62, 0, 34, -math.pi / 2, math.pi / 2)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(26)
    ctx.stroke()
    ctx.arc(62, 0, 34, -math.pi / 2, math.pi / 2)
    ctx.set_source_rgb(*hx("#EFE7D2"))
    ctx.set_line_width(13)
    ctx.stroke()
    rrect(ctx, -62, -78, 124, 156, 18)
    ctx.set_source_rgb(*CERVEZA)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    for k in range(3):
        rrect(ctx, -38 + k * 30, -50, 12, 108, 6)
        ctx.set_source_rgba(1, 1, 1, 0.32)
        ctx.fill()
    for bx, br in ((-40, 26), (-10, 32), (24, 28), (50, 22)):
        ctx.arc(bx, -82, br, 0, TAU)
    ctx.set_source_rgb(*ESPUMA)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def volante(ctx, x, y, R, p=0.3, look=(0, 0), boca="flat", ceja=None, rot=0.0, a=1.0, ojeras=0.0, wide=False,
            aro=None):
    """Volante con cara en el centro."""
    if R <= 1 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.push_group()
    if aro is not None:
        g = cairo.RadialGradient(0, 0, R * 0.9, 0, 0, R * 1.35)
        g.add_color_stop_rgba(0, *aro[0], 0.55 * aro[1])
        g.add_color_stop_rgba(1, *aro[0], 0)
        ctx.set_source(g)
        ctx.arc(0, 0, R * 1.35, 0, TAU)
        ctx.fill()
    for ang in (math.radians(200), math.radians(-20), math.radians(90)):
        ctx.move_to(0, 0)
        ctx.line_to(R * 0.9 * math.cos(ang), R * 0.9 * math.sin(ang))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(R * 0.2)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*hx("#4A5060"))
    ctx.set_line_width(R * 0.13)
    ctx.stroke()
    ctx.arc(0, 0, R * 0.9, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(R * 0.24)
    ctx.stroke()
    ctx.arc(0, 0, R * 0.9, 0, TAU)
    ctx.set_source_rgb(*GRIS_OSC)
    ctx.set_line_width(R * 0.16)
    ctx.stroke()
    ctx.arc(0, 0, R * 0.9, math.radians(200), math.radians(250))
    ctx.set_source_rgba(1, 1, 1, 0.18)
    ctx.set_line_width(R * 0.05)
    ctx.stroke()
    ctx.arc(0, 0, R * 0.44, 0, TAU)
    ctx.set_source_rgb(*ACERO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(R * 0.035)
    ctx.stroke()
    r = R / 230
    sep = 0.36 * R
    if ojeras > 0.01:
        for sx in (-1, 1):
            _elipse_suave(ctx, sx * sep / 2, -10 * r + 32 * r, 30 * r, 12 * r, LILA, 0.7 * ojeras)
    for sx in (-1, 1):
        ojo_p(ctx, sx * sep / 2, -10 * r, r, p, look, tapa=ACERO, wide=wide)
    if ceja:
        cejas(ctx, 0, -10 * r - 36 * r, sep, ceja, r)
    if boca:
        boquita(ctx, 0, 30 * r, boca, r)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def parpados(ctx, p):
    """Párpados que tapan la pantalla entera (p = 0 abiertos, 1 cerrados). Los subtítulos quedan encima."""
    if p <= 0.004:
        return
    p = clamp(p)
    h = 1010 * p
    curva = 260 * (1 - p)
    for arriba in (True, False):
        ctx.save()
        if not arriba:
            ctx.translate(0, H)
            ctx.scale(1, -1)
        ctx.move_to(-20, -20)
        ctx.line_to(W + 20, -20)
        ctx.line_to(W + 20, h - curva)
        ctx.curve_to(W * 0.75, h + curva * 0.35, W * 0.25, h + curva * 0.35, -20, h - curva)
        ctx.close_path()
        g = cairo.LinearGradient(0, h - 140, 0, h + 20)
        g.add_color_stop_rgb(0, 0.02, 0.01, 0.02)
        g.add_color_stop_rgb(1, 0.16, 0.05, 0.07)
        ctx.set_source(g)
        ctx.fill()
        if p < 0.98:
            ctx.move_to(-20, h - curva)
            ctx.curve_to(W * 0.25, h + curva * 0.35, W * 0.75, h + curva * 0.35, W + 20, h - curva)
            ctx.set_source_rgba(0, 0, 0, 0.9)
            ctx.set_line_width(10)
            ctx.stroke()
        ctx.restore()


def parpadeo(t, t0, cierra=0.09, queda=0.06, abre=0.12):
    """p del párpado para un parpadeo rápido que empieza en t0."""
    if t < t0:
        return 0.0
    if t < t0 + cierra:
        return ease((t - t0) / cierra, "in")
    if t < t0 + cierra + queda:
        return 1.0
    return 1 - ease((t - t0 - cierra - queda) / abre, "out")


def estatica(ctx, x0, y0, w, h, t, a=1.0):
    """Nieve de TV (cambia en cada cuadro)."""
    n = np.random.default_rng(int(t * FPS) + 7).integers(0, 255, (h // 8 + 1, w // 8 + 1), dtype=np.uint8)
    rgba = np.stack([n, n, n, np.full_like(n, 255)], axis=-1)
    rgba = np.repeat(np.repeat(rgba, 8, 0), 8, 1)[:h, :w].copy()
    surf = cairo.ImageSurface.create_for_data(memoryview(rgba), cairo.FORMAT_ARGB32, w, h, w * 4)
    ctx.save()
    ctx.set_source_surface(surf, x0, y0)
    ctx.paint_with_alpha(a)
    ctx.restore()


def contador(ctx, x, y, n, a=1.0, s=1.0, rojo=0.0):
    """Panel de horas despierto."""
    if a <= 0.01 or s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.push_group()
    rrect(ctx, -300, -150 + 10, 600, 300, 40)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    rrect(ctx, -300, -150, 600, 300, 40)
    ctx.set_source_rgb(*PANEL)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    col = mezcla(AMARILLO, ROJO, rojo)
    texto(ctx, f"{n} h", 0, -28, 180, fill=col, stroke=INK, sw=12)
    etiqueta(ctx, "DESPIERTO", 0, 96, 48)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def barra(ctx, x, y, L, h, col, txt, t, rayas=False, a=1.0):
    if L <= 2 or a <= 0.01:
        return
    ctx.save()
    ctx.push_group()
    rrect(ctx, x, y - h / 2 + 8, L, h, h / 2)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    rrect(ctx, x, y - h / 2, L, h, h / 2)
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    if rayas:
        ctx.save()
        ctx.clip_preserve()
        ctx.new_path()
        off = (t * 120) % 60
        for k in range(int(L / 60) + 3):
            xx = x + k * 60 - off
            ctx.move_to(xx, y + h / 2)
            ctx.line_to(xx + 30, y - h / 2)
            ctx.line_to(xx + 52, y - h / 2)
            ctx.line_to(xx + 22, y + h / 2)
            ctx.close_path()
        ctx.set_source_rgba(1, 1, 1, 0.22)
        ctx.fill()
        ctx.restore()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    if txt and L > 190:
        texto(ctx, txt, x + 34, y + 4, 62, fill=INK, stroke=None, ax=0.0)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def badge(ctx, txt, x, y, r, s, col=BLANCO, fg=INK, size=None):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.arc(0, 8, r, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.arc(0, 0, r, 0, TAU)
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    texto(ctx, txt, 0, 4, size or r * 1.15, fill=fg, stroke=None)
    ctx.restore()


def bateria(ctx, x, y, nivel, t, blink=False, s=1.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    w, h = 340, 160
    rrect(ctx, -w / 2, -h / 2 + 10, w, h, 30)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    rrect(ctx, -w / 2, -h / 2, w, h, 30)
    ctx.set_source_rgb(*PANEL)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    rrect(ctx, w / 2 - 2, -34, 30, 68, 12)
    ctx.set_source_rgb(*GRIS)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    col = VERDE if nivel > 0.5 else (AMARILLO if nivel > 0.22 else ROJO)
    on = not blink or (int(t * 6) % 2 == 0)
    if on and nivel > 0.005:
        rrect(ctx, -w / 2 + 18, -h / 2 + 18, (w - 36) * nivel, h - 36, 14)
        ctx.set_source_rgb(*col)
        ctx.fill()
    ctx.restore()


def simbolo_power(ctx, x, y, r, col, a=1.0):
    if a <= 0.01:
        return
    ctx.save()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.arc(x, y, r, math.radians(-60), math.radians(240))
    ctx.move_to(x, y - r * 1.15)
    ctx.line_to(x, y - r * 0.1)
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(r * 0.5)
    ctx.stroke_preserve()
    ctx.set_source_rgba(*col, a)
    ctx.set_line_width(r * 0.28)
    ctx.stroke()
    ctx.restore()


def cronometro(ctx, x, y, R, seg, t, cara_p=1.0, a=1.0, cara=True):
    """Cronómetro; seg = segundos marcados (la cuña amarilla)."""
    if R <= 1 or a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.push_group()
    rrect(ctx, -R * 0.16, -R * 1.28, R * 0.32, R * 0.24, R * 0.06)
    ctx.set_source_rgb(*GRIS)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(3, R * 0.025))
    ctx.stroke()
    ctx.move_to(0, -R * 1.06)
    ctx.line_to(0, -R)
    ctx.set_line_width(R * 0.12)
    ctx.stroke()
    ctx.save()
    ctx.rotate(math.radians(40))
    rrect(ctx, -R * 0.08, -R * 1.16, R * 0.16, R * 0.18, R * 0.04)
    ctx.set_source_rgb(*GRIS)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.restore()
    ctx.arc(0, R * 0.05, R, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.arc(0, 0, R, 0, TAU)
    ctx.set_source_rgb(*hx("#E9EDF4"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(R * 0.07)
    ctx.stroke()
    ctx.arc(0, 0, R * 0.86, 0, TAU)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill()
    if seg > 0.01:
        ctx.move_to(0, 0)
        ctx.arc(0, 0, R * 0.84, -math.pi / 2, -math.pi / 2 + TAU * seg / 60)
        ctx.close_path()
        ctx.set_source_rgba(*AMARILLO, 0.9)
        ctx.fill()
    for k in range(60):
        ang = TAU * k / 60 - math.pi / 2
        l = 0.12 if k % 5 == 0 else 0.06
        ctx.move_to(R * 0.84 * math.cos(ang), R * 0.84 * math.sin(ang))
        ctx.line_to(R * (0.84 - l) * math.cos(ang), R * (0.84 - l) * math.sin(ang))
        ctx.set_line_width(R * (0.025 if k % 5 == 0 else 0.012))
        ctx.set_source_rgb(*INK)
        ctx.stroke()
    if cara:
        r = R / 300
        for sx in (-1, 1):
            ojo_p(ctx, sx * 55 * r, R * 0.42, r * 1.1, cara_p, tapa=BLANCO)
        boquita(ctx, 0, R * 0.42 + 40 * r, "flat", r)
    ang = -math.pi / 2 + TAU * seg / 60
    ctx.move_to(-R * 0.12 * math.cos(ang), -R * 0.12 * math.sin(ang))
    ctx.line_to(R * 0.74 * math.cos(ang), R * 0.74 * math.sin(ang))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgb(*ROJO)
    ctx.set_line_width(R * 0.04)
    ctx.stroke()
    ctx.arc(0, 0, R * 0.06, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


# ------------------------------------------------------------------ escena 1: Vos borracho (gancho)
T_BORR = b(0, "borracho")
T_NOES = b(1)
T_MED = b(1, "medido")
T_HIC = T_BORR + 0.12


def globo_hic(ctx, t):
    if t < T_HIC or t > T_NOES + 0.2:
        return
    s = pop(t, T_HIC, 0.3) * sale(t, T_NOES, 0.2)
    cartel(ctx, "¡hic!", 780, 430, 64, box=BLANCO, s=s, rot=10, pad=(26, 12))


def estrellitas(ctx, t, a):
    if a <= 0.01:
        return
    for k in range(5):
        ang = t * 3.2 + TAU * k / 5
        x, y = 540 + 240 * math.cos(ang), 430 + 60 * math.sin(ang)
        estrella(ctx, x, y, 22 + 6 * math.sin(t * 9 + k), a, AMARILLO)


def d_apertura(ctx, t):
    snap = prog(t, T_NOES, 0.22, "out")
    amt = lerp(AMT0 + 0.45 * prog(t, T_BORR, 0.5, "out"), 0.0, snap)
    fondo(ctx, t)
    sx, sy = sacudida(t, T_MED + 0.1, 0.4, 22)
    ctx.translate(sx, sy)
    ctx.save()
    ctx.translate(540, 960)
    ctx.rotate(math.radians(amt * 2.4 * per(t, 13)))
    ctx.translate(-540, -960)
    hic = math.sin(math.pi * clamp((t - T_HIC) / 0.32)) if T_HIC < t < T_HIC + 0.32 else 0.0
    pose = "hic" if T_HIC < t < T_HIC + 0.4 else "cansado"
    vos_borracho(ctx, t, amt, pose, hic)
    estrellitas(ctx, t, prog(t, T_BORR, 0.25) * (1 - snap))
    ctx.restore()
    globo_hic(ctx, t)
    if t >= T_MED - 0.02:      # sello que golpea
        q = clamp((t - T_MED + 0.02) / 0.16)
        s = lerp(2.6, 1.0, ease(q, "in"))
        cartel(ctx, "ESTÁ MEDIDO", 540, 760, 116, box=ROJO, fg=BLANCO, s=s, alpha=clamp(q * 2.5), rot=-9,
               pad=(44, 24))


# ------------------------------------------------------------------ escena 2: el laboratorio (17 h = 0,05 %)
T17 = b(2, "17")
T_REAC = b(2, "reaccionas")
T_LENTO = b(2, "lento")
T_IGUAL = b(3, "igual")
T_ALC = b(3, "alcohol")
T24 = b(4, "24")
T_DUP = b(4, "duplica")
BX, BH, BL = 330, 120, 300          # barras: arranque, alto, largo a las 17 h
FILA1, FILA2 = 750, 1120


def horas(t):
    if t < T24 - 0.3:
        return int(round(17 * prog(t, b(2) + 0.06, T17 + 0.32 - b(2) - 0.06, "out")))
    return int(round(lerp(17, 24, prog(t, T24 - 0.3, 0.6, "out"))))


def d_lab(ctx, t):
    fondo(ctx, t)
    t0 = b(2)
    dup = prog(t, T_DUP, 0.4, "back")
    # contador
    contador(ctx, 540, 300, horas(t), s=pop(t, t0 + 0.02) * bump(t, T24 + 0.25, 0.3, 0.1), rojo=prog(t, T_DUP, 0.3))
    # fila 1: cerebro con sueño
    s1 = pop(t, b(2, "despierto") - 0.1)
    p1 = lerp(0.42, 0.62, prog(t, T24, 0.6)) + 0.08 * per(t, 9)
    cerebrito(ctx, 170, FILA1, 0.5 * s1, p=p1, boca="flat", ojeras=1.0, rot=4 * per(t, 7))
    L1 = BL * prog(t, T_REAC - 0.05, T_LENTO + 0.25 - T_REAC, "inout") * (1 + dup)
    barra(ctx, BX, FILA1, L1, BH, AMARILLO, f"{horas(t)} h", t, rayas=t < T_LENTO + 0.3)
    # fila 2: cerebro con alcohol
    s2 = pop(t, b(3) + 0.04)
    cerebrito(ctx, 170, FILA2, 0.5 * s2, p=0.3, boca="wavy", rubor=True, mareo=prog(t, T_DUP, 0.3), t=t,
              rot=8 * per(t, 11, 0.5))
    jarra(ctx, 256, FILA2 + 70, 0.46 * pop(t, T_ALC - 0.1), rot=14)
    jarra(ctx, 84, FILA2 + 76, 0.44 * pop(t, T_DUP + 0.05), rot=-14)
    L2 = BL * prog(t, T_IGUAL - 0.05, 0.6, "out") * (1 + dup)
    barra(ctx, BX, FILA2, L2, BH, NARANJA, "0,10 %" if t > T_DUP + 0.15 else "0,05 %", t)
    # el igual
    if t > T_IGUAL + 0.45:
        xe = BX + BL * (1 + dup)
        a = prog(t, T_IGUAL + 0.45, 0.25)
        ctx.save()
        ctx.set_dash([18, 14])
        ctx.move_to(xe, FILA1 - BH / 2 - 20)
        ctx.line_to(xe, FILA2 + BH / 2 + 20)
        ctx.set_source_rgba(1, 1, 1, 0.8 * a)
        ctx.set_line_width(6)
        ctx.stroke()
        ctx.restore()
        badge(ctx, "=", xe, (FILA1 + FILA2) / 2, 58, pop(t, T_IGUAL + 0.5) * bump(t, T_DUP + 0.3), size=96)
    badge(ctx, "×2", BX + 2 * BL - 30, FILA1 - 150, 70, pop(t, T_DUP + 0.15), col=ROJO, fg=BLANCO, size=70)


# ------------------------------------------------------------------ escena 3: el alcoholímetro
T_SUPERO = b(5, "superó")
T_COND = b(5, "conducir")
LIMITE = 0.55                     # fracción del dial donde empieza la zona roja (sin número: varía por país)


def valor_dial(t):
    """Fracción del dial: sube a 0,05 % (0,375) y después pasa el límite hasta 0,10 % (0,75)."""
    t0 = b(5)
    v = 0.375 * prog(t, t0 + 0.05, 0.55, "out")
    v += 0.375 * prog(t, T_SUPERO - 0.05, 0.45, "back")
    return v + 0.01 * math.sin(t * 40) * (v > LIMITE)


def d_alcoholimetro(ctx, t):
    fondo(ctx, t)
    v = valor_dial(t)
    alarma = v > LIMITE
    t_al = T_SUPERO + 0.12
    sx, sy = sacudida(t, t_al, 0.5, 18)
    ctx.translate(sx, sy)
    cx, cy = 540, 760
    if alarma:
        pul = 0.5 + 0.5 * math.sin((t - t_al) * 14)
        _elipse_suave(ctx, cx, cy, 620, 560, ROJO, 0.35 + 0.25 * pul)
    # cuerpo del aparato
    rrect(ctx, cx - 300, cy - 360 + 12, 600, 760, 70)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    rrect(ctx, cx - 300, cy - 360, 600, 760, 70)
    ctx.set_source_rgb(*hx("#34508C"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    rrect(ctx, cx - 60, cy - 470, 120, 130, 30)          # boquilla
    ctx.set_source_rgb(*BLANCO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    led = ROJO if alarma and int(t * 8) % 2 == 0 else hx("#3A2A3A")
    ctx.arc(cx + 210, cy - 290, 22, 0, TAU)
    ctx.set_source_rgb(*led)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()
    # dial
    dx, dy, R = cx, cy + 40, 230
    rrect(ctx, cx - 255, cy - 250, 510, 330, 40)
    ctx.set_source_rgb(*hx("#EEF2F8"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    for f0, f1, col in ((0, LIMITE, VERDE), (LIMITE, 1.0, ROJO)):
        ctx.arc(dx, dy, R - 40, math.pi + f0 * math.pi, math.pi + f1 * math.pi)
        ctx.set_source_rgb(*col)
        ctx.set_line_width(46)
        ctx.stroke()
    ang = math.pi + LIMITE * math.pi
    ctx.move_to(dx + (R - 80) * math.cos(ang), dy + (R - 80) * math.sin(ang))
    ctx.line_to(dx + (R + 4) * math.cos(ang), dy + (R + 4) * math.sin(ang))
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    texto(ctx, "LÍMITE", dx + (R + 8) * math.cos(ang) + 12, dy + (R + 8) * math.sin(ang) - 6, 38,
          fill=INK, stroke=None, ax=0.0)
    ang = math.pi + clamp(v, 0, 1) * math.pi
    ctx.move_to(dx, dy)
    ctx.line_to(dx + (R - 30) * math.cos(ang), dy + (R - 30) * math.sin(ang))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(14)
    ctx.stroke()
    ctx.arc(dx, dy, 24, 0, TAU)
    ctx.fill()
    # pantallita digital
    val = min(0.10, clamp(v, 0, 1) * 0.10 / 0.75)
    rrect(ctx, cx - 200, cy + 130, 400, 130, 22)
    ctx.set_source_rgb(*hx("#0E1A12"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    txt = f"{val:.2f} %".replace(".", ",")
    texto(ctx, txt, cx, cy + 196, 92, fill=ROJO if alarma else VERDE, stroke=None, fam=UI, bold=True)
    # no manejes
    s = pop(t, T_COND + 0.05)
    if s > 0.01:
        ctx.save()
        ctx.translate(540, 1300)
        ctx.scale(s, s)
        volante(ctx, 0, 0, 72, p=0.5, boca=None)
        ctx.arc(0, 0, 96, 0, TAU)
        ctx.move_to(-68, -68)
        ctx.line_to(68, 68)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(30)
        ctx.stroke()
        ctx.arc(0, 0, 96, 0, TAU)
        ctx.move_to(-68, -68)
        ctx.line_to(68, 68)
        ctx.set_source_rgb(*ROJO)
        ctx.set_line_width(18)
        ctx.stroke()
        ctx.restore()


# ------------------------------------------------------------------ escena 4: "Lo peor viene después"
T_PEOR = b(6, "peor")


def d_oscuro(ctx, t):
    fondo(ctx, t)
    t0 = b(6)
    q = prog(t, t0 + 0.05, 0.7, "inout")
    zoom(ctx, 1 + 0.1 * prog(t, t0, 1.8, "inout"), 540, 860)
    look = (math.sin(t * 5.0) * 0.9, -0.2) if t > T_PEOR + 0.2 else (0, 0)
    cerebrito(ctx, 540, 860, 1.05, p=0.25, look=look, boca="wavy", ceja="worried", ojeras=0.8)
    rin = lerp(1400, 320, q)
    g = cairo.RadialGradient(540, 820, rin, 540, 820, rin + 360)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0.01, 0.01, 0.03, 0.93)
    ctx.set_source(g)
    ctx.paint()


# ------------------------------------------------------------------ escena 5: la batería
T_NECES = b(7, "necesita")
T_PERM = b(7, "permiso")


def d_bateria(ctx, t):
    fondo(ctx, t)
    nivel = lerp(0.86, 0.04, prog(t, T_NECES - 0.1, b(7, "pedirte") - T_NECES + 0.1, "inout"))
    yawn = math.sin(math.pi * clamp((t - (T_PERM - 0.25)) / 0.75)) if t > T_PERM - 0.25 else 0.0
    p = lerp(0.35, 0.65, prog(t, b(7), 2.4)) if yawn < 0.3 else 1.0
    cerebrito(ctx, 540, 1000, 1.05, p=p, boca="flat", ojeras=1.0, yawn=yawn, rot=3 * per(t, 8))
    bump_b = bump(t, T_PERM, 0.3, 0.12)
    bateria(ctx, 540, 470, nivel, t, blink=nivel < 0.1, s=pop(t, b(7) + 0.02) * bump_b)
    a = prog(t, T_PERM - 0.05, 0.15)
    simbolo_power(ctx, 540, 470, 46, ROJO, a=a * (0.5 + 0.5 * (int(t * 6) % 2)))


# ------------------------------------------------------------------ escena 6: los palillos
T_PAL = b(8) + 0.05
T_SNAP = b(8, "duerme") + 0.08


def palillo(ctx, x, y0, y1, w=14, rot=0.0, cx=None, cy=None):
    ctx.save()
    if cx is not None:
        ctx.translate(cx, cy)
        ctx.rotate(rot)
        ctx.translate(-cx, -cy)
    capsula_y(ctx, x, y0, y1, w)
    ctx.restore()


def capsula_y(ctx, x, y0, y1, w):
    ctx.move_to(x, y0)
    ctx.line_to(x, y1)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(w + 8)
    ctx.stroke()
    ctx.move_to(x, y0)
    ctx.line_to(x, y1)
    ctx.set_source_rgb(*PALILLO)
    ctx.set_line_width(w)
    ctx.stroke()


def d_palillos(ctx, t):
    fondo(ctx, t)
    s = 2.1
    x, y = 540, 900
    zoom(ctx, 1 + 0.06 * prog(t, b(8), 1.8), 540, 800)
    r = 1.15 * s
    fy = y - 18 * s
    sep = 118 * s
    rx, ry = 24 * r, 28 * r
    cerrado = t >= T_SNAP
    if not cerrado:
        lucha = 0.07 * (1 + math.sin(t * 31)) * prog(t, T_PAL + 0.3, 0.3)
        p = lerp(0.12, 0.3, prog(t, T_PAL + 0.1, 0.3)) + lucha
    else:
        p = lerp(0.3, 1.0, prog(t, T_SNAP, 0.12, "in"))
    if not cerrado:
        cerebrito(ctx, x, y, s, p=p, look=(0, 0.5), boca="wavy", ojeras=1.0, ceja="worried")
    else:
        cerebrito(ctx, x, y, s, p=p, boca="flat", ojeras=1.0)
    for k, sx in enumerate((-1, 1)):
        ex = x + sx * sep / 2 + sx * 0.42 * rx
        ent = prog(t, T_PAL + 0.12 * k, 0.22, "out")
        if ent <= 0.01:
            continue
        top, bot = fy - ry + 2 * ry * min(p, 0.42) - 6, fy + ry + 26
        if not cerrado:
            dx = (1 - ent) * sx * 300
            capsula_y(ctx, ex + dx, top, bot, 20)
        else:
            q = clamp((t - T_SNAP) / 0.6)
            mid = (top + bot) / 2
            for half, sg in ((0, -1), (1, 1)):
                y0, y1 = (top, mid) if half == 0 else (mid, bot)
                cxh, cyh = ex, (y0 + y1) / 2
                ctx.save()
                ctx.translate(sx * 240 * q + sg * 40 * q, -260 * q + 900 * q * q)
                palillo(ctx, ex, y0, y1, 20, rot=sg * sx * 4 * q, cx=cxh, cy=cyh)
                ctx.restore()
    if cerrado:
        zzz(ctx, x + 250, y - 300, t, 1.6, prog(t, T_SNAP + 0.15, 0.2))
        estrella(ctx, x - 220, y - 320, 40 * (1 - prog(t, T_SNAP, 0.3)), 1.0, BLANCO)


# ------------------------------------------------------------------ escena 7: el apagón (el video se duerme)
T_APAGA = b(9, "apaga")
T_REABRE = b(9, "segundos") + 0.05
T_AVIS = b(9, "avisarte")


def p_apagon(t):
    if t < T_APAGA:
        return 0.0
    if t < T_REABRE:
        return ease((t - T_APAGA) / 0.16, "in")
    return 1 - ease((t - T_REABRE) / 0.18, "out")


def d_apagon(ctx, t):
    fondo(ctx, t)
    sx, sy = sacudida(t, T_REABRE + 0.1, 0.45, 26)
    ctx.translate(sx, sy)
    despierto = t > T_REABRE
    zoom(ctx, 1.0 + (0.08 * (1 - prog(t, T_REABRE, 0.4, "out")) if despierto else 0.0), 540, 900)
    if not despierto:
        cerebrito(ctx, 540, 960, 1.2, p=1.0, boca="flat", gris=prog(t, T_APAGA - 0.1, 0.3), ojeras=1.0)
        zzz(ctx, 760, 700, t, 1.3, 1.0)
    else:
        look = (math.sin((t - T_AVIS) * 7) * 0.9, 0) if t > T_AVIS else (0, -0.4)
        cerebrito(ctx, 540, 960, 1.2, p=0.0, wide=True, look=look, boca="o", ceja="up", ojeras=1.0)
        kartel(ctx, "!", 790, 610, 120, t, T_REABRE + 0.05, T_AVIS, box=AMARILLO, rot=12, pad=(30, 8))
        kartel(ctx, "?", 300, 620, 120, t, T_AVIS + 0.1, None, box=BLANCO, rot=-10, pad=(30, 8))
    parpados(ctx, p_apagon(t))


# ------------------------------------------------------------------ escena 8: ojos abiertos, cerebro sin señal
T_PAREC = b(11)
T_PERO = b(11, "pero")
T_NADA = b(11, "registra")


def ojo_grande(ctx, x, y, rx, ry, look, abre=1.0):
    ry2 = ry * abre
    ctx.save()
    ctx.move_to(x - rx, y)
    ctx.curve_to(x - rx * 0.5, y - ry2 * 1.25, x + rx * 0.5, y - ry2 * 1.25, x + rx, y)
    ctx.curve_to(x + rx * 0.5, y + ry2 * 1.1, x - rx * 0.5, y + ry2 * 1.1, x - rx, y)
    ctx.close_path()
    path = ctx.copy_path()
    ctx.set_source_rgb(*BLANCO)
    ctx.fill()
    ctx.append_path(path)
    ctx.clip()
    ir = ry * 0.82
    ix, iy = x + look[0] * rx * 0.3, y + look[1] * ry * 0.25
    g = cairo.RadialGradient(ix, iy, ir * 0.2, ix, iy, ir)
    g.add_color_stop_rgb(0, *hx("#C98A4B"))
    g.add_color_stop_rgb(1, *hx("#6B3E1E"))
    ctx.arc(ix, iy, ir, 0, TAU)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(ir * 0.08)
    ctx.stroke()
    ctx.arc(ix, iy, ir * 0.42, 0, TAU)
    ctx.set_source_rgb(0.02, 0.02, 0.03)
    ctx.fill()
    ctx.arc(ix - ir * 0.3, iy - ir * 0.32, ir * 0.17, 0, TAU)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill()
    ctx.restore()
    ctx.append_path(path)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(4, rx * 0.06))
    ctx.stroke()
    for k in range(6):                     # pestañas
        u = 0.18 + k * 0.13
        px = x - rx + 2 * rx * u
        py = y - ry2 * 1.25 * 4 * u * (1 - u) * 0.75
        ctx.move_to(px, py)
        ctx.line_to(px + (u - 0.5) * rx * 0.25, py - ry * 0.32)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(max(3, rx * 0.045))
    ctx.stroke()


def mirada(t):
    """Movimientos de ojos de a saltos (como la vista real)."""
    puntos = [(-0.2, 0.0), (0.5, -0.2), (-0.6, 0.1), (0.1, 0.3), (0.6, 0.0), (-0.4, -0.3)]
    k = int(t * 1.6)
    q = clamp((t * 1.6 - k) / 0.12)
    a, c = puntos[k % len(puntos)], puntos[(k + 1) % len(puntos)]
    return lerp(a[0], c[0], q), lerp(a[1], c[1], q)


def d_ojos(ctx, t):
    fondo(ctx, t)
    t0 = b(10)
    q = prog(t, T_PAREC - 0.1, 0.8, "inout")          # 0: ojos gigantes; 1: ojos arriba con cables al cerebro
    oy = lerp(820, 330, q)
    sc = lerp(1.0, 0.5, q)
    abre = 1 + 0.18 * (bump(t, b(10, "abiertos"), 0.35, 1.0) - 1)
    look = mirada(t)
    # cables con señales
    if q > 0.05:
        a = prog(t, T_PAREC + 0.2, 0.3)
        by = 1080
        for sx in (-1, 1):
            x0, y0 = 540 + sx * 210 * sc, oy + 70 * sc
            x1, y1 = 540 + sx * 70, by - 170
            ctx.move_to(x0, y0)
            ctx.curve_to(x0, y0 + 220, x1, y1 - 260, x1, y1)
            ctx.set_source_rgba(*INK, a)
            ctx.set_line_width(30)
            ctx.stroke()
            ctx.move_to(x0, y0)
            ctx.curve_to(x0, y0 + 220, x1, y1 - 260, x1, y1)
            ctx.set_source_rgba(*hx("#F2C14E"), a)
            ctx.set_line_width(16)
            ctx.stroke()
            for k in range(4):
                u = ((t - T_PAREC) * 0.9 + k / 4) % 1.0
                llega = u > 0.86 and t > T_PERO
                if llega:
                    continue
                mu = 1 - u
                px = mu ** 3 * x0 + 3 * mu * mu * u * x0 + 3 * mu * u * u * x1 + u ** 3 * x1
                py = mu ** 3 * y0 + 3 * mu * mu * u * (y0 + 220) + 3 * mu * u * u * (y1 - 260) + u ** 3 * y1
                ctx.arc(px, py, 15, 0, TAU)
                ctx.set_source_rgba(*BLANCO, a)
                ctx.fill()
                _elipse_suave(ctx, px, py, 40, 40, AMARILLO, 0.6 * a)
        # cerebro dormido; en "no registra nada" se llena de nieve
        sb = 0.95 * prog(t, T_PAREC + 0.1, 0.35, "back")
        if sb > 0.01:
            ctx.save()
            ctx.push_group()
            cerebrito(ctx, 540, by, sb, p=1.0, boca="flat", ojeras=1.0)
            forma = ctx.pop_group()
            ctx.set_source(forma)
            ctx.paint()
            nieve = prog(t, T_NADA - 0.05, 0.25)
            if nieve > 0.01:
                ctx.push_group()
                estatica(ctx, 0, 700, W, 700, t)
                ruido = ctx.pop_group()
                ctx.set_source(ruido)
                ctx.push_group()
                ctx.set_source(forma)
                ctx.paint_with_alpha(0.85 * nieve)
                masc = ctx.pop_group()
                ctx.set_source(ruido)
                ctx.mask(masc)
            ctx.restore()
            if t < T_NADA:
                zzz(ctx, 800, by - 200, t, 1.1, 1.0)
            kartel(ctx, "SIN SEÑAL", 540, by + 250, 82, t, T_NADA + 0.25, None, box=BLANCO, rot=-4)
    for sx in (-1, 1):
        ojo_grande(ctx, 540 + sx * 210 * sc, oy, 170 * sc, 118 * sc, look, abre)


# ------------------------------------------------------------------ escena 9: MICROSUEÑO
T_MICRO = b(12, "microsueño")


def d_micro(ctx, t):
    fondo(ctx, t)
    zoom(ctx, 1 + 0.05 * prog(t, b(12), 1.5), 540, 800)
    pal = "MICROSUEÑO"
    fuente(ctx, LILITA, 132)
    anchos = [ctx.text_extents(c)[4] for c in pal]
    x = 540 - sum(anchos) / 2
    for k, (c, w) in enumerate(zip(pal, anchos)):
        t0 = T_MICRO - 0.1 + 0.035 * k
        if t >= t0:
            q = clamp((t - t0) / 0.28)
            yy = 760 - 260 * (1 - ease(q, "back"))
            texto(ctx, c, x + w / 2, yy, 132, fill=AMARILLO, stroke=INK, sw=14, alpha=clamp(q * 3))
        x += w
    cerebrito(ctx, 540, 1120, 0.62 * pop(t, b(12) + 0.02), p=1.0, boca="flat", ojeras=1.0)
    zzz(ctx, 700, 1000, t, 1.0, prog(t, b(12) + 0.2, 0.2))


# ------------------------------------------------------------------ escena 10: la barra de "lo que ves"
BX0, BX1, BY = 110, 970, 1100
HUECOS = [(0.42, 0.55, b(13) + 0.05)]         # (desde, hasta, cuándo aparece)
_t = b(14) + 0.3
for _a, _c in ((0.61, 0.66), (0.70, 0.76), (0.79, 0.83), (0.86, 0.91), (0.93, 0.965)):
    HUECOS.append((_a, _c, _t))
    _t += 0.48
PARPADEOS = [b(14, "veces") - 0.1, b(14, "pasa") + 0.05]


def avance(t):
    """Posición de la reproducción (0 a 1) con saltos sobre cada hueco ya aparecido."""
    t0, t1 = b(13), b(15) - 0.15
    u = lerp(0.06, 0.985, clamp((t - t0) / (t1 - t0)))
    for a, c, ta in HUECOS:
        if t >= ta and a <= u < c:
            u = c
    return u


def d_linea(ctx, t):
    fondo(ctx, t)
    u = avance(t)
    n_huecos = sum(1 for _, _, ta in HUECOS if t >= ta)
    p = lerp(0.0, 0.55, clamp((n_huecos - 1) / 4))
    nota = math.sin(t * 6)
    cerebrito(ctx, 540, 680, 1.05, p=p, look=(0.5 * nota, 0), boca="smile", ojeras=clamp(n_huecos / 4),
              rot=3 * nota)
    if p < 0.3:
        texto(ctx, "♪", 780 + 10 * math.sin(t * 3), 470 - 20 * ((t * 1.2) % 1), 70, fill=BLANCO, stroke=INK, sw=6,
              alpha=1 - ((t * 1.2) % 1))
    etiqueta(ctx, "LO QUE VES", BX0, BY - 80, 44, ax=0.0, a=pop(t, b(13) + 0.02))
    rrect(ctx, BX0, BY - 24, BX1 - BX0, 48, 24)
    ctx.set_source_rgb(*hx("#5A6070"))
    ctx.fill()
    L = BX1 - BX0
    rrect(ctx, BX0, BY - 24, L * u, 48, 24)
    ctx.set_source_rgb(*ROJO)
    ctx.fill()
    for a, c, ta in HUECOS:
        if t < ta:
            continue
        s = max(pop(t, ta, 0.3), 0.01)
        ctx.save()
        ctx.translate(BX0 + L * (a + c) / 2, BY)
        ctx.scale(1, s)
        rrect(ctx, -L * (c - a) / 2, -34, L * (c - a), 68, 12)
        ctx.set_source_rgb(0.02, 0.02, 0.04)
        ctx.fill_preserve()
        ctx.set_source_rgb(*BLANCO)
        ctx.set_line_width(4)
        ctx.stroke()
        ctx.restore()
        if u >= c and t > ta + 0.27:
            texto(ctx, "?", BX0 + L * (a + c) / 2, BY - 90, 70 * pop(t, ta + 0.25), fill=AMARILLO, stroke=INK,
                  sw=8)
    ctx.arc(BX0 + L * u, BY, 42, 0, TAU)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    parpados(ctx, max(parpadeo(t, PARPADEOS[0]), parpadeo(t, PARPADEOS[1])))


# ------------------------------------------------------------------ escena 11: la ruta de noche (POV)
HZ = 760
T_IMAG = b(15, "imagina")
T_CONDUCES = b(15, "conduces")


def d_ruta(ctx, t):
    t0 = b(15)
    fondo(ctx, t)
    vel = 7 + 9 * prog(t, T_IMAG, 0.8)
    ctx.rectangle(0, HZ, W, H - HZ)
    ctx.set_source_rgb(*hx("#0B0F1E"))
    ctx.fill()
    ctx.move_to(540 - 26, HZ)
    ctx.line_to(540 + 26, HZ)
    ctx.line_to(540 + 900, H)
    ctx.line_to(540 - 900, H)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#252A36"))
    ctx.fill()
    g = cairo.RadialGradient(540, 1500, 50, 540, 1300, 760)
    g.add_color_stop_rgba(0, 1, 0.92, 0.6, 0.35)
    g.add_color_stop_rgba(1, 1, 0.92, 0.6, 0)
    ctx.move_to(540 - 22, HZ + 6)
    ctx.line_to(540 + 22, HZ + 6)
    ctx.line_to(540 + 880, H)
    ctx.line_to(540 - 880, H)
    ctx.close_path()
    ctx.set_source(g)
    ctx.fill()
    for sx in (-1, 1):                      # bordes
        ctx.move_to(540 + sx * 20, HZ)
        ctx.line_to(540 + sx * 760, H)
        ctx.set_source_rgba(1, 1, 1, 0.75)
        ctx.set_line_width(10)
        ctx.stroke()
    F = (H - HZ) * 1.0
    fase = (t - t0) * vel
    for k in range(14):                     # líneas del medio y postes que pasan
        z = 1.0 + ((k * 3.0 - fase) % 42.0)
        z2 = z + 1.4
        y1, y2 = HZ + F / z, HZ + F / z2
        w1, w2 = 60 / z, 60 / z2
        ctx.move_to(540 - w1 / 2, y1)
        ctx.line_to(540 + w1 / 2, y1)
        ctx.line_to(540 + w2 / 2, y2)
        ctx.line_to(540 - w2 / 2, y2)
        ctx.close_path()
        ctx.set_source_rgba(*AMARILLO, 0.95)
        ctx.fill()
        if k % 2 == 0:
            for sx in (-1, 1):
                px = 540 + sx * (20 + 740 * F / z / F * 1.12)
                ph = 220 / z
                ctx.rectangle(px - 8 / z * 3, y1 - ph, 16 / z * 3, ph)
                ctx.set_source_rgba(0.9, 0.9, 1, 0.7)
                ctx.fill()
                ctx.rectangle(px - 8 / z * 3, y1 - ph, 16 / z * 3, ph * 0.18)
                ctx.set_source_rgba(*ROJO, 0.9)
                ctx.fill()
    # tablero y volante (con sueño)
    ctx.move_to(0, 1540)
    ctx.curve_to(300, 1470, 780, 1470, W, 1540)
    ctx.line_to(W, H)
    ctx.line_to(0, H)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#11131A"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    volante(ctx, 540, 1840, 330, p=0.55 + 0.1 * math.sin(t * 2.3), ojeras=1.0, rot=6 * math.sin(t * 1.3))
    parpados(ctx, parpadeo(t, T_CONDUCES + 0.08, 0.1, 0.18, 0.16))


# ------------------------------------------------------------------ escena 12: la prueba (3 de cada 4)
VOL_XY = [(300, 590), (780, 590), (300, 1075), (780, 1075)]
T_VOL = b(16, "volante")
T_TRES = b(17, "tres")
CIERRAN = [T_TRES + 0.05, b(17, "cada") + 0.05, b(17, "cuatro") + 0.02]


def d_volantes(ctx, t):
    fondo(ctx, t)
    t0 = b(16)
    kartel(ctx, "PRUEBA DE MANEJO", 540, 230, 70, t, t0 + 0.05, None, box=BLANCO)
    T_SIN = b(16, "sin")
    for k, (x, y) in enumerate(VOL_XY):
        s = pop(t, T_VOL - 0.1 + 0.12 * k)
        if s <= 0.01:
            ctx.arc(x, y, 180, 0, TAU)
            ctx.set_dash([16, 14])
            ctx.set_source_rgba(1, 1, 1, 0.5 * prog(t, t0, 0.3))
            ctx.set_line_width(5)
            ctx.stroke()
            ctx.set_dash([])
            continue
        p = lerp(0.1, 0.5, prog(t, T_SIN, 0.4))
        ceja, boca, look, aro = None, "flat", (0, 0), None
        if k < 3 and t >= CIERRAN[k]:
            p = lerp(0.5, 1.0, prog(t, CIERRAN[k], 0.12, "in"))
            aro = (ROJO, 0.6 + 0.4 * math.sin((t - CIERRAN[k]) * 8))
        if k == 3 and t >= CIERRAN[0]:
            ceja, boca, p = "worried", "wavy", 0.0
            look = (-0.8, -0.6) if t < CIERRAN[1] else (-0.8, 0.0)
        bam = 5 * math.sin(t * 2.2 + k)
        volante(ctx, x, y, 175 * s, p=p, look=look, boca=boca, ceja=ceja, ojeras=prog(t, T_SIN, 0.4), rot=bam,
                aro=aro, wide=k == 3 and t >= CIERRAN[0])
        if k < 3 and t >= CIERRAN[k]:
            zzz(ctx, x + 120, y - 140, t, 0.9, prog(t, CIERRAN[k] + 0.1, 0.2), fase=k * 0.3)
    T34 = b(17, "cuatro", fin=True)
    s = pop(t, T34 - 0.05) * bump(t, T34 + 0.3, 0.3, 0.08)
    cartel(ctx, "3 DE CADA 4", 540, 832, 96, box=ROJO, fg=BLANCO, s=s, rot=-3)


# ------------------------------------------------------------------ escena 13: el cronómetro
T_CRONO0 = b(18) + 0.2
SEG_MICRO = 3.0


def seg_crono(t, t0):
    """Segundos marcados, de a saltos (tic, tic, tic)."""
    q = clamp((t - t0) / 1.8) * SEG_MICRO
    k = math.floor(q)
    return k + ease(clamp((q - k) / 0.25), "back") if q < SEG_MICRO else SEG_MICRO


def d_crono(ctx, t):
    fondo(ctx, t)
    s = pop(t, b(18) + 0.02)
    zoom(ctx, 1 + 0.05 * prog(t, b(18), 2.0), 540, 820)
    cronometro(ctx, 540, 820, 330 * s, seg_crono(t, T_CRONO0), t, cara_p=1.0)
    zzz(ctx, 790, 560, t, 1.2, prog(t, b(18) + 0.3, 0.2))
    kartel(ctx, "APENAS", 540, 1290, 80, t, b(18, "apenas") - 0.05, None, box=AMARILLO, rot=-3)


# ------------------------------------------------------------------ escena 14: la autopista y la cancha
M = 10.0                                   # unidades del mundo por metro
T_A0 = b(19) + 0.12                        # arranca el auto
T_100 = b(19, "100") + 0.15
V_AUTO = 100 * M / (T_100 - T_A0)          # unidades por segundo (el auto llega a 100 m cuando lo dice)
T_CANCHA = b(20)
T_NADIE = b(21)
CANCHA_L, CANCHA_A = 105 * M, 68 * M
CAMPO_X0 = 95                              # la cancha arranca a la derecha de la ruta
VISTA_LEJOS = (355.0, -560.0, 0.98)        # cámara alejada: centro x, centro y, escala


def dist(t):
    return max(0.0, (t - T_A0) * V_AUTO)


def deriva(t):
    """El auto se va de carril cuando nadie maneja."""
    q = prog(t, T_NADIE + 0.1, 1.0, "in")
    return 30 * q, 5 * q


def auto_arriba(ctx, x, y, s, techo=1.0, t=0.0, dormido=True, rot=0.0):
    """Auto visto desde arriba, trompa hacia arriba; (x, y) = centro. 1 unidad = 10 cm."""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.scale(s, s)
    w, h = 18.5, 45.0
    for fx in (-1, 1):
        for fy in (-1, 1):
            rrect(ctx, fx * w / 2 - 2.2, fy * 13.5 - 3.2, 4.4, 6.4, 1.2)
            ctx.set_source_rgb(*INK)
            ctx.fill()
    rrect(ctx, -w / 2, -h / 2, w, h, 6)
    ctx.set_source_rgb(*AMARILLO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(1.2)
    ctx.stroke()
    for fx in (-1, 1):
        ctx.arc(fx * 6, -h / 2 + 1.6, 1.8, 0, TAU)
        ctx.set_source_rgb(*hx("#FFF3B0"))
        ctx.fill()
    # adentro: asientos y volante (a la izquierda)
    rrect(ctx, -7.5, -10.5, 15, 25, 3)
    ctx.set_source_rgb(*hx("#1B1F2A"))
    ctx.fill()
    for fx in (-1, 1):
        rrect(ctx, fx * 3.8 - 3.2, -2, 6.4, 7, 1.6)
        ctx.set_source_rgb(*hx("#4A5060"))
        ctx.fill()
    rrect(ctx, -6.2, 7.5, 12.4, 5.5, 1.6)
    ctx.set_source_rgb(*hx("#4A5060"))
    ctx.fill()
    ctx.restore()
    if techo < 0.99:
        # volante dormido visto desde arriba (sin escalar con el auto, para que se lea la cara)
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(math.radians(rot))
        ctx.scale(s, s)
        ctx.arc(-3.8, -7.0, 1.9, 0, TAU)              # volante de verdad: unos 38 cm
        ctx.set_source_rgba(*INK, 1 - techo)
        ctx.set_line_width(0.7)
        ctx.stroke()
        ctx.arc(-3.8, -7.0, 1.9, 0, TAU)
        ctx.set_source_rgba(*hx("#4A5060"), 1 - techo)
        ctx.set_line_width(0.4)
        ctx.stroke()
        ctx.restore()
    if techo > 0.01:
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(math.radians(rot))
        ctx.scale(s, s)
        ctx.push_group()
        rrect(ctx, -7.8, -11.5, 15.6, 26, 3.5)
        ctx.set_source_rgb(*hx("#E0B400"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(1.0)
        ctx.stroke()
        rrect(ctx, -7.2, -16.5, 14.4, 6, 2)
        ctx.set_source_rgb(*hx("#9FD3F0"))
        ctx.fill()
        rrect(ctx, -6.6, 15.5, 13.2, 3.6, 1.5)
        ctx.fill()
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(techo)
        ctx.restore()


def cancha(ctx, x0, y0, a=1.0):
    """Cancha de 105 x 68 m con sus líneas reglamentarias; (x0, y0) = esquina de abajo a la izquierda."""
    if a <= 0.01:
        return
    ctx.save()
    ctx.push_group()
    L, A = CANCHA_L, CANCHA_A
    for k in range(10):
        ctx.rectangle(x0 - 40, y0 - L / 10 * (k + 1) - (40 if k == 9 else 0), A + 80,
                      L / 10 + (40 if k in (0, 9) else 0))
        ctx.set_source_rgb(*(PASTO if k % 2 == 0 else PASTO2))
        ctx.fill()
    ctx.set_source_rgb(1, 1, 1)
    ctx.set_line_width(1.2 * M)
    ctx.rectangle(x0, y0 - L, A, L)
    ctx.stroke()
    ctx.move_to(x0, y0 - L / 2)
    ctx.line_to(x0 + A, y0 - L / 2)
    ctx.stroke()
    ctx.arc(x0 + A / 2, y0 - L / 2, 9.15 * M, 0, TAU)
    ctx.stroke()
    for fy, sg in ((y0, -1), (y0 - L, 1)):
        ctx.rectangle(x0 + A / 2 - 20.15 * M, fy, 40.3 * M, sg * 16.5 * M)
        ctx.stroke()
        ctx.rectangle(x0 + A / 2 - 9.15 * M, fy, 18.3 * M, sg * 5.5 * M)
        ctx.stroke()
        ctx.rectangle(x0 + A / 2 - 3.66 * M, fy, 7.32 * M, -sg * 2.0 * M)
        ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def mundo_autopista(ctx, t, techo, ver_cancha):
    d = dist(t)
    ax, rot = deriva(t)
    y_car = -d
    # pasto
    ctx.rectangle(-3000, -6000, 6000, 9000)
    ctx.set_source_rgb(*hx("#22472D"))
    ctx.fill()
    # cancha (al lado, del metro 0 al 105)
    cancha(ctx, CAMPO_X0, 0, ver_cancha)
    # ruta: 3 carriles de 3,5 m
    ctx.rectangle(-62, -6000, 124, 9000)
    ctx.set_source_rgb(*ASFALTO)
    ctx.fill()
    ctx.set_source_rgb(1, 1, 1)
    ctx.set_line_width(2.2)
    for xx in (-55, 55):
        ctx.move_to(xx, -6000)
        ctx.line_to(xx, 3000)
        ctx.stroke()
    for xx in (-17.5, 17.5):
        for k in range(-60, 30):
            ctx.rectangle(xx - 1.0, k * 120, 2.0, 45)
        ctx.fill()
    # el tramo que se hace dormido (rojo) y la línea de partida
    if t > T_A0:
        hasta = min(d, 105 * M)
        ctx.rectangle(-55, -hasta, 110, hasta)
        ctx.set_source_rgba(*ROJO, 0.42)
        ctx.fill()
    ctx.rectangle(-62, -1.5, 124, 3)
    ctx.set_source_rgb(*AMARILLO)
    ctx.fill()
    auto_arriba(ctx, ax, y_car, 1.0, techo=techo, t=t, rot=rot)


def d_autopista(ctx, t):
    fondo(ctx, t)
    d = dist(t)
    ax, _ = deriva(t)
    sigue = (ax, -d - 4, 6.2)
    if t < T_CANCHA:
        cx, cy, s = sigue
        q_in = 0.0
    elif t < T_NADIE - 0.05:
        q = prog(t, T_CANCHA, 0.9, "inout")
        cx, cy = lerp(sigue[0], VISTA_LEJOS[0], q), lerp(sigue[1], VISTA_LEJOS[1], q)
        s = math.exp(lerp(math.log(sigue[2]), math.log(VISTA_LEJOS[2]), q))
        q_in = 0.0
    else:
        q = prog(t, T_NADIE - 0.05, 0.5, "inout")
        cerca = (ax - 3, -d - 5, 15.0)
        cx, cy = lerp(VISTA_LEJOS[0], cerca[0], q), lerp(VISTA_LEJOS[1], cerca[1], q)
        s = math.exp(lerp(math.log(VISTA_LEJOS[2]), math.log(cerca[2]), q))
        q_in = q
    ctx.save()
    ctx.translate(540, 820)
    ctx.scale(s, s)
    ctx.translate(-cx, -cy)
    techo = 1 - prog(t, T_NADIE + 0.25, 0.3)
    mundo_autopista(ctx, t, techo, prog(t, T_CANCHA, 0.5))
    ctx.restore()
    # trazo de velocidad (solo siguiendo al auto)
    if t < T_CANCHA:
        for k in range(7):
            yy = (k * 300 + (t - T_A0) * 2600) % 2100 - 100
            xx = 120 + (k * 137) % 840
            ctx.move_to(xx, yy - 120)
            ctx.line_to(xx, yy + 120)
            ctx.set_source_rgba(1, 1, 1, 0.12)
            ctx.set_line_width(6)
            ctx.stroke()
    # HUD: cronómetro chico y metros
    a_hud = 1 - prog(t, T_CANCHA + 0.4, 0.3)
    if a_hud > 0.01 and t > b(19):
        cronometro(ctx, 170, 290, 100 * pop(t, b(19) + 0.02), seg_crono(t, T_A0) if t > T_A0 else 0, t,
                   cara=False, a=a_hud)
        mts = min(100, int(d / M)) if t < T_100 + 0.05 else 100
        txt = f"{mts} m" if t < b(19, "más") else f"+{mts} m"
        cartel(ctx, txt, 640, 290, 120, box=AMARILLO, s=pop(t, b(19) + 0.05) * bump(t, T_100, 0.3, 0.15),
               alpha=a_hud, pad=(40, 16))
    # la cancha: cota de 100 m
    if T_CANCHA < t < T_NADIE + 0.2:
        a = prog(t, T_CANCHA + 0.6, 0.3) * (1 - prog(t, T_NADIE, 0.2))
        kartel(ctx, "+100 m", 540, 200, 110, t, T_CANCHA + 0.55, T_NADIE, box=AMARILLO, pad=(40, 16))
        if a > 0.01:
            def pant(wx, wy):
                return 540 + (wx - cx) * s, 820 + (wy - cy) * s
            x0, y0 = pant(-80, 0)
            _, y1 = pant(-80, -105 * M)
            ctx.move_to(x0, y0)
            ctx.line_to(x0, y1)
            for yy in (y0, y1):
                ctx.move_to(x0 - 18, yy)
                ctx.line_to(x0 + 18, yy)
            ctx.set_source_rgba(1, 1, 1, a)
            ctx.set_line_width(5)
            ctx.stroke()
    # nadie al volante: lupa sobre el asiento del conductor
    if t > T_NADIE + 0.25:
        sl = pop(t, T_NADIE + 0.3, 0.35)
        ang = math.radians(deriva(t)[1])
        wx, wy = ax + (-3.8) * math.cos(ang) - (-7.0) * math.sin(ang), -d + (-3.8) * math.sin(ang) + (-7.0) * math.cos(ang)
        px, py = 540 + (wx - cx) * s, 820 + (wy - cy) * s
        lx, ly = 300, 520
        ctx.move_to(px, py)
        ctx.line_to(lx, ly)
        ctx.set_source_rgba(1, 1, 1, 0.85 * sl)
        ctx.set_line_width(6)
        ctx.stroke()
        ctx.arc(px, py, 34, 0, TAU)
        ctx.stroke()
        if sl > 0.01:
            ctx.save()
            ctx.translate(lx, ly)
            ctx.scale(sl, sl)
            ctx.arc(0, 8, 190, 0, TAU)
            ctx.set_source_rgb(*INK)
            ctx.fill()
            ctx.arc(0, 0, 190, 0, TAU)
            ctx.set_source_rgb(*hx("#1B1F2A"))
            ctx.fill_preserve()
            ctx.set_source_rgb(*BLANCO)
            ctx.set_line_width(10)
            ctx.stroke()
            volante(ctx, 0, 10, 150, p=1.0, boca="flat", ojeras=1.0, rot=10 * math.sin(t * 3))
            zzz(ctx, 110, -110, t, 1.1, 1.0)
            ctx.restore()
    # nadie al volante: viñeta roja que late
    if t > T_NADIE:
        pul = 0.5 + 0.5 * math.sin((t - T_NADIE) * 9)
        g = cairo.RadialGradient(540, 860, 380, 540, 860, 1100)
        g.add_color_stop_rgba(0, *ROJO, 0)
        g.add_color_stop_rgba(1, *ROJO, (0.25 + 0.2 * pul) * prog(t, T_NADIE + 0.2, 0.3))
        ctx.set_source(g)
        ctx.paint()


# ------------------------------------------------------------------ escena 15: un día (empalme)
T_DIA = b(22) + 0.05
T_VUELTA = b(22, "mucho") - 0.2


def d_dia(ctx, t):
    fondo(ctx, t)
    q = prog(t, T_DIA, T_VUELTA - T_DIA + 0.1, "in")
    zoom(ctx, 1 + 0.25 * q, 540, 820)
    cx, cy, R = 540, 800, 360
    ctx.arc(cx, cy + 10, R, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.arc(cx, cy, R, 0, TAU)
    ctx.set_source_rgb(*PANEL)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(10)
    ctx.stroke()
    ctx.arc(cx, cy, R - 44, -math.pi / 2, -math.pi / 2 + TAU * q)
    ctx.set_source_rgb(*AMARILLO)
    ctx.set_line_width(48)
    ctx.stroke()
    for k in range(24):
        ang = TAU * k / 24 - math.pi / 2
        ctx.move_to(cx + (R - 80) * math.cos(ang), cy + (R - 80) * math.sin(ang))
        ctx.line_to(cx + (R - 96) * math.cos(ang), cy + (R - 96) * math.sin(ang))
        ctx.set_source_rgba(1, 1, 1, 0.6)
        ctx.set_line_width(5)
        ctx.stroke()
    ang = -math.pi / 2 + TAU * q
    ctx.move_to(cx, cy)
    ctx.line_to(cx + (R - 110) * math.cos(ang), cy + (R - 110) * math.sin(ang))
    ctx.set_source_rgb(*BLANCO)
    ctx.set_line_width(16)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.arc(cx, cy, 22, 0, TAU)
    ctx.fill()
    # sol y luna en el borde
    sa = -math.pi / 2 + TAU * q
    estrella(ctx, cx + (R + 70) * math.cos(sa), cy + (R + 70) * math.sin(sa), 46, 1.0, AMARILLO)
    texto(ctx, "1 DÍA", cx, cy + 130, 80, fill=BLANCO, stroke=INK, sw=10, alpha=pop(t, T_DIA + 0.2))


def d_vuelta(ctx, t):
    """Vuelve al primer cuadro: el de TOTAL es igual al de 0."""
    amt = AMT0 * prog(t, T_VUELTA + 0.05, 0.45, "out")
    fondo(ctx, t)
    ctx.translate(540, 960)
    ctx.rotate(math.radians(amt * 2.4 * per(t, 13)))
    ctx.translate(-540, -960)
    vos_borracho(ctx, t, amt)


# ------------------------------------------------------------------ escenas
ESCENAS = [
    (0.0, d_apertura),
    (b(2) - 0.06, d_lab),
    (b(5) - 0.06, d_alcoholimetro),
    (b(6) - 0.06, d_oscuro),
    (b(7) - 0.06, d_bateria),
    (b(8) - 0.06, d_palillos),
    (b(9) - 0.06, d_apagon),
    (b(10) - 0.06, d_ojos),
    (b(12) - 0.06, d_micro),
    (b(13) - 0.06, d_linea),
    (b(15) - 0.06, d_ruta),
    (b(16) - 0.06, d_volantes),
    (b(18) - 0.06, d_crono),
    (b(19) - 0.06, d_autopista),
    (b(22) - 0.06, d_dia),
    (T_VUELTA, d_vuelta),
]
XF = 0.18
WHOOSH += [t0 for t0, _ in ESCENAS[1:]]
DERIVA_CAM = {d_lab, d_bateria, d_ojos, d_linea, d_volantes}      # escenas largas: la cámara se acerca despacio


def punch(t, t0, d=0.3, amp=0.05):
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


def escena(t):
    return max(k for k, (t0, _) in enumerate(ESCENAS) if t >= t0)


def dibujar(ctx, i, t):
    t0, fn = ESCENAS[i]
    t1 = ESCENAS[i + 1][0] if i + 1 < len(ESCENAS) else TOTAL
    ctx.save()
    if i > 0:
        zoom(ctx, punch(t, t0))
    if fn in DERIVA_CAM:
        zoom(ctx, 1 + 0.035 * clamp((t - t0) / (t1 - t0)))
    fn(ctx, t)
    ctx.restore()


def componer(ctx, t):
    i = escena(t)
    t0, fn = ESCENAS[i]
    dt = t - t0
    if i > 0 and dt < XF:
        dibujar(ctx, i - 1, t)
        ctx.push_group()
        dibujar(ctx, i, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(clamp(dt / XF))
        return
    dibujar(ctx, i, t)


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

    for t0 in WHOOSH:
        if t0 not in (b(9) - 0.06,):
            ev(t0, "whoosh_suave", 0.4)
    ev(0.0, "zumbido", 0.12, d=T_NOES)
    ev(T_HIC, "boing", 0.35)
    ev(T_NOES, "whoosh", 0.4)
    ev(T_MED, "golpe", 0.8)
    ev(T_MED + 0.02, "clunk", 0.5)
    # contador de horas
    for t_a, t_b, n in ((b(2) + 0.06, T17 + 0.32, 17), (T24 - 0.3, T24 + 0.3, 7)):
        for k in range(n):
            ev(t_a + (t_b - t_a) * ease(k / n, "out"), "tick", 0.16, f=1800 + 40 * k, d=0.03)
    ev(b(2, "despierto") - 0.1, "pop", 0.35)
    ev(T_REAC - 0.05, "subida", 0.22, d=T_LENTO + 0.3 - T_REAC)
    ev(b(3) + 0.04, "pop", 0.35)
    ev(T_ALC - 0.1, "trago", 0.4)
    ev(T_IGUAL + 0.5, "ding", 0.35)
    ev(T_DUP, "zoom", 0.4)
    ev(T_DUP + 0.15, "golpe", 0.5)
    # alcoholímetro
    ev(b(5) + 0.05, "subida", 0.25, d=0.6)
    ev(T_SUPERO + 0.1, "alarma", 0.45, d=1.2)
    ev(T_COND + 0.05, "golpe", 0.45)
    # lo peor
    ev(T_PEOR, "golpe", 0.9)
    ev(b(6) + 0.05, "zumbido", 0.18, d=1.6)
    # batería
    for k in range(4):
        ev(T_PERM - 0.05 + k * 0.17, "tick", 0.25, f=900, d=0.08)
    # palillos
    ev(T_PAL, "clunk", 0.45)
    ev(T_PAL + 0.12, "clunk", 0.4)
    ev(T_SNAP, "crunch", 0.8, d=0.3)
    # apagón: silencio mientras la pantalla está a oscuras y sacudón al volver
    ev(T_APAGA - 0.02, "whoosh_suave", 0.35)
    ev(T_REABRE + 0.05, "golpe", 0.9)
    ev(T_REABRE + 0.07, "whoosh", 0.5)
    ev(T_AVIS + 0.1, "boing", 0.25)
    # ojos y nieve
    ev(T_PAREC, "whoosh_suave", 0.35)
    ev(T_NADA - 0.05, "siseo", 0.35, d=1.0)
    ev(T_MICRO - 0.1, "golpe", 0.6)
    ev(T_MICRO + 0.4, "ding", 0.3)
    # la barra de lo que ves
    for a, c, ta in HUECOS:
        ev(ta, "clic", 0.5)
    for tp in PARPADEOS:
        ev(tp, "whoosh_suave", 0.25)
    # la ruta
    ev(T_IMAG, "siseo", 0.2, d=2.2)
    ev(T_CONDUCES + 0.08, "whoosh_suave", 0.35)
    # 3 de cada 4
    for k in range(4):
        ev(T_VOL - 0.1 + 0.12 * k, "pop", 0.3)
    for tc in CIERRAN:
        ev(tc, "plop", 0.45)
    ev(b(17, "cuatro", fin=True) - 0.05, "golpe", 0.6)
    # cronómetro
    for k in range(int(SEG_MICRO)):
        ev(T_CRONO0 + k * 1.8 / SEG_MICRO, "tick", 0.35, f=1500, d=0.05)
    # autopista
    ev(T_A0, "zoom", 0.35)
    ev(T_A0, "siseo", 0.18, d=T_CANCHA - T_A0)
    ev(T_100, "ding", 0.4)
    ev(T_CANCHA, "whoosh", 0.45)
    ev(T_NADIE - 0.05, "whoosh", 0.4)
    k = 0
    while T_NADIE + 0.5 + k * 0.07 < b(22) - 0.1:            # el auto pisa la banda sonora del borde
        ev(T_NADIE + 0.5 + k * 0.07, "tick", 0.2, f=180, d=0.05)
        k += 1
    # un día
    for k in range(10):
        ev(T_DIA + (T_VUELTA - T_DIA) * ease(k / 10, "in"), "tick", 0.2, f=1300 + 60 * k, d=0.04)
    ev(T_VUELTA + 0.05, "whoosh_suave", 0.35)
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
    # silencio total de efectos mientras la pantalla está cerrada
    i0, i1 = int((T_APAGA + 0.12) * SR), int((T_REABRE + 0.04) * SR)
    mix[i0:i1] = 0
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "un_dia_sin_dormir.mp4"))
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

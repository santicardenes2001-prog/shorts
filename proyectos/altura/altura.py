"""Short "¿Por qué eres más alto por la mañana?" — animación procedural (armazón de momias.py y luna.py).

Cuerpo humano con el estilo del canal: fondo azul con puntos, zoom continuo, objetos con cara (los discos, el Sol,
la Luna) y subtítulos palabra por palabra. Vos sale solo en la apertura y en el cierre del loop (V2): el cuadro de
TOTAL es igual al de 0. Sin flechas de giro ni sonidos sostenidos (corrección de Luna v2): solo golpes cortos, y
cada tramo tiene un recurso propio para mirar.

Hilos que se repiten: la regla de pared con la escuadra sobre la cabeza, la lupa que agranda la marca (2 cm reales
se ven chicos a escala) y los discos con cara que se aplastan, sueltan agua y se vuelven a llenar.

    python proyectos/altura/altura.py --hoja 0,3,6      # hoja de fotogramas -> proyectos/altura/fotos/hoja.png
    python proyectos/altura/altura.py --probar
    python proyectos/altura/altura.py                   # render -> salidas/por_que_eres_mas_alto_a_la_manana.mp4
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
           os.path.join(ROOT, "proyectos", "cielo")):
    sys.path.insert(0, _p)
import kit  # noqa: E402
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
import cielo as C  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, bump, cartel, clamp, ease, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rng, rrect, texto)
from picante import _elipse_suave, capa, carita, fondo_azul, mezcla  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Esta noche vas a medir menos que esta mañana.",                         # b0
    "No es una ilusión: se puede medir con una regla.",                      # b1
    "¿Qué te está encogiendo mientras miras esto?",                          # b2
    "Desde que te levantas, tu cuerpo empieza a achicarse.",                 # b3
    "Al final del día, perdiste hasta 2 centímetros.",                       # b4
    "No se pierden en los huesos, sino entre ellos.",                        # b5
    "Tu columna tiene unas almohadillas llenas de agua.",                    # b6
    "Durante el día, tu propio peso las aplasta.",                           # b7
    "Sueltan agua, se afinan, y tú bajas con ellas.",                        # b8
    "Cuando te acuestas, dejan de cargar tu peso.",                          # b9
    "Vuelven a llenarse, y amaneces con tu altura completa.",                # b10
    "Entonces, ¿qué pasa si nada te aplasta nunca?",                         # b11
    "Eso ya se probó, en el espacio.",                                       # b12
    "Allá arriba, un astronauta puede crecer hasta 5 centímetros.",          # b13
    "Tanto, que cambia cómo le quedan el traje y el asiento.",               # b14
    "Pero al volver, la gravedad le cobra todo.",                            # b15
    "Con el tiempo, mide lo mismo que antes.",                               # b16
    "Vuelve a la rutina de todos en la Tierra:",                             # b17
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
HUESO = hx(kit.P["hueso"])
HUESO_OSC = hx("#E2D0AE")
DISCO = hx("#FF8FA8")
DISCO_OSC = hx("#E06A86")
DISCO_APAG = hx("#C9AEB6")
AGUA = hx("#45B0FF")
AGUA_CLARA = hx("#A8DDFF")
REGLA = hx("#FFD23F")
ACERO = hx("#D5DAE2")
ACERO_OSC = hx("#8E97A8")
CREMA = hx("#F6EEDC")
ROJO = hx("#E5383B")
VERDE = hx("#2BD45A")
VIOLETA = hx("#7B5BD6")
CIELO_DIA = hx("#8FD3FF")
CIELO_TARDE = hx("#FF9B5E")
CIELO_NOCHE = hx("#1E2656")
LUNA = hx("#F4F1D6")
LUNA_OSC = hx("#D8D3AE")
PELO = hx(kit.P["pelo"])
TRAJE = hx("#F3F5F8")
TRAJE_OSC = hx("#C3CAD6")
INTERIOR = hx("#6EC3FF")
VISOR = hx("#22345C")
PESA = hx("#4A4F5C")
PESA_CLARA = hx("#6E7586")
ARENA = hx("#E2C48D")
ARENA_OSC = hx("#B8935A")
NARANJA = hx("#FF8A3D")
PANEL = hx("#2F5FB8")
PANEL_CLARO = hx("#5C8FE8")
LCD = hx("#7CFF8A")
CAMA = hx("#5C7BD9")
CAMA_CLARA = hx("#8FA8F0")
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


def sacudida(t, t0, d=0.35, amp=14.0):
    if t < t0 or t > t0 + d:
        return 0.0, 0.0
    q = (t - t0) / d
    k = amp * (1 - q) ** 2
    return k * math.sin(t * 90), k * math.cos(t * 70)


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


def t_loop(t):
    """Tiempo para lo que gira solo (rayos del Sol): vale lo mismo en 0 y en TOTAL."""
    return t if t < TOTAL / 2 else t - TOTAL


# ------------------------------------------------------------------ Vos (solo apertura y cierre del loop)
VOS_POSES = {
    "mira": dict(look=(0.55, -1)),
    "sorpresa": dict(eyes="wide", brows="up", mouth_kind="o", look=(0.55, -1)),
    "cansado": dict(eyes="tired", brows="sad", mouth_kind="flat"),
}


@functools.lru_cache(maxsize=None)
def vos_surface(pose):
    body = kit.vos(**VOS_POSES[pose])
    png = cairosvg.svg2png(bytestring=kit.svg(520, 820, body).encode(), output_width=1040, output_height=1640)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


def vos(ctx, pose, x, y, k=1.0, alpha=1.0, sy=1.0):
    """Vos con los pies en (x, y); k = 1 es el dibujo a 520x820."""
    if alpha <= 0.01 or k <= 0.01:
        return
    s = vos_surface(pose)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(k / 2, k / 2 * sy)
    ctx.translate(-520, -1612)
    ctx.set_source_surface(s, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


# ------------------------------------------------------------------ 1. el cuarto: regla de pared, ventana y Vos
FLOOR = 1330
VOS_X, VOS_K = 390, 1.2
ALT = 172.0                                   # altura de Vos a la mañana, en cm
VOS_ALTO = 745 * VOS_K                        # del piso a la punta del pelo (el dibujo mide 745 de 61 a 806)
PXCM = VOS_ALTO / ALT
R_X0, R_X1 = 650, 722
PELO_X = VOS_X + (275 - 260) * VOS_K          # la punta del pelo está un poco a la derecha del centro
VEN = (70, 120, 300, 270)                     # ventana: x, y, ancho, alto
LX, LY, LR = 880, 800, 165                    # lupa
L_CM, L_MAG = 171.0, 42.0                     # la lupa centra 171 cm y agranda a 42 px por cm


def y_cm(c):
    return FLOOR - c * PXCM


def cabeza_y(menos_cm):
    return FLOOR - VOS_ALTO * (ALT - menos_cm) / ALT


def luna_cara(ctx, x, y, R, ojos="closed", boca="smile", a=1.0):
    if a <= 0.01 or R <= 1:
        return
    with alfa(ctx, a):
        _elipse_suave(ctx, x, y, R * 2.1, R * 2.1, LUNA, 0.25)
        ctx.arc(x, y, R, 0, TAU)
        g = cairo.RadialGradient(x - R * 0.3, y - R * 0.35, R * 0.1, x, y, R)
        g.add_color_stop_rgb(0, 1, 1, 0.94)
        g.add_color_stop_rgb(1, *LUNA)
        ctx.set_source(g)
        ctx.fill()
        for cx, cy, rr in ((0.45, -0.35, 0.16), (-0.55, 0.3, 0.12), (0.5, 0.45, 0.1)):
            elipse(ctx, x + cx * R, y + cy * R, rr * R, rr * R)
            ctx.set_source_rgba(*LUNA_OSC, 0.9)
            ctx.fill()
        ctx.arc(x, y, R, 0, TAU)
        trazo(ctx, INK, max(2, R * 0.06))
        carita(ctx, x, y - 0.06 * R, 0.6 * R, R / 150, ojos=ojos, boca=boca, rubor=True)


def cielo_color(noche):
    if noche < 0.5:
        return mezcla(CIELO_DIA, CIELO_TARDE, noche * 2)
    return mezcla(CIELO_TARDE, CIELO_NOCHE, (noche - 0.5) * 2)


def ventana(ctx, t, noche):
    x0, y0, w, h = VEN
    rrect(ctx, x0 - 18, y0 - 18, w + 36, h + 36, 24)
    rellena(ctx, CREMA, 7)
    ctx.save()
    rrect(ctx, x0, y0, w, h, 10)
    ctx.clip()
    ctx.set_source_rgb(*cielo_color(noche))
    ctx.paint()
    if noche > 0.55:
        for k, (sx, sy) in enumerate(((110, 160), (300, 150), (340, 230), (150, 250), (260, 300), (95, 330))):
            C.estrella(ctx, sx, sy, 6, a=clamp((noche - 0.55) / 0.3), halo=0.5)
    C.sol(ctx, x0 + 150, y0 + 125 + 230 * noche, 54, t_loop(t), boca="smile")
    luna_cara(ctx, x0 + 160, y0 + 120 + 230 * (1 - noche), 50)
    # techos de la ciudad
    ctx.move_to(x0, y0 + h)
    for bx, bh in ((0, 50), (60, 80), (110, 40), (170, 95), (230, 60), (300, 60)):
        ctx.line_to(x0 + bx, y0 + h - bh)
        ctx.line_to(x0 + min(w, bx + 55), y0 + h - bh)
    ctx.line_to(x0 + w, y0 + h)
    ctx.close_path()
    ctx.set_source_rgba(*mezcla(hx("#5B6BA8"), hx("#141A3A"), noche), 1)
    ctx.fill()
    ctx.restore()
    for xx, yy, ww, hh in ((x0 + w / 2 - 6, y0, 12, h), (x0, y0 + h / 2 - 6, w, 12)):
        ctx.rectangle(xx, yy, ww, hh)
        ctx.set_source_rgb(*CREMA)
        ctx.fill()
    rrect(ctx, x0, y0, w, h, 10)
    trazo(ctx, INK, 6)
    rrect(ctx, x0 - 34, y0 + h + 14, w + 68, 26, 8)
    rellena(ctx, CREMA, 6)


def regla_pared(ctx, brillo=0.0):
    top = y_cm(200) - 24
    if brillo > 0.01:
        _elipse_suave(ctx, (R_X0 + R_X1) / 2, (top + FLOOR) / 2, 120, 620, AMARILLO, 0.35 * brillo)
    rrect(ctx, R_X0, top, R_X1 - R_X0, FLOOR - top, 10)
    rellena(ctx, mezcla(REGLA, BLANCO, 0.4 * brillo), 6)
    for c in range(0, 201, 5):
        y = y_cm(c)
        L = 30 if c % 10 == 0 else 16
        ctx.move_to(R_X0 + 3, y)
        ctx.line_to(R_X0 + L, y)
        trazo(ctx, INK, 3.5 if c % 10 == 0 else 2.5)
    for c in range(20, 201, 20):
        texto(ctx, str(c), R_X1 - 8, y_cm(c), 21, fill=INK, stroke=None, ax=1.0)


def escuadra(ctx, y):
    """Tope de la regla: la barra apoya su borde de abajo en y."""
    rrect(ctx, R_X0 - 14, y - 34, R_X1 - R_X0 + 28, 46, 10)
    rellena(ctx, ACERO, 6)
    rrect(ctx, PELO_X - 70, y - 16, R_X0 - (PELO_X - 70) + 4, 16, 5)
    rellena(ctx, ACERO, 5)


def marca(ctx, y, col, icono, a):
    """Rayita sobre la regla con su iconito (sol o luna) a la izquierda."""
    if a <= 0.01:
        return
    with alfa(ctx, a):
        ctx.move_to(R_X0 - 26, y)
        ctx.line_to(R_X1 + 6, y)
        trazo(ctx, INK, 11)
        ctx.move_to(R_X0 - 26, y)
        ctx.line_to(R_X1 + 6, y)
        trazo(ctx, col, 6)
        if icono == "sol":
            C.sol(ctx, R_X1 + 44, y, 17, 0.0, con_cara=0.0)
        else:
            luna_cara(ctx, R_X1 + 44, y, 17)


def reloj_digital(ctx, x, y, s, hora):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        rrect(ctx, -150, -66, 300, 132, 26)
        rellena(ctx, hx("#1A1F33"), 7)
        rrect(ctx, -128, -46, 256, 92, 14)
        ctx.set_source_rgb(*hx("#0E2A18"))
        ctx.fill()
        texto(ctx, f"{int(hora):02d}:00", 0, 2, 76, fill=LCD, stroke=None)


def lupa(ctx, t, s, menos_cm, sol_a=0.0, luna_a=0.0, llave=0.0, focus_a=1.0):
    """Lupa sobre la regla: agranda la zona de la cabeza para que se vean los 2 cm."""
    if s <= 0.01:
        return
    fy = cabeza_y(menos_cm)
    fx = (R_X0 + R_X1) / 2

    def yl(cm):
        return LY + (L_CM - cm) * L_MAG

    with alfa(ctx, min(1.0, s * 1.5) * focus_a):
        elipse(ctx, fx, fy, 34, 34)
        trazo(ctx, BLANCO, 5, 0.9)
        ctx.move_to(fx + 30, fy + 12)
        ctx.line_to(LX - LR * 0.86, LY - LR * 0.5)
        trazo(ctx, BLANCO, 4, 0.7)
    with en(ctx, LX, LY, s), en(ctx, -LX, -LY):
        ctx.save()
        ctx.arc(LX, LY, LR, 0, TAU)
        ctx.clip()
        ctx.set_source_rgb(*hx("#24306B"))
        ctx.paint()
        # la cabeza (pelo) que apoya en la escuadra
        yh = yl(ALT - menos_cm)
        ctx.arc(LX - 150, yh + 330, 330, 0, TAU)
        rellena(ctx, PELO, 8)
        # la regla agrandada
        rx0, rx1 = LX - 20, LX + 100
        ctx.rectangle(rx0, LY - LR - 10, rx1 - rx0, 2 * LR + 20)
        rellena(ctx, REGLA, 6)
        for mm in range(int((L_CM - 5) * 10), int((L_CM + 5) * 10) + 1):
            y = yl(mm / 10)
            if abs(y - LY) > LR + 5:
                continue
            L, w = (40, 4) if mm % 10 == 0 else ((26, 3) if mm % 5 == 0 else (14, 2))
            ctx.move_to(rx0, y)
            ctx.line_to(rx0 + L, y)
            trazo(ctx, INK, w)
            if mm % 10 == 0:
                texto(ctx, str(mm // 10), rx1 - 8, y, 28, fill=INK, stroke=None, ax=1.0)
        # marcas de la mañana y de la noche
        for cm, col, a, ic in ((ALT, AMARILLO, sol_a, "sol"), (ALT - 2, AGUA_CLARA, luna_a, "luna")):
            if a > 0.01:
                with alfa(ctx, a):
                    ctx.move_to(LX - 200, yl(cm))
                    ctx.line_to(rx1, yl(cm))
                    ctx.set_dash([18, 12])
                    trazo(ctx, col, 7)
                    ctx.set_dash([])
                    if ic == "sol":
                        C.sol(ctx, LX - 70, yl(cm) - 34, 20, 0.0, con_cara=0.0)
                    else:
                        luna_cara(ctx, LX - 70, yl(cm) + 32, 20)
        # la escuadra apoyada en el pelo
        rrect(ctx, LX - 210, yh - 26, rx0 - (LX - 210) + 30, 26, 6)
        rellena(ctx, ACERO, 6)
        if llave > 0.01:
            with alfa(ctx, llave):
                x = LX - 130
                ctx.move_to(x - 18, yl(ALT))
                ctx.line_to(x, yl(ALT))
                ctx.line_to(x, yl(ALT - 2))
                ctx.line_to(x - 18, yl(ALT - 2))
                trazo(ctx, INK, 14)
                ctx.move_to(x - 18, yl(ALT))
                ctx.line_to(x, yl(ALT))
                ctx.line_to(x, yl(ALT - 2))
                ctx.line_to(x - 18, yl(ALT - 2))
                trazo(ctx, ROJO, 8)
        ctx.restore()
        ctx.arc(LX, LY, LR, 0, TAU)
        trazo(ctx, INK, 22)
        ctx.arc(LX, LY, LR, 0, TAU)
        trazo(ctx, ACERO_OSC, 11)
        ctx.new_sub_path()
        ctx.arc(LX, LY, LR - 26, math.radians(200), math.radians(250))
        trazo(ctx, BLANCO, 9, 0.5)


def cuarto(ctx, t, noche, menos_cm, pose, brillo_regla=0.0, marca_sol=0.0, marca_luna=0.0):
    """El cuarto completo. Con noche = 0, menos_cm = 0 y pose "mira" es el cuadro del loop."""
    fondo(ctx, t, 0.15 + 0.3 * noche)
    ventana(ctx, t, noche)
    regla_pared(ctx, brillo_regla)
    ctx.rectangle(-40, FLOOR, 1160, 40)
    rellena(ctx, hx("#33407A"), 6)
    _elipse_suave(ctx, VOS_X, FLOOR + 6, 250, 30, (0, 0, 0), 0.35)
    vos(ctx, pose, VOS_X, FLOOR, k=VOS_K, sy=(ALT - menos_cm) / ALT)
    marca(ctx, y_cm(ALT), AMARILLO, "sol", marca_sol)
    marca(ctx, y_cm(ALT - 2), AGUA_CLARA, "luna", marca_luna)
    escuadra(ctx, cabeza_y(menos_cm))


# tiempos de la apertura
T_NOCHE = b(0, "noche")
T_MENOS = b(0, "menos")
T_MANANA = b(0, "manana")
T_ILUSION = b(1, "ilusion")
T_MEDIR1 = b(1, "medir")
T_REGLA = b(1, "regla")
T_ENCOG = b(2, "encogiendo")
T_MIENTRAS = b(2, "mientras")
T_LEVANT = b(3, "levantas")
T_CUERPO = b(3, "cuerpo")
T_FINAL = b(4, "final")
T_DIA4 = b(4, "dia")
T_2CM = b(4, "2")
DIA0, DIA1 = T_CUERPO - 0.1, T_DIA4 + 0.15           # el día pasa entre estos dos tiempos
HORAS = [DIA0 + (DIA1 - DIA0) * k / 16 for k in range(1, 17)]


def hora_de(t):
    return 7 + sum(1 for h in HORAS if t >= h)


def apertura_estado(t):
    """noche, cm perdidos y pose de Vos en la apertura (0 a 13,4 s)."""
    if t < b(2):
        noche = prog(t, T_NOCHE, 0.25) * (1 - prog(t, T_MANANA, 0.25))
        menos = 2 * prog(t, T_NOCHE + 0.05, 0.3) * (1 - prog(t, T_MANANA + 0.05, 0.3))
        pose = "cansado" if T_NOCHE + 0.1 <= t < T_MANANA + 0.1 else "mira"
        return noche, menos, pose
    paso = (hora_de(t) - 7) / 16
    noche = prog(t, DIA0, DIA1 - DIA0, "linear")
    menos = 2 * paso
    if t < T_ENCOG:
        pose = "mira"
    elif t < T_LEVANT:
        pose = "sorpresa"
    elif t < T_FINAL:
        pose = "mira"
    else:
        pose = "cansado"
    return noche, menos, pose


def d_apertura(ctx, t):
    z = 1 + 0.06 * prog(t, 0.0, b(2), "out") + 0.03 * prog(t, b(2), b(5) - b(2), "linear")
    noche, menos, pose = apertura_estado(t)
    ctx.save()
    zoom(ctx, z, 520, 760)
    brillo = bump(t, T_MEDIR1, 0.6, 1.0) - 1 if t < b(2) else 0.0
    sol_a = prog(t, T_NOCHE + 0.2, 0.25) if t < b(5) else 0.0
    luna_a = prog(t, T_MANANA + 0.15, 0.25)
    cuarto(ctx, t, noche, menos, pose, brillo_regla=brillo, marca_sol=sol_a, marca_luna=luna_a)
    ctx.restore()
    # carteles y la lupa (fuera del zoom)
    kartel(ctx, "¿ILUSIÓN?", 760, 250, 76, t, T_ILUSION - 0.05, T_MEDIR1 - 0.1, box=VIOLETA, fg=BLANCO, rot=-3)
    if t < T_MEDIR1 - 0.1:
        C.tachado(ctx, 760, 250, 420, prog(t, T_ILUSION + 0.45, 0.25, "out"))
    sl = pop(t, T_REGLA - 0.1, 0.4)
    lupa(ctx, t, sl, menos, sol_a=sol_a, luna_a=luna_a, llave=prog(t, T_2CM, 0.3, "out"))
    signo(ctx, "?", 870, 360, 300, t, b(2) - 0.02, T_MIENTRAS - 0.1)
    if T_MIENTRAS - 0.05 <= t < b(3) - 0.05:
        s = pop(t, T_MIENTRAS - 0.05) * sale(t, b(3) - 0.25)
        cartel(ctx, "AHORA MISMO", 870, 300, 56, box=BLANCO, s=s, rot=2)
        if s > 0.3:
            ctx.arc(870 - 205 * s, 300, 13 * s, 0, TAU)
            ctx.set_source_rgba(*ROJO, 0.5 + 0.5 * (math.sin(t * 14) > 0))
            ctx.fill()
    reloj_digital(ctx, 885, 300, pop(t, T_LEVANT - 0.1) * sale(t, b(5) - 0.2), hora_de(t))
    kartel(ctx, "−2 cm", 880, 1040, 84, t, T_2CM, box=ROJO, fg=BLANCO, rot=-3)


# ------------------------------------------------------------------ 2. la columna entera (vista de costado)
def _niveles():
    """Nombre, tipo, alto del cuerpo, profundidad y disco de abajo, en mm."""
    N = [("C1", "C1", 10, 13, 0.0), ("C2", "C2", 15, 15, 5.0)]
    for k in range(3, 8):
        N.append((f"C{k}", "C", 13, 16, 5.0))
    for k in range(12):
        u = k / 11
        N.append((f"T{k + 1}", "T", 17 + 7 * u, 18 + 14 * u, 7.0 if k == 11 else 4 + 2 * u))
    for k, (h, d, dd) in enumerate([(26, 33, 9), (27, 35, 10), (28, 36, 11), (28, 37, 12), (27, 36, 11)]):
        N.append((f"L{k + 1}", "L", h, d, dd))
    return N


NIVELES = _niveles()
SACRO, COXIS = 100.0, 28.0
# línea media de los cuerpos (mm; x positiva = atrás, a la derecha). Lordosis cervical y lumbar hacia adelante,
# cifosis dorsal hacia atrás, sacro hacia atrás y cóccix que vuelve hacia adelante.
CTRL = [(0, 0), (-9, 55), (0, 122), (22, 205), (29, 272), (18, 350), (0, 415), (-17, 480), (-14, 545), (0, 590),
        (24, 645), (36, 695), (30, 735)]


def _catmull(pts, n=30):
    Pp = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(Pp) - 2):
        p0, p1, p2, p3 = (np.array(Pp[j], float) for j in (i - 1, i, i + 1, i + 2))
        for k in range(n):
            u = k / n
            out.append(0.5 * (2 * p1 + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    out.append(np.array(pts[-1], float))
    return np.array(out)


_CURVA = _catmull(CTRL)
_ARC = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(_CURVA, axis=0).T))])
L_TOTAL = sum(h + dd for _, _, h, _, dd in NIVELES) + SACRO + COXIS


def curva(s):
    u = s / L_TOTAL * _ARC[-1]
    return float(np.interp(u, _ARC, _CURVA[:, 0])), float(np.interp(u, _ARC, _CURVA[:, 1]))


def angulo(s):
    x0, y0 = curva(max(0, s - 2))
    x1, y1 = curva(min(L_TOTAL, s + 2))
    return math.atan2(-(x1 - x0), y1 - y0)


def _vertebras():
    V, s = [], 0.0
    for nom, tipo, h, d, dd in NIVELES:
        c = curva(s + h / 2)
        V.append(dict(nom=nom, tipo=tipo, h=h, d=d, disco=dd, c=c, th=angulo(s + h / 2)))
        s += h + dd
    return V, s


VERT, S_SACRO = _vertebras()


def a_mundo(v, lx, ly):
    c, s = math.cos(v["th"]), math.sin(v["th"])
    return v["c"][0] + lx * c - ly * s, v["c"][1] + lx * s + ly * c


ESPINOSA = {          # ángulo (grados, positivo = hacia abajo), largo (en profundidades del cuerpo), ancho de la punta
    "C": (14, 0.5, 0.25), "C2": (10, 0.68, 0.32), "C7": (18, 0.95, 0.22), "T": (55, 1.15, 0.12), "L": (4, 0.86, 0.6),
}


def arco_posterior(ctx, h, d, esp):
    """Pedículo, apófisis articulares, lámina y apófisis espinosa en un solo contorno (adelante a la izquierda)."""
    ang, L, ancho = ESPINOSA[esp]
    a = math.radians(ang)
    cx, cy = math.cos(a), math.sin(a)
    bu = (0.98 * d, -0.34 * h)              # base de la espinosa, arriba
    bl = (1.0 * d, 0.2 * h)                 # base de la espinosa, abajo
    mid = ((bu[0] + bl[0]) / 2 + L * d * cx, (bu[1] + bl[1]) / 2 + L * d * cy)
    nx, ny = -cy, cx                        # perpendicular a la espinosa
    half = ancho * h * 0.5
    tu = (mid[0] - nx * half, mid[1] - ny * half)
    tl = (mid[0] + nx * half, mid[1] + ny * half)
    ctx.move_to(0.45 * d, -0.38 * h)
    ctx.line_to(0.66 * d, -0.4 * h)
    ctx.curve_to(0.7 * d, -0.5 * h, 0.72 * d, -0.62 * h, 0.8 * d, -0.7 * h)       # apófisis articular superior
    ctx.curve_to(0.86 * d, -0.75 * h, 0.93 * d, -0.66 * h, 0.92 * d, -0.56 * h)
    ctx.curve_to(0.92 * d, -0.46 * h, 0.94 * d, -0.38 * h, bu[0], bu[1])
    ctx.curve_to(bu[0] + 0.5 * L * d * cx, bu[1] + 0.5 * L * d * cy - 0.05 * h, tu[0] - 0.08 * d * cx,
                 tu[1] - 0.08 * d * cy, tu[0], tu[1])
    ctx.curve_to(tu[0] + 0.06 * d * cx + nx * 0.2 * half, tu[1] + 0.06 * d * cy + ny * 0.2 * half,
                 tl[0] + 0.06 * d * cx - nx * 0.2 * half, tl[1] + 0.06 * d * cy - ny * 0.2 * half, tl[0], tl[1])
    ctx.curve_to(tl[0] - 0.3 * L * d * cx, tl[1] - 0.3 * L * d * cy, bl[0] + 0.2 * L * d * cx,
                 bl[1] + 0.2 * L * d * cy + 0.04 * h, bl[0], bl[1])
    ctx.curve_to(0.98 * d, 0.32 * h, 0.97 * d, 0.48 * h, 0.92 * d, 0.62 * h)       # apófisis articular inferior
    ctx.curve_to(0.88 * d, 0.7 * h, 0.8 * d, 0.68 * h, 0.79 * d, 0.56 * h)
    ctx.curve_to(0.78 * d, 0.4 * h, 0.76 * d, 0.22 * h, 0.68 * d, 0.1 * h)        # escotadura (agujero de conjunción)
    ctx.curve_to(0.62 * d, 0.03 * h, 0.55 * d, 0.02 * h, 0.45 * d, 0.02 * h)
    ctx.close_path()


def vertebra(ctx, tipo, h, d, lw, fill=HUESO, fill2=HUESO_OSC, solo=None, esp=None):
    """Vértebra de costado en coordenadas locales (mm): adelante a la izquierda, centro del cuerpo en 0.
    solo = "atras" dibuja solo el arco posterior; solo = "cuerpo", solo el cuerpo."""
    if solo != "cuerpo":
        if tipo == "C1":
            elipse(ctx, -d * 0.25, 0, d * 0.22, h * 0.42)
            rellena(ctx, fill, lw)
            ctx.move_to(d * 0.05, -h * 0.45)
            ctx.curve_to(d * 0.6, -h * 0.55, d * 1.2, -h * 0.3, d * 1.5, -h * 0.25)
            ctx.curve_to(d * 1.75, -h * 0.25, d * 1.75, h * 0.35, d * 1.5, h * 0.3)
            ctx.curve_to(d * 1.1, h * 0.25, d * 0.6, h * 0.5, d * 0.05, h * 0.45)
            ctx.close_path()
            rellena(ctx, fill2, lw)
        else:
            arco_posterior(ctx, h, d, esp or ("C" if tipo in ("C", "C2") else tipo))
            rellena(ctx, fill2, lw)
            elipse(ctx, 0.66 * d, -0.14 * h, 0.07 * d, 0.15 * h)         # apófisis transversa, vista de punta
            rellena(ctx, mezcla(fill2, INK, 0.12), lw * 0.7)
    if solo != "atras" and tipo != "C1":
        if tipo == "C2":             # la apófisis odontoides sube hacia el atlas
            rrect(ctx, -d * 0.3, -h / 2 - 11, d * 0.42, 16, 4)
            rellena(ctx, fill, lw)
        r = min(h, d) * 0.2
        ctx.move_to(-d / 2 + r, -h / 2)
        ctx.line_to(d / 2 - r, -h / 2)
        ctx.curve_to(d / 2, -h / 2, d / 2, -h / 2, d / 2, -h / 2 + r)
        ctx.line_to(d / 2, h / 2 - r)
        ctx.curve_to(d / 2, h / 2, d / 2, h / 2, d / 2 - r, h / 2)
        ctx.line_to(-d / 2 + r, h / 2)
        ctx.curve_to(-d / 2, h / 2, -d / 2 - 1.2, h * 0.25, -d / 2 - 1.2, 0)   # cara anterior apenas cóncava
        ctx.curve_to(-d / 2 - 1.2, -h * 0.25, -d / 2, -h / 2, -d / 2 + r, -h / 2)
        ctx.close_path()
        rellena(ctx, fill, lw)


def disco(ctx, Aa, Ap, Bp, Ba, lw, col=DISCO, agua=0.0, cara=None, cara_a=0.0, brillo=0.0, ghost=False, cara_rot=0.0):
    """Disco entre dos cuerpos. Aa/Ap: esquinas de abajo del cuerpo de arriba (adelante/atrás); Bp/Ba: esquinas
    de arriba del cuerpo de abajo. cara = (ojos, boca)."""
    am = ((Aa[0] + Ba[0]) / 2, (Aa[1] + Ba[1]) / 2)
    pm = ((Ap[0] + Bp[0]) / 2, (Ap[1] + Bp[1]) / 2)
    dx, dy = pm[0] - am[0], pm[1] - am[1]
    prof = math.hypot(dx, dy) or 1.0
    ux, uy = dx / prof, dy / prof
    alto = (math.hypot(Aa[0] - Ba[0], Aa[1] - Ba[1]) + math.hypot(Ap[0] - Bp[0], Ap[1] - Bp[1])) / 2
    bul = 0.12 * alto + 0.6
    cx, cy = (am[0] + pm[0]) / 2, (am[1] + pm[1]) / 2

    def forma():
        ctx.move_to(*Aa)
        ctx.line_to(*Ap)
        ctx.curve_to(Ap[0] + ux * bul * 1.3, Ap[1] + uy * bul * 1.3, Bp[0] + ux * bul * 1.3, Bp[1] + uy * bul * 1.3,
                     *Bp)
        ctx.line_to(*Ba)
        ctx.curve_to(Ba[0] - ux * bul * 1.3, Ba[1] - uy * bul * 1.3, Aa[0] - ux * bul * 1.3, Aa[1] - uy * bul * 1.3,
                     *Aa)
        ctx.close_path()

    if ghost:
        forma()
        ctx.set_dash([2.2, 1.6])
        trazo(ctx, BLANCO, lw * 0.6, 0.75)
        ctx.set_dash([])
        return
    if brillo > 0.01:
        _elipse_suave(ctx, cx, cy, prof * 0.9, alto * 2.2 + 4, DISCO, 0.55 * brillo)
    forma()
    rellena(ctx, col, lw)
    ang = math.atan2(uy, ux)
    with en(ctx, cx, cy, 1.0, ang):
        # anillo fibroso: láminas
        for k in (0.36, 0.42):
            elipse(ctx, 0.04 * prof, 0, prof * k, alto * 0.38)
            trazo(ctx, DISCO_OSC, lw * 0.35, 0.8)
        # núcleo pulposo: gel con mucha agua, un poco hacia atrás
        ncol = mezcla(hx("#FFB3C4"), AGUA, agua)
        elipse(ctx, 0.1 * prof, 0, prof * 0.24, alto * 0.27)
        ctx.set_source_rgb(*ncol)
        ctx.fill()
        if agua > 0.3:
            elipse(ctx, 0.04 * prof, -alto * 0.09, prof * 0.1, alto * 0.07)
            ctx.set_source_rgba(1, 1, 1, 0.55 * agua)
            ctx.fill()
        if cara and cara_a > 0.01:
            ojos, boca = cara
            r = alto / 64
            with alfa(ctx, cara_a), en(ctx, -0.2 * prof, 0, 1.0, cara_rot - ang):
                carita(ctx, 0, -alto * 0.1, 0.42 * alto, r, ojos=ojos, boca=boca, dy_boca=alto * 0.2, rubor=True)


def sacro(ctx, lw, fill=HUESO, fill2=HUESO_OSC):
    n = 24
    s0, s1 = S_SACRO, S_SACRO + SACRO
    ant, post = [], []
    for k in range(n + 1):
        s = s0 + (s1 - s0) * k / n
        x, y = curva(s)
        th = angulo(s)
        d = lerp(42, 13, (k / n) ** 1.2)
        c, si = math.cos(th), math.sin(th)
        ant.append((x - d * 0.5 * c, y - d * 0.5 * si))
        post.append((x + d * 0.62 * c, y + d * 0.62 * si))
    ctx.move_to(*ant[0])
    for p in post:
        ctx.line_to(*p)
    for p in reversed(ant):
        ctx.line_to(*p)
    ctx.close_path()
    rellena(ctx, fill, lw)
    for k in (5, 10, 15, 19):          # líneas de las vértebras sacras fusionadas
        ctx.move_to(*ant[k])
        ctx.line_to(*post[k])
        trazo(ctx, fill2, lw * 0.7)
    for k in (3, 8, 13, 17):           # cresta sacra media
        x, y = post[k]
        th = angulo(s0 + (s1 - s0) * k / n)
        elipse(ctx, x + 3 * math.cos(th), y + 3 * math.sin(th), 3.4, 3.4)
        rellena(ctx, fill2, lw * 0.7)
    s = s1
    for k, (hh, dd) in enumerate(((8, 11), (7, 9), (6, 7), (5, 5))):
        x, y = curva(s + hh / 2 + 0.6)
        with en(ctx, x, y, 1.0, angulo(s + hh / 2)):
            rrect(ctx, -dd / 2, -hh / 2, dd, hh, min(hh, dd) * 0.35)
            rellena(ctx, fill, lw)
        s += hh + 1.2


def columna_entera(ctx, lw, hueso_brillo=0.0, discos_t=None, agua=0.0, caras_a=0.0, cara=None):
    """La columna completa en mm. discos_t(i) da (color, brillo) de cada disco."""
    fill = mezcla(HUESO, BLANCO, hueso_brillo)
    fill2 = mezcla(HUESO_OSC, BLANCO, hueso_brillo * 0.8)
    for v in VERT:
        with en(ctx, v["c"][0], v["c"][1], 1.0, v["th"]):
            vertebra(ctx, v["tipo"], v["h"], v["d"], lw, fill, fill2, solo="atras",
                     esp="C7" if v["nom"] == "C7" else ("C2" if v["nom"] == "C2" else None))
    sacro(ctx, lw, fill, fill2)
    idx = 0
    for i, v in enumerate(VERT):
        if v["disco"] <= 0:
            continue
        w = VERT[i + 1] if i + 1 < len(VERT) else None
        Aa, Ap = a_mundo(v, -v["d"] / 2, v["h"] / 2), a_mundo(v, v["d"] / 2, v["h"] / 2)
        if w is None:        # L5/S1: el disco apoya en la base del sacro
            th = angulo(S_SACRO)
            x, y = curva(S_SACRO)
            c, si = math.cos(th), math.sin(th)
            Ba, Bp = (x - 21 * c, y - 21 * si), (x + 21 * c, y + 21 * si)
        else:
            Ba, Bp = a_mundo(w, -w["d"] / 2, -w["h"] / 2), a_mundo(w, w["d"] / 2, -w["h"] / 2)
        col, br = discos_t(idx) if discos_t else (DISCO, 0.0)
        disco(ctx, Aa, Ap, Bp, Ba, lw, col=col, agua=agua, cara=cara, cara_a=caras_a if v["tipo"] == "L" else 0.0,
              brillo=br)
        idx += 1
    for v in VERT:
        with en(ctx, v["c"][0], v["c"][1], 1.0, v["th"]):
            vertebra(ctx, v["tipo"], v["h"], v["d"], lw, fill, fill2, solo="cuerpo")


SILUETA = [(48, 92), (52, 22), (76, -62), (42, -150), (-38, -186), (-118, -152), (-148, -88), (-150, -44),
           (-176, -12), (-152, 10), (-160, 28), (-150, 52), (-116, 70), (-78, 84), (-82, 150), (-165, 205),
           (-205, 300), (-198, 405), (-176, 485), (-162, 565), (-142, 650), (-128, 790), (118, 790), (142, 700),
           (112, 612), (72, 525), (80, 425), (104, 305), (96, 205), (60, 145)]


def silueta(ctx, lw, a=1.0):
    """Perfil del cuerpo (mirando a la izquierda) alrededor de la columna, como en una radiografía."""
    if a <= 0.01:
        return
    pts = _catmull(SILUETA + [SILUETA[0]], 10)
    g = cairo.LinearGradient(0, 600, 0, 790)
    g.add_color_stop_rgba(0, *AGUA_CLARA, 0.16 * a)
    g.add_color_stop_rgba(1, *AGUA_CLARA, 0.0)
    ctx.move_to(*pts[0])
    for x, y in pts[1:]:
        ctx.line_to(x, y)
    ctx.close_path()
    ctx.set_source(g)
    ctx.fill()
    ctx.move_to(*pts[0])
    for x, y in pts[1:]:
        if y > 700:
            ctx.move_to(x, y)
            continue
        ctx.line_to(x, y)
    trazo(ctx, AGUA_CLARA, lw * 1.4, 0.55 * a)



N_DISCOS = sum(1 for v in VERT if v["disco"] > 0)
COL_X0, COL_Y0, MM_F = 528, 262, 1.36        # dónde va el borde de arriba de la columna y cuántos px por mm
L4 = next(v for v in VERT if v["nom"] == "L4")
FOCO = (COL_X0 + L4["c"][0] * MM_F, COL_Y0 + (L4["c"][1] - 18) * MM_F)

T_PIERDEN = b(5, "pierden")
T_HUESOS = b(5, "huesos")
T_SINO = b(5, "sino")
T_ENTRE = b(5, "entre")
T_COLUMNA = b(6, "columna")
T_ALMOH = b(6, "almohadillas")
T_LLENAS = b(6, "llenas")
T_AGUA6 = b(6, "agua")
Z0, Z1 = T_ALMOH - 0.15, T_LLENAS + 0.1


def d_columna(ctx, t):
    fondo(ctx, t, 0.25)
    pz = prog(t, Z0, Z1 - Z0, "inout")
    z = lerp(1.0, 3.9, pz) * (1 + 0.04 * prog(t, Z1, b(7) - Z1, "linear")) * (1 + 0.03 * prog(t, b(5), Z0 - b(5),
                                                                                                "linear"))
    fx, fy = lerp(540, FOCO[0], pz), lerp(860, FOCO[1], pz)
    hb = (bump(t, T_HUESOS, 0.7, 1.0) - 1) * 0.9

    def discos_t(i):
        t_i = T_SINO + 0.1 + (T_ENTRE + 0.5 - T_SINO) * i / (N_DISCOS - 1)
        k = prog(t, t_i, 0.15, "out")
        return mezcla(DISCO_APAG, DISCO, k), (bump(t, t_i, 0.35, 1.0) - 1) * 0.9

    caras_a = prog(t, T_ALMOH + 0.35, 0.3)
    agua = prog(t, T_LLENAS, 0.5)
    ctx.save()
    ctx.translate(540, 860)
    ctx.scale(z, z)
    ctx.translate(-fx, -fy)
    ctx.translate(COL_X0, COL_Y0)
    ctx.scale(MM_F, MM_F)
    lw = 2.1 if z < 2 else lerp(2.1, 1.25, clamp((z - 2) / 1.9))
    silueta(ctx, lw, a=1 - 0.6 * pz)
    columna_entera(ctx, lw, hueso_brillo=hb, discos_t=discos_t, agua=agua, caras_a=caras_a,
                   cara=("dot", "smile"))
    ctx.restore()
    kartel(ctx, "HUESOS", 840, 470, 70, t, T_HUESOS - 0.05, T_SINO + 0.1, box=BLANCO, rot=3)
    if T_HUESOS + 0.3 <= t < T_SINO + 0.1:
        C.cruz(ctx, 840, 600, 46, pop(t, T_HUESOS + 0.3, 0.3) * sale(t, T_SINO))
    if t < Z0 + 0.1:
        C.tilde(ctx, 840, 780, 52, pop(t, T_ENTRE + 0.15, 0.3) * sale(t, Z0 - 0.1))
    kartel(ctx, "TU COLUMNA", 300, 290, 66, t, T_COLUMNA, Z0 + 0.05, box=AMARILLO, rot=-3)
    kartel(ctx, "DISCOS", 540, 300, 84, t, T_ALMOH + 0.3, box=DISCO, rot=-2)
    if t >= T_AGUA6 - 0.1:
        for k, (x, y) in enumerate(((330, 470), (760, 520), (840, 1160), (250, 1210))):
            s = pop(t, T_AGUA6 - 0.1 + 0.08 * k, 0.3)
            K.gota(ctx, x, y + 6 * math.sin(t * 5 + k), 22 * s, AGUA)


# ------------------------------------------------------------------ 3. la pila de tres vértebras (L3, L4 y L5)
SX, SY, MM5 = 330, 900, 7.0
PILA = [("L3", 28, 36, 11), ("L4", 28, 37, 12), ("L5", 27, 36, 0)]
CF_MIN = 0.85                 # los discos pierden hasta un 15% de su alto en el día


def pila_geo(cf):
    """Centros (local, mm) y discos de la pila. El borde de abajo de L5 queda fijo en y = 53."""
    y = 53.0
    cuerpos = []
    for nom, h, d, dd in reversed(PILA):
        if cuerpos:
            y -= dd * cf
        cuerpos.append(dict(nom=nom, h=h, d=d, disco=dd, cy=y - h / 2))
        y -= h
    cuerpos.reverse()
    discos = []
    for a, c in zip(cuerpos[:-1], cuerpos[1:]):
        Aa, Ap = (-a["d"] / 2, a["cy"] + a["h"] / 2), (a["d"] / 2, a["cy"] + a["h"] / 2)
        Ba, Bp = (-c["d"] / 2, c["cy"] - c["h"] / 2), (c["d"] / 2, c["cy"] - c["h"] / 2)
        discos.append((Aa, Ap, Bp, Ba))
    return cuerpos, discos, y          # y = borde de arriba de L3


def pila_pt(lx, ly, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    return SX + MM5 * (lx * c - ly * s), SY + MM5 * (lx * s + ly * c)


def pila(ctx, cf, rot=0.0, cara=("dot", "smile"), agua=1.0, ghost=0.0, dx=0.0, dy=0.0):
    cuerpos, discos, _ = pila_geo(cf)
    ctx.save()
    ctx.translate(SX + dx, SY + dy)
    ctx.scale(MM5, MM5)
    ctx.rotate(rot)
    lw = 1.3
    for c in cuerpos:
        with en(ctx, 0, c["cy"]):
            vertebra(ctx, "L", c["h"], c["d"], lw, solo="atras")
    for Aa, Ap, Bp, Ba in discos:
        disco(ctx, Aa, Ap, Bp, Ba, lw, agua=agua, cara=cara, cara_a=1.0, cara_rot=-rot)
    for c in cuerpos:
        with en(ctx, 0, c["cy"]):
            vertebra(ctx, "L", c["h"], c["d"], lw, solo="cuerpo")
    if ghost > 0.01:
        _, d1, _ = pila_geo(1.0)
        with alfa(ctx, ghost):
            for Aa, Ap, Bp, Ba in d1:
                disco(ctx, Aa, Ap, Bp, Ba, lw, ghost=True)
    ctx.restore()


def pesa(ctx, x, y_base, s=1.0, a=1.0):
    """Pesa de hierro con "TU PESO"; (x, y_base) es el centro del borde de abajo."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y_base, s), alfa(ctx, a):
        ctx.new_sub_path()
        ctx.arc(0, -190, 62, math.pi, 0)
        trazo(ctx, INK, 40)
        ctx.new_sub_path()
        ctx.arc(0, -190, 62, math.pi, 0)
        trazo(ctx, PESA_CLARA, 26)
        ctx.move_to(-115, 0)
        ctx.line_to(-88, -190)
        ctx.line_to(88, -190)
        ctx.line_to(115, 0)
        ctx.close_path()
        rellena(ctx, PESA, 8)
        ctx.move_to(-82, -168)
        ctx.line_to(-98, -30)
        trazo(ctx, BLANCO, 8, 0.25)
        texto(ctx, "TU", 0, -128, 40, fill=BLANCO, stroke=None)
        texto(ctx, "PESO", 0, -80, 52, fill=BLANCO, stroke=None)


def regla_pila(ctx, y_top, y_orig, a=1.0, marca_ok=0.0):
    """Regla al costado de la pila: la flechita roja marca el borde de arriba."""
    if a <= 0.01:
        return
    x0, x1, yb, yt = 870, 930, SY + 53 * MM5, SY - 75 * MM5
    with alfa(ctx, a):
        rrect(ctx, x0, yt, x1 - x0, yb - yt, 8)
        rellena(ctx, REGLA, 5)
        k = 0
        y = yb
        while y > yt + 4:
            ctx.move_to(x0 + 2, y)
            ctx.line_to(x0 + (24 if k % 5 == 0 else 12), y)
            trazo(ctx, INK, 3 if k % 5 == 0 else 2)
            y -= MM5 * 2
            k += 1
        if abs(y_top - y_orig) > 1:
            ctx.move_to(SX - 150, y_orig)
            ctx.line_to(x1 + 10, y_orig)
            ctx.set_dash([16, 12])
            trazo(ctx, BLANCO, 5, 0.75)
            ctx.set_dash([])
        ctx.move_to(SX + 130, y_top)
        ctx.line_to(x0 - 6, y_top)
        trazo(ctx, ROJO, 5, 0.85)
        ctx.move_to(x0 - 2, y_top)
        ctx.line_to(x0 - 30, y_top - 18)
        ctx.line_to(x0 - 30, y_top + 18)
        ctx.close_path()
        rellena(ctx, ROJO, 5)
        if marca_ok > 0.01:
            C.tilde(ctx, x1 + 70, y_top, 34, marca_ok)


def gotas_sueltas(ctx, t, t0, cf, salen=True):
    """Gotas de agua que salen de los discos (o vuelven a entrar). En coordenadas de pantalla, pila de pie."""
    _, discos, _ = pila_geo(cf)
    rr = rng(11)
    for i, (Aa, Ap, Bp, Ba) in enumerate(discos):
        for k in range(8):
            lado = -1 if k % 2 == 0 else 1
            ta = t0 + 0.11 * k + 0.05 * i
            u = (t - ta) / 0.9
            if u <= 0 or u >= 1:
                continue
            ex, ey = (Aa if lado < 0 else Ap)
            ey = (Aa[1] + Ba[1]) / 2
            x0, y0 = pila_pt(ex + lado * 2, ey)
            vx = lado * float(rr.uniform(170, 300))
            vy = float(rr.uniform(-260, -120))
            q = u if salen else 1 - u
            x = x0 + vx * q * 0.9
            y = y0 + (vy * q + 700 * q * q) * 0.9
            a = (1 - u) ** 0.6 if salen else min(1.0, u * 3)
            K.gota(ctx, x, y, 15, AGUA, alpha=a)


_rv = rng(12)
VUELTA = [[(float(_rv.uniform(-280, 280)), float(_rv.uniform(380, 600))) for _ in range(7)] for _ in range(2)]


def gotas_vuelven(ctx, t, t0, cf, rot, dx, dy):
    """Gotas que caen desde arriba y entran por el borde de atrás de cada disco (la pila está acostada)."""
    _, discos, _ = pila_geo(cf)
    c, s_ = math.cos(rot), math.sin(rot)
    for i, (Aa, Ap, Bp, Ba) in enumerate(discos):
        lx, ly = Ap[0], (Aa[1] + Ba[1]) / 2
        tx = SX + dx + MM5 * (lx * c - ly * s_)
        ty = SY + dy + MM5 * (lx * s_ + ly * c)
        for k, (ox, oy) in enumerate(VUELTA[i]):
            ta = t0 + 0.11 * k + 0.05 * i
            u = (t - ta) / 0.6
            if u <= 0 or u >= 1:
                continue
            e = ease(u, "in")
            x = lerp(tx + ox, tx, e)
            y = lerp(ty - oy, ty, e)
            K.gota(ctx, x, y, 15, AGUA, alpha=min(1.0, u * 4, (1 - u) * 6))


T_DURANTE = b(7)
T_PESO = b(7, "peso")
T_APLASTA = b(7, "aplasta")
T_SUELTAN = b(8)
T_AFINAN = b(8, "afinan")
T_BAJAS = b(8, "bajas")


def cf_dia(t):
    return 1 - 0.07 * prog(t, T_APLASTA, 0.2, "out") - (0.15 - 0.07) * prog(t, T_SUELTAN, T_AFINAN + 0.5 - T_SUELTAN)


def d_dia(ctx, t):
    fondo(ctx, t, 0.15)
    C.sol(ctx, 900, 220, 74 * pop(t, T_DURANTE - 0.05, 0.4), t)
    kartel(ctx, "DE DÍA", 640, 230, 60, t, T_DURANTE + 0.15, box=AMARILLO, rot=-3)
    cf = cf_dia(t)
    sx, sy = sacudida(t, T_APLASTA, 0.35, 16)
    ctx.save()
    ctx.translate(sx, sy)
    _, _, ytop = pila_geo(cf)
    y_top = SY + ytop * MM5
    if t < T_APLASTA:
        cara = ("dot", "smile") if t < T_PESO else ("dot", "o")
    else:
        cara = ("closed", "wavy")
    pila(ctx, cf, cara=cara, ghost=prog(t, T_AFINAN, 0.3))
    q = prog(t, T_PESO - 0.05, T_APLASTA - T_PESO + 0.05, "in")
    pesa(ctx, SX, lerp(-60, y_top, q), 1.0, a=1.0)
    gotas_sueltas(ctx, t, T_SUELTAN, cf)
    regla_pila(ctx, y_top, SY - 53 * MM5, a=prog(t, T_BAJAS - 0.6, 0.3))
    ctx.restore()


# ------------------------------------------------------------------ 4. de noche, acostado
T_ACUEST = b(9, "acuestas")
T_DEJAN = b(9, "dejan")
T_CARGAR = b(9, "cargar")
T_VUELVEN = b(10)
T_AMANECES = b(10, "amaneces")
T_ALTURA = b(10, "altura")
T_COMPLETA = b(10, "completa")
ROT_A0, ROT_A1 = T_ACUEST + 0.25, T_DEJAN + 0.05          # se acuesta
ROT_B0, ROT_B1 = T_AMANECES + 0.15, T_ALTURA - 0.05       # se levanta


def cf_noche(t):
    return CF_MIN + (1 - CF_MIN) * prog(t, T_VUELVEN + 0.1, 0.95, "inout")


def rot_noche(t):
    """Acostada boca abajo: la cabeza a la izquierda, los cuerpos sobre el colchón y las espinosas arriba."""
    return -math.radians(90) * prog(t, ROT_A0, ROT_A1 - ROT_A0) * (1 - prog(t, ROT_B0, ROT_B1 - ROT_B0))


def almohada(ctx, a):
    if a <= 0.01:
        return
    with alfa(ctx, a):
        rrect(ctx, 70, 1000, 220, 120, 55)
        rellena(ctx, BLANCO, 7)


def cama(ctx, a):
    """Colchón."""
    if a <= 0.01:
        return
    with alfa(ctx, a):
        rrect(ctx, 50, 1092, 980, 190, 50)
        rellena(ctx, CAMA, 7)
        ctx.move_to(90, 1126)
        ctx.line_to(990, 1126)
        trazo(ctx, CAMA_CLARA, 12)


def d_noche(ctx, t):
    noche = prog(t, b(9), 0.4) * (1 - prog(t, T_AMANECES, 0.5))
    fondo(ctx, t, 0.15 + 0.45 * noche)
    C.campo(ctx, t, seed=4, n=26, a=noche * 0.8, y1=700)
    luna_cara(ctx, 900, 220 + 400 * prog(t, T_AMANECES, 0.5, "in"), 64, a=noche)
    C.sol(ctx, 900, 620 - 400 * prog(t, T_AMANECES, 0.6, "out"), 74, t, a=prog(t, T_AMANECES, 0.3))
    rot = rot_noche(t)
    lying = clamp(-rot / math.radians(90))
    almohada(ctx, lying)
    cama(ctx, lying)
    cf = cf_noche(t)
    if t < T_VUELVEN:
        cara = ("closed", "smile")
    elif t < T_AMANECES:
        cara = ("happy", "grin")
    else:
        cara = ("dot", "smile")
    dx, dy = 210 * lying, 66 * lying         # acostada queda apoyada en la cama
    pila(ctx, cf, rot=rot, cara=cara, dx=dx, dy=dy)
    gotas_vuelven(ctx, t, T_VUELVEN - 0.1, cf, rot, dx, dy)
    # la pesa se va
    _, _, ytop = pila_geo(CF_MIN)
    q = prog(t, b(9) - 0.05, ROT_A0 - b(9) + 0.25, "in")
    if q < 1:
        pesa(ctx, SX, lerp(SY + ytop * MM5, -400, q), 1.0, a=1 - q)
    # zzz
    if noche > 0.3:
        for k in range(3):
            u = ((t - b(9)) * 0.7 + k / 3) % 1
            texto(ctx, "z", 90 + 50 * u + 20 * k, 720 - 300 * u, 50 + 30 * k, fill=BLANCO,
                  alpha=noche * math.sin(math.pi * u) * lying)
    kartel(ctx, "SIN PESO", 540, 330, 70, t, T_DEJAN, T_VUELVEN - 0.1, box=BLANCO, rot=-2)
    # de pie otra vez: la regla vuelve
    _, _, ytop = pila_geo(cf)
    up = prog(t, ROT_B1 - 0.1, 0.3)
    regla_pila(ctx, SY + ytop * MM5, SY - 53 * MM5, a=up, marca_ok=pop(t, T_COMPLETA, 0.35))


# ------------------------------------------------------------------ 5. ¿y si nada te aplasta?
T_QUE11 = b(11, "que")
T_NADA = b(11, "nada")
T_APL11 = b(11, "aplasta")
T_NUNCA = b(11, "nunca")


def pesa_fantasma(ctx, x, y_base, a):
    if a <= 0.01:
        return
    with en(ctx, x, y_base), alfa(ctx, a):
        ctx.move_to(-115, 0)
        ctx.line_to(-88, -190)
        ctx.line_to(88, -190)
        ctx.line_to(115, 0)
        ctx.close_path()
        ctx.new_sub_path()
        ctx.arc(0, -190, 62, math.pi, 0)
        ctx.set_dash([18, 14])
        trazo(ctx, BLANCO, 7)
        ctx.set_dash([])


def d_nada(ctx, t):
    fondo(ctx, t, 0.15 + 0.25 * prog(t, T_NUNCA, b(12) - T_NUNCA))
    C.sol(ctx, 900, 220, 74, t, a=1 - prog(t, T_NADA, 0.4))
    _, _, ytop = pila_geo(1.0)
    y_top = SY + ytop * MM5
    flota = 8 * math.sin((t - b(11)) * 3) * prog(t, T_NUNCA, 0.3)
    pila(ctx, 1.0, cara=("dot", "smile") if t < T_APL11 else ("happy", "grin"), dy=flota)
    regla_pila(ctx, y_top + flota, y_top, a=1 - prog(t, T_NADA, 0.3))
    signo(ctx, "?", 700, 380, 280, t, T_QUE11 - 0.05, T_NADA - 0.1)
    pesa_fantasma(ctx, SX, y_top - 20, prog(t, T_NADA, 0.25))
    s = pop(t, T_APL11, 0.3) * bump(t, T_NUNCA, 0.35, 0.25)
    if t >= T_APL11:
        K.prohibido(ctx, SX, y_top - 115, 150, s)


# ------------------------------------------------------------------ 6. el espacio
T_PROBO = b(12, "probo")
T_ESPACIO = b(12, "espacio")
T_ARRIBA = b(13, "arriba")
T_ASTRO = b(13, "astronauta")
T_CRECER = b(13, "crecer")
T_5CM = b(13, "5")


def estacion(ctx, x, y, s=1.0, a=1.0):
    """Estación espacial genérica: armazón, módulos y cuatro alas de paneles solares."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        for sx in (-1, 1):
            for sy in (-1, 1):
                x0 = sx * 250 - 45
                y0 = -32 if sy < 0 else 32
                ctx.move_to(sx * 250, 0)
                ctx.line_to(sx * 250, sy * 32)
                trazo(ctx, INK, 6)
                rrect(ctx, x0, y0 if sy > 0 else y0 - 210, 90, 210, 6)
                rellena(ctx, PANEL, 6)
                for k in range(1, 6):
                    yy = (y0 if sy > 0 else y0 - 210) + 35 * k
                    ctx.move_to(x0 + 4, yy)
                    ctx.line_to(x0 + 86, yy)
                    trazo(ctx, PANEL_CLARO, 3)
                ctx.move_to(x0 + 45, (y0 if sy > 0 else y0 - 210) + 4)
                ctx.line_to(x0 + 45, (y0 if sy > 0 else y0 - 210) + 206)
                trazo(ctx, PANEL_CLARO, 3)
        rrect(ctx, -300, -10, 600, 20, 6)
        rellena(ctx, ACERO, 5)
        for k in range(-5, 6):
            ctx.move_to(k * 52 - 10, -10)
            ctx.line_to(k * 52 + 10, 10)
            trazo(ctx, ACERO_OSC, 3)
        rrect(ctx, -120, -36, 240, 72, 34)
        rellena(ctx, TRAJE, 6)
        rrect(ctx, -40, -70, 80, 140, 34)
        rellena(ctx, TRAJE, 6)
        for k in (-80, -40, 0, 40, 80):
            ctx.move_to(k, -32)
            ctx.line_to(k, 32)
            trazo(ctx, TRAJE_OSC, 3)
        elipse(ctx, 0, 70, 22, 10)
        rellena(ctx, ACERO_OSC, 4)


def astronauta(ctx, x, y, s=1.0, rot=0.0, crece=0.0, corto=0.0, a=1.0):
    """Astronauta de frente con traje; (x, y) = suela de las botas. Mide 745 (el torso suma 22 al crecer)."""
    if s <= 0.01 or a <= 0.01:
        return
    dT = 22 * crece
    g = 40 * corto
    top = -560 - dT
    with en(ctx, x, y, s, rot), alfa(ctx, a):
        # mochila
        rrect(ctx, -150, top - 24, 300, -300 - (top - 24) + 30, 30)
        rellena(ctx, TRAJE_OSC, 7)
        # piernas
        for lx in (-58, 58):
            rrect(ctx, lx - 44, -52 - g - 6, 88, g + 12, 10)
            rellena(ctx, INTERIOR, 6)
            rrect(ctx, lx - 50, -310, 100, 310 - 52 - g, 36)
            rellena(ctx, TRAJE, 7)
            elipse(ctx, lx, -185 - g * 0.5, 40, 26)
            rellena(ctx, TRAJE_OSC, 5)
            rrect(ctx, lx - 50, -58, 100, 58, 20)
            rellena(ctx, ACERO, 7)
        # brazos
        for sx in (-1, 1):
            hx_, hy = sx * 178, top + 300
            rrect(ctx, hx_ - 30, hy - 60 - g - 4, 60, g + 12, 10)
            rellena(ctx, INTERIOR, 6)
            ctx.move_to(sx * 120, top + 60)
            ctx.line_to(hx_, hy - 60 - g)
            trazo(ctx, INK, 86)
            ctx.move_to(sx * 120, top + 60)
            ctx.line_to(hx_, hy - 60 - g)
            trazo(ctx, TRAJE, 72)
            elipse(ctx, sx * 155, top + 185 - g * 0.4, 38, 16)
            rellena(ctx, TRAJE_OSC, 5)
            rrect(ctx, hx_ - 36, hy - 62, 72, 80, 24)
            rellena(ctx, ACERO, 7)
        # torso
        rrect(ctx, -132, top, 264, -300 - top + 20, 60)
        rellena(ctx, TRAJE, 7)
        rrect(ctx, -132, -330, 264, 34, 12)
        rellena(ctx, TRAJE_OSC, 6)
        rrect(ctx, -72, top + 70, 144, 84, 14)
        rellena(ctx, ACERO, 6)
        for k, col in enumerate((ROJO, AMARILLO, VERDE)):
            elipse(ctx, -40 + 40 * k, top + 112, 13, 13)
            rellena(ctx, col, 4)
        elipse(ctx, 96, top + 60, 20, 20)
        rellena(ctx, PANEL, 4)
        # casco
        rrect(ctx, -74, top - 22, 148, 32, 12)
        rellena(ctx, ACERO, 6)
        elipse(ctx, 0, top - 110, 104, 100)
        rellena(ctx, TRAJE, 8)
        elipse(ctx, 0, top - 106, 80, 68)
        g2 = cairo.LinearGradient(0, top - 170, 0, top - 40)
        g2.add_color_stop_rgb(0, *hx("#3A6EA5"))
        g2.add_color_stop_rgb(1, *VISOR)
        ctx.set_source(g2)
        ctx.fill_preserve()
        trazo(ctx, INK, 6)
        ctx.new_sub_path()
        ctx.arc(-6, top - 106, 58, math.radians(200), math.radians(250))
        trazo(ctx, BLANCO, 10, 0.6)
        elipse(ctx, 40, top - 70, 9, 9)
        ctx.set_source_rgba(1, 1, 1, 0.5)
        ctx.fill()


ASTRO_TOP = 560 + 110 + 100         # del suelo a la punta del casco


def d_espacio(ctx, t):
    fondo(ctx, t, 0.7)
    C.campo(ctx, t, seed=9, n=70, a=prog(t, b(12) - 0.1, 0.4))
    yE = lerp(2600, 2350, prog(t, b(12), 0.6, "out"))
    C.tierra(ctx, 540, yE, 1000, t)
    sello(ctx, "PROBADO", 540, 520, 80, t, T_PROBO, T_ESPACIO - 0.05, rot=-6, col=VERDE)
    q = prog(t, T_ESPACIO - 0.2, 0.7, "out")
    estacion(ctx, lerp(-500, 540, q), 760 + 10 * math.sin(t * 1.5), 1.0)
    kartel(ctx, "ESPACIO", 540, 1120, 70, t, T_ESPACIO + 0.1, box=BLANCO, rot=-2)


def regla_flota(ctx, x, y_suelo, s, crece, a=1.0, sube=0.0):
    """Regla que flota al lado del astronauta (en su marco): marca la punta del casco."""
    if a <= 0.01:
        return
    alto = 820
    with en(ctx, x, y_suelo, s), alfa(ctx, a):
        rrect(ctx, 0, -alto, 64, alto, 8)
        rellena(ctx, REGLA, 6)
        for k in range(0, alto, 20):
            ctx.move_to(2, -k)
            ctx.line_to(24 if k % 100 == 0 else 13, -k)
            trazo(ctx, INK, 3 if k % 100 == 0 else 2)
        y0 = -ASTRO_TOP
        y1 = -ASTRO_TOP - 22 * crece
        ctx.move_to(-330, y0)
        ctx.line_to(80, y0)
        ctx.set_dash([16, 12])
        trazo(ctx, BLANCO, 5, 0.7)
        ctx.set_dash([])
        ctx.move_to(-60, y1)
        ctx.line_to(-6, y1)
        trazo(ctx, VERDE, 7)
        ctx.move_to(-2, y1)
        ctx.line_to(-30, y1 - 18)
        ctx.line_to(-30, y1 + 18)
        ctx.close_path()
        rellena(ctx, VERDE, 5)


def d_flota(ctx, t):
    fondo(ctx, t, 0.7)
    C.campo(ctx, t, seed=9, n=70)
    C.tierra(ctx, 540, 2350, 1000, t)
    estacion(ctx, lerp(540, 250, prog(t, b(13), 0.6)), lerp(760, 330, prog(t, b(13), 0.6)),
             lerp(1.0, 0.55, prog(t, b(13), 0.6)))
    q = prog(t, T_ARRIBA - 0.1, 0.8, "out")
    ax, ay = lerp(300, 470, q), lerp(560, 1230, q) + 14 * math.sin(t * 1.7)
    rot = math.radians(lerp(-25, -3, q) + 2 * math.sin(t * 1.3))
    s = 0.8
    crece = prog(t, T_CRECER, 0.8)
    # cable de seguridad desde la estación
    ex, ey = lerp(250, 250, 1), 360
    ctx.move_to(ex + 30, ey + 40)
    ctx.curve_to(ex + 80, ey + 500, ax - 200, ay - 520, ax - 60, ay - 330 * s)
    trazo(ctx, INK, 9, prog(t, T_ARRIBA, 0.3))
    ctx.move_to(ex + 30, ey + 40)
    ctx.curve_to(ex + 80, ey + 500, ax - 200, ay - 520, ax - 60, ay - 330 * s)
    trazo(ctx, NARANJA, 5, prog(t, T_ARRIBA, 0.3))
    astronauta(ctx, ax, ay, s * pop(t, T_ARRIBA - 0.12, 0.4), rot, crece=crece)
    with en(ctx, ax, ay, 1.0, rot):
        regla_flota(ctx, 250 * s, 0, s, crece, a=prog(t, T_ASTRO + 0.2, 0.3))
    kartel(ctx, "+5 cm", 860, 380, 96, t, T_5CM, box=VERDE, fg=BLANCO, rot=-4)


T_TANTO = b(14)
T_CAMBIA = b(14, "cambia")
T_TRAJE = b(14, "traje")
T_ASIENTO = b(14, "asiento")


def asiento(ctx, x, y, s=1.0, a=1.0):
    """Asiento de la cápsula, de frente, con apoyacabezas; (x, y) = base. El apoyacabezas llega a -720."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        ctx.move_to(-190, 0)
        ctx.line_to(-200, -560)
        ctx.curve_to(-200, -610, -170, -620, -130, -620)
        ctx.line_to(-95, -620)
        ctx.line_to(-95, -720)
        ctx.line_to(95, -720)
        ctx.line_to(95, -620)
        ctx.line_to(130, -620)
        ctx.curve_to(170, -620, 200, -610, 200, -560)
        ctx.line_to(190, 0)
        ctx.close_path()
        rellena(ctx, hx("#3E4A6B"), 8)
        rrect(ctx, -150, -580, 300, 540, 40)
        rellena(ctx, hx("#56648C"), 5)


def d_traje(ctx, t):
    fondo(ctx, t, 0.7)
    C.campo(ctx, t, seed=9, n=70)
    C.tierra(ctx, 540, 2350, 1000, t)
    z = 1 + 0.06 * prog(t, T_CAMBIA, T_TRAJE - T_CAMBIA)
    ctx.save()
    zoom(ctx, z, 540, 760)
    s = 0.95
    ax, ay = 540, 1290
    sa = pop(t, T_ASIENTO - 0.05, 0.35)
    if sa > 0.01:
        asiento(ctx, ax, ay - lerp(-300, 0, sa), s, a=min(1, sa * 2))
    corto = prog(t, T_TRAJE - 0.35, 0.45, "out")
    astronauta(ctx, ax, ay + 6 * math.sin(t * 2), s, math.radians(1.5 * math.sin(t * 1.3)), crece=1.0, corto=corto)
    if sa > 0.01:
        yr = ay - 720 * s
        ctx.move_to(ax - 260, yr)
        ctx.line_to(ax + 260, yr)
        ctx.set_dash([18, 12])
        trazo(ctx, ROJO, 7, min(1, sa * 2))
        ctx.set_dash([])
    ctx.restore()
    kartel(ctx, "+5 cm", 860, 380, 96, t, -1, T_TRAJE - 0.4, box=VERDE, fg=BLANCO, rot=-4)
    kartel(ctx, "TRAJE", 220, 900, 64, t, T_TRAJE, box=BLANCO, rot=-4)
    signo(ctx, "!", 200, 1110, 170, t, T_TRAJE + 0.12, col=ROJO)
    kartel(ctx, "ASIENTO", 860, 470, 64, t, T_ASIENTO, box=BLANCO, rot=3)
    signo(ctx, "!", 880, 640, 170, t, T_ASIENTO + 0.12, col=ROJO)


# ------------------------------------------------------------------ 7. la vuelta: la gravedad cobra
T_VOLVER = b(15, "volver")
T_GRAV = b(15, "gravedad")
T_COBRA = b(15, "cobra")
T_ATERR = T_VOLVER + 0.3
SUELO = 1200


def suelo(ctx):
    ctx.move_to(-40, SUELO)
    for k in range(13):
        ctx.line_to(k * 100, SUELO + 6 * math.sin(k * 1.7))
    ctx.line_to(1120, 1960)
    ctx.line_to(-40, 1960)
    ctx.close_path()
    rellena(ctx, ARENA, 7)
    for x, y, r in ((160, 1290, 26), (820, 1330, 34), (930, 1250, 18), (420, 1360, 20)):
        elipse(ctx, x, y, r * 1.6, r)
        rellena(ctx, ARENA_OSC, 5)


def capsula(ctx, x, y, s=1.0, rot=0.0):
    """Cápsula de regreso; (x, y) = centro de la base (el escudo térmico)."""
    with en(ctx, x, y, s, rot):
        ctx.move_to(-135, -10)
        ctx.line_to(-62, -220)
        ctx.curve_to(-40, -250, 40, -250, 62, -220)
        ctx.line_to(135, -10)
        ctx.close_path()
        rellena(ctx, hx("#9AA3B5"), 8)
        rrect(ctx, -142, -28, 284, 36, 16)
        rellena(ctx, hx("#5A3A2A"), 7)
        elipse(ctx, 0, -130, 30, 30)
        rellena(ctx, VISOR, 6)
        for k in (-0.5, 0.2, 0.6):
            ctx.move_to(-100 + 200 * (k + 0.5) / 1.5, -40)
            ctx.line_to(-70 + 160 * (k + 0.5) / 1.5, -150)
            trazo(ctx, hx("#6E6A64"), 6, 0.5)


def paracaidas(ctx, x, y, s=1.0, rot=0.0, a=1.0):
    """Paracaídas; (x, y) = donde se juntan las cuerdas."""
    if a <= 0.01:
        return
    with en(ctx, x, y, s, rot), alfa(ctx, a):
        for k in range(-3, 4):
            ctx.move_to(0, 0)
            ctx.line_to(k * 78, -330)
            trazo(ctx, INK, 3)
        ctx.move_to(-260, -330)
        ctx.curve_to(-260, -560, 260, -560, 260, -330)
        ctx.curve_to(170, -360, 90, -360, 0, -330)
        ctx.curve_to(-90, -360, -170, -360, -260, -330)
        ctx.close_path()
        path = ctx.copy_path()
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()
        ctx.save()
        ctx.append_path(path)
        ctx.clip()
        for k in range(-3, 3, 2):
            ctx.move_to(0, -800)
            ctx.line_to(k * 120, -300)
            ctx.line_to((k + 1) * 120, -300)
            ctx.close_path()
            ctx.set_source_rgb(*NARANJA)
            ctx.fill()
        ctx.restore()
        ctx.append_path(path)
        trazo(ctx, INK, 7)


def flecha_grav(ctx, x, y_punta, largo, s=1.0, a=1.0):
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y_punta, s), alfa(ctx, a):
        ctx.move_to(0, 0)
        ctx.line_to(-130, -140)
        ctx.line_to(-55, -140)
        ctx.line_to(-55, -largo)
        ctx.line_to(55, -largo)
        ctx.line_to(55, -140)
        ctx.line_to(130, -140)
        ctx.close_path()
        rellena(ctx, ROJO, 9)
        ctx.move_to(-28, -largo + 24)
        ctx.line_to(-28, -170)
        trazo(ctx, BLANCO, 12, 0.4)


def polvo(ctx, t, t0, x, y):
    u = (t - t0) / 0.8
    if u <= 0 or u >= 1:
        return
    for k in range(9):
        lado = -1 if k % 2 else 1
        dx = lado * (60 + 30 * k) * ease(u, "out")
        r = (30 + 8 * k) * (0.5 + u)
        elipse(ctx, x + dx, y - 20 - 40 * u * (k % 3) / 2, r, r * 0.7)
        ctx.set_source_rgba(*mezcla(ARENA, BLANCO, 0.3), 0.7 * (1 - u))
        ctx.fill()


def d_vuelta(ctx, t):
    fondo(ctx, t, 0.1)
    sx, sy = sacudida(t, T_ATERR, 0.4, 18)
    sx2, sy2 = sacudida(t, T_GRAV + 0.12, 0.35, 14)
    ctx.save()
    ctx.translate(sx + sx2, sy + sy2)
    suelo(ctx)
    q = prog(t, b(15) - 0.15, T_ATERR - b(15) + 0.15, "out")
    cy = lerp(-200, SUELO + 18, q)
    # el paracaídas se suelta y cae al costado
    u = prog(t, T_ATERR, 0.9, "inout")
    paracaidas(ctx, 540 + 330 * u, cy - 260 + 520 * u * u, 0.9, math.radians(40 * u), a=1 - prog(t, T_ATERR + 0.5, 0.4))
    capsula(ctx, 540, cy, 1.0)
    polvo(ctx, t, T_ATERR, 540, SUELO + 10)
    fs = prog(t, T_GRAV - 0.1, 0.22, "in")
    flecha_grav(ctx, 540, lerp(-50, 900, fs), 420, 1.0, a=1.0 if fs > 0 else 0)
    ctx.restore()
    kartel(ctx, "GRAVEDAD", 250, 520, 64, t, T_GRAV + 0.05, box=BLANCO, rot=-4)
    sello(ctx, "COBRADO", 730, 330, 84, t, T_COBRA, rot=-8)


# ------------------------------------------------------------------ 8. con el tiempo, mide lo mismo
T_TIEMPO = b(16, "tiempo")
T_MIDE = b(16, "mide")
T_MISMO = b(16, "mismo")
T_ANTES = b(16, "antes")
FLIPS = [b(16) + 0.05 + 0.16 * k for k in range(5)]


def calendario(ctx, x, y, s, t):
    if s <= 0.01:
        return
    n = sum(1 for f in FLIPS if t >= f + 0.15)
    with en(ctx, x, y, s):
        def hoja(k):
            rrect(ctx, -120, -110, 240, 230, 16)
            rellena(ctx, BLANCO, 7)
            rrect(ctx, -120, -110, 240, 62, 16)
            rellena(ctx, ROJO, 7)
            for i in range(4):
                for j in range(5):
                    rrect(ctx, -96 + j * 40, -32 + i * 36, 30, 26, 5)
                    ctx.set_source_rgba(*ACERO_OSC, 0.55)
                    ctx.fill()
        hoja(n)
        for f in FLIPS:
            if f <= t < f + 0.15:
                q = (t - f) / 0.15
                with en(ctx, 0, -110), alfa(ctx, 1 - q):
                    ctx.scale(1, max(0.02, 1 - q))
                    ctx.translate(0, 110)
                    hoja(n)
        for sx in (-60, 60):
            rrect(ctx, sx - 10, -132, 20, 44, 10)
            rellena(ctx, ACERO, 5)


def d_tiempo(ctx, t):
    fondo(ctx, t, 0.1)
    suelo(ctx)
    s = 0.9
    ax, ay = 400, SUELO + 40
    crece = 1 - prog(t, T_MIDE - 0.1, T_ANTES - T_MIDE + 0.1, "inout")
    calendario(ctx, 860, 250, 0.85 * pop(t, b(16) - 0.1, 0.3), t)
    # regla en el suelo
    x0 = 700
    top = ay - 820 * s
    rrect(ctx, x0, top, 64, ay - top, 8)
    rellena(ctx, REGLA, 6)
    for k in range(0, 820, 20):
        y = ay - k * s
        ctx.move_to(x0 + 2, y)
        ctx.line_to(x0 + (24 if k % 100 == 0 else 13), y)
        trazo(ctx, INK, 3 if k % 100 == 0 else 2)
    astronauta(ctx, ax, ay, s, 0.0, crece=crece)
    y0 = ay - ASTRO_TOP * s
    y1 = ay - (ASTRO_TOP + 22 * crece) * s
    ctx.move_to(ax - 130, y0)
    ctx.line_to(x0 + 90, y0)
    ctx.set_dash([16, 12])
    trazo(ctx, BLANCO, 5, 0.75)
    ctx.set_dash([])
    texto(ctx, "ANTES", x0 + 150, y0, 36, fill=BLANCO, alpha=0.9)
    ctx.move_to(ax + 40, y1)
    ctx.line_to(x0 - 6, y1)
    trazo(ctx, VERDE if crece > 0.05 else BLANCO, 6)
    if t >= T_ANTES:
        C.tilde(ctx, x0 + 150, y0 - 80, 44, pop(t, T_ANTES, 0.35))
    kartel(ctx, "+5 cm", 870, 440, 80, t, -1, T_MIDE + 0.2, box=VERDE, fg=BLANCO, rot=-4)


# ------------------------------------------------------------------ 9. cierre: vuelve la rutina (loop)
T_RUTINA = b(17, "rutina")
T_TODOS = b(17, "todos")
T_TIERRA = b(17, "tierra")


def d_cierre(ctx, t):
    z = 1 + 0.07 * (1 - prog(t, b(17), TOTAL - 0.1 - b(17), "inout"))
    noche = prog(t, T_RUTINA - 0.1, 0.25) * (1 - prog(t, T_TODOS - 0.05, 0.3))
    menos = 2 * prog(t, T_RUTINA - 0.05, 0.3) * (1 - prog(t, T_TODOS, 0.3))
    pose = "cansado" if T_RUTINA <= t < T_TODOS + 0.1 else "mira"
    ctx.save()
    zoom(ctx, z, 520, 760)
    cuarto(ctx, t, noche, menos, pose)
    ctx.restore()


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_apertura),
    (b(5) - 0.08, d_columna),
    (b(7) - 0.08, d_dia),
    (b(9) - 0.08, d_noche),
    (b(11) - 0.08, d_nada),
    (b(12) - 0.08, d_espacio),
    (b(13) - 0.08, d_flota),
    (b(14) - 0.08, d_traje),
    (b(15) - 0.08, d_vuelta),
    (b(16) - 0.08, d_tiempo),
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

    # 1. apertura
    ev(T_NOCHE, "pop", 0.35)
    ev(T_NOCHE + 0.2, "clic", 0.3)
    ev(T_MANANA, "pop", 0.35)
    ev(T_MANANA + 0.2, "clic", 0.3)
    ev(T_ILUSION, "pop", 0.4)
    ev(T_ILUSION + 0.45, "tick", 0.4, f=500, d=0.09)
    ev(T_REGLA - 0.1, "pop", 0.45)
    ev(b(2), "pop", 0.5)
    ev(T_MIENTRAS, "pop", 0.35)
    ev(T_LEVANT - 0.1, "clic", 0.4)
    for h in HORAS:
        ev(h, "tick", 0.2, f=1800, d=0.03)
    ev(T_2CM, "golpe", 0.6)
    # 2. columna
    ev(T_HUESOS, "pop", 0.4)
    ev(T_HUESOS + 0.3, "tick", 0.4, f=420, d=0.08)
    for i in range(0, N_DISCOS, 2):
        ev(T_SINO + 0.1 + (T_ENTRE + 0.5 - T_SINO) * i / (N_DISCOS - 1), "tick", 0.18, f=1200 + 40 * i, d=0.03)
    ev(T_ENTRE + 0.15, "ding", 0.3)
    ev(T_COLUMNA, "pop", 0.35)
    ev(T_ALMOH + 0.3, "pop", 0.45)
    for k in range(4):
        ev(T_AGUA6 - 0.1 + 0.08 * k, "plop", 0.3)
    # 3. día
    ev(T_DURANTE, "pop", 0.35)
    ev(T_APLASTA, "clunk", 0.8)
    ev(T_APLASTA + 0.05, "golpe", 0.5)
    for k in range(0, 8, 2):
        ev(T_SUELTAN + 0.11 * k, "plop", 0.35)
    ev(T_AFINAN, "tick", 0.35, f=700, d=0.07)
    ev(T_BAJAS - 0.6, "pop", 0.3)
    # 4. noche
    ev(T_DEJAN, "pop", 0.35)
    ev(ROT_A1, "clunk", 0.35)
    for k in range(0, 8, 2):
        ev(T_VUELVEN - 0.1 + 0.11 * k + 0.6, "plop", 0.3)
    ev(T_AMANECES, "pop", 0.35)
    ev(ROT_B1, "clunk", 0.3)
    ev(T_COMPLETA, "ding", 0.5)
    # 5. nada
    ev(T_QUE11 - 0.05, "pop", 0.5)
    ev(T_NADA, "pop", 0.3)
    ev(T_APL11, "golpe", 0.7)
    ev(T_NUNCA, "tick", 0.4, f=900, d=0.06)
    # 6. espacio
    ev(b(12), "pop", 0.3)
    ev(T_PROBO, "golpe", 0.8)
    ev(T_ESPACIO, "pop", 0.4)
    ev(T_ARRIBA, "pop", 0.4)
    ev(T_ASTRO + 0.2, "clic", 0.3)
    for k in range(4):
        ev(T_CRECER + 0.2 * k, "tick", 0.3, f=1400 + 200 * k, d=0.04)
    ev(T_5CM, "ding", 0.5)
    # traje y asiento
    ev(T_TANTO, "pop", 0.3)
    ev(T_TRAJE - 0.3, "tick", 0.3, f=600, d=0.07)
    ev(T_TRAJE, "pop", 0.4)
    ev(T_TRAJE + 0.12, "tick", 0.4, f=900, d=0.06)
    ev(T_ASIENTO - 0.05, "clunk", 0.35)
    ev(T_ASIENTO + 0.12, "tick", 0.4, f=900, d=0.06)
    # 7. vuelta
    ev(T_ATERR, "clunk", 0.8)
    ev(T_ATERR + 0.02, "golpe", 0.5)
    ev(T_GRAV + 0.12, "golpe", 0.9)
    ev(T_COBRA, "golpe", 0.7)
    ev(T_COBRA + 0.1, "ding", 0.4)
    # 8. tiempo
    for f in FLIPS:
        ev(f, "tick", 0.3, f=2200, d=0.03)
    ev(T_ANTES, "ding", 0.45)
    # 9. cierre
    ev(T_RUTINA - 0.1, "pop", 0.3)
    ev(T_TODOS - 0.05, "pop", 0.3)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "por_que_eres_mas_alto_a_la_manana.mp4"))
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

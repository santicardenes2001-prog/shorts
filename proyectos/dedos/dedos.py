"""Short "¿Por qué se arrugan los dedos en el agua?" — animación procedural (armazón de bostezo.py).

Estilo del canal: fondo azul con puntos, cosas con cara (la gota, la esponja, el globo, el neumático, los dados)
y subtítulos palabra por palabra. Vos sale solo en la apertura (en la bañera) y el cierre vuelve al primer cuadro.

Hilo que se repite: el dibujo de las arrugas (`CURVAS`) es siempre el mismo y sigue a los vasos de sangre: es el que
aparece en la lupa del principio, en la yema grande, en las dos yemas de "salen siempre igual" y el que espera
escondido al final.

    python proyectos/dedos/dedos.py --hoja 0,3,6      # hoja de fotogramas -> proyectos/dedos/fotos/hoja.png
    python proyectos/dedos/dedos.py --probar
    python proyectos/dedos/dedos.py                   # render -> salidas/por_que_se_arrugan_los_dedos.mp4
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
from tierra import (CREMA, ROJO, VERDE, alfa, cruz_roja, destello, elipse, en, kartel, rellena, sale,  # noqa: E402
                    sello, signo, tilde, trazo, zoom)

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Después de un baño largo, tus dedos se arrugan.",                       # b0
    "Tu brazo estuvo igual de mojado, y sigue liso.",                        # b1
    "¿Por qué solo se arrugan los dedos?",                                   # b2
    "Parece que la piel chupa agua, como una esponja.",                      # b3
    "Pero si fuera eso, se arrugaría todo tu cuerpo.",                       # b4
    "Solo se arrugan los dedos de las manos y de los pies.",                 # b5
    "No es el agua: es una orden de tus nervios.",                           # b6
    "Los vasos de sangre de la yema se achican.",                            # b7
    "La yema se desinfla como un globo.",                                    # b8
    "La piel que sobra se pliega.",                                          # b9
    "Si el nervio de un dedo está dañado, ese dedo no se arruga.",           # b10
    "¿Para qué?",                                                            # b11
    "En un experimento, los dedos arrugados agarraron mejor cosas mojadas.", # b12
    "Las arrugas sacan el agua, como las ranuras de un neumático.",          # b13
    "Por eso saldrían justo donde agarras y donde pisas.",                   # b14
    "Lo más raro: tus arrugas no salen al azar.",                            # b15
    "Salen siempre igual, siguiendo tus vasos de sangre.",                   # b16
    "Ese dibujo ya está ahí, en la yema de tu dedo.",                        # b17
    "Esperando el próximo baño.",                                            # b18
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
PIEL = hx("#F8C9A2")
PIEL_YEMA = hx("#F7BFA3")
PIEL_OSC = hx("#E9A982")
PIEL_CLARA = hx("#FFE6D4")
ARRUGA = hx("#B86E52")
SANGRE = hx("#E5383B")
SANGRE_CLARA = hx("#FF7A7C")
AGUA = hx("#4FB6F5")
AGUA_OSC = hx("#2A8FD6")
AGUA_CLARA = hx("#BFE8FF")
BANERA = hx("#F4F7FF")
BANERA_SOMBRA = hx("#C9D3EA")
ESPUMA = hx("#FFFFFF")
PATO = hx("#FFD23F")
PICO = hx("#FF8F3F")
ESPONJA = hx("#FFD84A")
ESPONJA_OSC = hx("#E0B21E")
GLOBO = hx("#FF5D7A")
GOMA = hx("#3A3F55")
GOMA2 = hx("#2A2E40")
PANEL = hx("#1B2347")
GRIS = hx("#C9D1DE")
DADO = hx("#FFF7E8")
CANICA = hx("#6FD3FF")
RELOJ = hx("#FFF7E8")


# ------------------------------------------------------------------ ayudas
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


# El dibujo de las arrugas de una yema, en coordenadas de la yema: x de -1 a 1 (ancho), y desde la punta (0) hacia
# abajo. Las arrugas reales corren a lo largo del dedo y se ramifican; siguen a los vasos de sangre de abajo.
CURVAS = [
    [(-0.60, 0.34), (-0.70, 0.58), (-0.48, 0.82), (-0.60, 1.12)],
    [(-0.30, 0.14), (-0.42, 0.42), (-0.16, 0.64), (-0.30, 1.04)],
    [(0.02, 0.07), (-0.08, 0.34), (0.14, 0.56), (0.02, 0.98)],
    [(0.34, 0.16), (0.24, 0.42), (0.48, 0.68), (0.34, 1.06)],
    [(0.62, 0.36), (0.56, 0.58), (0.74, 0.82), (0.62, 1.12)],
    [(-0.20, 0.62), (-0.06, 0.74), (-0.14, 0.92), (-0.02, 1.14)],
    [(0.14, 0.56), (0.24, 0.68), (0.18, 0.84), (0.26, 1.10)],
]


def mapa(cx, ytop, r, k=1.0):
    """Pasa de coordenadas de la yema a la pantalla; r = medio ancho del dedo, k = alto relativo."""
    return lambda x, y: (cx + x * r * 0.95, ytop + y * r * 1.7 * k)


def curva(ctx, pts, a=1.0, n=26):
    if a <= 0.01:
        return False
    m = max(2, int(n * a))
    for j in range(m + 1):
        x, y = bez(pts, a * j / m)
        (ctx.move_to if j == 0 else ctx.line_to)(x, y)
    return True


def arrugas(ctx, mp, a, lw=8.0, alpha=1.0, col=ARRUGA, luz=True):
    """Dibuja el dibujo de arrugas (a = cuánto se formó, 0..1) con el mapeo mp."""
    if a <= 0.01 or alpha <= 0.01:
        return
    for k, c in enumerate(CURVAS):
        ak = clamp((a - 0.06 * k) / 0.6)
        pts = [mp(x, y) for x, y in c]
        if luz:
            off = [(x + lw * 0.55, y + lw * 0.2) for x, y in pts]
            if curva(ctx, off, ak):
                trazo(ctx, PIEL_CLARA, lw * 0.75, 0.9 * alpha)
        if curva(ctx, pts, ak):
            trazo(ctx, col, lw, alpha)


def vasos(ctx, mp, ancho, alpha=1.0, pulso=0.0):
    """Vasos de sangre debajo de la piel, por el mismo camino que las arrugas."""
    if alpha <= 0.01:
        return
    for c in CURVAS:
        pts = [mp(x, y) for x, y in c]
        curva(ctx, pts)
        trazo(ctx, INK, ancho + 8, alpha)
        curva(ctx, pts)
        trazo(ctx, SANGRE, ancho, alpha)
        curva(ctx, pts)
        trazo(ctx, SANGRE_CLARA, max(1.5, ancho * 0.3), alpha * (0.7 + 0.3 * pulso))


def brillo(ctx, x, y, r, a, col=AMARILLO):
    if a <= 0.01:
        return
    g = cairo.RadialGradient(x, y, r * 0.1, x, y, r)
    g.add_color_stop_rgba(0, *col, 0.8 * a)
    g.add_color_stop_rgba(1, *col, 0)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, TAU)
    ctx.fill()


def union(ctx, caminos, relleno, borde=8.0, a=1.0):
    """Rellena varias figuras como una sola silueta (contorno solo por fuera)."""
    for f in caminos:
        ctx.new_path()
        f()
        trazo(ctx, INK, borde * 2, a)
    for f in caminos:
        ctx.new_path()
        f()
        if isinstance(relleno, cairo.Pattern):
            ctx.set_source(relleno)
        else:
            ctx.set_source_rgba(*relleno, a)
        ctx.fill()


def capsula(ctx, x, y, w, h):
    return lambda: rrect(ctx, x, y, w, h, w / 2)


# ------------------------------------------------------------------ la mano (palma hacia la cámara)
DEDOS = [(-108, 64, 210), (-36, 70, 248), (36, 68, 232), (106, 58, 176)]   # (x, ancho, largo)
PULGAR = (-150, -120, -0.62, 70, 200)                                     # (x, y, giro, ancho, largo)


def mano(ctx, x, y, s=1.0, arr=0.0, brillo_y=0.0, antebrazo=0.0, rot=0.0, a=1.0, nervio=0.0, pulso=None):
    """Mano abierta con la palma de frente; (x, y) = muñeca. arr = arrugas en las yemas (0..1)."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s, rot), alfa(ctx, a):
        partes = [lambda: rrect(ctx, -150, -330, 300, 336, 80)]
        if antebrazo > 0:
            partes.append(lambda: rrect(ctx, -118, -60, 236, antebrazo + 60, 70))
        for fx, fw, fl in DEDOS:
            partes.append(lambda fx=fx, fw=fw, fl=fl: rrect(ctx, fx - fw / 2, -290 - fl, fw, fl + 70, fw / 2))

        def pulgar():
            px, py, g, pw, pl = PULGAR
            ctx.save()
            ctx.translate(px, py)
            ctx.rotate(g)
            rrect(ctx, -pw / 2, -pl, pw, pl + 40, pw / 2)
            ctx.restore()
        partes.append(pulgar)
        union(ctx, partes, PIEL, 7)
        # líneas de la palma
        ctx.move_to(-130, -170)
        ctx.curve_to(-60, -200, 40, -205, 128, -235)
        trazo(ctx, PIEL_OSC, 6)
        ctx.move_to(-120, -120)
        ctx.curve_to(-40, -140, 20, -120, 70, -150)
        trazo(ctx, PIEL_OSC, 6)
        ctx.move_to(-70, -40)
        ctx.curve_to(-110, -90, -110, -150, -95, -200)
        trazo(ctx, PIEL_OSC, 6)
        # pliegues de las falanges
        for fx, fw, fl in DEDOS:
            top = -290 - fl
            for q in (0.40, 0.70):
                yy = top + fl * q
                ctx.move_to(fx - fw * 0.28, yy)
                ctx.curve_to(fx - fw * 0.1, yy + 7, fx + fw * 0.1, yy + 7, fx + fw * 0.28, yy)
                trazo(ctx, PIEL_OSC, 5)
            # yema
            ctx.save()
            rrect(ctx, fx - fw / 2, top, fw, fl * 0.38, fw / 2)
            ctx.clip()
            if arr > 0.01:
                ctx.set_source_rgba(*PIEL_YEMA, 0.8 * arr)
                ctx.paint()
            arrugas(ctx, mapa(fx, top, fw / 2, 0.72), arr, lw=5.0)
            ctx.restore()
            brillo(ctx, fx, top + fw * 0.55, fw * 1.1, brillo_y)
        # nervio (amarillo) del antebrazo a las yemas
        if nervio > 0.01:
            nervio_mano(ctx, nervio, pulso, antebrazo)


def nervio_mano(ctx, a, pulso, antebrazo):
    base = (0, antebrazo * 0.9 if antebrazo else 0)
    for fx, fw, fl in DEDOS:
        top = -290 - fl
        pts = [base, (fx * 0.2, -150), (fx, -260), (fx, top + fw * 0.45)]
        curva(ctx, pts)
        trazo(ctx, INK, 15, a)
        curva(ctx, pts)
        trazo(ctx, AMARILLO, 8, a)
        if pulso is not None and 0 <= pulso <= 1:
            px, py = bez(pts, pulso)
            brillo(ctx, px, py, 70, a)
            ctx.arc(px, py, 13, 0, TAU)
            rellena(ctx, BLANCO, 4, a=a)


# ------------------------------------------------------------------ la yema grande (corte con lo de adentro)
def yema_camino(ctx, cx, ytop, r, abajo, pliegue=0.0):
    """Contorno del dedo apuntando arriba; con pliegue > 0 el borde de la yema se ondula."""
    pts = []
    yc = ytop + r
    for j in range(13):
        pts.append((cx - r, abajo - (abajo - yc) * j / 12))
    for j in range(1, 48):
        g = math.pi + math.pi * j / 48
        pts.append((cx + r * math.cos(g), yc + r * math.sin(g)))
    for j in range(13):
        pts.append((cx + r, yc + (abajo - yc) * j / 12))
    if pliegue > 0:
        out = []
        for k, (x, y) in enumerate(pts):
            zona = clamp((yc + 1.6 * r - y) / (0.8 * r))          # solo la yema se pliega
            dx, dy = x - cx, y - (yc + 0.4 * r)
            d = math.hypot(dx, dy) or 1
            amp = 9 * pliegue * zona * (0.5 + 0.5 * math.sin(k * 1.25))
            out.append((x - dx / d * amp, y - dy / d * amp))
        pts = out
    ctx.new_path()
    for k, (x, y) in enumerate(pts):
        (ctx.move_to if k == 0 else ctx.line_to)(x, y)
    ctx.close_path()


def yema(ctx, cx, ytop, r, abajo=2100, arr=0.0, rayos=0.0, ancho_vaso=24.0, pulso=0.0, nervio=0.0,
         pliegue=0.0, fantasma=0.0, corte=0.0, brillo_y=0.0, lw=None):
    """Dedo grande de frente (lado de la yema). rayos = cuánto se ve lo de adentro (vasos y nervio)."""
    lw = lw or r / 17
    yema_camino(ctx, cx, ytop, r, abajo, pliegue)
    g = cairo.LinearGradient(cx - r, 0, cx + r, 0)
    g.add_color_stop_rgb(0, *PIEL_OSC)
    g.add_color_stop_rgb(0.3, *PIEL)
    g.add_color_stop_rgb(0.7, *PIEL)
    g.add_color_stop_rgb(1, *PIEL_OSC)
    ctx.set_source(g)
    ctx.fill_preserve()
    trazo(ctx, INK, max(6, r / 26))
    mp = mapa(cx, ytop, r)
    ctx.save()
    yema_camino(ctx, cx, ytop, r, abajo, pliegue)
    ctx.clip()
    brillo(ctx, cx, ytop + r * 0.9, r * 1.2, brillo_y)
    if rayos > 0.01:
        # ventana de "rayos X": la piel se aclara y se ve lo de adentro
        ctx.set_source_rgba(*PIEL_CLARA, 0.35 * rayos)
        ctx.paint()
        if nervio > 0.01:
            nervio_yema(ctx, cx, ytop, r, abajo, rayos * nervio, corte)
        vasos(ctx, mp, ancho_vaso * r / 230, rayos, pulso)
    if fantasma > 0.01:
        for c in CURVAS:
            curva(ctx, [mp(x, y) for x, y in c])
            ctx.set_dash([lw * 1.3, lw * 1.3])
            trazo(ctx, AMARILLO, lw * 0.8, fantasma)
            ctx.set_dash([])
        brillo(ctx, cx, ytop + r * 1.0, r * 1.3, 0.45 * fantasma)
    arrugas(ctx, mp, arr, lw=lw)
    ctx.restore()


def nervio_yema(ctx, cx, ytop, r, abajo, a, corte=0.0):
    pts = [(cx, abajo), (cx - 0.1 * r, ytop + 3.4 * r), (cx + 0.12 * r, ytop + 2.2 * r), (cx, ytop + 1.3 * r)]
    ramas = [[(cx, ytop + 1.3 * r), (cx - 0.3 * r, ytop + 1.0 * r), (cx - 0.5 * r, ytop + 0.8 * r),
              (cx - 0.55 * r, ytop + 0.5 * r)],
             [(cx, ytop + 1.3 * r), (cx + 0.3 * r, ytop + 1.0 * r), (cx + 0.5 * r, ytop + 0.8 * r),
              (cx + 0.55 * r, ytop + 0.5 * r)],
             [(cx, ytop + 1.3 * r), (cx, ytop + 1.0 * r), (cx + 0.05 * r, ytop + 0.6 * r), (cx, ytop + 0.3 * r)]]
    w = r / 14
    for c in [pts] + ramas:
        curva(ctx, c)
        trazo(ctx, INK, w + 7, a)
        curva(ctx, c)
        trazo(ctx, AMARILLO, w, a)
    if corte > 0.01:
        # nervio cortado: un hueco con chispas y una cruz roja
        yc = ytop + 2.7 * r
        ctx.rectangle(cx - r * 0.3, yc - r * 0.18 * corte, r * 0.6, r * 0.36 * corte)
        ctx.set_source_rgba(*PIEL, a)
        ctx.fill()
        cruz_roja(ctx, cx, yc, 0.3 * r / 130 * pop(corte, 0, 0.6), a)


# ------------------------------------------------------------------ objetos con cara
def gota(ctx, x, y, R, a=1.0, cara=("open", "smile"), look=(0, 0), s=1.0, ceja=None):
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        ctx.move_to(0, -1.45 * R)
        ctx.curve_to(0.55 * R, -0.7 * R, R, -0.25 * R, R, 0.28 * R)
        ctx.curve_to(R, 0.85 * R, 0.5 * R, 1.15 * R, 0, 1.15 * R)
        ctx.curve_to(-0.5 * R, 1.15 * R, -R, 0.85 * R, -R, 0.28 * R)
        ctx.curve_to(-R, -0.25 * R, -0.55 * R, -0.7 * R, 0, -1.45 * R)
        ctx.close_path()
        rellena(ctx, AGUA, max(4, R / 14))
        ctx.move_to(-0.55 * R, 0.0)
        ctx.curve_to(-0.6 * R, -0.3 * R, -0.45 * R, -0.55 * R, -0.3 * R, -0.75 * R)
        trazo(ctx, BLANCO, R / 9, 0.6)
        if cara:
            carita(ctx, 0, 0.25 * R, 0.62 * R, R / 120, ojos=cara[0], boca=cara[1], look=look, ceja=ceja)


def gotita(ctx, x, y, r, a=1.0):
    if a <= 0.01:
        return
    ctx.move_to(x, y - 1.5 * r)
    ctx.curve_to(x + r, y - 0.2 * r, x + r, y + r, x, y + r)
    ctx.curve_to(x - r, y + r, x - r, y - 0.2 * r, x, y - 1.5 * r)
    ctx.close_path()
    rellena(ctx, AGUA_CLARA, max(2.5, r / 5), a=a)


def esponja(ctx, x, y, s=1.0, moja=0.0, look=(0, 0), boca="smile", ojos="open"):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        hinch = 1 + 0.18 * moja
        w, h = 300 * hinch, 210 * hinch
        rrect(ctx, -w / 2, -h / 2, w, h, 40)
        col = tuple(lerp(c0, c1, 0.45 * moja) for c0, c1 in zip(ESPONJA, AGUA))
        rellena(ctx, col, 8)
        for hx_, hy_, hr in ((-100, -60, 16), (95, -55, 12), (-110, 55, 13), (110, 50, 17), (-40, 75, 10),
                             (40, -82, 9), (128, -5, 8), (-128, -8, 9)):
            elipse(ctx, hx_ * hinch, hy_ * hinch, hr * hinch, hr * 0.8 * hinch)
            ctx.set_source_rgba(*ESPONJA_OSC, 0.9)
            ctx.fill()
        carita(ctx, 0, -10, 110, 1.15, ojos=ojos, boca=boca, look=look, rubor=True)


def globo(ctx, x, y, s=1.0, infla=1.0, look=(0, 0), boca="smile", ojos="open", t=0.0):
    if s <= 0.01:
        return
    with en(ctx, x, y, s, 0.08 * math.sin(t * 2.4)):
        R = 120 * (0.45 + 0.55 * infla)
        ctx.move_to(0, R * 1.1)
        ctx.curve_to(-40, R * 1.1 + 60, 40, R * 1.1 + 110, 0, R * 1.1 + 170)
        trazo(ctx, BLANCO, 5)
        elipse(ctx, 0, 0, R * 0.92, R * 1.1)
        rellena(ctx, GLOBO, 8)
        ctx.move_to(-12, R * 1.08)
        ctx.line_to(12, R * 1.08)
        ctx.line_to(0, R * 1.08 + 20)
        ctx.close_path()
        rellena(ctx, GLOBO, 5)
        elipse(ctx, -R * 0.4, -R * 0.5, R * 0.16, R * 0.26)
        ctx.set_source_rgba(1, 1, 1, 0.55)
        ctx.fill()
        if infla < 0.75:
            for k in range(5):   # pliegues del globo desinflado
                yy = -R * 0.6 + k * R * 0.32
                ctx.move_to(-R * 0.7, yy)
                ctx.curve_to(-R * 0.3, yy + 12, R * 0.3, yy - 12, R * 0.7, yy)
                trazo(ctx, hx("#C93A55"), 5, clamp((0.75 - infla) / 0.3))
        carita(ctx, 0, -R * 0.05, R * 0.75, R / 120, ojos=ojos, boca=boca, look=look, rubor=True)


def neumatico(ctx, x, y, R, giro=0.0, s=1.0, look=(0, 0), boca="smile"):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        ctx.arc(0, 0, R, 0, TAU)
        rellena(ctx, GOMA, 9)
        n = 16
        for k in range(n):
            g = giro + k * TAU / n
            ctx.save()
            ctx.rotate(g)
            ctx.move_to(R - 6, -14)
            ctx.line_to(R * 0.8, -4)
            ctx.line_to(R * 0.8, 14)
            ctx.line_to(R - 6, 24)
            trazo(ctx, GOMA2, 12)
            ctx.restore()
        ctx.arc(0, 0, R * 0.62, 0, TAU)
        rellena(ctx, GRIS, 8)
        ctx.arc(0, 0, R * 0.22, 0, TAU)
        rellena(ctx, hx("#8E97A8"), 6)
        carita(ctx, 0, -R * 0.08, R * 0.5, R / 220, look=look, boca=boca)


def dado(ctx, x, y, L, rot, s=1.0, pips=5):
    if s <= 0.01:
        return
    with en(ctx, x, y, s, rot):
        rrect(ctx, -L / 2, -L / 2, L, L, L * 0.18)
        rellena(ctx, DADO, 8)
        pos = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)],
               4: [(-1, -1), (1, -1), (-1, 1), (1, 1)], 5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
               6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}[pips]
        for px, py in pos:
            ctx.arc(px * L * 0.26, py * L * 0.26, L * 0.08, 0, TAU)
            ctx.set_source_rgb(*INK)
            ctx.fill()


def pie(ctx, x, y, s=1.0, arr=0.0, brillo_y=0.0):
    """Planta del pie (vista de abajo), dedos arriba; (x, y) = centro del talón."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        partes = [lambda: elipse(ctx, 0, -50, 105, 125), lambda: elipse(ctx, 15, -270, 140, 120),
                  lambda: rrect(ctx, -100, -250, 215, 220, 90)]
        TOES = [(-80, -430, 54), (12, -452, 40), (80, -438, 36), (134, -408, 32), (176, -366, 28)]
        for tx, ty, tr in TOES:
            partes.append(lambda tx=tx, ty=ty, tr=tr: elipse(ctx, tx, ty, tr, tr * 1.15))
        union(ctx, partes, PIEL, 7)
        for tx, ty, tr in TOES:
            ctx.save()
            elipse(ctx, tx, ty, tr, tr * 1.15)
            ctx.clip()
            arrugas(ctx, mapa(tx, ty - tr * 1.1, tr, 0.75), arr, lw=4, luz=False)
            ctx.restore()
            brillo(ctx, tx, ty, tr * 2.2, brillo_y)
        ctx.save()
        elipse(ctx, 15, -270, 130, 110)
        ctx.clip()
        arrugas(ctx, mapa(15, -380, 120, 0.9), arr, lw=5, luz=False)
        ctx.restore()
        brillo(ctx, 10, -270, 220, brillo_y * 0.7)


def cuerpo(ctx, x, y, s=1.0, look=(0, 0), ojos="open", boca="smile"):
    """Figura de una persona genérica (no es Vos); (x, y) = entre los pies."""
    with en(ctx, x, y, s):
        partes = [lambda: elipse(ctx, 0, -830, 105, 105),
                  lambda: rrect(ctx, -125, -720, 250, 360, 100),
                  capsula(ctx, -150, -700, 70, 330), capsula(ctx, 80, -700, 70, 330),     # brazos
                  capsula(ctx, -100, -420, 85, 400), capsula(ctx, 15, -420, 85, 400)]     # piernas
        union(ctx, partes, PIEL, 7)
        rrect(ctx, -125, -720, 250, 300, 100)
        rellena(ctx, hx("#4C8DFF"), 7)
        carita(ctx, 0, -840, 80, 0.95, ojos=ojos, boca=boca, look=look, rubor=True)
        for sx in (-1, 1):
            elipse(ctx, sx * 115, -360, 46, 46)        # manos
            rellena(ctx, PIEL, 7)
            elipse(ctx, sx * 60 - (15 if sx > 0 else -15), 0, 70, 36)   # pies
            rellena(ctx, PIEL, 7)


MANOS_C = [(-115, -360), (115, -360)]
PIES_C = [(-45, 0), (45, 0)]
# puntos del cuerpo donde aparecerían arrugas si la piel chupara agua (cabeza, torso, brazos, piernas)
CUERPO_ARR = [(-60, -880), (50, -800), (-70, -650), (60, -600), (-30, -520), (70, -470), (-80, -440),
              (0, -680), (-120, -620), (120, -560), (-120, -500), (120, -650), (-60, -330), (60, -300),
              (-55, -200), (55, -150), (-60, -80), (60, -260)]


def garabato(ctx, x, y, L, a, lw=5):
    if a <= 0.01:
        return
    ctx.move_to(x - L / 2, y)
    for j in range(1, 7):
        ctx.line_to(x - L / 2 + L * j / 6, y + (8 if j % 2 else -8))
    trazo(ctx, ARRUGA, lw, a)


# ------------------------------------------------------------------ 1. apertura: la bañera (Vos solo acá y en el cierre)
T_BANO0 = b(0, "bano")
T_LARGO = b(0, "largo")
T_DEDOS0 = b(0, "dedos")
T_ARRUGAN0 = b(0, "arrugan")
VK = 0.95
VX, VY = 470, 1330                  # pies de Vos (dentro de la bañera)
TINA = (470, 1125, 420, 230)        # centro x, borde de arriba, medio ancho, alto
LUPA = (790, 520, 225)
RELOJ_C = (215, 470, 105)


@functools.lru_cache(maxsize=None)
def vos_surface(pose):
    poses = {"neutral": dict(), "mira": dict(look=(0.9, -0.5)), "sorpresa": dict(eyes="wide", brows="up",
                                                                                     mouth_kind="o"),
             "contento": dict(eyes="happy", brows="happy", mouth_kind="open_smile")}
    body = kit.vos(**poses[pose])
    png = cairosvg.svg2png(bytestring=kit.svg(520, 820, body).encode(), output_width=1040, output_height=1640)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


def vos(ctx, pose, x, y, k=1.0, alpha=1.0):
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


def banera(ctx, u):
    cx, top, hw, h = TINA
    # patas
    for sx in (-1, 1):
        elipse(ctx, cx + sx * (hw - 70), top + h + 10, 34, 26)
        rellena(ctx, hx("#FFC933"), 6)
    ctx.move_to(cx - hw, top)
    ctx.line_to(cx + hw, top)
    ctx.curve_to(cx + hw, top + h * 0.9, cx + hw - 60, top + h, cx + hw - 140, top + h)
    ctx.line_to(cx - hw + 140, top + h)
    ctx.curve_to(cx - hw + 60, top + h, cx - hw, top + h * 0.9, cx - hw, top)
    ctx.close_path()
    g = cairo.LinearGradient(0, top, 0, top + h)
    g.add_color_stop_rgb(0, *BANERA)
    g.add_color_stop_rgb(1, *BANERA_SOMBRA)
    ctx.set_source(g)
    ctx.fill_preserve()
    trazo(ctx, INK, 8)
    rrect(ctx, cx - hw - 22, top - 22, 2 * hw + 44, 44, 22)
    rellena(ctx, BANERA, 8)


def espuma(ctx, u):
    cx, top, hw, h = TINA
    for k in range(11):
        x = cx - hw + 30 + k * (2 * hw - 60) / 10
        r = 46 + 12 * math.sin(k * 2.1)
        yy = top - 30 - 8 * math.sin(k * 1.7) + 4 * math.sin(u * 3 + k)
        ctx.arc(x, yy, r, 0, TAU)
        rellena(ctx, ESPUMA, 6)
    # burbujitas que suben (periódicas: el cierre empalma con el inicio)
    for k in range(7):
        ph = ((u / 2.2) + k / 7) % 1
        x = cx - hw + 80 + k * 110 + 18 * math.sin(ph * 6 + k)
        y = top - 70 - ph * 260
        r = 10 + (k % 3) * 5
        ctx.arc(x, y, r, 0, TAU)
        ctx.set_source_rgba(1, 1, 1, 0.75 * math.sin(ph * math.pi))
        ctx.set_line_width(4)
        ctx.stroke()


def patito(ctx, x, y, s, u):
    with en(ctx, x, y + 5 * math.sin(u * 2.4), s, 0.06 * math.sin(u * 2.4)):
        elipse(ctx, 0, 0, 80, 52)
        rellena(ctx, PATO, 7)
        ctx.arc(-40, -60, 46, 0, TAU)
        rellena(ctx, PATO, 7)
        elipse(ctx, -92, -52, 26, 13)
        rellena(ctx, PICO, 6)
        carita(ctx, -42, -66, 36, 0.55)
        ctx.move_to(10, -10)
        ctx.curve_to(40, -30, 70, -10, 60, 20)
        trazo(ctx, hx("#E0B21E"), 6)


def vapor(ctx, u):
    for k in range(3):
        ph = ((u / 2.4) + k / 3) % 1
        x = 230 + k * 220
        y = 980 - ph * 280
        a = 0.45 * math.sin(ph * math.pi)
        ctx.move_to(x, y)
        ctx.curve_to(x - 30, y - 40, x + 30, y - 70, x, y - 110)
        trazo(ctx, BLANCO, 12, a)


def reloj(ctx, u):
    x, y, R = RELOJ_C
    ctx.arc(x, y, R, 0, TAU)
    rellena(ctx, RELOJ, 8)
    for k in range(12):
        g = k * TAU / 12
        ctx.move_to(x + 0.78 * R * math.cos(g), y + 0.78 * R * math.sin(g))
        ctx.line_to(x + 0.9 * R * math.cos(g), y + 0.9 * R * math.sin(g))
        trazo(ctx, INK, 5)
    # el baño largo: el minutero da vueltas
    giro = 2.5 * TAU * prog(u, T_BANO0, T_ARRUGAN0 - T_BANO0, "inout") if u >= 0 else 0.0
    gm = -math.pi / 2 + giro
    gh = -math.pi / 2 + 1.0 + giro / 12
    ctx.move_to(x, y)
    ctx.line_to(x + 0.5 * R * math.cos(gh), y + 0.5 * R * math.sin(gh))
    trazo(ctx, INK, 11)
    ctx.move_to(x, y)
    ctx.line_to(x + 0.75 * R * math.cos(gm), y + 0.75 * R * math.sin(gm))
    trazo(ctx, ROJO, 8)
    ctx.arc(x, y, 10, 0, TAU)
    ctx.set_source_rgb(*INK)
    ctx.fill()


def lupa(ctx, u, arr):
    x, y, R = LUPA
    # cola de la burbuja: apunta a la mano de Vos, bajo el agua
    ctx.move_to(x - 0.55 * R, y + 0.7 * R)
    ctx.line_to(VX + 140, TINA[1] - 60)
    ctx.line_to(x - 0.2 * R, y + 0.92 * R)
    ctx.close_path()
    rellena(ctx, BLANCO, 8)
    ctx.arc(x, y, R, 0, TAU)
    ctx.set_source_rgb(*AGUA_CLARA)
    ctx.fill()
    ctx.save()
    ctx.arc(x, y, R, 0, TAU)
    ctx.clip()
    for k, (dx, r) in enumerate(((-150, 70), (-2, 78), (148, 72))):
        ytop = y - 105 + (22 if k != 1 else 0)
        yema(ctx, x + dx, ytop, r, abajo=y + R + 50, arr=arr, lw=5.5)
    ctx.restore()
    ctx.arc(x, y, R, 0, TAU)
    trazo(ctx, INK, 26)
    ctx.arc(x, y, R, 0, TAU)
    trazo(ctx, BLANCO, 14)


def d_apertura(ctx, u):
    """Apertura; también es el cierre con el tiempo corrido (u < 0 = antes del principio)."""
    fondo(ctx, u % TOTAL)
    reloj(ctx, u)
    vapor(ctx, u)
    vos(ctx, "mira", VX, VY, VK)
    banera(ctx, u)
    espuma(ctx, u)
    patito(ctx, TINA[0] + 290, TINA[1] - 80, 0.9, u)
    arr = prog(u, T_ARRUGAN0, 0.6, "out") if u >= 0 else 0.0
    sc = P.bump(u, T_DEDOS0 - 0.1, 0.3, 0.06) if u >= 0 else 1.0
    with en(ctx, LUPA[0], LUPA[1], sc):
        ctx.translate(-LUPA[0], -LUPA[1])
        lupa(ctx, u, arr)


def d_cierre(ctx, t):
    d_apertura(ctx, t - TOTAL)


# ------------------------------------------------------------------ 2. el brazo sigue liso
T_BRAZO = b(1, "brazo")
T_MOJADO = b(1, "mojado")
T_LISO = b(1, "liso")
T_POR2 = b(2)
T_DEDOS2 = b(2, "dedos")
MANO_B = (560, 1090, 1.2)


def d_brazo(ctx, t):
    fondo(ctx, t)
    x, y, s = MANO_B
    s *= pop(t, b(1) - 0.05, 0.4)
    brillo_y = 0.6 * prog(t, T_POR2, 0.3) * (0.75 + 0.25 * math.sin((t - T_POR2) * 7))
    brillo(ctx, x, y + 260, 330, 0.5 * P.bump(t, T_BRAZO, 0.5, 1.0) - 0.5 if t > T_BRAZO else 0, BLANCO)
    mano(ctx, x, y, s, arr=1.0, brillo_y=brillo_y, antebrazo=1000)
    # gotas que bajan por el brazo (mojado igual)
    for k in range(6):
        t0 = T_BRAZO - 0.2 + k * 0.32
        if t < t0:
            continue
        q = ((t - t0) / 1.6) % 1
        gx = x + (-80 + 34 * k) * s
        gy = y + (40 + q * 520) * s
        gotita(ctx, gx, gy, 16 * s, math.sin(q * math.pi))
    # liso: tilde en el antebrazo
    if t >= T_LISO - 0.1:
        tilde(ctx, x + 250, y + 200, 1.25 * pop(t, T_LISO - 0.1, 0.35))
        kartel(ctx, "LISO", x, y + 200, 70, t, T_LISO - 0.05, box=VERDE, fg=BLANCO)
    # ¿por qué solo los dedos?
    for k, (fx, fw, fl) in enumerate(DEDOS):
        signo(ctx, "?", x + fx * s, y + (-290 - fl - 85) * s, 92, t, T_POR2 + 0.12 * k)


# ------------------------------------------------------------------ 3. la esponja
T_PARECE = b(3)
T_PIEL3 = b(3, "piel")
T_CHUPA = b(3, "chupa")
T_ESPONJA = b(3, "esponja")


def d_esponja(ctx, t):
    fondo(ctx, t)
    # la piel que "chupa": la yema con una pajita
    yx, ytop, r = 330, 640, 150
    sy = pop(t, T_PARECE - 0.05, 0.4)
    with en(ctx, yx, ytop + 300, sy):
        ctx.translate(-yx, -(ytop + 300))
        yema(ctx, yx, ytop, r, abajo=1500, arr=0.0, lw=7)
        carita(ctx, yx, ytop + 190, 120, 1.2, ojos="open", boca="o" if t > T_CHUPA else "smile", rubor=True)
    # gotas que entran en la piel
    for k in range(5):
        t0 = T_CHUPA - 0.2 + 0.18 * k
        q = clamp((t - t0) / 0.55)
        if 0 < q < 1:
            gotita(ctx, yx + (-60 + 30 * k), lerp(380, ytop + 40, ease(q, "in")), 20, 1 - q * 0.6)
    # la esponja
    se = pop(t, T_ESPONJA - 0.25, 0.4)
    moja = prog(t, T_ESPONJA, 0.5)
    esponja(ctx, 800, 780, 1.3 * se, moja=moja, look=(-0.8, 0.1), boca="grin" if moja > 0.5 else "smile")
    for k in range(4):
        t0 = T_ESPONJA - 0.15 + 0.15 * k
        q = clamp((t - t0) / 0.5)
        if 0 < q < 1:
            gotita(ctx, 750 + 34 * k, lerp(420, 640, ease(q, "in")), 22, 1 - q * 0.5)
    signo(ctx, "=", 560, 760, 120, t, T_ESPONJA - 0.15)
    if t > T_CHUPA:
        kartel(ctx, "¿CHUPA AGUA?", 540, 330, 68, t, T_CHUPA - 0.05)


# ------------------------------------------------------------------ 4. si fuera eso, todo el cuerpo
T_PERO4 = b(4)
T_ARRUGARIA = b(4, "arrugaria")
T_CUERPO = b(4, "cuerpo")
T_SOLO5 = b(5)
T_MANOS = b(5, "manos")
T_PIES = b(5, "pies")
CUERPO_P = (540, 1340, 0.92)


def d_cuerpo(ctx, t):
    fondo(ctx, t)
    x, y, s = CUERPO_P
    sc = pop(t, T_PERO4 - 0.05, 0.4) * s
    hipot = prog(t, T_PERO4, 0.3) * sale(t, T_SOLO5 - 0.1, 0.25)
    if hipot > 0.01:
        # marco de "¿y si...?" (nube de pensamiento punteada)
        rrect(ctx, 150, 290, 780, 1110, 60)
        ctx.set_dash([26, 20])
        trazo(ctx, BLANCO, 7, 0.55 * hipot)
        ctx.set_dash([])
        kartel(ctx, "¿Y SI FUERA ESO?", 540, 300, 60, t, T_PERO4 + 0.05, T_SOLO5 - 0.15)
    ojos = "wide" if T_ARRUGARIA < t < T_SOLO5 + 0.4 else "open"
    boca = "o" if T_ARRUGARIA < t < T_SOLO5 + 0.4 else "smile"
    cuerpo(ctx, x, y, sc, ojos=ojos, boca=boca)
    # arrugas por todo el cuerpo (hipotéticas), que se van en "solo"
    for k, (px, py) in enumerate(CUERPO_ARR):
        a = prog(t, T_ARRUGARIA + 0.05 * k, 0.25) * sale(t, T_SOLO5 + 0.02 * k, 0.25)
        garabato(ctx, x + px * s, y + py * s, 70 * s, a)
    # solo manos y pies
    for (px, py), t0 in ((MANOS_C[0], T_MANOS), (MANOS_C[1], T_MANOS + 0.1), (PIES_C[0], T_PIES),
                         (PIES_C[1], T_PIES + 0.1)):
        if t < t0 - 0.1:
            continue
        gx, gy = x + px * s, y + py * s
        brillo(ctx, gx, gy, 110, prog(t, t0 - 0.1, 0.25))
        for j in range(3):
            garabato(ctx, gx, gy - 18 + 18 * j, 50, prog(t, t0 - 0.05, 0.2), 6)
        ctx.arc(gx, gy, 85 * P.bump(t, t0 - 0.1, 0.35, 0.25), 0, TAU)
        trazo(ctx, AMARILLO, 9, prog(t, t0 - 0.1, 0.2))


# ------------------------------------------------------------------ 5. no es el agua: es una orden de los nervios
T_NO6 = b(6)
T_AGUA6 = b(6, "agua")
T_ES6 = b(6, "es", n=1)
T_ORDEN = b(6, "orden")
T_NERVIOS = b(6, "nervios")
CEREBRO_P = (540, 420, 0.7)
MANO_N = (560, 1300, 0.95)


def d_orden(ctx, t):
    fondo(ctx, t)
    # la gota: no es el agua
    sg = pop(t, T_NO6 - 0.05, 0.35) * (1 - prog(t, T_ES6 - 0.05, 0.3, "in"))
    triste = t > T_AGUA6 + 0.15
    gota(ctx, 540, 760, 150, s=sg, cara=("open", "flat" if triste else "smile"), ceja="worried" if triste else None)
    if t >= T_AGUA6 - 0.05:
        cruz_roja(ctx, 540, 760, 1.1 * pop(t, T_AGUA6 - 0.05, 0.25) * (1 - prog(t, T_ES6 - 0.05, 0.3, "in")))
    # el cerebro manda la orden por el nervio
    sc = pop(t, T_ES6, 0.4)
    if sc > 0.01:
        cx, cy, cs = CEREBRO_P
        P.cerebro(ctx, cx, cy, cs * sc, brillo=0.8 * P.bump(t, T_ORDEN - 0.05, 0.5, 1.0) - 0.8 if t > T_ORDEN else 0)
        x, y, s = MANO_N
        mano(ctx, x, y, s * pop(t, T_ES6 + 0.15, 0.4), arr=0.0, antebrazo=400,
             brillo_y=prog(t, T_NERVIOS + 0.25, 0.3))
        # nervio del cerebro a la muñeca y de ahí a los dedos
        a = prog(t, T_ES6 + 0.2, 0.3)
        ruta = [(cx + 60, cy + 150 * cs * 1.6), (cx + 260, cy + 420), (cx - 220, y - 640), (x, y + 60)]
        q = prog(t, T_ORDEN, T_NERVIOS + 0.2 - T_ORDEN, "inout")
        curva(ctx, ruta, a)
        trazo(ctx, INK, 15, a)
        curva(ctx, ruta, a)
        trazo(ctx, AMARILLO, 8, a)
        with en(ctx, x, y, s):
            pulso = (q - 0.75) / 0.25 if q > 0.75 else None
            nervio_mano(ctx, a, pulso, 70)
        if 0 < q < 0.78:
            px, py = bez(ruta, q / 0.78)
            brillo(ctx, px, py, 90, 1.0)
            ctx.arc(px, py, 16, 0, TAU)
            rellena(ctx, BLANCO, 5)
        sello(ctx, "ORDEN", 790, 640, 76, t, T_ORDEN - 0.05)


# ------------------------------------------------------------------ 6. la yema: vasos que se achican, globo, pliegues
T_VASOS = b(7, "vasos")
T_SANGRE7 = b(7, "sangre")
T_YEMA7 = b(7, "yema")
T_ACHICAN = b(7, "achican")
T_YEMA8 = b(8, "yema")
T_DESINFLA = b(8, "desinfla")
T_GLOBO = b(8, "globo")
T_PIEL9 = b(9, "piel")
T_SOBRA = b(9, "sobra")
T_PLIEGA = b(9, "pliega")
YG = (470, 440, 250)   # yema grande: x, punta, medio ancho


def d_yema(ctx, t):
    fondo(ctx, t)
    cx, ytop, r = YG
    t0 = b(7) - 0.05
    achica = prog(t, T_ACHICAN - 0.1, 0.5)
    desinfla = prog(t, T_DESINFLA, 0.7)
    rr = r * (1 - 0.07 * desinfla)
    rayos = prog(t, T_VASOS - 0.15, 0.35) * (1 - 0.65 * prog(t, T_PIEL9, 0.4))
    pliegue = prog(t, T_SOBRA, 0.5)
    arr = prog(t, T_PLIEGA - 0.1, 0.7, "out")
    sc = lerp(0.85, 1.0, prog(t, t0, 0.45, "out"))
    with en(ctx, cx, ytop + 600, sc):
        ctx.translate(-cx, -(ytop + 600))
        yema(ctx, cx, ytop + (r - rr) * 0.6, rr, abajo=2000, arr=arr, rayos=rayos,
             ancho_vaso=lerp(22, 8, achica), pulso=0.5 + 0.5 * math.sin(t * 8), nervio=1.0, pliegue=pliegue)
    # flechas que aprietan los vasos
    if T_ACHICAN - 0.2 < t < T_YEMA8:
        a = prog(t, T_ACHICAN - 0.2, 0.2) * sale(t, T_YEMA8 - 0.2)
        for sx in (-1, 1):
            xx = cx + sx * (r + 70)
            ctx.move_to(xx + sx * 50, ytop + 330)
            ctx.line_to(xx - sx * 10, ytop + 330)
            trazo(ctx, BLANCO, 14, a)
            ctx.move_to(xx + sx * 5, ytop + 300)
            ctx.line_to(xx - sx * 25, ytop + 330)
            ctx.line_to(xx + sx * 5, ytop + 360)
            trazo(ctx, BLANCO, 14, a)
    kartel(ctx, "VASOS DE SANGRE", 540, 300, 58, t, T_VASOS - 0.05, T_YEMA8 - 0.2, box=SANGRE, fg=BLANCO)
    # el globo que se desinfla
    sg = pop(t, T_GLOBO - 0.4, 0.4) * sale(t, T_PIEL9 - 0.1, 0.3)
    infla = 1 - prog(t, T_GLOBO - 0.1, 0.6)
    globo(ctx, 850, 640, 0.95 * sg, infla=infla, look=(-0.8, 0.2), boca="o" if infla < 0.7 else "smile", t=t)
    if T_GLOBO - 0.1 < t < T_GLOBO + 0.8:
        for k in range(3):   # aire que sale
            q = clamp((t - T_GLOBO + 0.1 - 0.15 * k) / 0.5)
            if 0 < q < 1:
                ctx.arc(850 + 20 * k - 20, 640 + 260 + q * 120, 10 + 10 * q, 0, TAU)
                trazo(ctx, BLANCO, 5, 1 - q)
    kartel(ctx, "SE PLIEGA", 540, 300, 64, t, T_PLIEGA - 0.05)


# ------------------------------------------------------------------ 7. nervio dañado: ese dedo no se arruga
T_NERVIO10 = b(10, "nervio")
T_DANADO = b(10, "danado")
T_ESE = b(10, "ese")
T_NO10 = b(10, "no")
T_ARRUGA10 = b(10, "arruga")
DOS = [(310, 620, 140), (770, 620, 140)]


def d_danado(ctx, t):
    fondo(ctx, t)
    t0 = b(10) - 0.05
    for k, (x, ytop, r) in enumerate(DOS):
        s = pop(t, t0 + 0.12 * k, 0.4)
        corte = prog(t, T_DANADO, 0.35) if k == 1 else 0.0
        arr = prog(t, T_ESE + 0.1, 0.8, "out") if k == 0 else 0.0
        with en(ctx, x, ytop + 400, s):
            ctx.translate(-x, -(ytop + 400))
            rayos = prog(t, T_NERVIO10 - 0.1, 0.3) * (1 - 0.7 * prog(t, T_ESE, 0.4))
            yema(ctx, x, ytop, r, abajo=1450, arr=arr, rayos=rayos, nervio=1.0,
                 ancho_vaso=14, corte=corte, lw=8)
    # agua que cae sobre los dos
    for k in range(8):
        tt = T_ESE - 0.4 + 0.12 * k
        q = clamp((t - tt) / 0.5)
        if 0 < q < 1:
            x = DOS[k % 2][0] + (-60 + 40 * (k // 2))
            gotita(ctx, x, lerp(330, 560, ease(q, "in")), 18, 1 - q * 0.5)
    if t > T_DANADO:
        kartel(ctx, "NERVIO DAÑADO", DOS[1][0], 1250, 50, t, T_DANADO, box=ROJO, fg=BLANCO)
    if t > T_ARRUGA10 - 0.2:
        kartel(ctx, "SE ARRUGA", DOS[0][0], 1250, 50, t, T_ESE + 0.6)
        kartel(ctx, "LISO", DOS[1][0], 390, 64, t, T_NO10 - 0.05)
        tilde(ctx, DOS[0][0], 400, 0.9 * pop(t, T_ESE + 0.6, 0.3))


# ------------------------------------------------------------------ 8. ¿para qué? el experimento de las canicas mojadas
T_PARA = b(11)
T_EN12 = b(12)
T_EXPERIMENTO = b(12, "experimento")
T_ARRUGADOS = b(12, "arrugados")
T_AGARRARON = b(12, "agarraron")
T_MEJOR = b(12, "mejor")
T_MOJADAS = b(12, "mojadas")
PINZAS = [(300, 800), (780, 800)]


def pinza(ctx, x, y, arr, caida, s=1.0, t=0.0):
    """Índice que baja y pulgar que sube, apretando una canica mojada."""
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        cy = 0 + caida * 330
        # canica
        ctx.arc(0, cy, 62, 0, TAU)
        rellena(ctx, CANICA, 7)
        elipse(ctx, -20, cy - 22, 16, 11)
        ctx.set_source_rgba(1, 1, 1, 0.8)
        ctx.fill()
        for sy in (-1, 1):    # índice arriba, pulgar abajo
            w, L = 120, 290
            ytip = sy * 62 if sy < 0 else 62
            yi = -62 - L if sy < 0 else 62
            rrect(ctx, -w / 2, yi, w, L, w / 2)
            rellena(ctx, PIEL, 7)
            ctx.save()
            rrect(ctx, -w / 2, yi, w, L, w / 2)
            ctx.clip()
            if sy < 0:
                mp = (lambda xx, yy: (xx * 55, -62 - yy * 120))
            else:
                mp = (lambda xx, yy: (xx * 55, 62 + yy * 120))
            if arr > 0.01:
                ctx.set_source_rgba(*PIEL_YEMA, 0.8 * arr)
                ctx.rectangle(-w / 2, -62 - 150 if sy < 0 else 62, w, 150)
                ctx.fill()
            arrugas(ctx, mp, arr, lw=5, luz=False)
            ctx.restore()
            _ = ytip
        # gotitas en la canica
        for k in range(3):
            q = ((t * 1.3) + k / 3) % 1
            gotita(ctx, -30 + 30 * k, cy + 70 + q * 60, 9, 1 - q)


def cuenco(ctx, x, y):
    ctx.move_to(x - 200, y)
    ctx.curve_to(x - 200, y + 150, x + 200, y + 150, x + 200, y)
    ctx.close_path()
    rellena(ctx, hx("#FF8FA8"), 8)
    elipse(ctx, x, y, 200, 40)
    rellena(ctx, AGUA, 8)


def d_experimento(ctx, t):
    fondo(ctx, t)
    # ¿para qué?
    if t < T_EN12 + 0.3:
        signo(ctx, "?", 540, 760, 360, t, T_PARA - 0.05, T_EN12)
    if t < T_EN12 - 0.1:
        return
    kartel(ctx, "EXPERIMENTO", 540, 330, 66, t, T_EXPERIMENTO - 0.1, box=BLANCO)
    for k, (x, y) in enumerate(PINZAS):
        cuenco(ctx, x, y + 400)
        s = pop(t, T_EN12 + 0.1 + 0.15 * k, 0.4)
        caida = 0.0
        if k == 0:   # los lisos se resbalan
            caida = ease(clamp((t - T_AGARRARON - 0.25) / 0.45), "in")
        pinza(ctx, x, y, 1.0 if k == 1 else 0.0, caida, 0.9 * s, t)
        if k == 0 and t > T_AGARRARON + 0.7:
            q = clamp((t - T_AGARRARON - 0.7) / 0.5)
            for j in range(5):   # salpicadura
                g = math.pi + j * math.pi / 4
                gotita(ctx, x + math.cos(g) * 90 * q, y + 380 + math.sin(g) * 80 * q, 12, 1 - q)
    kartel(ctx, "LISOS", PINZAS[0][0], 1330, 54, t, T_EN12 + 0.3, box=GRIS)
    kartel(ctx, "ARRUGADOS", PINZAS[1][0], 1330, 54, t, T_ARRUGADOS - 0.05)
    if t > T_MEJOR - 0.1:
        tilde(ctx, PINZAS[1][0] + 150, PINZAS[1][1] - 90, 1.1 * pop(t, T_MEJOR - 0.1, 0.3))
        signo(ctx, "!", PINZAS[0][0] + 140, PINZAS[0][1] - 120, 130, t, T_AGARRARON + 0.3, col=ROJO)


# ------------------------------------------------------------------ 9. ranuras como un neumático
T_LAS13 = b(13)
T_SACAN = b(13, "sacan")
T_AGUA13 = b(13, "agua")
T_COMO13 = b(13, "como")
T_RANURAS = b(13, "ranuras")
T_NEUMATICO = b(13, "neumatico")
YN = (300, 520, 190)
NEU = (800, 760, 225)


def d_neumatico(ctx, t):
    fondo(ctx, t)
    cx, ytop, r = YN
    s = pop(t, b(13) - 0.05, 0.4)
    with en(ctx, cx, ytop + 400, s):
        ctx.translate(-cx, -(ytop + 400))
        yema(ctx, cx, ytop, r, abajo=1450, arr=1.0, lw=11)
    # el agua sale por los canales de las arrugas
    mp = mapa(cx, ytop, r)
    for k, c in enumerate(CURVAS[:5]):
        for j in range(2):
            t0 = T_SACAN - 0.1 + 0.08 * k + 0.45 * j
            q = clamp((t - t0) / 0.9)
            if 0 < q < 1:
                px, py = bez([mp(x, y) for x, y in c], q)
                gotita(ctx, px, py, 15, math.sin(q * math.pi))
    # el neumático, con agua que sale por las ranuras
    sn = pop(t, T_COMO13 - 0.05, 0.4)
    giro = 2.2 * (t - T_COMO13) if t > T_COMO13 else 0
    nx, ny, nr = NEU
    neumatico(ctx, nx, ny, nr, giro, sn, look=(-0.8, 0), boca="grin" if t > T_NEUMATICO else "smile")
    if t > T_RANURAS:
        for k in range(7):
            q = ((t - T_RANURAS) * 1.4 + k / 7) % 1
            g = math.pi * 0.95 + k * 0.08
            gotita(ctx, nx + math.cos(g) * (nr + 20 + 160 * q), ny + nr - 20 - 120 * q + 160 * q * q, 13,
                   (1 - q) * sn)
        ctx.move_to(nx - nr - 40, ny + nr + 12)
        ctx.line_to(nx + nr + 40, ny + nr + 12)
        trazo(ctx, BLANCO, 8, 0.6 * sn)
    signo(ctx, "=", 540, 760, 110, t, T_COMO13)
    kartel(ctx, "RANURAS", NEU[0], 1110, 62, t, T_RANURAS - 0.05)


# ------------------------------------------------------------------ 10. donde agarras y donde pisas
T_POR14 = b(14)
T_AGARRAS = b(14, "agarras")
T_PISAS = b(14, "pisas")


def d_donde(ctx, t):
    fondo(ctx, t)
    mano(ctx, 300, 1170, 0.86 * pop(t, T_POR14 - 0.05, 0.4), arr=1.0,
         brillo_y=prog(t, T_AGARRAS - 0.1, 0.3) * (0.8 + 0.2 * math.sin(t * 8)), antebrazo=300)
    pie(ctx, 790, 1180, 0.95 * pop(t, T_POR14 + 0.2, 0.4), arr=1.0,
        brillo_y=prog(t, T_PISAS - 0.1, 0.3) * (0.8 + 0.2 * math.sin(t * 8)))
    kartel(ctx, "AGARRAS", 300, 380, 62, t, T_AGARRAS - 0.1)
    kartel(ctx, "PISAS", 790, 380, 62, t, T_PISAS - 0.1)


# ------------------------------------------------------------------ 11. no salen al azar
T_LO15 = b(15)
T_RARO = b(15, "raro")
T_TUS15 = b(15, "tus")
T_AZAR = b(15, "azar")
YA = (330, 560, 190)


def d_azar(ctx, t):
    fondo(ctx, t)
    cx, ytop, r = YA
    s = pop(t, T_LO15 - 0.05, 0.4)
    with en(ctx, cx, ytop + 400, s):
        ctx.translate(-cx, -(ytop + 400))
        yema(ctx, cx, ytop, r, abajo=1450, arr=prog(t, T_TUS15 - 0.1, 0.6, "out"), lw=11)
    signo(ctx, "!", cx + r + 40, ytop - 20, 150, t, T_RARO - 0.1)
    # dados que ruedan
    for k, (dx, dy, pp) in enumerate(((760, 650, 3), (860, 900, 5))):
        t0 = b(15) + 0.2 + 0.15 * k
        q = prog(t, t0, 0.9, "out")
        x = lerp(1200, dx, q)
        rot = (1 - q) * 6 + k * 0.3
        dado(ctx, x, dy - 80 * math.sin(q * math.pi), 150, rot, pop(t, t0, 0.3), pp)
    if t >= T_AZAR - 0.1:
        cruz_roja(ctx, 810, 780, 1.25 * pop(t, T_AZAR - 0.1, 0.25))
        kartel(ctx, "AZAR", 810, 1060, 62, t, T_AZAR - 0.1, box=ROJO, fg=BLANCO)


# ------------------------------------------------------------------ 12. salen siempre igual, siguiendo los vasos
T_SALEN16 = b(16)
T_SIEMPRE = b(16, "siempre")
T_IGUAL = b(16, "igual")
T_SIGUIENDO = b(16, "siguiendo")
T_VASOS16 = b(16, "vasos")
T_SANGRE16 = b(16, "sangre")
DOS_I = [(300, 560, 175), (780, 560, 175)]


def d_igual(ctx, t):
    fondo(ctx, t)
    t0 = b(16) - 0.05
    for k, (x, ytop, r) in enumerate(DOS_I):
        s = pop(t, t0 + 0.1 * k, 0.4)
        arr = prog(t, T_SALEN16 + 0.05, 0.7, "out")
        rayos = prog(t, T_SIGUIENDO - 0.1, 0.4)
        with en(ctx, x, ytop + 400, s * P.bump(t, T_IGUAL - 0.05, 0.3, 0.06)):
            ctx.translate(-x, -(ytop + 400))
            yema(ctx, x, ytop, r, abajo=1450, arr=arr, rayos=rayos, ancho_vaso=24,
                 pulso=0.5 + 0.5 * math.sin(t * 8), lw=10)
        kartel(ctx, f"BAÑO {k + 1}", x, 380, 56, t, t0 + 0.2 + 0.1 * k, box=BLANCO)
    signo(ctx, "=", 540, 820, 150, t, T_IGUAL - 0.1)
    if t > T_SIGUIENDO:
        kartel(ctx, "SIGUEN LOS VASOS", 540, 1260, 56, t, T_VASOS16 - 0.1, box=SANGRE, fg=BLANCO)


# ------------------------------------------------------------------ 13. el dibujo ya está ahí, esperando
T_ESE17 = b(17)
T_DIBUJO = b(17, "dibujo")
T_AHI = b(17, "ahi")
T_YEMA17 = b(17, "yema")
T_DEDO17 = b(17, "dedo")
YD = (540, 520, 250)


def d_dibujo(ctx, t):
    fondo(ctx, t)
    cx, ytop, r = YD
    z = lerp(1.0, 1.06, prog(t, T_ESE17, 3.0, "inout"))
    with en(ctx, cx, ytop + 500, pop(t, T_ESE17 - 0.05, 0.4) * z):
        ctx.translate(-cx, -(ytop + 500))
        yema(ctx, cx, ytop, r, abajo=2000, arr=0.0, fantasma=prog(t, T_DIBUJO, 0.6) *
             (0.75 + 0.25 * math.sin(t * 5)), brillo_y=0.25 * P.bump(t, T_AHI - 0.1, 0.5, 1.0) - 0.25
             if t > T_AHI - 0.1 else 0)
    kartel(ctx, "YA ESTÁ AHÍ", 540, 330, 66, t, T_AHI - 0.1)


# ------------------------------------------------------------------ escenas
ESCENAS = [
    (0.0, d_apertura),
    (b(1) - 0.05, d_brazo),
    (b(3) - 0.05, d_esponja),
    (b(4) - 0.05, d_cuerpo),
    (b(6) - 0.05, d_orden),
    (b(7) - 0.05, d_yema),
    (b(10) - 0.05, d_danado),
    (b(11) - 0.05, d_experimento),
    (b(13) - 0.05, d_neumatico),
    (b(14) - 0.05, d_donde),
    (b(15) - 0.05, d_azar),
    (b(16) - 0.05, d_igual),
    (b(17) - 0.05, d_dibujo),
    (b(18) - 0.05, d_cierre),
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


# ------------------------------------------------------------------ sonido (solo golpes cortos)
def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    # 1. apertura
    for j in range(5):
        ev(T_BANO0 + 0.16 * j, "tick", 0.15, f=900 + 80 * j, d=0.04)
    ev(T_DEDOS0 - 0.1, "pop", 0.35)
    ev(T_ARRUGAN0, "crunch", 0.35, d=0.25)
    # 2. brazo
    ev(b(1) - 0.05, "pop", 0.4)
    ev(T_LISO - 0.1, "ding", 0.35)
    for k in range(4):
        ev(T_POR2 + 0.12 * k, "pop", 0.25)
    # 3. esponja
    ev(T_PARECE - 0.05, "pop", 0.35)
    ev(T_CHUPA, "plop", 0.35)
    ev(T_ESPONJA - 0.25, "pop", 0.4)
    ev(T_ESPONJA + 0.1, "plop", 0.35)
    # 4. cuerpo
    ev(T_PERO4 - 0.05, "pop", 0.35)
    for k in range(0, len(CUERPO_ARR), 3):
        ev(T_ARRUGARIA + 0.05 * k, "tick", 0.15, f=700 + 30 * k, d=0.04)
    ev(T_SOLO5, "clic", 0.35)
    ev(T_MANOS - 0.1, "ding", 0.3)
    ev(T_PIES - 0.1, "ding", 0.3)
    # 5. orden
    ev(T_NO6 - 0.05, "pop", 0.35)
    ev(T_AGUA6 - 0.05, "clunk", 0.45)
    ev(T_ES6, "pop", 0.35)
    ev(T_ORDEN - 0.05, "golpe", 0.45)
    ev(T_NERVIOS + 0.2, "zap", 0.35)
    # 6. yema
    ev(b(7) - 0.05, "pop", 0.35)
    ev(T_ACHICAN - 0.1, "clic", 0.4)
    ev(T_GLOBO - 0.4, "pop", 0.35)
    ev(T_GLOBO - 0.1, "plop", 0.3)
    ev(T_PLIEGA - 0.1, "crunch", 0.35, d=0.25)
    # 7. nervio dañado
    ev(b(10), "pop", 0.35)
    ev(T_DANADO, "zap", 0.4)
    ev(T_ESE + 0.1, "crunch", 0.3, d=0.25)
    ev(T_NO10 - 0.05, "clunk", 0.4)
    # 8. experimento
    ev(T_PARA - 0.05, "pop", 0.45)
    ev(T_EXPERIMENTO - 0.1, "pop", 0.35)
    ev(T_AGARRARON + 0.25, "tick", 0.25, f=500, d=0.06)
    ev(T_AGARRARON + 0.7, "plop", 0.4)
    ev(T_MEJOR - 0.1, "ding", 0.35)
    # 9. neumático
    ev(b(13) - 0.05, "pop", 0.35)
    ev(T_COMO13 - 0.05, "pop", 0.4)
    ev(T_RANURAS - 0.05, "pop", 0.3)
    # 10. donde
    ev(T_AGARRAS - 0.1, "ding", 0.3)
    ev(T_PISAS - 0.1, "ding", 0.3)
    # 11. azar
    ev(T_RARO - 0.1, "pop", 0.4)
    for k in range(2):
        ev(b(15) + 0.2 + 0.15 * k + 0.6, "clic", 0.3)
    ev(T_AZAR - 0.1, "clunk", 0.45)
    # 12. igual
    ev(b(16) - 0.05, "pop", 0.35)
    ev(T_IGUAL - 0.1, "ding", 0.4)
    ev(T_SIGUIENDO - 0.1, "pop", 0.3)
    # 13. dibujo
    ev(T_DIBUJO, "ding", 0.3)
    ev(T_AHI - 0.1, "pop", 0.3)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "por_que_se_arrugan_los_dedos.mp4"))
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

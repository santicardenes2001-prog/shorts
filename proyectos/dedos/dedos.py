"""Short "¿Por qué solo se arrugan los dedos?" — animación procedural (armazón de bostezo.py).

Estilo del canal: fondo azul con puntos, cámara con zoom continuo entre escenas, cosas con cara (el patito, la
esponja, la gota, el nervio, el globo) y subtítulos palabra por palabra. Vos sale solo en la bañera del principio y
el cierre vuelve al primer cuadro (loop).

Hilo que se repite: un único dibujo de arrugas por dedo (`PATRONES`), en coordenadas de la yema. Es el mismo en la
mano chica, en la yema gigante y en las fotos "BAÑO 1" y "BAÑO 2", y sigue a los vasos de sangre (la última idea).

Mano: siempre la izquierda, con la palma hacia nosotros (el pulgar queda a nuestra izquierda) y cinco dedos.

    python proyectos/dedos/dedos.py --hoja 0,3,6      # hoja de fotogramas -> proyectos/dedos/fotos/hoja.png
    python proyectos/dedos/dedos.py --probar
    python proyectos/dedos/dedos.py                   # render -> salidas/por_que_solo_se_arrugan_los_dedos.mp4
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
                    signo, tilde, trazo, zoom)

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "Después de un baño largo, tus dedos se arrugan.",                      # b0
    "Tu brazo estuvo igual de mojado, y sigue liso.",                       # b1
    "¿Por qué solo se arrugan los dedos?",                                  # b2
    "Parece que la piel chupa agua, como una esponja.",                     # b3
    "Pero si fuera eso, se arrugaría todo tu cuerpo.",                      # b4
    "Solo se arrugan los dedos de las manos y de los pies.",                # b5
    "No es el agua:",                                                       # b6
    "es una orden de tus nervios.",                                         # b7
    "Los vasos de sangre de la yema se achican.",                           # b8
    "La yema se desinfla como un globo.",                                   # b9
    "La piel que sobra se pliega.",                                         # b10
    "Si el nervio de un dedo está dañado, ese dedo no se arruga.",          # b11
    "¿Para qué?",                                                           # b12
    "En un experimento, los dedos arrugados agarraron mejor cosas mojadas.",  # b13
    "Las arrugas sacan el agua, como las ranuras de un neumático.",         # b14
    "Por eso saldrían justo donde agarras y donde pisas.",                  # b15
    "Lo más raro:",                                                         # b16
    "tus arrugas no salen al azar.",                                        # b17
    "Salen siempre igual, siguiendo tus vasos de sangre.",                  # b18
    "Ese dibujo ya está ahí, en la yema de tu dedo.",                       # b19
    "Esperando el próximo baño.",                                           # b20
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


# ------------------------------------------------------------------ tiempos clave
T_ARRUGAN0 = b(0, "arrugan")
T_BRAZO = b(1, "brazo")
T_MOJADO = b(1, "mojado")
T_LISO = b(1, "liso")
T_POR2 = b(2)
T_ARRUGAN2 = b(2, "arrugan")
T_DEDOS2 = b(2, "dedos")
T_PIEL3 = b(3, "piel")
T_CHUPA = b(3, "chupa")
T_ESPONJA = b(3, "esponja")
T_FUERA = b(4, "fuera")
T_ARRUGARIA = b(4, "arrugaria")
T_TODO = b(4, "todo")
T_CUERPO = b(4, "cuerpo")
T_SOLO5 = b(5)
T_DEDOS5 = b(5, "dedos")
T_MANOS = b(5, "manos")
T_PIES = b(5, "pies")
T_NO6 = b(6)
T_AGUA6 = b(6, "agua")
T_ES7 = b(7)
T_ORDEN = b(7, "orden")
T_NERVIOS = b(7, "nervios")
T_VASOS8 = b(8, "vasos")
T_SANGRE8 = b(8, "sangre")
T_YEMA8 = b(8, "yema")
T_ACHICAN = b(8, "achican")
T_DESINFLA = b(9, "desinfla")
T_GLOBO = b(9, "globo")
T_PIEL10 = b(10, "piel")
T_SOBRA = b(10, "sobra")
T_PLIEGA = b(10, "pliega")
T_NERVIO11 = b(11, "nervio")
T_DANADO = b(11, "danado")
T_ESE = b(11, "ese")
T_NO11 = b(11, "no")
T_ARRUGA11 = b(11, "arruga")
T_PARA = b(12)
T_EXPERIMENTO = b(13, "experimento")
T_ARRUGADOS13 = b(13, "arrugados")
T_AGARRARON = b(13, "agarraron")
T_MOJADAS = b(13, "mojadas")
T_SACAN = b(14, "sacan")
T_COMO14 = b(14, "como")
T_RANURAS = b(14, "ranuras")
T_NEUMATICO = b(14, "neumatico")
T_SALDRIAN = b(15, "saldrian")
T_AGARRAS = b(15, "agarras")
T_PISAS = b(15, "pisas")
T_LO16 = b(16)
T_ARRUGAS17 = b(17, "arrugas")
T_AZAR = b(17, "azar")
T_SALEN18 = b(18)
T_SIEMPRE = b(18, "siempre")
T_IGUAL18 = b(18, "igual")
T_SIGUIENDO = b(18, "siguiendo")
T_VASOS18 = b(18, "vasos")
T_DIBUJO = b(19, "dibujo")
T_AHI = b(19, "ahi")
T_YEMA19 = b(19, "yema")
T_ESPERANDO = b(20)
T_BANO20 = b(20, "bano")

# ------------------------------------------------------------------ colores
KF = 60 * round(14 * TOTAL / 60) / (14 * TOTAL)      # el fondo de puntos cierra justo en el loop
PIEL = hx(kit.P["piel"])
PIEL2 = hx(kit.P["piel2"])
PIEL_PALIDA = hx("#F4DCCB")
ARRUGA = hx("#B9785A")
ARRUGA_LUZ = hx("#FFEADB")
CARNE = hx("#F7B3A6")
CARNE2 = hx("#EE9A8C")
HUESO = hx(kit.P["hueso"])
UNA = hx("#FBE3E3")
SANGRE = hx("#E0303A")
SANGRE2 = hx("#A8182A")
NERVIO = hx("#FFD23F")
NERVIO_GRIS = hx("#8C8FA3")
AGUA = hx("#7CCBFF")
AGUA2 = hx("#3FA4F0")
ESPUMA = hx("#FFFFFF")
ESPUMA2 = hx("#DCE6FF")
BANERA = hx("#5BC0EB")
BANERA2 = hx("#2F8FC2")
BORDE_B = hx("#F4F7FF")
DORADO = hx("#F2B33D")
PATITO = hx("#FFD23F")
PICO_P = hx("#FF8F3F")
ESPONJA = hx("#FFD95A")
ESPONJA2 = hx("#E8B937")
GOMA = hx("#2B2F3D")
GOMA2 = hx("#3E4457")
ASFALTO = hx("#3A3F52")
VIDRIO = hx("#BFE6FF")
CANICA = [hx("#FF5D5D"), hx("#46C281"), hx("#4C8DFF"), hx("#FFD23F")]
GLOBO_C = hx("#FF6B8B")
CIAN = hx("#7FF5FF")


# ------------------------------------------------------------------ ayudas generales
def fondo(ctx, t, oscuro=0.0):
    fondo_azul(ctx, (t % TOTAL) * KF)
    if oscuro > 0:
        ctx.set_source_rgba(0.027, 0.043, 0.11, oscuro)
        ctx.paint()


def per(t, periodo):
    """Fase (0..TAU) de un movimiento que cierra justo en el loop: un número entero de vueltas en TOTAL."""
    n = max(1, round(TOTAL / periodo))
    return TAU * n * (t % TOTAL) / TOTAL


def camara(ctx, z, cx, cy, sx=540, sy=900):
    """Lleva el punto (cx, cy) del dibujo al punto (sx, sy) de la pantalla, con zoom z."""
    ctx.translate(sx, sy)
    ctx.scale(z, z)
    ctx.translate(-cx, -cy)


def deriva(ctx, t, t0, t1, amt=0.05, cx=540, cy=900):
    """Acercamiento lento y continuo para que ningún plano quede quieto."""
    zoom(ctx, 1 + amt * clamp((t - t0) / max(t1 - t0, 0.01)), cx, cy)


def catmull(pts, n=10):
    """Curva suave que pasa por los puntos."""
    if len(pts) < 3:
        return pts
    q = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(n):
            s = k / n
            s2, s3 = s * s, s * s * s
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * s + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * s2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * s3) for j in range(2)))
    out.append(pts[-1])
    return out


def polilinea(ctx, pts, frac=1.0):
    """Traza una polilínea hasta la fracción frac de su largo."""
    if frac <= 0 or len(pts) < 2:
        return
    d = [0.0]
    for i in range(1, len(pts)):
        d.append(d[-1] + math.dist(pts[i - 1], pts[i]))
    lim = d[-1] * clamp(frac)
    ctx.move_to(*pts[0])
    for i in range(1, len(pts)):
        if d[i] <= lim:
            ctx.line_to(*pts[i])
        else:
            f = (lim - d[i - 1]) / max(d[i] - d[i - 1], 1e-6)
            ctx.line_to(lerp(pts[i - 1][0], pts[i][0], f), lerp(pts[i - 1][1], pts[i][1], f))
            break


def punto_en(pts, f):
    d = [0.0]
    for i in range(1, len(pts)):
        d.append(d[-1] + math.dist(pts[i - 1], pts[i]))
    lim = d[-1] * clamp(f)
    for i in range(1, len(pts)):
        if d[i] >= lim:
            g = (lim - d[i - 1]) / max(d[i] - d[i - 1], 1e-6)
            return lerp(pts[i - 1][0], pts[i][0], g), lerp(pts[i - 1][1], pts[i][1], g)
    return pts[-1]


def brillo(ctx, x, y, r, col=CIAN, a=1.0):
    if a <= 0.01:
        return
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *col, 0.9 * a)
    g.add_color_stop_rgba(0.35, *col, 0.45 * a)
    g.add_color_stop_rgba(1, *col, 0)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, TAU)
    ctx.fill()


def gotita(ctx, x, y, r, a=1.0):
    if a > 0.01 and r > 0.5:
        K.gota(ctx, x, y, r, AGUA, a, borde=r > 6)


def chispa(ctx, x, y, t, t0, r=70, col=AMARILLO, d=0.35):
    if not (t0 <= t < t0 + d):
        return
    q = (t - t0) / d
    for k in range(8):
        a_ = k * TAU / 8 + 0.3
        r0, r1 = r * (0.25 + 0.7 * q), r * (0.6 + 0.7 * q)
        ctx.move_to(x + r0 * math.cos(a_), y + r0 * math.sin(a_))
        ctx.line_to(x + r1 * math.cos(a_), y + r1 * math.sin(a_))
    trazo(ctx, col, 9, 1 - q)
    brillo(ctx, x, y, r * 0.8, col, 1 - q)


def anillo(ctx, x, y, rx, ry, a, col=AMARILLO, w=10):
    if a <= 0.01:
        return
    elipse(ctx, x, y, rx, ry)
    trazo(ctx, INK, w + 6, a)
    elipse(ctx, x, y, rx, ry)
    trazo(ctx, col, w, a)


def burbujas(ctx, t, x0, x1, y_base, n=10, seed=3, a=1.0, alto=260):
    """Burbujitas que suben y se desvanecen (movimiento periódico del loop)."""
    r = np.random.default_rng(seed)
    for k in range(n):
        x = r.uniform(x0, x1)
        ph = r.uniform(0, 1)
        q = ((t % TOTAL) / TOTAL * max(1, round(TOTAL / r.uniform(1.6, 2.6))) + ph) % 1
        y = y_base - q * alto
        rr = r.uniform(6, 15)
        elipse(ctx, x + 10 * math.sin(q * 9 + k), y, rr, rr)
        trazo(ctx, BLANCO, 3, a * (1 - q) * 0.8)


# ------------------------------------------------------------------ patrones de arrugas (uno por dedo, fijo)
# Coordenadas de la yema: u de -1 (izquierda) a 1 (derecha); v de 0 (punta) a 1 (pliegue de la última falange).
PATRON_INDICE = [
    [(-0.62, 0.92), (-0.66, 0.66), (-0.52, 0.42), (-0.30, 0.22), (-0.12, 0.13)],
    [(-0.18, 0.98), (-0.24, 0.72), (-0.10, 0.50), (0.06, 0.30), (0.22, 0.17)],
    [(0.30, 0.96), (0.36, 0.72), (0.26, 0.52), (0.40, 0.33), (0.52, 0.24)],
    [(0.74, 0.86), (0.66, 0.64), (0.76, 0.44)],
    [(-0.86, 0.72), (-0.80, 0.50), (-0.70, 0.36)],
    [(-0.42, 0.56), (-0.24, 0.62), (-0.10, 0.58)],
    [(0.04, 0.84), (0.16, 0.80), (0.30, 0.84)],
]


def patron_azar(seed):
    """Otros dibujos posibles (para "no salen al azar")."""
    r = np.random.default_rng(seed)
    out = []
    for _ in range(7):
        u = r.uniform(-0.8, 0.8)
        v = r.uniform(0.3, 0.95)
        pts = [(u, v)]
        ang = r.uniform(0, TAU)
        for _ in range(r.integers(2, 5)):
            ang += r.uniform(-1.2, 1.2)
            u = clamp(u + 0.25 * math.cos(ang), -0.85, 0.85)
            v = clamp(v + 0.2 * math.sin(ang), 0.1, 0.98)
            pts.append((u, v))
        out.append(pts)
    return out


def _patron_dedo(seed):
    r = np.random.default_rng(seed)
    out = []
    for j, u0 in enumerate((-0.55, 0.0, 0.55)):
        u = u0 + r.uniform(-0.12, 0.12)
        out.append([(u + r.uniform(-0.1, 0.1), 0.95), (u + r.uniform(-0.15, 0.15), 0.65),
                    (u * 0.6 + r.uniform(-0.1, 0.1), 0.35), (u * 0.3, 0.18)])
    return out


PATRONES = {"pulgar": _patron_dedo(11), "indice": PATRON_INDICE, "medio": _patron_dedo(13),
            "anular": _patron_dedo(17), "menique": _patron_dedo(19)}


# ------------------------------------------------------------------ la mano (izquierda, palma hacia nosotros)
# Coordenadas locales: muñeca en (0, 0), hacia arriba es -y. Escala 1: unos 430 px de la muñeca a la punta del medio.
DEDOS = [  # nombre, x base, y base, ángulo (grados), largo, ancho
    ("indice", -76, -226, -7, 176, 50),
    ("medio", -24, -236, -1, 196, 52),
    ("anular", 27, -230, 6, 180, 49),
    ("menique", 74, -210, 14, 140, 43),
]
PULGAR = ("pulgar", -88, -92, -50, 150, 56)
TODOS = [PULGAR] + DEDOS
IDX = {d[0]: k for k, d in enumerate(TODOS)}
YEMA_FR = 0.32          # la yema ocupa el último 32% del dedo


def _dedo_pt(d, along, u=0.0):
    """Punto de un dedo en coordenadas de la mano: along = 0 (base) .. 1 (punta); u = -1..1 a lo ancho."""
    _, bx, by, ang, L, w = d
    a = math.radians(ang)
    dx, dy = math.sin(a), -math.cos(a)            # dirección del dedo
    nx, ny = math.cos(a), math.sin(a)             # a lo ancho
    return bx + dx * L * along + nx * u * w / 2, by + dy * L * along + ny * u * w / 2


def yema_a_mano(d, u, v):
    """Coordenadas de la yema (u, v) a coordenadas de la mano."""
    w = d[5]
    along = 1 - (w / 2) / d[4] * 0.55 - v * (YEMA_FR - 0.05)
    return _dedo_pt(d, along, u * 0.82)


def nervio_pts(d):
    """Recorrido del nervio de un dedo, desde el antebrazo hasta cerca de la punta (coordenadas de la mano)."""
    bx = d[1]
    if d[0] == "pulgar":
        pts = [(bx * 0.25, 260), (bx * 0.35, 120), (-58, 10), (-76, -60)]
    else:
        pts = [(bx * 0.25, 260), (bx * 0.35, 120), (bx * 0.55, 0), (bx * 0.85, -110)]
    for f in (0.0, 0.3, 0.52, 0.64):
        pts.append(_dedo_pt(d, f))
    return catmull(pts, 6)


def _capsula(ctx, L, w):
    r = w / 2
    ctx.move_to(-r, 16)
    ctx.line_to(-r, -L + r)
    ctx.arc(0, -L + r, r, math.pi, TAU)
    ctx.line_to(r, 16)
    ctx.close_path()


def arrugas_yema(ctx, pts_uv, mapa, wr, s=1.0, ancho=3.4, luz=True):
    """Dibuja un patrón de arrugas (coordenadas de yema) con la función `mapa(u, v) -> (x, y)`."""
    if wr <= 0.01:
        return
    for k, linea in enumerate(pts_uv):
        pts = catmull([mapa(u, v) for u, v in linea], 8)
        fr = clamp(wr * 1.25 - 0.05 * k)
        if fr <= 0:
            continue
        if luz:
            ctx.save()
            ctx.translate(1.6 * s, 2.2 * s)
            polilinea(ctx, pts, fr)
            trazo(ctx, ARRUGA_LUZ, ancho * s * 1.1, 0.85)
            ctx.restore()
        polilinea(ctx, pts, fr)
        trazo(ctx, ARRUGA, ancho * s, 1.0)


def mano(ctx, x, y, s=1.0, rot=0.0, wr=None, glow=None, ante=260, nervios=0.0, dano=0.0, pulsos=None,
         plegado=0.0, palido=None, t=0.0, brillo_ante=None):
    """Mano izquierda con la palma hacia nosotros. (x, y) = muñeca.

    wr: arrugas por dedo (dict nombre -> 0..1); glow: brillo de la yema por dedo; nervios: 0..1 (se ven los nervios);
    dano: 0..1 (nervio del índice cortado); pulsos: dict nombre -> fracción (0..1) del pulso que sube por el nervio;
    brillo_ante: 0..1, reflejo que recorre el antebrazo.
    """
    wr = wr or {}
    glow = glow or {}
    pulsos = pulsos or {}
    lw = 7
    with en(ctx, x, y, s, rot):
        # antebrazo
        if ante > 0:
            ctx.move_to(-74, 10)
            ctx.curve_to(-80, ante * 0.4, -86, ante * 0.7, -90, ante)
            ctx.line_to(90, ante)
            ctx.curve_to(86, ante * 0.7, 80, ante * 0.4, 74, 10)
            ctx.close_path()
            path = ctx.copy_path()
            rellena(ctx, PIEL, lw)
            if brillo_ante is not None and 0 < brillo_ante < 1:
                ctx.save()
                ctx.append_path(path)
                ctx.clip()
                yb = lerp(-40, ante + 80, brillo_ante)
                g = cairo.LinearGradient(0, yb - 70, 0, yb + 70)
                g.add_color_stop_rgba(0, 1, 1, 1, 0)
                g.add_color_stop_rgba(0.5, 1, 1, 1, 0.75)
                g.add_color_stop_rgba(1, 1, 1, 1, 0)
                ctx.set_source(g)
                ctx.paint()
                ctx.restore()
        # pulgar y dedos (detrás de la palma en la base)
        for d in TODOS:
            nom, bx, by, ang, L, w = d
            with en(ctx, bx, by, 1.0, math.radians(ang)):
                _capsula(ctx, L, w)
                rellena(ctx, PIEL, lw)
                pal = (palido or {}).get(nom, wr.get(nom, 0.0))
                if pal > 0.01:
                    ctx.save()
                    _capsula(ctx, L, w)
                    ctx.clip()
                    ctx.rectangle(-w, -L - 5, 2 * w, L * YEMA_FR + 10)
                    ctx.set_source_rgba(*PIEL_PALIDA, 0.65 * pal)
                    ctx.fill()
                    ctx.restore()
                    _capsula(ctx, L, w)
                    trazo(ctx, INK, lw)
                # pliegues de las falanges (del lado de la palma)
                for f, ww in ((1 - YEMA_FR, 0.62), (0.42, 0.7)) if nom != "pulgar" else ((1 - YEMA_FR - 0.04, 0.62),):
                    yy = -L * f
                    ctx.move_to(-w * ww / 2, yy)
                    ctx.curve_to(-w * 0.15, yy + 6, w * 0.15, yy + 6, w * ww / 2, yy)
                    trazo(ctx, PIEL2, 4.5)
        # palma
        ctx.move_to(-70, 8)
        ctx.curve_to(-96, -40, -112, -110, -112, -168)
        ctx.curve_to(-112, -214, -100, -238, -80, -244)
        ctx.curve_to(-30, -258, 40, -256, 90, -232)
        ctx.curve_to(104, -224, 108, -200, 104, -170)
        ctx.curve_to(100, -110, 92, -40, 70, 8)
        ctx.close_path()
        rellena(ctx, PIEL, lw)
        # líneas de la palma
        ctx.move_to(-104, -150)
        ctx.curve_to(-40, -170, 30, -190, 96, -176)
        trazo(ctx, PIEL2, 5)
        ctx.move_to(-108, -120)
        ctx.curve_to(-50, -120, 10, -110, 60, -128)
        trazo(ctx, PIEL2, 5)
        ctx.move_to(-62, -40)
        ctx.curve_to(-70, -80, -84, -120, -100, -150)
        trazo(ctx, PIEL2, 5)
        # uniones limpias: se borra el contorno de la palma dentro de cada dedo y en la muñeca
        ctx.move_to(-70, 8)
        ctx.curve_to(-96, -40, -112, -110, -112, -168)
        ctx.curve_to(-112, -214, -100, -238, -80, -244)
        ctx.curve_to(-30, -258, 40, -256, 90, -232)
        ctx.curve_to(104, -224, 108, -200, 104, -170)
        ctx.curve_to(100, -110, 92, -40, 70, 8)
        ctx.close_path()
        palma = ctx.copy_path()
        ctx.new_path()
        for d in TODOS:
            nom, bx, by, ang, L, w = d
            ctx.save()
            with en(ctx, bx, by, 1.0, math.radians(ang)):
                _capsula(ctx, L, w - 9)
            ctx.clip()
            ctx.append_path(palma)
            trazo(ctx, PIEL, 14)
            ctx.restore()
            # el contorno del dedo, solo afuera de la palma
            ctx.save()
            ctx.rectangle(-600, -900, 1200, 1500)
            ctx.append_path(palma)
            ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            ctx.clip()
            with en(ctx, bx, by, 1.0, math.radians(ang)):
                _capsula(ctx, L, w)
            trazo(ctx, INK, lw)
            ctx.restore()
        if ante > 0:
            ctx.save()
            ctx.rectangle(-80, 2, 160, 60)
            ctx.clip()
            ctx.append_path(palma)
            trazo(ctx, PIEL, 14)
            ctx.restore()
            ctx.move_to(-62, 6)
            ctx.curve_to(-20, 14, 20, 14, 62, 6)
            trazo(ctx, PIEL2, 5)
        # arrugas y brillo de las yemas
        for d in TODOS:
            nom = d[0]
            g = glow.get(nom, 0.0)
            if g > 0.01:
                cx, cy = yema_a_mano(d, 0, 0.45)
                brillo(ctx, cx, cy, d[5] * 1.5, AMARILLO, g)
            arrugas_yema(ctx, PATRONES[nom][:4], lambda u, v, d=d: yema_a_mano(d, u, v), wr.get(nom, 0.0), 1.0,
                         ancho=3.2 if nom != "indice" else 3.4)
        # nervios
        if nervios > 0.01:
            for d in TODOS:
                nom = d[0]
                pts = nervio_pts(d)
                cortado = nom == "indice" and dano > 0.01
                if cortado:
                    corte = 0.42
                    pa = pts[:int(len(pts) * corte)]
                    pb = pts[int(len(pts) * corte) + 2:]
                    for seg, col in ((pa, NERVIO), (pb, lerp_col(NERVIO, NERVIO_GRIS, dano))):
                        polilinea(ctx, seg)
                        trazo(ctx, INK, 10, nervios)
                        polilinea(ctx, seg)
                        trazo(ctx, col, 5, nervios)
                else:
                    polilinea(ctx, pts)
                    trazo(ctx, INK, 10, nervios)
                    polilinea(ctx, pts)
                    trazo(ctx, NERVIO, 5, nervios)
            for nom, f in pulsos.items():
                if f is None or not (0 <= f < 0.995):
                    continue
                d = TODOS[IDX[nom]]
                pts = nervio_pts(d)
                if nom == "indice" and dano > 0.5:
                    if f > 0.55:
                        continue
                    f = min(f, 0.40)
                px, py = punto_en(pts, f)
                brillo(ctx, px, py, 46, AMARILLO, 1.0)
                ctx.arc(px, py, 11, 0, TAU)
                rellena(ctx, BLANCO, 4)


def lerp_col(c0, c1, p):
    return tuple(lerp(a, b_, p) for a, b_ in zip(c0, c1))


def mano_a_mundo(x, y, s, px, py, rot=0.0):
    c, si = math.cos(rot), math.sin(rot)
    return x + s * (px * c - py * si), y + s * (px * si + py * c)


# ------------------------------------------------------------------ la yema gigante (vista de frente)
def yema_marco(cx, top, Wp, Hp):
    return lambda u, v: (cx + u * Wp / 2 * 0.86, top + Wp * 0.12 + v * (Hp - Wp * 0.12))


def yema_grande(ctx, cx, top, Wp, Hp, t=0.0, wr=1.0, patron=None, trans=0.0, latente=0.0, agua=0.0,
                drena=0.0, palido=None, glob=0.0, cara=None):
    """La última falange del índice vista del lado de la palma, enorme. top = punta; Hp = alto hasta el pliegue."""
    patron = patron if patron is not None else PATRON_INDICE
    palido = wr if palido is None else palido
    r = Wp / 2
    # silueta
    ctx.move_to(cx - r, top + Hp + 600)
    ctx.line_to(cx - r, top + r)
    ctx.arc(cx, top + r, r, math.pi, TAU)
    ctx.line_to(cx + r, top + Hp + 600)
    ctx.close_path()
    sil = ctx.copy_path()
    rellena(ctx, PIEL, 9)
    ctx.save()
    ctx.append_path(sil)
    ctx.clip()
    # sombreado suave en los bordes
    g = cairo.LinearGradient(cx - r, 0, cx + r, 0)
    g.add_color_stop_rgba(0, *PIEL2, 0.55)
    g.add_color_stop_rgba(0.22, *PIEL2, 0)
    g.add_color_stop_rgba(0.78, *PIEL2, 0)
    g.add_color_stop_rgba(1, *PIEL2, 0.55)
    ctx.set_source(g)
    ctx.paint()
    if palido > 0.01:
        ctx.set_source_rgba(*PIEL_PALIDA, 0.55 * palido)
        ctx.paint()
    # huella digital (fina, de fondo)
    hx_, hy_ = cx + 0.05 * Wp, top + Hp * 0.52
    for k in range(1, 15):
        rr = k * Wp * 0.034
        ctx.save()
        ctx.translate(hx_, hy_)
        ctx.scale(1.0, 1.25)
        ctx.arc(0, 0, rr, math.radians(200), math.radians(340 + 25))
        ctx.restore()
        trazo(ctx, PIEL2, 2.6, 0.45)
    # pliegue de la falange abajo
    yb = top + Hp
    ctx.move_to(cx - r * 0.7, yb)
    ctx.curve_to(cx - r * 0.2, yb + 14, cx + r * 0.2, yb + 14, cx + r * 0.7, yb)
    trazo(ctx, PIEL2, 8)
    mapa = yema_marco(cx, top, Wp, Hp)
    sc = Wp / 560
    # vasos de sangre debajo de la piel (se ven cuando la piel se vuelve transparente)
    if trans > 0.01:
        ctx.set_source_rgba(*PIEL, 0.0)
        for linea in patron:
            pts = catmull([mapa(u, v) for u, v in linea], 8)
            polilinea(ctx, pts)
            trazo(ctx, SANGRE2, 30 * sc, trans)
            polilinea(ctx, pts)
            trazo(ctx, SANGRE, 20 * sc, trans)
            if glob > 0:
                for j in range(4):
                    f = ((t * 0.45 * glob) + j / 4 + 0.13 * len(linea)) % 1
                    px, py = punto_en(pts, f)
                    ctx.arc(px, py, 7 * sc, 0, TAU)
                    ctx.set_source_rgba(1, 0.75, 0.75, trans)
                    ctx.fill()
    # agua sobre la yema (apoyada en un vidrio mojado)
    if agua > 0.01:
        ctx.set_source_rgba(*AGUA, 0.12 * agua)
        ctx.paint()
    ctx.restore()
    # arrugas
    arrugas_yema(ctx, patron, mapa, wr, s=sc * 2.6, ancho=4.2)
    # canales por donde sale el agua
    if drena > 0.01:
        for k, linea in enumerate(patron):
            pts = catmull([mapa(u, v) for u, v in linea], 8)
            for j in range(3):
                f = (drena * 1.6 + j / 3 + 0.17 * k) % 1
                px, py = punto_en(pts, f)
                gotita(ctx, px, py, 9 * sc, a=clamp(1.4 - drena))
    # dibujo latente (está aunque no haya arrugas)
    if latente > 0.01:
        ctx.save()
        ctx.set_dash([4 * sc * 2.6, 9 * sc * 2.6])
        for linea in patron:
            pts = catmull([mapa(u, v) for u, v in linea], 8)
            polilinea(ctx, pts)
            trazo(ctx, CIAN, 7 * sc * 2.2, latente)
        ctx.restore()
        for linea in patron:
            pts = catmull([mapa(u, v) for u, v in linea], 8)
            px, py = punto_en(pts, (t * 0.35) % 1)
            brillo(ctx, px, py, 40 * sc * 2.2, CIAN, 0.8 * latente)
    if cara:
        carita(ctx, cx, top + Hp * 0.55, 150 * sc * 2, 1.6 * sc * 2, **cara)


# ------------------------------------------------------------------ Vos en la bañera
@functools.lru_cache(maxsize=None)
def cabeza_vos(eyes, brows, mouth, lx, ly):
    body = kit.head(eyes=eyes, brows=brows, mouth_kind=mouth, look=(lx, ly))
    png = cairosvg.svg2png(bytestring=kit.svg(520, 560, body).encode(), output_width=1040, output_height=1120)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


def vos_cabeza(ctx, x, y, s, eyes="open", brows="neutral", mouth="smile", look=(0, 0), rot=0.0):
    """Cabeza de Vos (la del kit) con el centro en (x, y); s = 1 es radio 172."""
    surf = cabeza_vos(eyes, brows, mouth, round(look[0], 1), round(look[1], 1))
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s / 2, s / 2)
    ctx.translate(-520, -540)
    ctx.set_source_surface(surf, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint()
    ctx.restore()


AGUA_Y = 1168          # nivel del agua (borde de la bañera)
Z0, C0 = 1.4, (570, 1050)   # encuadre del primer cuadro
MANO_X, MANO_Y = 770, 805   # muñeca de la mano levantada
CAB = (425, 905)


def subida(u):
    """Cuánto salió el brazo del agua (0..1). u < 0 es el cierre (loop)."""
    if u < 0:
        return lerp(1.0, 0.32, ease(clamp((u + 1.25) / 1.25), "inout"))
    return lerp(0.32, 1.0, ease(clamp(u / 1.1), "out"))


def arrugas_bano(u):
    if u < 0:
        return 0.0
    return {d[0]: prog(u, T_ARRUGAN0 - 0.05 + 0.09 * k, 0.55, "out") for k, d in enumerate(TODOS)}


def cara_bano(u):
    """(eyes, brows, mouth, look) de Vos según el momento."""
    if u < 0 or u < T_ARRUGAN0 - 0.1:
        return "happy", "happy", "smile", (0, 0)
    if u < T_BRAZO:
        return "wide", "up", "o", (0.6, -0.6)
    if u < T_POR2:
        return "open", "neutral", "flat", (1, 0.6)
    if u < T_ARRUGAN2 + 0.2:
        return "open", "up", "o", (0.9, -0.7)
    return "open", "up", "flat", (0.9, -0.5)


def patito(ctx, x, y, s, t, look=(0.6, 0)):
    with en(ctx, x, y, s, 0.08 * math.sin(per(t, 1.9))):
        elipse(ctx, 0, 0, 95, 60)
        rellena(ctx, PATITO, 7)
        ctx.move_to(-95, -10)
        ctx.curve_to(-130, -40, -120, -70, -86, -40)
        rellena(ctx, PATITO, 7)
        ctx.arc(40, -70, 52, 0, TAU)
        rellena(ctx, PATITO, 7)
        ctx.move_to(84, -72)
        ctx.curve_to(130, -78, 132, -52, 86, -50)
        ctx.close_path()
        rellena(ctx, PICO_P, 6)
        ctx.move_to(-40, -6)
        ctx.curve_to(-10, 20, 30, 18, 50, -6)
        trazo(ctx, hx("#E8B92F"), 6)
        carita(ctx, 46, -84, 40, 0.6, ojos="open", boca="smile", look=look)


def espuma(ctx, t, x0, x1, y, seed=5, s=1.0):
    r = np.random.default_rng(seed)
    n = int((x1 - x0) / 46)
    for k in range(n):
        x = x0 + (k + r.uniform(-0.3, 0.3)) * (x1 - x0) / n
        rr = r.uniform(30, 52) * s
        dy = 5 * math.sin(per(t, r.uniform(1.6, 2.6)) + k)
        ctx.arc(x, y + dy - r.uniform(0, 18), rr, 0, TAU)
        ctx.set_source_rgb(*ESPUMA)
        ctx.fill_preserve()
        ctx.set_source_rgba(*ESPUMA2, 1)
        ctx.set_line_width(4)
        ctx.stroke()


def vapor_bano(ctx, t, a=1.0):
    for k, x in enumerate((180, 560, 930)):
        q = ((t % TOTAL) / TOTAL * max(1, round(TOTAL / 3.2)) + k * 0.33) % 1
        y = 1100 - q * 520
        ctx.move_to(x, y)
        for j in range(1, 6):
            ctx.line_to(x + 22 * math.sin(j * 1.3 + q * 6 + k), y - j * 34)
        trazo(ctx, BLANCO, 10, a * 0.22 * math.sin(q * math.pi))


def banera(ctx):
    for fx in (150, 930):
        with en(ctx, fx, 1445, 1.0):
            ctx.move_to(-34, -30)
            ctx.curve_to(-40, 20, -20, 46, 0, 50)
            ctx.curve_to(20, 46, 40, 20, 34, -30)
            ctx.close_path()
            rellena(ctx, DORADO, 7)
    ctx.move_to(40, AGUA_Y)
    ctx.line_to(1040, AGUA_Y)
    ctx.curve_to(1030, 1330, 960, 1440, 820, 1450)
    ctx.line_to(260, 1450)
    ctx.curve_to(120, 1440, 50, 1330, 40, AGUA_Y)
    ctx.close_path()
    path = ctx.copy_path()
    rellena(ctx, BANERA, 8)
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    g = cairo.LinearGradient(0, AGUA_Y, 0, 1450)
    g.add_color_stop_rgba(0, *BANERA2, 0)
    g.add_color_stop_rgba(1, *BANERA2, 0.9)
    ctx.set_source(g)
    ctx.paint()
    ctx.move_to(120, AGUA_Y + 70)
    ctx.curve_to(140, 1300, 200, 1360, 280, 1380)
    trazo(ctx, BLANCO, 14, 0.35)
    ctx.restore()
    rrect(ctx, 26, AGUA_Y - 18, 1028, 40, 20)
    rellena(ctx, BORDE_B, 8)


def gotas_mano(ctx, t, pts, seed=7, a=1.0):
    """Gotas que caen de la mano (movimiento periódico del loop)."""
    r = np.random.default_rng(seed)
    for k, (x, y) in enumerate(pts):
        n = max(1, round(TOTAL / r.uniform(0.9, 1.4)))
        q = ((t % TOTAL) / TOTAL * n + r.uniform(0, 1)) % 1
        yy = y + 380 * q * q
        if yy < AGUA_Y - 10:
            gotita(ctx, x, yy, 9 * (1 - 0.3 * q), a)


def d_bano(ctx, u):
    """La bañera. u = t en la apertura; u = t - TOTAL (negativo) en el cierre."""
    t = u % TOTAL
    fondo(ctx, t)
    ctx.save()
    # cámara: se acerca a la mano, baja por el brazo, se aleja con la pregunta
    if u < 0:
        f = ease(clamp((u + (TOTAL - T_ESPERANDO)) / 1.2), "inout")
        tip = _tip_bano(u)
        z = math.exp(lerp(math.log(6.0), math.log(Z0), f))
        cx, cy = lerp(tip[0], C0[0], f), lerp(tip[1], C0[1], f)
    else:
        f1 = ease(clamp(u / T_BRAZO), "inout")
        z, cx, cy = lerp(Z0, 1.6, f1), lerp(C0[0], 770, f1), lerp(C0[1], 650, f1)
        if u >= T_BRAZO:
            f2 = ease(clamp((u - T_BRAZO) / (T_POR2 - T_BRAZO)), "inout")
            z, cx, cy = lerp(1.6, 1.5, f2), 775, lerp(650, 950, f2)
        if u >= T_POR2:
            f3 = ease(clamp((u - T_POR2) / 0.8), "inout")
            z, cx, cy = lerp(1.5, 1.3, f3), lerp(775, 640, f3), lerp(950, 900, f3)
        if u >= T_DEDOS2:
            f4 = ease(clamp((u - T_DEDOS2) / (b(3) - T_DEDOS2)), "in")
            tip = _tip_bano(u)
            z, cx, cy = lerp(1.3, 3.4, f4), lerp(640, tip[0], f4), lerp(900, tip[1], f4)
    camara(ctx, z, cx, cy)
    vapor_bano(ctx, t)
    # Vos: hombros y cabeza
    eyes, brows, mouth, look = cara_bano(u)
    hx_, hy_ = CAB[0], CAB[1] + 6 * math.sin(per(t, 2.4))
    elipse(ctx, hx_, 1215, 200, 110)
    rellena(ctx, PIEL, 7)
    vos_cabeza(ctx, hx_, hy_, 0.93, eyes, brows, mouth, look, rot=0.03 * math.sin(per(t, 3.1)))
    # brazo izquierdo que sale del agua
    sub = subida(u)
    dy = (1 - sub) * 560
    ctx.save()
    ctx.rectangle(-2000, -2000, 5000, 2000 + AGUA_Y + 6)
    ctx.clip()
    wr = arrugas_bano(u)
    ba = None
    if 0 <= u and T_MOJADO - 0.2 <= u <= T_LISO + 0.6:
        ba = clamp((u - (T_MOJADO - 0.2)) / (T_LISO + 0.6 - T_MOJADO + 0.2))
    rot = math.radians(4 * math.sin(per(t, 2.2)))
    mano(ctx, MANO_X, MANO_Y + dy, 1.0, rot, wr=wr if isinstance(wr, dict) else {}, ante=430, brillo_ante=ba, t=t)
    if sub > 0.5:
        tips = [mano_a_mundo(MANO_X, MANO_Y + dy, 1.0, *_dedo_pt(d, 1.0), rot) for d in TODOS[1:]]
        gotas_mano(ctx, t, tips + [(MANO_X - 70, MANO_Y + dy + 120), (MANO_X + 80, MANO_Y + dy + 260)])
    ctx.restore()
    # anillos donde el brazo entra al agua
    for k in range(3):
        q = ((t % TOTAL) / TOTAL * max(1, round(TOTAL / 1.5)) + k / 3) % 1
        elipse(ctx, MANO_X, AGUA_Y - 6, 90 + 120 * q, 16 + 18 * q)
        trazo(ctx, BLANCO, 5, 0.7 * (1 - q))
    patito(ctx, 285, AGUA_Y - 34 + 6 * math.sin(per(t, 1.7)), 0.62, t, look=(0.7, -0.4))
    espuma(ctx, t, 40, 1040, AGUA_Y - 22)
    burbujas(ctx, t, 300, 1000, AGUA_Y - 40, n=8, seed=4, alto=200)
    banera(ctx)
    # la pregunta
    if u >= 0:
        if u >= T_LISO - 0.05:
            tilde(ctx, MANO_X + 150, 1040, 0.9 * pop(u, T_LISO - 0.05, 0.3) * sale(u, b(3) - 0.2))
        if u >= T_ARRUGAN2 - 0.05:
            sub = subida(u)
            rot = math.radians(4 * math.sin(per(t, 2.2)))
            ps = [mano_a_mundo(MANO_X, MANO_Y + (1 - sub) * 560, 1.0, *yema_a_mano(d, 0, 0.4), rot) for d in DEDOS]
            ax_, ay_ = sum(p_[0] for p_ in ps) / 4, sum(p_[1] for p_ in ps) / 4
            a = pop(u, T_ARRUGAN2 - 0.05, 0.3)
            anillo(ctx, ax_, ay_ + 10, 175 * a, 95 * a, sale(u, b(3) - 0.25))
    ctx.restore()
    if u >= 0:
        signo(ctx, "?", 190, 560, 260, u, T_POR2 + 0.05, b(3) - 0.15)


def _tip_bano(u):
    """Yema del índice de la mano de la bañera (coordenadas del mundo)."""
    sub = subida(u)
    t = u % TOTAL
    rot = math.radians(4 * math.sin(per(t, 2.2)))
    return mano_a_mundo(MANO_X, MANO_Y + (1 - sub) * 560, 1.0, *yema_a_mano(TODOS[IDX["indice"]], 0, 0.4), rot)


def d_apertura(ctx, t):
    d_bano(ctx, t)


def d_cierre(ctx, t):
    d_bano(ctx, t - TOTAL)


# ------------------------------------------------------------------ 2. la esponja
GOTAS_E = [(-1 if k % 2 else 1, 300 + 95 * k, 0.11 * k) for k in range(10)]


def esponja(ctx, x, y, s, t, cara=("open", "smile")):
    with en(ctx, x, y, s):
        rrect(ctx, -270, -300, 540, 600, 90)
        rellena(ctx, ESPONJA, 9)
        r = np.random.default_rng(8)
        for k in range(26):
            px, py = r.uniform(-220, 220), r.uniform(-250, 250)
            if abs(px) < 150 and -150 < py < 150:
                continue
            elipse(ctx, px, py, r.uniform(10, 26), r.uniform(8, 20))
            ctx.set_source_rgb(*ESPONJA2)
            ctx.fill()
        ctx.move_to(-240, 200)
        ctx.curve_to(-100, 230, 100, 230, 240, 200)
        trazo(ctx, ESPONJA2, 10)
        carita(ctx, 0, -20, 150, 2.0, ojos=cara[0], boca=cara[1], rubor=True)


def d_esponja(ctx, t):
    t0 = b(3)
    fondo(ctx, t)
    deriva(ctx, t, t0, b(4), 0.06)
    m = prog(t, T_ESPONJA - 0.12, 0.3, "out")
    absorbidas = sum(1 for lado, y0, dt in GOTAS_E if t > T_PIEL3 + dt + 0.55)
    hincha = 1 + 0.012 * absorbidas + 0.05 * math.sin(clamp((t - T_ESPONJA) / 0.4) * math.pi) * (t > T_ESPONJA)
    if m < 1:
        with alfa(ctx, 1 - m):
            ctx.save()
            zoom(ctx, hincha, 540, 900)
            yema_grande(ctx, 540, 330, 600, 760, t, wr=0.0, palido=0.0)
            ctx.restore()
    if m > 0:
        sq = 1 + 0.1 * math.sin(clamp((t - T_ESPONJA + 0.12) / 0.45) * math.pi * 2) * (1 - clamp((t - T_ESPONJA) / 0.6))
        with alfa(ctx, m):
            esponja(ctx, 540, 860, 0.95 * hincha * sq, t, cara=("happy", "grin"))
    # gotas que vuelan hacia la piel
    for lado, y0, dt in GOTAS_E:
        q = prog(t, T_PIEL3 + dt, 0.55, "in")
        if 0 < q < 1:
            x = lerp(540 + lado * 700, 540 + lado * 160, q)
            y = lerp(y0 + 200, 820 + 0.1 * (y0 - 700), q) - 120 * math.sin(q * math.pi)
            gotita(ctx, x, y, 26)


# ------------------------------------------------------------------ 3. "si fuera eso": burbuja de pensamiento
def nube_pensamiento(ctx, cx, cy, rx, ry, t, s=1.0):
    with en(ctx, cx, cy, s):
        n = 14
        for pasada in (0, 1):
            for k in range(n):
                a_ = k * TAU / n
                px, py = rx * 0.92 * math.cos(a_), ry * 0.92 * math.sin(a_)
                rr = 120 + 14 * math.sin(t * 3 + k * 1.7)
                ctx.arc(px, py, rr, 0, TAU)
                if pasada == 0:
                    trazo(ctx, INK, 16)
                else:
                    ctx.set_source_rgb(*hx("#2A3570"))
                    ctx.fill()
            if pasada == 0:
                elipse(ctx, 0, 0, rx, ry)
                trazo(ctx, INK, 16)
        elipse(ctx, 0, 0, rx, ry)
        ctx.set_source_rgb(*hx("#2A3570"))
        ctx.fill()


def personita_path(ctx):
    ctx.arc(0, -560, 92, 0, TAU)                       # cabeza
    ctx.new_sub_path()
    rrect(ctx, -110, -470, 220, 300, 70)               # torso
    ctx.new_sub_path()
    for sx in (-1, 1):                                  # brazos
        ctx.save()
        ctx.translate(sx * 112, -440)
        ctx.rotate(-sx * 0.22)
        rrect(ctx, -34, -10, 68, 250, 34)
        ctx.restore()
        ctx.new_sub_path()
    for sx in (-1, 1):                                  # piernas
        rrect(ctx, sx * 55 - 42, -200, 84, 200, 36)
        ctx.new_sub_path()
        elipse(ctx, sx * 62, 0, 56, 24)
        ctx.new_sub_path()


def d_burbuja(ctx, t):
    t0 = b(4)
    fondo(ctx, t)
    deriva(ctx, t, t0, b(5), 0.1, 560, 850)
    for k, (x, y, r) in enumerate(((150, 1390, 26), (215, 1300, 40), (300, 1205, 58))):
        s = pop(t, t0 + 0.06 * k, 0.25)
        if s > 0.01:
            ctx.arc(x, y, r * s, 0, TAU)
            rellena(ctx, hx("#2A3570"), 10)
    s = pop(t, t0 + 0.12, 0.4)
    if s < 0.02:
        return
    nube_pensamiento(ctx, 560, 850, 380, 470, t, s)
    ctx.save()
    with en(ctx, 560, 850, s):
        elipse(ctx, 0, 0, 380, 470)
        ctx.clip()
        p = prog(t, T_ARRUGARIA - 0.05, T_CUERPO + 0.25 - T_ARRUGARIA, "inout")
        tiembla = 4 * math.sin(t * 45) * clamp(p * 2 - 0.6)
        with en(ctx, tiembla, 380 + 14 * math.sin(t * 4), 0.98, 0.05 * math.sin(t * 2.5)):
            # toallón
            personita_path(ctx)
            rellena(ctx, lerp_col(PIEL, hx("#D9A07E"), p * 0.7), 8)
            ctx.save()
            personita_path(ctx)
            ctx.clip()
            yl = lerp(40, -680, p)
            r = np.random.default_rng(21)
            for k in range(70):
                x = r.uniform(-190, 190)
                y = r.uniform(-650, 20)
                if y < yl:
                    continue
                ctx.move_to(x - 26, y)
                ctx.curve_to(x - 10, y - 10, x + 10, y + 10, x + 26, y)
                trazo(ctx, ARRUGA, 4.5)
            ctx.restore()
            rrect(ctx, -125, -260, 250, 120, 30)
            rellena(ctx, hx("#7FD1FF"), 7)
            for k in range(4):
                ctx.move_to(-100 + 66 * k, -250)
                ctx.line_to(-100 + 66 * k, -150)
                trazo(ctx, hx("#5AB8EE"), 6)
            asust = t >= T_CUERPO - 0.1
            carita(ctx, 0, -575, 70, 1.05, ojos="open" if not asust else "open",
                   boca="smile" if p < 0.4 else ("o" if asust else "flat"), ceja="worried" if p > 0.4 else None,
                   look=(0, 0.2) if p < 0.5 else (0, 0.6), rubor=True)
    ctx.restore()


# ------------------------------------------------------------------ 4. solo manos y pies
DEDOS_PIE = [(-72, -470, 40, 52), (-14, -488, 27, 35), (30, -478, 25, 32), (67, -458, 22, 28), (98, -428, 19, 24)]


def pie_planta(ctx, x, y, s, wr=0.0, glow=0.0):
    """Planta del pie izquierdo, dedos hacia arriba (el dedo gordo a nuestra izquierda)."""
    with en(ctx, x, y, s):
        for k, (tx, ty, rx, ry) in enumerate(DEDOS_PIE):
            elipse(ctx, tx, ty, rx, ry)
            rellena(ctx, PIEL, 7)
        ctx.move_to(0, 0)
        ctx.curve_to(-82, 0, -96, -80, -82, -150)
        ctx.curve_to(-64, -230, -84, -300, -110, -370)
        ctx.curve_to(-120, -420, -100, -448, -60, -440)
        ctx.curve_to(0, -432, 60, -424, 104, -402)
        ctx.curve_to(124, -370, 108, -280, 86, -200)
        ctx.curve_to(72, -120, 86, -20, 0, 0)
        ctx.close_path()
        rellena(ctx, PIEL, 7)
        ctx.move_to(-70, -300)
        ctx.curve_to(-40, -250, 40, -250, 80, -280)
        trazo(ctx, PIEL2, 5)
        for k, (tx, ty, rx, ry) in enumerate(DEDOS_PIE):
            if glow > 0.01:
                brillo(ctx, tx, ty, rx * 1.9, AMARILLO, glow)
            if wr > 0.01:
                for j, du in enumerate((-0.45, 0.05, 0.5) if k == 0 else (-0.35, 0.3)):
                    fr = clamp(wr * 1.3 - 0.1 * j)
                    pts = [(tx + du * rx, ty - ry * 0.65), (tx + du * rx * 1.15, ty - ry * 0.1),
                           (tx + du * rx * 0.8, ty + ry * 0.5)]
                    ctx.save()
                    ctx.translate(1.5, 2)
                    polilinea(ctx, catmull(pts, 6), fr)
                    trazo(ctx, ARRUGA_LUZ, 3.6, 0.85)
                    ctx.restore()
                    polilinea(ctx, catmull(pts, 6), fr)
                    trazo(ctx, ARRUGA, 3.4)


def d_manos_pies(ctx, t):
    t0 = b(5)
    fondo(ctx, t)
    deriva(ctx, t, t0, b(6), 0.1, 540, 950)
    # la burbuja que explota
    if t < t0 + 0.35:
        q = (t - t0) / 0.35
        for k in range(16):
            a_ = k * TAU / 16
            rr = 300 + 420 * ease(q, "out")
            ctx.arc(560 + rr * math.cos(a_), 850 + rr * 1.2 * math.sin(a_), 34 * (1 - q), 0, TAU)
            ctx.set_source_rgba(*hx("#2A3570"), 1 - q)
            ctx.fill()
    salta = 1 + 0.06 * math.sin(clamp((t - T_DEDOS5) / 0.3) * math.pi)
    s1 = pop(t, t0 + 0.05, 0.35) * salta
    wrm = {d[0]: prog(t, T_MANOS - 0.12 + 0.05 * k, 0.4, "out") for k, d in enumerate(TODOS)}
    gm = {d[0]: wrm[d[0]] * (0.6 + 0.3 * math.sin(t * 8)) for d in TODOS}
    if s1 > 0.01:
        mano(ctx, 325, 1270, 1.12 * s1, -0.08 + 0.05 * math.sin(t * 2.6), wr=wrm, glow=gm, ante=140, t=t)
    s2 = pop(t, t0 + 0.22, 0.35) * salta
    wp = prog(t, T_PIES - 0.12, 0.4, "out")
    if s2 > 0.01:
        pie_planta(ctx, 790 + 10 * math.sin(t * 2.1), 1290, 1.12 * s2, wr=wp, glow=wp * (0.6 + 0.3 * math.sin(t * 8)))
    for k, (x, tt) in enumerate(((325, T_MANOS), (790, T_PIES))):
        chispa(ctx, x, 640, t, tt - 0.05, r=90)


# ------------------------------------------------------------------ 5. no es el agua
def gota_cara(ctx, x, y, r, rot=0.0, cara=None, sq=1.0):
    with en(ctx, x, y, 1.0, rot):
        ctx.scale(1 / sq, sq)
        K.gota(ctx, 0, 0, r, AGUA, 1.0)
        carita(ctx, 0, r * 0.25, r * 0.6, r / 110, **(cara or {}))


def d_gota(ctx, t):
    t0 = b(6)
    fondo(ctx, t)
    y = lerp(-250, 900, ease(clamp((t - t0) / 0.28), "out"))
    sq = 1 + 0.18 * math.sin(clamp((t - t0 - 0.24) / 0.22) * math.pi)
    x, rot = 540, 0.0
    hombros = math.sin(clamp((t - t0 - 0.3) / 0.3) * math.pi)
    rot = 0.12 * hombros
    cara = dict(ojos="open", boca="flat", ceja="worried" if hombros > 0.2 else None, look=(0.4, -0.3))
    q = prog(t, T_AGUA6 + 0.1, 0.32, "in")
    if q > 0:
        x = lerp(540, 1400, q)
        rot = 2.5 * q
        cara = dict(ojos="closed", boca="o", ceja="worried")
    gota_cara(ctx, x, y - 80 * hombros, 150, rot, cara, sq)
    for k in range(2):
        if 0.1 < hombros:
            texto(ctx, "?", 540 + (-230 if k else 230), 620 - 40 * hombros, 120, fill=BLANCO, alpha=hombros)
    sello(ctx, "NO", 540, 650, 170, t, T_AGUA6 - 0.04, col=ROJO)


# ------------------------------------------------------------------ 6. la orden de los nervios
def nervio_jefe(ctx, x, y, s, grita=0.0):
    with en(ctx, x, y, s):
        ctx.arc(0, 0, 78, 0, TAU)
        rellena(ctx, NERVIO, 8)
        carita(ctx, 0, -6, 52, 0.8, ojos="open", boca="o" if grita > 0.3 else "flat", ceja="angry")
        if grita > 0.01:
            for k in range(3):
                a_ = -math.pi / 2 + (k - 1) * 0.5
                ctx.move_to(100 * math.cos(a_), 100 * math.sin(a_))
                ctx.line_to((130 + 30 * grita) * math.cos(a_), (130 + 30 * grita) * math.sin(a_))
            trazo(ctx, BLANCO, 9, grita)


MANO_N = (540, 1010, 1.2)


def d_nervios(ctx, t):
    t0 = b(7)
    fondo(ctx, t)
    x, y, s = MANO_N
    tip = mano_a_mundo(x, y, s, *yema_a_mano(TODOS[IDX["indice"]], 0, 0.4))
    f = ease(clamp((t - (T_NERVIOS + 0.1)) / (b(8) - T_NERVIOS - 0.1)), "in")
    camara(ctx, lerp(1.0, 2.8, f), lerp(540, tip[0], f), lerp(900, tip[1], f))
    nv = prog(t, t0 - 0.05, 0.3)
    pul = {d[0]: prog(t, T_ORDEN + 0.05, T_NERVIOS - T_ORDEN + 0.05, "in") for d in TODOS}
    llego = prog(t, T_NERVIOS + 0.05, 0.25)
    mano(ctx, x, y, s, 0.0, ante=360, nervios=nv, pulsos=pul if t > T_ORDEN else None,
         glow={d[0]: llego * (1 - prog(t, T_NERVIOS + 0.5, 0.3)) for d in TODOS}, t=t)
    for d in TODOS:
        px, py = mano_a_mundo(x, y, s, *_dedo_pt(d, 0.8))
        chispa(ctx, px, py, t, T_NERVIOS + 0.05, r=46)
    grita = clamp((t - T_ORDEN + 0.05) / 0.15) * (1 - prog(t, T_NERVIOS, 0.3))
    nervio_jefe(ctx, x, y + 300 * s, 0.95 * pop(t, t0 - 0.02, 0.3), grita)


# ------------------------------------------------------------------ 7. el corte de la yema (de costado)
def _env(x, x0=180, x1=930, pico=620):
    if x <= x0 or x >= x1:
        return 0.0
    if x < pico:
        return math.sin((x - x0) / (pico - x0) * math.pi / 2) ** 2
    return math.cos((x - pico) / (x1 - pico) * math.pi / 2) ** 1.2


def contorno_dedo(desinfla=0.0, pliegue=0.0):
    """Contorno del dedo de costado (punta a la derecha, uña arriba, yema abajo)."""
    pts = []
    for k in range(30):
        x = lerp(-300, 640, k / 29)
        pts.append((x, 745 - 6 * (x / 640) ** 2))
    for k in range(1, 41):
        a_ = -math.pi / 2 + math.pi * k / 40
        x = 650 + 262 * math.cos(a_)
        y = 985 + 250 * math.sin(a_)
        pts.append((x, y))
    for k in range(1, 40):
        x = lerp(650, -300, k / 39)
        y = 1235 + 22 * math.sin(clamp((x - 200) / 450) * math.pi)
        pts.append((x, y))
    out = []
    for x, y in pts:
        if y > 990:
            e = _env(x)
            y -= desinfla * 62 * e
            y += pliegue * 20 * math.sin((x - 240) / 34) * e
        out.append((x, y))
    return out


def baja_yema(x, y, desinfla):
    return y - desinfla * 52 * _env(x) * clamp((y - 1000) / 180)


ARTERIA = [(-300, 1075), (100, 1078), (420, 1080), (620, 1065), (760, 1012), (860, 940)]
RAMAS = [[(300, 1080), (320, 1140), (380, 1172)], [(520, 1078), (560, 1150), (640, 1176)],
         [(700, 1045), (770, 1120), (840, 1112)], [(820, 975), (880, 1010), (895, 1050)]]


def d_corte(ctx, t):
    t0 = b(8)
    fondo(ctx, t)
    q_ = ease(clamp((t - t0) / (b(11) - t0)), "inout")
    zc = lerp(0.95, 1.2, q_)
    camara(ctx, zc, lerp(520, 660, q_), lerp(930, 1000, q_))
    ctx.translate(-60, 0)
    achica = prog(t, T_ACHICAN - 0.05, 0.45, "out")
    desinfla = prog(t, T_DESINFLA, T_GLOBO + 0.35 - T_DESINFLA, "inout")
    pliegue = prog(t, T_PLIEGA - 0.15, 0.5, "out")
    pts = contorno_dedo(desinfla, pliegue)
    # carne (la yema)
    ctx.move_to(*pts[0])
    for p_ in pts[1:]:
        ctx.line_to(*p_)
    ctx.close_path()
    sil = ctx.copy_path()
    ctx.set_source_rgb(*CARNE)
    ctx.fill()
    ctx.save()
    ctx.append_path(sil)
    ctx.clip()
    # piel: una franja que sigue el contorno
    ctx.append_path(sil)
    brilla = prog(t, T_PIEL10 - 0.05, 0.25) * (1 - prog(t, T_PLIEGA + 0.6, 0.3))
    trazo(ctx, PIEL, 64)
    ctx.append_path(sil)
    trazo(ctx, PIEL2, 18)
    if brilla > 0.01:
        ctx.append_path(sil)
        trazo(ctx, AMARILLO, 30, brilla * (0.55 + 0.25 * math.sin(t * 10)))
    # huesos: la última falange (con la punta ensanchada) y la del medio, con la articulación
    ctx.move_to(205, 868)
    ctx.curve_to(400, 860, 520, 872, 590, 874)
    ctx.curve_to(660, 862, 715, 892, 712, 925)
    ctx.curve_to(708, 962, 660, 975, 600, 958)
    ctx.curve_to(500, 962, 380, 970, 205, 978)
    ctx.curve_to(180, 960, 180, 886, 205, 868)
    ctx.close_path()
    rellena(ctx, HUESO, 7)
    ctx.move_to(-300, 850)
    ctx.line_to(140, 858)
    ctx.curve_to(185, 862, 190, 984, 140, 988)
    ctx.line_to(-300, 992)
    ctx.close_path()
    rellena(ctx, HUESO, 7)
    # nervio
    nv = [(-300, 1012), (200, 1016), (520, 1020), (700, 990), (800, 960)]
    polilinea(ctx, catmull(nv, 8))
    trazo(ctx, INK, 13)
    polilinea(ctx, catmull(nv, 8))
    trazo(ctx, NERVIO, 7)
    if t < t0 + 0.6:
        px, py = punto_en(catmull(nv, 8), prog(t, t0 - 0.1, 0.6, "inout"))
        brillo(ctx, px, py, 50, AMARILLO)
    # vasos de sangre
    w_v = lerp(30, 12, achica) * (1 + 0.12 * max(0.0, math.sin(t * 7.5)) ** 4)
    lineas = [catmull(ARTERIA, 8)] + [catmull([(x, baja_yema(x, y, desinfla)) for x, y in r_], 8) for r_ in RAMAS]
    resal = prog(t, T_VASOS8 - 0.05, 0.25) * (1 - prog(t, T_YEMA8, 0.3))
    for k, ln_ in enumerate(lineas):
        ww = w_v if k == 0 else w_v * 0.65
        polilinea(ctx, ln_)
        trazo(ctx, SANGRE2, ww + 9)
        polilinea(ctx, ln_)
        trazo(ctx, SANGRE, ww)
        if resal > 0.01:
            polilinea(ctx, ln_)
            trazo(ctx, BLANCO, ww * 0.35, 0.6 * resal)
    vel = lerp(1.0, 0.25, achica)
    fase = (t - t0) * 0.55 * vel if t < T_ACHICAN else (T_ACHICAN - t0) * 0.55 + (t - T_ACHICAN) * 0.55 * 0.25
    for k, ln_ in enumerate(lineas):
        n = 9 if k == 0 else 3
        for j in range(n):
            if achica > 0.5 and j % 2:
                continue
            f = (fase * (1 if k == 0 else 1.6) + j / n) % 1
            px, py = punto_en(ln_, f)
            ctx.arc(px, py, (w_v if k == 0 else w_v * 0.65) * 0.32, 0, TAU)
            ctx.set_source_rgb(*hx("#FF9A9A"))
            ctx.fill()
    ctx.restore()
    # uña
    ctx.move_to(470, 742)
    ctx.curve_to(620, 728, 790, 745, 870, 790)
    ctx.curve_to(880, 798, 876, 810, 862, 806)
    ctx.curve_to(780, 776, 620, 760, 470, 768)
    ctx.close_path()
    rellena(ctx, UNA, 7)
    # contorno
    ctx.append_path(sil)
    trazo(ctx, INK, 9)
    # el vaso con cara
    cx_, cy_ = punto_en(lineas[0], 0.56)
    if t > t0 + 0.2:
        carita(ctx, cx_, cy_ - 2, 30 * (w_v / 30) + 12, 0.42 + 0.14 * (w_v / 30),
               ojos="closed" if achica > 0.3 else "open", boca="wavy" if achica > 0.3 else "smile",
               ceja="angry" if achica > 0.3 else None)
    # flechitas que aprietan
    if 0 < achica < 1 or (T_ACHICAN - 0.05 < t < T_ACHICAN + 0.9):
        a = clamp((t - T_ACHICAN + 0.05) / 0.15) * (1 - prog(t, T_ACHICAN + 0.6, 0.3))
        for x0 in (250, 470):
            for sy in (-1, 1):
                y0 = 1078 + sy * (70 - 25 * achica)
                ctx.move_to(x0 - 22, y0 - sy * 10)
                ctx.line_to(x0, y0 + sy * 14)
                ctx.line_to(x0 + 22, y0 - sy * 10)
                trazo(ctx, BLANCO, 9, a)
    # carteles
    kartel(ctx, "UÑA", 660, 640, 46, t, t0 + 0.15, T_VASOS8 + 0.9, rot=-4)
    kartel(ctx, "HUESO", 400, 800, 46, t, t0 + 0.3, T_VASOS8 + 1.1, rot=3)
    kartel(ctx, "VASOS DE SANGRE", 470, 1330, 50, t, T_VASOS8 - 0.05, T_DESINFLA, box=ROJO, fg=BLANCO)
    # el globo que se desinfla
    gs = pop(t, T_GLOBO - 0.55, 0.3) * sale(t, T_PIEL10 + 0.15, 0.25)
    if gs > 0.01:
        dq = prog(t, T_GLOBO - 0.2, 0.6, "inout")
        tam = lerp(1.0, 0.42, dq)
        wob = 0.08 * math.sin(t * 30) * dq * (1 - dq) * 4
        gx, gy = 880, 460
        ctx.move_to(gx, gy + 150 * tam)
        ctx.curve_to(gx + 30, gy + 220, gx - 30, gy + 260, gx + 10, gy + 320)
        trazo(ctx, BLANCO, 4, gs)
        with en(ctx, gx, gy, gs, wob):
            ctx.save()
            ctx.scale(tam * (1 + wob), tam * 1.15)
            elipse(ctx, 0, 0, 115, 135)
            rellena(ctx, GLOBO_C, 8 / max(tam, 0.4))
            elipse(ctx, -40, -50, 22, 34)
            ctx.set_source_rgba(1, 1, 1, 0.6)
            ctx.fill()
            carita(ctx, 0, -10, 70, 1.0, ojos="open", boca="o" if dq > 0.1 else "smile",
                   ceja="worried" if dq > 0.1 else None)
            ctx.restore()
            if 0.05 < dq < 0.95:
                for k in range(3):
                    yy = 160 * tam + 20 + 30 * k + ((t * 3) % 1) * 30
                    ctx.move_to(-20 + 20 * k, yy)
                    ctx.line_to(-30 + 30 * k, yy + 30)
                trazo(ctx, BLANCO, 6, 0.8)


# ------------------------------------------------------------------ 8. el nervio dañado
MANO_D = (540, 1290, 1.42)


def d_dano(ctx, t):
    t0 = b(11)
    fondo(ctx, t)
    deriva(ctx, t, t0, b(13), 0.12, 540, 850)
    x, y, s = MANO_D
    nv = prog(t, t0 - 0.05, 0.3)
    dano = prog(t, T_DANADO - 0.05, 0.25)
    sube = {d[0]: prog(t, T_ESE - 0.08, 0.45, "in") for d in TODOS} if t > T_ESE - 0.08 else None
    wr = {d[0]: (0.0 if d[0] == "indice" else prog(t, T_ESE + 0.38, 0.35, "out")) for d in TODOS}
    luz = {d[0]: prog(t, T_NERVIO11 + 0.06 * k, 0.2) * (1 - prog(t, T_NERVIO11 + 0.5, 0.3)) for k, d in enumerate(TODOS)}
    mano(ctx, x, y, s, 0.03 * math.sin(t * 2.2), wr=wr, glow=luz, ante=150, nervios=nv, dano=dano, pulsos=sube, t=t)
    pts = nervio_pts(TODOS[IDX["indice"]])
    bx_, by_ = mano_a_mundo(x, y, s, *punto_en(pts, 0.43))
    chispa(ctx, bx_, by_, t, T_DANADO - 0.05, r=80, col=ROJO)
    if t > T_DANADO:
        cruz_roja(ctx, bx_ + 60, by_, 0.28 * pop(t, T_DANADO, 0.3))
    # el índice queda liso
    if t > T_NO11 - 0.1:
        ix, iy = mano_a_mundo(x, y, s, *yema_a_mano(TODOS[IDX["indice"]], 0, 0.45))
        a = pop(t, T_NO11 - 0.1, 0.3)
        anillo(ctx, ix, iy, 62 * s * a, 80 * s * a, 1.0, col=BLANCO)
        q = prog(t, T_ARRUGA11, 0.4)
        if 0 < q < 1:
            ctx.move_to(ix - 30, iy + 60 - 120 * q)
            ctx.line_to(ix + 30, iy + 20 - 120 * q)
            trazo(ctx, BLANCO, 10, math.sin(q * math.pi))


def d_paraque(ctx, t):
    d_dano(ctx, t)
    ctx.set_source_rgba(0.03, 0.05, 0.12, 0.6 * prog(t, b(12) - 0.05, 0.12))
    ctx.paint()
    sh = 6 * math.sin(t * 50) * (1 - prog(t, b(12) + 0.1, 0.3))
    s_ = 1 + 0.5 * (1 - ease(clamp((t - b(12) + 0.05) / 0.22), "back"))
    with en(ctx, 540 + sh, 880, s_ * (t > b(12) - 0.05), 0.08 * math.sin(t * 9)):
        texto(ctx, "?", 0, 0, 560, fill=AMARILLO, sw=18)


# ------------------------------------------------------------------ 9. el experimento de las canicas
FILAS = {"lisos": 590, "arrugados": 1135}
CICLO = {"lisos": 0.98, "arrugados": 0.66}
INICIO_EXP = T_EXPERIMENTO + 0.55
FIN_ARRUGADOS = INICIO_EXP + 4 * CICLO["arrugados"]
RESBALA = {1, 3}                   # ciclos de los dedos lisos en que se les cae la canica


def tazon(ctx, x, y, agua=True):
    elipse(ctx, x, y, 170, 40)
    rellena(ctx, hx("#E9EEF9"), 7)
    ctx.move_to(x - 170, y)
    ctx.curve_to(x - 160, y + 170, x + 160, y + 170, x + 170, y)
    ctx.curve_to(x + 120, y + 30, x - 120, y + 30, x - 170, y)
    rellena(ctx, hx("#DCE3F3"), 7)
    if agua:
        elipse(ctx, x, y + 14, 140, 28)
        ctx.set_source_rgba(*AGUA, 0.85)
        ctx.fill()


def estado_canicas(fila, t):
    """(cuántas pasaron, ciclo actual, fase 0..1 del ciclo o None)."""
    q = (t - INICIO_EXP) / CICLO[fila]
    if q < 0:
        return 0, -1, None
    k = int(q)
    ok = sum(1 for j in range(min(k, 6)) if not (fila == "lisos" and j in RESBALA))
    if ok >= 4:
        return 4, k, None
    return ok, k, q - k


def pinza(ctx, x, y, abre, arrugas, s=1.0):
    """Índice y pulgar que bajan desde arriba, con las puntas en (x, y); abre = 0 (cerrada) .. 1."""
    with en(ctx, x, y, s):
        elipse(ctx, 0, -205, 96, 64)
        rellena(ctx, PIEL, 7)
        for sx in (-1, 1):
            ang = sx * (0.10 + 0.24 * abre)
            with en(ctx, 0, -190, 1.0, ang):
                ctx.move_to(-24, 0)
                ctx.line_to(-24, 166)
                ctx.arc_negative(0, 166, 24, math.pi, 0)
                ctx.line_to(24, 0)
                ctx.close_path()
                rellena(ctx, PIEL, 7)
                if arrugas:
                    ctx.rectangle(-21, 140, 42, 46)
                    ctx.set_source_rgba(*PIEL_PALIDA, 0.7)
                    ctx.fill()
                    for j in range(3):
                        yy = 146 + 12 * j
                        ctx.move_to(-sx * 4, yy)
                        ctx.curve_to(-sx * 10, yy + 5, -sx * 15, yy + 1, -sx * 20, yy + 7)
                        trazo(ctx, ARRUGA, 3.4)
        elipse(ctx, 0, -205, 96, 64)
        ctx.set_source_rgb(*PIEL)
        ctx.fill()
        ctx.move_to(-90, -228)
        ctx.curve_to(-96, -170, -40, -150, 0, -150)
        ctx.curve_to(40, -150, 96, -170, 90, -228)
        trazo(ctx, INK, 7)


PANELES = {"arriba": (360, 885), "abajo": (905, 1430)}


def panel(ctx, y0, y1, a=1.0):
    """Recuadro de una de las dos mitades; devuelve el camino para recortar."""
    rrect(ctx, 50, y0, 980, y1 - y0, 40)
    path = ctx.copy_path()
    ctx.set_source_rgba(*hx("#1B2347"), 0.75 * a)
    ctx.fill()
    return path


def d_experimento(ctx, t):
    t0 = b(13)
    fondo(ctx, t)
    deriva(ctx, t, t0, b(14), 0.04)
    for fila, yf in FILAS.items():
        ap = pop(t, t0 + (0.15 if fila == "lisos" else 0.3), 0.35)
        if ap < 0.01:
            continue
        with en(ctx, 540, yf, ap):
            ctx.translate(-540, -yf)
            arr = fila == "arrugados"
            y0p, y1p = PANELES["abajo" if arr else "arriba"]
            marco = panel(ctx, y0p, y1p)
            ctx.save()
            ctx.append_path(marco)
            ctx.clip()
            pasaron, k, q = estado_canicas(fila, t)
            fin = arr and t >= FIN_ARRUGADOS
            tc = max(0.0, (min(t, FIN_ARRUGADOS) if arr else t) - INICIO_EXP)
            tazon(ctx, 290, yf + 70, agua=True)
            tazon(ctx, 790, yf + 70, agua=False)
            # canicas que esperan en el agua
            quedan = 4 - pasaron - (1 if q is not None and 0.32 < q < 0.88 and not (not arr and k in RESBALA and q > 0.6) else 0)
            for j in range(quedan):
                cx_ = 220 + 46 * j
                ctx.arc(cx_, yf + 95, 22, 0, TAU)
                rellena(ctx, CANICA[j], 5)
            for j in range(pasaron):
                ctx.arc(730 + 40 * j, yf + 95, 22, 0, TAU)
                rellena(ctx, CANICA[3 - j], 5)
            # la pinza
            px, py, abre, lleva = 290, yf - 50, 1.0, False
            if q is not None:
                if q < 0.22:
                    py = lerp(yf - 50, yf + 80, ease(q / 0.22))
                elif q < 0.32:
                    py, abre = yf + 80, 1 - (q - 0.22) / 0.1
                elif q < 0.55:
                    py, abre, lleva = lerp(yf + 80, yf - 30, ease((q - 0.32) / 0.23)), 0.0, True
                elif q < 0.82:
                    px, py, abre, lleva = lerp(290, 790, ease((q - 0.55) / 0.27)), yf - 30, 0.0, True
                elif q < 0.9:
                    px, py, abre = 790, yf + 10, (q - 0.82) / 0.08
                else:
                    px, py = lerp(790, 290, ease((q - 0.9) / 0.1)), yf - 50
                resbala = not arr and k in RESBALA and q > 0.6
                if resbala:
                    lleva = False
                    cq = clamp((q - 0.6) / 0.2)
                    sx_ = lerp(290, 790, ease((0.6 - 0.55) / 0.27))
                    ctx.arc(lerp(sx_, 300, cq), lerp(yf - 8, yf + 95, cq * cq), 22, 0, TAU)
                    rellena(ctx, CANICA[pasaron], 5)
                    if cq >= 1 and q < 0.9:
                        for m in range(5):
                            a_ = -math.pi / 2 + (m - 2) * 0.4
                            gotita(ctx, 300 + 60 * math.cos(a_) * (q - 0.8) * 8, yf + 60 - 50 * (q - 0.8) * 8, 10)
                    if 0.6 < q < 0.75:
                        texto(ctx, "¡UPS!", 150, yf - 60, 56, fill=ROJO, alpha=math.sin((q - 0.6) / 0.15 * math.pi))
            if lleva:
                ctx.arc(px, py + 22, 22, 0, TAU)
                rellena(ctx, CANICA[pasaron], 5)
                for m in range(2):
                    gotita(ctx, px - 10 + 20 * m, py + 60 + ((t * 4 + m * 0.5) % 1) * 60, 7)
            pinza(ctx, px, py, abre, arr, 0.95)
            ctx.restore()
            ctx.append_path(marco)
            trazo(ctx, INK, 7)
            # cartel con el nombre y el cronómetro
            nombre = "ARRUGADOS" if arr else "LISOS"
            txt = f"{nombre}   {tc:0.1f} s".replace(".", ",")
            cartel(ctx, txt, 540, yf + 245, 50, box=VERDE if fin else (AMARILLO if arr else BLANCO),
                   fg=BLANCO if fin else INK, s=pop(t, t0 + 0.3, 0.3))
            if fin:
                tilde(ctx, 870, yf + 245, 0.7 * pop(t, FIN_ARRUGADOS, 0.3))


# ------------------------------------------------------------------ 10. las arrugas sacan el agua / el neumático
YG = (540, 330, 620, 820)        # yema gigante: centro x, punta, ancho, alto


def vidrio(ctx, a=1.0):
    ctx.set_source_rgba(*VIDRIO, 0.04 * a)
    ctx.paint()
    for k, x in enumerate((140, 260, 820)):
        ctx.move_to(x, 300)
        ctx.line_to(x + 260, 1500)
        trazo(ctx, BLANCO, 26 if k != 1 else 12, 0.12 * a)


def d_drena(ctx, t):
    t0 = b(14)
    fondo(ctx, t)
    deriva(ctx, t, t0, T_COMO14, 0.05)
    cx, top, Wp, Hp = YG
    dr = prog(t, T_SACAN - 0.15, T_COMO14 - T_SACAN + 0.1, "inout")
    yema_grande(ctx, cx, top, Wp, Hp, t, wr=1.0, agua=1 - dr, drena=dr, palido=0.2)
    # el agua que sale por los bordes
    r = np.random.default_rng(31)
    for k in range(16):
        a_ = r.uniform(math.pi * 0.95, math.pi * 2.05)
        f = clamp((t - T_SACAN - r.uniform(0, 0.7)) / 0.5)
        if 0 < f < 1:
            rr = Wp * 0.52 + 260 * f
            gotita(ctx, cx + rr * math.cos(a_), top + Wp * 0.5 + rr * 1.2 * math.sin(a_) + 300, 14, 1 - f)
    vidrio(ctx)


def d_neumatico(ctx, t):
    t0 = T_COMO14
    fondo(ctx, t)
    deriva(ctx, t, t0, b(15), 0.06, 540, 1000)
    cx, cy, R = 540, 940, 300
    ys = cy + R
    vel = 900
    # ruta mojada que pasa
    ctx.rectangle(-100, ys, 1300, 260)
    ctx.set_source_rgb(*ASFALTO)
    ctx.fill()
    for k in range(-1, 8):
        x = (k * 200 - (t * vel) % 200)
        ctx.rectangle(x, ys + 120, 110, 16)
        ctx.set_source_rgba(1, 1, 1, 0.75)
        ctx.fill()
    ctx.rectangle(-100, ys - 6, 1300, 26)
    ctx.set_source_rgba(*AGUA, 0.6)
    ctx.fill()
    for k in range(-1, 12):
        x = k * 110 - (t * vel) % 110
        elipse(ctx, x, ys + 6, 34, 5)
        trazo(ctx, BLANCO, 3, 0.6)
    ctx.move_to(-100, ys)
    ctx.line_to(1300, ys)
    trazo(ctx, INK, 7)
    # chorros de agua que salen de las ranuras
    r = np.random.default_rng(41)
    for k in range(40):
        ph = r.uniform(0, 1)
        q = (t * 1.6 + ph) % 1
        lado = -1 if k % 3 else 1
        x = cx + lado * (40 + 460 * q) * (1 if lado > 0 else 1.2)
        y = ys - 10 - 330 * q * (1 - q) * r.uniform(0.6, 1.4)
        gotita(ctx, x, y, r.uniform(8, 16), 1 - q)
    # neumático
    ang = -t * vel / R
    ctx.arc(cx, cy, R, 0, TAU)
    rellena(ctx, GOMA, 9)
    glow = prog(t, T_RANURAS - 0.05, 0.2) * (1 - prog(t, T_RANURAS + 0.7, 0.3))
    n = 26
    for k in range(n):
        a_ = ang + k * TAU / n
        for rr0, rr1, w in ((R - 6, R - 52, 15),):
            ctx.move_to(cx + rr0 * math.cos(a_), cy + rr0 * math.sin(a_))
            ctx.line_to(cx + rr1 * math.cos(a_ + 0.05), cy + rr1 * math.sin(a_ + 0.05))
            trazo(ctx, hx("#151821"), w)
            if glow > 0.01:
                ctx.move_to(cx + rr0 * math.cos(a_), cy + rr0 * math.sin(a_))
                ctx.line_to(cx + rr1 * math.cos(a_ + 0.05), cy + rr1 * math.sin(a_ + 0.05))
                trazo(ctx, AMARILLO, w * 0.6, glow)
    ctx.arc(cx, cy, R - 70, 0, TAU)
    rellena(ctx, GOMA2, 6)
    ctx.arc(cx, cy, R - 118, 0, TAU)
    rellena(ctx, hx("#C9D1DE"), 7)
    for k in range(5):
        a_ = ang + k * TAU / 5
        ctx.arc(cx + 70 * math.cos(a_), cy + 70 * math.sin(a_), 16, 0, TAU)
        rellena(ctx, hx("#8C95A8"), 5)
    ctx.arc(cx, cy, 34, 0, TAU)
    rellena(ctx, hx("#8C95A8"), 6)
    ctx.arc(cx - R * 0.35, cy - R * 0.35, R * 0.55, math.radians(190), math.radians(260))
    trazo(ctx, BLANCO, 10, 0.25)
    for k in range(4):
        ctx.move_to(cx - R - 60 - 50 * k, cy - 120 + 80 * k)
        ctx.line_to(cx - R - 160 - 50 * k, cy - 120 + 80 * k)
        trazo(ctx, BLANCO, 8, 0.35)
    kartel(ctx, "RANURAS", 540, 520, 64, t, T_RANURAS - 0.05, rot=-3)


# ------------------------------------------------------------------ 11. donde agarras y donde pisas
def pie_costado(ctx, x, y, s, glow=0.0):
    """Pie derecho de costado (los dedos a la derecha); (x, y) = debajo del talón."""
    with en(ctx, x, y, s):
        ctx.move_to(-70, -330)
        ctx.line_to(-80, -120)
        ctx.curve_to(-120, -90, -120, -10, -80, 0)
        ctx.line_to(170, 0)
        ctx.curve_to(215, 0, 225, -40, 195, -58)
        ctx.curve_to(150, -80, 90, -95, 40, -140)
        ctx.line_to(40, -330)
        ctx.close_path()
        rellena(ctx, PIEL, 7)
        for k in range(3):
            ctx.arc(150 - 22 * k, -46 + 4 * k, 14, math.radians(200), math.radians(330))
            trazo(ctx, PIEL2, 4)
        if glow > 0.01:
            brillo(ctx, 165, -6, 80, AMARILLO, glow)
        ctx.move_to(-100, -1000)
        ctx.line_to(-96, -300)
        ctx.curve_to(-40, -285, 20, -285, 62, -300)
        ctx.line_to(66, -1000)
        ctx.close_path()
        rellena(ctx, hx(kit.P["pantalon"]), 7)


def d_agarre(ctx, t):
    t0 = b(15)
    fondo(ctx, t)
    deriva(ctx, t, t0, b(16), 0.09)
    # arriba: el vaso mojado, agarrado por una mano que viene de la izquierda
    y0p, y1p = PANELES["arriba"]
    ap = pop(t, t0, 0.3)
    with en(ctx, 540, (y0p + y1p) / 2, ap):
        ctx.translate(-540, -(y0p + y1p) / 2)
        marco = panel(ctx, y0p, y1p)
    ctx.save()
    ctx.append_path(marco)
    ctx.clip()
    vx, vy, vs = 650, 625, 1.2
    cierra = prog(t, T_AGARRAS - 0.35, 0.4, "out")
    lleg = ease(clamp((t - t0) / 0.5), "out")
    hxm = lerp(-200, 0, lleg)
    with alfa(ctx, 0.85):
        with en(ctx, vx - 40 + hxm, vy - 95, 1.0, -0.35):
            rrect(ctx, -60, -26, 150, 52, 26)
            rellena(ctx, PIEL2, 7)
    K.vaso(ctx, vx, vy, vs, 0, AGUA, nivel=0.7)
    r = np.random.default_rng(51)
    for k in range(7):
        gx = vx + r.uniform(-80, 80) * vs
        gy = vy - 110 * vs + ((t * 0.25 + r.uniform(0, 1)) % 1) * 220 * vs
        gotita(ctx, gx, gy, 9)
    with en(ctx, vx - 215 + hxm, vy + 30, 1.0, 1.35):
        rrect(ctx, -70, 40, 140, 700, 60)
        rellena(ctx, PIEL, 7)
    with en(ctx, vx - 215 + hxm, vy + 10, 1.0):
        elipse(ctx, 0, 0, 110, 140)
        rellena(ctx, PIEL, 7)
        ctx.move_to(-40, 90)
        ctx.curve_to(-10, 110, 30, 110, 60, 90)
        trazo(ctx, PIEL2, 5)
    for k in range(4):
        yy = vy - 105 + 64 * k
        L = lerp(70, 250 - 16 * abs(k - 1.3), cierra)
        x0 = vx - 200 + hxm
        rrect(ctx, x0, yy - 27, L + 26, 54, 27)
        rellena(ctx, PIEL, 7)
        ctx.move_to(x0 + L * 0.55, yy - 20)
        ctx.curve_to(x0 + L * 0.55 + 6, yy - 6, x0 + L * 0.55 + 6, yy + 6, x0 + L * 0.55, yy + 20)
        trazo(ctx, PIEL2, 4)
        if cierra > 0.3:
            # la uña (la yema está apoyada contra el vidrio)
            rrect(ctx, x0 + L - 20, yy - 16, 34, 32, 12)
            rellena(ctx, UNA, 4)
        if cierra > 0.95:
            g = 0.75 + 0.2 * math.sin(t * 9 + k)
            brillo(ctx, x0 + L + 16, yy, 56, AMARILLO, g * prog(t, T_AGARRAS, 0.2))
    if cierra > 0.95:
        for k in range(6):
            q = prog(t, T_AGARRAS + 0.05 * k, 0.5)
            if 0 < q < 1:
                gotita(ctx, vx + 80 + 70 * q, vy - 100 + 36 * k + 30 * q, 10, 1 - q)
    ctx.restore()
    ctx.append_path(marco)
    trazo(ctx, INK, 7)
    # abajo: el pie que pisa el piso mojado
    y0p, y1p = PANELES["abajo"]
    ap = pop(t, t0 + 0.12, 0.3)
    with en(ctx, 540, (y0p + y1p) / 2, ap):
        ctx.translate(-540, -(y0p + y1p) / 2)
        marco = panel(ctx, y0p, y1p)
    ctx.save()
    ctx.append_path(marco)
    ctx.clip()
    ys = 1330
    ctx.rectangle(-50, ys, 1200, 200)
    ctx.set_source_rgb(*hx("#E9EEF9"))
    ctx.fill()
    for k in range(7):
        ctx.move_to(k * 180 - 20, ys)
        ctx.line_to(k * 180 - 80, ys + 200)
        trazo(ctx, hx("#C9D3EE"), 5)
    ctx.rectangle(-50, ys - 4, 1200, 16)
    ctx.set_source_rgba(*AGUA, 0.55)
    ctx.fill()
    ctx.move_to(-50, ys)
    ctx.line_to(1150, ys)
    trazo(ctx, INK, 7)
    baja = prog(t, T_PISAS - 0.3, 0.3, "in")
    flota = 22 * math.sin(t * 5) * (1 - baja)
    py = lerp(ys - 150, ys, baja) + flota
    pie_costado(ctx, 470, py, 0.9, glow=prog(t, T_PISAS, 0.2) * (0.8 + 0.2 * math.sin(t * 9)))
    q = prog(t, T_PISAS - 0.02, 0.45, "out")
    if 0 < q < 1:
        for k in range(10):
            a_ = math.pi + k * math.pi / 9
            rr = 60 + 220 * q
            gotita(ctx, 620 + rr * math.cos(a_) * 1.2, ys + rr * 0.6 * math.sin(a_), 12, 1 - q)
    ctx.restore()
    ctx.append_path(marco)
    trazo(ctx, INK, 7)


# ------------------------------------------------------------------ 12-15. la yema gigante: no es al azar
def d_raro(ctx, t):
    t0 = b(16)
    fondo(ctx, t, 0.35)
    s = lerp(0.3, 1.0, ease(clamp((t - t0) / 0.6), "out"))
    with en(ctx, 540, 900, s):
        ctx.translate(-540, -900)
        cx, top, Wp, Hp = YG
        yema_grande(ctx, cx, top, Wp, Hp, t, wr=1.0)


def d_azar(ctx, t):
    t0 = b(17)
    fondo(ctx, t, 0.35)
    deriva(ctx, t, t0, b(18), 0.04)
    cx, top, Wp, Hp = YG
    patron = PATRON_INDICE
    sh = 0.0
    if T_ARRUGAS17 + 0.1 <= t < T_AZAR + 0.05:
        k = int((t - T_ARRUGAS17) / 0.11)
        patron = patron_azar(100 + k)
        sh = 5 * math.sin(t * 60)
    ctx.translate(sh, 0)
    if t >= T_AZAR + 0.05:
        zoom(ctx, 1 + 0.04 * (1 - ease(clamp((t - T_AZAR - 0.05) / 0.3), "out")))
    yema_grande(ctx, cx, top, Wp, Hp, t, wr=1.0, patron=patron)


def foto_yema(ctx, x, y, s, rot, titulo, a=1.0):
    with alfa(ctx, a), en(ctx, x, y, s, rot):
        rrect(ctx, -330, -430, 660, 860, 26)
        rellena(ctx, BLANCO, 9)
        ctx.save()
        ctx.rectangle(-290, -390, 580, 680)
        ctx.clip()
        ctx.set_source_rgb(*hx("#2A3570"))
        ctx.paint()
        yema_grande(ctx, 0, -360, 470, 640, 0.0, wr=1.0)
        ctx.restore()
        ctx.rectangle(-290, -390, 580, 680)
        trazo(ctx, INK, 6)
        texto(ctx, titulo, 0, 358, 66, fill=INK, stroke=None)


def d_igual(ctx, t):
    t0 = b(18)
    fondo(ctx, t, 0.35)
    cx, top, Wp, Hp = YG
    vuelve = prog(t, T_SIGUIENDO - 0.2, 0.4, "inout")
    if vuelve < 1:
        # las dos fotos
        q1 = ease(clamp((t - t0) / 0.32), "inout")
        q2 = ease(clamp((t - T_SIEMPRE) / 0.3), "out")
        q3 = ease(clamp((t - T_IGUAL18) / 0.3), "inout")
        s_f = 0.6
        x1 = lerp(lerp(540, 300, q1), 540, q3)
        x2 = lerp(lerp(1400, 790, q2), 540, q3)
        y1 = lerp(lerp(900, 860, q1), 860, q3)
        with alfa(ctx, 1 - vuelve):
            if t < t0 + 0.32:
                # la yema gigante se achica hasta ser la foto
                pass
            foto_yema(ctx, x1, y1, lerp(1.0, s_f, q1), lerp(0, -0.06, q1) * (1 - q3), "BAÑO 1")
            if t >= T_SIEMPRE:
                foto_yema(ctx, x2, 860, s_f, 0.07 * (1 - q3), "BAÑO 2", a=lerp(1.0, 0.6, q3))
            if t > T_IGUAL18 + 0.3:
                a = pop(t, T_IGUAL18 + 0.3, 0.3)
                tilde(ctx, 540 + 170, 860 - 230, 1.1 * a)
                ctx.set_source_rgba(1, 1, 1, 0.5 * (1 - prog(t, T_IGUAL18 + 0.3, 0.3)))
                ctx.paint()
    if vuelve > 0:
        with alfa(ctx, vuelve):
            ctx.save()
            s = lerp(0.6, 1.0, vuelve)
            zoom(ctx, s, 540, 860)
            tr = prog(t, T_SIGUIENDO + 0.15, 0.5)
            yema_grande(ctx, cx, top, Wp, Hp, t, wr=1.0, trans=tr, glob=1.0)
            ctx.restore()
            if t > T_VASOS18:
                texto(ctx, "", 540, 400, 10)


def d_latente(ctx, t):
    t0 = b(19)
    fondo(ctx, t, 0.35)
    cx, top, Wp, Hp = YG
    alej = ease(clamp((t - (T_YEMA19 - 0.25)) / (b(20) - T_YEMA19 + 0.25)), "in")
    s = lerp(1.0, 0.5, alej)
    tip_y = top + Wp * 0.12 + 0.4 * (Hp - Wp * 0.12)
    zoom(ctx, s * (1 + 0.08 * ease(clamp((t - t0) / 1.8), "inout")), cx, tip_y)
    ctx.translate(540, 900)
    ctx.rotate(0.04 * math.sin((t - t0) * 1.6))
    ctx.translate(-540, -900)
    ctx.translate(0, (900 - tip_y) * alej)
    tr = 1 - prog(t, t0, 0.3)
    wr = 1 - prog(t, t0 + 0.15, 0.6)
    lat = prog(t, T_DIBUJO - 0.1, 0.5) * (0.75 + 0.25 * math.sin(t * 6))
    lat = max(lat, prog(t, T_AHI - 0.05, 0.15) * (1 - prog(t, T_AHI + 0.2, 0.4)) * 1.0)
    yema_grande(ctx, cx, top, Wp, Hp, t, wr=wr, trans=tr, glob=1.0, latente=lat, palido=wr)


# ------------------------------------------------------------------ escenas
ESCENAS = [
    (0.0, d_apertura),
    (b(3), d_esponja),
    (b(4), d_burbuja),
    (b(5), d_manos_pies),
    (b(6), d_gota),
    (b(7), d_nervios),
    (b(8), d_corte),
    (b(11), d_dano),
    (b(12), d_paraque),
    (b(13), d_experimento),
    (b(14), d_drena),
    (T_COMO14, d_neumatico),
    (b(15), d_agarre),
    (b(16), d_raro),
    (b(17), d_azar),
    (b(18), d_igual),
    (b(19), d_latente),
    (b(20), d_cierre),
]
XF = 0.18
SIN_PUNCH = {d_paraque, d_cierre, d_azar, d_esponja}


def punch(t, t0, d=0.3, amp=0.05):
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


def escena(t):
    return max(k for k, (t0, _) in enumerate(ESCENAS) if t >= t0)


def capa(ctx, fn, t):
    ctx.save()
    fn(ctx, t)
    ctx.restore()


def flotar(ctx, t):
    """Vaivén suave de cámara en todo el video (cierra justo en el loop)."""
    a, b_ = per(t, 4.6), per(t, 3.1)
    ctx.translate(540, 900)
    ctx.rotate(math.radians(0.45 * math.sin(a)))
    ctx.scale(1.012 + 0.008 * math.sin(b_), 1.012 + 0.008 * math.sin(b_))
    ctx.translate(-540 + 7 * math.sin(b_ + 1), -900 + 6 * math.cos(a))


def componer(ctx, t):
    flotar(ctx, t)
    i = escena(t)
    t0, fn = ESCENAS[i]
    dt = t - t0
    sin_punch = fn in SIN_PUNCH
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
    ctx.save()
    if i > 0 and not sin_punch:
        zoom(ctx, punch(t, t0))
    fn(ctx, t)
    ctx.restore()


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


# ------------------------------------------------------------------ sonido (golpes cortos, por debajo de la voz)
def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    ev(0.02, "plop", 0.3)
    for k in range(5):
        ev(T_ARRUGAN0 + 0.09 * k, "tick", 0.16, f=900 + 90 * k, d=0.04)
    ev(T_LISO - 0.05, "ding", 0.25)
    ev(T_POR2 + 0.05, "pop", 0.4)
    ev(T_ARRUGAN2 - 0.05, "pop", 0.3)
    ev(b(3) - 0.35, "whoosh_suave", 0.35)
    for lado, y0, dt in GOTAS_E:
        ev(T_PIEL3 + dt + 0.5, "plop", 0.14)
    ev(T_ESPONJA - 0.1, "pop", 0.4)
    for k in range(3):
        ev(b(4) + 0.06 * k, "pop", 0.18)
    ev(b(4) + 0.12, "pop", 0.35)
    for k in range(6):
        ev(T_ARRUGARIA + 0.2 * k, "tick", 0.12, f=600 + 60 * k, d=0.04)
    ev(T_CUERPO - 0.05, "boing", 0.3)
    ev(b(5), "pop", 0.45)
    ev(b(5) + 0.22, "pop", 0.3)
    ev(T_MANOS - 0.08, "ding", 0.3)
    ev(T_PIES - 0.08, "ding", 0.3)
    ev(b(6) + 0.2, "plop", 0.4)
    ev(T_AGUA6 - 0.04, "golpe", 0.5)
    ev(T_AGUA6 + 0.12, "whoosh_suave", 0.3)
    ev(T_ORDEN, "zap", 0.35)
    ev(T_NERVIOS + 0.05, "chispa", 0.3)
    ev(b(8) - 0.3, "whoosh_suave", 0.3)
    ev(T_VASOS8 - 0.05, "pop", 0.3)
    ev(T_ACHICAN - 0.05, "clunk", 0.4)
    ev(T_GLOBO - 0.55, "pop", 0.35)
    ev(T_GLOBO - 0.2, "siseo", 0.25)
    ev(T_PLIEGA - 0.15, "tick", 0.2, f=500, d=0.06)
    ev(T_PLIEGA, "tick", 0.2, f=420, d=0.06)
    ev(T_NERVIO11, "pop", 0.25)
    ev(T_DANADO - 0.05, "zap", 0.4)
    ev(T_ESE - 0.05, "whoosh_suave", 0.25)
    for k in range(4):
        ev(T_ESE + 0.4 + 0.05 * k, "tick", 0.16, f=900 + 80 * k, d=0.04)
    ev(T_NO11 - 0.1, "clic", 0.4)
    ev(b(12) - 0.02, "boing", 0.45)
    ev(b(13) + 0.15, "pop", 0.3)
    ev(b(13) + 0.3, "pop", 0.3)
    for fila in FILAS:
        for k in range(6):
            tk = INICIO_EXP + CICLO[fila] * (k + 0.3)
            if tk < b(14):
                ev(tk, "clic", 0.16)
    for k in RESBALA:
        tk = INICIO_EXP + CICLO["lisos"] * (k + 0.8)
        if tk < b(14):
            ev(tk, "plop", 0.35)
    ev(FIN_ARRUGADOS, "ding", 0.35)
    ev(T_SACAN - 0.1, "plop", 0.3)
    ev(T_COMO14 - 0.1, "whoosh", 0.3)
    ev(T_RANURAS - 0.05, "pop", 0.35)
    ev(T_AGARRAS - 0.05, "clic", 0.4)
    ev(T_PISAS - 0.02, "plop", 0.5)
    ev(b(16), "whoosh", 0.35)
    for k in range(int((T_AZAR - T_ARRUGAS17) / 0.11)):
        ev(T_ARRUGAS17 + 0.1 + 0.11 * k, "tick", 0.1, f=1000 + 40 * k, d=0.03)
    ev(T_AZAR + 0.05, "golpe", 0.4)
    ev(b(18) + 0.05, "whoosh_suave", 0.25)
    ev(T_SIEMPRE, "whoosh_suave", 0.25)
    ev(T_IGUAL18 + 0.3, "ding", 0.4)
    ev(T_SIGUIENDO + 0.15, "pop", 0.25)
    ev(T_DIBUJO - 0.1, "ding", 0.25)
    ev(T_YEMA19 - 0.2, "whoosh_suave", 0.3)
    ev(TOTAL - 0.35, "plop", 0.25)
    return E


def pista_efectos():
    n = int((TOTAL + 3) * SR)
    mix = np.zeros(n, np.float32)
    for t, k, v, kw in eventos():
        x = K.sonido_picante(k, **kw) * v
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "por_que_solo_se_arrugan_los_dedos.mp4"))
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

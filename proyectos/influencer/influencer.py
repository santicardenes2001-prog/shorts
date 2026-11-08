"""Short "¿Puedo ser influencer?" — animación procedural, mismo estilo que pantalla/picante/pulmones.

Gancho con un celular visto en primera persona y un pulgar a punto de deslizar. Después, el mercado de la
atención con datos (Shorts por día, horas en redes, jóvenes que quieren ser influencers) y los números reales
del canal: el lote de prueba de ~1.200 vistas, el Short del océano (se frenó) y el del agua (siguió creciendo).
Cierra con el mosaico de los Shorts del canal y el botón SUBIR. Sin pregunta ni animación de suscripción, y con
una cola mínima para que el loop arranque enseguida (ver PAUTAS: reglas medidas el 7/11).

    python proyectos/influencer/influencer.py --fotos 1,5.5,14
    python proyectos/influencer/influencer.py            # render completo -> salidas/puedo_ser_influencer.mp4
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
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "proyectos", "pantalla"))
sys.path.insert(0, os.path.join(ROOT, "proyectos", "picante"))
import kit  # noqa: E402
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, bump, cartel, clamp, ease, fuente, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rng, rrect, texto)
from picante import _elipse_suave, capa, fondo_azul  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
UI = "Inter"

NARRACION = [
    "¿Alguna vez te preguntaste: puedo ser influencer?",                    # b0
    "Ahora mismo estás en la prueba.",                                      # b1
    "Tu pulgar está decidiendo si deslizas este video.",                    # b2
    "Esa decisión es lo que se vende en internet.",                         # b3
    "Se llama atención.",                                                   # b4
    "Cada día se miran más de 200.000 millones de Shorts.",                 # b5
    "Y pasamos más de dos horas por día en redes.",                         # b6
    "Más de la mitad de los jóvenes sería influencer si pudiera.",          # b7
    "Pero, ¿qué hace falta de verdad?",                                     # b8
    "Te lo muestro con los números de este canal.",                         # b9
    "Tiene tres semanas.",                                                  # b10
    "Cada video nuevo junta unas 1.200 vistas en pocas horas.",             # b11
    "Casi ninguna es de alguien suscrito.",                                 # b12
    "YouTube se lo muestra a desconocidos, y mira qué hacen.",              # b13
    "Si deslizan, el video se frena ahí.",                                  # b14
    "Mira estos dos.",                                                      # b15
    "Uno, sobre animales del fondo del mar que parecen extraterrestres.",   # b16
    "Lo deslizó casi la mitad.",                                            # b17
    "Y se frenó en 1.600 vistas.",                                          # b18
    "Otro, sobre por qué la Tierra tiene tanta agua.",                      # b19
    "Ahí se quedó a mirar el 83%.",                                         # b20
    "Siguió creciendo y pasó las 6.000.",                                   # b21
    "Pero el número más importante es otro.",                               # b22
    "Sus videos ya suman más de 35.000 vistas.",                            # b23
    "Ninguna existiría sin animarse a subir el primero.",                   # b24
    "La respuesta es simple: crea algo que te motive, y súbelo.",           # b25
]
WORDS = motor.align_times([{"texto": t} for t in NARRACION],
                          json.load(open(os.path.join(AQUI, "audio", "palabras.json"))))
COLA = 0.25                     # casi sin hueco: el loop vuelve a empezar enseguida
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
ROJO = hx("#FF3B2F")
VERDE = hx("#2BD45A")
CIAN = P.CIAN
AZUL_AGUA = hx("#5EC8FF")
ROSA = hx("#FF5FA2")
VIOLETA = hx("#8B5CF6")
GRIS = hx("#5A6378")
GRIS_CLARO = hx("#AEB6C8")
NAVY = hx("#121A33")

# ------------------------------------------------------------------ tiempos clave
T_INF = b(0, "influencer")
T_AHORA = b(1)
T_PRUEBA = b(1, "prueba")
T_PULGAR = b(2, "pulgar")
T_DESL = b(2, "deslizas")
T_VENDE = b(3, "vende")
T_INTERNET = b(3, "internet")
T_ATEN = b(4, "atencion")
T_200 = b(5, "200.000")
T_SHORTS = b(5, "shorts")
T_DOSH = b(6, "dos")
T_REDES = b(6, "redes")
T_MITAD = b(7, "mitad")
T_INFL2 = b(7, "influencer")
T_FALTA = b(8, "falta")
T_NUMEROS = b(9, "numeros")
T_SEM = b(10, "semanas")
T_JUNTA = b(11, "junta")
T_1200 = b(11, "1.200")
T_HORAS2 = b(11, "horas")
T_NING = b(12, "ninguna")
T_SUSC = b(12, "suscrito")
T_YT = b(13)
T_DESC = b(13, "desconocidos")
T_MIRA = b(13, "mira")
T_SID = b(14)
T_FRENA = b(14, "frena")
T_DOS = b(15)
T_UNO = b(16)
T_EXTRA = b(16, "extraterrestres")
T_DESL2 = b(17, "deslizo")
T_MITAD2 = b(17, "mitad")
T_FRENO = b(18, "freno")
T_1600 = b(18, "1.600")
T_OTRO = b(19)
T_AGUA = b(19, "agua")
T_QUEDO = b(20, "quedo")
T_83 = b(20, "83")
T_SIGUIO = b(21)
T_6000 = b(21, "6.000")
T_PERO = b(22)
T_IMPORT = b(22, "importante")
T_SUS = b(23)
T_35 = b(23, "35.000")
T_NINGUNA = b(24)
T_SUBIR = b(24, "subir")
T_PRIMERO = b(24, "primero")
T_RESP = b(25)
T_CREA = b(25, "crea")
T_MOTIVE = b(25, "motive")
T_SUBELO = b(25, "subelo")


# ------------------------------------------------------------------ ayudas
def fmt(v):
    return f"{int(round(v)):,}".replace(",", ".")


def contar(t, t0, t1, v1, v0=0.0):
    return lerp(v0, v1, prog(t, t0, max(t1 - t0, 0.05), "out"))


def sale(t, t1, d=0.2):
    return 1 - prog(t, t1, d, "in")


def nota(ctx, txt, x, y, size=30, alpha=0.8, ax=0.5):
    """Fuente de un dato: texto chico, sin caja."""
    texto(ctx, txt, x, y, size, fill=hx("#C9D3EA"), stroke=None, fam=UI, ax=ax, alpha=alpha)


def fondo(ctx, t):
    fondo_azul(ctx, t)


def sombra_suave(ctx, x, y, w, h, a=0.45):
    _elipse_suave(ctx, x, y, w, h, (0, 0, 0), a)


def punch(t, t0, d=0.3, amp=0.07):
    """Pequeño empujón de cámara al empezar una escena."""
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


# ------------------------------------------------------------------ Vos
@functools.lru_cache(maxsize=None)
def vos_surface(pose):
    kw = dict(kit.VOS_VARIANTS[pose])
    body = kit.vos(**kw)
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


# ------------------------------------------------------------------ íconos y miniaturas
def corazon(ctx, x, y, r, col=BLANCO):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(r / 50, r / 50)
    ctx.move_to(0, 38)
    ctx.curve_to(-60, -6, -36, -58, 0, -26)
    ctx.curve_to(36, -58, 60, -6, 0, 38)
    ctx.close_path()
    ctx.restore()
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()


def burbuja(ctx, x, y, r, col=BLANCO):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(r / 50, r / 50)
    rrect(ctx, -46, -38, 92, 66, 26)
    ctx.move_to(-16, 26)
    ctx.line_to(-30, 48)
    ctx.line_to(4, 28)
    ctx.restore()
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()


def compartir(ctx, x, y, r, col=BLANCO):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(r / 50, r / 50)
    ctx.move_to(-40, 34)
    ctx.curve_to(-38, -6, -6, -18, 10, -18)
    ctx.line_to(10, -42)
    ctx.line_to(46, -4)
    ctx.line_to(10, 32)
    ctx.line_to(10, 8)
    ctx.curve_to(-14, 8, -32, 16, -40, 34)
    ctx.close_path()
    ctx.restore()
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()


def play(ctx, x, y, r, a=1.0):
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source_rgba(0, 0, 0, 0.35 * a)
    ctx.fill()
    ctx.move_to(x - r * 0.32, y - r * 0.48)
    ctx.line_to(x + r * 0.52, y)
    ctx.line_to(x - r * 0.32, y + r * 0.48)
    ctx.close_path()
    ctx.set_source_rgba(1, 1, 1, 0.9 * a)
    ctx.fill()


def estrellas(ctx, w, h, n, seed, t, a=1.0):
    r = rng(seed)
    for _ in range(n):
        x, y, s, ph = r.uniform(0, w), r.uniform(0, h), r.uniform(1.5, 4), r.uniform(0, 6)
        ctx.arc(x, y, s, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, a * (0.45 + 0.4 * math.sin(t * 2 + ph)))
        ctx.fill()


def mini_oceano(ctx, w, h, t):
    g = cairo.LinearGradient(0, 0, 0, h)
    g.add_color_stop_rgb(0, *hx("#0E4C7A"))
    g.add_color_stop_rgb(1, *hx("#020D1C"))
    ctx.rectangle(0, 0, w, h)
    ctx.set_source(g)
    ctx.fill()
    r = rng(5)
    for _ in range(26):
        x, y0, s = r.uniform(0, w), r.uniform(0, h), r.uniform(2, 5)
        y = (y0 + t * 25) % h
        ctx.arc(x, y, s, 0, 2 * math.pi)
        ctx.set_source_rgba(0.8, 0.9, 1, 0.35)
        ctx.fill()
    # pez abisal con su señuelo de luz
    cx, cy, k = w * 0.5, h * 0.52, w / 300
    lx, ly = cx + 70 * k, cy - 120 * k + 6 * k * math.sin(t * 3)
    _elipse_suave(ctx, lx, ly, 90 * k, 90 * k, CIAN, 0.55)
    ctx.move_to(cx + 10 * k, cy - 50 * k)
    ctx.curve_to(cx + 30 * k, cy - 150 * k, lx - 40 * k, ly - 40 * k, lx, ly)
    ctx.set_source_rgb(*hx("#1C2840"))
    ctx.set_line_width(7 * k)
    ctx.stroke()
    ctx.arc(lx, ly, 13 * k, 0, 2 * math.pi)
    ctx.set_source_rgb(*hx("#BFFBFF"))
    ctx.fill()
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(k, k)
    ctx.move_to(-110, 0)
    ctx.curve_to(-110, -70, 40, -90, 95, -20)
    ctx.line_to(60, 8)
    ctx.line_to(100, 30)
    ctx.curve_to(40, 90, -110, 70, -110, 0)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#34446B"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    for i in range(5):                       # dientes
        xx = 58 + i * 8
        ctx.move_to(xx - 4, 4 + i * 2)
        ctx.line_to(xx, 18 + i * 2)
        ctx.line_to(xx + 4, 6 + i * 2)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
    ctx.move_to(-110, 0)                     # cola
    ctx.line_to(-160, -40)
    ctx.line_to(-150, 0)
    ctx.line_to(-160, 40)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#2A3858"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.arc(35, -28, 13, 0, 2 * math.pi)     # ojo
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.arc(38, -28, 5, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


def mini_agua(ctx, w, h, t):
    g = cairo.LinearGradient(0, 0, 0, h)
    g.add_color_stop_rgb(0, *hx("#0B1030"))
    g.add_color_stop_rgb(1, *hx("#040616"))
    ctx.rectangle(0, 0, w, h)
    ctx.set_source(g)
    ctx.fill()
    estrellas(ctx, w, h, 40, 9, t)
    k = w / 300
    cx, cy, r = w * 0.5, h * 0.58, 105 * k
    _elipse_suave(ctx, cx, cy, r * 1.5, r * 1.5, AZUL_AGUA, 0.3)
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.set_source_rgb(*hx("#2F7FE6"))
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    for (dx, dy, rx, ry) in ((-40, -30, 50, 34), (40, 40, 44, 30), (-10, 60, 30, 18), (60, -50, 26, 18)):
        ctx.save()
        ctx.translate(cx + dx * k + 10 * math.sin(t * 0.6) * k, cy + dy * k)
        ctx.scale(rx * k, ry * k)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*hx("#3FBF62"))
        ctx.fill()
    ctx.restore()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6 * k)
    ctx.stroke()
    # gota con signo de pregunta
    gx, gy = cx + 85 * k, cy - 140 * k + 5 * k * math.sin(t * 2.5)
    K.gota(ctx, gx, gy, 46 * k, AZUL_AGUA)
    texto(ctx, "?", gx, gy + 6 * k, 48 * k, fill=BLANCO, stroke=INK, sw=4 * k)


def mini_nuevo(ctx, w, h, t):
    g = cairo.LinearGradient(0, 0, w, h)
    g.add_color_stop_rgb(0, *hx("#3B2A7A"))
    g.add_color_stop_rgb(1, *hx("#151A3A"))
    ctx.rectangle(0, 0, w, h)
    ctx.set_source(g)
    ctx.fill()
    play(ctx, w / 2, h * 0.45, w * 0.18)


ICONOS = {}


def icono(nombre):
    def deco(fn):
        ICONOS[nombre] = fn
        return fn
    return deco


@icono("insecto")
def _i_insecto(ctx, x, y, k):
    ctx.set_line_width(5 * k)
    for s in (-1, 1):
        for dy in (-18, 0, 18):
            ctx.move_to(x, y + dy * k)
            ctx.line_to(x + s * 46 * k, y + (dy - 14) * k)
            ctx.set_source_rgb(*INK)
            ctx.stroke()
    for (dy, r) in ((-30, 14), (0, 22), (34, 18)):
        ctx.arc(x, y + dy * k, r * k, 0, 2 * math.pi)
        ctx.set_source_rgb(*hx("#8B5A2B"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.stroke()


@icono("diamante")
def _i_diamante(ctx, x, y, k):
    pts = [(-40, -14), (-22, -38), (22, -38), (40, -14), (0, 40)]
    ctx.move_to(x + pts[0][0] * k, y + pts[0][1] * k)
    for px, py in pts[1:]:
        ctx.line_to(x + px * k, y + py * k)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#9FE8FF"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5 * k)
    ctx.stroke()
    ctx.move_to(x - 40 * k, y - 14 * k)
    ctx.line_to(x + 40 * k, y - 14 * k)
    ctx.stroke()


@icono("planta")
def _i_planta(ctx, x, y, k):
    ctx.move_to(x, y + 40 * k)
    ctx.line_to(x, y - 30 * k)
    ctx.set_source_rgb(*hx("#2E8B3E"))
    ctx.set_line_width(7 * k)
    ctx.stroke()
    for s, dy in ((-1, 0), (1, -16)):
        ctx.save()
        ctx.translate(x + s * 22 * k, y + dy * k)
        ctx.rotate(s * 0.6)
        ctx.scale(26 * k, 12 * k)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*hx("#3FBF62"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(4 * k)
        ctx.stroke()


@icono("cadena")
def _i_cadena(ctx, x, y, k):
    for i in range(3):
        ctx.save()
        ctx.translate(x - 30 * k + i * 30 * k, y + (i % 2) * 6 * k)
        ctx.rotate(0.5 if i % 2 else -0.5)
        ctx.scale(20 * k, 12 * k)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*GRIS_CLARO)
        ctx.set_line_width(8 * k)
        ctx.stroke()


@icono("pez")
def _i_pez(ctx, x, y, k):
    _elipse_suave(ctx, x + 28 * k, y - 34 * k, 22 * k, 22 * k, CIAN, 0.8)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(k * 0.38, k * 0.38)
    ctx.move_to(-110, 0)
    ctx.curve_to(-110, -70, 40, -90, 95, -20)
    ctx.line_to(60, 8)
    ctx.line_to(100, 30)
    ctx.curve_to(40, 90, -110, 70, -110, 0)
    ctx.close_path()
    ctx.restore()
    ctx.set_source_rgb(*hx("#34446B"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(4 * k)
    ctx.stroke()


@icono("ave")
def _i_ave(ctx, x, y, k):
    ctx.arc(x, y + 6 * k, 30 * k, 0, 2 * math.pi)
    ctx.set_source_rgb(*hx("#9AA7B8"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5 * k)
    ctx.stroke()
    ctx.move_to(x + 24 * k, y - 4 * k)
    ctx.line_to(x + 60 * k, y + 8 * k)
    ctx.line_to(x + 24 * k, y + 18 * k)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#E2C07A"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.arc(x + 8 * k, y - 4 * k, 5 * k, 0, 2 * math.pi)
    ctx.fill()


@icono("risa")
def _i_risa(ctx, x, y, k):
    ctx.arc(x, y, 36 * k, 0, 2 * math.pi)
    ctx.set_source_rgb(*AMARILLO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5 * k)
    ctx.stroke()
    K.carita(ctx, x, y - 6 * k, 26 * k, 0.55 * k, ojos="happy", boca="open_smile")


@icono("tierra")
def _i_tierra(ctx, x, y, k):
    ctx.arc(x, y, 34 * k, 0, 2 * math.pi)
    ctx.set_source_rgb(*hx("#2F7FE6"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5 * k)
    ctx.stroke()
    K.gota(ctx, x + 30 * k, y - 34 * k, 16 * k, AZUL_AGUA)


@icono("celular")
def _i_celular(ctx, x, y, k):
    rrect(ctx, x - 24 * k, y - 42 * k, 48 * k, 84 * k, 10 * k)
    ctx.set_source_rgb(*hx("#121418"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5 * k)
    ctx.stroke()
    rrect(ctx, x - 18 * k, y - 34 * k, 36 * k, 66 * k, 6 * k)
    ctx.set_source_rgb(*hx("#FFB347"))
    ctx.fill()


@icono("aji")
def _i_aji(ctx, x, y, k):
    K.aji(ctx, x, y, s=0.32 * k, rot=-20)


@icono("pulmones")
def _i_pulmones(ctx, x, y, k):
    for s in (-1, 1):
        ctx.save()
        ctx.translate(x + s * 18 * k, y + 6 * k)
        ctx.scale(16 * k, 32 * k)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*hx("#FF8FA3"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5 * k)
        ctx.stroke()
    ctx.move_to(x, y - 40 * k)
    ctx.line_to(x, y - 6 * k)
    ctx.set_line_width(7 * k)
    ctx.stroke()


@icono("camara")
def _i_camara(ctx, x, y, k):
    rrect(ctx, x - 40 * k, y - 24 * k, 80 * k, 54 * k, 10 * k)
    ctx.set_source_rgb(*hx("#3A3F4B"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5 * k)
    ctx.stroke()
    ctx.arc(x, y + 3 * k, 17 * k, 0, 2 * math.pi)
    ctx.set_source_rgb(*hx("#7CC4FF"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()


@icono("mas")
def _i_mas(ctx, x, y, k):
    for (dx, dy, w, h) in ((-8, -36, 16, 72), (-36, -8, 72, 16)):
        rrect(ctx, x + dx * k, y + dy * k, w * k, h * k, 6 * k)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()


# (etiqueta, color de fondo, ícono) — los 14 Shorts del canal sin el de pelotitas, en orden de publicación
MOSAICO = [("INSECTOS", "#7A4A1E", "insecto"), ("DIAMANTE", "#3B2A7A", "diamante"), ("PLANTA", "#1F5E33", "planta"),
           ("TORTURAS", "#4A2626", "cadena"), ("OCÉANO", "#0E3C66", "pez"), ("AVES", "#2E5E2E", "ave"),
           ("MEMES", "#6B5A12", "risa"), ("TORTURAS 2", "#4A2626", "cadena"), ("TORTURAS 3", "#4A2626", "cadena"),
           ("AGUA", "#0B1030", "tierra"), ("PANTALLA", "#5A3A10", "celular"), ("PICANTE", "#6B1A14", "aji"),
           ("PULMONES", "#5A2440", "pulmones"), ("CÁMARAS", "#2A3040", "camara")]


def tarjeta(ctx, x, y, w, t, mini=None, titulo=None, alpha=1.0, s=1.0, borde=INK, brillo=0.0, gris=0.0,
            titulo_size=None, badge=None):
    """Tarjeta de un Short (9:16) centrada en (x, y) con ancho w."""
    if alpha <= 0.01 or s <= 0.01:
        return
    h = w * 16 / 9
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.push_group()
    if brillo > 0:
        _elipse_suave(ctx, 0, 0, w * 0.9, h * 0.7, AMARILLO, 0.5 * brillo)
    rrect(ctx, -w / 2 + 6, -h / 2 + 12, w, h, 26)
    ctx.set_source_rgba(0, 0, 0, 0.45)
    ctx.fill()
    ctx.save()
    rrect(ctx, -w / 2, -h / 2, w, h, 26)
    ctx.clip()
    ctx.translate(-w / 2, -h / 2)
    if mini:
        mini(ctx, w, h, t)
    if titulo:
        g = cairo.LinearGradient(0, h * 0.55, 0, h)
        g.add_color_stop_rgba(0, 0, 0, 0, 0)
        g.add_color_stop_rgba(1, 0, 0, 0, 0.8)
        ctx.rectangle(0, h * 0.55, w, h * 0.45)
        ctx.set_source(g)
        ctx.fill()
        lines = titulo.split("\n")
        ts = titulo_size or w * 0.105
        for i, l in enumerate(lines):
            texto(ctx, l, w / 2, h * 0.86 - (len(lines) - 1 - i) * ts * 1.05, ts, fill=BLANCO, stroke=INK,
                  sw=ts * 0.12)
    if gris > 0:
        ctx.rectangle(0, 0, w, h)
        ctx.set_source_rgba(0.12, 0.13, 0.16, 0.72 * gris)
        ctx.fill()
    ctx.restore()
    rrect(ctx, -w / 2, -h / 2, w, h, 26)
    ctx.set_source_rgb(*borde)
    ctx.set_line_width(7)
    ctx.stroke()
    if badge:
        cartel(ctx, badge, 0, -h / 2 + 4, w * 0.13, box=AMARILLO, s=1.0, rot=-4, pad=(20, 10), r=18, borde=5,
               sombra=6)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def mini_mosaico(i):
    lab, col, ic = MOSAICO[i]

    def f(ctx, w, h, t):
        g = cairo.LinearGradient(0, 0, 0, h)
        c = hx(col)
        g.add_color_stop_rgb(0, *[min(1, v * 1.5) for v in c])
        g.add_color_stop_rgb(1, *[v * 0.6 for v in c])
        ctx.rectangle(0, 0, w, h)
        ctx.set_source(g)
        ctx.fill()
        ICONOS[ic](ctx, w / 2, h * 0.4, w / 150)
        texto(ctx, lab, w / 2, h * 0.8, w * 0.13 if len(lab) < 9 else w * 0.11, fill=BLANCO, stroke=INK,
              sw=w * 0.018)
    return f


def barra(ctx, x, y, w, h, frac, col, etiqueta, valor, alpha=1.0, s=1.0):
    """Barra horizontal con etiqueta arriba y valor a la derecha."""
    if alpha <= 0.01 or s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.push_group()
    texto(ctx, etiqueta, -w / 2, -h / 2 - 38, 50, ax=0.0)
    rrect(ctx, -w / 2, -h / 2, w, h, h / 2)
    ctx.set_source_rgb(*hx("#1A2240"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    if frac > 0.003:
        rrect(ctx, -w / 2 + 6, -h / 2 + 6, max(h - 12, (w - 12) * frac), h - 12, (h - 12) / 2)
        ctx.set_source_rgb(*col)
        ctx.fill()
    texto(ctx, valor, w / 2, -h / 2 - 38, 58, fill=col, ax=1.0)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def curva(ctx, pts, p, x0, y0, w, h, col=CIAN, ancho=12, relleno=True):
    """Línea de vistas: pts = [(fx, fy)] en 0..1, dibujada hasta la fracción p del recorrido."""
    if p <= 0.001:
        return None
    n = len(pts)
    k = p * (n - 1)
    i = int(k)
    vis = pts[:i + 1]
    if i < n - 1:
        fa, fb = pts[i], pts[i + 1]
        q = k - i
        vis = vis + [(lerp(fa[0], fb[0], q), lerp(fa[1], fb[1], q))]
    xy = [(x0 + fx * w, y0 + h - fy * h) for fx, fy in vis]
    if relleno:
        ctx.move_to(xy[0][0], y0 + h)
        for px, py in xy:
            ctx.line_to(px, py)
        ctx.line_to(xy[-1][0], y0 + h)
        ctx.close_path()
        g = cairo.LinearGradient(0, y0, 0, y0 + h)
        g.add_color_stop_rgba(0, *col, 0.35)
        g.add_color_stop_rgba(1, *col, 0.0)
        ctx.set_source(g)
        ctx.fill()
    for lw, c in ((ancho + 10, INK), (ancho, col)):
        ctx.move_to(*xy[0])
        for px, py in xy[1:]:
            ctx.line_to(px, py)
        ctx.set_source_rgb(*c)
        ctx.set_line_width(lw)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    ex, ey = xy[-1]
    ctx.arc(ex, ey, ancho * 1.3, 0, 2 * math.pi)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()
    return ex, ey


def ejes(ctx, x0, y0, w, h, etiquetas, alpha=1.0):
    ctx.move_to(x0, y0 + h)
    ctx.line_to(x0 + w, y0 + h)
    ctx.set_source_rgba(1, 1, 1, 0.5 * alpha)
    ctx.set_line_width(4)
    ctx.stroke()
    for fx, lab in etiquetas:
        texto(ctx, lab, x0 + fx * w, y0 + h + 34, 34, fill=GRIS_CLARO, stroke=None, fam=UI, bold=True, alpha=alpha)


# curvas reales (Studio, 7/11): vistas acumuladas normalizadas
CURVA_LOTE = [(0, 0), (0.02, 0.35), (0.04, 0.62), (0.06, 0.8), (0.09, 0.9), (0.13, 0.95), (0.25, 0.98), (0.5, 0.99),
              (1.0, 1.0)]
CURVA_OCEANO = [(0, 0), (0.02, 0.4), (0.04, 0.62), (0.07, 0.71), (0.12, 0.73), (0.2, 0.8), (0.3, 0.86), (0.42, 0.94),
                (0.55, 0.99), (0.75, 1.0), (1.0, 1.0)]
CURVA_AGUA = [(0, 0), (0.03, 0.2), (0.06, 0.24), (0.12, 0.25), (0.2, 0.3), (0.25, 0.43), (0.35, 0.52),
              (0.5, 0.66), (0.62, 0.78), (0.75, 0.86), (0.88, 0.94), (1.0, 1.0)]


# ------------------------------------------------------------------ 1. gancho: el pulgar a punto de deslizar
TEL = (540, 920, 0.5)


def contenido_short(t, off=0.0):
    def f(ctx):
        g = cairo.LinearGradient(0, 0, 0, 1920)
        g.add_color_stop_rgb(0, *hx("#3B1E6E"))
        g.add_color_stop_rgb(1, *hx("#0C1230"))
        ctx.rectangle(0, 0, 1080, 1920)
        ctx.set_source(g)
        ctx.fill()
        ctx.save()
        ctx.translate(0, off)
        estrellas(ctx, 1080, 1920, 50, 2, t, 0.6)
        _elipse_suave(ctx, 540, 780, 520, 360, ROSA, 0.25)
        s = bump(t, T_INF, 0.4, 0.12)
        ctx.save()
        ctx.translate(540, 780)
        ctx.scale(s, s)
        texto(ctx, "¿PUEDO SER", 0, -90, 150, sw=14)
        texto(ctx, "INFLUENCER?", 0, 90, 168, fill=AMARILLO, sw=14)
        ctx.restore()
        for i, (fn, yy) in enumerate(((corazon, 1180), (burbuja, 1360), (compartir, 1540))):
            fn(ctx, 975, yy, 58)
        ctx.arc(110, 1700, 46, 0, 2 * math.pi)
        ctx.set_source_rgb(*AMARILLO)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(6)
        ctx.stroke()
        rrect(ctx, 180, 1676, 330, 46, 23)
        ctx.set_source_rgba(1, 1, 1, 0.75)
        ctx.fill()
        ctx.restore()
        rrect(ctx, 0, 1904, 1080, 16, 0)
        ctx.set_source_rgba(1, 1, 1, 0.25)
        ctx.fill()
        rrect(ctx, 0, 1904, 1080 * clamp(t / 7.5), 16, 0)
        ctx.set_source_rgb(*ROJO)
        ctx.fill()
    return f


def pos_dedo(t):
    llega = prog(t, 0.0, 0.75, "out")
    x = lerp(760, 660, llega)
    y = lerp(2150, 1300, llega)
    gesto = prog(t, 2.35, 0.55, "inout") if t < T_AHORA else 1.0
    y -= 130 * gesto
    if t >= T_AHORA:
        y += 4 * math.sin(t * 31) + 3 * math.sin(t * 17)       # tiembla: la decisión
        x += 3 * math.sin(t * 23)
    return x, y, gesto


def medidor(ctx, t, x, y, a):
    if a <= 0.01:
        return
    ctx.save()
    ctx.push_group()
    w, h = 820, 60
    g = cairo.LinearGradient(x - w / 2, 0, x + w / 2, 0)
    g.add_color_stop_rgb(0, *VERDE)
    g.add_color_stop_rgb(0.5, *AMARILLO)
    g.add_color_stop_rgb(1, *ROJO)
    rrect(ctx, x - w / 2, y - h / 2, w, h, h / 2)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    texto(ctx, "MIRAR", x - w / 2, y + 74, 52, fill=VERDE, ax=0.0)
    texto(ctx, "DESLIZAR", x + w / 2, y + 74, 52, fill=ROJO, ax=1.0)
    v = 0.5 + 0.08 * math.sin(t * 5.3) + 0.05 * math.sin(t * 8.1)
    v += 0.33 * math.sin(math.pi * clamp((t - T_DESL + 0.1) / 0.9))
    nx = x - w / 2 + w * clamp(v, 0.04, 0.96)
    ctx.move_to(nx, y - h / 2 - 22)
    ctx.line_to(nx - 22, y - h / 2 - 50)
    ctx.line_to(nx + 22, y - h / 2 - 50)
    ctx.close_path()
    ctx.set_source_rgb(*BLANCO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    rrect(ctx, nx - 9, y - h / 2 - 20, 18, h + 40, 9)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill_preserve()
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def d_gancho(ctx, t):
    fondo(ctx, t)
    x, y, gesto = pos_dedo(t)
    z = 1 + 0.1 * prog(t, b(2) - 0.1, 2.6, "inout")
    ctx.save()
    ctx.translate(560, 980)
    ctx.scale(z, z)
    ctx.translate(-560, -980)
    cx, cy, s = TEL
    off = -260 * gesto * (1 if t < T_AHORA else 1.0)
    P.telefono(ctx, cx, cy, s, contenido_short(t, off), t)
    if t >= T_AHORA:                                     # congelado: la prueba está en curso
        k = clamp((t - T_AHORA) / 0.25)
        rrect(ctx, cx - 540 * s, cy - 960 * s, 1080 * s, 1920 * s, 70 * s)
        ctx.set_source_rgba(0.1, 0.5, 1.0, 0.16 * k * (0.7 + 0.3 * math.sin(t * 6)))
        ctx.fill()
    P.dedo(ctx, x, y, ang=-14, s=0.62, sombra=0.8)
    ctx.restore()
    # "ESTÁS EN LA PRUEBA" y la etiqueta del pulgar
    if t >= T_PRUEBA - 0.25:
        sp = pop(t, T_PRUEBA - 0.25)
        ctx.save()
        ctx.translate(540, 165)
        ctx.scale(sp, sp)
        rrect(ctx, -330, -52, 660, 104, 52)
        ctx.set_source_rgb(*ROJO)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(7)
        ctx.stroke()
        ctx.arc(-270, 0, 16, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.5 + 0.5 * (math.sin(t * 9) > 0))
        ctx.fill()
        texto(ctx, "ESTÁS EN LA PRUEBA", 22, 4, 58, fill=BLANCO, stroke=None)
        ctx.restore()
    if t >= T_PULGAR - 0.15:
        sp = pop(t, T_PULGAR - 0.15)
        cartel(ctx, "TU PULGAR", 230, 1310, 66, s=sp, rot=-6)
        if sp > 0.5:
            P.flecha(ctx, 330, 1250, x - 105, y + 90, t, color=AMARILLO, w=14, curva=-0.35)
    medidor(ctx, t, 540, 318, prog(t, b(2) + 0.2, 0.3))


# ------------------------------------------------------------------ 2. lo que se vende
def moneda(ctx, x, y, r, rot=0.0, a=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(math.cos(rot) * 0.9 + 0.1, 1)
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgba(*hx("#FFC928"), a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(5)
    ctx.stroke()
    ctx.arc(0, 0, r * 0.7, 0, 2 * math.pi)
    ctx.set_source_rgba(*hx("#E0A400"), a)
    ctx.set_line_width(4)
    ctx.stroke()
    texto(ctx, "$", 0, 3, r * 1.1, fill=hx("#8A5A00"), stroke=None, alpha=a)
    ctx.restore()


def d_vende(ctx, t):
    fondo(ctx, t)
    t0 = b(3) - 0.08
    q = prog(t, t0, 0.45, "out")
    cx, cy, s = 540, lerp(920, 900, q), lerp(0.5, 0.4, q)
    P.telefono(ctx, cx, cy, s, contenido_short(t, -260), t)
    x, y, _ = pos_dedo(t)
    fx, fy = lerp(x, 610, q), lerp(y, 1120, q)
    P.dedo(ctx, fx, fy, ang=-14, s=lerp(0.62, 0.46, q), sombra=0.8)
    # monedas que salen del toque
    if t > T_VENDE - 0.3:
        r = rng(11)
        for i in range(16):
            ph = r.uniform(0, 1)
            tt = t - (T_VENDE - 0.3) - ph * 0.9
            if tt < 0:
                continue
            u = tt * 1.1
            mx = fx + r.uniform(-260, 260) * min(1, u * 1.5)
            my = fy - 60 - u * 620 + 200 * u * u
            moneda(ctx, mx, my, r.uniform(26, 40), rot=t * 6 + ph * 6, a=clamp(1.6 - u))
    # el cartel colgado: SE VENDE
    if t >= T_VENDE - 0.2:
        sp = pop(t, T_VENDE - 0.2, 0.45)
        sw = math.sin((t - T_VENDE) * 6) * 9 * math.exp(-(t - T_VENDE) * 1.5)
        ctx.move_to(340, 530)
        ctx.line_to(300, 430)
        ctx.set_source_rgba(1, 1, 1, sp)
        ctx.set_line_width(5)
        ctx.stroke()
        cartel(ctx, "SE VENDE", 300, 400, 92, box=AMARILLO, s=sp, rot=-10 + sw)


# ------------------------------------------------------------------ 3. atención
def ojo_grande(ctx, x, y, s, abre, t):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ry = 120 * max(abre, 0.04)
    ctx.move_to(-230, 0)
    ctx.curve_to(-110, -ry * 1.4, 110, -ry * 1.4, 230, 0)
    ctx.curve_to(110, ry * 1.4, -110, ry * 1.4, -230, 0)
    ctx.close_path()
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill_preserve()
    ctx.save()
    ctx.clip()
    lx = 18 * math.sin(t * 2)
    ctx.arc(lx, 0, 96, 0, 2 * math.pi)
    ctx.set_source_rgb(*hx("#2F7FE6"))
    ctx.fill()
    ctx.arc(lx, 0, 48, 0, 2 * math.pi)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.arc(lx + 26, -26, 18, 0, 2 * math.pi)
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    ctx.restore()
    ctx.move_to(-230, 0)
    ctx.curve_to(-110, -ry * 1.4, 110, -ry * 1.4, 230, 0)
    ctx.curve_to(110, ry * 1.4, -110, ry * 1.4, -230, 0)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(12)
    ctx.stroke()
    ctx.restore()


def d_atencion(ctx, t):
    fondo(ctx, t)
    t0 = b(4) - 0.08
    _elipse_suave(ctx, 540, 820, 560, 460, AMARILLO, 0.18 * prog(t, T_ATEN - 0.1, 0.3))
    ojo_grande(ctx, 540, 640, 1.25, prog(t, t0, 0.35, "out"), t)
    if t >= T_ATEN - 0.12:
        q = prog(t, T_ATEN - 0.12, 0.22, "out")
        s = lerp(2.0, 1.0, q) * bump(t, T_ATEN + 0.1, 0.3, 0.06)
        ctx.save()
        ctx.translate(540, 1010)
        ctx.scale(s, s)
        texto(ctx, "ATENCIÓN", 0, 0, 170, fill=AMARILLO, sw=16, alpha=q)
        ctx.restore()


# ------------------------------------------------------------------ 4. 200 mil millones de Shorts por día
def d_feed(ctx, t):
    fondo(ctx, t)
    t0 = b(5) - 0.08
    ctx.save()
    ctx.push_group()
    cols = [(150, 900, 0), (400, 1250, 1), (660, 1050, 2), (920, 1400, 3)]
    for cx, vel, seed in cols:
        r = rng(40 + seed)
        hh = 380
        off = (t * vel) % (hh + 30)
        for j in range(-1, 7):
            yy = j * (hh + 30) - off + r.uniform(0, 60)
            c = [hx("#3B2A7A"), hx("#0E3C66"), hx("#5A2440"), hx("#1F5E33"), hx("#6B1A14")][(j + seed) % 5]
            rrect(ctx, cx - 105, yy, 210, hh, 22)
            ctx.set_source_rgb(*c)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(6)
            ctx.stroke()
            play(ctx, cx, yy + hh * 0.45, 34)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(0.55)
    ctx.restore()
    # panel con el contador
    sp = pop(t, t0, 0.35)
    ctx.save()
    ctx.translate(540, 780)
    ctx.scale(sp, sp)
    rrect(ctx, -500, -230, 1000, 460, 44)
    ctx.set_source_rgba(*NAVY, 0.94)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    texto(ctx, "SHORTS VISTOS POR DÍA", 0, -140, 60, fill=BLANCO)
    v = contar(t, T_200 - 0.5, T_SHORTS + 0.1, 200e9)
    texto(ctx, fmt(v), 0, 10, 112, fill=AMARILLO, sw=11)
    texto(ctx, "MÁS DE 200 MIL MILLONES", 0, 130, 46, fill=CIAN, sw=6, alpha=prog(t, T_SHORTS - 0.2, 0.3))
    ctx.restore()
    nota(ctx, "Fuente: YouTube (2025)", 540, 1060, alpha=0.85 * sp)


# ------------------------------------------------------------------ 5. dos horas por día
def d_reloj(ctx, t):
    fondo(ctx, t)
    t0 = b(6) - 0.08
    sp = pop(t, t0, 0.35)
    cx, cy, r = 650, 640, 250
    mins = contar(t, T_DOSH - 0.3, T_REDES + 0.2, 141)
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(sp, sp)
    rrect(ctx, -46, -r - 62, 92, 60, 14)
    ctx.set_source_rgb(*GRIS_CLARO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgb(*NAVY)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(14)
    ctx.stroke()
    frac = mins / 180
    ctx.move_to(0, 0)
    ctx.arc(0, 0, r - 26, -math.pi / 2, -math.pi / 2 + 2 * math.pi * frac)
    ctx.close_path()
    ctx.set_source_rgba(*ROSA, 0.85)
    ctx.fill()
    for i in range(12):
        a = i / 12 * 2 * math.pi
        ctx.move_to(math.sin(a) * (r - 22), -math.cos(a) * (r - 22))
        ctx.line_to(math.sin(a) * (r - 46), -math.cos(a) * (r - 46))
        ctx.set_source_rgba(1, 1, 1, 0.6)
        ctx.set_line_width(6)
        ctx.stroke()
    h, m = int(mins) // 60, int(mins) % 60
    texto(ctx, f"{h} h {m:02d} min", 0, 10, 92, fill=BLANCO, sw=10)
    ctx.restore()
    texto(ctx, "POR DÍA EN REDES", cx, cy + r + 80, 64, fill=AMARILLO, alpha=prog(t, T_REDES - 0.3, 0.3))
    nota(ctx, "Promedio mundial · DataReportal (2026)", cx, cy + r + 140, alpha=0.85 * sp)
    vos(ctx, "vos_cansado", 230, 1400, k=0.82, alpha=prog(t, t0, 0.25))
    # celular en la mano de Vos (brilla en la cara)
    _elipse_suave(ctx, 230, 1040, 170, 150, CIAN, 0.18 + 0.05 * math.sin(t * 7))


# ------------------------------------------------------------------ 6. más de la mitad sería influencer
ORDEN_57 = list(rng(57).permutation(100))[:57]


def persona(ctx, x, y, s, col):
    ctx.arc(x, y - 22 * s, 15 * s, 0, 2 * math.pi)
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(3.5 * s)
    ctx.stroke()
    ctx.move_to(x - 24 * s, y + 26 * s)
    ctx.curve_to(x - 24 * s, y - 6 * s, x + 24 * s, y - 6 * s, x + 24 * s, y + 26 * s)
    ctx.close_path()
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()


def d_jovenes(ctx, t):
    fondo(ctx, t)
    t0 = b(7) - 0.08
    x0, y0, dx, dy = 165, 440, 83, 80
    t_ini, t_fin = T_MITAD - 0.25, T_INFL2 + 0.2
    on = {}
    for k, idx in enumerate(ORDEN_57):
        on[int(idx)] = t_ini + (t_fin - t_ini) * k / 57
    for i in range(100):
        cx, cy = x0 + (i % 10) * dx, y0 + (i // 10) * dy
        ap = pop(t, t0 + (i % 10 + i // 10) * 0.015, 0.3)
        if ap <= 0:
            continue
        lit = i in on and t >= on[i]
        s = ap * (bump(t, on[i], 0.3, 0.35) if lit else 1.0)
        persona(ctx, cx, cy, 1.25 * s, AMARILLO if lit else GRIS)
        if lit:
            _elipse_suave(ctx, cx, cy - 6, 40, 40, AMARILLO, 0.25)
    if t >= T_MITAD - 0.2:
        sp = pop(t, T_MITAD - 0.2, 0.4)
        n = min(57, int(57 * clamp((t - t_ini) / (t_fin - t_ini))))
        cartel(ctx, f"{n}%", 540, 270, 130, s=sp, rot=-4)
    texto(ctx, "SERÍA INFLUENCER", 540, 1290, 76, fill=AMARILLO, alpha=prog(t, T_INFL2 - 0.3, 0.3))
    nota(ctx, "Generación Z · EE. UU. · Morning Consult (2023)", 540, 1350, alpha=0.85 * prog(t, t0, 0.3))


# ------------------------------------------------------------------ 7. ¿qué hace falta?
def d_pregunta(ctx, t):
    fondo(ctx, t)
    t0 = b(8) - 0.08
    sp = pop(t, t0, 0.4)
    vos(ctx, "vos_sorpresa", 540, 1400, k=1.05 * sp, alpha=1.0)
    qs = pop(t, T_FALTA - 0.2, 0.45)
    if qs > 0:
        ctx.save()
        ctx.translate(560, 330 + 14 * math.sin(t * 4))
        ctx.rotate(0.12 * math.sin(t * 3))
        ctx.scale(qs, qs)
        texto(ctx, "?", 0, 0, 360, fill=AMARILLO, sw=20)
        ctx.restore()
    for i, (x, y) in enumerate(((240, 360), (850, 420), (300, 640), (800, 700))):
        q = pop(t, T_FALTA + i * 0.07, 0.35)
        if q > 0:
            texto(ctx, "?", x, y + 8 * math.sin(t * 4 + i), 110 * q, fill=BLANCO, sw=9)


# ------------------------------------------------------------------ 8. este canal: tres semanas
def d_canal(ctx, t):
    fondo(ctx, t)
    t0 = b(9) - 0.08
    sp = pop(t, t0, 0.4)
    ctx.save()
    ctx.translate(540, 770)
    ctx.scale(sp, sp)
    rrect(ctx, -420, -380, 840, 760, 46)
    ctx.set_source_rgba(*NAVY, 0.95)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    rrect(ctx, -420, -380, 840, 150, 46)
    ctx.set_source_rgb(*AMARILLO)
    ctx.fill()
    ctx.rectangle(-420, -280, 840, 50)
    ctx.fill()
    ctx.move_to(-420, -230)
    ctx.line_to(420, -230)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    texto(ctx, "ESTE CANAL", 0, -300, 84, fill=INK, stroke=None)
    for i in range(21):
        c, f = i % 7, i // 7
        x, y = -330 + c * 110, -120 + f * 150
        rrect(ctx, x - 44, y - 50, 88, 100, 16)
        ctx.set_source_rgb(*hx("#202A4A"))
        ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.25)
        ctx.set_line_width(3)
        ctx.stroke()
        tc = T_NUMEROS - 0.2 + i * (T_SEM - T_NUMEROS + 0.2) / 21
        q = pop(t, tc, 0.25)
        if q > 0:
            ctx.save()
            ctx.translate(x, y)
            ctx.scale(q, q)
            ctx.move_to(-24, 2)
            ctx.line_to(-6, 22)
            ctx.line_to(28, -22)
            ctx.set_source_rgb(*VERDE)
            ctx.set_line_width(13)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.stroke()
            ctx.restore()
    ctx.restore()
    if t >= T_SEM - 0.25:
        cartel(ctx, "3 SEMANAS", 560, 1240, 104, box=AMARILLO, s=pop(t, T_SEM - 0.25, 0.4), rot=-5)


# ------------------------------------------------------------------ 9. el lote de prueba: ~1.200 vistas
def d_lote(ctx, t):
    fondo(ctx, t)
    t0 = b(11) - 0.08
    sp = pop(t, t0, 0.4)
    tarjeta(ctx, 290, 560, 300, t, mini=mini_nuevo, titulo="VIDEO\nNUEVO", s=sp)
    v = contar(t, T_JUNTA - 0.1, T_HORAS2 + 0.3, 1200)
    texto(ctx, "VISTAS", 760, 380, 60, fill=GRIS_CLARO, alpha=sp)
    ctx.save()
    ctx.translate(760, 500)
    s = sp * bump(t, T_1200, 0.35, 0.15)
    ctx.scale(s, s)
    texto(ctx, fmt(v), 0, 0, 150, fill=AMARILLO, sw=13)
    ctx.restore()
    # reloj chico: "pocas horas"
    if t >= T_HORAS2 - 0.4:
        q = pop(t, T_HORAS2 - 0.4, 0.35)
        cartel(ctx, "EN 3 HORAS", 760, 660, 60, box=CIAN, s=q, rot=4)
    gx, gy, gw, gh = 150, 900, 790, 360
    a = prog(t, t0 + 0.2, 0.3)
    ejes(ctx, gx, gy, gw, gh, [(0, "0 h"), (0.125, "3 h"), (0.5, "12 h"), (1.0, "24 h")], alpha=a)
    p = prog(t, T_JUNTA - 0.1, T_HORAS2 - T_JUNTA + 0.9, "linear")
    curva(ctx, CURVA_LOTE, p, gx, gy, gw, gh, col=AMARILLO)


# ------------------------------------------------------------------ 10. casi nadie suscrito
def d_suscritos(ctx, t):
    fondo(ctx, t)
    t0 = b(12) - 0.08
    sp = pop(t, t0, 0.4)
    cx, cy, r = 540, 700, 300
    frac = 0.99 * prog(t, T_NING - 0.1, T_SUSC - T_NING + 0.4, "out")
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(sp, sp)
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgb(*AMARILLO)
    ctx.set_line_width(110)
    ctx.stroke()
    if frac > 0.001:
        ctx.arc(0, 0, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * frac)
        ctx.set_source_rgb(*CIAN)
        ctx.stroke()
    for rr in (r + 55, r - 55):
        ctx.arc(0, 0, rr, 0, 2 * math.pi)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(8)
        ctx.stroke()
    texto(ctx, f"{int(round(frac * 100))}%", 0, -10, 170, fill=CIAN, sw=14)
    texto(ctx, "NO SUSCRITOS", 0, 110, 56, fill=BLANCO)
    ctx.restore()
    if t > T_SUSC:
        cartel(ctx, "1% SUSCRITOS", 820, 330, 50, box=AMARILLO, s=pop(t, T_SUSC, 0.35), rot=6)
    nota(ctx, "Horas de reproducción del canal · Studio", 540, 1150, alpha=0.85 * sp)


# ------------------------------------------------------------------ 11. se lo muestra a desconocidos
GENTE = [(185 + i * 237 + (f % 2) * 40, 900 + f * 185) for f in range(3) for i in range(4)]
DESLIZA = {0, 2, 5, 7, 8, 11}      # los que deslizan (la mitad)


def silueta(ctx, x, y, s, a=1.0, cara=True):
    persona(ctx, x, y, s, GRIS_CLARO)
    if cara:
        texto(ctx, "?", x, y - 22 * s, 24 * s, fill=INK, stroke=None, alpha=a)


def lupa(ctx, x, y, s):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(70, 70)
    ctx.line_to(150, 150)
    ctx.set_source_rgb(*hx("#6B4A2B"))
    ctx.set_line_width(34)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.arc(0, 0, 95, 0, 2 * math.pi)
    ctx.set_source_rgba(0.7, 0.9, 1, 0.25)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(20)
    ctx.stroke()
    ctx.arc(0, 0, 95, 0, 2 * math.pi)
    ctx.set_source_rgb(*GRIS_CLARO)
    ctx.set_line_width(10)
    ctx.stroke()
    ctx.restore()


def mini_copia(ctx, x, y, w, a=1.0):
    """Copia chiquita del video: tarjeta violeta con borde amarillo y play."""
    h = w * 16 / 9
    rrect(ctx, x - w / 2, y - h / 2, w, h, 12)
    ctx.set_source_rgba(*hx("#5B3FC4"), a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*AMARILLO, a)
    ctx.set_line_width(6)
    ctx.stroke()
    play(ctx, x, y, w * 0.28, a)


def d_desconocidos(ctx, t):
    fondo(ctx, t)
    t0 = b(13) - 0.08
    frenado = t >= T_FRENA - 0.1
    gris = prog(t, T_FRENA - 0.1, 0.3)
    tarjeta(ctx, 540, 400, 220, t, mini=mini_nuevo, s=pop(t, t0, 0.35), gris=gris * 0.8,
            brillo=0.6 * (1 - gris))
    texto(ctx, "DESCONOCIDOS", 540, 700, 66, fill=GRIS_CLARO,
          alpha=prog(t, T_DESC - 0.2, 0.3) * (1 - prog(t, T_FRENA - 0.3, 0.2)))
    for i, (x, y) in enumerate(GENTE):
        ap = pop(t, T_DESC - 0.4 + i * 0.03, 0.3)
        if ap <= 0:
            continue
        silueta(ctx, x, y, 2.9 * ap)
        # cada uno recibe una copia del video
        tc = T_DESC - 0.2 + i * 0.05
        if t >= tc:
            q = prog(t, tc, 0.4, "out")
            mx, my = lerp(540, x + 70, q), lerp(430, y - 95, q)
            a = 1.0
            if frenado and i in DESLIZA:
                u = prog(t, T_SID + (i % 4) * 0.12, 0.35, "in")
                my -= 1000 * u
                a = 1 - u
            if a > 0.02:
                mini_copia(ctx, mx, my, lerp(120, 64, q), a)
    if T_MIRA - 0.2 <= t < T_SID + 0.7:
        q = prog(t, T_MIRA - 0.2, T_SID - T_MIRA + 0.7, "inout")
        lupa(ctx, lerp(120, 980, q), 960 + 120 * math.sin(q * 6), 0.95)
    if frenado:
        cartel(ctx, "SE FRENA", 540, 700, 100, box=ROJO, fg=BLANCO, s=pop(t, T_FRENA - 0.1, 0.35), rot=-6)


# ------------------------------------------------------------------ 12. dos ejemplos
TIT_OCEANO = "EXTRATERRESTRES\nDEL OCÉANO"
TIT_AGUA = "¿POR QUÉ HAY\nTANTA AGUA EN\nLA TIERRA?"


def d_dos(ctx, t):
    fondo(ctx, t)
    t0 = b(15) - 0.08
    qa = prog(t, t0, 0.35, "out")
    qb = prog(t, t0 + 0.12, 0.35, "out")
    tarjeta(ctx, lerp(-300, 300, qa), 760, 360, t, mini=mini_oceano, titulo=TIT_OCEANO, titulo_size=34)
    tarjeta(ctx, lerp(1380, 780, qb), 760, 360, t, mini=mini_agua, titulo=TIT_AGUA, titulo_size=32)
    texto(ctx, "VS", 540, 760, 90, fill=AMARILLO, alpha=prog(t, t0 + 0.3, 0.2))


def d_oceano(ctx, t):
    fondo(ctx, t)
    t0 = b(16) - 0.08
    q = prog(t, t0, 0.4, "out")
    x, y, w = lerp(300, 540, q), lerp(760, 640, q), lerp(360, 420, q)
    tarjeta(ctx, lerp(780, 1400, q), 760, 360, t, mini=mini_agua, titulo=TIT_AGUA, titulo_size=32,
            alpha=1 - q)
    gris = prog(t, T_FRENO - 0.05, 0.35)
    tarjeta(ctx, x, y, w, t, mini=mini_oceano, titulo=TIT_OCEANO, titulo_size=40, gris=gris * 0.6,
            s=bump(t, T_EXTRA, 0.35, 0.05))
    if t >= T_DESL2 - 0.2:
        frac = 0.44 * prog(t, T_DESL2 - 0.1, T_MITAD2 - T_DESL2 + 0.4, "out")
        barra(ctx, 540, 1100, 840, 70, frac, ROJO, "LO DESLIZARON", f"{int(round(frac * 100))}%",
              s=pop(t, T_DESL2 - 0.2, 0.35))
    if t >= T_FRENO - 0.4:
        v = contar(t, T_FRENO - 0.4, T_1600 + 0.25, 1611)
        sh = 10 * math.sin((t - T_1600) * 40) * math.exp(-(t - T_1600) * 6) if t > T_1600 else 0
        ctx.save()
        ctx.translate(540 + sh, 1290)
        sp = pop(t, T_FRENO - 0.4, 0.3)
        ctx.scale(sp, sp)
        texto(ctx, f"{fmt(v)} VISTAS", 0, 0, 96, fill=BLANCO, sw=10)
        ctx.restore()
        if t >= T_1600 + 0.1:
            cartel(ctx, "SE FRENÓ", 820, 400, 64, box=ROJO, fg=BLANCO, s=pop(t, T_1600 + 0.1, 0.3), rot=8)


def d_agua(ctx, t):
    fondo(ctx, t)
    t0 = b(19) - 0.08
    q = prog(t, t0, 0.4, "out")
    tarjeta(ctx, lerp(540, -400, q), 640, 420, t, mini=mini_oceano, titulo=TIT_OCEANO, titulo_size=40,
            gris=0.6, alpha=1 - q)
    # fase 1: la tarjeta grande; fase 2 (siguió creciendo): se achica y aparece la curva
    q2 = prog(t, T_SIGUIO - 0.25, 0.45, "inout")
    x = lerp(lerp(1400, 540, q), 250, q2)
    y = lerp(640, 450, q2)
    w = lerp(420, 260, q2)
    tarjeta(ctx, x, y, w, t, mini=mini_agua, titulo=TIT_AGUA, titulo_size=lerp(38, 24, q2),
            brillo=prog(t, T_83, 0.3) * 0.8)
    if t >= T_QUEDO - 0.25 and q2 < 1:
        frac = 0.83 * prog(t, T_QUEDO - 0.1, T_83 - T_QUEDO + 0.35, "out")
        barra(ctx, 540, 1100, 840, 70, frac, VERDE, "SE QUEDARON A MIRAR", f"{int(round(frac * 100))}%",
              s=pop(t, T_QUEDO - 0.25, 0.35) * (1 - q2), alpha=1 - q2)
    if q2 > 0:
        gx, gy, gw, gh = 140, 760, 800, 470
        ejes(ctx, gx, gy, gw, gh, [(0, "DÍA 0"), (0.25, "1"), (0.5, "2"), (0.75, "3"), (1.0, "4")], alpha=q2)
        p = prog(t, T_SIGUIO, T_6000 - T_SIGUIO + 0.4, "linear")
        curva(ctx, CURVA_AGUA, p, gx, gy, gw, gh, col=VERDE)
        v = contar(t, T_SIGUIO, T_6000 + 0.4, 6131)
        texto(ctx, "VISTAS", 720, 340, 54, fill=GRIS_CLARO, alpha=q2)
        ctx.save()
        ctx.translate(720, 450)
        s = q2 * bump(t, T_6000, 0.35, 0.15)
        ctx.scale(s, s)
        texto(ctx, fmt(v), 0, 0, 140, fill=VERDE, sw=13)
        ctx.restore()
        if t >= T_6000:
            cartel(ctx, "+6.000", 720, 600, 64, box=VERDE, fg=INK, s=pop(t, T_6000, 0.35), rot=-5)


# ------------------------------------------------------------------ 13. el número más importante
def d_importante(ctx, t):
    fondo(ctx, t)
    t0 = b(22) - 0.08
    a = prog(t, t0, 0.3)
    ctx.rectangle(0, 0, W, H)
    ctx.set_source_rgba(0, 0, 0, 0.55 * a)
    ctx.fill()
    ctx.move_to(440, 0)
    ctx.line_to(640, 0)
    ctx.line_to(860, 1180)
    ctx.line_to(220, 1180)
    ctx.close_path()
    g = cairo.LinearGradient(0, 0, 0, 1180)
    g.add_color_stop_rgba(0, 1, 0.95, 0.7, 0.32 * a)
    g.add_color_stop_rgba(1, 1, 0.95, 0.7, 0.08 * a)
    ctx.set_source(g)
    ctx.fill()
    _elipse_suave(ctx, 540, 1180, 360, 70, hx("#FFF3C4"), 0.5 * a)
    qs = pop(t, t0 + 0.15, 0.45)
    if qs > 0:
        ctx.save()
        ctx.translate(540, 820 + 10 * math.sin(t * 4))
        ctx.scale(qs, qs)
        texto(ctx, "?", 0, 0, 380, fill=AMARILLO, sw=20)
        ctx.restore()
    if t >= T_IMPORT - 0.2:
        cartel(ctx, "EL MÁS IMPORTANTE", 540, 300, 76, s=pop(t, T_IMPORT - 0.2, 0.35), rot=-3)


# ------------------------------------------------------------------ 14. el mosaico: 35.000 vistas
COLS, FILAS = 5, 3
CW = 170
CH = CW * 16 / 9
GAP = 18
MX0 = 540 - (COLS * CW + (COLS - 1) * GAP) / 2 + CW / 2
MY0 = 430 + CH / 2


def slot(i):
    return MX0 + (i % COLS) * (CW + GAP), MY0 + (i // COLS) * (CH + GAP)


BOTON = (540, 520)


def boton_subir(ctx, x, y, s, t, presion=0.0, alpha=1.0):
    if s <= 0.01 or alpha <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s * (1 - 0.08 * presion), s * (1 - 0.08 * presion))
    ctx.push_group()
    w, h = 600, 210
    rrect(ctx, -w / 2, -h / 2 + 18 * (1 - presion), w, h, 60)
    ctx.set_source_rgb(*hx("#A3141F"))
    ctx.fill()
    rrect(ctx, -w / 2, -h / 2 + 10 * presion, w, h, 60)
    ctx.set_source_rgb(*ROJO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    yy = 10 * presion
    ctx.move_to(-200, yy + 30)
    ctx.line_to(-200, yy - 20)
    ctx.move_to(-238, yy - 2)
    ctx.line_to(-200, yy - 44)
    ctx.line_to(-162, yy - 2)
    ctx.set_source_rgb(*BLANCO)
    ctx.set_line_width(20)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    texto(ctx, "SUBIR", 50, yy + 6, 120, fill=BLANCO, stroke=INK, sw=8)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def d_mosaico(ctx, t):
    fondo(ctx, t)
    t0 = b(23) - 0.08
    apagado_ini = T_NINGUNA - 0.1
    for i in range(15):
        x, y = slot(i)
        ap = pop(t, t0 + i * 0.07, 0.3)
        if ap <= 0:
            continue
        if i < 14:
            # "ninguna existiría": se apagan de atrás para adelante
            tq = apagado_ini + (13 - i) * 0.09
            out = prog(t, tq, 0.25, "in")
            if out >= 1:
                continue
            tarjeta(ctx, x, y, CW, t, mini=mini_mosaico(i), s=ap * (1 - 0.6 * out), alpha=1 - out)
        else:
            # el lugar vacío: el próximo video
            q = prog(t, T_SUBIR - 0.3, 0.5, "inout")
            xx, yy = lerp(x, BOTON[0], q), lerp(y, BOTON[1], q)
            if q < 1:
                ctx.save()
                ctx.translate(xx, yy)
                ctx.scale(ap * (1 - q), ap * (1 - q))
                rrect(ctx, -CW / 2, -CH / 2, CW, CH, 26)
                ctx.set_source_rgba(1, 1, 1, 0.08)
                ctx.fill_preserve()
                ctx.set_dash([18, 12])
                ctx.set_source_rgba(1, 1, 1, 0.7)
                ctx.set_line_width(6)
                ctx.stroke()
                ctx.set_dash([])
                _i_mas(ctx, 0, -20, 1.0)
                texto(ctx, "EL PRÓXIMO", 0, 90, 26, fill=BLANCO, sw=4)
                ctx.restore()
            boton_subir(ctx, BOTON[0], BOTON[1], q, t)
    # contador
    if t >= t0:
        v = contar(t, t0 + 0.1, T_35 + 0.5, 35000)
        a = 1 - prog(t, apagado_ini, 0.4)
        ctx.save()
        ctx.translate(540, 290)
        s = pop(t, t0, 0.35) * bump(t, T_35 + 0.2, 0.35, 0.12)
        ctx.scale(s, s)
        texto(ctx, f"+{fmt(v)} VISTAS", 0, 0, 104, fill=AMARILLO, sw=11, alpha=a)
        ctx.restore()
    if t >= T_PRIMERO - 0.25:
        a = prog(t, T_PRIMERO - 0.25, 0.2)
        texto(ctx, "EL PRIMERO", 540, 820, 88, fill=AMARILLO, alpha=a)
        P.flecha(ctx, 540, 760, 540, 650, t, color=AMARILLO, w=14, curva=0.0, alpha=a)


# ------------------------------------------------------------------ 15. la respuesta
def d_final(ctx, t):
    fondo(ctx, t)
    t0 = b(25) - 0.08
    pres = clamp(1 - abs(t - (T_SUBELO + 0.12)) / 0.14)
    boton_subir(ctx, BOTON[0], BOTON[1], 1.0, t, presion=pres)
    pose = "vos_contento" if t < T_SUBELO else "vos_pulgar"
    sv = pop(t, t0, 0.35)
    vos(ctx, pose, 540, 1420, k=0.86 * sv * bump(t, T_SUBELO + 0.1, 0.3, 0.06))
    if t >= T_CREA - 0.15:
        sp = pop(t, T_CREA - 0.15, 0.4)
        # chispas: la idea que te motiva
        r = rng(3)
        for i in range(10):
            a = i / 10 * 2 * math.pi + t * 0.8
            rr = 250 + 30 * math.sin(t * 5 + i)
            x, y = 540 + math.cos(a) * rr, 1000 + math.sin(a) * rr * 0.55
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(t * 2 + i)
            ctx.scale(sp * r.uniform(0.6, 1.1), sp * r.uniform(0.6, 1.1))
            for k in range(4):
                ctx.rotate(math.pi / 2)
                ctx.move_to(0, 0)
                ctx.line_to(8, 26)
                ctx.line_to(0, 34)
                ctx.line_to(-8, 26)
                ctx.close_path()
            ctx.set_source_rgb(*AMARILLO)
            ctx.fill()
            ctx.restore()
    if t >= T_RESP - 0.1 and t < T_SUBELO:
        cartel(ctx, "LA RESPUESTA", 540, 290, 76, s=pop(t, T_RESP - 0.1, 0.35), rot=-3)
    if t >= T_SUBELO + 0.05:
        k = clamp(1 - (t - T_SUBELO - 0.05) / 0.35)
        ctx.rectangle(0, 0, W, H)
        ctx.set_source_rgba(1, 1, 1, 0.75 * k)
        ctx.fill()


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_gancho),
    (b(3) - 0.08, d_vende),
    (b(4) - 0.08, d_atencion),
    (b(5) - 0.08, d_feed),
    (b(6) - 0.08, d_reloj),
    (b(7) - 0.08, d_jovenes),
    (b(8) - 0.08, d_pregunta),
    (b(9) - 0.08, d_canal),
    (b(11) - 0.08, d_lote),
    (b(12) - 0.08, d_suscritos),
    (b(13) - 0.08, d_desconocidos),
    (b(15) - 0.08, d_dos),
    (b(16) - 0.08, d_oceano),
    (b(19) - 0.08, d_agua),
    (b(22) - 0.08, d_importante),
    (b(23) - 0.08, d_mosaico),
    (b(25) - 0.08, d_final),
]
# escenas que continúan a la anterior (sin fundido ni empujón: los objetos ya vienen moviéndose)
CONTINUAS = {d_vende, d_oceano, d_agua, d_final}
XF = 0.16


def escena(t):
    i = max(k for k, (t0, _) in enumerate(ESCENAS) if t >= t0)
    return i


def componer(ctx, t):
    i = escena(t)
    t0, fn = ESCENAS[i]
    dt = t - t0
    if i > 0 and dt < XF and fn not in CONTINUAS:
        capa(ctx, ESCENAS[i - 1][1], t)
        z = punch(t, t0)
        ctx.save()
        ctx.push_group()
        ctx.translate(540, 900)
        ctx.scale(z, z)
        ctx.translate(-540, -900)
        fn(ctx, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(clamp(dt / XF))
        ctx.restore()
        return
    if fn not in CONTINUAS and i > 0:
        z = punch(t, t0)
        ctx.translate(540, 900)
        ctx.scale(z, z)
        ctx.translate(-540, -900)
    fn(ctx, t)


CAPS = motor.Captions(WORDS, {"size": 76, "y": 1470, "max_palabras": 3, "max_letras": 18})


def cuadro(t):
    s, ctx = lienzo()
    try:
        componer(ctx, t)
    except Exception as e:
        raise RuntimeError(f"falló el cuadro en t={t:.3f}: {e}") from e
    im = Image.fromarray(a_rgb(s))
    CAPS.draw(im, t)
    return im


# ------------------------------------------------------------------ sonido
def sonido(kind, **kw):
    return K.snd(kind, **kw)


def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    # gancho
    ev(0.15, "whoosh_suave", 0.6)
    ev(T_INF, "pop", 0.5)
    ev(2.35, "whoosh_suave", 0.4)
    ev(T_AHORA, "frenada", 0.45, d=0.4)
    ev(T_PRUEBA - 0.25, "pop", 0.8)
    for k in range(6):
        ev(T_PRUEBA + 0.1 + k * 0.5, "tick", 0.15, f=1900, d=0.03)
    ev(T_PULGAR - 0.15, "pop", 0.7)
    ev(T_DESL, "zumbido", 0.25, d=0.8)
    # se vende
    ev(T_VENDE - 0.25, "chispa", 0.6, d=0.6)
    for k in range(6):
        ev(T_VENDE - 0.2 + k * 0.11, "clic", 0.35)
    ev(T_VENDE - 0.2, "boing", 0.5)
    # atención
    ev(T_ATEN - 0.12, "golpe", 0.9)
    ev(T_ATEN - 0.12, "whoosh", 0.5)
    # contador de Shorts
    ev(b(5) - 0.1, "whoosh", 0.6)
    for k in range(int((T_SHORTS - T_200 + 0.6) / 0.07)):
        ev(T_200 - 0.5 + k * 0.07, "tick", 0.18, f=2000 + 15 * k, d=0.025)
    ev(T_SHORTS + 0.1, "ding", 0.45)
    # reloj
    ev(b(6) - 0.1, "whoosh_suave", 0.6)
    for k in range(int((T_REDES - T_DOSH + 0.5) / 0.12)):
        ev(T_DOSH - 0.3 + k * 0.12, "tick", 0.2, f=1500, d=0.03)
    # jóvenes
    ev(b(7) - 0.1, "whoosh_suave", 0.6)
    for k in range(0, 57, 3):
        ev(T_MITAD - 0.25 + (T_INFL2 + 0.45 - T_MITAD) * k / 57, "pop", 0.25)
    ev(T_MITAD - 0.2, "boing", 0.5)
    # ¿qué hace falta?
    ev(b(8) - 0.1, "whoosh", 0.6)
    ev(T_FALTA - 0.2, "boing", 0.7)
    # este canal
    ev(b(9) - 0.1, "whoosh_suave", 0.6)
    for k in range(0, 21, 2):
        ev(T_NUMEROS - 0.2 + k * (T_SEM - T_NUMEROS + 0.2) / 21, "tick", 0.3, f=2200, d=0.03)
    ev(T_SEM - 0.25, "pop", 0.8)
    # lote de prueba
    ev(b(11) - 0.1, "whoosh", 0.6)
    for k in range(int((T_HORAS2 - T_JUNTA + 0.4) / 0.08)):
        ev(T_JUNTA - 0.1 + k * 0.08, "tick", 0.18, f=2100 + 10 * k, d=0.025)
    ev(T_HORAS2 - 0.4, "pop", 0.6)
    # suscritos
    ev(b(12) - 0.1, "whoosh_suave", 0.6)
    ev(T_NING - 0.1, "subida", 0.4, d=0.8)
    ev(T_SUSC, "pop", 0.6)
    # desconocidos
    ev(b(13) - 0.1, "whoosh_suave", 0.6)
    for i in range(0, 15, 2):
        ev(T_DESC - 0.2 + i * 0.04, "pop", 0.25)
    ev(T_MIRA - 0.2, "escaneo", 0.25, d=1.2)
    for k, i in enumerate(sorted(DESLIZA)):
        ev(T_SID + (i % 5) * 0.12, "whoosh_suave", 0.35)
    ev(T_FRENA - 0.1, "frenada", 0.6, d=0.6)
    # dos ejemplos
    ev(b(15) - 0.1, "whoosh", 0.7)
    ev(b(15) + 0.05, "whoosh", 0.5)
    ev(T_EXTRA, "pop", 0.4)
    ev(T_DESL2 - 0.2, "whoosh_suave", 0.5)
    for k in range(int((T_1600 - T_FRENO + 0.6) / 0.08)):
        ev(T_FRENO - 0.4 + k * 0.08, "tick", 0.18, f=1900, d=0.025)
    ev(T_1600 + 0.1, "frenada", 0.6, d=0.6)
    ev(b(19) - 0.1, "whoosh", 0.7)
    ev(T_83, "ding", 0.6)
    ev(T_SIGUIO - 0.2, "subida", 0.5, d=1.6)
    ev(T_6000, "pop", 0.8)
    ev(T_6000 + 0.05, "ding", 0.4)
    # el más importante
    ev(b(22) - 0.1, "whoosh_suave", 0.5)
    for k in range(int((b(23) - b(22)) / 0.06)):
        ev(b(22) + k * 0.06, "tick", 0.07 + 0.1 * k / 30, f=900, d=0.03)
    # mosaico
    for i in range(15):
        ev(b(23) - 0.08 + i * 0.07, "pop", 0.3)
    ev(T_35 + 0.2, "ding", 0.6)
    for i in range(14):
        ev(T_NINGUNA - 0.1 + (13 - i) * 0.09, "tick", 0.15, f=700, d=0.04)
    ev(T_SUBIR - 0.3, "whoosh_suave", 0.5)
    # final
    ev(T_CREA - 0.15, "chispa", 0.4, d=0.7)
    ev(T_SUBELO + 0.05, "clic", 0.9)
    ev(T_SUBELO + 0.08, "ding", 0.6)
    return E


def pista_efectos():
    n = int((TOTAL + 3) * SR)
    mix = np.zeros(n, np.float32)
    for t, k, v, kw in eventos():
        x = sonido(k, **kw) * v
        i0 = int(t * SR)
        i1 = min(n, i0 + len(x))
        if 0 <= i0 < n:
            mix[i0:i1] += x[:i1 - i0]
    mix = mix[:int(TOTAL * SR)]
    fade = int(0.08 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix *= 0.5 / (np.abs(mix).max() or 1)
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
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "puedo_ser_influencer.mp4"))
    ap.add_argument("--hilos", type=int, default=2)
    a = ap.parse_args()
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

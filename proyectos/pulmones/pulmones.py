"""Short "Tus pulmones no pueden respirar solos" — animación procedural; Vos solo en la apertura.

Mismo estilo que el picante: fondo azul oscuro con puntos, cámara que entra y sale de las escenas y
órganos con cara. El tramo de Reagan es serio: sin caras, sin personaje y sin dibujarlo a él.

    python proyectos/pulmones/pulmones.py --fotos 1,5.5,14
    python proyectos/pulmones/pulmones.py            # render completo -> salidas/tus_pulmones.mp4

Reutiliza las piezas de proyectos/picante/picante.py y proyectos/pantalla/pantalla.py.
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
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, bump, cartel, clamp, ease, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rng, rrect, texto)
from picante import (_elipse_suave, camara, capa, carita, fondo_azul, gota, mezcla, prohibido,  # noqa: E402
                     vineta_roja, zoom_entre)

W, H, FPS, SR = 1080, 1920, 30, 48000

NARRACION = [
    "Tus pulmones no pueden respirar solos.",                                                           # b0
    "No tienen ni un músculo para inflarse.",                                                           # b1
    "Los estira el diafragma, un músculo que está debajo.",                                             # b2
    "Cuando se contrae, baja como el émbolo de una jeringa.",                                           # b3
    "¿Cómo arrastra a los pulmones?",                                                                   # b4
    "Están envueltos en dos capas finitas, con un poco de líquido en el medio.",                        # b5
    "Se pegan como dos vidrios mojados: pueden deslizarse, pero no separarse.",                         # b6
    "Entonces, cuando tu pecho se agranda, los pulmones se estiran con él, y el aire entra solo.",      # b7
    "El problema es cuando algo despega esas capas.",                                                   # b8
    "En 1981 le dispararon a Ronald Reagan, el presidente de Estados Unidos.",                          # b9
    "La bala rebotó en el auto, le atravesó el pulmón y quedó a dos centímetros y medio del corazón.",  # b10
    "Por la herida entraron aire y sangre entre las dos capas.",                                        # b11
    "Se despegaron, y parte de su pulmón se desinfló como un globo.",                                   # b12
    "Su pecho se seguía moviendo, pero ese pulmón ya no se inflaba.",                                   # b13
    "Entró caminando al hospital, sin poder respirar, y cayó de rodillas.",                             # b14
    "Los médicos le metieron tubos entre las costillas para sacar el aire y la sangre, "
    "y el pulmón volvió a pegarse.",                                                                    # b15
]
WORDS = motor.align_times([{"texto": t} for t in NARRACION],
                          json.load(open(os.path.join(AQUI, "audio", "palabras.json"))))
COLA = 0.8
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
ROSA_P, ROSA_P2, ROSA_P3 = hx("#FFB0C2"), hx("#F27593"), hx("#C94A6C")
MUSCULO, MUSCULO2 = hx("#E0574F"), hx("#A8332F")
HUESO = hx("#F4ECDC")
CIAN = P.CIAN
AZUL_AGUA = hx("#5EC8FF")
SANGRE = hx("#8E0F1E")
VERDE_OK = hx("#2BB24C")
GRIS_SERIO = hx("#C9D2E3")
MONO = "DejaVu Sans Mono"
DISPLAY = "Inter Display"

# ------------------------------------------------------------------ tiempos clave
T_PULM, T_RESP = b(0, "pulmones"), b(0, "respirar")
T_MUSC, T_INFL = b(1, "músculo"), b(1, "inflarse")
T_DIAF, T_MUS2, T_DEBA = b(2, "diafragma"), b(2, "músculo"), b(2, "debajo")
T_CONT, T_BAJA, T_EMBO, T_JERI = b(3, "contrae"), b(3, "baja"), b(3, "émbolo"), b(3, "jeringa")
T_ARRA = b(4, "arrastra")
T_ENVU, T_DOS, T_CAPA, T_LIQU = b(5, "envueltos"), b(5, "dos"), b(5, "capas"), b(5, "líquido")
T_PEGA, T_VIDR, T_MOJA, T_DESL, T_PERO, T_SEPA = (b(6, "pegan"), b(6, "vidrios"), b(6, "mojados"),
                                                  b(6, "deslizarse"), b(6, "pero"), b(6, "separarse"))
T_PECH, T_AGRA, T_ESTI, T_AIRE, T_ENTR = b(7, "pecho"), b(7, "agranda"), b(7, "estiran"), b(7, "aire"), b(7, "entra")
T_PROB, T_DESP = b(8, "problema"), b(8, "despega")
T_1981, T_DISP, T_RONA, T_PRES = b(9, "1981"), b(9, "dispararon"), b(9, "Ronald"), b(9, "presidente")
T_BALA, T_REBO, T_AUTO, T_ATRA, T_PULR, T_QUED, T_CM, T_CORA = (
    b(10, "bala"), b(10, "rebotó"), b(10, "auto"), b(10, "atravesó"), b(10, "pulmón"), b(10, "quedó"),
    b(10, "dos"), b(10, "corazón"))
T_HERI, T_AIR2, T_SANG = b(11, "herida"), b(11, "aire"), b(11, "sangre")
T_DESG, T_DESI, T_GLOB = b(12, "despegaron"), b(12, "desinfló"), b(12, "globo")
T_PEC2, T_ESE, T_INFB = b(13, "pecho"), b(13, "ese"), b(13, "inflaba")
T_CAMI, T_HOSP, T_SINP, T_CAYO = b(14, "caminando"), b(14, "hospital"), b(14, "poder"), b(14, "cayó")
T_TUBO, T_COST, T_SACA, T_VOLV, T_PEG2 = (b(15, "tubos"), b(15, "costillas"), b(15, "sacar"), b(15, "volvió"),
                                          b(15, "pegarse"))

# escenas y transiciones (inicio, duración)
Z1 = (0.95, 0.42)                       # Vos -> rayos X del pecho
Z2 = (b(5) - 0.38, 0.42)                # pulmón -> las dos capas, de cerca
Z3 = (b(7) - 0.2, 0.42)                 # las capas -> el pecho (hacia afuera)
F4 = (b(9) - 0.35, 0.35)                # fundido a negro: empieza el caso real
F5 = (T_BALA - 0.12, 0.3)               # 1981 -> el auto
Z6 = (T_ATRA - 0.22, 0.4)               # el auto -> el pecho de Reagan (sin dibujarlo)
F7 = (b(14) - 0.1, 0.3)                 # pecho -> hospital
F8 = (b(15) - 0.15, 0.3)                # hospital -> pecho


# ------------------------------------------------------------------ Vos (solo en la apertura)
@functools.lru_cache(maxsize=None)
def vos_surface(pose):
    if pose == "inhala":
        body = kit.vos(eyes="closed", brows="up", mouth_kind="o")
    elif pose == "neutral":
        body = kit.vos(eyes="open", brows="neutral", mouth_kind="smile")
    else:
        raise ValueError(pose)
    png = cairosvg.svg2png(bytestring=kit.svg(520, 820, body).encode(), output_width=1040, output_height=1640)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


VK, VX, VY = 1.35, 540, 1560


def vpos(x, y):
    return VX + (x - 260) * VK, VY + (y - 806) * VK


def dibujar_vos(ctx, pose, sy=1.0, alpha=1.0):
    s = vos_surface(pose)
    ctx.save()
    ctx.translate(VX, VY)
    ctx.scale(VK / 2, VK / 2 * sy)
    ctx.translate(-520, -1612)
    ctx.set_source_surface(s, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


# ------------------------------------------------------------------ el pecho por dentro
TC = (540, 975)                          # centro del pecho en pantalla
TS = 1.38                                # escala del dibujo del pecho

PULMON_I = [(-118, -345), (-178, -312), (-232, -210), (-262, -60), (-272, 90), (-268, 228), (-215, 238),
            (-150, 206), (-85, 192), (-46, 168), (-36, 70), (-50, -10), (-40, -100), (-58, -220), (-84, -310)]
PULMON_D = [(118, -345), (178, -312), (232, -210), (262, -60), (272, 90), (268, 228), (215, 238),
            (165, 214), (128, 182), (120, 130), (104, 74), (66, 22), (48, -60), (58, -220), (84, -310)]
BASE = {5, 6, 7, 8, 9}                   # puntos que se apoyan en el diafragma
HILIO = {"i": (-55, -30), "d": (60, -25)}
CORAZON = (40, 112)


def tw(x, y):
    return TC[0] + x * TS, TC[1] + y * TS


def domo(x, c):
    """Altura del diafragma (local) en x; c = 0 relajado, 1 contraído (baja y se aplana)."""
    return lerp(196, 252, c) + lerp(0.00092, 0.0003, c) * x * x


def puntos_pulmon(lado, c=0.0, e=0.0, col=0.0, t=0.0):
    base = PULMON_I if lado == "i" else PULMON_D
    out = []
    for i, (x, y) in enumerate(base):
        if i in BASE:
            y = domo(x, c) - 14
        else:
            w = clamp((y + 150) / 330)
            y = y + (domo(x, c) - domo(x, 0)) * w
        x = x * (1 + 0.06 * e * clamp((y + 330) / 420))
        if col > 0:
            hx_, hy_ = HILIO[lado]
            k = 1 - 0.55 * col
            x, y = hx_ + (x - hx_) * k, hy_ + (y - hy_) * k
            x += 5 * col * math.sin(i * 2.3 + t * 0.5)
            y += 5 * col * math.cos(i * 1.7)
        out.append((x, y))
    return out


def curva_cerrada(ctx, pts):
    n = len(pts)
    ctx.move_to(*pts[0])
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        ctx.curve_to(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                     p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1])
    ctx.close_path()


def silueta(ctx, serio):
    ctx.move_to(-78, -720)
    ctx.line_to(-78, -480)
    ctx.curve_to(-170, -440, -380, -450, -430, -380)
    ctx.curve_to(-470, -320, -420, -100, -400, 120)
    ctx.curve_to(-390, 300, -360, 420, -340, 700)
    ctx.line_to(340, 700)
    ctx.curve_to(360, 420, 390, 300, 400, 120)
    ctx.curve_to(420, -100, 470, -320, 430, -380)
    ctx.curve_to(380, -450, 170, -440, 78, -480)
    ctx.line_to(78, -720)
    ctx.close_path()
    path = ctx.copy_path()
    g = cairo.LinearGradient(0, -500, 0, 600)
    g.add_color_stop_rgba(0, *hx("#24366E"), 0.75 if not serio else 0.6)
    g.add_color_stop_rgba(1, *hx("#142048"), 0.75 if not serio else 0.6)
    ctx.set_source(g)
    ctx.fill()
    for lw, a in ((18 / TS, 0.12), (5 / TS, 0.6)):
        ctx.append_path(path)
        ctx.set_source_rgba(*CIAN, a)
        ctx.set_line_width(lw)
        ctx.stroke()


def traquea(ctx, serio):
    col = hx("#F6CDD5") if not serio else hx("#B9C6DA")
    for d, w in (("t", 50), ("i", 34), ("d", 34)):
        if d == "t":
            ctx.move_to(0, -720)
            ctx.line_to(0, -150)
        else:
            hx_, hy_ = HILIO[d]
            ctx.move_to(0, -160)
            ctx.curve_to(0, -110, hx_ * 0.6, -90, hx_, hy_)
        path = ctx.copy_path()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_source_rgb(*INK) if not serio else ctx.set_source_rgba(1, 1, 1, 0.5)
        ctx.set_line_width(w + 10)
        ctx.stroke()
        ctx.append_path(path)
        ctx.set_source_rgb(*col)
        ctx.set_line_width(w)
        ctx.stroke()
    for y in range(-700, -170, 34):
        ctx.move_to(-22, y)
        ctx.line_to(22, y)
        ctx.set_source_rgba(*(INK if not serio else (0.3, 0.35, 0.45)), 0.35)
        ctx.set_line_width(5)
        ctx.stroke()


def corazon(ctx, t, serio, latido=1.0, alpha=1.0):
    fase = (t * 1.25) % 1
    beat = math.exp(-((fase - 0.08) / 0.05) ** 2) + 0.6 * math.exp(-((fase - 0.25) / 0.05) ** 2)
    s = 1 + 0.07 * beat * latido
    ctx.save()
    ctx.translate(*CORAZON)
    ctx.rotate(-0.35)
    ctx.scale(s, s)
    ctx.move_to(0, 78)
    ctx.curve_to(-60, 40, -98, 6, -96, -32)
    ctx.curve_to(-94, -72, -42, -86, 0, -48)
    ctx.curve_to(42, -86, 94, -72, 96, -32)
    ctx.curve_to(98, 6, 60, 40, 0, 78)
    ctx.close_path()
    path = ctx.copy_path()
    g = cairo.RadialGradient(-30, -40, 5, 0, 0, 110)
    g.add_color_stop_rgb(0, *hx("#FF6A7A"))
    g.add_color_stop_rgb(1, *hx("#B3142B"))
    ctx.save()
    ctx.clip()
    ctx.set_source(g)
    ctx.paint_with_alpha(alpha)
    ctx.restore()
    ctx.append_path(path)
    ctx.set_source_rgba(*(INK if not serio else (1, 0.8, 0.8)), alpha)
    ctx.set_line_width(7 / TS if not serio else 4 / TS)
    ctx.stroke()
    ctx.restore()


def pulmon(ctx, lado, t, c=0.0, e=0.0, col=0.0, serio=False, alarma=0.0, cara=None, mira=(0, 0)):
    pts = puntos_pulmon(lado, c, e, col, t)
    curva_cerrada(ctx, pts)
    path = ctx.copy_path()
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    if not serio:
        g = cairo.RadialGradient(cx - 50, cy - 120, 20, cx, cy, 330)
        g.add_color_stop_rgb(0, *ROSA_P)
        g.add_color_stop_rgb(0.6, *ROSA_P2)
        g.add_color_stop_rgb(1, *ROSA_P3)
        ctx.set_source(g)
        ctx.fill()
    else:
        g = cairo.RadialGradient(cx - 40, cy - 100, 20, cx, cy, 320)
        g.add_color_stop_rgba(0, *hx("#F2B3C0"), 0.85)
        g.add_color_stop_rgba(1, *hx("#9C4A62"), 0.85)
        ctx.set_source(g)
        ctx.fill()
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    # alvéolos y bronquios
    r = rng(3 if lado == "i" else 4)
    for _ in range(70):
        x = r.uniform(min(xs), max(xs))
        y = r.uniform(min(ys), max(ys))
        rr = r.uniform(7, 15)
        ctx.arc(x, y, rr, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.13 if not serio else 0.1)
        ctx.fill()
    hx_, hy_ = HILIO[lado]
    sg = -1 if lado == "i" else 1
    for k, (ex, ey) in enumerate(((sg * 200, -230), (sg * 220, -40), (sg * 200, 150), (sg * 120, 120), (sg * 140, -280))):
        ex, ey = hx_ + (ex - hx_) * (1 - 0.5 * col), hy_ + (ey - hy_) * (1 - 0.5 * col)
        ctx.move_to(hx_, hy_)
        ctx.curve_to(lerp(hx_, ex, 0.4), lerp(hy_, ey, 0.1), lerp(hx_, ex, 0.7), lerp(hy_, ey, 0.8), ex, ey)
        ctx.set_source_rgba(1, 1, 1, 0.25)
        ctx.set_line_width(9 - k)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    # brillo
    if not serio:
        ctx.save()
        ctx.translate(cx - sg * 40, cy - 170)
        ctx.rotate(sg * 0.4)
        ctx.scale(36, 70)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(1, 1, 1, 0.3)
        ctx.fill()
    if alarma > 0:
        ctx.append_path(path)
        ctx.set_source_rgba(*ROJO, 0.35 * alarma)
        ctx.fill()
    ctx.restore()
    ctx.append_path(path)
    if not serio:
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(7 / TS)
    else:
        ctx.set_source_rgba(*mezcla((1, 0.85, 0.9), ROJO, alarma), 0.9)
        ctx.set_line_width(4 / TS + 4 * alarma / TS)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    if cara:
        fx_ = sg * 150
        fy_ = -40 + (domo(0, c) - domo(0, 0)) * 0.35
        carita(ctx, fx_ * (1 + 0.04 * e), fy_, 74, 1.45, look=mira, **cara)
    return pts


def pleura(ctx, lado, c, e, t, col_brillo=CIAN, a=1.0, separacion=0.0):
    """La capa de afuera (pegada a las costillas): sigue la forma del pulmón inflado, un poco más grande."""
    if a <= 0.01:
        return
    pts = puntos_pulmon(lado, c, e)
    hx_, hy_ = HILIO[lado]
    k = 1.035 + 0.02 * separacion
    pts = [(hx_ + (x - hx_) * k, hy_ + (y - hy_) * k) for x, y in pts]
    for lw, al in ((16, 0.18), (5, 0.95)):
        curva_cerrada(ctx, pts)
        ctx.set_source_rgba(*col_brillo, al * a)
        ctx.set_line_width(lw / TS)
        ctx.stroke()
    return pts


def costillas(ctx, e, serio, a=1.0):
    col = HUESO
    for i in range(7):
        y0 = -300 + i * 70 - 10 * e
        for sg in (-1, 1):
            x1 = sg * (262 + i * 12) * (1 + 0.06 * e)
            y1 = y0 + 46 + i * 4
            ctx.move_to(sg * 24, y0)
            ctx.curve_to(sg * 150, y0 - 70 - 6 * e, x1 * 0.92, y0 - 50, x1, y1)
            path = ctx.copy_path()
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            if not serio:
                ctx.set_source_rgba(*col, 0.42 * a)
                ctx.set_line_width(20 / TS)
                ctx.stroke()
                ctx.append_path(path)
                ctx.set_source_rgba(1, 1, 1, 0.55 * a)
                ctx.set_line_width(5 / TS)
                ctx.stroke()
            else:
                ctx.set_source_rgba(1, 1, 1, 0.12 * a)
                ctx.set_line_width(26 / TS)
                ctx.stroke()
                ctx.append_path(path)
                ctx.set_source_rgba(*GRIS_SERIO, 0.75 * a)
                ctx.set_line_width(8 / TS)
                ctx.stroke()
    # esternón y clavículas
    rrect(ctx, -20, -330, 40, 470, 18)
    ctx.set_source_rgba(*(col if not serio else GRIS_SERIO), (0.45 if not serio else 0.4) * a)
    ctx.fill()
    for sg in (-1, 1):
        ctx.move_to(sg * 30, -372)
        ctx.curve_to(sg * 120, -400, sg * 200, -370, sg * 300, -405)
        ctx.set_source_rgba(*(col if not serio else GRIS_SERIO), (0.5 if not serio else 0.6) * a)
        ctx.set_line_width(20 / TS)
        ctx.stroke()


def diafragma(ctx, c, t, serio=False, cara=None, brillo=0.0, a=1.0):
    if a <= 0.01:
        return
    xs = [-340 + 680 * i / 40 for i in range(41)]
    ctx.move_to(xs[0], domo(xs[0], c))
    for x in xs[1:]:
        ctx.line_to(x, domo(x, c))
    for x in reversed(xs):
        ctx.line_to(x, domo(x, c) + 70 - 0.00025 * x * x)
    ctx.close_path()
    path = ctx.copy_path()
    ctx.save()
    ctx.push_group()
    g = cairo.LinearGradient(0, domo(0, c), 0, domo(0, c) + 60)
    g.add_color_stop_rgb(0, *mezcla(MUSCULO, (1, 0.8, 0.6), 0.3 * brillo))
    g.add_color_stop_rgb(1, *MUSCULO2)
    ctx.append_path(path)
    ctx.set_source(g)
    ctx.fill()
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    for k in range(-330, 340, 26):
        ctx.move_to(k, domo(k, c) - 2)
        ctx.line_to(k + 10, domo(k, c) + 60)
        ctx.set_source_rgba(1, 1, 1, 0.16)
        ctx.set_line_width(5)
        ctx.stroke()
    ctx.restore()
    ctx.append_path(path)
    ctx.set_source_rgb(*INK) if not serio else ctx.set_source_rgba(1, 0.8, 0.75, 0.8)
    ctx.set_line_width(7 / TS if not serio else 4 / TS)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    if cara:
        carita(ctx, 0, domo(0, c) + 22, 56, 1.05, **cara)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def aire(ctx, flujo, vel, t, serio=False, a=1.0):
    """Partículas de aire que bajan por la tráquea (vel > 0) o suben (vel < 0)."""
    al = clamp(abs(vel) * 2.5) * a
    if al <= 0.02:
        return
    r = rng(17)
    for k in range(34):
        lado = "i" if k % 2 else "d"
        tx = r.uniform(80, 220) * (-1 if lado == "i" else 1)
        ty = r.uniform(-260, 160)
        u = (k / 34 + flujo * 0.9) % 1
        if u < 0.55:
            q = u / 0.55
            x, y = 0, lerp(-760, -150, q)
        else:
            q = (u - 0.55) / 0.45
            hx_, hy_ = HILIO[lado]
            x, y = lerp(0, hx_, min(1, q * 2)), lerp(-150, hy_, min(1, q * 2))
            if q > 0.5:
                qq = (q - 0.5) * 2
                x, y = lerp(hx_, tx, qq), lerp(hy_, ty, qq)
        x += 6 * math.sin(t * 9 + k)
        ctx.arc(x, y, 9, 0, 2 * math.pi)
        ctx.set_source_rgba(*(CIAN if not serio else (0.9, 0.95, 1)), 0.85 * al)
        ctx.fill()


def respiracion(t, ciclos):
    """ciclos: [(t0, t1, v0, v1)] tramos de la inspiración; fuera de ellos se mantiene el último valor."""
    v = ciclos[0][2]
    for t0, t1, v0, v1 in ciclos:
        if t >= t0:
            v = lerp(v0, v1, ease(clamp((t - t0) / (t1 - t0)), "inout"))
    return v


# ------------------------------------------------------------------ 1. el gancho: Vos y sus pulmones a rayos X
CAMISA = vpos(260, 566)                  # centro de la remera en pantalla
ZG = 3.1                                 # cuánto entra la cámara


def d_gancho(ctx, t):
    fondo_azul(ctx, t)
    sy = 1 + 0.025 * math.sin(math.pi * clamp(t / 0.9))
    dibujar_vos(ctx, "inhala", sy=sy)
    # ventana de rayos X sobre la remera
    x0, y0 = vpos(158, 452)
    x1, y1 = vpos(362, 680)
    ctx.save()
    rrect(ctx, x0 - 6, y0 - 6, x1 - x0 + 12, y1 - y0 + 12, 70)
    ctx.clip()
    ctx.save()
    camara(ctx, 540, 900, 1 / ZG, CAMISA[0], CAMISA[1])
    d_torso(ctx, t)
    ctx.restore()
    q = (t * 0.9) % 1
    ctx.rectangle(x0, lerp(y0, y1, q) - 6, x1 - x0, 12)
    ctx.set_source_rgba(*CIAN, 0.55)
    ctx.fill()
    ctx.restore()
    rrect(ctx, x0 - 6, y0 - 6, x1 - x0 + 12, y1 - y0 + 12, 70)
    ctx.set_source_rgba(*CIAN, 0.9)
    ctx.set_line_width(6)
    ctx.stroke()
    cartel(ctx, "TUS PULMONES\nNO RESPIRAN SOLOS", 540, 245, 80, s=1 + 0.012 * math.sin(t * 2.4), pad=(52, 26))


# ------------------------------------------------------------------ 2. el pecho con los pulmones que no pueden solos
def insp_lindo(t):
    return respiracion(t, [
        (0, 0.1, 0, 0),
        (T_CONT + 0.1, T_BAJA + 0.4, 0, 1),            # el diafragma baja
        (T_EMBO - 0.35, T_EMBO + 0.05, 1, 0.1),          # suelta
        (T_EMBO + 0.15, T_JERI + 0.35, 0.1, 1),          # otra vez, junto a la jeringa
        (T_ARRA - 0.35, T_ARRA, 1, 0.15),
        (T_ARRA + 0.05, T_ARRA + 0.9, 0.15, 1),          # ¿cómo los arrastra?
        (Z3[0], Z3[0] + 0.3, 1, 0.1),
        (T_PECH, T_AGRA + 0.5, 0.1, 1),                  # el pecho se agranda
        (T_ESTI + 0.3, T_ESTI + 0.9, 1, 0.2),
        (T_AIRE - 0.3, T_ENTR + 0.4, 0.2, 1),            # y el aire entra solo
        (T_PROB, T_PROB + 0.9, 1, 0.3),
    ])


def esfuerzo(t):
    """Los pulmones intentan inflarse solos y no pueden."""
    return clamp((t - 0.3) / 0.3) * (1 - prog(t, b(2) - 0.1, 0.4))


def cara_pulmon(t, lado):
    if t < b(1):
        return dict(ojos="closed", boca="wavy", ceja="angry", rubor=True)
    if t < T_DIAF:
        return dict(ojos="open", boca="flat", ceja="worried")
    if t < T_BAJA:
        return dict(ojos="open", boca="smile")
    if t < T_ARRA:
        return dict(ojos="happy", boca="grin")
    if t < b(5):
        return dict(ojos="wide", boca="o", ceja="up")
    if t < T_PROB:
        return dict(ojos="happy", boca="grin")
    if lado == "d" and t >= T_DESP:
        return dict(ojos="wide", boca="o", ceja="worried")
    return dict(ojos="open", boca="flat", ceja="worried")


def d_torso(ctx, t):
    ins = insp_lindo(t)
    v = (insp_lindo(t + 0.04) - insp_lindo(t - 0.04)) / 0.08
    flujo = ins
    tiembla = esfuerzo(t)
    oscuro = prog(t, T_PROB - 0.2, 0.8)
    fondo_azul(ctx, t)
    # cámara: se corre a la izquierda para mostrar la jeringa
    jer = prog(t, T_EMBO - 0.45, 0.45) * (1 - prog(t, T_ARRA - 0.4, 0.45))
    fx, fy, z = lerp(540, 700, jer), lerp(960, 930, jer), lerp(1.0, 0.8, jer)
    z *= 1 + 0.03 * math.sin(t * 0.7)
    ctx.save()
    camara(ctx, fx, fy, z)
    ctx.save()
    ctx.translate(*TC)
    ctx.scale(TS, TS)
    ctx.translate(4 * math.sin(t * 50) * tiembla, 0)
    silueta(ctx, False)
    traquea(ctx, False)
    corazon(ctx, t, False)
    sep_d = 0.0
    if t >= T_DESP:
        sep_d = prog(t, T_DESP, 0.5)
    for lado in ("i", "d"):
        sx = 1 + 0.03 * math.sin(t * 40) * tiembla
        ctx.save()
        hx_, hy_ = HILIO[lado]
        ctx.translate(hx_, hy_)
        ctx.scale(sx, 2 - sx)
        ctx.translate(-hx_, -hy_)
        col = 0.18 * sep_d if lado == "d" else 0.0
        mira = (0, 1) if T_DIAF <= t < T_CONT else (0, 0)
        pulmon(ctx, lado, t, c=ins, e=ins * (1.0 if t >= b(7) else 0.3), col=col, cara=cara_pulmon(t, lado),
               mira=mira, alarma=0.6 * sep_d if lado == "d" else 0.0)
        ctx.restore()
    # la capa de afuera: se ve cuando la explicamos
    a_pl = prog(t, T_ARRA, 0.4) * (1 - prog(t, T_PROB + 0.3, 0.3)) + prog(t, T_DESP - 0.2, 0.3)
    for lado in ("i", "d"):
        rojo = sep_d if lado == "d" else 0.0
        pleura(ctx, lado, ins, ins * (1.0 if t >= b(7) else 0.3), t, col_brillo=mezcla(CIAN, ROJO, rojo),
               a=clamp(a_pl), separacion=6 * rojo)
    aire(ctx, flujo * 3, v, t)
    # diafragma
    a_d = pop(t, T_DIAF - 0.15, 0.4)
    if a_d > 0.01:
        brillo = max(bump(t, T_MUS2, 0.4, 1.0) - 1, clamp((insp_lindo(t + 0.05) - insp_lindo(t - 0.05)) * 6))
        ctx.save()
        ctx.translate(0, 120 * (1 - a_d))
        diafragma(ctx, ins, t, brillo=brillo, a=min(1, a_d * 1.2))
        ctx.restore()
    costillas(ctx, ins * (1.0 if t >= b(7) else 0.25), False)
    ctx.restore()
    # jeringa
    if jer > 0.01:
        jeringa(ctx, 1000, 900, 1.3 * pop(t, T_EMBO - 0.3, 0.4), ins, t, v)
    ctx.restore()
    # carteles
    if t >= T_MUSC - 0.1 and t < b(2) + 0.2:
        a = 1 - prog(t, b(2) - 0.1, 0.25)
        biceps(ctx, 830, 300, 0.95 * pop(t, T_MUSC - 0.1) * a)
        if a > 0:
            prohibido(ctx, 820, 280, 150, pop(t, T_MUSC + 0.15) * a)
    if T_DIAF <= t < T_CONT + 0.3:
        cartel(ctx, "DIAFRAGMA", 540, TC[1] + (domo(0, 0) + 38) * TS, 70,
               s=pop(t, T_DIAF) * (1 - prog(t, T_CONT, 0.25, "in")), rot=-2)
    if T_ARRA <= t < Z2[0] + 0.1:
        cartel(ctx, "¿CÓMO?", 540, 230, 90, s=pop(t, T_ARRA), rot=-3)
    if oscuro > 0:
        ctx.rectangle(0, 0, W, H)
        ctx.set_source_rgba(0.0, 0.0, 0.03, 0.45 * oscuro)
        ctx.fill()
        if t >= T_DESP:
            vineta_roja(ctx, 0.5 * prog(t, T_DESP, 0.4) * (0.8 + 0.2 * math.sin(t * 8)))


def biceps(ctx, x, y, s):
    """Brazo flexionado (el músculo que los pulmones no tienen)."""
    if s <= 0.01:
        return
    piel = hx(kit.P["piel"])
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(-150, 70)
    ctx.line_to(-150, 0)
    ctx.curve_to(-120, -60, -20, -70, 10, -20)
    ctx.line_to(20, -90)
    ctx.curve_to(10, -150, 110, -160, 110, -90)
    ctx.line_to(100, 30)
    ctx.curve_to(95, 80, 60, 90, 20, 90)
    ctx.line_to(-150, 90)
    ctx.close_path()
    ctx.set_source_rgb(*piel)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    for x0, y0, x1, y1 in ((22, -100, 98, -104), (24, -72, 96, -76)):
        ctx.move_to(x0, y0)
        ctx.line_to(x1, y1)
        ctx.set_line_width(5)
        ctx.stroke()
    ctx.move_to(-110, -10)
    ctx.curve_to(-80, -40, -40, -40, -20, -20)
    ctx.set_source_rgba(1, 1, 1, 0.6)
    ctx.set_line_width(8)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    rrect(ctx, -200, 40, 60, 60, 12)
    ctx.set_source_rgb(*hx(kit.P["remera"]))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.restore()


def jeringa(ctx, x, y, s, ins, t, vel):
    """Jeringa vertical con la punta arriba: al bajar el émbolo entra aire."""
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    top, bot, w = -330, 260, 150
    # aguja / pico
    rrect(ctx, -14, top - 120, 28, 120, 8)
    ctx.set_source_rgb(*hx("#DDE5F0"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    # cilindro
    rrect(ctx, -w / 2, top, w, bot - top, 22)
    ctx.set_source_rgba(0.8, 0.95, 1, 0.22)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    yp = lerp(top + 60, bot - 70, ins)
    # aire adentro
    r = rng(5)
    for k in range(int(4 + 26 * ins)):
        px, py = r.uniform(-w / 2 + 18, w / 2 - 18), r.uniform(top + 16, top + 16 + (bot - top) * 0.95)
        if py < yp - 20:
            ctx.arc(px + 4 * math.sin(t * 5 + k), py, 7, 0, 2 * math.pi)
            ctx.set_source_rgba(*CIAN, 0.8)
            ctx.fill()
    for k in range(5):
        ctx.move_to(w / 2 - 6, top + 60 + k * 100)
        ctx.line_to(w / 2 - 30, top + 60 + k * 100)
        ctx.set_source_rgba(*INK, 0.6)
        ctx.set_line_width(4)
        ctx.stroke()
    # émbolo
    rrect(ctx, -w / 2 + 8, yp - 20, w - 16, 40, 10)
    ctx.set_source_rgb(*hx("#3B4256"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    rrect(ctx, -16, yp + 20, 32, bot + 140 - yp, 8)
    ctx.set_source_rgb(*hx("#E8EDF5"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    rrect(ctx, -70, yp + bot + 140 - yp - 6 + 20 - 20, 140, 26, 12)
    ctx.set_source_rgb(*hx("#E8EDF5"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    # aire que entra por la punta
    if vel > 0.05:
        for k in range(5):
            q = (t * 2.2 + k / 5) % 1
            ctx.arc(6 * math.sin(k * 3 + t * 6), top - 190 + q * 230, 8, 0, 2 * math.pi)
            ctx.set_source_rgba(*CIAN, 0.9 * clamp(vel))
            ctx.fill()
    ctx.restore()


# ------------------------------------------------------------------ 3. las dos capas y los vidrios mojados
APEX = tw(-118, -345)                    # punto del pulmón donde entra la cámara
CAPAS_C = (540, 700)


def yo(x):
    return 0.00035 * (clamp(x, -200, 1280) - 540) ** 2


def banda(ctx, y0, y1, col, a, dy=0.0):
    xs = [-4000] + list(range(-200, 1281, 30)) + [5000]
    for i, x in enumerate(xs):
        (ctx.move_to if i == 0 else ctx.line_to)(x, y0 + yo(x) + dy)
    for x in reversed(xs):
        ctx.line_to(x, y1 + yo(x) + dy)
    ctx.close_path()
    ctx.set_source_rgba(*col, a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, a)
    ctx.set_line_width(5)
    ctx.stroke()


def d_capas(ctx, t):
    m = prog(t, T_VIDR - 0.35, 0.45)
    if m < 0.999:
        ctx.save()
        ctx.push_group()
        # pared del pecho
        g = cairo.LinearGradient(0, 0, 0, 700)
        g.add_color_stop_rgb(0, *hx("#5E1828"))
        g.add_color_stop_rgb(1, *hx("#A33A4C"))
        ctx.set_source(g)
        ctx.paint()
        for k in range(-20, 40):
            ctx.move_to(k * 40, -200)
            ctx.line_to(k * 40 + 390, 700)
            ctx.set_source_rgba(1, 1, 1, 0.06)
            ctx.set_line_width(8)
            ctx.stroke()
        for x, y in ((270, 380), (810, 400)):
            ctx.save()
            ctx.translate(x, y)
            ctx.scale(150, 92)
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgb(*HUESO)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(7)
            ctx.stroke()
            r = rng(int(x))
            for _ in range(14):
                ctx.arc(x + r.uniform(-90, 90), y + r.uniform(-50, 50), r.uniform(5, 11), 0, 2 * math.pi)
                ctx.set_source_rgba(*hx("#E2C9A8"), 0.8)
                ctx.fill()
        # pulmón
        xs = [-4000] + list(range(-200, 1281, 30)) + [5000]
        for i, x in enumerate(xs):
            (ctx.move_to if i == 0 else ctx.line_to)(x, 760 + yo(x))
        ctx.line_to(5000, 9000)
        ctx.line_to(-4000, 9000)
        ctx.close_path()
        g = cairo.LinearGradient(0, 760, 0, 1900)
        g.add_color_stop_rgb(0, *ROSA_P2)
        g.add_color_stop_rgb(1, *ROSA_P3)
        ctx.set_source(g)
        ctx.fill()
        r = rng(9)
        for _ in range(140):
            x, y = r.uniform(-20, 1100), r.uniform(800, 1920)
            if y < 790 + yo(x):
                continue
            rr = r.uniform(18, 40)
            ctx.arc(x, y, rr, 0, 2 * math.pi)
            ctx.set_source_rgba(*ROSA_P, 0.55)
            ctx.fill_preserve()
            ctx.set_source_rgba(*ROSA_P3, 0.6)
            ctx.set_line_width(4)
            ctx.stroke()
        # las dos capas y el líquido
        g1 = bump(t, T_DOS, 0.45, 0.6) - 1
        g2 = bump(t, T_CAPA, 0.45, 0.6) - 1
        gl = bump(t, T_LIQU, 0.5, 0.8) - 1
        banda(ctx, 640, 676, mezcla(hx("#BDEFFF"), (1, 1, 1), g1), 1.0)
        banda(ctx, 676, 724, mezcla(AZUL_AGUA, (0.8, 0.95, 1), gl), 0.85)
        r = rng(4)
        for k in range(26):
            x = (r.uniform(0, 1080) + t * 60 * (1 if k % 2 else -1)) % 1120 - 20
            ctx.arc(x, 700 + yo(x) + 8 * math.sin(t * 3 + k), 5, 0, 2 * math.pi)
            ctx.set_source_rgba(1, 1, 1, 0.7)
            ctx.fill()
        banda(ctx, 724, 760, mezcla(hx("#BDEFFF"), (1, 1, 1), g2), 1.0)
        # brillo que recorre las capas cuando dice "envueltos"
        if T_ENVU <= t < T_ENVU + 0.8:
            q = (t - T_ENVU) / 0.8
            _elipse_suave(ctx, lerp(-100, 1180, q), 700 + yo(lerp(-100, 1180, q)), 160, 70, (1, 1, 1), 0.7)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(1 - m)
        ctx.restore()
        if T_CAPA <= t < T_LIQU - 0.1:
            cartel(ctx, "DOS CAPAS", 540, 1080, 84, box=BLANCO, s=pop(t, T_CAPA) * (1 - prog(t, T_LIQU - 0.35, 0.25)) * (1 - m))
        if T_LIQU <= t:
            cartel(ctx, "LÍQUIDO", 540, 1080, 84, box=AZUL_AGUA, s=pop(t, T_LIQU) * (1 - prog(t, T_PEGA, 0.25)) * (1 - m))
    if m > 0.001:
        ctx.save()
        ctx.push_group()
        d_vidrios(ctx, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(m)
        ctx.restore()


def vidrio(ctx, x, y, w, h, flex=0.0):
    ctx.save()
    rrect(ctx, x, y - flex, w, h, 18)
    ctx.set_source_rgba(0.75, 0.93, 1, 0.55)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    for k, (dx, ww) in enumerate(((60, 40), (130, 16))):
        ctx.move_to(x + dx, y + h - 14 - flex)
        ctx.line_to(x + dx + 70, y + 14 - flex)
        ctx.set_source_rgba(1, 1, 1, 0.6)
        ctx.set_line_width(ww / 2)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
    ctx.restore()


def d_vidrios(ctx, t):
    fondo_azul(ctx, t)
    desl = 0.0
    if T_DESL - 0.05 <= t < T_PERO + 0.05:
        q = clamp((t - T_DESL + 0.05) / (T_PERO - T_DESL + 0.1))
        desl = 250 * math.sin(math.pi * ease(q, "inout"))
    tira = 0.0
    if t >= T_SEPA - 0.25:
        sube = prog(t, T_SEPA - 0.25, 0.35, "out")
        cae = prog(t, T_SEPA + 0.45, 0.25, "in")
        tira = 70 * sube * (1 - cae)
        if t >= T_SEPA + 0.7:
            tira = -12 * math.sin((t - T_SEPA - 0.7) * 25) * math.exp(-(t - T_SEPA - 0.7) * 8)
    tiembla = 5 * math.sin(t * 60) if T_SEPA - 0.1 <= t < T_SEPA + 0.45 else 0.0
    agua = prog(t, T_MOJA - 0.1, 0.4)
    yb = 800
    ctx.save()
    ctx.translate(0, -tira)
    # vidrio de abajo (sube con el de arriba: no se separan)
    vidrio(ctx, 110 + tiembla * 0.5, yb, 860, 150)
    carita(ctx, 540 + tiembla * 0.5, yb + 66, 80, 1.6,
           **(dict(ojos="happy", boca="grin") if tira <= 1 else dict(ojos="closed", boca="wavy", ceja="angry")))
    # película de agua
    if agua > 0:
        rrect(ctx, 120, yb - 12, 840, 14, 7)
        ctx.set_source_rgba(*AZUL_AGUA, 0.9 * agua)
        ctx.fill()
    vidrio(ctx, 110 + desl + tiembla, yb - 164, 860, 150)
    cara_arr = dict(ojos="open", boca="smile")
    if desl > 5:
        cara_arr = dict(ojos="happy", boca="grin")
    if tira > 1:
        cara_arr = dict(ojos="closed", boca="wavy", ceja="angry")
    carita(ctx, 540 + desl + tiembla, yb - 98, 80, 1.6, **cara_arr)
    ctx.restore()
    # gotas que caen al mojarlos
    if T_MOJA - 0.4 <= t < T_MOJA + 0.6:
        r = rng(6)
        for k in range(10):
            t0 = T_MOJA - 0.4 + r.uniform(0, 0.4)
            if t < t0:
                continue
            q = clamp((t - t0) / 0.4)
            x = r.uniform(220, 860)
            gota(ctx, x, lerp(320, 630, q * q), 18, AZUL_AGUA, alpha=1 - prog(t, t0 + 0.35, 0.1))
    # flechas
    if T_DESL - 0.1 <= t < T_PERO + 0.2:
        a = pop(t, T_DESL - 0.1, 0.3) * (1 - prog(t, T_PERO, 0.2))
        flecha_doble(ctx, 540, 520, 240, a)
    if T_SEPA - 0.35 <= t < T_SEPA + 0.9:
        a = pop(t, T_SEPA - 0.35, 0.3) * (1 - prog(t, T_SEPA + 0.6, 0.3))
        ventosa(ctx, 540, yb - 164 - tira, a, tira)


def flecha_doble(ctx, x, y, L, a):
    if a <= 0.01:
        return
    for sg in (-1, 1):
        ctx.move_to(x, y)
        ctx.line_to(x + sg * L, y)
        ctx.move_to(x + sg * (L - 40), y - 34)
        ctx.line_to(x + sg * L, y)
        ctx.line_to(x + sg * (L - 40), y + 34)
    for lw, col in ((24, INK), (12, AMARILLO)):
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgba(*col, a)
        ctx.set_line_width(lw)
        ctx.stroke_preserve()
    ctx.new_path()


def ventosa(ctx, x, y, a, tira):
    if a <= 0.01:
        return
    ctx.save()
    ctx.push_group()
    # flecha hacia arriba
    for lw, col in ((26, INK), (13, AMARILLO)):
        ctx.move_to(x, y - 110)
        ctx.line_to(x, y - 320 - tira)
        ctx.move_to(x - 40, y - 270 - tira)
        ctx.line_to(x, y - 320 - tira)
        ctx.line_to(x + 40, y - 270 - tira)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        ctx.stroke()
    rrect(ctx, x - 14, y - 120, 28, 90, 10)
    ctx.set_source_rgb(*hx("#C9D0DD"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.move_to(x - 70, y)
    ctx.curve_to(x - 60, y - 40, x - 30, y - 40, x, y - 40)
    ctx.curve_to(x + 30, y - 40, x + 60, y - 40, x + 70, y)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#FF5A6E"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


# ------------------------------------------------------------------ 4. el caso real (serio)
def fondo_serio(ctx, t, k=1.0):
    P.fondo(ctx, t, tinte=(0.012, 0.018, 0.04))
    g = cairo.RadialGradient(540, 900, 300, 540, 900, 1250)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.7)
    ctx.set_source(g)
    ctx.paint()


def grano(ctx, t):
    r = rng(int(t * FPS) + 3)
    for _ in range(260):
        x, y = r.uniform(0, W), r.uniform(0, H)
        ctx.rectangle(x, y, 3, 3)
        ctx.set_source_rgba(1, 1, 1, r.uniform(0.02, 0.07))
        ctx.fill()


def maquina(ctx, s, x, y, size, t, t0, cps=18, fam=MONO, fill=BLANCO, bold=False, cursor=True, centro=True,
            alpha=1.0):
    """Texto que aparece letra por letra, como máquina de escribir (centrado en x)."""
    if t < t0:
        return
    P.fuente(ctx, fam, size, bold)
    if centro:
        x = x - ctx.text_extents(s)[4] / 2
    n = int((t - t0) * cps)
    txt = s[:max(0, min(len(s), n))]
    ancho = texto(ctx, txt, x, y, size, fill=fill, stroke=None, sw=0, ax=0.0, fam=fam, bold=bold,
                  alpha=alpha) if txt else 0
    if cursor and n < len(s) + 6 and int(t * 4) % 2 == 0:
        ctx.rectangle(x + ancho + 6, y - size * 0.45, size * 0.5, size * 0.9)
        ctx.set_source_rgba(*fill, 0.85 * alpha)
        ctx.fill()


def rotulo(ctx, s, x, y, size, col, t, t0, t1=None):
    """Rótulo sobrio: caja oscura con borde fino y texto a máquina."""
    if t < t0:
        return
    a = prog(t, t0, 0.15) * (1 - (prog(t, t1, 0.25) if t1 is not None else 0))
    if a <= 0.01:
        return
    P.fuente(ctx, MONO, size, True)
    w = ctx.text_extents(s)[4] + 56
    h = size * 1.7
    rrect(ctx, x - w / 2, y - h / 2, w, h, 10)
    ctx.set_source_rgba(0.02, 0.03, 0.06, 0.78 * a)
    ctx.fill_preserve()
    ctx.set_source_rgba(*col, 0.85 * a)
    ctx.set_line_width(3)
    ctx.stroke()
    maquina(ctx, s, x, y, size, t, t0, cps=26, fill=col, bold=True, cursor=False, alpha=a)


def d_1981(ctx, t):
    fondo_serio(ctx, t)
    shake = 0.0
    if T_DISP <= t < T_DISP + 0.35:
        shake = 14 * math.sin(t * 90) * (1 - (t - T_DISP) / 0.35)
    ctx.save()
    ctx.translate(shake, 0)
    # el año
    if t >= T_1981 - 0.1:
        n = min(4, int((t - T_1981 + 0.1) * 9))
        fuente_y = 640
        texto(ctx, "1981"[:n], 540, fuente_y, 300, fill=BLANCO, stroke=None, sw=0, fam=DISPLAY, bold=True)
        L = 560 * prog(t, T_1981 + 0.4, 0.6)
        ctx.rectangle(540 - L / 2, 800, L, 8)
        ctx.set_source_rgb(*ROJO)
        ctx.fill()
    maquina(ctx, "30 DE MARZO · WASHINGTON D. C.", 540, 880, 40, t, T_1981 + 0.7, cps=26, cursor=False)
    if t >= T_RONA - 0.05:
        a = prog(t, T_RONA - 0.05, 0.25)
        texto(ctx, "RONALD REAGAN", 540, 1100, 112, fill=BLANCO, stroke=None, sw=0, fam=DISPLAY, bold=True,
              alpha=a)
    if t >= T_PRES - 0.05:
        maquina(ctx, "PRESIDENTE DE ESTADOS UNIDOS", 540, 1210, 40, t, T_PRES - 0.05, cps=30, fill=GRIS_SERIO,
                cursor=False)
    ctx.restore()
    if T_DISP <= t < T_DISP + 0.18:
        ctx.rectangle(0, 0, W, H)
        ctx.set_source_rgba(1, 1, 1, 0.35 * (1 - (t - T_DISP) / 0.18))
        ctx.fill()
    grano(ctx, t)


def limusina(ctx, x, y, s):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(-440, 40)
    ctx.line_to(-440, -10)
    ctx.curve_to(-430, -40, -400, -50, -350, -54)
    ctx.line_to(-250, -60)
    ctx.curve_to(-210, -130, -170, -140, -120, -142)
    ctx.line_to(230, -142)
    ctx.curve_to(280, -140, 300, -120, 330, -66)
    ctx.line_to(400, -56)
    ctx.curve_to(440, -50, 450, -20, 450, 10)
    ctx.line_to(450, 40)
    ctx.close_path()
    ctx.set_source_rgb(*hx("#0B0F1A"))
    ctx.fill_preserve()
    ctx.set_source_rgba(1, 1, 1, 0.85)
    ctx.set_line_width(5)
    ctx.stroke()
    for x0, x1 in ((-200, -40), (-20, 120), (140, 285)):
        ctx.move_to(x0 + 10, -70)
        ctx.line_to(x0 + 20, -126)
        ctx.line_to(x1 - 10, -126)
        ctx.line_to(x1, -70)
        ctx.close_path()
        ctx.set_source_rgba(0.5, 0.6, 0.75, 0.35)
        ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.6)
        ctx.set_line_width(3)
        ctx.stroke()
    for xr in (-300, 300):
        ctx.arc(xr, 44, 58, 0, 2 * math.pi)
        ctx.set_source_rgb(*hx("#05070C"))
        ctx.fill_preserve()
        ctx.set_source_rgba(1, 1, 1, 0.85)
        ctx.set_line_width(5)
        ctx.stroke()
        ctx.arc(xr, 44, 22, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.5)
        ctx.fill()
    for xf in (-80, 160):
        ctx.move_to(xf, -126)
        ctx.line_to(xf, 30)
        ctx.set_source_rgba(1, 1, 1, 0.3)
        ctx.set_line_width(3)
        ctx.stroke()
    ctx.restore()


BLANCO_BALA = (720, 880)                 # donde estaba él (sin dibujarlo): un punto en el auto


def d_auto(ctx, t):
    fondo_serio(ctx, t)
    ctx.save()
    zz = 1 + 0.05 * prog(t, F5[0], 2.0)
    camara(ctx, 540, 960, zz)
    # suelo
    ctx.move_to(0, 1120)
    ctx.line_to(W, 1120)
    ctx.set_source_rgba(1, 1, 1, 0.25)
    ctx.set_line_width(4)
    ctx.stroke()
    limusina(ctx, 540, 1060, 1.0)
    choque = (690, 1000)
    # trayectoria de la bala
    if t >= T_BALA - 0.1:
        q = prog(t, T_BALA - 0.1, T_REBO + 0.05 - T_BALA + 0.1)
        x0, y0 = -40, 820
        x1, y1 = lerp(x0, choque[0], q), lerp(y0, choque[1], q)
        ctx.set_dash([26, 18])
        ctx.move_to(x0, y0)
        ctx.line_to(x1, y1)
        ctx.set_source_rgb(*ROJO)
        ctx.set_line_width(8)
        ctx.stroke()
        ctx.set_dash([])
        if t >= T_REBO + 0.05:
            k = prog(t, T_REBO + 0.05, 0.35)
            ctx.set_dash([26, 18])
            ctx.move_to(*choque)
            ctx.line_to(lerp(choque[0], BLANCO_BALA[0], k), lerp(choque[1], BLANCO_BALA[1], k))
            ctx.set_source_rgb(*ROJO)
            ctx.set_line_width(8)
            ctx.stroke()
            ctx.set_dash([])
            # chispa del rebote
            q2 = clamp((t - T_REBO - 0.05) / 0.3)
            for j in range(8):
                ang = j * math.pi / 4
                ctx.move_to(choque[0] + math.cos(ang) * 18, choque[1] + math.sin(ang) * 18)
                ctx.line_to(choque[0] + math.cos(ang) * (18 + 60 * q2), choque[1] + math.sin(ang) * (18 + 60 * q2))
            ctx.set_source_rgba(1, 0.85, 0.4, 1 - q2)
            ctx.set_line_width(6)
            ctx.stroke()
        if t >= T_REBO + 0.4:
            a = prog(t, T_REBO + 0.4, 0.2)
            for rr, al in ((40, 0.25), (22, 0.9)):
                ctx.arc(*BLANCO_BALA, rr, 0, 2 * math.pi)
                ctx.set_source_rgba(*ROJO, al * a)
                ctx.set_line_width(6)
                ctx.stroke()
    ctx.restore()
    if t >= T_AUTO - 0.1:
        maquina(ctx, "AUTO BLINDADO", 540, 1260, 42, t, T_AUTO - 0.1, cps=30, fill=GRIS_SERIO, cursor=False)
    grano(ctx, t)


ENTRADA = (300, 60)                      # por donde entró la bala (costado izquierdo de él)
BALA = (150, 72)                         # donde quedó, junto al corazón


def insp_serio(t):
    ciclos = [(0, 0.1, 0.35, 0.35)]
    # sigue respirando mientras el pulmón se desinfla
    k = T_PEC2 - 0.2
    while k < b(14):
        ciclos.append((k, k + 0.75, 0.0, 1.0))
        ciclos.append((k + 0.85, k + 1.5, 1.0, 0.0))
        k += 1.6
    k = T_VOLV - 0.3
    while k < TOTAL:
        ciclos.append((k, k + 0.8, 0.0, 1.0))
        ciclos.append((k + 0.9, k + 1.6, 1.0, 0.0))
        k += 1.7
    return respiracion(t, ciclos)


def colapso(t):
    c = 0.0
    c = max(c, 0.32 * prog(t, T_AIR2 - 0.2, 1.6))
    c = max(c, lerp(0.32, 0.55, prog(t, T_DESG, 0.6)) if t >= T_DESG else 0)
    c = max(c, lerp(0.55, 0.85, prog(t, T_DESI, 0.9)) if t >= T_DESI else 0)
    if t >= T_SACA:
        c = lerp(0.85, 0.0, prog(t, T_SACA + 0.3, T_PEG2 - T_SACA - 0.1, "inout"))
    return c


def nivel_sangre(t):
    """Altura (local) de la sangre acumulada abajo, entre las capas."""
    h = 80 * prog(t, T_SANG - 0.1, 2.5)
    if t >= T_SACA:
        h *= 1 - prog(t, T_SACA + 0.2, 1.8)
    return h


def cam_serio(t):
    kf = [(Z6[0], 150, 40, 1.12), (T_QUED - 0.1, 150, 40, 1.12), (T_CM - 0.1, 130, 90, 1.9),
          (T_CORA + 0.3, 130, 90, 1.9), (T_HERI, 170, 40, 1.35), (T_PEC2 - 0.2, 170, 40, 1.35),
          (T_PEC2 + 0.4, 0, -40, 1.0), (b(14), 0, -40, 1.0),
          (F8[0], 190, 120, 1.35), (T_VOLV - 0.3, 190, 120, 1.35), (T_PEG2 + 0.3, 0, -40, 1.0), (TOTAL + 1, 0, -40, 1.0)]
    for (t0, x0, y0, z0), (t1, x1, y1, z1) in zip(kf, kf[1:]):
        if t0 <= t < t1:
            q = ease((t - t0) / (t1 - t0), "inout")
            return lerp(x0, x1, q), lerp(y0, y1, q), lerp(z0, z1, q)
    return kf[-1][1:]


def d_torso_serio(ctx, t):
    fondo_serio(ctx, t)
    ins = insp_serio(t)
    col = colapso(t)
    lx, ly, z = cam_serio(t)
    fx, fy = tw(lx, ly)
    ctx.save()
    camara(ctx, fx, fy, z)
    ctx.save()
    ctx.translate(*TC)
    ctx.scale(TS, TS)
    silueta(ctx, True)
    traquea(ctx, True)
    corazon(ctx, t, True, latido=1.6 if T_CORA - 0.2 <= t < T_CORA + 1.0 else 1.0)
    pulmon(ctx, "i", t, c=ins, e=ins, serio=True)
    # el espacio entre las capas del pulmón izquierdo de él (a la derecha de la pantalla)
    cav = puntos_pulmon("d", ins, ins)
    hx_, hy_ = HILIO["d"]
    cav = [(hx_ + (x - hx_) * 1.03, hy_ + (y - hy_) * 1.03) for x, y in cav]
    if col > 0.01 or nivel_sangre(t) > 0.5:
        curva_cerrada(ctx, cav)
        ctx.set_source_rgba(0.85, 0.92, 1, 0.22 * clamp(col * 3))
        ctx.fill()
        hs = nivel_sangre(t)
        if hs > 0.5:
            ctx.save()
            curva_cerrada(ctx, cav)
            ctx.clip()
            yfondo = max(y for _, y in cav)
            ctx.rectangle(-500, yfondo - hs + 4 * math.sin(t * 3), 1000, hs + 50)
            ctx.set_source_rgba(*SANGRE, 0.95)
            ctx.fill()
            ctx.restore()
        # burbujas de aire entrando por la herida
        if T_AIR2 - 0.3 <= t < T_SACA + 1.5:
            r = rng(31)
            for k in range(16):
                ph = r.uniform(0, 1)
                q = ((t - T_AIR2) * 0.7 + ph) % 1
                bx = lerp(ENTRADA[0] - 20, r.uniform(150, 270), q)
                by = lerp(ENTRADA[1], r.uniform(-260, 120), q)
                if t >= T_SACA:
                    q2 = prog(t, T_SACA, 1.4)
                    bx, by = lerp(bx, TUBO_IN[0], q2), lerp(by, TUBO_IN[1], q2)
                ctx.arc(bx, by, 8 + 4 * math.sin(k), 0, 2 * math.pi)
                ctx.set_source_rgba(1, 1, 1, 0.55 * clamp(col * 4))
                ctx.set_line_width(3)
                ctx.stroke()
    pulmon(ctx, "d", t, c=ins * (1 - col), e=ins * (1 - col), col=col, serio=True,
           alarma=clamp(col * 1.6) * (0.75 + 0.25 * math.sin(t * 6)) if t < T_VOLV else clamp(col * 1.6))
    # la capa de afuera
    pegado = prog(t, T_PEG2 - 0.1, 0.3)
    for lado in ("i", "d"):
        sep = col if lado == "d" else 0.0
        pleura(ctx, lado, ins, ins, t, col_brillo=mezcla(mezcla(CIAN, ROJO, clamp(sep * 2)), VERDE_OK,
                                                          pegado if lado == "d" else 0), a=0.9)
    aire(ctx, ins * 3, (insp_serio(t + 0.04) - insp_serio(t - 0.04)) / 0.08 * 0.6, t, serio=True, a=0.6)
    diafragma(ctx, ins, t, serio=True, a=0.9)
    costillas(ctx, ins, True)
    # la bala
    if t >= T_ATRA - 0.05:
        q = prog(t, T_ATRA - 0.05, 0.55, "out")
        bx, by = lerp(ENTRADA[0] + 160, BALA[0], q), lerp(ENTRADA[1] - 30, BALA[1], q)
        ctx.set_dash([18 / TS * 1.4, 12 / TS * 1.4])
        ctx.move_to(ENTRADA[0] + 160, ENTRADA[1] - 30)
        ctx.line_to(bx, by)
        ctx.set_source_rgba(*ROJO, 0.9 * (1 - prog(t, T_HERI, 0.6)))
        ctx.set_line_width(6 / TS)
        ctx.stroke()
        ctx.set_dash([])
        ctx.save()
        ctx.translate(bx, by)
        ctx.rotate(math.atan2(BALA[1] - ENTRADA[1] + 30, BALA[0] - ENTRADA[0] - 160))
        rrect(ctx, -16, -8, 32, 16, 8)
        ctx.set_source_rgb(*hx("#B8BCC4"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(2)
        ctx.stroke()
        ctx.restore()
        # la herida
        ctx.arc(ENTRADA[0] + 95, ENTRADA[1] - 12, 9, 0, 2 * math.pi)
        ctx.set_source_rgba(*ROJO, 0.9)
        ctx.fill()
    # la medida
    if T_CM - 0.1 <= t < T_HERI:
        a = prog(t, T_CM - 0.1, 0.25) * (1 - prog(t, T_HERI - 0.3, 0.3))
        x0, x1 = 112, BALA[0] - 16
        ctx.move_to(x0, BALA[1] - 34)
        ctx.line_to(x0, BALA[1] - 46)
        ctx.line_to(x1, BALA[1] - 46)
        ctx.line_to(x1, BALA[1] - 34)
        ctx.set_source_rgba(1, 1, 1, a)
        ctx.set_line_width(2.5)
        ctx.stroke()
        texto(ctx, "2,5 cm", (x0 + x1) / 2, BALA[1] - 72, 22, fill=BLANCO, stroke=INK, sw=1.5, fam=MONO, bold=True,
              alpha=a)
    # el tubo
    tubo(ctx, t)
    ctx.restore()
    ctx.restore()
    # textos sobrios
    if T_AIR2 - 0.05 <= t < T_DESG + 0.3:
        rotulo(ctx, "AIRE", 300, 300, 44, BLANCO, t, T_AIR2 - 0.05, T_DESG)
        rotulo(ctx, "SANGRE", 760, 300, 44, hx("#FF6A78"), t, T_SANG - 0.05, T_DESG)
    if T_ESE - 0.1 <= t < b(14):
        rotulo(ctx, "ESE PULMÓN NO SE INFLA", 540, 250, 44, hx("#FF6A78"), t, T_ESE - 0.1)
    if t >= T_VOLV:
        rotulo(ctx, "SE VUELVE A PEGAR", 540, 250, 48, hx("#6BE38A"), t, T_VOLV)
    grano(ctx, t)


TUBO_IN = (232, 196)                     # punta del tubo, dentro del espacio entre las capas
TUBO_OUT = (520, 380)                    # afuera del pecho, hacia el frasco


def tubo(ctx, t):
    if t < T_TUBO - 0.1:
        return
    q = prog(t, T_TUBO - 0.1, 0.8, "out")
    x0, y0 = TUBO_OUT
    x1, y1 = lerp(x0, TUBO_IN[0], q), lerp(y0, TUBO_IN[1], q)
    ctx.move_to(x0 + 200, y0 + 200)
    ctx.curve_to(x0 + 60, y0 + 80, x0, y0, x0, y0)
    ctx.line_to(x1, y1)
    path = ctx.copy_path()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(1, 1, 1, 0.95)
    ctx.set_line_width(30 / TS)
    ctx.stroke()
    ctx.append_path(path)
    ctx.set_source_rgba(0.15, 0.2, 0.3, 1)
    ctx.set_line_width(18 / TS)
    ctx.stroke()
    # lo que sale por el tubo
    if t >= T_SACA:
        a = 1 - prog(t, T_VOLV + 0.2, 0.4)
        for k in range(12):
            u = ((t - T_SACA) * 0.8 + k / 12) % 1
            px, py = lerp(TUBO_IN[0], x0, u), lerp(TUBO_IN[1], y0, u)
            if u > 0.999:
                continue
            col = SANGRE if k % 3 else (1, 1, 1)
            ctx.arc(px, py, 6, 0, 2 * math.pi)
            ctx.set_source_rgba(*col, 0.95 * a)
            ctx.fill()
    if T_COST - 0.1 <= t < T_SACA + 0.4:
        a = prog(t, T_COST - 0.1, 0.2) * (1 - prog(t, T_SACA + 0.1, 0.3))
        for yy in (172, 236):
            ctx.move_to(240, yy)
            ctx.line_to(330, yy + 16)
            ctx.set_source_rgba(1, 0.95, 0.6, 0.85 * a)
            ctx.set_line_width(10 / TS)
            ctx.stroke()


# ------------------------------------------------------------------ 5. el hospital: solo las huellas
def huella(ctx, x, y, s, rot, a, lado=1, rodilla=False):
    if a <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s * lado, s)
    ctx.set_source_rgba(0.92, 0.95, 1, 0.85 * a)
    if rodilla:
        # rodilla, canilla y la punta del pie: la marca de alguien arrodillado
        ctx.arc(0, 0, 36, 0, 2 * math.pi)
        ctx.fill()
        rrect(ctx, -22, 20, 44, 170, 22)
        ctx.fill()
        for dx in (-12, 0, 12):
            ctx.arc(dx, 214, 8, 0, 2 * math.pi)
            ctx.fill()
    else:
        ctx.save()
        ctx.scale(0.62, 1)
        ctx.arc(0, -10, 42, 0, 2 * math.pi)
        ctx.restore()
        ctx.fill()
        ctx.save()
        ctx.scale(0.55, 0.6)
        ctx.arc(-4, 70, 40, 0, 2 * math.pi)
        ctx.restore()
        ctx.fill()
        for k, (dx, dy, r) in enumerate(((-16, -62, 9), (-2, -66, 8), (11, -63, 7), (21, -56, 6), (28, -46, 5))):
            ctx.arc(dx, dy, r, 0, 2 * math.pi)
            ctx.fill()
    ctx.restore()


PASOS = [(500, 1360, 0.0), (580, 1230, 0.0), (505, 1100, 0.0), (575, 975, 0.0), (500, 860, 0.05),
         (585, 770, 0.18), (515, 690, 0.32), (570, 640, 0.5)]
PARED_Y = 1160


def d_hospital(ctx, t):
    fondo_serio(ctx, t)
    caida = prog(t, T_CAYO, 0.2, "in")
    sac = 16 * math.sin(t * 70) * (1 - clamp((t - T_CAYO - 0.05) / 0.5)) if t >= T_CAYO else 0.0
    ctx.save()
    zz = 1 + 0.06 * prog(t, F7[0], 3.5)
    camara(ctx, 540, 960, zz, 540 + sac, 960)
    # adentro (piso del hospital) y afuera (vereda)
    ctx.rectangle(-200, -200, 1480, PARED_Y + 200)
    ctx.set_source_rgba(0.75, 0.82, 0.95, 0.07)
    ctx.fill()
    for y in range(PARED_Y - 120, -200, -120):
        ctx.move_to(-200, y)
        ctx.line_to(1280, y)
        ctx.set_source_rgba(1, 1, 1, 0.05)
        ctx.set_line_width(2)
        ctx.stroke()
    for x in range(0, 1081, 120):
        ctx.move_to(x, -200)
        ctx.line_to(x, PARED_Y)
        ctx.set_source_rgba(1, 1, 1, 0.05)
        ctx.set_line_width(2)
        ctx.stroke()
    # pared con la puerta
    ab = prog(t, T_CAMI + 0.25, 0.5)
    for x0, x1 in ((-200, 380), (700, 1280)):
        ctx.rectangle(x0, PARED_Y - 14, x1 - x0, 28)
        ctx.set_source_rgba(*GRIS_SERIO, 0.9)
        ctx.fill()
    for sg in (-1, 1):
        x = 540 + sg * (80 + 150 * ab)
        ctx.rectangle(x - 80, PARED_Y - 6, 160, 12)
        ctx.set_source_rgba(0.55, 0.75, 0.95, 0.9)
        ctx.fill()
    maquina(ctx, "HOSPITAL", 540, 230, 60, t, F7[0] + 0.15, cps=20, bold=True, cursor=False, fill=GRIS_SERIO)
    maquina(ctx, "ENTRADA DE", 200, PARED_Y + 62, 30, t, F7[0] + 0.4, cps=30, cursor=False, fill=(0.6, 0.66, 0.78))
    maquina(ctx, "EMERGENCIAS", 200, PARED_Y + 104, 30, t, F7[0] + 0.7, cps=30, cursor=False, fill=(0.6, 0.66, 0.78))
    # las huellas: él no aparece, solo sus pasos
    t0 = T_CAMI - 0.1
    for i, (x, y, tambalea) in enumerate(PASOS):
        tt = t0 + i * 0.3 + 0.1 * max(0, i - 4) ** 1.3
        if t >= tt:
            lado = 1 if i % 2 else -1
            huella(ctx, x, y, 0.95, lado * (0.08 + 0.4 * tambalea), pop(t, tt, 0.12), lado=lado)
    if t >= T_CAYO:
        for sg in (-1, 1):
            huella(ctx, 540 + sg * 52, 400, 0.95, sg * 0.06, pop(t, T_CAYO, 0.15), rodilla=True)
    ctx.restore()
    if t >= T_SINP:
        g = cairo.RadialGradient(540, 860, lerp(800, 300, prog(t, T_SINP, 1.0)), 540, 860, 1250)
        g.add_color_stop_rgba(0, 0, 0, 0, 0)
        g.add_color_stop_rgba(1, 0, 0, 0, 0.85)
        ctx.set_source(g)
        ctx.paint()
    if caida > 0:
        ctx.rectangle(0, 0, W, H)
        ctx.set_source_rgba(0, 0, 0, 0.45 * prog(t, T_CAYO + 0.35, 0.5))
        ctx.fill()
    grano(ctx, t)


# ------------------------------------------------------------------ composición
def fundido(ctx, q, A, tA, B, tB, negro=False):
    if not negro:
        A(ctx, tA)
        capa(ctx, B, tB, alpha=ease(q, "inout"))
        return
    if q < 0.5:
        A(ctx, tA)
        ctx.rectangle(0, 0, W, H)
        ctx.set_source_rgba(0, 0, 0, ease(q * 2, "in"))
        ctx.fill()
    else:
        B(ctx, tB)
        ctx.rectangle(0, 0, W, H)
        ctx.set_source_rgba(0, 0, 0, 1 - ease((q - 0.5) * 2, "out"))
        ctx.fill()


def componer(ctx, t):
    def tr(T):
        return clamp((t - T[0]) / T[1])
    if t < Z1[0]:
        d_gancho(ctx, t)
    elif t < sum(Z1):
        zoom_entre(ctx, tr(Z1), d_gancho, t, CAMISA, d_torso, t, (540, 900), ZG)
    elif t < Z2[0]:
        d_torso(ctx, t)
    elif t < sum(Z2):
        zoom_entre(ctx, tr(Z2), d_torso, t, APEX, d_capas, t, CAPAS_C, 9.0)
    elif t < Z3[0]:
        d_capas(ctx, t)
    elif t < sum(Z3):
        zoom_entre(ctx, 1 - tr(Z3), d_torso, t, APEX, d_capas, t, CAPAS_C, 9.0, a0=0.45, a1=0.85)
    elif t < F4[0]:
        d_torso(ctx, t)
    elif t < sum(F4):
        fundido(ctx, tr(F4), d_torso, t, d_1981, t, negro=True)
    elif t < F5[0]:
        d_1981(ctx, t)
    elif t < sum(F5):
        fundido(ctx, tr(F5), d_1981, t, d_auto, t)
    elif t < Z6[0]:
        d_auto(ctx, t)
    elif t < sum(Z6):
        zoom_entre(ctx, tr(Z6), d_auto, t, BLANCO_BALA, d_torso_serio, t, tw(*ENTRADA), 6.0)
    elif t < F7[0]:
        d_torso_serio(ctx, t)
    elif t < sum(F7):
        fundido(ctx, tr(F7), d_torso_serio, t, d_hospital, t, negro=True)
    elif t < F8[0]:
        d_hospital(ctx, t)
    elif t < sum(F8):
        fundido(ctx, tr(F8), d_hospital, t, d_torso_serio, t, negro=True)
    else:
        d_torso_serio(ctx, t)


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
def _env(n, a=0.005, r=0.05):
    e = np.ones(n, np.float32)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def _ruido(n, seed, suave=1):
    x = np.random.default_rng(seed).standard_normal(n).astype(np.float32)
    if suave > 1:
        x = np.convolve(x, np.ones(suave) / suave, mode="same").astype(np.float32)
    return x


def s_respira(d=1.0, sube=True, seed=1):
    """Aire que entra (sube = True) o sale: ruido filtrado con forma de soplido."""
    n = int(d * SR)
    t = np.arange(n) / SR
    x = _ruido(n, seed, 6) - 0.6 * _ruido(n, seed + 1, 40)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** (1.4 if sube else 0.8)
    return (x * env * 0.9).astype(np.float32)


def s_latido():
    out = np.zeros(int(0.7 * SR), np.float32)
    for i0, a in ((0, 1.0), (int(0.22 * SR), 0.7)):
        t = np.arange(int(0.18 * SR)) / SR
        out[i0:i0 + len(t)] += (np.sin(2 * np.pi * 55 * t) * np.exp(-t * 26) * a).astype(np.float32)
    return out * 0.9


def s_disparo():
    """Disparo apagado y lejano, con eco."""
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    x = _ruido(n, 7, 3) * np.exp(-t * 30) * 0.9
    x += np.sin(2 * np.pi * 70 * t) * np.exp(-t * 9) * 0.6
    eco = np.zeros(n, np.float32)
    k = int(0.18 * SR)
    eco[k:] = x[:-k] * 0.35
    return (x + eco).astype(np.float32)


def s_rebote():
    t = np.arange(int(0.6 * SR)) / SR
    f = 3400 * np.exp(-t * 2.2) + 900
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * 0.45).astype(np.float32)


def s_dron(d=3.0, f=55):
    n = int(d * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) * 0.5 + np.sin(2 * np.pi * f * 1.5 * t) * 0.25
    x *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.3 * t)
    return (x * 0.5 * _env(n, 0.8, 1.0)).astype(np.float32)


def s_burbujas(d=1.5, seed=3):
    n = int(d * SR)
    out = np.zeros(n, np.float32)
    r = np.random.default_rng(seed)
    for _ in range(int(d * 14)):
        i0 = r.integers(0, max(1, n - 4000))
        tt = np.arange(4000) / SR
        f = r.uniform(500, 1100) * (1 + tt * 6)
        out[i0:i0 + 4000] += (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 40) * 0.35).astype(np.float32)
    return out


def s_desinfla(d=1.0):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = 520 * np.exp(-t * 1.6) + 90
    tono = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 31 * t)))
    return (tono * 0.22 * _env(n, 0.02, 0.2) + _ruido(n, 5, 3) * 0.12 * _env(n, 0.02, 0.3)).astype(np.float32)


def s_desliza(d=0.6):
    n = int(d * SR)
    t = np.arange(n) / SR
    x = _ruido(n, 9, 2) * (0.6 + 0.4 * np.sin(2 * np.pi * 40 * t))
    return (x * 0.3 * _env(n, 0.05, 0.2)).astype(np.float32)


def s_cruje(d=0.5):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = 160 + 60 * np.sin(2 * np.pi * 3 * t)
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * (np.random.default_rng(2).random(n) > 0.6)
    return (x * 0.25 * _env(n, 0.05, 0.15)).astype(np.float32)


def s_paso(seed=1):
    t = np.arange(int(0.16 * SR)) / SR
    x = _ruido(len(t), seed, 8) * np.exp(-t * 40) * 0.8 + np.sin(2 * np.pi * 90 * t) * np.exp(-t * 30) * 0.5
    return x.astype(np.float32)


def s_vidrio():
    t = np.arange(int(0.6 * SR)) / SR
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * k) * a for f, k, a in ((2650, 7, 0.4), (3970, 9, 0.25),
                                                                             (5300, 12, 0.15)))
    return x.astype(np.float32)


def sonido(kind, **kw):
    f = {"respira": s_respira, "latido": s_latido, "disparo": s_disparo, "rebote": s_rebote, "dron": s_dron,
         "burbujas": s_burbujas, "desinfla": s_desinfla, "desliza": s_desliza, "cruje": s_cruje, "paso": s_paso,
         "vidrio": s_vidrio}.get(kind)
    if f:
        return f(**kw)
    return K.snd(kind, **kw)


def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    # gancho
    ev(0.0, "respira", 0.7, d=0.9)
    ev(Z1[0], "zoom", 0.8)
    ev(T_RESP - 0.1, "cruje", 0.5, d=0.8)
    ev(T_MUSC - 0.1, "pop", 0.7)
    ev(T_MUSC + 0.15, "boing", 0.6)
    ev(T_INFL, "desinfla", 0.4, d=0.6)
    # diafragma y jeringa
    ev(T_DIAF - 0.15, "pop", 0.8)
    ev(T_MUS2, "golpe", 0.4)
    ev(T_CONT + 0.1, "respira", 0.8, d=1.2, seed=2)
    ev(T_EMBO - 0.3, "pop", 0.6)
    ev(T_EMBO - 0.35, "respira", 0.5, d=0.45, sube=False, seed=3)
    ev(T_EMBO + 0.15, "respira", 0.8, d=0.95, seed=4)
    ev(T_EMBO + 0.15, "desliza", 0.5, d=0.8)
    ev(T_ARRA, "pop", 0.7)
    ev(T_ARRA + 0.05, "respira", 0.7, d=0.9, seed=5)
    # las capas
    ev(Z2[0], "zoom", 0.8)
    ev(T_ENVU, "whoosh_suave", 0.5)
    ev(T_DOS, "tick", 0.4, f=1500, d=0.05)
    ev(T_CAPA, "pop", 0.7)
    ev(T_LIQU, "plop", 0.6)
    ev(T_LIQU + 0.05, "burbujas", 0.4, d=0.6)
    ev(T_VIDR - 0.2, "vidrio", 0.7)
    ev(T_MOJA - 0.3, "plop", 0.4)
    ev(T_MOJA - 0.1, "plop", 0.35)
    ev(T_DESL - 0.05, "desliza", 0.8, d=0.9)
    ev(T_SEPA - 0.25, "cruje", 0.7, d=0.6)
    ev(T_SEPA + 0.6, "boing", 0.6)
    # el pecho se agranda
    ev(Z3[0], "whoosh", 0.7)
    ev(T_PECH, "respira", 0.8, d=1.3, seed=6)
    ev(T_AIRE - 0.3, "respira", 1.0, d=1.2, seed=7)
    ev(T_PROB, "dron", 0.5, d=3.2, f=49)
    ev(T_DESP, "desliza", 0.6, d=0.5)
    ev(T_DESP + 0.1, "latido", 0.6)
    # Reagan
    ev(T_1981 - 0.1, "dron", 0.45, d=21.0, f=41)
    for k in range(4):
        ev(T_1981 - 0.1 + k * 0.11, "tick", 0.5, f=2200, d=0.04)
    for k in range(14):
        ev(T_1981 + 0.7 + k * 0.08, "tick", 0.15, f=2600, d=0.03)
    ev(T_DISP, "disparo", 0.9)
    for k in range(14):
        ev(T_PRES - 0.05 + k * 0.07, "tick", 0.15, f=2600, d=0.03)
    ev(T_REBO + 0.05, "rebote", 0.7)
    ev(Z6[0], "whoosh", 0.6)
    for k in range(int((b(14) - T_ATRA) / 0.8)):
        ev(T_ATRA + k * 0.8, "latido", 0.55 if T_CORA - 0.3 <= T_ATRA + k * 0.8 < T_CORA + 1.0 else 0.3)
    ev(T_CM - 0.1, "tick", 0.5, f=1800, d=0.05)
    ev(T_AIR2 - 0.2, "burbujas", 0.5, d=1.8)
    ev(T_DESG, "desliza", 0.6, d=0.6)
    ev(T_DESI, "desinfla", 0.7, d=1.1)
    for k in range(3):
        ev(T_PEC2 - 0.2 + k * 1.6, "respira", 0.4, d=0.75, seed=10 + k)
    for k in range(10):
        ev(T_ESE - 0.1 + k * 0.05, "tick", 0.12, f=2400, d=0.03)
    # hospital
    for i in range(len(PASOS)):
        tt = T_CAMI - 0.1 + i * 0.3 + 0.1 * max(0, i - 4) ** 1.3
        ev(tt, "paso", 0.5 - 0.03 * i, seed=i)
    ev(T_SINP, "respira", 0.6, d=0.5, seed=21)
    ev(T_CAYO, "golpe", 0.9)
    # el tubo
    ev(F8[0], "dron", 0.35, d=TOTAL - F8[0], f=46)
    ev(T_TUBO - 0.1, "whoosh_suave", 0.6)
    ev(T_SACA, "burbujas", 0.6, d=2.2, seed=5)
    ev(T_VOLV - 0.3, "respira", 0.8, d=0.8, seed=30)
    ev(T_PEG2, "ding", 0.7)
    ev(T_PEG2 + 0.5, "respira", 0.6, d=0.8, seed=31)
    return E


def pista_efectos():
    n = int((TOTAL + 25) * SR)
    mix = np.zeros(n, np.float32)
    for t, k, v, kw in eventos():
        x = sonido(k, **kw) * v
        i0 = int(t * SR)
        i1 = min(n, i0 + len(x))
        if 0 <= i0 < n:
            mix[i0:i1] += x[:i1 - i0]
    mix = mix[:int((TOTAL + 1) * SR)]
    mix *= 0.55 / (np.abs(mix).max() or 1)
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
                    "-filter_complex", "[1:a][2:a]amix=inputs=2:normalize=0:duration=longest,"
                    "alimiter=limit=0.89:level=false[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", salida],
                   check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fotos")
    ap.add_argument("--dir", default=os.path.join(AQUI, "fotos"))
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "tus_pulmones.mp4"))
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

"""Recursos del short "¿Por qué hay tanta agua en la Tierra?".

Se importa desde kit.py (build_agua) y usa la misma guía de estilo.
"""
import math
import random

from kit import INK, SW, P, W, H, add, ln, stroke_path, estrella4, vos, sol

AGUA = "#4FA8FF"
AGUA2 = "#2F7FD8"
TIERRA_VERDE = "#5CC46B"

# Tablero de sospechosos: centro de cada foto (lienzo 1080x1920) y su chinche
TABLERO = {1: (265, 640), 2: (815, 640), 3: (540, 1060)}
FOTO_W, FOTO_H = 320, 380
PIN_DY = -160          # chinche respecto del centro de la foto


# ---------------------------------------------------------------- caritas genéricas
def ojos(cx, cy, sep, kind="open", r=1.0, look=(0, 0)):
    """Par de ojos centrados en (cx, cy)."""
    s = []
    for x in (cx - sep / 2, cx + sep / 2):
        if kind in ("open", "wide"):
            rx, ry, pr = (24 * r, 28 * r, 11 * r) if kind == "open" else (30 * r, 34 * r, 8 * r)
            px, py = x + look[0] * 9 * r, cy + look[1] * 9 * r + 3 * r
            s.append(f'<ellipse cx="{x:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="#fff" stroke="{INK}" stroke-width="{5*r:.1f}"/>'
                     f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{pr:.1f}" fill="{INK}"/>'
                     f'<circle cx="{px-pr*.35:.1f}" cy="{py-pr*.4:.1f}" r="{max(2.5, pr*.32):.1f}" fill="#fff"/>')
        elif kind == "happy":
            s.append(ln(f"M {x-20*r:.1f} {cy+8*r:.1f} Q {x:.1f} {cy-16*r:.1f} {x+20*r:.1f} {cy+8*r:.1f}", 7 * r))
        elif kind == "closed":
            s.append(ln(f"M {x-20*r:.1f} {cy:.1f} Q {x:.1f} {cy+10*r:.1f} {x+20*r:.1f} {cy:.1f}", 7 * r))
        elif kind == "dot":
            s.append(f'<circle cx="{x:.1f}" cy="{cy:.1f}" r="{9*r:.1f}" fill="{INK}"/>')
        elif kind == "squint":
            s.append(ln(f"M {x-20*r:.1f} {cy-8*r:.1f} L {x+18*r:.1f} {cy:.1f} L {x-20*r:.1f} {cy+8*r:.1f}", 7 * r))
    return "".join(s)


def boca(cx, cy, kind="smile", r=1.0):
    if kind == "smile":
        return ln(f"M {cx-26*r:.1f} {cy:.1f} Q {cx:.1f} {cy+24*r:.1f} {cx+26*r:.1f} {cy:.1f}", 7 * r)
    if kind == "grin":
        d = f"M {cx-32*r:.1f} {cy-4*r:.1f} Q {cx:.1f} {cy+44*r:.1f} {cx+32*r:.1f} {cy-4*r:.1f} Z"
        return (ln(d, 6 * r, INK, P["boca"])
                + f'<ellipse cx="{cx:.1f}" cy="{cy+18*r:.1f}" rx="{14*r:.1f}" ry="{6*r:.1f}" fill="{P["lengua"]}"/>' + ln(d, 6 * r))
    if kind == "o":
        return f'<ellipse cx="{cx:.1f}" cy="{cy+6*r:.1f}" rx="{13*r:.1f}" ry="{17*r:.1f}" fill="{P["boca"]}" stroke="{INK}" stroke-width="{6*r:.1f}"/>'
    if kind == "flat":
        return ln(f"M {cx-20*r:.1f} {cy+6*r:.1f} L {cx+20*r:.1f} {cy+6*r:.1f}", 7 * r)
    if kind == "sad":
        return ln(f"M {cx-22*r:.1f} {cy+14*r:.1f} Q {cx:.1f} {cy-6*r:.1f} {cx+22*r:.1f} {cy+14*r:.1f}", 7 * r)
    if kind == "wavy":
        return ln(f"M {cx-28*r:.1f} {cy+6*r:.1f} Q {cx-14*r:.1f} {cy-6*r:.1f} {cx:.1f} {cy+6*r:.1f} "
                  f"Q {cx+14*r:.1f} {cy+18*r:.1f} {cx+28*r:.1f} {cy+6*r:.1f}", 7 * r)
    if kind == "grumpy":
        return ln(f"M {cx-22*r:.1f} {cy+12*r:.1f} Q {cx:.1f} {cy+2*r:.1f} {cx+22*r:.1f} {cy+12*r:.1f}", 7 * r)
    raise ValueError(kind)


def cejas(cx, cy, sep, kind, r=1.0):
    a, b = cx - sep / 2, cx + sep / 2
    if kind == "worried":
        return (ln(f"M {a-20*r:.1f} {cy+4*r:.1f} L {a+18*r:.1f} {cy-8*r:.1f}", 7 * r)
                + ln(f"M {b-18*r:.1f} {cy-8*r:.1f} L {b+20*r:.1f} {cy+4*r:.1f}", 7 * r))
    if kind == "angry":
        return (ln(f"M {a-20*r:.1f} {cy-8*r:.1f} L {a+18*r:.1f} {cy+4*r:.1f}", 7 * r)
                + ln(f"M {b-18*r:.1f} {cy+4*r:.1f} L {b+20*r:.1f} {cy-8*r:.1f}", 7 * r))
    if kind == "up":
        return (ln(f"M {a-18*r:.1f} {cy:.1f} Q {a:.1f} {cy-14*r:.1f} {a+18*r:.1f} {cy:.1f}", 7 * r)
                + ln(f"M {b-18*r:.1f} {cy:.1f} Q {b:.1f} {cy-14*r:.1f} {b+18*r:.1f} {cy:.1f}", 7 * r))
    return ""


def mejillas(cx, cy, sep, r=1.0):
    return "".join(f'<ellipse cx="{x:.1f}" cy="{cy:.1f}" rx="{18*r:.1f}" ry="{10*r:.1f}" fill="{P["rosa"]}" opacity=".55"/>'
                   for x in (cx - sep / 2, cx + sep / 2))


def gotita_sudor(x, y, r=1.0):
    d = (f"M {x:.1f} {y:.1f} C {x:.1f} {y:.1f} {x+16*r:.1f} {y+22*r:.1f} {x+16*r:.1f} {y+32*r:.1f} "
         f"A {16*r:.1f} {16*r:.1f} 0 0 1 {x-16*r:.1f} {y+32*r:.1f} C {x-16*r:.1f} {y+22*r:.1f} {x:.1f} {y:.1f} {x:.1f} {y:.1f} Z")
    return ln(d, 5 * r, INK, "#BFEFFF")


# ---------------------------------------------------------------- fondos
def fondo_espacio():
    rnd = random.Random(21)
    s = [f'<rect width="{W}" height="{H}" fill="url(#esp)"/>',
         '<ellipse cx="160" cy="420" rx="460" ry="280" fill="#6A5BE0" opacity=".16"/>',
         '<ellipse cx="960" cy="1380" rx="480" ry="320" fill="#2F9BE0" opacity=".13"/>',
         '<ellipse cx="700" cy="760" rx="260" ry="160" fill="#C25BE0" opacity=".08"/>']
    for _ in range(150):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        r = rnd.choice([2, 2, 2, 3, 3, 4])
        s.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#FFFFFF" opacity="{rnd.uniform(.35, .9):.2f}"/>')
    for _ in range(16):
        s.append(estrella4(rnd.uniform(40, 1040), rnd.uniform(40, 1880), rnd.uniform(9, 18), "#FFE9A3", 0))
    defs = ('<linearGradient id="esp" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#12173F"/>'
            '<stop offset="1" stop-color="#26327A"/></linearGradient>')
    return "".join(s), defs


def fondo_corcho():
    rnd = random.Random(31)
    s = [f'<rect width="{W}" height="{H}" fill="#6B4430"/>']
    for y in range(0, H, 46):   # vetas de la madera del marco
        s.append(ln(f"M 0 {y} Q 540 {y + rnd.uniform(-14, 14):.0f} {W} {y}", 4, "#5A382A", extra='opacity=".6"'))
    s.append(f'<rect x="44" y="44" width="{W-88}" height="{H-88}" rx="16" fill="#CC955E" stroke="{INK}" stroke-width="{SW}"/>')
    s.append('<clipPath id="crk"><rect x="44" y="44" width="992" height="1832" rx="16"/></clipPath><g clip-path="url(#crk)">')
    for _ in range(1500):
        x, y = rnd.uniform(44, W - 44), rnd.uniform(44, H - 44)
        col = rnd.choice(["#B9804A", "#B9804A", "#DCA874", "#A86F3E"])
        s.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rnd.uniform(2, 6):.1f}" ry="{rnd.uniform(1.5, 4):.1f}" '
                 f'fill="{col}" opacity=".7"/>')
    s.append(f'<rect x="44" y="44" width="{W-88}" height="{H-88}" fill="url(#crkv)"/></g>')
    s.append(f'<rect x="44" y="44" width="{W-88}" height="{H-88}" rx="16" fill="none" stroke="{INK}" stroke-width="{SW}"/>')
    defs = ('<radialGradient id="crkv" cx="0.5" cy="0.45" r="0.75"><stop offset="0.6" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#4A2A14" stop-opacity="0.35"/></radialGradient>')
    return "".join(s), defs


def fondo_lab():
    s = [f'<rect width="{W}" height="{H}" fill="#DDF1EE"/>']
    for x in range(0, W + 1, 108):
        s.append(ln(f"M {x} 0 L {x} 1180", 4, "#C3E2DD"))
    for y in range(0, 1181, 108):
        s.append(ln(f"M 0 {y} L {W} {y}", 4, "#C3E2DD"))
    # estante con frascos (a la izquierda, fuera de la zona de carteles)
    s.append(f'<rect x="40" y="560" width="270" height="26" rx="8" fill="{P["marron"]}" stroke="{INK}" stroke-width="{SW}"/>')
    for (x, col, k) in [(95, P["verde"], 1.0), (172, P["rosa"], .8), (250, P["violeta"], 1.05)]:
        s.append(f'<g transform="translate({x} 560) scale({k})">'
                 + ln("M -26 0 L -26 -70 Q -26 -82 -14 -86 L -14 -110 L 14 -110 L 14 -86 Q 26 -82 26 -70 L 26 0 Z", 6, INK, "#F4FBFF")
                 + f'<rect x="-22" y="-44" width="44" height="40" fill="{col}" opacity=".85"/>'
                 + ln("M -26 0 L -26 -70 Q -26 -82 -14 -86 L -14 -110 L 14 -110 L 14 -86 Q 26 -82 26 -70 L 26 0 Z", 6) + '</g>')
    s.append(f'<rect x="0" y="1180" width="{W}" height="{H-1180}" fill="#8796AC"/>')
    s.append(f'<rect x="-10" y="1160" width="{W+20}" height="44" fill="#B8C4D4" stroke="{INK}" stroke-width="{SW}"/>')
    for x in range(60, W, 240):
        s.append(f'<rect x="{x}" y="1260" width="180" height="300" rx="14" fill="#7A889E" stroke="#6A778C" stroke-width="5"/>')
    return "".join(s), ""


# ---------------------------------------------------------------- Tierra con cara
CONTINENTES = [
    "M 80 130 Q 120 64 196 84 Q 236 116 200 160 Q 160 196 124 176 Q 72 166 80 130 Z",
    "M 252 70 Q 318 50 362 112 Q 372 156 330 166 Q 284 156 262 122 Z",
    "M 262 318 Q 316 280 362 312 Q 384 364 328 396 Q 270 398 254 352 Z",
    "M 46 262 Q 92 236 128 280 Q 140 336 96 360 Q 52 340 46 262 Z",
]


def tierra(tipo="normal", cara="smile"):
    cx, cy, r = 220, 220, 190
    base, tierra_c, extra = AGUA, TIERRA_VERDE, ""
    if tipo == "seca":
        base, tierra_c = "#D9A35F", "#B57A3C"
    if tipo == "lava":
        base, tierra_c = "#B7372A", "#6E2620"
    s = [f'<clipPath id="tc"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>',
         f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{base}"/>', '<g clip-path="url(#tc)">']
    for d in CONTINENTES:
        s.append(f'<path d="{d}" fill="{tierra_c}"/>')
    if tipo == "seca":
        for d in ["M 120 230 L 150 250 L 140 280 L 170 300", "M 300 200 L 280 230 L 310 250 L 300 280",
                  "M 200 360 L 230 380 L 220 410", "M 330 120 L 350 150", "M 90 330 L 120 350 L 110 380"]:
            s.append(ln(d, 6, "#8A5A2B"))
    if tipo == "lava":
        for d in ["M 40 200 L 120 230 L 160 200 L 230 240 L 300 210 L 400 250",
                  "M 90 110 L 150 140 L 200 120", "M 250 330 L 300 300 L 360 330",
                  "M 120 340 L 170 380 L 150 420", "M 330 140 L 380 120"]:
            s.append(ln(d, 16, "#FF8A2A") + ln(d, 7, "#FFD23F"))
    # sombra suave abajo a la derecha
    s.append(f'<circle cx="{cx+60}" cy="{cy+60}" r="{r}" fill="#000" opacity=".0"/>')
    s.append(f'<path d="M {cx+r} {cy} A {r} {r} 0 0 1 {cx} {cy+r} A {r*1.2} {r*1.2} 0 0 0 {cx+r} {cy} Z" fill="#000" opacity=".12"/>')
    s.append('</g>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{INK}" stroke-width="{SW+1}"/>')
    s.append(ln(f"M {cx-130} {cy-90} Q {cx-110} {cy-140} {cx-60} {cy-160}", 14, "#fff", extra='opacity=".45"'))
    fx, fy = cx, cy + 10
    if cara == "smile":
        s.append(ojos(fx, fy - 24, 100) + mejillas(fx, fy + 22, 170) + boca(fx, fy + 28))
    elif cara == "contenta":
        s.append(ojos(fx, fy - 20, 100, "happy") + mejillas(fx, fy + 22, 170) + boca(fx, fy + 24, "grin"))
    elif cara == "sorpresa":
        s.append(cejas(fx, fy - 80, 100, "up") + ojos(fx, fy - 24, 100, "wide") + boca(fx, fy + 30, "o"))
    elif cara == "triste":
        s.append(cejas(fx, fy - 70, 100, "worried") + ojos(fx, fy - 24, 100, "open", look=(0, .5)) + boca(fx, fy + 34, "sad"))
    elif cara == "agobiada":
        s.append(cejas(fx, fy - 68, 100, "worried") + ojos(fx, fy - 22, 100, "squint") + boca(fx, fy + 30, "wavy")
                 + gotita_sudor(cx + 128, cy - 110, 1.3) + gotita_sudor(cx - 140, cy - 60, 1.0))
    return "".join(s) + extra


# ---------------------------------------------------------------- hielo que se derrite
def hielo(p):
    """p=0 cubito entero, p=1 charquito."""
    s = []
    prx = 46 + 84 * p
    s.append(f'<ellipse cx="130" cy="236" rx="{prx:.1f}" ry="{10 + 10*p:.1f}" fill="{P["cielo"]}" stroke="{INK}" '
             f'stroke-width="{SW}" opacity="{min(1, .2 + p*1.4):.2f}"/>')
    h = 170 * (1 - p) ** 1.3 + 4
    if h > 12:
        w = 170 - 40 * p
        x0, y0 = 130 - w / 2, 238 - h
        rr = min(30, h / 2.2)
        s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rr:.1f}" fill="#CFF3FF" stroke="{INK}" stroke-width="{SW}"/>')
        s.append(ln(f"M {x0+18:.1f} {y0+16:.1f} L {x0+18:.1f} {y0+max(18, h*.45):.1f}", 9, "#fff", extra='opacity=".85"'))
        if h > 70:
            fy = y0 + h * .45
            s.append(ojos(130, fy, 60, "open" if p < .3 else "squint", .75) + boca(130, fy + 34, "o" if p < .3 else "wavy", .7))
        for k in range(int(p * 5)):
            s.append(gotita_sudor(130 + (k - 2) * 34, y0 - 30 - (k % 2) * 16, .7))
    return "".join(s)


def vapor(k=0):
    rnd = random.Random(40 + k)
    puffs = [(130 + rnd.uniform(-10, 10), 190, 48), (80, 150 + rnd.uniform(-8, 8), 42), (175, 140, 46),
             (125, 100 + rnd.uniform(-8, 8), 50), (95, 55, 34), (165, 60 + rnd.uniform(-6, 6), 30)]
    s = [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r+SW:.1f}" fill="{INK}"/>' for x, y, r in puffs]
    s += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#FFFFFF"/>' for x, y, r in puffs]
    s += [f'<circle cx="{x-r*.3:.1f}" cy="{y+r*.25:.1f}" r="{r*.55:.1f}" fill="#E3F4FF"/>' for x, y, r in puffs[:3]]
    return "".join(s)


# ---------------------------------------------------------------- tablero de sospechosos
def pregunta(cx, cy, k=1.0, color="#fff"):
    d = (f"M {cx-34*k:.1f} {cy-42*k:.1f} Q {cx-34*k:.1f} {cy-86*k:.1f} {cx:.1f} {cy-86*k:.1f} "
         f"Q {cx+38*k:.1f} {cy-86*k:.1f} {cx+38*k:.1f} {cy-48*k:.1f} Q {cx+38*k:.1f} {cy-20*k:.1f} {cx+4*k:.1f} {cy-2*k:.1f} "
         f"L {cx+4*k:.1f} {cy+18*k:.1f}")
    return (stroke_path(d, color, 22 * k, INK, 36 * k)
            + f'<circle cx="{cx+4*k:.1f}" cy="{cy+56*k:.1f}" r="{17*k:.1f}" fill="{color}" stroke="{INK}" stroke-width="{7*k:.1f}"/>')


def chinche(x, y):
    return (f'<circle cx="{x+3}" cy="{y+5}" r="17" fill="#000" opacity=".25"/>'
            f'<circle cx="{x}" cy="{y}" r="17" fill="{P["rojo"]}" stroke="{INK}" stroke-width="6"/>'
            f'<circle cx="{x-5}" cy="{y-5}" r="5" fill="#fff" opacity=".8"/>')


def foto(contenido, fondo="#1E2656", polvo=False, rot=0):
    """Polaroid de 320x380 con chinche arriba. `contenido` se dibuja en el recuadro (240x220)."""
    s = [f'<g transform="rotate({rot} 160 190)">',
         f'<rect x="28" y="40" width="280" height="330" rx="8" fill="#000" opacity=".22"/>',
         f'<rect x="20" y="30" width="280" height="330" rx="8" fill="#FFFDF7" stroke="{INK}" stroke-width="{SW}"/>',
         '<clipPath id="fc"><rect x="42" y="52" width="236" height="222"/></clipPath>',
         f'<rect x="42" y="52" width="236" height="222" fill="{fondo}"/>',
         f'<g clip-path="url(#fc)">{contenido}</g>',
         f'<rect x="42" y="52" width="236" height="222" fill="none" stroke="{INK}" stroke-width="5"/>']
    if polvo:
        rnd = random.Random(9)
        for _ in range(26):
            x, y = rnd.uniform(30, 290), rnd.uniform(40, 350)
            s.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rnd.uniform(18, 44):.0f}" ry="{rnd.uniform(12, 28):.0f}" '
                     f'fill="#B9B2AA" opacity=".55"/>')
        s.append(ln("M 24 34 Q 70 70 60 120 M 24 34 Q 80 50 120 44 M 24 34 L 90 96", 3, "#EEE", extra='opacity=".8"'))
    s.append('</g>')
    s.append(chinche(160, 30))
    return "".join(s)


def mini(asset_body, cx, cy, k, w, h):
    """Dibuja el cuerpo SVG de otro recurso centrado en (cx, cy) con escala k."""
    return f'<g transform="translate({cx} {cy}) scale({k}) translate({-w/2} {-h/2})">{asset_body}</g>'


def hilos():
    """Hilos rojos entre las chinches del tablero (lienzo completo)."""
    pins = {k: (x, y + PIN_DY) for k, (x, y) in TABLERO.items()}
    s = []
    for a, b in [(1, 2), (1, 3), (2, 3)]:
        (x0, y0), (x1, y1) = pins[a], pins[b]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + 40
        d = f"M {x0} {y0} Q {mx} {my} {x1} {y1}"
        s.append(ln(d, 10, "#7A1F1F", extra='opacity=".35" transform="translate(4 6)"'))
        s.append(ln(d, 8, "#E03A3A"))
    return "".join(s)


# ---------------------------------------------------------------- cometa, sonda, gotas, polvo
def cometa(cara="smile"):
    s = []
    for (dy, w, col, op) in [(0, 190, "#7FCBFF", .55), (-34, 110, "#BDEBFF", .75), (38, 90, "#BDEBFF", .7), (0, 70, "#fff", .85)]:
        d = f"M 420 {150-w/2+dy:.0f} Q 200 {150+dy*2:.0f} 10 {150+dy*2.4:.0f} Q 200 {150+dy*1.4:.0f} 420 {150+w/2+dy:.0f} Z"
        s.append(f'<path d="{d}" fill="{col}" opacity="{op}"/>')
    head = ("M 420 52 Q 474 50 504 92 Q 530 140 512 190 Q 490 244 428 248 Q 366 250 336 206 "
            "Q 314 160 334 110 Q 360 56 420 52 Z")
    s.append(ln(head, SW, INK, "#DCE5EE"))
    s.append(f'<clipPath id="ch"><path d="{head}"/></clipPath><g clip-path="url(#ch)">'
             + "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="#8E9AA8" opacity=".75"/>'
                       for x, y, rx, ry in [(470, 210, 30, 18), (352, 140, 18, 26), (500, 110, 14, 10), (380, 228, 22, 12)])
             + '</g>')
    s.append(ln("M 368 92 Q 390 70 420 66", 10, "#fff", extra='opacity=".85"'))
    if cara == "smile":
        s.append(ojos(426, 146, 66, "open", .85) + boca(426, 186, "smile", .8))
    else:
        s.append(cejas(426, 106, 66, "angry", .85) + ojos(426, 146, 66, "open", .85) + boca(426, 186, "grumpy", .8))
    return "".join(s)


def sonda():
    s = []
    for x in (14, 276):
        s.append(f'<rect x="{x}" y="86" width="130" height="68" rx="6" fill="#3D5A9E" stroke="{INK}" stroke-width="{SW}"/>')
        s += [ln(f"M {x+k*32.5:.1f} 86 L {x+k*32.5:.1f} 154", 4, "#6F8FD0") for k in (1, 2, 3)]
        s.append(ln(f"M {x} 120 L {x+130} 120", 4, "#6F8FD0"))
    s.append(ln("M 144 120 L 160 120 M 260 120 L 276 120", 10))
    s.append(f'<rect x="150" y="62" width="120" height="116" rx="14" fill="#F2C14E" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 166 86 L 196 116 M 236 76 L 254 100", 6, "#FFE3A0"))
    s.append(ln("M 210 62 L 210 34", 8))
    s.append(ln("M 172 34 Q 210 4 248 34 Z", 6, INK, "#E8EEF5"))
    s.append(f'<circle cx="210" cy="198" r="16" fill="#9AA6B8" stroke="{INK}" stroke-width="6"/>')
    return "".join(s)


GOTA = "M 90 15 C 90 15 165 120 165 160 A 75 75 0 0 1 15 160 C 15 120 90 15 90 15 Z"


def gota(color=AGUA, cara="smile"):
    s = [ln(GOTA, 8, INK, color), ln("M 52 132 Q 52 104 70 84", 10, "#fff", extra='opacity=".7"')]
    if cara == "smile":
        s.append(ojos(90, 158, 46, "dot") + boca(90, 186, "smile", .65))
    elif cara == "feliz":
        s.append(ojos(90, 156, 50, "happy", .75) + boca(90, 178, "grin", .6))
    elif cara == "enojada":
        s.append(cejas(90, 136, 50, "angry", .6) + ojos(90, 160, 46, "dot") + boca(90, 192, "grumpy", .65))
    return "".join(s)


def nube_polvo():
    puffs = [(120, 160, 70), (210, 120, 80), (300, 160, 66), (180, 200, 58), (260, 205, 56), (360, 190, 42), (60, 196, 40)]
    s = [f'<circle cx="{x}" cy="{y}" r="{r+SW}" fill="{INK}"/>' for x, y, r in puffs]
    s += [f'<circle cx="{x}" cy="{y}" r="{r}" fill="#B3ACA4"/>' for x, y, r in puffs]
    s += [f'<circle cx="{x-r*.25:.0f}" cy="{y-r*.3:.0f}" r="{r*.45:.0f}" fill="#CFC9C2"/>' for x, y, r in puffs[:4]]
    rnd = random.Random(4)
    s += [f'<circle cx="{rnd.uniform(60, 360):.0f}" cy="{rnd.uniform(120, 230):.0f}" r="{rnd.uniform(3, 7):.0f}" fill="#8C847B"/>'
          for _ in range(16)]
    return "".join(s)


# ---------------------------------------------------------------- asteroides y Luna
ROCA_AST = ("M 70 120 Q 60 60 130 46 Q 190 20 250 52 Q 316 70 312 140 Q 330 210 270 248 "
            "Q 200 284 130 262 Q 50 240 52 180 Q 44 150 70 120 Z")


def asteroide(cara="smile"):
    s = [ln(ROCA_AST, SW, INK, "#A08C78"),
         f'<clipPath id="ac"><path d="{ROCA_AST}"/></clipPath><g clip-path="url(#ac)">'
         f'<path d="M 200 290 Q 330 260 330 120 L 340 300 Z" fill="#000" opacity=".12"/>']
    for x, y, r in [(110, 90, 24), (268, 96, 18), (240, 232, 26), (96, 212, 16), (290, 186, 12)]:
        s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#86735F" stroke="#6E5D4C" stroke-width="5"/>')
    s.append('</g>')
    s.append(ln("M 110 60 Q 140 44 170 42", 9, "#fff", extra='opacity=".45"'))
    if cara == "smile":
        s.append(ojos(184, 140, 76, "open", .9) + boca(184, 186, "smile", .85))
    elif cara == "feliz":
        s.append(ojos(184, 140, 76, "happy", .9) + boca(184, 180, "grin", .8))
    return "".join(s)


def meteorito():
    s = [f'<path d="M 170 120 Q 80 40 0 0 Q 70 70 150 150 Z" fill="#FF8A2A" opacity=".85"/>',
         f'<path d="M 168 126 Q 110 74 50 40 Q 104 92 152 144 Z" fill="#FFD23F"/>',
         ln("M 150 110 Q 160 92 186 96 Q 214 100 220 128 Q 222 158 196 170 Q 164 176 152 152 Q 140 130 150 110 Z",
            6, INK, "#8E7B6B"),
         f'<circle cx="196" cy="140" r="9" fill="#6E5D4C"/>']
    return "".join(s)


def luna_llena(cara=True):
    cx, cy, r = 200, 200, 180
    s = [f'<clipPath id="lc"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>',
         f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#D3D3DA"/>', '<g clip-path="url(#lc)">']
    for x, y, rr in [(120, 110, 34), (290, 130, 26), (110, 290, 40), (300, 300, 30), (210, 330, 18), (70, 200, 16)]:
        s.append(f'<circle cx="{x}" cy="{y}" r="{rr}" fill="#BABAC4" stroke="#A3A3AF" stroke-width="5"/>')
    s.append(f'<path d="M {cx+r} {cy} A {r} {r} 0 0 1 {cx} {cy+r} A {r*1.2} {r*1.2} 0 0 0 {cx+r} {cy} Z" fill="#000" opacity=".1"/>')
    s.append('</g>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{INK}" stroke-width="{SW+1}"/>')
    if cara:
        s.append(ojos(cx, cy - 6, 96, "open", 1.0, look=(-.8, 0)) + boca(cx, cy + 50, "smile", .9))
    return "".join(s)


def bolsa_muestras():
    s = [ln("M 40 70 L 260 70 L 268 350 Q 268 366 252 366 L 48 366 Q 32 366 32 350 Z", SW, INK, "#EEF7FB"),
         ln("M 34 280 Q 70 236 118 252 Q 160 226 206 250 Q 246 236 266 270 L 268 350 Q 268 366 252 366 L 48 366 Q 32 366 32 350 Z",
            0, INK, "#9A958E"),
         ln("M 40 70 L 260 70 L 268 350 Q 268 366 252 366 L 48 366 Q 32 366 32 350 Z", SW),
         f'<rect x="34" y="52" width="232" height="30" rx="8" fill="{P["rojo"]}" stroke="{INK}" stroke-width="{SW}"/>',
         f'<rect x="70" y="112" width="160" height="74" rx="10" fill="#fff" stroke="{INK}" stroke-width="6"/>',
         ln("M 56 110 L 56 250", 10, "#fff", extra='opacity=".8"')]
    rnd = random.Random(2)
    s += [f'<circle cx="{rnd.uniform(60, 240):.0f}" cy="{rnd.uniform(290, 350):.0f}" r="{rnd.uniform(3, 7):.0f}" fill="#7E7973"/>'
          for _ in range(18)]
    return "".join(s)


# ---------------------------------------------------------------- rocas, hidrógeno, frascos
def roca(k=0):
    rnd = random.Random(60 + k)
    pts = []
    for i in range(9):
        a = i * 2 * math.pi / 9
        rr = 52 * rnd.uniform(.78, 1.05)
        pts.append(f"{80 + rr*math.cos(a):.1f} {70 + rr*.8*math.sin(a):.1f}")
    d = "M " + " L ".join(pts) + " Z"
    return (ln(d, SW, INK, ["#8E7B6B", "#9E8A72", "#7F6E60"][k % 3])
            + f'<circle cx="{64 + 10*k}" cy="62" r="8" fill="#6E5D4C"/>' + ln("M 52 44 Q 66 34 84 34", 7, "#fff", extra='opacity=".4"'))


def burbuja_h():
    return (f'<circle cx="60" cy="60" r="50" fill="#E6F7FF" stroke="{INK}" stroke-width="{SW}"/>'
            + ln("M 42 36 L 42 84 M 78 36 L 78 84 M 42 60 L 78 60", 11, "#3A72D9")
            + ln("M 26 46 Q 30 30 46 22", 7, "#fff"))


FRASCO = "M 40 92 Q 40 70 62 66 L 62 36 L 178 36 L 178 66 Q 200 70 200 92 L 200 272 Q 200 292 180 292 L 60 292 Q 40 292 40 272 Z"


def frasco(p):
    lvl = 286 - p * 196
    s = [f'<clipPath id="fr"><path d="{FRASCO}"/></clipPath>',
         f'<path d="{FRASCO}" fill="#F2FBFF"/>', '<g clip-path="url(#fr)">']
    if p > 0.01:
        s.append(f'<path d="M 30 {lvl:.1f} Q 70 {lvl-14:.1f} 120 {lvl:.1f} Q 170 {lvl+14:.1f} 210 {lvl:.1f} L 210 300 L 30 300 Z" fill="{AGUA}"/>')
        s.append(f'<path d="M 30 {lvl+26:.1f} Q 80 {lvl+14:.1f} 130 {lvl+26:.1f} Q 180 {lvl+38:.1f} 210 {lvl+26:.1f} L 210 300 L 30 300 Z" fill="{AGUA2}" opacity=".45"/>')
    s.append('</g>')
    s.append(ln(FRASCO, SW))
    s.append(f'<rect x="54" y="18" width="132" height="30" rx="8" fill="#5C9BD6" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 62 110 L 62 250", 10, "#fff", extra='opacity=".75"'))
    return "".join(s)


# ---------------------------------------------------------------- laboratorio
def horno():
    s = [f'<rect x="60" y="430" width="50" height="26" rx="6" fill="{INK}"/><rect x="370" y="430" width="50" height="26" rx="6" fill="{INK}"/>',
         f'<rect x="30" y="50" width="420" height="390" rx="28" fill="#7D8AA0" stroke="{INK}" stroke-width="{SW}"/>',
         f'<rect x="30" y="50" width="420" height="60" rx="28" fill="#94A1B6" stroke="{INK}" stroke-width="{SW}"/>',
         f'<rect x="58" y="134" width="250" height="250" rx="22" fill="#2A2F3E" stroke="{INK}" stroke-width="{SW}"/>',
         '<clipPath id="hv"><rect x="66" y="142" width="234" height="234" rx="16"/></clipPath>',
         '<g clip-path="url(#hv)">',
         '<rect x="66" y="142" width="234" height="234" fill="url(#hg)"/>',
         ln("M 120 330 Q 118 290 150 280 Q 176 262 206 278 Q 246 284 244 320 Q 250 340 230 346 L 136 346 Q 116 344 120 330 Z",
            6, INK, "#6E2620"),
         ln("M 146 310 L 170 296 L 196 312 L 222 300", 6, "#FFD23F"),
         '</g>',
         ln("M 84 160 L 84 230", 9, "#fff", extra='opacity=".35"'),
         f'<rect x="330" y="140" width="96" height="62" rx="10" fill="#1E2430" stroke="{INK}" stroke-width="6"/>']
    for y in (250, 326):
        s.append(f'<circle cx="378" cy="{y}" r="26" fill="#C9D2DE" stroke="{INK}" stroke-width="{SW}"/>'
                 + ln(f"M 378 {y} L 378 {y-18}", 7))
    defs = ('<radialGradient id="hg" cx="0.5" cy="0.62" r="0.6"><stop offset="0" stop-color="#FFE27A"/>'
            '<stop offset="0.45" stop-color="#FF9A2A"/><stop offset="1" stop-color="#C2412F"/></radialGradient>')
    return "".join(s), defs


def termometro():
    return (f'<rect x="40" y="20" width="50" height="320" rx="25" fill="#fff" stroke="{INK}" stroke-width="{SW}"/>'
            f'<circle cx="65" cy="360" r="46" fill="{P["rojo"]}" stroke="{INK}" stroke-width="{SW}"/>'
            f'<rect x="54" y="60" width="22" height="300" rx="11" fill="{P["rojo"]}"/>'
            + "".join(ln(f"M 90 {y} L 108 {y}", 5) for y in range(70, 320, 40))
            + ln("M 50 350 Q 52 336 62 330", 7, "#fff", extra='opacity=".7"'))


# ---------------------------------------------------------------- cierre
def bola_agua():
    return (f'<circle cx="100" cy="100" r="84" fill="url(#ba)" stroke="{INK}" stroke-width="{SW}"/>'
            + ln("M 50 76 Q 62 44 96 34", 12, "#fff", extra='opacity=".7"')
            + ojos(100, 104, 50, "dot", .9) + boca(100, 132, "smile", .7)), \
           ('<radialGradient id="ba" cx="0.38" cy="0.35" r="0.75"><stop offset="0" stop-color="#8FD3FF"/>'
            f'<stop offset="1" stop-color="{AGUA2}"/></radialGradient>')


def tachon():
    return stroke_path("M 16 46 Q 110 22 210 40 Q 310 58 404 30", P["rojo"], 16, INK, 28)


def reloj_arena():
    s = [ln("M 60 70 L 200 70 Q 200 150 140 190 Q 200 230 200 310 L 60 310 Q 60 230 120 190 Q 60 150 60 70 Z", SW, INK, "#EAF8FF"),
         ln("M 80 96 L 180 96 Q 176 140 130 176 Q 84 140 80 96 Z", 0, INK, P["amarillo"]),
         ln("M 130 196 L 130 250", 6, "#E8B400"),
         ln("M 76 300 Q 130 240 184 300 Z", 0, INK, P["amarillo"]),
         ln("M 60 70 L 200 70 Q 200 150 140 190 Q 200 230 200 310 L 60 310 Q 60 230 120 190 Q 60 150 60 70 Z", SW),
         f'<rect x="30" y="40" width="200" height="36" rx="12" fill="{P["marron"]}" stroke="{INK}" stroke-width="{SW}"/>',
         f'<rect x="30" y="304" width="200" height="36" rx="12" fill="{P["marron"]}" stroke="{INK}" stroke-width="{SW}"/>',
         ln("M 82 110 Q 84 140 100 160", 7, "#fff", extra='opacity=".7"')]
    return "".join(s)


def rayo():
    """Rayo de medición punteado, visible sobre fondos oscuros."""
    d = "M 16 20 L 844 20"
    return (f'<path d="{d}" stroke="{INK}" stroke-width="24" stroke-dasharray="44 26" stroke-linecap="round" fill="none"/>'
            f'<path d="{d}" stroke="{P["amarillo"]}" stroke-width="12" stroke-dasharray="44 26" stroke-linecap="round" fill="none"/>')


def tilde():
    return (f'<circle cx="80" cy="80" r="66" fill="{P["verde"]}" stroke="{INK}" stroke-width="{SW}"/>'
            + stroke_path("M 46 82 L 72 108 L 118 54", "#fff", 18, INK, 30))


def cruz():
    return (f'<circle cx="80" cy="80" r="66" fill="{P["rojo"]}" stroke="{INK}" stroke-width="{SW}"/>'
            + stroke_path("M 52 52 L 108 108 M 108 52 L 52 108", "#fff", 18, INK, 30))


# ---------------------------------------------------------------- Vos detective
def sombrero():
    return (f'<ellipse cx="262" cy="118" rx="214" ry="36" fill="#8B6440" stroke="{INK}" stroke-width="{SW}"/>'
            + ln("M 128 120 L 150 26 Q 205 -2 262 22 Q 320 -2 374 26 L 396 120 Q 262 146 128 120 Z", SW, INK, "#A47A50")
            + ln("M 140 74 Q 262 98 384 74 L 392 108 Q 262 134 132 108 Z", 6, INK, "#3B2B23")
            + ln("M 176 40 Q 200 30 226 32", 8, "#fff", extra='opacity=".35"'))


def vos_det(**kw):
    return vos(**kw) + sombrero()


DET = {
    "vosdet_neutral": dict(),
    "vosdet_mira": dict(look=(1, -0.3)),
    "vosdet_sorpresa": dict(eyes="wide", brows="up", mouth_kind="o"),
    "vosdet_pulgar": dict(eyes="happy", brows="happy", mouth_kind="open_smile", arm_kind="thumb"),
    "vosdet_contento": dict(eyes="happy", brows="happy", mouth_kind="open_smile"),
}


# ---------------------------------------------------------------- armado
def build_agua(META):
    for name, kw in DET.items():
        add(name, 520, 820, vos_det(**kw), anchor=(0.5, 1.0))
        if name in ("vosdet_neutral", "vosdet_mira", "vosdet_sorpresa"):
            add(name + "__blink", 520, 820, vos_det(**dict(kw, eyes="closed")), anchor=(0.5, 1.0))
    for tipo, cara, name in [("normal", "smile", "tierra"), ("normal", "contenta", "tierra_contenta"),
                             ("normal", "sorpresa", "tierra_sorpresa"), ("seca", "triste", "tierra_seca"),
                             ("lava", "agobiada", "tierra_lava")]:
        add(name, 440, 440, tierra(tipo, cara))
    for i in range(8):
        add(f"hielo_{i}", 260, 250, hielo(i / 7), anchor=(0.5, 0.95))
    add("vapor_a", 260, 250, vapor(0), anchor=(0.5, 0.9))
    add("vapor_b", 260, 250, vapor(1), anchor=(0.5, 0.9))
    # fotos del tablero
    space = "#1E2656"
    add("foto_cometa", FOTO_W, FOTO_H, foto(mini(cometa(), 150, 163, .52, 560, 300), space, rot=-3))
    add("foto_asteroide", FOTO_W, FOTO_H, foto(mini(asteroide(), 160, 163, .62, 360, 300), space, rot=2))
    add("foto_misterio", FOTO_W, FOTO_H, foto(pregunta(160, 160, 1.15), "#3A3550", rot=-2))
    add("foto_misterio_polvo", FOTO_W, FOTO_H, foto(pregunta(160, 160, 1.15), "#3A3550", polvo=True, rot=-2))
    add("foto_tierra", FOTO_W, FOTO_H, foto(mini(tierra("normal", "contenta"), 160, 163, .48, 440, 440), space, rot=-2))
    add("hilos", W, H, hilos())
    add("chinche", 40, 44, chinche(20, 20))
    add("cometa", 560, 300, cometa(), anchor=(420 / 560, 150 / 300))
    add("cometa_enojado", 560, 300, cometa("enojado"), anchor=(420 / 560, 150 / 300))
    add("sonda", 420, 220, sonda())
    add("gota_tierra", 180, 240, gota(AGUA, "smile"))
    add("gota_tierra_feliz", 180, 240, gota(AGUA, "feliz"))
    add("gota_cometa", 180, 240, gota("#B7A4FF", "enojada"))
    add("nube_polvo", 420, 280, nube_polvo())
    add("asteroide", 360, 300, asteroide())
    add("asteroide_feliz", 360, 300, asteroide("feliz"))
    add("meteorito", 230, 190, meteorito(), anchor=(186 / 230, 136 / 190))
    add("luna_llena", 400, 400, luna_llena())
    add("bolsa_muestras", 300, 380, bolsa_muestras())
    for k in range(3):
        add(f"roca_{k}", 160, 140, roca(k))
    add("burbuja_h", 120, 120, burbuja_h())
    for i in range(11):
        add(f"frasco_{i:02d}", 240, 300, frasco(i / 10), anchor=(0.5, 0.97))
    body, defs = horno()
    add("horno", 480, 460, body, defs, anchor=(0.5, 0.98))
    add("termometro", 130, 420, termometro())
    body, defs = bola_agua()
    add("bola_agua", 200, 200, body, defs)
    add("tachon", 420, 80, tachon(), anchor=(0.0, 0.5))
    add("reloj_arena", 260, 360, reloj_arena())
    add("rayo", 860, 40, rayo())
    add("tilde", 160, 160, tilde())
    add("cruz", 160, 160, cruz())
    for name, fn in [("fondo_espacio", fondo_espacio), ("fondo_corcho", fondo_corcho), ("fondo_lab", fondo_lab)]:
        body, defs = fn()
        add(name, W, H, body, defs)
    META["tablero"] = {str(k): list(v) for k, v in TABLERO.items()}

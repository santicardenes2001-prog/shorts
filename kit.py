"""Kit de recursos en SVG para los shorts.

Todo sale de una guía de estilo común (contorno, paleta) para que
cualquier recurso nuevo quede coherente con el resto.

Uso: python kit.py  -> escribe kit/svg/*.svg, kit/png/*.png y kit/meta.json
"""
import json
import math
import os
import random

import cairosvg

# ---------------------------------------------------------------- guía de estilo
INK = "#24201F"   # color de contorno
SW = 7            # grosor de contorno base (px a escala 1)
RS = 1.5          # escala de rasterizado (margen para animar sin perder nitidez)

P = dict(
    piel="#F8C9A2", piel2="#E9A982", pelo="#3B2B23",
    remera="#4C8DFF", remera2="#3A72D9", pantalon="#2F3A5C",
    rojo="#FF5D5D", amarillo="#FFD23F", verde="#46C281", verde2="#2E9E62",
    rosa="#FF8FA8", violeta="#7A5CFF", crema="#FFF3DF",
    marron="#A0714D", marron2="#7A5236", hueso="#F6EBD6", blanco="#FFFFFF",
    cielo="#9ADCFF", noche="#262E63", boca="#7A2735", lengua="#FF7E93",
    acaro="#EEDBB8", acaro2="#CDB48C", coral="#FF8F6B",
)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kit")
ASSETS = {}   # nombre -> svg
META = {}


def svg(w, h, body, defs=""):
    d = f"<defs>{defs}</defs>" if defs else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">{d}{body}</svg>')


def add(name, w, h, body, defs="", anchor=(0.5, 0.5)):
    ASSETS[name] = svg(w, h, body, defs)
    META.setdefault("anchors", {})[name] = list(anchor)


def stroke_path(d, color, width, outline=INK, ow=None):
    """Trazo con contorno (para brazos, patas, etc.)."""
    ow = ow or width + 2 * SW
    return (f'<path d="{d}" fill="none" stroke="{outline}" stroke-width="{ow}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def ln(d, w=SW, color=INK, fill="none", extra=""):
    return (f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{w}" '
            f'stroke-linecap="round" stroke-linejoin="round" {extra}/>')


# ---------------------------------------------------------------- personaje Vos
EYE_L, EYE_R, EYE_Y = 200, 320, 305


def eye(cx, cy, kind, look, side):
    lx, ly = look
    cid = f"clip{side}"
    if kind == "open" or kind == "wide":
        rx, ry, pr = (38, 44, 16) if kind == "open" else (46, 54, 11)
        px, py = cx + lx * 14, cy + ly * 14 + 4
        return (f'<clipPath id="{cid}"><ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/></clipPath>'
                f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#fff" stroke="{INK}" stroke-width="6"/>'
                f'<g clip-path="url(#{cid})"><circle cx="{px}" cy="{py}" r="{pr}" fill="{INK}"/>'
                f'<circle cx="{px - pr * .35}" cy="{py - pr * .4}" r="{max(3, pr * .3)}" fill="#fff"/></g>')
    if kind == "closed":      # dormido / parpadeo
        return ln(f"M {cx-34} {cy+4} Q {cx} {cy+16} {cx+34} {cy+4}", 8)
    if kind == "happy":
        return ln(f"M {cx-34} {cy+12} Q {cx} {cy-24} {cx+34} {cy+12}", 9)
    if kind == "squint":
        return (f'<clipPath id="{cid}"><ellipse cx="{cx}" cy="{cy+10}" rx="38" ry="20"/></clipPath>'
                f'<ellipse cx="{cx}" cy="{cy+10}" rx="38" ry="20" fill="#fff" stroke="{INK}" stroke-width="6"/>'
                f'<g clip-path="url(#{cid})"><circle cx="{cx}" cy="{cy+14}" r="12" fill="{INK}"/></g>'
                + ln(f"M {cx-42} {cy-2} Q {cx} {cy-12} {cx+42} {cy-2}", 9))
    if kind == "tired":
        return (f'<clipPath id="{cid}"><ellipse cx="{cx}" cy="{cy}" rx="38" ry="44"/></clipPath>'
                f'<ellipse cx="{cx}" cy="{cy}" rx="38" ry="44" fill="#fff"/>'
                f'<g clip-path="url(#{cid})"><circle cx="{cx}" cy="{cy+18}" r="16" fill="{INK}"/>'
                f'<rect x="{cx-40}" y="{cy-46}" width="80" height="46" fill="{P["piel"]}"/></g>'
                f'<ellipse cx="{cx}" cy="{cy}" rx="38" ry="44" fill="none" stroke="{INK}" stroke-width="6"/>'
                + ln(f"M {cx-38} {cy} Q {cx} {cy+8} {cx+38} {cy}", 7)
                + ln(f"M {cx-26} {cy+56} Q {cx} {cy+64} {cx+26} {cy+56}", 5, P["piel2"]))
    raise ValueError(kind)


BROWS = {
    "neutral": ("M 168 248 Q 200 234 232 246", "M 288 246 Q 320 234 352 248"),
    "up": ("M 166 222 Q 200 202 234 218", "M 286 218 Q 320 202 354 222"),
    "asco": ("M 168 236 L 234 258", "M 286 234 Q 320 216 354 230"),
    "sad": ("M 168 258 L 232 242", "M 288 242 L 352 258"),
    "happy": ("M 168 240 Q 200 224 232 238", "M 288 238 Q 320 224 352 240"),
}


def mouth(kind):
    if kind == "smile":
        return ln("M 222 392 Q 260 428 298 392", 8)
    if kind == "open_smile":
        return ('<clipPath id="mclip"><path d="M 214 388 Q 260 452 306 388 Z"/></clipPath>'
                f'<path d="M 214 388 Q 260 452 306 388 Z" fill="{P["boca"]}"/>'
                f'<g clip-path="url(#mclip)"><ellipse cx="260" cy="428" rx="28" ry="14" fill="{P["lengua"]}"/></g>'
                + ln("M 214 388 Q 260 452 306 388 Z", 7))
    if kind == "o":
        return f'<ellipse cx="260" cy="405" rx="22" ry="29" fill="{P["boca"]}" stroke="{INK}" stroke-width="7"/>'
    if kind == "bleh":
        return (ln("M 262 400 Q 260 446 280 446 Q 300 446 298 402 Z", 6, INK, P["lengua"])
                + ln("M 214 398 Q 229 386 244 398 Q 260 410 276 398 Q 291 386 306 398", 8))
    if kind == "yawn":
        return ('<clipPath id="yclip"><ellipse cx="260" cy="408" rx="32" ry="40"/></clipPath>'
                f'<ellipse cx="260" cy="408" rx="32" ry="40" fill="{P["boca"]}"/>'
                f'<g clip-path="url(#yclip)"><ellipse cx="260" cy="446" rx="26" ry="16" fill="{P["lengua"]}"/></g>'
                f'<ellipse cx="260" cy="408" rx="32" ry="40" fill="none" stroke="{INK}" stroke-width="7"/>')
    if kind == "flat":
        return ln("M 228 404 L 292 404", 8)
    if kind == "mid":
        return f'<ellipse cx="260" cy="404" rx="28" ry="14" fill="{P["boca"]}" stroke="{INK}" stroke-width="7"/>'
    raise ValueError(kind)


HAIR = ("M 92 240 C 72 110, 190 58, 275 66 C 372 74, 452 130, 430 240 "
        "L 404 186 L 372 204 L 338 170 L 300 198 L 262 164 L 222 200 L 186 170 L 152 204 L 122 178 Z")


def head(eyes="open", brows="neutral", mouth_kind="smile", look=(0, 0), extra=""):
    """Cabeza de Vos en coordenadas del lienzo de 520x820 (centro 260,270)."""
    s = []
    for x in (90, 430):
        s.append(f'<circle cx="{x}" cy="292" r="30" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<circle cx="260" cy="270" r="172" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln(HAIR, SW, INK, P["pelo"]))
    s.append(f'<ellipse cx="165" cy="372" rx="28" ry="15" fill="{P["rosa"]}" opacity=".5"/>'
             f'<ellipse cx="355" cy="372" rx="28" ry="15" fill="{P["rosa"]}" opacity=".5"/>')
    s.append(extra)
    s.append(eye(EYE_L, EYE_Y, eyes, look, "L"))
    s.append(eye(EYE_R, EYE_Y, eyes, look, "R"))
    bl, br = BROWS[brows]
    s.append(ln(bl, 13) + ln(br, 13))
    s.append(ln("M 262 332 Q 278 352 258 362", 6))
    s.append(mouth(mouth_kind))
    return "".join(s)


def arms(kind):
    def arm(d, hand):
        hx, hy = hand
        return (stroke_path(d, P["piel"], 28)
                + f'<circle cx="{hx}" cy="{hy}" r="25" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
    sleeves = (f'<circle cx="186" cy="500" r="30" fill="{P["remera"]}" stroke="{INK}" stroke-width="{SW}"/>'
               f'<circle cx="334" cy="500" r="30" fill="{P["remera"]}" stroke="{INK}" stroke-width="{SW}"/>')
    if kind == "down":
        return arm("M 182 505 Q 150 575 148 652", (148, 655)) + arm("M 338 505 Q 370 575 372 652", (372, 655)) + sleeves, ""
    if kind == "up":   # detrás de la cabeza
        back = arm("M 182 495 Q 40 430 72 150", (72, 150)) + arm("M 338 495 Q 480 430 448 150", (448, 150))
        return sleeves, back
    if kind == "thumb":
        left = arm("M 182 505 Q 150 575 148 652", (148, 655))
        right = (stroke_path("M 338 505 L 420 562 L 440 432", P["piel"], 28)
                 + f'<rect x="428" y="368" width="24" height="52" rx="12" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>'
                 + f'<circle cx="440" cy="432" r="28" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>'
                 + ln("M 424 440 L 452 440", 5))
        return left + right + sleeves, ""
    raise ValueError(kind)


def vos(eyes="open", brows="neutral", mouth_kind="smile", arm_kind="down", look=(0, 0), extra=""):
    s = [f'<ellipse cx="260" cy="806" rx="125" ry="13" fill="#000" opacity=".12"/>']
    front, back = arms(arm_kind)
    s.append(back)
    for x in (205, 269):
        s.append(f'<rect x="{x}" y="640" width="46" height="150" rx="20" fill="{P["pantalon"]}" stroke="{INK}" stroke-width="{SW}"/>')
    for x in (220, 300):
        s.append(f'<ellipse cx="{x}" cy="794" rx="40" ry="21" fill="{INK}"/>')
    s.append(f'<rect x="158" y="452" width="204" height="228" rx="72" fill="{P["remera"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 224 462 Q 260 494 296 462", 6))
    s.append(front)
    s.append(head(eyes, brows, mouth_kind, look, extra))
    return "".join(s)


VOS_VARIANTS = {
    "vos_neutral": dict(),
    "vos_sorpresa": dict(eyes="wide", brows="up", mouth_kind="o"),
    "vos_asco": dict(eyes="squint", brows="asco", mouth_kind="bleh",
                     extra=f'<ellipse cx="165" cy="372" rx="34" ry="20" fill="{P["verde"]}" opacity=".7"/>'
                           f'<ellipse cx="355" cy="372" rx="34" ry="20" fill="{P["verde"]}" opacity=".7"/>'),
    "vos_contento": dict(eyes="happy", brows="happy", mouth_kind="open_smile"),
    "vos_pulgar": dict(eyes="happy", brows="happy", mouth_kind="open_smile", arm_kind="thumb"),
    "vos_estira": dict(eyes="closed", brows="neutral", mouth_kind="yawn", arm_kind="up"),
    "vos_cansado": dict(eyes="tired", brows="sad", mouth_kind="flat"),
    "vos_mira": dict(look=(1, -0.3)),
}
# Variantes de parpadeo automáticas para las que tienen ojos abiertos
BLINKABLE = ["vos_neutral", "vos_mira", "vos_cansado", "vos_sorpresa"]

# Bocas para lip sync (cabeza neutral con distintas bocas)
LIPSYNC = {"vos_boca_cerrada": "flat", "vos_boca_media": "mid", "vos_boca_abierta": "o"}


def build_vos():
    for name, kw in VOS_VARIANTS.items():
        add(name, 520, 820, vos(**kw), anchor=(0.5, 1.0))
        if name in BLINKABLE:
            kw2 = dict(kw)
            kw2["eyes"] = "closed"
            add(name + "__blink", 520, 820, vos(**kw2), anchor=(0.5, 1.0))
    for name, m in LIPSYNC.items():
        add(name, 520, 820, vos(mouth_kind=m), anchor=(0.5, 1.0))
    META["vos_ojo_derecho"] = [EYE_R, EYE_Y]
    META["vos_ojo_izquierdo"] = [EYE_L, EYE_Y]
    META["vos_size"] = [520, 820]


# ---------------------------------------------------------------- cama
def cama(con_vos):
    s = []
    s.append(f'<rect x="20" y="70" width="60" height="300" rx="18" fill="{P["marron"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<rect x="600" y="170" width="56" height="200" rx="16" fill="{P["marron"]}" stroke="{INK}" stroke-width="{SW}"/>')
    for x in (40, 612):
        s.append(f'<rect x="{x}" y="356" width="26" height="34" rx="6" fill="{P["marron2"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<rect x="60" y="300" width="560" height="52" rx="12" fill="{P["marron"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<rect x="64" y="240" width="552" height="72" rx="22" fill="{P["blanco"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<ellipse cx="160" cy="226" rx="84" ry="38" fill="{P["blanco"]}" stroke="{INK}" stroke-width="{SW}"/>')
    if con_vos:
        s.append('<g transform="translate(178 168) scale(0.40) translate(-260 -270)">'
                 + head("closed", "neutral", "smile") + '</g>')
        blanket = "M 228 258 Q 236 176 330 172 L 598 182 Q 626 184 626 212 L 626 304 L 228 304 Z"
    else:
        blanket = "M 330 240 L 598 240 Q 626 240 626 262 L 626 304 L 330 304 Z"
    s.append(ln(blanket, SW, INK, P["coral"]))
    s.append(f'<clipPath id="bl"><path d="{blanket}"/></clipPath><g clip-path="url(#bl)" opacity=".45">'
             + "".join(f'<rect x="{x}" y="150" width="22" height="200" fill="#fff"/>' for x in range(260, 640, 70))
             + '</g>')
    return "".join(s)


# ---------------------------------------------------------------- objetos chicos
def zzz():
    s = []
    for (x, y, k) in [(20, 190, 40), (80, 120, 55), (150, 30, 75)]:
        d = f"M {x} {y} L {x+k} {y} L {x} {y+k} L {x+k} {y+k}"
        s.append(stroke_path(d, "#fff", 9, INK, 21))
    return "".join(s)


def sol(face=True):
    s = []
    for i in range(10):
        a = i * 36
        s.append(f'<rect x="122" y="10" width="16" height="44" rx="8" fill="{P["amarillo"]}" stroke="{INK}" '
                 f'stroke-width="6" transform="rotate({a} 130 130)"/>')
    s.append(f'<circle cx="130" cy="130" r="64" fill="{P["amarillo"]}" stroke="{INK}" stroke-width="{SW}"/>')
    if face:
        s.append(ln("M 102 128 Q 112 116 122 128", 6) + ln("M 138 128 Q 148 116 158 128", 6)
                 + ln("M 112 148 Q 130 164 148 148", 6))
    return "".join(s)


def luna():
    return (ln("M 120 20 A 82 82 0 1 0 184 152 A 66 66 0 1 1 120 20 Z", SW, INK, "#FFE9A3")
            + f'<circle cx="80" cy="120" r="6" fill="{INK}"/>' + ln("M 70 146 Q 84 154 98 144", 5))


def estrella4(cx, cy, r, fill=None, w=6):
    fill = fill or P["amarillo"]
    k = r * 0.16
    d = (f"M {cx} {cy-r} Q {cx+k} {cy-k} {cx+r} {cy} Q {cx+k} {cy+k} {cx} {cy+r} "
         f"Q {cx-k} {cy+k} {cx-r} {cy} Q {cx-k} {cy-k} {cx} {cy-r} Z")
    return ln(d, w, INK, fill)


def flecha_gravedad():
    d = ("M 105 20 Q 105 10 115 10 L 185 10 Q 195 10 195 20 L 195 170 L 268 170 "
         "L 150 305 L 32 170 L 105 170 Z")
    return ln(d, 8, INK, P["rojo"]) + ln("M 128 30 L 128 150", 10, "#fff", extra='opacity=".45"')


def regla():
    s = [f'<rect x="10" y="10" width="100" height="700" rx="12" fill="{P["amarillo"]}" stroke="{INK}" stroke-width="{SW}"/>']
    for i in range(1, 35):
        y = 710 - i * 20
        L = 44 if i % 5 == 0 else 24
        s.append(ln(f"M 14 {y} L {14+L} {y}", 4))
    return "".join(s)


def linea_punteada():
    return (f'<path d="M 8 8 L 852 8" stroke="{INK}" stroke-width="6" stroke-dasharray="26 18" '
            f'stroke-linecap="round" fill="none"/>')


def lupa():
    return (stroke_path("M 196 196 L 292 292", P["marron2"], 34, INK, 48)
            + f'<circle cx="125" cy="125" r="100" fill="#BDEBFF" opacity=".45"/>'
            + f'<circle cx="125" cy="125" r="100" fill="none" stroke="{INK}" stroke-width="28"/>'
            + f'<circle cx="125" cy="125" r="100" fill="none" stroke="#8E97A8" stroke-width="16"/>'
            + ln("M 68 110 Q 75 75 110 66", 12, "#fff", extra='opacity=".8"'))


def flechita():
    return ln("M 20 40 Q 110 10 160 96", 12) + ln("M 128 92 L 164 104 L 170 66", 12)


def exclamacion():
    return (ln("M 40 20 L 80 20 L 70 170 L 50 170 Z", 8, INK, P["rojo"])
            + f'<circle cx="60" cy="220" r="24" fill="{P["rojo"]}" stroke="{INK}" stroke-width="8"/>')


def brillo():
    return estrella4(60, 60, 54)


# ---------------------------------------------------------------- árbol
def arbol_body():
    circles = [(210, 190, 150), (110, 270, 95), (310, 270, 95), (210, 300, 112)]
    s = [ln("M 176 552 L 186 330 L 234 330 L 244 552 Q 210 562 176 552 Z", SW, INK, P["marron"])]
    s += [f'<circle cx="{x}" cy="{y}" r="{r}" fill="{INK}" stroke="{INK}" stroke-width="{SW*2}"/>' for x, y, r in circles]
    s += [f'<circle cx="{x}" cy="{y}" r="{r}" fill="#57C46B"/>' for x, y, r in circles]
    s += [f'<circle cx="{x}" cy="{y}" r="{r}" fill="#3FA557" opacity=".55"/>'
          for x, y, r in [(150, 330, 50), (280, 330, 45), (300, 200, 40)]]
    s += [f'<circle cx="{x}" cy="{y}" r="16" fill="{P["rojo"]}" stroke="{INK}" stroke-width="5"/>'
          for x, y in [(150, 170), (270, 240), (120, 300), (330, 310), (230, 110)]]
    s.append(ln("M 120 110 Q 150 70 200 66", 12, "#fff", extra='opacity=".35"'))
    return "".join(s)


# ---------------------------------------------------------------- columna
def columna(p):
    """p=1 descomprimida (discos gordos), p=0 comprimida."""
    s = []
    vh, cx = 104, 160
    dh = 16 + 46 * p
    dw = 196 + 54 * (1 - p)
    y = 815
    for i in range(9):
        if i % 2 == 0:   # vértebra
            top = y - vh
            s.append(f'<rect x="{cx-150}" y="{top+vh/2-20}" width="300" height="40" rx="18" fill="{P["hueso"]}" stroke="{INK}" stroke-width="{SW}"/>')
            s.append(f'<rect x="{cx-115}" y="{top}" width="230" height="{vh}" rx="30" fill="{P["hueso"]}" stroke="{INK}" stroke-width="{SW}"/>')
            s.append(ln(f"M {cx-80} {top+vh/2} L {cx+80} {top+vh/2}", 5, "#D9C7A6"))
            y = top
        else:            # disco (cartílago)
            top = y - dh
            s.append(f'<rect x="{cx-dw/2}" y="{top}" width="{dw}" height="{dh}" rx="{min(dh/2, 26)}" fill="{P["rosa"]}" stroke="{INK}" stroke-width="{SW}"/>')
            fy = top + dh / 2
            if p > 0.66:
                s.append(ln(f"M {cx-34} {fy-2} Q {cx-26} {fy-12} {cx-18} {fy-2}", 5)
                         + ln(f"M {cx+18} {fy-2} Q {cx+26} {fy-12} {cx+34} {fy-2}", 5)
                         + ln(f"M {cx-12} {fy+8} Q {cx} {fy+16} {cx+12} {fy+8}", 5))
            elif p > 0.33:
                s.append(f'<circle cx="{cx-26}" cy="{fy-2}" r="5" fill="{INK}"/><circle cx="{cx+26}" cy="{fy-2}" r="5" fill="{INK}"/>'
                         + ln(f"M {cx-10} {fy+8} L {cx+10} {fy+8}", 5))
            else:
                k = max(3, dh / 3)
                s.append(ln(f"M {cx-36} {fy-k} L {cx-24} {fy} L {cx-36} {fy+k}", 4)
                         + ln(f"M {cx+36} {fy-k} L {cx+24} {fy} L {cx+36} {fy+k}", 4)
                         + ln(f"M {cx-10} {fy} L {cx-5} {fy-k*.6} L {cx} {fy} L {cx+5} {fy-k*.6} L {cx+10} {fy}", 3))
            y = top
    return "".join(s)


# ---------------------------------------------------------------- ojo zoom
def ojo_zoom():
    P0, P1, P2 = (120, 440), (500, 150), (880, 440)
    s = []
    # ceja
    s.append(stroke_path("M 140 120 Q 500 -6 870 110", P["pelo"], 40, INK, 54))
    # pliegue
    s.append(ln("M 150 360 Q 500 70 850 360", 7, INK, extra='opacity=".5"'))
    almond = f"M {P0[0]} {P0[1]} Q {P1[0]} {P1[1]} {P2[0]} {P2[1]} Q 500 700 {P0[0]} {P0[1]} Z"
    s.append(f'<clipPath id="alm"><path d="{almond}"/></clipPath>')
    s.append(f'<path d="{almond}" fill="#fff"/>')
    s.append('<g clip-path="url(#alm)">'
             f'<circle cx="500" cy="430" r="128" fill="#5C9BD6" stroke="{INK}" stroke-width="8"/>'
             + "".join(ln(f"M {500+60*math.cos(a)} {430+60*math.sin(a)} L {500+118*math.cos(a)} {430+118*math.sin(a)}", 5, "#3F7AB8")
                       for a in [i * math.pi / 9 for i in range(18)])
             + f'<circle cx="500" cy="430" r="58" fill="{INK}"/>'
             f'<circle cx="470" cy="398" r="20" fill="#fff"/><circle cx="530" cy="460" r="9" fill="#fff"/>'
             '</g>')
    s.append(ln(almond, 9))
    roots = []
    lashes = []
    n = 13
    for i in range(n):
        t = 0.12 + 0.76 * i / (n - 1)
        x = (1 - t) ** 2 * P0[0] + 2 * (1 - t) * t * P1[0] + t ** 2 * P2[0]
        y = (1 - t) ** 2 * P0[1] + 2 * (1 - t) * t * P1[1] + t ** 2 * P2[1]
        tx = 2 * (1 - t) * (P1[0] - P0[0]) + 2 * t * (P2[0] - P1[0])
        ty = 2 * (1 - t) * (P1[1] - P0[1]) + 2 * t * (P2[1] - P1[1])
        L = math.hypot(tx, ty)
        tx, ty = tx / L, ty / L
        nx, ny = ty, -tx           # normal hacia afuera (arriba)
        side = -1 if t < 0.5 else 1
        c1 = (x + nx * 60 + tx * side * 10, y + ny * 60 + ty * side * 10)
        e = (x + nx * 112 + tx * side * 44, y + ny * 112 + ty * side * 44)
        lashes.append(ln(f"M {x:.1f} {y:.1f} Q {c1[0]:.1f} {c1[1]:.1f} {e[0]:.1f} {e[1]:.1f}", 12))
        roots.append([round(x, 1), round(y, 1), round(math.degrees(math.atan2(nx, -ny)), 1)])
    s.extend(lashes)
    META["ojo_zoom_raices"] = roots   # x, y, ángulo de la normal (0 = hacia arriba)
    return "".join(s)


# ---------------------------------------------------------------- ácaro
def acaro(legs="down", face="smile", babero=False, wave=0):
    s = []
    bc = P["acaro"]
    # palpos
    for x in (136, 184):
        s.append(f'<circle cx="{x}" cy="46" r="15" fill="{bc}" stroke="{INK}" stroke-width="{SW}"/>')
    # patas (4 pares)
    for k, y in enumerate([150, 186, 222, 258]):
        if legs == "down":
            dy = 18
        else:   # saludando: ángulo alterna con wave
            dy = -34 - 14 * ((k + wave) % 2)
        s.append(stroke_path(f"M 70 {y} L 22 {y+dy}", bc, 16))
        s.append(stroke_path(f"M 250 {y} L 298 {y+dy}", bc, 16))
    body = "M 160 40 C 250 40 262 140 258 220 L 240 470 Q 160 560 80 470 L 62 220 C 58 140 70 40 160 40 Z"
    s.append(ln(body, 8, INK, bc))
    for y in range(290, 480, 34):
        f = (y - 220) / 250
        hw = 98 - 18 * f
        s.append(ln(f"M {160-hw+6} {y} Q 160 {y+14} {160+hw-6} {y}", 5, P["acaro2"]))
    s.append(f'<ellipse cx="112" cy="150" rx="16" ry="9" fill="{P["rosa"]}" opacity=".6"/>'
             f'<ellipse cx="208" cy="150" rx="16" ry="9" fill="{P["rosa"]}" opacity=".6"/>')
    if face == "happy":
        s.append(ln("M 104 112 Q 125 90 146 112", 7) + ln("M 174 112 Q 195 90 216 112", 7))
    else:
        for x in (125, 195):
            s.append(f'<circle cx="{x}" cy="110" r="25" fill="#fff" stroke="{INK}" stroke-width="6"/>'
                     f'<circle cx="{x+3}" cy="114" r="12" fill="{INK}"/><circle cx="{x-1}" cy="109" r="4" fill="#fff"/>')
    if babero:
        s.append(ln("M 104 212 Q 160 232 216 212 L 208 296 Q 160 322 112 296 Z", 6, INK, "#fff")
                 + "".join(f'<circle cx="{x}" cy="{y}" r="7" fill="{P["rojo"]}"/>'
                           for x, y in [(136, 238), (184, 238), (160, 266), (132, 284), (188, 284)])
                 + ln("M 112 214 L 92 196", 5) + ln("M 208 214 L 228 196", 5))
    if face == "chew_open":
        s.append(f'<ellipse cx="160" cy="166" rx="26" ry="20" fill="{P["boca"]}" stroke="{INK}" stroke-width="6"/>'
                 f'<circle cx="150" cy="172" r="6" fill="#ECE4D6"/>')
    elif face == "chew_closed":
        s.append(ln("M 134 166 Q 147 154 160 166 Q 173 178 186 166", 7))
    elif face == "open":
        s.append(ln("M 136 152 Q 160 186 184 152 Z", 6, INK, P["boca"]))
    else:
        s.append(ln("M 138 154 Q 160 172 182 154", 7))
    return "".join(s)


# ---------------------------------------------------------------- comida del ácaro
def celulas():
    rnd = random.Random(3)
    s = []
    for (cx, cy, r) in [(80, 120, 52), (170, 90, 44), (190, 160, 34), (100, 50, 30), (40, 170, 22)]:
        pts = []
        for i in range(7):
            a = i * 2 * math.pi / 7 + rnd.uniform(-.2, .2)
            rr = r * rnd.uniform(.75, 1.1)
            pts.append(f"{cx+rr*math.cos(a):.1f} {cy+rr*math.sin(a):.1f}")
        s.append(ln("M " + " L ".join(pts) + " Z", 6, INK, "#ECE4D6"))
    # ojitos "x x" en la más grande
    for x in (64, 96):
        s.append(ln(f"M {x-8} 108 L {x+8} 124", 5) + ln(f"M {x+8} 108 L {x-8} 124", 5))
    s.append(ln("M 70 142 L 92 142", 5))
    return "".join(s)


def gota_grasa():
    d = "M 90 15 C 90 15 165 120 165 160 A 75 75 0 0 1 15 160 C 15 120 90 15 90 15 Z"
    return (ln(d, 8, INK, P["amarillo"]) + ln("M 52 130 Q 52 104 70 84", 10, "#fff", extra='opacity=".7"')
            + f'<circle cx="70" cy="165" r="7" fill="{INK}"/><circle cx="112" cy="165" r="7" fill="{INK}"/>'
            + ln("M 78 190 Q 91 200 104 190", 5))


# ---------------------------------------------------------------- diagrama del ojo
def diagrama():
    """Tres capas con el mismo lienzo de 1000x700 para que encajen."""
    C, R = (700, 350), 230
    lens = (520, 350)
    sc = 0.42
    top = (150, 470 - sc * (560 - 40))
    bot = (150, 470)

    def hit(p):
        dx, dy = lens[0] - p[0], lens[1] - p[1]
        L = math.hypot(dx, dy)
        dx, dy = dx / L, dy / L
        ox, oy = lens[0] - C[0], lens[1] - C[1]
        r = 205
        b = 2 * (ox * dx + oy * dy)
        c = ox * ox + oy * oy - r * r
        sres = (-b + math.sqrt(b * b - 4 * c)) / 2
        return (lens[0] + dx * sres, lens[1] + dy * sres)

    e_top, e_bot = hit(top), hit(bot)
    base = []
    base.append(f'<g transform="translate(150 470) scale({sc}) translate(-210 -560)">{arbol_body()}</g>')
    base.append(stroke_path("M 915 350 L 995 350", "#FFC2CF", 56))
    base.append(f'<ellipse cx="478" cy="350" rx="52" ry="132" fill="#D8F2FF" stroke="{INK}" stroke-width="{SW}"/>')
    base.append(f'<circle cx="{C[0]}" cy="{C[1]}" r="{R}" fill="#fff" stroke="{INK}" stroke-width="9"/>')
    a1, a2 = math.radians(-62), math.radians(62)
    p1 = (C[0] + 205 * math.cos(a1), C[1] + 205 * math.sin(a1))
    p2 = (C[0] + 205 * math.cos(a2), C[1] + 205 * math.sin(a2))
    base.append(f'<path d="M {p1[0]:.1f} {p1[1]:.1f} A 205 205 0 0 1 {p2[0]:.1f} {p2[1]:.1f}" '
                f'fill="none" stroke="{P["rosa"]}" stroke-width="24" stroke-linecap="round"/>')
    base.append(ln("M 506 238 L 506 270", 18, "#5C9BD6") + ln("M 506 430 L 506 462", 18, "#5C9BD6"))
    base.append(f'<ellipse cx="{lens[0]}" cy="{lens[1]}" rx="32" ry="92" fill="{P["cielo"]}" stroke="{INK}" stroke-width="{SW}"/>')
    base.append(ln("M 510 290 Q 504 320 508 340", 6, "#fff", extra='opacity=".8"'))
    add("diag_base", 1000, 700, "".join(base))

    def ray(a, b, c):
        d = f"M {a[0]:.1f} {a[1]:.1f} L {b[0]:.1f} {b[1]:.1f} L {c[0]:.1f} {c[1]:.1f}"
        ang = math.atan2(c[1] - b[1], c[0] - b[0])
        h1 = (c[0] - 26 * math.cos(ang - .45), c[1] - 26 * math.sin(ang - .45))
        h2 = (c[0] - 26 * math.cos(ang + .45), c[1] - 26 * math.sin(ang + .45))
        head = f"M {h1[0]:.1f} {h1[1]:.1f} L {c[0]:.1f} {c[1]:.1f} L {h2[0]:.1f} {h2[1]:.1f}"
        return stroke_path(d, "#FFB800", 8, INK, 16) + stroke_path(head, "#FFB800", 8, INK, 16)
    add("diag_rayos", 1000, 700, ray(top, lens, e_top) + ray(bot, lens, e_bot))

    h = abs(e_top[1] - e_bot[1]) * 0.92
    s2 = h / 520
    xm = (e_top[0] + e_bot[0]) / 2 - 18
    ytop = min(e_top[1], e_bot[1]) + abs(e_top[1] - e_bot[1]) * 0.04
    inv = (f'<g transform="translate({xm:.1f} {ytop:.1f}) scale({s2:.3f} {-s2:.3f}) translate(-210 -560)">'
           f'{arbol_body()}</g>')
    add("diag_invertido", 1000, 700, inv)
    META["diag"] = {"lente": list(lens), "retina": [905, 350], "size": [1000, 700]}


# ---------------------------------------------------------------- cerebro, engranaje, marco
def cerebro():
    lobes = [(190, 240, 105), (300, 215, 115), (400, 250, 100), (250, 330, 110), (370, 330, 105), (150, 318, 80)]
    s = [f'<circle cx="{x}" cy="{y}" r="{r}" fill="{INK}" stroke="{INK}" stroke-width="{SW*2}"/>' for x, y, r in lobes]
    s += [f'<circle cx="{x}" cy="{y}" r="{r}" fill="#FF9EB8"/>' for x, y, r in lobes]
    for d in ["M 150 220 Q 180 180 220 200 Q 250 220 240 250", "M 300 130 Q 340 150 330 190",
              "M 410 200 Q 440 240 420 280", "M 180 360 Q 220 390 260 370", "M 340 380 Q 380 400 420 370",
              "M 120 300 Q 140 280 160 300", "M 250 150 Q 270 120 300 130"]:
        s.append(ln(d, 8, "#E9739A"))
    # cara
    for x in (230, 350):
        s.append(f'<circle cx="{x}" cy="280" r="28" fill="#fff" stroke="{INK}" stroke-width="6"/>'
                 f'<circle cx="{x+4}" cy="286" r="13" fill="{INK}"/>')
    s.append(ln("M 196 236 L 256 252", 11) + ln("M 384 236 L 324 252", 11))
    s.append(ln("M 258 340 Q 290 362 322 340", 8))
    s.append(ln("M 312 348 Q 326 372 340 352", 6, INK, P["lengua"]))
    # casco
    s.append(ln("M 165 156 Q 165 22 300 22 Q 435 22 435 156 Z", SW, INK, P["amarillo"]))
    s.append(f'<rect x="125" y="140" width="350" height="30" rx="15" fill="{P["amarillo"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 300 30 L 300 140", 14, "#E8B400"))
    s.append(ln("M 200 60 Q 220 40 250 34", 9, "#fff", extra='opacity=".6"'))
    return "".join(s)


def engranaje(color, n=10, ro=130, ri=104, hole=36):
    pts = []
    for i in range(n * 4):
        a = i * 2 * math.pi / (n * 4)
        r = ro if (i % 4) in (1, 2) else ri
        pts.append(f"{150 + r*math.cos(a):.1f} {150 + r*math.sin(a):.1f}")
    return (ln("M " + " L ".join(pts) + " Z", SW, INK, color)
            + f'<circle cx="150" cy="150" r="{hole}" fill="#4B2E7E" stroke="{INK}" stroke-width="{SW}"/>')


def marco_foto():
    s = [f'<rect x="10" y="10" width="420" height="340" rx="18" fill="{P["marron"]}" stroke="{INK}" stroke-width="8"/>',
         '<clipPath id="pic"><rect x="40" y="40" width="360" height="280"/></clipPath>',
         '<g clip-path="url(#pic)">',
         f'<rect x="40" y="40" width="360" height="280" fill="{P["cielo"]}"/>',
         f'<rect x="40" y="262" width="360" height="70" fill="#56B65B"/>',
         f'<g transform="translate(330 95) scale(0.45) translate(-130 -130)">{sol(False)}</g>',
         f'<g transform="translate(200 280) scale(0.42) translate(-210 -560)">{arbol_body()}</g>',
         '</g>',
         f'<rect x="40" y="40" width="360" height="280" fill="none" stroke="{INK}" stroke-width="6"/>']
    return "".join(s)


# ---------------------------------------------------------------- fondos (1080x1920)
W, H = 1080, 1920


def fondo_liso():
    return (f'<rect width="{W}" height="{H}" fill="{P["crema"]}"/>'
            f'<rect width="{W}" height="{H}" fill="url(#dots)"/>'), \
           ('<pattern id="dots" width="64" height="64" patternUnits="userSpaceOnUse">'
            '<circle cx="16" cy="16" r="5" fill="#F4DFBE"/><circle cx="48" cy="48" r="5" fill="#F4DFBE"/></pattern>')


def fondo_burst():
    cx, cy = 540, 950
    s = [f'<rect width="{W}" height="{H}" fill="#FFC23E"/>']
    n = 28
    for i in range(0, n, 2):
        a1 = i * 2 * math.pi / n
        a2 = (i + 1) * 2 * math.pi / n
        R = 2400
        s.append(f'<path d="M {cx} {cy} L {cx+R*math.cos(a1):.0f} {cy+R*math.sin(a1):.0f} '
                 f'L {cx+R*math.cos(a2):.0f} {cy+R*math.sin(a2):.0f} Z" fill="#FFD76E"/>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    defs = ('<radialGradient id="vig" cx="0.5" cy="0.5" r="0.75">'
            '<stop offset="0.55" stop-color="#FF9F1C" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#FF8C00" stop-opacity="0.35"/></radialGradient>')
    return "".join(s), defs


def dormitorio(noche=False):
    wall = "#3E4482" if noche else "#FFE6C2"
    stripe = "#393F7A" if noche else "#FFDCAE"
    floor = "#6E5C80" if noche else "#D79A66"
    plank = "#5E4E70" if noche else "#C4864F"
    curtain = "#B5607A" if noche else P["coral"]
    s = [f'<rect width="{W}" height="{H}" fill="{wall}"/>']
    s += [f'<rect x="{x}" y="0" width="40" height="1200" fill="{stripe}"/>' for x in range(30, W, 110)]
    s.append(f'<rect x="0" y="1180" width="{W}" height="{H-1180}" fill="{floor}"/>')
    s += [ln(f"M 0 {y} L {W} {y}", 5, plank) for y in range(1290, H, 120)]
    s.append(f'<rect x="0" y="1160" width="{W}" height="34" fill="#fff" stroke="{INK}" stroke-width="6"/>')
    # ventana
    sky = P["noche"] if noche else P["cielo"]
    s.append(f'<rect x="560" y="480" width="380" height="380" rx="14" fill="{sky}" stroke="{INK}" stroke-width="{SW}"/>')
    if noche:
        s.append(f'<g transform="translate(690 560) scale(0.55) translate(-120 -100)">{luna()}</g>')
        for (x, y) in [(830, 560), (880, 700), (620, 760), (780, 810)]:
            s.append(estrella4(x, y, 16, "#FFE9A3", 4))
    else:
        s.append(f'<ellipse cx="650" cy="790" rx="70" ry="28" fill="#fff" opacity=".9"/>'
                 f'<ellipse cx="840" cy="620" rx="56" ry="22" fill="#fff" opacity=".9"/>')
    s.append(ln("M 750 480 L 750 860", 10) + ln("M 560 670 L 940 670", 10))
    s.append(ln("M 530 450 L 970 450", 14))
    s.append(ln("M 540 456 Q 600 640 540 880 L 510 880 L 510 456 Z", 6, INK, curtain))
    s.append(ln("M 960 456 Q 900 640 960 880 L 990 880 L 990 456 Z", 6, INK, curtain))
    # cuadro
    pic = "#8DA0C9" if noche else "#BFE6C5"
    s.append(f'<rect x="110" y="560" width="250" height="190" rx="10" fill="{P["marron"]}" stroke="{INK}" stroke-width="{SW}"/>'
             f'<rect x="134" y="584" width="202" height="142" fill="{pic}" stroke="{INK}" stroke-width="5"/>'
             + ln("M 140 720 L 200 640 L 240 690 L 280 620 L 330 720 Z", 5, INK, "#fff"))
    if noche:
        s.append(f'<rect width="{W}" height="{H}" fill="#0B1240" opacity=".18"/>')
    return "".join(s)


def fondo_piel():
    rnd = random.Random(7)
    s = [f'<rect width="{W}" height="{H}" fill="#F3B497"/>']
    for _ in range(140):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        s.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rnd.uniform(4, 9):.1f}" ry="{rnd.uniform(3, 6):.1f}" fill="#E39C7E" opacity=".55"/>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#pv)"/>')
    defs = ('<radialGradient id="pv" cx="0.5" cy="0.45" r="0.8"><stop offset="0.5" stop-color="#fff" stop-opacity="0.12"/>'
            '<stop offset="1" stop-color="#B8604A" stop-opacity="0.25"/></radialGradient>')
    return "".join(s), defs


def fondo_exterior():
    s = [f'<rect width="{W}" height="{H}" fill="url(#sky)"/>']
    for (cx, cy, k) in [(200, 560, 1.0), (820, 470, 0.8), (620, 760, 0.6)]:
        s.append(f'<g transform="translate({cx} {cy}) scale({k})">'
                 + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff"/>'
                           for x, y, r in [(-70, 10, 50), (0, -10, 70), (70, 10, 50), (0, 30, 50)]) + '</g>')
    s.append(f'<ellipse cx="250" cy="1250" rx="520" ry="200" fill="#8BD48A" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<ellipse cx="900" cy="1270" rx="480" ry="170" fill="#7CCB7A" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln(f"M -10 1300 Q 270 1250 540 1300 Q 810 1350 1090 1290 L 1090 1930 L -10 1930 Z", SW, INK, "#56B65B"))
    rnd = random.Random(5)
    for _ in range(22):
        x, y = rnd.uniform(40, 1040), rnd.uniform(1380, 1880)
        col = rnd.choice(["#fff", P["amarillo"], P["rosa"]])
        s.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="9" fill="{col}" stroke="{INK}" stroke-width="4"/>')
    defs = ('<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6CC6FF"/>'
            '<stop offset="0.6" stop-color="#CFEFFF"/></linearGradient>')
    return "".join(s), defs


def fondo_cabeza():
    rnd = random.Random(11)
    s = [f'<rect width="{W}" height="{H}" fill="#4B2E7E"/>', f'<rect width="{W}" height="{H}" fill="url(#hg)"/>']
    for _ in range(26):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        d = f"M {x:.0f} {y:.0f}"
        for _ in range(4):
            x += rnd.uniform(-120, 120)
            y += rnd.uniform(-120, 120)
            d += f" Q {x + rnd.uniform(-40, 40):.0f} {y + rnd.uniform(-40, 40):.0f} {x:.0f} {y:.0f}"
        s.append(ln(d, 6, "#FF9EB8", extra='opacity=".18"'))
    for _ in range(18):
        s.append(estrella4(rnd.uniform(40, 1040), rnd.uniform(40, 1880), rnd.uniform(8, 16), "#C9B6FF", 0))
    defs = ('<radialGradient id="hg" cx="0.5" cy="0.5" r="0.7"><stop offset="0" stop-color="#7B58BD" stop-opacity="1"/>'
            '<stop offset="1" stop-color="#2E1A55" stop-opacity="1"/></radialGradient>')
    return "".join(s), defs


# ---------------------------------------------------------------- armado
def build():
    build_vos()
    add("cama_vos", 680, 400, cama(True), anchor=(0.5, 1.0))
    add("cama_vacia", 680, 400, cama(False), anchor=(0.5, 1.0))
    add("zzz", 240, 280, zzz())
    add("sol", 260, 260, sol())
    add("luna", 200, 200, luna())
    add("flecha_gravedad", 300, 320, flecha_gravedad())
    add("regla", 120, 720, regla(), anchor=(0.5, 1.0))
    add("linea_punteada", 860, 16, linea_punteada())
    add("lupa", 320, 320, lupa(), anchor=(125 / 320, 125 / 320))
    add("flechita", 200, 140, flechita())
    add("exclamacion", 120, 260, exclamacion())
    add("brillo", 120, 120, brillo())
    add("arbol", 420, 560, arbol_body(), anchor=(0.5, 1.0))
    for i in range(11):
        add(f"columna_{i:02d}", 320, 820, columna(i / 10), anchor=(0.5, 1.0))
    add("ojo_zoom", 1000, 720, ojo_zoom())
    add("acaro", 320, 560, acaro())
    add("acaro_saluda_a", 320, 560, acaro("up", "open", wave=0))
    add("acaro_saluda_b", 320, 560, acaro("up", "open", wave=1))
    add("acaro_come_a", 320, 560, acaro("down", "chew_open", babero=True))
    add("acaro_come_b", 320, 560, acaro("down", "chew_closed", babero=True))
    ASSETS["acaro_asoma"] = svg(320, 250, acaro("up", "smile"))   # solo la parte de arriba
    META.setdefault("anchors", {})["acaro_asoma"] = [0.5, 1.0]
    add("foliculo", 160, 50, f'<ellipse cx="80" cy="25" rx="70" ry="17" fill="#5A2E2A" stroke="{INK}" stroke-width="6"/>')
    add("celulas", 240, 220, celulas())
    add("grasa", 180, 240, gota_grasa())
    diagrama()
    add("cerebro", 560, 480, cerebro())
    add("engranaje_gris", 300, 300, engranaje("#B8C2D6"))
    add("engranaje_amarillo", 300, 300, engranaje(P["amarillo"], n=8, ro=120, ri=96))
    add("marco_foto", 440, 360, marco_foto())
    for name, fn in [("fondo_liso", fondo_liso), ("fondo_burst", fondo_burst), ("fondo_piel", fondo_piel),
                     ("fondo_exterior", fondo_exterior), ("fondo_cabeza", fondo_cabeza)]:
        body, defs = fn()
        add(name, W, H, body, defs)
    add("dormitorio", W, H, dormitorio(False))
    add("dormitorio_noche", W, H, dormitorio(True))
    add("blanco", W, H, f'<rect width="{W}" height="{H}" fill="#fff"/>')

    os.makedirs(os.path.join(OUT, "svg"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "png"), exist_ok=True)
    for name, s in ASSETS.items():
        with open(os.path.join(OUT, "svg", name + ".svg"), "w") as f:
            f.write(s)
        scale = 1.0 if name.startswith(("fondo", "dormitorio", "blanco")) else RS
        cairosvg.svg2png(bytestring=s.encode(), write_to=os.path.join(OUT, "png", name + ".png"), scale=scale)
    META["rs"] = RS
    with open(os.path.join(OUT, "meta.json"), "w") as f:
        json.dump(META, f, indent=1)
    print(f"{len(ASSETS)} recursos generados")


if __name__ == "__main__":
    build()

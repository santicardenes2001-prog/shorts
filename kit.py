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
    if kind == "pain":        # > <  (dolor, ojos apretados)
        k = 1 if side == "L" else -1
        return ln(f"M {cx-28*k} {cy-24} L {cx+22*k} {cy} L {cx-28*k} {cy+24}", 10)
    if kind == "bulge":       # ojos que se salen
        return (f'<ellipse cx="{cx}" cy="{cy-6}" rx="64" ry="70" fill="#fff" stroke="{INK}" stroke-width="7"/>'
                + "".join(ln(f"M {cx+64*math.cos(a)*.95:.0f} {cy-6+70*math.sin(a)*.95:.0f} "
                             f"L {cx+40*math.cos(a+.2):.0f} {cy-6+44*math.sin(a+.2):.0f}", 3, P["rojo"])
                          for a in (0.3, 1.2, 2.3, 3.4, 4.4, 5.6))
                + f'<circle cx="{cx}" cy="{cy-6}" r="9" fill="{INK}"/>')
    raise ValueError(kind)


BROWS = {
    "neutral": ("M 168 248 Q 200 234 232 246", "M 288 246 Q 320 234 352 248"),
    "up": ("M 166 222 Q 200 202 234 218", "M 286 218 Q 320 202 354 222"),
    "asco": ("M 168 236 L 234 258", "M 286 234 Q 320 216 354 230"),
    "sad": ("M 168 258 L 232 242", "M 288 242 L 352 258"),
    "happy": ("M 168 240 Q 200 224 232 238", "M 288 238 Q 320 224 352 240"),
    "miedo": ("M 166 236 Q 196 214 234 226", "M 286 226 Q 324 214 354 236"),
    "dolor": ("M 166 222 L 232 250", "M 288 250 L 354 222"),
    "alto": ("M 160 196 Q 200 176 238 192", "M 282 192 Q 320 176 360 196"),
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
    if kind == "wavy":        # boca temblorosa de miedo
        return ln("M 214 408 Q 226 394 238 408 Q 250 422 262 408 Q 274 394 286 408 Q 298 422 310 408", 8)
    if kind in ("scream", "broken"):   # grito; "broken" con dientes que faltan
        d = "M 210 380 Q 260 364 310 380 Q 316 426 260 432 Q 204 426 210 380 Z"
        teeth = [(225, 380), (243, 376), (261, 375), (279, 376), (297, 380)]
        if kind == "broken":
            teeth = [teeth[0], teeth[3]]
        t = "".join(f'<rect x="{x-9}" y="{y-6}" width="18" height="22" rx="4" fill="#fff" stroke="{INK}" stroke-width="4"/>'
                    for x, y in teeth)
        return (f'<clipPath id="sclip"><path d="{d}"/></clipPath><path d="{d}" fill="{P["boca"]}"/>'
                f'<g clip-path="url(#sclip)"><ellipse cx="260" cy="428" rx="30" ry="14" fill="{P["lengua"]}"/>{t}</g>'
                + ln(d, 7))
    raise ValueError(kind)


HAIR = ("M 92 240 C 72 110, 190 58, 275 66 C 372 74, 452 130, 430 240 "
        "L 404 186 L 372 204 L 338 170 L 300 198 L 262 164 L 222 200 L 186 170 L 152 204 L 122 178 Z")


def head(eyes="open", brows="neutral", mouth_kind="smile", look=(0, 0), extra="", hair=None, hair_color=None):
    """Cabeza de Vos en coordenadas del lienzo de 520x820 (centro 260,270)."""
    s = []
    for x in (90, 430):
        s.append(f'<circle cx="{x}" cy="292" r="30" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<circle cx="260" cy="270" r="172" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln(hair or HAIR, SW, INK, hair_color or P["pelo"]))
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


def arms(kind, sleeve=None):
    def arm(d, hand):
        hx, hy = hand
        return (stroke_path(d, P["piel"], 28)
                + f'<circle cx="{hx}" cy="{hy}" r="25" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
    sc = sleeve or P["remera"]
    sleeves = (f'<circle cx="186" cy="500" r="30" fill="{sc}" stroke="{INK}" stroke-width="{SW}"/>'
               f'<circle cx="334" cy="500" r="30" fill="{sc}" stroke="{INK}" stroke-width="{SW}"/>')
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
    if kind == "colgado":   # manos atadas por encima de la cabeza
        back = arm("M 182 500 Q 120 300 240 34", (244, 30)) + arm("M 338 500 Q 400 300 280 34", (276, 30))
        back += "".join(ln(f"M 226 {y} L 294 {y+8}", 9, P["marron2"]) for y in (14, 34))
        return sleeves, back
    if kind == "atado":     # brazos atrás del cuerpo
        back = arm("M 182 505 Q 140 590 196 660", (200, 662)) + arm("M 338 505 Q 380 590 324 660", (320, 662))
        return sleeves, back
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


# ---------------------------------------------------------------- torturas (mazmorra)
P.update(arpillera="#C9A878", arpillera2="#A88A5C", hierro="#8E97A8", hierro2="#626B7D",
         madera="#9C6B45", madera2="#7A5236", piedra="#5E6380", piedra2="#4A4E68",
         fuego="#FF8A2B", fuego2="#FFD23F", brasa="#FF5A1F", capucha="#3A3340")

PELO_PRESO = ("M 88 250 L 70 200 L 92 180 L 80 130 L 120 120 L 120 80 L 170 86 L 190 48 L 236 70 "
              "L 270 36 L 304 70 L 350 46 L 362 90 L 412 88 L 404 130 L 450 140 L 430 186 L 452 214 L 432 250 "
              "L 404 196 L 370 214 L 338 176 L 300 206 L 262 170 L 222 206 L 186 176 L 150 210 L 118 186 Z")


def barba_preso():
    """Barba de varios días y tierra en la cara."""
    pts = [(160, 392), (176, 410), (198, 420), (222, 428), (298, 428), (322, 420), (344, 410), (360, 392),
           (188, 398), (332, 398), (206, 412), (314, 412)]
    return ("".join(f'<circle cx="{x}" cy="{y}" r="4" fill="#8A6E5A" opacity=".7"/>' for x, y in pts)
            + f'<ellipse cx="350" cy="228" rx="26" ry="12" fill="#B98A6A" opacity=".45"/>')


def cabeza_preso(eyes, brows, mouth_kind, extra=""):
    return head(eyes, brows, mouth_kind, extra=barba_preso() + extra, hair=PELO_PRESO, hair_color="#5A4433")


SUDOR = "M 0 0 C 0 0 16 24 16 34 A 16 16 0 0 1 -16 34 C -16 24 0 0 0 0 Z"


def gota_sudor(x, y, k=1.0):
    return (f'<g transform="translate({x} {y}) scale({k})">' + ln(SUDOR, 5, INK, P["cielo"])
            + ln("M -7 30 Q -7 22 -2 16", 4, "#fff") + '</g>')


def preso(eyes="wide", brows="miedo", mouth_kind="wavy", arm_kind="down", sudor=False):
    """Prisionero: túnica de arpillera rota, descalzo, pelo revuelto (lienzo 520x820 como Vos)."""
    s = [f'<ellipse cx="260" cy="806" rx="125" ry="13" fill="#000" opacity=".12"/>']
    front, back = arms(arm_kind, P["arpillera"])
    s.append(back)
    for x in (210, 268):
        s.append(f'<rect x="{x}" y="640" width="42" height="150" rx="20" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
    for x in (226, 294):
        s.append(f'<ellipse cx="{x}" cy="792" rx="36" ry="19" fill="{P["piel"]}" stroke="{INK}" stroke-width="6"/>')
    tunic = ("M 194 454 Q 260 440 326 454 Q 366 470 368 540 L 374 712 L 350 690 L 330 716 L 306 692 L 284 718 "
             "L 260 694 L 236 718 L 214 692 L 190 716 L 170 690 L 146 712 L 152 540 Q 154 470 194 454 Z")
    s.append(ln(tunic, SW, INK, P["arpillera"]))
    s.append(f'<rect x="282" y="620" width="44" height="40" rx="4" fill="{P["arpillera2"]}" stroke="{INK}" stroke-width="4" transform="rotate(8 304 640)"/>')
    s.append(ln("M 292 628 L 300 636 M 312 626 L 318 636", 3))
    s.append(ln("M 224 462 Q 260 494 296 462", 6))
    s.append(stroke_path("M 156 590 Q 260 610 364 590", P["madera2"], 12))
    if arm_kind == "atado":   # sogas que lo atan al poste
        for y in (530, 580):
            s.append(stroke_path(f"M 140 {y} Q 260 {y+22} 380 {y}", "#C79A5B", 14))
    s.append(front)
    s.append(cabeza_preso(eyes, brows, mouth_kind, gota_sudor(410, 190) if sudor else ""))
    return "".join(s)


PRESO_VARIANTS = {
    "preso_miedo": dict(sudor=True),
    "preso_grito": dict(eyes="pain", brows="dolor", mouth_kind="scream"),
    "preso_atado": dict(arm_kind="atado", sudor=True),
    "preso_atado_grito": dict(arm_kind="atado", eyes="pain", brows="dolor", mouth_kind="scream"),
}
CUERDA = 1300   # largo de soga por encima de las manos del preso colgado


def build_preso():
    for name, kw in PRESO_VARIANTS.items():
        add(name, 520, 820, preso(**kw), anchor=(0.5, 1.0))
    # colgado: lienzo más alto con la soga hacia arriba; ancla en los pies
    for name, kw in [("preso_colgado", dict(sudor=True)),
                     ("preso_colgado_grito", dict(eyes="pain", brows="dolor", mouth_kind="scream"))]:
        hgt = 820 + CUERDA
        body = (stroke_path(f"M 260 30 L 260 {-CUERDA}", "#C79A5B", 14)
                + preso(arm_kind="colgado", **kw))
        add(name, 520, hgt, f'<g transform="translate(0 {CUERDA})">{body}</g>', anchor=(0.5, (CUERDA + 806) / hgt))
    # cabezas sueltas para el aplastacabezas (ancla en el mentón)
    for name, (e, b, m) in {"cabeza_miedo": ("wide", "miedo", "wavy"),
                            "cabeza_grito": ("pain", "dolor", "scream"),
                            "cabeza_dientes": ("pain", "dolor", "broken"),
                            "cabeza_ojos": ("bulge", "alto", "broken")}.items():
        add(name, 520, 470, cabeza_preso(e, b, m), anchor=(0.5, 442 / 470))


# ---------------------------------------------------------------- verdugo
def verdugo(cara="malo"):
    s = [f'<ellipse cx="260" cy="806" rx="150" ry="14" fill="#000" opacity=".14"/>']
    for x in (196, 272):
        s.append(f'<rect x="{x}" y="640" width="52" height="150" rx="20" fill="#2F2A33" stroke="{INK}" stroke-width="{SW}"/>')
    for x in (214, 306):
        s.append(f'<ellipse cx="{x}" cy="794" rx="44" ry="22" fill="#5A3A2A" stroke="{INK}" stroke-width="6"/>')
    # brazos gruesos
    for d, h in [("M 160 500 Q 110 590 118 668", (118, 672)), ("M 360 500 Q 410 590 402 668", (402, 672))]:
        s.append(stroke_path(d, P["piel"], 46))
        s.append(f'<circle cx="{h[0]}" cy="{h[1]}" r="34" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
        s.append(ln(f"M {h[0]-14} {h[1]-8} L {h[0]+14} {h[1]-8}", 4))
    s.append(f'<rect x="138" y="440" width="244" height="250" rx="70" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 214 520 Q 236 540 258 520 M 262 520 Q 284 540 306 520", 5, P["piel2"]))
    # delantal de cuero
    s.append(ln("M 170 560 L 350 560 L 362 702 Q 260 724 158 702 Z", SW, INK, "#7A4A2E"))
    s.append(ln("M 170 500 L 196 560 M 350 500 L 324 560", 8, "#5A3420"))
    s.append(f'<rect x="226" y="600" width="68" height="44" rx="8" fill="#5A3420" stroke="{INK}" stroke-width="5"/>')
    # capucha puntiaguda
    hood = "M 74 476 Q 70 300 170 170 Q 220 96 262 30 Q 300 96 352 170 Q 450 300 446 476 Q 260 528 74 476 Z"
    s.append(ln(hood, SW, INK, P["capucha"]))
    s.append(ln("M 150 250 Q 200 200 240 170", 10, "#fff", extra='opacity=".12"'))
    for cx in (204, 316):
        s.append(f'<ellipse cx="{cx}" cy="330" rx="48" ry="40" fill="#1A1620" stroke="{INK}" stroke-width="5"/>')
        if cara == "risa":
            s.append(ln(f"M {cx-26} 342 Q {cx} 312 {cx+26} 342", 9, "#fff"))
        else:
            s.append(f'<circle cx="{cx}" cy="334" r="20" fill="#fff"/><circle cx="{cx + (6 if cx < 260 else -6)}" cy="338" r="10" fill="{INK}"/>')
    if cara == "malo":
        s.append(ln("M 150 288 L 246 312", 12, P["capucha"]) + ln("M 370 288 L 274 312", 12, P["capucha"]))
        s.append(ln("M 150 286 L 246 310", 6) + ln("M 370 286 L 274 310", 6))
    if cara == "risa":
        s.append(ln("M 214 420 Q 260 452 306 420", 7, "#fff", extra='opacity=".5"'))
    return "".join(s)


# ---------------------------------------------------------------- instrumentos
def textura_madera(x0, y0, x1, y1, n=4, seed=1):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        y = y0 + (y1 - y0) * (i + .5) / n + rnd.uniform(-6, 6)
        xa, xb = x0 + rnd.uniform(8, 30), x1 - rnd.uniform(8, 30)
        out.append(ln(f"M {xa:.0f} {y:.0f} Q {(xa+xb)/2:.0f} {y + rnd.uniform(-8, 8):.0f} {xb:.0f} {y:.0f}", 4, P["madera2"]))
    return "".join(out)


def piramide():
    """La cuna de Judas: pirámide de madera sobre un taburete (lienzo 380x560)."""
    s = []
    for d in ["M 92 360 L 40 550", "M 288 360 L 340 550", "M 190 360 L 190 556"]:
        s.append(stroke_path(d, P["madera2"], 22))
    s.append(ln("M 70 470 L 310 470", 14, P["madera2"]) + ln("M 70 470 L 310 470", 5, INK, extra='opacity=".4"'))
    s.append(f'<rect x="30" y="330" width="320" height="40" rx="10" fill="{P["madera"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 190 24 L 64 332 L 210 332 Z", SW, INK, "#B9845A"))
    s.append(ln("M 190 24 L 210 332 L 316 332 Z", SW, INK, P["madera"]))
    s.append(ln("M 150 160 Q 140 220 120 290 M 170 200 Q 168 260 160 316", 4, P["madera2"]))
    s.append(ln("M 228 150 Q 240 230 262 300", 4, P["madera2"]))
    s.append(ln("M 190 22 L 176 64 L 202 64 Z", 4, INK, "#D9DCE4"))
    return "".join(s)


def polea():
    """Viga con polea; la soga baja por la izquierda de la rueda hacia el preso (lienzo 360x300)."""
    s = [f'<rect x="0" y="16" width="360" height="56" rx="10" fill="{P["madera"]}" stroke="{INK}" stroke-width="{SW}"/>',
         textura_madera(0, 20, 360, 70, 2, 4),
         ln("M 170 72 L 150 160 M 210 72 L 230 160", 16, P["hierro2"]),
         stroke_path("M 246 170 Q 300 190 330 300", "#C79A5B", 14)]
    s.append(f'<circle cx="190" cy="170" r="64" fill="{P["hierro"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<circle cx="190" cy="170" r="44" fill="{P["hierro2"]}" stroke="{INK}" stroke-width="5"/>')
    for a in range(0, 360, 60):
        r = math.radians(a)
        s.append(ln(f"M 190 170 L {190+40*math.cos(r):.0f} {170+40*math.sin(r):.0f}", 8, P["hierro"]))
    s.append(f'<circle cx="190" cy="170" r="14" fill="{P["hierro"]}" stroke="{INK}" stroke-width="5"/>')
    s.append(stroke_path("M 128 168 L 128 310", "#C79A5B", 14))
    return "".join(s)


def garra(roja=False):
    """Garra de gato: mango de madera y cuatro uñas de hierro curvas (lienzo 560x340)."""
    met, met2 = ("#FF6A2B", "#FFB347") if roja else (P["hierro"], "#C3CAD6")
    s = [f'<rect x="20" y="148" width="210" height="44" rx="20" fill="{P["madera"]}" stroke="{INK}" stroke-width="{SW}"/>',
         ln("M 50 160 Q 120 154 200 162", 4, P["madera2"]) + ln("M 60 180 Q 130 176 210 182", 4, P["madera2"]),
         f'<rect x="214" y="138" width="40" height="64" rx="8" fill="{met}" stroke="{INK}" stroke-width="{SW}"/>']
    claw = "M 250 156 Q 410 120 480 176 Q 500 196 492 228 Q 470 196 430 186 Q 360 174 250 186 Z"
    for ang in (-30, -10, 10, 30):
        s.append(f'<g transform="rotate({ang} 250 170)">' + ln(claw, 6, INK, met)
                 + ln("M 300 160 Q 400 140 460 176", 5, met2) + '</g>')
    s.append(f'<circle cx="262" cy="170" r="34" fill="{met}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<circle cx="262" cy="170" r="10" fill="{INK}"/>')
    return "".join(s)


def resplandor(color, r=200):
    """Halo de degradado radial (para cosas al rojo vivo)."""
    return (f'<circle cx="{r}" cy="{r}" r="{r}" fill="url(#g)"/>',
            f'<radialGradient id="g"><stop offset="0" stop-color="{color}" stop-opacity=".75"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')


def llama(cx, base, w, h, fase):
    k = 1 if fase == 0 else -1
    outer = (f"M {cx-w} {base} Q {cx-w*1.1} {base-h*.5} {cx-w*.3*k} {base-h*.75} Q {cx-w*.1*k} {base-h*.95} "
             f"{cx+w*.2*k} {base-h} Q {cx+w*.15*k} {base-h*.7} {cx+w*.6} {base-h*.55} Q {cx+w*1.1} {base-h*.3} {cx+w} {base} Z")
    inner = (f"M {cx-w*.5} {base} Q {cx-w*.6} {base-h*.3} {cx-w*.05*k} {base-h*.6} "
             f"Q {cx+w*.5} {base-h*.3} {cx+w*.5} {base} Z")
    return ln(outer, 6, INK, P["fuego"]) + ln(inner, 0, "none", P["fuego2"])


def brasero(fase=0):
    """Brasero con brasas y llamas (lienzo 360x400). fase 0/1 para animar el fuego."""
    s = []
    for d in ["M 110 300 L 70 392", "M 250 300 L 290 392", "M 180 310 L 180 396"]:
        s.append(stroke_path(d, P["hierro2"], 16))
    for (cx, w, h) in [(120, 46, 150), (190, 60, 200), (255, 44, 140)]:
        s.append(llama(cx, 250, w, h if fase == 0 else h * .88, (fase + (cx > 150)) % 2))
    for x, y, r in [(110, 240, 26), (160, 232, 30), (214, 236, 28), (262, 242, 24), (190, 248, 22), (136, 252, 18)]:
        s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{P["brasa"]}" stroke="{INK}" stroke-width="5"/>'
                 f'<circle cx="{x-6}" cy="{y-6}" r="{r*.35:.0f}" fill="{P["fuego2"]}"/>')
    s.append(ln("M 50 246 L 310 246 Q 300 316 180 316 Q 60 316 50 246 Z", SW, INK, P["hierro2"]))
    s.append(ln("M 72 262 Q 120 296 180 300", 6, P["hierro"]))
    return "".join(s)


def antorcha(fase=0):
    s = [stroke_path("M 80 300 L 80 170", P["madera"], 22),
         ln("M 40 140 L 120 140 L 104 190 L 56 190 Z", SW, INK, P["hierro2"]),
         llama(80, 146, 40 if fase == 0 else 36, 120 if fase == 0 else 108, fase)]
    return "".join(s)


def poste():
    return (f'<rect x="20" y="10" width="110" height="1000" rx="10" fill="{P["madera"]}" stroke="{INK}" stroke-width="{SW}"/>'
            + textura_madera(20, 10, 130, 1000, 1, 2)
            + ln("M 50 40 L 50 980 M 100 60 L 100 960", 4, P["madera2"]))


def costillas_burbuja():
    """Burbuja tipo rayos X con unas costillas de caricatura (lienzo 300x300)."""
    s = [f'<circle cx="150" cy="150" r="140" fill="#1E2A44" stroke="{INK}" stroke-width="9"/>',
         f'<circle cx="150" cy="150" r="128" fill="none" stroke="#fff" stroke-width="5" opacity=".6"/>']
    s.append(f'<rect x="138" y="50" width="24" height="200" rx="10" fill="{P["hueso"]}" stroke="{INK}" stroke-width="5"/>')
    for i, y in enumerate([84, 120, 156, 192]):
        w = 92 - i * 6
        s.append(stroke_path(f"M 146 {y} Q {150-w} {y-10} {150-w} {y+30}", P["hueso"], 12, INK, 22))
        s.append(stroke_path(f"M 154 {y} Q {150+w} {y-10} {150+w} {y+30}", P["hueso"], 12, INK, 22))
    s.append(f'<circle cx="112" cy="92" r="6" fill="{INK}"/><circle cx="188" cy="92" r="6" fill="{INK}"/>')
    return "".join(s)


def diente():
    return ln("M 12 10 Q 30 0 48 10 Q 54 30 44 46 L 40 66 Q 34 70 32 50 L 28 50 Q 26 70 20 66 L 16 46 Q 6 30 12 10 Z",
              5, INK, "#fff")


# Aplastacabezas en tres capas que encajan (lienzo base 700x900):
#   cabeza (ancla en el mentón, x=350, y=565) < tornillo con casco < marco con mesa.
APLASTA = {"menton": [350, 565], "casco": [350, 300], "size": [700, 900]}


def aplasta_base():
    s = []
    for x in (80, 560):
        s.append(f'<rect x="{x}" y="680" width="60" height="214" rx="8" fill="{P["madera2"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<rect x="10" y="616" width="680" height="76" rx="12" fill="{P["madera"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(textura_madera(10, 620, 690, 690, 2, 7))
    for x in (130, 520):
        s.append(f'<rect x="{x}" y="60" width="50" height="566" rx="8" fill="{P["hierro"]}" stroke="{INK}" stroke-width="{SW}"/>')
        s.append(ln(f"M {x+14} 130 L {x+14} 540", 6, "#C3CAD6"))
    s.append(f'<rect x="120" y="60" width="460" height="64" rx="12" fill="{P["hierro"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 314 92 L 330 64 L 370 64 L 386 92 L 370 120 L 330 120 Z", 6, INK, P["hierro2"]))
    s.append(ln("M 120 566 L 270 566 Q 350 600 430 566 L 580 566 L 580 616 L 120 616 Z", SW, INK, P["hierro"]))
    for x, y in [(155, 92), (545, 92), (155, 590), (545, 590)]:
        s.append(f'<circle cx="{x}" cy="{y}" r="11" fill="{P["hierro2"]}" stroke="{INK}" stroke-width="4"/>')
    return "".join(s)


def aplasta_tornillo(fase=0):
    """Tornillo con manivela arriba y casco abajo (lienzo 400x380, ancla en el borde del casco).
    fase 0/1/2: la manivela vista girando."""
    s = [f'<rect x="186" y="26" width="28" height="300" fill="{P["hierro2"]}" stroke="{INK}" stroke-width="6"/>']
    for y in range(40 + fase * 8, 310, 24):
        s.append(ln(f"M 188 {y} L 212 {y+10}", 5, P["hierro"]))
    half = [160, 90, 30][fase]
    s.append(f'<rect x="{200-half}" y="10" width="{2*half}" height="28" rx="12" fill="{P["hierro"]}" stroke="{INK}" stroke-width="6"/>')
    knob = [(200 - half, 22), (200 + half, 22)] if fase < 2 else [(200, 22)]
    for i, (x, y) in enumerate(knob):
        s.append(f'<rect x="{x-16}" y="{y-40}" width="32" height="56" rx="14" fill="{P["madera"]}" stroke="{INK}" stroke-width="6"/>')
    s.append(ln("M 50 350 C 50 250, 350 250, 350 350 Z", SW, INK, P["hierro"]))
    s.append(ln("M 92 316 Q 120 284 170 274", 9, "#C3CAD6"))
    s.append(f'<rect x="40" y="336" width="320" height="30" rx="10" fill="{P["hierro2"]}" stroke="{INK}" stroke-width="6"/>')
    return "".join(s)


def aplasta_icono():
    """Aplastacabezas armado en una sola pieza (para la presentación)."""
    head_g = (f'<g transform="translate(350 565) scale(.82) translate(-260 -442)">'
              + cabeza_preso("wide", "miedo", "wavy") + '</g>')
    torn = f'<g transform="translate(150 {300-366})">{aplasta_tornillo(0)}</g>'
    return head_g + torn + aplasta_base()


def fondo_mazmorra():
    rnd = random.Random(21)
    s = [f'<rect width="{W}" height="{H}" fill="{P["piedra2"]}"/>']
    y, row = 0, 0
    while y < 1330:
        h = rnd.choice([90, 100, 110])
        x = -rnd.randint(0, 90)
        while x < W:
            w = rnd.choice([150, 180, 210])
            col = rnd.choice([P["piedra"], "#585C78", "#646987"])
            s.append(f'<rect x="{x+5}" y="{y+5}" width="{w-10}" height="{h-10}" rx="18" fill="{col}" stroke="#3B3E55" stroke-width="5"/>')
            if rnd.random() < .25:
                s.append(ln(f"M {x+30} {y+20} L {x+50} {y+40} L {x+44} {y+60}", 4, "#3B3E55"))
            x += w
        y += h
        row += 1
    # suelo de losas
    s.append(f'<rect x="0" y="1300" width="{W}" height="{H-1300}" fill="#3E3548"/>')
    for yy in range(1300, H, 110):
        s.append(ln(f"M 0 {yy} L {W} {yy}", 5, "#2E2738"))
        off = rnd.randint(0, 200)
        for xx in range(off, W, 260):
            s.append(ln(f"M {xx} {yy} L {xx-30} {yy+110}", 5, "#2E2738"))
    s.append(ln(f"M 0 1300 L {W} 1300", SW, INK))
    # resplandor de las antorchas y viñeta
    s.append(f'<circle cx="120" cy="620" r="360" fill="url(#luz)"/><circle cx="960" cy="620" r="360" fill="url(#luz)"/>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#vin)"/>')
    # cadenas colgando
    for cx, n in [(330, 7), (760, 5)]:
        for i in range(n):
            yy = i * 34
            if i % 2 == 0:
                s.append(f'<ellipse cx="{cx}" cy="{yy+18}" rx="12" ry="20" fill="none" stroke="{INK}" stroke-width="11"/>'
                         f'<ellipse cx="{cx}" cy="{yy+18}" rx="12" ry="20" fill="none" stroke="#7A8194" stroke-width="5"/>')
            else:
                s.append(f'<rect x="{cx-3}" y="{yy}" width="6" height="36" rx="3" fill="#7A8194" stroke="{INK}" stroke-width="3"/>')
    defs = ('<radialGradient id="luz"><stop offset="0" stop-color="#FFB357" stop-opacity=".35"/>'
            '<stop offset="1" stop-color="#FFB357" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="vin" cx="0.5" cy="0.45" r="0.8"><stop offset="0.55" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#000" stop-opacity="0.45"/></radialGradient>')
    return "".join(s), defs


def build_torturas():
    build_preso()
    add("verdugo", 520, 820, verdugo("malo"), anchor=(0.5, 1.0))
    add("verdugo_risa", 520, 820, verdugo("risa"), anchor=(0.5, 1.0))
    add("vos_miedo", 520, 820, vos(eyes="wide", brows="miedo", mouth_kind="wavy",
                                  extra=gota_sudor(410, 190)), anchor=(0.5, 1.0))
    add("vos_miedo__blink", 520, 820, vos(eyes="closed", brows="miedo", mouth_kind="wavy",
                                         extra=gota_sudor(410, 190)), anchor=(0.5, 1.0))
    add("vos_grito", 520, 820, vos(eyes="pain", brows="dolor", mouth_kind="scream"), anchor=(0.5, 1.0))
    add("piramide", 380, 560, piramide(), anchor=(0.5, 1.0))
    META["piramide_punta"] = [190, 24]
    add("polea", 360, 320, polea(), anchor=(128 / 360, 170 / 320))
    add("garra", 560, 340, garra(), anchor=(0.25, 0.5))
    add("garra_roja", 560, 340, garra(True), anchor=(0.25, 0.5))
    body, defs = resplandor("#FF7A1A")
    add("resplandor", 400, 400, body, defs)
    for f in (0, 1):
        add(f"brasero_{f}", 360, 400, brasero(f), anchor=(0.5, 1.0))
        add(f"antorcha_{f}", 160, 310, antorcha(f), anchor=(0.5, 1.0))
    add("poste", 150, 1020, poste(), anchor=(0.5, 1.0))
    add("costillas", 300, 300, costillas_burbuja())
    add("diente", 60, 72, diente())
    add("sudor", 40, 60, f'<g transform="translate(20 4)">{ln(SUDOR, 5, INK, P["cielo"])}</g>')
    add("aplasta_base", 700, 900, aplasta_base(), anchor=(0.5, 1.0))
    for f in range(3):
        add(f"aplasta_tornillo_{f}", 400, 380, aplasta_tornillo(f), anchor=(0.5, 366 / 380))
    add("aplasta_icono", 700, 900, aplasta_icono(), anchor=(0.5, 1.0))
    META["aplasta"] = APLASTA
    body, defs = fondo_mazmorra()
    add("fondo_mazmorra", W, H, body, defs)


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
    build_torturas()

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

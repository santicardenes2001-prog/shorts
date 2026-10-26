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
    if kind == "muerto":      # X
        return ln(f"M {cx-26} {cy-26} L {cx+26} {cy+26}", 10) + ln(f"M {cx+26} {cy-26} L {cx-26} {cy+26}", 10)
    if kind == "sin_parpados":   # ojos enormes, sin párpados
        return (f'<circle cx="{cx}" cy="{cy}" r="44" fill="#fff" stroke="{INK}" stroke-width="6"/>'
                f'<circle cx="{cx + look[0] * 8}" cy="{cy + 4}" r="9" fill="{INK}"/>')
    if kind == "dolor":       # ojos apretados: > <
        k = 1 if side == "L" else -1
        return ln(f"M {cx-30*k} {cy-24} L {cx+26*k} {cy+2} L {cx-30*k} {cy+26}", 10)
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
    if kind == "grito":       # boca muy abierta con dientes arriba
        return ('<clipPath id="gclip"><ellipse cx="260" cy="414" rx="42" ry="50"/></clipPath>'
                f'<ellipse cx="260" cy="414" rx="42" ry="50" fill="{P["boca"]}"/>'
                f'<g clip-path="url(#gclip)"><rect x="210" y="356" width="100" height="22" fill="#fff"/>'
                f'<ellipse cx="260" cy="458" rx="30" ry="16" fill="{P["lengua"]}"/></g>'
                f'<ellipse cx="260" cy="414" rx="42" ry="50" fill="none" stroke="{INK}" stroke-width="7"/>')
    if kind == "dientes":     # dientes al aire (sin labios)
        return (f'<rect x="200" y="384" width="120" height="48" rx="14" fill="#F6EBD6" stroke="{INK}" stroke-width="6"/>'
                + ln("M 202 408 L 318 408", 5) + "".join(ln(f"M {x} 386 L {x} 430", 4) for x in range(220, 320, 20)))
    if kind == "nervio":      # boca temblorosa
        return ln("M 214 404 L 232 392 L 250 406 L 268 392 L 286 406 L 304 394", 8)
    raise ValueError(kind)


HAIR = ("M 92 240 C 72 110, 190 58, 275 66 C 372 74, 452 130, 430 240 "
        "L 404 186 L 372 204 L 338 170 L 300 198 L 262 164 L 222 200 L 186 170 L 152 204 L 122 178 Z")


def head(eyes="open", brows="neutral", mouth_kind="smile", look=(0, 0), extra="", hair=HAIR, hair_color=None,
         skin=None, cheeks=True):
    """Cabeza de Vos en coordenadas del lienzo de 520x820 (centro 260,270).
    hair/hair_color/skin permiten armar otros personajes con la misma cabeza (hair=None: sin pelo)."""
    skin = skin or P["piel"]
    s = []
    for x in (90, 430):
        s.append(f'<circle cx="{x}" cy="292" r="30" fill="{skin}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<circle cx="260" cy="270" r="172" fill="{skin}" stroke="{INK}" stroke-width="{SW}"/>')
    if hair:
        s.append(ln(hair, SW, INK, hair_color or P["pelo"]))
    if cheeks:
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


def arms(kind, skin=None, sleeve=None):
    skin = skin or P["piel"]
    sleeve = sleeve or P["remera"]
    def arm(d, hand):
        hx, hy = hand
        return (stroke_path(d, skin, 28)
                + f'<circle cx="{hx}" cy="{hy}" r="25" fill="{skin}" stroke="{INK}" stroke-width="{SW}"/>')
    sleeves = (f'<circle cx="186" cy="500" r="30" fill="{sleeve}" stroke="{INK}" stroke-width="{SW}"/>'
               f'<circle cx="334" cy="500" r="30" fill="{sleeve}" stroke="{INK}" stroke-width="{SW}"/>')
    if kind == "down":
        return arm("M 182 505 Q 150 575 148 652", (148, 655)) + arm("M 338 505 Q 370 575 372 652", (372, 655)) + sleeves, ""
    if kind == "up":   # detrás de la cabeza
        back = arm("M 182 495 Q 40 430 72 150", (72, 150)) + arm("M 338 495 Q 480 430 448 150", (448, 150))
        return sleeves, back
    if kind == "thumb":
        left = arm("M 182 505 Q 150 575 148 652", (148, 655))
        right = (stroke_path("M 338 505 L 420 562 L 440 432", skin, 28)
                 + f'<rect x="428" y="368" width="24" height="52" rx="12" fill="{skin}" stroke="{INK}" stroke-width="{SW}"/>'
                 + f'<circle cx="440" cy="432" r="28" fill="{skin}" stroke="{INK}" stroke-width="{SW}"/>'
                 + ln("M 424 440 L 452 440", 5))
        return left + right + sleeves, ""
    raise ValueError(kind)


TRAJE, TRAJE2, GUANTE = "#EEF2F7", "#C9D2E0", "#F7F7F2"


def casco():
    """Escafandra de astronauta: burbuja de vidrio sobre la cabeza de Vos."""
    return (f'<circle cx="260" cy="268" r="212" fill="#BDEBFF" opacity=".22"/>'
            f'<circle cx="260" cy="268" r="212" fill="none" stroke="{INK}" stroke-width="{SW + 1}"/>'
            f'<circle cx="260" cy="268" r="203" fill="none" stroke="#fff" stroke-width="5" opacity=".55"/>'
            + ln("M 110 200 Q 130 110 220 78", 16, "#fff", extra='opacity=".75"')
            + ln("M 96 262 L 98 240", 14, "#fff", extra='opacity=".75"')
            + ln("M 392 400 Q 420 360 430 320", 9, "#fff", extra='opacity=".4"'))


def casco_safari():
    """Casco de explorador (salacot) sobre la cabeza de Vos."""
    return (ln("M 70 190 Q 260 120 450 190 Q 460 214 430 218 Q 260 176 90 218 Q 60 214 70 190 Z", SW, INK, "#D9C08A")
            + ln("M 110 196 Q 116 40 260 36 Q 404 40 410 196 Q 260 160 110 196 Z", SW, INK, "#E8D3A0")
            + ln("M 112 182 Q 260 146 408 182", 14, "#8A6A3A")
            + ln("M 170 110 Q 200 70 250 60", 10, "#fff", extra='opacity=".5"'))


def vos(eyes="open", brows="neutral", mouth_kind="smile", arm_kind="down", look=(0, 0), extra="", astro=False,
        explorador=False):
    s = [f'<ellipse cx="260" cy="806" rx="125" ry="13" fill="#000" opacity=".12"/>']
    if astro:   # mochila de oxígeno, detrás de todo
        s.append(f'<rect x="120" y="440" width="280" height="250" rx="40" fill="{TRAJE2}" stroke="{INK}" stroke-width="{SW}"/>')
        s.append(f'<rect x="132" y="470" width="30" height="120" rx="15" fill="{P["coral"]}" stroke="{INK}" stroke-width="6"/>')
    encima = ""   # brazos/objetos que van por delante de la cara (binoculares, nariz)
    if arm_kind in ("binoculares", "nariz", "linterna"):
        encima, arm_kind_base = accesorio(arm_kind), "down"
    else:
        arm_kind_base = arm_kind
    front, back = arms(arm_kind_base, GUANTE if astro else None, TRAJE if astro else None)
    if arm_kind in ("binoculares", "nariz", "linterna"):
        front = arms("down")[0] if arm_kind == "linterna" else ""
        if arm_kind == "linterna":   # solo el brazo izquierdo abajo; el derecho sostiene la linterna
            front = (stroke_path("M 182 505 Q 150 575 148 652", P["piel"], 28)
                     + f'<circle cx="148" cy="655" r="25" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>'
                     + f'<circle cx="186" cy="500" r="30" fill="{P["remera"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(back)
    legs = TRAJE if astro else P["pantalon"]
    for x in (205, 269):
        s.append(f'<rect x="{x}" y="640" width="46" height="150" rx="20" fill="{legs}" stroke="{INK}" stroke-width="{SW}"/>')
    for x in (220, 300):
        s.append(f'<ellipse cx="{x}" cy="794" rx="40" ry="21" fill="{INK}"/>')
    body = TRAJE if astro else P["remera"]
    s.append(f'<rect x="158" y="452" width="204" height="228" rx="72" fill="{body}" stroke="{INK}" stroke-width="{SW}"/>')
    if astro:   # panel del pecho y cuello de la escafandra
        s.append(f'<rect x="212" y="540" width="96" height="66" rx="14" fill="{TRAJE2}" stroke="{INK}" stroke-width="6"/>')
        for i, c in enumerate([P["rojo"], P["amarillo"], P["verde"]]):
            s.append(f'<circle cx="{234 + i * 26}" cy="573" r="9" fill="{c}" stroke="{INK}" stroke-width="4"/>')
        s.append(f'<rect x="176" y="452" width="168" height="40" rx="20" fill="{TRAJE2}" stroke="{INK}" stroke-width="{SW}"/>')
    else:
        s.append(ln("M 224 462 Q 260 494 296 462", 6))
    s.append(front)
    s.append(head(eyes, brows, mouth_kind, look, extra))
    if astro:
        s.append(casco())
    if explorador:
        s.append(casco_safari())
    s.append(encima)
    return "".join(s)


def accesorio(kind):
    """Brazos con objetos que se dibujan encima de la cara de Vos."""
    piel, manga = P["piel"], P["remera"]
    hombros = (f'<circle cx="186" cy="500" r="30" fill="{manga}" stroke="{INK}" stroke-width="{SW}"/>'
               f'<circle cx="334" cy="500" r="30" fill="{manga}" stroke="{INK}" stroke-width="{SW}"/>')
    if kind == "binoculares":
        brazos = (stroke_path("M 182 505 Q 110 440 184 330", piel, 28) + stroke_path("M 338 505 Q 410 440 336 330", piel, 28))
        bino = (f'<rect x="150" y="272" width="96" height="74" rx="22" fill="#2E3440" stroke="{INK}" stroke-width="{SW}"/>'
                f'<rect x="274" y="272" width="96" height="74" rx="22" fill="#2E3440" stroke="{INK}" stroke-width="{SW}"/>'
                f'<rect x="232" y="290" width="56" height="30" rx="8" fill="#2E3440" stroke="{INK}" stroke-width="6"/>'
                f'<circle cx="198" cy="309" r="22" fill="#7FC8F0" stroke="{INK}" stroke-width="5"/>'
                f'<circle cx="322" cy="309" r="22" fill="#7FC8F0" stroke="{INK}" stroke-width="5"/>'
                + ln("M 186 300 Q 192 292 202 292", 5, "#fff") + ln("M 310 300 Q 316 292 326 292", 5, "#fff"))
        manos = (f'<circle cx="180" cy="350" r="25" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>'
                 f'<circle cx="340" cy="350" r="25" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>')
        return brazos + hombros + bino + manos
    if kind == "nariz":   # se tapa la nariz con la mano derecha
        return (stroke_path("M 182 505 Q 150 575 148 652", piel, 28)
                + f'<circle cx="148" cy="655" r="25" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>'
                + stroke_path("M 338 505 Q 380 430 290 352", piel, 28) + hombros
                + f'<ellipse cx="272" cy="350" rx="30" ry="22" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>'
                + ln("M 252 342 L 292 342 M 254 356 L 290 356", 4))
    if kind == "linterna":   # brazo derecho estirado con una linterna; el haz sale de (500, 470)
        return (stroke_path("M 338 505 Q 400 520 440 486", piel, 28)
                + f'<circle cx="334" cy="500" r="30" fill="{manga}" stroke="{INK}" stroke-width="{SW}"/>'
                + f'<g transform="rotate(-20 470 480)"><rect x="430" y="462" width="76" height="34" rx="8" fill="#5B5566" '
                  f'stroke="{INK}" stroke-width="{SW}"/><rect x="498" y="454" width="22" height="50" rx="6" fill="#FFE27A" '
                  f'stroke="{INK}" stroke-width="{SW}"/></g>'
                + f'<circle cx="440" cy="486" r="25" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>')
    raise ValueError(kind)


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
    "vos_miedo": dict(eyes="wide", brows="sad", mouth_kind="nervio"),
    # astronauta (escafandra + traje)
    "vos_astro": dict(astro=True),
    "vos_astro_mira": dict(astro=True, look=(1, -0.3)),
    "vos_astro_sorpresa": dict(astro=True, eyes="wide", brows="up", mouth_kind="o"),
    "vos_astro_contento": dict(astro=True, eyes="happy", brows="happy", mouth_kind="open_smile"),
    "vos_astro_pulgar": dict(astro=True, eyes="happy", brows="happy", mouth_kind="open_smile", arm_kind="thumb"),
    "vos_astro_susto": dict(astro=True, eyes="wide", brows="sad", mouth_kind="o", look=(-1, 0)),
    # explorador (casco de safari)
    "vos_explo": dict(explorador=True),
    "vos_explo_mira": dict(explorador=True, look=(1, -0.3)),
    "vos_explo_sorpresa": dict(explorador=True, eyes="wide", brows="up", mouth_kind="o"),
    "vos_explo_asco": dict(explorador=True, **{k: v for k, v in dict(eyes="squint", brows="asco", mouth_kind="bleh").items()},
                           extra=f'<ellipse cx="165" cy="372" rx="34" ry="20" fill="{P["verde"]}" opacity=".7"/>'
                                 f'<ellipse cx="355" cy="372" rx="34" ry="20" fill="{P["verde"]}" opacity=".7"/>'),
    "vos_explo_miedo": dict(explorador=True, eyes="wide", brows="sad", mouth_kind="nervio"),
    "vos_explo_pulgar": dict(explorador=True, eyes="happy", brows="happy", mouth_kind="open_smile", arm_kind="thumb"),
    "vos_explo_binoculares": dict(explorador=True, mouth_kind="o", arm_kind="binoculares"),
    "vos_explo_linterna": dict(explorador=True, eyes="wide", brows="sad", mouth_kind="nervio", arm_kind="linterna"),
    "vos_explo_nariz": dict(explorador=True, eyes="squint", brows="asco", mouth_kind="flat", arm_kind="nariz",
                            extra=f'<ellipse cx="165" cy="372" rx="34" ry="20" fill="{P["verde"]}" opacity=".7"/>'
                                  f'<ellipse cx="355" cy="372" rx="34" ry="20" fill="{P["verde"]}" opacity=".7"/>'),
    "vos_explo_pensando": dict(explorador=True, look=(1, -1), brows="up", mouth_kind="flat"),
}
# Variantes de parpadeo automáticas para las que tienen ojos abiertos
BLINKABLE = ["vos_neutral", "vos_mira", "vos_cansado", "vos_sorpresa", "vos_miedo", "vos_explo_linterna", "vos_explo_pensando",
             "vos_explo", "vos_explo_mira", "vos_explo_sorpresa", "vos_explo_miedo",
             "vos_astro", "vos_astro_mira", "vos_astro_sorpresa", "vos_astro_susto"]

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


# ---------------------------------------------------------------- planetas (short "3 planetas")
def cara(kind, cx, cy, k=1.0, uid="c", fill_lid=None, tinta=INK):
    """Cara genérica para planetas y objetos, en coordenadas locales (ojos en x=±62)
    y escalada por k. kind: neutral lindo malo sorpresa contento susto cool celoso.
    tinta: color de cejas y boca (más claro sobre objetos oscuros)."""
    s = []

    def L(d, w, fill="none"):
        return ln(d, w, tinta, fill)
    lid = fill_lid or INK

    def ojo(x, rx, ry, pr, look=(0, 0), hl=True, i=0):
        cid = f"{uid}o{i}"
        px, py = x + look[0] * rx * .35, look[1] * ry * .35 + 4
        o = (f'<clipPath id="{cid}"><ellipse cx="{x}" cy="0" rx="{rx}" ry="{ry}"/></clipPath>'
             f'<ellipse cx="{x}" cy="0" rx="{rx}" ry="{ry}" fill="#fff" stroke="{INK}" stroke-width="6"/>'
             f'<g clip-path="url(#{cid})"><circle cx="{px}" cy="{py}" r="{pr}" fill="{INK}"/>')
        if hl:
            o += (f'<circle cx="{px - pr * .35}" cy="{py - pr * .4}" r="{max(3, pr * .32)}" fill="#fff"/>'
                  f'<circle cx="{px + pr * .4}" cy="{py + pr * .35}" r="{max(2, pr * .14)}" fill="#fff"/>')
        return o + '</g>'

    if kind in ("neutral", "lindo", "celoso"):
        big = kind == "lindo"
        rx, ry, pr = (36, 42, 22) if big else (30, 36, 15)
        look = (1, 0) if kind == "celoso" else (0, 0)
        s += [ojo(-62, rx, ry, pr, look, i=0), ojo(62, rx, ry, pr, look, i=1)]
        if kind == "celoso":   # párpados a media asta y boca torcida
            s.append(f'<path d="M -96 -40 L -28 -40 L -28 -6 Q -62 -14 -96 -6 Z" fill="{lid}" stroke="{INK}" stroke-width="6"/>'
                     f'<path d="M 28 -40 L 96 -40 L 96 -6 Q 62 -14 28 -6 Z" fill="{lid}" stroke="{INK}" stroke-width="6"/>')
            s.append(L("M -30 70 Q 0 58 34 64", 8))
        elif big:
            s.append(L("M -26 62 Q -13 76 0 64 Q 13 76 26 62", 7))
        else:
            s.append(L("M -26 62 Q 0 82 26 62", 8))
    elif kind == "malo":
        s += [ojo(-62, 32, 30, 12, (.6, .3), hl=False, i=0), ojo(62, 32, 30, 12, (-.6, .3), hl=False, i=1)]
        # cejas en V
        s.append(L("M -108 -52 L -24 -14", 14) + L("M 108 -52 L 24 -14", 14))
        # sonrisa malvada con dientes
        mouth = "M -70 44 Q 0 66 70 44 Q 40 112 0 112 Q -40 112 -70 44 Z"
        s.append(f'<clipPath id="{uid}m"><path d="{mouth}"/></clipPath>'
                 f'<path d="{mouth}" fill="{P["boca"]}"/>'
                 f'<g clip-path="url(#{uid}m)"><rect x="-80" y="30" width="160" height="34" fill="#fff"/>'
                 + "".join(L(f"M {x} 40 L {x} 66", 4) for x in (-36, -12, 12, 36))
                 + L("M -80 64 L 80 64", 4) + '</g>' + L(mouth, 7))
    elif kind in ("sorpresa", "susto"):
        s += [ojo(-62, 36, 44, 10, i=0), ojo(62, 36, 44, 10, i=1)]
        if kind == "sorpresa":
            s.append(L("M -96 -66 Q -62 -88 -28 -70", 11) + L("M 28 -70 Q 62 -88 96 -66", 11))
            s.append(f'<ellipse cx="0" cy="76" rx="20" ry="26" fill="{P["boca"]}" stroke="{INK}" stroke-width="7"/>')
        else:
            s.append(L("M -96 -56 L -30 -72", 11) + L("M 30 -72 L 96 -56", 11))
            s.append(L("M -40 76 Q -27 62 -13 76 Q 0 90 13 76 Q 27 62 40 76", 8))
    elif kind == "contento":
        s.append(L("M -94 10 Q -62 -28 -30 10", 10) + L("M 30 10 Q 62 -28 94 10", 10))
        mouth = "M -46 50 Q 0 110 46 50 Z"
        s.append(f'<clipPath id="{uid}m"><path d="{mouth}"/></clipPath><path d="{mouth}" fill="{P["boca"]}"/>'
                 f'<g clip-path="url(#{uid}m)"><ellipse cx="0" cy="96" rx="26" ry="16" fill="{P["lengua"]}"/></g>'
                 + L(mouth, 7))
    elif kind == "cool":   # anteojos de sol
        glass = "M -112 -30 L -18 -30 L -22 8 Q -26 34 -64 34 Q -102 34 -108 8 Z"
        glass2 = "M 112 -30 L 18 -30 L 22 8 Q 26 34 64 34 Q 102 34 108 8 Z"
        s.append(L(glass, 7, "#14121A") + L(glass2, 7, "#14121A"))
        s.append(L("M -18 -24 Q 0 -32 18 -24", 7))
        s.append(ln("M -92 -18 L -70 -18", 7, "#fff", extra='opacity=".7"') + ln("M 38 -18 L 60 -18", 7, "#fff", extra='opacity=".7"'))
        s.append(L("M -20 70 Q 14 84 40 60", 8))
    else:
        raise ValueError(kind)
    return f'<g transform="translate({cx} {cy}) scale({k})">' + "".join(s) + '</g>'


def mejillas(cx, cy, k, color=None, op=.5):
    color = color or P["rosa"]
    return (f'<ellipse cx="{cx - 100 * k}" cy="{cy + 40 * k}" rx="{24 * k}" ry="{13 * k}" fill="{color}" opacity="{op}"/>'
            f'<ellipse cx="{cx + 100 * k}" cy="{cy + 40 * k}" rx="{24 * k}" ry="{13 * k}" fill="{color}" opacity="{op}"/>')


def esfera(cx, cy, r, base, bandas, uid, sombra="#000", brillo=True, contorno=INK):
    """Planeta: círculo con bandas recortadas, sombra lateral y brillo."""
    s = [f'<clipPath id="{uid}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>',
         f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{base}"/>', f'<g clip-path="url(#{uid})">']
    s += bandas
    s.append(f'<circle cx="{cx + r * .35}" cy="{cy + r * .3}" r="{r}" fill="none" stroke="{sombra}" '
             f'stroke-width="{r * .5}" opacity=".18"/>')
    s.append('</g>')
    if brillo:
        s.append(ln(f"M {cx - r * .72} {cy - r * .18} Q {cx - r * .66} {cy - r * .62} {cx - r * .22} {cy - r * .76}",
                    r * .07, "#fff", extra='opacity=".55"'))
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{contorno}" stroke-width="{SW + 1}"/>')
    return "".join(s)


def banda(cy, h, color, cx=300, w=700, curva=18, op=1):
    return (f'<path d="M {cx - w / 2} {cy} Q {cx} {cy + curva} {cx + w / 2} {cy} L {cx + w / 2} {cy + h} '
            f'Q {cx} {cy + h + curva} {cx - w / 2} {cy + h} Z" fill="{color}" opacity="{op}"/>')


def hd189733b(face="lindo"):
    """Gigante gaseoso azul cobalto (600x600, radio 250)."""
    bands = [banda(150, 40, "#4C7DFF"), banda(230, 26, "#2346A8"), banda(330, 50, "#4C7DFF", op=.8),
             banda(420, 30, "#2346A8"), banda(470, 22, "#6E97FF", op=.7),
             f'<ellipse cx="170" cy="455" rx="54" ry="20" fill="#2346A8" stroke="#1B3580" stroke-width="5"/>']
    s = esfera(300, 300, 250, "#2F5BD8", bands, "hdc")
    s += mejillas(300, 300, 1.1, P["rosa"] if face in ("lindo", "contento") else "#7A9BFF", .6)
    s += cara(face, 300, 300, 1.1, "hd")
    return s


def tres2b(face="neutral", brasa=0.0):
    """TrES-2b: esfera casi negra. brasa (0-1) agrega borde y grietas rojas encendidas."""
    bands = [banda(170, 30, "#2E2A33"), banda(260, 20, "#17141B"), banda(360, 40, "#2E2A33"), banda(450, 24, "#17141B")]
    if brasa > 0:
        bands.append(f'<circle cx="300" cy="300" r="250" fill="none" stroke="#FF4A2A" stroke-width="{46 * brasa}" '
                     f'opacity="{.55 * brasa}"/>')
        bands.append(f'<circle cx="300" cy="300" r="250" fill="none" stroke="#FFB13B" stroke-width="{12 * brasa}" '
                     f'opacity="{.7 * brasa}"/>')
        for d in ["M 90 360 L 140 380 L 170 430", "M 470 160 L 430 200 L 452 240", "M 380 500 L 420 470 L 470 480"]:
            bands.append(ln(d, 7, "#FF6A3D", extra=f'opacity="{.8 * brasa}"'))
    s = esfera(300, 300, 250, "#221F27", bands, "trc", contorno=INK)
    # borde gris para que se lea sobre el fondo oscuro
    s += f'<circle cx="300" cy="300" r="244" fill="none" stroke="#5B5566" stroke-width="5" opacity=".7"/>'
    s += cara(face, 300, 300, 1.1, "tr", fill_lid="#221F27", tinta="#FFB13B" if brasa else "#CFC8DA")
    return s


def jupiter(face="neutral"):
    bands = [banda(110, 40, "#E8C9A0"), banda(170, 46, "#C98B5A"), banda(250, 30, "#F1DDBE"),
             banda(320, 56, "#D9A06C"), banda(410, 36, "#B97A4D"), banda(470, 40, "#E8C9A0"),
             f'<ellipse cx="420" cy="440" rx="60" ry="30" fill="#D9573E" stroke="#A8432F" stroke-width="6"/>']
    s = esfera(300, 300, 250, "#F0D8B4", bands, "jpc")
    s += mejillas(300, 300, 1.1)
    s += cara(face, 300, 300, 1.1, "jp")
    return s


def tierra(face="contento"):
    land = [ln("M 120 150 Q 180 90 250 130 Q 300 170 260 220 Q 220 260 240 320 Q 200 360 150 300 Q 110 240 120 150 Z",
               0, "none", "#5BC46A"),
            ln("M 360 110 Q 440 120 470 190 Q 480 260 420 250 Q 380 220 350 170 Z", 0, "none", "#5BC46A"),
            ln("M 330 380 Q 400 360 450 420 Q 430 490 360 480 Q 310 440 330 380 Z", 0, "none", "#5BC46A"),
            f'<ellipse cx="300" cy="560" rx="200" ry="60" fill="#fff"/>',
            f'<ellipse cx="300" cy="40" rx="180" ry="50" fill="#fff"/>']
    s = esfera(300, 300, 250, "#3E8EF0", land, "tic")
    s += mejillas(300, 300, 1.1)
    s += cara(face, 300, 300, 1.1, "ti")
    return s


def cancri(face="neutral", corte=False):
    """55 Cancri e: roca oscura con grietas de lava. corte=True: cuña abierta con el interior de diamante."""
    cx = cy = 300
    r = 250
    rnd = random.Random(55)
    bands = []
    for _ in range(14):   # manchas de roca
        x, y, rr = rnd.uniform(80, 520), rnd.uniform(80, 520), rnd.uniform(20, 55)
        bands.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rr:.0f}" fill="#3A2F45" opacity=".8"/>')
    for d in ["M 50 380 L 100 400 L 120 370 L 160 390", "M 380 70 L 360 120 L 410 160",
              "M 120 430 L 180 420 L 210 470 L 270 470", "M 470 330 L 520 360", "M 330 520 L 360 470 L 420 480"]:
        bands.append(ln(d, 16, "#FF5A1F") + ln(d, 7, "#FFC23E"))
    s = esfera(cx, cy, r, "#4E3F5C", bands, "cac")
    if corte:
        # cuña de 90° hacia abajo a la derecha (de 0° a 90°): capas de corteza, manto y núcleo de diamante
        def sector(rad, fill, w=SW):
            return (f'<path d="M {cx} {cy} L {cx + rad} {cy} A {rad} {rad} 0 0 1 {cx} {cy + rad} Z" '
                    f'fill="{fill}" stroke="{INK}" stroke-width="{w}" stroke-linejoin="round"/>')
        s += sector(r, "#2A2230")
        s += sector(r - 34, "#6B5A73")          # manto de carbono
        s += sector(r - 74, "#9FE8FF")          # diamante
        # facetas del diamante
        for a in range(0, 91, 18):
            t = math.radians(a)
            s += ln(f"M {cx} {cy} L {cx + (r - 74) * math.cos(t):.1f} {cy + (r - 74) * math.sin(t):.1f}", 4, "#5CC8F0")
        for rr in (60, 120):
            s += (f'<path d="M {cx + rr} {cy} A {rr} {rr} 0 0 1 {cx} {cy + rr}" fill="none" stroke="#5CC8F0" stroke-width="4"/>')
        s += ln(f"M {cx + 40} {cy + 30} L {cx + 120} {cy + 50}", 9, "#fff", extra='opacity=".85"')
        s += ln(f"M {cx + 30} {cy + 90} L {cx + 60} {cy + 140}", 9, "#fff", extra='opacity=".7"')
        s += estrella4(cx + 110, cy + 110, 22, "#fff", 4)
        # la cara se corre arriba a la izquierda para dejar ver el corte
        s += cara(face, 230, 230, .9, "ca")
    else:
        s += mejillas(300, 300, 1.1, "#FF7A4A", .5)
        s += cara(face, 300, 300, 1.1, "ca")
    return s


def halo(color, op=0.85):
    """Resplandor redondo (degradado radial) para poner detrás de algo que brilla."""
    defs = (f'<radialGradient id="hg" cx="0.5" cy="0.5" r="0.5">'
            f'<stop offset="0.35" stop-color="{color}" stop-opacity="{op}"/>'
            f'<stop offset="0.6" stop-color="{color}" stop-opacity="{op * .4}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
    return '<circle cx="400" cy="400" r="400" fill="url(#hg)"/>', defs


def estrella_anfitriona():
    """Estrella con más rayos que el sol y cara entrecerrada por el brillo."""
    s = []
    for i in range(14):
        a = i * 360 / 14
        L = 60 if i % 2 == 0 else 40
        s.append(f'<rect x="{200 - 11}" y="{40 + (60 - L)}" width="22" height="{L}" rx="11" fill="#FFE27A" stroke="{INK}" '
                 f'stroke-width="6" transform="rotate({a} 200 200)"/>')
    s.append(f'<circle cx="200" cy="200" r="98" fill="#FFF4C2" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<circle cx="200" cy="200" r="76" fill="#FFE27A"/>')
    s.append(ln("M 160 196 Q 172 182 184 196", 7) + ln("M 216 196 Q 228 182 240 196", 7)
             + ln("M 176 226 Q 200 246 224 226", 7))
    s.append(f'<ellipse cx="150" cy="222" rx="14" ry="8" fill="{P["coral"]}" opacity=".6"/>'
             f'<ellipse cx="250" cy="222" rx="14" ry="8" fill="{P["coral"]}" opacity=".6"/>')
    return "".join(s)


def rayo_luz():
    """Haz de luz amarilla semitransparente que apunta a la derecha (ancla a la izquierda)."""
    return (f'<path d="M 0 90 L 700 0 L 700 260 L 0 170 Z" fill="#FFE27A" opacity=".45"/>'
            f'<path d="M 0 112 L 700 70 L 700 190 L 0 148 Z" fill="#FFF4C2" opacity=".55"/>')


def vidrio(kind, fill="#9ADCFF"):
    """Fragmento de vidrio filoso, alargado en horizontal (vuela hacia la derecha)."""
    shapes = {"a": "M 10 40 L 150 20 L 190 34 L 60 62 Z",
              "b": "M 8 30 L 120 8 L 150 30 L 110 52 L 30 50 Z",
              "c": "M 10 36 L 90 14 L 120 40 L 40 58 Z"}
    d = shapes[kind]
    return (ln(d, 6, INK, fill)
            + ln({"a": "M 50 42 L 140 28", "b": "M 40 32 L 110 18", "c": "M 34 38 L 86 24"}[kind], 6, "#fff",
                 extra='opacity=".85"'))


def viento():
    return (ln("M 10 40 L 300 40 Q 350 40 350 10", 9, "#fff", extra='opacity=".85"'))


def termometro(p):
    """p de 0 a 1 = nivel del líquido."""
    s = [f'<rect x="50" y="20" width="80" height="420" rx="40" fill="#fff" stroke="{INK}" stroke-width="{SW}"/>']
    top = 420 - p * 360
    s.append(f'<rect x="72" y="{top}" width="36" height="{440 - top}" rx="18" fill="{P["rojo"]}"/>')
    s.append(f'<circle cx="90" cy="470" r="62" fill="{P["rojo"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<rect x="50" y="20" width="80" height="420" rx="40" fill="none" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<rect x="72" y="380" width="36" height="80" fill="{P["rojo"]}"/>')
    for i in range(1, 9):
        y = 420 - i * 45
        s.append(ln(f"M 130 {y} L {150 if i % 2 else 160} {y}", 6))
    s.append(ln("M 70 70 L 70 300", 9, "#fff", extra='opacity=".7"'))
    s.append(f'<circle cx="70" cy="452" r="14" fill="#fff" opacity=".6"/>')
    return "".join(s)


def velocimetro():
    """Dial semicircular (400x270). La aguja va aparte (velocimetro_aguja)."""
    cx, cy, r = 200, 220, 180
    s = [ln(f"M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy} Z", SW, INK, "#fff")]
    s.append(f'<path d="M {cx + r * math.cos(math.radians(-40)):.1f} {cy + r * math.sin(math.radians(-40)):.1f} '
             f'A {r} {r} 0 0 1 {cx + r} {cy}" fill="none" stroke="{P["rojo"]}" stroke-width="30"/>')
    s.append(f'<path d="M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r * math.cos(math.radians(-140)):.1f} '
             f'{cy + r * math.sin(math.radians(-140)):.1f}" fill="none" stroke="{P["verde"]}" stroke-width="30"/>')
    for i in range(11):
        a = math.radians(180 + i * 18)
        L = 34 if i % 5 == 0 else 20
        s.append(ln(f"M {cx + (r - 22) * math.cos(a):.1f} {cy + (r - 22) * math.sin(a):.1f} "
                    f"L {cx + (r - 22 - L) * math.cos(a):.1f} {cy + (r - 22 - L) * math.sin(a):.1f}", 6))
    s.append(ln(f"M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy} Z", SW))
    s.append(f'<rect x="{cx - r - 12}" y="{cy - 4}" width="{2 * r + 24}" height="40" rx="14" fill="{TRAJE2}" stroke="{INK}" stroke-width="{SW}"/>')
    return "".join(s)


def velocimetro_aguja():
    """Aguja apuntando a la derecha; pivote en (30, 30). r=-180 apunta a la izquierda (0)."""
    return (ln("M 30 18 L 170 28 L 170 32 L 30 42 Z", 6, INK, P["rojo"])
            + f'<circle cx="30" cy="30" r="22" fill="{INK}"/><circle cx="30" cy="30" r="9" fill="#fff"/>')


def carbon(face="celoso", brasa=False):
    pts = "M 40 150 L 70 60 L 160 30 L 250 60 L 290 140 L 260 230 L 160 260 L 70 230 Z"
    fill = "#3A353D" if not brasa else "#5A2A24"
    s = [ln(pts, SW, INK, fill)]
    s.append(ln("M 70 60 L 120 120 L 160 30", 5, "#55505A") + ln("M 250 60 L 200 130 L 290 140", 5, "#55505A"))
    if brasa:
        for d in ["M 60 180 L 110 170 L 140 210", "M 200 200 L 240 180 L 270 200", "M 120 110 L 170 130 L 210 110"]:
            s.append(ln(d, 14, "#FF5A1F") + ln(d, 6, "#FFD23F"))
        s.append(f'<path d="{pts}" fill="#FF7A1A" opacity=".18"/>')
    s.append(cara(face, 165, 140, .62, "cb", fill_lid=fill, tinta="#FFD23F" if brasa else "#CFC8DA"))
    s.append(ln("M 80 90 L 110 70", 8, "#fff", extra='opacity=".3"'))
    return "".join(s)


def diamante(face="contento"):
    s = [ln("M 40 120 L 100 40 L 260 40 L 320 120 L 180 300 Z", SW, INK, "#9FE8FF")]
    s.append(ln("M 40 120 L 320 120", 5, "#5CC8F0") + ln("M 100 40 L 140 120 L 180 300", 5, "#5CC8F0")
             + ln("M 260 40 L 220 120 L 180 300", 5, "#5CC8F0") + ln("M 140 120 L 180 40 L 220 120", 5, "#5CC8F0"))
    s.append(f'<path d="M 100 40 L 140 120 L 40 120 Z" fill="#fff" opacity=".55"/>')
    s.append(ln("M 40 120 L 100 40 L 260 40 L 320 120 L 180 300 Z", SW))
    s.append(cara(face, 180, 170, .5, "dm"))
    return "".join(s)


def reloj():
    s = [f'<rect x="150" y="10" width="60" height="40" rx="10" fill="{P["amarillo"]}" stroke="{INK}" stroke-width="{SW}"/>',
         f'<circle cx="180" cy="200" r="150" fill="{P["amarillo"]}" stroke="{INK}" stroke-width="{SW}"/>',
         f'<circle cx="180" cy="200" r="122" fill="#fff" stroke="{INK}" stroke-width="{SW}"/>']
    for i in range(12):
        a = math.radians(i * 30)
        L = 22 if i % 3 == 0 else 12
        s.append(ln(f"M {180 + 108 * math.sin(a):.1f} {200 - 108 * math.cos(a):.1f} "
                    f"L {180 + (108 - L) * math.sin(a):.1f} {200 - (108 - L) * math.cos(a):.1f}", 6))
    s.append(ln("M 180 200 L 180 140", 12))
    return "".join(s)


def reloj_aguja():
    """Aguja larga apuntando arriba; pivote en el centro de abajo (ancla 0.5, 0.9)."""
    return ln("M 20 20 L 20 180", 10, INK) + f'<circle cx="20" cy="180" r="14" fill="{INK}"/>'


def llama():
    out = "M 110 20 Q 190 110 180 180 Q 172 250 110 260 Q 40 250 34 180 Q 30 120 80 90 Q 76 130 100 140 Q 90 80 110 20 Z"
    inn = "M 110 120 Q 150 170 146 205 Q 140 240 110 242 Q 76 240 74 205 Q 74 170 110 120 Z"
    return ln(out, SW, INK, "#FF7A1A") + ln(inn, 0, "none", P["amarillo"])


def atomo_c():
    s = [f'<ellipse cx="110" cy="110" rx="100" ry="38" fill="none" stroke="{INK}" stroke-width="6" transform="rotate({a} 110 110)"/>'
         for a in (0, 60, 120)]
    s.append(f'<circle cx="110" cy="110" r="44" fill="#55505A" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 126 92 Q 96 80 92 110 Q 96 140 126 128", 10, "#fff"))
    for a in (0, 120, 240):
        t = math.radians(a + 30)
        s.append(f'<circle cx="{110 + 100 * math.cos(t) * .9:.1f}" cy="{110 + 38 * math.sin(t) * 1.2:.1f}" r="10" '
                 f'fill="{P["cielo"]}" stroke="{INK}" stroke-width="5"/>')
    return "".join(s)


def flecha(color):
    """Flecha gruesa que apunta hacia abajo (rotar con r)."""
    d = ("M 75 15 Q 75 8 82 8 L 138 8 Q 145 8 145 15 L 145 120 L 200 120 "
         "L 110 225 L 20 120 L 75 120 Z")
    return ln(d, 8, INK, color) + ln("M 96 28 L 96 108", 10, "#fff", extra='opacity=".45"')


def corazon():
    d = "M 80 140 Q 10 90 14 52 Q 18 14 52 14 Q 72 14 80 38 Q 88 14 108 14 Q 142 14 146 52 Q 150 90 80 140 Z"
    return ln(d, SW, INK, P["rosa"]) + ln("M 36 44 Q 40 30 52 28", 8, "#fff", extra='opacity=".7"')


def estrellita(fill="#FFF6D6"):
    return estrella4(30, 30, 26, fill, 0)


def punto_estrella():
    return f'<circle cx="10" cy="10" r="7" fill="#FFF6D6"/>'


# ---------------------------------------------------------------- Edad Media (short "3 torturas")
PELO_PRISIONERO = ("M 84 250 C 50 120, 170 50, 270 60 C 380 66, 470 130, 438 252 L 426 300 L 404 214 L 380 236 "
                   "L 362 190 L 330 222 L 300 180 L 262 214 L 228 176 L 196 220 L 160 186 L 130 236 L 108 210 L 98 300 Z")
TUNICA, TUNICA2 = "#B89A6A", "#957A4E"


def barba():
    """Barba de varios días (va en 'extra' de head, debajo de ojos y boca)."""
    return (f'<path d="M 120 330 Q 130 440 260 446 Q 390 440 400 330 Q 360 420 260 424 Q 160 420 120 330 Z" '
            f'fill="#5A4636" opacity=".55"/>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="3" fill="#5A4636" opacity=".6"/>'
                      for x, y in [(180, 400), (200, 420), (230, 432), (290, 432), (320, 420), (340, 400), (160, 380), (360, 380)]))


PIEL_PODRIDA, PIEL_PODRIDA2 = "#B7C49A", "#93A57A"


def cabeza_prisionero(eyes="wide", brows="sad", mouth_kind="o", look=(0, 0), extra="", skin=None, hair_color="#6B4A2F"):
    return head(eyes, brows, mouth_kind, look, barba() + extra, hair=PELO_PRISIONERO, hair_color=hair_color, skin=skin)


def podredumbre(nivel):
    """Moretones, ojeras y larvas para la cara del prisionero (coordenadas de head)."""
    s = [f'<ellipse cx="200" cy="350" rx="50" ry="22" fill="#5E4A6E" opacity=".35"/>'
         f'<ellipse cx="320" cy="350" rx="50" ry="22" fill="#5E4A6E" opacity=".35"/>',
         f'<circle cx="140" cy="220" r="26" fill="#6E5A7E" opacity=".45"/><circle cx="380" cy="400" r="20" fill="#6E5A7E" opacity=".45"/>']
    if nivel >= 2:
        s.append(f'<circle cx="370" cy="210" r="30" fill="#4E6B3A" opacity=".5"/><circle cx="160" cy="420" r="22" fill="#4E6B3A" opacity=".5"/>')
        for x, y, r in [(150, 300, 20), (390, 330, 30), (230, 170, 10)]:
            s.append(ln(f"M {x - 14} {y} q 7 -10 14 0 q 7 10 14 0", 9, "#F4EED8", extra=f'transform="rotate({r} {x} {y})"'))
    return "".join(s)


def prisionero(eyes="wide", brows="sad", mouth_kind="o", arm_kind="down", look=(0, 0), extra="", desnudo=False):
    """Prisionero medieval: túnica rota, descalzo, barba y pelo revuelto (520x820, como Vos).
    desnudo=True: sin túnica (la censura de la entrepierna va aparte, en y≈675)."""
    s = [f'<ellipse cx="260" cy="806" rx="125" ry="13" fill="#000" opacity=".12"/>']
    front, back = arms(arm_kind, None, P["piel"] if desnudo else TUNICA)
    s.append(back)
    for x in (205, 269):
        s.append(f'<rect x="{x}" y="640" width="46" height="150" rx="20" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
    for x in (220, 300):
        s.append(f'<ellipse cx="{x}" cy="792" rx="36" ry="18" fill="{P["piel2"]}" stroke="{INK}" stroke-width="5"/>')
    if desnudo:
        s.append(f'<rect x="166" y="452" width="188" height="236" rx="66" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
        s.append(ln("M 196 510 Q 224 530 252 514", 5, P["piel2"]) + ln("M 324 510 Q 296 530 268 514", 5, P["piel2"]))
        s.append(ln("M 214 580 Q 230 590 246 580", 4, P["piel2"]) + ln("M 274 580 Q 290 590 306 580", 4, P["piel2"]))
        s.append(f'<circle cx="260" cy="616" r="6" fill="{P["piel2"]}"/>')
    else:
        # túnica con borde roto
        s.append(ln("M 176 470 Q 260 440 344 470 L 364 690 L 340 672 L 320 700 L 296 674 L 270 704 L 246 676 "
                    "L 222 702 L 198 674 L 174 696 L 156 690 Z", SW, INK, TUNICA))
        s.append(ln("M 196 560 L 230 590", 5, TUNICA2) + ln("M 300 610 L 330 580", 5, TUNICA2))
        s.append(f'<rect x="200" y="520" width="34" height="26" rx="6" fill="{TUNICA2}" opacity=".8"/>')
        s.append(ln("M 220 474 Q 260 500 300 474", 6))
    s.append(front)
    s.append(cabeza_prisionero(eyes, brows, mouth_kind, look, extra))
    return "".join(s)


PRISIONERO_VARIANTS = {
    "prisionero_miedo": dict(),
    "prisionero_nervio": dict(eyes="open", brows="sad", mouth_kind="nervio", look=(-1, 0)),
    "prisionero_desnudo": dict(eyes="wide", brows="sad", mouth_kind="nervio", desnudo=True),
    "prisionero_dolor": dict(eyes="dolor", brows="sad", mouth_kind="grito"),
    "prisionero_asco": dict(eyes="squint", brows="asco", mouth_kind="bleh",
                            extra=f'<ellipse cx="165" cy="372" rx="34" ry="20" fill="{P["verde"]}" opacity=".7"/>'
                                  f'<ellipse cx="355" cy="372" rx="34" ry="20" fill="{P["verde"]}" opacity=".7"/>'),
    # colgado: con los brazos "arriba" que, dado vuelta (r=180), quedan colgando hacia el piso
    "prisionero_colgado": dict(arm_kind="up", eyes="wide", brows="sad", mouth_kind="o"),
    "prisionero_colgado_grito": dict(arm_kind="up", eyes="dolor", brows="sad", mouth_kind="grito"),
}


def verdugo(eyes="mira", sostiene=False):
    """Verdugo con capucha negra; solo se le ven los ojos (520x820).
    sostiene=True: brazo derecho bien en alto, con la mano en (480, 40) para agarrar el mango de la sierra."""
    s = [f'<ellipse cx="260" cy="806" rx="140" ry="14" fill="#000" opacity=".12"/>']
    front, back = arms("down", None, "#5A1622")
    if sostiene:
        front = (stroke_path("M 182 505 Q 150 575 148 652", P["piel"], 28)
                 + f'<circle cx="148" cy="655" r="25" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>'
                 + f'<circle cx="186" cy="500" r="30" fill="#5A1622" stroke="{INK}" stroke-width="{SW}"/>')
        brazo = (stroke_path("M 338 500 Q 490 470 480 44", P["piel"], 30)
                 + f'<circle cx="480" cy="40" r="28" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>'
                 + f'<circle cx="334" cy="500" r="30" fill="#5A1622" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(back)
    for x in (200, 274):
        s.append(f'<rect x="{x}" y="640" width="50" height="150" rx="20" fill="#3A3540" stroke="{INK}" stroke-width="{SW}"/>')
    for x in (220, 300):
        s.append(f'<ellipse cx="{x}" cy="794" rx="42" ry="22" fill="{INK}"/>')
    s.append(f'<rect x="140" y="440" width="240" height="250" rx="70" fill="#7A1E2E" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<rect x="146" y="590" width="228" height="34" fill="#3A2A20" stroke="{INK}" stroke-width="6"/>'
             f'<rect x="240" y="584" width="40" height="46" rx="6" fill="{P["amarillo"]}" stroke="{INK}" stroke-width="6"/>')
    s.append(front)
    # capucha en punta, cubre toda la cabeza
    s.append(ln("M 100 330 Q 96 160 200 96 L 260 20 L 320 96 Q 424 160 420 330 Q 430 470 260 480 Q 90 470 100 330 Z",
                SW, INK, "#1E1A1F"))
    s.append(ln("M 150 150 Q 190 100 230 80", 10, "#fff", extra='opacity=".18"'))
    for cx in (200, 320):
        s.append(f'<ellipse cx="{cx}" cy="300" rx="52" ry="36" fill="#0E0C10"/>')
        if eyes == "risa":
            s.append(ln(f"M {cx-26} 308 Q {cx} 280 {cx+26} 308", 9, "#fff"))
        else:
            look = 8 if eyes == "mira" else 0
            s.append(f'<ellipse cx="{cx}" cy="302" rx="26" ry="24" fill="#fff"/>'
                     f'<circle cx="{cx + look}" cy="306" r="12" fill="{INK}"/>')
    # cejas enojadas pintadas sobre la capucha
    s.append(ln("M 150 252 L 236 278", 12, "#0E0C10") + ln("M 370 252 L 284 278", 12, "#0E0C10"))
    if sostiene:
        s.append(brazo)
    return "".join(s)


def barcas(face="miedo", miel=False):
    """Dos barcas, una encima de la otra, con el prisionero adentro: asoman cabeza, manos y pies (760x420).
    face: miedo asco dolor nervio podrido1 podrido2."""
    faces = {"miedo": dict(), "asco": PRISIONERO_VARIANTS["prisionero_asco"],
             "dolor": dict(eyes="dolor", brows="sad", mouth_kind="grito"),
             "nervio": dict(eyes="open", brows="sad", mouth_kind="nervio", look=(1, 0)),
             "podrido1": dict(eyes="dolor", brows="sad", mouth_kind="grito", skin=PIEL_PODRIDA, extra=podredumbre(1)),
             "podrido2": dict(eyes="muerto", brows="sad", mouth_kind="o", skin=PIEL_PODRIDA2, extra=podredumbre(2),
                              hair_color="#6E6A60")}
    kw = {k: v for k, v in faces[face].items() if k in ("eyes", "brows", "mouth_kind", "look", "extra", "skin", "hair_color")}
    kw = dict(dict(eyes="wide", brows="sad", mouth_kind="o"), **kw)
    piel = kw.get("skin") or P["piel"]
    madera, madera2, madera3 = "#A0714D", "#7A5236", "#8A5E3E"
    s = []
    # barca de abajo
    s.append(ln("M 150 212 L 690 212 Q 680 330 560 362 L 270 362 Q 160 330 150 212 Z", SW, INK, madera))
    s.append(ln("M 176 262 L 668 262", 5, madera2) + ln("M 220 312 L 630 312", 5, madera2))
    # barca de arriba (dada vuelta, un poco más oscura)
    s.append(ln("M 150 212 L 690 212 Q 680 96 560 64 L 270 64 Q 160 96 150 212 Z", SW, INK, madera3))
    s.append(ln("M 176 162 L 668 162", 5, madera2) + ln("M 220 112 L 630 112", 5, madera2))
    s.append(ln("M 140 212 L 700 212", 12))
    if miel:
        s.append(ln("M 380 68 Q 440 60 500 68 L 498 112 Q 490 128 482 112 L 480 82 L 450 82 L 446 140 "
                    "Q 438 156 430 140 L 428 82 L 400 82 L 396 104 Q 388 120 380 104 Z", 5, INK, P["amarillo"]))
    # manos que asoman por la junta y pies a la derecha
    for x, dx in [(360, -30), (540, 30)]:
        s.append(stroke_path(f"M {x} 212 L {x + dx} 176", piel, 24) +
                 f'<circle cx="{x + dx}" cy="172" r="22" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>')
    for y in (190, 238):
        s.append(f'<ellipse cx="716" cy="{y}" rx="36" ry="22" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>')
    if face.startswith("podrido"):   # manchas en la madera y larvas
        s.append(f'<ellipse cx="420" cy="290" rx="120" ry="30" fill="#4E3A20" opacity=".45"/>'
                 f'<ellipse cx="600" cy="120" rx="70" ry="24" fill="#4E3A20" opacity=".4"/>')
        n = 6 if face == "podrido1" else 14
        rnd = random.Random(8)
        for _ in range(n):
            x, y, r = rnd.uniform(220, 660), rnd.choice([rnd.uniform(90, 190), rnd.uniform(232, 330)]), rnd.uniform(-40, 40)
            s.append(ln(f"M {x - 14:.0f} {y:.0f} q 7 -10 14 0 q 7 10 14 0", 10, "#F4EED8", extra=f'transform="rotate({r:.0f} {x:.0f} {y:.0f})"')
                     .replace('stroke="#F4EED8"', 'stroke="#F4EED8"'))
    # cabeza asomando a la izquierda
    s.append('<g transform="translate(118 200) scale(0.52) translate(-260 -290)">' + cabeza_prisionero(**kw) + '</g>')
    if miel:   # miel chorreando por la cabeza
        s.append(ln("M 44 92 Q 118 56 192 92 L 190 120 Q 182 140 174 120 L 170 104 L 150 106 L 146 154 "
                    "Q 138 172 130 154 L 126 106 L 96 106 L 92 134 Q 84 150 76 134 L 70 104 L 50 106 Z", 5, INK, P["amarillo"]))
        s.append(ln("M 80 86 Q 100 76 122 78", 6, "#fff", extra='opacity=".7"'))
    return "".join(s)


CORTE = "#C0392B"


def colgado_v(face="miedo", mitad=None):
    """Prisionero colgado cabeza abajo de los dos pies, piernas abiertas (600x900).
    Los pies quedan arriba en (130, 60) y (470, 60). mitad: None, "izq" o "der" (partido al medio)."""
    faces = {"miedo": dict(eyes="wide", brows="sad", mouth_kind="o"),
             "grito": dict(eyes="dolor", brows="sad", mouth_kind="grito"),
             "muerto": dict(eyes="muerto", brows="sad", mouth_kind="o")}
    b = []
    # piernas abiertas (en coordenadas "de pie", después se rota 180°)
    for x0, x1 in [(262, 130), (338, 470)]:
        b.append(stroke_path(f"M {x0} 600 L {x1} 830", P["piel"], 46))
        b.append(f'<ellipse cx="{x1}" cy="846" rx="40" ry="22" fill="{P["piel2"]}" stroke="{INK}" stroke-width="{SW}"/>')
    # brazos "arriba" (quedan colgando hacia el piso)
    for x0, x1 in [(232, 140), (368, 460)]:
        b.append(stroke_path(f"M {x0} 420 Q {x1} 380 {x1} 130", P["piel"], 28)
                 + f'<circle cx="{x1}" cy="126" r="25" fill="{P["piel"]}" stroke="{INK}" stroke-width="{SW}"/>')
    # túnica
    b.append(ln("M 214 390 Q 300 362 386 390 L 404 640 L 380 622 L 356 650 L 330 624 L 300 654 L 270 624 "
                "L 244 650 L 220 622 L 196 640 Z", SW, INK, TUNICA))
    b.append(f'<circle cx="214" cy="420" r="28" fill="{TUNICA}" stroke="{INK}" stroke-width="{SW}"/>'
             f'<circle cx="386" cy="420" r="28" fill="{TUNICA}" stroke="{INK}" stroke-width="{SW}"/>')
    b.append('<g transform="translate(300 220) scale(0.82) translate(-260 -270)">' + cabeza_prisionero(**faces[face]) + '</g>')
    body = '<g transform="rotate(180 300 450)">' + "".join(b) + '</g>'
    if mitad is None:
        return body
    # partido al medio: recorte por x=300 y la "carne" del corte en el borde
    clip = '<rect x="0" y="0" width="300" height="900"/>' if mitad == "izq" else '<rect x="300" y="0" width="300" height="900"/>'
    x = 284 if mitad == "izq" else 300
    corte = (f'<rect x="{x}" y="262" width="16" height="560" rx="8" fill="{CORTE}" stroke="{INK}" stroke-width="5"/>'
             + "".join(f'<rect x="{x + 3}" y="{y}" width="10" height="22" rx="5" fill="#F6EBD6"/>' for y in (330, 380, 430, 480))
             + f'<rect x="{x + 4}" y="560" width="8" height="90" rx="4" fill="#E07A6E"/>')
    return f'<clipPath id="m"><{clip[1:]}</clipPath><g clip-path="url(#m)">{body}</g>{corte}'


MUSCULO, MUSCULO2, MUSCULO3 = "#C8473F", "#E07A6E", "#9E2F2A"


def desollado(muerto=False):
    """Prisionero sin piel (estilo lámina de anatomía), atado al poste: músculo rojo con fibras,
    ojos sin párpados y dientes al aire. Mismo lienzo que el prisionero (520x820)."""
    s = [f'<ellipse cx="260" cy="806" rx="125" ry="13" fill="#000" opacity=".12"/>']
    def fibras(d, w=28):
        return stroke_path(d, MUSCULO, w) + ln(d, 4, MUSCULO2, extra='opacity=".8"')
    for d in ("M 182 505 Q 150 575 148 652", "M 338 505 Q 370 575 372 652"):
        s.append(fibras(d))
    for x in (148, 372):
        s.append(f'<circle cx="{x}" cy="655" r="24" fill="{MUSCULO}" stroke="{INK}" stroke-width="{SW}"/>')
    for x in (205, 269):
        s.append(f'<rect x="{x}" y="640" width="46" height="150" rx="20" fill="{MUSCULO}" stroke="{INK}" stroke-width="{SW}"/>')
        s.append(ln(f"M {x + 14} 660 Q {x + 22} 720 {x + 14} 780", 4, MUSCULO2) + ln(f"M {x + 32} 660 Q {x + 26} 720 {x + 32} 780", 4, MUSCULO2))
    for x in (220, 300):
        s.append(f'<ellipse cx="{x}" cy="792" rx="36" ry="18" fill="{MUSCULO3}" stroke="{INK}" stroke-width="5"/>')
    # torso: pectorales y abdominales
    s.append(f'<rect x="166" y="452" width="188" height="214" rx="64" fill="{MUSCULO}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 186 500 Q 222 540 258 510", 5, MUSCULO3) + ln("M 334 500 Q 298 540 262 510", 5, MUSCULO3))
    s.append(ln("M 260 520 L 260 650", 5, MUSCULO3))
    for y in (560, 594, 628):
        s.append(ln(f"M 220 {y} L 300 {y}", 4, MUSCULO3))
    for x in (190, 330):
        s.append(f'<circle cx="{x}" cy="500" r="26" fill="{MUSCULO}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<rect x="196" y="630" width="128" height="50" rx="12" fill="#EDE3CC" stroke="{INK}" stroke-width="6"/>')
    # cabeza sin piel ni pelo, con fibras en la cara
    fib = (ln("M 130 260 Q 160 200 230 186", 6, MUSCULO2) + ln("M 390 260 Q 360 200 290 186", 6, MUSCULO2)
           + ln("M 140 330 Q 170 400 220 410", 6, MUSCULO3) + ln("M 380 330 Q 350 400 300 410", 6, MUSCULO3)
           + ln("M 260 110 L 260 200", 6, MUSCULO3) + ln("M 200 120 Q 230 160 236 200", 5, MUSCULO2)
           + ln("M 320 120 Q 290 160 284 200", 5, MUSCULO2))
    s.append(head("muerto" if muerto else "sin_parpados", "neutral", "dientes", (0, 0), fib, hair=None, skin=MUSCULO,
                  cheeks=False).replace(ln(BROWS["neutral"][0], 13) + ln(BROWS["neutral"][1], 13), ""))
    return "".join(s)


def jarra_leche():
    s = [ln("M 60 40 L 180 40 L 196 80 Q 210 250 190 290 L 50 290 Q 30 250 44 80 Z", SW, INK, "#fff")]
    s.append(ln("M 196 110 Q 260 120 250 180 Q 240 230 196 236", 18) + ln("M 196 110 Q 260 120 250 180 Q 240 230 196 236", 8, "#fff"))
    s.append(f'<rect x="46" y="150" width="150" height="40" fill="{P["remera"]}" opacity=".85"/>')
    s.append(ln("M 60 40 L 180 40 L 196 80 Q 210 250 190 290 L 50 290 Q 30 250 44 80 Z", SW))
    s.append(ln("M 60 40 Q 40 20 30 34", SW, INK, "#fff"))
    s.append(ln("M 70 220 L 70 260", 9, "#DCE8F5"))
    return "".join(s)


def tarro_miel():
    s = [ln("M 50 90 Q 30 200 70 280 L 210 280 Q 250 200 230 90 Z", SW, INK, "#E8A317")]
    s.append(f'<rect x="40" y="56" width="200" height="44" rx="14" fill="{P["marron"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 60 96 L 220 96 L 214 124 Q 206 140 198 124 L 194 110 L 160 112 L 156 150 Q 148 168 140 150 "
                "L 136 112 L 100 112 L 96 132 Q 88 148 80 132 L 74 112 L 62 112 Z", 5, INK, P["amarillo"]))
    s.append(ln("M 80 170 Q 76 220 96 250", 10, "#fff", extra='opacity=".5"'))
    # cucharón de miel
    s.append(stroke_path("M 200 70 L 250 10", P["marron2"], 14))
    return "".join(s)


def mosca():
    """Mosca chiquita (100x80) mirando a la derecha."""
    return (f'<ellipse cx="40" cy="22" rx="24" ry="14" fill="#DDF2FF" opacity=".85" stroke="{INK}" stroke-width="4" transform="rotate(-25 40 22)"/>'
            f'<ellipse cx="58" cy="20" rx="20" ry="12" fill="#DDF2FF" opacity=".85" stroke="{INK}" stroke-width="4" transform="rotate(20 58 20)"/>'
            f'<ellipse cx="46" cy="50" rx="30" ry="20" fill="#2E2A33" stroke="{INK}" stroke-width="5"/>'
            f'<circle cx="78" cy="46" r="15" fill="#2E2A33" stroke="{INK}" stroke-width="5"/>'
            f'<circle cx="84" cy="42" r="6" fill="{P["rojo"]}"/>'
            + ln("M 30 66 L 24 76", 4) + ln("M 46 70 L 46 78", 4) + ln("M 60 68 L 66 76", 4))


def olor():
    s = []
    for x in (30, 80, 130):
        s.append(ln(f"M {x} 200 Q {x - 22} 160 {x} 120 Q {x + 22} 80 {x} 40", 12, "#8BD06A", extra='opacity=".85"'))
    return "".join(s)


def sierra():
    """Sierra de dos manos (900x200), hoja con dientes y dos mangos."""
    # el contorno vuelve de derecha a izquierda por el filo, diente por diente
    teeth = " ".join(f"L {x - 16} 158 L {x - 32} 128" for x in range(770, 140, -32))
    blade = f"M 130 60 L 770 60 L 770 128 {teeth} L 130 128 Z"
    s = [ln(blade, 6, INK, "#C8D0DC")]
    s.append(ln("M 150 80 L 740 80", 8, "#fff", extra='opacity=".6"'))
    for x in (60, 840):
        s.append(f'<rect x="{x - 40}" y="40" width="80" height="110" rx="26" fill="{P["marron"]}" stroke="{INK}" stroke-width="{SW}"/>')
        s.append(f'<rect x="{x - 14}" y="66" width="28" height="58" rx="14" fill="{P["marron2"]}"/>')
    return "".join(s)


def cuchillo():
    s = [ln("M 30 70 Q 160 20 300 60 L 300 100 L 30 100 Z", 6, INK, "#D7DEE8")]
    s.append(ln("M 60 82 Q 160 52 280 74", 6, "#fff", extra='opacity=".7"'))
    s.append(f'<rect x="300" y="50" width="26" height="66" rx="8" fill="#8E97A8" stroke="{INK}" stroke-width="6"/>')
    s.append(f'<rect x="322" y="62" width="130" height="42" rx="18" fill="{P["marron2"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<circle cx="360" cy="83" r="6" fill="#E8D7A0"/><circle cx="420" cy="83" r="6" fill="#E8D7A0"/>')
    return "".join(s)


def sombrero_bruja():
    return (ln("M 30 230 Q 150 200 270 230 Q 280 250 250 256 L 50 256 Q 20 250 30 230 Z", SW, INK, "#3B2A55")
            + ln("M 80 224 L 150 30 Q 166 0 190 30 Q 180 40 176 60 L 220 224 Z", SW, INK, "#3B2A55")
            + f'<rect x="84" y="196" width="134" height="30" fill="{P["violeta"]}" stroke="{INK}" stroke-width="6"/>'
            + f'<rect x="136" y="194" width="30" height="34" rx="4" fill="{P["amarillo"]}" stroke="{INK}" stroke-width="5"/>')


def corona():
    d = "M 30 200 L 20 60 L 90 120 L 150 30 L 210 120 L 280 60 L 270 200 Z"
    return (ln(d, SW, INK, P["amarillo"]) + f'<rect x="30" y="180" width="240" height="40" rx="10" fill="#E8B400" stroke="{INK}" stroke-width="{SW}"/>'
            + "".join(f'<circle cx="{x}" cy="200" r="11" fill="{c}" stroke="{INK}" stroke-width="4"/>'
                      for x, c in [(90, P["rojo"]), (150, P["remera"]), (210, P["verde"])]))


def poste():
    """Poste de madera alto (200x900) con anillo de hierro arriba; ancla abajo."""
    return (f'<rect x="60" y="20" width="80" height="870" rx="16" fill="{P["marron"]}" stroke="{INK}" stroke-width="{SW}"/>'
            + ln("M 82 60 L 82 860", 6, P["marron2"]) + ln("M 116 120 L 116 700", 6, P["marron2"])
            + f'<circle cx="100" cy="90" r="34" fill="none" stroke="#5B5566" stroke-width="16"/>'
            + f'<circle cx="100" cy="90" r="34" fill="none" stroke="{INK}" stroke-width="4"/>')


def cuerdas():
    """Cuerdas que atan al prisionero al poste (se ponen encima, 360x420)."""
    s = []
    for y in (90, 300):
        d = f"M 20 {y} Q 180 {y + 40} 340 {y}"
        s.append(stroke_path(d, "#C9A46A", 22))
        for x in range(60, 330, 40):
            s.append(ln(f"M {x} {y + 4 + 20 * math.sin(math.pi * (x - 20) / 320)} l 10 14", 4, "#8E6E3E"))
    return "".join(s)


def cuerda_vertical():
    """Soga que cuelga del techo (40x700); ancla arriba."""
    s = [f'<rect x="10" y="0" width="20" height="700" rx="8" fill="#C9A46A" stroke="{INK}" stroke-width="5"/>']
    s += [ln(f"M 12 {y} L 28 {y + 14}", 4, "#8E6E3E") for y in range(10, 690, 28)]
    return "".join(s)


def microbio(color, color2, face="malo"):
    rnd = random.Random(len(color))
    pts = []
    for i in range(14):
        a = i * 2 * math.pi / 14
        r = 100 + (18 if i % 2 else -6) + rnd.uniform(-6, 6)
        pts.append(f"{150 + r * math.cos(a):.1f} {150 + r * math.sin(a):.1f}")
    d = "M " + " Q ".join(f"{pts[i]} {pts[(i + 1) % 14]}" for i in range(0, 14, 2)) + " Z"
    s = [ln(d, SW, INK, color)]
    s += [f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color2}"/>' for x, y, r in [(100, 210, 14), (210, 220, 10), (220, 100, 12)]]
    s.append(cara(face, 150, 150, .6, "mb"))
    return "".join(s)


def gota():
    d = "M 60 10 C 60 10 110 80 110 112 A 50 50 0 0 1 10 112 C 10 80 60 10 60 10 Z"
    return ln(d, SW, INK, "#D7263D") + ln("M 36 104 Q 36 84 50 70", 8, "#fff", extra='opacity=".6"')


def antorcha():
    """Llama de antorcha sobre un soporte (160x300); ancla abajo."""
    s = [ln("M 60 170 L 100 170 L 92 290 L 68 290 Z", SW, INK, P["marron2"])]
    s.append(f'<rect x="44" y="150" width="72" height="32" rx="10" fill="#5B5566" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<g transform="translate(80 160) scale(0.55) translate(-110 -260)">{llama()}</g>')
    return "".join(s)


def calavera():
    s = [ln("M 40 120 Q 40 30 130 30 Q 220 30 220 120 Q 220 170 190 180 L 190 220 L 70 220 L 70 180 Q 40 170 40 120 Z",
            SW, INK, P["hueso"])]
    s.append(f'<ellipse cx="95" cy="120" rx="28" ry="32" fill="{INK}"/><ellipse cx="165" cy="120" rx="28" ry="32" fill="{INK}"/>')
    s.append(ln("M 130 150 L 118 176 L 142 176 Z", 5, INK, INK))
    s += [ln(f"M {x} 196 L {x} 220", 5) for x in (100, 130, 160)]
    return "".join(s)


# ---------------------------------------------------------------- plantas (short "3 plantas")
def euforbia(face="contento"):
    """Euforbia (planta huésped de Hydnora, 360x320, ancla abajo): mata de tallos finos,
    lisos y verdes, sin espinas ni hojas, con florcitas amarillas en las puntas."""
    rnd = random.Random(12)
    s, tips = [], []

    def rama(x, y, ang, largo, n):
        x1 = x + largo * math.sin(math.radians(ang))
        y1 = y - largo * math.cos(math.radians(ang))
        s.append(stroke_path(f"M {x:.0f} {y:.0f} Q {x + (x1 - x) * .4 + 6:.0f} {y + (y1 - y) * .5:.0f} {x1:.0f} {y1:.0f}",
                             "#9CC453", 13, INK, 23))
        if n > 0:
            for d in (-1, 1):
                rama(x1, y1, ang + d * rnd.uniform(14, 26), largo * .62, n - 1)
        else:
            tips.append((x1, y1))
    for ang in (-52, -26, 0, 24, 50):
        rama(180, 300, ang, rnd.uniform(110, 135), 1)
    for x, y in tips:
        s.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="9" fill="{P["amarillo"]}" stroke="{INK}" stroke-width="4"/>')
    s.append(ln("M 70 300 Q 180 236 290 300 Z", SW, INK, "#86B046"))
    s.append(cara(face, 180, 266, .36, "eu"))
    return "".join(s)


def raices():
    """Raíces de la planta huésped, vistas en corte (500x520, ancla arriba al centro)."""
    s = []
    for d in ["M 250 0 Q 240 120 180 200 Q 130 280 60 330", "M 250 0 Q 270 140 330 230 Q 380 310 470 360",
              "M 250 0 Q 250 200 240 330 Q 230 420 260 510", "M 180 200 Q 120 210 70 190",
              "M 330 230 Q 360 300 340 400", "M 240 330 Q 300 360 360 420"]:
        s.append(stroke_path(d, "#C9A46A", 14, INK, 24))
    return "".join(s)


def hydnora_rizoma(face="neutral"):
    """Cuerpo subterráneo de Hydnora: tallo verrugoso marrón (440x260)."""
    s = [ln("M 30 150 Q 40 70 140 80 Q 220 40 300 80 Q 410 70 420 150 Q 430 230 320 220 Q 220 250 130 220 Q 20 230 30 150 Z",
            SW, INK, "#8A5A44")]
    rnd = random.Random(4)
    for _ in range(18):
        x, y = rnd.uniform(70, 380), rnd.uniform(100, 210)
        s.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.uniform(6, 11):.0f}" fill="#6E4535" stroke="{INK}" stroke-width="3"/>')
    s.append(cara(face, 225, 150, .55, "hz", tinta=INK))
    return "".join(s)


def hydnora(apertura=0.0, face="neutral", llena=False):
    """Flor de Hydnora africana (400x440, ancla abajo): tubo verrugoso marrón y tres lóbulos
    gruesos y carnosos unidos en la punta. Al abrirse (apertura 0-1) se separan un poco y
    muestran la cara interna color salmón con cerdas. Cara en la base del tubo."""
    cx, base = 200, 430
    a = apertura
    s = [f'<ellipse cx="{cx}" cy="{base - 4}" rx="130" ry="16" fill="#000" opacity=".15"/>']
    # cavidad oscura que se ve entre los lóbulos al abrirse
    if a > 0:
        s.append(f'<path d="M 120 300 Q {cx} {110 - 20 * a:.0f} 280 300 Z" fill="#3A1414"/>')

    def lobulo(rot, ancho, tip_y, frente):
        x0, x1 = cx - ancho / 2, cx + ancho / 2
        d = f"M {x0:.0f} 306 Q {x0 - 26:.0f} 190 {cx} {tip_y:.0f} Q {x1 + 26:.0f} 190 {x1:.0f} 306 Z"
        g = f'<g transform="rotate({rot:.1f} {cx} 306)">' + ln(d, SW + 2, INK, "#7E5442")
        for (px, py) in [(cx - 30, 250), (cx + 24, 220), (cx - 10, 180), (cx + 30, 280)]:
            g += f'<circle cx="{px}" cy="{py}" r="7" fill="#64402F"/>'
        if a > 0.15 and frente:   # cara interna salmón con cerdas blancas en el borde
            inner = f"M {x0 + 22:.0f} 300 Q {x0 + 2:.0f} 200 {cx} {tip_y + 34:.0f} Q {x1 - 2:.0f} 200 {x1 - 22:.0f} 300 Z"
            op = min(1, (a - .15) * 1.6)
            g += f'<path d="{inner}" fill="#F0805A" opacity="{op:.2f}" stroke="{INK}" stroke-width="5"/>'
            for k in range(7):
                t = k / 6
                yy = tip_y + 50 + t * (250 - tip_y - 50)
                g += ln(f"M {cx - 30 + 8 * t:.0f} {yy:.0f} l -10 -6 M {cx + 30 - 8 * t:.0f} {yy:.0f} l 10 -6", 4, "#FFE2D2",
                        extra=f'opacity="{op:.2f}"')
        return g + '</g>'
    # lóbulo de atrás (centro) y los dos de adelante
    s.append(lobulo(0, 110, 70 + 26 * a, a > 0.15))
    s.append(lobulo(-(14 + 22 * a), 130, 74 + 20 * a, True))
    s.append(lobulo(14 + 22 * a, 130, 74 + 20 * a, True))
    # tubo verrugoso
    s.append(ln(f"M 100 {base} Q 90 330 128 296 L 272 296 Q 310 330 300 {base} Z", SW, INK, "#8A5A44"))
    for x, y in [(130, 360), (160, 404), (244, 330), (270, 392), (204, 412), (118, 412), (286, 350)]:
        s.append(f'<circle cx="{x}" cy="{y}" r="8" fill="#6E4535"/>')
    if llena and a > 0.5:   # escarabajos espiando entre los lóbulos
        for x, y in [(cx - 52, 262), (cx + 52, 250)]:
            s.append(f'<ellipse cx="{x}" cy="{y}" rx="20" ry="14" fill="#2E4A5C" stroke="{INK}" stroke-width="4"/>'
                     f'<circle cx="{x - 6}" cy="{y - 3}" r="4" fill="#fff"/><circle cx="{x + 7}" cy="{y - 3}" r="4" fill="#fff"/>')
    s.append(cara(face, cx, 368, .45, "hy"))
    return "".join(s)


def tallo():
    """Tallo subterráneo que une el cuerpo de Hydnora con la flor (60x240, ancla arriba)."""
    return (f'<rect x="12" y="4" width="36" height="232" rx="16" fill="#8A5A44" stroke="{INK}" stroke-width="{SW}"/>'
            + "".join(f'<circle cx="{x}" cy="{y}" r="5" fill="#6E4535"/>' for x, y in [(26, 50), (36, 110), (24, 170), (34, 210)]))


def burbuja():
    return (f'<circle cx="22" cy="22" r="18" fill="#fff" opacity=".35" stroke="#fff" stroke-width="4"/>'
            f'<circle cx="16" cy="15" r="5" fill="#fff"/>')


def hoja():
    d = "M 20 160 Q 30 40 170 20 Q 160 150 20 160 Z"
    return ln(d, SW, INK, "#6FB35A") + ln("M 30 150 Q 90 90 160 30", 6, "#4E8A3A")


def prohibido():
    return (f'<circle cx="110" cy="110" r="90" fill="none" stroke="{INK}" stroke-width="34"/>'
            f'<circle cx="110" cy="110" r="90" fill="none" stroke="{P["rojo"]}" stroke-width="22"/>'
            + ln("M 48 48 L 172 172", 34) + ln("M 48 48 L 172 172", 22, P["rojo"]))


def escarabajo(face="contento"):
    """Escarabajo pelotero mirando a la derecha (240x170)."""
    s = []
    for x in (70, 110, 150):
        s.append(ln(f"M {x} 120 L {x - 16} 158", 7) + ln(f"M {x} 120 L {x + 14} 158", 7))
    s.append(f'<ellipse cx="110" cy="96" rx="80" ry="54" fill="#2E4A5C" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 110 44 L 110 148", 5, "#1E3240"))
    s.append(ln("M 60 70 Q 80 54 104 52", 8, "#fff", extra='opacity=".35"'))
    s.append(f'<circle cx="196" cy="96" r="34" fill="#2E4A5C" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 214 68 L 236 44", 6) + ln("M 222 78 L 238 70", 6))
    s.append(cara(face, 198, 96, .26, "es", tinta="#E8E2F0"))
    return "".join(s)


def bola_estiercol():
    s = [f'<circle cx="80" cy="80" r="70" fill="#7A5236" stroke="{INK}" stroke-width="{SW}"/>']
    rnd = random.Random(3)
    for _ in range(10):
        x, y = rnd.uniform(30, 130), rnd.uniform(30, 130)
        s.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.uniform(5, 10):.0f}" fill="#5E3E28"/>')
    return "".join(s)


def punto(color, r=10):
    return f'<circle cx="{r + 2}" cy="{r + 2}" r="{r}" fill="{color}" stroke="{INK}" stroke-width="3"/>'


def jarra(face="neutral", corte=False):
    """Jarra de Nepenthes rajah (460x700, ancla abajo): urna rojo-púrpura con pintas, boca con
    peristoma rojo acanalado y la tapa pegada atrás del borde; abajo la hoja con su zarcillo.
    corte=True: se ve el líquido adentro (agua arriba y jugos digestivos abajo)."""
    s = [f'<ellipse cx="230" cy="690" rx="150" ry="14" fill="#000" opacity=".15"/>']
    body = "M 120 300 Q 40 420 60 560 Q 90 690 230 690 Q 370 690 400 560 Q 420 420 340 300 Z"
    # hoja y zarcillo que sostiene la jarra
    s.append(ln("M 210 694 Q 100 704 16 650 Q 110 636 210 694 Z", SW, INK, "#6FA84A"))
    s.append(ln("M 30 652 Q 110 668 196 690", 4, "#4E8A3A"))
    s.append(stroke_path("M 22 650 Q 0 600 40 580 Q 70 572 78 600", "#6FA84A", 10))
    # tapa: pegada atrás del peristoma, inclinada sobre la boca
    s.append(ln("M 170 268 Q 110 150 220 112 Q 360 86 336 214 Q 326 252 296 268 Z", SW, INK, "#C04658"))
    s.append(ln("M 200 230 Q 210 160 280 140", 5, "#8E2A3C") + ln("M 250 240 Q 280 190 320 170", 5, "#8E2A3C"))
    s.append(ln("M 150 180 Q 160 140 200 126", 8, "#fff", extra='opacity=".35"'))
    if corte:
        s.append(f'<clipPath id="jc"><path d="{body}"/></clipPath>')
        s.append(ln(body, SW, INK, "#F6D6DA"))
        s.append('<g clip-path="url(#jc)">'
                 f'<rect x="0" y="430" width="460" height="300" fill="#7FC8F0"/>'
                 f'<rect x="0" y="560" width="460" height="200" fill="#B5D84A"/>'
                 + ln("M 40 430 Q 120 418 230 430 Q 340 442 430 430", 6, "#fff", extra='opacity=".7"')
                 + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff" opacity=".7"/>'
                           for x, y, r in [(150, 600, 10), (260, 640, 7), (310, 590, 12), (200, 520, 8), (290, 480, 6)])
                 + '</g>')
        s.append(ln(body, SW + 3, "#B8404F") + ln(body, 3))
    else:
        s.append(ln(body, SW, INK, "#B8404F"))
        s.append(f'<clipPath id="jc"><path d="{body}"/></clipPath><g clip-path="url(#jc)">'
                 f'<rect x="0" y="560" width="460" height="200" fill="#8E2A3C" opacity=".6"/>'
                 + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#7A2238" opacity=".85"/>'
                           for x, y, r in [(110, 420, 12), (300, 380, 10), (330, 480, 14), (150, 520, 10), (250, 600, 12),
                                           (90, 600, 9), (360, 590, 10), (200, 350, 8)])
                 + ln("M 80 380 Q 100 330 140 312", 14, "#fff", extra='opacity=".3"') + '</g>')
        s.append(ln("M 150 330 L 140 640", 6, "#8E2A3C") + ln("M 310 330 L 320 640", 6, "#8E2A3C"))
    # peristoma (borde acanalado)
    s.append(f'<ellipse cx="230" cy="300" rx="125" ry="42" fill="#E0404A" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<ellipse cx="230" cy="300" rx="90" ry="24" fill="#3A1E22" stroke="{INK}" stroke-width="5"/>')
    for i in range(14):
        ang = math.pi * (i / 13)
        x0, y0 = 230 + 108 * math.cos(ang), 300 + 34 * math.sin(ang)
        s.append(ln(f"M {x0:.0f} {y0:.0f} L {230 + 124 * math.cos(ang):.0f} {300 + 41 * math.sin(ang):.0f}", 4, "#9E2A2A"))
    if face:
        s.append(cara(face, 230, 420 if not corte else 380, .7, "jr"))
    return "".join(s)


def botella():
    s = [ln("M 40 70 L 80 70 L 80 100 Q 110 120 110 160 L 110 280 Q 110 300 90 300 L 30 300 Q 10 300 10 280 "
            "L 10 160 Q 10 120 40 100 Z", SW, INK, "#CFEFFF")]
    s.append(f'<rect x="12" y="170" width="96" height="128" fill="#7FC8F0" opacity=".9"/>')
    s.append(f'<rect x="36" y="40" width="48" height="34" rx="8" fill="{P["remera"]}" stroke="{INK}" stroke-width="6"/>')
    s.append(ln("M 40 70 L 80 70 L 80 100 Q 110 120 110 160 L 110 280 Q 110 300 90 300 L 30 300 Q 10 300 10 280 "
                "L 10 160 Q 10 120 40 100 Z", SW))
    s.append(ln("M 30 150 L 30 260", 8, "#fff", extra='opacity=".7"'))
    return "".join(s)


def rana():
    s = [ln("M 30 150 Q 20 80 110 70 Q 200 80 190 150 Q 180 190 110 190 Q 40 190 30 150 Z", SW, INK, "#6FC46A")]
    for x in (70, 150):
        s.append(f'<circle cx="{x}" cy="62" r="30" fill="#6FC46A" stroke="{INK}" stroke-width="{SW}"/>'
                 f'<circle cx="{x}" cy="62" r="17" fill="#fff" stroke="{INK}" stroke-width="5"/><circle cx="{x + 3}" cy="66" r="8" fill="{INK}"/>')
    s.append(ln("M 70 130 Q 110 160 150 130", 7))
    s.append(f'<ellipse cx="50" cy="186" rx="34" ry="14" fill="#5AAE56" stroke="{INK}" stroke-width="5"/>'
             f'<ellipse cx="170" cy="186" rx="34" ry="14" fill="#5AAE56" stroke="{INK}" stroke-width="5"/>')
    return "".join(s)


def lagartija():
    s = [stroke_path("M 40 120 Q 10 90 30 60 Q 50 40 80 70", "#E0A030", 22)]
    for x, d in [(110, 1), (180, -1)]:
        s.append(stroke_path(f"M {x} 130 L {x - 14} 160", "#E0A030", 12) + stroke_path(f"M {x} 100 L {x - 14} 70", "#E0A030", 12))
    s.append(ln("M 70 115 Q 150 80 230 100 Q 270 112 270 120 Q 270 132 230 140 Q 150 150 70 125 Z", SW, INK, "#F0B840"))
    s += [f'<circle cx="{x}" cy="{y}" r="6" fill="#C98A20"/>' for x, y in [(120, 110), (150, 118), (180, 108), (200, 124)]]
    s.append(f'<circle cx="240" cy="110" r="10" fill="#fff" stroke="{INK}" stroke-width="4"/><circle cx="243" cy="111" r="5" fill="{INK}"/>')
    s.append(ln("M 248 128 Q 258 132 266 126", 4))
    return "".join(s)


def ave():
    s = [ln("M 40 110 L 10 90 L 14 130 Z", SW, INK, "#4C8DFF")]
    s.append(f'<ellipse cx="100" cy="110" rx="70" ry="52" fill="#6FA8FF" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 70 100 Q 100 70 130 104 Q 100 130 70 100 Z", 6, INK, "#4C8DFF"))
    s.append(f'<circle cx="150" cy="70" r="40" fill="#6FA8FF" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 186 66 L 216 76 L 186 86 Z", 5, INK, P["amarillo"]))
    s.append(f'<circle cx="160" cy="62" r="12" fill="#fff" stroke="{INK}" stroke-width="4"/><circle cx="163" cy="64" r="6" fill="{INK}"/>')
    s.append(ln("M 90 160 L 86 180", 5) + ln("M 116 160 L 120 180", 5))
    return "".join(s)


def rata():
    s = [stroke_path("M 40 130 Q 0 120 10 80", "#F3B6B0", 8)]
    s.append(ln("M 40 130 Q 40 70 120 70 Q 200 70 220 120 Q 230 140 200 146 L 60 146 Q 40 146 40 130 Z", SW, INK, "#9A9AA8"))
    s.append(f'<circle cx="150" cy="70" r="22" fill="#9A9AA8" stroke="{INK}" stroke-width="{SW}"/>'
             f'<circle cx="150" cy="70" r="11" fill="#F3B6B0"/>')
    s.append(f'<circle cx="190" cy="104" r="8" fill="{INK}"/><circle cx="226" cy="124" r="8" fill="#F3B6B0" stroke="{INK}" stroke-width="3"/>')
    s.append(ln("M 214 128 L 246 120", 3) + ln("M 214 132 L 246 138", 3))
    return "".join(s)


def welwitschia(hojas=1.0, rasgada=False, face="neutral"):
    """Welwitschia (1000x440, ancla abajo): tronco leñoso bajo con cara y dos hojas
    larguísimas tiradas en el suelo. hojas (0-1) = largo; rasgada = hecha tiras (tentáculos)."""
    cx, base = 500, 420
    s = [f'<ellipse cx="{cx}" cy="{base - 4}" rx="{120 + 360 * hojas:.0f}" ry="18" fill="#000" opacity=".15"/>']
    L = 100 + 260 * hojas
    for side in (-1, 1):
        x0 = cx + side * 130
        if rasgada:   # tiras onduladas
            for k in range(5):
                yk = 330 + k * 18
                lk = L * (0.75 + 0.25 * ((k * 37) % 5) / 4)
                d = (f"M {x0} {yk} Q {x0 + side * lk * .35:.0f} {yk - 40 + k * 12} {x0 + side * lk * .6:.0f} {yk + 10} "
                     f"Q {x0 + side * lk * .85:.0f} {yk + 40} {x0 + side * lk:.0f} {yk - 10 + k * 8}")
                s.append(stroke_path(d, "#6E8A3A" if k % 2 else "#86A24A", 30))
        else:
            d = (f"M {x0} 290 Q {x0 + side * L * .5:.0f} 270 {x0 + side * L:.0f} 370 "
                 f"Q {x0 + side * L * .5:.0f} 430 {x0} 414 Z")
            s.append(ln(d, SW, INK, "#86A24A"))
            for k in (1, 2, 3):
                s.append(ln(f"M {x0} {330 + k * 18} Q {x0 + side * L * .5:.0f} {320 + k * 16} {x0 + side * L * .95:.0f} {378 + k * 4}",
                            4, "#6E8A3A"))
            # puntas secas
            s.append(ln(f"M {x0 + side * L * .85:.0f} 370 Q {x0 + side * L * .95:.0f} 372 {x0 + side * L:.0f} 380", 10, "#B59A5A"))
    # tronco (como una mesa leñosa)
    s.append(ln(f"M {cx - 150} {base} Q {cx - 175} 280 {cx - 125} 230 Q {cx} 196 {cx + 125} 230 Q {cx + 175} 280 {cx + 150} {base} Z",
                SW, INK, "#8A6A4A"))
    s.append(f'<ellipse cx="{cx}" cy="236" rx="126" ry="34" fill="#A0805A" stroke="{INK}" stroke-width="6"/>')
    s.append(ln(f"M {cx - 80} 238 Q {cx} 218 {cx + 80} 238", 5, "#7A5A3A"))
    s.append(cara(face, cx, 330, .72, "ww"))
    return "".join(s)


def dino():
    """Dinosaurio cuello largo (440x420, ancla abajo), con cara simpática."""
    s = []
    for x in (150, 210, 300, 360):
        s.append(f'<rect x="{x - 22}" y="320" width="44" height="100" rx="16" fill="#6FB35A" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(stroke_path("M 120 300 Q 40 300 10 360", "#6FB35A", 40))
    s.append(f'<ellipse cx="250" cy="290" rx="150" ry="80" fill="#7FC46A" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(stroke_path("M 360 260 Q 400 160 380 70", "#7FC46A", 54))
    s.append(f'<ellipse cx="370" cy="60" rx="56" ry="40" fill="#7FC46A" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<circle cx="384" cy="50" r="12" fill="#fff" stroke="{INK}" stroke-width="4"/><circle cx="388" cy="52" r="6" fill="{INK}"/>')
    s.append(ln("M 390 76 Q 404 84 418 72", 5))
    s += [f'<circle cx="{x}" cy="{y}" r="{r}" fill="#5FA845"/>' for x, y, r in [(200, 260, 14), (260, 240, 10), (300, 290, 12)]]
    return "".join(s)


def torta():
    """Torta de cumpleaños con muchas velitas (320x320, ancla abajo)."""
    s = [f'<rect x="40" y="200" width="240" height="110" rx="20" fill="#F7C6D0" stroke="{INK}" stroke-width="{SW}"/>',
         ln("M 40 230 Q 70 260 100 230 Q 130 260 160 230 Q 190 260 220 230 Q 250 260 280 230", SW, INK, "#fff"),
         f'<rect x="80" y="120" width="160" height="90" rx="16" fill="#FFE4A8" stroke="{INK}" stroke-width="{SW}"/>',
         ln("M 80 146 Q 120 170 160 146 Q 200 170 240 146", 6, INK, "#fff")]
    for i, x in enumerate(range(96, 240, 18)):
        h = 46 + (i % 3) * 8
        s.append(f'<rect x="{x - 5}" y="{120 - h}" width="10" height="{h}" rx="4" fill="{[P["rojo"], P["remera"], P["verde"]][i % 3]}" '
                 f'stroke="{INK}" stroke-width="3"/>')
        s.append(ln(f"M {x} {112 - h} Q {x + 7} {104 - h} {x} {92 - h} Q {x - 7} {104 - h} {x} {112 - h} Z", 3, INK, "#FFB13B"))
    return "".join(s)


def gota_agua():
    d = "M 60 10 C 60 10 110 80 110 112 A 50 50 0 0 1 10 112 C 10 80 60 10 60 10 Z"
    return ln(d, SW, INK, "#5CC8F0") + ln("M 36 104 Q 36 84 50 70", 8, "#fff", extra='opacity=".7"')


# ---------------------------------------------------------------- aves (short "3 aves raras")
PZ, PZ2, PZ_PICO, PZ_MANCHA = "#8E9CAB", "#71808E", "#D8CDA0", "#B5A777"


def picozapato(ojo="abierto", pico=0.0):
    """Picozapato (Balaeniceps rex), de perfil mirando a la derecha (600x900, ancla en los pies).
    pico 0-1 = apertura de la mandíbula de abajo (para el castañeteo). ojo: abierto | cerrado."""
    s = [f'<ellipse cx="282" cy="884" rx="130" ry="14" fill="#000" opacity=".15"/>']
    # patas (la "rodilla" de las aves dobla hacia atrás) y dedos largos
    for x0, xk, xf in [(252, 238, 248), (318, 330, 318)]:
        s.append(stroke_path(f"M {x0} 640 L {xk} 760 L {xf} 872", "#4A4F58", 18))
        s.append(ln(f"M {xf} 872 L {xf - 52} 884 M {xf} 872 L {xf + 46} 886 M {xf} 872 L {xf - 6} 888", 9, "#4A4F58"))
    # cola, cuerpo y ala
    s.append(ln("M 196 600 Q 150 690 176 716 Q 214 700 236 640 Z", SW, INK, PZ2))
    s.append(f'<ellipse cx="290" cy="520" rx="128" ry="178" fill="{PZ}" stroke="{INK}" stroke-width="{SW}" transform="rotate(-12 290 520)"/>')
    s.append(ln("M 214 420 Q 300 400 360 470 Q 380 580 320 670 Q 250 690 210 640 Q 180 540 214 420 Z", SW, INK, PZ2))
    for y in (480, 530, 580, 630):
        s.append(ln(f"M 226 {y} Q 270 {y + 16} 330 {y - 6}", 4, "#5E6C79"))
    # cuello grueso
    s.append(ln("M 286 400 Q 296 330 320 290 L 410 300 Q 400 360 396 430 Z", SW, INK, PZ))
    # cabeza y copete
    s.append(f'<circle cx="358" cy="250" r="90" fill="#9DAAB8" stroke="{INK}" stroke-width="{SW}"/>')
    for d in ("M 286 226 Q 262 214 254 194", "M 290 244 Q 262 240 248 226", "M 296 210 Q 280 190 282 170"):
        s.append(stroke_path(d, "#9DAAB8", 12))
    # pico en forma de zueco: mandíbula de abajo (rota para abrir) y de arriba
    bisagra = (410, 262)
    lower = "M 410 262 L 562 262 Q 552 314 470 330 Q 414 336 396 310 Z"
    if pico > 0:
        s.append(f'<path d="M 410 262 L 566 262 L 560 {262 + 44 * pico:.0f} Z" fill="#5A3A3A" transform="rotate({8 * pico:.1f} 410 262)"/>')
    s.append(f'<g transform="rotate({14 * pico:.1f} {bisagra[0]} {bisagra[1]})">' + ln(lower, SW, INK, PZ_PICO)
             + f'<circle cx="470" cy="300" r="10" fill="{PZ_MANCHA}"/><circle cx="520" cy="290" r="7" fill="{PZ_MANCHA}"/></g>')
    upper = "M 396 192 Q 480 168 562 204 Q 600 222 594 262 Q 592 282 572 290 Q 578 266 560 262 L 410 262 Z"
    s.append(ln(upper, SW, INK, PZ_PICO))
    s.append(ln("M 430 216 Q 500 204 556 226", 5, PZ_MANCHA))
    for x, y, r in [(452, 236, 10), (500, 230, 8), (540, 242, 7), (476, 250, 6)]:
        s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{PZ_MANCHA}"/>')
    s.append(ln("M 404 262 L 566 262", 6))
    # ojo pálido de mirada fija y ceja severa
    if ojo == "cerrado":
        s.append(ln("M 362 244 Q 380 254 398 244", 8))
    else:
        s.append(f'<circle cx="380" cy="240" r="17" fill="#EDE8C0" stroke="{INK}" stroke-width="5"/>'
                 f'<circle cx="384" cy="241" r="6" fill="{INK}"/>')
    s.append(ln("M 352 214 L 408 226", 10))
    return "".join(s)


UR, UR2, UR3 = "#9A8A72", "#6E604E", "#B8A88E"


def urutau(modo="rama"):
    """Urutaú (Nyctibius griseus) parado en la punta de un tronco roto, mimetizado (360x760, ancla abajo).
    modo: rama (ojos cerrados con ranuras) | ojos (enormes y amarillos) | boca (abierta enorme) | canto."""
    s = [f'<ellipse cx="180" cy="752" rx="80" ry="10" fill="#000" opacity=".15"/>']
    # tronco roto
    s.append(ln("M 120 760 L 128 484 L 150 474 L 160 494 L 180 468 L 200 490 L 222 476 L 236 760 Z", SW, INK, "#7A6650"))
    for d in ("M 148 520 Q 140 600 150 700", "M 200 540 Q 210 620 200 720", "M 176 600 L 176 660"):
        s.append(ln(d, 5, "#5E4E3C"))
    # cuerpo alargado y vertical, como si siguiera el tronco
    body = "M 180 478 Q 106 470 108 340 Q 108 250 122 196 Q 140 150 180 148 Q 220 150 238 196 Q 252 250 252 340 Q 254 470 180 478 Z"
    s.append(ln(body, SW, INK, UR))
    s.append(f'<clipPath id="ub"><path d="{body}"/></clipPath><g clip-path="url(#ub)">')
    rnd = random.Random(9)
    for _ in range(28):
        x, y = rnd.uniform(112, 248), rnd.uniform(270, 470)
        s.append(ln(f"M {x:.0f} {y:.0f} l {rnd.uniform(-8, 8):.0f} {rnd.uniform(10, 22):.0f}", 4, UR2))
    for _ in range(10):
        s.append(f'<ellipse cx="{rnd.uniform(116, 244):.0f}" cy="{rnd.uniform(280, 460):.0f}" rx="9" ry="5" fill="{UR3}"/>')
    s.append('</g>')
    ojos = (140, 220)
    if modo == "boca":
        # boca abierta enorme: la mitad de arriba de la cabeza se levanta y parece partirse en dos
        s.append(ln("M 104 262 Q 180 330 256 262 Q 180 150 104 262 Z", SW, INK, "#7A1E2E"))
        s.append(ln("M 126 262 Q 180 312 234 262 Q 180 196 126 262 Z", 0, "none", "#E8788A"))
        s.append(ln("M 104 248 Q 110 150 180 96 Q 250 150 256 248 Q 180 196 104 248 Z", SW, INK, UR))
        for x in ojos:
            s.append(f'<circle cx="{x}" cy="176" r="24" fill="#F5C518" stroke="{INK}" stroke-width="5"/>'
                     f'<circle cx="{x}" cy="178" r="9" fill="{INK}"/><circle cx="{x - 7}" cy="170" r="5" fill="#fff"/>')
        s.append(ln("M 174 100 L 180 82 L 188 100 Z", 4, INK, UR2))
        return "".join(s)
    s.append(ln("M 172 152 L 180 132 L 190 152 Z", 5, INK, UR2))
    s.append(ln("M 116 262 Q 180 286 244 262", 5, UR2))   # comisura ancha de la boca
    if modo == "ojos":
        for x in ojos:
            s.append(f'<circle cx="{x}" cy="212" r="34" fill="#F5C518" stroke="{INK}" stroke-width="6"/>'
                     f'<circle cx="{x}" cy="214" r="12" fill="{INK}"/><circle cx="{x - 10}" cy="202" r="7" fill="#fff"/>')
    else:
        for x in ojos:   # párpados cerrados con dos ranuritas
            s.append(f'<ellipse cx="{x}" cy="212" rx="32" ry="24" fill="{UR3}" stroke="{INK}" stroke-width="5"/>')
            s.append(ln(f"M {x - 28} 214 Q {x} 228 {x + 28} 214", 5))
            if modo == "rama":
                for dx in (-10, 10):
                    s.append(f'<circle cx="{x + dx}" cy="220" r="4.5" fill="#F5C518" stroke="{INK}" stroke-width="1.5"/>')
        if modo == "canto":
            s.append(ln("M 104 186 L 140 196 M 256 186 L 220 196", 7))
            s.append(f'<ellipse cx="180" cy="270" rx="16" ry="20" fill="#7A1E2E" stroke="{INK}" stroke-width="5"/>')
    return "".join(s)


def urutau_ojo(modo="ranura", mira=0):
    """Primer plano del ojo del urutaú (700x460). modo: ranura (cerrado, se ve por dos muescas;
    mira -1/0/1 mueve la pupila) | abierto (enorme y amarillo, con brillo)."""
    cx, cy = 350, 230
    s = [f'<ellipse cx="{cx}" cy="{cy}" rx="330" ry="210" fill="{UR}" stroke="{INK}" stroke-width="{SW}"/>']
    rnd = random.Random(5)
    for _ in range(40):
        x, y = rnd.uniform(40, 660), rnd.uniform(40, 420)
        if ((x - cx) / 300) ** 2 + ((y - cy) / 190) ** 2 < 1 and abs(y - cy) > 120 or abs(x - cx) > 230:
            s.append(ln(f"M {x:.0f} {y:.0f} l {rnd.uniform(-14, 14):.0f} {rnd.uniform(14, 30):.0f}", 6, UR2))
    if modo == "abierto":
        s.append(f'<circle cx="{cx}" cy="{cy}" r="150" fill="#F5C518" stroke="{INK}" stroke-width="{SW}"/>')
        s.append(f'<circle cx="{cx}" cy="{cy + 6}" r="58" fill="{INK}"/>')
        s.append(f'<circle cx="{cx - 50}" cy="{cy - 52}" r="26" fill="#fff"/><circle cx="{cx + 40}" cy="{cy + 40}" r="10" fill="#fff"/>')
        for a in range(0, 360, 30):
            t = math.radians(a)
            s.append(ln(f"M {cx + 70 * math.cos(t):.0f} {cy + 6 + 70 * math.sin(t):.0f} L {cx + 135 * math.cos(t):.0f} "
                        f"{cy + 6 + 135 * math.sin(t):.0f}", 4, "#D9A800"))
        return "".join(s)
    # párpado cerrado: la línea del ojo y dos muescas por donde se ve el iris amarillo
    s.append(f'<ellipse cx="{cx}" cy="{cy}" rx="170" ry="120" fill="{UR3}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln(f"M {cx - 160} {cy + 10} Q {cx} {cy + 70} {cx + 160} {cy + 10}", SW + 2))
    for mx in (-60, 60):
        x0 = cx + mx
        y0 = cy + 10 + 60 * (1 - (mx / 160) ** 2) - 6
        s.append(f'<clipPath id="m{mx + 100}"><path d="M {x0 - 22} {y0 - 6} L {x0} {y0 + 26} L {x0 + 22} {y0 - 6} Z"/></clipPath>')
        s.append(f'<path d="M {x0 - 22} {y0 - 6} L {x0} {y0 + 26} L {x0 + 22} {y0 - 6} Z" fill="#F5C518"/>')
        s.append(f'<g clip-path="url(#m{mx + 100})"><circle cx="{x0 + 10 * mira}" cy="{y0 + 8}" r="11" fill="{INK}"/></g>')
        s.append(ln(f"M {x0 - 22} {y0 - 6} L {x0} {y0 + 26} L {x0 + 22} {y0 - 6}", 5))
    return "".join(s)


HO_CUERPO, HO_CREMA, HO_RUFO, HO_ALA = "#8A5A3A", "#E8C98A", "#C0703A", "#9E4A2A"


def hoacin(ojo="abierto"):
    """Hoacín (Opisthocomus hoazin) posado, mirando a la derecha (520x640, ancla en las patas, y=590).
    Cresta de plumas en punta, piel azul en la cara, ojo rojo, cuerpo marrón con rayas crema."""
    s = []
    # cola larga que cuelga
    s.append(ln("M 220 430 Q 150 520 132 630 Q 160 640 186 626 Q 220 530 262 456 Z", SW, INK, "#4E3A2A"))
    s.append(ln("M 134 612 Q 160 626 184 612", 12, HO_CREMA))
    # cuerpo, pecho, panza y ala
    s.append(f'<ellipse cx="282" cy="420" rx="118" ry="98" fill="{HO_CUERPO}" stroke="{INK}" stroke-width="{SW}" transform="rotate(-25 282 420)"/>')
    s.append(f'<ellipse cx="334" cy="430" rx="58" ry="78" fill="{HO_CREMA}"/>')
    s.append(f'<ellipse cx="318" cy="486" rx="56" ry="34" fill="{HO_RUFO}"/>')
    s.append(ln("M 196 360 Q 280 330 320 400 Q 300 480 230 500 Q 180 470 196 360 Z", SW, INK, HO_ALA))
    for d in ("M 214 390 Q 250 380 290 410", "M 210 424 Q 250 416 286 444", "M 214 458 Q 246 452 270 472"):
        s.append(ln(d, 6, HO_CREMA))
    # patas agarrando la rama
    for x in (286, 326):
        s.append(ln(f"M {x} 506 L {x - 4} 584", 9, "#5A4A3A") + ln(f"M {x - 4} 584 l -18 8 M {x - 4} 584 l 16 8", 7, "#5A4A3A"))
    # cuello con rayas
    s.append(stroke_path("M 330 350 Q 344 290 366 236", HO_CUERPO, 46))
    s.append(ln("M 340 330 Q 350 300 362 270", 6, HO_CREMA))
    # cresta en punta (va detrás de la cabeza)
    for i in range(9):
        a = math.radians(-160 + i * 17)
        x0, y0 = 366 + 30 * math.cos(a), 176 + 30 * math.sin(a)
        x1, y1 = 366 + 104 * math.cos(a), 176 + 98 * math.sin(a)
        s.append(stroke_path(f"M {x0:.0f} {y0:.0f} L {x1:.0f} {y1:.0f}", "#D98A3A" if i % 2 else "#E8A84A", 12))
        s.append(f'<circle cx="{x1:.0f}" cy="{y1:.0f}" r="7" fill="#4E3A2A"/>')
    # cabeza, piel azul y ojo rojo; pico corto
    s.append(f'<circle cx="372" cy="196" r="50" fill="#7A4A2A" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<ellipse cx="396" cy="194" rx="30" ry="24" fill="#4FA8E0" stroke="{INK}" stroke-width="4"/>')
    if ojo == "cerrado":
        s.append(ln("M 386 196 Q 398 204 410 196", 6))
    else:
        s.append(f'<circle cx="398" cy="194" r="11" fill="#C0392B" stroke="{INK}" stroke-width="3"/><circle cx="400" cy="194" r="4.5" fill="{INK}"/>')
    s.append(ln("M 416 206 Q 446 206 458 216 Q 440 224 414 220 Z", 5, INK, "#5A5A62"))
    return "".join(s)


def hoacin_pichon(frame=0):
    """Pichón de hoacín trepando, con dos garras en cada ala (320x320). frame 0/1 alterna las alas."""
    s = []
    up = 1 if frame == 0 else -1
    for side, (x0, y0) in ((-1, (118, 170)), (1, (202, 160))):
        tip = (x0 + side * 92, y0 - 40 * up * side + (10 if side > 0 else 0))
        s.append(stroke_path(f"M {x0} {y0} Q {x0 + side * 50} {y0 - 30} {tip[0]} {tip[1]}", "#5E4A3A", 26))
        for k in (0, 1):   # dos garras en la punta del ala
            gx, gy = tip[0] + side * 8, tip[1] - 6 + k * 14
            s.append(stroke_path(f"M {gx - side * 6} {gy} Q {gx + side * 16} {gy - 2} {gx + side * 14} {gy + 16}", "#F0E6CC", 7))
    s.append(f'<ellipse cx="160" cy="190" rx="70" ry="78" fill="#6E5A48" stroke="{INK}" stroke-width="{SW}"/>')
    for a in range(0, 360, 30):   # pelusa
        t = math.radians(a)
        s.append(f'<circle cx="{160 + 70 * math.cos(t):.0f}" cy="{190 + 78 * math.sin(t):.0f}" r="10" fill="#6E5A48"/>')
    s.append(f'<ellipse cx="164" cy="210" rx="36" ry="44" fill="#A08A70"/>')
    for x in (140, 182):
        s.append(ln(f"M {x} 262 L {x - 2} 296", 8, "#4A3A2A") + ln(f"M {x - 2} 296 l -12 6 M {x - 2} 296 l 12 6", 6, "#4A3A2A"))
    s.append(f'<circle cx="186" cy="104" r="42" fill="#6E5A48" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 172 66 L 166 46 M 186 64 L 188 42 M 198 68 L 208 50", 6, "#8A6A50"))
    s.append(f'<circle cx="200" cy="100" r="13" fill="#fff" stroke="{INK}" stroke-width="4"/><circle cx="204" cy="101" r="6" fill="{INK}"/>')
    s.append(ln("M 222 112 L 242 118 L 222 124 Z", 4, INK, "#5A5A62"))
    return "".join(s)


def rama(hojas=True):
    """Rama larga con hojas (900x260); la parte de arriba (y≈120) sirve de percha."""
    s = [stroke_path("M 10 150 Q 300 110 520 128 Q 720 140 890 100", "#7A5A3A", 34)]
    s.append(stroke_path("M 520 128 Q 600 70 660 40", "#7A5A3A", 18))
    s.append(ln("M 60 144 Q 200 124 300 126", 5, "#5E4430"))
    if hojas:
        for x, y, r in [(80, 160, 30), (230, 150, -20), (650, 50, 40), (700, 30, -30), (820, 110, 20), (870, 90, -40)]:
            s.append(f'<g transform="translate({x} {y}) rotate({r})">'
                     + ln("M 0 0 Q 40 -36 90 0 Q 40 36 0 0 Z", 5, INK, "#5FA845") + ln("M 4 0 L 84 0", 3, "#3E8A3A") + '</g>')
    return "".join(s)


def pez_pulmonado():
    s = [ln("M 20 70 Q 120 30 260 50 Q 320 60 330 70 Q 320 84 260 92 Q 120 110 20 70 Z", SW, INK, "#7A8A6A")]
    s.append(ln("M 20 70 L 0 50 L 6 90 Z", 5, INK, "#6A7A5A"))
    s += [f'<circle cx="{x}" cy="{y}" r="6" fill="#5A6A4A"/>' for x, y in [(80, 66), (130, 60), (180, 74), (220, 62)]]
    s.append(ln("M 150 90 L 140 112 M 200 92 L 196 114", 5))
    s.append(f'<circle cx="294" cy="62" r="9" fill="#fff" stroke="{INK}" stroke-width="3"/><circle cx="296" cy="63" r="4" fill="{INK}"/>')
    s.append(ln("M 318 76 Q 310 82 300 80", 4))
    return "".join(s)


def cocodrilo_bebe(cara_kind="susto"):
    s = [stroke_path("M 40 110 Q 10 100 4 80", "#5FA845", 20)]
    for x in (90, 170):
        s.append(stroke_path(f"M {x} 120 L {x - 6} 148", "#5FA845", 14))
    s.append(ln("M 30 110 Q 40 70 120 66 Q 200 62 260 88 Q 280 100 262 112 Q 200 126 120 128 Q 50 130 30 110 Z", SW, INK, "#6FC456"))
    s += [ln(f"M {x} 70 l 8 -10 l 8 10", 4, INK, "#5FA845") for x in (80, 110, 140)]
    s.append(f'<circle cx="214" cy="66" r="22" fill="#6FC456" stroke="{INK}" stroke-width="5"/>')
    s.append(f'<circle cx="214" cy="64" r="13" fill="#fff" stroke="{INK}" stroke-width="3"/><circle cx="216" cy="66" r="6" fill="{INK}"/>')
    if cara_kind == "susto":
        s.append(ln("M 200 40 L 228 46", 6))
    s.append(ln("M 220 104 L 262 104", 4))
    s += [ln(f"M {x} 104 l 4 6 l 4 -6", 3, INK, "#fff") for x in (228, 240, 252)]
    return "".join(s)


def zueco():
    """Zueco (zapato de madera) visto de costado (320x170), para comparar con el pico."""
    s = [ln("M 20 120 Q 20 60 90 50 L 200 40 Q 290 40 304 100 Q 310 130 280 140 L 60 150 Q 20 150 20 120 Z", SW, INK, "#C9A46A")]
    s.append(ln("M 120 44 Q 160 90 230 70 Q 270 60 290 80", 6, "#8E6E3E"))
    s.append(ln("M 60 140 L 280 132", 6, "#8E6E3E"))
    s.append(ln("M 60 70 Q 80 58 110 54", 8, "#fff", extra='opacity=".5"'))
    return "".join(s)


def vaca():
    s = [f'<rect x="40" y="110" width="220" height="120" rx="50" fill="#fff" stroke="{INK}" stroke-width="{SW}"/>']
    s += [f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{INK}"/>' for x, y, rx, ry in [(100, 150, 26, 20), (180, 190, 22, 16)]]
    for x in (80, 120, 190, 230):
        s.append(f'<rect x="{x - 10}" y="220" width="20" height="40" rx="6" fill="#fff" stroke="{INK}" stroke-width="5"/>')
    s.append(f'<ellipse cx="270" cy="110" rx="56" ry="50" fill="#fff" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 236 70 Q 226 46 240 40 M 300 70 Q 312 46 298 40", 8, INK))
    s.append(f'<ellipse cx="280" cy="140" rx="40" ry="24" fill="#F7B6C2" stroke="{INK}" stroke-width="5"/>')
    s.append(f'<circle cx="268" cy="140" r="5" fill="{INK}"/><circle cx="292" cy="140" r="5" fill="{INK}"/>')
    s.append(f'<circle cx="252" cy="100" r="8" fill="{INK}"/><circle cx="290" cy="100" r="8" fill="{INK}"/>')
    return "".join(s)


def jaguar(cara_kind="mira"):
    """Jaguar caminando hacia la derecha (440x280); cara_kind: mira | asco."""
    s = [stroke_path("M 60 120 Q 10 110 20 60", "#E8A83A", 18)]
    for x in (110, 150, 290, 330):
        s.append(f'<rect x="{x - 14}" y="170" width="28" height="90" rx="12" fill="#E8A83A" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 60 130 Q 70 80 180 80 L 300 84 Q 360 90 360 150 Q 350 196 300 196 L 110 196 Q 60 190 60 130 Z", SW, INK, "#F0B84A"))
    rnd = random.Random(2)
    for _ in range(14):
        x, y = rnd.uniform(90, 330), rnd.uniform(100, 180)
        s.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="10" fill="none" stroke="#6A4A2A" stroke-width="5"/>')
    s.append(f'<circle cx="376" cy="110" r="52" fill="#F0B84A" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<circle cx="346" cy="66" r="14" fill="#F0B84A" stroke="{INK}" stroke-width="5"/><circle cx="398" cy="64" r="14" fill="#F0B84A" stroke="{INK}" stroke-width="5"/>')
    s.append(f'<ellipse cx="400" cy="128" rx="22" ry="16" fill="#FBE3B0"/><path d="M 404 116 L 416 116 L 410 124 Z" fill="{INK}"/>')
    if cara_kind == "asco":
        s.append(ln("M 360 96 Q 370 88 382 96 M 392 96 Q 402 88 414 96", 6))
        s.append(ln("M 396 142 Q 404 136 412 144 Q 418 150 424 142", 5) + f'<ellipse cx="420" cy="150" rx="8" ry="10" fill="{P["lengua"]}" stroke="{INK}" stroke-width="3"/>')
        s.append(f'<ellipse cx="370" cy="126" rx="12" ry="8" fill="{P["verde"]}" opacity=".7"/>')
    else:
        s += [f'<circle cx="{x}" cy="100" r="8" fill="#2A2420"/>' for x in (368, 404)]
        s.append(ln("M 400 140 Q 410 146 418 140", 4))
    return "".join(s)


def polilla():
    return (f'<ellipse cx="28" cy="34" rx="26" ry="20" fill="#C9B89A" stroke="{INK}" stroke-width="4" transform="rotate(-20 28 34)"/>'
            f'<ellipse cx="62" cy="34" rx="26" ry="20" fill="#C9B89A" stroke="{INK}" stroke-width="4" transform="rotate(20 62 34)"/>'
            f'<ellipse cx="45" cy="40" rx="8" ry="20" fill="#8A7A5A" stroke="{INK}" stroke-width="4"/>'
            + ln("M 42 22 Q 34 6 26 4 M 48 22 Q 56 6 64 4", 3))


def luciernaga():
    defs = ('<radialGradient id="lg" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#F7FF9A" stop-opacity="1"/>'
            '<stop offset=".35" stop-color="#E8F05A" stop-opacity=".7"/><stop offset="1" stop-color="#E8F05A" stop-opacity="0"/></radialGradient>')
    return '<circle cx="30" cy="30" r="30" fill="url(#lg)"/><circle cx="30" cy="30" r="5" fill="#FFFFE0"/>', defs


def nota_musical():
    return (ln("M 30 90 L 30 14 L 70 6 L 70 74", 8, INK)
            + f'<ellipse cx="20" cy="92" rx="18" ry="13" fill="#7A9BFF" stroke="{INK}" stroke-width="5"/>'
            + f'<ellipse cx="60" cy="76" rx="18" ry="13" fill="#7A9BFF" stroke="{INK}" stroke-width="5"/>'
            + ln("M 30 14 L 70 6", 12, INK))


def cursor_mano():
    """Cursor de mano con el dedo índice (110x150); la punta del dedo en (38, 8)."""
    d = ("M 30 14 Q 38 2 46 14 L 46 66 Q 52 56 62 62 Q 70 56 78 64 Q 86 60 94 70 L 96 104 Q 96 138 66 142 "
         "L 48 142 Q 22 138 14 110 L 6 86 Q 4 72 18 74 L 30 90 Z")
    return ln(d, 6, INK, "#fff") + ln("M 62 64 L 62 92 M 78 66 L 78 94", 4)


def campana():
    d = "M 90 30 Q 150 30 156 110 Q 160 150 176 166 L 4 166 Q 20 150 24 110 Q 30 30 90 30 Z"
    return (ln(d, SW, INK, P["amarillo"]) + f'<circle cx="90" cy="186" r="16" fill="{P["amarillo"]}" stroke="{INK}" stroke-width="6"/>'
            + f'<rect x="80" y="10" width="20" height="24" rx="8" fill="{P["amarillo"]}" stroke="{INK}" stroke-width="6"/>'
            + ln("M 50 60 Q 56 44 72 40", 8, "#fff", extra='opacity=".6"'))


def anillo():
    return f'<circle cx="100" cy="100" r="80" fill="none" stroke="#fff" stroke-width="14"/>'


def tronco_roto():
    """Tronco roto suelto (como el del urutaú, para comparar), 200x420, ancla abajo."""
    s = [ln("M 40 420 L 48 120 L 70 110 L 80 130 L 100 92 L 120 126 L 142 112 L 156 420 Z", SW, INK, "#7A6650")]
    for d in ("M 68 160 Q 60 260 70 380", "M 120 170 Q 130 280 120 400"):
        s.append(ln(d, 5, "#5E4E3C"))
    return "".join(s)


# ---------------------------------------------------------------- océano profundo (short "3 animales del océano")
KIWA, KIWA_PELO, KIWA2 = "#EDE3CC", "#D9C38A", "#CFC2A4"


def cangrejo_yeti(pose="quieto", bacterias=False):
    """Cangrejo yeti (Kiwa): cuerpo pálido, pinzas larguísimas cubiertas de pelos, ojitos atrofiados.
    pose: quieto | baila_a | baila_b | come. 700x420, ancla abajo."""
    puntas = {"quieto": ((90, 260), (610, 260)), "baila_a": ((70, 110), (640, 230)),
              "baila_b": ((60, 230), (630, 100)), "come": ((140, 250), (378, 292))}[pose]
    s = [f'<ellipse cx="350" cy="410" rx="230" ry="12" fill="#000" opacity=".25"/>']
    # patitas
    for i, x in enumerate((280, 320, 380, 420)):
        d = -1 if x < 350 else 1
        s.append(stroke_path(f"M {x} 330 Q {x + d * 60} 360 {x + d * 80} 404", KIWA2, 12))
    # pinzas peludas: brazo + pelos + pinza (al comer, la derecha va por delante de la boca)
    adelante = []
    for lado, ((hx, hy), (tx, ty)) in enumerate(zip(((270, 285), (430, 285)), puntas)):
        dest = adelante if (pose == "come" and lado == 1) else s
        mx, my = (hx + tx) / 2, min(hy, ty) - 40
        if pose == "come" and lado == 1:   # el brazo hace un arco hacia afuera y vuelve a la boca
            mx, my = 560, 170
        d = f"M {hx} {hy} Q {mx} {my} {tx} {ty}"
        dest.append(stroke_path(d, KIWA, 30))
        for k in range(1, 12):   # pelos a lo largo del brazo
            t = k / 12
            px = (1 - t) ** 2 * hx + 2 * (1 - t) * t * mx + t ** 2 * tx
            py = (1 - t) ** 2 * hy + 2 * (1 - t) * t * my + t ** 2 * ty
            for sgn in (-1, 1):
                dest.append(ln(f"M {px:.0f} {py:.0f} l {sgn * 10:.0f} {22 + 6 * (k % 3)}", 5, KIWA_PELO))
                if bacterias and k % 2:
                    dest.append(f'<circle cx="{px + sgn * 12:.0f}" cy="{py + 26:.0f}" r="5" fill="#9BE07A" stroke="{INK}" stroke-width="2"/>')
        ang = math.atan2(ty - my, tx - mx)
        for da in (-.45, .45):   # dedos de la pinza
            ex, ey = tx + 34 * math.cos(ang + da), ty + 34 * math.sin(ang + da)
            dest.append(stroke_path(f"M {tx} {ty} L {ex:.0f} {ey:.0f}", KIWA, 14))
    # cuerpo y cola recogida
    s.append(f'<ellipse cx="350" cy="300" rx="120" ry="78" fill="{KIWA}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 270 300 Q 350 270 430 300", 5, KIWA2) + ln("M 290 330 Q 350 310 410 330", 5, KIWA2))
    for x in (300, 400):
        s.append(ln(f"M {x} 240 Q {x + (10 if x > 350 else -10)} 210 {x + (30 if x > 350 else -30)} 200", 4))
    # ojitos atrofiados (casi ciego) y boca
    s.append(f'<circle cx="326" cy="270" r="9" fill="#F4EED8" stroke="{INK}" stroke-width="3"/>'
             f'<circle cx="374" cy="270" r="9" fill="#F4EED8" stroke="{INK}" stroke-width="3"/>')
    if pose == "come":
        s.append(f'<ellipse cx="350" cy="306" rx="16" ry="12" fill="{P["boca"]}" stroke="{INK}" stroke-width="4"/>')
    else:
        s.append(ln("M 334 302 Q 350 314 366 302", 5))
    return "".join(s + adelante)


VAMP, VAMP2, VAMP_IN = "#7A1E3A", "#9A2E50", "#4A0E22"


def calamar_vampiro(modo="nada", brilla=False):
    """Calamar vampiro (Vampyroteuthis infernalis), 520x640. modo: nada (capa de brazos abierta) |
    pina (se da vuelta los brazos: queda una bola con 'púas' blandas). brilla: fotóforos azules."""
    s = []
    if modo == "pina":
        s.append(f'<circle cx="260" cy="330" r="190" fill="{VAMP_IN}" stroke="{INK}" stroke-width="{SW}"/>')
        for i in range(26):   # cirros (púas blandas) por toda la bola
            a = i * 2 * math.pi / 26
            x0, y0 = 260 + 186 * math.cos(a), 330 + 186 * math.sin(a)
            s.append(stroke_path(f"M {x0:.0f} {y0:.0f} L {260 + 232 * math.cos(a):.0f} {330 + 232 * math.sin(a):.0f}", "#C9506E", 10))
        for i in range(8):   # brazos plegados (líneas) con puntas negras
            a = i * 2 * math.pi / 8 + .2
            s.append(ln(f"M 260 330 Q {260 + 90 * math.cos(a + .4):.0f} {330 + 90 * math.sin(a + .4):.0f} "
                        f"{260 + 170 * math.cos(a):.0f} {330 + 170 * math.sin(a):.0f}", 6, "#2A0612"))
            s.append(f'<circle cx="{260 + 172 * math.cos(a):.0f}" cy="{330 + 172 * math.sin(a):.0f}" r="10" fill="{INK}"/>')
        for x in (210, 310):   # ojos espiando
            s.append(f'<circle cx="{x}" cy="300" r="26" fill="#6FC8FF" stroke="{INK}" stroke-width="5"/><circle cx="{x}" cy="304" r="11" fill="{INK}"/>')
        return "".join(s)
    # capa de brazos (membrana) con borde ondulado
    cape = "M 110 300 Q 60 470 40 560 Q 90 600 140 560 Q 190 610 230 566 Q 260 620 290 566 Q 330 610 380 560 Q 430 600 480 560 Q 460 470 410 300 Z"
    s.append(ln(cape, SW, INK, VAMP2))
    for x0, x1 in [(150, 70), (200, 170), (260, 260), (320, 350), (370, 450)]:
        s.append(ln(f"M {x0} 320 Q {(x0 + x1) / 2:.0f} 450 {x1} 566", 5, VAMP_IN))
        for k in range(3):   # cirros a lo largo de cada brazo
            yy = 380 + k * 55
            xx = x0 + (x1 - x0) * (yy - 320) / 246
            s.append(ln(f"M {xx:.0f} {yy} l 10 8", 4, "#C9506E"))
    for x in (40, 140, 230, 290, 380, 480):
        s.append(f'<circle cx="{x}" cy="{566 if x not in (40, 480) else 560}" r="9" fill="{INK}"/>')
    # manto (cuerpo) y aletas como orejas
    s.append(ln("M 150 120 Q 70 90 64 30 Q 140 50 186 100 Z", SW, INK, VAMP2))
    s.append(ln("M 370 120 Q 450 90 456 30 Q 380 50 334 100 Z", SW, INK, VAMP2))
    s.append(ln("M 120 320 Q 100 120 260 70 Q 420 120 400 320 Z", SW, INK, VAMP))
    s.append(ln("M 170 140 Q 190 100 230 90", 10, "#fff", extra='opacity=".25"'))
    for x in (200, 320):   # ojos enormes
        s.append(f'<circle cx="{x}" cy="250" r="44" fill="#6FC8FF" stroke="{INK}" stroke-width="6"/>'
                 f'<circle cx="{x}" cy="256" r="18" fill="{INK}"/><circle cx="{x - 12}" cy="240" r="9" fill="#fff"/>')
    if brilla:
        for x, y in [(110, 70), (410, 70), (40, 560), (480, 560), (140, 560), (380, 560), (230, 566), (290, 566)]:
            s.append(f'<circle cx="{x}" cy="{y}" r="22" fill="#9FE8FF" opacity=".45"/><circle cx="{x}" cy="{y}" r="9" fill="#E8FBFF"/>')
    return "".join(s)


def pez_vibora(cara_kind="malo"):
    """Pez víbora (depredador abisal) mirando a la izquierda: colmillos enormes y fotóforos (560x260)."""
    s = [ln("M 520 130 L 556 80 L 552 180 Z", SW, INK, "#2A2E40")]
    s.append(ln("M 40 130 Q 90 60 260 70 Q 440 80 520 130 Q 440 180 260 190 Q 90 200 40 130 Z", SW, INK, "#2E3448"))
    for x in range(120, 480, 40):
        s.append(f'<circle cx="{x}" cy="{176 - abs(x - 300) // 20}" r="7" fill="#7FD8FF"/>')
    # boca y colmillos
    s.append(ln("M 40 130 L 130 128 L 60 160 Z", 5, INK, "#5A1E2E"))
    for x, y, h in [(60, 118, 60), (88, 120, 70), (112, 124, 50)]:
        s.append(ln(f"M {x - 6} {y} L {x} {y + h} L {x + 6} {y} Z", 4, INK, "#F4EED8"))
    if cara_kind == "mareado":
        s.append(f'<circle cx="150" cy="100" r="22" fill="#fff" stroke="{INK}" stroke-width="5"/>'
                 + ln("M 150 100 m -12 0 a 12 12 0 1 1 12 12 a 8 8 0 1 1 -6 -8", 4))
        s.append(estrella4(200, 40, 16, P["amarillo"], 4) + estrella4(120, 30, 12, P["amarillo"], 4))
    else:
        s.append(f'<circle cx="150" cy="100" r="22" fill="#F5C518" stroke="{INK}" stroke-width="5"/><circle cx="146" cy="100" r="9" fill="{INK}"/>')
        s.append(ln("M 124 74 L 176 88", 8))
    return "".join(s)


RAPE, RAPE2 = "#3A2E2A", "#2A2220"


def rape_hembra(cara_kind="malo"):
    """Hembra de rape abisal mirando a la derecha (700x600): bocaza con dientes de aguja y señuelo
    luminoso (la punta brillante está en (640, 70)). cara_kind: malo | feliz."""
    s = [ln("M 120 330 Q 40 260 30 200 Q 90 230 120 280 Z", SW, INK, RAPE2)]            # aleta de la cola
    s.append(ln("M 120 330 Q 40 400 30 470 Q 90 430 130 380 Z", SW, INK, RAPE2))
    s.append(f'<ellipse cx="340" cy="340" rx="230" ry="200" fill="{RAPE}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<ellipse cx="320" cy="430" rx="150" ry="70" fill="#4A3C36"/>')
    # boca enorme con dientes
    s.append(ln("M 420 280 Q 600 270 610 360 Q 600 470 430 470 Q 520 380 420 280 Z", SW, INK, "#1A0E10"))
    for i in range(7):
        x = 470 + i * 20
        s.append(ln(f"M {x - 5} {286 + i * 2} L {x} {330 + (i % 2) * 14} L {x + 5} {286 + i * 2} Z", 3, INK, "#F4EED8"))
        s.append(ln(f"M {x - 5} {466 - i * 2} L {x} {426 - (i % 2) * 14} L {x + 5} {466 - i * 2} Z", 3, INK, "#F4EED8"))
    # señuelo: caña que sale de la cabeza con una bolita que brilla
    s.append(stroke_path("M 420 160 Q 520 20 640 70", "#4A3C36", 10))
    s.append(f'<circle cx="640" cy="70" r="22" fill="#E8FBFF" stroke="{INK}" stroke-width="5"/>')
    # ojo chiquito
    if cara_kind == "feliz":
        s.append(ln("M 380 230 Q 396 214 412 230", 7, "#E8E2D0"))
    else:
        s.append(f'<circle cx="396" cy="226" r="16" fill="#EDE8C0" stroke="{INK}" stroke-width="4"/><circle cx="400" cy="226" r="6" fill="{INK}"/>')
        s.append(ln("M 370 202 L 420 214", 8, "#E8E2D0"))
    s.append(ln("M 300 180 Q 330 160 370 160", 8, "#fff", extra='opacity=".15"'))
    return "".join(s)


def rape_macho(etapa=0):
    """Macho diminuto (180x100) mirando a la izquierda; con la boca muerde lo que está a su izquierda.
    etapa: 0 libre | 1 prendido | 2 fundido (pálido, con vasos) | 3 sin ojos | 4 bulto."""
    s = []
    if etapa == 4:
        s.append(ln("M 10 50 Q 40 10 110 26 Q 170 46 120 80 Q 50 96 10 50 Z", 5, INK, "#5A4A44"))
        s.append(ln("M 30 50 Q 70 40 110 52", 4, "#B5474F"))
        return "".join(s)
    cuerpo = "#5A4A44" if etapa < 2 else "#7A6460"
    s.append(ln("M 150 50 L 176 26 L 176 74 Z", 4, INK, cuerpo))
    s.append(ln("M 20 50 Q 50 16 110 22 Q 156 30 152 50 Q 156 70 110 78 Q 50 84 20 50 Z", 5, INK, cuerpo))
    s.append(ln("M 20 44 L 6 50 L 20 56 Z", 3, INK, "#1A0E10"))
    if etapa >= 2:
        s.append(ln("M 10 50 Q 60 40 120 56 M 30 60 Q 80 70 130 64", 4, "#B5474F"))
    if etapa <= 2:
        s.append(f'<circle cx="52" cy="40" r="14" fill="#fff" stroke="{INK}" stroke-width="3"/><circle cx="48" cy="41" r="6" fill="{INK}"/>')
    return "".join(s)


def batiscafo(cara_kw):
    """Batiscafo amarillo con Vos mirando por el ojo de buey (440x400). La lámpara apunta a la derecha
    desde (420, 250)."""
    s = [f'<rect x="60" y="300" width="60" height="40" rx="10" fill="#8E97A8" stroke="{INK}" stroke-width="{SW}"/>',
         ln("M 40 300 L 20 270 M 40 340 L 20 370", 10, "#5B5566")]
    s.append(f'<rect x="180" y="30" width="80" height="50" rx="14" fill="#E8B400" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<circle cx="220" cy="230" r="180" fill="{P["amarillo"]}" stroke="{INK}" stroke-width="{SW}"/>')
    for a in range(0, 360, 30):
        t = math.radians(a)
        s.append(f'<circle cx="{220 + 166 * math.cos(t):.0f}" cy="{230 + 166 * math.sin(t):.0f}" r="6" fill="#E8B400" stroke="{INK}" stroke-width="2"/>')
    s.append(f'<rect x="380" y="226" width="56" height="48" rx="10" fill="#8E97A8" stroke="{INK}" stroke-width="{SW}"/>'
             f'<rect x="420" y="232" width="16" height="36" rx="5" fill="#FFF4C2" stroke="{INK}" stroke-width="4"/>')
    # ojo de buey con la cara de Vos (con el casco de explorador)
    s.append(f'<clipPath id="ojb"><circle cx="220" cy="230" r="112"/></clipPath>')
    s.append(f'<circle cx="220" cy="230" r="112" fill="#1E3A5A"/>')
    s.append('<g clip-path="url(#ojb)"><g transform="translate(220 250) scale(0.56) translate(-260 -280)">'
             + head(**cara_kw) + casco_safari() + '</g></g>')
    s.append(f'<circle cx="220" cy="230" r="112" fill="#BDEBFF" opacity=".15"/>')
    s.append(f'<circle cx="220" cy="230" r="112" fill="none" stroke="#8E97A8" stroke-width="20"/>'
             f'<circle cx="220" cy="230" r="112" fill="none" stroke="{INK}" stroke-width="5"/>')
    s.append(ln("M 150 170 Q 170 140 210 132", 9, "#fff", extra='opacity=".6"'))
    return "".join(s)


def tinta():
    s = [ln("M 60 140 Q 40 60 130 50 Q 180 10 240 60 Q 300 70 280 140 Q 300 220 210 220 Q 150 250 100 210 Q 30 210 60 140 Z",
            5, "#000", "#06070C")]
    for x, y, r in [(40, 60, 18), (270, 40, 14), (300, 200, 16), (30, 220, 12)]:
        s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#06070C"/>')
    return "".join(s)


def destello():
    defs = ('<radialGradient id="ds" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#F0FDFF"/>'
            '<stop offset=".3" stop-color="#9FE8FF" stop-opacity=".8"/><stop offset="1" stop-color="#5CC8F0" stop-opacity="0"/></radialGradient>')
    return '<circle cx="40" cy="40" r="40" fill="url(#ds)"/>', defs


def nieve_marina():
    defs = ('<radialGradient id="nm" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#fff" stop-opacity=".9"/>'
            '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>')
    return '<circle cx="10" cy="10" r="10" fill="url(#nm)"/>', defs


def humo_toxico():
    return (f'<circle cx="40" cy="40" r="30" fill="#B8D84A" opacity=".55" stroke="#7A9A2A" stroke-width="4"/>'
            f'<circle cx="30" cy="30" r="8" fill="#fff" opacity=".5"/>')


def platillo():
    return (f'<ellipse cx="130" cy="60" rx="60" ry="44" fill="#BDEBFF" opacity=".8" stroke="{INK}" stroke-width="{SW}"/>'
            + ln("M 10 84 Q 130 40 250 84 Q 130 128 10 84 Z", SW, INK, "#9AA4B8")
            + "".join(f'<circle cx="{x}" cy="88" r="8" fill="{P["verde"]}" stroke="{INK}" stroke-width="3"/>' for x in (60, 100, 160, 200)))


def globo_comentario(puntos=3):
    s = [ln("M 30 20 L 330 20 Q 360 20 360 50 L 360 150 Q 360 180 330 180 L 120 180 L 70 226 L 80 180 L 30 180 "
            "Q 0 180 0 150 L 0 50 Q 0 20 30 20 Z", SW, INK, "#fff")]
    for i in range(3):
        op = 1 if i < puntos else .25
        s.append(f'<circle cx="{120 + i * 60}" cy="100" r="18" fill="#8A8F9E" opacity="{op}"/>')
    return "".join(s)


def gusano_tubo():
    """Gusanos de tubo de las fumarolas (Riftia): tubos blancos con penacho rojo (160x300, ancla abajo)."""
    s = []
    for x, h in [(40, 220), (80, 270), (120, 200)]:
        s.append(f'<rect x="{x - 14}" y="{300 - h}" width="28" height="{h}" rx="12" fill="#EDE8DA" stroke="{INK}" stroke-width="5"/>')
        s.append(f'<ellipse cx="{x}" cy="{300 - h - 10}" rx="22" ry="26" fill="#E0404A" stroke="{INK}" stroke-width="5"/>')
    return "".join(s)


def cortina_burbujas():
    rnd = random.Random(88)
    s = [f'<rect x="150" y="0" width="1200" height="2100" rx="200" fill="#123A5E"/>']
    for _ in range(90):
        x, y, r = rnd.uniform(0, 1500), rnd.uniform(-60, 2160), rnd.uniform(20, 110)
        s.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="{rnd.choice(["#1E5A8A", "#2E7AAE", "#174A72"])}" '
                 f'stroke="#9FD8F0" stroke-width="5" opacity=".95"/>'
                 f'<circle cx="{x - r * .35:.0f}" cy="{y - r * .35:.0f}" r="{r * .18:.0f}" fill="#fff" opacity=".5"/>')
    return "".join(s)


# ---------------------------------------------------------------- personas reales (short "3 memes")
# Caricaturas de figuras públicas: rasgos que las identifican (forma de cara, pelo, barba, anteojos,
# ropa) en el mismo estilo plano del kit. Busto de 520x620 con ancla abajo; cabeza centrada en x=260.
def ojo_c(cx, cy, kind="open", iris="#5B3A29", w=24, h=11, look=(0, 0), piel=None, uid="o"):
    """Ojo de caricatura realista (almendra con iris), más chico que los de Vos."""
    lx, ly = look
    if kind == "closed":
        return ln(f"M {cx - w} {cy} Q {cx} {cy + h * .9} {cx + w} {cy}", 6)
    if kind == "happy":
        return ln(f"M {cx - w} {cy + h * .4} Q {cx} {cy - h * 1.3} {cx + w} {cy + h * .4}", 6)
    if kind == "wide":
        w, h = w * 1.05, h * 1.6
    alm = f"M {cx - w} {cy} Q {cx} {cy - h * 2} {cx + w} {cy} Q {cx} {cy + h * 1.5} {cx - w} {cy} Z"
    r = h * (.78 if kind == "wide" else .95)
    px, py = cx + lx * w * .4, cy - h * .1 + ly * h * .3
    s = (f'<clipPath id="{uid}"><path d="{alm}"/></clipPath><path d="{alm}" fill="#fff"/>'
         f'<g clip-path="url(#{uid})"><circle cx="{px}" cy="{py}" r="{r}" fill="{iris}"/>'
         f'<circle cx="{px}" cy="{py}" r="{r * .5}" fill="{INK}"/>'
         f'<circle cx="{px - r * .35}" cy="{py - r * .4}" r="{r * .28}" fill="#fff"/>')
    if kind == "tired":   # párpado caído (cansado / triste)
        s += f'<rect x="{cx - w - 2}" y="{cy - h * 2}" width="{2 * w + 4}" height="{h * 1.6}" fill="{piel}"/>'
    s += "</g>" + f'<path d="{alm}" fill="none" stroke="{INK}" stroke-width="4.5"/>'
    top = cy - h * (.6 if kind == "tired" else 1.0)
    s += ln(f"M {cx - w - 2} {cy + 1} Q {cx} {top - h * .9} {cx + w + 2} {cy + 1}", 6.5)
    return s


def boca_c(kind, cx, cy, w=30, labio="#B5544F", dientes=True, uid="b"):
    if kind == "sonrisa":
        return ln(f"M {cx - w} {cy - 4} Q {cx} {cy + w * .55} {cx + w} {cy - 4}", 6.5)
    if kind == "sonrisa_ladeada":
        return ln(f"M {cx - w} {cy + 2} Q {cx + w * .1} {cy + w * .45} {cx + w * 1.05} {cy - w * .3}", 6.5)
    if kind == "risa":
        d = f"M {cx - w} {cy - 6} Q {cx} {cy + w * 1.1} {cx + w} {cy - 6} Z"
        s = (f'<clipPath id="{uid}"><path d="{d}"/></clipPath><path d="{d}" fill="{P["boca"]}"/>'
             f'<g clip-path="url(#{uid})">')
        if dientes:
            s += f'<rect x="{cx - w}" y="{cy - 8}" width="{2 * w}" height="{w * .32}" fill="#fff"/>'
        s += f'<ellipse cx="{cx}" cy="{cy + w * .75}" rx="{w * .55}" ry="{w * .3}" fill="{P["lengua"]}"/></g>'
        return s + ln(d, 6)
    if kind == "serio":
        return ln(f"M {cx - w * .8} {cy} Q {cx} {cy + 3} {cx + w * .8} {cy}", 6.5)
    if kind == "triste":
        return ln(f"M {cx - w * .8} {cy + 8} Q {cx} {cy - 10} {cx + w * .8} {cy + 8}", 6.5)
    if kind == "o":
        return f'<ellipse cx="{cx}" cy="{cy + 6}" rx="{w * .45}" ry="{w * .6}" fill="{P["boca"]}" stroke="{INK}" stroke-width="6"/>'
    raise ValueError(kind)


CEJAS_C = {   # desplazamiento (dy interno, dy externo) de cada ceja según la emoción
    "neutral": (0, 0), "arriba": (-16, -12), "triste": (-12, 6), "enojo": (8, -6), "duda": (0, 0),
}


def cejas_c(xl, xr, y, w, kind, color, grosor):
    di, de = CEJAS_C[kind]
    izq = f"M {xl - w} {y + de} Q {xl} {y - 10 + (di + de) / 2} {xl + w} {y + di}"
    der = f"M {xr - w} {y + di} Q {xr} {y - 10 + (di + de) / 2} {xr + w} {y + de}"
    if kind == "duda":   # una sola ceja levantada
        der = f"M {xr - w} {y - 10} Q {xr} {y - 30} {xr + w} {y - 18}"
    return ln(izq, grosor, color) + ln(der, grosor, color)


EXPR = {   # ojos, cejas, boca
    "contento": ("open", "neutral", "sonrisa"),
    "risa": ("happy", "neutral", "risa"),
    "serio": ("open", "neutral", "serio"),
    "sorpresa": ("wide", "arriba", "o"),
    "triste": ("tired", "triste", "triste"),
    "preocupado": ("open", "triste", "serio"),
    "picaro": ("open", "duda", "sonrisa_ladeada"),
}


def torso_c(ropa, piel, con_cuello=True):
    """Hombros y ropa del busto (debajo de la cabeza). con_cuello=False: sin el cuello de piel."""
    hombros = "M 24 620 C 34 520 104 484 188 470 L 332 470 C 416 484 486 520 496 620 Z"
    cuello = (f'<path d="M 214 404 L 214 482 Q 260 506 306 482 L 306 404 Z" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>'
              if con_cuello else "")
    if ropa == "traje":          # traje azul, camisa blanca, corbata roja (y pin de bandera)
        return (cuello + ln(hombros, SW, INK, "#26324F")
                + ln("M 200 468 L 260 586 L 320 468 Z", 5, INK, "#FFFFFF")
                + ln("M 246 492 L 274 492 L 270 512 L 250 512 Z", 5, INK, "#C8312F")
                + ln("M 250 512 L 240 600 L 260 620 L 280 600 L 270 512 Z", 5, INK, "#C8312F")
                + ln("M 200 468 L 236 520 L 222 532 L 260 600", 5, INK) + ln("M 320 468 L 284 520 L 298 532 L 260 600", 5, INK)
                + ln("M 214 470 L 238 506 L 256 488 Z", 4, INK, "#FFFFFF") + ln("M 306 470 L 282 506 L 264 488 Z", 4, INK, "#FFFFFF")
                + f'<rect x="354" y="530" width="30" height="20" rx="3" fill="#fff" stroke="{INK}" stroke-width="3"/>'
                + '<rect x="354" y="530" width="13" height="10" fill="#3A5BA8"/>'
                + "".join(f'<rect x="367" y="{532 + i * 6}" width="17" height="3" fill="#D8343A"/>' for i in range(3)))
    if ropa == "blanco":         # traje blanco de fiesta con cadena de oro
        cadena = "".join(f'<circle cx="{260 + 64 * math.sin(a)}" cy="{486 + 62 * (1 - math.cos(a))}" r="7" fill="#F2C230" stroke="{INK}" stroke-width="3"/>'
                         for a in [i * .21 - 1.26 for i in range(13)])
        return (cuello + ln(hombros, SW, INK, "#F4F1EA")
                + ln("M 206 468 L 260 560 L 314 468 Z", 5, INK, "#FFFFFF")
                + ln("M 206 468 L 240 530 L 226 540 L 252 600", 5, INK) + ln("M 314 468 L 280 530 L 294 540 L 268 600", 5, INK)
                + cadena + f'<circle cx="260" cy="572" r="16" fill="#F2C230" stroke="{INK}" stroke-width="4"/>'
                + ln("M 252 566 L 268 578 M 268 566 L 252 578", 3, "#C99A12"))
    if ropa == "sueter":         # suéter oscuro con cuello de camisa celeste
        return (cuello + ln(hombros, SW, INK, "#2E3445")
                + ln("M 206 470 Q 260 530 314 470", 6, INK, "#3A4256")
                + ln("M 212 470 L 236 500 L 256 486 Z", 4, INK, "#D7E4F2") + ln("M 308 470 L 284 500 L 264 486 Z", 4, INK, "#D7E4F2")
                + ln("M 120 560 Q 160 590 170 620", 4, "#252A38") + ln("M 400 560 Q 360 590 350 620", 4, "#252A38"))
    if ropa in ("preso_naranja", "preso_caqui"):
        col, col2 = ("#F08A2C", "#D9701A") if ropa == "preso_naranja" else ("#C9B48A", "#AE9970")
        return (cuello + ln(hombros, SW, INK, col)
                + ln("M 206 470 L 260 540 L 314 470", 6, INK) + ln("M 206 470 L 232 512 L 252 494", 5, INK, col2)
                + ln("M 314 470 L 288 512 L 268 494", 5, INK, col2)
                + f'<rect x="350" y="540" width="70" height="24" rx="4" fill="#fff" stroke="{INK}" stroke-width="3"/>'
                + "".join(ln(f"M {356 + i * 9} 546 L {356 + i * 9} 558", 3) for i in range(7)))
    raise ValueError(ropa)


FOTOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recursos", "fotos")


def foto(nombre, x, y, ancho):
    """Imagen de recursos/fotos (generada con foto_recurso.py) dentro del SVG. Devuelve (svg, alto)."""
    import base64
    from PIL import Image
    ruta = os.path.join(FOTOS, nombre + ".png")
    w, h = Image.open(ruta).size
    alto = ancho * h / w
    b64 = base64.b64encode(open(ruta, "rb").read()).decode()
    return (f'<image x="{x}" y="{y}" width="{ancho}" height="{alto:.1f}" preserveAspectRatio="none" '
            f'href="data:image/png;base64,{b64}"/>'), alto


def color_piel(nombre, zona=(.35, .55, .65, .75)):
    """Color medio de la piel de una cara recortada (para dibujar el cuello del mismo tono)."""
    from PIL import Image
    im = Image.open(os.path.join(FOTOS, nombre + ".png")).convert("RGB")
    w, h = im.size
    r, g, b = [int(c) for c in im.crop((int(w * zona[0]), int(h * zona[2]), int(w * zona[1]), int(h * zona[3])))
               .resize((1, 1), Image.BOX).getpixel((0, 0))]
    return f"#{r:02X}{g:02X}{b:02X}"


def pelo_epstein(x0, ancho, costura):
    """Completa la parte de arriba de la cabeza (la foto está cortada en la frente): pelo canoso con
    volumen, peinado hacia atrás. x0/ancho = la foto en el lienzo; costura = y donde empieza la foto real."""
    x1, cx = x0 + ancho, x0 + ancho / 2
    y = costura
    forma = (f"M {x0 + 4} {y + 70} C {x0 - 14} {y - 10} {x0 + 20} {y - 96} {cx - 40} {y - 118} "
             f"C {cx + 30} {y - 134} {x1 + 6} {y - 104} {x1 - 2} {y - 20} L {x1 - 8} {y + 70} "
             f"C {x1 - 20} {y + 30} {x1 - 50} {y + 12} {cx + 50} {y + 10} "
             f"C {cx + 10} {y + 2} {cx - 40} {y + 4} {cx - 80} {y + 14} C {x0 + 40} {y + 26} {x0 + 18} {y + 44} {x0 + 4} {y + 70} Z")
    s = [ln(forma, 6, INK, "#D6D3CE")]
    for i, (a, b, c) in enumerate([(-80, -90, .2), (-60, -60, .35), (-40, -30, .5), (-30, 0, .62), (10, -100, .3),
                                   (20, -70, .45), (40, -40, .6), (60, -10, .72), (70, 20, .85)]):
        xa = x0 + ancho * c - 60
        s.append(ln(f"M {xa:.0f} {y + b + 70:.0f} C {xa + 30:.0f} {y + b + 10:.0f} {xa + 90:.0f} {y + b - 20:.0f} "
                    f"{xa + 150:.0f} {y + b - 10:.0f}", 4, "#AEA9A2" if i % 2 else "#F1EFEC"))
    s.append(f'<clipPath id="pe"><path d="{forma}"/></clipPath>')
    return "".join(s)


PERSONAS = {   # cara (recursos/fotos), ancho en el lienzo, dónde queda el mentón (fracción del alto de la foto)
    "kirk": ("kirk_cara", 300, .985), "kirk_chica": ("kirk_cara_chica", 300, .985),
    "kirk_habla": ("kirk_habla_cara", 290, .985), "diddy": ("diddy_cara", 300, .9), "epstein": ("epstein_cara", 300, .985),
    # caras borrosas para el gancho (intriga: todavía no se sabe quiénes son)
    "kirk_borroso": ("kirk_cara_borrosa", 300, .985), "diddy_borroso": ("diddy_cara_borrosa", 300, .9),
    "epstein_borroso": ("epstein_cara_borrosa", 300, .985),
}
PERSONA_W, PERSONA_H, MENTON = 520, 660, 494   # lienzo del busto y altura del mentón (justo arriba del cuello)


def persona(quien, ropa):
    """Busto (520x660, ancla abajo): cuello dibujado, la cara de la foto y la ropa dibujada encima del
    borde de abajo de la foto (así el corte del cuello queda tapado por el cuello de la ropa)."""
    cara, ancho, menton = PERSONAS[quien]
    piel = color_piel(cara)
    x0 = 260 - ancho / 2
    _, alto = foto(cara, 0, 0, ancho)
    top = MENTON - alto * menton
    img, _ = foto(cara, x0, top, ancho)
    cuello = (f'<path d="M 222 {MENTON - 70} L 222 540 L 298 540 L 298 {MENTON - 70} Z" fill="{piel}"/>'
              + ln(f"M 222 {MENTON - 40} L 222 530", SW) + ln(f"M 298 {MENTON - 40} L 298 530", SW)
              + ln(f"M 236 {MENTON + 6} Q 260 {MENTON + 20} 284 {MENTON + 6}", 4, INK, extra='opacity=".25"'))
    return cuello + img + f'<g transform="translate(0 40)">{torso_c(ropa, piel, False)}</g>'


# ---------------------------------------------------------------- memes: Vos con el celular, estudiantes y objetos
def accesorio_celular():
    """Vos sostiene el celular con las dos manos frente al pecho (la pantalla le ilumina la cara)."""
    piel = P["piel"]
    s = [stroke_path("M 182 505 Q 160 590 226 600", piel, 28), stroke_path("M 338 505 Q 360 590 294 600", piel, 28)]
    s.append(f'<circle cx="186" cy="500" r="30" fill="{P["remera"]}" stroke="{INK}" stroke-width="{SW}"/>'
             f'<circle cx="334" cy="500" r="30" fill="{P["remera"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<rect x="212" y="500" width="96" height="160" rx="16" fill="#1E1E24" stroke="{INK}" stroke-width="6"/>'
             f'<rect x="222" y="512" width="76" height="136" rx="8" fill="#9ADCFF"/>'
             f'<rect x="230" y="524" width="60" height="40" rx="5" fill="#fff" opacity=".8"/>'
             f'<rect x="230" y="572" width="60" height="8" rx="4" fill="#fff" opacity=".6"/>'
             f'<rect x="230" y="588" width="44" height="8" rx="4" fill="#fff" opacity=".6"/>')
    s.append(f'<circle cx="226" cy="604" r="25" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>'
             f'<circle cx="294" cy="604" r="25" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>')
    return "".join(s)


def vos_celu(eyes="open", brows="neutral", mouth_kind="smile", look=(0, .6)):
    """Vos mirando el celular (sin brazos de abajo: los dos sostienen el teléfono)."""
    s = [f'<ellipse cx="260" cy="806" rx="125" ry="13" fill="#000" opacity=".12"/>']
    for x in (205, 269):
        s.append(f'<rect x="{x}" y="640" width="46" height="150" rx="20" fill="{P["pantalon"]}" stroke="{INK}" stroke-width="{SW}"/>')
    for x in (220, 300):
        s.append(f'<ellipse cx="{x}" cy="794" rx="40" ry="21" fill="{INK}"/>')
    s.append(f'<rect x="158" y="452" width="204" height="228" rx="72" fill="{P["remera"]}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 224 462 Q 260 494 296 462", 6))
    s.append(head(eyes, brows, mouth_kind, look))
    s.append(accesorio_celular())
    return "".join(s)


VOS_CELU = {   # cara de Vos según la reacción
    "contento": dict(), "risa": dict(eyes="happy", brows="happy", mouth_kind="open_smile"),
    "sorpresa": dict(eyes="wide", brows="up", mouth_kind="o"), "miedo": dict(eyes="wide", brows="sad", mouth_kind="nervio"),
    "triste": dict(eyes="open", brows="sad", mouth_kind="flat", look=(0, .8)), "serio": dict(mouth_kind="flat"),
    "pensando": dict(brows="asco", mouth_kind="flat", look=(.6, -.6)),
}


def estudiante(remera, piel, pelo, mano=False):
    """Estudiante genérico (mismo cuerpo que Vos, otros colores); mano=True levanta la mano."""
    s = [f'<ellipse cx="260" cy="806" rx="125" ry="13" fill="#000" opacity=".12"/>']
    for x in (205, 269):
        s.append(f'<rect x="{x}" y="640" width="46" height="150" rx="20" fill="#3A3F55" stroke="{INK}" stroke-width="{SW}"/>')
    for x in (220, 300):
        s.append(f'<ellipse cx="{x}" cy="794" rx="40" ry="21" fill="{INK}"/>')
    s.append(f'<rect x="158" y="452" width="204" height="228" rx="72" fill="{remera}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 196 470 L 196 600 M 324 470 L 324 600", 9, "#2B2730"))   # tiras de la mochila
    brazo = lambda d, h: (stroke_path(d, piel, 28) + f'<circle cx="{h[0]}" cy="{h[1]}" r="25" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(brazo("M 182 505 Q 150 575 148 652", (148, 655)))
    s.append(brazo("M 338 505 Q 420 440 430 330", (430, 326)) if mano else brazo("M 338 505 Q 370 575 372 652", (372, 655)))
    s.append(f'<circle cx="186" cy="500" r="30" fill="{remera}" stroke="{INK}" stroke-width="{SW}"/>'
             f'<circle cx="334" cy="500" r="30" fill="{remera}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(head("open", "neutral", "smile", (0, 0), "", HAIR, pelo, piel))
    return "".join(s)


def mesa_debate(banner=True):
    """Mesa con mantel azul y un cartel blanco al frente (el texto se pone con el motor). 760x330, ancla abajo.
    banner=False: el mismo mantel sin el cartel."""
    s = [ln("M 20 120 L 740 120 L 740 150 L 20 150 Z", SW, INK, "#2F4C8F")]
    s.append(ln("M 34 150 L 726 150 L 712 320 L 48 320 Z", SW, INK, "#3A5DAE"))
    if banner:
        s.append(ln("M 120 172 L 640 172 L 632 292 L 128 292 Z", 6, INK, "#FFFFFF"))
    s.append(ln("M 34 150 Q 120 170 200 150 Q 300 172 380 150 Q 460 172 560 150 Q 640 170 726 150", 4, "#26407A"))
    s.append(f'<rect x="560" y="70" width="70" height="52" rx="8" fill="#E9E4D8" stroke="{INK}" stroke-width="5"/>'
             + ln("M 630 84 Q 656 92 630 108", 6))   # taza
    s.append(f'<rect x="120" y="96" width="120" height="26" rx="4" fill="#F7F2E6" stroke="{INK}" stroke-width="4"/>')
    return "".join(s)


def carpa():
    """Gazebo plegable azul detrás de la mesa (900x620, ancla abajo)."""
    s = [ln("M 60 180 L 450 40 L 840 180 Z", SW, INK, "#2F4C8F"),
         ln("M 60 180 L 840 180 L 840 230 Q 795 260 750 230 Q 705 260 660 230 Q 615 260 570 230 Q 525 260 480 230 "
            "Q 435 260 390 230 Q 345 260 300 230 Q 255 260 210 230 Q 165 260 120 230 Q 90 250 60 230 Z", SW, INK, "#3A5DAE")]
    for x in (80, 820):
        s.append(f'<rect x="{x - 9}" y="230" width="18" height="390" fill="#C9CED8" stroke="{INK}" stroke-width="5"/>')
    s.append(ln("M 450 40 L 450 180", 4, "#26407A") + ln("M 250 112 L 300 180 M 650 112 L 600 180", 4, "#26407A"))
    return "".join(s)


def microfono():
    """Micrófono de mano (120x300, ancla abajo)."""
    s = [f'<rect x="44" y="110" width="32" height="180" rx="14" fill="#2B2B33" stroke="{INK}" stroke-width="6"/>',
         f'<rect x="38" y="100" width="44" height="30" rx="8" fill="#55555F" stroke="{INK}" stroke-width="5"/>',
         f'<circle cx="60" cy="62" r="46" fill="#9AA0AE" stroke="{INK}" stroke-width="6"/>']
    for k in range(-2, 3):
        s.append(ln(f"M {60 + k * 16} 22 L {60 + k * 16} 102", 3, "#6E7484"))
    s.append(ln("M 20 62 L 100 62 M 26 40 L 94 40 M 26 84 L 94 84", 3, "#6E7484"))
    return "".join(s)


def celular_marco(w=520, h=1000):
    """Marco de celular con la pantalla hueca (lo que va 'adentro' se pone por debajo)."""
    r = 70
    hueco = f"M {28} {64} L {w - 28} 64 L {w - 28} {h - 64} L 28 {h - 64} Z"
    marco = (f"M {r} 0 L {w - r} 0 Q {w} 0 {w} {r} L {w} {h - r} Q {w} {h} {w - r} {h} L {r} {h} Q 0 {h} 0 {h - r} "
             f"L 0 {r} Q 0 0 {r} 0 Z")
    return (f'<path d="{marco} {hueco}" fill="#17171D" fill-rule="evenodd" stroke="{INK}" stroke-width="{SW}"/>'
            f'<rect x="{w / 2 - 60}" y="22" width="120" height="22" rx="11" fill="#2E2E38"/>'
            f'<rect x="{w / 2 - 70}" y="{h - 42}" width="140" height="10" rx="5" fill="#55555F"/>'
            + ln(f"M 28 64 L {w - 28} 64 L {w - 28} {h - 64} L 28 {h - 64} Z", 4, "#000"))


def pantalla_feed():
    """Pantalla de una red social (370x720) para poner detrás del marco del celular: barra con avatar
    arriba, fondo claro para la foto y botones de corazón, comentario y compartir abajo."""
    s = [f'<rect width="370" height="720" fill="#F3F1FA"/>',
         f'<rect width="370" height="96" fill="#FFFFFF"/>' + ln("M 0 96 L 370 96", 3, "#DDD8EA"),
         f'<circle cx="52" cy="58" r="24" fill="#C9B8FF" stroke="{INK}" stroke-width="3"/>',
         f'<rect x="90" y="44" width="140" height="14" rx="7" fill="#8A8499"/><rect x="90" y="66" width="90" height="10" rx="5" fill="#C4BFD1"/>',
         f'<rect y="600" width="370" height="120" fill="#FFFFFF"/>' + ln("M 0 600 L 370 600", 3, "#DDD8EA"),
         f'<g transform="translate(30 618) scale(.34)">{corazon()}</g>',
         ln("M 120 626 L 170 626 L 170 656 L 140 656 L 128 668 L 128 656 L 120 656 Z", 5, INK, "#FFFFFF"),
         ln("M 210 660 L 250 630 L 250 646 Q 280 646 290 668 Q 270 656 250 658 L 250 676 Z", 5, INK, "#FFFFFF"),
         f'<rect x="30" y="684" width="200" height="12" rx="6" fill="#C4BFD1"/>']
    return "".join(s)


def video_card(nombre_foto):
    """Miniatura de video (480x330): foto + botón de play + barra de progreso."""
    img, alto = foto(nombre_foto, 20, 20, 440)
    s = [f'<rect x="8" y="8" width="464" height="314" rx="22" fill="#fff" stroke="{INK}" stroke-width="{SW}"/>',
         f'<clipPath id="vc"><rect x="20" y="20" width="440" height="250" rx="14"/></clipPath>',
         f'<g clip-path="url(#vc)">{img}</g>',
         f'<circle cx="240" cy="145" r="44" fill="#000" opacity=".55"/>', ln("M 224 120 L 266 145 L 224 170 Z", 0, "none", "#fff"),
         f'<rect x="20" y="282" width="440" height="12" rx="6" fill="#DDD"/><rect x="20" y="282" width="300" height="12" rx="6" fill="#FF3B3B"/>',
         f'<circle cx="320" cy="288" r="12" fill="#FF3B3B" stroke="#fff" stroke-width="3"/>']
    return "".join(s)


def emoji_risa():
    """Carita llorando de risa (200x200)."""
    return (f'<circle cx="100" cy="100" r="86" fill="#FFCC33" stroke="{INK}" stroke-width="{SW}"/>'
            + ln("M 52 82 Q 70 60 88 82", 8) + ln("M 112 82 Q 130 60 148 82", 8)
            + '<path d="M 50 112 Q 100 186 150 112 Z" fill="#7A2735"/>'
            + '<path d="M 58 116 L 142 116 L 138 128 L 62 128 Z" fill="#fff"/>' + ln("M 50 112 Q 100 186 150 112 Z", 6)
            + ln("M 36 92 Q 16 118 30 140 Q 46 130 40 100 Z", 4, INK, "#6FC8FF")
            + ln("M 164 92 Q 184 118 170 140 Q 154 130 160 100 Z", 4, INK, "#6FC8FF"))


def calavera_emoji():
    """💀 (200x200): la reacción de 'me morí de risa'."""
    return (ln("M 30 98 Q 30 20 100 20 Q 170 20 170 98 Q 170 136 146 146 L 146 178 L 54 178 L 54 146 Q 30 136 30 98 Z", SW, INK, "#F1EFEA")
            + f'<ellipse cx="72" cy="98" rx="22" ry="25" fill="{INK}"/><ellipse cx="128" cy="98" rx="22" ry="25" fill="{INK}"/>'
            + ln("M 100 120 L 90 142 L 110 142 Z", 4, INK, INK) + "".join(ln(f"M {x} 160 L {x} 178", 5) for x in (78, 100, 122)))


def vela():
    """Vela blanca (90x240, ancla abajo); la llama va aparte para que titile."""
    return (f'<ellipse cx="45" cy="232" rx="40" ry="8" fill="#000" opacity=".2"/>'
            + ln("M 18 70 L 18 228 Q 45 238 72 228 L 72 70 Z", 6, INK, "#F6F1E4")
            + ln("M 18 70 Q 45 82 72 70 Q 45 58 18 70 Z", 5, INK, "#FFFDF6")
            + ln("M 62 74 Q 66 110 60 130", 6, "#FFFDF6") + ln("M 45 68 L 45 50", 4))


def llama_vela():
    """Llamita de vela (60x90, ancla abajo)."""
    return (ln("M 30 86 C 6 70 14 40 30 4 C 46 40 54 70 30 86 Z", 4, "#E07A10", "#FFB627")
            + ln("M 30 80 C 20 70 22 52 30 36 C 38 52 40 70 30 80 Z", 0, "none", "#FFF2B0"))


def flores():
    """Ramo de flores apoyado (300x240, ancla abajo)."""
    s = [ln("M 90 236 L 150 120 M 150 236 L 150 110 M 210 236 L 150 120", 6, "#3F8A3A")]
    for (x, y, c) in [(110, 96, "#FFFFFF"), (150, 70, "#FF8FA8"), (192, 96, "#FFFFFF"), (130, 130, "#FFD23F"), (176, 128, "#FF8FA8")]:
        for a in range(0, 360, 60):
            s.append(f'<circle cx="{x + 16 * math.cos(math.radians(a)):.0f}" cy="{y + 16 * math.sin(math.radians(a)):.0f}" r="14" '
                     f'fill="{c}" stroke="{INK}" stroke-width="3.5"/>')
        s.append(f'<circle cx="{x}" cy="{y}" r="9" fill="#F2B233" stroke="{INK}" stroke-width="3"/>')
    s.append(ln("M 60 190 L 240 190 L 210 236 L 90 236 Z", 5, INK, "#E9E1F2"))
    return "".join(s)


def retrato(nombre_foto, luto=True):
    """Portarretrato (360x440) con la foto; luto=True agrega la cinta negra en la esquina."""
    img, alto = foto(nombre_foto, 40, 40, 280)
    s = [f'<rect x="8" y="8" width="344" height="424" rx="10" fill="#3A2A1E" stroke="{INK}" stroke-width="{SW}"/>',
         f'<rect x="28" y="28" width="304" height="384" rx="4" fill="#C9A15A"/>',
         f'<clipPath id="rt"><rect x="40" y="40" width="280" height="360"/></clipPath><g clip-path="url(#rt)">{img}</g>',
         ln("M 40 40 L 320 40 L 320 400 L 40 400 Z", 4)]
    if luto:
        s.append(ln("M 250 8 L 352 110 L 352 60 L 300 8 Z", 4, INK, "#141414"))
    return "".join(s)


def disco_oro():
    """Disco de oro enmarcado (240x300)."""
    return (f'<rect x="8" y="8" width="224" height="284" rx="10" fill="#1B1B22" stroke="{INK}" stroke-width="{SW}"/>'
            f'<circle cx="120" cy="124" r="88" fill="#F2C230" stroke="{INK}" stroke-width="5"/>'
            + "".join(f'<circle cx="120" cy="124" r="{r}" fill="none" stroke="#C99A12" stroke-width="2"/>' for r in (74, 62, 50))
            + f'<circle cx="120" cy="124" r="24" fill="#FFF2B0" stroke="{INK}" stroke-width="4"/>'
            + f'<rect x="56" y="234" width="128" height="30" rx="4" fill="#F2C230"/>'
            + ln("M 70 80 Q 90 60 116 56", 6, "#fff", extra='opacity=".6"'))


def bola_disco():
    """Bola de espejos (220x260, ancla arriba con su cable)."""
    s = [ln("M 110 0 L 110 50", 5), f'<circle cx="110" cy="150" r="100" fill="#B8C4D6" stroke="{INK}" stroke-width="{SW}"/>']
    s.append('<clipPath id="bd"><circle cx="110" cy="150" r="96"/></clipPath><g clip-path="url(#bd)">')
    rnd = random.Random(8)
    for y in range(50, 260, 22):
        for x in range(0, 230, 22):
            c = rnd.choice(["#E8EEF6", "#9FAFC6", "#C9D4E4", "#FFFFFF", "#7F8FA8"])
            s.append(f'<rect x="{x + (11 if (y // 22) % 2 else 0)}" y="{y}" width="20" height="20" fill="{c}"/>')
    s.append("</g>" + f'<circle cx="110" cy="150" r="100" fill="none" stroke="{INK}" stroke-width="{SW}"/>')
    return "".join(s)


def siluetas_fiesta(k=0):
    """Gente bailando a contraluz (900x520, ancla abajo); k=0/1 cambia la pose (loop de baile)."""
    s = []
    poses = [(110, 1), (290, -1), (470, 1), (650, -1), (820, 1)]
    for i, (x, d) in enumerate(poses):
        d = d if k == 0 else -d
        c = "#3A2459" if i % 2 else "#2A1A45"
        s.append(f'<circle cx="{x}" cy="{230 + (i % 2) * 30}" r="46" fill="{c}"/>')
        s.append(f'<path d="M {x - 60} 520 Q {x - 66} {330 + (i % 2) * 30} {x} {300 + (i % 2) * 30} Q {x + 66} {330 + (i % 2) * 30} {x + 60} 520 Z" fill="{c}"/>')
        s.append(stroke_path(f"M {x - 40} {340 + (i % 2) * 30} Q {x - 90 * d} {250} {x - 70 * d} {150 + (i % 2) * 20}", c, 26, c))
        s.append(stroke_path(f"M {x + 40} {340 + (i % 2) * 30} Q {x + 80} {390} {x + 60 * d} {300}", c, 26, c))
    return "".join(s)


def aceite_bebe():
    """Botella de aceite para bebés (genérica, sin marca): 120x260, ancla abajo."""
    return (ln("M 30 70 L 30 250 Q 60 262 90 250 L 90 70 Q 60 56 30 70 Z", 6, INK, "#F7B8C4")
            + ln("M 30 70 Q 60 56 90 70 L 90 120 Q 60 108 30 120 Z", 0, "none", "#FAD1D9")
            + f'<rect x="40" y="26" width="40" height="40" rx="8" fill="#FFFFFF" stroke="{INK}" stroke-width="5"/>'
            + f'<rect x="48" y="8" width="24" height="22" rx="6" fill="#FFFFFF" stroke="{INK}" stroke-width="4"/>'
            + f'<rect x="36" y="140" width="48" height="70" rx="6" fill="#FFFFFF" stroke="{INK}" stroke-width="4"/>'
            + ln("M 46 160 L 74 160 M 46 176 L 74 176 M 46 192 L 66 192", 4, "#7FB5E8")
            + ln("M 78 86 Q 82 160 78 236", 5, "#fff", extra='opacity=".6"'))


def caja_evidencia():
    """Caja de cartón de evidencia (300x220, ancla abajo)."""
    return (ln("M 20 60 L 280 60 L 280 216 L 20 216 Z", SW, INK, "#C99A5B")
            + ln("M 10 40 L 290 40 L 290 76 L 10 76 Z", SW, INK, "#DDB074")
            + f'<rect x="90" y="110" width="120" height="50" rx="6" fill="#FFFFFF" stroke="{INK}" stroke-width="4"/>'
            + ln("M 104 128 L 196 128 M 104 144 L 170 144", 4, "#B33A3A"))


def luz_sirena(color):
    """Resplandor de sirena para toda la pantalla (se alterna rojo/azul con un loop)."""
    lado = 0 if color == "rojo" else W
    c = "#FF2A2A" if color == "rojo" else "#2A6BFF"
    return (f'<rect width="{W}" height="{H}" fill="url(#sir)"/>',
            f'<radialGradient id="sir" cx="{lado / W}" cy="0.35" r="0.85"><stop offset="0" stop-color="{c}" stop-opacity=".8"/>'
            f'<stop offset=".6" stop-color="{c}" stop-opacity=".25"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>')


def esposas():
    """Esposas (300x170)."""
    s = []
    for cx in (80, 220):
        s.append(f'<circle cx="{cx}" cy="96" r="58" fill="none" stroke="{INK}" stroke-width="30"/>'
                 f'<circle cx="{cx}" cy="96" r="58" fill="none" stroke="#C9CED8" stroke-width="18"/>'
                 + ln(f"M {cx - 30} 50 Q {cx - 10} 40 {cx + 20} 44", 5, "#fff", extra='opacity=".7"'))
    s.append(ln("M 134 70 Q 150 54 166 70", 12, INK) + ln("M 134 70 Q 150 54 166 70", 6, "#C9CED8"))
    return "".join(s)


def rejas():
    """Rejas de celda que cubren toda la pantalla (1080x1920, transparentes entre barrotes)."""
    s = []
    for y in (120, 1640):
        s.append(f'<rect x="-10" y="{y}" width="{W + 20}" height="48" fill="#4A4F5C" stroke="{INK}" stroke-width="{SW}"/>')
    for x in range(60, W, 140):
        s.append(f'<rect x="{x - 18}" y="-10" width="36" height="{H + 20}" fill="#5E6474" stroke="{INK}" stroke-width="{SW}"/>'
                 f'<rect x="{x - 10}" y="-10" width="8" height="{H + 20}" fill="#8A91A3"/>')
    return "".join(s)


def fajo():
    """Fajo de billetes (240x150)."""
    s = []
    for i in range(3):
        y = 60 - i * 16
        s.append(f'<rect x="{14 + i * 4}" y="{y}" width="200" height="80" rx="6" fill="#7CC27A" stroke="{INK}" stroke-width="5"/>')
    s.append(f'<circle cx="122" cy="68" r="22" fill="#A8DDA4" stroke="{INK}" stroke-width="4"/>'
             f'<rect x="96" y="28" width="52" height="80" fill="#F2E7C9" stroke="{INK}" stroke-width="4"/>')
    return "".join(s)


def avion():
    """Avión privado blanco (520x220), mirando a la derecha."""
    return (ln("M 30 120 Q 60 86 160 84 L 420 84 Q 500 92 510 116 Q 500 140 420 146 L 160 146 Q 60 144 30 120 Z", SW, INK, "#F5F6F8")
            + ln("M 220 140 L 330 210 L 370 210 L 300 140 Z", 6, INK, "#DCE0E8")
            + ln("M 230 90 L 320 20 L 356 20 L 300 90 Z", 6, INK, "#DCE0E8")
            + ln("M 40 116 L 20 50 L 60 50 L 96 92 Z", 6, INK, "#2F4C8F")
            + "".join(f'<rect x="{x}" y="100" width="22" height="18" rx="7" fill="#2F4C8F"/>' for x in range(170, 400, 40))
            + ln("M 440 96 Q 480 100 496 112 L 452 112 Z", 0, "none", "#2F4C8F"))


def silueta_vip(k=0):
    """Persona famosa anónima: silueta de traje con un '?' (220x420, ancla abajo)."""
    c = ["#2B2F3E", "#3A2F45", "#2F3A45"][k % 3]
    return (f'<circle cx="110" cy="96" r="62" fill="{c}"/>'
            f'<path d="M 10 420 Q 14 210 110 180 Q 206 210 210 420 Z" fill="{c}"/>'
            f'<path d="M 90 186 L 110 260 L 130 186 Z" fill="#E8E8EE"/><path d="M 104 200 L 116 200 L 112 270 L 108 270 Z" fill="#B33A3A"/>')


def camara_seguridad(rota=False):
    """Cámara de seguridad en un soporte de pared (300x200); rota=True: con una X roja."""
    s = [ln("M 20 40 L 20 160", 10), ln("M 20 100 L 80 100", 10),
         ln("M 80 70 L 240 50 L 260 110 L 96 134 Z", SW, INK, "#E8E9EE"),
         ln("M 240 50 L 286 62 L 300 116 L 260 110 Z", SW, INK, "#2B2B33"),
         f'<circle cx="276" cy="88" r="11" fill="#5A9BD8"/>']
    if rota:
        s.append(ln("M 120 40 L 220 150 M 220 40 L 120 150", 16, "#E53935"))
    else:
        s.append(f'<circle cx="104" cy="88" r="7" fill="#E53935"/>')
    return "".join(s)


def monitor_estatica(k=0):
    """Monitor de vigilancia con estática (300x260); k cambia el ruido (loop)."""
    rnd = random.Random(40 + k)
    s = [f'<rect x="8" y="8" width="284" height="210" rx="16" fill="#2B2B33" stroke="{INK}" stroke-width="{SW}"/>',
         '<clipPath id="me"><rect x="26" y="26" width="248" height="174" rx="6"/></clipPath><g clip-path="url(#me)">',
         '<rect x="26" y="26" width="248" height="174" fill="#777"/>']
    for _ in range(260):
        g = rnd.randint(30, 240)
        s.append(f'<rect x="{rnd.randint(26, 270)}" y="{rnd.randint(26, 196)}" width="{rnd.randint(4, 18)}" height="{rnd.randint(2, 6)}" '
                 f'fill="rgb({g},{g},{g})"/>')
    for y in range(26, 200, 8):
        s.append(f'<rect x="26" y="{y}" width="248" height="2" fill="#000" opacity=".18"/>')
    s.append("</g>" + ln("M 130 218 L 120 250 L 180 250 L 170 218", 6, INK, "#2B2B33"))
    return "".join(s)


def guardia_dormido():
    """Guardia de cárcel dormido sentado en el escritorio (620x560, ancla abajo)."""
    piel = "#E9B58F"
    s = [f'<rect x="20" y="360" width="580" height="40" rx="8" fill="#7A5236" stroke="{INK}" stroke-width="{SW}"/>',
         f'<rect x="50" y="400" width="30" height="160" fill="#5E3E28" stroke="{INK}" stroke-width="5"/>'
         f'<rect x="540" y="400" width="30" height="160" fill="#5E3E28" stroke="{INK}" stroke-width="5"/>']
    s.append(f'<rect x="200" y="240" width="220" height="140" rx="60" fill="#3E5272" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<ellipse cx="300" cy="330" rx="120" ry="34" fill="#3E5272" stroke="{INK}" stroke-width="{SW}"/>')   # brazos cruzados
    s.append(f'<circle cx="300" cy="250" r="86" fill="{piel}" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(ln("M 252 250 Q 268 260 284 250", 6) + ln("M 316 250 Q 332 260 348 250", 6) + ln("M 286 290 Q 300 300 314 290", 6))
    s.append(ln("M 206 214 Q 300 150 394 214 L 394 230 L 206 230 Z", SW, INK, "#2F3E5C")
             + ln("M 194 230 L 406 230 Q 420 246 400 252 L 200 252 Q 180 246 194 230 Z", SW, INK, "#24324A")
             + f'<rect x="286" y="182" width="28" height="24" rx="4" fill="#F2C230" stroke="{INK}" stroke-width="3"/>')
    s.append(f'<rect x="440" y="300" width="110" height="62" rx="6" fill="#F5F0E6" stroke="{INK}" stroke-width="4"/>'
             + ln("M 456 320 L 530 320 M 456 336 L 512 336", 4, "#7F8FA8"))
    return "".join(s)


def taza():
    """Taza blanca (260x240) para el meme estampado (el texto va con el motor)."""
    return (ln("M 30 30 L 200 30 L 190 220 Q 115 236 40 220 Z", SW, INK, "#FFFFFF")
            + ln("M 198 70 Q 260 74 254 128 Q 248 176 192 170", 14, INK) + ln("M 198 70 Q 260 74 254 128 Q 248 176 192 170", 6, "#fff")
            + f'<ellipse cx="115" cy="30" rx="85" ry="14" fill="#5B3A29" stroke="{INK}" stroke-width="6"/>')


def remera():
    """Remera negra (420x420) para el meme estampado."""
    return ln("M 120 20 Q 210 70 300 20 L 410 80 L 370 170 L 320 150 L 320 410 L 100 410 L 100 150 L 50 170 L 10 80 Z",
              SW, INK, "#24242C") + ln("M 150 30 Q 210 80 270 30", 5, "#3A3A46")


def cortina_feed():
    """Transición de los memes: un panel de 'feed' (tarjetas, corazones y caritas) que cruza la pantalla."""
    rnd = random.Random(33)
    s = [f'<rect x="0" y="0" width="1500" height="2100" rx="60" fill="#5B3FD9" stroke="{INK}" stroke-width="10"/>',
         '<rect x="40" y="0" width="1420" height="2100" fill="#6A4FF0" opacity=".5"/>']
    for col in range(3):
        y = -60 + col * 140
        while y < 2100:
            x, h = 80 + col * 470, rnd.choice([300, 360, 420])
            s.append(f'<rect x="{x}" y="{y}" width="400" height="{h}" rx="28" fill="#FFFFFF" stroke="{INK}" stroke-width="6"/>'
                     f'<rect x="{x + 18}" y="{y + 18}" width="364" height="{h - 110}" rx="16" '
                     f'fill="{rnd.choice(["#9ADCFF", "#FFD23F", "#FF8FA8", "#8BD06A", "#C9B8FF"])}"/>'
                     f'<rect x="{x + 18}" y="{y + h - 72}" width="230" height="16" rx="8" fill="#D8D4E8"/>'
                     f'<rect x="{x + 18}" y="{y + h - 44}" width="150" height="16" rx="8" fill="#D8D4E8"/>')
            if rnd.random() < .6:
                s.append(f'<g transform="translate({x + 300} {y + h - 60}) scale(.32)">{emoji_risa() if rnd.random() < .5 else corazon()}</g>')
            y += h + 40
    return "".join(s)


# ---------------------------------------------------------------- memes: fondos
def fondo_internet():
    """'Internet': violeta a azul con luces desenfocadas, grilla de puntos y siluetas de íconos."""
    rnd = random.Random(71)
    s = [f'<rect width="{W}" height="{H}" fill="url(#inet)"/>']
    for _ in range(14):
        s.append(f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(0, H):.0f}" r="{rnd.uniform(60, 200):.0f}" '
                 f'fill="{rnd.choice(["#7A5CFF", "#3FA9F5", "#FF5DA2"])}" opacity="{rnd.uniform(.06, .14):.2f}"/>')
    for y in range(40, H, 60):
        for x in range(30, W, 60):
            s.append(f'<circle cx="{x}" cy="{y}" r="2" fill="#fff" opacity=".07"/>')
    iconos = ["M 0 -30 C 30 -60 60 -10 0 30 C -60 -10 -30 -60 0 -30 Z", "M -24 -30 L 30 0 L -24 30 Z",
              "M -40 -28 L 40 -28 L 40 18 L 0 18 L -20 36 L -20 18 L -40 18 Z"]
    for i in range(10):
        x, y = rnd.uniform(60, W - 60), rnd.uniform(200, H - 200)
        s.append(f'<path transform="translate({x:.0f} {y:.0f}) scale({rnd.uniform(1, 1.8):.2f}) rotate({rnd.uniform(-20, 20):.0f})" '
                 f'd="{iconos[i % 3]}" fill="none" stroke="#fff" stroke-width="5" opacity=".08"/>')
    defs = ('<linearGradient id="inet" x1="0" y1="0" x2="0.3" y2="1"><stop offset="0" stop-color="#2A1B5C"/>'
            '<stop offset=".55" stop-color="#1A2470"/><stop offset="1" stop-color="#0E1640"/></linearGradient>')
    return "".join(s), defs


def fondo_campus(noche=False):
    """Campus universitario: edificio de ladrillo con columnas, árboles, césped; noche=True: oscuro con ventanas prendidas."""
    cielo = ("#0E1A3A", "#24315C") if noche else ("#8FD3FF", "#D6F0FF")
    s = [f'<rect width="{W}" height="{H}" fill="url(#cc)"/>']
    if noche:
        rnd = random.Random(5)
        s += [f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(0, 700):.0f}" r="2" fill="#fff" opacity="{rnd.uniform(.3, .8):.2f}"/>'
              for _ in range(60)]
        s.append('<circle cx="900" cy="640" r="56" fill="#F4F1DC" opacity=".9"/>')
    lad, lad2, col = ("#5A2E28", "#4A2520", "#8A8FA0") if noche else ("#B5523B", "#9C4330", "#F4F1EA")
    s.append(ln("M 100 1250 L 100 760 L 980 760 L 980 1250 Z", SW, INK, lad))
    for y in range(800, 1250, 40):
        s.append(ln(f"M 100 {y} L 980 {y}", 2, lad2))
    s.append(ln("M 330 760 L 540 600 L 750 760 Z", SW, INK, col))   # frontón
    s.append(ln("M 300 760 L 780 760 L 780 790 L 300 790 Z", SW, INK, col))
    for x in range(330, 760, 70):
        s.append(f'<rect x="{x}" y="790" width="34" height="420" fill="{col}" stroke="{INK}" stroke-width="5"/>')
    ventana = "#FFD86B" if noche else "#5B7FA6"
    for x in (150, 220, 860, 930):
        for y in (840, 980, 1120):
            s.append(f'<rect x="{x - 25}" y="{y}" width="50" height="80" rx="20" fill="{ventana}" stroke="{INK}" stroke-width="5"/>')
    s.append(ln("M 300 1210 L 780 1210 L 800 1250 L 280 1250 Z", SW, INK, col))
    arbol, arbol2 = ("#1F3A2A", "#16301F") if noche else ("#5DB85A", "#3F9A44")
    for x, y, r in [(40, 1080, 170), (1040, 1060, 180), (170, 1170, 120), (920, 1170, 130)]:
        s.append(f'<rect x="{x - 14}" y="{y}" width="28" height="200" fill="#6B4A2F" stroke="{INK}" stroke-width="5"/>')
        s.append(f'<circle cx="{x}" cy="{y - r * .3:.0f}" r="{r}" fill="{arbol}" stroke="{INK}" stroke-width="{SW}"/>')
        s.append(f'<circle cx="{x - r * .3:.0f}" cy="{y - r * .5:.0f}" r="{r * .45:.0f}" fill="{arbol2}"/>')
    pasto = ("#1E3324", "#253D2B") if noche else ("#7CC56B", "#6AB35A")
    s.append(f'<rect x="0" y="1250" width="{W}" height="{H - 1250}" fill="{pasto[0]}"/>')
    s.append(ln("M 0 1250 L 1080 1250", SW))
    s.append(f'<path d="M 420 1250 L 660 1250 L 860 1920 L 220 1920 Z" fill="{"#3B3A44" if noche else "#E2D6BC"}"/>')
    if noche:
        s.append(f'<rect width="{W}" height="{H}" fill="#0A1030" opacity=".35"/>')
    defs = (f'<linearGradient id="cc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{cielo[0]}"/>'
            f'<stop offset="1" stop-color="{cielo[1]}"/></linearGradient>')
    return "".join(s), defs


def fondo_mansion():
    """Fiesta en una mansión de noche: paredes violetas, ventanal con la ciudad, neones y piso brillante."""
    rnd = random.Random(9)
    s = [f'<rect width="{W}" height="{H}" fill="url(#mv)"/>']
    s.append(ln("M 190 380 L 890 380 L 890 1120 L 190 1120 Z", SW, INK, "#0D1033"))
    for _ in range(26):   # ciudad
        x, w, h = rnd.uniform(190, 860), rnd.uniform(40, 90), rnd.uniform(180, 520)
        s.append(f'<rect x="{x:.0f}" y="{1120 - h:.0f}" width="{w:.0f}" height="{h:.0f}" fill="#1A1F4A"/>')
        for _ in range(int(h / 60)):
            s.append(f'<rect x="{x + rnd.uniform(6, w - 14):.0f}" y="{1120 - h + rnd.uniform(10, h - 20):.0f}" width="8" height="10" fill="#FFD86B" opacity=".7"/>')
    s.append(ln("M 540 380 L 540 1120 M 190 750 L 890 750", 10, "#2A2552"))
    s.append(ln("M 190 380 L 890 380 L 890 1120 L 190 1120 Z", 16, "#2A2552"))
    s.append(ln("M 60 300 L 1020 300", 12, "#FF4FD8", extra='opacity=".9"') + ln("M 60 300 L 1020 300", 30, "#FF4FD8", extra='opacity=".18"'))
    s.append(ln("M 60 1200 L 1020 1200", 10, "#3FD0FF", extra='opacity=".9"') + ln("M 60 1200 L 1020 1200", 26, "#3FD0FF", extra='opacity=".18"'))
    s.append(f'<rect x="0" y="1250" width="{W}" height="{H - 1250}" fill="url(#piso)"/>' + ln("M 0 1250 L 1080 1250", SW))
    for x in range(-200, 1300, 160):
        s.append(ln(f"M 540 1250 L {x} 1920", 3, "#3A2E62"))
    s.append('<ellipse cx="540" cy="1500" rx="420" ry="90" fill="#FF4FD8" opacity=".1"/>')
    defs = ('<linearGradient id="mv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2B1650"/>'
            '<stop offset="1" stop-color="#4A2470"/></linearGradient>'
            '<linearGradient id="piso" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#22163E"/>'
            '<stop offset="1" stop-color="#120B24"/></linearGradient>')
    return "".join(s), defs


def fondo_celda():
    """Celda: paredes de bloques de hormigón, ventanita alta con rejas, cucheta, inodoro de acero."""
    s = [f'<rect width="{W}" height="{H}" fill="#7C8796"/>']
    for y in range(0, 1300, 70):
        off = 0 if (y // 70) % 2 else 70
        s.append(ln(f"M 0 {y} L {W} {y}", 3, "#6A7484"))
        for x in range(off, W, 140):
            s.append(ln(f"M {x} {y} L {x} {y + 70}", 3, "#6A7484"))
    s.append(f'<rect x="420" y="190" width="240" height="150" fill="#24315C" stroke="{INK}" stroke-width="{SW}"/>'
             '<circle cx="610" cy="230" r="26" fill="#F4F1DC" opacity=".9"/>')
    for x in range(450, 660, 45):
        s.append(f'<rect x="{x - 7}" y="190" width="14" height="150" fill="#4A4F5C" stroke="{INK}" stroke-width="4"/>')
    s.append('<path d="M 420 340 L 660 340 L 760 1250 L 320 1250 Z" fill="#DDE6F2" opacity=".08"/>')
    s.append(ln("M 40 900 L 330 900 L 330 960 L 40 960 Z", SW, INK, "#5A6272")
             + f'<rect x="40" y="860" width="290" height="40" rx="10" fill="#C9D2E0" stroke="{INK}" stroke-width="5"/>'
             + ln("M 40 960 L 40 1250 M 330 960 L 330 1250", 10, "#5A6272"))   # cama
    s.append(ln("M 860 1080 L 1000 1080 L 980 1200 Q 930 1230 880 1200 Z", SW, INK, "#B8C0CC")
             + f'<rect x="900" y="980" width="100" height="100" rx="10" fill="#B8C0CC" stroke="{INK}" stroke-width="{SW}"/>')
    s.append(f'<rect x="0" y="1250" width="{W}" height="{H - 1250}" fill="#5A6170"/>' + ln("M 0 1250 L 1080 1250", SW))
    s.append(f'<rect width="{W}" height="{H}" fill="url(#cv)"/>')
    defs = ('<radialGradient id="cv" cx="0.5" cy="0.45" r="0.75"><stop offset=".55" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#000" stop-opacity=".5"/></radialGradient>')
    return "".join(s), defs


def fondo_isla():
    """Isla privada al atardecer: cielo naranja y rosa, mar, palmeras y una mansión blanca."""
    s = [f'<rect width="{W}" height="{H}" fill="url(#ia)"/>',
         '<circle cx="540" cy="1080" r="150" fill="#FFE08A" opacity=".95"/>',
         f'<rect x="0" y="1080" width="{W}" height="{H - 1080}" fill="url(#im)"/>']
    for y in range(1100, 1300, 28):
        s.append(ln(f"M {300 + (y % 3) * 40} {y} L {780 - (y % 3) * 40} {y}", 4, "#FFE08A", extra='opacity=".45"'))
    s.append(ln("M 80 1300 Q 540 1150 1000 1300 L 1000 1360 L 80 1360 Z", SW, INK, "#F2D49B"))
    s.append(ln("M 380 1210 L 380 1120 L 700 1120 L 700 1210 Z", SW, INK, "#FFFFFF")
             + ln("M 360 1124 L 540 1060 L 720 1124 Z", SW, INK, "#D8DCE6")
             + "".join(f'<rect x="{x}" y="1140" width="36" height="46" fill="#5B7FA6" stroke="{INK}" stroke-width="4"/>'
                       for x in (410, 480, 564, 634)))
    for x, h, d in [(200, 380, 1), (880, 420, -1), (300, 300, -1)]:
        s.append(ln(f"M {x} 1300 Q {x + 30 * d} {1300 - h / 2} {x + 10 * d} {1300 - h}", 16, INK)
                 + ln(f"M {x} 1300 Q {x + 30 * d} {1300 - h / 2} {x + 10 * d} {1300 - h}", 10, "#8A5A3A"))
        top = (x + 10 * d, 1300 - h)
        for a in (-150, -110, -70, -30, 10, 200):
            r = math.radians(a)
            ex, ey = top[0] + 150 * math.cos(r), top[1] + 90 * math.sin(r) + 40
            s.append(ln(f"M {top[0]} {top[1]} Q {(top[0] + ex) / 2} {top[1] - 40} {ex:.0f} {ey:.0f}", 22, INK)
                     + ln(f"M {top[0]} {top[1]} Q {(top[0] + ex) / 2} {top[1] - 40} {ex:.0f} {ey:.0f}", 14, "#2F7A43"))
    defs = ('<linearGradient id="ia" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5A3A8A"/>'
            '<stop offset=".35" stop-color="#E86A8A"/><stop offset=".55" stop-color="#FF9F5A"/></linearGradient>'
            '<linearGradient id="im" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E8806A"/>'
            '<stop offset=".25" stop-color="#3A5EA8"/><stop offset="1" stop-color="#1F2F6B"/></linearGradient>')
    return "".join(s), defs


# ---------------------------------------------------------------- fondos (1080x1920)
W, H = 1080, 1920


def fondo_espacio(tema="azul"):
    """Cielo estrellado con nebulosas suaves. tema: azul, rojo, violeta."""
    temas = {"azul": ("#1B2259", "#0A0D2B", ["#5B3FB8", "#1E7FA8"]),
             "rojo": ("#24142E", "#0B070F", ["#7A1E2E", "#4A1E5E"]),
             "violeta": ("#3A1A5E", "#120A26", ["#B23A8E", "#3F4FC8"])}
    c0, c1, neb = temas[tema]
    rnd = random.Random({"azul": 1, "rojo": 2, "violeta": 3}[tema])
    s = [f'<rect width="{W}" height="{H}" fill="url(#esp)"/>']
    for i, (x, y, rx, ry) in enumerate([(220, 520, 520, 300), (860, 1250, 560, 340), (500, 1700, 420, 220)]):
        s.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="url(#neb{i % 2})" '
                 f'transform="rotate({rnd.uniform(-25, 25):.0f} {x} {y})"/>')
    for _ in range(170):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        r = rnd.choice([1.5, 2, 2, 2.5, 3, 4])
        s.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" opacity="{rnd.uniform(.35, .9):.2f}"/>')
    for _ in range(16):
        s.append(estrella4(rnd.uniform(40, 1040), rnd.uniform(40, 1880), rnd.uniform(7, 14), "#FFF6D6", 0))
    defs = (f'<radialGradient id="esp" cx="0.5" cy="0.42" r="0.85"><stop offset="0" stop-color="{c0}"/>'
            f'<stop offset="1" stop-color="{c1}"/></radialGradient>'
            + "".join(f'<radialGradient id="neb{i}" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{c}" stop-opacity=".55"/>'
                      f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>' for i, c in enumerate(neb)))
    return "".join(s), defs


def fondo_espacio_azul():
    return fondo_espacio("azul")


def fondo_espacio_rojo():
    return fondo_espacio("rojo")


def fondo_espacio_violeta():
    return fondo_espacio("violeta")


def fondo_mazmorra():
    """Pared de piedra con cadenas, piso oscuro y viñeta. Las antorchas van aparte (para animarlas)."""
    rnd = random.Random(21)
    s = [f'<rect width="{W}" height="{H}" fill="#3B3F52"/>']
    bh, y, row = 96, 0, 0
    while y < 1240:
        off = 0 if row % 2 == 0 else -80
        x = off
        while x < W:
            bw = rnd.choice([150, 170, 190])
            c = rnd.choice(["#4A4F66", "#454A60", "#50556D", "#42475C"])
            s.append(f'<rect x="{x + 5}" y="{y + 5}" width="{bw - 10}" height="{bh - 10}" rx="14" fill="{c}" '
                     f'stroke="#2C2F3E" stroke-width="5"/>')
            x += bw
        y += bh
        row += 1
    # cadenas colgando
    for cx, n in [(180, 7), (900, 9)]:
        for i in range(n):
            yy = 40 + i * 46
            if i % 2 == 0:
                s.append(f'<ellipse cx="{cx}" cy="{yy}" rx="16" ry="26" fill="none" stroke="#8E97A8" stroke-width="9"/>')
            else:
                s.append(f'<rect x="{cx - 4}" y="{yy - 24}" width="8" height="48" rx="4" fill="#8E97A8"/>')
        s.append(f'<circle cx="{cx}" cy="{40 + n * 46}" r="30" fill="none" stroke="#8E97A8" stroke-width="12"/>')
    s.append(f'<rect x="0" y="1230" width="{W}" height="{H - 1230}" fill="#2A2C38"/>')
    s.append(ln(f"M 0 1232 L {W} 1232", 10, "#1E1F28"))
    for y in range(1330, H, 130):
        s.append(ln(f"M 0 {y} L {W} {y}", 5, "#23252F"))
    for x in range(-200, W + 400, 260):
        s.append(ln(f"M {W / 2 + (x - W / 2) * .3:.0f} 1232 L {x} {H}", 5, "#23252F"))
    s.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    defs = ('<radialGradient id="vig" cx="0.5" cy="0.45" r="0.75"><stop offset="0.45" stop-color="#FF9A3C" stop-opacity="0.10"/>'
            '<stop offset="1" stop-color="#0A0A12" stop-opacity="0.65"/></radialGradient>')
    return "".join(s), defs


def fondo_pantano():
    """Pantano de noche: cielo verdoso, luna, árboles secos y agua turbia (desde y=1080)."""
    rnd = random.Random(31)
    s = [f'<rect width="{W}" height="{H}" fill="url(#cielo)"/>']
    s.append(f'<circle cx="820" cy="420" r="120" fill="#F4F1C9" opacity=".9"/>'
             f'<circle cx="820" cy="420" r="190" fill="#F4F1C9" opacity=".12"/>')
    for _ in range(40):
        s.append(f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(0, 900):.0f}" r="{rnd.choice([2, 2.5, 3])}" '
                 f'fill="#fff" opacity="{rnd.uniform(.3, .8):.2f}"/>')
    # árboles secos (siluetas)
    for x0, k in [(90, 1.0), (980, .85), (300, .6)]:
        g = (f"M {x0 - 26 * k} 1090 L {x0 - 14 * k} {1090 - 520 * k} L {x0 - 90 * k} {1090 - 700 * k} "
             f"L {x0 - 6 * k} {1090 - 580 * k} L {x0 + 10 * k} {1090 - 760 * k} L {x0 + 20 * k} {1090 - 560 * k} "
             f"L {x0 + 100 * k} {1090 - 640 * k} L {x0 + 26 * k} {1090 - 470 * k} L {x0 + 30 * k} 1090 Z")
        s.append(f'<path d="{g}" fill="#1C2620"/>')
    s.append(ln(f"M -10 1090 Q 270 1060 540 1090 Q 810 1120 1090 1080 L 1090 1930 L -10 1930 Z", SW, INK, "#3E5A3A"))
    s.append(f'<rect x="0" y="1090" width="{W}" height="{H - 1090}" fill="url(#agua)"/>')
    for _ in range(18):
        x, y = rnd.uniform(40, 1040), rnd.uniform(1160, 1880)
        w = rnd.uniform(60, 140)
        s.append(ln(f"M {x - w / 2:.0f} {y:.0f} Q {x:.0f} {y - 12:.0f} {x + w / 2:.0f} {y:.0f}", 5, "#6E8C5E", extra='opacity=".6"'))
    # juncos
    for x in [40, 70, 1010, 1040, 520]:
        h = rnd.uniform(140, 220)
        s.append(stroke_path(f"M {x} 1110 Q {x + 10} {1110 - h / 2:.0f} {x - 6} {1110 - h:.0f}", "#4E6B3A", 10, INK, 20))
        s.append(f'<rect x="{x - 14}" y="{1110 - h - 40:.0f}" width="22" height="56" rx="11" fill="#6B4A2F" stroke="{INK}" stroke-width="5"/>')
    defs = ('<linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1B2433"/>'
            '<stop offset="0.55" stop-color="#2F4A3E"/></linearGradient>'
            '<linearGradient id="agua" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3E5A3A" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#1A2A1C" stop-opacity=".8"/></linearGradient>')
    return "".join(s), defs


def fondo_abismo():
    """Aguas profundas: azul noche que se va a negro, un resplandor lejano arriba y nieve marina quieta."""
    rnd = random.Random(61)
    s = [f'<rect width="{W}" height="{H}" fill="url(#ab)"/>',
         f'<ellipse cx="540" cy="-200" rx="900" ry="700" fill="url(#luz)"/>']
    for _ in range(90):
        s.append(f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(0, H):.0f}" r="{rnd.choice([1.5, 2, 2.5])}" '
                 f'fill="#CFE8F0" opacity="{rnd.uniform(.15, .45):.2f}"/>')
    defs = ('<linearGradient id="ab" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0E2A4A"/>'
            '<stop offset=".6" stop-color="#06121F"/><stop offset="1" stop-color="#020509"/></linearGradient>'
            '<radialGradient id="luz" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#3A7AA8" stop-opacity=".35"/>'
            '<stop offset="1" stop-color="#3A7AA8" stop-opacity="0"/></radialGradient>')
    return "".join(s), defs


def fondo_lecho():
    """Fondo marino con fumarolas (chimeneas que largan gases), tapetes de bacterias y gusanos de tubo."""
    body, defs = fondo_abismo()
    s = [body]
    for x, h, w in [(200, 400, 110), (880, 640, 130), (560, 300, 80)]:   # chimeneas
        s.append(ln(f"M {x - w} 1300 L {x - w * .6:.0f} {1300 - h} Q {x} {1280 - h} {x + w * .6:.0f} {1300 - h} L {x + w} 1300 Z",
                    SW, INK, "#2A2624"))
        for k in range(4):
            yy = 1300 - h * (k + 1) / 5
            s.append(ln(f"M {x - w * .7:.0f} {yy:.0f} Q {x} {yy + 14:.0f} {x + w * .7:.0f} {yy:.0f}", 5, "#3E3834"))
        s.append(f'<ellipse cx="{x}" cy="{1300 - h}" rx="{w * .5:.0f}" ry="14" fill="#FF8A3A" opacity=".35"/>')
    s.append(ln("M -10 1290 Q 200 1240 420 1280 Q 640 1320 860 1270 Q 980 1250 1090 1280 L 1090 1930 L -10 1930 Z",
                SW, INK, "#1E2430"))
    rnd = random.Random(62)
    for _ in range(9):   # tapetes blancos de bacterias
        x, y = rnd.uniform(40, 1040), rnd.uniform(1290, 1500)
        s.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rnd.uniform(40, 90):.0f}" ry="12" fill="#E8E2D0" opacity=".55"/>')
    s.append(f'<g transform="translate(330 1006)">{gusano_tubo()}</g>')
    s.append(f'<g transform="translate(980 1010) scale(.8)">{gusano_tubo()}</g>')
    return "".join(s), defs


def papiro(x, base, alto, k=1.0, color="#5E8A3A", color2="#7FA84A", contorno=INK):
    """Mata de papiro: tallos finos con una 'explosión' de hebras arriba."""
    s = []
    for dx, h in [(-14, alto), (0, alto * 1.12), (16, alto * .95)]:
        x0, y1 = x + dx * k, base - h * k
        s.append(stroke_path(f"M {x0:.0f} {base} Q {x0 + 6:.0f} {(base + y1) / 2:.0f} {x0:.0f} {y1:.0f}", color, 8 * k, contorno, 16 * k))
        for a in range(-84, 85, 12):
            t = math.radians(a - 90)
            L = 80 * k
            s.append(ln(f"M {x0:.0f} {y1:.0f} Q {x0 + L * .6 * math.cos(t):.0f} {y1 + L * .6 * math.sin(t) - 10 * k:.0f} "
                        f"{x0 + L * math.cos(t):.0f} {y1 + L * math.sin(t) + 16 * k:.0f}", 4.5 * k, color2))
    return "".join(s)


def fondo_humedal():
    """Pantano de papiros a la mañana (hábitat del picozapato): agua desde y≈1250 y una orilla de pasto."""
    s = [f'<rect width="{W}" height="{H}" fill="url(#cielo)"/>']
    s.append(f'<circle cx="780" cy="560" r="90" fill="#FFF0C8"/><circle cx="780" cy="560" r="170" fill="#FFF0C8" opacity=".3"/>')
    s.append(ln("M -10 900 Q 150 820 320 880 Q 500 800 700 870 Q 880 810 1090 870 L 1090 1000 L -10 1000 Z", 0, "none", "#A9C2B4"))
    s.append(ln("M -10 960 Q 200 900 400 950 Q 640 890 860 950 Q 980 930 1090 950 L 1090 1060 L -10 1060 Z", 0, "none", "#8FB09A"))
    for x, h, k in [(60, 260, .8), (190, 220, .7), (900, 250, .8), (1010, 230, .7), (420, 180, .55), (640, 200, .6)]:
        s.append(papiro(x, 1080, h, k, "#6E9A5A", "#8FB86A", "#4E6A44"))
    s.append(f'<rect x="0" y="1060" width="{W}" height="{H - 1060}" fill="url(#agua)"/>')
    for y in range(1100, H, 90):
        s.append(ln(f"M 80 {y} Q 300 {y - 12} 520 {y} Q 760 {y + 12} 1000 {y}", 5, "#BFE0DA", extra='opacity=".35"'))
    # orilla flotante de vegetación donde se para el picozapato
    s.append(ln("M 120 1250 Q 300 1200 560 1215 Q 820 1200 1000 1260 Q 980 1330 780 1340 Q 520 1360 280 1340 Q 110 1320 120 1250 Z",
                SW, INK, "#7A944A"))
    for x in range(160, 980, 46):
        s.append(ln(f"M {x} 1250 l -6 -26 M {x} 1250 l 8 -30", 5, "#5E7A3A"))
    defs = ('<linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F3D2B2"/>'
            '<stop offset=".55" stop-color="#D5E8E4"/></linearGradient>'
            '<linearGradient id="agua" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7AA8A2"/>'
            '<stop offset="1" stop-color="#3E6A66"/></linearGradient>')
    return "".join(s), defs


def fondo_bosque(noche=False):
    """Bosque seco (hábitat del urutaú). La misma composición de día y de noche, para fundirlas."""
    c = dict(c0="#1E2552", c1="#3A2E62", lejos="#2A2E52", arbol="#1E1A2E", copa="#25324A", suelo="#2A3A34",
             pasto="#3A4E44") if noche else \
        dict(c0="#9ED4F0", c1="#F5EBC8", lejos="#B8C8A0", arbol="#6E5A44", copa="#8AAA5A", suelo="#C9B07A", pasto="#A89A5A")
    s = [f'<rect width="{W}" height="{H}" fill="url(#cielo)"/>']
    if noche:
        rnd = random.Random(14)
        for _ in range(60):
            s.append(f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(0, 900):.0f}" r="{rnd.choice([1.5, 2, 2.5])}" '
                     f'fill="#fff" opacity="{rnd.uniform(.4, .9):.2f}"/>')
        s.append(f'<circle cx="800" cy="420" r="80" fill="#F4F1C9"/><circle cx="800" cy="420" r="150" fill="#F4F1C9" opacity=".15"/>')
    else:
        s.append(f'<circle cx="820" cy="380" r="80" fill="#FFF4C2" opacity=".9"/>')
    s.append(ln("M -10 1150 Q 200 1080 400 1130 Q 640 1070 860 1120 Q 980 1100 1090 1130 L 1090 1400 L -10 1400 Z", 0, "none", c["lejos"]))
    # árboles finos y secos con copas ralas
    for x, h, w in [(90, 900, 26), (300, 760, 20), (760, 820, 22), (980, 940, 28)]:
        s.append(ln(f"M {x - w} 1380 L {x - w / 2:.0f} {1380 - h} L {x + w / 2:.0f} {1380 - h} L {x + w} 1380 Z", 0, "none", c["arbol"]))
        for dy, d in [(.55, 1), (.75, -1), (.85, 1)]:
            y0 = 1380 - h * dy
            s.append(stroke_path(f"M {x} {y0:.0f} L {x + d * 120} {y0 - 90:.0f}", c["arbol"], 10, c["arbol"], 10))
            s.append(f'<ellipse cx="{x + d * 130}" cy="{y0 - 110:.0f}" rx="90" ry="40" fill="{c["copa"]}" opacity=".85"/>')
    s.append(ln(f"M -10 1360 Q 270 1330 540 1360 Q 810 1390 1090 1350 L 1090 1930 L -10 1930 Z", SW, INK, c["suelo"]))
    rnd = random.Random(15)
    for _ in range(40):
        x, y = rnd.uniform(0, W), rnd.uniform(1380, 1880)
        s.append(ln(f"M {x:.0f} {y:.0f} l -8 -22 M {x:.0f} {y:.0f} l 6 -26", 5, c["pasto"]))
    defs = (f'<linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c["c0"]}"/>'
            f'<stop offset=".65" stop-color="{c["c1"]}"/></linearGradient>')
    return "".join(s), defs


def fondo_rio():
    """Río amazónico (hábitat del hoacín): paredes de selva, ramas sobre el agua."""
    s = [f'<rect width="{W}" height="{H}" fill="url(#cielo)"/>']
    for x0, w, c in [(-60, 420, "#2E6A3A"), (720, 440, "#2E6A3A"), (-20, 300, "#3E8A4A"), (820, 300, "#3E8A4A")]:
        rnd = random.Random(int(x0) + 99)
        for _ in range(14):
            cx, cy, r = x0 + rnd.uniform(0, w), rnd.uniform(200, 1250), rnd.uniform(60, 130)
            s.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="{c}"/>')
    s.append(f'<rect x="0" y="1250" width="{W}" height="{H - 1250}" fill="url(#agua)"/>')
    for y in range(1290, H, 80):
        s.append(ln(f"M 60 {y} Q 300 {y - 14} 540 {y} Q 780 {y + 14} 1020 {y}", 5, "#B9D89A", extra='opacity=".3"'))
    s.append(ln("M -10 1250 Q 270 1236 540 1250 Q 810 1264 1090 1246", SW))
    defs = ('<linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#BFE6C8"/>'
            '<stop offset=".7" stop-color="#E8F2C8"/></linearGradient>'
            '<linearGradient id="agua" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7A8A4A"/>'
            '<stop offset="1" stop-color="#4E5A2E"/></linearGradient>')
    return "".join(s), defs


def pajarito():
    """Silueta de pájaro volando (60x34)."""
    return ln("M 4 22 Q 16 4 30 20 Q 44 4 56 22 Q 44 14 30 28 Q 16 14 4 22 Z", 3, "#2A2A34", "#2A2A34")


def rayitas():
    """Líneas de acción de historieta alrededor de un punto (300x300, centro libre)."""
    s = []
    for a in range(0, 360, 30):
        t = math.radians(a + 8)
        s.append(ln(f"M {150 + 95 * math.cos(t):.0f} {150 + 95 * math.sin(t):.0f} L {150 + 140 * math.cos(t):.0f} "
                    f"{150 + 140 * math.sin(t):.0f}", 9, INK))
    return "".join(s)


def capa_rayos():
    """Rayos de luz diagonales, transparentes (capa de pantalla completa)."""
    s = []
    for x0, w, op in [(-200, 140, .16), (60, 90, .12), (300, 160, .14), (620, 100, .1), (820, 140, .12)]:
        s.append(f'<path d="M {x0} -40 L {x0 + w} -40 L {x0 + w + 700} {H} L {x0 + 500} {H} Z" fill="url(#rayo)" opacity="{op}"/>')
    defs = ('<linearGradient id="rayo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF6C8"/>'
            '<stop offset="1" stop-color="#FFF6C8" stop-opacity="0"/></linearGradient>')
    return "".join(s), defs


def hoja_grande(x, y, r, k, c1="#2E6A2A", c2="#1E4A1E"):
    return (f'<g transform="translate({x} {y}) rotate({r}) scale({k})">'
            + ln("M 0 0 Q 160 -120 400 -20 Q 200 100 0 0 Z", 10, "#163A16", c1) + ln("M 10 0 Q 200 -40 390 -20", 8, c2) + '</g>')


def capa_hojas_frente():
    """Hojas grandes en primer plano, en las esquinas (se desenfocan: profundidad de campo)."""
    return "".join([hoja_grande(-60, 160, 20, 1.2), hoja_grande(-80, 330, -10, 1.0, "#3E7A3A"),
                    hoja_grande(1140, 120, 160, 1.1), hoja_grande(1150, 300, 200, .9, "#3E7A3A"),
                    hoja_grande(-90, 1720, -30, 1.3), hoja_grande(1170, 1760, 210, 1.3, "#3E7A3A")])


def capa_papiros_frente():
    return (papiro(40, 1990, 520, 1.6, "#4E7A3A", "#6E9A4A") + papiro(1030, 1990, 480, 1.5, "#4E7A3A", "#6E9A4A")
            + papiro(150, 1990, 300, 1.3, "#5E8A3A", "#7FA84A"))


def capa_vineta():
    defs = ('<radialGradient id="vg" cx="0.5" cy="0.45" r="0.75"><stop offset="0.55" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#05081A" stop-opacity="0.7"/></radialGradient>')
    return f'<rect width="{W}" height="{H}" fill="url(#vg)"/>', defs


def niebla():
    defs = ('<radialGradient id="nb" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#fff" stop-opacity=".55"/>'
            '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>')
    return '<ellipse cx="700" cy="200" rx="700" ry="200" fill="url(#nb)"/>', defs


def cortina_hojas():
    """Cortina de hojas para las transiciones entre ítems (1500x2100): cubre toda la pantalla al pasar."""
    rnd = random.Random(77)
    s = [f'<rect x="150" y="0" width="1200" height="2100" rx="200" fill="#2E6A2A"/>']
    for _ in range(60):
        x, y = rnd.uniform(0, 1400), rnd.uniform(-100, 2100)
        s.append(hoja_grande(x, y, rnd.uniform(0, 360), rnd.uniform(.5, .9), rnd.choice(["#2E6A2A", "#3E8A3A", "#4E9A4A", "#26582A"])))
    return "".join(s)


def fondo_burst_verde():
    """Rayos como fondo_burst, en verdes (para el gancho de plantas)."""
    cx, cy = 540, 950
    s = [f'<rect width="{W}" height="{H}" fill="#7CCB5A"/>']
    n = 28
    for i in range(0, n, 2):
        a1, a2 = i * 2 * math.pi / n, (i + 1) * 2 * math.pi / n
        s.append(f'<path d="M {cx} {cy} L {cx + 2400 * math.cos(a1):.0f} {cy + 2400 * math.sin(a1):.0f} '
                 f'L {cx + 2400 * math.cos(a2):.0f} {cy + 2400 * math.sin(a2):.0f} Z" fill="#9BDB72"/>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    defs = ('<radialGradient id="vig" cx="0.5" cy="0.5" r="0.75"><stop offset="0.55" stop-color="#2E7A3A" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#1E5A2A" stop-opacity="0.45"/></radialGradient>')
    return "".join(s), defs


def fondo_subsuelo():
    """Corte del suelo: cielo arriba, superficie de arena en y=700 y tierra con capas y piedras."""
    rnd = random.Random(41)
    s = [f'<rect width="{W}" height="700" fill="url(#cielo)"/>']
    s.append(f'<circle cx="880" cy="430" r="80" fill="{P["amarillo"]}" opacity=".9"/>')
    s.append(f'<rect x="0" y="690" width="{W}" height="{H - 690}" fill="#8A5E3E"/>')
    for y, c in [(880, "#7A5236"), (1150, "#6B4630"), (1450, "#5E3E28")]:
        s.append(ln(f"M -10 {y} Q 270 {y - 30} 540 {y} Q 810 {y + 30} 1090 {y} L 1090 1930 L -10 1930 Z", 0, "none", c))
    for _ in range(26):
        x, y, r = rnd.uniform(0, W), rnd.uniform(780, 1880), rnd.uniform(10, 28)
        s.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r:.0f}" ry="{r * .7:.0f}" fill="#A08060" stroke="#4E3420" stroke-width="4"/>')
    s.append(ln(f"M -10 700 Q 270 680 540 700 Q 810 720 1090 696 L 1090 760 L -10 760 Z", SW, INK, "#E8C98A"))
    for _ in range(14):
        x = rnd.uniform(20, 1060)
        s.append(ln(f"M {x:.0f} 700 l -10 -26 M {x:.0f} 700 l 8 -30 M {x:.0f} 700 l 22 -18", 5, "#A89A5A"))
    defs = ('<linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7CC8F0"/>'
            '<stop offset="1" stop-color="#F6E3B0"/></linearGradient>')
    return "".join(s), defs


def fondo_sabana():
    """Sabana seca: cielo, acacia lejana y suelo de arena desde y=1150."""
    rnd = random.Random(42)
    s = [f'<rect width="{W}" height="{H}" fill="url(#cielo)"/>']
    s.append(f'<circle cx="820" cy="460" r="110" fill="{P["amarillo"]}" opacity=".9"/>')
    s.append(f'<path d="M 140 1150 L 150 900 L 170 900 L 180 1150 Z" fill="#6B5A40" opacity=".55"/>'
             f'<ellipse cx="160" cy="880" rx="150" ry="40" fill="#5E7A3A" opacity=".55"/>')
    s.append(ln(f"M -10 1150 Q 270 1120 540 1150 Q 810 1180 1090 1140 L 1090 1930 L -10 1930 Z", SW, INK, "#E8C98A"))
    for _ in range(30):
        x, y = rnd.uniform(0, W), rnd.uniform(1200, 1880)
        s.append(ln(f"M {x:.0f} {y:.0f} l -8 -20 M {x:.0f} {y:.0f} l 6 -24", 5, "#C9A86A"))
    defs = ('<linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6CC0F0"/>'
            '<stop offset="0.6" stop-color="#FCE6B8"/></linearGradient>')
    return "".join(s), defs


def fondo_selva():
    """Selva de Borneo: verdes profundos, hojas grandes en los bordes, lianas y rayos de luz."""
    s = [f'<rect width="{W}" height="{H}" fill="url(#selva)"/>']
    for x0, w in [(260, 120), (620, 160), (860, 90)]:
        s.append(f'<path d="M {x0} 0 L {x0 + w} 0 L {x0 + w * 2.4:.0f} {H} L {x0 + w * .8:.0f} {H} Z" fill="#E8F7C0" opacity=".08"/>')
    for x in (180, 520, 900):
        s.append(stroke_path(f"M {x} 0 Q {x + 40} 300 {x - 20} 600 Q {x - 60} 800 {x + 10} 980", "#4E7A2A", 12, "#1E3A14", 20))
    for (x, y, r, k) in [(-40, 300, 30, 1.2), (1120, 520, 200, 1.1), (-60, 1000, -20, 1.4), (1130, 1250, 210, 1.3),
                         (120, 1700, 10, 1.2), (980, 1780, 190, 1.2)]:
        s.append(f'<g transform="translate({x} {y}) rotate({r}) scale({k})">'
                 + ln("M 0 0 Q 120 -90 300 -20 Q 160 70 0 0 Z", SW, INK, "#3E8A3A")
                 + ln("M 10 0 Q 150 -30 290 -20", 5, "#2E6A2A") + '</g>')
    s.append(ln(f"M -10 1300 Q 270 1260 540 1300 Q 810 1340 1090 1290 L 1090 1930 L -10 1930 Z", SW, INK, "#3E6A2A"))
    defs = ('<linearGradient id="selva" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2E6A3A"/>'
            '<stop offset="1" stop-color="#14361E"/></linearGradient>')
    return "".join(s), defs


def fondo_desierto():
    """Desierto de Namibia: dunas naranjas, cielo pálido y sol fuerte."""
    s = [f'<rect width="{W}" height="{H}" fill="url(#cielo)"/>']
    s.append(f'<circle cx="800" cy="480" r="120" fill="#FFF1B0"/><circle cx="800" cy="480" r="200" fill="#FFF1B0" opacity=".25"/>')
    s.append(ln("M -10 1000 Q 200 760 460 980 Q 600 1080 760 900 Q 900 780 1090 960 L 1090 1930 L -10 1930 Z", SW, INK, "#E8894A"))
    s.append(ln("M 460 980 Q 600 1080 760 900", 6, "#C96A34"))
    s.append(ln("M -10 1180 Q 300 1080 600 1170 Q 860 1240 1090 1150 L 1090 1930 L -10 1930 Z", SW, INK, "#F0A060"))
    s.append(ln(f"M -10 1330 Q 270 1300 540 1330 Q 810 1360 1090 1320 L 1090 1930 L -10 1930 Z", SW, INK, "#F6C089"))
    for y in range(1420, H, 110):
        s.append(ln(f"M 60 {y} Q 300 {y - 20} 540 {y} Q 780 {y + 20} 1020 {y}", 5, "#E0A070", extra='opacity=".6"'))
    defs = ('<linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8FD0F0"/>'
            '<stop offset="0.6" stop-color="#FCE3C0"/></linearGradient>')
    return "".join(s), defs


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


def build_memes():
    """Recursos del short "3 personas que ahora son memes"."""
    for quien, ropas in [("kirk", ["traje"]), ("kirk_chica", ["traje"]), ("kirk_habla", ["traje"]),
                         ("diddy", ["blanco", "preso_caqui"]), ("epstein", ["sueter", "preso_naranja"]),
                         ("kirk_borroso", ["traje"]), ("diddy_borroso", ["blanco"]), ("epstein_borroso", ["sueter"])]:
        for ropa in ropas:
            add(f"{quien}_{ropa}", PERSONA_W, PERSONA_H, persona(quien, ropa), anchor=(0.5, 1.0))
    for cara, kw in VOS_CELU.items():
        add(f"vos_celu_{cara}", 520, 820, vos_celu(**kw), anchor=(0.5, 1.0))
        add(f"vos_celu_{cara}__blink", 520, 820, vos_celu(**dict(kw, eyes="closed")), anchor=(0.5, 1.0))
    add("estudiante_a", 520, 820, estudiante("#46C281", "#F8C9A2", "#E3B24F"), anchor=(0.5, 1.0))
    add("estudiante_b", 520, 820, estudiante("#FF8F6B", "#9B6A4A", "#2A1E1A", mano=True), anchor=(0.5, 1.0))
    add("estudiante_c", 520, 820, estudiante("#7A5CFF", "#E9B58F", "#6B3A1E"), anchor=(0.5, 1.0))
    add("mesa_debate", 760, 330, mesa_debate(), anchor=(0.5, 1.0))
    add("mesa_sin_cartel", 760, 330, mesa_debate(False), anchor=(0.5, 1.0))
    add("carpa", 900, 620, carpa(), anchor=(0.5, 1.0))
    add("microfono", 120, 300, microfono(), anchor=(0.5, 1.0))
    add("celular_marco", 520, 1000, celular_marco())
    add("pantalla_feed", 370, 720, pantalla_feed())
    add("video_kirk", 480, 330, video_card("kirk_video"))
    add("emoji_risa", 200, 200, emoji_risa())
    add("calavera_emoji", 200, 200, calavera_emoji())
    add("vela", 90, 240, vela(), anchor=(0.5, 1.0))
    add("llama_vela", 60, 90, llama_vela(), anchor=(0.5, 1.0))
    add("flores", 300, 240, flores(), anchor=(0.5, 1.0))
    add("retrato_kirk", 360, 440, retrato("kirk_retrato"))
    add("disco_oro", 240, 300, disco_oro())
    add("bola_disco", 220, 260, bola_disco(), anchor=(0.5, 0.0))
    add("siluetas_fiesta_0", 900, 520, siluetas_fiesta(0), anchor=(0.5, 1.0))
    add("siluetas_fiesta_1", 900, 520, siluetas_fiesta(1), anchor=(0.5, 1.0))
    add("aceite_bebe", 120, 260, aceite_bebe(), anchor=(0.5, 1.0))
    add("caja_evidencia", 300, 220, caja_evidencia(), anchor=(0.5, 1.0))
    for c in ("rojo", "azul"):
        body, defs = luz_sirena(c)
        add(f"capa_sirena_{c}", W, H, body, defs)
    add("esposas", 300, 170, esposas())
    add("capa_rejas", W, H, rejas())
    add("fajo", 240, 150, fajo())
    add("avion", 520, 220, avion())
    for k in range(3):
        add(f"silueta_vip_{k}", 220, 420, silueta_vip(k), anchor=(0.5, 1.0))
        add(f"monitor_estatica_{k}", 300, 260, monitor_estatica(k))
    add("camara_seguridad", 300, 200, camara_seguridad())
    add("camara_seguridad_rota", 300, 200, camara_seguridad(True))
    add("guardia_dormido", 620, 560, guardia_dormido(), anchor=(0.5, 1.0))
    add("taza", 260, 240, taza(), anchor=(0.5, 1.0))
    add("remera", 420, 420, remera())
    add("cortina_feed", 1500, 2100, cortina_feed())
    add("capa_negra", W, H, f'<rect width="{W}" height="{H}" fill="#05060A"/>')
    for name, fn in [("fondo_internet", fondo_internet), ("fondo_campus", fondo_campus),
                     ("fondo_campus_noche", lambda: fondo_campus(True)), ("fondo_mansion", fondo_mansion),
                     ("fondo_celda", fondo_celda), ("fondo_isla", fondo_isla)]:
        body, defs = fn()
        add(name, W, H, body, defs)


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
    # ---- short "3 planetas"
    for f in ("lindo", "contento", "malo", "susto"):
        add(f"hd189733b_{f}", 600, 600, hd189733b(f))
    for f in ("neutral", "cool", "sorpresa", "contento"):
        add(f"tres2b_{f}", 600, 600, tres2b(f))
    add("tres2b_brasa", 600, 600, tres2b("contento", brasa=1.0))
    for f in ("neutral", "sorpresa"):
        add(f"jupiter_{f}", 600, 600, jupiter(f))
    add("tierra", 600, 600, tierra())
    for f in ("neutral", "contento", "sorpresa"):
        add(f"cancri_{f}", 600, 600, cancri(f))
    add("cancri_corte", 600, 600, cancri("contento", corte=True))
    for name, col in [("halo_rojo", "#FF4A2A"), ("halo_blanco", "#FFFFFF"), ("halo_celeste", "#9FE8FF"), ("halo_verde", "#8BD06A"),
                      ("halo_amarillo", "#FFE27A"), ("halo_azul", "#6E97FF")]:
        body, defs = halo(col)
        add(name, 800, 800, body, defs)
    add("estrella", 400, 400, estrella_anfitriona())
    add("rayo_luz", 700, 260, rayo_luz(), anchor=(0.0, 0.5))
    for k in "abc":
        add(f"vidrio_{k}", 200, 70, vidrio(k))
        add(f"vidrio_fundido_{k}", 200, 70, vidrio(k, "#FFB13B"))
    add("viento", 360, 60, viento())
    for i in range(11):
        add(f"termometro_{i:02d}", 180, 550, termometro(i / 10), anchor=(0.5, 1.0))
    add("velocimetro", 400, 270, velocimetro(), anchor=(0.5, 220 / 270))
    add("velocimetro_aguja", 180, 60, velocimetro_aguja(), anchor=(30 / 180, 0.5))
    add("carbon", 330, 290, carbon("celoso"))
    add("carbon_sorpresa", 330, 290, carbon("sorpresa"))
    add("brasa", 330, 290, carbon("contento", brasa=True))
    add("diamante", 360, 320, diamante())
    add("reloj", 360, 360, reloj(), anchor=(0.5, 200 / 360))
    add("reloj_aguja", 40, 200, reloj_aguja(), anchor=(0.5, 0.9))
    add("llama", 220, 280, llama(), anchor=(0.5, 1.0))
    add("atomo_c", 220, 220, atomo_c())
    add("flecha_roja", 220, 240, flecha(P["rojo"]))
    add("corazon", 160, 160, corazon())
    add("estrellita", 60, 60, estrellita())
    add("punto_estrella", 20, 20, punto_estrella())
    # ---- short "3 torturas"
    for name, kw in PRISIONERO_VARIANTS.items():
        add(name, 520, 820, prisionero(**kw), anchor=(0.5, 1.0))
    add("prisionero_miedo__blink", 520, 820, prisionero(eyes="closed"), anchor=(0.5, 1.0))
    add("verdugo", 520, 820, verdugo("mira"), anchor=(0.5, 1.0))
    add("verdugo_frente", 520, 820, verdugo("frente"), anchor=(0.5, 1.0))
    add("verdugo_risa", 520, 820, verdugo("risa"), anchor=(0.5, 1.0))
    add("verdugo_sierra", 520, 820, verdugo("mira", sostiene=True), anchor=(0.5, 1.0))
    for f in ("miedo", "asco", "dolor", "nervio"):
        add(f"barcas_{f}", 760, 420, barcas(f))
    add("barcas_miel", 760, 420, barcas("asco", miel=True))
    add("barcas_miel_dolor", 760, 420, barcas("dolor", miel=True))
    add("barcas_podrido1", 760, 420, barcas("podrido1", miel=True))
    add("barcas_podrido2", 760, 420, barcas("podrido2", miel=True))
    for f in ("miedo", "grito"):
        add(f"colgado_v_{f}", 600, 900, colgado_v(f), anchor=(0.5, 60 / 900))
    for m, ax in (("izq", 130), ("der", 470)):
        add(f"colgado_mitad_{m}", 600, 900, colgado_v("muerto", m), anchor=(ax / 600, 60 / 900))
    add("desollado", 520, 820, desollado(), anchor=(0.5, 1.0))
    add("desollado_muerto", 520, 820, desollado(True), anchor=(0.5, 1.0))
    add("jarra_leche", 280, 320, jarra_leche())
    add("tarro_miel", 280, 300, tarro_miel())
    add("mosca", 100, 80, mosca())
    add("olor", 170, 220, olor(), anchor=(0.5, 1.0))
    add("sierra", 900, 200, sierra())
    add("cuchillo", 470, 140, cuchillo())
    add("sombrero_bruja", 300, 270, sombrero_bruja())
    add("corona", 300, 240, corona())
    add("poste", 200, 900, poste(), anchor=(0.5, 1.0))
    add("cuerdas", 360, 420, cuerdas())
    add("cuerda", 40, 700, cuerda_vertical(), anchor=(0.5, 0.0))
    add("microbio_verde", 300, 300, microbio("#8BD06A", "#5FA845"))
    add("microbio_violeta", 300, 300, microbio("#B79CFF", "#8E6EE8", "sorpresa"))
    add("gota", 120, 170, gota())
    add("antorcha", 160, 300, antorcha(), anchor=(0.5, 1.0))
    add("calavera", 260, 240, calavera())
    # ---- short "3 plantas"
    for f in ("contento", "susto"):
        add(f"euforbia_{f}", 360, 320, euforbia(f), anchor=(0.5, 300 / 320))
    add("raices", 500, 520, raices(), anchor=(0.5, 0.0))
    for f in ("neutral", "malo", "contento"):
        add(f"hydnora_rizoma_{f}", 440, 260, hydnora_rizoma(f))
    for i, a in enumerate([0, .35, .7, 1]):
        add(f"hydnora_{i}", 400, 440, hydnora(a, "neutral"), anchor=(0.5, 1.0))
    add("hydnora_malo", 400, 440, hydnora(1, "malo"), anchor=(0.5, 1.0))
    add("hydnora_llena", 400, 440, hydnora(1, "contento", llena=True), anchor=(0.5, 1.0))
    add("hydnora_contento", 400, 440, hydnora(1, "contento"), anchor=(0.5, 1.0))
    add("hydnora_cerrada_malo", 400, 440, hydnora(0, "malo"), anchor=(0.5, 1.0))
    add("hoja", 190, 180, hoja())
    add("tallo", 60, 240, tallo(), anchor=(0.5, 0.0))
    add("burbuja", 44, 44, burbuja())
    add("prohibido", 220, 220, prohibido())
    add("escarabajo", 240, 170, escarabajo(), anchor=(0.5, 1.0))
    add("escarabajo_susto", 240, 170, escarabajo("susto"), anchor=(0.5, 1.0))
    add("bola_estiercol", 160, 160, bola_estiercol(), anchor=(0.5, 1.0))
    add("polen", 24, 24, punto(P["amarillo"]))
    add("nutriente", 24, 24, punto("#8BD06A"))
    for f in ("neutral", "malo", "contento", "sorpresa"):
        add(f"jarra_{f}", 460, 700, jarra(f), anchor=(0.5, 1.0))
    add("jarra_corte", 460, 700, jarra("neutral", corte=True), anchor=(0.5, 1.0))
    add("jarra_corte_malo", 460, 700, jarra("malo", corte=True), anchor=(0.5, 1.0))
    add("botella", 120, 310, botella())
    add("rana", 220, 200, rana())
    add("lagartija", 280, 180, lagartija())
    add("ave", 220, 190, ave())
    add("rata", 250, 160, rata())
    for i, h in enumerate([0, .25, .5, .75, 1]):
        add(f"welwitschia_{i}", 1000, 440, welwitschia(h), anchor=(0.5, 1.0))
    add("welwitschia_rasgada", 1000, 440, welwitschia(1, True, "sorpresa"), anchor=(0.5, 1.0))
    add("welwitschia_monstruo", 1000, 440, welwitschia(1, True, "malo"), anchor=(0.5, 1.0))
    add("welwitschia_contento", 1000, 440, welwitschia(1, True, "contento"), anchor=(0.5, 1.0))
    add("dino", 440, 420, dino(), anchor=(0.5, 1.0))
    add("torta", 320, 320, torta(), anchor=(0.5, 310 / 320))
    add("gota_agua", 120, 170, gota_agua())
    # ---- short "3 aves raras"
    for i, ap in enumerate([0, .5, 1]):
        add(f"picozapato_{i}", 600, 900, picozapato("abierto", ap), anchor=(282 / 600, 1.0))
    add("picozapato_0__blink", 600, 900, picozapato("cerrado"), anchor=(282 / 600, 1.0))
    for mo in ("rama", "ojos", "boca", "canto"):
        add(f"urutau_{mo}", 360, 760, urutau(mo), anchor=(0.5, 1.0))
    for i, mi in enumerate([-1, 0, 1]):
        add(f"urutau_ojo_{i}", 700, 460, urutau_ojo("ranura", mi))
    add("urutau_ojo_abierto", 700, 460, urutau_ojo("abierto"))
    add("hoacin", 520, 640, hoacin(), anchor=(0.5, 590 / 640))
    add("hoacin__blink", 520, 640, hoacin("cerrado"), anchor=(0.5, 590 / 640))
    for i in (0, 1):
        add(f"hoacin_pichon_{i}", 320, 320, hoacin_pichon(i))
    add("rama", 900, 260, rama())
    add("pez_pulmonado", 340, 120, pez_pulmonado())
    add("cocodrilo_bebe", 290, 160, cocodrilo_bebe())
    add("zueco", 320, 170, zueco())
    add("vaca", 340, 270, vaca(), anchor=(0.5, 1.0))
    add("jaguar", 440, 280, jaguar(), anchor=(0.5, 1.0))
    add("jaguar_asco", 440, 280, jaguar("asco"), anchor=(0.5, 1.0))
    add("polilla", 90, 70, polilla())
    body, defs = luciernaga()
    add("luciernaga", 60, 60, body, defs)
    add("nota_musical", 90, 110, nota_musical())
    add("cursor_mano", 110, 150, cursor_mano(), anchor=(38 / 110, 8 / 150))
    add("campana", 180, 210, campana())
    add("anillo", 200, 200, anillo())
    add("tronco_roto", 200, 420, tronco_roto(), anchor=(0.5, 1.0))
    for name, fn in [("capa_rayos", capa_rayos), ("capa_vineta", capa_vineta)]:
        body, defs = fn()
        add(name, W, H, body, defs)
    add("capa_hojas_frente", W, H, capa_hojas_frente())
    add("capa_papiros_frente", W, H, capa_papiros_frente())
    body, defs = niebla()
    add("niebla", 1400, 400, body, defs)
    add("cortina_hojas", 1500, 2100, cortina_hojas())
    add("pajarito", 60, 34, pajarito())
    add("rayitas", 300, 300, rayitas())
    # ---- short "3 animales del océano profundo"
    for pose in ("quieto", "baila_a", "baila_b", "come"):
        add(f"cangrejo_yeti_{pose}", 700, 420, cangrejo_yeti(pose), anchor=(0.5, 1.0))
    add("cangrejo_yeti_bacterias", 700, 420, cangrejo_yeti("quieto", bacterias=True), anchor=(0.5, 1.0))
    add("cangrejo_yeti_come_bacterias", 700, 420, cangrejo_yeti("come", bacterias=True), anchor=(0.5, 1.0))
    add("calamar_vampiro", 520, 640, calamar_vampiro())
    add("calamar_vampiro_brilla", 520, 640, calamar_vampiro(brilla=True))
    add("calamar_vampiro_pina", 520, 640, calamar_vampiro("pina"))
    add("pez_vibora", 560, 260, pez_vibora())
    add("pez_vibora_mareado", 560, 260, pez_vibora("mareado"))
    add("rape_hembra", 700, 600, rape_hembra())
    add("rape_hembra_feliz", 700, 600, rape_hembra("feliz"))
    for e in range(5):
        add(f"rape_macho_{e}", 180, 100, rape_macho(e))
    caras = {"neutral": dict(), "sorpresa": dict(eyes="wide", brows="up", mouth_kind="o"),
             "miedo": dict(eyes="wide", brows="sad", mouth_kind="nervio"), "pensando": dict(look=(1, -1), brows="up", mouth_kind="flat"),
             "contento": dict(eyes="happy", brows="happy", mouth_kind="open_smile"),
             "asco": dict(eyes="squint", brows="asco", mouth_kind="bleh")}
    for nombre_cara, kw in caras.items():
        add(f"batiscafo_{nombre_cara}", 440, 420, batiscafo(kw))
    add("batiscafo_neutral__blink", 440, 420, batiscafo(dict(eyes="closed")))
    add("tinta", 320, 260, tinta())
    for name, fn in [("destello", destello), ("nieve_marina", nieve_marina)]:
        body, defs = fn()
        add(name, 80 if name == "destello" else 20, 80 if name == "destello" else 20, body, defs)
    add("humo_toxico", 80, 80, humo_toxico())
    add("platillo", 260, 140, platillo())
    for k in (1, 2, 3):
        add(f"globo_comentario_{k}", 370, 240, globo_comentario(k))
    add("gusano_tubo", 160, 300, gusano_tubo(), anchor=(0.5, 1.0))
    add("cortina_burbujas", 1500, 2100, cortina_burbujas())
    for name, fn in [("fondo_liso", fondo_liso), ("fondo_burst", fondo_burst), ("fondo_piel", fondo_piel),
                     ("fondo_abismo", fondo_abismo), ("fondo_lecho", fondo_lecho),
                     ("fondo_burst_verde", fondo_burst_verde), ("fondo_subsuelo", fondo_subsuelo),
                     ("fondo_humedal", fondo_humedal), ("fondo_bosque_dia", lambda: fondo_bosque(False)),
                     ("fondo_bosque_noche", lambda: fondo_bosque(True)), ("fondo_rio", fondo_rio),
                     ("fondo_sabana", fondo_sabana), ("fondo_selva", fondo_selva), ("fondo_desierto", fondo_desierto),
                     ("fondo_mazmorra", fondo_mazmorra), ("fondo_pantano", fondo_pantano),
                     ("fondo_exterior", fondo_exterior), ("fondo_cabeza", fondo_cabeza),
                     ("fondo_espacio", fondo_espacio_azul), ("fondo_espacio_rojo", fondo_espacio_rojo),
                     ("fondo_espacio_violeta", fondo_espacio_violeta)]:
        body, defs = fn()
        add(name, W, H, body, defs)
    add("dormitorio", W, H, dormitorio(False))
    add("dormitorio_noche", W, H, dormitorio(True))
    add("blanco", W, H, f'<rect width="{W}" height="{H}" fill="#fff"/>')

    build_memes()
    os.makedirs(os.path.join(OUT, "svg"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "png"), exist_ok=True)
    # capas de primer plano desenfocadas (profundidad de campo): nombre -> radio en px
    DESENFOQUE = {"capa_hojas_frente": 9, "capa_papiros_frente": 7}
    for name, s in ASSETS.items():
        with open(os.path.join(OUT, "svg", name + ".svg"), "w") as f:
            f.write(s)
        scale = 1.0 if name.startswith(("fondo", "dormitorio", "blanco", "capa")) else RS
        png = os.path.join(OUT, "png", name + ".png")
        cairosvg.svg2png(bytestring=s.encode(), write_to=png, scale=scale)
        if name in DESENFOQUE:
            from PIL import Image, ImageFilter
            Image.open(png).filter(ImageFilter.GaussianBlur(DESENFOQUE[name])).save(png)
    META["rs"] = RS
    with open(os.path.join(OUT, "meta.json"), "w") as f:
        json.dump(META, f, indent=1)
    print(f"{len(ASSETS)} recursos generados")


if __name__ == "__main__":
    build()

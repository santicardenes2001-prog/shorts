"""Motor de animación: escenas.json -> short vertical en MP4.

    python motor.py proyectos/3cosas/escenas.json            # render completo
    python motor.py proyectos/3cosas/escenas.json --fotos 1.2,5,9.5   # fotogramas sueltos (PNG)

Las acciones se anclan a palabras del guion ("b3:gravedad" = cuando se dice
"gravedad" en el bloque 3). Sin audio, los tiempos se estiman por largo de
palabra; con una grabación + palabras.json (Whisper) se usan los tiempos reales.

Extras (todo opcional desde el JSON):
  - elemento "particulas": lluvia/viento/estrellas con semilla fija (clase Particles).
  - idle "latido" (la opacidad late: halos, brasas) y "titila" (estrellas).
  - fx_in/fx_out "suave" (carteles prolijos) y "sombra" en los textos con caja.
  - "pausas" (silencio en la voz para lucir un efecto) y "ambiente" por escena (selva, pantano, noche, bosque).
  - más sonidos: matraca, llanto, muu, aleteo, pio, click.
  - "loops" con ventana de tiempo (from/to) para animar cuadro a cuadro solo en un momento.
  - escena "camara": zoom/paneo con keys y "temblor" (clase Camera).
  - "sigue": {"id", "punto"} pega un elemento a un punto del dibujo de otro (luz con su fuente).
  - sonidos: viento, cristal, brillo, tictac, zumbido, mosca, sierra, filo, golpe, glup.
"""
import argparse
import difflib
import functools
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(ROOT, "kit")
FONT = os.path.join(ROOT, "fonts", "LilitaOne-Regular.ttf")
W, H, FPS = 1080, 1920, 30
INK = "#24201F"
SR = 44100

META = json.load(open(os.path.join(KIT, "meta.json")))
RS = META["rs"]


# ================================================================ utilidades
def norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)


NUM = {"uno": "1", "un": "1", "una": "1", "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5",
       "seis": "6", "siete": "7", "ocho": "8", "nueve": "9", "diez": "10"}


def canon(w):
    """Forma canónica para alinear guion y transcripción ("tres" == "3")."""
    n = norm(w)
    return NUM.get(n, n)


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def ease(name, p):
    p = clamp(p)
    if name == "linear":
        return p
    if name == "out":
        return 1 - (1 - p) ** 3
    if name == "in":
        return p ** 3
    if name == "inout":
        return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
    if name == "back":
        c = 1.70158
        return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2
    if name == "bounce":
        n, d = 7.5625, 2.75
        if p < 1 / d:
            return n * p * p
        if p < 2 / d:
            p -= 1.5 / d
            return n * p * p + .75
        if p < 2.5 / d:
            p -= 2.25 / d
            return n * p * p + .9375
        p -= 2.625 / d
        return n * p * p + .984375
    raise ValueError(name)


def phase_of(key):
    return int(hashlib.md5(key.encode()).hexdigest()[:6], 16) / 0xFFFFFF * 2 * math.pi


# ================================================================ tiempos
def word_duration(tok):
    letters = norm(tok)
    n = len(letters)
    if letters.isdigit():
        n = 4
    return 0.09 + 0.052 * max(n, 1)


def estimate_times(beats, speed=1.0, lead=0.35):
    t = lead
    out = []
    for b in beats:
        words = []
        for tok in b["texto"].split():
            d = word_duration(tok) / speed
            words.append({"w": tok, "n": norm(tok), "start": t, "end": t + d})
            t += d + 0.03 / speed
            if tok.endswith(","):
                t += 0.18 / speed
            elif tok[-1] in ".!?:;":
                t += 0.32 / speed
        t += 0.12 / speed
        out.append(words)
    return out


def align_times(beats, whisper_words):
    """Asigna a cada palabra del guion el tiempo real reconocido por Whisper."""
    est = estimate_times(beats)
    flat = [w for bw in est for w in bw]
    script_n = [canon(w["w"]) for w in flat]
    rec_n = [canon(w["word"]) for w in whisper_words]
    sm = difflib.SequenceMatcher(a=script_n, b=rec_n, autojunk=False)
    known = {}
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            # iguales, o sustituciones 1 a 1 (el reconocedor escribió mal la palabra)
            for k in range(i2 - i1):
                ww = whisper_words[j1 + k]
                known[i1 + k] = (ww["start"], ww["end"])
        elif op == "replace":
            # distinta cantidad de palabras: repartir el tramo reconocido en proporción
            t0, t1 = whisper_words[j1]["start"], whisper_words[j2 - 1]["end"]
            lens = [max(1, len(script_n[i])) for i in range(i1, i2)]
            tot, acc = sum(lens), 0
            for k, i in enumerate(range(i1, i2)):
                s0 = t0 + (t1 - t0) * acc / tot
                acc += lens[k]
                known[i] = (s0, t0 + (t1 - t0) * acc / tot)
    # interpolar las que no matchearon
    idx = sorted(known)
    faltan = [flat[i]["w"] for i in range(len(flat)) if i not in known]
    if faltan:
        print(f"aviso: {len(faltan)} palabras del guion no se reconocieron en el audio "
              f"(tiempo interpolado): {' '.join(faltan)}")
    for i, w in enumerate(flat):
        if i in known:
            w["start"], w["end"] = known[i]
            continue
        prev = max([j for j in idx if j < i], default=None)
        nxt = min([j for j in idx if j > i], default=None)
        if prev is not None and nxt is not None:
            f = (i - prev) / (nxt - prev)
            s0, s1 = known[prev][1], known[nxt][0]
            w["start"] = s0 + (s1 - s0) * f
        elif prev is not None:
            w["start"] = known[prev][1] + 0.3 * (i - prev)
        elif nxt is not None:
            w["start"] = max(0, known[nxt][0] - 0.3 * (nxt - i))
        w["end"] = w["start"] + 0.25
    return est


# ================================================================ referencias de tiempo
REF = re.compile(r"^(?:b(\d+)(?::([^+>]+?))?(>)?|e(\d+)(>)?|esc(>)?|fin)?\s*([+-]\s*\d+(?:\.\d+)?)?$")


class Timeline:
    def __init__(self, doc, words):
        self.words = words
        self.doc = doc
        n = len(doc["escenas"])
        self.scene_start = []
        for i, sc in enumerate(doc["escenas"]):
            if i == 0:
                self.scene_start.append(0.0)
            else:
                b = sc["beats"][0]
                self.scene_start.append(words[b][0]["start"] - sc.get("antes", 0.12))
        last = words[-1][-1]["end"]
        self.total = last + doc.get("cola", 1.3)
        self.scene_end = self.scene_start[1:] + [self.total]

    def resolve(self, ref, scene=None):
        if isinstance(ref, (int, float)):
            return float(ref)
        m = REF.match(ref.strip())
        if not m:
            raise ValueError(f"referencia de tiempo inválida: {ref!r}")
        bi, word, bend, ei, eend, escend, off = m.groups()
        off = float(off.replace(" ", "")) if off else 0.0
        if bi is not None:
            ws = self.words[int(bi)]
            if word:
                target = norm(word)
                cand = [w for w in ws if w["n"] == target] or [w for w in ws if w["n"].startswith(target)]
                if not cand:
                    raise ValueError(f"no encuentro la palabra {word!r} en el bloque {bi}: "
                                     + " ".join(w["w"] for w in ws))
                w = cand[0]
                return (w["end"] if bend else w["start"]) + off
            return (ws[-1]["end"] if bend else ws[0]["start"]) + off
        if ei is not None:
            k = int(ei)
            return (self.scene_end[k] if eend else self.scene_start[k]) + off
        if ref.strip().startswith("fin"):
            return self.total + off
        # esc / esc>
        if scene is None:
            raise ValueError("'esc' solo vale dentro de una escena")
        return (self.scene_end[scene] if escend else self.scene_start[scene]) + off


# ================================================================ imágenes
@functools.lru_cache(maxsize=None)
def load_asset(name):
    path = os.path.join(KIT, "png", name + ".png")
    if not os.path.exists(path):
        raise FileNotFoundError(f"falta el recurso {name!r} en el kit")
    im = Image.open(path).convert("RGBA")
    res = 1.0 if im.size == (W, H) else RS
    return im, res


def asset_exists(name):
    return os.path.exists(os.path.join(KIT, "png", name + ".png"))


def rounded_box(draw, box, r, fill, outline, width):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


@functools.lru_cache(maxsize=None)
def render_text(spec_json):
    sp = json.loads(spec_json)
    k = RS
    size = sp.get("size", 64)
    font = ImageFont.truetype(sp.get("font", FONT), int(size * k))
    lines = sp["t"].split("\n")
    stroke = int(sp.get("stroke", 0 if sp.get("box") else 10) * k)
    asc, desc = font.getmetrics()
    lh = (asc + desc) * sp.get("interlineado", 0.92)
    widths = [font.getbbox(l, stroke_width=stroke)[2] - font.getbbox(l, stroke_width=stroke)[0] for l in lines]
    padx, pady = [v * k for v in sp.get("pad", [34, 18] if sp.get("box") else [12, 8])]
    bw = max(widths) + 2 * padx
    bh = lh * len(lines) + 2 * pady
    if sp.get("circle"):
        bw = bh = max(bw, bh)
    sh = int(sp.get("sombra", 10) * k) if sp.get("box") and sp.get("shadow", True) else 0
    im = Image.new("RGBA", (int(bw + 8 * k), int(bh + 8 * k + sh)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = 4 * k, 4 * k
    if sp.get("box"):
        bs = int(sp.get("box_stroke", 6) * k)
        r = bh / 2 if sp.get("circle") else sp.get("radius", 26) * k
        if sh:
            rounded_box(d, [ox, oy + sh, ox + bw, oy + bh + sh], r, INK, None, 0)
        if sp.get("circle"):
            d.ellipse([ox, oy, ox + bw, oy + bh], fill=sp["box"], outline=INK, width=bs)
        else:
            rounded_box(d, [ox, oy, ox + bw, oy + bh], r, sp["box"], INK, bs)
    for i, l in enumerate(lines):
        cy = oy + pady + lh * (i + 0.5) + sp.get("ajuste_y", 3) * k
        d.text((ox + bw / 2, cy), l, font=font, fill=sp.get("color", "#FFFFFF"), anchor="mm",
               stroke_width=stroke, stroke_fill=sp.get("stroke_color", INK))
    return im


def get_image(el_asset):
    """el_asset: nombre de recurso o dict de texto."""
    if isinstance(el_asset, dict):
        return render_text(json.dumps(el_asset, sort_keys=True)), RS
    return load_asset(el_asset)


@functools.lru_cache(maxsize=512)
def scaled(key, w, h, flip):
    src = _IMG_REG[key]
    im = src.resize((w, h), Image.BICUBIC)
    return ImageOps.mirror(im) if flip else im


_IMG_REG = {}


def img_key(el_asset):
    k = el_asset if isinstance(el_asset, str) else "txt:" + json.dumps(el_asset, sort_keys=True)
    if k not in _IMG_REG:
        _IMG_REG[k] = get_image(el_asset)[0]
    return k


# ================================================================ elementos
FX_DUR = {"pop": .35, "grow": .35, "jump": .45, "drop": .6, "fade": .3, "wipe": .8, "suave": .4,
          "slide_up": .45, "slide_down": .45, "slide_left": .45, "slide_right": .45, "none": 0}
FX_SFX = {"pop": "pop", "grow": "pop", "jump": "pop", "drop": "pop", "suave": "pop", "slide_up": "whoosh",
          "slide_down": "whoosh", "slide_left": "whoosh", "slide_right": "whoosh", "wipe": "whoosh_suave"}


class Element:
    def __init__(self, spec, tl, scene=None, idx=0):
        self.sp = spec
        self.tl = tl
        R = lambda r: tl.resolve(r, scene)
        self.tin = R(spec.get("in", "esc" if scene is not None else 0))
        self.tout = R(spec.get("out", "esc>" if scene is not None else "fin"))
        self.fx_in = spec.get("fx_in", "none")
        self.fx_out = spec.get("fx_out", "none")
        self.dur_in = spec.get("dur_in", FX_DUR[self.fx_in])
        self.dur_out = spec.get("dur_out", .25 if self.fx_out != "none" else 0)
        self.asset = spec.get("a") or spec.get("texto")
        if isinstance(self.asset, dict) and "estilo" in self.asset:
            merged = dict(tl.doc.get("estilos", {})[self.asset["estilo"]])
            merged.update({k: v for k, v in self.asset.items() if k != "estilo"})
            self.asset = merged
        self.swaps = sorted([dict(s, t=R(s["at"])) for s in spec.get("swaps", [])], key=lambda s: s["t"])
        self.keys = sorted([dict(k, t=R(k["at"])) for k in spec.get("keys", [])], key=lambda k: k["t"])
        for k in self.keys:   # "hasta": ref = el movimiento dura hasta ese momento (en vez de "dur")
            if "hasta" in k:
                k["dur"] = max(R(k["hasta"]) - k["t"], .001)
        # "loops": [{"frames": [...], "fps": 18, "from": ref, "to": ref}] = secuencias en bucle solo en esa ventana
        self.loops = [dict(lp, t0=R(lp["from"]), t1=R(lp["to"])) for lp in spec.get("loops", [])]
        self.seq = None
        if "seq" in spec:
            sq = spec["seq"]
            self.seq = dict(sq, t=R(sq["at"]))
        self.idle = []
        for i in (spec.get("idle") or []) if isinstance(spec.get("idle"), list) else [spec.get("idle")] if spec.get("idle") else []:
            if isinstance(i, str):
                self.idle.append({"fx": i, "t0": -1e9, "t1": 1e9})
            else:
                self.idle.append(dict(i, t0=R(i["from"]) if "from" in i else -1e9, t1=R(i["to"]) if "to" in i else 1e9))
        self.z = spec.get("z", 0) + idx * 1e-3
        # "fase" fija la fase de los idle: el mismo personaje queda sincronizado entre escenas
        self.ph = float(spec["fase"]) if "fase" in spec else phase_of(json.dumps(spec, sort_keys=True))
        self.blink = spec.get("blink", False)
        # "sigue": {"id": "rape", "punto": [640, 70]} = pegado a ese punto del dibujo (coordenadas del recurso)
        # del elemento con ese "id": acompaña su posición, idle, inclinación y escala (luces con su fuente).
        # Sin "punto" conserva la distancia que ya tenía con el líder.
        self.sigue = spec.get("sigue")
        self.lider = None

    # ------------------------------------------------------------ sonidos
    def sfx_events(self):
        ev = []
        s = self.sp.get("sfx", FX_SFX.get(self.fx_in))
        if s and s != "none":
            ev.append((self.tin, s, self.sp.get("vol", 1.0)))
        for sw in self.swaps:
            if sw.get("fx") == "punch" and sw.get("sfx") != "none":
                ev.append((sw["t"], sw.get("sfx", "boing"), .7))
        for k in self.keys:
            if k.get("sfx"):
                ev.append((k["t"], k["sfx"], 1.0))
        return ev

    def active(self, t):
        return self.tin <= t < self.tout

    def _seguir(self, st, t):
        L = self.lider
        ls, lsp = L.state(t), L.sp
        k = ls["s"] / lsp.get("s", 1.0)
        if "punto" in self.sigue:
            # punto en coordenadas del dibujo del líder: se escala y se gira con él
            src = _IMG_REG[img_key(ls["asset"])]
            res = 1.0 if src.size == (W, H) else RS
            ax, ay = anchor_of(lsp, ls["asset"])
            px, py = self.sigue["punto"]
            dx = (px - ax * src.width / res) * ls["s"] * ls["sx"]
            dy = (py - ay * src.height / res) * ls["s"] * ls["sy"]
            if lsp.get("flip"):
                dx = -dx
            a = math.radians(ls["r"])
        else:
            # sin "punto": conserva la distancia que ya tenía con el líder (en reposo)
            dx = (self.sp.get("x", W / 2) - lsp.get("x", W / 2)) * k
            dy = (self.sp.get("y", H / 2) - lsp.get("y", H / 2)) * k
            a = math.radians(ls["r"] - lsp.get("r", 0.0))
        # lo propio del seguidor (keys, idle, entrada) se suma como desplazamiento respecto de su x/y
        st["x"] += ls["x"] + dx * math.cos(a) - dy * math.sin(a) - self.sp.get("x", W / 2)
        st["y"] += ls["y"] + dx * math.sin(a) + dy * math.cos(a) - self.sp.get("y", H / 2)
        st["r"] += ls["r"] - lsp.get("r", 0.0)
        st["s"] *= k

    # ------------------------------------------------------------ estado en t
    def state(self, t):
        sp = self.sp
        st = dict(x=sp.get("x", W / 2), y=sp.get("y", H / 2), s=sp.get("s", 1.0), sx=sp.get("sx", 1.0),
                  sy=sp.get("sy", 1.0), r=sp.get("r", 0.0), alpha=sp.get("alpha", 1.0), crop=1.0)
        asset = self.asset
        # keyframes
        for k in self.keys:
            if t < k["t"]:
                break
            p = ease(k.get("ease", "inout"), (t - k["t"]) / max(k.get("dur", .5), 1e-6))
            for prop in ("x", "y", "s", "sx", "sy", "r", "alpha"):
                if prop in k:
                    st[prop] = st[prop] + (k[prop] - st[prop]) * p
        # cambios de dibujo
        punch = None
        for sw in self.swaps:
            if t >= sw["t"]:
                asset = sw["a"]
                if sw.get("fx") == "punch":
                    punch = t - sw["t"]
        if self.seq:
            sq = self.seq
            frames = sq["frames"]
            p = ease(sq.get("ease", "inout"), (t - sq["t"]) / max(sq.get("dur", 1), 1e-6))
            asset = frames[int(round(p * (len(frames) - 1)))]
        if "loop" in sp:
            lp = sp["loop"]
            asset = lp["frames"][int((t - self.tin) * lp.get("fps", 6)) % len(lp["frames"])]
        for lp in self.loops:
            if lp["t0"] <= t < lp["t1"]:
                asset = lp["frames"][int((t - lp["t0"]) * lp.get("fps", 6)) % len(lp["frames"])]
        if punch is not None and punch < .3:
            q = punch / .3
            st["sx"] *= 1 + .12 * math.sin(math.pi * q) * (1 - q)
            st["sy"] *= 1 - .10 * math.sin(math.pi * q) * (1 - q)
        # entrada
        fx = self.fx_in
        if fx != "none" and t < self.tin + self.dur_in:
            p = (t - self.tin) / self.dur_in
            if fx == "pop":
                st["s"] *= max(ease("back", p), 0.001)
                st["alpha"] *= clamp(p * 4)
            elif fx == "grow":
                st["s"] *= max(ease("out", p), 0.001)
            elif fx == "jump":
                st["y"] += (1 - ease("back", p)) * 260
                st["sy"] *= 1 + .15 * math.sin(math.pi * p)
                st["alpha"] *= clamp(p * 5)
            elif fx == "drop":
                st["y"] -= (1 - ease("bounce", p)) * 700
            elif fx == "fade":
                st["alpha"] *= p
            elif fx == "suave":
                # entrada prolija para carteles: aparece, crece desde 85 % y sube un poco
                e = ease("out", p)
                st["alpha"] *= clamp(p * 2.2)
                st["s"] *= .85 + .15 * e
                st["y"] += (1 - e) * 36
            elif fx == "wipe":
                st["crop"] = max(ease("inout", p), 0.001)
            elif fx == "slide_up":
                st["y"] += (1 - ease("out", p)) * 1000
            elif fx == "slide_down":
                st["y"] -= (1 - ease("out", p)) * 1000
            elif fx == "slide_left":
                st["x"] += (1 - ease("out", p)) * 1100
            elif fx == "slide_right":
                st["x"] -= (1 - ease("out", p)) * 1100
        # salida
        fo = self.fx_out
        if fo != "none" and t > self.tout - self.dur_out:
            q = clamp((t - (self.tout - self.dur_out)) / self.dur_out)
            if fo == "pop":
                st["s"] *= max(1 + .15 * math.sin(math.pi * q) - q, 0.001)
            elif fo == "fade":
                st["alpha"] *= 1 - q
            elif fo == "suave":
                st["alpha"] *= 1 - ease("in", q)
                st["s"] *= 1 - .08 * q
                st["y"] -= 24 * ease("in", q)
            elif fo == "slide_down":
                st["y"] += ease("in", q) * 1000
            elif fo == "slide_up":
                st["y"] -= ease("in", q) * 1000
            elif fo == "slide_left":
                st["x"] -= ease("in", q) * 1100
            elif fo == "slide_right":
                st["x"] += ease("in", q) * 1100
        # movimientos en loop
        ph = self.ph
        for idl in self.idle:
            if not (idl["t0"] <= t < idl["t1"]):
                continue
            f = idl["fx"]
            a = idl.get("fuerza", 1.0)
            if f == "breathe":
                v = math.sin(2 * math.pi * .8 * t + ph)
                st["sy"] *= 1 + .014 * a * v
                st["sx"] *= 1 - .007 * a * v
            elif f == "bob":
                st["y"] += 9 * a * math.sin(2 * math.pi * 1.1 * t + ph)
            elif f == "float":
                st["y"] += 16 * a * math.sin(2 * math.pi * .55 * t + ph)
                st["r"] += 2 * a * math.sin(2 * math.pi * .4 * t + ph)
            elif f == "wiggle":
                st["r"] += 7 * a * math.sin(2 * math.pi * 1.6 * t + ph)
            elif f == "sway":
                st["r"] += 3 * a * math.sin(2 * math.pi * .5 * t + ph)
            elif f == "shake":
                st["x"] += 7 * a * math.sin(2 * math.pi * 14 * t)
                st["y"] += 5 * a * math.sin(2 * math.pi * 11 * t + 1)
            elif f == "spin":
                st["r"] += idl.get("vel", 60) * (t - max(self.tin, idl["t0"]))
            elif f == "pulse":
                st["s"] *= 1 + .07 * a * math.sin(2 * math.pi * 1.4 * t + ph)
            elif f == "work":
                st["y"] -= 12 * a * abs(math.sin(2 * math.pi * 2.2 * t + ph))
            elif f == "chew":
                v = math.sin(2 * math.pi * 3 * t + ph)
                st["sy"] *= 1 + .035 * a * v
                st["sx"] *= 1 - .02 * a * v
            elif f == "latido":
                # brillo que late: la opacidad sube y baja (halos, brasas)
                v = .5 + .5 * math.sin(2 * math.pi * idl.get("vel", 1.2) * t + ph)
                st["alpha"] *= 1 - .5 * min(a, 2) * (1 - v)
            elif f == "vaiven":
                # ida y vuelta horizontal (serrucho, péndulo); fuerza 1 = ±40 px
                st["x"] += 40 * a * math.sin(2 * math.pi * idl.get("vel", 2.5) * t + ph)
            elif f == "titila":
                # parpadeo irregular de estrella: suma de dos senos rápidos
                v = math.sin(2 * math.pi * 2.3 * t + ph) * math.sin(2 * math.pi * 3.7 * t + 2 * ph)
                st["alpha"] *= clamp(1 - .6 * a * (.5 + .5 * v))
            else:
                raise ValueError(f"idle desconocido: {f}")
        if self.lider is not None:
            self._seguir(st, t)
        # parpadeo
        if self.blink and isinstance(asset, str) and asset_exists(asset + "__blink"):
            per = 3.3 + (ph % 1.0)
            if ((t + ph) % per) < .12:
                asset = asset + "__blink"
        st["asset"] = asset
        return st


class Particles(Element):
    """Muchas copias de uno o varios recursos con posición, velocidad, escala, rotación
    y giro aleatorios (semilla fija). Se mueven en línea recta y reaparecen del otro
    lado de la zona, así que sirven para lluvias, viento, nieve o estrellas que titilan.

    "particulas": {"a": ["vidrio_a", "vidrio_b"], "n": 40, "semilla": 1,
                   "zona": [x0, y0, x1, y1], "vx": [900, 1400], "vy": [-40, 60],
                   "s": [.5, 1], "r": [-8, 8], "giro": [0, 0], "alpha": [.7, 1],
                   "titila": 0, "orientar": false, "ondula": [amplitud_px, vueltas_por_seg]}
    "ondula" suma un vaivén circular propio de cada partícula (moscas que zumban).
    "desvanece": true = cada partícula se ve apenas sale de la fuente y se apaga de a poco a lo largo de su
    recorrido por la zona (humo o burbujas que salen de una fuente, sin que se vea dónde reaparecen); "crece": 2 = al final del
    recorrido mide el doble (el gas se expande al subir).
    "continuo": true = se mueven con el tiempo absoluto del video: el mismo grupo (misma semilla) sigue
    igual de una escena a la siguiente en el mismo lugar, sin saltar en el corte.
    in/out, fx_in/fx_out (fade, pop...), x/y/s/alpha y keys afectan a todo el grupo
    (x/y desplazan respecto de la posición de reposo W/2, H/2).
    """

    def __init__(self, spec, tl, scene=None, idx=0):
        pc = spec["particulas"]
        names = pc["a"] if isinstance(pc["a"], list) else [pc["a"]]
        super().__init__(dict(spec, a=names[0]), tl, scene, idx)
        self.assets_extra = names
        rnd = np.random.default_rng(pc.get("semilla", 1))
        n = pc.get("n", 30)
        self.zona = pc.get("zona", [0, 0, W, H])
        x0, y0, x1, y1 = self.zona
        U = lambda key, d: rnd.uniform(*pc.get(key, d), size=n)
        self.p = dict(x=rnd.uniform(x0, x1, n), y=rnd.uniform(y0, y1, n), vx=U("vx", [0, 0]), vy=U("vy", [0, 0]),
                      s=U("s", [1, 1]), r=U("r", [0, 0]), giro=U("giro", [0, 0]), alpha=U("alpha", [1, 1]),
                      ph=rnd.uniform(0, 2 * math.pi, n), k=rnd.integers(0, len(names), n))
        self.names = names
        self.titila = pc.get("titila", 0)
        self.orientar = pc.get("orientar", False)
        self.ondula = pc.get("ondula")
        self.desvanece = pc.get("desvanece", False)
        if self.desvanece:   # chorro parejo desde la fuente: repartidas a lo largo del recorrido, sin huecos
            orden = rnd.permutation(n)
            if abs(np.mean(self.p["vy"])) >= abs(np.mean(self.p["vx"])):
                self.p["y"] = y0 + (orden + rnd.uniform(.3, .7, n)) / n * (y1 - y0)
            else:
                self.p["x"] = x0 + (orden + rnd.uniform(.3, .7, n)) / n * (x1 - x0)
        self.crece = pc.get("crece", 1.0)
        self.continuo = pc.get("continuo", False)

    def draw(self, frame, t):
        base = Element.state(self, t)
        dx, dy = base["x"] - self.sp.get("x", W / 2), base["y"] - self.sp.get("y", H / 2)
        x0, y0, x1, y1 = self.zona
        zw, zh = x1 - x0, y1 - y0
        dt = t if self.continuo else t - self.tin
        p = self.p
        for i in range(len(p["x"])):
            ux = (p["x"][i] - x0 + p["vx"][i] * dt) % zw
            uy = (p["y"][i] - y0 + p["vy"][i] * dt) % zh
            x, y = x0 + ux + dx, y0 + uy + dy
            # avance a lo largo de la zona (0 = donde nace, 1 = donde termina), según el eje del movimiento
            if abs(p["vy"][i]) >= abs(p["vx"][i]):
                u = uy / zh if p["vy"][i] >= 0 else 1 - uy / zh
            else:
                u = ux / zw if p["vx"][i] >= 0 else 1 - ux / zw
            r = p["r"][i] + p["giro"][i] * dt
            if self.ondula:
                amp, f = self.ondula
                w = 2 * math.pi * f * (1 + .3 * math.sin(p["ph"][i] * 3))
                x += amp * math.sin(w * t + p["ph"][i])
                y += amp * .7 * math.sin(1.3 * w * t + 2 * p["ph"][i])
            if self.orientar:
                r += math.degrees(math.atan2(p["vy"][i], p["vx"][i]))
            a = base["alpha"] * p["alpha"][i]
            if self.desvanece:
                # ya se ve al salir de la fuente (entra en el primer 6 % del recorrido) y se apaga al final
                a *= min(1.0, u / .06) * (1 - u) ** .8
            if self.titila:
                a *= clamp(1 - self.titila * (.5 + .5 * math.sin(2 * math.pi * 2.6 * t + p["ph"][i])))
            st = dict(x=x, y=y, s=base["s"] * p["s"][i] * (1 + (self.crece - 1) * u), sx=1.0, sy=1.0, r=round(r), alpha=a, crop=1.0,
                      asset=self.names[p["k"][i]])
            draw_element(frame, self, st)


# ================================================================ cámara
class Camera:
    """Zoom/paneo de la escena entera (fondo + elementos; no afecta persistentes ni subtítulos).

    "camara": {"keys": [{"at": "b3:vientos", "dur": .8, "zoom": 1.2, "x": 540, "y": 800, "ease": "inout"}],
               "temblor": [{"from": "b5", "to": "b5>", "fuerza": 1}]}
    x/y = punto de la escena que queda en el centro del encuadre.
    """

    def __init__(self, spec, tl, scene):
        R = lambda r: tl.resolve(r, scene)
        self.keys = sorted([dict(k, t=R(k["at"])) for k in spec.get("keys", [])], key=lambda k: k["t"])
        for k in self.keys:   # "hasta": ref = el movimiento dura hasta ese momento (en vez de "dur")
            if "hasta" in k:
                k["dur"] = max(R(k["hasta"]) - k["t"], .001)
        self.shake = [dict(s, t0=R(s["from"]), t1=R(s["to"])) for s in spec.get("temblor", [])]

    def state(self, t):
        st = dict(zoom=1.0, x=W / 2, y=H / 2)
        for k in self.keys:
            if t < k["t"]:
                break
            p = ease(k.get("ease", "inout"), (t - k["t"]) / max(k.get("dur", .6), 1e-6))
            for prop in ("zoom", "x", "y"):
                if prop in k:
                    st[prop] += (k[prop] - st[prop]) * p
        for sh in self.shake:
            if sh["t0"] <= t < sh["t1"]:
                a = sh.get("fuerza", 1.0)
                st["x"] += 9 * a * math.sin(2 * math.pi * 13 * t) + 5 * a * math.sin(2 * math.pi * 7 * t)
                st["y"] += 7 * a * math.sin(2 * math.pi * 11 * t + 1)
                st["zoom"] = max(st["zoom"], 1.03)   # un poco de margen para que no se vean bordes
        return st

    def apply(self, frame, t):
        st = self.state(t)
        z = max(st["zoom"], 1.0)
        if z == 1.0 and st["x"] == W / 2 and st["y"] == H / 2:
            return frame
        cw, ch = W / z, H / z
        cx = clamp(st["x"], cw / 2, W - cw / 2)
        cy = clamp(st["y"], ch / 2, H - ch / 2)
        box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
        return frame.resize((W, H), Image.BICUBIC, box=box)


# ================================================================ dibujo
def anchor_of(spec, asset):
    if "anchor" in spec:
        return spec["anchor"]
    if isinstance(asset, str):
        base = asset.replace("__blink", "")
        return META["anchors"].get(base, [0.5, 0.5])
    return [0.5, 0.5]


def draw_element(frame, el, st):
    asset = st["asset"]
    key = img_key(asset)
    src = _IMG_REG[key]
    res = 1.0 if src.size == (W, H) else RS
    sx = st["s"] * st["sx"] / res
    sy = st["s"] * st["sy"] / res
    if st["alpha"] <= 0.004 or abs(sx) < 1e-3 or abs(sy) < 1e-3:
        return
    flip = el.sp.get("flip", False)
    ax, ay = anchor_of(el.sp, asset)
    if flip:
        ax = 1 - ax
    w, h = src.width * sx, src.height * sy
    crop = st["crop"]
    if abs(st["r"]) < 0.05:
        left, top = st["x"] - ax * w, st["y"] - ay * h
        vis_w = w * crop
        vx0, vy0 = max(0, left), max(0, top)
        vx1, vy1 = min(W, left + vis_w), min(H, top + h)
        if vx1 - vx0 < 1 or vy1 - vy0 < 1:
            return
        full = vx0 == left and vy0 == top and vx1 == left + w and vy1 == top + h and crop >= 1 and w * h < 4e6
        if full:
            im = scaled(key, max(1, round(w)), max(1, round(h)), flip)
        else:
            s_src = ImageOps.mirror(src) if flip else src
            box = ((vx0 - left) / sx, (vy0 - top) / sy, (vx1 - left) / sx, (vy1 - top) / sy)
            im = s_src.resize((max(1, round(vx1 - vx0)), max(1, round(vy1 - vy0))), Image.BICUBIC, box=box)
        pos = (round(vx0), round(vy0))
    else:
        iw, ih = max(1, round(w)), max(1, round(h))
        im = scaled(key, iw, ih, flip)
        if crop < 1:
            im = im.crop((0, 0, max(1, int(iw * crop)), ih))
        # dejar el ancla en el centro y rotar alrededor de ella
        axp, ayp = ax * iw, ay * ih
        pw = int(2 * max(axp, iw - axp)) + 2
        ph = int(2 * max(ayp, ih - ayp)) + 2
        pad = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        pad.paste(im, (int(pw / 2 - axp), int(ph / 2 - ayp)))
        im = pad.rotate(-st["r"], resample=Image.BICUBIC, expand=True)
        pos = (round(st["x"] - im.width / 2), round(st["y"] - im.height / 2))
    if st["alpha"] < 0.999:
        im = im.copy()
        a = np.asarray(im.getchannel("A"), dtype=np.float32) * st["alpha"]
        im.putalpha(Image.fromarray(a.astype(np.uint8)))
    frame.paste(im, pos, im)


# ================================================================ subtítulos
class Captions:
    def __init__(self, words, cfg):
        self.cfg = cfg
        self.font = ImageFont.truetype(FONT, int(cfg.get("size", 76) * RS))
        flat = [w for bw in words for w in bw]
        chunks, cur = [], []
        for w in flat:
            cur.append(w)
            text = " ".join(x["w"] for x in cur)
            if len(cur) >= cfg.get("max_palabras", 3) or len(text) >= cfg.get("max_letras", 18) or w["w"][-1] in ".,!?:;":
                chunks.append(cur)
                cur = []
        if cur:
            chunks.append(cur)
        self.chunks = []
        for i, c in enumerate(chunks):
            t0 = c[0]["start"]
            t1 = chunks[i + 1][0]["start"] if i + 1 < len(chunks) else c[-1]["end"] + .5
            t1 = min(t1, c[-1]["end"] + .6)
            self.chunks.append((t0, t1, c))

    @functools.lru_cache(maxsize=256)
    def chunk_image(self, ci, hi):
        _, _, c = self.chunks[ci]
        k = RS
        stroke = int(self.cfg.get("stroke", 12) * k)
        toks = [w["w"].upper() if self.cfg.get("mayusculas", True) else w["w"] for w in c]
        space = self.font.getlength(" ")
        widths = [self.font.getbbox(tk, stroke_width=stroke)[2] - self.font.getbbox(tk, stroke_width=stroke)[0] for tk in toks]
        total = sum(widths) + space * (len(toks) - 1)
        asc, desc = self.font.getmetrics()
        im = Image.new("RGBA", (int(total + 4 * stroke), int(asc + desc + 4 * stroke)), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        x = 2 * stroke
        for i, (tk, wd) in enumerate(zip(toks, widths)):
            col = self.cfg.get("color_activa", "#FFD23F") if i == hi else self.cfg.get("color", "#FFFFFF")
            d.text((x - self.font.getbbox(tk, stroke_width=stroke)[0], 2 * stroke), tk, font=self.font, fill=col,
                   stroke_width=stroke, stroke_fill=INK)
            x += wd + space
        return im

    def draw(self, frame, t):
        for ci, (t0, t1, c) in enumerate(self.chunks):
            if t0 <= t < t1:
                hi = max([i for i, w in enumerate(c) if w["start"] <= t], default=0)
                im = self.chunk_image(ci, hi)
                s = 1 / RS
                if im.width * s > W - 90:
                    s = (W - 90) / im.width
                p = clamp((t - t0) / .12)
                s *= .85 + .15 * ease("back", p)
                w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
                im2 = im.resize((w, h), Image.BICUBIC)
                cx, cy = self.cfg.get("x", W / 2), self.cfg.get("y", 1470)
                frame.paste(im2, (round(cx - w / 2), round(cy - h / 2)), im2)
                return


# ================================================================ proyecto
class Project:
    def __init__(self, path):
        self.path = path
        self.dir = os.path.dirname(os.path.abspath(path))
        self.doc = json.load(open(path))
        doc = self.doc
        beats = doc["narracion"]
        wpath = doc.get("palabras_json")
        if wpath:
            ww = json.load(open(os.path.join(self.dir, wpath)))
            self.words = align_times(beats, ww)
        else:
            self.words = estimate_times(beats, doc.get("velocidad", 1.0))
        self.pausas = self._aplicar_pausas(doc.get("pausas", []))
        self.tl = Timeline(doc, self.words)
        self.scenes = []
        make = lambda e, sc_i, j: (Particles if "particulas" in e else Element)(e, self.tl, sc_i, j)
        for i, sc in enumerate(doc["escenas"]):
            els = [make(e, i, j) for j, e in enumerate(sc.get("elementos", []))]
            self._enlazar(els)
            cam = Camera(sc["camara"], self.tl, i) if sc.get("camara") else None
            self.scenes.append(dict(sc, els=els, cam=cam))
        self.persist = [make(dict(e, z=e.get("z", 50)), None, j) for j, e in enumerate(doc.get("persistentes", []))]
        self._enlazar(self.persist)
        self.caps = Captions(self.words, doc.get("subtitulos", {})) if doc.get("subtitulos", {}).get("activos", True) else None
        for el in self.all_elements():
            img_key(el.asset)
            for a in getattr(el, "assets_extra", []):
                img_key(a)
            for sw in el.swaps:
                img_key(sw["a"])
            if el.seq:
                for f in el.seq["frames"]:
                    img_key(f)
            if "loop" in el.sp:
                for f in el.sp["loop"]["frames"]:
                    img_key(f)
            for lp in getattr(el, "loops", []):
                for f in lp["frames"]:
                    img_key(f)
            if el.blink and isinstance(el.asset, str):
                for a in [el.asset] + [s["a"] for s in el.swaps]:
                    if asset_exists(a + "__blink"):
                        img_key(a + "__blink")
        self.bg = {}
        for sc in self.scenes:
            self.bg[sc["fondo"]] = _IMG_REG[img_key(sc["fondo"])].convert("RGB")

    @staticmethod
    def _enlazar(els):
        """Conecta los elementos con "sigue" con su líder (por "id", dentro de la misma escena)."""
        ids = {e.sp["id"]: e for e in els if "id" in e.sp}
        for e in els:
            if e.sigue:
                if e.sigue["id"] not in ids:
                    raise ValueError(f"sigue: no hay elemento con id {e.sigue['id']!r} en la escena")
                e.lider = ids[e.sigue["id"]]

    def _aplicar_pausas(self, pausas):
        """"pausas": [{"despues": "b4:disparos", "dur": 1.4}] mete silencio en la voz después de esa
        palabra (para que se luzca un efecto de sonido) y corre todo lo que viene después.
        Devuelve [(t_en_audio_original, dur)] para armar la voz con los huecos."""
        if not pausas:
            return []
        tl0 = Timeline(dict(self.doc, escenas=[{"beats": [0]}]), self.words)
        puntos = sorted((tl0.resolve(p["despues"] + (">" if ">" not in p["despues"] else "")), p["dur"]) for p in pausas)
        for w in (w for bw in self.words for w in bw):
            corrimiento = sum(d for t, d in puntos if w["start"] >= t - 1e-3)
            w["start"] += corrimiento
            w["end"] += corrimiento
        return puntos

    def voz_con_pausas(self, path_voz, path_out):
        """Escribe la voz con los silencios de "pausas" insertados."""
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path_voz, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)
        partes, pos = [], 0
        for t, d in self.pausas:
            i = min(len(x), int(t * SR))
            partes += [x[pos:i], np.zeros((int(d * SR), 2), dtype=np.float32)]
            pos = i
        partes.append(x[pos:])
        y = np.concatenate(partes)
        pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16)
        with wave.open(path_out, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        return path_out

    def ambiente_track(self, n):
        """Sonido ambiente por escena ("ambiente": "selva" | "pantano" | "noche" | "bosque", o
        {"tipo": ..., "vol": ...}), con fundidos de 0,5 s entre escenas. Va por debajo de todo."""
        out = np.zeros(n, dtype=np.float32)
        for i, sc in enumerate(self.scenes):
            amb = sc.get("ambiente")
            if not amb:
                continue
            amb = {"tipo": amb} if isinstance(amb, str) else amb
            t0, t1 = self.tl.scene_start[i], self.tl.scene_end[i]
            i0, i1 = int(max(0, t0 - .25) * SR), min(n, int((t1 + .25) * SR))
            if i1 <= i0:
                continue
            seg = ambiente(amb["tipo"], i1 - i0, seed=i) * amb.get("vol", 1.0)
            f = min(int(.5 * SR), len(seg) // 2)
            ramp = np.linspace(0, 1, f, dtype=np.float32)
            seg[:f] *= ramp
            seg[-f:] *= ramp[::-1]
            out[i0:i1] += seg
        return out * self.ducking(n) * self.doc.get("volumen_ambiente", .22)

    def ducking(self, n):
        """Ganancia (0-1) que baja el ambiente ~10 dB mientras habla el narrador y lo deja volver en las
        pausas, para que nunca compita con la voz."""
        voz = self.doc.get("audio_voz")
        if not voz:
            return np.ones(n, dtype=np.float32)
        path = os.path.join(self.dir, voz)
        if self.pausas:
            tmp = tempfile.mkdtemp()
            path = self.voz_con_pausas(path, os.path.join(tmp, "v.wav"))
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                             capture_output=True, check=True).stdout
        v = np.frombuffer(raw, dtype=np.float32)
        hop = SR // 50
        k = len(v) // hop
        env = np.sqrt((v[:k * hop].reshape(k, hop) ** 2).mean(1))
        hablando = (20 * np.log10(env + 1e-9) > -40).astype(np.float32)
        # ataque rápido, liberación lenta (~0,4 s)
        g = np.zeros(k, dtype=np.float32)
        for i in range(k):
            prev = g[i - 1] if i else 0
            g[i] = hablando[i] if hablando[i] > prev else prev * .95
        gain = 1 - .68 * np.repeat(g, hop)
        out = np.ones(n, dtype=np.float32)
        out[:min(n, len(gain))] = gain[:n]
        return out

    def all_elements(self):
        for sc in self.scenes:
            yield from sc["els"]
        yield from self.persist

    def scene_at(self, t):
        for i in range(len(self.scenes)):
            if self.tl.scene_start[i] <= t < self.tl.scene_end[i]:
                return i
        return len(self.scenes) - 1

    def frame(self, t):
        si = self.scene_at(t)
        sc = self.scenes[si]
        frame = self.bg[sc["fondo"]].copy()
        cam = sc["cam"]
        # con cámara, los persistentes se dibujan después del encuadre (quedan fijos)
        groups = [sc["els"], self.persist] if cam else [sc["els"] + self.persist]
        for gi, group in enumerate(groups):
            for el in sorted([e for e in group if e.active(t)], key=lambda e: e.z):
                if isinstance(el, Particles):
                    el.draw(frame, t)
                else:
                    draw_element(frame, el, el.state(t))
            if cam and gi == 0:
                frame = cam.apply(frame, t)
        if sc.get("flash"):
            q = (t - self.tl.scene_start[si]) / .25
            if q < 1:
                white = Image.new("RGB", (W, H), "#FFFFFF")
                frame = Image.blend(white, frame, clamp(q))
        if self.caps:
            self.caps.draw(frame, t)
        return frame

    # ------------------------------------------------------------ audio
    def sfx_track(self):
        n = int((self.tl.total + 1) * SR)
        mix = np.zeros(n, dtype=np.float32)
        events = []
        destacados = []   # "destacado": true = efecto protagonista: no se baja ni se normaliza con el resto
        for el in self.all_elements():
            events += el.sfx_events()
        for sc_i, sc in enumerate(self.scenes):
            for s in sc.get("sonidos", []):
                ev = (self.tl.resolve(s["at"], sc_i), s["s"], s.get("vol", 1.0))
                (destacados if s.get("destacado") else events).append(ev)
            if sc.get("flash"):
                events.append((self.tl.scene_start[sc_i], "whoosh", .8))
        for (t, kind, vol) in events:
            snd = synth(kind, phase_of(f"{t:.3f}{kind}")) * vol
            i0 = int(t * SR)
            i1 = min(n, i0 + len(snd))
            if i0 < n:
                mix[i0:i1] += snd[:i1 - i0]
        mix *= self.doc.get("volumen_efectos", 0.5)
        peak = np.abs(mix).max() or 1
        if peak > .7:
            mix *= .7 / peak
        if self.doc.get("audio_voz"):
            # con voz, los efectos van más bajos para no tapar la narración
            mix *= 10 ** (self.doc.get("efectos_bajo_voz_db", -5) / 20)
        for (t, kind, vol) in destacados:
            snd = synth(kind, phase_of(f"{t:.3f}{kind}")) * vol
            i0 = int(t * SR)
            i1 = min(n, i0 + len(snd))
            if i0 < n:
                mix[i0:i1] += snd[:i1 - i0]
        return mix + self.ambiente_track(n)


@functools.lru_cache(maxsize=None)
def _noise(n, seed):
    return np.random.default_rng(seed).standard_normal(n).astype(np.float32)


def synth(kind, ph=0.0):
    var = 0.9 + 0.2 * (ph / (2 * math.pi))
    if kind == "pop":
        d = .09
        t = np.arange(int(d * SR)) / SR
        f = 900 * var * np.exp(-t * 18) + 220
        sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38)
        return (sig * .9).astype(np.float32)
    if kind in ("whoosh", "whoosh_suave"):
        d = .38 if kind == "whoosh" else .3
        n = int(d * SR)
        x = _noise(n, 1)
        k = np.ones(40, dtype=np.float32) / 40
        lp = np.convolve(x, k, mode="same")
        band = lp - np.convolve(lp, np.ones(400, dtype=np.float32) / 400, mode="same")
        env = np.sin(np.pi * np.arange(n) / n) ** 2
        g = .9 if kind == "whoosh" else .5
        return (band / (np.abs(band).max() + 1e-6) * env * g).astype(np.float32)
    if kind == "ding":
        d = .9
        t = np.arange(int(d * SR)) / SR
        sig = (np.sin(2 * np.pi * 1568 * t) + .6 * np.sin(2 * np.pi * 2349 * t) + .3 * np.sin(2 * np.pi * 3136 * t))
        return (sig / 1.9 * np.exp(-t * 5) * .8).astype(np.float32)
    if kind == "boing":
        d = .28
        t = np.arange(int(d * SR)) / SR
        f = 260 * var + 140 * np.sin(2 * np.pi * 14 * t) * np.exp(-t * 6) + 200 * t
        sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
        return (sig * .6).astype(np.float32)
    if kind == "zoom":
        d = .55
        n = int(d * SR)
        t = np.arange(n) / SR
        x = _noise(n, 2)
        lp = np.convolve(x, np.ones(12, dtype=np.float32) / 12, mode="same")
        env = (t / d) ** 2 * np.exp(-((t - d * .85) ** 2) / .01)
        tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * t / d) / SR) * .3
        sig = (lp / (np.abs(lp).max() + 1e-6) + tone) * env
        return (sig / (np.abs(sig).max() + 1e-6) * .8).astype(np.float32)
    if kind == "viento":
        # ráfaga larga: ruido filtrado con un "silbido" de banda que sube y baja
        d = 2.2
        n = int(d * SR)
        t = np.arange(n) / SR
        x = _noise(n, 3)
        lp = np.convolve(x, np.ones(30, dtype=np.float32) / 30, mode="same")
        band = lp - np.convolve(lp, np.ones(300, dtype=np.float32) / 300, mode="same")
        swell = .55 + .45 * np.sin(2 * np.pi * .9 * t + ph)
        env = np.minimum(1, t / .35) * np.minimum(1, (d - t) / .7)
        sig = band / (np.abs(band).max() + 1e-6) * swell * env
        return (sig * .8).astype(np.float32)
    if kind == "cristal":
        # tintineo de vidrio: parciales agudas desafinadas que se apagan rápido, en tres golpecitos
        d = .7
        t = np.arange(int(d * SR)) / SR
        sig = np.zeros_like(t)
        for k, (t0, f) in enumerate([(0, 2637), (.07, 3520), (.15, 3136)]):
            tt = np.clip(t - t0, 0, None)
            on = (t >= t0).astype(np.float32)
            ff = f * var
            sig += on * (np.sin(2 * np.pi * ff * tt) + .5 * np.sin(2 * np.pi * ff * 2.76 * tt)) * np.exp(-tt * 14)
        return (sig / (np.abs(sig).max() + 1e-6) * .55).astype(np.float32)
    if kind == "brillo":
        # destello mágico: arpegio rápido ascendente de campanitas
        d = 1.0
        t = np.arange(int(d * SR)) / SR
        sig = np.zeros_like(t)
        for k, f in enumerate([1319, 1568, 1976, 2637, 3136]):
            t0 = k * .06
            tt = np.clip(t - t0, 0, None)
            sig += (t >= t0) * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 6)
        return (sig / (np.abs(sig).max() + 1e-6) * .5).astype(np.float32)
    if kind == "tictac":
        # reloj acelerado: clics cada vez más seguidos
        d = 1.0
        n = int(d * SR)
        sig = np.zeros(n, dtype=np.float32)
        click = np.sin(2 * np.pi * 2200 * np.arange(int(.012 * SR)) / SR) * np.exp(-np.arange(int(.012 * SR)) / SR * 400)
        tk, gap, hi = 0.0, .16, True
        while tk < d - .02:
            i0 = int(tk * SR)
            c = click * (1 if hi else .7)
            sig[i0:i0 + len(c)] += c[:n - i0]
            tk += gap
            gap = max(.05, gap * .85)
            hi = not hi
        return (sig * .7).astype(np.float32)
    if kind == "zumbido":
        # tono grave que crece (aparición de algo enorme o amenazante)
        d = .9
        t = np.arange(int(d * SR)) / SR
        f = 70 + 30 * t / d
        sig = (np.sin(2 * np.pi * np.cumsum(f) / SR) + .4 * np.sin(2 * np.pi * np.cumsum(2 * f) / SR))
        env = np.minimum(1, t / .25) * np.exp(-np.clip(t - .5, 0, None) * 6)
        return (sig / 1.4 * env * .8).astype(np.float32)
    if kind == "mosca":
        # zumbido de moscas: diente de sierra grave con trémolo y vibrato
        d = 1.6
        t = np.arange(int(d * SR)) / SR
        f = 210 * var + 18 * np.sin(2 * np.pi * 7 * t)
        phase = np.cumsum(f) / SR
        saw = 2 * (phase % 1) - 1
        trem = .6 + .4 * np.sin(2 * np.pi * 23 * t)
        env = np.minimum(1, t / .2) * np.minimum(1, (d - t) / .4)
        sig = np.convolve(saw * trem * env, np.ones(6, dtype=np.float32) / 6, mode="same")
        return (sig * .35).astype(np.float32)
    if kind == "sierra":
        # serrucho: tres pasadas de ruido áspero que suben y bajan
        d = 1.2
        n = int(d * SR)
        t = np.arange(n) / SR
        x = _noise(n, 4)
        hp = x - np.convolve(x, np.ones(8, dtype=np.float32) / 8, mode="same")
        grain = .6 + .4 * np.sign(np.sin(2 * np.pi * 90 * t))
        env = np.abs(np.sin(np.pi * t / .4)) ** .7
        return (hp / (np.abs(hp).max() + 1e-6) * grain * env * .6).astype(np.float32)
    if kind == "filo":
        # "shing" metálico de cuchillo: barrido agudo + resonancia
        d = .8
        t = np.arange(int(d * SR)) / SR
        x = _noise(len(t), 5)
        hp = x - np.convolve(x, np.ones(4, dtype=np.float32) / 4, mode="same")
        swish = hp * np.exp(-((t - .08) ** 2) / .003)
        ring = (np.sin(2 * np.pi * 3400 * t) + .6 * np.sin(2 * np.pi * 5100 * t)) * np.exp(-t * 5) * (t > .05)
        sig = .5 * swish / (np.abs(swish).max() + 1e-6) + .4 * ring
        return (sig * .7).astype(np.float32)
    if kind == "golpe":
        # golpe dramático: bombo grave + ruido corto (para ganchos y cortes)
        d = .7
        t = np.arange(int(d * SR)) / SR
        f = 45 + 110 * np.exp(-t * 18)
        boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5)
        x = _noise(len(t), 6)
        click = np.convolve(x, np.ones(20, dtype=np.float32) / 20, mode="same") * np.exp(-t * 40)
        sig = boom + 2 * click
        return (sig / (np.abs(sig).max() + 1e-6) * .95).astype(np.float32)
    if kind == "glup":
        # algo que cae en un líquido: "plop" grave + burbujitas
        d = .6
        t = np.arange(int(d * SR)) / SR
        f = 900 * np.exp(-t * 30) + 180
        plop = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)
        bub = np.zeros_like(t)
        for k, t0 in enumerate([.12, .2, .3]):
            tt = np.clip(t - t0, 0, None)
            bub += (t >= t0) * np.sin(2 * np.pi * (500 + 300 * k) * (1 + 3 * tt) * tt) * np.exp(-tt * 40) * .5
        sig = plop + bub
        return (sig / (np.abs(sig).max() + 1e-6) * .7).astype(np.float32)
    if kind == "matraca":
        # picozapato: castañeteo de pico, golpes secos de madera muy seguidos (~18 por segundo)
        d = 1.4
        n = int(d * SR)
        sig = np.zeros(n, dtype=np.float32)
        tk = 0.0
        k = 0
        while tk < d - .03:
            tt = np.arange(int(.03 * SR)) / SR
            f = 900 + 250 * ((k * 7) % 3)
            golpe = (np.sin(2 * np.pi * f * tt) + .6 * np.sin(2 * np.pi * 2.3 * f * tt)) * np.exp(-tt * 160)
            i0 = int(tk * SR)
            amp = .7 + .3 * np.sin(k * 1.7)
            sig[i0:i0 + len(golpe)] += golpe[:n - i0] * amp
            tk += 1 / 18 * (1 + .08 * np.sin(k * 2.1))
            k += 1
        env = np.minimum(1, np.arange(n) / (.05 * SR)) * np.minimum(1, (n - np.arange(n)) / (.15 * SR))
        return (sig * env / (np.abs(sig).max() + 1e-6) * .9).astype(np.float32)
    if kind == "llanto":
        # urutaú: silbidos tristes que bajan, como un lamento (5 notas)
        notas = [(1050, .55), (930, .45), (820, .45), (700, .5), (560, .9)]
        partes = []
        for i, (f0, d) in enumerate(notas):
            tt = np.arange(int(d * SR)) / SR
            f = f0 * (1 - .06 * tt / d) * (1 + .01 * np.sin(2 * np.pi * 5 * tt))
            env = np.sin(np.pi * np.minimum(1, tt / d)) ** 1.5
            partes.append(np.sin(2 * np.pi * np.cumsum(f) / SR) * env)
            partes.append(np.zeros(int(.08 * SR)))
        sig = np.concatenate(partes)
        return (sig / (np.abs(sig).max() + 1e-6) * .6).astype(np.float32)
    if kind == "muu":
        d = 1.1
        t = np.arange(int(d * SR)) / SR
        f = 120 + 40 * np.sin(np.pi * t / d) - 25 * t
        ph = np.cumsum(f) / SR
        saw = 2 * (ph % 1) - 1
        form = np.convolve(saw, np.ones(18) / 18, mode="same")
        env = np.minimum(1, t / .12) * np.minimum(1, (d - t) / .3)
        return (form / (np.abs(form).max() + 1e-6) * env * .7).astype(np.float32)
    if kind == "aleteo":
        # alas: ráfagas cortas de aire
        d = .6
        n = int(d * SR)
        x = _noise(n, 7)
        lp = np.convolve(x, np.ones(25, dtype=np.float32) / 25, mode="same")
        t = np.arange(n) / SR
        env = np.abs(np.sin(2 * np.pi * 9 * t)) ** 3 * np.exp(-t * 2)
        return (lp / (np.abs(lp).max() + 1e-6) * env * .7).astype(np.float32)
    if kind == "pio":
        partes = []
        for f0 in (2600, 3100):
            tt = np.arange(int(.09 * SR)) / SR
            f = f0 * (1 + .3 * tt / .09)
            partes.append(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / .09) ** 2)
            partes.append(np.zeros(int(.05 * SR)))
        return (np.concatenate(partes) * .5).astype(np.float32)
    if kind == "click":
        tt = np.arange(int(.04 * SR)) / SR
        sig = (np.sin(2 * np.pi * 3000 * tt) + .5 * _noise(len(tt), 8)) * np.exp(-tt * 180)
        return (sig / (np.abs(sig).max() + 1e-6) * .8).astype(np.float32)
    if kind == "notificacion":
        # aviso de celular: dos notas cortas que suben
        partes = []
        for f0, d in ((1318, .08), (1760, .14)):
            tt = np.arange(int(d * SR)) / SR
            partes.append((np.sin(2 * np.pi * f0 * tt) + .3 * np.sin(4 * np.pi * f0 * tt)) * np.exp(-tt * 18))
        return (np.concatenate(partes) * .45).astype(np.float32)
    if kind == "sirena":
        # sirena de policía: sube y baja dos veces, con armónicos suaves
        d = 1.3
        t = np.arange(int(d * SR)) / SR
        f = 1000 + 380 * np.sin(2 * np.pi * t / .65 - np.pi / 2)
        fase = 2 * np.pi * np.cumsum(f) / SR
        sig = np.sin(fase) + .35 * np.sin(2 * fase) + .15 * np.sin(3 * fase)
        env = np.minimum(1, t / .08) * np.minimum(1, (d - t) / .2)
        return (sig / 1.5 * env * .5).astype(np.float32)
    if kind == "estatica":
        # estática de monitor: ruido de banda media con chasquidos
        d = .8
        n = int(d * SR)
        t = np.arange(n) / SR
        x = _noise(n, 11)
        band = x - np.convolve(x, np.ones(12, dtype=np.float32) / 12, mode="same")
        band = np.convolve(band, np.ones(3, dtype=np.float32) / 3, mode="same")
        crack = (np.random.default_rng(12).random(n) > .9985) * np.random.default_rng(13).standard_normal(n) * 6
        env = np.minimum(1, t / .03) * np.minimum(1, (d - t) / .25)
        sig = (band / (np.abs(band).max() + 1e-6) * .6 + crack * .1) * env
        return (sig * .5).astype(np.float32)
    if kind == "ronquido":
        # ronquido: inspiración grave que vibra (aleteo ~28 Hz) y una exhalación suave
        d = 1.7
        n = int(d * SR)
        t = np.arange(n) / SR
        x = _noise(n, 14)
        lp = np.convolve(np.convolve(x, np.ones(60, dtype=np.float32) / 60, mode="same"), np.ones(30, dtype=np.float32) / 30, mode="same")
        lp /= np.abs(lp).max() + 1e-6
        insp = (t < 1.0) * np.sin(np.pi * np.clip(t / 1.0, 0, 1)) ** 2 * (.55 + .45 * np.sin(2 * np.pi * 28 * t))
        exh = (t >= 1.05) * np.sin(np.pi * np.clip((t - 1.05) / .6, 0, 1)) ** 2 * .35
        tono = np.sin(2 * np.pi * 95 * t) * insp * .4
        return ((lp * (insp + exh) + tono) * .8).astype(np.float32)
    if kind == "rejas":
        # puerta de rejas que se cierra: golpe metálico con resonancias inarmónicas
        d = 1.4
        t = np.arange(int(d * SR)) / SR
        sig = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * k)
                  for f, a, k in ((180, 1, 4), (523, .6, 5), (1371, .45, 7), (2210, .3, 9), (3320, .2, 12)))
        x = _noise(len(t), 15)
        golpe = np.convolve(x, np.ones(8, dtype=np.float32) / 8, mode="same") * np.exp(-t * 60)
        sig = sig + 1.5 * golpe
        return (sig / (np.abs(sig).max() + 1e-6) * .8).astype(np.float32)
    if kind == "obturador":
        # foto: clic doble de obturador
        partes = []
        for k in (0, 1):
            tt = np.arange(int(.05 * SR)) / SR
            partes.append((_noise(len(tt), 16 + k) * np.exp(-tt * 120) + np.sin(2 * np.pi * 2200 * tt) * np.exp(-tt * 200)))
            partes.append(np.zeros(int(.06 * SR)))
        sig = np.concatenate(partes)
        return (sig / (np.abs(sig).max() + 1e-6) * .6).astype(np.float32)
    raise ValueError(f"sonido desconocido: {kind}")


def ambiente(tipo, n, seed=0):
    """Ambiente procedural (semilla fija) de n muestras: SOLO eventos sueltos y naturales con silencio entre
    medio (pájaros, ranas, grillos en ráfagas) + un aire muy suave en graves. Nada de ruido ni tonos
    continuos: debajo de la voz se escuchan como un siseo molesto (corrección del usuario, video de aves)."""
    rnd = np.random.default_rng(100 + seed)
    t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float32)
    # aire: ruido filtrado por debajo de ~300 Hz, muy bajo y que sube y baja despacio
    base = np.random.default_rng(200 + seed).standard_normal(n).astype(np.float32)
    lp = np.convolve(base, np.ones(160, dtype=np.float32) / 160, mode="same")
    lp = np.convolve(lp, np.ones(160, dtype=np.float32) / 160, mode="same")
    out += lp / (np.abs(lp).max() + 1e-6) * .03 * (.6 + .4 * np.sin(2 * np.pi * .07 * t + seed)).astype(np.float32)

    def pegar(snd, at):
        i = int(at * SR)
        if 0 <= i < n:
            out[i:i + len(snd)] += snd[:n - i]

    def pio(f0, d=.12):
        tt = np.arange(int(d * SR)) / SR
        f = f0 * (1 + .25 * np.sin(2 * np.pi * 18 * tt)) * (1 + .4 * tt / d)
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / d) ** 2).astype(np.float32)

    dur = n / SR
    if tipo in ("selva", "bosque"):
        k = 1.0 if tipo == "selva" else .6
        at = rnd.uniform(.3, 1.0)
        while at < dur:   # pájaros: frases de 1-3 notas, bien separadas
            f0 = rnd.uniform(1600, 3200)
            for j in range(rnd.integers(1, 4)):
                pegar(pio(f0 * rnd.uniform(.9, 1.1)) * rnd.uniform(.12, .25) * k, at + j * .15)
            at += rnd.uniform(1.0, 2.6) / k
        if tipo == "selva":   # de vez en cuando un llamado más grave y lejano
            at = rnd.uniform(2, 4)
            while at < dur:
                pegar(pio(rnd.uniform(700, 1000), .35) * .1, at)
                at += rnd.uniform(4, 8)
    elif tipo == "pantano":
        at = rnd.uniform(.5, 1.5)
        while at < dur:   # ranas: croar suave (pulsos redondeados), en grupos espaciados
            f0 = rnd.uniform(140, 240)
            for j in range(rnd.integers(2, 5)):
                tt = np.arange(int(.08 * SR)) / SR
                croak = np.sin(2 * np.pi * f0 * tt) * np.sin(np.pi * tt / .08) ** 2
                pegar((croak * .16).astype(np.float32), at + j * .12)
            at += rnd.uniform(1.6, 3.5)
        at = rnd.uniform(2, 4)
        while at < dur:
            pegar(pio(rnd.uniform(1200, 1800), .25) * .1, at)
            at += rnd.uniform(4, 7)
    elif tipo == "abismo":   # sonar lejano, grupos de burbujas y algún llamado grave
        at = rnd.uniform(1, 3)
        while at < dur:
            tt = np.arange(int(1.4 * SR)) / SR
            ping = np.sin(2 * np.pi * 1250 * tt) * np.exp(-tt * 3.5) * (tt < 1.4)
            pegar((ping * .08).astype(np.float32), at)
            at += rnd.uniform(6, 9)
        at = rnd.uniform(.5, 1.5)
        while at < dur:
            for j in range(rnd.integers(2, 6)):
                tt = np.arange(int(.06 * SR)) / SR
                f = rnd.uniform(400, 900) * (1 + 2.5 * tt / .06)
                burb = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / .06) ** 2
                pegar((burb * .1).astype(np.float32), at + j * rnd.uniform(.05, .12))
            at += rnd.uniform(1.8, 3.5)
        at = rnd.uniform(4, 7)
        while at < dur:
            tt = np.arange(int(2.2 * SR)) / SR
            f = 170 - 60 * tt / 2.2
            moan = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / 2.2) ** 2
            pegar((moan * .07).astype(np.float32), at)
            at += rnd.uniform(9, 14)
    elif tipo == "fiesta":   # música de fiesta lejana: frases de bombo (120 bpm) con pausas, algún platillo
        at = rnd.uniform(.2, .6)
        while at < dur:
            for j in range(int(rnd.choice([8, 8, 12, 16]))):
                tt = np.arange(int(.18 * SR)) / SR
                f = 48 + 70 * np.exp(-tt * 30)
                bombo = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 16)
                pegar((bombo * .32).astype(np.float32), at + j * .5)
                if j % 2:
                    th = np.arange(int(.04 * SR)) / SR
                    hat = np.random.default_rng(int(at * 10) + j).standard_normal(len(th)) * np.exp(-th * 90)
                    pegar((hat * .025).astype(np.float32), at + j * .5)
            at += j * .5 + rnd.uniform(1.0, 2.0)
    elif tipo == "carcel":   # cárcel: goteo espaciado y algún portazo metálico lejano
        at = rnd.uniform(.5, 1.5)
        while at < dur:
            tt = np.arange(int(.12 * SR)) / SR
            f = 1400 * np.exp(-tt * 25) + 700
            gota = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 40)
            pegar((gota * .1).astype(np.float32), at)
            at += rnd.uniform(2.2, 4.0)
        at = rnd.uniform(3, 6)
        while at < dur:
            tt = np.arange(int(1.0 * SR)) / SR
            clank = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * k) for f, a, k in ((150, 1, 5), (440, .5, 7), (1100, .25, 10)))
            pegar((clank * .05).astype(np.float32), at)
            at += rnd.uniform(6, 10)
    elif tipo == "internet":   # algún aviso de celular suelto, muy bajo
        at = rnd.uniform(1, 2.5)
        while at < dur:
            for f0, d0, off in ((1318, .07, 0), (1760, .1, .08)):
                tt = np.arange(int(d0 * SR)) / SR
                pegar((np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 20) * .05).astype(np.float32), at + off)
            at += rnd.uniform(3, 6)
    elif tipo == "noche":   # grillos: ráfagas cortas con silencios, no un pitido continuo
        at = rnd.uniform(.2, .8)
        while at < dur:
            f0 = rnd.uniform(3600, 4200)
            for j in range(rnd.integers(3, 6)):
                tt = np.arange(int(.05 * SR)) / SR
                chirp = np.sin(2 * np.pi * f0 * tt) * np.sin(np.pi * tt / .05) ** 2
                pegar((chirp * .07).astype(np.float32), at + j * .09)
            at += rnd.uniform(.9, 2.0)
    return out.astype(np.float32)


def write_wav(path, data):
    pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
    stereo = np.stack([pcm, pcm], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())


# ================================================================ render
_PROJ = None


def _render_segment(args):
    f0, f1, out = args
    proj = _PROJ
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-r", str(FPS), out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(proj.frame(f / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return out


def render(proj, out_path, workers=2):
    global _PROJ
    _PROJ = proj
    nframes = int(math.ceil(proj.tl.total * FPS))
    tmp = tempfile.mkdtemp(prefix="render_", dir=proj.dir)
    k = max(1, workers)
    bounds = [round(nframes * i / k) for i in range(k + 1)]
    segs = [(bounds[i], bounds[i + 1], os.path.join(tmp, f"seg{i}.mp4")) for i in range(k)]
    with Pool(k) as pool:
        files = pool.map(_render_segment, segs)
    lst = os.path.join(tmp, "lista.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{x}'\n" for x in files)
    video = os.path.join(tmp, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video], check=True)
    sfx = os.path.join(tmp, "efectos.wav")
    write_wav(sfx, proj.sfx_track())
    voz = proj.doc.get("audio_voz")
    if voz:
        voz = os.path.join(proj.dir, voz)
        if proj.pausas:
            voz = proj.voz_con_pausas(voz, os.path.join(tmp, "voz_pausas.wav"))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", voz, "-i", sfx, "-filter_complex",
               "[1:a][2:a]amix=inputs=2:normalize=0,alimiter=limit=0.89:attack=3:release=60:level=false[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy",
               "-c:a", "aac", "-b:a", "192k", "-shortest", out_path]
    else:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", sfx, "-map", "0:v", "-map", "1:a",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", out_path]
    subprocess.run(cmd, check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    return nframes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("escenas")
    ap.add_argument("--salida")
    ap.add_argument("--fotos", help="tiempos separados por coma para exportar PNG sueltos")
    ap.add_argument("--hilos", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--tiempos", action="store_true", help="mostrar tiempos estimados por bloque")
    a = ap.parse_args()
    proj = Project(a.escenas)
    if a.tiempos:
        for i, ws in enumerate(proj.words):
            print(f"b{i:<2} {ws[0]['start']:6.2f}-{ws[-1]['end']:6.2f}  {' '.join(w['w'] for w in ws)}")
        print(f"total {proj.tl.total:.2f}s")
        for i in range(len(proj.scenes)):
            print(f"escena {i}: {proj.tl.scene_start[i]:.2f} - {proj.tl.scene_end[i]:.2f}  {proj.scenes[i].get('nombre', '')}")
        return
    if a.fotos:
        outdir = os.path.join(proj.dir, "fotos")
        os.makedirs(outdir, exist_ok=True)
        for ts in a.fotos.split(","):
            t = float(ts)
            proj.frame(t).save(os.path.join(outdir, f"f_{t:06.2f}.png"))
        print("fotos en", outdir)
        return
    out = a.salida or os.path.join(proj.dir, "short.mp4")
    n = render(proj, out, a.hilos)
    print(f"listo: {out}  ({n} fotogramas, {proj.tl.total:.1f}s)")


if __name__ == "__main__":
    main()

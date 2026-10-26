"""Motor de animación: escenas.json -> short vertical en MP4.

    python motor.py proyectos/3cosas/escenas.json            # render completo
    python motor.py proyectos/3cosas/escenas.json --fotos 1.2,5,9.5   # fotogramas sueltos (PNG)

Las acciones se anclan a palabras del guion ("b3:gravedad" = cuando se dice
"gravedad" en el bloque 3). Sin audio, los tiempos se estiman por largo de
palabra; con una grabación + palabras.json (Whisper) se usan los tiempos reales.
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
    sh = int(10 * k) if sp.get("box") and sp.get("shadow", True) else 0
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
FX_DUR = {"pop": .35, "grow": .35, "jump": .45, "drop": .6, "fade": .3, "wipe": .8,
          "slide_up": .45, "slide_down": .45, "slide_left": .45, "slide_right": .45, "none": 0}
FX_SFX = {"pop": "pop", "grow": "pop", "jump": "pop", "drop": "pop", "slide_up": "whoosh",
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
        self.ph = phase_of(json.dumps(spec, sort_keys=True))
        self.blink = spec.get("blink", False)
        lp = spec.get("loop", {})
        self.loop_t0 = R(lp["from"]) if "from" in lp else None
        self.loop_t1 = R(lp["to"]) if "to" in lp else 1e9

    # ------------------------------------------------------------ sonidos
    def sfx_events(self):
        ev = []
        s = self.sp.get("sfx", FX_SFX.get(self.fx_in))
        if s and s != "none":
            ev.append((self.tin, s, self.sp.get("vol", 1.0)))
        for sw in self.swaps:
            if sw.get("fx") == "punch" and sw.get("sfx", "boing") != "none":
                ev.append((sw["t"], sw.get("sfx", "boing"), .7))
        for k in self.keys:
            if k.get("sfx") and k["sfx"] != "none":
                ev.append((k["t"], k["sfx"], 1.0))
        return ev

    def active(self, t):
        return self.tin <= t < self.tout

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
            # secuencia en bucle; con "from"/"to" solo corre en esa ventana (fuera muestra el primer dibujo)
            lp = sp["loop"]
            t0 = self.loop_t0 if self.loop_t0 is not None else self.tin
            if t0 <= t < self.loop_t1:
                asset = lp["frames"][int((t - t0) * lp.get("fps", 6)) % len(lp["frames"])]
            elif self.loop_t0 is not None:
                asset = lp["frames"][0]
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
            else:
                raise ValueError(f"idle desconocido: {f}")
        # parpadeo
        if self.blink and isinstance(asset, str) and asset_exists(asset + "__blink"):
            per = 3.3 + (ph % 1.0)
            if ((t + ph) % per) < .12:
                asset = asset + "__blink"
        st["asset"] = asset
        return st


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
        self.tl = Timeline(doc, self.words)
        self.scenes = []
        for i, sc in enumerate(doc["escenas"]):
            els = [Element(e, self.tl, i, j) for j, e in enumerate(sc.get("elementos", []))]
            # cámara: zoom de toda la escena; "s" es el zoom y (x, y) el punto que queda fijo en pantalla
            cam = Element({"keys": sc["camara"], "x": W / 2, "y": H / 2, "s": 1.0}, self.tl, i) if sc.get("camara") else None
            self.scenes.append(dict(sc, els=els, cam=cam))
        self.persist = [Element(dict(e, z=e.get("z", 50)), self.tl, None, j) for j, e in enumerate(doc.get("persistentes", []))]
        self.caps = Captions(self.words, doc.get("subtitulos", {})) if doc.get("subtitulos", {}).get("activos", True) else None
        for el in self.all_elements():
            img_key(el.asset)
            for sw in el.swaps:
                img_key(sw["a"])
            if el.seq:
                for f in el.seq["frames"]:
                    img_key(f)
            if "loop" in el.sp:
                for f in el.sp["loop"]["frames"]:
                    img_key(f)
            if el.blink and isinstance(el.asset, str):
                for a in [el.asset] + [s["a"] for s in el.swaps]:
                    if asset_exists(a + "__blink"):
                        img_key(a + "__blink")
        self.bg = {}
        for sc in self.scenes:
            self.bg[sc["fondo"]] = _IMG_REG[img_key(sc["fondo"])].convert("RGB")

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
        els = [e for e in sc["els"] + self.persist if e.active(t)]
        for el in sorted(els, key=lambda e: e.z):
            draw_element(frame, el, el.state(t))
        if sc.get("cam"):
            cs = sc["cam"].state(t)
            z = max(cs["s"], 1.0)
            if z > 1.001:
                left, top = cs["x"] - cs["x"] / z, cs["y"] - cs["y"] / z
                frame = frame.resize((W, H), Image.BICUBIC, box=(left, top, left + W / z, top + H / z))
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
        for el in self.all_elements():
            events += el.sfx_events()
        for sc_i, sc in enumerate(self.scenes):
            for s in sc.get("sonidos", []):
                events.append((self.tl.resolve(s["at"], sc_i), s["s"], s.get("vol", 1.0)))
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
        return mix


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
    if kind == "crack":     # crujido seco (hueso, madera)
        d = .32
        n = int(d * SR)
        t = np.arange(n) / SR
        x = _noise(n, 3)
        clicks = np.zeros(n, dtype=np.float32)
        for k, at in enumerate((0, .025, .05, .09, .14)):
            i = int(at * SR)
            clicks[i:i + 400] += np.exp(-np.arange(min(400, n - i)) / 60) * (1 - .15 * k)
        hp = x - np.convolve(x, np.ones(6, dtype=np.float32) / 6, mode="same")
        sig = hp * clicks * 1.4 + np.sin(2 * np.pi * 110 * t) * np.exp(-t * 30) * .5
        return (sig / (np.abs(sig).max() + 1e-6) * .9).astype(np.float32)
    if kind == "golpe":     # golpe sordo
        d = .3
        t = np.arange(int(d * SR)) / SR
        f = 140 * var * np.exp(-t * 10) + 45
        sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)
        lp = np.convolve(_noise(len(t), 4), np.ones(30, dtype=np.float32) / 30, mode="same") * np.exp(-t * 40)
        sig = sig + lp * 2
        return (sig / (np.abs(sig).max() + 1e-6) * .9).astype(np.float32)
    if kind == "clic":      # trinquete metálico (manivela)
        d = .07
        t = np.arange(int(d * SR)) / SR
        sig = (np.sin(2 * np.pi * 2600 * var * t) + .5 * np.sin(2 * np.pi * 4100 * t)) * np.exp(-t * 90)
        return (sig * .5).astype(np.float32)
    if kind == "fuego":     # chisporroteo
        d = 1.0
        n = int(d * SR)
        rng = np.random.default_rng(int(ph * 1000) % 2 ** 32)
        sig = np.convolve(_noise(n, 5), np.ones(50, dtype=np.float32) / 50, mode="same") * .25
        for i in rng.integers(0, n - 300, 40):
            sig[i:i + 300] += _noise(300, 6) * np.exp(-np.arange(300) / 40) * rng.uniform(.2, .8)
        env = np.minimum(1, np.minimum(np.arange(n) / 2000, (n - np.arange(n)) / 8000))
        return (sig * env / (np.abs(sig).max() + 1e-6) * .7).astype(np.float32)
    if kind == "cuervo":    # graznido: tono ronco con ruido, dos golpes
        d = .5
        n = int(d * SR)
        t = np.arange(n) / SR
        f = 520 * var * (1 - .25 * t / d)
        car = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * .5 + _noise(n, 7) * .35
        env = np.zeros(n, dtype=np.float32)
        for t0 in (0, .24):
            i0, i1 = int(t0 * SR), int((t0 + .2) * SR)
            env[i0:i1] = np.sin(np.pi * np.arange(i1 - i0) / (i1 - i0)) ** .6
        sig = np.convolve(car * env, np.ones(8, dtype=np.float32) / 8, mode="same")
        return (sig / (np.abs(sig).max() + 1e-6) * .6).astype(np.float32)
    if kind == "cruje":     # crujido de madera y soga tensa
        d = .7
        n = int(d * SR)
        t = np.arange(n) / SR
        pulses = (np.sin(2 * np.pi * 38 * t) > .7).astype(np.float32)
        tone = np.sin(2 * np.pi * np.cumsum(180 + 60 * np.sin(2 * np.pi * 3 * t)) / SR)
        sig = (tone * .6 + _noise(n, 8) * .4) * pulses
        sig = np.convolve(sig, np.ones(20, dtype=np.float32) / 20, mode="same") * np.sin(np.pi * t / d)
        return (sig / (np.abs(sig).max() + 1e-6) * .7).astype(np.float32)
    raise ValueError(f"sonido desconocido: {kind}")


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
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", voz, "-i", sfx, "-filter_complex",
               "[1:a][2:a]amix=inputs=2:normalize=0[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy",
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

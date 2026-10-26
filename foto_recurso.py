"""Convierte una foto de referencia en un recurso del kit con el estilo de los dibujos.

    python3 foto_recurso.py recursos_foto.json            # procesa todas las entradas
    python3 foto_recurso.py recursos_foto.json kirk_cara   # solo una

Para personas reales que tienen que reconocerse: se recorta la cabeza de la foto (por color de fondo
o por un contorno marcado sobre la foto), se suaviza y se reduce a pocos colores (plano, como el resto
del kit) y se le pone el mismo contorno oscuro. El PNG sale a `recursos/fotos/<nombre>.png` y `kit.py`
lo usa dentro de los SVG (`foto()`), así se combina con cuerpos, ropa y accesorios dibujados.

Cada entrada del JSON:
  {"nombre": "kirk_cara", "foto": "proyectos/memes/referencias/kirk.jpg",
   "contorno": [[x, y], ...],          # polígono sobre la foto original (se suaviza), o
   "fondo": [r, g, b], "tolerancia": 60,   # quitar un fondo liso por color (se puede combinar)
   "excluir": "r > 1.9 * g",            # quitar lo que cumpla esto (r, g, b de 0 a 255) solo en el borde
   "banda": 40,                        # ancho (px de salida) del borde donde se aplica "excluir"
   "extender_arriba": 80,              # foto cortada arriba: estira el borde superior (el contorno puede
                                       # usar y negativas)
   "pelo": {"parche": [x0, y0, x1, y1], "linea": [[x, y], ...]},   # completa la cabeza: encima de la
                                       # línea del pelo, textura de pelo sacada de un parche de la misma foto
   "achicar": {"centro": [x, y], "radios": [rx, ry], "escala": .42},   # el meme de la "cara chiquita":
                                       # ojos, nariz y boca achicados en el medio; alrededor, la misma cara borrosa
   "ancho": 600,                       # ancho de salida en px
   "colores": 14, "suavizado": 3,      # estilo: cantidad de colores y filtro de mediana
   "contorno_px": 9}                   # grosor del borde oscuro
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "recursos", "fotos")
INK = (36, 32, 31)


def suavizar_poligono(pts, pasos=12):
    """Catmull-Rom cerrado: el contorno marcado a mano queda curvo y prolijo."""
    p = np.array(pts, dtype=float)
    n = len(p)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = p[i - 1], p[i], p[(i + 1) % n], p[(i + 2) % n]
        for t in np.linspace(0, 1, pasos, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                             + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return [tuple(q) for q in out]


def achicar(im, centro, radios, escala=.42):
    """Achica la zona de los rasgos (elipse) hacia su centro y rellena con la cara desenfocada."""
    (cx, cy), (rx, ry) = centro, radios
    W, H = im.size
    elipse = Image.new("L", (W, H), 0)
    ImageDraw.Draw(elipse).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    pluma = elipse.filter(ImageFilter.GaussianBlur(max(rx, ry) * .18))
    # relleno: un modelo suave del color de la piel (luz y sombra) ajustado solo con píxeles de piel
    # alrededor y adentro de la elipse (sin pelo, cejas, ojos ni dientes): no deja rastros de los rasgos
    k = 4
    a = np.asarray(im.resize((W // k, H // k), Image.BILINEAR), dtype=float)
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    u, v = (xx * k - cx) / rx, (yy * k - cy) / ry
    rad = np.sqrt(u ** 2 + v ** 2)
    lum = a.mean(-1)
    piel = (rad < 1.4) & (lum > 95) & (lum < 225) & (a[..., 0] > a[..., 2] * 1.05)
    A = np.stack([np.ones_like(u), u, v, u * u, v * v, u * v], -1)
    coef = np.linalg.lstsq(A[piel], a[piel], rcond=None)[0]
    rel = (A @ coef).clip(0, 255).astype(np.uint8)
    fondo = Image.fromarray(rel).resize((W, H), Image.BICUBIC)
    out = Image.composite(fondo, im, pluma)
    rasgos = im.crop((cx - rx, cy - ry, cx + rx, cy + ry))
    m = pluma.crop((cx - rx, cy - ry, cx + rx, cy + ry))
    w, h = max(1, round(2 * rx * escala)), max(1, round(2 * ry * escala))
    rasgos = rasgos.resize((w, h), Image.LANCZOS)
    m = Image.new("L", (w, h), 0)   # borde suave propio a la escala chica
    ImageDraw.Draw(m).ellipse((w * .1, h * .1, w * .9, h * .9), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(min(w, h) * .08))
    out.paste(rasgos, (round(cx - w / 2), round(cy - h / 2)), m)
    return out


def pelo(im, spec, n):
    """Rellena lo que está arriba de la línea del pelo con mechones tomados de un parche de la foto
    (repetido con espejos para que no se note el patrón) y lo sombrea para dar volumen."""
    x0, y0, x1, y1 = spec["parche"]
    parche = im.crop((x0, y0 + n, x1, y1 + n))
    linea = [(x, y + n) for x, y in spec["linea"]]
    xa, xb = linea[0][0], linea[-1][0]
    alto = int(max(y for _, y in linea)) + 1
    W = int(xb - xa) + 1
    tex = Image.new("RGBA", (W, alto), (0, 0, 0, 0))
    rnd = np.random.default_rng(3)
    pw = parche.width
    paso = max(4, int(pw * .45))
    for x in list(range(-pw // 2, W, paso)):
        k = rnd.uniform(.95, 1.35)
        p = parche.resize((pw, int(alto * k)), Image.BICUBIC)
        if rnd.random() < .5:
            p = p.transpose(Image.FLIP_LEFT_RIGHT)
        # mechones en abanico: a la izquierda se inclinan hacia la izquierda y a la derecha al revés
        ang = ((x + pw / 2) / W - .5) * -spec.get("abanico", 34) + rnd.uniform(-4, 4)
        borde = Image.new("L", p.size, 0)
        ImageDraw.Draw(borde).rectangle((pw * .2, 0, pw * .8, p.height), fill=255)
        borde = borde.filter(ImageFilter.GaussianBlur(pw * .12))
        p = p.convert("RGBA")
        p.putalpha(borde)
        p = p.rotate(ang, Image.BICUBIC, expand=True)
        tex.alpha_composite(p, (int(x - (p.width - pw) / 2), int(alto - p.height + rnd.uniform(0, alto * .15))))
    base = Image.new("RGBA", tex.size, tuple(int(c) for c in np.asarray(parche).reshape(-1, 3).mean(0)) + (255,))
    base.alpha_composite(tex)
    a = np.asarray(base.convert("RGB"), dtype=float)
    yy = np.linspace(0, 1, alto)[:, None, None]
    xx = np.abs(np.linspace(-1, 1, W))[None, :, None]
    a = a * spec.get("brillo", .93) * (1.0 - .16 * xx ** 2) * (.9 + .12 * np.sin(yy * np.pi * .9))   # volumen: costados y raíz más oscuros
    tex = Image.fromarray(a.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.5))
    tex = tex.filter(ImageFilter.UnsharpMask(3, spec.get("contraste", 120), 2))   # mechones marcados
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).polygon(suavizar_poligono(linea + [(xb, 0), (xa, 0)], 6), fill=255)
    # línea del pelo irregular: mechones que bajan sobre la frente (no un corte recto)
    mb = np.asarray(m.filter(ImageFilter.GaussianBlur(9)), dtype=float) / 255
    rnd = np.random.default_rng(5)
    vetas = rnd.random((1, im.width)).repeat(im.height, 0)
    vetas = np.asarray(Image.fromarray((vetas * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.7)),
                       dtype=float) / 255
    m = Image.fromarray(((mb + (vetas - .5) * .7) > .5).astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(1))
    capa = im.copy()
    capa.paste(tex, (int(xa), 0))
    return Image.composite(capa, im, m)


def mascara(im, e, k):
    """Máscara (L) en la escala de trabajo k: polígono y/o fondo por color."""
    W, H = im.size
    m = Image.new("L", (W, H), 255)
    if "contorno" in e:
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon([(x * k, y * k) for x, y in suavizar_poligono(e["contorno"])], fill=255)
    if "fondo" in e:
        a = np.asarray(im.convert("RGB"), dtype=float)
        d = np.sqrt(((a - np.array(e["fondo"], dtype=float)) ** 2).sum(-1))
        tol = e.get("tolerancia", 60)
        key = Image.fromarray((np.clip((d - tol * .6) / (tol * .4), 0, 1) * 255).astype(np.uint8))
        key = key.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))   # sin pelusas sueltas
        m = ImageChops.multiply(m, key)
    return m.filter(ImageFilter.GaussianBlur(1.2))


def procesar(e):
    im = Image.open(os.path.join(AQUI, e["foto"])).convert("RGB")
    if e.get("extender_arriba"):
        n = e["extender_arriba"]
        a = np.asarray(im)
        fila = Image.fromarray(a[:8].mean(0, keepdims=True).astype(np.uint8)).resize((a.shape[1], 1))
        borde = np.asarray(fila.resize((a.shape[1] // 8, 1), Image.BILINEAR).resize((a.shape[1], 1), Image.BILINEAR))
        im = Image.fromarray(np.concatenate([np.repeat(borde, n, axis=0), a], axis=0))
        e = dict(e, contorno=[[x, y + n] for x, y in e["contorno"]]) if "contorno" in e else e
        if "pelo" in e:
            im = pelo(im, e["pelo"], n)
    if "recorte" in e:   # [x0, y0, x1, y1] en la foto original
        x0, y0, x1, y1 = e["recorte"]
        im = im.crop((x0, y0, x1, y1))
        for key in ("contorno",):
            if key in e:
                e = dict(e, **{key: [[x - x0, y - y0] for x, y in e[key]]})
    if "achicar" in e:
        im = achicar(im, **e["achicar"])
    W0, H0 = im.size
    ancho = e.get("ancho", 600)
    k = ancho / W0
    im = im.resize((ancho, round(H0 * k)), Image.LANCZOS)
    m = mascara(im.resize((W0, H0)), e, 1).resize(im.size, Image.LANCZOS) if "fondo" in e else mascara(im, e, k)
    if "excluir" in e:   # restos de fondo pegados al contorno (cortina, pared) que no son pelo ni piel
        a = np.asarray(im.filter(ImageFilter.GaussianBlur(1.5)), dtype=float)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        fuera = Image.fromarray((eval(e["excluir"], {"np": np}, {"r": r, "g": g, "b": b}) * 255).astype(np.uint8))
        fuera = fuera.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(5))
        n = e.get("banda", 40) | 1
        borde = ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(n)))
        quitar = ImageChops.multiply(fuera, borde.point(lambda v: 255 if v > 0 else 0))
        m = ImageChops.subtract(m, quitar)
    # borde prolijo: sin escalones ni pelusas (desenfocar, cortar al medio y suavizar apenas)
    m = m.filter(ImageFilter.GaussianBlur(e.get("alisado", 4))).point(lambda v: 255 if v > 128 else 0)
    m = m.filter(ImageFilter.GaussianBlur(1.1))
    # estilo plano: suavizar, pocos colores, un poco más de color y contraste
    st = im
    if e.get("suavizado", 3) > 1:
        st = st.filter(ImageFilter.MedianFilter(e["suavizado"] | 1 if "suavizado" in e else 3))
    st = ImageEnhance.Color(st).enhance(e.get("saturacion", 1.15))
    st = ImageEnhance.Contrast(st).enhance(e.get("contraste", 1.05))
    if e.get("colores"):
        st = st.quantize(e["colores"], method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
        st = st.filter(ImageFilter.ModeFilter(e.get("moda", 5)))
    # contorno oscuro igual al de los dibujos (máscara engordada por detrás)
    borde = e.get("contorno_px", 9)
    mb = m.point(lambda v: 255 if v > 100 else 0)
    pad = borde + 4
    lienzo = Image.new("RGBA", (st.width + 2 * pad, st.height + 2 * pad), (0, 0, 0, 0))
    gordo = Image.new("L", lienzo.size, 0)
    gordo.paste(mb, (pad, pad))
    if borde > 0:
        gordo = gordo.filter(ImageFilter.MaxFilter(2 * borde + 1)).filter(ImageFilter.GaussianBlur(1))
        lienzo.paste(Image.new("RGBA", lienzo.size, INK + (255,)), (0, 0), gordo)
    cara = st.convert("RGBA")
    cara.putalpha(m)
    lienzo.alpha_composite(cara, (pad, pad))
    # recortar al contenido
    lienzo = lienzo.crop(lienzo.getbbox())
    os.makedirs(SALIDA, exist_ok=True)
    out = os.path.join(SALIDA, e["nombre"] + ".png")
    lienzo.save(out)
    print(f"{e['nombre']}: {lienzo.size[0]}x{lienzo.size[1]} -> {os.path.relpath(out, AQUI)}")
    return out


if __name__ == "__main__":
    specs = json.load(open(sys.argv[1]))
    solo = sys.argv[2:] or None
    for e in specs:
        if not solo or e["nombre"] in solo:
            procesar(e)

"""Piezas compartidas para los armar_escenas.py de cada proyecto.

Lo que se mejora acá lo heredan todos los videos nuevos (ver PAUTAS.md). Uso:

    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    from comun import cartel, encabezado, armar_doc
"""
import json
import os

# Carteles: borde y sombra finos (PAUTAS: "los mensajes que popean no están finos").
_CAJA = {"sombra": 6, "box_stroke": 5}
ESTILOS = {
    "titulo": {"size": 84, "color": "#FFFFFF", "stroke": 12},
    "num": {"size": 96, "color": "#24201F", "box": "#FFD23F", "circle": True, "pad": [22, 14]},
    "cartel": {"size": 80, "color": "#24201F", "box": "#FFFFFF", **_CAJA},
    "cartel_rojo": {"size": 80, "color": "#FFFFFF", "box": "#FF5D5D", "stroke": 9, **_CAJA},
    "cartel_amarillo": {"size": 80, "color": "#24201F", "box": "#FFD23F", **_CAJA},
    "cartel_celeste": {"size": 80, "color": "#24201F", "box": "#9ADCFF", **_CAJA},
    "cartel_verde": {"size": 80, "color": "#24201F", "box": "#8BD06A", **_CAJA},
    "cartel_violeta": {"size": 80, "color": "#FFFFFF", "box": "#7A5CFF", "stroke": 9, **_CAJA},
    "cartel_marron": {"size": 80, "color": "#FFFFFF", "box": "#7A5236", "stroke": 9, **_CAJA},
    "cartel_rosa": {"size": 80, "color": "#24201F", "box": "#F7A08C", **_CAJA},
    "cartel_naranja": {"size": 80, "color": "#24201F", "box": "#F0A060", **_CAJA},
    "cartel_negro": {"size": 80, "color": "#FFFFFF", "box": "#2B2730", "stroke": 0, **_CAJA},
    "censura": {"size": 104, "color": "#FFFFFF", "box": "#14121A", "stroke": 0, "radius": 10},
}


def cartel(t, x, y, at, size=76, estilo="cartel", **kw):
    """Cartel con entrada y salida suaves; si no se indica "out", se va prolijo antes del corte de escena."""
    e = {"texto": {"t": t, "estilo": estilo, "size": size}, "x": x, "y": y, "in": at, "fx_in": "suave",
         "fx_out": "suave", "vol": .6, "z": 20}
    e.update(kw)
    return e


def encabezado(num, titulo, desde, hasta, size=80):
    """Número en círculo + nombre arriba (y=250), desde una referencia hasta otra (p. ej. "b1" → "e4")."""
    return [
        {"texto": {"t": str(num), "estilo": "num"}, "x": 130, "y": 250, "in": desde, "out": hasta, "fx_in": "pop",
         "fx_out": "pop", "idle": "breathe"},
        {"texto": {"t": titulo, "estilo": "titulo", "size": size}, "x": 600, "y": 250, "in": desde + "+0.15", "out": hasta,
         "fx_in": "slide_left", "fx_out": "fade"},
    ]


def armar_doc(aqui, narracion, escenas, persistentes, estilos=None, audio=True, **extra):
    """Arma el escenas.json estándar y verifica que la narración sea el guion.txt palabra por palabra."""
    guion = " ".join(open(os.path.join(aqui, "guion.txt")).read().split())
    assert " ".join(narracion) == guion, "la narración no coincide con guion.txt"
    doc = {"cola": 1.4, "volumen_efectos": .5, "subtitulos": {"activos": True, "y": 1470, "size": 76},
           "estilos": dict(ESTILOS, **(estilos or {})), "narracion": [{"texto": t} for t in narracion],
           "persistentes": persistentes, "escenas": escenas}
    doc.update(extra)
    if audio:
        doc["audio_voz"] = "audio/voz.wav"
        doc["palabras_json"] = "audio/palabras.json"
    out = os.path.join(aqui, "escenas.json")
    json.dump(doc, open(out, "w"), ensure_ascii=False, indent=1)
    print("ok", out)
    return doc

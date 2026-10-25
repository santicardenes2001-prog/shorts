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
    "pregunta": {"size": 150, "color": "#FFD23F", "stroke": 12},
    "boton": {"size": 70, "color": "#FFFFFF", "box": "#E53935", "stroke": 0, "radius": 20, "pad": [44, 22], **_CAJA},
    "boton_hecho": {"size": 70, "color": "#FFFFFF", "box": "#8A8F9E", "stroke": 0, "radius": 20, "pad": [44, 22], **_CAJA},
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


def cortina(corte, asset="cortina_hojas", dur=.8, z=60, sfx="whoosh"):
    """Transición: una cortina (p. ej. de hojas) cruza la pantalla tapando el corte de escena.
    Va en "persistentes" (queda por encima de todo, también del encabezado). corte: "e4", etc."""
    return {"a": asset, "x": 1830, "y": 960, "z": z, "in": f"{corte}-{dur / 2:.2f}", "out": f"{corte}+{dur / 2:.2f}",
            "sfx": sfx, "vol": .8, "keys": [{"at": f"{corte}-{dur / 2:.2f}", "dur": dur, "x": -750, "ease": "linear"}]}


def suscripcion(fin, x=540, y=380, campana_x=860):
    """Cierre estándar: aparece "SUSCRIBIRSE", entra el cursor, hace clic (anillo + sonido), el botón
    pasa a "SUSCRIPTO" y suena la campanita. fin = referencia de cuando termina la pregunta ("b14>").
    Devuelve (elementos, sonidos) para sumar a la escena de cierre (dejar ~3,4 s de "cola")."""
    cx, cy = x + 120, y + 30   # dónde hace clic el cursor
    elementos = [
        {"texto": {"t": "SUSCRIBIRSE", "estilo": "boton"}, "x": x, "y": y, "in": f"{fin}+0.1", "fx_in": "pop",
         "out": f"{fin}+1.15", "z": 20, "keys": [{"at": f"{fin}+1.05", "dur": .1, "s": .92}]},
        {"texto": {"t": "SUSCRIPTO", "estilo": "boton_hecho"}, "x": x, "y": y, "in": f"{fin}+1.15", "z": 20, "sfx": "none",
         "fx_in": "none", "swaps": [], "keys": [{"at": f"{fin}+1.15", "dur": .25, "s": 1.0, "ease": "back"}], "s": .9},
        {"a": "anillo", "x": cx, "y": cy, "s": .2, "z": 22, "in": f"{fin}+1.1", "out": f"{fin}+1.6", "sfx": "none",
         "keys": [{"at": f"{fin}+1.1", "dur": .5, "s": .9, "alpha": 0, "ease": "out"}]},
        {"a": "cursor_mano", "x": 960, "y": y + 520, "s": .8, "z": 23, "in": f"{fin}+0.4", "fx_in": "fade", "sfx": "none",
         "keys": [{"at": f"{fin}+0.4", "dur": .6, "x": cx, "y": cy, "ease": "out"},
                  {"at": f"{fin}+1.05", "dur": .08, "s": .7}, {"at": f"{fin}+1.15", "dur": .1, "s": .8},
                  {"at": f"{fin}+1.6", "dur": .5, "x": 980, "y": y + 600, "alpha": 0, "ease": "in"}]},
        {"a": "campana", "x": campana_x, "y": y - 10, "s": .5, "z": 21, "in": f"{fin}+1.5", "fx_in": "pop", "sfx": "none",
         "idle": {"fx": "wiggle", "fuerza": 2.2}},
    ]
    sonidos = [{"at": f"{fin}+1.1", "s": "click"}, {"at": f"{fin}+1.5", "s": "ding"}]
    return elementos, sonidos


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

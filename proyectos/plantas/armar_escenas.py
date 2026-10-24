"""Genera escenas.json (python3 armar_escenas.py [--sin-audio]). Editá acá y volvé a correrlo."""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", ".."))
from comun import armar_doc, cartel, encabezado  # noqa: E402

narracion = [
    "Te cuento sobre 3 plantas extrañas!",
    "1. Hydnora africana (La flor subterránea):",
    "Esta extraña planta africana vive completamente bajo tierra y carece de hojas o clorofila,",
    "ya que es un parásito que absorbe nutrientes de las raíces de otras plantas.",
    "Solo emerge a la superficie su flor de aspecto alienígena,",
    "la cual se abre como tres gruesos labios de color carne",
    "y emite un fuerte olor a heces para atraer a los escarabajos peloteros,",
    "atrapándolos temporalmente en su interior para asegurar su polinización antes de liberarlos.",
    "2. Nepenthes rajah (La planta carnívora gigante):",
    "Originaria de las selvas de Borneo, esta espectacular planta carnívora posee trampas en forma de jarra tan inmensas",
    "que pueden contener hasta 3.5 litros de agua y más de 2 litros de jugos digestivos.",
    "Aunque su dieta principal se compone de insectos,",
    "es tan grande que se han documentado casos reales donde ha atrapado, ahogado y digerido por completo a pequeños vertebrados,",
    "como ranas, lagartijas, aves e incluso ratas.",
    "3. Welwitschia mirabilis (La planta inmortal):",
    "Esta planta desértica originaria de Namibia posee únicamente dos hojas que crecen continuamente a lo largo de toda su vida,",
    "las cuales son rasgadas por el viento dándole el aspecto de un monstruo tentacular.",
    "Es un auténtico fósil viviente capaz de sobrevivir en condiciones extremas de sequía extrema,",
    "y algunos ejemplares han llegado a vivir más de 1,500 años.",
]


def cae_en_jarra(a, x, y, at, s=1.0, flip=False):
    """Animal que aparece y a los 0,7 s cae dentro de la jarra (boca en 540, 860)."""
    return {"a": a, "x": x, "y": y, "s": s, "flip": flip, "in": at, "fx_in": "pop", "idle": "shake", "z": 6,
            "keys": [{"at": at + "+0.7", "dur": .5, "x": 540, "y": 870, "s": .15, "r": 200, "alpha": 0, "ease": "in",
                      "sfx": "glup"}]}


escenas = []

# ------------------------------------------------------------ 0. gancho
escenas.append({
    "nombre": "gancho", "beats": [0], "fondo": "fondo_burst_verde",
    "elementos": [
        {"texto": {"t": "3 PLANTAS\nEXTRAÑAS", "estilo": "titulo_verde", "size": 110}, "x": 540, "y": 330,
         "in": "b0:3", "fx_in": "pop", "fx_out": "suave", "idle": "breathe"},
        {"a": "hydnora_malo", "x": 230, "y": 920, "s": .72, "in": "b0:plantas", "fx_in": "pop", "idle": "sway"},
        {"a": "jarra_malo", "x": 540, "y": 880, "s": .62, "in": "b0:plantas+0.15", "fx_in": "pop", "idle": "sway"},
        {"a": "welwitschia_monstruo", "x": 850, "y": 930, "s": .44, "in": "b0:plantas+0.3", "fx_in": "pop",
         "idle": "wiggle"},
        {"a": "vos_explo", "x": 540, "y": 1330, "s": .55, "in": "b0+0.1", "fx_in": "jump", "idle": "breathe", "blink": True,
         "swaps": [{"at": "b0:extrañas", "a": "vos_explo_sorpresa", "fx": "punch"}]},
    ]})

# ------------------------------------------------------------ 1. Hydnora bajo tierra
escenas.append({
    "nombre": "hydnora_subsuelo", "beats": [1, 2, 3], "fondo": "fondo_subsuelo", "flash": True,
    "sonidos": [{"at": "b3:parásito", "s": "zumbido", "vol": .7}],
    "elementos": [
        {"a": "hydnora_rizoma_neutral", "x": 540, "y": 1000, "s": .9, "in": "b1:hydnora", "fx_in": "pop", "idle": "breathe",
         "keys": [{"at": "b3:raíces", "dur": .6, "x": 740}],
         "swaps": [{"at": "b3:parásito", "a": "hydnora_rizoma_malo", "fx": "punch"}]},
        {"a": "flecha_roja", "x": 540, "y": 790, "s": .35, "in": "b2:bajo", "fx_in": "pop", "idle": "work",
         "out": "b2:hojas", "fx_out": "pop"},
        {"a": "raices", "x": 270, "y": 700, "s": .9, "z": -2, "in": "b3:raíces", "fx_in": "grow", "dur_in": .6, "sfx": "none"},
        {"a": "euforbia_contento", "x": 270, "y": 705, "s": .8, "in": "b3:otras", "fx_in": "grow", "idle": "sway",
         "swaps": [{"at": "b3:plantas+0.2", "a": "euforbia_susto", "fx": "punch"}]},
        cartel("(LA FLOR SUBTERRÁNEA)", 540, 420, "b1:flor", size=60, out="b2"),
        cartel("BAJO TIERRA", 540, 1260, "b2:bajo", size=70, estilo="cartel_marron", out="b2:hojas"),
        {"a": "hoja", "x": 200, "y": 1270, "s": .55, "in": "b2:hojas", "fx_in": "pop", "out": "b3", "fx_out": "pop"},
        {"a": "prohibido", "x": 200, "y": 1270, "s": .6, "in": "b2:hojas+0.15", "fx_in": "pop", "sfx": "boing",
         "out": "b3", "fx_out": "pop"},
        cartel("NI HOJAS NI CLOROFILA", 610, 1270, "b2:clorofila", size=50, out="b3"),
        cartel("¡PARÁSITO!", 540, 1270, "b3:parásito", size=84, estilo="cartel_rojo", idle="pulse"),
        {"particulas": {"a": "nutriente", "n": 12, "semilla": 3, "zona": [430, 930, 600, 1080], "vx": [120, 200],
                        "vy": [-10, 10], "s": [.8, 1.3], "ondula": [8, .8]},
         "in": "b3:raíces+0.4", "fx_in": "fade", "z": 2},
    ]})

# ------------------------------------------------------------ 2. la flor emerge y se abre
escenas.append({
    "nombre": "hydnora_flor", "beats": [4, 5], "fondo": "fondo_sabana",
    "sonidos": [{"at": "b5:abre", "s": "whoosh_suave"}],
    "elementos": [
        {"a": "hydnora_0", "x": 540, "y": 1180, "s": 1.15, "in": "b4:emerge", "fx_in": "slide_up", "idle": "sway", "fase": 0,
         "seq": {"frames": ["hydnora_0", "hydnora_1", "hydnora_2", "hydnora_3"], "at": "b5:abre", "dur": 1.0}},
        {"a": "vos_explo", "x": 170, "y": 1330, "s": .45, "in": "b4", "fx_in": "jump", "idle": "breathe", "blink": True, "fase": 0,
         "swaps": [{"at": "b4:alienígena", "a": "vos_explo_sorpresa", "fx": "punch"}]},
        cartel("¿ALIENÍGENA?", 540, 470, "b4:alienígena", size=80, estilo="cartel_violeta", r=-4, out="b5:labios",
               fx_out="pop"),
        cartel("3 LABIOS GRUESOS", 540, 470, "b5:labios", size=72, estilo="cartel_rosa", out="b5:carne"),
        cartel("COLOR CARNE", 540, 470, "b5:carne", size=80, estilo="cartel_rosa", idle="pulse"),
    ]})

# ------------------------------------------------------------ 3. olor, escarabajos y polinización
escenas.append({
    "nombre": "hydnora_escarabajos", "beats": [6, 7], "fondo": "fondo_sabana",
    "sonidos": [{"at": "b6:heces", "s": "boing"}, {"at": "b7:atrapándolos", "s": "glup"},
                {"at": "b7:polinización", "s": "brillo", "vol": .7}, {"at": "b7:liberarlos", "s": "pop"}],
    "elementos": [
        {"a": "hydnora_3", "x": 540, "y": 1180, "s": 1.15, "idle": "sway", "fase": 0,
         "swaps": [{"at": "b7:atrapándolos+0.4", "a": "hydnora_llena", "fx": "punch"},
                   {"at": "b7:liberarlos", "a": "hydnora_contento", "fx": "punch"}]},
        {"a": "olor", "x": 450, "y": 760, "s": .6, "in": "b6:olor", "fx_in": "fade", "idle": "sway"},
        {"a": "olor", "x": 640, "y": 750, "s": .55, "in": "b6:olor+0.15", "fx_in": "fade", "idle": "sway", "flip": True},
        {"a": "vos_explo_sorpresa", "x": 170, "y": 1330, "s": .45, "idle": "breathe", "blink": True, "fase": 0,
         "swaps": [{"at": "b6:heces", "a": "vos_explo_asco", "fx": "punch"}]},
        cartel("OLOR A HECES", 540, 470, "b6:heces", size=80, estilo="cartel_marron", out="b6:escarabajos"),
        cartel("ESCARABAJOS PELOTEROS", 540, 470, "b6:escarabajos", size=62, out="b7"),
        {"a": "bola_estiercol", "x": 760, "y": 1200, "s": .55, "in": "b6:escarabajos", "fx_in": "slide_left", "idle": "bob"},
        {"a": "escarabajo", "x": 870, "y": 1200, "s": .6, "flip": True, "in": "b6:escarabajos", "fx_in": "slide_left",
         "idle": "work", "keys": [{"at": "b7:atrapándolos", "dur": .6, "x": 540, "y": 900, "s": .15, "alpha": 0, "ease": "in"}]},
        {"a": "bola_estiercol", "x": 820, "y": 1330, "s": .45, "in": "b6:peloteros", "fx_in": "slide_left", "idle": "bob"},
        {"a": "escarabajo", "x": 920, "y": 1330, "s": .5, "flip": True, "in": "b6:peloteros", "fx_in": "slide_left",
         "idle": "work", "sfx": "none",
         "keys": [{"at": "b7:atrapándolos+0.15", "dur": .6, "x": 540, "y": 900, "s": .15, "alpha": 0, "ease": "in"}]},
        cartel("¡ATRAPADOS!", 540, 470, "b7:atrapándolos", size=84, estilo="cartel_rojo", out="b7:polinización"),
        cartel("POLINIZACIÓN", 540, 470, "b7:polinización", size=80, estilo="cartel_amarillo"),
        {"particulas": {"a": "polen", "n": 22, "semilla": 4, "zona": [300, 640, 780, 1100], "vy": [-40, -10],
                        "s": [.7, 1.3], "titila": .5, "ondula": [20, .5]},
         "in": "b7:polinización", "fx_in": "fade", "z": 8},
        {"a": "escarabajo_susto", "x": 540, "y": 900, "s": .5, "in": "b7:liberarlos", "fx_in": "pop", "sfx": "none", "z": 9,
         "keys": [{"at": "b7:liberarlos", "dur": .5, "x": 820, "y": 1250, "ease": "out"}], "idle": "work"},
    ]})

# ------------------------------------------------------------ 4. Nepenthes: presentación y tamaño
escenas.append({
    "nombre": "nepenthes_intro", "beats": [8, 9], "fondo": "fondo_selva", "flash": True,
    "sonidos": [{"at": "b9:inmensas", "s": "boing"}],
    "elementos": [
        {"a": "jarra_neutral", "x": 540, "y": 1300, "s": 1.0, "in": "b8:nepenthes", "fx_in": "grow", "idle": "sway", "fase": 0,
         "swaps": [{"at": "b8:carnívora", "a": "jarra_malo", "fx": "punch"}],
         "keys": [{"at": "b9:inmensas", "dur": .5, "s": 1.12, "ease": "back"}]},
        cartel("(LA PLANTA CARNÍVORA GIGANTE)", 540, 470, "b8:planta", size=54, out="b9"),
        cartel("BORNEO", 540, 470, "b9:borneo", size=84, estilo="cartel_verde", out="b9:trampas"),
        {"a": "vos_explo", "x": 150, "y": 1330, "s": .4, "in": "b9:trampas", "fx_in": "jump", "idle": "breathe", "blink": True,
         "fase": 0,
         "swaps": [{"at": "b9:inmensas", "a": "vos_explo_sorpresa", "fx": "punch"}]},
        cartel("¡ENORMES!", 540, 470, "b9:inmensas", size=86, estilo="cartel_amarillo", idle="pulse"),
    ]})

# ------------------------------------------------------------ 5. qué tiene adentro
escenas.append({
    "nombre": "nepenthes_liquido", "beats": [10], "fondo": "fondo_selva",
    "sonidos": [{"at": "b10:litros", "s": "glup"}, {"at": "b10:jugos", "s": "glup"}],
    "elementos": [
        {"a": "jarra_corte_malo", "x": 540, "y": 1300, "s": 1.12, "idle": "sway", "fase": 0, "out": "esc>-0.06"},
        {"a": "jarra_malo", "x": 540, "y": 1300, "s": 1.12, "idle": "sway", "fase": 0, "z": 1,
         "keys": [{"at": "b10:contener", "dur": .7, "alpha": 0}, {"at": "esc>-0.5", "dur": .45, "alpha": 1}]},
        {"particulas": {"a": "burbuja", "n": 10, "semilla": 2, "zona": [400, 1170, 680, 1300], "vy": [-50, -25],
                        "s": [.5, 1], "ondula": [6, .6]}, "in": "b10:agua", "fx_in": "fade", "out": "esc>-0.4",
         "fx_out": "fade", "z": 3},
        {"a": "botella", "x": 880, "y": 1150, "s": .6, "in": "b10:litros", "fx_in": "pop", "idle": "bob"},
        cartel("3.5 L DE AGUA", 540, 450, "b10:litros", size=78, estilo="cartel_celeste"),
        cartel("+ 2 L DE JUGOS DIGESTIVOS", 540, 580, "b10:jugos", size=54, estilo="cartel_verde"),
        {"a": "vos_explo_sorpresa", "x": 150, "y": 1330, "s": .4, "idle": "breathe", "blink": True, "fase": 0},
    ]})

# ------------------------------------------------------------ 6. qué come
escenas.append({
    "nombre": "nepenthes_presas", "beats": [11, 12, 13], "fondo": "fondo_selva",
    "sonidos": [{"at": "b11:insectos", "s": "mosca"}, {"at": "b12:atrapado", "s": "golpe", "vol": .6},
                {"at": "b13:ratas+1.3", "s": "boing"}],
    "elementos": [
        {"a": "jarra_malo", "x": 540, "y": 1300, "s": 1.12, "idle": "sway", "fase": 0,
         "keys": [{"at": "b12:grande", "dur": .5, "s": 1.2, "ease": "back"}],
         "swaps": [{"at": "b13:ratas+1.3", "a": "jarra_contento", "fx": "punch"}]},
        {"particulas": {"a": "mosca", "n": 10, "semilla": 3, "zona": [320, 640, 760, 900], "vx": [-40, 40], "vy": [-30, 30],
                        "s": [.35, .55], "ondula": [40, .7]}, "in": "b11:insectos", "fx_in": "fade", "out": "b12:vertebrados",
         "fx_out": "fade", "z": 5},
        cartel("CASOS REALES", 540, 470, "b12:casos", size=78, out="b12:atrapado"),
        cartel("¡ATRAPADO!", 540, 470, "b12:atrapado", size=84, estilo="cartel_rojo", out="b12:ahogado"),
        cartel("¡AHOGADO!", 540, 470, "b12:ahogado", size=84, estilo="cartel_celeste", out="b12:digerido"),
        cartel("¡DIGERIDO!", 540, 470, "b12:digerido", size=84, estilo="cartel_verde", out="b13"),
        {"a": "vos_explo_sorpresa", "x": 150, "y": 1330, "s": .4, "idle": "breathe", "blink": True, "fase": 0,
         "swaps": [{"at": "b12:vertebrados", "a": "vos_explo_miedo", "fx": "punch"}]},
        cae_en_jarra("rana", 830, 650, "b13:ranas"),
        cae_en_jarra("lagartija", 250, 650, "b13:lagartijas", s=.9),
        cae_en_jarra("ave", 830, 650, "b13:aves"),
        cae_en_jarra("rata", 250, 650, "b13:ratas"),
    ]})

# ------------------------------------------------------------ 7. Welwitschia: presentación y hojas
escenas.append({
    "nombre": "welwitschia_intro", "beats": [14, 15], "fondo": "fondo_desierto", "flash": True,
    "elementos": [
        {"a": "welwitschia_0", "x": 540, "y": 1300, "s": 1.05, "in": "b14:welwitschia", "fx_in": "grow", "idle": "breathe", "fase": 0,
         "seq": {"frames": [f"welwitschia_{i}" for i in range(5)], "at": "b15:crecen", "dur": 2.6, "ease": "linear"}},
        cartel("(LA PLANTA INMORTAL)", 540, 470, "b14:planta", size=64, out="b15"),
        cartel("NAMIBIA", 540, 470, "b15:namibia", size=84, estilo="cartel_naranja", out="b15:dos"),
        cartel("SOLO 2 HOJAS", 540, 470, "b15:dos", size=84, estilo="cartel_verde", out="b15:crecen"),
        {"a": "flecha_roja", "x": 330, "y": 960, "s": .35, "in": "b15:hojas", "fx_in": "pop", "idle": "work",
         "out": "b15:crecen", "fx_out": "pop"},
        {"a": "flecha_roja", "x": 750, "y": 960, "s": .35, "in": "b15:hojas+0.1", "fx_in": "pop", "idle": "work", "sfx": "none",
         "out": "b15:crecen", "fx_out": "pop"},
        cartel("¡NUNCA DEJAN DE CRECER!", 540, 470, "b15:continuamente", size=60, estilo="cartel_amarillo", idle="pulse"),
    ]})

# ------------------------------------------------------------ 8. el viento la hace un monstruo
escenas.append({
    "nombre": "welwitschia_monstruo", "beats": [16], "fondo": "fondo_desierto",
    "sonidos": [{"at": "b16:viento", "s": "viento"}, {"at": "b16:monstruo", "s": "zumbido"}],
    "camara": {"keys": [{"at": "b16:monstruo", "dur": .6, "zoom": 1.12, "y": 1050, "ease": "back"}]},
    "elementos": [
        {"a": "vos_explo", "x": 180, "y": 1010, "s": .38, "z": -1, "in": "b16", "fx_in": "jump", "idle": "breathe",
         "blink": True, "fase": 0, "swaps": [{"at": "b16:monstruo", "a": "vos_explo_miedo", "fx": "punch"}]},
        {"a": "welwitschia_4", "x": 540, "y": 1300, "s": 1.05, "idle": "breathe", "fase": 0,
         "swaps": [{"at": "b16:rasgadas", "a": "welwitschia_rasgada", "fx": "punch"},
                   {"at": "b16:monstruo", "a": "welwitschia_monstruo", "fx": "punch"}],
},
        {"particulas": {"a": "viento", "n": 10, "semilla": 3, "zona": [-400, 500, 1480, 1300], "vx": [1500, 2100],
                        "s": [.6, 1.1], "alpha": [.4, .8]}, "in": "b16:rasgadas", "fx_in": "fade", "z": 8},
        cartel("¡MONSTRUO TENTACULAR!", 540, 560, "b16:monstruo", size=64, estilo="cartel_violeta", idle="shake"),
    ]})

# ------------------------------------------------------------ 9. fósil viviente, sequía y 1500 años
escenas.append({
    "nombre": "welwitschia_final", "beats": [17, 18], "fondo": "fondo_desierto",
    "camara": {"keys": [{"at": "esc", "dur": .001, "zoom": 1.12, "y": 1050},
                        {"at": "b17+0.2", "dur": .8, "zoom": 1.0, "y": 960}]},
    "sonidos": [{"at": "b18:años", "s": "brillo"}, {"at": "b18:años+0.4", "s": "ding", "vol": .5}],
    "elementos": [
        {"a": "welwitschia_monstruo", "x": 540, "y": 1300, "s": 1.05, "idle": "breathe", "fase": 0,
         "swaps": [{"at": "b17:fósil", "a": "welwitschia_rasgada", "fx": "punch"},
                   {"at": "b18:años", "a": "welwitschia_contento", "fx": "punch"}]},
        {"a": "vos_explo_miedo", "x": 180, "y": 1010, "s": .38, "z": -1, "idle": "breathe", "blink": True, "fase": 0,
         "swaps": [{"at": "b18:vivir", "a": "vos_explo_pulgar", "fx": "punch"}]},
        {"a": "dino", "x": 860, "y": 1010, "s": .55, "z": -1, "in": "b17:fósil", "fx_in": "slide_left", "idle": "bob",
         "out": "b17:sobrevivir", "fx_out": "slide_right"},
        cartel("FÓSIL VIVIENTE", 540, 470, "b17:fósil", size=80, estilo="cartel_verde", out="b17:sequía"),
        {"a": "termometro_10", "x": 160, "y": 1000, "s": .5, "z": -1, "in": "b17:condiciones", "fx_in": "pop", "idle": "shake",
         "out": "b18:años", "fx_out": "pop"},
        {"a": "gota_agua", "x": 880, "y": 820, "s": .6, "in": "b17:sequía", "fx_in": "pop", "out": "b18:años", "fx_out": "pop"},
        {"a": "prohibido", "x": 880, "y": 830, "s": .55, "in": "b17:sequía+0.15", "fx_in": "pop", "sfx": "boing",
         "out": "b18:años", "fx_out": "pop"},
        cartel("SEQUÍA EXTREMA", 540, 470, "b17:sequía", size=80, estilo="cartel_naranja", out="b18:1500"),
        cartel("+1500 AÑOS", 540, 470, "b18:1500", size=100, estilo="cartel_amarillo", idle="pulse"),
        {"a": "torta", "x": 540, "y": 1050, "s": .55, "in": "b18:años", "fx_in": "drop", "sfx": "none"},
    ]})


armar_doc(
    AQUI, narracion, escenas,
    persistentes=(encabezado(1, "Hydnora africana", "b1", "e4")
                  + encabezado(2, "Nepenthes rajah", "b8", "e7")
                  + encabezado(3, "Welwitschia mirabilis", "b14", "fin", size=66)),
    estilos={"titulo_verde": {"size": 100, "color": "#FFFFFF", "stroke": 14, "stroke_color": "#1E5A2A"}},
    audio="--sin-audio" not in sys.argv)

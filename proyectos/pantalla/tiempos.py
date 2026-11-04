"""Guion por bloques y tiempos por palabra del short "¿Cómo funciona la pantalla de tu celular?"."""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, ROOT)
import motor  # noqa: E402

NARRACION = [
    "Desde que apareció esta imagen, tu pantalla ya la dibujó de nuevo más de 100 veces.",            # b0  gancho
    "No lo notas porque no cambia de golpe: la redibuja fila por fila, de arriba abajo, "
    "más rápido de lo que tu ojo alcanza a seguir.",                                                     # b1  barrido
    "Cada fila es una hilera de puntitos de solo tres colores: rojo, verde y azul.",                     # b2  zoom
    "Todo lo que ves sale de prenderlos más fuerte o más suave.",                                        # b3  perillas
    "Son tan chiquitos que tus ojos no los separan: los ven mezclados.",                                 # b4  zoom out
    "Mira este amarillo.",                                                                               # b5
    "En tu pantalla no hay ni una luz de este color: son puntitos rojos y verdes prendidos juntos.",     # b6
    "El amarillo lo está inventando tu cerebro.",                                                        # b7
    "Pero tu pantalla no solo te muestra cosas. También te siente.",                                     # b8  bisagra
    "Justo debajo del vidrio hay una cuadrícula de cables transparentes, "
    "con electricidad recorriéndola todo el tiempo.",                                                    # b9  capas
    "Tu dedo conduce la electricidad, igual que un cable.",                                              # b10
    "Cuando lo apoyas, se lleva un poco, y el celular, que revisa la cuadrícula más de 100 veces "
    "por segundo, nota en qué punto le falta.",                                                          # b11
    "Pruébalo tú mismo: entra a la caja de comentarios y escribe lo que sea.",                           # b12
    "Cada vez que tu dedo toca una letra, le roba un poco de electricidad a un cruce de la cuadrícula.",  # b13
    "El celular encuentra ese punto, sabe qué letra está ahí, y en el siguiente redibujo "
    "prende los puntitos que la forman.",                                                                # b14
    "Todo eso pasa con cada letra, en una fracción de segundo.",                                         # b15
    "¿Te interesó nuestro video? Róbale un poco de electricidad al botón de suscribirse.",              # b16
]

COLA = 1.9


def palabras():
    ww = json.load(open(os.path.join(AQUI, "audio", "palabras.json")))
    return motor.align_times([{"texto": t} for t in NARRACION], ww)


class Tiempos:
    def __init__(self):
        self.words = palabras()
        self.total = self.words[-1][-1]["end"] + COLA

    def b(self, i, palabra=None, fin=False, n=0):
        ws = self.words[i]
        if palabra is None:
            return ws[-1]["end"] if fin else ws[0]["start"]
        objetivo = motor.norm(palabra)
        cand = [w for w in ws if w["n"] == objetivo] or [w for w in ws if w["n"].startswith(objetivo)]
        if not cand:
            raise ValueError(f"no está {palabra!r} en el bloque {i}")
        w = cand[min(n, len(cand) - 1)]
        return w["end"] if fin else w["start"]


if __name__ == "__main__":
    T = Tiempos()
    for i, ws in enumerate(T.words):
        print(f"b{i:<2} {ws[0]['start']:6.2f}-{ws[-1]['end']:6.2f}  "
              + " ".join(f"{w['w']}@{w['start']:.2f}" for w in ws))
    print("total", round(T.total, 2))

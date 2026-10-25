"""Revisor automático de un escenas.json: busca los errores que ya se corrigieron alguna vez.

    python3 revisar.py proyectos/plantas/escenas.json

Cada chequeo sale de una corrección real (ver PAUTAS.md). Avisa, no corrige:
  - carteles que se pisan entre sí o con el título del número
  - textos en la zona de botones (x>960, 1000<y<1650), sobre los subtítulos o fuera de cuadro
  - cortes de escena donde un mismo personaje/objeto salta un poco (cara, posición o tamaño): un cambio
    grande se lee como re-encuadre y no se avisa; uno chico parece un error
  - carteles que desaparecen de golpe en un corte (sin fx_out)
  - ruido de fondo continuo en efectos + ambiente (se escucha como un siseo debajo de la voz)
  - personajes/objetos que desaparecen de golpe en un corte cuando el lugar (fondo) sigue igual
    (no se revisan los cortes tapados por una cortina ni las escenas con "transicion": "...")
  - luces (halo_*, rayo_luz, destello) sobre un personaje que se mueve, sin "sigue": quedan separadas
    de su fuente (señuelo, lámpara); si la luz se suelta a propósito (una nube que queda), "suelta": true
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor  # noqa: E402
from motor import H, RS, W, Particles, _IMG_REG, anchor_of, img_key  # noqa: E402

PASO = 0.1
ZONA_BOTONES = (960, 1000, W, 1650)
SUBTITULOS = (0, 1420, W, 1525)


def familia(asset):
    """"jarra_malo" -> "jarra", "vos_explo_miedo" -> "vos": mismo personaje/objeto con otra cara."""
    if not isinstance(asset, str):
        return None
    if asset.startswith(("capa_", "fondo_")):   # capas y fondos usados como elemento: cada uno es único
        return asset
    return asset.split("_")[0]


def caja(el, st, cam=None):
    """Rectángulo aproximado (sin rotación) de un elemento en pantalla, o None si no se ve."""
    asset = st["asset"]
    src = _IMG_REG[img_key(asset)]
    res = 1.0 if src.size == (W, H) else RS
    w = src.width * abs(st["s"] * st["sx"]) / res
    h = src.height * abs(st["s"] * st["sy"]) / res
    if st["alpha"] < .5 or w < 2 or h < 2:
        return None
    ax, ay = anchor_of(el.sp, asset)
    x0, y0 = st["x"] - ax * w, st["y"] - ay * h
    box = [x0, y0, x0 + w, y0 + h]
    if cam is not None:
        c = cam.state(st["_t"])
        z = max(c["zoom"], 1.0)
        cx = motor.clamp(c["x"], W / z / 2, W - W / z / 2)
        cy = motor.clamp(c["y"], H / z / 2, H - H / z / 2)
        box = [(box[0] - cx) * z + W / 2, (box[1] - cy) * z + H / 2, (box[2] - cx) * z + W / 2, (box[3] - cy) * z + H / 2]
    return box


def cruza(a, b, margen=0):
    return a[0] < b[2] - margen and b[0] < a[2] - margen and a[1] < b[3] - margen and b[1] < a[3] - margen


def es_texto(el):
    return isinstance(el.asset, dict)


LUCES = ("halo_", "rayo_luz", "destello")
MOVIMIENTO = {"float", "bob", "sway", "wiggle", "work", "vaiven", "shake", "spin"}   # "breathe" casi no mueve


def es_luz(el):
    return isinstance(el.asset, str) and el.asset.startswith(LUCES) and not el.sigue and not el.sp.get("suelta")


def se_mueve(el):
    return (any(i["fx"] in MOVIMIENTO for i in el.idle)
            or any(k in ("x", "y", "r", "s") for key in el.keys for k in key))


def nombre(el):
    return ("«" + el.asset["t"].replace("\n", " ") + "»") if es_texto(el) else el.asset


def revisar(path):
    proj = motor.Project(path)
    tl = proj.tl
    avisos = {}

    def avisar(clave, t):
        r = avisos.setdefault(clave, [t, t])
        r[1] = t

    t = 0.0
    while t < tl.total:
        si = proj.scene_at(t)
        sc = proj.scenes[si]
        vis = []
        for el in sc["els"] + proj.persist:
            if isinstance(el, Particles) or not el.active(t):
                continue
            st = el.state(t)
            st["_t"] = t
            if es_luz(el) and st["alpha"] > .05:
                st["alpha"] = 1.0   # un halo tenue igual se ve: también se revisa
            b = caja(el, st, sc["cam"] if el in sc["els"] else None)
            if b:
                vis.append((el, b))
        textos = [(el, b) for el, b in vis if es_texto(el)]
        for el, b in vis:
            if es_luz(el):
                # la fuente de la luz es su ancla (centro del halo, origen del haz), no el centro del dibujo
                ax, ay = anchor_of(el.sp, el.asset)
                px, py = b[0] + ax * (b[2] - b[0]), b[1] + ay * (b[3] - b[1])
                for e2, b2 in vis:
                    if e2 is not el and not es_texto(e2) and not es_luz(e2) and se_mueve(e2) \
                            and not str(e2.asset).startswith(("capa", "fondo", "cortina")) \
                            and b2[0] <= px <= b2[2] and b2[1] <= py <= b2[3] and e2.z < el.z + 50:
                        avisar(f"[{sc.get('nombre', si)}] {el.asset} está sobre {e2.asset}, que se mueve, pero no lo "
                               f"sigue: usar \"sigue\": {{\"id\", \"punto\"}} (o \"suelta\": true)", t)
                        break
        pers = [(el, b) for el, b in textos if el in proj.persist]
        for i, (e1, b1) in enumerate(textos):
            esc = sc.get("nombre", si)
            if t < e1.tin + e1.dur_in or t > e1.tout - e1.dur_out:
                continue   # entrando o saliendo: puede venir de afuera a propósito
            if e1 not in proj.persist:
                for e2, b2 in textos[i + 1:]:
                    if e2 not in proj.persist and cruza(b1, b2, 4):
                        avisar(f"[{esc}] carteles que se pisan: {nombre(e1)} y {nombre(e2)}", t)
                for e2, b2 in pers:
                    if cruza(b1, b2, 4):
                        avisar(f"[{esc}] {nombre(e1)} pisa el título {nombre(e2)}", t)
                if cruza(b1, ZONA_BOTONES):
                    avisar(f"[{esc}] {nombre(e1)} entra en la zona de botones (x>960, y 1000-1650)", t)
                if cruza(b1, SUBTITULOS):
                    avisar(f"[{esc}] {nombre(e1)} tapa los subtítulos", t)
            if b1[0] < 0 or b1[2] > W or b1[1] < 0 or b1[3] > H:
                avisar(f"[{esc}] {nombre(e1)} se sale del cuadro", t)
        t += PASO

    # cortes de escena
    for i in range(1, len(proj.scenes)):
        tc = tl.scene_start[i]
        antes, despues = proj.scenes[i - 1], proj.scenes[i]
        # corte declarado a propósito ("transicion": "primer plano", etc.): no se revisa la continuidad
        if despues.get("transicion"):
            continue
        # una cortina de transición tapa el corte: ahí los saltos no se ven
        if any(isinstance(p.asset, str) and p.asset.startswith("cortina") and p.tin <= tc <= p.tout for p in proj.persist):
            continue

        def en_pantalla(el, st):
            st["_t"] = tc
            return caja(el, st) is not None and not (lambda b: b[2] < 0 or b[0] > W or b[3] < 0 or b[1] > H)(caja(el, st))
        a_vis = []
        for el in antes["els"]:
            if isinstance(el, Particles) or not el.active(tc - 0.02):
                continue
            st = el.state(tc)   # mismo instante a los dos lados del corte (la salida ya terminó)
            if es_texto(el):
                if el.fx_out == "none" and st["alpha"] > .5:
                    avisar(f"[{antes.get('nombre', i - 1)}] {nombre(el)} desaparece de golpe en el corte "
                           f"(poné fx_out o un out antes del final)", tc)
            elif st["alpha"] > .5 and en_pantalla(el, st):
                st["_salida"] = el.fx_out
                st["_alto"] = _IMG_REG[img_key(st["asset"])].height / RS
                a_vis.append(st)
        d_vis = []
        for el in despues["els"]:
            if isinstance(el, Particles) or es_texto(el) or not el.active(tc + 0.02):
                continue
            st = el.state(tc)
            if st["alpha"] > .5 and en_pantalla(el, st):
                d_vis.append(st)
        mismo_lugar = antes["fondo"] == despues["fondo"] and not despues.get("flash")
        for s0 in a_vis:
            mismos = [st for st in d_vis if familia(st["asset"]) == familia(s0["asset"])]
            if not mismos:
                if mismo_lugar and s0.get("_salida") == "none" and s0["s"] * s0.get("_alto", 0) > 70:
                    avisar(f"[corte {antes.get('nombre', i - 1)} → {despues.get('nombre', i)}] {s0['asset']} "
                           f"desaparece de golpe (el lugar sigue igual: que salga animado o siga en la escena)", tc)
                continue
            dist = lambda st: abs(st["x"] - s0["x"]) + abs(st["y"] - s0["y"])
            if any(st["asset"] == s0["asset"] and dist(st) <= 12 and abs(st["s"] - s0["s"]) <= .03 * s0["s"] for st in mismos):
                continue   # sigue igual del otro lado
            st = min(mismos, key=dist)
            d, ds = dist(st), abs(st["s"] - s0["s"]) / max(st["s"], s0["s"])
            if d > 150 or ds > .25:
                continue   # re-encuadre grande: se lee como corte a propósito
            cambios = []
            if s0["asset"] != st["asset"]:
                cambios.append(f"dibujo {s0['asset']} → {st['asset']}")
            if d > 12:
                cambios.append(f"posición ({s0['x']:.0f},{s0['y']:.0f}) → ({st['x']:.0f},{st['y']:.0f})")
            if ds > .03:
                cambios.append(f"tamaño {s0['s']:.2f} → {st['s']:.2f}")
            if cambios:
                avisar(f"[corte {antes.get('nombre', i - 1)} → {despues.get('nombre', i)}] {familia(st['asset'])} "
                       f"salta: " + ", ".join(cambios), tc)

    # ruido de fondo: el piso de efectos + ambiente tiene que quedar muy por debajo de la voz
    import numpy as np
    pista = proj.sfx_track()
    h = motor.SR * 30 // 1000
    k = len(pista) // h
    niveles = 20 * np.log10(np.sqrt((pista[:k * h].reshape(k, h) ** 2).mean(1)) + 1e-9)
    piso = float(np.percentile(niveles, 10))
    if piso > -58:
        avisar(f"ruido de fondo continuo en efectos/ambiente: piso {piso:.0f} dB (tiene que quedar por debajo de -58 dB)", 0.0)

    if not avisos:
        print("sin avisos")
        return 0
    for clave, (t0, t1) in sorted(avisos.items(), key=lambda kv: kv[1][0]):
        rango = f"{t0:6.1f}s" if t1 - t0 < PASO / 2 else f"{t0:6.1f}-{t1:.1f}s"
        print(f"{rango}  {clave}")
    print(f"{len(avisos)} avisos")
    return len(avisos)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("escenas")
    revisar(ap.parse_args().escenas)

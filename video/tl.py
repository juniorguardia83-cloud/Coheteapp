# Línea de tiempo compartida por render.py y audio.py (todo sale de voz.json)
import json, os
WD = os.environ.get('WD', os.path.expanduser('~/cohete_video'))
TL = json.load(open(WD + '/voz.json'))
DURATION = float(TL['duration']); LINES = TL['lines']
S = [0.0] + [max(0.0, l['t0'] - 0.05) for l in LINES[1:]]      # inicio de cada escena (una por línea de voz)
E = S[1:] + [DURATION]
sA, sB, sC, sD, sE, sF, sG, sH, sI = S
kD = min(1.0, (E[3] - sD) / 3.4)                                # si la escena D es corta, se comprimen sus eventos
lenE = E[4] - sE
JOIN = [sB + 0.35 + 0.55 * k for k in range(5)]                  # entran 5 espectadores (escena B)
TU_JOIN = sC + 0.2                                               # entra "TU NOMBRE" (escena C)
LEAVE0 = sD + 0.1 * kD                                           # el primero de la fila va al arco
GATE0 = sD + 0.8 * kD
SCAN = (sD + 0.8 * kD, sD + 2.0 * kD)                            # revisión de la skin
OK0 = SCAN[1]
LEAVE1 = sE + 0.0                                                # el segundo sale hacia el arco
DOOR0 = sE + 0.2                                                 # el primero sube al cohete
DOOR1 = sE + 1.05                                                # el segundo sube al cohete
LAUNCH = sE + 0.68 * lenE
CD = [LAUNCH - 1.5, LAUNCH - 1.0, LAUNCH - 0.5]                  # 3, 2, 1
FLIGHT0 = sF                                                     # empieza el viaje en el mapa
ARRIVE = sG + 0.9                                                # llega a Marte
def line_at(t):
    for i, l in enumerate(LINES):
        if l['t0'] - 0.05 <= t <= l['t1'] + 0.35: return i
    return None

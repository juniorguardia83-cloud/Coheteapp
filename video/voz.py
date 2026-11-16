# Genera las voces del video (edge-tts) y la línea de tiempo de 30 s -> voz.json
import asyncio, json, os, subprocess, sys, edge_tts

WD = os.path.expanduser('~/cohete_video'); os.makedirs(WD, exist_ok=True)
TARGET, LEAD, MIN_TAIL = 30.0, 0.06, 0.9
# (quién, texto en pantalla, texto para la voz: mismas palabras, pronunciación más natural)
LINES = [
 ('J', '¡Entra a mi live y tu skin sube a un cohete!', '¡Entra a mi láiv y tu eskin sube a un cohete!'),
 ('J', 'Apenas entras, aparece tu personaje con tu nombre.', 'Apenas entras, aparece tu personaje con tu nombre.'),
 ('D', '¡Mira, ya estoy en la fila!', '¡Mira, ya estoy en la fila!'),
 ('J', 'Dos policías revisan tu skin antes de subir.', 'Dos policías revisan tu eskin antes de subir.'),
 ('J', 'Subes al cohete, cuenta regresiva, ¡y despegas!', 'Subes al cohete, cuenta regresiva, ¡y despegas!'),
 ('J', 'Cada cohete viaja a un planeta distinto.', 'Cada cohete viaja a un planeta distinto.'),
 ('D', '¡Yo quiero ir a Marte!', '¡Yo quiero ir a Marte!'),
 ('J', 'Entra ahora al live, y que tu nombre sea el siguiente.', 'Entra ahora al láiv, y que tu nombre sea el siguiente.'),
 ('J', '¡Te espero!', '¡Te espero!'),
]
VOICE = {'J': ('es-MX-JorgeNeural', 0, '+0Hz'), 'D': ('es-MX-DaliaNeural', 2, '+3Hz')}  # (voz, extra de velocidad, tono)

def dur(f):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).decode())

async def gen(i, who, spoken, base):
    vname, extra, pitch = VOICE[who]
    rate = '%+d%%' % (base + extra)
    out = '%s/l%d.mp3' % (WD, i)
    com = edge_tts.Communicate(spoken, vname, rate=rate, pitch=pitch, boundary='WordBoundary')
    pal = []
    with open(out, 'wb') as f:
        async for ch in com.stream():
            if ch['type'] == 'audio': f.write(ch['data'])
            elif ch['type'] == 'WordBoundary':
                pal.append((ch['text'], ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7))
    return pal, dur(out)

async def run(base):
    res = await asyncio.gather(*[gen(i, w, sp, base) for i, (w, tx, sp) in enumerate(LINES)])
    return res

def build(base):
    res = asyncio.run(run(base))
    speech = sum(d for _, d in res)
    gap_total = TARGET - LEAD - MIN_TAIL - speech
    gap = gap_total / (len(LINES) - 1)
    return res, speech, gap

base = 4
for base in (4, 8, 12, 16, 20, 24):
    res, speech, gap = build(base)
    print('velocidad +%d%%: voz %.2fs, pausa disponible %.2fs' % (base, speech, gap), flush=True)
    if gap >= 0.25: break
gap = min(gap, 0.85)
t = LEAD; lines = []
for i, ((who, tx, sp), (pal, d)) in enumerate(zip(LINES, res)):
    words = [[w, round(t + a, 3), round(t + b, 3)] for (w, a, b) in pal]
    lines.append({'id': i + 1, 'who': who, 'text': tx, 'spoken': sp, 't0': round(t, 3), 't1': round(t + d, 3), 'words': words})
    t += d + gap
out = {'duration': TARGET, 'lines': lines}
json.dump(out, open(WD + '/voz.json', 'w'), ensure_ascii=False, indent=1)
print('fin de la última línea: %.2fs (pausa %.2fs)' % (lines[-1]['t1'], gap))
for l in lines:
    n1, n2 = len(l['text'].split(' ')), len(l['words'])
    print(l['id'], l['who'], '%.2f-%.2f' % (l['t0'], l['t1']), 'palabras pantalla/voz: %d/%d' % (n1, n2))

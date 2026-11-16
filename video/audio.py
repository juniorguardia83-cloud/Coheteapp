# Audio del video: voces (mp3) + efectos y musica sinteticos con numpy -> audio.wav
import os, sys, subprocess, numpy as np, wave
import tl
from tl import *
SR = 22050; N = int(DURATION * SR) + SR
rng = np.random.default_rng(3)
def T(d): return np.arange(int(d * SR)) / SR
mix_fx = np.zeros(N); mix_mu = np.zeros(N); mix_vo = np.zeros(N)
def put(buf, x, t0, g=1.0):
    i = int(t0 * SR)
    if i < 0: x = x[-i:]; i = 0
    n = min(len(x), len(buf) - i)
    if n > 0: buf[i:i + n] += x[:n] * g
def env(n, a=0.005, r=0.1):
    e = np.ones(n); na = max(1, int(a * SR)); nr = max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr) if nr <= n else 1
    return e
def tone(f, d, g=0.4, a=0.005, r=0.1, kind='sin'):
    t = T(d); ph = 2 * np.pi * f * t
    y = np.sin(ph) if kind == 'sin' else (np.sign(np.sin(ph)) * 0.5 + np.sin(ph) * 0.5)
    return y * env(len(t), a, r) * g
def noise_f(d, lo, hi, g=0.4):
    n = rng.standard_normal(int(d * SR)); F = np.fft.rfft(n); fr = np.fft.rfftfreq(len(n), 1 / SR)
    F[(fr < lo) | (fr > hi)] = 0; y = np.fft.irfft(F, len(n)); return y / (np.abs(y).max() + 1e-9) * g
def whoosh(d, g=0.5):
    n = int(d * SR); y = rng.standard_normal(n); out = np.zeros(n); k = 0.0
    sw = np.linspace(0.02, 0.45, n) ** 1.5
    for i in range(n):
        k += sw[i] * (y[i] - k); out[i] = k
    e = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return out / (np.abs(out).max() + 1e-9) * e * g
def mixs(*a):
    n = max(len(x) for x in a); o = np.zeros(n)
    for x in a: o[:len(x)] += x
    return o
def pop(g=0.4): return mixs(tone(520, 0.12, g, 0.002, 0.1), tone(780, 0.1, g * 0.6, 0.002, 0.08))
def ding(g=0.4): return mixs(tone(988, 0.5, g, 0.002, 0.45), tone(1318, 0.5, g * 0.7, 0.002, 0.45))
def beep(f, d=0.18, g=0.4): return tone(f, d, g, 0.003, 0.05, 'sq')
def rumble(d, g=0.6):
    n = int(d * SR); y = noise_f(d, 30, 400, 1.0) * np.linspace(0.3, 1, n) ** 0.7
    return y * env(n, 0.05, 0.6) * g
def kick(g=0.5):
    t = T(0.25); f = 120 * np.exp(-t * 18) + 40; return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12) * g
def hat(g=0.12): return noise_f(0.05, 6000, 10000, g) * np.exp(-T(0.05) * 60)

# ---- efectos ----
put(mix_fx, rumble(2.6, 0.5), 0.0); put(mix_fx, whoosh(1.4, 0.5), 0.6)         # hook: cohete despegando
put(mix_fx, kick(0.9), 0.0)
for s in S[1:]: put(mix_fx, whoosh(0.35, 0.35), s - 0.15)                        # transicion
for k in range(5): put(mix_fx, pop(0.35), JOIN[k])
put(mix_fx, ding(0.4), TU_JOIN + 0.3)
for k in range(8): put(mix_fx, beep(1400 if k % 2 else 1100, 0.07, 0.18), SCAN[0] + k * (SCAN[1] - SCAN[0]) / 8)
put(mix_fx, ding(0.5), OK0)
for i, ct in enumerate(CD): put(mix_fx, beep(660 if i < 2 else 1100, 0.22, 0.4), ct)
put(mix_fx, rumble(3.0, 0.75), LAUNCH - 0.3); put(mix_fx, whoosh(1.8, 0.5), LAUNCH)
put(mix_fx, ding(0.5), ARRIVE); put(mix_fx, noise_f(0.8, 2000, 9000, 0.25) * env(int(0.8 * SR), 0.01, 0.7), ARRIVE)
put(mix_fx, kick(0.6), sH); put(mix_fx, ding(0.5), sI)

# ---- musica: bajo + acordes + ritmo, 120 bpm ----
bpm = 128; beat = 60 / bpm; chords = [[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]]
nb = int(DURATION / beat) + 1
for b in range(nb):
    t0 = b * beat; ch = chords[(b // 4) % 4]
    put(mix_mu, kick(0.32), t0)
    put(mix_mu, hat(0.10), t0 + beat / 2)
    root = ch[0] / 2
    put(mix_mu, tone(root, beat * 0.45, 0.22, 0.01, 0.15), t0 + beat / 2)
    if b % 4 == 0:
        for f in ch: put(mix_mu, tone(f, beat * 3.8, 0.07, 0.05, 0.6), t0)
    put(mix_mu, tone(ch[(b * 2) % 3] * 2, beat * 0.22, 0.05, 0.004, 0.12), t0)
    put(mix_mu, tone(ch[(b * 2 + 1) % 3] * 2, beat * 0.22, 0.05, 0.004, 0.12), t0 + beat / 2)
mix_mu *= np.minimum(1, T(DURATION + 1)[:N] / 0.3 + 0.0)[:N] if False else 1.0

# ---- voces ----
WDIR = os.environ.get('WD', os.path.expanduser('~/cohete_video'))
for i, l in enumerate(LINES):
    f = '%s/l%d.mp3' % (WDIR, i)
    if not os.path.exists(f): print('falta', f); continue
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', f, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-']); v = np.frombuffer(raw, np.int16) / 32768.0
    put(mix_vo, v, l['t0'], 1.0)

# ducking: la musica y los efectos bajan cuando habla la voz
vo_env = np.convolve(np.abs(mix_vo), np.ones(int(0.12 * SR)) / int(0.12 * SR), 'same'); duck = 1 - 0.55 * np.clip(vo_env * 12, 0, 1)
out = mix_vo * 1.0 + mix_mu * 0.55 * duck + mix_fx * 0.8 * (0.5 + 0.5 * duck)
out = out[:int(DURATION * SR)]
fade = int(0.5 * SR); out[-fade:] *= np.linspace(1, 0, fade)
pk = np.abs(out).max(); out = out / max(pk, 1e-9) * 0.9
w = wave.open(WDIR + '/audio.wav', 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((out * 32767).astype(np.int16).tobytes()); w.close()
print('audio listo', len(out) / SR, 's, pico', round(pk, 2))

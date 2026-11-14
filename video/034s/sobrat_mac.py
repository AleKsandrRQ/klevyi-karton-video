# Сборка #034s на Mac: видео с субтитрами (из облака) + фон (fon.wav) + живой голос 3 по timing.json → −14 LUFS, копия до 10 МБ для Metricool
# Запуск: python3 sobrat_mac.py <папка_из_облака> <папка_голоса>
import json, subprocess, sys, os, numpy as np
D, G = sys.argv[1], sys.argv[2]
FF = os.environ.get('FF', 'ffmpeg')
SR = 48000
def load(p):
    raw = subprocess.run([FF, '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()
fon = subprocess.run([FF, '-v', 'error', '-i', f'{D}/fon.flac', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True).stdout
fon = np.frombuffer(fon, np.float32).reshape(-1, 2).copy()
N = len(fon)
TIM = json.load(open(f'{D}/timing.json'))
v = np.zeros(N, np.float32)
for k, (a, b) in TIM['frazy'].items():
    y = load(f'{G}/{k}.wav'); i = int(a * SR)
    y = y[:max(0, N - i)]; v[i:i + len(y)] += y
    print(k, a, round(len(y) / SR, 3), 'окно', round(b - a, 3))
act = np.abs(v) > 0.01
v = v / (np.sqrt(np.mean(v[act] ** 2)) + 1e-9) * 0.16
T = N / SR; t = np.arange(N) / SR
fade = np.clip(t / 0.05, 0, 1) * np.clip((T - t) / 0.6, 0, 1)
mix = fon + np.stack([v * fade, v * fade], 1)
pk = np.abs(mix).max()
if pk > 0.95: mix *= 0.95 / pk
mix.astype(np.float32).tofile(f'{D}/mix.f32')
src = ['-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', f'{D}/mix.f32']
m = subprocess.run([FF, '-hide_banner', *src, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
j = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
ln = f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true"
OUT = os.path.expanduser('~/Downloads/klevyi-karton-sudak-zimoj.mp4')
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', f'{D}/video_subs.mp4', *src, '-map', '0:v', '-map', '1:a', '-af', ln + ',aresample=48000,alimiter=limit=0.78:level=false',
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ac', '2', '-shortest', '-movflags', '+faststart', OUT], check=True)
UP = OUT.replace('.mp4', '-up.mp4')
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', OUT, '-c:v', 'libx264', '-preset', 'slow', '-crf', '26', '-maxrate', '1.6M', '-bufsize', '3.2M', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', UP], check=True)
r = subprocess.run([FF, '-hide_banner', '-i', OUT, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
print([l for l in r.splitlines() if ' I:' in l][-1], os.path.getsize(OUT) // 1024, 'КБ;', os.path.getsize(UP) // 1024, 'КБ (up)')

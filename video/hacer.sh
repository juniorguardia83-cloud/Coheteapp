#!/data/data/com.termux/files/usr/bin/bash
# Genera el video de TikTok (30 s, voces es-MX) y lo deja en /sdcard/Movies
set -e
cd "$(dirname "$0")"
export WD=$HOME/cohete_video
mkdir -p "$WD"
echo "1/4 voces..."; python3 voz.py
echo "2/4 audio...";  python3 audio.py
echo "3/4 cuadros..."; rm -rf "$WD/frames"; python3 render.py
echo "4/4 video...";  ffmpeg -y -v error -framerate 24 -i "$WD/frames/f%05d.jpg" -i "$WD/audio.wav" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -af loudnorm=I=-14:TP=-1.5 -shortest -movflags +faststart "$WD/cohete_live_tiktok.mp4"
mkdir -p /sdcard/Movies; cp "$WD/cohete_live_tiktok.mp4" /sdcard/Movies/cohete_live_tiktok.mp4
termux-media-scan /sdcard/Movies/cohete_live_tiktok.mp4 2>/dev/null || true
echo "LISTO: /sdcard/Movies/cohete_live_tiktok.mp4"

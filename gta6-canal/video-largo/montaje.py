#!/usr/bin/env python3
"""Montaje automático del video largo a partir de guion.md.

Uso:
  python3 montaje.py --t1 trailer1.mp4 --t2 trailer2.mp4 --salida borrador.mp4 --teleprompter
  python3 montaje.py --t1 trailer1.mp4 --t2 trailer2.mp4 --voz voz/ --salida final.mp4

- Sin --voz: la duración de cada sección se estima por cantidad de palabras (≈145 por minuto).
- Con --voz: usa la duración real de voz/00.mp3, voz/01.mp3, … y mezcla esa voz.
- --teleprompter: muestra el texto del guion abajo (para leerlo mientras grabás).
- Los trailers se usan SIN su audio (la música tiene derechos de terceros).
Requiere ffmpeg/ffprobe y Pillow.
"""
import argparse, glob, json, os, re, shutil, subprocess, tempfile, textwrap
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PPM = 145                       # palabras por minuto estimadas
VEL = 0.7                       # velocidad de los planos (0.7 = cámara lenta suave)
FPS = 30
FUENTE_B = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
FUENTE_M = "/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf"
ROSA, CIAN = (255, 72, 170), (60, 220, 255)


def sh(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def duracion(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def leer_guion(path):
    s = open(path, encoding="utf-8").read()
    secciones = []
    for bloque in re.split(r"\n## ", s)[1:]:
        cab = bloque.split("\n", 1)[0]
        m = re.match(r"(\d\d) — (.+)", cab)
        if not m:
            continue
        titulo = re.search(r"titulo:\s*(.+?)\s*-->", bloque).group(1)
        planos = []
        for p in re.search(r"planos:\s*(.+?)\s*-->", bloque).group(1).split():
            src, rng = p.split(":")
            a, b = map(float, rng.split("-"))
            planos.append((src, a, b))
        cuerpo = re.sub(r"<!--.*?-->", "", bloque.split("\n", 1)[1], flags=re.S)
        cuerpo = re.sub(r"\[[^\]]*\]", "", cuerpo)
        parrafos = [" ".join(x.split()) for x in cuerpo.split("\n\n") if x.strip()]
        secciones.append(dict(num=m.group(1), nombre=m.group(2), titulo=titulo,
                              planos=planos, texto=parrafos))
    return secciones


def png_titulo(texto, w, h, path):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    partes = texto.split(" · ", 1)
    f_num = ImageFont.truetype(FUENTE_B, int(h * 0.075))
    f_tit = ImageFont.truetype(FUENTE_B, int(h * 0.09))
    y = int(h * 0.36)
    # franja oscura detrás del texto
    banda = Image.new("RGBA", (w, int(h * 0.30)), (0, 0, 0, 150))
    img.alpha_composite(banda, (0, y - int(h * 0.04)))
    if len(partes) == 2:
        d.text((w // 2, y), partes[0], font=f_num, fill=ROSA, anchor="mt")
        y += int(h * 0.10)
        principal = partes[1]
    else:
        principal = partes[0]
    for linea in textwrap.wrap(principal, 28):
        d.text((w // 2, y), linea, font=f_tit, fill=(255, 255, 255), anchor="mt",
               stroke_width=max(2, h // 300), stroke_fill=(0, 0, 0))
        y += int(h * 0.105)
    d.line([(w * 0.35, y + h * 0.01), (w * 0.65, y + h * 0.01)], fill=CIAN, width=max(3, h // 200))
    img.save(path)


def png_credito(w, h, path):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FUENTE_M, int(h * 0.022))
    d.text((w - int(w * 0.015), int(h * 0.02)), "Imágenes: trailers oficiales de Rockstar Games",
           font=f, fill=(255, 255, 255, 170), anchor="rt")
    img.save(path)


def srt_tiempo(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guion", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "guion.md"))
    ap.add_argument("--t1", required=True); ap.add_argument("--t2", required=True)
    ap.add_argument("--voz"); ap.add_argument("--salida", required=True)
    ap.add_argument("--teleprompter", action="store_true")
    ap.add_argument("--alto", type=int, default=1080)
    ap.add_argument("--solo", help="renderizar solo estas secciones, ej. 00,01")
    a = ap.parse_args()

    H = a.alto; W = H * 16 // 9
    fuentes = {"T1": a.t1, "T2": a.t2}
    secciones = leer_guion(a.guion)
    if a.solo:
        secciones = [s for s in secciones if s["num"] in a.solo.split(",")]
    tmp = tempfile.mkdtemp(prefix="montaje_")
    print("Carpeta temporal:", tmp)

    # 1) duración de cada sección
    for s in secciones:
        palabras = sum(len(p.split()) for p in s["texto"])
        s["palabras"] = palabras
        voz = sorted(glob.glob(os.path.join(a.voz, s["num"] + ".*"))) if a.voz else []
        if voz:
            s["voz"] = voz[0]; s["dur"] = duracion(voz[0]) + 0.8
        else:
            s["voz"] = None; s["dur"] = palabras / PPM * 60 + 1.5
    total = sum(s["dur"] for s in secciones)
    print(f"Duración total: {total/60:.1f} min")

    # 2) planos de cada sección (los fragmentos se repiten en ciclo si la sección es larga)
    lista, t0, overlays, subs = [], 0.0, [], []
    k = 0
    for s in secciones:
        s["inicio"] = t0
        restante, i = s["dur"], 0
        while restante > 0.05:
            src, ia, ib = s["planos"][i % len(s["planos"])]
            vuelta = i // len(s["planos"])
            largo = min((ib - ia) / VEL, restante)
            if restante - largo < 1.0:          # no dejar un plano final de menos de 1 s
                largo = restante
            out = os.path.join(tmp, f"p{k:04d}.mp4")
            # paneo horizontal suave; cambia de dirección en cada plano y en cada vuelta
            izq = (i + vuelta) % 2 == 0
            zx = f"(iw-{W})*t/{largo:.3f}" if izq else f"(iw-{W})*(1-t/{largo:.3f})"
            vf = (f"setpts=PTS/{VEL},scale={int(W*1.12)}:{int(H*1.12)},"
                  f"crop={W}:{H}:'{zx}':'(ih-{H})/2',fps={FPS},format=yuv420p")
            # si el fragmento se acaba antes (ej. último plano estirado), se congela el último cuadro
            vf += f",tpad=stop_mode=clone:stop_duration={largo:.3f}"
            sh(["ffmpeg", "-y", "-ss", f"{ia}", "-i", fuentes[src], "-t", f"{(ib-ia):.3f}",
                "-an", "-vf", vf, "-t", f"{largo:.3f}", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "20", out])
            lista.append(out); restante -= largo; i += 1; k += 1
        # título de la sección
        png = os.path.join(tmp, f"titulo_{s['num']}.png"); png_titulo(s["titulo"], W, H, png)
        overlays.append((png, t0 + 0.3, t0 + 4.3))
        # teleprompter: oraciones repartidas por cantidad de palabras
        if a.teleprompter:
            oraciones = [o for p in s["texto"] for o in re.split(r"(?<=[.!?:])\s+", p) if o]
            pal = sum(len(o.split()) for o in oraciones)
            t = t0 + 0.6
            util = s["dur"] - 1.2
            for o in oraciones:
                d = util * len(o.split()) / pal
                subs.append((t, t + d, o)); t += d
        t0 += s["dur"]
        print(f"  sección {s['num']} lista ({s['dur']:.0f} s)")

    # 3) unir planos
    with open(os.path.join(tmp, "lista.txt"), "w") as f:
        f.writelines(f"file '{p}'\n" for p in lista)
    base = os.path.join(tmp, "base.mp4")
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "lista.txt"), "-c", "copy", base])

    # 4) voz: concatenar audios con silencio donde falte
    pistas = []
    for s in secciones:
        out = os.path.join(tmp, f"a_{s['num']}.wav")
        if s["voz"]:
            sh(["ffmpeg", "-y", "-i", s["voz"], "-af", f"adelay=300:all=1,apad=whole_dur={s['dur']:.3f}",
                "-ar", "48000", "-ac", "2", out])
        else:
            sh(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{s['dur']:.3f}", out])
        pistas.append(out)
    with open(os.path.join(tmp, "audios.txt"), "w") as f:
        f.writelines(f"file '{p}'\n" for p in pistas)
    audio = os.path.join(tmp, "voz.wav")
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "audios.txt"), "-c", "copy", audio])

    # 5) títulos, crédito, teleprompter y audio
    cred = os.path.join(tmp, "credito.png"); png_credito(W, H, cred)
    entradas = ["-i", base, "-i", audio, "-i", cred]
    for png, _, _ in overlays:
        entradas += ["-loop", "1", "-i", png]
    filtros, ult = [f"[0:v][2:v]overlay=0:0[v0]"], "v0"
    for j, (_, ta, tb) in enumerate(overlays):
        n = 3 + j
        filtros.append(f"[{n}:v]format=rgba,fade=in:st={ta}:d=0.5:alpha=1,fade=out:st={tb-0.5}:d=0.5:alpha=1[o{j}]")
        filtros.append(f"[{ult}][o{j}]overlay=0:0:shortest=1:enable='between(t,{ta},{tb})'[v{j+1}]")
        ult = f"v{j+1}"
    if subs:
        srt = os.path.join(tmp, "tp.srt")
        with open(srt, "w", encoding="utf-8") as f:
            for j, (ta, tb, o) in enumerate(subs, 1):
                f.write(f"{j}\n{srt_tiempo(ta)} --> {srt_tiempo(tb)}\n{o}\n\n")
        estilo = ("FontName=Inter Display,Bold=1,FontSize=17,PrimaryColour=&H00FFFFFF,"
                  "OutlineColour=&H00000000,BackColour=&H99000000,BorderStyle=4,Outline=1,"
                  "Shadow=0,Alignment=2,MarginV=40,MarginL=80,MarginR=80")
        filtros.append(f"[{ult}]subtitles='{srt}':force_style='{estilo}'[vf]"); ult = "vf"
    # fundido de entrada y salida
    filtros.append(f"[{ult}]fade=in:st=0:d=0.8,fade=out:st={total-1.2:.3f}:d=1.2[vout]")
    sh(["ffmpeg", "-y", *entradas, "-filter_complex", ";".join(filtros), "-map", "[vout]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-t", f"{total:.3f}", a.salida])

    # capítulos para la descripción de YouTube
    caps = os.path.splitext(a.salida)[0] + "_capitulos.txt"
    with open(caps, "w", encoding="utf-8") as f:
        for s in secciones:
            m, sec = divmod(int(s["inicio"]), 60)
            f.write(f"{m}:{sec:02d} {s['nombre']}\n")
    shutil.rmtree(tmp)
    print("Listo:", a.salida, "| capítulos:", caps)


if __name__ == "__main__":
    main()

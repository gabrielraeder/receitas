"""Localiza intervalos estáveis (páginas) em um vídeo do caderno.

Uso:
    python scripts/find_pages.py <video> <slug> [--crop-h 500] [--rotate ccw|cw|none]

Saída:
    work/<slug>/segments.json  — intervalos estáveis, com o quadro mais nítido de cada um
    work/<slug>/pages/page_NN_t<seg>.png — quadro escolhido, recortado, girado e ampliado 2x

Lógica:
1. Amostra o vídeo a ~10 fps, recorta a região do caderno e mede a diferença
   média entre quadros consecutivos (movimento de mão ou de página).
2. Intervalos com movimento baixo por >= MIN_LEN segundos viram candidatos.
3. Intervalos vizinhos cujos quadros são muito parecidos são fundidos (mesma página dupla).
4. Em cada intervalo, escolhe o quadro com maior nitidez (variância do Laplaciano).
"""
import argparse
import json
import os

import cv2
import numpy as np

MOTION_THRESH = 2.5   # diferença média (0-255) acima disso = movimento
MIN_LEN = 0.8         # segundos mínimos de estabilidade
SAME_PAGE_THRESH = 6.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("slug")
    ap.add_argument("--crop-h", type=int, default=500)
    ap.add_argument("--rotate", default="ccw", choices=["ccw", "cw", "none"])
    args = ap.parse_args()

    out_dir = os.path.join("work", args.slug)
    pages_dir = os.path.join(out_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)

    cap = cv2.VideoCapture(args.video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    step = max(1, round(fps / 10))

    times, diffs, sharp, smalls = [], [], [], []
    prev = None
    idx = 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            _, frame = cap.retrieve()
            region = frame[: args.crop_h]
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, (120, 125), interpolation=cv2.INTER_AREA).astype(np.float32)
            d = float(np.mean(np.abs(small - prev))) if prev is not None else 99.0
            times.append(idx / fps)
            diffs.append(d)
            sharp.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
            smalls.append(small)
            prev = small
        idx += 1
    cap.release()

    # intervalos estáveis
    segments = []
    start = None
    for i, d in enumerate(diffs):
        still = d < MOTION_THRESH
        if still and start is None:
            start = i
        if (not still or i == len(diffs) - 1) and start is not None:
            end = i if not still else i + 1
            if times[end - 1] - times[start] >= MIN_LEN:
                segments.append([start, end])
            start = None

    # funde intervalos vizinhos da mesma página
    merged = []
    for s in segments:
        if merged:
            a = smalls[(merged[-1][0] + merged[-1][1]) // 2]
            b = smalls[(s[0] + s[1]) // 2]
            if float(np.mean(np.abs(a - b))) < SAME_PAGE_THRESH:
                merged[-1][1] = s[1]
                continue
        merged.append(s)

    result = []
    for n, (a, b) in enumerate(merged, 1):
        best = max(range(a, b), key=lambda i: sharp[i])
        t = times[best]
        result.append({
            "page": n,
            "start": round(times[a], 2),
            "end": round(times[b - 1], 2),
            "best": round(t, 2),
            "sharpness": round(sharp[best], 1),
        })

    # extrai quadros em resolução cheia
    cap = cv2.VideoCapture(args.video)
    for r in result:
        cap.set(cv2.CAP_PROP_POS_MSEC, r["best"] * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        img = frame[: args.crop_h]
        if args.rotate == "ccw":
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif args.rotate == "cw":
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)
        name = f"page_{r['page']:02d}_t{r['best']:06.2f}.png"
        cv2.imwrite(os.path.join(pages_dir, name), img)
        r["file"] = name
    cap.release()

    with open(os.path.join(out_dir, "segments.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    for r in result:
        print(f"{r['page']:02d}  {r['start']:6.2f}-{r['end']:6.2f}  best={r['best']:6.2f}  sharp={r['sharpness']}")


if __name__ == "__main__":
    main()

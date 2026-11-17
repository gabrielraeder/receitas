"""Empilha vários quadros de um intervalo (mediana alinhada) para melhorar a leitura.

Uso:
    python scripts/stack_frames.py <video> <out.png> <t_ini> <t_fim> --region x0,y0,x1,y1 [--scale 4] [--n 12]

A região é dada em frações da imagem já girada (anti-horário). Cada quadro é ampliado,
alinhado ao primeiro por correlação de fase (translação) e combinado pela mediana,
o que reduz ruído de compressão. Só use em intervalos em que a página não se mexe.
"""
import argparse

import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("t0", type=float)
    ap.add_argument("t1", type=float)
    ap.add_argument("--region", required=True)
    ap.add_argument("--scale", type=float, default=4.0)
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--crop-h", type=int, default=500)
    args = ap.parse_args()

    x0, y0, x1, y1 = (float(v) for v in args.region.split(","))
    cap = cv2.VideoCapture(args.video)
    frames = []
    for t in np.linspace(args.t0, args.t1, args.n):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        img = cv2.rotate(frame[: args.crop_h], cv2.ROTATE_90_COUNTERCLOCKWISE)
        h, w = img.shape[:2]
        img = img[int(y0 * h): int(y1 * h), int(x0 * w): int(x1 * w)]
        img = cv2.resize(img, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_CUBIC)
        frames.append(img.astype(np.float32))
    cap.release()

    ref = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    aligned = [frames[0]]
    for f in frames[1:]:
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        (dx, dy), _ = cv2.phaseCorrelate(ref, g)
        m = np.float32([[1, 0, -dx], [0, 1, -dy]])
        aligned.append(cv2.warpAffine(f, m, (f.shape[1], f.shape[0]), borderMode=cv2.BORDER_REPLICATE))
    out = np.median(np.stack(aligned), axis=0).astype(np.uint8)
    # leve realce de nitidez
    blur = cv2.GaussianBlur(out, (0, 0), 2)
    out = cv2.addWeighted(out, 1.6, blur, -0.6, 0)
    cv2.imwrite(args.out, out)
    print(args.out, len(aligned), "quadros")


if __name__ == "__main__":
    main()

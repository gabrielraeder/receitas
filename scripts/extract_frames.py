"""Extrai quadros em timestamps específicos, recortados, girados e ampliados.

Uso:
    python scripts/extract_frames.py <video> <out_dir> <t1> [<t2> ...] [--crop-h 500] [--scale 2] [--prefix page]

Cada quadro vira <out_dir>/<prefix>_t<t>.png. Com --region x0,y0,x1,y1 (frações 0-1 da
imagem já girada), recorta só um trecho — útil para gerar zooms de linhas difíceis.
"""
import argparse
import os

import cv2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out_dir")
    ap.add_argument("times", nargs="+", type=float)
    ap.add_argument("--crop-h", type=int, default=500)
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--prefix", default="page")
    ap.add_argument("--region", default=None)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    cap = cv2.VideoCapture(args.video)
    for t in args.times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            print(f"falhou: {t}")
            continue
        img = cv2.rotate(frame[: args.crop_h], cv2.ROTATE_90_COUNTERCLOCKWISE)
        if args.region:
            x0, y0, x1, y1 = (float(v) for v in args.region.split(","))
            h, w = img.shape[:2]
            img = img[int(y0 * h): int(y1 * h), int(x0 * w): int(x1 * w)]
        img = cv2.resize(img, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_LANCZOS4)
        name = f"{args.prefix}_t{t:06.2f}.png"
        cv2.imwrite(os.path.join(args.out_dir, name), img)
        print(name)
    cap.release()


if __name__ == "__main__":
    main()

"""Generate the recipe book logo (light/dark wordmark + favicon) as SVG.

Text is converted to paths using the Caveat font (SIL OFL), so the logo
renders the same everywhere without loading a web font.

Usage: python scripts/make_logo.py <path/to/Caveat[wght].ttf>
"""
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

OUT = Path(__file__).resolve().parent.parent / "images"

PALETTE = {
    "light": {"cover": "#C4572E", "spine": "#9E4222", "rings": "#4A3326",
              "heart": "#FBF1E3", "text": "#3A2A1F", "accent": "#C4572E"},
    "dark": {"cover": "#D9693F", "spine": "#B4502B", "rings": "#F3E6D3",
             "heart": "#FBF1E3", "text": "#F3E6D3", "accent": "#E8875F"},
}


def icon(c: dict) -> str:
    """Spiral notebook with a heart on the cover, drawn on a 64x64 grid."""
    rings = "".join(
        f'<rect x="9" y="{y}" width="12" height="5" rx="2.5" fill="none" '
        f'stroke="{c["rings"]}" stroke-width="2.6"/>'
        for y in (14, 24.5, 35, 45.5)
    )
    heart = ("M37 46.5c-.6 0-1.2-.2-1.6-.6C30.2 41.4 25 37.1 25 31.4"
             "c0-3.9 3-6.9 6.6-6.9 2.2 0 4.2 1.1 5.4 2.9"
             "c1.2-1.8 3.2-2.9 5.4-2.9 3.6 0 6.6 3 6.6 6.9"
             "c0 5.7-5.2 10-10.4 14.5-.4.4-1 .6-1.6.6z")
    return (
        f'<rect x="14" y="7" width="44" height="50" rx="6" fill="{c["cover"]}"/>'
        f'<rect x="14" y="7" width="7" height="50" rx="3" fill="{c["spine"]}"/>'
        f'<path d="{heart}" fill="{c["heart"]}"/>'
        f"{rings}"
    )


def text_path(font: TTFont, text: str, size: float, x: float, baseline: float,
              tracking: float = 0.0) -> tuple[str, float]:
    """Return an SVG path for `text` and the x where it ends."""
    upm = font["head"].unitsPerEm
    scale = size / upm
    cmap = font.getBestCmap()
    glyphs = font.getGlyphSet()
    hmtx = font["hmtx"]
    parts = []
    for ch in text:
        name = cmap[ord(ch)]
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, baseline)))
        parts.append(pen.getCommands())
        x += hmtx[name][0] * scale + tracking
    return "".join(parts), x


def wordmark(font: TTFont, c: dict) -> str:
    main, end = text_path(font, "Caderno", 44, 70, 41, tracking=0.4)
    sub, end2 = text_path(font, "de receitas", 25, 72, 60, tracking=0.6)
    width = max(end, end2) + 4
    body = (
        f'<path d="{main}" fill="{c["text"]}"/>'
        f'<path d="{sub}" fill="{c["accent"]}"/>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} 64" '
        f'role="img" aria-label="Caderno de receitas">'
        f"{icon(c)}{body}</svg>\n"
    )


def favicon(c: dict) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="4 2 58 60" '
        f'role="img" aria-label="Caderno de receitas">{icon(c)}</svg>\n'
    )


def main() -> None:
    font = instantiateVariableFont(TTFont(sys.argv[1]), {"wght": 700})
    OUT.mkdir(exist_ok=True)
    (OUT / "logo_light.svg").write_text(wordmark(font, PALETTE["light"]), encoding="utf-8")
    (OUT / "logo_dark.svg").write_text(wordmark(font, PALETTE["dark"]), encoding="utf-8")
    (OUT / "favicon.svg").write_text(favicon(PALETTE["light"]), encoding="utf-8")
    print("written:", *sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()

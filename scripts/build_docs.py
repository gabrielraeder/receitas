"""Gera os MDX das receitas, a navegação do WriteDocs e as páginas de índice.

Uso:
    python scripts/build_docs.py <video-slug> [--source videos/<arquivo>.mp4]

Entradas (em work/<video-slug>/):
    transcription_part_*.json  -> juntados em transcription.json (ordenado por número)
    classification.json        -> categoria, tags, tempos etc., por número de receita

Saídas:
    docs/receitas/<categoria>/<slug>.mdx
    writedocs.json             (navegação reconstruída a partir de todos os MDX existentes)
    docs/receitas/index.mdx    (cards por categoria com contagem)
    docs/index.mdx             (página inicial, com as receitas do último lote)
    work/<video-slug>/build_report.json (arquivos gerados, pulados e conflitos)

Regra de sobrescrita: um MDX existente só é regravado se o frontmatter dele tiver a
mesma origem (notebook.source) e o mesmo número (notebook.number). Caso contrário o
arquivo é mantido e o conflito vai para o relatório.
"""
import argparse
import glob
import json
import os
import re
import unicodedata

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CATEGORIES = [
    ("bolos", "Bolos", "cake"),
    ("doces", "Doces", "candy"),
    ("sobremesas-geladas", "Sobremesas geladas", "ice-cream-cone"),
    ("paes-e-massas", "Pães e massas", "wheat"),
    ("salgados", "Salgados", "utensils"),
    ("bebidas", "Bebidas", "cup-soda"),
]
CATEGORY_KEYS = [c[0] for c in CATEGORIES]

TAGS = {
    "doce", "salgado", "bebida",
    "bolo", "torta", "pudim", "mousse", "sorvete", "pao", "biscoito", "massa", "sopa", "salada",
    "prato-principal", "acompanhamento", "molho", "lanche", "sobremesa",
    "assado", "frito", "cozido", "sem-forno", "gelado", "fermentado", "calda", "claras-em-neve",
    "chocolate", "fruta", "maracuja", "morango", "limao", "coco", "leite-condensado", "iogurte",
    "queijo", "frango", "carne",
    "festa", "cafe-da-manha", "lanche-da-tarde", "natal", "rapido",
    "sem-gluten", "sem-lactose", "vegetariano", "vegano",
}


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", text)


def q(value):
    """Escalar YAML seguro (string JSON é YAML válido)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def qlist(values):
    return "[" + ", ".join(q(v) for v in values) + "]"


def mdx_text(text):
    """Escapa caracteres que quebram MDX em texto corrido."""
    return (text.replace("{", "&#123;").replace("}", "&#125;")
                .replace("<", "&lt;").replace(">", "&gt;"))


def read_frontmatter(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    m = re.match(r"^---\n(.*?)\n---\n", content, re.S)
    return yaml.safe_load(m.group(1)) if m else {}


def merge_parts(work, pattern):
    parts = sorted(glob.glob(os.path.join(work, pattern)))
    recipes = []
    for p in parts:
        with open(p, encoding="utf-8") as f:
            recipes.extend(json.load(f))
    recipes.sort(key=lambda r: r["number"])
    numbers = [r["number"] for r in recipes]
    dupes = sorted({n for n in numbers if numbers.count(n) > 1})
    if dupes:
        raise SystemExit(f"Números repetidos entre as partes: {dupes}")
    with open(os.path.join(work, "transcription.json"), "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    return recipes, parts


def build_frontmatter(r, c, slug, source):
    first = r["pages"][0]
    lines = ["---", f"title: {q(r['title'])}", f"description: {q(c['description'])}"]
    if c.get("sidebarTitle"):
        lines.append(f"sidebarTitle: {q(c['sidebarTitle'])}")
    lines += [f"category: {c['category']}", f"tags: {qlist(c['tags'])}"]
    if r.get("yield"):
        lines.append(f"servings: {q(r['yield'])}")
    for key in ("prepTime", "totalTime"):
        if c.get(key):
            lines.append(f"{key}: {q(c[key])}")
    if c.get("estimatedTimes"):
        lines.append("estimatedTimes: true")
    lines += [
        f"difficulty: {c['difficulty']}",
        f"mainIngredients: {qlist(c['mainIngredients'])}",
        f"equipment: {qlist(c['equipment'])}",
    ]
    # oven/freezer/fridge: omitidos quando o caderno não permite afirmar (valor null)
    lines += [f"{k}: {q(c[k])}" for k in ("oven", "freezer", "fridge") if c.get(k) is not None]
    lines += [
        f"status: {r['status']}",
        f"doubts: {len(r['doubts'])}",
        "notebook:",
        f"  number: {r['number']}",
        f"  source: {source}",
        f"  timestamp: {q(first['timestamp'])}",
        "---",
    ]
    return "\n".join(lines)


def build_body(r, c):
    out = []
    info = [f"Receita nº {r['number']} do caderno"]
    if r.get("yield"):
        info.append(f"rende {r['yield']}")
    if c.get("totalTime"):
        label = "tempo total estimado" if c.get("estimatedTimes") else "tempo total"
        info.append(f"{label}: {c['totalTime']}")
    out += ["<Info>", "  " + mdx_text(" · ".join(info)), "</Info>", ""]

    if r["status"] == "incomplete":
        # texto vem da classificação (escrito para o leitor), nunca das notas internas da transcrição
        missing = c.get("incompleteNote") or "Parte da receita não aparece no vídeo."
        out += ["<Warning>", f"  **Receita incompleta.** {mdx_text(missing)}", "</Warning>", ""]
    elif r["status"] == "needs-review":
        out += ["<Warning>",
                "  **Receita a revisar.** Há trechos que não foi possível ler com segurança. "
                "Veja os avisos no fim da página antes de preparar.",
                "</Warning>", ""]

    out += ["## Ingredientes", ""]
    for group in r["ingredients"]:
        if group.get("section"):
            out += [f"### {mdx_text(group['section'])}", ""]
        out += [f"- {mdx_text(item)}" for item in group["items"]]
        out.append("")

    out += ["## Modo de preparo", "", "<Steps>"]
    for step in r["steps"]:
        out += [f"  <Step title={q(step['title'])}>", f"    {mdx_text(step['text'])}", "  </Step>"]
    out += ["</Steps>", ""]

    if r.get("tips"):
        out += ["## Dicas", "", "<Tip>"]
        if len(r["tips"]) == 1:
            out.append("  " + mdx_text(r["tips"][0]))
        else:
            out += [f"  - {mdx_text(t)}" for t in r["tips"]]
        out += ["</Tip>", ""]

    for d in r["doubts"]:
        out += ["<Warning>",
                f"  **Trecho com dúvida:** {mdx_text(d['text'])} Confira no caderno (vídeo, {d['timestamp']}).",
                "</Warning>", ""]
    return "\n".join(out).rstrip() + "\n"


def scan_recipes():
    items = []
    for path in glob.glob(os.path.join(ROOT, "docs", "receitas", "*", "*.mdx")):
        fm = read_frontmatter(path)
        rel = os.path.relpath(path, ROOT).replace("\\", "/")[:-4]
        if os.path.basename(rel) == "index":
            continue
        items.append({"path": rel, "title": fm.get("title", ""), "sidebar": fm.get("sidebarTitle") or fm.get("title", ""),
                      "category": fm.get("category"), "number": (fm.get("notebook") or {}).get("number")})
    return items


def sort_key(item):
    title = unicodedata.normalize("NFKD", item["title"]).encode("ascii", "ignore").decode("ascii").lower()
    return (title, item["number"] or 0)


def write_config(items):
    path = os.path.join(ROOT, "writedocs.json")
    config = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            config = json.load(f)
    config.setdefault("$schema", "https://docs.writedocs.io/schema.json")
    config.setdefault("name", "Caderno de receitas")
    config.setdefault("description", "Receitas transcritas de um caderno manuscrito.")
    nav = [{"group": "Início", "pages": ["docs/index", "docs/receitas/index"]}]
    for key, label, _icon in CATEGORIES:
        pages = sorted((i for i in items if i["category"] == key), key=sort_key)
        if pages:
            nav.append({"group": label, "pages": [p["path"] for p in pages]})
    config["navigation"] = nav
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_receitas_index(items):
    lines = [
        "---",
        'title: "Receitas"',
        'description: "Todas as receitas do caderno, organizadas por categoria."',
        "---",
        "",
        "Todas as receitas transcritas do caderno, separadas por categoria. Dentro de cada categoria, "
        "a navegação lateral lista as receitas em ordem alfabética.",
        "",
        "<CardGroup cols={2}>",
    ]
    for key, label, icon in CATEGORIES:
        pages = sorted((i for i in items if i["category"] == key), key=sort_key)
        if not pages:
            continue
        n = len(pages)
        count = f"{n} receita" if n == 1 else f"{n} receitas"
        lines += [f'  <Card title="{label}" icon="{icon}" href="/{pages[0]["path"]}">',
                  f"    {count}", "  </Card>"]
    lines += ["</CardGroup>", ""]
    with open(os.path.join(ROOT, "docs", "receitas", "index.mdx"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_home(items, batch, video_slug):
    total = len(items)
    labels = {k: l for k, l, _ in CATEGORIES}
    lines = [
        "---",
        'title: "Caderno de receitas"',
        'description: "Receitas de família transcritas de um caderno manuscrito, com ingredientes, modo de preparo e dúvidas de leitura."',
        "slug: /",
        "---",
        "",
        f"Este site reúne as receitas de um caderno manuscrito, transcritas a partir de vídeos do caderno "
        f"folheado página a página. São {total} receitas até agora.",
        "",
        "## Como navegar",
        "",
        "- **Por categoria:** a barra lateral agrupa as receitas em bolos, doces, sobremesas geladas, pães e massas, "
        "salgados e bebidas. A página [Receitas](/docs/receitas/index) mostra quantas há em cada uma.",
        "- **Por tags:** cada receita tem tags no cabeçalho (tipo de prato, técnica, ingrediente principal, ocasião), "
        "que ajudam a achar, por exemplo, tudo que leva chocolate ou não vai ao forno.",
        "- **Número do caderno:** o quadro azul no topo de cada receita mostra o número dela no caderno original.",
        "",
        "<Note>",
        "  As receitas foram transcritas como estão no caderno, sem correções. Quando um trecho não pôde ser lido com "
        "segurança, a página traz um aviso com o momento do vídeo em que ele aparece.",
        "</Note>",
        "",
        "## Adicionadas por último",
        "",
        f"Lote `{video_slug}`:",
        "",
    ]
    by_path = {i["path"]: i for i in items}
    for path in batch:
        i = by_path[path]
        lines.append(f"- [{i['title']}](/{path}) · {labels.get(i['category'], i['category'])}")
    lines.append("")
    with open(os.path.join(ROOT, "docs", "index.mdx"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video_slug")
    ap.add_argument("--source", default=None)
    ap.add_argument("--parts", default="transcription_part_*.json",
                    help="glob das partes a juntar (padrão: todas)")
    args = ap.parse_args()
    source = args.source or f"videos/{args.video_slug}.mp4"
    work = os.path.join(ROOT, "work", args.video_slug)

    recipes, parts = merge_parts(work, args.parts)
    with open(os.path.join(work, "classification.json"), encoding="utf-8") as f:
        classification = json.load(f)

    report = {"parts": [os.path.basename(p) for p in parts], "written": [], "skipped": [], "slugCollisions": []}
    batch, used = [], {}
    for r in recipes:
        c = classification.get(str(r["number"]))
        if not c:
            raise SystemExit(f"Receita {r['number']} sem classificação")
        bad = [t for t in c["tags"] if t not in TAGS]
        if bad or c["category"] not in CATEGORY_KEYS:
            raise SystemExit(f"Receita {r['number']}: tag/categoria fora do vocabulário: {bad or c['category']}")
        slug = c.get("slug") or slugify(r["title"])
        if slug in used:
            report["slugCollisions"].append({"slug": slug, "numbers": [used[slug], r["number"]]})
            raise SystemExit(f"Slug repetido no lote: {slug} (receitas {used[slug]} e {r['number']}). "
                             f"Defina 'slug' na classificação de uma delas.")
        used[slug] = r["number"]
        rel = f"docs/receitas/{c['category']}/{slug}"
        path = os.path.join(ROOT, rel + ".mdx")
        if os.path.exists(path):
            nb = read_frontmatter(path).get("notebook") or {}
            if nb.get("source") != source or nb.get("number") != r["number"]:
                report["skipped"].append({"number": r["number"], "file": rel + ".mdx", "existing": nb})
                continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_frontmatter(r, c, slug, source) + "\n\n" + build_body(r, c))
        report["written"].append({"number": r["number"], "file": rel + ".mdx", "status": r["status"],
                                  "doubts": len(r["doubts"])})
        batch.append(rel)

    items = scan_recipes()
    write_config(items)
    write_receitas_index(items)
    write_home(items, batch, args.video_slug)
    with open(os.path.join(work, "build_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"{len(report['written'])} gerados, {len(report['skipped'])} pulados (já existiam de outra origem)")
    for s in report["skipped"]:
        print("  pulado:", s["file"], s["existing"])


if __name__ == "__main__":
    main()

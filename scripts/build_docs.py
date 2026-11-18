"""Gera os MDX das receitas, a navegação do WriteDocs e as páginas de índice.

Uso:
    python scripts/build_docs.py <video-slug> [--source videos/<arquivo>.mp4]

Entradas (em work/<video-slug>/):
    transcription_part_*.json  -> juntados em transcription.json (ordenado por número)
    classification.json        -> categoria, tags, tempos etc., por número de receita

Saídas:
    docs/receitas/<categoria>/<slug>.mdx
    docs/writedocs.json        (só a chave "navigation" é reconstruída, em tabs; o resto é preservado)
    docs/receitas/index.mdx    (cards por seção, agrupados por tab, com contagem)
    work/<video-slug>/build_report.json (arquivos gerados, pulados e conflitos)

A homepage (docs/index.mdx) é feita à mão e NÃO é tocada por este script.
Tabs e seções vêm de scripts/taxonomy.json (cada seção = uma categoria/pasta).
O nome do caderno no quadro <Info> vem de scripts/notebooks.json (por vídeo de origem).

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
DOCS = os.path.join(ROOT, "docs")  # raiz do site WriteDocs (onde fica writedocs.json)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "taxonomy.json"), encoding="utf-8") as _f:
    TAXONOMY = json.load(_f)["tabs"]
CATEGORY_KEYS = [s["key"] for t in TAXONOMY for s in t["sections"]]

TAGS = {
    "doce", "salgado", "bebida",
    "bolo", "torta", "pudim", "mousse", "sorvete", "pao", "biscoito", "massa", "sopa", "salada",
    "prato-principal", "acompanhamento", "molho", "lanche", "sobremesa",
    "assado", "frito", "cozido", "sem-forno", "gelado", "fermentado", "calda", "claras-em-neve",
    "chocolate", "fruta", "maracuja", "morango", "limao", "coco", "leite-condensado", "iogurte",
    "queijo", "frango", "carne", "peixe", "frutos-do-mar",
    "festa", "cafe-da-manha", "lanche-da-tarde", "natal", "rapido",
    "sem-gluten", "sem-lactose", "sem-acucar", "vegetariano", "vegano",
    "maquina-de-pao",
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
    lines = ["---", f"title: {q(c.get('title') or r['title'])}", f"description: {q(c['description'])}"]
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


def build_body(r, c, notebook_label="caderno"):
    out = []
    info = [f"Receita nº {r['number']} do {notebook_label}"]
    if c.get("title") and c["title"] != r["title"]:
        # título com complemento editorial: mostra como está no caderno
        info.append(f"no caderno: “{r['title']}”")
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

    out += ["## Modo de preparo", ""]
    if r["steps"]:
        out.append("<Steps>")
        for step in r["steps"]:
            out += [f"  <Step title={q(step['title'])}>", f"    {mdx_text(step['text'])}", "  </Step>"]
        out += ["</Steps>", ""]
    else:
        out += ["O caderno não traz o modo de preparo desta receita.", ""]

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
    """Lista todas as receitas publicadas. `path` é relativo a docs/ (formato da navegação e das URLs)."""
    items, seen = [], {}
    for path in glob.glob(os.path.join(DOCS, "receitas", "*", "*.mdx")):
        fm = read_frontmatter(path)
        rel = os.path.relpath(path, DOCS).replace("\\", "/")[:-4]
        if os.path.basename(rel) == "index":
            continue
        nb = fm.get("notebook") or {}
        key = (nb.get("source"), nb.get("number"))
        if key in seen:
            raise SystemExit(f"Mesma receita em dois arquivos: {seen[key]} e {rel} "
                             f"(notebook {key}). Apague a cópia antiga.")
        seen[key] = rel
        items.append({"path": rel, "title": fm.get("title", ""), "sidebar": fm.get("sidebarTitle") or fm.get("title", ""),
                      "category": fm.get("category"), "number": nb.get("number")})
    return items


def sort_key(item):
    title = unicodedata.normalize("NFKD", item["title"]).encode("ascii", "ignore").decode("ascii").lower()
    return (title, item["number"] or 0)


def sections_with_pages(items):
    """[(tab, [(section, [páginas ordenadas])])], só com seções e tabs que têm receitas."""
    out = []
    for tab in TAXONOMY:
        secs = []
        for s in tab["sections"]:
            pages = sorted((i for i in items if i["category"] == s["key"]), key=sort_key)
            if pages:
                secs.append((s, pages))
        if secs:
            out.append((tab, secs))
    return out


def write_config(items):
    path = os.path.join(DOCS, "writedocs.json")
    config = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            config = json.load(f)
    config.setdefault("$schema", "https://docs.writedocs.io/schema.json")
    config.setdefault("name", "Caderno de receitas")
    generated = []
    for tab, secs in sections_with_pages(items):
        generated.append({"tab": tab["label"], "icon": tab["icon"],
                          "pages": [{"group": s["label"], "pages": [p["path"] for p in pages]} for s, pages in secs]})
    # Tabs que não vêm da taxonomia (ex.: "Home" com a página index) são manuais:
    # ficam como estão, na mesma posição. As tabs da taxonomia entram onde estava a primeira delas.
    taxonomy_labels = {t["label"] for t in TAXONOMY}
    existing = (config.get("navigation") or {}).get("tabs", []) if isinstance(config.get("navigation"), dict) else []
    tabs, inserted = [], False
    for t in existing:
        if t.get("tab") in taxonomy_labels:
            if not inserted:
                tabs.extend(generated)
                inserted = True
        else:
            tabs.append(t)
    if not inserted:
        tabs.extend(generated)
    config["navigation"] = {"tabs": tabs}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_receitas_index(items):
    lines = [
        "---",
        'title: "Receitas"',
        'description: "Todas as receitas do caderno, organizadas em doces, salgados e bebidas."',
        "---",
        "",
        "Todas as receitas transcritas do caderno, separadas em doces, salgados e bebidas. Cada grupo abre "
        "numa aba do topo, e a barra lateral lista as receitas de cada seção em ordem alfabética.",
        "",
    ]
    for tab, secs in sections_with_pages(items):
        lines += [f"## {tab['label']}", "", "<CardGroup cols={2}>"]
        for s, pages in secs:
            n = len(pages)
            count = f"{n} receita" if n == 1 else f"{n} receitas"
            lines += [f'  <Card title="{s["label"]}" icon="{s["icon"]}" href="/{pages[0]["path"]}">',
                      f"    {count}", "  </Card>"]
        lines += ["</CardGroup>", ""]
    with open(os.path.join(DOCS, "receitas", "index.mdx"), "w", encoding="utf-8") as f:
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
    notebooks_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notebooks.json")
    notebook_label = "caderno"
    if os.path.exists(notebooks_path):
        with open(notebooks_path, encoding="utf-8") as f:
            notebook_label = json.load(f).get(source, "caderno")
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
        slug = c.get("slug") or slugify(c.get("title") or r["title"])
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
            f.write(build_frontmatter(r, c, slug, source) + "\n\n" + build_body(r, c, notebook_label))
        report["written"].append({"number": r["number"], "file": rel + ".mdx", "status": r["status"],
                                  "doubts": len(r["doubts"])})
        batch.append(rel)

    items = scan_recipes()
    write_config(items)
    write_receitas_index(items)
    with open(os.path.join(work, "build_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"{len(report['written'])} gerados, {len(report['skipped'])} pulados (já existiam de outra origem)")
    for s in report["skipped"]:
        print("  pulado:", s["file"], s["existing"])


if __name__ == "__main__":
    main()

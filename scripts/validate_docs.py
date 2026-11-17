"""Confere os MDX gerados contra o checklist do CLAUDE.md.

Uso:
    python scripts/validate_docs.py [<video-slug>]

Verifica:
- frontmatter faz parse (YAML) e tem os campos obrigatórios;
- categoria igual à pasta, tags do vocabulário controlado, de 3 a 8 tags;
- não há {, } ou < soltos no texto (fora dos componentes conhecidos);
- o número de avisos de dúvida bate com `doubts` e, se o slug do vídeo for dado,
  com o transcription.json;
- a navegação do writedocs.json aponta para arquivos que existem.
Sai com código 1 se houver erro.
"""
import glob
import json
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_docs import CATEGORY_KEYS, ROOT, TAGS  # noqa: E402

REQUIRED = ["title", "description", "category", "tags", "status"]
COMPONENT_LINE = re.compile(
    r"^\s*(</?(Info|Warning|Tip|Note|Steps|CardGroup)>|<Step title=\"[^\"]*\">|</Step>|<CardGroup cols=\{\d\}>"
    r"|<Card title=\"[^\"]*\" icon=\"[^\"]*\" href=\"[^\"]*\">|</Card>)\s*$")


def main():
    errors = []
    slug = sys.argv[1] if len(sys.argv) > 1 else None
    expected = {}
    if slug:
        with open(os.path.join(ROOT, "work", slug, "transcription.json"), encoding="utf-8") as f:
            expected = {r["number"]: len(r["doubts"]) for r in json.load(f)}

    files = sorted(glob.glob(os.path.join(ROOT, "docs", "**", "*.mdx"), recursive=True))
    for path in files:
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.S)
        if not m:
            errors.append(f"{rel}: sem frontmatter")
            continue
        try:
            fm = yaml.safe_load(m.group(1))
        except yaml.YAMLError as e:
            errors.append(f"{rel}: YAML inválido: {e}")
            continue
        body = m.group(2)

        for n, line in enumerate(body.splitlines(), 1):
            if COMPONENT_LINE.match(line):
                continue
            if re.search(r"[{}<]", line):
                errors.append(f"{rel}: caractere solto na linha {n} do corpo: {line.strip()[:80]}")

        if "/receitas/" not in rel or rel.endswith("/index.mdx"):
            continue
        for k in REQUIRED:
            if k not in fm:
                errors.append(f"{rel}: falta '{k}'")
        folder = rel.split("/")[2]
        if fm.get("category") != folder or folder not in CATEGORY_KEYS:
            errors.append(f"{rel}: categoria '{fm.get('category')}' não bate com a pasta '{folder}'")
        tags = fm.get("tags") or []
        bad = [t for t in tags if t not in TAGS]
        if bad:
            errors.append(f"{rel}: tags fora do vocabulário: {bad}")
        if not 3 <= len(tags) <= 8:
            errors.append(f"{rel}: {len(tags)} tags (esperado 3 a 8)")
        if fm.get("status") not in ("complete", "incomplete", "needs-review"):
            errors.append(f"{rel}: status inválido")
        warnings = body.count("**Trecho com dúvida:**")
        if warnings != fm.get("doubts"):
            errors.append(f"{rel}: doubts={fm.get('doubts')} mas há {warnings} avisos de dúvida")
        number = (fm.get("notebook") or {}).get("number")
        if expected and number in expected and expected[number] != warnings:
            errors.append(f"{rel}: transcription.json tem {expected[number]} dúvidas, a página tem {warnings}")
        if len(str(fm.get("description", ""))) > 160:
            errors.append(f"{rel}: description com {len(fm['description'])} caracteres")

    with open(os.path.join(ROOT, "writedocs.json"), encoding="utf-8") as f:
        config = json.load(f)
    for group in config["navigation"]:
        for page in group["pages"]:
            if not os.path.exists(os.path.join(ROOT, page + ".mdx")):
                errors.append(f"writedocs.json: página inexistente {page}")

    for e in errors:
        print("ERRO", e)
    print(f"{len(files)} arquivos verificados, {len(errors)} erros")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

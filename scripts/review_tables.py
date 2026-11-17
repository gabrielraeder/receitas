"""Gera as seções mecânicas do relatório de revisão de um lote.

Uso:
    python scripts/review_tables.py <video-slug> > /tmp/tabelas.md

Imprime em Markdown: resumo, tabela de receitas (nº, título, arquivo, status, dúvidas)
e a lista de dúvidas por receita, com timestamp e recorte em work/<slug>/zoom/.
As seções de análise (duplicatas, tags propostas, observações) são escritas à mão.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    slug = sys.argv[1]
    work = os.path.join(ROOT, "work", slug)
    with open(os.path.join(work, "transcription.json"), encoding="utf-8") as f:
        recipes = json.load(f)
    with open(os.path.join(work, "build_report.json"), encoding="utf-8") as f:
        report = json.load(f)
    files = {w["number"]: w["file"] for w in report["written"]}

    counts = {}
    for r in recipes:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    total_doubts = sum(len(r["doubts"]) for r in recipes)
    print(f"- Receitas: **{len(recipes)}** "
          f"({counts.get('complete', 0)} complete, {counts.get('needs-review', 0)} needs-review, "
          f"{counts.get('incomplete', 0)} incomplete)")
    print(f"- Dúvidas registradas: **{total_doubts}**")
    print(f"- Arquivos gerados: {len(report['written'])}; pulados por já existirem: {len(report['skipped'])}")
    print()
    print("## Receitas\n")
    print("| Nº | Título | Arquivo | Status | Dúvidas |")
    print("|---:|---|---|---|---:|")
    for r in recipes:
        f = files.get(r["number"], "—")
        link = f"[{os.path.basename(f)}](../{f})" if f != "—" else f
        print(f"| {r['number']} | {r['title']} | {link} | `{r['status']}` | {len(r['doubts'])} |")
    print()
    print("## Dúvidas por receita\n")
    print("Recortes relativos a `work/" + slug + "/` (não versionado; regenerável com `scripts/extract_frames.py`).\n")
    for r in recipes:
        if not r["doubts"]:
            continue
        print(f"### {r['number']}. {r['title']}\n")
        for d in r["doubts"]:
            print(f"- **{d['timestamp']}** — {d['text']} (`{d['zoom']}`)")
        print()


if __name__ == "__main__":
    main()

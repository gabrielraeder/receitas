# Caderno de receitas → documentação WriteDocs

Este projeto transforma vídeos de um caderno de receitas manuscrito (folheado página a página) em uma documentação no WriteDocs: um arquivo `.mdx` por receita, com frontmatter estruturado, tags de classificação e páginas de índice.

Todo o conteúdo gerado é em **português do Brasil**. Código, scripts, nomes de variável e chaves do frontmatter ficam em **inglês**.

---

## Estrutura do projeto

```
.
├── CLAUDE.md
├── videos/                 # vídeos originais (não editar, não versionar se forem grandes)
├── work/                   # artefatos temporários — no .gitignore
│   └── <video-slug>/
│       ├── sheets/         # contact sheets para localizar as páginas
│       ├── pages/          # um quadro nítido por página (já na orientação certa)
│       ├── zoom/           # recortes ampliados de trechos difíceis
│       └── transcription.json
├── scripts/                # scripts auxiliares (JavaScript ou Python)
├── docs/
│   ├── index.mdx           # página inicial do livro de receitas
│   ├── writedocs.json
│   ├── images/
│   ├── receitas/
│   │   ├── index.mdx       # visão geral por categoria
│   │   ├── doces/
│   │   ├── salgados/
│   │   ├── paes-e-massas/
│   │   ├── bolos/
│   │   ├── sobremesas-geladas/
│   │   └── bebidas/
│   └── tags/               # (opcional) uma página por tag
└── review/
    └── <video-slug>.md     # relatório de revisão de cada lote
```

Pré-requisitos: `ffmpeg`/`ffprobe` e Python 3 com Pillow (`pip install pillow`).

---

## Pipeline (siga nesta ordem)

### 1. Inspecionar o vídeo

```bash
ffprobe -v error -show_entries format=duration:stream=width,height,codec_type:stream_side_data=rotation -of compact videos/<arquivo>.mp4
```

- Anote a duração e a orientação. Vídeos de celular costumam ter metadado de rotação; o `ffmpeg` já aplica isso automaticamente.
- Para nomear a pasta em `work/`, use um slug a partir do nome do arquivo ou da data.

### 2. Localizar as páginas

Vídeos longos têm muitos quadros repetidos e quadros borrados durante a virada de página. O objetivo é **um quadro nítido por página dupla**.

1. Gere contact sheets para ter uma visão geral (1 quadro por segundo, 24 por folha):
   ```bash
   ffmpeg -v error -i <video> -vf "fps=1,scale=480:-1,tile=4x6" work/<slug>/sheets/sheet_%02d.jpg
   ```
2. Detecte as viradas de página por mudança de cena:
   ```bash
   ffmpeg -i <video> -vf "select='gt(scene,0.25)',showinfo" -f null - 2>&1 | grep pts_time
   ```
3. Para cada intervalo estável entre viradas, extraia o quadro **do meio** do intervalo (mão fora da página, sem borrão) em resolução máxima:
   ```bash
   ffmpeg -v error -ss <t> -i <video> -frames:v 1 work/<slug>/pages/page_<NN>_t<t>.png
   ```
4. Se o texto estiver de lado, gire com `-vf transpose=1` (horário) ou `transpose=2` (anti-horário). Confira olhando a imagem.
5. Se um quadro estiver borrado, tente ±0,5 s. Guarde o timestamp de cada página: ele vai para o frontmatter.

### 3. Ler e transcrever

Leia cada imagem de `pages/` com a ferramenta de leitura de imagens. Para linhas difíceis, recorte e amplie (2–3×) com Pillow e salve em `zoom/`.

Regras de transcrição:

- **Fidelidade acima de tudo.** Não invente ingrediente, quantidade, temperatura nem tempo. Se não der para ler, marque como dúvida.
- **Ignore o "fantasma"** da página de trás (tinta que vaza pelo papel): é texto espelhado e mais claro.
- **Receitas que continuam na página seguinte:** a página da esquerda pode ter o final da receita anterior. Junte as partes.
- **Receita cortada:** se o vídeo acabar ou pular a continuação, marque `status: incomplete` e indique o que falta.
- **Numeração:** o caderno numera as receitas (1, 2, 3…). Preserve esse número em `notebook.number`.
- Expanda abreviações comuns: `c/` → com, `s/` → sem, `xíc.` → xícara, `col.` → colher, `+ ou -` → cerca de. "Trigo" → "farinha de trigo".
- Padronize as medidas sem alterar valores: `1 xícara (chá) de açúcar`, `2 colheres (sopa) de manteiga`, `3/4 de xícara`, `180 °C`.
- Valores suspeitos (ex.: forno a 300 °C por 8 min) **não são corrigidos**: transcreva como está e registre a dúvida.

Salve o resultado bruto em `work/<slug>/transcription.json` antes de gerar o MDX. Um objeto por receita, com o texto lido, a página e o timestamp, e a lista de dúvidas. Isso permite regerar os MDX sem reler o vídeo.

### 4. Classificar

Para cada receita, defina a categoria (pasta), as tags e os metadados do frontmatter (ver abaixo). Use **somente** as tags do vocabulário controlado. Se nenhuma servir, proponha uma nova no relatório de revisão em vez de criá-la por conta própria.

### 5. Gerar os arquivos MDX

- Caminho: `docs/receitas/<categoria>/<slug>.mdx`. O slug é o título em minúsculas, sem acento e com hífens (`bolo-gelado-de-maracuja`).
- Se o slug já existir (receita repetida em outro vídeo), **não sobrescreva**: compare as versões e registre no relatório.
- Siga o template da seção "Template MDX".

### 6. Atualizar a navegação e os índices

- Adicione as novas páginas à navegação no arquivo de configuração do WriteDocs, agrupadas por categoria e em ordem alfabética dentro de cada grupo.
- Atualize `docs/receitas/index.mdx` (cards por categoria com a contagem de receitas).
- Se houver páginas de tag em `docs/tags/`, atualize as listas.

### 7. Revisar e gerar o relatório

Crie `review/<video-slug>.md` contendo:

- Tabela de receitas: número no caderno, título, arquivo gerado, status (`complete` / `incomplete` / `needs-review`).
- Lista de dúvidas por receita, com o timestamp do vídeo e o recorte em `zoom/` correspondente.
- Receitas duplicadas ou conflitantes.
- Tags novas propostas.

Antes de encerrar, confira:

- [ ] Todo arquivo MDX tem frontmatter válido (YAML que faz parse).
- [ ] Não há `{`, `}` ou `<` soltos no texto (quebram o MDX). Use `&lt;` ou reescreva.
- [ ] Toda dúvida do `transcription.json` aparece no MDX (componente de aviso) **e** no relatório.
- [ ] A navegação aponta para arquivos que existem.
- [ ] Se possível, rode o build local do WriteDocs e corrija os erros.

---

## Frontmatter

```yaml
---
title: Bolo gelado de maracujá
description: Pão de ló com creme de maracujá, chantilly e morangos, servido gelado.
sidebarTitle: Bolo gelado de maracujá # opcional, para títulos longos
category: bolos # igual ao nome da pasta
tags: [bolo, sobremesa, gelado, fruta, maracuja, morango]
servings: 12 porções # só se o caderno indicar; senão omita
prepTime: 40 min # estimativa → ver regra abaixo
totalTime: 4 h # inclui forno, geladeira, fermentação
difficulty: media # facil | media | dificil
mainIngredients: [maracujá, leite condensado, chantilly, morango]
equipment: [batedeira, panela, forma]
oven: false # usa forno?
freezer: false # vai ao freezer?
fridge: true # vai à geladeira?
status: incomplete # complete | incomplete | needs-review
doubts: 1 # número de trechos com dúvida
notebook:
  number: 4 # número da receita no caderno
  source: videos/1000031714.mp4
  timestamp: "00:11" # onde a página aparece no vídeo
---
```

Regras:

- `title`, `description`, `category`, `tags` e `status` são **obrigatórios**.
- `servings`, `prepTime` e `totalTime`: use o que o caderno informa. Quando for estimativa sua (ex.: soma dos tempos de forno e fermentação), mantenha o valor e acrescente `estimatedTimes: true`.
- `difficulty` é sempre estimativa: baseie-se no número de etapas e nas técnicas usadas (claras em neve, calda, massa fermentada etc.).
- `description`: uma frase, até ~150 caracteres, que descreva o prato. Não comece com "Receita de".
- Acentos são permitidos nos valores; as tags ficam **sem acento**.

---

## Vocabulário controlado de tags

| Grupo             | Tags                                                                                                                                                             |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tipo              | `doce`, `salgado`, `bebida`                                                                                                                                      |
| Prato             | `bolo`, `torta`, `pudim`, `mousse`, `sorvete`, `pao`, `biscoito`, `massa`, `sopa`, `salada`, `prato-principal`, `acompanhamento`, `molho`, `lanche`, `sobremesa` |
| Técnica           | `assado`, `frito`, `cozido`, `sem-forno`, `gelado`, `fermentado`, `calda`, `claras-em-neve`                                                                      |
| Ingrediente-chave | `chocolate`, `fruta`, `maracuja`, `morango`, `limao`, `coco`, `leite-condensado`, `iogurte`, `queijo`, `frango`, `carne`                                         |
| Ocasião           | `festa`, `cafe-da-manha`, `lanche-da-tarde`, `natal`, `rapido`                                                                                                   |
| Restrição         | `sem-gluten`, `sem-lactose`, `vegetariano`, `vegano`                                                                                                             |

- Use de 3 a 8 tags por receita.
- Tags de **restrição** só quando for inequívoco pelos ingredientes. Se houver ingrediente processado com dúvida (ex.: chocolate em pó com glúten), não use a tag.
- `rapido` = tempo total até 30 min.

Categorias (pastas): `bolos`, `doces`, `sobremesas-geladas`, `paes-e-massas`, `salgados`, `bebidas`. Uma receita pertence a **uma** categoria; as tags cobrem o resto.

---

## Template MDX

> Os componentes abaixo seguem o padrão do Mintlify, que o WriteDocs replica. Antes do primeiro lote, confira na documentação do WriteDocs quais componentes existem e ajuste este template se precisar.

```mdx
---
(frontmatter)
---

<Info>
  Receita nº {número} do caderno · rende {porções} · {tempo total}
</Info>

## Ingredientes

### Massa

- 1 xícara (chá) de açúcar
- 3/4 de xícara de chocolate em pó

### Creme

- ...

## Modo de preparo

<Steps>
  <Step title="Prepare a calda">Leve o açúcar ao fogo até derreter e passe para uma forma de pudim.</Step>
  <Step title="Faça o creme">...</Step>
</Steps>

## Dicas

<Tip>Dicas que estavam no caderno. Se não houver nenhuma, omita a seção.</Tip>

<Warning>**Trecho com dúvida:** está escrito "forno 300°". Confira no caderno (vídeo, 00:08).</Warning>
```

Regras do conteúdo:

- **Ingredientes:** listas com `-`. Use subtítulos `###` quando o caderno separa partes (base, massa, creme, recheio, cobertura). Itens de finalização (ex.: "manteiga derretida para pincelar") também entram na lista.
- **Preparo:** `<Steps>` com um `<Step>` por etapa lógica. O título da etapa é curto e imperativo; o texto, no imperativo ("Bata", "Leve ao forno").
- **Dúvidas:** um `<Warning>` por dúvida, no fim da página, citando o texto como foi lido e o timestamp do vídeo.
- **Receita incompleta:** um `<Warning>` no topo dizendo o que falta, e `status: incomplete`.
- **Não acrescente** dicas, variações ou substituições que não estejam no caderno. Se quiser sugerir algo, faça isso no relatório de revisão, não na página.

---

## Páginas de índice

`docs/receitas/index.mdx`: título "Receitas", uma frase de introdução e um `<CardGroup cols={2}>` com um `<Card>` por categoria (título, ícone, contagem de receitas, link para a primeira receita ou para a página da categoria).

`docs/index.mdx`: apresentação do caderno, como navegar (categorias × tags) e a lista das receitas adicionadas por último.

---

## O que não fazer

- Não altere os vídeos em `videos/`.
- Não versione `work/` (quadros e recortes são grandes e regeneráveis).
- Não "corrija" a receita: diferenças de quantidade, temperatura ou tempo são registradas como dúvida, nunca ajustadas em silêncio.
- Não sobrescreva uma receita existente sem registrar a comparação no relatório.

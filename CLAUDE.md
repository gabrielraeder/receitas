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
├── scripts/                # scripts auxiliares (ver "Notas para os próximos lotes")
│   └── taxonomy.json       # tabs e seções da navegação (fonte única das categorias)
├── docs/                   # raiz do site WriteDocs: caminhos da navegação e URLs são relativos a esta pasta
│   ├── index.mdx           # homepage feita à mão (não é gerada por script)
│   ├── writedocs.json      # só a chave "navigation" é gerada; o resto (estilos, logo) é manual
│   ├── images/
│   ├── receitas/
│   │   ├── index.mdx       # visão geral: cards por seção, agrupados por tab
│   │   └── <categoria>/    # uma pasta por seção de scripts/taxonomy.json (bolos/, tortas-doces/, …)
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
- Receita repetida **no mesmo caderno** (ex.: nº 15 e nº 20): publique as duas com slug `-2` e o número no `sidebarTitle`, e registre a comparação no relatório.
- Siga o template da seção "Template MDX".

### 6. Atualizar a navegação e os índices

- A navegação de `docs/writedocs.json` usa **tabs** (Doces, Salgados, Bebidas) e, dentro de cada tab, um grupo por **seção** (= categoria), com as receitas em ordem alfabética. Tabs e seções vêm de `scripts/taxonomy.json`; seção ou tab sem receitas não aparece.
- Atualize `docs/receitas/index.mdx` (um `## <tab>` por tab e um `<CardGroup cols={2}>` com um card por seção e a contagem).
- A homepage `docs/index.mdx` é feita à mão: quando entrar seção nova ou mudar a contagem, atualize os cards e os números dela manualmente (e confira que todo `href` aponta para um arquivo que existe).
- Se houver páginas de tag em `docs/tags/`, atualize as listas.
- `python scripts/build_docs.py <slug>` faz os passos 5 e 6 (menos a homepage).

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

`python scripts/validate_docs.py <slug>` confere os quatro primeiros itens (e que toda receita está na navegação). O build do WriteDocs é `npx @writedocs/generator validate` e `npx @writedocs/generator dev`, rodados dentro de `docs/`.

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

### Categorias (seções) e tabs

Uma receita pertence a **uma** categoria; as tags cobrem o resto. A categoria é a pasta, o valor de `category` no frontmatter e a seção na navegação. Cada categoria pertence a uma tab:

| Tab      | Categorias (pastas)                                                                                                       |
| -------- | ------------------------------------------------------------------------------------------------------------------------- |
| Doces    | `bolos`, `tortas-doces`, `sobremesas-geladas`, `biscoitos`, `docinhos`, `paes-doces`, `recheios-e-coberturas`             |
| Salgados | `paes-e-massas`, `salgadinhos`, `tortas-salgadas`, `pratos-principais`, `acompanhamentos`                                 |
| Bebidas  | `bebidas-quentes`, `bebidas-frias`                                                                                        |

- A fonte de verdade é `scripts/taxonomy.json` (rótulos e ícones). Para criar uma categoria nova, acrescente lá **e** nesta tabela, e proponha no relatório.
- Critérios: brownie e bem-casados → `docinhos`; pães de massa doce (babka, pão de maçã e canela) → `paes-doces`; pão comum (pão de leite) → `paes-e-massas`; recheios e coberturas avulsos → `recheios-e-coberturas`; misturas para bebida (pó para capuccino) → `bebidas-quentes`; bolo servido gelado continua em `bolos`.
- Mudar a categoria de uma receita publicada muda a URL: mova com `git mv`, atualize a classificação e os links da homepage.

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

`docs/receitas/index.mdx`: título "Receitas", uma frase de introdução e, para cada tab, um `## <tab>` com um `<CardGroup cols={2}>` e um `<Card>` por seção (título, ícone, contagem de receitas, link para a primeira receita da seção). Gerado por `build_docs.py`.

`docs/index.mdx`: homepage estilizada (`mode: custom`, Tailwind), feita à mão: apresentação do caderno, um bloco de cards por tab (uma card por seção, com contagem) e como as receitas estão organizadas. Sem lista de "adicionadas por último" nem menção a lotes. Nunca gere nem sobrescreva por script.

Nem `index.mdx` nem `receitas/index.mdx` entram na navegação: com tabs, o schema do WriteDocs não aceita páginas soltas fora delas. As duas continuam acessíveis por `/` e `/receitas`.

---

## O que não fazer

- Não altere os vídeos em `videos/`.
- Não versione `work/` (quadros e recortes são grandes e regeneráveis).
- Não "corrija" a receita: diferenças de quantidade, temperatura ou tempo são registradas como dúvida, nunca ajustadas em silêncio.
- Não sobrescreva uma receita existente sem registrar a comparação no relatório.

---

## Notas para os próximos lotes

Aprendizados do lote `receitas1` (43 receitas, 34 páginas duplas):

- **ffmpeg:** não está instalado no sistema. Use o binário do pacote Python `imageio-ffmpeg` (`python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`) e o OpenCV (`cv2`), que já está instalado. Não há `ffprobe`: `ffmpeg -i <video>` mostra duração e resolução.
- **Formato dos vídeos:** 478×850, retrato, caderno deitado na metade de cima. Recorte `crop=478:500:0:0` e gire com `transpose=2`. A letra só fica confiável em recortes ampliados 3× ou mais.
- **Localizar páginas:** a detecção de cena do ffmpeg não acha nenhuma virada (câmera fixa, virada lenta). `scripts/find_pages.py` (por movimento) perde páginas com a mão por cima e junta páginas parecidas. Monte sempre o mapa à mão com contact sheets **giradas** (1 quadro/s, `crop` + `transpose=2` + `tile`) e anote o intervalo estável de cada página dupla.
- **Scripts** (rodar da raiz do projeto):
  - `extract_frames.py <video> <dir> <t...> [--region x0,y0,x1,y1 --scale 3 --prefix rNN_x]`: quadros e recortes girados.
  - `stack_frames.py <video> <out.png> <t0> <t1> --region ...`: mediana de vários quadros, para números ambíguos (não ajuda se a página se mexe).
  - `build_docs.py <slug> [--parts <glob>]`: junta `work/<slug>/transcription_part_*.json` em `transcription.json`, lê `work/<slug>/classification.json` (categoria, tags, tempos, `slug`/`sidebarTitle`/`incompleteNote` opcionais) e gera MDX, navegação e `receitas/index.mdx`.
  - `validate_docs.py <slug>`: checklist do passo 7.
  - `review_tables.py <slug>`: tabela e lista de dúvidas do relatório.
- **Transcrição em paralelo:** dividir as páginas duplas em blocos contíguos para subagentes funcionou bem, usando `work/<slug>/TRANSCRIPTION_BRIEF.md` como instrução comum (regras, ferramentas e formato JSON). Confira algumas receitas de cada bloco contra os recortes.
- **Aviso de receita incompleta:** o texto vem de `incompleteNote` na classificação, escrito para o leitor. Nunca use o campo `notes` da transcrição, que é nota interna.
- **Build do WriteDocs:** `npx @writedocs/generator validate` ainda não foi rodado neste projeto (bloqueado pela política de permissões da sessão). Pendente confirmar se as chaves próprias do frontmatter (`tags`, `notebook`, `mainIngredients` etc.) passam na validação.

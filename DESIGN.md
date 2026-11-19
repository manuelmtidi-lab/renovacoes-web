# DESIGN.md — Painel de renovações

Sistema de design do projecto. Mistura três fontes:
- **NVIDIA** (awesome-design-md, VoltAgent): atmosfera, cor e geometria.
- **taste-skill** (Leonxlnx): os três "dials" e as regras anti-genérico.
- **design-motion-principles** (Kyle Zantos, a partir de Emil Kowalski, Jakub Krehel e Jhey Tompkins): regras de movimento.

## 1. Dials (escala 1 a 10)

| Dial | Valor | Porquê |
|---|---|---|
| VARIANCE | 3 | Painel de trabalho: layout previsível, nada de composições "artísticas". |
| MOTION | 6 | Vivo, mas sem atrapalhar quem usa a ferramenta todos os dias. |
| DENSITY | 8 | Muita informação por ecrã, como um painel técnico. |

## 2. Atmosfera (estilo NVIDIA)

- Tela quase preta, texto branco, **um único acento**: verde `#76b900`.
- O verde é **sinal, não superfície**: bordas de 2px, sublinhados, indicador activo, pequeno quadrado no canto dos cartões. Nunca fundos grandes.
- Geometria técnica: **raio de 2px** (nada de cantos muito redondos), linhas finas (`hairline`) em vez de sombras.
- Tipografia sem serifa, pesos 400 e 700, rótulos pequenos em maiúsculas com espaçamento. Números grandes em negrito, com `tabular-nums`.

### Tokens

| Token | Valor | Uso |
|---|---|---|
| `--marca` | `#76b900` | CTA, item activo, sublinhado, quadrado de canto |
| `--marca-activa` | `#5a8d00` | botão premido |
| `--marca-palida` | `#bff230` | destaque raro (brilho, contador) |
| `--tela` | `#000000` / `#0a0a0a` | fundo |
| `--superficie` | `#111111` | cartões |
| `--linha` | `#262626` | bordas finas |
| atrasado | vermelho | estado |
| 7 dias | `#df6500` | estado |
| 30 dias | `#ef9100` | estado |
| 60 dias / ok | azul-petróleo (não verde) | estado; evita confusão com o verde da marca |

Tema claro: tela `#ffffff`, superfície `#f7f7f7`, mantendo o mesmo verde como acento.

## 3. Movimento

Pergunta-guia (Emil Kowalski): **"Isto precisa mesmo de animar?"** Num painel usado todos os dias, só anima o que dá sentido.

### Regras
- Anima só `transform` e `opacity` (e `clip-path` quando preciso). Nunca `width`, `height`, `top`, `left`.
- Easing nunca é o `ease` simples. Padrão: `cubic-bezier(0.22, 1, 0.36, 1)`.
- Durações: hover e clique 120–180 ms · entradas 300–500 ms · contadores 700–900 ms · transição de página 200–250 ms.
- Nada começa em `scale(0)`: começa em `scale(0.97)` com `opacity: 0`.
- **`prefers-reduced-motion`** desliga tudo o que não seja mudança de cor.
- Entradas só **uma vez**, no carregamento. Stagger no máximo 6 elementos, 40 ms entre cada.
- Nada de movimento em ciclo infinito, excepto um ponto discreto em "Atrasado".

### Proibido (marcas de "interface gerada por IA")
- Pulsar em tudo, `hover:scale` em todos os cartões, desfoque (blur) nas entradas, molas saltitantes em botões de uso comum, fade-in em conteúdo estático, stagger em listas longas.

### Movimentos de assinatura do painel
1. **Quadrado verde no canto** dos cartões (12 px), que cresce ligeiramente no hover.
2. **Sublinhado verde de 2 px** que desliza em links e no item activo da barra lateral.
3. **Contadores** dos 4 cartões sobem de 0 ao valor final, uma vez.
4. **Brilho que segue o rato** na borda dos cartões (variáveis CSS `--mx` e `--my`), só no portátil.
5. **Fundo técnico**: grelha fina com esbatido verde no topo, estática.
6. **Linha da tabela**: barra verde de 2 px à esquerda no hover.
7. **Barra de dias até expirar** em cada serviço, com a cor do estado.
8. **Transição entre páginas** com View Transitions (`@view-transition { navigation: auto; }`).
9. **HTMX**: o conteúdo trocado entra com fade curto (classes `htmx-added` e `htmx-swapping`).
10. **Revelar ao rolar** com `animation-timeline: view()`, com alternativa sem animação.

## 4. Densidade

- Linhas de tabela de 44 px; cabeçalho de 36 px em maiúsculas pequenas.
- Cartões com 20–24 px de padding. Espaçamento base de 4 px.
- No telemóvel, tabelas viram cartões; alvos de toque com pelo menos 44 px.

## 5. Contraste e acessibilidade

- Texto normal com contraste mínimo de 4,5:1. O verde `#76b900` serve em fundo escuro, mas **não** como texto em fundo branco: no tema claro usar `#5a8d00` para texto.
- Estado nunca só pela cor: sempre ponto + texto ("Atrasado", "7 dias").
- Foco visível com contorno verde de 2 px.

## 6. Referências por consultar

- https://github.com/VoltAgent/awesome-design-md (pasta `design-md/nvidia`)
- https://github.com/Leonxlnx/taste-skill
- https://github.com/kylezantos/design-motion-principles
- https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

# Manual de Identidade Visual — Braid System

Este manual define a identidade visual do **Braid System**, a aplicação de gestão financeira para trancistas. Ele padroniza cores, tipografia, uso da marca e diretrizes de interface para garantir uma experiência coerente, acolhedora e profissional em todos os pontos de contato.

A identidade do Braid System nasce do universo das tranças: tons terrosos, naturais e quentes que remetem à raiz, à terra e ao trabalho manual valorizado. A paleta combina o verde da floresta com a terracota, o marrom da terra e o dourado, transmitindo confiança, calor humano e cuidado.

---

## 1. Paleta de cores

A paleta principal é composta por seis cores. Cada uma tem um papel definido na interface — fundo, superfícies, acentos e destaques.

| Cor | Amostra | HEX | RGB | Papel |
|---|---|---|---|---|
| Verde Musgo | <span style="display:inline-block;width:48px;height:20px;background:#2F3B2E;border:1px solid #00000022;border-radius:4px"></span> | `#2F3B2E` | `47, 59, 46` | Cor primária — superfícies, cabeçalhos, barras |
| Verde Floresta | <span style="display:inline-block;width:48px;height:20px;background:#1E2A1F;border:1px solid #00000022;border-radius:4px"></span> | `#1E2A1F` | `30, 42, 31` | Fundo principal, modo escuro, base |
| Terracota | <span style="display:inline-block;width:48px;height:20px;background:#8C4A2F;border:1px solid #00000022;border-radius:4px"></span> | `#8C4A2F` | `140, 74, 47` | Acento — botões de ação, links, alertas quentes |
| Marrom Terra | <span style="display:inline-block;width:48px;height:20px;background:#5A3A20;border:1px solid #00000022;border-radius:4px"></span> | `#5A3A20` | `90, 58, 32` | Secundária — bordas, textos sobre claro, ícones |
| Dourado Antigo | <span style="display:inline-block;width:48px;height:20px;background:#C8A15A;border:1px solid #00000022;border-radius:4px"></span> | `#C8A15A` | `200, 161, 90` | Destaque — valores positivos, badges, realces |
| Bege Areia | <span style="display:inline-block;width:48px;height:20px;background:#E7DAC1;border:1px solid #00000022;border-radius:4px"></span> | `#E7DAC1` | `231, 218, 193` | Fundo claro, superfícies de cartão, texto sobre escuro |

### Hierarquia de uso

A regra geral segue a proporção **60 / 30 / 10**:

- **60%** — cores de base (Verde Floresta e Verde Musgo no modo escuro; Bege Areia no modo claro).
- **30%** — cores secundárias e de superfície (Marrom Terra, Verde Musgo).
- **10%** — cores de acento e destaque (Terracota e Dourado Antigo), reservadas para chamar atenção a ações e dados financeiros importantes.

### Significado das cores

- **Terracota** sinaliza ação e atenção: é a cor dos botões primários e de alertas que exigem decisão.
- **Dourado Antigo** representa valor e conquista: usado em receitas, lucro e indicadores positivos.
- **Marrom Terra** transmite solidez e estrutura: bordas, divisórias e textos de apoio.
- **Verde Musgo / Verde Floresta** são a base de confiança e estabilidade da marca.

---

## 2. Tokens de cor (CSS / design tokens)

Use sempre tokens em vez de valores HEX soltos no código. Isto garante consistência e facilita o suporte a tema claro e escuro.

```css
:root {
  /* Cores de marca */
  --color-moss:      #2F3B2E; /* Verde Musgo */
  --color-forest:    #1E2A1F; /* Verde Floresta */
  --color-terracota: #8C4A2F; /* Terracota */
  --color-earth:     #5A3A20; /* Marrom Terra */
  --color-gold:      #C8A15A; /* Dourado Antigo */
  --color-sand:      #E7DAC1; /* Bege Areia */

  /* Papéis semânticos — tema claro (padrão) */
  --bg:           var(--color-sand);
  --surface:      #FFFFFF;
  --text:         var(--color-forest);
  --text-muted:   var(--color-earth);
  --border:       #00000022;
  --primary:      var(--color-terracota);
  --primary-text: #FFFFFF;
  --accent:       var(--color-gold);
  --success:      #4A6B3A;
  --danger:       #B23A2E;
}

/* Papéis semânticos — tema escuro */
[data-theme="dark"] {
  --bg:         var(--color-forest);
  --surface:    var(--color-moss);
  --text:       var(--color-sand);
  --text-muted: #C8B79A;
  --border:     #FFFFFF1A;
  --primary:    var(--color-terracota);
  --accent:     var(--color-gold);
}
```

---

## 3. Acessibilidade e contraste

Todas as combinações de texto devem atender ao mínimo **WCAG 2.1 AA** (contraste ≥ 4,5:1 para texto normal e ≥ 3:1 para texto grande).

Combinações aprovadas:

| Fundo | Texto | Uso |
|---|---|---|
| Verde Floresta `#1E2A1F` | Bege Areia `#E7DAC1` | Corpo de texto no modo escuro |
| Bege Areia `#E7DAC1` | Verde Floresta `#1E2A1F` | Corpo de texto no modo claro |
| Terracota `#8C4A2F` | Branco `#FFFFFF` | Texto sobre botões primários |
| Verde Musgo `#2F3B2E` | Bege Areia `#E7DAC1` | Cabeçalhos e barras |

Evite usar **Dourado Antigo** como cor de texto sobre fundo claro (contraste insuficiente). Reserve-o para ícones grandes, badges com fundo escuro e elementos decorativos. Nunca use cor como único meio de transmitir informação — combine com ícone, rótulo ou forma.

---

## 4. Tipografia

A aplicação é **mobile-first**, portanto a tipografia prioriza legibilidade em telas pequenas.

- **Família principal:** Inter (UI, corpo e números). Alternativa de sistema: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`.
- **Família de títulos:** Poppins (SemiBold) para dar personalidade aos cabeçalhos.
- **Números financeiros:** usar variação tabular (`font-variant-numeric: tabular-nums`) para alinhar valores em colunas.

### Escala tipográfica

| Token | Tamanho | Peso | Uso |
|---|---|---|---|
| `display` | 28 px | 600 | Título de tela principal |
| `h1` | 22 px | 600 | Seções |
| `h2` | 18 px | 600 | Subseções |
| `body` | 16 px | 400 | Texto corrido |
| `caption` | 13 px | 400 | Legendas, rótulos auxiliares |
| `value` | 24 px | 600 | Valores monetários em destaque |

A altura de linha padrão para corpo é **1,5**. Tamanho mínimo de fonte na interface: **13 px**.

---

## 5. Logotipo e marca

Enquanto o logotipo definitivo não é finalizado, seguem as diretrizes provisórias:

- **Área de proteção:** mantenha um espaço livre ao redor da marca equivalente à altura da letra "B" do nome.
- **Tamanho mínimo:** 24 px de altura em telas; 12 mm em impressos.
- **Fundos permitidos:** Verde Floresta, Verde Musgo ou Bege Areia. Sempre garanta contraste suficiente.
- **Não faça:** distorcer proporções, aplicar sombras pesadas, recolorir fora da paleta, rotacionar ou aplicar sobre fundos de baixo contraste.

---

## 6. Componentes de interface

Diretrizes de aplicação da identidade nos componentes mais comuns.

### Botões

- **Primário:** fundo Terracota `#8C4A2F`, texto branco, cantos arredondados de 8 px. Usado para a ação principal de cada tela (ex.: "Registrar atendimento").
- **Secundário:** contorno Marrom Terra `#5A3A20`, fundo transparente, texto Marrom Terra.
- **Terciário / texto:** apenas texto Terracota, sem fundo.

### Cartões e superfícies

Cartões usam fundo de superfície (`--surface`) com borda sutil (`--border`) e raio de 12 px. Valores positivos (receita, lucro) recebem realce em Dourado Antigo; valores negativos (despesas) em vermelho terroso `#B23A2E`.

### Indicadores financeiros

- **Receita / lucro positivo:** Dourado Antigo ou verde de sucesso.
- **Despesa / saldo negativo:** vermelho terroso `#B23A2E`.
- **Neutro / informativo:** Marrom Terra.

### Espaçamento

Sistema de grid base **8 px** (4 / 8 / 16 / 24 / 32). Raio de borda padrão: 8 px (botões) e 12 px (cartões).

---

## 7. Tom e voz

A comunicação do Braid System é **acolhedora, direta e livre de jargão técnico ou contábil**. Fala-se com a trancista de igual para igual, valorizando seu trabalho. Prefira frases curtas, verbos no imperativo amigável ("Registre seu atendimento") e evite termos financeiros complexos sem explicação.

---

## 8. Resumo rápido

| Elemento | Valor |
|---|---|
| Cor primária (ação) | Terracota `#8C4A2F` |
| Cor de destaque (valor) | Dourado Antigo `#C8A15A` |
| Fundo escuro | Verde Floresta `#1E2A1F` |
| Fundo claro | Bege Areia `#E7DAC1` |
| Fonte UI | Inter |
| Fonte títulos | Poppins |
| Grid base | 8 px |
| Padrão de contraste | WCAG 2.1 AA |

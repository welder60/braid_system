# Documento de Visão
## Braid System — Gestão Financeira para Trancistas

**Versão:** 1.0  
**Data:** 14 de junho de 2026  
**Status:** Rascunho

---

## 1. Introdução

### 1.1 Propósito

Este documento descreve a visão do produto **Braid System**, uma aplicação web mobile-first voltada exclusivamente para trancistas de pequeno e médio porte. Seu objetivo é permitir que a profissional registre atendimentos, acompanhe receitas e despesas e visualize a saúde financeira do negócio de forma simples, rápida e acessível, sem exigir conhecimento técnico ou contábil.

### 1.2 Escopo

O Braid System abrange:

- Registro de atendimentos realizados (valor, tempo, características);
- Cadastro e monitoramento de custos fixos e variáveis;
- Relatórios de desempenho financeiro a médio prazo;
- Controle mínimo e seguro de clientes, em conformidade com a LGPD;
- Autenticação via SSO do Google.

Estão **fora do escopo** desta versão inicial:

- Agendamento de serviços;
- Controle de estoque de insumos;
- Emissão de notas fiscais ou integração com sistemas contábeis;
- Múltiplos usuários por conta ou gestão de equipes.

### 1.3 Definições e siglas

| Termo | Definição |
|---|---|
| Trancista | Profissional especializada em tranças, box braids, twists e técnicas afins |
| Atendimento | Registro de um serviço realizado para uma cliente |
| Perfil de atendimento | Conjunto pré-definido de campos descritivos de um serviço (tipo de tranças, tamanho, quantidade, etc.) |
| SSO | Single Sign-On — autenticação delegada a um provedor externo (Google) |
| LGPD | Lei Geral de Proteção de Dados (Lei nº 13.709/2018) |
| Custo fixo | Despesa recorrente independente do volume de atendimentos (ex.: aluguel, internet) |
| Custo variável | Despesa vinculada a um atendimento específico (ex.: linha para tranças) |
| Lucro da hora trabalhada | Métrica calculada a partir do lucro líquido dividido pelo tempo total trabalhado no período |

---

## 2. Posicionamento

### 2.1 Problema

Trancistas em empreendimentos de pequeno e médio porte geralmente não dispõem de ferramentas adequadas à realidade do seu negócio. As opções existentes no mercado são genéricas demais (planilhas, ERPs) ou voltadas a salões com múltiplos colaboradores. O resultado prático é que a profissional frequentemente desconhece:

- Quanto lucra por hora trabalhada;
- Quais serviços consomem mais tempo do que rendem;
- Se o negócio está saudável financeiramente a médio prazo.

### 2.2 Solução

O Braid System resolve esse problema ao oferecer uma interface hipernichada — com campos e perfis pré-definidos para o universo das tranças — que torna o registro de atendimentos rápido e natural. O sistema processa esses dados e apresenta indicadores financeiros relevantes sem exigir que a usuária preencha formulários complexos ou entenda conceitos contábeis.

### 2.3 Declaração de posicionamento

| Campo | Conteúdo |
|---|---|
| **Para** | Trancistas autônomas ou com microempreendimento |
| **Que** | Têm dificuldade em mensurar custos e acompanhar a saúde financeira do negócio |
| **O Braid System é** | Uma aplicação web mobile-first |
| **Que** | Permite registrar atendimentos e visualizar receitas, despesas e lucro da hora trabalhada de forma simples |
| **Diferente de** | Planilhas genéricas ou sistemas de gestão de salão |
| **Nosso produto** | É hipernichado para tranças, acessível a não técnicas e projetado para o uso diário com o mínimo de passos |

---

## 3. Partes interessadas e usuários

### 3.1 Partes interessadas

| Parte interessada | Interesse |
|---|---|
| Trancista (usuária e operadora do sistema) | Compreender o desempenho financeiro do próprio negócio |
| Equipe de desenvolvimento | Entregar um produto funcional, seguro e de fácil manutenção |

### 3.2 Perfil da usuária

- **Nome:** Trancista autônoma ou MEI
- **Faixa:** Pequeno e médio porte (atendimento individual ou com poucos auxiliares não gerenciados pelo sistema)
- **Dificuldades:** Baixa familiaridade com ferramentas digitais complexas; sem tempo para preencher muitos campos; clientela majoritariamente fiel e recorrente
- **Contexto de uso:** Smartphone, frequentemente logo após terminar um atendimento

### 3.3 Necessidades da usuária

| Necessidade | Prioridade |
|---|---|
| Registrar um atendimento rapidamente, com poucos toques | Alta |
| Saber quanto lucrou no mês e no período | Alta |
| Entender quais serviços consomem mais tempo | Alta |
| Registrar custos fixos mensais de forma simples | Média |
| Registrar custos variáveis por atendimento | Média |
| Visualizar relatório de desempenho | Média |
| Ter controle mínimo de clientes sem expor dados desnecessários | Baixa |

---

## 4. Visão geral do produto

### 4.1 Perspectiva do produto

O Braid System é uma aplicação web standalone, acessada via navegador em dispositivos móveis. Não se integra, nesta versão, a nenhum sistema externo além do provedor de autenticação (Google OAuth 2.0). Os dados são armazenados na própria plataforma.

### 4.2 Premissas de design

- **Mobile-first:** toda a interface é projetada para telas de smartphone e deve funcionar sem degradação em desktop;
- **Mínimo de passos:** o registro de um atendimento comum não deve exigir mais de 3 a 4 interações;
- **Perfil pré-definido e ajustável:** o sistema oferece campos padrão do universo das tranças (tipo, técnica, tamanho, quantidade de mechas, uso de cabelo sintético, etc.), permitindo à usuária desabilitar campos irrelevantes para sua realidade local;
- **Linguagem simples:** sem jargão financeiro; indicadores apresentados em linguagem cotidiana;
- **Acessibilidade:** compatível com leitores de tela; contraste adequado; fontes legíveis.

### 4.3 Minimização de dados (LGPD)

O sistema adota o princípio da minimização de dados como diretriz central:

- O cadastro de clientes é opcional e limitado ao estritamente necessário (ex.: nome ou apelido, sem CPF, endereço ou dados sensíveis);
- Não há coleta de localização, contatos ou dados biométricos;
- Os dados de autenticação são gerenciados inteiramente pelo Google (OAuth 2.0); o sistema não armazena senhas;
- Os dados da usuária ficam associados à conta Google e podem ser excluídos a qualquer momento;
- A política de privacidade deve ser exibida de forma clara no primeiro acesso.

---

## 5. Funcionalidades do produto

### 5.1 Registro de atendimentos

- Seleção do tipo de serviço a partir de perfil pré-configurado (ex.: box braids, knotless, twist, nagô, etc.);
- Campos complementares: valor cobrado, tempo gasto (início/fim ou duração informada), custos variáveis do atendimento;
- Campo opcional de vínculo com cliente cadastrada;
- Campos de caracterização do atendimento (ex.: tamanho, quantidade de mechas, uso de cabelo sintético) configuráveis pela usuária;
- Confirmação com o mínimo de toques possível (padrões pré-preenchidos com os valores mais recentes).

### 5.2 Gestão de custos

- **Custos fixos:** cadastro de despesas mensais recorrentes (ex.: aluguel de espaço, internet, assinatura de plataformas);
- **Custos variáveis:** registro por atendimento ou em lote;
- O sistema calcula automaticamente o custo total do período e subtrai da receita para apresentar o lucro estimado.

### 5.3 Controle de clientes (minimizado)

- Cadastro simples: nome ou apelido (único campo obrigatório);
- Campos opcionais: telefone (para contato externo ao sistema, não usado para envio de mensagens pelo app), observações livres;
- Histórico de atendimentos vinculados à cliente;
- Sem coleta de dados sensíveis.

### 5.4 Painel de desempenho

Indicadores apresentados de forma visual e resumida:

- Receita bruta do período;
- Custos totais (fixos + variáveis);
- Lucro estimado;
- Lucro por hora trabalhada;
- Serviços mais realizados;
- Tempo médio por tipo de serviço;
- Evolução da receita ao longo do tempo (gráfico simples).

### 5.5 Relatórios

- Relatório mensal e por período personalizado;
- Exportação em PDF (futuro) ou visualização direta na tela;
- Linguagem interpretativa: o sistema não apenas apresenta números, mas oferece frases simples de contexto (ex.: "Você trabalhou X horas este mês e lucrou R$ Y por hora").

### 5.6 Autenticação

- Login exclusivamente via SSO do Google (OAuth 2.0) na versão inicial;
- Sem cadastro manual de senha;
- Sessão persistente com renovação automática de token.

---

## 6. Restrições

| Restrição | Descrição |
|---|---|
| Tecnologia | Django (Python) — aplicação web; banco de dados relacional |
| Interface | Mobile-first; compatível com navegadores modernos em Android e iOS |
| Autenticação | Somente Google OAuth 2.0 na versão 1.0 |
| Privacidade | Conformidade com a LGPD; coleta mínima de dados pessoais |
| Funcionalidade | Sem agendamento, sem controle de estoque na v1.0 |
| Usuário | Aplicação monousuária por conta (uma trancista por login) |

---

## 7. Intervalos de qualidade

### 7.1 Usabilidade

- Uma usuária sem experiência com sistemas de gestão deve conseguir registrar seu primeiro atendimento em menos de 5 minutos, sem treinamento;
- O fluxo de registro de atendimento rotineiro (cliente recorrente, serviço já cadastrado) deve ser concluído em no máximo 4 toques.

### 7.2 Desempenho

- Tempo de carregamento inicial inferior a 3 segundos em conexão 4G;
- Registro de atendimento deve ser salvo em menos de 1 segundo após confirmação.

### 7.3 Disponibilidade

- Disponibilidade mínima de 99% em horário comercial expandido (07h–22h, horário de Brasília).

### 7.4 Segurança e privacidade

- Comunicação exclusivamente via HTTPS;
- Tokens de autenticação armazenados de forma segura (HttpOnly cookies ou equivalente);
- Nenhum dado pessoal de clientes exposto em URLs ou logs de sistema.

---

## 8. Precedência e prioridade

| Prioridade | Funcionalidade |
|---|---|
| 1 — Essencial | Autenticação via Google SSO |
| 1 — Essencial | Registro de atendimentos com perfil pré-definido |
| 1 — Essencial | Registro de custos fixos e variáveis |
| 2 — Importante | Painel de desempenho com indicadores financeiros |
| 2 — Importante | Lucro da hora trabalhada |
| 3 — Desejável | Controle básico de clientes |
| 3 — Desejável | Relatório por período |
| 4 — Futuro | Exportação em PDF |
| 4 — Futuro | Novos provedores de autenticação (Apple, e-mail) |
| 4 — Futuro | Agendamento de serviços |

---

*Fim do documento — versão 1.0*

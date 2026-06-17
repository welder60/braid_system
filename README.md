# Braid System

Aplicação web **mobile-first** de gestão financeira desenvolvida exclusivamente para trancistas autônomas e MEIs.

## O problema

Trancistas geralmente não dispõem de ferramentas adequadas à sua realidade. Planilhas são genéricas demais; ERPs e sistemas de salão pressupõem equipes. O resultado: a profissional não sabe quanto lucra por hora, quais serviços consomem mais tempo do que rendem, nem se o negócio está saudável a médio prazo.

## A solução

O Braid System oferece uma interface hipernichada — com campos e perfis pré-definidos para o universo das tranças — que torna o registro de atendimentos rápido e natural. O sistema processa esses dados e apresenta indicadores financeiros sem exigir conhecimento técnico ou contábil.

## Funcionalidades (v1.0)

- Registro de atendimentos com perfil de serviço pré-configurado (tipo de tranças, tamanho, quantidade, etc.)
- Gestão de custos fixos e variáveis, com categorias hierárquicas
- Painel de desempenho com lucro da hora trabalhada
- Controle mínimo de clientes em conformidade com a LGPD
- Autenticação via Google (SSO)

**Fora do escopo desta versão:** agendamento, controle de estoque, emissão de notas fiscais, gestão de equipes.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Django (Python) |
| Banco de dados | SQLite (dev) / PostgreSQL (prod) |
| Autenticação | Google OAuth 2.0 |
| Interface | Mobile-first |

## Estrutura do projeto

```
braid_system/
├── braid_system/          # Configurações Django (settings, urls, wsgi)
│   └── core/              # App principal
│       ├── models/        # Modelos de dados
│       ├── views.py
│       ├── urls.py
│       └── templates/
├── docs/                  # Documentação MkDocs
├── manage.py
└── db.sqlite3
```

## Modelos principais

- **Usuario** — autenticação customizada com AbstractBaseUser
- **Estabelecimento / EstabelecimentoUsuario** — suporte a múltiplos estabelecimentos por usuário
- **Cliente** — dados mínimos necessários, com governança LGPD
- **Atendimento / Pagamento** — registro do serviço, duração e formas de pagamento
- **CaracteristicaAtendimento** — atributos configuráveis do serviço (ex.: tipo de tranças, tamanho)
- **CategoriaCusto / Custo** — estrutura hierárquica de despesas fixas e variáveis

## Como rodar localmente

```bash
# Clone e entre no diretório
git clone <repo-url>
cd braid_system

# Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instale dependências
pip install -r requirements.txt

# Aplique as migrations e suba o servidor
python manage.py migrate
python manage.py runserver
```

Ou use o atalho `rodar braid system.bat` (Windows).

## Documentação

A documentação completa (visão do produto, identidade visual) está em `/docs` e é servida via MkDocs:

```bash
mkdocs serve
```

Ou use o atalho `rodar mkdocs.bat` (Windows).

## Conformidade LGPD

Dados de clientes são coletados no mínimo necessário. Campos com dados sensíveis (ex.: alergias) são sinalizados via `contem_dado_sensivel = True` nas características de atendimento, habilitando governança diferenciada.

---

**Status:** Em desenvolvimento — v1.0 (junho 2026)

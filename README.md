# Braid System

Aplicação web **mobile-first** de gestão financeira desenvolvida exclusivamente para trancistas autônomas e MEIs.

🔗 **Aplicação:** https://www.braidsystem.com.br
📖 **Documentação:** https://welder60.github.io/braid_system

---

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
| Backend | Django 6 (Python) |
| Banco de dados | SQLite (dev) / PostgreSQL via Supabase (prod) |
| Autenticação | Google OAuth 2.0 (Authlib) |
| Storage de arquivos | Supabase Storage (protocolo S3) |
| Servidor | Gunicorn + WhiteNoise |
| Deploy | Railway |
| Observabilidade | Sentry |
| Interface | Mobile-first |

## Estrutura do projeto

```
braid_system/
├── braid_system/          # Configurações Django (settings, urls, wsgi, asgi)
│   ├── core/              # App principal
│   │   ├── models/        # Modelos de dados (atendimento, cliente, custo, etc.)
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── access.py      # Controle de acesso
│   │   └── templates/
│   └── security/          # App de segurança (headers, políticas)
├── docs/                  # Documentação MkDocs
├── Procfile               # Configuração Railway/Gunicorn
├── manage.py
└── requirements.txt
```

## Modelos principais

- **Usuario** — autenticação customizada com `AbstractBaseUser`
- **Estabelecimento / EstabelecimentoUsuario** — suporte a múltiplos estabelecimentos por usuário
- **Cliente** — dados mínimos necessários, com governança LGPD
- **Atendimento / Pagamento** — registro do serviço, duração e formas de pagamento
- **CaracteristicaAtendimento** — atributos configuráveis do serviço (ex.: tipo de tranças, tamanho)
- **CategoriaCusto / Custo** — estrutura hierárquica de despesas fixas e variáveis

## Como rodar localmente

```bash
# Clone e entre no diretório
git clone https://github.com/welder60/braid_system.git
cd braid_system

# Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instale dependências
pip install -r requirements.txt

# Configure variáveis de ambiente
cp .env.example .env  # edite com suas credenciais

# Aplique as migrations e suba o servidor
python manage.py migrate
python manage.py runserver
```


## Testes

A suíte cobre os apps `core` e `security` com **122 testes** e **90,6% de cobertura** (branch coverage).

```bash
# Rodar toda a suíte
python manage.py test braid_system.core

# Com cobertura
coverage run --rcfile=.coveragerc manage.py test braid_system.core
coverage report          # resumo no terminal
coverage html            # relatório navegável em htmlcov/index.html
```


> O comando precisa apontar para `braid_system.core` por causa do layout de pacote aninhado (`braid_system/braid_system/`).

## Deploy (Railway)

A aplicação roda em Railway com as seguintes variáveis de ambiente obrigatórias:

| Variável | Descrição |
|---|---|
| `SECRET_KEY` | Chave secreta Django |
| `DEBUG` | `False` em produção |
| `ALLOWED_HOSTS` | Domínios permitidos |
| `DATABASE_URL` | URL do PostgreSQL (Supabase) |
| `GOOGLE_CLIENT_ID` | Credencial OAuth Google |
| `GOOGLE_CLIENT_SECRET` | Credencial OAuth Google |
| `SENTRY_DSN` | DSN do projeto no Sentry |
| `AWS_*` | Credenciais Supabase Storage |

O `Procfile` executa migrations e coleta estáticos automaticamente a cada deploy:

```
release: python manage.py migrate
web: python manage.py collectstatic --noinput && gunicorn braid_system.wsgi
```

## Documentação

A documentação completa (visão do produto, identidade visual, regras de desenvolvimento e segurança) está em `/docs`, publicada via MkDocs Material em:

**https://welder60.github.io/braid_system**

Para servir localmente:

```bash
mkdocs serve
```

## Conformidade LGPD

Dados de clientes são coletados no mínimo necessário. Campos com dados sensíveis (ex.: alergias) são sinalizados via `contem_dado_sensivel = True` nas características de atendimento, habilitando governança diferenciada.

---

**Status:** Em desenvolvimento — v1.0 (junho 2026)

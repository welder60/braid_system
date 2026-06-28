# Regras de Desenvolvimento

**Versão:** 2.0  
**Data:** 28 de junho de 2026  
**Status:** Vigente

---

## 1. Princípios Fundamentais

**Simplicidade primeiro.** A solução mais simples que resolve o problema real é a certa. Evite abstrações prematuras e arquiteturas que antecipam requisitos inexistentes.

**Código legível é código correto.** Nomes claros, funções curtas e comentários onde a intenção não é óbvia valem mais do que otimizações prematuras. Um código que funciona mas ninguém entende é um passivo.

**Disciplina de escopo.** Nenhuma funcionalidade entra no sistema sem estar prevista no documento de visão ou aprovada explicitamente. Escopo rasteiro é a principal causa de atrasos.

**Segurança e privacidade por design.** Segurança e conformidade com a LGPD não são camadas a adicionar depois — são requisitos de projeto desde o primeiro commit.

**Falha rápida e ruidosa.** Prefira erros explícitos e imediatos a comportamentos silenciosos ou degradação invisível. Bugs escondidos em produção custam muito mais do que crashes em desenvolvimento.

---

## 2. Stack e Dependências

### 2.1 Stack oficial

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 / Django 6.x |
| Banco (desenvolvimento) | SQLite |
| Banco (produção) | PostgreSQL via Supabase |
| Storage (produção) | Supabase Storage (protocolo S3) |
| Autenticação | Google OAuth2 via Authlib |
| Servidor de aplicação | Gunicorn + Whitenoise |
| Observabilidade | Sentry SDK |
| Lint / formatação | Ruff |
| CI/CD | GitHub Actions |
| Documentação | MkDocs Material |

### 2.2 Gestão de dependências

Todas as dependências de produção ficam em `requirements.txt`. Ferramentas de desenvolvimento (lint, testes, type checking) ficam em `requirements-dev.txt`, que nunca chega à imagem de produção.

**Antes de adicionar qualquer pacote**, avalie: o Django já resolve isso nativamente? O pacote tem manutenção ativa? A licença é compatível? O tamanho da dependência é justificado pelo problema que resolve?

Versões usam o operador `>=` com o mínimo testado (`Django>=6.0.5`). Nunca use `==` (impede patches de segurança) nem ausência de versão (permite quebras silenciosas).

Mantenha as dependências atualizadas. Verifique regularmente por vulnerabilidades:

```bash
pip list --outdated
pip-audit   # instalar com: pip install pip-audit
```

---

## 3. Arquitetura

### 3.1 Camadas

O projeto segue uma arquitetura em três camadas dentro de cada app Django. O princípio central é **thin views, fat services**: views orquestram, a lógica de negócio vive em serviços ou métodos de model.

```
request → View → Service → Model / QuerySet
                     ↓
               (nenhuma lógica de negócio além desta linha)
```

**View** — recebe o request, valida a entrada via Form, chama o service, retorna o response. Não deve conter lógica de negócio.

**Service** — funções ou classes Python puras que implementam os casos de uso. Não importam `request`, não chamam `render`. São facilmente testáveis sem o cliente HTTP.

**Model** — define a estrutura de dados e comportamentos que pertencem exclusivamente àquela entidade (ex.: propriedades calculadas, validações de integridade). Não deve conhecer a camada de request nem de serviços.

```python
# ✅ Correto — view fina, lógica no service
def registrar_atendimento(request):
    form = AtendimentoForm(request.POST)
    if form.is_valid():
        atendimento = atendimento_service.criar(
            estabelecimento=get_estabelecimento_ativo(request),
            dados=form.cleaned_data,
        )
        messages.success(request, "Atendimento registrado.")
        return redirect("gestao")
    return render(request, "core/atendimento_form.html", {"form": form})

# ❌ Errado — lógica de negócio na view
def registrar_atendimento(request):
    duracao = int(request.POST["horas"]) * 60 + int(request.POST["minutos"])
    receita = Decimal(request.POST["valor"])
    lucro_hora = receita / (duracao / 60)
    Atendimento.objects.create(
        duracao_minutos=duracao,
        valor=receita,
        lucro_hora=lucro_hora,
        ...
    )
```

> **Estado atual:** `core/views.py` ainda concentra lógica de negócio. A migração para serviços deve ocorrer gradualmente, priorizando os módulos sob modificação ativa.

### 3.2 Estrutura de arquivos

```
braid_system/
├── braid_system/
│   ├── settings.py          # configuração por ambiente via variáveis de ambiente
│   ├── urls.py              # roteamento raiz
│   ├── core/
│   │   ├── models/          # um arquivo por model
│   │   ├── services/        # lógica de negócio (a criar)
│   │   ├── forms.py         # validação de entrada
│   │   ├── views.py         # orquestração HTTP
│   │   └── tests.py         # testes automatizados
│   └── security/
│       ├── models/
│       ├── oauth.py         # integração Google OAuth2
│       └── views.py
├── docs/                    # documentação MkDocs
├── requirements.txt
├── requirements-dev.txt
└── .github/workflows/       # CI (ci.yml) e CD (deploy.yml)
```

### 3.3 Apps Django

Cada app tem responsabilidade única e coesa. Não misture domínios. URLs de cada app são declaradas em `urls.py` local e incluídas no root com um `namespace`:

```python
# braid_system/urls.py
path("", include("braid_system.core.urls", namespace="core"))
```

---

## 4. Convenções de Código

### 4.1 Formatação e lint

A configuração vive em `pyproject.toml` (a criar) ou nas opções do `ruff.toml`. Configurações relevantes:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "S", "B", "A", "C4", "DTZ", "DJ"]
ignore = ["S101"]  # allow assert in tests
```

O CI já executa `ruff check` e `ruff format --check` em todo PR. Nenhum PR é mergeado com erros de lint.

### 4.2 Tipagem estática

Type hints são obrigatórios em funções públicas, métodos de model e funções de service. Use `mypy` para verificação estática:

```bash
mypy braid_system/ --ignore-missing-imports
```

Adicione `mypy` ao `requirements-dev.txt` e ao CI. Erros de tipo são tratados como erros de build.

```python
# ✅ Correto
def calcular_lucro_hora(receita: Decimal, horas_trabalhadas: Decimal) -> Decimal:
    if horas_trabalhadas <= 0:
        raise ValueError("Horas trabalhadas devem ser positivas")
    return receita / horas_trabalhadas

# ❌ Errado
def calcular_lucro_hora(receita, horas):
    return receita / horas
```

### 4.3 Nomenclatura

| Elemento | Convenção | Exemplo |
|---|---|---|
| Classes | PascalCase | `PerfilAtendimento` |
| Funções / métodos | snake_case | `calcular_lucro_hora` |
| Variáveis | snake_case | `custo_total` |
| Constantes de módulo | UPPER_SNAKE_CASE | `TEMPO_MINIMO_ATENDIMENTO_MINUTOS` |
| URLs (path) | kebab-case | `atendimentos/novo/` |
| Templates | snake_case + sufixo de tipo | `atendimento_form.html`, `atendimento_list.html` |
| Arquivos de service | `<dominio>_service.py` | `atendimento_service.py` |

Nomes devem ser **descritivos e sem abreviações**. `custo_total` é melhor que `ct`. `calcular_lucro_hora` é melhor que `calc_lh`.

### 4.4 Imports

Ordenação: stdlib → third-party → Django → local. O Ruff (regra `I`) aplica isso automaticamente.

```python
# stdlib
from decimal import Decimal
from datetime import date

# third-party
import sentry_sdk

# Django
from django.db import models
from django.utils.translation import gettext_lazy as _

# local
from braid_system.core.models import Atendimento
```

### 4.5 Models

Todo model deve ter:

- `__str__` definido e informativo.
- `verbose_name` e `verbose_name_plural` em português na `Meta`.
- Campos de auditoria: `criado_em` e `atualizado_em` (via `auto_now_add` / `auto_now`).

```python
class Atendimento(models.Model):
    # ...campos de domínio...
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "atendimento"
        verbose_name_plural = "atendimentos"
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        return f"Atendimento {self.pk} — {self.estabelecimento}"
```

Choices usam `TextChoices` ou `IntegerChoices`. Nunca tuplas soltas.

Campos de string nunca usam `null=True` — use `blank=True, default=""`.

Campos monetários usam `DecimalField(max_digits=10, decimal_places=2)`. Nunca `FloatField` para dinheiro.

Índices explícitos em campos usados frequentemente em filtros ou ordenação:

```python
class Meta:
    indexes = [
        models.Index(fields=["estabelecimento", "-criado_em"]),
    ]
```

### 4.6 Views

Prefira **Function-Based Views** para casos simples e lógica específica de domínio. **Class-Based Views** para CRUD padronizado (`ListView`, `DetailView`, `CreateView`, etc.).

Toda view que altera estado usa exclusivamente `POST`. Nunca `GET` para mutations.

Autenticação é obrigatória por padrão via `@login_required`. Views públicas são a exceção, não a regra, e devem ser explicitamente documentadas com um comentário explicando por que não exigem autenticação.

Views devem permanecer curtas (idealmente menos de 40 linhas). Se uma view cresce além disso, a lógica extra pertence a um service.

### 4.7 Forms

Todo dado enviado pelo usuário passa por um `Form` ou `ModelForm` antes de qualquer processamento. Nunca acesse `request.POST` diretamente para construir objetos de domínio.

Validações de negócio que dependem de múltiplos campos ficam no método `clean()` do form, não na view.

### 4.8 Templates

Templates herdam de um `base.html` único. Não há exceções.

Lógica de negócio não pertence ao template. Se você está calculando algo num template, mova para uma view, model method ou template tag.

Template tags customizadas ficam em `<app>/templatetags/` e são documentadas com docstring.

---

## 5. Banco de Dados e Migrations

### 5.1 Migrations

**Nunca edite uma migration já aplicada em produção.** Crie uma nova migration para corrigir.

Toda alteração de schema tem migration gerada automaticamente pelo Django — nunca alterações manuais no banco.

Antes de cada deploy, revise as migrations pendentes e confirme se são reversíveis onde possível (implemente `state_operations` quando necessário).

Migrations que podem demorar (ex.: adicionar índice a tabela grande) devem ser executadas separadamente do deploy, com atenção ao impacto em produção.

### 5.2 Queries

Evite queries N+1. Use `select_related` para ForeignKey/OneToOne e `prefetch_related` para M2M e reversas. Use o Django Debug Toolbar em desenvolvimento para inspecionar queries.

Queries complexas ou reutilizadas ficam em `Manager` ou `QuerySet` customizado — nunca espalhadas pelas views:

```python
class AtendimentoQuerySet(models.QuerySet):
    def do_estabelecimento(self, estabelecimento):
        return self.filter(estabelecimento=estabelecimento)

    def no_periodo(self, inicio: date, fim: date):
        return self.filter(data__range=(inicio, fim))

class AtendimentoManager(models.Manager):
    def get_queryset(self):
        return AtendimentoQuerySet(self.model, using=self._db)
```

Queries que retornam grandes volumes de dados usam `.iterator()` ou paginação. Nunca carregue um queryset inteiro na memória se puder evitar.

### 5.3 Consistência

Operações que envolvem múltiplas escritas no banco usam `transaction.atomic()`. O objetivo é que o banco nunca fique em estado parcialmente consistente:

```python
with transaction.atomic():
    atendimento = Atendimento.objects.create(...)
    Pagamento.objects.create(atendimento=atendimento, ...)
```

---

## 6. Segurança

### 6.1 Segredos e configuração

**Nunca** commite segredos (chaves, tokens, senhas, DSNs) no repositório. Use variáveis de ambiente carregadas via `python-dotenv` em desenvolvimento. Adicione `.env` ao `.gitignore`.

O `settings.py` já usa `env_required()` para variáveis obrigatórias em produção — mantenha esse padrão para qualquer novo segredo.

Audite o `.env.example` periodicamente para garantir que está atualizado com todas as variáveis esperadas.

### 6.2 Configurações de produção obrigatórias

O `settings.py` já aplica automaticamente as configurações abaixo quando `DEBUG=False`. Não as remova:

- `SECURE_SSL_REDIRECT = True` — força HTTPS
- `SESSION_COOKIE_SECURE = True` — cookie de sessão apenas via HTTPS
- `CSRF_COOKIE_SECURE = True` — cookie CSRF apenas via HTTPS
- `SECURE_PROXY_SSL_HEADER` — confia no cabeçalho do proxy Railway

### 6.3 Isolamento de dados (multi-tenant)

Este é o controle de segurança mais crítico do sistema. Cada usuária acessa exclusivamente os dados do seu estabelecimento. Toda query de dados sensíveis filtra por `request.user` ou pelo estabelecimento ativo na sessão.

```python
# ✅ Correto — dados isolados por estabelecimento
atendimentos = Atendimento.objects.filter(
    estabelecimento=get_estabelecimento_ativo(request)
)

# ❌ Crítico — expõe dados de todas as usuárias
atendimentos = Atendimento.objects.all()
```

Em code review, queries sem filtro de tenant são **bloqueadoras**.

### 6.4 LGPD

O Braid System processa dados pessoais de clientes (nome, características). As seguintes regras são mandatórias:

- Colete apenas dados estritamente necessários para a funcionalidade (princípio da minimização).
- Dados de clientes nunca são compartilhados entre estabelecimentos distintos.
- Implemente e documente o fluxo de exclusão de dados quando solicitado pela titular.
- Logs de sistema não registram dados pessoais de clientes (nome, contato). Registre IDs opacos.
- `send_default_pii=False` permanece ativo no Sentry — não altere.

### 6.5 Proteção contra ataques comuns (OWASP Top 10)

**Injeção (SQL):** Use o ORM do Django para todas as queries. Raw SQL só com `params` parametrizados — nunca interpolação de string.

**Broken Access Control:** Toda view autenticada verifica pertencimento ao estabelecimento ativo. Use `get_object_or_404` com filtro de tenant, não apenas por PK.

```python
# ✅ Correto
atendimento = get_object_or_404(
    Atendimento,
    pk=pk,
    estabelecimento=get_estabelecimento_ativo(request)
)

# ❌ Errado — qualquer usuária autenticada acessa qualquer atendimento
atendimento = get_object_or_404(Atendimento, pk=pk)
```

**CSRF:** Toda view que altera estado usa `{% csrf_token %}` no form. O middleware CSRF está ativo globalmente — não o desabilite nem em views de API.

**XSS:** O sistema de templates do Django escapa HTML automaticamente. Nunca use `{{ variavel | safe }}` com conteúdo vindo do usuário.

**Rate limiting:** Implemente rate limiting em endpoints de autenticação e em qualquer endpoint de envio de formulário para evitar abuso. Considere `django-axes` para proteção contra brute force no login.

---

## 7. Testes

### 7.1 Cobertura mínima

A suíte atual tem **122 testes e 90,6% de cobertura**. Este é o piso — a cobertura não pode regredir. O CI deve falhar se a cobertura cair abaixo de **90%**.

Configure o threshold no `.coveragerc`:

```ini
[coverage:report]
fail_under = 90
show_missing = true
branch = true
```

### 7.2 O que testar

- **Caminhos felizes:** a funcionalidade funciona quando os dados são válidos.
- **Caminhos de erro:** forms inválidos, objetos não encontrados, permissão negada.
- **Isolamento de tenant:** uma usuária não consegue acessar dados de outro estabelecimento.
- **Regressões:** todo bug corrigido ganha um teste que teria detectado o bug.

### 7.3 Organização

Use `TestCase` do Django para testes que tocam o banco; `SimpleTestCase` para lógica pura sem I/O.

Agrupe testes em classes nomeadas pelo comportamento sob teste, não pela classe testada:

```python
class IsolamentoDeTenantTests(TestCase):
    """Garante que usuárias não acessam dados de outros estabelecimentos."""

    def test_atendimento_de_outro_estabelecimento_retorna_404(self):
        ...
```

### 7.4 Dados de teste

Use factories ou fixtures para criar dados de teste — nunca construa objetos de domínio hardcoded espalhados pelos testes. Considere adotar `factory_boy` para fixtures mais expressivas e composáveis.

### 7.5 Execução

```bash
# Testes
python manage.py test braid_system.core

# Com cobertura
coverage run --rcfile=.coveragerc manage.py test braid_system.core
coverage report

# Antes de abrir PR (equivalente ao CI)
ruff check . && ruff format --check . && python manage.py test braid_system.core
```

---

## 8. CI/CD

### 8.1 Pipeline de CI (ci.yml)

Executado em todo push para `main` e `developer`, e em todo Pull Request para essas branches. O pipeline tem dois jobs em sequência:

**lint** — executa `ruff check` e `ruff format --check`. Falha rápida: se o código não está formatado, os testes nem rodam.

**test** — instala dependências, aplica migrations e executa a suíte completa. Depende do job `lint` (campo `needs: lint`).

Nenhum PR é mergeado se o CI não está verde. Sem exceções.

### 8.2 Pipeline de CD (deploy.yml)

Executado automaticamente em push para `main`, apenas após o CI passar. Faz deploy na plataforma Railway.

O `Procfile` define os comandos de release e web:

```
release: python manage.py migrate
web: python manage.py collectstatic --noinput && gunicorn braid_system.wsgi
```

### 8.3 Branches protegidas

- `main` — produção. Requer PR aprovado + CI verde. Nenhum push direto.
- `developer` — integração. Requer CI verde. PRs podem ser mergeados com aprovação.

### 8.4 Checklist pré-merge

Antes de aprovar um PR, verifique:

- [ ] CI está verde (lint + testes).
- [ ] Cobertura de testes não regrediu.
- [ ] Nenhum segredo ou dado sensível no diff.
- [ ] Migrations geradas para toda alteração de schema.
- [ ] Queries com filtro de tenant onde aplicável.
- [ ] Nenhuma lógica de negócio adicionada à camada de view.
- [ ] Type hints em funções públicas novas.
- [ ] Docstrings em funções/classes públicas novas.

---

## 9. Logging e Observabilidade

### 9.1 O que logar

Use o logger do módulo — nunca `print()`:

```python
import logging
logger = logging.getLogger(__name__)
```

| Nível | Quando usar |
|---|---|
| `DEBUG` | Informação detalhada útil durante desenvolvimento (desativado em produção) |
| `INFO` | Eventos de negócio relevantes: atendimento criado, usuária autenticada |
| `WARNING` | Situação inesperada mas recuperável: tentativa de acesso negado |
| `ERROR` | Falha que impede a operação: exception não tratada, integridade violada |
| `CRITICAL` | Falha sistêmica: banco inacessível, configuração corrompida |

### 9.2 O que NÃO logar

Por exigência da LGPD e boas práticas de segurança, **nunca registre em logs**:

- Senhas ou tokens (mesmo parcialmente).
- Dados pessoais de clientes: nome, contato, características.
- Valores financeiros associados a uma cliente específica.

Registre IDs opacos (PKs, UUIDs) em vez de dados pessoais.

### 9.3 Sentry

O Sentry está configurado para capturar exceptions e logs de nível `ERROR` ou acima em produção. Após cada deploy, monitore o painel por novos erros. Erros novos em produção têm prioridade máxima de triagem.

O `release` no Sentry deve ser preenchido com o hash do commit via CI:

```yaml
# .github/workflows/deploy.yml
env:
  GIT_COMMIT: ${{ github.sha }}
```

---

## 10. Performance

### 10.1 Regra geral

Otimize com dados, não com intuição. Antes de qualquer otimização, meça: use o Django Debug Toolbar em desenvolvimento para inspecionar queries e o Sentry Performance em produção para identificar endpoints lentos.

### 10.2 Queries

Sempre prefira um único queryset com `annotate()` e `aggregate()` a múltiplas queries em loop. A regra é: se você está iterando sobre um queryset e fazendo queries dentro do loop, há um problema de N+1.

```python
# ✅ Correto — uma query
from django.db.models import Sum
resumo = Atendimento.objects.filter(
    estabelecimento=estabelecimento,
    data__range=(inicio, fim),
).aggregate(
    total_receita=Sum("valor"),
    total_atendimentos=Count("pk"),
)

# ❌ Errado — N queries
total = 0
for atendimento in Atendimento.objects.filter(...):
    total += atendimento.valor
```

### 10.3 Caching

Para dados calculados que não mudam frequentemente (ex.: totais mensais), use o framework de cache do Django. Em desenvolvimento, o cache de memória (`LocMemCache`) é suficiente. Em produção, avalie Redis via Supabase ou Railway.

```python
from django.core.cache import cache

def get_resumo_mensal(estabelecimento, ano, mes):
    cache_key = f"resumo:{estabelecimento.pk}:{ano}:{mes}"
    resumo = cache.get(cache_key)
    if resumo is None:
        resumo = calcular_resumo(estabelecimento, ano, mes)
        cache.set(cache_key, resumo, timeout=3600)  # 1 hora
    return resumo
```

Invalide o cache ao criar, editar ou excluir dados que o afetam.

---

## 11. Acessibilidade

O Braid System é uma aplicação mobile-first cujas usuárias podem acessar via dispositivos e condições variadas. O padrão mínimo é **WCAG 2.1 nível AA**.

Diretrizes práticas:

- Todo `<img>` tem `alt` descritivo. Imagens decorativas usam `alt=""`.
- Controles de formulário têm `<label>` associado via `for`/`id`.
- A hierarquia de headings é semântica (`h1` → `h2` → `h3`), não cosmética.
- A interface é navegável integralmente por teclado (tab order lógico, focus visível).
- Contraste mínimo de 4.5:1 entre texto e fundo (verificar com o manual de identidade visual).
- Mensagens de erro de formulário são associadas ao campo correspondente via `aria-describedby`.
- Ações destrutivas (exclusão) pedem confirmação explícita.

---

## 12. Git e Controle de Versão

### 12.1 Branches

| Tipo | Padrão | Exemplo |
|---|---|---|
| Funcionalidade | `feat/<descricao>` | `feat/relatorio-mensal` |
| Correção | `fix/<descricao>` | `fix/calculo-lucro-hora` |
| Melhoria técnica | `refactor/<descricao>` | `refactor/querysets-atendimento` |
| Documentação | `docs/<descricao>` | `docs/regras-desenvolvimento` |
| Hotfix em produção | `hotfix/<descricao>` | `hotfix/csrf-token-ausente` |

### 12.2 Commits

Siga o padrão [Conventional Commits](https://www.conventionalcommits.org/):

```
<tipo>(<escopo>): <descrição curta em português>

[corpo opcional — o quê e por quê, não o como]

[rodapé opcional — refs, breaking changes]
```

Tipos válidos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`.

```
# ✅ Correto
feat(atendimento): adicionar campo de duração ao registro de serviço

Usuárias precisam registrar quanto tempo cada serviço durou para
o cálculo correto do lucro por hora trabalhada.

Closes #42

# ❌ Errado
ajuste no form
wip
fix
```

Commits atômicos: cada commit representa uma mudança coesa e compilável. Não commite código comentado ou arquivos de debug.

### 12.3 Pull Requests

- Descrição obrigatória: o que foi feito, por que e como testar.
- Um PR por funcionalidade ou correção — evite PRs que misturam múltiplos contextos.
- PRs com mais de 400 linhas alteradas devem ser justificados ou divididos.
- Toda discussão de code review deve ser resolvida antes do merge.

---

## 13. Deploy e Ambientes

| Ambiente | Branch | Banco | Debug | Notas |
|---|---|---|---|---|
| Desenvolvimento local | qualquer | SQLite | `True` | `.env` local |
| Produção | `main` | PostgreSQL (Supabase) | `False` | Sentry ativo, HTTPS forçado |

O deploy em produção é automático via CD após merge em `main`. Variáveis de ambiente de produção são gerenciadas exclusivamente na plataforma (Railway) — nunca no repositório.

**Rollback:** se um deploy causa regressão, faça revert do commit no `main` e deixe o CD fazer o rollback automaticamente.

---

## 14. Documentação

### 14.1 Código

Docstrings são obrigatórias em funções e classes públicas. Use o formato Google Style:

```python
def calcular_lucro_hora(receita: Decimal, horas_trabalhadas: Decimal) -> Decimal:
    """Calcula o lucro médio por hora trabalhada no período.

    Args:
        receita: Receita líquida total do período, em reais.
        horas_trabalhadas: Total de horas efetivamente trabalhadas no período.

    Returns:
        Lucro por hora em reais, arredondado a duas casas decimais.

    Raises:
        ValueError: Se `horas_trabalhadas` for menor ou igual a zero.
    """
```

Comentários no código explicam **por quê**, não **o quê**. O quê já está no código.

### 14.2 MkDocs

Toda decisão técnica relevante — especialmente decisões que vão contra o óbvio — deve ser documentada aqui. Inclua o contexto que levou à decisão, para que um desenvolvedor futuro entenda sem precisar perguntar.

O `README.md` na raiz deve estar sempre atualizado com instruções de setup local completas, incluindo todas as variáveis de ambiente necessárias.

### 14.3 CHANGELOG

Mantenha um `CHANGELOG.md` atualizado seguindo o formato [Keep a Changelog](https://keepachangelog.com/). Toda versão registra as mudanças em: `Added`, `Changed`, `Fixed`, `Removed`, `Security`.

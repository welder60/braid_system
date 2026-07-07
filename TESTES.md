# Testes — Braid System

Suíte de testes automatizados do app `core` e do app `security`, usando o
test runner nativo do Django (`unittest` / `TestCase`).

## Organização

Os testes vivem no pacote `braid_system/core/tests/`, separados por domínio:

| Módulo                  | Conteúdo                                         |
| ----------------------- | ------------------------------------------------ |
| `utils.py`              | helpers de criação e mixins compartilhados       |
| `test_helpers.py`       | funções utilitárias puras de `views.py`          |
| `test_models.py`        | modelos, managers e regras `on_delete`           |
| `test_access.py`        | autorização centralizada e context processor     |
| `test_urls.py`          | `reverse`/`resolve` das rotas nomeadas           |
| `test_auth.py`          | login/logout, proteção de rotas, home e perfil   |
| `test_admin_views.py`   | CRUDs do painel administrativo                   |
| `test_atendimentos.py`  | fluxo completo de atendimentos e validações      |
| `test_clientes.py`      | CRUD de clientes (multi-tenant)                  |
| `test_custos.py`        | CRUD de custos avulsos                           |
| `test_relatorios.py`    | relatórios da gestão com movimento real          |
| `test_render_edicao.py` | GET dos formulários de edição                    |
| `test_isolamento.py`    | isolamento de dados entre estabelecimentos       |
| `test_onboarding.py`    | criação do primeiro estabelecimento              |
| `test_consultor.py`     | painel do consultor e exportações CSV            |
| `test_security.py`      | login social com Google (OAuth2/OIDC, com mocks) |

Durante os testes, `settings.py` troca o hasher de senha por `MD5PasswordHasher`
(prática recomendada pela documentação do Django), o que reduziu o tempo da
suíte de minutos para poucos segundos.

## Como rodar

```bash
# requer Python 3.12+ (Django 6) e as dependências instaladas
pip install -r requirements.txt

# rodar toda a suíte
python manage.py test braid_system.core
```

> O comando **precisa** apontar para `braid_system.core`. Rodar apenas
> `python manage.py test` falha na descoberta automática por causa do layout
> de pacote aninhado (`braid_system/braid_system/`).

## Cobertura (coverage.py)

```bash
coverage run --rcfile=.coveragerc manage.py test braid_system.core
coverage report          # resumo no terminal
coverage html            # relatório navegável em htmlcov/index.html
```

Resultado atual: **252 testes**, **97,8%** de cobertura do código de produção
(modelos, `access.py`, context processor, URLs e o app `security` — incluindo
o fluxo OAuth do Google — em 100%; `core/views.py` em 97,5%).

A configuração (`.coveragerc`) mede `branch coverage` e exclui migrations,
o pacote de testes, settings e o módulo morto
`braid_system/core/models/usuario.py` (ver abaixo).

## O que é coberto

- **Funções utilitárias** de `views.py`: `_fmt_duracao`, `_parse_hora`,
  `_duracao_para_minutos`, `_parse_dinheiro` (válidos, inválidos e bordas).
- **Modelos**: `__str__`, defaults, `is_active`, `UsuarioManager`
  (`create_user`/`create_superuser`), `unique_together`, hierarquias
  (categoria/opção) e regras `on_delete` (`PROTECT`/`CASCADE`/`SET_NULL`).
- **Context processor** `estabelecimento_ativo` (auto-seleção, sessão válida,
  sessão inválida, múltiplos vínculos).
- **URLs**: `reverse`/`resolve` das rotas nomeadas.
- **Views**: login/logout, proteção de rotas autenticadas, CRUD de
  estabelecimentos, categorias, características+opções, usuários, acessos,
  clientes e custos, e o fluxo completo de atendimento (com pagamento,
  características e custos vinculados), incluindo isolamento multi-tenant
  pelo estabelecimento ativo na sessão.

## Bugs encontrados e corrigidos

1. **`Pagamento.forma_pagamento` recebia `''` numa ForeignKey** —
   `atendimento_criar`/`atendimento_editar` quebravam ao registrar o
   pagamento (erro silenciado e exibido como mensagem). O campo virou
   opcional (`null=True, blank=True`) e as views passam `None`
   (migration `0008`).

2. **Migration `0007` usava SQL exclusivo do PostgreSQL**
   (`gen_random_uuid()`, `UPDATE ... FROM`), quebrando a criação do banco
   em SQLite (dev/testes). Substituída por uma `RunPython` portável.

3. **`custos()` quebrava com `?mes=&ano=` vazios** (`int('')` →
   `ValueError`) — justamente o que `custo_criar` gerava ao redirecionar.
   Endurecido para tratar valores vazios.

## Pendência conhecida (não coberta)

A view `consultor_dashboard_caracteristicas` (final de `core/views.py`,
linhas 2706+) está **incompleta no código-fonte**: a função termina no meio
da implementação (após o cálculo do período) e não retorna `HttpResponse`.
Acessar `/consultor/dashboard-caracteristicas/` gera erro 500. Por isso ela
está fora da cobertura — ao concluir a view, adicionar os testes em
`tests/test_consultor.py`.

## Observação — código morto

`braid_system/core/models/usuario.py` é uma duplicata **não utilizada** do
modelo de usuário (o projeto usa `AUTH_USER_MODEL = 'security.Usuario'` e o
arquivo não é importado em `core/models/__init__.py`). Pode ser removido com
segurança. Está excluído da medição de cobertura.

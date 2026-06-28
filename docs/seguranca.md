# Regras de Segurança

**Versão:** 1.0  
**Data:** 28 de junho de 2026  
**Status:** Vigente

---

## 1. Princípios Gerais

**Segurança por design, não por adição.** Controles de segurança são requisitos de projeto, não patches posteriores. Toda nova funcionalidade é avaliada quanto a seus riscos de segurança antes de ser implementada.

**Menor privilégio.** Cada componente do sistema — usuário, processo, serviço — opera com o mínimo de permissões necessário para cumprir sua função.

**Defesa em profundidade.** Não dependa de um único controle de segurança. Camadas sobrepostas garantem que a falha de um controle não comprometa o sistema inteiro.

**Falha segura.** Em caso de erro, o sistema nega acesso por padrão. Um sistema que falha "aberto" é inaceitável.

**Auditabilidade.** Toda ação sensível deve ser rastreável. O sistema deve ser capaz de responder: quem fez o quê, quando e a partir de onde.

---

## 2. Gestão de Segredos e Configuração

### 2.1 Segredos nunca entram no repositório

Nenhum segredo (chave secreta, token, senha, DSN de banco, client secret OAuth) pode ser commitado no repositório, mesmo em branches de desenvolvimento, mesmo em arquivos de teste. Isso inclui:

- `SECRET_KEY` do Django
- Credenciais do banco de dados (Supabase)
- `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`
- DSN do Sentry
- Qualquer token de serviço de terceiros

O `.gitignore` já exclui `.env`. Nunca remova essa entrada. Se um segredo for acidentalmente commitado, trate como comprometido: revogue e gere novo imediatamente, mesmo que o commit tenha sido feito em branch privada.

### 2.2 Variáveis de ambiente

Todo segredo é injetado via variável de ambiente. Em desenvolvimento local, use `.env` carregado via `python-dotenv`. Em produção, as variáveis são configuradas exclusivamente na plataforma Railway.

O `settings.py` usa `env_required()` para variáveis obrigatórias — qualquer variável ausente causa falha explícita na inicialização, não comportamento silencioso e inseguro:

```python
# ✅ Correto — falha ruidosa se ausente
SECRET_KEY = env_required("DJANGO_SECRET_KEY")
DATABASE_URL = env_required("DATABASE_URL")

# ❌ Errado — silenciosamente inseguro
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-key-hardcoded")
```

Mantenha o `.env.example` atualizado com todas as variáveis esperadas e seus formatos, sem valores reais.

### 2.3 Rotação de segredos

Segredos de longa duração devem ser rotacionados periodicamente ou imediatamente após:

- Saída de um colaborador com acesso.
- Suspeita de exposição (logs, screenshots, acidente em pair programming).
- Comprometimento confirmado.

Documente a data da última rotação de cada segredo crítico.

---

## 3. Autenticação e Gerenciamento de Sessão

### 3.1 Autenticação exclusivamente via Google OAuth2

O Braid System não gerencia senhas. A autenticação é delegada inteiramente ao Google OAuth2 via Authlib. Não implemente autenticação local com senha, nem endpoints de criação de conta fora do fluxo OAuth.

Valide o `state` CSRF no callback OAuth para prevenir ataques de CSRF no fluxo de autenticação:

```python
# O Authlib gerencia o state automaticamente via session
# Certifique-se de que SESSION_COOKIE_SECURE e CSRF_COOKIE_SECURE estão ativos
```

### 3.2 Configuração de sessão

As seguintes configurações são obrigatórias em produção e já devem estar ativas no `settings.py`:

```python
SESSION_COOKIE_SECURE = True        # cookie só via HTTPS
SESSION_COOKIE_HTTPONLY = True      # cookie inacessível via JavaScript
SESSION_COOKIE_SAMESITE = "Lax"    # proteção contra CSRF cross-site
SESSION_COOKIE_AGE = 86400 * 7     # expiração em 7 dias (ajustar conforme política)
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
```

**[Pendente]** Revisar se todas essas configurações estão presentes e ativas no `settings.py` atual.

### 3.3 Encerramento de sessão

O endpoint de logout deve invalidar a sessão do lado do servidor e limpar os cookies:

```python
from django.contrib.auth import logout

def logout_view(request):
    logout(request)  # invalida a sessão no servidor
    return redirect("home")
```

Não implemente logout apenas limpando cookies no cliente — a sessão deve ser invalidada no servidor.

### 3.4 Proteção contra força bruta

**[Pendente]** Implemente `django-axes` para bloquear IPs após tentativas repetidas de autenticação falhas:

```bash
pip install django-axes
```

```python
# settings.py
INSTALLED_APPS += ["axes"]
MIDDLEWARE = ["axes.middleware.AxesMiddleware"] + MIDDLEWARE

AXES_FAILURE_LIMIT = 5          # bloqueio após 5 falhas
AXES_COOLOFF_TIME = 1           # desbloqueio após 1 hora
AXES_LOCKOUT_CALLABLE = None    # retorna 403 por padrão
AXES_RESET_ON_SUCCESS = True    # reseta contador após login bem-sucedido

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
```

---

## 4. Controle de Acesso

### 4.1 Autenticação obrigatória por padrão

Toda view exige autenticação. Views públicas são a exceção explícita e documentada. Configure o decorator padrão globalmente ou use `LoginRequiredMiddleware` do Django 5+:

```python
# settings.py (Django 5+)
MIDDLEWARE = [
    ...
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
]
```

Views genuinamente públicas são marcadas explicitamente:

```python
from django.contrib.auth.decorators import login_not_required

@login_not_required
def landing_page(request):
    """View pública intencional — página de entrada para usuárias não autenticadas."""
    return render(request, "core/landing.html")
```

### 4.2 Isolamento de tenant (controle mais crítico)

Cada usuária acessa exclusivamente os dados do seu estabelecimento. Esta é a regra de segurança mais importante do sistema e deve ser verificada em todo code review.

**Toda** query que retorna dados sensíveis filtra por tenant:

```python
# ✅ Correto — dados isolados
atendimento = get_object_or_404(
    Atendimento,
    pk=pk,
    estabelecimento=get_estabelecimento_ativo(request),
)

# ❌ Crítico — expõe dados de todas as usuárias
atendimento = get_object_or_404(Atendimento, pk=pk)
```

Queries sem filtro de tenant em dados sensíveis são **bloqueadoras** em code review, sem exceção.

**[Pendente]** Considere implementar um `Manager` customizado que aplica o filtro de tenant automaticamente, tornando o padrão seguro impossível de esquecer:

```python
class TenantManager(models.Manager):
    def for_tenant(self, request):
        return self.get_queryset().filter(
            estabelecimento=get_estabelecimento_ativo(request)
        )
```

### 4.3 Verificação de pertencimento em mutações

Operações de escrita (edição, exclusão) verificam pertencimento antes de agir, não só antes de exibir. Nunca assuma que um POST autenticado é automaticamente autorizado:

```python
def editar_atendimento(request, pk):
    # A query já verifica pertencimento — se não pertencer, 404
    atendimento = get_object_or_404(
        Atendimento,
        pk=pk,
        estabelecimento=get_estabelecimento_ativo(request),
    )
    ...
```

### 4.4 Referências diretas a objetos (IDOR)

Nunca exponha IDs sequenciais em URLs se isso permitir enumeração de recursos de outros tenants. Onde aplicável, use UUIDs como identificadores públicos:

```python
import uuid

class Atendimento(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ...
```

**[Pendente]** Avaliar adoção de UUIDs nas URLs dos recursos mais sensíveis.

---

## 5. Proteção contra Ataques Web (OWASP Top 10)

### 5.1 Injeção de SQL

Use o ORM do Django para todas as queries. Raw SQL é permitido apenas com parâmetros, nunca com interpolação de string:

```python
# ✅ Correto — parâmetros seguros
Atendimento.objects.raw(
    "SELECT * FROM core_atendimento WHERE estabelecimento_id = %s",
    [estabelecimento.pk]
)

# ❌ Crítico — vulnerável a SQL injection
Atendimento.objects.raw(
    f"SELECT * FROM core_atendimento WHERE nome = '{nome_recebido}'"
)
```

### 5.2 Cross-Site Scripting (XSS)

O sistema de templates do Django escapa HTML automaticamente. Preserve esse comportamento:

- Nunca use `{{ variavel | safe }}` com conteúdo originado do usuário.
- Nunca use `mark_safe()` com conteúdo dinâmico.
- Evite renderizar conteúdo HTML do usuário diretamente, mesmo que "sanitizado".

Se for necessário permitir HTML rico, use uma biblioteca de sanitização consolidada (ex.: `bleach`) com uma allowlist estrita de tags e atributos.

### 5.3 CSRF

O middleware CSRF do Django está ativo globalmente. Não o desative nem em views que parecem "seguras". Toda view que altera estado usa `{% csrf_token %}` no formulário:

```html
<form method="post">
  {% csrf_token %}
  ...
</form>
```

Views que recebem dados via JavaScript usam o header `X-CSRFToken`. O token é lido do cookie (não httpOnly para este propósito).

### 5.4 Clickjacking

Configure o header `X-Frame-Options` para impedir que o sistema seja embutido em iframes de outros domínios:

```python
# settings.py
X_FRAME_OPTIONS = "DENY"
```

O middleware `XFrameOptionsMiddleware` do Django já está na pilha padrão — confirme que não foi removido.

### 5.5 Headers de segurança HTTP

**[Pendente]** Adicione `django-csp` ou configure os headers via Whitenoise/Gunicorn para estabelecer uma Content Security Policy:

```python
# Mínimo recomendado — settings.py
SECURE_CONTENT_TYPE_NOSNIFF = True      # X-Content-Type-Options: nosniff
SECURE_BROWSER_XSS_FILTER = True        # X-XSS-Protection (legado, mas inofensivo)
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
```

CSP completo (recomendado adicionar futuramente):

```python
# Exemplo de CSP restritiva
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # refinar quando possível
CSP_IMG_SRC = ("'self'", "data:")
CSP_FONT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)
```

### 5.6 Upload de arquivos

**[Pendente]** Se o sistema vier a aceitar uploads de arquivos (fotos de perfil, comprovantes), aplique:

- Validação de tipo MIME no servidor, não apenas extensão.
- Limite de tamanho de arquivo.
- Armazenamento fora do diretório web-acessível (Supabase Storage, não `MEDIA_ROOT` exposto).
- Nunca execute arquivos recebidos do usuário.
- Gere novos nomes de arquivo no servidor — nunca use o nome fornecido pelo cliente.

---

## 6. HTTPS e Transporte

### 6.1 HTTPS obrigatório em produção

Todo tráfego em produção é obrigatoriamente cifrado. As configurações abaixo são aplicadas automaticamente quando `DEBUG=False` e devem permanecer intactas:

```python
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### 6.2 HSTS (HTTP Strict Transport Security)

**[Pendente]** Após confirmar que o sistema funciona exclusivamente via HTTPS sem exceções, habilite HSTS:

```python
# Começar com valor pequeno, aumentar após validação
SECURE_HSTS_SECONDS = 3600              # 1 hora inicialmente
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False             # habilitar apenas após testes exaustivos
```

> **Atenção:** HSTS é irreversível durante o período configurado. Uma vez que um browser recebe esse header, ele recusará conexões HTTP para o domínio pelo tempo configurado. Teste com valores pequenos antes de ir para 31536000 (1 ano).

---

## 7. Proteção de Dados e LGPD

### 7.1 Minimização de dados

Colete apenas dados estritamente necessários para a funcionalidade. Antes de adicionar um campo que armazena dado pessoal, pergunte: esse dado é indispensável para a funcionalidade ou é conveniência?

Dados pessoais presentes no sistema: nome do cliente, características físicas (tipo de cabelo, comprimento). Não adicione dados sensíveis (saúde, biometria além de características de cabelo, localização) sem revisão explícita de privacidade.

### 7.2 Isolamento entre estabelecimentos

Dados de clientes de um estabelecimento nunca são acessíveis por outro, nem mesmo para fins analíticos. O modelo multi-tenant é o único controle de acesso horizontal do sistema.

### 7.3 Direito à exclusão (Art. 18, LGPD)

**[Pendente]** Implemente e documente o fluxo de exclusão de dados pessoais mediante solicitação da titular:

1. Identificar todos os registros associados à cliente (Atendimento, dados de perfil).
2. Aplicar exclusão física ou anonimização irreversível (substituição por dados sintéticos).
3. Confirmar a exclusão por escrito para a solicitante.
4. Registrar o evento de exclusão em log de auditoria (sem os dados excluídos).

Anonimização é preferível à exclusão onde a integridade histórica de relatórios for relevante:

```python
def anonimizar_cliente(cliente):
    """Anonimiza dados pessoais de um cliente mantendo registros históricos."""
    cliente.nome = f"[Removido {cliente.pk}]"
    cliente.observacoes = ""
    cliente.anonimizado_em = timezone.now()
    cliente.save()
```

### 7.4 Logs sem dados pessoais

Logs de sistema nunca registram dados pessoais de clientes: nome, contato, características físicas. Registre IDs opacos (PKs ou UUIDs):

```python
# ✅ Correto
logger.info("Atendimento %d criado para cliente %d", atendimento.pk, cliente.pk)

# ❌ Errado — dados pessoais no log
logger.info("Atendimento criado para %s (%s)", cliente.nome, cliente.telefone)
```

O Sentry está configurado com `send_default_pii=False` — não altere essa configuração.

### 7.5 Retenção de dados

**[Pendente]** Defina e documente a política de retenção de dados: por quanto tempo registros de atendimentos inativos são mantidos? Implemente rotina de limpeza ou arquivamento para dados fora do período de retenção.

---

## 8. Segurança de Dependências

### 8.1 Auditoria regular

Execute regularmente:

```bash
pip-audit                    # auditoria de vulnerabilidades conhecidas
pip list --outdated          # dependências desatualizadas
```

Configure `pip-audit` no CI para bloquear builds com vulnerabilidades críticas:

```yaml
# .github/workflows/ci.yml
- name: Audit dependencies
  run: pip-audit --requirement requirements.txt --severity high
```

### 8.2 Avaliação antes de adicionar dependência

Antes de adicionar qualquer pacote, avalie:

- Tem manutenção ativa (último commit < 1 ano, issues respondidas)?
- Quantos mantenedores? Pacotes de mantenedor único são risco de abandono.
- A licença é compatível (MIT, BSD, Apache 2.0 — verificar GPL)?
- O histórico de CVEs é limpo ou gerenciado responsavelmente?
- O Django resolve isso nativamente?

### 8.3 Pinagem de versões em produção

Use o operador `>=` com mínimo testado em `requirements.txt`, mas considere gerar um `requirements.lock` com versões exatas para reproducibilidade de builds:

```bash
pip freeze > requirements.lock
```

O `requirements.lock` é usado no CI e no deploy; `requirements.txt` define as restrições de versão.

---

## 9. Segurança no CI/CD

### 9.1 Segredos no CI

Segredos usados no pipeline (deploy, auditoria) são configurados exclusivamente como GitHub Secrets — nunca hardcoded nos arquivos de workflow:

```yaml
# ✅ Correto
env:
  RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

# ❌ Errado
env:
  RAILWAY_TOKEN: "railway_token_aqui"
```

### 9.2 Permissões mínimas no workflow

Configure permissões mínimas nos workflows do GitHub Actions:

```yaml
permissions:
  contents: read
  deployments: write   # apenas no workflow de deploy
```

### 9.3 Verificação de segredos no diff

**[Pendente]** Adicione `gitleaks` ou `trufflehog` ao pipeline de CI para detectar segredos acidentalmente commitados:

```yaml
- name: Scan for secrets
  uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 9.4 Imagem de produção mínima

O `requirements-dev.txt` nunca chega à imagem de produção. Ferramentas de teste, lint e debug não são instaladas no ambiente de produção.

---

## 10. Logging de Segurança e Auditoria

### 10.1 Eventos que devem ser registrados

Os seguintes eventos de segurança devem gerar log em nível `WARNING` ou superior:

| Evento | Nível | Informação a registrar |
|---|---|---|
| Login bem-sucedido | `INFO` | user_id, IP, timestamp |
| Falha de autenticação | `WARNING` | email tentado (se disponível), IP, timestamp |
| Acesso negado (403) | `WARNING` | user_id, URL tentada, IP |
| Tentativa de acesso cross-tenant | `ERROR` | user_id, recurso tentado, tenant do recurso |
| Logout | `INFO` | user_id, timestamp |
| Exclusão de dados | `INFO` | user_id, tipo e ID do recurso excluído |

```python
# Exemplo — acesso cross-tenant detectado
logger.error(
    "Tentativa de acesso cross-tenant: usuário %d tentou acessar atendimento %d "
    "(estabelecimento %d, estabelecimento do usuário: %d)",
    request.user.pk, atendimento_pk, tenant_do_recurso, tenant_do_usuario,
)
```

### 10.2 O que NÃO registrar

- Senhas, tokens ou qualquer credencial (mesmo que inválida).
- Dados pessoais de clientes (ver seção 7.4).
- Valores financeiros associados a clientes específicos.
- Conteúdo de formulários (pode conter dados sensíveis).

### 10.3 Integridade dos logs

Logs de segurança devem ser tratados como evidência forense. Em produção (Railway + Sentry):

- Logs são armazenados fora da aplicação — não dependem do filesystem da instância.
- O acesso aos logs é restrito — apenas pessoas com acesso às plataformas.
- **[Pendente]** Defina política de retenção dos logs (recomendado: mínimo 90 dias).

---

## 11. Resposta a Incidentes

### 11.1 Definição de incidente de segurança

São considerados incidentes de segurança:

- Acesso não autorizado confirmado ou suspeito a dados de usuárias.
- Vazamento de segredos (chaves, tokens) para repositório ou log.
- Exploração confirmada ou tentativa de exploit detectada nos logs.
- Comprometimento de conta de colaborador com acesso ao sistema.
- Vulnerabilidade crítica descoberta em dependência em uso.

### 11.2 Procedimento inicial

1. **Contenção imediata:** se houver acesso ativo não autorizado, revogar credenciais ou derrubar o serviço.
2. **Preservação de evidências:** não altere logs. Capture screenshots e exporte logs antes de qualquer intervenção.
3. **Avaliação de impacto:** quais dados foram expostos? Quantas usuárias afetadas? Por quanto tempo?
4. **Comunicação:** notificar as usuárias afetadas. A LGPD exige notificação à ANPD em até 72 horas quando há risco aos titulares (Art. 48).
5. **Remediação:** corrigir a causa raiz, não apenas o sintoma.
6. **Post-mortem:** documentar o incidente, causa, impacto, remediação e controles para prevenção futura.

### 11.3 Contatos de emergência

**[Pendente]** Manter lista atualizada de contatos para acionamento em caso de incidente: responsável técnico, responsável pelo negócio, plataformas (Railway, Supabase, Google OAuth console).

---

## 12. Testes de Segurança

### 12.1 Testes obrigatórios na suíte

A suíte de testes deve cobrir os seguintes cenários de segurança:

**Isolamento de tenant:**
```python
class IsolamentoDeTenantTests(TestCase):
    def test_atendimento_de_outro_tenant_retorna_404(self):
        """Usuária não acessa atendimento de outro estabelecimento."""
        outro_atendimento = AtendimentoFactory(estabelecimento=self.outro_estabelecimento)
        response = self.client.get(reverse("core:atendimento", args=[outro_atendimento.pk]))
        self.assertEqual(response.status_code, 404)

    def test_edicao_de_atendimento_de_outro_tenant_retorna_404(self):
        """POST de edição em atendimento alheio retorna 404, não edita."""
        ...
```

**Autenticação:**
```python
class AutenticacaoTests(TestCase):
    def test_view_protegida_redireciona_usuario_nao_autenticado(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertRedirects(response, "/login/?next=/dashboard/")
```

**CSRF:**
```python
class CsrfTests(TestCase):
    def test_post_sem_token_csrf_retorna_403(self):
        self.client.enforce_csrf_checks = True
        response = self.client.post(reverse("core:criar_atendimento"), data={})
        self.assertEqual(response.status_code, 403)
```

### 12.2 Revisão de segurança em PRs

Todo PR que modifica: autenticação, controle de acesso, queries de banco, configurações de segurança ou processamento de entrada do usuário deve ser revisado com atenção redobrada. O checklist de PR inclui:

- [ ] Queries de dados sensíveis têm filtro de tenant.
- [ ] Nenhuma variável de template usa `| safe` com dado do usuário.
- [ ] Views que alteram estado exigem `POST` e verificam CSRF.
- [ ] Nenhum segredo novo foi adicionado ao código.
- [ ] Dados pessoais não aparecem em mensagens de log.

### 12.3 Varredura periódica

**[Pendente]** Realize varreduras periódicas com `bandit` (análise estática de segurança Python):

```bash
pip install bandit
bandit -r braid_system/ -ll  # reporta apenas médio e alto
```

Adicione ao CI como verificação não-bloqueante inicialmente, tornando bloqueante após resolver os achados existentes.

---

## 13. Checklist de Segurança por Fase

### Ao desenvolver uma nova funcionalidade

- [ ] A funcionalidade exige autenticação? (padrão: sim)
- [ ] Queries de dados filtram por tenant?
- [ ] Entrada do usuário é validada via Form antes de qualquer processamento?
- [ ] Dados pessoais novos são estritamente necessários?
- [ ] Logs da funcionalidade não registram dados pessoais?
- [ ] Testes de isolamento de tenant foram escritos?

### Antes de abrir um PR

- [ ] Nenhum segredo no diff.
- [ ] `pip-audit` sem achados críticos.
- [ ] `bandit` sem achados de alta severidade novos.
- [ ] Cobertura de segurança mantida.

### Antes de um deploy em produção

- [ ] Migrations revisadas — nenhuma exposição de dados durante a migração.
- [ ] Headers de segurança HTTP confirmados no ambiente de staging.
- [ ] Sentry configurado e recebendo eventos do novo ambiente (se aplicável).
- [ ] Variáveis de ambiente de produção atualizadas na plataforma.

### Periodicamente (trimestral)

- [ ] Dependências auditadas e atualizadas.
- [ ] Segredos de longa duração rotacionados.
- [ ] Logs de acesso revisados em busca de anomalias.
- [ ] Política de retenção de dados aplicada.
- [ ] Acesso às plataformas (Railway, Supabase, GitHub) revisado — revogar acessos desnecessários.

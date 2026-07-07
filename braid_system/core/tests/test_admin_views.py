"""Painel administrativo: CRUDs de cadastros e regras de acesso."""

from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from braid_system.core.models import (
    CaracteristicaAtendimento,
    CaracteristicaAtendimentoOpcao,
    CategoriaCusto,
    Estabelecimento,
    EstabelecimentoUsuario,
    FormaPagamento,
    Pagamento,
)

from .utils import (
    HASHERS_RAPIDOS,
    AdminLogadoMixin,
    Usuario,
    criar_atendimento,
    criar_estabelecimento,
    criar_usuario,
)


# ===========================================================================
# 17. Isolamento de estabelecimentos (requisito de seguranca)
# ===========================================================================
class AdminPainelAcessoTests(TestCase):
    """Painel administrativo: somente tipo='admin' acessa."""

    ROTAS = [
        "admin_painel",
        "estabelecimentos",
        "usuarios",
        "acessos_estabelecimento",
        "categorias_custo",
        "caracteristicas_atendimento",
        "formas_pagamento",
    ]

    def test_anonimo_redireciona_para_home(self):
        for nome in self.ROTAS:
            with self.subTest(rota=nome):
                self.assertRedirects(self.client.get(reverse(nome)), reverse("home"))

    def test_profissional_redireciona_para_gestao(self):
        user = criar_usuario(email="pro2@b.com", tipo="profissional")
        # Vincula a um estabelecimento para que /gestao/ resolva (200) e nao
        # dispare o redirecionamento de onboarding ao seguir o redirect.
        EstabelecimentoUsuario.objects.create(
            estabelecimento=criar_estabelecimento("Est Pro2"), usuario=user
        )
        self.client.force_login(user)
        for nome in self.ROTAS:
            with self.subTest(rota=nome):
                self.assertRedirects(self.client.get(reverse(nome)), reverse("gestao"))

    def test_consultor_nao_e_admin(self):
        # Decisao do time: 'consultor' NAO bypassa a restricao de estabelecimentos.
        user = criar_usuario(email="cons@b.com", tipo="consultor")
        EstabelecimentoUsuario.objects.create(
            estabelecimento=criar_estabelecimento("Est Cons"), usuario=user
        )
        self.client.force_login(user)
        self.assertRedirects(
            self.client.get(reverse("estabelecimentos")), reverse("gestao")
        )
        self.assertRedirects(
            self.client.get(reverse("acessos_estabelecimento")), reverse("gestao")
        )

    def test_admin_acessa_todas_as_rotas(self):
        self.client.force_login(criar_usuario(email="adm@b.com", tipo="admin"))
        for nome in self.ROTAS:
            with self.subTest(rota=nome):
                self.assertEqual(self.client.get(reverse(nome)).status_code, 200)


# ===========================================================================
# 8. CRUD de estabelecimentos
# ===========================================================================
class EstabelecimentoViewTests(AdminLogadoMixin, TestCase):
    def test_listar(self):
        criar_estabelecimento("A")
        self.assertEqual(self.client.get(reverse("estabelecimentos")).status_code, 200)

    def test_criar_valido(self):
        resp = self.client.post(
            reverse("estabelecimento_criar"), {"nome": "Novo Salao"}
        )
        self.assertRedirects(resp, reverse("estabelecimentos"))
        self.assertTrue(Estabelecimento.objects.filter(nome="Novo Salao").exists())

    def test_criar_nome_vazio_nao_cria(self):
        resp = self.client.post(reverse("estabelecimento_criar"), {"nome": "   "})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Estabelecimento.objects.count(), 0)

    def test_editar(self):
        est = criar_estabelecimento("Antigo")
        resp = self.client.post(
            reverse("estabelecimento_editar", args=[est.pk]), {"nome": "Renovado"}
        )
        self.assertRedirects(resp, reverse("estabelecimentos"))
        est.refresh_from_db()
        self.assertEqual(est.nome, "Renovado")

    def test_excluir(self):
        est = criar_estabelecimento("Para Excluir")
        resp = self.client.post(reverse("estabelecimento_excluir", args=[est.pk]))
        self.assertRedirects(resp, reverse("estabelecimentos"))
        self.assertFalse(Estabelecimento.objects.filter(pk=est.pk).exists())

    def test_excluir_protegido_redireciona_com_erro(self):
        est = criar_estabelecimento("Com Atendimento")
        criar_atendimento(est)
        resp = self.client.post(reverse("estabelecimento_excluir", args=[est.pk]))
        self.assertRedirects(resp, reverse("estabelecimentos"))
        self.assertTrue(Estabelecimento.objects.filter(pk=est.pk).exists())
        msgs = [str(m) for m in resp.wsgi_request._messages]
        self.assertTrue(any("Não é possível excluir" in m for m in msgs))

    def test_editar_inexistente_404(self):
        import uuid

        resp = self.client.post(
            reverse("estabelecimento_editar", args=[uuid.uuid4()]), {"nome": "x"}
        )
        self.assertEqual(resp.status_code, 404)

    def test_pagina_publica_cadastro(self):
        self.assertEqual(
            self.client.get(reverse("cadastro_estabelecimento")).status_code, 200
        )
        resp = self.client.post(
            reverse("cadastro_estabelecimento"), {"nome": "Via Cadastro"}
        )
        self.assertRedirects(resp, reverse("cadastro_estabelecimento"))
        self.assertTrue(Estabelecimento.objects.filter(nome="Via Cadastro").exists())


@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class CadastroEstabelecimentoTests(AdminLogadoMixin, TestCase):
    def test_post_sem_nome_nao_cria(self):
        resp = self.client.post(reverse("cadastro_estabelecimento"), {"nome": "  "})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Estabelecimento.objects.count(), 0)

    def test_post_valido_cria_e_redireciona(self):
        resp = self.client.post(
            reverse("cadastro_estabelecimento"), {"nome": "Novo Salao"}
        )
        self.assertRedirects(resp, reverse("cadastro_estabelecimento"))
        self.assertTrue(Estabelecimento.objects.filter(nome="Novo Salao").exists())


# ===========================================================================
# 9. CRUD de categorias de custo
# ===========================================================================
class CategoriaCustoViewTests(AdminLogadoMixin, TestCase):
    def test_listar(self):
        self.assertEqual(self.client.get(reverse("categorias_custo")).status_code, 200)

    def test_criar_com_flag_vinculado(self):
        resp = self.client.post(
            reverse("categoria_custo_criar"),
            {"nome": "Material", "vinculado_atendimento": "on"},
        )
        self.assertRedirects(resp, reverse("categorias_custo"))
        cat = CategoriaCusto.objects.get(nome="Material")
        self.assertTrue(cat.vinculado_atendimento)

    def test_criar_subcategoria(self):
        pai = CategoriaCusto.objects.create(nome="Pai")
        resp = self.client.post(
            reverse("categoria_custo_criar"),
            {"nome": "Filha", "nivel_superior": str(pai.pk)},
        )
        self.assertRedirects(resp, reverse("categorias_custo"))
        self.assertEqual(CategoriaCusto.objects.get(nome="Filha").nivel_superior, pai)

    def test_criar_sem_nome(self):
        resp = self.client.post(reverse("categoria_custo_criar"), {"nome": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(CategoriaCusto.objects.count(), 0)

    def test_editar(self):
        cat = CategoriaCusto.objects.create(nome="Velho")
        resp = self.client.post(
            reverse("categoria_custo_editar", args=[cat.pk]), {"nome": "Novo"}
        )
        self.assertRedirects(resp, reverse("categorias_custo"))
        cat.refresh_from_db()
        self.assertEqual(cat.nome, "Novo")

    def test_excluir(self):
        cat = CategoriaCusto.objects.create(nome="X")
        resp = self.client.post(reverse("categoria_custo_excluir", args=[cat.pk]))
        self.assertRedirects(resp, reverse("categorias_custo"))
        self.assertEqual(CategoriaCusto.objects.count(), 0)


# ===========================================================================
# 10. CRUD de caracteristicas e suas opcoes
# ===========================================================================
class CaracteristicaViewTests(AdminLogadoMixin, TestCase):
    def test_criar_valido(self):
        resp = self.client.post(
            reverse("caracteristica_atendimento_criar"),
            {
                "nome": "Tipo",
                "pergunta": "Qual tipo?",
                "ordem": "1",
                "numero_maximo_selecao": "2",
                "contem_dado_sensivel": "on",
            },
        )
        self.assertRedirects(resp, reverse("caracteristicas_atendimento"))
        c = CaracteristicaAtendimento.objects.get(nome="Tipo")
        self.assertEqual(c.numero_maximo_selecao, 2)
        self.assertTrue(c.contem_dado_sensivel)

    def test_criar_faltando_campos(self):
        resp = self.client.post(
            reverse("caracteristica_atendimento_criar"), {"nome": "Tipo"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(CaracteristicaAtendimento.objects.count(), 0)

    def test_editar(self):
        c = CaracteristicaAtendimento.objects.create(ordem=1, nome="A", pergunta="Q")
        resp = self.client.post(
            reverse("caracteristica_atendimento_editar", args=[c.pk]),
            {"nome": "B", "pergunta": "Q2", "ordem": "3"},
        )
        self.assertRedirects(resp, reverse("caracteristicas_atendimento"))
        c.refresh_from_db()
        self.assertEqual((c.nome, c.ordem), ("B", 3))

    def test_excluir(self):
        c = CaracteristicaAtendimento.objects.create(ordem=1, nome="A", pergunta="Q")
        resp = self.client.post(
            reverse("caracteristica_atendimento_excluir", args=[c.pk])
        )
        self.assertRedirects(resp, reverse("caracteristicas_atendimento"))
        self.assertEqual(CaracteristicaAtendimento.objects.count(), 0)

    def test_opcoes_crud(self):
        c = CaracteristicaAtendimento.objects.create(ordem=1, nome="Tipo", pergunta="Q")
        # listar
        self.assertEqual(
            self.client.get(
                reverse("caracteristica_atendimento_opcoes", args=[c.pk])
            ).status_code,
            200,
        )
        # criar
        resp = self.client.post(
            reverse("opcao_caracteristica_criar", args=[c.pk]), {"nome": "Box braids"}
        )
        self.assertRedirects(
            resp, reverse("caracteristica_atendimento_opcoes", args=[c.pk])
        )
        opcao = CaracteristicaAtendimentoOpcao.objects.get(nome="Box braids")
        # criar subopcao
        self.client.post(
            reverse("opcao_caracteristica_criar", args=[c.pk]),
            {"nome": "Fina", "nivel_superior": str(opcao.pk)},
        )
        self.assertEqual(
            CaracteristicaAtendimentoOpcao.objects.get(nome="Fina").nivel_superior,
            opcao,
        )
        # editar
        self.client.post(
            reverse("opcao_caracteristica_editar", args=[c.pk, opcao.pk]),
            {"nome": "Box braids G"},
        )
        opcao.refresh_from_db()
        self.assertEqual(opcao.nome, "Box braids G")
        # excluir
        resp = self.client.post(
            reverse("opcao_caracteristica_excluir", args=[c.pk, opcao.pk])
        )
        self.assertRedirects(
            resp, reverse("caracteristica_atendimento_opcoes", args=[c.pk])
        )


# ===========================================================================
# 11. CRUD de usuarios (painel admin)
# ===========================================================================
class UsuarioViewTests(AdminLogadoMixin, TestCase):
    def test_listar(self):
        self.assertEqual(self.client.get(reverse("usuarios")).status_code, 200)

    def test_criar_valido(self):
        resp = self.client.post(
            reverse("usuario_criar"),
            {
                "nome": "Nova",
                "email": "nova@b.com",
                "tipo": "profissional",
                "password": "senha123456",
            },
        )
        self.assertRedirects(resp, reverse("usuarios"))
        self.assertTrue(Usuario.objects.filter(email="nova@b.com").exists())

    def test_criar_email_duplicado(self):
        criar_usuario(email="dup@b.com")
        resp = self.client.post(
            reverse("usuario_criar"),
            {
                "nome": "X",
                "email": "dup@b.com",
                "tipo": "profissional",
                "password": "senha123456",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Usuario.objects.filter(email="dup@b.com").count(), 1)

    def test_criar_campos_faltando(self):
        resp = self.client.post(reverse("usuario_criar"), {"nome": "X"})
        self.assertEqual(resp.status_code, 200)
        # admin logado ja conta como 1 usuario; garantimos que o alvo nao foi criado
        self.assertFalse(Usuario.objects.filter(nome="X").exists())

    def test_editar_desativa(self):
        u = criar_usuario(email="e@b.com", nome="Edita")
        resp = self.client.post(
            reverse("usuario_editar", args=[u.pk]),
            {"nome": "Editada", "tipo": "gerente", "ativo": "0"},
        )
        self.assertRedirects(resp, reverse("usuarios"))
        u.refresh_from_db()
        self.assertEqual(u.nome, "Editada")
        self.assertEqual(u.tipo, "gerente")
        self.assertFalse(u.ativo)

    def test_excluir(self):
        u = criar_usuario(email="x@b.com")
        resp = self.client.post(reverse("usuario_excluir", args=[u.pk]))
        self.assertRedirects(resp, reverse("usuarios"))
        self.assertFalse(Usuario.objects.filter(pk=u.pk).exists())


# ===========================================================================
# 12. CRUD de acessos (vinculo usuario <-> estabelecimento)
# ===========================================================================
class AcessoViewTests(TestCase):
    def setUp(self):
        self.admin = criar_usuario(email="admin@b.com", nome="Admin", tipo="admin")
        self.client.force_login(self.admin)
        self.est = criar_estabelecimento("Est A")
        self.alvo = criar_usuario(email="alvo@b.com", nome="Alvo")

    def test_listar(self):
        self.assertEqual(
            self.client.get(reverse("acessos_estabelecimento")).status_code, 200
        )

    def test_criar_registra_incluido_por(self):
        resp = self.client.post(
            reverse("acesso_criar"),
            {
                "usuario": str(self.alvo.pk),
                "estabelecimento": str(self.est.pk),
                "tipo_acesso": "editar",
            },
        )
        self.assertRedirects(resp, reverse("acessos_estabelecimento"))
        vinc = EstabelecimentoUsuario.objects.get(
            usuario=self.alvo, estabelecimento=self.est
        )
        self.assertEqual(vinc.tipo_acesso, "editar")
        self.assertEqual(vinc.incluido_por, self.admin)

    def test_criar_duplicado(self):
        EstabelecimentoUsuario.objects.create(
            usuario=self.alvo, estabelecimento=self.est
        )
        resp = self.client.post(
            reverse("acesso_criar"),
            {
                "usuario": str(self.alvo.pk),
                "estabelecimento": str(self.est.pk),
                "tipo_acesso": "ver",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(EstabelecimentoUsuario.objects.count(), 1)

    def test_criar_campos_faltando(self):
        resp = self.client.post(reverse("acesso_criar"), {"usuario": str(self.alvo.pk)})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(EstabelecimentoUsuario.objects.count(), 0)

    def test_editar_tipo_acesso(self):
        vinc = EstabelecimentoUsuario.objects.create(
            usuario=self.alvo, estabelecimento=self.est, tipo_acesso="ver"
        )
        resp = self.client.post(
            reverse("acesso_editar", args=[vinc.pk]), {"tipo_acesso": "administrar"}
        )
        self.assertRedirects(resp, reverse("acessos_estabelecimento"))
        vinc.refresh_from_db()
        self.assertEqual(vinc.tipo_acesso, "administrar")

    def test_excluir(self):
        vinc = EstabelecimentoUsuario.objects.create(
            usuario=self.alvo, estabelecimento=self.est
        )
        resp = self.client.post(reverse("acesso_excluir", args=[vinc.pk]))
        self.assertRedirects(resp, reverse("acessos_estabelecimento"))
        self.assertEqual(EstabelecimentoUsuario.objects.count(), 0)

    def test_filtro_por_estabelecimento(self):
        outro = criar_estabelecimento("Est B")
        EstabelecimentoUsuario.objects.create(
            usuario=self.alvo, estabelecimento=self.est
        )
        EstabelecimentoUsuario.objects.create(usuario=self.alvo, estabelecimento=outro)
        resp = self.client.get(
            reverse("acessos_estabelecimento"), {"estabelecimento": str(self.est.pk)}
        )
        self.assertEqual(resp.context["total_acessos"], 1)


# ===========================================================================
# Formas de pagamento — CRUD completo (painel admin)
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class FormaPagamentoViewTests(AdminLogadoMixin, TestCase):
    def test_listar(self):
        # A migracao 0009 ja semeia PIX/Debito/Credito/Dinheiro.
        baseline = FormaPagamento.objects.count()
        FormaPagamento.objects.create(nome="Vale Presente")
        resp = self.client.get(reverse("formas_pagamento"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_formas"], baseline + 1)

    def test_criar_valido(self):
        resp = self.client.post(
            reverse("forma_pagamento_criar"), {"nome": "Vale Presente", "padrao": "on"}
        )
        self.assertRedirects(resp, reverse("formas_pagamento"))
        forma = FormaPagamento.objects.get(nome="Vale Presente")
        self.assertTrue(forma.padrao)
        # A nova padrao rebaixa a padrao anterior (PIX, semeada na migracao).
        self.assertEqual(FormaPagamento.objects.filter(padrao=True).count(), 1)

    def test_criar_sem_nome_nao_cria(self):
        baseline = FormaPagamento.objects.count()
        resp = self.client.post(reverse("forma_pagamento_criar"), {"nome": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(FormaPagamento.objects.count(), baseline)

    def test_editar(self):
        forma = FormaPagamento.objects.create(nome="Dinheiro")
        resp = self.client.post(
            reverse("forma_pagamento_editar", args=[forma.pk]),
            {"nome": "Especie", "padrao": "on"},
        )
        self.assertRedirects(resp, reverse("formas_pagamento"))
        forma.refresh_from_db()
        self.assertEqual(forma.nome, "Especie")
        self.assertTrue(forma.padrao)

    def test_editar_sem_nome_nao_altera(self):
        forma = FormaPagamento.objects.create(nome="Dinheiro")
        resp = self.client.post(
            reverse("forma_pagamento_editar", args=[forma.pk]), {"nome": " "}
        )
        self.assertEqual(resp.status_code, 200)
        forma.refresh_from_db()
        self.assertEqual(forma.nome, "Dinheiro")

    def test_editar_get_exibe_form(self):
        forma = FormaPagamento.objects.create(nome="Dinheiro")
        resp = self.client.get(reverse("forma_pagamento_editar", args=[forma.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["editando"], forma)

    def test_excluir(self):
        forma = FormaPagamento.objects.create(nome="Cheque")
        resp = self.client.post(reverse("forma_pagamento_excluir", args=[forma.pk]))
        self.assertRedirects(resp, reverse("formas_pagamento"))
        self.assertFalse(FormaPagamento.objects.filter(pk=forma.pk).exists())

    def test_excluir_protegida_por_pagamento(self):
        est = criar_estabelecimento()
        at = criar_atendimento(est)
        forma = FormaPagamento.objects.create(nome="Pix")
        Pagamento.objects.create(
            atendimento=at, forma_pagamento=forma, valor=Decimal("10")
        )
        resp = self.client.post(reverse("forma_pagamento_excluir", args=[forma.pk]))
        self.assertRedirects(resp, reverse("formas_pagamento"))
        self.assertTrue(FormaPagamento.objects.filter(pk=forma.pk).exists())


# ===========================================================================
# Ramos de validacao dos formularios do painel admin
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class EdicaoRamosAdminTests(AdminLogadoMixin, TestCase):
    def test_estabelecimento_editar_sem_nome(self):
        est = criar_estabelecimento("Original")
        resp = self.client.post(
            reverse("estabelecimento_editar", args=[est.pk]), {"nome": ""}
        )
        self.assertEqual(resp.status_code, 200)
        est.refresh_from_db()
        self.assertEqual(est.nome, "Original")

    def test_categoria_editar_sem_nome(self):
        cat = CategoriaCusto.objects.create(nome="Insumos")
        resp = self.client.post(
            reverse("categoria_custo_editar", args=[cat.pk]), {"nome": " "}
        )
        self.assertEqual(resp.status_code, 200)
        cat.refresh_from_db()
        self.assertEqual(cat.nome, "Insumos")

    def test_categoria_editar_pai_igual_a_si_mesma_vira_raiz(self):
        pai = CategoriaCusto.objects.create(nome="Pai")
        cat = CategoriaCusto.objects.create(nome="Filha", nivel_superior=pai)
        resp = self.client.post(
            reverse("categoria_custo_editar", args=[cat.pk]),
            {"nome": "Filha", "nivel_superior": str(cat.pk)},
        )
        self.assertRedirects(resp, reverse("categorias_custo"))
        cat.refresh_from_db()
        self.assertIsNone(cat.nivel_superior)

    def test_caracteristica_editar_faltando_campos(self):
        car = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Qual?"
        )
        resp = self.client.post(
            reverse("caracteristica_atendimento_editar", args=[car.pk]),
            {"nome": "Tipo", "pergunta": "", "ordem": "1"},
        )
        self.assertEqual(resp.status_code, 200)
        car.refresh_from_db()
        self.assertEqual(car.pergunta, "Qual?")

    def test_opcao_criar_get_exibe_form(self):
        car = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Qual?"
        )
        resp = self.client.get(reverse("opcao_caracteristica_criar", args=[car.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_opcao_criar_sem_nome(self):
        car = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Qual?"
        )
        resp = self.client.post(
            reverse("opcao_caracteristica_criar", args=[car.pk]), {"nome": ""}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(CaracteristicaAtendimentoOpcao.objects.count(), 0)

    def test_opcao_editar_sem_nome(self):
        car = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Qual?"
        )
        opcao = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=car, nome="Box"
        )
        resp = self.client.post(
            reverse("opcao_caracteristica_editar", args=[car.pk, opcao.pk]),
            {"nome": " "},
        )
        self.assertEqual(resp.status_code, 200)
        opcao.refresh_from_db()
        self.assertEqual(opcao.nome, "Box")

    def test_opcao_editar_pai_igual_a_si_mesma_vira_raiz(self):
        car = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Qual?"
        )
        raiz = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=car, nome="Raiz"
        )
        opcao = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=car, nome="Box", nivel_superior=raiz
        )
        resp = self.client.post(
            reverse("opcao_caracteristica_editar", args=[car.pk, opcao.pk]),
            {"nome": "Box", "nivel_superior": str(opcao.pk)},
        )
        self.assertRedirects(
            resp, reverse("caracteristica_atendimento_opcoes", args=[car.pk])
        )
        opcao.refresh_from_db()
        self.assertIsNone(opcao.nivel_superior)

    def test_usuario_editar_faltando_campos(self):
        alvo = criar_usuario(email="alvo@b.com", nome="Alvo")
        resp = self.client.post(
            reverse("usuario_editar", args=[alvo.pk]), {"nome": "", "tipo": ""}
        )
        self.assertEqual(resp.status_code, 200)
        alvo.refresh_from_db()
        self.assertEqual(alvo.nome, "Alvo")

    def test_acesso_editar_sem_tipo(self):
        est = criar_estabelecimento()
        alvo = criar_usuario(email="alvo@b.com")
        acesso = EstabelecimentoUsuario.objects.create(
            estabelecimento=est, usuario=alvo, tipo_acesso="visualizar"
        )
        resp = self.client.post(
            reverse("acesso_editar", args=[acesso.pk]), {"tipo_acesso": ""}
        )
        self.assertEqual(resp.status_code, 200)
        acesso.refresh_from_db()
        self.assertEqual(acesso.tipo_acesso, "visualizar")

    def test_acessos_filtro_por_usuario(self):
        est = criar_estabelecimento()
        alvo = criar_usuario(email="alvo@b.com")
        outro = criar_usuario(email="outro@b.com")
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=alvo)
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=outro)
        resp = self.client.get(
            reverse("acessos_estabelecimento"), {"usuario": str(alvo.pk)}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_acessos"], 1)


# ===========================================================================
# GET em rotas de exclusao nao remove nada (exigem POST)
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class ExcluirViaGetNaoRemoveTests(AdminLogadoMixin, TestCase):
    def test_get_nao_exclui_objetos_admin(self):
        est = criar_estabelecimento()
        cat = CategoriaCusto.objects.create(nome="Insumos")
        car = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Qual?"
        )
        opcao = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=car, nome="Box"
        )
        usuario = criar_usuario(email="alvo@b.com")
        acesso = EstabelecimentoUsuario.objects.create(
            estabelecimento=est, usuario=usuario
        )
        forma = FormaPagamento.objects.create(nome="Pix")

        rotas = [
            ("estabelecimento_excluir", [est.pk]),
            ("categoria_custo_excluir", [cat.pk]),
            ("caracteristica_atendimento_excluir", [car.pk]),
            ("opcao_caracteristica_excluir", [car.pk, opcao.pk]),
            ("usuario_excluir", [usuario.pk]),
            ("acesso_excluir", [acesso.pk]),
            ("forma_pagamento_excluir", [forma.pk]),
        ]
        for nome, args in rotas:
            with self.subTest(rota=nome):
                resp = self.client.get(reverse(nome, args=args))
                self.assertEqual(resp.status_code, 302)

        self.assertTrue(Estabelecimento.objects.filter(pk=est.pk).exists())
        self.assertTrue(CategoriaCusto.objects.filter(pk=cat.pk).exists())
        self.assertTrue(CaracteristicaAtendimento.objects.filter(pk=car.pk).exists())
        self.assertTrue(
            CaracteristicaAtendimentoOpcao.objects.filter(pk=opcao.pk).exists()
        )
        self.assertTrue(type(usuario).objects.filter(pk=usuario.pk).exists())
        self.assertTrue(EstabelecimentoUsuario.objects.filter(pk=acesso.pk).exists())
        self.assertTrue(FormaPagamento.objects.filter(pk=forma.pk).exists())


# ===========================================================================
# Upload de ilustracao (_salvar_ilustracao)
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class IlustracaoUploadTests(AdminLogadoMixin, TestCase):
    def test_criar_categoria_com_arquivo(self):
        import tempfile

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                arquivo = SimpleUploadedFile(
                    "icone.png", b"fake-png-bytes", content_type="image/png"
                )
                resp = self.client.post(
                    reverse("categoria_custo_criar"),
                    {"nome": "Com Icone", "ilustracao_arquivo": arquivo},
                )
                self.assertRedirects(resp, reverse("categorias_custo"))
                cat = CategoriaCusto.objects.get(nome="Com Icone")
                self.assertIn("icone", cat.ilustracao)

    def test_editar_sem_ilustracao_mantem_atual(self):
        cat = CategoriaCusto.objects.create(nome="Insumos", ilustracao="🧴")
        resp = self.client.post(
            reverse("categoria_custo_editar", args=[cat.pk]),
            {"nome": "Insumos", "ilustracao": ""},
        )
        self.assertRedirects(resp, reverse("categorias_custo"))
        cat.refresh_from_db()
        self.assertEqual(cat.ilustracao, "🧴")

    def test_texto_substitui_ilustracao(self):
        cat = CategoriaCusto.objects.create(nome="Insumos", ilustracao="🧴")
        resp = self.client.post(
            reverse("categoria_custo_editar", args=[cat.pk]),
            {"nome": "Insumos", "ilustracao": "💇"},
        )
        self.assertRedirects(resp, reverse("categorias_custo"))
        cat.refresh_from_db()
        self.assertEqual(cat.ilustracao, "💇")

from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("gestao/", views.gestao, name="gestao"),
    path("perfil/", views.perfil, name="perfil"),
    path(
        "estabelecimentos/novo/",
        views.cadastro_estabelecimento,
        name="cadastro_estabelecimento",
    ),
    path(
        "bem-vindo/estabelecimento/",
        views.onboarding_estabelecimento,
        name="onboarding_estabelecimento",
    ),
    # Usuarios
    path("admin-painel/usuarios/", views.usuarios, name="usuarios"),
    path("admin-painel/usuarios/criar/", views.usuario_criar, name="usuario_criar"),
    path(
        "admin-painel/usuarios/<uuid:pk>/editar/",
        views.usuario_editar,
        name="usuario_editar",
    ),
    path(
        "admin-painel/usuarios/<uuid:pk>/excluir/",
        views.usuario_excluir,
        name="usuario_excluir",
    ),
    # Estabelecimentos
    path(
        "admin-painel/estabelecimentos/",
        views.estabelecimentos,
        name="estabelecimentos",
    ),
    path(
        "admin-painel/estabelecimentos/criar/",
        views.estabelecimento_criar,
        name="estabelecimento_criar",
    ),
    path(
        "admin-painel/estabelecimentos/<uuid:pk>/editar/",
        views.estabelecimento_editar,
        name="estabelecimento_editar",
    ),
    path(
        "admin-painel/estabelecimentos/<uuid:pk>/excluir/",
        views.estabelecimento_excluir,
        name="estabelecimento_excluir",
    ),
    path("admin-painel/", views.admin_painel, name="admin_painel"),
    # Categorias de Custo
    path(
        "admin-painel/categorias-custo/",
        views.categorias_custo,
        name="categorias_custo",
    ),
    path(
        "admin-painel/categorias-custo/criar/",
        views.categoria_custo_criar,
        name="categoria_custo_criar",
    ),
    path(
        "admin-painel/categorias-custo/<uuid:pk>/editar/",
        views.categoria_custo_editar,
        name="categoria_custo_editar",
    ),
    path(
        "admin-painel/categorias-custo/<uuid:pk>/excluir/",
        views.categoria_custo_excluir,
        name="categoria_custo_excluir",
    ),
    # Caracteristicas de Atendimento
    path(
        "admin-painel/caracteristicas-atendimento/",
        views.caracteristicas_atendimento,
        name="caracteristicas_atendimento",
    ),
    path(
        "admin-painel/caracteristicas-atendimento/criar/",
        views.caracteristica_atendimento_criar,
        name="caracteristica_atendimento_criar",
    ),
    path(
        "admin-painel/caracteristicas-atendimento/<uuid:pk>/editar/",
        views.caracteristica_atendimento_editar,
        name="caracteristica_atendimento_editar",
    ),
    path(
        "admin-painel/caracteristicas-atendimento/<uuid:pk>/excluir/",
        views.caracteristica_atendimento_excluir,
        name="caracteristica_atendimento_excluir",
    ),
    path(
        "admin-painel/caracteristicas-atendimento/<uuid:pk>/opcoes/",
        views.caracteristica_atendimento_opcoes,
        name="caracteristica_atendimento_opcoes",
    ),
    path(
        "admin-painel/caracteristicas-atendimento/<uuid:pk>/opcoes/criar/",
        views.opcao_caracteristica_criar,
        name="opcao_caracteristica_criar",
    ),
    path(
        "admin-painel/caracteristicas-atendimento/<uuid:pk>/opcoes/<uuid:opcao_pk>/editar/",
        views.opcao_caracteristica_editar,
        name="opcao_caracteristica_editar",
    ),
    path(
        "admin-painel/caracteristicas-atendimento/<uuid:pk>/opcoes/<uuid:opcao_pk>/excluir/",
        views.opcao_caracteristica_excluir,
        name="opcao_caracteristica_excluir",
    ),
    # Acessos
    path(
        "admin-painel/acessos/",
        views.acessos_estabelecimento,
        name="acessos_estabelecimento",
    ),
    path("admin-painel/acessos/criar/", views.acesso_criar, name="acesso_criar"),
    path(
        "admin-painel/acessos/<uuid:pk>/editar/",
        views.acesso_editar,
        name="acesso_editar",
    ),
    path(
        "admin-painel/acessos/<uuid:pk>/excluir/",
        views.acesso_excluir,
        name="acesso_excluir",
    ),
    # Formas de Pagamento
    path(
        "admin-painel/formas-pagamento/",
        views.formas_pagamento,
        name="formas_pagamento",
    ),
    path(
        "admin-painel/formas-pagamento/criar/",
        views.forma_pagamento_criar,
        name="forma_pagamento_criar",
    ),
    path(
        "admin-painel/formas-pagamento/<uuid:pk>/editar/",
        views.forma_pagamento_editar,
        name="forma_pagamento_editar",
    ),
    path(
        "admin-painel/formas-pagamento/<uuid:pk>/excluir/",
        views.forma_pagamento_excluir,
        name="forma_pagamento_excluir",
    ),
    # Modulos principais
    path("atendimentos/", views.atendimentos, name="atendimentos"),
    path("atendimentos/criar/", views.atendimento_criar, name="atendimento_criar"),
    path(
        "atendimentos/verificar/",
        views.atendimento_verificar,
        name="atendimento_verificar",
    ),
    path(
        "atendimentos/<uuid:pk>/editar/",
        views.atendimento_editar,
        name="atendimento_editar",
    ),
    path(
        "atendimentos/<uuid:pk>/excluir/",
        views.atendimento_excluir,
        name="atendimento_excluir",
    ),
    path("custos/", views.custos, name="custos"),
    path("custos/criar/", views.custo_criar, name="custo_criar"),
    path("custos/<uuid:pk>/editar/", views.custo_editar, name="custo_editar"),
    path("custos/<uuid:pk>/excluir/", views.custo_excluir, name="custo_excluir"),
    path("clientes/", views.clientes, name="clientes"),
    path("clientes/criar/", views.cliente_criar, name="cliente_criar"),
    path("clientes/<uuid:pk>/editar/", views.cliente_editar, name="cliente_editar"),
    path("clientes/<uuid:pk>/excluir/", views.cliente_excluir, name="cliente_excluir"),
    path("relatorios/", views.relatorios, name="relatorios"),
    # Painel do Consultor
    path("consultor/", views.consultor_painel, name="consultor_painel"),
    path(
        "consultor/relatorios/", views.consultor_relatorios, name="consultor_relatorios"
    ),
    path(
        "consultor/exportar-csv/",
        views.consultor_exportar_csv,
        name="consultor_exportar_csv",
    ),
    path(
        "consultor/relatorios/atendimentos/",
        views.consultor_relatorio_atendimentos,
        name="consultor_relatorio_atendimentos",
    ),
    path(
        "consultor/relatorios/atendimentos/csv/",
        views.consultor_exportar_csv_atendimentos,
        name="consultor_exportar_csv_atendimentos",
    ),
    path(
        "consultor/dashboard-caracteristicas/",
        views.consultor_dashboard_caracteristicas,
        name="consultor_dashboard_caracteristicas",
    ),
]

"""
Suite de testes do Braid System (apps core + security).

Modulos:
    utils ................. helpers de criacao e mixins compartilhados
    test_helpers .......... funcoes utilitarias puras de views.py
    test_models ........... modelos (managers, __str__, defaults, on_delete)
    test_access ........... autorizacao centralizada e context processor
    test_urls ............. resolucao/reverse das URLs nomeadas
    test_auth ............. login/logout, protecao de rotas, home e perfil
    test_admin_views ...... CRUDs do painel administrativo
    test_atendimentos ..... fluxo completo de atendimentos
    test_clientes ......... CRUD de clientes (multi-tenant)
    test_custos ........... CRUD de custos avulsos
    test_relatorios ....... relatorios da gestao
    test_render_edicao .... GET dos formularios de edicao
    test_isolamento ....... isolamento de dados entre estabelecimentos
    test_onboarding ....... criacao do primeiro estabelecimento
    test_consultor ........ painel do consultor e exportacoes CSV
    test_security ......... login social com Google (OAuth2/OIDC)

Rodar com:  python manage.py test braid_system.core
"""

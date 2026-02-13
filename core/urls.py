from . import views
from django.contrib.auth import views as auth_views
from django.urls import path, include

urlpatterns = [
    path('', views.home, name='home'),
    # Hub Pages
    path('cadastros/', views.cadastros_view, name='cadastros'),
    path('configuracoes/', views.configuracoes_view, name='configuracoes'),
    # Registration
    path('cadastros/musico/', views.musician_registration, name='musician_registration'),
    path('cadastros/instituicao/', views.institution_registration, name='institution_registration'),
    path('cadastros/instituicoes/', views.institution_list, name='institution_list'),
    path('cadastros/instituicoes/editar/<int:institution_id>/', views.institution_edit, name='institution_edit'),
    path('cadastros/instituicoes/excluir/<int:institution_id>/', views.institution_delete, name='institution_delete'),
    path('cadastros/categorias/', views.music_categories, name='music_categories'),
    path('cadastros/categorias/salvar/', views.save_category, name='save_category'),
    path('cadastros/categorias/excluir/<int:category_id>/', views.delete_category, name='delete_category'),
    path('cadastros/categorias/sub/salvar/', views.save_subcategory, name='save_subcategory'),
    path('cadastros/categorias/sub/excluir/<int:subcategory_id>/', views.delete_subcategory, name='delete_subcategory'),
    # User Management
    path('configuracoes/usuarios/', views.settings_users, name='settings_users'),
    path('configuracoes/usuarios/editar/<int:user_id>/', views.edit_user, name='edit_user'),
    path('configuracoes/usuarios/excluir/<int:user_id>/', views.delete_user, name='delete_user'),
    path('configuracoes/paleta/', views.theme_settings, name='theme_settings'),
    # Profile (self-service)
    path('perfil/editar/', views.profile_edit, name='profile_edit'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Teams
    path('equipes/criar/', views.create_team, name='create_team'),
    path('equipes/entrar/', views.join_team, name='join_team'),
    path('equipes/<int:team_id>/', views.team_detail, name='team_detail'),
    path('equipes/<int:team_id>/excluir/', views.team_delete, name='team_delete'),
    path('equipes/<int:team_id>/avisos/enviar/', views.send_team_announcement, name='send_team_announcement'),
    path('avisos/<int:announcement_id>/dismiss/', views.dismiss_announcement, name='dismiss_announcement'),
    path('avisos/', views.announcements_list, name='announcements_list'),
    path('avisos/<int:announcement_id>/like/', views.toggle_announcement_like, name='toggle_announcement_like'),
    # Music Management
    path('musicas/adicionar/', views.add_music_search, name='add_music_search'),
    path('musicas/api/buscar/', views.music_search_api, name='music_search_api'),
    path('musicas/api/salvar/', views.save_music, name='save_music'),
    path('musicas/excluir/<int:music_id>/', views.delete_music, name='delete_music'),
    path('importar/spotify/', views.import_spotify_playlist, name='import_spotify'),
    path('importar/spotify/buscar/', views.fetch_spotify_playlist, name='fetch_spotify_playlist'),
    path('importar/spotify/salvar/', views.save_spotify_import, name='save_spotify_import'),
    # Repertório
    path('repertorio/', views.repertorio, name='repertorio'),
    # Setlist Builder
    path('setlist/criar/', views.setlist_builder, name='setlist_builder'),

    # Setlist APIs
    path('api/members/', views.api_members, name='api_members'),
    path('api/repertoire/', views.api_repertoire, name='api_repertoire'),
    path('api/setlists/', views.api_setlists, name='api_setlists'),
    path('api/setlists/<int:setlist_id>/', views.api_setlist_detail, name='api_setlist_detail'),
    # Admin Tools
    path('admin-tools/apis/', views.apis_config, name='apis_config'),
    path('admin-tools/manutencao/', views.manutencao_banco, name='manutencao_banco'),
    path('admin-tools/manutencao/exportar/', views.db_export, name='db_export'),
    path('admin-tools/manutencao/importar/', views.db_import, name='db_import'),
]




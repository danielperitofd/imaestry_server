from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_delete
from django.dispatch import receiver

class Skill(models.Model):
    name = models.CharField(max_length=50)
    icon_class = models.CharField(max_length=50, help_text="Bootstrap icon class (e.g., 'bi-mic')")

    def __str__(self):
        return self.name

class Institution(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nome da Instituição")
    photo = models.ImageField(upload_to='institutions/', blank=True, null=True, verbose_name="Foto/Logo")
    responsible_name = models.CharField(max_length=150, verbose_name="Responsável")
    phone = models.CharField(max_length=20, verbose_name="Telefone")
    address = models.CharField(max_length=255, verbose_name="Endereço")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Musician(models.Model):
    photo = models.ImageField(upload_to='musicians/', blank=True, null=True)
    username = models.CharField(max_length=150, unique=True, verbose_name="Usuário")
    first_name = models.CharField(max_length=150, verbose_name="Nome")
    last_name = models.CharField(max_length=150, verbose_name="Sobrenome")
    date_of_birth = models.DateField(verbose_name="Data de Nascimento", blank=True, null=True)
    skills = models.ManyToManyField(Skill, verbose_name="Habilidades", blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name='musicians', verbose_name="Instituição")
    is_leader = models.BooleanField(default=False, verbose_name="É Líder?")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

import random
import string

def generate_team_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Team.objects.filter(code=code).exists():
            return code

class Team(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nome da Equipe")
    description = models.TextField(blank=True, verbose_name="Descrição")
    photo = models.ImageField(upload_to='teams/', blank=True, null=True, verbose_name="Foto/Banner")
    leader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='led_teams', verbose_name="Líder")
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name='teams', verbose_name="Instituição")
    members = models.ManyToManyField(User, related_name='teams', blank=True, verbose_name="Membros")
    code = models.CharField(max_length=6, default=generate_team_code, unique=True, verbose_name="Código de Convite")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Setlist(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='setlists')
    title = models.CharField(max_length=200, verbose_name="Título")
    date = models.DateField(verbose_name="Data do Evento")
    # For now, storing content as simple text or JSON can be done later. 
    # Let's add a simple placeholder for description or notes.
    description = models.TextField(blank=True, verbose_name="Detalhes")
    content = models.TextField(blank=True, verbose_name="Conteúdo (JSON)")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.team.name}"


class TeamAnnouncement(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='announcements')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_announcements')
    message = models.TextField(verbose_name="Mensagem")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Aviso {self.team.name} por {self.author.username}"


class TeamAnnouncementDismissal(models.Model):
    announcement = models.ForeignKey(TeamAnnouncement, on_delete=models.CASCADE, related_name='dismissals')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dismissed_announcements')
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('announcement', 'user')


class TeamAnnouncementLike(models.Model):
    announcement = models.ForeignKey(TeamAnnouncement, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcement_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('announcement', 'user')


class APIConfig(models.Model):
    """Stores API keys for external services (Spotify, YouTube, etc.)"""
    google_api_key = models.CharField(max_length=300, blank=True, null=True, verbose_name="Google API Key (YouTube)")
    spotify_client_id = models.CharField(max_length=300, blank=True, null=True, verbose_name="Spotify Client ID")
    spotify_client_secret = models.CharField(max_length=300, blank=True, null=True, verbose_name="Spotify Client Secret")
    
    deezer_enabled = models.BooleanField(default=True, verbose_name="Deezer Habilitado")
    cifra_enabled = models.BooleanField(default=True, verbose_name="Cifra Club Habilitado")
    letras_enabled = models.BooleanField(default=True, verbose_name="Letras.mus.br Habilitado")
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de API"
        verbose_name_plural = "Configurações de APIs"

    def __str__(self):
        return "Configurações de APIs"


class MusicCategory(models.Model):
    """Main music categories (e.g., Adoração, Exaltação)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Categoria de Música"
        verbose_name_plural = "Categorias de Músicas"
        ordering = ['name']

    def __str__(self):
        return self.name


class MusicSubCategory(models.Model):
    """Subcategories for music (e.g., Evangelismo, Festa, Consagração)"""
    name = models.CharField(max_length=100, verbose_name="Nome")
    category = models.ForeignKey(MusicCategory, on_delete=models.CASCADE, related_name='subcategories', verbose_name="Categoria", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Subcategoria de Música"
        verbose_name_plural = "Subcategorias de Músicas"
        ordering = ['name']

    def __str__(self):
        return f"{self.name}" if not self.category else f"{self.name} ({self.category.name})"


class Music(models.Model):
    """Stores music entries with metadata and service links"""
    title = models.CharField(max_length=300, verbose_name="Título")
    artist = models.CharField(max_length=300, verbose_name="Artista")
    key = models.CharField(max_length=20, blank=True, null=True, verbose_name="Tom")
    bpm = models.PositiveIntegerField(blank=True, null=True, verbose_name="BPM")
    
    # Category fields
    category = models.ForeignKey(MusicCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='musics', verbose_name="Categoria")
    subcategory = models.ForeignKey(MusicSubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='musics', verbose_name="Subcategoria")
    
    # Service links
    spotify_url = models.URLField(blank=True, null=True, verbose_name="Link Spotify")
    deezer_url = models.URLField(blank=True, null=True, verbose_name="Link Deezer")
    youtube_url = models.URLField(blank=True, null=True, verbose_name="Link YouTube")
    cifra_url = models.URLField(blank=True, null=True, verbose_name="Link Cifra Club")
    letras_url = models.URLField(blank=True, null=True, unique=True, verbose_name="Link Letras.mus.br")
    
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='added_musics', verbose_name="Adicionado por")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Música"
        verbose_name_plural = "Músicas"
        ordering = ['title', 'artist']

    def __str__(self):
        return f"{self.title} - {self.artist}"

class ThemeConfig(models.Model):
    """Stores the dynamic color palette for the system"""
    primary_color = models.CharField(max_length=7, default='#6F2682', verbose_name="Cor Primária")
    secondary_color = models.CharField(max_length=7, default='#36C2D7', verbose_name="Cor Secundária")
    error_color = models.CharField(max_length=7, default='#F25F5C', verbose_name="Cor de Erro")
    success_color = models.CharField(max_length=7, default='#A0D440', verbose_name="Cor de Sucesso")
    warning_color = models.CharField(max_length=7, default='#FFB337', verbose_name="Cor de Alerta")
    
    sidebar_bg = models.CharField(max_length=7, default='#D2D9E8', verbose_name="Fundo da Sidebar")
    main_bg = models.CharField(max_length=7, default='#FCFCFC', verbose_name="Fundo Principal")
    
    # Extended customization fields
    border_color = models.CharField(max_length=7, default='#dee2e6', verbose_name="Cor da Borda")
    card_bg = models.CharField(max_length=7, default='#ffffff', verbose_name="Fundo dos Cards")
    card_radius = models.PositiveSmallIntegerField(default=12, verbose_name="Raio dos Cards (px)")
    title_color = models.CharField(max_length=7, default='#212529', verbose_name="Cor do Título")
    subtitle_color = models.CharField(max_length=7, default='#495057', verbose_name="Cor do Subtítulo")
    body_text_color = models.CharField(max_length=7, default='#212529', verbose_name="Cor do Texto")
    sidebar_text_color = models.CharField(max_length=7, default='#555555', verbose_name="Cor do Texto da Sidebar")
    
    gradient_start = models.CharField(max_length=7, default='#6F2682', verbose_name="Início do Gradiente")
    gradient_end = models.CharField(max_length=7, default='#B469FB', verbose_name="Fim do Gradiente")
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Tema"
        verbose_name_plural = "Configurações de Temas"

    def __str__(self):
        return "Configuração de Tema Ativa"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


# ===== Signals: limpeza de dependências ao excluir User (inclusive via Admin) =====
@receiver(pre_delete, sender=User)
def _cleanup_user_dependencies(sender, instance: User, **kwargs):  # pragma: no cover
    try:
        # Remover do M2M de equipes
        for team in getattr(instance, 'teams', []).all():
            team.members.remove(instance)
    except Exception:
        pass
    try:
        # Apagar times liderados explicitamente (evita issues de ordem em alguns bancos)
        Team.objects.filter(leader=instance).delete()
    except Exception:
        pass
    try:
        # Avisos / curtidas / dispensas vinculados ao usuário
        TeamAnnouncementLike.objects.filter(user=instance).delete()
        TeamAnnouncementDismissal.objects.filter(user=instance).delete()
        TeamAnnouncement.objects.filter(author=instance).delete()
    except Exception:
        pass
    try:
        # Perfil de músico associado por username
        Musician.objects.filter(username=instance.username).delete()
    except Exception:
        pass

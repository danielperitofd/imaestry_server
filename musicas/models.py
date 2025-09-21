from django.db import models
from django.contrib.auth.models import User

class Song(models.Model):
    class Category(models.TextChoices):
        EXALTACAO = "exaltacao", "Exaltação"
        ADORACAO = "adoracao", "Adoração"
        NEUTRA = "neutra", "Neutra"

    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=120, blank=True, null=True)
    key = models.CharField(max_length=10, blank=True, null=True)
    bpm = models.PositiveIntegerField(blank=True, null=True)
    lyrics_excerpt = models.TextField(blank=True, null=True)
    links = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.NEUTRA)
    themes = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    # update (09/09/2025) ------------------------------------------------
    audio_link = models.URLField(blank=True, null=True)  # Spotify/YouTube
    lyrics_link = models.URLField(blank=True, null=True) # Link da letra
    chord_link = models.URLField(blank=True, null=True)  # Link da cifra
    # --------------------------------------------------------------------- 
    band = models.ForeignKey("Band", on_delete=models.CASCADE, related_name="songs", null=True)

    def __str__(self):
        return f"{self.title} ({self.artist})"

class Category(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name
    
class Company(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=2)

    def __str__(self):
        return self.name
    
class Band(models.Model):
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    members = models.ManyToManyField(User, related_name="bands")
    country = models.CharField(
        max_length=2,
        choices=[
            ("br", "Brasil"),
            ("us", "Estados Unidos"),
            ("pt", "Portugal"),
            ("fr", "França"),
            ("de", "Alemanha"),
            ("es", "Espanha"),
            ("mx", "México"),
            ("jp", "Japão"),
            ("kr", "Coreia do Sul"),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.company.name})"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    band = models.ForeignKey(Band, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.user.username

class Feature(models.Model):
    name = models.CharField(max_length=100)
    module = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=[("feito", "Feito"), ("pendente", "Pendente"), ("em andamento", "Em andamento")])
    equipe = models.ForeignKey(Band, on_delete=models.CASCADE)
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    prazo = models.DateField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=30, default="Sócio")
    data_nascimento = models.DateField(null=True, blank=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    can_manage_users = models.BooleanField(default=False)
    can_manage_categories = models.BooleanField(default=False)
    can_manage_articles = models.BooleanField(default=False)
    can_view_dashboard = models.BooleanField(default=False)

    def __str__(self):
        return f"Perfil de {self.user.username}"

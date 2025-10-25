from django.contrib import admin
from .models import Song

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "category", "bpm", "key")
    search_fields = ("title", "artist", "themes")
    list_filter = ("category", "key")

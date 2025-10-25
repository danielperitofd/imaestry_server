from django import forms
from .models import Song, Company, Band

class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ["title", "artist", "key", "bpm", "lyrics_excerpt", "links", "audio_link", "lyrics_link", "chord_link", "category", "themes", "notes"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "input"}),
            "artist": forms.TextInput(attrs={"class": "input"}),
            "key": forms.TextInput(attrs={"class": "input"}),
            "bpm": forms.NumberInput(attrs={"class": "input"}),
            "lyrics_excerpt": forms.Textarea(attrs={"class": "textarea"}),
            "links": forms.Textarea(attrs={"class": "textarea"}),
            "themes": forms.TextInput(attrs={"class": "input"}),
            "notes": forms.Textarea(attrs={"class": "textarea"}),
        }

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "city", "country"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "city": forms.TextInput(attrs={"class": "input"}),
            "country": forms.TextInput(attrs={"class": "input"}),
        }

class BandForm(forms.ModelForm):
    class Meta:
        model = Band
        fields = ["name", "company"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "company": forms.Select(attrs={"class": "input"}),
        }

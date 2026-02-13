from django import forms
from django.contrib.auth.models import User
from .models import Musician, Skill, Team, Institution

class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = ['photo', 'name', 'responsible_name', 'phone', 'address']
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da Instituição'}),
            'responsible_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Responsável'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Endereço'}),
        }

class TeamForm(forms.ModelForm):
    institution = forms.ModelChoiceField(queryset=Institution.objects.all(), required=False, label="Instituição", widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Team
        fields = ['name', 'institution', 'description', 'photo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da Equipe'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descrição (Opcional)', 'rows': 3}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

class JoinTeamForm(forms.Form):
    code = forms.CharField(max_length=6, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código de Convite'}))
    
    def clean_code(self):
        code = self.cleaned_data['code']
        if not Team.objects.filter(code=code).exists():
            raise forms.ValidationError("Código de convite inválido.")
        return code

class MusicianForm(forms.ModelForm):
    class Meta:
        model = Musician
        fields = ['photo', 'username', 'first_name', 'last_name', 'date_of_birth', 'skills']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuário'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sobrenome'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'skills': forms.CheckboxSelectMultiple(),
        }
    
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Senha'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar Senha'}))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("As senhas não conferem.")
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skills'].queryset = Skill.objects.all()

class UserEditForm(forms.ModelForm):
    photo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'd-none', 'id': 'id_photo', 'onchange': 'previewImage(this)'}))
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Habilidades"
    )
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False, label="Nova Senha", help_text="Deixe em branco para manter a senha atual.")
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False, label="Confirmar Senha")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("As senhas não conferem.")
        return cleaned_data

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login
from .models import Profile
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import redirect

import csv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from .spotify_client import fetch_spotify_playlist, fetch_spotify_track, fetch_spotify_album

from .models import Song
from .models import Category
from .forms import SongForm
from django.shortcuts import render
from django.utils import timezone

from .models import Band, Company
from django.contrib import messages
from .forms import CompanyForm, BandForm

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id="10e22c8b31cd4aff8505ddf6abc48245",
    client_secret="a2f61be369974ae2ae8b05cc3bdc840e"
))

def get_audio_features(track_id):
    features = sp.audio_features([track_id])[0]
    if features:
        bpm = round(features['tempo']) if features['tempo'] else None
        key_map = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        key = key_map[features['key']] if features['key'] is not None else None
        if features['mode'] == 0 and key:
            key += "m"
        return bpm, key
    return None, None

@login_required
def create_company_and_band(request):
    if request.method == "POST":
        company_form = CompanyForm(request.POST)
        band_form = BandForm(request.POST)
        if company_form.is_valid() and band_form.is_valid():
            company = company_form.save()
            band = band_form.save(commit=False)
            band.company = company
            band.save()
            band.members.add(request.user)
            return redirect("musicas:welcome")
    else:
        company_form = CompanyForm()
        band_form = BandForm()
    return render(request, "musicas/create_company_and_band.html", {
        "company_form": company_form,
        "band_form": band_form
    })

@login_required
def welcome(request):
    user = request.user
    social = user.socialaccount_set.first()
    context = {
        "name": user.first_name or user.username,
        "email": user.email,
        "photo": social.extra_data.get("picture") if social else None,
        "social": social,
    }
    return render(request, "musicas/welcome.html", context)

def song_repertorio(request):
    songs = Song.objects.all()
    return render(request, "musicas/song_repertorio.html", {"songs": songs})

def song_create(request):
    if request.method == "POST":
        form = SongForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("musicas:song_repertorio")
    else:
        form = SongForm()
    return render(request, "musicas/song_form.html", {"form": form})

def song_edit(request, pk):
    song = get_object_or_404(Song, pk=pk)
    if request.method == "POST":
        form = SongForm(request.POST, instance=song)
        if form.is_valid():
            form.save()
            return redirect("musicas:song_repertorio")
    else:
        form = SongForm(instance=song)
    return render(request, "musicas/song_form.html", {"form": form})

def song_delete(request, pk):
    try:
        song = Song.objects.get(pk=pk)
        song.delete()
        messages.success(request, "Música excluída com sucesso.")
    except Song.DoesNotExist:
        messages.error(request, "Essa música já foi excluída ou não existe.")
    return redirect("musicas:song_repertorio")


# ------------ Modulo Import Musicas CSV -----------------------

def _try_read_csv_bytes(uploaded_file):
    """
    Tenta decodificar o arquivo em várias codificações comuns no BR.
    Retorna (texto_decodificado, encoding_usada) ou (None, None) se falhar.
    """
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    for enc in encodings:
        try:
            uploaded_file.seek(0)
            return uploaded_file.read().decode(enc), enc
        except UnicodeDecodeError:
            continue
    return None, None

def _detect_dialect(sample_str):
    # Detecta delimitador ; ou ,. Se o Sniffer falhar, tenta fallback.
    try:
        return csv.Sniffer().sniff(sample_str, delimiters=";,")
    except Exception:
        class SimpleDialect(csv.Dialect):
            delimiter = ";" if ";" in sample_str.splitlines()[0] else ","
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = "\n"
            quoting = csv.QUOTE_MINIMAL
        return SimpleDialect()

def _normalize_keys(row):
    # Mapeia cabeçalhos PT->EN usados no modelo
    mapping = {
        "titulo": "title", "título": "title", "title": "title",
        "artista": "artist", "artist": "artist",
        "tom": "key", "key": "key",
        "bpm": "bpm",
        "letra": "lyrics_excerpt", "trecho": "lyrics_excerpt", "lyrics_excerpt": "lyrics_excerpt",
        "links": "links",
        "categoria": "category", "category": "category",
        "temas": "themes", "themes": "themes",
        "observacoes": "notes", "observações": "notes", "notes": "notes",
    }
    out = {}
    for k, v in row.items():
        if k is None:
            continue
        kk = mapping.get(k.strip().lower(), k.strip().lower())
        out[kk] = v
    return out

def _normalize_category(value):
    if not value:
        return "neutra"
    s = str(value).strip().lower()
    # tira acentos/variações simples
    for a, b in [("ç", "c"), ("ã", "a"), ("á","a"), ("â","a"),
                 ("é","e"), ("ê","e"), ("í","i"), ("ó","o"),
                 ("ô","o"), ("ú","u")]:
        s = s.replace(a, b)
    if "exalt" in s:
        return "exaltacao"
    if "ador" in s:
        return "adoracao"
    return "neutra"

def song_import(request):
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            messages.error(request, "Selecione um arquivo CSV.")
            return redirect("musicas:song_repertorio")
        if not csv_file.name.lower().endswith(".csv"):
            messages.error(request, "Envie um arquivo .csv")
            return redirect("musicas:song_repertorio")

        text, used_enc = _try_read_csv_bytes(csv_file)
        if text is None:
            messages.error(request, "Não foi possível ler o CSV (encoding desconhecida). Tente salvar como 'CSV UTF-8' no Excel.")
            return redirect("musicas:song_repertorio")

        lines = text.splitlines()
        if not lines:
            messages.error(request, "O arquivo CSV está vazio.")
            return redirect("musicas:song_repertorio")

        created = 0
        skipped = 0  # <-- ESSA LINHA PRECISA ESTAR AQUI

        sample = lines[0]
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.DictReader(lines, delimiter=delimiter)
#--------------------------------------------------------------------------------------
        for raw in reader:
            row = _normalize_keys(raw)

            title = (row.get("title") or "").strip()
            if not title:
                skipped += 1
                continue

            artist = (row.get("artist") or "").strip() or None
            key = (row.get("key") or "").strip() or None
            bpm_raw = (row.get("bpm") or "").strip()
            try:
                bpm = int(bpm_raw) if bpm_raw else None
            except ValueError:
                bpm = None

            lyrics_excerpt = (row.get("lyrics_excerpt") or "").strip() or None
            links = (row.get("links") or "").strip() or None
            category = _normalize_category(row.get("category"))
            themes = (row.get("themes") or "").strip() or None
            notes = (row.get("notes") or "").strip() or None

            Song.objects.create(
                title=title, artist=artist, key=key, bpm=bpm,
                lyrics_excerpt=lyrics_excerpt, links=links,
                category=category, themes=themes, notes=notes
            )
            created += 1

        messages.success(request, f"Importadas {created} música(s). Ignoradas {skipped} linha(s) sem título. Encoding: {used_enc.upper()}.")
        return redirect("musicas:song_repertorio")

    return render(request, "musicas/song_import.html")

# -------------- SEÇÃO SPOTFY ------------------------

def import_from_spotify(request):
    if request.method == "POST":
        playlist_url = request.POST.get("playlist_url")
        if not playlist_url:
            messages.error(request, "Informe a URL da playlist do Spotify.")
            return redirect("musicas:import_from_spotify")

        try:
            if "playlist" in playlist_url:
                songs_data = fetch_spotify_playlist(playlist_url)
            elif "album" in playlist_url:
                songs_data = fetch_spotify_album(playlist_url)
            elif "track" in playlist_url:
                songs_data = fetch_spotify_track(playlist_url)
            else:
                messages.error(request, "URL inválida.")
                return redirect("musicas:import_from_spotify")
        except Exception as e:
            messages.error(request, f"Erro ao acessar Spotify: {e}")
            return redirect("musicas:import_from_spotify")

        # --- ENRIQUECIMENTO DOS DADOS ---
        enriched_songs = []
        for song in songs_data:
            track_id = song.get("id")
            bpm, key = (None, None)
            if track_id:
                bpm, key = get_audio_features(track_id)

                # Log de debug no console
                print(f"[DEBUG] Track: {song.get('title')} ({track_id}) -> BPM={bpm}, Key={key}")

            enriched_songs.append({
                "title": song.get("title"),
                "artist": song.get("artist"),
                "links": song.get("links") or song.get("audio_link") or "",
                "category": song.get("category") or "",
                "bpm": bpm if bpm else "Desconhecido",
                "key": key if key else "Desconhecido",
                "lyrics_link": "",
                "chord_link": ""
            })

        categories = Category.objects.all()
        TONS = [
            "C", "Cm", "C#", "C#m", "D", "Dm", "D#", "D#m",
            "E", "Em", "F", "Fm", "F#", "F#m", "G", "Gm",
            "G#", "G#m", "A", "Am", "A#", "A#m", "B", "Bm"
        ]
        return render(request, "musicas/spotify_preview.html", {
            "songs": enriched_songs,
            "categories": categories,
            "tones": TONS
        })

    return render(request, "musicas/import_spotify.html")


def confirm_spotify_import(request):
    if request.method == "POST":
        total = int(request.POST.get("total", 0))
        created = 0
        for i in range(1, total + 1):
            title = request.POST.get(f"title_{i}", "").strip()
            artist = request.POST.get(f"artist_{i}", "").strip()
            links = request.POST.get(f"links_{i}", "").strip()
            category = request.POST.get(f"category_{i}", "").strip()
            bpm_raw = request.POST.get(f"bpm_{i}", "").strip()
            key = request.POST.get(f"key_{i}", "").strip()
            lyrics_link = request.POST.get(f"lyrics_link_{i}", "").strip()
            chord_link = request.POST.get(f"chord_link_{i}", "").strip()

            # --- Tratamento de BPM ---
            try:
                bpm = int(bpm_raw) if bpm_raw else None
            except ValueError:
                bpm = None  # sempre None se não for número

            # --- Tratamento de Key ---
            if not key:
                key = None  # aqui pode ser TextField/CharField, aceita vazio

            if not title or not artist:
                continue
            
            # --- Evitar duplicatas ---
            exists = Song.objects.filter(
                title__iexact=title,
                artist__iexact=artist
            ).exists()

            if exists:
                print(f"[DUPLICATA] {title} - {artist} já existe, ignorado.")
                continue

            # --- Criar música nova ---
            Song.objects.create(
                title=title,
                artist=artist,
                key=key,
                bpm=bpm,
                lyrics_excerpt="",
                links=links,
                category=category,
                themes="",
                notes="",
                audio_link=links,
                lyrics_link=lyrics_link,
                chord_link=chord_link
            )
            created += 1

        messages.success(request, f"{created} música(s) importadas da playlist.")
        return redirect("musicas:song_repertorio")


    
def import_top_country(request):
    band = request.user.userprofile.band  # ou country_code = "br" se ainda não tiver userprofile
    country_code = band.country

    top_playlists = {
        "br": "37i9dQZEVXbMXbN3EUUhlg",
        "us": "37i9dQZEVXbLRQDuF5jeBp",
        "pt": "37i9dQZEVXbKyJS56d1pgi",
        # outros países...
    }

    playlist_id = top_playlists.get(country_code)
    if not playlist_id:
        messages.error(request, "Não há playlist configurada para este país.")
        return redirect("musicas:song_repertorio")

    try:
        songs_data = fetch_spotify_playlist(f"https://open.spotify.com/playlist/{playlist_id}")
    except Exception as e:
        messages.error(request, f"Erro ao acessar Spotify: {e}")
        return redirect("musicas:song_repertorio")

    categories = Category.objects.all()
    TONS = ["C", "Cm", "C#", "C#m", "D", "Dm", "D#", "D#m", "E", "Em", "F", "Fm", "F#", "F#m", "G", "Gm", "G#", "G#m", "A", "Am", "A#", "A#m", "B", "Bm"]

    return render(request, "musicas/spotify_preview.html", {
        "songs": songs_data,
        "categories": categories,
        "tones": TONS
    })

def roadmap(request):
    progress_data = {
        "autenticacao": {
            "title": "🔐 Autenticação e Equipes",
            "percent": 40,
            "items": [
                ("Tela de login e cadastro de usuário", True),
                ("Usuário pode criar equipe como ADM", True),
                ("Gerar código de entrada para equipe", False),
                ("Entrar em equipe via código ou convite", True),
                ("Promoção de membro a ADM", False),
                ("Melhorar layout da tela register_choice", False),
                ("Melhorar layout da tela register_manual", False),
            ]
        },
        "membros": {
            "title": "👤 Cadastro de Membros",
            "percent": 30,
            "items": [
                ("CRUD completo de membros com ícones visuais", False),
                ("Campos pessoais: nome, nascimento, gênero, foto", True),
                ("Lembrete automático de aniversários", False),
                ("Contato: telefone, e-mail, cidade/estado", False),
                ("Função na banda: instrumentos, vocal, categoria", False),
                ("Quiz musical para validar categoria", False),
                ("Equipamento pessoal: próprio ou da banda", False),
                ("Tela perfil_membro.html para complementar cadastro", False),
                ("Mudar foto de avatar caso não tenha logado com Google", False),
            ]
        },
        "realidade": {
            "title": "📅 Realidade da Equipe",
            "percent": 0,
            "items": [
                ("Configuração de eventos e ensaios por dia/horário", False),
                ("Frequência: semanal, quinzenal, mensal", False),
                ("Datas comemorativas (Natal, Páscoa etc.)", False),
            ]
        },
        "convocacao": {
            "title": "📣 Disponibilidade e Convocação",
            "percent": 0,
            "items": [
                ("Calendário de disponibilidade por membro", False),
                ("Convocação manual ou automática por evento", False),
                ("Equipe automática com travas por membro", False),
                ("Notificação via WhatsApp para confirmação", False),
                ("Substituição em caso de ausência", False),
            ]
        },
        "setlists": {
            "title": "📋 Montagem de SetList",
            "percent": 15,
            "items": [
                ("Criar e salvar setlists com datas/horários", False),
                ("Estrutura fixa por momento (Exaltação + Adoração)", False),
                ("Modelo alternativo com quantidade definida", False),
                ("Definir tom de execução", False),
                ("Associação de equipe escalada", False),
                ("Upload de setlist externa", False),
                ("Random inteligente com regras e botão “manter”", False),
                ("Busca por tema bíblico para Pós-Mensagem", False),
                ("Poslúdio definido manualmente", False),
            ]
        },
        "musicas": {
            "title": "🎵 Biblioteca de Músicas e IA",
            "percent": 60,
            "items": [
                ("CRUD completo de músicas", True),
                ("Campos: título, artista, tom, BPM, letra, links, categoria, temas, observações", True),
                ("Importação via CSV/TXT/Excel", True),
                ("Classificação com IA (categoria + temas)", False),
                ("Integração com Spotify", True),
                ("Importar (Nome, Artista) do Spotify", True),
                ("Importar Tom e BPM da música do Spotify", False),
                ("Não repetir músicas já importadas/cadastradas", True),
                ("Integração com YouTube", False),
                ("Integração com CifraClub", False),
            ]
        },
        "dashboard": {
            "title": "📊 Dashboard & Relatórios",
            "percent": 0,
            "items": [
                ("Ranking das músicas mais tocadas", False),
                ("Estatísticas: BPM médio, tonalidades, temas", False),
                ("Histórico de setlists", False),
                ("Histórico da equipe", False),
                ("Frequência por integrante (% de presença)", False),
                ("Eventos perdidos e atrasos", False),
                ("Exportação para planilha ou gráfico", False),
            ]
        },
        "culto": {
            "title": "🕹️ Modo Culto (dinâmico)",
            "percent": 0,
            "items": [
                ("Tela simplificada para uso ao vivo", False),
                ("Busca por temas em tempo real", False),
                ("Botão rápido “Sugerir Pós-Mensagem”", False),
                ("Ações rápidas: “Tocar agora”, “Projetar link”", False),
            ]
        },
        "infra": {
            "title": "🌐 Infraestrutura",
            "percent": 60,
            "items": [
                ("Banco de dados: Postgres (produção), SQLite (dev)", True),
                ("Hospedagem gratuita: Railway / Render / PythonAnywhere / Netlify", False),
                ("Exportar setlists como playlist (Spotify/YouTube)", False),
                ("Exportar calendário (ICS)", False),
                ("Subdomínio gratuito para testes online", False),
                ("Integração com Google OAuth", True),
                ("Estilização de telas de login/signup", True),
                ("Exibição de foto de perfil com borda verde", True),
                ("Botões com ícones visuais (editar/excluir)", True),
                ("Cards de acesso rápido na tela de boas-vindas", True),
                ("Cadastro manual com foto de perfil", True),
            ]
        }
    }

    return render(request, "musicas/roadmap.html", {"progress_data": progress_data})


def perfil_membro(request):
    return render(request, "musicas/perfil_membro.html")

def config_system(request):
    return render(request, "musicas/config_system.html")

def register_manual(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        birth_date = request.POST.get("birth_date")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if len(full_name) < 15:
            messages.error(request, "Digite nome e sobrenome com pelo menos 15 caracteres.")
            return redirect("musicas:register_manual")

        if password1 != password2:
            messages.error(request, "Senhas não coincidem.")
            return redirect("musicas:register_manual")

        if User.objects.filter(username=email).exists():
            messages.error(request, "Este e-mail já está cadastrado. Tente fazer login.")
            return redirect("musicas:register_manual")

            # user = User.objects.create_user(username=email, email=email, password=password1)
            user.first_name = full_name
            user.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)

        return redirect("musicas:register_team_or_join")

    # Aqui fora do if
    return render(request, "musicas/register_manual.html", {"today": timezone.now().date()})


@login_required
def register_team_or_join(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "join":
            code = request.POST.get("team_code")
            band = Band.objects.filter(name=code).first()
            if band:
                band.members.add(request.user)
                return redirect("musicas:welcome")
            else:
                messages.error(request, "Código inválido.")
        elif action == "create":
            name = request.POST.get("team_name")
            company = Company.objects.first()
            band = Band.objects.create(name=name, company=company)
            band.members.add(request.user)
            return redirect("musicas:welcome")

    return render(request, "musicas/register_team_or_join.html")


def register_choice(request):
    return render(request, "musicas/register_choice.html")

@login_required
def config_users(request):
    users = User.objects.select_related("profile").all()
    return render(request, "musicas/config_users.html", {"users": users})

@login_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == "POST":
        user.first_name = request.POST.get("first_name")
        user.last_name = request.POST.get("last_name")
        user.email = request.POST.get("email")
        user.is_active = 'is_active' in request.POST
        profile.tipo = request.POST.get("tipo")

        data_nascimento = request.POST.get("data_nascimento")
        if data_nascimento:
            profile.data_nascimento = data_nascimento
        else:
            profile.data_nascimento = None

        profile.telefone = request.POST.get("telefone")
        profile.genero = request.POST.get("genero")
        profile.can_manage_users = 'can_manage_users' in request.POST
        profile.can_manage_categories = 'can_manage_categories' in request.POST
        profile.can_manage_articles = 'can_manage_articles' in request.POST
        profile.can_view_dashboard = 'can_view_dashboard' in request.POST

        if 'photo' in request.FILES:
            profile.photo = request.FILES['photo']

        user.save()
        profile.save()
        messages.success(request, "Usuário atualizado com sucesso.")
        return redirect("musicas:config_users")


    return render(request, "musicas/edit_user.html", {"user": user, "profile": profile})


@login_required
def delete_user(request, user_id):
    user_to_delete = get_object_or_404(User, id=user_id)

    # Protege contra autoexclusão
    if user_to_delete == request.user:
        messages.error(request, "Você não pode excluir a si mesmo.")
        return redirect("musicas:config_users")

    # Verifica se o usuário logado tem permissão
    if not hasattr(request.user, "profile") or not request.user.profile.can_manage_users:
        messages.error(request, "Você não tem permissão para excluir usuários.")
        return redirect("musicas:config_users")

    if request.method == "POST":
        user_to_delete.delete()
        messages.success(request, "Usuário excluído com sucesso.")
        return redirect("musicas:config_users")

    return redirect("musicas:config_users")

@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    Profile.objects.get_or_create(user=instance)

@login_required
def create_user(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        tipo = request.POST.get("tipo")
        telefone = request.POST.get("telefone")
        data_nascimento = request.POST.get("data_nascimento")
        genero = request.POST.get("genero")

        if User.objects.filter(email=email).exists():
            messages.error(request, "E-mail já cadastrado.")
            return redirect("musicas:create_user")

        user = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        profile = Profile.objects.get(user=user)
        profile.tipo = tipo
        profile.telefone = telefone
        profile.data_nascimento = data_nascimento
        profile.genero = genero

        if 'photo' in request.FILES:
            profile.photo = request.FILES['photo']

        profile.save()
        messages.success(request, "Usuário criado com sucesso.")
        return redirect("musicas:config_users")

    return render(request, "musicas/create_user.html")

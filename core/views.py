import json
import requests
import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from .forms import MusicianForm, TeamForm, JoinTeamForm, InstitutionForm
from .models import Skill, Musician, Team, Institution, Music, MusicCategory, MusicSubCategory, APIConfig, ThemeConfig, TeamAnnouncement, TeamAnnouncementDismissal, TeamAnnouncementLike
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator


@login_required
def home(request):
    # Profile completion check for non-staff users
    if not request.user.is_staff:
        try:
            musician = Musician.objects.get(username=request.user.username)
            if not musician.skills.exists():
                messages.warning(request, 'Por favor, complete seu perfil adicionando suas habilidades.')
                return redirect('profile_edit')
        except Musician.DoesNotExist:
            # If musician profile doesn't exist, redirect to create it
            messages.warning(request, 'Bem-vindo! Por favor, complete seu perfil.')
            return redirect('profile_edit')

    # Get teams where user is leader or member
    user_teams = request.user.led_teams.all() | request.user.teams.all()
    user_teams = user_teams.distinct()

    # Aggregate recent likes per team (últimos 30 dias)
    cutoff = timezone.now() - timedelta(days=30)
    like_counts = (TeamAnnouncementLike.objects
                   .filter(announcement__team__in=user_teams, created_at__gte=cutoff)
                   .values('announcement__team_id')
                   .annotate(c=Count('id')))
    likes_map = {row['announcement__team_id']: row['c'] for row in like_counts}
    teams_list = list(user_teams)
    for t in teams_list:
        t.recent_likes = likes_map.get(t.id, 0)
    # Announcements not dismissed by user
    announcements = TeamAnnouncement.objects.filter(team__in=user_teams)
    announcements = announcements.exclude(dismissals__user=request.user).select_related('team', 'author').prefetch_related('likes')[:10]
    ann_ids = [a.id for a in announcements]
    liked_ids = set(TeamAnnouncementLike.objects.filter(user=request.user, announcement_id__in=ann_ids).values_list('announcement_id', flat=True))
    
    return render(request, 'core/home.html', {'teams': teams_list, 'announcements': announcements, 'liked_ids': liked_ids})


@login_required
def setlist_builder(request):
    """Novo Setlist Builder (moderno)"""
    # Times do usuário para seleção
    user_teams = (request.user.led_teams.all() | request.user.teams.all()).distinct()
    return render(request, "core/setlist_builder.html", {"user_teams": user_teams})


@login_required
def api_members(request):
    team_id = request.GET.get('team_id')
    if not team_id:
        return HttpResponseBadRequest('team_id required')
    team = get_object_or_404(Team, id=team_id)
    # Permissão: precisa ser líder, membro ou staff
    if not (request.user.is_staff or request.user == team.leader or team.members.filter(id=request.user.id).exists()):
        return HttpResponseForbidden('not allowed')

    users = list(team.members.all())
    if team.leader not in users:
        users.insert(0, team.leader)

    usernames = [u.username for u in users]
    musicians = {m.username: m for m in Musician.objects.filter(username__in=usernames).prefetch_related('skills')}
    data = []
    for u in users:
        m = musicians.get(u.username)
        skills = [s.name for s in (m.skills.all() if m else [])]
        data.append({
            'id': u.id,
            'name': u.get_full_name() or u.username,
            'skills': skills,
        })
    return JsonResponse({'members': data})


@login_required
def api_repertoire(request):
    # Monta estrutura Categoria -> Subcategoria -> músicas
    cats = []
    for cat in MusicCategory.objects.all().order_by('name'):
        subs_list = []
        subs = MusicSubCategory.objects.filter(category=cat).order_by('name')
        for sub in subs:
            songs = Music.objects.filter(category=cat, subcategory=sub).order_by('title')
            subs_list.append({
                'name': sub.name,
                'songs': [{'id': s.id, 'title': s.title, 'key': s.key or ''} for s in songs]
            })
        cats.append({'category': cat.name, 'subcategories': subs_list})
    return JsonResponse({'repertoire': cats})


@login_required
def api_setlists(request):
    # GET: lista recentes do usuário; POST: criar
    if request.method == 'GET':
        user_teams = (request.user.led_teams.all() | request.user.teams.all()).distinct()
        items = (Setlist.objects.filter(team__in=user_teams)
                 .order_by('-created_at')[:20] if hasattr(Setlist, 'created_at') else Setlist.objects.filter(team__in=user_teams).order_by('-id')[:20])
        data = [{'id': s.id, 'title': s.title, 'date': s.date.isoformat(), 'team': s.team.name} for s in items]
        return JsonResponse({'setlists': data})

    # POST create
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('invalid json')

    team = get_object_or_404(Team, id=payload.get('team_id'))
    if not (request.user.is_staff or request.user == team.leader or team.members.filter(id=request.user.id).exists()):
        return HttpResponseForbidden('not allowed')

    title = payload.get('title') or f"Setlist {payload.get('number', '')}".strip()
    date_str = payload.get('date1')
    try:
        from datetime import date as _date
        d = _date.fromisoformat(date_str) if date_str else None
    except Exception:
        d = None
    if d is None:
        return HttpResponseBadRequest('date1 required (YYYY-MM-DD)')

    s = Setlist.objects.create(team=team, title=title, date=d, description=payload.get('summary',''), content=json.dumps(payload, ensure_ascii=False))
    return JsonResponse({'id': s.id, 'status': 'created'})


@login_required
def api_setlist_detail(request, setlist_id):
    s = get_object_or_404(Setlist, id=setlist_id)
    if not (request.user.is_staff or request.user == s.team.leader or s.team.members.filter(id=request.user.id).exists()):
        return HttpResponseForbidden('not allowed')
    if request.method == 'GET':
        data = {
            'id': s.id,
            'title': s.title,
            'date': s.date.isoformat(),
            'team_id': s.team_id,
            'content': json.loads(s.content) if s.content else {},
        }
        return JsonResponse(data)
    if request.method in ['PUT', 'PATCH']:
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('invalid json')
        s.title = payload.get('title', s.title)
        if payload.get('date1'):
            try:
                from datetime import date as _date
                s.date = _date.fromisoformat(payload['date1'])
            except Exception:
                pass
        s.description = payload.get('summary', s.description)
        s.content = json.dumps(payload, ensure_ascii=False)
        s.save()
        return JsonResponse({'status': 'updated'})
    if request.method == 'DELETE':
        s.delete()
        return JsonResponse({'status': 'deleted'})
    return HttpResponseBadRequest('unsupported method')
    
def musician_registration(request):
    if request.method == 'POST':
        form = MusicianForm(request.POST, request.FILES)
        if form.is_valid():
            # Create the User first
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            email = form.cleaned_data.get('email', '') # Assuming email might be added later, or just empty for now
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']

            if User.objects.filter(username=username).exists():
                messages.error(request, 'Este nome de usuÃ¡rio jÃ¡ estÃ¡ em uso.')
                return render(request, 'core/registration.html', {'form': form, 'skills': Skill.objects.all()})

            user = User.objects.create_user(username=username, password=password, email=email, first_name=first_name, last_name=last_name)
            
            # Save the Musician
            musician = form.save(commit=False)
            musician.save() # Save first to get ID if needed, though not needed for M2M immediately
            form.save_m2m() # Save skills

            messages.success(request, 'MÃºsico e UsuÃ¡rio cadastrados com sucesso!')
            return redirect('musician_registration')
    else:
        form = MusicianForm()
    
    # Garantir que existam habilidades base para seleção (fallback em ambientes novos)
    skills = Skill.objects.all()
    if not skills.exists():
        base_skills = [
            ("Bateria", "bi-music-note-beamed"),
            ("Baixo", "bi-music-note-beamed"),
            ("Teclado", "bi-keyboard"),
            ("Guitarra", "bi-music-note-beamed"),
            ("Violão", "bi-music-note-beamed"),
            ("Vocal", "bi-mic"),
        ]
        for name, icon in base_skills:
            Skill.objects.create(name=name, icon_class=icon)
        skills = Skill.objects.all()
    
    # Get selected skills for the checkbox state
    selected_skills = form['skills'].value()
    if selected_skills:
        # Ensure it's a list of integers
        selected_skills = [int(s) for s in selected_skills if str(s).isdigit()]
    else:
        selected_skills = []

    return render(request, 'core/registration.html', {'form': form, 'skills': skills, 'selected_skills': selected_skills})

def institution_registration(request):
    if request.method == 'POST':
        form = InstitutionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Instituição cadastrada com sucesso!')
            return redirect('institution_list')
    else:
        form = InstitutionForm()
    
    return render(request, 'core/institution_form.html', {'form': form})


@login_required
def institution_list(request):
    """List all institutions"""
    institutions = Institution.objects.all().order_by('name')
    return render(request, 'core/institution_list.html', {'institutions': institutions})


@login_required
def institution_edit(request, institution_id):
    """Edit an existing institution"""
    institution = get_object_or_404(Institution, id=institution_id)
    
    if request.method == 'POST':
        form = InstitutionForm(request.POST, request.FILES, instance=institution)
        if form.is_valid():
            form.save()
            messages.success(request, f'Instituição "{institution.name}" atualizada com sucesso!')
            return redirect('institution_list')
    else:
        form = InstitutionForm(instance=institution)
    
    return render(request, 'core/institution_form.html', {
        'form': form,
        'institution': institution,
        'is_edit': True
    })


@login_required
def institution_delete(request, institution_id):
    """Delete an institution"""
    if request.method != 'POST':
        return redirect('institution_list')
    
    institution = get_object_or_404(Institution, id=institution_id)
    name = institution.name
    institution.delete()
    messages.success(request, f'Instituição "{name}" excluída com sucesso!')
    return redirect('institution_list')


@login_required
@user_passes_test(lambda u: u.is_staff)
def settings_users(request):
    users = User.objects.all()
    # Match musicians to users by username to get photo
    musicians = {m.username: m for m in Musician.objects.all()}
    
    users_data = []
    for u in users:
        musician = musicians.get(u.username)
        users_data.append({
            'user': u,
            'photo_url': musician.photo.url if musician and musician.photo else None,
            'musician': musician 
        })
        
    return render(request, 'core/settings_users.html', {'users_data': users_data})

@login_required
def edit_user(request, user_id):
    user_to_edit = get_object_or_404(User, id=user_id)
    # Allow if staff or editing own profile
    if not (request.user.is_staff or request.user.id == user_to_edit.id):
        messages.error(request, 'Você não tem permissão para editar este usuário.')
        return redirect('home')
    # Try to find associated musician by username
    try:
        musician = Musician.objects.get(username=user_to_edit.username)
    except Musician.DoesNotExist:
        musician = None

    if request.method == 'POST':
        from .forms import UserEditForm
        form = UserEditForm(request.POST, request.FILES, instance=user_to_edit)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                
                # Handle password change
                new_password = form.cleaned_data.get('new_password')
                if new_password:
                    user.set_password(new_password)
                user.save()
                # Keep current user logged in if they changed their own password
                if new_password and user.id == request.user.id:
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, user)
                
                # Always create/update Musician record to keep names and photo in sync
                if not musician:
                    musician = Musician(username=user.username)
                
                # Sync names
                musician.first_name = user.first_name
                musician.last_name = user.last_name
                musician.username = user.username
                
                # Handle photo upload
                photo = request.FILES.get('photo')
                if photo:
                    musician.photo = photo
                
                musician.save()

                # Handle skills
                skills = form.cleaned_data.get('skills')
                if skills is not None:
                    musician.skills.set(skills)

                messages.success(request, 'Usuário atualizado com sucesso!')
                return redirect('settings_users')
            except Exception as e:
                messages.error(request, f'Erro ao salvar: {str(e)}')
                import traceback
                print(traceback.format_exc())
        else:
            messages.error(request, 'Erro ao salvar usuário. Verifique os campos.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        from .forms import UserEditForm
        initial_data = {'skills': musician.skills.all() if musician else []}
        form = UserEditForm(instance=user_to_edit, initial=initial_data)

    return render(request, 'core/user_edit.html', {
        'form': form, 
        'user_to_edit': user_to_edit,
        'musician': musician,
        'skills': Skill.objects.all()
    })


@login_required
def profile_edit(request):
    """Allow any authenticated user to edit their own profile."""
    user_to_edit = request.user
    try:
        musician = Musician.objects.get(username=user_to_edit.username)
    except Musician.DoesNotExist:
        musician = None

    if request.method == 'POST':
        from .forms import UserEditForm
        form = UserEditForm(request.POST, request.FILES, instance=user_to_edit)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                new_password = form.cleaned_data.get('new_password')
                if new_password:
                    user.set_password(new_password)
                user.save()
                # Keep the user logged in if they changed their own password
                if new_password:
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, user)

                if not musician:
                    musician = Musician(username=user.username)
                musician.first_name = user.first_name
                musician.last_name = user.last_name
                musician.username = user.username
                photo = request.FILES.get('photo')
                if photo:
                    musician.photo = photo
                musician.save()

                # Handle skills
                skills = form.cleaned_data.get('skills')
                if skills is not None:
                    musician.skills.set(skills)

                messages.success(request, 'Seu perfil foi atualizado com sucesso!')
                return redirect('home')
            except Exception as e:
                messages.error(request, f'Erro ao salvar: {str(e)}')
        else:
            messages.error(request, 'Erro ao salvar perfil. Verifique os campos.')
    else:
        from .forms import UserEditForm
        initial_data = {'skills': musician.skills.all() if musician else []}
        form = UserEditForm(instance=user_to_edit, initial=initial_data)

    return render(request, 'core/user_edit.html', {
        'form': form,
        'user_to_edit': user_to_edit,
        'musician': musician,
        'is_self_edit': True,
        'skills': Skill.objects.all()
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def delete_user(request, user_id):
    user_to_delete = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        try:
            from django.db import transaction
            with transaction.atomic():
            # Remove user from all team memberships (ManyToMany)
                for team in user_to_delete.teams.all():
                    team.members.remove(user_to_delete)

                # Guard: contar times liderados antes do delete (CASCADE cuidará da remoção)
                led_teams_count = user_to_delete.led_teams.count()

                # Apagar avisos/curtidas/dismiss vinculados a este usuário (como autor)
                try:
                    TeamAnnouncementLike.objects.filter(user=user_to_delete).delete()
                    TeamAnnouncementDismissal.objects.filter(user=user_to_delete).delete()
                    TeamAnnouncement.objects.filter(author=user_to_delete).delete()
                except Exception:
                    pass

                # Deletar explicitamente os times liderados (evita cascatas complexas em alguns bancos)
                from .models import Team
                Team.objects.filter(leader=user_to_delete).delete()

                # Apagar perfil Musician vinculado por username (se existir)
                Musician.objects.filter(username=user_to_delete.username).delete()

                # Admin LogEntry é opcional: só apaga se disponível
                try:
                    from django.contrib.admin.models import LogEntry  # noqa: WPS433
                    LogEntry.objects.filter(user_id=user_to_delete.id).delete()
                except Exception:
                    pass

                # Agora remove o usuário (tabelas dependentes já tratadas/limpas)
                username = user_to_delete.username
                user_to_delete.delete()
            if led_teams_count > 0:
                messages.success(request, f'Usuário {username} excluído com sucesso! {led_teams_count} equipe(s) liderada(s) também foram excluídas.')
            else:
                messages.success(request, f'Usuário {username} excluído com sucesso!')
            return redirect('settings_users')
        except Exception as e:
            messages.error(request, f'Erro ao excluir usuário: {str(e)}')
            # Log the full traceback to help debugging
            import traceback
            print(traceback.format_exc())
            return redirect('settings_users')
    
    return render(request, 'core/user_confirm_delete.html', {'user_to_delete': user_to_delete})


@login_required
def create_team(request):
    if request.method == 'POST':
        form = TeamForm(request.POST, request.FILES)
        if form.is_valid():
            team = form.save(commit=False)
            team.leader = request.user
            # Manually assign if needed, but form should handle it since we added 'institution' to fields?
            # Actually, ModelForm doesn't save M2M or foreign keys if not in fields or handled.
            # We added 'institution' to fields, so it should be fine.
            # But wait, ModelForm save(commit=False) doesn't save FKs? No, it does if they are in cleaned_data.
            # The issue is we are setting commit=False.
            team.institution = form.cleaned_data.get('institution') 
            team.save()
            team.members.add(request.user) # Leader is also a member
            messages.success(request, 'Equipe criada com sucesso!')
            return redirect('home')
    else:
        form = TeamForm()
    return render(request, 'core/team_form.html', {'form': form})

@login_required
def join_team(request):
    if request.method == 'POST':
        form = JoinTeamForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            team = Team.objects.get(code=code)
            if team.members.filter(id=request.user.id).exists():
                messages.info(request, 'VocÃª jÃ¡ Ã© membro desta equipe.')
            else:
                team.members.add(request.user)
                messages.success(request, f'VocÃª entrou na equipe {team.name}!')
            return redirect('home')
    else:
        form = JoinTeamForm()
    return render(request, 'core/join_team.html', {'form': form})

@login_required
def team_detail(request, team_id):
    team = Team.objects.get(id=team_id)
    # Check if user is member or leader
    if request.user != team.leader and not team.members.filter(id=request.user.id).exists():
        messages.error(request, 'VocÃª nÃ£o tem permissÃ£o para acessar esta equipe.')
        return redirect('home')
        
    last_setlist = team.setlists.order_by('-created_at').first()
    
    # Prepare members list with Musician data for photos
    # Get all usernames from leader and members
    member_users = list(team.members.all())
    # Add leader content if not in members (though create_team adds leader to members, let's be safe)
    if team.leader not in member_users:
        member_users.insert(0, team.leader)
        
    # Fetch musicians matching these usernames
    usernames = [u.username for u in member_users]
    musicians = Musician.objects.filter(username__in=usernames)
    musician_map = {m.username: m for m in musicians}
    
    members_data = []
    for user in member_users:
        members_data.append({
            'user': user,
            'musician': musician_map.get(user.username)
        })

    return render(request, 'core/team_detail.html', {'team': team, 'last_setlist': last_setlist, 'members_data': members_data})


@login_required
def send_team_announcement(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    if request.user != team.leader:
        messages.error(request, 'Apenas o líder pode enviar avisos para a equipe.')
        return redirect('team_detail', team_id=team.id)
    if request.method == 'POST':
        msg = request.POST.get('message', '').strip()
        if not msg:
            messages.error(request, 'Digite uma mensagem para enviar.')
        else:
            TeamAnnouncement.objects.create(team=team, author=request.user, message=msg)
            messages.success(request, 'Aviso enviado para todos os membros da equipe.')
    return redirect('team_detail', team_id=team.id)


@login_required
def dismiss_announcement(request, announcement_id):
    ann = get_object_or_404(TeamAnnouncement, id=announcement_id)
    # Only team members (or leader) can dismiss
    is_member = ann.team.members.filter(id=request.user.id).exists() or request.user == ann.team.leader
    if not is_member:
        messages.error(request, 'Você não pode descartar este aviso.')
        return redirect('home')
    if request.method == 'POST':
        TeamAnnouncementDismissal.objects.get_or_create(announcement=ann, user=request.user)
    # Return to referrer if present
    next_url = request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('home')


@login_required
def announcements_list(request):
    """List all undismissed announcements for the user with pagination."""
    user_teams = request.user.led_teams.all() | request.user.teams.all()
    user_teams = user_teams.distinct()
    qs = (TeamAnnouncement.objects
          .filter(team__in=user_teams)
          .exclude(dismissals__user=request.user)
          .select_related('team', 'author')
          .prefetch_related('likes')
          .order_by('-created_at'))

    team_filter = request.GET.get('team')
    query = request.GET.get('q', '').strip()
    if team_filter and team_filter.isdigit():
        qs = qs.filter(team_id=int(team_filter))
    if query:
        qs = qs.filter(message__icontains=query)
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    liked_ids = set(TeamAnnouncementLike.objects.filter(user=request.user, announcement_id__in=page_obj.object_list.values_list('id', flat=True)).values_list('announcement_id', flat=True))
    return render(request, 'core/announcements_list.html', {
        'page_obj': page_obj,
        'announcements': page_obj.object_list,
        'liked_ids': liked_ids,
        'teams': user_teams,
        'selected_team': int(team_filter) if (team_filter and team_filter.isdigit()) else None,
        'q': query,
    })


@login_required
def toggle_announcement_like(request, announcement_id):
    ann = get_object_or_404(TeamAnnouncement, id=announcement_id)
    is_member = ann.team.members.filter(id=request.user.id).exists() or request.user == ann.team.leader
    if not is_member:
        messages.error(request, 'Você não pode interagir com este aviso.')
        return redirect('home')
    like, created = TeamAnnouncementLike.objects.get_or_create(announcement=ann, user=request.user)
    if not created:
        like.delete()
    next_url = request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('home')


@login_required
def team_delete(request, team_id):
    """Delete a team. Leader can delete only if there are no other members and no setlists.
    Otherwise, require current user to be staff and confirm their password.
    """
    team = get_object_or_404(Team, id=team_id)

    # Only leader or staff can access this page
    if request.user != team.leader and not request.user.is_staff:
        messages.error(request, 'Você não tem permissão para excluir esta equipe.')
        return redirect('team_detail', team_id=team.id)

    non_leader_members = team.members.exclude(id=team.leader_id).count()
    setlists_count = team.setlists.count()
    deletable_by_leader = (non_leader_members == 0 and setlists_count == 0)

    if request.method == 'POST':
        if deletable_by_leader and (request.user == team.leader or request.user.is_staff):
            team_name = team.name
            team.delete()
            messages.success(request, f'Equipe "{team_name}" excluída com sucesso.')
            return redirect('home')
        else:
            password = request.POST.get('staff_password', '')
            if not request.user.is_staff:
                messages.error(request, 'Somente um usuário staff pode excluir uma equipe com membros ou setlists.')
            elif not password or not request.user.check_password(password):
                messages.error(request, 'Senha de staff inválida. Tente novamente.')
            else:
                team_name = team.name
                team.delete()
                messages.success(request, f'Equipe "{team_name}" excluída com sucesso.')
                return redirect('home')

    context = {
        'team': team,
        'non_leader_members': non_leader_members,
        'setlists_count': setlists_count,
        'deletable_by_leader': deletable_by_leader,
    }
    return render(request, 'core/team_confirm_delete.html', context)


# ===============================
# Music Repository Views
# ===============================
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import APIConfig, Music, MusicCategory, MusicSubCategory
import requests
import base64
import json
import urllib.parse
import base64
import json
import urllib.parse


@login_required
@user_passes_test(lambda u: u.is_staff)
def apis_config(request):
    """Admin page for configuring API keys"""
    config = APIConfig.objects.first()
    
    if request.method == 'POST':
        google = request.POST.get('google_api_key', '').strip()
        sp_id = request.POST.get('spotify_client_id', '').strip()
        sp_secret = request.POST.get('spotify_client_secret', '').strip()
        deezer = 'deezer_enabled' in request.POST
        cifra = 'cifra_enabled' in request.POST
        letras = 'letras_enabled' in request.POST
        
        if not config:
            config = APIConfig()
        
        config.google_api_key = google if google else None
        config.spotify_client_id = sp_id if sp_id else None
        config.spotify_client_secret = sp_secret if sp_secret else None
        config.deezer_enabled = deezer
        config.cifra_enabled = cifra
        config.letras_enabled = letras
        config.save()
        
        messages.success(request, 'ConfiguraÃ§Ãµes de APIs salvas com sucesso!')
        return redirect('apis_config')
    
    return render(request, 'core/apis.html', {'config': config})


@login_required
def add_music_search(request):
    """Render the music search page"""
    categories = MusicCategory.objects.all()
    subcategories = MusicSubCategory.objects.all()
    return render(request, 'core/add_music_search.html', {
        'categories': categories,
        'subcategories': subcategories
    })


@login_required
def music_search_api(request):
    """API endpoint for multi-service music search"""
    query = request.GET.get('q', '').strip()
    title = request.GET.get('title', '').strip()
    artist = request.GET.get('artist', '').strip()
    
    if not query and not title:
        return JsonResponse({'error': 'Nenhuma busca fornecida'})
    
    config = APIConfig.objects.first()
    
    result = {
        'query': query,
        'title': title,
        'artist': artist,
        'youtube': None,
        'spotify': None,
        'deezer': None,
        'cifra': None,
        'letras': None,
        'key': None,
        'bpm': None,
        'exists': False
    }
    
    search_query = query if query else f"{title} {artist}".strip()
    encoded_query = urllib.parse.quote(search_query)
    
    # ---------------- YOUTUBE ----------------
    if config and config.google_api_key:
        try:
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": search_query,
                "maxResults": 1,
                "type": "video",
                "key": config.google_api_key
            }
            r = requests.get(url, params=params, timeout=10).json()
            
            if r.get("items"):
                vid = r["items"][0]["id"]["videoId"]
                result["youtube"] = f"https://www.youtube.com/watch?v={vid}"
        except Exception:
            pass
    
    # ---------------- DEEZER ----------------
    if not config or config.deezer_enabled:
        try:
            url = f"https://api.deezer.com/search?q={encoded_query}"
            r = requests.get(url, timeout=10).json()
            if r.get("data") and len(r["data"]) > 0:
                result["deezer"] = r["data"][0].get("link")
                # Try to get BPM from Deezer if available
                if r["data"][0].get("bpm"):
                    result["bpm"] = r["data"][0]["bpm"]
        except Exception:
            pass
    
    # ---------------- SPOTIFY ----------------
    if config and config.spotify_client_id and config.spotify_client_secret:
        try:
            auth = f"{config.spotify_client_id}:{config.spotify_client_secret}"
            b64 = base64.b64encode(auth.encode()).decode()
            
            token_resp = requests.post(
                "https://accounts.spotify.com/api/token",
                headers={"Authorization": f"Basic {b64}"},
                data={"grant_type": "client_credentials"},
                timeout=10
            ).json()
            
            token = token_resp.get("access_token")
            
            if token:
                headers = {"Authorization": f"Bearer {token}"}
                params = {"q": search_query, "type": "track", "limit": 1}
                r = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params, timeout=10).json()
                
                items = r.get("tracks", {}).get("items", [])
                if items:
                    result["spotify"] = items[0]["external_urls"]["spotify"]
                    # Get artist if not provided
                    if not artist and items[0].get("artists"):
                        result["artist"] = items[0]["artists"][0]["name"]
        except Exception:
            pass
    
    # ---------------- CIFRA CLUB ----------------
    if not config or config.cifra_enabled:
        result["cifra"] = f"https://www.cifraclub.com.br/?q={encoded_query}"
    
    # ---------------- LETRAS.MUS.BR ----------------
    if not config or config.letras_enabled:
        result["letras"] = f"https://www.letras.mus.br/?q={encoded_query}"
    
    # Check if music already exists in database (using letras_url for uniqueness)
    if result["letras"]:
        exists = Music.objects.filter(letras_url=result["letras"]).exists()
        result["exists"] = exists
    
    return JsonResponse(result)


@login_required
@csrf_exempt
def save_music(request):
    """Save music to database"""
    if request.method != 'POST':
        return JsonResponse({'error': 'MÃ©todo nÃ£o permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Dados invÃ¡lidos'}, status=400)
    
    title = data.get('title', '').strip()
    artist = data.get('artist', '').strip()
    key = data.get('key', '').strip()
    bpm = data.get('bpm', '')
    category_id = data.get('category_id')
    subcategory_id = data.get('subcategory_id')
    
    if not title:
        return JsonResponse({'error': 'TÃ­tulo Ã© obrigatÃ³rio'}, status=400)
    
    letras_url = data.get('letras_url', '').strip()
    
    # Check for duplicates using letras_url
    if letras_url:
        if Music.objects.filter(letras_url=letras_url).exists():
            return JsonResponse({'error': 'Esta mÃºsica jÃ¡ existe no repertÃ³rio!', 'exists': True}, status=400)
    
    # Get category and subcategory objects if IDs provided
    category = None
    subcategory = None
    
    if category_id:
        try:
            category = MusicCategory.objects.get(id=category_id)
        except MusicCategory.DoesNotExist:
            pass
    
    if subcategory_id:
        try:
            subcategory = MusicSubCategory.objects.get(id=subcategory_id)
        except MusicSubCategory.DoesNotExist:
            pass
    
    # Create music entry
    music = Music(
        title=title,
        artist=artist,
        key=key if key else None,
        bpm=int(bpm) if bpm and str(bpm).isdigit() else None,
        category=category,
        subcategory=subcategory,
        spotify_url=data.get('spotify_url', '').strip() or None,
        deezer_url=data.get('deezer_url', '').strip() or None,
        youtube_url=data.get('youtube_url', '').strip() or None,
        cifra_url=data.get('cifra_url', '').strip() or None,
        letras_url=letras_url if letras_url else None,
        added_by=request.user
    )
    music.save()
    
    return JsonResponse({'success': True, 'id': music.id, 'message': 'MÃºsica adicionada com sucesso!'})


@login_required
def repertorio(request):
    """List all music entries"""
    musics = Music.objects.select_related('category', 'subcategory').all().order_by('title')
    return render(request, 'core/repertorio.html', {'musics': musics})


@login_required
@csrf_exempt
def delete_music(request, music_id):
    """Delete a music entry"""
    if request.method != 'POST':
        return JsonResponse({'error': 'MÃ©todo nÃ£o permitido'}, status=405)
    
    try:
        music = Music.objects.get(id=music_id)
        music.delete()
        return JsonResponse({'success': True, 'message': 'MÃºsica excluÃ­da com sucesso!'})
    except Music.DoesNotExist:
        return JsonResponse({'error': 'MÃºsica nÃ£o encontrada'}, status=404)


# ===============================
# Database Maintenance Views
# ===============================
from django.http import HttpResponse
from .models import Team, Setlist
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
import datetime


@login_required
@user_passes_test(lambda u: u.is_staff)
def manutencao_banco(request):
    """Database maintenance page"""
    return render(request, 'core/manutencao_banco.html')


@login_required
@user_passes_test(lambda u: u.is_staff)
def db_export(request):
    """Export data to JSON file"""
    if request.method != 'POST':
        return redirect('manutencao_banco')
    
    export_type = request.POST.get('export_type', '')
    
    data = {
        'export_type': export_type,
        'exported_at': datetime.datetime.now().isoformat(),
        'version': '1.0'
    }
    
    if export_type == 'teams' or export_type == 'all':
        teams_data = []
        for team in Team.objects.all():
            teams_data.append({
                'id': team.id,
                'name': team.name,
                'code': team.code,
                'description': team.description,
                'leader_username': team.leader.username if team.leader else None,
                'members': [u.username for u in team.members.all()],
                'institution_id': team.institution.id if team.institution else None
            })
        data['teams'] = teams_data
    
    if export_type == 'setlists' or export_type == 'all':
        setlists_data = []
        for setlist in Setlist.objects.all():
            setlists_data.append({
                'id': setlist.id,
                'team_id': setlist.team.id if setlist.team else None,
                'title': setlist.title,
                'date': setlist.date.isoformat() if setlist.date else None,
                'description': setlist.description
            })
        data['setlists'] = setlists_data
    
    if export_type == 'repertorio' or export_type == 'all':
        musics_data = []
        for music in Music.objects.all():
            musics_data.append({
                'id': music.id,
                'title': music.title,
                'artist': music.artist,
                'key': music.key,
                'bpm': music.bpm,
                'category_name': music.category.name if music.category else None,
                'subcategory_name': music.subcategory.name if music.subcategory else None,
                'spotify_url': music.spotify_url,
                'deezer_url': music.deezer_url,
                'youtube_url': music.youtube_url,
                'cifra_url': music.cifra_url,
                'letras_url': music.letras_url
            })
        data['musics'] = musics_data

    if export_type == 'categories' or export_type == 'all':
        categories_data = []
        for cat in MusicCategory.objects.all():
            categories_data.append({
                'id': cat.id,
                'name': cat.name
            })
        data['categories'] = categories_data

    if export_type == 'subcategories' or export_type == 'all':
        subcategories_data = []
        for sub in MusicSubCategory.objects.all():
            subcategories_data.append({
                'id': sub.id,
                'name': sub.name,
                'category_name': sub.category.name if sub.category else None
            })
        data['subcategories'] = subcategories_data
    
    if export_type == 'institutions' or export_type == 'all':
        institutions_data = []
        for inst in Institution.objects.all():
            institutions_data.append({
                'id': inst.id,
                'name': inst.name,
                'responsible_name': inst.responsible_name,
                'phone': inst.phone,
                'address': inst.address,
                # Note: photo is not exported (binary file)
            })
        data['institutions'] = institutions_data
    
    if export_type == 'apis' or export_type == 'all':
        config = APIConfig.objects.first()
        if config:
            data['api_config'] = {
                'google_api_key': config.google_api_key,
                'spotify_client_id': config.spotify_client_id,
                'spotify_client_secret': config.spotify_client_secret,
                'deezer_enabled': config.deezer_enabled,
                'cifra_enabled': config.cifra_enabled,
                'letras_enabled': config.letras_enabled
            }
    
    # Generate filename
    type_names = {
        'teams': 'equipes',
        'setlists': 'setlists',
        'repertorio': 'repertorio',
        'apis': 'apis',
        'all': 'backup_completo'
    }
    filename = f"imaestry_{type_names.get(export_type, 'backup')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    response = HttpResponse(
        json.dumps(data, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@user_passes_test(lambda u: u.is_staff)
def db_import(request):
    """Import data from JSON file"""
    if request.method != 'POST':
        return redirect('manutencao_banco')
    
    import_file = request.FILES.get('import_file')
    
    if not import_file:
        messages.error(request, 'Nenhum arquivo selecionado.')
        return redirect('manutencao_banco')
    
    try:
        content = import_file.read().decode('utf-8')
        data = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        messages.error(request, f'Arquivo invÃ¡lido: {str(e)}')
        return redirect('manutencao_banco')
    
    imported_items = []
    
    # Auto-detect and import teams
    if 'teams' in data:
        count = 0
        skipped = 0
        warnings = []
        for team_data in data['teams']:
            # Check if team already exists by code
            if Team.objects.filter(code=team_data['code']).exists():
                skipped += 1
                warnings.append(f"Equipe '{team_data['name']}' (código {team_data['code']}) já existe")
                continue
            
            # Try to find leader, use current user as fallback
            leader_username = team_data.get('leader_username')
            leader = User.objects.filter(username=leader_username).first() if leader_username else None
            
            if not leader:
                leader = request.user
                if leader_username:
                    warnings.append(f"Líder '{leader_username}' não encontrado para equipe '{team_data['name']}'. Usando usuário atual como líder.")
            
            team = Team.objects.create(
                name=team_data['name'],
                code=team_data['code'],
                description=team_data.get('description', ''),
                leader=leader
            )
            
            # Add members
            members_added = 0
            members_missing = []
            for username in team_data.get('members', []):
                user = User.objects.filter(username=username).first()
                if user:
                    team.members.add(user)
                    members_added += 1
                else:
                    members_missing.append(username)
            
            if members_missing:
                warnings.append(f"Equipe '{team_data['name']}': {len(members_missing)} membro(s) não encontrado(s): {', '.join(members_missing[:3])}{'...' if len(members_missing) > 3 else ''}")
            
            count += 1
        
        if count:
            imported_items.append(f'{count} equipe(s)')
        if skipped:
            imported_items.append(f'{skipped} equipe(s) ignorada(s) (já existem)')
        if warnings:
            for warning in warnings[:5]:  # Limit to 5 warnings
                messages.warning(request, warning)
    
    # Auto-detect and import setlists
    if 'setlists' in data:
        count = 0
        for setlist_data in data['setlists']:
            team = Team.objects.filter(id=setlist_data.get('team_id')).first()
            if team:
                Setlist.objects.create(
                    team=team,
                    title=setlist_data['title'],
                    date=setlist_data.get('date'),
                    description=setlist_data.get('description', '')
                )
                count += 1
        if count:
            imported_items.append(f'{count} setlist(s)')
    
    # Auto-detect and import categories
    if 'categories' in data:
        count = 0
        for cat_data in data['categories']:
            _, created = MusicCategory.objects.get_or_create(name=cat_data['name'])
            if created:
                count += 1
        if count:
            imported_items.append(f'{count} categoria(s)')

    # Auto-detect and import subcategories
    if 'subcategories' in data:
        count = 0
        for sub_data in data['subcategories']:
            category = None
            if sub_data.get('category_name'):
                category = MusicCategory.objects.filter(name=sub_data['category_name']).first()
            
            _, created = MusicSubCategory.objects.get_or_create(
                name=sub_data['name'],
                defaults={'category': category}
            )
            if created:
                count += 1
        if count:
            imported_items.append(f'{count} subcategoria(s)')

    # Auto-detect and import music
    if 'musics' in data:
        count = 0
        for music_data in data['musics']:
            # Check uniqueness by letras_url or title+artist
            letras = music_data.get('letras_url')
            if letras and Music.objects.filter(letras_url=letras).exists():
                continue
            if not letras and Music.objects.filter(title=music_data['title'], artist=music_data['artist']).exists():
                continue
            
            # Resolve category and subcategory
            category = None
            if music_data.get('category_name'):
                category = MusicCategory.objects.filter(name=music_data['category_name']).first()
                
            subcategory = None
            if music_data.get('subcategory_name'):
                subcategory = MusicSubCategory.objects.filter(name=music_data['subcategory_name']).first()

            Music.objects.create(
                title=music_data['title'],
                artist=music_data.get('artist', ''),
                key=music_data.get('key'),
                bpm=music_data.get('bpm'),
                category=category,
                subcategory=subcategory,
                spotify_url=music_data.get('spotify_url'),
                deezer_url=music_data.get('deezer_url'),
                youtube_url=music_data.get('youtube_url'),
                cifra_url=music_data.get('cifra_url'),
                letras_url=letras,
                added_by=request.user
            )
            count += 1
        if count:
            imported_items.append(f'{count} música(s)')
    
    # Auto-detect and import institutions
    if 'institutions' in data:
        count = 0
        for inst_data in data['institutions']:
            # Check if institution already exists by name
            if not Institution.objects.filter(name=inst_data['name']).exists():
                Institution.objects.create(
                    name=inst_data['name'],
                    responsible_name=inst_data.get('responsible_name', ''),
                    phone=inst_data.get('phone', ''),
                    address=inst_data.get('address', '')
                    # Note: photo is not imported (binary file)
                )
                count += 1
        if count:
            imported_items.append(f'{count} instituição(ões)')
    
    # Auto-detect and import API config
    if 'api_config' in data:
        config_data = data['api_config']
        config = APIConfig.objects.first()
        if not config:
            config = APIConfig()
        
        config.google_api_key = config_data.get('google_api_key')
        config.spotify_client_id = config_data.get('spotify_client_id')
        config.spotify_client_secret = config_data.get('spotify_client_secret')
        config.deezer_enabled = config_data.get('deezer_enabled', True)
        config.cifra_enabled = config_data.get('cifra_enabled', True)
        config.letras_enabled = config_data.get('letras_enabled', True)
        config.save()
        imported_items.append('configuraÃ§Ãµes de API')
    
    if imported_items:
        messages.success(request, f'ImportaÃ§Ã£o concluÃ­da: {", ".join(imported_items)}.')
    else:
        messages.warning(request, 'Nenhum dado novo foi importado (possÃ­veis duplicatas ou arquivo vazio).')
    
    return redirect('manutencao_banco')


@login_required
def cadastros_view(request):
    """Cadastros hub page"""
    return render(request, 'core/cadastros.html')


@login_required
@user_passes_test(lambda u: u.is_staff)
def configuracoes_view(request):
    """Configurações hub page (staff only)"""
    return render(request, 'core/configuracoes.html')


@login_required
@user_passes_test(lambda u: u.is_staff)
def theme_settings(request):
    """Manage system color palette"""
    theme = ThemeConfig.get_solo()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'reset':
            # Reset to defaults
            theme.primary_color = '#6F2682'
            theme.secondary_color = '#36C2D7'
            theme.error_color = '#F25F5C'
            theme.success_color = '#A0D440'
            theme.warning_color = '#FFB337'
            theme.sidebar_bg = '#D2D9E8'
            theme.main_bg = '#FCFCFC'
            theme.gradient_start = '#6F2682'
            theme.gradient_end = '#B469FB'
            # Extended fields
            theme.border_color = '#dee2e6'
            theme.card_bg = '#ffffff'
            theme.card_radius = 12
            theme.title_color = '#212529'
            theme.subtitle_color = '#495057'
            theme.body_text_color = '#212529'
            theme.sidebar_text_color = '#555555'
            theme.save()
            messages.success(request, 'Paleta resetada para o padrão com sucesso!')
        else:
            theme.primary_color = request.POST.get('primary_color', theme.primary_color)
            theme.secondary_color = request.POST.get('secondary_color', theme.secondary_color)
            theme.error_color = request.POST.get('error_color', theme.error_color)
            theme.success_color = request.POST.get('success_color', theme.success_color)
            theme.warning_color = request.POST.get('warning_color', theme.warning_color)
            theme.sidebar_bg = request.POST.get('sidebar_bg', theme.sidebar_bg)
            theme.main_bg = request.POST.get('main_bg', theme.main_bg)
            theme.gradient_start = request.POST.get('gradient_start', theme.gradient_start)
            theme.gradient_end = request.POST.get('gradient_end', theme.gradient_end)
            # Extended fields
            theme.border_color = request.POST.get('border_color', theme.border_color)
            theme.card_bg = request.POST.get('card_bg', theme.card_bg)
            try:
                theme.card_radius = int(request.POST.get('card_radius', theme.card_radius))
            except (TypeError, ValueError):
                pass
            theme.title_color = request.POST.get('title_color', theme.title_color)
            theme.subtitle_color = request.POST.get('subtitle_color', theme.subtitle_color)
            theme.body_text_color = request.POST.get('body_text_color', theme.body_text_color)
            theme.sidebar_text_color = request.POST.get('sidebar_text_color', theme.sidebar_text_color)
            theme.save()
            messages.success(request, 'Paleta de cores atualizada com sucesso!')
            
        return redirect('theme_settings')
        
    return render(request, 'core/theme_settings.html', {'theme_config': theme})


@login_required
def music_categories(request):
    """Music categories and subcategories management page"""
    categories = MusicCategory.objects.all()
    subcategories = MusicSubCategory.objects.all()
    return render(request, 'core/categorias_musicas.html', {
        'categories': categories,
        'subcategories': subcategories
    })


@login_required
def save_category(request):
    """Create or update a music category"""
    if request.method != 'POST':
        return redirect('music_categories')
    
    category_id = request.POST.get('category_id')
    name = request.POST.get('name', '').strip()
    
    if not name:
        messages.error(request, 'Nome da categoria Ã© obrigatÃ³rio.')
        return redirect('music_categories')
    
    if category_id:
        # Update existing category
        try:
            category = MusicCategory.objects.get(id=category_id)
            category.name = name
            category.save()
            messages.success(request, f'Categoria "{name}" atualizada com sucesso!')
        except MusicCategory.DoesNotExist:
            messages.error(request, 'Categoria nÃ£o encontrada.')
    else:
        # Create new category
        MusicCategory.objects.create(name=name)
        messages.success(request, f'Categoria "{name}" criada com sucesso!')
    
    return redirect('music_categories')


@login_required
def delete_category(request, category_id):
    """Delete a music category"""
    if request.method != 'POST':
        return redirect('music_categories')
    
    try:
        category = MusicCategory.objects.get(id=category_id)
        name = category.name
        category.delete()
        messages.success(request, f'Categoria "{name}" excluÃ­da com sucesso!')
    except MusicCategory.DoesNotExist:
        messages.error(request, 'Categoria nÃ£o encontrada.')
    
    return redirect('music_categories')


@login_required
def save_subcategory(request):
    """Create or update a music subcategory"""
    if request.method != 'POST':
        return redirect('music_categories')
    
    subcategory_id = request.POST.get('subcategory_id')
    name = request.POST.get('name', '').strip()
    
    if not name:
        messages.error(request, 'Nome da subcategoria Ã© obrigatÃ³rio.')
        return redirect('music_categories')
    
    if subcategory_id:
        # Update existing subcategory
        try:
            subcategory = MusicSubCategory.objects.get(id=subcategory_id)
            subcategory.name = name
            subcategory.save()
            messages.success(request, f'Subcategoria "{name}" atualizada com sucesso!')
        except MusicSubCategory.DoesNotExist:
            messages.error(request, 'Subcategoria nÃ£o encontrada.')
    else:
        # Create new subcategory
        MusicSubCategory.objects.create(name=name)
        messages.success(request, f'Subcategoria "{name}" criada com sucesso!')
    
    return redirect('music_categories')


@login_required
def delete_subcategory(request, subcategory_id):
    """Delete a music subcategory"""
    if request.method != 'POST':
        return redirect('music_categories')
    
    try:
        subcategory = MusicSubCategory.objects.get(id=subcategory_id)
        name = subcategory.name
        subcategory.delete()
        messages.success(request, f'Subcategoria "{name}" excluÃ­da com sucesso!')
    except MusicSubCategory.DoesNotExist:
        messages.error(request, 'Subcategoria nÃ£o encontrada.')
    
    return redirect('music_categories')


# ==================== SPOTIFY PLAYLIST IMPORT ====================

@login_required
def import_spotify_playlist(request):
    """Render Spotify playlist import page"""
    categories = MusicCategory.objects.all()
    subcategories = MusicSubCategory.objects.all()
    return render(request, 'core/import_spotify.html', {
        'categories': categories,
        'subcategories': subcategories
    })


@login_required
@csrf_exempt
def fetch_spotify_playlist(request):
    """Fetch tracks from a Spotify playlist URL"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Dados inválidos'}, status=400)
    
    url = data.get('url', '').strip()
    
    if not url:
        return JsonResponse({'error': 'URL é obrigatória'}, status=400)
    
    # Extract playlist ID from URL
    import re
    pattern = r'playlist[/:]([a-zA-Z0-9]+)'
    match = re.search(pattern, url)
    
    if not match:
        return JsonResponse({'error': 'URL inválida. Use uma URL de playlist do Spotify.'}, status=400)
    
    playlist_id = match.group(1)
    
    # Get Spotify credentials
    config = APIConfig.objects.first()
    
    if not config or not config.spotify_client_id or not config.spotify_client_secret:
        return JsonResponse({'error': 'Credenciais do Spotify não configuradas'}, status=500)
    
    try:
        # Get Spotify access token
        auth = f"{config.spotify_client_id}:{config.spotify_client_secret}"
        b64 = base64.b64encode(auth.encode()).decode()
        
        token_resp = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {b64}"},
            data={"grant_type": "client_credentials"},
            timeout=10
        ).json()
        
        token = token_resp.get("access_token")
        
        if not token:
            return JsonResponse({'error': 'Não foi possível autenticar com o Spotify'}, status=500)
        
        # Fetch playlist tracks
        headers = {"Authorization": f"Bearer {token}"}
        tracks = []
        offset = 0
        limit = 100
        
        while True:
            params = {"offset": offset, "limit": limit}
            response = requests.get(
                f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                if response.status_code == 404:
                    return JsonResponse({'error': 'Playlist não encontrada ou privada'}, status=404)
                return JsonResponse({'error': 'Erro ao buscar playlist'}, status=500)
            
            data = response.json()
            items = data.get('items', [])
            
            for item in items:
                track = item.get('track')
                if not track:
                    continue
                
                tracks.append({
                    'title': track.get('name', ''),
                    'artist': track.get('artists', [{}])[0].get('name', '') if track.get('artists') else '',
                    'album': track.get('album', {}).get('name', ''),
                    'spotify_url': track.get('external_urls', {}).get('spotify', '')
                })
            
            # Check if there are more tracks
            if not data.get('next'):
                break
            
            offset += limit
            
            # Safety limit: max 500 tracks
            if offset >= 500:
                break
        
        return JsonResponse({'tracks': tracks, 'count': len(tracks)})
        
    except requests.exceptions.RequestException:
        return JsonResponse({'error': 'Erro ao conectar com o Spotify'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Erro: {str(e)}'}, status=500)


@login_required
@csrf_exempt
def save_spotify_import(request):
    """Save imported tracks from Spotify playlist"""
    try:
        print("DEBUG: save_spotify_import view CALLED")
        
        if request.method != 'POST':
            return JsonResponse({'error': 'Método não permitido'}, status=405)
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Dados inválidos'}, status=400)
        
        tracks = data.get('tracks', [])
        
        if not tracks:
            return JsonResponse({'error': 'Nenhuma música para importar'}, status=400)
        
        imported = 0
        updated = 0
        skipped = 0
        errors = []
        
        for track_data in tracks:
            try:
                title = (track_data.get('title') or '').strip()
                artist = (track_data.get('artist') or '').strip()
                spotify_url = (track_data.get('spotify_url') or '').strip()
                youtube_url = (track_data.get('youtube_url') or '').strip()
                deezer_url = (track_data.get('deezer_url') or '').strip()
                cifra_url = (track_data.get('cifra_url') or '').strip()
                letras_url = (track_data.get('letras_url') or '').strip()
                key = (track_data.get('key') or '').strip()
                bpm = track_data.get('bpm')
                category_id = track_data.get('category_id')
                subcategory_id = track_data.get('subcategory_id')
                
                if not title:
                    continue
                
                # Check for existing music by Spotify URL
                existing_music = None
                if spotify_url:
                    existing_music = Music.objects.filter(spotify_url=spotify_url).first()
                
                if existing_music:
                    # Update metadata if missing in DB but present in payload
                    has_changes = False
                    
                    if not existing_music.youtube_url and youtube_url:
                        existing_music.youtube_url = youtube_url
                        has_changes = True
                    
                    if not existing_music.deezer_url and deezer_url:
                        existing_music.deezer_url = deezer_url
                        has_changes = True
                        
                    if not existing_music.cifra_url and cifra_url:
                        existing_music.cifra_url = cifra_url
                        has_changes = True
                        
                    if not existing_music.letras_url and letras_url:
                        # Check unique constraint for letras_url
                        if not Music.objects.filter(letras_url=letras_url).exclude(id=existing_music.id).exists():
                            existing_music.letras_url = letras_url
                            has_changes = True
                    
                    # Update BPM/Key if missing
                    if not existing_music.bpm and bpm and str(bpm).isdigit():
                        existing_music.bpm = int(bpm)
                        has_changes = True
                        
                    if not existing_music.key and key:
                        existing_music.key = key
                        has_changes = True

                    if has_changes:
                        existing_music.save()
                        updated += 1
                    else:
                        skipped += 1
                    continue
                
                # Get category and subcategory objects
                category = None
                subcategory = None
                
                if category_id:
                    try:
                        category = MusicCategory.objects.get(id=category_id)
                    except MusicCategory.DoesNotExist:
                        pass
                
                if subcategory_id:
                    try:
                        subcategory = MusicSubCategory.objects.get(id=subcategory_id)
                    except MusicSubCategory.DoesNotExist:
                        pass
                
                # Create music entry
                Music.objects.create(
                    title=title,
                    artist=artist,
                    key=key if key else None,
                    bpm=int(bpm) if bpm and str(bpm).isdigit() else None,
                    category=category,
                    subcategory=subcategory,
                    spotify_url=spotify_url if spotify_url else None,
                    youtube_url=youtube_url if youtube_url else None,
                    deezer_url=deezer_url if deezer_url else None,
                    cifra_url=cifra_url if cifra_url else None,
                    letras_url=letras_url if letras_url else None,
                    added_by=request.user
                )
                imported += 1
            except Exception as e:
                error_msg = f"{track_data.get('title', 'Desconhecida')}: {str(e)}"
                print(f"Erro ao processar música: {error_msg}")
                errors.append(error_msg)
                continue
        
        return JsonResponse({
            'success': True,
            'imported': imported,
            'updated': updated,
            'skipped': skipped,
            'errors': errors,
            'message': f'{imported} música(s) importada(s), {updated} atualizada(s)!'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Erro interno do servidor: {str(e)}'}, status=500)

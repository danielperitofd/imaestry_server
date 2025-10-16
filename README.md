# 🎼 MaestroV1

MaestroV1 é um sistema web desenvolvido em **Django** para facilitar a curadoria, organização e importação de músicas cristãs.  
Este primeiro módulo já traz cadastro manual, importação via CSV e integração com o Spotify para playlists, álbuns e faixas individuais.

-------------------------------------------------------------------------------------------

## 🚀 Funcionalidades

- ✍️ Cadastro manual de músicas (título, artista, tom, BPM, categoria e observações)
- 📂 Importação de músicas via arquivo CSV com suporte a múltiplos encodings
- 🎧 Integração com a API do Spotify:
  - Importação de **playlists públicas**
  - Importação de **álbuns** e **faixas individuais**
  - Sugestão automática de **tom** com base em nome e artista
- 👀 Pré-visualização das músicas antes da importação
- 🗂️ Dropdown dinâmico de categorias direto do banco de dados
- 📱 Interface limpa e responsiva para gestão de repertório

-------------------------------------------------------------------------------------------
## 🛠️ Tecnologias

- **Python 3.12**
- **Django 5.2**
- **Gunicorn + Nginx** (produção)
- **SQLite** (desenvolvimento)
- **Allauth** (autenticação)
- **Widget Tweaks** (customização de formulários)
- **Spotify API** (importação de músicas)

-------------------------------------------------------------------------------------------
## 🧱 Estrutura do Projeto

maestrov1/
├── musicas/
│ ├── models.py # Modelos Song e Category
│ ├── views.py # CRUD + importação CSV + integração Spotify
│ ├── spotify_client.py # Cliente para comunicação com API do Spotify
│ └── templates/musicas/ # Templates HTML organizados por funcionalidade
└── manage.py

maestrov1/
├── musicas/                # App principal
├── staticfiles/            # Arquivos estáticos coletados
├── media/                  # Uploads de usuários
├── templates/              # Templates HTML
├── db.sqlite3              # Banco de dados local
└── .venv/                  # Ambiente virtual (ignorado no Git)

-------------------------------------------------------------------------------------------
## 🛠️ Instalação (VSCODE)

Clone o repositório e configure o ambiente virtual:
git clone https://github.com/seu-usuario/maestrov1.git
cd maestrov1

python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# ou
.venv\Scripts\activate      # Windows
pip install -r requirements.txt

Aplique as migrações e rode o servidor:
python manage.py migrate
python manage.py runserver

🔐 Configuração da API do Spotify
Crie um app no Spotify Developer Dashboard

Copie seu CLIENT_ID e CLIENT_SECRET

Insira no arquivo spotify_client.py:
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id="SEU_CLIENT_ID",
    client_secret="SEU_CLIENT_SECRET"
))
-------------------------------------------------------------------------------------------
## 🚀 Instalação local (SERVIDOR)

```bash
# Clonar o repositório
git clone https://github.com/danielperitofd/imaestry_server.git
cd imaestry_server

# Criar e ativar ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Aplicar migrações
python manage.py migrate

# Criar superusuário
python manage.py createsuperuser

# Rodar servidor local
python manage.py runserver
-------------------------------------------------------------------------------------------
📥 Importação via CSV
Acesse /musicas/song_import/

Envie um arquivo .csv com os campos:
title, artist, key, bpm, lyrics_excerpt, links, category, themes, notes
-------------------------------------------------------------------------------------------
🎧 Importação via Spotify
Acesse /musicas/import-spotify/
Cole a URL de uma playlist, álbum ou faixa pública do Spotify
Edite os campos sugeridos e clique em “Importar músicas”
-------------------------------------------------------------------------------------------
📌 Roadmap futuro
Filtros por categoria, artista e BPM
Exportação de músicas como PDF ou CSV
Dashboard com estatísticas de repertório
Sugestão de BPM via análise de áudio
Múltiplas categorias por música
-------------------------------------------------------------------------------------------
🌐 Deploy em produção
Servidor Linux com Nginx + Gunicorn
Banco SQLite (temporário)
Arquivos estáticos servidos via Nginx
HTTPS via Certbot (Let's Encrypt)
-------------------------------------------------------------------------------------------
📄 Licença
Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

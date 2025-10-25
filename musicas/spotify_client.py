import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id="10e22c8b31cd4aff8505ddf6abc48245",
    client_secret="a2f61be369974ae2ae8b05cc3bdc840e"
))

def suggest_key(title, artist):
    title = title.lower()
    artist = artist.lower()

    if "adoração" in title or "louvor" in title or "graça" in title:
        return "D"
    if "fernandinho" in artist:
        return "E"
    if "aline barros" in artist:
        return "G"
    return ""


def fetch_spotify_playlist(playlist_url):
    import re
    playlist_id = re.search(r"playlist/([a-zA-Z0-9]+)", playlist_url).group(1)
    results = sp.playlist_tracks(playlist_id)
    tracks = []

    while results:
        for item in results["items"]:
            track = item["track"]
            title = track["name"]
            artist = track["artists"][0]["name"]
            link = track["external_urls"]["spotify"]
            bpm = None
            category = "neutra"
            key = suggest_key(title, artist)

            tracks.append({
                "title": title,
                "artist": artist,
                "links": link,
                "category": category,
                "bpm": bpm,
                "key": key,
                "lyrics_excerpt": "",
                "themes": "",
                "notes": ""
            })
        if results["next"]:
            results = sp.next(results)
        else:
            break
    return tracks

def fetch_spotify_album(album_url):
    import re
    album_id = re.search(r"album/([a-zA-Z0-9]+)", album_url).group(1)
    album = sp.album_tracks(album_id)
    album_info = sp.album(album_id)
    tracks = []

    for item in album["items"]:
        title = item["name"]
        artist = album_info["artists"][0]["name"]
        link = item["external_urls"]["spotify"]
        bpm = None
        category = "neutra"
        key = suggest_key(title, artist)

        tracks.append({
            "title": title,
            "artist": artist,
            "links": link,
            "category": category,
            "bpm": bpm,
            "key": key,
            "lyrics_excerpt": "",
            "themes": "",
            "notes": ""
        })
    return tracks

def fetch_spotify_track(track_url):
    import re
    track_id = re.search(r"track/([a-zA-Z0-9]+)", track_url).group(1)
    track = sp.track(track_id)

    title = track["name"]
    artist = track["artists"][0]["name"]
    link = track["external_urls"]["spotify"]
    category = "neutra"
    bpm = None
    key = suggest_key(title, artist)

    return [{
        "title": title,
        "artist": artist,
        "links": link,
        "category": category,
        "bpm": bpm,
        "key": key,
        "lyrics_excerpt": "",
        "themes": "",
        "notes": ""
    }]

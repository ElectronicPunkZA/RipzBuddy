import musicbrainzngs

musicbrainzngs.set_useragent("NFO-GUI", "1.0", "https://github.com/yourrepo")

def search_musicbrainz_release(artist, album):
    """
    Search MusicBrainz for a release by artist and album title.
    Returns a list of dicts: [{"artist": ..., "album": ..., "year": ..., "tracks": [...], "id": ..., "source": "MusicBrainz"}]
    """
    results = []
    try:
        res = musicbrainzngs.search_releases(artist=artist, release=album, limit=5)
        for release in res.get("release-list", []):
            title = release.get("title", "Unknown")
            year = release.get("date", "Unknown")[:4] if "date" in release else "Unknown"
            mbid = release.get("id", "")
            # Get artist credit
            if "artist-credit" in release and release["artist-credit"]:
                artist_name = release["artist-credit"][0]["artist"]["name"]
            else:
                artist_name = "Unknown"
            # Get tracklist (requires extra query)
            tracks = []
            track_artists = []
            try:
                full_release = musicbrainzngs.get_release_by_id(mbid, includes=["recordings"])
                for med in full_release["release"]["medium-list"]:
                    for trk in med["track-list"]:
                        tracks.append(trk["recording"]["title"])
                        # Per-track artist extraction
                        if "artist-credit" in trk["recording"] and trk["recording"]["artist-credit"]:
                            track_artists.append(trk["recording"]["artist-credit"][0]["artist"]["name"])
                        else:
                            track_artists.append(artist_name)
            except Exception:
                pass
            results.append({
                "artist": artist_name,
                "album": title,
                "year": year,
                "tracks": tracks,
                "track_artists": track_artists,
                "id": mbid,
                "source": "MusicBrainz",
                "label": release["label-info-list"][0]["label"]["name"] if "label-info-list" in release and release["label-info-list"] and "label" in release["label-info-list"][0] and "name" in release["label-info-list"][0]["label"] else "Unknown",
                "catno": release["label-info-list"][0]["catalog-number"] if "label-info-list" in release and release["label-info-list"] and "catalog-number" in release["label-info-list"][0] else "Unknown",
                "country": release.get("country", "Unknown"),
                "release_obj": release
            })
    except Exception as e:
        print(f"[MusicBrainz] Error: {e}")
    return results

def get_release_by_id(mbid):
    """
    Fetch a MusicBrainz release by MBID. Returns a dict with artist, album, year, tracks, id, and source.
    """
    try:
        full_release = musicbrainzngs.get_release_by_id(mbid, includes=["recordings"])
        release = full_release["release"]
        title = release.get("title", "Unknown")
        year = release.get("date", "Unknown")[:4] if "date" in release else "Unknown"
        mbid = release.get("id", mbid)
        # Get artist credit
        if "artist-credit" in release and release["artist-credit"]:
            artist_name = release["artist-credit"][0]["artist"]["name"]
        else:
            artist_name = "Unknown"
        # Get tracklist
        tracks = []
        track_artists = []
        if "medium-list" in release:
            for med in release["medium-list"]:
                for trk in med.get("track-list", []):
                    tracks.append(trk["recording"]["title"])
                    # Per-track artist extraction
                    if "artist-credit" in trk["recording"] and trk["recording"]["artist-credit"]:
                        track_artists.append(trk["recording"]["artist-credit"][0]["artist"]["name"])
                    else:
                        track_artists.append(artist_name)
        return {
            "artist": artist_name,
            "album": title,
            "year": year,
            "tracks": tracks,
            "track_artists": track_artists,
            "id": mbid,
            "source": "MusicBrainz",
            "label": release["label-info-list"][0]["label"]["name"] if "label-info-list" in release and release["label-info-list"] and "label" in release["label-info-list"][0] and "name" in release["label-info-list"][0]["label"] else "Unknown",
            "catno": release["label-info-list"][0]["catalog-number"] if "label-info-list" in release and release["label-info-list"] and "catalog-number" in release["label-info-list"][0] else "Unknown",
            "country": release.get("country", "Unknown"),
            "release_obj": release
        }
    except Exception as e:
        print(f"[MusicBrainz] Error in get_release_by_id: {e}")
        return None

def search_release_by_catno(catno):
    """
    Search MusicBrainz for a release by catalog number. Returns the first matching release as a dict, or None.
    """
    try:
        res = musicbrainzngs.search_releases(catno=catno, limit=5)
        for release in res.get("release-list", []):
            title = release.get("title", "Unknown")
            year = release.get("date", "Unknown")[:4] if "date" in release else "Unknown"
            mbid = release.get("id", "")
            # Get artist credit
            if "artist-credit" in release and release["artist-credit"]:
                artist_name = release["artist-credit"][0]["artist"]["name"]
            else:
                artist_name = "Unknown"
            # Get tracklist (requires extra query)
            tracks = []
            track_artists = []
            try:
                full_release = musicbrainzngs.get_release_by_id(mbid, includes=["recordings"])
                for med in full_release["release"]["medium-list"]:
                    for trk in med["track-list"]:
                        tracks.append(trk["recording"]["title"])
                        # Per-track artist extraction
                        if "artist-credit" in trk["recording"] and trk["recording"]["artist-credit"]:
                            track_artists.append(trk["recording"]["artist-credit"][0]["artist"]["name"])
                        else:
                            track_artists.append(artist_name)
            except Exception:
                pass
            return {
                "artist": artist_name,
                "album": title,
                "year": year,
                "tracks": tracks,
                "track_artists": track_artists,
                "id": mbid,
                "source": "MusicBrainz",
                "label": release["label-info-list"][0]["label"]["name"] if "label-info-list" in release and release["label-info-list"] and "label" in release["label-info-list"][0] and "name" in release["label-info-list"][0]["label"] else "Unknown",
                "catno": release["label-info-list"][0]["catalog-number"] if "label-info-list" in release and release["label-info-list"] and "catalog-number" in release["label-info-list"][0] else "Unknown",
                "country": release.get("country", "Unknown"),
                "release_obj": release
            }
    except Exception as e:
        print(f"[MusicBrainz] Error in search_release_by_catno: {e}")
    return None

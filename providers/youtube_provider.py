"""
YouTube Music Provider - รองรับ YouTube Music ผ่าน ytmusicapi
"""

import os
from typing import List, Optional, Dict, Any
from ytmusicapi import YTMusic

from .base import BaseProvider, Track, Playlist


class YouTubeMusicProvider(BaseProvider):
    """
    YouTube Music Provider
    
    รองรับ 2 วิธีการ authenticate:
    1. OAuth (ถาวรกว่า แต่ตั้งค่ายาก)
    2. Browser Headers (ง่ายกว่า แต่หมดอายุ)
    """
    
    name = "youtube"
    display_name = "YouTube Music"
    supports_oauth = True
    supports_browser_auth = True
    
    def __init__(self):
        super().__init__()
        self.ytm: Optional[YTMusic] = None
    
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with YouTube Music
        
        Args:
            credentials: Dict with key 'auth_file' (path to oauth/browser json)
                      หรือ 'headers_raw' (raw browser headers string)
        
        Returns:
            bool: True if successful
        """
        try:
            auth_file = credentials.get('auth_file')
            headers_raw = credentials.get('headers_raw')
            
            if auth_file and os.path.exists(auth_file):
                self.ytm = YTMusic(auth_file)
            elif headers_raw:
                import json
                import tempfile
                import os
                from ytmusicapi import setup
                # Debug: show first 200 chars of headers
                print(f"[DEBUG] Headers preview: {headers_raw[:200]}...")
                print(f"[DEBUG] Headers length: {len(headers_raw)} chars")
                # Use ytmusicapi.setup function (returns dict)
                auth_json = setup(headers_raw=headers_raw)
                print(f"[DEBUG] Setup returned type: {type(auth_json)}")
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(auth_json, f)
                    temp_file = f.name
                self.ytm = YTMusic(temp_file)
                # Clean up temp file after loading
                try:
                    os.unlink(temp_file)
                except:
                    pass
            else:
                raise ValueError("Must provide 'auth_file' or 'headers_raw'")
            
            # Test authentication
            self.ytm.get_library_playlists(limit=1)
            self.authenticated = True
            self.credentials = credentials
            return True
            
        except Exception as e:
            print(f"Authentication failed: {e}")
            self.authenticated = False
            return False
    
    def _parse_track(self, track_data: Dict) -> Track:
        """Convert ytmusic track data to universal Track format"""
        artists = []
        if 'artists' in track_data:
            artists = [a['name'] for a in track_data['artists'] if 'name' in a]
        elif 'artist' in track_data:
            artists = [track_data['artist']]
        
        return Track(
            title=track_data.get('title', 'Unknown'),
            artists=artists,
            album=track_data.get('album', {}).get('name') if isinstance(track_data.get('album'), dict) else track_data.get('album'),
            duration_ms=track_data.get('duration_seconds', 0) * 1000 if track_data.get('duration_seconds') else None,
            platform_id=track_data.get('videoId'),
            platform_data=track_data
        )
    
    def _parse_playlist(self, playlist_data: Dict) -> Playlist:
        """Convert ytmusic playlist data to universal Playlist format"""
        # Extract track count from API response
        count = playlist_data.get('count', 0)
        if count is None:
            count = 0
        else:
            # Convert to int in case it's a string
            try:
                count = int(count)
            except (ValueError, TypeError):
                count = 0
        
        return Playlist(
            name=playlist_data.get('title', 'Unknown'),
            description=playlist_data.get('description', ''),
            platform_id=playlist_data.get('playlistId'),
            is_public=playlist_data.get('privacy') == 'PUBLIC',
            api_track_count=count,
            platform_data=playlist_data
        )
    
    def get_playlists(self, limit: int = 100) -> List[Playlist]:
        """Get user's playlists"""
        if not self.ytm:
            raise RuntimeError("Not authenticated")
        
        raw_playlists = self.ytm.get_library_playlists(limit=limit)
        return [self._parse_playlist(p) for p in raw_playlists]
    
    def get_playlist_tracks(self, playlist_id: str, limit: int = 1000) -> List[Track]:
        """Get tracks in a playlist"""
        if not self.ytm:
            raise RuntimeError("Not authenticated")
        
        playlist_data = self.ytm.get_playlist(playlist_id, limit=limit)
        tracks = playlist_data.get('tracks', [])
        return [self._parse_track(t) for t in tracks]
    
    def create_playlist(self, name: str, description: str = "", 
                       is_public: bool = False) -> Optional[str]:
        """Create new playlist"""
        if not self.ytm:
            raise RuntimeError("Not authenticated")
        
        privacy = 'PUBLIC' if is_public else 'PRIVATE'
        try:
            playlist_id = self.ytm.create_playlist(
                title=name,
                description=description,
                privacy_status=privacy
            )
            return playlist_id
        except Exception as e:
            print(f"Failed to create playlist: {e}")
            return None
    
    def add_tracks_to_playlist(self, playlist_id: str, 
                               tracks: List[Track]) -> tuple[int, int]:
        """Add tracks to playlist"""
        if not self.ytm:
            raise RuntimeError("Not authenticated")
        
        success = 0
        failed = 0
        
        for track in tracks:
            try:
                # Search for track on YouTube Music
                if track.platform_id:
                    # Use original ID if available
                    video_id = track.platform_id
                else:
                    # Search by title and artist
                    query = track.search_query()
                    results = self.ytm.search(query, filter="songs", limit=1)
                    if not results:
                        failed += 1
                        continue
                    video_id = results[0]['videoId']
                
                self.ytm.add_playlist_items(playlist_id, [video_id])
                success += 1
                
            except Exception as e:
                failed += 1
        
        return success, failed
    
    def search_track(self, query: str, limit: int = 5) -> List[Track]:
        """Search for tracks"""
        if not self.ytm:
            raise RuntimeError("Not authenticated")
        
        results = self.ytm.search(query, filter="songs", limit=limit)
        return [self._parse_track(r) for r in results]
    
    # YouTube Music specific methods
    
    def get_liked_tracks(self, limit: int = 1000) -> List[Track]:
        """Get liked songs (LM playlist)"""
        if not self.ytm:
            raise RuntimeError("Not authenticated")
        
        liked_data = self.ytm.get_liked_songs(limit=limit)
        tracks = liked_data.get('tracks', [])
        return [self._parse_track(t) for t in tracks]
    
    def get_saved_albums(self, limit: int = 1000) -> List[Dict]:
        """Get saved albums"""
        if not self.ytm:
            raise RuntimeError("Not authenticated")
        
        return self.ytm.get_library_albums(limit=limit)
    
    def get_subscriptions(self, limit: int = 1000) -> List[Dict]:
        """Get artist subscriptions"""
        if not self.ytm:
            raise RuntimeError("Not authenticated")
        
        return self.ytm.get_library_subscriptions(limit=limit)
    
    def like_track(self, video_id: str) -> bool:
        """Like a track"""
        if not self.ytm:
            raise RuntimeError("Not authenticated")
        
        try:
            self.ytm.rate_song(video_id, 'LIKE')
            return True
        except Exception:
            return False
    
    def subscribe_artist(self, channel_id: str) -> bool:
        """Subscribe to artist"""
        if not self.ytm:
            raise RuntimeError("Not authenticated")
        
        try:
            self.ytm.subscribe_artists([channel_id])
            return True
        except Exception:
            return False
    
    def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a playlist"""
        if not self.ytm:
            raise RuntimeError("Not authenticated")
        
        try:
            self.ytm.delete_playlist(playlist_id)
            return True
        except Exception as e:
            print(f"Failed to delete playlist: {e}")
            return False

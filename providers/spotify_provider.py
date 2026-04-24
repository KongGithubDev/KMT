"""
Spotify Provider - รองรับ Spotify ผ่าน Spotify Web API
"""

import os
import base64
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

import requests

from .base import BaseProvider, Track, Playlist


class SpotifyProvider(BaseProvider):
    """
    Spotify Provider
    
    รองรับการ authenticate ผ่าน:
    1. OAuth2 Authorization Code flow (สำหรับ production)
    2. Access Token ที่มีอยู่แล้ว (สำหรับ testing)
    """
    
    name = "spotify"
    display_name = "Spotify"
    supports_oauth = True
    supports_browser_auth = False
    
    # Spotify API endpoints
    API_BASE = "https://api.spotify.com/v1"
    AUTH_URL = "https://accounts.spotify.com/authorize"
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    
    def __init__(self):
        super().__init__()
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self.user_id: Optional[str] = None
    
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with Spotify
        
        Args:
            credentials: Dict with keys:
                - 'access_token': OAuth access token
                - 'refresh_token': (optional) Refresh token
                - 'client_id': Spotify app client ID
                - 'client_secret': Spotify app client secret
        
        Returns:
            bool: True if successful
        """
        try:
            self.access_token = credentials.get('access_token')
            self.refresh_token = credentials.get('refresh_token')
            self.client_id = credentials.get('client_id')
            self.client_secret = credentials.get('client_secret')
            
            if not self.access_token:
                raise ValueError("Must provide 'access_token'")
            
            # Test authentication by getting current user profile
            self._test_authentication()
            
            self.authenticated = True
            self.credentials = credentials
            return True
            
        except Exception as e:
            print(f"Spotify authentication failed: {e}")
            self.authenticated = False
            return False
    
    def _test_authentication(self):
        """Test if access token is valid by getting user profile"""
        headers = self._get_auth_headers()
        response = requests.get(f"{self.API_BASE}/me", headers=headers)
        
        if response.status_code == 401:
            # Token expired, try to refresh
            if self.refresh_token and self.client_id and self.client_secret:
                self._refresh_access_token()
                headers = self._get_auth_headers()
                response = requests.get(f"{self.API_BASE}/me", headers=headers)
        
        response.raise_for_status()
        user_data = response.json()
        self.user_id = user_data.get('id')
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _refresh_access_token(self):
        """Refresh access token using refresh token"""
        if not all([self.refresh_token, self.client_id, self.client_secret]):
            raise ValueError("Missing credentials for token refresh")
        
        auth_string = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {auth_string}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        response = requests.post(self.TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data.get('access_token')
        
        # Update refresh token if new one provided
        if 'refresh_token' in token_data:
            self.refresh_token = token_data['refresh_token']
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make authenticated request to Spotify API"""
        headers = self._get_auth_headers()
        url = f"{self.API_BASE}/{endpoint}"
        
        response = requests.request(method, url, headers=headers, **kwargs)
        
        if response.status_code == 401 and self.refresh_token:
            # Token expired, refresh and retry
            self._refresh_access_token()
            headers = self._get_auth_headers()
            response = requests.request(method, url, headers=headers, **kwargs)
        
        response.raise_for_status()
        return response.json() if response.content else {}
    
    def _parse_track(self, track_data: Dict) -> Track:
        """Convert Spotify track data to universal Track format"""
        if not track_data:
            return Track(title="Unknown", artists=["Unknown"])
        
        # Handle track object structure
        track_info = track_data
        if 'track' in track_data:
            track_info = track_data['track']
        
        # Get artists
        artists = []
        for artist in track_info.get('artists', []):
            if 'name' in artist:
                artists.append(artist['name'])
        
        # Get album
        album = track_info.get('album', {}).get('name') if track_info.get('album') else None
        
        # Get duration
        duration_ms = track_info.get('duration_ms')
        
        # Get ISRC if available
        isrc = track_info.get('external_ids', {}).get('isrc')
        
        return Track(
            title=track_info.get('name', 'Unknown'),
            artists=artists if artists else ['Unknown'],
            album=album,
            duration_ms=duration_ms,
            isrc=isrc,
            platform_id=track_info.get('id'),
            platform_data=track_info
        )
    
    def _parse_playlist(self, playlist_data: Dict) -> Playlist:
        """Convert Spotify playlist data to universal Playlist format"""
        # Get track count from tracks object
        tracks_data = playlist_data.get('tracks', {})
        if isinstance(tracks_data, dict):
            track_count = tracks_data.get('total', 0)
        else:
            track_count = len(tracks_data) if tracks_data else 0
        
        return Playlist(
            name=playlist_data.get('name', 'Unknown'),
            description=playlist_data.get('description', ''),
            platform_id=playlist_data.get('id'),
            is_public=playlist_data.get('public', False),
            api_track_count=track_count,
            platform_data=playlist_data
        )
    
    def get_playlists(self, limit: int = 100) -> List[Playlist]:
        """Get user's playlists"""
        if not self.access_token:
            raise RuntimeError("Not authenticated")
        
        playlists = []
        offset = 0
        
        while len(playlists) < limit:
            params = {
                'limit': min(50, limit - len(playlists)),
                'offset': offset
            }
            
            data = self._make_request('GET', 'me/playlists', params=params)
            items = data.get('items', [])
            
            if not items:
                break
            
            for item in items:
                # Skip if this playlist is not owned by user (e.g., followed playlists)
                if item.get('owner', {}).get('id') == self.user_id:
                    playlists.append(self._parse_playlist(item))
            
            offset += len(items)
            
            if len(items) < 50:
                break
        
        return playlists[:limit]
    
    def get_playlist_tracks(self, playlist_id: str, limit: int = 1000) -> List[Track]:
        """Get tracks in a playlist"""
        if not self.access_token:
            raise RuntimeError("Not authenticated")
        
        tracks = []
        offset = 0
        
        while len(tracks) < limit:
            params = {
                'limit': min(100, limit - len(tracks)),
                'offset': offset,
                'fields': 'items(track(id,name,artists,album,duration_ms,external_ids))'
            }
            
            data = self._make_request('GET', f'playlists/{playlist_id}/tracks', params=params)
            items = data.get('items', [])
            
            if not items:
                break
            
            for item in items:
                track = self._parse_track(item)
                if track.title != "Unknown":
                    tracks.append(track)
            
            offset += len(items)
            
            if len(items) < 100:
                break
        
        return tracks[:limit]
    
    def create_playlist(self, name: str, description: str = "", 
                       is_public: bool = False) -> Optional[str]:
        """Create new playlist"""
        if not self.access_token or not self.user_id:
            raise RuntimeError("Not authenticated")
        
        try:
            data = {
                'name': name,
                'description': description,
                'public': is_public
            }
            
            result = self._make_request(
                'POST', 
                f'users/{self.user_id}/playlists',
                json=data
            )
            
            return result.get('id')
            
        except Exception as e:
            print(f"Failed to create playlist: {e}")
            return None
    
    def add_tracks_to_playlist(self, playlist_id: str, 
                               tracks: List[Track]) -> tuple[int, int]:
        """Add tracks to playlist"""
        if not self.access_token:
            raise RuntimeError("Not authenticated")
        
        success = 0
        failed = 0
        track_uris = []
        
        for track in tracks:
            try:
                # Search for track on Spotify
                if track.isrc:
                    # Try ISRC search first (most accurate)
                    search_query = f"isrc:{track.isrc}"
                else:
                    # Search by title and artist
                    search_query = f"track:{track.title} artist:{track.artists[0]}"
                
                search_result = self.search_track(search_query, limit=1)
                
                if search_result:
                    spotify_track_id = search_result[0].platform_id
                    track_uris.append(f"spotify:track:{spotify_track_id}")
                else:
                    failed += 1
                    
            except Exception as e:
                print(f"Failed to find track '{track.title}': {e}")
                failed += 1
        
        # Add tracks in batches (max 100 per request)
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            try:
                self._make_request(
                    'POST',
                    f'playlists/{playlist_id}/tracks',
                    json={'uris': batch}
                )
                success += len(batch)
            except Exception as e:
                print(f"Failed to add batch to playlist: {e}")
                failed += len(batch)
        
        return success, failed
    
    def search_track(self, query: str, limit: int = 5) -> List[Track]:
        """Search for tracks"""
        if not self.access_token:
            raise RuntimeError("Not authenticated")
        
        params = {
            'q': query,
            'type': 'track',
            'limit': limit
        }
        
        data = self._make_request('GET', 'search', params=params)
        tracks_data = data.get('tracks', {}).get('items', [])
        
        return [self._parse_track(t) for t in tracks_data]
    
    def get_liked_tracks(self, limit: int = 1000) -> List[Track]:
        """Get user's liked/saved tracks"""
        if not self.access_token:
            raise RuntimeError("Not authenticated")
        
        tracks = []
        offset = 0
        
        while len(tracks) < limit:
            params = {
                'limit': min(50, limit - len(tracks)),
                'offset': offset
            }
            
            data = self._make_request('GET', 'me/tracks', params=params)
            items = data.get('items', [])
            
            if not items:
                break
            
            for item in items:
                track = self._parse_track(item)
                if track.title != "Unknown":
                    tracks.append(track)
            
            offset += len(items)
            
            if len(items) < 50:
                break
        
        return tracks[:limit]
    
    def like_track(self, track_id: str) -> bool:
        """Like/save a track"""
        if not self.access_token:
            raise RuntimeError("Not authenticated")
        
        try:
            self._make_request(
                'PUT',
                'me/tracks',
                json={'ids': [track_id]}
            )
            return True
        except Exception:
            return False

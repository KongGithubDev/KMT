"""
Base Provider - Abstract class สำหรับทุก music platform
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class Track:
    """Universal Track Representation"""
    title: str
    artists: List[str]
    album: Optional[str] = None
    duration_ms: Optional[int] = None
    isrc: Optional[str] = None  # International Standard Recording Code
    platform_id: Optional[str] = None  # ID บนแพลตฟอร์มต้นทาง
    platform_data: Optional[Dict[str, Any]] = None  # ข้อมูลดิบจากแพลตฟอร์ม
    
    def __str__(self):
        artists_str = ', '.join(self.artists)
        return f"{self.title} - {artists_str}"
    
    def search_query(self) -> str:
        """Generate search query for cross-platform matching"""
        return f"{self.title} {self.artists[0]}"


@dataclass
class Playlist:
    """Universal Playlist Representation"""
    name: str
    description: str = ""
    tracks: List[Track] = None
    platform_id: Optional[str] = None
    is_public: bool = False
    api_track_count: int = 0  # Track count from API (lazy loading)
    platform_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.tracks is None:
            self.tracks = []
    
    def track_count(self) -> int:
        # Return API track count if available, otherwise actual loaded tracks
        if self.api_track_count > 0:
            return self.api_track_count
        return len(self.tracks)


class BaseProvider(ABC):
    """
    Abstract base class สำหรับทุก music platform provider
    
    ทุก provider ต้อง implement methods เหล่านี้:
    - authenticate: เชื่อมต่อกับแพลตฟอร์ม
    - get_playlists: ดึงรายการเพลย์ลิสต์
    - get_playlist_tracks: ดึงเพลงในเพลย์ลิสต์
    - create_playlist: สร้างเพลย์ลิสต์ใหม่
    - add_tracks_to_playlist: เพิ่มเพลงเข้าเพลย์ลิสต์
    - search_track: ค้นหาเพลง
    """
    
    name: str = "base"
    display_name: str = "Base Provider"
    supports_oauth: bool = False
    supports_browser_auth: bool = False
    
    def __init__(self):
        self.authenticated = False
        self.credentials = None
    
    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with the platform
        
        Args:
            credentials: OAuth tokens, browser headers, or API keys
            
        Returns:
            bool: True if authentication successful
        """
        pass
    
    @abstractmethod
    def get_playlists(self, limit: int = 100) -> List[Playlist]:
        """
        Get list of user's playlists
        
        Args:
            limit: Maximum number of playlists to return
            
        Returns:
            List of Playlist objects
        """
        pass
    
    @abstractmethod
    def get_playlist_tracks(self, playlist_id: str, limit: int = 1000) -> List[Track]:
        """
        Get tracks in a playlist
        
        Args:
            playlist_id: Platform-specific playlist ID
            limit: Maximum number of tracks
            
        Returns:
            List of Track objects
        """
        pass
    
    @abstractmethod
    def create_playlist(self, name: str, description: str = "", 
                       is_public: bool = False) -> Optional[str]:
        """
        Create a new playlist
        
        Args:
            name: Playlist name
            description: Playlist description
            is_public: Whether playlist is public
            
        Returns:
            New playlist ID or None if failed
        """
        pass
    
    @abstractmethod
    def add_tracks_to_playlist(self, playlist_id: str, 
                               tracks: List[Track]) -> tuple[int, int]:
        """
        Add tracks to playlist
        
        Args:
            playlist_id: Target playlist ID
            tracks: List of Track objects to add
            
        Returns:
            Tuple of (success_count, failed_count)
        """
        pass
    
    @abstractmethod
    def search_track(self, query: str, limit: int = 5) -> List[Track]:
        """
        Search for tracks
        
        Args:
            query: Search query string
            limit: Maximum results
            
        Returns:
            List of matching Track objects
        """
        pass
    
    # Optional methods for additional features
    
    def get_liked_tracks(self, limit: int = 1000) -> List[Track]:
        """Get user's liked/saved tracks (optional)"""
        raise NotImplementedError(f"{self.name} does not support liked tracks")
    
    def get_saved_albums(self, limit: int = 1000) -> List[Any]:
        """Get user's saved albums (optional)"""
        raise NotImplementedError(f"{self.name} does not support saved albums")
    
    def get_subscriptions(self, limit: int = 1000) -> List[Any]:
        """Get user's artist subscriptions (optional)"""
        raise NotImplementedError(f"{self.name} does not support subscriptions")
    
    def like_track(self, track_id: str) -> bool:
        """Like/save a track (optional)"""
        raise NotImplementedError(f"{self.name} does not support liking tracks")
    
    def subscribe_artist(self, artist_id: str) -> bool:
        """Subscribe to an artist (optional)"""
        raise NotImplementedError(f"{self.name} does not support artist subscription")

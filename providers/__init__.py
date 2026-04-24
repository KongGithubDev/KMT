"""
Music Platform Providers
รองรับหลายแพลตฟอร์ม: YouTube Music, Spotify, Apple Music, etc.
"""

from .base import BaseProvider, Track, Playlist
from .youtube_provider import YouTubeMusicProvider
from .spotify_provider import SpotifyProvider

__all__ = ['BaseProvider', 'Track', 'Playlist', 'YouTubeMusicProvider', 'SpotifyProvider']

# Provider Registry
PROVIDERS = {
    'youtube': YouTubeMusicProvider,
    'ytmusic': YouTubeMusicProvider,
    'spotify': SpotifyProvider,
    # Future providers:
    # 'apple': AppleMusicProvider,
    # 'tidal': TidalProvider,
    # 'deezer': DeezerProvider,
}


def get_provider(name: str) -> type[BaseProvider]:
    """Get provider class by name"""
    provider = PROVIDERS.get(name.lower())
    if not provider:
        raise ValueError(f"Unknown provider: {name}. Available: {list(PROVIDERS.keys())}")
    return provider

# 🎵 K(MT) Music Transfer

Transfer playlists between music streaming platforms. Supports Spotify, YouTube Music, Apple Music, TIDAL, Deezer, and more.

![Supported Platforms](https://img.shields.io/badge/Platforms-28+-green)
![Python](https://img.shields.io/badge/Python-3.9+-blue)

## 🎯 Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| 🎵 **YouTube Music** | ✅ Ready | OAuth & Browser Headers supported |
| 🎧 **Spotify** | ✅ Ready | Spotify Web API with OAuth |
| 🍎 **Apple Music** | 🚧 In Development | MusicKit required |
| 🎼 **TIDAL** | 📋 Planned | |
| 💿 **Deezer** | 📋 Planned | |
| ☁️ **SoundCloud** | 📋 Planned | |
| 🎹 **Amazon Music** | 📋 Planned | |
| 📻 **KKBOX** | 📋 Planned | |
| 🎸 **Last.fm** | 📋 Planned | |
| 🎤 **More** | 📋 Planned | Qobuz, Anghami, Napster, Pandora... |

**Legend:** ✅ Ready | 🚧 In Development | 📋 Planned

---

## ✨ Features

### Available (YouTube Music & Spotify)
- ✅ Transfer playlists between accounts
- ✅ Transfer all playlists at once
- ✅ Transfer Liked Songs, Saved Albums, Subscriptions
- ✅ Automatic track search and matching
- ✅ Progress bar during transfer
- ✅ Support for Browser Headers (easy) and OAuth (secure)
- ✅ Cross-platform transfer (e.g., Spotify → YouTube Music)

### Multi-Platform Roadmap
- 🚧 Unified API for all platforms
- 🚧 Smart matching algorithm (cross-platform track matching)
- 🚧 Web UI (Flask)
- 🚧 Import/Export from files (CSV, JSON)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Web UI (Recommended)
```bash
python web_app.py
```
Then open http://localhost:5000 in your browser.

### Method 1: Browser Headers (Easy, no Google Cloud Project needed)

```bash
# Setup source account
python ytmusic_transfer.py setup --source --browser

# Setup destination account
python ytmusic_transfer.py setup --dest --browser
```

Follow these steps:
1. Open browser and go to https://music.youtube.com and login
2. Press **F12** to open Developer Tools → **Network** tab
3. Play a song or click something
4. Find the request named **'browse'** in the Network tab
5. Right-click on the request → **Copy** → **Copy as cURL (bash)**
6. Paste everything back and press Enter twice

---

### Method 2: OAuth (More durable, requires Google Cloud Project)

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project → Enable **YouTube Data API v3**
3. **Credentials > Create Credentials > OAuth client ID** → Select **Desktop app**
4. Run:
```bash
python ytmusic_transfer.py setup --source --oauth --client-id "ID" --client-secret "SECRET"
```

### 3. View Playlists
```bash
# View source account playlists
python ytmusic_transfer.py list-playlists --source

# View destination account playlists
python ytmusic_transfer.py list-playlists --dest
```

### 4. Transfer Playlist
```bash
# Transfer single playlist
python ytmusic_transfer.py transfer PLAYLIST_ID

# Transfer with new name
python ytmusic_transfer.py transfer PLAYLIST_ID --new-name "My New Playlist"

# Transfer and set as Public
python ytmusic_transfer.py transfer PLAYLIST_ID --privacy PUBLIC
```

### 5. Transfer All Playlists
```bash
python ytmusic_transfer.py transfer-all-playlists --all
```

### 6. Transfer Other Data (Liked Songs, Albums, Subscriptions)
```bash
# Transfer liked songs
python ytmusic_transfer.py transfer-liked-songs

# Transfer saved albums
python ytmusic_transfer.py transfer-saved-albums

# Transfer artist subscriptions
python ytmusic_transfer.py transfer-subscriptions
```

## All Commands

| Command | Description |
|---------|-------------|
| `setup --source --browser` | Setup source account (Browser Headers) |
| `setup --dest --browser` | Setup destination account (Browser Headers) |
| `setup --source --oauth --client-id X --client-secret Y` | Setup source account (OAuth) |
| `list-accounts` | Show account status |
| `list-playlists --source/--dest` | Show playlists |
| `view-playlist PLAYLIST_ID` | View playlist details |
| `transfer PLAYLIST_ID` | Transfer playlist |
| `transfer-all-playlists --all` | Transfer all playlists |
| `transfer-liked-songs` | Transfer liked songs |
| `transfer-saved-albums` | Transfer saved albums |
| `transfer-subscriptions` | Transfer subscriptions |

## 🏗️ Architecture (For Contributors)

```
┌─────────────────────────────────────────────────────────────┐
│                    MusicTransfer System                      │
├─────────────────────────────────────────────────────────────┤
│  Web UI (Flask)                                             │
│  └── Cross-platform selection modal                         │
│  └── Setup pages for each platform                         │
│  └── Transfer page with playlist selection                 │
├─────────────────────────────────────────────────────────────┤
│  BaseProvider (Abstract Class)                               │
│  ├── authenticate()                                          │
│  ├── get_playlists()                                         │
│  ├── get_playlist_tracks()                                   │
│  ├── create_playlist()                                       │
│  ├── add_tracks_to_playlist()                                │
│  └── search_track()                                          │
├─────────────────────────────────────────────────────────────┤
│  Providers:                                                  │
│  ├── YouTubeMusicProvider ✅                                 │
│  ├── SpotifyProvider ✅                                      │
│  ├── AppleMusicProvider 🚧                                   │
│  └── ... (more coming)                                       │
├─────────────────────────────────────────────────────────────┤
│  TransferEngine                                              │
│  ├── match_tracks() - Cross-platform track matching          │
│  ├── transfer_playlist()                                     │
│  └── transfer_all()                                          │
└─────────────────────────────────────────────────────────────┘
```

## 🤝 Contributing

Want to add a new platform? Follow these steps:

1. Create a file in `providers/[platform]_provider.py`
2. Inherit from `BaseProvider`
3. Implement required methods
4. Add tests and submit PR!

**Example:**
```python
from providers.base import BaseProvider

class SpotifyProvider(BaseProvider):
    def authenticate(self, credentials):
        # Implement OAuth flow
        pass
    
    def get_playlists(self):
        # Return list of playlists
        pass
    
    def search_track(self, title, artist, album=None):
        # Search and return best match
        pass
```

## 📋 Roadmap

### Phase 1: Foundation ✅
- [x] YouTube Music Provider
- [x] CLI Interface
- [x] Transfer between same platform
- [x] Web UI with platform selection

### Phase 2: Multi-Platform ✅
- [x] Spotify Provider
- [ ] Apple Music Provider
- [ ] Unified Transfer Engine
- [ ] Cross-platform track matching

### Phase 3: Advanced Features 📋
- [ ] Smart matching with fuzzy search
- [ ] CSV/JSON import-export
- [ ] Batch operations
- [ ] Playlist synchronization (sync changes)

### Phase 4: More Platforms 📋
- [ ] TIDAL
- [ ] Deezer
- [ ] Amazon Music
- [ ] SoundCloud
- [ ] KKBOX, Last.fm, etc.

## 📝 Notes

- OAuth tokens are saved to `~/.ytmusic_transfer/`
- Tracks not found will be skipped and shown in the report
- Supports up to 10,000 tracks per playlist
- **Browser headers expire** every 2-4 weeks and need to be renewed
- Cross-platform transfer requires matching algorithm (ISRC or title+artist)

## 📄 License

MIT License - Free to use, modify at your own risk

---

**Support this project:** ⭐ Star on GitHub or share with friends!

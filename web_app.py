"""
Music Transfer Web UI - Flask App
Design: Notion-inspired warm minimalism
Production-ready with OAuth support for Render deployment
"""

import os
import sys
import json
import secrets
import base64
import hashlib
from urllib.parse import urlencode
import requests
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
from colorama import init, Fore, Style

# Import providers
from providers import get_provider, PROVIDERS
from providers.youtube_provider import YouTubeMusicProvider
from providers.spotify_provider import SpotifyProvider

init(autoreset=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Production config
IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production'
BASE_URL = os.environ.get('BASE_URL', 'https://kmt.kongwatcharapong.in.th')

# Config
CONFIG_DIR = os.path.expanduser("~/.ytmusic_transfer")
UPLOAD_FOLDER = os.path.join(CONFIG_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'json', 'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['SESSION_TYPE'] = 'filesystem'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# OAuth Configuration from environment
OAUTH_CONFIG = {
    'spotify': {
        'client_id': os.environ.get('SPOTIFY_CLIENT_ID'),
        'client_secret': os.environ.get('SPOTIFY_CLIENT_SECRET'),
        'redirect_uri': os.environ.get('SPOTIFY_REDIRECT_URI', f'{BASE_URL}/callback/spotify'),
        'auth_url': 'https://accounts.spotify.com/authorize',
        'token_url': 'https://accounts.spotify.com/api/token',
        'scopes': 'playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public user-library-read user-library-modify'
    },
    'youtube': {
        'client_id': os.environ.get('YOUTUBE_CLIENT_ID'),
        'client_secret': os.environ.get('YOUTUBE_CLIENT_SECRET'),
        'redirect_uri': os.environ.get('YOUTUBE_REDIRECT_URI', f'{BASE_URL}/callback/youtube'),
        'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'scopes': 'https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.readonly'
    }
}

# Active connections stored in session
SESSION_CONNECTIONS_KEY = 'music_transfer_connections'


@app.route('/')
def index():
    """Main page - Platform selection like TuneMyMusic"""
    platforms = {
        'youtube': {
            'name': 'YouTube Music',
            'icon': 'youtube',
            'status': 'ready',
            'color': '#FF0000',
            'description': 'รองรับเต็มรูปแบบ'
        },
        'spotify': {
            'name': 'Spotify',
            'icon': 'spotify',
            'status': 'ready',
            'color': '#1DB954',
            'description': 'รองรับเต็มรูปแบบ'
        },
        'apple': {
            'name': 'Apple Music',
            'icon': 'apple',
            'status': 'coming_soon',
            'color': '#FA57C1',
            'description': 'กำลังพัฒนา'
        },
        'tidal': {
            'name': 'TIDAL',
            'icon': 'tidal',
            'status': 'planned',
            'color': '#000000',
            'description': 'แผนอนาคต'
        },
        'deezer': {
            'name': 'Deezer',
            'icon': 'deezer',
            'status': 'planned',
            'color': '#EF5466',
            'description': 'แผนอนาคต'
        },
        'soundcloud': {
            'name': 'SoundCloud',
            'icon': 'soundcloud',
            'status': 'planned',
            'color': '#FF5500',
            'description': 'แผนอนาคต'
        },
        'amazon': {
            'name': 'Amazon Music',
            'icon': 'amazon',
            'status': 'planned',
            'color': '#00A8E1',
            'description': 'แผนอนาคต'
        },
        'kkbox': {
            'name': 'KKBOX',
            'icon': 'kkbox',
            'status': 'planned',
            'color': '#00C9A7',
            'description': 'แผนอนาคต'
        },
        'yandex': {
            'name': 'Yandex Music',
            'icon': 'music',
            'status': 'planned',
            'color': '#FFCC00',
            'description': 'แผนอนาคต'
        },
        'bandcamp': {
            'name': 'Bandcamp',
            'icon': 'music',
            'status': 'planned',
            'color': '#629AA9',
            'description': 'แผนอนาคต'
        },
        'napster': {
            'name': 'Napster',
            'icon': 'music',
            'status': 'planned',
            'color': '#E62E2D',
            'description': 'แผนอนาคต'
        },
        'qobuz': {
            'name': 'Qobuz',
            'icon': 'music',
            'status': 'planned',
            'color': '#2E5DFF',
            'description': 'แผนอนาคต'
        },
        'beatport': {
            'name': 'Beatport',
            'icon': 'music',
            'status': 'planned',
            'color': '#00A7E1',
            'description': 'แผนอนาคต'
        },
        'pandora': {
            'name': 'Pandora',
            'icon': 'music',
            'status': 'planned',
            'color': '#005483',
            'description': 'แผนอนาคต'
        },
        'anghami': {
            'name': 'Anghami',
            'icon': 'music',
            'status': 'planned',
            'color': '#E94F3B',
            'description': 'แผนอนาคต'
        },
        'lastfm': {
            'name': 'Last.fm',
            'icon': 'music',
            'status': 'planned',
            'color': '#D51007',
            'description': 'แผนอนาคต'
        },
        'boomplay': {
            'name': 'Boomplay',
            'icon': 'music',
            'status': 'planned',
            'color': '#E91E63',
            'description': 'แผนอนาคต'
        },
        'audiomack': {
            'name': 'Audiomack',
            'icon': 'music',
            'status': 'planned',
            'color': '#E35B20',
            'description': 'แผนอนาคต'
        },
        'jiosaavn': {
            'name': 'JioSaavn',
            'icon': 'music',
            'status': 'planned',
            'color': '#2BC48A',
            'description': 'แผนอนาคต'
        },
        'gaana': {
            'name': 'Gaana',
            'icon': 'music',
            'status': 'planned',
            'color': '#E72C30',
            'description': 'แผนอนาคต'
        },
        'resso': {
            'name': 'Resso',
            'icon': 'music',
            'status': 'planned',
            'color': '#FF0050',
            'description': 'แผนอนาคต'
        },
        'joox': {
            'name': 'JOOX',
            'icon': 'music',
            'status': 'planned',
            'color': '#00CC66',
            'description': 'แผนอนาคต'
        },
        'bugs': {
            'name': 'Bugs',
            'icon': 'music',
            'status': 'planned',
            'color': '#E31937',
            'description': 'แผนอนาคต'
        },
        'melon': {
            'name': 'Melon',
            'icon': 'music',
            'status': 'planned',
            'color': '#00CD3C',
            'description': 'แผนอนาคต'
        },
        'genie': {
            'name': 'Genie',
            'icon': 'music',
            'status': 'planned',
            'color': '#0088FF',
            'description': 'แผนอนาคต'
        },
        'flo': {
            'name': 'FLO',
            'icon': 'music',
            'status': 'planned',
            'color': '#3F51B5',
            'description': 'แผนอนาคต'
        },
        'vibe': {
            'name': 'VIBE',
            'icon': 'music',
            'status': 'planned',
            'color': '#FF0055',
            'description': 'แผนอนาคต'
        },
        'soribada': {
            'name': 'Soribada',
            'icon': 'music',
            'status': 'planned',
            'color': '#00AEEF',
            'description': 'แผนอนาคต'
        }
    }
    return render_template('index.html', platforms=platforms)


@app.route('/setup/<platform>', methods=['GET', 'POST'])
def setup_platform(platform):
    """Setup authentication for a platform"""
    if platform not in PROVIDERS:
        flash(f'แพลตฟอร์ม {platform} ยังไม่รองรับ', 'error')
        return redirect(url_for('index'))
    
    connection_type = request.args.get('as', 'source')
    
    if request.method == 'POST':
        setup_type = request.form.get('setup_type', 'oauth')  # Default to OAuth now
        
        if setup_type == 'oauth':
            # Start OAuth flow
            config = OAUTH_CONFIG.get(platform)
            if not config or not config.get('client_id'):
                flash(f'OAuth ไม่พร้อมใช้งานสำหรับ {platform} กรุณาตั้งค่า Client ID', 'error')
                return redirect(url_for('setup_platform', platform=platform, **{'as': connection_type}))
            
            # Generate state parameter with connection type
            state_data = {
                'platform': platform,
                'connection_type': connection_type,
                'nonce': secrets.token_urlsafe(16)
            }
            state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
            session['oauth_state'] = state
            
            # Generate PKCE verifier
            code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')
            session['code_verifier'] = code_verifier
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip('=')
            
            # Build authorization URL
            auth_params = {
                'client_id': config['client_id'],
                'response_type': 'code',
                'redirect_uri': config['redirect_uri'],
                'scope': config['scopes'],
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'
            }
            
            if platform == 'youtube':
                auth_params['access_type'] = 'offline'
                auth_params['prompt'] = 'consent'
            
            auth_url = f"{config['auth_url']}?{urlencode(auth_params)}"
            return redirect(auth_url)
        
        elif setup_type == 'browser':
            headers_raw = request.form.get('headers_raw', '').strip()
            if not headers_raw:
                flash('กรุณาวาง Browser Headers', 'error')
                return redirect(url_for('setup_platform', platform=platform))
            
            try:
                from ytmusicapi import setup
                import os
                import re
                
                # Parse cURL and extract headers manually
                import json
                
                headers_dict = {}
                
                # Extract -H headers (format: -H 'key: value')
                # Use non-greedy match for value part to handle multiple headers
                header_matches = re.findall(r"-H\s+'([^:]+):(.+?)'(?:\s*\\?\n?|$)", headers_raw, re.MULTILINE)
                for key, value in header_matches:
                    headers_dict[key.lower().strip()] = value.strip()
                
                print(f"DEBUG: Found {len(header_matches)} -H headers")
                
                # Extract -b cookie and convert to header format
                cookie_match = re.search(r"-b\s+'([^']+)'", headers_raw)
                if cookie_match:
                    headers_dict['cookie'] = cookie_match.group(1)
                    print(f"DEBUG: Found cookie from -b flag")
                
                # Build clean headers in format that ytmusicapi expects
                header_lines = []
                for key, value in headers_dict.items():
                    header_lines.append(f"{key}: {value}")
                
                headers_clean = '\n'.join(header_lines)
                
                print(f"DEBUG: Extracted headers: {list(headers_dict.keys())}")
                print(f"DEBUG: Has cookie: {'cookie' in headers_dict}")
                print(f"DEBUG: Has x-goog-authuser: {'x-goog-authuser' in headers_dict}")
                
                # Save headers to file first (same as CLI)
                session_key = request.args.get('as', 'source')
                auth_file = os.path.join(CONFIG_DIR, f'web_{session_key}.json')
                
                # Setup and save to file
                setup(filepath=auth_file, headers_raw=headers_clean)
                
                # Now load from file
                provider = YouTubeMusicProvider()
                success = provider.authenticate({'auth_file': auth_file})
                
                if success:
                    active_connections[session_key] = provider
                    flash(f'เชื่อมต่อ {platform} สำเร็จ!', 'success')
                    return redirect(url_for('transfer'))
                else:
                    flash('เชื่อมต่อไม่สำเร็จ กรุณาตรวจสอบ headers', 'error')
                    
            except Exception as e:
                flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return render_template('setup.html', platform=platform)


@app.route('/transfer')
def transfer():
    """Transfer page - show playlists and start transfer"""
    if not active_connections.get('source'):
        flash('กรุณาเชื่อมต่อบัญชีต้นทางก่อน', 'warning')
        return redirect(url_for('index'))
    
    if not active_connections.get('dest'):
        flash('กรุณาเชื่อมต่อบัญชีปลายทางก่อน', 'warning')
        return redirect(url_for('index'))
    
    try:
        source_provider = active_connections['source']
        playlists = source_provider.get_playlists(limit=50)
        return render_template('transfer.html', playlists=playlists)
    except Exception as e:
        flash(f'ไม่สามารถดึงเพลย์ลิสต์: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/api/playlists')
def api_get_playlists():
    """API: Get all playlists from source"""
    if not active_connections.get('source'):
        return jsonify({'error': 'Not connected', 'playlists': []}), 401
    
    try:
        provider = active_connections['source']
        playlists = provider.get_playlists(limit=50)
        return jsonify({
            'playlists': [
                {
                    'name': p.name,
                    'platform_id': p.platform_id,
                    'api_track_count': p.api_track_count
                }
                for p in playlists
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e), 'playlists': []}), 500


@app.route('/api/playlists/<playlist_id>/tracks')
def get_playlist_tracks(playlist_id):
    """API: Get tracks in a playlist"""
    if not active_connections.get('source'):
        return jsonify({'error': 'Not connected'}), 401
    
    try:
        provider = active_connections['source']
        tracks = provider.get_playlist_tracks(playlist_id, limit=1000)
        return jsonify({
            'tracks': [
                {
                    'title': t.title,
                    'artists': t.artists,
                    'album': t.album,
                    'duration_ms': t.duration_ms
                }
                for t in tracks
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/transfer', methods=['POST'])
def api_transfer():
    """API: Start transfer"""
    data = request.get_json()
    playlist_id = data.get('playlist_id')
    new_name = data.get('new_name')
    
    if not active_connections.get('source') or not active_connections.get('dest'):
        return jsonify({'error': 'Both source and destination must be connected'}), 400
    
    # TODO: Implement actual transfer with progress
    return jsonify({
        'status': 'started',
        'message': 'Transfer started',
        'playlist_id': playlist_id
    })


@app.route('/status')
def status():
    """Check connection status"""
    return jsonify({
        'source_connected': active_connections.get('source') is not None,
        'dest_connected': active_connections.get('dest') is not None,
        'source_platform': active_connections['source'].name if active_connections.get('source') else None,
        'dest_platform': active_connections['dest'].name if active_connections.get('dest') else None
    })


@app.route('/disconnect/<conn_type>')
def disconnect(conn_type):
    """Disconnect a connection"""
    if conn_type in active_connections:
        active_connections[conn_type] = None
        flash(f'ตัดการเชื่อมต่อ {conn_type} แล้ว', 'info')
    return redirect(url_for('index'))


# ============================================
# CSV Import/Export (Workaround for Spotify Free)
# ============================================

@app.route('/api/playlists/<playlist_id>/export/csv')
def export_playlist_csv(playlist_id):
    """Export playlist to CSV format"""
    import csv
    import io
    
    if not active_connections.get('source'):
        return jsonify({'error': 'Not connected'}), 401
    
    try:
        provider = active_connections['source']
        tracks = provider.get_playlist_tracks(playlist_id, limit=1000)
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Title', 'Artist', 'Album', 'Duration (ms)', 'Platform ID'])
        
        # Data
        for track in tracks:
            writer.writerow([
                track.title,
                ', '.join(track.artists) if track.artists else '',
                track.album or '',
                track.duration_ms or '',
                track.platform_id or ''
            ])
        
        output.seek(0)
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=playlist_{playlist_id}.csv'
        }
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/csv', methods=['POST'])
def import_csv_playlist():
    """Import playlist from CSV"""
    import csv
    import io
    
    if not active_connections.get('dest'):
        return jsonify({'error': 'Destination not connected'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    playlist_name = request.form.get('playlist_name', 'Imported Playlist')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Read CSV
        stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        reader = csv.DictReader(stream)
        
        from providers.base import Track
        
        tracks = []
        for row in reader:
            track = Track(
                title=row.get('Title', 'Unknown'),
                artists=[a.strip() for a in row.get('Artist', '').split(',')] if row.get('Artist') else ['Unknown'],
                album=row.get('Album'),
                duration_ms=int(row['Duration (ms)']) if row.get('Duration (ms)') else None
            )
            tracks.append(track)
        
        # Create playlist and add tracks
        dest_provider = active_connections['dest']
        playlist_id = dest_provider.create_playlist(playlist_name, description="Imported from CSV")
        
        if not playlist_id:
            return jsonify({'error': 'Failed to create playlist'}), 500
        
        success, failed = dest_provider.add_tracks_to_playlist(playlist_id, tracks)
        
        return jsonify({
            'status': 'success',
            'playlist_id': playlist_id,
            'playlist_name': playlist_name,
            'total_tracks': len(tracks),
            'success': success,
            'failed': failed
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/csv-transfer')
def csv_transfer_page():
    """Page for CSV-based transfer (no Spotify API needed)"""
    return render_template('csv_transfer.html')


@app.route('/callback/<platform>')
def oauth_callback(platform):
    """Handle OAuth callback from platforms"""
    if platform not in OAUTH_CONFIG:
        flash(f'แพลตฟอร์ม {platform} ไม่รองรับ OAuth', 'error')
        return redirect(url_for('index'))
    
    # Get authorization code
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        flash(f'OAuth Error: {error}', 'error')
        return redirect(url_for('index'))
    
    if not code:
        flash('ไม่ได้รับ authorization code', 'error')
        return redirect(url_for('index'))
    
    # Verify state
    stored_state = session.get('oauth_state')
    if not stored_state or state != stored_state:
        flash('Invalid state parameter (CSRF protection)', 'error')
        return redirect(url_for('index'))
    
    # Decode state to get connection type
    try:
        state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
        connection_type = state_data.get('connection_type', 'source')
    except:
        connection_type = 'source'
    
    config = OAUTH_CONFIG[platform]
    code_verifier = session.get('code_verifier')
    
    # Exchange code for tokens
    try:
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': config['redirect_uri'],
            'client_id': config['client_id'],
        }
        
        if platform == 'spotify':
            # Spotify uses Basic Auth for client credentials
            auth_string = base64.b64encode(
                f"{config['client_id']}:{config['client_secret']}".encode()
            ).decode()
            headers = {
                'Authorization': f'Basic {auth_string}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            token_data['code_verifier'] = code_verifier
        else:
            # YouTube/Google uses client_secret in body
            token_data['client_secret'] = config['client_secret']
            token_data['code_verifier'] = code_verifier
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        response = requests.post(config['token_url'], data=token_data, headers=headers)
        response.raise_for_status()
        tokens = response.json()
        
        # Store tokens in session
        if SESSION_CONNECTIONS_KEY not in session:
            session[SESSION_CONNECTIONS_KEY] = {}
        
        session[SESSION_CONNECTIONS_KEY][connection_type] = {
            'platform': platform,
            'access_token': tokens.get('access_token'),
            'refresh_token': tokens.get('refresh_token'),
            'expires_in': tokens.get('expires_in')
        }
        
        # Authenticate provider
        if platform == 'spotify':
            provider = SpotifyProvider()
            provider.authenticate({
                'access_token': tokens.get('access_token'),
                'refresh_token': tokens.get('refresh_token'),
                'client_id': config['client_id'],
                'client_secret': config['client_secret']
            })
            # Store in active connections
            from flask import g
            if not hasattr(g, 'active_connections'):
                g.active_connections = {}
            g.active_connections[connection_type] = provider
        
        flash(f'เชื่อมต่อ {platform} สำเร็จ!', 'success')
        return redirect(url_for('transfer'))
        
    except Exception as e:
        flash(f'OAuth ล้มเหลว: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/health')
def health():
    """Health check for Render"""
    return jsonify({'status': 'ok', 'service': 'kmusic-transfer'})


@app.route('/env-check')
def env_check():
    """Check environment variables (admin only)"""
    # Check if client IDs are configured
    spotify_ready = bool(OAUTH_CONFIG['spotify']['client_id'])
    youtube_ready = bool(OAUTH_CONFIG['youtube']['client_id'])
    
    return jsonify({
        'spotify_oauth_ready': spotify_ready,
        'youtube_oauth_ready': youtube_ready,
        'production': IS_PRODUCTION,
        'base_url': BASE_URL
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = not IS_PRODUCTION
    
    if debug:
        print(f"{Fore.CYAN}🎵 Music Transfer Web UI{Style.RESET_ALL}")
        print(f"{Fore.GREEN}เปิดที่: http://localhost:{port}{Style.RESET_ALL}")
    
    app.run(debug=debug, host='0.0.0.0', port=port)

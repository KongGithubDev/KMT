#!/usr/bin/env python3
"""
YouTube Music Playlist Transfer CLI
โอนเพลย์ลิสต์ระหว่างบัญชี YouTube Music
"""

import os
import json
import pickle
import click
from colorama import init, Fore, Style
from tqdm import tqdm
from dotenv import load_dotenv
from ytmusicapi import YTMusic, setup_oauth, setup

# Load environment variables from .env file
load_dotenv()

init(autoreset=True)

CONFIG_DIR = os.path.expanduser("~/.ytmusic_transfer")
OAUTH_FILE_SRC = os.path.join(CONFIG_DIR, "oauth_source.json")
OAUTH_FILE_DST = os.path.join(CONFIG_DIR, "oauth_dest.json")


def ensure_config_dir():
    """สร้างโฟลเดอร์ config ถ้ายังไม่มี"""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)


def get_ytmusic(oauth_file):
    """สร้าง YTMusic instance จากไฟล์ OAuth"""
    if not os.path.exists(oauth_file):
        return None
    try:
        return YTMusic(oauth_file)
    except Exception as e:
        click.echo(f"{Fore.RED}Error loading OAuth: {e}{Style.RESET_ALL}")
        return None


@click.group()
def cli():
    """🎵 YouTube Music Playlist Transfer Tool"""
    ensure_config_dir()




@cli.command(name='setup')
@click.option('--source', is_flag=True, help='Setup บัญชีต้นทาง (Source)')
@click.option('--dest', is_flag=True, help='Setup บัญชีปลายทาง (Destination)')
@click.option('--browser', is_flag=True, help='ใช้ Browser Headers (ง่าย ไม่ต้องสร้าง Google Cloud)')
@click.option('--oauth', is_flag=True, help='ใช้ OAuth (ต้องสร้าง Google Cloud Project)')
@click.option('--client-id', envvar='YTMUSIC_CLIENT_ID', help='Google OAuth Client ID (ใช้กับ --oauth)')
@click.option('--client-secret', envvar='YTMUSIC_CLIENT_SECRET', help='Google OAuth Client Secret (ใช้กับ --oauth)')
def setup_cmd(source, dest, browser, oauth, client_id, client_secret):
    """ตั้งค่าบัญชี YouTube Music (เลือกวิธี: --browser หรือ --oauth)"""
    if not source and not dest:
        click.echo(f"{Fore.YELLOW}กรุณาระบุ --source หรือ --dest{Style.RESET_ALL}")
        return

    if not browser and not oauth:
        # ถ้าไม่ระบุวิธี ให้ถาม
        click.echo(f"{Fore.CYAN}เลือกวิธีการตั้งค่า:{Style.RESET_ALL}")
        click.echo(f"  1) Browser Headers (ง่าย ไม่ต้องสร้าง Google Cloud)")
        click.echo(f"  2) OAuth (ยุ่งยาก แต่ทนทานกว่า)")
        choice = click.prompt("เลือก (1/2)", type=click.Choice(['1', '2']), default='1')
        browser = (choice == '1')
        oauth = (choice == '2')

    if browser:
        # Browser Headers method
        click.echo(f"{Fore.CYAN}=== วิธีการรับ Browser Headers (สำคัญ!) ==={Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}1. เปิด browser ไปที่ https://music.youtube.com และ login{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}2. กด F12 เปิด Developer Tools > แท็บ Network{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}3. ในช่อง Filter พิมพ์: {Fore.CYAN}music.youtube.com/youtubei{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}4. คลิกเล่นเพลง หรือ คลิกเข้าไปดู Playlist{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}5. หา request ที่ URL มี {Fore.CYAN}'/browse'{Style.RESET_ALL} หรือ {Fore.CYAN}'/next'{Style.RESET_ALL}")
        click.echo(f"   {Fore.GREEN}ตัวอย่าง URL ที่ถูกต้อง:{Style.RESET_ALL}")
        click.echo(f"   {Fore.GREEN}  https://music.youtube.com/youtubei/v1/browse?...{Style.RESET_ALL}")
        click.echo(f"   {Fore.RED}❌ ไม่เอา: jnn-pa.googleapis.com, googlevideo.com, หรืออื่นๆ{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}6. คลิก request นั้น > ดูแท็บ Headers ขวามือ{Style.RESET_ALL}")
        click.echo(f"   {Fore.GREEN}ต้องมี: Authorization, cookie, x-goog-authuser{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}7. คลิกขวาที่ request > Copy > Copy as cURL (bash){Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}8. กลับมา paste ทั้งหมดตรงนี้ แล้วกด Enter 2 ครั้ง:{Style.RESET_ALL}")
        click.echo()

        # รับ input หลายบรรทัด
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == '' and lines:
                    break
                lines.append(line)
            except EOFError:
                break

        headers_raw = '\n'.join(lines)

        # แปลงข้อมูล cURL เป็น Raw Headers ที่ ytmusicapi ต้องการ
        import re
        if 'curl ' in headers_raw or '-H ' in headers_raw or '-b ' in headers_raw:
            parsed_headers = []
            
            cookie_match = re.search(r"-b ['\"]([^'\"]+)['\"]", headers_raw)
            if cookie_match:
                parsed_headers.append(f"cookie: {cookie_match.group(1)}")
                
            for line in headers_raw.split('\n'):
                h_match = re.search(r"-H ['\"]([^:]+):\s*(.*?)['\"](?:[ \\])*$", line.strip())
                if h_match:
                    k = h_match.group(1).strip()
                    v = h_match.group(2).strip()
                    if k.lower() == 'cookie' and cookie_match:
                        continue
                    parsed_headers.append(f"{k}: {v}")
                    
            if parsed_headers:
                headers_raw = '\n'.join(parsed_headers)

        if not headers_raw.strip():
            click.echo(f"{Fore.RED}ไม่ได้รับข้อมูล กรุณาลองใหม่{Style.RESET_ALL}")
            return

        if source:
            click.echo(f"{Fore.CYAN}กำลัง setup บัญชีต้นทาง...{Style.RESET_ALL}")
            try:
                setup(filepath=OAUTH_FILE_SRC, headers_raw=headers_raw)
                click.echo(f"{Fore.GREEN}✓ บันทึก headers ต้นทางสำเร็จ{Style.RESET_ALL}")
            except Exception as e:
                click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

        if dest:
            click.echo(f"{Fore.CYAN}กำลัง setup บัญชีปลายทาง...{Style.RESET_ALL}")
            try:
                setup(filepath=OAUTH_FILE_DST, headers_raw=headers_raw)
                click.echo(f"{Fore.GREEN}✓ บันทึก headers ปลายทางสำเร็จ{Style.RESET_ALL}")
            except Exception as e:
                click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

    elif oauth:
        # OAuth method
        # Debug: แสดงค่าที่อ่านได้จาก environment
        import os
        env_client_id = os.environ.get('YTMUSIC_CLIENT_ID', '')
        env_client_secret = os.environ.get('YTMUSIC_CLIENT_SECRET', '')
        
        if not client_id and env_client_id:
            client_id = env_client_id
            click.echo(f"{Fore.CYAN}ℹ อ่าน Client ID จาก .env/environment{Style.RESET_ALL}")
        if not client_secret and env_client_secret:
            client_secret = env_client_secret
            click.echo(f"{Fore.CYAN}ℹ อ่าน Client Secret จาก .env/environment{Style.RESET_ALL}")
        
        if not client_id or not client_secret:
            click.echo(f"{Fore.YELLOW}ต้องระบุ --client-id และ --client-secret สำหรับ OAuth{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}วิธีใช้:{Style.RESET_ALL}")
            click.echo(f"  1) ใส่ใน .env file แล้วรัน: python ytmusic_transfer.py setup --source --oauth")
            click.echo(f"  2) หรือระบุตรงคำสั่ง (PowerShell):")
            click.echo(f"     --client-id $env:YTMUSIC_CLIENT_ID --client-secret $env:YTMUSIC_CLIENT_SECRET")
            click.echo(f"  3) หรือระบุตรงคำสั่ง (Command Prompt):")
            click.echo(f"     --client-id %YTMUSIC_CLIENT_ID% --client-secret %YTMUSIC_CLIENT_SECRET%")
            click.echo(f"{Fore.CYAN}สร้าง OAuth credentials ได้ที่: https://console.cloud.google.com/apis/credentials{Style.RESET_ALL}")
            return

        if source:
            click.echo(f"{Fore.CYAN}กำลัง setup บัญชีต้นทางด้วย OAuth...{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}เปิดเบราว์เซอร์เพื่อยืนยันตัวตน...{Style.RESET_ALL}")
            try:
                setup_oauth(client_id=client_id, client_secret=client_secret, filepath=OAUTH_FILE_SRC, open_browser=True)
                click.echo(f"{Fore.GREEN}✓ บันทึก OAuth ต้นทางสำเร็จ{Style.RESET_ALL}")
            except Exception as e:
                click.echo(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
                click.echo(f"\n{Fore.YELLOW}=== วิธีแก้ไขปัญหา OAuth ==={Style.RESET_ALL}")
                click.echo(f"{Fore.CYAN}1. เปิด YouTube Data API v3:{Style.RESET_ALL}")
                click.echo(f"   https://console.cloud.google.com/apis/library/youtube.googleapis.com")
                click.echo(f"{Fore.CYAN}2. ตรวจสอบ OAuth Consent Screen:{Style.RESET_ALL}")
                click.echo(f"   https://console.cloud.google.com/apis/credentials/consent")
                click.echo(f"   - ต้องเป็น 'Publishing status: Testing' หรือ 'In production'")
                click.echo(f"   - เพิ่มอีเมลของคุณใน 'Test users' ถ้าเป็น Testing")
                click.echo(f"{Fore.CYAN}3. ตรวจสอบ Redirect URIs:{Style.RESET_ALL}")
                click.echo(f"   https://console.cloud.google.com/apis/credentials")
                click.echo(f"   - ต้องมี: http://localhost:8080/oauth/callback")
                click.echo(f"{Fore.CYAN}4. ถ้าใช้ PowerShell ให้ลอง:{Style.RESET_ALL}")
                click.echo(f"   $env:YTMUSIC_CLIENT_ID = 'your-client-id'")
                click.echo(f"   $env:YTMUSIC_CLIENT_SECRET = 'your-secret'")
                click.echo(f"   python ytmusic_transfer.py setup --source --oauth")

        if dest:
            click.echo(f"{Fore.CYAN}กำลัง setup บัญชีปลายทางด้วย OAuth...{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}เปิดเบราว์เซอร์เพื่อยืนยันตัวตน...{Style.RESET_ALL}")
            try:
                setup_oauth(client_id=client_id, client_secret=client_secret, filepath=OAUTH_FILE_DST, open_browser=True)
                click.echo(f"{Fore.GREEN}✓ บันทึก OAuth ปลายทางสำเร็จ{Style.RESET_ALL}")
            except Exception as e:
                click.echo(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
                click.echo(f"\n{Fore.YELLOW}=== วิธีแก้ไขปัญหา OAuth ==={Style.RESET_ALL}")
                click.echo(f"{Fore.CYAN}1. เปิด YouTube Data API v3:{Style.RESET_ALL}")
                click.echo(f"   https://console.cloud.google.com/apis/library/youtube.googleapis.com")
                click.echo(f"{Fore.CYAN}2. ตรวจสอบ OAuth Consent Screen:{Style.RESET_ALL}")
                click.echo(f"   https://console.cloud.google.com/apis/credentials/consent")
                click.echo(f"   - ต้องเป็น 'Publishing status: Testing' หรือ 'In production'")
                click.echo(f"   - เพิ่มอีเมลของคุณใน 'Test users' ถ้าเป็น Testing")
                click.echo(f"{Fore.CYAN}3. ตรวจสอบ Redirect URIs:{Style.RESET_ALL}")
                click.echo(f"   https://console.cloud.google.com/apis/credentials")
                click.echo(f"   - ต้องมี: http://localhost:8080/oauth/callback")


@cli.command()
def list_accounts():
    """แสดงสถานะบัญชีที่ setup ไว้"""
    click.echo(f"{Fore.CYAN}=== สถานะบัญชี ==={Style.RESET_ALL}")
    
    if os.path.exists(OAUTH_FILE_SRC):
        click.echo(f"{Fore.GREEN}✓ บัญชีต้นทาง (Source): {OAUTH_FILE_SRC}{Style.RESET_ALL}")
        try:
            ytm = YTMusic(OAUTH_FILE_SRC)
            library = ytm.get_library_playlists(limit=1)
            click.echo(f"  สามารถเชื่อมต่อได้ ({len(library)} playlists)")
        except:
            click.echo(f"  {Fore.RED}⚠ ไฟล์ OAuth อาจหมดอายุ{Style.RESET_ALL}")
    else:
        click.echo(f"{Fore.RED}✗ บัญชีต้นทาง: ยังไม่ได้ setup{Style.RESET_ALL}")
    
    if os.path.exists(OAUTH_FILE_DST):
        click.echo(f"{Fore.GREEN}✓ บัญชีปลายทาง (Dest): {OAUTH_FILE_DST}{Style.RESET_ALL}")
        try:
            ytm = YTMusic(OAUTH_FILE_DST)
            library = ytm.get_library_playlists(limit=1)
            click.echo(f"  สามารถเชื่อมต่อได้ ({len(library)} playlists)")
        except:
            click.echo(f"  {Fore.RED}⚠ ไฟล์ OAuth อาจหมดอายุ{Style.RESET_ALL}")
    else:
        click.echo(f"{Fore.RED}✗ บัญชีปลายทาง: ยังไม่ได้ setup{Style.RESET_ALL}")


@cli.command()
@click.option('--source', 'source_account', is_flag=True, help='ใช้บัญชีต้นทาง')
@click.option('--dest', 'dest_account', is_flag=True, help='ใช้บัญชีปลายทาง')
def list_playlists(source_account, dest_account):
    """แสดงรายการเพลย์ลิสต์"""
    oauth_file = None
    account_name = ""
    
    if source_account:
        oauth_file = OAUTH_FILE_SRC
        account_name = "ต้นทาง"
    elif dest_account:
        oauth_file = OAUTH_FILE_DST
        account_name = "ปลายทาง"
    else:
        click.echo(f"{Fore.YELLOW}กรุณาระบุ --source หรือ --dest{Style.RESET_ALL}")
        return
    
    ytm = get_ytmusic(oauth_file)
    if not ytm:
        click.echo(f"{Fore.RED}ไม่สามารถเชื่อมต่อบัญชี {account_name} ได้ กรุณา setup ก่อน{Style.RESET_ALL}")
        return
    
    click.echo(f"{Fore.CYAN}=== เพลย์ลิสต์บัญชี {account_name} ==={Style.RESET_ALL}")
    
    playlists = ytm.get_library_playlists(limit=100)
    
    for i, pl in enumerate(playlists, 1):
        title = pl['title']
        count = pl.get('count', 'N/A')
        pl_id = pl['playlistId']
        print(f"{i}. {title} ({count} เพลง) - ID: {pl_id}")


@cli.command()
@click.argument('playlist_id')
@click.option('--source', 'source_account', is_flag=True, help='ดูจากบัญชีต้นทาง')
@click.option('--dest', 'dest_account', is_flag=True, help='ดูจากบัญชีปลายทาง')
def view_playlist(playlist_id, source_account, dest_account):
    """แสดงรายละเอียดเพลย์ลิสต์"""
    oauth_file = OAUTH_FILE_SRC if source_account else OAUTH_FILE_DST if dest_account else OAUTH_FILE_SRC
    
    ytm = get_ytmusic(oauth_file)
    if not ytm:
        click.echo(f"{Fore.RED}ไม่สามารถเชื่อมต่อได้ กรุณา setup ก่อน{Style.RESET_ALL}")
        return
    
    try:
        playlist = ytm.get_playlist(playlist_id, limit=1000)
        click.echo(f"{Fore.CYAN}=== {playlist['title']} ==={Style.RESET_ALL}")
        click.echo(f"เจ้าของ: {playlist.get('author', 'N/A')}")
        click.echo(f"จำนวนเพลง: {playlist.get('trackCount', len(playlist['tracks']))}")
        click.echo(f"{Fore.YELLOW}--- รายการเพลง ---{Style.RESET_ALL}")
        
        for i, track in enumerate(playlist['tracks'][:50], 1):
            title = track['title']
            artist = ', '.join([a['name'] for a in track['artists']])
            print(f"{i}. {title} - {artist}")
        
        if len(playlist['tracks']) > 50:
            print(f"... และอีก {len(playlist['tracks']) - 50} เพลง")
    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")


@cli.command()
@click.argument('source_playlist_id')
@click.option('--new-name', help='ชื่อใหม่สำหรับเพลย์ลิสต์ (ถ้าไม่ระบุจะใช้ชื่อเดิม)')
@click.option('--privacy', default='PRIVATE', type=click.Choice(['PUBLIC', 'PRIVATE', 'UNLISTED']),
              help='การตั้งค่าความเป็นส่วนตัว')
def transfer(source_playlist_id, new_name, privacy):
    """โอนเพลย์ลิสต์จากบัญชีต้นทางไปยังบัญชีปลายทาง"""
    
    # Connect to source
    ytm_src = get_ytmusic(OAUTH_FILE_SRC)
    if not ytm_src:
        click.echo(f"{Fore.RED}ไม่สามารถเชื่อมต่อบัญชีต้นทางได้ กรุณา setup --source ก่อน{Style.RESET_ALL}")
        return
    
    # Connect to destination
    ytm_dst = get_ytmusic(OAUTH_FILE_DST)
    if not ytm_dst:
        click.echo(f"{Fore.RED}ไม่สามารถเชื่อมต่อบัญชีปลายทางได้ กรุณา setup --dest ก่อน{Style.RESET_ALL}")
        return
    
    # Get source playlist
    click.echo(f"{Fore.CYAN}กำลังอ่านเพลย์ลิสต์ต้นทาง...{Style.RESET_ALL}")
    try:
        source_playlist = ytm_src.get_playlist(source_playlist_id, limit=10000)
    except Exception as e:
        click.echo(f"{Fore.RED}ไม่สามารถอ่านเพลย์ลิสต์ได้: {e}{Style.RESET_ALL}")
        return
    
    playlist_name = new_name or source_playlist['title']
    tracks = source_playlist['tracks']
    
    click.echo(f"{Fore.GREEN}พบเพลย์ลิสต์: {source_playlist['title']} ({len(tracks)} เพลง){Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}จะสร้างเพลย์ลิสต์ '{playlist_name}' ในบัญชีปลายทาง{Style.RESET_ALL}")
    
    # Create playlist on destination
    try:
        click.echo(f"{Fore.YELLOW}กำลังสร้างเพลย์ลิสต์ใหม่...{Style.RESET_ALL}")
        new_playlist_id = ytm_dst.create_playlist(
            title=playlist_name,
            description=f"Transferred from YouTube Music - {source_playlist.get('title', '')}",
            privacy_status=privacy
        )
        click.echo(f"{Fore.GREEN}✓ สร้างเพลย์ลิสต์สำเร็จ: {new_playlist_id}{Style.RESET_ALL}")
    except Exception as e:
        click.echo(f"{Fore.RED}ไม่สามารถสร้างเพลย์ลิสต์ได้: {e}{Style.RESET_ALL}")
        return
    
    # Transfer tracks
    click.echo(f"{Fore.CYAN}กำลังโอนเพลง...{Style.RESET_ALL}")
    
    success_count = 0
    failed_tracks = []
    
    for track in tqdm(tracks, desc="โอนเพลง"):
        try:
            # Search for track in destination
            search_query = f"{track['title']} {' '.join([a['name'] for a in track['artists']])}"
            search_results = ytm_dst.search(search_query, filter="songs", limit=1)
            
            if search_results:
                video_id = search_results[0]['videoId']
                ytm_dst.add_playlist_items(new_playlist_id, [video_id])
                success_count += 1
            else:
                failed_tracks.append(f"{track['title']} - {', '.join([a['name'] for a in track['artists']])}")
        except Exception as e:
            failed_tracks.append(f"{track['title']} - {', '.join([a['name'] for a in track['artists']])}")
    
    # Summary
    click.echo(f"\n{Fore.GREEN}=== สรุปผลการโอน ==={Style.RESET_ALL}")
    click.echo(f"เพลงทั้งหมด: {len(tracks)}")
    click.echo(f"สำเร็จ: {success_count}")
    click.echo(f"ไม่สำเร็จ: {len(failed_tracks)}")
    
    if failed_tracks:
        click.echo(f"\n{Fore.YELLOW}เพลงที่โอนไม่สำเร็จ:{Style.RESET_ALL}")
        for track in failed_tracks[:10]:
            click.echo(f"  - {track}")
        if len(failed_tracks) > 10:
            click.echo(f"  ... และอีก {len(failed_tracks) - 10} เพลง")


@cli.command()
@click.option('--all', 'transfer_all', is_flag=True, help='โอนทุกเพลย์ลิสต์')
@click.option('--privacy', default='PRIVATE', type=click.Choice(['PUBLIC', 'PRIVATE', 'UNLISTED']))
def transfer_all_playlists(transfer_all, privacy):
    """โอนทุกเพลย์ลิสต์จากบัญชีต้นทางไปยังบัญชีปลายทาง"""
    
    if not transfer_all:
        click.echo(f"{Fore.YELLOW}ใช้ --all เพื่อโอนทุกเพลย์ลิสต์{Style.RESET_ALL}")
        return
    
    # Connect
    ytm_src = get_ytmusic(OAUTH_FILE_SRC)
    ytm_dst = get_ytmusic(OAUTH_FILE_DST)
    
    if not ytm_src or not ytm_dst:
        click.echo(f"{Fore.RED}กรุณา setup ทั้งสองบัญชีก่อน{Style.RESET_ALL}")
        return
    
    # Get all playlists
    click.echo(f"{Fore.CYAN}กำลังดึงรายการเพลย์ลิสต์...{Style.RESET_ALL}")
    playlists = ytm_src.get_library_playlists(limit=100)
    
    click.echo(f"{Fore.GREEN}พบ {len(playlists)} เพลย์ลิสต์{Style.RESET_ALL}")
    
    for pl in playlists:
        pl_id = pl['playlistId']
        pl_name = pl['title']
        
        # Skip liked songs and system playlists if needed
        if pl_id in ['LM', 'SE']:
            continue
            
        click.echo(f"\n{Fore.CYAN}กำลังโอน: {pl_name}{Style.RESET_ALL}")
        
        # Call transfer logic
        ctx = click.get_current_context()
        ctx.invoke(transfer, source_playlist_id=pl_id, new_name=None, privacy=privacy)


@cli.command()
def transfer_liked_songs():
    """โอนเพลงที่กดถูกใจ (Liked Songs)"""
    ytm_src = get_ytmusic(OAUTH_FILE_SRC)
    ytm_dst = get_ytmusic(OAUTH_FILE_DST)
    if not ytm_src or not ytm_dst:
        click.echo(f"{Fore.RED}กรุณา setup ทั้งสองบัญชีก่อน{Style.RESET_ALL}")
        return
    
    click.echo(f"{Fore.CYAN}กำลังดึงรายการเพลงที่กดถูกใจ (อาจใช้เวลาสักครู่)...{Style.RESET_ALL}")
    liked = ytm_src.get_liked_songs(limit=10000)
    tracks = liked.get('tracks', [])
    click.echo(f"{Fore.GREEN}พบเพลงที่ถูกใจทั้งหมด {len(tracks)} เพลง{Style.RESET_ALL}")
    
    success_count = 0
    for track in tqdm(tracks, desc="โอนเพลง"):
        try:
            ytm_dst.rate_song(track['videoId'], 'LIKE')
            success_count += 1
        except Exception as e:
            pass
            
    click.echo(f"{Fore.GREEN}✓ โอนสำเร็จ {success_count}/{len(tracks)} เพลง{Style.RESET_ALL}")


@cli.command()
def transfer_saved_albums():
    """โอนอัลบั้มที่บันทึกไว้ (Saved Albums)"""
    ytm_src = get_ytmusic(OAUTH_FILE_SRC)
    ytm_dst = get_ytmusic(OAUTH_FILE_DST)
    if not ytm_src or not ytm_dst:
        click.echo(f"{Fore.RED}กรุณา setup ทั้งสองบัญชีก่อน{Style.RESET_ALL}")
        return
        
    click.echo(f"{Fore.CYAN}กำลังดึงรายการอัลบั้ม...{Style.RESET_ALL}")
    albums = ytm_src.get_library_albums(limit=10000)
    click.echo(f"{Fore.GREEN}พบอัลบั้มทั้งหมด {len(albums)} อัลบั้ม{Style.RESET_ALL}")
    
    success_count = 0
    for album in tqdm(albums, desc="โอนอัลบั้ม"):
        try:
            pl_id = album.get('playlistId')
            if pl_id:
                ytm_dst.rate_playlist(pl_id, 'LIKE')
                success_count += 1
        except Exception as e:
            pass
            
    click.echo(f"{Fore.GREEN}✓ โอนสำเร็จ {success_count}/{len(albums)} อัลบั้ม{Style.RESET_ALL}")


@cli.command()
def transfer_subscriptions():
    """โอนรายชื่อศิลปินที่ติดตาม (Subscriptions)"""
    ytm_src = get_ytmusic(OAUTH_FILE_SRC)
    ytm_dst = get_ytmusic(OAUTH_FILE_DST)
    if not ytm_src or not ytm_dst:
        click.echo(f"{Fore.RED}กรุณา setup ทั้งสองบัญชีก่อน{Style.RESET_ALL}")
        return
        
    click.echo(f"{Fore.CYAN}กำลังดึงรายชื่อศิลปินที่ติดตาม...{Style.RESET_ALL}")
    subs = ytm_src.get_library_subscriptions(limit=10000)
    click.echo(f"{Fore.GREEN}พบศิลปินทั้งหมด {len(subs)} คน{Style.RESET_ALL}")
    
    channel_ids = [sub['browseId'] for sub in subs if 'browseId' in sub]
    
    if channel_ids:
        click.echo(f"{Fore.YELLOW}กำลังกดติดตามศิลปิน {len(channel_ids)} คน...{Style.RESET_ALL}")
        success = 0
        failed = 0
        for channel_id in tqdm(channel_ids, desc="กดติดตาม"):
            try:
                ytm_dst.subscribe_artists([channel_id])
                success += 1
            except Exception as e:
                failed += 1
        click.echo(f"{Fore.GREEN}✓ กดติดตามสำเร็จ {success}/{len(channel_ids)} ศิลปิน{Style.RESET_ALL}")
        if failed > 0:
            click.echo(f"{Fore.YELLOW}⚠ ไม่สำเร็จ {failed} คน{Style.RESET_ALL}")


if __name__ == '__main__':
    cli()

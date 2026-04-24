#!/usr/bin/env python3
"""
K(MT) Music Transfer - Duplicate Playlist Remover
ตรวจสอบและลบเพลย์ลิสต์ที่มีชื่อซ้ำกัน

Usage:
    python remove_duplicate_playlists.py --platform youtube --keep first --curl "curl command"
    python remove_duplicate_playlists.py --platform youtube --keep last --curl "curl command"
    python remove_duplicate_playlists.py --platform youtube --dry-run --curl "curl command"
"""

import argparse
import re
import sys
from collections import defaultdict
from typing import List, Dict, Any, Optional

# Import providers
from providers.youtube_provider import YouTubeMusicProvider


def parse_curl_command(curl_command: str) -> str:
    """
    Parse cURL command and extract headers in the format ytmusicapi expects.
    
    Args:
        curl_command: Raw cURL command from browser
        
    Returns:
        Clean headers string for ytmusicapi
    """
    headers_dict = {}
    
    # Extract -H headers (format: -H 'key: value' or -H "key: value")
    # Use lazy matching to handle values with quotes inside
    header_pattern = r"-H\s+['\"]([^:]+):(.*?)['\"](?=\s|$|\\)"
    header_matches = re.findall(header_pattern, curl_command, re.MULTILINE | re.DOTALL)
    for key, value in header_matches:
        headers_dict[key.lower().strip()] = value.strip()
    
    # Extract -b cookie 
    cookie_pattern = r"-b\s+['\"](.+?)['\"](?=\s|$|\\)"
    cookie_match = re.search(cookie_pattern, curl_command, re.MULTILINE | re.DOTALL)
    if cookie_match:
        headers_dict['cookie'] = cookie_match.group(1)
    
    # Build clean headers in format that ytmusicapi expects
    header_lines = []
    for key, value in headers_dict.items():
        header_lines.append(f"{key}: {value}")
    
    result = '\n'.join(header_lines)
    if not result.strip():
        raise ValueError("Could not parse any headers from cURL command")
    
    return result


def get_provider(platform: str):
    """Get provider instance for the specified platform."""
    if platform == 'youtube':
        return YouTubeMusicProvider()
    else:
        raise ValueError(f"Platform {platform} ยังไม่รองรับ")


def find_duplicate_playlists(playlists: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    หาเพลย์ลิสต์ที่มีชื่อซ้ำกัน
    
    Returns:
        Dict mapping playlist name to list of playlists with that name
    """
    name_groups = defaultdict(list)
    
    for playlist in playlists:
        name = playlist.get('name', '').strip()
        if name:
            name_groups[name].append(playlist)
    
    # คืนค่าเฉพาะกลุ่มที่มีมากกว่า 1 เพลย์ลิสต์
    return {name: group for name, group in name_groups.items() if len(group) > 1}


def remove_duplicate_playlists(
    provider,
    duplicates: Dict[str, List[Dict[str, Any]]],
    keep_strategy: str = 'first',
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    ลบเพลย์ลิสต์ที่ซ้ำกัน
    
    Args:
        provider: Provider instance
        duplicates: Dictionary of duplicate playlists by name
        keep_strategy: 'first' เก็บอันแรก, 'last' เก็บอันล่าสุด
        dry_run: ถ้า True จะไม่ลบจริง แค่แสดงรายการ
    
    Returns:
        Statistics about removed playlists
    """
    stats = {
        'total_duplicates': 0,
        'removed': 0,
        'kept': 0,
        'errors': []
    }
    
    for name, playlists in duplicates.items():
        print(f"\n[Playlist] '{name}'")
        print(f"   Found {len(playlists)} duplicates")
        
        stats['total_duplicates'] += len(playlists)
        
        # เรียงตามวันที่สร้าง (ถ้ามี)
        sorted_playlists = sorted(
            playlists,
            key=lambda x: x.get('created_at', '') or x.get('id', '')
        )
        
        # เลือกว่าจะเก็บอันไหน
        if keep_strategy == 'first':
            keep_index = 0
            to_remove = sorted_playlists[1:]
        else:  # 'last'
            keep_index = len(sorted_playlists) - 1
            to_remove = sorted_playlists[:-1]
        
        kept = sorted_playlists[keep_index]
        print(f"   [KEEP] ID={kept.get('id')} (created: {kept.get('created_at', 'N/A')})")
        stats['kept'] += 1
        
        # ลบที่เหลือ
        for playlist in to_remove:
            playlist_id = playlist.get('id')
            print(f"   Removed: ID={playlist_id}")
            
            if not dry_run:
                try:
                    success = provider.delete_playlist(playlist_id)
                    if success:
                        stats['removed'] += 1
                        print(f"      [OK] Deleted successfully")
                    else:
                        stats['errors'].append(f"Cannot delete {playlist_id}")
                        print(f"      [FAIL] Delete failed")
                except Exception as e:
                    stats['errors'].append(f"Error deleting {playlist_id}: {str(e)}")
                    print(f"      [ERROR] {str(e)}")
            else:
                stats['removed'] += 1
                print(f"      [Dry run - not actually deleted]")
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='K(MT) Music Transfer - ลบเพลย์ลิสต์ที่มีชื่อซ้ำกัน'
    )
    parser.add_argument(
        '--platform', '-p',
        choices=['youtube'],
        default='youtube',
        help='แพลตฟอร์มที่ต้องการตรวจสอบ (default: youtube)'
    )
    parser.add_argument(
        '--keep', '-k',
        choices=['first', 'last'],
        default='first',
        help='เก็บเพลย์ลิสต์อันแรกหรืออันล่าสุด (default: first)'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='แสดงรายการที่จะลบโดยไม่ลบจริง'
    )
    parser.add_argument(
        '--auth-file', '-a',
        type=str,
        help='Path to authentication file (optional)'
    )
    parser.add_argument(
        '--curl', '-c',
        type=str,
        help='cURL command from browser (for authentication)'
    )
    parser.add_argument(
        '--curl-file', '-cf',
        type=str,
        help='Path to file containing cURL command (easier for PowerShell)'
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive mode: paste cURL and press Enter twice to confirm'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    has_auth = args.auth_file or args.curl or args.curl_file or args.interactive
    if not has_auth:
        # Default to interactive mode if no auth method specified
        args.interactive = True
    
    print("=" * 60)
    print("K(MT) Music Transfer - Duplicate Playlist Remover")
    print("=" * 60)
    print(f"Platform: {args.platform}")
    print(f"Keep strategy: {args.keep}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 60)
    
    try:
        # Initialize provider
        provider = get_provider(args.platform)
        
        # Prepare authentication
        auth_config = {}
        if args.auth_file:
            auth_config['auth_file'] = args.auth_file
        elif args.curl:
            headers_raw = parse_curl_command(args.curl)
            auth_config['headers_raw'] = headers_raw
        elif args.curl_file:
            with open(args.curl_file, 'r', encoding='utf-8') as f:
                curl_command = f.read()
            headers_raw = parse_curl_command(curl_command)
            auth_config['headers_raw'] = headers_raw
        elif args.interactive:
            # Interactive mode: prompt for cURL with double Enter confirmation
            print("\n[Interactive Mode]")
            print("Paste your cURL command from browser (Copy as cURL), then press Enter twice to confirm:")
            print("-" * 60)
            
            lines = []
            empty_count = 0
            while empty_count < 2:
                try:
                    line = input()
                    if line.strip() == '':
                        empty_count += 1
                    else:
                        empty_count = 0
                        lines.append(line)
                except EOFError:
                    break
            
            curl_command = '\n'.join(lines)
            if not curl_command.strip():
                print("[FAILED] No cURL command provided")
                sys.exit(1)
            
            print("-" * 60)
            print("[OK] cURL command received")
            headers_raw = parse_curl_command(curl_command)
            auth_config['headers_raw'] = headers_raw
        
        print("\n[Connecting...]")
        if not provider.authenticate(auth_config):
            print("[FAILED] Authentication failed")
            sys.exit(1)
        
        print("[OK] Connected successfully")
        
        # Get all playlists
        print("\n[Fetching playlists...]")
        playlists = provider.get_playlists()
        print(f"   Total playlists: {len(playlists)}")
        
        # Find duplicates
        print("\n[Checking for duplicates...]")
        duplicates = find_duplicate_playlists(playlists)
        
        if not duplicates:
            print("[OK] No duplicate playlists found")
            sys.exit(0)
        
        print(f"[FOUND] {len(duplicates)} groups with duplicate names")
        
        # Remove duplicates
        stats = remove_duplicate_playlists(
            provider,
            duplicates,
            keep_strategy=args.keep,
            dry_run=args.dry_run
        )
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"   Duplicate groups: {len(duplicates)}")
        print(f"   Total duplicates: {stats['total_duplicates']}")
        print(f"   Kept: {stats['kept']}")
        print(f"   Removed: {stats['removed']}")
        
        if stats['errors']:
            print(f"   Errors: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"      - {error}")
        
        if args.dry_run:
            print("\n[NOTE] This was a dry run. No actual deletions occurred.")
            print("   Run without --dry-run to delete for real.")
        
        print("\n[DONE]")
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
K(MT) Music Transfer - Duplicate Playlist Remover
ตรวจสอบและลบเพลย์ลิสต์ที่มีชื่อซ้ำกัน

Usage:
    python remove_duplicate_playlists.py --platform youtube --keep first
    python remove_duplicate_playlists.py --platform youtube --keep last
    python remove_duplicate_playlists.py --platform youtube --dry-run
"""

import argparse
import sys
from collections import defaultdict
from typing import List, Dict, Any, Optional

# Import providers
from providers.youtube_provider import YouTubeMusicProvider
from utils.config_manager import ConfigManager


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
        print(f"\n🎵 เพลย์ลิสต์: '{name}'")
        print(f"   พบ {len(playlists)} รายการซ้ำ")
        
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
        print(f"   ✅ เก็บ: ID={kept.get('id')} (created: {kept.get('created_at', 'N/A')})")
        stats['kept'] += 1
        
        # ลบที่เหลือ
        for playlist in to_remove:
            playlist_id = playlist.get('id')
            print(f"   🗑️  ลบ: ID={playlist_id}")
            
            if not dry_run:
                try:
                    success = provider.delete_playlist(playlist_id)
                    if success:
                        stats['removed'] += 1
                        print(f"      ✓ ลบสำเร็จ")
                    else:
                        stats['errors'].append(f"ไม่สามารถลบ {playlist_id}")
                        print(f"      ✗ ลบไม่สำเร็จ")
                except Exception as e:
                    stats['errors'].append(f"Error deleting {playlist_id}: {str(e)}")
                    print(f"      ✗ Error: {str(e)}")
            else:
                stats['removed'] += 1
                print(f"      [Dry run - ไม่ได้ลบจริง]")
    
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
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎵 K(MT) Music Transfer - Duplicate Playlist Remover")
    print("=" * 60)
    print(f"📱 Platform: {args.platform}")
    print(f"🔧 Keep strategy: {args.keep}")
    print(f"🧪 Dry run: {args.dry_run}")
    print("=" * 60)
    
    try:
        # Initialize provider
        provider = get_provider(args.platform)
        
        # Authenticate
        auth_config = {}
        if args.auth_file:
            auth_config['auth_file'] = args.auth_file
        
        print("\n🔐 กำลังเชื่อมต่อ...")
        if not provider.authenticate(auth_config):
            print("❌ เชื่อมต่อไม่สำเร็จ")
            sys.exit(1)
        
        print("✅ เชื่อมต่อสำเร็จ")
        
        # Get all playlists
        print("\n📋 กำลังดึงรายการเพลย์ลิสต์...")
        playlists = provider.get_playlists()
        print(f"   พบทั้งหมด {len(playlists)} เพลย์ลิสต์")
        
        # Find duplicates
        print("\n🔍 กำลังตรวจหาเพลย์ลิสต์ที่ซ้ำกัน...")
        duplicates = find_duplicate_playlists(playlists)
        
        if not duplicates:
            print("✅ ไม่พบเพลย์ลิสต์ที่ซ้ำกัน")
            sys.exit(0)
        
        print(f"⚠️ พบ {len(duplicates)} กลุ่มที่มีชื่อซ้ำกัน")
        
        # Remove duplicates
        stats = remove_duplicate_playlists(
            provider,
            duplicates,
            keep_strategy=args.keep,
            dry_run=args.dry_run
        )
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 สรุปผล")
        print("=" * 60)
        print(f"   จำนวนกลุ่มที่ซ้ำ: {len(duplicates)}")
        print(f"   เพลย์ลิสต์ที่ซ้ำทั้งหมด: {stats['total_duplicates']}")
        print(f"   เก็บไว้: {stats['kept']}")
        print(f"   ลบออก: {stats['removed']}")
        
        if stats['errors']:
            print(f"   ⚠️ ข้อผิดพลาด: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"      - {error}")
        
        if args.dry_run:
            print("\n📝 นี่เป็นการทดสอบ (dry run) ไม่มีการลบจริง")
            print("   รันคำสั่งอีกครั้งโดยไม่ใส่ --dry-run เพื่อลบจริง")
        
        print("\n✅ เสร็จสิ้น")
        
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาด: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

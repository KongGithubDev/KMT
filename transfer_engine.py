"""
Transfer Engine - จัดการการโอนเพลงระหว่างแพลตฟอร์ม
"""

from typing import List, Optional, Callable
from dataclasses import dataclass
from fuzzywuzzy import fuzz

from providers.base import BaseProvider, Track, Playlist


@dataclass
class TransferResult:
    """ผลการโอน"""
    success_count: int
    failed_count: int
    not_found: List[Track]
    matched_tracks: List[tuple[Track, Track]]  # (source_track, dest_track)


class TransferEngine:
    """
    Engine สำหรับโอนเพลงระหว่างแพลตฟอร์ม
    
    รองรับ:
    - Same-platform transfer (YT→YT, Spotify→Spotify)
    - Cross-platform transfer (YT→Spotify, etc.)
    - Smart track matching ด้วย fuzzy search
    """
    
    def __init__(self, source: BaseProvider, dest: BaseProvider):
        self.source = source
        self.dest = dest
    
    def match_track(self, track: Track, candidates: List[Track], 
                   threshold: int = 80) -> Optional[Track]:
        """
        จับคู่เพลงจาก source กับ candidates จาก dest platform
        
        ใช้ fuzzy matching เปรียบเทียบ:
        - ชื่อเพลง (60% weight)
        - ชื่อศิลปิน (40% weight)
        
        Args:
            track: เพลงต้นทาง
            candidates: รายการเพลงจากแพลตฟอร์มปลายทาง
            threshold: คะแนนขั้นต่ำที่ถือว่าตรงกัน (0-100)
        
        Returns:
            Track ที่ตรงกันที่สุด หรือ None ถ้าไม่มีที่ตรง
        """
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            # Compare title
            title_score = fuzz.ratio(
                track.title.lower(), 
                candidate.title.lower()
            )
            
            # Compare artists (ใช้ artist คนแรก)
            source_artist = track.artists[0].lower() if track.artists else ""
            dest_artist = candidate.artists[0].lower() if candidate.artists else ""
            artist_score = fuzz.ratio(source_artist, dest_artist)
            
            # Weighted average
            total_score = (title_score * 0.6) + (artist_score * 0.4)
            
            if total_score > best_score and total_score >= threshold:
                best_score = total_score
                best_match = candidate
        
        return best_match
    
    def transfer_playlist(self, source_playlist_id: str, 
                         new_name: Optional[str] = None,
                         progress_callback: Optional[Callable] = None) -> TransferResult:
        """
        โอนเพลย์ลิสต์จาก source ไป dest
        
        Args:
            source_playlist_id: ID เพลย์ลิสต์ต้นทาง
            new_name: ชื่อใหม่ (ถ้าไม่ระบุใช้ชื่อเดิม)
            progress_callback: ฟังก์ชัน callback(progress, total)
        
        Returns:
            TransferResult
        """
        # 1. ดึงข้อมูลเพลย์ลิสต์ต้นทาง
        source_tracks = self.source.get_playlist_tracks(source_playlist_id)
        source_playlists = self.source.get_playlists()
        source_playlist = next(
            (p for p in source_playlists if p.platform_id == source_playlist_id),
            None
        )
        
        playlist_name = new_name or (source_playlist.name if source_playlist else "Transferred Playlist")
        
        # 2. สร้างเพลย์ลิสต์ใหม่บน dest
        dest_playlist_id = self.dest.create_playlist(
            name=playlist_name,
            description=f"Transferred from {self.source.display_name}",
            is_public=False
        )
        
        if not dest_playlist_id:
            return TransferResult(0, len(source_tracks), source_tracks, [])
        
        # 3. โอนแต่ละเพลง
        success_count = 0
        failed_count = 0
        not_found = []
        matched = []
        
        for i, track in enumerate(source_tracks):
            try:
                # Search on destination platform
                candidates = self.dest.search_track(track.search_query(), limit=5)
                
                if not candidates:
                    not_found.append(track)
                    failed_count += 1
                    continue
                
                # Match best candidate
                best_match = self.match_track(track, candidates)
                
                if best_match:
                    # Add to playlist
                    self.dest.add_tracks_to_playlist(dest_playlist_id, [best_match])
                    matched.append((track, best_match))
                    success_count += 1
                else:
                    not_found.append(track)
                    failed_count += 1
                
                # Report progress
                if progress_callback:
                    progress_callback(i + 1, len(source_tracks))
                    
            except Exception as e:
                not_found.append(track)
                failed_count += 1
        
        return TransferResult(success_count, failed_count, not_found, matched)
    
    def transfer_liked_songs(self, limit: int = 1000,
                            progress_callback: Optional[Callable] = None) -> TransferResult:
        """
        โอนเพลงที่ถูกใจจาก source ไป dest
        
        สำหรับ YouTube Music → ใช้ rate_song
        สำหรับแพลตฟอร์มอื่น → เพิ่มเข้า playlist "Liked Songs"
        """
        # ดึง liked songs จาก source
        liked_tracks = self.source.get_liked_tracks(limit=limit)
        
        success_count = 0
        failed_count = 0
        
        for i, track in enumerate(liked_tracks):
            try:
                # สำหรับ YouTube Music dest ใช้ rate_song
                if hasattr(self.dest, 'like_track') and track.platform_id:
                    if self.dest.like_track(track.platform_id):
                        success_count += 1
                    else:
                        failed_count += 1
                else:
                    # สำหรับแพลตฟอร์มอื่น ค้นหาแล้ว like
                    candidates = self.dest.search_track(track.search_query(), limit=1)
                    if candidates and hasattr(self.dest, 'like_track'):
                        # Note: This requires the dest track to have platform_id
                        if self.dest.like_track(candidates[0].platform_id):
                            success_count += 1
                        else:
                            failed_count += 1
                    else:
                        failed_count += 1
                
                if progress_callback:
                    progress_callback(i + 1, len(liked_tracks))
                    
            except Exception:
                failed_count += 1
        
        return TransferResult(success_count, failed_count, [], [])
    
    def compare_playlists(self, playlist_id_1: str, 
                         playlist_id_2: str) -> dict:
        """
        เปรียบเทียบเพลงใน 2 เพลย์ลิสต์
        
        Returns:
            Dict with common tracks, unique to each, etc.
        """
        tracks_1 = self.source.get_playlist_tracks(playlist_id_1)
        tracks_2 = self.dest.get_playlist_tracks(playlist_id_2)
        
        # Create sets for comparison
        set_1 = {(t.title.lower(), tuple(a.lower() for a in t.artists)) for t in tracks_1}
        set_2 = {(t.title.lower(), tuple(a.lower() for a in t.artists)) for t in tracks_2}
        
        common = set_1 & set_2
        only_in_1 = set_1 - set_2
        only_in_2 = set_2 - set_1
        
        return {
            'common_count': len(common),
            'only_in_source': len(only_in_1),
            'only_in_dest': len(only_in_2),
            'similarity_ratio': len(common) / max(len(set_1), len(set_2)) * 100
        }

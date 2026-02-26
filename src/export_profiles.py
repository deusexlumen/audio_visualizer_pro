"""
Export-Profile für verschiedene Plattformen und Anwendungsfälle.

Vordefinierte Einstellungen für YouTube, Instagram, TikTok, etc.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from enum import Enum


class Platform(Enum):
    """Unterstützte Plattformen."""
    YOUTUBE = "youtube"
    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_REELS = "instagram_reels"
    TIKTOK = "tiktok"
    CUSTOM = "custom"


@dataclass
class ExportProfile:
    """Export-Profil mit Plattform-spezifischen Einstellungen."""
    
    name: str
    resolution: Tuple[int, int]
    fps: int
    aspect_ratio: str
    ffmpeg_preset: str
    ffmpeg_crf: int
    ffmpeg_audio_bitrate: str
    max_duration: Optional[int] = None  # Sekunden
    max_file_size: Optional[int] = None  # MB
    description: str = ""
    
    def get_ffmpeg_args(self) -> Dict[str, str]:
        """Gibt FFmpeg-Argumente zurück."""
        return {
            'preset': self.ffmpeg_preset,
            'crf': str(self.ffmpeg_crf),
            'audio_bitrate': self.ffmpeg_audio_bitrate
        }


# Vordefinierte Profile
EXPORT_PROFILES = {
    Platform.YOUTUBE: ExportProfile(
        name="YouTube (1080p)",
        resolution=(1920, 1080),
        fps=60,
        aspect_ratio="16:9",
        ffmpeg_preset="slow",  # Bessere Qualität
        ffmpeg_crf=18,
        ffmpeg_audio_bitrate="320k",
        max_duration=None,
        description="Optimale Einstellungen für YouTube-Videos in Full HD"
    ),
    
    Platform.YOUTUBE.value + "_4k": ExportProfile(
        name="YouTube (4K)",
        resolution=(3840, 2160),
        fps=60,
        aspect_ratio="16:9",
        ffmpeg_preset="medium",
        ffmpeg_crf=20,
        ffmpeg_audio_bitrate="320k",
        description="4K-Qualität für YouTube"
    ),
    
    Platform.INSTAGRAM_FEED: ExportProfile(
        name="Instagram Feed",
        resolution=(1080, 1080),
        fps=30,
        aspect_ratio="1:1",
        ffmpeg_preset="medium",
        ffmpeg_crf=23,
        ffmpeg_audio_bitrate="128k",
        max_duration=60,
        max_file_size=100,
        description="Quadratisches Format für Instagram Feed"
    ),
    
    Platform.INSTAGRAM_REELS: ExportProfile(
        name="Instagram Reels",
        resolution=(1080, 1920),
        fps=30,
        aspect_ratio="9:16",
        ffmpeg_preset="medium",
        ffmpeg_crf=23,
        ffmpeg_audio_bitrate="128k",
        max_duration=90,
        max_file_size=100,
        description="Vertikales Format für Instagram Reels"
    ),
    
    Platform.TIKTOK: ExportProfile(
        name="TikTok",
        resolution=(1080, 1920),
        fps=30,
        aspect_ratio="9:16",
        ffmpeg_preset="fast",  # Schneller für schnelleres Uploaden
        ffmpeg_crf=25,
        ffmpeg_audio_bitrate="128k",
        max_duration=180,
        max_file_size=287,  # TikTok Limit
        description="Optimale Einstellungen für TikTok-Videos"
    ),
    
    Platform.TIKTOK.value + "_hd": ExportProfile(
        name="TikTok (HD)",
        resolution=(1080, 1920),
        fps=60,
        aspect_ratio="9:16",
        ffmpeg_preset="medium",
        ffmpeg_crf=20,
        ffmpeg_audio_bitrate="192k",
        max_duration=180,
        max_file_size=287,
        description="Hohe Qualität für TikTok"
    ),
    
    Platform.CUSTOM: ExportProfile(
        name="Benutzerdefiniert",
        resolution=(1920, 1080),
        fps=60,
        aspect_ratio="16:9",
        ffmpeg_preset="medium",
        ffmpeg_crf=23,
        ffmpeg_audio_bitrate="320k",
        description="Eigene Einstellungen"
    )
}


def get_profile(platform: Platform) -> ExportProfile:
    """Gibt ein Export-Profil zurück."""
    return EXPORT_PROFILES.get(platform, EXPORT_PROFILES[Platform.CUSTOM])


def get_profile_by_name(name: str) -> Optional[ExportProfile]:
    """Sucht ein Profil nach Namen."""
    for profile in EXPORT_PROFILES.values():
        if profile.name.lower() == name.lower():
            return profile
    return None


def list_profiles() -> Dict[str, str]:
    """Listet alle verfügbaren Profile auf."""
    return {key.value if isinstance(key, Platform) else key: profile.name 
            for key, profile in EXPORT_PROFILES.items()}


def calculate_bitrate(profile: ExportProfile, duration_seconds: float) -> int:
    """
    Berechnet die empfohlene Bitrate für eine maximale Dateigröße.
    
    Args:
        profile: Export-Profil
        duration_seconds: Video-Dauer in Sekunden
    
    Returns:
        Empfohlene Video-Bitrate in kbps
    """
    if not profile.max_file_size:
        return 8000  # Standard: 8 Mbps
    
    # Verfügbare Größe für Video (Audio abziehen)
    audio_size = (duration_seconds * 128) / 8  # kB für 128kbps
    max_video_size = (profile.max_file_size * 1024) - audio_size  # kB
    
    # Bitrate = Größe / Dauer
    video_bitrate = (max_video_size * 8) / duration_seconds  # kbps
    
    # Min/Max Grenzen
    return max(1000, min(int(video_bitrate), 20000))


def apply_profile_to_settings(profile: ExportProfile, settings_dict: dict) -> dict:
    """
    Wendet ein Export-Profil auf Settings an.
    
    Args:
        profile: Das anzuwendende Profil
        settings_dict: Bestehende Settings
    
    Returns:
        Aktualisierte Settings
    """
    settings_dict['visual']['resolution'] = list(profile.resolution)
    settings_dict['visual']['fps'] = profile.fps
    settings_dict['ffmpeg_preset'] = profile.ffmpeg_preset
    settings_dict['ffmpeg_crf'] = profile.ffmpeg_crf
    settings_dict['ffmpeg_audio_bitrate'] = profile.ffmpeg_audio_bitrate
    
    return settings_dict

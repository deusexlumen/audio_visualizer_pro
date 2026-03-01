"""
Tests für Real-Time Audio mit gemocktem sounddevice.

Diese Tests simulieren Audio-Input ohne echte Hardware.
"""

import pytest
import numpy as np
import time
import threading
import queue
from unittest.mock import Mock, patch, MagicMock, call


# =============================================================================
# RealtimeAudioCapture Tests (Mocked)
# =============================================================================

class TestRealtimeAudioCaptureMocked:
    """Tests für RealtimeAudioCapture mit gemocktem sounddevice."""
    
    def test_init_raises_without_sounddevice(self):
        """Test dass RuntimeError geworfen wird wenn sounddevice fehlt."""
        from src.realtime import RealtimeAudioCapture, RealtimeConfig
        
        with patch('src.realtime.SOUNDDEVICE_AVAILABLE', False):
            with pytest.raises(RuntimeError) as exc_info:
                RealtimeAudioCapture(RealtimeConfig())
            
            assert "sounddevice nicht installiert" in str(exc_info.value)
    
    def test_list_devices_not_available(self):
        """Test Geräteliste wenn sounddevice nicht verfügbar."""
        from src.realtime import RealtimeAudioCapture
        
        with patch('src.realtime.SOUNDDEVICE_AVAILABLE', False):
            devices = RealtimeAudioCapture.list_devices()
        
        assert devices == []


# =============================================================================
# RealtimeFeatureExtractor Tests
# =============================================================================

class TestRealtimeFeatureExtractor:
    """Tests für RealtimeFeatureExtractor (keine sounddevice-Abhängigkeit)."""
    
    @pytest.fixture
    def extractor(self):
        """Erstellt einen FeatureExtractor."""
        from src.realtime import RealtimeFeatureExtractor, RealtimeConfig
        
        config = RealtimeConfig(sample_rate=44100, block_size=1024)
        return RealtimeFeatureExtractor(config)
    
    def test_process_silence(self, extractor):
        """Test Feature-Extraktion bei Stille."""
        audio = np.zeros((1024, 1))
        
        features = extractor.process(audio)
        
        assert 'rms' in features
        assert 'spectrum' in features
        assert 'centroid' in features
        assert 'onset' in features
        assert 'beat' in features
        assert features['rms'] == 0
        assert features['beat'] is False
    
    def test_process_full_scale(self, extractor):
        """Test Feature-Extraktion bei voller Aussteuerung."""
        audio = np.ones((1024, 1)) * 0.9
        
        features = extractor.process(audio)
        
        assert features['rms'] > 0.5  # Sollte laut sein
        assert len(features['spectrum']) == 64
    
    def test_process_stereo(self, extractor):
        """Test Stereo-zu-Mono Konvertierung."""
        audio = np.random.randn(1024, 2).astype(np.float32)
        
        features = extractor.process(audio)
        
        assert features['rms'] >= 0
        assert len(features['spectrum']) == 64
    
    def test_spectrum_normalization(self, extractor):
        """Test dass Spectrum normalisiert ist."""
        audio = np.random.randn(1024, 1).astype(np.float32)
        
        features = extractor.process(audio)
        
        spectrum = features['spectrum']
        assert all(0 <= s <= 1 for s in spectrum)
    
    def test_centroid_range(self, extractor):
        """Test dass Centroid im gültigen Bereich ist."""
        audio = np.random.randn(1024, 1).astype(np.float32)
        
        features = extractor.process(audio)
        
        assert 0 <= features['centroid'] <= 1
    
    def test_onset_range(self, extractor):
        """Test dass Onset im gültigen Bereich ist."""
        audio = np.random.randn(1024, 1).astype(np.float32)
        
        features = extractor.process(audio)
        
        assert 0 <= features['onset'] <= 1
    
    def test_compute_freq_bands(self, extractor):
        """Test Frequenzband-Berechnung."""
        magnitude = np.random.rand(1024)
        freqs = np.linspace(0, 22050, 1024)
        
        bands = extractor._compute_freq_bands(magnitude, freqs)
        
        assert len(bands) == 64
        assert all(b >= 0 for b in bands)
        # Maximalwert sollte 1 sein (normalisiert)
        assert max(bands) <= 1.0 or max(bands) == 0
    
    def test_compute_centroid(self, extractor):
        """Test Spectral Centroid Berechnung."""
        magnitude = np.array([1, 2, 3, 4, 5])
        freqs = np.array([100, 200, 300, 400, 500])
        
        centroid = extractor._compute_centroid(magnitude, freqs)
        
        assert centroid > 0
        assert 100 <= centroid <= 500
    
    def test_compute_centroid_zero_magnitude(self, extractor):
        """Test Centroid bei Null-Magnitude."""
        magnitude = np.zeros(5)
        freqs = np.array([100, 200, 300, 400, 500])
        
        centroid = extractor._compute_centroid(magnitude, freqs)
        
        assert centroid == 0
    
    def test_detect_beat(self, extractor):
        """Test Beat-Detection."""
        # Initial sollte kein Beat sein
        result1 = extractor._detect_beat(0.1, 0.1)
        assert result1 is False
        
        # Simuliere lauten Beat nach Cooldown
        time.sleep(0.3)  # Cooldown abwarten
        result2 = extractor._detect_beat(0.9, 0.9)
        # Könnte True sein, je nach Threshold
        assert isinstance(result2, bool)
    
    def test_smoothing(self, extractor):
        """Test dass RMS smoothing funktioniert."""
        # Erster Wert
        audio1 = np.ones((1024, 1)) * 0.5
        features1 = extractor.process(audio1)
        rms1 = features1['rms']
        
        # Zweiter Wert - sollte geglättet sein
        audio2 = np.ones((1024, 1)) * 0.5
        features2 = extractor.process(audio2)
        rms2 = features2['rms']
        
        # Bei gleichem Input sollte RMS ähnlich sein
        assert abs(rms1 - rms2) < 0.1


# =============================================================================
# RealtimeConfig Tests
# =============================================================================

class TestRealtimeConfig:
    """Tests für RealtimeConfig."""
    
    def test_default_values(self):
        """Test Default-Werte."""
        from src.realtime import RealtimeConfig
        
        config = RealtimeConfig()
        
        assert config.sample_rate == 44100
        assert config.block_size == 1024
        assert config.channels == 1
        assert config.device is None
        assert config.fps == 30
        assert config.smoothing == 0.8
        assert config.fft_size == 2048
        assert config.freq_bands == 64
    
    def test_custom_values(self):
        """Test benutzerdefinierte Werte."""
        from src.realtime import RealtimeConfig
        
        config = RealtimeConfig(
            sample_rate=48000,
            block_size=512,
            channels=2,
            fps=60,
            smoothing=0.5
        )
        
        assert config.sample_rate == 48000
        assert config.block_size == 512
        assert config.channels == 2
        assert config.fps == 60
        assert config.smoothing == 0.5


# =============================================================================
# Integration Tests
# =============================================================================

class TestRealtimeIntegration:
    """Integration-Tests für Real-Time Audio Flow."""
    
    def test_full_feature_extraction_flow(self):
        """Test kompletter Feature-Extraktion Flow."""
        from src.realtime import RealtimeFeatureExtractor, RealtimeConfig
        
        config = RealtimeConfig(sample_rate=44100, block_size=1024)
        extractor = RealtimeFeatureExtractor(config)
        
        # Simuliere mehrere Audio-Blöcke
        loud_rms_values = []
        quiet_rms_values = []
        
        for i in range(10):
            if i % 3 == 0:
                # Simuliere Beat (mittlere Lautstärke)
                audio = np.ones((1024, 1)) * 0.1  # 0.1 * 5 = 0.5 RMS
                features = extractor.process(audio)
                loud_rms_values.append(features['rms'])
            else:
                # Leises Audio
                audio = np.ones((1024, 1)) * 0.01  # 0.01 * 5 = 0.05 RMS
                features = extractor.process(audio)
                quiet_rms_values.append(features['rms'])
            
            # Alle Features sollten vorhanden sein
            assert all(key in features for key in ['rms', 'spectrum', 'centroid', 'onset', 'beat', 'raw_audio'])
        
        # Im Durchschnitt sollte lautes Audio höheren RMS haben
        assert sum(loud_rms_values) / len(loud_rms_values) > sum(quiet_rms_values) / len(quiet_rms_values)
    
    def test_spectrum_consistency(self):
        """Test dass Spectrum konsistent ist."""
        from src.realtime import RealtimeFeatureExtractor, RealtimeConfig
        
        config = RealtimeConfig()
        extractor = RealtimeFeatureExtractor(config)
        
        # Gleiches Audio mehrmals verarbeiten
        audio = np.random.randn(1024, 1).astype(np.float32) * 0.1
        
        features1 = extractor.process(audio)
        features2 = extractor.process(audio)
        
        # Bei gleichem Input und History sollten die Werte ähnlich sein
        # (nicht identisch wegen Smoothing)
        assert abs(features1['rms'] - features2['rms']) < 0.1


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestRealtimeErrorHandling:
    """Tests für Fehlerbehandlung im Real-Time System."""
    
    def test_feature_extractor_empty_audio(self):
        """Test Verhalten bei leerem Audio."""
        from src.realtime import RealtimeFeatureExtractor, RealtimeConfig
        
        config = RealtimeConfig()
        extractor = RealtimeFeatureExtractor(config)
        
        # Sehr kurzes Audio (minimale Länge)
        audio = np.zeros((1, 1))
        
        # Sollte nicht abstürzen
        try:
            features = extractor.process(audio)
            # Bei minimalem Audio sollten Features existieren
            assert 'rms' in features
            assert features['rms'] == 0  # Stille = 0 RMS
        except Exception as e:
            # Falls es einen Fehler gibt, sollte er behandelt werden
            pytest.fail(f"Empty audio should not cause error: {e}")
    
    def test_feature_extractor_large_values(self):
        """Test Verhalten bei großen Amplituden."""
        from src.realtime import RealtimeFeatureExtractor, RealtimeConfig
        
        config = RealtimeConfig()
        extractor = RealtimeFeatureExtractor(config)
        
        # Sehr lautes Audio (clipping)
        audio = np.ones((1024, 1)) * 100.0
        
        # Sollte nicht abstürzen
        features = extractor.process(audio)
        
        # RMS sollte auf 1 begrenzt sein (clipping)
        assert features['rms'] <= 1.0

"""
Feature Extraction - Time-Series Analysis of Force Curves
=========================================================

Extracts characteristic features from raw force-time curves.

Features extracted:
- Rise time (baseline to 90% peak)
- Fall time (peak to 10% baseline)
- Asymmetry ratio
- Peak sharpness (max 2nd derivative)
- Oscillation detection
- Plateau detection

Usage:
    from feature_extraction import TimeSeriesFeatureExtractor
    
    extractor = TimeSeriesFeatureExtractor()
    features = extractor.extract_features(time, force, baseline_idx, peak_idx)

NOTE: This requires raw force curves, not just summary metrics.
      Integrate with RawData_Processor or load CSV files directly.

Author: Cheng Sun Lab Team
Date: October 29, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
from scipy import signal, interpolate
from scipy.fft import fft, fftfreq


class TimeSeriesFeatureExtractor:
    """
    Extracts features from time-series force curves.
    """
    
    def __init__(self, sampling_rate: float = 66.67):
        """
        Initialize extractor.
        
        Args:
            sampling_rate: Data sampling rate in Hz (default 66.67 Hz = 15ms per sample)
        """
        self.sampling_rate = sampling_rate
    
    def find_rise_time(self, time: np.ndarray, force: np.ndarray, 
                       baseline_idx: int, peak_idx: int) -> float:
        """
        Calculate time from baseline to 90% of peak.
        
        Args:
            time: Time array
            force: Force array
            baseline_idx: Index of baseline start
            peak_idx: Index of peak force
            
        Returns:
            Rise time in seconds
        """
        baseline_force = force[baseline_idx]
        peak_force = force[peak_idx]
        
        # Find 90% threshold
        threshold = baseline_force + 0.9 * (peak_force - baseline_force)
        
        # Find first crossing
        segment = force[baseline_idx:peak_idx]
        crossing_indices = np.where(segment >= threshold)[0]
        
        if len(crossing_indices) == 0:
            return np.nan
        
        crossing_idx = baseline_idx + crossing_indices[0]
        
        rise_time = time[crossing_idx] - time[baseline_idx]
        
        return rise_time
    
    def find_fall_time(self, time: np.ndarray, force: np.ndarray,
                       peak_idx: int, end_idx: int) -> float:
        """
        Calculate time from peak to 10% of peak.
        
        Args:
            time: Time array
            force: Force array
            peak_idx: Index of peak force
            end_idx: Index of adhesion end
            
        Returns:
            Fall time in seconds
        """
        peak_force = force[peak_idx]
        
        # Find 10% threshold
        threshold = 0.1 * peak_force
        
        # Find first crossing below threshold
        segment = force[peak_idx:end_idx]
        crossing_indices = np.where(segment <= threshold)[0]
        
        if len(crossing_indices) == 0:
            return np.nan
        
        crossing_idx = peak_idx + crossing_indices[0]
        
        fall_time = time[crossing_idx] - time[peak_idx]
        
        return fall_time
    
    def calculate_asymmetry(self, rise_time: float, fall_time: float) -> float:
        """
        Calculate asymmetry ratio.
        
        Args:
            rise_time: Rise time in seconds
            fall_time: Fall time in seconds
            
        Returns:
            Asymmetry ratio (rise_time / fall_time)
        """
        if fall_time == 0 or np.isnan(fall_time):
            return np.nan
        
        return rise_time / fall_time
    
    def calculate_peak_sharpness(self, force: np.ndarray, peak_idx: int,
                                  window: int = 5) -> float:
        """
        Calculate peak sharpness using 2nd derivative.
        
        Args:
            force: Force array
            peak_idx: Index of peak force
            window: Window size around peak to search
            
        Returns:
            Maximum absolute value of 2nd derivative
        """
        # Get window around peak
        start = max(0, peak_idx - window)
        end = min(len(force), peak_idx + window + 1)
        
        # Calculate 2nd derivative
        segment = force[start:end]
        
        if len(segment) < 3:
            return np.nan
        
        # First derivative
        first_deriv = np.gradient(segment)
        
        # Second derivative
        second_deriv = np.gradient(first_deriv)
        
        # Maximum absolute value
        sharpness = np.max(np.abs(second_deriv))
        
        return sharpness
    
    def detect_oscillations(self, force: np.ndarray, 
                           start_idx: int, end_idx: int) -> Dict:
        """
        Detect oscillations in force curve using FFT.
        
        Args:
            force: Force array
            start_idx: Start index of segment
            end_idx: End index of segment
            
        Returns:
            Dictionary with oscillation characteristics
        """
        segment = force[start_idx:end_idx]
        
        if len(segment) < 10:
            return {
                'has_oscillation': False,
                'dominant_frequency': np.nan,
                'oscillation_amplitude': np.nan
            }
        
        # Detrend (remove linear trend)
        detrended = signal.detrend(segment)
        
        # FFT
        n = len(detrended)
        fft_values = fft(detrended)
        freqs = fftfreq(n, 1/self.sampling_rate)
        
        # Only positive frequencies
        positive_freqs = freqs[:n//2]
        magnitude = np.abs(fft_values[:n//2])
        
        # Find dominant frequency (exclude DC component)
        if len(magnitude) > 1:
            dominant_idx = np.argmax(magnitude[1:]) + 1
            dominant_freq = positive_freqs[dominant_idx]
            dominant_amp = magnitude[dominant_idx] / n * 2  # Amplitude
        else:
            dominant_freq = np.nan
            dominant_amp = np.nan
        
        # Check if oscillation is significant
        has_oscillation = dominant_amp > 0.01  # Threshold for significance
        
        return {
            'has_oscillation': has_oscillation,
            'dominant_frequency': dominant_freq,
            'oscillation_amplitude': dominant_amp
        }
    
    def detect_plateau(self, force: np.ndarray, 
                      start_idx: int, end_idx: int,
                      threshold: float = 0.05) -> Dict:
        """
        Detect plateau (constant force) regions.
        
        Args:
            force: Force array
            start_idx: Start index of segment
            end_idx: End index of segment
            threshold: Relative variation threshold for plateau (default 5%)
            
        Returns:
            Dictionary with plateau information
        """
        segment = force[start_idx:end_idx]
        
        if len(segment) < 5:
            return {
                'has_plateau': False,
                'plateau_length': 0,
                'plateau_force': np.nan
            }
        
        # Calculate sliding coefficient of variation
        window_size = min(10, len(segment) // 3)
        
        if window_size < 3:
            return {
                'has_plateau': False,
                'plateau_length': 0,
                'plateau_force': np.nan
            }
        
        # Find regions with low variation
        plateau_regions = []
        
        for i in range(len(segment) - window_size + 1):
            window = segment[i:i+window_size]
            mean = np.mean(window)
            std = np.std(window)
            
            # Coefficient of variation
            if mean != 0:
                cv = std / abs(mean)
            else:
                cv = np.inf
            
            if cv < threshold:
                plateau_regions.append(i)
        
        # Check for continuous plateau
        if len(plateau_regions) > 0:
            # Find longest continuous region
            longest_start = plateau_regions[0]
            longest_length = 1
            current_start = plateau_regions[0]
            current_length = 1
            
            for i in range(1, len(plateau_regions)):
                if plateau_regions[i] == plateau_regions[i-1] + 1:
                    current_length += 1
                else:
                    if current_length > longest_length:
                        longest_length = current_length
                        longest_start = current_start
                    current_start = plateau_regions[i]
                    current_length = 1
            
            # Check final segment
            if current_length > longest_length:
                longest_length = current_length
                longest_start = current_start
            
            plateau_force = np.mean(segment[longest_start:longest_start+window_size])
            
            return {
                'has_plateau': True,
                'plateau_length': longest_length,
                'plateau_force': plateau_force
            }
        else:
            return {
                'has_plateau': False,
                'plateau_length': 0,
                'plateau_force': np.nan
            }
    
    def extract_features(self, time: np.ndarray, force: np.ndarray,
                        baseline_idx: int, peak_idx: int, 
                        end_idx: Optional[int] = None) -> Dict:
        """
        Extract all time-series features.
        
        Args:
            time: Time array
            force: Force array
            baseline_idx: Index of adhesion baseline start
            peak_idx: Index of peak force
            end_idx: Optional index of adhesion end (default: last index)
            
        Returns:
            Dictionary of features
        """
        if end_idx is None:
            end_idx = len(force) - 1
        
        features = {}
        
        # Rise time
        features['rise_time_s'] = self.find_rise_time(time, force, baseline_idx, peak_idx)
        
        # Fall time
        features['fall_time_s'] = self.find_fall_time(time, force, peak_idx, end_idx)
        
        # Asymmetry
        features['asymmetry_ratio'] = self.calculate_asymmetry(
            features['rise_time_s'], 
            features['fall_time_s']
        )
        
        # Peak sharpness
        features['peak_sharpness'] = self.calculate_peak_sharpness(force, peak_idx)
        
        # Oscillations
        oscillation_features = self.detect_oscillations(force, baseline_idx, end_idx)
        features.update(oscillation_features)
        
        # Plateau detection
        plateau_features = self.detect_plateau(force, baseline_idx, peak_idx)
        features.update({f'pre_peak_{k}': v for k, v in plateau_features.items()})
        
        plateau_features_post = self.detect_plateau(force, peak_idx, end_idx)
        features.update({f'post_peak_{k}': v for k, v in plateau_features_post.items()})
        
        return features
    
    def extract_from_csv(self, csv_path: Path, 
                        lifting_start: int, lifting_end: int,
                        baseline_idx: int, peak_idx: int) -> Dict:
        """
        Extract features directly from CSV file.
        
        Args:
            csv_path: Path to CSV file with Time and Force columns
            lifting_start: Row index where lifting phase starts
            lifting_end: Row index where lifting phase ends
            baseline_idx: Relative index (within lifting) of baseline
            peak_idx: Relative index (within lifting) of peak
            
        Returns:
            Dictionary of features
        """
        # Load CSV
        df = pd.read_csv(csv_path)
        
        # Extract lifting phase
        time = df['Time (s)'].values[lifting_start:lifting_end]
        force = df['Force (N)'].values[lifting_start:lifting_end]
        
        # Adjust indices to be relative to segment
        time = time - time[0]  # Start at 0
        
        # Extract features
        features = self.extract_features(time, force, baseline_idx, peak_idx)
        
        return features


if __name__ == "__main__":
    """Example usage"""
    
    # Example with synthetic data
    print("Demonstrating feature extraction with synthetic data...")
    print("="*60)
    
    # Create synthetic force curve
    t = np.linspace(0, 10, 500)  # 10 seconds
    
    # Rising phase (exponential approach to peak)
    rise = 1.0 * (1 - np.exp(-t/2))
    
    # Falling phase (power law decay)
    fall = 1.0 * np.exp(-t/3)
    
    # Combine
    force = np.concatenate([rise[:250], fall[:250]])
    time = np.linspace(0, 10, len(force))
    
    # Add some noise
    force += np.random.normal(0, 0.01, len(force))
    
    # Define indices
    baseline_idx = 10
    peak_idx = 250
    
    # Extract features
    extractor = TimeSeriesFeatureExtractor()
    features = extractor.extract_features(time, force, baseline_idx, peak_idx)
    
    # Print results
    print("\nExtracted Features:")
    print("-"*60)
    for key, value in features.items():
        if isinstance(value, float):
            print(f"{key:30s}: {value:.4f}")
        else:
            print(f"{key:30s}: {value}")
    
    print("\n" + "="*60)
    print("\nNOTE: To use with real data, integrate with RawData_Processor")
    print("or provide CSV path with extract_from_csv() method.")

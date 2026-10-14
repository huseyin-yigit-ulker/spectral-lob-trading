"""
features/frequency_features.py
Limit Order Book (LOB) Frequency Domain Analysis Module.

Transforms high-frequency order book dynamics (OBI and depth churn) from the time domain
to the frequency domain via Real Fast Fourier Transform (FFT) and Power Spectral Density (PSD).

Distinguishes between:
1. Low-Frequency Persistent Liquidity (Institutional absorption & resting human flow)
2. High-Frequency Micro-Flickering (HFT pinging & quote stuffing)
3. Deterministic Spectral Spikes (Algorithmic spoofing & layering cycles)
"""

import numpy as np
from typing import Dict, Any


class LOBSpectralAnalyzer:
    """
    Performs real-time Fourier analysis on a rolling window of Limit Order Book metrics.
    Uses pure NumPy (np.fft) for sub-millisecond execution overhead (<0.15ms).
    """

    def __init__(self, window_size: int = 128, sample_rate_hz: float = 10.0):
        """
        :param window_size: Number of samples in rolling window (default 128 = ~12.8s at 100ms ticks).
        :param sample_rate_hz: Sampling frequency in Hz (default 10 Hz for 100ms Binance depth updates).
        """
        self.N = window_size
        self.fs = sample_rate_hz
        self.buffer_obi = np.zeros(self.N, dtype=np.float32)
        self.buffer_churn = np.zeros(self.N, dtype=np.float32)
        self.count = 0
        
        # Hanning window to eliminate spectral leakage
        self.hanning = np.hanning(self.N).astype(np.float32)
        
        # Real FFT frequencies (Nyquist frequency = fs / 2 = 5 Hz for 10 Hz sampling)
        self.freqs = np.fft.rfftfreq(self.N, d=1.0 / self.fs)
        
        # Frequency band definitions:
        # Low band: 0.05 Hz - 0.8 Hz (Periods 1.25s to 20s) -> Resting institutional/human flow
        # High band: 1.0 Hz - 5.0 Hz (Periods 200ms to 1s) -> HFT quote flickering & spoofing loops
        self.low_mask = (self.freqs >= 0.05) & (self.freqs < 0.8)
        self.high_mask = (self.freqs >= 1.0) & (self.freqs <= (self.fs / 2.0))

    def add_tick(self, obi: float, churn: float = 0.0):
        """
        Add a new sample to the rolling buffer.
        """
        self.buffer_obi = np.roll(self.buffer_obi, -1)
        self.buffer_obi[-1] = obi
        self.buffer_churn = np.roll(self.buffer_churn, -1)
        self.buffer_churn[-1] = churn
        self.count += 1

    def is_ready(self) -> bool:
        """Returns True if the buffer has collected at least N ticks."""
        return self.count >= self.N

    def analyze(self) -> Dict[str, Any]:
        """
        Computes Power Spectral Density (PSD) and extracts microstructure metrics:
        - RLR: Real Liquidity Ratio (0.0 to 1.0)
        - BSI: Bot Spoofing Index (0.0 to 1.0)
        - clean_obi: Inverse-FFT low-pass filtered OBI (stripped of HFT noise and spoofing peaks)
        - state: 'ORGANIC', 'HFT_NOISE', 'SPOOFING_ALERT', or 'WARMING_UP'
        """
        if not self.is_ready():
            last_val = float(self.buffer_obi[-1]) if self.count > 0 else 0.0
            return {
                "rlr": 1.0,
                "bsi": 0.0,
                "clean_obi": round(last_val, 4),
                "state": "WARMING_UP",
                "is_spoofing": False,
                "dominant_freq": 0.0
            }

        # 1. Zero-mean detrending & windowing
        mean_obi = float(np.mean(self.buffer_obi))
        detrended = self.buffer_obi - mean_obi
        windowed = detrended * self.hanning

        # 2. Real FFT & Power Spectral Density (PSD)
        fft_vals = np.fft.rfft(windowed)
        psd = np.abs(fft_vals) ** 2

        # Ignore DC component (k=0)
        ac_psd = psd[1:]
        total_ac_energy = float(np.sum(ac_psd)) + 1e-9

        # Band energies
        e_low = float(np.sum(psd[self.low_mask]))
        e_high = float(np.sum(psd[self.high_mask]))

        # 3. Real Liquidity Ratio (RLR)
        # Ratio of low-frequency persistent energy to (low + high) energy
        rlr = float(e_low / (e_low + e_high + 1e-9))
        rlr = float(np.clip(rlr, 0.0, 1.0))

        # 4. Bot Spoofing Index (BSI / High-Frequency Deterministic Spike)
        # When an HFT bot adds/cancels orders in a cyclic loop (e.g. at 2 Hz or 3 Hz),
        # a massive spike appears in the high frequency band (f >= 1.0 Hz).
        high_psd = psd.copy()
        high_psd[self.freqs < 1.0] = 0.0
        total_high_energy = float(np.sum(high_psd))

        if total_high_energy > 0:
            high_max_idx = int(np.argmax(high_psd))
            max_high_peak = float(high_psd[high_max_idx])
            dominant_high_freq = float(self.freqs[high_max_idx])
            
            # Peak concentration in high-freq band:
            peak_concentration = max_high_peak / (total_high_energy + 1e-9)
            # Energy share of high-freq band in total signal:
            hf_share = total_high_energy / total_ac_energy
            
            # BSI: Combination of peak concentration and high-frequency dominance
            bsi = float(peak_concentration * np.sqrt(hf_share))
        else:
            dominant_high_freq = 0.0
            bsi = 0.0

        bsi = float(np.clip(bsi, 0.0, 1.0))

        # 5. De-spoofed Clean OBI (Frequency-domain low-pass filtering)
        # Zero out high frequencies (>0.8 Hz)
        filtered_fft = fft_vals.copy()
        cutoff_mask = self.freqs >= 0.8
        filtered_fft[cutoff_mask] = 0.0

        # Reconstruct clean signal in time domain via Inverse Real FFT
        reconstructed = np.fft.irfft(filtered_fft, n=self.N)
        clean_obi = float(mean_obi + reconstructed[-1])
        clean_obi = float(np.clip(clean_obi, -1.0, 1.0))

        # 6. Classification State
        # Spoofing alert: strong high-frequency concentration and significant BSI (>= 0.35)
        if bsi >= 0.35 and total_high_energy > 0.20 * total_ac_energy:
            state = "SPOOFING_ALERT"
            is_spoofing = True
        elif rlr < 0.45 and total_high_energy > total_ac_energy * 0.4:
            state = "HFT_NOISE"
            is_spoofing = False
        else:
            state = "ORGANIC"
            is_spoofing = False

        return {
            "rlr": round(rlr, 3),
            "bsi": round(bsi, 3),
            "clean_obi": round(clean_obi, 4),
            "state": state,
            "is_spoofing": is_spoofing,
            "dominant_freq": round(dominant_high_freq, 2)
        }

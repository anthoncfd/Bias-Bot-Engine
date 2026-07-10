import numpy as np
from typing import List, Dict, Any, Optional
from app.logger import logger

class QuantitativeMathEngine:
    """Institutional mathematical analytics engine.
    Computes statistical indicators, processes vectorized asset variances,
    and isolates predictive trends using purely deterministic quantitative modeling.
    """

    @staticmethod
    def _extract_closes(historical_bars: List[Dict[str, Any]]) -> np.ndarray:
        """Helper method to parse and reverse historical bars into a chronological NumPy array."""
        # Database returns date DESC; we invert to date ASC (chronological) for moving averages
        closes = [float(bar["close"]) for bar in historical_bars]
        return np.array(closes[::-1])

    @staticmethod
    def calculate_technical_indicators(historical_bars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates institutional indicators from expanded daily historical lookback matrices."""
        try:
            closes = QuantitativeMathEngine._extract_closes(historical_bars)
            n_bars = len(closes)

            # 🛡️ EXPANDED THRESHOLD GUARD
            if n_bars < 50:
                logger.warning(f"⚠️ Shallow matrix lookback detected ({n_bars} bars). Indicator processing using max available fallback capacity.")

            if n_bars < 2:
                raise ValueError("Insufficient data bars to compute basic lookback statistics.")

            # 1. Moving Averages (Safely constrained to maximum array capacity)
            sma_20_len = min(20, n_bars)
            sma_50_len = min(50, n_bars)
            
            sma_20 = float(np.mean(closes[-sma_20_len:]))
            sma_50 = float(np.mean(closes[-sma_50_len:]))

            # 2. Average True Range (ATR) Fallback Realization
            if n_bars > 1:
                atr_window = min(14, n_bars - 1)
                close_diffs = np.abs(np.diff(closes))
                atr = float(np.mean(close_diffs[-atr_window:]))
            else:
                atr = 0.0

            # 3. Momentum (Absolute rate of change relative to standard 10-period lookback)
            mom_window = min(10, n_bars - 1)
            momentum = float(closes[-1] - closes[-1 - mom_window])

            # 4. Trend Slope (Ordinary Least Squares Linear Regression over final 14 bars)
            slope_window = min(14, n_bars)
            if slope_window > 1:
                y = closes[-slope_window:]
                x = np.arange(slope_window)
                # OLS Slope formula: Cov(X,Y) / Var(X)
                slope = float(np.cov(x, y)[0, 1] / np.var(x, ddof=1))
            else:
                slope = 0.0

            # 5. Z-Score (Distance of current close from the 20-period moving average in Standard Deviations)
            z_window = min(20, n_bars)
            if z_window > 1:
                window_mean = np.mean(closes[-z_window:])
                window_std = np.std(closes[-z_window:], ddof=1)
                z_score = float((closes[-1] - window_mean) / window_std) if window_std > 0 else 0.0
            else:
                z_score = 0.0

            # 6. Quantitative Technical Score Normalization Layer Matrix
            # Allocation weights: Trend Alignment & Slope (40%), Momentum & Z-Score State (60%)
            tech_score = 0.0
            
            if sma_20 > sma_50: tech_score += 0.20
            else: tech_score -= 0.20
            
            if slope > 0: tech_score += 0.20
            else: tech_score -= 0.20
            
            if momentum > 0: tech_score += 0.30
            else: tech_score -= 0.30
            
            # Map Z-Score scale bounds symmetrically over standard +/- 2.0 Sigma boundaries
            z_bounded = max(-2.0, min(2.0, z_score))
            tech_score += (z_bounded / 2.0) * 0.30

            return {
                "sma_20": sma_20,
                "sma_50": sma_50,
                "atr": atr,
                "momentum": momentum,
                "slope": slope,
                "z_score": z_score,
                "technical_score_pct": float(tech_score * 100)
            }

        except Exception as err:
            logger.error(f"Quantitative calculation exception inside Math Engine: {err}")
            return {
                "sma_20": 0.0, "sma_50": 0.0, "atr": 0.0, "momentum": 0.0,
                "slope": 0.0, "z_score": 0.0, "technical_score_pct": 0.0
            }

    @staticmethod
    def calculate_monte_carlo(current_price: float, historical_bars: List[Dict[str, Any]], 
                              paths: int = 2000, horizons: int = 1) -> Dict[str, Any]:
        """Calculates classic Geometric Brownian Motion drift paths using continuous logged variances."""
        try:
            closes = QuantitativeMathEngine._extract_closes(historical_bars)
            if len(closes) < 3:
                return {"prob_up": 50.0, "prob_down": 50.0, "expected_value": current_price, "sigma_pct": 0.5, "kelly_suggested_allocation_pct": 0.0}

            log_returns = np.log(closes[1:] / closes[:-1])
            mu = np.mean(log_returns)
            sigma = np.std(log_returns, ddof=1)
            
            if sigma == 0:
                sigma = 0.0001

            drift = mu - 0.5 * (sigma ** 2)
            shock = sigma * np.random.normal(0, 1, (paths, horizons))
            simulated_paths = current_price * np.exp(drift + shock)
            final_prices = simulated_paths[:, -1]

            expected_value = float(np.mean(final_prices))
            prob_up = float(np.sum(final_prices > current_price) / paths * 100)
            prob_down = 100.0 - prob_up

            edge = abs(prob_up - prob_down) / 100.0
            kelly = (edge / 1.0) * 0.10 if edge > 0.02 else 0.0

            return {
                "prob_up": prob_up,
                "prob_down": prob_down,
                "expected_value": expected_value,
                "sigma_pct": float(sigma * 100),
                "kelly_suggested_allocation_pct": float(kelly * 100)
            }
        except Exception as err:
            logger.error(f"Vectorized Monte Carlo calculus processing fault: {err}")
            return {"prob_up": 50.0, "prob_down": 50.0, "expected_value": current_price, "sigma_pct": 0.0, "kelly_suggested_allocation_pct": 0.0}

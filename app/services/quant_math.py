import numpy as np
from typing import List, Dict, Any
from app.logger import logger

class QuantitativeMathEngine:
    """Institutional mathematical analytics engine.
    Computes statistical indicators, processes vectorized asset variances,
    and isolates predictive trends using purely deterministic quantitative modeling.
    """

    @staticmethod
    def _extract_vectorized_closes(historical_bars: List[Dict[str, Any]], live_price: float) -> np.ndarray:
        """Loads historical matrices into a contiguous memory block via high-performance 
        NumPy C-arrays, then dynamically appends the active live price token.
        """
        iterator = (float(bar["close"]) for bar in historical_bars)
        historical_vector = np.fromiter(iterator, dtype=float, count=len(historical_bars))
        chronological_vector = historical_vector[::-1]
        return np.append(chronological_vector, live_price)

    @staticmethod
    def calculate_technical_indicators(historical_bars: List[Dict[str, Any]], live_price: float, asset_class: str) -> Dict[str, Any]:
        """Calculates institutional indicators and executes dynamic volatility-normalized confluence signaling."""
        try:
            closes = QuantitativeMathEngine._extract_vectorized_closes(historical_bars, live_price)
            n_bars = len(closes)

            if n_bars < 2:
                raise ValueError("Insufficient time-series elements to calculate foundational lookbacks.")

            # 1. Moving Averages
            sma_20_len = min(20, n_bars)
            sma_50_len = min(50, n_bars)
            sma_20 = float(np.mean(closes[-sma_20_len:]))
            sma_50 = float(np.mean(closes[-sma_50_len:]))

            # 2. Closing Volatility Range (CVR) - Realized 14-period daily historical variance
            if n_bars > 1:
                cvr_window = min(14, n_bars - 1)
                close_diffs = np.abs(np.diff(closes))
                cvr = float(np.mean(close_diffs[-cvr_window:]))
            else:
                cvr = 0.0001  # Safe denominator configuration protection

            # 3. Momentum
            mom_window = min(10, n_bars - 1)
            momentum = float(closes[-1] - closes[-1 - mom_window])

            # 4. Trend Slope (OLS Linear Regression Gradient)
            slope_window = min(14, n_bars)
            if slope_window > 1:
                y = closes[-slope_window:]
                x = np.arange(slope_window)
                slope = float(np.cov(x, y)[0, 1] / np.var(x, ddof=1))
            else:
                slope = 0.0

            # 5. Z-Score (Standardized deviation distance from the short-term mean)
            z_window = min(20, n_bars)
            if z_window > 1:
                window_mean = np.mean(closes[-z_window:])
                window_std = np.std(closes[-z_window:], ddof=1)
                z_score = float((closes[-1] - window_mean) / window_std) if window_std > 0 else 0.0
            else:
                z_score = 0.0

            # 6. Quantitative Technical Score Normalization Layer
            tech_score = 0.0
            if sma_20 > sma_50: tech_score += 0.20
            else: tech_score -= 0.20
            if slope > 0: tech_score += 0.20
            else: tech_score -= 0.20
            if momentum > 0: tech_score += 0.30
            else: tech_score -= 0.30
            
            z_bounded = max(-2.0, min(2.0, z_score))
            tech_score += (z_bounded / 2.0) * 0.30
            tech_score_pct = float(tech_score * 100)

            # ━━━━ 🏛️ VOLATILITY-NORMALIZED CONFLUENCE FILTER ━━━━
            # Instead of guessing hardcoded figures, evaluate the intraday net change against the 14-day CVR
            net_change = live_price - float(historical_bars[0]["close"])
            
            # Mathematically derive the noise score profile (Intraday Sigma Deviation)
            intraday_noise_z = abs(net_change) / cvr if cvr > 0 else 0.0
            is_noise = intraday_noise_z < 0.20  # Under 0.2 Sigma represents raw inside consolidation noise
            
            # Asset class adaptive breakout thresholds
            barrier = 15.0 if asset_class == "FOREX" else 30.0

            if tech_score_pct > barrier:
                if is_noise:
                    bias_state = "BULLISH_CONSOLIDATION"
                    display_text = "🟢 STRUCTURAL BULLISH (INTRADAY CONSOLIDATION)"
                    icon = "📈"
                elif net_change > 0:
                    bias_state = "STRONGLY_BULLISH"
                    display_text = "🟢 STRONGLY BULLISH BIAS"
                    icon = "🚀"
                else:
                    bias_state = "BULLISH_RETRACEMENT"
                    display_text = "🟡 BULLISH RETRACEMENT (DIP BUYING ZONE)"
                    icon = "⚡"
                    
            elif tech_score_pct < -barrier:
                if is_noise:
                    bias_state = "BEARISH_CONSOLIDATION"
                    display_text = "🔴 STRUCTURAL BEARISH (INTRADAY CONSOLIDATION)"
                    icon = "📉"
                elif net_change < 0:
                    bias_state = "STRONGLY_BEARISH"
                    display_text = "🔴 STRONGLY BEARISH BIAS"
                    icon = "💥"
                else:
                    bias_state = "BEARISH_RECOVERY"
                    display_text = "🟡 BEARISH RECOVERY (RALLY SELLING ZONE)"
                    icon = "⚡"
                    
            else:
                bias_state = "NEUTRAL"
                display_text = "培育 NEUTRAL MEAN REVERSION BLOCK"
                icon = "秤️"

            return {
                "sma_20": sma_20,
                "sma_50": sma_50,
                "cvr": cvr,
                "momentum": momentum,
                "slope": slope,
                "z_score": z_score,
                "technical_score_pct": tech_score_pct,
                "bias_state": bias_state,
                "bias_display": display_text,
                "bias_icon": icon
            }

        except Exception as err:
            logger.error(f"Quantitative calculation exception inside Math Engine: {err}")
            return {
                "sma_20": 0.0, "sma_50": 0.0, "cvr": 0.0, "momentum": 0.0, "slope": 0.0, "z_score": 0.0,
                "technical_score_pct": 0.0, "bias_state": "NEUTRAL", "bias_display": "⚪ SYSTEM ERROR", "bias_icon": "⚠️"
            }

    @staticmethod
    def calculate_monte_carlo(current_price: float, historical_bars: List[Dict[str, Any]], 
                              paths: int = 2000, horizons: int = 1) -> Dict[str, Any]:
        """Calculates classic Geometric Brownian Motion drift paths using continuous logged variances."""
        try:
            iterator = (float(bar["close"]) for bar in historical_bars)
            closes = np.fromiter(iterator, dtype=float, count=len(historical_bars))[::-1]
            
            if len(closes) < 3:
                return {"prob_up": 50.0, "prob_down": 50.0, "expected_value": current_price, "sigma_pct": 0.5, "kelly_suggested_allocation_pct": 0.0}

            log_returns = np.log(closes[1:] / closes[:-1])
            mu = np.mean(log_returns)
            sigma = np.std(log_returns, ddof=1)
            
            if sigma == 0: sigma = 0.0001

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

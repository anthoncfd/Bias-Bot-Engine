import numpy as np
from app.logger import logger

class QuantitativeMathEngine:
    """Institutional-grade mathematical modeling engine specializing in stochastic path simulations."""

    @staticmethod
    def calculate_monte_carlo(current_price: float, historical_bars: list) -> dict:
        """
        Runs an ultra-fast vectorized Geometric Brownian Motion simulation using NumPy.
        Returns expected values, volatility bounds, and probabilistic distribution edges.
        """
        try:
            if not historical_bars or len(historical_bars) < 2:
                raise ValueError("Insufficient historical data blocks to compute return matrix.")

            closes = [float(bar["close"]) for bar in historical_bars][::-1]
            log_returns = np.diff(np.log(closes))
            
            mu = np.mean(log_returns)
            sigma = np.std(log_returns)
            
            if sigma == 0: 
                sigma = 0.001
            
            simulations = 2000
            steps = 4 
            dt = 1.0
            
            Z = np.random.normal(0, 1, (steps, simulations))
            drift_factor = (mu - 0.5 * (sigma ** 2)) * dt
            vol_factor = sigma * np.sqrt(dt)
            
            price_paths = np.zeros((steps + 1, simulations))
            price_paths[0] = current_price
            
            for t in range(1, steps + 1):
                price_paths[t] = price_paths[t-1] * np.exp(drift_factor + vol_factor * Z[t-1])
            
            final_prices = price_paths[-1]
            
            expected_value = float(np.mean(final_prices))
            prob_up = float(np.sum(final_prices > current_price) / simulations) * 100
            prob_down = 100.0 - prob_up
            
            # 🧠 FIXED QUANT MATH: Calculate absolute statistical edge distance
            # This captures the deviation delta regardless of whether it's bullish or bearish
            edge = abs(prob_up - prob_down) / 100.0
            
            # Define structural activation threshold (minimum 4% delta imbalance required to trigger risk allocation)
            # Example: 52% vs 48% = 4% edge delta (Our minimum required floor)
            if edge >= 0.04:
                # Apply 20% Fractional Kelly scale factor to raw edge vector
                kelly_fraction = edge * 0.2
            else:
                kelly_fraction = 0.0
            
            return {
                "expected_value": expected_value,
                "prob_up": prob_up,
                "prob_down": prob_down,
                "sigma_pct": float(sigma * 100),
                "kelly_suggested_allocation_pct": kelly_fraction * 100
            }
        except Exception as err:
            logger.error(f"Quantitative Math Engine mathematical execution fault: {err}")
            return {
                "expected_value": current_price,
                "prob_up": 50.0,
                "prob_down": 50.0,
                "sigma_pct": 0.0,
                "kelly_suggested_allocation_pct": 0.0
            }

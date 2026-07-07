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

            # 1. Isolate and reverse closes so array moves chronologically (oldest to newest)
            closes = [float(bar["close"]) for bar in historical_bars][::-1]
            
            # 2. Compute log returns to model volatility distributions accurately
            log_returns = np.diff(np.log(closes))
            
            # 3. Extract baseline drift (mu) and period volatility (sigma)
            mu = np.mean(log_returns)
            sigma = np.std(log_returns)
            
            # Guard against edge-case division-by-zero or zero-volatility calculation crashes
            if sigma == 0: 
                sigma = 0.001
            
            # 4. Vectorized Simulation Configuration (2,000 paths across 4 distinct intraday step intervals)
            simulations = 2000
            steps = 4 
            dt = 1.0
            
            # Generate complete standard normal random distribution matrix (steps x simulations)
            Z = np.random.normal(0, 1, (steps, simulations))
            
            # Formulate GBM components
            drift_factor = (mu - 0.5 * (sigma ** 2)) * dt
            vol_factor = sigma * np.sqrt(dt)
            
            # Allocate paths array initialized to the current live tick asset value
            price_paths = np.zeros((steps + 1, simulations))
            price_paths[0] = current_price
            
            # Vectorized projection matrix cascade
            for t in range(1, steps + 1):
                price_paths[t] = price_paths[t-1] * np.exp(drift_factor + vol_factor * Z[t-1])
            
            # Isolate the final settled price row array
            final_prices = price_paths[-1]
            
            # 5. Compile probability density profiles
            expected_value = float(np.mean(final_prices))
            prob_up = float(np.sum(final_prices > current_price) / simulations) * 100
            prob_down = 100.0 - prob_up
            
            # 6. Optional Feature: Apply Fractional Kelly Sizing Guideline (20% Edge Sizing Variant)
            # Edge = win_probability - lose_probability
            edge = (prob_up / 100.0) - (prob_down / 100.0)
            kelly_fraction = max(0.0, edge * 0.2) # Allocation cap guard rails
            
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

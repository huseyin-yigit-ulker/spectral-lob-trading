"""
Reward functions for RL agent.
"""
import numpy as np
from typing import List

def pnl_reward(realized_pnl: float, commission: float) -> float:
    """
    Basic PnL minus costs.
    """
    return float(realized_pnl - commission)

def sharpe_reward(returns_history: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Sharpe ratio based reward.
    """
    if len(returns_history) < 2:
        return 0.0
        
    returns_arr = np.array(returns_history)
    mean_return = np.mean(returns_arr) - risk_free_rate
    std_return = np.std(returns_arr)
    
    if std_return == 0:
        return 0.0
        
    return float(mean_return / std_return)

def sortino_reward(returns_history: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Sortino ratio (downside risk only).
    """
    if len(returns_history) < 2:
        return 0.0
        
    returns_arr = np.array(returns_history)
    mean_return = np.mean(returns_arr) - risk_free_rate
    
    downside_returns = returns_arr[returns_arr < 0]
    if len(downside_returns) == 0:
        return float(mean_return) # Infinite Sortino, return mean
        
    downside_std = np.std(downside_returns)
    if downside_std == 0:
        return float(mean_return)
        
    return float(mean_return / downside_std)

def composite_reward(pnl: float, drawdown: float, win_rate: float, pnl_weight: float = 1.0, dd_weight: float = 0.5) -> float:
    """
    Composite reward combining PnL and drawdown penalties.
    """
    reward = (pnl * pnl_weight) - (drawdown * dd_weight)
    
    # Optional: Bonus for high win rate
    if win_rate > 0.5:
        reward += 0.1
        
    return float(reward)

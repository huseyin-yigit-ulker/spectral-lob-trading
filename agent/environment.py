"""
Gymnasium environment for trading agent.
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, Any, Tuple

class TradingEnvironment(gym.Env):
    """
    Custom Trading Environment that follows gymnasium interface.
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, state_dim: int, initial_balance: float = 10000.0, commission_rate: float = 0.0004):
        super().__init__()
        
        self.state_dim = state_dim
        self.initial_balance = initial_balance
        self.commission_rate = commission_rate
        self.risk_per_trade = 0.01 # 1% risk
        
        # Actions: 0 = Hold, 1 = Long, 2 = Short, 3 = Close
        self.action_space = spaces.Discrete(4)
        
        # Observation space
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.state_dim,), dtype=np.float32
        )
        
        self.reset()

    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        
        self.balance = self.initial_balance
        self.position = 0 # 1 for long, -1 for short, 0 for flat
        self.entry_price = 0.0
        self.current_step = 0
        self.max_balance = self.initial_balance
        self.max_drawdown = 0.0
        
        # Placeholder for initial state
        obs = np.zeros(self.state_dim, dtype=np.float32)
        info = {}
        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        # Placeholder current price (should be provided by data feed)
        current_price = 100.0 
        
        reward = 0.0
        done = False
        truncated = False
        
        # Execute action
        if action == 1 and self.position <= 0: # Long
            if self.position == -1:
                # Close short first
                pnl = (self.entry_price - current_price) / self.entry_price
                reward += pnl - self.commission_rate
            self.position = 1
            self.entry_price = current_price
            reward -= self.commission_rate
            
        elif action == 2 and self.position >= 0: # Short
            if self.position == 1:
                # Close long first
                pnl = (current_price - self.entry_price) / self.entry_price
                reward += pnl - self.commission_rate
            self.position = -1
            self.entry_price = current_price
            reward -= self.commission_rate
            
        elif action == 3 and self.position != 0: # Close
            if self.position == 1:
                pnl = (current_price - self.entry_price) / self.entry_price
            else:
                pnl = (self.entry_price - current_price) / self.entry_price
            reward += pnl - self.commission_rate
            self.position = 0
            self.entry_price = 0.0
            
        # Update balance and drawdown
        self.balance += reward * self.balance * self.risk_per_trade # Simplified
        if self.balance > self.max_balance:
            self.max_balance = self.balance
        
        dd = (self.max_balance - self.balance) / self.max_balance
        if dd > self.max_drawdown:
            self.max_drawdown = dd
            
        if self.balance <= 0:
            done = True
            
        self.current_step += 1
        
        obs = np.zeros(self.state_dim, dtype=np.float32) # Fetch new state
        info = {
            "balance": self.balance,
            "max_drawdown": self.max_drawdown,
            "position": self.position
        }
        
        return obs, float(reward), done, truncated, info

    def render(self):
        print(f"Step: {self.current_step}, Balance: {self.balance:.2f}, Position: {self.position}")

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, Any, Tuple

class TradingEnvironment(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self, states: np.ndarray, prices: np.ndarray, initial_balance: float = 10000.0, commission_rate: float = 0.0004):
        super().__init__()
        self.states = states
        self.prices = prices
        # State boyutunu 1 artiriyoruz (Mevcut Pozisyon icin)
        self.state_dim = states.shape[1] + 1
        self.initial_balance = initial_balance
        self.commission_rate = commission_rate
        self.n_steps = len(states)
        
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(self.state_dim,), dtype=np.float32)
        
        self.reset()

    def _get_obs(self):
        # Ajanin o anki piyasa gozlemine, KENDI POZISYONUNU da ekliyoruz!
        return np.append(self.states[self.current_step], self.position).astype(np.float32)

    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self.balance = self.initial_balance
        self.position = 0 
        self.entry_price = 0.0
        self.current_step = 0
        return self._get_obs(), {}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        prev_balance = self.balance
        current_price = self.prices[self.current_step]
        target_pos = action - 1
        
        if target_pos != self.position:
            # Yon degisikliginde cift yonlu komisyon (Cikis + Yeni Giris)
            self.balance -= self.balance * self.commission_rate * 2
            self.position = target_pos
            self.entry_price = current_price if target_pos != 0 else 0.0
        
        if self.position != 0 and self.current_step < self.n_steps - 1:
            next_price = self.prices[self.current_step + 1]
            price_diff = (next_price - current_price) / current_price
            step_pnl = self.balance * price_diff * self.position
            self.balance += step_pnl
        
        reward = (self.balance - prev_balance) / self.initial_balance
        
        # Gereksiz islem (Overtrading) cezasini biraz daha keskinlestirelim
        if target_pos == 0:
            reward -= 0.00001
            
        self.current_step += 1
        done = self.current_step >= self.n_steps - 1
        
        obs = self._get_obs() if not done else np.zeros(self.state_dim, dtype=np.float32)
        
        return obs, float(reward), done, False, {"balance": self.balance}

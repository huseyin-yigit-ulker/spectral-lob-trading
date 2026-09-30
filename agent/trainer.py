"""
Agent trainer module using stable-baselines3.
"""
import os
from typing import Dict, Any, Optional
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import EvalCallback
from .environment import TradingEnvironment

class AgentTrainer:
    """
    Trains and evaluates the RL agent.
    """
    def __init__(self, env: TradingEnvironment, algo: str = "PPO", config: Optional[Dict[str, Any]] = None):
        self.env = DummyVecEnv([lambda: env])
        self.algo_name = algo.upper()
        self.config = config or {}
        self.model = self._build_model()
        
    def _build_model(self):
        # TODO: integrate custom feature extractors (LSTM/TCN) via policy_kwargs
        if self.algo_name == "PPO":
            return PPO("MlpPolicy", self.env, verbose=1, **self.config)
        elif self.algo_name == "SAC":
            return SAC("MlpPolicy", self.env, verbose=1, **self.config)
        else:
            raise ValueError(f"Unsupported algorithm: {self.algo_name}")

    def train(self, total_timesteps: int, save_path: str, eval_env: Optional[TradingEnvironment] = None):
        """
        Train the model.
        """
        callbacks = []
        if eval_env is not None:
            eval_vec_env = DummyVecEnv([lambda: eval_env])
            eval_callback = EvalCallback(
                eval_vec_env, 
                best_model_save_path=os.path.dirname(save_path),
                log_path=os.path.dirname(save_path),
                eval_freq=10000,
                deterministic=True,
                render=False
            )
            callbacks.append(eval_callback)
            
        print(f"Starting training for {total_timesteps} timesteps using {self.algo_name}...")
        self.model.learn(total_timesteps=total_timesteps, callback=callbacks)
        
        self.save_model(save_path)
        print("Training completed.")

    def evaluate(self, episodes: int = 10):
        """
        Evaluate the trained model.
        """
        # TODO: Implement evaluation loop and metrics collection
        print(f"Evaluating for {episodes} episodes...")
        for i in range(episodes):
            obs = self.env.reset()
            done = False
            while not done:
                action, _states = self.model.predict(obs, deterministic=True)
                obs, rewards, done, info = self.env.step(action)
        print("Evaluation completed.")

    def save_model(self, path: str):
        """Save model to disk."""
        self.model.save(path)
        
    def load_model(self, path: str):
        """Load model from disk."""
        if self.algo_name == "PPO":
            self.model = PPO.load(path, env=self.env)
        elif self.algo_name == "SAC":
            self.model = SAC.load(path, env=self.env)

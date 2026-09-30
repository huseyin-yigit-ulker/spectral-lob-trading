"""
PyTorch model architectures for RL agent.
"""
import torch
import torch.nn as nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
import gymnasium as gym

class LSTMFeatureExtractor(BaseFeaturesExtractor):
    """
    LSTM-based feature extractor for temporal state dependencies.
    """
    def __init__(self, observation_space: gym.Space, features_dim: int = 256, hidden_size: int = 128, num_layers: int = 1):
        super().__init__(observation_space, features_dim)
        
        state_dim = observation_space.shape[0]
        
        self.lstm = nn.LSTM(
            input_size=state_dim,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )
        
        self.linear = nn.Linear(hidden_size, features_dim)
        self._initialize_weights()
        
    def _initialize_weights(self):
        for name, param in self.lstm.named_parameters():
            if 'weight_ih' in name:
                nn.init.xavier_uniform_(param.data)
            elif 'weight_hh' in name:
                nn.init.orthogonal_(param.data)
            elif 'bias' in name:
                param.data.fill_(0)
                
        nn.init.xavier_uniform_(self.linear.weight)
        nn.init.constant_(self.linear.bias, 0)

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        # Assuming observations might need unsqueeze for sequence length if not provided
        if len(observations.shape) == 2:
            observations = observations.unsqueeze(1) # Add seq dim
            
        lstm_out, _ = self.lstm(observations)
        # Take the output of the last time step
        last_out = lstm_out[:, -1, :]
        return self.linear(last_out)

class TCNFeatureExtractor(BaseFeaturesExtractor):
    """
    Temporal Convolutional Network feature extractor.
    Uses 1D causal convolutions with dilation.
    """
    def __init__(self, observation_space: gym.Space, features_dim: int = 256):
        super().__init__(observation_space, features_dim)
        
        state_dim = observation_space.shape[0]
        
        self.tcn = nn.Sequential(
            nn.Conv1d(in_channels=state_dim, out_channels=64, kernel_size=3, padding=2, dilation=1),
            nn.ReLU(),
            nn.Conv1d(in_channels=64, out_channels=128, kernel_size=3, padding=4, dilation=2),
            nn.ReLU(),
            nn.AdaptiveMaxPool1d(1)
        )
        
        self.linear = nn.Linear(128, features_dim)
        self._initialize_weights()
        
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv1d) or isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        if len(observations.shape) == 2:
             # (batch, features) -> (batch, features, seq=1)
            observations = observations.unsqueeze(2)
        elif len(observations.shape) == 3:
             # (batch, seq, features) -> (batch, features, seq)
            observations = observations.transpose(1, 2)
            
        conv_out = self.tcn(observations)
        conv_out = conv_out.squeeze(2)
        return self.linear(conv_out)

"""
dqn_agent.py
============
Step 2: a compact Deep Q-Network (PyTorch) for the HAPS-UAV MDP.

Design follows Arani et al. (2023): each UAV runs its own DQN with a shared
network, experience replay, an epsilon-greedy behaviour policy, and a separate
target network updated every N_T steps. The Q-target is
    y = r + gamma * max_a' Q(s', a'; theta^-).
"""

import random
from collections import deque

import numpy as np
import torch
import torch.nn as nn


class QNet(nn.Module):
    """Policy network: state -> Q-value per action (paper Fig. 3 style MLP)."""
    def __init__(self, state_dim, n_actions, hidden=(128, 64)):
        super().__init__()
        layers, d = [], state_dim
        for h in hidden:
            layers += [nn.Linear(d, h), nn.ReLU()]
            d = h
        layers += [nn.Linear(d, n_actions)]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class DQNAgent:
    def __init__(self, state_dim, n_actions,
                 gamma=0.95, lr=5e-4,
                 eps_start=1.0, eps_end=0.05, eps_decay=0.99,
                 buffer=50_000, batch=128, target_every=200, device="cpu", seed=0):
        torch.manual_seed(seed)
        self.n_actions = n_actions
        self.gamma = gamma
        self.batch = batch
        self.target_every = target_every
        self.eps = eps_start
        self.eps_end, self.eps_decay = eps_end, eps_decay
        self.device = device

        self.q = QNet(state_dim, n_actions).to(device)
        self.qt = QNet(state_dim, n_actions).to(device)
        self.qt.load_state_dict(self.q.state_dict())
        self.opt = torch.optim.Adam(self.q.parameters(), lr=lr)
        self.mem = deque(maxlen=buffer)
        self.learn_steps = 0

    def act(self, state):
        """Epsilon-greedy over a single state vector."""
        if random.random() < self.eps:
            return random.randrange(self.n_actions)
        with torch.no_grad():
            s = torch.as_tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
            return int(self.q(s).argmax(dim=1).item())

    def remember(self, s, a, r, s2, done):
        self.mem.append((s, a, r, s2, done))

    def train_step(self):
        if len(self.mem) < self.batch:
            return None
        batch = random.sample(self.mem, self.batch)
        s, a, r, s2, d = zip(*batch)
        s = torch.as_tensor(np.array(s), dtype=torch.float32, device=self.device)
        a = torch.as_tensor(a, dtype=torch.int64, device=self.device).unsqueeze(1)
        r = torch.as_tensor(r, dtype=torch.float32, device=self.device).unsqueeze(1)
        s2 = torch.as_tensor(np.array(s2), dtype=torch.float32, device=self.device)
        d = torch.as_tensor(d, dtype=torch.float32, device=self.device).unsqueeze(1)

        q = self.q(s).gather(1, a)
        with torch.no_grad():
            q_next = self.qt(s2).max(dim=1, keepdim=True)[0]
            y = r + self.gamma * q_next * (1.0 - d)
        loss = nn.functional.smooth_l1_loss(q, y)

        self.opt.zero_grad()
        loss.backward()
        self.opt.step()

        self.learn_steps += 1
        if self.learn_steps % self.target_every == 0:
            self.qt.load_state_dict(self.q.state_dict())
        return float(loss.item())

    def decay_eps(self):
        self.eps = max(self.eps_end, self.eps * self.eps_decay)

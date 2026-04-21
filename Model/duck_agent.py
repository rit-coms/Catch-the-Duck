import torch
import torch.nn as nn
from torch.distributions import Categorical
from Model.duck_model import ActorCritic
import os

# -----------------------------------------------------------
# Action definitions
# 0: idle
# 1: left
# 2: right
# 3: jump
# 4: jump + left
# 5: jump + right
# -----------------------------------------------------------
ACTION_COUNT = 6

# How many input features we're giving the model
# 2 relative pos + 2 duck velocity + 1 grounded + 8 rays = 13
STATE_DIM = 13

CHECKPOINT_PATH = "../Model/duck_weights.pt"

# PPO hyperparameters - these are intentionally conservative
# so training is stable even with noisy ray data
GAMMA = 0.99  # discount factor — how much future rewards matter
LR = 3e-4  # learning rate
CLIP_EPS = 0.2  # PPO clip epsilon — how much policy can change per update
EPOCHS = 4  # how many passes over experience per training call
BATCH_SIZE = 64


class DuckAgent:
    def __init__(self):
        self.model = ActorCritic(STATE_DIM, ACTION_COUNT)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=LR)

        # load saved weights if they exist
        if os.path.exists(CHECKPOINT_PATH):
            self.model.load_state_dict(torch.load(CHECKPOINT_PATH))
            print("[DuckAgent] Loaded saved weights.")
        else:
            print("[DuckAgent] No saved weights found, starting fresh.")

        # experience buffer — stores one full episode
        self.states = []
        self.actions = []
        self.log_probs = []
        self.rewards = []
        self.values = []
        self.dones = []

    def build_observation(self, ai_pos, ai_vel_x, ai_vel_y, ai_on_ground,
                          player_pos, ray_data, screen_w, screen_h):
        """
        Builds the flat observation vector fed into the model.
        All values are normalized to roughly [-1, 1] so the network
        doesn't have to deal with raw pixel values.
        """
        # relative position to player (normalized by screen size)
        delta_x = (player_pos[0] - ai_pos[0]) / screen_w
        delta_y = (player_pos[1] - ai_pos[1]) / screen_h

        # duck's own velocity (normalized by a reasonable max speed)
        vel_x = ai_vel_x / 10.0
        vel_y = ai_vel_y / 15.0

        # grounded flag
        grounded = 1.0 if ai_on_ground else 0.0

        # 8 ray distances normalized by the diagonal of the screen
        max_dist = (screen_w ** 2 + screen_h ** 2) ** 0.5
        ray_distances = [
            ray_data[i]["distance"] / max_dist for i in range(8)
        ]

        obs = [delta_x, delta_y, vel_x, vel_y, grounded] + ray_distances
        return torch.tensor(obs, dtype=torch.float32)

    def select_action(self, obs):
        """
        Runs the actor to sample an action.
        Returns action index and stores log_prob + value for training.
        """
        with torch.no_grad():
            probs, value = self.model(obs)

        dist = Categorical(probs)
        action = dist.sample()
        log_prob = dist.log_prob(action)

        # store for training later
        self.states.append(obs)
        self.actions.append(action)
        self.log_probs.append(log_prob)
        self.values.append(value.squeeze())

        return action.item()

    def store_reward(self, reward, done):
        """Call once per frame after the action is taken."""
        self.rewards.append(reward)
        self.dones.append(done)

    def compute_reward(self, ai_pos, player_pos, ai_on_ground, caught):
        """
        Reward signal for the duck:
        - Surviving each frame gives a small positive reward
        - Being far from the player gives a bonus
        - Getting caught gives a large penalty
        """
        if caught:
            return -10.0

        dist = ((ai_pos[0] - player_pos[0]) ** 2 +
                (ai_pos[1] - player_pos[1]) ** 2) ** 0.5

        # normalize distance reward — encourage staying far
        dist_reward = min(dist / 300.0, 1.0)

        # small survival reward every frame
        survival_reward = 0.01

        return survival_reward + dist_reward * 0.5

    def train(self):
        """
        PPO update — call this at the end of each round (on gameover).
        Uses all experience collected during the episode.
        """
        if len(self.rewards) < 2:
            self._clear_buffer()
            return

        # --- compute discounted returns ---
        returns = []
        G = 0
        for reward, done in zip(reversed(self.rewards), reversed(self.dones)):
            G = reward + GAMMA * G * (1 - done)
            returns.insert(0, G)

        returns = torch.tensor(returns, dtype=torch.float32)
        states = torch.stack(self.states)
        actions = torch.stack(self.actions)
        old_log_probs = torch.stack(self.log_probs).detach()
        values = torch.stack(self.values).detach()

        # normalize advantages — makes training more stable
        advantages = returns - values
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # --- PPO update loop ---
        for _ in range(EPOCHS):
            # shuffle into mini-batches
            indices = torch.randperm(len(states))
            for start in range(0, len(states), BATCH_SIZE):
                batch_idx = indices[start:start + BATCH_SIZE]

                batch_states = states[batch_idx]
                batch_actions = actions[batch_idx]
                batch_old_log_probs = old_log_probs[batch_idx]
                batch_advantages = advantages[batch_idx]
                batch_returns = returns[batch_idx]

                probs, values_new = self.model(batch_states)
                dist = Categorical(probs)
                new_log_probs = dist.log_prob(batch_actions)
                entropy = dist.entropy().mean()

                # PPO clipped objective
                ratio = (new_log_probs - batch_old_log_probs).exp()
                clipped = torch.clamp(ratio, 1 - CLIP_EPS, 1 + CLIP_EPS)
                actor_loss = -torch.min(ratio * batch_advantages,
                                        clipped * batch_advantages).mean()

                # critic tries to predict returns accurately
                critic_loss = nn.MSELoss()(values_new.squeeze(), batch_returns)

                # entropy bonus encourages exploration
                loss = actor_loss + 0.5 * critic_loss - 0.01 * entropy

                self.optimizer.zero_grad()
                loss.backward()
                # gradient clipping — prevents exploding gradients
                nn.utils.clip_grad_norm_(self.model.parameters(), 0.5)
                self.optimizer.step()

        print(f"[DuckAgent] Training done. "
              f"Steps: {len(self.rewards)} | "
              f"Mean reward: {sum(self.rewards) / len(self.rewards):.4f}")

        torch.save(self.model.state_dict(), CHECKPOINT_PATH)
        print(f"[DuckAgent] Weights saved to {CHECKPOINT_PATH}")

        self._clear_buffer()

    def _clear_buffer(self):
        self.states.clear()
        self.actions.clear()
        self.log_probs.clear()
        self.rewards.clear()
        self.values.clear()
        self.dones.clear()
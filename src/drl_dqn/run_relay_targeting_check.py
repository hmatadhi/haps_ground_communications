"""
Does the DQN's relay usage target poor-direct-SINR users / track the rain forecast?
10-seed check, same seeds/training as run_multiseed.py. Writes one row per seed to CSV
immediately after that seed finishes, so progress is visible without waiting for all 10.

Output: data/processed/dqn_multiseed/relay_targeting_check.csv
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import torch
from real_episode_env import RealEpisodeEnv, load_episodes
from run_multiseed import train_dqn, SEEDS

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                    "data", "processed", "dqn_multiseed", "relay_targeting_check.csv")


def main():
    train_eps = load_episodes("train")
    eval_eps = load_episodes("eval")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device}", flush=True)

    rows = []
    for seed in SEEDS:
        t0 = time.time()
        agent = train_dqn(seed, train_eps, device)
        agent.eps = 0.0
        print(f"  seed {seed}: training done in {time.time()-t0:.1f}s", flush=True)

        env = RealEpisodeEnv(eval_eps, seed=seed + 1000)
        np.random.seed(seed + 1000)

        relay_sinr, relay_rain, all_sinr, all_rain = [], [], [], []
        for _ in range(len(eval_eps)):
            s = env.reset()
            for _ in range(24):
                a = agent.act_batch(s)
                best_sinr = env._sinr_db.max(axis=1)
                rain_fc = env.ep["lstm_db"][env.t, 0]
                is_relay = a >= env.n_haps
                for k in range(env.n_users):
                    all_sinr.append(best_sinr[k]); all_rain.append(rain_fc)
                    if is_relay[k]:
                        relay_sinr.append(best_sinr[k]); relay_rain.append(rain_fc)
                s, r, done, info = env.step(a)

        n_relay = len(relay_sinr)
        row = {"seed": seed, "n_relay": n_relay, "frac_relay": n_relay / len(all_sinr),
               "mean_sinr_relay": float(np.mean(relay_sinr)) if n_relay else np.nan,
               "mean_sinr_all": float(np.mean(all_sinr)),
               "mean_rain_relay": float(np.mean(relay_rain)) if n_relay else np.nan,
               "mean_rain_all": float(np.mean(all_rain))}
        rows.append(row)
        print(f"  seed {seed}: {row}  (total {time.time()-t0:.1f}s)", flush=True)

        pd.DataFrame(rows).to_csv(OUT, index=False)

    print(f"\nWrote {OUT}", flush=True)


if __name__ == "__main__":
    main()

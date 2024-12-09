#! /bin/python3

import os, subprocess
import pandas as pd
import statistics

nn_range = range(10, 121, 10)
runs = 20
out_dir = "results/exp6/"
os.makedirs(out_dir, exist_ok=True)

# run experiments
procs = {}
for nn in nn_range:
    procs[nn] = {}
    for i in range(runs):
        print(f"launching exp: num_nodes={nn}, run={i}")
        exp_env = os.environ
        exp_env["Nn"] = f"{nn}"
        exp_env["out_dir"] = out_dir
        exp_env["Run"] = f"{i}"
        procs[nn][i] = subprocess.Popen(["python", "Main.py"], env=exp_env)

records = []
for nn in nn_range:
    chain_length = []
    stale_rate = []
    for i in range(runs):
        print(f"waiting for exp: num_nodes={nn}, run={i}")
        procs[nn][i].communicate()
        output_file = f"{nn}Nodes_Run{i}.xlsx"
        output_path = os.path.join(out_dir, output_file)
        df = pd.read_excel(output_path, sheet_name="SimOutput")
        chain_length.append(df["Main Blocks"].iloc[0])
        stale_rate.append(df["Stale Rate"].iloc[0] / 100)
    chain_length_mean = statistics.fmean(chain_length)
    chain_length_stdev = statistics.stdev(chain_length) if len(chain_length) > 1 else 0
    stale_rate_mean = statistics.fmean(stale_rate)
    stale_rate_stdev = statistics.stdev(stale_rate) if len(chain_length) > 1 else 0
    records.append([nn, chain_length_mean, chain_length_stdev, stale_rate_mean, stale_rate_stdev])

df = pd.DataFrame(records, columns=["num-nodes", "avg-chain-length", "std-dev-chain-length", "avg-stale-rate", "std-dev-stale-rate"])
print(df)

out_path = os.path.join(out_dir, "agg_results.csv")
df.to_csv(out_path)
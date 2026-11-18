
import numpy as np
import pandas as pd

from modules.simulation import simulate_checkout

lam = 64
mu = 20
counters = 4
duration = 4
seeds = range(30)

results = []

for seed in seeds:

    shortest = simulate_checkout(
        lam, mu, counters,
        duration_hours=duration,
        seed=seed,
        routing="shortest"
    )

    round_robin = simulate_checkout(
        lam, mu, counters,
        duration_hours=duration,
        seed=seed,
        routing="round_robin"
    )

    results.append({
        "Seed": seed,
        "Shortest workload": shortest["avg_wait_min"],
        "Round robin": round_robin["avg_wait_min"]
    })

df = pd.DataFrame(results)

shortest_avg = df["Shortest workload"].mean()
rr_avg = df["Round robin"].mean()

improvement = (
    (rr_avg - shortest_avg) / rr_avg * 100
    if rr_avg > 0 else 0
)

print("\nCHECQOUT - MULTIPLE SIMULATION RESULTS")
print("=" * 50)

print("Number of simulations:", len(seeds))
print("Average waiting time - Shortest workload:",
      round(shortest_avg, 2), "minutes")

print("Average waiting time - Round robin:",
      round(rr_avg, 2), "minutes")

print("Average waiting-time reduction:",
      round(improvement, 2), "%")

print("\nSTANDARD DEVIATION")
print("Shortest workload:",
      round(df["Shortest workload"].std(), 2), "minutes")

print("Round robin:",
      round(df["Round robin"].std(), 2), "minutes")

print("\nDETAILED RESULTS")
print(df.round(2).to_string(index=False))

df.to_csv("simulation_comparison.csv", index=False)

print("\nResults saved to simulation_comparison.csv")

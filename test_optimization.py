
from modules.optimization import optimize_counters

# Test input parameters
arrival_rate = 64
service_rate = 20
max_counters = 6

counter_cost = 150
waiting_cost = 30
max_wait = 8

# Run optimization
result = optimize_counters(
    arrival_rate,
    service_rate,
    max_counters,
    counter_cost,
    waiting_cost,
    max_wait
)

print("\nCHECQOUT - COUNTER OPTIMIZATION TEST")
print("=" * 45)

print("Feasible:", result["feasible"])

if result["feasible"]:

    print("Recommended counters:", result["recommended_c"])

    print("\nOPTIMAL CONFIGURATION")
    print("-" * 45)

    metrics = result["metrics"]

    print("Utilization:", round(metrics["rho"] * 100, 2), "%")
    print("Probability of waiting:", round(metrics["p_wait"] * 100, 2), "%")
    print("Average waiting time:", round(metrics["Wq"], 2), "minutes")
    print("Average queue length:", round(metrics["Lq"], 2))
    print("Average system time:", round(metrics["W"], 2), "minutes")
    print("Average system length:", round(metrics["L"], 2))

    print("\nFEASIBLE CONFIGURATIONS")
    print("-" * 45)

    for candidate in result["candidates"]:
        print(
            f"Counters: {candidate['c']} | "
            f"Utilization: {candidate['rho']*100:.2f}% | "
            f"Waiting time: {candidate['wq_minutes']:.2f} min | "
            f"Queue length: {candidate['lq']:.2f}"
        )

    print("\nTotal optimized cost:", round(result["objective_value"], 2))

    assert result["recommended_c"] == 4
    assert abs(metrics["rho"] - 0.8) < 1e-6
    assert metrics["Wq"] <= max_wait

    print("\nAll optimization checks passed!")

else:
    print("Message:", result["message"])

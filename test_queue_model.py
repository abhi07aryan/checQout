from modules.queue_model import mmc_metrics

arrival_rate = 48
service_rate = 20
counters = 3

result = mmc_metrics(
lam=arrival_rate,
mu=service_rate,
c=counters
)

print("CHECQOUT - QUEUE MODEL TEST")
print("----------------------------")

print("Stable:", result["stable"])
print("Utilization:", round(result["rho"] * 100, 2), "%")
print("Probability of waiting:",
round(result["p_wait"] * 100, 2), "%")
print("Average waiting time:",
round(result["wq_hours"] * 60, 2), "minutes")
print("Average queue length:",
round(result["lq"], 2))

assert result["stable"] is True
assert abs(result["rho"] - 0.8) < 1e-6

print("\nAll basic checks passed!")
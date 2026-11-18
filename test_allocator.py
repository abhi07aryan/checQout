
from modules.allocator import recommend_counter

queues = [3, 1, 2, 2]
service_rates = [20, 20, 20, 20]

# Remaining service time in minutes
remaining_minutes = [2, 1, 0, 2]

# Convert minutes to hours
remaining_hours = [
    value / 60 for value in remaining_minutes
]

result = recommend_counter(
    queues,
    service_rates,
    remaining_service=remaining_hours
)

print("\nCHECQOUT - CUSTOMER ALLOCATION TEST")
print("=" * 45)

print("Recommended counter:", result["counter_index"] + 1)

print("\nCOUNTER WORKLOADS")
for i, workload in enumerate(result["workloads_minutes"]):
    print(f"Counter {i + 1}: {workload:.2f} minutes")

print(
    "\nRecommended workload:",
    round(result["estimated_wait_minutes"], 2),
    "minutes"
)

assert result["counter_index"] == 1
assert abs(result["estimated_wait_minutes"] - 4) < 1e-6

print("\nAll allocation checks passed!")

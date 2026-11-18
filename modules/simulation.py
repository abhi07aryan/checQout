
import random
import simpy
import numpy as np


def simulate_checkout(
    lam,
    mu,
    counters,
    duration_hours=3,
    seed=7,
    routing="shortest"
):
    """
    SimPy simulation of independent checkout counters.

    Routing policies:
    1. shortest: Counter with the fewest expected customers
    2. round_robin: Customers distributed cyclically

    Calculates:
    - Average and maximum waiting time
    - Average time in system
    - Workload assigned to each counter
    - Allocation efficiency using Jain's Fairness Index
    """

    if lam <= 0 or mu <= 0 or counters < 1 or duration_hours <= 0:
        raise ValueError("Rates, duration and counter count must be positive.")

    if routing not in ("shortest", "round_robin"):
        raise ValueError("Routing must be 'shortest' or 'round_robin'.")

    # Reproducible random generators
    arrival_rng = random.Random(seed)
    service_rng = random.Random(seed + 1)

    # Generate arrival times
    arrival_times = []
    current_time = 0.0

    while True:
        current_time += arrival_rng.expovariate(lam)

        if current_time > duration_hours:
            break

        arrival_times.append(current_time)

    # Generate service times
    service_times = [
        service_rng.expovariate(mu)
        for _ in arrival_times
    ]

    env = simpy.Environment()

    resources = [
        simpy.Resource(env, capacity=1)
        for _ in range(counters)
    ]

    waits = []
    system_times = []

    # Track workload and customer allocation
    counter_workloads = [0.0] * counters
    counter_customers = [0] * counters

    def customer(customer_id, arrival_time, service_time):

        # Select counter
        if routing == "round_robin":
            idx = customer_id % counters

        else:
            idx = min(
                range(counters),
                key=lambda j: (
                    resources[j].count
                    + len(resources[j].queue)
                ) / mu
            )

        res = resources[idx]

        # Record assigned service workload
        counter_workloads[idx] += service_time * 60
        counter_customers[idx] += 1

        with res.request() as req:

            yield req

            service_start = env.now

            wait = service_start - arrival_time
            waits.append(wait)

            yield env.timeout(service_time)

            system_times.append(
                env.now - arrival_time
            )

    def arrival_process():

        for customer_id, arrival_time in enumerate(arrival_times):

            yield env.timeout(arrival_time - env.now)

            env.process(
                customer(
                    customer_id,
                    arrival_time,
                    service_times[customer_id]
                )
            )

    env.process(arrival_process())

    # Complete all customer processes
    env.run()

    # Calculate allocation efficiency
    total_workload = sum(counter_workloads)
    sum_squared = sum(w ** 2 for w in counter_workloads)

    if sum_squared > 0:
        allocation_efficiency = (
            total_workload ** 2
            / (counters * sum_squared)
        ) * 100
    else:
        allocation_efficiency = None

    return {
        "customers": len(waits),
        "arrivals": len(arrival_times),

        "avg_wait_min": (
            float(np.mean(waits) * 60)
            if waits else 0.0
        ),

        "avg_system_min": (
            float(np.mean(system_times) * 60)
            if system_times else 0.0
        ),

        "max_wait_min": (
            float(np.max(waits) * 60)
            if waits else 0.0
        ),

        "waits_min": [
            float(x * 60) for x in waits
        ],

        "system_times_min": [
            float(x * 60) for x in system_times
        ],

        "counter_workloads_min": counter_workloads,

        "counter_customers": counter_customers,

        "allocation_efficiency": (
            float(allocation_efficiency)
            if allocation_efficiency is not None
            else None
        )
    }

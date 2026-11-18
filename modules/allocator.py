
import math


def recommend_counter(
    queue_lengths,
    service_rates,
    remaining_service=None,
    active=None
):
    """
    Recommend the active counter with the lowest estimated workload.

    Parameters
    ----------
    queue_lengths : list
        Number of customers waiting at each counter.

    service_rates : list
        Service rate of each counter in customers/hour.

    remaining_service : list, optional
        Remaining service time of the customer currently being
        served at each counter, in hours.

    active : list, optional
        Whether each counter is active.

    Returns
    -------
    dict
        Recommended counter, estimated workload and workloads
        for all counters.
    """

    n = len(queue_lengths)

    if n == 0:
        raise ValueError("At least one counter is required.")

    if len(service_rates) != n:
        raise ValueError(
            "Queue lengths and service rates must have equal lengths."
        )

    if remaining_service is None:
        remaining_service = [0.0] * n

    if active is None:
        active = [True] * n

    if len(remaining_service) != n or len(active) != n:
        raise ValueError(
            "All counter input lists must have equal lengths."
        )

    workloads = []

    for j in range(n):

        if queue_lengths[j] < 0:
            raise ValueError("Queue length cannot be negative.")

        if remaining_service[j] < 0:
            raise ValueError("Remaining service time cannot be negative.")

        if not active[j]:
            workloads.append(float("inf"))
            continue

        mu = service_rates[j]

        if mu <= 0:
            workloads.append(float("inf"))
            continue

        # Remaining service time + service time for waiting customers
        workload = (
            remaining_service[j]
            + queue_lengths[j] / mu
        )

        workloads.append(workload)

    if all(math.isinf(value) for value in workloads):
        raise ValueError(
            "No active counter with a valid service rate."
        )

    # Select the counter with the lowest estimated workload
    recommended_index = min(
        range(n),
        key=lambda j: workloads[j]
    )

    recommended_workload = workloads[recommended_index]

    return {
        "counter_index": recommended_index,
        "estimated_wait_hours": recommended_workload,
        "estimated_wait_minutes": recommended_workload * 60,
        "workloads_hours": workloads,
        "workloads_minutes": [
            value * 60 for value in workloads
        ]
    }


def recommend_round_robin(number_of_counters, next_counter=0):
    """
    Return a counter index using Round Robin allocation.

    next_counter is zero-based.
    """

    if number_of_counters < 1:
        raise ValueError("At least one active counter is required.")

    if next_counter < 0:
        raise ValueError("Counter index cannot be negative.")

    selected_index = next_counter % number_of_counters

    next_index = (
        selected_index + 1
    ) % number_of_counters

    return {
        "counter_index": selected_index,
        "next_counter": next_index
    }

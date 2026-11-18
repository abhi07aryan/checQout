
import pulp
from modules.queue_model import mmc_metrics


def optimize_counters(
    lam,
    mu,
    max_c,
    counter_cost,
    wait_cost,
    max_wait
):
    """
    Optimize the number of active checkout counters.

    Parameters
    ----------
    lam : float
        Customer arrival rate (customers/hour).

    mu : float
        Service rate per counter (customers/hour).

    max_c : int
        Maximum available counters.

    counter_cost : float
        Operating cost per counter per hour.

    wait_cost : float
        Cost per customer-hour spent waiting.

    max_wait : float
        Maximum permitted average queue waiting time (minutes).

    Returns
    -------
    dict
        Feasibility, recommended counter count, queue metrics
        and total objective cost.
    """

    # --------------------------------------------------
    # 1. Validate inputs
    # --------------------------------------------------

    if lam < 0:
        raise ValueError("Arrival rate cannot be negative.")

    if mu <= 0:
        raise ValueError("Service rate must be greater than zero.")

    if max_c < 1:
        raise ValueError("At least one counter must be available.")

    if counter_cost < 0 or wait_cost < 0:
        raise ValueError("Cost values cannot be negative.")

    if max_wait < 0:
        raise ValueError("Maximum waiting time cannot be negative.")

    # --------------------------------------------------
    # 2. Generate feasible counter configurations
    # --------------------------------------------------

    candidates = []

    for c in range(1, int(max_c) + 1):

        # Stability condition: total service capacity > arrival rate
        if c * mu <= lam:
            continue

        metrics = mmc_metrics(lam, mu, c)

        if not metrics["stable"]:
            continue

        # Convert waiting time from hours to minutes
        wq_minutes = metrics["wq_hours"] * 60

        # Enforce maximum waiting-time requirement
        if wq_minutes <= max_wait:

            candidates.append({
                "c": c,
                "rho": metrics["rho"],
                "p_wait": metrics["p_wait"],
                "wq_hours": metrics["wq_hours"],
                "wq_minutes": wq_minutes,
                "lq": metrics["lq"]
            })

    # --------------------------------------------------
    # 3. Handle infeasible problem
    # --------------------------------------------------

    if not candidates:
        return {
            "feasible": False,
            "recommended_c": None,
            "metrics": {},
            "candidates": [],
            "message": "No counter configuration satisfies the constraints."
        }

    # --------------------------------------------------
    # 4. Define Integer Programming model
    # --------------------------------------------------

    model = pulp.LpProblem(
        "Checkout_Counter_Optimization",
        pulp.LpMinimize
    )

    # Binary variable:
    # x[c] = 1 if c counters are selected, otherwise 0

    x = {
        item["c"]: pulp.LpVariable(
            name=f"select_{item['c']}",
            cat="Binary"
        )
        for item in candidates
    }

    # --------------------------------------------------
    # 5. Objective function
    # --------------------------------------------------

    # Minimize:
    # Counter operating cost + Customer waiting cost
    #
    # For a one-hour planning interval:
    # Average number waiting = lambda * Wq = Lq
    #
    # Therefore, waiting cost = wait_cost * Lq

    model += pulp.lpSum(
        x[item["c"]] * (
            counter_cost * item["c"]
            + wait_cost * item["lq"]
        )
        for item in candidates
    )

    # --------------------------------------------------
    # 6. Constraints
    # --------------------------------------------------

    # Exactly one counter configuration must be selected

    model += pulp.lpSum(
        x[item["c"]]
        for item in candidates
    ) == 1

    # --------------------------------------------------
    # 7. Solve the optimization problem
    # --------------------------------------------------

    solver = pulp.PULP_CBC_CMD(msg=False)

    model.solve(solver)

    status = pulp.LpStatus[model.status]

    if status != "Optimal":
        return {
            "feasible": False,
            "recommended_c": None,
            "metrics": {},
            "message": f"Optimization failed. Solver status: {status}"
        }

    # --------------------------------------------------
    # 8. Extract optimal counter configuration
    # --------------------------------------------------

    selected_c = None

    for c in x:
        if pulp.value(x[c]) is not None and pulp.value(x[c]) > 0.5:
            selected_c = c
            break

    if selected_c is None:
        return {
            "feasible": False,
            "recommended_c": None,
            "metrics": {},
            "message": "No optimal counter configuration was selected."
        }

    selected = next(
        item for item in candidates
        if item["c"] == selected_c
    )

    # --------------------------------------------------
    # 9. Calculate remaining queue metrics
    # --------------------------------------------------

    rho = selected["rho"]
    p_wait = selected["p_wait"]
    wq_hours = selected["wq_hours"]
    lq = selected["lq"]

    # Average total time in the system (hours)
    w_hours = wq_hours + (1 / mu)

    # Average number of customers in the system
    l = lq + (lam / mu)

    # Convert time metrics into minutes
    w_minutes = w_hours * 60

    # --------------------------------------------------
    # 10. Calculate objective value
    # --------------------------------------------------

    total_cost = pulp.value(model.objective)

    # --------------------------------------------------
    # 11. Return results in dashboard-compatible format
    # --------------------------------------------------

    return {
        "feasible": True,

        "recommended_c": selected_c,

        "metrics": {
            "rho": rho,
            "p_wait": p_wait,
            "Wq": wq_hours * 60,
            "Lq": lq,
            "W": w_minutes,
            "L": l,
            "wq_hours": wq_hours,
            "w_hours": w_hours,
            "utilization": rho,
            "waiting_probability": p_wait,
            "average_waiting_time": wq_hours * 60,
            "average_queue_length": lq,
            "average_system_time": w_minutes,
            "average_system_length": l
        },

        "candidates": candidates,

        "objective_value": total_cost,
        "status": status
    }
import math

def mmc_metrics(lam: float, mu: float, c: int):
    """Return M/M/c steady-state metrics. Rates must use the same time unit."""
    if lam < 0 or mu <= 0 or c < 1:
        raise ValueError("Require lambda >= 0, mu > 0 and c >= 1.")
    capacity = c * mu
    rho = lam / capacity
    if rho >= 1:
        return {"stable": False, "rho": rho, "p_wait": None,
                "wq_hours": math.inf, "lq": math.inf,
                "w_hours": math.inf, "l_system": math.inf, "p0": None}
    a = lam / mu
    sum_terms = sum((a ** n) / math.factorial(n) for n in range(c))
    tail = (a ** c) / (math.factorial(c) * (1 - rho))
    p0 = 1.0 / (sum_terms + tail)
    p_wait = tail * p0
    wq = p_wait / (capacity - lam)
    lq = lam * wq
    w = wq + 1 / mu
    l_system = lam * w
    return {"stable": True, "rho": rho, "p_wait": p_wait, "wq_hours": wq,
            "lq": lq, "w_hours": w, "l_system": l_system, "p0": p0}

def candidate_table(lam: float, mu: float, max_c: int):
    rows=[]
    for c in range(1, max_c+1):
        m=mmc_metrics(lam,mu,c)
        rows.append({"counters":c,"stable":m["stable"],"utilization":m["rho"],
                     "wait_min":m["wq_hours"]*60 if m["stable"] else None,
                     "queue_length":m["lq"] if m["stable"] else None,
                     "p_wait":m["p_wait"]})
    return rows

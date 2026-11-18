"""
checQout - Intelligent Retail Queue Management & Customer Allocation System
MSL304 project model.

Modules
  1. Queueing analysis  : M/M/c, Erlang C, Little's Law
  2. Counter allocation : Integer Program (model A), one binary x[t,c] per interval
  3. Customer routing   : Model B (min expected wait assignment, queue estimates updated)
  4. Simulation         : discrete-event simulation, checQout vs. existing operations

Units: time in hours, rates in customers/hour, costs in currency/hour.
Run:   python checqout.py
"""
import heapq, math, random, statistics
from collections import deque
from dataclasses import dataclass, field

try:
    import numpy as np
    from scipy.optimize import milp, LinearConstraint, Bounds
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False


# ----------------------------------------------------------------- inputs
@dataclass
class Inputs:
    lam: list            # arrival rate lambda_t for each interval (cust/h)
    mu: float            # service rate per counter (cust/h)
    Cs: float            # cost per active counter per hour
    Cw: float            # waiting cost per customer-hour
    Cmax: int            # counters available
    Wmax: float          # max acceptable mean wait (hours)
    h: float = 1.0       # interval length (hours)
    target: float = 5/60 # service-level target wait (hours)
    start_hour: int = 9


# ------------------------------------------------- 1. queueing analysis
def erlang_c(c, a):
    """P(wait) for M/M/c, offered load a = lam/mu. Stable Erlang-B recursion."""
    if a >= c:
        return 1.0
    B = 1.0
    for k in range(1, c + 1):
        B = a * B / (k + a * B)
    rho = a / c
    return B / (1 - rho * (1 - B))

def mmc_metrics(lam, mu, c):
    """Returns dict of steady-state metrics; inf if unstable (c*mu <= lam)."""
    if c * mu <= lam:
        return dict(rho=lam / (c * mu), Pw=1.0, Wq=math.inf, W=math.inf, Lq=math.inf, L=math.inf)
    a, rho = lam / mu, lam / (c * mu)
    Pw = erlang_c(c, a)
    Wq = Pw / (c * mu - lam)
    return dict(rho=rho, Pw=Pw, Wq=Wq, W=Wq + 1 / mu,
                Lq=lam * Wq,                 # Little's Law  Lq = lam * Wq
                L=lam * (Wq + 1 / mu))       # Little's Law  L  = lam * W


# --------------------------------------- 2. counter optimisation (model A)
def optimise_counters(p: Inputs):
    """min sum_t sum_c x_tc [Cs*c*h + Cw*lam_t*h*Wq(t,c)]
       s.t. sum_c x_tc = 1, Wq<=Wmax, sum c*x_tc<=Cmax, c*mu>lam_t, x binary.
    Stability and Wmax constraints are linear in x for fixed (t,c) data, so
    infeasible (t,c) pairs get upper bound 0. Solved with MILP (HiGHS) if
    scipy is available, else by exact enumeration (the problem is separable in t)."""
    T, C = len(p.lam), p.Cmax
    cost = [[math.inf] * (C + 1) for _ in range(T)]
    for t in range(T):
        for c in range(1, C + 1):
            m = mmc_metrics(p.lam[t], p.mu, c)
            if m["Wq"] <= p.Wmax:                       # also excludes unstable
                cost[t][c] = p.Cs * c * p.h + p.Cw * p.lam[t] * p.h * m["Wq"]
    infeasible = [t for t in range(T) if all(math.isinf(v) for v in cost[t])]
    if infeasible:
        raise ValueError(f"Infeasible intervals {infeasible}: raise Cmax or Wmax.")

    if HAVE_SCIPY:
        n = T * C
        obj = np.array([cost[t][c] if not math.isinf(cost[t][c]) else 0
                        for t in range(T) for c in range(1, C + 1)])
        ub = np.array([0 if math.isinf(cost[t][c]) else 1
                       for t in range(T) for c in range(1, C + 1)])
        A = np.zeros((T, n))
        for t in range(T):
            A[t, t * C:(t + 1) * C] = 1                 # one configuration per interval
        res = milp(obj, constraints=LinearConstraint(A, 1, 1),
                   integrality=np.ones(n), bounds=Bounds(0, ub))
        x = res.x.round().astype(int).reshape(T, C)
        sched = [int(np.argmax(x[t])) + 1 for t in range(T)]
    else:
        sched = [min(range(1, C + 1), key=lambda c: cost[t][c]) for t in range(T)]
    return sched, sum(cost[t][sched[t]] for t in range(T))


# ------------------------------------ 3. customer-to-counter routing (B)
def assign_customer(queue_len, mu_j, active):
    """Model B for one arriving customer: pick active j minimising W_j.
    W_j = (Q_j + 1)/mu_j : the customer's own service is included so that empty
    counters are still ranked by speed. Q_j is refreshed after every assignment,
    which is what stops a single counter being overloaded."""
    best = min(active, key=lambda j: (queue_len[j] + 1) / mu_j[j])
    return best

def assign_batch(queue_len, mu_j, active, n_new):
    """Assign n_new simultaneous arrivals sequentially, updating estimates."""
    q, out = list(queue_len), []
    for _ in range(n_new):
        j = assign_customer(q, mu_j, active)
        q[j] += 1
        out.append(j)
    return out


# ----------------------------------------------- 4. discrete-event simulation
def simulate(p: Inputs, sched, policy, seed):
    """policy: 'jsew' (checQout routing) or 'random' (customers choose blindly).
    Counters 0..sched[k]-1 are open in interval k. A closed counter accepts no
    new customers but finishes those already in its queue."""
    rng = random.Random(seed)
    T, C = len(p.lam), p.Cmax
    arrivals = []
    for k in range(T):                                  # piecewise-constant Poisson
        t, end = k * p.h, (k + 1) * p.h
        while True:
            t += rng.expovariate(p.lam[k])
            if t >= end: break
            arrivals.append(t)
    mu_j = [p.mu] * C
    q = [deque() for _ in range(C)]
    busy = [False] * C
    qlen = [0] * C                                      # waiting + in service
    deps, waits, busy_time = [], [], 0.0
    served = [0] * C
    area_q, nwait, last = 0.0, 0, 0.0

    def start(j, now):
        nonlocal busy_time
        s = rng.expovariate(mu_j[j])
        busy[j] = True; busy_time += s
        heapq.heappush(deps, (now + s, j))

    i, N = 0, len(arrivals)
    while i < N or deps:
        if i < N and (not deps or arrivals[i] <= deps[0][0]):
            now = arrivals[i]; i += 1
            area_q += nwait * (now - last); last = now
            active = range(sched[min(int(now / p.h), T - 1)])
            j = assign_customer(qlen, mu_j, active) if policy == "jsew" \
                else rng.choice(list(active))
            qlen[j] += 1
            if not busy[j]:
                waits.append(0.0); start(j, now)
            else:
                q[j].append(now); nwait += 1
        else:
            now, j = heapq.heappop(deps)
            area_q += nwait * (now - last); last = now
            busy[j] = False; qlen[j] -= 1; served[j] += 1
            if q[j]:
                arr = q[j].popleft(); nwait -= 1
                waits.append(now - arr); start(j, now)

    horizon = last
    open_hours = sum(sched) * p.h
    # Jain's index on customers served per open-hour, so counters open for
    # different durations are compared fairly
    rate = [served[j] / (p.h * sum(c > j for c in sched)) for j in range(max(sched))]
    jain = sum(rate) ** 2 / (len(rate) * sum(r * r for r in rate))
    return dict(
        avg_wait_min=60 * statistics.mean(waits),
        avg_queue_len=area_q / horizon,
        utilisation=busy_time / open_hours,
        cost=p.Cs * open_hours + p.Cw * sum(waits),
        service_level=sum(w <= p.target for w in waits) / len(waits),
        alloc_eff=jain,                                 # Jain's fairness index (1 = even)
        customers=len(waits))

def replicate(p, sched, policy, reps=50, seed0=1000):
    runs = [simulate(p, sched, policy, seed0 + r) for r in range(reps)]
    out = {}
    for k in runs[0]:
        v = [r[k] for r in runs]
        sd = statistics.stdev(v)
        out[k] = (statistics.mean(v), 1.96 * sd / math.sqrt(reps))
    return out


# ----------------------------------------------------------------- driver
def main():
    p = Inputs(
        lam=[40, 55, 70, 90, 110, 95, 80, 85, 120, 150, 130, 80],  # 09:00-21:00
        mu=25.0,            # 2.4 min per customer per counter
        Cs=300.0,           # cost / active counter-hour
        Cw=150.0,           # cost / customer-hour of waiting
        Cmax=10, Wmax=3 / 60)   # mean wait <= 3 min

    # ---- Step 1-2: analytic model + IP
    sched, z = optimise_counters(p)
    print("=== Counter allocation (Integer Program) ===")
    print(f"{'Time':>6} {'lambda':>7} {'c*':>3} {'rho':>6} {'P(wait)':>8} {'Wq(min)':>8} {'Lq':>6}")
    for t, c in enumerate(sched):
        m = mmc_metrics(p.lam[t], p.mu, c)
        print(f"{p.start_hour + t:02d}:00 {p.lam[t]:7.0f} {c:3d} {m['rho']:6.2f} "
              f"{m['Pw']:8.2f} {60 * m['Wq']:8.2f} {m['Lq']:6.2f}")
    print(f"Optimal analytic cost Z = {z:,.0f}   (solver: {'MILP/HiGHS' if HAVE_SCIPY else 'enumeration'})\n")

    # ---- Step 3 demo: routing
    print("=== Routing demo: queues [3,0,2,1], equal mu, 5 arrivals ===")
    print("assigned to counters:", assign_batch([3, 0, 2, 1], [p.mu] * 4, range(4), 5), "\n")

    # ---- Step 4: simulation, checQout vs existing practice
    base_c = 7          # existing: fixed staffing all day, customers pick a queue blindly
    systems = {
        "Existing (7 fixed, random choice)": ([base_c] * len(p.lam), "random"),
        "Fixed 7 + checQout routing":        ([base_c] * len(p.lam), "jsew"),
        "checQout (IP counters + routing)":  (sched, "jsew"),
    }
    results = {name: replicate(p, s, pol) for name, (s, pol) in systems.items()}
    print("=== Simulation (50 replications, mean +/- 95% CI) ===")
    rows = [("avg_wait_min", "Avg wait (min)"), ("avg_queue_len", "Avg queue length"),
            ("utilisation", "Counter utilisation"), ("cost", "Total cost"),
            ("service_level", "Served within 5 min"), ("alloc_eff", "Allocation efficiency")]
    print(f"{'Metric':<24}" + "".join(f"{n:>38}" for n in results))
    for k, label in rows:
        line = f"{label:<24}"
        for n in results:
            m, ci = results[n][k]
            line += f"{m:>28.2f} +/- {ci:<6.2f}"
        print(line)

    e, c_ = results["Existing (7 fixed, random choice)"], results["checQout (IP counters + routing)"]
    print(f"\nchecQout vs existing: wait {100 * (1 - c_['avg_wait_min'][0] / e['avg_wait_min'][0]):.0f}% lower, "
          f"cost {100 * (1 - c_['cost'][0] / e['cost'][0]):.0f}% lower.")

if __name__ == "__main__":
    main()
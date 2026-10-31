"""Reference logic shared by test cases and the prototype (small, brute-force/heuristic versions)."""
import itertools, statistics

# ---------- Module 1: SOPT inventory simulation (periodic review (S,T), perishable) ----------
GINGER_DEMAND = [15,14,5,1,8,6,13,12,3,9,6,5,13,13,6,7,12,3,8,6,6,15,9,10,3,8,6,13,7,8]

def simulate(demand, S, T=1, shelf_life=3, pattern="FIFO", lead_time=0, h=0.1, w=1.5, l=1.5, trace=False):
    """Each batch = [units, age]. Order up to S every T days, arrives after lead_time days."""
    stock, pipeline = [], []
    tot_inv = shrink = oos = sold = 0
    daily = []
    for t, d in enumerate(demand):
        # receive
        arr = [q for (due, q) in pipeline if due == t]
        pipeline = [(due, q) for (due, q) in pipeline if due != t]
        for q in arr:
            if q > 0: stock.append([q, 0])
        # order (review)
        if t % T == 0:
            pos = sum(b[0] for b in stock) + sum(q for _, q in pipeline)
            q = max(0, S - pos)
            if lead_time == 0:
                if q > 0: stock.append([q, 0])
            else:
                pipeline.append((t + lead_time, q))
        # serve demand
        order = sorted(stock, key=lambda b: -b[1]) if pattern == "FIFO" else sorted(stock, key=lambda b: b[1])
        rem = d
        for b in order:
            take = min(b[0], rem); b[0] -= take; rem -= take; sold += take
            if rem == 0: break
        oos += rem
        day_lost = rem
        stock = [b for b in stock if b[0] > 0]
        # age & expire
        for b in stock: b[1] += 1
        day_shrink = sum(b[0] for b in stock if b[1] >= shelf_life)
        shrink += day_shrink
        stock = [b for b in stock if b[1] < shelf_life]
        tot_inv += sum(b[0] for b in stock)
        daily.append(dict(day=t + 1, demand=d, ending_inventory=sum(b[0] for b in stock), shrink=day_shrink, lost=day_lost))
    n = len(demand)
    cost = h * tot_inv + w * shrink + l * oos
    return dict(S=S, T=T, avg_inv=round(tot_inv / n, 2), shrink=shrink, oos=oos, sold=sold,
                fill_rate=round(sold / sum(demand), 3) if sum(demand) else 1.0, cost=round(cost, 2),
                **({"daily": daily} if trace else {}))

def sopt_search(demand, pattern, S_range=range(0, 41), **kw):
    """Local search on S, using min-ending-inventory move (the paper's Delta move) from a start point."""
    S = int(statistics.mean(demand) * 2)
    best = simulate(demand, S, pattern=pattern, **kw)
    improved = True
    while improved:
        improved = False
        for cand in (best["S"] - 1, best["S"] + 1):
            if cand in S_range:
                r = simulate(demand, cand, pattern=pattern, **kw)
                if r["cost"] < best["cost"]:
                    best, improved = r, True
    return best

# ---------- Module 2: multiproduct promotional pricing (Appendix A) ----------
PRICING = {
    "products": {"Rice 5kg": 6.0, "Cooking oil 1L": 2.2, "Green tea 250g": 3.0},  # procurement cost c_i
    # (product, campaign, price point) -> (price p, predicted sales q)
    "options": {
        ("Rice 5kg", "20% off", "k1"): (8.0, 120), ("Rice 5kg", "20% off", "k2"): (7.5, 150),
        ("Rice 5kg", "Spend-100 coupon", "k1"): (8.5, 110),
        ("Cooking oil 1L", "20% off", "k1"): (3.2, 300), ("Cooking oil 1L", "20% off", "k2"): (2.9, 380),
        ("Cooking oil 1L", "Spend-100 coupon", "k1"): (3.4, 260),
        ("Green tea 250g", "20% off", "k1"): (4.8, 90),
        ("Green tea 250g", "Spend-100 coupon", "k1"): (5.0, 85), ("Green tea 250g", "Spend-100 coupon", "k2"): (4.4, 130),
    },
    "N": {"20% off": 2, "Spend-100 coupon": 2},
    "r_star": 0.22,
}

def eval_pricing(choice, d=PRICING):
    rev = sum(d["options"][c][0] * d["options"][c][1] for c in choice)
    prof = sum((d["options"][c][0] - d["products"][c[0]]) * d["options"][c][1] for c in choice)
    margin = prof / rev
    counts = {}
    for c in choice: counts[c[1]] = counts.get(c[1], 0) + 1
    feasible = margin >= d["r_star"] and all(counts.get(j, 0) <= n for j, n in d["N"].items())
    return dict(choice=choice, revenue=round(rev, 1), profit=round(prof, 1), margin=round(margin, 4), feasible=feasible)

def solve_pricing_bruteforce(d=PRICING):
    per = {i: [o for o in d["options"] if o[0] == i] for i in d["products"]}
    sols = [eval_pricing(c, d) for c in itertools.product(*per.values())]
    feas = [s for s in sols if s["feasible"]]
    return max(feas, key=lambda s: s["revenue"]) if feas else None, sols

# ---------- Module 3: markdown + recommendation ranking (Appendix B) ----------
RANK = {
    "products": {  # price p, salvage s, inventory I
        "Ginger": (1.2, 0.2, 2), "Spinach": (1.5, 0.1, 1), "Milk 1L": (1.8, 0.6, 3), "Strawberries": (4.0, 0.5, 1)},
    "users": ["U1", "U2", "U3"],
    "ctcvr": {  # P(click and buy)
        ("U1","Ginger"):0.6, ("U1","Spinach"):0.5, ("U1","Milk 1L"):0.3, ("U1","Strawberries"):0.4,
        ("U2","Ginger"):0.2, ("U2","Spinach"):0.7, ("U2","Milk 1L"):0.6, ("U2","Strawberries"):0.5,
        ("U3","Ginger"):0.5, ("U3","Spinach"):0.3, ("U3","Milk 1L"):0.4, ("U3","Strawberries"):0.8},
    "ctr": {  # click-through rate
        ("U1","Ginger"):0.7, ("U1","Spinach"):0.6, ("U1","Milk 1L"):0.5, ("U1","Strawberries"):0.6,
        ("U2","Ginger"):0.3, ("U2","Spinach"):0.8, ("U2","Milk 1L"):0.7, ("U2","Strawberries"):0.6,
        ("U3","Ginger"):0.6, ("U3","Spinach"):0.4, ("U3","Milk 1L"):0.5, ("U3","Strawberries"):0.9},
    "S_t": 2, "ctr_star": 2.5,
}

def eval_rank(x, d=RANK):
    P = d["products"]; obj = 0; ok = True
    for k,(p,s,I) in P.items():
        exp_sold = sum(d["ctcvr"][(t,k)] for t in d["users"] if (t,k) in x)
        obj += exp_sold * p - (I - exp_sold) * s
        if exp_sold > I + 1e-9: ok = False
    if sum(d["ctr"][c] for c in x) < d["ctr_star"]: ok = False
    for t in d["users"]:
        if sum(1 for c in x if c[0] == t) > d["S_t"]: ok = False
    return round(obj, 3), ok

def solve_rank_bruteforce(d=RANK):
    cells = [(t,k) for t in d["users"] for k in d["products"]]
    best = None
    for mask in range(1 << len(cells)):
        x = {cells[i] for i in range(len(cells)) if mask >> i & 1}
        obj, ok = eval_rank(x, d)
        if ok and (best is None or obj > best[0]): best = (obj, x)
    return best

def rank_scores(alpha, d=RANK):
    """Step-3 rule: score = ctcvr*(p+s) - alpha_k*ctcvr ; show top S_t per user."""
    out = {}
    for t in d["users"]:
        sc = {k: round(d["ctcvr"][(t,k)]*(p+s) - alpha.get(k,0)*d["ctcvr"][(t,k)], 3) for k,(p,s,I) in d["products"].items()}
        out[t] = sorted(sc.items(), key=lambda kv: -kv[1])
    return out

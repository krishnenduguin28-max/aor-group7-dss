import copy, pytest
from model_core import *

def test_inv01():
    r = sopt_search(GINGER_DEMAND, "FIFO"); assert (r["S"], r["avg_inv"], r["shrink"], r["oos"], r["fill_rate"], r["cost"]) == (14, 5.73, 0, 2, 0.992, 20.2)
def test_inv02():
    r = sopt_search(GINGER_DEMAND, "LIFO"); assert (r["S"], r["avg_inv"], r["shrink"], r["oos"], r["cost"]) == (12, 3.5, 17, 12, 54.0)
def test_inv03():
    f, l = sopt_search(GINGER_DEMAND, "FIFO"), sopt_search(GINGER_DEMAND, "LIFO"); assert l["cost"] > f["cost"] and l["shrink"] > f["shrink"]
def test_inv04():
    r = simulate(GINGER_DEMAND, 24); assert (r["shrink"], r["oos"], r["cost"]) == (30, 0, 89.0)
def test_inv05():
    r = simulate(GINGER_DEMAND, 10); assert (r["oos"], r["fill_rate"], r["cost"]) == (30, 0.88, 53.0)
def test_inv06():
    r = sopt_search([0]*30, "FIFO"); assert (r["S"], r["cost"]) == (0, 0)
def validate(d):
    if any(x < 0 for x in d): raise ValueError("negative demand")
def test_inv07():
    d = GINGER_DEMAND.copy(); d[4] = -3
    with pytest.raises(ValueError): validate(d)
def test_pr01():
    b, _ = solve_pricing_bruteforce(); assert [c[2] for c in b["choice"]] == ["k2","k2","k2"] and (b["revenue"], b["profit"], b["margin"]) == (2799.0, 673.0, 0.2404)
def test_pr02():
    d = copy.deepcopy(PRICING); d["r_star"] = .26; b, _ = solve_pricing_bruteforce(d); assert b["choice"][1][2] == "k1" and (b["revenue"], b["margin"]) == (2657.0, 0.2661)
def test_pr03():
    d = copy.deepcopy(PRICING); d["N"]["20% off"] = 1; b, _ = solve_pricing_bruteforce(d); assert b["choice"][0][1] == "Spend-100 coupon" and (b["revenue"], b["margin"]) == (2609.0, 0.2771)
def test_pr04():
    c = (("Rice 5kg","20% off","k2"),("Cooking oil 1L","20% off","k2"),("Green tea 250g","20% off","k1")); r = eval_pricing(c); assert r["revenue"] == 2659.0 and not r["feasible"]
def test_pr05():
    d = copy.deepcopy(PRICING); d["r_star"] = .35; assert solve_pricing_bruteforce(d)[0] is None
def test_rk01():
    obj, x = solve_rank_bruteforce(); assert obj == 5.88 and x == {("U1","Ginger"),("U1","Milk 1L"),("U2","Spinach"),("U2","Milk 1L"),("U3","Strawberries"),("U3","Milk 1L")}
def test_rk02():
    d = copy.deepcopy(RANK); d["S_t"] = 1; assert solve_rank_bruteforce(d) is None
def test_rk03():
    assert rank_scores({})["U3"][0] == ("Strawberries", 3.6)
def test_rk04():
    r = rank_scores({"Strawberries":3.0,"Spinach":1.0})["U1"]; assert r[:3] == [("Ginger",0.84),("Milk 1L",0.72),("Strawberries",0.6)]

"""Alibaba-style Integrated Inventory, Pricing & Markdown-Recommendation DSS — AOR Group 7 prototype.
Run locally:  streamlit run app.py
Deploy:       push app.py, model_core.py, requirements.txt to GitHub -> share.streamlit.io -> New app.
"""
import copy
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from model_core import (GINGER_DEMAND, PRICING, RANK, simulate, sopt_search, solve_pricing_bruteforce,
                        eval_pricing, solve_rank_bruteforce, rank_scores, eval_rank)

st.set_page_config(page_title="Omnichannel Retail DSS", page_icon="🛒", layout="wide")
ACC, ACC2, WARN = "#2563eb", "#f97316", "#dc2626"

st.sidebar.title("Retail Optimisation DSS")
st.sidebar.caption("AOR Final Project · Group 7 · after Deng et al. (2023), INFORMS J. Applied Analytics 53(1)")
page = st.sidebar.radio("Module", ["Overview", "M1 · Inventory (SOPT)", "M2 · Promotional pricing", "M3 · Markdown ranking"])
st.sidebar.markdown("---")
st.sidebar.caption("Hard-coded sample data (D1–D3 in the wiki). Small instances are solved exactly; "
                   "production would use the heuristics in the TDD.")

# ---------------------------------------------------------------- Overview
if page == "Overview":
    st.title("Integrated inventory, pricing and markdown-ranking DSS")
    st.write("One forecast feeds three optimisation modules. Pick a module on the left to see its input data, run it, and view the results.")
    c = st.columns(4)
    c[0].metric("Shrinkage rate (Freshippo)", "3.7%", "-0.8 pp", delta_color="inverse")
    c[1].metric("Out-of-stock rate", "3.8%", "-1.0 pp", delta_color="inverse")
    c[2].metric("Inventory staff", "~70", "-130", delta_color="inverse")
    c[3].metric("Annual benefit", "$42M cost · $110M GMV · $13M profit")
    st.caption("Paper results, Aug 2018–Jul 2019 vs Aug 2020–Jul 2021 (Table 3, Table 4).")
    st.subheader("Data flow")
    st.graphviz_chart("""
    digraph { rankdir=LR; node [shape=box style="rounded,filled" fillcolor="#eef2ff" color="#94a3b8" fontname=Helvetica];
      F [label="Falcon demand forecast\n+ DML predicted sales"];
      M1 [label="M1 SOPT inventory\n(S,T) / (s,S) per SKU"]; M2 [label="M2 Promotional pricing\nprice point per product"];
      M3 [label="M3 Markdown ranking\ntop-S products per user"];
      D [label="Dashboards & APIs\nstore · pricing · app" fillcolor="#fff7ed"];
      F->M1; F->M2; F->M3; M1->M3 [label="stock I_k"]; M1->D; M2->D; M3->D; }""")
    a, b = st.columns(2)
    t4 = pd.DataFrame({"Metric": ["Shrinkage rate", "Shrinkage rate", "Out-of-stock rate", "Out-of-stock rate"],
                       "Period": ["Aug 2018–Jul 2019", "Aug 2020–Jul 2021"] * 2, "%": [4.5, 3.7, 4.8, 3.8]})
    a.plotly_chart(px.bar(t4, x="Metric", y="%", color="Period", barmode="group", text="%",
                          color_discrete_sequence=["#94a3b8", ACC], title="Freshippo before vs after (paper Table 4)")
                   .update_layout(height=340), use_container_width=True)
    t2 = pd.DataFrame({"Method": ["Falcon", "Wavenet", "DeepAR", "MA28", "Prophet"], "1 − WMAPE (%)": [52.22, 43.38, 37.39, 35.77, 29.41]})
    b.plotly_chart(px.bar(t2, x="1 − WMAPE (%)", y="Method", orientation="h", text="1 − WMAPE (%)",
                          color=t2["Method"].eq("Falcon").map({True: "Falcon", False: "Benchmark"}),
                          color_discrete_map={"Falcon": ACC, "Benchmark": "#cbd5e1"},
                          title="Forecast accuracy feeding the DSS (paper Table 2)")
                   .update_layout(height=340, showlegend=False, yaxis=dict(categoryorder="total ascending")), use_container_width=True)

# ---------------------------------------------------------------- M1
elif page == "M1 · Inventory (SOPT)":
    st.title("M1 · Inventory policy for a perishable SKU")
    ex = st.selectbox("Example", ["A · Ginger, 30 days (paper Fig. 8 shape)", "B · Ginger with a festival spike (days 20–24 ×1.8)"])
    demand = GINGER_DEMAND.copy()
    if ex.startswith("B"):
        demand = [round(d * 1.8) if 19 <= i <= 23 else d for i, d in enumerate(demand)]
    st.subheader("1 · Input data")
    a, b = st.columns([2, 1])
    with a:
        dfin = pd.DataFrame({"day": range(1, 31), "demand": demand})
        st.plotly_chart(px.bar(dfin, x="day", y="demand", color_discrete_sequence=["#94a3b8"]).update_layout(height=250, margin=dict(t=10)),
                        use_container_width=True)
    with b:
        L = st.number_input("Shelf life (days)", 1, 10, 3)
        lt = st.number_input("Lead time (days)", 0, 5, 0)
        h = st.number_input("Holding cost / unit / day", 0.0, 5.0, 0.1, 0.05)
        w = st.number_input("Shrinkage cost / unit", 0.0, 10.0, 1.5, 0.1)
        l = st.number_input("Lost-sale cost / unit", 0.0, 10.0, 1.5, 0.1)
    if any(d < 0 for d in demand):
        st.error("Demand cannot be negative."); st.stop()
    kw = dict(shelf_life=L, lead_time=lt, h=h, w=w, l=l)
    st.subheader("2 · Run SOPT")
    st.caption("Local search over S using the simulator (re-runs automatically when any input changes).")
    if True:
        res = {p: sopt_search(demand, p, **kw) for p in ["FIFO", "LIFO"]}
        st.subheader("3 · Results")
        cols = st.columns(2)
        for col, p in zip(cols, ["FIFO", "LIFO"]):
            r = res[p]
            col.markdown(f"**{p}** — {'online pickers take oldest' if p=='FIFO' else 'store shoppers take freshest'}")
            m = col.columns(4)
            m[0].metric("Best S", r["S"]); m[1].metric("Avg inventory", r["avg_inv"])
            m[2].metric("Shrinkage", r["shrink"]); m[3].metric("Stock-outs", r["oos"])
            col.caption(f"Fill rate {r['fill_rate']:.1%} · total cost {r['cost']}")
        tr = []
        for p in ["FIFO", "LIFO"]:
            d = simulate(demand, res[p]["S"], pattern=p, trace=True, **kw)["daily"]
            tr += [dict(x, pattern=f"{p} (S={res[p]['S']})") for x in d]
        fig = px.bar(pd.DataFrame(tr), x="day", y="ending_inventory", color="pattern", barmode="group",
                     color_discrete_sequence=[ACC, ACC2], title="Daily ending inventory at the best policy")
        st.plotly_chart(fig.update_layout(height=320), use_container_width=True)
        curve = [dict(S=S, cost=simulate(demand, S, pattern=p, **kw)["cost"], pattern=p) for p in ["FIFO", "LIFO"] for S in range(4, 31)]
        fig2 = px.line(pd.DataFrame(curve), x="S", y="cost", color="pattern", markers=True,
                       color_discrete_sequence=[ACC, ACC2], title="Total cost vs order-up-to level S (simulation)")
        st.plotly_chart(fig2.update_layout(height=320), use_container_width=True)
        st.info(f"Recommendation: set S = {res['FIFO']['S']} for online (FIFO) stock and S = {res['LIFO']['S']} "
                f"for shelf (LIFO) stock. LIFO costs {res['LIFO']['cost'] / max(res['FIFO']['cost'], 0.01):.1f}× more because "
                "older packs expire on the shelf — consistent with the paper's FIFO vs LIFO finding.")

# ---------------------------------------------------------------- M2
elif page == "M2 · Promotional pricing":
    st.title("M2 · Multiproduct promotional pricing")
    ex = st.selectbox("Example", ["A · Base campaign (r* = 22%, N = 2 per campaign)",
                                  "B · Finance tightens margin (r* = 26%) and '20% off' capped at 1"])
    d = copy.deepcopy(PRICING)
    if ex.startswith("B"):
        d["r_star"], d["N"]["20% off"] = 0.26, 1
    st.subheader("1 · Input data")
    grid = pd.DataFrame([dict(product=i, campaign=j, price_point=k, price=v[0], predicted_sales=v[1],
                              cost=d["products"][i], revenue=v[0] * v[1]) for (i, j, k), v in d["options"].items()])
    st.dataframe(grid, use_container_width=True, hide_index=True)
    c = st.columns(3)
    d["r_star"] = c[0].slider("Target margin r*", 0.10, 0.40, d["r_star"], 0.01)
    d["N"]["20% off"] = c[1].number_input("Max price points in '20% off'", 0, 3, d["N"]["20% off"])
    d["N"]["Spend-100 coupon"] = c[2].number_input("Max in 'Spend-100 coupon'", 0, 3, d["N"]["Spend-100 coupon"])
    st.subheader("2 · Run optimiser")
    best, sols = solve_pricing_bruteforce(d)
    st.subheader("3 · Results")
    if best is None:
        st.error("No feasible price plan meets the margin target and campaign caps. Lower r* or raise N_j.")
    else:
        m = st.columns(4)
        m[0].metric("Revenue (GMV)", f"{best['revenue']:,.0f}"); m[1].metric("Profit", f"{best['profit']:,.0f}")
        m[2].metric("Margin", f"{best['margin']:.2%}", f"{best['margin'] - d['r_star']:+.2%} vs target")
        m[3].metric("Plans evaluated", f"{len(sols)} ({sum(s['feasible'] for s in sols)} feasible)")
        plan = pd.DataFrame([dict(product=i, campaign=j, price_point=k, price=d["options"][(i, j, k)][0],
                                  predicted_sales=d["options"][(i, j, k)][1]) for (i, j, k) in best["choice"]])
        st.markdown("**Recommended price plan**")
        st.dataframe(plan, use_container_width=True, hide_index=True)
        sp = pd.DataFrame([dict(revenue=s["revenue"], margin=s["margin"], status="feasible" if s["feasible"] else "infeasible",
                                plan=" | ".join(f"{c[0]}:{c[1]}/{c[2]}" for c in s["choice"])) for s in sols])
        fig = px.scatter(sp, x="margin", y="revenue", color="status", hover_data=["plan"],
                         color_discrete_map={"feasible": ACC, "infeasible": "#cbd5e1"},
                         title="Every candidate plan: revenue vs margin (best plan circled)")
        fig.add_vline(x=d["r_star"], line_dash="dash", line_color=WARN, annotation_text="r*")
        fig.add_trace(go.Scatter(x=[best["margin"]], y=[best["revenue"]], mode="markers", name="chosen",
                                 marker=dict(size=18, color="rgba(0,0,0,0)", line=dict(color=ACC2, width=3))))
        st.plotly_chart(fig.update_layout(height=380), use_container_width=True)

# ---------------------------------------------------------------- M3
else:
    st.title("M3 · Markdown-aware product ranking")
    ex = st.selectbox("Example", ["A · Exact IP on 3 users × 4 products", "B · Real-time rule with dual prices (scarce strawberries)"])
    d = copy.deepcopy(RANK)
    st.subheader("1 · Input data")
    prod = pd.DataFrame([dict(product=k, markdown_price=v[0], salvage=v[1], inventory=v[2]) for k, v in d["products"].items()])
    a, b = st.columns([1, 1])
    a.dataframe(prod, hide_index=True, use_container_width=True)
    heat = pd.DataFrame([[d["ctcvr"][(t, k)] for k in d["products"]] for t in d["users"]], index=d["users"], columns=list(d["products"]))
    b.plotly_chart(px.imshow(heat, text_auto=True, color_continuous_scale="Blues", title="ctcvr (P click & buy)")
                   .update_layout(height=260, margin=dict(t=40, b=0)), use_container_width=True)
    st.subheader("2 · Run model")
    if ex.startswith("A"):
        c = st.columns(2)
        d["S_t"] = c[0].number_input("Slots per user S_t", 1, 4, 2)
        d["ctr_star"] = c[1].slider("Click-through target ctr*", 0.0, 6.0, 2.5, 0.1)
        best = solve_rank_bruteforce(d)
        st.subheader("3 · Results")
        if best is None:
            st.error("Infeasible: the click-through target cannot be met with these slots and stock limits.")
        else:
            obj, x = best
            m = st.columns(3)
            m[0].metric("Objective (revenue − salvage loss)", obj)
            m[1].metric("Total expected clicks", round(sum(d["ctr"][c] for c in x), 2))
            m[2].metric("Assignments", len(x))
            cols = st.columns(len(d["users"]))
            for col, t in zip(cols, d["users"]):
                col.markdown(f"**{t}** sees")
                for k in [k for k in d["products"] if (t, k) in x]:
                    col.success(k)
            use = pd.DataFrame([dict(product=k, expected_sales=round(sum(d["ctcvr"][(t, k)] for t in d["users"] if (t, k) in x), 2),
                                     inventory=v[2]) for k, v in d["products"].items()])
            fig = go.Figure([go.Bar(x=use["product"], y=use["inventory"], name="inventory I_k", marker_color="#cbd5e1"),
                             go.Bar(x=use["product"], y=use["expected_sales"], name="expected sales", marker_color=ACC)])
            st.plotly_chart(fig.update_layout(barmode="overlay", height=300, title="Stock constraint (B.2): expected sales ≤ inventory"),
                            use_container_width=True)
    else:
        st.caption("Step 3 of the hierarchical approach: score = ctcvr·(p + s) − α·ctcvr, show the top S_t per user.")
        c = st.columns(4)
        alpha = {k: c[i].slider(f"α {k}", 0.0, 5.0, {"Strawberries": 3.0, "Spinach": 1.0}.get(k, 0.0), 0.5)
                 for i, k in enumerate(d["products"])}
        sc = rank_scores(alpha, d)
        st.subheader("3 · Results")
        cols = st.columns(len(d["users"]))
        for col, t in zip(cols, d["users"]):
            col.markdown(f"**{t}** ranking")
            col.dataframe(pd.DataFrame(sc[t], columns=["product", "score"]).assign(
                shown=lambda z: ["✅" if i < d["S_t"] else "" for i in range(len(z))]), hide_index=True, use_container_width=True)
        st.info("A high dual price α means stock is scarce relative to demand, so the product is pushed down the list "
                "and slots go to items with excess stock — e.g. strawberries drop off U1's list at α = 3.")

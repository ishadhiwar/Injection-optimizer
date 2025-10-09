import streamlit as st
from pyomo.environ import *

# ---------------------------
# Streamlit Page Setup
# ---------------------------
st.set_page_config(page_title="Production Scheduling", page_icon="🏭", layout="wide")
st.title("🏭 Production Scheduling Optimizer")
st.write("Optimize medical consumables production across injection molding machines.")
st.markdown("---")

# ---------------------------
# User Inputs
# ---------------------------
st.subheader("📦 Define Jobs (Medical Consumables)")
jobs = st.multiselect("Select Jobs", ["Syringe", "Gloves", "Catheter", "IV_Set"], default=["Syringe", "Gloves"])

st.subheader("🏭 Define Machines (Injection Molding)")
machines = st.multiselect("Select Machines", 
    ["Arburg_Allrounder_320C", "Engel_Victory_200", "KraussMaffei_Hydronica_300"],
    default=["Arburg_Allrounder_320C", "Engel_Victory_200"]
)

# Demand input
st.subheader("📊 Demand (Units Required)")
demand = {}
for j in jobs:
    demand[j] = st.number_input(f"Demand for {j}", min_value=0, value=1000, step=100)

# Cycle times input
st.subheader("⚙️ Cycle Times (seconds per part)")
cycle_time = {}
for j in jobs:
    for m in machines:
        cycle_time[(j, m)] = st.number_input(f"Cycle Time for {j} on {m}", min_value=1, value=30, step=1)

# Changeover and capacity
st.subheader("🔧 Process Parameters")
changeover_time = st.number_input("Setup Changeover Time (minutes)", min_value=1, value=30, step=1)

available_hours = {}
for m in machines:
    available_hours[m] = st.number_input(f"Available Hours for {m}", min_value=1, value=200, step=10)

st.markdown("---")

# ---------------------------
# Optimization
# ---------------------------
if st.button("🚀 Optimize Production Schedule"):

    model = ConcreteModel()

    # Decision variables
    model.production = Var(jobs, machines, within=NonNegativeReals)  # units produced
    model.assignment = Var(jobs, machines, within=Binary)            # setup decision
    model.slack = Var(jobs, within=NonNegativeReals)                 # unmet demand (penalty)

    # Objective: minimize time + setup + slack penalty
    def objective_rule(model):
        prod_time = sum(model.production[j, m] * cycle_time[j, m] / 3600 for j in jobs for m in machines)
        setup_time = sum(model.assignment[j, m] * changeover_time / 60 for j in jobs for m in machines)
        penalty = sum(model.slack[j] * 10 for j in jobs)  # heavy penalty for unmet demand
        return prod_time + setup_time + penalty
    model.objective = Objective(rule=objective_rule, sense=minimize)

    # Demand constraint
    def demand_rule(model, j):
        return sum(model.production[j, m] for m in machines) + model.slack[j] >= demand[j]
    model.demand_constraint = Constraint(jobs, rule=demand_rule)

    # Machine capacity constraint
    def capacity_rule(model, m):
        prod_time = sum(model.production[j, m] * cycle_time[j, m] / 3600 for j in jobs)
        setup_time = sum(model.assignment[j, m] for j in jobs) * changeover_time / 60
        return prod_time + setup_time <= available_hours[m]
    model.capacity_constraint = Constraint(machines, rule=capacity_rule)

    # Assignment linking
    def assignment_link_rule(model, j, m):
        return model.production[j, m] <= demand[j] * model.assignment[j, m]
    model.assignment_link = Constraint(jobs, machines, rule=assignment_link_rule)

    # Solve
    solver = SolverFactory("highs")
    results = solver.solve(model, tee=False)

    if results.solver.termination_condition == TerminationCondition.optimal:
        st.success("✅ Optimal production schedule found!")

        total_obj = model.objective()
        st.subheader(f"📊 Objective Value (time + penalty): {total_obj:.2f}")

        for m in machines:
            st.markdown(f"### 🏭 {m}")
            rows = []
            for j in jobs:
                qty = model.production[j, m].value or 0
                if qty > 1:
                    time_used = qty * cycle_time[j, m] / 3600
                    rows.append([j, f"{qty:.0f}", f"{time_used:.2f} hrs"])
            if rows:
                st.table(rows)
            else:
                st.write("No jobs assigned.")

        # Unmet demand report
        st.markdown("### ⚠️ Unmet Demand (Slack)")
        slack_data = []
        for j in jobs:
            if (model.slack[j].value or 0) > 0:
                slack_data.append([j, f"{model.slack[j].value:.0f} units"])
        if slack_data:
            st.table(slack_data)
        else:
            st.write("All demand satisfied ✅")

    else:
        st.error("❌ Optimization failed.")


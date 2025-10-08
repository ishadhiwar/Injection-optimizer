import streamlit as st
from pyomo.environ import *

st.set_page_config(page_title="Production Scheduling", page_icon="🏭", layout="wide")
st.title("🏭 Production Scheduling Optimizer")
st.write("Assign jobs to machines to minimize time and changeover costs while meeting demand.")
st.markdown("---")

# --- Input Data ---
jobs = ['JobA', 'JobB', 'JobC']
machines = ['IMM_1', 'IMM_2']

# Demand (units)
demand = {'JobA': 500, 'JobB': 400, 'JobC': 300}

# Cycle time (seconds per part)
cycle_time = {
    ('JobA', 'IMM_1'): 25, ('JobA', 'IMM_2'): 28,
    ('JobB', 'IMM_1'): 35, ('JobB', 'IMM_2'): 32,
    ('JobC', 'IMM_1'): 20, ('JobC', 'IMM_2'): 22,
}

# Setup changeover time (minutes)
changeover_time = 30  

# Machine available time (hours) – deliberately high to avoid infeasibility
available_hours = {'IMM_1': 200, 'IMM_2': 180}

# --- Optimization ---
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

    # Constraint: meet demand (with slack if needed)
    def demand_rule(model, j):
        return sum(model.production[j, m] for m in machines) + model.slack[j] >= demand[j]
    model.demand_constraint = Constraint(jobs, rule=demand_rule)

    # Constraint: machine time
    def capacity_rule(model, m):
        prod_time = sum(model.production[j, m] * cycle_time[j, m] / 3600 for j in jobs)
        setup_time = sum(model.assignment[j, m] for j in jobs) * changeover_time / 60
        return prod_time + setup_time <= available_hours[m]
    model.capacity_constraint = Constraint(machines, rule=capacity_rule)

    # Constraint: link assignment to production
    def assignment_link_rule(model, j, m):
        return model.production[j, m] <= demand[j] * model.assignment[j, m]
    model.assignment_link = Constraint(jobs, machines, rule=assignment_link_rule)

    # Solve with HiGHS
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

        # Show unmet demand if any
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

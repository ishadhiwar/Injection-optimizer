import streamlit as st
from pyomo.environ import *

st.set_page_config(page_title="Production Scheduling", page_icon="🏭", layout="centered")

st.title("🏭 Injection Molding Production Scheduling Optimizer")
st.write("Assign jobs to machines to minimize time and changeover costs while meeting demand.")

st.markdown("---")

# --- Input Data ---
jobs = ['JobA', 'JobB', 'JobC', 'JobD']
machines = ['IMM_1', 'IMM_2', 'IMM_3']

demand = {'JobA': 5000, 'JobB': 3000, 'JobC': 4000, 'JobD': 2000}
cycle_time = {
    ('JobA', 'IMM_1'): 25, ('JobA', 'IMM_2'): 28, ('JobA', 'IMM_3'): 30,
    ('JobB', 'IMM_1'): 35, ('JobB', 'IMM_2'): 32, ('JobB', 'IMM_3'): 38,
    ('JobC', 'IMM_1'): 20, ('JobC', 'IMM_2'): 22, ('JobC', 'IMM_3'): 21,
    ('JobD', 'IMM_1'): 40, ('JobD', 'IMM_2'): 38, ('JobD', 'IMM_3'): 42,
}
changeover_time = 60  # minutes
available_hours = {'IMM_1': 20, 'IMM_2': 22, 'IMM_3': 16}

# --- Run Optimization ---
if st.button("🚀 Optimize Production"):

    model = ConcreteModel()

    model.production = Var(jobs, machines, within=NonNegativeReals)
    model.assignment = Var(jobs, machines, within=Binary)

    def objective_rule(model):
        prod_cost = sum(model.production[j,m] * cycle_time[j,m] / 3600 for j in jobs for m in machines)
        changeover_cost = sum(model.assignment[j,m] * changeover_time / 60 for j in jobs for m in machines) * 5
        return prod_cost + changeover_cost
    model.objective = Objective(rule=objective_rule, sense=minimize)

    def demand_rule(model, j):
        return sum(model.production[j,m] for m in machines) >= demand[j]
    model.demand_constraint = Constraint(jobs, rule=demand_rule)

    def capacity_rule(model, m):
        prod_time = sum(model.production[j,m] * cycle_time[j,m] / 3600 for j in jobs)
        setup_time = sum(model.assignment[j,m] for j in jobs) * changeover_time / 60
        return prod_time + setup_time <= available_hours[m]
    model.capacity_constraint = Constraint(machines, rule=capacity_rule)

    def assignment_link_rule(model, j, m):
        return model.production[j,m] <= demand[j] * model.assignment[j,m]
    model.assignment_link = Constraint(jobs, machines, rule=assignment_link_rule)

    solver = SolverFactory("highs")  # Use HiGHS for Streamlit Cloud
    results = solver.solve(model, tee=False)

    if results.solver.termination_condition == TerminationCondition.optimal:
        st.success("✅ Optimal production schedule found!")
        for m in machines:
            st.write(f"### {m}")
            for j in jobs:
                qty = model.production[j,m].value
                if qty and qty > 1:
                    st.write(f"- {j}: {qty:.0f} parts")
    else:
        st.error("❌ Optimization failed.")

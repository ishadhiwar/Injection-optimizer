import streamlit as st
from pyomo.environ import *

st.set_page_config(page_title="Maintenance Scheduling", page_icon="🛠️", layout="centered")
st.title("🛠️ Maintenance Scheduling Optimizer")
st.write("Optimize preventive and major maintenance schedule to minimize downtime + failure costs.")
st.markdown("---")

machines = ['IMM_1', 'IMM_2', 'IMM_3']
weeks = list(range(1, 9))
pm_minor_cost, pm_major_cost = 500, 2000
downtime_cost_per_hour = 300
task_duration = {'PM_Minor': 2, 'PM_Major': 8}
labor_available = {w: 40 for w in weeks}

if st.button("🚀 Optimize Maintenance"):
    model = ConcreteModel()
    model.pm_minor = Var(machines, weeks, within=Binary)
    model.pm_major = Var(machines, weeks, within=Binary)

    def objective_rule(model):
        pm_cost = sum(model.pm_minor[m,w]*pm_minor_cost + model.pm_major[m,w]*pm_major_cost for m in machines for w in weeks)
        downtime = sum((model.pm_minor[m,w]*task_duration['PM_Minor'] + model.pm_major[m,w]*task_duration['PM_Major'])*downtime_cost_per_hour for m in machines for w in weeks)
        return pm_cost + downtime
    model.objective = Objective(rule=objective_rule, sense=minimize)

    def labor_rule(model, w):
        return sum(model.pm_minor[m,w]*task_duration['PM_Minor'] + model.pm_major[m,w]*task_duration['PM_Major'] for m in machines) <= labor_available[w]
    model.labor_constraint = Constraint(weeks, rule=labor_rule)

    solver = SolverFactory("highs")
    results = solver.solve(model, tee=False)

    if results.solver.termination_condition == TerminationCondition.optimal:
        st.success("✅ Maintenance schedule found!")
        for m in machines:
            st.write(f"### {m}")
            for w in weeks:
                if model.pm_minor[m,w].value > 0.5:
                    st.write(f"- Week {w}: Minor PM")
                if model.pm_major[m,w].value > 0.5:
                    st.write(f"- Week {w}: Major PM")
    else:
        st.error("❌ Optimization failed.")

import streamlit as st
from pyomo.environ import *

# ---------------------------
# Streamlit Page Setup
# ---------------------------
st.set_page_config(page_title="Maintenance Scheduling", page_icon="🛠️", layout="centered")
st.title("🛠️ Maintenance Scheduling Optimizer")
st.write("Plan preventive and major maintenance for injection molding machines (medical consumables).")
st.markdown("---")

# ---------------------------
# User Inputs
# ---------------------------

# Machines
st.subheader("🏭 Define Injection Molding Machines")
machines = st.multiselect("Select Machines", 
    ["Arburg_Allrounder_320C", "Engel_Victory_200", "KraussMaffei_Hydronica_300"],
    default=["Arburg_Allrounder_320C", "Engel_Victory_200"]
)

# Weeks
num_weeks = st.number_input("Number of Weeks to Schedule", min_value=4, max_value=52, value=8, step=1)
weeks = list(range(1, num_weeks+1))

# Costs
st.subheader("💰 Maintenance Costs")
pm_minor_cost = st.number_input("Minor PM Cost ($)", min_value=100, value=500, step=100)
pm_major_cost = st.number_input("Major PM Cost ($)", min_value=500, value=2000, step=100)
downtime_cost_per_hour = st.number_input("Downtime Cost per Hour ($)", min_value=100, value=300, step=50)

# Failure penalty if machine breaks down
failure_penalty = st.number_input("Expected Failure Penalty per Week ($)", min_value=500, value=3000, step=500)

# Durations
st.subheader("⏱️ Task Durations (hours)")
task_duration = {
    "PM_Minor": st.number_input("Minor PM Duration (hours)", min_value=1, value=2, step=1),
    "PM_Major": st.number_input("Major PM Duration (hours)", min_value=4, value=8, step=1),
}

# Labor
st.subheader("👷 Labor Availability per Week (hours)")
labor_available = {}
for w in weeks:
    labor_available[w] = st.number_input(f"Week {w} Labor Hours", min_value=1, value=40, step=5)

st.markdown("---")

# ---------------------------
# Optimization
# ---------------------------
if st.button("🚀 Optimize Maintenance Schedule"):

    model = ConcreteModel()

    # Decision variables
    model.pm_minor = Var(machines, weeks, within=Binary)
    model.pm_major = Var(machines, weeks, within=Binary)

    # Objective: minimize cost + downtime + failure penalty
    def objective_rule(model):
        pm_cost = sum(model.pm_minor[m,w]*pm_minor_cost + model.pm_major[m,w]*pm_major_cost 
                      for m in machines for w in weeks)

        downtime = sum((model.pm_minor[m,w]*task_duration['PM_Minor'] +
                        model.pm_major[m,w]*task_duration['PM_Major'])*downtime_cost_per_hour 
                       for m in machines for w in weeks)

        # Failure risk penalty: if no maintenance in a week, risk accumulates
        failure_cost = 0
        for m in machines:
            for w in weeks:
                # If no PM scheduled, add expected penalty
                failure_cost += (1 - model.pm_minor[m,w] - model.pm_major[m,w]) * (failure_penalty * (w/num_weeks))

        return pm_cost + downtime + failure_cost

    model.objective = Objective(rule=objective_rule, sense=minimize)

    # Labor capacity constraint
    def labor_rule(model, w):
        return sum(model.pm_minor[m,w]*task_duration['PM_Minor'] + 
                   model.pm_major[m,w]*task_duration['PM_Major'] for m in machines) <= labor_available[w]
    model.labor_constraint = Constraint(weeks, rule=labor_rule)

    # Solve
    solver = SolverFactory("highs")
    results = solver.solve(model, tee=False)

    # Results
    if results.solver.termination_condition == TerminationCondition.optimal:
        st.success("✅ Maintenance schedule optimized!")

        for m in machines:
            st.markdown(f"### 🏭 {m}")
            schedule_rows = []
            for w in weeks:
                tasks = []
                if model.pm_minor[m,w].value > 0.5:
                    tasks.append("Minor PM")
                if model.pm_major[m,w].value > 0.5:
                    tasks.append("Major PM")
                if tasks:
                    schedule_rows.append([f"Week {w}", ", ".join(tasks)])
            if schedule_rows:
                st.table(schedule_rows)
            else:
                st.write("No maintenance assigned (⚠️ higher risk of failure).")

        # Interpretation
        st.markdown("## 📈 Interpretation of Schedule")
        total_minor = sum(model.pm_minor[m,w].value for m in machines for w in weeks)
        total_major = sum(model.pm_major[m,w].value for m in machines for w in weeks)
        st.write(f"- Planned **{int(total_minor)} Minor PM** and **{int(total_major)} Major PM** tasks.")
        st.info("💡 Interpretation: The optimizer now includes **failure risk penalties**. "
                "Machines are more likely to receive preventive maintenance when downtime or breakdown "
                "costs are high. If no PM is scheduled, it indicates the model found it cheaper to accept the "
                "failure risk than perform maintenance.")
    else:
        st.error("❌ Optimization failed.")

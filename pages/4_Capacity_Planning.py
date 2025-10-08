import streamlit as st
from pyomo.environ import *

st.set_page_config(page_title="Capacity Planning", page_icon="📦", layout="wide")
st.title("📦 Capacity Planning Optimizer")
st.write("Maximize profit given machine capacity, labor, and demand constraints.")
st.markdown("---")

# -----------------------------
# Example Data
# -----------------------------
products = ['PartX', 'PartY']
machines = ['IMM_100T', 'IMM_200T']
months = [1, 2, 3]

product_data = {
    'PartX': {
        'selling_price': 5.0,
        'material_cost': 2.0,
        'labor_hours': 0.05,
        'cycle_time': {'IMM_100T': 30, 'IMM_200T': 28},
        'max_demand_per_month': 2000,
    },
    'PartY': {
        'selling_price': 8.0,
        'material_cost': 3.0,
        'labor_hours': 0.08,
        'cycle_time': {'IMM_100T': 0, 'IMM_200T': 40},
        'max_demand_per_month': 1500,
    }
}

machine_capacity = {'IMM_100T': 200, 'IMM_200T': 150}  # hours
labor_hours_available = 500  # per month

# -----------------------------
# Optimization
# -----------------------------
if st.button("🚀 Optimize Capacity Plan"):

    model = ConcreteModel()

    # Decision Variables
    model.production = Var(products, machines, months, within=NonNegativeReals)
    model.sales = Var(products, months, within=NonNegativeReals)
    model.slack = Var(products, months, within=NonNegativeReals)  # unmet demand

    # Objective: Maximize profit (Revenue - Costs - Slack penalty)
    def objective_rule(model):
        revenue = sum(model.sales[p, t] * product_data[p]['selling_price']
                      for p in products for t in months)

        material_cost = sum(model.production[p, m, t] * product_data[p]['material_cost']
                            for p in products for m in machines for t in months)

        labor_cost = sum(model.production[p, m, t] * product_data[p]['labor_hours'] * 25
                         for p in products for m in machines for t in months)

        # Slack penalty = lost revenue
        slack_penalty = sum(model.slack[p, t] * product_data[p]['selling_price']
                            for p in products for t in months)

        return revenue - material_cost - labor_cost - slack_penalty
    model.objective = Objective(rule=objective_rule, sense=maximize)

    # Constraint: Machine capacity
    def capacity_rule(model, m, t):
        time_used = sum(model.production[p, m, t] *
                        product_data[p]['cycle_time'].get(m, 0) / 3600 for p in products)
        return time_used <= machine_capacity[m]
    model.capacity_constraint = Constraint(machines, months, rule=capacity_rule)

    # Constraint: Labor
    def labor_rule(model, t):
        return sum(model.production[p, m, t] * product_data[p]['labor_hours']
                   for p in products for m in machines) <= labor_hours_available
    model.labor_constraint = Constraint(months, rule=labor_rule)

    # Constraint: Sales + Slack <= Demand
    def demand_rule(model, p, t):
        return model.sales[p, t] + model.slack[p, t] <= product_data[p]['max_demand_per_month']
    model.demand_constraint = Constraint(products, months, rule=demand_rule)

    # Constraint: Sales <= Production (can't sell more than produced)
    def sales_rule(model, p, t):
        return model.sales[p, t] <= sum(model.production[p, m, t] for m in machines)
    model.sales_constraint = Constraint(products, months, rule=sales_rule)

    # Solve
    solver = SolverFactory("highs")
    results = solver.solve(model, tee=False)

    # -----------------------------
    # Results
    # -----------------------------
    if results.solver.termination_condition == TerminationCondition.optimal:
        st.success("✅ Optimal capacity plan found!")

        st.subheader(f"📊 Objective (Profit): ${model.objective():,.2f}")

        for t in months:
            st.markdown(f"### 📅 Month {t}")
            rows = []
            for p in products:
                sales = model.sales[p, t].value or 0
                slack = model.slack[p, t].value or 0
                rows.append([p,
                             f"{sales:.0f} sold",
                             f"{slack:.0f} unmet"])
            st.table(rows)

        # Show machine utilization
        st.markdown("### 🏭 Machine Utilization")
        util_rows = []
        for m in machines:
            for t in months:
                time_used = sum((model.production[p, m, t].value or 0) *
                                product_data[p]['cycle_time'].get(m, 0) / 3600
                                for p in products)
                util_rows.append([m, f"Month {t}", f"{time_used:.1f} hrs / {machine_capacity[m]} hrs"])
        st.table(util_rows)

        # Show unmet demand summary
        st.markdown("### ⚠️ Unmet Demand Summary")
        slack_rows = []
        for p in products:
            total_slack = sum(model.slack[p, t].value or 0 for t in months)
            if total_slack > 0:
                slack_rows.append([p, f"{total_slack:.0f} units"])
        if slack_rows:
            st.table(slack_rows)
        else:
            st.write("All demand satisfied ✅")

    else:
        st.error("❌ Optimization failed. Try adjusting data or constraints.")

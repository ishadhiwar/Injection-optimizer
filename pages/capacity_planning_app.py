import streamlit as st
from pyomo.environ import *

st.set_page_config(page_title="Capacity Planning", page_icon="📦", layout="centered")
st.title("📦 Capacity Planning Optimizer")
st.write("Maximize profit given machine capacity, labor, and demand constraints.")
st.markdown("---")

products = ['PartX', 'PartY']
machines = ['IMM_100T', 'IMM_200T']
months = [1, 2, 3]

selling_price = {'PartX': 5.0, 'PartY': 8.0}
material_cost = {'PartX': 2.0, 'PartY': 3.0}
cycle_time = {('PartX','IMM_100T'): 30, ('PartX','IMM_200T'): 28,
              ('PartY','IMM_100T'): 0,  ('PartY','IMM_200T'): 40}
machine_capacity = {'IMM_100T': 200, 'IMM_200T': 150}

if st.button("🚀 Optimize Capacity Plan"):
    model = ConcreteModel()
    model.production = Var(products, machines, months, within=NonNegativeReals)
    model.sales = Var(products, months, within=NonNegativeReals)

    def objective_rule(model):
        revenue = sum(model.sales[p,t]*selling_price[p] for p in products for t in months)
        cost = sum(model.production[p,m,t]*material_cost[p] for p in products for m in machines for t in months)
        return revenue - cost
    model.objective = Objective(rule=objective_rule, sense=maximize)

    def capacity_rule(model, m, t):
        time_used = sum(model.production[p,m,t]*cycle_time.get((p,m),0)/3600 for p in products)
        return time_used <= machine_capacity[m]
    model.capacity_constraint = Constraint(machines, months, rule=capacity_rule)

    solver = SolverFactory("highs")
    results = solver.solve(model, tee=False)

    if results.solver.termination_condition == TerminationCondition.optimal:
        st.success("✅ Capacity plan optimized!")
        for t in months:
            st.write(f"### Month {t}")
            for p in products:
                sales = model.sales[p,t].value or 0
                st.write(f"- {p}: {sales:.0f} units sold")
    else:
        st.error("❌ Optimization failed.")

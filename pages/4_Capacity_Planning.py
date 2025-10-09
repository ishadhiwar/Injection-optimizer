import streamlit as st
from pyomo.environ import *

# ---------------------------
# Streamlit Page Setup
# ---------------------------
st.set_page_config(page_title="Capacity Planning", page_icon="📦", layout="wide")
st.title("📦 Capacity Planning Optimizer")
st.write("Maximize profit for medical consumables given machine, labor, and demand constraints.")
st.markdown("---")

# ---------------------------
# User Inputs
# ---------------------------
st.subheader("📦 Define Products (Medical Consumables)")
products = st.multiselect("Select Products", 
    ["Syringe", "IV_Set", "Catheter", "Gloves"],
    default=["Syringe", "IV_Set"])

st.subheader("🏭 Define Machines (Injection Molding)")
machines = st.multiselect("Select Machines",
    ["Arburg_Allrounder_320C", "Engel_Victory_200"],
    default=["Arburg_Allrounder_320C", "Engel_Victory_200"])

months = [1, 2, 3]  # 3-month horizon

product_data = {}
for p in products:
    st.markdown(f"### 📦 {p}")
    selling_price = st.number_input(f"Selling Price of {p} ($/unit)", min_value=0.1, value=5.0, step=0.1)
    material_cost = st.number_input(f"Material Cost of {p} ($/unit)", min_value=0.1, value=2.0, step=0.1)
    labor_hours = st.number_input(f"Labor Hours per unit of {p}", min_value=0.01, value=0.05, step=0.01)
    max_demand = st.number_input(f"Max Demand per Month for {p} (units)", min_value=100, value=2000, step=100)

    cycle_time = {}
    for m in machines:
        cycle_time[m] = st.number_input(f"Cycle Time of {p} on {m} (seconds)", min_value=0, value=30, step=1)
    product_data[p] = {
        "selling_price": selling_price,
        "material_cost": material_cost,
        "labor_hours": labor_hours,
        "max_demand_per_month": max_demand,
        "cycle_time": cycle_time,
    }

st.markdown("---")

# Machine capacities
st.subheader("🏭 Machine Monthly Capacity (hours)")
machine_capacity = {}
for m in machines:
    machine_capacity[m] = st.number_input(f"Available Hours for {m} per month", min_value=10, value=200, step=10)

# Labor availability
labor_hours_available = st.number_input("👷 Total Labor Hours Available per Month", min_value=50, value=500, step=10)

st.markdown("---")

# ---------------------------
# Optimization
# ---------------------------
if st.button("🚀 Optimize Capacity Plan"):

    model = ConcreteModel()

    # Decision Variables
    model.production = Var(products, machines, months, within=NonNegativeReals)
    model.sales = Var(products, months, within=NonNegativeReals)
    model.slack = Var(products, months, within=NonNegativeReals)  # unmet demand

    # Objective: Maximize profit
    def objective_rule(model):
        revenue = sum(model.sales[p, t] * product_data[p]["selling_price"]
                      for p in products for t in months)
        material_cost = sum(model.production[p, m, t] * product_data[p]["material_cost"]
                            for p in products for m in machines for t in months)
        labor_cost = sum(model.production[p, m, t] * product_data[p]["labor_hours"] * 25
                         for p in products for m in machines for t in months)
        slack_penalty = sum(model.slack[p, t] * product_data[p]["selling_price"]
                            for p in products for t in months)
        return revenue - material_cost - labor_cost - slack_penalty
    model.objective = Objective(rule=objective_rule, sense=maximize)

    # Constraints
    def capacity_rule(model, m, t):
        time_used = sum(model.production[p, m, t] * product_data[p]["cycle_time"].get(m, 0) / 3600
                        for p in products)
        return time_used <= machine_capacity[m]
    model.capacity_constraint = Constraint(machines, months, rule=capacity_rule)

    def labor_rule(model, t):
        return sum(model.production[p, m, t] * product_data[p]["labor_hours"]
                   for p in products for m in machines) <= labor_hours_available
    model.labor_constraint = Constraint(months, rule=labor_rule)

    def demand_rule(model, p, t):
        return model.sales[p, t] + model.slack[p, t] <= product_data[p]["max_demand_per_month"]
    model.demand_constraint = Constraint(products, months, rule=demand_rule)

    def sales_rule(model, p, t):
        return model.sales[p, t] <= sum(model.production[p, m, t] for m in machines)
    model.sales_constraint = Constraint(products, months, rule=sales_rule)

    # Solve
    solver = SolverFactory("highs")
    results = solver.solve(model, tee=False)

    # ---------------------------
    # Results
    # ---------------------------
    if results.solver.termination_condition == TerminationCondition.optimal:
        st.success("✅ Optimal capacity plan found!")

        st.subheader(f"📊 Objective (Profit): ${model.objective():,.2f}")

        for t in months:
            st.markdown(f"### 📅 Month {t}")
            rows = []
            for p in products:
                sales = model.sales[p, t].value or 0
                slack = model.slack[p, t].value or 0
                rows.append([p, f"{sales:.0f} sold", f"{slack:.0f} unmet"])
            st.table(rows)

        st.markdown("### 🏭 Machine Utilization")
        util_rows = []
        for m in machines:
            for t in months:
                time_used = sum((model.production[p, m, t].value or 0) *
                                product_data[p]["cycle_time"].get(m, 0) / 3600
                                for p in products)
                util_rows.append([m, f"Month {t}", f"{time_used:.1f} hrs / {machine_capacity[m]} hrs"])
        st.table(util_rows)

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

        # Interpretation
        st.markdown("## 📈 Interpretation")
        st.write("- Profit is maximized by prioritizing products with **higher selling price-to-cost ratio**.")
        st.write("- Machines with **faster cycle times** are loaded first to improve throughput.")
        st.write("- Unmet demand occurs when capacity or labor is insufficient.")
        st.info("💡 Use these results to decide whether to add machine shifts, increase labor, or outsource production.")

    else:
        st.error("❌ Optimization failed. Try adjusting data or constraints.")

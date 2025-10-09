import streamlit as st
from pyomo.environ import *

# ---------------------------
# Streamlit Page Setup
# ---------------------------
st.set_page_config(page_title="Material Blending", page_icon="🧪", layout="centered")
st.title("🧪 Material Blending Optimizer")
st.write("Optimize resin + regrind + additive blend to minimize cost while meeting quality specs.")
st.markdown("---")

# ---------------------------
# User Inputs
# ---------------------------

st.subheader("🧾 Define Material Properties")

# Default materials with float values
materials = {
    'Virgin': {'cost': 2.5, 'strength': 35.0, 'density': 1.05},
    'Regrind': {'cost': 1.0, 'strength': 25.0, 'density': 0.95},
    'Additive': {'cost': 5.0, 'strength': 50.0, 'density': 1.20},
}

user_materials = {}
for mat, props in materials.items():
    st.markdown(f"### ⚙️ {mat}")
    cost = st.number_input(
        f"Cost of {mat} ($/kg)", 
        min_value=0.1, 
        value=float(props["cost"]), 
        step=0.1
    )
    strength = st.number_input(
        f"Tensile Strength of {mat} (MPa)", 
        min_value=1.0, 
        value=float(props["strength"]), 
        step=1.0
    )
    density = st.number_input(
        f"Density of {mat} (g/cm³)", 
        min_value=0.1, 
        value=float(props["density"]), 
        step=0.01
    )
    user_materials[mat] = {"cost": cost, "strength": strength, "density": density}

st.markdown("---")

# Constraints
st.subheader("📊 Quality Constraints")
min_strength = st.number_input("Minimum Required Strength (MPa)", min_value=1.0, value=30.0, step=1.0)
max_density = st.number_input("Maximum Allowed Density (g/cm³)", min_value=0.5, value=1.1, step=0.01)

st.markdown("---")

# ---------------------------
# Optimization
# ---------------------------
if st.button("🚀 Optimize Blend"):
    model = ConcreteModel()

    # Decision variables: fraction of each material
    model.x = Var(user_materials.keys(), bounds=(0, 1))

    # Objective: Minimize cost
    model.cost = Objective(
        expr=sum(model.x[m] * user_materials[m]['cost'] for m in user_materials),
        sense=minimize
    )

    # Constraint: proportions must sum to 1 (100%)
    model.mix = Constraint(expr=sum(model.x[m] for m in user_materials) == 1)

    # Constraint: minimum strength
    model.strength = Constraint(
        expr=sum(model.x[m] * user_materials[m]['strength'] for m in user_materials) >= min_strength
    )

    # Constraint: maximum density
    model.density = Constraint(
        expr=sum(model.x[m] * user_materials[m]['density'] for m in user_materials) <= max_density
    )

    # Solve
    solver = SolverFactory("highs")
    results = solver.solve(model, tee=False)

    # Results
    if results.solver.termination_condition == TerminationCondition.optimal:
        st.success("✅ Blend optimized successfully!")

        st.subheader("📦 Optimal Material Proportions")
        for m in user_materials:
            st.write(f"- {m}: {model.x[m]()*100:.1f}%")

        st.info(f"💰 Cost per kg of blend: **${model.cost():.2f}**")

    else:
        st.error("❌ Optimization failed. Try adjusting constraints or inputs.")

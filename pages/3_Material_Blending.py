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
st.subheader("📦 Define Raw Materials")

default_materials = {
    "PP_Virgin": {"cost": 2.5, "strength": 35, "density": 1.05},
    "PP_Regrind": {"cost": 1.2, "strength": 25, "density": 0.95},
    "GlassFiber_Additive": {"cost": 5.0, "strength": 50, "density": 1.2},
}

materials = {}
for mat, props in default_materials.items():
    st.markdown(f"**{mat}**")
    cost = st.number_input(f"Cost of {mat} ($/kg)", min_value=0.1, value=props["cost"], step=0.1)
    strength = st.number_input(f"Tensile Strength of {mat} (MPa)", min_value=1.0, value=props["strength"], step=1.0)
    density = st.number_input(f"Density of {mat} (g/cm³)", min_value=0.5, value=props["density"], step=0.01)
    materials[mat] = {"cost": cost, "strength": strength, "density": density}
    st.markdown("---")

# Quality constraints
st.subheader("⚙️ Quality Constraints")
min_strength = st.number_input("Minimum Blend Strength (MPa)", 0.0, 100.0, 30.0)
max_density = st.number_input("Maximum Blend Density (g/cm³)", 0.0, 2.0, 1.1)

st.markdown("---")

# ---------------------------
# Optimization
# ---------------------------
if st.button("🚀 Optimize Blend"):
    model = ConcreteModel()

    # Decision variables (fraction of each material)
    model.x = Var(materials.keys(), bounds=(0, 1))

    # Objective: minimize cost
    model.cost = Objective(
        expr=sum(model.x[m] * materials[m]["cost"] for m in materials),
        sense=minimize
    )

    # Constraints
    model.mix = Constraint(expr=sum(model.x[m] for m in materials) == 1)
    model.strength = Constraint(expr=sum(model.x[m] * materials[m]["strength"] for m in materials) >= min_strength)
    model.density = Constraint(expr=sum(model.x[m] * materials[m]["density"] for m in materials) <= max_density)

    solver = SolverFactory("highs")
    results = solver.solve(model, tee=False)

    if results.solver.termination_condition == TerminationCondition.optimal:
        st.success("✅ Blend optimized!")

        st.subheader("🔬 Blend Composition")
        blend_strength = sum(model.x[m]() * materials[m]["strength"] for m in materials)
        blend_density = sum(model.x[m]() * materials[m]["density"] for m in materials)
        blend_cost = model.cost()

        for m in materials:
            st.write(f"- {m}: **{model.x[m]()*100:.1f}%**")

        st.markdown(f"**💲 Cost per kg:** ${blend_cost:.2f}")
        st.markdown(f"**💪 Blend Strength:** {blend_strength:.2f} MPa")
        st.markdown(f"**⚖️ Blend Density:** {blend_density:.3f} g/cm³")

        # Interpretation
        st.info(
            "💡 Interpretation: Virgin resin improves strength but increases cost, "
            "while regrind lowers cost but reduces strength. Additives like glass fiber "
            "boost strength and stiffness but may push density higher. "
            "The optimizer balances these trade-offs to meet quality constraints at lowest cost."
        )
    else:
        st.error("❌ Optimization failed. Try adjusting constraints.")

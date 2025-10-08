import streamlit as st
from pyomo.environ import *

st.set_page_config(page_title="Material Blending", page_icon="🧪", layout="centered")
st.title("🧪 Material Blending Optimizer")
st.write("Optimize resin + regrind + additive blend to minimize cost while meeting quality specs.")
st.markdown("---")

materials = {
    'Virgin': {'cost': 2.5, 'strength': 35, 'density': 1.05},
    'Regrind': {'cost': 1.0, 'strength': 25, 'density': 0.95},
    'Additive': {'cost': 5.0, 'strength': 50, 'density': 1.2},
}

min_strength = st.number_input("Minimum Strength (MPa)", 0.0, 100.0, 30.0)
max_density = st.number_input("Maximum Density (g/cm³)", 0.0, 2.0, 1.1)

if st.button("🚀 Optimize Blend"):
    model = ConcreteModel()
    model.x = Var(materials.keys(), bounds=(0,1))
    model.cost = Objective(expr=sum(model.x[m]*materials[m]['cost'] for m in materials), sense=minimize)
    model.mix = Constraint(expr=sum(model.x[m] for m in materials) == 1)
    model.strength = Constraint(expr=sum(model.x[m]*materials[m]['strength'] for m in materials) >= min_strength)
    model.density = Constraint(expr=sum(model.x[m]*materials[m]['density'] for m in materials) <= max_density)

    solver = SolverFactory("highs")
    results = solver.solve(model, tee=False)

    if results.solver.termination_condition == TerminationCondition.optimal:
        st.success("✅ Blend optimized!")
        for m in materials:
            st.write(f"{m}: {model.x[m]()*100:.1f}%")
        st.info(f"Cost per kg: ${model.cost():.2f}")
    else:
        st.error("❌ Optimization failed.")

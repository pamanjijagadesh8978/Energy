"""
app.py
------
Streamlit front-end for the BMI, calorie and macro calculator.
Collects user details into a dictionary and uses helpers.py for the calculations.

Run with:  streamlit run app.py
"""

import streamlit as st

from PROFILE.helpers import (
    ACTIVITY_FACTORS, ACTIVITY_LABELS, COMMON_DISEASES, SUGAR_PCT_OF_ENERGY, build_plan,
)

st.set_page_config(page_title="Macro Calculator", page_icon="🥗", layout="wide")

st.title("🥗 BMI, Calorie & Macro Calculator")

with st.form("user_form"):
    name = st.text_input("Name")

    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age (years)", min_value=10, max_value=100, value=30, step=1)
        height_cm = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=170.0, step=0.5)
    with col2:
        sex = st.selectbox("Sex", ["male", "female"], format_func=str.title)
        weight_kg = st.number_input("Weight (kg)", min_value=25.0, max_value=300.0, value=70.0, step=0.5)

    activity_level = st.selectbox(
        "Activity level",
        options=list(ACTIVITY_FACTORS),
        format_func=lambda k: ACTIVITY_LABELS[k],
        index=1,
    )

    selected_diseases = st.multiselect("Existing health conditions (if any)", COMMON_DISEASES)
    other_diseases = st.text_input("Other conditions (comma separated)", placeholder="e.g. Arthritis, Migraine")

    submitted = st.form_submit_button("Calculate", type="primary", width="stretch")

if submitted:
    extra = [d.strip() for d in other_diseases.split(",") if d.strip()]

    user = {
        "name": name.strip() or "User",
        "age": int(age),
        "sex": sex,
        "height_cm": float(height_cm),
        "weight_kg": float(weight_kg),
        "activity_level": activity_level,
        "diseases": selected_diseases + extra,
    }

    plan = build_plan(user)

    st.divider()
    st.subheader(f"Results for {user['name']}")

    if plan["numbers_withheld"]:
        st.metric("BMI", plan["bmi"], plan["category"], delta_color="off")
        st.error("Calorie and macro targets are not shown for the condition(s) you listed.")
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("BMI", plan["bmi"], plan["category"], delta_color="off")
    m2.metric("Maintenance calories", f"{plan['maintenance_calories']} kcal")
    sign = "+" if plan["adjustment"] > 0 else ""
    label = "Surplus" if plan["adjustment"] > 0 else "Deficit" if plan["adjustment"] < 0 else "Surplus / deficit"
    m3.metric(label, f"{sign}{plan['adjustment']} kcal")
    m4.metric("Daily target", f"{plan['target_calories']} kcal")

    if plan.get("adjustment_range") and plan.get("target_range"):
        lo, hi = plan["adjustment_range"]
        t_lo, t_hi = plan["target_range"]
        kind = "surplus" if plan["adjustment"] > 0 else "deficit"
        st.caption(
            f"Calorie {kind} range: {lo} to {hi} kcal/day "
            f"(daily calories {t_lo} to {t_hi} kcal). Applied: {abs(plan['adjustment'])} kcal."
        )

    macros = plan["macros"]

    if not macros["available"]:
        st.subheader("Daily nutrients")
        st.error(macros["message"])
    else:
        d = macros["daily"]

        st.subheader("Daily nutrients")
        st.dataframe(
            [
                {"Nutrient": "Calories", "Per day": f"{d['calories']} kcal", "% of energy": "-"},
                {"Nutrient": "Protein", "Per day": f"{d['protein_g']} g", "% of energy": f"{macros['protein']['pct']}%"},
                {"Nutrient": "Carbohydrate", "Per day": f"{d['carbs_g']} g", "% of energy": f"{macros['carbs']['pct']}%"},
                {"Nutrient": "Fat", "Per day": f"{d['fat_g']} g", "% of energy": f"{macros['fat']['pct']}%"},
                {"Nutrient": "Fibre", "Per day": f"{d['fibre_g']} g", "% of energy": "-"},
                {"Nutrient": "Sugar (max)", "Per day": f"{d['sugar_g']} g", "% of energy": f"{SUGAR_PCT_OF_ENERGY}%"},
                {"Nutrient": "Sodium (max)", "Per day": f"{d['sodium_mg']} mg", "% of energy": "-"},
            ],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            f"Protein, carbohydrate and fat add back to the {macros['energy_target']} kcal target "
            f"(rounding difference: {macros['energy_difference']} kcal). "
            f"Protein is {macros['protein_per_kg']} g per kg body weight."
        )

        st.subheader("Meal-wise distribution")
        rows = [
            {
                "Meal": f"{m['meal']} ({m['share_pct']}%)",
                "Calories": f"{m['calories']} kcal",
                "Protein": f"{m['protein_g']} g",
                "Carbs": f"{m['carbs_g']} g",
                "Fat": f"{m['fat_g']} g",
                "Fibre": f"{m['fibre_g']} g",
                "Sugar": f"{m['sugar_g']} g",
                "Sodium": f"{m['sodium_mg']} mg",
            }
            for m in macros["meals"]
        ]
        rows.append(
            {
                "Meal": "Total (100%)",
                "Calories": f"{d['calories']} kcal",
                "Protein": f"{d['protein_g']} g",
                "Carbs": f"{d['carbs_g']} g",
                "Fat": f"{d['fat_g']} g",
                "Fibre": f"{d['fibre_g']} g",
                "Sugar": f"{d['sugar_g']} g",
                "Sodium": f"{d['sodium_mg']} mg",
            }
        )
        st.dataframe(rows, hide_index=True, width="stretch")


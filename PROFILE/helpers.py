"""
helpers.py
----------
Calculation functions for the BMI, calorie target and macronutrient planner.

BMI-based rule:
  Underweight (BMI < 18.5)  -> surplus  of +300 to +500 kcal
  Normal      (18.5 - 24.9) -> maintenance (0 kcal)
  Overweight / Obese (>=25) -> deficit  of -300 to -500 kcal
"""

ACTIVITY_FACTORS = {
    "sedentary": 1.2,          # little or no exercise
    "light": 1.375,            # 1-3 days/week
    "moderate": 1.55,          # 3-5 days/week
    "active": 1.725,           # 6-7 days/week
    "very_active": 1.9,        # hard exercise / physical job
}

# Conditions where we stay at the gentle end (+/-300) of the range
CAUTION_CONDITIONS = [
    "diabetes", "kidney", "heart", "hypertension", "thyroid",
    "pcos", "liver", "cholesterol", "gerd", "asthma",
]

# Conditions where no surplus/deficit (and no macro split) is calculated
NO_ADJUSTMENT_CONDITIONS = [
    "eating disorder", "anorexia", "bulimia", "pregnan", "breastfeeding",
    "cancer", "dialysis",
]

# For these, no calorie or macro numbers are shown at all
EATING_DISORDER_CONDITIONS = ["eating disorder", "anorexia", "bulimia"]

# Macro settings
KCAL_PER_G = {"protein": 4, "carbs": 4, "fat": 9}
PROTEIN_RDA_G_PER_KG = 0.83      # ICMR-NIN RDA for healthy adults (used for kidney disease)
PROTEIN_MAX_ENERGY_PCT = 35      # cap on protein as % of energy
FAT_PCT_RANGE = (25, 35)         # % of energy
CARB_PCT_MIN = 35                # % of energy
CARB_PCT_MAX_DEFICIT = 50        # fat-loss plans
CARB_PCT_MAX_NEUTRAL = 55        # weight-neutral / surplus plans

# Size of the daily surplus / deficit (kcal)
ADJUSTMENT_RANGE_KCAL = (300, 500)

# Other daily targets
FIBRE_G = 30                     # g/day (25 g minimum, building toward 30 g+)
SUGAR_PCT_OF_ENERGY = 5          # added/free sugar, % of energy (working target)
SODIUM_MG = 2300                 # mg/day maximum

# How the daily totals are shared across the 5 meals (must add up to 100)
MEAL_SPLIT = [
    ("Breakfast", 25),
    ("Morning snack", 10),
    ("Lunch", 30),
    ("Evening snack", 10),
    ("Dinner", 25),
]
assert sum(share for _, share in MEAL_SPLIT) == 100

COMMON_DISEASES = [
    "Type 2 Diabetes",
    "Type 1 Diabetes",
    "Hypertension",
    "Heart Disease",
    "High Cholesterol",
    "Thyroid Disorder",
    "PCOS",
    "Kidney Disease",
    "Liver Disease",
    "Asthma",
    "GERD",
    "Eating Disorder",
    "Pregnancy",
]

ACTIVITY_LABELS = {
    "sedentary": "Sedentary (little or no exercise)",
    "light": "Light (1-3 days/week)",
    "moderate": "Moderate (3-5 days/week)",
    "active": "Active (6-7 days/week)",
    "very_active": "Very active (hard exercise / physical job)",
}


def calculate_bmi(weight_kg, height_cm):
    height_m = height_cm / 100
    return weight_kg / (height_m ** 2)


def classify_bmi(bmi):
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal weight"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def calculate_bmr(weight_kg, height_cm, age, sex):
    """Mifflin-St Jeor equation."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex.lower() == "male" else base - 161


def match_conditions(diseases, keywords):
    found = []
    for d in diseases:
        if any(k in d.lower() for k in keywords):
            found.append(d)
    return found


def decide_calorie_adjustment(bmi, diseases):
    """Returns the calorie adjustment in kcal (+ surplus, - deficit, 0 maintenance)."""
    if match_conditions(diseases, NO_ADJUSTMENT_CONDITIONS):
        return 0

    cautious = bool(match_conditions(diseases, CAUTION_CONDITIONS))

    if bmi < 18.5:                      # surplus
        if cautious or bmi >= 17:
            return 300
        return 500 if bmi < 16 else 400

    if bmi < 25:                        # maintain
        return 0

    if cautious or bmi < 27.5:          # deficit
        return -300
    if bmi < 30:
        return -400
    return -500


def distribute(total, shares=MEAL_SPLIT):
    """
    Split a daily total across meals by percentage. Each part is rounded, and any
    rounding leftover goes to the largest meal so the parts always add back to the total.
    """
    total = round(total)
    parts = [round(total * share / 100) for _, share in shares]
    biggest = max(range(len(shares)), key=lambda i: shares[i][1])
    parts[biggest] += total - sum(parts)
    return parts


def choose_protein_per_kg(adjustment, diseases):
    """Protein target in g/kg/day, inside the 1.0-1.6 working range."""
    if match_conditions(diseases, ["kidney"]):
        return PROTEIN_RDA_G_PER_KG
    if adjustment < 0:
        return 1.4
    if adjustment > 0:
        return 1.2
    return 1.1


def calculate_macros(weight_kg, target_kcal, adjustment, diseases):
    """
    Split the daily calorie target into protein / carbohydrate / fat (grams).
    Carbohydrate takes the remaining energy, so the macros add back to the target.
    """
    if match_conditions(diseases, NO_ADJUSTMENT_CONDITIONS):
        return {
            "available": False,
            "message": "Macros are not calculated for your listed condition(s).",
        }

    # Protein
    per_kg = choose_protein_per_kg(adjustment, diseases)
    protein_g = per_kg * weight_kg
    protein_g = min(protein_g, PROTEIN_MAX_ENERGY_PCT / 100 * target_kcal / KCAL_PER_G["protein"])
    protein_g = round(protein_g)
    protein_pct = protein_g * KCAL_PER_G["protein"] / target_kcal * 100

    # Fat: start at 30%, nudge within 25-35% to keep carbohydrate in range
    carb_max = CARB_PCT_MAX_DEFICIT if adjustment < 0 else CARB_PCT_MAX_NEUTRAL
    fat_pct = 30.0
    carb_pct = 100 - protein_pct - fat_pct
    if carb_pct > carb_max:
        fat_pct = min(FAT_PCT_RANGE[1], fat_pct + (carb_pct - carb_max))
    elif carb_pct < CARB_PCT_MIN:
        fat_pct = max(FAT_PCT_RANGE[0], fat_pct - (CARB_PCT_MIN - carb_pct))
    fat_g = round(fat_pct / 100 * target_kcal / KCAL_PER_G["fat"])

    # Carbohydrate: the remainder
    carb_g = round((target_kcal - protein_g * KCAL_PER_G["protein"] - fat_g * KCAL_PER_G["fat"])
                   / KCAL_PER_G["carbs"])

    protein_kcal = protein_g * KCAL_PER_G["protein"]
    carb_kcal = carb_g * KCAL_PER_G["carbs"]
    fat_kcal = fat_g * KCAL_PER_G["fat"]
    total_kcal = protein_kcal + carb_kcal + fat_kcal
    pct = lambda kcal: round(kcal / total_kcal * 100, 1)

    # Other daily targets
    sugar_g = round(SUGAR_PCT_OF_ENERGY / 100 * target_kcal / 4)

    daily = {
        "calories": target_kcal,
        "protein_g": protein_g,
        "carbs_g": carb_g,
        "fat_g": fat_g,
        "fibre_g": FIBRE_G,
        "sugar_g": sugar_g,
        "sodium_mg": SODIUM_MG,
    }

    # Share every daily value across the 5 meals
    split = {key: distribute(value) for key, value in daily.items()}
    meals = []
    for i, (meal_name, share) in enumerate(MEAL_SPLIT):
        meals.append({"meal": meal_name, "share_pct": share,
                      **{key: split[key][i] for key in daily}})

    return {
        "available": True,
        "protein_per_kg": round(per_kg, 2),
        "protein": {"grams": protein_g, "kcal": protein_kcal, "pct": pct(protein_kcal)},
        "carbs": {"grams": carb_g, "kcal": carb_kcal, "pct": pct(carb_kcal)},
        "fat": {"grams": fat_g, "kcal": fat_kcal, "pct": pct(fat_kcal)},
        "total_kcal": total_kcal,
        "energy_target": target_kcal,
        "energy_difference": target_kcal - total_kcal,
        "daily": daily,
        "meals": meals,
    }


def build_plan(user):
    """Takes the user dictionary and returns BMI, calorie target and macros."""
    weight = user["weight_kg"]
    height = user["height_cm"]
    diseases = user.get("diseases", [])

    bmi = calculate_bmi(weight, height)
    bmr = calculate_bmr(weight, height, user["age"], user["sex"])
    tdee = bmr * ACTIVITY_FACTORS[user["activity_level"]]
    adjustment = decide_calorie_adjustment(bmi, diseases)
    target = round(tdee + adjustment)

    # Allowed surplus/deficit window and the calorie range it gives
    lo, hi = ADJUSTMENT_RANGE_KCAL
    maintenance = round(tdee)
    if adjustment > 0:
        target_range = (maintenance + lo, maintenance + hi)
    elif adjustment < 0:
        target_range = (maintenance - hi, maintenance - lo)
    else:
        target_range = None

    return {
        "bmi": round(bmi, 1),
        "category": classify_bmi(bmi),
        "bmr": round(bmr),
        "maintenance_calories": round(tdee),
        "adjustment": adjustment,
        "target_calories": target,
        "adjustment_range": ADJUSTMENT_RANGE_KCAL if adjustment else None,
        "target_range": target_range,
        "numbers_withheld": bool(match_conditions(diseases, EATING_DISORDER_CONDITIONS)),
        "macros": calculate_macros(weight, target, adjustment, diseases),
    }


import numpy as np
import mysql.connector

from scipy.stats import chisquare
from statsmodels.stats.proportion import (
    proportions_ztest,
    confint_proportions_2indep,
)
from scipy.optimize import brentq
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

# Подключение к MySQL
connection = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    database="product_analytics",
)

cursor = connection.cursor(dictionary=True)

query = """
SELECT
    experiment_group,
    COUNT(*) AS users,
    SUM(converted) AS conversions
FROM ab_data_final
GROUP BY experiment_group;
"""

cursor.execute(query)
rows = cursor.fetchall()

cursor.close()
connection.close()


# Записываем результаты по группам в словарь
groups = {}

for row in rows:
    group_name = row["experiment_group"]

    groups[group_name] = {
        "users": int(row["users"]),
        "conversions": int(row["conversions"]),
    }


control_users = groups["control"]["users"]
control_conversions = groups["control"]["conversions"]

treatment_users = groups["treatment"]["users"]
treatment_conversions = groups["treatment"]["conversions"]


control_rate = control_conversions / control_users
treatment_rate = treatment_conversions / treatment_users

absolute_difference = treatment_rate - control_rate
relative_difference = absolute_difference / control_rate


print("A/B TEST RESULTS")
print()

print("Control:")
print(f"Users: {control_users}")
print(f"Conversions: {control_conversions}")
print(f"Conversion rate: {control_rate:.4%}")
print()

print("Treatment:")
print(f"Users: {treatment_users}")
print(f"Conversions: {treatment_conversions}")
print(f"Conversion rate: {treatment_rate:.4%}")
print()

print(f"Absolute difference: {absolute_difference * 100:.4f} p.p.")
print(f"Relative difference: {relative_difference:.4%}")


# Проверка Sample Ratio Mismatch
observed_users = np.array([
    control_users,
    treatment_users,
])

expected_users = np.array([
    observed_users.sum() / 2,
    observed_users.sum() / 2,
])

srm_statistic, srm_p_value = chisquare(
    observed_users,
    expected_users,
)

print()
print("SAMPLE RATIO MISMATCH CHECK")
print(f"Chi-square statistic: {srm_statistic:.4f}")
print(f"P-value: {srm_p_value:.4f}")

if srm_p_value < 0.05:
    print("There may be a problem with group allocation.")
else:
    print("No Sample Ratio Mismatch was detected.")


# Z-тест для двух долей
conversion_counts = np.array([
    treatment_conversions,
    control_conversions,
])

user_counts = np.array([
    treatment_users,
    control_users,
])

z_statistic, p_value = proportions_ztest(
    count=conversion_counts,
    nobs=user_counts,
    alternative="two-sided",
)

print()
print("TWO-PROPORTION Z-TEST")
print(f"Z-statistic: {z_statistic:.4f}")
print(f"P-value: {p_value:.4f}")


# Доверительный интервал для разницы:
# treatment conversion - control conversion
ci_low, ci_high = confint_proportions_2indep(
    count1=treatment_conversions,
    nobs1=treatment_users,
    count2=control_conversions,
    nobs2=control_users,
    method="wald",
    alpha=0.05,
)

print()
print("95% CONFIDENCE INTERVAL")
print(
    f"Difference: "
    f"[{ci_low * 100:.4f}; {ci_high * 100:.4f}] p.p."
)


alpha = 0.05

print()
print("DECISION")

if p_value < alpha:
    print("The difference is statistically significant.")
else:
    print("The difference is not statistically significant.")

if p_value >= alpha:
    print(
        "There is not enough evidence that the new page "
        "changes conversion."
    )
elif absolute_difference > 0:
    print("The new page significantly increases conversion.")
else:
    print("The new page significantly decreases conversion.")

    # Minimum Detectable Effect

power_analysis = NormalIndPower()

alpha = 0.05
target_power = 0.80

sample_ratio = treatment_users / control_users


def calculate_power(difference):
    assumed_treatment_rate = control_rate + difference

    effect_size = proportion_effectsize(
        assumed_treatment_rate,
        control_rate,
    )

    return power_analysis.power(
        effect_size=effect_size,
        nobs1=control_users,
        ratio=sample_ratio,
        alpha=alpha,
        alternative="two-sided",
    )


mde = brentq(
    lambda difference: calculate_power(difference) - target_power,
    0.000001,
    0.05,
)

print()
print("MINIMUM DETECTABLE EFFECT")
print(f"MDE: {mde * 100:.4f} p.p.")
print(f"Relative MDE: {mde / control_rate:.4%}")


import math

observed_effect_size = abs(
    proportion_effectsize(
        treatment_rate,
        control_rate,
    )
)

required_control_users = power_analysis.solve_power(
    effect_size=observed_effect_size,
    power=0.80,
    alpha=0.05,
    ratio=sample_ratio,
    alternative="two-sided",
)

required_treatment_users = (
    required_control_users * sample_ratio
)

print()
print("REQUIRED SAMPLE SIZE FOR OBSERVED EFFECT")
print(
    f"Control: {math.ceil(required_control_users)}"
)
print(
    f"Treatment: {math.ceil(required_treatment_users)}"
)
print(
    f"Total: "
    f"{math.ceil(required_control_users + required_treatment_users)}"
)
import pandas as pd
import mysql.connector
import numpy as np

from statsmodels.stats.contingency_tables import StratifiedTable
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import (
    confint_proportions_2indep,
    proportions_ztest,
)


connection = mysql.connector.connect(
    host="localhost",
    port=3306,
    user="root",
    password="",
    database="product_analytics",
)

cursor = connection.cursor(dictionary=True)

query = """
SELECT
    country,
    experiment_group,
    COUNT(*) AS users,
    SUM(converted) AS conversions
FROM ab_data_final
GROUP BY
    country,
    experiment_group
ORDER BY
    country,
    experiment_group;
"""

cursor.execute(query)
rows = cursor.fetchall()

cursor.close()
connection.close()

country_data = pd.DataFrame(rows)

results = []

for country in sorted(country_data["country"].unique()):
    data = country_data[country_data["country"] == country]
    data = data.set_index("experiment_group")

    control_users = int(data.loc["control", "users"])
    control_conversions = int(data.loc["control", "conversions"])

    treatment_users = int(data.loc["treatment", "users"])
    treatment_conversions = int(data.loc["treatment", "conversions"])

    control_rate = control_conversions / control_users
    treatment_rate = treatment_conversions / treatment_users

    difference = treatment_rate - control_rate

    z_statistic, p_value = proportions_ztest(
        count=[
            treatment_conversions,
            control_conversions,
        ],
        nobs=[
            treatment_users,
            control_users,
        ],
        alternative="two-sided",
    )

    ci_low, ci_high = confint_proportions_2indep(
        count1=treatment_conversions,
        nobs1=treatment_users,
        count2=control_conversions,
        nobs2=control_users,
        method="wald",
        alpha=0.05,
    )

    results.append({
        "country": country,
        "control_users": control_users,
        "treatment_users": treatment_users,
        "control_rate_pct": control_rate * 100,
        "treatment_rate_pct": treatment_rate * 100,
        "difference_pp": difference * 100,
        "z_statistic": z_statistic,
        "p_value": p_value,
        "ci_low_pp": ci_low * 100,
        "ci_high_pp": ci_high * 100,
    })

results = pd.DataFrame(results)

# Поправка на три статистических теста
reject, corrected_p_values, _, _ = multipletests(
    results["p_value"],
    alpha=0.05,
    method="holm",
)

results["p_value_holm"] = corrected_p_values
results["significant_after_correction"] = reject

columns_to_round = [
    "control_rate_pct",
    "treatment_rate_pct",
    "difference_pp",
    "z_statistic",
    "p_value",
    "ci_low_pp",
    "ci_high_pp",
    "p_value_holm",
]

results[columns_to_round] = results[columns_to_round].round(4)

print("A/B TEST BY COUNTRY")
print()
print(results.to_string(index=False))


# Проверка того, отличается ли эффект между странами

country_tables = []

for country in sorted(country_data["country"].unique()):
    data = country_data[
        country_data["country"] == country
    ].set_index("experiment_group")

    control_users = int(data.loc["control", "users"])
    control_conversions = int(
        data.loc["control", "conversions"]
    )

    treatment_users = int(data.loc["treatment", "users"])
    treatment_conversions = int(
        data.loc["treatment", "conversions"]
    )

    table = np.array([
        [
            treatment_conversions,
            treatment_users - treatment_conversions,
        ],
        [
            control_conversions,
            control_users - control_conversions,
        ],
    ])

    country_tables.append(table)


tables_array = np.stack(
    country_tables,
    axis=2,
)

stratified_table = StratifiedTable(tables_array)

heterogeneity_test = (
    stratified_table.test_equal_odds()
)

pooled_odds_ratio = (
    stratified_table.oddsratio_pooled
)

or_ci_low, or_ci_high = (
    stratified_table.oddsratio_pooled_confint()
)


print()
print("EFFECT HETEROGENEITY BY COUNTRY")
print(
    f"Breslow-Day statistic: "
    f"{heterogeneity_test.statistic:.4f}"
)
print(
    f"P-value: "
    f"{heterogeneity_test.pvalue:.4f}"
)

print()
print("POOLED ODDS RATIO")
print(
    f"Odds ratio: "
    f"{pooled_odds_ratio:.4f}"
)
print(
    f"95% confidence interval: "
    f"[{or_ci_low:.4f}; {or_ci_high:.4f}]"
)


alpha = 0.05

print()
print("HETEROGENEITY DECISION")

if heterogeneity_test.pvalue < alpha:
    print(
        "The effect of the new page differs "
        "statistically significantly between countries."
    )
else:
    print(
        "There is no statistically significant evidence "
        "that the effect differs between countries."
    )
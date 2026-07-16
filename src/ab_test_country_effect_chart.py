from pathlib import Path

import matplotlib.pyplot as plt
import mysql.connector
import numpy as np
import pandas as pd

from statsmodels.stats.proportion import (
    confint_proportions_2indep,
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
    data = country_data[
        country_data["country"] == country
    ].set_index("experiment_group")

    control_users = int(
        data.loc["control", "users"]
    )
    control_conversions = int(
        data.loc["control", "conversions"]
    )

    treatment_users = int(
        data.loc["treatment", "users"]
    )
    treatment_conversions = int(
        data.loc["treatment", "conversions"]
    )

    control_rate = (
        control_conversions / control_users
    )

    treatment_rate = (
        treatment_conversions / treatment_users
    )

    difference = (
        treatment_rate - control_rate
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
        "difference_pp": difference * 100,
        "ci_low_pp": ci_low * 100,
        "ci_high_pp": ci_high * 100,
    })


results = pd.DataFrame(results)

countries = results["country"]
differences = results["difference_pp"]

lower_errors = (
    differences - results["ci_low_pp"]
)

upper_errors = (
    results["ci_high_pp"] - differences
)

errors = np.array([
    lower_errors,
    upper_errors,
])


project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "images"
output_folder.mkdir(exist_ok=True)

output_path = (
    output_folder
    / "ab_test_effect_by_country.png"
)


plt.figure(figsize=(9, 5))

plt.errorbar(
    differences,
    countries,
    xerr=errors,
    fmt="o",
    capsize=6,
)

plt.axvline(
    x=0,
    linewidth=1,
)

plt.title("A/B Test Effect by Country")
plt.xlabel(
    "Conversion difference, percentage points\n"
    "Treatment minus control"
)
plt.ylabel("Country")
plt.grid(axis="x", alpha=0.3)


for index, row in results.iterrows():
    plt.text(
        row["ci_high_pp"] + 0.05,
        index,
        f'{row["difference_pp"]:+.2f} p.p.',
        va="center",
        fontsize=9,
    )


plt.tight_layout()

plt.savefig(
    output_path,
    dpi=300,
    bbox_inches="tight",
)

plt.close()

print(f"График сохранён: {output_path}")
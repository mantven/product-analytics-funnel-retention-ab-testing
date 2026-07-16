from pathlib import Path

import matplotlib.pyplot as plt
import mysql.connector
import numpy as np


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
    experiment_group,
    COUNT(*) AS users,
    SUM(converted) AS conversions
FROM ab_data_final
GROUP BY experiment_group
ORDER BY experiment_group;
"""

cursor.execute(query)
rows = cursor.fetchall()

cursor.close()
connection.close()


groups = {}

for row in rows:
    groups[row["experiment_group"]] = {
        "users": int(row["users"]),
        "conversions": int(row["conversions"]),
    }


control_users = groups["control"]["users"]
control_conversions = groups["control"]["conversions"]

treatment_users = groups["treatment"]["users"]
treatment_conversions = groups["treatment"]["conversions"]


control_rate = control_conversions / control_users
treatment_rate = treatment_conversions / treatment_users


# Стандартные ошибки долей
control_se = np.sqrt(
    control_rate
    * (1 - control_rate)
    / control_users
)

treatment_se = np.sqrt(
    treatment_rate
    * (1 - treatment_rate)
    / treatment_users
)


# 95% доверительные интервалы
control_error = 1.96 * control_se * 100
treatment_error = 1.96 * treatment_se * 100


labels = ["Control", "Treatment"]

conversion_rates = [
    control_rate * 100,
    treatment_rate * 100,
]

errors = [
    control_error,
    treatment_error,
]


project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "images"
output_folder.mkdir(exist_ok=True)

output_path = output_folder / "ab_test_conversion.png"


plt.figure(figsize=(8, 5))

bars = plt.bar(
    labels,
    conversion_rates,
    yerr=errors,
    capsize=6,
)

plt.title(
    "A/B Test Conversion Rate\n"
    "Difference: -0.16 p.p.; p-value = 0.1897"
)
plt.ylabel("Conversion rate, %")
plt.ylim(0, 13)


for bar, value in zip(bars, conversion_rates):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        value + 0.2,
        f"{value:.2f}%",
        ha="center",
    )


plt.tight_layout()
plt.savefig(
    output_path,
    dpi=300,
    bbox_inches="tight",
)

plt.close()

print(f"График сохранён: {output_path}")
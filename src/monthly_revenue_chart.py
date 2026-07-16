from pathlib import Path

import matplotlib.pyplot as plt
import mysql.connector
import pandas as pd


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
    report_month,
    revenue
FROM monthly_product_metrics
ORDER BY report_month;
"""

cursor.execute(query)
rows = cursor.fetchall()

cursor.close()
connection.close()


data = pd.DataFrame(rows)

data["report_month"] = pd.to_datetime(
    data["report_month"]
)

data["revenue"] = data["revenue"].astype(float)
data["revenue_mln"] = data["revenue"] / 1_000_000

data["month_label"] = data[
    "report_month"
].dt.strftime("%Y-%m")


project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "images"
output_folder.mkdir(exist_ok=True)

output_path = output_folder / "monthly_revenue.png"


plt.figure(figsize=(11, 6))

plt.plot(
    data["month_label"],
    data["revenue_mln"],
    marker="o",
)

plt.ylabel("Revenue, million")

plt.title("Monthly Revenue")
plt.xlabel("Month")
plt.xticks(rotation=45)
plt.grid(axis="y", alpha=0.3)


for month, revenue in zip(
    data["month_label"],
    data["revenue_mln"],
):
    plt.text(
        month,
        revenue + 0.02,
        f"{revenue:.2f}M",
        ha="center",
        fontsize=8,
    )


plt.tight_layout()

plt.savefig(
    output_path,
    dpi=300,
    bbox_inches="tight",
)

plt.close()

print(f"График сохранён: {output_path}")
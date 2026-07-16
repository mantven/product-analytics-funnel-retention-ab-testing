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
WITH buyer_metrics AS (
    SELECT
        user_id,
        COUNT(*) AS purchases,
        SUM(price) AS revenue
    FROM clean_user_events
    WHERE event_type = 'purchase'
    GROUP BY user_id
)

SELECT
    CASE
        WHEN purchases = 1 THEN 'One-time buyers'
        ELSE 'Repeat buyers'
    END AS buyer_type,

    COUNT(*) AS buyers,
    SUM(purchases) AS purchases,
    SUM(revenue) AS revenue

FROM buyer_metrics

GROUP BY
    CASE
        WHEN purchases = 1 THEN 'One-time buyers'
        ELSE 'Repeat buyers'
    END;
"""

cursor.execute(query)
rows = cursor.fetchall()

cursor.close()
connection.close()


data = pd.DataFrame(rows)

data["revenue"] = data["revenue"].astype(float)

data["revenue_share_pct"] = (
    data["revenue"]
    / data["revenue"].sum()
    * 100
)

order = [
    "One-time buyers",
    "Repeat buyers",
]

data["buyer_type"] = pd.Categorical(
    data["buyer_type"],
    categories=order,
    ordered=True,
)

data = data.sort_values("buyer_type")


project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "images"
output_folder.mkdir(exist_ok=True)

output_path = (
    output_folder
    / "revenue_share_by_buyer_type.png"
)


plt.figure(figsize=(8, 5))

bars = plt.bar(
    data["buyer_type"],
    data["revenue_share_pct"],
)

plt.title("Revenue Share by Buyer Type")
plt.xlabel("Buyer type")
plt.ylabel("Revenue share, %")
plt.ylim(0, 100)
plt.grid(axis="y", alpha=0.3)


for bar, share, revenue in zip(
    bars,
    data["revenue_share_pct"],
    data["revenue"],
):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        share + 2,
        f"{share:.1f}%\n{revenue / 1_000_000:.2f}M",
        ha="center",
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
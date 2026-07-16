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
        COUNT(*) AS purchase_count
    FROM clean_user_events
    WHERE event_type = 'purchase'
    GROUP BY user_id
)

SELECT
    purchase_count,
    COUNT(*) AS buyers
FROM buyer_metrics
GROUP BY purchase_count
ORDER BY purchase_count;
"""

cursor.execute(query)
rows = cursor.fetchall()

cursor.close()
connection.close()


data = pd.DataFrame(rows)

data["purchase_count"] = data["purchase_count"].astype(int)
data["buyers"] = data["buyers"].astype(int)

data["buyers_share_pct"] = (
    data["buyers"]
    / data["buyers"].sum()
    * 100
)


project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "images"
output_folder.mkdir(exist_ok=True)

output_path = (
    output_folder
    / "buyers_by_purchase_count.png"
)


plt.figure(figsize=(10, 6))

bars = plt.bar(
    data["purchase_count"],
    data["buyers"],
)

plt.title("Buyer Distribution by Number of Purchases")
plt.xlabel("Number of purchases")
plt.ylabel("Number of buyers")
plt.xticks(data["purchase_count"])
plt.grid(axis="y", alpha=0.3)


for bar, buyers, share in zip(
    bars,
    data["buyers"],
    data["buyers_share_pct"],
):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        buyers + 45,
        f"{buyers}\n{share:.1f}%",
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
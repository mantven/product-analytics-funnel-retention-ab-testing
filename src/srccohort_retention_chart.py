from pathlib import Path

import matplotlib.pyplot as plt
import mysql.connector
import numpy as np
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
WITH purchase_months AS (
    SELECT DISTINCT
        user_id,
        CAST(
            DATE_FORMAT(event_datetime, '%Y-%m-01')
            AS DATE
        ) AS purchase_month
    FROM clean_user_events
    WHERE event_type = 'purchase'
),

first_purchases AS (
    SELECT
        user_id,
        MIN(purchase_month) AS cohort_month
    FROM purchase_months
    GROUP BY user_id
),

cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(*) AS cohort_size
    FROM first_purchases
    GROUP BY cohort_month
),

cohort_activity AS (
    SELECT
        f.cohort_month,

        TIMESTAMPDIFF(
            MONTH,
            f.cohort_month,
            p.purchase_month
        ) AS month_number,

        COUNT(DISTINCT p.user_id) AS active_buyers

    FROM first_purchases AS f

    INNER JOIN purchase_months AS p
        ON f.user_id = p.user_id

    GROUP BY
        f.cohort_month,
        TIMESTAMPDIFF(
            MONTH,
            f.cohort_month,
            p.purchase_month
        )
)

SELECT
    a.cohort_month,
    a.month_number,
    s.cohort_size,

    ROUND(
        a.active_buyers
        / s.cohort_size
        * 100,
        2
    ) AS retention_pct

FROM cohort_activity AS a

INNER JOIN cohort_sizes AS s
    ON a.cohort_month = s.cohort_month

ORDER BY
    a.cohort_month,
    a.month_number;
"""

cursor.execute(query)
rows = cursor.fetchall()

cursor.close()
connection.close()


data = pd.DataFrame(rows)

data["cohort_month"] = pd.to_datetime(
    data["cohort_month"]
)

data["month_number"] = data[
    "month_number"
].astype(int)

data["retention_pct"] = data[
    "retention_pct"
].astype(float)


# M0 не добавляем, потому что он всегда равен 100%
retention_data = data[
    data["month_number"] > 0
]

retention_table = retention_data.pivot(
    index="cohort_month",
    columns="month_number",
    values="retention_pct",
)

retention_table = retention_table.reindex(
    columns=range(1, 12)
)

retention_table.index = retention_table.index.strftime(
    "%Y-%m"
)

retention_table.columns = [
    f"M{month}"
    for month in retention_table.columns
]


values = retention_table.to_numpy(
    dtype=float
)

masked_values = np.ma.masked_invalid(values)


project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "images"
output_folder.mkdir(exist_ok=True)

output_path = (
    output_folder
    / "cohort_retention_heatmap.png"
)


plt.figure(figsize=(12, 7))

image = plt.imshow(
    masked_values,
    aspect="auto",
    cmap="Blues",
    vmin=0,
    vmax=20,
)

plt.colorbar(
    image,
    label="Retention rate, %",
)

plt.xticks(
    ticks=range(len(retention_table.columns)),
    labels=retention_table.columns,
)

plt.yticks(
    ticks=range(len(retention_table.index)),
    labels=retention_table.index,
)

plt.xlabel("Months since first purchase")
plt.ylabel("Cohort month")
plt.title("Cohort Retention by Purchase Month")


for row_number in range(values.shape[0]):
    for column_number in range(values.shape[1]):
        value = values[
            row_number,
            column_number,
        ]

        if not np.isnan(value):
            text_color = "white" if value >= 17 else "black"
            plt.text(
                column_number,
                row_number,
                f"{value:.1f}%",
                ha="center",
                va="center",
                fontsize=8,
                color=text_color,
            )


plt.tight_layout()

plt.savefig(
    output_path,
    dpi=300,
    bbox_inches="tight",
)

plt.close()

print(f"График сохранён: {output_path}")
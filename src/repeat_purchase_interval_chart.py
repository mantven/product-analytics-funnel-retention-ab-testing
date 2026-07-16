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
WITH ranked_purchases AS (
    SELECT
        user_id,
        event_datetime,

        ROW_NUMBER() OVER (
            PARTITION BY user_id
            ORDER BY event_datetime, event_id
        ) AS purchase_number

    FROM clean_user_events
    WHERE event_type = 'purchase'
),

first_two_purchases AS (
    SELECT
        user_id,

        MAX(
            CASE
                WHEN purchase_number = 1
                THEN event_datetime
            END
        ) AS first_purchase,

        MAX(
            CASE
                WHEN purchase_number = 2
                THEN event_datetime
            END
        ) AS second_purchase

    FROM ranked_purchases

    WHERE purchase_number <= 2

    GROUP BY user_id
),

repeat_buyers AS (
    SELECT
        user_id,

        DATEDIFF(
            second_purchase,
            first_purchase
        ) AS days_to_second_purchase

    FROM first_two_purchases

    WHERE second_purchase IS NOT NULL
),

grouped_buyers AS (
    SELECT
        CASE
            WHEN days_to_second_purchase = 0
                THEN '0 days'

            WHEN days_to_second_purchase BETWEEN 1 AND 7
                THEN '1-7 days'

            WHEN days_to_second_purchase BETWEEN 8 AND 30
                THEN '8-30 days'

            WHEN days_to_second_purchase BETWEEN 31 AND 60
                THEN '31-60 days'

            WHEN days_to_second_purchase BETWEEN 61 AND 90
                THEN '61-90 days'

            ELSE '91+ days'
        END AS repeat_period,

        CASE
            WHEN days_to_second_purchase = 0 THEN 1
            WHEN days_to_second_purchase BETWEEN 1 AND 7 THEN 2
            WHEN days_to_second_purchase BETWEEN 8 AND 30 THEN 3
            WHEN days_to_second_purchase BETWEEN 31 AND 60 THEN 4
            WHEN days_to_second_purchase BETWEEN 61 AND 90 THEN 5
            ELSE 6
        END AS period_number

    FROM repeat_buyers
)

SELECT
    repeat_period,
    period_number,
    COUNT(*) AS buyers

FROM grouped_buyers

GROUP BY
    repeat_period,
    period_number

ORDER BY period_number;
"""

cursor.execute(query)
rows = cursor.fetchall()

cursor.close()
connection.close()


data = pd.DataFrame(rows)

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
    / "repeat_purchase_interval.png"
)


plt.figure(figsize=(10, 6))

bars = plt.bar(
    data["repeat_period"],
    data["buyers_share_pct"],
)

plt.title("Time to Second Purchase")
plt.xlabel("Time between first and second purchase")
plt.ylabel("Share of repeat buyers, %")
plt.ylim(0, 52)
plt.grid(axis="y", alpha=0.3)


for bar, share, buyers in zip(
    bars,
    data["buyers_share_pct"],
    data["buyers"],
):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        share + 1,
        f"{share:.1f}%\n{buyers}",
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
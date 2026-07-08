import pandas as pd
csv_path = r"D:\2025_langchain_aivision\silmari\data\raw\administrative_dong.csv"
df_raw = pd.read_csv(
    csv_path,
    encoding="utf-8",
    dtype=str
)
df = df_raw.copy()
seoul_df = df[df["시도명"] == "서울특별시"]
seoul_df = seoul_df.drop_duplicates(subset=["행정동코드"])
seoul_df = seoul_df.drop(columns=["법정동명", ])
print(seoul_df.head)
# for row in seoul_df.itertuples(index=False):
#     gu=row[]
#     dong=row["행정동명"]

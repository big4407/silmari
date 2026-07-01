import pandas as pd
csv_path = r"D:\2025_langchain_aivision\silmari\backend\utils\국가데이터처_법정동 연계정보_20250602.csv"
df_raw = pd.read_csv(
    csv_path,
    encoding="cp949",
    dtype=str
)
df = df_raw.copy()
seoul_df = df[df["시도명"] == "서울특별시"]
seoul_df = seoul_df.drop_duplicates(subset=["행정동코드"])
print(seoul_df.head)
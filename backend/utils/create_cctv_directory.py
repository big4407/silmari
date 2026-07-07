import pandas as pd
from pathlib import Path
base_dir = Path(__file__).resolve().parents[2]
csv_path = r"D:\2025_langchain_aivision\silmari\data\raw\administrative_dong.csv"
df_raw = pd.read_csv(
    csv_path,
    encoding="utf-8",
    dtype=str
)
df = df_raw.copy()
seoul_df = df[df["시도명"] == "서울특별시"]
seoul_df = seoul_df[seoul_df["시도명"] != seoul_df["행정동명"]]
seoul_df = seoul_df[seoul_df["시군구명"] != seoul_df["행정동명"]]
seoul_df = seoul_df[['시도명', '시군구명', '행정동명', "행정동코드"]].drop_duplicates()
for _, row in seoul_df.iterrows():
    dong_code=row["행정동코드"]

    folder_path = base_dir / dong_code
    folder_path.mkdir(parents=True, exist_ok=True)
    print(folder_path)


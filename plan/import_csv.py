import pandas as pd
from sqlalchemy import create_engine

CSV_PATH = "sentiment_market_panel.csv"

MYSQL_USER = "zhijiandv"
MYSQL_PASSWORD = "zhijian123456"
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = "3306"
MYSQL_DB = "guardian_demo"

df = pd.read_csv(CSV_PATH)

engine = create_engine(
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)

df.to_sql(
    "sentiment_market_panel",
    engine,
    if_exists="replace",
    index=False
)

print("Imported sentiment_market_panel successfully")
print(df.shape)
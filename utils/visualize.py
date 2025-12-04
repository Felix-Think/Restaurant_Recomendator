import pandas as pd

path = "data/foody_page1.csv"

df = pd.read_csv(path)
print(df.head())
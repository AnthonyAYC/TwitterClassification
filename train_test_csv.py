import pandas as pd
from sklearn.model_selection import train_test_split

# =============================
# 1. CARREGAR CSV ORIGINAL
# =============================
csv_path = "csv_files/boamente_original.csv"

df = pd.read_csv("csv_files/boamente_original.csv")
df = df.dropna(subset=["text", "target"])
#df["text"] = df["text"].apply(tp.clean_text)
df.to_csv(csv_path, index=False)

#Divisão do dataset original
train_df, test_df = train_test_split(
    df,
    test_size=0.1,          # 80% treino / 20% teste
    random_state=42,        # reprodutibilidade
    stratify=df["target"]   # mantém proporção das classes
)

#Save do csv
train_df.to_csv("csv_files/boamente_train.csv", index=False)
test_df.to_csv("csv_files/boamente_test.csv", index=False)

print("Arquivos gerados com sucesso!")
print(f"Treino: {len(train_df)}")
print(f"Teste:  {len(test_df)}")

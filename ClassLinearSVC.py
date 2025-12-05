import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_predict
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC

#Definindo o dataframe
df = pd.read_csv('csv_files/boamente_dataset.csv')

#Variaveis independentes e dependentes
X = df['text'].values
y = df['target'].values

#Definindo o modelo
model = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1,2),
        max_features=20000
    )),
    ("svc", LinearSVC(class_weight="balanced"))
])

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

y_pred = cross_val_predict(model, X, y, cv=skf)

#Métricas
print("\n===== CLASSIFICATION REPORT =====\n")
print(classification_report(y, y_pred))

print("\n===== CONFUSION MATRIX =====\n")
print(confusion_matrix(y, y_pred))

#Exportando o csv com predições
df_target = pd.read_csv('csv_files/tweets.csv')
texts = df_target["text"].tolist()
model.fit(X, y)
preds = model.predict(texts)

result_df = pd.DataFrame({
    "text": texts,
    "pred": preds
})

result_df.to_csv("csv_files/results_LinearSVC.csv", index=False, encoding="utf-8")
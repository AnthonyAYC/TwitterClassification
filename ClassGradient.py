import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import RandomOverSampler

# Carregar o dataset de treino e teste
df_train = pd.read_csv('csv_files/boamente_train.csv').dropna()
X_train = df_train['text'].values
y_train = df_train['target'].values

df_test = pd.read_csv('csv_files/boamente_test.csv').dropna()
X_test = df_test['text'].values
y_test = df_test['target'].values

# Transformação dos textos para representação numérica e oversampling do dataset (melhores métricas obtidas)
model = ImbPipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=20000)),
    ("oversampler", RandomOverSampler(random_state=42)),
    ("clf", GradientBoostingClassifier(random_state=42))
])

# Treinamento
print("Iniciando treinamento com Gradient Boosting e Oversampling")
model.fit(X_train, y_train)

# Predição do modelo
y_pred = model.predict(X_test)

# Resultados
print("\n===== GRADIENT BOOSTING (OVERSAMPLED) =====\n")
print(classification_report(y_test, y_pred, digits=3))
print("\nMatriz de Confusão:\n", confusion_matrix(y_test, y_pred))
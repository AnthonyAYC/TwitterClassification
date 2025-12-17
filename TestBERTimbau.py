import pandas as pd
import torch
from sklearn.metrics import classification_report, confusion_matrix
from transformers import AutoTokenizer, AutoModelForSequenceClassification

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Caminho do modelo treinado
model_path = "best_model/modelo_ideacao_suicida_godlike"

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path).to(device)

# Carrega o dataset novamente
df = pd.read_csv("csv_files/boamente_test.csv")
texts = df["text"].tolist()
#labels = df["target"].tolist()

preds = []

def predict(text):
    inputs = tokenizer(text, return_tensors="pt", max_length=256, truncation=True, padding=True).to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    logits = outputs.logits
    probs = torch.softmax(logits, dim=1)
    return torch.argmax(probs).item()

# Inferência no dataset
for t in texts:
    p = predict(t)
    preds.append(p)
    print(f'{len(preds)}/{len(texts)}')

# Relatórios -> Se tiver df com label.
print("\n===== CLASSIFICATION REPORT =====\n")
print(classification_report(labels, preds, digits=3))

print("\n===== MATRIZ DE CONFUSÃO =====\n")
print(confusion_matrix(labels, preds))
'''
#Exportando o resultado
result_df = pd.DataFrame({
    "text": texts,
    "pred": preds
})

result_df.to_csv("csv_files/results_BERTimbau.csv", index=False, encoding="utf-8")
'''
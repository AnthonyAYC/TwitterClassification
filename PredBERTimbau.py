import pandas as pd
import torch
from sklearn.metrics import classification_report, confusion_matrix
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tqdm import tqdm

#Configs
BATCH_SIZE = 16  # Aumente se tiver muita VRAM, diminua se der erro de memória
MAX_LENGTH = 256
MODEL_PATH = "best_model/best_model_bert_base"
INPUT_FILE = "tweets/tweets_11.csv"
OUTPUT_FILE = "results/results_BERTimbau.csv"

#Verifica a placa
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Rodando em: {device}")

# Carregar modelo e tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH).to(device)
model.eval()  #desativar dropout/batchnorm

# Carregar dados
df = pd.read_csv(INPUT_FILE)
texts = df["text"].tolist()

#Verificação se há labels
has_labels = "target" in df.columns
if has_labels:
    true_labels = df["target"].tolist()

preds = []
probs_list =[]

print(f"Iniciando inferência em {len(texts)} textos...")

for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="Processando"):

    batch_texts = texts[i: i + BATCH_SIZE]

    inputs = tokenizer(
        batch_texts,
        return_tensors="pt",
        max_length=MAX_LENGTH,
        truncation=True,
        padding=True
    ).to(device)

    # Inferência otimizada
    with torch.inference_mode():  # Mais rápido que no_grad()
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=1)

        # Pega a classe com maior probabilidade
        batch_preds = torch.argmax(probs, dim=1).cpu().numpy()

        preds.extend(batch_preds)
        probs_list.extend(probs[:, 1].cpu().numpy()) # Se quiser guardar score da classe 1

# --- RELATÓRIOS E EXPORTAÇÃO ---

# Se o dataset tinha labels, mostra a performance
if has_labels:
    print("\n===== CLASSIFICATION REPORT =====")
    print(classification_report(true_labels, preds, digits=3))

    print("\n===== MATRIZ DE CONFUSÃO =====")
    print(confusion_matrix(true_labels, preds))

# Salva o resultado
print(f"\nSalvando resultados em {OUTPUT_FILE}...")
df["pred"] = preds
df["prob_suicidio"] = probs_list
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
print("Concluído!")
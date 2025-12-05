import pandas as pd
import evaluate
import numpy as np
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from transformers import TrainingArguments, Trainer

import torch

print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "Sem GPU")
print(torch.__version__)


# =============================
# 1. CARREGAR DATASET
# =============================
df = pd.read_csv("csv_files/boamente_dataset.csv")   # deve ter: text, target
df = df.dropna()

dataset = Dataset.from_pandas(df)

# =============================
# 2. TOKENIZER DO BERTIMBAU
# =============================
model_name = "neuralmind/bert-base-portuguese-cased"
tokenizer = AutoTokenizer.from_pretrained(model_name)

def tokenize(batch):
    return tokenizer(
        batch["text"],
        truncation=True,
        padding="max_length",
        max_length=128
    )

dataset = dataset.map(tokenize, batched=True)

# Necessário para o Trainer
dataset = dataset.rename_column("target", "labels")
dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

# Dividir treino/teste
dataset_split = dataset.train_test_split(test_size=0.2)

train_ds = dataset_split["train"]
test_ds = dataset_split["test"]

# =============================
# 3. CARREGAR MODELO
# =============================
model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=2
)

# =============================
# 4. MÉTRICAS
# =============================
accuracy = evaluate.load("accuracy")
precision = evaluate.load("precision")
recall = evaluate.load("recall")
f1 = evaluate.load("f1")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)

    return {
        "accuracy": accuracy.compute(predictions=preds, references=labels)["accuracy"],
        "precision": precision.compute(predictions=preds, references=labels, average="binary")["precision"],
        "recall": recall.compute(predictions=preds, references=labels, average="binary")["recall"],
        "f1": f1.compute(predictions=preds, references=labels, average="binary")["f1"]
    }

# =============================
# 5. TRAINING ARGUMENTS
# =============================
training_args = TrainingArguments(
    output_dir="./bertimbau-suicidio",
    eval_strategy="epoch",
    save_strategy="epoch",
    logging_steps=50,
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    do_eval=True,
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    push_to_hub=False
)

# =============================
# 6. TREINAR MODELO
# =============================
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=test_ds,
    compute_metrics=compute_metrics,
    processing_class=tokenizer
)

trainer.train()

# =============================
# 7. SALVAR MODELO
# =============================
trainer.save_model("modelo_ideacao_suicida")
tokenizer.save_pretrained("modelo_ideacao_suicida")

print("Treinamento finalizado!")

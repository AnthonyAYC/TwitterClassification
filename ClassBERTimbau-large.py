import pandas as pd
import evaluate
import numpy as np
import torch
from datasets import Dataset
from sklearn.utils.class_weight import compute_class_weight
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from transformers import TrainingArguments, Trainer


print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "Sem GPU")
print(torch.__version__)


#Carregar o dataset de treino
df = pd.read_csv("csv_files/boamente_train.csv")   # deve ter: text, target
df = df.dropna()

dataset = Dataset.from_pandas(df)

#Pesos opcionais (para testes)
class_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.unique(df["target"]),
    y=df["target"]
)

weights_tensor = torch.tensor(class_weights, dtype=torch.float)

print(f"Pesos calculados para as classes {np.unique(df['target'])}: {class_weights}")

# tokenizer padrão para treino do bertimbau
model_name = "neuralmind/bert-large-portuguese-cased"
tokenizer = AutoTokenizer.from_pretrained(model_name)

def tokenize(batch):
    return tokenizer(
        batch["text"],
        truncation=True,
        padding="max_length",
        max_length=256
    )

dataset = dataset.map(tokenize, batched=True)

# Configurações do dataset para o trainer
dataset = dataset.rename_column("target", "labels")
dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

# train test split
dataset_split = dataset.train_test_split(test_size=0.1)

train_ds = dataset_split["train"]
test_ds = dataset_split["test"]

# Carregar modelo
model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=2
)

#Custom trainer (para testes)
class WeightedTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs.get("labels")

        outputs = model(**inputs)
        logits = outputs.get("logits")

        # Definição da Loss Function com os pesos
        # Garantimos que o peso esteja no mesmo device do modelo
        loss_fct = torch.nn.CrossEntropyLoss(weight=weights_tensor.to(model.device))

        # Calcula a loss
        loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))

        return (loss, outputs) if return_outputs else loss



# Métricas observadas
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

#Training Arguments
training_args = TrainingArguments(
    output_dir="./bertimbau-suicidio",
    eval_strategy="epoch",
    save_strategy="epoch",
    logging_steps=50,
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=4,
    weight_decay=0.01,
    do_eval=True,
    fp16=True,
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    push_to_hub=False
)

#Treinamento do modelo
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=test_ds,
    compute_metrics=compute_metrics,
    processing_class=tokenizer
)

trainer.train()

#Save do modelo
trainer.save_model("modelo_ideacao_suicida_large")
tokenizer.save_pretrained("modelo_ideacao_suicida_large")

print("Treinamento finalizado!")
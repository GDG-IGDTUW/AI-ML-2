from multilingual_model import load_model, SMSDataset
from transformers import Trainer, TrainingArguments
import pandas as pd
import torch

df = pd.read_csv("your_sms_dataset.csv")

train_texts, val_texts, train_labels, val_labels = train_test_split(
    df["text"], df["label"], test_size=0.2
)

train_dataset = SMSDataset(train_texts.tolist(), train_labels.tolist())
val_dataset = SMSDataset(val_texts.tolist(), val_labels.tolist())

model = load_model()

training_args = TrainingArguments(
    output_dir="./results",
    evaluation_strategy="epoch",
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    save_total_limit=2
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
)

trainer.train()

torch.save(model.state_dict(), "multilingual_sms_model.pt")

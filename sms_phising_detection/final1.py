from multilingual_model import load_model, tokenizer
from codeswitch_utils import is_code_switched
import torch

model = load_model()
model.load_state_dict(torch.load("multilingual_sms_model.pt"))
model.eval()

def predict_sms(text):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)
        confidence, prediction = torch.max(probs, dim=1)

    return {
        "prediction": "Phishing" if prediction.item() == 1 else "Legitimate",
        "confidence": confidence.item(),
        "code_switched": is_code_switched(text)
    }

# hate_speech_model.py
from transformers import pipeline
import config


class HateSpeechDetector:
    def __init__(self):
        # Initialize the classifier; this loads a relatively small, fast model.
        self.classifier = pipeline(
            "text-classification", model="unitary/toxic-bert", return_all_scores=True
        )
        self.threshold = config.HATE_SPEECH_THRESHOLD

    def detect(self, text):
        results = self.classifier(text)
        # The classifier returns a list (per sample) of dicts with 'label' and 'score'
        for result in results[0]:
            # Here we assume labels like "toxic" indicate hate speech.
            if (
                result["label"].lower() in ["toxic", "hate"]
                and result["score"] > self.threshold
            ):
                return True
        return False

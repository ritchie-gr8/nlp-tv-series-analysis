import torch
from transformers import pipeline
from nltk.tokenize import sent_tokenize
import numpy as np
import pandas as pd
import os
import sys
import pathlib
import nltk

folder_path = pathlib.Path(__file__).parent.resolve()
sys.path.append(os.path.join(folder_path, "../"))

from utils.data_loader import load_subtitle_dataset

nltk.download("punkt")
nltk.download("punkt_tab")

class ThemeClassifier:
  def __init__(self, theme_list):
    self.model_name = "facebook/bart-large-mnli"
    self.theme_list = theme_list

    if torch.cuda.is_available():
        self.device = torch.device('cuda')
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        self.device = torch.device('mps')
    else:
        self.device = torch.device('cpu')

    self.theme_classifier = self.load_model(self.device)


  def load_model(self, device):
    theme_classifier = pipeline(
      "zero-shot-classification",
      model = self.model_name,
      device = device
    )
    return theme_classifier

  def get_theme_inference(self, script):
    script_sentences = sent_tokenize(script)

    # Batch sentence
    sentence_batch_size = 20
    script_batches = []
    for index in range(0, len(script_sentences), sentence_batch_size):
      sent = " ".join(script_sentences[index:index + sentence_batch_size])
      script_batches.append(sent)

    # Run model
    theme_output = self.theme_classifier(
      script_batches[:2],
      self.theme_list,
      multi_label=True,
    )

    # Wrangle output
    themes = {}
    for output in theme_output:
      for label, score in zip(output["labels"], output["scores"]):
        if label not in themes:
          themes[label] = []
        themes[label].append(score)

    themes = {
      key: np.mean(np.array(val)) for key, val in themes.items()
    }

    return themes

  def get_themes(self, dataset_path, save_path = None):
    if save_path is not None and os.path.exists(save_path):
      df = pd.read_csv(save_path)
      return df

    df = load_subtitle_dataset(dataset_path)
    df = df.head(2)

    output_themes = df["script"].apply(self.get_theme_inference)
    themes_df = pd.DataFrame(output_themes.tolist())
    df[themes_df.columns] = themes_df

    if save_path:
      df.to_csv(save_path, index=False)

    return df


from tensorflow.keras.models import load_model
from utils.clean import downsample_mono, envelope
from kapre.time_frequency import STFT, Magnitude, ApplyFilterbank, MagnitudeToDecibel
from sklearn.preprocessing import LabelEncoder
import numpy as np
from glob import glob
import argparse
import os
import pandas as pd
from tqdm import tqdm
import tempfile
import requests
import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# sys.stdout = open(os.devnull, 'w')
# sys.stderr = open(os.devnull, 'w')


def download_file(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        raise ValueError(f"Failed to download file from URL: {url}")


def make_prediction(model_url, src_dir):

    # Download model file
    model_content = download_file(model_url)

    # Create a temporary file to save the model content
    temp_model_file = tempfile.NamedTemporaryFile(delete=False)
    temp_model_file.write(model_content)
    temp_model_file.close()

    model = load_model(temp_model_file.name,
                       custom_objects={'STFT': STFT,
                                       'Magnitude': Magnitude,
                                       'ApplyFilterbank': ApplyFilterbank,
                                       'MagnitudeToDecibel': MagnitudeToDecibel})
    wav_paths = glob('{}/**'.format(src_dir), recursive=True)
    wav_paths = sorted([x.replace(os.sep, '/')
                       for x in wav_paths if '.wav' in x])
    classes = sorted(os.listdir(src_dir))
    labels = [os.path.split(x)[0].split('/')[-1] for x in wav_paths]
    le = LabelEncoder()
    y_true = le.fit_transform(labels)
    results = []

    for z, wav_fn in enumerate(wav_paths):
        rate, wav = downsample_mono(wav_fn, 16000)
        mask, env = envelope(wav, rate, threshold=20)
        clean_wav = wav[mask]
        step = int(16000*3.0)
        batch = []

        for i in range(0, clean_wav.shape[0], step):
            sample = clean_wav[i:i+step]
            sample = sample.reshape(-1, 1)
            if sample.shape[0] < step:
                tmp = np.zeros(shape=(step, 1), dtype=np.float32)
                tmp[:sample.shape[0], :] = sample.flatten().reshape(-1, 1)
                sample = tmp
            if sample.shape[0] == 0:
                continue  # Skip empty sample

            batch.append(sample)

        if len(batch) == 0:
            continue  # Skip empty batch

        X_batch = np.array(batch, dtype=np.float32)
        y_pred = model.predict(X_batch)
        y_mean = np.mean(y_pred, axis=0)
        y_pred = np.argmax(y_mean)
        real_class = os.path.dirname(wav_fn).split('/')[-1]
        file_name = os.path.basename(wav_fn)
        predicted_class = classes[y_pred]

        if real_class != predicted_class:
            os.remove(wav_fn)  # Remove misclassified file

        results.append(y_mean)

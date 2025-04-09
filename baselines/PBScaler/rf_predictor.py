import pathlib

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from utils import io_util

class Predictor:
    def __init__(self):
        self.predictor = RandomForestClassifier(n_estimators=100, random_state=42)

    def train(self, dir: str, namespace: str, deployments: list):
        path = pathlib.Path(f'{dir}/{namespace}')
        deployments = sorted(deployments)
        data_cols = []
        data, labels = None, None
        for f in path.rglob('record.csv'):
            record = pd.read_csv(f)
            if len(data_cols) == 0:
                p90_cols = [ms+'&count' for ms in deployments]
                qps_cols = [ms+'&qps' for ms in deployments]
                data_cols = p90_cols+qps_cols
                data = record[data_cols].values
                labels = record['istio-ingressgateway&0.9'].apply(self.convert_to_binary).to_numpy()
            else:
                data = np.vstack([data, record[data_cols].values])
                labels = np.concatenate([labels, record['istio-ingressgateway&0.9'].apply(self.convert_to_binary).to_numpy()])

        X_train, X_val, y_train, y_val = train_test_split(data, labels, test_size=0.3, random_state=42, stratify=labels)
        self.predictor.fit(X_train, y_train)
        y_pred = self.predictor.predict(X_val)
        precision = precision_score(y_val, y_pred, average='binary')
        recall = recall_score(y_val, y_pred, average='binary')
        f1 = f1_score(y_val, y_pred, average='binary')
        auc = roc_auc_score(y_val, y_pred) 

        print(f"Precision: {precision:.4f}")
        print(f"Recall: {recall:.4f}")
        print(f"F1 Score: {f1:.4f}")
        print(f"AUC: {auc:.4f}")
        io_util.save_pkl(f'baselines/PBScaler/{namespace}.pkl', self.predictor)


    def convert_to_binary(self, x):
        return 1 if x > 500 else 0

    def predict(self, data):
        return self.predictor.predict(data)


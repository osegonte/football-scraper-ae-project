"""
AutoEncoder Model
==================
Contains the AggregatedPlayerDataset and AggregationAutoencoder model.
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from torch.utils.data import Dataset

def clean_dataset(df):
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)
    return df

class AggregatedPlayerDataset(Dataset):
    def _init_(self, df, target_date, alpha=0.1):
        df = clean_dataset(df)
        if 'Home/Away' in df.columns:
            df['Home/Away'] = pd.to_numeric(df['Home/Away'], errors='coerce')

        self.target_date = pd.to_datetime(target_date)
        target_players = df[df['Date'] == self.target_date]
        target_ids = set(target_players['Player_ID'])

        df_hist = df[df['Date'] < self.target_date]
        hist_ids = set(df_hist['Player_ID'])

        valid_ids = target_ids.intersection(hist_ids)

        df = df[df['Player_ID'].isin(valid_ids)]

        df_train = df[df['Date'] < self.target_date]
        df_val = df[df['Date'] == self.target_date]

        df_train['TimeDiff'] = (self.target_date - df_train['Date']).dt.days
        df_train['Weight'] = np.exp(-alpha * df_train['TimeDiff'])

        numeric_cols = df_train.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [col for col in numeric_cols if col not in ['Weight', 'TimeDiff']]

        df_train[feature_cols] = df_train[feature_cols].apply(pd.to_numeric, errors='coerce')
        df_val[feature_cols] = df_val[feature_cols].apply(pd.to_numeric, errors='coerce')

        aggregated = (
            df_train[['Player_ID', 'Weight'] + feature_cols]
            .groupby('Player_ID')
            .apply(lambda group: group[feature_cols].multiply(group['Weight'], axis=0).sum() / group['Weight'].sum())
            .reset_index()
        )

        common_cols = list(set(feature_cols).intersection(df_val.columns))

        self.aggregated_features = []
        self.target_values = []
        self.player_ids = []

        for pid in aggregated['Player_ID'].unique():
            row = aggregated.loc[aggregated['Player_ID'] == pid, common_cols].values[0].astype(np.float32)
            target = df_val[df_val['Player_ID'] == pid][common_cols].iloc[0].values.astype(np.float32)

            self.aggregated_features.append(row)
            self.target_values.append(target)
            self.player_ids.append(pid)

        self.aggregated_features = np.array(self.aggregated_features)
        self.target_values = np.array(self.target_values)

    def __len__(self):
        return len(self.aggregated_features)

    def __getitem__(self, idx):
        return torch.tensor(self.aggregated_features[idx]), torch.tensor(self.target_values[idx]), self.player_ids[idx]
        #optional alternative
        """return (
                torch.tensor(self.aggregated_features[idx], dtype=torch.float32),
                torch.tensor(self.target_values[idx], dtype=torch.float32),
                self.player_ids[idx]
        )"""
class AggregationAutoencoder(nn.Module):
    def __init__(self, input_dim, encoding_dims=[128, 64, 32]):
        super(AggregationAutoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, encoding_dims[0]), nn.ReLU(),
            nn.Linear(encoding_dims[0], encoding_dims[1]), nn.ReLU(),
            nn.Linear(encoding_dims[1], encoding_dims[2]), nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(encoding_dims[2], encoding_dims[1]), nn.ReLU(),
            nn.Linear(encoding_dims[1], encoding_dims[0]), nn.ReLU(),
            nn.Linear(encoding_dims[0], input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

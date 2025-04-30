"""
Player Latents Extraction
=========================
Functions to extract player latent vectors using trained autoencoders.
"""
import pandas as pd
import torch
import numpy as np

def get_player_latent_vector(model, player_df, target_date, alpha=0.1):
    """
    Aggregates a player's historical stats and extracts a latent vector using the encoder.
    
    Args:
        model: Trained AggregationAutoencoder model.
        player_df (pd.DataFrame): Player historical data.
        target_date (str): Target date in 'YYYY-MM-DD' format.
        alpha (float): Decay parameter.

    Returns:
        np.array: Latent vector for the player.
    """
    target_date = pd.to_datetime(target_date)
    player_df = player_df[player_df['Date'] < target_date].copy()

    if player_df.empty:
        print(f"Warning: No historical data for player before {target_date}")
        return None

    if 'Home/Away' in player_df.columns:
        player_df['Home/Away'] = pd.to_numeric(player_df['Home/Away'], errors='coerce')

    player_df['TimeDiff'] = (target_date - player_df['Date']).dt.days
    player_df['Weight'] = np.exp(-alpha * player_df['TimeDiff'])

    numeric_cols = player_df.select_dtypes(include=[np.number]).columns.tolist()
    exclude_cols = ['Player_ID', 'Date', 'TimeDiff', 'Weight']
    feature_cols = [col for col in numeric_cols if col not in exclude_cols]

    feature_df = player_df[feature_cols].fillna(0)

    weighted_sum = feature_df.multiply(player_df['Weight'].values, axis=0).sum(axis=0)
    weight_total = player_df['Weight'].sum()

    if weight_total == 0:
        print("Warning: Zero total weight")
        return None

    aggregated_vector = (weighted_sum / weight_total).values.astype(np.float32)

    model.eval()
    with torch.no_grad():
        features_tensor = torch.tensor(aggregated_vector).unsqueeze(0)
        latent_vector = model.encoder(features_tensor).numpy()

    return latent_vector.squeeze()

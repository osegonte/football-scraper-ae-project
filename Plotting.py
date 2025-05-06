"""
Plotting Module
==============
Visualization tools for player embeddings and team statistics.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

def plot_player_embeddings(latent_vectors, player_ids, metadata=None, method='pca', **kwargs):
    """
    Plot player embeddings in 2D using dimensionality reduction.
    
    Args:
        latent_vectors (np.array): Array of player latent vectors
        player_ids (list): List of player IDs corresponding to latent vectors
        metadata (pd.DataFrame, optional): DataFrame with player metadata like position, team
        method (str): Dimensionality reduction method ('pca' or 'tsne')
        **kwargs: Additional arguments for the dimensionality reduction
    
    Returns:
        matplotlib.figure.Figure: The generated figure
    """
    # Apply dimensionality reduction
    if method.lower() == 'pca':
        model = PCA(n_components=2, **kwargs)
    elif method.lower() == 'tsne':
        model = TSNE(n_components=2, **kwargs)
    else:
        raise ValueError(f"Unknown method: {method}. Use 'pca' or 'tsne'.")
    
    embeddings_2d = model.fit_transform(latent_vectors)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Basic scatter plot
    scatter = ax.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], alpha=0.7)
    
    # Add metadata coloring if available
    if metadata is not None:
        # Example: Color by position
        if 'Position' in metadata.columns:
            positions = metadata.set_index('Player_ID').loc[player_ids, 'Position']
            scatter = ax.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], 
                               c=positions, cmap='viridis', alpha=0.7)
            plt.colorbar(scatter, ax=ax, label='Position')
    
    # Add annotations for some points
    for i, player_id in enumerate(player_ids):
        # Add labels for notable players or randomly sample some players
        if np.random.random() < 0.05:  # Label ~5% of players
            ax.annotate(player_id, (embeddings_2d[i, 0], embeddings_2d[i, 1]))
    
    plt.title(f'Player Embeddings ({method.upper()})')
    plt.tight_layout()
    
    return fig

# Add more plotting functions as needed
# Football Scraper AE Project

This project scrapes player-level football data from SofaScore, preprocesses it, and applies an Autoencoder to generate player latent representations.
## Purpose 
This project scrapes football match statistics from SofaScore, preprocesses the data across multiple games, and trains an autoencoder model to extract meaningful player embeddings. The embeddings are visualized using PCA and t-SNE to reveal player similarity patterns across leagues and positions. 
The purpose is to fit a model that given past performances, we'll extract a player form in a fixed timestamp.
The end goal is to achieve a informative low dimension representation by using the autoencoders' output for latent space of players' game stats.


//add system requierments


## Structure
- scraping: SofaScore game data scraper
- preprocessing: Data cleaning and normalization
- modeling: Autoencoder model, training, and latent extraction
- notebooks: Project walkthrough and visualizations
- data: Folder for raw scraped Excel files (not uploaded)
- outputs: Folder for outputs like final CSVs (not uploaded)

## General Steps
1. Scrape match data using sofascore_scraper.py.
2. Preprocess using preprocessing_pipeline.py.
3. Train Autoencoder and extract latent vectors.
4. Visualize and analyze results using project_walkthrough.ipynb.

## Screping & Preprocessing 
short explain
**Further** explaination on technical steps and scraping and preprocessing can be fouhnd in "link to ..."

## Training 
## Testing 
## Visualize
## Requirements
```bash
pip install -r requirements.txt

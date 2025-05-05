# Football Scraper AE Project

This project scrapes player-level football data from SofaScore, preprocesses it, and applies an Autoencoder to generate player latent representations.

//add system requierments


## Structure
- scraping: SofaScore game data scraper
- preprocessing: Data cleaning and normalization
- modeling: Autoencoder model, training, and latent extraction
- notebooks: Project walkthrough and visualizations
- data: Folder for raw scraped Excel files (not uploaded)
- outputs: Folder for outputs like final CSVs (not uploaded)

## Steps
1. Scrape match data using sofascore_scraper.py.
2. Preprocess using preprocessing_pipeline.py.
3. Train Autoencoder and extract latent vectors.
4. Visualize and analyze results using project_walkthrough.ipynb.

## Requirements
```bash
pip install -r requirements.txt

# Football Scraper AE Project

This project scrapes player-level football data from SofaScore, preprocesses it, and applies an Autoencoder to generate player latent representations.
## Purpose 
This project scrapes football match statistics from SofaScore, preprocesses the data across multiple games, and trains an autoencoder model to extract meaningful player embeddings. The embeddings are visualized using PCA and t-SNE to reveal player similarity patterns across leagues and positions. 
The purpose is to fit a model that given past performances, extracts a player form for a fixed timestamp.
The end goal is to achieve a informative low dimension representation by using the encoders' output for latent space of players' game stats.


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

## Scraping & Preprocessing 
Before training the autoencoder, raw match statitics are scraped from SofaScore and after that are preprocessed to autoencoder ready input.
**Scarping** 
First, the inputs are start date, end date, Country, league and season. the scraper is built from two main modules, the first one opens SofaScore, and navigates through the site to the specified season and league and collects the URLs of all matches played in that season in between the dates. The second module of the scraper gets all the URLs and iterates all over them and one by one, loads the match and scrapes all the stats to one data frame. lastly all the data concats and converted to one xlsx file.

Important notes  - the scraper navigates throught the site using HTML elements that might change overtime. It is recommended to first try explore this option in case of bugs. The first module (URL collection) is more prone to crashes from time to time, when scraping large amounnts of data (more than a couple os seasons), we recommend to verify that the URL collection is finished.
**Preprocessing**
We identify uniqely each (playerID, date) as a different record.
Preprocessing takes in the data, keeps the relevant columns, extracts ratings table aside and the goes over the columns so that every important colum consists of one number, so rates (succusful/attempted) columns are separated. position, home/away on the field also translated to numbers.
All aggregative stats are divided by minutes played attributed to normalize performances and finally miuntes played is normalized as well to (0,1]

**Further** explaination on technical steps and scraping and preprocessing can be found in [here](Data/Technicalities.md)


## Training 
## Testing 
## Visualize
## Requirements
```bash
pip install -r requirements.txt

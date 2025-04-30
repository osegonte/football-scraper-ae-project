"""
Preprocessing Pipeline
=======================
Preprocess SofaScore scraped data into a clean, normalized dataset ready for modeling.
"""

import pandas as pd
import numpy as np

def fix_dates(df, filename):
    """
    Fix season-specific date formatting issues.
    """
    year_part1 = filename.split('_')[1].split('-')[0][1] #e.g. 2019 -> 9
    year_part2 = filename.split('_')[1].split('-')[1][1] #e.g. 2020 -> 0

    flag = True
    new_dates = []
    last_month = 100 * 100

    for _, row in df.iterrows():
        if len(row['Date']) == 8:
            new_dates.append(row['Date'])
        elif len(row['Date']) == 7:
            month = int(row['Date'][2:4])
            if month > last_month:
                flag = False
            last_month = month
            new_date = row['Date'] + (year_part2 if flag else year_part1)
            new_dates.append(new_date)

    df['Date'] = new_dates
    return df

def preprocess_df(df):
    """
    Preprocess a SofaScore season dataset.
    """
    columns_to_drop = ['Duels (won)', 'Sofascore Rating', 'Notes Attack', 'Defensive actions',
                       'Notes Defence', 'Notes Passing', 'Notes Goalkeeper']

    sofaScore_rating_df = df[['Player_ID', 'Date', 'Sofascore Rating']]
    df = df.drop(columns=columns_to_drop, errors='ignore')

    df['Minutes played'] = df['Minutes played'].str.replace(r"(\d+)'", r'\1', regex=True).astype(float)

    parenthesis_columns = [col for col in df.columns if '(' in col and col != 'Expected Goals (xG)']
    for column in parenthesis_columns:
        base_name = column.split(' (')[0] + " Total"
        inner_name = column.split(' (')[0] + " Successful"
        df[[base_name, inner_name]] = df[column].str.extract(r'(\d+)\s*\((\d+)\)')
        df[base_name] = pd.to_numeric(df[base_name], errors='coerce')
        df[inner_name] = pd.to_numeric(df[inner_name], errors='coerce')
        df.drop(columns=[column], inplace=True)

    if 'Accurate passes' in df.columns:
        df[['Successful Passes', 'Pass Attempts']] = df['Accurate passes'].str.extract(r'(\d+)/(\d+)').astype(float)
        df.drop(columns=['Accurate passes'], inplace=True)

    df.fillna(0, inplace=True)

    non_normed = ['Player', 'Player_ID', 'Team', 'Position', 'Home/Away', 'Date', 'Score', 'Minutes played']
    columns_to_normalize = [col for col in df.columns if col not in non_normed]

    df[columns_to_normalize] = df[columns_to_normalize].div(df['Minutes played'], axis=0)
    df['Minutes played'] = df['Minutes played'] / 90

    position_map = {'G': 0, 'D': 1/3, 'M': 2/3, 'F': 1}
    df['Position'] = df['Position'].apply(lambda x: position_map.get(x, None))

    def extract_goals(row):
        is_home = row['Home/Away']
        goals_for, goals_against = row['Score'].split('-') if is_home == '1' else row['Score'].split('-')[::-1]
        return pd.Series([int(goals_for), int(goals_against)])
        #optional exception catch
        """
        try:
            parts = row['Score'].split('-')
            if len(parts) != 2:
                return pd.Series([0, 0])
            goals_for, goals_against = parts if row['Home/Away'] == '1' else parts[::-1]
            return pd.Series([int(goals_for), int(goals_against)])
        except:
            return pd.Series([0, 0])
        """

    df[['Goals for', 'Goals against']] = df.apply(extract_goals, axis=1)

    df['Date'] = pd.to_datetime(df['Date'], format="%d%m%Y", errors="coerce")

    df = df.drop(columns=['Player', 'Team', 'Score'], errors='ignore')

    return df, sofaScore_rating_df

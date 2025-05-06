"""
Team Stats Preprocessing
=======================
Preprocess team statistics from SofaScore into a clean dataset ready for analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def preprocess_team_stats(df):
    """
    Preprocess team statistics dataframe.
    
    Args:
        df (pd.DataFrame): Raw team statistics dataframe
        
    Returns:
        pd.DataFrame: Processed team statistics dataframe
    """
    # Convert date to datetime if it's not already
    df['date'] = pd.to_datetime(df['date'], format="%Y%m%d")
    
    # Ensure numeric columns are numeric
    numeric_columns = ['gf', 'ga', 'sh', 'sot', 'dist', 'fk', 'pk', 'pkatt']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Add calculated columns that might be useful
    df['goal_diff'] = df['gf'] - df['ga']
    df['shot_accuracy'] = np.where(df['sh'] > 0, df['sot'] / df['sh'], 0)
    df['pk_conversion'] = np.where(df['pkatt'] > 0, df['pk'] / df['pkatt'], 0)
    
    # Add match result column (win/loss/draw)
    df['result'] = 'draw'
    df.loc[df['gf'] > df['ga'], 'result'] = 'win'
    df.loc[df['gf'] < df['ga'], 'result'] = 'loss'
    
    # Convert scrape_date to datetime if string
    if isinstance(df['scrape_date'].iloc[0], str):
        df['scrape_date'] = pd.to_datetime(df['scrape_date'])
        
    return df

def get_team_form(team_stats_df, team_name, target_date=None, num_matches=7):
    """
    Get the form of a team based on their last N matches before a target date.
    
    Args:
        team_stats_df (pd.DataFrame): Team statistics dataframe
        team_name (str): Name of the team
        target_date (str or datetime, optional): Target date. If None, uses today's date
        num_matches (int): Number of recent matches to consider
        
    Returns:
        pd.DataFrame: Last N matches for the team before target date
    """
    if target_date is None:
        target_date = datetime.now()
    elif isinstance(target_date, str):
        target_date = pd.to_datetime(target_date)
    
    # Filter for the specific team and matches before target_date
    team_df = team_stats_df[(team_stats_df['team'] == team_name) & 
                           (team_stats_df['date'] < target_date)]
    
    # Sort by date descending and get the most recent N matches
    team_form = team_df.sort_values('date', ascending=False).head(num_matches)
    
    return team_form

def aggregate_team_form(team_form_df, weighted=True, alpha=0.1):
    """
    Aggregate team form statistics, optionally with exponential time weighting.
    
    Args:
        team_form_df (pd.DataFrame): Team form dataframe from get_team_form
        weighted (bool): Whether to apply time-based weighting
        alpha (float): Decay parameter for exponential weighting
        
    Returns:
        dict: Aggregated team statistics
    """
    if team_form_df.empty:
        return {}
    
    # Sort by date ascending for correct time weighting
    df = team_form_df.sort_values('date')
    
    if weighted:
        # Calculate days from first match in set
        first_date = df['date'].min()
        df['days_from_first'] = (df['date'] - first_date).dt.days
        
        # Apply exponential weighting
        df['weight'] = np.exp(alpha * df['days_from_first'])
        weight_sum = df['weight'].sum()
        
        # Numeric columns to aggregate
        numeric_cols = ['gf', 'ga', 'sh', 'sot', 'dist', 'fk', 'pk', 'pkatt', 
                         'goal_diff', 'shot_accuracy', 'pk_conversion']
        
        # Compute weighted averages
        weighted_stats = {}
        for col in numeric_cols:
            if col in df.columns:
                weighted_stats[f'avg_{col}'] = (df[col] * df['weight']).sum() / weight_sum
        
        # Add form indicators
        results_count = df['result'].value_counts()
        weighted_stats['wins'] = results_count.get('win', 0)
        weighted_stats['draws'] = results_count.get('draw', 0)
        weighted_stats['losses'] = results_count.get('loss', 0)
        weighted_stats['points'] = weighted_stats['wins'] * 3 + weighted_stats['draws']
        
        return weighted_stats
    else:
        # Simple averages
        numeric_cols = ['gf', 'ga', 'sh', 'sot', 'dist', 'fk', 'pk', 'pkatt', 
                         'goal_diff', 'shot_accuracy', 'pk_conversion']
        
        avg_stats = {}
        for col in numeric_cols:
            if col in df.columns:
                avg_stats[f'avg_{col}'] = df[col].mean()
        
        # Add form indicators
        results_count = df['result'].value_counts()
        avg_stats['wins'] = results_count.get('win', 0)
        avg_stats['draws'] = results_count.get('draw', 0)
        avg_stats['losses'] = results_count.get('loss', 0)
        avg_stats['points'] = avg_stats['wins'] * 3 + avg_stats['draws']
        
        return avg_stats

def compile_team_recent_form(team_stats_df, teams, target_date=None, num_matches=7):
    """
    Compile recent form for multiple teams.
    
    Args:
        team_stats_df (pd.DataFrame): Team statistics dataframe
        teams (list): List of team names
        target_date (str or datetime, optional): Target date
        num_matches (int): Number of recent matches to consider
        
    Returns:
        pd.DataFrame: Dataframe with aggregated form data for each team
    """
    team_forms = []
    
    for team in teams:
        # Get recent form for the team
        form_df = get_team_form(team_stats_df, team, target_date, num_matches)
        
        # Aggregate the form data
        form_stats = aggregate_team_form(form_df)
        
        if form_stats:
            form_stats['team'] = team
            form_stats['form_date'] = target_date
            form_stats['matches_included'] = len(form_df)
            team_forms.append(form_stats)
    
    if team_forms:
        return pd.DataFrame(team_forms)
    else:
        return pd.DataFrame()

def get_recent_matches_for_all_teams(df, num_matches=7):
    """
    Get last N matches for all teams in the dataset.
    
    Args:
        df (pd.DataFrame): Team statistics dataframe
        num_matches (int): Number of recent matches to retrieve per team
        
    Returns:
        dict: Dictionary with team names as keys and their recent matches as values
    """
    teams = df['team'].unique()
    team_matches = {}
    
    for team in teams:
        # Get today's date as default target date
        today = datetime.now()
        
        # Get recent form
        team_form = get_team_form(df, team, today, num_matches)
        team_matches[team] = team_form
    
    return team_matches
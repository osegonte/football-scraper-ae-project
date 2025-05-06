"""
Team Form Scraper
================
Main script to scrape and analyze team form based on recent matches.
"""

import argparse
import os
import time
import pandas as pd
from datetime import datetime
import json

from scraper.team_stats_scraper import get_team_last_matches
from preprocessing.team_stats_preprocessing import preprocess_team_stats, compile_team_recent_form

def scrape_team_data(team_names, num_matches=7, output_dir="data"):
    """
    Scrape match data for multiple teams and save to CSV.
    
    Args:
        team_names (list): List of team names to scrape
        num_matches (int): Number of recent matches to retrieve
        output_dir (str): Directory to save output files
        
    Returns:
        pd.DataFrame: Combined dataframe of all team match data
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    all_match_data = []
    
    for i, team in enumerate(team_names):
        print(f"[{i+1}/{len(team_names)}] Scraping data for {team}...")
        
        try:
            # Get recent matches for team
            team_matches = get_team_last_matches(team, num_matches)
            
            if team_matches:
                # Save team data to individual CSV
                team_df = pd.DataFrame(team_matches)
                team_filename = os.path.join(output_dir, f"{team.replace(' ', '_')}_matches.csv")
                team_df.to_csv(team_filename, index=False)
                print(f"  - Saved {len(team_matches)} matches to {team_filename}")
                
                # Add to combined data
                all_match_data.extend(team_matches)
            else:
                print(f"  - No match data found for {team}")
                
            # Wait between teams to avoid overloading the server
            if i < len(team_names) - 1:
                time.sleep(2)
                
        except Exception as e:
            print(f"  - Error scraping data for {team}: {e}")
    
    # Create and save combined dataset if we have data
    if all_match_data:
        combined_df = pd.DataFrame(all_match_data)
        combined_filename = os.path.join(output_dir, "all_team_matches.csv")
        combined_df.to_csv(combined_filename, index=False)
        print(f"Saved combined data with {len(all_match_data)} matches to {combined_filename}")
        return combined_df
    else:
        print("No match data was collected.")
        return pd.DataFrame()

def analyze_team_form(match_data_df, target_date=None, num_matches=7, output_dir="outputs"):
    """
    Analyze team form based on their recent matches.
    
    Args:
        match_data_df (pd.DataFrame): Combined match data
        target_date (str or datetime): Target date for analysis
        num_matches (int): Number of recent matches to consider
        output_dir (str): Directory to save output files
        
    Returns:
        pd.DataFrame: Team form analysis dataframe
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Preprocess the match data
    processed_df = preprocess_team_stats(match_data_df)
    
    # Get all unique teams
    teams = processed_df['team'].unique().tolist()
    
    # Compile team form
    team_form_df = compile_team_recent_form(processed_df, teams, target_date, num_matches)
    
    if not team_form_df.empty:
        # Save team form data
        form_filename = os.path.join(output_dir, "team_form_analysis.csv")
        team_form_df.to_csv(form_filename, index=False)
        print(f"Saved team form analysis to {form_filename}")
        
        # Create a summary report
        summary = team_form_df.sort_values('points', ascending=False)[
            ['team', 'points', 'wins', 'draws', 'losses', 'avg_gf', 'avg_ga', 'avg_sh', 'avg_sot']
        ].round(2)
        
        summary_filename = os.path.join(output_dir, "team_form_summary.csv")
        summary.to_csv(summary_filename, index=False)
        print(f"Saved team form summary to {summary_filename}")
        
        return team_form_df
    else:
        print("No team form data could be generated.")
        return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser(description="Scrape and analyze team form data")
    parser.add_argument('--teams', type=str, help='Path to JSON file with team names or comma-separated list of teams')
    parser.add_argument('--matches', type=int, default=7, help='Number of recent matches to scrape per team')
    parser.add_argument('--data_dir', type=str, default='data', help='Directory to save raw data')
    parser.add_argument('--output_dir', type=str, default='outputs', help='Directory to save analysis outputs')
    args = parser.parse_args()
    
    # Get list of teams
    if args.teams:
        if args.teams.endswith('.json'):
            # Load from JSON file
            with open(args.teams, 'r') as f:
                teams = json.load(f)
        else:
            # Parse comma-separated list
            teams = [team.strip() for team in args.teams.split(',')]
    else:
        # Default to some example teams
        teams = ["Bayern Munich", "Real Madrid", "Manchester City", "Barcelona"]
    
    print(f"Will scrape data for {len(teams)} teams: {', '.join(teams)}")
    
    # Step 1: Scrape match data for teams
    match_data = scrape_team_data(teams, args.matches, args.data_dir)
    
    if not match_data.empty:
        # Step 2: Analyze team form
        analyze_team_form(match_data, None, args.matches, args.output_dir)
    else:
        print("No match data to analyze.")

if __name__ == "__main__":
    main()
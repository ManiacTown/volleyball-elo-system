# 
#
# ELO TRACKER FOR VOLLEYBALL
#
# VERSION 1.0.3, 2/1/2025, Avery Miclea

import gspread
from google.oauth2.service_account import Credentials
from math import pow
from datetime import datetime
from itertools import combinations
import streamlit as st
import json

st.write(st.secrets["GOOGLE_CREDS"])

# Load Google Credentials from Streamlit secrets
creds_data = st.secrets["GOOGLE_CREDS"]

# If it's a string, parse it; otherwise, use it as is
if isinstance(creds_data, str):
    creds_dict = json.loads(creds_data)  # Convert JSON string to dict
else:
    creds_dict = creds_data  # It's already a dictionary

# Authenticate with Google Sheets
credentials = Credentials.from_service_account_info(creds_dict)# scopes=["https://www.googleapis.com/auth/spreadsheets"])
client = gspread.authorize(credentials)

# Google Sheets authentication
#SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
#CREDS_FILE = 'google_creds.json'  # credentials file path

#credentials = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
#client = gspread.authorize(credentials)

# Open the spreadsheet and worksheet
SPREADSHEET_NAME = "Volleyball ELO Tracker"
SHEET_NAME = "ELO_Data"
PLAYER_TAB_NAME = "ELO_Data"
MATCH_HISTORY_TAB_NAME = "Match History"

# Constants
DEFAULT_ELO = 1000
K_FACTOR = 32

# Access the spreadsheet and worksheet
spreadsheet = client.open(SPREADSHEET_NAME)
elo_sheet = spreadsheet.worksheet(SHEET_NAME)
player_sheet = spreadsheet.worksheet(PLAYER_TAB_NAME)
match_sheet = spreadsheet.worksheet(MATCH_HISTORY_TAB_NAME)

# Test
def get_all_names():
    expected_headers = ["Player Name"]
    data = player_sheet.get_all_records(expected_headers=expected_headers)
    return {row['Player Name'] for row in data}

# Get all player data
def get_all_players():
    """Fetch all player names and their ELO ratings."""
    data = player_sheet.get_all_records()
    return {row['Player Name']: row['Rating'] for row in data}

def get_player_stats():
    """Fetch all player stats from the Google Sheet and return them as a dictionary."""
    try:
        # Define the expected headers (adjust them to match your sheet headers)
        expected_headers = ["Player Name", "Rating", "Matches", "Streak"]
        
        # Fetch all records with expected headers
        records = player_sheet.get_all_records(expected_headers=expected_headers)

        # Convert the list of records into a dictionary keyed by player name
        player_stats = {
            record["Player Name"]: {
                "Player Name": record["Player Name"],
                "elo": int(record["Rating"]),
                "matches": int(record["Matches"]),
                "streak": int(record["Streak"]),
            }
            for record in records if record["Player Name"]
        }
        
        return player_stats
    except Exception as e:
        print(f"Error fetching player stats: {e}")
        return {}

def update_google_sheet(player_stats):
    """Update the Google Sheets with the player stats."""
    data_to_update = []
    
    # Iterate over the player stats to prepare data for batch update
    for i, (player, stats) in enumerate(player_stats.items(), start=2):
        row = [stats["Player Name"], stats["elo"], stats["matches"], stats["streak"]]
        data_to_update.append({
            'range': f'A{i}:D{i}',  # Update the row for the player
            'values': [row]  # The row of data to write
        })
    
    # Perform batch update of all player data
    player_sheet.batch_update(data_to_update)
    print("Google Sheet updated successfully.")

def add_player(player_name):
    """Add a new player to the sheet with the default ELO."""
    players = get_all_players()
    if player_name in players:
        print(f"Player {player_name} already exists!")
        return

    # Add new player to the next available row
    next_row = len(players) + 2  # Account for header row
    player_sheet.update_cell(next_row, 1, player_name)
    player_sheet.update_cell(next_row, 2, DEFAULT_ELO)
    player_sheet.update_cell(next_row, 3, 0)  # Matches Played
    player_sheet.update_cell(next_row, 4, 0)  # Streak
    print(f"Player {player_name} added with default ELO of {DEFAULT_ELO}.")
    sort_leaderboard()

# Update a player's ELO rating
def update_player_elo(player_name, new_elo):
    """Update a player's ELO rating."""
    players = get_all_players()
    if player_name not in players:
        print(f"Player {player_name} not found! Adding them as a new player.")
        add_player(player_name)

    # Find the row of the player
    data = player_sheet.get_all_records()
    row = next(i + 2 for i, p in enumerate(data) if p['Player Name'] == player_name)
    player_sheet.update_cell(row, 2, new_elo)
    print(f"Player {player_name}'s ELO updated to {new_elo}.")

# Sort leaderboard by ELO in descending order
def sort_leaderboard(player_stats):
    """Sort the leaderboard and update Google Sheets in a single batch."""
    try:
        # Retrieve player data and sort by ELO in descending order
        sorted_players = sorted(player_stats.items(), key=lambda x: x[1]["elo"], reverse=True)

        # Prepare sorted data for the Google Sheets update
        rows_to_update = []
        for player, stats in sorted_players:
            rows_to_update.append([player, stats["elo"], stats["matches"], stats["streak"]])

        # Define the range to update all rows
        range_to_update = f"A2:D{len(sorted_players) + 1}"
        
        # Correct order of arguments or use named arguments
        player_sheet.update(range_name=range_to_update, values=rows_to_update)

        print("Leaderboard sorted and updated successfully.")
    except Exception as e:
        print(f"Failed to sort leaderboard: {e}")

# Log match details in the Match History tab
def log_match(team1, team2, score):
    """Log match details and update stats."""
    team1_names = [name.strip() for name in team1.split(",")]
    team2_names = [name.strip() for name in team2.split(",")]
    score1, score2 = map(int, score.split("-"))

    player_stats = get_player_stats()
    
    # Calculate ELO changes
    team1_elo = [player_stats[name]["elo"] for name in team1_names]
    team2_elo = [player_stats[name]["elo"] for name in team2_names]
    changes1, changes2 = calculate_elo_change(team1_elo, team2_elo, score1, score2, player_stats, team1, team2)

    # Update stats for Team 1
    for idx, player in enumerate(team1):
        player_stats[player]["elo"] += changes1[idx]
        player_stats[player]["matches"] += 1
        # Adjust the streak depending on the score comparison
        if score1 > score2:  # Winning streak
            player_stats[player]["streak"] += 1
        elif score1 < score2:  # Losing streak
            player_stats[player]["streak"] -= 1

    # Update stats for Team 2
    for idx, player in enumerate(team2):
        player_stats[player]["elo"] += changes2[idx]
        player_stats[player]["matches"] += 1
        # Adjust the streak depending on the score comparison
        if score2 > score1:  # Winning streak
            player_stats[player]["streak"] += 1
        elif score2 < score1:  # Losing streak
            player_stats[player]["streak"] -= 1

    update_google_sheet(player_stats)
    match_date = datetime.now().strftime("%m-%d-%Y")
    match_sheet.append_row([match_date, ",".join(team1_names), ",".join(team2_names), score])
    print("Match logged and stats updated.")
    
# Calculate the baseline ELO for each player based on their match history
def get_baseline(player_stats, player):
    """Calculate the baseline ELO for each player based on their match history."""
    if player not in player_stats:
        print(f"Player {player} not found in player stats!")
        return 40  # Default baseline ELO if player is not found

    matches = player_stats[player]["matches"]
    #print(matches)
    if matches < 2:
        return 40
    elif matches < 4:
        return 35
    elif matches < 6:
        return 30
    elif matches < 8:
        return 25
    elif matches < 10:
        return 20
    else:
        return 15

# Calculate the ELO changes after the matches
def calculate_elo_change(team1_elo, team2_elo, score1, score2, player_stats, team1, team2):
    #team1_avg_elo = sum(team1_elo) / len(team1_elo)
    #team2_avg_elo = sum(team2_elo) / len(team2_elo)
    margin = abs(score1 - score2)

    #expected1 = 1 / (1 + 10 ** ((team2_avg_elo - team1_avg_elo) / 400))
    #expected2 = 1 / (1 + 10 ** ((team1_avg_elo - team2_avg_elo) / 400))

    result1 = 1 if score1 > score2 else -1
    result2 = 1 if score2 > score1 else -1

    margin_adjustment = min(5, margin // 3) if margin >= 3 else 0
    #elo_diff_adjustment = int(abs(team1_avg_elo - team2_avg_elo) / 100) * 3
    #if team1_avg_elo > team2_avg_elo:
        #elo_diff_adjustment *= -1

    changes1, changes2 = [], []
    
    # Loop through players in team 1
    for player in team1:  # Use player names from the team
        baseline = get_baseline(player_stats, player)
        #print("baseline1 is ")
        #print(baseline)
        streak_adjustment = 2 * player_stats[player]["streak"]
        #print("Streak1 is ")
        #print(streak_adjustment)
        change = round((baseline*result1 + streak_adjustment + margin_adjustment*result1))# + elo_diff_adjustment) * (result1 - expected1))
        changes1.append(change)

    # Loop through players in team 2
    for player in team2:  # Use player names from the team
        baseline = get_baseline(player_stats, player)
        #print("baseline2 is ")
        #print(baseline)
        streak_adjustment = 2 * player_stats[player]["streak"]
        #print("Streak2 is ")
        #print(streak_adjustment)
        change = round((baseline*result2 + streak_adjustment + margin_adjustment*result2))# + elo_diff_adjustment) * (result2 - expected2))
        changes2.append(change)

    return changes1, changes2

# Match input and processing
def process_match():
    # Take input for the teams
    team1_input = input("Enter Team 1 players (comma-separated): ").split(",")
    team2_input = input("Enter Team 2 players (comma-separated): ").split(",")
    
    # Strip any whitespace and create the actual team lists
    team1 = [p.strip() for p in team1_input]
    team2 = [p.strip() for p in team2_input]
    
    # Ensure team1 and team2 are correctly initialized
    print(f"Team 1: {team1}")
    print(f"Team 2: {team2}")
    
    # Add players to the system if they don't already exist
    #for player in team1 + team2:
    #    add_player(player)

    # Get match score
    score = input("Enter the score (e.g., 21-18): ")
    score1, score2 = map(int, score.split("-"))

    # Get the player stats (ELO, matches, streak)
    player_stats = get_player_stats()

    # Use the player names to get the ELO values
    try:
        team1_elo = [player_stats[p]["elo"] for p in team1]
        team2_elo = [player_stats[p]["elo"] for p in team2]
    except KeyError as e:
        print(f"Error: Player '{e}' not found in player stats. Please check the player names.")
        return

    # Debug ELOs being used
    print(f"Team 1 ELOs: {team1_elo}")
    print(f"Team 2 ELOs: {team2_elo}")

    # Calculate the ELO changes based on the match result
    changes1, changes2 = calculate_elo_change(team1_elo, team2_elo, score1, score2, player_stats, team1, team2)

    # Debug the changes
    print(f"ELO changes for Team 1: {changes1}")
    print(f"ELO changes for Team 2: {changes2}")

    # Update player stats for team 1
    for i, player in enumerate(team1):
        player_stats[player]["elo"] += changes1[i]
        player_stats[player]["matches"] += 1
        if score1 > score2:
            if player_stats[player]["streak"] >= 0:
                player_stats[player]["streak"] += 1
            else:
                player_stats[player]["streak"] = 1
        else:
            if player_stats[player]["streak"] >= 0:
                player_stats[player]["streak"] = -1
            else:
                player_stats[player]["streak"] -= 1
        #player_stats[player]["streak"] += 1 if score1 > score2 else -player_stats[player]["streak"]

    # Update player stats for team 2
    for i, player in enumerate(team2):
        player_stats[player]["elo"] += changes2[i]
        player_stats[player]["matches"] += 1
        if score2 > score1:
            if player_stats[player]["streak"] >= 0:
                player_stats[player]["streak"] += 1
            else:
                player_stats[player]["streak"] = 1
        else:
            if player_stats[player]["streak"] >= 0:
                player_stats[player]["streak"] = -1
            else:
                player_stats[player]["streak"] -= 1
        #player_stats[player]["streak"] += 1 if score2 > score1 else -player_stats[player]["streak"]

    #log_match(', '.join(team1), ', '.join(team2), f"{score1}-{score2}")

    # Update Google Sheets with new stats
    update_google_sheet(player_stats)

    # After updating ELOs, sort the leaderboard by ELO
    sort_leaderboard(player_stats)
    print("Match processed and stats updated.")

# Create a match by inputing the players that are there
def create_match():
    """
    Create two balanced teams based on ELO ratings of players.

    Args:
        player_stats (dict): Dictionary of player statistics, including ELO scores.

    Returns:
        tuple: Two lists representing the teams.
    """

    player_stats = get_player_stats()
    
    # Step 1: Get player input
    player_input = input("Enter the names of players (comma-separated): ")
    player_names = [name.strip() for name in player_input.split(",")]

    # Step 2: Retrieve player ELOs
    player_elo = []
    for name in player_names:
        if name in player_stats:
            player_elo.append((name, player_stats[name]['elo']))
        else:
            print(f"Warning: Player '{name}' not found. Assigning default ELO of 1000.")
            player_elo.append((name, 1000))  # Default ELO for missing players.

    # Step 3: Sort players by ELO (descending)
    player_elo.sort(key=lambda x: x[1], reverse=True)

    num_players = len(player_elo)
    half_size = num_players // 2

    # Generate all possible combinations for Team 1
    all_combinations = list(combinations(player_elo, half_size))
    
    best_team1, best_team2 = None, None
    smallest_elo_diff = float('inf')
    
    for team1 in all_combinations:
        # Create Team 2 as the complement of Team 1
        team1_set = set(team1)
        team2 = [player for player in player_elo if player not in team1_set]
        
        # Calculate ELO totals
        team1_elo = sum(player[1] for player in team1)
        team2_elo = sum(player[1] for player in team2)
        
        # Find the ELO difference
        elo_diff = abs(team1_elo - team2_elo)
        
        # Update the best teams if this split is better
        if elo_diff < smallest_elo_diff:
            print(elo_diff)
            smallest_elo_diff = elo_diff
            best_team1, best_team2 = team1, team2
            best_team1_elo, best_team2_elo = team1_elo, team2_elo

    # Extract player names for the final teams
    team1_names = [player[0] for player in best_team1]
    team2_names = [player[0] for player in best_team2]

    print(f"Team 1: {team1_names}, Total ELO: {best_team1_elo}")
    print(f"Team 2: {team2_names}, Total ELO: {best_team2_elo}")

    return team1_names, team2_names

def create_match_button(player_list):

    player_stats = get_player_stats()

    # Step 2: Retrieve player ELOs
    player_elo = []
    for name in player_list:
        if name in player_stats:
            player_elo.append((name, player_stats[name]['elo']))
        else:
            print(f"Warning: Player '{name}' not found. Assigning default ELO of 1000.")
            player_elo.append((name, 1000))  # Default ELO for missing players.

    # Step 3: Sort players by ELO (descending)
    player_elo.sort(key=lambda x: x[1], reverse=True)

    num_players = len(player_elo)
    half_size = num_players // 2

    # Generate all possible combinations for Team 1
    all_combinations = list(combinations(player_elo, half_size))
    
    best_team1, best_team2 = None, None
    smallest_elo_diff = float('inf')
    
    for team1 in all_combinations:
        # Create Team 2 as the complement of Team 1
        team1_set = set(team1)
        team2 = [player for player in player_elo if player not in team1_set]
        
        # Calculate ELO totals
        team1_elo = sum(player[1] for player in team1)
        team2_elo = sum(player[1] for player in team2)
        
        # Find the ELO difference
        elo_diff = abs(team1_elo - team2_elo)
        
        # Update the best teams if this split is better
        if elo_diff < smallest_elo_diff:
            print(elo_diff)
            smallest_elo_diff = elo_diff
            best_team1, best_team2 = team1, team2
            best_team1_elo, best_team2_elo = team1_elo, team2_elo

    # Extract player names for the final teams
    team1_names = [player[0] for player in best_team1]
    team2_names = [player[0] for player in best_team2]

    print(f"Team 1: {team1_names}, Total ELO: {best_team1_elo}")
    print(f"Team 2: {team2_names}, Total ELO: {best_team2_elo}")

    return team1_names, team2_names
    

if __name__ == "__main__":

    # Has to happen
    #splayer_stats = get_player_stats()  # Fetch player stats from Google Sheets

    # Header
    print("")
    print("========================================================")
    print("WELCOME TO VOLLEYBALL ELO TRACKER")
    print("Version 1.0.1")
    print("Developed by Avery Miclea")
    print("========================================================")
    print("Commands (for now):")
    print("     1.) process_match() --> Log the scores and teams")
    print("     2.) create_match(player_stats) --> Create teams based upon ELO data")
    print("========================================================")
    print("Steps to setup the bot for the night:")
    print("     1.) python")
    print("     2.) from elo_project import process_match")
    print("     3.) from elo_project import create_match")
    print("     4.) use those functions ( e.g process_match() )")
    print("========================================================")
    print("")

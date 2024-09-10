import requests
import json
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import re

load_dotenv()

player = os.getenv("PLAYER")

headers = {
    "User-Agent": os.getenv("EMAIL")
}

def extract_moves(pgn):
    # Remove the metadata before the actual moves (anything before the first move number)
    pgn_without_metadata = re.sub(r"(\[.*?\]\n)+", "", pgn, flags=re.DOTALL)

    # Remove clock data, which is enclosed in curly braces and starts with [%clk]
    pgn_without_timestamps = re.sub(r"\{.*?\}", "", pgn_without_metadata).strip()

    # Remove move numbers followed by '...'
    pgn_without_black_move_numbers = re.sub(r"\d+\.\.\.\s?", "", pgn_without_timestamps)

    # Return the cleaned PGN string
    return pgn_without_black_move_numbers

def extract_player_color(game_data):
    white_player = game_data['white']['username']
    
    if player == white_player:
        return 'white'
    else:
        return 'black'

# Step 1: Fetch the list of archives from the Chess.com API
def fetch_archives(player):
    url = f"https://api.chess.com/pub/player/{player}/games/archives"
    print(f"Fetching archives from {url}")
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("archives", [])
    else:
        print(f"Failed to fetch archives: {response.status_code}")
        return []

# Step 2: Fetch games from each archive
def fetch_games_from_archive(archive_url):
    response = requests.get(archive_url, headers=headers)
    if response.status_code == 200:
        return response.json().get("games", [])
    else:
        print(f"Failed to fetch games from {archive_url}: {response.status_code}")
        return []

# Step 3: Filter archives for the past year
def filter_past_year_archives(archives):
    one_year_ago = datetime.now() - timedelta(days=365)
    filtered_archives = []

    for archive_url in archives:
        try:
            # Extract year and month from the URL
            parts = archive_url.split("/")
            year, month = int(parts[-2]), int(parts[-1])
            archive_date = datetime(year, month, 1)
            
            if archive_date > one_year_ago:
                filtered_archives.append(archive_url)
        except Exception as e:
            print(f"Error parsing date from {archive_url}: {e}")

    return filtered_archives

# Step 4: Fetch all games for the past year
def fetch_all_games(player):
    archives = fetch_archives(player)
    past_year_archives = filter_past_year_archives(archives)
    
    all_games = []
    for archive_url in past_year_archives:
        games = fetch_games_from_archive(archive_url)
        for game in games:
            all_games.append({
                "id": game.get("uuid"),
                "url": game.get("url"),
                "pgn": extract_moves(game.get("pgn")),
                "end_time": game.get("end_time"),
                "color": extract_player_color(game)
            })

    # Sort games by end_time
    all_games.sort(key=lambda x: x["end_time"])
    return all_games

def save_games_to_db(games, db_name="chess_games.db"):
    # Connect to the SQLite database (creates the file if it doesn't exist)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create a table to store chess game data if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chess_games (
            id TEXT UNIQUE,
            url TEXT NOT NULL,
            pgn TEXT NOT NULL,
            end_time INTEGER,
            color TEXT
        )
    ''')

    # Insert each game into the database
    for game in games:
        cursor.execute('''
            INSERT INTO chess_games (id, url, pgn, end_time, color)
            VALUES (?, ?, ?, ?, ?)
        ''', (game['id'], game['url'], game['pgn'], game['end_time'], game['color']))

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()

# Main function to execute the script
if __name__ == "__main__":
    games = fetch_all_games(player)
    save_games_to_db(games)
    print(f"Saved {len(games)} games to chess_games.db")

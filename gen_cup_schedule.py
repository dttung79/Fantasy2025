import csv
import random
from itertools import combinations

def read_teams(filename):
    """Read teams from the teams.txt file."""
    with open(filename, 'r') as file:
        teams = [line.strip() for line in file.readlines() if line.strip()]
    return teams

def generate_round_robin_schedule(teams):
    """Generate a round-robin schedule for the given teams using proper algorithm."""
    if len(teams) % 2 != 0:
        teams.append("BYE")  # Add a bye team if odd number of teams
    
    num_teams = len(teams)
    num_rounds = num_teams - 1
    matches_per_round = num_teams // 2
    
    schedule = []
    
    # Use the standard round-robin algorithm
    # Fix one team (team 0) and rotate others
    for round_num in range(num_rounds):
        round_matches = []
        
        # Create two lists: fixed team and rotating teams
        fixed_team = teams[0]
        rotating_teams = teams[1:]
        
        # Rotate the teams for this round
        rotated_teams = rotating_teams[round_num:] + rotating_teams[:round_num]
        
        # Pair teams: fixed with opposite, then pairs from both ends
        for i in range(matches_per_round):
            if i == 0:
                # Fixed team plays with the last team in rotated list
                team1 = fixed_team
                team2 = rotated_teams[-1]
            else:
                # Pair teams from both ends of the remaining list
                team1 = rotated_teams[i-1]
                team2 = rotated_teams[-(i+1)]
            
            # Skip matches with BYE team
            if team1 != "BYE" and team2 != "BYE":
                round_matches.append((team1, team2))
        
        schedule.append(round_matches)
    
    return schedule

def validate_round_robin_schedule(teams, schedule):
    """Validate that each team plays each other team exactly once."""
    all_matches = []
    for round_matches in schedule:
        all_matches.extend(round_matches)
    
    # Create a set to track all unique pairings
    pairings = set()
    team_opponents = {team: set() for team in teams if team != "BYE"}
    
    for team1, team2 in all_matches:
        # Create a canonical pairing (sorted order)
        pair = tuple(sorted([team1, team2]))
        
        # Check for duplicate pairings
        if pair in pairings:
            print(f"ERROR: Duplicate pairing found: {team1} vs {team2}")
            return False
        pairings.add(pair)
        
        # Track opponents for each team
        team_opponents[team1].add(team2)
        team_opponents[team2].add(team1)
    
    # Verify each team plays exactly n-1 opponents (where n is number of teams)
    expected_opponents = len([t for t in teams if t != "BYE"]) - 1
    
    for team, opponents in team_opponents.items():
        if len(opponents) != expected_opponents:
            print(f"ERROR: Team {team} plays {len(opponents)} opponents, expected {expected_opponents}")
            print(f"  Opponents: {opponents}")
            return False
    
    print(f"✅ Schedule validation PASSED: Each team plays exactly {expected_opponents} different opponents")
    return True

def save_tournament_to_csv(schedule, tournament_num, filename_prefix="tournament"):
    """Save tournament schedule to a CSV file."""
    filename = f"{filename_prefix}_{tournament_num}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Week', 'Team1', 'Team2'])
        
        for week, matches in enumerate(schedule, 1):
            for team1, team2 in matches:
                writer.writerow([week, team1, team2])

def main():
    """Main function to generate 5 tournaments."""
    # Read teams from file
    teams = read_teams('teams.txt')
    print(f"Loaded {len(teams)} teams: {teams}")
    
    # Generate 5 tournaments
    for tournament_num in range(1, 6):
        print(f"Generating tournament {tournament_num}...")
        
        # Shuffle teams for each tournament to create variety
        shuffled_teams = teams.copy()
        random.shuffle(shuffled_teams)
        
        # Generate schedule
        schedule = generate_round_robin_schedule(shuffled_teams)
        
        # Validate schedule
        print(f"Validating tournament {tournament_num}...")
        if not validate_round_robin_schedule(shuffled_teams, schedule):
            print(f"❌ Tournament {tournament_num} validation FAILED!")
            continue
        
        # Save to CSV
        save_tournament_to_csv(schedule, tournament_num)
        
        print(f"Tournament {tournament_num} saved to tournament_{tournament_num}.csv")
        print(f"  - {len(schedule)} rounds")
        print(f"  - {sum(len(matches) for matches in schedule)} total matches")
        print()

if __name__ == "__main__":
    main()

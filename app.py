from flask import Flask, render_template, request, jsonify
from extract_live_new import extract_league_data
import os
import pandas as pd
from datetime import datetime
import csv

app = Flask(__name__, static_url_path='/static')

@app.route('/')
def index():
    return build_league_page('week_tpl.html', 1798895)

@app.route('/week/<league_id>')
def week(league_id):
    return build_league_page('week_tpl.html', league_id)

@app.route('/cup/<int:cup_number>')
def cup(cup_number):
    return build_cup_page('cup_tpl.html', cup_number)

@app.route('/api/week/<league_id>')
def get_weeks_data(league_id):
    """
    Fetch weeks data for the given league_id.
    Checks current time against deadlines to determine if live data should be fetched.
    """
    try:
        # Read deadlines to get current week info
        current_week, deadline_passed = get_current_week_info()
        
        if deadline_passed:
            # Get live data and merge with historical data
            data = get_live_and_historical_data(league_id, current_week)
        else:
            # Just return historical data from weeks.csv
            data = get_historical_data()
        
        # Return data with current week information
        response = {
            "data": data,
            "current_week": current_week,
            "deadline_passed": deadline_passed
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cup/<int:cup_number>')
def get_cup_data(cup_number):
    """
    Fetch cup data for the given cup number.
    Returns standings, schedule, and results.
    """
    try:
        # Get current week info
        current_week, deadline_passed = get_current_week_info()
        
        # Get cup weeks range
        cup_weeks = get_cup_weeks(cup_number)
        
        # Get tournament schedule
        tournament_data = get_tournament_data(cup_number)
        
        # Get team points data
        team_points = get_team_points_for_cup(cup_weeks, current_week, deadline_passed)
        
        # Calculate standings
        standings = calculate_cup_standings(tournament_data, team_points, cup_weeks, current_week)
        
        # Prepare schedule with results
        schedule = prepare_cup_schedule(tournament_data, team_points, cup_weeks, current_week)
        
        # Cup info
        cup_info = {
            "current_week": current_week,
            "deadline_passed": deadline_passed,
            "weeks": cup_weeks
        }
        
        response = {
            "cup_info": cup_info,
            "standings": standings,
            "schedule": schedule
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_current_week_info():
    """
    Read deadlines.txt and determine current week and if deadline has passed.
    Returns: (current_week, deadline_passed)
    """
    try:
        with open('deadlines.txt', 'r') as f:
            lines = f.read().strip().split('\n')
        
        # Get the last line which contains the current/latest week
        last_line = lines[-1].strip()
        
        # Parse format: "3: 2025-08-30, 17:00"
        week_num = int(last_line.split(':')[0])
        deadline_str = last_line.split(':', 1)[1].strip()
        
        # Parse deadline string to datetime
        # Format: "2025-08-30, 17:00"
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d, %H:%M")
        except ValueError:
            # If parsing fails, assume deadline has passed
            deadline = datetime.now()
        
        # Check if current time has passed the deadline
        now = datetime.now()
        deadline_passed = now >= deadline
        
        return week_num, deadline_passed
    except Exception as e:
        # If error reading deadlines, assume we're in week 1 and deadline passed
        return 1, True

def get_historical_data():
    """
    Read and format data from weeks.csv for frontend consumption.
    Returns: 2D array with headers and team data in "points:hits" format
    """
    df = pd.read_csv('weeks.csv')
    
    # Convert DataFrame to the format expected by frontend
    data = []
    
    # Add headers row
    headers = df.columns.tolist()
    data.append(headers)
    
    # Add team rows
    for _, row in df.iterrows():
        team_row = [row['team']]  # First column is team name
        
        # Add week data (skip team column)
        for col in headers[1:]:
            value = row[col]
            if pd.isna(value) or value == '':
                team_row.append('0:0')  # Default for empty cells
            else:
                team_row.append(str(value))  # Keep existing format "points:hits"
        
        data.append(team_row)
    
    return data

def get_live_and_historical_data(league_id, current_week):
    """
    Get live data and merge with historical data.
    """
    # Get historical data first
    historical_data = get_historical_data()
    
    try:
        # Get live data
        live_df = extract_league_data(league_id)
        
        # Create a mapping of team names to live data
        live_data_map = {}
        for _, row in live_df.iterrows():
            team_name = row['team_name']
            live_points = row['live_points'] if pd.notna(row['live_points']) else 0
            hits = row['hits'] if pd.notna(row['hits']) else 0
            live_data_map[team_name] = f"{live_points}:{hits}"
        
        # Update historical data with live data for current week
        headers = historical_data[0]
        current_week_col_index = current_week  # Index in headers array (0=team, 1=week1, etc.)
        
        if current_week_col_index < len(headers):
            for i in range(1, len(historical_data)):  # Skip header row
                team_name = historical_data[i][0]
                
                # Try to match team names (case-insensitive, flexible matching)
                live_data = None
                for live_team, live_value in live_data_map.items():
                    if team_name.lower() in live_team.lower() or live_team.lower() in team_name.lower():
                        live_data = live_value
                        break
                
                if live_data:
                    # Ensure the row has enough columns
                    while len(historical_data[i]) <= current_week_col_index:
                        historical_data[i].append('0:0')
                    
                    historical_data[i][current_week_col_index] = live_data
        
        return historical_data
    
    except Exception as e:
        # If live data fetch fails, return historical data
        print(f"Error fetching live data: {e}")
        return historical_data

def build_league_page(filename, league_id):
    head = render_template('header_tpl.html', league_id=league_id)
    content = render_template(filename, league_id=league_id)
    footer = render_template('footer_tpl.html')
    return head + '\n' + content + '\n' + footer

def build_cup_page(filename, cup_number):
    head = render_template('header_tpl.html', league_id=1798895)
    content = render_template(filename, cup_number=cup_number)
    footer = render_template('footer_tpl.html')
    return head + '\n' + content + '\n' + footer

def get_cup_weeks(cup_number):
    """
    Get the weeks range for a specific cup.
    Each cup contains 7 weeks.
    Cup 1: weeks 1-7, Cup 2: weeks 8-14, etc.
    """
    start_week = (cup_number - 1) * 7 + 1
    end_week = cup_number * 7
    return list(range(start_week, end_week + 1))

def get_tournament_data(cup_number):
    """
    Read tournament data from tournament_{cup_number}.csv
    Returns: list of matches with week, team1, team2
    """
    try:
        filename = f'tournament_{cup_number}.csv'
        tournament_data = []
        
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tournament_data.append({
                    'week': int(row['Week']),
                    'team1': row['Team1'],
                    'team2': row['Team2']
                })
        
        return tournament_data
    except Exception as e:
        print(f"Error reading tournament data: {e}")
        return []

def get_team_points_for_cup(cup_weeks, current_week, deadline_passed):
    """
    Get team points for cup weeks, including live data if available.
    Returns: dict of {team_name: {week: points}}
    """
    try:
        # Get historical data from weeks.csv
        df = pd.read_csv('weeks.csv')
        team_points = {}
        
        for _, row in df.iterrows():
            team_name = row['team']
            team_points[team_name] = {}
            
            for week in cup_weeks:
                if week < len(df.columns):
                    week_col = str(week)  # week columns are named as numbers
                    if week_col in df.columns:
                        value = row[week_col]
                    else:
                        value = ''
                    
                    if pd.isna(value) or value == '':
                        points = 0
                    else:
                        # Parse "points:hits" format
                        parts = str(value).split(':')
                        points = int(parts[0]) if parts[0].isdigit() else 0
                    
                    team_points[team_name][week] = points
        
        # If current week is in cup and deadline passed, get live data
        if current_week in cup_weeks and deadline_passed:
            try:
                live_df = extract_league_data(1798895)
                for _, row in live_df.iterrows():
                    live_team = row['team_name']
                    live_points = row['live_points'] if pd.notna(row['live_points']) else 0
                    
                    # Find matching team in our data
                    for team_name in team_points:
                        if team_name.lower() in live_team.lower() or live_team.lower() in team_name.lower():
                            team_points[team_name][current_week] = live_points
                            break
            except Exception as e:
                print(f"Error getting live data: {e}")
        
        return team_points
    except Exception as e:
        print(f"Error getting team points: {e}")
        return {}

def calculate_match_result(team1_points, team2_points):
    """
    Calculate match result based on cup rules.
    Returns: ('win'/'draw'/'loss' for team1, points_difference)
    """
    diff = team1_points - team2_points
    
    if abs(diff) < 3:
        return 'draw', diff
    elif diff >= 3:
        return 'win', diff
    else:
        return 'loss', diff

def find_head_to_head_result(team1, team2, tournament_data, team_points, current_week):
    """
    Find head-to-head result between two teams.
    Returns: ('team1_wins', 'team2_wins', 'draw', head_to_head_week, team1_h2h_points, team2_h2h_points)
    """
    # Tìm trận đối đầu giữa 2 đội
    for match in tournament_data:
        week = match['week']
        if week >= current_week:
            continue
            
        if ((match['team1'] == team1 and match['team2'] == team2) or 
            (match['team1'] == team2 and match['team2'] == team1)):
            
            # Tìm điểm của 2 đội trong tuần đó
            if match['team1'] == team1:
                team1_points = team_points.get(team1, {}).get(week, 0)
                team2_points = team_points.get(team2, {}).get(week, 0)
            else:
                team1_points = team_points.get(team2, {}).get(week, 0)
                team2_points = team_points.get(team1, {}).get(week, 0)
                team1_points, team2_points = team2_points, team1_points
            
            result, diff = calculate_match_result(team1_points, team2_points)
            
            if result == 'win':
                return 'team1_wins', week, team1_points, team2_points
            elif result == 'loss':
                return 'team2_wins', week, team1_points, team2_points
            else:
                return 'draw', week, team1_points, team2_points
    
    # Không tìm thấy trận đối đầu
    return 'no_match', None, 0, 0

def get_team_total_hits(team_name, team_points, cup_weeks):
    """
    Calculate total hits (transfers) for a team during cup weeks.
    """
    total_hits = 0
    for week in cup_weeks:
        if team_name in team_points and week in team_points[team_name]:
            # team_points contains raw points, need to get hits from weeks.csv data
            # This will be handled in get_team_points_for_cup function
            pass
    return total_hits

def get_team_hits_from_data(team_name, week, raw_data_source):
    """
    Extract hits from the raw data source (weeks.csv format).
    Format: "points:hits" -> extract hits
    """
    try:
        # Read weeks.csv to get hits data
        import pandas as pd
        df = pd.read_csv('weeks.csv')
        
        if team_name in df['team'].values:
            week_col = str(week)
            if week_col in df.columns:
                team_row = df[df['team'] == team_name].iloc[0]
                value = team_row[week_col]
                
                if pd.notna(value) and ':' in str(value):
                    parts = str(value).split(':')
                    if len(parts) == 2 and parts[1].isdigit():
                        return int(parts[1])  # Return hits
        return 0
    except Exception:
        return 0

def apply_tiebreaker_rules(teams_with_same_points, tournament_data, team_points, current_week):
    """
    Apply tiebreaker rules for teams with same cup points:
    1. Head-to-head result
    2. If head-to-head is draw, compare points in that week  
    3. If still tied, compare total transfers (hits) - ai mua ít hơn xếp trên
    4. Fallback to goal difference
    """
    if len(teams_with_same_points) <= 1:
        return teams_with_same_points
    
    # Nếu chỉ có 2 đội, áp dụng head-to-head
    if len(teams_with_same_points) == 2:
        team1, team2 = teams_with_same_points
        
        h2h_result, h2h_week, team1_h2h_points, team2_h2h_points = find_head_to_head_result(
            team1['team_name'], team2['team_name'], tournament_data, team_points, current_week
        )
        
        if h2h_result == 'team1_wins':
            return [team1, team2]
        elif h2h_result == 'team2_wins':
            return [team2, team1]
        elif h2h_result == 'draw':
            # So sánh điểm tuần đối đầu
            if team1_h2h_points > team2_h2h_points:
                return [team1, team2]
            elif team2_h2h_points > team1_h2h_points:
                return [team2, team1]
            else:
                # Nếu vẫn bằng điểm đối đầu, so sánh total hits
                # Ai mua ít hơn (hits nhỏ hơn) xếp trên
                team1_total_hits = get_team_total_hits_from_csv(team1['team_name'], current_week)
                team2_total_hits = get_team_total_hits_from_csv(team2['team_name'], current_week)
                
                if team1_total_hits < team2_total_hits:
                    return [team1, team2]  # Team1 mua ít hơn -> xếp trên
                elif team2_total_hits < team1_total_hits:
                    return [team2, team1]  # Team2 mua ít hơn -> xếp trên
                else:
                    # Nếu hits cũng bằng nhau, fallback về goal difference
                    if team1['goal_difference'] >= team2['goal_difference']:
                        return [team1, team2]
                    else:
                        return [team2, team1]
    
    # Nếu có nhiều hơn 2 đội, sắp xếp theo hits rồi goal difference
    def sort_key(team):
        total_hits = get_team_total_hits_from_csv(team['team_name'], current_week)
        return (-total_hits, team['goal_difference'])  # Âm hits để sort tăng dần hits (ít hơn trước)
    
    return sorted(teams_with_same_points, key=sort_key, reverse=True)

def get_team_total_hits_from_csv(team_name, current_week):
    """
    Get total hits for a team from weeks.csv data up to current week.
    """
    try:
        import pandas as pd
        df = pd.read_csv('weeks.csv')
        
        if team_name not in df['team'].values:
            return 0
            
        team_row = df[df['team'] == team_name].iloc[0]
        total_hits = 0
        
        # Sum hits from week 1 to current_week - 1 (completed weeks)
        for week in range(1, current_week):
            week_col = str(week)
            if week_col in df.columns:
                value = team_row[week_col]
                if pd.notna(value) and ':' in str(value):
                    parts = str(value).split(':')
                    if len(parts) == 2 and parts[1].isdigit():
                        total_hits += int(parts[1])
        
        return total_hits
    except Exception as e:
        print(f"Error getting hits for {team_name}: {e}")
        return 0

def calculate_cup_standings(tournament_data, team_points, cup_weeks, current_week):
    """
    Calculate cup standings based on matches and points.
    Returns: list of team standings sorted by cup points
    """
    # Initialize team stats
    teams = set()
    for match in tournament_data:
        teams.add(match['team1'])
        teams.add(match['team2'])
    
    standings = {}
    for team in teams:
        standings[team] = {
            'team_name': team,
            'played': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'cup_points': 0,
            'goal_difference': 0
        }
    
    # Process matches
    for match in tournament_data:
        week = match['week']
        team1 = match['team1']
        team2 = match['team2']
        
        # Only process if week has been played (or is current week with deadline passed)
        if week < current_week or (week == current_week and get_current_week_info()[1]):
            team1_points = team_points.get(team1, {}).get(week, 0)
            team2_points = team_points.get(team2, {}).get(week, 0)
            
            result, diff = calculate_match_result(team1_points, team2_points)
            
            # Update team1 stats
            standings[team1]['played'] += 1
            standings[team1]['goal_difference'] += diff
            
            # Update team2 stats  
            standings[team2]['played'] += 1
            standings[team2]['goal_difference'] -= diff
            
            if result == 'win':
                standings[team1]['wins'] += 1
                standings[team1]['cup_points'] += 3
                standings[team2]['losses'] += 1
            elif result == 'draw':
                standings[team1]['draws'] += 1
                standings[team1]['cup_points'] += 1
                standings[team2]['draws'] += 1
                standings[team2]['cup_points'] += 1
            else:  # loss
                standings[team1]['losses'] += 1
                standings[team2]['wins'] += 1
                standings[team2]['cup_points'] += 3
    
    # Sắp xếp với tiebreaker rules
    all_teams = list(standings.values())
    
    # Nhóm các đội theo cup points
    points_groups = {}
    for team in all_teams:
        points = team['cup_points']
        if points not in points_groups:
            points_groups[points] = []
        points_groups[points].append(team)
    
    # Sắp xếp từng nhóm theo tiebreaker rules
    final_standings = []
    for points in sorted(points_groups.keys(), reverse=True):
        teams_in_group = points_groups[points]
        sorted_group = apply_tiebreaker_rules(teams_in_group, tournament_data, team_points, current_week)
        final_standings.extend(sorted_group)
    
    return final_standings

def prepare_cup_schedule(tournament_data, team_points, cup_weeks, current_week):
    """
    Prepare schedule with results for display.
    Only returns weeks that have been played or are currently being played.
    Returns: dict of {week: {matches: [], is_current: bool}}
    """
    schedule = {}
    
    # Only process weeks that are current or past
    weeks_to_show = [week for week in cup_weeks if week <= current_week]
    
    for week in weeks_to_show:
        week_matches = [m for m in tournament_data if m['week'] == week]
        
        matches_with_results = []
        for match in week_matches:
            team1 = match['team1']
            team2 = match['team2']
            
            # Check if match has been played
            if week < current_week or (week == current_week and get_current_week_info()[1]):
                team1_points = team_points.get(team1, {}).get(week, 0)
                team2_points = team_points.get(team2, {}).get(week, 0)
                
                result, diff = calculate_match_result(team1_points, team2_points)
                
                if result == 'win':
                    result_text = f"{team1_points}-{team2_points} (Thắng {team1})"
                elif result == 'draw':
                    result_text = f"{team1_points}-{team2_points} (Hòa)"
                else:
                    result_text = f"{team1_points}-{team2_points} (Thắng {team2})"
            else:
                result_text = "Chưa đấu"
            
            matches_with_results.append({
                'team1': team1,
                'team2': team2,
                'result': result_text
            })
        
        schedule[week] = {
            'matches': matches_with_results,
            'is_current': week == current_week
        }
    
    return schedule

# cronjob to keep the server running
@app.route('/cronjob', methods=['GET'])
def cronjob():
    return jsonify({"message": "Cronjob is running"})

####### main function #######
if __name__ == '__main__':
    app.run(debug = True, host='0.0.0.0', port=5000)
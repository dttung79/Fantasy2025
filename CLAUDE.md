# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Fantasy Premier League (FPL) mini-league tracking and cup tournament system. It displays live and historical team performance data for a private FPL league, runs cup tournaments across multiple weeks, and determines rankings based on custom scoring rules.

## Key Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask development server
python app.py
# Server runs on http://0.0.0.0:5001

# Run all cup logic tests
python test_cup_functions.py

# Run actual cup data tests
python test_actual_cup.py

# Debug cup standings
python debug_cup.py
python debug_cup_fast.py
```

### Data Generation
```bash
# Generate tournament schedules (creates tournament_1.csv through tournament_5.csv)
python gen_cup_schedule.py

# Extract live FPL data for a league (interactive - prompts for league ID)
python extract_live_new.py
```

### Accessing the Application
```bash
# Weekly view for league 1798895
http://localhost:5001/week/1798895

# Cup view for cup 1-5
http://localhost:5001/cup/1
http://localhost:5001/cup/2
# etc.

# API endpoints
http://localhost:5001/api/week/1798895
http://localhost:5001/api/cup/1
```

## Architecture

### Core Application (app.py)
Flask web server with two main display modes:
- **Weekly view** (`/week/<league_id>`): Shows team performance across gameweeks
- **Cup view** (`/cup/<cup_number>`): Shows tournament standings and match results

### Data Flow
1. **deadlines.txt**: Contains gameweek deadlines in format `week: YYYY-MM-DD, HH:MM, GMT+7`
   - Last line determines current week
   - Used to decide whether to show live or historical data

2. **weeks.csv**: Historical team performance data
   - Format: `team,1,2,3,...` (columns are gameweek numbers)
   - Cell format: `points:hits` (e.g., `68:0` = 68 points, 0 transfer hits)

3. **tournament_{n}.csv**: Cup tournament schedules
   - Format: `Week,Team1,Team2`
   - Each cup spans 7 consecutive gameweeks
   - Cup 1: weeks 1-7, Cup 2: weeks 8-14, etc.

4. **Live Data**: Fetched from livefpl.net when current week deadline has passed
   - `extract_live_new.py` scrapes league data using BeautifulSoup
   - Returns: rank, team_name, total_points, live_points, hits

### Cup Tournament System

**Scoring Rules** (from cup_rules.md):
- **Win**: 3 cup points (score ≥ 3 points more than opponent)
- **Draw**: 1 cup point (score difference < 3 points)
- **Loss**: 0 cup points

**Tiebreaker Rules** (in order):
1. Head-to-head result
2. If H2H is draw, compare points scored in that specific week
3. Total transfer hits (fewer hits ranks higher - `ai mua ít hơn xếp trên`)
4. Goal difference (sum of point differentials across all matches)

**Key Functions**:
- `calculate_match_result(team1_points, team2_points)`: Determines win/draw/loss
- `calculate_cup_standings()`: Computes standings with tiebreaker logic
- `apply_tiebreaker_rules()`: Handles teams with equal cup points
- `get_team_total_hits_from_csv()`: Extracts total transfer hits for tiebreaking

### API Endpoints

- **GET /api/week/<league_id>**: Returns weekly performance data
  - Merges historical (weeks.csv) + live data if deadline passed
  - Response: `{data: 2D array, current_week: int, deadline_passed: bool}`

- **GET /api/cup/<cup_number>**: Returns cup tournament data
  - Response: `{cup_info: {...}, standings: [...], schedule: {...}}`
  - Standings sorted by cup points, then tiebreakers
  - Schedule shows matches grouped by week (reverse chronological)

### Frontend
Templates use Jinja2:
- `header_tpl.html` / `footer_tpl.html`: Common layout
- `week_tpl.html`: Weekly leaderboard view
- `cup_tpl.html`: Cup tournament standings and schedule
- `fe_script.js`: Frontend JavaScript for API calls and UI updates

### Tournament Generation (gen_cup_schedule.py)
- Implements round-robin scheduling algorithm
- Generates 5 different tournament schedules with shuffled team orders
- Validates that each team plays every other team exactly once per tournament
- Creates `tournament_1.csv` through `tournament_5.csv`

## Important Implementation Details

### Time Handling
- All deadlines use Asia/Bangkok timezone (GMT+7)
- `get_current_week_info()` compares current Bangkok time vs deadline
- Supports both `zoneinfo.ZoneInfo` (Python 3.9+) and `pytz` fallback

### Data Merging Logic
When deadline has passed for current week:
1. Load historical data from weeks.csv
2. Fetch live data via `extract_league_data(league_id)`
3. Match teams by fuzzy name matching (case-insensitive substring match)
4. Update current week column with live `points:hits` format

### Cup Week Calculation
- Each cup contains exactly 7 consecutive gameweeks
- Formula: Cup N covers weeks `(N-1)*7+1` to `N*7`
- Example: Cup 2 = weeks 8-14

### Match Result Display
Results shown in format:
- Win: `"{team1_points}-{team2_points} (Thắng {winner})"`
- Draw: `"{team1_points}-{team2_points} (Hòa)"`
- Not played yet: `"Chưa đấu"`

## Testing

The project includes comprehensive unit tests in `test_cup_functions.py`:
- Match result calculation (win/draw/loss scenarios)
- Cup standings calculation
- Tiebreaker rules validation
- Edge cases (equal points, equal goal difference)

Run tests to validate cup logic after making changes to scoring or ranking algorithms.

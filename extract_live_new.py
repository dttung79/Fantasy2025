import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

# ==== regex helpers ====
re_hits_pattern = re.compile(r'(\d+)\s*\(-(\d+)\)\s*=\s*-?(\d+)')     # e.g. 0 (-12)=-12
re_all_ints = re.compile(r'-?\d+')

def parse_manager_row(manager_div):
    """
    Parse a single manager row from the new liveFPL structure.
    Based on the actual structure: Manager Name, Captain Info, GW Points, Total Points
    Returns: (team_name, live_points, total_points, hits)
    """
    try:
        # Find team name from the entry link
        team_name_elem = manager_div.find('a', href=lambda x: x and '/entry/' in x)
        if team_name_elem:
            team_name = team_name_elem.get_text(strip=True)
        else:
            # Fallback: extract from text
            row_text = manager_div.get_text(" ", strip=True)
            lines = [line.strip() for line in row_text.split('\n') if line.strip()]
            team_name = lines[0] if lines else "Unknown Team"
        
        # Get all text content for parsing
        row_text = manager_div.get_text(" ", strip=True)
        
        # Initialize defaults
        live_points = 0
        total_points = 0
        hits = 0
        
        # Debug: print row text to understand structure
        # print(f"DEBUG: Row text: {row_text}")
        
        # Look for hits pattern: "0 (-12)=-12" or "12 (-24)=-12"
        hits_match = re_hits_pattern.search(row_text)
        if hits_match:
            live_points = int(hits_match.group(1))  # GW points before hits
            hits = abs(int(hits_match.group(2)))    # Hit penalty (positive)
            
            # For hits case, total is at the end of the row (rightmost large number)
            all_numbers = [int(x) for x in re_all_ints.findall(row_text)]
            # Filter out small numbers that are likely not total points
            large_numbers = [n for n in all_numbers if n >= 10]
            if large_numbers:
                total_points = max(large_numbers)  # Largest number should be total
            else:
                total_points = all_numbers[-1] if all_numbers else 0
        else:
            # No hits - extract clean numbers
            all_numbers = [int(x) for x in re_all_ints.findall(row_text)]
            
            # For no hits case, structure is typically: pos, captain, gw_points, total_points
            # We need to identify which is live_points and which is total_points
            if all_numbers:
                # Filter candidates: total points should be reasonably large
                potential_totals = [n for n in all_numbers if n >= 30]  # Reasonable total points
                if potential_totals:
                    total_points = max(potential_totals)
                    # Find live points: should be smaller than total and reasonable for GW
                    potential_live = [n for n in all_numbers if n < total_points and n >= 0 and n <= 150]
                    if potential_live:
                        live_points = max(potential_live)  # Take largest reasonable live points
                    else:
                        live_points = 0
                else:
                    # If no large numbers, take the largest available as total
                    total_points = max(all_numbers)
                    # Try to find a reasonable live points value
                    remaining_numbers = [n for n in all_numbers if n != total_points and n >= 0 and n <= 150]
                    if remaining_numbers:
                        live_points = max(remaining_numbers)
                    else:
                        live_points = 0
        
        # Sanity checks
        if live_points < 0:
            live_points = 0
        if total_points < 0:
            total_points = abs(total_points)  # Convert negative totals to positive
            
        return team_name, live_points, total_points, hits
        
    except Exception as e:
        print(f"Error parsing manager row: {e}")
        return "Error Team", 0, 0, 0

def find_table_rows(soup):
    """
    Find all manager rows in the new liveFPL structure.
    """
    # Try multiple selectors to find manager rows
    rows = []
    
    # Method 1: Look for divs containing entry links
    entry_links = soup.find_all('a', href=lambda x: x and '/entry/' in x and 'fantasy.premierleague.com' in x)
    
    for link in entry_links:
        # Find the parent container that represents the full row
        row_container = link
        for _ in range(5):  # Go up max 5 levels
            if row_container.parent:
                row_container = row_container.parent
                # Check if this container has enough data (numbers)
                text = row_container.get_text(" ", strip=True)
                numbers = re_all_ints.findall(text)
                if len(numbers) >= 3:  # Should have at least rank, gw, total
                    break
        
        rows.append(row_container)
    
    return rows

def extract_league_data(league_code):
    """
    Trích xuất dữ liệu từ league FPL theo mã league với cấu trúc HTML mới.
    
    Args:
        league_code (str or int): Mã league (ví dụ: 1798895)
    
    Returns:
        pd.DataFrame: DataFrame chứa thông tin các đội trong league
        Columns: rank, team_name, total_points, live_points, hits
    """
    league_url = f"https://plan.livefpl.net/leagues/{league_code}"
    
    try:
        # ==== fetch & parse ====
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(league_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all manager rows
        manager_rows = find_table_rows(soup)
        
        if not manager_rows:
            print("No manager rows found. Trying alternative parsing...")
            # Fallback: try to find any div/tr that contains manager data
            all_elements = soup.find_all(['div', 'tr'])
            manager_rows = []
            for elem in all_elements:
                text = elem.get_text(" ", strip=True)
                if '/entry/' in str(elem) and len(re_all_ints.findall(text)) >= 2:
                    manager_rows.append(elem)
        
        rows = []
        for rank, manager_row in enumerate(manager_rows, start=1):
            team_name, live_points, total_points, hits = parse_manager_row(manager_row)
            
            rows.append({
                "rank": rank,
                "team_name": team_name,
                "total_points": total_points,
                "live_points": live_points,
                "hits": hits
            })
        
        if not rows:
            print("Warning: No data extracted from the league page")
            return pd.DataFrame(columns=["rank", "team_name", "total_points", "live_points", "hits"])
        
        df = pd.DataFrame(rows)
        print(f"Successfully extracted {len(df)} teams from league {league_code}")
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return pd.DataFrame(columns=["rank", "team_name", "total_points", "live_points", "hits"])
    except Exception as e:
        print(f"Error extracting league data: {e}")
        return pd.DataFrame(columns=["rank", "team_name", "total_points", "live_points", "hits"])

# Example usage:
if __name__ == "__main__":
    df = extract_league_data("1798895")
    print(df)
    # df.to_csv("league_1798895_live.csv", index=False)
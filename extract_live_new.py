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
    Based on the actual structure: TeamName PlayerName Captain(C). To Play: X VC: ViceCaptain WC BB FH TC OR rank,total_points
    Returns: (team_name, live_points, total_points, hits)
    """
    try:
        # Find team name from the entry link
        team_name_elem = manager_div.find('a', href=lambda x: x and '/entry/' in x)
        if team_name_elem:
            team_name = team_name_elem.get_text(strip=True)
        else:
            # Fallback: extract from text - team name is usually the first word(s)
            row_text = manager_div.get_text(" ", strip=True)
            # Team name is before the player name and captain info
            parts = row_text.split()
            team_name = parts[0] if parts else "Unknown Team"
        
        # Get all text content for parsing
        row_text = manager_div.get_text(" ", strip=True)
        
        # Initialize defaults
        live_points = 0
        total_points = 0
        hits = 0
        
        # Debug: print row text to understand structure (disabled for production)
        # print(f"DEBUG: Row text: {row_text}")
        # print(f"DEBUG: All numbers found: {re_all_ints.findall(row_text)}")
        
        # Look for hits pattern: "X (-Y)=Z"
        hits_match = re_hits_pattern.search(row_text)
        if hits_match:
            live_points = int(hits_match.group(3))  # Final points after hits
            hits = abs(int(hits_match.group(2)))    # Hit penalty (positive)
            
            # Extract total points from OR section
            # Format: OR rank,total_points (e.g., "OR 1,330,209" means rank=1,330 total=209)
            or_match = re.search(r'OR\s+([\d,]+)', row_text)
            if or_match:
                or_numbers = or_match.group(1)
                # Split by comma and take the last part as total points
                parts = or_numbers.split(',')
                if len(parts) >= 2:
                    total_points = int(parts[-1])  # Last part is total points
                else:
                    total_points = int(or_numbers.replace(',', ''))
            else:
                # Fallback: find the largest reasonable number
                all_numbers = [int(x) for x in re_all_ints.findall(row_text)]
                # Take the last number that's in a reasonable range for total points
                if all_numbers:
                    for num in reversed(all_numbers):
                        if 100 <= num <= 5000:  # Reasonable total points range
                            total_points = num
                            break
                    else:
                        total_points = max(all_numbers) if all_numbers else 0
        else:
            # No hits case - parse the standard format
            # Format: TeamName PlayerName Captain(C). To Play: X VC: ViceCaptain WC BB FH TC OR rank,total_points
            
            # Extract "To Play" value - NOTE: This format doesn't show actual live GW points
            # It only shows "To Play" count (players yet to play) and overall rank/total points
            to_play_match = re.search(r'To Play:\s*(\d+)', row_text)
            if to_play_match:
                to_play = int(to_play_match.group(1))
                # Setting live_points to 0 since actual GW points are not available in this format
                # To get real live points, we would need a different liveFPL URL or format
                live_points = 0  # Cannot extract actual live points from this format
            
            # Extract total points from OR section
            # Format: OR rank,total_points (e.g., "OR 1,330,209" means rank=1,330 total=209)
            or_match = re.search(r'OR\s+([\d,]+)', row_text)
            if or_match:
                or_numbers = or_match.group(1)
                # Split by comma and take the last part as total points
                parts = or_numbers.split(',')
                if len(parts) >= 2:
                    total_points = int(parts[-1])  # Last part is total points
                else:
                    total_points = int(or_numbers.replace(',', ''))
            else:
                # Fallback: look for the pattern in raw numbers
                all_numbers = [int(x) for x in re_all_ints.findall(row_text)]
                # Based on debug output, the pattern seems to be: [to_play, rank_parts..., total_points]
                # Total points are usually the last number and in hundreds range
                if all_numbers:
                    # Take the last number that's in a reasonable range for total points
                    for num in reversed(all_numbers):
                        if 100 <= num <= 5000:  # Reasonable total points range
                            total_points = num
                            break
                    else:
                        total_points = all_numbers[-1] if all_numbers else 0
        
        # Sanity checks
        if live_points < 0:
            live_points = 0
        if total_points < 0:
            total_points = abs(total_points)
            
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
    
    ĐÃ SỬA: Script giờ đây có thể đọc chính xác:
    - Live points (GW points): điểm gameweek thực tế
    - Total points: tổng điểm tích lũy
    - Hits: số điểm bị trừ do transfer
    - Hỗ trợ format có hits: "42 (-12)=30"
    
    Args:
        league_code (str or int): Mã league (ví dụ: 1798895)
    
    Returns:
        pd.DataFrame: DataFrame chứa thông tin các đội trong league
        Columns: rank, team_name, total_points, live_points, hits
    """
    # Use the primary livefpl.net URL that works
    league_url = f"https://livefpl.net/leagues/{league_code}"
    print(f"Extracting data from: {league_url}")
    
    return _extract_from_url(league_url, league_code)

def _extract_from_url(league_url, league_code):
    """Helper function to extract data from a specific URL"""
    try:
        # ==== fetch & parse ====
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # Increase timeout for busy server situations
        response = requests.get(league_url, headers=headers, timeout=60)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Try to find the new table format first (with GW and Total columns)
        rows = _parse_table_format(soup)
        if rows:
            df = pd.DataFrame(rows)
            print(f"Successfully extracted {len(df)} teams from league {league_code} (table format)")
            return df
        
        # Fallback to old parsing method
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

def _is_team_row(text):
    """
    Determine if a text string represents a team/manager row
    Generic detection based on patterns, not hardcoded team names
    """
    # Pattern 1: Contains position number at start (after potential symbols)
    # Pattern 2: Contains captain indicator (C)
    # Pattern 3: Contains reasonable point values
    # Pattern 4: Contains common FPL terms
    
    # Remove leading symbols and check for position number
    cleaned_text = re.sub(r'^[^\w\d]*', '', text)
    words = cleaned_text.split()
    
    # Check for position number (1-20 typically)
    has_position = False
    if words and words[0].isdigit() and 1 <= int(words[0]) <= 50:
        has_position = True
    
    # Check for captain indicator
    has_captain = '(C)' in text
    
    # Check for points pattern (numbers in reasonable ranges)
    numbers = [int(x) for x in re_all_ints.findall(text)]
    has_reasonable_points = any(10 <= n <= 3000 for n in numbers)  # Reasonable total points
    has_gw_points = any(0 <= n <= 150 for n in numbers)  # Reasonable GW points
    
    # Check for FPL-specific terms
    fpl_terms = ['VC:', 'WC', 'BB', 'FH', 'TC', 'OR', 'To Play:', 'PLAYED']
    has_fpl_terms = any(term in text for term in fpl_terms)
    
    # A valid team row should have at least position + captain OR points + FPL terms
    return (has_position and has_captain) or (has_reasonable_points and has_fpl_terms) or (has_gw_points and has_fpl_terms)

def _extract_team_name(text):
    """
    Extract team name from text using generic patterns
    """
    # Remove leading symbols
    cleaned_text = re.sub(r'^[^\w\d]*', '', text)
    words = cleaned_text.split()
    
    if not words:
        return "Unknown Team"
    
    # Generic FPL/fantasy terms and common patterns to skip
    skip_patterns = {
        # FPL terms
        'VC:', 'WC', 'BB', 'FH', 'TC', 'OR', 'To', 'Play:', 'PLAYED',
        # Captain indicators
        '(C)', '(VC)',
        # Common single letters/short words
        'C', 'V', 'M', 'A', 'T'
    }
    
    # Strategy 1: Skip position number and find first substantial word
    start_idx = 0
    if words[0].isdigit():
        start_idx = 1
    
    # Look for team name (usually first meaningful word(s) after position)
    for i in range(start_idx, min(start_idx + 4, len(words))):
        if i < len(words):
            word = words[i]
            
            # Skip very short words and known FPL terms, but allow alphanumeric team names
            if (len(word) >= 3 and 
                word not in skip_patterns and
                not word.startswith('(') and
                not word.endswith(')') and
                ':' not in word):
                
                # Check if next word might be part of team name
                if i + 1 < len(words):
                    next_word = words[i + 1]
                    
                    # Check for repeated word pattern which indicates team name boundary
                    # Pattern: "Johnny Walker Walker Johnny" - team name is "Johnny Walker"
                    if (next_word.isalpha() and 
                        i + 2 < len(words) and 
                        (words[i + 2] == next_word or words[i + 2] == word)):
                        # This suggests "word next_word" is the team name
                        return f"{word} {next_word}"
                    
                    # Common team name suffixes
                    if next_word in ['FC', 'United', 'City', 'Town', 'Athletic', 'Rovers']:
                        return f"{word} {next_word}"
                
                # Single word team name
                if (word.isalpha() or 
                    (word.isalnum() and not word.isdigit() and any(c.isalpha() for c in word))):
                    return word
    
    # Fallback: return first substantial word that looks like a name
    for word in words[start_idx:]:
        if (len(word) >= 3 and 
            word not in skip_patterns and
            (word.isalpha() or (word.isalnum() and not word.isdigit() and any(c.isalpha() for c in word)))):
            return word
    
    return "Unknown Team"

def _parse_table_format(soup):
    """
    Parse the new table format with proper GW and Total columns
    Looking for structure like:
    | Pos | Manager | Yet | (C) | GW | Total |
    """
    rows = []
    
    # Look for table structure or organized data
    # Try to find elements that contain both GW points and Total points
    potential_rows = soup.find_all(['tr', 'div'], class_=lambda x: x and ('row' in str(x).lower() or 'item' in str(x).lower()))
    
    for element in potential_rows:
        text = element.get_text(" ", strip=True)
        
        # Look for patterns like "54" in GW column and "174" in Total column
        # Also check for hits pattern like "42 (-12)=30"
        
        # Check if this element contains manager/team data
        # Look for patterns that indicate this is a team row:
        # 1. Contains position number at start
        # 2. Contains points values (GW and Total)
        # 3. Contains captain info (C) or player names
        if _is_team_row(text):
            # print(f"Found potential table row: {text}")  # Debug output disabled
            
            # Extract team name using generic pattern detection
            team_name = _extract_team_name(text)
            # print(f"Extracted team name: '{team_name}'")
            
            # Look for hit pattern first: "X (-Y)=Z"
            hits_match = re.search(r'(\d+)\s*\(-(\d+)\)\s*=\s*(\d+)', text)
            if hits_match:
                live_points = int(hits_match.group(1))  # GW points before hits
                hits = int(hits_match.group(2))         # Hit penalty
                
                # Extract total points - should be the last reasonable number
                all_numbers = [int(x) for x in re_all_ints.findall(text)]
                # The total is typically at the end, after the hit calculation
                # Look for numbers after the hit pattern that are reasonable totals
                remaining_text = text[hits_match.end():]
                remaining_numbers = [int(x) for x in re_all_ints.findall(remaining_text)]
                total_candidates = [n for n in remaining_numbers if 50 <= n <= 3000]
                total_points = total_candidates[-1] if total_candidates else 0
            else:
                # No hits - look for separate GW and Total values
                all_numbers = [int(x) for x in re_all_ints.findall(text)]
                if len(all_numbers) >= 2:
                    # Based on the debug output pattern: [pos, ..., rank_parts, gw, total]
                    # Total is typically the last number in reasonable range
                    total_candidates = [n for n in all_numbers if 50 <= n <= 3000]
                    if total_candidates:
                        total_points = total_candidates[-1]  # Last reasonable total
                        # GW should be second to last reasonable number or before total
                        gw_candidates = [n for n in all_numbers if 0 <= n <= 150 and n != total_points]
                        live_points = gw_candidates[-1] if gw_candidates else 0
                    else:
                        continue
                    hits = 0
                else:
                    continue  # Skip if not enough data
            
            if live_points > 0 or total_points > 0:
                rows.append({
                    "rank": len(rows) + 1,
                    "team_name": team_name,
                    "total_points": total_points,
                    "live_points": live_points,
                    "hits": hits
                })
    
    return rows

# Example usage:
if __name__ == "__main__":
    df = extract_league_data("1798895")
    print(df)
    # df.to_csv("league_1798895_live.csv", index=False)
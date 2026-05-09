# Final Cup - Plan Cài Đặt Chi Tiết

## 1. Tổng Quan

Final Cup là giải đấu knockout 3 vòng cuối mùa giải (tuần 36-38), bao gồm:
- **Tứ kết** (Vòng 36): 4 cặp đấu từ `quarter.csv`
- **Bán kết** (Vòng 37): Thắng cặp 1-2 gặp thắng cặp 3-4
- **Chung kết** (Vòng 38): 2 đội thắng bán kết

Trang `/final_cup` sẽ hiển thị sơ đồ giải đấu bracket và cập nhật theo tiến độ thực tế.

---

## 2. Cặp Đấu Tứ Kết (từ quarter.csv)

| Cặp | Team 1 | Team 2 |
|-----|--------|--------|
| Cặp 1 | Morningstar FC | dautamhanhxxxlll |
| Cặp 2 | Namdzai | PhiHungDentist |
| Cặp 3 | Galaticos FC | Johnny Walker |
| Cặp 4 | savapain | nani29 |

**Bán kết:**
- BK1: Thắng Cặp 1 vs Thắng Cặp 2
- BK2: Thắng Cặp 3 vs Thắng Cặp 4

**Chung kết:**
- CK: Thắng BK1 vs Thắng BK2

---

## 3. Luật Thắng/Thua Final Cup

> Khác với 5 cup thường (phải hơn 3đ mới thắng), Final Cup chỉ cần hơn 1đ.

**Thứ tự ưu tiên khi xác định người thắng:**

1. **Hơn điểm**: Nếu team1_points > team2_points (dù chỉ 1đ) → team1 thắng
2. **Bằng điểm → So hits**: Ai bị hits **nhiều hơn** thì **thua** (ai mua ít hơn = thắng)
3. **Bằng điểm + bằng hits → So total FPL**: Ai có tổng điểm fantasy **cao hơn** thì **thắng**
4. **Bằng tất cả → Alphabet**: Tên đội xếp trước theo alphabet thì thắng

```python
def calculate_final_cup_match_result(
    team1_name, team2_name,
    team1_pts, team2_pts,       # Điểm vòng đó
    team1_hits, team2_hits,     # Hits vòng đó
    team1_total, team2_total    # Tổng FPL points tích lũy
):
    if team1_pts > team2_pts:
        return "win_team1", team1_name
    elif team2_pts > team1_pts:
        return "win_team2", team2_name
    # Bằng điểm → so hits
    elif team1_hits < team2_hits:  # Ít hits hơn = thắng
        return "win_team1", team1_name
    elif team2_hits < team1_hits:
        return "win_team2", team2_name
    # Bằng hits → so total
    elif team1_total > team2_total:
        return "win_team1", team1_name
    elif team2_total > team1_total:
        return "win_team2", team2_name
    # Bằng tất cả → alphabet
    elif team1_name.lower() <= team2_name.lower():
        return "win_team1", team1_name
    else:
        return "win_team2", team2_name
```

---

## 4. State Machine - 7 Trạng Thái Hiển Thị

Trạng thái được xác định dựa trên `current_week` (từ deadlines.txt) và `deadline_passed`.

| State | Điều Kiện | Hiển Thị |
|-------|-----------|----------|
| `PRE_QF` | current_week < 36 HOẶC (current_week == 36 AND NOT deadline_passed) | Lịch đấu tứ kết |
| `LIVE_QF` | current_week == 36 AND deadline_passed | Kết quả **live** tứ kết + Lịch bán kết dự kiến |
| `OFFICIAL_QF` | current_week == 37 AND NOT deadline_passed | Kết quả **chính thức** tứ kết + Lịch bán kết chính thức |
| `LIVE_SF` | current_week == 37 AND deadline_passed | Kết quả chính thức tứ kết + Kết quả **live** bán kết + Lịch CK dự kiến |
| `OFFICIAL_SF` | current_week == 38 AND NOT deadline_passed | Kết quả chính thức tứ kết + bán kết + Lịch CK chính thức |
| `LIVE_FINAL` | current_week == 38 AND deadline_passed | Tất cả kết quả chính thức + Kết quả **live** chung kết |
| `POST_FINAL` | current_week > 38 | Toàn bộ kết quả chính thức (weeks.csv) |

```python
def get_final_cup_state(current_week, deadline_passed):
    if current_week < 36 or (current_week == 36 and not deadline_passed):
        return "PRE_QF"
    elif current_week == 36 and deadline_passed:
        return "LIVE_QF"
    elif current_week == 37 and not deadline_passed:
        return "OFFICIAL_QF"
    elif current_week == 37 and deadline_passed:
        return "LIVE_SF"
    elif current_week == 38 and not deadline_passed:
        return "OFFICIAL_SF"
    elif current_week == 38 and deadline_passed:
        return "LIVE_FINAL"
    else:  # current_week > 38
        return "POST_FINAL"
```

---

## 5. Nguồn Dữ Liệu

### 5.1 Dữ Liệu Tĩnh
- **Lịch tứ kết**: `quarter.csv` — đọc 1 lần, không thay đổi
- **Điểm chính thức**: `weeks.csv` — cột `36`, `37`, `38` (định dạng `points:hits`)

### 5.2 Dữ Liệu Live
- Gọi `extract_league_data(1798895)` — trả về DataFrame với các cột:
  - `team_name`: tên đội
  - `live_points`: điểm vòng hiện tại
  - `hits`: số hit vòng hiện tại
  - `total_points`: tổng điểm FPL tích lũy

### 5.3 Lấy Điểm Cho Một Vòng Cụ Thể

```python
def get_final_cup_week_data(week, is_live=False, live_data_map=None):
    """
    Trả về: dict {team_name: {'points': int, 'hits': int, 'total': int}}
    - is_live=False: đọc từ weeks.csv (cột str(week))
    - is_live=True: dùng live_data_map từ extract_league_data()
    """
    result = {}
    df = pd.read_csv('weeks.csv')
    week_col = str(week)

    for _, row in df.iterrows():
        team = row['team']
        # Luôn lấy total_points từ weeks.csv (tổng đến tuần trước)
        total = sum_points_from_csv(row, up_to_week=week - 1)

        if is_live and live_data_map and team in live_data_map:
            pts = live_data_map[team]['live_points']
            hits = live_data_map[team]['hits']
            total = live_data_map[team]['total_points']  # live total
        elif week_col in df.columns:
            value = row[week_col]
            pts, hits = parse_points_hits(value)  # "68:0" → (68, 0)
            # total = accumulated from all previous weeks in weeks.csv
        else:
            pts, hits = 0, 0

        result[team] = {'points': pts, 'hits': hits, 'total': total}

    return result
```

### 5.4 Fuzzy Matching Team Names
Khi merge live data với dữ liệu weeks.csv, dùng logic đã có:
```python
for team in teams_csv:
    for live_team in live_data:
        if team.lower() in live_team.lower() or live_team.lower() in team.lower():
            # match
```

---

## 6. Về deadlines.txt

`deadlines.txt` sẽ được cập nhật **dần dần** theo lịch FPL. Nếu tuần chưa có trong file nghĩa là chưa qua deadline của tuần đó.

**Cơ chế hoạt động** (dựa trên `get_current_week_info()` đọc dòng cuối file):

| Dòng cuối file | deadline_passed | State |
|---------------|----------------|-------|
| `36: ...` | false | `PRE_QF` |
| `36: ...` | true | `LIVE_QF` |
| `37: ...` | false | `OFFICIAL_QF` |
| `37: ...` | true | `LIVE_SF` |
| `38: ...` | false | `OFFICIAL_SF` |
| `38: ...` | true | `LIVE_FINAL` |
| `39: ...` | bất kỳ | `POST_FINAL` |

→ **Không cần thêm deadline trước.** Chỉ cần thêm khi biết chính xác lịch FPL.

---

## 7. Thay Đổi Backend (app.py)

### 7.1 Hàm Mới Cần Thêm

```python
# ---- FINAL CUP FUNCTIONS ----

def get_final_cup_state(current_week, deadline_passed) -> str:
    """Trả về state string: PRE_QF, LIVE_QF, OFFICIAL_QF, LIVE_SF, OFFICIAL_SF, LIVE_FINAL, POST_FINAL"""

def read_quarter_final_bracket() -> list[dict]:
    """Đọc quarter.csv, trả về 4 cặp đấu: [{pair:1, team1:..., team2:...}, ...]"""

def calculate_final_cup_match_result(
    team1_name, team2_name, team1_pts, team2_pts,
    team1_hits, team2_hits, team1_total, team2_total
) -> tuple[str, str]:
    """
    Trả về: (result_code, winner_name)
    result_code: "win_team1" | "win_team2"
    """

def get_week_data_from_csv(week: int) -> dict:
    """
    Đọc cột tuần từ weeks.csv.
    Trả về: {team_name: {'points': int, 'hits': int}}
    """

def get_accumulated_total_from_csv(team_name: str, up_to_week: int) -> int:
    """
    Tính tổng điểm FPL tích lũy từ tuần 1 đến up_to_week (inclusive).
    Dùng cho tiebreaker total points.
    """

def build_final_cup_response(current_week: int, deadline_passed: bool) -> dict:
    """
    Hàm chính build response cho /api/final_cup.
    Xác định state → thu thập dữ liệu → tính kết quả → trả về JSON.
    """
```

### 7.2 Route và API Endpoint Mới

```python
@app.route('/final_cup')
def final_cup():
    return build_final_cup_page('final_cup_tpl.html')

def build_final_cup_page(filename):
    head = render_template('header_tpl.html', league_id=1798895, current_page='final_cup')
    content = render_template(filename)
    footer = render_template('footer_tpl.html')
    return head + '\n' + content + '\n' + footer

@app.route('/api/final_cup')
def get_final_cup_data():
    try:
        current_week, deadline_passed = get_current_week_info()
        response = build_final_cup_response(current_week, deadline_passed)
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### 7.3 Cấu Trúc JSON Response

```json
{
  "state": "LIVE_QF",
  "current_week": 36,
  "deadline_passed": true,
  "last_updated": "2026-05-09T18:30:00+07:00",

  "quarter_finals": [
    {
      "pair": 1,
      "week": 36,
      "team1": "Morningstar FC",
      "team2": "dautamhanhxxxlll",
      "team1_points": 68,
      "team2_points": 65,
      "team1_hits": 0,
      "team2_hits": 0,
      "team1_total": 1523,
      "team2_total": 1487,
      "result": "win_team1",
      "winner": "Morningstar FC",
      "is_live": true,
      "tiebreaker_used": null
    }
  ],

  "semi_finals": [
    {
      "match": 1,
      "week": 37,
      "team1": "Morningstar FC",
      "team2": "Namdzai",
      "team1_from": "winner_qf_pair_1",
      "team2_from": "winner_qf_pair_2",
      "team1_points": null,
      "team2_points": null,
      "team1_hits": null,
      "team2_hits": null,
      "team1_total": null,
      "team2_total": null,
      "result": "pending",
      "winner": null,
      "is_live": false,
      "tiebreaker_used": null
    }
  ],

  "final": {
    "match": 1,
    "week": 38,
    "team1": null,
    "team2": null,
    "team1_from": "winner_sf_1",
    "team2_from": "winner_sf_2",
    "team1_points": null,
    "team2_points": null,
    "result": "pending",
    "winner": null,
    "is_live": false,
    "tiebreaker_used": null
  }
}
```

**Giá trị `tiebreaker_used`:** `null` | `"hits"` | `"total_points"` | `"alphabet"`

---

## 8. Logic Build Response Theo State

### PRE_QF
- `quarter_finals`: 4 cặp, tất cả `result = "pending"`, `winner = null`
- `semi_finals`: 2 cặp, `team1 = null`, `team2 = null`, `result = "pending"`
- `final`: `team1 = null`, `team2 = null`, `result = "pending"`

### LIVE_QF
- Gọi `extract_league_data(1798895)` → live_data_map
- `quarter_finals`: Tính kết quả live dùng `calculate_final_cup_match_result()`
- `semi_finals`: Dùng live winner từ QF nếu đã xác định, còn lại là `"TBD"`, `result = "pending"`
- `final`: `team1 = null`, `team2 = null`

### OFFICIAL_QF
- `quarter_finals`: Đọc từ `weeks.csv` cột `36`, tính kết quả chính thức
- `semi_finals`: Dùng official winner từ QF, `result = "pending"`
- `final`: Chưa biết

### LIVE_SF
- `quarter_finals`: Kết quả chính thức (weeks.csv cột 36)
- `semi_finals`: Gọi live data, tính kết quả live vòng 37
- `final`: Dùng live winner từ SF nếu đã xác định, còn lại `"TBD"`

### OFFICIAL_SF
- `quarter_finals`: Chính thức từ weeks.csv cột 36
- `semi_finals`: Chính thức từ weeks.csv cột 37
- `final`: Dùng official winner từ SF, `result = "pending"`

### LIVE_FINAL
- `quarter_finals`: Chính thức từ weeks.csv cột 36
- `semi_finals`: Chính thức từ weeks.csv cột 37
- `final`: Gọi live data, tính kết quả live vòng 38

### POST_FINAL
- Tất cả kết quả chính thức từ weeks.csv (cột 36, 37, 38)

---

## 9. Template Frontend (templates/final_cup_tpl.html)

### 9.1 Cấu Trúc HTML

```html
{% include 'header_tpl.html' %}

<div class="final-cup-container">
  <!-- State Badge -->
  <div class="tournament-header">
    <h1 class="tournament-title">🏆 Final Cup 2025-2026</h1>
    <div class="tournament-subtitle">Vòng 36-38</div>
    <div id="state-badge" class="state-badge"></div>
    <button id="refresh-button" class="refresh-btn" onclick="refreshFinalCupData()">
      <span class="refresh-icon">🔄</span> Làm mới
    </button>
  </div>

  <!-- Loading skeleton -->
  <div id="loading" class="loading-state">...</div>

  <!-- Error message -->
  <div id="error-message" class="error-message" style="display: none;"></div>

  <!-- Main bracket -->
  <div id="final-cup-content" style="display: none;">

    <!-- QF Section -->
    <section class="round-section qf-section">
      <div class="round-header">
        <h2 class="round-title">Tứ Kết</h2>
        <span class="round-week-badge">Vòng 36</span>
        <span id="qf-status-badge" class="status-badge"></span>
      </div>
      <div class="matches-grid qf-matches" id="qf-matches"></div>
    </section>

    <!-- Arrow connector (desktop only) -->
    <div class="bracket-connector" aria-hidden="true">→</div>

    <!-- SF Section -->
    <section class="round-section sf-section">
      <div class="round-header">
        <h2 class="round-title">Bán Kết</h2>
        <span class="round-week-badge">Vòng 37</span>
        <span id="sf-status-badge" class="status-badge"></span>
      </div>
      <div class="matches-grid sf-matches" id="sf-matches"></div>
    </section>

    <!-- Arrow connector -->
    <div class="bracket-connector" aria-hidden="true">→</div>

    <!-- Final Section -->
    <section class="round-section final-section">
      <div class="round-header">
        <h2 class="round-title">⚽ Chung Kết</h2>
        <span class="round-week-badge">Vòng 38</span>
        <span id="final-status-badge" class="status-badge"></span>
      </div>
      <div class="matches-grid final-match" id="final-match"></div>
    </section>

    <!-- Champion Banner (chỉ hiện khi có kết quả CK) -->
    <div id="champion-banner" class="champion-banner" style="display: none;">
      <div class="champion-trophy">🏆</div>
      <div class="champion-label">Vô Địch Final Cup</div>
      <div class="champion-name" id="champion-name"></div>
    </div>

  </div>
</div>

<script>
  // Tất cả JS logic ở đây (xem mục 9.2)
</script>
```

### 9.2 JavaScript Logic

```javascript
async function loadFinalCupData() {
  const response = await fetch('/api/final_cup');
  const data = await response.json();

  // Hiện nội dung, ẩn loading
  renderStateBadge(data.state);
  renderQF(data.quarter_finals, data.state);
  renderSF(data.semi_finals, data.state);
  renderFinal(data.final, data.state);
  renderChampionBanner(data.final);
}

function renderMatchCard(match, isLive) {
  const isPending = match.result === 'pending';
  const team1Wins = match.result === 'win_team1';
  const team2Wins = match.result === 'win_team2';

  return `
    <div class="match-card ${isLive ? 'match-live' : ''} ${isPending ? 'match-pending' : ''}">
      <div class="match-team ${team1Wins ? 'team-win' : team2Wins ? 'team-loss' : ''}">
        <span class="team-name">${match.team1 || 'TBD'}</span>
        ${!isPending ? `<span class="team-score">${match.team1_points}</span>` : ''}
      </div>
      <div class="match-divider">
        ${isPending ? 'vs' : `${match.team1_points} - ${match.team2_points}`}
        ${isLive ? '<span class="live-indicator">LIVE</span>' : ''}
      </div>
      <div class="match-team ${team2Wins ? 'team-win' : team1Wins ? 'team-loss' : ''}">
        <span class="team-name">${match.team2 || 'TBD'}</span>
        ${!isPending ? `<span class="team-score">${match.team2_points}</span>` : ''}
      </div>
      ${match.tiebreaker_used ? renderTiebreakerInfo(match) : ''}
      ${!isPending ? `<div class="match-result-badge ${team1Wins ? 'result-win-left' : 'result-win-right'}">
        Thắng: ${match.winner}
      </div>` : ''}
    </div>
  `;
}

function renderTiebreakerInfo(match) {
  const labels = {
    'hits': `Phân định qua Hits (${match.team1_hits} vs ${match.team2_hits})`,
    'total_points': `Phân định qua Điểm Tổng (${match.team1_total} vs ${match.team2_total})`,
    'alphabet': 'Phân định theo Alphabet'
  };
  return `<div class="tiebreaker-info">⚖️ ${labels[match.tiebreaker_used]}</div>`;
}

function renderStateBadge(state) {
  const badges = {
    'PRE_QF': { text: 'Chưa bắt đầu', cls: 'badge-pending' },
    'LIVE_QF': { text: '🔴 Tứ Kết - LIVE', cls: 'badge-live' },
    'OFFICIAL_QF': { text: '✅ Tứ Kết hoàn thành', cls: 'badge-done' },
    'LIVE_SF': { text: '🔴 Bán Kết - LIVE', cls: 'badge-live' },
    'OFFICIAL_SF': { text: '✅ Bán Kết hoàn thành', cls: 'badge-done' },
    'LIVE_FINAL': { text: '🔴 Chung Kết - LIVE', cls: 'badge-live' },
    'POST_FINAL': { text: '🏆 Giải đấu kết thúc', cls: 'badge-champion' },
  };
  // render badge
}
```

---

## 10. CSS Additions (styles.css)

```css
/* ===== FINAL CUP ===== */

.final-cup-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.tournament-header {
  text-align: center;
  margin-bottom: 32px;
}

.tournament-title {
  font-size: 2.2rem;
  color: var(--gold);
  text-shadow: 0 2px 8px rgba(0,0,0,0.4);
}

/* Bracket layout: 3 columns on desktop, stacked on mobile */
.bracket-layout {
  display: flex;
  flex-direction: column;
  gap: 40px;
}

@media (min-width: 900px) {
  .bracket-layout {
    flex-direction: row;
    align-items: flex-start;
    gap: 20px;
  }
  .round-section {
    flex: 1;
  }
}

/* Round section */
.round-section {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 20px;
}

.round-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.round-title {
  font-size: 1.3rem;
  color: var(--cream);
  margin: 0;
}

.round-week-badge {
  background: var(--navy-blue);
  color: var(--cream);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
}

/* Match cards */
.match-card {
  background: var(--navy-dark);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 12px;
}

.match-card.match-live {
  border-color: var(--danger);
  box-shadow: 0 0 10px rgba(239, 83, 80, 0.3);
}

.match-card.match-pending {
  border-color: var(--neutral);
  opacity: 0.8;
}

.match-team {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
}

.match-team.team-win .team-name {
  font-weight: 700;
  color: var(--success);
}

.match-team.team-loss .team-name {
  color: var(--neutral);
  text-decoration: line-through;
}

.team-score {
  font-weight: 700;
  font-size: 1.2rem;
  color: var(--gold);
}

.match-divider {
  text-align: center;
  color: var(--sand);
  font-size: 0.85rem;
  padding: 4px 0;
  border-top: 1px solid rgba(255,255,255,0.1);
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.live-indicator {
  display: inline-block;
  background: var(--danger);
  color: white;
  font-size: 0.7rem;
  padding: 1px 5px;
  border-radius: 3px;
  animation: blink 1s step-start infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.match-result-badge {
  text-align: center;
  margin-top: 8px;
  font-size: 0.85rem;
  color: var(--gold);
  font-style: italic;
}

.tiebreaker-info {
  text-align: center;
  font-size: 0.75rem;
  color: var(--amber);
  margin: 4px 0;
}

/* State badges */
.state-badge { padding: 4px 12px; border-radius: 20px; font-size: 0.9rem; }
.badge-pending { background: var(--neutral); color: var(--navy-dark); }
.badge-live { background: var(--danger); color: white; }
.badge-done { background: var(--success); color: white; }
.badge-champion { background: var(--gold); color: var(--navy-dark); font-weight: 700; }

/* Status badges for each round */
.status-badge { font-size: 0.75rem; padding: 2px 8px; border-radius: 3px; }

/* Champion banner */
.champion-banner {
  text-align: center;
  margin-top: 40px;
  padding: 40px 20px;
  background: linear-gradient(135deg, var(--gold-dark), var(--gold), var(--gold-dark));
  border-radius: 16px;
  color: var(--navy-dark);
}

.champion-trophy { font-size: 4rem; margin-bottom: 12px; }
.champion-label { font-size: 1.2rem; font-weight: 600; }
.champion-name { font-size: 2.5rem; font-weight: 700; margin-top: 8px; }

/* Bracket connector (desktop) */
.bracket-connector {
  display: none;
  font-size: 2rem;
  color: var(--gold);
  align-self: center;
  padding: 10px;
}

@media (min-width: 900px) {
  .bracket-connector { display: flex; }
}
```

---

## 11. Cập Nhật Navigation (header_tpl.html)

Thêm link **Final Cup** vào nav bar, sau section Cúp:

```html
<div class="nav-section">
    <a href="/final_cup" class="nav-link final-cup-link {% if current_page == 'final_cup' %}active{% endif %}">
        🏆 Final Cup <span class="week-range-small">(36-38)</span>
    </a>
</div>
```

Thêm CSS cho nav link mới:
```css
.final-cup-link {
  background: linear-gradient(135deg, var(--gold-dark), var(--gold));
  color: var(--navy-dark) !important;
  font-weight: 700;
}
.final-cup-link:hover {
  background: var(--gold-light);
}
```

---

## 12. Danh Sách Files Cần Thay Đổi

| File | Loại thay đổi | Mô tả |
|------|--------------|-------|
| `deadlines.txt` | Thêm dần | Thêm deadline tuần 37, 38, 39 khi biết lịch FPL chính xác |
| `app.py` | Thêm code | Route `/final_cup`, API `/api/final_cup`, 6 hàm helper |
| `templates/final_cup_tpl.html` | Tạo mới | Template cho trang Final Cup |
| `templates/header_tpl.html` | Sửa | Thêm nav link Final Cup |
| `static/styles.css` | Thêm | CSS cho Final Cup bracket |

---

## 13. Các Trường Hợp Đặc Biệt Cần Xử Lý

1. **Live data fetch thất bại**: Nếu `extract_league_data()` throw exception → fallback về schedule (pending), hiện thông báo "Không thể tải dữ liệu live"

2. **Tuần chưa có trong weeks.csv**: Nếu cột 37 hoặc 38 trống → `points = 0`, `hits = 0` → không hiển thị kết quả, hiện "Chưa đấu"

3. **Team không match được**: Nếu team từ quarter.csv không tìm thấy trong weeks.csv/live data → dùng 0 điểm, log warning

4. **Tiebreaker đặc biệt**: Luôn hiển thị cách phân định (tiebreaker_used) rõ ràng để minh bạch

5. **Total points tính như thế nào**: 
   - State LIVE_QF: `total_points` từ live API (tổng FPL tích lũy thực)
   - State LIVE_SF: `total_points` = tổng từ weeks.csv cột 1–36 + live_points tuần 37
   - State LIVE_FINAL: tương tự, cộng thêm tuần 37 chính thức + live tuần 38

---

## 14. Thứ Tự Cài Đặt (Implementation Order)

1. **Bước 1**: Thêm functions helper vào `app.py` (calculate_final_cup_match_result, get_week_data_from_csv, get_accumulated_total_from_csv)
2. **Bước 2**: Thêm route + API endpoint vào `app.py` (final_cup route, /api/final_cup, build_final_cup_response)
3. **Bước 3**: Tạo `templates/final_cup_tpl.html` với HTML skeleton và JavaScript
4. **Bước 4**: Thêm CSS vào `static/styles.css`
5. **Bước 5**: Cập nhật `templates/header_tpl.html` thêm nav link
6. **Bước 6**: Test thủ công từng state bằng cách tạm thời mock `get_current_week_info()` trả về từng trạng thái
7. **Bước 7** (khi biết lịch): Thêm deadline tuần 37, 38, 39 vào `deadlines.txt`

---

## 15. Test Scenarios

| Scenario | current_week | deadline_passed | Kỳ vọng |
|---------|-------------|----------------|---------|
| Trước tứ kết | 35 | true | Chỉ hiện lịch QF |
| Đúng ngày QF, chưa qua deadline | 36 | false | Chỉ hiện lịch QF |
| Trong khi QF đang diễn ra | 36 | true | Live QF + lịch SF dự kiến |
| Sau QF, trước BK | 37 | false | Official QF + lịch SF chính thức |
| Trong khi BK đang diễn ra | 37 | true | Official QF + Live SF + lịch CK dự kiến |
| Sau BK, trước CK | 38 | false | Official QF + Official SF + lịch CK |
| Trong khi CK đang diễn ra | 38 | true | Official QF + Official SF + Live CK |
| Sau CK (kết thúc mùa) | 39 | true | Tất cả official + banner vô địch |
| Tiebreaker hits | 36 | true | Hiện thông tin phân định qua hits |
| Tiebreaker total | 36 | true | Hiện thông tin phân định qua tổng điểm |

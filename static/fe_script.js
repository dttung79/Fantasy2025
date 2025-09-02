let currentStartWeek = 0; // Biến để theo dõi tuần bắt đầu hiện tại

function initializeDataTable(data, leagueId, orderByLatestPoints = false, currentWeek = null) {
    const tableHeader = document.getElementById('table-header');
    const tableBody = document.getElementById('data-body');
    const loadingButton = document.getElementById('toggle-button');
    loadingButton.style.display = 'none'; // Hide loading message

    // Clear existing table content
    tableHeader.innerHTML = '';
    tableBody.innerHTML = '';

    // Create table headers dynamically
    const headers = data[0]; // First row contains headers
    const headerRow = document.createElement('tr');
    headers.forEach((header, index) => {
        const th = document.createElement('th');
        th.textContent = header; // Set header text
        
        // Add responsive classes
        if (index === 0) {
            th.className = 'col-team-name';
        } else {
            th.className = 'col-week';
            th.setAttribute('data-week', index);
        }
        
        headerRow.appendChild(th);
    });
    tableHeader.appendChild(headerRow); // Append header row to the table

    // Initialize arrays to track max points and hits for each week
    const maxPoints = Array(headers.length - 1).fill(0); // Exclude team name
    const maxHits = Array(headers.length - 1).fill(0); // Exclude team name

    // Sort data by latest points if the parameter is true
    if (orderByLatestPoints) {
        data = [data[0], ...data.slice(1).sort((a, b) => {
            const latestPointsA = parseInt(a[a.length - 1].split(':')[0]); // Get latest points for team A
            const latestPointsB = parseInt(b[b.length - 1].split(':')[0]); // Get latest points for team B
            return latestPointsB - latestPointsA; // Sort in descending order
        })]; // Ensure the header row is included
    }

    // Process each team row
    data.slice(1).forEach(row => {
        const tr = document.createElement('tr');
        tr.className = 'team-row';

        // Team name
        const teamCell = document.createElement('td');
        teamCell.className = 'col-team-name team-name-cell';
        teamCell.innerHTML = `<span class="team-name-text">${row[0]}</span>`;
        tr.appendChild(teamCell);

        // Process scores and hits for each week
        row.slice(1).forEach((weekData, index) => {
            const [points, hits] = weekData.split(':'); // Split points and hits
            const weekCell = document.createElement('td');
            weekCell.className = 'col-week week-cell';
            weekCell.setAttribute('data-week', index + 1);

            // Create points container
            const pointsContainer = document.createElement('div');
            pointsContainer.className = 'points-container';
            
            const pointsSpan = document.createElement('span');
            pointsSpan.className = 'points-value';
            pointsSpan.textContent = points;
            pointsContainer.appendChild(pointsSpan);

            // Add hits if present
            if (parseInt(hits) > 0) {
                const hitSpan = document.createElement('span');
                hitSpan.className = 'hits-highlight';
                hitSpan.textContent = ` (${hits})`;
                pointsContainer.appendChild(hitSpan);
            }

            weekCell.appendChild(pointsContainer);

            // Update max points and hits for the week
            maxPoints[index] = Math.max(maxPoints[index], parseInt(points));
            maxHits[index] = Math.max(maxHits[index], parseInt(hits));

            // Append the week cell to the row
            tr.appendChild(weekCell);
        });

        // Append the completed row to the table body
        tableBody.appendChild(tr);
    });

    // Highlight max points and hits for each week using CSS classes
    const weekCells = tableBody.querySelectorAll('.team-row');
    weekCells.forEach(row => {
        row.querySelectorAll('.week-cell').forEach((cell, index) => {
            const pointsValue = cell.querySelector('.points-value');
            if (pointsValue) {
                const points = parseInt(pointsValue.textContent);
                // Only highlight if points > 0 (week has been played) and is max for that week
                if (points > 0 && points === maxPoints[index]) {
                    pointsValue.classList.add('max-points'); // Use CSS class for max points styling
                }
            }
        });
    });

    document.getElementById('data-table').style.display = 'table'; // Show the table
    if (orderByLatestPoints)
        drawLineChart(data); // Add this line to draw the chart

    // Hiển thị các cột ưu tiên tuần hiện tại
    const totalWeeks = headers.length - 1; // Trừ cột đầu tiên (Team)
    
    if (currentWeek && currentWeek <= totalWeeks) {
        // Tính toán để hiển thị 10 tuần với tuần hiện tại ở giữa hoặc gần đầu
        if (currentWeek <= 10) {
            // Nếu tuần hiện tại <= 10, hiển thị từ tuần 1-10
            currentStartWeek = 0;
        } else if (currentWeek + 5 <= totalWeeks) {
            // Nếu có thể, đặt tuần hiện tại ở giữa (hiển thị 5 tuần trước và 4 tuần sau)
            currentStartWeek = Math.max(0, currentWeek - 6);
        } else {
            // Nếu gần cuối, hiển thị 10 tuần cuối
            currentStartWeek = Math.max(0, totalWeeks - 10);
        }
    } else {
        // Fallback: hiển thị 10 tuần cuối (logic cũ)
        currentStartWeek = Math.max(0, totalWeeks - 10);
    }
    
    showColumns(currentStartWeek);
    updateArrowButtons();
}

function showColumns(startWeek) {
    const table = document.getElementById('data-table');
    const rows = table.rows;
    const totalWeeks = rows[0].cells.length - 1; // Trừ cột đầu tiên (Team)
    const endWeek = Math.min(startWeek + 10, totalWeeks);

    for (let i = 0; i < rows.length; i++) {
        for (let j = 1; j < rows[i].cells.length; j++) {
            if (j >= startWeek + 1 && j <= endWeek) {
                rows[i].cells[j].style.display = '';
            } else {
                rows[i].cells[j].style.display = 'none';
            }
        }
    }
}

function updateArrowButtons() {
    const table = document.getElementById('data-table');
    const totalWeeks = table.rows[0].cells.length - 1; // Trừ cột đầu tiên (Team)
    const leftArrow = document.getElementById('left-arrow');
    const rightArrow = document.getElementById('right-arrow');

    leftArrow.disabled = currentStartWeek === 0;
    rightArrow.disabled = currentStartWeek + 10 >= totalWeeks;
}

function shiftLeft() {
    if (currentStartWeek > 0) {
        currentStartWeek--;
        showColumns(currentStartWeek);
        updateArrowButtons();
    }
}

function shiftRight() {
    const table = document.getElementById('data-table');
    const totalWeeks = table.rows[0].cells.length - 1; // Trừ cột đầu tiên (Team)
    if (currentStartWeek + 10 < totalWeeks) {
        currentStartWeek++;
        showColumns(currentStartWeek);
        updateArrowButtons();
    }
}

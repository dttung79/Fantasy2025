1. Xây dựng giao diện cho cup {n} (file cup_tpl.html)
Giao diện sẽ hiển thị bảng xếp hạng (tên đội, tổng điểm, hiệu số)
Dưới bảng xếp hạng sẽ là lịch đấu từng tuần và kết quả của từng vòng đấu. Lịch đấu và kết quả sắp xếp từ trên xuống. Ví dụ hiện tại đang là tuần 3, cúp 1 gồm các tuần 1-7, do vậy sẽ hiển thị kết quả của tuần hiện tại là tuần 3 ngay dưới bảng xếp hạng, dưới tuần 3 là tuần 2, dưới tuần 2 là tuần 1.

Ví dụ sang cup 2 và tuần hiện tại đang là tuần 11 thì sẽ hiển thị tuần 11 -> tuần 10 -> tuần 9 -> tuần 8 (tuần đầu tiên của cup 2).

2. Xây dựng các hàm và API cần thiết cho cup {n}
Lịch đấu lấy từ file tournament_{n}.csv
Tuần hiện tại lấy từ deadlines.txt
Điểm của các đội lấy từ file weeks.csv (tuần đã đấu), điểm hiện tại lấy từ hàm extract_league_data
Luật đấu cup đọc từ file cup_rules.md
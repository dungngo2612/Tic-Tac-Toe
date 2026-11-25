# Khung dự án AI: Cờ Caro và Cờ tướng

Đây là bộ khung để bốn thành viên ghép phần việc, chưa chứa mã nguồn và chưa chạy được. Cấu trúc phản ánh dự án hiện tại; các tệp trong README là tệp dự kiến, không phải tệp đã có trong khung.

## Cách ghép phần việc

1. Mỗi người mở phần được giao trong `phan_cong_4_nguoi/01_nguoi_1` đến `04_nguoi_4` của dự án gốc.
2. Trong mỗi phần, bỏ lớp tên nhiệm vụ (`luat_choi`, `thuat_toan_ai`, `giao_dien_tich_hop`, `kiem_thu_thuc_nghiem`), rồi chép tệp vào `aipro` theo đường dẫn còn lại. Ví dụ: `02_nguoi_2/thuat_toan_ai/src/tictactoe/ai/mcts.py` → `aipro/src/tictactoe/ai/mcts.py`.
3. Giữ nguyên tên tệp, đường dẫn và các README trong khung. Phối hợp trước khi sửa tệp do người khác phụ trách. Các README con ghi danh sách tệp theo người.
4. Sau khi nhận đủ mã và cấu hình, kiểm tra tích hợp và chạy thử từ thư mục `aipro`. Các bản sao phân công không phải bốn dự án độc lập.

## Tệp tại thư mục gốc

- Người 4: `play.py` (cổng chơi chung), `pyproject.toml` (cấu hình gói và pytest), `demo_caro.py` (demo cũ; kiểm tra phụ thuộc trước khi sử dụng).
- `README.md`: tài liệu khung này.

## Các phần chính

- `src/tictactoe/`: luật, AI, CLI và web Cờ Caro.
- `xiangqi/`: hai triển khai Cờ tướng hiện có, giao diện và kiểm thử.
- `portal/`: trang chọn trò chơi dùng chung.
- `configs/`, `tests/`: cấu hình và kiểm thử.
- `docs/`, `results/`: tài liệu và kết quả thực nghiệm khi được bổ sung.

Khi đã ghép đủ tệp, từ PowerShell tại `aipro` có thể chạy `python play.py --open`, và kiểm thử các phần chính bằng `python -m pytest -q tests xiangqi\test_web.py`. Cần Python 3.11 trở lên và pytest cho lệnh kiểm thử. Hai bài kiểm thử Cờ tướng cũ dùng import chỉ phù hợp khi chạy từ thư mục `xiangqi`, nên thu thập toàn bộ bằng pytest từ gốc hiện có thể lỗi.

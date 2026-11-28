# Khung dự án AI: Cờ Caro và Cờ tướng

Đây là dự án ghép dần từ phần việc của bốn thành viên. Phần Người 2 đã được thêm vào; các tệp thuộc Người 1, 3 và 4 vẫn đang chờ ghép, nên toàn bộ ứng dụng hiện chưa chạy độc lập.

## Cách ghép phần việc

1. Mỗi người mở phần được giao trong `phan_cong_4_nguoi/01_nguoi_1` đến `04_nguoi_4` của dự án gốc.
2. Trong mỗi phần, bỏ lớp tên nhiệm vụ (`luat_choi`, `thuat_toan_ai`, `giao_dien_tich_hop`, `kiem_thu_thuc_nghiem`), rồi chép tệp vào `aipro` theo đường dẫn còn lại. Ví dụ: `02_nguoi_2/thuat_toan_ai/src/tictactoe/ai/mcts.py` → `aipro/src/tictactoe/ai/mcts.py`.
3. Giữ nguyên tên tệp, đường dẫn và các README trong khung. Phối hợp trước khi sửa tệp do người khác phụ trách. README trong thư mục của mỗi người liệt kê phần được giao.
4. Sau khi nhận đủ mã và cấu hình, kiểm tra tích hợp và chạy thử từ thư mục `aipro`. Các bản sao phân công không phải bốn dự án độc lập.

## Tiến độ ghép

- **Người 2 — đã thêm:** trạng thái Caro, MCTS/rollout/tactics, máy chủ và tài nguyên web Caro, benchmark và các kiểm thử liên quan.
- **Người 1, 3, 4 — đang chờ:** xem README trong thư mục phân công của từng người.
- Phần MCTS và web dùng luật, trạng thái và agent chung; cần ghép các phần còn lại trước khi chạy ứng dụng tổng thể.

## Tệp tại thư mục gốc

- Người 4: `play.py` (cổng chơi chung), `pyproject.toml` (cấu hình gói và pytest), `demo_caro.py` (demo cũ; kiểm tra phụ thuộc trước khi sử dụng).
- `README.md`: tài liệu khung này.

## Các phần chính

- `src/tictactoe/`: mã Caro đang ghép dần; các README con mô tả tệp đã có và phần còn chờ.
- `xiangqi/`: hai triển khai Cờ tướng hiện có, giao diện và kiểm thử.
- `portal/`: trang chọn trò chơi dùng chung.
- `configs/`, `tests/`: cấu hình và kiểm thử.
- `docs/`, `results/`: tài liệu và kết quả thực nghiệm khi được bổ sung.

Khi đã ghép đủ tệp, từ PowerShell tại `aipro` có thể chạy `python play.py --open`. Cấu hình dự án yêu cầu Python 3.11 trở lên; pytest cần thiết để chạy kiểm thử. Các bài kiểm thử hiện chỉ chạy đầy đủ sau khi các phần phụ thuộc của những thành viên còn lại được ghép.

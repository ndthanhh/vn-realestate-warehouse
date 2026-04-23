# Milestone 1.2: Phân trang & Phân loại Dữ liệu (Automation)

Mục tiêu là biến script `crawl_link.py` đơn lẻ thành một hệ thống thu thập link tự động theo vùng miền và số trang.

## User Review Required

> [!IMPORTANT]
> **Cấu trúc URL Phân trang**: Batdongsan dùng mẫu `/p2`, `/p3` ở cuối URL. Chúng ta sẽ dùng vòng lặp để tạo danh sách URL này thay vì click nút "Next" để tăng tốc độ và độ ổn định.

## Các thay đổi chính

### 1. Cấu hình "Seed URLs" (Danh sách điểm bắt đầu)
Thay vì chỉ cào một link cố định, chúng ta sẽ bắt đầu với một danh sách các vùng miền trọng điểm:
- `https://batdongsan.com.vn/ban-can-ho-chung-cu-ha-noi`
- `https://batdongsan.com.vn/ban-can-ho-chung-cu-tp-hcm`
- `https://batdongsan.com.vn/ban-can-ho-chung-cu-da-nang`

### 2. Logic Phân trang (Pagination Loop)
Thiết lập một vòng lặp `for page in range(1, MAX_PAGES + 1)` để tự động duyệt qua các trang.
- Ví dụ: Trang 2 sẽ là `{base_url}/p2`.

### 3. Chiến lược "Săn tin mới" (Avoid Stale Links)
- **Cơ chế Tự động**: Batdongsan mặc định hiện tin mới ở trang đầu. Chúng ta chỉ cần cào từ trang 1 -> 5 hàng ngày.
- **DB Check**: Nhờ lệnh `ON CONFLICT (url) DO NOTHING` chúng ta đã viết ở [Milestone 1.1](file:///c:/vn-realestate-warehouse/docs/implementation_plan.md), những link cũ đã có trong DB sẽ tự động bị bỏ qua, hệ thống chỉ lưu những link "Fresh" (lần đầu xuất hiện).

## Các bước thực hiện cụ thể

1. **Cập nhật hàm `crawl_lists_link`**: Thêm tham số `base_url` và `max_pages`.
2. **Thêm Vòng lặp**: Duyệt qua từng trang, lấy link và gọi hàm `save_to_db` sau mỗi trang.
3. **Thêm thời gian trễ ngẫu nhiên (Random Delay)**: Giữa các trang cần nghỉ 3-7 giây để tránh bị Cloudflare "sờ gáy".

## Open Questions

1. Bạn muốn cào tối đa bao nhiêu trang cho mỗi địa điểm trong một lần chạy? (Gợi ý: 5-10 trang để demo là đủ đẹp).

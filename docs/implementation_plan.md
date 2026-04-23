# Milestone 1: Xây dựng Crawler "Thực chiến"

Mục tiêu là tạo ra một Crawler ổn định, có thể vượt qua rào cản của Batdongsan và lưu trữ dữ liệu thô (Bronze Layer) đúng chuẩn Data Engineering.

## User Review Required

> [!IMPORTANT]
> **Cloudflare Protection**: Batdongsan sử dụng Cloudflare Turnstile rất nghiêm ngặt. Chúng ta sẽ dùng Playwright để mô phỏng người dùng thật, nhưng bạn cần học cách thêm các khoảng trễ (random delays) để tránh bị chặn.

## Quy trình triển khai (Step-by-step)

Chúng ta sẽ không viết 1 file code duy nhất mà chia thành 4 phần (Modules):

### Bước 1: Thiết lập cấu trúc & Thư viện
Bạn cần cài đặt các công cụ sau:
- `playwright`: Để điều khiển trình duyệt và lấy HTML.
- `beautifulsoup4`: Để băm nhỏ HTML và lấy dữ liệu.
- `playwright-stealth`: Để ẩn danh trình duyệt khỏi các hệ thống quét bot.

### Bước 2: Listing Collector (Bộ thu thập link)
**Nhiệm vụ**: Vào trang danh sách (ví dụ: /ban-can-ho-chung-cu-ha-noi), cuộn trang và thu thập tất cả link của các bài đăng.
- **Kỹ thuật cần học**: Cách Page Navigation trong Playwright và cách dùng CSS Selector để lấy thuộc tính `href`.

### Bước 3: Detail Extractor (Bộ bóc tách chi tiết)
**Nhiệm vụ**: Với mỗi link có được, truy cập vào và lấy các trường: Tiêu đề, Giá, Diện tích, Dự án, Địa chỉ, Mô tả, Thông tin liên hệ.
- **Kỹ thuật cần học**: Sử dụng BeautifulSoup để tìm phần tử theo Class Name. Cách xử lý lỗi khi một bài đăng bị thiếu dữ liệu (ví dụ: không có số phòng ngủ).

### Bước 4: Bronze Storage (Lưu trữ dữ liệu thô)
**Nhiệm vụ**: Lưu kết quả trả về dưới dạng file `.json` với tên file là mã băm (Hash) của URL.
- **Kỹ thuật cần học**: Dùng thư viện `hashlib` để tạo Unique ID và `json` để ghi file.

## Các câu hỏi thảo luận trước khi làm

1. **Bạn muốn cào bao nhiêu trang?** (Nên bắt đầu với 2-3 trang danh sách để test logic).
2. **Bạn đã cài đặt Python environment (venv) chưa?**

---

## Verification Plan

1. **Kiểm tra thủ công**: Mở file JSON lưu được ra xem dữ liệu có bị lỗi font hay thiếu trường không.
2. **Kiểm tra Logs**: Crawler phải in ra được tiến độ (đang cào link nào, thành công hay thất bại).

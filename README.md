# Yvonne Finance Job Radar

Trang tổng hợp đầu mối tuyển dụng Finance Controller, FP&A, Finance Business Partner và Senior Financial Analyst tại TP.HCM.

## Tính năng

- GitHub Actions quét 08:15 hằng ngày (Asia/Ho_Chi_Minh), với Bing RSS làm nguồn phát hiện tin miễn phí không API key. Không cam kết độ bao phủ hoặc nguồn luôn hoạt động.
- Lọc vị trí, điểm khớp, từ khóa; xem trang tuyển dụng nguồn và xuất CSV.
- Gắn trạng thái cá nhân: Chưa xem / Quan tâm / Đã ứng tuyển / Không phù hợp. Trạng thái chỉ được lưu ở trình duyệt (localStorage), không đồng bộ nhiều thiết bị.
- Phân biệt tin phát hiện được với tin đã xác minh. Hiện chưa có bộ kiểm chứng tự động cho mức lương, ngày nghỉ cuối tuần hoặc tin còn tuyển.

## Cài đặt (không cần cài phần mềm)

1. Tạo **repository mới** trên GitHub (ví dụ `finance-job-radar`), để **Public** nếu dùng GitHub Pages miễn phí.
2. Bấm **Add file → Upload files**, tải **nội dung bên trong** thư mục dự án lên GitHub. Lưu ý: giao diện Upload files của GitHub có thể không giữ thư mục ẩn `.github` khi kéo thả; với workflow, dùng **Add file → Create new file**, đặt tên `.github/workflows/daily.yml` rồi dán nội dung file workflow.
3. Trong repo vào **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. Trong **Actions → Finance Job Radar daily scan → Run workflow** để quét ngay lần đầu.
5. Vào **Settings → Pages** mở đường link trang web được phát hành: `https://TEN-TAI-KHOAN.github.io/finance-job-radar/` (URL thực tế lấy từ Pages).
6. Nếu commit jobs.json thất bại: vào **Settings → Actions → General → Workflow permissions**, bật **Read and write permissions** nếu tổ chức cho phép; hoặc điều chỉnh cách lưu kết quả. Nếu repo có branch protection, cấu hình quyền bot phù hợp.

## Giới hạn

- RSS công khai là nguồn tìm kiếm *lead*; một số kết quả là bài viết, tin cũ hoặc trang tuyển dụng không còn hoạt động. Không thay thế xác minh JD và liên hệ recruiter.
- Điểm khớp là heuristic theo tiêu đề/snippet và từ khóa, không đánh giá chi tiết JD hay CV; ngưỡng lương ≥30 triệu và nghỉ trọn T7–CN là bộ lọc cần xác minh thủ công, **chưa được thực thi tự động**.
- Công việc trước đây không còn trong kết quả RSS được giữ tối đa 30 ngày; không đồng nghĩa còn mở.
- Nguồn RSS có thể chặn truy cập từ GitHub Actions và dữ liệu khi đó sẽ ít hoặc không có; lỗi được ghi vào `jobs.json`.
- Trang GitHub Pages public có thể xem bởi bất kỳ ai có URL. Không nhập thông tin nhận diện, CV hoặc dữ liệu riêng tư lên repo công khai.

## Tùy chỉnh

Sửa `QUERIES` trong `collector.py` để thay đổi từ khóa. Sửa lịch trong `.github/workflows/daily.yml`. Cấu hình điểm trong `score()`.

## Test cục bộ

`python collector.py` (cần truy cập internet) và `python -m http.server 8000` tại thư mục dự án; mở `http://localhost:8000`.

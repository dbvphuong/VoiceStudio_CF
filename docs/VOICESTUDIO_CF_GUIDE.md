# Hướng dẫn sử dụng chi tiết VoiceStudio_CF 🎙️

Tài liệu này cung cấp hướng dẫn đầy đủ từ A-Z về cách thiết lập, cấu hình và vận hành ứng dụng **VoiceStudio_CF**.

---

## 1. Tổng quan kiến trúc

VoiceStudio_CF được thiết kế theo mô hình phân tầng:
1. **Presentation Layer (PySide6)**: Giao diện người dùng desktop theo phong cách Lavender hiện đại. Mọi tương tác nặng đều được đưa sang background thread bằng `QThread` và `QObject worker` để đảm bảo UI không bao giờ bị đơ (freeze).
2. **Batch Processing Engine**: Đọc file TXT với cơ chế nhận diện encoding thông minh, chia nhỏ văn bản thành các đoạn (chunk) dựa trên ranh giới ngữ nghĩa câu, tránh ngắt giữa câu thoại.
3. **VoiceStudio TTS Core**:
   - `OmniVoiceBackend`: Kế thừa tối ưu hóa Prompt Caching và Low-VRAM Guard từ VoiceStudio.
   - `SherpaOnnxBackend`: Chạy các mô hình ONNX offline nhẹ trên CPU.
   - `MockTTSBackend`: Giúp người dùng hoặc nhà phát triển thử nghiệm toàn bộ luồng tạo file MP3 ngay lập tức.
4. **Audio Assembly & Encoding**: Ghép các đoạn WAV với khoảng lặng ngắt nghỉ tùy chỉnh và encode sang MP3 320kbps bằng FFmpeg qua cơ chế ghi tạm an toàn (`.part`).

---

## 2. Các bước vận hành thực tế

### Bước 1: Khởi động ứng dụng
Nhấp đúp vào `run.bat` trong thư mục dự án.

### Bước 2: Tạo giọng Clone (Voice Cloning)
1. Chuẩn bị 1 file âm thanh mẫu (.wav hoặc .mp3) có độ dài từ 3 đến 15 giây. Âm thanh càng sạch, ít tạp âm và ít nhạc nền thì chất lượng giọng clone càng cao.
2. Mở tab **Quản lý template**.
3. Bấm **+ Thêm template mới**.
4. Chọn chế độ: **Clone giọng mẫu (Voice Cloning)**.
5. Tại mục **Audio mẫu**, bấm **Chọn file…** và tìm đến file âm thanh vừa chuẩn bị. Bấm **Nghe thử** để kiểm tra lại âm thanh.
6. Tại mục **Lời thoại mẫu**, nhập nội dung văn bản mà người trong audio mẫu đã nói.
7. Chọn ngôn ngữ mục tiêu (mặc định là `Vietnamese`).
8. Bấm **Lưu template**.

### Bước 3: Thiết kế giọng tự do (Voice Design)
Nếu không có file audio mẫu, bạn có thể tạo một giọng nói hoàn toàn mới:
1. Chọn chế độ: **Thiết kế giọng (Voice Design)**.
2. Chọn:
   - **Giới tính**: `male` (nam) hoặc `female` (nữ).
   - **Độ tuổi**: `young adult` (thanh niên), `middle-aged` (trung niên), `elderly` (người già)...
   - **Cao độ**: `low pitch` (trầm), `moderate pitch` (vừa), `high pitch` (bổng).
   - **Phong cách**: `whisper` (thì thầm), `calm` (điềm tĩnh), `dramatic` (kịch tính)...
   - **Hướng dẫn thêm**: Bạn có thể ghi thêm mô tả bằng tiếng Anh, ví dụ: `gentle storytelling voice, warm tone`.
3. Bấm **Lưu template**.

### Bước 4: Tạo audio hàng loạt từ file TXT
1. Chuyển sang tab **Xử lý hàng chờ**.
2. Chọn Template giọng bạn vừa tạo ở ô chọn giọng.
3. Bấm **Thêm file TXT** hoặc **Thêm folder** (nếu muốn thêm toàn bộ file trong thư mục).
4. Bấm **▶ Bắt đầu chạy**.
5. Bảng hiển thị 50 dòng sẽ bắt đầu cập nhật tiến độ từng câu.
6. Sau khi hoàn thành, file MP3 sẽ xuất hiện ngay cạnh file TXT hoặc trong thư mục được cấu hình.

---

## 3. Cài đặt tối ưu cho máy có Card NVIDIA GTX 1650 (4GB VRAM)

Với GPU 4GB VRAM, VoiceStudio_CF đã được cấu hình sẵn các cơ chế bảo vệ tối ưu:
- **Ký tự tối đa mỗi đoạn**: Đặt từ `400` đến `600` ký tự.
- **Giới hạn VRAM GPU**: Đặt ở mức `70% - 75%`.
- **Số luồng CPU**: Đặt `2` hoặc `4` luồng.
- **Low-VRAM Guard**: Ứng dụng tự động phát hiện card <= 6GB VRAM và offload bộ giải mã âm thanh sang CPU, đảm bảo quá trình sinh không bao giờ bị dừng giữa chừng.

---

## 4. Xử lý sự cố thường gặp (Troubleshooting)

- **Lỗi thiếu FFmpeg**: Hãy đảm bảo FFmpeg đã được cài đặt và thêm vào biến môi trường PATH của Windows.
- **Lỗi không nạp được CUDA**: Mở **Cài đặt hệ thống → Kiểm tra môi trường** để xem thông tin PyTorch và CUDA. Nếu đang hiển thị CPU, hãy chạy `setup_env.bat` để cài đặt PyTorch CUDA 12.8.
- **Muốn nghe thử nhanh không cần nạp model lớn**: Trong phần template, chuyển Động cơ TTS sang **Mock Engine**. Bạn có thể test toàn bộ quy trình đọc file, phân trang và xuất MP3 chỉ trong vài giây.

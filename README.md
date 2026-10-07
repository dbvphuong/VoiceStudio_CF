# VoiceStudio_CF 🎙️

Ứng dụng Desktop chạy **100% Local** để tạo giọng nói nhân tạo, clone giọng và thiết kế giọng hàng loạt từ file TXT.

Ứng dụng kết hợp sức mạnh động cơ TTS từ [VoiceStudio](https://github.com/debpalash/VoiceStudio) (cốt lõi k2-fsa/OmniVoice hỗ trợ 600+ ngôn ngữ, bộ nhớ đệm Prompt Caching và cân bằng Low-VRAM thông minh) cùng giao diện người dùng tiếng Việt phong cách Lavender tuyệt đẹp, tối ưu hàng chờ và realtime log từ source code **Voice_Omni**.

---

## 🌟 Điểm nổi bật & Tính năng chính

### 1. Động cơ tạo giọng từ VoiceStudio
- **Hỗ trợ 600+ ngôn ngữ**: Tiếng Việt, Anh, Trung, Nhật, Hàn... với chất lượng tự nhiên.
- **Voice Cloning (Clone giọng mẫu)**: Chỉ cần 1 file mẫu audio 3–15 giây và lời thoại mẫu tương ứng.
- **Voice Design (Thiết kế giọng theo mô tả)**: Điều khiển giới tính (nam/nữ), độ tuổi (trẻ, trung niên, già), cao độ (trầm, vừa, bổng), phong cách (thì thầm, kịch tính, vui tươi, đọc tin...), vùng miền và câu lệnh hướng dẫn tự do.
- **Tối ưu hóa độc quyền từ VoiceStudio**:
  - **Voice Clone Prompt Caching**: Giọng mẫu được mã hóa 1 lần duy nhất trong phiên và tái sử dụng cho hàng trăm câu văn bản tiếp theo, tăng tốc độ xử lý gấp **2–3 lần**.
  - **Low-VRAM Guard**: Tự động cân bằng giữa GPU và CPU khi chạy trên các dòng card đồ họa 4GB–6GB VRAM (như NVIDIA GeForce GTX 1650), tránh tuyệt đối lỗi tràn bộ nhớ (Out of Memory).
  - **Đa động cơ (Multi-Engine)**: Hỗ trợ linh hoạt OmniVoice, Sherpa-ONNX (chạy CPU offline siêu nhẹ) và Mock Engine (kiểm thử nhanh).

### 2. Giao diện Desktop hiện đại & Full tính năng
- **Bảng phân trang 50 dòng/trang**: Hiển thị rõ ràng từng đoạn văn bản, trạng thái (Chờ, Đang chạy, Thành công, Lỗi), thời gian xử lý thực tế, tỷ lệ thời gian thực (RTF).
- **Hàng chờ Batch linh hoạt**: Thêm cả thư mục hoặc từng file TXT. Tự động kiểm tra file đã hoàn thành để bỏ qua (skip duplicate).
- **Điều khiển an toàn**: Hỗ trợ Tạm dừng (Pause) và Dừng an toàn (Stop) có hiệu lực sau khi đoạn hiện tại kết thúc, không làm hỏng file âm thanh dở dang.
- **Nghe thử (Audio Preview)**: Hộp thoại nghe thử giọng trực tiếp cho bất kỳ template nào mà không cần tạo file hàng chờ.
- **Realtime Log & Quản lý phiên**: Cửa sổ log nền tối trực quan, lọc cấp độ (Info, Warning, Error), tự động dọn dẹp log quá hạn ngày.
- **Xuất MP3 chất lượng cao**: Tự động ghép nối các đoạn văn bản với khoảng lặng ngắt nghỉ tự nhiên và xuất ra file MP3 thông qua FFmpeg.

---

## 🚀 Cài đặt & Khởi động nhanh

### Yêu cầu hệ thống
- Hệ điều hành: Windows 10/11 (64-bit)
- Python 3.10 trở lên (khuyên dùng Python 3.12)
- Card đồ họa NVIDIA (khuyên dùng) hoặc CPU
- FFmpeg (đã có sẵn trong hệ thống)

### Cách khởi động 1 click
Chỉ cần nhấp đúp vào file:
```cmd
run.bat
```

### Cài đặt môi trường (Nếu cần tạo venv mới)
Chạy script:
```cmd
setup_env.bat
```
Hoặc cài thủ công qua `pip` / `uv`:
```powershell
# Bằng uv:
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
uv pip install -e .

# Hoặc bằng pip:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -e .
```

---

## 📖 Hướng dẫn sử dụng

### 1. Quản lý template giọng
1. Nhấn vào tab **🎭 Quản lý template** ở thanh bên trái.
2. Chọn một template có sẵn hoặc nhấn **+ Thêm template mới**.
3. Chọn chế độ:
   - **Clone giọng mẫu**: Chọn file audio mẫu (định dạng `.wav`, `.mp3`) và nhập lời thoại chính xác trong audio mẫu.
   - **Thiết kế giọng**: Thiết lập giới tính, độ tuổi, cao độ, phong cách...
4. Nhấn **Lưu template**.

### 2. Xử lý hàng chờ tạo audio
1. Tại tab **📋 Xử lý hàng chờ**, chọn template giọng mong muốn từ danh sách thả xuống.
2. Nhấn **📁 Thêm folder** hoặc **📄 Thêm file TXT** để đưa văn bản vào danh sách.
3. Nhấn **▶ Bắt đầu chạy**.
4. Theo dõi tiến trình trực tiếp trên bảng 50 dòng hoặc xem tab **📝 Log realtime**.
5. File MP3 hoàn chỉnh sẽ được tạo tại thư mục đầu ra hoặc ngay cạnh file TXT nguồn.

---

## 📁 Cấu trúc dự án

```text
VoiceStudio_CF/
├── voicestudio_cf/
│   ├── app/                    # Toàn bộ giao diện PySide6 và xử lý ứng dụng
│   │   ├── main.py             # Điểm khởi chạy chính của app
│   │   ├── main_window.py      # Cửa sổ chính & phân trang hàng chờ 50 dòng
│   │   ├── template_page.py    # Trang cấu hình template giọng
│   │   ├── log_page.py         # Màn hình log realtime
│   │   ├── preview_dialog.py   # Hộp thoại nghe thử giọng
│   │   ├── settings_dialog.py  # Hộp thoại cài đặt & kiểm tra phần cứng
│   │   ├── processor.py        # Bộ xử lý hàng chờ & ghép audio MP3
│   │   ├── styles.py           # Theme giao diện Lavender gốc
│   │   └── ...
│   ├── tts/                    # Lõi động cơ TTS từ VoiceStudio
│   │   ├── base.py             # Giao diện trừu tượng TTSBackend
│   │   ├── omnivoice_backend.py# Engine OmniVoice tích hợp Prompt Cache & Low-VRAM
│   │   ├── sherpa_backend.py   # Engine Sherpa-ONNX offline cho CPU
│   │   └── registry.py         # Quản lý và đăng ký các backend
│   └── omnivoice/              # Thư viện mô hình OmniVoice tích hợp sẵn
├── template_voice/             # Mẫu âm thanh và lời thoại có sẵn (Frederick Surrey...)
├── run.bat                     # File kích hoạt ứng dụng 1 click
├── setup_env.bat               # Script cài đặt môi trường tự động
└── pyproject.toml              # Cấu hình dự án và dependencies
```

---

## 🛡️ Bản quyền & Công nghệ
- Động cơ TTS phát triển dựa trên [VoiceStudio](https://github.com/debpalash/VoiceStudio) & [k2-fsa/OmniVoice](https://github.com/k2-fsa/OmniVoice).
- Giao diện và kiến trúc xử lý desktop dựa trên [Voice_Omni].

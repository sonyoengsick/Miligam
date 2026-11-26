
# LAN Chat & File Sharing

Ứng dụng chat và chia sẻ file ngang hàng (Peer-to-Peer) trong cùng mạng LAN/Wi-Fi, viết bằng Python.

Mỗi máy chạy một instance của chương trình và đồng thời đóng vai trò:

- **UDP broadcaster/listener:** quảng bá sự hiện diện và phát hiện các peer.
- **TCP server:** nhận kết nối chat hoặc truyền file từ peer khác.
- **TCP client:** chủ động kết nối tới peer mà người dùng chọn.

> Phiên bản này là bản console có thể chạy và kiểm thử trên nhiều máy. Chương trình dùng Python Socket API và Threading; không dùng framework server hay thư viện mạng bên ngoài.

## 1. Chức năng

| Chức năng | Cách triển khai |
| --- | --- |
| Peer discovery | UDP broadcast `HELLO` mỗi 3 giây |
| Online/away | Trạng thái được gửi trong gói HELLO |
| Peer timeout | Xóa peer sau 10 giây không nhận HELLO |
| Danh sách peer | Lệnh `/list` |
| Chat hai chiều | TCP, một receiver thread cho mỗi kết nối chat |
| Nhiều peer | Có thể giữ nhiều kết nối chat đồng thời |
| Tin chưa đọc | Tin từ peer không phải cửa sổ chat hiện tại được lưu và đếm |
| Gửi file | Kết nối TCP riêng cho từng lần gửi |
| Tiến độ gửi | Hiển thị phần trăm ở phía gửi |
| Nhận file | Lưu vào `downloads/`, ghi `.part` trước rồi đổi tên khi hoàn tất |
| Nhập liệu console | `prompt_toolkit` + `patch_stdout()` để tin đến không phá dòng đang gõ |

## 2. Yêu cầu

- Python 3.10 trở lên.
- Hai hoặc nhiều máy trong cùng mạng LAN/Wi-Fi.
- Cho phép UDP discovery port và TCP listening port qua firewall.
- `prompt_toolkit` (được cài từ `requirements.txt`).

## 3. Cấu trúc project

```text
lan_chat_file_sharing/
├── run.py
├── requirements.txt
├── README.md
├── .gitignore
├── downloads/
│   └── .gitkeep
├── lanchat/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── protocol.py
│   ├── peer_manager.py
│   ├── chat_manager.py
│   ├── connection_manager.py
│   ├── discovery.py
│   ├── tcp_server.py
│   └── file_transfer.py
└── tests/
    └── test_protocol.py
```

### Trách nhiệm từng module

- `app.py`: vòng lặp console, lệnh người dùng, ghép các dịch vụ.
- `config.py`: cấu hình port, broadcast interval, timeout, thư mục tải.
- `protocol.py`: framing TCP; đọc/gửi frame JSON có header độ dài.
- `peer_manager.py`: bảng peer được phát hiện qua UDP, cập nhật và timeout.
- `discovery.py`: UDP broadcaster, listener và peer cleaner.
- `connection_manager.py`: quản lý các kết nối chat TCP và receiver thread.
- `chat_manager.py`: lịch sử chat và số tin chưa đọc.
- `tcp_server.py`: TCP acceptor, phân loại kết nối chat/file.
- `file_transfer.py`: gửi file trên TCP riêng và nhận file an toàn vào thư mục downloads.

## 4. Cài đặt

### Linux (Arch Linux)

```bash
cd lan_chat_file_sharing

python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Nếu dùng Arch Linux và chưa có Python/pip:

```bash
sudo pacman -S python python-pip
```

### Windows

```powershell
cd lan_chat_file_sharing

py -m venv .venv
.venv\Scripts\Activate.ps1

py -m pip install -r requirements.txt
```

## 5. Chạy chương trình

Mở Terminal trên mỗi máy và chạy:

```bash
python run.py --name Andrey
```

Máy thứ hai:

```bash
python run.py --name Minh
```

Mặc định:

- TCP port: `5000`
- UDP discovery port: `9999`
- Broadcast: `255.255.255.255`
- Chu kỳ HELLO: `3` giây
- Peer timeout: `10` giây
- Thư mục nhận file: `downloads/`

Nếu chạy nhiều instance trên cùng một máy, phải dùng TCP port khác nhau:

```bash
python run.py --name Andrey --tcp-port 5000
python run.py --name Test --tcp-port 5001
```

Lưu ý: kiểm thử discovery đáng tin cậy nhất trên hai máy thật cùng LAN. Một số hệ điều hành/router không phân phối broadcast đến nhiều socket cùng bind một UDP port trên cùng máy.

### Tham số tùy chọn

```bash
python run.py --help
```

Ví dụ đổi port:

```bash
python run.py --name Andrey --tcp-port 5000 --udp-port 9999
```

Nếu mạng không chuyển tiếp broadcast mặc định, có thể chỉ định broadcast address phù hợp với subnet, ví dụ `192.168.1.255`:

```bash
python run.py --name Andrey --broadcast 192.168.1.255
```

Địa chỉ broadcast phải phù hợp với cấu hình mạng thực tế của cậu.

## 6. Các lệnh trong ứng dụng

| Lệnh | Ý nghĩa |
| --- | --- |
| `/help` | Hiển thị trợ giúp |
| `/list` | Liệt kê peer đã phát hiện |
| `/chat <name\|number>` | Mở hoặc chuyển sang chat với peer |
| `<văn bản>` | Gửi tin nhắn cho peer đang chat |
| `/leave` | Gửi BYE và đóng chat hiện tại |
| `/send <file-path>` | Gửi file cho peer đang chat |
| `/status online` | Đặt trạng thái online |
| `/status away` | Đặt trạng thái away |
| `/quit` | Thoát chương trình |

Ví dụ:

```text
> /list
Online peers:
  1. Minh             192.168.1.12:5000 online [not connected]

> /chat Minh
[*] Connected to Minh
> Chào Minh!
[Minh] Chào Andrey!

> /send ./report.pdf
[FILE] Sending report.pdf: 25%
[FILE] Sending report.pdf: 50%
...
[FILE] Sent report.pdf to Minh successfully.
```

Nếu peer gửi tin trong khi cậu đang chat với người khác, chương trình sẽ thông báo số tin chưa đọc. Khi chuyển sang peer đó bằng `/chat`, lịch sử và tin chưa đọc được hiển thị.

## 7. Firewall

Mở cả hai port trên máy nhận kết nối. Ví dụ Arch Linux dùng firewalld, zone `public`:

```bash
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --zone=public --add-port=9999/udp
sudo firewall-cmd --zone=public --add-port=5000/tcp
```

Để lưu cấu hình qua reboot:

```bash
sudo firewall-cmd --permanent --zone=public --add-port=9999/udp
sudo firewall-cmd --permanent --zone=public --add-port=5000/tcp
sudo firewall-cmd --reload
```

Nếu đổi TCP port, phải mở đúng port mới trên firewall của máy đó.

Kiểm tra port đang lắng nghe trên Linux:

```bash
ss -lntup | grep -E '5000|9999'
```

Khi không cần thử nghiệm nữa, có thể xóa rule tạm:

```bash
sudo firewall-cmd --zone=public --remove-port=9999/udp
sudo firewall-cmd --zone=public --remove-port=5000/tcp
```

## 8. Giao thức ứng dụng

### 8.1 UDP discovery

Mỗi peer gửi một datagram:

```text
HELLO|<name>|<tcp_port>|<status>
```

Ví dụ:

```text
HELLO|Andrey|5000|online
```

- Đích mặc định: `255.255.255.255:9999`.
- Gửi lại mỗi 3 giây.
- Listener lấy IP nguồn từ `recvfrom()` và TCP port từ payload.
- Không nhận HELLO trong 10 giây thì peer bị đánh dấu offline và xóa khỏi danh sách.
- `away` vẫn được phát hiện, nhưng hiển thị trạng thái away.

### 8.2 TCP control framing

TCP là byte stream, vì vậy chương trình không giả định một lần `recv()` tương ứng một message.

Mỗi control frame có định dạng:

```text
+----------------------+-----------------------------+
| 4-byte unsigned size | JSON payload (UTF-8)        |
+----------------------+-----------------------------+
```

Size là số byte của JSON payload, theo network byte order (big-endian).

Các frame chính:

```json
{"type":"HI","kind":"chat","name":"Andrey","port":5000,"peer_id":"192.168.1.10:5000"}
{"type":"MSG","text":"Xin chào"}
{"type":"BYE"}
```

### 8.3 TCP file transfer

Mỗi lần gửi file mở một TCP connection riêng, không dùng chung socket chat:

1. Gửi frame `HI` với `kind=file`.
2. Gửi frame `FILE_META` gồm tên file và kích thước byte.
3. Gửi đúng số byte nội dung file.
4. Bên nhận ghi vào file `.part`.
5. Chỉ đổi tên thành file hoàn chỉnh khi nhận đủ dữ liệu.

Ví dụ metadata:

```json
{"type":"FILE_META","name":"report.pdf","size":123456}
```

Cách tách socket giúp truyền file không chặn luồng chat.

## 9. Mô hình luồng

| Thread | Công việc |
| --- | --- |
| Main thread | Đọc lệnh và nội dung người dùng |
| UDP broadcaster | Gửi HELLO theo chu kỳ |
| UDP listener | Nhận HELLO và cập nhật peer |
| Peer cleaner | Xóa peer hết timeout |
| TCP acceptor | Chờ kết nối mới |
| Incoming handler | Đọc HI, phân loại chat/file |
| Chat receiver × N | Nhận tin nhắn từ từng peer |
| File sender × N | Gửi file ở luồng riêng |
| File receiver × N | Nhận file từ kết nối riêng |

Dữ liệu dùng chung như peer list, connection registry, chat history và unread counter được bảo vệ bằng `threading.Lock`.

## 10. Kiểm thử

### Test A — Discovery

1. Chạy ứng dụng trên ít nhất hai máy.
2. Đợi khoảng 3–6 giây.
3. Gõ `/list` ở cả hai máy.
4. Đổi trạng thái máy thứ hai bằng `/status away`.
5. Kiểm tra `/list` trên máy thứ nhất.
6. Tắt hẳn máy thứ hai.
7. Đợi hơn 10 giây và kiểm tra peer bị xóa khỏi danh sách.

### Test B — TCP chat

1. Trên máy A, gõ `/list`.
2. Gõ `/chat <tên hoặc số thứ tự>` của máy B.
3. Gửi nhiều tin nhắn hai chiều.
4. Mở chat từ máy C nếu có.
5. Gửi tin từ B trong lúc A đang chat với C.
6. Chuyển lại `/chat B` và kiểm tra lịch sử/tin chưa đọc.
7. Thử `/leave` và kết nối lại.

### Test C — File transfer

1. Mở chat giữa A và B.
2. Gõ `/send ./sample.pdf`.
3. Quan sát phần trăm ở phía gửi.
4. Kiểm tra file ở `downloads/` phía nhận.
5. So sánh kích thước hoặc checksum:

```bash
sha256sum sample.pdf downloads/sample.pdf
```

Hai checksum phải giống nhau.

### Test D — Lỗi

- Gõ `/chta Minh`: chương trình báo lệnh không hợp lệ, không crash.
- Gõ `/send missing.pdf`: báo không tìm thấy file.
- Tắt peer giữa lúc chat: kết nối được đóng và thông báo lỗi.
- Tắt mạng giữa lúc gửi file: file `.part` dở dang bị xóa.
- Gửi dữ liệu không đúng định dạng vào TCP port: kết nối lỗi bị từ chối, server chính vẫn tiếp tục chạy.

### Unit test framing

```bash
python -m unittest discover -s tests -v
```

## 11. Wireshark

Bắt gói trên card mạng Wi-Fi/Ethernet thật khi chạy hai máy.

| Mục tiêu | Display filter |
| --- | --- |
| UDP discovery | `udp.port == 9999` |
| TCP handshake | `tcp.port == 5000 && tcp.flags.syn == 1` |
| FIN/RST | `tcp.flags.fin == 1 \|\| tcp.flags.reset == 1` |
| Theo dõi luồng chat | Chọn packet → Follow → TCP Stream |

Cần chụp:

1. Gói UDP broadcast có payload `HELLO|...`.
2. Bắt tay TCP SYN, SYN-ACK, ACK khi mở chat.
3. TCP stream chứa các frame chat.
4. Kết nối TCP riêng được tạo khi gửi file.
5. FIN khi đóng kết nối bình thường.

JSON control frame có header 4 byte nên khi xem raw stream, phần đầu frame có thể xuất hiện ký tự không in được. Đây là length prefix, không phải dữ liệu rác.

## 12. Giới hạn và hướng phát triển

Đây là bản nền tảng phục vụ học tập và demo trong LAN, chưa phải ứng dụng an toàn để dùng trên mạng công cộng.

- Chưa có xác thực danh tính hay mã hóa TLS; người cùng LAN có thể giả mạo HELLO hoặc kết nối.
- Chưa có resume file transfer, giới hạn quota hoặc chống file độc hại.
- Tên peer không phải định danh bảo mật; `peer_id` hiện dựa trên IP và TCP port.
- Broadcast có thể bị router/AP chặn bởi client isolation hoặc cấu hình mạng.
- Tính năng terminal phụ thuộc `prompt_toolkit` để redraw dòng nhập khi có tin đến.

Hướng nâng cấp:

- TLS và xác thực peer.
- Hash SHA-256 sau khi nhận file.
- Resume truyền file và giới hạn kích thước.
- Lưu lịch sử chat xuống SQLite.
- GUI bằng Qt hoặc Tkinter.
- Kiểm thử tự động nhiều peer và kiểm thử tải.

## 13. Đối chiếu yêu cầu đồ án

| Yêu cầu trong hướng dẫn | Module/điểm triển khai |
| --- | --- |
| UDP HELLO mỗi 3 giây | `discovery.py` |
| Danh sách peer, timeout 10 giây | `peer_manager.py`, `discovery.py` |
| Trạng thái online/away | `discovery.py`, `/status` |
| TCP chat, nhiều peer | `tcp_server.py`, `connection_manager.py` |
| Tin đến khi đang gõ | `prompt_toolkit` + `patch_stdout()` |
| Tin peer khác, unread count | `chat_manager.py`, `app.py` |
| TCP framing | `protocol.py` |
| File trên socket riêng | `file_transfer.py` |
| Hiện tiến độ | `file_transfer.py` |
| Lưu vào downloads | `file_transfer.py` |
| README và hướng dẫn kiểm thử | Tài liệu này |

---

**Lưu ý trước khi nộp:** hãy chạy kiểm thử trên ít nhất hai máy thật cùng LAN, chụp ảnh Wireshark, xác nhận mọi lệnh và tình huống lỗi. README này mô tả thiết kế và cách chạy của mã nguồn; báo cáo kết quả thực nghiệm nên dùng ảnh/log do chính nhóm tạo ra.
#   M i l i g a m  
 
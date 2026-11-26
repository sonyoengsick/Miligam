#import thư viện hệ thống
import socket
import threading
#import file .py của dự án
from .connection_manager import PeerConnection
from .file_transfer import FileTransfer
from .protocol import recv_frame

# Tạo class chấp nhận kết nối TCP
class TCPServer:
    """Accepts incoming chat and file TCP connections."""
    # [SỬA] Thêm tham số on_file_received để truyền cầu nối xuống cho FileTransfer
    def __init__(self, config, local_ip, connection_manager, on_message, on_close, print_fn = print, on_file_received = None):
        """Constructor."""
        self.config = config # cấu hình server như giới hạn port, Frame, ...
        self.local_ip = local_ip # địa chỉ ip của máy hiện tại
        self.connections = connection_manager # quản lí các kết nối peer
        self.on_message = on_message # callback khi nhận được tin nhắn
        self.on_closed = on_close # callback khi kết nối đóng
        self.print = print_fn # hiển thị thông tin
        # [SỬA] Truyền on_file_received vào FileTransfer để khi nhận xong file thì báo ngược lên App
        self.file_transfer = FileTransfer(config, local_ip, print_fn, on_file_received = on_file_received)
        # hàm nội bộ
        self._server = None # socket TCP Server
        self._stop = threading.Event() # flag yêu cầu dừng server
        self._thread = None # thread chạy theo vòng lặp accept

    # hàm khởi chạy TCP Server
    def start(self):
        """Start TCP Server."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Tạo socket server IPv4, TCP
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Cho phép tái sử dụng IP khi còn hiệu lực
        server.bind((self.config.host, self.config.tcp_port)) # bind vào HOST, PORT server đăng kí
        server.listen(32) # lắng nghe kết nối, back_log = 32: hàng đợi kết nối là 32
        server.settimeout(1.0) # thời gian cho các thao tác trên socket là 1s
        self._server = server # lưu socket vào thuộc tính đối tượng hiện tại
        self._thread = threading.Thread(target = self._accept_loop, name = "tcp-acceptor", daemon = True) # tạo thread mới
        self._thread.start() # chạy thread
        self.print(f"[*] TCP Server listening on {self.config.host}:{self.config.tcp_port}")

    # hàm dừng TCP Server
    def stop(self):
        """Stop TCP Server"""
        self._stop.set() # bật flag dừng server
        if self._server: # kiểm tra socket server đóng chưa
            try:
                self._server.close() # Thử đóng socket server
            except OSError:
                pass # Xảy ra lỗi khi đóng socket thì bỏ qua

    # hàm tạo các vòng lặp tiếp nhận kết nối
    def _accept_loop(self):
        """Accept connections until receive STOP flag."""
        while not self._stop.is_set(): # chạy đến khi nhận flag dừng
            try:
                sock, addr = self._server.accept() # chấp nhận các kết nối
            except socket.timeout:
                continue # nếu timeout thì chạy tiếp lần lặp mới
            except OSError:
                break # nếu có lỗi hệ thống lúc accept thì thoát vòng lặp
            threading.Thread(
                target = self._handle_new_connection,
                args = (sock, addr),
                name = f"tcp-incoming-{addr[0]}",
                daemon = True).start() # tạo và khởi chạy một thread riêng cho kết nối mới

    # hàm xử lí kết nối mới
    def _handle_new_connection(self, sock, addr):
        """Handle new connection."""
        handed_off = False
        try:
            sock.settimeout(8.0)
            hello = recv_frame(sock, self.config.max_control_frame) # nhận 1 frame
            if hello.get("type") != "HI": # không phải thông điêp HI
                raise ValueError("First frame must be HI.") # Server từ chối kết nối kèm lí do
            name = str(hello.get("name", "Unknown"))[:64] # lấy dạng string tối đa 64 kí tự tên client
            port = int(hello.get("port", 0)) # lấy port, mặc định là 0
            kind = hello.get("kind") # chat hay truyền file
            peer = {
                "name": name,
                "ip": addr[0],
                "tcp_port": port,
                "status": "online",
                "peer_id": str(hello.get("peer_id", f"{addr[0]}"))
            }
            if not 1 <= port <= 65535:
                raise ValueError("Invalid peer TCP port.")
            if kind == "file":
                sock.settimeout(300.0) # sau 5p không nhận được dữ liệu thì dừng
                self.file_transfer.handle_incoming(sock, peer) # bàn giao socket cho FileTransfer xử lí
                return
            if kind != "chat":
                raise ValueError("Unknown connection kind.")
            sock.settimeout(None) # tắt cho chat
            connection = PeerConnection(sock, peer, peer["peer_id"], self.on_message, self.on_closed) # bàn giao quản lí kết nối chat cho PeerConnection
            if self.connections.register(connection): # nếu đã đăng kí thì chat
                handed_off = True
                self.print(f"[*] Chat connection from {name} ({addr[0]}:{port})")
                connection.start()
        except (OSError, ValueError, TypeError) as exc: # bị lỗi thì thông báo và thử đóng socket
            self.print(f"[TCP] Rejected connection from {addr}: {exc}")
        finally:
            if not handed_off:
                try:
                    sock.close()
                except OSError:
                    pass
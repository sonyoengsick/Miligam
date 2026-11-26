#import thư viện chuẩn
import argparse
import socket
import sys
import threading
from pathlib import Path
#import thư viện hỗ trợ giao diện
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
#import module của dự án
from .config import Config
from .connection_manager import ConnectionManager, PeerConnection
from .chat_manager import ChatManager
from .discovery import DiscoveryService
from .peer_manager import PeerManager
from .protocol import send_frame
from .tcp_server import TCPServer

# [THÊM] Chuỗi đánh dấu ngầm (Control marker) dùng để báo "Đã xem" qua kênh chat TCP mà không cần đổi giao thức protocol.py
SEEN_MARKER = "\x00SEEN\x00"

# Hàm xác định địa chỉ IPv4 của máy khi ra mạng
def detect_local_ip() -> str:
    """Tìm địa chỉ IPv4 nguồn dùng cho route mặc định mà không cần gửi dữ liệu."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # IPv4 UDP
    try:
        probe.connect(("8.8.8.8", 80)) # kết nối với public dns của google
        return probe.getsockname()[0] # getsockname(): (IP, port) -> getsockname()[0]: IP
    except OSError:
        return "127.0.0.1" # loopback
    finally:
        probe.close()

# tạo lớp quản lí chính, giao tiếp với user
class LANChatApp:
    def __init__(self, config: Config):
        config.validate()
        self.config = config
        self.local_ip = detect_local_ip()
        self.peers = PeerManager()
        self.connections = ConnectionManager()
        self.chats = ChatManager()
        self.current_peer_key = None
        self.ui = None # giữ tham chiếu tới cửa sổ GUI
        self._screen_lock = threading.Lock()
        self._stop = threading.Event()
        self.discovery = DiscoveryService(config, self.peers, self.local_ip, self._on_peer_event, self.say)
        # [SỬA] Truyền thêm callback self._on_file_received vào TCPServer để nhận thông báo khi tải xong file từ peer
        self.tcp_server = TCPServer(
            config, self.local_ip, self.connections,
            self._on_message, self._on_connection_closed, self.say,
            on_file_received = self._on_file_received
        )

    # hàm in ra tin nhắn ngay lập tức
    def say(self, message: str):
        with self._screen_lock:
            print(message, flush= True)

    # hàm khởi chạy app
    def start(self):
        Path(self.config.download_dir).mkdir(parents= True, exist_ok= True)
        self.tcp_server.start()
        self.discovery.start()
        self.say("")
        self.say(f"P2P LAN Messenger started as {self.config.username}")
        self.say(f"Local address: {self.local_ip}:{self.config.tcp_port}")
        self.say("Type /help to see commands.")

    # hàm chạy chương trình chính (CLI)
    def run(self):
        self.start()
        session = PromptSession()
        try:
            with patch_stdout():
                while not self._stop.is_set():
                    try:
                        line = session.prompt("> ")
                    except (EOFError, KeyboardInterrupt):
                        self.quit()
                        break
                    try:
                        self._handle_input(line.strip())
                    except Exception as exc:
                        self.say(f"[!] Internal error: {exc!r}")
        finally:
            self.shutdown()

    # hàm chạy chương trình giao diện (GUI)
    def run_gui(self):
        from PyQt6.QtWidgets import QApplication
        from .ui import LanChatUI

        self.start()
        qt_app = QApplication(sys.argv)
        self.ui = LanChatUI(self)
        self.ui.show()
        sys.exit(qt_app.exec())

    # hàm xử lí callback _on_peer_event
    def _on_peer_event(self, event, peer):
        """Cập nhật mỗi khi dùng /list, để tránh bị in lại nhiều lần mỗi khi nhận HELLO."""
        if self.ui:
            self.ui.sig_peer_event.emit(event, peer)
        if event == "online":
            self.say(f"[*] {peer['name']} is online ({peer['ip']}:{peer['tcp_port']})")
        elif event == "offline":
            self.say(f"[-] {peer['name']} is offline")

    # hàm xử lí callback _on_message
    def _on_message(self, connection: PeerConnection, message: str):
        key = connection.key
        # [THÊM] Nếu nhận được gói đánh dấu SEEN_MARKER thì chỉ báo "Đã xem" lên UI, không lưu vào lịch sử chat
        if message == SEEN_MARKER:
            if self.ui:
                self.ui.sig_peer_seen.emit(key, connection.peer["name"])
            return

        is_unread = (key != self.current_peer_key)
        self.chats.add(key, "in", message, unread= is_unread) # thêm lịch sử trò chuyện
        count = self.chats.unread_count(key)
        if self.ui:
            self.ui.sig_message_received.emit(key, connection.peer["name"], message, count)
        if not is_unread: # tin nhắn từ người đang chat chung
            self.say(f"[{connection.peer['name']}] {message}")
            # [THÊM] Đang mở sẵn khung chat với người gửi -> tự gửi ngược SEEN_MARKER để bên kia hiện "Đã xem"
            try:
                connection.send_message(SEEN_MARKER)
            except OSError:
                pass
        else: # tin nhắn đến từ người khác
            self.say(f"[*] New message from {connection.peer['name']} ({count} unread)")

    # [THÊM] Callback được gọi từ FileTransfer khi nhận xong file từ máy khác -> lưu vào ChatManager và đẩy lên khung chat UI
    def _on_file_received(self, peer: dict, saved_path: Path, size: int):
        key = (peer["ip"], peer["tcp_port"])
        # Đổi kích thước byte sang KB/MB cho dễ đọc
        if size >= 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        elif size >= 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"

        text = f"📁 Đã gửi file: {saved_path.name}"
        is_unread = (key != self.current_peer_key)
        self.chats.add(key, "in", text, unread= is_unread)
        count = self.chats.unread_count(key)

        if self.ui:
            self.ui.sig_message_received.emit(key, peer["name"], text, count)

        # Nếu người nhận đang mở sẵn khung chat thì báo "Đã xem" ngược lại luôn
        if not is_unread:
            conn = self.connections.get(key)
            if conn:
                try:
                    conn.send_message(SEEN_MARKER)
                except OSError:
                    pass

    # hàm xử lí callback _on_connection_closed
    def _on_connection_closed(self, connection, reason, already_closing):
        removed = self.connections.remove(connection)
        if removed:
            if self.current_peer_key == connection.key:
                self.current_peer_key = None # peer rời chat
            if self.ui:
                self.ui.sig_connection_closed.emit(connection.key, str(reason))
            if not already_closing: # đã đóng chat
                self.say(f"[*] Chat with {connection.peer['name']} closed: {reason}")

    # hàm xử lí callback _connect_to_peer
    def _connect_to_peer(self, peer):
        key = (peer["ip"], peer["tcp_port"])
        existing = self.connections.get(key)
        if existing:
            return existing
        sock = socket.create_connection((peer["ip"], peer["tcp_port"]), timeout= 8)
        sock.settimeout(None)
        peer_id = f"{self.local_ip}:{self.config.tcp_port}"
        send_frame(sock, {
            "type": "HI",
            "kind": "chat",
            "name": self.config.username,
            "port": self.config.tcp_port,
            "peer_id": peer_id,
        })
        connection = PeerConnection(sock, peer, peer_id, self._on_message, self._on_connection_closed)
        if self.connections.register(connection):
            connection.start()
            self.say(f"[*] Connected to {peer['name']}")
            return connection
        return self.connections.get(key)

    # ================= CÁC HÀM CẦU NỐI CHO GUI =================
    def select_peer_from_ui(self, peer):
        try:
            connection = self._connect_to_peer(peer)
            if connection is None:
                return False, "Không thể kết nối"
            self.current_peer_key = connection.key
            unread = self.chats.clear_unread(connection.key)
            # [SỬA] Chỉ gửi báo "Đã xem" khi thực sự có tin nhắn chưa đọc
            if unread > 0:
                try:
                    connection.send_message(SEEN_MARKER)
                except OSError:
                    pass
            return True, self.chats.history(connection.key)
        except (OSError, ValueError) as exc:
            return False, str(exc)

    def send_message_from_ui(self, peer_key, text: str):
        connection = self.connections.get(peer_key)
        if not connection:
            return False, "Chưa kết nối với người này"
        try:
            connection.send_message(text)
            self.chats.add(connection.key, "out", text)
            return True, ""
        except OSError as exc:
            return False, str(exc)

    # [SỬA] Gắn trực tiếp callback on_progress và on_complete vào FileTransfer.send() để cập nhật thanh % thời gian thực
    def send_file_from_ui(self, peer_key, file_path: str):
        connection = self.connections.get(peer_key)
        if not connection:
            return
        peer = connection.peer
        file_name = Path(file_path).name

        def _on_progress(percent: int):
            if self.ui:
                self.ui.sig_file_progress.emit(peer_key, file_name, percent)

        def _on_complete(success: bool, err: str):
            if success:
                self.chats.add(peer_key, "out", f"✅ Đã gửi file: {file_name} (100%)")
            if self.ui:
                self.ui.sig_file_sent.emit(peer_key, file_name, success, err)

        from .file_transfer import FileTransfer
        # Không cần tạo thread bọc ngoài nữa vì bản thân FileTransfer.send() đã tự tạo thread daemon gửi file
        FileTransfer(self.config, self.local_ip, self.say).send(
            peer, file_path, on_progress= _on_progress, on_complete= _on_complete
        )

    # hàm xử lí input
    def _handle_input(self, line: str):
        if not line:
            return
        if line.startswith("/"):
            self._handle_command(line)
            return
        if self.current_peer_key is None:
            self.say("[!] Open a chat first with /chat <name|number>.")
            return
        connection = self.connections.get(self.current_peer_key)
        if not connection:
            self.say("[!] Current chat is no longer connected.")
            self.current_peer_key = None
            return
        try:
            connection.send_message(line)
            self.chats.add(connection.key, "out", line)
        except (OSError) as exc:
            self.say(f"[!] Could not send message: {exc}")

    # hàm xử lí command
    def _handle_command(self, line: str):
        parts = line.split(maxsplit= 1)
        command = parts[0].lower()
        argument = parts[1].strip() if len(parts) > 1 else ""
        if command == "/help":
            self.say(
                "Commands:\n"
                "  /list                 List discovered peers\n"
                "  /chat <name|number>   Connect to a peer / switch chat\n"
                "  /leave                Close the current chat\n"
                "  /send <file-path>     Send a file to the current peer\n"
                "  /status online|away   Change presence status\n"
                "  /help                 Show this help\n"
                "  /quit                 Exit"
            )
        elif command == "/list":
            self._list_peers()
        elif command == "/chat":
            self._chat(argument)
        elif command == "/leave":
            self._leave()
        elif command == "/send":
            self._send_file(argument)
        elif command == "/status":
            self._set_status(argument)
        elif command == "/quit":
            self.quit()
        else:
            self.say("[!] Unknown command. Type /help.")

    def _list_peers(self):
        peers = sorted(self.peers.snapshot(), key= lambda p: (p["name"].casefold(), p["ip"]))
        if not peers:
            self.say("[*] No peers discovered yet.")
            return
        self.say("Online peers:")
        for index, peer in enumerate(peers, 1):
            connected = "connected" if self.connections.get((peer["ip"], peer["tcp_port"])) else "not connected"
            self.say(
                f"  {index}. {peer['name']:<16} {peer['ip']}:{peer['tcp_port']} "
                f"{peer['status']:<7} [{connected}]"
            )

    def _chat(self, query):
        if not query:
            self.say("Usage: /chat <name|number>")
            return
        peer = self.peers.find(query)
        if not peer:
            self.say("[!] Peer not found or name is ambiguous. Use /list and select its number.")
            return
        try:
            connection = self._connect_to_peer(peer)
            if connection is None:
                self.say("[!] Could not establish chat connection.")
                return
            self.current_peer_key = connection.key
            unread = self.chats.clear_unread(connection.key)
            self.say(f"[*] Chatting with {peer['name']}. {unread} unread message(s).")
            for direction, message in self.chats.history(connection.key):
                label = self.config.username if direction == "out" else peer["name"]
                self.say(f"[{label}] {message}")
        except (OSError, ValueError) as exc:
            self.say(f"[!] Could not connect to {peer['name']}: {exc}")

    def _leave(self):
        if self.current_peer_key is None:
            self.say("[*] No active chat.")
            return
        connection = self.connections.get(self.current_peer_key)
        self.current_peer_key = None
        if connection:
            connection.close(send_bye= True)
            self.connections.remove(connection)
            self.say(f"[*] Left chat with {connection.peer['name']}.")

    def _send_file(self, argument):
        if not argument:
            self.say("Usage: /send <file-path>")
            return
        if self.current_peer_key is None:
            self.say("[!] Open a chat first.")
            return
        connection = self.connections.get(self.current_peer_key)
        if not connection:
            self.say("[!] Current peer is disconnected.")
            return
        peer = connection.peer
        from .file_transfer import FileTransfer
        FileTransfer(self.config, self.local_ip, self.say).send(peer, argument)

    def _set_status(self, status):
        if status not in ("online", "away"):
            self.say("Usage: /status online|away")
            return
        self.discovery.set_status(status)
        self.say(f"[*] Status changed to {status}.")

    def quit(self):
        self._stop.set()

    def shutdown(self):
        self._stop.set()
        self.discovery.stop()
        self.tcp_server.stop()
        self.connections.close_all()
        self.say("[*] LAN Chat stopped.")

def main():
    parser = argparse.ArgumentParser(description="LAN peer-to-peer chat and file sharing.")
    parser.add_argument("--name", required=True, help="Your display name on the LAN.")
    parser.add_argument("--tcp-port", type=int, default=5000, help="TCP listening port (default: 5000).")
    parser.add_argument("--udp-port", type=int, default=9999, help="UDP discovery port (default: 9999).")
    parser.add_argument("--broadcast", default="255.255.255.255", help="IPv4 broadcast address.")
    parser.add_argument("--downloads", default="downloads", help="Directory for received files.")
    args = parser.parse_args()

    config = Config(
        username=args.name,
        tcp_port=args.tcp_port,
        udp_port=args.udp_port,
        broadcast_ip=args.broadcast,
        download_dir=args.downloads,
    )
    try:
        LANChatApp(config).run_gui()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Startup failed: {exc}")
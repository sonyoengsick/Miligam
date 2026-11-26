from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap


AVATAR_COLORS = ["#419FD9", "#FF9800", "#4CAF50", "#F44336", "#9C27B0", "#009688"]


def pick_color(text: str) -> str:
    return AVATAR_COLORS[sum(ord(c) for c in text) % len(AVATAR_COLORS)]


class AvatarWidget(QLabel):
    def __init__(self, text, bg_color="#50A8EB", size=42):
        super().__init__()
        self.setFixedSize(size, size)
        self.set_avatar(text, bg_color, size)

    def set_avatar(self, text, bg_color="#50A8EB", size=42):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

        painter.setPen(QColor("white"))
        font = QFont("Segoe UI", int(size * 0.38), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, (text[:1] or "?").upper())
        painter.end()

        self.setPixmap(pixmap)


class ChatListItemWidget(QWidget):
    def __init__(self, name, subtitle, time_str, color="#50A8EB"):
        super().__init__()
        self.name = name
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        self.avatar = AvatarWidget(name, color, 44)
        layout.addWidget(self.avatar)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)

        top_row = QHBoxLayout()
        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.time_label = QLabel(time_str)
        self.time_label.setFont(QFont("Segoe UI", 8))
        self.time_label.setStyleSheet("color: #888888;")

        top_row.addWidget(self.name_label)
        top_row.addStretch()
        top_row.addWidget(self.time_label)

        self.msg_label = QLabel(subtitle)
        self.msg_label.setFont(QFont("Segoe UI", 9))
        self.msg_label.setStyleSheet("color: #777777;")

        text_layout.addLayout(top_row)
        text_layout.addWidget(self.msg_label)
        layout.addLayout(text_layout)

    def set_selected_style(self, selected: bool):
        if selected:
            self.name_label.setStyleSheet("color: white;")
            self.time_label.setStyleSheet("color: #E0F0FF;")
            self.msg_label.setStyleSheet("color: #E0F0FF;")
        else:
            self.name_label.setStyleSheet("color: #222222;")
            self.time_label.setStyleSheet("color: #888888;")
            self.msg_label.setStyleSheet("color: #777777;")


class MessageWidget(QWidget):
    def __init__(self, sender, text, time_str, is_me=False, avatar_color="#50A8EB"):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        avatar = AvatarWidget(sender, avatar_color, 36)
        layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignTop)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)

        sender_label = QLabel(sender)
        sender_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        sender_label.setStyleSheet("color: #2B82C9;")

        msg_label = QLabel(text)
        msg_label.setFont(QFont("Segoe UI", 10))
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #111111;")
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        content_layout.addWidget(sender_label)
        content_layout.addWidget(msg_label)
        layout.addLayout(content_layout, stretch=1)

        check = "✓✓ " if is_me else ""
        time_label = QLabel(f"<span style='color:#2B82C9;'>{check}</span>{time_str}")
        time_label.setFont(QFont("Segoe UI", 8))
        time_label.setStyleSheet("color: #999999;")
        layout.addWidget(time_label, alignment=Qt.AlignmentFlag.AlignTop)


class LanChatUI(QMainWindow):
    # Signals để nhận dữ liệu từ thread socket an toàn (thread-safe)
    sig_peer_event = pyqtSignal(str, dict)
    sig_message_received = pyqtSignal(object, str, str, int)
    sig_connection_closed = pyqtSignal(object, str)
    sig_status_notice = pyqtSignal(str)

    def __init__(self, app_controller):
        super().__init__()
        self.app = app_controller
        self.setWindowTitle(f"LAN Chat - {self.app.config.username} ({self.app.local_ip}:{self.app.config.tcp_port})")
        self.resize(1000, 650)

        self.current_peer_key = None
        self.peer_items = {}  # {peer_key: (QListWidgetItem, ChatListItemWidget, peer_dict)}

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ================= SIDEBAR TRÁI =================
        left_panel = QFrame()
        left_panel.setFixedWidth(300)
        left_panel.setStyleSheet("background-color: #FFFFFF; border-right: 1px solid #E5E5E5;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        search_bar = QWidget()
        search_bar.setFixedHeight(54)
        search_layout = QHBoxLayout(search_bar)
        search_layout.setContentsMargins(10, 10, 10, 10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search")
        self.search_input.setFixedHeight(32)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #F1F1F1;
                border: none;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 13px;
            }
        """)
        self.search_input.textChanged.connect(self._filter_users)
        search_layout.addWidget(self.search_input)
        left_layout.addWidget(search_bar)

        self.user_list = QListWidget()
        self.user_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: #FFFFFF;
                outline: 0;
            }
            QListWidget::item:selected {
                background-color: #419FD9;
            }
            QListWidget::item:hover:!selected {
                background-color: #F5F5F5;
            }
        """)
        self.user_list.itemClicked.connect(self._handle_user_click)
        left_layout.addWidget(self.user_list)

        bottom_nav = QFrame()
        bottom_nav.setFixedHeight(48)
        bottom_nav.setStyleSheet("border-top: 1px solid #E5E5E5; background-color: #FAFAFA;")
        nav_layout = QHBoxLayout(bottom_nav)
        for icon_txt in ["👤", "📞", "💬", "⚙️"]:
            btn = QPushButton(icon_txt)
            btn.setFlat(True)
            btn.setStyleSheet("font-size: 18px; border: none;")
            nav_layout.addWidget(btn)
        left_layout.addWidget(bottom_nav)

        main_layout.addWidget(left_panel)

        # ================= KHUNG CHAT PHẢI =================
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #FFFFFF;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(54)
        header.setStyleSheet("border-bottom: 1px solid #E5E5E5; background-color: #FFFFFF;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 6, 16, 6)

        self.header_avatar = AvatarWidget("?", "#CCCCCC", 38)
        header_layout.addWidget(self.header_avatar)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        self.header_name = QLabel("Chưa chọn người chat")
        self.header_name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.header_status = QLabel("Đang tìm các máy trong mạng LAN...")
        self.header_status.setFont(QFont("Segoe UI", 9))
        self.header_status.setStyleSheet("color: #888888;")
        title_box.addWidget(self.header_name)
        title_box.addWidget(self.header_status)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        for icon_txt in ["📞", "🔍", "⋯"]:
            btn = QPushButton(icon_txt)
            btn.setFlat(True)
            btn.setStyleSheet("font-size: 16px; color: #2B82C9; border: none; padding: 6px;")
            header_layout.addWidget(btn)

        right_layout.addWidget(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: #FFFFFF;")

        self.msg_container = QWidget()
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.msg_layout.setSpacing(4)
        self.scroll_area.setWidget(self.msg_container)

        right_layout.addWidget(self.scroll_area)

        input_bar = QFrame()
        input_bar.setFixedHeight(52)
        input_bar.setStyleSheet("border-top: 1px solid #E5E5E5; background-color: #FFFFFF;")
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(12, 6, 12, 6)
        input_layout.setSpacing(8)

        self.attach_btn = QPushButton("📎")
        self.attach_btn.setToolTip("Gửi file")
        self.attach_btn.setFixedSize(36, 36)
        self.attach_btn.setStyleSheet("font-size: 18px; border: none; color: #777777;")
        self.attach_btn.clicked.connect(self._handle_attach_file)
        input_layout.addWidget(self.attach_btn)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Write a message...")
        self.msg_input.setStyleSheet("border: none; font-size: 14px; color: #222222;")
        self.msg_input.returnPressed.connect(self._handle_send_click)
        input_layout.addWidget(self.msg_input)

        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(36, 36)
        self.send_btn.setStyleSheet("font-size: 18px; border: none; color: #419FD9;")
        self.send_btn.clicked.connect(self._handle_send_click)
        input_layout.addWidget(self.send_btn)

        right_layout.addWidget(input_bar)
        main_layout.addWidget(right_panel)

    def _connect_signals(self):
        self.sig_peer_event.connect(self._on_peer_event_ui)
        self.sig_message_received.connect(self._on_message_received_ui)
        self.sig_connection_closed.connect(self._on_connection_closed_ui)
        self.sig_status_notice.connect(self._on_status_notice_ui)

    # ================= SLOTS CẬP NHẬT GIAO DIỆN =================
    def _on_peer_event_ui(self, event: str, peer: dict):
        key = (peer["ip"], peer["tcp_port"])
        now_str = datetime.now().strftime("%I:%M %p")

        if event == "online":
            if key in self.peer_items:
                _, widget, _ = self.peer_items[key]
                widget.name_label.setText(peer["name"])
                widget.time_label.setText(now_str)
                self.peer_items[key] = (self.peer_items[key][0], widget, peer)
                return

            item = QListWidgetItem(self.user_list)
            color = pick_color(peer["name"])
            widget = ChatListItemWidget(peer["name"], f"{peer['ip']}:{peer['tcp_port']}", now_str, color)
            item.setSizeHint(QSize(0, 64))
            self.user_list.addItem(item)
            self.user_list.setItemWidget(item, widget)
            self.peer_items[key] = (item, widget, peer)

        elif event == "offline":
            if key in self.peer_items:
                item, _, _ = self.peer_items.pop(key)
                row = self.user_list.row(item)
                self.user_list.takeItem(row)
                if self.current_peer_key == key:
                    self.current_peer_key = None
                    self.header_status.setText("offline")

    def _on_message_received_ui(self, peer_key, sender_name: str, text: str, unread_count: int):
        now_str = datetime.now().strftime("%I:%M %p")
        if peer_key in self.peer_items:
            _, widget, _ = self.peer_items[peer_key]
            preview = f"({unread_count} mới) {text}" if unread_count > 0 else text
            widget.msg_label.setText(preview)
            widget.time_label.setText(now_str)

        if peer_key == self.current_peer_key:
            self._append_message(sender_name, text, is_me=False, time_str=now_str)

    def _on_connection_closed_ui(self, peer_key, reason: str):
        if peer_key == self.current_peer_key:
            self.header_status.setText(f"Đã ngắt kết nối ({reason})")

    def _on_status_notice_ui(self, text: str):
        self.header_status.setText(text)

    # ================= TƯƠNG TÁC NGƯỜI DÙNG =================
    def _handle_user_click(self, clicked_item):
        for key, (item, widget, peer) in self.peer_items.items():
            is_sel = (item == clicked_item)
            widget.set_selected_style(is_sel)
            if is_sel:
                self.current_peer_key = key
                self.header_avatar.set_avatar(peer["name"], pick_color(peer["name"]), 38)
                self.header_name.setText(peer["name"])
                self.header_status.setText(f"{peer['ip']}:{peer['tcp_port']} • đang kết nối...")

                ok, history_or_err = self.app.select_peer_from_ui(peer)
                if ok:
                    self.header_status.setText(f"{peer['ip']}:{peer['tcp_port']} • online")
                    widget.msg_label.setText(f"{peer['ip']}:{peer['tcp_port']}")
                    self._render_history(peer["name"], history_or_err)
                else:
                    self.header_status.setText(f"Lỗi kết nối: {history_or_err}")

    def _handle_send_click(self):
        text = self.msg_input.text().strip()
        if not text or self.current_peer_key is None:
            return
        self.msg_input.clear()

        ok, err = self.app.send_message_from_ui(self.current_peer_key, text)
        if ok:
            now_str = datetime.now().strftime("%I:%M %p")
            self._append_message(self.app.config.username, text, is_me=True, time_str=now_str)
            if self.current_peer_key in self.peer_items:
                _, widget, _ = self.peer_items[self.current_peer_key]
                widget.msg_label.setText(f"You: {text}")
                widget.time_label.setText(now_str)
        else:
            self.header_status.setText(f"Gửi lỗi: {err}")

    def _handle_attach_file(self):
        if self.current_peer_key is None:
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file để gửi")
        if file_path:
            file_name = file_path.split("/")[-1].split("\\")[-1]
            self._append_message(self.app.config.username, f"📁 Đang gửi file: {file_name}", is_me=True)
            self.app.send_file_from_ui(self.current_peer_key, file_path)

    def _filter_users(self, keyword: str):
        kw = keyword.lower()
        for _, (item, _, peer) in self.peer_items.items():
            item.setHidden(kw not in peer["name"].lower())

    def _render_history(self, peer_name: str, history: list):
        self._clear_messages()
        for direction, text in history:
            is_me = (direction == "out")
            sender = self.app.config.username if is_me else peer_name
            self._append_message(sender, text, is_me=is_me, time_str="")

    def _append_message(self, sender: str, text: str, is_me=False, time_str=""):
        if time_str == "":
            time_str = datetime.now().strftime("%I:%M %p")
        msg_w = MessageWidget(sender, text, time_str, is_me, pick_color(sender))
        self.msg_layout.addWidget(msg_w)
        QApplication.processEvents()
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def _clear_messages(self):
        while self.msg_layout.count():
            child = self.msg_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def closeEvent(self, event):
        self.app.shutdown()
        event.accept()
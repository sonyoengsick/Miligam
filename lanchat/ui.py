from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog, QGraphicsDropShadowEffect,
    QSizePolicy, QStackedWidget
)
from PyQt6.QtCore import Qt, QSize, QRect, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap, QIcon, QLinearGradient, QPen


# Tự tạo thư mục lanchat/icons nếu chưa có
ICON_DIR = Path(__file__).resolve().parent / "icons"
ICON_DIR.mkdir(parents=True, exist_ok=True)

FONT_FAMILY = "Calibri"

AVATAR_GRADIENTS = [
    ("#3eb8ff", "#0078ff"),
    ("#FF7E5F", "#FEB47B"),
    ("#43E97B", "#38F9D7"),
    ("#FA709A", "#FEE140"),
    ("#A18CD1", "#FBC2EB"),
    ("#00C6FB", "#005BEA"),
]


def pick_gradient(text: str) -> tuple[str, str]:
    return AVATAR_GRADIENTS[sum(ord(c) for c in text) % len(AVATAR_GRADIENTS)]


def load_icon(filename: str) -> QIcon:
    path = ICON_DIR / filename
    return QIcon(str(path)) if path.exists() else QIcon()


def load_crisp_pixmap(path: Path, size: int) -> QPixmap:
    """Scale ảnh theo đúng DPI màn hình để không bị mờ/vỡ."""
    screen = QApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    px = int(size * dpr)
    pix = QPixmap(str(path)).scaled(
        px, px,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )
    pix.setDevicePixelRatio(dpr)
    return pix


def apply_shadow(widget: QWidget, blur=20, y_offset=4, alpha=40):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)


def setup_autohide_scrollbar(widget):
    """Thanh cuộn mảnh bo tròn, lăn mới hiện, đứng yên 5s tự ẩn."""
    sb = widget.verticalScrollBar()
    style_show = """
        QScrollBar:vertical {
            background: transparent;
            width: 6px;
            margin: 4px 2px 4px 0px;
        }
        QScrollBar::handle:vertical {
            background: rgba(120, 120, 120, 0.55);
            border-radius: 3px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background: rgba(90, 90, 90, 0.8);
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            height: 0px;
            background: none;
        }
    """
    style_hide = """
        QScrollBar:vertical {
            background: transparent;
            width: 6px;
            margin: 4px 2px 4px 0px;
        }
        QScrollBar::handle:vertical {
            background: transparent;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            height: 0px;
            background: none;
        }
    """
    sb.setStyleSheet(style_hide)

    timer = QTimer(widget)
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: sb.setStyleSheet(style_hide))

    def on_scroll():
        sb.setStyleSheet(style_show)
        timer.start(5000)

    sb.valueChanged.connect(on_scroll)
    sb.sliderMoved.connect(on_scroll)
    widget._sb_timer = timer


class AvatarWidget(QLabel):
    """Avatar tròn có nền gradient, vẽ sắc nét High-DPI."""
    def __init__(self, text, size=42, online_dot=False, white_border=False):
        super().__init__()
        self.setFixedSize(size, size)
        self.set_avatar(text, size, online_dot, white_border)

    def set_avatar(self, text, size=42, online_dot=False, white_border=False):
        c1, c2 = pick_gradient(text or "?")
        screen = QApplication.primaryScreen()
        dpr = screen.devicePixelRatio() if screen else 1.0

        pixmap = QPixmap(int(size * dpr), int(size * dpr))
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0, QColor(c1))
        grad.setColorAt(1, QColor(c2))
        painter.setBrush(grad)

        if white_border:
            painter.setPen(QPen(QColor("#FFFFFF"), 2.5))
            painter.drawEllipse(2, 2, size - 4, size - 4)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, size, size)

        painter.setPen(QColor("#FFFFFF"))
        font = QFont(FONT_FAMILY, int(size * 0.38), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, (text[:1] or "?").upper())

        if online_dot:
            dot_size = max(10, int(size * 0.28))
            painter.setBrush(QColor("#2ECC71"))
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            painter.drawEllipse(size - dot_size - 1, size - dot_size - 1, dot_size, dot_size)

        painter.end()
        self.setPixmap(pixmap)


class ChatListItemWidget(QWidget):
    """Item người đang online giống Zalo / Telegram."""
    def __init__(self, name, subtitle, time_str):
        super().__init__()
        self.name = name
        self.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        self.avatar = AvatarWidget(name, size=44, online_dot=True)
        layout.addWidget(self.avatar)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)

        top_row = QHBoxLayout()
        self.name_label = QLabel(name)
        self.name_label.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #1F2937; background: transparent;")

        self.time_label = QLabel(time_str)
        self.time_label.setFont(QFont(FONT_FAMILY, 8))
        self.time_label.setStyleSheet("color: #9CA3AF; background: transparent;")

        top_row.addWidget(self.name_label)
        top_row.addStretch()
        top_row.addWidget(self.time_label)

        bottom_row = QHBoxLayout()
        self.msg_label = QLabel(subtitle)
        self.msg_label.setFont(QFont(FONT_FAMILY, 9))
        self.msg_label.setStyleSheet("color: #6B7280; background: transparent;")

        self.unread_badge = QLabel("")
        self.unread_badge.setFixedHeight(18)
        self.unread_badge.setMinimumWidth(18)
        self.unread_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.unread_badge.setFont(QFont(FONT_FAMILY, 8, QFont.Weight.Bold))
        self.unread_badge.setStyleSheet("""
            background-color: #FF3B5C;
            color: #FFFFFF;
            border-radius: 9px;
            padding: 0 5px;
        """)
        self.unread_badge.hide()

        bottom_row.addWidget(self.msg_label, stretch=1)
        bottom_row.addWidget(self.unread_badge)

        text_layout.addLayout(top_row)
        text_layout.addLayout(bottom_row)
        layout.addLayout(text_layout)

    def set_unread(self, count: int):
        if count > 0:
            self.unread_badge.setText(str(count) if count < 99 else "99+")
            self.unread_badge.show()
        else:
            self.unread_badge.hide()

    def set_selected_style(self, selected: bool):
        if selected:
            self.name_label.setStyleSheet("color: #FFFFFF; background: transparent;")
            self.time_label.setStyleSheet("color: #E0F4FF; background: transparent;")
            self.msg_label.setStyleSheet("color: #E0F4FF; background: transparent;")
        else:
            self.name_label.setStyleSheet("color: #1F2937; background: transparent;")
            self.time_label.setStyleSheet("color: #9CA3AF; background: transparent;")
            self.msg_label.setStyleSheet("color: #6B7280; background: transparent;")


class MessageBubbleWidget(QWidget):
    """Bong bóng tin nhắn kiểu Messenger / Zalo: gửi màu xanh #3eb8ff, nhận màu trắng viền nhẹ."""
    def __init__(self, sender: str, text: str, time_str: str, is_me: bool = False):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(18, 4, 18, 4)
        outer.setSpacing(8)

        if not is_me:
            av = AvatarWidget(sender, size=32)
            outer.addWidget(av, alignment=Qt.AlignmentFlag.AlignBottom)

        bubble = QFrame()
        if is_me:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #3eb8ff;
                    border-radius: 16px;
                    border-bottom-right-radius: 4px;
                }
            """)
            text_color = "#FFFFFF"
            time_color = "#E0F4FF"
        else:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #E5E7EB;
                    border-radius: 16px;
                    border-bottom-left-radius: 4px;
                }
            """)
            text_color = "#1F2937"
            time_color = "#9CA3AF"

        bubble.setMaximumWidth(520)
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)

        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(14, 9, 14, 7)
        b_layout.setSpacing(3)

        msg_lbl = QLabel(text)
        msg_lbl.setFont(QFont(FONT_FAMILY, 12))
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
        msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        b_layout.addWidget(msg_lbl)

        check = " ✓✓" if is_me else ""
        time_lbl = QLabel(f"{time_str}{check}")
        time_lbl.setFont(QFont(FONT_FAMILY, 8))
        time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        time_lbl.setStyleSheet(f"color: {time_color}; background: transparent; border: none;")
        b_layout.addWidget(time_lbl)

        if is_me:
            outer.addStretch()
            outer.addWidget(bubble)
        else:
            outer.addWidget(bubble)
            outer.addStretch()


class LanChatUI(QMainWindow):
    sig_peer_event = pyqtSignal(str, dict)
    sig_message_received = pyqtSignal(object, str, str, int)
    sig_connection_closed = pyqtSignal(object, str)
    sig_status_notice = pyqtSignal(str)

    def __init__(self, app_controller):
        super().__init__()
        self.app = app_controller
        self.setWindowTitle(f"LAN Chat - {self.app.config.username} ({self.app.local_ip}:{self.app.config.tcp_port})")
        self.resize(1180, 720)
        self.setFont(QFont(FONT_FAMILY, 10))

        self.current_peer_key = None
        self.peer_items = {}

        self._init_ui()
        self._connect_signals()
        self._load_initial_peers()

    def _init_ui(self):
        central = QWidget()
        central.setStyleSheet("background-color: #e2e2e2;")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ================= TOP HEADER (#3eb8ff) =================
        top_bar = QFrame()
        top_bar.setFixedHeight(74)
        top_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3eb8ff, stop:1 #1e9cf5);
                border: none;
            }
        """)
        apply_shadow(top_bar, blur=18, y_offset=3, alpha=45)

        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(24, 6, 24, 6)
        top_layout.setSpacing(12)

        # Logo app sắc nét (lanchat/icons/logo.png)
        logo_label = QLabel()
        logo_label.setStyleSheet("background: transparent;")
        logo_path = ICON_DIR / "logo.png"
        if logo_path.exists():
            logo_label.setPixmap(load_crisp_pixmap(logo_path, 62))
        else:
            logo_label.setText("LAN CHAT")
            logo_label.setFont(QFont(FONT_FAMILY, 15, QFont.Weight.Bold))
            logo_label.setStyleSheet("color: white; background: transparent;")
        top_layout.addWidget(logo_label)

        top_layout.addStretch()

        # Thẻ Profile user góc trên bên phải (chỉ đúng 1 khung duy nhất)
        profile_pill = QFrame()
        profile_pill.setObjectName("profilePill")
        profile_pill.setFixedHeight(48)
        profile_pill.setStyleSheet("""
            QFrame#profilePill {
                background-color: rgba(255, 255, 255, 0.22);
                border-radius: 24px;
                border: none;
            }
        """)
        pill_layout = QHBoxLayout(profile_pill)
        pill_layout.setContentsMargins(16, 4, 6, 4)
        pill_layout.setSpacing(10)

        me_name = QLabel(self.app.config.username)
        me_name.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
        me_name.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        pill_layout.addWidget(me_name)

        self.my_avatar = AvatarWidget(self.app.config.username, size=38, online_dot=True, white_border=True)
        self.my_avatar.setStyleSheet("background: transparent; border: none;")
        self.my_avatar.setToolTip(f"{self.app.config.username} • {self.app.local_ip}:{self.app.config.tcp_port}")
        pill_layout.addWidget(self.my_avatar)

        top_layout.addWidget(profile_pill)
        root_layout.addWidget(top_bar)

        # ================= BODY (2 KHUNG BO TRÒN TO HƠN & ĐỔ BÓNG) =================
        body = QWidget()
        body.setStyleSheet("background-color: #e2e2e2;")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(14, 14, 14, 14)
        body_layout.setSpacing(14)

        # ---------- KHUNG TRÁI: TIÊU ĐỀ + SEARCH + ONLINE LIST ----------
        left_card = QFrame()
        left_card.setFixedWidth(340)
        left_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 22px;
            }
        """)
        apply_shadow(left_card, blur=24, y_offset=6, alpha=45)

        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 16, 16, 14)
        left_layout.setSpacing(12)

        # Tiêu đề + số người online
        list_header = QHBoxLayout()
        title_lbl = QLabel("Tin nhắn")
        title_lbl.setFont(QFont(FONT_FAMILY, 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #111827; background: transparent;")

        self.online_count_lbl = QLabel("Online: 0")
        self.online_count_lbl.setFont(QFont(FONT_FAMILY, 8, QFont.Weight.Bold))
        self.online_count_lbl.setStyleSheet("""
            background-color: #E6F6FF;
            color: #0284C7;
            border-radius: 10px;
            padding: 3px 9px;
        """)
        list_header.addWidget(title_lbl)
        list_header.addStretch()
        list_header.addWidget(self.online_count_lbl)
        left_layout.addLayout(list_header)

        # Thanh Search (#eeecec) với icon find.png sắc nét
        search_box = QFrame()
        search_box.setFixedHeight(44)
        search_box.setStyleSheet("""
            QFrame {
                background-color: #eeecec;
                border-radius: 22px;
            }
        """)
        sb_layout = QHBoxLayout(search_box)
        sb_layout.setContentsMargins(15, 0, 14, 0)
        sb_layout.setSpacing(10)

        find_lbl = QLabel()
        find_lbl.setStyleSheet("background: transparent;")
        find_path = ICON_DIR / "find.png"
        if find_path.exists():
            find_lbl.setPixmap(load_crisp_pixmap(find_path, 22))
        else:
            find_lbl.setText("🔍")
            find_lbl.setStyleSheet("font-size: 16px; background: transparent;")
        sb_layout.addWidget(find_lbl)

        self.search_input = QLineEdit()
        self.search_input.setFont(QFont(FONT_FAMILY, 10))
        self.search_input.setPlaceholderText("Tìm kiếm người online...")
        self.search_input.setStyleSheet("border: none; background: transparent; color: #222222; font-size: 13px;")
        self.search_input.textChanged.connect(self._filter_users)
        sb_layout.addWidget(self.search_input)
        left_layout.addWidget(search_box)

        # Danh sách user online
        self.user_list = QListWidget()
        self.user_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                outline: 0;
            }
            QListWidget::item {
                border-radius: 14px;
                margin-bottom: 4px;
            }
            QListWidget::item:selected {
                background-color: #3eb8ff;
            }
            QListWidget::item:hover:!selected {
                background-color: #F3F4F6;
            }
        """)
        self.user_list.itemClicked.connect(self._handle_user_click)
        setup_autohide_scrollbar(self.user_list)
        left_layout.addWidget(self.user_list)

        body_layout.addWidget(left_card)

        # ---------- KHUNG PHẢI: STACK (CHÀO MỪNG / KHUNG CHAT) ----------
        right_card = QFrame()
        right_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 22px;
            }
        """)
        apply_shadow(right_card, blur=24, y_offset=6, alpha=45)

        right_outer = QVBoxLayout(right_card)
        right_outer.setContentsMargins(0, 0, 0, 0)

        self.right_stack = QStackedWidget()
        right_outer.addWidget(self.right_stack)

        # Trang 0: Màn hình chào mừng khi chưa chọn ai
        welcome_page = QWidget()
        welcome_page.setStyleSheet("background: transparent;")
        w_layout = QVBoxLayout(welcome_page)
        w_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_layout.setSpacing(10)

        w_icon = QLabel("💬")
        w_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_icon.setStyleSheet("font-size: 52px; background: transparent;")
        w_title = QLabel(f"Xin chào, {self.app.config.username}!")
        w_title.setFont(QFont(FONT_FAMILY, 16, QFont.Weight.Bold))
        w_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_title.setStyleSheet("color: #1F2937; background: transparent;")
        w_sub = QLabel("Chọn một người để gửi gắm tình yêu nhaa💕!")
        w_sub.setFont(QFont(FONT_FAMILY, 10))
        w_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_sub.setStyleSheet("color: #6B7280; background: transparent;")

        w_layout.addWidget(w_icon)
        w_layout.addWidget(w_title)
        w_layout.addWidget(w_sub)
        self.right_stack.addWidget(welcome_page)

        # Trang 1: Khung chat chính
        chat_page = QWidget()
        chat_page.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(chat_page)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Header người đang nhắn
        chat_header = QWidget()
        chat_header.setFixedHeight(68)
        chat_header.setStyleSheet("background: transparent;")
        ch_layout = QHBoxLayout(chat_header)
        ch_layout.setContentsMargins(20, 10, 20, 10)
        ch_layout.setSpacing(12)

        self.header_avatar = AvatarWidget("?", size=44, online_dot=True)
        ch_layout.addWidget(self.header_avatar)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self.header_name = QLabel("")
        self.header_name.setFont(QFont(FONT_FAMILY, 11, QFont.Weight.Bold))
        self.header_name.setStyleSheet("color: #111827; background: transparent;")

        self.header_status = QLabel("")
        self.header_status.setFont(QFont(FONT_FAMILY, 9))
        self.header_status.setStyleSheet("color: #10B981; background: transparent;")

        title_box.addWidget(self.header_name)
        title_box.addWidget(self.header_status)
        ch_layout.addLayout(title_box)
        ch_layout.addStretch()

        right_layout.addWidget(chat_header)

        # Line chia cắt trên (#eeecec)
        top_line = QFrame()
        top_line.setFixedHeight(2)
        top_line.setStyleSheet("background-color: #eeecec; border: none;")
        right_layout.addWidget(top_line)

        # Khu vực tin nhắn ở giữa
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: #F5F7FA;")
        setup_autohide_scrollbar(self.scroll_area)

        self.msg_container = QWidget()
        self.msg_container.setStyleSheet("background-color: #F5F7FA;")
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.msg_layout.setContentsMargins(10, 14, 10, 14)
        self.msg_layout.setSpacing(6)
        self.scroll_area.setWidget(self.msg_container)

        right_layout.addWidget(self.scroll_area)

        # Line chia cắt dưới (#eeecec)
        bottom_line = QFrame()
        bottom_line.setFixedHeight(2)
        bottom_line.setStyleSheet("background-color: #eeecec; border: none;")
        right_layout.addWidget(bottom_line)

        # Khung nhập tin nhắn bo tròn dạng pill + file.png + send.png
        input_bar = QWidget()
        input_bar.setFixedHeight(68)
        input_bar.setStyleSheet("background: transparent;")
        in_layout = QHBoxLayout(input_bar)
        in_layout.setContentsMargins(16, 12, 16, 12)
        in_layout.setSpacing(10)

        input_pill = QFrame()
        input_pill.setStyleSheet("""
            QFrame {
                background-color: #F3F4F6;
                border-radius: 22px;
            }
        """)
        ip_layout = QHBoxLayout(input_pill)
        ip_layout.setContentsMargins(16, 0, 12, 0)

        self.msg_input = QLineEdit()
        self.msg_input.setFont(QFont(FONT_FAMILY, 11))
        self.msg_input.setPlaceholderText("Nhập tin nhắn...")
        self.msg_input.setStyleSheet("border: none; font-size: 16px; color: #1F2937; background: transparent;")
        self.msg_input.returnPressed.connect(self._handle_send_click)
        ip_layout.addWidget(self.msg_input)
        in_layout.addWidget(input_pill, stretch=1)

        btn_style = """
            QPushButton {
                border: none;
                border-radius: 20px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #EBF7FF;
            }
        """

        self.attach_btn = QPushButton()
        self.attach_btn.setToolTip("Gửi file")
        self.attach_btn.setFixedSize(40, 40)
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        file_icon = load_icon("file.png")
        if not file_icon.isNull():
            self.attach_btn.setIcon(file_icon)
            self.attach_btn.setIconSize(QSize(26, 26))
            self.attach_btn.setStyleSheet(btn_style)
        else:
            self.attach_btn.setText("📎")
            self.attach_btn.setStyleSheet(btn_style + "QPushButton { font-size: 18px; color: #3eb8ff; }")
        self.attach_btn.clicked.connect(self._handle_attach_file)
        in_layout.addWidget(self.attach_btn)

        self.send_btn = QPushButton()
        self.send_btn.setToolTip("Gửi tin nhắn")
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_icon = load_icon("send.png")
        if not send_icon.isNull():
            self.send_btn.setIcon(send_icon)
            self.send_btn.setIconSize(QSize(26, 26))
            self.send_btn.setStyleSheet(btn_style)
        else:
            self.send_btn.setText("➤")
            self.send_btn.setStyleSheet(btn_style + "QPushButton { font-size: 20px; color: #3eb8ff; }")
        self.send_btn.clicked.connect(self._handle_send_click)
        in_layout.addWidget(self.send_btn)

        right_layout.addWidget(input_bar)
        self.right_stack.addWidget(chat_page)
        self.right_stack.setCurrentIndex(0)

        body_layout.addWidget(right_card, stretch=1)
        root_layout.addWidget(body, stretch=1)

    def _connect_signals(self):
        self.sig_peer_event.connect(self._on_peer_event_ui)
        self.sig_message_received.connect(self._on_message_received_ui)
        self.sig_connection_closed.connect(self._on_connection_closed_ui)
        self.sig_status_notice.connect(self._on_status_notice_ui)

    def _load_initial_peers(self):
        for peer in self.app.peers.snapshot():
            self._on_peer_event_ui("online", peer)

    def _update_online_count(self):
        self.online_count_lbl.setText(f"Online: {len(self.peer_items)}")

    # ================= SLOTS CẬP NHẬT GIAO DIỆN =================
    def _on_peer_event_ui(self, event: str, peer: dict):
        key = (peer["ip"], peer["tcp_port"])
        now_str = datetime.now().strftime("%H:%M")

        if event == "online":
            if key in self.peer_items:
                item, widget, _ = self.peer_items[key]
                widget.name_label.setText(peer["name"])
                widget.time_label.setText(now_str)
                self.peer_items[key] = (item, widget, peer)
                return

            item = QListWidgetItem(self.user_list)
            widget = ChatListItemWidget(peer["name"], f"Đang hoạt động • {peer['ip']}", now_str)
            item.setSizeHint(QSize(0, 64))
            self.user_list.addItem(item)
            self.user_list.setItemWidget(item, widget)
            self.peer_items[key] = (item, widget, peer)
            self._update_online_count()

        elif event == "offline":
            if key in self.peer_items:
                item, _, _ = self.peer_items.pop(key)
                row = self.user_list.row(item)
                self.user_list.takeItem(row)
                self._update_online_count()
                if self.current_peer_key == key:
                    self.current_peer_key = None
                    self.header_status.setText("Đã ngoại tuyến")
                    self.header_status.setStyleSheet("color: #9CA3AF; background: transparent;")

    def _on_message_received_ui(self, peer_key, sender_name: str, text: str, unread_count: int):
        now_str = datetime.now().strftime("%H:%M")
        if peer_key in self.peer_items:
            _, widget, _ = self.peer_items[peer_key]
            widget.msg_label.setText(text)
            widget.time_label.setText(now_str)
            widget.set_unread(unread_count if peer_key != self.current_peer_key else 0)

        if peer_key == self.current_peer_key:
            self._append_message(sender_name, text, is_me=False, time_str=now_str)

    def _on_connection_closed_ui(self, peer_key, reason: str):
        if peer_key == self.current_peer_key:
            self.header_status.setText(f"Đã ngắt kết nối ({reason})")
            self.header_status.setStyleSheet("color: #EF4444; background: transparent;")

    def _on_status_notice_ui(self, text: str):
        self.header_status.setText(text)

    # ================= TƯƠNG TÁC NGƯỜI DÙNG =================
    def _handle_user_click(self, clicked_item):
        for key, (item, widget, peer) in self.peer_items.items():
            is_sel = (item == clicked_item)
            widget.set_selected_style(is_sel)
            if is_sel:
                self.current_peer_key = key
                self.right_stack.setCurrentIndex(1)
                self.header_avatar.set_avatar(peer["name"], size=42, online_dot=True)
                self.header_name.setText(peer["name"])
                self.header_status.setText(f"Đang kết nối tới {peer['ip']}:{peer['tcp_port']}...")
                self.header_status.setStyleSheet("color: #6B7280; background: transparent;")

                ok, history_or_err = self.app.select_peer_from_ui(peer)
                if ok:
                    self.header_status.setText(f"● Đang hoạt động • {peer['ip']}:{peer['tcp_port']}")
                    self.header_status.setStyleSheet("color: #10B981; background: transparent;")
                    widget.set_unread(0)
                    self._render_history(peer["name"], history_or_err)
                    self.msg_input.setFocus()
                else:
                    self.header_status.setText(f"Lỗi kết nối: {history_or_err}")
                    self.header_status.setStyleSheet("color: #EF4444; background: transparent;")

    def _handle_send_click(self):
        text = self.msg_input.text().strip()
        if not text or self.current_peer_key is None:
            return
        self.msg_input.clear()

        ok, err = self.app.send_message_from_ui(self.current_peer_key, text)
        if ok:
            now_str = datetime.now().strftime("%H:%M")
            self._append_message(self.app.config.username, text, is_me=True, time_str=now_str)
            if self.current_peer_key in self.peer_items:
                _, widget, _ = self.peer_items[self.current_peer_key]
                widget.msg_label.setText(f"Bạn: {text}")
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
            time_str = datetime.now().strftime("%H:%M")
        msg_w = MessageBubbleWidget(sender, text, time_str, is_me)
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
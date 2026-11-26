from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog, QGraphicsDropShadowEffect,
    QSizePolicy, QStackedWidget, QProgressBar  # [THÊM] QProgressBar để vẽ thanh % gửi file
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


def apply_shadow(widget: QWidget, blur=30, y_offset=4, alpha=50):
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
    """Avatar tròn có nền gradient, vẽ sắc nét High-DPI và hỗ trợ chấm xanh (online) / chấm đỏ (offline)."""
    # [SỬA] Đổi tham số online_dot thành dot_state ("online" = xanh, "offline" = đỏ, None = ẩn chấm)
    def __init__(self, text, size=42, dot_state=None, white_border=False):
        super().__init__()
        self.setFixedSize(size, size)
        self.set_avatar(text, size, dot_state, white_border)

    def set_avatar(self, text, size=42, dot_state=None, white_border=False):
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

        # [SỬA] Vẽ chấm xanh khi online, chấm đỏ khi offline để nhìn phát biết ngay trạng thái user
        if dot_state in ("online", "offline"):
            dot_size = max(10, int(size * 0.28))
            dot_color = "#2ECC71" if dot_state == "online" else "#EF4444"
            painter.setBrush(QColor(dot_color))
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            painter.drawEllipse(size - dot_size - 1, size - dot_size - 1, dot_size, dot_size)

        painter.end()
        self.setPixmap(pixmap)


class ChatListItemWidget(QWidget):
    """Item người đang online/offline giống Zalo / Telegram."""
    def __init__(self, name, subtitle, time_str):
        super().__init__()
        self.name = name
        self.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        self.avatar = AvatarWidget(name, size=44, dot_state="online")
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

    # [SỬA] Đổi chấm trạng thái trên avatar giữa xanh (online) và đỏ (offline)
    def set_online(self, is_online: bool):
        self.avatar.set_avatar(self.name, size=44, dot_state="online" if is_online else "offline")

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
            av = AvatarWidget(sender, size=32, dot_state=None)
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

        self.msg_lbl = QLabel(text)
        self.msg_lbl.setFont(QFont(FONT_FAMILY, 12))
        self.msg_lbl.setWordWrap(True)
        self.msg_lbl.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
        self.msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        b_layout.addWidget(self.msg_lbl)

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


# [THÊM] Widget bong bóng riêng cho việc gửi file, tích hợp thanh QProgressBar hiển thị 0% -> 100% và trạng thái "Đã gửi"
class FileProgressBubbleWidget(QWidget):
    def __init__(self, file_name: str, time_str: str):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(18, 4, 18, 4)
        outer.addStretch()

        bubble = QFrame()
        bubble.setFixedWidth(290)
        bubble.setStyleSheet("""
            QFrame {
                background-color: #3eb8ff;
                border-radius: 16px;
                border-bottom-right-radius: 4px;
            }
        """)

        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(14, 10, 14, 8)
        b_layout.setSpacing(6)

        self.title_lbl = QLabel(f"📁 {file_name}")
        self.title_lbl.setFont(QFont(FONT_FAMILY, 11, QFont.Weight.Bold))
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        b_layout.addWidget(self.title_lbl)

        # Thanh phần trăm tiến độ gửi file
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(7)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.35);
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #FFFFFF;
                border-radius: 3px;
            }
        """)
        b_layout.addWidget(self.progress_bar)

        bottom_row = QHBoxLayout()
        self.status_lbl = QLabel("Đang gửi: 0%")
        self.status_lbl.setFont(QFont(FONT_FAMILY, 9))
        self.status_lbl.setStyleSheet("color: #E0F4FF; background: transparent; border: none;")

        time_lbl = QLabel(f"{time_str} ✓✓")
        time_lbl.setFont(QFont(FONT_FAMILY, 8))
        time_lbl.setStyleSheet("color: #E0F4FF; background: transparent; border: none;")

        bottom_row.addWidget(self.status_lbl)
        bottom_row.addStretch()
        bottom_row.addWidget(time_lbl)
        b_layout.addLayout(bottom_row)

        outer.addWidget(bubble)

    def set_progress(self, percent: int):
        self.progress_bar.setValue(percent)
        self.status_lbl.setText(f"Đang gửi: {percent}%")

    def set_done(self, success: bool, err: str = ""):
        if success:
            self.progress_bar.setValue(100)
            self.status_lbl.setText("100% • Đã gửi")
        else:
            self.status_lbl.setText(f"Lỗi gửi file: {err}")


class LanChatUI(QMainWindow):
    sig_peer_event = pyqtSignal(str, dict)
    sig_message_received = pyqtSignal(object, str, str, int)
    sig_connection_closed = pyqtSignal(object, str)
    sig_status_notice = pyqtSignal(str)
    sig_file_progress = pyqtSignal(object, str, int)          # [THÊM] Tín hiệu cập nhật % gửi file từ thread socket
    sig_file_sent = pyqtSignal(object, str, bool, str)        # [THÊM] Tín hiệu báo gửi file xong/lỗi
    sig_peer_seen = pyqtSignal(object, str)                   # [THÊM] Tín hiệu báo đối phương đã xem tin nhắn

    def __init__(self, app_controller):
        super().__init__()
        self.app = app_controller
        self.setWindowTitle(f"LAN Chat - {self.app.config.username} ({self.app.local_ip}:{self.app.config.tcp_port})")
        self.resize(1180, 720)
        self.setFont(QFont(FONT_FAMILY, 10))

        self.current_peer_key = None
        self.peer_items = {}             # {key: (QListWidgetItem, ChatListItemWidget, peer_dict)}
        self.pending_file_bubbles = {}   # [THÊM] Lưu bong bóng thanh % đang gửi để cập nhật theo từng chunk
        self.seen_widget = None          # [THÊM] Giữ widget dòng chữ "✓ Đã xem" để dời xuống dưới cùng khi có tin mới

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

        # ================= TOP HEADER (GRADIENT #38b6ff -> #0349a6) =================
        top_bar = QFrame()
        top_bar.setFixedHeight(74)
        top_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38b6ff, stop:1 #0349a6);
                border: none;
            }
        """)
        apply_shadow(top_bar, blur=24, y_offset=5, alpha=70)

        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(24, 6, 24, 6)
        top_layout.setSpacing(12)

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

        self.my_avatar = AvatarWidget(self.app.config.username, size=38, dot_state="online", white_border=True)
        self.my_avatar.setStyleSheet("background: transparent; border: none;")
        self.my_avatar.setToolTip(f"{self.app.config.username} • {self.app.local_ip}:{self.app.config.tcp_port}")
        pill_layout.addWidget(self.my_avatar)

        top_layout.addWidget(profile_pill)
        root_layout.addWidget(top_bar)

        # ================= BODY =================
        body = QWidget()
        body.setStyleSheet("background-color: #e2e2e2;")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(26, 24, 26, 26)
        body_layout.setSpacing(22)

        # ---------- KHUNG TRÁI ----------
        left_card = QFrame()
        left_card.setFixedWidth(315)
        left_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 22px;
            }
        """)
        apply_shadow(left_card, blur=36, y_offset=8, alpha=80)

        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 16, 16, 14)
        left_layout.setSpacing(12)

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

        # ---------- KHUNG PHẢI ----------
        right_card = QFrame()
        right_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 22px;
            }
        """)
        apply_shadow(right_card, blur=36, y_offset=8, alpha=80)

        right_outer = QVBoxLayout(right_card)
        right_outer.setContentsMargins(0, 0, 0, 0)

        self.right_stack = QStackedWidget()
        right_outer.addWidget(self.right_stack)

        # Trang 0: Màn hình chào mừng
        welcome_page = QWidget()
        welcome_page.setStyleSheet("background: transparent;")
        w_layout = QVBoxLayout(welcome_page)
        w_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_layout.setSpacing(10)

        w_icon = QLabel("🤏")
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

        chat_header = QWidget()
        chat_header.setFixedHeight(68)
        chat_header.setStyleSheet("background: transparent;")
        ch_layout = QHBoxLayout(chat_header)
        ch_layout.setContentsMargins(20, 10, 20, 10)
        ch_layout.setSpacing(12)

        self.header_avatar = AvatarWidget("?", size=44, dot_state="online")
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

        top_line = QFrame()
        top_line.setFixedHeight(2)
        top_line.setStyleSheet("background-color: #eeecec; border: none;")
        right_layout.addWidget(top_line)

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

        bottom_line = QFrame()
        bottom_line.setFixedHeight(2)
        bottom_line.setStyleSheet("background-color: #eeecec; border: none;")
        right_layout.addWidget(bottom_line)

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
        self.sig_file_progress.connect(self._on_file_progress_ui)   # [THÊM]
        self.sig_file_sent.connect(self._on_file_sent_ui)           # [THÊM]
        self.sig_peer_seen.connect(self._on_peer_seen_ui)           # [THÊM]

    def _load_initial_peers(self):
        for peer in self.app.peers.snapshot():
            self._on_peer_event_ui("online", peer)

    def _update_online_count(self):
        count = sum(1 for _, _, p in self.peer_items.values() if p.get("online", True))
        self.online_count_lbl.setText(f"Online: {count}")

    # [THÊM] Hàm dùng chung để đánh dấu 1 user đã offline ngay lập tức (đổi chấm đỏ ở cả list lẫn header)
    def _mark_peer_offline(self, key):
        now_str = datetime.now().strftime("%H:%M")
        if key in self.peer_items:
            _, widget, old_peer = self.peer_items[key]
            old_peer["online"] = False
            widget.set_online(False)  # Đổi sang chấm đỏ ngay lập tức
            widget.msg_label.setText("Đã ngắt kết nối")
            widget.time_label.setText(now_str)
            self._update_online_count()

            if self.current_peer_key == key:
                self.header_avatar.set_avatar(old_peer["name"], size=44, dot_state="offline")
                self.header_status.setText("● Đã ngắt kết nối")
                self.header_status.setStyleSheet("color: #EF4444; background: transparent;")

    # ================= SLOTS CẬP NHẬT GIAO DIỆN =================
    def _on_peer_event_ui(self, event: str, peer: dict):
        peer = dict(peer)
        key = (peer["ip"], peer["tcp_port"])
        now_str = datetime.now().strftime("%H:%M")

        if event == "online":
            peer["online"] = True

            # Nếu user cũ vừa đăng nhập lại với cùng tên, tái sử dụng lại đúng ô cũ trong list
            if key not in self.peer_items:
                for old_key, (old_item, old_widget, old_peer) in list(self.peer_items.items()):
                    if not old_peer.get("online", True) and old_peer["name"].casefold() == peer["name"].casefold():
                        self.peer_items.pop(old_key)
                        self.peer_items[key] = (old_item, old_widget, peer)
                        if self.current_peer_key == old_key:
                            self.current_peer_key = key
                        break

            if key in self.peer_items:
                item, widget, _ = self.peer_items[key]
                widget.name = peer["name"]
                widget.name_label.setText(peer["name"])
                widget.set_online(True)  # Bật lại chấm xanh
                widget.msg_label.setText(f"Đang hoạt động • {peer['ip']}")
                widget.time_label.setText(now_str)
                self.peer_items[key] = (item, widget, peer)

                if self.current_peer_key == key:
                    self.header_avatar.set_avatar(peer["name"], size=44, dot_state="online")
                    ok, _ = self.app.select_peer_from_ui(peer)
                    if ok:
                        self.header_status.setText(f"● Đang hoạt động • {peer['ip']}:{peer['tcp_port']}")
                        self.header_status.setStyleSheet("color: #10B981; background: transparent;")
                self._update_online_count()
                return

            item = QListWidgetItem(self.user_list)
            widget = ChatListItemWidget(peer["name"], f"Đang hoạt động • {peer['ip']}", now_str)
            item.setSizeHint(QSize(0, 64))
            self.user_list.addItem(item)
            self.user_list.setItemWidget(item, widget)
            self.peer_items[key] = (item, widget, peer)
            self._update_online_count()

        elif event == "offline":
            self._mark_peer_offline(key)

    def _on_message_received_ui(self, peer_key, sender_name: str, text: str, unread_count: int):
        now_str = datetime.now().strftime("%H:%M")
        if peer_key in self.peer_items:
            _, widget, _ = self.peer_items[peer_key]
            # Lấy dòng đầu tiên làm preview trên danh sách bên trái cho gọn
            widget.msg_label.setText(text.splitlines()[0])
            widget.time_label.setText(now_str)
            widget.set_unread(unread_count if peer_key != self.current_peer_key else 0)

        if peer_key == self.current_peer_key:
            self._append_message(sender_name, text, is_me=False, time_str=now_str)

    # [SỬA] Khi kết nối TCP bị đóng (user bên kia thoát app), đổi sang chấm đỏ ngay lập tức không chờ UDP timeout
    def _on_connection_closed_ui(self, peer_key, reason: str):
        self._mark_peer_offline(peer_key)

    def _on_status_notice_ui(self, text: str):
        self.header_status.setText(text)

    # [THÊM] Cập nhật thanh % đang gửi file (0% -> 100%) trên bong bóng chat
    def _on_file_progress_ui(self, peer_key, file_name: str, percent: int):
        bubble = self.pending_file_bubbles.get((peer_key, file_name))
        if bubble:
            bubble.set_progress(percent)

    # [THÊM] Khi gửi file hoàn tất -> đổi chữ thành "100% • Đã gửi" và cập nhật dòng preview bên trái
    def _on_file_sent_ui(self, peer_key, file_name: str, success: bool, err: str):
        bubble = self.pending_file_bubbles.pop((peer_key, file_name), None)
        if bubble:
            bubble.set_done(success, err)
        if success and peer_key in self.peer_items:
            _, widget, _ = self.peer_items[peer_key]
            widget.msg_label.setText(f"Bạn: Đã gửi {file_name}")

    def _remove_seen_indicator(self):
        if self.seen_widget is not None:
            self.msg_layout.removeWidget(self.seen_widget)
            self.seen_widget.deleteLater()
            self.seen_widget = None

    # [SỬA] Thay icon avatar nhỏ bằng dòng chữ "✓ Đã xem" gọn gàng ở dưới bong bóng tin nhắn
    def _on_peer_seen_ui(self, peer_key, peer_name: str):
        if peer_key != self.current_peer_key:
            return
        self._remove_seen_indicator()

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        r_layout = QHBoxLayout(row)
        r_layout.setContentsMargins(18, 0, 22, 4)
        r_layout.addStretch()

        seen_lbl = QLabel("✓ Đã xem")
        seen_lbl.setFont(QFont(FONT_FAMILY, 9))
        seen_lbl.setStyleSheet("color: #6B7280; background: transparent;")
        r_layout.addWidget(seen_lbl)

        self.seen_widget = row
        self.msg_layout.addWidget(row)
        QApplication.processEvents()
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    # ================= TƯƠNG TÁC NGƯỜI DÙNG =================
    def _handle_user_click(self, clicked_item):
        for key, (item, widget, peer) in self.peer_items.items():
            is_sel = (item == clicked_item)
            widget.set_selected_style(is_sel)
            if is_sel:
                self.current_peer_key = key
                self.right_stack.setCurrentIndex(1)
                is_online = peer.get("online", True)
                self.header_avatar.set_avatar(peer["name"], size=44, dot_state="online" if is_online else "offline")
                self.header_name.setText(peer["name"])

                if not is_online:
                    self.header_status.setText("● Đã ngắt kết nối")
                    self.header_status.setStyleSheet("color: #EF4444; background: transparent;")
                    widget.set_unread(0)
                    self._render_history(peer["name"], self.app.chats.history(key))
                    return

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

        if self.current_peer_key in self.peer_items:
            _, _, peer = self.peer_items[self.current_peer_key]
            if not peer.get("online", True):
                self.header_status.setText("● Người này đã ngắt kết nối, chờ họ online lại để gửi")
                self.header_status.setStyleSheet("color: #EF4444; background: transparent;")
                return

        self.msg_input.clear()
        ok, err = self.app.send_message_from_ui(self.current_peer_key, text)

        if not ok and self.current_peer_key in self.peer_items:
            _, _, peer = self.peer_items[self.current_peer_key]
            reconn_ok, _ = self.app.select_peer_from_ui(peer)
            if reconn_ok:
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

    # [SỬA] Tạo bong bóng FileProgressBubbleWidget (có thanh %) rồi mới gọi app.send_file_from_ui
    def _handle_attach_file(self):
        if self.current_peer_key is None:
            return
        if self.current_peer_key in self.peer_items:
            _, _, peer = self.peer_items[self.current_peer_key]
            if not peer.get("online", True):
                self.header_status.setText("● Người này đã ngắt kết nối, ko thể gửi file")
                return
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file để gửi")
        if file_path:
            file_name = Path(file_path).name
            now_str = datetime.now().strftime("%H:%M")
            self._remove_seen_indicator()
            bubble = FileProgressBubbleWidget(file_name, now_str)
            self.msg_layout.addWidget(bubble)
            QApplication.processEvents()
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().maximum()
            )
            self.pending_file_bubbles[(self.current_peer_key, file_name)] = bubble
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
        self._remove_seen_indicator()
        if time_str == "":
            time_str = datetime.now().strftime("%H:%M")
        msg_w = MessageBubbleWidget(sender, text, time_str, is_me)
        self.msg_layout.addWidget(msg_w)
        QApplication.processEvents()
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
        return msg_w

    def _clear_messages(self):
        self.seen_widget = None
        while self.msg_layout.count():
            child = self.msg_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def closeEvent(self, event):
        self.app.shutdown()
        event.accept()
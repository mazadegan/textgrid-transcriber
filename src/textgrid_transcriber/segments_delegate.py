from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPalette
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from textgrid_transcriber.segments_model import STATUS_EMPTY, STATUS_UNVERIFIED, STATUS_VERIFIED


class SegmentListDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        is_selected = bool(option.state & QStyle.State_Selected)
        if is_selected:
            painter.fillRect(option.rect, option.palette.highlight())

        text = index.data(Qt.DisplayRole) or ""
        status = index.data(Qt.UserRole + 1) or STATUS_EMPTY

        palette = option.palette
        text_color = palette.highlightedText().color() if is_selected else palette.text().color()

        rect = option.rect.adjusted(8, 2, -8, -2)
        badge_text = status
        badge_padding_x = 8
        badge_padding_y = 2
        fm = QFontMetrics(option.font)
        badge_width = fm.horizontalAdvance(badge_text) + (badge_padding_x * 2)
        badge_height = fm.height() + (badge_padding_y * 2)

        badge_rect = QRect(
            rect.right() - badge_width,
            rect.center().y() - (badge_height // 2),
            badge_width,
            badge_height,
        )

        if status == STATUS_VERIFIED:
            badge_color = QColor(72, 155, 116)
        elif status == STATUS_UNVERIFIED:
            badge_color = QColor(214, 142, 52)
        else:
            badge_color = QColor(120, 120, 120)

        if is_selected:
            badge_color = badge_color.lighter(125)

        painter.setPen(Qt.NoPen)
        painter.setBrush(badge_color)
        painter.drawRoundedRect(badge_rect, 8, 8)

        painter.setPen(text_color)
        text_rect = QRect(rect.left(), rect.top(), rect.width() - badge_width - 8, rect.height())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)

        badge_text_color = palette.highlightedText().color() if is_selected else palette.brightText().color()
        painter.setPen(badge_text_color)
        painter.drawText(badge_rect, Qt.AlignCenter, badge_text)

        painter.restore()

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        hint.setHeight(32)
        return hint

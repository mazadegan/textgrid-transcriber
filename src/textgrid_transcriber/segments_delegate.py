from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPalette
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from textgrid_transcriber.segments_model import STATUS_EMPTY, STATUS_UNVERIFIED, STATUS_VERIFIED


class SegmentListDelegate(QStyledItemDelegate):
    @staticmethod
    def _badge_colors(status: str, is_selected: bool) -> tuple[QColor, QColor, QColor]:
        if status == STATUS_VERIFIED:
            badge_color = QColor(46, 163, 94)
        elif status == STATUS_UNVERIFIED:
            badge_color = QColor(227, 140, 41)
        else:
            badge_color = QColor(140, 140, 140)

        if is_selected:
            badge_color = badge_color.lighter(120)

        border_color = badge_color.darker(140)
        luminance = (badge_color.red() * 0.299) + (badge_color.green() * 0.587) + (badge_color.blue() * 0.114)
        text_color = QColor(0, 0, 0) if luminance > 160 else QColor(255, 255, 255)
        return badge_color, border_color, text_color

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

        badge_color, border_color, badge_text_color = self._badge_colors(status, is_selected)

        painter.setPen(border_color)
        painter.setBrush(badge_color)
        painter.drawRoundedRect(badge_rect, 8, 8)

        painter.setPen(text_color)
        text_rect = QRect(rect.left(), rect.top(), rect.width() - badge_width - 8, rect.height())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)

        painter.setPen(badge_text_color)
        painter.drawText(badge_rect, Qt.AlignCenter, badge_text)

        painter.restore()

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        hint.setHeight(32)
        return hint

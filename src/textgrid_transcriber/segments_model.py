from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QAbstractTableModel, QSortFilterProxyModel, Qt

from textgrid_transcriber.project import Segment

STATUS_EMPTY = "Empty"
STATUS_UNVERIFIED = "Unverified"
STATUS_VERIFIED = "Verified"


def segment_status(segment: Segment) -> str:
    if not segment.transcript.strip():
        return STATUS_EMPTY
    if segment.verified:
        return STATUS_VERIFIED
    return STATUS_UNVERIFIED


def status_rank(status: str) -> int:
    if status == STATUS_EMPTY:
        return 0
    if status == STATUS_UNVERIFIED:
        return 1
    return 2


class SegmentTableModel(QAbstractTableModel):
    COLUMN_FILE = 0
    COLUMN_STATUS = 1

    def __init__(self, segments: Iterable[Segment] | None = None):
        super().__init__()
        self._segments = list(segments or [])

    def rowCount(self, parent=None):
        return len(self._segments)

    def columnCount(self, parent=None):
        return 2

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        if section == self.COLUMN_FILE:
            return "File"
        if section == self.COLUMN_STATUS:
            return "Status"
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        segment = self._segments[index.row()]
        status = segment_status(segment)
        name = Path(segment.path).name

        if role == Qt.DisplayRole:
            if index.column() == self.COLUMN_FILE:
                return name
            if index.column() == self.COLUMN_STATUS:
                return status
        if role == Qt.UserRole:
            return segment
        if role == Qt.UserRole + 1:
            return status_rank(status)
        if role == Qt.UserRole + 2:
            return segment.end_ms - segment.start_ms
        if role == Qt.UserRole + 3:
            return segment.tier
        if role == Qt.UserRole + 4:
            return segment.transcript
        return None

    def set_segments(self, segments: list[Segment]) -> None:
        self.beginResetModel()
        self._segments = list(segments)
        self.endResetModel()

    def segment_at(self, row: int) -> Segment:
        return self._segments[row]


class SegmentFilterProxy(QSortFilterProxyModel):
    SORT_STATUS = "status"
    SORT_DURATION = "duration"
    SORT_NAME = "name"

    def __init__(self):
        super().__init__()
        self._filter_text = ""
        self._filter_tier = "All"
        self._filter_status = "All"
        self._sort_mode = self.SORT_STATUS

    def set_filter_text(self, text: str) -> None:
        self._filter_text = text.strip().lower()
        self.invalidateFilter()

    def set_filter_tier(self, tier: str) -> None:
        self._filter_tier = tier
        self.invalidateFilter()

    def set_filter_status(self, status: str) -> None:
        self._filter_status = status
        self.invalidateFilter()

    def set_sort_mode(self, mode: str) -> None:
        self._sort_mode = mode
        self.invalidate()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        segment = model.segment_at(source_row)

        if self._filter_tier != "All" and segment.tier != self._filter_tier:
            return False

        status = segment_status(segment)
        if self._filter_status != "All" and status != self._filter_status:
            return False

        if self._filter_text:
            name = Path(segment.path).name.lower()
            transcript = segment.transcript.lower()
            if self._filter_text not in name and self._filter_text not in transcript:
                return False

        return True

    def lessThan(self, left, right):
        model = self.sourceModel()
        left_segment = model.segment_at(left.row())
        right_segment = model.segment_at(right.row())

        if self._sort_mode == self.SORT_DURATION:
            left_value = left_segment.end_ms - left_segment.start_ms
            right_value = right_segment.end_ms - right_segment.start_ms
        elif self._sort_mode == self.SORT_NAME:
            left_value = Path(left_segment.path).name
            right_value = Path(right_segment.path).name
        else:
            left_value = status_rank(segment_status(left_segment))
            right_value = status_rank(segment_status(right_segment))

        if left_value == right_value:
            left_value = Path(left_segment.path).name
            right_value = Path(right_segment.path).name

        return left_value < right_value

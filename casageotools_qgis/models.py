#  Copyright 2026 casaGeo Data + Services GmbH <info@casageo.de>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  SPDX-License-Identifier: Apache-2.0

from typing import LiteralString, override

from qgis.PyQt.QtCore import (
    QAbstractListModel,
    QCollator,
    QCoreApplication,
    QModelIndex,
    QObject,
    Qt,
)


class CasaGeoToolsUnitSystemModel(QAbstractListModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.__systems = [
            {"id": "metric", "name": self.__tr("Metric", "Unit System")},
            {"id": "imperial", "name": self.__tr("Imperial", "Unit System")},
        ]

    @override
    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self.__systems)

    @override
    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if (
            section == 0
            and orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.__tr("Unit System", "Column Header")
        return None

    @override
    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> str | None:
        if not index.isValid() or index.row() >= self.rowCount():
            return None

        match role:
            case Qt.ItemDataRole.DisplayRole:
                return self.__systems[index.row()]["name"]
            case Qt.ItemDataRole.EditRole:
                return self.__systems[index.row()]["id"]
        return None

    @staticmethod
    def __tr(
        sourceText: LiteralString,
        disambiguation: LiteralString | None = None,
        /,
        n: int = -1,
    ) -> str:
        return QCoreApplication.translate(
            __class__.__name__, sourceText, disambiguation, n
        )


class CasaGeoToolsPoliticalViewModel(QAbstractListModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._default_view = {
            "code": "",
            "name": self.__tr("Default", "Political View"),
        }
        self._views = [
            {"code": "ARG", "name": self.__tr("Argentina", "Political View")},
            {"code": "EGY", "name": self.__tr("Egypt", "Political View")},
            {"code": "KEN", "name": self.__tr("Kenya", "Political View")},
            {"code": "IND", "name": self.__tr("India", "Political View")},
            {"code": "MAR", "name": self.__tr("Morocco", "Political View")},
            {"code": "PAK", "name": self.__tr("Pakistan", "Political View")},
            {"code": "RUS", "name": self.__tr("Russia", "Political View")},
            {"code": "SDN", "name": self.__tr("Sudan", "Political View")},
            {"code": "SRB", "name": self.__tr("Serbia", "Political View")},
            {"code": "SUR", "name": self.__tr("Suriname", "Political View")},
            {"code": "SYR", "name": self.__tr("Syria", "Political View")},
            {"code": "TUR", "name": self.__tr("Turkey", "Political View")},
            {"code": "TZA", "name": self.__tr("Tanzania", "Political View")},
            {"code": "URY", "name": self.__tr("Uruguay", "Political View")},
            {"code": "VNM", "name": self.__tr("Vietnam", "Political View")},
        ]

    @override
    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._views) + 1

    @override
    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if (
            section == 0
            and orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.__tr("Political View", "Column Header")

        return None

    @override
    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> str | None:
        if not index.isValid() or index.row() >= self.rowCount() or index.column() != 0:
            return None

        item = self._default_view if index.row() == 0 else self._views[index.row() - 1]

        match role:
            case Qt.ItemDataRole.DisplayRole:
                return item["name"]
            case Qt.ItemDataRole.EditRole:
                return item["code"]
            case Qt.ItemDataRole.UserRole:
                return item["code"]
        return None

    @override
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        collator = QCollator()
        self._views.sort(
            key=lambda item: collator.sortKey(item["name"]),
            reverse=(order == Qt.SortOrder.DescendingOrder),
        )

    @staticmethod
    def __tr(
        sourceText: LiteralString,
        disambiguation: LiteralString | None = None,
        /,
        n: int = -1,
    ) -> str:
        return QCoreApplication.translate(
            __class__.__name__, sourceText, disambiguation, n
        )

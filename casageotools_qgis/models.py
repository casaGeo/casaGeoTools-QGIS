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

from collections.abc import Mapping
from typing import TYPE_CHECKING, Final, override

from qgis.PyQt.QtCore import (
    QT_VERSION,
    QAbstractListModel,
    QCollator,
    QLocale,
    QModelIndex,
    QObject,
    Qt,
)

from .utils import QT_VERSION_CHECK, TrMethod

if TYPE_CHECKING:
    from .plugin import CasaGeoToolsPlugin


POLITICAL_VIEW_QLOCALE_ALPHA3_MAPPING: Final[Mapping[QLocale.Country, str]] = {
    QLocale.Country.Argentina: "ARG",
    QLocale.Country.Egypt: "EGY",
    QLocale.Country.India: "IND",
    QLocale.Country.Kenya: "KEN",
    QLocale.Country.Morocco: "MAR",
    QLocale.Country.Pakistan: "PAK",
    QLocale.Country.Russia: "RUS",
    QLocale.Country.Sudan: "SDN",
    QLocale.Country.Serbia: "SRB",
    QLocale.Country.Suriname: "SUR",
    QLocale.Country.Syria: "SYR",
    QLocale.Country.Turkey: "TUR",
    QLocale.Country.Tanzania: "TZA",
    QLocale.Country.Uruguay: "URY",
    QLocale.Country.Vietnam: "VNM",
}


def preferredLanguagesFromLocale(locale: QLocale) -> list[str]:
    return locale.uiLanguages()


def preferredUnitSystemFromLocale(locale: QLocale) -> str | None:
    match locale.measurementSystem():
        case QLocale.MeasurementSystem.MetricSystem:
            return "metric"
        case QLocale.MeasurementSystem.ImperialSystem:
            return "imperial"
    return None


def preferredPoliticalViewFromLocale(locale: QLocale) -> str | None:
    QT_VERSION_6_2 = QT_VERSION_CHECK(6, 2)
    territory = locale.territory() if QT_VERSION >= QT_VERSION_6_2 else locale.country()
    return POLITICAL_VIEW_QLOCALE_ALPHA3_MAPPING.get(territory)


class CasaGeoToolsUnitSystemModel(QAbstractListModel):
    __tr = TrMethod()

    def __init__(
        self, plugin: "CasaGeoToolsPlugin", parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        trUnitSystem = plugin.translations.translateUnitSystem
        self._default = preferredUnitSystemFromLocale(QLocale()) or "metric"
        self._unit_systems = [
            {"id": "metric", "name": trUnitSystem("metric")},
            {"id": "imperial", "name": trUnitSystem("imperial")},
        ]
        self._unit_system_map = {elem["id"]: elem for elem in self._unit_systems}

    @override
    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._unit_systems) + 1

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
        if not (index.isValid() and 0 <= index.row() < self.rowCount()):
            return None

        if index.row() == 0:
            match role:
                case Qt.ItemDataRole.DisplayRole:
                    return self.__tr("System default ({value})").format(
                        value=self._unit_system_map[self._default]["name"],
                    )
                case Qt.ItemDataRole.AccessibleTextRole:
                    return self.__tr("System default, currently {value}").format(
                        value=self._unit_system_map[self._default]["name"],
                    )
                case Qt.ItemDataRole.UserRole:
                    return ""
            return None

        match role:
            case Qt.ItemDataRole.DisplayRole:
                return self._unit_systems[index.row() - 1]["name"]
            case Qt.ItemDataRole.UserRole:
                return self._unit_systems[index.row() - 1]["id"]

        return None


class CasaGeoToolsPoliticalViewModel(QAbstractListModel):
    __tr = TrMethod()

    def __init__(
        self, plugin: "CasaGeoToolsPlugin", parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        trPoliticalView = plugin.translations.translatePoliticalView
        self._default = preferredPoliticalViewFromLocale(QLocale()) or "XXX"
        self._international_view = {"code": "XXX", "name": trPoliticalView("XXX")}
        # Sadly QLocale.countryToString() does not return localized names.
        self._views = [
            {"code": "ARG", "name": trPoliticalView("ARG")},
            {"code": "EGY", "name": trPoliticalView("EGY")},
            {"code": "KEN", "name": trPoliticalView("KEN")},
            {"code": "IND", "name": trPoliticalView("IND")},
            {"code": "MAR", "name": trPoliticalView("MAR")},
            {"code": "PAK", "name": trPoliticalView("PAK")},
            {"code": "RUS", "name": trPoliticalView("RUS")},
            {"code": "SDN", "name": trPoliticalView("SDN")},
            {"code": "SRB", "name": trPoliticalView("SRB")},
            {"code": "SUR", "name": trPoliticalView("SUR")},
            {"code": "SYR", "name": trPoliticalView("SYR")},
            {"code": "TUR", "name": trPoliticalView("TUR")},
            {"code": "TZA", "name": trPoliticalView("TZA")},
            {"code": "URY", "name": trPoliticalView("URY")},
            {"code": "VNM", "name": trPoliticalView("VNM")},
        ]
        self._view_map = {elem["code"]: elem for elem in self._views}
        self._view_map[self._international_view["code"]] = self._international_view

    @override
    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._views) + 2

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
        if not (index.isValid() and 0 <= index.row() < self.rowCount()):
            return None

        if index.row() == 0:
            match role:
                case Qt.ItemDataRole.DisplayRole:
                    return self.__tr("System default ({value})").format(
                        value=self._view_map[self._default]["name"],
                    )
                case Qt.ItemDataRole.AccessibleTextRole:
                    return self.__tr("System default, currently {value}").format(
                        value=self._view_map[self._default]["name"],
                    )
                case Qt.ItemDataRole.UserRole:
                    return ""
            return None

        item = (
            self._international_view
            if index.row() == 1
            else self._views[index.row() - 2]
        )

        match role:
            case Qt.ItemDataRole.DisplayRole:
                return item["name"]
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

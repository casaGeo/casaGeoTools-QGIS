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

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QWidget

from .models import CasaGeoToolsPoliticalViewModel, CasaGeoToolsUnitSystemModel
from .ui.MainDialog import Ui_CasaGeoToolsMainDialog


class CasaGeoToolsMainDialog(QDialog):
    IdentifierRole = Qt.ItemDataRole.UserRole

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.ui = Ui_CasaGeoToolsMainDialog()
        self.ui.setupUi(self)

        # self.ui.apikey_lineEdit.setFont(
        #     QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        # )

        self.unit_system_model = CasaGeoToolsUnitSystemModel()
        self.ui.unitspref_comboBox.setModel(self.unit_system_model)

        self.political_views_model = CasaGeoToolsPoliticalViewModel()
        self.ui.politicalpref_comboBox.setModel(self.political_views_model)

    # def make_unit_system_model(self) -> QStandardItemModel:
    #     model = QStandardItemModel()
    #
    #     item = QStandardItem(self.tr("Metric", "Unit System"))
    #     item.setData("metric", CasaGeoToolsMainDialog.IdentifierRole)
    #     model.appendRow(item)
    #
    #     item = QStandardItem(self.tr("Imperial", "Unit System"))
    #     item.setData("imperial", CasaGeoToolsMainDialog.IdentifierRole)
    #     model.appendRow(item)
    #
    #     return model

    # def make_political_views_model(self) -> QStandardItemModel:
    #     model = QStandardItemModel()
    #
    #     # https://docs.here.com/geocoding-and-search/docs/political-views-coverage
    #     views = {
    #         "ARG": self.tr("Argentina", "Political View"),
    #         "EGY": self.tr("Egypt", "Political View"),
    #         "KEN": self.tr("Kenya", "Political View"),
    #         "IND": self.tr("India", "Political View"),
    #         "MAR": self.tr("Morocco", "Political View"),
    #         "PAK": self.tr("Pakistan", "Political View"),
    #         "RUS": self.tr("Russia", "Political View"),
    #         "SDN": self.tr("Sudan", "Political View"),
    #         "SRB": self.tr("Serbia", "Political View"),
    #         "SUR": self.tr("Suriname", "Political View"),
    #         "SYR": self.tr("Syria", "Political View"),
    #         "TUR": self.tr("Turkey", "Political View"),
    #         "TZA": self.tr("Tanzania", "Political View"),
    #         "URY": self.tr("Uruguay", "Political View"),
    #         "VNM": self.tr("Vietnam", "Political View"),
    #     }
    #
    #     for code, name in views.items():
    #         item = QStandardItem(name)
    #         item.setData(code, CasaGeoToolsMainDialog.IdentifierRole)
    #         model.appendRow(item)
    #
    #     model.sort(0)
    #
    #     item = QStandardItem(self.tr("Default", "Political View"))
    #     item.setData("", CasaGeoToolsMainDialog.IdentifierRole)
    #     model.insertRow(0, item)
    #
    #     return model

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

from typing import TYPE_CHECKING, LiteralString

from qgis.PyQt.QtCore import QCoreApplication, pyqtSlot
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget

from .models import CasaGeoToolsPoliticalViewModel, CasaGeoToolsUnitSystemModel
from .ui.SettingsWidget import Ui_CasaGeoToolsSettingsWidget

if TYPE_CHECKING:
    from .plugin import CasaGeoToolsPlugin


class CasaGeoToolsSettingsWidget(QWidget):
    def __init__(self, plugin: "CasaGeoToolsPlugin", parent: QWidget | None = None):
        super().__init__(parent)
        self.plugin = plugin
        self.ui = Ui_CasaGeoToolsSettingsWidget()
        self.ui.setupUi(self)

        self.unit_system_model = CasaGeoToolsUnitSystemModel()
        self.ui.unitspref_comboBox.setModel(self.unit_system_model)

        self.political_views_model = CasaGeoToolsPoliticalViewModel()
        self.ui.politicalpref_comboBox.setModel(self.political_views_model)

        self.loadSettings()

    @pyqtSlot()
    def loadSettings(self):
        self.ui.apikey_lineEdit.setText(self.plugin.setting_apikey.value())
        # self.ui.languagepref_lineEdit.setText(self.plugin.setting_output_language.value())
        # self.ui.unitspref_comboBox.setCurrentText(self.plugin.setting_unit_system.value())
        # self.ui.politicalpref_comboBox.setCurrentText(self.plugin.setting_political_view.value())

    @pyqtSlot()
    def applySettings(self):
        self.plugin.setting_apikey.setValue(self.ui.apikey_lineEdit.text())
        # self.plugin.setting_output_language.setValue(
        #     self.ui.languagepref_lineEdit.text()
        # )
        # self.plugin.setting_unit_system.setValue(
        #     self.ui.unitspref_comboBox.currentText()
        # )
        # self.plugin.setting_political_view.setValue(
        #     self.ui.politicalpref_comboBox.currentText()
        # )

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


class CasaGeoToolsSettingsDialog(QDialog):
    def __init__(self, plugin: "CasaGeoToolsPlugin", parent: QWidget | None = None):
        super().__init__(parent)
        self.plugin = plugin

        self.setObjectName("CasaGeoToolsSettingsDialog")
        self.resize(400, 300)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setObjectName("verticalLayout")
        self.settingsWidget = CasaGeoToolsSettingsWidget(self.plugin, self)
        self.verticalLayout.addWidget(self.settingsWidget)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.accepted.connect(self.settingsWidget.applySettings)

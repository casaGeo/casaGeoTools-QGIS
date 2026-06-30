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

from typing import TYPE_CHECKING

from qgis.PyQt.QtCore import Qt, pyqtSlot
from qgis.PyQt.QtWidgets import QDialog, QWidget

from .models import CasaGeoToolsPoliticalViewModel, CasaGeoToolsUnitSystemModel
from .ui.SettingsDialog import Ui_CasaGeoToolsSettingsDialog

if TYPE_CHECKING:
    from .plugin import CasaGeoToolsPlugin


class CasaGeoToolsSettingsDialog(QDialog):
    def __init__(
        self,
        plugin: "CasaGeoToolsPlugin",
        parent: QWidget | None = None,
        flags: Qt.WindowFlags = Qt.WindowFlags(),
    ) -> None:
        super().__init__(parent, flags)
        self._plugin = plugin
        self._ui = Ui_CasaGeoToolsSettingsDialog()
        self._unit_system_model = CasaGeoToolsUnitSystemModel()
        self._political_views_model = CasaGeoToolsPoliticalViewModel()

        self.setWindowIcon(self._plugin.icon)
        self._ui.setupUi(self)
        self._ui.unitsPrefComboBox.setModel(self._unit_system_model)
        self._ui.politicalPrefComboBox.setModel(self._political_views_model)

        self.loadSettings()
        self.accepted.connect(self.saveSettings)

    @pyqtSlot()
    def loadSettings(self) -> None:
        self._ui.apikeyLineEdit.setText(self._plugin.settingApikey.value())
        self._ui.languagePrefLineEdit.setText(self._plugin.settingLanguage.value())
        self._ui.unitsPrefComboBox.setCurrentIndex(
            self._ui.unitsPrefComboBox.findData(self._plugin.settingUnitSystem.value())
        )
        self._ui.politicalPrefComboBox.setCurrentIndex(
            self._ui.politicalPrefComboBox.findData(
                self._plugin.settingPoliticalView.value()
            )
        )

    @pyqtSlot()
    def saveSettings(self) -> None:
        self._plugin.settingApikey.setValue(self._ui.apikeyLineEdit.text())
        self._plugin.settingLanguage.setValue(self._ui.languagePrefLineEdit.text())
        self._plugin.settingUnitSystem.setValue(
            self._ui.unitsPrefComboBox.currentData()
        )
        self._plugin.settingPoliticalView.setValue(
            self._ui.politicalPrefComboBox.currentData()
        )

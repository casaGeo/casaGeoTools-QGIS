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

from typing import TYPE_CHECKING, override

from qgis.gui import (
    QgsOptionsDialogHighlightLabel,
    QgsOptionsPageWidget,
    QgsOptionsWidgetFactory,
)
from qgis.PyQt.QtWidgets import QWidget

from .models import CasaGeoToolsPoliticalViewModel, CasaGeoToolsUnitSystemModel
from .ui.OptionsPage import Ui_CasaGeoToolsOptionsPage
from .utils import TrMethod

if TYPE_CHECKING:
    from .plugin import CasaGeoToolsPlugin


class CasaGeoToolsOptionsPage(QgsOptionsPageWidget):
    def __init__(
        self,
        plugin: "CasaGeoToolsPlugin",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._plugin = plugin
        self._ui = Ui_CasaGeoToolsOptionsPage()
        self._unit_system_model = CasaGeoToolsUnitSystemModel()
        self._political_views_model = CasaGeoToolsPoliticalViewModel()

        self._ui.setupUi(self)
        self._ui.unitsPrefComboBox.setModel(self._unit_system_model)
        self._ui.politicalPrefComboBox.setModel(self._political_views_model)

        self._highlighters = [
            QgsOptionsDialogHighlightLabel(self._ui.apikeyLabel),
            QgsOptionsDialogHighlightLabel(self._ui.languagePrefLabel),
            QgsOptionsDialogHighlightLabel(self._ui.unitsPrefLabel),
            QgsOptionsDialogHighlightLabel(self._ui.politicalPrefLabel),
        ]

        for highlighter in self._highlighters:
            self.registerHighlightWidget(highlighter)

        self.loadSettings()

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

    @override
    def apply(self) -> None:
        self._plugin.settingApikey.setValue(self._ui.apikeyLineEdit.text())
        self._plugin.settingLanguage.setValue(self._ui.languagePrefLineEdit.text())
        self._plugin.settingUnitSystem.setValue(
            self._ui.unitsPrefComboBox.currentData()
        )
        self._plugin.settingPoliticalView.setValue(
            self._ui.politicalPrefComboBox.currentData()
        )

    # We would like to implement helpKey(), but that system doesn’t
    # appear to be working for QGIS 4.0 yet, which makes it hard to
    # figure out how to use it correctly.


class CasaGeoToolsOptionsWidgetFactory(QgsOptionsWidgetFactory):
    __tr = TrMethod()

    def __init__(self, plugin: "CasaGeoToolsPlugin"):
        super().__init__(plugin.name, plugin.icon, plugin.identifier)
        self._plugin = plugin

    @override
    def createWidget(self, parent: QWidget | None = None) -> CasaGeoToolsOptionsPage:
        return CasaGeoToolsOptionsPage(self._plugin, parent)

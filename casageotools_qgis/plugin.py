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

from functools import cached_property
from typing import LiteralString, override

from qgis.core import QgsApplication, QgsProcessingProvider
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QLocale,
    QTranslator,
)
from qgis.PyQt.QtGui import (
    QAction,
    QDesktopServices,
    QIcon,
)

from . import resources
from .maindialog import CasaGeoToolsMainDialog
from .resources import PLUGIN_I18N_DIRECTORY, PLUGIN_IDENTIFIER

# class CasaGeoToolsPluginTranslationComponent:
#     translator: QTranslator
#
#     def __init__(self, plugin: "CasaGeoToolsPlugin") -> None:
#         self.plugin = plugin
#         self.plugin.components.append(self)
#
#     def initialize(self) -> None:
#         self.translator = QTranslator()
#         if self.translator.load(QLocale(), "casageotools_qgis", ".", R("i18n")):
#             QCoreApplication.installTranslator(self.translator)
#
#     def finalize(self) -> None:
#         QCoreApplication.removeTranslator(self.translator)


class CasaGeoToolsPlugin:
    def __init__(self, iface: QgisInterface) -> None:
        self.iface = iface

    @cached_property
    def translator(self) -> QTranslator:
        return QTranslator()

    @cached_property
    def icon(self) -> QIcon:
        return resources.casageotools_icon()

    @cached_property
    def dialog(self) -> CasaGeoToolsMainDialog:
        return CasaGeoToolsMainDialog()

    @cached_property
    def processing_provider(self) -> "CasaGeoToolsProcessingProvider":
        return CasaGeoToolsProcessingProvider()

    @cached_property
    def plugin_action(self) -> QAction:
        action = QAction(self.icon, self.__tr("casaGeoTools"))
        action.triggered.connect(self.dialog.show)
        return action

    @cached_property
    def help_action(self) -> QAction:
        action = QAction(self.icon, self.__tr("casaGeoTools Documentation"))
        action.triggered.connect(self.show_help)
        return action

    def initGui(self) -> None:
        """Called when the plugin is loaded."""

        if self.translator.load(
            QLocale(), PLUGIN_IDENTIFIER, ".", PLUGIN_I18N_DIRECTORY
        ):
            QCoreApplication.installTranslator(self.translator)

        self.iface.addToolBarIcon(self.plugin_action)
        self.iface.addPluginToMenu("&casaGeoTools", self.plugin_action)
        self.iface.addPluginToVectorMenu("&casaGeoTools", self.plugin_action)

        if menu := self.iface.pluginHelpMenu():
            menu.addAction(self.help_action)

        if registry := QgsApplication.processingRegistry():
            registry.addProvider(self.processing_provider)

    def unload(self) -> None:
        """Called when the plugin is unloaded."""

        if registry := QgsApplication.processingRegistry():
            registry.removeProvider(self.processing_provider)

        if menu := self.iface.pluginHelpMenu():
            menu.removeAction(self.help_action)

        self.iface.removeToolBarIcon(self.plugin_action)
        self.iface.removePluginMenu("&casaGeoTools", self.plugin_action)
        self.iface.removePluginVectorMenu("&casaGeoTools", self.plugin_action)

        QCoreApplication.removeTranslator(self.translator)

    @staticmethod
    def show_help() -> None:
        """Show the plugin documentation."""
        # We would like to use qgis.utils.showPluginHelp(), but that
        # function is currently broken because it passes a path with
        # file:// prefix to QUrl.fromLocalFile().
        QDesktopServices.openUrl(resources.help_url())

    # def initProcessing(self):
    #     """Init Processing provider for QGIS >= 3.8."""
    #     self.provider = CasaGeoToolsProcessingProvider()
    #     QgsApplication.processingRegistry().addProvider(self.provider)

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


class CasaGeoToolsProcessingProvider(QgsProcessingProvider):
    @override
    def id(self):
        return "casageotools"

    @override
    def name(self):
        return self.__tr("casaGeoTools")

    @override
    def icon(self):
        return resources.casageotools_icon()

    @override
    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        from .coder import CasaGeoToolsPOISearchAlgorithm
        from .spatial import CasaGeoToolsIsolinesAlgorithm

        self.addAlgorithm(CasaGeoToolsPOISearchAlgorithm())
        self.addAlgorithm(CasaGeoToolsIsolinesAlgorithm())

    # @override
    # def longName(self):
    #     return self.__tr("casaGeoTools for QGIS (version {version})").format(
    #         version=self.versionInfo(),
    #     )
    #
    # @override
    # def versionInfo(self):
    #     return resources.plugin_version()

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

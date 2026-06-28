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
from typing import TYPE_CHECKING, LiteralString, override

from qgis.core import (
    QgsApplication,
    QgsProcessingProvider,
    QgsSettingsEntryString,
    QgsSettingsTree,
)
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
from .resources import PLUGIN_I18N_DIRECTORY, PLUGIN_IDENTIFIER

if TYPE_CHECKING:
    from .maindialog import CasaGeoToolsMainDialog


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


# def component(func):
#     def wrapper(self, *args, **kwargs):
#         g = func(self, *args, **kwargs)
#         v = g.send(None)
#         self._component_generators.append(g)
#         return v
#


def ensure[T](value: T | None) -> T:
    assert value is not None
    return value


class CasaGeoToolsPlugin:
    def __init__(self, iface: QgisInterface) -> None:
        self.iface = iface

    @cached_property
    def icon(self) -> QIcon:
        return resources.casageotools_icon()

    @cached_property
    def action_main(self) -> QAction:
        action = QAction(self.icon, self.__tr("casaGeoTools"))
        action.triggered.connect(self.dialog_main.show)
        return action

    @cached_property
    def action_help(self) -> QAction:
        action = QAction(self.icon, self.__tr("casaGeoTools Documentation"))
        action.triggered.connect(self.show_help)
        return action

    @cached_property
    def dialog_main(self) -> "CasaGeoToolsMainDialog":
        from .maindialog import CasaGeoToolsMainDialog

        return CasaGeoToolsMainDialog()

    @cached_property
    def settings(self):
        return ensure(QgsSettingsTree.createPluginTreeNode(PLUGIN_IDENTIFIER))

    @cached_property
    def setting_apikey(self):
        return QgsSettingsEntryString(
            "apikey",
            PLUGIN_IDENTIFIER,
            description=self.__tr("Your casaGeo API Key"),
            maxLength=64,
        )

    @cached_property
    def translator(self) -> QTranslator:
        return QTranslator()

    @cached_property
    def processing_provider(self) -> "CasaGeoToolsProcessingProvider":
        return CasaGeoToolsProcessingProvider(self)

    def initGui(self) -> None:
        """Called when the plugin is loaded."""

        if self.translator.load(
            QLocale(), PLUGIN_IDENTIFIER, ".", PLUGIN_I18N_DIRECTORY
        ):
            QCoreApplication.installTranslator(self.translator)

        # The settings tree system is kind of unintuitive and/or buggy
        # regarding the registration of child settings. What seems to
        # work is creating the child setting with the PLUGIN_IDENTIFIER
        # and then manually registering it afterward (even though it
        # should register itself automatically).
        self.settings.registerChildSetting(self.setting_apikey, None)

        self.iface.addToolBarIcon(self.action_main)
        self.iface.addPluginToMenu("&casaGeoTools", self.action_main)
        self.iface.addPluginToVectorMenu("&casaGeoTools", self.action_main)

        if pluginHelpMenu := self.iface.pluginHelpMenu():
            pluginHelpMenu.addAction(self.action_help)

        if processingRegistry := QgsApplication.processingRegistry():
            processingRegistry.addProvider(self.processing_provider)

    def unload(self) -> None:
        """Called when the plugin is unloaded."""

        if processingRegistry := QgsApplication.processingRegistry():
            processingRegistry.removeProvider(self.processing_provider)

        if pluginHelpMenu := self.iface.pluginHelpMenu():
            pluginHelpMenu.removeAction(self.action_help)

        self.iface.removeToolBarIcon(self.action_main)
        self.iface.removePluginMenu("&casaGeoTools", self.action_main)
        self.iface.removePluginVectorMenu("&casaGeoTools", self.action_main)

        QgsSettingsTree.unregisterPluginTreeNode(PLUGIN_IDENTIFIER)

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
    def __init__(self, plugin: CasaGeoToolsPlugin):
        super().__init__()
        self.plugin = plugin

    @override
    def id(self):
        return PLUGIN_IDENTIFIER

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
        from .coder import (
            # CasaGeoToolsAddressSearchAlgorithm,
            CasaGeoToolsPOISearchAlgorithm,
        )
        from .spatial import CasaGeoToolsIsolinesAlgorithm

        # self.addAlgorithm(CasaGeoToolsAddressSearchAlgorithm(self.plugin))
        self.addAlgorithm(CasaGeoToolsPOISearchAlgorithm(self.plugin))
        self.addAlgorithm(CasaGeoToolsIsolinesAlgorithm(self.plugin))

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

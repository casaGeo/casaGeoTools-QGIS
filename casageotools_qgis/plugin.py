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

import os
from functools import cached_property
from typing import TYPE_CHECKING

from qgis.core import (
    QgsApplication,
    QgsSettingsEntryString,
    QgsSettingsTree,
    QgsSettingsTreeNode,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QLocale,
    QTranslator,
    QUrl,
)
from qgis.PyQt.QtGui import (
    QAction,
    QDesktopServices,
    QIcon,
)

from .resources import (
    PLUGIN_ASSETS_DIRECTORY,
    PLUGIN_HELP_DIRECTORY,
    PLUGIN_I18N_DIRECTORY,
    PLUGIN_IDENTIFIER,
)
from .utils import TrMethod, ensure

if TYPE_CHECKING:
    from .options import CasaGeoToolsOptionsWidgetFactory
    from .processing import CasaGeoToolsProcessingProvider


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


class CasaGeoToolsPlugin:
    __tr = TrMethod()

    identifier = PLUGIN_IDENTIFIER

    @property
    def name(self) -> str:
        return self.__tr("casaGeoTools", "Plugin name")

    @cached_property
    def icon(self) -> QIcon:
        return QIcon(os.path.join(PLUGIN_ASSETS_DIRECTORY, "casageotools.png"))

    @cached_property
    def actionSettings(self) -> QAction:
        action = QAction(
            self.icon, self.__tr("casaGeoTools Settings", "Settings action")
        )
        action.triggered.connect(self.showSettingsDialog)
        return action

    @cached_property
    def actionHelp(self) -> QAction:
        action = QAction(
            self.icon, self.__tr("casaGeoTools Documentation", "Help action")
        )
        action.setStatusTip(
            self.__tr(
                "Open casaGeoTools plugin documentation in the browser", "Help action"
            )
        )
        action.triggered.connect(self.showHelp)
        return action

    @cached_property
    def settings(self) -> QgsSettingsTreeNode:
        return ensure(QgsSettingsTree.createPluginTreeNode(PLUGIN_IDENTIFIER))

    @cached_property
    def settingApikey(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "apikey",
            PLUGIN_IDENTIFIER,
            description=self.__tr("Your casaGeo API Key"),
            maxLength=64,
        )

    @cached_property
    def settingLanguage(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "language",
            PLUGIN_IDENTIFIER,
            description=self.__tr("Preferred output language"),
            maxLength=64,
        )

    @cached_property
    def settingUnitSystem(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "unitSystem",
            PLUGIN_IDENTIFIER,
            description=self.__tr("Preferred unit system"),
        )

    @cached_property
    def settingPoliticalView(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "politicalView",
            PLUGIN_IDENTIFIER,
            description=self.__tr("Preferred political view"),
            maxLength=64,
        )

    def __init__(self, iface: QgisInterface) -> None:
        self.iface = iface
        self.translator = QTranslator()
        self.processing_provider: CasaGeoToolsProcessingProvider | None = None
        self.options_widget_factory: CasaGeoToolsOptionsWidgetFactory | None = None
        self.is_processing_initialized = False
        self.is_fully_initialized = False

        # self._main_dialog: CasaGeoToolsMainDialog | None = None

        if self.translator.load(
            QLocale(), PLUGIN_IDENTIFIER, ".", PLUGIN_I18N_DIRECTORY
        ):
            QCoreApplication.installTranslator(self.translator)

        # The settings tree system is kind of unintuitive and/or buggy
        # regarding the registration of child settings. What seems to
        # work is creating the child setting with the PLUGIN_IDENTIFIER
        # and then manually registering it afterward (even though it
        # should register itself automatically).
        self.settings.registerChildSetting(self.settingApikey, None)
        self.settings.registerChildSetting(self.settingLanguage, None)
        self.settings.registerChildSetting(self.settingUnitSystem, None)
        self.settings.registerChildSetting(self.settingPoliticalView, None)

    def initProcessing(self) -> None:
        """
        Initialize only the processing components of this plugin.

        QGIS calls this function instead of :meth:`initGui` when the
        plugin is loaded in processing-only mode.
        """
        from .processing import CasaGeoToolsProcessingProvider

        self.processing_provider = CasaGeoToolsProcessingProvider(self)
        if processingRegistry := QgsApplication.processingRegistry():
            processingRegistry.addProvider(self.processing_provider)

        self.is_processing_initialized = True

    def initGui(self) -> None:
        """
        Initialize all components of this plugin.

        This is the main entry point of the plugin, which initializes
        all graphical and processing components.
        """
        from .options import CasaGeoToolsOptionsWidgetFactory

        self.initProcessing()

        # self.iface.addToolBarIcon(self.actionSettings)
        # self.iface.addPluginToMenu("&casaGeoTools", self.actionSettings)
        # self.iface.addPluginToVectorMenu("&casaGeoTools", self.actionSettings)

        if pluginHelpMenu := self.iface.pluginHelpMenu():
            pluginHelpMenu.addAction(self.actionHelp)

        self.options_widget_factory = CasaGeoToolsOptionsWidgetFactory(self)
        self.iface.registerOptionsWidgetFactory(self.options_widget_factory)

        self.is_fully_initialized = True

    def unloadGui(self) -> None:
        """Unload the graphical components of this plugin."""

        # self.iface.removeToolBarIcon(self.actionSettings)
        # self.iface.removePluginMenu("&casaGeoTools", self.actionSettings)
        # self.iface.removePluginVectorMenu("&casaGeoTools", self.actionSettings)

        if pluginHelpMenu := self.iface.pluginHelpMenu():
            pluginHelpMenu.removeAction(self.actionHelp)

        self.iface.unregisterOptionsWidgetFactory(self.options_widget_factory)

    def unloadProcessing(self) -> None:
        """Unload the processing components of this plugin."""

        if processingRegistry := QgsApplication.processingRegistry():
            processingRegistry.removeProvider(self.processing_provider)

    def unload(self) -> None:
        """
        Unload all loaded components of this plugin.

        QGIS calls this function when the plugin is unloaded, whether it
        was loaded in graphical or processing-only mode.
        """

        if self.is_fully_initialized:
            self.unloadGui()

        if self.is_processing_initialized:
            self.unloadProcessing()

        QgsSettingsTree.unregisterPluginTreeNode(PLUGIN_IDENTIFIER)
        QCoreApplication.removeTranslator(self.translator)

    def helpFile(self, path: str = "index.html") -> str:
        return os.path.join(PLUGIN_HELP_DIRECTORY, path)

    def helpUrl(self, path: str = "index.html") -> QUrl:
        return QUrl.fromLocalFile(self.helpFile(path))

    # def showMainDialog(self) -> None:
    #     """Show the main dialog."""
    #     from .maindialog import CasaGeoToolsMainDialog
    #
    #     if self._main_dialog is None:
    #         dialog = CasaGeoToolsMainDialog(self.iface.mainWindow())
    #         dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    #         dialog.destroyed.connect(lambda: setattr(self, "_main_dialog", None))
    #         self._main_dialog = dialog
    #
    #     # self._main_dialog.open()
    #     self._main_dialog.show()
    #     self._main_dialog.activateWindow()
    #     # self._main_dialog.raise_()

    def showSettingsDialog(self) -> None:
        """Show the plugin settings dialog."""
        self.iface.showOptionsDialog(self.iface.mainWindow(), self.identifier)

    def showHelp(self) -> None:
        """Show the plugin documentation."""
        # We would like to use qgis.utils.showPluginHelp(), but that
        # function is currently broken because it passes a path with
        # file:// prefix to QUrl.fromLocalFile().
        QDesktopServices.openUrl(self.helpUrl())

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
    Qt,
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
    from .maindialog import CasaGeoToolsMainDialog
    from .processing import CasaGeoToolsProcessingProvider
    from .settingsdialog import CasaGeoToolsSettingsDialog


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

    @cached_property
    def icon(self) -> QIcon:
        return QIcon(os.path.join(PLUGIN_ASSETS_DIRECTORY, "casageotools.png"))

    @cached_property
    def action_main(self) -> QAction:
        action = QAction(self.icon, self.__tr("casaGeoTools"))
        action.triggered.connect(self.show_settings_dialog)
        # action.triggered.connect(self.dialog_main.show)
        return action

    @cached_property
    def action_help(self) -> QAction:
        action = QAction(self.icon, self.__tr("casaGeoTools Documentation"))
        action.triggered.connect(self.show_help)
        return action

    @cached_property
    def settings(self) -> QgsSettingsTreeNode:
        return ensure(QgsSettingsTree.createPluginTreeNode(PLUGIN_IDENTIFIER))

    @cached_property
    def setting_apikey(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "apikey",
            PLUGIN_IDENTIFIER,
            description=self.__tr("Your casaGeo API Key"),
            maxLength=64,
        )

    @cached_property
    def setting_language(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "language",
            PLUGIN_IDENTIFIER,
            description=self.__tr("Preferred output language"),
            maxLength=64,
        )

    @cached_property
    def setting_unit_system(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "unitSystem",
            PLUGIN_IDENTIFIER,
            description=self.__tr("Preferred unit system"),
        )

    @cached_property
    def setting_political_view(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "politicalView",
            PLUGIN_IDENTIFIER,
            description=self.__tr("Preferred political view"),
            maxLength=64,
        )

    def __init__(self, iface: QgisInterface) -> None:
        self.iface = iface
        self.translator: QTranslator = QTranslator()
        self.processing_provider: CasaGeoToolsProcessingProvider | None = None
        self.is_processing_initialized = False
        self.is_fully_initialized = False

        self._main_dialog: CasaGeoToolsMainDialog | None = None
        self._settings_dialog: CasaGeoToolsSettingsDialog | None = None

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
        self.settings.registerChildSetting(self.setting_language, None)
        self.settings.registerChildSetting(self.setting_unit_system, None)
        self.settings.registerChildSetting(self.setting_political_view, None)

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
        self.initProcessing()

        self.iface.addToolBarIcon(self.action_main)
        self.iface.addPluginToMenu("&casaGeoTools", self.action_main)
        self.iface.addPluginToVectorMenu("&casaGeoTools", self.action_main)

        if pluginHelpMenu := self.iface.pluginHelpMenu():
            pluginHelpMenu.addAction(self.action_help)

        self.is_fully_initialized = True

    def unloadGui(self) -> None:
        """Unload the graphical components of this plugin."""

        self.iface.removeToolBarIcon(self.action_main)
        self.iface.removePluginMenu("&casaGeoTools", self.action_main)
        self.iface.removePluginVectorMenu("&casaGeoTools", self.action_main)

        if pluginHelpMenu := self.iface.pluginHelpMenu():
            pluginHelpMenu.removeAction(self.action_help)

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

    def help_file(self, path: str = "index.html") -> str:
        return os.path.join(PLUGIN_HELP_DIRECTORY, path)

    def help_url(self, path: str = "index.html") -> QUrl:
        return QUrl.fromLocalFile(self.help_file(path))

    def show_main_dialog(self) -> None:
        """Show the main dialog."""
        from .maindialog import CasaGeoToolsMainDialog

        if self._main_dialog is None:
            dialog = CasaGeoToolsMainDialog()
            dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dialog.destroyed.connect(lambda: setattr(self, "_main_dialog", None))
            self._main_dialog = dialog

        self._main_dialog.open()

    def show_settings_dialog(self) -> None:
        """Show the plugin settings dialog."""
        from .settingsdialog import CasaGeoToolsSettingsDialog

        if self._settings_dialog is None:
            dialog = CasaGeoToolsSettingsDialog(self, self.iface.mainWindow())
            dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dialog.destroyed.connect(lambda: setattr(self, "_settings_dialog", None))
            self._settings_dialog = dialog

        # self._settings_dialog.open()
        self._settings_dialog.show()
        self._settings_dialog.activateWindow()
        # self._settings_dialog.raise_()

    def show_help(self) -> None:
        """Show the plugin documentation."""
        # We would like to use qgis.utils.showPluginHelp(), but that
        # function is currently broken because it passes a path with
        # file:// prefix to QUrl.fromLocalFile().
        QDesktopServices.openUrl(self.help_url())

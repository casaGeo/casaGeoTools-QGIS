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
    Qgis,
    QgsApplication,
    QgsFeedback,
    QgsMessageLog,
    QgsSettingsEntryString,
    QgsSettingsTree,
    QgsSettingsTreeNode,
    QgsTask,
)
from qgis.gui import (
    QgisInterface,
    QgsMessageBar,
)
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
    PLUGIN_DIRECTORY,
    PLUGIN_HELP_DIRECTORY,
    PLUGIN_I18N_DIRECTORY,
    PLUGIN_IDENTIFIER,
)
from .utils import (
    CasaGeoToolsCoderTranslator,
    CasaGeoToolsSpatialTranslator,
    TrMethod,
    ensure,
)

if TYPE_CHECKING:
    from casageo.tools import CasaGeoClient

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

    translator: QTranslator
    processing_provider: "CasaGeoToolsProcessingProvider"
    options_widget_factory: "CasaGeoToolsOptionsWidgetFactory"

    plugin_menu_name: str
    vector_menu_name: str
    plugin_menu_entries: list[QAction]
    vector_menu_entries: list[QAction]
    plugin_help_menu_entries: list[QAction]

    identifier = PLUGIN_IDENTIFIER
    directory = PLUGIN_DIRECTORY
    assets_directory = PLUGIN_ASSETS_DIRECTORY
    help_directory = PLUGIN_HELP_DIRECTORY
    i18n_directory = PLUGIN_I18N_DIRECTORY

    __install_python_dependencies_task: QgsTask | None = None

    @cached_property
    def name(self) -> str:
        return self.__tr("casaGeoTools", "Plugin name")

    @cached_property
    def icon(self) -> QIcon:
        return QIcon(os.path.join(self.assets_directory, "casageotools.png"))

    @cached_property
    def coderTranslator(self) -> CasaGeoToolsCoderTranslator:
        return CasaGeoToolsCoderTranslator(self)

    @cached_property
    def spatialTranslator(self) -> CasaGeoToolsSpatialTranslator:
        return CasaGeoToolsSpatialTranslator(self)

    # Settings

    @cached_property
    def settings(self) -> QgsSettingsTreeNode:
        return ensure(QgsSettingsTree.createPluginTreeNode(self.identifier))

    @cached_property
    def settingApikey(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "apikey",
            self.identifier,
            description=self.__tr("Your casaGeo API Key"),
            maxLength=64,
        )

    @cached_property
    def settingLanguage(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "language",
            self.identifier,
            description=self.__tr("Preferred output language"),
            maxLength=64,
        )

    @cached_property
    def settingUnitSystem(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "unitSystem",
            self.identifier,
            description=self.__tr("Preferred unit system"),
        )

    @cached_property
    def settingPoliticalView(self) -> QgsSettingsEntryString:
        return QgsSettingsEntryString(
            "politicalView",
            self.identifier,
            description=self.__tr("Preferred political view"),
            maxLength=64,
        )

    # Primary Interface

    def __init__(self, iface: QgisInterface) -> None:
        self.iface = iface
        self.is_processing_initialized = False
        self.is_fully_initialized = False

        self.translator = QTranslator()
        if self.translator.load(QLocale(), self.identifier, ".", self.i18n_directory):
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

        self.options_widget_factory = CasaGeoToolsOptionsWidgetFactory(self)

        self.plugin_menu_name = self.__tr("&casaGeoTools", "Plugin menu")
        self.plugin_menu_entries = [
            self.showSettingsAction,
            self.installPythonDependenciesAction,
        ]

        self.vector_menu_name = self.__tr("&casaGeoTools", "Vector menu")
        self.vector_menu_entries = []

        self.plugin_help_menu_entries = [
            self.showDocumentationAction,
        ]

        self.iface.registerOptionsWidgetFactory(self.options_widget_factory)

        for entry in self.plugin_menu_entries:
            self.iface.addPluginToMenu(self.plugin_menu_name, entry)

        for entry in self.vector_menu_entries:
            self.iface.addPluginToVectorMenu(self.vector_menu_name, entry)

        if pluginHelpMenu := self.iface.pluginHelpMenu():
            for entry in self.plugin_help_menu_entries:
                pluginHelpMenu.addAction(entry)

        self.is_fully_initialized = True

    def unloadGui(self) -> None:
        """Unload the graphical components of this plugin."""

        self.iface.unregisterOptionsWidgetFactory(self.options_widget_factory)

        for entry in self.plugin_menu_entries:
            self.iface.removePluginMenu(self.plugin_menu_name, entry)

        for entry in self.vector_menu_entries:
            self.iface.removePluginVectorMenu(self.vector_menu_name, entry)

        if pluginHelpMenu := self.iface.pluginHelpMenu():
            for entry in self.plugin_help_menu_entries:
                pluginHelpMenu.removeAction(entry)

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

        QgsSettingsTree.unregisterPluginTreeNode(self.identifier)
        QCoreApplication.removeTranslator(self.translator)

    # Secondary Interface

    def casaGeoClient(self, feedback: QgsFeedback | None = None) -> "CasaGeoClient":
        from .utilscg import CasaGeoToolsQgisEnabledCasaGeoClient

        return CasaGeoToolsQgisEnabledCasaGeoClient(
            self.settingApikey.value(),
            preferred_language=self.settingLanguage.value() or None,
            preferred_unit_system=self.settingUnitSystem.value() or None,
            preferred_political_view=self.settingPoliticalView.value() or None,
            qgis_feedback=feedback,
        )

    def helpFile(self, path: str = "index.html") -> str:
        return os.path.join(self.help_directory, path)

    def helpUrl(self, path: str = "index.html", fragment: str | None = None) -> QUrl:
        url = QUrl.fromLocalFile(self.helpFile(path))
        url.setFragment(fragment)
        return url

    def requirementsFile(self) -> str:
        return os.path.join(self.directory, "requirements.txt")

    # Actions

    @cached_property
    def installPythonDependenciesAction(self) -> QAction:
        action = QAction(
            self.icon,
            self.__tr(
                "Install Python dependencies...",
                "Install Python dependencies action",
            ),
        )
        action.triggered.connect(self.installPythonDependencies)
        return action

    def installPythonDependencies(self) -> None:
        from casageotools_qgis.install import CasaGeoToolsInstallRequirementsTask

        info_title = ""
        info_text = self.__tr(
            "Dependencies for {plugin} are currently being installed. Please wait...",
            "Message bar text",
        ).format(plugin=self.identifier)
        info_level = Qgis.MessageLevel.Info

        def onRunning():
            messageBar: QgsMessageBar = ensure(self.iface.messageBar())
            messageBar.pushMessage(
                title=info_title,
                text=info_text,
                level=info_level,
            )

        def onFinish(*, successful: bool):
            self.__install_python_dependencies_task = None
            messageBar: QgsMessageBar = ensure(self.iface.messageBar())

            # Dismiss the progress message(s) so they don't stack behind
            # the success message and reappear once it is dismissed.
            for item in messageBar.items():
                if (
                    item.level() == info_level
                    and item.title() == info_title
                    and item.text() == info_text
                ):
                    item.dismiss()

            if successful:
                messageBar.pushMessage(
                    self.__tr("Installation Successful", "Message bar title"),
                    self.__tr(
                        "Dependencies for {plugin} are now installed. Please restart QGIS for the changes to take effect.",
                        "Message bar text",
                    ).format(plugin=self.identifier),
                    level=Qgis.MessageLevel.Success,
                    duration=0,
                )
            else:
                messageBar.pushMessage(
                    self.__tr("Installation Failed", "Message bar title"),
                    self.__tr(
                        "Dependencies for {plugin} could not be installed. Please check the Log Messages panel.",
                        "Message bar text",
                    ).format(plugin=self.identifier),
                    level=Qgis.MessageLevel.Critical,
                    duration=0,
                )

        if self.__install_python_dependencies_task:
            onRunning()
            return

        task = CasaGeoToolsInstallRequirementsTask(self.requirementsFile())
        task.begun.connect(onRunning)
        task.taskCompleted.connect(lambda: onFinish(successful=True))
        task.taskTerminated.connect(lambda: onFinish(successful=False))

        # IMPORTANT: The ownership transfer from Python to C++ in
        # QgsTaskManager::addTask() appears to be broken; we have to
        # keep a reference to the QgsTask object around, or it will be
        # cancelled and deleted as soon as it goes out of scope.

        if ensure(QgsApplication.taskManager()).addTask(task):
            self.__install_python_dependencies_task = task
        else:
            QgsMessageLog.logMessage(
                "Failed to add dependency installation task to QgsApplication.taskManager()",
                tag=self.identifier,
                level=Qgis.MessageLevel.Critical,
            )

    @cached_property
    def showDocumentationAction(self) -> QAction:
        action = QAction(
            self.icon, self.__tr("casaGeoTools Documentation", "Documentation action")
        )
        action.setStatusTip(
            self.__tr(
                "Open casaGeoTools plugin documentation in the browser",
                "Documentation action",
            )
        )
        action.triggered.connect(self.showDocumentation)
        return action

    def showDocumentation(self) -> None:
        """Show the plugin documentation."""
        # We would like to use qgis.utils.showPluginHelp(), but that
        # function is currently broken because it passes a path with
        # file:// prefix to QUrl.fromLocalFile().
        QDesktopServices.openUrl(self.helpUrl())

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

    @cached_property
    def showSettingsAction(self) -> QAction:
        action = QAction(
            self.icon, self.__tr("casaGeoTools Settings", "Settings action")
        )
        action.triggered.connect(self.showSettings)
        return action

    def showSettings(self) -> None:
        """Show the plugin settings dialog."""
        self.iface.showOptionsDialog(self.iface.mainWindow(), self.identifier)

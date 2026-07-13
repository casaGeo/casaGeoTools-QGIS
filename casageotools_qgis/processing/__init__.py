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

from typing import TYPE_CHECKING, Any, Self, override

from qgis.core import QgsProcessingAlgorithm, QgsProcessingProvider

from ..utils import TrMethod

if TYPE_CHECKING:
    from casageo.tools import CasaGeoClient
    from qgis.PyQt.QtGui import QIcon

    from ..plugin import CasaGeoToolsPlugin


class CasaGeoToolsProcessingProvider(QgsProcessingProvider):
    __tr = TrMethod()

    def __init__(self, plugin: "CasaGeoToolsPlugin") -> None:
        super().__init__()
        self.plugin = plugin

    @override
    def id(self) -> str:
        return self.plugin.identifier

    @override
    def name(self) -> str:
        return self.plugin.name

    @override
    def icon(self) -> "QIcon":
        return self.plugin.icon

    @override
    def loadAlgorithms(self) -> None:
        from .coder import (
            CasaGeoToolsAddressSearchAlgorithm,
            CasaGeoToolsPOISearchAlgorithm,
        )
        from .spatial import (
            CasaGeoToolsIsolinesAlgorithm,
            CasaGeoToolsRoutesSingleAlgorithm,
        )

        self.addAlgorithm(CasaGeoToolsAddressSearchAlgorithm(self.plugin))
        self.addAlgorithm(CasaGeoToolsPOISearchAlgorithm(self.plugin))
        self.addAlgorithm(CasaGeoToolsIsolinesAlgorithm(self.plugin))
        self.addAlgorithm(CasaGeoToolsRoutesSingleAlgorithm(self.plugin))

    # @override
    # def longName(self):
    #     return self.__tr("casaGeoTools for QGIS (version {version})").format(
    #         version=self.versionInfo(),
    #     )
    #
    # @override
    # def versionInfo(self):
    #     return resources.plugin_version()


class CasaGeoToolsProcessingAlgorithm(QgsProcessingAlgorithm):
    __tr = TrMethod()

    GROUP_ID_CODER = "coder"
    GROUP_ID_SPATIAL = "spatial"

    @override
    def __init__(self, plugin: "CasaGeoToolsPlugin") -> None:
        super().__init__()
        self.plugin = plugin
        self.status_ok = True
        self.status_message = ""

    @override
    def createInstance(self) -> Self:
        return self.__class__(self.plugin)

    @override
    def canExecute(self) -> tuple[bool, str]:
        return self.status_ok, self.status_message

    @override
    def group(self) -> str:
        match self.groupId():
            case self.GROUP_ID_CODER:
                return self.__tr("Coder", "Group")
            case self.GROUP_ID_SPATIAL:
                return self.__tr("Spatial", "Group")
            case gid:
                return gid

    @override
    def helpUrl(self) -> str:
        return self.plugin.helpUrl(
            f"algorithms/{self.groupId()}/{self.name()}.html"
        ).toString()

    @override
    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        from importlib import import_module

        if configuration is None:
            configuration = {}

        try:
            import_module("casageo.tools")
            import_module("casageo.coder")
            import_module("casageo.spatial")
        except ModuleNotFoundError as err:
            self.status_ok = False
            self.status_message = self.__tr(
                "The {module} module is not installed",
            ).format(module=err.name)
            return
        except ImportError as err:
            self.status_ok = False
            self.status_message = self.__tr(
                "The {module} module could not be imported: {err}",
            ).format(module=err.name, err=err)
            return

        if not self.plugin.settingApikey.value():
            self.status_ok = False
            self.status_message = self.__tr("Please input your API key in the settings")
            return

    def casaGeoClient(self) -> "CasaGeoClient":
        from casageo.tools import CasaGeoClient

        return CasaGeoClient(
            self.plugin.settingApikey.value(),
            preferred_language=self.plugin.settingLanguage.value() or None,
            preferred_unit_system=self.plugin.settingUnitSystem.value() or None,
            preferred_political_view=self.plugin.settingPoliticalView.value() or None,
        )

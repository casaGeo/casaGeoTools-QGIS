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

from qgis.core import QgsProcessingAlgorithm, QgsProcessingProvider

from ..resources import PLUGIN_IDENTIFIER
from ..utils import TrMethod

if TYPE_CHECKING:
    from casageo.tools import CasaGeoClient

    from ..plugin import CasaGeoToolsPlugin


class CasaGeoToolsProcessingProvider(QgsProcessingProvider):
    __tr = TrMethod()

    def __init__(self, plugin: "CasaGeoToolsPlugin"):
        super().__init__()
        self.plugin = plugin

    @override
    def id(self):
        return PLUGIN_IDENTIFIER

    @override
    def name(self):
        return self.plugin.name

    @override
    def icon(self):
        return self.plugin.icon

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


class CasaGeoToolsAbstractProcessingAlgorithm(QgsProcessingAlgorithm):
    __tr = TrMethod()

    @override
    def __init__(self, plugin: "CasaGeoToolsPlugin") -> None:
        super().__init__()
        self.plugin = plugin

    @override
    def canExecute(self) -> tuple[bool, str]:
        import importlib

        for module in self.requiredPythonModules():
            try:
                importlib.import_module(module)
            except ModuleNotFoundError:
                return False, self.__tr(
                    "The {module} module is not installed",
                ).format(module=module)
            except ImportError as err:
                return False, self.__tr(
                    "The {module} module could not be imported: {err}",
                ).format(module=module, err=err)

        if not self.plugin.settingApikey.value():
            return False, self.__tr("Please input your API key in the settings")

        return True, ""

    @override
    def helpUrl(self) -> str:
        return self.plugin.helpUrl(
            f"algorithms/{self.groupId()}/{self.name()}.html"
        ).toString()

    def casaGeoClient(self) -> "CasaGeoClient":
        from casageo.tools import CasaGeoClient

        return CasaGeoClient(
            self.plugin.settingApikey.value(),
            preferred_language=self.plugin.settingLanguage.value() or None,
            preferred_unit_system=self.plugin.settingUnitSystem.value() or None,
            preferred_political_view=self.plugin.settingPoliticalView.value() or None,
        )

    def requiredPythonModules(self) -> list[str]:
        return ["casageo.tools"]

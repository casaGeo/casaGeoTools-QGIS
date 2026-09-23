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

from collections.abc import Generator
from functools import cached_property
from typing import TYPE_CHECKING, Any, Never, Self, override

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCsException,  # pyright: ignore[reportAttributeAccessIssue]
    QgsFeature,
    QgsFeatureRequest,
    QgsPointXY,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,  # pyright: ignore[reportAttributeAccessIssue]
    QgsProcessingFeatureSource,
    QgsProcessingFeedback,
    QgsProcessingParameterDefinition,
    QgsProcessingProvider,
)

from ..resources import LIBRARY_IDENTIFIER, MINIMUM_REQUIRED_LIBRARY_VERSION
from ..utils import (
    ProcessingFeatureSinkDefinition,
    TrMethod,
    parameter_crs_pairs,
    version_tuple,
)

if TYPE_CHECKING:
    from pandas import DataFrame
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
        from .address import CasaGeoToolsAddressSearchAlgorithm
        from .isolines import CasaGeoToolsIsolinesAlgorithm
        from .poi import CasaGeoToolsPOISearchAlgorithm
        from .routes import (
            CasaGeoToolsRoutesLineSegmentAlgorithm,
            CasaGeoToolsRoutesSingleAlgorithm,
        )

        self.addAlgorithm(CasaGeoToolsAddressSearchAlgorithm(self.plugin))
        self.addAlgorithm(CasaGeoToolsPOISearchAlgorithm(self.plugin))
        self.addAlgorithm(CasaGeoToolsIsolinesAlgorithm(self.plugin))
        self.addAlgorithm(CasaGeoToolsRoutesSingleAlgorithm(self.plugin))
        self.addAlgorithm(CasaGeoToolsRoutesLineSegmentAlgorithm(self.plugin))

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

    GROUP_ID_CODER = ""
    GROUP_ID_SPATIAL = ""

    def __init__(self, plugin: "CasaGeoToolsPlugin") -> None:
        super().__init__()
        self.plugin = plugin
        self.status_ok = True
        self.status_message = ""
        self.batch_mode = False

    @cached_property
    def HERE_CRS(self) -> QgsCoordinateReferenceSystem:
        return QgsCoordinateReferenceSystem.fromEpsgId(4326)

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
        return self.plugin.helpUrl(f"algorithms/{self.name()}.html").toString()

    @override
    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        from importlib.metadata import PackageNotFoundError, version

        try:
            version_s = version(LIBRARY_IDENTIFIER)
        except PackageNotFoundError as err:
            self.status_ok = False
            self.status_message = self.__tr(
                "The {module} Python module is not installed",
            ).format(module=err.name)
            return

        try:
            version_t = version_tuple(version_s)
        except ValueError:
            self.status_ok = False
            self.status_message = self.__tr(
                "Failed to parse version information for the {module} Python module",
            ).format(module=LIBRARY_IDENTIFIER)
            return

        if version_t < MINIMUM_REQUIRED_LIBRARY_VERSION:
            self.status_ok = False
            self.status_message = self.__tr(
                "The {module} library is outdated, please install at least version {version}",
            ).format(
                module=LIBRARY_IDENTIFIER,
                version=".".join(map(str, MINIMUM_REQUIRED_LIBRARY_VERSION)),
            )
            return

        if not self.plugin.settingApikey.value():
            self.status_ok = False
            self.status_message = self.__tr("Please input your API key in the settings")
            return

        try:
            self._initAlgorithm(configuration)
        except ModuleNotFoundError as err:
            self.status_ok = False
            self.status_message = self.__tr(
                "The {module} module is not installed",
            ).format(module=err.name)
        except ImportError as err:
            self.status_ok = False
            self.status_message = self.__tr(
                "The {module} module could not be imported: {err}",
            ).format(module=err.name, err=err)
        except Exception as err:
            self.status_ok = False
            self.status_message = self.__tr(
                "An error occurred while initializing the algorithm: {err}",
            ).format(err=err)

    def _initAlgorithm(self, configuration: dict[str, Any] | None) -> None:
        pass

    def _addParameter(
        self,
        parameterDefinition: QgsProcessingParameterDefinition,
        /,
        *,
        createOutput: bool = True,
    ) -> None:
        self.addParameter(parameterDefinition, createOutput)

    def _addBatchParameter(
        self,
        parameterDefinition: QgsProcessingParameterDefinition,
        /,
        *,
        createOutput: bool = True,
    ) -> None:
        if not self.batch_mode:
            return

        self.addParameter(parameterDefinition, createOutput)

    @override
    def validateInputCrs(
        self, parameters: dict[str, Any], context: QgsProcessingContext
    ) -> bool:
        return super().validateInputCrs(parameters, context) and all(
            QgsCoordinateTransform.isTransformationPossible(crs, self.HERE_CRS)
            for _, crs in parameter_crs_pairs(
                self.parameterDefinitions(), parameters, context
            )
        )

    @override
    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, Any]:
        from pandas import DataFrame

        if feedback is None:
            feedback = QgsProcessingFeedback(logFeedback=False)

        feedback.setProgressText(self._convertInputGeometriesMessage())
        queries = self._convertInputGeometries(parameters, context, feedback)

        if queries.empty:
            feedback.pushInfo(self.__tr("No valid features in input layer"))
            results = DataFrame()
        else:
            feedback.setProgressText(self._calculateResultsMessage())
            results = self._calculateResults(parameters, context, feedback, queries)

        feedback.setProgressText(self._writeOutputGeometriesMessage())
        return self._writeOutputGeometries(parameters, context, feedback, results)

    def _convertInputGeometriesMessage(self) -> str:
        return self.__tr("Converting input geometries")

    def _convertInputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> "DataFrame":
        raise NotImplementedError

    def _calculateResultsMessage(self) -> str:
        return self.__tr("Calculating results")

    def _calculateResults(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "DataFrame":
        raise NotImplementedError

    def _writeOutputGeometriesMessage(self) -> str:
        return self.__tr("Converting results")

    def _writeOutputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        results: "DataFrame",
    ) -> dict[str, str]:
        raise NotImplementedError

    # Helper methods

    def _getSource(
        self,
        name: str,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
    ) -> QgsProcessingFeatureSource:
        source = self.parameterAsSource(parameters, name, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, name))
        return source

    def _getSink(
        self,
        name: str,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
    ) -> ProcessingFeatureSinkDefinition:
        props = self.sinkProperties(name, parameters, context, {})
        if props.availability == Qgis.ProcessingPropertyAvailability.NotAvailable:
            raise QgsProcessingException(self.invalidSinkError(parameters, name))

        sink, dest = self.parameterAsSink(
            parameters,
            name,
            context,
            props.fields,
            props.wkbType,
            props.crs,
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, name))

        return ProcessingFeatureSinkDefinition(
            name=name,
            props=props,
            dest=dest,
            sink=sink,
        )

    def _parameterAsTransformedPoint(
        self,
        name: str,
        crs: QgsCoordinateReferenceSystem,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
    ) -> QgsPointXY:
        point = self.parameterAsPoint(parameters, name, context)
        if point.isEmpty():
            return point

        sourcecrs = self.parameterAsPointCrs(parameters, name, context)
        destcrs = crs
        xform = QgsCoordinateTransform(sourcecrs, destcrs, context.transformContext())
        if not xform.isValid():
            msg = self.__tr(
                "Unable to construct a coordinate transformation from {sourcecrs} to {destcrs} for parameter {parameter}"
            ).format(
                sourcecrs=sourcecrs.authid(),
                destcrs=destcrs.authid(),
                parameter=name,
            )
            raise QgsProcessingException(msg)

        try:
            return xform.transform(point)
        except QgsCsException as err:
            msg = self.__tr(
                "Coordinate transformation failed for parameter {parameter}: {error}"
            ).format(parameter=name, error=err)
            raise QgsProcessingException(msg) from err

    def _simpleFeatureRequest(
        self,
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> QgsFeatureRequest:
        request = QgsFeatureRequest()
        request.setExpressionContext(context.expressionContext())
        request.setFeedback(feedback)
        request.setTransformErrorCallback(self._onTransformError)
        return request

    def _geometryFeatureRequest(
        self,
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> QgsFeatureRequest:
        request = self._simpleFeatureRequest(context, feedback)
        request.setDestinationCrs(self.HERE_CRS, context.transformContext())
        return request

    def _resultsOf(
        self, df: "DataFrame", /, feedback: QgsProcessingFeedback
    ) -> Generator[Any]:
        for result in df.itertuples():
            # We DO NOT check for feedback.isCanceled() because we never want to skip already computed results.

            if error_code := getattr(result, "error_code", None):
                if error_message := getattr(result, "error_message", None):
                    error = self.__tr("Error ({code}): {message}").format(
                        code=error_code, message=error_message
                    )
                else:
                    error = self.__tr("Error ({code})").format(code=error_code)

                feedback.reportError(error)

            yield result

    def _onTransformError(self, feature: QgsFeature) -> Never:
        msg = self.__tr("Reprojection of feature {featid} failed").format(
            featid=feature.id()
        )
        raise QgsProcessingException(msg)

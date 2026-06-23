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

__all__ = [
    "CasaGeoToolsIsolinesAlgorithm",
]

import importlib
from typing import Any, LiteralString, override

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterString,
    QgsProject,
    QgsSettings,
)
from qgis.PyQt.QtCore import QCoreApplication, QMetaType

from casageotools_qgis import resources


def _get_api_key() -> str:
    return QgsSettings().value("casaGeoTools/APIKey", "", type=str)


class CasaGeoToolsAbstractSpatialAlgorithm(QgsProcessingAlgorithm):
    @override
    def group(self) -> str:
        return self.__tr("Spatial", "Group")

    @override
    def groupId(self) -> str:
        return "spatial"

    @override
    def canExecute(self) -> tuple[bool, str]:
        for module in ["casageo.tools", "casageo.spatial", "geopandas"]:
            try:
                importlib.import_module(module)
            except ModuleNotFoundError:
                return False, f"The {module} module is not installed"
            except ImportError as err:
                return False, f"The {module} module could not be imported: {err}"

        if not _get_api_key():
            return False, "Please input your API key in the settings"

        return True, ""

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


class CasaGeoToolsIsolinesAlgorithm(CasaGeoToolsAbstractSpatialAlgorithm):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    RANGES = "RANGES"
    RANGES_UNIT = "RANGES_UNIT"
    TRANSPORT_MODE = "TRANSPORT_MODE"
    ROUTING_MODE = "ROUTING_MODE"
    DIRECTION = "DIRECTION"

    @override
    def displayName(self) -> str:
        return self.__tr("Isolines", "Algorithm")

    @override
    def name(self) -> str:
        return "isolines"

    @override
    def shortDescription(self) -> str:
        return self.__tr("Calculates isolines around locations.")

    @override
    def shortHelpString(self) -> str:
        return self.__tr("""
        Calculates isolines around locations.
        The input points will be converted into EPSG:4326 and the resulting isolines are EPSG:4326 polygons. There may be multiple output polygons for a single input point. 
        """)

    @override
    def helpUrl(self) -> str:
        return resources.help_url("algorithms/spatial/isolines.html").toString()

    @override
    def createInstance(self) -> QgsProcessingAlgorithm | None:
        return CasaGeoToolsIsolinesAlgorithm()

    @override
    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        try:
            import casageo.tools._consts
        except ImportError:
            return

        if configuration is None:
            configuration = {}

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.__tr("Input layer"),
                [Qgis.ProcessingSourceType.VectorPoint],
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.__tr("Output layer"),
                Qgis.ProcessingSourceType.VectorPolygon,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.RANGES,
                self.__tr("Ranges (separated by semicolons"),
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.RANGES_UNIT,
                self.__tr("Ranges unit"),
                options=casageo.tools._consts.RANGE_UNITS,
                defaultValue=casageo.tools._consts.RANGE_UNITS[0],
                usesStaticStrings=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.TRANSPORT_MODE,
                self.__tr("Transport mode"),
                options=casageo.tools._consts.TRANSPORT_MODES,
                defaultValue=casageo.tools._consts.TRANSPORT_MODES[0],
                usesStaticStrings=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.ROUTING_MODE,
                self.__tr("Routing mode"),
                options=casageo.tools._consts.ROUTING_MODES,
                defaultValue=casageo.tools._consts.ROUTING_MODES[0],
                usesStaticStrings=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.DIRECTION,
                self.__tr("Direction"),
                options=casageo.tools._consts.DIRECTION_TYPES,
                defaultValue=casageo.tools._consts.DIRECTION_TYPES[0],
                usesStaticStrings=True,
            )
        )

    def _get_ranges(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
    ) -> list[float]:
        ranges_str = self.parameterAsString(parameters, self.RANGES, context)
        return [float(r) for r in ranges_str.split(";")]

    def _get_ranges_unit(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
    ) -> str:
        return self.parameterAsString(parameters, self.RANGES_UNIT, context)

    def _get_transport_mode(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
    ) -> str:
        import casageo.tools._consts

        index = self.parameterAsEnum(parameters, self.TRANSPORT_MODE, context)
        return casageo.tools._consts.TRANSPORT_MODES[index]

    def _get_routing_mode(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
    ) -> str:
        import casageo.tools._consts

        index = self.parameterAsEnum(parameters, self.ROUTING_MODE, context)
        return casageo.tools._consts.ROUTING_MODES[index]

    def _get_direction(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
    ) -> str:
        import casageo.tools._consts

        index = self.parameterAsEnum(parameters, self.DIRECTION, context)
        return casageo.tools._consts.DIRECTION_TYPES[index]

    @override
    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, Any]:
        import casageo.spatial
        import casageo.tools
        from geopandas import GeoDataFrame

        client = casageo.tools.CasaGeoClient(_get_api_key())

        epsg4326 = QgsCoordinateReferenceSystem.fromEpsgId(4326)
        assert epsg4326.isValid()

        fields = QgsFields([
            QgsField("id", QMetaType.Type.Int),
            QgsField("subid", QMetaType.Type.Int),
            QgsField("rangetype", QMetaType.Type.QString),
            QgsField("rangeunit", QMetaType.Type.QString),
            QgsField("rangevalue", QMetaType.Type.Double),
        ])

        source = self.parameterAsSource(
            parameters,
            self.INPUT,
            context,
        )
        assert source is not None

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            Qgis.WkbType.Polygon,
            epsg4326,
        )
        assert sink is not None

        defaults = {
            "ranges": self._get_ranges(parameters, context),
            "ranges_unit": self._get_ranges_unit(parameters, context),
            "transport_mode": self._get_transport_mode(parameters, context),
            "routing_mode": self._get_routing_mode(parameters, context),
            "direction": self._get_direction(parameters, context),
        }

        if feedback is not None:
            feedback.setProgressText(self.__tr("Converting input geometries"))

        into_epsg4326 = QgsCoordinateTransform(
            source.sourceCrs(),
            epsg4326,
            QgsProject.instance(),
        )

        inputs = []
        for feature in source.getFeatures():  # pyright: ignore[reportGeneralTypeIssues]
            position = feature.geometry()
            if position.isEmpty():
                continue

            position.transform(into_epsg4326)
            if position.isEmpty():
                continue

            inputs.append({"position": position.as_shapely()})

        queries = GeoDataFrame(inputs, geometry="position", crs=epsg4326.authid())

        if feedback is not None:
            feedback.setProgressText(self.__tr("Calculating isolines"))

        results = casageo.spatial.isolines(client, queries, defaults)

        if feedback is not None:
            feedback.setProgressText(self.__tr("Converting results"))

        for result in results.itertuples():
            feature = QgsFeature(fields)
            feature.setGeometry(QgsGeometry.from_shapely(result.geometry))  # pyright: ignore[reportAttributeAccessIssue]
            feature.setAttributes([
                result.id,  # pyright: ignore[reportAttributeAccessIssue]
                result.subid,  # pyright: ignore[reportAttributeAccessIssue]
                result.rangetype,  # pyright: ignore[reportAttributeAccessIssue]
                result.rangeunit,  # pyright: ignore[reportAttributeAccessIssue]
                result.rangevalue,  # pyright: ignore[reportAttributeAccessIssue]
            ])
            sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)

        return {self.OUTPUT: dest_id}

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

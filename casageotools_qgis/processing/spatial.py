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

from typing import TYPE_CHECKING, Any, override

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsPointXY,
    QgsProcessingContext,
    QgsProcessingException,  # pyright: ignore[reportAttributeAccessIssue]
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterString,
    QgsProject,
)
from qgis.PyQt.QtCore import QMetaType

from ..utils import (
    TrMethod,
    features_of,
    geometry_as_shapely,
    geometry_from_shapely,
    pydatetime,
)
from . import CasaGeoToolsAbstractProcessingAlgorithm

if TYPE_CHECKING:
    from geopandas import GeoDataFrame
    from pandas import DataFrame


class CasaGeoToolsAbstractSpatialAlgorithm(CasaGeoToolsAbstractProcessingAlgorithm):
    __tr = TrMethod()

    @override
    def group(self) -> str:
        return self.__tr("Spatial", "Group")

    @override
    def groupId(self) -> str:
        return "spatial"

    @override
    def requiredPythonModules(self) -> list[str]:
        return ["casageo.tools", "casageo.spatial", "geopandas"]


class CasaGeoToolsIsolinesAlgorithm(CasaGeoToolsAbstractSpatialAlgorithm):
    __tr = TrMethod()

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    RANGES = "RANGES"
    RANGES_UNIT = "RANGES_UNIT"
    TRANSPORT_MODE = "TRANSPORT_MODE"
    ROUTING_MODE = "ROUTING_MODE"
    DIRECTION = "DIRECTION"
    DEPARTURE_TIME = "DEPARTURE_TIME"
    ARRIVAL_TIME = "ARRIVAL_TIME"
    TRAFFIC = "TRAFFIC"
    AVOID_FEATURES = "AVOID_FEATURES"
    EXCLUDE_COUNTRIES = "EXCLUDE_COUNTRIES"

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
    def createInstance(self) -> "CasaGeoToolsIsolinesAlgorithm":
        return CasaGeoToolsIsolinesAlgorithm(self.plugin)

    @override
    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        try:
            import casageo.spatial

            DIRECTION_TYPES = casageo.spatial.DIRECTION_TYPES
            RANGE_UNITS = casageo.spatial.RANGE_UNITS
            ROUTING_MODES = casageo.spatial.ROUTING_MODES
            TRANSPORT_MODES = casageo.spatial.TRANSPORT_MODES
            DEFAULT_RANGE_UNIT = casageo.spatial.DEFAULT_RANGE_UNIT
            DEFAULT_TRANSPORT_MODE = casageo.spatial.DEFAULT_TRANSPORT_MODE
            DEFAULT_ROUTING_MODE = casageo.spatial.DEFAULT_ROUTING_MODE
            DEFAULT_DIRECTION = casageo.spatial.DEFAULT_DIRECTION
            DEFAULT_DEPARTURE_TIME = casageo.spatial.DEFAULT_DEPARTURE_TIME
            DEFAULT_ARRIVAL_TIME = casageo.spatial.DEFAULT_ARRIVAL_TIME
            DEFAULT_TRAFFIC = casageo.spatial.DEFAULT_TRAFFIC
            DEFAULT_AVOID_FEATURES = casageo.spatial.DEFAULT_AVOID_FEATURES
            DEFAULT_EXCLUDE_COUNTRIES = casageo.spatial.DEFAULT_EXCLUDE_COUNTRIES
        except (ImportError, AttributeError):
            DIRECTION_TYPES = [None]
            RANGE_UNITS = [None]
            ROUTING_MODES = [None]
            TRANSPORT_MODES = [None]
            DEFAULT_RANGE_UNIT = None
            DEFAULT_TRANSPORT_MODE = None
            DEFAULT_ROUTING_MODE = None
            DEFAULT_DIRECTION = None
            DEFAULT_DEPARTURE_TIME = None
            DEFAULT_ARRIVAL_TIME = None
            DEFAULT_TRAFFIC = None
            DEFAULT_AVOID_FEATURES = ()
            DEFAULT_EXCLUDE_COUNTRIES = ()

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
                self.__tr("Ranges (separated by semicolons)"),
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.RANGES_UNIT,
                self.__tr("Ranges unit"),
                options=RANGE_UNITS,
                defaultValue=DEFAULT_RANGE_UNIT,
                usesStaticStrings=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.TRANSPORT_MODE,
                self.__tr("Transport mode"),
                options=TRANSPORT_MODES,
                defaultValue=DEFAULT_TRANSPORT_MODE,
                usesStaticStrings=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.ROUTING_MODE,
                self.__tr("Routing mode"),
                options=ROUTING_MODES,
                defaultValue=DEFAULT_ROUTING_MODE,
                usesStaticStrings=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.DIRECTION,
                self.__tr("Direction"),
                options=DIRECTION_TYPES,
                defaultValue=DEFAULT_DIRECTION,
                usesStaticStrings=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterDateTime(
                self.DEPARTURE_TIME,
                self.__tr("Departure time (if outgoing)"),
                defaultValue=DEFAULT_DEPARTURE_TIME,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterDateTime(
                self.ARRIVAL_TIME,
                self.__tr("Arrival time (if incoming)"),
                defaultValue=DEFAULT_ARRIVAL_TIME,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.TRAFFIC,
                self.__tr("Use traffic data"),
                defaultValue=DEFAULT_TRAFFIC,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.AVOID_FEATURES,
                self.__tr("Avoid features (separated by commas)"),
                defaultValue=",".join(DEFAULT_AVOID_FEATURES),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.EXCLUDE_COUNTRIES,
                self.__tr("Exclude countries (separated by commas)"),
                defaultValue=",".join(DEFAULT_EXCLUDE_COUNTRIES),
            )
        )

    @override
    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, Any]:
        from geopandas import GeoDataFrame

        if feedback is None:
            feedback = QgsProcessingFeedback(logFeedback=False)

        feedback.setProgressText(self.__tr("Converting input geometries"))
        queries = self._convertInputGeometries(parameters, context, feedback)

        if queries.empty:
            feedback.pushInfo(self.__tr("No valid features in input layer"))
            results = GeoDataFrame()
        else:
            feedback.setProgressText(self.__tr("Calculating isolines"))
            results = self._calculateIsolines(parameters, context, feedback, queries)

        feedback.setProgressText(self.__tr("Converting results"))
        return self._writeOutputGeometries(parameters, context, feedback, results)

    def _convertInputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> "DataFrame":
        from pandas import DataFrame

        source = self.parameterAsSource(
            parameters,
            self.INPUT,
            context,
        )
        assert source is not None

        into_epsg4326 = QgsCoordinateTransform(
            source.sourceCrs(),
            QgsCoordinateReferenceSystem.fromEpsgId(4326),
            QgsProject.instance(),
        )

        data = []
        for feature in features_of(source):
            geometry = feature.geometry()
            if geometry.isEmpty():
                feedback.pushInfo(
                    self.__tr(
                        "Skipping feature {featid} due to empty geometry",
                    ).format(featid=feature.id())
                )
                continue

            geometry.transform(into_epsg4326)
            if geometry.isEmpty():
                feedback.pushInfo(
                    self.__tr(
                        "Skipping feature {featid} due to reprojection failure",
                    ).format(featid=feature.id())
                )
                continue

            position = geometry.asPoint()
            data.append({
                "position_longitude": position.x(),
                "position_latitude": position.y(),
            })

        return DataFrame(data)

    def _calculateIsolines(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "GeoDataFrame":
        """Calculate isolines using the casaGeoTools library."""
        import casageo.spatial
        import casageo.tools
        from casageo.spatial import (
            DIRECTION_TYPES,
            ROUTING_MODES,
            TRANSPORT_MODES,
        )

        client = self.casaGeoClient()

        ranges = self.parameterAsString(parameters, self.RANGES, context).split(";")
        ranges_unit = self.parameterAsString(parameters, self.RANGES_UNIT, context)
        transport_index = self.parameterAsEnum(parameters, self.TRANSPORT_MODE, context)
        routing_index = self.parameterAsEnum(parameters, self.ROUTING_MODE, context)
        direction_index = self.parameterAsEnum(parameters, self.DIRECTION, context)
        departure_time = self.parameterAsDateTime(
            parameters, self.DEPARTURE_TIME, context
        )
        arrival_time = self.parameterAsDateTime(parameters, self.ARRIVAL_TIME, context)
        traffic = self.parameterAsBool(parameters, self.TRAFFIC, context)
        avoid_features = self.parameterAsString(
            parameters, self.AVOID_FEATURES, context
        )
        exclude_countries = self.parameterAsString(
            parameters, self.EXCLUDE_COUNTRIES, context
        )

        defaults = {
            "ranges": [float(r) for r in ranges],
            "ranges_unit": ranges_unit,
            "transport_mode": TRANSPORT_MODES[transport_index],
            "routing_mode": ROUTING_MODES[routing_index],
            "direction": DIRECTION_TYPES[direction_index],
            "departure_time": pydatetime(departure_time),
            "arrival_time": pydatetime(arrival_time),
            "traffic": traffic,
            "avoid_features": avoid_features,
            "exclude_countries": exclude_countries,
        }

        try:
            return casageo.spatial.isolines(client, queries, defaults)
        except casageo.tools.CasaGeoError as err:
            raise QgsProcessingException(str(err)) from err

    def _writeOutputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        results: "GeoDataFrame",
    ) -> dict[str, str]:
        """Convert results to features and write them to the feature sink."""

        fields = QgsFields([
            QgsField("id", QMetaType.Type.Int),
            QgsField("subid", QMetaType.Type.Int),
            QgsField("rangetype", QMetaType.Type.QString),
            QgsField("rangeunit", QMetaType.Type.QString),
            QgsField("rangevalue", QMetaType.Type.Double),
            QgsField("timestamp", QMetaType.Type.QDateTime),
            # QgsField("error_code", QMetaType.Type.QString),
            # QgsField("error_message", QMetaType.Type.QString),
        ])

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            Qgis.WkbType.Polygon,
            QgsCoordinateReferenceSystem.fromEpsgId(4326),
        )
        assert sink is not None

        result: Any  # Make Pyright shut up about the named tuples.
        for result in results.itertuples():
            if result.error_code is not None:
                feedback.reportError(
                    self.__tr("Error ({code}): {message}").format(
                        code=result.error_code, message=result.error_message
                    )
                )
                continue

            feature = QgsFeature(fields)
            feature.setGeometry(geometry_from_shapely(result.geometry))
            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["rangetype"] = result.rangetype
            feature["rangeunit"] = result.rangeunit
            feature["rangevalue"] = result.rangevalue
            feature["timestamp"] = result.timestamp.isoformat()
            sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)

        return {self.OUTPUT: dest_id}


class CasaGeoToolsRoutingAlgorithm(CasaGeoToolsAbstractSpatialAlgorithm):
    __tr = TrMethod()

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    @override
    def displayName(self) -> str:
        return self.__tr("Routes", "Algorithm")

    @override
    def name(self) -> str:
        return "routes"

    @override
    def shortDescription(self) -> str:
        return self.__tr("Calculate routes between locations.")

    @override
    def createInstance(self) -> "CasaGeoToolsRoutingAlgorithm":
        return CasaGeoToolsRoutingAlgorithm(self.plugin)

    @override
    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        if configuration is None:
            configuration = {}

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.__tr("Input layer"),
                [Qgis.ProcessingSourceType.VectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.__tr("Output layer"),
                Qgis.ProcessingSourceType.VectorLine,
            )
        )

    @override
    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, Any]:
        from geopandas import GeoDataFrame

        if feedback is None:
            feedback = QgsProcessingFeedback(logFeedback=False)

        feedback.setProgressText(self.__tr("Converting input geometries"))
        queries = self._convertInputGeometries(parameters, context, feedback)

        if queries.empty:
            feedback.pushInfo(self.__tr("No valid features in input layer"))
            results = GeoDataFrame()
        else:
            feedback.setProgressText(self.__tr("Calculating routes"))
            results = self._calculateRoutes(parameters, context, feedback, queries)

        feedback.setProgressText(self.__tr("Converting results"))
        return self._writeOutputGeometries(parameters, context, feedback, results)

    def _convertInputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> "DataFrame":
        from pandas import DataFrame

        source = self.parameterAsSource(
            parameters,
            self.INPUT,
            context,
        )
        assert source is not None

        into_epsg4326 = QgsCoordinateTransform(
            source.sourceCrs(),
            QgsCoordinateReferenceSystem.fromEpsgId(4326),
            QgsProject.instance(),
        )

        show_intermediate_waypoint_warning = False

        data = []
        for feature in features_of(source):
            itinerary = feature.geometry()
            if itinerary.isEmpty():
                feedback.pushInfo(
                    self.__tr(
                        "Skipping feature {featid} due to empty geometry",
                    ).format(featid=feature.id())
                )
                continue

            itinerary.transform(into_epsg4326)
            if itinerary.isEmpty():
                feedback.pushInfo(
                    self.__tr(
                        "Skipping feature {featid} due to reprojection failure",
                    ).format(featid=feature.id())
                )
                continue

            waypoints: list[QgsPointXY] = itinerary.asPolyline()
            if len(waypoints) > 2:
                feedback.pushInfo(
                    self.__tr(
                        "Feature {featid} has intermediate waypoints which will be ignored",
                    ).format(featid=feature.id())
                )
                show_intermediate_waypoint_warning = True

            origin = waypoints[0]
            destination = waypoints[-1]

            data.append({
                "origin_longitude": origin.x(),
                "origin_latitude": origin.y(),
                "destination_longitude": destination.x(),
                "destination_latitude": destination.y(),
            })

        if show_intermediate_waypoint_warning:
            feedback.pushWarning(
                self.__tr(
                    "Some input geometries contain intermediate waypoints. Routing with intermediate waypoints is not implemented yet and these waypoints will be ignored."
                )
            )

        return DataFrame(data)

    def _calculateRoutes(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "GeoDataFrame":
        import casageo.spatial
        import casageo.tools

        client = self.casaGeoClient()
        defaults = {}

        try:
            return casageo.spatial.routes(client, queries, defaults)
        except casageo.tools.CasaGeoError as err:
            raise QgsProcessingException(str(err)) from err

    def _writeOutputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        results: "GeoDataFrame",
    ) -> dict[str, str]:
        """Convert results to features and write them to the feature sink."""

        fields = QgsFields([
            QgsField("id", QMetaType.Type.Int),
            QgsField("subid", QMetaType.Type.Int),
            QgsField("length", QMetaType.Type.Double),
            QgsField("duration", QMetaType.Type.Double),
            QgsField("timestamp", QMetaType.Type.QDateTime),
            # QgsField("error_code", QMetaType.Type.QString),
            # QgsField("error_message", QMetaType.Type.QString),
        ])

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            # TODO: Make this a MultiLineStringZM with elevation and time datapoints.
            Qgis.WkbType.MultiLineString,
            QgsCoordinateReferenceSystem.fromEpsgId(4326),
        )
        assert sink is not None

        result: Any  # Make Pyright shut up about the named tuples.
        for result in results.itertuples():
            if result.error_code is not None:
                feedback.reportError(
                    self.__tr("Error ({code}): {message}").format(
                        code=result.error_code, message=result.error_message
                    )
                )
                continue

            feature = QgsFeature(fields)
            feature.setGeometry(geometry_from_shapely(result.geometry))
            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["length"] = result.length
            feature["duration"] = result.duration
            feature["timestamp"] = result.timestamp.isoformat()
            sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)

        return {self.OUTPUT: dest_id}

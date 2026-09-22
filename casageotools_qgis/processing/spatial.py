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

from datetime import datetime
from typing import TYPE_CHECKING, Any, override

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,  # pyright: ignore[reportAttributeAccessIssue]
    QgsProcessingFeedback,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExpression,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QMetaType

from ..utils import (
    ProcessingFeatureSinkDefinition,
    TrMethod,
    and_then,
    features_of,
    geometry_as_shapely,
    geometry_from_shapely,
    pydatetime,
)
from . import CasaGeoToolsProcessingAlgorithm

if TYPE_CHECKING:
    from geopandas import GeoDataFrame
    from pandas import DataFrame


class CasaGeoToolsIsolinesAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    INPUT = "INPUT"
    RANGES = "RANGES"
    RANGES_UNIT = "RANGES_UNIT"
    TRANSPORT_MODE = "TRANSPORT_MODE"
    ROUTING_MODE = "ROUTING_MODE"
    DIRECTION = "DIRECTION"
    DATETIME = "DATETIME"
    AVOID_FEATURES = "AVOID_FEATURES"
    EXCLUDE_COUNTRIES = "EXCLUDE_COUNTRIES"

    OUTPUT_ISOLINES = "OUTPUT_ISOLINES"
    OUTPUT_NAVIGATIONS = "OUTPUT_NAVIGATIONS"

    @override
    def groupId(self) -> str:
        return self.GROUP_ID_SPATIAL

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
    def _initAlgorithm(self, configuration: dict[str, Any] | None) -> None:
        from casageo.spatial import (
            DEFAULT_DIRECTION,
            DEFAULT_RANGE_UNIT,
            DEFAULT_ROUTING_MODE,
            DEFAULT_TRANSPORT_MODE,
            AvoidableFeature,
            DirectionType,
            RangeUnit,
            RoutingMode,
            TransportMode,
        )

        translator = self.plugin.spatialTranslator
        trRangeUnit = translator.translateRangeUnit
        trTransportMode = translator.translateTransportMode
        trRoutingMode = translator.translateRoutingMode
        trDirectionType = translator.translateDirectionType
        trAvoidableFeature = translator.translateAvoidableFeature

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.__tr("Input layer"),
                [Qgis.ProcessingSourceType.VectorPoint],
            )
        )

        # This could be converted into a QgsProcessingParameterMatrix.
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
                options=map(trRangeUnit, RangeUnit),
                defaultValue=trRangeUnit(DEFAULT_RANGE_UNIT),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.TRANSPORT_MODE,
                self.__tr("Transport mode"),
                options=map(trTransportMode, TransportMode),
                defaultValue=trTransportMode(DEFAULT_TRANSPORT_MODE),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.ROUTING_MODE,
                self.__tr("Routing mode"),
                options=map(trRoutingMode, RoutingMode),
                defaultValue=trRoutingMode(DEFAULT_ROUTING_MODE),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.DIRECTION,
                self.__tr("Direction"),
                options=map(trDirectionType, DirectionType),
                defaultValue=trDirectionType(DEFAULT_DIRECTION),
            )
        )

        self.addParameter(
            QgsProcessingParameterDateTime(
                self.DATETIME,
                self.__tr("Time of departure/arrival"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.AVOID_FEATURES,
                self.__tr("Avoid features"),
                options=map(trAvoidableFeature, AvoidableFeature),
                allowMultiple=True,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.EXCLUDE_COUNTRIES,
                self.__tr("Exclude countries (separated by commas)"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_ISOLINES,
                self.__tr("Isoline polygons"),
                Qgis.ProcessingSourceType.VectorPolygon,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_NAVIGATIONS,
                self.__tr("Isoline navigation points"),
                Qgis.ProcessingSourceType.VectorPoint,
            )
        )

    @override
    def sinkProperties(
        self,
        sink: str | None,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        sourceProperties: dict[str | None, QgsProcessingAlgorithm.VectorProperties],
    ) -> QgsProcessingAlgorithm.VectorProperties:
        match sink:
            case self.OUTPUT_ISOLINES:
                props = QgsProcessingAlgorithm.VectorProperties()
                props.availability = Qgis.ProcessingPropertyAvailability.Available
                props.crs = self.HERE_CRS
                props.fields = QgsFields([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("rangetype", QMetaType.Type.QString),
                    QgsField("rangeunit", QMetaType.Type.QString),
                    QgsField("rangevalue", QMetaType.Type.Double),
                    QgsField("direction", QMetaType.Type.QString),
                    QgsField("location_placename", QMetaType.Type.QString),
                    QgsField("location_longitude", QMetaType.Type.Double),
                    QgsField("location_latitude", QMetaType.Type.Double),
                    QgsField("location_datetime", QMetaType.Type.QDateTime),
                    QgsField("timestamp", QMetaType.Type.QDateTime),
                    QgsField("error_code", QMetaType.Type.QString),
                    QgsField("error_message", QMetaType.Type.QString),
                ])
                props.wkbType = Qgis.WkbType.MultiPolygon
                return props

            case self.OUTPUT_NAVIGATIONS:
                props = QgsProcessingAlgorithm.VectorProperties()
                props.availability = Qgis.ProcessingPropertyAvailability.Available
                props.crs = self.HERE_CRS
                props.fields = QgsFields([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("placename", QMetaType.Type.QString),
                    QgsField("longitude", QMetaType.Type.Double),
                    QgsField("latitude", QMetaType.Type.Double),
                    QgsField("datetime", QMetaType.Type.QDateTime),
                    QgsField("timestamp", QMetaType.Type.QDateTime),
                    QgsField("error_code", QMetaType.Type.QString),
                    QgsField("error_message", QMetaType.Type.QString),
                ])
                props.wkbType = Qgis.WkbType.Point
                return props

        return super().sinkProperties(sink, parameters, context, sourceProperties)

    @override
    def validateInputCrs(
        self, parameters: dict[str, Any], context: QgsProcessingContext
    ) -> bool:
        return (
            super().validateInputCrs(parameters, context)
            and self._validateSourceCrsCompatible(self.INPUT, parameters, context)
            and True
        )

    @override
    def _convertInputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> "DataFrame":
        from pandas import DataFrame

        source = self._getSource(self.INPUT, parameters, context)
        request = self._geometryFeatureRequest(context, feedback)
        data = [
            {
                "id": feature.id(),
                "position": geometry_as_shapely(feature.geometry()),
            }
            for feature in features_of(source, request)
        ]

        return DataFrame(data)

    @override
    def _calculateResultsMessage(self) -> str:
        return self.__tr("Calculating isolines")

    @override
    def _calculateResults(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "GeoDataFrame":
        """Calculate isolines using the casaGeoTools library."""
        import casageo.spatial
        from casageo.spatial import (
            AvoidableFeature,
            DirectionType,
            RangeUnit,
            RoutingMode,
            TransportMode,
        )

        AVOIDABLE_FEATURES = list(AvoidableFeature)
        DIRECTION_TYPES = list(DirectionType)
        RANGE_UNITS = list(RangeUnit)
        ROUTING_MODES = list(RoutingMode)
        TRANSPORT_MODES = list(TransportMode)

        client = self.plugin.casaGeoClient(feedback)

        ranges = self.parameterAsString(parameters, self.RANGES, context).split(";")
        ranges_unit_index = self.parameterAsEnum(parameters, self.RANGES_UNIT, context)
        transport_index = self.parameterAsEnum(parameters, self.TRANSPORT_MODE, context)
        routing_index = self.parameterAsEnum(parameters, self.ROUTING_MODE, context)
        direction_index = self.parameterAsEnum(parameters, self.DIRECTION, context)
        date_and_time = self.parameterAsDateTime(parameters, self.DATETIME, context)
        avoid_features_indices = self.parameterAsEnums(
            parameters, self.AVOID_FEATURES, context
        )
        exclude_countries = self.parameterAsString(
            parameters, self.EXCLUDE_COUNTRIES, context
        )

        defaults = {
            "ranges": [float(r) for r in ranges],
            "ranges_unit": RANGE_UNITS[ranges_unit_index],
            "transport_mode": TRANSPORT_MODES[transport_index],
            "routing_mode": ROUTING_MODES[routing_index],
            "direction": DIRECTION_TYPES[direction_index],
            "departure_time": pydatetime(date_and_time),
            "arrival_time": pydatetime(date_and_time),
            "traffic": date_and_time.isValid(),
            "avoid_features": [AVOIDABLE_FEATURES[i] for i in avoid_features_indices],
            "exclude_countries": exclude_countries,
        }

        try:
            return casageo.spatial.isolines(
                client,
                queries,
                defaults,
                departure_info=True,
                arrival_info=True,
                coordinates=True,
            )
        except Exception as err:
            raise QgsProcessingException(str(err)) from err

    @override
    def _writeOutputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        results: "DataFrame",
    ) -> dict[str, str]:
        """Convert results to features and write them to the feature sink."""

        from casageo.spatial import DirectionType

        isoformat = datetime.isoformat

        isolines = self._getSink(self.OUTPUT_ISOLINES, parameters, context)
        navigations = self._getSink(self.OUTPUT_NAVIGATIONS, parameters, context)

        def addFeature(
            output: ProcessingFeatureSinkDefinition, feature: QgsFeature
        ) -> None:
            if not output.sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert):
                error = self.writeFeatureError(output.sink, parameters, output.name)
                feedback.reportError(error)

        def center(result: Any, key: str, /) -> Any:
            if result.direction == DirectionType.OUTGOING:
                return getattr(result, f"departure_{key}")
            if result.direction == DirectionType.INCOMING:
                return getattr(result, f"arrival_{key}")
            return None

        for result in self._resultsOf(results, feedback):
            feature = QgsFeature(isolines.props.fields)
            if (geom := result.geometry) is not None:
                feature.setGeometry(geometry_from_shapely(geom))

            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["rangetype"] = result.rangetype
            feature["rangeunit"] = result.rangeunit
            feature["rangevalue"] = result.rangevalue
            feature["direction"] = result.direction
            feature["location_placename"] = center(result, "placename")
            feature["location_longitude"] = center(result, "longitude")
            feature["location_latitude"] = center(result, "latitude")
            feature["location_datetime"] = and_then(center(result, "time"), isoformat)
            feature["timestamp"] = and_then(result.timestamp, isoformat)
            feature["error_code"] = result.error_code
            feature["error_message"] = result.error_message
            addFeature(isolines, feature)

            if result.subid > 0:
                continue

            feature = QgsFeature(navigations.props.fields)
            if (geom := center(result, "position")) is not None:
                feature.setGeometry(geometry_from_shapely(geom))

            feature["id"] = result.id
            feature["placename"] = center(result, "placename")
            feature["longitude"] = center(result, "longitude")
            feature["latitude"] = center(result, "latitude")
            feature["datetime"] = and_then(center(result, "time"), isoformat)
            feature["timestamp"] = and_then(result.timestamp, isoformat)
            feature["error_code"] = result.error_code
            feature["error_message"] = result.error_message
            addFeature(navigations, feature)

        return {
            isolines.name: isolines.dest,
            navigations.name: navigations.dest,
        }


class CasaGeoToolsRoutesAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    ALTERNATIVES = "ALTERNATIVES"
    TRANSPORT_MODE = "TRANSPORT_MODE"
    ROUTING_MODE = "ROUTING_MODE"
    DEPARTURE_TIME = "DEPARTURE_TIME"
    ARRIVAL_TIME = "ARRIVAL_TIME"
    AVOID_FEATURES = "AVOID_FEATURES"
    EXCLUDE_COUNTRIES = "EXCLUDE_COUNTRIES"

    OUTPUT_ROUTES = "OUTPUT_ROUTES"
    OUTPUT_NAVIGATIONS = "OUTPUT_NAVIGATIONS"

    @override
    def groupId(self) -> str:
        return self.GROUP_ID_SPATIAL

    @override
    def _initAlgorithm(self, configuration: dict[str, Any] | None) -> None:
        from casageo.spatial import (
            DEFAULT_ALTERNATIVES,
            DEFAULT_ROUTING_MODE,
            DEFAULT_TRANSPORT_MODE,
            MAX_ALTERNATIVES,
            MIN_ALTERNATIVES,
            AvoidableFeature,
            RoutingMode,
            TransportMode,
        )

        translator = self.plugin.spatialTranslator
        trTransportMode = translator.translateTransportMode
        trRoutingMode = translator.translateRoutingMode
        trAvoidableFeature = translator.translateAvoidableFeature

        self.addParameter(
            QgsProcessingParameterNumber(
                self.ALTERNATIVES,
                self.__tr("Number of alternative routes", "Parameter"),
                Qgis.ProcessingNumberParameterType.Integer,
                minValue=MIN_ALTERNATIVES,
                maxValue=MAX_ALTERNATIVES,
                defaultValue=DEFAULT_ALTERNATIVES,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.TRANSPORT_MODE,
                self.__tr("Transport mode"),
                options=map(trTransportMode, TransportMode),
                defaultValue=trTransportMode(DEFAULT_TRANSPORT_MODE),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.ROUTING_MODE,
                self.__tr("Routing mode"),
                options=map(trRoutingMode, RoutingMode),
                defaultValue=trRoutingMode(DEFAULT_ROUTING_MODE),
            )
        )

        self.addParameter(
            QgsProcessingParameterDateTime(
                self.DEPARTURE_TIME,
                self.__tr("Departure time", "Parameter"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterDateTime(
                self.ARRIVAL_TIME,
                self.__tr("Arrival time", "Parameter"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.AVOID_FEATURES,
                self.__tr("Avoid features"),
                options=map(trAvoidableFeature, AvoidableFeature),
                allowMultiple=True,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.EXCLUDE_COUNTRIES,
                self.__tr("Exclude countries (separated by commas)"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_ROUTES,
                self.__tr("Calculated routes", "Parameter"),
                Qgis.ProcessingSourceType.VectorLine,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_NAVIGATIONS,
                self.__tr("Routing navigation points"),
                Qgis.ProcessingSourceType.VectorPoint,
            )
        )

    @override
    def sinkProperties(
        self,
        sink: str | None,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        sourceProperties: dict[str | None, QgsProcessingAlgorithm.VectorProperties],
    ) -> QgsProcessingAlgorithm.VectorProperties:
        match sink:
            case self.OUTPUT_ROUTES:
                props = QgsProcessingAlgorithm.VectorProperties()
                props.availability = Qgis.ProcessingPropertyAvailability.Available
                props.crs = self.HERE_CRS
                props.fields = QgsFields([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("length", QMetaType.Type.Double),
                    QgsField("duration", QMetaType.Type.Double),
                    QgsField("timestamp", QMetaType.Type.QDateTime),
                    QgsField("error_code", QMetaType.Type.QString),
                    QgsField("error_message", QMetaType.Type.QString),
                ])
                # TODO: Make this a MultiLineStringZM with elevation and time datapoints.
                props.wkbType = Qgis.WkbType.MultiLineString
                return props

            case self.OUTPUT_NAVIGATIONS:
                props = QgsProcessingAlgorithm.VectorProperties()
                props.availability = Qgis.ProcessingPropertyAvailability.Available
                props.crs = self.HERE_CRS
                props.fields = QgsFields([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("navid", QMetaType.Type.Int),
                    QgsField("placename", QMetaType.Type.QString),
                    QgsField("longitude", QMetaType.Type.Double),
                    QgsField("latitude", QMetaType.Type.Double),
                    QgsField("datetime", QMetaType.Type.QDateTime),
                    QgsField("timestamp", QMetaType.Type.QDateTime),
                    QgsField("error_code", QMetaType.Type.QString),
                    QgsField("error_message", QMetaType.Type.QString),
                ])
                props.wkbType = Qgis.WkbType.Point
                return props

        return super().sinkProperties(sink, parameters, context, sourceProperties)

    @override
    def _calculateResultsMessage(self) -> str:
        return self.__tr("Calculating routes")

    @override
    def _calculateResults(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "GeoDataFrame":
        import casageo.spatial
        from casageo.spatial import (
            AvoidableFeature,
            RoutingMode,
            TransportMode,
        )

        AVOIDABLE_FEATURES = list(AvoidableFeature)
        ROUTING_MODES = list(RoutingMode)
        TRANSPORT_MODES = list(TransportMode)

        client = self.plugin.casaGeoClient(feedback)

        alternatives = self.parameterAsInt(parameters, self.ALTERNATIVES, context)
        transport_index = self.parameterAsEnum(parameters, self.TRANSPORT_MODE, context)
        routing_index = self.parameterAsEnum(parameters, self.ROUTING_MODE, context)
        departure_time = self.parameterAsDateTime(
            parameters, self.DEPARTURE_TIME, context
        )
        arrival_time = self.parameterAsDateTime(parameters, self.ARRIVAL_TIME, context)
        avoid_features_indices = self.parameterAsEnums(
            parameters, self.AVOID_FEATURES, context
        )
        exclude_countries = self.parameterAsString(
            parameters, self.EXCLUDE_COUNTRIES, context
        )

        defaults = {
            "alternatives": alternatives,
            "transport_mode": TRANSPORT_MODES[transport_index],
            "routing_mode": ROUTING_MODES[routing_index],
            "departure_time": pydatetime(departure_time),
            "arrival_time": pydatetime(arrival_time),
            "traffic": departure_time.isValid() or arrival_time.isValid(),
            "avoid_features": [AVOIDABLE_FEATURES[i] for i in avoid_features_indices],
            "exclude_countries": exclude_countries,
        }

        try:
            return casageo.spatial.routes(
                client,
                queries,
                defaults,
                departure_info=True,
                arrival_info=True,
                coordinates=True,
            )
        except Exception as err:
            raise QgsProcessingException(str(err)) from err

    @override
    def _writeOutputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        results: "DataFrame",
    ) -> dict[str, str]:
        """Convert results to features and write them to the feature sink."""

        routes = self._getSink(self.OUTPUT_ROUTES, parameters, context)
        navigations = self._getSink(self.OUTPUT_NAVIGATIONS, parameters, context)

        def addFeature(
            output: ProcessingFeatureSinkDefinition, feature: QgsFeature
        ) -> None:
            if not output.sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert):
                error = self.writeFeatureError(output.sink, parameters, output.name)
                feedback.reportError(error)

        for result in self._resultsOf(results, feedback):
            feature = QgsFeature(routes.props.fields)
            if (geom := result.geometry) is not None:
                feature.setGeometry(geometry_from_shapely(geom))

            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["length"] = result.length
            feature["duration"] = result.duration
            feature["timestamp"] = and_then(result.timestamp, datetime.isoformat)
            feature["error_code"] = result.error_code
            feature["error_message"] = result.error_message
            addFeature(routes, feature)

            for navid, prefix in enumerate(("departure", "arrival")):
                feature = QgsFeature(navigations.props.fields)
                if (geom := getattr(result, f"{prefix}_position")) is not None:
                    feature.setGeometry(geometry_from_shapely(geom))

                feature["id"] = result.id
                feature["subid"] = result.subid
                feature["navid"] = navid
                feature["placename"] = getattr(result, f"{prefix}_placename")
                feature["longitude"] = getattr(result, f"{prefix}_longitude")
                feature["latitude"] = getattr(result, f"{prefix}_latitude")
                feature["datetime"] = and_then(
                    getattr(result, f"{prefix}_time"), datetime.isoformat
                )
                feature["timestamp"] = and_then(result.timestamp, datetime.isoformat)
                feature["error_code"] = result.error_code
                feature["error_message"] = result.error_message
                addFeature(navigations, feature)

        return {
            routes.name: routes.dest,
            navigations.name: navigations.dest,
        }


class CasaGeoToolsRoutesSingleAlgorithm(CasaGeoToolsRoutesAlgorithm):
    __tr = TrMethod()

    ORIGIN = "ORIGIN"
    DESTINATION = "DESTINATION"

    @override
    def displayName(self) -> str:
        return self.__tr("Routes (single)", "Algorithm")

    @override
    def name(self) -> str:
        return "routes_single"

    @override
    def shortDescription(self) -> str:
        return self.__tr("Calculate routes between two locations.")

    @override
    def _initAlgorithm(self, configuration: dict[str, Any] | None) -> None:
        self.addParameter(
            QgsProcessingParameterPoint(
                self.ORIGIN,
                self.__tr("Origin", "Parameter"),
            )
        )

        self.addParameter(
            QgsProcessingParameterPoint(
                self.DESTINATION,
                self.__tr("Destination", "Parameter"),
            )
        )

        super()._initAlgorithm(configuration)

    @override
    def validateInputCrs(
        self, parameters: dict[str, Any], context: QgsProcessingContext
    ) -> bool:
        return (
            super().validateInputCrs(parameters, context)
            and self._validatePointCrsCompatible(self.ORIGIN, parameters, context)
            and self._validatePointCrsCompatible(self.DESTINATION, parameters, context)
        )

    @override
    def _convertInputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> "DataFrame":
        from pandas import DataFrame

        EPSG4326 = QgsCoordinateReferenceSystem.fromEpsgId(4326)

        origin = QgsCoordinateTransform(
            self.parameterAsPointCrs(parameters, self.ORIGIN, context),
            EPSG4326,
            context.transformContext(),
        ).transform(self.parameterAsPoint(parameters, self.ORIGIN, context))

        if origin.isEmpty():
            msg = self.__tr("Origin point is invalid in {crs}").format(
                crs=EPSG4326.authid()
            )
            raise QgsProcessingException(msg)

        destination = QgsCoordinateTransform(
            self.parameterAsPointCrs(parameters, self.DESTINATION, context),
            EPSG4326,
            context.transformContext(),
        ).transform(self.parameterAsPoint(parameters, self.DESTINATION, context))

        if destination.isEmpty():
            msg = self.__tr("Destination point is invalid in {crs}").format(
                crs=EPSG4326.authid()
            )
            raise QgsProcessingException(msg)

        return DataFrame([
            {
                "origin_longitude": origin.x(),
                "origin_latitude": origin.y(),
                "destination_longitude": destination.x(),
                "destination_latitude": destination.y(),
            }
        ])


class CasaGeoToolsRoutesViaAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    INPUT = "INPUT"
    SEQUENCE_EXPRESSION = "SEQUENCE_EXPRESSION"

    OUTPUT_ROUTES = "OUTPUT_ROUTES"

    @override
    def groupId(self) -> str:
        return self.GROUP_ID_SPATIAL

    @override
    def displayName(self) -> str:
        return self.__tr("Routes Via", "Algorithm")

    @override
    def name(self) -> str:
        return "routesvia"

    @override
    def shortDescription(self) -> str:
        return self.__tr("Calculate routes passing through a list of points.")

    @override
    def _initAlgorithm(self, configuration: dict[str, Any] | None) -> None:
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.__tr("Input layer"),
                [Qgis.ProcessingSourceType.VectorPoint],
            )
        )

        self.addParameter(
            QgsProcessingParameterExpression(
                self.SEQUENCE_EXPRESSION,
                self.__tr("Sequence expression"),
                parentLayerParameterName=self.INPUT,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_ROUTES,
                self.__tr("Calculated routes"),
                Qgis.ProcessingSourceType.VectorLine,
            )
        )

    @override
    def validateInputCrs(
        self, parameters: dict[str, Any], context: QgsProcessingContext
    ) -> bool:
        return (
            super().validateInputCrs(parameters, context)
            and self._validateSourceCrsCompatible(self.INPUT, parameters, context)
            and True
        )

    @override
    def _convertInputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> "DataFrame":
        from pandas import DataFrame

        source = self._getSource(self.INPUT, parameters, context)
        sequence_expression = self.parameterAsExpression(
            parameters,
            self.SEQUENCE_EXPRESSION,
            context,
        )

        request = self._geometryFeatureRequest(context, feedback)
        request.addOrderBy(sequence_expression)

        data = [
            {
                "id": feature.id(),
                "position": geometry_as_shapely(feature.geometry()),
            }
            for feature in features_of(source, request)
        ]

        if len(data) > 2:
            feedback.pushWarning(
                self.__tr(
                    "The input layer contains intermediate waypoints. Routing with intermediate waypoints is not implemented yet and these waypoints will be ignored."
                )
            )

        return DataFrame(data)

    @override
    def _calculateResultsMessage(self) -> str:
        return self.__tr("Calculating routes")

    @override
    def _calculateResults(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "GeoDataFrame":
        import casageo.spatial

        client = self.plugin.casaGeoClient(feedback)
        defaults = {}

        try:
            return casageo.spatial.routes(client, queries, defaults)
        except Exception as err:
            raise QgsProcessingException(str(err)) from err

    @override
    def _writeOutputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        results: "DataFrame",
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
            self.OUTPUT_ROUTES,
            context,
            fields,
            # TODO: Make this a MultiLineStringZM with elevation and time datapoints.
            Qgis.WkbType.MultiLineString,
            self.HERE_CRS,
        )
        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(parameters, self.OUTPUT_ROUTES)
            )

        for result in self._resultsOf(results, feedback):
            feature = QgsFeature(fields)
            and_then(result.geometry, geometry_from_shapely, feature.setGeometry)
            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["length"] = result.length
            feature["duration"] = result.duration
            feature["timestamp"] = result.timestamp.isoformat()
            sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)

        return {self.OUTPUT_ROUTES: dest_id}

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
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsPointXY,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,  # pyright: ignore[reportAttributeAccessIssue]
    QgsProcessingFeedback,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExpression,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
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


class CasaGeoToolsRoutesAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    INPUT_LAYER = "INPUT_LAYER"

    ALTERNATIVES = "ALTERNATIVES"
    ALTERNATIVES_FIELD = "ALTERNATIVES_FIELD"

    TRANSPORT_MODE = "TRANSPORT_MODE"
    TRANSPORT_MODE_FIELD = "TRANSPORT_MODE_FIELD"

    ROUTING_MODE = "ROUTING_MODE"
    ROUTING_MODE_FIELD = "ROUTING_MODE_FIELD"

    DEPARTURE_TIME = "DEPARTURE_TIME"
    DEPARTURE_TIME_FIELD = "DEPARTURE_TIME_FIELD"

    ARRIVAL_TIME = "ARRIVAL_TIME"
    ARRIVAL_TIME_FIELD = "ARRIVAL_TIME_FIELD"

    AVOID_FEATURES = "AVOID_FEATURES"
    AVOID_FEATURES_FIELD = "AVOID_FEATURES_FIELD"

    EXCLUDE_COUNTRIES = "EXCLUDE_COUNTRIES"
    EXCLUDE_COUNTRIES_FIELD = "EXCLUDE_COUNTRIES_FIELD"

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

        self._addParameter(
            QgsProcessingParameterNumber(
                self.ALTERNATIVES,
                self.__tr("Number of alternative routes", "Parameter"),
                Qgis.ProcessingNumberParameterType.Integer,
                minValue=MIN_ALTERNATIVES,
                maxValue=MAX_ALTERNATIVES,
                defaultValue=DEFAULT_ALTERNATIVES,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.ALTERNATIVES_FIELD,
                self.__tr("Number of alternative routes (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.Numeric,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterEnum(
                self.TRANSPORT_MODE,
                self.__tr("Transport mode", "Parameter"),
                options=map(trTransportMode, TransportMode),
                defaultValue=trTransportMode(DEFAULT_TRANSPORT_MODE),
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.TRANSPORT_MODE_FIELD,
                self.__tr("Transport mode (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterEnum(
                self.ROUTING_MODE,
                self.__tr("Routing mode", "Parameter"),
                options=map(trRoutingMode, RoutingMode),
                defaultValue=trRoutingMode(DEFAULT_ROUTING_MODE),
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.ROUTING_MODE_FIELD,
                self.__tr("Routing mode (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterDateTime(
                self.DEPARTURE_TIME,
                self.__tr("Departure time", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.DEPARTURE_TIME_FIELD,
                self.__tr("Departure time (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.DateTime,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterDateTime(
                self.ARRIVAL_TIME,
                self.__tr("Arrival time", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.ARRIVAL_TIME_FIELD,
                self.__tr("Arrival time (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.DateTime,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterEnum(
                self.AVOID_FEATURES,
                self.__tr("Avoid features", "Parameter"),
                options=map(trAvoidableFeature, AvoidableFeature),
                allowMultiple=True,
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.AVOID_FEATURES_FIELD,
                self.__tr("Avoid features (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.EXCLUDE_COUNTRIES,
                self.__tr("Exclude countries (separated by commas)", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.EXCLUDE_COUNTRIES_FIELD,
                self.__tr("Exclude countries (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_ROUTES,
                self.__tr("Calculated routes", "Parameter"),
                Qgis.ProcessingSourceType.VectorLine,
            )
        )

        self._addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_NAVIGATIONS,
                self.__tr("Routing navigation points", "Parameter"),
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
                # TODO: Make this a MultiLineStringZM with elevation and time datapoints.
                props.wkbType = Qgis.WkbType.MultiLineString
                props.fields.append([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("length", QMetaType.Type.Double),
                    QgsField("duration", QMetaType.Type.Double),
                    QgsField("timestamp", QMetaType.Type.QDateTime),
                    QgsField("error_code", QMetaType.Type.QString),
                    QgsField("error_message", QMetaType.Type.QString),
                ])
                return props

            case self.OUTPUT_NAVIGATIONS:
                props = QgsProcessingAlgorithm.VectorProperties()
                props.availability = Qgis.ProcessingPropertyAvailability.Available
                props.crs = self.HERE_CRS
                props.wkbType = Qgis.WkbType.Point
                props.fields.append([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("navid", QMetaType.Type.Int),
                    QgsField("placename", QMetaType.Type.QString),
                    QgsField("longitude", QMetaType.Type.Double),
                    QgsField("latitude", QMetaType.Type.Double),
                    # QgsField("datetime", QMetaType.Type.QDateTime),
                ])
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
                # feature["datetime"] = and_then(
                #     getattr(result, f"{prefix}_time"), datetime.isoformat
                # )
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
    def _convertInputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> "DataFrame":
        from pandas import DataFrame

        origin = self._parameterAsTransformedPoint(
            self.ORIGIN, self.HERE_CRS, parameters, context
        )
        destination = self._parameterAsTransformedPoint(
            self.DESTINATION, self.HERE_CRS, parameters, context
        )

        return DataFrame([
            {
                "origin_longitude": origin.x(),
                "origin_latitude": origin.y(),
                "destination_longitude": destination.x(),
                "destination_latitude": destination.y(),
            }
        ])


class CasaGeoToolsRoutesLineSegmentAlgorithm(CasaGeoToolsRoutesAlgorithm):
    __tr = TrMethod()

    @override
    def displayName(self) -> str:
        return self.__tr("Routes (line segments)", "Algorithm")

    @override
    def name(self) -> str:
        return "routes_linesegment"

    @override
    def shortDescription(self) -> str:
        return self.__tr(
            "Calculate routes between two points where the origin and destination are given as a line segment."
        )

    @override
    def _initAlgorithm(self, configuration: dict[str, Any] | None) -> None:
        self.batch_mode = True

        self._addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_LAYER,
                self.__tr("Layer of line segments defining origin and destination"),
                [Qgis.ProcessingSourceType.VectorLine],
            )
        )

        super()._initAlgorithm(configuration)

    @override
    def _convertInputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> "DataFrame":
        from pandas import DataFrame

        def getString(name: str, /) -> str:
            return self.parameterAsString(parameters, name, context)

        def toEndpoints(feature: QgsFeature) -> tuple[QgsPointXY, QgsPointXY]:
            # FIXME: Better error messages.
            try:
                origin, destination = feature.geometry().asPolyline()
            except (TypeError, ValueError) as err:
                msg = self.__tr(
                    "Invalid geometry on feature {featureid}: {error}"
                ).format(featureid=feature.id(), error=err)
                raise QgsProcessingException(msg) from err
            return (origin, destination)

        source = self._getSource(self.INPUT_LAYER, parameters, context)
        fields = [
            alternatives_field := getString(self.ALTERNATIVES_FIELD),
            transport_mode_field := getString(self.TRANSPORT_MODE_FIELD),
            routing_mode_field := getString(self.ROUTING_MODE_FIELD),
            departure_time_field := getString(self.DEPARTURE_TIME_FIELD),
            arrival_time_field := getString(self.ARRIVAL_TIME_FIELD),
            avoid_features_field := getString(self.AVOID_FEATURES_FIELD),
            exclude_countries_field := getString(self.EXCLUDE_COUNTRIES_FIELD),
        ]

        request = self._geometryFeatureRequest(context, feedback)
        request.setSubsetOfAttributes((f for f in fields if f), source.fields())

        data = []
        for feature in features_of(source, request):
            data.append(row := {})
            origin, destination = toEndpoints(feature)
            row["origin_longitude"] = origin.x()
            row["origin_latitude"] = origin.y()
            row["destination_longitude"] = destination.x()
            row["destination_latitude"] = destination.y()
            if f := alternatives_field:
                row["alternatives"] = feature[f]
            if f := transport_mode_field:
                row["transport_mode"] = feature[f]
            if f := routing_mode_field:
                row["routing_mode"] = feature[f]
            if f := departure_time_field:
                row["departure_time"] = pydatetime(feature[f])
            if f := arrival_time_field:
                row["arrival_time"] = pydatetime(feature[f])
            if f := avoid_features_field:
                row["avoid_features"] = feature[f]
            if f := exclude_countries_field:
                row["exclude_countries"] = feature[f]

        return DataFrame(data)


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

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

import contextlib
from typing import TYPE_CHECKING, Any, override

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsExpression,
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
    TrMethod,
    features_of,
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
    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        super().initAlgorithm(configuration)
        if not self.status_ok:
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

        with contextlib.suppress(ImportError):
            self.addParameter(self._paramRanges())
            self.addParameter(self._paramRangesUnit())
            self.addParameter(self._paramTransportMode())
            self.addParameter(self._paramRoutingMode())
            self.addParameter(self._paramDirection())
            self.addParameter(self._paramDateTime())
            self.addParameter(self._paramAvoidFeatures())
            self.addParameter(self._paramExcludeCountries())

        self.addParameter(self._paramOutputIsolines())

    def _paramRanges(self) -> QgsProcessingParameterString:
        # This could be converted into a QgsProcessingParameterMatrix.
        return QgsProcessingParameterString(
            self.RANGES,
            self.__tr("Ranges (separated by semicolons)"),
        )

    def _paramRangesUnit(self) -> QgsProcessingParameterEnum:
        from casageo.spatial import DEFAULT_RANGE_UNIT, RANGE_UNITS

        return QgsProcessingParameterEnum(
            self.RANGES_UNIT,
            self.__tr("Ranges unit"),
            options=RANGE_UNITS,
            defaultValue=DEFAULT_RANGE_UNIT,
            usesStaticStrings=True,
        )

    def _paramTransportMode(self) -> QgsProcessingParameterEnum:
        from casageo.spatial import DEFAULT_TRANSPORT_MODE, TRANSPORT_MODES

        return QgsProcessingParameterEnum(
            self.TRANSPORT_MODE,
            self.__tr("Transport mode"),
            options=TRANSPORT_MODES,
            defaultValue=DEFAULT_TRANSPORT_MODE,
            usesStaticStrings=True,
        )

    def _paramRoutingMode(self) -> QgsProcessingParameterEnum:
        from casageo.spatial import DEFAULT_ROUTING_MODE, ROUTING_MODES

        return QgsProcessingParameterEnum(
            self.ROUTING_MODE,
            self.__tr("Routing mode"),
            options=ROUTING_MODES,
            defaultValue=DEFAULT_ROUTING_MODE,
            usesStaticStrings=True,
        )

    def _paramDirection(self) -> QgsProcessingParameterEnum:
        from casageo.spatial import DEFAULT_DIRECTION, DIRECTION_TYPES

        return QgsProcessingParameterEnum(
            self.DIRECTION,
            self.__tr("Direction"),
            options=DIRECTION_TYPES,
            defaultValue=DEFAULT_DIRECTION,
            usesStaticStrings=True,
        )

    def _paramDateTime(self) -> QgsProcessingParameterDateTime:
        return QgsProcessingParameterDateTime(
            self.DATETIME,
            self.__tr("Time of departure/arrival"),
            optional=True,
        )

    def _paramAvoidFeatures(self) -> QgsProcessingParameterString:
        from casageo.spatial import DEFAULT_AVOID_FEATURES

        return QgsProcessingParameterString(
            self.AVOID_FEATURES,
            self.__tr("Avoid features (separated by commas)"),
            optional=True,
            defaultValue=",".join(DEFAULT_AVOID_FEATURES),
        )

    def _paramExcludeCountries(self) -> QgsProcessingParameterString:
        from casageo.spatial import DEFAULT_EXCLUDE_COUNTRIES

        return QgsProcessingParameterString(
            self.EXCLUDE_COUNTRIES,
            self.__tr("Exclude countries (separated by commas)"),
            optional=True,
            defaultValue=",".join(DEFAULT_EXCLUDE_COUNTRIES),
        )

    def _paramOutputIsolines(self) -> QgsProcessingParameterFeatureSink:
        return QgsProcessingParameterFeatureSink(
            self.OUTPUT_ISOLINES,
            self.__tr("Calculated isolines"),
            Qgis.ProcessingSourceType.VectorPolygon,
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
                props.crs = QgsCoordinateReferenceSystem.fromEpsgId(4326)
                props.fields = QgsFields([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("rangetype", QMetaType.Type.QString),
                    QgsField("rangeunit", QMetaType.Type.QString),
                    QgsField("rangevalue", QMetaType.Type.Double),
                    QgsField("timestamp", QMetaType.Type.QDateTime),
                    # QgsField("error_code", QMetaType.Type.QString),
                    # QgsField("error_message", QMetaType.Type.QString),
                ])
                props.wkbType = Qgis.WkbType.Polygon
                return props

        return super().sinkProperties(sink, parameters, context, sourceProperties)

    @override
    def validateInputCrs(
        self, parameters: dict[str, Any], context: QgsProcessingContext
    ) -> bool:
        isTransformationPossible = QgsCoordinateTransform.isTransformationPossible
        EPSG4326 = QgsCoordinateReferenceSystem.fromEpsgId(4326)

        if (
            (src := self.parameterAsSource(parameters, self.INPUT, context)) is not None
            and (crs := src.sourceCrs()).isValid()
            and not isTransformationPossible(crs, EPSG4326)
        ):
            return False

        return super().validateInputCrs(parameters, context)

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
        if source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        into_epsg4326 = QgsCoordinateTransform(
            source.sourceCrs(),
            QgsCoordinateReferenceSystem.fromEpsgId(4326),
            context.transformContext(),
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

        client = self.plugin.casaGeoClient()

        ranges = self.parameterAsString(parameters, self.RANGES, context).split(";")
        ranges_unit = self.parameterAsString(parameters, self.RANGES_UNIT, context)
        transport_index = self.parameterAsEnum(parameters, self.TRANSPORT_MODE, context)
        routing_index = self.parameterAsEnum(parameters, self.ROUTING_MODE, context)
        direction_index = self.parameterAsEnum(parameters, self.DIRECTION, context)
        date_and_time = self.parameterAsDateTime(parameters, self.DATETIME, context)
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
            "departure_time": pydatetime(date_and_time),
            "arrival_time": pydatetime(date_and_time),
            "traffic": date_and_time.isValid(),
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

        sink_name = self.OUTPUT_ISOLINES
        sink_props = self.sinkProperties(sink_name, parameters, context, {})
        sink, dest_id = self.parameterAsSink(
            parameters,
            sink_name,
            context,
            sink_props.fields,
            sink_props.wkbType,
            sink_props.crs,
        )
        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(parameters, self.OUTPUT_ISOLINES)
            )

        result: Any  # Make Pyright shut up about the named tuples.
        for result in results.itertuples():
            if result.error_code is not None:
                feedback.reportError(
                    self.__tr("Error ({code}): {message}").format(
                        code=result.error_code, message=result.error_message
                    )
                )
                continue

            feature = QgsFeature(sink_props.fields)
            feature.setGeometry(geometry_from_shapely(result.geometry))
            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["rangetype"] = result.rangetype
            feature["rangeunit"] = result.rangeunit
            feature["rangevalue"] = result.rangevalue
            feature["timestamp"] = result.timestamp.isoformat()
            sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)

        return {self.OUTPUT_ISOLINES: dest_id}


class CasaGeoToolsRoutesAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    ORIGIN = "ORIGIN"
    DESTINATION = "DESTINATION"
    ALTERNATIVES = "ALTERNATIVES"
    TRANSPORT_MODE = "TRANSPORT_MODE"
    ROUTING_MODE = "ROUTING_MODE"
    DEPARTURE_TIME = "DEPARTURE_TIME"
    ARRIVAL_TIME = "ARRIVAL_TIME"
    AVOID_FEATURES = "AVOID_FEATURES"
    EXCLUDE_COUNTRIES = "EXCLUDE_COUNTRIES"

    OUTPUT_ROUTES = "OUTPUT_ROUTES"

    @override
    def groupId(self) -> str:
        return self.GROUP_ID_SPATIAL

    @override
    def displayName(self) -> str:
        return self.__tr("Routes", "Algorithm")

    @override
    def name(self) -> str:
        return "routes"

    @override
    def shortDescription(self) -> str:
        return self.__tr("Calculate routes between two locations.")

    @override
    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        super().initAlgorithm(configuration)
        if not self.status_ok:
            return

        if configuration is None:
            configuration = {}

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

        with contextlib.suppress(ImportError):
            self.addParameter(self._paramAlternatives())
            self.addParameter(self._paramTransportMode())
            self.addParameter(self._paramRoutingMode())
            self.addParameter(self._paramDepartureTime())
            self.addParameter(self._paramArrivalTime())
            self.addParameter(self._paramAvoidFeatures())
            self.addParameter(self._paramExcludeCountries())

        self.addParameter(self._paramOutputRoutes())

    def _paramAlternatives(self):
        from casageo.spatial import (
            DEFAULT_ALTERNATIVES,
            MAX_ALTERNATIVES,
            MIN_ALTERNATIVES,
        )

        return QgsProcessingParameterNumber(
            self.ALTERNATIVES,
            self.__tr("Number of alternative routes", "Parameter"),
            Qgis.ProcessingNumberParameterType.Integer,
            minValue=MIN_ALTERNATIVES,
            maxValue=MAX_ALTERNATIVES,
            defaultValue=DEFAULT_ALTERNATIVES,
        )

    def _paramTransportMode(self) -> QgsProcessingParameterEnum:
        from casageo.spatial import DEFAULT_TRANSPORT_MODE, TRANSPORT_MODES

        return QgsProcessingParameterEnum(
            self.TRANSPORT_MODE,
            self.__tr("Transport mode"),
            options=TRANSPORT_MODES,
            defaultValue=DEFAULT_TRANSPORT_MODE,
            usesStaticStrings=True,
        )

    def _paramRoutingMode(self) -> QgsProcessingParameterEnum:
        from casageo.spatial import DEFAULT_ROUTING_MODE, ROUTING_MODES

        return QgsProcessingParameterEnum(
            self.ROUTING_MODE,
            self.__tr("Routing mode"),
            options=ROUTING_MODES,
            defaultValue=DEFAULT_ROUTING_MODE,
            usesStaticStrings=True,
        )

    def _paramDepartureTime(self):
        return QgsProcessingParameterDateTime(
            self.DEPARTURE_TIME,
            self.__tr("Departure time", "Parameter"),
            optional=True,
        )

    def _paramArrivalTime(self):
        return QgsProcessingParameterDateTime(
            self.ARRIVAL_TIME,
            self.__tr("Arrival time", "Parameter"),
            optional=True,
        )

    def _paramAvoidFeatures(self) -> QgsProcessingParameterString:
        from casageo.spatial import DEFAULT_AVOID_FEATURES

        return QgsProcessingParameterString(
            self.AVOID_FEATURES,
            self.__tr("Avoid features (separated by commas)"),
            optional=True,
            defaultValue=",".join(DEFAULT_AVOID_FEATURES),
        )

    def _paramExcludeCountries(self) -> QgsProcessingParameterString:
        from casageo.spatial import DEFAULT_EXCLUDE_COUNTRIES

        return QgsProcessingParameterString(
            self.EXCLUDE_COUNTRIES,
            self.__tr("Exclude countries (separated by commas)"),
            optional=True,
            defaultValue=",".join(DEFAULT_EXCLUDE_COUNTRIES),
        )

    def _paramOutputRoutes(self) -> QgsProcessingParameterFeatureSink:
        return QgsProcessingParameterFeatureSink(
            self.OUTPUT_ROUTES,
            self.__tr("Calculated routes", "Parameter"),
            Qgis.ProcessingSourceType.VectorLine,
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
                props.crs = QgsCoordinateReferenceSystem.fromEpsgId(4326)
                props.fields = QgsFields([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("length", QMetaType.Type.Double),
                    QgsField("duration", QMetaType.Type.Double),
                    QgsField("timestamp", QMetaType.Type.QDateTime),
                    # QgsField("error_code", QMetaType.Type.QString),
                    # QgsField("error_message", QMetaType.Type.QString),
                ])
                # TODO: Make this a MultiLineStringZM with elevation and time datapoints.
                props.wkbType = Qgis.WkbType.MultiLineString
                return props

        return super().sinkProperties(sink, parameters, context, sourceProperties)

    @override
    def validateInputCrs(
        self, parameters: dict[str, Any], context: QgsProcessingContext
    ) -> bool:
        isTransformationPossible = QgsCoordinateTransform.isTransformationPossible
        EPSG4326 = QgsCoordinateReferenceSystem.fromEpsgId(4326)

        orig_crs = self.parameterAsPointCrs(parameters, self.ORIGIN, context)
        if orig_crs.isValid() and not isTransformationPossible(orig_crs, EPSG4326):
            return False

        dest_crs = self.parameterAsPointCrs(parameters, self.DESTINATION, context)
        if dest_crs.isValid() and not isTransformationPossible(dest_crs, EPSG4326):
            return False

        return super().validateInputCrs(parameters, context)

    @override
    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, Any]:
        if feedback is None:
            feedback = QgsProcessingFeedback(logFeedback=False)

        feedback.setProgressText(self.__tr("Converting input geometries"))
        queries = self._convertInputGeometries(parameters, context, feedback)

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

    def _calculateRoutes(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "GeoDataFrame":
        import casageo.spatial
        import casageo.tools
        from casageo.spatial import (
            ROUTING_MODES,
            TRANSPORT_MODES,
        )

        client = self.plugin.casaGeoClient()

        alternatives = self.parameterAsInt(parameters, self.ALTERNATIVES, context)
        transport_index = self.parameterAsEnum(parameters, self.TRANSPORT_MODE, context)
        routing_index = self.parameterAsEnum(parameters, self.ROUTING_MODE, context)
        departure_time = self.parameterAsDateTime(
            parameters, self.DEPARTURE_TIME, context
        )
        arrival_time = self.parameterAsDateTime(parameters, self.ARRIVAL_TIME, context)
        avoid_features = self.parameterAsString(
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
            "avoid_features": avoid_features,
            "exclude_countries": exclude_countries,
        }

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

        sink_name = self.OUTPUT_ROUTES
        sink_props = self.sinkProperties(sink_name, parameters, context, {})
        sink, dest_id = self.parameterAsSink(
            parameters,
            sink_name,
            context,
            sink_props.fields,
            sink_props.wkbType,
            sink_props.crs,
        )
        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(parameters, self.OUTPUT_ROUTES)
            )

        result: Any  # Make Pyright shut up about the named tuples.
        for result in results.itertuples():
            if result.error_code is not None:
                feedback.reportError(
                    self.__tr("Error ({code}): {message}").format(
                        code=result.error_code, message=result.error_message
                    )
                )
                continue

            feature = QgsFeature(sink_props.fields)
            feature.setGeometry(geometry_from_shapely(result.geometry))
            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["length"] = result.length
            feature["duration"] = result.duration
            feature["timestamp"] = result.timestamp.isoformat()
            sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)

        return {self.OUTPUT_ROUTES: dest_id}


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
    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        super().initAlgorithm(configuration)
        if not self.status_ok:
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
        if source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        expr = QgsExpression(
            self.parameterAsExpression(
                parameters,
                self.SEQUENCE_EXPRESSION,
                context,
            )
        )

        if expr.hasParserError():
            raise QgsProcessingException(
                self.__tr("Invalid sequence expression: {error}").format(
                    error=expr.parserErrorString(),
                )
            )

        into_epsg4326 = QgsCoordinateTransform(
            source.sourceCrs(),
            QgsCoordinateReferenceSystem.fromEpsgId(4326),
            context.transformContext(),
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
            sequence_id = -1  # FIXME

            # ctx = QgsExpressionContext()
            # ctx.setFeature(feature)
            # expr.evaluate()

            data.append({
                "position_longitude": position.x(),
                "position_latitude": position.y(),
                "sequence_id": sequence_id,
            })

        if len(data) > 2:
            feedback.pushWarning(
                self.__tr(
                    "The input layer contains intermediate waypoints. Routing with intermediate waypoints is not implemented yet and these waypoints will be ignored."
                )
            )

        return DataFrame(data).sort_values("sequence_id", ignore_index=True)

    def _calculateRoutes(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "GeoDataFrame":
        import casageo.spatial
        import casageo.tools

        client = self.plugin.casaGeoClient()
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
            self.OUTPUT_ROUTES,
            context,
            fields,
            # TODO: Make this a MultiLineStringZM with elevation and time datapoints.
            Qgis.WkbType.MultiLineString,
            QgsCoordinateReferenceSystem.fromEpsgId(4326),
        )
        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(parameters, self.OUTPUT_ROUTES)
            )

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

        return {self.OUTPUT_ROUTES: dest_id}

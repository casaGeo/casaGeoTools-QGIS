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
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,  # pyright: ignore[reportAttributeAccessIssue]
    QgsProcessingFeedback,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterPoint,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QDateTime, QMetaType

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


class CasaGeoToolsIsolineAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    INPUT_LAYER = "INPUT_LAYER"

    RANGES = "RANGES"
    RANGES_FIELD = "RANGES_FIELD"

    RANGES_UNIT = "RANGES_UNIT"
    RANGES_UNIT_FIELD = "RANGES_UNIT_FIELD"

    TRANSPORT_MODE = "TRANSPORT_MODE"
    TRANSPORT_MODE_FIELD = "TRANSPORT_MODE_FIELD"

    ROUTING_MODE = "ROUTING_MODE"
    ROUTING_MODE_FIELD = "ROUTING_MODE_FIELD"

    DIRECTION = "DIRECTION"
    DIRECTION_FIELD = "DIRECTION_FIELD"

    DATETIME = "DATETIME"
    DATETIME_FIELD = "DATETIME_FIELD"

    AVOID_FEATURES = "AVOID_FEATURES"
    AVOID_FEATURES_FIELD = "AVOID_FEATURES_FIELD"

    EXCLUDE_COUNTRIES = "EXCLUDE_COUNTRIES"
    EXCLUDE_COUNTRIES_FIELD = "EXCLUDE_COUNTRIES_FIELD"

    OUTPUT_ISOLINES = "OUTPUT_ISOLINES"
    OUTPUT_NAVIGATIONS = "OUTPUT_NAVIGATIONS"

    @override
    def groupId(self) -> str:
        return self.GROUP_ID_SPATIAL

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

        # This could be converted into a QgsProcessingParameterMatrix.
        self._addParameter(
            QgsProcessingParameterString(
                self.RANGES,
                self.__tr("Ranges (separated by semicolons)", "Parameter"),
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.RANGES_FIELD,
                self.__tr("Ranges (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.Any,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterEnum(
                self.RANGES_UNIT,
                self.__tr("Ranges unit", "Parameter"),
                options=map(trRangeUnit, RangeUnit),
                defaultValue=trRangeUnit(DEFAULT_RANGE_UNIT),
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.RANGES_UNIT_FIELD,
                self.__tr("Ranges unit (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
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
            QgsProcessingParameterEnum(
                self.DIRECTION,
                self.__tr("Direction", "Parameter"),
                options=map(trDirectionType, DirectionType),
                defaultValue=trDirectionType(DEFAULT_DIRECTION),
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.DIRECTION_FIELD,
                self.__tr("Direction (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterDateTime(
                self.DATETIME,
                self.__tr("Time of departure/arrival", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.DATETIME_FIELD,
                self.__tr("Time of departure/arrival (field)", "Parameter"),
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
                self.OUTPUT_ISOLINES,
                self.__tr("Isoline polygons", "Parameter"),
                Qgis.ProcessingSourceType.VectorPolygon,
            )
        )

        self._addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_NAVIGATIONS,
                self.__tr("Isoline navigation points", "Parameter"),
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
                props.wkbType = Qgis.WkbType.MultiPolygon
                props.fields.append([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("rangetype", QMetaType.Type.QString),
                    QgsField("rangeunit", QMetaType.Type.QString),
                    QgsField("rangevalue", QMetaType.Type.Double),
                    QgsField("direction", QMetaType.Type.QString),
                    QgsField("location_placename", QMetaType.Type.QString),
                    QgsField("location_longitude", QMetaType.Type.Double),
                    QgsField("location_latitude", QMetaType.Type.Double),
                    # QgsField("location_datetime", QMetaType.Type.QDateTime),
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
                    QgsField("placename", QMetaType.Type.QString),
                    QgsField("longitude", QMetaType.Type.Double),
                    QgsField("latitude", QMetaType.Type.Double),
                    # QgsField("datetime", QMetaType.Type.QDateTime),
                ])
                return props

        return super().sinkProperties(sink, parameters, context, sourceProperties)

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
            # feature["location_datetime"] = and_then(center(result, "time"), isoformat)
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
            # feature["datetime"] = and_then(center(result, "time"), isoformat)
            addFeature(navigations, feature)

        return {
            isolines.name: isolines.dest,
            navigations.name: navigations.dest,
        }


class CasaGeoToolsIsolineSingleAlgorithm(CasaGeoToolsIsolineAlgorithm):
    __tr = TrMethod()

    LOCATION = "LOCATION"

    @override
    def displayName(self) -> str:
        return self.__tr("Isolines", "Algorithm")

    @override
    def name(self) -> str:
        return "isolines_single"

    @override
    def _initAlgorithm(self, configuration: dict[str, Any] | None) -> None:
        self._addParameter(
            QgsProcessingParameterPoint(
                self.LOCATION,
                self.__tr("Location", "Parameter"),
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

        position = self._parameterAsTransformedPoint(
            self.LOCATION, self.HERE_CRS, parameters, context
        )

        return DataFrame([
            {
                "position_longitude": position.x(),
                "position_latitude": position.y(),
            }
        ])


class CasaGeoToolsIsolineBatchAlgorithm(CasaGeoToolsIsolineAlgorithm):
    __tr = TrMethod()

    @override
    def displayName(self) -> str:
        return self.__tr("Isolines (batch)", "Algorithm")

    @override
    def name(self) -> str:
        return "isolines_batch"

    @override
    def _initAlgorithm(self, configuration: dict[str, Any] | None) -> None:
        self.batch_mode = True

        self._addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_LAYER,
                self.__tr("Input layer", "Parameter"),
                [Qgis.ProcessingSourceType.VectorPoint],
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

        source = self._getSource(self.INPUT_LAYER, parameters, context)
        fields = [
            ranges_field := getString(self.RANGES_FIELD),
            ranges_unit_field := getString(self.RANGES_UNIT_FIELD),
            transport_mode_field := getString(self.TRANSPORT_MODE_FIELD),
            routing_mode_field := getString(self.ROUTING_MODE_FIELD),
            direction_field := getString(self.DIRECTION_FIELD),
            datetime_field := getString(self.DATETIME_FIELD),
            avoid_features_field := getString(self.AVOID_FEATURES_FIELD),
            exclude_countries_field := getString(self.EXCLUDE_COUNTRIES_FIELD),
        ]

        request = self._geometryFeatureRequest(context, feedback)
        request.setSubsetOfAttributes((f for f in fields if f), source.fields())

        return DataFrame([
            {
                "id": feature.id(),
                "position": geometry_as_shapely(feature.geometry()),
                "ranges": (
                    [float(r) for r in feature[f].split(";")]
                    if (f := ranges_field)
                    else None
                ),
                "ranges_unit": feature[f] if (f := ranges_unit_field) else None,
                "transport_mode": feature[f] if (f := transport_mode_field) else None,
                "routing_mode": feature[f] if (f := routing_mode_field) else None,
                "direction": feature[f] if (f := direction_field) else None,
                "departure_time": (
                    pydatetime(feature[f]) if (f := datetime_field) else None
                ),
                "arrival_time": (
                    pydatetime(feature[f]) if (f := datetime_field) else None
                ),
                "traffic": (
                    QDateTime.isValid(feature[f]) if (f := datetime_field) else None
                ),
                "avoid_features": feature[f] if (f := avoid_features_field) else None,
                "exclude_countries": (
                    feature[f] if (f := exclude_countries_field) else None
                ),
            }
            for feature in features_of(source, request)
        ])

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
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,  # pyright: ignore[reportAttributeAccessIssue]
    QgsProcessingFeedback,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
)
from qgis.PyQt.QtCore import QMetaType

from ..utils import TrMethod, features_of, geometry_from_shapely
from . import CasaGeoToolsProcessingAlgorithm

if TYPE_CHECKING:
    from geopandas import GeoDataFrame
    from pandas import DataFrame


class CasaGeoToolsAddressSearchAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    @override
    def groupId(self) -> str:
        return self.GROUP_ID_CODER

    @override
    def displayName(self) -> str:
        return self.__tr("Address search", "Algorithm")

    @override
    def name(self) -> str:
        return "address"

    @override
    def shortDescription(self) -> str:
        return self.__tr("Geocodes addresses.")

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
                [Qgis.ProcessingSourceType.Vector],
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.__tr("Output layer"),
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
            case self.OUTPUT:
                props = QgsProcessingAlgorithm.VectorProperties()
                props.availability = Qgis.ProcessingPropertyAvailability.Available
                props.crs = QgsCoordinateReferenceSystem.fromEpsgId(4326)
                props.fields = QgsFields([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("address", QMetaType.Type.QString),
                    QgsField("resulttype", QMetaType.Type.QString),
                    QgsField("distance", QMetaType.Type.Double),
                    QgsField("relevance", QMetaType.Type.Double),
                    QgsField("timestamp", QMetaType.Type.QDateTime),
                    # QgsField("error_code", QMetaType.Type.QString),
                    # QgsField("error_message", QMetaType.Type.QString),
                ])
                props.wkbType = Qgis.WkbType.Point
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
            feedback.setProgressText(self.__tr("Geocoding addresses"))
            results = self._geocodeAddresses(parameters, context, feedback, queries)

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

        return DataFrame([feature.attributeMap() for feature in features_of(source)])

    def _geocodeAddresses(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "GeoDataFrame":
        import casageo.coder
        import casageo.tools

        client = self.plugin.casaGeoClient()
        defaults = {}

        try:
            return casageo.coder.address(client, queries, defaults)
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

        sink_name = self.OUTPUT
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
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        last_id_and_address = (None, None)
        result: Any  # Make Pyright shut up about the named tuples.
        for result in results.itertuples():
            # This weirdness is necessary because the library returns
            # multiple results when the location has multiple navigation
            # points.
            if (result.id, result.address) == last_id_and_address:
                continue
            last_id_and_address = (result.id, result.address)

            if result.error_code is not None:
                feedback.reportError(
                    self.__tr("Error ({code}): {message}").format(
                        code=result.error_code, message=result.error_message
                    )
                )
                continue

            feature = QgsFeature(sink_props.fields)
            feature.setGeometry(geometry_from_shapely(result.position))
            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["address"] = result.address
            feature["resulttype"] = result.resulttype
            feature["distance"] = result.distance
            feature["relevance"] = result.relevance
            feature["timestamp"] = result.timestamp.isoformat()
            sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)

        return {self.OUTPUT: dest_id}


class CasaGeoToolsPOISearchAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    LIMIT = "LIMIT"

    @override
    def groupId(self) -> str:
        return self.GROUP_ID_CODER

    @override
    def displayName(self) -> str:
        return self.__tr("POI Search", "Algorithm")

    @override
    def name(self) -> str:
        return "poisearch"

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
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.__tr("Output layer"),
                Qgis.ProcessingSourceType.VectorPoint,
            )
        )

        with contextlib.suppress(ImportError):
            self.addParameter(self._paramLimit())

    def _paramLimit(self) -> QgsProcessingParameterNumber:
        from casageo.coder import DEFAULT_LIMIT, MAX_LIMIT, MIN_LIMIT

        return QgsProcessingParameterNumber(
            self.LIMIT,
            self.__tr("Limit"),
            Qgis.ProcessingNumberParameterType.Integer,
            defaultValue=DEFAULT_LIMIT,
            minValue=MIN_LIMIT,
            maxValue=MAX_LIMIT,
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
            case self.OUTPUT:
                props = QgsProcessingAlgorithm.VectorProperties()
                props.availability = Qgis.ProcessingPropertyAvailability.Available
                props.crs = QgsCoordinateReferenceSystem.fromEpsgId(4326)
                props.fields = QgsFields([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("title", QMetaType.Type.QString),
                    QgsField("resulttype", QMetaType.Type.QString),
                    QgsField("distance", QMetaType.Type.Double),
                    QgsField("timestamp", QMetaType.Type.QDateTime),
                    # QgsField("error_code", QMetaType.Type.QString),
                    # QgsField("error_message", QMetaType.Type.QString),
                ])
                props.wkbType = Qgis.WkbType.Point
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
            feedback.setProgressText(self.__tr("Searching for POIs"))
            results = self._searchForPOIs(parameters, context, feedback, queries)

        feedback.setProgressText(self.__tr("Converting results"))
        return self._writeOutputGeometries(parameters, context, feedback, results)

        # """
        # Here is where the processing itself takes place.
        # """
        #
        # # Retrieve the feature source and sink. The 'dest_id' variable is used
        # # to uniquely identify the feature sink, and must be included in the
        # # dictionary returned by the processAlgorithm function.
        # source = self.parameterAsSource(parameters, self.INPUT, context)
        # (sink, dest_id) = self.parameterAsSink(
        #     parameters,
        #     self.OUTPUT,
        #     context,
        #     source.fields(),
        #     source.wkbType(),
        #     source.sourceCrs(),
        # )
        #
        # # Compute the number of steps to display within the progress bar and
        # # get features from source
        # total = 100.0 / source.featureCount() if source.featureCount() else 0
        # features = source.getFeatures()
        #
        # for current, feature in enumerate(features):
        #     # Stop the algorithm if cancel button has been clicked
        #     if feedback.isCanceled():
        #         break
        #
        #     # Add a feature in the sink
        #     sink.addFeature(feature, QgsFeatureSink.FastInsert)
        #
        #     # Update the progress bar
        #     feedback.setProgress(int(current * total))
        #
        # # Return the results of the algorithm. In this case our only result is
        # # the feature sink which contains the processed features, but some
        # # algorithms may return multiple feature sinks, calculated numeric
        # # statistics, etc. These should all be included in the returned
        # # dictionary, with keys matching the feature corresponding parameter
        # # or output names.

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

    def _searchForPOIs(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "GeoDataFrame":
        import casageo.coder
        import casageo.tools

        client = self.plugin.casaGeoClient()
        defaults = {"limit": self.parameterAsInt(parameters, self.LIMIT, context)}

        try:
            return casageo.coder.poi(client, queries, defaults)
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

        sink_name = self.OUTPUT
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
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        last_id_and_title = (None, None)
        result: Any  # Make Pyright shut up about the named tuples.
        for result in results.itertuples():
            # This weirdness is necessary because the library returns
            # multiple results when the location has multiple navigation
            # points.
            if (result.id, result.title) == last_id_and_title:
                continue
            last_id_and_title = (result.id, result.title)

            if result.error_code is not None:
                feedback.reportError(
                    self.__tr("Error ({code}): {message}").format(
                        code=result.error_code, message=result.error_message
                    )
                )
                continue

            feature = QgsFeature(sink_props.fields)
            feature.setGeometry(geometry_from_shapely(result.position))
            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["title"] = result.title
            feature["resulttype"] = result.resulttype
            feature["distance"] = result.distance
            feature["timestamp"] = result.timestamp.isoformat()
            sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)

        return {self.OUTPUT: dest_id}

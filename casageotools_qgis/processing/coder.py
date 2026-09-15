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
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QMetaType

from ..utils import (
    ProcessingFeatureSinkDefinition,
    TrMethod,
    features_of,
    geometry_as_shapely,
    geometry_from_shapely,
)
from . import CasaGeoToolsProcessingAlgorithm

if TYPE_CHECKING:
    from geopandas import GeoDataFrame
    from pandas import DataFrame


class CasaGeoToolsAddressSearchAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    INPUT = "INPUT"
    INPUT_ADDRESS_FIELD = "INPUT_ADDRESS_FIELD"
    INPUT_COUNTRY_FIELD = "INPUT_COUNTRY_FIELD"
    INPUT_STATE_FIELD = "INPUT_STATE_FIELD"
    INPUT_COUNTY_FIELD = "INPUT_COUNTY_FIELD"
    INPUT_CITY_FIELD = "INPUT_CITY_FIELD"
    INPUT_DISTRICT_FIELD = "INPUT_DISTRICT_FIELD"
    INPUT_STREET_FIELD = "INPUT_STREET_FIELD"
    INPUT_HOUSENUMBER_FIELD = "INPUT_HOUSENUMBER_FIELD"
    INPUT_POSTALCODE_FIELD = "INPUT_POSTALCODE_FIELD"
    INPUT_USE_GEOMETRY = "INPUT_USE_GEOMETRY"

    LIMIT = "LIMIT"
    ADDRESS_NAMES_MODE = "ADDRESS_NAMES_MODE"
    POSTAL_CODE_MODE = "POSTAL_CODE_MODE"
    COUNTRIES = "COUNTRIES"

    OUTPUT_LOCATIONS = "OUTPUT_LOCATIONS"
    OUTPUT_NAVIGATIONS = "OUTPUT_NAVIGATIONS"

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

        try:
            from casageo.coder import (
                DEFAULT_ADDRESS_NAMES_MODE,
                DEFAULT_LIMIT,
                DEFAULT_POSTAL_CODE_MODE,
                MAX_LIMIT,
                MIN_LIMIT,
                AddressNamesMode,
                PostalCodeMode,
            )
        except ImportError as err:
            self.status_ok = False
            self.status_message = str(err)
            return

        translator = self.plugin.coderTranslator
        trAddressNamesMode = translator.translateAddressNamesMode
        trPostalCodeMode = translator.translatePostalCodeMode

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.__tr("Input layer"),
                [Qgis.ProcessingSourceType.Vector],
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.INPUT_ADDRESS_FIELD,
                self.__tr("Free-form address field"),
                parentLayerParameterName=self.INPUT,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.INPUT_COUNTRY_FIELD,
                self.__tr("Country field"),
                parentLayerParameterName=self.INPUT,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.INPUT_STATE_FIELD,
                self.__tr("State field"),
                parentLayerParameterName=self.INPUT,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.INPUT_COUNTY_FIELD,
                self.__tr("County field"),
                parentLayerParameterName=self.INPUT,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.INPUT_CITY_FIELD,
                self.__tr("City field"),
                parentLayerParameterName=self.INPUT,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.INPUT_DISTRICT_FIELD,
                self.__tr("District field"),
                parentLayerParameterName=self.INPUT,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.INPUT_STREET_FIELD,
                self.__tr("Street field"),
                parentLayerParameterName=self.INPUT,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.INPUT_HOUSENUMBER_FIELD,
                self.__tr("House number field"),
                parentLayerParameterName=self.INPUT,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.INPUT_POSTALCODE_FIELD,
                self.__tr("Postal code field"),
                parentLayerParameterName=self.INPUT,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_USE_GEOMETRY,
                self.__tr("Search around feature location"),
                defaultValue=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.LIMIT,
                self.__tr("Limit"),
                Qgis.ProcessingNumberParameterType.Integer,
                defaultValue=DEFAULT_LIMIT,
                minValue=MIN_LIMIT,
                maxValue=MAX_LIMIT,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.COUNTRIES,
                self.__tr("Search countries (separated by commas)"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.ADDRESS_NAMES_MODE,
                self.__tr("Address names mode"),
                options=map(trAddressNamesMode, AddressNamesMode),
                defaultValue=trAddressNamesMode(DEFAULT_ADDRESS_NAMES_MODE),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.POSTAL_CODE_MODE,
                self.__tr("Postal code mode"),
                options=map(trPostalCodeMode, PostalCodeMode),
                defaultValue=trPostalCodeMode(DEFAULT_POSTAL_CODE_MODE),
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_LOCATIONS,
                self.__tr("Geocoded locations"),
                Qgis.ProcessingSourceType.VectorPoint,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_NAVIGATIONS,
                self.__tr("Geocoded navigation points"),
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
            case self.OUTPUT_LOCATIONS | self.OUTPUT_NAVIGATIONS:
                props = QgsProcessingAlgorithm.VectorProperties()
                props.availability = Qgis.ProcessingPropertyAvailability.Available
                props.crs = QgsCoordinateReferenceSystem.fromEpsgId(4326)
                props.fields = QgsFields([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("navid", QMetaType.Type.Int),
                    QgsField("address", QMetaType.Type.QString),
                    QgsField("resulttype", QMetaType.Type.QString),
                    QgsField("distance", QMetaType.Type.Double),
                    QgsField("relevance", QMetaType.Type.Double),
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
    def checkParameterValues(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
    ) -> tuple[bool, str]:
        if not any(
            self.parameterAsString(parameters, name, context)
            for name in (
                self.INPUT_ADDRESS_FIELD,
                self.INPUT_COUNTRY_FIELD,
                self.INPUT_STATE_FIELD,
                self.INPUT_COUNTY_FIELD,
                self.INPUT_CITY_FIELD,
                self.INPUT_DISTRICT_FIELD,
                self.INPUT_STREET_FIELD,
                self.INPUT_HOUSENUMBER_FIELD,
                self.INPUT_POSTALCODE_FIELD,
            )
        ):
            return False, self.__tr("At least one input field must be specified")

        return super().checkParameterValues(parameters, context)

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

        def getString(name: str, /) -> str:
            return self.parameterAsString(parameters, name, context)

        source = self._getSource(self.INPUT, parameters, context)
        param_fields = {
            "address": getString(self.INPUT_ADDRESS_FIELD),
            "country": getString(self.INPUT_COUNTRY_FIELD),
            "state": getString(self.INPUT_STATE_FIELD),
            "county": getString(self.INPUT_COUNTY_FIELD),
            "city": getString(self.INPUT_CITY_FIELD),
            "district": getString(self.INPUT_DISTRICT_FIELD),
            "street": getString(self.INPUT_STREET_FIELD),
            "housenumber": getString(self.INPUT_HOUSENUMBER_FIELD),
            "postalcode": getString(self.INPUT_POSTALCODE_FIELD),
        }
        use_geometry = self.parameterAsBoolean(
            parameters, self.INPUT_USE_GEOMETRY, context
        )

        if use_geometry:
            request = self._epsg4326FeatureRequest(context, feedback)
        else:
            request = self._simpleFeatureRequest(context, feedback)
            request.setFlags(Qgis.FeatureRequestFlag.NoGeometry)

        request.setSubsetOfAttributes(
            (f for f in param_fields.values() if f),
            source.fields(),
        )

        data = [
            {
                "id": feature.id(),
                **{
                    param: feature[field] if field else None
                    for param, field in param_fields.items()
                },
                "position": (
                    geometry_as_shapely(feature.geometry())
                    if feature.hasGeometry()
                    else None
                ),
            }
            for feature in features_of(source, request)
        ]

        return DataFrame(data)

    def _geocodeAddresses(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "GeoDataFrame":
        import casageo.coder
        import casageo.tools
        from casageo.coder import AddressNamesMode, PostalCodeMode

        ADDRESS_NAMES_MODES = list(AddressNamesMode)
        POSTAL_CODE_MODES = list(PostalCodeMode)

        limit = self.parameterAsInt(parameters, self.LIMIT, context)
        address_names_mode_index = self.parameterAsEnum(
            parameters, self.ADDRESS_NAMES_MODE, context
        )
        postal_code_mode_index = self.parameterAsEnum(
            parameters, self.POSTAL_CODE_MODE, context
        )
        countries = self.parameterAsString(parameters, self.COUNTRIES, context)

        client = self.plugin.casaGeoClient(feedback)
        defaults = {
            "limit": limit,
            "countries": countries,
            "address_names_mode": ADDRESS_NAMES_MODES[address_names_mode_index],
            "postal_code_mode": POSTAL_CODE_MODES[postal_code_mode_index],
        }

        try:
            return casageo.coder.address(
                client,
                queries,
                defaults,
            )
        except Exception as err:
            raise QgsProcessingException(str(err)) from err

    def _writeOutputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        results: "GeoDataFrame",
    ) -> dict[str, str]:
        """Convert results to features and write them to the feature sink."""

        locations = self._getSink(self.OUTPUT_LOCATIONS, parameters, context)
        navigations = self._getSink(self.OUTPUT_NAVIGATIONS, parameters, context)

        def addFeature(
            output: ProcessingFeatureSinkDefinition,
            result: Any,
            geometryfield: str,
        ) -> None:
            feature = QgsFeature(output.props.fields)
            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["navid"] = result.navid
            feature["address"] = result.address
            feature["resulttype"] = result.resulttype
            feature["distance"] = result.distance
            feature["relevance"] = result.relevance
            feature["timestamp"] = result.timestamp.isoformat()
            feature["error_code"] = result.error_code
            feature["error_message"] = result.error_message

            if (geom := result[geometryfield]) is not None:
                feature.setGeometry(geometry_from_shapely(geom))

            if not output.sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert):
                error = self.writeFeatureError(output.sink, parameters, output.name)
                feedback.reportError(error)

        for result in self._resultsOf(results, feedback):
            if result.navid == 0:
                addFeature(locations, result, "position")
            addFeature(navigations, result, "navigation")

        return {
            locations.name: locations.dest,
            navigations.name: navigations.dest,
        }


class CasaGeoToolsPOISearchAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    INPUT = "INPUT"
    LIMIT = "LIMIT"
    COUNTRIES = "COUNTRIES"
    ADDRESS_NAMES_MODE = "ADDRESS_NAMES_MODE"
    POSTAL_CODE_MODE = "POSTAL_CODE_MODE"

    OUTPUT_LOCATIONS = "OUTPUT_LOCATIONS"
    OUTPUT_NAVIGATIONS = "OUTPUT_NAVIGATIONS"

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

        try:
            from casageo.coder import (
                DEFAULT_ADDRESS_NAMES_MODE,
                DEFAULT_LIMIT,
                DEFAULT_POSTAL_CODE_MODE,
                MAX_LIMIT,
                MIN_LIMIT,
                AddressNamesMode,
                PostalCodeMode,
            )
        except ImportError as err:
            self.status_ok = False
            self.status_message = str(err)
            return

        translator = self.plugin.coderTranslator
        trAddressNamesMode = translator.translateAddressNamesMode
        trPostalCodeMode = translator.translatePostalCodeMode

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.__tr("Input layer"),
                [Qgis.ProcessingSourceType.VectorPoint],
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.LIMIT,
                self.__tr("Limit"),
                Qgis.ProcessingNumberParameterType.Integer,
                defaultValue=DEFAULT_LIMIT,
                minValue=MIN_LIMIT,
                maxValue=MAX_LIMIT,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.COUNTRIES,
                self.__tr("Search countries (separated by commas)"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.ADDRESS_NAMES_MODE,
                self.__tr("Address names mode"),
                options=map(trAddressNamesMode, AddressNamesMode),
                defaultValue=trAddressNamesMode(DEFAULT_ADDRESS_NAMES_MODE),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.POSTAL_CODE_MODE,
                self.__tr("Postal code mode"),
                options=map(trPostalCodeMode, PostalCodeMode),
                defaultValue=trPostalCodeMode(DEFAULT_POSTAL_CODE_MODE),
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_LOCATIONS,
                self.__tr("POI locations"),
                Qgis.ProcessingSourceType.VectorPoint,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_NAVIGATIONS,
                self.__tr("POI navigation points"),
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
            case self.OUTPUT_LOCATIONS | self.OUTPUT_NAVIGATIONS:
                props = QgsProcessingAlgorithm.VectorProperties()
                props.availability = Qgis.ProcessingPropertyAvailability.Available
                props.crs = QgsCoordinateReferenceSystem.fromEpsgId(4326)
                props.fields = QgsFields([
                    QgsField("id", QMetaType.Type.Int),
                    QgsField("subid", QMetaType.Type.Int),
                    QgsField("navid", QMetaType.Type.Int),
                    QgsField("title", QMetaType.Type.QString),
                    QgsField("resulttype", QMetaType.Type.QString),
                    QgsField("distance", QMetaType.Type.Double),
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

        source = self._getSource(self.INPUT, parameters, context)
        request = self._epsg4326FeatureRequest(context, feedback)
        data = [
            {
                "id": feature.id(),
                "position": geometry_as_shapely(feature.geometry()),
            }
            for feature in features_of(source, request)
        ]

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
        from casageo.coder import AddressNamesMode, PostalCodeMode

        ADDRESS_NAMES_MODES = list(AddressNamesMode)
        POSTAL_CODE_MODES = list(PostalCodeMode)

        client = self.plugin.casaGeoClient(feedback)

        limit = self.parameterAsInt(parameters, self.LIMIT, context)
        countries = self.parameterAsString(parameters, self.COUNTRIES, context)
        address_names_mode_index = self.parameterAsEnum(
            parameters, self.ADDRESS_NAMES_MODE, context
        )
        postal_code_mode_index = self.parameterAsEnum(
            parameters, self.POSTAL_CODE_MODE, context
        )

        defaults = {
            "limit": limit,
            "countries": countries,
            "address_names_mode": ADDRESS_NAMES_MODES[address_names_mode_index],
            "postal_code_mode": POSTAL_CODE_MODES[postal_code_mode_index],
        }

        try:
            return casageo.coder.poi(
                client,
                queries,
                defaults,
            )
        except Exception as err:
            raise QgsProcessingException(str(err)) from err

    def _writeOutputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        results: "GeoDataFrame",
    ) -> dict[str, str]:
        """Convert results to features and write them to the feature sink."""

        locations = self._getSink(self.OUTPUT_LOCATIONS, parameters, context)
        navigations = self._getSink(self.OUTPUT_NAVIGATIONS, parameters, context)

        def addFeature(
            output: ProcessingFeatureSinkDefinition,
            result: Any,
            geometryfield: str,
        ) -> None:
            feature = QgsFeature(output.props.fields)
            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["navid"] = result.navid
            feature["title"] = result.title
            feature["resulttype"] = result.resulttype
            feature["distance"] = result.distance
            feature["timestamp"] = result.timestamp.isoformat()
            feature["error_code"] = result.error_code
            feature["error_message"] = result.error_message

            if (geom := result[geometryfield]) is not None:
                feature.setGeometry(geometry_from_shapely(geom))

            if not output.sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert):
                error = self.writeFeatureError(output.sink, parameters, output.name)
                feedback.reportError(error)

        for result in self._resultsOf(results, feedback):
            if result.navid == 0:
                addFeature(locations, result, "position")
            addFeature(navigations, result, "navigation")

        return {
            locations.name: locations.dest,
            navigations.name: navigations.dest,
        }

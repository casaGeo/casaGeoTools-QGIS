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
from enum import StrEnum
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
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
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
)
from . import CasaGeoToolsProcessingAlgorithm

if TYPE_CHECKING:
    from geopandas import GeoDataFrame
    from pandas import DataFrame


class CasaGeoToolsPOISearchAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    class Mode(StrEnum):
        SINGLE = "single"
        BATCH = "batch"

    REQUEST_ID = "REQUEST_ID"
    LOCATION = "LOCATION"

    INPUT_LAYER = "INPUT_LAYER"

    LIMIT = "LIMIT"
    LIMIT_FIELD = "LIMIT_FIELD"

    COUNTRIES = "COUNTRIES"
    COUNTRIES_FIELD = "COUNTRIES_FIELD"

    ADDRESS_NAMES_MODE = "ADDRESS_NAMES_MODE"
    ADDRESS_NAMES_MODE_FIELD = "ADDRESS_NAMES_MODE_FIELD"

    POSTAL_CODE_MODE = "POSTAL_CODE_MODE"
    POSTAL_CODE_MODE_FIELD = "POSTAL_CODE_MODE_FIELD"

    WITH_ADDRESS_DETAILS = "WITH_ADDRESS_DETAILS"
    WITH_COORDINATES = "WITH_COORDINATES"

    OUTPUT_LOCATIONS = "OUTPUT_LOCATIONS"
    OUTPUT_NAVIGATIONS = "OUTPUT_NAVIGATIONS"

    @override
    def groupId(self) -> str:
        return self.GROUP_ID_CODER

    @override
    def displayName(self) -> str:
        match self.Mode(self.mode):
            case self.Mode.SINGLE:
                return self.__tr("POI Search", "Algorithm")
            case self.Mode.BATCH:
                return self.__tr("POI Search (batch)", "Algorithm")

    @override
    def name(self) -> str:
        match self.Mode(self.mode):
            case self.Mode.SINGLE:
                return "poi_single"
            case self.Mode.BATCH:
                return "poi_batch"

    @override
    def _initAlgorithm(self, configuration: dict[str, Any] | None) -> None:
        from casageo.coder import (
            DEFAULT_ADDRESS_NAMES_MODE,
            DEFAULT_LIMIT,
            DEFAULT_POSTAL_CODE_MODE,
            MAX_LIMIT,
            MIN_LIMIT,
            AddressNamesMode,
            PostalCodeMode,
        )

        translator = self.plugin.coderTranslator
        trAddressNamesMode = translator.translateAddressNamesMode
        trPostalCodeMode = translator.translatePostalCodeMode

        self._addParameter(
            QgsProcessingParameterNumber(
                self.REQUEST_ID,
                self.__tr("Request ID", "Parameter"),
                type=Qgis.ProcessingNumberParameterType.Integer,
                defaultValue=self.request_counter.value + 1,
                minValue=0,
            ),
            modes={self.Mode.SINGLE},
        )

        self._addParameter(
            QgsProcessingParameterPoint(
                self.LOCATION,
                self.__tr("Location", "Parameter"),
            ),
            modes={self.Mode.SINGLE},
        )

        self._addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_LAYER,
                self.__tr("Input layer", "Parameter"),
                [Qgis.ProcessingSourceType.VectorPoint],
            ),
            modes={self.Mode.BATCH},
        )

        self._addParameter(
            QgsProcessingParameterNumber(
                self.LIMIT,
                self.__tr("Limit"),
                Qgis.ProcessingNumberParameterType.Integer,
                defaultValue=DEFAULT_LIMIT,
                minValue=MIN_LIMIT,
                maxValue=MAX_LIMIT,
            )
        )
        self._addParameter(
            QgsProcessingParameterField(
                self.LIMIT_FIELD,
                self.__tr("Limit (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.Numeric,
                optional=True,
            ),
            modes={self.Mode.BATCH},
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.COUNTRIES,
                self.__tr("Search countries (separated by commas)"),
                optional=True,
            )
        )
        self._addParameter(
            QgsProcessingParameterField(
                self.COUNTRIES_FIELD,
                self.__tr("Search countries (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            ),
            modes={self.Mode.BATCH},
        )

        self._addParameter(
            QgsProcessingParameterEnum(
                self.ADDRESS_NAMES_MODE,
                self.__tr("Address names mode"),
                options=map(trAddressNamesMode, AddressNamesMode),
                defaultValue=trAddressNamesMode(DEFAULT_ADDRESS_NAMES_MODE),
            )
        )
        self._addParameter(
            QgsProcessingParameterField(
                self.ADDRESS_NAMES_MODE_FIELD,
                self.__tr("Address names mode (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            ),
            modes={self.Mode.BATCH},
        )

        self._addParameter(
            QgsProcessingParameterEnum(
                self.POSTAL_CODE_MODE,
                self.__tr("Postal code mode"),
                options=map(trPostalCodeMode, PostalCodeMode),
                defaultValue=trPostalCodeMode(DEFAULT_POSTAL_CODE_MODE),
            )
        )
        self._addParameter(
            QgsProcessingParameterField(
                self.POSTAL_CODE_MODE_FIELD,
                self.__tr("Postal code mode (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            ),
            modes={self.Mode.BATCH},
        )

        self._addParameter(
            QgsProcessingParameterBoolean(
                self.WITH_ADDRESS_DETAILS,
                self.__tr("Include address details", "Parameter"),
                defaultValue=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterBoolean(
                self.WITH_COORDINATES,
                self.__tr("Include coordinates", "Parameter"),
                defaultValue=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_LOCATIONS,
                self.__tr("POI locations", "Parameter"),
                Qgis.ProcessingSourceType.VectorPoint,
            )
        )

        self._addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_NAVIGATIONS,
                self.__tr("POI navigation points", "Parameter"),
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
        with_address_details = self.parameterAsBool(
            parameters, self.WITH_ADDRESS_DETAILS, context
        )
        with_coordinates = self.parameterAsBool(
            parameters, self.WITH_COORDINATES, context
        )

        match sink:
            case self.OUTPUT_LOCATIONS | self.OUTPUT_NAVIGATIONS:
                props = QgsProcessingAlgorithm.VectorProperties()
                props.availability = Qgis.ProcessingPropertyAvailability.Available
                props.crs = self.HERE_CRS
                props.wkbType = Qgis.WkbType.Point
                props.fields.append([
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

                if with_address_details:
                    props.fields.append([
                        QgsField("postaladdress", QMetaType.Type.QString),
                        QgsField("country", QMetaType.Type.QString),
                        QgsField("countrycode", QMetaType.Type.QString),
                        QgsField("state", QMetaType.Type.QString),
                        QgsField("statecode", QMetaType.Type.QString),
                        QgsField("county", QMetaType.Type.QString),
                        QgsField("countycode", QMetaType.Type.QString),
                        QgsField("city", QMetaType.Type.QString),
                        QgsField("district", QMetaType.Type.QString),
                        QgsField("subdistrict", QMetaType.Type.QString),
                        QgsField("street", QMetaType.Type.QString),
                        QgsField("block", QMetaType.Type.QString),
                        QgsField("subblock", QMetaType.Type.QString),
                        QgsField("postalcode", QMetaType.Type.QString),
                        QgsField("housenumber", QMetaType.Type.QString),
                        QgsField("building", QMetaType.Type.QString),
                        QgsField("unit", QMetaType.Type.QString),
                    ])

                if with_coordinates:
                    props.fields.append([
                        QgsField("longitude", QMetaType.Type.Double),
                        QgsField("latitude", QMetaType.Type.Double),
                    ])

                return props

        return super().sinkProperties(sink, parameters, context, sourceProperties)

    @override
    def _convertInputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> "DataFrame":
        match self.Mode(self.mode):
            case self.Mode.SINGLE:
                return self._convertInputGeometriesSingle(parameters, context, feedback)
            case self.Mode.BATCH:
                return self._convertInputGeometriesBatch(parameters, context, feedback)

    def _convertInputGeometriesSingle(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> "DataFrame":
        from pandas import DataFrame

        request_id = self.parameterAsInt(parameters, self.REQUEST_ID, context)
        position = self._parameterAsTransformedPoint(
            self.LOCATION, self.HERE_CRS, parameters, context
        )

        data = [
            {
                "id": request_id,
                "position_longitude": position.x() if not position.isEmpty() else None,
                "position_latitude": position.y() if not position.isEmpty() else None,
            }
        ]

        return DataFrame(data)

    def _convertInputGeometriesBatch(
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
            limit_field := getString(self.LIMIT_FIELD),
            countries_field := getString(self.COUNTRIES_FIELD),
            address_names_mode_field := getString(self.ADDRESS_NAMES_MODE_FIELD),
            postal_code_mode_field := getString(self.POSTAL_CODE_MODE_FIELD),
        ]

        request = self._geometryFeatureRequest(context, feedback)
        request.setSubsetOfAttributes((f for f in fields if f), source.fields())

        data = []
        for feature in features_of(source, request):
            data.append(row := {})
            row["id"] = feature.id()
            row["position"] = geometry_as_shapely(feature.geometry())
            if f := limit_field:
                row["limit"] = feature[f]
            if f := countries_field:
                row["countries"] = feature[f]
            if f := address_names_mode_field:
                row["address_names_mode"] = feature[f]
            if f := postal_code_mode_field:
                row["postal_code_mode"] = feature[f]

        return DataFrame(data)

    @override
    def _calculateResultsMessage(self) -> str:
        return self.__tr("Searching for POIs")

    @override
    def _calculateResults(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
        queries: "DataFrame",
    ) -> "GeoDataFrame":
        import casageo.coder
        from casageo.coder import AddressNamesMode, PostalCodeMode
        from casageo.tools import CasaGeoError

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
        with_address_details = self.parameterAsBool(
            parameters, self.WITH_ADDRESS_DETAILS, context
        )
        with_coordinates = self.parameterAsBool(
            parameters, self.WITH_COORDINATES, context
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
                address_details=with_address_details,
                coordinates=with_coordinates,
            )
        except CasaGeoError as err:
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

        locations = self._getSink(self.OUTPUT_LOCATIONS, parameters, context)
        navigations = self._getSink(self.OUTPUT_NAVIGATIONS, parameters, context)
        with_address_details = self.parameterAsBool(
            parameters, self.WITH_ADDRESS_DETAILS, context
        )
        with_coordinates = self.parameterAsBool(
            parameters, self.WITH_COORDINATES, context
        )

        def addFeature(
            output: ProcessingFeatureSinkDefinition,
            result: Any,
            geometryfield: str,
        ) -> None:
            feature = QgsFeature(output.props.fields)
            if (geom := getattr(result, geometryfield)) is not None:
                feature.setGeometry(geometry_from_shapely(geom))

            feature["id"] = result.id
            feature["subid"] = result.subid
            feature["navid"] = result.navid
            feature["title"] = result.title
            feature["resulttype"] = result.resulttype
            feature["distance"] = result.distance
            feature["timestamp"] = and_then(result.timestamp, datetime.isoformat)
            feature["error_code"] = result.error_code
            feature["error_message"] = result.error_message

            if with_address_details:
                feature["postaladdress"] = result.postaladdress
                feature["country"] = result.country
                feature["countrycode"] = result.countrycode
                feature["state"] = result.state
                feature["statecode"] = result.statecode
                feature["county"] = result.county
                feature["countycode"] = result.countycode
                feature["city"] = result.city
                feature["district"] = result.district
                feature["subdistrict"] = result.subdistrict
                feature["street"] = result.street
                feature["block"] = result.block
                feature["subblock"] = result.subblock
                feature["postalcode"] = result.postalcode
                feature["housenumber"] = result.housenumber
                feature["building"] = result.building
                feature["unit"] = result.unit

            if with_coordinates:
                feature["longitude"] = getattr(result, f"{geometryfield}_longitude")
                feature["latitude"] = getattr(result, f"{geometryfield}_latitude")

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

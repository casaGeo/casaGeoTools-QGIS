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

    WITH_ADDRESS_DETAILS = "WITH_ADDRESS_DETAILS"
    WITH_COORDINATES = "WITH_COORDINATES"
    WITH_MATCH_QUALITY = "WITH_MATCH_QUALITY"

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
                self.__tr("Search around feature point geometry"),
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
            QgsProcessingParameterBoolean(
                self.WITH_ADDRESS_DETAILS,
                self.__tr("Include address details"),
                defaultValue=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.WITH_COORDINATES,
                self.__tr("Include coordinates"),
                defaultValue=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.WITH_MATCH_QUALITY,
                self.__tr("Include match quality"),
                defaultValue=True,
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
        with_address_details = self.parameterAsBool(
            parameters, self.WITH_ADDRESS_DETAILS, context
        )
        with_coordinates = self.parameterAsBool(
            parameters, self.WITH_COORDINATES, context
        )
        with_match_quality = self.parameterAsBool(
            parameters, self.WITH_MATCH_QUALITY, context
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
                    QgsField("address", QMetaType.Type.QString),
                    QgsField("resulttype", QMetaType.Type.QString),
                    QgsField("distance", QMetaType.Type.Double),
                    QgsField("relevance", QMetaType.Type.Double),
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

                if with_match_quality:
                    props.fields.append([
                        QgsField("mq_country", QMetaType.Type.Double),
                        QgsField("mq_countrycode", QMetaType.Type.Double),
                        QgsField("mq_state", QMetaType.Type.Double),
                        QgsField("mq_statecode", QMetaType.Type.Double),
                        QgsField("mq_county", QMetaType.Type.Double),
                        QgsField("mq_countycode", QMetaType.Type.Double),
                        QgsField("mq_city", QMetaType.Type.Double),
                        QgsField("mq_district", QMetaType.Type.Double),
                        QgsField("mq_subdistrict", QMetaType.Type.Double),
                        QgsField("mq_street", QMetaType.Type.Double),
                        QgsField("mq_block", QMetaType.Type.Double),
                        QgsField("mq_subblock", QMetaType.Type.Double),
                        QgsField("mq_postalcode", QMetaType.Type.Double),
                        QgsField("mq_housenumber", QMetaType.Type.Double),
                        QgsField("mq_building", QMetaType.Type.Double),
                        QgsField("mq_unit", QMetaType.Type.Double),
                        QgsField("mq_placename", QMetaType.Type.Double),
                        QgsField("mq_ontologyname", QMetaType.Type.Double),
                    ])

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
            request = self._geometryFeatureRequest(context, feedback)
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

    @override
    def _calculateResultsMessage(self) -> str:
        return self.__tr("Geocoding addresses")

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
        with_address_details = self.parameterAsBool(
            parameters, self.WITH_ADDRESS_DETAILS, context
        )
        with_coordinates = self.parameterAsBool(
            parameters, self.WITH_COORDINATES, context
        )
        with_match_quality = self.parameterAsBool(
            parameters, self.WITH_MATCH_QUALITY, context
        )

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
                address_details=with_address_details,
                coordinates=with_coordinates,
                match_quality=with_match_quality,
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

        locations = self._getSink(self.OUTPUT_LOCATIONS, parameters, context)
        navigations = self._getSink(self.OUTPUT_NAVIGATIONS, parameters, context)
        with_address_details = self.parameterAsBool(
            parameters, self.WITH_ADDRESS_DETAILS, context
        )
        with_coordinates = self.parameterAsBool(
            parameters, self.WITH_COORDINATES, context
        )
        with_match_quality = self.parameterAsBool(
            parameters, self.WITH_MATCH_QUALITY, context
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
            feature["address"] = result.address
            feature["resulttype"] = result.resulttype
            feature["distance"] = result.distance
            feature["relevance"] = result.relevance
            feature["timestamp"] = result.timestamp.isoformat()
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

            if with_match_quality:
                feature["mq_country"] = result.mq_country
                feature["mq_countrycode"] = result.mq_countrycode
                feature["mq_state"] = result.mq_state
                feature["mq_statecode"] = result.mq_statecode
                feature["mq_county"] = result.mq_county
                feature["mq_countycode"] = result.mq_countycode
                feature["mq_city"] = result.mq_city
                feature["mq_district"] = result.mq_district
                feature["mq_subdistrict"] = result.mq_subdistrict
                feature["mq_street"] = result.mq_street
                feature["mq_block"] = result.mq_block
                feature["mq_subblock"] = result.mq_subblock
                feature["mq_postalcode"] = result.mq_postalcode
                feature["mq_housenumber"] = result.mq_housenumber
                feature["mq_building"] = result.mq_building
                feature["mq_unit"] = result.mq_unit
                feature["mq_placename"] = result.mq_placename
                feature["mq_ontologyname"] = result.mq_ontologyname

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

    WITH_ADDRESS_DETAILS = "WITH_ADDRESS_DETAILS"
    WITH_COORDINATES = "WITH_COORDINATES"

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
            QgsProcessingParameterBoolean(
                self.WITH_ADDRESS_DETAILS,
                self.__tr("Include address details"),
                defaultValue=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.WITH_COORDINATES,
                self.__tr("Include coordinates"),
                defaultValue=True,
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
            feature["timestamp"] = result.timestamp.isoformat()
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

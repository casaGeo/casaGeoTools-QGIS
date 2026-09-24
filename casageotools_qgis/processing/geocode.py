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

from collections.abc import Sequence
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


class CasaGeoToolsGeocodeAlgorithm(CasaGeoToolsProcessingAlgorithm):
    __tr = TrMethod()

    INPUT_LAYER = "INPUT_LAYER"

    ADDRESS = "ADDRESS"
    ADDRESS_FIELD = "ADDRESS_FIELD"

    COUNTRY = "COUNTRY"
    COUNTRY_FIELD = "COUNTRY_FIELD"

    STATE = "STATE"
    STATE_FIELD = "STATE_FIELD"

    COUNTY = "COUNTY"
    COUNTY_FIELD = "COUNTY_FIELD"

    CITY = "CITY"
    CITY_FIELD = "CITY_FIELD"

    DISTRICT = "DISTRICT"
    DISTRICT_FIELD = "DISTRICT_FIELD"

    STREET = "STREET"
    STREET_FIELD = "STREET_FIELD"

    HOUSENUMBER = "HOUSENUMBER"
    HOUSENUMBER_FIELD = "HOUSENUMBER_FIELD"

    POSTALCODE = "POSTALCODE"
    POSTALCODE_FIELD = "POSTALCODE_FIELD"

    USE_GEOMETRY = "USE_GEOMETRY"
    USE_GEOMETRY_FIELD = "USE_GEOMETRY_FIELD"

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
    WITH_MATCH_QUALITY = "WITH_MATCH_QUALITY"

    OUTPUT_LOCATIONS = "OUTPUT_LOCATIONS"
    OUTPUT_NAVIGATIONS = "OUTPUT_NAVIGATIONS"

    @override
    def groupId(self) -> str:
        return self.GROUP_ID_CODER

    @override
    def displayName(self) -> str:
        return self.__tr("Geocode", "Algorithm")

    @override
    def name(self) -> str:
        return "geocode"

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

        self.batch_mode = True

        self._addBatchParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_LAYER,
                self.__tr("Input layer"),
                [Qgis.ProcessingSourceType.Vector],
            )
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.ADDRESS,
                self.__tr("Free-form address", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.ADDRESS_FIELD,
                self.__tr("Free-form address (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.COUNTRY,
                self.__tr("Country", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.COUNTRY_FIELD,
                self.__tr("Country (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.STATE,
                self.__tr("State", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.STATE_FIELD,
                self.__tr("State (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.COUNTY,
                self.__tr("County", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.COUNTY_FIELD,
                self.__tr("County (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.CITY,
                self.__tr("City", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.CITY_FIELD,
                self.__tr("City (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.DISTRICT,
                self.__tr("District", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.DISTRICT_FIELD,
                self.__tr("District (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.STREET,
                self.__tr("Street (and optionally house number)", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.STREET_FIELD,
                self.__tr("Street (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.HOUSENUMBER,
                self.__tr("House number", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.HOUSENUMBER_FIELD,
                self.__tr("House number (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.POSTALCODE,
                self.__tr("Postal code", "Parameter"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.POSTALCODE_FIELD,
                self.__tr("Postal code (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterBoolean(
                self.USE_GEOMETRY,
                self.__tr("Search around feature point geometry", "Parameter"),
                defaultValue=False,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.USE_GEOMETRY_FIELD,
                self.__tr("Search around feature point geometry (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.Boolean,
                optional=True,
            )
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
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.LIMIT_FIELD,
                self.__tr("Limit (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.Numeric,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterString(
                self.COUNTRIES,
                self.__tr("Search countries (separated by commas)"),
                optional=True,
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.COUNTRIES_FIELD,
                self.__tr("Search countries (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterEnum(
                self.ADDRESS_NAMES_MODE,
                self.__tr("Address names mode"),
                options=map(trAddressNamesMode, AddressNamesMode),
                defaultValue=trAddressNamesMode(DEFAULT_ADDRESS_NAMES_MODE),
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.ADDRESS_NAMES_MODE_FIELD,
                self.__tr("Address names mode (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterEnum(
                self.POSTAL_CODE_MODE,
                self.__tr("Postal code mode"),
                options=map(trPostalCodeMode, PostalCodeMode),
                defaultValue=trPostalCodeMode(DEFAULT_POSTAL_CODE_MODE),
            )
        )
        self._addBatchParameter(
            QgsProcessingParameterField(
                self.POSTAL_CODE_MODE_FIELD,
                self.__tr("Postal code mode (field)", "Parameter"),
                parentLayerParameterName=self.INPUT_LAYER,
                type=Qgis.ProcessingFieldParameterDataType.String,
                optional=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterBoolean(
                self.WITH_ADDRESS_DETAILS,
                self.__tr("Include address details"),
                defaultValue=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterBoolean(
                self.WITH_COORDINATES,
                self.__tr("Include coordinates"),
                defaultValue=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterBoolean(
                self.WITH_MATCH_QUALITY,
                self.__tr("Include match quality"),
                defaultValue=True,
            )
        )

        self._addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_LOCATIONS,
                self.__tr("Geocoded locations"),
                Qgis.ProcessingSourceType.VectorPoint,
            )
        )

        self._addParameter(
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
    def checkParameterValues(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
    ) -> tuple[bool, str]:
        if not any(
            self.parameterAsString(parameters, name, context)
            for name in (
                self.ADDRESS,
                self.ADDRESS_FIELD,
                self.COUNTRY,
                self.COUNTRY_FIELD,
                self.STATE,
                self.STATE_FIELD,
                self.COUNTY,
                self.COUNTY_FIELD,
                self.CITY,
                self.CITY_FIELD,
                self.DISTRICT,
                self.DISTRICT_FIELD,
                self.STREET,
                self.STREET_FIELD,
                self.HOUSENUMBER,
                self.HOUSENUMBER_FIELD,
                self.POSTALCODE,
                self.POSTALCODE_FIELD,
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

        source = self._getSource(self.INPUT_LAYER, parameters, context)
        fields = [
            address_field := getString(self.ADDRESS_FIELD),
            country_field := getString(self.COUNTRY_FIELD),
            state_field := getString(self.STATE_FIELD),
            county_field := getString(self.COUNTY_FIELD),
            city_field := getString(self.CITY_FIELD),
            district_field := getString(self.DISTRICT_FIELD),
            street_field := getString(self.STREET_FIELD),
            housenumber_field := getString(self.HOUSENUMBER_FIELD),
            postalcode_field := getString(self.POSTALCODE_FIELD),
            use_geometry_field := getString(self.USE_GEOMETRY_FIELD),
            limit_field := getString(self.LIMIT_FIELD),
            countries_field := getString(self.COUNTRIES_FIELD),
            address_names_mode_field := getString(self.ADDRESS_NAMES_MODE_FIELD),
            postal_code_mode_field := getString(self.POSTAL_CODE_MODE_FIELD),
        ]
        use_geometry = self.parameterAsBoolean(parameters, self.USE_GEOMETRY, context)

        if use_geometry or use_geometry_field:
            request = self._geometryFeatureRequest(context, feedback)
        else:
            request = self._simpleFeatureRequest(context, feedback)
            request.setFlags(Qgis.FeatureRequestFlag.NoGeometry)

        request.setSubsetOfAttributes((f for f in fields if f), source.fields())

        def shouldUseGeometry(feature):
            if f := use_geometry_field:
                return feature[f]
            return use_geometry

        return DataFrame([
            {
                "id": feature.id(),
                "position": (
                    geometry_as_shapely(feature.geometry())
                    if shouldUseGeometry(feature)
                    else None
                ),
                "address": feature[f] if (f := address_field) else None,
                "country": feature[f] if (f := country_field) else None,
                "state": feature[f] if (f := state_field) else None,
                "county": feature[f] if (f := county_field) else None,
                "city": feature[f] if (f := city_field) else None,
                "district": feature[f] if (f := district_field) else None,
                "street": feature[f] if (f := street_field) else None,
                "housenumber": feature[f] if (f := housenumber_field) else None,
                "postalcode": feature[f] if (f := postalcode_field) else None,
                "limit": feature[f] if (f := limit_field) else None,
                "countries": feature[f] if (f := countries_field) else None,
                "address_names_mode": (
                    feature[f] if (f := address_names_mode_field) else None
                ),
                "postal_code_mode": (
                    feature[f] if (f := postal_code_mode_field) else None
                ),
            }
            for feature in features_of(source, request)
        ])

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

        def getBool(name: str, /) -> bool:
            return self.parameterAsBool(parameters, name, context)

        def getInt(name: str, /) -> int:
            return self.parameterAsInt(parameters, name, context)

        def getString(name: str, /) -> str:
            return self.parameterAsString(parameters, name, context)

        def getEnum[T](name: str, mapping: Sequence[T], /) -> T:
            return mapping[self.parameterAsEnum(parameters, name, context)]

        client = self.plugin.casaGeoClient(feedback)
        defaults = {
            "address": getString(self.ADDRESS) or None,
            "country": getString(self.COUNTRY) or None,
            "state": getString(self.STATE) or None,
            "county": getString(self.COUNTY) or None,
            "city": getString(self.CITY) or None,
            "district": getString(self.DISTRICT) or None,
            "street": getString(self.STREET) or None,
            "housenumber": getString(self.HOUSENUMBER) or None,
            "postalcode": getString(self.POSTALCODE) or None,
            "limit": getInt(self.LIMIT),
            "countries": getString(self.COUNTRIES),
            "address_names_mode": getEnum(
                self.ADDRESS_NAMES_MODE, list(AddressNamesMode)
            ),
            "postal_code_mode": getEnum(self.POSTAL_CODE_MODE, list(PostalCodeMode)),
        }

        with_address_details = getBool(self.WITH_ADDRESS_DETAILS)
        with_coordinates = getBool(self.WITH_COORDINATES)
        with_match_quality = getBool(self.WITH_MATCH_QUALITY)

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

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
    def _convertInputGeometries(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> "DataFrame":
        from pandas import DataFrame

        source = self._getSource(self.INPUT, parameters, context)
        request = self._geometryFeatureRequest(context, feedback)
        request.setSubsetOfAttributes([])

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

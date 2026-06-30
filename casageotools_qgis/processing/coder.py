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

__all__ = [
    "CasaGeoToolsAddressSearchAlgorithm",
    "CasaGeoToolsPOISearchAlgorithm",
]

import importlib
from typing import TYPE_CHECKING, Any, override

from qgis.core import (
    Qgis,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
)
from qgis.PyQt.QtCore import QMetaType

from ..utils import TrMethod

if TYPE_CHECKING:
    from ..plugin import CasaGeoToolsPlugin


class CasaGeoToolsAbstractGeocodingAlgorithm(QgsProcessingAlgorithm):
    __tr = TrMethod()

    def __init__(self, plugin: "CasaGeoToolsPlugin"):
        super().__init__()
        self.plugin = plugin

    @override
    def group(self) -> str:
        return self.__tr("Coder", "Group")

    @override
    def groupId(self) -> str:
        return "coder"

    @override
    def canExecute(self) -> tuple[bool, str]:
        for module in ["casageo.tools", "casageo.coder", "geopandas"]:
            try:
                importlib.import_module(module)
            except ModuleNotFoundError:
                return False, f"The {module} module is not installed"
            except ImportError as err:
                return False, f"The {module} module could not be imported: {err}"

        return True, ""

    @override
    def helpUrl(self) -> str:
        return self.plugin.help_url(
            f"algorithms/{self.groupId()}/{self.name()}.html"
        ).toString()


class CasaGeoToolsAddressSearchAlgorithm(CasaGeoToolsAbstractGeocodingAlgorithm):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    __tr = TrMethod()

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
    def createInstance(self) -> QgsProcessingAlgorithm | None:
        return CasaGeoToolsAddressSearchAlgorithm(self.plugin)

    @override
    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        if configuration is None:
            configuration = {}
        raise NotImplementedError

    @override
    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class CasaGeoToolsPOISearchAlgorithm(CasaGeoToolsAbstractGeocodingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    __tr = TrMethod()

    @override
    def displayName(self) -> str:
        return self.__tr("POI search", "Algorithm")

    @override
    def name(self) -> str:
        return "poisearch"

    @override
    def createInstance(self) -> QgsProcessingAlgorithm | None:
        return CasaGeoToolsPOISearchAlgorithm(self.plugin)

    @override
    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        if configuration is None:
            configuration = {}

        # # We add the input vector features source. It can have any kind of
        # # geometry.
        # self.addParameter(
        #     QgsProcessingParameterFeatureSource(
        #         self.INPUT,
        #         self.tr("Input layer"),
        #         [QgsProcessing.TypeVectorAnyGeometry],
        #     )
        # )
        #
        # # We add a feature sink in which to store our processed features (this
        # # usually takes the form of a newly created vector layer when the
        # # algorithm is run in QGIS).
        # self.addParameter(
        #     QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Output layer"))
        # )

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

    @override
    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, Any]:
        source = self.parameterAsSource(parameters, self.INPUT, context)
        assert source is not None

        sink_fields = QgsFields([
            QgsField("id", QMetaType.Type.Int),
            QgsField("subid", QMetaType.Type.Int),
            QgsField("title", QMetaType.Type.QString),
            QgsField("resulttype", QMetaType.Type.QString),
            QgsField("distance", QMetaType.Type.Double),
            QgsField("error_code", QMetaType.Type.QString),
            QgsField("error_message", QMetaType.Type.QString),
        ])

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            sink_fields,
            source.wkbType(),
            source.sourceCrs(),
        )
        assert sink is not None

        """
        client = CasaGeoClient("")
        casageo.coder.poi(client, queries)

        feature = QgsFeature(sink_fields)
        feature.setAttributes([1, 0, "Test", "POI", 1.0, "0", "No error"])
        feature.setGeometry(source.getFeature(0).geometry())
        sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)
        """

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

        return {self.OUTPUT: dest_id}

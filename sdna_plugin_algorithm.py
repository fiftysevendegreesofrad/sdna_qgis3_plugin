# -*- coding: utf-8 -*-

"""
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = "Crispin Cooper, Jeffrey Morgan"
__date__ = "July 2020"
__copyright__ = "(C) 2020 Cardiff University"

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = "$Format:%H$"

import os
import sys
import tempfile

from PyQt5.QtCore import QVariant
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProject,
    QgsMessageLog,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingOutputFile,
    QgsProcessingOutputVectorLayer,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterVectorDestination,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsProcessingUtils
)
import qgis.utils


class ShapefileParameterVectorDestination(QgsProcessingParameterVectorDestination):

    def __init__(
        self,
        name,
        description = '',
        type = QgsProcessing.TypeVectorAnyGeometry,
        defaultValue = None,
        optional = False,
        createByDefault = True
    ):
        super(QgsProcessingParameterVectorDestination, self).__init__(name, description, type, defaultValue, optional, createByDefault)


    def defaultFileExtension(self):
        """Override to use Shapefile as the temporary file format, as required by sDNA."""
        return "shp"


class SDNAAlgorithm(QgsProcessingAlgorithm):

    def __init__(self, algorithm_spec, sdna_path, run_sdna_command):
        QgsProcessingAlgorithm.__init__(self)
        self.outputs = []
        self.varnames = []
        self.outputnames = []
        self.selectvaroptions = {}
        self.sdna_path = sdna_path
        self.run_sdna_command = run_sdna_command
        self.algorithm_spec = algorithm_spec

    def initAlgorithm(self, config):
        """Set up the algorithm, add the parameters, etc."""

        sdna_to_qgis_vectortype = {
            "Polyline": QgsProcessing.TypeVectorLine,
            None: QgsProcessing.TypeVectorAnyGeometry
        }
        sdna_to_qgis_fieldtype = {
            "Numeric": QgsProcessingParameterField.DataType.Numeric,
            "String": QgsProcessingParameterField.DataType.String
        }

        for varname, displayname, datatype, filter, default, required in self.algorithm_spec.getInputSpec():

            if datatype == "OFC" or datatype == "OutFile":
                self.outputnames += [varname]
            else:
                self.varnames += [varname]

            if datatype == "FC":
                self.addParameter(
                    QgsProcessingParameterFeatureSource(
                        varname,
                        self.tr(displayname),
                        types=[sdna_to_qgis_vectortype[filter]],
                        optional=not required
                    )
                )
            elif datatype == "OFC":
                output = ShapefileParameterVectorDestination(
                    varname,
                    self.tr(displayname)
                )
                self.outputs.append(output)
                self.addParameter(output)
            elif datatype == "InFile":
                self.addParameter(
                    QgsProcessingParameterFile(
                        varname,
                        self.tr(displayname),
                        behavior=QgsProcessingParameterFile.File,
                        fileFilter=filter,
                        optional=not required
                    )
                )
            elif datatype == "MultiInFile":
                self.addParameter(
                    QgsProcessingParameterFile(
                        varname,
                        self.tr(displayname),
                        behavior=QgsProcessingParameterFile.File,
                        optional=not required
                    )
                )
            elif datatype == "OutFile":
                output = QgsProcessingParameterFileDestination(
                    varname,
                    self.tr(displayname),
                    optional=not required
                )
                self.outputs.append(output)
                self.addParameter(output)
            elif datatype == "Field":
                fieldtype, source = filter
                self.addParameter(
                    QgsProcessingParameterField(
                        varname,
                        self.tr(displayname),
                        parentLayerParameterName=source,
                        type=sdna_to_qgis_fieldtype[fieldtype],
                        optional=not required
                    )
                )
            elif datatype == "MultiField":
                self.addParameter(
                    QgsProcessingParameterString(
                        varname,
                        f"{self.tr(displayname)} (field names separated by commas)",
                        defaultValue=default,
                        multiLine=False,
                        optional=not required
                    )
                )
            elif datatype == "Bool":
                self.addParameter(
                    QgsProcessingParameterBoolean(
                        varname,
                        self.tr(displayname),
                        defaultValue=default,
                        optional=not required
                    )
                )
            elif datatype == "Text":
                if filter:
                    self.addParameter(
                        QgsProcessingParameterEnum(
                            varname,
                            self.tr(displayname),
                            options=filter,
                            defaultValue=0,
                            optional=not required
                        )
                    )
                    self.selectvaroptions[varname] = filter
                else:
                    self.addParameter(
                        QgsProcessingParameterString(
                            varname,
                            self.tr(displayname),
                            defaultValue=default,
                            multiLine=False,
                            optional=not required
                        )
                    )
            else:
                raise Exception(f"Unrecognized parameter type: '{datatype}'")


    def processAlgorithm(self, parameters, context, feedback):
        # 'input' is the name of the sDNA variable for the input layer
        source = self.parameterAsSource(parameters, 'input', context)
        source_crs = source.sourceCrs()

        feedback.setProgressText("**********************************************************************\n"\
                                 "WARNING: sDNA ignores your selection and will process the entire layer\n"\
                                 "**********************************************************************")

        args = self.extract_args(parameters, context)
        syntax = self.extract_syntax(args, context, feedback, source_crs)

        print("ARGS:", args)
        print("SYNTAX:", syntax)

        # return_object = {}
        # if "net" in syntax["outputs"]:
        #     net = syntax["outputs"]["net"]
        #     print("###NET###", net)
        #     if net.endswith(".gpkg"):
        #         net = net[:-5] + ".shp"
        #     print("###NET2##", net)
        # syntax["outputs"]["net"] = net

        retval = self.issue_sdna_command(syntax, feedback)
        if retval != 0:
            QgsMessageLog.logMessage("ERROR: PROCESS DID NOT COMPLETE SUCCESSFULLY", "SDNA")

        print("BEFORE RETURNING THE RESULT OBJECT!")

        # if "output" in return_object:
        #     new_output_layer_path = return_object["output"]
        #     if new_output_layer_path.endswith(".gpkg"):
        #         new_output_layer_path = new_output_layer_path[:-5] + ".shp"
        #     print("new_output_layer_path=", new_output_layer_path)
        #     new_output_layer = QgsVectorLayer(new_output_layer_path, "sDNA Output Later", "ogr")
        #     if not new_output_layer.isValid():
        #         print("sDNA output layer failed to load!")
        #     else:
        #         QgsProject.instance().addMapLayer(new_output_layer)
        #         new_output_layer.triggerRepaint()
        #         qgis.utils.iface.layerTreeView().refreshLayerSymbology(new_output_layer.id())

        # Return the results of the algorithm.
        return_object = {
            "OUTPUT": self.outputs[0]
        }
        return return_object

    def extract_args(self, parameters, context):
        args = {}

        for outname, output in zip(self.outputnames, self.outputs):
            args[outname] = self.parameterAsOutputLayer(parameters, outname, context)

        for vn in self.varnames:
            value = parameters[vn]
            value = None if type(value) == QVariant and value.isNull() else value  # Convert Qt's NULL into Python's None
            args[vn] = value
            if vn in self.selectvaroptions:
                args[vn] = self.selectvaroptions[vn][args[vn]]
            if args[vn] is None:
                args[vn] = ""

        # Get the path to the source of the layer. If the layer was loaded from a file
        # it will have a file extension that we will check later so see if we need to
        # create a temporary file to write the contents of a memory layer (that won't
        # have a file extension).
        layer_id = args["input"]
        layer = QgsProject.instance().mapLayer(layer_id)
        args["input"] = layer.source()
        return args

    def extract_syntax(self, args, context, feedback, source_crs):
        # Convert inputs to shapefiles if necessary, renaming in syntax as appropriate
        syntax = self.algorithm_spec.getSyntax(args)
        converted_inputs = {}
        for name, path in syntax["inputs"].items():
            if path:
                _, file_extension = os.path.splitext(path.lower())
                if not file_extension or file_extension not in [".shp", ".csv"]:
                    # If the input layer did not come from a shapefile or a CSV file or does not
                    # have a file extension (in the case of a memory layer) we need to write the
                    # contents of the layer to a temporary file so sDNA can read it as its input file.
                    with tempfile.TemporaryDirectory() as tmp:
                        temporary_filename = f"{tmp}.shp"
                        feedback.setProgressText(f"Converting input layer to shapefile: {temporary_filename}")
                        ret = QgsVectorFileWriter.writeAsVectorFormat(
                            QgsProcessingUtils.mapLayerFromString(path, context, allowLoadingNewLayers=True),
                            temporary_filename,
                            "utf-8",
                            source_crs,
                            "ESRI Shapefile"
                        )
                        if ret != QgsVectorFileWriter.NoError:
                            QgsMessageLog.logMessage("ERROR: COULD NOT WRITE TEMPORARY SHAPEFILE", "SDNA")
                        converted_inputs[name] = temporary_filename
                else:
                    converted_inputs[name] = path
        syntax["inputs"] = converted_inputs
        return syntax

    def issue_sdna_command(self, syntax, feedback):
        pythonexe, pythonpath = self.get_qgis_python_installation()
        sdna_command_path = self.sdna_path[:-5]
        progress_adapter = ProgressAdaptor(feedback)
        return self.run_sdna_command(syntax, self.sdna_path, progress_adapter, pythonexe, pythonpath)

    def get_qgis_python_installation(self):
        qgisbase = os.path.dirname(os.path.dirname(sys.executable))
        pythonexe = os.path.join(qgisbase, "bin", "python3.exe")
        pythonbase = os.path.join(qgisbase, "apps", "python27")
        pythonpath = ";".join([os.path.join(pythonbase, x) for x in ["", "Lib", "Lib/site-packages"]])
        return pythonexe, pythonpath

    def name(self):
        """The name of this algorithm. Should not be localised."""
        return self.algorithm_spec.alias

    def displayName(self):
        """The name of the algorithm in the UI. Should be localised."""
        return self.tr(self.name())

    def group(self):
        """The name of the algorithm's disclosure group in the UI. Should be localised."""
        return self.tr(self.groupId())

    def groupId(self):
        """The group ID of this algorithm. Should not be localised."""
        return self.algorithm_spec.category

    def shortHelpString(self):
        return f"{self.algorithm_spec.desc}"

    @staticmethod
    def tr(string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return SDNAAlgorithm(self.algorithm_spec, self.sdna_path, self.run_sdna_command)


class ProgressAdaptor:

    def __init__(self, feedback):
        self.feedback = feedback

    def setInfo(self, info):
        self.feedback.setProgressText(info)

    def setPercentage(self, percentage):
        self.feedback.setProgress(percentage)
    
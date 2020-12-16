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
from qgis.core import QgsMessageLog
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingOutputFile
from qgis.core import QgsProcessingOutputVectorLayer
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSource
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsVectorFileWriter
from qgis.core import QgsProcessingUtils


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

            # print(f"varname={varname} ('{self.tr(displayname)}') datatype={datatype} required={required}")

            if datatype == "OFC" or datatype == "OutFile":
                self.outputnames += [varname]
            else:
                self.varnames += [varname]

            if datatype == "FC":
                # print(f"FC Parameter: {varname} '{displayname}'")
                self.addParameter(
                    QgsProcessingParameterFeatureSource(
                        varname,
                        self.tr(displayname),
                        types=[sdna_to_qgis_vectortype[filter]],
                        optional=not required
                    )
                )
            elif datatype == "OFC":
                print(f"OFC Parameter: {varname} '{displayname}'")
                output = QgsProcessingParameterFeatureSink(
                    varname,
                    self.tr(displayname),
                )
                self.outputs.append(output)
                self.addParameter(output)
                print("OFC output:", output)
            elif datatype == "InFile":
                # print(f"InFile Parameter: {varname} '{displayname}'")
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
                # print(f"MultiInFile Parameter: {varname} '{displayname}'")
                self.addParameter(
                    QgsProcessingParameterFile(
                        varname,
                        self.tr(displayname),
                        behavior=QgsProcessingParameterFile.File,
                        optional=not required
                    )
                )
            elif datatype == "OutFile":
                print(f"OutFile Parameter: {varname} '{displayname}'")
                # output = QgsProcessingParameterOutputFile(varname, self.tr(displayname))
                # self.outputs.append(output)
                # self.addParameter(output)
            elif datatype == "Field":
                # print(f"Field Parameter: {varname} '{displayname}'")
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
                # print(f"MultiField Parameter: {varname} '{displayname}'")
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
                # print(f"Bool Parameter: {varname} '{displayname}'")
                self.addParameter(
                    QgsProcessingParameterBoolean(
                        varname,
                        self.tr(displayname),
                        defaultValue=default,
                        optional=not required
                    )
                )
            elif datatype == "Text":
                # print(f"Text Parameter: {varname} '{displayname}'")
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

        # print(f"\noutputnames={self.outputnames}")
        # print(f"varnames={self.varnames}")


    def processAlgorithm(self, parameters, context, feedback):

        QgsMessageLog.logMessage("Parameters:", "sDNA")
        QgsMessageLog.logMessage(str(parameters), "sDNA")

        # 'input' is the name of the sDNA variable for the input layer
        source = self.parameterAsSource(parameters, 'input', context)
        source_crs = source.sourceCrs()
        QgsMessageLog.logMessage(f"Features: {source.featureCount()}", "sDNA")

        # The parameterAsSource method return a QgsProcessingFeatureSource object that
        # operates on all of the features. To issue this warning, we'd need to check
        # if QGIS has a selection in the active layer, which would be the active
        # layer when this processing algorithm was invoked. However, when the input 
        # is chosen by selecting a file the current selection would not be relevant.
        # https://qgis.org/pyqgis/3.14/core/QgsProcessingFeatureSource.html#module-QgsProcessingFeatureSource
        #
        # feedback.setProgressText("**********************************************************************\n"\
        #                         "WARNING: sDNA ignores your selection and will process the entire layer\n"\
        #                         "**********************************************************************")

        args = self.extract_args(parameters, context)
        print(f"\nargs: {args}")

        syntax = self.extract_syntax(args, context, feedback, source_crs)
        print(f"\nsyntax: {syntax}")

        retval = self.issue_sdna_command(syntax, feedback)
        if retval != 0:
            QgsMessageLog.logMessage("ERROR: PROCESS DID NOT COMPLETE SUCCESSFULLY", "SDNA")

        return {}

    def extract_args(self, parameters, context):
        args = {}

        print("parameters:", parameters)
        print("output:", parameters["output"])

        for outname, output in zip(self.outputnames, self.outputs):
            print(f"outname={outname}; output={output}")
            args[outname] = self.parameterAsFileOutput(parameters, outname, context)
            # TODO: Do we need to handle command line parameters?
            # args[outname] = output.getValueAsCommandLineParameter().replace('"', '')  # strip quotes - sdna adds them again

        for vn in self.varnames:
            value = parameters[vn]
            value = None if type(value) == QVariant and value.isNull() else value  # Convert Qt's NULL into Python's None
            args[vn] = value
            if vn in self.selectvaroptions:
                args[vn] = self.selectvaroptions[vn][args[vn]]
            if args[vn] is None:
                args[vn] = ""
            # print(f"{vn}: {args[vn]} ({type(args[vn])})")

        print("input:", args["input"])
        print("output:", args["output"])

        return args

    def extract_syntax(self, args, context, feedback, source_crs):
        syntax = self.algorithm_spec.getSyntax(args)
        print("syntax:", syntax)
        # convert inputs to shapefiles if necessary, renaming in syntax as appropriate
        converted_inputs = {}
        print("syntax items:", syntax["inputs"])
        for name, path in syntax["inputs"].items():
            print(f"name={name}; path={path}")
            print(f"extract_syntax() path:'{path}'")
            if path:
                _, file_extension = os.path.splitext(path.lower())
                if file_extension and file_extension not in [".shp", ".csv"]:
                    # convert inputs to shapefiles if they aren't already shp or csv
                    # do this by hand rather than using dataobjects.exportVectorLayer(processing.getObject(path))
                    # as we want to ignore selection if present
                    feedback.setProgressText(f"Converting input to shapefile: {path}")
                    with tempfile.TemporaryDirectory() as tmp:
                        temporary_file = os.path.join(tmp, "shp")
                        ret = QgsVectorFileWriter.writeAsVectorFormat(
                            QgsProcessingUtils.mapLayerFromString(path, context, allowLoadingNewLayers=True),
                            temporary_file,
                            "utf-8",
                            source_crs,
                            "ESRI Shapefile"
                        )
                        print(f"ret={ret}")
                        if ret != QgsVectorFileWriter.NoError:
                            print("ERROR WRITING TEMP FILE!")
                        # assert ret == QgsVectorFileWriter.NoError
                        converted_inputs[name] = tempfile
                else:
                    converted_inputs[name] = path
        syntax["inputs"] = converted_inputs
        return syntax

    def issue_sdna_command(self, syntax, feedback):
        pythonexe, pythonpath = self.get_qgis_python_installation()
        print(f"\nPython:\n\texe={pythonexe};\n\tpath={pythonpath}")
        print(f"sDNA Command:\n\tsyntax={syntax}\n\tsdna_path={self.sdna_path}")
        sdna_command_path = self.sdna_path[:-5]
        print(f"sdna_command_path", sdna_command_path)
        # return self.run_sdna_command(syntax, self.sdna_path, feedback, pythonexe, pythonpath)
        return 0

    def get_qgis_python_installation(self):
        qgisbase = os.path.dirname(os.path.dirname(sys.executable))
        pythonexe = os.path.join(qgisbase, "bin", "python3.exe")
        pythonbase = os.path.join(qgisbase, "apps", "python27")
        pythonpath = ";".join([os.path.join(pythonbase, x) for x in ["", "Lib", "Lib/site-packages"]])
        print()
        print(f"qgisbase={qgisbase}")
        print(f"pythonpath={pythonpath}")
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

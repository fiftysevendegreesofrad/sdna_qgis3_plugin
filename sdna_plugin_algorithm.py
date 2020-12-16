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
            if datatype == "OFC" or datatype == "OutFile":
                self.outputnames += [varname]
            else:
                self.varnames += [varname]

            if datatype == "FC":
                self.addParameter(
                    QgsProcessingParameterVectorLayer(
                        varname,
                        self.tr(displayname),
                        types=[sdna_to_qgis_vectortype[filter]],
                        optional=not required
                    )
                )
            elif datatype == "OFC":
                output = QgsProcessingOutputVectorLayer(varname, self.tr(displayname))
                self.outputs.append(output)
                self.addOutput(output)
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
                output = QgsProcessingOutputFile(varname, self.tr(displayname))
                self.outputs.append(output)
                self.addOutput(output)
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

            # print("outputnames:", self.outputnames)
            # print("varnames:", self.varnames)

    def processAlgorithm(self, parameters, context, feedback):

        QgsMessageLog.logMessage("Parameters:", "sDNA")
        QgsMessageLog.logMessage(str(parameters), "sDNA")

        # TODO: There is no ProcessingConfig.USE_SELECTED
        # if ProcessingConfig.getSetting(ProcessingConfig.USE_SELECTED):
        if False:  # TODO: A placeholder for the fix for the above line
            feedback.setProgressText("**********************************************************************\n"\
                                    "WARNING: sDNA ignores your selection and will process the entire layer\n"\
                                    "**********************************************************************")

        args = self.extract_args(parameters, context)
        print(args)
        QgsMessageLog.logMessage(f"args: {args}", "sDNA")

        syntax = self.extract_syntax(args, context, feedback)
        print(syntax)
        QgsMessageLog.logMessage(f"syntax: {syntax}", "sDNA")

        retval = self.issue_sdna_command(syntax, feedback)
        if retval != 0:
            QgsMessageLog.logMessage("ERROR: PROCESS DID NOT COMPLETE SUCCESSFULLY")

        return {}

    def extract_args(self, parameters, context):
        args = {}

        # TODO: Find equivalents for the undocumented methods below
        for outname, output in zip(self.outputnames, self.outputs):
            print(f"outname={outname}; output={output}")
            # TODO: What is the equivalent for of getCompatibleFileName in QGIS3? Seems undocumented.
            if hasattr(output, "getCompatibleFileName"):
                args[outname] = output.getCompatibleFileName(self)
            # TODO: What is the equivalent for of getValueAsCommandLineParameter in QGIS3? Seems undocumented.
            elif hasattr(output, "getValueAsCommandLineParameter"):
                args[outname] = output.getValueAsCommandLineParameter().replace('"', '')  # strip quotes - sdna adds them again
            else:
                QgsMessageLog.logMessage(f"ERROR: Invalid output type {output}")

        for vn in self.varnames:
            value = parameters[vn]
            value = None if type(value) == QVariant and value.isNull() else value  # Convert Qt's NULL into Python's None
            args[vn] = value
            if vn in self.selectvaroptions:
                args[vn] = self.selectvaroptions[vn][args[vn]]
            if args[vn] is None:
                args[vn] = ""
            # print(f"{vn}: {args[vn]} ({type(args[vn])})")

        args["input"] = "dummy"  # TODO: Temporary to move things along
        args["output"] = "dummy"  # TODO: Temporary to move things along

        return args

    def extract_syntax(self, args, context, feedback):
        syntax = self.algorithm_spec.getSyntax(args)
        # convert inputs to shapefiles if necessary, renaming in syntax as appropriate
        converted_inputs = {}
        print("syntax items:", syntax["inputs"])
        for name, path in syntax["inputs"].items():
            QgsMessageLog.logMessage(f"path:{path}", "sDNA")
            if path and path != "dummy":
                # convert inputs to shapefiles if they aren't already shp or csv
                # do this by hand rather than using dataobjects.exportVectorLayer(processing.getObject(path))
                # as we want to ignore selection if present
                if path[-4:].lower() not in [".shp", ".csv"]:
                    feedback.setProgressText(f"Converting input to shapefile: {path}")
                    with tempfile.TemporaryDirectory() as tmp:
                        temporary_file = os.path.join(tmp, "shp")
                        ret = QgsVectorFileWriter.writeAsVectorFormat(
                            QgsProcessingUtils.mapLayerFromString(path, context, allowLoadingNewLayers=True),
                            temporary_file,
                            "utf-8",
                            # TODO: None is not a valid value here. However this documentation says to use
                            # an "invalid CRS for no reprojection". What should we use here? What is invalid?
                            # https://qgis.org/pyqgis/3.14/core/QgsVectorFileWriter.html?highlight=qgsvectorfilewriter#qgis.core.QgsVectorFileWriter.writeAsVectorFormat
                            None,
                            "ESRI Shapefile"
                        )
                        assert ret == QgsVectorFileWriter.NoError
                        converted_inputs[name] = tempfile
                else:
                    converted_inputs[name] = path
        syntax["inputs"] = converted_inputs
        return syntax

    def issue_sdna_command(self, syntax, feedback):
        pythonexe, pythonpath = self.get_qgis_python_installation()
        print()
        print(f"Python:\n\texe={pythonexe};\n\tpath={pythonpath}")
        print(f"sDNA Command:\n\tsyntax={syntax}\n\tsdna_path={self.sdna_path}")
        sdna_command_path = self.sdna_path[:-5]
        print(f"sdna_command_path", sdna_command_path)
        return self.run_sdna_command(syntax, self.sdna_path, feedback, pythonexe, pythonpath)

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

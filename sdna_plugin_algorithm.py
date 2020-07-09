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

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingUtils
from qgis.core import QgsVectorFileWriter
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterFile


class SDNAAlgorithm(QgsProcessingAlgorithm):

    def __init__(self, algorithm_spec):
        QgsProcessingAlgorithm.__init__(self)
        self.varnames = []
        self.outputnames = []
        self.selectvaroptions = {}
        self.algorithm_spec = algorithm_spec

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        # print(config)

        for varname, displayname, datatype, filter, default, required in self.algorithm_spec.getInputSpec():
            print(varname, displayname, datatype, filter, default, required)
            if datatype == "OFC" or datatype == "OutFile":
                self.outputnames += [varname]
            else:
                self.varnames += [varname]

            if datatype == "FC":
                pass
                # self.addParameter(ParameterVector(varname, self.tr(displayname), sdna_to_qgis_vectortype[filter], not required))
                # self.addParameter(ParameterVector(varname, self.tr(displayname), sdna_to_qgis_vectortype[filter], not required))
            elif datatype == "OFC":
                pass
                # self.addOutput(OutputVector(varname, self.tr(displayname)))
                # self.addOutput(OutputVector(varname, self.tr(displayname)))
            elif datatype == "InFile":
                print("INFILE:", varname, self.tr(displayname), f"filter={filter}")
                # self.addParameter(ParameterFile(varname, self.tr(displayname), False, not required, filter))
                # self.addParameter(ParameterFile(varname, self.tr(displayname), False, not required, filter))
            elif datatype == "MultiInFile":
                self.addParameter(QgsProcessingParameterFile(varname, self.tr(displayname), QgsProcessingParameterFile.File, optional=not required))
            elif datatype == "OutFile":
                pass
                # self.addOutput(OutputFile(varname, self.tr(displayname), filter))
                # self.addOutput(OutputFile(varname, self.tr(displayname), filter))
            elif datatype == "Field":
                fieldtype, source = filter
                # self.addParameter(ParameterTableField(varname, self.tr(displayname), source, sdna_to_qgis_fieldtype[fieldtype], not required))
                # self.addParameter(ParameterTableField(varname, self.tr(displayname), source, sdna_to_qgis_fieldtype[fieldtype], not required))
            elif datatype == "MultiField":
                pass
                # self.addParameter(ParameterString(varname, self.tr(displayname + " (field names separated by commas)"), default, False, not required))
                # self.addParameter(ParameterString(varname, self.tr(displayname + " (field names separated by commas)"), default, False, not required))
            elif datatype == "Bool":
                self.addParameter(QgsProcessingParameterBoolean(varname, self.tr(displayname), default))
            elif datatype == "Text":
                if filter:
                    pass
                    # self.addParameter(ParameterSelection(varname, self.tr(displayname), filter))
                    # self.selectvaroptions[varname] = filter
                else:
                    self.addParameter(QgsProcessingParameterString(varname, self.tr(displayname), default, False, not required))
            else:
                raise Exception(f"Unrecognized parameter type: '{datatype}'")  # TODO: Raise this exception
                assert False  # unrecognized parameter type

            print("outputnames:", self.outputnames)
            print("varnames:", self.varnames)

    def processAlgorithm(self, parameters, context, feedback):
        # TODO: Warn user that selections are ignored
        args = self.extract_args()
        print(args)
        syntax = self.extract_syntax(args)
        print(syntax)
        self.issue_sdna_command(syntax)

    def extract_args(self):
        args = {}
        for outname, output in zip(self.outputnames, self.outputs):
            if hasattr(output, "getCompatibleFileName"):
                args[outname] = output.getCompatibleFileName(self)
            elif hasattr(output, "getValueAsCommandLineParameter"):
                args[outname] = output.getValueAsCommandLineParameter().replace('"', '')  # strip quotes - sdna adds them again
            else:
                # raise Exception("Invalid output type")  # TODO: Raise this exception
                assert False  # don't know what to do with this output type
        for vn in self.varnames:
            args[vn] = self.getParameterValue(vn)
            if vn in self.selectvaroptions:
                args[vn] = self.selectvaroptions[vn][args[vn]]
            if args[vn] is None:
                args[vn] = ""
        return args

    def extract_syntax(self, args):
        syntax = self.algorithm_spec.getSyntax(args)
        # convert inputs to shapefiles if necessary, renaming in syntax as appropriate
        converted_inputs = {}
        for name, path in syntax["inputs"].items():
            if path:
                # convert inputs to shapefiles if they aren't already shp or csv
                # do this by hand rather than using dataobjects.exportVectorLayer(processing.getObject(path))
                # as we want to ignore selection if present
                if path[-4:].lower() not in [".shp", ".csv"]:
                    pass  # TODO: Pass for now
                    # progress.setInfo(f"Converting input to shapefile: {path}")
                    # tempfile = system.getTempFilename("shp")
                    # ret = QgsVectorFileWriter.writeAsVectorFormat(
                    #     processing.getObject(path),
                    #     tempfile,
                    #     "utf-8",
                    #     None,
                    #     "ESRI Shapefile"
                    # )
                    # assert ret == QgsVectorFileWriter.NoError
                    # converted_inputs[name] = tempfile
                else:
                    converted_inputs[name] = path
        syntax["inputs"] = converted_inputs
        return syntax

    def issue_sdna_command(self, syntax):
        pass

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return self.algorithm_spec.alias

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return self.algorithm_spec.category

    @staticmethod
    def tr(string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return SDNAAlgorithm(self.algorithm_spec)

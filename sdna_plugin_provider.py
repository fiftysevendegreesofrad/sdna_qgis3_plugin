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
from importlib import reload

from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QMessageBox
from qgis.core import QgsMessageLog
from qgis.core import QgsProcessingProvider

from .sdna_plugin_algorithm import SDNAAlgorithm


class SDNAPluginProvider(QgsProcessingProvider):

    # SDNA_FOLDER_SETTING = "SDNA_FOLDER_SETTING"

    def __init__(self):
        self.sdna_path = None
        self.run_sdna_command = None
        QgsProcessingProvider.__init__(self)
        self.import_sdna_library()

    def import_sdna_library(self):
        # sdna_root_dir = ProcessingConfig.getSetting(SDNA_FOLDER_SETTING)
        sdna_root_dir = "/Users/jeff/Programming/Work/sDNA/sdna_open/arcscripts"
        # sdna_root_dir = "c:\\Program Files (x86)\\sDNA"
        self.sdna_path = '"' + os.path.join(sdna_root_dir, "bin") + '"'
        QgsMessageLog.logMessage(f"sDNA root: {sdna_root_dir}", "sDNA")
        if sdna_root_dir not in sys.path:
            sys.path.insert(0, sdna_root_dir)
        try:
            import sDNAUISpec
            import runsdnacommand
            reload(sDNAUISpec)
            reload(runsdnacommand)
            self.run_sdna_command = runsdnacommand.runsdnacommand
            QgsMessageLog.logMessage("Successfully imported sDNA modules", "sDNA")
            for tool_class in sDNAUISpec.get_tools():
                print(tool_class)
        except ImportError as e:
            QgsMessageLog.logMessage(str(e), "sDNA")
            self.show_install_sdna_message()

    def show_install_sdna_message(self):
        QMessageBox.critical(
            QDialog(),
            "sDNA: Error",
            (
                "Please ensure sDNA version 3.0 or later is installed ensure"
                "the sDNA installation folder is set correctly in"
                "Processing -> Options -> Providers -> Spatial Design Network Analysis"
            )
        )

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        self.addAlgorithm(SDNAAlgorithm())
        # add additional algorithms here
        # self.addAlgorithm(MyOtherAlgorithm())

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return "sDNA Provider"

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr("sDNA Provider")

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QgsProcessingProvider.icon(self)

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()

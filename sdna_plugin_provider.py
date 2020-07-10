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
        self.sdna_algorithm_spec_classes = None
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
            self.sdna_algorithm_spec_classes = sDNAUISpec.get_tools()
            self.run_sdna_command = runsdnacommand.runsdnacommand
            QgsMessageLog.logMessage("Successfully imported sDNA modules", "sDNA")
        except ImportError as e:
            QgsMessageLog.logMessage(str(e), "sDNA")
            self.show_install_sdna_message()

    @staticmethod
    def show_install_sdna_message():
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
        """Load all of the algorithms belonging to this provider."""
        for sdna_algorithm_spec_class in self.sdna_algorithm_spec_classes:
            sdna_algorithm_spec = sdna_algorithm_spec_class()
            sdna_algorithm = SDNAAlgorithm(sdna_algorithm_spec)
            self.addAlgorithm(sdna_algorithm)

    def id(self):
        """The unique provider id. Should not be localised."""
        return "sDNA Provider"

    def name(self):
        """The short name of this provider. Should be localised."""
        return self.tr("sDNA")

    def icon(self):
        """The QIcon for the provider inside the Processing toolbox."""
        return QgsProcessingProvider.icon(self)

    def longName(self):
        """The longer name of this provider. Should be localised."""
        return self.tr("Spatial Design Network Analysis")

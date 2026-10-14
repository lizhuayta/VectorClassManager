# -*- coding: utf-8 -*-
import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QTranslator, QCoreApplication, QLocale
from qgis.core import QgsSettings


from .compat import QAction, RIGHT_DOCK_WIDGET_AREA, log_exception
from .dock.VectorClassManagerDockWidget import VectorClassManagerDockWidget


class VectorClassManager:
    def __init__(self, iface):
        self.iface = iface
        self.dockwidget = None
        self.action = None
        self.icon_off = None
        self.icon_on = None
        self.translator = None

    def tr(self, text):
        return QCoreApplication.translate('VectorClassManager', text)

    def load_translation(self):
        locale = QgsSettings().value(
            "locale/userLocale", QLocale.system().name()
        )
        lang = str(locale).split("_")[0].lower()

        if lang not in ("es", "fr"):
            return

        i18n_path = os.path.join(
            os.path.dirname(__file__),
            "i18n",
            f"VectorClassManager_{lang}.qm"
        )

        if os.path.exists(i18n_path):
            self.translator = QTranslator()

            if self.translator.load(i18n_path):
                QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        """Init GUI."""
        try:
            self.load_translation()
        except Exception as error:
            log_exception("Could not load plugin translations", error)

        base_path = os.path.dirname(__file__)
        icons_path = os.path.join(base_path, 'resources', 'icons')
        # On/off button icons
        self.icon_off = QIcon(os.path.join(icons_path, 'icon_off.png'))
        self.icon_on = QIcon(os.path.join(icons_path, 'icon_on.png'))
        # Toolbar button
        self.action = QAction(
            self.icon_off,
            self.tr('Vector Class Manager'),
            self.iface.mainWindow(),
        )
        self.action.setObjectName('VectorClassManager')
        # Click event
        self.action.triggered.connect(self.show_dock)
        # Menu
        self.iface.addPluginToMenu('&Vector Class Manager', self.action)
        # Toolbar icon
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.action.setIcon(self.icon_off)
            self.iface.removePluginMenu('&Vector Class Manager', self.action)
            self.iface.removeToolBarIcon(self.action)

        if self.dockwidget:
            try:
                if self.dockwidget.entity_creation_mode:
                    self.dockwidget.exit_feature_creation_mode(
                        update_info=False
                    )

                if self.dockwidget.map_tool:
                    self.dockwidget.exit_class_mode(update_info=False)
            except Exception as error:
                log_exception("Could not finish plugin editing modes", error)

            self.iface.removeDockWidget(self.dockwidget)
            self.dockwidget = None

    def show_dock(self):
        """Show the dock."""
        if not self.dockwidget:
            self.dockwidget = VectorClassManagerDockWidget()
            # When the panel is closed, return to the OFF icon.
            self.dockwidget.visibilityChanged.connect(
                self.on_visibility_changed
            )

            self.iface.addDockWidget(RIGHT_DOCK_WIDGET_AREA, self.dockwidget)

        if self.dockwidget.isVisible():
            self.dockwidget.hide()
        else:
            self.dockwidget.show()
            self.dockwidget.raise_()

    def on_visibility_changed(self, visible):
        """Handle dock visibility."""
        if not self.action:
            return

        if visible:
            self.action.setIcon(self.icon_on)
        else:
            self.action.setIcon(self.icon_off)

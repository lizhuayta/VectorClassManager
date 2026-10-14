# -*- coding: utf-8 -*-

"""
/************************************************************************************************
Vector Class Manager
Assign and manage attribute classes, digitize vector features by class, and edit
categorized symbology from a compact side panel.

Class assignment, renaming, and feature creation require the target layer to be in
edit mode. Symbol previews and editing require categorized symbology based on the chosen field.
    ---------------------------------------
        Start       : october 2026
        Author      : Liz Fedra Huayta Hernani
        Contact     : huaytahe@outlook.com
************************************************************************************************/
"""

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QColorDialog,
    QShortcut,
    QMenu,
    QInputDialog,
    QListView,
    QLabel,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QApplication,
    QWidget,
    QFrame,
    QToolButton,
    QGraphicsDropShadowEffect,
    QLineEdit,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
)
from qgis.PyQt.QtGui import QIcon, QPixmap, QPainter, QKeySequence, QColor, QDesktopServices
from qgis.PyQt.QtCore import QCoreApplication, QEvent, QTimer, QUrl
from qgis.core import QgsProject, QgsVectorLayer, QgsCategorizedSymbolRenderer, QgsStyle, QgsRendererCategory, QgsSymbol, QgsSettings, QgsGeometry, QgsCoordinateTransform, QgsEditFormConfig, QgsFieldConstraints, QgsDefaultValue, Qgis, NULL
from qgis.gui import QgsMapToolIdentifyFeature, QgsSymbolSelectorDialog
from qgis.utils import iface
from ..compat import (
    ALIGN_CENTER,
    ARROW_CURSOR,
    CONSTRAINT_NOT_NULL,
    CONSTRAINT_UNIQUE,
    CUSTOM_CONTEXT_MENU,
    FRAME_HLINE,
    FRAME_SUNKEN,
    IDENTIFY_TOP_DOWN_ALL,
    LEFT_BUTTON,
    POINTING_HAND_CURSOR,
    RICH_TEXT,
    RIGHT_BUTTON,
    SMALL_ICON_SIZE,
    TITLE_BAR_CLOSE_BUTTON,
    TITLE_BAR_NORMAL_BUTTON,
    TRANSPARENT,
    USER_ROLE,
    is_integer_field,
    log_exception,
    qt_exec,
)
import json
import os
from html import escape
from urllib.parse import quote

UI_PATH = os.path.join(os.path.dirname(__file__), 'VectorClassManagerDockWidget.ui')


class ClassListItemDelegate(QStyledItemDelegate):
    """Hide hover feedback while the class context menu is open."""

    def paint(self, painter, option, index):
        if self.parent().property("classMenuOpen"):
            option = QStyleOptionViewItem(option)
            style_flags = getattr(QStyle, "StateFlag", QStyle)
            option.state &= ~style_flags.State_MouseOver

        super().paint(painter, option, index)


class VectorClassManagerDockWidget(QDockWidget):
    def __init__(self, parent=None):
        """UI widgets."""
        super().__init__(parent)
        uic.loadUi(UI_PATH, self)
        self.setup_title_bar()
        self.apply_ui_font()

        # Layer selection and field/column selection
        self.layerCombo = self.findChild(object, 'layerCombo')
        self.fieldCombo = self.findChild(object, 'fieldCombo')

        self.layerCombo.setToolTip(
            self.tr("Layer used for class editing and feature creation")
        )
        self.fieldCombo.setToolTip(
            self.tr("Field used to read and assign class values")
        )

        self.layerCombo.setView(QListView())
        self.fieldCombo.setView(QListView())

        # Value list
        self.valueList = self.findChild(object, 'valueList')
        self.valueList.setProperty("classMenuOpen", False)
        self.valueList.setItemDelegate(ClassListItemDelegate(self.valueList))

        settings = QgsSettings()
        ui_theme = str(settings.value("UI/UITheme", "default")).strip().lower()

        if ui_theme == "default":
            self.layerCombo.setStyleSheet("""
                QComboBox {
                    color: black;
                }

                QListView {
                    background-color: #f0f0f0;
                    color: black;
                    selection-background-color: #c65f00;
                    selection-color: white;
                    outline: 0px;
                }

                QListView::item {
                    background-color: #f0f0f0;
                    color: black;
                }

                QListView::item:hover {
                    background-color: #c65f00;
                    color: white;
                }

                QListView::item:selected {
                    background-color: #c65f00;
                    color: white;
                }
            """)

            self.fieldCombo.setStyleSheet("""
                QComboBox {
                    color: black;
                }

                QListView {
                    background-color: #f0f0f0;
                    color: black;
                    selection-background-color: #c65f00;
                    selection-color: white;
                    outline: 0px;
                }

                QListView::item {
                    background-color: #f0f0f0;
                    color: black;
                }

                QListView::item:hover {
                    background-color: #c65f00;
                    color: white;
                }

                QListView::item:selected {
                    background-color: #c65f00;
                    color: white;
                }
            """)

        else:
            self.layerCombo.setStyleSheet("""
                QComboBox {
                    color: white;
                }

                QListView {
                    background-color: #2a2a2a;
                    color: white;
                    selection-background-color: #ffd400;
                    selection-color: black;
                    outline: 0px;
                }

                QListView::item {
                    background-color: #2a2a2a;
                    color: white;
                }

                QListView::item:hover {
                    background-color: #ffd400;
                    color: black;
                }

                QListView::item:selected {
                    background-color: #ffd400;
                    color: black;
                }
            """)

            self.fieldCombo.setStyleSheet("""
                QComboBox {
                    color: white;
                }

                QListView {
                    background-color: #2a2a2a;
                    color: white;
                    selection-background-color: #ffd400;
                    selection-color: black;
                    outline: 0px;
                }

                QListView::item {
                    background-color: #2a2a2a;
                    color: white;
                }

                QListView::item:hover {
                    background-color: #ffd400;
                    color: black;
                }

                QListView::item:selected {
                    background-color: #ffd400;
                    color: black;
                }
            """)

        self.apply_combo_style(creation_mode=False)

        if ui_theme == "default":
            self.valueList.setStyleSheet("""
                QListWidget {
                    background-color: #fafafa;
                    border: none;
                }

                QListWidget::item {
                    padding: 0px;            
                    margin: 0px;
                    background-color: #f0f0f0;
                    border: none;
                    color: #333333;
                }

                QListWidget[classMenuOpen="false"]::item:hover:!selected {
                    background-color: #f2f2f2;
                }

                QListWidget::item:selected {
                    background-color: #cc4c02;
                    border: 2px solid #cc4c02;
                    color: white;
                    font-weight: bold;
                }
            """)
        else:
            self.valueList.setStyleSheet("""
                QListWidget {
                    background-color: black;
                    border: none;
                }

                QListWidget::item {
                    padding: 0px;            
                    margin: 0px;
                    background-color: black;
                    border: none;
                    color: white;
                }

                QListWidget[classMenuOpen="false"]::item:hover:!selected {
                    background-color: #4a4a4a;
                }

                QListWidget::item:selected {
                    background-color: #ffd400;
                    border: 2px solid #ffd400;
                    color: black;
                    font-weight: bold;
                }
            """)

        self.apply_value_list_base_style()

        # Refresh button
        self.refreshButton = self.findChild(object, 'refreshButton')

        self.refreshButton.setStyleSheet("""
            QPushButton {
                background-color: #e8f1fb;
                color: #1f4e79;
                font-size: 14px;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #b7cde3;
                border-radius: 6px;
            }

            QPushButton:hover {
                background-color: #357abd;
                color: white;
            }

            QPushButton:pressed {
                background-color: #2c5f99;
                color: white;
            }
        """)

        # Info label
        self.infoLabel = self.findChild(object, 'infoLabel')
        self.apply_info_label_style()

        # Sidebar size
        self.setMinimumWidth(120)
        self.setMaximumWidth(16777215)

        self.valueList.setMinimumWidth(80)
        self.layerCombo.setMinimumWidth(80)
        self.fieldCombo.setMinimumWidth(80)
        self.infoLabel.setMinimumWidth(80)
        self.infoLabel.setWordWrap(True)

        # Internal stateh
        self.current_layer = None
        self.current_field = None
        self.current_value = None
        self.current_apply_value = None
        self.map_tool = None
        self.shortcuts = []
        self.shortcut_by_value = {}
        self.entity_creation_mode = False
        self.entity_creation_layer = None
        self.entity_creation_field = None
        self.entity_creation_value = None
        self.entity_creation_map_tool = None
        self.entity_creation_original_suppress = None
        self.entity_creation_original_defaults = {}
        self.entity_creation_form_suppressed = False
        self.entity_creation_auto_fields = {}
        self.entity_creation_cached_auto_fields = {}
        self.entity_creation_blocking_fields = []
        self.entity_creation_constraints_cached = False
        self.entity_creation_map_tool_signal_connected = False
        self.value_cache = {}
        self.value_cache_signal_layers = set()

        # Create features by class button
        self.exitClassModeButton = QPushButton(self.tr("Create features by class"))
        self.exitClassModeButton.clicked.connect(self.toggle_feature_creation_mode)

        # Initial state (inactive)
        self.set_exit_button_inactive()
       
        self.contactLabel = QLabel()
        self.contactLabel.setOpenExternalLinks(False)
        self.contactLabel.setTextFormat(RICH_TEXT)
        self.contactLabel.setAlignment(ALIGN_CENTER)

        contact_color = "#008cff"

        self.contactLabel.setText(
            f'<a href="contact" '
            f'style="color: {contact_color}; text-decoration: none;">'
            f'<b>{self.tr("Contact questions?")}</b></a>'
        )
        self.contactLabel.linkActivated.connect(
            lambda _link: self.show_contact_dialog()
        )
        self.contactLabel.setStyleSheet("""
            QLabel {
                font-size: 12px;
                padding-top: 2px;
            }
        """)

        parent_widget = self.valueList.parent()
        if parent_widget and parent_widget.layout():
            parent_layout = parent_widget.layout()
            refresh_index = parent_layout.indexOf(self.refreshButton)

            if refresh_index >= 0:
                parent_layout.insertWidget(refresh_index, self.exitClassModeButton)
            else:
                parent_layout.addWidget(self.exitClassModeButton)

            parent_layout.addWidget(self.contactLabel)

        # Signals
        self.refreshButton.clicked.connect(self.refresh_sidebar)
        self.layerCombo.currentIndexChanged.connect(self.layer_changed)
        self.fieldCombo.currentIndexChanged.connect(self.field_changed)
        self.valueList.itemClicked.connect(self.value_selected)

        # Right-click on a class: symbol / shortcut / remove shortcut
        self.valueList.viewport().installEventFilter(self)
        self.valueList.setContextMenuPolicy(CUSTOM_CONTEXT_MENU)
        self.valueList.customContextMenuRequested.connect(self.show_class_context_menu)

        # Prepare shortcut system
        self.create_shortcuts()
        self.load_shortcuts_from_project()
        self.load_layers()

        # Sync with active layer
        iface.currentLayerChanged.connect(self.sync_with_active_layer)

        try:
            QgsProject.instance().layersAdded.connect(self.project_layers_added)
        except Exception:
            try:
                QgsProject.instance().layerWasAdded.connect(self.project_layers_added)
            except Exception as error:
                log_exception("Could not connect project layer signals", error)

        self.sync_with_active_layer(iface.activeLayer())

    def eventFilter(self, watched, event):
        """Keep right-clicks from selecting or activating a different class."""
        if watched is self.valueList.viewport():
            event_type = event.type()
            if event_type in (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.MouseButtonDblClick,
            ):
                if event.button() == RIGHT_BUTTON:
                    if event_type != QEvent.Type.MouseButtonRelease:
                        self.set_class_menu_open(True)
                    return True

                if event_type == QEvent.Type.MouseButtonPress:
                    self.set_class_menu_open(False)

            elif event_type == QEvent.Type.MouseMove:
                if (
                    not getattr(self, "_class_context_menu_visible", False)
                    and not event.buttons() & RIGHT_BUTTON
                ):
                    self.set_class_menu_open(False)

        return super().eventFilter(watched, event)

    def set_class_menu_open(self, menu_open):
        """Refresh hover styling immediately, without changing selection."""
        if self.valueList.property("classMenuOpen") == menu_open:
            return

        self.valueList.setProperty("classMenuOpen", menu_open)
        self.valueList.setStyleSheet(self.valueList.styleSheet())
        self.valueList.viewport().repaint()

    def showEvent(self, event):
        """Resume sidebar work when the dock becomes visible."""
        super().showEvent(event)
        QTimer.singleShot(0, self.resume_sidebar_when_visible)

    def hideEvent(self, event):
        """Stop active tools while the dock is hidden."""
        super().hideEvent(event)

        if self.entity_creation_mode:
            self.exit_feature_creation_mode(update_info=False)

        if self.map_tool:
            self.exit_class_mode(update_info=False)

    def resume_sidebar_when_visible(self):
        """Synchronize once when the sidebar wakes from hibernation."""
        if not self.isVisible():
            return

        self.load_layers(target_layer=iface.activeLayer())

    def project_layers_added(self, _layers=None):
        """Refresh the layer combo after new layers are added to the project."""
        if not self.isVisible():
            return

        QTimer.singleShot(0, lambda: self.load_layers(target_layer=iface.activeLayer()))

    def setup_title_bar(self):
        """Custom title bar for the dock."""
        title_widget = QWidget()
        title_outer = QVBoxLayout(title_widget)
        title_outer.setContentsMargins(0, 0, 0, 0)
        title_outer.setSpacing(0)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(4, 0, 0, 0)
        title_row.setSpacing(0)

        title_label = QLabel(self.tr("Vector Class Manager"))
        title_color = "white" if self.is_dark_interface() else "black"
        title_label.setStyleSheet(f"font-weight: bold; color: {title_color};")
        title_row.addWidget(title_label)
        title_row.addStretch()

        icon_size = self.style().pixelMetric(SMALL_ICON_SIZE)

        float_btn = QToolButton()
        float_btn.setIcon(self.style().standardIcon(TITLE_BAR_NORMAL_BUTTON))
        float_btn.setFixedSize(icon_size + 4, icon_size + 4)
        float_btn.setAutoRaise(True)
        float_btn.clicked.connect(lambda: self.setFloating(not self.isFloating()))
        title_row.addWidget(float_btn)

        close_btn = QToolButton()
        close_btn.setIcon(self.style().standardIcon(TITLE_BAR_CLOSE_BUTTON))
        close_btn.setFixedSize(icon_size + 4, icon_size + 4)
        close_btn.setAutoRaise(True)
        close_btn.clicked.connect(self.close)
        title_row.addWidget(close_btn)

        title_outer.addLayout(title_row)

        separator = QFrame()
        separator.setFrameShape(FRAME_HLINE)
        separator.setFrameShadow(FRAME_SUNKEN)
        title_outer.addWidget(separator)

        self.setTitleBarWidget(title_widget)

    def apply_ui_font(self):
        """Fuente del Panel."""
        app = QApplication.instance()

        if app:
            self.setFont(app.font())

    def is_dark_interface(self):
        """Detect whether the current Qt palette is visually dark."""
        color = self.palette().color(self.backgroundRole())
        luminance = (
            0.299 * color.red()
            + 0.587 * color.green()
            + 0.114 * color.blue()
        )

        return luminance < 128

    def theme_variant(self):
        """Return light, dark, or default_dark for QGIS 4 default dark palettes."""
        settings = QgsSettings()
        ui_theme = str(settings.value("UI/UITheme", "default")).strip().lower()

        if ui_theme == "default":
            return "default_dark" if self.is_dark_interface() else "light"

        return "dark"

    def apply_info_label_style(self):
        """Keep status messages readable in light, dark, and QGIS 4 default-dark themes."""
        text_color = "#333333" if self.theme_variant() == "light" else "white"

        self.infoLabel.setStyleSheet(f"""
            QLabel {{
                font-size: 13px;
                color: {text_color};
            }}
        """)

    def combo_style_values(self, creation_mode=False):
        """Return combo colors without changing plugin behavior."""
        variant = self.theme_variant()

        if creation_mode:
            selected_bg, _border, selected_text = self.creation_value_list_style()
            hover_bg = "#c6dbef"
        else:
            if variant == "dark":
                selected_bg = "#ffd400"
                selected_text = "black"
                hover_bg = "#fee8c8"
            else:
                selected_bg = "#c65f00"
                selected_text = "white"
                hover_bg = "#fdd0a2"

        if variant == "dark":
            combo_bg = "#2a2a2a"
            combo_text = "white"
            popup_bg = "#2a2a2a"
            popup_text = "white"
        else:
            combo_bg = "#f0f0f0"
            combo_text = "black"
            popup_bg = "#f0f0f0"
            popup_text = "black"

        hover_text = "black"

        return combo_bg, combo_text, popup_bg, popup_text, hover_bg, hover_text, selected_bg, selected_text

    def apply_combo_style(self, creation_mode=False):
        """Apply layer/field combo styling for the current visual mode."""
        (
            combo_bg,
            combo_text,
            popup_bg,
            popup_text,
            hover_bg,
            hover_text,
            selected_bg,
            selected_text,
        ) = self.combo_style_values(creation_mode)

        style = f"""
            QComboBox {{
                background-color: {combo_bg};
                color: {combo_text};
                selection-background-color: {hover_bg};
                selection-color: {hover_text};
            }}

            QComboBox:hover {{
                background-color: {hover_bg};
                color: {hover_text};
            }}

            QListView {{
                background-color: {popup_bg};
                color: {popup_text};
                selection-background-color: {selected_bg};
                selection-color: {selected_text};
                outline: 0px;
            }}

            QListView::item {{
                background-color: {popup_bg};
                color: {popup_text};
            }}

            QListView::item:hover {{
                background-color: {selected_bg};
                color: {selected_text};
            }}

            QListView::item:selected {{
                background-color: {selected_bg};
                color: {selected_text};
            }}
        """

        self.layerCombo.setStyleSheet(style)
        self.fieldCombo.setStyleSheet(style)

    def apply_value_list_base_style(self):
        """Apply class list colors for the current Qt/QGIS appearance."""
        variant = self.theme_variant()

        if variant == "dark":
            self.valueList.setStyleSheet("""
                QListWidget {
                    background-color: black;
                    border: none;
                }

                QListWidget::item {
                    padding: 0px;
                    margin: 0px;
                    background-color: black;
                    border: none;
                    color: white;
                }

                QListWidget[classMenuOpen="false"]::item:hover:!selected {
                    background-color: #fee6ce;
                    color: black;
                }

                QListWidget::item:selected {
                    background-color: #ffd400;
                    border: 2px solid #ffd400;
                    color: black;
                    font-weight: bold;
                }
            """)
            return

        self.valueList.setStyleSheet("""
            QListWidget {
                background-color: #fafafa;
                border: none;
            }

            QListWidget::item {
                padding: 0px;
                margin: 0px;
                background-color: #f0f0f0;
                border: none;
                color: #333333;
            }

            QListWidget[classMenuOpen="false"]::item:hover:!selected {
                background-color: #fdd0a2;
                color: black;
            }

            QListWidget::item:selected {
                background-color: #cc4c02;
                border: 2px solid #cc4c02;
                color: white;
                font-weight: bold;
            }
        """)

    def field_memory_key(self, layer):
        """Remember the most recent field used for each layer."""
        layer_id = self.layer_id_or_none(layer)

        if not layer_id:
            return ""

        return f"last_field_{layer_id}"

    def layer_id_or_none(self, layer):
        """Return the layer id only while the QGIS layer object is still alive."""
        if layer is None:
            return None

        try:
            return layer.id()
        except RuntimeError:
            return None

    def save_last_field_for_layer(self):
        if not self.layer_id_or_none(self.current_layer) or not self.current_field:
            return

        QgsProject.instance().writeEntry(
            "VectorClassManager",
            self.field_memory_key(self.current_layer),
            self.current_field
        )


    def get_last_field_for_layer(self, layer):
        if not self.layer_id_or_none(layer):
            return ""

        value, ok = QgsProject.instance().readEntry(
            "VectorClassManager",
            self.field_memory_key(layer),
            ""
        )

        return value if ok else ""

    def value_cache_key(self, layer=None, field_name=None):
        """Build the cache key used for the current layer and field."""
        if layer is None:
            layer = self.current_layer

        field_name = field_name or self.current_field
        layer_id = self.layer_id_or_none(layer)

        if not layer_id or not field_name:
            return None

        return (layer_id, field_name)

    def clear_value_cache(self, layer=None, field_name=None, layer_id=None):
        """Clear cached sidebar values after Refresh or layer edits."""
        if layer_id is None:
            layer_id = self.layer_id_or_none(layer)

        if layer_id is None and field_name is None:
            self.value_cache.clear()
            return

        for cache_key in list(self.value_cache.keys()):
            cache_layer_id, cache_field_name = cache_key

            if layer_id is not None and cache_layer_id != layer_id:
                continue

            if field_name is not None and cache_field_name != field_name:
                continue

            self.value_cache.pop(cache_key, None)

    def clear_value_cache_for_field_index(self, layer_id, field_index):
        """Clear cached values only for the edited attribute field."""
        layer = QgsProject.instance().mapLayer(layer_id)

        if not layer:
            self.clear_value_cache(layer_id=layer_id)
            return

        try:
            field = layer.fields().field(field_index)
            field_name = field.name() if field is not None else None
        except Exception:
            field_name = None

        if field_name:
            self.clear_value_cache(layer_id=layer_id, field_name=field_name)
        else:
            self.clear_value_cache(layer_id=layer_id)

    def connect_value_cache_signals(self, layer):
        """Invalidate cached sidebar values when an editable layer changes."""
        if not isinstance(layer, QgsVectorLayer):
            return

        layer_id = layer.id()

        if layer_id in self.value_cache_signal_layers:
            return

        self.value_cache_signal_layers.add(layer_id)

        try:
            layer.attributeValueChanged.connect(
                lambda _fid, field_index, _value, layer_id=layer_id:
                    self.clear_value_cache_for_field_index(layer_id, field_index)
            )
        except Exception as error:
            log_exception("Could not monitor attribute changes", error)

        for signal_name in (
            "featureAdded",
            "featureDeleted",
            "geometryChanged",
            "editingStopped",
            "beforeCommitChanges",
            "afterCommitChanges",
            "committedFeaturesAdded",
            "committedFeaturesRemoved",
            "committedAttributeValuesChanges",
            "committedGeometriesChanges",
            "rolledBack",
        ):
            signal = getattr(layer, signal_name, None)

            if signal is None:
                continue

            try:
                signal.connect(
                    lambda *args, layer_id=layer_id:
                        self.clear_value_cache(layer_id=layer_id)
                )
            except Exception as error:
                log_exception(
                    f"Could not connect layer signal {signal_name}", error
                )

    def contact_email(self):
        """Contact email."""
        return 'huaytahe@outlook.com'

    def contact_mailto_url(self):
        """Contacto."""
        subject = quote(self.tr("Question about Vector Class Manager"))
        body = quote(self.tr("Hello,\n\nI have a question about Vector Class Manager."))

        return f"mailto:{self.contact_email()}?subject={subject}&body={body}"

    def open_contact_email(self):
        QDesktopServices.openUrl(
            QUrl.fromEncoded(self.contact_mailto_url().encode("utf-8"))
        )

    def copy_contact_email(self, feedback_label=None):
        QApplication.clipboard().setText(self.contact_email())

        if feedback_label:
            feedback_label.setText(self.tr("Email copied to clipboard."))
            QTimer.singleShot(2500, feedback_label.clear)

    def show_contact_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Contact questions?"))
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(self.tr("For questions and support, write to:"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        email_label = QLabel(
            f'<a href="{self.contact_mailto_url()}">{self.contact_email()}</a>'
        )
        email_label.setTextFormat(RICH_TEXT)
        email_label.setOpenExternalLinks(False)
        email_label.linkActivated.connect(lambda _link: self.open_contact_email())
        layout.addWidget(email_label)

        button_layout = QHBoxLayout()

        open_button = QPushButton(self.tr("Open email"))
        copy_button = QPushButton(self.tr("Copy email"))
        close_button = QPushButton(self.tr("Close"))

        feedback_label = QLabel("")
        feedback_label.setAlignment(ALIGN_CENTER)
        feedback_label.setStyleSheet("""
            QLabel {
                color: #238b45;
                font-weight: bold;
                padding-top: 4px;
            }
        """)

        open_button.clicked.connect(self.open_contact_email)
        copy_button.clicked.connect(lambda: self.copy_contact_email(feedback_label))
        close_button.clicked.connect(dialog.accept)

        button_layout.addWidget(open_button)
        button_layout.addWidget(copy_button)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)
        layout.addWidget(feedback_label)
        qt_exec(dialog)

    def load_layers(self, target_layer=None):
        """Load layers."""
        current_layer_id = self.layer_id_or_none(self.current_layer)

        if self.current_layer is not None and current_layer_id is None:
            self.current_layer = None

        active_layer = target_layer if target_layer is not None else iface.activeLayer()
        active_layer_id = self.layer_id_or_none(active_layer) if isinstance(active_layer, QgsVectorLayer) else None
        target_layer_id = active_layer_id if target_layer is not None else (current_layer_id or active_layer_id)
        target_index = -1

        self.layerCombo.blockSignals(True)
        self.layerCombo.clear()
        layers = QgsProject.instance().mapLayers().values()

        for lyr in layers:
            if isinstance(lyr, QgsVectorLayer):
                self.connect_value_cache_signals(lyr)
                self.layerCombo.addItem(lyr.name(), lyr.id())

                if target_layer_id and lyr.id() == target_layer_id:
                    target_index = self.layerCombo.count() - 1

        if target_index < 0 and self.layerCombo.count() > 0:
            target_index = 0

        if target_index >= 0:
            self.layerCombo.setCurrentIndex(target_index)

        self.layerCombo.blockSignals(False)

        if target_index >= 0:
            layer_id = self.layerCombo.itemData(target_index)
            layer = QgsProject.instance().mapLayer(layer_id)

            if layer:
                self.current_layer = layer
                self.load_fields()

    def sync_with_active_layer(self, layer):
        """Sync with the active layer."""
        if not self.isVisible():
            return

        layer_id = self.layer_id_or_none(layer)

        if layer_id is None:
            if self.current_layer is not None and self.layer_id_or_none(self.current_layer) is None:
                if self.entity_creation_mode:
                    self.exit_feature_creation_mode(update_info=False)

                if self.map_tool:
                    self.exit_class_mode(update_info=False)

                self.current_layer = None
            return

        current_layer_id = self.layer_id_or_none(self.current_layer)

        if self.current_layer is not None and current_layer_id is None:
            if self.entity_creation_mode:
                self.exit_feature_creation_mode(update_info=False)

            if self.map_tool:
                self.exit_class_mode(update_info=False)

            self.current_layer = None

        if (
            current_layer_id
            and layer_id != current_layer_id
            and self.entity_creation_mode
        ):
            self.exit_feature_creation_mode(update_info=False)

        if self.map_tool and current_layer_id and layer_id != current_layer_id:
            self.exit_class_mode(update_info=False)

        found_layer = False

        for i in range(self.layerCombo.count()):
            combo_layer_id = self.layerCombo.itemData(i)

            if combo_layer_id == layer_id:
                found_layer = True
                self.layerCombo.blockSignals(True)
                self.layerCombo.setCurrentIndex(i)
                self.layerCombo.blockSignals(False)

                self.current_layer = layer
                self.load_fields()

                break

        if not found_layer:
            QTimer.singleShot(0, lambda layer=layer: self.load_layers(target_layer=layer))

    def layer_changed(self, index):
        """Layer changed."""
        layer_id = self.layerCombo.itemData(index)
        layer = QgsProject.instance().mapLayer(layer_id)

        if not layer:
            return

        if self.entity_creation_mode:
            self.exit_feature_creation_mode(update_info=False)

        if self.map_tool:
            self.exit_class_mode(update_info=False)

        self.current_layer = layer

        # Reset shortcut context
        self.current_field = None
        self.shortcut_by_value = {}
        self.rebuild_shortcuts()

        # Load fields
        self.load_fields()

    def load_fields(self):
        """Load fields."""
        self.fieldCombo.blockSignals(True)
        self.fieldCombo.clear()

        if not self.current_layer:
            self.fieldCombo.blockSignals(False)
            return

        for field in self.current_layer.fields():
            self.fieldCombo.addItem(field.name())

        last_field = self.get_last_field_for_layer(self.current_layer)

        if last_field:
            index = self.fieldCombo.findText(last_field)

            if index >= 0:
                self.fieldCombo.setCurrentIndex(index)

        self.fieldCombo.blockSignals(False)

        self.field_changed(self.fieldCombo.currentIndex())

    def field_changed(self, index):
        """Field changed."""
        if index < 0:
            self.current_field = None
            return

        if self.entity_creation_mode:
            self.exit_feature_creation_mode(update_info=False)

        if self.map_tool:
            self.exit_class_mode(update_info=False)

        self.current_field = self.fieldCombo.currentText()

        if not self.current_field:
            return

        self.save_last_field_for_layer()
        self.load_shortcuts_from_project()
        self.load_values()

    def refresh_sidebar(self):
        """Refresh the sidebar and leave active modes."""
        if self.entity_creation_mode:
            self.exit_feature_creation_mode(update_info=False)

        if self.map_tool:
            self.exit_class_mode(update_info=False)

        self.clear_value_cache()
        self.load_layers(target_layer=iface.activeLayer())

    def is_real_null_value(self, value):
        """Detect real provider NULL values without treating text as NULL."""
        if isinstance(value, str):
            return False

        if value is None:
            return True

        try:
            if value == NULL:
                return True
        except Exception as error:
            log_exception(
                "Could not compare the value with QGIS NULL",
                error,
                warning=False,
            )

        try:
            return bool(value.isNull())
        except Exception:
            return False

    def null_category_labels(self):
        return {
            "null",
            "nul",
            "none",
            "no value",
            "empty",
            "blank",
            "without value",
            "null / no value",
            "null / sin valor",
            "null/sin valor",
            "sin valor",
            "vacio",
            "vacío",
            "vacÃ­o",
            "nulo",
            "sin dato",
            "sin datos",
            "sans valeur",
            "vide",
            "nulle",
            "valeur nulle",
            "valeur vide",
            "aucune valeur",
            "all other values",
            "all others",
            "other values",
            "others",
            "otros valores",
            "todos los demás valores",
            "todos los demas valores",
            "autres valeurs",
            "toutes les autres valeurs",
        }

    def is_null_renderer_category(self, category):
        """Detect renderer categories intended for real null/empty values."""
        cat_value = category.value()
        cat_value_text = str(cat_value).strip()
        cat_label = str(category.label()).strip().lower()

        return (
            self.is_real_null_value(cat_value)
            or cat_value_text == ""
            or cat_label in self.null_category_labels()
        )

    def current_field_is_numeric(self):
        """Detect numeric class fields before using tolerant numeric matching."""
        if not self.current_layer or not self.current_field:
            return False

        try:
            field = self.current_layer.fields().field(self.current_field)
            type_name = str(field.typeName()).lower() if field is not None else ""
        except Exception:
            return False

        numeric_tokens = ("int", "real", "double", "float", "numeric", "decimal")
        return any(token in type_name for token in numeric_tokens)

    def field_is_text_like(self, field):
        """Detect text fields for length validation."""
        try:
            type_name = str(field.typeName()).strip().lower()
        except Exception:
            return False

        text_tokens = ("string", "text", "char", "varchar", "nvarchar", "bpchar")
        return any(token in type_name for token in text_tokens)

    def field_type_display(self, field):
        """Return a readable field type for validation messages."""
        try:
            display_type = str(field.displayType()).strip()
        except Exception:
            display_type = ""

        if display_type:
            return display_type

        try:
            type_name = str(field.typeName()).strip()
        except Exception:
            type_name = ""

        if not type_name:
            try:
                type_name = str(field.type())
            except Exception:
                type_name = self.tr("selected field")

        try:
            length = int(field.length())
        except Exception:
            length = 0

        try:
            precision = int(field.precision())
        except Exception:
            precision = 0

        if length > 0 and "(" not in type_name:
            if precision > 0:
                return f"{type_name}({length},{precision})"

            return f"{type_name}({length})"

        return type_name

    def validate_class_value_for_field(self, field, value):
        """Validate and convert a renamed class value for the selected field."""
        field_type = self.field_type_display(field)
        type_name = str(field.typeName()).strip().lower()

        if self.field_is_text_like(field):
            try:
                max_length = int(field.length())
            except Exception:
                max_length = 0

            if max_length > 0 and len(value) > max_length:
                return (
                    False,
                    None,
                    self.tr("This field is {field_type}. The new value is too long for this class.").format(
                        field_type=field_type
                    )
                )

        if is_integer_field(field):
            integer_text = value.lstrip("+-")

            if not integer_text.isdigit():
                return (
                    False,
                    None,
                    self.tr("This field stores {field_type} values. Use a valid value for this class.").format(
                        field_type=field_type
                    )
                )

        if type_name in ("bool", "boolean"):
            boolean_values = {
                "true": True,
                "t": True,
                "1": True,
                "yes": True,
                "y": True,
                "oui": True,
                "o": True,
                "si": True,
                "sí": True,
                "false": False,
                "f": False,
                "0": False,
                "no": False,
                "n": False,
                "non": False,
            }
            boolean_value = boolean_values.get(value.casefold())

            if boolean_value is None:
                return (
                    False,
                    None,
                    self.tr("This field stores {field_type} values. Use a valid value for this class.").format(
                        field_type=field_type
                    )
                )

            return True, boolean_value, ""

        try:
            converted_value = field.convertCompatible(value)
        except Exception:
            return (
                False,
                None,
                self.tr("This field stores {field_type} values. Use a valid value for this class.").format(
                    field_type=field_type
                )
            )

        return True, converted_value, ""

    def prompt_for_class_value(
        self,
        title,
        prompt,
        explanation,
        field,
        unchanged_value=None
    ):
        """Ask for a class value and validate it while the user types."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setFixedWidth(430)

        layout = QVBoxLayout(dialog)

        prompt_label = QLabel(prompt, dialog)
        prompt_label.setTextFormat(RICH_TEXT)
        prompt_label.setWordWrap(True)
        layout.addWidget(prompt_label)

        explanation_label = QLabel(explanation, dialog)
        explanation_label.setWordWrap(True)
        explanation_label.setStyleSheet("QLabel { font-weight: 600; }")
        layout.addWidget(explanation_label)

        value_edit = QLineEdit(dialog)
        layout.addWidget(value_edit)

        warning_label = QLabel(dialog)
        warning_label.setWordWrap(True)
        warning_color = "#ffb4ab" if self.theme_variant() == "dark" else "#b3261e"
        warning_label.setStyleSheet(
            f"QLabel {{ color: {warning_color}; font-weight: 600; }}"
        )
        layout.addWidget(warning_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton(self.tr("OK"), dialog)
        cancel_button = QPushButton(self.tr("Cancel"), dialog)
        ok_button.setEnabled(False)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        converted_value = {"value": None}

        def update_validation(text):
            candidate = text.strip()

            if not candidate or (
                unchanged_value is not None and candidate == unchanged_value
            ):
                converted_value["value"] = None
                warning_label.clear()
                ok_button.setEnabled(False)
                return

            valid, field_value, message = self.validate_class_value_for_field(
                field,
                candidate
            )
            converted_value["value"] = field_value if valid else None
            warning_label.setText("" if valid else message)
            ok_button.setEnabled(valid)

        value_edit.textChanged.connect(update_validation)
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        value_edit.setFocus()

        if not qt_exec(dialog):
            return None, False

        return converted_value["value"], True

    def highlighted_field_name(self, field):
        """Format a field name for class-value dialogs."""
        field_color = "#4da3ff" if self.theme_variant() == "dark" else "#0066ff"
        return (
            f'<span style="color: {field_color}; font-weight: 600;">'
            f'{escape(str(field.name()))}</span>'
        )

    def prompt_for_renamed_class_value(self, old_value, field):
        """Ask for a renamed class value."""
        return self.prompt_for_class_value(
            self.tr("Rename class"),
            self.tr("New value for class '{value}' in the '{field}' field:").format(
                value=escape(str(old_value)),
                field=self.highlighted_field_name(field)
            ),
            self.tr(
                "This will update the value in the attribute table, not only the class label shown here."
            ),
            field,
            unchanged_value=old_value
        )

    def number_for_renderer_match(self, value):
        """Convert a renderer/table value to a number only when it is safe."""
        if isinstance(value, bool):
            return None

        try:
            text = str(value).strip()
        except Exception:
            return None

        if not text:
            return None

        try:
            return float(text)
        except Exception:
            return None

    def renderer_values_match(self, renderer_value, value, text):
        """Match renderer values to table values without changing stored values."""
        if self.is_real_null_value(renderer_value) or self.is_real_null_value(value):
            return False

        try:
            if renderer_value == value:
                return True
        except Exception as error:
            log_exception(
                "Could not compare category values directly",
                error,
                warning=False,
            )

        renderer_text = str(renderer_value).strip()
        value_text = str(text).strip()

        if renderer_text == value_text:
            return True

        has_numeric_value = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
        )
        has_numeric_renderer_value = (
            isinstance(renderer_value, (int, float))
            and not isinstance(renderer_value, bool)
        )

        if not (self.current_field_is_numeric() or has_numeric_value or has_numeric_renderer_value):
            return False

        renderer_number = self.number_for_renderer_match(renderer_value)
        value_number = self.number_for_renderer_match(value)

        if renderer_number is None or value_number is None:
            return False

        return abs(renderer_number - value_number) <= 1e-12

    def renderer_category_for_sidebar_value(self, categories, value, text):
        """Find the renderer category without merging text NULL and real NULL."""
        if self.is_real_null_value(value):
            for cat in categories:
                if self.is_real_null_value(cat.value()):
                    return cat

            for cat in categories:
                if self.is_null_renderer_category(cat):
                    return cat

            return None

        for cat in categories:
            if self.renderer_values_match(cat.value(), value, text):
                return cat

        return None

    def renderer_sidebar_legend_text(self, category, text):
        """Return the optional legend text shown after the real class value."""
        if category is None:
            return ""

        try:
            label = str(category.label()).strip()
        except Exception:
            return ""

        if label.lower() in self.null_category_labels():
            return ""

        value_text = str(text).strip()

        if not label or label == value_text:
            return ""

        for separator in (':', '-', chr(8211), chr(8212)):
            if separator not in label:
                continue

            label_prefix, label_suffix = label.split(separator, 1)

            if self.renderer_values_match(label_prefix.strip(), text, text):
                label = label_suffix.strip()
                break

        if not label or label == value_text:
            return ""

        return label

    def class_sort_key(self, value):
        """Sort classes while keeping empty or NULL values at the end."""
        if self.is_real_null_value(value):
            return (1, "")

        text = str(value).strip()
        null_tokens = {"", "NULL", "(NULL)", "<NULL>"}
        is_null_like = text.upper() in null_tokens

        return (1 if is_null_like else 0, text.lower())

    def populate_value_list_from_cache(self, cache_entries):
        """Populate the sidebar from cached values and cached symbol icons."""
        self.valueList.setUpdatesEnabled(False)

        try:
            self.valueList.clear()

            for entry in cache_entries:
                text = entry.get("text", "")
                legend = entry.get("legend", "")
                item = QListWidgetItem(self.class_display_text(text, legend=legend))
                item.setData(USER_ROLE, text)
                item.setData(USER_ROLE + 2, entry.get("apply_value"))
                item.setData(USER_ROLE + 3, bool(entry.get("is_real_null", False)))
                item.setData(USER_ROLE + 4, legend)

                icon = entry.get("icon")

                if not isinstance(icon, QIcon):
                    icon = QIcon()

                item.setIcon(icon)
                item.setData(USER_ROLE + 1, icon)

                if legend:
                    item.setToolTip(f"{text} - {legend}")

                self.valueList.addItem(item)

        finally:
            self.valueList.setUpdatesEnabled(True)

        self.update_creation_item_markers()
        self.refresh_active_class_style()
        self.clear_class_field_default_for_class_mode()

    def load_values(self):
        """Load values and symbology."""
        if not self.isVisible():
            return

        if not self.current_layer or not self.current_field:
            self.valueList.clear()
            return

        idx = self.current_layer.fields().indexOf(self.current_field)

        if idx < 0:
            self.valueList.clear()
            return

        self.connect_value_cache_signals(self.current_layer)

        cache_key = self.value_cache_key()

        if cache_key in self.value_cache:
            self.populate_value_list_from_cache(self.value_cache[cache_key])
            return
            
        # Do not clean renderer categories here: it can remove template symbology classes.
        
        try:
            values = self.current_layer.uniqueValues(idx)
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Could not get unique values: {error}").format(error=e)
            )

            return

        renderer = self.current_layer.renderer()
        renderer_categories = []
        if (
            isinstance(renderer, QgsCategorizedSymbolRenderer)
            and renderer.classAttribute() == self.current_field
        ):
            renderer_categories = renderer.categories()

        values = list(values)

        if (
            renderer_categories
            and not any(self.is_real_null_value(value) for value in values)
            and any(self.is_null_renderer_category(cat) for cat in renderer_categories)
        ):
            values.append(NULL)

        cache_entries = []

        for v in sorted(values, key=self.class_sort_key):
            text = str(v)
            is_real_null = self.is_real_null_value(v)
            apply_value = None if is_real_null else text
            category = self.renderer_category_for_sidebar_value(renderer_categories, v, text)
            symbol = category.symbol().clone() if category else None
            legend = self.renderer_sidebar_legend_text(category, text)
            icon = QIcon()

            if symbol:
                pix = QPixmap(60, 40)
                pix.fill(TRANSPARENT)

                painter = QPainter(pix)
                symbol.drawPreviewIcon(painter, pix.size())
                painter.end()

                icon = QIcon(pix)

            cache_entries.append({
                "text": text,
                "apply_value": apply_value,
                "is_real_null": is_real_null,
                "legend": legend,
                "icon": icon,
            })

        if cache_key is not None:
            self.value_cache[cache_key] = cache_entries

        self.populate_value_list_from_cache(cache_entries)
        
    def clean_unused_renderer_categories(self):
        """Remove unused categories while keeping Null/empty categories."""
        if not self.current_layer or not self.current_field:
            return

        renderer = self.current_layer.renderer()

        if not isinstance(renderer, QgsCategorizedSymbolRenderer):
            return

        if renderer.classAttribute() != self.current_field:
            return

        existing_values = set()

        for feat in self.current_layer.getFeatures():
            value = feat[self.current_field]

            if value is not None and str(value).strip() != "":
                existing_values.add(str(value))

        new_categories = []

        for cat in renderer.categories():
            cat_value = cat.value()
            cat_value_str = str(cat_value).strip()
            cat_label = str(cat.label()).strip().lower()

            is_null_category = (
                cat_value is None
                or cat_value_str == ""
                or cat_label in [
                    "null",
                    "sin valor",
                    "vacío",
                    "vacio",
                    "null / sin valor",
                    "nul",
                    "sans valeur",
                    "vide",
                    "valeur nulle",
                    "valeur vide",
                    "null / sans valeur"
                ]
            )

            if cat_value_str in existing_values or is_null_category:
                new_categories.append(
                    QgsRendererCategory(
                        cat.value(),
                        cat.symbol().clone(),
                        cat.label()
                    )
                )

        new_renderer = QgsCategorizedSymbolRenderer(
            self.current_field,
            new_categories
        )

        self.current_layer.setRenderer(new_renderer)
        self.current_layer.triggerRepaint()
        iface.layerTreeView().refreshLayerSymbology(self.current_layer.id())
        self.clear_value_cache(self.current_layer, self.current_field)
        
    def value_selected(self, item):
        """Select a class from the sidebar."""
        self.current_value = self.item_class_value(item)
        self.current_apply_value = self.item_class_apply_value(item)
        self.highlight_active_class(item)

        if not self.current_layer or not self.current_field:
            return

        if self.entity_creation_mode:
            self.activate_creation_class_from_item(item, flash=True)
            return

        self.clear_class_field_default_for_class_mode()

        if not self.current_layer.isEditable():
            QMessageBox.warning(
                self,
                self.tr("Layer is not editable"),
                self.tr("Turn on editing for the layer before changing classes.")
            )
            self.infoLabel.setText(self.tr("Turn on layer editing."))
            return

        selected_ids = self.current_layer.selectedFeatureIds()

        # If there is a multi-selection, apply the class to all selected features.
        if selected_ids:
            updated = apply_value_to_feature_ids(
                self.current_layer,
                self.current_field,
                self.current_apply_value,
                selected_ids,
                self
            )

            if updated:
                self.infoLabel.setText(
                    self.tr("Active class: {value} -> {count} feature(s) updated.").format(
                        value=self.current_value,
                        count=len(selected_ids)
                    )
                )
                self.current_layer.triggerRepaint()
                self.flash_applied_item(item)

            # Do not activate class mode after applying to an existing selection.
            # This lets the user keep selecting new features with the current tool.
            if self.map_tool:
                try:
                    iface.mapCanvas().unsetMapTool(self.map_tool)
                except Exception as error:
                    log_exception("Could not stop map-click assignment", error)

                self.map_tool = None

            self.set_exit_button_inactive()
            return

        self.infoLabel.setText(
            self.tr("Class active: {value}. Left-click a feature to assign it. Right-click to exit.").format(
                value=self.current_value
            )
        )
        self.flash_applied_item(item)

        # Continuous class painting mode
        self.activate_map_tool()

    def highlight_active_class(self, active_item):
        """Highlight the active class."""
        for i in range(self.valueList.count()):
            item = self.valueList.item(i)
            font = item.font()
            font.setBold(False)
            item.setFont(font)

        font = active_item.font()
        font.setBold(True)
        active_item.setFont(font)

        self.valueList.setCurrentItem(active_item)

    def refresh_active_class_style(self):
        """Refresh the active class symbology."""
        if not self.current_value:
            return

        for i in range(self.valueList.count()):
            item = self.valueList.item(i)
            item_value = self.item_class_value(item)

            if item_value == self.current_value:
                self.highlight_active_class(item)
                break

    def flash_applied_item(self, item):
        """Visual flash after applying a class from a selection."""
        if not item:
            return

        settings = QgsSettings()
        ui_theme = str(settings.value("UI/UITheme", "default")).strip().lower()

        if ui_theme == "default":
            flash_background = "#ffd400"
            flash_text = "black"
        else:
            flash_background = "#cc4c02"
            flash_text = "white"

        current_style = self.valueList.styleSheet()
        base_style = current_style.split("/* applied-flash */", 1)[0].rstrip()
        self._value_list_base_style = base_style
        self._flash_item = item

        self.valueList.setCurrentItem(item)
        self.valueList.setStyleSheet(base_style + f"""
            /* applied-flash */
            QListWidget::item:selected {{
                background-color: {flash_background};
                border: 2px solid {flash_background};
                color: {flash_text};
                font-weight: bold;
            }}
        """)

        if not hasattr(self, "_flash_timer"):
            self._flash_timer = QTimer(self)
            self._flash_timer.setSingleShot(True)
            self._flash_timer.timeout.connect(self.restore_applied_item_style)

        # Flash duration
        self._flash_timer.start(110)

    def restore_applied_item_style(self):
        base_style = getattr(self, "_value_list_base_style", None)

        if base_style is not None:
            self.valueList.setStyleSheet(base_style)

        item = getattr(self, "_flash_item", None)

        try:
            if item:
                self.highlight_active_class(item)
        except Exception as error:
            log_exception(
                "Could not restore the class highlight",
                error,
                warning=False,
            )

    def item_class_value(self, item):
        """Get the real class value without visual helper text."""
        if not item:
            return ""

        value = item.data(USER_ROLE)

        if value is not None:
            return str(value)

        return self.clean_item_text(item.text())

    def item_class_apply_value(self, item):
        """Get the value to write, preserving real NULL values."""
        if not item:
            return ""

        if bool(item.data(USER_ROLE + 3)):
            return None

        value = item.data(USER_ROLE + 2)

        if value is not None:
            return value

        return self.item_class_value(item)

    def default_expression_literal_text(self, expression):
        """Read only simple literal defaults; leave real expressions untouched."""
        if expression is None:
            return None, False

        text = str(expression).strip()

        if not text:
            return None, False

        if text.upper() == "NULL":
            return None, True

        if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
            return text[1:-1].replace("''", "'"), True

        try:
            float(text)
            return text, True
        except Exception:
            return None, False

    def class_mode_default_matches_sidebar_value(self, literal_value):
        if literal_value is None:
            return True

        literal_text = str(literal_value)

        for i in range(self.valueList.count()):
            item = self.valueList.item(i)

            if not item:
                continue

            if self.item_class_value(item) == literal_text:
                return True

            apply_value = self.item_class_apply_value(item)

            if apply_value is not None and str(apply_value) == literal_text:
                return True

        return False

    def clear_class_field_default_for_class_mode(self):
        """Prevent native tools from inheriting a class value while class mode is used."""
        if self.entity_creation_mode or not self.current_layer or not self.current_field:
            return

        field_idx = self.current_layer.fields().indexOf(self.current_field)

        if field_idx < 0:
            return

        try:
            default_definition = self.current_layer.defaultValueDefinition(field_idx)
            expression = default_definition.expression()
        except Exception:
            return

        literal_value, is_literal = self.default_expression_literal_text(expression)

        if not is_literal:
            return

        if not self.class_mode_default_matches_sidebar_value(literal_value):
            return

        try:
            self.current_layer.setDefaultValueDefinition(
                field_idx,
                QgsDefaultValue("", False)
            )
        except Exception as error:
            log_exception("Could not clear the class field default", error)

    def class_display_text(self, value, creation_marker=False, legend=""):
        """Create visible class text while keeping shortcuts."""
        value_text = str(value)
        display_text = value_text
        legend_text = str(legend).strip() if legend else ""

        if legend_text:
            display_text = f"{display_text} - {legend_text}"

        if value_text in self.shortcut_by_value:
            display_text = f"{display_text} [{self.shortcut_by_value[value_text]}]"

        if creation_marker:
            display_text = f"{display_text} {chr(0x270e)}"

        return display_text

    def find_item_by_value(self, value):
        for i in range(self.valueList.count()):
            item = self.valueList.item(i)

            if self.item_class_value(item) == value:
                return item

        return None

    def update_creation_item_markers(self):
        """Show the pencil on the right only for the active class in creation mode."""
        for i in range(self.valueList.count()):
            item = self.valueList.item(i)
            value = self.item_class_value(item)
            is_creation_item = self.entity_creation_mode and value == self.current_value
            legend = item.data(USER_ROLE + 4) or ""
            base_icon = item.data(USER_ROLE + 1)

            if not isinstance(base_icon, QIcon):
                base_icon = QIcon()
                item.setData(USER_ROLE + 1, base_icon)

            item.setData(USER_ROLE, value)
            item.setText(self.class_display_text(value, is_creation_item, legend))
            item.setIcon(base_icon)

    def creation_value_list_style(self):
        variant = self.theme_variant()

        if variant != "dark":
            return "#6f63a6", "#6f63a6", "white"

        return "#b8aef2", "#b8aef2", "#211d35"

    def apply_creation_value_list_style(self):
        """Apply a distinct visual style for the class used to create features."""
        current_style = self.valueList.styleSheet()
        base_style = current_style.split("/* creation-flash */", 1)[0]
        base_style = base_style.split("/* applied-flash */", 1)[0]
        base_style = base_style.split("/* creation-mode */", 1)[0].rstrip()
        background, border, text_color = self.creation_value_list_style()
        hover_background = "#deebf7" if self.theme_variant() == "dark" else "#c6dbef"

        self.valueList.setStyleSheet(base_style + f"""
            /* creation-mode */
            QListWidget[classMenuOpen="false"]::item:hover:!selected {{
                background-color: {hover_background};
                color: black;
            }}

            QListWidget::item:selected {{
                background-color: {background};
                border: none;
                color: {text_color};
                font-weight: bold;
            }}
        """)

    def clear_creation_value_list_style(self):
        if hasattr(self, "_creation_flash_timer"):
            self._creation_flash_timer.stop()

        self._creation_flash_base_style = None
        self._creation_flash_item = None
        current_style = self.valueList.styleSheet()
        base_style = current_style.split("/* creation-flash */", 1)[0]
        base_style = base_style.split("/* applied-flash */", 1)[0]
        base_style = base_style.split("/* creation-mode */", 1)[0].rstrip()
        self.valueList.setStyleSheet(base_style)

    def creation_flash_style(self):
        """Return the swapped creation colors used for the click flash."""
        variant = self.theme_variant()

        if variant != "dark":
            return "#b8aef2", "#b8aef2", "#211d35"

        return "#6f63a6", "#6f63a6", "white"

    def flash_creation_item(self, item):
        """Briefly flash the selected class while creation mode is active."""
        if not item:
            return

        current_style = self.valueList.styleSheet()
        base_style = current_style.split("/* creation-flash */", 1)[0].rstrip()
        background, border, text_color = self.creation_flash_style()

        self._creation_flash_base_style = base_style
        self._creation_flash_item = item
        self.valueList.setCurrentItem(item)
        self.valueList.setStyleSheet(base_style + f"""
            /* creation-flash */
            QListWidget::item:selected {{
                background-color: {background};
                border: none;
                color: {text_color};
                font-weight: bold;
            }}
        """)

        if not hasattr(self, "_creation_flash_timer"):
            self._creation_flash_timer = QTimer(self)
            self._creation_flash_timer.setSingleShot(True)
            self._creation_flash_timer.timeout.connect(self.restore_creation_item_style)

        self._creation_flash_timer.start(110)

    def restore_creation_item_style(self):
        base_style = getattr(self, "_creation_flash_base_style", None)

        if base_style is not None:
            self.valueList.setStyleSheet(base_style)

        item = getattr(self, "_creation_flash_item", None)

        try:
            if item:
                self.highlight_active_class(item)
        except Exception as error:
            log_exception(
                "Could not restore the digitizing class highlight",
                error,
                warning=False,
            )

        self._creation_flash_base_style = None
        self._creation_flash_item = None

    def info_label_text_flash_color(self):
        settings = QgsSettings()
        ui_theme = str(settings.value("UI/UITheme", "default")).strip().lower()

        if ui_theme == "default":
            return "#0EA5E9"

        return "#67E8F9"

    def flash_info_label_text(self):
        """Flash only the infoLabel text color."""
        current_style = self.infoLabel.styleSheet()
        base_style = current_style.split("/* info-label-text-flash */", 1)[0].rstrip()
        self._info_label_base_style = base_style
        self._info_label_flash_steps = 0
        self._info_label_flash_on = False

        if not hasattr(self, "_info_label_flash_timer"):
            self._info_label_flash_timer = QTimer(self)
            self._info_label_flash_timer.setSingleShot(True)
            self._info_label_flash_timer.timeout.connect(self.toggle_info_label_text_flash)

        self._info_label_flash_timer.stop()
        self.toggle_info_label_text_flash()

    def set_info_label_text_halo(self, enabled):
        if not enabled:
            if getattr(self, "_info_label_flash_effect", None) is not None:
                self.infoLabel.setGraphicsEffect(None)
                self._info_label_flash_effect = None

            return

        effect = getattr(self, "_info_label_flash_effect", None)

        if effect is None:
            effect = QGraphicsDropShadowEffect(self.infoLabel)
            self._info_label_flash_effect = effect

        effect.setBlurRadius(12)
        effect.setOffset(0, 0)
        effect.setColor(QColor(self.info_label_text_flash_color()))
        self.infoLabel.setGraphicsEffect(effect)

    def toggle_info_label_text_flash(self):
        base_style = getattr(self, "_info_label_base_style", None)

        if base_style is None:
            return

        if getattr(self, "_info_label_flash_steps", 0) >= 6:
            self.infoLabel.setStyleSheet(base_style)
            self.set_info_label_text_halo(False)
            self._info_label_base_style = None
            return

        self._info_label_flash_on = not getattr(self, "_info_label_flash_on", False)

        if self._info_label_flash_on:
            flash_color = self.info_label_text_flash_color()
            self.set_info_label_text_halo(True)
            self.infoLabel.setStyleSheet(base_style + f"""
                /* info-label-text-flash */
                QLabel {{
                    color: {flash_color};
                }}
            """)
        else:
            self.set_info_label_text_halo(False)
            self.infoLabel.setStyleSheet(base_style)

        self._info_label_flash_steps = getattr(self, "_info_label_flash_steps", 0) + 1
        self._info_label_flash_timer.start(120)

    def stop_info_label_text_flash(self):
        if hasattr(self, "_info_label_flash_timer"):
            self._info_label_flash_timer.stop()

        base_style = getattr(self, "_info_label_base_style", None)

        if base_style is not None:
            self.infoLabel.setStyleSheet(base_style)

        self.set_info_label_text_halo(False)
        self._info_label_base_style = None
        self._info_label_flash_steps = 0
        self._info_label_flash_on = False

    def clear_feature_creation_cache(self):
        """Clear automatic values calculated for creation mode."""
        self.entity_creation_auto_fields = {}
        self.entity_creation_cached_auto_fields = {}
        self.entity_creation_blocking_fields = []
        self.entity_creation_constraints_cached = False

    def deactivate_map_tool(self):
        try:
            if self.map_tool:
                iface.mapCanvas().unsetMapTool(self.map_tool)
        except Exception as error:
            log_exception("Could not deactivate the class map tool", error)

        self.map_tool = None

    def connect_feature_creation_map_tool_signal(self):
        """Watch tool changes so temporary creation defaults do not leak to native tools."""
        if self.entity_creation_map_tool_signal_connected:
            return

        try:
            iface.mapCanvas().mapToolSet.connect(self.on_feature_creation_map_tool_changed)
            self.entity_creation_map_tool_signal_connected = True
        except Exception:
            self.entity_creation_map_tool_signal_connected = False

    def disconnect_feature_creation_map_tool_signal(self):
        if not self.entity_creation_map_tool_signal_connected:
            return

        try:
            iface.mapCanvas().mapToolSet.disconnect(self.on_feature_creation_map_tool_changed)
        except Exception as error:
            log_exception(
                "Map-tool change signal could not be disconnected",
                error,
                warning=False,
            )

        self.entity_creation_map_tool_signal_connected = False

    def feature_creation_tool_is_current(self):
        if not self.entity_creation_map_tool:
            return False

        try:
            return iface.mapCanvas().mapTool() == self.entity_creation_map_tool
        except Exception:
            return False

    def on_feature_creation_map_tool_changed(self, *args):
        if not self.entity_creation_mode or not self.entity_creation_map_tool:
            return

        new_tool = args[0] if args else None

        if new_tool is None:
            try:
                new_tool = iface.mapCanvas().mapTool()
            except Exception:
                new_tool = None

        if new_tool == self.entity_creation_map_tool:
            return

        self.restore_feature_creation_defaults()
        self.restore_feature_creation_form_config()

    def toggle_feature_creation_mode(self):
        """Start or stop feature creation by class."""
        if self.entity_creation_mode:
            self.exit_feature_creation_mode()
        else:
            self.enter_feature_creation_mode()

    def enter_feature_creation_mode(self):
        """Create new features while automatically assigning the active class."""
        if not self.current_layer or not self.current_field:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Select a layer and field before creating features.")
            )
            return

        if not self.current_layer.isEditable():
            QMessageBox.warning(
                self,
                self.tr("Layer is not editable"),
                self.tr("Turn on editing before creating features.")
            )
            return

        selected_item = None

        if self.current_value:
            selected_item = self.find_item_by_value(self.current_value)

        self.deactivate_map_tool()
        self.entity_creation_layer = self.current_layer
        self.entity_creation_field = self.current_field
        self.entity_creation_value = None
        self.clear_feature_creation_cache()

        try:
            self.entity_creation_layer.featureAdded.disconnect(self.on_feature_added_for_class)
        except Exception as error:
            log_exception(
                "Previous feature-created signal was not connected",
                error,
                warning=False,
            )

        try:
            self.entity_creation_layer.editingStopped.disconnect(self.exit_feature_creation_mode)
        except Exception as error:
            log_exception(
                "Previous editing-stopped signal was not connected",
                error,
                warning=False,
            )

        try:
            self.entity_creation_layer.featureAdded.connect(self.on_feature_added_for_class)
            self.entity_creation_layer.editingStopped.connect(self.exit_feature_creation_mode)
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Could not prepare feature creation mode: {error}").format(error=e)
            )
            self.restore_feature_creation_form_config()
            self.entity_creation_layer = None
            self.entity_creation_field = None
            self.entity_creation_value = None
            self.clear_feature_creation_cache()
            return

        self.prepare_feature_creation_cache()
        self.connect_feature_creation_map_tool_signal()

        self.entity_creation_mode = True
        self.set_exit_button_active()
        self.update_creation_item_markers()
        self.apply_combo_style(creation_mode=True)
        self.apply_creation_value_list_style()

        if selected_item:
            self.activate_creation_class_from_item(selected_item, flash=False)
            return

        self.current_value = None
        self.valueList.clearSelection()
        self.infoLabel.setText(
            self.tr("Feature creation mode is active. Select a class to start creating features.")
        )

    def activate_creation_class_from_item(self, item, flash=False):
        """Choose or change the class used by creation mode."""
        if not item:
            return False

        if not self.entity_creation_layer or not self.entity_creation_field:
            return False

        if not self.entity_creation_layer.isEditable():
            self.exit_feature_creation_mode(update_info=False)
            QMessageBox.warning(
                self,
                self.tr("Layer is not editable"),
                self.tr("Turn on editing before creating features.")
            )
            return False

        selected_value = self.item_class_value(item)
        current_map_tool = iface.mapCanvas().mapTool()
        should_activate_tool = (
            self.entity_creation_value is None
            or self.entity_creation_map_tool is None
            or current_map_tool != self.entity_creation_map_tool
        )
        self.current_value = selected_value
        self.entity_creation_value = selected_value

        self.restore_feature_creation_form_config()

        if not self.entity_creation_constraints_cached:
            self.prepare_feature_creation_cache()

        self.entity_creation_auto_fields = dict(self.entity_creation_cached_auto_fields)
        blocking_fields = list(self.entity_creation_blocking_fields)
        self.apply_feature_creation_defaults_to_layer(
            self.current_feature_creation_default_values()
        )

        if blocking_fields:
            self.infoLabel.setText(
                self.tr("Creating features with class: {value}. The attribute form will open because these required fields need a value: {fields}").format(
                    value=selected_value,
                    fields=", ".join(blocking_fields)
                )
            )
            self.flash_info_label_text()
        else:
            self.stop_info_label_text_flash()
            self.suppress_feature_creation_form(self.entity_creation_layer)
            self.infoLabel.setText(
                self.tr("Creating features with class: {value}. New features will receive this value.").format(
                    value=selected_value
                )
            )

        self.update_creation_item_markers()
        self.apply_creation_value_list_style()
        self.highlight_active_class(item)

        if flash:
            self.flash_creation_item(item)

        if should_activate_tool and not self.activate_feature_creation_tool():
            self.exit_feature_creation_mode(update_info=False)
            return False

        return True

    def exit_feature_creation_mode(self, update_info=True):
        """Stop feature creation by class."""
        layer = self.entity_creation_layer
        layer_id = self.layer_id_or_none(layer)

        if layer_id:
            try:
                layer.featureAdded.disconnect(self.on_feature_added_for_class)
            except Exception as error:
                log_exception(
                    "Feature-created signal could not be disconnected",
                    error,
                    warning=False,
                )

            try:
                layer.editingStopped.disconnect(self.exit_feature_creation_mode)
            except Exception as error:
                log_exception(
                    "Editing-stopped signal could not be disconnected",
                    error,
                    warning=False,
                )

        self.disconnect_feature_creation_map_tool_signal()

        if layer_id:
            self.restore_feature_creation_defaults()
            self.restore_feature_creation_form_config()
        else:
            self.entity_creation_original_defaults = {}
            self.entity_creation_original_suppress = None
            self.entity_creation_form_suppressed = False

        self.stop_info_label_text_flash()

        self.entity_creation_mode = False
        self.entity_creation_layer = None
        self.entity_creation_field = None
        self.entity_creation_value = None
        self.entity_creation_map_tool = None
        self.clear_feature_creation_cache()
        self.set_exit_button_inactive()
        self.update_creation_item_markers()
        self.clear_creation_value_list_style()
        self.apply_combo_style(creation_mode=False)

        try:
            iface.actionPan().trigger()
        except Exception as error:
            log_exception("Could not restore the map pan tool", error)

        if update_info:
            self.infoLabel.setText(self.tr("Feature creation mode stopped."))

    def should_auto_increment_field(self, layer, field_index):
        """Detect simple ID fields where max + 1 is safe."""
        field = layer.fields().field(field_index)

        if not field:
            return False

        field_name = field.name().strip().lower()
        id_names = {
            "id",
            "fid",
            "gid",
            "objectid",
            "object_id",
            "ogc_fid",
            "pk",
            "uid",
        }

        if field_name not in id_names and not field_name.endswith("_id"):
            return False

        if not is_integer_field(field):
            return False

        if layer.editFormConfig().readOnly(field_index):
            return False

        try:
            default_value = layer.defaultValue(field_index)

            if default_value not in (None, ""):
                return False
        except Exception as error:
            log_exception("Could not inspect the ID field default", error)

        try:
            default_definition = layer.defaultValueDefinition(field_index)

            if default_definition and default_definition.expression():
                return False
        except Exception as error:
            log_exception("Could not inspect the ID default expression", error)

        constraints = field.constraints()
        constraint_flags = constraints.constraints()
        has_not_null = bool(constraint_flags & CONSTRAINT_NOT_NULL)
        has_unique = bool(constraint_flags & CONSTRAINT_UNIQUE)

        return has_not_null or has_unique

    def next_integer_value_for_field(self, layer, field_name):
        """Calculate max + 1 for simple integer fields."""
        max_value = 0

        for feat in layer.getFeatures():
            value = feat[field_name]

            if value in (None, ""):
                continue

            try:
                value = int(value)
            except Exception as error:
                log_exception(
                    "Skipping a non-integer value while calculating an ID",
                    error,
                    warning=False,
                )
            else:
                if value > max_value:
                    max_value = value

        return max_value + 1

    def field_has_provider_default(self, layer, field_index):
        """Detectar defaults SQL del proveedor, como secuencias PostGIS."""
        try:
            provider = layer.dataProvider()

            if not provider or not hasattr(provider, "defaultValueClause"):
                return False

            default_clause = provider.defaultValueClause(field_index)
        except Exception:
            return False

        if default_clause is None:
            return False

        default_clause = str(default_clause).strip().lower()

        if not default_clause:
            return False

        provider_default_keywords = [
            "nextval(",
            "::regclass",
            "generated",
            "identity"
        ]

        return any(keyword in default_clause for keyword in provider_default_keywords)

    def prepare_feature_creation_cache(self):
        """Prepare constraints and ID values once for feature creation."""
        auto_values = {}
        blocking_fields = []
        layer = self.entity_creation_layer
        class_field = self.entity_creation_field

        if not layer or not class_field:
            self.entity_creation_cached_auto_fields = auto_values
            self.entity_creation_blocking_fields = blocking_fields
            self.entity_creation_constraints_cached = True
            return

        fields = layer.fields()
        class_field_index = fields.indexOf(class_field)

        for field_index, field in enumerate(fields):
            if field_index == class_field_index:
                continue

            if layer.editFormConfig().readOnly(field_index):
                continue

            constraints = field.constraints()
            constraint_flags = constraints.constraints()
            has_not_null = bool(constraint_flags & CONSTRAINT_NOT_NULL)
            has_unique = bool(constraint_flags & CONSTRAINT_UNIQUE)

            if not has_not_null and not has_unique:
                continue

            try:
                default_value = layer.defaultValue(field_index)

                if default_value not in (None, ""):
                    continue
            except Exception as error:
                log_exception(
                    "Could not inspect a required field default", error
                )

            try:
                default_definition = layer.defaultValueDefinition(field_index)

                if default_definition and default_definition.expression():
                    continue
            except Exception as error:
                log_exception(
                    "Could not inspect a required field default expression",
                    error,
                )

            if self.field_has_provider_default(layer, field_index):
                continue

            if self.should_auto_increment_field(layer, field_index):
                auto_values[field_index] = self.next_integer_value_for_field(layer, field.name())
            elif has_not_null or has_unique:
                blocking_fields.append(field.name())

        self.entity_creation_cached_auto_fields = auto_values
        self.entity_creation_auto_fields = dict(auto_values)
        self.entity_creation_blocking_fields = blocking_fields
        self.entity_creation_constraints_cached = True

    def prepare_feature_creation_defaults(self, layer, class_field, class_value):
        """Prepare automatic values and detect unresolved required fields."""
        auto_values = {}
        blocking_fields = []

        if not layer or not class_field:
            return auto_values, blocking_fields

        fields = layer.fields()
        class_field_index = fields.indexOf(class_field)

        if class_field_index >= 0:
            auto_values[class_field_index] = cast_value(None, layer, class_field, class_value)

        for field_index, field in enumerate(fields):
            if field_index == class_field_index:
                continue

            if layer.editFormConfig().readOnly(field_index):
                continue

            constraints = field.constraints()
            constraint_flags = constraints.constraints()
            has_not_null = bool(constraint_flags & CONSTRAINT_NOT_NULL)
            has_unique = bool(constraint_flags & CONSTRAINT_UNIQUE)

            if not has_not_null and not has_unique:
                continue

            try:
                default_value = layer.defaultValue(field_index)

                if default_value not in (None, ""):
                    continue
            except Exception as error:
                log_exception(
                    "Could not inspect a creation field default", error
                )

            try:
                default_definition = layer.defaultValueDefinition(field_index)

                if default_definition and default_definition.expression():
                    continue
            except Exception as error:
                log_exception(
                    "Could not inspect a creation field default expression",
                    error,
                )

            if self.field_has_provider_default(layer, field_index):
                continue

            if self.should_auto_increment_field(layer, field_index):
                auto_values[field_index] = self.next_integer_value_for_field(layer, field.name())
            elif has_not_null or has_unique:
                blocking_fields.append(field.name())

        return auto_values, blocking_fields

    def default_expression_for_value(self, value):
        """Build a QGIS expression literal for a temporary default value."""
        if value is None:
            return "NULL"

        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)

        text = str(value).replace("'", "''")
        return f"'{text}'"

    def current_feature_creation_default_values(self):
        """Return defaults that should be active for the next created feature."""
        layer = self.entity_creation_layer
        field_name = self.entity_creation_field
        value_text = self.entity_creation_value
        default_values = dict(self.entity_creation_auto_fields)

        if not layer or not field_name or value_text is None:
            return default_values

        field_idx = layer.fields().indexOf(field_name)

        if field_idx >= 0:
            default_values[field_idx] = cast_value(None, layer, field_name, value_text)

        return default_values

    def apply_feature_creation_defaults_to_layer(self, default_values):
        """Apply temporary layer defaults used only while creation mode is active."""
        layer = self.entity_creation_layer

        self.restore_feature_creation_defaults()

        if not layer or not default_values:
            return

        for field_idx, value in default_values.items():
            if field_idx < 0:
                continue

            field = layer.fields().field(field_idx)

            if not field:
                continue

            try:
                self.entity_creation_original_defaults[field_idx] = layer.defaultValueDefinition(field_idx)
                layer.setDefaultValueDefinition(
                    field_idx,
                    QgsDefaultValue(self.default_expression_for_value(value), False)
                )
            except Exception:
                self.entity_creation_original_defaults.pop(field_idx, None)

    def restore_feature_creation_defaults(self):
        """Restore the layer defaults that existed before creation mode changed them."""
        layer = self.entity_creation_layer or self.current_layer

        if not layer or not self.entity_creation_original_defaults:
            self.entity_creation_original_defaults = {}
            return

        for field_idx, default_definition in list(self.entity_creation_original_defaults.items()):
            try:
                layer.setDefaultValueDefinition(field_idx, default_definition)
            except Exception as error:
                log_exception("Could not restore a layer field default", error)

        self.entity_creation_original_defaults = {}

    def feature_form_suppression_on_value(self):
        """Get the form suppression value for the current QGIS version."""
        for enum_class, group_name, member_name in (
            (Qgis, "AttributeFormSuppression", "On"),
            (QgsEditFormConfig, "FeatureFormSuppress", "SuppressOn"),
        ):
            enum_group = getattr(enum_class, group_name, None)
            value = getattr(enum_group, member_name, None)
            if value is not None:
                return value

        return getattr(QgsEditFormConfig, "SuppressOn", 1)

    def suppress_feature_creation_form(self, layer):
        """Temporarily hide the native form when required attributes are already resolved."""
        if not layer:
            return

        try:
            config = layer.editFormConfig()
            self.entity_creation_original_suppress = config.suppress()
            config.setSuppress(self.feature_form_suppression_on_value())
            layer.setEditFormConfig(config)
            self.entity_creation_form_suppressed = True
        except Exception:
            self.entity_creation_original_suppress = None
            self.entity_creation_form_suppressed = False

    def restore_feature_creation_form_config(self):
        """Restore the layer's native form configuration."""
        layer = self.entity_creation_layer or self.current_layer

        if not layer or self.entity_creation_original_suppress is None:
            self.entity_creation_form_suppressed = False
            self.entity_creation_original_suppress = None
            return

        try:
            config = layer.editFormConfig()
            config.setSuppress(self.entity_creation_original_suppress)
            layer.setEditFormConfig(config)
        except Exception as error:
            log_exception("Could not restore the attribute form settings", error)

        self.entity_creation_form_suppressed = False
        self.entity_creation_original_suppress = None

    def activate_feature_creation_tool(self):
        """Activate the native add feature tool."""
        try:
            iface.setActiveLayer(self.current_layer)
        except Exception as error:
            log_exception("Could not activate the digitizing layer", error)

        try:
            action = iface.actionAddFeature()

            if action:
                action.trigger()
                self.entity_creation_map_tool = iface.mapCanvas().mapTool()
                return True
        except Exception as error:
            log_exception("Could not start the feature creation tool", error)

        QMessageBox.warning(
            self,
            self.tr("Error"),
            self.tr("Could not activate the feature creation tool.")
        )
        return False

    def on_feature_added_for_class(self, fid, retry=True):
        """Assign the active class to a newly created feature."""
        if not self.feature_creation_tool_is_current():
            return

        applied = self.apply_creation_class_to_feature(fid)

        if retry and not applied:
            QTimer.singleShot(0, lambda fid=fid: self.on_feature_added_for_class(fid, retry=False))

    def apply_creation_class_to_feature(self, fid):
        if not self.entity_creation_mode:
            return True

        layer = self.entity_creation_layer
        field_name = self.entity_creation_field
        value_text = self.entity_creation_value

        if not layer or not field_name or value_text is None:
            return True

        if not layer.isEditable():
            self.exit_feature_creation_mode(update_info=False)
            return True

        field_idx = layer.fields().indexOf(field_name)

        if field_idx < 0:
            self.exit_feature_creation_mode(update_info=False)
            return True

        try:
            feat = layer.getFeature(fid)
            
            if feat is None or not feat.isValid():
                return False

            auto_fields = dict(self.entity_creation_auto_fields)
            auto_fields[field_idx] = cast_value(feat, layer, field_name, value_text)
            pending_changes = []
            target_values = {}

            for auto_field_idx, auto_value in auto_fields.items():
                if auto_field_idx == field_idx:
                    value_to_apply = auto_value
                else:
                    auto_field = layer.fields().field(auto_field_idx)

                    if not auto_field:
                        continue

                    value_to_apply = cast_value(feat, layer, auto_field.name(), auto_value)

                target_values[auto_field_idx] = value_to_apply
                current_value = feat[auto_field_idx]

                if current_value != value_to_apply:
                    pending_changes.append((auto_field_idx, value_to_apply))

            if pending_changes:
                new_values = {}
                old_values = {}

                for auto_field_idx, value_to_apply in pending_changes:
                    new_values[auto_field_idx] = value_to_apply
                    old_values[auto_field_idx] = feat[auto_field_idx]

                if not layer.changeAttributeValues(fid, new_values, old_values, True):
                    raise RuntimeError("Could not update new feature attributes.")

            for auto_field_idx in list(self.entity_creation_cached_auto_fields):
                used_value = target_values.get(auto_field_idx, feat[auto_field_idx])

                try:
                    next_value = int(used_value) + 1
                except Exception:
                    next_value = used_value

                self.entity_creation_cached_auto_fields[auto_field_idx] = next_value
                self.entity_creation_auto_fields[auto_field_idx] = next_value

            self.apply_feature_creation_defaults_to_layer(
                self.current_feature_creation_default_values()
            )

            if pending_changes:
                layer.triggerRepaint()

            self.infoLabel.setText(
                self.tr("Creating features with class: {value}. New features will receive this value.").format(
                    value=value_text
                )
            )
            return True
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Error assigning class to new feature: {error}").format(error=e)
            )
            return True

    def activate_map_tool(self):
        """Activate class painting mode."""
        self.map_tool = MapClickTool(
            iface.mapCanvas(),
            self.current_layer,
            self.current_field,
            self.current_apply_value,
            self
        )
        iface.mapCanvas().setMapTool(self.map_tool)

    def exit_class_mode(self, update_info=True):
        """Exit class mode."""
        self.deactivate_map_tool()
        self.current_value = None
        self.current_apply_value = None
        iface.mapCanvas().setCursor(ARROW_CURSOR)

        for i in range(self.valueList.count()):
            item = self.valueList.item(i)
            font = item.font()
            font.setBold(False)
            item.setFont(font)

        self.valueList.clearSelection()

        if not self.entity_creation_mode:
            self.set_exit_button_inactive()

        if update_info:
            self.infoLabel.setText(self.tr("Class mode is off."))

    def set_exit_button_active(self):
        """Active button."""
        self.exitClassModeButton.setText(self.tr("Stop creating features by class"))
        self.exitClassModeButton.setToolTip(self.tr("Stop creating features by class"))
        self.exitClassModeButton.setStyleSheet("""
            QPushButton {
                background-color: #ef6548;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #ef6548;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #fc9272;
                color: black;
            }
            QPushButton:pressed {
                background-color: #b83f2d;
                color: white;
            }
        """)

    def set_exit_button_inactive(self):
        """Inactive button."""
        self.exitClassModeButton.setText(self.tr("Create features by class"))
        self.exitClassModeButton.setToolTip(self.tr("Create new features using the selected class"))
        self.exitClassModeButton.setStyleSheet("""
            QPushButton {
                background-color: #41ab5d;
                color: black;
                font-size: 14px;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #41ab5d;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #d9f0a3;
                color: black;
            }
            QPushButton:pressed {
                background-color: #41ab5d;
                color: white;
            }
        """)

    def show_class_context_menu(self, pos):
        """Right-click menu for a class."""
        menu = QMenu(self)

        settings = QgsSettings()
        ui_theme = str(settings.value("UI/UITheme", "default")).strip().lower()

        if ui_theme == "default":
            menu.setStyleSheet("""
                QMenu {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #cfcfcf;
                }

                QMenu::item {
                    padding: 6px 24px 6px 24px;
                    background-color: transparent;
                    color: #333333;
                }

                QMenu::item:selected {
                    background-color: #ae017e;
                    color: white;
                }

                QMenu::separator {
                    height: 1px;
                    background-color: #d0d0d0;
                    margin: 4px 8px 4px 8px;
                }
            """)
        else:
            menu.setStyleSheet("""
                QMenu {
                    background-color: black;
                    color: white;
                    border: 1px solid #555555;
                }

                QMenu::item {
                    padding: 6px 24px 6px 24px;
                    background-color: transparent;
                    color: white;
                }

                QMenu::item:selected {
                    background-color: #fff7f3;
                    color: black;
                }

                QMenu::separator {
                    height: 1px;
                    background-color: #555555;
                    margin: 4px 8px 4px 8px;
                }
            """)

        action_new_value = menu.addAction(self.tr("Assign new class to selection"))
        menu.addSeparator()

        item = self.valueList.itemAt(pos)

        action_color = None
        action_shortcut = None
        action_remove_shortcut = None

        if item:
            action_rename_class = menu.addAction(self.tr("Rename class"))
            action_color = menu.addAction(self.tr("Edit symbology"))
            action_shortcut = menu.addAction(self.tr("Assign shortcut"))
            action_remove_shortcut = menu.addAction(self.tr("Remove shortcut"))

        self._class_context_menu_visible = True
        self.set_class_menu_open(True)
        try:
            selected_action = qt_exec(menu, self.valueList.mapToGlobal(pos))
        finally:
            self._class_context_menu_visible = False
            self.set_class_menu_open(False)

        if selected_action == action_new_value:
            self.assign_new_class_to_selection()
            return
            
        if item and selected_action == action_rename_class:
            self.rename_class_value(item)
            return

        if item and selected_action == action_color:
            self.change_class_color(item)

        elif item and selected_action == action_shortcut:
            self.assign_shortcut_to_class(item)

        elif item and selected_action == action_remove_shortcut:
            self.remove_shortcut_from_class(item)
    
    def add_renderer_category_if_missing(self, class_value):
        """Add a class to the renderer without deleting the predefined template."""
        if not self.current_layer or not self.current_field:
            return

        renderer = self.current_layer.renderer()

        if not isinstance(renderer, QgsCategorizedSymbolRenderer):
            return

        if renderer.classAttribute() != self.current_field:
            return

        class_value_text = str(class_value)

        for cat in renderer.categories():
            if self.renderer_values_match(cat.value(), class_value, class_value_text):
                return

        symbol = QgsSymbol.defaultSymbol(self.current_layer.geometryType())

        if symbol:
            symbol.setColor(QColor(200, 200, 200))

        new_categories = list(renderer.categories())
        new_categories.append(
            QgsRendererCategory(
                class_value,
                symbol.clone() if symbol else None,
                class_value_text
            )
        )

        new_renderer = QgsCategorizedSymbolRenderer(
            self.current_field,
            new_categories
        )

        self.current_layer.setRenderer(new_renderer)
        self.current_layer.triggerRepaint()
        iface.layerTreeView().refreshLayerSymbology(self.current_layer.id())

    def assign_new_class_to_selection(self):
        """Create a new class from the right-click menu selection."""
        if not self.current_layer or not self.current_field:
            return

        if not self.current_layer.isEditable():
            QMessageBox.warning(
                self,
                self.tr("Layer is not editable"),
                self.tr("Turn on editing for the layer before changing classes.")
            )
            return

        selected_ids = self.current_layer.selectedFeatureIds()

        if not selected_ids:
            QMessageBox.warning(
                self,
                self.tr("No selection"),
                self.tr("Select one or more features before assigning a new class.")
            )
            return

        field_idx = self.current_layer.fields().indexOf(self.current_field)

        if field_idx < 0:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Field not found: {field}").format(
                    field=self.current_field
                )
            )
            return

        field = self.current_layer.fields().field(field_idx)
        new_value, ok = self.prompt_for_class_value(
            self.tr("New class"),
            self.tr("Enter the new class value for the '{field}' field:").format(
                field=self.highlighted_field_name(field)
            ),
            self.tr(
                "This will assign the value to the selected features in the attribute table."
            ),
            field
        )

        if not ok:
            return

        new_value_text = str(new_value)

        updated = apply_value_to_feature_ids(
            self.current_layer,
            self.current_field,
            new_value,
            selected_ids,
            self
        )

        if updated:
            self.current_value = new_value_text
            self.add_renderer_category_if_missing(new_value)
            self.clear_value_cache(self.current_layer, self.current_field)
            self.load_values()
            self.current_layer.triggerRepaint()

            self.infoLabel.setText(
                self.tr("New class '{value}' assigned to {count} feature(s).").format(
                    value=new_value,
                    count=len(selected_ids)
                )
            )

    def rename_class_value(self, item):
        """Rename a class."""
        if not self.current_layer or not self.current_field:
            return

        if not self.current_layer.isEditable():
            QMessageBox.warning(
                self,
                self.tr("Layer is not editable"),
                self.tr("Turn on editing for the layer before renaming classes.")
            )
            return

        old_value = self.item_class_value(item)

        field_idx = self.current_layer.fields().indexOf(self.current_field)

        if field_idx < 0:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Field not found: {field}").format(
                    field=self.current_field
                )
            )
            return

        field = self.current_layer.fields().field(field_idx)
        new_value, ok = self.prompt_for_renamed_class_value(
            old_value,
            field,
        )

        if not ok:
            return

        new_value_text = str(new_value)

        if new_value_text == old_value:
            return

        feature_ids = []

        for feat in self.current_layer.getFeatures():
            if str(feat[self.current_field]) == old_value:
                feature_ids.append(feat.id())

        if not feature_ids:
            QMessageBox.warning(
                self,
                self.tr("Class not found"),
                self.tr("No features were found with class '{value}'.").format(
                    value=old_value
                )
            )
            return

        updated = apply_value_to_feature_ids(
            self.current_layer,
            self.current_field,
            new_value,
            feature_ids,
            self
        )

        if not updated:
            return

        renderer = self.current_layer.renderer()

        if (
            isinstance(renderer, QgsCategorizedSymbolRenderer)
            and renderer.classAttribute() == self.current_field
        ):
            new_categories = []

            for cat in renderer.categories():
                if self.renderer_values_match(cat.value(), old_value, old_value):
                    new_cat = QgsRendererCategory(
                        new_value,
                        cat.symbol().clone(),
                        new_value
                    )
                    new_categories.append(new_cat)
                else:
                    new_categories.append(
                        QgsRendererCategory(
                            cat.value(),
                            cat.symbol().clone(),
                            cat.label()
                        )
                    )

            new_renderer = QgsCategorizedSymbolRenderer(
                self.current_field,
                new_categories
            )

            self.current_layer.setRenderer(new_renderer)
            self.current_layer.triggerRepaint()
            iface.layerTreeView().refreshLayerSymbology(self.current_layer.id())

        if old_value in self.shortcut_by_value:
            self.shortcut_by_value[new_value_text] = self.shortcut_by_value.pop(old_value)
            self.save_shortcuts_to_project()

        self.current_value = new_value_text
        self.clear_value_cache(self.current_layer, self.current_field)
        self.load_values()

        self.infoLabel.setText(
            self.tr("Class renamed: '{old_value}' -> '{new_value}' ({count} feature(s) updated).").format(
                old_value=old_value,
                new_value=new_value,
                count=len(feature_ids)
            )
        )

    def change_class_color(self, item):
        """Edit symbology from the sidebar."""
        if not self.current_layer or not self.current_field:
            return

        renderer = self.current_layer.renderer()

        if not isinstance(renderer, QgsCategorizedSymbolRenderer):
            QMessageBox.warning(
                self,
                self.tr("Unsupported symbology"),
                self.tr("The layer must use categorized symbology.")
            )
            return

        if renderer.classAttribute() != self.current_field:
            QMessageBox.warning(
                self,
                self.tr("Different symbology field"),
                self.tr("Symbology uses '{renderer_field}', but the sidebar is using '{sidebar_field}'.").format(
                    renderer_field=renderer.classAttribute(),
                    sidebar_field=self.current_field
                )
            )
            return

        class_value = self.item_class_value(item)

        target_index = -1
        target_symbol = None

        for i, cat in enumerate(renderer.categories()):
            if self.renderer_values_match(cat.value(), class_value, class_value):
                target_index = i
                target_symbol = cat.symbol().clone()
                break

        # If the category does not exist in the symbology, create it.
        if target_index < 0:
            target_symbol = QgsSymbol.defaultSymbol(self.current_layer.geometryType())
            target_symbol.setColor(QColor(200, 200, 200))

            new_category = QgsRendererCategory(
                class_value,
                target_symbol.clone(),
                class_value
            )

            new_categories = list(renderer.categories())
            new_categories.append(new_category)

            renderer = QgsCategorizedSymbolRenderer(
                self.current_field,
                new_categories
            )

            self.current_layer.setRenderer(renderer)
            self.current_layer.triggerRepaint()
            iface.layerTreeView().refreshLayerSymbology(self.current_layer.id())
            self.clear_value_cache(self.current_layer, self.current_field)

            target_index = len(new_categories) - 1

        dialog = QgsSymbolSelectorDialog(
            target_symbol,
            QgsStyle.defaultStyle(),
            self.current_layer,
            iface.mainWindow()
        )

        dialog.setWindowTitle(
            self.tr("Edit symbol: {value}").format(
                value=class_value
            )
        )

        if qt_exec(dialog):
            renderer = self.current_layer.renderer()

            if isinstance(renderer, QgsCategorizedSymbolRenderer):
                renderer.updateCategorySymbol(target_index, target_symbol)

                self.current_layer.setRenderer(renderer)
                self.current_layer.triggerRepaint()
                iface.layerTreeView().refreshLayerSymbology(self.current_layer.id())

                self.clear_value_cache(self.current_layer, self.current_field)
                self.load_values()

                self.infoLabel.setText(
                    self.tr("Symbol updated for class: {value}").format(
                        value=class_value
                    )
                )

    def create_shortcuts(self):
        """
        Prepare the custom shortcut system.
        Shortcuts are assigned from the sidebar with right-click.
        """
        self.shortcut_by_value = {}
        self.shortcuts = []

    def save_shortcuts_to_project(self):
        if not self.current_layer or not self.current_field:
            return

        key = f"shortcuts_{self.current_layer.name()}_{self.current_field}"

        data = json.dumps(self.shortcut_by_value)

        QgsProject.instance().writeEntry(
            "VectorClassManager",
            key,
            data
        )

    def load_shortcuts_from_project(self):
        if not self.current_layer or not self.current_field:
            self.shortcut_by_value = {}
            return

        key = f"shortcuts_{self.current_layer.name()}_{self.current_field}"

        data, ok = QgsProject.instance().readEntry(
            "VectorClassManager",
            key,
            "{}"
        )

        try:
            self.shortcut_by_value = json.loads(data)
        except Exception:
            self.shortcut_by_value = {}

        self.rebuild_shortcuts()

    def rebuild_shortcuts(self):
        """Rebuild the current shortcuts from the configured classes."""
        for shortcut in self.shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()

        self.shortcuts = []

        for class_value, key_sequence in self.shortcut_by_value.items():
            shortcut = QShortcut(QKeySequence(key_sequence), self)
            shortcut.activated.connect(
                lambda checked=False, value=class_value: self.activate_value_by_name(value)
            )
            self.shortcuts.append(shortcut)

    def activate_value_by_name(self, class_value):
        """
        Activate a class by its current class name.
        Works with any symbology and any value type.
        """
        for i in range(self.valueList.count()):
            item = self.valueList.item(i)
            item_value = self.item_class_value(item)

            if item_value == class_value:
                self.value_selected(item)
                return

        self.infoLabel.setText(
            self.tr("No class found for shortcut: {value}").format(
                value=class_value
            )
        )

    def assign_shortcut_to_class(self, item):
        """Assign a shortcut to a class."""
        class_value = self.item_class_value(item)

        key_sequence, ok = QInputDialog.getText(
            self,
            self.tr("Assign shortcut"),
            self.tr("Enter the shortcut for class '{value}'\nExamples: A, Z, Ctrl+1, Shift+F, Alt+M").format(
                value=class_value
            )
        )

        if not ok or not key_sequence.strip():
            return

        key_sequence = key_sequence.strip()

        # Avoid assigning the same key to two classes.
        for existing_class, existing_key in list(self.shortcut_by_value.items()):
            if existing_key.lower() == key_sequence.lower() and existing_class != class_value:
                del self.shortcut_by_value[existing_class]

        self.shortcut_by_value[class_value] = key_sequence
        self.rebuild_shortcuts()
        self.load_values()
        self.save_shortcuts_to_project()

        self.infoLabel.setText(
            self.tr("Shortcut '{key}' assigned to class: {value}").format(
                key=key_sequence,
                value=class_value
            )
        )

    def remove_shortcut_from_class(self, item):
        """Remove a shortcut from a class."""
        class_value = self.item_class_value(item)

        if class_value in self.shortcut_by_value:
            del self.shortcut_by_value[class_value]

        self.rebuild_shortcuts()
        self.load_values()
        self.save_shortcuts_to_project()

        self.infoLabel.setText(
            self.tr("Shortcut removed for class: {value}").format(
                value=class_value
            )
        )

    def clean_item_text(self, text):
        """
        Clean the visual text from the class list.
        Ejemplo: 'Friche [A]' -> 'Friche'
        """
        text = text.strip()

        if text.startswith(f"{chr(0x270e)} "):
            text = text[2:].strip()

        if text.endswith(f" {chr(0x270e)}"):
            text = text[:-2].strip()

        if " [" in text and text.endswith("]"):
            return text.rsplit(" [", 1)[0]

        return text

class MapClickTool(QgsMapToolIdentifyFeature):
    def __init__(self, canvas, layer, field_name, value, parent_widget=None):
        """Map click tool."""
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.field_name = field_name
        self.value = value
        self.parent_widget = parent_widget

    def activate(self):
        super().activate()
        self.canvas.setCursor(POINTING_HAND_CURSOR)

    def deactivate(self):
        super().deactivate()
        self.canvas.unsetCursor()

    def event_pixel_xy(self, event):
        """Return click pixel coordinates for QGIS 3 and QGIS 4 mouse events."""
        try:
            return event.x(), event.y()
        except Exception as error:
            log_exception(
                "Trying alternative mouse-event coordinate methods",
                error,
                warning=False,
            )

        for point_method_name in ("pixelPoint", "originalPixelPoint", "pos"):
            try:
                point_method = getattr(event, point_method_name, None)

                if not point_method:
                    continue

                point = point_method()
                return point.x(), point.y()
            except Exception as error:
                log_exception(
                    f"Mouse-event method {point_method_name} was unavailable",
                    error,
                    warning=False,
                )

        return None

    def canvasReleaseEvent(self, event):
        if event.button() == RIGHT_BUTTON:
            if self.parent_widget:
                self.parent_widget.exit_class_mode()
            return

        if event.button() != LEFT_BUTTON:
            return

        if not self.layer or not self.field_name:
            return

        if not self.layer.isEditable():
            translator = self.parent_widget if self.parent_widget else self.canvas

            QMessageBox.warning(
                self.parent_widget or self.canvas,
                QCoreApplication.translate("VectorClassManagerDockWidget", "Layer is not editable"),
                QCoreApplication.translate("VectorClassManagerDockWidget", "Turn on editing for the layer before changing classes.")
            )
            return

        pixel_xy = self.event_pixel_xy(event)

        if pixel_xy is None:
            return

        results = self.identify(
            pixel_xy[0],
            pixel_xy[1],
            [self.layer],
            IDENTIFY_TOP_DOWN_ALL
        )

        if not results:
            return

        feat = self.feature_at_clicked_point(event, results)

        if not feat:
            return

        updated = apply_value_to_feature_ids(
            self.layer,
            self.field_name,
            self.value,
            [feat.id()],
            self.parent_widget or self.canvas
        )

        if updated:
            self.layer.triggerRepaint()

    def feature_at_clicked_point(self, event, results):
        try:
            point = event.mapPoint()
        except Exception:
            return results[0].mFeature if results else None

        try:
            canvas_crs = self.canvas.mapSettings().destinationCrs()
            layer_crs = self.layer.crs()

            if canvas_crs != layer_crs:
                transform = QgsCoordinateTransform(
                    canvas_crs,
                    layer_crs,
                    QgsProject.instance()
                )
                point = transform.transform(point)
        except Exception as error:
            log_exception("Could not transform the map-click coordinates", error)

        point_geometry = QgsGeometry.fromPointXY(point)

        for result in results:
            feature = result.mFeature
            geometry = feature.geometry()

            if not geometry or geometry.isEmpty():
                continue

            try:
                if geometry.contains(point_geometry) or geometry.intersects(point_geometry):
                    return feature
            except Exception as error:
                log_exception(
                    "Could not test a feature geometry at the map click",
                    error,
                )

        return results[0].mFeature if results else None

def apply_value_to_feature_ids(layer, field_name, value_text, feature_ids, parent_widget=None):
    """Apply a value to one or more features."""
    if not layer or not field_name or not feature_ids:
        return False

    def tr(text):
        return QCoreApplication.translate("VectorClassManagerDockWidget", text)

    if not layer.isEditable():
        QMessageBox.warning(
            parent_widget,
            tr("Layer is not editable"),
            tr("Turn on editing for the layer before changing classes.")
        )
        return False

    field_idx = layer.fields().indexOf(field_name)

    if field_idx < 0:
        QMessageBox.warning(
            parent_widget,
            tr("Error"),
            tr("Field not found: {field}").format(field=field_name)
        )
        return False

    try:
        layer.beginEditCommand(
            tr("Class change for {count} feature(s) - {field}").format(
                count=len(feature_ids),
                field=field_name
            )
        )
        
        for fid in feature_ids:
            feat = layer.getFeature(fid)
            new_value = cast_value(feat, layer, field_name, value_text)
            layer.changeAttributeValue(fid, field_idx, new_value)
            
        layer.endEditCommand()
        return True

    except Exception as e:
        layer.destroyEditCommand()
        
        QMessageBox.warning(
            parent_widget,
            tr("Error"),
            tr("Error updating features: {error}").format(error=e)
        )
        return False

def cast_value(feat, layer, field_name, value_text):
    """Cast a value according to the field type."""
    if value_text is None:
        return None

    fld = layer.fields().field(field_name)

    if fld is None:
        return value_text

    t = fld.typeName()

    if t in ('Integer', 'Integer64'):
        try:
            return int(value_text)
        except (TypeError, ValueError, OverflowError):
            return value_text

    if t in ('Double', 'Real'):
        try:
            return float(value_text)
        except (TypeError, ValueError, OverflowError):
            return value_text

    return value_text

# -*- coding: utf-8 -*-
"""Small Qt/PyQGIS compatibility helpers for QGIS 3 and QGIS 4."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QFrame, QStyle
from qgis.core import Qgis, QgsFieldConstraints, QgsMessageLog
from qgis.gui import QgsMapToolIdentify

try:
    from qgis.PyQt.QtCore import QVariant
except ImportError:
    QVariant = None

try:
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction


def _qt_enum(group_name, member_name, fallback_name=None):
    group = getattr(Qt, group_name, None)

    if group is not None and hasattr(group, member_name):
        return getattr(group, member_name)

    return getattr(Qt, fallback_name or member_name)


def _qt_int(value):
    try:
        return int(value)
    except Exception:
        return int(value.value)


def _class_enum(enum_class, group_name, member_name, fallback_name=None):
    group = getattr(enum_class, group_name, None)

    if group is not None and hasattr(group, member_name):
        return getattr(group, member_name)

    return getattr(enum_class, fallback_name or member_name)


def _qgis_enum(enum_class, group_name, member_name, fallback_name=None):
    group = getattr(enum_class, group_name, None)

    if group is not None and hasattr(group, member_name):
        return getattr(group, member_name)

    return getattr(enum_class, fallback_name or member_name)


def log_exception(message, error, warning=True):
    """Record recoverable errors without repeated user notifications."""
    severity = _qgis_enum(
        Qgis, "MessageLevel", "Warning" if warning else "Info"
    )
    QgsMessageLog.logMessage(
        f"{message}: {type(error).__name__}: {error}",
        "Vector Class Manager",
        level=severity,
        notifyUser=False,
    )


def qt_exec(widget, *args):
    exec_method = getattr(widget, "exec", None)

    if callable(exec_method):
        return exec_method(*args)

    return getattr(widget, "exec_")(*args)


RIGHT_DOCK_WIDGET_AREA = _qt_enum("DockWidgetArea", "RightDockWidgetArea")
RICH_TEXT = _qt_enum("TextFormat", "RichText")
ALIGN_CENTER = _qt_enum("AlignmentFlag", "AlignCenter")
CUSTOM_CONTEXT_MENU = _qt_enum("ContextMenuPolicy", "CustomContextMenu")
USER_ROLE = _qt_int(_qt_enum("ItemDataRole", "UserRole"))
TRANSPARENT = _qt_enum("GlobalColor", "transparent")
ARROW_CURSOR = _qt_enum("CursorShape", "ArrowCursor")
POINTING_HAND_CURSOR = _qt_enum("CursorShape", "PointingHandCursor")
RIGHT_BUTTON = _qt_enum("MouseButton", "RightButton")
LEFT_BUTTON = _qt_enum("MouseButton", "LeftButton")
SMALL_ICON_SIZE = _class_enum(QStyle, "PixelMetric", "PM_SmallIconSize")
TITLE_BAR_NORMAL_BUTTON = _class_enum(
    QStyle, "StandardPixmap", "SP_TitleBarNormalButton"
)
TITLE_BAR_CLOSE_BUTTON = _class_enum(
    QStyle, "StandardPixmap", "SP_TitleBarCloseButton"
)
FRAME_HLINE = _class_enum(QFrame, "Shape", "HLine")
FRAME_SUNKEN = _class_enum(QFrame, "Shadow", "Sunken")
CONSTRAINT_NOT_NULL = _qgis_enum(
    QgsFieldConstraints, "Constraint", "ConstraintNotNull"
)
CONSTRAINT_UNIQUE = _qgis_enum(
    QgsFieldConstraints, "Constraint", "ConstraintUnique"
)
IDENTIFY_TOP_DOWN_ALL = _qgis_enum(
    QgsMapToolIdentify, "IdentifyMode", "TopDownAll"
)


def is_integer_field(field):
    """Detect integer fields without depending on Qt5-only QVariant names."""
    if not field:
        return False

    if QVariant is not None:
        integer_types = []

        for type_name in ("Int", "LongLong", "UInt", "ULongLong"):
            if hasattr(QVariant, type_name):
                integer_types.append(getattr(QVariant, type_name))

        try:
            if field.type() in tuple(integer_types):
                return True
        except Exception as error:
            log_exception(
                "Could not inspect the field's Qt type; using its type name",
                error,
                warning=False,
            )

    try:
        type_name = str(field.typeName()).strip().lower()
    except Exception:
        return False

    integer_type_names = {
        "integer",
        "integer64",
        "int",
        "int2",
        "int4",
        "int8",
        "uint",
        "uint64",
        "long",
        "longlong",
        "ulonglong",
        "short",
        "smallint",
        "bigint",
        "serial",
        "bigserial",
    }

    return type_name in integer_type_names

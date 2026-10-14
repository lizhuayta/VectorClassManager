# Vector Class Manager

Vector Class Manager brings class assignment, vector digitizing, and category symbol editing together in a compact, dockable panel. Choose a layer and a field from its attribute table to work with the class values stored in that field.

## Key Features

1. List the unique class values stored in the chosen attribute-table field.
2. Preview category symbols and legend labels.
3. Assign a class to one or many selected features with one click.
4. Apply the active class continuously by clicking features on the map.
5. Digitize points, lines, and polygons with a preselected class, and switch classes while continuing to digitize.
6. Create new class values and assign them to selected features.
7. Rename existing class values across all matching features.
8. Edit the symbol associated with each class from the panel.
9. Preserve predefined symbology categories, including those not currently used by any feature.
10. Activate classes using custom keyboard shortcuts.

## Requirements

- QGIS desktop with Vector Class Manager installed.
- A vector layer with an attribute field containing the class values.
- The target layer must be in edit mode to assign or rename class values or create features.
- Symbol previews and editing require categorized symbology based on the same field selected in the panel.

## Getting Started

1. Open the panel using the **Vector Class Manager** toolbar button or its entry in the **Plugins** menu.
2. Choose the vector layer and the field that stores its classes.
3. Enable editing for that layer before changing values or creating features.

The panel follows the active vector layer. Its class list is built from the unique values in the chosen attribute-table field.

When you finish editing, save the layer changes in QGIS.

## Assigning Classes

**To selected features:** select one or more features with the QGIS selection tools, then click a class in the panel. That value is assigned to every selected feature.

**By map clicks:** clear the selection, then click a class in the panel. Left-click existing features on the map to assign the active class repeatedly. Right-click on the map to end this mode.

## Digitizing Features by Class

1. Click **Create features by class**.
2. Choose a class in the panel. An already selected class can also be used.
3. Digitize a point, line, or polygon with the QGIS feature creation tool. Each new feature receives the chosen class automatically.
4. Choose another class to continue digitizing with a different value.
5. Click **Stop creating features by class** to leave creation mode.

If other required fields still need values, the attribute form opens so you can complete them. Changing the layer or field stops creation mode.

## Creating and Renaming Classes

To create a class, select one or more features, right-click inside the class list, and choose **Assign new class to selection**. Enter the new value to assign it to the selection.

To rename a class, right-click its entry and choose **Rename class**. The new value replaces the old value in all matching features, including features outside the current selection.

New and renamed class values are checked against the field's data type and text-length limit.

## Categorized Symbology

When categorized symbology uses the chosen field, the panel displays matching symbols and legend labels. Right-click a class and choose **Edit symbology** to change its symbol.

Creating a new class also adds its corresponding category to the existing categorized symbology when needed. Renaming a class updates its matching category while retaining its symbol.

Predefined categories remain in the layer's symbology even when no features currently use them. The palette is based on stored attribute values, so it does not list every unused template category.

## Keyboard Shortcuts

Right-click a class and choose **Assign shortcut**. Enter a key sequence such as `A`, `Ctrl+1`, or `Shift+F`.

The shortcut activates that class according to the current workflow: assigning it to the selection, activating map-click assignment, or changing the class used for digitizing.

To remove a shortcut, right-click the class and choose **Remove shortcut**.

## Refreshing the Panel

Click **Refresh** to reload the layer, field, and class list. Refresh ends any active assignment or creation mode.

## Contact

For questions or feedback: [huaytahe@outlook.com](mailto:huaytahe@outlook.com).

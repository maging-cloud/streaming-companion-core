from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
)


def _make_field(field_schema: dict):
    ftype = field_schema.get("type", "string")
    enum = field_schema.get("enum")
    if enum:
        w = QComboBox()
        w.addItems([str(e) for e in enum])
        return w
    if ftype == "number":
        w = QDoubleSpinBox()
        w.setMinimum(field_schema.get("minimum", 0.0))
        w.setMaximum(field_schema.get("maximum", 9999.0))
        return w
    if ftype == "integer":
        w = QSpinBox()
        w.setMinimum(int(field_schema.get("minimum", 0)))
        w.setMaximum(int(field_schema.get("maximum", 9999)))
        return w
    return QLineEdit()


def build_form(schema: dict):
    """JSON Schema から (QWidget, get_values, set_values) を返す。"""
    container = QWidget()
    layout = QFormLayout(container)
    fields: dict[str, QWidget] = {}

    for key, field in schema.get("properties", {}).items():
        title = field.get("title", key)
        widget = _make_field(field)
        layout.addRow(title, widget)
        fields[key] = widget

    def get_values() -> dict:
        result = {}
        for k, w in fields.items():
            if isinstance(w, QComboBox):
                result[k] = w.currentText()
            elif isinstance(w, (QDoubleSpinBox, QSpinBox)):
                result[k] = w.value()
            else:
                result[k] = w.text()
        return result

    def set_values(values: dict) -> None:
        for k, w in fields.items():
            v = values.get(k)
            if v is None:
                continue
            if isinstance(w, QComboBox):
                idx = w.findText(str(v))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            elif isinstance(w, (QDoubleSpinBox, QSpinBox)):
                w.setValue(v)
            else:
                w.setText(str(v))

    return container, get_values, set_values

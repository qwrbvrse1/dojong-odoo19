/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Convert a decimal float (0–24) to an HH:MM string required by <input type="time">.
 */
function floatToTimeInput(value) {
    const totalMinutes = Math.round((value || 0) * 60);
    const h = Math.floor(totalMinutes / 60) % 24;
    const m = totalMinutes % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/**
 * Convert an HH:MM string from <input type="time"> back to a decimal float.
 */
function timeInputToFloat(str) {
    if (!str) return 0;
    const [h, m] = str.split(":").map(Number);
    return h + m / 60;
}

export class FloatTime12hField extends Component {
    static template = "dojo_classes.FloatTime12hField";
    static props = { ...standardFieldProps };

    get timeValue() {
        const val = this.props.record.data[this.props.name];
        if (val === undefined || val === false) return "";
        return floatToTimeInput(val);
    }

    onChange(ev) {
        this.props.record.update({
            [this.props.name]: timeInputToFloat(ev.target.value),
        });
    }
}

registry.category("fields").add("float_time_12h", {
    component: FloatTime12hField,
    supportedTypes: ["float"],
    extractProps: ({ attrs }) => ({}),
});

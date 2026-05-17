/** @odoo-module **/
import {X2Many2DMatrixRenderer} from "@web_widget_x2many_2d_matrix/components/x2many_2d_matrix_renderer/x2many_2d_matrix_renderer.esm";

export class PsPlanningMatrixRenderer extends X2Many2DMatrixRenderer {
    onClickStateCheckbox(ev) {
        const row = parseInt(ev.currentTarget.dataset.row, 10);
        const state = ev.currentTarget.checked ? "final" : "draft";
        this.matrix[row].forEach((x) =>
            x.records.forEach((record) => record.update({state}))
        );
    }
    getRowRecordValue(row, field_name) {
        const y = this.rows.findIndex((r) => r.value === row);
        const record =
            this.matrix[y] && this.matrix[y][0] && this.matrix[y][0].records[0];
        if (record) {
            let value = record.data[field_name];
            if (record.fields[field_name].type === "many2one") {
                value = value[1];
            }
            return value;
        }
        return "";
    }
    getValueFieldProps() {
        const result = super.getValueFieldProps(...arguments);
        result.readonly = result.record.data.disabled;
        return result;
    }
    _aggregateColumnContracted(column) {
        return this.matrix
            .map((row) => row[column].records)
            .flat()
            .filter((record) => record.data.line_type === "contracted")
            .reduce((sum, record) => sum + record.data.days, 0);
    }
    _aggregateAllContracted() {
        return this.matrix
            .flat()
            .map((row) => row.records)
            .flat()
            .filter((record) => record.data.line_type === "contracted")
            .reduce((sum, record) => sum + record.data.days, 0);
    }
}

PsPlanningMatrixRenderer.template = "ps_planning.PsPlanningMatrixRenderer";

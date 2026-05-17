/** @odoo-module **/
import {PsPlanningMatrixRenderer} from "@ps_planning/PsPlanningMatrixRenderer.esm";
import {X2Many2DMatrixField} from "@web_widget_x2many_2d_matrix/components/x2many_2d_matrix_field/x2many_2d_matrix_field.esm";
import {registry} from "@web/core/registry";

class PsPlanningMatrixField extends X2Many2DMatrixField {}

PsPlanningMatrixField.components = {X2Many2DMatrixRenderer: PsPlanningMatrixRenderer};
PsPlanningMatrixField.additionalClasses = ["o_field_x2many_2d_matrix"];

registry.category("fields").add("x2many_2d_matrix_ps_planning", PsPlanningMatrixField);

# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Professional services time control",
    "summary": "Adapt time control to professional services",
    "version": "16.0.1.0.0",
    "category": "module_category_specific_industry_applications",
    "author": "The Open Source Company",
    "license": "AGPL-3",
    "depends": [
        "ps_timesheet_invoicing",
        "project_timesheet_time_control",
        "helpdesk_mgmt_timesheet",
    ],
    "data": [
        "views/helpdesk_ticket.xml",
        "views/ps_time_line.xml",
    ],
    "post_init_hook": "post_init_hook",
}

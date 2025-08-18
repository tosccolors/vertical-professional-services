# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Delegation for timesheets",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "summary": "Approve subordinates' subordinates' timesheets",
    "author": "The Open Source Company",
    "website": "http://www.tosc.nl",
    "category": "module_category_specific_industry_applications",
    "depends": [
        "ps_timesheet_invoicing",
    ],
    "installable": True,
    "data": [
        "security/ps_timesheet_delegate.xml",
        "views/menu.xml",
    ],
}

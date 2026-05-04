from odoo import models, fields


class BasePerson(models.AbstractModel):
    _name = 'base.person'
    _description = 'Base Person'

    # index=True lets Postgres use a B-tree on this column for name searches and
    # Many2one lookups. Add it on fields that appear in WHERE/ORDER BY frequently;
    # skip it on fields that are written constantly, as indexes slow down inserts.
    name = fields.Char(string='Name', required=True, index=True)
    age = fields.Integer(string='Age')

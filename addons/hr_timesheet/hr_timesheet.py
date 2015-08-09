# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api, fields, exceptions

from openerp.tools.translate import _


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    product_id = fields.Many2one('product.product', 'Product', help="If you want to reinvoice working time of employees, link this employee to a service to determinate the cost price of the job.")
    uom_id = fields.Many2one('product.uom', related='product_id.uom_id', string='Unit of Measure', store=True, readonly=True)


class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'

    def default_get(self, cr, uid, fields, context=None):
        values = super(account_analytic_line, self).default_get(cr, uid, fields, context=context)
        if values.get('is_timesheet'):
            if 'product_id' in fields:
                values['product_id'] = self._get_employee_product(cr, uid, context=context)
            if 'product_uom_id' in fields:
                values['product_uom_id'] = self._get_employee_unit(cr, uid, context=context)
            if 'general_account_id' in fields:
                values['general_account_id'] = self._get_general_account(cr, uid, context=context)
        return values

    is_timesheet = fields.Boolean()

    @api.model
    def _get_employee_product(self, user_id=None):
        emp = self.env['hr.employee'].search([('user_id', '=', user_id or self.env.uid)], limit=1)
        if emp and emp.product_id.id:
            return emp.product_id.id
        else:
            return None

    @api.model
    def _get_employee_unit(self, user_id=None):
        emp = self.env['hr.employee'].search([('user_id', '=', user_id or self.env.uid)], limit=1)
        if emp and emp.product_id.uom_id.id:
            return emp.product_id.uom_id.id
        else:
            return None

    @api.model
    def _get_general_account(self, user_id=None):
        emp = self.env['hr.employee'].search([('user_id', '=', user_id or self.env.uid)], limit=1)
        if emp and emp.product_id.categ_id.property_account_expense_categ_id.id:
            return emp.product_id.categ_id.property_account_expense_categ_id.id
        else:
            return None

    @api.onchange('user_id')
    def V8_on_change_user_id(self):
        new_values = self.on_change_user_id(self.user_id.id, self.is_timesheet)
        if new_values.get("value"):
            for key, value in new_values["value"].iteritems():
                setattr(self, key, value)

    def on_change_user_id(self, cr, uid, ids, user_id, is_timesheet=False, context=None):
        if not is_timesheet or not user_id:
            return {}
        res = {"value": {
            'product_id': self._get_employee_product(cr, uid, user_id, context=context),
            'uom_id': self._get_employee_unit(cr, uid, user_id, context=context),
            'general_account_id': self._get_general_account(cr, uid, user_id, context=context)
            }
        }
        return res

    def on_change_unit_amount(self, cr, uid, id, prod_id, unit_amount, company_id, unit=False, context=None):
        res = {'value': {}}
        if unit_amount:
            # find company
            company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'account.analytic.line', context=context)
            r = super(account_analytic_line, self).on_change_unit_amount(cr, uid, id, prod_id, unit_amount, company_id, unit, context=context)
            if r:
                res.update(r)
        # update unit of measurement
        if prod_id:
            uom = self.pool.get('product.product').browse(cr, uid, prod_id, context=context)
            if uom.uom_id:
                res['value'].update({'product_uom_id': uom.uom_id.id})
        else:
            res['value'].update({'product_uom_id': False})
        return res

    @api.onchange('date')
    def on_change_date(self):
        if self.is_timesheet and self._origin.date and (self._origin.date != self.date):
            raise exceptions.Warning(_('Changing the date will let this entry appear in the timesheet of the new date.'))


class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'

    use_timesheets = fields.Boolean('Timesheets', help="Check this field if this project manages timesheets", deprecated=True)

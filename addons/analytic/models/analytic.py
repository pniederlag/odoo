# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime

from openerp import api, fields, models, _

from openerp import tools
from openerp.tools.translate import _
from openerp.exceptions import UserError

class account_analytic_tag(models.Model):
    _name = 'account.analytic.tag'
    _description = 'Analytic Tags'
    name = fields.Char(string='Analytic Tag', index=True, required=True)


class account_analytic_account(models.Model):
    _name = 'account.analytic.account'
    _inherit = ['mail.thread']
    _description = 'Analytic Account'
    _order = 'code, name asc'

    @api.multi
    def _debit_credit_compute(self):
        analytic_obj = self.env['account.analytic.line']
        domain = []
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        data = analytic_obj.read_group(
            domain+[('analytic_account_id','in',self.mapped('id'))],
            ['analytic_account_id','debit','credit'], ['analytic_account_id'])
        data = map(lambda x: (x['analytic_account_id'], (x['debit'], x['credit'])), data)

        for account in self:
            self.debit = data.get(account.id, {}).get('debit', 0.0)
            self.credit = data.get(account.id, {}).get('credit', 0.0)
            self.balance = self.debit - self.credit

    @api.model
    def _default_company(self):
        return self.env.user.company_id.id

    @api.model
    def _default_user(self):
        return self.env.user.id

    name = fields.Char(string='Analytic Account', index=True, required=True, track_visibility='onchange')
    code = fields.Char(string='Reference', index=True, track_visibility='onchange')
    account_type = fields.Selection([
            ('normal','Analytic View')
        ], string='Type of Account', required=True, default='normal')

    tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_account_tag_rel', 'account_id', 'tag_id', string='Tags', copy=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=_default_company)
    partner_id = fields.Many2one('res.partner', string='Customer')

    balance = fields.Monetary(compute='_debit_credit_compute', string='Balance')
    debit = fields.Monetary(compute='_debit_credit_compute', string='Debit')
    credit = fields.Monetary(compute='_debit_credit_compute', string='Credit')

    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)

    @api.multi
    def name_get(self):
        res = []
        for analytic in self:
            name = self.name
            if self.code:
                name = '['+self.code+'] '+name
            res.append((self.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.search(['|', ('code', operator, name), ('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'open':
            return 'analytic.mt_account_opened'
        elif 'state' in init_values and self.state == 'close':
            return 'analytic.mt_account_closed'
        elif 'state' in init_values and self.state == 'pending':
            return 'analytic.mt_account_pending'
        return super(account_analytic_account, self)._track_subtype(init_values)


class account_analytic_line(models.Model):
    _name = 'account.analytic.line'
    _description = 'Analytic Line'
    _order = 'date desc'

    @api.model
    def _default_user(self):
        return self.env.user.id

    name = fields.Char('Description', required=True)
    date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today)
    amount = fields.Monetary('Amount', required=True, default=0.0)
    unit_amount = fields.Float('Quantity', default=0.0)
    account_id = fields.Many2one('account.analytic.account', 'Analytic Account', required=True, ondelete='restrict', index=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    user_id = fields.Many2one('res.users', string='User', default=_default_user)

    tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_line_tag_rel', 'line_id', 'tag_id', string='Tags', copy=True)

    company_id = fields.Many2one(related='account_id.company_id', string='Company', store=True, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)


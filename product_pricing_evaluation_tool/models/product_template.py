# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
from datetime import datetime


class ProductTemplateEvaluation(models.Model):
    _inherit = 'product.template'
    calculation = fields.Boolean('Calculation')
    accessories_ids = fields.One2many('accessories.list', 'template_id', string='Accessories')
    commissions_ids = fields.One2many('commissions.list', 'template_id', string='Commissions')

    """====================="""
    less_warranty_discount_por = fields.Float('Less Warranty Discount %', digits=(10, 2))
    less_warranty_discount = fields.Float('Less Warranty Discount', digits=(10, 2), compute='_calcular_less_warranty')

    @api.one
    @api.depends('less_warranty_discount_por', 'standard_price')
    def _calcular_less_warranty(self):
        if (self.less_warranty_discount_por * self.standard_price) != 0:
            self.less_warranty_discount = self.less_warranty_discount_por * self.standard_price / 100
    """====================="""



    exchange_rate_por = fields.Float('Exchange Rate %', digits=(10, 2), default=1.17)
    exchange_rate = fields.Float('Exchange Rate', digits=(10, 2), compute='_calcular_exchange_rate')

    @api.one
    @api.depends('exchange_rate_por', 'standard_price','exchange_rate')
    def _calcular_exchange_rate(self):
        # self.exchange_rate = ((self.standard_price + self.less_warranty_discount)*self.exchange_rate_por)-self.standard_price
        suma = self.standard_price - self.less_warranty_discount
        suma_ma = suma * self.exchange_rate_por
        self.exchange_rate = suma_ma - self.standard_price



    unit_price = fields.Float('Unit Price', digits=(10, 2), compute='_calcular_usd_price')

    @api.one
    @api.depends('standard_price', 'exchange_rate', 'less_warranty_discount')
    def _calcular_usd_price(self):
        self.unit_price = self.standard_price - self.less_warranty_discount + self.exchange_rate

    freight_in_us = fields.Float('Freight In US', digits=(10, 2))


    total_fob = fields.Float('Total Fob', digits=(10, 2), compute='_calcular_fob')
    @api.one
    @api.depends('freight_in_us', 'unit_price')
    def _calcular_fob(self):
        self.total_fob = self.freight_in_us + self.unit_price


    total_cost_delivered = fields.Float('Total Unit Cost as Delivered Sum', digits=(10, 2), compute='_calc_total_cost_delivered')
    @api.one
    @api.depends('accessories_ids')
    def _calc_total_cost_delivered(self):
        tacc = 0
        if self.accessories_ids:
            for acc in self.accessories_ids:
                if acc.price > 0:
                    tacc += acc.price
            self.total_cost_delivered = tacc

    total_cost_delivered_t = fields.Float('Total Unit Cost as Delivered', digits=(10, 2),
                                        compute='_calc_total_cost_delivered_t')

    @api.one
    @api.depends('total_cost_delivered','unit_price')
    def _calc_total_cost_delivered_t(self):
        self.total_cost_delivered_t = self.total_cost_delivered + self.total_fob


    total_commission = fields.Float('commission', digits=(10, 2), compute='_calc_total_commission')
    @api.one
    @api.depends('commissions_ids')
    def _calc_total_commission(self):
        tacc = 0
        if self.commissions_ids:
            for com in self.commissions_ids:
                if com.commission > 0:
                    tacc += com.commission
            self.total_commission = tacc





    freight_to_customer = fields.Float('Freight to Customer', digits=(10, 2))

    warranty = fields.Float('Warranty', digits=(10, 2))
    bk = fields.Float('B&K/Labor', digits=(10, 2))



    floor_por = fields.Float('Financing/Floor Plan %', digits=(10, 2))
    floor_rate = fields.Float('Financing/Floor Plan', digits=(10, 2), compute='_calc_floor_rate')
    @api.one
    @api.depends('floor_por','total_cost_delivered_t')
    def _calc_floor_rate(self):
        self.floor_rate = self.floor_por/100 * self.list_price

    dime_bank_interest_charges = fields.Float('Dime Bank Interest Charges', digits=(10, 2), compute='_calc_day_bank_interest')
    @api.one
    @api.depends('per_day', 'days_financed')
    def _calc_day_bank_interest(self):
        self.dime_bank_interest_charges = self.per_day * self.days_financed

    sub_total = fields.Float('Sub Total', digits=(10, 2), compute='_calc_sub_total')

    @api.one
    @api.depends('total_cost_delivered_t', 'freight_to_customer','warranty','bk','total_commission','floor_rate','dime_bank_interest_charges')
    def _calc_sub_total(self):
        self.sub_total = self.total_cost_delivered_t + self.freight_to_customer  + self.warranty + self.bk + self.total_commission + self.floor_rate

    risk_factor = fields.Float('Risk Factor %', digits=(10, 2))
    risk_factor_value = fields.Float('Risk Factor', digits=(10, 2), compute='_calc_risk_factor_value')

    @api.one
    @api.depends('risk_factor', 'sub_total')
    def _calc_risk_factor_value(self):
        if (self.sub_total) != 0:
            self.risk_factor_value = self.risk_factor/100 * self.sub_total

    cogs = fields.Float('Total COGS', digits=(10, 2), compute='_calc_cogs')
    @api.one
    @api.depends('risk_factor_value', 'sub_total')
    def _calc_cogs(self):
        self.cogs = self.risk_factor_value + self.sub_total

    over_factor = fields.Float('Overhead Factor Applied Factor %', digits=(10, 2))
    over_factor_total = fields.Float('Overhead Factor Applied', digits=(10, 2), compute='_calc_over_factor_total')

    @api.one
    @api.depends('over_factor', 'cogs')
    def _calc_over_factor_total(self):
        self.over_factor_total = self.over_factor * self.total_cost_delivered_t


    total_costs = fields.Float('Total Costs', digits=(10, 2), compute='_calc_total_costs')

    @api.one
    @api.depends('cogs', 'over_factor_total')
    def _calc_total_costs(self):
        self.total_costs = self.cogs + self.over_factor_total

    net_profit = fields.Float('Net Profit (with OH)', digits=(10, 2), compute='_calc_net_profit')
    net_profit_por = fields.Float('Net Profit (with OH) %', digits=(10, 2), compute='_calc_net_profit')
    @api.one
    @api.depends('total_costs', 'list_price')
    def _calc_net_profit(self):
        self.net_profit = self.list_price - self.total_costs
        if (self.list_price) != 0:
            self.net_profit_por = self.net_profit / self.list_price * 100





    gross_profit = fields.Float('Gross Profit without OH)', digits=(10, 2) , compute='_calc_gross_profit')
    gross_profit_por = fields.Float('Gross Profit without OH) %', digits=(10, 2), compute='_calc_gross_profit')

    @api.one
    @api.depends('cogs', 'list_price')
    def _calc_gross_profit(self):
        self.gross_profit = self.list_price - self.cogs
        if (self.list_price) != 0:
            self.gross_profit_por = self.gross_profit / self.list_price * 100


    price_target_marg_por = fields.Float('Price at Target Margin %', digits=(10, 2), default=10)
    price_target_marg = fields.Float('Price at Target Margin', digits=(10, 2), default=10, compute='_calc_price_target_marg')

    @api.one
    @api.depends('total_costs', 'price_target_marg_por')
    def _calc_price_target_marg(self):
        if (self.price_target_marg_por) != 0:
            self.price_target_marg = self.total_costs / (1-self.price_target_marg_por/100)



    days_financed = fields.Float('Days Financed', digits=(10, 2), default=10)
    interest_rate = fields.Float('Interest Rate', digits=(10, 2), default=10)
    per_day = fields.Float('per Day', digits=(10, 2), compute='_calc_per_day')

    @api.one
    @api.depends('unit_price', 'per_day')
    def _calc_per_day(self):
        self.per_day = (self.unit_price * self.interest_rate/100)/360

    day_bank_interest = fields.Float('Dime Bank Interest to Date', digits=(10, 2), default=10, compute='_cal_day_bank_interest')

    @api.one
    @api.depends('days_financed', 'per_day')
    def _cal_day_bank_interest(self):
        self.day_bank_interest = self.days_financed * self.per_day





class CommissionsList(models.Model):
    _name = 'commissions.list'
    _description = 'Commissions List'
    employee_id = fields.Many2one('hr.employee', 'Employee')
    porcent = fields.Float()
    commission = fields.Float()
    note = fields.Char('Note')
    template_id = fields.Many2one('product.template', 'producto', ondelete='cascade')



class AccessoriesList(models.Model):
    _name = 'accessories.list'
    _description = 'Accessories List'
    product_id = fields.Many2one('product.product', 'Product')
    qty = fields.Float('Quantity')
    price = fields.Float()
    subtotal = fields.Float('Subtotal', compute='give_subtotal')
    note = fields.Char('Note')

    @api.one
    @api.depends('price','price')
    def give_subtotal(self):
        self.subtotal = self.qty * self.price

    @api.onchange('qty','price')
    def onchange_subtotal(self):
        self.subtotal = self.qty * self.price

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.price = self.product_id.standard_price

    template_id = fields.Many2one('product.template', 'producto', ondelete='cascade')
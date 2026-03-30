# Copyright 2023 Domatix - Carlos Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command, api, fields, models
from odoo.tools.misc import get_lang


class SaleSubscriptionLine(models.Model):
    _name = "sale.subscription.line"
    _description = "Subscription lines added to a given subscription"
    _inherit = "analytic.mixin"

    product_id = fields.Many2one(
        comodel_name="product.product",
        domain=[("sale_ok", "=", True)],
        string="Product",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="sale_subscription_id.currency_id",
        store=True,
        readonly=True,
    )
    name = fields.Char(
        string="Description", compute="_compute_name", store=True, readonly=False
    )
    product_uom_qty = fields.Float(default=1.0, string="Quantity")
    price_unit = fields.Float(
        string="Unit price", compute="_compute_price_unit", store=True, readonly=False
    )
    discount = fields.Float(
        string="Discount (%)", compute="_compute_discount", store=True, readonly=False
    )
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        relation="subscription_line_tax",
        column1="subscription_line_id",
        column2="tax_id",
        string="Taxes",
        compute="_compute_tax_ids",
        store=True,
        readonly=False,
    )
    price_subtotal = fields.Monetary(
        string="Subtotal", readonly=True, compute="_compute_subtotal", store=True
    )
    price_total = fields.Monetary(
        string="Total", readonly=True, compute="_compute_subtotal", store=True
    )
    amount_tax_line_amount = fields.Float(
        string="Taxes Amount", compute="_compute_subtotal", store=True
    )
    sale_subscription_id = fields.Many2one(
        comodel_name="sale.subscription", string="Subscription"
    )
    company_id = fields.Many2one(
        related="sale_subscription_id.company_id",
        string="Company",
        store=True,
        index=True,
    )

    @api.depends("product_id", "price_unit", "product_uom_qty", "discount", "tax_ids")
    def _compute_subtotal(self):
        for record in self:
            price = record.price_unit * (1 - (record.discount or 0.0) / 100.0)
            taxes = record.tax_ids.compute_all(
                price,
                record.currency_id,
                record.product_uom_qty,
                product=record.product_id,
                partner=record.sale_subscription_id.partner_id,
            )
            record.update(
                {
                    "amount_tax_line_amount": sum(
                        t.get("amount", 0.0) for t in taxes.get("taxes", [])
                    ),
                    "price_total": taxes["total_included"],
                    "price_subtotal": taxes["total_excluded"],
                }
            )

    @api.depends("product_id")
    def _compute_name(self):
        for record in self:
            if not record.product_id:
                record.name = False
            lang = get_lang(self.env, record.sale_subscription_id.partner_id.lang).code
            product = record.product_id.with_context(lang=lang)
            record.name = product.with_context(
                lang=lang
            ).get_product_multiline_description_sale()

    @api.depends("product_id", "sale_subscription_id.fiscal_position_id")
    def _compute_tax_ids(self):
        for line in self:
            fpos = (
                line.sale_subscription_id.fiscal_position_id
                or line.sale_subscription_id.fiscal_position_id._get_fiscal_position(
                    line.sale_subscription_id.partner_id
                )
            )
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(
                lambda t: t.company_id == self.env.company
            )
            line.tax_ids = fpos.map_tax(taxes)

    @api.depends(
        "product_id",
        "sale_subscription_id.partner_id",
        "sale_subscription_id.pricelist_id",
    )
    def _compute_price_unit(self):
        for record in self:
            if not record.product_id:
                continue
            pricelist = record.sale_subscription_id.pricelist_id
            if pricelist and record.sale_subscription_id.partner_id:
                record.price_unit = pricelist._get_product_price(
                    record.product_id,
                    record.product_uom_qty or 1.0,
                    uom=record.product_id.uom_id,
                    date=fields.Date.today(),
                )

    @api.depends(
        "product_id",
        "price_unit",
        "product_uom_qty",
        "tax_ids",
        "sale_subscription_id.partner_id",
        "sale_subscription_id.pricelist_id",
    )
    def _compute_discount(self):
        for record in self:
            if not (
                record.product_id
                and record.product_id.uom_id
                and record.sale_subscription_id.partner_id
                and record.sale_subscription_id.pricelist_id
                and self.env.user.has_group("sale.group_discount_per_so_line")
            ):
                record.discount = 0.0
                continue

            pricelist = record.sale_subscription_id.pricelist_id
            pricelist_price = pricelist._get_product_price(
                record.product_id,
                record.product_uom_qty or 1.0,
                uom=record.product_id.uom_id,
                date=fields.Date.today(),
            )
            base_price = record.product_id.lst_price
            if base_price:
                discount = (base_price - pricelist_price) / base_price * 100
                if (discount > 0 and base_price > 0) or (
                    discount < 0 and base_price < 0
                ):
                    record.discount = discount
                else:
                    record.discount = 0.0
            else:
                record.discount = 0.0

    def _prepare_sale_order_line(self):
        self.ensure_one()
        return {
            "product_id": self.product_id.id,
            "name": self.name,
            "product_uom_qty": self.product_uom_qty,
            "price_unit": self.price_unit,
            "discount": self.discount,
            "price_subtotal": self.price_subtotal,
            "tax_id": self.tax_ids,
            "product_uom": self.product_id.uom_id.id,
            "analytic_distribution": self.analytic_distribution,
        }

    def _prepare_account_move_line(self):
        self.ensure_one()
        account = (
            self.product_id.property_account_income_id
            or self.product_id.categ_id.property_account_income_categ_id
        )
        return {
            "product_id": self.product_id.id,
            "name": self.name,
            "quantity": self.product_uom_qty,
            "price_unit": self.price_unit,
            "discount": self.discount,
            "price_subtotal": self.price_subtotal,
            "tax_ids": [Command.set(self.tax_ids.ids)],
            "product_uom_id": self.product_id.uom_id.id,
            "account_id": account.id,
            "analytic_distribution": self.analytic_distribution,
        }

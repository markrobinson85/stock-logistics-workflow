# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, _
from odoo.exceptions import ValidationError
from odoo.tools import config, float_compare


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    # for reference
    @api.multi
    def record_production(self):
        self.ensure_one()
        p = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        child_locations = self.env['stock.location'].search([('location_id', 'child_of', self.production_id.location_src_id.id)])
        for move_lot in self.active_move_lot_ids:
            # Get the quantity of the requested lot code from the MO source location and child locations.
            quants_at_location = self.env['stock.quant'].search(['&', ('lot_id', '=', move_lot.lot_id.id), ('product_id', '=', move_lot.product_id.id), ('location_id', 'in', child_locations.ids)])
            quantity_at_location = sum(quants_at_location.mapped('qty'))

            # Get the related move_lots that match the lot code and product from the production order and workorder that are not done.
            related_move_lots = (move_lot.move_id.active_move_lot_ids + self.active_move_lot_ids).filtered(lambda x: x.product_id == move_lot.product_id and x.lot_id == move_lot.lot_id and move_lot.move_id.state not in ['done', 'cancel'])

            # Sum and compare move lots of wo and mo.
            if (quantity_at_location < sum(related_move_lots.mapped('quantity_done')) and
                    move_lot.product_id.type == 'product' and
                    not move_lot.product_id.allow_negative_stock and
                    not move_lot.product_id.categ_id.allow_negative_stock):

                previously_committed = sum(move_lot.move_id.active_move_lot_ids.filtered(lambda x: x.product_id == move_lot.product_id and x.lot_id == move_lot.lot_id and move_lot.move_id.state not in ['done', 'cancel']).mapped('quantity_done'))
                currently_committed = sum(self.active_move_lot_ids.filtered(lambda x: x.product_id == move_lot.product_id and x.lot_id == move_lot.lot_id and move_lot.move_id.state not in ['done', 'cancel']).mapped('quantity_done'))
                total_requested = sum(related_move_lots.mapped('quantity_done'))
                available = quantity_at_location - previously_committed

                raise ValidationError(_(
                    "You cannot validate this workorder operation because the "
                    "stock level of the product %s %s would become negative "
                    "on the stock location '%s' and negative stock is "
                    "not allowed for this product. \n\n"
                    # "Previously Requested: %s \n"
                    # "Currently Requested: %s \n"
                    "Total Requested: %s \n"
                    "Available: %s") % (
                        move_lot.product_id.name,
                        move_lot.lot_id.name,
                        # move_lot.qty,
                        self.production_id.location_src_id.complete_name,
                        # previously_committed,
                        currently_committed,
                        # total_requested,
                        available,
                ))

        return super(MrpWorkorder, self).record_production()


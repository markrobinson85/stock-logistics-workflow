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
        for move_lot in self.active_move_lot_ids.filtered(lambda x: x.lot_id and x.product_id.tracking != 'none'):

            # Get the quantity of the requested lot code from the MO source location and child locations.
            quants_at_location = self.env['stock.quant'].search(['&', ('lot_id', '=', move_lot.lot_id.id), ('product_id', '=', move_lot.product_id.id), ('location_id', 'in', child_locations.ids)])
            quantity_at_location = sum(quants_at_location.mapped('qty'))

            # Get the related move_lots that match the lot code and product from the production order and workorder that are not done.
            related_move_lots = (move_lot.move_id.active_move_lot_ids + self.active_move_lot_ids).filtered(lambda x: x.product_id == move_lot.product_id and x.lot_id == move_lot.lot_id and move_lot.move_id.state not in ['done', 'cancel'])
            other_move_lots = self.env['stock.move.lots'].search(
                [('move_id.location_id', '=', self.production_id.location_src_id.id),
                 ('move_id.state', 'not in', ['done', 'cancel']),
                 ('product_id', '=', move_lot.move_id.product_id.id),
                 ('active_lot', '=', True),
                 ('workorder_id', '!=', self.id),
                 ('done_wo', '=', True),
                 ('lot_id', 'in', move_lot.mapped('move_id.active_move_lot_ids.lot_id').ids)])

            other_move_lots = other_move_lots.filtered(lambda x: x.lot_id)

            sum_other_mo = sum(other_move_lots.mapped('quantity_done'))
            sum_related = sum(related_move_lots.mapped('quantity_done'))

            outstanding_commitments = sum_other_mo + sum_related

            # Sum and compare move lots of wo and mo.
            if (float_compare(quantity_at_location, outstanding_commitments, precision_digits=p) == -1 and
                    move_lot.product_id.type == 'product' and
                    not move_lot.product_id.allow_negative_stock and
                    not move_lot.product_id.categ_id.allow_negative_stock):

                previously_committed = sum(move_lot.move_id.active_move_lot_ids.filtered(lambda x: x.product_id == move_lot.product_id and x.lot_id == move_lot.lot_id and move_lot.move_id.state not in ['done', 'cancel']).mapped('quantity_done'))
                currently_committed = sum(self.active_move_lot_ids.filtered(lambda x: x.product_id == move_lot.product_id and x.lot_id == move_lot.lot_id and move_lot.move_id.state not in ['done', 'cancel']).mapped('quantity_done'))
                other_mo_committed = sum_other_mo

                total_requested = sum(related_move_lots.mapped('quantity_done'))
                available = round(quantity_at_location - previously_committed - other_mo_committed, 3)
                error_msg = ("You cannot validate this workorder operation because the "
                    "stock level of the product %s %s would become negative "
                    "on the stock location '%s' and negative stock is "
                    "not allowed for this product. \n\n"
                    "Registered on MO: %s \n") % (
                        move_lot.product_id.name,
                        move_lot.lot_id.name,
                        # move_lot.qty,
                        self.production_id.location_src_id.complete_name,
                        previously_committed)

                if other_mo_committed > 0:
                    error_msg += "\n"
                    for mo in other_move_lots.mapped('production_id'):
                        error_msg += ("%s: %s\n") % (mo.name, sum(other_move_lots.filtered(lambda x: x.production_id == mo).mapped('quantity_done')))
                    error_msg += ("Total Other MOs: %s\n\n") % (other_mo_committed)

                error_msg += ("Requested: %s \n"
                              "Available: %s") % (
                        currently_committed,
                        available,)

                raise ValidationError(error_msg)

        return super(MrpWorkorder, self).record_production()


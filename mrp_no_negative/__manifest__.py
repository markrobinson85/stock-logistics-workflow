# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'MRP Disallow Negative',
    'version': '10.0.1.0.1',
    'category': 'Inventory, Logistic, Storage',
    'license': 'AGPL-3',
    'summary': 'Extends the stock_no_negative module to also block confirming workorders with negative inventory.',
    'author': 'Mark Robinson, J3 Solution',
    'website': 'http://www.j3solution.com',
    'depends': ['stock_no_negative', 'mrp'],
    # 'data': ['views/product.xml'],
    'installable': True,
}
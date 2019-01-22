# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, osv, models, api
import logging
_logger = logging.getLogger(__name__)
import urllib2

from meli_oerp_config import *
from warning import warning

import requests
from ..melisdk.meli import Meli
import json

class product_public_category(models.Model):

    _inherit="product.public.category"

    mercadolibre_category = fields.Many2one( "mercadolibre.category", string="Mercado Libre Category")

product_public_category()


class mercadolibre_category_attribute(models.Model):
    _name = "mercadolibre.category.attribute"
    _description = "MercadoLibre Attribute"

    att_id = fields.Char(string="Attribute Id (ML)")
    name = fields.Char(string="Attribute Name (ML)")

    value_type = fields.Char(string="Value Type")

    hidden = fields.Boolean(string="Hidden")
    variation_attribute = fields.Boolean(string="Variation Attribute")
    multivalued = fields.Boolean(string="Multivalued")

    tooltip = fields.Text(string="Tooltip")
    values = fields.Text(string="Values")
    type = fields.Char(string="Type")

mercadolibre_category_attribute()

class product_attribute(models.Model):

    _inherit="product.attribute"

    mercadolibre_attribute_id = fields.Many2one( "mercadolibre.category.attribute", string="MercadoLibre Attribute")

product_attribute()

class mercadolibre_category(models.Model):
    _name = "mercadolibre.category"
    _description = "Categories of MercadoLibre"

    @api.one
    def get_attributes( self ):

        company = self.env.user.company_id

        warningobj = self.env['warning']
        category_obj = self.env['mercadolibre.category']
        att_obj = self.env['mercadolibre.category.attribute']

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        if (self.meli_category_id):
            self.meli_category_attributes = "https://api.mercadolibre.com/categories/"+str(self.meli_category_id)+"/attributes"
            resp = meli.get("/categories/"+str(self.meli_category_id)+"/attributes", {'access_token':meli.access_token})
            rjs = resp.json()
            for att in rjs:
                _logger.info(att)
                attrs = att_obj.search( [ ('att_id','=',att['id']) ] )
                attrs_field = {
                    'name': att['name'],
                    'value_type': att['value_type'],
                    'hidden': ('hidden' in att['tags']),
                    'multivalued': ( 'multivalued' in att['tags']),
                    'variation_attribute': ('variation_attribute' in att['tags'])
                }

                if ('tooltip' in att):
                    attrs_field['tooltip'] = att['tooltip']

                if ('values' in att):
                    attrs_field['values'] = json.dumps(att['values'])

                if ('type' in att):
                    attrs_field['type'] = att['type']

                if (len(attrs)):
                    attrs[0].write(attrs_field)
                else:
                    attrs_field['att_id'] = att['id']
                    attrs = att_obj.create(attrs_field)


        return {}


    def import_category(self, category_id ):
        company = self.env.user.company_id

        warningobj = self.env['warning']
        category_obj = self.env['mercadolibre.category']

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        if (category_id):
            is_branch = False
            father = None
            ml_cat_id = category_obj.search([('meli_category_id','=',category_id)])
            if (ml_cat_id.id):
              _logger.info("category exists!" + str(ml_cat_id))
              ml_cat_id.get_attributes()
            else:
              _logger.info("Creating category: " + str(category_id))
              #https://api.mercadolibre.com/categories/MLA1743
              response_cat = meli.get("/categories/"+str(category_id), {'access_token':meli.access_token})
              rjson_cat = response_cat.json()
              _logger.info("category:" + str(rjson_cat))
              fullname = ""

              if ("children_categories" in rjson_cat):
                  is_branch = True

              if ("path_from_root" in rjson_cat):
                  path_from_root = rjson_cat["path_from_root"]
                  for path in path_from_root:
                    fullname = fullname + "/" + path["name"]
                  if (len(rjson_cat["path_from_root"])>1):
                      father_ml_id = rjson_cat["path_from_root"][len(rjson_cat["path_from_root"])-2]["id"]
                      father = category_obj.search([('meli_category_id','=',father_ml_id)]).id


              #fullname = fullname + "/" + rjson_cat['name']
              #_logger.info( "category fullname:" + str(fullname) )
              _logger.info(fullname)
              cat_fields = {
                'name': fullname,
                'meli_category_id': ''+str(category_id),
                'is_branch': is_branch,
                'meli_father_category': father
              }
              ml_cat_id = category_obj.create((cat_fields))
              if (ml_cat_id.id):
                  ml_cat_id.get_attributes()


    def import_all_categories(self, category_root ):
        company = self.env.user.company_id

        warningobj = self.env['warning']
        category_obj = self.env['mercadolibre.category']

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        RECURSIVE_IMPORT = company.mercadolibre_recursive_import

        if (category_root):
            response = meli.get("/categories/"+str(category_root), {'access_token':meli.access_token} )

            _logger.info( "response.content:", response.content )

            rjson = response.json()
            if ("name" in rjson):
                # en el html deberia ir el link  para chequear on line esa categoría corresponde a sus productos.
                warningobj.info( title='MELI WARNING', message="Preparando importación de todas las categorías en "+str(category_root), message_html=response )
                if ("children_categories" in rjson):
                    #empezamos a iterar categorias
                    for child in rjson["children_categories"]:
                        ml_cat_id = child["id"]
                        if (ml_cat_id):
                            category_obj.import_category(category_id=ml_cat_id)
                            if (RECURSIVE_IMPORT):
                                category_obj.import_all_categories(category_root=ml_cat_id)


    name = fields.Char('Name',index=True)
    is_branch = fields.Boolean('Rama (no hoja)',index=True)
    meli_category_id = fields.Char('Category Id',index=True)
    meli_father_category = fields.Many2one('mercadolibre.category',string="Padre",index=True)
    public_category_id = fields.Integer('Public Category Id',index=True)

    #public_category = fields.Many2one( "product.category.public", string="Product Website category default", help="Select Public Website category for this ML category ")
    meli_category_attributes = fields.Char(compute=get_attributes,  string="Mercado Libre Category Attributes")
    meli_category_attribute_ids = fields.Many2many("mercadolibre.category.attribute",string="Attributes")


mercadolibre_category()

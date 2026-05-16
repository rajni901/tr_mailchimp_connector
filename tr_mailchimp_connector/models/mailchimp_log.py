from odoo import fields, models


class MailChimpLog(models.Model):
    _name = 'mailchimp.log'
    _description = 'MailChimp Sync Log'
    _order = 'create_date desc'

    account_id = fields.Many2one('mailchimp.account', string='Account', ondelete='cascade')
    operation = fields.Selection([
        ('import_audiences', 'Import Audiences'),
        ('export_audiences', 'Export Audiences'),
        ('import_contacts', 'Import Contacts'),
        ('export_contacts', 'Export Contacts'),
        ('import_campaigns', 'Import Campaigns'),
        ('import_stats', 'Import Stats'),
        ('webhook', 'Webhook'),
    ], string='Operation')
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('warning', 'Warning'),
    ], string='Status')
    message = fields.Text(string='Message')
    mc_id = fields.Char(string='MailChimp ID')
    create_date = fields.Datetime(string='Date', readonly=True)

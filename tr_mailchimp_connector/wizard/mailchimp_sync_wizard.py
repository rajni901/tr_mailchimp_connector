from odoo import _, fields, models


class MailChimpSyncWizard(models.TransientModel):
    _name = 'mailchimp.sync.wizard'
    _description = 'MailChimp Sync Wizard'

    account_id = fields.Many2one('mailchimp.account', string='Account', required=True)
    operation = fields.Selection([
        ('import_audiences', 'Import Audiences from MailChimp'),
        ('export_audiences', 'Export Audiences to MailChimp'),
        ('import_contacts', 'Import Contacts from MailChimp'),
        ('export_contacts', 'Export Contacts to MailChimp'),
        ('import_campaigns', 'Import Campaigns from MailChimp'),
        ('import_stats', 'Import Campaign Statistics'),
    ], string='Operation', required=True)
    result_message = fields.Text(string='Result', readonly=True)

    def action_sync(self):
        self.ensure_one()
        account = self.account_id
        try:
            if self.operation == 'import_audiences':
                count = account._do_import_audiences()
                msg = _(f'Imported {count} audiences.')
            elif self.operation == 'export_audiences':
                count = account._do_export_audiences()
                msg = _(f'Exported {count} audiences.')
            elif self.operation == 'import_contacts':
                count = account._do_import_contacts()
                msg = _(f'Imported {count} contacts.')
            elif self.operation == 'export_contacts':
                count = account._do_export_contacts()
                msg = _(f'Exported {count} contacts.')
            elif self.operation == 'import_campaigns':
                count = account._do_import_campaigns()
                msg = _(f'Imported {count} campaigns.')
            elif self.operation == 'import_stats':
                count = account._do_import_campaign_stats()
                msg = _(f'Updated stats for {count} campaigns.')
            else:
                msg = _('Unknown operation.')
            self.result_message = msg
        except Exception as e:
            self.result_message = f'Error: {str(e)}'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mailchimp.sync.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

from odoo import _, fields, models


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    mailchimp_id = fields.Char(string='MailChimp Campaign ID', copy=False, index=True)
    mailchimp_account_id = fields.Many2one('mailchimp.account', string='MailChimp Account', copy=False)
    mailchimp_status = fields.Char(string='MailChimp Status', readonly=True)
    mailchimp_sends = fields.Integer(string='MC Sends', readonly=True)
    mailchimp_opens = fields.Integer(string='MC Opens', readonly=True)
    mailchimp_clicks = fields.Integer(string='MC Clicks', readonly=True)
    mailchimp_bounces = fields.Integer(string='MC Bounces', readonly=True)
    mailchimp_unsubscribes = fields.Integer(string='MC Unsubscribes', readonly=True)
    mailchimp_open_rate = fields.Float(string='MC Open Rate %', readonly=True)
    mailchimp_click_rate = fields.Float(string='MC Click Rate %', readonly=True)


class MailChimpAccountCampaign(models.Model):
    _inherit = 'mailchimp.account'

    def _do_import_campaigns(self):
        """Import MailChimp campaigns as Odoo mailings."""
        data = self._api_get('campaigns', {'count': 1000})
        campaigns = data.get('campaigns', [])
        imported = 0
        for campaign in campaigns:
            mc_id = campaign['id']
            existing = self.env['mailing.mailing'].search(
                [('mailchimp_id', '=', mc_id)], limit=1)
            settings = campaign.get('settings', {})
            vals = {
                'subject': settings.get('subject_line', campaign.get('id', '')),
                'mailchimp_id': mc_id,
                'mailchimp_account_id': self.id,
                'mailchimp_status': campaign.get('status', ''),
                'email_from': settings.get('reply_to', self.env.company.email or ''),
            }
            if existing:
                existing.write(vals)
            else:
                self.env['mailing.mailing'].create(vals)
                imported += 1
        self.last_campaign_sync = fields.Datetime.now()
        self._log('import_campaigns', 'success', f'Imported {imported} campaigns.')
        return imported

    def _do_import_campaign_stats(self):
        """Import campaign statistics from MailChimp."""
        campaigns = self.env['mailing.mailing'].search([
            ('mailchimp_account_id', '=', self.id),
            ('mailchimp_id', '!=', False),
        ])
        updated = 0
        for campaign in campaigns:
            try:
                data = self._api_get(f'reports/{campaign.mailchimp_id}')
                stats = data.get('stats', {})
                opens = data.get('opens', {})
                clicks = data.get('clicks', {})

                campaign.write({
                    'mailchimp_sends': data.get('emails_sent', 0),
                    'mailchimp_opens': opens.get('opens_total', 0),
                    'mailchimp_clicks': clicks.get('clicks_total', 0),
                    'mailchimp_bounces': stats.get('bounce_drops', 0),
                    'mailchimp_unsubscribes': stats.get('unsub_count', 0),
                    'mailchimp_open_rate': round(opens.get('open_rate', 0) * 100, 2),
                    'mailchimp_click_rate': round(clicks.get('click_rate', 0) * 100, 2),
                })
                updated += 1
            except Exception as e:
                self._log('import_stats', 'error',
                          f'Campaign {campaign.mailchimp_id}: {str(e)}')
        self._log('import_stats', 'success', f'Updated stats for {updated} campaigns.')
        return updated

    def _do_export_campaign(self, campaign):
        """Export a single Odoo mailing to MailChimp."""
        audience = self.env['mailing.list'].search([
            ('mailchimp_account_id', '=', self.id),
            ('mailchimp_id', '!=', False),
        ], limit=1)
        if not audience:
            raise Exception('No MailChimp audience found. Import audiences first.')

        data = {
            'type': 'regular',
            'settings': {
                'subject_line': campaign.subject or 'No Subject',
                'from_name': self.account_name or self.name,
                'reply_to': campaign.email_from or self.env.company.email or '',
            },
            'recipients': {
                'list_id': audience.mailchimp_id,
            },
        }
        if campaign.mailchimp_id:
            result = self._api_put(f'campaigns/{campaign.mailchimp_id}', data)
        else:
            result = self._api_post('campaigns', data)
            campaign.write({
                'mailchimp_id': result['id'],
                'mailchimp_account_id': self.id,
            })
        return result

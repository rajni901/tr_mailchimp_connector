import requests
from requests.auth import HTTPBasicAuth

from odoo import _, api, fields, models
from odoo.exceptions import UserError

MAILCHIMP_API_BASE = 'https://{dc}.api.mailchimp.com/3.0'


class MailChimpAccount(models.Model):
    _name = 'mailchimp.account'
    _description = 'MailChimp Account'
    _rec_name = 'name'

    name = fields.Char(string='Account Name', required=True)
    active = fields.Boolean(default=True)
    api_key = fields.Char(
        string='API Key', required=True,
        help='Get from MailChimp → Account → Extras → API Keys',
    )
    data_center = fields.Char(
        string='Data Center', readonly=True,
        help='Auto-detected from API Key (e.g. us1, us21)',
    )
    account_id = fields.Char(string='MailChimp Account ID', readonly=True)
    account_name = fields.Char(string='MailChimp Account Name', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # Auto sync
    auto_sync_contacts = fields.Boolean('Auto Sync Contacts', default=False)
    auto_sync_audiences = fields.Boolean('Auto Sync Audiences', default=False)
    auto_import_stats = fields.Boolean('Auto Import Campaign Stats', default=False)

    # Last sync
    last_audience_sync = fields.Datetime(readonly=True)
    last_contact_sync = fields.Datetime(readonly=True)
    last_campaign_sync = fields.Datetime(readonly=True)

    # Stats
    audience_count = fields.Integer(compute='_compute_counts')
    campaign_count = fields.Integer(compute='_compute_counts')
    log_count = fields.Integer(compute='_compute_counts')

    def _compute_counts(self):
        for rec in self:
            rec.audience_count = self.env['mailing.list'].search_count(
                [('mailchimp_account_id', '=', rec.id)])
            rec.campaign_count = self.env['mailing.mailing'].search_count(
                [('mailchimp_account_id', '=', rec.id)])
            rec.log_count = self.env['mailchimp.log'].search_count(
                [('account_id', '=', rec.id)])

    def _get_dc(self):
        if self.data_center:
            return self.data_center
        # Extract DC from API key (format: key-dc)
        if '-' in (self.api_key or ''):
            return self.api_key.split('-')[-1]
        raise UserError(_('Cannot determine MailChimp data center from API key.'))

    def _get_url(self, endpoint):
        dc = self._get_dc()
        return f'{MAILCHIMP_API_BASE.format(dc=dc)}/{endpoint}'

    def _get_auth(self):
        return HTTPBasicAuth('anystring', self.api_key)

    def _api_get(self, endpoint, params=None):
        url = self._get_url(endpoint)
        try:
            resp = requests.get(url, auth=self._get_auth(),
                                params=params or {}, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            raise UserError(_(f'MailChimp API Error: {str(e)}\n{resp.text}'))
        except Exception as e:
            raise UserError(_(f'Connection Error: {str(e)}'))

    def _api_post(self, endpoint, data):
        url = self._get_url(endpoint)
        try:
            resp = requests.post(url, auth=self._get_auth(),
                                 json=data, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise UserError(_(f'MailChimp API Error: {str(e)}'))

    def _api_put(self, endpoint, data):
        url = self._get_url(endpoint)
        try:
            resp = requests.put(url, auth=self._get_auth(),
                                json=data, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise UserError(_(f'MailChimp API Error: {str(e)}'))

    def _log(self, operation, status, message, mc_id=None):
        self.env['mailchimp.log'].create({
            'account_id': self.id,
            'operation': operation,
            'status': status,
            'message': message,
            'mc_id': str(mc_id) if mc_id else False,
        })

    def action_test_connection(self):
        self.ensure_one()
        result = self._api_get('')
        dc = self.api_key.split('-')[-1] if '-' in self.api_key else ''
        self.write({
            'data_center': dc,
            'account_id': result.get('account_id', ''),
            'account_name': result.get('account_name', ''),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Connected!'),
                'message': _(f'MailChimp Account: {result.get("account_name")} ({dc})'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_import_audiences(self):
        self.ensure_one()
        count = self._do_import_audiences()
        return self._notify(_(f'Imported {count} audiences.'))

    def action_export_audiences(self):
        self.ensure_one()
        count = self._do_export_audiences()
        return self._notify(_(f'Exported {count} audiences.'))

    def action_import_contacts(self):
        self.ensure_one()
        count = self._do_import_contacts()
        return self._notify(_(f'Imported {count} contacts.'))

    def action_export_contacts(self):
        self.ensure_one()
        count = self._do_export_contacts()
        return self._notify(_(f'Exported {count} contacts.'))

    def action_import_campaigns(self):
        self.ensure_one()
        count = self._do_import_campaigns()
        return self._notify(_(f'Imported {count} campaigns.'))

    def action_import_stats(self):
        self.ensure_one()
        count = self._do_import_campaign_stats()
        return self._notify(_(f'Imported stats for {count} campaigns.'))

    def _notify(self, message, success=True):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Done'),
                'message': message,
                'type': 'success' if success else 'warning',
                'sticky': False,
            },
        }

    def action_view_audiences(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('MailChimp Audiences'),
            'res_model': 'mailing.list',
            'view_mode': 'list,form',
            'domain': [('mailchimp_account_id', '=', self.id)],
        }

    def action_view_campaigns(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('MailChimp Campaigns'),
            'res_model': 'mailing.mailing',
            'view_mode': 'list,form',
            'domain': [('mailchimp_account_id', '=', self.id)],
        }

    def action_view_logs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sync Logs'),
            'res_model': 'mailchimp.log',
            'view_mode': 'list',
            'domain': [('account_id', '=', self.id)],
        }

    def action_register_webhooks(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        audiences = self.env['mailing.list'].search([
            ('mailchimp_account_id', '=', self.id),
            ('mailchimp_id', '!=', False),
        ])
        registered = 0
        for audience in audiences:
            try:
                self._api_post(f'lists/{audience.mailchimp_id}/webhooks', {
                    'url': f'{base_url}/mailchimp/webhook/{self.id}',
                    'events': {'subscribe': True, 'unsubscribe': True,
                               'profile': True, 'cleaned': True, 'campaign': True},
                    'sources': {'user': True, 'admin': True, 'api': True},
                })
                registered += 1
            except Exception as e:
                self._log('webhook', 'warning', str(e))
        return self._notify(_(f'Registered webhooks for {registered} audiences.'))

    @api.model
    def _cron_sync_audiences(self):
        for acc in self.search([('active', '=', True), ('auto_sync_audiences', '=', True)]):
            try:
                acc._do_import_audiences()
            except Exception as e:
                acc._log('import_audiences', 'error', str(e))

    @api.model
    def _cron_sync_contacts(self):
        for acc in self.search([('active', '=', True), ('auto_sync_contacts', '=', True)]):
            try:
                acc._do_import_contacts()
                acc._do_export_contacts()
            except Exception as e:
                acc._log('sync_contacts', 'error', str(e))

    @api.model
    def _cron_import_stats(self):
        for acc in self.search([('active', '=', True), ('auto_import_stats', '=', True)]):
            try:
                acc._do_import_campaign_stats()
            except Exception as e:
                acc._log('import_stats', 'error', str(e))

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MailChimpWebhook(http.Controller):

    @http.route('/mailchimp/webhook/<int:account_id>', type='http',
                auth='none', methods=['GET', 'POST'], csrf=False)
    def mailchimp_webhook(self, account_id, **kwargs):
        # MailChimp sends a GET to verify the webhook URL
        if request.httprequest.method == 'GET':
            return request.make_response('OK', status=200)

        try:
            event_type = kwargs.get('type', '')
            email = kwargs.get('data[email]', '')
            list_id = kwargs.get('data[list_id]', '')

            _logger.info('MailChimp Webhook: %s for %s', event_type, email)

            env = request.env(user=request.env.ref('base.user_admin').id)
            account = env['mailchimp.account'].sudo().browse(account_id)

            if not account.exists():
                return request.make_response('Not Found', status=404)

            if event_type == 'unsubscribe':
                contact = env['mailing.contact'].sudo().search(
                    [('email', '=', email)], limit=1)
                if contact:
                    contact.sudo().write({
                        'opt_out': True,
                        'mailchimp_status': 'unsubscribed',
                    })
                    account.sudo()._log('webhook', 'success',
                                        f'Unsubscribed: {email}')

            elif event_type == 'subscribe':
                contact = env['mailing.contact'].sudo().search(
                    [('email', '=', email)], limit=1)
                if contact:
                    contact.sudo().write({
                        'opt_out': False,
                        'mailchimp_status': 'subscribed',
                    })
                    account.sudo()._log('webhook', 'success',
                                        f'Subscribed: {email}')

            elif event_type == 'cleaned':
                contact = env['mailing.contact'].sudo().search(
                    [('email', '=', email)], limit=1)
                if contact:
                    contact.sudo().write({'mailchimp_status': 'cleaned'})
                    account.sudo()._log('webhook', 'success',
                                        f'Cleaned: {email}')

            return request.make_response('OK', status=200)

        except Exception as e:
            _logger.error('MailChimp Webhook error: %s', str(e))
            return request.make_response(str(e), status=500)

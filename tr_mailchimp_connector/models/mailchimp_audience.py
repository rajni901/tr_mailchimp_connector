import hashlib

from odoo import _, fields, models


class MailingList(models.Model):
    _inherit = 'mailing.list'

    mailchimp_id = fields.Char(string='MailChimp Audience ID', copy=False, index=True)
    mailchimp_account_id = fields.Many2one('mailchimp.account', string='MailChimp Account', copy=False)
    mailchimp_last_sync = fields.Datetime(string='Last Sync', readonly=True)


class MailingContact(models.Model):
    _inherit = 'mailing.contact'

    mailchimp_id = fields.Char(string='MailChimp Member ID', copy=False, index=True)
    mailchimp_status = fields.Selection([
        ('subscribed', 'Subscribed'),
        ('unsubscribed', 'Unsubscribed'),
        ('cleaned', 'Cleaned'),
        ('pending', 'Pending'),
    ], string='MailChimp Status', copy=False)


class MailChimpAccountAudience(models.Model):
    _inherit = 'mailchimp.account'

    def _do_import_audiences(self):
        """Import MailChimp lists/audiences as Odoo mailing lists."""
        data = self._api_get('lists', {'count': 1000})
        lists = data.get('lists', [])
        imported = 0
        for mc_list in lists:
            mc_id = mc_list['id']
            existing = self.env['mailing.list'].search(
                [('mailchimp_id', '=', mc_id)], limit=1)
            vals = {
                'name': mc_list['name'],
                'mailchimp_id': mc_id,
                'mailchimp_account_id': self.id,
                'mailchimp_last_sync': fields.Datetime.now(),
            }
            if existing:
                existing.write(vals)
            else:
                self.env['mailing.list'].create(vals)
                imported += 1
        self.last_audience_sync = fields.Datetime.now()
        self._log('import_audiences', 'success', f'Imported {imported} audiences.')
        return imported

    def _do_export_audiences(self):
        """Export Odoo mailing lists to MailChimp as audiences."""
        lists = self.env['mailing.list'].search([
            ('mailchimp_account_id', '=', self.id),
        ])
        exported = 0
        for ml in lists:
            try:
                data = {
                    'name': ml.name,
                    'contact': {
                        'company': self.account_name or self.name,
                        'address1': '',
                        'city': '',
                        'state': '',
                        'zip': '',
                        'country': 'US',
                    },
                    'permission_reminder': 'You subscribed to our mailing list.',
                    'campaign_defaults': {
                        'from_name': self.account_name or self.name,
                        'from_email': self.env.company.email or 'info@example.com',
                        'subject': '',
                        'language': 'en',
                    },
                    'email_type_option': False,
                }
                if ml.mailchimp_id:
                    self._api_put(f'lists/{ml.mailchimp_id}', data)
                else:
                    result = self._api_post('lists', data)
                    ml.write({
                        'mailchimp_id': result['id'],
                        'mailchimp_last_sync': fields.Datetime.now(),
                    })
                exported += 1
            except Exception as e:
                self._log('export_audiences', 'error', f'"{ml.name}": {str(e)}')
        self._log('export_audiences', 'success', f'Exported {exported} audiences.')
        return exported

    def _do_import_contacts(self):
        """Import MailChimp members as Odoo mailing contacts."""
        audiences = self.env['mailing.list'].search([
            ('mailchimp_account_id', '=', self.id),
            ('mailchimp_id', '!=', False),
        ])
        total = 0
        for audience in audiences:
            offset = 0
            while True:
                data = self._api_get(
                    f'lists/{audience.mailchimp_id}/members',
                    {'count': 1000, 'offset': offset, 'status': 'subscribed'}
                )
                members = data.get('members', [])
                if not members:
                    break
                for member in members:
                    try:
                        self._sync_member_to_contact(member, audience)
                        total += 1
                    except Exception as e:
                        self._log('import_contacts', 'error',
                                  f'{member.get("email_address")}: {str(e)}')
                if len(members) < 1000:
                    break
                offset += 1000
        self.last_contact_sync = fields.Datetime.now()
        self._log('import_contacts', 'success', f'Imported {total} contacts.')
        return total

    def _sync_member_to_contact(self, member, audience):
        email = member.get('email_address', '')
        if not email:
            return
        mc_member_id = member.get('id', '')
        merge_fields = member.get('merge_fields', {})
        fname = merge_fields.get('FNAME', '')
        lname = merge_fields.get('LNAME', '')
        name = f'{fname} {lname}'.strip() or email

        contact = self.env['mailing.contact'].search(
            [('email', '=', email)], limit=1)
        vals = {
            'email': email,
            'name': name,
            'mailchimp_id': mc_member_id,
            'mailchimp_status': member.get('status', 'subscribed'),
        }
        if contact:
            contact.write(vals)
        else:
            contact = self.env['mailing.contact'].create(vals)

        # Link to mailing list
        if audience not in contact.list_ids:
            contact.write({'list_ids': [(4, audience.id)]})

    def _do_export_contacts(self):
        """Export Odoo mailing contacts to MailChimp."""
        audiences = self.env['mailing.list'].search([
            ('mailchimp_account_id', '=', self.id),
            ('mailchimp_id', '!=', False),
        ])
        total = 0
        for audience in audiences:
            contacts = self.env['mailing.contact'].search([
                ('list_ids', 'in', [audience.id]),
                ('opt_out', '=', False),
            ])
            for contact in contacts:
                try:
                    email = contact.email or ''
                    if not email:
                        continue
                    # MailChimp member ID = MD5 of lowercase email
                    member_hash = hashlib.md5(email.lower().encode()).hexdigest()
                    name_parts = (contact.name or '').split(' ', 1)
                    data = {
                        'email_address': email,
                        'status_if_new': 'subscribed',
                        'merge_fields': {
                            'FNAME': name_parts[0],
                            'LNAME': name_parts[1] if len(name_parts) > 1 else '',
                        },
                    }
                    self._api_put(
                        f'lists/{audience.mailchimp_id}/members/{member_hash}',
                        data
                    )
                    total += 1
                except Exception as e:
                    self._log('export_contacts', 'error',
                              f'{contact.email}: {str(e)}')
        self._log('export_contacts', 'success', f'Exported {total} contacts.')
        return total

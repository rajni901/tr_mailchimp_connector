{
    'name': 'MailChimp Connector',
    'version': '19.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Sync Contacts, Audiences and Campaigns between MailChimp and Odoo',
    'description': """
MailChimp Connector — by Vayu Sharma
=========================================
Complete bi-directional sync between MailChimp and Odoo.

Features:
- Import Audiences (Lists) from MailChimp → Odoo Mailing Lists
- Export Mailing Lists from Odoo → MailChimp Audiences
- Import/Export Contacts (Members) bi-directionally
- Import Campaigns from MailChimp
- Export Campaigns to MailChimp
- Campaign Statistics import (opens, clicks, bounces)
- Webhook support for real-time updates
- 4 Scheduled Actions for auto-sync
- Sync logs and error tracking
- Test Connection button
    """,
    'author': 'Vayu Sharma',
    'website': '',
    'license': 'OPL-1',
    'depends': ['mass_mailing', 'contacts', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/scheduled_actions.xml',
        'views/mailchimp_log_views.xml',
        'views/mailing_list_views.xml',
        'views/mailing_views.xml',
        'wizard/mailchimp_sync_wizard_views.xml',
        'views/mailchimp_account_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 5.00,
    'currency': 'USD',
}

# -*- coding: utf-8 -*-
{
    'name': 'Openerp Celery',
    'version': '1.0',
    'author': 'sunchao',
    'category': 'Tools',
    'description': """
通过celery异步消息队列发送短信
需要配置openerp-server.conf
db_password
db_user
db_name
db_port
db_host
sms_send

需要配置短信网关
data/sms.xml

启动具体参考README.md
    """,
    'website': 'https://github.com/xlsunchaoyx',
    'depends': ['mail', ],
    'data': [
        'views/sms_view.xml',
        'data/sms.xml',
    ],
    'installable': True,
    'auto_install': False,
}

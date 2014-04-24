# -*- coding: utf-8 -*-
{
    'name': 'Openerp Celery',
    'version': '1.0',
    'author': 'sunchao',
    'category': 'Tools',
    'description': """
通过celery异步消息队列发送短信 需要配置data/sms.xml
配置celery_worker.py 24-27行数据库配置


后台运行启动rabbitmq-serverserver服务
    sudo rabbitmq-server -detached


停止rabbitmq-server服务
    sudo rabbitmqctl stop


启动异步消息队列 celery
    cd到 openerp/addons/openerp_celery
    运行celery worker --app=celery_worker -l info -E

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

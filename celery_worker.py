# -*- coding: utf-8 -*-
import sys
import os
import logging
import ConfigParser
from celery import Celery


_logger = logging.getLogger(__name__)

# 添加项目目录到环境变量 为了导入openerp
openerp_path = __file__.split('/openerp/addons/openerp_celery')[0]
sys.path.insert(0, openerp_path)


import openerp
from openerp.modules.registry import RegistryManager


# 读取数据库连接配置 配置在openerp-server.conf
db_config = ConfigParser.ConfigParser()
with open('%s/openerp-server.conf' % openerp_path) as conf:
    db_config.readfp(conf)
    config = openerp.tools.config
    config['db_password'] = db_config.get('options', 'db_password')
    config['db_user'] = db_config.get('options', 'db_user')
    config['db_name'] = db_config.get('options', 'db_name')
    config['db_port'] = db_config.get('options', 'db_port')
    config['db_host'] = db_config.get('options', 'db_host')
    try:
        config['sms_send'] = True if db_config.get('options', 'sms_send') == 'True' else False
    except ConfigParser.NoOptionError:
        config['sms_send'] = False

# 注册celery
app = Celery(
    'celery_worker.celery',
    broker='amqp://guest@localhost:5672//',
    backend='amqp://guest@localhost:5672//',
    )


@app.task(name='openerp.addons.openerp_celery.celery_worker.send_sms', max_retries=10)
def send_sms(queue_id):
    """
        发送短信
        max_retries： 最多重发10次
    """
    _logger.info("queue_id: %s" % queue_id)
    _logger.info("retry_test id:%s" % send_sms.request.id)
    _logger.info("retries:%s" % send_sms.request.retries)   # 当前重发次数 从0开始

    send_sms.request.called_directly = False    # 强制制定False 否则无法重发
    registry = RegistryManager.get(config['db_name'])
    with registry.cursor() as cr:
        queue_obj = registry.get('sms.gateway.queue')
        queue = queue_obj.browse(cr, 1, queue_id, context=None)
        result = queue.send()

    _logger.info("result: %s" % result)
    # result在with外判断是为了防止重发机制导致事物无法提交的情况
    if result == 'success':
        return True
    elif result == 'nosend':
        return False
    else:
        args = send_sms.request.args
        kwargs = send_sms.request.kwargs
        # 重发必须放在cr外 否则会导致无法提交
        send_sms.retry(args=args, kwargs=kwargs, exc=Exception(result), countdown=2)

# -*- coding: utf-8 -*-
from openerp.modules.registry import RegistryManager
from openerp.addons.openerp_celery.celery_worker import app, openerp
import logging
import ConfigParser
from celery import Celery


_logger = logging.getLogger(__name__)
"""
    Celery的回调函数
"""

db_name = openerp.tools.config['db_name']


@app.task(name='openerp.addons.openerp_celery.celery_worker.send_sms')
def send_sms(queue_id):
    """发送短信"""
    registry = RegistryManager.get(db_name)
    with registry.cursor() as cr:
        queue_obj = registry.get('sms.gateway.queue')
        _logger.info("queue_id: %s" % queue_id)
        queue = queue_obj.browse(cr, 1, queue_id, context=None)
        result = queue.send()

    return result

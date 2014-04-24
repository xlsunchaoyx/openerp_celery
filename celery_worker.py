# -*- coding: utf-8 -*-
import sys
import os
import logging
import ConfigParser
from celery import Celery


_logger = logging.getLogger(__name__)

# 添加项目目录到环境变量 为了导入openerp
openerp_path = os.getcwd().split('/openerp')[0]
sys.path.insert(0, openerp_path)

import openerp


# 读取数据库连接配置
db_config = ConfigParser.ConfigParser()
with open('%s/openerp-server.conf' % openerp_path) as conf:
    db_config.readfp(conf)
    config = openerp.tools.config
    # 此处读取数据库配置 默认读取工程下openerp-server.conf文件
    config['db_password'] = db_config.get('options', 'db_password')
    config['db_user'] = db_config.get('options', 'db_user')
    config['db_name'] = db_config.get('options', 'db_name')
    config['db_port'] = db_config.get('options', 'db_port')

# 注册celery
app = Celery(
    'openerp',
    broker='amqp://guest@localhost:5672//',
    include=['openerp.addons.openerp_celery.tasks'])

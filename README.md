功能

    openerp下使用celery异步消息队列实现短信发送功能
    支持重新发送 支持发送失败 手工修改短信queue中
    模块的代码参考了openerp的短信模块smsclient（该模块通过cron发送）
    最新版代码未测试 有各种bug欢迎联系qq：395263055


下载工程

    修改openerp_celery/data/sms.xml中xxx数据 配置自己的默认短信网关数据
    配置celery_worker.py 24-27行数据库配置


安装rabbitMQ

    brew install rabbitmq # for mac

    sudo apt-get install rabbitmq-server # for ubuntu


安装celery

    pip install celery


mac下如果rabbitmq未添加到环境变量
配置rabbmitmq服务到PATH
修改vi ~/.bash_profile

    export PATH=/usr/local/bin:/usr/local/sbin:$PATH


mac:后台运行启动停止rabbitmq-serverserver服务

    sudo rabbitmq-server -detached

    sudo rabbitmqctl stop

ubuntu:

    sudo service rabbitmq-server start

openerp项目配置文件修改 增加如下参数

    db_password
    db_user
    db_name
    db_port
    db_host
    sms_send


增加短信网关配置

    修改data/sms.xml


启动异步消息队列 celery

    cd到 openerp/addons/openerp_celery

    运行celery worker --app=celery_worker -l info -E


或后台运行

    celery multi start celery_worker -A celery_worker --concurrency=4 -l info --pidfile=/data/logs/celery_worker.pid --logfile=/data/logs/celery_worker.log
    celery multi restart celery_worker -A celery_worker --concurrency=4 -l info --pidfile=/data/logs/celery_worker.pid --logfile=/data/logs/celery_worker.log
    celery multi stop celery_worker -A celery_worker --concurrency=4 -l info --pidfile=/data/logs/celery_worker.pid --logfile=/data/logs/celery_worker.log


短信发送调用方式
因为MessageQueue写入是实时操作 OE是按照事物提交或者回滚
所以会有发送时 短信网关的数据还在OE的事务中 并未提交到数据库
解决的办法是已经支持了短信重新发送

    self.pool.get('sms.gateway.queue').create_sms(cr, uid, {'mobile': '1xxxxxxxxxx', 'msg': 'msg',})


备注

    rabbitmq必须运行 celery挂掉会在重启后读取rabbitmq的数据 celery调用rabbitmq默认是持久话的
    rabbitmq默认有一个guest用户密码guest


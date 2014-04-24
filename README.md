功能

    openerp下使用celery异步消息队列实现短信发送功能


下载工程

    修改openerp_celery/data/sms.xml中xxx数据 配置自己的默认短信网关数据


安装rabbitMQ

    brew install rabbitmq # for mac

    sudo apt-get install rabbitmq-server # for ubuntu


安装celery

    pip install celery


如果rabbitmq未添加到环境变量
配置rabbmitmq服务到PATH
例如mac下 修改vi ~/.bash_profile

    export PATH=/usr/local/bin:/usr/local/sbin:$PATH


后台运行启动rabbitmq-serverserver服务

    sudo rabbitmq-server -detached


停止rabbitmq-server服务
    sudo rabbitmqctl stop


启动异步消息队列 celery

    cd到 openerp/addons/openerp_celery

    运行celery worker --app=celery_worker -l info -E


备注
    rabbitmq必须运行 celery挂掉会在重启后读取rabbitmq的数据


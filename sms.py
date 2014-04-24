# -*- coding: utf-8 -*-
import datetime
import urllib
import re
from openerp.osv import orm, osv, fields
from openerp.tools.translate import _
from openerp.addons.openerp_celery.tasks import send_sms


"""
    短信发送实现方式
    
    调用短信写入
        self.pool.get('sms.gateway.queue').create_sms(cr, uid, {'mobile': '1xxxxxxxxxx', 'msg': 'msg',})
"""


class sms_gateway(osv.Model):
    """短信网关"""
    _name = 'sms.gateway'

    _columns = {
        'name': fields.char('Gateway Name', size=256, required=True),
        'url': fields.char('Gateway URL', size=256, required=True, help='Base url for message'),
        'state': fields.selection([('ava', 'Available'), ('unava', 'Unavailable')],
            'State', required=True, help='Whether a gateway is available'),
        'param_ids': fields.one2many('sms.gateway.param', 'gateway_id', 'Parameters'),
        'max_send': fields.integer('Max send count'),
    }

    _defaults = {
        'max_send': 3,
        'state': 'ava',
    }

    def get_url(self, cr, uid, ids, mobile, msg, context=None):
        """根据队列传递的手机号和信息拼接短信发送url"""
        gateway = self.browse(cr, uid, ids[0], context)
        prms = {}
        for p in gateway.param_ids:
            if p.type == 'user':
                prms[p.name] = p.value
            elif p.type == 'password':
                prms[p.name] = p.value
            elif p.type == 'to':
                prms[p.name] = mobile
            elif p.type == 'sms':
                prms[p.name] = msg.encode('utf-8')
            elif p.type == 'extra':
                prms[p.name] = p.value
        params = urllib.urlencode(prms)
        url = gateway.url + "?" + params
        return url


class sms_gateway_param(osv.Model):
    """短信网关参数"""
    _name = "sms.gateway.param"

    _columns = {
        'gateway_id': fields.many2one('sms.gateway', 'SMS Gateway', required=True),
        'type': fields.selection([
                ('user', 'User'),
                ('password', 'Password'),
                ('sender', 'Sender Name'),
                ('to', 'Recipient No'),
                ('sms', 'SMS Message'),
                ('extra', 'Extra Info')
            ], 'API Method', select=True,
            help='If parameter concern a value to substitute, indicate it'),
        'name': fields.char('Property name', size=256,
             help='Name of the property whom appear on the URL'),
        'value': fields.char('Property value', size=256,
             help='Value associate on the property for the URL'),
    }


class sms_gateway_queue(osv.Model):
    """短信队列"""
    _name = 'sms.gateway.queue'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _columns = {
        'gateway_id': fields.many2one('sms.gateway', 'SMS Gateway', required=True, help=u"使用的短信网关 默认取第一个"),
        'url': fields.char('SMS URL', size=256, readonly=True,
            states={'draft': [('readonly', False)]},
            help=u"短信发送url 在队列状态中清楚 会在发送的时候根据最新数据重新生成"),
        'mobile': fields.char('Mobile No', size=256,
            required=True, readonly=True,
            states={'draft': [('readonly', False)]}),
        'msg': fields.text('SMS Text', size=256, required=True, readonly=True,
            states={'draft': [('readonly', False)]}),
        'state': fields.selection([
            ('draft', 'Queued'),
            ('sending', 'Waiting'),
            ('send', 'Sent'),
            ('error', 'Error'),
        ], 'Message Status', select=True, readonly=False),#TODO
        'content': fields.text('Return Message', size=256, readonly=True),
        'send_count': fields.integer('Send Count', readonly=False),#TODO
        'create_time': fields.datetime('Create Time', readonly=True),
        'send_time': fields.datetime('Send Time', readonly=True),
        'back_time': fields.datetime('Back Time', readonly=True),
        'is_manual': fields.boolean('Manual', readonly=True),
    }

    def _get_gateway_id(self, cr, uid, context=None):
        gateway_ids = self.pool.get('sms.gateway').search(cr, uid, [], limit=1, order='id')
        if gateway_ids:
            return gateway_ids[0]

    _defaults = {
        'gateway_id': _get_gateway_id,
        'state': 'draft',
        'create_time': fields.datetime.now,
        'send_count': 0,
        'is_manual': True,
    }

    _order = "id desc"

    def create(self, cr, uid, vals, context=None):
        """创建短信队列 根据手机号和短信内容生成短信发送url"""
        gateway_obj = self.pool.get('sms.gateway')
        gateway = gateway_obj.browse(cr, uid, vals['gateway_id'])
        url = gateway.get_url(vals['mobile'], vals['msg'])
        vals['url'] = url
        res_id = super(sms_gateway_queue, self).create(cr, uid, vals, context=context)
        # 加入到短信队列
        send_sms.delay(res_id)

        return res_id

    def create_sms(self, cr, uid, vals, context=None):
        """
            创建短信

            :param dict {'mobile': str, 'msg': str,}
        """
        vals['is_manual'] = False
        return self.create(cr, uid, vals, context)

    def send(self, cr, uid, ids, context=None):
        """发送短信 发送前校验 通过调用_send_sms发送"""
        queue = self.browse(cr, uid, ids[0], context)
        gateway = queue.gateway_id

        # 如果url不存在 重新生成
        if not queue.url:
            url = gateway.get_url(queue.mobile, queue.msg)
            self.write(cr, uid, ids[0], {'url': url})

        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if queue.state != 'draft':
            msg = [u'发送前验证失败', u'当前状态不是队列状态 %s' % queue.state, user.partner_id.id]
            queue.send_message(msg)
            return False

        if gateway.state == 'unava':
            msg = [u'发送前验证失败', u'当前队列指定的短信网关不可用', user.partner_id.id]
            queue.send_message(msg)
            self.write(cr, uid, ids[0], {'state': 'error'})
            return False

        if queue.send_count >= gateway.max_send:
            msg = [u'发送前验证失败', u'发送次数达到当前队列允许的最大发送次数: %s次' % gateway.max_send, user.partner_id.id]
            queue.send_message(msg)
            self.write(cr, uid, ids[0], {'state': 'error'})
            return False

        if len(queue.msg) > 160:
            msg = [u'发送前验证失败', u'超出允许发送的最大160字符长度', user.partner_id.id]
            queue.send_message(msg)
            self.write(cr, uid, ids[0], {'state': 'error'})
            return False

        if not re.match(r'^1\d{10}$', queue.mobile):
            msg = [u'发送前验证失败', u'手机号码格式错误', user.partner_id.id]
            queue.send_message(msg)
            self.write(cr, uid, ids[0], {'state': 'error'})
            return False

        return self._send_sms(cr, uid, ids, context)

    def _send_sms(self, cr, uid, ids, context=None):
        """通过http发送短信"""
        error = False

        queue = self.browse(cr, uid, ids[0], context)
        user = self.pool.get('res.users').browse(cr, uid, uid, context)

        # 请求短信接口
        try:
            send_time = datetime.datetime.now()
            self.write(cr, uid, ids[0], {
                'state': 'sending',
                'send_time': send_time,
                'send_count': queue.send_count + 1})

            smshtml = urllib.urlopen(queue.url)
        except IOError:
            back_time = datetime.datetime.now()
            self.write(cr, uid, ids[0], {
                'back_time': back_time,
                'state': 'draft',
                'content': u'IOError 无法连接到短信服务器',})

            msg = [u'发送失败', u'IOError 无法连接到短信服务器', user.partner_id.id]
            queue.send_message(msg)

            # 加入到短信队列
            send_sms.delay(ids[0])

            error = True

        if error: return error

        # 处理接口返回数据
        try:
            result = smshtml.read()
        except Exception, e:
            back_time = datetime.datetime.now()
            self.write(cr, uid, ids[0], {
                'back_time': back_time,
                'state': 'draft',
                'content': u'未知异常 %s' % e,})

            msg = [u'发送失败', u'未知异常 %s' % e, user.partner_id.id]
            queue.send_message(msg)

            # 加入到短信队列
            send_sms.delay(ids[0])

            error = True
        else:
            back_time = datetime.datetime.now()
            self.write(cr, uid, ids[0], {'back_time': back_time})
            result = result.decode('utf-8')
            res_tuple = result.split("|")
            if len(res_tuple) == 3:
                status, msgId, description = res_tuple

                if status == '1':
                    msg = [u'发送成功', u'返回数据: %s' % result, user.partner_id.id]
                    queue.send_message(msg)

                    self.write(cr, uid, ids[0], {
                        'state': 'send',
                        'content': u'发送成功: %s' % result,})

                    queue = self.browse(cr, uid, ids[0], context)
                    history_obj = self.pool.get('sms.gateway.history')
                    history_obj.create(cr, uid, {
                         'gateway_id': queue.gateway_id.id,
                         'queue_id': queue.id,
                         'url': queue.url,
                         'mobile': queue.mobile,
                         'msg': queue.msg,
                         'number_of_times': queue.send_count,
                         'create_time': queue.create_time,
                         'send_time': queue.send_time,
                         'back_time': queue.back_time,
                         }, )

                else:
                    msg = [u'发送失败', u'返回数据: %s' % result, user.partner_id.id]
                    queue.send_message(msg)

                    self.write(cr, uid, ids[0], {
                        'state': 'error',
                        'content': u'返回数据: %s' % result,})

            else:
                msg = [u'发送失败', u'接口异常 返回格式错误 %s' % result, user.partner_id.id]
                queue.send_message(msg)

                self.write(cr, uid, ids[0], {
                    'state': 'draft',
                    'content': u'接口异常 返回格式错误 %s' % result})

                # 加入到短信队列
                send_sms.delay(ids[0])
        finally:
            smshtml.close()

        return not error

    def send_message(self, cr, uid, ids, msg, context=None):
        """
            增加评论信息

            @param msg ['subject', 'body', res.partner.id]
        """
        subtype = 'mail.mt_comment'

        subject = msg[0]
        body = msg[1]
        send_partner_id = msg[2]
        message_values = {
            'subject': subject,
            'body': body,
            'parent_id': '',
            'partner_ids': [send_partner_id, ],
            'attachment_ids': [],
            'res_id': ids[0],
        }

        self.message_post(cr, 1, ids, subtype=subtype, context=context, **message_values)


class sms_gateway_history(osv.Model):
    """
        短信成功发送历史记录
    """
    _name = 'sms.gateway.history'
    _columns = {
        'gateway_id': fields.many2one('sms.gateway', 'SMS Gateway', required=True, readonly=True,),
        'queue_id': fields.many2one('sms.gateway.queue', 'SMS Gateway Queue', required=True, readonly=True,),
        'url': fields.char('SMS URL', size=256, required=True, readonly=True, help='Url for send message'),
        'mobile': fields.char('Mobile No', size=256,
            required=True, readonly=True),
        'msg': fields.text('SMS Text', size=256, required=True, readonly=True),
        'number_of_times': fields.integer('Number of times', readonly=True, help=u"发送次数"),
        'create_time': fields.datetime('Create Time', readonly=True),
        'send_time': fields.datetime('Send Time', readonly=True),
        'back_time': fields.datetime('Back Time', readonly=True),
    }

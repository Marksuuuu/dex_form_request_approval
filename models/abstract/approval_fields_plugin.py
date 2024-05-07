import hashlib
import re
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

# from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ApprovalFieldsPlugin(models.AbstractModel):
    _name = 'approval.fields.plugins'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Approval Fields Plugin for Abstract Models'

    def _get_department_domain(self):
        return []

    name = fields.Char(string='Control No.', copy=False, readonly=True, index=True,
                       default=lambda self: _('New'), tracking=True)
    requesters_id = fields.Many2one('hr.employee', string='Requesters', required=True,
                                    default=lambda self: self.env.user.employee_id.id, tracking=True)
    requesters_email = fields.Char(related='requesters_id.work_email', string='Requesters Email', required=True,
                                   tracking=True)
    requesters_department = fields.Many2one(related='requesters_id.department_id', string='Requesters Department',
                                            store=True, tracking=True)

    # to be overridden by child models

    department_id = fields.Many2one('approver.setup', string='Department', domain=lambda a: a._get_department_domain(),
                                    tracking=True, required=True)

    form_request_type = fields.Selection(related='department_id.approval_type', string='Form Request Type', store=True,
                                         readonly=True, tracking=True)

    approval_stage = fields.Integer(default=1, tracking=True)
    approval_link = fields.Char(string='Approval Link')

    state = fields.Selection(
        selection=[('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'),
                   ('disapprove', 'Disapproved'), ('cancel', 'Cancelled')],
        default='draft', tracking=True)

    approval_status = fields.Selection(
        selection=[('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'),
                   ('disapprove', 'Disapproved'), ('cancel', 'Cancelled')], string='Status', default='draft',
        tracking=True)

    initial_approver_email = fields.Char(string='Initial Approver Email', tracking=True)
    second_approver_email = fields.Char(string='Second Approver Email', tracking=True)
    third_approver_email = fields.Char(string='Third Approver Email', tracking=True)
    fourth_approver_email = fields.Char(string='Fourth Approver Email', tracking=True)
    final_approver_email = fields.Char(string='Final Approver Email', tracking=True)

    initial_approver_name = fields.Char(string='Initial Approver Name', tracking=True)
    second_approver_name = fields.Char(string='Second Approver Name', tracking=True)
    third_approver_name = fields.Char(string='Third Approver name', tracking=True)
    fourth_approver_name = fields.Char(string='Fourth Approver name', tracking=True)
    final_approver_name = fields.Char(string='Final Approver name', tracking=True)

    disapproval_reason = fields.Char(string="Reason for Disapproval", tracking=True)
    disapproved_by = fields.Many2one('res.users', string="Disapproved By", tracking=True)
    disapproved_date = fields.Datetime(string="Disapproved Date", tracking=True)

    cancellation_reason = fields.Char(string="Reason for Cancellation", tracking=True)
    cancelled_by = fields.Many2one('res.users', string="Cancelled By", tracking=True)
    cancelled_date = fields.Datetime(string="Cancelled Date", tracking=True)

    initial_approver_job_title = fields.Char(compute='get_approver_title', store=True)
    second_approver_job_title = fields.Char(compute='get_approver_title', store=True)
    third_approver_job_title = fields.Char(compute='get_approver_title', store=True)
    fourth_approver_job_title = fields.Char(compute='get_approver_title', store=True)
    final_approver_job_title = fields.Char(compute='get_approver_title', store=True)

    def approval_dashboard_link(self):
        pass

    def user_error_notif(self, msg):
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Error {}'.format(msg)),
                'message': f'{msg}',
                'sticky': True,
            }
        }
        return notification

    def main_connection(self):
        # Load credentials from a secure source
        sender = self.env['ir.config_parameter'].sudo().get_param('dex_form_request_approval.sender')
        host = self.env['ir.config_parameter'].sudo().get_param('dex_form_request_approval.host')
        port = self.env['ir.config_parameter'].sudo().get_param('dex_form_request_approval.port')
        username = self.env['ir.config_parameter'].sudo().get_param('dex_form_request_approval.username')
        password = self.env['ir.config_parameter'].sudo().get_param('dex_form_request_approval.password')

        credentials = {
            'sender': sender,
            'host': host,
            'port': port,
            'username': username,
            'password': password
        }
        return credentials

    @api.depends('initial_approver_name', 'second_approver_name', 'third_approver_name', 'fourth_approver_name',
                 'final_approver_name')
    def get_approver_title(self):
        for record in self:
            if record.initial_approver_name:
                approver = self.env['hr.employee'].search([('name', '=', record.initial_approver_name)], limit=1)
                record.initial_approver_job_title = approver.job_title if approver else False

            if record.second_approver_name:
                approver = self.env['hr.employee'].search([('name', '=', record.second_approver_name)], limit=1)
                record.second_approver_job_title = approver.job_title if approver else False

            if record.third_approver_name:
                approver = self.env['hr.employee'].search([('name', '=', record.third_approver_name)], limit=1)
                record.third_approver_job_title = approver.job_title if approver else False

            if record.fourth_approver_name:
                approver = self.env['hr.employee'].search([('name', '=', record.fourth_approver_name)], limit=1)
                record.fourth_approver_job_title = approver.job_title if approver else False

            if record.final_approver_name:
                approver = self.env['hr.employee'].search([('name', '=', record.final_approver_name)], limit=1)
                record.final_approver_job_title = approver.job_title if approver else False

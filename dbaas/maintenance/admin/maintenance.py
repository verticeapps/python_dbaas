# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from django_services import admin
from ..service.maintenance import MaintenanceService
from ..forms import MaintenanceForm
from django.utils.html import format_html
from django.http import HttpResponseRedirect
import logging
from django.contrib import messages
from django.core.urlresolvers import reverse
LOG = logging.getLogger(__name__)
from .. import models


class MaintenanceAdmin(admin.DjangoServicesAdmin):
    service_class = MaintenanceService
    search_fields = ("scheduled_for", "description", "maximum_workers", "status")
    list_display = ("description", "scheduled_for", "started_at", "finished_at",
        "maximum_workers", "affected_hosts_html", "friendly_status")
    fields = ( "description", "scheduled_for", "started_at", "finished_at",
         "main_script", "rollback_script", "hostsid", "maximum_workers",
         "status", "celery_task_id", "affected_hosts")
    form = MaintenanceForm
    actions = None

    def revoke_maintenance(request, id):
        maintenance = models.Maintenance.objects.get(id=id)

        if maintenance.status == maintenance.WAITING:
            if maintenance.revoke_maintenance():
                messages.add_message(request,  messages.SUCCESS,
                    "Maintenance revoked!",)
            else:
                messages.add_message(request,  messages.ERROR,
                    "Maintenance has already started!",)
        else:
            messages.add_message(request,  messages.ERROR,
                "Maintenance can't be revoked!",)

        return HttpResponseRedirect(reverse('admin:maintenance_maintenance_changelist'))

    buttons = [
        {
         'url': 'revoke_maintenance',
         'textname': 'Revoke Maintenance',
         'func': revoke_maintenance,
         'confirm': u'Do you really want to revoke this maintenance?'
        },
    ]

    def change_view(self, request, object_id, form_url='', extra_context={}):
        extra_context['buttons'] = self.buttons
        return super(MaintenanceAdmin, self).change_view(request, object_id, form_url, extra_context=extra_context)

    def get_urls(self):
        from django.conf.urls import url
        urls = super(MaintenanceAdmin, self).get_urls()
        my_urls = list( (url(r'^(.+)/%(url)s/$' % b, self.admin_site.admin_view(b['func'])) for b in self.buttons) )
        return my_urls + urls


    def get_readonly_fields(self, request, obj=None):
        maintenance = obj
        if maintenance and maintenance.status !=models.Maintenance.REJECTED:
            self.change_form_template = "admin/maintenance/maintenance/custom_change_form.html"
        else:
            self.change_form_template = None

        if maintenance and maintenance.celery_task_id:
            return self.fields

        return ('status', 'celery_task_id', 'affected_hosts', 'started_at', 'finished_at')

    def friendly_status(self, maintenance):

        html_finished = '<span class="label label-info">Finished</span>'
        html_rejected = '<span class="label label-important">Rejected</span>'
        html_waiting = '<span class="label label-warning">Waiting</span>'
        html_running = '<span class="label label-success">Running</span>'
        html_revoked = '<span class="label label-primary">Revoked</span>'

        if maintenance.status == models.Maintenance.FINISHED:
            return format_html(html_finished)
        elif maintenance.status == models.Maintenance.REJECTED:
            return format_html(html_rejected)
        elif maintenance.status == models.Maintenance.WAITING:
            return format_html(html_waiting)
        elif maintenance.status == models.Maintenance.RUNNING:
            return format_html(html_running)
        elif maintenance.status == models.Maintenance.REVOKED:
            return format_html(html_revoked)

    friendly_status.short_description = "Status"


    def affected_hosts_html(self, maintenance):
        html = []
        html.append("<a href='../hostmaintenance/?maintenance__id=%s'>%s</a>" % (maintenance.id, maintenance.affected_hosts))

        return format_html("".join(html))

    affected_hosts_html.short_description = "Affected hosts"


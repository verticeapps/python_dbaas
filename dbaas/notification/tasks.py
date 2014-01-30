# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.conf import settings

import os
import logging
from celery import states
from celery.utils.log import get_task_logger
from dbaas.celery import app

from util import call_script
from .util import get_clone_args
from .models import TaskHistory
 
LOG = get_task_logger(__name__)

CLONE_DATABASE_SCRIPT_NAME="dummy_clone.sh"

def get_history_for_task_id(task_id):
    try:
        return TaskHistory.objects.get(task_id=task_id)
    except Exception, e:
        LOG.error("could not find history for task id %s" % task_id)
        return None

@app.task(bind=True)
def clone_database(self, origin_database, dest_database, user=None):
    
    #register History
    task_history = TaskHistory.register(request=self.request, user=user)
    
    LOG.info("origin_database: %s" % origin_database)
    LOG.info("dest_database: %s" % dest_database)

    LOG.info("id: %s | task: %s | kwargs: %s | args: %s" % (self.request.id,
                                                            self.request.task,
                                                            self.request.kwargs,
                                                            str(self.request.args)))

    args = get_clone_args(origin_database, dest_database)

    try:
        call_script(CLONE_DATABASE_SCRIPT_NAME, working_dir=settings.SCRIPTS_PATH, args=args)
        task_history.update_status_for(TaskHistory.STATUS_SUCCESS)
    except Exception, e:
        LOG.error("task id %s error: %s" % (self.request.id, e))
        task_history.update_status_for(TaskHistory.STATUS_ERROR)

    return
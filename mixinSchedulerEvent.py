# coding=utf-8
# !/usr/bin/python3
# Name:         mixinSchedulerEvent
# Copyright:   (c) 2019 TK
# Licence:     MIT
# -------------------------------------------------------------------------------
import logging
logger = logging.getLogger('mixin')

import apscheduler.events as _SchedulerEvents

# ==================================================================================
class mixinSchedulerEvent(object):
    _scheduler = None
    event_codes = {
        _SchedulerEvents.EVENT_ALL_JOBS_REMOVED:    ('EVENT_ALL_JOBS_REMOVED',      logger.info),
        _SchedulerEvents.EVENT_EXECUTOR_ADDED:      ('EVENT_EXECUTOR_ADDED',        logger.info),
        _SchedulerEvents.EVENT_EXECUTOR_REMOVED:    ('EVENT_EXECUTOR_REMOVED',      logger.info),
        _SchedulerEvents.EVENT_JOB_ADDED:           ('EVENT_JOB_ADDED',             logger.info),
        _SchedulerEvents.EVENT_JOB_ERROR:           ('EVENT_JOB_ERROR',             logger.error),
        _SchedulerEvents.EVENT_JOB_EXECUTED:        ('EVENT_JOB_EXECUTED',          logger.info),
        _SchedulerEvents.EVENT_JOB_MAX_INSTANCES:   ('EVENT_MAX_INSTANCES',         logger.warning),
        _SchedulerEvents.EVENT_JOB_MISSED:          ('EVENT_JOB_MISSED',            logger.warning),
        _SchedulerEvents.EVENT_JOB_MODIFIED:        ('EVENT_JOB_MODIFIED',          logger.info),
        _SchedulerEvents.EVENT_JOB_REMOVED:         ('EVENT_JOB_REMOVED',           logger.info),
        _SchedulerEvents.EVENT_JOB_SUBMITTED:       ('EVENT_JOB_SUBMITTED',         logger.debug),
        _SchedulerEvents.EVENT_JOBSTORE_ADDED:      ('EVENT_JOBSTORE_ADDED',        logger.info),
        _SchedulerEvents.EVENT_JOBSTORE_REMOVED:    ('EVENT_JOBSTORE_REMOVED',      logger.info),
        _SchedulerEvents.EVENT_SCHEDULER_PAUSED:    ('EVENT_SCHEDULER_PAUSED',      logger.info),
        _SchedulerEvents.EVENT_SCHEDULER_RESUMED:   ('EVENT_SCHEDULER_RESUMED',     logger.info),
        _SchedulerEvents.EVENT_SCHEDULER_SHUTDOWN:  ('EVENT_SCHEDULER_SHUTDOWN',    logger.info),
        _SchedulerEvents.EVENT_SCHEDULER_START:     ('EVENT_SCHEDULER_START',       logger.info),
        _SchedulerEvents.EVENT_SCHEDULER_STARTED:   ('EVENT_SCHEDULER_STARTED',     logger.info)
    }
    event_list = [
        _SchedulerEvents.EVENT_ALL_JOBS_REMOVED,
        _SchedulerEvents.EVENT_JOB_ADDED,
        _SchedulerEvents.EVENT_JOB_ERROR,
        _SchedulerEvents.EVENT_JOB_MAX_INSTANCES,
        _SchedulerEvents.EVENT_JOB_MISSED,
        _SchedulerEvents.EVENT_JOB_REMOVED,
        _SchedulerEvents.EVENT_SCHEDULER_SHUTDOWN,
        _SchedulerEvents.EVENT_SCHEDULER_START,
        _SchedulerEvents.EVENT_SCHEDULER_STARTED,
        _SchedulerEvents.EVENT_JOB_EXECUTED,
        _SchedulerEvents.EVENT_JOB_SUBMITTED
    ]

#-----------------------------------------------------------------------------------
    def _job_event(self, p_event):
        logger.debug(f'enter event:{p_event}')

        if not (p_event.code in self.event_list):
            return

        if p_event.code in self.event_codes:
            (l_event_name, l_event_logger) = self.event_codes[p_event.code]
        else:
            l_event_name = ''
            l_event_logger = logger.info

        if hasattr(p_event, 'job_id'):
            if p_event.job_id == '_ticktak_':
              return
            l_job = self._scheduler.get_job(p_event.job_id)
        else:
            l_job = None
 
        if getattr(p_event, 'exception', None):
            logger.error(f'*** exception {l_event_name} ({p_event.code}) job_id:{p_event.job_id} exception:{p_event.exception}')
            return

        if (isinstance(p_event, _SchedulerEvents.JobExecutionEvent) or
            isinstance(p_event, _SchedulerEvents.JobSubmissionEvent) or
            isinstance(p_event, _SchedulerEvents.JobEvent)
        ):
            l_event_logger(f'{l_event_name} ({p_event.code}) job_id:{p_event.job_id}')
        elif isinstance(p_event, _SchedulerEvents.SchedulerEvent):
            l_event_logger(f'{l_event_name} ({p_event.code})')

        if l_job:
          logger.debug(f'{l_job}')

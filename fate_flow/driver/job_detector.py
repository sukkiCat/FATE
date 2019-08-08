from arch.api.utils.core import get_lan_ip
from fate_flow.settings import detect_logger, API_VERSION, schedule_logger
from fate_flow.utils import cron, job_utils, api_utils


class JobDetector(cron.Cron):
    def run_do(self):
        running_tasks = job_utils.query_task(status='running', run_ip=get_lan_ip())
        stop_job_ids = set()
        detect_logger.info('start to detect running job..')
        for task in running_tasks:
            try:
                process_exist = job_utils.check_job_process(int(task.f_run_pid),
                                                            keywords=[task.f_job_id, task.f_task_id, task.f_role,
                                                                      task.f_party_id])
                if not process_exist:
                    detect_logger.info(
                        'job {} component {} on {} {} task {} {} process does not exist'.format(task.f_job_id,
                                                                                                task.f_component_name,
                                                                                                task.f_role,
                                                                                                task.f_party_id,
                                                                                                task.f_task_id,
                                                                                                task.f_run_pid))
                    stop_job_ids.add(task.f_job_id)
            except Exception as e:
                detect_logger.exception(e)
        if stop_job_ids:
            schedule_logger.info('start to stop jobs: {}'.format(stop_job_ids))
        for job_id in stop_job_ids:
            jobs = job_utils.query_job(job_id=job_id)
            if jobs:
                initiator_party_id = jobs[0].f_initiator_party_id
                job_work_mode = jobs[0].f_work_mode
                if len(jobs) > 1:
                    # i am initiator
                    my_party_id = initiator_party_id
                else:
                    my_party_id = jobs[0].f_party_id
                    initiator_party_id = jobs[0].f_initiator_party_id
                api_utils.federated_api(job_id=job_id,
                                        method='POST',
                                        url_without_host='/{}/job/stop'.format(
                                            API_VERSION),
                                        src_party_id=my_party_id,
                                        dest_party_id=initiator_party_id,
                                        json_body={'job_id': job_id},
                                        work_mode=job_work_mode)
                schedule_logger.info('send stop job {} command'.format(job_id))
        detect_logger.info('finish detect running job')

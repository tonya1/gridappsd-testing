from contextlib import contextmanager
import json
import logging

import os

from time import sleep, time
import pytest
import yaml

from conftest import gridappsd_client
from gridappsd import GridAPPSD

# from gridappsd.simulation import Simulation
# from gridappsd_docker import docker_up, docker_down
from gridappsd import topics as t

LOGGER = logging.getLogger(__name__)
sim_id = "151989"
log_topic = '/topic/goss.gridappsd.simulation.log'
request_topic = '.'.join((t.BASE_SIMULATION_STATUS_TOPIC , sim_id))


os.environ['GRIDAPPSD_APPLICATION_ID'] = 'test-logging-service'
os.environ['GRIDAPPSD_APPLICATION_STATUS'] = 'STARTED'
os.environ['GRIDAPPSD_SIMULATION_ID'] = sim_id


def on_message(self, message):
    json_msg = yaml.safe_load(str(message))
    print(json_msg)

def test_logging_output(gridappsd_client):

    gapps = gridappsd_client
    gapps.subscribe(t.simulation_log_topic(sim_id), on_message)
    gapps_logger = gapps.get_logger()
    gapps_logger.info("Publishing logs to database")
    query = {"query": "select * from log"}
    print(gapps.get_response(t.LOGS, json.dumps(query), timeout=60))
    sleep(30)



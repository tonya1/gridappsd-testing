import json
import logging
import os
from time import sleep, time
import yaml
from gridappsd import topics as t

LOGGER = logging.getLogger(__name__)
sim_id = "151989"
log_topic = '/topic/goss.gridappsd.simulation.log'
request_topic = t.simulation_log_topic(sim_id)


os.environ['GRIDAPPSD_APPLICATION_ID'] = 'test-logging-service'
os.environ['GRIDAPPSD_APPLICATION_STATUS'] = 'STARTED'
os.environ['GRIDAPPSD_SIMULATION_ID'] = sim_id


def on_message(self, message):
    json_msg = yaml.safe_load(str(message))
    print(json_msg)


def test_logging_output(record_property, gridappsd_client):
    doc_str = """This function queries the database through the gridappsd api.  Specifically checking that the 
    specific logs are available.  The results are interrogated for the logs pushed to the topic and stored in the 
    database. The return values of the query are interrogated and the values associated are tested """

    record_property("gridappsd_doc", doc_str)
    gapps = gridappsd_client
    gapps_logger = gapps.get_logger()
    gapps_logger.info("Publishing logs to database")
    sleep(5)
    print("-------------")
    query = {"query": "select * from log where log_message ='Publishing logs to database'"}
    print(gapps.get_response(t.LOGS, json.dumps(query), timeout=60))
    sleep(30)



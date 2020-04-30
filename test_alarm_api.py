from contextlib import contextmanager
import json
import logging
import os
from time import sleep, time
import sys
import pandas as pd
import pytest
from numbers import Number
from math import isclose

import yaml
from gridappsd import GridAPPSD, topics as t
# tm: added for run_simulation workaround
from gridappsd.simulation import Simulation
from gridappsd_docker import docker_up, docker_down

LOGGER = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


@contextmanager
def startup_containers(spec=None):
    docker_up(spec)

    yield

    docker_down()


@contextmanager
def gappsd() -> GridAPPSD:
    gridappsd = GridAPPSD()

    yield gridappsd

    gridappsd.disconnect()


def on_message(self, message):
    """ This method handles incoming messages on the fncs_output_topic for the simulation_id.
    Parameters
    ----------
    headers: dict
        A dictionary of headers that could be used to determine topic of origin and
        other attributes.
    message: object
    """
    # message ={}
    try:
        message_str = 'received message ' + str(message)

        json_msg = yaml.safe_load(str(message))

        with open("/tmp/output/alarm.json", 'w') as f:
            f.write(json.dumps(json_msg))
        with open("/tmp/output/alarm.json", 'r') as fp:
            alarm = json.load(fp)
            for y in alarm:
                if "created_by" in y:
                    print("Alarm present")

    except Exception as e:
        message_str = "An error occurred while trying to translate the  message received" + str(e)


@pytest.mark.parametrize("sim_config_file, sim_result_file", [
    ("9500-alarm-config.json", "9500-alarm-simulation.output")
    # ("123-config.json", "123-simulation.output"),
    # ("13-node-config.json", "13-node-sim.output"),
    # , ("t3-p1-config.json", "t3-p1.output"),
])
def test_alarm_output(sim_config_file, sim_result_file):
    simulation_id = None
    sim_config_file = os.path.join(os.path.dirname(__file__), f"simulation_config_files/{sim_config_file}")
    sim_result_file = os.path.join(os.path.dirname(__file__), f"simulation_baseline_files/{sim_result_file}")
    # sim_test_config = os.path.join(os.path.dirname(__file__), f"simulation_baseline_files/{sim_test_file}")

    assert os.path.exists(sim_config_file), f"File {sim_config_file} must exist to run simulation test"
    # assert os.path.exists(sim_result_file), f"File {sim_result_file} must exist to run simulation test"

    with startup_containers():
        with gappsd() as gapps:
            os.makedirs("/tmp/output", exist_ok=True)
            with open("/tmp/output/simulation.output", 'w') as outfile:
                sim_complete = False
                rcvd_measurement = False

                def onmeasurement(sim, timestep, measurements):
                    nonlocal rcvd_measurement
                    # print(rcvd_measurement)
                    if not rcvd_measurement:
                        LOGGER.info('A measurement happened at {timestep}"')
                        rcvd_measurement = True

                def onfinishsimulation(sim):
                    nonlocal sim_complete
                    sim_complete = True
                    print("Completed simulator")

                #print("Running config")
                with open(sim_config_file) as fp:
                    run_config = json.load(fp)
                    print(run_config["simulation_config"]["start_time"])

                sim = Simulation(gapps, run_config)

                sim.start_simulation()
                LOGGER.info('Starting sim')
                print(sim.simulation_id)
                alarms_topic = t.service_output_topic('gridappsd-alarms', sim.simulation_id)
                print(alarms_topic)
                gapps.subscribe(alarms_topic, on_message)

                print("Alarm topic working")
                #print(gapps.subscribe(alarms_topic, on_message))
                sim.add_onmesurement_callback(onmeasurement)
                sim.add_oncomplete_callback(onfinishsimulation)
                LOGGER.info('sim.add_onmesurement_callback')
                sim.add_onmesurement_callback(onmeasurement)
                LOGGER.info('sim.add_oncomplete_callback')
                sim.add_oncomplete_callback(onfinishsimulation)


                while not sim_complete:
                    LOGGER.info('Sleeping')
                    sleep(30)

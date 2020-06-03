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
    LOGGER.info('Starting gridappsd containers')
    docker_up(spec)
    LOGGER.info('Containers started')

    yield

    # LOGGER.info('Stopping gridappsd containers')
    # docker_down()
    # LOGGER.info('Containers stopped')


@contextmanager
def gappsd() -> GridAPPSD:
    gridappsd = GridAPPSD()
    LOGGER.info('Gridappsd connected')

    yield gridappsd

    gridappsd.disconnect()
    LOGGER.info('Gridappsd disconnected')


# def test_start_gridappsd():
#    with startup_containers():
#        g = GridAPPSD()
#        assert g.connected


def on_message(headers, message):
    try:
        message_str = 'received message ' + str(message)
        json_msg = yaml.safe_load(str(message))
        #print(headers)
        if "gridappsd-alarms" in headers["destination"]:
            print(json_msg)
            with open("/tmp/output/alarm.json", 'w') as f:
                f.write(json.dumps(json_msg))
            with open("/tmp/output/alarm.json", 'r') as fp:
                alarm = json.load(fp)
                for y in alarm:
                    if "_302E3119-B3ED-46A1-87D5-EBC8496357DF" or "_A0E0AB93-FFC2-471B-B84C-19015CB15ED2" or "_2FA4B41B-C31B-4861-B8BB-941A8DFD1B41" in json_msg['equipment_mrid']:
                        if "Open" in y['value']:
                            LOGGER.info('Alarms created')

        if "output" in headers["destination"]:
            measurement_values = json_msg["message"]["measurements"]
            for x in measurement_values:
                m = measurement_values[x]
                if m.get("measurement_id") == "_0f8202ca-a4bf-4c7e-9302-601919c09992":
                    print("Present")
                    if m.get("value") == "10":
                        LOGGER.info('Value changed from 5 to 10')

    except Exception as e:
        message_str = "An error occurred while trying to translate the  message received" + str(e)


@pytest.mark.parametrize("sim_config_file, sim_result_file", [
    ("9500-alarm-config.json", "9500-alarm-simulation.output")

])
def test_alarm_output(sim_config_file, sim_result_file):
    simulation_id = None
    sim_config_file = os.path.join(os.path.dirname(__file__), f"simulation_config_files/{sim_config_file}")
    sim_result_file = os.path.join(os.path.dirname(__file__), f"simulation_baseline_files/{sim_result_file}")

    assert os.path.exists(sim_config_file), f"File {sim_config_file} must exist to run simulation test"

    with startup_containers():
        with gappsd() as gapps:
            os.makedirs("/tmp/output", exist_ok=True)
            with open("/tmp/output/simulation.output", 'w') as outfile:
                sim_complete = False
                rcvd_measurement = False

                def onmeasurement(sim, timestep, measurements):
                    nonlocal rcvd_measurement
                    LOGGER.info('A measurement happened at %s', timestep)
                    rcvd_measurement = True

                def onfinishsimulation(sim):
                    nonlocal sim_complete
                    sim_complete = True
                    print("Completed simulator")

                with open(sim_config_file) as fp:
                    run_config = json.load(fp)
                    print(run_config["simulation_config"]["start_time"])

                sim = Simulation(gapps, run_config)

                sim.start_simulation()
                LOGGER.info('Starting the  simulation')
                print(sim.simulation_id)
                alarms_topic = t.service_output_topic('gridappsd-alarms', sim.simulation_id)
                print(alarms_topic)
                sim.add_onmesurement_callback(onmeasurement)
                sim.add_oncomplete_callback(onfinishsimulation)
                LOGGER.info('sim.add_onmesurement_callback')
                log_topic = t.simulation_output_topic(sim.simulation_id)
                LOGGER.info("Querying Alarm topic for alarms")
                gapps.subscribe(alarms_topic, on_message)
                gapps.subscribe(log_topic, on_message)
                print(log_topic)

                while not sim_complete:
                    LOGGER.info('Sleeping')
                    sleep(30)

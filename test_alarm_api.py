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
# global tapchanger_value

tapchanger_value = -1
alarm_count = 0
#outage_mrid = {}

def on_message(headers, message):
    global tapchanger_value
    global alarm_count
    #global outage_mrid
    if "gridappsd-alarms" in headers["destination"]:
        # print(headers)
        if "_302E3119-B3ED-46A1-87D5-EBC8496357DF" or "_A0E0AB93-FFC2-471B-B84C-19015CB15ED2" or "_2FA4B41B-C31B-4861-B8BB-941A8DFD1B41" in \
                message['equipment_mrid']:
            for y in message:
                print(y)
                if "Open" in y['value']:
                    LOGGER.info('Alarms created')
                    alarm_count += 1

    if "gridappsd-alarms" not in headers["destination"]:
        # print(headers)
        measurement_values = message["message"]["measurements"]
        for x in measurement_values:
            # print(measurement_values)
            m = measurement_values[x]
            if m.get("measurement_mrid") == "_0f8202ca-a4bf-4c7e-9302-601919c09992":
                if m.get("value") != tapchanger_value:
                    tapchanger_value = m.get("value")
                    LOGGER.info(f"Tap Changer Value changed to {tapchanger_value}")
                                    
            # elif m.get("measurement_mrid") != outage_mrid:
            #     outage_mrid = "_0f8202ca-a4bf-4c7e-9302-601919c09992"
            #     print("mRID not present")


            # if "_0f8202ca-a4bf-4c7e-9302-601919c09992" not in m.get("measurement_mrid"):
            #     print("mRID not there")
            #     with open("./input.txt", 'w') as f:
            #         f.write(x)

            # if m.get("measurement_mrid") == "_E44571D4-52CE-4ACE-9012-37DEBF17FCF8":
            #     print("mRID not there")
            #     with open("./input.txt", 'a') as f:
            #         f.write(x)


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
                    # if not rcvd_measurement:
                    rcvd_measurement = True
                    LOGGER.info('A measurement happened at %s', timestep)

                def onfinishsimulation(sim):
                    nonlocal sim_complete
                    sim_complete = True
                    print("Completed simulator")

                with open(sim_config_file) as fp:
                    run_config = json.load(fp)
                    print(run_config["simulation_config"]["start_time"])

                sim = Simulation(gapps, run_config)

                LOGGER.info('Starting the  simulation')
                sim.add_onmesurement_callback(onmeasurement)
                sim.add_oncomplete_callback(onfinishsimulation)
                LOGGER.info('sim.add_onmesurement_callback')
                LOGGER.info("Querying Alarm topic for alarms")
                sim.start_simulation()
                print(sim.simulation_id)
                alarms_topic = t.service_output_topic('gridappsd-alarms', sim.simulation_id)
                log_topic = t.simulation_output_topic(sim.simulation_id)
                input_topic = t.simulation_input_topic(sim.simulation_id)
                gapps.subscribe(alarms_topic, on_message)
                gapps.subscribe(log_topic, on_message)
                # gapps.subscribe(input_topic, on_message)

                while not sim_complete:
                    LOGGER.info('Sleeping')
                    sleep(30)


def test_tap_changer():
    global tapchanger_value
    assert tapchanger_value == 10, "Tap Changer value is not as expected"

def test_alarm_count():
    global alarm_count
    assert alarm_count == 3, "Three Alarms were not generated"

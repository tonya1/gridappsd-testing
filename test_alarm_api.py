from contextlib import contextmanager
import json
import logging
import os
import yaml
from time import sleep, time
import sys
import pytest

from gridappsd import GridAPPSD
from gridappsd.simulation import Simulation
from gridappsd_docker import docker_up, docker_down
from gridappsd import topics as t

LOGGER = logging.getLogger(__name__)

tapchanger_value = []
alarm_count = 0

def on_message(headers, message):
    global tapchanger_value
    global alarm_count
    
    if "gridappsd-alarms" in headers["destination"]:
        if "ln1047pvfrm_sw" or "ln5001chp_sw" or "ln0895780_sw" in \
                message['equipment_name']:
            for y in message:
                if "Open" in y['value']:
                    LOGGER.info(f'Alarm created {y}')
                    alarm_count += 1

    if "gridappsd-alarms" not in headers["destination"]:
        measurement_values = message["message"]["measurements"]
        for x in measurement_values:
            m = measurement_values[x]
            if m.get("measurement_mrid") == "_48e11ee1-ea9f-4e0c-a6dd-2807a9dbc032":
               if not tapchanger_value:
                    LOGGER.info(f'Tap Changer value is {m.get("value")}')
                    tapchanger_value.append(m.get("value"))
               else:
                    if m.get("value") != tapchanger_value[-1]:
                        LOGGER.info(f'Tap Changer value changed from {tapchanger_value[-1]} to {m.get("value")} {m}')
                        tapchanger_value.append(m.get("value"))

@pytest.mark.parametrize("sim_config_file, sim_result_file", [
    ("9500-alarm-config.json", "9500-alarm-simulation.output")

])
def test_alarm_output(gridappsd_client, sim_config_file, sim_result_file):
    sim_config_file = os.path.join(os.path.dirname(__file__), f"simulation_config_files/{sim_config_file}")
    sim_result_file = os.path.join(os.path.dirname(__file__), f"simulation_baseline_files/{sim_result_file}")
    assert os.path.exists(sim_config_file), f"File {sim_config_file} must exist to run simulation test"

    gapps = gridappsd_client
    # Allow proven to come up
    sleep(30)
    
    sim_complete = False
    rcvd_measurement = False

    
    #def onmeasurement(sim, timestep, measurements):
    #    nonlocal rcvd_measurement
        # if not rcvd_measurement:
    #    rcvd_measurement = True
    #    LOGGER.info('A measurement happened at %s', timestep)

    def onfinishsimulation(sim):
        nonlocal sim_complete
        sim_complete = True
        LOGGER.info('Simulation Complete')

    with open(sim_config_file) as fp:
        LOGGER.info('Loading config')
        run_config = json.load(fp)
        LOGGER.info(f'Simulation start time {run_config["simulation_config"]["start_time"]}')

    sim = Simulation(gapps, run_config)

    LOGGER.info('Starting the simulation')
    sim.start_simulation()

    #LOGGER.info('sim.add_onmesurement_callback')
    #sim.add_onmesurement_callback(onmeasurement)
    LOGGER.info('sim.add_oncomplete_callback')
    sim.add_oncomplete_callback(onfinishsimulation)

    LOGGER.info("Querying for alarm topic")
    alarms_topic = t.service_output_topic('gridappsd-alarms', sim.simulation_id)
    log_topic = t.simulation_output_topic(sim.simulation_id)
    gapps.subscribe(alarms_topic, on_message)
    gapps.subscribe(log_topic, on_message)

    while not sim_complete:
        LOGGER.info('Sleeping')
        sleep(30)


def test_tap_changer():
    global tapchanger_value
    assert tapchanger_value == [4, 10, 5], f"Expected tap changer values [4, 10, 5] received {tapchanger_value}"


def test_alarm_count():
    global alarm_count
    assert alarm_count == 3, f"Expecting 3 alarms received {alarm_count}"

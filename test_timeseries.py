import ast
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

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

LOGGER = logging.getLogger(__name__)


@contextmanager
def startup_containers(spec=None):
    LOGGER.info('Starting gridappsd containers')
    docker_up(spec)
    LOGGER.info('Containers started')

    yield

    LOGGER.info('Stopping gridappsd containers')
    #docker_down()
    #LOGGER.info('Containers stopped')


@contextmanager
def gappsd() -> GridAPPSD:
    gridappsd = GridAPPSD()
    LOGGER.info('Gridappsd connected')

    yield gridappsd

    gridappsd.disconnect()
    LOGGER.info('Gridappsd disconnected')


@pytest.mark.parametrize("sim_config_file, sim_result_file", [
    ("9500-timeseries-config.json", "9500-simulation.json")
    # ("123-config.json", "123-simulation.json"),
    # ("13-node-config.json", "13-node-sim.json"),
    # , ("t3-p1-config.json", "t3-p1.json"),
])
def test_timeseries_output(sim_config_file, sim_result_file):
    simulation_id = None
    sim_config_file = os.path.join(os.path.dirname(__file__), f"simulation_config_files/{sim_config_file}")
    sim_result_file = os.path.join(os.path.dirname(__file__), f"simulation_baseline_files/{sim_result_file}")
    # sim_test_config = os.path.join(os.path.dirname(__file__), f"simulation_baseline_files/{sim_test_file}")

    assert os.path.exists(sim_config_file), f"File {sim_config_file} must exist to run simulation test"
    # assert os.path.exists(sim_result_file), f"File {sim_result_file} must exist to run simulation test"

    with startup_containers():
        with gappsd() as gapps:
            os.makedirs("/tmp/output", exist_ok=True)
            with open("/tmp/output/simulation.json", 'w') as outfile:
                sim_complete = False
                rcvd_measurement = False

                def onmeasurement(sim, timestep, measurements):
                    nonlocal rcvd_measurement
                    # print(rcvd_measurement)
                    if not rcvd_measurement:
                        print(f"A measurement happened at {timestep}")
                        LOGGER.info('Measurement received at %s', timestep)
                        outfile.write(f"{timestep}|{json.dumps(measurements)}\n")

                starttime = int(time())
                with open(sim_config_file) as fp:
                    run_config = json.load(fp)
                    run_config["simulation_config"]["start_time"] = str(starttime)
                    print(run_config["simulation_config"]["start_time"])

                def onfinishsimulation(sim):
                    nonlocal sim_complete
                    sim_complete = True
                    LOGGER.info('Simulation Complete')

                sim = Simulation(gapps, run_config)
                sim.add_oncomplete_callback(onfinishsimulation)
                sim.add_onmesurement_callback(onmeasurement)
                sim.start_simulation()
                print("Starting sim")
                print(sim.simulation_id)

                with open("./simulation_config_files/weather_data.json", 'r') as g:
                    LOGGER.info('Querying weather data from timeseries')
                    a = gapps.get_response(t.TIMESERIES, json.load(g), timeout=30)
                    print(a)
                    #assert "Diffuse" in a, "Weather data query does not expected output"
                    LOGGER.info('Query failed')

                with open("./simulation_config_files/timeseries_query.json", 'r') as f:
                    query = json.load(f)
                    query["queryFilter"]["simulation_id"] = sim.simulation_id
                    print(query["queryFilter"]["simulation_id"])

                    LOGGER.info('Querying simulation data from timeseries')
                    q = gapps.get_response(t.TIMESERIES, query, timeout=30)
                    print(q)
                    assert "points" in q, "Time series query does not have expected output"
                    LOGGER.info('Simulation Query failed')

                while not sim_complete:
                    sleep(5)

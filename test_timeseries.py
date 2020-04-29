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
from gridappsd import GridAPPSD,topics as t
# tm: added for run_simulation workaround
from gridappsd.simulation import Simulation
from gridappsd_docker import docker_up, docker_down

# sys.path.append("/home/singha42/repos/gridappsd_alarms")
# from gridappsd_alarms import SimulationSubscriber
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


#def test_start_gridappsd():
#    with startup_containers():
#        g = GridAPPSD()
#        assert g.connected


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
                        outfile.write(f"{timestep}|{json.dumps(measurements)}\n")

                with open(sim_config_file) as fp:
                    run_config = json.load(fp)

                def onfinishsimulation(sim):
                    nonlocal sim_complete
                    sim_complete = True
                    print("Completed simulator")

                starttime = int(time())
                # tm: added to get the simulation to run.  Copied from run_simulation.py.  Need to figure out what Craig was trying to do with the run_simulation code.
                with open(sim_config_file) as fp:
                    run_config = json.load(fp)
                    run_config["simulation_config"]["start_time"] = str(starttime)
                    print(starttime)

                sim = Simulation(gapps, run_config)
                sim.add_oncomplete_callback(onfinishsimulation)
                sim.add_onmesurement_callback(onmeasurement)
                print("Starting sim")
                print(sim.simulation_id)

                with open("./simulation_config_files/timeseries_query.json", 'r') as f:
                    query = json.load(f)
                    query["queryFilter"]["simulation_id"] = sim.simulation_id
                    print(gapps.get_response(t.TIMESERIES, query, timeout=30))

                with open("./simulation_config_files/weather_data.json", 'r') as g:
                    print(gapps.get_response(t.TIMESERIES, json.load(g), timeout=30))

                sim.start_simulation()
                while not sim_complete:
                    sleep(5)


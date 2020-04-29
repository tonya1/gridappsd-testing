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

from gridappsd import GridAPPSD
# tm: added for run_simulation workaround
from gridappsd.simulation import Simulation
from gridappsd_docker import docker_up, docker_down


LOGGER = logging.getLogger(__name__)

@contextmanager
def startup_containers(spec=None):
    LOGGER.info('Starting gridappsd containers')
    docker_up(spec)
    LOGGER.info('Containers started')

    yield

    LOGGER.info('Stopping gridappsd containers')
    docker_down()
    LOGGER.info('Containers stopped')


@contextmanager
def gappsd() -> GridAPPSD:
    gridappsd = GridAPPSD()
    LOGGER.info('Gridappsd connected')

    yield gridappsd

    gridappsd.disconnect()
    LOGGER.info('Gridappsd disconnected')


def dictsAlmostEqual(file1, file2, rel_tol=1e-3):
    # file1 = "/home/singha42/repos/gridappsd-testing/simulation_baseline_files/123-simulation.output"
    #
    # file2 = "/tmp/output/simulation.output"
    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:
            # dict1 = [json.loads(line) for line in f1]
            # dict2 = [json.loads(line) for line in f2]
            dict1 = json.load(f1)
            dict2 = json.load(f2)

            if len(dict1) != len(dict2):
                return False
            # Loop through each item in the first dict and compare it to the second dict

            for y in dict1:
                m = dict1[y]
                # If it is a nested dictionary, need to call the function again
                if "magnitude" in m.keys():
                    for k in dict2:
                        n = dict2[k]
                        if not abs(m.get("magnitude") - n.get("magnitude") <= 1e-3):
                            return False
                elif "angle" in m.keys():
                    if not abs(m.get("angle") - n.get("angle")) <= 0.1:
                        return False
                elif "value" in m.keys():
                    if m.get("value") == n.get("value"):
                        return False

            return True


@pytest.mark.parametrize("sim_config_file, sim_result_file", [
    # ("9500-config.json", "9500-simulation.output")
    # ("123-config.json", "123-simulation.output"),
    ("13-node-config.json", "13-node-sim.output"),
    # , ("t3-p1-config.json", "t3-p1.output"),
])
def test_simulation_output(sim_config_file, sim_result_file):
    sim_config_file = os.path.join(os.path.dirname(__file__), f"simulation_config_files/{sim_config_file}")
    sim_result_file = os.path.join(os.path.dirname(__file__), f"simulation_baseline_files/{sim_result_file}")
    assert os.path.exists(sim_config_file), f"File {sim_config_file} must exist to run simulation test"
    # assert os.path.exists(sim_result_file), f"File {sim_result_file} must exist to run simulation test"

    with startup_containers():
        # Allow proven to come up
        sleep(30)
        with gappsd() as gapps:
            os.makedirs("/tmp/output", exist_ok=True)
            with open("/tmp/output/simulation.output", 'w') as outfile:
                LOGGER.info('Configuring simulation')
                sim_complete = False
                rcvd_measurement = False

                def onmeasurement(sim, timestep, measurements):
                    LOGGER.info('Measurement received at %s', timestep)
                    nonlocal rcvd_measurement
                    # print(rcvd_measurement)
                    if not rcvd_measurement:
                        print(f"A measurement happened at {timestep}")
                        #outfile.write(f"{timestep}|{json.dumps(measurements)}\n")
                        data = {}
                        data["data"] = measurements
                        outfile.write(json.dumps(data))
                        rcvd_measurement = True


                    print("Time is", int(time()))
                    print("Start time is ", starttime)

                    if int(time()) > starttime + 10:
                        sim.pause()
                        # print(sim.simulation_id)
                        LOGGER.info('Pausing simulation')

                    # if int(time()) > starttime + 15:
                    if timestep > starttime + 15:
                        sim.resume_pause_at(starttime + 20)
                        # print(sim.simulation_id)
                        LOGGER.info('Resuming simulation')

                    # if timestep == 1580420729:
                    #     sim.resume()
                    #     outfile.write("resuming")

                def onfinishsimulation(sim):
                    nonlocal sim_complete
                    sim_complete = True
                    LOGGER.info('Simulation Complete')
                
                LOGGER.info('Loading config')
                starttime = int(time())
                # tm: added to get the simulation to run.  Copied from run_simulation.py.  
                # tm: Need to figure out what Craig was trying to do with the run_simulation code.
                with open(sim_config_file) as fp:
                    LOGGER.info('Reading config')
                    run_config = json.load(fp)
                    run_config["simulation_config"]["start_time"] = str(starttime)
                    print(starttime)

                sim = Simulation(gapps, run_config)
                # sim = gapps.run_simulation(run_config)

                # tm: typo in add_onmesurement
                LOGGER.info('sim.add_onmesurement_callback')
                sim.add_onmesurement_callback(onmeasurement)
                LOGGER.info('sim.add_oncomplete_callback')
                sim.add_oncomplete_callback(onfinishsimulation)
                LOGGER.info('Starting sim')
                sim.start_simulation()

                while not sim_complete:
                    LOGGER.info('Sleeping')
                    sleep(5)

            assert dictsAlmostEqual(sim_result_file, "/tmp/output/simulation.output")

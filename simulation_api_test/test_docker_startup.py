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


def test_start_gridappsd():
    with startup_containers():
        g = GridAPPSD()
        assert g.connected


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
        with gappsd() as gapps:
            os.makedirs("/tmp/output", exist_ok=True)
            with open("/tmp/output/simulation.output", 'w') as outfile:
                sim_complete = False
                rcvd_measurement = False

                def onmeasurement(sim, timestep, measurements):
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
                        outfile.write("\n Pausing simulation")

                    # if int(time()) > starttime + 15:
                    if timestep > starttime + 15:
                        sim.resume_pause_at(starttime + 20)
                        # print(sim.simulation_id)
                        outfile.write("\n Resuming simulation")

                    # if timestep == 1580420729:
                    #     sim.resume()
                    #     outfile.write("resuming")

                def onfinishsimulation(sim):
                    nonlocal sim_complete
                    sim_complete = True
                    print("Completed simulator")

                print("Running config")
                starttime = int(time())
                # tm: added to get the simulation to run.  Copied from run_simulation.py.  Need to figure out what
                # Craig was trying to do with the run_simulation code.
                with open(sim_config_file) as fp:
                    run_config = json.load(fp)
                    run_config["simulation_config"]["start_time"] = str(starttime)
                    print(starttime)

                sim = Simulation(gapps, run_config)
                # sim = gapps.run_simulation(run_config)

                sim.add_onmesurement_callback(onmeasurement)
                sim.add_oncomplete_callback(onfinishsimulation)
                print("Starting sim")
                sim.start_simulation()

                while not sim_complete:
                    sleep(5)

            assert dictsAlmostEqual(sim_result_file, "/tmp/output/simulation.output")

from contextlib import contextmanager
import json
import logging
import os
from time import sleep
import sys

import pytest

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


def assert_files_are_equal(file1, file2):
    with open(file1) as f1:
        with open(file2) as f2:
            for line_f1 in f1.readline():
                line_f2 = f2.readline()
                assert line_f1 == line_f2


def test_start_gridappsd():
    with startup_containers():
        g = GridAPPSD()
        assert g.connected


@pytest.mark.parametrize("sim_config_file, sim_result_file", [
    ("t1-p1-config.json", "t1-p1.output")
    #, ("t2-p2-config.json", "t2-p1.output"),
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
            with open("/tmp/output/foo.output", 'w') as outfp:
                sim_complete = False

                def onmeasurement(sim, timestep, measurements):
                    print(f"A measurement happened at {timestep}")
                    outfp.write(f"{timestep}|{json.dumps(measurements)}\n")

                def onfinishsimulation(sim):
                    nonlocal sim_complete
                    sim_complete = True
                    print("Completed simulator")
                
                print("Running config")
                # tm: added to get the simulation to run.  Copied from run_simulation.py.  Need to figure out what Craig was trying to do with the run_simulation code.
                with open(sim_config_file) as fp:
                    run_config = json.load(fp)
                sim = Simulation(gapps, run_config)
                #sim = gapps.run_simulation(run_config)

                # tm: typo in add_onmesurement
                sim.add_onmesurement_callback(onmeasurement)
                sim.add_oncomplete_callback(onfinishsimulation)
                print("Starting sim")
                sim.start_simulation()

                while not sim_complete:
                    sleep(5)

            assert_files_are_equal(sim_result_file, "/tmp/output/foo.output")

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

POWERGRID_MODEL = 'powergridmodel'

database_type = POWERGRID_MODEL

request_topic = '.'.join((t.REQUEST_DATA, database_type))

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


def test_start_gridappsd():
    with startup_containers():
        g = GridAPPSD()
        assert g.connected


def model_files_are_equal(file1, file2):
    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:

            dict1 = json.load(f1)
            # print(dict1)
            dict2 = json.load(f2)

            # print(dict2)
            if len(dict1) != len(dict2):
                return False
            for y in dict1:
                m = dict1[y]
                for k in dict2:
                    n = dict2[k]
                    if "modelNames" in m.keys():
                        if m.get("modelNames") == n.get("modelNames"):
                            print("both same")
                            return False
            return True


def object_files_are_equal(file1, file2):

    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:

            dict1 = json.load(f1)
            # print(dict1)
            dict2 = json.load(f2)

            # print(dict2)
            if len(dict1) != len(dict2):
                return False
            for y in dict1:
                m = dict1[y]
                for k in dict2:
                    n = dict2[k]
                    if "results" in m.keys():
                        if m.get("bindings") == n.get("bindings"):
                            print(" objects both same")
                            return False
            return True


def object_types_are_equal(file1, file2):

    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:

            dict1 = json.load(f1)
            # print(dict1)
            dict2 = json.load(f2)

            # print(dict2)
            if len(dict1) != len(dict2):
                return False
            for y in dict1:
                m = dict1[y]
                for k in dict2:
                    n = dict2[k]
                    if "objectTypes" in m.keys():
                        if m.get("objectTypes") == n.get("objectTypes"):
                            print("both objects types are  same")
                            return False
            return True


def models_are_equal(file1, file2):

    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:

            dict1 = json.load(f1)
            # print(dict1)
            dict2 = json.load(f2)

            # print(dict2)
            if len(dict1) != len(dict2):
                return False
            for y in dict1:
                m = dict1[y]
                for k in dict2:
                    n = dict2[k]
                    if "models" in m.keys():
                        if m.get("models") == n.get("models"):
                            print("Models data is  same")
                            return False
            return True


def query_data_equal(file1, file2):

    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:

            dict1 = json.load(f1)
            # print(dict1)
            dict2 = json.load(f2)

            # print(dict2)
            if len(dict1) != len(dict2):
                return False
            for y in dict1:
                m = dict1[y]
                for k in dict2:
                    n = dict2[k]
                    if "results" in m.keys():
                        if m.get("bindings") == n.get("bindings"):
                            print("Query data are  same")
                            return False
            return True


@pytest.mark.parametrize("sim_config_file, sim_result_file", [
    ("9500-config.json", "9500-simulation.json")
    # ("123-config.json", "123-simulation.json"),
    # ("13-node-config.json", "13-node-sim.json"),
    # , ("t3-p1-config.json", "t3-p1.json"),
])
def test_simulation_output(sim_config_file, sim_result_file):
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

                with open("/tmp/output/power.json", 'w') as f:
                    r = gapps.query_model_names(model_id=None)
                    f.write(json.dumps(r, indent=4, sort_keys=True))

                with open("/tmp/output/power2.json", 'w') as f:
                    obj = '_0f6f3735-b297-46aa-8861-547d3cd0dee9'
                    r2 = gapps.query_object(obj, model_id=None)
                    f.write(json.dumps(r2, indent=4, sort_keys=True))

                with open("/tmp/output/power3.json", 'w') as f:
                    r3 = gapps.query_object_types(model_id=None)
                    f.write(json.dumps(r3, indent=4, sort_keys=True))

                with open("/tmp/output/power4.json", 'w') as f:
                    r4 = gapps.query_model_info()
                    f.write(json.dumps(r4, indent=4, sort_keys=True))

                with open("/tmp/output/power5.json", 'w') as f:
                    query = "select ?feeder_name ?subregion_name ?region_name WHERE {?line r:type c:Feeder.?line c:IdentifiedObject.name  ?feeder_name.?line c:Feeder.NormalEnergizingSubstation ?substation.?substation r:type c:Substation.?substation c:Substation.Region ?subregion.?subregion  c:IdentifiedObject.name  ?subregion_name .?subregion c:SubGeographicalRegion.Region  ?region . ?region   c:IdentifiedObject.name  ?region_name}"
                    r5 = gapps.query_data(query, database_type=POWERGRID_MODEL, timeout=30)
                    f.write(json.dumps(r5, indent=4, sort_keys=True))

                sim.start_simulation()
                while not sim_complete:
                    sleep(5)

            model_files_are_equal(sim_result_file, '/tmp/output/power.json')
            object_files_are_equal('/tmp/output/power2.json', './simulation_baseline_files/9500-query2.json')
            object_types_are_equal('/tmp/output/power3.json', './simulation_baseline_files/9500-query3.json')
            models_are_equal('/tmp/output/power4.json', './simulation_baseline_files/9500-query4.json')
            query_data_equal('/tmp/output/power5.json', './simulation_baseline_files/9500-query5.json')
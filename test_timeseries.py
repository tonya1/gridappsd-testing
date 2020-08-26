import ast
from contextlib import contextmanager
import json
import logging
import os
from time import sleep, time
import sys
import pytest
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
    # docker_down()
    # LOGGER.info('Containers stopped')


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
                        # print(f"A measurement happened at {timestep}")
                        LOGGER.info('Measurement received at %s', timestep)
                        outfile.write(f"{timestep}|{json.dumps(measurements)}\n")

                with open(sim_config_file) as fp:
                    run_config = json.load(fp)
                    starttime = run_config["simulation_config"]["start_time"]
                    # run_config["simulation_config"]["start_time"] = str(starttime)
                    print(run_config["simulation_config"]["start_time"])

                def onfinishsimulation(sim):
                    nonlocal sim_complete
                    sim_complete = True
                    LOGGER.info('Simulation Complete')

                sim = Simulation(gapps, run_config)
                sim.add_oncomplete_callback(onfinishsimulation)
                sim.add_onmesurement_callback(onmeasurement)
                sim.start_simulation()
                LOGGER.info("Starting simulation")
                print(sim.simulation_id)

                with open("./simulation_config_files/weather_data.json", 'r') as g:
                    LOGGER.info('Querying weather data from timeseries')
                    query1 = json.load(g)

                    a = gapps.get_response(t.TIMESERIES, query1, timeout=60)
                    LOGGER.info('Weather data received ')
                    assert "Diffuse" in a["data"][0], "Weather data query does not have expected output"
                    LOGGER.info('Weather data query has expected output')

                while not sim_complete:
                    sleep(5)

            with open("./simulation_config_files/timeseries_query.json", 'r') as f:
                query2 = json.load(f)
                query2["queryFilter"]["simulation_id"] = sim.simulation_id
                LOGGER.info('Querying simulation data from timeseries')
                q = gapps.get_response(t.TIMESERIES, query2, timeout=300)
                LOGGER.info('Simulation data received for Timeseries API')
                file2 = open("./out-input.txt", 'w')
                file2.write(json.dumps(q))
                assert "hasSimulationMessageType" in q["data"][0], "Simulation data query does not have expected output"
                LOGGER.info('Simulation data query has expected output')

            with open("./simulation_config_files/sensor_query.json", 'r') as file:
                sensor_query = json.load(file)
                sensor_query["queryFilter"]["simulation_id"] = sim.simulation_id
                LOGGER.info('Querying GridAPPS-D sensor simulator data from timeseries')
                result = gapps.get_response(t.TIMESERIES, sensor_query, timeout=300)
                assert "hasSimulationMessageType" in result["data"][0], "Sensor simulator data does not have expected output"
                LOGGER.info('Query response received for  GridAPPS-D sensor simulator data from timeseries')

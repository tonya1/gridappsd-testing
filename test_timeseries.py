import ast
from contextlib import contextmanager
import json
import logging
import os
from time import sleep, time
import sys
import pytest

from gridappsd import GridAPPSD
from gridappsd.simulation import Simulation
from gridappsd_docker import docker_up, docker_down
from gridappsd import GridAPPSD, topics as t

LOGGER = logging.getLogger(__name__)

result_weather_data = []
result_timeseries_query = []
result_sensor_query = []

@pytest.mark.parametrize("sim_config_file, sim_result_file", [
    ("9500-timeseries-config.json", "9500-simulation.json")
    # ("123-config.json", "123-simulation.json"),
    # ("13-node-config.json", "13-node-sim.json"),
    # , ("t3-p1-config.json", "t3-p1.json"),
])
def test_timeseries_output(gridappsd_client, sim_config_file, sim_result_file):
    global result_weather_data
    global result_timeseries_query
    global result_sensor_query
    simulation_id = None
    sim_config_file = os.path.join(os.path.dirname(__file__), f"simulation_config_files/{sim_config_file}")
    sim_result_file = os.path.join(os.path.dirname(__file__), f"simulation_baseline_files/{sim_result_file}")

    assert os.path.exists(sim_config_file), f"File {sim_config_file} must exist to run simulation test"

    gapps = gridappsd_client
    sim_complete = False
    rcvd_measurement = False

    def onmeasurement(sim, timestep, measurements):
        LOGGER.info('Measurement received at %s', timestep)

    def onfinishsimulation(sim):
        nonlocal sim_complete
        sim_complete = True
        LOGGER.info('Simulation Complete')

    with open(sim_config_file) as fp:
        LOGGER.info('Loading config')
        run_config = json.load(fp)
        LOGGER.info(f'Simulation start time {run_config["simulation_config"]["start_time"]}')

    LOGGER.info('Starting the simulation')
    sim = Simulation(gapps, run_config)
    sim.start_simulation()
    LOGGER.info(f'Simulation id {sim.simulation_id}')

    LOGGER.info('sim.add_oncomplete_callback')
    sim.add_oncomplete_callback(onfinishsimulation)

    LOGGER.info('sim.add_onmeasurement_callback')
    sim.add_onmesurement_callback(onmeasurement)

    with open("./simulation_config_files/weather_data.json", 'r') as g:
        LOGGER.info('Querying weather data from timeseries')
        query1 = json.load(g)
        result_weather_data = gapps.get_response(t.TIMESERIES, query1, timeout=60)
        LOGGER.info('Weather data received ')

    while not sim_complete:
        LOGGER.info('Sleeping')
        sleep(5)
    else:
        with open("./simulation_config_files/timeseries_query.json", 'r') as f:
            query2 = json.load(f)
            query2["queryFilter"]["simulation_id"] = sim.simulation_id
            LOGGER.info('Querying simulation data from timeseries')
            result_timeseries_query = gapps.get_response(t.TIMESERIES, query2, timeout=300)
            LOGGER.info('Simulation data received for Timeseries API')
    
        with open("./simulation_config_files/sensor_query.json", 'r') as file:
            sensor_query = json.load(file)
            sensor_query["queryFilter"]["simulation_id"] = sim.simulation_id
            LOGGER.info('Querying GridAPPS-D sensor simulator data from timeseries')
            result_sensor_query = gapps.get_response(t.TIMESERIES, sensor_query, timeout=300)
            LOGGER.info('Simulation data received for sensor simulator')

def test_weather_api():
    global result_weather_data
    assert "Diffuse" in result_weather_data["data"][0], \
        "Weather data query does not have expected output"
    LOGGER.info('Weather data query has expected output')

def test_timeseries_simulation_api():
    global result_timeseries_query
    assert "hasSimulationMessageType" in result_timeseries_query["data"][0], \
        "Simulation data query does not have expected output"
    LOGGER.info('Simulation data query has expected output')

def test_sensor_simulator_api():
    global result_sensor_query
    assert "hasSimulationMessageType" in result_sensor_query["data"][0], \
        "Sensor simulator data does not have expected output"
    LOGGER.info('Query response received for  GridAPPS-D sensor simulator data from timeseries')

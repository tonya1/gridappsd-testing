from contextlib import contextmanager
import json
import logging
import os
from time import sleep
import pytest

from gridappsd import GridAPPSD
from gridappsd import GridAPPSD,topics as t
from gridappsd.simulation import Simulation
from gridappsd_docker import docker_up, docker_down

LOGGER = logging.getLogger(__name__)

POWERGRID_MODEL = 'powergridmodel'
database_type = POWERGRID_MODEL
request_topic = '.'.join((t.REQUEST_DATA, database_type))

def model_files_are_equal(file1, file2):
    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:

            dict1 = json.load(f1)
            dict2 = json.load(f2)

            if len(dict1) != len(dict2):
                return False

            if dict1['data']['modelNames'] != dict2['data']['modelNames']:
                if len(dict1['data']['modelNames']) == 0:
                    return False
                for key in dict1['data']['modelNames']:
                    if key not in dict2['data']['modelNames']:
                        return False


    return True


def object_files_are_equal(file1, file2):

    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:

            dict1 = json.load(f1)
            dict2 = json.load(f2)

            if len(dict1) != len(dict2):
                return False

            if dict1['data']['results']['bindings'] != dict2['data']['results']['bindings']:
                if len(dict1['data']['results']['bindings']) == 0:
                    return False
                for key in dict1['data']['results']['bindings']:
                    if key not in dict2['data']['results']['bindings']:
                        return False


    return True


def object_types_are_equal(file1, file2):

    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:

            dict1 = json.load(f1)
            dict2 = json.load(f2)

            if len(dict1) != len(dict2):
                return False

            if dict1['data']['objectTypes'] != dict2['data']['objectTypes']:
                if len(dict1['data']['objectTypes']) == 0:
                    return False
                for key in dict1['data']['objectTypes']:
                    if key not in dict2['data']['objectTypes']:
                        return False

    return True


def models_are_equal(file1, file2):

    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:

            dict1 = json.load(f1)
            dict2 = json.load(f2)

            if len(dict1) != len(dict2):
                return False

            if dict1['data']['models'] != dict2['data']['models']:
                if len(dict1['data']['models']) == 0:
                    return False
                for key in dict1['data']['models']:
                    if key not in dict2['data']['models']:
                        return False

    return True


def query_data_equal(file1, file2):

    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:

            dict1 = json.load(f1)
            dict2 = json.load(f2)

            if len(dict1) != len(dict2):
                return False

            if dict1['data']['results']['bindings'] != dict2['data']['results']['bindings']:
                if len(dict1['data']['results']['bindings']) == 0:
                    return False
                for key in dict1['data']['results']['bindings']:
                    if key not in dict2['data']['results']['bindings']:
                        return False

    return True


def test_power_model_names(gridappsd_client):
    gapps = gridappsd_client
    # Allow blazegraph to come up
    sleep(30)
    os.makedirs("/tmp/output", exist_ok=True)
    LOGGER.info('Performing model name query')
    with open("/tmp/output/power.json", 'w') as f:
        r = gapps.query_model_names(model_id=None)
        f.write(json.dumps(r, indent=4, sort_keys=True))

    LOGGER.info('Performing object query')
    with open("/tmp/output/power2.json", 'w') as f:
        obj = '_46EA069B-F08C-4945-9C08-8F7CABECCF5C'
        r2 = gapps.query_object(obj, model_id=None)
        f.write(json.dumps(r2, indent=4, sort_keys=True))

    LOGGER.info('Performing object type query')
    with open("/tmp/output/power3.json", 'w') as f:
        r3 = gapps.query_object_types(model_id=None)
        f.write(json.dumps(r3, indent=4, sort_keys=True))

    LOGGER.info('Performing model info query')
    with open("/tmp/output/power4.json", 'w') as f:
        r4 = gapps.query_model_info()
        f.write(json.dumps(r4, indent=4, sort_keys=True))

    LOGGER.info('Performing model data query')
    with open("/tmp/output/power5.json", 'w') as f:
        query = "select ?feeder_name ?subregion_name ?region_name WHERE {?line r:type c:Feeder.?line c:IdentifiedObject.name  ?feeder_name.?line c:Feeder.NormalEnergizingSubstation ?substation.?substation r:type c:Substation.?substation c:Substation.Region ?subregion.?subregion  c:IdentifiedObject.name  ?subregion_name .?subregion c:SubGeographicalRegion.Region  ?region . ?region   c:IdentifiedObject.name  ?region_name}"
        r5 = gapps.query_data(query, database_type=POWERGRID_MODEL, timeout=30)
        f.write(json.dumps(r5, indent=4, sort_keys=True))
    assert model_files_are_equal('/tmp/output/power.json', './simulation_baseline_files/power_api_models.json'), 'Powergrid API model name differs'


def test_power_object():
    assert object_files_are_equal('/tmp/output/power2.json', './simulation_baseline_files/9500-query2.json'), 'Powergrid API objects differ'

def test_power_object_type():
    assert object_types_are_equal('/tmp/output/power3.json', './simulation_baseline_files/9500-query3.json'), 'Powergrid API object types differ'

def test_power_query_model_info():
    assert models_are_equal('/tmp/output/power4.json', './simulation_baseline_files/9500-query4.json'), 'Powergrid API query model info differs'

def test_power_query_data():
    assert query_data_equal('/tmp/output/power5.json', './simulation_baseline_files/9500-query5.json'), 'Powergrid API quer data differs'

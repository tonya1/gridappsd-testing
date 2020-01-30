from contextlib import contextmanager

import pytest
from gridappsd import GridAPPSD

import gridappsd_docker
from gridappsd_docker import docker_up, docker_down


@contextmanager
def startup_containers(spec=None):
    docker_up(spec)

    yield

    docker_down()


def assert_files_are_equal(file1, file2):
    with open(file1) as f1:
        with open(file2) as f2:
            for line_f1 in f1.readline():
                line_f2 = f2.readline()
                assert line_f1 == line_f2


# def test_start_gridappsd():
#     g = GridAPPSD()
#     assert g.connected


@pytest.mark.parametrize("sim_config_file, sim_result_file", [
    ("t1-p1-config.json", "t1-p1.output")
    , ("t2-p2-config.json", "t2-p1.output"),
    # , ("t3-p1-config.json", "t3-p1.output"),
])
def test_simulation_output(sim_config_file, sim_result_file):

    with startup_containers():
        print("Doing all the sim stuff and then comparing output")

    #
    # with startup_containers():
    #     print(f"Running sim for {sim_config_file} with output in {sim_result_file}")

    #assert_files_are_equal(sim_result_file, new_sim_out_file)
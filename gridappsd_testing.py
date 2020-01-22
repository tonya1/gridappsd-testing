#!/usr/bin/env python3

import docker
import os
import shutil
import time
import urllib.request

gridappsd_docker = { 
  'influxdb': {
    'start': True,
    'image': 'gridappsd/influxdb:develop',
    'pull': True,
    'ports': {'8086/tcp': 8086},
    'environment': {"INFLUXDB_DB": "proven"},
    'links': '',
    'volumes': '',
    'entrypoint': '',
  }, 
  'redis': {
    'start': True,
    'image': 'redis:3.2.11-alpine',
    'pull': True,
    'ports': {'6379/tcp': 6379},
    'environment': [],
    'links': '',
    'volumes': {
       '/data/docker/gridappsd_testing/gridappsd/redis/data': {'bind': '/data', 'mode': 'rw'}
     },
    'entrypoint': 'redis-server -appendonly yes',
  },
  'blazegraph': {
    'start': True,
    'image': 'gridappsd/blazegraph:develop',
    'pull': True,
    'ports': {'8080/tcp': 8889},
    'environment': [],
    'links': '',
    'volumes': '',
    'entrypoint': '',
  },
  'mysql': {
    'start': True,
    'image': 'mysql/mysql-server:5.7',
    'pull': True,
    'ports': {'3306/tcp': 3306},
    'environment': {
       "MYSQL_RANDOM_ROOT_PASSWORD": "yes",
       "MYSQL_PORT": '3306'
    },
    'links': '',
    'volumes': {
       '/data/docker/gridappsd_testing/gridappsd/mysql': {'bind': '/var/lib/mysql', 'mode': 'rw'},
       '/data/docker/gridappsd_testing/dumps/gridappsdmysql_dump.sql': {'bind': '/docker-entrypoint-initdb.d/schema.sql', 'mode': 'ro'}
    },
    'entrypoint': '',
  },
  'proven': {
    'start': True,
    'image': 'gridappsd/proven:develop',
    'pull': True,
    'ports': {'8080/tcp': 18080},
    'environment': {
      "PROVEN_SERVICES_PORT": "18080", 
      "PROVEN_SWAGGER_HOST_PORT": "localhost:18080", 
      "PROVEN_USE_IDB": "true", 
      "PROVEN_IDB_URL": "http://influxdb:8086", 
      "PROVEN_IDB_DB": "proven",
      "PROVEN_IDB_RP": "autogen",
      "PROVEN_IDB_USERNAME": "root",
      "PROVEN_IDB_PASSWORD": "root",
      "PROVEN_T3DIR":"/proven"},
    'links': '',
    'volumes': '',
    'entrypoint': '',
  },
  'gridappsd': {
    'start': True,
    'image': 'gridappsd/gridappsd:develop',
    'pull': True,
    'ports': {'61613/tcp': 61613, '61614/tcp': 61614, '61616/tcp': 61616},
    'environment': {
      "PATH": "/gridappsd/bin:/gridappsd/lib:/gridappsd/services/fncsgossbridge/service:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin", 
      "DEBUG": 1,
      "START": 1
    },
    'links': {'mysql': 'mysql'},
    'volumes': {
       '/data/gridappsd_testing/entrypoint.sh': {'bind': '/gridappsd/entrypoint.sh', 'mode': 'rw'}
    },
    'entrypoint': '',
  },
  'viz': {
    'start': True,
    'image': 'gridappsd/viz:develop',
    'pull': True,
    'ports': {'8082/tcp': 8080},
    'environment': '',
    'links': '',
    'volumes': '',
    'entrypoint': '',
  }
}

client = docker.from_env()

# Stop all containers
print ("\nStopping all containers")
for container in client.containers.list():
  container.stop()  
  time.sleep(5)

print ("\nRemoving previous data")
path='/data/docker/gridappsd_testing/gridappsd'
if os.path.isdir(path): 
  shutil.rmtree(path, ignore_errors=False, onerror=None)

# Downlaod mysql file
print ("\nDownloading mysql file")
if not os.path.isdir("/data/docker/gridappsd_testing/dumps"): 
  os.makedirs('/data/docker/gridappsd_testing/dumps', 0o0775 )
urllib.request.urlretrieve('https://raw.githubusercontent.com/GRIDAPPSD/Bootstrap/master/gridappsd_mysql_dump.sql', filename='/data/docker/gridappsd_testing/dumps/gridappsd_mysql_dump.sql')

# Pull the container
print ("\n")
for service, value in gridappsd_docker.items():
  if gridappsd_docker[service]['pull']:
    print ("Pulling %s : %s" % ( service, gridappsd_docker[service]['image']))
    image = client.images.pull(gridappsd_docker[service]['image'])

# Start the container
print ("\n")
for service, value in gridappsd_docker.items():
  if gridappsd_docker[service]['start']:
    print ("Starting %s : %s" % ( service, gridappsd_docker[service]['image']))
    kwargs = {} 
    kwargs['image'] = gridappsd_docker[service]['image']
    # Only name the containers if remove is on
    kwargs['remove'] = True
    kwargs['name'] = service
    kwargs['detach'] = True
    if gridappsd_docker[service]['environment']:   
      kwargs['environment'] = gridappsd_docker[service]['environment']
    if gridappsd_docker[service]['ports']:   
      kwargs['ports'] = gridappsd_docker[service]['ports']
    if gridappsd_docker[service]['volumes']:   
      kwargs['volumes'] = gridappsd_docker[service]['volumes']
    if gridappsd_docker[service]['entrypoint']:   
      kwargs['entrypoint'] = gridappsd_docker[service]['entrypoint']
    if gridappsd_docker[service]['links']:
      kwargs['links'] = gridappsd_docker[service]['links']
    print (kwargs)
    container = client.containers.run(**kwargs)
    gridappsd_docker[service]['containerid'] = container.id

time.sleep(30)

# List all running containers
print("\n")
print ("\n\nList all containers")
for container in client.containers.list():
  print (container.name)


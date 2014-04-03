#! /bin/bash
source virtualenv/bin/activate
python osm-rejoin-ways.py -d gis -w 'highway IS NOT NULL'

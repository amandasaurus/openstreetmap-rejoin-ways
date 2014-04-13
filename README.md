opensteetmap-rejoin-ways
========================

Motivation
----------

Roads in OpenStreetMap are stored as ways. One single road may be broken up into many ways for various reasons. If a speed limit changes, that road needs to split into 2 ways. If there's a no-right-turn restriction, then you need to split the road. If a bus route turns off, you need to split.

However if you want to do analysis of the road geometry, you don't care about turn restrictions. The splitting of roads makes it seem like there are more roads then there actually are.

This programme will rejoin 

Usage
-----

1. First import the data with osm2pgsql

Copyright & Licence
-------------------

Copyright 2014 Rory McCann <rory@technomancy.org>, licenced under GNU General Public Licence version 3 (or at your option a later version). See the file LICENCE for more. Code is hosted on github: https://github.com/rory/openstreetmap-rejoin-ways Patches / forks / pull requests welcome!

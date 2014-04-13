opensteetmap-rejoin-ways
========================

Motivation
----------

Roads in [OpenStreetMap]() are stored as [ways](). One single road may be broken up into many ways. If a speed limit changes, that road needs to split into 2 ways (for different [``maxspeed``]() tags). If there's a [no-right-turn restriction](), then you need to split the road. If a [bus route]() turns off, you need to split.

However if you want to do analysis of the road geometry, you don't care about turn restrictions. The splitting of roads makes it seem like there are more roads then there actually are, and it would be better to undo this splitting.

This programme will do that rejoining of ways, in effect undoing the splitting of ways.

How should we merge ways together? A good approach is the [``ref`` tag], which is used for the road reference. It's usually assigned locally by local authorities. If you have 3 ways joining together in a Y shape, with the bottom and top right way sharing the same ``ref`` and the top left having a different ``ref``, then it's quite likely that those 2 ways represent what the common person on the ground would call the same road. If there are no ``ref`` tags, but 2 ways touch and share the ``name``, then it's likely they are the same 'road'. Likewise if 2 ways touch and there is no ``ref`` or ``name``, but they share the same ``highway`` tag then they probably are the same road.

This is the default behaviour of ``osm-rejoin-ways`` is to rejoin ways based on these tags but the tags can be overridden.

Installation
------------

    pip install openstreetmap-rejoin-ways

Usage
-----

1. First import the data with osm2pgsql

1. 

Configuration & options
-----------------------



Copyright & Licence
-------------------

Copyright 2014 Rory McCann <rory@technomancy.org>, licenced under GNU General Public Licence version 3 (or at your option a later version). See the file LICENCE for more. Code is hosted on github: https://github.com/rory/openstreetmap-rejoin-ways Patches / forks / pull requests welcome!

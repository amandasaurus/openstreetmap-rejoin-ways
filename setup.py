from setuptools import setup

setup(
    name="openstreemap-rejoin-ways",
    version="0.1",
    author="Rory McCann",
    author_email="rory@technomancy.org",
    py_modules=['osm-rejoin-ways'],
    platforms=['any',],
    requires=[],
    license="GPLv3+",
    entry_points={
        'console_scripts': [
            'osm-rejoin-ways = osm-rejoin-ways:main',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Environment :: Console',
    ],
)

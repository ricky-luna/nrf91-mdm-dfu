import sys
from setuptools import find_packages, setup
from nrf9160_mdm_dfu.api.nrf_dfu_API import PACKAGE_VERSION

if len(sys.argv) == 3:
    package_tags = sys.argv.pop(2)
else:
    package_tags = '{0}+dev'.format(PACKAGE_VERSION)

PACKAGE_DATA = {
    'nrf9160_mdm_dfu': []
}

REQUIREMENTS = [
    'pynrfjprog>=9.8.1',
    'intelhex>=2.2.1'
]

setup(
    name='nrf9160_mdm_dfu',  # TODO: Package name should be probably changed?
    version=package_tags,
    description='A python interface for using dfu commands towards nrf9160 devices.',
    long_description='A python interface for using dfu commands towards nrf9160 devices.',
    author='Nordic Semiconductor',
    author_email='per.arne.ronning@nordicsemi.no',
    license='Nordic Internal',
    url='https://projecttools.nordicsemi.no/bitbucket/projects/SAT/repos/nrf-dfu-tool',  # TODO: Update
    classifiers=[
        'Development Status :: 4 - Beta',  # TODO: Update development status, audience etc.
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Software Development :: Quality Assurance',
        'License :: Other/Proprietary License',
        'Operating System :: Posix :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 34',
        'Programming Language :: Python :: 35',
        'Programming Language :: Python :: 36',
    ],
    packages=find_packages(),
    package_data=PACKAGE_DATA,

    install_requires=REQUIREMENTS,

    entry_points={
        'console_scripts': [
            '{0} = nrf9160_mdm_dfu.bin.nrf9160_mdm_dfu:main'.format("nrf9160_mdm_dfu"),
        ]
    }, )

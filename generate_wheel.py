import os
import argparse

GEN_PACKAGE_CMD = "python setup.py bdist_wheel "
from nrf9160_mdm_dfu.api.nrf_dfu_API import PACKAGE_VERSION


def main():
    """Parse command line arguments and generate wheel package.

    """
    desc = '''Generate wheel package'''
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("--version_number", "-v",
                        help="Add release version number to package name",
                        default=PACKAGE_VERSION,
                        required=False)
    parser.add_argument("--build_number", "-b",
                        help="Add build number to package name",
                        default='dev',
                        required=False)
    parser.add_argument("--git_hash", "-g",
                        help="Add git hash to package name",
                        required=False)
    args = parser.parse_args()

    generate_wheel(args.version_number,
                   args.build_number,
                   args.git_hash)


def generate_wheel(version=PACKAGE_VERSION, build_number=None, git_hash=None):
    """Generate wheel package.

    Creates a Python Wheel package.
    The wheel package follows the PEP 0427 naming convention, which gives
    this package name format:

    product-{version}+{build_number}.{git_hash}-py34-none-any.py.whl

    NOTE! Newer versions of setuptools, pip, and PyPI require that format
    Older version might create:
    product-{version}_{build_number}.{git_hash}-py34-none-any.py.whl
    eventhough '+' is added.

    Args:
    version [str]       : The product release version to be added
                           to the wheel package name.
    build_number [str]  : The build number to be added
                           to the wheel package name.
    git_hash[str]       : The 7 digit Git hash to be added
                           to the wheel package name.
    """
    cmd = "{0}{1}".format(GEN_PACKAGE_CMD, version)
    if build_number:
        cmd += "+" + build_number
    if git_hash:
        cmd += "." + git_hash[:7]

    os.system(cmd)


if __name__ == "__main__":
    main()

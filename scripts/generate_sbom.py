"""
Generates a Software Bill of Materials (SBOM) for the project.
"""

import os
import cyclonedx.model.component
from cyclonedx.model.bom import Bom
from cyclonedx.output import make_outputter

def generate_sbom():
    """
    Generates an SBOM for the project.
    """
    # Get a list of installed packages
    installed_packages = os.popen('pip freeze').read().split('\n')

    # Create a list of CycloneDX components
    components = []
    for package in installed_packages:
        if '==' in package:
            name, version = package.split('==')
            components.append(
                cyclonedx.model.component.Component(
                    name=name,
                    version=version,
                )
            )

    # Create a BOM
    bom = Bom(components=components)

    # Output the BOM to a file
    outputter = make_outputter(bom, output_format='json')
    with open('sbom.json', 'w') as f:
        f.write(outputter.output_as_string())

if __name__ == "__main__":
    generate_sbom()


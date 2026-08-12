from setuptools import setup

package_name = 'flight_control'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='drone-sim',
    maintainer_email='vous@exemple.com',
    description='Manette -> RC override ArduPilot',
    license='MIT',
    entry_points={
        'console_scripts': [
            'flight_control_node = flight_control.flight_control_node:main',
        ],
    },
)

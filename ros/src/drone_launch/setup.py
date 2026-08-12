import os
from setuptools import setup

package_name = 'drone_launch'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), ['launch/drone.launch.py', 'launch/stack.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='drone-sim',
    maintainer_email='rgasore@virunga.org',
    description='Lancement de la stack ROS2 (MAVROS + nodes)',
    license='MIT',
)

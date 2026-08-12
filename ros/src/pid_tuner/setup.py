from setuptools import setup

package_name = 'pid_tuner'

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
    description='Réglage PID ArduPilot via paramètres ROS2',
    license='MIT',
    entry_points={
        'console_scripts': [
            'pid_tuner_node = pid_tuner.pid_tuner_node:main',
        ],
    },
)

from setuptools import setup

package_name = 'joy_bridge'

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
    description='Bridge UDP (RC-N1) -> sensor_msgs/Joy',
    license='MIT',
    entry_points={
        'console_scripts': [
            'joy_bridge_node = joy_bridge.joy_bridge_node:main',
        ],
    },
)

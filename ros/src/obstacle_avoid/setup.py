from setuptools import setup

package_name = 'obstacle_avoid'

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
    description="Évitement d'obstacles simple (exemple pédagogique)",
    license='MIT',
    entry_points={
        'console_scripts': [
            'obstacle_avoid_node = obstacle_avoid.obstacle_avoid_node:main',
        ],
    },
)

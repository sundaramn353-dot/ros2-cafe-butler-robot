import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'cafe_robot'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # ament index registration
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        # package manifest
        ('share/' + package_name, ['package.xml']),
        # launch files
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        # config / parameter files
        (os.path.join('share', package_name, 'config'),
            glob(os.path.join('config', '*.yaml'))),
        # world files (Gazebo SDF)
        (os.path.join('share', package_name, 'worlds'),
            glob(os.path.join('worlds', '*.sdf'))),
        # map files (Nav2 YAML + PGM)
        (os.path.join('share', package_name, 'maps'),
            glob(os.path.join('maps', '*.*'))),
        # RViz config files
        (os.path.join('share', package_name, 'rviz'),
            glob(os.path.join('rviz', '*.rviz'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='sundar',
    maintainer_email='sundar@todo.todo',
    description='Autonomous French café butler robot with Nav2 and Gazebo Harmonic.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'cafe_robot_node = cafe_robot.cafe_robot_node:main',
            'cafe_goal_navigator = cafe_robot.cafe_goal_navigator:main',
            'cancel_order = cafe_robot.cancel_order:main',
            'cafe_operator_node = cafe_robot.cafe_operator_node:main',
        ],
    },
)

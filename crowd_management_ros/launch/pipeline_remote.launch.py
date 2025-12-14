import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    ld = LaunchDescription()
    
    dr_spaam_remote = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('detectors_ros'), 'launch'),
            '/dr_spaam_ros_remote.launch.py'])
    )

    yolo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('detectors_ros'), 'launch'),
            '/yolo.launch.py'])
    )
        
    tracker = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('tracker_ros'), 'launch'),
            '/tracker_ros.launch.py'])     
    )
          
    detect_following=Node(
        package = 'crowd_management_ros',
        executable = 'detect_following'
    )

    ld.add_action(dr_spaam_remote)
    ld.add_action(yolo)
    ld.add_action(tracker)
    ld.add_action(detect_following)
    
    return ld


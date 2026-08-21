import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess

def generate_launch_description():
    # --- CONFIGURATION ---
    # Path to the URDF file inside the Docker container
    urdf_file_path = '/app/urdf/worx_mower.urdf'
    
    # Read the URDF file into a string
    with open(urdf_file_path, 'r') as infp:
        robot_desc = infp.read()

    return LaunchDescription([
        # 1. Start the Robot State Publisher
        # This node takes your URDF XML and constantly broadcasts the physical dimensions
        # to the ROS 2 'tf2' network, so Nav2 knows exactly where the camera is.
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_desc}]
        ),
        
        # 2. Start the Stereo Vision & AI Node
        # We use ExecuteProcess because stereo_node.py is a standalone python script in /app
        ExecuteProcess(
            cmd=['python3', '/app/stereo_node.py'],
            output='screen'
        )
    ])

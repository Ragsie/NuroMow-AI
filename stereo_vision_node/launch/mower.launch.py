import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown

def generate_launch_description():
    # --- CONFIGURATION ---
    urdf_file_path = '/app/urdf/worx_mower.urdf'
    
    with open(urdf_file_path, 'r') as infp:
        robot_desc = infp.read()

    # 1. Start the Robot State Publisher
    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc}]
    )

    # 2. Start the Stereo Vision & AI Node
    stereo_process = ExecuteProcess(
        cmd=['python3', '/app/stereo_node.py'],
        output='screen'
    )

    # 3. CRASH HANDLER (Docker Auto-Recovery)
    # If the AI or camera connection fails, this forces the entire Launch file to shut down.
    # This intentionally crashes the container, allowing Watchtower/Docker's 
    # 'restart: unless-stopped' policy to immediately reboot the vision system.
    crash_handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=stereo_process,
            on_exit=[EmitEvent(event=Shutdown())]
        )
    )

    return LaunchDescription([
        rsp_node,
        stereo_process,
        crash_handler
    ])

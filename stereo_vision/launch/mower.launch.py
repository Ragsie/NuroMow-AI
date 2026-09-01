from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    urdf_file = os.path.join(
        get_package_share_directory('stereo_vision'),
        'urdf',
        'NuroMower.urdf'
    )

    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()

    # Indlæs chassis og kameraspecifikationer fra miljøvariabler (fra nuromow.env) med robuste fallbacks 🆕 [DYNAMISK INDLÆSNING]
    camera_x = os.getenv('NUROMOW_CAMERA_OFFSET_X', '0.25')
    camera_z = os.getenv('NUROMOW_CAMERA_HEIGHT_Z', '0.10')
    camera_pitch = os.getenv('NUROMOW_CAMERA_PITCH_Y', '0.0')
    gps_x = os.getenv('NUROMOW_GPS_OFFSET_X', '-0.15')
    gps_z = os.getenv('NUROMOW_GPS_HEIGHT_Z', '0.25')

    baseline = float(os.getenv('NUROMOW_CAMERA_BASELINE', '0.06'))
    focal_length = float(os.getenv('NUROMOW_CAMERA_FOCAL_LENGTH', '350.0'))

    # 🆕 DYNAMISK NAV2 PARAMETER-INDSPRØJTNING TIL ASYMMETRISK SKÆREHOVED
    # For at undgå at det asymmetriske skærehoved skraber mod forhindringer,
    # indlæser vi Nav2 yaml-skabelonen og erstatter robot_radius og inflation_radius
    # med værdierne direkte fra nuromow.env før kørsel.
    nav2_template_file = os.path.join(
        get_package_share_directory('stereo_vision'),
        'config',
        'nav2_params.yaml'
    )
    resolved_nav2_file = '/tmp/nav2_params_resolved.yaml'

    if os.path.exists(nav2_template_file):
        with open(nav2_template_file, 'r') as f:
            nav2_template = f.read()

        # Erstat parametre
        nav2_resolved = nav2_template.format(
            ROBOT_RADIUS=os.getenv('NUROMOW_ROBOT_RADIUS', '0.28'),
            INFLATION_RADIUS=os.getenv('NUROMOW_NAV2_INFLATION_RADIUS', '0.48')
        )

        # Gem den færdige runtime-konfiguration til Nav2
        with open(resolved_nav2_file, 'w') as f:
            f.write(nav2_resolved)
        print(f"[NuroMow Launch] Dynamisk Nav2-konfiguration gemt i {resolved_nav2_file} med inflation={os.getenv('NUROMOW_NAV2_INFLATION_RADIUS', '0.48')}m")

    # Erstat pladsholderne i URDF-skabelonen dynamisk under opstart 🆕 [DYNAMISK TEMPLATE REPLACEMENT]
    robot_desc_formatted = robot_desc.format(
        CAMERA_OFFSET_X=camera_x,
        CAMERA_HEIGHT_Z=camera_z,
        CAMERA_PITCH_Y=camera_pitch,
        GPS_OFFSET_X=gps_x,
        GPS_HEIGHT_Z=gps_z
    )

    return LaunchDescription([
        # Udgiv robottens transformationer (TF-træ med dynamisk formateret URDF)
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_desc_formatted}]
        ),
        # Start den centrale 3D Stereo Vision node (med parametre hentet fra nuromow.env)
        Node(
            package='stereo_vision',
            executable='stereo_node.py',
            name='stereo_node',
            output='screen',
            parameters=[{
                'video_device': '/dev/video_stereo',
                'frame_id': 'camera_link',
                'baseline': baseline,
                'focal_length': focal_length,
                'camera_height_z': float(camera_z),
                'camera_offset_x': float(camera_x),
                'camera_pitch_y': float(camera_pitch)
            }]
        )
    ])
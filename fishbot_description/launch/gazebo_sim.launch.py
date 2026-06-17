import os
import launch
import launch_ros
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 获取 pkg 的路径
    urdf_tutorial_path = get_package_share_directory('fishbot_description')
    default_model_path = os.path.join(urdf_tutorial_path, 'urdf', 'fishbot', 'fishbot.urdf.xacro')
    
    # 💡 根据你的提醒配置世界
    world_name = 'empty' 
    default_gazebo_world_path = os.path.join(urdf_tutorial_path, 'world', 'custom_room.world')

    # 为 Launch 声明参数
    action_declare_arg_mode_path = launch.actions.DeclareLaunchArgument(
        name='model', default_value=str(default_model_path),
        description='URDF 的绝对路径')

    # xacro 引擎运转，生成 robot_description
    robot_description = launch_ros.parameter_descriptions.ParameterValue(
        launch.substitutions.Command(
            ['xacro ', launch.substitutions.LaunchConfiguration('model')]),
        value_type=str)

    # 状态发布节点
    robot_state_publisher_node = launch_ros.actions.Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True  # 🌟 就是在这里加上这极其关键的一行！
        }]
    )

    # 启动新版 Gazebo Sim
    action_launch_gazebo = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
           [get_package_share_directory('ros_gz_sim'), '/launch/gz_sim.launch.py'],
        ),
        launch_arguments=[('gz_args', [f'-r {default_gazebo_world_path}'])]
    )

    # 在 Gazebo 中生成实体机器人模型
    action_spawn_entity = launch_ros.actions.Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'my_fishbot',                 
            '-topic', 'robot_description',         
            '-x', '0.0', '-y', '0.0', '-z', '0.2'  
        ],
        output='screen'
    )

    # 1️⃣ 传感器数据桥接：⚠️ 注意！这里去掉了 cmd_vel, odom 和 joint_states
    action_ros_gz_bridge = launch_ros.actions.Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # 激光雷达与 IMU
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/imu/data@sensor_msgs/msg/Imu[gz.msgs.IMU',
            # 🌟 极其关键：把 Gazebo 的时间桥接给 ROS 2 系统！
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
        ],
        output='screen'
    )

    # 2️⃣ 深度相机桥接保持不变
    action_ros_gz_depth_camera_bridge = launch_ros.actions.Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/depth_camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/depth_camera/depth/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/depth_camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/depth_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        remappings=[
            # 骗过算法的重映射
            ('/depth_camera/camera_info', '/depth_camera/depth/camera_info'),
        ],
        output='screen'
    )

 # 🎮 3️⃣ 自动加载关节状态控制器 (精简版)
    load_joint_state_controller = launch_ros.actions.Node(
        package='controller_manager',
        executable='spawner',
        arguments=['fishbot_joint_state_controller'],
        output='screen'
    )
    # 🎮 4️⃣ 自动加载差速驱动控制器 (精简版)
    load_diff_drive_controller = launch_ros.actions.Node(
        package='controller_manager',
        executable='spawner',
        arguments=['fishbot_diff_drive_controller'],
        output='screen'
    )
    # 🎮 5️⃣ 自动加载力控制器
    load_effort_controller = launch_ros.actions.Node(
        package='controller_manager',
        executable='spawner',
        arguments=['fishbot_effort_controller'],
        output='screen'
    )

    return launch.LaunchDescription([
        action_declare_arg_mode_path,
        robot_state_publisher_node,
        action_launch_gazebo,
        action_spawn_entity,
        action_ros_gz_bridge,
        action_ros_gz_depth_camera_bridge,
        
        # 🌟 核心回调：当 action_spawn_entity 节点退出（即模型生成完毕）后，再加载控制器
        launch.actions.RegisterEventHandler(
            event_handler=launch.event_handlers.OnProcessExit(
                target_action=action_spawn_entity,
                on_exit=[
                    load_joint_state_controller,
                ]
            )
        ),
        launch.actions.RegisterEventHandler(
            event_handler=launch.event_handlers.OnProcessExit(
                target_action=load_joint_state_controller,
                on_exit=[
                    # load_effort_controller,  # 注释掉力控制器，避免与差速驱动控制器冲突
                    load_diff_drive_controller,  # 启用差速驱动控制器，发布odom->base_footprint TF
                ]
            )
        ),
    ])
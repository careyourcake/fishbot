import launch
import launch_ros
from ament_index_python.packages import get_package_share_directory
"""
Question: Launch 是个 Python 文件，为什么不直接像写普通 Python 代码那样，一行行去 node.start(),
        非要在一开头统一定义好，最后一股脑放进 return LaunchDescription([A, B, C, D]) 里呢？
Answer: 因为 ROS 2 的 Launch 底层是一个“异步并发”引擎！
        如果你用普通的 Python 一行行往下执行，它是阻塞（同步）的。第一行代码卡住了，后面的节点就永远启动不了。
        而你把 A、B、C、D 统统打包进 LaunchDescription 这个清单里并交上去之后：
        统一审查： 底层引擎会先审查整个清单，理清所有节点和旋钮的关系。
        并发拉起： 引擎会像撒网一样，同时把这几十个节点“砰”地一下全部在后台拉起，最大化利用你电脑的 CPU 多核性能。
        生死监控： 引擎会拿着这份清单，一直死死盯着这些进程。如果按 Ctrl+C,引擎会照着清单把它们挨个优雅地干掉,防止出现“僵尸进程”卡死你的 Ubuntu。

"""


"""
generate_launch_description():
    整个系统的开机报告单
    1.描述所有的node
    2.把系统提供给外部的旋钮(参数)也描述一下
    3.启动所有的node
    return:
    一个LaunchDescription对象
    

"""


def generate_launch_description():


    """
    先获取pkg的路径,再获取pkg下的urdf文件(node)路径
    model:还不会动的node,只是个参数,用于在Launch文件中指定urdf文件的路径

    get_package_share_directory():
        文件导航,这里获取pkg的share路径
    launch.actions.DeclareLaunchArgument():
        为Launch这个文件声明一个参数(旋钮),用于在Launch文件中指定urdf文件的路径
        ros2 launch fishbot_description display.launch.py
     --> ros2 launch fishbot_description display.launch.py model:=/home/haoye/Downloads/dji_car.urdf 

    """
    urdf_tutorial_path = get_package_share_directory('fishbot_description')
    default_model_path = urdf_tutorial_path + '/urdf/fishbot/fishbot.urdf.xacro'
    default_rviz_config_path = urdf_tutorial_path + '/config/display_robot_model.rviz'
    # 为 Launch 声明参数
    action_declare_arg_mode_path = launch.actions.DeclareLaunchArgument(
        name='model', default_value=str(default_model_path),
        description='URDF 的绝对路径')


    """
    Question:为什么要将urdf文件转换为字符串类型并好包贴上robot_description的标签?
    Answer:
        1.各个节点是独立进程不能直接把硬盘里urdf文件塞给对方
        2.各个节点传配置信息用的是Parameter,而Parameter只能是基础数据类型其中string类型才能包含xml文件
        3.robot_state_publisher是官方老早写好的代码死规定了启动后去找叫robot_description的参数


    launch.substitutions.Command() :
        相当于ROS2在后台打开一个终端,在此处就是执行xacro命令,将吐出纯XML的URDF文件
    launch.substitutions.LaunchConfiguration('model'):
        是获取Launch文件中定义的参数值
    launch_ros.parameter_descriptions.ParameterValue(value_type=str):
        是将command吐出的urdf转为字符串类型并打好包贴上robot_description的标签
    """
    robot_description = launch_ros.parameter_descriptions.ParameterValue(
        launch.substitutions.Command(
            ['xacro ', launch.substitutions.LaunchConfiguration('model')]),
        value_type=str)



    """
    Question:为什么时间割裂会造成看不见odom
    Answer:
        在 ROS 2 中坐标系(TF)不光记录了位置(x, y, z),还严格绑定了时间戳(Timestamp)。
        在 ROS 2(和 ROS 1)中,“时间”(Time)不仅仅是一个无关紧要的标签,它是整个坐标变换(TF)系统的“生命线”。
        如果不桥接 /clock 统一时间，你的机器人身体活在 2026 年,而它的里程计(odom)却活在 1970 年。
        RViz 无法跨越半个世纪去帮你连接这两个坐标系，只能无奈地把 odom 隐藏起来。



    Argument :
        是给【Launch 文件】用的;生命周期仅在启动前一瞬间
        决定启动哪个Node,去哪个路径下找urdf,给启动的node套上那个namespace
      * node是cpp或python写的独立底层进程,根本听不懂launch(pthon编排脚本)层面的语言
    Parameter:
        是给【具体的 Node (节点)】用的。
        伴随node整个生命周期,最关键的是parameter是动态的
        控制微观算法
    
    launch_ros.actions.Node():
        启动一个node,并给它传递参数
    """
    # 状态发布节点
    robot_state_publisher_node = launch_ros.actions.Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True  # 🌟 就是在这里加上这极其关键的一行！
        }]
    )
    # 关节状态发布节点
    joint_state_publisher_node = launch_ros.actions.Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
    )
    # RViz 节点
    rviz_node = launch_ros.actions.Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', default_rviz_config_path]
    )
    return launch.LaunchDescription([
        action_declare_arg_mode_path,
        joint_state_publisher_node,
        robot_state_publisher_node,
        rviz_node
    ])
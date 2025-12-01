FROM nvidia/cuda:12.8.1-devel-ubuntu24.04

ARG RELEASE
ARG LAUNCHPAD_BUILD_ARCH
ENV USER=user1
ARG PASSWORD=user1
USER root
RUN apt update && apt install -y software-properties-common && add-apt-repository universe
RUN apt update && apt install -y locales && locale-gen en_US en_US.UTF-8
RUN ln -fs /usr/share/zoneinfo/Europe/Rome /etc/localtime
RUN apt update && DEBIAN_FRONTEND=noninteractive apt install --no-install-recommends -qq -y ffmpeg libsm6 libxext6 locales software-properties-common curl sudo git cmake iproute2 unzip bash-completion micro && rm -rf /var/lib/apt/lists/*
RUN update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

RUN addgroup ${USER} \
    && useradd -ms /bin/bash ${USER} -g ${USER} \
    && echo "${USER}:${PASSWORD}" | chpasswd \
    && usermod -a -G sudo ${USER} \
    && sed -i.bak -e 's/%sudo\s\+ALL=(ALL\(:ALL\)\?)\s\+ALL/%sudo ALL=NOPASSWD:ALL/g' /etc/sudoers

USER ${USER}
WORKDIR /home/${USER}

# ROS2 Install
ENV ROS_DISTRO=jazzy
RUN sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg 
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
RUN sudo apt update && DEBIAN_FRONTEND=noninteractive sudo apt install ros-$ROS_DISTRO-ros-base \
    ros-$ROS_DISTRO-sensor-msgs ros-$ROS_DISTRO-geometry-msgs \
    ros-$ROS_DISTRO-cv-bridge ros-$ROS_DISTRO-nav2-common ros-dev-tools ros-$ROS_DISTRO-rmw-cyclonedds-cpp python3-pip python3.12-venv micro tmux -y
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /home/${USER}/.bashrc

RUN sudo apt clean 

# Install pip and system dependencies
RUN cd && mkdir -p $HOME/ros2_ws/src && cd $HOME/ros2_ws/src && git clone https://github.com/hsp-iit/2d_lidar_people_tracker
RUN cd $HOME && python3 -m venv venv && . $HOME/venv/bin/activate && pip install torch && pip install numpy==1.26.4 colcon-common-extensions
RUN cd $HOME/ros2_ws/src/2d_lidar_people_tracker && . $HOME/venv/bin/activate && pip install -r requirements.txt && pip cache purge

# Installing repository
RUN . $HOME/venv/bin/activate && cd $HOME/ros2_ws && colcon build && sh install/setup.bash

# # Update repo
# SHELL ["/bin/bash", "-c"]
# # For recompiling docker here

RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /home/${USER}/.bashrc
RUN echo "source /home/user1/ros2_ws/install/setup.bash" >> /home/${USER}/.bashrc
RUN echo "export ROS_DOMAIN_ID=0" >> /home/${USER}/.bashrc

# Cleanup
CMD ["bash", "-c", ". generate_cyclone_config.sh"]

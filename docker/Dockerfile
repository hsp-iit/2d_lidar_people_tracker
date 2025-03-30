FROM nvidia/cuda:12.1.0-devel-ubuntu22.04

ARG RELEASE
ARG LAUNCHPAD_BUILD_ARCH
ENV USER=user1
ARG PASSWORD=user1

RUN ln -fs /usr/share/zoneinfo/Europe/Rome /etc/localtime && \
    apt update &&\
    apt install --no-install-recommends -y -qq sudo git cmake && \
    rm -rf /var/lib/apt/lists/*

RUN addgroup ${USER} \
    && useradd -ms /bin/bash ${USER} -g ${USER} \
    && echo "${USER}:${PASSWORD}" | chpasswd \
    && usermod -a -G sudo ${USER} \
    && sed -i.bak -e 's/%sudo\s\+ALL=(ALL\(:ALL\)\?)\s\+ALL/%sudo ALL=NOPASSWD:ALL/g' /etc/sudoers

USER ${USER}
WORKDIR /home/${USER}

# # Installing python packages
# Can't use env.yml because cuda install asks to accept agreement
RUN sudo apt update && DEBIAN_FRONTEND=noninteractive sudo apt install ffmpeg libsm6 libxext6 -y

# ROS2 Install
ENV ROS_DISTRO=iron
RUN sudo apt update && sudo apt install -y locales && sudo locale-gen en_US en_US.UTF-8 \
    && sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
    && export LANG=en_US.UTF-8
    
RUN sudo apt install software-properties-common -y\
    && sudo add-apt-repository universe \
    && sudo apt update && sudo apt install curl -y
    
RUN sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg 
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

RUN sudo apt update && sudo apt install ros-$ROS_DISTRO-ros-base \
    ros-$ROS_DISTRO-sensor-msgs ros-$ROS_DISTRO-geometry-msgs \
    ros-$ROS_DISTRO-cv-bridge ros-$ROS_DISTRO-nav2-common ros-dev-tools -y

RUN sudo apt update && sudo apt install ros-$ROS_DISTRO-rmw-cyclonedds-cpp -y
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /home/${USER}/.bashrc

# Install pip and system dependencies
RUN sudo apt update && sudo apt install -y python3-pip
RUN pip3 install torch torchvision
RUN pip3 install numpy==1.21.5 scipy==1.10 numpy-quaternion==2023 pandas==2.0 numba==0.57 matplotlib==3.5 seaborn==0.13 contourpy==1.2 pip setuptools==68

RUN cd && mkdir -p $HOME/ros2_ws/src 

# Git Setup
ARG GIT_USERNAME
ARG GIT_USER_EMAIL
ARG GIT_TOKEN
RUN git config --global user.name ${GIT_USERNAME} && git config --global user.email ${GIT_USER_EMAIL}
# Installing repository and pip dependencies
RUN cd && mkdir -p $HOME/ros2_ws/src && cd $HOME/ros2_ws/src git clone https://${GIT_TOKEN}@github.com/hsp-iit/2d_lidar_people_tracker
RUN pip3 install -r 2d_lidar_people_tracker/requirements.txt
RUN cd $HOME/ros2_ws && colcon build && source install/setup.bash

# # Update repo
# SHELL ["/bin/bash", "-c"]
# # For recompiling docker here

RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /home/${USER}/.bashrc
RUN echo "source /home/user1/ros2_ws/install/setup.bash" >> /home/${USER}/.bashrc
RUN echo "export ROS_DOMAIN_ID=0" >> /home/${USER}/.bashrc

# Cleanup
RUN sudo apt update && sudo apt install -y iproute2 unzip terminator bash-completion micro mlocate && sudo apt clean && sudo rm -rf /var/lib/apt/lists/* && sudo updatedb

CMD ["bash", "-c", ". generate_cyclone_config.sh"]

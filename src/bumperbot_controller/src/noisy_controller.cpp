#include "bumperbot_controller/noisy_controller.h"
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_ros/transform_broadcaster.h>
#include <random>


NoisyController::NoisyController(const ros::NodeHandle &nh, double radius, double separation) : 
            nh_(nh), 
            wheel_radius_(radius),
            wheel_separation_(separation),
            left_wheel_prev_pos_(0.0),
            right_wheel_prev_pos_(0.0),
            x_(0.0),
            y_(0.0),
            theta_(0.0)
{
    ROS_INFO_STREAM("Using wheel radius " << radius);
    ROS_INFO_STREAM("Using wheel separation " << separation);

    // GET global parameter for topic and services
    std::string odom_noisy_topic_pub_;
    nh_.getParam("/bumperbot_controller/topics/odom_noisy", odom_noisy_topic_pub_);
    std::string joint_states_topic_sub_;
    nh_.getParam("/bumperbot_controller/topics/joint_states", joint_states_topic_sub_);

    prev_time_ = ros::Time::now();

    odom_pub_ = nh_.advertise<nav_msgs::Odometry>(odom_noisy_topic_pub_, 10);
    joint_sub_ = nh_.subscribe(joint_states_topic_sub_, 1000, &NoisyController::jointCallback, this);

    odom_msg_.header.frame_id = "odom";
    odom_msg_.child_frame_id = "base_footprint_ekf";
    odom_msg_.pose.pose.orientation.x = 0.0;
    odom_msg_.pose.pose.orientation.y = 0.0;
    odom_msg_.pose.pose.orientation.z = 0.0;
    odom_msg_.pose.pose.orientation.w = 1.0;

    transform_stamped_.header.frame_id = "odom";
    transform_stamped_.child_frame_id = "base_footprint_noisy";
}


void NoisyController::jointCallback(const sensor_msgs::JointState &state)
{
    // Adds noise to the encoder to simulate a more realistic measurement from the odometry.
    // This uses the C++ random engine and assumes a gaussian random noise.
    unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
    
    std::default_random_engine noise_generator(seed);
    std::normal_distribution<double> left_encoder_noise(0, 0.005);
    std::normal_distribution<double> right_encoder_noise(0, 0.005);

    double wheel_encoder_left = state.position.at(0) + left_encoder_noise(noise_generator);
    double wheel_encoder_right = state.position.at(1) + right_encoder_noise(noise_generator);


    // Implements the inverse differential kinematic model
    // Given the position of the wheels, calculates their velocities
    // then calculates the velocity of the robot wrt the robot frame
    // and then converts it in the global frame and publishes the TF
    double dp_left = wheel_encoder_left - left_wheel_prev_pos_;
    double dp_right = wheel_encoder_right - right_wheel_prev_pos_;
    double dt = (state.header.stamp - prev_time_).toSec();

    // Actualize the prev pose for the next itheration
    left_wheel_prev_pos_ = wheel_encoder_left;
    right_wheel_prev_pos_ = wheel_encoder_right;
    prev_time_ = state.header.stamp;

    // Calculate the rotational speed of each wheel
    double phi_left = dp_left / dt;
    double phi_right = dp_right / dt;

    // Calculate the linear and angular velocity
    double linear = (wheel_radius_ * phi_right + wheel_radius_ * phi_left) / 2;
    double angular = (wheel_radius_ * phi_right - wheel_radius_ * phi_left) / wheel_separation_;

    double d_s = (wheel_radius_ * dp_right + wheel_radius_ * dp_left) / 2;
    double d_theta = (wheel_radius_ * dp_right - wheel_radius_ * dp_left) / wheel_separation_;
    theta_ += d_theta;
    x_ += d_s * cos(theta_);
    y_ += d_s * sin(theta_);

    tf2::Quaternion q;
    q.setRPY(0, 0, theta_);
    odom_msg_.pose.pose.orientation.x = q.x();
    odom_msg_.pose.pose.orientation.y = q.y();
    odom_msg_.pose.pose.orientation.z = q.z();
    odom_msg_.pose.pose.orientation.w = q.w();
    odom_msg_.header.stamp = ros::Time::now();
    odom_msg_.pose.pose.position.x = x_;
    odom_msg_.pose.pose.position.y = y_;
    odom_msg_.twist.twist.linear.x = linear;
    odom_msg_.twist.twist.angular.z = angular;

    odom_pub_.publish(odom_msg_);

    transform_stamped_.transform.translation.x = x_;
    transform_stamped_.transform.translation.y = y_;
    transform_stamped_.transform.rotation.x = q.getX();
    transform_stamped_.transform.rotation.y = q.getY();
    transform_stamped_.transform.rotation.z = q.getZ();
    transform_stamped_.transform.rotation.w = q.getW();
    transform_stamped_.header.stamp = ros::Time::now();

    static tf2_ros::TransformBroadcaster br;
    br.sendTransform(transform_stamped_);
}